"""1.13.2 (ships 1.14.0) step C3, area scan: the orphan-page scanners -- A8, N211, N212, N263, N197.

Plan: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (C3 rows), settlements Q31, Q32, Q36, Q37; decision 22 (N211's
words); direct mode (PLAN decision 46): about five nodes per item. A8's image nodes and its unit node are in
`test_1132_red_a_coverage.py` (green in C3); the nodes below add the scanner's own unit cases.

A8   a cluster the scan cannot read is recorded on its own (the rest of its 16 MiB block is still read), the coverage
     line gives the clusters read, says INCOMPLETE, and the run exits 2.
N211 the scanners read the whole page (16 KiB on 4K clusters): rows past the first 4 KiB are found; an old page's
     listed rows are reported, checked against the live tree ("old version of an existing file" / "deleted, seen on
     an old page"), its slack rows are "slack of an old page".
N212 `--scan-pages` skips every page of the live tree, as `--full` does.
N263 `--scan-pages` "Found at": the cluster in hex, the offset from the start of the image, in hex.
N197 a page carrying another volume's signature (+0x0C) is not this volume's: left out of both scans, said, exit 0.
     labJjournal keeps 17 such pages (signature 0x58407e6a; the volume's is 0xc77b66a1).
"""
import errno
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

from test_1132_red_a_coverage import _need, _run, _fx    # noqa: E402

V34 = "step1/win10refsmini.raw"
LABJ = "labJjournal.raw"
CS = 4096
VSIG = 0x11223344


# ─── a synthetic image: MSB+ leaf pages with directory rows placed where the case needs them ──────────────────

def _key(name):
    return struct.pack("<HH", 0x30, 0) + name.encode("utf-16-le")


def _val(ct=0x01DB000000000000, mt=0x01DB000000000001):
    v = bytearray(72)                                     # a non-resident name row: times at +0x10 / +0x18
    struct.pack_into("<QQQ", v, 0x08, 0x700, ct, mt)
    return bytes(v)


def _page(rows, listed, sig=VSIG, size=0x4000, at=0x200):
    """A leaf page: `rows` = [(offset in the page, name)]; the offset array lists the rows whose index is in `listed`.
    The array sits right after the node header, the rows at their offsets (one past the first 4 KiB if asked)."""
    p = bytearray(size)
    p[0:4] = b"MSB+"
    struct.pack_into("<I", p, 0x0C, sig)
    struct.pack_into("<I", p, 0x50, 0x10)
    thoff = 0x60
    astart = 0x40
    hdr = [0] * 10
    hdr[4], hdr[8] = astart, astart + 4 * len(listed)
    struct.pack_into("<10I", p, thoff, *hdr)
    for j, i in enumerate(listed):
        struct.pack_into("<I", p, thoff + astart + 4 * j, rows[i][0] - thoff)
    for off, name in rows:
        k, v = _key(name), _val()
        struct.pack_into("<I6H", p, off, 16 + len(k) + len(v), 0x10, len(k), 0, 0x10 + len(k), len(v), 0)
        p[off + 0x10:off + 0x10 + len(k)] = k
        p[off + 0x10 + len(k):off + 0x10 + len(k) + len(v)] = v
    return bytes(p)


def _named(page, cl):
    """The page with its address tuple (+0x20) naming the four 4 KiB clusters it fills from `cl`, as every page a volume
    writes does: the orphan scans read a page of this volume only at the address it names (N474, wave D's close)."""
    p = bytearray(page)
    struct.pack_into("<4Q", p, 0x20, *[cl + i for i in range(4)])
    return bytes(p)


def _image(tmp_path, pages, clusters=4096):
    path = str(tmp_path / "scan.raw")
    with open(path, "wb") as fh:
        fh.truncate(clusters * CS)
        for cl, data in pages.items():
            fh.seek(cl * CS)
            fh.write(data)
    return path


def _scan(path, end, **kw):
    with open(path, "rb") as f:
        return list(F._iter_msb_clusters(f, 0, CS, end, **kw))


# ═══ N211 -- the whole page ═══════════════════════════════════════════════════════════════════════════════════

def test_n211_the_scanner_yields_the_whole_page(tmp_path):
    pg = _page([(0x200, "early.txt"), (0x1200, "past4k.txt")], listed=[0, 1])
    got = _scan(_image(tmp_path, {8: pg}), 64)
    assert [(c, len(b)) for c, b in got] == [(8, 0x4000)] and got[0][1] == pg


def test_n211_a_page_that_runs_past_a_read_block_is_read_whole(tmp_path):
    pg = _page([(0x200, "a.txt"), (0x3200, "lastcluster.txt")], listed=[0, 1])
    got = _scan(_image(tmp_path, {14: pg}), 64, block_bytes=16 * CS)     # the page spans clusters 14..17
    assert [(c, len(b)) for c, b in got] == [(14, 0x4000)] and got[0][1] == pg


