"""1.13.2 (ships 1.14.0) step C4, area bundles: N267, N268, N269, N350 (JSON + log half), N397, N436, N378 (5), RV-7.

Plan: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (C4 rows), settlements Q40-Q43; direct mode (PLAN decision 46):
about five nodes per item.

N267 the manifest records `BytesPerSector`; the reader places a boot sector's `lba` with it (a 4Kn volume's backup boot
     sector landed 8x too low and the bundle reported it missing); a bundle without the key uses its own primary boot
     sector's size.
N268 manifest.json and sha256sums.txt are written in binary from the bytes hashed (text mode broke the seal on CRLF).
N269 a manifest warning (stderr too, exit 0) for each expected backup superblock slot with no valid copy, end-3 first.
N350 in bundle mode every offset is the source image's (the volume is rehydrated at the manifest's partition start) and
     `image` / the recovery log's `Image:` name the bundle; `summary --hash` hashes no temporary file.
N397 the bundle records the source image's $J holes; bundle-mode `usn` / `timeline` / `timestomp` state them as the
     image's readers do, of the source image, and exit 2 as they do.
N436 the bundle records the source image's holes in the MLog data area; A7 says them of the source image.
N378 (5) an artefact address that is not a file offset is an artefact that could not be placed.
RV-7 the bundle's index headers in one form (PascalCase, as mlog_log_index.csv's); older headers still read.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jint                              # noqa: E402  (K21 / K10 readers)
from conftest import jdoc                              # noqa: E402  (K21: internal names)

from test_1132_red_b_items import (_run, _scratch, _image_or_skip, _file_sha, _ctx, _synthetic_vol,  # noqa: E402
                                   _image_vol, FOREFST, AB)
from test_1132_red_b2_journal import beforef_hole_copy, _split, _sentences, _hole_stated  # noqa: E402,F401

BASE = AB.BASE_IMAGE                                     # step1/win11refsmini.raw: partition at 16 MiB
K4N = "step6/lab314_4kn.raw"                             # 4,096-byte sectors


def _reseal(d):
    lines = []
    for n in sorted(os.listdir(d)):
        if n in ("sha256sums.txt", "holes.json") or not os.path.isfile(os.path.join(d, n)):
            continue
        lines.append("%s  %s" % (_file_sha(os.path.join(d, n)), n))
    open(os.path.join(d, "sha256sums.txt"), "w", newline="\n").write("\n".join(lines) + "\n")


def _bundle(img, s, *what, name="b"):
    d = os.path.join(s, name)
    rc, out, err = _run(FOREFST, img, "export", "metadata", d, *(("--what", ",".join(what)) if what else ()), cwd=s)
    AB._fx(os.path.isfile(os.path.join(d, "manifest.json")), "export metadata wrote no bundle" + _ctx(rc, out, err))
    return d, rc, out, err


def _json(rc_out_err):
    rc, out, err = rc_out_err
    i = out.find("{")
    return rc, jdoc(json.JSONDecoder().raw_decode(out[i:])[0]), err      # K21: internal names


def _flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _flat(v, p + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _flat(v, "%s[%d]" % (p, i))
    else:
        yield p, o


def _json_diff(a, b):
    da, db = dict(_flat(a)), dict(_flat(b))
    return sorted(k for k in set(da) | set(db) if da.get(k) != db.get(k))


# ═══ N267 -- the sector size ════════════════════════════════════════════════════════════════════════════════════

def _vbr_backup(d):
    return d["bootstrap_backups"]["vbr"]["backup"]


def test_n267_a_4kn_bundle_places_the_backup_boot_sector_where_the_image_holds_it():
    img = _image_or_skip(K4N)
    with _scratch("c4b") as s:
        # mlog too (1.14.0, Q-D D3): `summary` reads the log, and over a bundle without it says it cannot (exit 2)
        b, *_x = _bundle(img, s, "vbr", "chkp", "supb", "btree", "mlog")
        rc0, a, _e = _json(_run(FOREFST, img, "summary", "--json", cwd=s))
        rc1, d, err = _json(_run(FOREFST, b, "summary", "--json", cwd=s))
        assert _vbr_backup(d) == _vbr_backup(a) and _vbr_backup(d)["present"] and _vbr_backup(d)["cksum_ok"], (
            _vbr_backup(a), _vbr_backup(d))
        assert not [t for t in d["redundancy_findings"] if "backup boot sector" in t], d["redundancy_findings"]
        assert rc1 == rc0, (rc0, rc1, err[-2000:])


def test_n267_the_manifest_records_the_sector_size():
    with _scratch("c4b") as s:
        b4, *_x = _bundle(_image_or_skip(K4N), s, "vbr", name="b4")
        b5, *_x = _bundle(_image_or_skip(BASE), s, "vbr", name="b5")
        assert json.load(open(os.path.join(b4, "manifest.json")))["BytesPerSector"] == 4096
        assert json.load(open(os.path.join(b5, "manifest.json")))["BytesPerSector"] == 512


def test_n267_a_bundle_without_the_key_uses_its_own_primary_boot_sectors_size():
    img = _image_or_skip(K4N)
    with _scratch("c4b") as s:
        b, *_x = _bundle(img, s, "vbr", "chkp", "supb", "btree")
        m = jdoc(json.load(open(os.path.join(b, "manifest.json"))), F._BUNDLE_KEYS)
        del m["BytesPerSector"]                                          # a bundle of an earlier release
        open(os.path.join(b, "manifest.json"), "w").write(json.dumps(m, indent=2))
        _reseal(b)
        rc, d, err = _json(_run(FOREFST, b, "summary", "--json", cwd=s))
        assert _vbr_backup(d)["present"] and _vbr_backup(d)["cksum_ok"], (_vbr_backup(d), err[-1500:])


@pytest.mark.parametrize("man,vbr_bps,want", [
    ({"BytesPerSector": 4096}, 512, 4096), ({}, 4096, 4096), ({}, 512, 512), ({"BytesPerSector": 7}, 4096, 4096),
    ({"BytesPerSector": True}, 512, 512)])
def test_n267_sector_size_rule(tmp_path, man, vbr_bps, want):
    vbr = bytearray(512)
    vbr[3:7] = b"ReFS"
    struct.pack_into("<I", vbr, 0x20, vbr_bps)
    (tmp_path / "vbr_primary.bin").write_bytes(bytes(vbr))
    man = dict(man, artifacts=[{"file": "vbr_primary.bin", "lba": 0}])
    assert F._bundle_sector_size(str(tmp_path), man) == want


# ═══ N268 -- the seal is made from the bytes written ═══════════════════════════════════════════════════════════

def test_n268_the_seal_verifies_when_text_mode_writes_crlf(monkeypatch, tmp_path, capsys):
    """Windows' text mode writes CRLF for "\\n": simulated here for every text-mode write of the exporter."""
    v = _synthetic_vol(tmp_path, "s1")
    real_open = open

    def crlf_open(file, mode="r", *a, **k):
        if "b" not in mode and ("w" in mode or "a" in mode) and "newline" not in k and len(a) < 3:
            k["newline"] = "\r\n"
        return real_open(file, mode, *a, **k)
    monkeypatch.setattr(F, "open", crlf_open, raising=False)
    out = str(tmp_path / "bundle")
    rc = F.cmd_export_metadata(v.path, [out], v.geo.ps)
    capsys.readouterr()
    assert F._bundle_verify_sums(out) == [], F._bundle_verify_sums(out)
    assert b"\r\n" not in open(os.path.join(out, "manifest.json"), "rb").read()


