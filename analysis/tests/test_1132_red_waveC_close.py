"""1.13.2 (ships 1.14.0) wave C's close: the review of C3 + C4 (`analysis/reports/v1.13.2/fixes/REVIEW_C3C4.md`) and what
its fixes found. Direct mode (PLAN decision 46): about five nodes per item.

RC-1 (A6)  `integrity --fullchecksums` verifies the child pages below a v3.4 file's extent index (the v3.4 key form of
           the $DATA row); the pages are found here by the VALUE's form, independently of the tool's key rule.
RC-6       the v3.4 files whose extent map is an index decode: `dataruns` lists their extents, `extract` writes them and
           verifies their CRC-32C.
N462       v3.4 integrity streams are verified (they carry the same inline CRC-32C); a file whose CRCs are not read is
           said, never dropped; "No file on this volume carries an integrity stream" only when none does.
N463       an integrity file's clusters in extent rows that carry no CRC-32C are counted and said.
RC-5 (A8)  one orphan-scan coverage line, printed after the scan, from the clusters read; the recovery log the same.
RC-2       an orphan-page scan over a metadata bundle says it read only what the bundle carries, and exits 2.
RC-4 (B11) `export metadata .` and a bundle opened as `.` are named by the folder's own name.
N461       redo opcodes 0x12 and 0x15 call no handler (E123): `mlog` names no handler for them, a transaction of tree-update
           records only is TREE_UPDATE, a no-handler record does not decide a transaction's action, CONTAINER needs
           0x13 or 0x14 (the maintainer's option (a), 2026-10-24).
"""
import os
import re
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

from test_1132_red_b_items import _run, _scratch, _image_or_skip, _ctx, FOREFST, AB   # noqa: E402
from test_1132_red_a_coverage import _run as _hrun, _carve                           # noqa: E402
from test_1132_red_waveb_mlog import build_log, redo_rec, inproc, csv_table, _col   # noqa: E402  (synthetic logs)

V34 = "step3/win10refs8gsetintegristystreams1.raw"     # v3.4, 4K, every file an integrity stream
SAMPLE = "step5/win11refstestmftecmd.raw"                # the public sample
BASE = AB.BASE_IMAGE                                     # step1/win11refsmini.raw
INDEX_FILE = "test/xbpt_config_log_714507.md"            # a v3.4 file whose extent map is an index (108 clusters)


def _v34_index_refs(img):
    """{child reference prefix} of every extent-form stream summary (+0 = 0x88, +4 = 0x00010028) whose node is an index,
    found by the VALUE's form only (not by the attribute key), and the tool's own references for the same rows."""
    f, ps, cs, tr, roots, om, vmaj, vmin, _c = F.bootstrap(img, None)
    ctx = (f, ps, cs, tr)
    mine, tools = set(), set()
    try:
        for oid in sorted(om):
            for kd, vd in F.walk_bplus(f, ps, cs, tr, om[oid]):
                if len(kd) < 4 or F.le16(kd, 0) not in (0x30, 0x40) or len(vd) < 0xC0:
                    continue
                for _akd, aval in F.parse_resident_btree_rows(bytes(vd), ctx):
                    aval = bytes(aval)
                    if not (len(aval) > 0x88 and F.le32(aval, 0) == 0x88 and F.le32(aval, 4) == 0x00010028):
                        continue
                    level, offs = F._extent_node_rows(aval, 0x88)
                    for ro in offs if level else ():
                        vo, vl = F.le16(aval, ro + 0x0A), F.le16(aval, ro + 0x0C)    # the row header <I6H
                        if vl >= 0x30:
                            mine.add(aval[ro + vo:ro + vo + 8])
                tools |= {bytes(r[:8]) for r in F._row_index_child_refs(bytes(vd), ctx)}
    finally:
        f.close()
    return mine, tools, ps, cs


def _coverage(out):
    m = re.search(r"Coverage: +(.+)", out)
    return m.group(1) if m else ""


