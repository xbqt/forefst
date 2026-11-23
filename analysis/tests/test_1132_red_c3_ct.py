"""1.13.2 (ships 1.14.0) step C3, area ct: the Container Table -- A9, N216, N264, N338 (containers half).

Plan: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (C3 rows), settlements Q27-Q30; closure table CL-2 in
`fixes/WAVEC_READING_tables.md`; direct mode (PLAN decision 46): about five nodes per item.

A9   (target check, Q27) a page read for a reference must record, in its header's LCN tuple (+0x20..+0x3F), the address
     it was read for (the reference's LCNs: equal on all 66,153 walked pages of the 117 ReFS corpus volumes, C3's
     measurement); a page that records another one is noted ("wrong-page") and not used. (Overlap) two translated
     containers on overlapping clusters are a view condition. The row-flip nodes of `test_1132_red_a_coverage.py`
     (four surfaces) are the image half of the overlap check.
N216 a row the tools cannot translate linearly (CL-2 rows 3-8: version byte, layout k, flag 0x800, 0x2, 0x8, range
     count != 1) is listed with its reason by `summary`, `integrity` and refsanalysis `containers`, is not in the
     translation map, and a translation into it is a recorded skip (exit 2); the base is the FIRST range.
N264 refsanalysis `containers -v`: only the twice-read flags are named, the state line's categories add up to the rows,
     no "free clusters" figure from row +0x20 (allocated clusters, read once).
N338 refsanalysis `containers` counts and `schema` over a walk that raises: "unreadable", exit 2, no traceback.
"""
import os
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import refsanalysis as RA                                # noqa: E402

from test_1132_red_a_coverage import (                   # noqa: E402
    _COPY, _ct_row_field, _need, _run, _fx, LAB)
from test_1132_red_g2c3 import vol, plant_root_lcn_huge, _run_whole   # noqa: E402,F401
from test_1132_red_a_bootstrap import FOREFST, REFSANALYSIS   # noqa: E402

V34 = "step1/win10refsmini.raw"
NULL = (0, 0xFFFFFFFFFFFFFFFF)


@pytest.fixture(scope="module", autouse=True)
def _drop_the_scratch_copy():
    """N568: `_flag_plant` makes its copy through test_1132_red_a_coverage's `_COPY`, whose own fixture has already
    run by the time these nodes run; without this the copy of LAB stayed in the scratch directory."""
    yield
    _COPY.drop()


# ─── synthetic pages and rows ──────────────────────────────────────────────────────────────────────────────────

def _leaf(tup, rows=((b"K" * 8, b"V" * 16),), size=0x4000):
    """A minimal MSB+ leaf the tool's `_walk` reads: the LCN tuple `tup` at +0x20, `rows` (key, value)."""
    page = bytearray(size)
    page[0:4] = b"MSB+"
    for i, x in enumerate(list(tup) + [0] * (4 - len(tup))):
        struct.pack_into("<Q", page, 0x20 + 8 * i, x)
    struct.pack_into("<I", page, 0x50, 0x10)
    thoff = 0x60
    astart = 0x40
    hdr = [0] * 10
    hdr[4], hdr[8] = astart, astart + 4 * len(rows)
    struct.pack_into("<10I", page, thoff, *hdr)
    at = 0x200
    for i, (k, v) in enumerate(rows):
        struct.pack_into("<I6H", page, thoff + at, 16 + len(k) + len(v), 16, len(k), 0, 16 + len(k), len(v), 0)
        page[thoff + at + 16:thoff + at + 16 + len(k)] = k
        page[thoff + at + 16 + len(k):thoff + at + 16 + len(k) + len(v)] = v
        struct.pack_into("<I", page, thoff + astart + 4 * i, at)
        at += 16 + len(k) + len(v) + 8
    return bytes(page)


