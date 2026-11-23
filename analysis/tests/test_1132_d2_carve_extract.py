"""Wave D step D2 (1.14.0): carve and extract -- the nodes the RED files of the items do not hold.

Plan: `analysis/reports/v1.13.2/fixes/WAVED_PLAN.md` D2; `fixes/D2_NOTES.md`. The RED nodes of B5, B6 (N113, N130,
N192, N193), N127 and N128 are in `test_1132_red_b2_carve.py`; these nodes cover the items with no RED until now, and
the rules D2 settled.

What each group asserts
-----------------------
N165     a deleted split file whose data stayed inline in its type-0x40 backing, and the backing survives in slack:
         the entry holds that content (graded and written), not "metadata only".
WC-3     decision 48: an entry whose file is live (renamed, same file with another creation time, still present) gets
         no carve from its extent map -- the map's clusters may hold the live file's current content.
plan     B6: one predicate -- an all-unwritten map is refused in the verdict as in the carve, and says why; a cluster
         past the volume is not read.

Volumes: the synthetic builders of `test_1132_red_b2_deleted.py` (pages with live and slack rows) and of
`test_1132_red_b2_carve.py` (planted clusters and remnants); corpus images READ-ONLY, skipped when absent.
"""
import errno
import json
import os
import struct
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21: internal names)
import test_1132_red_b2_deleted as D                     # noqa: E402  (DirVol, rows, the runners)
import test_1132_red_b2_carve as C                       # noqa: E402  (Syn, remnants, matchers)

_T, _S = D._T, D._S
_row, _name_key, _file_value = D._row, D._name_key, D._file_value
_fx = D._fx


def _vol(tmp_path, dirs):
    v = D.DirVol()
    v.objects = v.tree(dirs)
    return v.write(str(tmp_path / "target.raw"))


def _t40_key(fid, home):
    """The 24-byte key of a type-0x40 backing row: type 0x40 @0, the file id @0x08, the home directory @0x10."""
    return struct.pack("<HHIQQ", 0x40, 0, 0, fid, home)


def _inline_backing(size, content, ct):
    """A type-0x40 backing value whose $DATA stayed INLINE (E82): the $SI head (times @0x28, attributes @0x48, size
    @0x58, allocation @0x60), then an embedded node at +0xA8 holding one single-instance $DATA row (key marker
    0x80000001, type 0x80) in the resident form: summary size 0x30 @+0x0C, flags 0 @+0x10, byte count @+0x20, the bytes
    @+0x3C -- the layout `_backing_inline_data` reads."""
    dv = bytearray(0x3C + len(content))
    struct.pack_into("<II", dv, 0x0C, 0x30, 0)
    struct.pack_into("<Q", dv, 0x20, size)
    dv[0x3C:] = content
    dk = struct.pack("<QIBB", 0, 0x80000001, 0x80, 0) + b"\0" * 2
    sub = _row(dk, bytes(dv))
    v = bytearray(0xA8 + 0x28 + len(sub) + 4)            # the row array ends the value, as on the volume
    base, rows_at = 0xA8, 0x28
    struct.pack_into("<I", v, 0, base)
    struct.pack_into("<QQQQ", v, 0x28, ct, ct, ct, ct)
    struct.pack_into("<I", v, 0x48, 0x20)
    struct.pack_into("<QQ", v, 0x58, size, (size + 7) & ~7)
    v[base + rows_at:base + rows_at + len(sub)] = sub
    arr_lo = rows_at + len(sub)
    struct.pack_into("<III", v, base + 0x10, arr_lo, 1, 0)
    struct.pack_into("<I", v, base + 0x20, arr_lo + 4)
    struct.pack_into("<HH", v, base + arr_lo, rows_at, 0xFFFF)
    _fx(F._backing_inline_data(bytes(v)) == content == F._backing_inline_data(bytes(v), salvage=True),
        "the planted backing does not read as inline data")
    return bytes(v)


_CONTENT = b"inline in the backing record: N165 " * 2 + b"0123456789abcdefghijklmnopqrstuvwxyzABCDEF"


def _n165_volume(tmp_path):
    """/d holds, in its page's free space, a deleted split file's name row (gone.txt, FileRef 0x761:0x9, size 112)
    and its type-0x40 backing, whose $DATA is inline."""
    _fx(len(_CONTENT) == 112, "content length")
    name = bytearray(_file_value(9, 0x761, _T + 3 * _S))
    struct.pack_into("<Q", name, 0x38, len(_CONTENT))
    return _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("keep.txt"), _file_value(5, 0x761, _T))],
                                   "slack": [_row(_name_key("gone.txt"), bytes(name)),
                                             _row(_t40_key(9, 0x761),
                                                  _inline_backing(len(_CONTENT), _CONTENT, _T + 3 * _S))]}})


