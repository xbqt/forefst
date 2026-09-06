"""Below the first container id the volume is not containerised, so identity is the ANSWER.

ReFS container ids begin at 2 (E74), so keys 0 and 1 never appear in the container table. An
address there is already a physical cluster. Counting it as an unmapped-container "miss" made
the reader attach "output may be incomplete — corrupt/truncated container table" to volumes
whose output was complete and correct: three large files on every v3.4 image, plus several
2 TB volumes. The caveat must stay for a GENUINE gap, which is what these pin.

Mutation coverage (with __pycache__ cleared):
    excuse ALL misses          killed by 3 tests
    excuse nothing (revert)    killed by 1 test
    probe moves the counter    NOT killed -- see below

The surviving mutant swaps `_vlcn_mappable(tr, vlcn)` for `tr.tr(vlcn) is not None` inside
`_plausible_vlcn`, which is a CLOSURE defined in `_decode_inline_extents` and cannot be called
from a unit test. That path is covered at corpus level instead: `dataruns` is byte-identical
across the corpus while the spurious container caveat drops to 0 on four volumes. Stated here
rather than left to look like coverage this file does not have.
"""
import forefst as F


class _T(F.Translator):
    """Translator with a hand-built map, bypassing the on-disk constructor."""
    def __init__(self, mapping, shift=15, cpc=1 << 15):
        self.map = mapping
        self.shift = shift
        self.mask = cpc - 1
        self.misses = 0
        self._first_cid = min(mapping) if mapping else None


def test_address_below_the_first_container_is_identity_and_not_a_miss():
    t = _T({2: 0x1000, 3: 0x2000})
    assert t.tr(0x100) == 0x100        # key 0 -> already physical
    assert t.tr((1 << 15) + 7) == (1 << 15) + 7
    assert t.misses == 0


def test_a_genuine_gap_still_counts_as_a_miss():
    t = _T({2: 0x1000, 4: 0x3000})     # container 3 missing from the middle
    assert t.tr(3 << 15) == 3 << 15    # identity fallback
    assert t.misses == 1, "a real unmapped container must still raise the caveat"


def test_an_address_above_the_table_still_counts_as_a_miss():
    t = _T({2: 0x1000})
    t.tr(9 << 15)
    assert t.misses == 1


def test_mapped_addresses_translate_and_do_not_count():
    t = _T({2: 0x1000, 3: 0x2000})
    assert t.tr((2 << 15) + 5) == 0x1000 + 5
    assert t.tr((3 << 15) + 1) == 0x2000 + 1
    assert t.misses == 0


def test_vlcn_mappable_agrees_with_tr_without_moving_the_counter():
    """The probe must never move the caveat counter -- that is what made it fire spuriously."""
    t = _T({2: 0x1000, 4: 0x3000})
    assert F._vlcn_mappable(t, 0x100) is True        # direct-addressed region
    assert F._vlcn_mappable(t, (2 << 15) + 1) is True
    assert F._vlcn_mappable(t, 3 << 15) is False     # genuine gap
    assert t.misses == 0


def test_empty_map_does_not_excuse_anything():
    t = _T({})
    t.tr(0x100)
    assert t.misses == 1
