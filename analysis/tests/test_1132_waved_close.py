"""Wave D's close (1.14.0): the items the close itself changed in the tool (`analysis/reports/v1.13.2/fixes/WAVED_CLOSE.md`;
evidence `fixes/WAVED_CLOSE_evidence/`).

What each group asserts
-----------------------
B13    `_decode_inline_extents` reads an extent row only where the previous row's own declared size puts it; a row whose
       size field (+0x0A) is neither 24 nor 24 + 4 x run ends the walk, and `stop` says so (a carve plan refuses on it).
       The two probes that guessed the next row at +24 / +32 are gone: on the corpus they never fired (221,056 decodes
       on 141 volumes, 3,206 by position, none past its first row: `b13_census.jsonl`).

N474   the two orphan-page scans read a page with THIS volume's signature only when it lies at the address it names
       (+0x20, its own units, directly or through the container table: `_page_at_own_address`); any other is a copy
       inside a file's content or a page whose address is damaged: counted and said, not read.

Synthetic holders and images only (no corpus image is read).
"""
import struct

from _repo import REPO                                   # noqa: F401  layout-independent; see _repo.py

import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21: internal names)
import test_1132_red_c3_scan as SC                       # noqa: E402  (the page builder)

NCL = 1 << 20


def _row(fvcn, vlcn, run, size, flags=0, crcs=()):
    """An extent row: VLCN +0x00 (u64), flags +0x08 (u16), size +0x0A (u16), file VCN +0x0C (u32), run +0x14 (u32),
    then the CRC-32C array when it carries one, padded to 8."""
    r = bytearray(24)
    struct.pack_into("<QHHI", r, 0, vlcn, flags, size, fvcn)
    struct.pack_into("<I", r, 0x14, run)
    r += b"".join(struct.pack("<I", c) for c in crcs)
    r += b"\0" * (-len(r) % 8)
    return bytes(r)


def _positional_holder(rows):
    """A 0x10028 holder whose extent node header does not validate (le32 at the node != 0x28): read by position."""
    ihdr = 0x50
    v = bytearray(ihdr + 0x28)
    struct.pack_into("<I", v, 0, ihdr)
    struct.pack_into("<I", v, 4, F.SNAP_DATA_DESC)
    struct.pack_into("<I", v, ihdr, 0x30)
    struct.pack_into("<I", v, ihdr + 0x14, len(rows))
    return bytes(v) + b"".join(rows) + b"\0" * 64


def test_b13_a_row_with_an_illegal_size_ends_the_walk_and_says_so():
    # row 2 declares size 0; a valid row sits 24 bytes after it -- the old +24 probe read it as the third extent
    v = _positional_holder([_row(0, 0x1000, 1, 24), _row(1, 0x1001, 1, 0), _row(2, 0x1002, 1, 24)])
    stop = []
    got = F._decode_inline_extents(v, NCL, stop=stop)
    assert got == [(0, 0x1000, 1), (1, 0x1001, 1)], got
    assert stop == ["an extent row whose size field is neither 24 nor 24 + 4 x its cluster count (a malformed row)"]


def test_b13_no_guess_at_plus_32_either():
    # the illegal row followed by 8 bytes and a valid row: the old +32 probe read it
    bad = _row(1, 0x1001, 1, 0) + b"\0" * 8
    v = _positional_holder([_row(0, 0x1000, 1, 24), bad, _row(2, 0x1002, 1, 24)])
    got = F._decode_inline_extents(v, NCL)
    assert (2, 0x1002, 1) not in got and len(got) == 2, got


def test_b13_control_legal_sizes_are_followed_crc_rows_included():
    # 24, then a three-cluster row carrying three CRC-32C (size 36, next row at 40), then 24
    v = _positional_holder([_row(0, 0x1000, 1, 24), _row(1, 0x2000, 3, 36, flags=0x80, crcs=(1, 2, 3)),
                            _row(4, 0x3000, 2, 24)])
    stop = []
    got = F._decode_inline_extents(v, NCL, stop=stop)
    assert got == [(0, 0x1000, 1), (1, 0x2000, 3), (4, 0x3000, 2)], got
    assert stop == []