def test_n165_split_file_inline_in_a_slack_backing_is_graded_by_its_content(tmp_path):
    """N165: the entry's Recoverability says the content is inline (in the backing), not 'metadata only', and the CSV
    Reliability is not NONE."""
    path = _n165_volume(tmp_path)
    rc, out, err, rows = D._syn_csv(path, "deleted")
    r = [x for x in rows if x["FileName"] == "gone.txt"]
    _fx(r, "gone.txt is not listed" + D._ctx(rc, out, err))
    assert not r[0]["Recoverability"].startswith("metadata only"), r[0]
    assert "inline" in r[0]["Recoverability"] and r[0]["Reliability"] != "NONE", r[0]


def test_n165_export_writes_the_backings_inline_content(tmp_path):
    """N165: `export deleted` writes content/gone.txt with the backing's 112 bytes, and the manifest names the backing
    as the source of those bytes."""
    path = _n165_volume(tmp_path)
    out_dir = str(tmp_path / "exp")
    rc, out, err = D._syn(path, "export", "deleted", out_dir)
    p = os.path.join(out_dir, "content", "gone.txt")
    assert os.path.isfile(p), "no content/gone.txt" + D._ctx(rc, out, err)
    with open(p, "rb") as fh:
        assert fh.read() == _CONTENT
    with open(os.path.join(out_dir, "recovery_manifest.json")) as fh:
        man = jdoc(json.load(fh), F._DELETED_MANIFEST_KEYS)                              # K21: internal names
    rec = [m for m in man["Records"] if m["name"] == "gone.txt"]                     # K21 (acceptance 1.14.0)
    assert rec and rec[0]["recoverable"] == "recoverable_inline" and "backing" in rec[0]["verdict"], rec


# ═══ WC-3: no carve of a live file's map ═════════════════════════════════════════════════════════════════════

def _live_map_volume(tmp_path, ct):
    """/d holds a.bin live (a split row, creation time `ct`), and in its page's free space an embedded row a.bin with
    the same creation time whose 0x1000 holder maps 3 clusters: a STILL PRESENT entry with an extent map."""
    hv = C.holder_value(3 * C.CS, 3 * C.CS, [C.ext_row(C.V(10), 0, 3, C.W)])
    old = C.long_row([(C.key80(0x1000), hv)], size=3 * C.CS, alloc=3 * C.CS)
    return _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("a.bin"), _file_value(5, 0x761, ct))],
                                   "slack": [_row(_name_key("a.bin"), old)]}})


def test_wc3_still_present_entry_with_an_extent_map_is_not_carved(tmp_path):
    """WC-3 (decision 48): the STILL PRESENT entry's verdict says its map is not carved because the file is live, and
    `export deleted --carve` writes no carve for it and says why in the manifest (no_carve_reason)."""
    path = _live_map_volume(tmp_path, C.FT)
    out_dir = str(tmp_path / "exp")
    rc, out, err = D._syn(path, "export", "deleted", "--carve", out_dir, "-v")
    blk = [l for l in out.splitlines() if l.strip().startswith("a.bin")]
    _fx(blk, "a.bin is not listed as STILL PRESENT" + D._ctx(rc, out, err))
    assert "not carved: the same file is live" in blk[0], blk
    with open(os.path.join(out_dir, "recovery_manifest.json")) as fh:
        rec = [m for m in jdoc(json.load(fh), F._DELETED_MANIFEST_KEYS)["records"] if m["name"] == "a.bin"]            # K21 (acceptance 1.14.0)
    assert rec and rec[0]["recoverable"] == "live_file_map" and not rec[0]["ContentFile"], rec
    assert "live" in (rec[0]["no_carve_reason"] or ""), rec
    assert not os.path.exists(os.path.join(out_dir, "content", "a.bin.carved"))


def test_wc3_control_a_deleted_entry_with_the_same_map_is_not_held_back(tmp_path):
    """Control: with another creation time and no live file of that identity (the row records none: an embedded row
    whose page owner + ordinal name no live file), the entry is not a live file's: its map is graded by the plan."""
    path = _live_map_volume(tmp_path, _T)            # the live a.bin has another creation time
    out_dir = str(tmp_path / "exp")
    rc, out, err = D._syn(path, "export", "deleted", "--carve", out_dir)
    with open(os.path.join(out_dir, "recovery_manifest.json")) as fh:
        rec = [m for m in jdoc(json.load(fh), F._DELETED_MANIFEST_KEYS)["records"] if m["name"] == "a.bin"]            # K21 (acceptance 1.14.0)
    _fx(rec and rec[0]["Status"] not in ("still present", "renamed", "same file, other creation time"),
        "the control entry is a live file's: %r" % (rec,))
    # the synthetic Container Table does not map the planted VLCN, so the plan refuses it for THAT reason: what the
    # control shows is that the live-file rule did not apply
    assert rec[0]["recoverable"] in ("extent_backed", "map_not_carveable"), rec
    assert "live" not in (rec[0]["no_carve_reason"] or "") and "live" not in rec[0]["verdict"], rec


# ═══ the carve plan: one predicate ═══════════════════════════════════════════════════════════════════════════

