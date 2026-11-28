"""1.14.1 F5 (the auditor's post-publication check of 1.14.0, finding F5): an MLog row dated by a file's content.

1.14.0 dated an UpdateRow (opcode 0x03) by a fallback -- value 1 read at +0xA0, +0x90, +0x30, +0x28, +0x08, +0x00, the
first plausible FILETIME -- written for the volume-information row (K059) but run on every update with two or more
values. A three-value UpdateRow rewrites PART of a row: refs.sys passes value 2 to CmsBPlusTable::UpdateInIndex as the
offset in the row where value 1 goes (RedoUpdateRow, 26100.9818), so value 1 is a fragment -- on the corpus the size
fields (+0x10) or the inline bytes (+0x3C) of a $DATA or named-stream row -- and on the public Insider sample the bytes
8-15 of a 157-byte .cfg file dated a row 2081-11-18T20:20:59.9829808Z (`timeline`, `mlog --parse`).

The rule since 1.14.1: an UpdateRow is dated only when it rewrites a whole row (two values), by the row's key -- the
volume-information row (0x0520) +0xA0, else +0x90; a name row's embedded record or a directory's own row (0x30 / 0x10)
its $SI times; a 72 / 84-byte index entry its entry times -- and no other row; an InsertRow is read at the record
offsets only on a name row or a directory's own row. Measured old against new on the corpus:
analysis/reports/v1.14.1/F5/ (f5_census*, f5_rows*).

Each test is RED on 1.14.0 (forefst 50dfb8e6...) and GREEN on 1.14.1, except the controls, which hold on both."""
import os
import struct
import subprocess
import sys

import pytest

from _repo import REPO
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_mlog_chkp as MC                     # noqa: E402  (corpus paths, cached runs)

FOREFST = os.path.join(REPO, "forefst.py")


def ft(y, mo, d, h=12, mi=0, s=0):
    """A FILETIME (100 ns since 1601) for a UTC date-time."""
    import datetime
    t = datetime.datetime(y, mo, d, h, mi, s) - datetime.datetime(1601, 1, 1)
    return (t.days * 86400 + t.seconds) * 10 ** 7


T1, T2, T3 = ft(2026, 5, 19, 19, 0, 0), ft(2026, 5, 19, 20, 0, 0), ft(2026, 5, 20, 8, 0, 0)


def redo(opcode, values, tpl=1):
    """A _SmsRedoRecord: size +0x00, opcode +0x04, key-path length +0x08, value count +0x10, the key path's
    (offset, length) pairs from +0x38, then the values' pairs, then the bytes they point at."""
    head = 0x38 + 8 * tpl + 8 * len(values)
    comps = [b"\x00" * 28] * tpl                         # a table component (schema, OID at +20): content not read here
    blobs = comps + list(values)
    pairs, off = [], head
    for b in blobs:
        pairs.append((off, len(b)))
        off += len(b)
    rec = bytearray(off)
    struct.pack_into("<IIII", rec, 0, off, opcode, tpl, 0)
    struct.pack_into("<I", rec, 0x10, len(values))
    for i, (o, n) in enumerate(pairs):
        struct.pack_into("<II", rec, 0x38 + 8 * i, o, n)
    p = head
    for b in blobs:
        rec[p:p + len(b)] = b
        p += len(b)
    return bytes(rec)


def rec_time(rec):
    rs, op, tpl = struct.unpack_from("<III", rec, 0)
    vc = struct.unpack_from("<I", rec, 0x10)[0]
    return F._mlog_extract_timestamp(rec, rs, op, tpl, vc, 0x38 + tpl * 8)


def value(n, times=()):
    """`n` zero bytes with FILETIME `t` at offset `o` for each (o, t)."""
    b = bytearray(n)
    for o, t in times:
        struct.pack_into("<Q", b, o, t)
    return bytes(b)


ATTR_KEY_DATA = bytes.fromhex("4c000000000000000100008080000000")      # an inline $DATA row's key (marker, 0x80)