# ═══ RC-1 -- A6 on v3.4 ════════════════════════════════════════════════════════════════════════════════════════

def test_rc1_every_v34_extent_index_child_found_by_the_value_form_is_one_the_tool_verifies():
    mine, tools, _ps, _cs = _v34_index_refs(_image_or_skip(V34))
    assert len(mine) >= 39 and mine <= tools, (len(mine), len(mine - tools))


def test_rc1_fullchecksums_counts_the_v34_child_pages():
    rc, out, err = _run(FOREFST, _image_or_skip(V34), "integrity", "--fullchecksums")
    assert rc == 0 and "with the 44 child page(s) below their extent and attribute indexes" in _coverage(out), \
        _ctx(rc, out, err)
    assert re.search(r"Pages verified: +141\b", out), _ctx(rc, out, err)


def test_rc1_a_flipped_byte_in_a_v34_child_page_is_a_mismatch():
    img = _image_or_skip(V34)
    f, ps, cs, tr, *_r = F.bootstrap(img, None)
    f.close()
    with _scratch("wc_rc1") as d:
        p = os.path.join(d, "target.raw")
        _carve(img, p)
        off = ps + 0x364 * cs + 0x3000              # child page PLCN 0x364 of test/xbpt_config_log_714507.md
        with open(p, "r+b") as fh:
            fh.seek(off); b = fh.read(1); fh.seek(off); fh.write(bytes([b[0] ^ 1]))
        rc, out, err = _run(FOREFST, p, "integrity", "--fullchecksums")
        # D3 (N470): the clean verdict's words since 1.14.0
        assert rc == 2 and "Verdict: PASS" not in out and "no tampering or corruption detected" not in out, \
            _ctx(rc, out, err)
        rc2, out2, err2 = _run(FOREFST, p, "integrity", "--checksums")      # control: --checksums does not reach it
        assert rc2 == 0, _ctx(rc2, out2, err2)


# ═══ RC-6 -- v3.4 extent indexes decode ════════════════════════════════════════════════════════════════════════

def test_rc6_dataruns_decodes_every_v34_extent_index_file():
    rc, out, err = _run(FOREFST, _image_or_skip(V34), "dataruns", "-v")
    assert rc == 0 and "extents not decoded" not in out and re.search(r"With decoded extents: +262\b", out), \
        _ctx(rc, out, err)


def test_rc6_extract_writes_a_v34_extent_index_file_and_verifies_its_crcs():
    with _scratch("wc_rc6") as d:
        o = os.path.join(d, "x.bin")
        rc, out, err = _run(FOREFST, _image_or_skip(V34), "extract", INDEX_FILE, "-o", o)
        assert os.path.getsize(o) == 440919, _ctx(rc, out, err)
        assert "integrity: 105/105 clusters CRC32-C-verified" in err and "no extents decoded" not in err, \
            _ctx(rc, out, err)


def test_rc6_control_the_leaf_files_keep_the_extents_the_holder_reader_gives():
    img = _image_or_skip(V34)
    f, ps, cs, tr, roots, om, *_r = F.bootstrap(img, None)
    ctx = (f, ps, cs, tr)
    n = differ = 0
    try:
        for oid in sorted(om):
            for kd, vd in F.walk_bplus(f, ps, cs, tr, om[oid]):
                if len(kd) < 4 or F.le16(kd, 0) != 0x30 or len(vd) <= 0xA8:
                    continue
                old = F._parse_inline_holder_extents(bytes(vd), cs, tr)
                if not old:
                    continue
                new = F._embedded_data_extents(bytes(vd), cs, ctx)
                key = lambda es: sorted((e["file_vcn"], e["vlcn"], e["clusters"]) for e in es)
                n += 1
                differ += key(old) != key(new)
    finally:
        f.close()
    assert n >= 200 and differ == 0, (n, differ)