def test_n211_the_name_scan_finds_a_row_stored_past_the_first_4_kib(tmp_path, capsys, monkeypatch):
    path = _image(tmp_path, {8: _named(_page([(0x200, "early.txt"), (0x1200, "past4k.txt")], listed=[0, 1]), 8)})
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: VSIG)
    with open(path, "rb") as f:
        got = F._scan_for_deleted_entries(f, 0, CS, None, set())
    capsys.readouterr()
    assert sorted(e["name"] for e in got) == ["early.txt", "past4k.txt"], got


def test_n211_an_old_page_returns_its_listed_rows_too_and_marks_them(tmp_path):
    pg = _page([(0x200, "listed.txt"), (0x400, "gone.txt")], listed=[0])
    old = {e["name"]: e["listed"] for e in F._scan_page_slack(pg, 8, F._TAG_OLD_PAGE_SLACK, listed=True)}
    live = {e["name"]: e["listed"] for e in F._scan_page_slack(pg, 8, F._TAG_LIVE_PAGE_SLACK)}
    assert old == {"listed.txt": True, "gone.txt": False}, old
    assert live == {"gone.txt": False}, live                  # a live page: its listed rows are live, not remnants


def test_n211_deleted_full_words_an_old_pages_rows_by_the_live_tree():
    """Wave D (WC-1, decision 49): the tag says WHERE a row was found (a live page's slack, an old page's slack, listed
    on an old page); what it is -- here a copy of a live entry -- is the section and the status."""
    rc, out, _ = _run("forefst", _need(V34), ["deleted", "--full", "-v"])     # group 2: the locators are under -v
    tags = re.findall(r"\((?:[a-z ]+, )?(listed on an old page|slack of an old page|slack of a live page|"
                      r"old version of an existing file|deleted, seen on an old page|live-slack|orphan-slack) "
                      r"@ cluster 0x[0-9a-f]+ off", out)
    assert rc == 0 and not {"orphan-slack", "live-slack", "old version of an existing file",
                            "deleted, seen on an old page"} & set(tags), tags
    assert {"listed on an old page", "slack of an old page", "slack of a live page"} <= set(tags), tags
    sp = out.split("STILL PRESENT", 1)[1].split("NOTE:", 1)[0]
    svi = next(l for l in sp.splitlines() if l.strip().startswith("System Volume Information"))
    assert "listed on an old page" in svi and "copy of the current entry" in svi, svi   # listed, and live


def test_n211_scan_pages_finds_the_rows_past_the_first_4_kib_on_a_real_volume():
    rc, out, _ = _run("forefst", _need(V34), ["deleted", "--scan-pages", "-v"])   # group 2: the locators: -v
    sect = out.split("── Orphaned Page Scan ──", 1)[1].split("\n── ", 1)[0]   # group 2: the view nests "  ── " heads
    names = re.findall(r"^    (?:FILE |DIR  )?(\S.*?)  \((?:[a-z ]+, )?listed on an old page @ cluster 0x[0-9a-f]+", sect,
                       re.M)
    assert rc == 0 and "STILL PRESENT" in sect, sect[:1500]
    assert {"System Volume Information", "bye.txt", "coucou", "test"} <= set(names), names


# ═══ N212 -- the skip set ═════════════════════════════════════════════════════════════════════════════════════

def test_n212_scan_pages_skips_every_page_of_the_live_tree(capsys):
    img = _need(V34)
    f, ps, cs, tr, roots, om, *_ = F.bootstrap(img, None)
    try:
        heads, _ptc = F._live_page_heads(f, ps, cs, tr, roots, om)
        old_skip = {tr.tr(v) if tr else v for r in list(roots) + list(om.values()) for v in r}
        _fx(heads - old_skip, "the live tree has no page beyond the roots' first clusters")   # the premise of N212
        found = F._scan_for_deleted_entries(f, ps, cs, tr, heads)
    finally:
        f.close()
    capsys.readouterr()
    assert not {e["plcn"] for e in found} & heads, sorted({e["plcn"] for e in found} & heads)


def test_n212_both_orphan_scans_skip_the_same_pages():
    img = _need(V34)
    f, ps, cs, tr, roots, om, *_ = F.bootstrap(img, None)
    try:
        heads, ptc = F._live_page_heads(f, ps, cs, tr, roots, om)
    finally:
        f.close()
    rc, out, _ = _run("forefst", img, ["deleted", "--scan-pages"])
    m = re.search(r"Current tree references (\d+) metadata pages", out)
    s = re.search(r"Scanned (\d+) live pages", out)
    assert m and s and int(m.group(1)) == len(heads) == int(s.group(1)) == len(ptc), (m and m.group(0), len(heads))


# ═══ N263 -- "Found at" ═════════════════════════════════════════════════════════════════════════════════════

