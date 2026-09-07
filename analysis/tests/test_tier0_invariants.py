"""Tier 0 — structural invariants. No disk image, runs in well under a second.

These are the cheapest tests in the suite and the ones that prevent the largest
class of silent regressions: the seven hand-maintained command registries drifting
apart, and the CSV header drifting from the row builder.
"""
import ast
import inspect
import os
import subprocess
import sys

import pytest

import forefst as F
import refsanalysis as R

# tests/ lives at analysis/tests/, so the repo root is THREE levels up (tests -> analysis -> repo).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── command registries ──────────────────────────────────────────────────────

def _all_forefst_commands():
    return set(F.SUBCOMMANDS) | set(F.HIDDEN_SUBCOMMANDS) | set(F.FORENSIC_SUBCOMMANDS)


def test_every_forensic_subcommand_has_a_handler():
    assert set(F.FORENSIC_SUBCOMMANDS) == set(F.FORENSIC_HANDLERS)


def test_every_command_has_help_text():
    missing = _all_forefst_commands() - set(F.CMD_HELP)
    assert not missing, f"commands with no CMD_HELP entry: {sorted(missing)}"


def test_no_orphan_help_entries():
    orphans = set(F.CMD_HELP) - _all_forefst_commands() - set(F.SUBCOMMAND_ALIASES)
    assert not orphans, f"CMD_HELP entries for non-existent commands: {sorted(orphans)}"


def test_every_alias_resolves_to_a_real_command():
    bad = set(F.SUBCOMMAND_ALIASES.values()) - _all_forefst_commands()
    assert not bad, f"aliases pointing at nothing: {sorted(bad)}"


def test_hidden_and_visible_command_sets_are_disjoint():
    assert not (set(F.HIDDEN_SUBCOMMANDS) & set(F.SUBCOMMANDS))


def test_refsanalysis_registries_agree():
    declared = {t[0] for t in R.SUBCOMMANDS}
    handled = set(R._HANDLERS)
    # summary++ is dispatched through cmd_summary with a flag, so it is expected
    # to be declared without its own handler entry.
    assert declared - handled == {"summary++"}
    assert not handled - declared
    assert not declared - set(R.CMD_HELP)


def test_moved_commands_are_not_also_served_locally():
    """A command listed as moved to forefst must not still be a refsanalysis verb."""
    declared = {t[0] for t in R.SUBCOMMANDS}
    assert not (R.MOVED_TO_FOREFST & declared)


def test_every_command_renders_help_without_raising():
    for cmd in sorted(_all_forefst_commands()):
        F._render_cmd_help(cmd)          # must not raise
    for cmd in sorted({t[0] for t in R.SUBCOMMANDS}):
        R._render_cmd_help(cmd)


# ─── output-schema invariants ────────────────────────────────────────────────

def test_csv_columns_match_csv_field_builder():
    """CSV_COLUMNS and _csv_fields() keys must be identical — no header/row drift.

    The code comments at emit_csv already claim this invariant; assert it.
    """
    stub = {"path": "a/b.txt", "parent_path": "a", "parent_oid": 0x600,
            "name": "b.txt", "oid": 0, "is_dir": False, "is_resident": True,
            "file_size": 1, "create_time": 0, "modify_time": 0,
            "change_time": 0, "access_time": 0, "file_attrs": 0x20,
            "security_id": 0, "usn": 0, "internal_flags": 0,
            "allocated_size": None, "file_id": 1, "home_oid": 0x600}
    produced = set(F._csv_fields(stub, {}, "3.14", {}))
    declared = set(F.CSV_COLUMNS)
    assert produced == declared, (
        f"only in _csv_fields: {sorted(produced - declared)}; "
        f"only in CSV_COLUMNS: {sorted(declared - produced)}")


def test_csv_columns_are_unique():
    assert len(F.CSV_COLUMNS) == len(set(F.CSV_COLUMNS))


def test_deleted_csv_columns_are_unique():
    assert len(F.DELETED_CSV_COLUMNS) == len(set(F.DELETED_CSV_COLUMNS))


def test_file_filters_are_all_callable():
    for name, pred in F.FILE_FILTERS.items():
        assert callable(pred), name
        pred({})                          # must tolerate an empty record


def test_specials_predicates_are_all_callable():
    for name, _desc, pred in F.SPECIALS_TYPES:
        assert callable(pred), name
        pred({})


# ─── cross-module consistency ────────────────────────────────────────────────

def test_the_two_tools_report_the_same_version():
    assert F.VERSION == R.VERSION


def test_checkpoint_flag_tables_agree():
    """Both tools must name the same CHKP flag bit identically.

    Currently FAILS: the labels diverged (e.g. 0x080 'native-Win11-format
    (v3.10+)' vs 'native-Win11-format'). Once the constant is shared this
    becomes a permanent guard.
    """
    assert F._CHKP_FLAG_BITS == R._CHKP_FLAG_BITS