def test_n268_control_the_seal_names_the_manifests_bytes(tmp_path):
    v = _synthetic_vol(tmp_path, "s1")
    out = str(tmp_path / "bundle")
    _run(FOREFST, v.path, "export", "metadata", out, cli=v.geo.cli, cwd=str(tmp_path))
    sums = dict(reversed(ln.split("  ", 1)) for ln in open(os.path.join(out, "sha256sums.txt"), "rb").read()
                .decode().splitlines() if ln)
    assert sums["manifest.json"] == _file_sha(os.path.join(out, "manifest.json"))


# ═══ N269 -- a backup superblock slot with no valid copy ══════════════════════════════════════════════════════

def _supb_warnings(b):
    return [w["reason"] for w in jdoc(json.load(open(os.path.join(b, "manifest.json"))), F._BUNDLE_KEYS)["warnings"] if w["what"] == "supb"]


def test_n269_a_zeroed_backup_slot_is_a_manifest_warning_and_exit_0():
    with _image_vol() as v, _scratch("c4b") as s:
        lo = v.geo.backups[0]                                            # end-3
        v.write(v.at(lo), b"\0" * AB.CS)
        b, rc, out, err = _bundle(v.path, s, "vbr", "supb")
        w = _supb_warnings(b)
        assert w == ["the backup superblock slot at LCN %#x holds no valid copy: all zeros" % lo], w
        assert rc == 0 and "WARNING: " + w[0] in err, _ctx(rc, out, err)
        assert not os.path.exists(os.path.join(b, "supb_backup_lcn%x.bin" % lo))


