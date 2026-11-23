"""1.13.2 (ships as 1.14.0) RED cases, wave C step C1, area `mlog`: N422 (tool half); N445 (b), (c); N428 (O4, O5);
N429; N430; N431; N434 (N-4, N-5, N-8, the `mlog --json` help row); N437; N446 (b); N447 (nodes only).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (settlements Q9, Q11-Q13, Q15), `fixes/WAVEC_READING_tables.md`
section 3 CL-1 (the system-table pair choice: LIT {0xA, 0x9}, Upcase {8, 7}), `fixes/WAVEC_measurements/tables_probe.jsonl`
(MR-1: both copies of the Logfile Information Table and of the Upcase Table match their digests, page+0x58 bit 0x8 clear,
121 of 121 volumes -- so no corpus output moves for N422 but MLogInfo.OID), `fixes/WAVEC_INVENTORY.md` /
`fixes/WAVEC_CENSUS.md` (the item rows), `fixes/REVIEW_GB_correctness.md` N-1..N-8, `fixes/GOLDEN_GB_critic.md` U-5,
`fixes/GOLDEN_GBb_critic.md` C-8, RUNNING_LOG N422-N447. Report: `analysis/reports/v1.13.2/fixes/RED_C1.md`.

  N422  (Q9; CL-1 rows 2-5) the Logfile Information Table is read 0xA then 0x9, the Upcase Table 8 then 7; a copy that
        cannot be read is stated and the other used; copies that differ are a redundancy condition (V-a: exit 2 in
        `summary`, `fastsummary`, `integrity`); rows come from the copy in use only; "pri/dup" leaves the labels of
        OID 0x7-0xA (0x500/0x501, 0x540/0x541 keep theirs: not read).
  N445  (b) the one-copy sentence "the Object Table holds no record of OID 0x.." is not made over an Object Table read
        in part; (c) one table down: with the Logfile Information Table's root pages unread, `mlog`, `timeline` and the
        manifest state no driver outcome ("holds no row with key 1 ... would not open", "names no control copy").
  N428  (O4) no count of missing records from a log start (+0x18) that names no block of the data area; (O5) a Logfile
        Information Table read in full with no row 1: the text view stops after the row statement.
  N429  (Q12, option (b)) with no readable control copy, records of another format magic than the volume's are left
        out and counted; the statement says the UUID test cannot be made (not that the format magic is unknown).
  N430  a log end more than one generation ahead of the newest record: the count is that of the data area's blocks.
  N431  (Q13) a MOVE row whose sides name several parent directories prints both sets, never a pick (public sample
        step5/win11refstestmftecmd: 38 rows with overlapping sets print a pick; the class search adds 34 rows whose
        disjoint sets hold more than one OID -- wrong output on the public sample).
  N434  help strings, decimal sizes and counts, PascalCase keys and headers, the P0.1 battery's MLog case.
  N437  (Q15; K29) `ReFS 3.14` in the version sentences; N417's row not padding `supb --verify`'s table; one unit word
        per count ("log blocks", "redo records", "log records"); A7's hole sentence starts with a capital.
  N446  (b) refsanalysis `boot --verify`'s help says it exits 2 on the volume view's conditions.
  N447  coverage nodes (no code change): they pass now and must keep passing.

Measured constants (each cited where it is used): the public sample's 313 MOVE rows split 180 / 34 / 38 / 61 (one parent
each side / disjoint sets with several OIDs / overlapping sets whose lowest OIDs differ / overlapping sets whose lowest
OIDs are equal), read on the dev tree b802dca7 in-process from `_mlog_name_entry_parents` (RED_C1 evidence); step1/
win11refsmini's Logfile Information Table roots (OID 0xA PLCN 0x8074, OID 0x9 PLCN 0x8078, row 1 at page +0x138) and
Upcase roots (OID 0x7 PLCN 0x8020, OID 0x8 PLCN 0x801c, 385 data rows), each re-read below as a premise.
"""
import contextlib
import csv
import io
import json
import os
import re
import struct
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                                # noqa: E402  (K21: internal names)
import test_1132_red_a_bootstrap as AB                   # noqa: E402
import test_1132_red_mlog_chkp as MC                     # noqa: E402
import test_1132_red_waveb_mlog as WM                    # noqa: E402  (SynLog runners, LB68 / N412 / N414 helpers)
import test_1132_red_c1_objtable as OT                   # noqa: E402  (driver, matchers, planted copies)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
_red = OT._red
FOREFST, REFSANALYSIS = AB.FOREFST, AB.REFSANALYSIS
SynLog, lsn = MC.SynLog, MC.lsn
_ctx = OT._ctx

MINI = "step1/win11refsmini.raw"
MINI_PS = 0x1000000
LIT_ROOT = {0x9: 0x8078, 0xA: 0x8074}            # 16 KiB root pages (4 clusters each)
UPCASE_ROOT = {0x7: 0x8020, 0x8: 0x801C}
LIT_ROW1 = struct.pack("<QQQQQ", 0x10000, 0x20000, 0x10000, 0x8000, 0x8001)
LIT_ROW1_AT = 0x138                              # row 1's value in both root pages
UPCASE_DATA_ROWS = 385
_RUNS = {}


def _cli(tool, rel, *args):
    """A read-only CLI run on a corpus image, once per process."""
    key = (tool, rel, args)
    if key not in _RUNS:
        _RUNS[key] = OT.run_cli(tool, MC.corpus(rel), *args)
    return _RUNS[key]


def _clusters(lcn, n=4):
    return [lcn + i for i in range(n)]


def _mini_page(lcn, n=0x4000):
    with open(MC.corpus(MINI), "rb") as fh:
        fh.seek(MINI_PS + lcn * 0x1000)
        return fh.read(n)


def _lit_premise():
    for oid, lcn in LIT_ROOT.items():
        pg = _mini_page(lcn)
        _fx(pg[:4] == b"MSB+" and pg[LIT_ROW1_AT:LIT_ROW1_AT + 40] == LIT_ROW1,
            "OID 0x%x's root (PLCN 0x%x) does not hold row 1 at +0x%x" % (oid, lcn, LIT_ROW1_AT))
    for oid, lcn in UPCASE_ROOT.items():
        _fx(_mini_page(lcn)[:4] == b"MSB+", "Upcase OID 0x%x's root page (PLCN 0x%x) is not MSB+" % (oid, lcn))


def _lines(text, *pats):
    return [ln for ln in text.splitlines() if all(re.search(p, ln) for p in pats)]


_DIFFER = r"(?i)\bdiffer|\bnot\s+the\s+same\b|\bdo(?:es)?\s+not\s+match|\bmismatch"
# critic M-2: "reads as all zeros" is the tool's own wording for a page it read as zeros (N132), so it counts
_UNREAD = r"(?i)could\s+not\s+be\s+read|cannot\s+be\s+read|\bunreadable\b|\bfail|\breads?\s+as\s+(?:all\s+)?zeros\b"
# A copy that differs, or (if the fix verifies each copy against the Object Table's digest without the plant's
# resealed digest) one that fails its digest: either is the redundancy condition the V-a nodes ask for
_DIFFER_OR_FAIL = _DIFFER + r"|\bfail"


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N422 -- the system-table pairs (CL-1)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# RED 1.13.2 N422: the Logfile Information Table is read from OID 0x9; the driver reads OID 0xA first (InitializeTables) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_the_logfile_information_table_is_read_from_oid_0xa_first_on_image_win11refsmini():
    _lit_premise()
    rc, out, err = _cli(FOREFST, MINI, "mlog", "--json")
    mi = json.loads(out).get("MLogInfo") or {}
    assert str(mi.get("OID")).lower() == "0xa", "both copies hold row 1 (CL-1 row 2: copies opened in slot order 0, 1 " \
        "= OID 0xA, 0x9; two good -> slot 0): MLogInfo.OID is %r, not 0xa (Q9)" % mi.get("OID")


# RED 1.13.2 N422: OID 0xA's root page unreadable is not stated (the tool reads OID 0x9 and never looks at 0xA) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_an_unreadable_oid_0xa_copy_is_stated_and_oid_0x9_used_on_image_win11refsmini(tmp_path):
    _lit_premise()
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["mlog", "--stats"],
                                  {"zero": _clusters(LIT_ROOT[0xA])})
    said = _lines(out + "\n" + err, r"(?i)Logfile\s+Information\s+Table|\bOID\s+0x0*a\b", r"(?i)\b0x0*a\b", _UNREAD)
    located = re.search(r"(?im)^\s*Control PLCN:\s+0x8001\b", out)
    assert said and located, "OID 0xA's root page reads as zeros: refs.sys fails over to OID 0x9 (CL-1 rows 3-4); " \
        "`mlog --stats` must state that the copy OID 0xa could not be read (%d line(s)) and locate the log through " \
        "OID 0x9 (control PLCN 0x8001: %s). The exit is not asserted: a failed copy not in use is V-a (exit 2 in " \
        "summary / fastsummary / integrity); exit %s" % (len(said), bool(located), rc) + _ctx(rc, out[:1200], err)


