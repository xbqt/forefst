"""N166 (1.14.0 RC3): a split file's stream snapshots are in its backing record.

The driver puts them there (RC1D/rc3/N166_DRIVER_READING.md: RefsCreateStreamSnapshot inserts the 0xB0 rows into the
file's own table and refuses no split file; RefsLinkFileToSelf re-parents that table, snapshot rows included, under the
backing key 0x80000040; 26100.9549 and Insider 29574). No corpus image holds such a file (0 snapshot versions in split
files' backings on 117 volumes), so the cases use the bytes of a REAL record that holds snapshots -- an embedded entry
of win11refs2tsnapshots, which has the backing's layout -- as the backing of a split name. RED on forefst c53c8db7: the
backing tuple carries no snapshot list, and `snapshots` lists no split file.
"""
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

F = MC.AB.F
BASE = "step3/win11refs2tsnapshots.raw"
_REC = {}


def _record_with_snapshots():
    """(dir oid, name, value) of the first embedded file entry of the base whose record holds snapshot versions."""
    if "r" in _REC:
        return _REC["r"]
    img = MC.corpus(BASE)
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _c = F.bootstrap(img)
    stack, seen = [0x600], set()
    while stack:
        oid = stack.pop()
        if oid in seen or oid not in obj_map:
            continue
        seen.add(oid)
        for kd, vd in F.walk_bplus(f, ps, cs, tr, obj_map[oid], oid=oid):
            if len(kd) < 4 or F.le16(kd, 0) != 0x30:
                continue
            if len(vd) <= 84:
                if len(vd) >= 0x44 and F.le32(vd, 0x40) & 0x10000000:
                    stack.append(F.le64(vd, 0x08))
                continue
            if F._snapshot_meta(vd, (f, ps, cs, tr)) and F._parse_snapshots_from_value(vd, (f, ps, cs, tr)):
                _REC["r"] = ((f, ps, cs, tr, obj_map), oid, kd[4:].decode("utf-16-le", "replace").rstrip("\0"),
                             bytes(vd))
                return _REC["r"]
    pytest.skip("no embedded entry with snapshot versions on %s" % BASE)


def test_n166_the_backing_tuple_carries_snapshots():
    (f, ps, cs, tr, _om), _oid, name, vd = _record_with_snapshots()
    want = F._snapshot_meta(vd, (f, ps, cs, tr))
    t = F._t40_record_tuple(vd, (f, ps, cs, tr))
    assert len(t) >= 15 and t[14] == want, \
        "a split file's backing holds its snapshot rows (%s: %d version(s)): the backing tuple must carry them" \
        % (name, len(want))


def test_n166_snapshots_lists_a_split_file_once_from_its_backing(monkeypatch):
    (f, ps, cs, tr, obj_map), _oid, name, vd = _record_with_snapshots()
    HOME, FID, DIR = 0x7777, 0x1234, 0x600

    def name_row(n):
        v = bytearray(84)
        struct.pack_into("<Q", v, 0x00, FID)                 # the file id the backing is keyed by
        struct.pack_into("<Q", v, 0x08, HOME)                # the home backref
        struct.pack_into("<I", v, 0x40, 0x20)                # Archive: not a directory
        k = struct.pack("<HH", 0x30, 0) + n.encode("utf-16-le")
        return bytes(k), bytes(v)
    rows = [name_row("first.bin"), name_row("second_link.bin")]
    monkeypatch.setattr(F, "walk_bplus", lambda *a, **k: iter(rows))
    monkeypatch.setattr(F, "_home_backings", lambda *a, **k: {FID: vd})
    om = {DIR: obj_map.get(DIR) or [1], HOME: [2]}
    results = []
    F._find_snapshot_files(f, ps, cs, tr, om, DIR, "", 0, 10, results)
    assert len(results) == 1, "one split file with two names: listed once (%d entries)" % len(results)
    r = results[0]
    assert r["path"] == "first.bin" and r.get("other_names") == ["second_link.bin"] \
        and r.get("record_placement") == "split" and r["vd"] == vd \
        and len(r["snapshots"]) == len(F._parse_snapshots_from_value(vd, (f, ps, cs, tr))), \
        "the entry: the first name, the other name, the backing's versions: %r" % \
        {k: r.get(k) for k in ("path", "other_names", "record_placement")}
