"""1.11.4 — the extent-decoder ORDER: structural first, the positional walks as fallback.

Through 1.11.3 the contiguous 0xA8 scan answered first wherever it produced any cover, and the structural
decoder was consulted only when it produced none. The scan walks a record's bytes POSITIONALLY, so it can
return a row the $DATA node's INDEX ARRAY does not reference -- dead space inside the node -- or a constant
that merely looks like an entry. The cover guard cannot tell: a wrong single run of the right length covers
the allocation exactly as well as the right one.

Measured over the corpus that was 11 maps wrong, on 5 distinct records:

  * 6 (3 distinct, v3.10) mapped a file to **VLCN 0 -- the volume boot record** -- and returned 43 non-zero
    bytes of `ReFS` signature as file content;
  * 1 (v3.14, 64K SHA-256) was built on **0x000E0080**, the `$DATA` sub-record descriptor constant, and
    returned 505,381 zero bytes for a file whose real content is recoverable;
  * 4 (1 distinct, v3.14) read an **unindexed row** from inside the extent node.

These need the corpus and skip cleanly without it. The property tests below do not.
"""
import glob
import os

import pytest

import forefst as F

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESCRIPTOR_CONSTANT = 0x000E0080          # 917632 -- a $DATA sub-record descriptor, never a cluster address


def _corpus_root():
    """Walk UP for analysis/rawdisk/disks, the same way test_exit_codes.py does.

    Resolving the corpus relative to the test file finds `forefstdev/analysis/...`, which holds the tests
    but no images -- so every corpus test skipped, and a skip reads exactly like a pass that had nothing
    to say. Walking up finds the corpus wherever the checkout sits, and finds nothing in a clone.
    """
    seen = set()
    for start in (os.getcwd(), REPO):
        d = os.path.abspath(start)
        while d not in seen:
            seen.add(d)
            cand = os.path.join(d, "analysis", "rawdisk", "disks")
            if os.path.isdir(cand):
                return cand
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


def _image(name):
    root = _corpus_root()
    if not root:
        pytest.skip("no image corpus here (a clone ships none)")
    hits = glob.glob(os.path.join(root, "**", name), recursive=True)
    if not hits:
        pytest.skip("corpus image not present: " + name)
    return hits[0]


def _all_extents(img, unreadable=None):
    """Yield (info, extent) for every mapped stream. `unreadable` collects directories that would not walk."""
    if unreadable is None:
        unreadable = []
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _c = F.bootstrap(img, None)
    try:
        for oid in list(obj_map):
            try:
                infos = F._analyze_dir_extents(f, ps, cs, tr, obj_map, oid)
            except Exception as exc:
                # A directory we cannot read is a directory whose files we did not check. Recorded, so a
                # corpus that starts failing to walk cannot make these assertions pass by having nothing
                # left to assert on.
                unreadable.append((oid, type(exc).__name__))
                continue
            for info in infos:
                for e in (info.get("extents") or []):
                    yield info, e
    finally:
        f.close()


# ── the property: neither bad address may appear in any map ───────────────────────────────────────
@pytest.mark.parametrize("image", ["win1123h2test.raw", "win1123h2test_testchecksum.raw"])
def test_no_file_maps_to_the_boot_sector(image):
    """VLCN 0 is the boot sector. A file's data never lives there."""
    unreadable = []
    bad = [i.get("name") for i, e in _all_extents(_image(image), unreadable) if e.get("vlcn") == 0]
    assert not bad, f"{len(bad)} file(s) map to VLCN 0, the volume boot record: {bad[:5]}"
    assert not unreadable, f"{len(unreadable)} directory(ies) would not walk: {unreadable[:3]}"


@pytest.mark.parametrize("image", ["win11refs2t64ksha256checksums.raw"])
def test_no_map_is_built_on_the_data_descriptor_constant(image):
    unreadable = []
    bad = [i.get("name") for i, e in _all_extents(_image(image), unreadable)
           if e.get("vlcn") == DESCRIPTOR_CONSTANT]
    assert not bad, (f"{len(bad)} file(s) carry VLCN {DESCRIPTOR_CONSTANT} (0x000E0080), the $DATA "
                     f"sub-record descriptor, as a cluster address: {bad[:5]}")


def test_the_known_zero_filled_file_now_recovers_its_content():
    """`xbpt_victor_tango_152379.bin` returned 505,381 zero bytes through 1.11.3.

    Its real content starts with the generator's own marker, so the right answer is known independently of
    this codebase.
    """
    img = _image("win11refs2t64ksha256checksums.raw")
    for info, _e in _all_extents(img):
        if info.get("name") == "xbpt_victor_tango_152379.bin":
            f, ps, cs, tr, roots, obj_map, vmaj, vmin, _c = F.bootstrap(img, None)
            try:
                content, _meta = F.get_file_content(f, ps, cs, tr, info)
            finally:
                f.close()
            assert content is not None, "the file no longer resolves at all"
            assert content[:10] == b"GFSAREPLAY", \
                f"expected the generator marker, got {content[:10]!r} ({sum(1 for b in content if b)} non-zero)"
            return
    pytest.skip("target file not found on this image")


# ── the ordering itself, without the corpus ───────────────────────────────────────────────────────
def test_the_dispatcher_asks_the_structural_decoder_first():
    """The order is the fix. If a later change reinstates the positional walk first, these records break
    again silently -- the cover guard does not catch it."""
    import inspect
    src = inspect.getsource(F._decode_holder_extents)
    i_struct = src.find("_embedded_data_extents")
    i_index = src.find("_parse_inline_holder_extents")
    i_contig = src.find("_parse_extents_from_type40")
    assert i_struct != -1, "the structural decoder is no longer called from the dispatcher"
    assert i_struct < i_index < i_contig, \
        "order changed: structural must be tried before the positional walks"


def test_both_fallback_decoders_are_still_present():
    """1.11.4 changes the ORDER only. Removing a decoder is C1.5, and belongs in 1.12.0 -- the index array
    is the only decoder that answers on v3.4."""
    import inspect
    src = inspect.getsource(F._decode_holder_extents)
    assert "_parse_inline_holder_extents" in src
    assert "_parse_extents_from_type40" in src


def test_the_dispatcher_still_works_without_a_context():
    """`ctx` is optional: a caller that cannot supply one keeps the pre-1.11.4 behaviour rather than
    failing, so no call site is obliged to change."""
    assert F._decode_holder_extents(b"\x00" * 0x80, 4096, None) == []
