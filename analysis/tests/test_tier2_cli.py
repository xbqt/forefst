"""Tier 2 — CLI contract: exit codes, flag rejection, and output safety.

The exit-code table below is a PROPOSAL, not a description of current behaviour.
Agree it, document it in the README, then let this file enforce it.

    0  success
    1  runtime error (unreadable image, unparseable structure)
    2  usage error (unknown flag, missing value, bad subcommand)
    3  completed, findings of interest (tamper / checksum failure)
"""
import csv
import io
import json
import os
import subprocess
import sys

import pytest

import forefst as F

# tests/ lives at analysis/tests/, so the repo root is THREE levels up (tests -> analysis -> repo).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(REPO, "forefst.py")

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_FINDINGS = 0, 1, 2, 3

ALL_COMMANDS = sorted(set(F.SUBCOMMANDS) | set(F.FORENSIC_SUBCOMMANDS))


def run(*argv, timeout=60):
    return subprocess.run([sys.executable, TOOL, *argv],
                          capture_output=True, text=True, timeout=timeout)


# ─── Finding 1.8 — one exit-code contract ────────────────────────────────────

@pytest.mark.parametrize("cmd", ALL_COMMANDS)
def test_missing_file_is_always_exit_1(cmd, tmp_path):
    r = run(str(tmp_path / "nope.raw"), cmd)
    assert r.returncode == EXIT_ERROR, f"{cmd}: rc={r.returncode}\n{r.stderr[:300]}"
    assert "not found" in r.stderr.lower()


@pytest.mark.parametrize("cmd", ALL_COMMANDS)
def test_unknown_flag_is_always_exit_2(cmd, raw_refs_image):
    r = run(raw_refs_image, cmd, "--definitely-not-a-flag")
    assert r.returncode == EXIT_USAGE, f"{cmd}: rc={r.returncode}\n{r.stderr[:300]}"


@pytest.mark.parametrize("cmd", ALL_COMMANDS)
def test_unknown_flag_is_reported_before_the_image_is_read(cmd, tiny_image):
    """Finding 1.6: a CLI mistake must be diagnosed before image validation.

    Today the native commands do this and the forensic ones do not, so
    `forefst tiny.img usn --typo` complains about the image, not the typo.
    """
    r = run(tiny_image, cmd, "--definitely-not-a-flag")
    assert "definitely-not-a-flag" in r.stderr, (
        f"{cmd}: reported the image problem instead of the flag typo:\n{r.stderr[:300]}")


def test_missing_option_value_says_so(raw_refs_image):
    """Finding 1.7: --partition-start with no value is not an 'unknown option'."""
    r = run(raw_refs_image, "deleted", "--partition-start")
    assert r.returncode == EXIT_USAGE
    assert "unknown option" not in r.stderr.lower(), r.stderr[:300]
    assert "requires a value" in r.stderr.lower() or "expected" in r.stderr.lower()


@pytest.mark.parametrize("cmd", ALL_COMMANDS)
def test_no_command_ever_exits_on_an_unhandled_traceback(cmd, raw_refs_image):
    r = run(raw_refs_image, cmd)
    assert "Traceback (most recent call last)" not in r.stderr, (
        f"{cmd} produced a traceback:\n{r.stderr[-800:]}")


def test_help_works_for_every_command_without_an_image():
    for cmd in ALL_COMMANDS:
        r = run("help", cmd)
        assert r.returncode == EXIT_OK, f"help {cmd}: rc={r.returncode}"
        assert r.stdout.strip(), f"help {cmd} printed nothing"


def test_readme_quickstart_commands_are_all_accepted():
    """Finding 1.4: every command shape shown in the README must parse."""
    readme = os.path.join(REPO, "README.md")
    if not os.path.exists(readme):
        pytest.skip("README.md not present")
    import re
    text = open(readme, encoding="utf-8").read()
    # A command must START with a letter. `[a-z-]+` also matched the OPTION in
    # `forefst.py disk.raw -o files.csv`, so the test demanded that `-o` be a subcommand.
    invocations = re.findall(r"forefst\.py\s+(?:disk\.raw|<image>)\s+([a-z][a-z-]*)", text)
    for cmd in set(invocations):
        if cmd in ("help",):
            continue
        assert cmd in ALL_COMMANDS or cmd in F.SUBCOMMAND_ALIASES, \
            f"README shows `{cmd}` but it is not a command"


# ─── Finding 1.10 — CSV formula injection ────────────────────────────────────