def test_b13_the_carve_plan_s_entry_point_passes_the_stop_on():
    # `_carve_plan` reads a remnant's holder through `parse_snapshot_data_entry(..., rows=, stop=)` and refuses a map
    # whose decode stopped (`plan["refuse"] = stopped`): the malformed row reaches it
    holder = bytearray(_positional_holder([_row(0, 0x1000, 1, 24), _row(1, 0x1001, 1, 0), _row(2, 0x1002, 1, 24)]))
    struct.pack_into("<Q", holder, 0x38, 3 * 4096)        # stream size: 3 clusters
    struct.pack_into("<Q", holder, 0x48, 3 * 4096)        # allocation
    rows, stop = [], []
    _sz, _al, exts = F.parse_snapshot_data_entry(bytes(holder), NCL, rows=rows, stop=stop)
    assert [e[:3] for e in exts] == [(0, 0x1000, 1), (1, 0x1001, 1)] and len(rows) == 2
    assert stop and "a malformed row" in stop[0]


def test_b13_the_probes_are_gone_from_the_source():
    import inspect
    src = inspect.getsource(F._decode_inline_extents)
    assert "stride-fallback" not in src and "_ext(pos + 24)" not in src and "_ext(pos + 32)" not in src


# ═══ N474 -- a page with this volume's signature is read only at the address it names ═══════════════════════════
# N474   The two orphan-page scans read a page with THIS volume's signature only when it lies at the address it names
#        (+0x20, its own units, directly or through the container table: `_page_at_own_address`); any other is a copy
#        inside a file's content (an image or a backup of the metadata) or a page whose address is damaged: counted and
#        said, not read. On the corpus every orphan page the scans read lies at its address (`n474_census.jsonl`).


def _own(cl, name, names_cl=None):
    """A leaf page of this volume (SC.VSIG) whose tuple names `names_cl` (default: where it lies) in 4 KiB units."""
    p = bytearray(SC._page([(0x200, name)], [0]))
    at = cl if names_cl is None else names_cl
    struct.pack_into("<4Q", p, 0x20, *[at + i for i in range(4)])
    return bytes(p)


def _two_page_image(tmp_path):
    # cluster 8: a page at its own address; cluster 16: the same kind of page naming cluster 40 (a copy inside a file)
    return SC._image(tmp_path, {8: _own(8, "mine.txt"), 16: _own(16, "copied.txt", names_cl=40)}, clusters=64)


def test_n474_scan_pages_reads_only_the_page_at_its_own_address(tmp_path, capsys, monkeypatch):
    path = _two_page_image(tmp_path)
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: SC.VSIG)
    with open(path, "rb") as f:
        got = F._scan_for_deleted_entries(f, 0, SC.CS, None, set())
    out = capsys.readouterr().out
    assert sorted(e["name"] for e in got) == ["mine.txt"], got
    said = [l for l in out.splitlines() if "do not lie at the address they name" in l and "this volume's signature" in l]
    assert len(said) == 1 and "1 cluster(s) begin" in said[0] and "the first at cluster 0x10" in said[0], out


def test_n474_full_scan_reads_only_the_page_at_its_own_address(tmp_path, capsys, monkeypatch):
    path = _two_page_image(tmp_path)
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: SC.VSIG)
    log, stats = [], {}
    with open(path, "rb") as f:
        entries = F._slack_recover(f, 0, SC.CS, None, [None] * 13, {}, None, log.append, scan_orphans=True,
                                   live_identity={}, stats=stats)
    capsys.readouterr()
    names = sorted(e["name"] for e in entries)
    assert "copied.txt" not in names and "mine.txt" in names, names
    said = [l for l in log if "do not lie at the address they name" in l and "this volume's signature" in l]
    assert len(said) == 1 and "the first at cluster 0x10" in said[0], log


def test_n474_control_every_page_at_its_own_address_says_nothing(tmp_path, capsys, monkeypatch):
    path = SC._image(tmp_path, {8: _own(8, "mine.txt"), 16: _own(16, "also.txt")}, clusters=64)
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: SC.VSIG)
    with open(path, "rb") as f:
        got = F._scan_for_deleted_entries(f, 0, SC.CS, None, set())
    out = capsys.readouterr().out
    assert sorted(e["name"] for e in got) == ["also.txt", "mine.txt"], got
    assert "do not lie at the address they name" not in out, out


