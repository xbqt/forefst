"""N578 / N579 / N580 (the auditor's RC1 check, O1-O3): a checkpoint copy that fails its self-checksum, as `deleted`
and refsanalysis `chkp --verify` report it.

O1: with the superseded copy damaged, `summary` and `integrity` exit 2, but `deleted`, whose Checkpoint Comparison reads
that copy, printed a NOTE and exited 0. O2: with the newest copy damaged, `deleted` labelled the newer copy
"Previous checkpoint". O3: `chkp --verify` verified the copy it decodes only, so with the other copy damaged it exited 0
and said nothing. Each copy is damaged by flipping the last byte of its record (one cluster, all of it under the
self-checksum, E118) on a scratch copy of the public sample.
"""
import os
import sys

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402
import forefst as F                                      # noqa: E402

SAMPLE = "step5/win11refstestmftecmd.raw"
REFSANALYSIS = os.path.join(REPO, "refsanalysis.py")


def _copies(p):
    """(partition start, cluster size, in-use copy, other copy) of the sample: each copy a checkpoint_select record."""
    ps, _desc = F.find_refs_partition(p)                # the sample's volume is in a partition, as the tools find it
    assert ps is not None, "no ReFS volume found in the scratch copy"
    with open(p, "rb") as f:
        cs = F.parse_vbr(f, ps)[0]
        sel = F.checkpoint_select(f, ps, cs, F.parse_supb(f, ps, cs, say=False), require_roots=True)
    use = sel["in_use"]
    other = [c for c in sel["copies"] if c is not use][0]
    return ps, cs, use, other


def _flip_last_byte(p, ps, lcn, cs):
    off = ps + lcn * cs + cs - 1
    with open(p, "r+b") as fh:
        fh.seek(off)
        b = fh.read(1)
        fh.seek(off)
        fh.write(bytes([b[0] ^ 0xFF]))


def test_n578_deleted_exits_2_when_its_comparison_reads_a_failed_superseded_copy():
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        ps, cs, use, other = _copies(p)
        assert other["vc"] < use["vc"], "the sample's other copy is not the older one: the case would not test O1"
        _flip_last_byte(p, ps, other["lcn"], cs)
        rc, text = MC.run_tool(MC.FOREFST, p, "deleted")
    assert rc == 2 and "FAILED its self-checksum" in text, \
        "the superseded copy fails its self-checksum and `deleted` compares against it: exit 2 with the copy named, " \
        "as summary and integrity (exit %s)" % rc + MC._ctx(rc, text[-1500:])


def test_n578_control_deleted_exits_0_with_both_copies_intact():
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        rc, text = MC.run_tool(MC.FOREFST, p, "deleted")
    assert rc == 0, "the undamaged sample: `deleted` exits 0 (exit %s)" % rc + MC._ctx(rc, text[-1500:])


def test_n579_a_newer_copy_that_failed_is_not_called_previous():
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        ps, cs, use, other = _copies(p)
        _flip_last_byte(p, ps, use["lcn"], cs)              # the newest copy fails: the older one is read instead
        rc, text = MC.run_tool(MC.FOREFST, p, "deleted")
    lines = [ln for ln in text.splitlines() if "checkpoint" in ln.lower() and "VC=" in ln]
    assert lines and not any(ln.strip().startswith("Previous checkpoint") and "newest" in ln for ln in lines), \
        "the newest copy failed and the older one is in use: the newer copy must not be labelled 'Previous' " \
        "(lines: %r)" % lines + MC._ctx(rc, text[-1500:])


def test_n580_chkp_verify_reports_the_other_copy_that_fails_and_exits_2():
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        ps, cs, use, other = _copies(p)
        _flip_last_byte(p, ps, other["lcn"], cs)
        rc, text = MC.run_tool(REFSANALYSIS, p, "chkp", "--verify")
    assert rc == 2 and any("[FAIL]" in ln and ("0x%x" % other["lcn"]) in ln for ln in text.splitlines()), \
        "the copy not decoded fails its self-checksum: `chkp --verify` must name it with [FAIL] and exit 2 (exit %s)" \
        % rc + MC._ctx(rc, text[-1500:])


def test_n580_control_chkp_verify_exits_0_with_both_copies_intact():
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        rc, text = MC.run_tool(REFSANALYSIS, p, "chkp", "--verify")
    assert rc == 0 and "[FAIL]" not in text, "the undamaged sample: `chkp --verify` exits 0 (exit %s)" % rc \
        + MC._ctx(rc, text[-1500:])
