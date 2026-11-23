"""N395 (1.14.0 RC3): a $J that holds non-zero bytes and no record is not said to have bytes "BEYOND the last record".

`parse_usn_records` on a stream of non-zero bytes no record parses from (a record length of 0x11111111): the note must
say the journal holds no record, never "BEYOND the last record" or "ring space not yet written", and the skip must be
recorded (the listing may miss records). No corpus volume has such a journal. RED on forefst b250d99d.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

F = MC.AB.F


def test_n395_a_journal_with_no_record_is_not_said_to_have_bytes_beyond_its_last_record(capsys):
    F._new_view()
    n0 = len(F._SKIP_FINDING)
    recs = F.parse_usn_records(bytes([0x11]) * 0x2000)
    err = " ".join(capsys.readouterr().err.split())
    assert not list(recs), "the bytes parse as no record"
    assert "holds no record" in err and "BEYOND the last record" not in err and "not yet written" not in err, err[-600:]
    assert len(F._SKIP_FINDING) > n0 and F._SKIP_FINDING[-1] == "USN journal", \
        "a $J with no record and non-zero bytes: a recorded skip (exit 2), not a note"


def test_n395_control_bytes_after_the_last_record_keep_their_note():
    """The case K173 measured stays a note: real records, then non-zero bytes after the last one."""
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus("step5/win11refstestmftecmd.raw"), "usn", "--stats")
    t = " ".join(text.split())
    assert "BEYOND the last record" in t and "holds no record" not in t, t[-800:]