def test_n474_a_page_whose_tuple_names_no_place_is_not_read(tmp_path, capsys, monkeypatch):
    # an all-zero tuple (no unit): the page does not say where it was written
    path = SC._image(tmp_path, {8: SC._page([(0x200, "nowhere.txt")], [0])}, clusters=64)
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: SC.VSIG)
    with open(path, "rb") as f:
        got = F._scan_for_deleted_entries(f, 0, SC.CS, None, set())
    assert got == [] and "the first at cluster 0x8" in capsys.readouterr().out


# ═══ RW-1 -- a row of ANOTHER object with a live file's name and creation time ══════════════════════════════════
# RW-1   A remnant copy whose identity is READ (row or journal) and is not the ObjectRef of any live row of its name and
#        creation time is another object's row (a file deleted and a new one made with the same name and times:
#        `robocopy /MOV`, a tree copy that keeps times, a safe-save): it is its own entry, decided by that identity
#        (DELETED when live nowhere, RENAMED when live under another name), and says that the live file of that name
#        and creation time is another object; copies whose identity is the live file's, or that carry none, stay
#        STILL PRESENT. The review: 359 entries on 13 corpus volumes, the lab's T20 among them.

import csv as _csv                                       # noqa: E402
import os as _os                                         # noqa: E402
import subprocess as _sp                                 # noqa: E402
import sys as _sys                                       # noqa: E402

import test_1132_red_b2_deleted as D                     # noqa: E402  (DirVol, rows, the runners)


def _rw1_volume(tmp_path, slack, extra_files=()):
    """/d (0x761) holds a.bin live (a split row, FileRef 0x761:0x5, creation time D._T) and `slack` in its page."""
    v = D.DirVol()
    v.objects = v.tree({0x600: {"name": ""},
                        0x761: {"parent": 0x600, "name": "d",
                                "files": [D._row(D._name_key("a.bin"), D._file_value(5, 0x761, D._T))]
                                + list(extra_files),
                                "slack": slack}})
    return v.write(str(tmp_path / "rw1.raw"))


def _other_object_row():
    # another object's row: the same name and creation time, FileRef 0x761:0x9 (no live row has it)
    return D._row(D._name_key("a.bin"), D._file_value(9, 0x761, D._T))


def test_rw1_another_objects_row_with_a_live_files_name_and_time_is_deleted(tmp_path):
    path = _rw1_volume(tmp_path, [_other_object_row()])
    rc, out, err = D._syn(path, "deleted", "-v")
    lines = [l.strip() for l in out.splitlines()]
    assert "Identity: ObjectRef 0x761:0x9, read from the row, live nowhere" in lines, out[-3000:]
    assert any(l.startswith("A live file has this name and creation time but is another object: ObjectRef 0x761:0x5 "
                            "(d/a.bin)") for l in lines), out[-3000:]                 # K22 (1.14.0)
    rc2, out2, err2, rows = D._syn_csv(path, "deleted")
    r = [x for x in rows if x["FileName"] == "a.bin"]
    assert r and r[0]["Status"] == "deleted" and r[0]["ObjectRef"] == "0x761:0x9", (r, err2[-1500:])


def test_rw1_another_objects_row_live_under_another_name_is_renamed(tmp_path):
    path = _rw1_volume(tmp_path, [_other_object_row()],
                       extra_files=[D._row(D._name_key("b.bin"), D._file_value(9, 0x761, D._T + D._S))])
    rc, out, err = D._syn(path, "deleted", "-v")
    lines = [l.strip() for l in out.splitlines()]
    assert any(l.startswith("Now: d/b.bin") and "ObjectRef 0x761:0x9" in l for l in lines), out[-3000:]
    assert any(l.startswith("A live file has this name and creation time but is another object: ObjectRef 0x761:0x5")
               for l in lines), out[-3000:]


def test_rw1_control_the_live_files_own_row_stays_still_present(tmp_path):
    # a copy of the live file's own row (FileRef 0x761:0x5) in the page's free space
    path = _rw1_volume(tmp_path, [D._row(D._name_key("a.bin"), D._file_value(5, 0x761, D._T))])
    rc, out, err = D._syn(path, "deleted", "-v")
    assert "but is another object" not in out and "read from the row, live nowhere" not in out, out[-3000:]
    assert "STILL PRESENT -- " in out, out[-3000:]
    rc2, out2, err2, rows = D._syn_csv(path, "deleted")
    # acceptance 1.14.0 (E-1 / N315): the entry is a row of every form, with its Status "still present"
    assert [x["Status"] for x in rows if x["FileName"] == "a.bin"] == ["still present"], rows