def test_b6_all_unwritten_map_is_refused_in_the_view_too(syn_c):
    """B6: a map whose every run is marked unwritten is no carve candidate in the VIEW (1.13.1 graded it 'metadata +
    carve' and the export then refused it): the verdict says no carve is made and why; Reliability NONE."""
    s = syn_c
    hv = C.holder_value(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(20), 0, 2, C.NW)])
    e = C.entry("unw.bin", C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS))
    r = s.deleted_view([e])
    row = [x for x in r.rows if x.get("FileName") == "unw.bin"]
    _fx(row, "unw.bin is not listed" + r.ctx())
    assert row[0]["Reliability"] == "NONE", row[0]
    assert "no carve is made" in row[0]["Recoverability"] and "unwritten" in row[0]["Recoverability"], row[0]


def test_b6_all_unwritten_refusal_still_discloses_its_runs(syn_c):
    """B6 keeps 1.13.1's disclosure of a refused all-unwritten map: refused_all_unwritten, its runs and the bytes the
    clusters hold now, in the manifest."""
    s = syn_c
    s.put(20, b"F" * C.CS)
    hv = C.holder_value(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(20), 0, 2, C.NW)])
    e = C.entry("unw.bin", C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS))
    r = s.export_deleted([e])
    rec = r.records.get("unw.bin", [{}])[0]
    assert rec.get("refused_all_unwritten") is True and rec.get("unwritten_runs") == [[0, 2]], rec
    assert rec.get("unwritten_nonzero_on_disk_bytes") == C.CS and not rec.get("content_file"), rec
    assert "unwritten" in (rec.get("no_carve_reason") or ""), rec


@pytest.fixture
def syn_c(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "volume_clusters", lambda f, ps, cs: C.NCL, raising=False)
    monkeypatch.setattr(F, "_volume_ncl", lambda f, ps, cs: C.NCL, raising=False)
    return C.Syn(tmp_path)


# ═══ N217: inline extent nodes by their key index; an unflagged VLCN-0 row is malformed ══════════════════════

def _indexed_holder(stream_size, disk_alloc, rows, superseded=None):
    """A 0x10028 holder whose extent node at ihdr has a VALID header (0x28 @0, the key index from +0x10 to +0x20,
    the row count @0x14): `superseded` (a row) is placed in the first slot at +0x28 OUTSIDE the index -- the shape the
    critic measured on 22 of 180 slack nodes -- and `rows` follow it, each named by the index in order."""
    ihdr = 0x88
    v = bytearray(ihdr + 0x28)
    struct.pack_into("<I", v, 0, ihdr)
    struct.pack_into("<I", v, 4, F.SNAP_DATA_DESC)
    struct.pack_into("<Q", v, 0x38, stream_size)
    struct.pack_into("<Q", v, 0x48, disk_alloc)
    body, offs = bytearray(), []
    if superseded is not None:
        body += superseded
    for r in rows:
        offs.append(0x28 + len(body))
        body += r
    idx_lo = 0x28 + len(body)
    struct.pack_into("<I", v, ihdr, 0x28)
    struct.pack_into("<I", v, ihdr + 0x10, idx_lo)
    struct.pack_into("<I", v, ihdr + 0x14, len(rows))
    struct.pack_into("<I", v, ihdr + 0x20, idx_lo + 4 * len(rows))
    v += body
    for o in offs:
        v += struct.pack("<HH", o, 0)
    _fx(F._extent_node_header(bytes(v), ihdr)[2] is None, "the planted node header does not validate")
    return bytes(v)


def test_n217a_holder_rows_are_read_through_the_key_index():
    """N217 (a): a node whose first slot (+0x28) holds a superseded row outside the key index gives the indexed rows
    -- VCN 0 and VCN 1 -- not the superseded row, and not with the last indexed row dropped."""
    sup = C.ext_row(C.V(40), 0, 1, C.W)                           # superseded: VCN 0 at cluster 40
    hv = _indexed_holder(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1, C.W), C.ext_row(C.V(11), 1, 1, C.W)], sup)
    got = F._decode_inline_extents(hv, 1 << 20, tr=C._tr())
    assert got == [(0, C.V(10), 1), (1, C.V(11), 1)], got


def test_n217a_carve_plan_takes_the_indexed_rows(syn_c):
    """N217 (a) at the carve: the remnant's carve reads the indexed clusters (A, B), never the superseded slot's (S)."""
    s = syn_c
    s.put(10, b"A" * C.CS)
    s.put(11, b"B" * C.CS)
    s.put(40, b"S" * C.CS)
    sup = C.ext_row(C.V(40), 0, 1, C.W)
    hv = _indexed_holder(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1, C.W), C.ext_row(C.V(11), 1, 1, C.W)], sup)
    e = C.entry("idx.bin", C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS))
    r = s.export_deleted([e])
    assert r.files.get("idx.bin.carved") == b"A" * C.CS + b"B" * C.CS, r.ctx()


def test_n217b_unflagged_vlcn0_row_stops_the_decode_with_its_reason():
    """N217 (b): a row at VLCN 0 without the sparse-hole flag (E98) is malformed -- not zero-filled as a hole: the decode
    stops there and says why."""
    hv = C.holder_value(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1, C.W), C.ext_row(0, 1, 1, C.W)])
    stop = []
    got = F._decode_inline_extents(hv, 1 << 20, tr=C._tr(), stop=stop)
    assert got == [(0, C.V(10), 1)] and stop and "VLCN 0 without the sparse-hole flag" in stop[0], (got, stop)