def _row(cid, flags=0, count=1, k=4, ranges=None, version=1, length=None):
    """A Container Table row (key, value) laid out as CL-2 row 4 says: (k + 5 + count) x 16 bytes."""
    ranges = ranges if ranges is not None else [(0x1000 * cid, 0x4000)] * count
    n = length if length is not None else (k + 5 + count) * 16
    v = bytearray(max(n, 0x50))
    struct.pack_into("<Q", v, 0, cid)
    v[0x10] = version
    struct.pack_into("<I", v, 0x14, flags)
    struct.pack_into("<I", v, 0x18, 0x4000)
    struct.pack_into("<I", v, 0x4C, count)
    for i, (s, ln) in enumerate(ranges):
        if 0x50 + 16 * (k + i) + 16 <= len(v):
            struct.pack_into("<QQ", v, 0x50 + 16 * (k + i), s, ln)
    key = struct.pack("<QII", cid, 0, 1)
    return key, bytes(v[:n])


@pytest.fixture
def damage(monkeypatch):
    """A fresh damage register and skip registers for one in-process node (the run's registers are left alone)."""
    reg = F._DamageList()
    monkeypatch.setattr(F, "_WALK_DAMAGE", reg)
    monkeypatch.setattr(F, "_SKIP_FINDING", [])
    monkeypatch.setattr(F, "_SKIP_NOTES", {})
    return reg


def _kinds(reg):
    return [k for k, _d in reg]


# ═══ A9 -- the page address check ═════════════════════════════════════════════════════════════════════════════

def test_a9_walk_refuses_a_page_that_records_another_address(damage, capsys):
    page = _leaf([0x8100, 0x8101, 0x8102, 0x8103])
    rows = F._walk(page, None, 0, 4096, None, 3, plcns=[0x500], vlcns=[0x8200, 0x8201, 0x8202, 0x8203])
    assert rows == [] and _kinds(damage) == ["wrong-page"], (rows, list(damage))
    assert "0x8100" in damage[0][1] and "0x8200" in damage[0][1] and "plcn 0x500" in damage[0][1], damage[0]


def test_a9_control_a_page_that_records_its_own_address_is_read(damage):
    page = _leaf([0x8100, 0x8101, 0x8102, 0x8103])
    rows = F._walk(page, None, 0, 4096, None, 3, plcns=[0x500], vlcns=[0x8100, 0x8101, 0x8102, 0x8103])
    assert rows == [(b"K" * 8, b"V" * 16)] and not list(damage)


def test_a9_control_the_64k_tuple_is_the_page_and_three_zeros(damage):
    page = _leaf([0x8100, 0, 0, 0], size=0x10000)
    assert F._walk(page, None, 0, 65536, None, 3, plcns=[0x77], vlcns=[0x8100]) == [(b"K" * 8, b"V" * 16)]
    assert not list(damage)


def test_a9_no_check_where_no_reference_names_the_page(damage):
    """The page scanners read pages by position, not through a reference: no address to compare (vlcns=None)."""
    page = _leaf([0x8100, 0x8101, 0x8102, 0x8103])
    assert F._walk(page, None, 0, 4096, None, 3, plcns=[0x500]) == [(b"K" * 8, b"V" * 16)]
    assert not list(damage)


def test_a9_a_container_row_pointing_at_another_containers_clusters_is_refused_on_a_real_volume(damage):
    """In memory (the image is not touched): the container holding a directory's root page mapped onto another
    container whose clusters hold a page of ANOTHER table at the same offset -- an MSB+ page, so only the address
    check can tell. The walk notes it and uses none of its rows."""
    img = _need(LAB)
    f, ps, cs, tr, roots, obj_map, _a, _b, _c = F.bootstrap(img, None)
    try:
        pick = None
        for oid in sorted(o for o in obj_map if o >= 0x600 and obj_map[o]):
            v = obj_map[oid][0]
            cid, off = v >> tr.shift, v & tr.mask
            for c in sorted(tr.map):
                if c == cid:
                    continue
                pg = F._seek_read(f, ps + (tr.map[c] + off) * cs, cs)
                if pg[:4] == b"MSB+" and F.le64(pg, 0x20) != v:
                    pick = (oid, cid, c)
                    break
            if pick:
                break
        _fx(pick, "no directory whose root page's offset holds another table's page in another container")
        oid, cid, other = pick
        honest = F.walk_bplus(f, ps, cs, tr, obj_map[oid])
        _fx(honest and not list(damage), "the honest walk of 0x%x: %d rows, damage %r" % (oid, len(honest),
                                                                                        list(damage)))
        tr.map = dict(tr.map)
        tr.map[cid] = tr.map[other]
        got = F.walk_bplus(f, ps, cs, tr, obj_map[oid])
    finally:
        f.close()
    assert _kinds(damage)[:1] == ["wrong-page"] and got == [], (oid, cid, other, len(got), list(damage)[:3])