def test_rw1_unit_a_plain_name_time_map_splits_nothing():
    # without ObjectRef evidence (a plain {(name, ctime): dirs} map) no copy can be shown to be another object's
    raw = [{"name": "a.bin", "create_time": 5, "is_dir": False, "confidence": "high", "owning_table_oid": 0x761,
            "vd": D._file_value(9, 0x761, 5), "plcn": 1, "page_off": 0x200, "tag": F._TAG_LIVE_PAGE_SLACK}]
    got = F._classify_remnants(raw, {("a.bin", 5): {0x761}}, {0x761: "/d"}, {0x600: [1], 0x761: [2]})
    assert [e["status"] for e in got] == [F._ST_PRESENT] and not got[0].get("same_name_time_live"), got


def _corpus(rel):
    return D._image_or_skip(_os.path.basename(rel))


def test_rw1_image_lab314_main_t20_the_moved_away_file_is_deleted(tmp_path):
    """The lab's T20 ("copy vs move identity", `robocopy /MOV`): d1/t20_src.bin (0x706:0x8) was deleted (the lab's own
    journal dump: FILE_DELETE at USN 2777608); the live d2/t20_src.bin (0x707:0x3) is a new file with the same creation
    time. Until the close the old file was STILL PRESENT ("the same file is live") and in no machine output."""
    img = _corpus("step6/lab314_main.raw")
    r = _sp.run([_sys.executable, "-B", D.FOREFST, img, "deleted", "--full", "--search", "t20_src", "-v"],
                capture_output=True, text=True, timeout=1800)
    lines = [l.strip() for l in r.stdout.splitlines()]
    assert "Identity: ObjectRef 0x706:0x8, read from the change journal, live nowhere" in lines, r.stdout[-4000:]
    assert any(l.startswith("A live file has this name and creation time but is another object: ObjectRef 0x707:0x3")
               for l in lines), r.stdout[-4000:]
    dest = str(tmp_path / "t20.csv")
    _sp.run([_sys.executable, "-B", D.FOREFST, img, "deleted", "--full", "--search", "t20_src", "--csv", dest],
            capture_output=True, text=True, timeout=1800)
    with open(dest, newline="", encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    assert any(x["FileName"] == "t20_src.bin" and x["Status"] == "deleted" and x["ObjectRef"] == "0x706:0x8"
               for x in rows), rows


# ═══ RW-2 -- the export summary counts entries ══════════════════════════════════════════════════════════════════

def test_rw2_image_sample_export_summary_counts_the_carves_the_manifest_records(tmp_path):
    """The public sample, `export deleted DIR --full --carve`: "Carves read from extent maps: N file(s)" counts the
    entries carved (the "Content recovered" line's N and the manifest's records with a carve), not distinct names (25
    beside 32 until the close); the unwritten-run line counts manifest records too."""
    import json as _json
    import re as _re
    img = _corpus("win11refstestmftecmd.raw")
    out = str(tmp_path / "exp")
    r = _sp.run([_sys.executable, "-B", D.FOREFST, img, "export", "deleted", out, "--full", "--carve"],
                capture_output=True, text=True, timeout=3600)
    with open(_os.path.join(out, "recovery_manifest.json")) as fh:
        recs = jdoc(_json.load(fh), F._DELETED_MANIFEST_KEYS)["records"]                                         # K21 (acceptance 1.14.0)
    carved = [m for m in recs if m.get("Carve")]
    m1 = _re.search(r"\+ (\d+) extent-backed carved", r.stdout)
    m2 = _re.search(r"Carves read from extent maps: (\d+) file\(s\)", r.stdout)
    assert m1 and m2, r.stdout[-3000:]
    assert int(m2.group(1)) == int(m1.group(1)) == len(carved), (m1.group(1), m2.group(1), len(carved))
    m3 = _re.search(r"(\d+) file\(s\) carved with such runs \((\d+) over non-zero on-disk data.*?(\d+) file\(s\) refused "
                    r"because EVERY run is unwritten \((\d+) over non-zero data\)", r.stdout, _re.S)
    if m3:
        zf = [m for m in recs if m.get("unwritten_zero_filled_bytes") and not m.get("refused_all_unwritten")]
        # acceptance 1.14.0 E2: a refused carve zero-filled nothing (0); its runs are what the count reads
        rf = [m for m in recs if m.get("unwritten_runs") and m.get("refused_all_unwritten")]
        assert not any(m.get("unwritten_zero_filled_bytes") for m in recs if m.get("refused_all_unwritten"))
        assert int(m3.group(1)) == len(zf) and int(m3.group(3)) == len(rf), (m3.groups(), len(zf), len(rf))


# ═══ RW-7 -- `extract`'s streamed path says what the in-memory path says ═══════════════════════════════════════════
# RW-7   (a) the bytes past the image's end are counted over every cluster cut, as the in-memory path adds them up;
#        (b) a streamed file is written before its hole statement, so a read error during the write leaves no statement
#        about bytes not written; (c) a failed read past the file's size is not part of the output and not recorded;
#        (d) after a read error the in-memory path does not call the shortfall a coverage gap. Latent on the corpus
#        (no image ends inside its volume; read errors planted).

CS4 = 4096


def test_rw7_a_the_streamed_past_the_end_count_is_the_in_memory_sum():
    exts = [{"file_vcn": 0, "clusters": 4, "plcn": 10, "flags": 0x50},
            {"file_vcn": 4, "clusters": 2, "plcn": 0, "flags": 0x20, "is_hole": True},
            {"file_vcn": 6, "clusters": 5, "plcn": 20, "flags": 0x50}]
    img_end = 22 * CS4 + 100                         # the image ends 100 bytes into cluster 22
    cut = F._image_end_cut(exts, 0, CS4, img_end)
    ref = []                                         # the in-memory path: one entry per cluster read short
    for e in exts:
        if F._ext_skip_read(e):
            continue
        for i in range(e["clusters"]):
            a = (e["plcn"] + i) * CS4
            if a + CS4 > img_end:
                ref.append(((e["file_vcn"] + i) * CS4, max(0, min(CS4, img_end - a)), CS4))
    assert sum(w - g for _o, g, w in cut) == sum(w - g for _o, g, w in ref) == 3 * CS4 - 100
    assert min(o + g for o, g, _w in cut) == min(o + g for o, g, _w in ref)


def test_rw7_c_a_failed_read_past_the_files_size_is_not_recorded(tmp_path, monkeypatch):
    img = str(tmp_path / "img.raw")
    with open(img, "wb") as fh:
        for i in range(8):
            fh.write(bytes([0x41 + i]) * CS4)
    real = F._seek_read

    def sr(f, off, n):                               # image cluster 4 (the run's last, past the file's end) fails
        if off <= 4 * CS4 < off + n:
            raise OSError(5, "Input/output error")
        return real(f, off, n)
    monkeypatch.setattr(F, "_seek_read", sr)
    exts = [{"file_vcn": 0, "clusters": 4, "plcn": 1, "vlcn": 1, "flags": 0x50}]     # clusters 1-4: B, C, D, E
    out = str(tmp_path / "out.bin")
    with open(img, "rb") as f, open(out, "wb") as o:
        sc = F._StreamedContent(f, 0, CS4, exts, 2 * CS4 + 10)      # the file ends 10 bytes into its 3rd cluster
        sc.write(o, sparse=True)
    assert sc.unread == [] and sc.written == 2 * CS4 + 10, (sc.unread, sc.written)
    assert open(out, "rb").read() == b"B" * CS4 + b"C" * CS4 + b"D" * 10


def _extract_inproc(img, path, mode, fault, tmp_path):
    """`extract PATH -o OUT` in a subprocess with the streamed path forced on ("stream") or off ("mem") and a read fault
    at image byte `fault`: (rc, stderr lines, the sidecar or None, the output's size)."""
    out = str(tmp_path / ("out_%s.bin" % mode))
    code = ("import sys; sys.path.insert(0, %r); import forefst as F\n"
            "F._EXTRACT_STREAM_MIN = %d\n"
            "real = F._seek_read\n"
            "def sr(f, off, n):\n"
            "    if off <= %d < off + n: raise OSError(5, 'Input/output error (planted)')\n"
            "    return real(f, off, n)\n"
            "F._seek_read = sr\n"
            "sys.argv = ['forefst.py', %r, 'extract', %r, '-o', %r]\n"
            "try:\n    r = F.main(); rc = F.rc_escalate(0 if r is None else r)\n"
            "except SystemExit as e:\n    rc = F.rc_escalate(0 if e.code is None else e.code)\n"
            "sys.exit(rc)\n") % (_os.path.dirname(D.FOREFST), -1 if mode == "stream" else 1 << 62, fault, img, path, out)
    r = _sp.run([_sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=1800)
    import json as _json
    side = None
    if _os.path.exists(out + ".holes.json"):
        with open(out + ".holes.json") as fh:
            side = _json.load(fh)
    size = _os.path.getsize(out) if _os.path.exists(out) else None
    return r.returncode, r.stderr.splitlines(), side, size


def test_rw7_b_image_dedupindex_a_read_error_while_streaming_leaves_no_hole_statement_past_it(tmp_path):
    """win11refs8gdedup DedupIndex.db, streamed, a read fault planted in its data: the output ends at the fault (122,880
    bytes), and no hole statement names a range past that (its first hole range starts at 151,552): the sidecar says
    'none' for the bytes written (until the close: "405504 of 2680160256 bytes ... were written from ranges ...")."""
    img = _corpus("step3/win11refs8gdedup.raw")
    rc, err, side, size = _extract_inproc(img, "System Volume Information/NativeDedup/DedupIndex.db", "stream",
                                          _RW7_DEDUP_FAULT, tmp_path)
    assert rc == 2 and size is not None and size < 151552, (rc, size, err[-6:])
    assert not [l for l in err if "were written from ranges" in l], err
    assert side is not None and side["Status"] == "none", side          # K21 (1.14.0)


_RW7_DEDUP_FAULT = 1701187594      # the review's plant (REVIEW_WAVED_evidence/p3/dedup_fault_stream.json)


def test_rw7_d_image_sample_a_read_error_is_not_called_a_coverage_gap(tmp_path):
    """The public sample, the in-memory path, a read fault in /testintegrity/dotnet-sdk-9.0.314-win-x64.exe: the output
    ends at the unread cluster and says so; the extents cover the file, so no "coverage gap or a sparse file" line."""
    img = _corpus("win11refstestmftecmd.raw")
    rc, err, _side, size = _extract_inproc(img, "/testintegrity/dotnet-sdk-9.0.314-win-x64.exe", "mem",
                                           _RW7_SAMPLE_FAULT, tmp_path)
    assert rc == 2 and [l for l in err if "could not be read" in l and "the output ends at the first" in l], err[-8:]
    assert not [l for l in err if "coverage gap" in l], err


_RW7_SAMPLE_FAULT = 1254244352     # the review's plant (p3/f3_fault_mem.json): file offset 204,800


# ═══ N486 -- an extent node whose index array names no row of it is not read through that index ═════════════════
# N486   A remnant's extent node can carry a valid header and an index array of zeros: every entry then names the node's
#        own header. Read through that index the holder gave no row and recorded no stop, so the carve plan was None and
#        the verdict said the remnant holds no map (win11refs4gattributes cluster 0x1214: a holder cut at a cluster
#        boundary, its two intact rows the live file's first 64 clusters). `_extent_node_header` now takes an index
#        only when each entry names a row of the node (past the header, before the index array, each row once); a node
#        whose index does not is read as one whose header does not validate (by position; the tag scan in the
#        multi-level map), and a live one is recorded as damage.

import test_1132_red_b2_carve as C                       # noqa: E402  (Syn, remnants)
import pytest as _pytest                                 # noqa: E402

# the holder of win11refs4gattributes cluster 0x1214 (page offset 0xf18, 264 bytes): rows at +0x28 and +0x40 intact,
# the third row's VLCN then zeros from the page's offset 0x1000 on (its index array included)
_N486_HOLDER = bytes.fromhex(
    "88000000280001000100000000020000000200000200000000000000000000000300000000000000000000002800000000900400"
    "00000000158604000000000015860400000000000090040000000000010000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000280000007000000004000000000e000074000000"
    "0300000000000000000000008000000000000000672a050000000000500018000000000000000000010000006b36050000000000"
    "5000180001000000000000003f000000aa3605000000000000000000000000000000000000000000000000000000000000000000"
    "00000000")


def _with_index(entries):
    """The N486 holder with its index array (3 entries at value offset 0xfc) written as `entries` (node-relative)."""
    return _N486_HOLDER[:0xfc] + b"".join(struct.pack("<HH", o, 0) for o in entries)


def test_n486_a_zeroed_index_array_does_not_validate():
    assert len(_N486_HOLDER) == 264
    assert F._extent_node_header(_N486_HOLDER, 0x88) == (None, [], "index")


def test_n486_an_entry_into_the_index_array_or_a_repeated_entry_does_not_validate():
    # 0x60 + 24 runs into the index array (it starts at +0x74); 0x40 named twice
    assert F._extent_node_header(_with_index([0x28, 0x40, 0x60]), 0x88)[2] == "index"
    assert F._extent_node_header(_with_index([0x28, 0x40, 0x40]), 0x88)[2] == "index"


def test_n486_control_a_written_index_validates_and_is_read_through():
    lvl, offs, why = F._extent_node_header(_with_index([0x28, 0x40, 0x58]), 0x88)
    assert (lvl, why) == (0, None) and offs == [0x88 + 0x28, 0x88 + 0x40, 0x88 + 0x58]
    # the index names the rows in another order than their places: the index's rows, sorted by file VCN
    assert F._decode_inline_extents(_with_index([0x40, 0x28, 0x58]), NCL << 20) == [(0, 0x52a67, 1), (1, 0x5366b, 63)]


def test_n486_the_cut_holder_is_read_by_position():
    # its two intact rows: 1 + 63 clusters (the third, cut, does not validate: the walk ends there)
    assert F._decode_inline_extents(_N486_HOLDER, NCL << 20) == [(0, 0x52a67, 1), (1, 0x5366b, 63)]


def _zero_index_holder(stream_size, alloc, rows):
    """A 0x10028 holder whose extent node header validates as a header (0x28, the row area end at +0x04, the index
    array at +0x10..+0x20 sized for the rows) and whose index array is zeros."""
    ihdr = 0x88
    v = bytearray(ihdr + 0x28)
    struct.pack_into("<I", v, 0, ihdr)
    struct.pack_into("<I", v, 4, F.SNAP_DATA_DESC)
    struct.pack_into("<Q", v, 0x38, stream_size)
    struct.pack_into("<Q", v, 0x48, alloc)
    body = b"".join(rows)
    lo = 0x28 + len(body)
    for at, w in ((0, 0x28), (4, lo), (0x10, lo), (0x14, len(rows)), (0x20, lo + 4 * len(rows))):
        struct.pack_into("<I", v, ihdr + at, w)
    return bytes(v) + body + b"\0" * (4 * len(rows))


@_pytest.fixture
def syn(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "volume_clusters", lambda f, ps, cs: C.NCL, raising=False)
    monkeypatch.setattr(F, "_volume_ncl", lambda f, ps, cs: C.NCL, raising=False)
    return C.Syn(tmp_path)


def test_n486_a_deleted_remnant_whose_index_is_zeros_is_carved(syn):
    syn.put(10, b"A" * C.CS)
    syn.put(11, b"B" * C.CS)
    hv = _zero_index_holder(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)])
    e = C.entry("cut.bin", C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS))
    r = syn.export_deleted([e])
    assert r.files.get("cut.bin.carved") == b"A" * C.CS + b"B" * C.CS, r.ctx()