def test_n217b_carve_refuses_a_map_with_an_unflagged_vlcn0_row(syn_c):
    """N217 (b), the settlement: in a carve the malformed row refuses the map, with the reason (no zero-filled run)."""
    s = syn_c
    s.put(10, b"A" * C.CS)
    hv = C.holder_value(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1, C.W), C.ext_row(0, 1, 1, C.W)])
    e = C.entry("vlcn0.bin", C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS))
    r = s.export_deleted([e])
    rec = r.records.get("vlcn0.bin", [{}])[0]
    assert rec.get("recoverable") == "map_not_carveable" and not rec.get("content_file"), rec
    assert "malformed" in (rec.get("no_carve_reason") or "") and "malformed" in rec.get("verdict", ""), rec


def test_n217b_control_a_flagged_hole_is_a_hole():
    """Control: the same row WITH the hole flag (0x20) is a sparse hole -- kept, VLCN 0, no stop."""
    hv = C.holder_value(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1, C.W), C.ext_row(1, 1, 1, C.HOLE)])
    stop = []
    assert F._decode_inline_extents(hv, 1 << 20, tr=C._tr(), stop=stop) == [(0, C.V(10), 1), (1, 0, 1)] and not stop


# ═══ B7: the holder-index cover is bounded by its node header and its rows' declared sizes ═══════════════════

def test_b7_tag_pointing_into_a_row_is_not_a_row():
    """B7 / N130: an index tag that points 8 bytes into a real row reads a flags word as a VLCN and a zero size word --
    not a legal row (24, or 24 + 4 x run): it is not taken, so a coincidental 1 + 40 = 41 cover is not accepted."""
    r1 = C.ext_row(C.V(10), 0, 1, C.W)
    r2 = C.ext_row(C.V(11), 40, 1, C.W) + b"\0" * 4 + struct.pack("<I", 40)
    vd, node, offs = C.multilevel_row([r1, r2], 41, 41 * C.CS)
    vd, node, _o = C.multilevel_row([r1, r2], 41, 41 * C.CS, index=[offs[0], offs[1] + 8])
    assert F._parse_inline_holder_extents(vd, C.CS, C._tr()) == []


def test_b7_valid_node_header_bounds_the_rows():
    """B7: when the holder's node header validates, only the rows its key index names count -- a planted row that a
    0xffff-tag scan would also find (outside the index) does not join the cover."""
    vd, node, offs = C.multilevel_row([C.ext_row(C.V(10), 0, 1, C.W), C.ext_row(C.V(11), 1, 1, C.W)], 2, 2 * C.CS)
    vd = bytearray(vd)
    idx = node + 0xC0                              # the node's own key index: names row 0 only
    struct.pack_into("<I", vd, node, 0x28)
    struct.pack_into("<I", vd, node + 0x10, idx - node)
    struct.pack_into("<I", vd, node + 0x14, 1)
    struct.pack_into("<I", vd, node + 0x20, idx - node + 4)
    struct.pack_into("<HH", vd, idx, offs[0], 0)
    _fx(F._extent_node_header(bytes(vd), node)[2] is None, "the planted header does not validate")
    # by the header, one row of 1 cluster: no cover of the 2-cluster allocation -> nothing
    assert F._parse_inline_holder_extents(bytes(vd), C.CS, C._tr()) == []


def test_b7_control_tag_scan_still_reads_a_node_without_a_header():
    """Control: a holder node without a valid header is read by its 0xffff tags, as before (the v3.4 form)."""
    vd, _n, _o = C.multilevel_row([C.ext_row(C.V(10), 0, 1, C.W), C.ext_row(C.V(11), 1, 1, C.W)], 2, 2 * C.CS)
    got = F._parse_inline_holder_extents(vd, C.CS, C._tr())
    assert [(x["file_vcn"], x["vlcn"], x["clusters"]) for x in got] == [(0, C.V(10), 1), (1, C.V(11), 1)], got


# ═══ extract: N380, N390, N208, B12, N201 (the synthetic `extract` harness) ═══════════════════════════════════

_NO_SEEK = ('if spec.get("no_seek_data"):\n'
            '    for _n in ("SEEK_DATA", "SEEK_HOLE"):\n'
            '        if hasattr(os, _n):\n'
            '            delattr(os, _n)\n')


class SynX(C.Syn):
    """The carve module's harness, with one option: `no_seek_data` removes os.SEEK_DATA / SEEK_HOLE in the tool's
    process (decision 23's RED state: a host that cannot answer the hole query)."""

    def run(self, mode, args, fsize=None, **spec):
        real = C._DRIVER
        C._DRIVER = real.replace("import forefst as F\n", "import forefst as F\n" + _NO_SEEK, 1)
        try:
            return C.Syn.run(self, mode, args, fsize=fsize, **spec)
        finally:
            C._DRIVER = real