def test_n263_found_at_gives_the_cluster_in_hex_and_the_offset_from_the_image_start():
    img = _need(LABJ)
    ps = F.find_refs_partition(img)[0]
    _fx(ps, "labJjournal: no partition start")
    rc, out, _ = _run("forefst", img, ["deleted", "--scan-pages", "-v"])
    # wave D (B8, one block for both scans): the header gives the cluster in hex, the row's page offset and the
    # row's offset from the start of the image
    hits = re.findall(r"@ cluster (0x[0-9a-f]+) off (0x[0-9a-f]+), image offset (0x[0-9a-f]+)\)", out)
    assert hits and all(int(o, 16) == ps + int(c, 16) * CS + int(po, 16) for c, po, o in hits), (ps, hits[:3])
    assert not re.search(r"cluster \d+ ", out), "a decimal cluster"


def test_n263_the_slack_lines_and_the_recovery_log_give_the_cluster_in_hex(tmp_path):
    img = _need(V34)
    out_dir = str(tmp_path / "exp")
    rc, out, _ = _run("forefst", img, ["export", "deleted", out_dir, "-v"])
    with open(os.path.join(out_dir, "recovery_log.txt"), encoding="utf-8", errors="replace") as fh:
        log = fh.read()
    assert re.search(r"slack of a live page @ cluster 0x[0-9a-f]+ off", out), out[-2000:]
    assert re.search(r"@cluster 0x[0-9a-f]+", log) and not re.search(r"@cluster \d+\b(?!x)", log), log[:2000]


# ═══ N197 -- another volume's pages ═════════════════════════════════════════════════════════════════════════

def test_n197_the_scanner_leaves_out_a_page_with_another_volumes_signature(tmp_path):
    path = _image(tmp_path, {8: _page([(0x200, "mine.txt")], [0]), 16: _page([(0x200, "theirs.txt")], [0], sig=0x99)})
    foreign = []
    got = _scan(path, 64, vsig=VSIG, foreign=foreign)
    # D3b: each entry also carries the page's byte offset inside its cluster (0 at a cluster's start)
    assert [c for c, _b in got] == [8] and foreign == [(16, 0x99, 0)], (got, foreign)
    assert [c for c, _b in _scan(path, 64)] == [8, 16]               # no signature given: no check (as before)


@pytest.mark.parametrize("args", [("deleted", "--full"), ("deleted", "--scan-pages")], ids=["full", "scan-pages"])
def test_n197_labjjournal_another_volumes_pages_are_said_and_not_listed(args):
    rc, out, _ = _run("forefst", _need(LABJ), list(args))
    said = [l for l in out.splitlines() if "another volume's signature" in l]
    assert rc == 0 and said and "0x58407e6a on 17" in said[0] and "0xc77b66a1" in said[0], (rc, said)
    # the 17 pages' clusters (measured on the pre-step tree) never appear as where a row was found
    assert not re.search(r"cluster (0x1008|0x2804)\b", out), [l for l in out.splitlines() if "0x2804" in l][:3]


def test_n197_control_a_volume_without_another_volumes_pages_says_nothing():
    rc, out, _ = _run("forefst", _need(V34), ["deleted", "--full"])
    assert rc == 0 and "another volume's signature" not in out


# ═══ A8 -- the scanner's own unit cases ═════════════════════════════════════════════════════════════════════

def _eio_at(monkeypatch, bad):
    real = F._seek_read

    def sr(f, off, n):
        if off <= bad * CS < off + n:
            raise OSError(errno.EIO, "injected by the C3 A8 node")
        return real(f, off, n)
    monkeypatch.setattr(F, "_seek_read", sr)


def test_a8_one_unreadable_cluster_costs_that_cluster_not_its_block(tmp_path, monkeypatch):
    path = _image(tmp_path, {8: _page([(0x200, "a.txt")], [0]), 40: _page([(0x200, "b.txt")], [0])})
    _eio_at(monkeypatch, 30)
    failed = []
    got = _scan(path, 64, failed=failed)
    assert [c for c, _b in got] == [8, 40] and [c for c, _e in failed] == [30], (got, failed)


def test_a8_control_nothing_unreadable_nothing_failed(tmp_path):
    failed = []
    got = _scan(_image(tmp_path, {8: _page([(0x200, "a.txt")], [0])}), 64, failed=failed)
    assert [c for c, _b in got] == [8] and failed == []


def test_a8_the_coverage_statement_counts_the_clusters_read_and_records_the_skip(monkeypatch, capsys):
    monkeypatch.setattr(F, "_SKIP_FINDING", [])
    monkeypatch.setattr(F, "_SKIP_NOTES", {})
    # RC-5 (wave C's close): the skip is recorded by _scan_unread_said, the coverage said once by _scan_coverage_note
    n, first = F._scan_unread_said([(30, OSError(errno.EIO, "x")), (31, OSError(errno.EIO, "x"))], "t")
    line = F._scan_coverage_note(64, 64, False, None, n, first)
    assert (n, first) == (2, 30) and "read 62 of 64 clusters" in line and "INCOMPLETE" in line and "0x1e" in line, line
    assert F._SKIP_FINDING == ["t"] and F.rc_escalate(0) == 2
    assert F._scan_unread_said([], "t") == (0, None)            # nothing to record when every cluster was read
    assert F._scan_coverage_note(64, 64, False) == "scanned 64 of 64 clusters (100% of the volume)"