def test_n486_a_live_file_s_remnant_is_said_to_hold_its_map_not_no_map():
    # STILL PRESENT (the live file has this name + creation time): the map is not carved (WC-3), and it is said to be
    # there -- not "the file's data is not in this remnant"
    hv = _zero_index_holder(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)])
    e = C.entry("live.bin", C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS), status=F._ST_PRESENT)
    kind, label, _d = F._deleted_recoverability(e, C.CS, C._tr())
    assert kind == "live_file_map" and "not in this remnant" not in label, (kind, label)


def test_n486_a_live_node_whose_index_names_no_row_is_recorded():
    before = len(F._SKIP_FINDING)
    assert F._extent_node_rows(_N486_HOLDER, 0x88) == (None, [])
    assert F._SKIP_FINDING[before:] == ["extent node header"]


# ═══ N487 -- a map that survives in a remnant whose size fields are 0 or disagree is said to survive ════════════════
# N487   `_carve_plan` read a remnant's map only when the row (multi-level map) or the current stream's holder declared a
#        size above 0 and, for the holder, an allocation: a map that survived otherwise gave no plan, and the verdict
#        said "the file's data is not in this remnant" (1,013 remnants of the corpus, nearly all on winsider and
#        winsiderv2: Appx files whose rows were written between their allocation and their size). Now the plan holds
#        the map and refuses, with what the fields say: the row declares 0 B; the stream declares no allocation; the
#        two sizes disagree. No carve is added.