@pytest.fixture
def synx(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "volume_clusters", lambda f, ps, cs: C.NCL, raising=False)
    monkeypatch.setattr(F, "_volume_ncl", lambda f, ps, cs: C.NCL, raising=False)
    return SynX(tmp_path)


def _target(exts, size, attrs=0x20, **kw):
    t = {"name": "x.bin", "storage": "non-resident", "file_size": size, "file_attrs": attrs, "raw_value": b"",
         "ads": [], "extents": exts}
    t.update(kw)
    return t


def test_n380_extract_unreadable_cluster_is_a_recorded_skip(synx):
    """N380: an extent whose PLCN gives an offset past any file offset (VLCN bit 60) is a recorded skip: exit 2 (not
    1), the output ends at the first byte not read, and the warning says which cluster."""
    synx.put(10, b"W" * C.CS)
    exts = [C._xt(10, 0, 1, C.W), dict(C._xt(20, 1, 1, C.W), plcn=1 << 60)]
    r = synx.extract(_target(exts, 2 * C.CS))
    assert r.rc == 2, r.ctx()
    assert r.data == b"W" * C.CS, r.ctx()
    assert "could not be read" in r.err and "file offset %d" % C.CS in r.err, r.ctx()


def test_n390_extract_of_an_index_node_holder_exits_2_with_the_reason(synx):
    """N390: an embedded record whose holder's extent node is an INDEX node (its runs in child pages): exit 2 with the
    reason, nothing written -- not exit 1, and no advice to use a command that does not decode it either."""
    hv = bytearray(_indexed_holder(3 * C.CS, 3 * C.CS, [C.ext_row(C.V(10), 0, 3, C.W)]))
    hv[0x88 + 0x0C] = 1                                                        # level 1: an index node
    vd = C.long_row([(C.key80(0x1000), bytes(hv))], size=3 * C.CS, alloc=3 * C.CS)
    r = synx.extract(_target([], 3 * C.CS, storage="resident", extent_backed=True, raw_value=vd))
    assert r.rc == 2 and r.data is None, r.ctx()
    assert "index node" in r.err and "use `dataruns`" not in r.err, r.ctx()


def test_n208_extract_on_a_host_without_seek_data_exits_2(synx):
    """N208 (decision 23): the host cannot answer the hole query -> the neutral sentence, an 'undeterminable'
    sidecar, exit 2 (1.13.1: exit 0 with a warning)."""
    synx.put(10, b"W" * C.CS)
    r = synx.extract(_target([C._xt(10, 0, 1, C.W)], C.CS), extra=[])
    _fx(r.rc in (0, 2), r.ctx())
    rr = synx.run("extract", ["d/x.bin", "-o", os.path.join(synx.dir, "nd.bin")],
                  target=_target([C._xt(10, 0, 1, C.W)], C.CS), no_seek_data=True)
    rc, so, se = rr
    assert rc == 2, se
    assert "could not check whether these bytes come from holes in the image file" in se, se
    with open(os.path.join(synx.dir, "nd.bin.holes.json")) as fh:
        assert json.load(fh)["Status"] == "undeterminable"             # K21 (1.14.0)


def test_n208_refuse_holes_refuses_when_holes_cannot_be_checked(synx):
    synx.put(10, b"W" * C.CS)
    o = os.path.join(synx.dir, "nr.bin")
    rc, so, se = synx.run("extract", ["d/x.bin", "-o", o, "--refuse-holes"], target=_target([C._xt(10, 0, 1, C.W)], C.CS),
                          no_seek_data=True)
    assert rc == 2 and not os.path.exists(o), se


def test_n208_inline_holder_branch_honours_the_unchecked_state(synx):
    """N208's widening: the inline-holder branch (an embedded record's extent map) -- 1.13.1 recorded the unchecked
    state there and exited 0 with no word."""
    synx.put(10, b"W" * C.CS)
    hv = C.holder_value(C.CS, C.CS, [C.ext_row(C.V(10), 0, 1, C.W)])
    vd = C.long_row([(C.key80(0x1000), hv)], size=C.CS, alloc=C.CS)
    rc, so, se = synx.run("extract", ["d/x.bin", "-o", os.path.join(synx.dir, "ih.bin")],
                          target=_target([], C.CS, storage="resident", extent_backed=True, raw_value=vd),
                          no_seek_data=True)
    assert rc == 2 and "could not check whether these bytes come from holes" in se, se


def test_n208_control_a_host_with_seek_data_exits_0(synx):
    synx.put(10, b"W" * C.CS)
    r = synx.extract(_target([C._xt(10, 0, 1, C.W)], C.CS))
    assert r.rc == 0 and r.data == b"W" * C.CS, r.ctx()


def test_b12_clean_extract_writes_a_none_sidecar(synx):
    """B12: `extract -o` of a file checked and clean writes its sidecar with status "none" (no hole byte), so the
    absence of a sidecar never has to be read as either state."""
    synx.put(10, b"W" * C.CS)
    r = synx.extract(_target([C._xt(10, 0, 1, C.W)], C.CS))
    assert r.rc == 0 and r.sidecar and r.sidecar["Status"] == "none" and r.sidecar["HoleBytes"] == 0, r.ctx()


