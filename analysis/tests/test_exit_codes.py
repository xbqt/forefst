"""Exit-code contract matrix (audit 2.13 / 2.9).

This LOCKS the process exit codes forefst.py returns per (command, scenario), so an accidental change to the
contract is caught. It documents — deliberately — the CURRENT behaviour, including two known rough edges:

  * exit 2 is OVERLOADED: a `integrity`/`security --audit` FINDING and an argparse USAGE error both use 2;
  * a bad flag exits 2 on the native argparse commands (files/summary/search/details) but 1 on the manually
    parsed forensic commands (usn/mlog/deleted/...).

If a future release renumbers the contract (2 = usage, 3 = findings), update the expectations here in the same
change — that is exactly the regression this test exists to force a conscious decision about.

Needs the real image corpus (findings/tamper cannot be synthesised); skips cleanly when it is not present.
"""
import glob
import os
import subprocess
import sys

import pytest

# tests/ lives at analysis/tests/, so the repo root is THREE levels up (tests -> analysis -> repo).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FOREFST = os.path.join(REPO, "forefst.py")

EXIT_OK = 0            # success / no finding
EXIT_ERROR = 1        # unreadable/unparseable input, invalid argument/target, die()
EXIT_2 = 2            # OVERLOADED: a finding (integrity/security) OR a usage error (argparse commands)


def _corpus_root():
    """Locate the image corpus (analysis/rawdisk/disks) regardless of where the tests were copied to."""
    # No hard-coded absolute path: it was one maintainer's workspace, tried FIRST, so a clone silently
    # searched a directory that does not exist before looking at its own tree. Walk UP instead -- that
    # finds a corpus wherever the checkout sits, and finds nothing in a clone (which ships no images),
    # so the corpus-dependent tests skip rather than pretending to pass.
    seen = set()
    for start in (os.getcwd(), REPO):
        d = os.path.abspath(start)
        while d not in seen:
            seen.add(d)
            cand = os.path.join(d, "analysis", "rawdisk", "disks")
            if os.path.isdir(cand):
                return cand
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


def _find(name):
    root = _corpus_root()
    if not root:
        return None
    hits = glob.glob(os.path.join(root, "**", name), recursive=True)
    return hits[0] if hits else None


def _rc(image, *args):
    r = subprocess.run([sys.executable, FOREFST, image, *args],
                       capture_output=True, text=True, timeout=300)
    return r.returncode


@pytest.fixture(scope="module")
def refs_image():
    p = _find("win11refs8g.raw")
    if not p:
        pytest.skip("no ReFS corpus image available")
    return p


@pytest.fixture(scope="module")
def ntfs_image():
    p = _find("win11ntfstestmftecmd.raw")
    if not p:
        pytest.skip("no NTFS control image available")
    return p


@pytest.fixture(scope="module")
def integrity_fail_image():
    p = _find("win11refs2tmillionsofactions.raw")
    if not p:
        pytest.skip("no integrity-failing image available")
    return p


# ── success = 0 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("cmd", [
    ("summary",), ("files", "--csv"), ("usn", "--stats"), ("mlog", "--stats"),
    ("deleted",), ("timeline", "--csv"), ("specials", "--json"), ("reparse",), ("security",),
])
def test_success_is_zero(refs_image, cmd):
    assert _rc(refs_image, *cmd) == EXIT_OK, f"{cmd} on a clean volume must exit 0"


# ── findings = 2 ─────────────────────────────────────────────────────────────
def test_integrity_failure_is_two(integrity_fail_image):
    """`integrity` returns 2 on a checksum/structural failure (documented, scriptable)."""
    assert _rc(integrity_fail_image, "integrity") == EXIT_2


def test_security_audit_clean_is_zero(refs_image):
    """`security --audit` with no tampering exits 0 (2 is reserved for a real finding)."""
    assert _rc(refs_image, "security", "--audit") == EXIT_OK


# ── errors = 1 ───────────────────────────────────────────────────────────────
def test_bad_image_is_one(ntfs_image):
    assert _rc(ntfs_image, "files") == EXIT_ERROR
    assert _rc(ntfs_image, "usn") == EXIT_ERROR


def test_missing_file_is_one():
    assert _rc(os.path.join(REPO, "definitely-not-here.raw"), "files") == EXIT_ERROR


def test_details_json_no_target_is_nonzero(refs_image):
    """audit 2.12: a machine format with no target must fail (non-zero), not print help + exit 0."""
    assert _rc(refs_image, "details", "--json") != EXIT_OK


def test_partition_start_no_value_is_nonzero(refs_image):
    """audit 2.9: --partition-start with no value is an error, not exit 0."""
    assert _rc(refs_image, "deleted", "--partition-start") != EXIT_OK


# ── the two documented rough edges (locked so a fix is a conscious change) ────
def test_bad_flag_native_command_is_two(refs_image):
    """Native argparse commands reject an unknown flag with 2 (argparse convention)."""
    assert _rc(refs_image, "files", "--definitely-not-a-flag") == EXIT_2


def test_bad_flag_forensic_command_is_one(refs_image):
    """Forensic commands (manual flag parsing) currently exit 1 on an unknown flag — inconsistent with the
    native commands' 2. Locked here; a contract cleanup would change both to the same code."""
    assert _rc(refs_image, "usn", "--definitely-not-a-flag") == EXIT_ERROR