# ═══ N462 -- v3.4 integrity streams are verified, and an unread one is said ══════════════════════════════════

def test_n462_integrity_checksums_verifies_the_v34_streams():
    rc, out, err = _run(FOREFST, _image_or_skip(V34), "integrity", "--checksums")
    assert "No file on this volume carries an integrity stream" not in out, _ctx(rc, out, err)
    assert re.search(r"Files with a stream: +259 \(and 3 with no data in clusters: nothing to verify\)", out), \
        _ctx(rc, out, err)
    assert re.search(r"Clusters checked: +3929 \(3929 OK, 0 FAILED\)", out) and rc == 0, _ctx(rc, out, err)


def test_n462_a_flipped_data_cluster_of_a_v34_integrity_file_is_a_mismatch():
    img = _image_or_skip(V34)
    f, ps, cs, tr, *_r = F.bootstrap(img, None)
    f.close()
    with _scratch("wc_n462") as d:
        p = os.path.join(d, "target.raw")
        _carve(img, p)
        off = ps + 0x3bd09 * cs + 0x10              # the first (checksummed) cluster of INDEX_FILE
        with open(p, "r+b") as fh:
            fh.seek(off); b = fh.read(1); fh.seek(off); fh.write(bytes([b[0] ^ 1]))
        rc, out, err = _run(FOREFST, p, "integrity", "--checksums")
        assert rc == 2 and "INTEGRITY STREAM MISMATCH" in out and INDEX_FILE.split("/")[-1] in out, _ctx(rc, out, err)
        o = os.path.join(d, "x.bin")
        rc2, out2, err2 = _run(FOREFST, p, "extract", INDEX_FILE, "-o", o)
        assert rc2 == 2 and "INTEGRITY MISMATCH" in err2, _ctx(rc2, out2, err2)


def test_n462_extract_says_when_an_integrity_files_checksums_are_not_read(capsys):
    F._integrity_unverified_said({"name": "a.bin", "file_attrs": 0x8000, "extents": [{"clusters": 1}]}, None)
    err = capsys.readouterr().err
    assert "carries an integrity stream, but no CRC-32C row this tool reads" in err and "NOT verified" in err, err
    F._integrity_unverified_said({"name": "b.bin", "file_attrs": 0x20, "extents": [{"clusters": 1}]}, None)
    F._integrity_unverified_said({"name": "c.bin", "file_attrs": 0x8000, "extents": []}, None)
    assert capsys.readouterr().err == ""


def test_n462_the_public_sample_counts_its_integrity_files_with_no_data_in_clusters():
    rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "integrity", "--checksums")
    assert re.search(r"Files with a stream: +189 \(and 151 with no data in clusters: nothing to verify\)", out), \
        _ctx(rc, out, err)


# ═══ N463 -- clusters in rows without a CRC are said ════════════════════════════════════════════════════════

def test_n463_integrity_counts_the_clusters_without_a_crc():
    # N582 (the auditor's RC1 check O5): the 25,338 clusters are in runs marked never written (flags 0x40, N63): they
    # hold no data and are counted as such; no written cluster of these files lacks a CRC-32C, so that line is absent
    rc, out, err = _run(FOREFST, _image_or_skip(V34), "integrity", "--checksums")
    m = re.search(r"Never written: +(\d+) \(clusters of these files in runs marked allocated but never written: no "
                  r"data, read as zeros, nothing to verify\)", out)
    assert m and int(m.group(1)) == 25338 and "Clusters without a CRC:" not in out, _ctx(rc, out, err)
    v = [l for l in out.splitlines() if "every checksummed file cluster matches" in l]
    assert v and "without" not in v[0], v