# RED 1.13.2 N422: ra upcase reads OID 0x07 only: with its root unreadable the table is not read from OID 0x8 (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_upcase_is_read_from_oid_0x8_first_on_image_win11refsmini(tmp_path):
    _lit_premise()
    rc0, out0, _e0 = _cli(REFSANALYSIS, MINI, "upcase")
    _fx(WM.labelled_int(out0, "Data rows") == UPCASE_DATA_ROWS, "the base's upcase: %r" % out0[:400])
    rc, out, err = OT.run_planted(tmp_path, REFSANALYSIS, MC.corpus(MINI), ["upcase"],
                                  {"zero": _clusters(UPCASE_ROOT[0x7])})
    rows = WM.labelled_int(out, "Data rows")
    assert rows == UPCASE_DATA_ROWS, "the Upcase Table is the failover pair {OID 0x8, OID 0x7}, 0x8 read first " \
        "(InitializeUpcaseTable; CL-1 row 2): with OID 0x7's root page unreadable, ra `upcase` must read the %d data " \
        "rows from OID 0x8 (it reads %r)" % (UPCASE_DATA_ROWS, rows) + _ctx(rc, out[:800], err)


def _lit_differ_spec():
    """OID 0x9's row 1 names control copy 1 at PLCN 0x8002 (OID 0xA's: 0x8001); the edited root page's digest in the
    tool's register recomputed, as a resealed Object Table would record it: two copies that both verify and differ."""
    _lit_premise()
    off = LIT_ROW1_AT + 0x20
    return {"edit": [[LIT_ROOT[0x9] + off // 0x1000, off % 0x1000, struct.pack("<Q", 0x8002).hex()]],
            "reref": [0x9]}


def test_n422_control_the_v_a_commands_exit_0_on_the_base():
    """Not a RED: the premise of the V-a nodes. `summary`, `fastsummary`, `integrity` on the base: exit 0, no line
    saying the Logfile Information Table's copies differ."""
    for cmd in ("summary", "fastsummary", "integrity"):
        rc, out, err = _cli(FOREFST, MINI, cmd)
        _keep(rc == 0 and not _lines(out + err, r"(?i)Logfile\s+Information", _DIFFER), "%s on the base: rc %s" % (cmd, rc))


# RED 1.13.2 N422: two copies of the Logfile Information Table that differ are not a redundancy condition (V-a) (the strict xfail mark removed: fixed in step C1, area mlog)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity"])
def test_n422_differing_logfile_information_copies_are_a_redundancy_condition(tmp_path, cmd):
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), [cmd], _lit_differ_spec())
    # critic M-1: the line names the pair by either copy's OID (0x9 or 0xa)
    said = _lines(out + "\n" + err, r"(?i)Logfile\s+Information\s+Table", r"(?i)\b0x0*(?:9|a)\b", _DIFFER_OR_FAIL)
    assert rc == 2 and said, "OID 0x9's row 1 differs from OID 0xA's (control copy 1 at 0x8002 / 0x8001), both verify: " \
        "a redundancy condition (CL-1 row 5; V-a) -- `%s` must exit 2 (exit %s) and say the two copies differ (%d " \
        "line(s))" % (cmd, rc, len(said)) + _ctx(rc, out[-1500:], err)


# RED 1.13.2 N422: the log's place is read from OID 0x9's row 1, not from the copy in use (OID 0xA) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_the_rows_come_from_the_copy_in_use_on_image_win11refsmini(tmp_path):
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["mlog", "--stats"], _lit_differ_spec())
    plcns = re.findall(r"(?im)^\s*Control copy \d+ \(PLCN (0x[0-9a-f]+)\)", out)
    assert re.search(r"(?im)^\s*Control PLCN:\s+0x8001\b", out) and plcns == ["0x8000", "0x8001"], "the copy in use " \
        "is OID 0xA, whose row 1 names control copies 0x8000 and 0x8001 (CL-1 row 5: rows from the current copy only; " \
        "the other copy is evidence); the run reads %r" % plcns + _ctx(rc, out[:1500], err)


_LIT_OR_OID_A = r"(?i)Logfile\s+Information\s+Table|\b(?:OID|object)\s+0x0*a\b"


# RED 1.13.2 N422: an unreadable OID 0xA copy (not in use: 0x9 is read) is not a redundancy condition (V-a) (the strict xfail mark removed: fixed in step C1, area mlog)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity"])
def test_n422_an_unreadable_logfile_information_copy_is_a_redundancy_condition(tmp_path, cmd):
    """Critic M-2 (the brief's exit rule: a copy not in use that fails or cannot be read is V-a, exit 2 in summary,
    fastsummary, integrity; CL-1 rows 3-4): OID 0xA's root page reads as zeros, the volume is read through OID 0x9."""
    _lit_premise()
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), [cmd], {"zero": _clusters(LIT_ROOT[0xA])})
    said = _lines(out + "\n" + err, _LIT_OR_OID_A, r"(?i)\b0x0*a\b", _UNREAD)
    assert rc == 2 and said, "OID 0xA's copy of the Logfile Information Table cannot be read (the copy refs.sys opens " \
        "first; the log is reached through OID 0x9): a redundancy condition (V-a) -- `%s` must exit 2 (exit %s) and " \
        "say the copy could not be read (%d line(s))" % (cmd, rc, len(said)) + _ctx(rc, out[-1500:], err)


def _lit_a_premise_digest(monkeypatch):
    """The Object Table records a digest for OID 0xA's root page (the test that makes an altered copy a failed one)."""
    import test_1132_red_waveb_rest as WR
    WR._n425_fresh(monkeypatch)
    for name in ("_OBJ_ROOT_REF", "_OBJ_ROOT_LCNS"):
        monkeypatch.setattr(F, name, {})
    monkeypatch.setattr(F, "_OBJ_ROOT_VERIFIED", set())
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        f, *_r = F.bootstrap(MC.corpus(MINI), None)
    f.close()
    ref = F._OBJ_ROOT_REF.get(0xA)
    _fx(ref and ref[0] == 8 and F.refs_crc64(_mini_page(LIT_ROOT[0xA])) == int.from_bytes(ref[1], "little"),
        "the Object Table records no CRC64 digest for OID 0xA's root page that its page matches: %r" % (ref,))


