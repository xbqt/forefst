"""A reparse point's target lives in a REPARSE_DATA_BUFFER, and for a DIRECTORY reparse point that buffer
sits inside the object record's embedded attribute tree rather than in a top-level 0xC0 row.

These tests build the buffers synthetically — no corpus image required — and pin two things the decoder got
wrong before: that a MOUNT_POINT carrying only a SubstituteName must yield that name (it used to fall back to
returning the *tag name* as if it were the target), and that the SYMLINK path buffer starts 4 bytes later
than the MOUNT_POINT one because of the Flags field.
"""
import struct

import forefst as F

SYMLINK = 0xA000000C
MOUNT_POINT = 0xA0000003


def _buf(tag, substitute, printname):
    """Build a REPARSE_DATA_BUFFER: tag, ReparseDataLength, Reserved, then the two name pairs + path buffer."""
    sub = substitute.encode("utf-16-le")
    pr = printname.encode("utf-16-le")
    flags = 4 if tag == SYMLINK else 0          # SYMLINK has a 4-byte Flags field before the path buffer
    path = sub + pr
    body = struct.pack("<HHHH", 0, len(sub), len(sub), len(pr)) + b"\x00" * flags + path
    return struct.pack("<IHH", tag, len(body), 0) + body


def test_symlink_prefers_the_print_name():
    assert F._reparse_buffer_target(_buf(SYMLINK, r"\??\C:\real", r"C:\real")) == r"C:\real"


def test_symlink_falls_back_to_the_substitute_name():
    assert F._reparse_buffer_target(_buf(SYMLINK, r"\??\C:\real", "")) == r"\??\C:\real"


def test_mount_point_prefers_the_print_name():
    assert F._reparse_buffer_target(_buf(MOUNT_POINT, r"\??\C:\tgt", r"C:\tgt")) == r"C:\tgt"


def test_mount_point_with_only_a_substitute_name_returns_it():
    """A junction commonly carries no PrintName. The target must still be the path, never the tag name."""
    out = F._reparse_buffer_target(_buf(MOUNT_POINT, r"\??\C:\tgt", ""))
    assert out == r"\??\C:\tgt"
    assert "IO_REPARSE_TAG" not in out


def test_unknown_tag_degrades_to_the_tag_name_not_a_crash():
    assert F._reparse_buffer_target(struct.pack("<IHH", 0xA0001234, 0, 0)) == "0xA0001234"


def test_truncated_buffer_is_not_an_exception():
    assert F._reparse_buffer_target(b"\x03\x00\x00\xa0") == ""


def test_embedded_lookup_ignores_a_value_that_is_not_an_attribute_tree():
    assert F._embedded_reparse_target(b"\x00" * 8) == ""
    assert F._embedded_reparse_target(b"\xff" * 0x40) == ""
