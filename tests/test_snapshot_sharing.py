"""ReFS stream snapshots are copy-on-write, so a snapshotted file's blocks are split across streams.

A block is duplicated only when it is about to be overwritten; everything not yet modified stays SHARED —
present once on disk, listed in a snapshot's extent table and absent from the current stream's. Reading a
version therefore means resolving each file VCN across the streams. These tests pin that resolution and, in
particular, the direction rule: a PRIOR version may only borrow from snapshots OLDER than itself, because a
newer snapshot can hold content written after it.
"""
import struct

import forefst as F


def _key(sub_id, attr_type=0x80):
    """Embedded-tree key with the attribute type at +0x0C and the sub-stream id at +0x10."""
    return b"\x00" * 12 + struct.pack("<HH", attr_type, 0) + struct.pack("<Q", sub_id)


def _stream(size, extents):
    """Minimal $DATA stream record carrying the snapshot-data descriptor and an extent list."""
    return (size, len(extents) * 4096, extents)


def _patch(monkeypatch, streams):
    """streams: {sub_id: [(file_vcn, vlcn, run), ...]} -> the rows/parse the helper reads.

    Each stream gets a distinct value object so the fake parser can map a value back to its extents; keying
    on call order would be wrong, because the helper filters rows (by `exclude`/`older_than`) before parsing.
    """
    vals = {sub: bytes([i]) + b"\x00" * 0x4F for i, sub in enumerate(streams)}
    rows = [(_key(sub), vals[sub]) for sub in streams]
    back = {vals[sub]: streams[sub] for sub in streams}
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None: rows)
    monkeypatch.setattr(F, "le32", lambda b, o: F.SNAP_DATA_DESC if o == 4 else 0)
    # signature mirrors the real one, which takes an optional translator (E85)
    monkeypatch.setattr(F, "parse_snapshot_data_entry",
                        lambda v, ncl=None, tr=None: _stream(0, back[bytes(v)]))


def test_newest_snapshot_wins_for_the_current_stream(monkeypatch):
    """Assembling the CURRENT stream, a block held by several snapshots comes from the newest."""
    _patch(monkeypatch, {0x1002: [(3, 0xBB, 1)], 0x1001: [(0, 0xAA, 3), (3, 0xCC, 1)]})
    shared = F._snapshot_shared_blocks(b"x" * 0x100, None, 1 << 20)
    assert shared[0] == 0xAA and shared[1] == 0xAB and shared[2] == 0xAC
    assert shared[3] == 0xBB          # 0x1002 is newer than 0x1001, so it wins


def test_a_prior_version_never_borrows_from_a_newer_snapshot(monkeypatch):
    """Recovering v1 must not pull a block written after v1."""
    _patch(monkeypatch, {0x1003: [(0, 0x99, 1)], 0x1002: [(0, 0x88, 1)], 0x1001: [(0, 0x77, 1)]})
    shared = F._snapshot_shared_blocks(b"x" * 0x100, None, 1 << 20, exclude=0x1002, older_than=0x1002)
    assert shared[0] == 0x77          # only 0x1001 is older than 0x1002


def test_the_stream_being_assembled_is_excluded(monkeypatch):
    _patch(monkeypatch, {0x1001: [(0, 0x55, 1)]})
    assert F._snapshot_shared_blocks(b"x" * 0x100, None, 1 << 20, exclude=0x1001) == {}


def test_a_sparse_extent_is_not_offered_as_a_shared_block(monkeypatch):
    """vlcn 0 is a hole, not a location — it must never be handed out as a source cluster."""
    _patch(monkeypatch, {0x1001: [(0, 0, 2), (2, 0x44, 1)]})
    shared = F._snapshot_shared_blocks(b"x" * 0x100, None, 1 << 20)
    assert 0 not in shared and 1 not in shared and shared[2] == 0x44


def test_no_snapshots_means_no_sharing(monkeypatch):
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None: [])
    assert F._snapshot_shared_blocks(b"x" * 0x100, None, 1 << 20) == {}