# RED 1.13.2 N422: OID 0xA's copy failing its Object-Table digest is not stated (the tool never reads 0xA) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_a_logfile_information_copy_failing_its_digest_is_stated_and_the_other_used(monkeypatch, tmp_path):
    """Critic M-3 (CL-1 row 3: failed = unreadable, not matching the Object Table's digest, or +0x58 bit 0x8; row 4:
    use 0x9 when 0xA failed, stated). OID 0xA's row 1 names control copy 1 at PLCN 0x8002 and its digest is NOT
    resealed: 0xA fails, so the log is located through OID 0x9's row (control copies 0x8000, 0x8001)."""
    _lit_premise()
    _lit_a_premise_digest(monkeypatch)
    off = LIT_ROW1_AT + 0x20
    spec = {"edit": [[LIT_ROOT[0xA] + off // 0x1000, off % 0x1000, struct.pack("<Q", 0x8002).hex()]]}
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["mlog", "--stats"], spec)
    said = _lines(out + "\n" + err, _LIT_OR_OID_A, r"(?i)\b0x0*a\b", _DIFFER_OR_FAIL + r"|ALTERED")
    plcns = re.findall(r"(?im)^\s*Control copy \d+ \(PLCN (0x[0-9a-f]+)\)", out)
    assert said and plcns == ["0x8000", "0x8001"], "OID 0xA's root page no longer matches the digest the Object Table " \
        "records: that copy has failed, so the rows come from OID 0x9 (control copies %r, expected 0x8000 / 0x8001) and " \
        "the failed copy is stated (%d line(s)); the exit is not asserted (V-a), exit %s" % (plcns, len(said), rc) \
        + _ctx(rc, out[:1500], err)


# RED 1.13.2 N422: page +0x58 bit 0x8 on OID 0xA's root page (the driver's failed-copy flag) is not stated (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_the_failed_copy_flag_on_a_logfile_information_root_is_stated(tmp_path):
    """Critic M-4 (CL-1 row 3: the descriptor's +0x08 bit 0x8 = page +0x58, read once: "a statement, not a silent
    switch"). The bit set on OID 0xA's root page, its digest resealed (the copy verifies): a line names OID 0xa (or
    the Logfile Information Table's copy) and the flag. Which copy is used is not asserted (not settled)."""
    _lit_premise()
    pg = _mini_page(LIT_ROOT[0xA])
    _fx(not pg[0x58] & 0x08, "OID 0xA's root page +0x58 already has bit 0x8 (MR-1: clear on 121 of 121 volumes)")
    spec = {"edit": [[LIT_ROOT[0xA], 0x58, bytes([pg[0x58] | 0x08]).hex()]], "reref": [0xA]}
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["mlog", "--stats"], spec)
    said = _lines(out + "\n" + err, _LIT_OR_OID_A, r"(?i)\b0x0*a\b", r"(?i)\+?0x58\b|\bflag|\bbit\b")
    assert said, "OID 0xA's root page carries bit 0x8 at +0x58 (the flag refs.sys reads as a failed copy, CL-1 row 3): " \
        "the tool must state it (%d line(s)), not switch or carry on silently; exit %s" % (len(said), rc) \
        + _ctx(rc, out[:1500], err)


def _msb_spans(page):
    """[(row offset, key off, key len, value off, value len)] of one MSB+ page, read by this module."""
    thoff = 0x50 + F.le32(page, 0x50)
    astart, aend = F.le32(page, thoff + 0x10), F.le32(page, thoff + 0x20)
    out = []
    for i in range((aend - astart) // 4):
        ro = thoff + F.le16(page, thoff + astart + 4 * i)
        out.append((ro, ro + F.le16(page, ro + 4), F.le16(page, ro + 6), ro + F.le16(page, ro + 10),
                    F.le16(page, ro + 12)))
    return out


def _upcase_differ_spec(monkeypatch):
    """One byte of a data row of OID 0x7's first leaf changed (its child page; read through the volume's container
    translation, taken from an in-process bootstrap, registers fresh and restored)."""
    import test_1132_red_waveb_rest as WR
    WR._n425_fresh(monkeypatch)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        f, ps, cs, tr, *_r = F.bootstrap(MC.corpus(MINI), None)
    f.close()
    root = _mini_page(UPCASE_ROOT[0x7])
    _fx(F.le32(root, 0x50 + F.le32(root, 0x50) + 0x0C) & 0x100, "OID 0x7's root is not an index page")
    ro, ko, kl, vo, vl = _msb_spans(root)[0]
    child = tr.tr(F.le64(root, vo))
    leaf = _mini_page(child)
    spans = [s for s in _msb_spans(leaf) if s[4] >= 0x100]
    _fx(leaf[:4] == b"MSB+" and spans, "OID 0x7's first child (PLCN 0x%x) is not a leaf with data rows" % child)
    off = spans[0][3] + 0x10
    return {"edit": [[child + off // 0x1000, off % 0x1000, bytes([leaf[off] ^ 0x01]).hex()]]}


# RED 1.13.2 N422: two Upcase Table copies that differ are not a redundancy condition (V-a) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_differing_upcase_copies_are_a_redundancy_condition(monkeypatch, tmp_path):
    spec = _upcase_differ_spec(monkeypatch)
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["fastsummary"], spec)
    said = _lines(out + "\n" + err, r"(?i)Upcase", r"(?i)\b0x0*7\b|\b0x0*8\b", _DIFFER_OR_FAIL)
    assert rc == 2 and said, "a data row of OID 0x7's Upcase Table differs from OID 0x8's: a redundancy condition " \
        "(Q9: differing copies, V-a) -- `fastsummary` must exit 2 (exit %s) and say the copies differ (%d line(s))" \
        % (rc, len(said)) + _ctx(rc, out[-1200:], err)


def _upcase_counts(text):
    return tuple(WM.labelled_int(text, k) for k in ("Data rows", "Non-identity mappings", "Identity mappings"))


# RED 1.13.2 N422: ra upcase reads OID 0x7 first: with both copies readable the mappings come from 0x7, not 0x8 (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_upcase_mappings_come_from_oid_0x8_when_both_copies_read_on_image_win11refsmini(monkeypatch, tmp_path):
    """Critic M-5 (CL-1 rows 2 and 5: the Upcase Table is opened 8 first and its rows come from the copy in use; the
    node with OID 0x7's root unreadable passes for a tool that reads 0x7 first and falls back too). One byte of a
    data row of OID 0x7's first leaf changed: read through OID 0x7 alone (0x8's root unreadable) the mapping counts
    differ from the base's -- the plant is visible; with both copies readable they are the base's."""
    _lit_premise()
    rc0, out0, _e0 = _cli(REFSANALYSIS, MINI, "upcase")
    base = _upcase_counts(out0)
    _fx(base[0] == UPCASE_DATA_ROWS and None not in base, "the base's upcase counts: %r" % (base,))
    spec = _upcase_differ_spec(monkeypatch)
    rc1, out1, err1 = OT.run_planted(tmp_path, REFSANALYSIS, MC.corpus(MINI), ["upcase"],
                                     dict(spec, zero=_clusters(UPCASE_ROOT[0x8])))
    _fx(_upcase_counts(out1)[0] == UPCASE_DATA_ROWS and _upcase_counts(out1) != base,
        "the plant is not visible through OID 0x7 alone: %r (base %r)" % (_upcase_counts(out1), base)
        + _ctx(rc1, out1[:800], err1))
    rc, out, err = OT.run_planted(tmp_path, REFSANALYSIS, MC.corpus(MINI), ["upcase"], spec)
    assert _upcase_counts(out) == base, "both Upcase copies are readable and OID 0x8 is the one refs.sys opens first " \
        "(InitializeUpcaseTable; CL-1 rows 2, 5): ra `upcase` must show 0x8's mappings, the base's %r; it shows %r " \
        "(OID 0x7's, which differ in one row)" % (base, _upcase_counts(out)) + _ctx(rc, out[:800], err)


# RED 1.13.2 N422: an unreadable Upcase copy (OID 0x7, not in use: 0x8 is opened first) is not a redundancy condition (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_an_unreadable_upcase_copy_is_a_redundancy_condition(tmp_path):
    """Critic M-5 (V-a, as the differing-copies node): OID 0x7's root page reads as zeros."""
    _lit_premise()
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["fastsummary"],
                                  {"zero": _clusters(UPCASE_ROOT[0x7])})
    said = _lines(out + "\n" + err, r"(?i)Upcase", r"(?i)\b0x0*7\b", _UNREAD)
    assert rc == 2 and said, "OID 0x7's copy of the Upcase Table cannot be read: a redundancy condition (V-a) -- " \
        "`fastsummary` must exit 2 (exit %s) and say the copy could not be read (%d line(s))" % (rc, len(said)) \
        + _ctx(rc, out[-1200:], err)


def _label_tables():
    import refsanalysis as RA
    return {"forefst.KNOWN_SYSTEM_OIDS": F.KNOWN_SYSTEM_OIDS, "forefst._KNOWN_OIDS": F._KNOWN_OIDS,
            "refsanalysis._KNOWN_OIDS": RA._KNOWN_OIDS}


_PRIDUP = re.compile(r"(?i)\b(?:pri|dup|primary|duplicate)\b")


# RED 1.13.2 N422: OID 0x7-0xA carry 'pri'/'dup' labels the driver contradicts (KNOWN_SYSTEM_OIDS, _KNOWN_OIDS) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n422_the_pair_labels_of_oid_0x7_to_0xa_say_no_primary_or_duplicate():
    bad = ["%s[0x%x]=%r" % (name, oid, t[oid]) for name, t in _label_tables().items()
           for oid in (0x7, 0x8, 0x9, 0xA) if oid in t and _PRIDUP.search(t[oid])]
    assert not bad, "the driver opens {0xA, 0x9} and {8, 7} as failover pairs, table 0 (0xA / 8) first: no copy is " \
        "the primary; labels %s (Q9)" % "; ".join(bad)


def test_n422_cb9_the_other_two_pairs_say_no_primary_or_duplicate_either():
    """Was a control (Q9: 0x500/0x501 and 0x540/0x541 kept their 'dup' labels, not read then). The conformance batch
    (CB-9) read them: `MsCreateDurableFailoverTableObject` creates both as failover pairs, and their copies hold equal
    rows on 117 / 117 volumes (CB_evidence/pairs_census.jsonl), so no copy is the primary and the labels say none."""
    bad = ["%s[0x%x]=%r" % (name, oid, t[oid]) for name, t in _label_tables().items()
           for oid in (0x500, 0x501, 0x540, 0x541) if oid in t and _PRIDUP.search(t[oid])]
    assert not bad, "0x500 / 0x501 and 0x540 / 0x541 are failover pairs: labels %s" % "; ".join(bad)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# In-process runner with the REAL get_mlog_info over a synthetic Object Table (N445 (b), N428 (O5))
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

LIT_VLCN = {0x9: 0x90, 0xA: 0xA0}


def _object_map(oids, damaged):
    """The REAL build_object_map over a walk that returns one row per OID of `oids` (root at LIT_VLCN, else 0x7xx) and,
    when `damaged`, records one page it could not read: an Object Table read in part (else in full)."""
    def walk(*_a, **_k):
        rows = []
        for o in oids:
            vd = bytearray(0x48)
            struct.pack_into("<Q", vd, 0x20, LIT_VLCN.get(o, 0x700 + o))
            rows.append((b"\0" * 8 + struct.pack("<Q", o), bytes(vd)))
        if damaged:
            F._walk_note_damage("unreadable", "page at plcn 0x99: short read (0 bytes) where a page was expected",
                                page=0x99)
        return rows
    real = F.walk_bplus
    F.walk_bplus = walk
    try:
        m = F.build_object_map(None, 0, 0x1000, MC._IdentityTr(), [0x99], register=False)
    finally:
        F.walk_bplus = real
    _fx(sorted(m) == sorted(oids) and (F.object_table_read_state(m) == "partial") == damaged,
        "the object map: %r, state %r" % (sorted(m), F.object_table_read_state(m)))
    return m


def _lit_rows(log, row1=True):
    name = b"\0" * 4 + "Logfile Information Table".encode("utf-16-le")
    rows = [(name, b"")]
    if row1:
        i = log.info
        rows.append((struct.pack("<I", 1), struct.pack("<QQQQQQ", i["data_start_lcn"], i["data_end_lcn"],
                                                       i["data_size_clusters"], i["ctrl_plcn_0"], i["ctrl_plcn_1"], 0)))
    return rows


def lit_inproc(monkeypatch, log, om, lit, cmd, *args):
    """(rc, stdout, stderr) of `cmd` in-process on the SynLog: bootstrap returns `om`; a walk of a Logfile Information
    Table copy's root (LIT_VLCN) returns `lit[oid]`; any other walk is a fixture error. The real get_mlog_info."""
    roots = {(v,): o for o, v in LIT_VLCN.items()}

    def _boot(image, partition_start=None):
        return open(log.path, "rb"), 0, log.cs, MC._IdentityTr(), [], om, 3, 14, []

    def _walk(f, ps, cs, tr, vlcns, *a, **k):
        o = roots.get(tuple(vlcns))
        if o is None:
            raise RedFixtureError("an unexpected table walk (%r): adapt lit_inproc" % (vlcns,))
        return list(lit.get(o, []))

    monkeypatch.setattr(F, "bootstrap", _boot)
    monkeypatch.setattr(F, "walk_bplus", _walk)
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: {})
    WM._n423_regs(monkeypatch)
    return WM._n423_call(cmd, log.path, args)


def _plain_log(tmp_path, name):
    return SynLog(tmp_path / ("%s.raw" % name)).run(1, 0x20, 1, session_start=True).control(MC.END, MC.END).write()


# ─── N445 (b) ─────────────────────────────────────────────────────────────────────────────────────────────────────

_ONE_COPY = re.compile(r"(?i)Object\s+Table\s+holds\s+no\s+record\s+of\s+OID\s+0x0*a\b")


def test_n445_b_control_over_an_object_table_read_in_full_the_one_copy_sentence_is_made(monkeypatch, tmp_path):
    """Not a RED (N421): an Object Table read in full that holds OID 0x9 only: the sentence and exit 2 stay."""
    log = _plain_log(tmp_path, "n445b_full")
    WM._n423_regs(monkeypatch)
    om = _object_map([0x9, 0x701], damaged=False)
    rc, out, err = lit_inproc(monkeypatch, log, om, {0x9: _lit_rows(log)}, "mlog", "--stats")
    _keep(rc == 2 and _ONE_COPY.search(out + err), "the one-copy sentence over a table read in full" + _ctx(rc, out, err))


# RED 1.13.2 N445: (b) 'the Object Table holds no record of OID 0xa' is said over an Object Table read in part (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n445_b_the_one_copy_sentence_is_not_made_over_an_object_table_read_in_part(monkeypatch, tmp_path):
    log = _plain_log(tmp_path, "n445b_part")
    WM._n423_regs(monkeypatch)
    om = _object_map([0x9, 0x701], damaged=True)
    rc, out, err = lit_inproc(monkeypatch, log, om, {0x9: _lit_rows(log)}, "mlog", "--stats")
    one = _ONE_COPY.findall(out + "\n" + err)
    said = OT.undetermined_lines(out + "\n" + err, also=r"(?i)0x0*a\b|Logfile")
    assert rc == 2 and said and not one, "OID 0xA is not among the rows of an Object Table read in part: whether the " \
        "table holds it is not determined (%d line(s)), never 'holds no record of OID 0xa' (%d; Q11), exit 2 (exit %s)" \
        % (len(said), len(one), rc) + _ctx(rc, out, err)


# ─── N445 (c): one table down, both LIT root pages unread ─────────────────────────────────────────────────────────

LIT_UNREAD = {"zero": _clusters(LIT_ROOT[0x9]) + _clusters(LIT_ROOT[0xA])}
_DRIVER_OUTCOME = re.compile(r"(?i)holds\s+no\s+row\s+(?:with\s+key\s+)?1|would\s+not\s+open|names\s+no\s+control\s+cop")


# RED 1.13.2 N445: (c) with both LIT root pages unread, mlog/timeline state 'holds no row with key 1 ... would not open a log' (the strict xfail mark removed: fixed in step C1, area mlog)
@pytest.mark.parametrize("args", [("mlog", "--stats"), ("timeline", "--fast", "--csv")],
                            ids=["mlog-stats", "timeline-csv"])
def test_n445_c_no_driver_outcome_over_a_logfile_information_table_not_read(tmp_path, args):
    _lit_premise()
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), list(args), LIT_UNREAD)
    _fx(re.search(r"(?i)plcn 0x8078 reads as all zeros", err), "the LIT roots did not read as zeros" + _ctx(rc, out, err))
    claims = [ln for ln in (out + "\n" + err).splitlines() if _DRIVER_OUTCOME.search(ln)]
    said = OT.undetermined_lines(out + "\n" + err, table=r"Logfile\s+Information\s+Table")
    assert said and not claims and rc == 2, "the Logfile Information Table's root pages could not be read: its rows are " \
        "not determined (%d line(s)); no driver outcome may be stated (%r), exit 2 (exit %s; Q11 one level down)" \
        % (len(said), [c[:120] for c in claims[:2]], rc) + _ctx(rc, out[:600], err)