def _ct(monkeypatch, rows, cpc=0x4000):
    monkeypatch.setattr(F, "walk_bplus", lambda f, ps, cs, tr, v, *a, **k: list(rows))
    return F.container_table_read(None, 0, 4096, [0x10], cpc)


@pytest.mark.parametrize("bases,overlap", [
    pytest.param((0x40000, 0x40000), True, id="same-start"),
    pytest.param((0x40000, 0x42000), True, id="inside"),
    pytest.param((0x40000, 0x44000), False, id="adjacent"),
    pytest.param((0x40000, 0x80000), False, id="apart"),
])
def test_a9_overlapping_containers_are_a_condition(monkeypatch, bases, overlap):
    rows = [_row(3, ranges=[(bases[0], 0x4000)]), _row(4, ranges=[(bases[1], 0x4000)])]
    ct = _ct(monkeypatch, rows)
    assert bool(ct["overlaps"]) is overlap and len(ct["conditions"]) == int(overlap), ct["conditions"]
    if overlap:
        assert "0x3 and 0x4" in ct["conditions"][0] and "overlapping clusters" in ct["conditions"][0]


# ═══ N216 -- the rows the tools cannot translate ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("kw,why", [
    pytest.param({"flags": 0x2}, "compressed", id="flag-0x2"),
    pytest.param({"flags": 0x8}, "compacted", id="flag-0x8"),
    pytest.param({"flags": 0x800, "count": 2}, "Container Index row it needs was not found", id="flag-0x800-2-ranges"),
    pytest.param({"flags": 0x80A}, "Container Index row it needs was not found", id="flag-0x800-compacted"),
    pytest.param({"count": 0}, "no mapping range", id="count-0"),
    pytest.param({"count": 2}, "mapped by 2 ranges", id="count-2"),
    pytest.param({"length": 0x50, "count": 0, "version": 0}, "version byte is 0x0", id="version"),
    pytest.param({"length": 0x98}, "do not hold the 1 mapping range", id="length-not-whole"),
])
def test_n216_a_row_the_tools_cannot_translate_says_why(kw, why):
    r = F.ct_row(*_row(5, **kw))
    assert r["why"] and why in r["why"], r


@pytest.mark.parametrize("flags", [0x800, 0x880])
def test_n216_a_container_refs_sys_refuses_but_the_tools_can_map_is_read_and_said(flags):
    """The maintainer's rule (2026-11-06): refs.sys refuses a container with flag 0x800, but one range, neither
    compressed nor compacted, maps linearly -- it is translated, and the refusal is a condition of the view."""
    r = F.ct_row(*_row(5, flags=flags))
    assert r["why"] is None and r["base"] == 0x5000, r
    assert "refs.sys refuses it; the tools read it through its one range" in r["refused"], r
    assert "flags 0x%x" % flags in r["refused"], r


def test_n216_a_refused_container_read_anyway_is_a_condition_of_the_view(monkeypatch):
    rows = [_row(5, flags=0x800), _row(6)]
    monkeypatch.setattr(F, "walk_bplus", lambda *a, **k: iter(rows))
    ct = F.container_table_read(None, 0, 4096, [0x10], 0x4000)
    assert 5 in ct["map"] and 5 not in ct["skipped"], ct["skipped"]
    assert [c for c in ct["conditions"] if c.startswith("container 0x5: ") and "refs.sys refuses it" in c], ct["conditions"]


@pytest.mark.parametrize("flags", [0x0, 0x1, 0x40, 0x200, 0x2000, 0x2440, 0x4001, 0x4200, 0x80])
def test_n216_control_the_corpus_flags_translate(flags):
    """Every flag value of the corpus's 1.59 M rows (WAVEC_measurements MR-3) translates; 0x80 alone is not a refusal
    (refs.sys refuses on 0x800)."""
    r = F.ct_row(*_row(5, flags=flags))
    assert r["why"] is None and r["base"] == 0x5000, r


