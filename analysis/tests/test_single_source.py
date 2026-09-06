"""Audit 5.1 (follow-up) — byte-identical helpers are single-sourced from forefst.

The follow-up audit was right: `forefst.py` staying self-contained does NOT require `refsanalysis` to duplicate
it — refsanalysis imports *from* forefst. Only helpers whose LOGIC is exactly the same (verified AST-identical AND
free of any module global that differs, e.g. PROG) are shared; divergent code (_human_size KB/KiB, _filetime_to_str,
the parsers, die) is deliberately left alone.
"""
import forefst as F
import refsanalysis as R

# The helpers refsanalysis now imports from forefst instead of redefining (directly referenced ones).
SINGLE_SOURCED = ["_attrs_to_str", "_find_snapshot_files", "_guid_str", "_hx",
                  "_parse_extended_attributes", "_vbr_checksum"]

# Functions that MUST remain distinct between the two tools (different behaviour or module identity) — a guard so a
# future "de-duplication" pass cannot wrongly merge them.
MUST_DIFFER = ["die", "_human_size", "_filetime_to_str", "_parse_dir_entries", "_walk_dir_tree", "main"]


def test_shared_helpers_are_single_source():
    for name in SINGLE_SOURCED:
        assert getattr(R, name) is getattr(F, name), f"{name} should be forefst's object (single source)"


def test_intentionally_divergent_functions_stay_distinct():
    for name in MUST_DIFFER:
        r = getattr(R, name, None)
        f = getattr(F, name, None)
        if r is not None and f is not None:
            assert r is not f, f"{name} must NOT be merged — it differs between the tools (see AUDIT_RESPONSE)"


def test_safe_filename_is_faithful_never_shortens():
    """The property chosen over the auditor's original 'all sanitizers identical' (which required truncation):
    the extraction sanitizer only maps illegal characters and NEVER shortens a name."""
    for n in ["short.txt", "A" * 300, "漢字" * 130, "My File.txt", "Program Files (x86)"]:
        out = F._safe_filename(n)
        assert len(out) == len(n), f"{n[:20]!r} ({len(n)}) shortened to {out[:20]!r} ({len(out)})"
    assert F._safe_filename("") == "unnamed"
