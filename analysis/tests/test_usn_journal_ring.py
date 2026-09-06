"""`$J` is a ring, and a record's USN IS its byte offset in that ring.

`usn % alloc == offset` holds on every genuine record: measured 217,892/217,892 on `winsider`,
9,371/9,378 on `win11refstestmftecmd`, 33,379/33,381 on `win11refs8gtestmove_aftermove` — the
few failures are zero-filled slack that happens to parse as a record. The invariant is reported,
never used to drop records: a torn or overwritten record is evidence.

Buffer order is only time order until the ring wraps. `winsider` IS wrapped (one descending step
in 217,892 records — the first wrapped journal observed on this corpus), so the listing is sorted
by USN to restore chronology.
"""
import struct

import forefst as F


def _rec(usn, name="a", reclen=None):
    """A minimal USN_RECORD_V3: 128-bit file ids push Usn to +0x28."""
    nm = name.encode("utf-16-le")
    body = 0x4C + len(nm)
    rl = reclen if reclen is not None else (body + 7) & ~7
    r = bytearray(rl)
    struct.pack_into("<I", r, 0x00, rl)
    struct.pack_into("<H", r, 0x04, 3)          # major version 3
    struct.pack_into("<Q", r, 0x28, usn)
    struct.pack_into("<H", r, 0x48, len(nm))    # name length
    struct.pack_into("<H", r, 0x4A, 0x4C)       # name offset
    r[0x4C:0x4C + len(nm)] = nm
    return bytes(r)


def _journal(records, alloc):
    """Lay records at the offsets their USNs imply, so the invariant holds by construction."""
    buf = bytearray(alloc)
    for usn, name in records:
        r = _rec(usn, name)
        buf[usn:usn + len(r)] = r
    return bytes(buf)


def test_usn_is_the_record_offset():
    alloc = 0x10000
    data = _journal([(0x100, "a"), (0x200, "b"), (0x300, "c")], alloc)
    recs = F.parse_usn_records(data, alloc=alloc)
    assert [r.usn for r in recs] == [0x100, 0x200, 0x300]
    assert all(r.usn % alloc == r.offset for r in recs)


def test_a_record_whose_usn_is_not_its_offset_is_kept_not_dropped():
    """Violations are reported. Dropping them would discard a torn or overwritten record."""
    alloc = 0x10000
    buf = bytearray(alloc)
    r = _rec(0x999)                      # USN disagrees with where it is placed
    buf[0x100:0x100 + len(r)] = r
    recs = F.parse_usn_records(bytes(buf), alloc=alloc)
    assert len(recs) == 1
    assert recs[0].usn == 0x999 and recs[0].offset == 0x100


def test_zero_filled_slack_is_not_reported_as_torn():
    """An unwrapped journal is mostly zeros; that is normal and must not raise a caveat."""
    F._SKIP_NOTES.clear()
    data = _journal([(0x100, "a")], 0x8000)
    F.parse_usn_records(data, alloc=0x8000)
    assert not any(k[0] == "USN journal" for k in F._SKIP_NOTES), F._SKIP_NOTES


def test_non_zero_unparseable_bytes_are_reported():
    F._SKIP_NOTES.clear()
    buf = bytearray(_journal([(0x100, "a")], 0x8000))
    buf[0x2000:0x2040] = b"\xde\xad\xbe\xef" * 16      # non-zero, parses as no record
    F.parse_usn_records(bytes(buf), alloc=0x8000)
    assert any(k[0] == "USN journal" for k in F._SKIP_NOTES)


def test_alloc_omitted_means_no_invariant_check():
    """Existing call sites pass no allocation and must behave exactly as before."""
    F._SKIP_NOTES.clear()
    buf = bytearray(0x8000)
    r = _rec(0x999)
    buf[0x100:0x100 + len(r)] = r
    recs = F.parse_usn_records(bytes(buf))
    assert len(recs) == 1
    assert not any("not their journal offset" in str(k) for k in F._SKIP_NOTES)