def test_n216_the_base_is_the_first_range():
    r = F.ct_row(*_row(5, count=2, ranges=[(0x9000, 0x2000), (0x7000, 0x2000)]))
    assert (r["base"], r["length"], r["k"]) == (0x9000, 0x2000, 4) and "2 ranges" in r["why"], r


def test_n216_a_row_whose_layout_differs_from_the_volumes_is_not_translated(monkeypatch):
    rows = [_row(2), _row(3), _row(4, k=5)]
    ct = _ct(monkeypatch, rows)
    assert sorted(ct["map"]) == [2, 3] and "layout" in ct["skipped"][4], ct["skipped"]


def test_n216_a_translation_into_a_container_not_translated_is_a_recorded_skip(monkeypatch, damage, capsys):
    rows = [_row(2), _row(3, flags=0x2), _row(4)]
    ct = _ct(monkeypatch, rows)
    tr = F.Translator(ct["map"], 0x4000, ct["skipped"], ct["first_id"])
    v = (3 << tr.shift) + 5
    assert tr.tr(v) == v and tr.tr(v + 1) == v + 1                  # read nowhere else: identity, as a miss
    assert F._SKIP_FINDING == ["container translation"], F._SKIP_FINDING   # once per container, exit 2
    assert not F._vlcn_mappable(tr, v)                                # the content readers withhold its bytes
    err = capsys.readouterr().err
    assert "container 0x3" in err and "compressed" in err, err
    low = (1 << tr.shift) + 7                                         # below the first id (2): physical, no skip
    assert tr.tr(low) == low and F._SKIP_FINDING == ["container translation"]


def _ct_rows_raw(f, ps, cs, slots):
    """The table's leaf rows (key, value) read with the walker both trees have, independently of `container_table_read`."""
    return [(kd, vd) for kd, vd in F.walk_bplus(f, ps, cs, None, slots) if len(kd) >= 8]


def _ct_value_len(f, ps, cs, slots, cid):
    lens = [len(vd) for kd, vd in _ct_rows_raw(f, ps, cs, slots) if F.le64(kd, 0) == cid]
    _fx(lens, "container 0x%x has no row" % cid)
    return lens[-1]


def _flag_plant(cid_pick):
    """A scratch copy of LAB with one Container Table row's flags byte XORed with 0x02 (compressed), in BOTH copies of
    the table (roots 7 and 8: CB-11, 1.14.0 -- the tool reads root 8 when root 7 fails its check, as refs.sys does, so a
    plant in root 7 alone is read past). The table pages' digests then fail as well (N205: exit 2 on its own); the
    nodes test what only N216 says."""
    img = _need(LAB)
    f, ps, cs, tr, roots, obj_map, _a, _b, _c = F.bootstrap(img, None)
    try:
        cid = cid_pick(tr)
        plants = []
        for ri in F._CT_ROOT_PAIR:
            field = _ct_row_field(f, ps, cs, roots[ri], cid)
            _fx(field is not None, "container 0x%x's row not found in root %d" % (cid, ri))
            vl = _ct_value_len(f, ps, cs, roots[ri], cid)
            flags_at = field - (vl - 16) + 0x14
            f.seek(flags_at)
            _fx(F.le32(f.read(4), 0) & 0x2 == 0, "container 0x%x already has flag 0x2 in root %d" % (cid, ri))
            plants.append((flags_at, 0x02))
    finally:
        f.close()
    return _COPY.get(("c3", "n216", cid), img, plants), cid


@pytest.mark.parametrize("tool,args,said", [
    pytest.param("forefst", ("summary",), "Container not read: 0x%x: it is compressed", id="summary"),
    pytest.param("forefst", ("integrity",), "Container not read: 0x%x: it is compressed", id="integrity"),
    pytest.param("refsanalysis", ("containers",), "container 0x%x is not translated: it is compressed",
                 id="refsanalysis-containers"),
    pytest.param("refsanalysis", ("containers", "-v"), "0x%x      0x", id="refsanalysis-containers-v"),
])
def test_n216_a_compressed_container_is_listed_and_exits_2(tool, args, said):
    path, cid = _flag_plant(lambda tr: max(tr.map))       # the last container: data space, no bootstrap page
    rc, out, _ = _run(tool, path, list(args))
    if args == ("containers", "-v"):
        line = next((l for l in out.splitlines() if l.strip().startswith("0x%x " % cid)), "")
        assert "compressed" in line and rc == 2, "rc %d, row line %r" % (rc, line)
    else:
        assert said % cid in out and rc == 2, "rc %d; %r not in the output" % (rc, said % cid)


