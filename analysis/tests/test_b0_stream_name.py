"""The 0xB0 stream name must be read from the right offset, in BOTH on-disk key forms.

The name sits at key+0x10 when the v3.7+ instance marker is present, and at key+0x0C on v3.4,
which has no marker. Reading the marker form at +0x14 silently chops the first two characters
off every name ("beforemod" -> "foremod") and still returns a plausible-looking string, so the
damage is invisible unless the test names are chosen to expose it. Every name below is picked
so that a 2-character slip changes it into something that still looks like a name.

Mutation coverage (verified, with __pycache__ cleared -- `0x10`->`0x14` is the same byte
length, so a stale .pyc silently hides the mutant and the suite appears to pass):

    v3.7 branch  0x10 -> 0x14   killed by 3 tests
    v3.4 branch  0x0C -> 0x10   killed by 1 test
    type check   0xB0 -> 0x80   killed by 4 tests
    marker set widened          killed by test_a_key_with_the_wrong_marker_is_rejected

Every test here except `test_TESTDATA_*` is sensitive to at least one of those.
"""
import struct

import forefst as F

B0_MARKER = b"\x02\x00\x00\x80"      # multi-instance
SI_MARKER = b"\x01\x00\x00\x80"      # single-instance


def _key_v37(name, marker=B0_MARKER):
    """v3.7+: [u32 value_len][u32][marker][u16 0x00B0][u16 0x0005][name UTF-16LE]"""
    return (struct.pack("<II", 0x64, 0) + marker + struct.pack("<HH", 0x00B0, 0x0005)
            + name.encode("utf-16-le"))


def _key_v34(name):
    """v3.4: no marker — type u32 at +0x08, name from +0x0C."""
    return struct.pack("<II", 0x64, 0) + struct.pack("<I", 0x000000B0) + name.encode("utf-16-le")


def test_v37_marker_form_name_is_complete():
    for name in ("beforemod", "backup 2", "hidden_3867", "sweep", "st2"):
        assert F._b0_stream_name(_key_v37(name)) == name


def test_v34_markerless_form_name_is_complete():
    for name in ("beforemod", "hidden_3867", "sweep"):
        assert F._b0_stream_name(_key_v34(name)) == name


def test_TESTDATA_a_two_character_slip_would_be_caught():
    """NOT a test of the code — a guard on the test DATA.

    It asserts the names above actually change under a 2-character slip, so the code tests
    can detect one. It is insensitive to every mutation of `_b0_name_offset` by design, and
    is named so that nobody mistakes its passing for coverage.
    """
    for name in ("beforemod", "backup 2", "hidden_3867"):
        assert name[2:] != name and len(name) > 3


def test_last_two_characters_survive():
    """A name whose final two characters are distinctive — catches an end-truncation too."""
    for name in ("streamXZ", "ads_qq", "payload_ZZ"):
        got = F._b0_stream_name(_key_v37(name))
        assert got == name, got
        assert got.endswith(name[-2:])


def test_single_instance_marker_is_also_accepted():
    assert F._b0_stream_name(_key_v37("beforemod", SI_MARKER)) == "beforemod"


def test_a_key_with_the_wrong_marker_is_rejected():
    """The marker set must stay closed. A key carrying neither instance marker is not a 0xB0
    attribute key, and widening the accepted set would make junk decode as a stream name --
    a mutation that survived every other test here until this one was added."""
    bad = struct.pack("<II", 0x64, 0) + b"\x00\x00\x00\x00" + struct.pack("<HH", 0x00B0, 0x0005)
    assert F._b0_stream_name(bad + "ghost".encode("utf-16-le")) == ""


def test_not_a_b0_key_returns_empty():
    notb0 = struct.pack("<II", 0x64, 0) + B0_MARKER + struct.pack("<HH", 0x0080, 0x0005)
    assert F._b0_stream_name(notb0 + "x".encode("utf-16-le")) == ""