def test_n463_extract_says_how_many_of_the_files_clusters_carry_no_crc():
    with _scratch("wc_n463") as d:
        o = os.path.join(d, "x.bin")
        rc, out, err = _run(FOREFST, _image_or_skip(V34), "extract", INDEX_FILE, "-o", o)
        # N582 (O5): the 3 clusters are in a run marked never written -- written as zeros, nothing to verify
        assert ("integrity: 105/105 clusters CRC32-C-verified; 3 more cluster(s) of the file are in runs marked never "
                "written (no data: written as zeros, nothing to verify)") in err, _ctx(rc, out, err)


# ═══ RC-5 -- one coverage line, after the scan ═════════════════════════════════════════════════════════════════

def test_rc5_the_coverage_line_and_the_recovery_log_count_an_unread_cluster():
    img = _image_or_skip(BASE)
    with _scratch("wc_rc5") as d:
        o = os.path.join(d, "out")
        rc, text, hits = _hrun("forefst", img, ["export", "deleted", o, "--full"], harness=("eio", 0x19000000, 0x1000))
        cov = [l.strip() for l in text.splitlines() if l.strip().startswith("Orphan-page scan:")
               and "clusters" in l]
        # D3 (WC-2): on a sparse copy the line also counts the clusters read from the image's holes
        assert rc == 2 and len(cov) == 1 and re.fullmatch(
            r"Orphan-page scan: read 507903 of 507904 clusters \(99\.99% of the volume\)(; [\d,]+ of them are image "
            r"holes: no page can be read there)? -- INCOMPLETE: 1 cluster\(s\) could not be read, the first at cluster "
            r"0x18000; deleted data on them was NOT examined", cov[0]), (rc, cov, text[-3000:])
        with open(os.path.join(o, "recovery_log.txt"), encoding="utf-8") as fh:
            log = fh.read()
        assert (re.search(r"Scan coverage: read 507903 of 507904 clusters \(99\.99% of the volume\)(; [\d,]+ of them "
                          r"are image holes: no page can be read there)? -- INCOMPLETE", log)
                and "(100% of the volume)" not in log), log[:2000]


def test_rc5_the_coverage_note_never_rounds_a_short_scan_up():
    assert F._pct_floor(507903, 507904) == "99.99" and F._pct_floor(1, 1) == "100.00" and F._pct_floor(0, 0) == "0.00"
    assert F._scan_coverage_note(100, 100, False) == "scanned 100 of 100 clusters (100% of the volume)"
    n = F._scan_coverage_note(100, 100, False, None, 1, 0x40)
    assert n.startswith("read 99 of 100 clusters (99.00% of the volume) -- INCOMPLETE: 1 cluster(s) could not be "
                        "read, the first at cluster 0x40"), n
    n = F._scan_coverage_note(50, 100, True)
    assert n.startswith("scanned 50 of 100 clusters (50.00% of the volume) -- INCOMPLETE: bounded by --max-scan"), n


def test_rc5_control_a_whole_scan_prints_one_full_coverage_line():
    rc, out, err = _run(FOREFST, _image_or_skip(BASE), "deleted", "--scan-pages")
    cov = [l.strip() for l in out.splitlines() if l.strip().startswith("Orphan-page scan:")]
    # D3 (WC-2, decision 47): on a sparse copy the line also counts the clusters read from the image's holes
    assert rc == 0 and len(cov) == 1 and re.fullmatch(r"Orphan-page scan: scanned 507904 of 507904 clusters \(100% of "
                                                      r"the volume\)(; [\d,]+ of them are image holes: no page can be "
                                                      r"read there)?", cov[0]), _ctx(rc, out, err)


# ═══ RC-2 -- an orphan-page scan over a bundle ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def bundle():
    img = _image_or_skip(BASE)
    with _scratch("wc_rc2") as d:
        b = os.path.join(d, "b")
        rc, out, err = _run(FOREFST, img, "export", "metadata", "-o", b)
        if rc != 0:
            pytest.fail("export metadata failed:" + _ctx(rc, out, err))
        yield b