def test_n201_efs_extract_says_the_ciphertext_is_cut_at_the_logical_size(synx):
    """N201: an EFS-encrypted 100-byte file in a 4 KiB cluster: the warning says the bytes are ciphertext cut at the
    logical size, that the ciphertext goes on to the allocation's end, and that 100 is not a multiple of the AES
    block -- not that they decrypt with the key."""
    synx.put(10, os.urandom(C.CS))
    r = synx.extract(_target([C._xt(10, 0, 1, C.W)], 100, attrs=0x4020))
    assert r.data is not None and len(r.data) == 100, r.ctx()
    assert "cut at the logical size (100 B)" in r.err and "not a multiple of the 16-byte AES block" in r.err, r.err
    assert "4096 B" in r.err, r.err


# ═══ unit-level: N210, N339, N272, N194, N191, N381, B13, the N208 widening ══════════════════════════════════

def test_n210_id_resolves_by_the_home_directory_only(tmp_path):
    """N210: /d (0x761) holds aaa.txt, a file MOVED IN from 0x762 (its FileRef 0x762:0x3), and zzz.txt, d's own file
    0x761:0x3. `details --id 0x761:0x3` names zzz.txt -- 1.13.1 matched the parent directory too, and the walk reached
    aaa.txt first."""
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("aaa.txt"), _file_value(3, 0x762, _T)),
                                             _row(_name_key("zzz.txt"), _file_value(3, 0x761, _T + _S))]},
                           0x762: {"parent": 0x600, "name": "e"}})
    rc, out, err = D._syn(path, "details", "--id", "0x761:0x3")
    assert "zzz.txt" in out and "aaa.txt" not in out, D._ctx(rc, out, err)


def test_n210_moved_in_name_resolves_by_its_own_reference(tmp_path):
    """Control: the moved-in aaa.txt is addressed by ITS reference, 0x762:0x3."""
    path = _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("aaa.txt"), _file_value(3, 0x762, _T)),
                                             _row(_name_key("zzz.txt"), _file_value(3, 0x761, _T + _S))]},
                           0x762: {"parent": 0x600, "name": "e"}})
    rc, out, err = D._syn(path, "details", "--id", "0x762:0x3")
    assert "aaa.txt" in out and "zzz.txt" not in out, D._ctx(rc, out, err)


def test_n339_extract_not_found_after_a_recorded_skip_exits_2(tmp_path, monkeypatch, capsys):
    """N339: `extract` of a name not found, in a run that recorded a skip, exits 2 and says it is not evidence of
    absence (1.13.1: exit 1, as a plain not-found)."""
    path = _vol(tmp_path, {0x600: {"name": ""}, 0x761: {"parent": 0x600, "name": "d"}})
    # C1-3 (1.14.0): the test is of THIS view's skips. The view starts with the volume's read (`parse_supb`), which
    # empties its registers, so the skip is recorded inside it, right after the bootstrap, by the real `_skip_note`
    # (a skip planted in the run's list before the command is not this view's: a plain not-found, exit 1)
    for name in ("_SKIP_FINDING", "_SKIP_NOTES", "_VIEW_INCOMPLETE"):
        monkeypatch.setattr(F, name, type(getattr(F, name))())
    _boot = F.bootstrap

    def boot(*a, **k):
        r = _boot(*a, **k)
        F._skip_note("planted", "a planted read", ValueError("planted"))
        return r
    monkeypatch.setattr(F, "bootstrap", boot)
    with pytest.raises(SystemExit) as ex:
        F.cmd_extract(path, ["nothere.txt"], 0)
    assert ex.value.code == 2 and "not evidence that it is absent" in capsys.readouterr().err


def test_n339_control_plain_not_found_exits_1(tmp_path):
    """Control (a fresh process, nothing skipped): the plain not-found, exit 1."""
    path = _vol(tmp_path, {0x600: {"name": ""}, 0x761: {"parent": 0x600, "name": "d"}})
    rc, out, err = D._syn(path, "extract", "nothere.txt")
    assert rc == 1 and "not found" in err and "not evidence" not in err, D._ctx(rc, out, err)


def test_n272_undeterminable_paths_are_relative(tmp_path, monkeypatch):
    """N272: holes.json's undeterminable[].file is relative to the export directory, as streams[].file."""
    out = str(tmp_path / "exp")
    monkeypatch.setattr(F, "_HOLE_STREAMS", [])
    monkeypatch.setattr(F, "_HOLE_REFUSALS", [])
    monkeypatch.setattr(F, "_UNDET_STREAMS", [{"file": os.path.join(out, "content", "a.bin"), "what": "a",
                                               "reason": "r"}])
    assert F._bulk_hole_finish(out) == 2
    with open(os.path.join(out, "holes.json")) as fh:
        doc = json.load(fh)
    assert doc["Undeterminable"][0]["File"] == os.path.join("content", "a.bin"), doc   # K21 (1.14.0)