# RED 1.13.2 N445: (c) the manifest says the Logfile Information Table 'holds no row 1' when its root pages were not read (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n445_c_the_manifest_states_no_driver_outcome_over_a_logfile_information_table_not_read(tmp_path):
    _lit_premise()
    outdir = str(tmp_path / "bundle")
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["export", "metadata", "-o", outdir], LIT_UNREAD)
    with open(os.path.join(outdir, "manifest.json")) as fh:
        warn = [w for w in (jdoc(json.load(fh), F._BUNDLE_KEYS).get("warnings") or []) if w.get("what") == "mlog"]
    reason = " | ".join(str(w.get("reason")) for w in warn)
    assert warn and not _DRIVER_OUTCOME.search(reason) and OT.undetermined_lines(
        reason, table=r"Logfile\s+Information\s+Table"), "the manifest's MLog warning: %r -- the table could not be read, " \
        "so 'not determined', never 'holds no row 1'" % reason


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N428 -- (O4) a log start that names no block; (O5) no row 1
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# N576 (1.14.0): the count is of 4 KiB log blocks ("records are missing from N log block(s) of this volume's log"); the
# old form is no longer printed (test_1132_rc1check_f1 checks the source), so an absence test cannot pass on it
_MISSING = re.compile(r"(?i)missing\s+from\s+(\d+)\s+log\s+block\(s\)\s+of\s+this\s+volume's\s+log")


# RED 1.13.2 N428: (O4) a count of missing records is made from a log start (+0x18) past the data area (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n428_o4_no_count_from_a_log_start_that_names_no_block(monkeypatch, tmp_path):
    """No record of this log in the 128-block area; the control's log start 5:0x85 names no block (offset > 0x80); the
    end 6:0x3. Today: '3 record(s) ... missing, from 5:0x85 ... (the range starts at the log start)'."""
    log = SynLog(tmp_path / "n428_o4.raw").control(lsn(5, 0x85), lsn(6, 3)).write()
    _fx(log.NBLK == 0x80, "the synthetic area is not 128 blocks")
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--stats")
    counts = _MISSING.findall(out + "\n" + err)
    # critic M-6: any wording that places the start outside the area
    said = _lines(out + "\n" + err, r"(?i)log\s+start", r"(?i)past|beyond|outside|exceed|greater\s+than|larger\s+than"
                  r"|not\s+(?:with)?in\s+the\s+(?:MLog\s+)?data\s+area|names\s+no\s+block|no\s+block")
    assert not counts and said, "the log start's offset 0x85 lies past the data area's 128 blocks, so it names no " \
        "block and no count can be made from it (as N424 for the log end): counts %r, statement %d line(s); the exit " \
        "is not asserted (exit %s)" % (counts, len(said), rc) + _ctx(rc, out[-1500:], err)


# RED 1.13.2 N428: (O5) with no row 1 the text view still prints 'No valid MLog control page found' / 'Log may be clean' (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n428_o5_the_text_view_stops_after_the_row_statement(monkeypatch, tmp_path):
    log = _plain_log(tmp_path, "n428_o5")
    WM._n423_regs(monkeypatch)
    om = _object_map([0x9, 0xA, 0x701], damaged=False)
    rc, out, err = lit_inproc(monkeypatch, log, om, {0x9: _lit_rows(log, row1=False), 0xA: _lit_rows(log, row1=False)},
                              "mlog")
    _keep(re.search(r"(?i)holds\s+no\s+row\s+with\s+key\s+1", out), "the row statement is gone" + _ctx(rc, out, err))
    empty = [ln for ln in out.splitlines() if re.search(r"(?i)No valid MLog control page found|Log may be clean", ln)]
    assert not empty, "the Logfile Information Table holds no row 1, so no log can be located: the text view must stop " \
        "after that statement (as N423's case does), not print the empty sections %r, which read as a clean log" % empty


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N429 -- no readable control copy: another format magic is still told apart
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _n429_log(tmp_path):
    """Records 1..6 of this volume (MAGIC_A, UUID_A) and 7..10 of an earlier volume (MAGIC_B, UUID_B); the volume's
    superblock at LCN 0x1e (data-area block 14) gives the format magic MAGIC_A; both control copies zeroed."""
    log = SynLog(tmp_path / "n429.raw").run(1, 6, 1, session_start=True)
    log.run(7, 10, 1, magic=MC.MAGIC_B, uid=MC.UUID_B)
    log.blocks[14] = WM._supb_block(MC.MAGIC_A)
    log.control(lsn(1, 11), lsn(1, 11))
    WM._unreadable_control(log, "zeroed")
    s = MC.read_block(log.path, 0x1E * log.cs)
    _fx(s[:4] == b"SUPB" and F.le32(s, 0x50) ^ F.le32(s, 0x54) ^ F.le32(s, 0x58) ^ F.le32(s, 0x5C) == MC.MAGIC_A,
        "the planted superblock does not give MAGIC_A")
    return log