def test_f5_a_three_value_update_is_not_dated():
    """The F5 record: a three-value UpdateRow writing a file's inline bytes at row offset 0x3C. Its value 1 holds a
    plausible FILETIME at +0x08 -- the file's bytes 8-15 -- which 1.14.0 printed as the row's time."""
    rec = redo(0x03, [ATTR_KEY_DATA, value(160, [(0x08, T1)]), struct.pack("<I", 0x3C)], tpl=2)
    assert rec_time(rec) == 0


def test_f5_b_three_value_update_of_size_fields_is_not_dated():
    rec = redo(0x03, [ATTR_KEY_DATA, value(40, [(0x00, T1)]), struct.pack("<I", 0x10)], tpl=2)
    assert rec_time(rec) == 0


def test_f5_c_whole_row_update_of_another_row_is_not_dated():
    """A two-value UpdateRow of a FileId row (key type 0x20): its value holds a name or a reference, no time."""
    rec = redo(0x03, [b"\x20\x00" + b"\x00" * 22, value(0x60, [(0x30, T1)])])
    assert rec_time(rec) == 0


def test_f5_d_insert_of_a_fileid_row_is_not_read_at_the_record_offsets():
    """An InsertRow of a 72-byte FileId row (key type 0x20) with nothing at the entry offsets: 1.14.0 read it at the
    record offsets (+0x28..+0x40)."""
    rec = redo(0x01, [b"\x20\x00" + b"\x00" * 22, value(72, [(0x30, T1)])])
    assert rec_time(rec) == 0


# ── controls: what K059 and N646 date, unchanged ────────────────────────────────────────────────────────────────

def test_control_volume_information_row_write_time():
    rec = redo(0x03, [b"\x20\x05" + b"\x00" * 6, value(0xA8, [(0x90, T1), (0xA0, T2)])])
    assert rec_time(rec) == T2


def test_control_volume_information_row_format_time_when_no_write_time():
    rec = redo(0x03, [b"\x20\x05" + b"\x00" * 6, value(0xA8, [(0x90, T1)])])
    assert rec_time(rec) == T1


def test_control_index_entry_update_latest_entry_time():
    rec = redo(0x03, [b"\x30\x00\x01\x00" + "a.txt".encode("utf-16-le"), value(84, [(0x10, T1), (0x20, T3)])])
    assert rec_time(rec) == T3


def test_control_insert_of_an_embedded_record_latest_si_time():
    rec = redo(0x01, [b"\x30\x00\x01\x00" + "a.txt".encode("utf-16-le"),
                      value(0x200, [(0x28, T1), (0x30, T2), (0x38, T3), (0x40, T1)])])
    assert rec_time(rec) == T3


def test_f5_e_whole_row_update_of_an_embedded_record_latest_si_time():
    """A two-value UpdateRow of a name row's embedded record: its $SI times (+0x28..+0x40), the latest -- 1.14.0's
    fallback took the first plausible at +0xA0, +0x90, +0x30 (Modified here, not the change time)."""
    rec = redo(0x03, [b"\x30\x00\x01\x00" + "a.txt".encode("utf-16-le"),
                      value(0x320, [(0x28, T1), (0x30, T2), (0x38, T3), (0x40, T1)])])
    assert rec_time(rec) == T3


# ── the public sample ──────────────────────────────────────────────────────────────────────────────────────────────

F5_TIME = "2081-11-18T20:20:59.9829808Z"


@pytest.mark.parametrize("args", [("timeline", "--csv"), ("mlog", "--parse", "--csv", "-")],
                         ids=["timeline", "mlog-parse"])
def test_f5_public_sample_no_row_dated_by_file_content(args):
    rc, out = MC.corpus_run(FOREFST, "step4/wininsiderrefs8gtest2.raw", *args)
    assert F5_TIME not in out, "a row is still dated by the .cfg file's bytes 8-15"