def test_n194_output_write_errors_do_not_blame_the_image():
    """N194: a write-only error (file too large, disk full) and an error naming another file are not 'cannot read
    image'; an error with no file named stays the image's."""
    img = "/evidence/img.raw"
    assert F._oserror_text(OSError(errno.EFBIG, "File too large"), img).startswith("cannot write the output")
    e = PermissionError(errno.EACCES, "Permission denied", "/out/x.csv")
    assert "not the image" in F._oserror_text(e, img) and "/out/x.csv" in F._oserror_text(e, img)
    assert F._oserror_text(OSError(errno.EIO, "Input/output error"), img).startswith("cannot read image")


@pytest.mark.parametrize("cmd", (["usn", "--csv", "-"], ["mlog", "--json"]), ids=("usn-csv", "mlog-json"))
def test_n194_image_a_closed_stdout_pipe_ends_quietly(cmd):
    """N194 (widened): a closed stdout pipe ends `usn --csv` and `mlog --json` with N171's quiet exit 0 -- 1.13.1 and
    the pre-step tree: rc 1 'cannot read image' (the forensic dispatch caught the BrokenPipeError as an image error).
    The public sample's output is far larger than a pipe's buffer, so the write after the close fails."""
    img = D._image_or_skip("win11refstestmftecmd.raw")
    p = subprocess.Popen([sys.executable, "-B", D.FOREFST, img] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         cwd=os.path.dirname(img))
    p.stdout.read(16)
    p.stdout.close()
    err = p.stderr.read().decode("utf-8", "replace")
    rc = p.wait(timeout=1800)
    assert "cannot read image" not in err and "Traceback" not in err, err[-2000:]
    assert rc == 0, (rc, err[-2000:])


def test_n191_hole_probe_runs_once_per_run_of_clusters(tmp_path, monkeypatch):
    """N191: 32 adjacent clusters (one carve run, added per cluster) are probed with ONE hole query, and the bytes
    counted are the same."""
    img = str(tmp_path / "h.raw")
    with open(img, "wb") as fh:
        fh.truncate(64 * C.CS)
    calls = []
    real = F._hole_bytes_in
    monkeypatch.setattr(F, "_hole_bytes_in", lambda fd, a, b: calls.append((a, b)) or real(fd, a, b))
    monkeypatch.setattr(F, "_CONTENT_HOLES", [])
    with open(img, "rb") as f:
        n = F.content_holes(f, 0, C.CS, [(10 + j, 1, j * C.CS) for j in range(32)], "t", stream_size=32 * C.CS)
    assert len(calls) == 1 and n == 32 * C.CS, (calls, n)


def test_n381_unwritten_run_whose_read_fails_is_not_called_zeros(monkeypatch):
    """N381: a cluster of a zero-filled unwritten run whose read fails is counted as not read (and recorded), not as
    'holds only zeros now'."""
    class Bad(object):
        def seek(self, o):
            pass

        def read(self, n):
            raise OSError(errno.EIO, "Input/output error")
    monkeypatch.setattr(F, "_SKIP_FINDING", [])
    uw = {}
    F._note_unwritten(Bad(), 0, C.CS, {"file_vcn": 0, "clusters": 2, "flags": C.NW, "vlcn": C.V(20), "plcn": 20},
                      2 * C.CS, uw)
    assert uw.get("unread_on_disk_bytes") == 2 * C.CS and uw.get("nonzero_on_disk_bytes") == 0, uw
    assert F._SKIP_FINDING, "the failed read is not recorded"


def test_b13_detect_ads_is_deleted():
    """B13: the unreachable `detect_ads` is gone (the live ADS path is `detect_ads_in_resident`)."""
    assert not hasattr(F, "detect_ads") and hasattr(F, "detect_ads_in_resident")


def test_n208_widening_an_unanswered_hole_query_is_said_and_recorded(tmp_path, monkeypatch, capsys):
    """N208 (widened): a hole statement the host cannot check (`_image_hole_state`, used by the checkpoint, MLog and page
    statements) is said once, in decision 23's words, and recorded as a finding (exit 2)."""
    img = str(tmp_path / "h.raw")
    with open(img, "wb") as fh:
        fh.truncate(8 * C.CS)
    monkeypatch.setattr(F, "_HOLE_UNCHECKED", [])
    monkeypatch.setattr(F, "_FINDINGS", [])
    monkeypatch.setattr(F, "_VIEW_FINDINGS", [])
    monkeypatch.delattr(os, "SEEK_DATA", raising=False)
    with open(img, "rb") as f:
        assert F._image_hole_state(f, 0, C.CS, 0, C.CS) is None
        assert F._image_hole_state(f, 0, C.CS, C.CS, 2 * C.CS) is None
    err = capsys.readouterr().err
    assert err.count("could not check whether the bytes this run read come from holes in the image file") == 1, err
    assert [k for k, _t in F._FINDINGS] == ["hole coverage"], F._FINDINGS