def _total_redo(text):
    """The listing's count of redo records under today's label ("Total records") or N437's ("Total redo records",
    "Redo records") -- critic M-7: N437 renames it in the same step."""
    m = re.search(r"(?im)^\s*(?:Total\s+(?:redo\s+)?records|Redo\s+records(?:\s+total)?)\s*:\s*(\d+)\s*$", text)
    return int(m.group(1)) if m else None


def _left_out(text):
    """The count a 'left out' statement gives for an earlier volume's records (another format magic): today's form
    ("N log record(s) of an earlier volume's log are left out") or any line that says N records are left out and names
    an earlier volume or another format magic (critic M-7: the no-control wording is the fix's own)."""
    for ln in text.splitlines():
        if re.search(r"(?i)\bleft\s+out\b", ln) and re.search(r"(?i)earlier\s+volume|format\s+magic", ln):
            m = re.search(r"(?i)\b(\d+)\s+(?:log\s+|redo\s+)?records?(?:\(s\))?[^\d]*?\bleft\s+out\b", ln) or \
                re.search(r"(?i)\bleft\s+out\b[^\d]*?\b(\d+)\s+(?:log\s+|redo\s+)?records?", ln)
            if m:
                return int(m.group(1))
    return 0


# RED 1.13.2 N429: with no readable control copy, records of another format magic are listed, none left out (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n429_another_format_magic_is_left_out_without_a_control_copy(monkeypatch, tmp_path):
    rc, out, err = WM.inproc(monkeypatch, _n429_log(tmp_path), "mlog", "-v")
    listed = _total_redo(out)
    left = _left_out(out + "\n" + err)
    assert listed == 6 and left == 4, "the volume's format magic is known from its superblock (N414), so the 4 records " \
        "of another magic are an earlier volume's even without a control copy (Q12, option (b)): `mlog -v` lists %r " \
        "redo records (6 expected) and states %d left out (4 expected)" % (listed, left) + _ctx(rc, out[-1500:], err)


