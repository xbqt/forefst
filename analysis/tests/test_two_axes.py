"""Record placement and data residency are independent axes (E87).

`_stream_data_form` must read the answer out of the $DATA descriptor and must not be
influenced by where the record sits. These build both descriptor forms synthetically and
pin the four residency answers, including the two that only differ by a witness:
a stream owning no allocation is `snapshot-shared` when a snapshot sub-record exists for the
same stream and `sparse` when none does — without that distinction a fully sparse file is
reported as sharing a snapshot's blocks.
"""
import struct

import forefst as F

SI = b"\x01\x00\x00\x80"
MI = b"\x02\x00\x00\x80"


def _key(marker, sub=None):
    k = b"\x00" * 8 + marker + struct.pack("<HH", 0x0080, 0)
    return k + struct.pack("<I", sub) if sub is not None else k


def _inline_value(content, declared=None):
    v = bytearray(0x3C + len(content))
    struct.pack_into("<I", v, 0x0C, 0x30)                  # summary size
    struct.pack_into("<I", v, 0x10, 0)                     # storage type 0 = inline
    struct.pack_into("<Q", v, 0x20, len(content) if declared is None else declared)
    v[0x3C:0x3C + len(content)] = content
    return bytes(v)


def _extent_value(size, disk_alloc):
    v = bytearray(0x90)
    struct.pack_into("<I", v, 0x00, 0x88)                  # inner header
    struct.pack_into("<I", v, 0x04, 0x00010028)            # descriptor
    struct.pack_into("<I", v, 0x0C, 0x200)                 # summary size (v3.11+)
    struct.pack_into("<Q", v, 0x38, size)
    struct.pack_into("<Q", v, 0x48, disk_alloc)
    return bytes(v)


def _patch(monkeypatch, rows):
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None: rows)


def test_inline_form_is_inline(monkeypatch):
    _patch(monkeypatch, [(_key(SI), _inline_value(b"hello"))])
    assert F._stream_data_form(b"x" * 64) == F.DATA_INLINE


def test_an_empty_inline_form_record_is_still_inline(monkeypatch):
    """A 0-byte file is decided by descriptor form like any other -- no special case."""
    _patch(monkeypatch, [(_key(SI), _inline_value(b"", declared=0))])
    assert F._stream_data_form(b"x" * 64) == F.DATA_INLINE


def test_an_empty_extent_form_record_is_extents(monkeypatch):
    """The other half: 0 bytes in the extent form is `extents`, not `inline`.
    Reading this from the placement flag instead put 1,098 corpus rows on the wrong side."""
    _patch(monkeypatch, [(_key(MI, 0x1000), _extent_value(0, 4096))])
    assert F._stream_data_form(b"x" * 64) == F.DATA_EXTENTS


def test_extent_form_with_allocation_is_extents(monkeypatch):
    _patch(monkeypatch, [(_key(MI, 0x1000), _extent_value(200000, 200704))])
    assert F._stream_data_form(b"x" * 64) == F.DATA_EXTENTS


def test_no_allocation_with_a_snapshot_row_is_snapshot_shared(monkeypatch):
    _patch(monkeypatch, [(_key(MI, 0x1000), _extent_value(5, 0)),
                         (_key(MI, 0x1001), _extent_value(5, 4096))])
    assert F._stream_data_form(b"x" * 64) == F.DATA_SNAPSHOT_SHARED


def test_no_allocation_and_no_snapshot_row_is_sparse(monkeypatch):
    """Same descriptor shape as the snapshot case; only the witness separates them."""
    _patch(monkeypatch, [(_key(MI, 0x1000), _extent_value(1234567891, 0))])
    assert F._stream_data_form(b"x" * 64) == F.DATA_SPARSE


def test_no_data_row_is_unknown(monkeypatch):
    _patch(monkeypatch, [])
    assert F._stream_data_form(b"x" * 64) == F.DATA_UNKNOWN


def test_isresident_is_exactly_inline():
    """The deprecated alias must track the new column, not the placement flag."""
    for form, expected in ((F.DATA_INLINE, True), (F.DATA_EXTENTS, False),
                           (F.DATA_SNAPSHOT_SHARED, False), (F.DATA_SPARSE, False)):
        r = {"data_form": form, "record_embedded": True, "is_resident": True}
        assert (F._data_residency(r) == F.DATA_INLINE) is expected, form


def test_placement_is_not_residency():
    """A split record can hold its bytes inline -- the whole point of E87."""
    r = {"record_embedded": False, "data_form": F.DATA_INLINE}
    assert F._record_placement(r) == "split"
    assert F._data_residency(r) == F.DATA_INLINE
    r2 = {"record_embedded": True, "data_form": F.DATA_EXTENTS}
    assert F._record_placement(r2) == "embedded"
    assert F._data_residency(r2) == F.DATA_EXTENTS


def test_directories_get_blank_axes():
    r = {"is_dir": True, "record_embedded": False, "data_form": F.DATA_EXTENTS}
    assert F._record_placement(r) == ""
    assert F._data_residency(r) == ""