def _plan_of(vd, **kw):
    return F._carve_plan(vd, C.CS, C._tr(), ncl=C.NCL, **kw)


def test_n487_a_row_declaring_0_b_whose_map_survives_is_refused_as_0_b():
    vd, _n, _o = C.multilevel_row([C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)], 2, 0)
    plan = _plan_of(vd)
    assert plan is not None and plan["refuse"] == "the row declares a size of 0 B: there is nothing to carve", plan
    e = C.entry("zero.bin", vd)
    kind, label, _d = F._deleted_recoverability(e, C.CS, C._tr())
    assert kind == "map_not_carveable" and "0 B" in label and "not in this remnant" not in label, (kind, label)


def test_n487_a_live_file_s_0_b_row_gets_the_live_file_line():
    vd, _n, _o = C.multilevel_row([C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)], 2, 0)
    e = C.entry("zero.bin", vd, status=F._ST_PRESENT)
    assert F._deleted_recoverability(e, C.CS, C._tr())[0] == "live_file_map"


def test_n487_holder_rows_with_a_0_stream_size_against_the_row_s_size_are_refused_with_both():
    hv = C.holder_value(0, 2 * C.CS, [C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)])
    vd = C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS)
    plan = _plan_of(vd)
    assert plan is not None and plan["refuse"] == ("the row declares 8192 B and its current stream 0 B: the sizes "
                                                   "disagree, so the length to carve is not known"), plan


