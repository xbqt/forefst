"""M3.3 — a handler on an evidence path must RECORD when it fires.

None of these fire on the 106-image corpus. That was measured, not assumed: every handler was given a
counter and nine commands were run against every image, and not one fired. The corpus is 102 mostly-healthy
volumes, and these guard damaged, truncated and hostile input -- which is what a forensic tool meets and
what the corpus does not contain.

So "fix it and watch the corpus change" is not an available proof, and these tests inject the failure
instead: call the function with input that cannot decode, and assert the skip was recorded. A handler that
returns the same answer for "absent" and "unreadable" is the class behind every retraction in this project.
"""
import forefst as F
import pytest


@pytest.fixture(autouse=True)
def _clear_notes():
    F._SKIP_NOTES.clear()
    yield
    F._SKIP_NOTES.clear()


def _recorded(stage):
    return any(k[0] == stage for k in F._SKIP_NOTES)


# ── the shared name decoder ───────────────────────────────────────────────────────────────────────
def test_row_name_decodes_a_good_name():
    assert F._row_name("hi.txt".encode("utf-16-le"), "test", off=0) == "hi.txt"
    assert not _recorded("filename decode"), "a name that decoded must not be recorded as a skip"


def test_row_name_records_a_bad_name_instead_of_dropping_it_silently():
    assert F._row_name(b"\xff\xfe\x00", "test", off=0) is None
    assert _recorded("filename decode"), \
        "an undecodable name returned None without recording — the entry vanishes with nothing said"


def test_row_name_carries_the_context_it_was_given():
    F._row_name(b"\xff\xfe\x00", "a place worth naming", off=0)
    assert _recorded("filename decode")


# ── the reparse target chain ──────────────────────────────────────────────────────────────────────
def _symlink_buffer(target_bytes):
    """A minimal SYMLINK REPARSE_DATA_BUFFER whose PrintName and SubstituteName are `target_bytes`."""
    import struct
    tag = 0xA000000C
    n = len(target_bytes)
    hdr = struct.pack("<IHH", tag, 12 + n, 0) + struct.pack("<HHHHI", 0, n, 0, n, 0)
    return hdr + target_bytes


def test_reparse_target_decodes_a_good_target():
    vd = _symlink_buffer("C:\\x".encode("utf-16-le"))
    assert "C:" in F._reparse_buffer_target(vd)
    assert not _recorded("reparse target decode")


def test_reparse_target_records_when_no_candidate_decodes():
    """Both candidates fail, so the caller is told the reparse point carries no target.

    "This symlink has no target" and "its target would not decode" are different facts, and they used to
    print the same.
    """
    vd = _symlink_buffer(b"\xff\xfe\xff")          # odd length + a lone surrogate: not decodable UTF-16
    F._reparse_buffer_target(vd)
    assert _recorded("reparse target decode"), \
        "every candidate failed and nothing was recorded — the target reads as absent"


# ── the USN banner ────────────────────────────────────────────────────────────────────────────────
def test_the_usn_banner_distinguishes_absent_from_unreadable():
    """The banner is the first thing an examiner reads about a volume.

    Asserted on the source, because the branch lives in `main` around a real image open.
    """
    import inspect
    src = inspect.getsource(F.main)
    assert "_usn_unknown" in src, "the USN banner no longer separates 'absent' from 'could not look'"
    assert "USN: unknown" in src


# ── the pins are decisions, not debt ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fn,marker", [
    ("_looks_text", "PINNED, cosmetic"),
    ("_extent_hole_ranges", "PINNED, and None is the CONTRACT here"),
    ("_extent_hole_bytes", "PINNED, and None is the CONTRACT here"),
])
def test_a_pinned_silent_skip_carries_its_written_reason(fn, marker):
    """A pin without a reason is indistinguishable from an oversight nobody got to."""
    import inspect
    assert marker in inspect.getsource(getattr(F, fn)), \
        f"{fn}'s silent skip lost the reason that justifies pinning it"


def test_a_pin_may_not_sit_on_a_path_that_produces_bytes():
    """`_vlcn_mappable` was pinned and should not have been.

    Its `False` is the safe direction -- it withholds a map rather than inventing one -- but at the
    marker-scan site a False REJECTS the candidate, so a recoverable map is silently not recovered. The
    condition for pinning a silent skip is that it must not decide bytes, a size or a verdict; this decides
    all three. It records now, and the answer it returns is unchanged.
    """
    import inspect
    src = inspect.getsource(F._vlcn_mappable)
    assert "PINNED" not in src, "_vlcn_mappable was re-pinned; it decides bytes and must record"
    assert "_skip_note(" in src, "_vlcn_mappable no longer records a failed mappability test"

    F._SKIP_NOTES.clear()
    assert F._vlcn_mappable(object(), 5) is False, "the safe answer must not change"
    assert any(k[0] == "container-table mappability" for k in F._SKIP_NOTES)
