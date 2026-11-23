"""N576 (the auditor's RC1 check, F1): the count of MLog records missing up to the log end.

An LSN is (generation << 32) | the 4 KiB block's offset in the data area. The generation changes at a wrap -- the
offset restarts at 0 (refs.sys 26100.9818 `LogCoreWriteDataRecord`; `LogCoreScanDataRecord` retries at (gen + 1, 0))
-- AND when a log is created to follow an earlier one, which begins at the next generation and the SAME offset
(`MlLogOpenLog`). On win11refstestmftecmd four generations sit side by side, offsets continuous. 1.14.0 RC1 placed an
LSN at generation x blocks + offset, so a loss that crossed a generation change read as the whole data area:
"65536 record(s) ... missing ... every block of the area should hold a newer record" for 7 zeroed blocks.

The rule now: the blocks missing are those from the tail (the newest record of this log plus its length) forward to
the log end, wrapping at the area's end -- (end - tail) mod blocks. With a record of this log in the area that is
exact: a whole lap written after it would have overwritten its block. The count is of 4 KiB blocks (a record can span
several), stated as such.
"""
import os
import re
import sys

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402
import test_1132_red_waveb_mlog as WM                    # noqa: E402

SynLog, lsn = MC.SynLog, MC.lsn
_COUNT = re.compile(r"(?i)missing\s+from\s+(\d+)\s+log\s+block\(s\)\s+of\s+this\s+volume's\s+log")
_EVERY = re.compile(r"(?i)every\s+block\s+of\s+the\s+area")


def _counts(out, err):
    return [int(c) for c in _COUNT.findall(out + "\n" + err)]


def test_n576_matcher_reads_the_count_and_not_another_number():
    assert _COUNT.findall("MLog: records are missing from 7 log block(s) of this volume's log, from x") == ["7"]
    assert not _COUNT.findall("MLog: 65536 record(s) of this volume's log are missing")


def test_n576_generations_side_by_side_count_the_blocks_from_the_tail(monkeypatch, tmp_path):
    """Four generations at continuous offsets (no wrap), as on win11refstestmftecmd; 11 blocks zeroed across the change
    from generation 3 to 4. The count is 11, and the area is not said to be overwritten."""
    log = (SynLog(tmp_path / "f1.raw").run(1, 0x10, 1, session_start=True).run(0x11, 0x20, 2).run(0x21, 0x30, 3)
           .run(0x31, 0x38, 4).control(lsn(4, 0x31), lsn(4, 0x39)).zero(0x2E, 0x38).write())
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--stats")
    assert _counts(out, err) == [11] and rc == 2 and not _EVERY.search(out + err), \
        "blocks 0x2e-0x38 (generations 3 and 4, offsets continuous) are zeroed: 11 blocks from the tail 3:0x2e to the " \
        "log end 4:0x39, exit 2 (counts %r, exit %s)" % (_counts(out, err), rc) + MC._ctx(rc, out[-1500:] + err)


def test_n576_control_a_wrap_counts_across_the_area_end(monkeypatch, tmp_path):
    """A real wrap (generation 1 to the area's end, generation 2 from block 0): the count runs across the area's end.
    (`session_start` only because the builder cannot write a previous LSN for block 0; the wrap is the LSNs.)"""
    log = (SynLog(tmp_path / "f1w.raw").run(0x10, 0x7F, 1, session_start=True).run(0x00, 0x0C, 2, session_start=True)
           .control(lsn(2, 0x00), lsn(2, 0x0D)).zero(0x7A, 0x7F).zero(0x00, 0x0C).write())
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--stats")
    assert _counts(out, err) == [19] and rc == 2, \
        "tail 1:0x7a, log end 2:0xd after a wrap: 6 + 13 = 19 blocks (counts %r, exit %s)" % (_counts(out, err), rc) \
        + MC._ctx(rc, out[-1500:] + err)


def test_n576_control_nothing_missing_when_a_new_generation_starts_at_the_tail(monkeypatch, tmp_path):
    """A log begun anew at the tail's offset, nothing written after it: nothing is missing."""
    log = (SynLog(tmp_path / "f1n.raw").run(1, 0x20, 1, session_start=True)
           .control(lsn(2, 0x21), lsn(2, 0x21)).write())
    rc, out, err = WM.inproc(monkeypatch, log, "mlog", "--stats")
    assert _counts(out, err) == [] and rc == 0, "end 2:0x21 = the tail's next position: nothing missing (counts %r, " \
        "exit %s)" % (_counts(out, err), rc) + MC._ctx(rc, out[-1500:] + err)


SAMPLE = "step5/win11refstestmftecmd.raw"
_DS = 0x1000000 + 0x8000 * 0x1000                      # the sample's MLog data area (image offset)


def test_n576_the_auditors_case_on_image_win11refstestmftecmd():
    """The auditor's case: blocks 0x12d2-0x12d8 (generation 4) zeroed; the newest record left is 3:0x12d1."""
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        MC._zero_range(p, _DS + 0x12D2 * 0x1000, 7 * 0x1000)
        rc, text = MC.run_tool(MC.FOREFST, p, "mlog", "--stats")
    assert _counts(text, "") == [7] and rc == 2 and not _EVERY.search(text), \
        "7 blocks zeroed across the generation change 3 -> 4: the count is 7, exit 2 (counts %r, exit %s)" % (
            _counts(text, ""), rc) + MC._ctx(rc, text[-1500:])


def test_n576_the_old_count_form_is_printed_nowhere():
    """The matchers of the A7 / N428 / N430 tests read the block form only, so an old-form print left anywhere would let
    their absence assertions pass on it. String literals only: a comment may quote the old form."""
    import ast
    tree = ast.parse(open(os.path.join(REPO, "forefst.py"), encoding="utf-8").read())
    lits = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not [x for x in lits if "of this volume's log are missing" in x or "every block of the area" in x]