def test_n487_holder_rows_with_no_allocation_are_refused_as_such():
    hv = C.holder_value(2 * C.CS, 0, [C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)])
    vd = C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS)
    plan = _plan_of(vd)
    assert plan is not None and (plan["refuse"] or "").startswith(
        "its current stream declares no allocation although its map holds rows"), plan


def test_n487_control_a_holder_with_sizes_and_rows_is_carved_and_a_zeroed_one_has_no_plan():
    hv = C.holder_value(2 * C.CS, 2 * C.CS, [C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)])
    plan = _plan_of(C.long_row([(C.key80(0x1000), hv)], size=2 * C.CS, alloc=2 * C.CS))
    assert plan is not None and plan["refuse"] is None and plan["source"] == "inline holder", plan
    hz = C.holder_value(2 * C.CS, 2 * C.CS, [b"\0" * 24, b"\0" * 24])
    assert _plan_of(C.long_row([(C.key80(0x1000), hz)], size=2 * C.CS, alloc=2 * C.CS)) is None


def test_n487_the_export_writes_no_file_and_records_the_reason(syn):
    syn.put(10, b"A" * C.CS)
    syn.put(11, b"B" * C.CS)
    vd, _n, _o = C.multilevel_row([C.ext_row(C.V(10), 0, 1), C.ext_row(C.V(11), 1, 1)], 2, 0)
    r = syn.export_deleted([C.entry("zero.bin", vd)])
    rec = r.records.get("zero.bin", [{}])[0]
    assert not [n for n in r.files if n.startswith("zero.bin")], r.ctx()
    assert rec.get("recoverable") == "map_not_carveable" and "0 B" in (rec.get("no_carve_reason") or ""), rec


def test_n487_the_reason_names_what_the_fields_say():
    assert F._carve_size_refusal(0, 0, 4096, True) == "the row declares a size of 0 B: there is nothing to carve"
    assert F._carve_size_refusal(8192, 8192, 0, True).startswith("its current stream declares no allocation")
    assert F._carve_size_refusal(0, 8192, 0, False) == ("the row declares 0 B and its current stream 8192 B: the sizes "
                                                         "disagree, so the length to carve is not known")