# ═══ images (READ-ONLY; skipped when absent) ═════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def sample_export():
    """ONE `export deleted --full --carve` of the public sample, its directory removed by exact path at the end."""
    import shutil
    import tempfile
    img = D._image_or_skip("win11refstestmftecmd.raw")
    os.makedirs(C.SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="d2_sample_", dir=C.SCRATCH)
    try:
        out = os.path.join(d, "out")
        r = subprocess.run([sys.executable, "-B", D.FOREFST, img, "export", "deleted", "--full", "--carve", out],
                           capture_output=True, text=True, timeout=1800, cwd=d)
        _fx("Traceback" not in r.stderr, r.stderr[-3000:])
        with open(os.path.join(out, "recovery_manifest.json")) as fh:
            recs = jdoc(json.load(fh), F._DELETED_MANIFEST_KEYS)["records"]                                      # K21 (acceptance 1.14.0)
        yield {"rc": r.returncode, "err": r.stderr, "out": r.stdout, "records": recs}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _rec(sample, name):
    got = [r for r in sample["records"] if r["name"] == name and (r["content_file"] or "").find(".carved") >= 0]
    _fx(got, "%s is not carved on the sample" % name)
    return got[0]


def test_b5_image_sample_a_carve_whose_crc_matches(sample_export):
    """B5 on real data: xbpt_papa_echo_912265.md (a deleted file) is carved from a map whose first row carries a
    CRC-32C; the carved cluster matches it (1 of 1), and no mismatch is said."""
    c = _rec(sample_export, "xbpt_papa_echo_912265.md")["carve"]["crc"]
    assert c and c["clusters_with_crc"] == 1 and c["checked"] == 1 and c["match"] == 1 and c["mismatch"] == 0, c
    assert "xbpt_papa_echo_912265.md': " not in sample_export["err"] or "differ from the CRC-32C" not in [
        l for l in sample_export["err"].splitlines() if "xbpt_papa_echo_912265.md" in l][0]


def test_b5_image_sample_a_carve_whose_cluster_differs_from_its_crc(sample_export):
    """B5 on real data: xbpt_whiskey_alpha_896270.bak's one CRC-bearing cluster does NOT match the CRC-32C its map
    stores (the cluster was written again after the map) -- counted in the manifest and said on stderr; exit code not
    changed by it (Q5 A)."""
    r = _rec(sample_export, "xbpt_whiskey_alpha_896270.bak")
    c = r["carve"]["crc"]
    assert c and c["checked"] == 1 and c["mismatch"] == 1 and c["mismatch_vcns"], c
    assert any("xbpt_whiskey_alpha_896270.bak" in l and "differ from the CRC-32C" in l
               for l in sample_export["err"].splitlines()), sample_export["err"][-3000:]


def test_wc3_image_sample_no_live_files_map_is_carved(sample_export):
    """WC-3 on the sample: no entry whose file is live (still present, renamed, same file with another creation time)
    has a carve; each one with an extent map says why (626 entries on the sample: 1.13.1 carved 282 of them)."""
    live = ("still present", "renamed", "same file, other creation time")
    bad = [r["name"] for r in sample_export["records"] if r["status"] in live
           and (r["content_file"] or "").find(".carved") >= 0]
    assert not bad, bad[:10]
    lm = [r for r in sample_export["records"] if r["recoverable"] == "live_file_map"]
    _fx(lm, "no live-file map on the sample")
    assert all(r["status"] in live and "live" in (r["no_carve_reason"] or "") for r in lm), lm[:2]


def test_d50_image_sample_no_live_files_inline_bytes_are_written(sample_export):
    """Wave D step D3, decision 50 (on this module's export): no entry whose file is live has a content file of its
    inline bytes -- each such entry is listed `live_file_inline` with the reason (1.13.2 wrote them: on the sample and
    lab314_main 735, every one the live file's bytes again)."""
    live = ("still present", "renamed", "same file, other creation time")
    bad = [r["name"] for r in sample_export["records"] if r["status"] in live and r["content_file"]]
    assert not bad, bad[:10]
    held = [r for r in sample_export["records"] if r["recoverable"] == "live_file_inline"]
    _fx(held, "no held-back inline content on the sample")
    # acceptance 1.14.0 (decision 37, N317): the manifest no longer writes is_resident -- RecoverabilityCode says it
    assert all(r["status"] in live and "not written: the same file is live" in r["verdict"]
               and r["reliability"] == "NONE" for r in held), held[:2]


def test_b6_image_sample_every_extent_map_gives_a_carve_or_a_reason(sample_export):
    """B6 on the sample: every entry graded 'metadata + carve' has a carve file, and every entry whose extent map
    gives none says why (no_carve_reason)."""
    for r in sample_export["records"]:
        if r["recoverable"] == "extent_backed":
            assert r["content_file"] and r["carve"] and r["carve"]["declared_clusters"] >= 1, r
        if r["recoverable"] in ("map_not_carveable", "live_file_map"):
            assert not r["content_file"] and r["no_carve_reason"], r


# N390's DedupIndex.db node: superseded in wave D step D3 by N472 (`test_1132_d3_rest.py`: the file is now
# decoded and extracted, streamed and sparse)