@pytest.mark.parametrize("mode", ["--scan-pages", "--full"])
def test_rc2_an_orphan_scan_over_a_bundle_reads_only_what_it_carries(bundle, mode):
    rc, out, err = _run(FOREFST, bundle, "deleted", mode)
    txt = out + err
    assert rc == 2 and re.search(r"Orphan-page scan: read the [\d,]+ cluster\(s\) a metadata bundle carries, of "
                                 r"507904 -- INCOMPLETE: the bundle carries the live tree's pages", txt), \
        _ctx(rc, out, err)
    assert "(100% of the volume)" not in txt, _ctx(rc, out, err)


def test_rc2_the_coverage_note_for_a_bundle():
    n = F._scan_coverage_note(1000, 1000, False, carried=390)
    assert n.startswith("read the 390 cluster(s) a metadata bundle carries, of 1000 -- INCOMPLETE"), n


# ═══ RC-4 -- "." is named by its folder ════════════════════════════════════════════════════════════════════════

def test_rc4_export_metadata_into_a_non_empty_current_folder_writes_a_named_sibling():
    img = _image_or_skip(BASE)
    with _scratch("wc_rc4") as d:
        w = os.path.join(d, "work")
        os.makedirs(w)
        with open(os.path.join(w, "other.txt"), "w") as fh:
            fh.write("x")
        rc, out, err = _run(FOREFST, img, "export", "metadata", ".", cwd=w)
        assert rc == 0 and os.path.isdir(os.path.join(d, "work_2")) and not os.path.exists(os.path.join(w, "._2")), \
            _ctx(rc, out, err)
        assert sorted(os.listdir(w)) == ["other.txt"] and os.path.join(d, "work_2") in err, _ctx(rc, out, err)
        rc2, out2, err2 = _run(FOREFST, ".", "summary", "--json", cwd=os.path.join(d, "work_2"))
        assert '"Image": "work_2"' in out2, _ctx(rc2, out2, err2)          # K21 (acceptance 1.14.0)


# ═══ N461 -- 0x12 and 0x15 call no handler (E123) ═════════════════════════════════════════════════════════════════

def _actions(monkeypatch, tmp_path, txns, vmin=14, tag="n461"):
    """[(Action, Opcodes, OpcodesHex)] of `mlog --csv` on a synthetic log of one single-block payload per transaction
    (each a list of opcodes)."""
    log = build_log(tmp_path / ("%s_%d.raw" % (tag, vmin)), [[[redo_rec(op) for op in t]] for t in txns]).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--csv", vmin=vmin)
    hdr, rows, _at = csv_table(out)
    a, o, h = _col(hdr, r"(?i)^(derived)?action$"), _col(hdr, r"(?i)^opcodes$"), _col(hdr, r"(?i)^opcodeshex$")
    AB._fx(len(rows) == len(txns), "%d CSV rows for %d transactions" % (len(rows), len(txns)) + _ctx(rc, out, err))
    return [(r[a], r[o], r[h]) for r in rows]


@pytest.mark.parametrize("vmin", [14, 4])
def test_n461_a_transaction_of_tree_update_records_is_tree_update_not_container(monkeypatch, tmp_path, vmin):
    rows = _actions(monkeypatch, tmp_path, [[0x12], [0x12, 0x12], [0x15]], vmin)
    assert rows == [("TREE_UPDATE", "TREE_UPDATE_RECORD", "0x12"),
                    ("TREE_UPDATE", "TREE_UPDATE_RECORD;TREE_UPDATE_RECORD", "0x12;0x12"),
                    ("OP", "NO_HANDLER", "0x15")], rows


@pytest.mark.parametrize("vmin", [14, 4])
def test_n461_control_add_and_move_container_records_still_class_container(monkeypatch, tmp_path, vmin):
    rows = _actions(monkeypatch, tmp_path, [[0x13], [0x14], [0x03, 0x14]], vmin, tag="n461c")
    assert [r[0] for r in rows] == ["CONTAINER"] * 3 and rows[1][1] == "MOVE_CONTAINER", rows


