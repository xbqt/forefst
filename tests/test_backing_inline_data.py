"""A file whose record was split out of its name row can still hold its data inside that record.

The backing's main $DATA is then the *resident* form; the alternative is the extent-bearing form. These tests
build both synthetically and pin the discriminator, the offsets, and the two traps that made this hard to see:
an ADS is a MULTI-instance 0x80 row (so matching any 0x80 row picks the wrong stream), and a truncated or
oversized length must be rejected rather than returning garbage.
"""
import struct

import forefst as F

SI = b"\x01\x00\x00\x80"        # single-instance marker  -> the file's own $DATA
MULTI = b"\x02\x00\x00\x80"     # multi-instance marker   -> an ADS


def _key(marker, attr_type=0x80):
    """Embedded-tree key: 8 bytes of preamble, the instance marker, then the attribute type."""
    return b"\x00" * 8 + marker + bytes([attr_type, 0x00])


def _resident_value(content, declared=None):
    """Resident $DATA: summary_size@0x0C = 0x30, storage_type@0x10 = 0, size@0x20, content@0x3C."""
    v = bytearray(0x3C + len(content))
    struct.pack_into("<I", v, 0x0C, 0x30)
    struct.pack_into("<I", v, 0x10, 0)
    struct.pack_into("<Q", v, 0x20, len(content) if declared is None else declared)
    v[0x3C:0x3C + len(content)] = content
    return bytes(v)


def _extent_value():
    """Extent-bearing stream record: inner header 0x88, summary 0x200 — no inline content."""
    v = bytearray(0x90)
    struct.pack_into("<I", v, 0x00, 0x88)
    struct.pack_into("<I", v, 0x0C, 0x200)
    struct.pack_into("<I", v, 0x10, 0x200)
    return bytes(v)


def _patched_rows(monkeypatch, rows):
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None: rows)


def test_resident_form_returns_the_inline_bytes(monkeypatch):
    _patched_rows(monkeypatch, [(_key(SI), _resident_value(b"hello world"))])
    assert F._backing_inline_data(b"x" * 64) == b"hello world"


def test_extent_bearing_form_returns_none(monkeypatch):
    _patched_rows(monkeypatch, [(_key(SI), _extent_value())])
    assert F._backing_inline_data(b"x" * 64) is None


def test_an_ads_is_not_the_files_data(monkeypatch):
    """A multi-instance 0x80 row is an ADS. Accepting it returns a stream that is not the file's."""
    _patched_rows(monkeypatch, [(_key(MULTI), _resident_value(b"ADS PAYLOAD"))])
    assert F._backing_inline_data(b"x" * 64) is None


def test_the_files_own_data_is_picked_even_when_an_ads_comes_first(monkeypatch):
    _patched_rows(monkeypatch, [(_key(MULTI), _resident_value(b"ADS PAYLOAD")),
                                (_key(SI), _resident_value(b"REAL"))])
    assert F._backing_inline_data(b"x" * 64) == b"REAL"


def test_a_length_running_past_the_record_is_rejected(monkeypatch):
    """Never return short/garbage bytes for an impossible length."""
    _patched_rows(monkeypatch, [(_key(SI), _resident_value(b"abc", declared=4096))])
    assert F._backing_inline_data(b"x" * 64) is None


def test_zero_length_is_empty_content_not_absent_content(monkeypatch):
    """An inline form declaring size 0 is an EMPTY resident stream, not a missing one.

    The distinction is the whole point of the return type: `None` means "not inline — look for extents",
    while `b""` means "inline, and there are no bytes". Returning None here made a 0-byte split-record file
    indistinguishable from an extent-backed one, so it was reported non-resident and `extract` failed with
    "file not found" (772 rows over 11 corpus images; E88). Every caller tests `is not None`, so the falsy
    empty value is safe."""
    _patched_rows(monkeypatch, [(_key(SI), _resident_value(b"", declared=0))])
    result = F._backing_inline_data(b"x" * 64)
    assert result == b""
    assert result is not None


def test_no_data_row_at_all(monkeypatch):
    _patched_rows(monkeypatch, [(_key(SI, attr_type=0xB0), _resident_value(b"stream"))])
    assert F._backing_inline_data(b"x" * 64) is None


def test_a_short_backing_value_is_not_parsed():
    assert F._backing_inline_data(b"\x00" * 8) is None
