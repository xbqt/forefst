"""The three 1.10.3 fixes, one test each, built from the lab volumes that exposed them.

Each test fails on 1.10.2. The witnesses are named in the register rows:
  MD_DEL_RA_004 (T17)  a moved-then-deleted file whose remnant keeps the $DATA descriptor but not its bytes
  MD_ADS_RA_005 (T9)   a named stream on a record split out by a move
  MD_TS_RA_008  (T15)  the printed tier legend against timestomp_verdict(), the single tier source
"""
import inspect

import forefst as F

# ── T17: a remnant that declares content it does not hold must not be graded EXACT ────────────
def test_zeroed_inline_region_is_not_recovered_content():
    """`export deleted` wrote 500 zero bytes for del_split.bin and labelled them EXACT.

    The $DATA descriptor survives the deletion and still declares 500 inline bytes; the bytes themselves
    are gone. Grading that `recoverable_inline` asserts content that was never read. Measured on
    lab314_main (T17) and on the T16 set, where 214 of 849 recovered f_*.bin were all zeros although the
    generator wrote 300 non-zero bytes to every one.
    """
    assert "content_zero_or_absent" in F._RECOVER_LABEL, "the outcome must exist as its own verdict"

    src = inspect.getsource(F._deleted_recoverability)
    # the guard must sit BEFORE the recoverable_inline return, or it can never fire
    guard = src.index("not any(decoded)")
    inline = src.index('return ("recoverable_inline"')
    assert guard < inline, "the empty-content guard must precede the recoverable_inline verdict"

    assert F._RELIABILITY.get("content_zero_or_absent") != "EXACT", \
        "a remnant with no content must never be reported as EXACT"
    assert F._RELIABILITY.get("recoverable_inline") == "EXACT"


def test_content_zero_or_absent_label_states_the_ambiguity():
    """The label has to tell the examiner what was recovered AND what cannot be decided.

    A remnant whose declared inline region reads as zeros has two explanations — the file held zeros, or
    the deletion took the bytes — and nothing in the remnant separates them. A label that asserted only
    "content not present" would state the second as fact.
    """
    label = F._RECOVER_LABEL["content_zero_or_absent"].format(n=500)
    assert "indistinguishable" in label, "the label must not assert one of the two explanations"
    assert "zero" in label.lower()
    assert "500" in label


# ── T9: a named stream on a split record lives in the backing ─────────────────────────────────
def test_backing_tuple_carries_named_streams():
    """`t9_adshost.bin` (a 500 B file with a 500 B ADS, then moved) reported HasADS=False.

    The enumeration read only the type-0x30 name row; a move puts the 0xB0 sub-records in the type-0x40
    backing. 655 backing records on 28 of 102 corpus images carried streams no command could see.
    """
    src = inspect.getsource(F._t40_record_tuple)
    assert "detect_ads_in_resident" in src, \
        "the backing tuple must enumerate the streams the backing holds"
    # appended, never inserted, so every existing rec[N] index keeps its meaning. v1.11.0 appends the
    # per-stream residency map after it, so the list is second-to-last rather than last.
    ret = [l for l in src.splitlines() if l.strip().startswith("return (")][-1]
    fields = [f.strip() for f in ret.split("(", 1)[1].rstrip(")").split(",")]
    assert "_ads" in fields, "the stream list must still be on the tuple"
    assert fields.index("_ads") >= 11, "the stream list must be appended after the original fields"


def test_extract_resolves_streams_on_a_split_record():
    """`extract 'file:stream'` answered \"ADS 's500' not found\" for a moved host.

    Both split-record branches of the extract resolver hardcoded an empty stream list.
    """
    src = inspect.getsource(F.cmd_extract) if hasattr(F, "cmd_extract") else ""
    resolver = inspect.getsource(F._resolve_extract_targets) if hasattr(F, "_resolve_extract_targets") else ""
    body = src + resolver + inspect.getsource(F)  # whole module as the fallback
    # no split-record branch may still declare an empty stream list unconditionally
    assert '"record_placement": "split",\n' in body
    assert body.count('"ads": [],') == 0, \
        "a split-record branch still hardcodes an empty stream list"


# ── T15: the printed legend must match the function that decides the tier ─────────────────────
def test_timestomp_legend_matches_the_verdict_function():
    """The legend said \"HIGH = >=2 independent signals or 1 authoritative\".

    timestomp_verdict() awards HIGH only for USN or hard-link corroboration and never for a signal count:
    on the T15 controlled set a file with three signals is INFO, correctly, because that set is a subset
    of the copy signature.
    """
    # the function's own behaviour, pinned
    assert F.timestomp_verdict({"CHANGE_LATE", "PRE_FORMAT"}, round_ts=True)[0] == "INFO"
    assert F.timestomp_verdict({"PRE_FORMAT"}, usn_conf=True)[0] == "HIGH"
    assert F.timestomp_verdict({"PRE_FORMAT"}, hl_conf=True)[0] == "HIGH"
    assert F.timestomp_verdict({"CHANGE_LATE"})[0] == "MEDIUM"

    legend = "".join(l for l in inspect.getsource(F).splitlines() if "Tiers" in l or "HIGH   —" in l)
    assert ">=2 independent signals" not in legend, \
        "the legend still promises a tier the verdict function never awards"
    assert "AUTHORITATIVE" in inspect.getsource(F), "the legend must name the only route to HIGH"