def test_n461_a_no_handler_record_does_not_decide_the_action(monkeypatch, tmp_path):
    """The bases are the measured mixes of 0x12 (17 volumes, WAVEC_CLOSE): 0x03 + 0x04, 0x06, 0x08, 0x01-0x04; each
    with a 0x12 and with a 0x15 must class as it does without them."""
    bases = [[0x03, 0x04], [0x06], [0x08], [0x01, 0x02, 0x03, 0x04], [0x01]]
    txns = bases + [b + [0x12] for b in bases] + [b + [0x15] for b in bases]
    acts = [r[0] for r in _actions(monkeypatch, tmp_path, txns, tag="n461m")]
    n = len(bases)
    assert acts[n:2 * n] == acts[:n] and acts[2 * n:] == acts[:n] and "CONTAINER" not in acts, acts


def test_n461_mlog_info_names_no_handler_for_0x12_and_0x15():
    table = F._gen_redo_opcode_table().splitlines()
    for title in ("ReFS 3.14", "ReFS 3.4"):
        i = next(j for j, ln in enumerate(table) if ln.strip().startswith(title))
        rows = {}
        for ln in table[i + 1:]:
            if not ln.strip():
                break                     # the blank line that ends the table
            m = re.match(r"^  0x([0-9a-f]+) +(\S+) +(.+)$", ln)
            if not m:
                continue                  # N554 (1.14.0): a wrapped title's or a row's scope continuation line
            rows[int(m.group(1), 16)] = (m.group(2), m.group(3))
        assert rows[0x12][0] == "TREE_UPDATE_RECORD" and rows[0x15][0] == "NO_HANDLER", (title, rows[0x12], rows[0x15])
        assert all("no handler" in rows[op][1] and "Container" not in rows[op][1] for op in (0x12, 0x15)), title
        assert rows[0x14] == ("MOVE_CONTAINER", "RedoMoveContainer"), (title, rows[0x14])
    assert re.search(r"(?m)^  TREE_UPDATE +Only tree-update records \(opcode 0x12\)", F._MLOG_INFO_TEXT)


def test_n461_stats_puts_a_tree_update_record_in_no_container_category(monkeypatch, tmp_path):
    log = build_log(tmp_path / "n461s.raw", [[[redo_rec(0x12)]], [[redo_rec(0x15)]], [[redo_rec(0x14)]]]).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--stats")
    cats = dict((m.group(1).strip(), int(m.group(2))) for m in re.finditer(r"(?m)^  ([a-z][a-z ]*?) +(\d+) +[\d.]+$", out))
    assert cats.get("container") == 1 and cats.get("tree update") == 1 and cats.get("no handler") == 1, \
        repr(cats) + _ctx(rc, out, err)


def test_n461_on_the_public_sample_no_container_row_lacks_a_container_record():
    """win11refstestmftecmd: 13 CONTAINER transactions to ed5c4082, none with 0x13 or 0x14; 12 hold only 0x12 (the
    measurement in WAVEC_CLOSE). Every CONTAINER row must now hold 0x13 or 0x14, and the 12 are TREE_UPDATE."""
    import csv as _csv
    rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "mlog", "--csv")
    rows = list(_csv.DictReader(out.splitlines()))
    AB._fx(rc == 0 and len(rows) > 4000, "mlog --csv on the sample" + _ctx(rc, out[-500:], err))
    ops = [set(int(x, 16) for x in r["OpcodesHex"].split(";") if x) for r in rows]
    bad = [r["Seq"] for r, o in zip(rows, ops) if r["DerivedAction"] == "CONTAINER" and not o & {0x13, 0x14}]   # P8
    only12 = [r["DerivedAction"] for r, o in zip(rows, ops) if o == {0x12}]
    assert not bad and only12 == ["TREE_UPDATE"] * 12, (bad[:5], only12)
