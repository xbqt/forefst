"""E86 — the nested extent node inside an embedded $DATA record.

A large file's extent map is not a flat run array in its $DATA value: the value holds a B+-tree node whose
leaf rows are the extent records, and past one node an index node pointing at a child page. These tests pin
the row/field layout, the leaf-vs-index discriminator, the integrity-stream row size, and — most
importantly — the guards that keep a partial decode from producing bytes.
"""
import struct
import forefst as m


class _AllMapped:
    """Every container id maps."""
    def __contains__(self, _cid):
        return True


def _node(level, rows, tail_pad=0):
    """Build a node: 0x28-byte header, rows laid out in order, trailing 4-byte index array."""
    hdr = bytearray(0x28)
    body = bytearray()
    offs = []
    for r in rows:
        offs.append(0x28 + len(body))
        body += r
    body += b"\0" * tail_pad
    idx = bytearray()
    for o in offs:
        idx += struct.pack("<HH", o, 0)
    node_sz = 0x28 + len(body) + len(idx)
    struct.pack_into("<I", hdr, 0x00, 0x28)
    hdr[0x0C] = level
    # The key-index array is delimited by its START at +0x10 and its END at +0x20, with the row
    # count at +0x14 -- and (end - start) / 4 == count holds on 480 of 480 real nodes measured.
    # This builder used to write only the end and leave +0x10 zero, which no real node does; the
    # reader then had to infer the start by subtracting count*4, and could not tell a damaged
    # header from a good one.
    struct.pack_into("<I", hdr, 0x10, node_sz - len(idx))
    struct.pack_into("<I", hdr, 0x14, len(rows))
    struct.pack_into("<I", hdr, 0x20, node_sz)
    return bytes(hdr + body + idx)


def _leaf_row(vlcn, file_vcn, run, crcs=0, flags=0x50):
    row = bytearray(24 + crcs * 4)
    struct.pack_into("<Q", row, 0x00, vlcn)
    struct.pack_into("<H", row, 0x08, flags)
    struct.pack_into("<H", row, 0x0A, len(row))
    struct.pack_into("<I", row, 0x0C, file_vcn)
    struct.pack_into("<I", row, 0x14, run)
    return bytes(row)


class _Tr:
    """Stands in for the container-table translator: `shift`/`map` are what the mappability test reads
    (it deliberately avoids tr(), whose miss counter feeds the user-facing incompleteness caveat)."""
    shift = 0
    map = _AllMapped()

    def tr(self, v):
        return v


def test_leaf_rows_decode_to_extents():
    node = _node(0, [_leaf_row(0x1000, 0, 64), _leaf_row(0x2000, 64, 16)])
    exts = m._extent_node_map(node, 0, None, 0, 4096, _Tr())
    assert [(e["file_vcn"], e["vlcn"], e["clusters"]) for e in exts] == [(0, 0x1000, 64), (64, 0x2000, 16)]


def test_integrity_row_size_is_24_plus_run_times_4():
    """An integrity stream appends one u32 CRC32-C per cluster; the row size grows with it."""
    node = _node(0, [_leaf_row(0x1000, 0, 15, crcs=15, flags=0xD0)])
    exts = m._extent_node_map(node, 0, None, 0, 4096, _Tr())
    assert len(exts) == 1 and exts[0]["clusters"] == 15


def test_row_with_inconsistent_size_is_rejected():
    """row_size must be 24 or 24+run*4 — anything else is not a run row and must not become an extent."""
    bad = bytearray(_leaf_row(0x1000, 0, 64))
    struct.pack_into("<H", bad, 0x0A, 99)          # neither 24 nor 24+64*4
    node = _node(0, [bytes(bad)])
    assert m._extent_node_map(node, 0, None, 0, 4096, _Tr()) == []


def test_zero_run_and_zero_vlcn_rejected():
    node = _node(0, [_leaf_row(0x1000, 0, 0), _leaf_row(0, 0, 8)])
    assert m._extent_node_map(node, 0, None, 0, 4096, _Tr()) == []


def test_not_a_node_returns_nothing():
    assert m._extent_node_rows(b"\x99" * 0x40, 0) == (None, [])
    assert m._extent_node_rows(b"", 0) == (None, [])
    assert m._extent_node_map(b"\x99" * 0x40, 0, None, 0, 4096, _Tr()) == []


def test_level_byte_selects_leaf_vs_index():
    """level 0 = leaf (rows are extents); non-zero = index (rows are child references)."""
    leaf = _node(0, [_leaf_row(0x1000, 0, 8)])
    assert m._extent_node_rows(leaf, 0)[0] == 0
    idx = _node(1, [_leaf_row(0x1000, 0, 8)])
    assert m._extent_node_rows(idx, 0)[0] == 1
    # an index node whose rows carry no usable 48-byte reference yields nothing, never a bogus extent
    assert m._extent_node_map(idx, 0, None, 0, 4096, _Tr()) == []


def test_recursion_is_bounded():
    """depth<=0 stops the descent, so a malformed/cyclic tree cannot spin."""
    idx = _node(1, [_leaf_row(0x1000, 0, 8)])
    assert m._extent_node_map(idx, 0, None, 0, 4096, _Tr(), depth=0) == []


def test_embedded_data_extents_needs_context():
    assert m._embedded_data_extents(b"\x00" * 0x200, 4096, None) == []
    assert m._embedded_data_extents(b"", 4096, (None, 0, 4096, _Tr())) == []


def test_a_header_whose_index_array_disagrees_with_the_row_count_is_rejected():
    """(end - start) / 4 must equal the row count. A node claiming more rows than its index
    array can hold is damaged, and decoding it would emit extents built from arbitrary bytes."""
    good = _node(0, [_leaf_row(0x1000, 0, 8), _leaf_row(0x2000, 8, 8)])
    assert m._extent_node_rows(good, 0)[0] == 0
    bad = bytearray(good)
    struct.pack_into("<I", bad, 0x14, 7)          # claim 7 rows; the array holds 2
    assert m._extent_node_rows(bytes(bad), 0) == (None, [])


def test_a_header_with_no_index_start_is_rejected():
    """+0x10 is a real field. A node with it zeroed is not a node this reader will decode."""
    good = _node(0, [_leaf_row(0x1000, 0, 8)])
    bad = bytearray(good)
    struct.pack_into("<I", bad, 0x10, 0)
    assert m._extent_node_rows(bytes(bad), 0) == (None, [])