def test_n269_a_damaged_backup_copy_is_exported_and_warned_about():
    with _image_vol() as v, _scratch("c4b") as s:
        hi = v.geo.backups[1]                                            # end-2
        blk = bytearray(v.read(v.at(hi), AB.CS))
        blk[0x100] ^= 0xFF                                               # inside the checksummed range
        v.write(v.at(hi), bytes(blk))
        b, rc, out, err = _bundle(v.path, s, "vbr", "supb")
        w = _supb_warnings(b)
        assert len(w) == 1 and w[0].startswith("the backup superblock slot at LCN %#x holds no valid copy: " % hi), w
        assert "self-checksum FAILED" in w[0] or "FAILED" in w[0], w
        assert os.path.isfile(os.path.join(b, "supb_backup_lcn%x.bin" % hi)) and rc == 0


def test_n269_both_slots_are_warned_about_end_3_first():
    with _image_vol() as v, _scratch("c4b") as s:
        for lcn in v.geo.backups:
            v.write(v.at(lcn), b"\0" * AB.CS)
        b, rc, out, err = _bundle(v.path, s, "vbr", "supb")
        w = _supb_warnings(b)
        assert [re.search(r"LCN (0x[0-9a-f]+)", x).group(1) for x in w] == ["%#x" % l for l in v.geo.backups], w


def test_n269_control_an_intact_volume_has_no_superblock_warning():
    with _scratch("c4b") as s:
        b, rc, out, err = _bundle(_image_or_skip(BASE), s, "vbr", "supb")
        assert _supb_warnings(b) == [] and rc == 0
        names = [a["file"] for a in jdoc(json.load(open(os.path.join(b, "manifest.json"))), F._BUNDLE_KEYS)["artifacts"]]
        assert [n for n in names if n.startswith("supb_backup")] == ["supb_backup_lcn7bffd.bin",
                                                                       "supb_backup_lcn7bffe.bin"], names


# ═══ N350 -- the source image's offsets and the bundle's name ═════════════════════════════════════════════════

@pytest.fixture(scope="module")
def base_bundle():
    img = _image_or_skip(BASE)
    with _scratch("c4bb") as s:
        b, rc, out, err = _bundle(img, s)
        yield img, b, s


def test_n350_summary_json_of_a_bundle_is_the_images_but_its_name(base_bundle):
    img, b, s = base_bundle
    _rc, a, _e = _json(_run(FOREFST, img, "summary", "--json", cwd=s))
    _rc, d, _e = _json(_run(FOREFST, b, "summary", "--json", cwd=s))
    assert jint(d["partition_start"]) == jint(a["partition_start"]) == 0x1000000          # K10: hex in JSON
    assert d["image"] == os.path.basename(b)
    assert [k for k in _json_diff(a, d) if not k.startswith("/ImageTail")] == ["/Image"], _json_diff(a, d)
    assert d["ImageTail"] is None                       # a bundle does not record the source image's tail


def test_n350_integrity_json_of_a_bundle_is_the_images_but_its_name(base_bundle):
    img, b, s = base_bundle
    _rc, a, _e = _json(_run(FOREFST, img, "integrity", "--json", cwd=s))
    _rc, d, _e = _json(_run(FOREFST, b, "integrity", "--json", cwd=s))
    assert _json_diff(a, d) == ["/Image"] and d["image"] == os.path.basename(b), _json_diff(a, d)