def test_known_oid_tables_agree():
    assert F._KNOWN_OIDS == R._KNOWN_OIDS


def _module_level_functions(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_no_function_is_defined_twice_in_one_module():
    for mod in ("forefst.py", "refsanalysis.py"):
        tree = ast.parse(open(os.path.join(REPO, mod), encoding="utf-8").read())
        seen, dupes = set(), []
        for n in tree.body:
            if isinstance(n, ast.FunctionDef):
                if n.name in seen:
                    dupes.append(f"{mod}:{n.name}@L{n.lineno}")
                seen.add(n.name)
        assert not dupes, dupes


# Same NAME in both modules, but genuinely different bodies -- these are not copies, they are tool-specific
# renderings (refsanalysis is a lab/structure view, forefst a forensic listing). Frozen so a NEW one cannot
# appear unnoticed; shrinking this set is welcome, growing it needs a reason.
_DIFFERENT_BY_DESIGN = {
    "_filetime_to_str", "_human_size", "_parse_dir_entries",
    "_render_cmd_help", "_walk_dir_tree", "validate_image",
}


def test_no_duplicated_function_bodies_across_modules():
    """No function BODY may be copied between the two modules.

    The single-file rule applies to `forefst.py` only -- it must stay self-contained and stdlib-only.
    `refsanalysis.py` is free to import from it, so a copied body there is duplication with no upside.

    Copying is what this forbids, not sharing a name: `die`, `_int_arg` and `_parse_args` were byte-identical
    copies, but each read its own module-level `PROG`, so importing them bare would have made refsanalysis
    print "forefst: error:". The logic now lives once in forefst and refsanalysis keeps three thin wrappers
    that pass its own PROG -- different bodies, one implementation, identical output.
    """
    a = _module_level_functions(os.path.join(REPO, "forefst.py"))
    b = _module_level_functions(os.path.join(REPO, "refsanalysis.py"))

    copied = []
    for name in (set(a) & set(b)) - {"main"}:
        if ast.dump(a[name]) == ast.dump(b[name]):
            copied.append(name)
    assert not copied, (
        "identical function bodies in both modules -- refsanalysis should import these from forefst: "
        + str(sorted(copied)))

    # and the same-name/different-body set must not grow silently
    same_name = (set(a) & set(b)) - {"main"} - set(_DIFFERENT_BY_DESIGN) - {"die", "_int_arg", "_parse_args"}
    assert not same_name, (
        "new same-name function in both modules; import it or justify the divergence: " + str(sorted(same_name)))


# ─── hygiene ─────────────────────────────────────────────────────────────────

def test_pyflakes_is_clean():
    r = subprocess.run([sys.executable, "-m", "pyflakes",
                        os.path.join(REPO, "forefst.py"),
                        os.path.join(REPO, "refsanalysis.py")],
                       capture_output=True, text=True)
    if r.returncode == 1 and "No module named" in r.stderr:
        pytest.skip("pyflakes not installed")
    assert r.stdout == "", "\n" + r.stdout


def test_declared_python_floor_matches_the_syntax_actually_used():
    """`from __future__ import annotations` is 3.7+, so the README must not say 3.6."""
    readme = os.path.join(REPO, "README.md")
    if not os.path.exists(readme):
        pytest.skip("README.md not present")
    text = open(readme, encoding="utf-8").read()
    src = open(os.path.join(REPO, "forefst.py"), encoding="utf-8").read()
    if "from __future__ import annotations" in src:
        assert "Python 3.6" not in text, (
            "README advertises 3.6 but the code uses PEP 563 (3.7+)")


def test_readme_documented_flags_all_exist():
    """Every `forefst.py <image> --flag` in the README must be a live flag.

    Catches the --provenance class of drift, where a documented entry point was
    disabled in code but left in the README.
    """
    import re
    readme = os.path.join(REPO, "README.md")
    if not os.path.exists(readme):
        pytest.skip("README.md not present")
    text = open(readme, encoding="utf-8").read()
    flags = set(re.findall(r"forefst\.py\s+\S+\s+(--[a-z][a-z-]+)", text))
    known = set(F._VALUED_OPTS)
    for cmd in F.CMD_HELP.values():
        known |= set(re.findall(r"--[a-z][a-z-]+", str(cmd)))
    parser_flags = set(re.findall(r'add_argument\("(--[a-z-]+)"',
                                  inspect.getsource(F.main)))
    known |= parser_flags
    # argparse supplies these itself, so they never appear in an add_argument() call and were
    # reported as "documented but not accepted" the first time this test ran against a README.
    known |= {"--help", "--version"}
    missing = flags - known
    assert not missing, f"README documents flags the code does not accept: {sorted(missing)}"