DANGEROUS_PREFIXES = ["=", "+", "-", "@", "\t", "\r"]


@pytest.mark.parametrize("prefix", DANGEROUS_PREFIXES)
def test_csv_cells_never_start_with_a_formula_prefix(prefix):
    """A filename on the evidence volume must not become a formula in Excel.

    The examiner opens files.csv in a spreadsheet; a file named
    `=cmd|'/c calc'!A1` on the suspect volume is a code-execution path.
    """
    payload = prefix + "cmd|'/c calc.exe'!A1"
    rec = {"path": payload, "parent_path": ".", "parent_oid": 0x600,
           "name": payload, "oid": 0, "is_dir": False, "is_resident": True,
           "file_size": 1, "create_time": 0, "modify_time": 0,
           "change_time": 0, "access_time": 0, "file_attrs": 0x20,
           "security_id": 0, "usn": 0, "internal_flags": 0,
           "allocated_size": None, "file_id": 1, "home_oid": 0x600,
           "reparse_target": payload, "ads_names": payload}
    buf = io.StringIO()
    F.emit_csv([rec], {}, "3.14", buf)
    row = next(csv.reader([buf.getvalue().splitlines()[1]]))
    offenders = [c for c in row if c and c[0] in "".join(DANGEROUS_PREFIXES)]
    assert not offenders, f"unescaped formula cells: {offenders}"


# ─── Finding 1.9 — one filename sanitizer ────────────────────────────────────

SANITIZER_CASES = [
    "My File.txt", "rapport final.pdf", "../../etc/passwd",
    "A" * 300, "\u6f22\u5b57" * 130, "CON", "nai\u0308ve caf\u00e9.txt",
    "=cmd|'/c calc'!A1", "trailing.  ", ".", "..", "",
]


def _snapshots_inline(name):
    """The third sanitizer, inlined at cmd_snapshots (kept here to compare)."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


@pytest.mark.parametrize("name", SANITIZER_CASES)
def test_all_sanitizers_produce_the_same_result(name):
    """Finding 1.9: three implementations with three different rulesets.

    `My File.txt` survives two of them and becomes `My_File.txt` in the third,
    so the same file lands under different names depending on the subcommand.
    """
    a = F._safe_filename(name)
    b = os.path.basename(F._safe_relpath(name))
    c = _snapshots_inline(name)
    assert a == b == c, f"{name!r} -> _safe_filename={a!r} _safe_relpath={b!r} inline={c!r}"


@pytest.mark.parametrize("name", SANITIZER_CASES)
def test_sanitized_names_fit_the_filesystem_limit(name):
    """255 BYTES, not characters — 120 CJK characters is 360 bytes."""
    for label, out in (("_safe_filename", F._safe_filename(name)),
                       ("_safe_relpath", F._safe_relpath(name)),
                       ("snapshots inline", _snapshots_inline(name))):
        for component in out.split(os.sep):
            assert len(component.encode("utf-8")) <= 255, (
                f"{label}({name[:20]!r}) component is "
                f"{len(component.encode('utf-8'))} bytes")


@pytest.mark.parametrize("name", ["../../etc/passwd", "/abs/path", "a/../../b"])
def test_relpath_never_escapes_the_output_directory(name, tmp_path):
    rel = F._safe_relpath(name)
    resolved = os.path.realpath(os.path.join(str(tmp_path), rel))
    assert resolved.startswith(os.path.realpath(str(tmp_path)) + os.sep)


# ─── output-format equivalence ───────────────────────────────────────────────

@pytest.mark.parametrize("cmd", ALL_COMMANDS)
def test_json_output_is_valid_json_when_the_command_supports_it(cmd, raw_refs_image):
    r = run(raw_refs_image, cmd, "--json")
    if r.returncode == EXIT_USAGE:
        pytest.skip(f"{cmd} does not accept --json")
    if r.returncode != EXIT_OK or not r.stdout.strip():
        pytest.skip(f"{cmd} produced no output on a metadata-only image")
    json.loads(r.stdout)


def test_stdout_and_file_output_are_byte_identical(raw_refs_image, tmp_path):
    """`--csv` and `--csv FILE` must not diverge."""
    dest = tmp_path / "out.csv"
    a = run(raw_refs_image, "files", "--csv")
    run(raw_refs_image, "files", "--csv", str(dest))
    if a.returncode != EXIT_OK or not dest.exists():
        pytest.skip("image too synthetic to produce a listing")
    assert a.stdout == dest.read_text()
