"""Audit 5.1 (follow-up) — byte-identical helpers are single-sourced from forefst.

The follow-up audit was right: `forefst.py` staying self-contained does NOT require `refsanalysis` to duplicate
it — refsanalysis imports *from* forefst. Only helpers whose LOGIC is exactly the same (verified AST-identical AND
free of any module global that differs, e.g. PROG) are shared; divergent code (die, main) is
deliberately left alone (1.14.0: _human_size is one IEC form, K6).

K086: `_filetime_to_str`, `_parse_dir_entries` and `_walk_dir_tree` used to be listed as "must differ", and the guard
asserted only that the two objects were not the same object. They were not different in any way that mattered --
`_filetime_to_str` agreed on 1,037,632 of 1,037,632 inputs -- and the walker copies each lacked what the other had
(a cycle guard; real resident sizes). They are merged in forefst.py now, and a divergence is asserted as BEHAVIOUR.
"""
import forefst as F
import refsanalysis as R

# The helpers refsanalysis now imports from forefst instead of redefining (directly referenced ones).
# N340 (PLAN_1.13.2 decision 27.5; a control edit decided by the group-2 lead): `_find_snapshot_files` left this list.
# refsanalysis no longer uses that name -- `summary++` takes fs_content_summary's full-depth snapshot count (N249) --
# and an alias kept only so that this list passed guarded a name the tool does not use.
# 1.14.0 (K6, K14): `_human_size` is one IEC form in both tools; refsanalysis renders flag words with forefst's
# flag_text / flag_names and no longer names `_attrs_to_str`. 1.14.0 (the conformance batch, C2-6): refsanalysis
# computes a boot sector's checksum only through forefst's `boot_sector_checksum` (over the copy's own +0x14 bytes),
# so it no longer names `_vbr_checksum` (N340's rule: no alias kept for this list)
SINGLE_SOURCED = ["_guid_str", "_hx", "_human_size",
                  "_parse_extended_attributes",
                  "_walk_dir_tree", "_filetime_to_str"]                  # K086: merged


def test_c2_6_refsanalysis_sums_a_boot_sector_only_through_forefst():
    """C2-6: no second checksum routine in refsanalysis; every sum goes through forefst's one function."""
    import inspect
    src = inspect.getsource(R)
    assert "_vbr_checksum" not in src
    assert src.count("_forefst.boot_sector_checksum(") >= 4


def test_s8_refsanalysis_reads_a_boot_copy_only_through_forefst():
    """The review S8: refsanalysis's `_read_boot_copy` is a guard around forefst's `_boot_copy_read`, not a second
    reader (it reads nothing itself)."""
    import inspect
    body = inspect.getsource(R._read_boot_copy)
    assert "_forefst._boot_copy_read(" in body and "_read_at(" not in body and "_seek_read(" not in body


# Functions that MUST remain distinct between the two tools (different behaviour or module identity) — a guard so a
# future "de-duplication" pass cannot wrongly merge them.
MUST_DIFFER = ["die", "main"]


def test_shared_helpers_are_single_source():
    for name in SINGLE_SOURCED:
        assert getattr(R, name) is getattr(F, name), f"{name} should be forefst's object (single source)"


def test_human_size_is_one_iec_form_in_both_tools():
    """1.14.0 (K6, decisions 35 / 38): one size form -- IEC units, whole when exact -- so the KB / KiB divergence the
    audit left alone is gone, and the two names are one function."""
    assert F._human_size(1536) == "1.5 KiB" and R._human_size(1536) == "1.5 KiB" and F._human_size(4096) == "4 KiB"


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