# ═══ N264 -- refsanalysis containers -v ════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("name", [V34, LAB])
def test_n264_containers_v_names_only_the_twice_read_flags_and_its_state_line_adds_up(name):
    img = _need(name)
    rc, out, _ = _run("refsanalysis", img, ["containers", "-v"])
    assert rc == 0 and "Free cluster" not in out and "free/unalloc" not in out, out[:3000]
    rows = [l.split() for l in out.splitlines() if l.startswith("  0x") and len(l.split()) >= 5]
    import re
    m = re.search(r"By state: (\d+) translated, (\d+) not translated", out)
    assert m and int(m.group(1)) + int(m.group(2)) == len(rows) > 0, (m and m.group(0), len(rows))
    allowed = {"compressed", "compacted", "index", "row", "missing", "all", "allocated", "-"}
    for r in rows:
        assert set(" ".join(r[4:]).replace("|", " ").split()) <= allowed, r
        if int(r[2], 16) & 0x4000:
            assert "all allocated" in " ".join(r[4:]), r
    cap = re.search(r"Total capacity: ([\d,]+) clusters", out)
    assert cap, out[:2000]


def test_n264_control_the_v34_capacity_is_the_sum_of_the_rows_capacities():
    img = _need(V34)
    f, ps, cs, tr, roots, *_ = F.bootstrap(img, None)
    try:
        want = sum(F.le32(vd, 0x18) for _k, vd in _ct_rows_raw(f, ps, cs, F._select_ct_root(f, ps, cs, roots)))
    finally:
        f.close()
    rc, out, _ = _run("refsanalysis", img, ["containers", "-v"])
    assert "Total capacity: {} clusters".format(want) in out, (want, out[:2500])           # K28 (1.14.0)


# ═══ N338 -- unreadable counts, no traceback ═════════════════════════════════════════════════════════════════

def test_n338_containers_says_unreadable_for_a_count_whose_walk_raises(vol):
    plant_root_lcn_huge(vol, vol.geo.lo, 1, True)      # the Medium Allocator's root, in the copy in use, re-sealed
    rc, out, tb = _run_whole(vol, REFSANALYSIS, "containers")
    assert not tb and rc == 2, "rc %d, traceback %s" % (rc, tb)
    line = next((l for l in out.splitlines() if "Medium Allocator" in l), "")
    assert "unreadable" in line, line


def test_n338_schema_says_unreadable_for_a_root_3_walk_that_raises(vol):
    plant_root_lcn_huge(vol, vol.geo.lo, 3, True)
    rc, out, tb = _run_whole(vol, REFSANALYSIS, "schema", "-H")
    assert not tb and rc == 2 and "Schema Table: unreadable" in out, "rc %d tb %s\n%s" % (rc, tb, out[-1500:])


def test_n338_all_runs_past_a_root_3_walk_that_raises(vol):
    plant_root_lcn_huge(vol, vol.geo.lo, 3, True)
    rc, out, tb = _run_whole(vol, REFSANALYSIS, "all")
    assert not tb and "Schema Table: unreadable" in out and "refsanalysis: containers" in out, out[-2000:]


def test_n338_control_the_counts_of_an_undamaged_volume(vol):
    rc, out, tb = _run_whole(vol, REFSANALYSIS, "containers")
    lines = [l for l in out.splitlines() if "Allocator" in l and "rows" in l]
    assert not tb and lines and all("unreadable" not in l for l in lines), lines


# ═══ the class site: refsanalysis chkp's own map (N216's escalation N-1) ═══════════════════════════════════════

def test_n216_refsanalysis_chkp_and_containers_read_the_table_through_the_shared_reader(monkeypatch, capsys):
    img = _need(V34)
    calls = []
    real = F.container_table_read
    monkeypatch.setattr(RA, "container_table_read", lambda *a: calls.append(a[3]) or real(*a))
    for cmd in (RA.cmd_chkp, RA.cmd_containers):
        cmd(img, [], None)
    capsys.readouterr()
    assert len(calls) == 2, calls