# RED 1.13.2 N429: N412's statement says the log instance's format magic is unknown, though the superblock gives it (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n429_the_statement_says_only_the_uuid_test_cannot_be_made(monkeypatch, tmp_path):
    rc, out, err = WM.inproc(monkeypatch, _n429_log(tmp_path), "mlog", "--stats")
    text = out + "\n" + err
    unknown = [ln for ln in text.splitlines() if re.search(r"(?i)format\s+magic[^.]*\bunknown\b", ln)]
    uuid_said = [ln for ln in text.splitlines()
                 if re.search(r"(?i)\bUUID\b", ln) and re.search(r"(?i)\bcannot\b|\bcould\s+not\b|\bcan't\b", ln)]
    assert not unknown and uuid_said and rc == 2, "no control copy can be read: the statement may say only that the " \
        "UUID test cannot be made (an earlier log of this volume cannot be told apart), not that the format magic is " \
        "unknown (%r); UUID line(s): %d; exit %s (N412 keeps 2)" % ([u[:120] for u in unknown[:1]], len(uuid_said), rc) \
        + _ctx(rc, out[:800], err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N430 -- A7 across more than one generation
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# RED 1.13.2 N430: a log end two generations ahead gave '143 record(s) ... missing' in a 128-block data area (fixed in
# step C1). N576 (1.14.0, the auditor's RC1 check F1) withdrew C1's reading -- the generation as a lap of the ring, so
# "the count is the area's 128 blocks" -- because a generation also changes when a log is begun anew at the same offset
# (refs.sys MlLogOpenLog); see test_1132_rc1check_f1.
def test_n430_n576_the_count_across_two_generations_is_the_blocks_from_the_tail(monkeypatch, tmp_path):
    """The newest record of this log is 1:0x10; the log end 3:0x20 (REVIEW_GB_correctness N-2's probe shape). The record
    1:0x10 is still in the area, so less than a whole lap was written after it (a lap would have overwritten its block):
    the blocks missing are 1:0x11 forward to the log end, 0x20 - 0x11 = 15, stated once, exit 2."""
    log = SynLog(tmp_path / "n430.raw").run(1, 0x10, 1, session_start=True).control(lsn(2, 0x30), lsn(3, 0x20)).write()
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--stats")
    counts = [int(c) for c in _MISSING.findall(out + "\n" + err)]
    assert counts == [0x20 - 0x11] and rc == 2, "the log end is two generations past the newest record 1:0x10, which is " \
        "still in the area: the count is the 15 blocks from 1:0x11 to the log end, stated once (counts %r), exit 2 " \
        "(exit %s)" % (counts, rc) + _ctx(rc, out[-1200:], err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N431 -- MOVE rows: both parent sets, never a pick (the public sample)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

SAMPLE = "step5/win11refstestmftecmd.raw"
# Group 1 (1.14.0): decision 53 and N533 changed the sample's classes -- the 99 MOVE rows with overlapping sets (61 + 38)
# and the 30 RENAME rows with differing sets are MOVE_OR_RENAME (129), and 6 single-parent rows (5 MOVE, 1 RENAME) whose
# new name is in a table embedded in a directory row (an alternate stream) are DATA_OR_REPARSE_WRITE (432 -> 438);
# measured with the dev tool and with fixes/prefix_G1's on the sample (RC1D/G1_MLOG_NOTES.md)
# Group 1b (1.14.0, decision 55): a move or rename is read from the file's own records (N556); on the sample every one
# pairs -- 295 moves, all under a new name (MOVE_AND_RENAME: the workload renames what it moves), each printing one
# parent per side; no MOVE_OR_RENAME row is left (checked against the sample's key: 697 pairs right, 0 wrong,
# RC1D/evidence/measures/g1b_hval_sample.json)
# (so on the sample these nodes no longer see a directory-set row: that output -- both sets printed, never a pick, and
# "names not paired" -- is pinned by test_1132_g1_mlog test_d53_* and test_1132_g1b_mlog r8 / r14 / review_5)
MOVES, MOVE_SINGLE, MOVE_OVERLAP, MOVE_MULTI_DISJOINT = 295, 295, 0, 0
MOVE_OR_RENAME_ROWS = 0
_OIDS = re.compile(r"0x[0-9a-f]+")


def _move_detail(ln):
    """The parenthesised MOVE detail that starts with 'parent' / 'parents', up to ITS closing parenthesis (critic M-8:
    depth-aware, so a fix that prints each set in parentheses is read whole)."""
    m = re.search(r"\((?=parents?\b)", ln)
    if not m:
        return None
    depth = 0
    for i in range(m.start(), len(ln)):
        if ln[i] == "(":
            depth += 1
        elif ln[i] == ")":
            depth -= 1
            if depth == 0:
                return ln[m.start() + 1:i]
    return None


def _no_names(d):
    """Group 1b: a pair's detail ends with its names (': old → new'), and a payload's other changes follow after
    '; also'; the sides are the OIDs before both."""
    d = d.split("; also ", 1)[0]
    return re.sub(r":\s[^:]*$", "", d) if re.match(r"^(?:same )?parents? 0x", d) else d


def _move_rows():
    rc, out, err = _cli(FOREFST, SAMPLE, "mlog", "--parse")
    rows = [ln for ln in out.splitlines() if re.match(r"^\s+\[MOVE(?:_AND_RENAME)?\s*\]", ln)]
    _fx(len(rows) == MOVES, "%d MOVE / MOVE_AND_RENAME rows: not the sample's %d" % (len(rows), MOVES))
    return rows


def _move_sides():
    """[(old OIDs, new OIDs) as printed] for every MOVE row of `mlog --parse` on the sample: the row's parenthesised
    detail split at its arrow ('→' / '->') or at ', new'."""
    sides = []
    for ln in _move_rows():
        d = _move_detail(ln)
        if d is None:
            sides.append(None)
            continue
        parts = re.split(r"→|->|,\s*new\b", _no_names(d), maxsplit=1)
        sides.append((_OIDS.findall(parts[0]), _OIDS.findall(parts[1])) if len(parts) == 2 else None)
    return sides


# RED 1.13.2 N431: 38 MOVE rows whose parent sets overlap print a pick 'parent A → B' (public sample) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n431_every_move_with_overlapping_parent_sets_shows_both_sets_on_image_win11refstestmftecmd():
    """Decision 53 (1.14.0): a row whose old and new sets overlap without being equal is MOVE_OR_RENAME, and it prints
    both sets (Q13: never a pick); no MOVE row names overlapping sets any more."""
    sides = _move_sides()
    both = [s for s in sides if s and (len(s[0]) > 1 or len(s[1]) > 1) and set(s[0]) & set(s[1])]
    assert len(both) == MOVE_OVERLAP, "%d MOVE rows name overlapping parent sets: such a row is MOVE_OR_RENAME" \
        % len(both)
    rc, out, err = _cli(FOREFST, SAMPLE, "mlog", "--parse")
    mor = [ln for ln in out.splitlines() if re.match(r"^\s+\[MOVE_OR_RENAME\s*\]", ln)]
    shown = [ln for ln in mor if re.search(r"\(parents undetermined: old 0x[0-9a-f]+(;0x[0-9a-f]+)*, new "
                                           r"0x[0-9a-f]+(;0x[0-9a-f]+)*\)", ln)]
    assert len(mor) == MOVE_OR_RENAME_ROWS and len(shown) == len(mor), \
        "%d MOVE_OR_RENAME rows (the sample's %d), %d printing both sets" % (len(mor), MOVE_OR_RENAME_ROWS, len(shown))


# RED 1.13.2 N431: 34 MOVE rows whose disjoint parent sets hold several OIDs print a pick of the lowest (class addition) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n431_a_single_pair_is_printed_only_where_each_side_names_one_parent_on_image_win11refstestmftecmd():
    sides = _move_sides()
    single = [s for s in sides if s and len(s[0]) == 1 and len(s[1]) == 1]
    assert len(single) == MOVE_SINGLE, "%d MOVE rows name one parent directory on each side; the others (%d disjoint " \
        "with several OIDs, %d overlapping) must print their sets, not the lowest OID of each (Q13: never a pick): %d " \
        "rows print a single pair" % (MOVE_SINGLE, MOVE_MULTI_DISJOINT, MOVE_OVERLAP, len(single))


# ---- Added by reviewer 2 of step C1 (fixes/REVIEW_C1_tests.md; C1_LEAD_SETTLEMENTS mlog N-2): N431's RENAME class ----
# The class addition the mlog fixer made in-step (S1: wrong output on the public sample) had no RED node. On the sample
# the 205 RENAME rows' name rows give one directory on each side, the same, for 170; for 35 a side names several
# directories: 5 equal sets, 30 sets that differ (fixes/C1_fix_mlog_evidence/probe_rename.txt). 1.13.1 (prefix_C1)
# printed every one as "same parent <the lowest OID of the new set>": a pick (Q13). Not a RED: written after the fix,
# it fails on a make_tp.sh copy of fixes/prefix_C1 and passes on the dev tree (REVIEW_C1_tests.md section 4).
# Group 1 (1.14.0): the 30 RENAME rows whose sets differ are MOVE_OR_RENAME (decision 53), one is DATA_OR_REPARSE_WRITE
# Group 1b (1.14.0, N556): 323 RENAME rows, each a pair the file's records give ('same parent 0x..: old → new'); the
# pair read inside its own transaction (independent review 1) adds one (322 before)
RENAMES, RENAME_SINGLE, RENAME_SETS_EQUAL, RENAME_SETS_DIFFER = 323, 323, 0, 0


def _rename_sides():
    """[[OID set, ...] per side as printed, or None] for every RENAME row of `mlog --parse` on the sample: the row's
    parenthesised detail that starts with 'same parent(s)' / 'new parent(s)' / 'parent(s)' (depth-aware, as
    `_move_detail`), split into sides at its arrow ('→' / '->') or at ', new'."""
    rc, out, err = _cli(FOREFST, SAMPLE, "mlog", "--parse")
    rows = [ln for ln in out.splitlines() if re.match(r"^\s+\[RENAME\s*\]", ln)]
    _fx(len(rows) == RENAMES, "%d RENAME rows: not the sample's %d" % (len(rows), RENAMES))
    sides = []
    for ln in rows:
        m, d, depth = re.search(r"\((?=(?:same |new )?parents?\b)", ln), None, 0
        for i in range(m.start(), len(ln)) if m else ():
            depth += {"(": 1, ")": -1}.get(ln[i], 0)
            if depth == 0:
                d = ln[m.start() + 1:i]
                break
        sides.append([set(_OIDS.findall(p)) for p in re.split(r"→|->|,\s*new\b", _no_names(d), maxsplit=1)]
                     if d else None)
    return sides


def test_n431_class_a_rename_prints_one_parent_only_where_each_side_names_one_on_image_win11refstestmftecmd():
    """A RENAME prints one parent directory only where its name rows name one directory on each side; equal sets of
    several directories are printed whole, and sets that differ print both sets (Q13: never the lowest OID picked)."""
    sides = _rename_sides()
    one = [s for s in sides if s and len(set().union(*s)) == 1]
    several = [s for s in sides if s and len(set().union(*s)) > 1]
    differ = [s for s in several if len(s) == 2 and s[0] != s[1]]
    assert (len(one), len(several), len(differ)) == (RENAME_SINGLE, RENAME_SETS_EQUAL + RENAME_SETS_DIFFER,
                                                     RENAME_SETS_DIFFER), \
        "RENAME rows printing one parent / a set of several directories / two sets that differ: %d / %d / %d; the " \
        "name rows give %d / %d / %d (the lowest OID of a set is not the parent, Q13)" % (
            len(one), len(several), len(differ), RENAME_SINGLE, RENAME_SETS_EQUAL + RENAME_SETS_DIFFER,
            RENAME_SETS_DIFFER)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N434 -- help strings, forms, the battery's MLog case
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _help(tool, cmd):
    r = subprocess.run([sys.executable, "-B", tool, "help", cmd], capture_output=True, text=True, timeout=120, cwd=REPO)
    _fx(r.returncode == 0 and cmd in r.stdout, "%s help %s: rc %s" % (os.path.basename(tool), cmd, r.returncode))
    return r.stdout


def _opt_text(help_text, opt):
    """The help text of option `opt`: its line and the continuation lines (an empty first column) after it."""
    lines = help_text.splitlines()
    for i, ln in enumerate(lines):
        if re.match(r"^\s+%s\b" % re.escape(opt), ln):
            out = [ln]
            for nxt in lines[i + 1:]:
                if re.match(r"^\s{20,}\S", nxt) and not re.match(r"^\s+-", nxt):
                    out.append(nxt)
                else:
                    break
            return " ".join(x.strip() for x in out)
    raise RedFixtureError("no %s option in the help" % opt)


# RED 1.13.2 N434: the mlog --json help row misses View, LogInstance, EarlierLogs and how transactions refer to records (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_the_mlog_json_help_row_names_every_top_level_key_and_the_record_references():
    rc, out, err = _cli(FOREFST, MINI, "mlog", "--json")
    keys = list(json.loads(out))
    row = _opt_text(_help(FOREFST, "mlog"), "--json")
    missing = [k for k in keys if k not in row] + [k for k in ("RecordIndices", "FirstRecordIndex") if k not in row]
    assert not missing, "the --json help row %r does not name %s (N434 N-4 / LB66)" % (row, missing)


# RED 1.13.2 N434: the mlog help says --parse groups the redo opcodes 'of each transaction' (a row is one log payload) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_the_mlog_help_does_not_say_a_parse_row_is_a_transaction():
    h = _help(FOREFST, "mlog")
    assert not re.search(r"(?is)groups\s+the\s+low-level\s+redo\s+opcodes\s+of\s+each\s+transaction", h), \
        "the help says --parse groups the opcodes 'of each transaction'; a row is one log PAYLOAD (C57)"


# RED 1.13.2 N434: the mlog help's MOVE form lists only 'parent 0x.. -> 0x..' (I3's undetermined form is missing) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_the_mlog_help_names_every_move_form_the_sample_prints():
    """Critic M-9: N-4 asks the help to show the MOVE forms the output prints, and N431 (same step) changes those
    forms; so the node reads the forms from the public sample's `mlog --parse` (the words of each detail before its
    first OID: today 'parent' and 'parents undetermined: old') and asks the help for each, words in order."""
    h = _help(FOREFST, "mlog")
    forms = set()
    for ln in _move_rows():
        d = _move_detail(ln)
        lead = re.split(r"0x[0-9a-f]+", d, maxsplit=1)[0] if d else ""
        words = re.findall(r"[A-Za-z]+", lead)
        if words:
            forms.add(tuple(w.lower() for w in words))
    _fx(forms, "no MOVE detail form read from the sample")
    missing = [" ".join(f) for f in sorted(forms) if not re.search(r"(?i)\b" + r"\W+".join(f) + r"\b", h)]
    assert not missing, "the MOVE forms the sample prints %s; the help does not show %s (N434 N-4: today it shows only " \
        "'parent 0x.. -> 0x..')" % (sorted(" ".join(f) for f in forms), missing)


# RED 1.13.2 N434: `mlog --parse` titles its payload rows 'MLog Transactions (parsed)' (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_the_parse_section_title_does_not_call_payloads_transactions_on_image_win11refsmini():
    rc, out, err = _cli(FOREFST, MINI, "mlog", "--parse")
    _keep(re.search(r"(?i)Log payloads:\s*\d+", out), "the payload count line is gone")
    assert not re.search(r"(?im)^MLog Transactions \(parsed\)", out), "the --parse section is titled 'MLog " \
        "Transactions (parsed)' over rows that are log payloads (C57; N434 N-4)"


# RED 1.13.2 N434: `mlog -v` prints the snake_case label 'format_magic (per-volume format/log-instance constant)' (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_the_logcore_footer_label_on_image_win11refsmini():
    rc, out, err = _cli(FOREFST, MINI, "mlog", "-v")
    _keep(re.search(r"(?i)LogCore Record Headers", out), "the LogCore header listing is gone")
    bad = [ln for ln in out.splitlines() if re.search(r"format_magic|log-instance constant", ln)]
    assert not bad, "the -v footer %r: a snake_case label in text, and the magic is the volume's signature, the " \
        "instance its magic and UUID (N414 / A41)" % bad


# RED 1.13.2 N434: the timeline help's exit-2 list misses the log end past the data area (N424) and N400's USN offset (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_the_timeline_help_lists_every_exit_2_condition():
    h = _help(FOREFST, "timeline")
    assert re.search(r"(?i)(?:past|beyond|outside)\s+(?:the\s+)?(?:MLog\s+|log's\s+)?data\s+area", h) \
        and re.search(r"(?i)\bUSN\b[^.]{0,80}\boffset\b", h), \
        "the timeline help's exit-2 list does not name a log end past the data area (N424) and a USN record whose " \
        "USN is not its offset (N400)"


def _mlog_table_statement(monkeypatch, **geom):
    WM._n423_regs(monkeypatch)
    g = {"row_read": True, "row_len": 48, "table_oids": [0x9, 0xA], "oid": 0x9}
    g.update(geom)
    return F.mlog_table_statements(g)


# RED 1.13.2 N434: N-5: the log size statement prints a byte size in hex ('that is 0x%016x bytes') (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_n5_a_log_size_in_bytes_is_decimal(monkeypatch):
    sz = 0x0010000000000000                  # clusters: times 4 KiB wraps 64 bits to 0
    out = _mlog_table_statement(monkeypatch, size=sz, size_bytes=(sz << 12) & 0xFFFFFFFFFFFFFFFF)
    _fx(out and re.search(r"(?i)\bbytes\b", out[-1]), "no size statement: %r" % out)
    assert not re.search(r"0x[0-9a-f]+\s+bytes", out[-1]), "a byte size is printed in hex: %r (decision 35: sizes " \
        "decimal)" % out[-1]


# RED 1.13.2 N434: N-5: the log size statement prints a cluster count in hex ('at least 0x50 (80) clusters') (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_n5_a_cluster_count_is_decimal(monkeypatch):
    out = _mlog_table_statement(monkeypatch, size=0x40, size_bytes=0x40000)
    _fx(out and re.search(r"(?i)cluster", out[-1]), "no size statement: %r" % out)
    assert not re.search(r"0x[0-9a-f]+(?:\s+\(\d+\))?\s+clusters", out[-1]), "a count of clusters is printed in hex: " \
        "%r (decision 35: counts decimal)" % out[-1]


# RED 1.13.2 N434: N-5: a control copy's log block size is printed in hex ('0x2000 (+0x0C) is not 0x1000') (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_n5_a_log_block_size_is_decimal(monkeypatch, tmp_path):
    log = SynLog(tmp_path / "n434_bs.raw").run(1, 0x20, 1, session_start=True).control(MC.END, MC.END)
    for i in range(2):
        b = bytearray(log.ctrl[i])
        struct.pack_into("<I", b, 0x0C, 0x2000)
        log.ctrl[i] = MC._seal(b)
    log.write()
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--stats")
    lines = _lines(out + "\n" + err, r"(?i)log\s+block\s+size", r"(?i)\+0x0?C\b")
    _fx(lines, "no log block size statement" + _ctx(rc, out[-1500:], err))
    assert not [ln for ln in lines if re.search(r"0x2000|0x1000(?!\w)", ln)], "the block sizes are printed in hex: %r " \
        "(decision 35: sizes decimal, 8192 / 4096)" % lines[:1]


# RED 1.13.2 N434: N-5: `mlog --json` DataArea.PageTypes is keyed by page-type values (zero, MLog, MSB+, data) (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_n5_the_page_type_census_is_not_keyed_by_values_on_image_win11refsmini():
    rc, out, err = _cli(FOREFST, MINI, "mlog", "--json")
    da = json.loads(out).get("DataArea") or {}
    bad = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if not re.match(r"^[A-Z][A-Za-z0-9]*$", k):     # critic M-11: "MLog" is PascalCase (as MLogInfo)
                    bad.append("%s.%s" % (path, k))
                walk(v, "%s.%s" % (path, k))
        elif isinstance(o, list):
            for x in o:
                walk(x, path + "[]")
    walk(da, "DataArea")
    assert not bad, "JSON keys that are values, not PascalCase field names: %s (K21; N434 N-5)" % bad


# RED 1.13.2 N434: N-5: `mlog --json` DataArea.PageTypes keys 'MSB+' / 'data' / 'zero' are page-type values (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_n5_every_page_type_key_is_a_field_name_on_a_synthetic_log(monkeypatch, tmp_path):
    """Critic M-11: step1/win11refsmini's data area holds two of the four page types (zero, MLog); a synthetic log
    adds an MSB+ block and a data block, so the four keys N-5 names are all seen."""
    log = SynLog(tmp_path / "n434_pt.raw").run(1, 0x20, 1, session_start=True)
    log.blocks[0x30] = b"MSB+" + bytes(MC.MLOG_BLK - 4)
    log.blocks[0x31] = b"\x01" * MC.MLOG_BLK
    log.control(lsn(1, 0x21), lsn(1, 0x21)).write()
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--json")
    pt = (json.loads(out).get("DataArea") or {}).get("PageTypes")
    if isinstance(pt, dict):
        keys = list(pt)
        _fx(len(pt) == 4, "the synthetic data area does not hold four page types: %r" % pt)
    else:                                           # a fix may give the census as a list of records
        keys = [k for x in (pt or []) if isinstance(x, dict) for k in x]
        _fx(pt, "no PageTypes census: %r" % pt)
    bad = [k for k in keys if not re.match(r"^[A-Z][A-Za-z0-9]*$", k)]
    assert not bad, "DataArea.PageTypes keys %r: page-type values, not PascalCase field names (K21; N434 N-5)" % bad


# RED 1.13.2 N434: N-5: the bundle's mlog_log_index.csv header mixes forms ('BlockIndex,byte_offset') (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_n5_the_mlog_index_header_is_pascal_case_on_image_win11refsmini(tmp_path):
    outdir = str(tmp_path / "bundle")
    rc, out, err = OT.run_cli(FOREFST, MC.corpus(MINI), "export", "metadata", "-o", outdir)
    p = os.path.join(outdir, "mlog_log_index.csv")
    _fx(os.path.isfile(p), "no mlog_log_index.csv" + _ctx(rc, out, err))
    with open(p) as fh:
        hdr = next(csv.reader(fh))
    assert all(re.match(r"^[A-Z][A-Za-z0-9]*$", c) for c in hdr), "mlog_log_index.csv's header %r: PascalCase " \
        "everywhere (decision 38; N434 N-5)" % hdr


# RED 1.13.2 N434: N-8: the P0.1 damaged battery holds no MLog case (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n434_n8_the_damaged_battery_has_an_mlog_case():
    p = os.path.join(os.path.dirname(REPO), "analysis", "verification", "phase0", "P0.1_damaged_golden", "golden.json")
    _fx(os.path.isfile(p), "the battery's golden.json is not at %s" % p)
    with open(p) as fh:
        cases = json.load(fh)["cases"]
    mlog = [c["id"] for c in cases for pr in c.get("probes", [])
            if (pr.get("args") or [None])[0] == "mlog" and 2 in (pr.get("expect") or {}).get("rc", [])
            and 0 not in (pr.get("expect") or {}).get("rc", [])]
    assert mlog, "no case of the P0.1 battery probes `mlog` expecting exit 2 (A7's plan clause: 'a new battery case " \
        "zeroing the newest 1,024 records'; N434 N-8): cases %r" % [c["id"] for c in cases]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N437 -- forms of wave B's outputs
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

VERSION_EDITED = "step4continuing/win11refsmini_afterchangingversion.raw"
_V_FORM = re.compile(r"(?<![\w.])v\d+\.\d+\b")


def _version_lines(text):
    return [ln for ln in text.splitlines()
            if re.search(r"(?i)boot[- ]sector|VOLUME_INFORMATION", ln) and re.search(r"(?i)version|says|declares", ln)]


# RED 1.13.2 N437: K29: the version sentences print 'v6.66' / 'v3.14' (K29: 'ReFS 3.14') (the strict xfail mark removed: fixed in step C1, area mlog)
@pytest.mark.parametrize("args", [("summary",), ("summary", "--json")], ids=["text", "json"])
def test_n437_k29_the_version_sentences_use_the_refs_form_on_image_afterchangingversion(args):
    rc, out, err = _cli(FOREFST, VERSION_EDITED, *args)
    lines = _version_lines(out)
    _fx(lines and [ln for ln in lines if "6.66" in ln], "no version sentence names 6.66" + _ctx(rc, out[-800:], err))
    bad = [ln.strip()[:140] for ln in lines if _V_FORM.search(ln)]
    assert not bad, "K29 (decided: 'ReFS 3.14'): %s" % bad[:3]


# RED 1.13.2 N437: K29: refsanalysis boot --verify's version rows print 'v3.14' / '$VOLUME_INFORMATION v3.14' (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n437_k29_boot_verify_version_rows_on_image_win11refsmini():
    rc, out, err = _cli(REFSANALYSIS, MINI, "boot", "--verify")
    rows = [ln for ln in out.splitlines() if re.match(r"^\s*version_(?:plausible|corroborated)\b", ln)]
    _fx(len(rows) == 2, "the two version rows: %r" % rows)
    bad = [ln.strip() for ln in rows if _V_FORM.search(ln)]
    assert not bad, "K29 (decided: 'ReFS 3.14'): %s" % bad


# RED 1.13.2 N437: N417's supb_payloads_match row holds the whole sentence: every row of supb --verify padded to 323 (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n437_the_payload_sentence_does_not_pad_the_verify_table_on_image_aftercorruption():
    rc, out, err = _cli(REFSANALYSIS, "step4continuing/win11refsmini_aftercorruption.raw", "supb", "--verify")
    rows = [ln for ln in out.splitlines() if re.match(r"^(?:Check\s|-{10,}\s|[a-z][a-z0-9_]+\s+(?:OK|FAIL|WARN)\b)", ln)]
    pay = [ln for ln in rows if ln.startswith("supb_payloads_match")]
    _fx(pay and "FAIL" in pay[0], "no FAIL supb_payloads_match row" + _ctx(rc, out[-1500:], err))
    below = [ln for ln in out.splitlines() if ln not in rows and re.search(r"(?i)differs in its payload", ln)]
    widest = max(len(ln.rstrip()) for ln in rows)
    assert below and widest <= 160, "the shared sentence belongs below the table (as part 2 did for N265): sentence " \
        "outside the table %d time(s); the widest table line is %d columns" % (len(below), widest)


# RED 1.13.2 N437: `mlog --stats` names 4 KiB log blocks 'pages' and gives redo and log record counts one word 'records' (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n437_each_mlog_count_names_its_unit_on_image_win11refsmini():
    rc, out, err = _cli(FOREFST, MINI, "mlog", "--stats")
    _fx(re.search(r"65536 log blocks of 4 KiB", out), "the data-area line is gone" + _ctx(rc, out[:1500], err))
    pages = _lines(out, r"(?i)^\s*Total pages:")
    blocks = _lines(out, r"(?i)log\s+blocks?", r"\b65536\b")
    redo = _lines(out, r"(?i)redo\s+records?", r"\b746\b")
    logrec = _lines(out, r"(?i)log\s+records?", r"\b145\b")
    assert not pages and len(blocks) >= 2 and redo and logrec, "one unit word per count: 'Total pages' %r for the " \
        "65536 log blocks; 746 redo records labelled %r; 145 log records checked labelled %r (U-5)" % (
            pages, redo[:1], logrec[:1])


# RED 1.13.2 N437: `mlog --json` DataArea.TotalPages counts 4 KiB log blocks under the name 'pages' (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n437_the_json_block_count_is_named_for_log_blocks_on_image_win11refsmini():
    rc, out, err = _cli(FOREFST, MINI, "mlog", "--json")
    da = json.loads(out).get("DataArea") or {}
    named = [k for k, v in da.items() if re.search(r"Block", k) and v == 65536]
    assert "TotalPages" not in da and named, "DataArea keys %r: the 65536 4 KiB log blocks under a name for log " \
        "blocks, not 'pages' (U-5; decision 33: corrected in place)" % sorted(da)


# RED 1.13.2 N437: A7's hole sentence starts in lower case ('the image stores their log blocks as a hole') (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n437_the_a7_hole_sentence_starts_with_a_capital(monkeypatch, tmp_path):
    log = (SynLog(tmp_path / "n437_hole.raw").run(1, 0x20, 1, session_start=True).hole(0x21, 0x2F)
           .control(lsn(1, 0x30), lsn(1, 0x30)).write())
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--stats")
    _fx(_MISSING.search(out + err), "no A7 statement" + _ctx(rc, out[-1200:], err))
    low = [ln for ln in (out + "\n" + err).splitlines() if re.match(r"^\s*(?:\[forefst\]\s*)?[a-z]", ln)
           and re.search(r"(?i)\bhole\b", ln)]
    assert not low, "a sentence starts in lower case: %r (N437)" % low[:1]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N446 (b) -- refsanalysis boot --verify's help
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# RED 1.13.2 N446: (b) ra boot --verify's help does not say it exits 2 on the conditions of the volume view (the strict xfail mark removed: fixed in step C1, area mlog)
def test_n446_b_boot_verify_help_says_it_exits_2_on_view_conditions():
    row = _opt_text(_help(REFSANALYSIS, "boot"), "--verify")
    # critic M-12: "exit 2", "exits 2", "exit code 2", "exit status 2"
    assert re.search(r"(?is)\bexit(?:s|\s+code|\s+status)?\s+(?:is\s+)?2\b.*\b(?:view|every\s+command)\b", row), \
        "the --verify help %r does not say it " \
        "exits 2 on every condition of the volume view, as every command that reads the view does (LB67, N446 (a))" % row


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N447 -- coverage nodes (no code change; they pass and keep passing)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n447_mlog_record_refs_both_branches():
    _keep(F.mlog_record_refs([3, 4, 5]) == {"FirstRecordIndex": 3}, "contiguous: %r" % F.mlog_record_refs([3, 4, 5]))
    _keep(F.mlog_record_refs([3, 5, 6]) == {"RecordIndices": [3, 5, 6]}, "gapped: %r" % F.mlog_record_refs([3, 5, 6]))
    _keep(F.mlog_record_refs([7]) == {"FirstRecordIndex": 7}, "one record: %r" % F.mlog_record_refs([7]))


# critic M-13: the kept property is that every form SAYS the Object Table was read in part and the table could not
# be looked up -- in LB68's words or in Q11's ("was read in part", "not determined"), which N358 asks of other readers
_LB68_PARTIAL = re.compile(r"(?i)Object\s+Table\s+(?:could\s+not\s+be\s+read\s+in\s+full|was\s+read\s+in\s+part)\b[^.\n]*?"
                           r"Logfile\s+Information\s+Table[^.\n]*?(?:could\s+not\s+be\s+looked\s+up|not\s+determined)")


@pytest.mark.parametrize("args", [("mlog", "--stats"), ("mlog", "--json"), ("mlog", "--csv"),
                                     ("timeline", "--fast", "--csv", "--source", "MLOG")],
                            ids=["mlog-stats", "mlog-json", "mlog-csv", "timeline-csv"])
def test_n447_the_partial_object_table_wording_through_the_cli_on_image_millionsofactionsv2(tmp_path, args):
    """GBb critic C-8: millionsofactionsv2's Object-Table leaf 0x424 read as zeros (OT.PARTIAL): exit 2 and LB68's
    'could not be read in full' wording in every form (stdout in text mode, stderr in export modes)."""
    rc, out, err = OT._partial(tmp_path, FOREFST, *args)
    where = out if args == ("mlog", "--stats") else err
    _keep(rc == 2 and _LB68_PARTIAL.search(where), "C-8 %s: rc %s" % (" ".join(args), rc) + _ctx(rc, out[:600], err))


def test_n447_the_manifest_says_in_full_on_image_millionsofactionsv2(tmp_path):
    """The manifest's ' in full' (LB68) through the CLI: `export metadata` on the C-8 fixture."""
    rc, warns = OT.partial_v2_manifest(tmp_path)
    warn = [w for w in warns if w.get("what") == "mlog"]
    _keep(rc == 2 and len(warn) == 1 and re.search(r"(?i)could not be read in full|was read in part",
                                                     str(warn[0].get("reason"))),
          "the manifest's MLog warning: %r" % warn)


def test_n447_an_object_table_read_in_full_holding_neither_oid_gives_n423s_sentence_on_image_win11refsmini(tmp_path):
    """The real ObjectMap, read in full, holding neither OID 0x9 nor 0xA (both removed from the map bootstrap builds;
    `object_table_read_state` None): N423's sentence and exit 2."""
    rc, out, err = OT.run_planted(tmp_path, FOREFST, MC.corpus(MINI), ["mlog", "--stats"], {"drop": [0x9, 0xA]})
    _keep(rc == 2 and WM.n423_statements(out + "\n" + err), "N423's sentence over a table read in full" +
          _ctx(rc, out[:1200], err))


def test_n447_mlog_json_file_equals_the_stdout_document_on_image_win11refsmini(tmp_path):
    dest = str(tmp_path / "m.json")
    rc1, out1, err1 = _cli(FOREFST, MINI, "mlog", "--json")
    rc2, out2, err2 = OT.run_cli(FOREFST, MC.corpus(MINI), "mlog", "--json", dest)
    with open(dest) as fh:
        doc = fh.read()
    _keep(rc1 == rc2 and json.loads(doc) == json.loads(out1) and doc == out1, "--json FILE differs from stdout")