def test_n350_a_bundle_named_with_a_trailing_separator_still_names_the_bundle(base_bundle):
    img, b, s = base_bundle
    _rc, d, _e = _json(_run(FOREFST, b + os.sep, "integrity", "--json", cwd=s))
    assert d["image"] == os.path.basename(b), d["image"]


def test_n350_summary_text_offsets_are_the_images_and_say_so(base_bundle):
    img, b, s = base_bundle
    rc, out, err = _run(FOREFST, b, "summary", cwd=s)
    assert "(offsets are the source image's: the bundle's volume is read where its partition starts there, at " \
           "0x1000000)" in out, out[-3000:]
    assert re.search(r"(?m)^\s+SUPB\s.*0x101e000", out) or "0x101e000" in out, out[-3000:]
    assert "0x1e000 " not in out and "(offset 0x1e000)" not in out + err


def test_n350_the_recovery_log_names_the_bundle(base_bundle):
    img, b, s = base_bundle
    log = os.path.join(s, "rec.log")
    rc, out, err = _run(FOREFST, b, "deleted", "--log", log, cwd=s)
    first = [ln for ln in open(log, encoding="utf-8").read().splitlines() if ln.startswith("Image:")]
    assert first and os.path.abspath(b) in first[0] and "rehydrated" not in first[0], first


def test_n350_summary_hash_of_a_bundle_hashes_no_temporary_file(base_bundle):
    img, b, s = base_bundle
    rc, d, err = _json(_run(FOREFST, b, "summary", "--json", "--hash", cwd=s))
    assert "image_sha256" not in d and "sha256sums.txt" in d["ImageNotHashed"], d.get("ImageNotHashed")


# ═══ N397 -- the source image's $J holes ══════════════════════════════════════════════════════════════════════

def _beforef_bundle(copy, s):
    b, rc, out, err = _bundle(copy.path, s, name="bf")
    return b


@pytest.mark.parametrize("args", [("usn", "--info"), ("usn", "--csv"), ("timeline", "--csv"), ("timestomp",)],
                         ids=["usn-info", "usn-csv", "timeline-csv", "timestomp"])
def test_n397_a_bundle_states_the_source_images_j_hole_and_exits_2_as_the_image(beforef_hole_copy, args):
    with _scratch("c4bj") as s:
        b = _beforef_bundle(beforef_hole_copy, s)
        rc, out, err = _run(FOREFST, b, *args, cwd=s)
        prose, _h, _r = _split(out, err)
        said = [x for x in _sentences(prose) if "source image" in x and "as the bundle's manifest lists" in x]
        assert _hole_stated(_sentences(prose)) and said, (args, rc, prose[-3000:])
        rc_img, _o, _e = beforef_hole_copy.run(*args)
        assert rc == rc_img == 2, (rc, rc_img)


def test_n397_the_manifest_lists_the_punched_j_cluster(beforef_hole_copy):
    from test_1132_red_b2_journal import BF_J_BASE, BF_HOLE_CLUSTER, HCS
    with _scratch("c4bj") as s:
        b = _beforef_bundle(beforef_hole_copy, s)
        m = jdoc(json.load(open(os.path.join(b, "manifest.json"))), F._BUNDLE_KEYS)
        ps = jint(m["partition_start_bytes"])                            # K10: hex in JSON
        lcn = (BF_J_BASE + BF_HOLE_CLUSTER * HCS - ps) // m["cluster_size"]
        assert any(jint(h["lcn"]) <= lcn < jint(h["lcn"]) + h["clusters"]
                   and h["hole_bytes"] == h["clusters"] * m["cluster_size"]
                   for h in m["source_holes"]), (lcn, m["source_holes"][:10])
        assert m["SourceHolesCover"] == ["metadata pages", "$J", "MLog data area"]


def test_n397_control_the_unplanted_bundle_reports_no_journal_hole():
    img = _image_or_skip("step7/labBeforeF.raw")
    with _scratch("c4bj") as s:
        b, *_x = _bundle(img, s, name="bf0")
        rc, out, err = _run(FOREFST, b, "usn", "--info", cwd=s)
        prose, _h, _r = _split(out, err)
        assert rc == 0 and not _hole_stated(_sentences(prose)), (rc, prose[-3000:])


def test_n397_an_older_bundle_says_it_does_not_record_the_streams_holes(base_bundle, tmp_path):
    img, b, s = base_bundle
    d = str(tmp_path / "old")
    shutil.copytree(b, d)
    m = jdoc(json.load(open(os.path.join(d, "manifest.json"))), F._BUNDLE_KEYS)
    del m["SourceHolesCover"]
    open(os.path.join(d, "manifest.json"), "w").write(json.dumps(m, indent=2))
    _reseal(d)
    rc, out, err = _run(FOREFST, d, "usn", "--info", cwd=str(tmp_path))
    assert "does not record which bytes of its $J and MLog data came from holes of the source image" in err, err


@pytest.mark.parametrize("where,want", [
    ("hole", "The image stores the whole $J stream as a hole: "),
    ("source-hole", "The source image stores the whole $J stream as a hole, as the bundle's manifest lists: "),
    ("bundle-absent", "This bundle does not carry the $J stream.")])
def test_n397_the_empty_journal_sentence_by_where(where, want):
    assert F._usn_empty_hole_line(4096, [(0, 4096)], where)[0].startswith(want)


# ═══ N436 -- the source image's holes in the MLog data area ═══════════════════════════════════════════════════

def test_n436_the_manifest_lists_the_mlog_data_areas_holes(base_bundle):
    img, b, s = base_bundle
    m = jdoc(json.load(open(os.path.join(b, "manifest.json"))), F._BUNDLE_KEYS)
    ps, cs = jint(m["partition_start_bytes"]), m["cluster_size"]              # K10: hex in JSON
    code = ("import json,sys; sys.path.insert(0, %r); import forefst as F\n"
            "f, ps, cs, tr, roots, om, a, b, c = F.bootstrap(%r, None)\n"
            "mi = F.get_mlog_info(f, ps, cs, tr, om); ctrl = F.read_mlog_control(f, ps, cs, mi)\n"
            "print(json.dumps(F.mlog_data_range(mi, ctrl, cs)))\n" % (REPO, img))
    import subprocess
    ds, de = json.loads(subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                                       timeout=600).stdout.strip().splitlines()[-1])
    fd = os.open(img, os.O_RDONLY)
    try:
        want = set()
        for a, z in F._hole_ranges_in(fd, ps + ds * cs, ps + de * cs):
            want.update(range((a - ps + cs - 1) // cs, (z - ps) // cs))
    finally:
        os.close(fd)
    AB._fx(want, "base A's MLog data area holds no hole: the node has nothing to check")
    listed = set()
    for h in m["source_holes"]:
        if h["hole_bytes"] == h["clusters"] * cs:
            listed.update(range(jint(h["lcn"]), jint(h["lcn"]) + h["clusters"]))
    assert want <= listed, sorted(want - listed)[:10]


def _a7(monkeypatch, states):
    """mlog_tail_check in bundle mode over a log end two spans past the tail (the ring wraps): 16 blocks, the newest
    record 1:a (one block), the log end 2:4 -- spans [11, 16) and [0, 4); `states` = their `_image_hole_state`s."""
    got = []
    monkeypatch.setattr(F, "_finding", lambda kind, text: got.append(text))
    monkeypatch.setattr(F, "_BUNDLE", {"dir": "/b", "manifest": {}})
    it = iter(states)
    monkeypatch.setattr(F, "_image_hole_state", lambda *a, **k: next(it))

    class Split:
        newest = ((1 << 32) | 0xA, 1)
    end = (2 << 32) | 4
    lines = F.mlog_tail_check(None, 0, 4096, {"data_start_lcn": 0x100, "data_size_clusters": 16},
                              {"log_start": end, "log_end": end, "slot": 0, "plcn": 0x10}, Split())
    assert len(lines) == 2 and got, lines
    return lines[1]


def test_n436_a7_says_listed_holes_of_the_source_image(monkeypatch):
    assert _a7(monkeypatch, ["source-hole", "source-hole"]) == (
        "The source image stores their log blocks as a hole, as the bundle's manifest lists: %s." % F.HOLE_CAUSE_TEXT)


def test_n436_a7_mixed_spans_say_both(monkeypatch):
    assert _a7(monkeypatch, ["source-hole", "bundle-absent"]) == (
        "The source image stores part of their log blocks as holes, as the bundle's manifest lists: %s; this bundle "
        "does not carry the others." % F.HOLE_CAUSE_TEXT)


def test_n436_a7_a_partial_span_in_bundle_mode_never_says_an_image_hole(monkeypatch):
    why = _a7(monkeypatch, ["partial", "none"])
    assert "image hole" not in why and why.startswith("Part of their log blocks is a hole of the source image or is "
                                                      "not carried by this bundle"), why


def test_n436_control_a7_on_an_image_keeps_its_words(monkeypatch):
    monkeypatch.setattr(F, "_BUNDLE", None)
    got = []
    monkeypatch.setattr(F, "_finding", lambda kind, text: got.append(text))
    it = iter(["partial", "none"])
    monkeypatch.setattr(F, "_image_hole_state", lambda *a, **k: next(it))

    class Split:
        newest = ((1 << 32) | 0xA, 1)
    end = (2 << 32) | 4
    lines = F.mlog_tail_check(None, 0, 4096, {"data_start_lcn": 0x100, "data_size_clusters": 16},
                              {"log_start": end, "log_end": end, "slot": 0, "plcn": 0x10}, Split())
    assert lines[1].startswith("Part of their log blocks lies in an image hole ("), lines


# ═══ N378 (5) -- an address that is not a file offset ═════════════════════════════════════════════════════════

def test_n378_5_an_artefact_address_past_any_file_offset_is_not_placed(base_bundle, tmp_path):
    img, b, s = base_bundle
    d = str(tmp_path / "t")
    shutil.copytree(b, d)
    m = jdoc(json.load(open(os.path.join(d, "manifest.json"))), F._BUNDLE_KEYS)
    a = next(x for x in m["artifacts"] if "lcn" in x and x["file"].startswith("supb_backup"))
    a["lcn"] = 1 << 62
    open(os.path.join(d, "manifest.json"), "w").write(json.dumps(m, indent=2))
    _reseal(d)
    rc, out, err = _run(FOREFST, d, "verify-bundle", cwd=str(tmp_path))
    assert rc == 2 and "could not be placed" in out and "is not a file offset" in out, out
    rc, out, err = _run(FOREFST, d, "summary", cwd=str(tmp_path))
    assert "artefact(s) could not be placed" in err and "Traceback" not in err, err[-2000:]


# ═══ RV-7 -- one header form ═══════════════════════════════════════════════════════════════════════════════════

def test_rv7_the_index_headers_are_pascalcase(beforef_hole_copy):
    with _scratch("c4bj") as s:
        b = _beforef_bundle(beforef_hole_copy, s)
        heads = {n: open(os.path.join(b, n)).readline().strip() for n in
                 ("metadata_index.csv", "usn_J_index.csv", "mlog_log_index.csv") if os.path.exists(os.path.join(b, n))}
        assert heads == {"metadata_index.csv": "HeadPLCN,Clusters,ByteOffset,Owner",
                         "usn_J_index.csv": "PLCN,ByteOffset,Clusters",
                         "mlog_log_index.csv": "BlockIndex,ByteOffset"}, heads


def test_rv7_a_bundle_with_the_older_headers_reads_the_same(base_bundle, tmp_path):
    img, b, s = base_bundle
    d = str(tmp_path / "old")
    shutil.copytree(b, d)
    p = os.path.join(d, "metadata_index.csv")
    lines = open(p).read().split("\n")
    lines[0] = "head_plcn,n_clusters,byte_offset,owner"
    open(p, "w").write("\n".join(lines))
    _reseal(d)
    rc, out, err = _run(FOREFST, d, "verify-bundle", cwd=str(tmp_path))
    assert rc == 0 and "PASS" in out, out
    a = _run(FOREFST, b, "files", "--csv", cwd=str(tmp_path))[1]
    c = _run(FOREFST, d, "files", "--csv", cwd=str(tmp_path))[1]
    assert a == c and a.count("\n") > 5
