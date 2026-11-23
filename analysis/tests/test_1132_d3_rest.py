"""Wave D step D3 (1.14.0): the rest of decisions 47-50 -- IsMoved, the integrity verdict, the bootstrap note, the
unsigned superblock copy, the earlier volumes' pages, the hole count of the orphan scans, the inline content of a live
file's earlier row, and the sparse file whose extent map is an index node.

Plan: `analysis/reports/v1.13.2/fixes/WAVED_PLAN.md` D3, PLAN_1.13.2.md decisions 47-50; `fixes/D3_NOTES.md`; evidence
`fixes/D3_evidence/`.

What each group asserts
-----------------------
N468   IsMoved is False only where the name sits in the creation directory; a file's one name outside it is "moved, or
       hard-linked and the original name removed" (the metadata does not tell the two apart); a hard-linked file's
       name outside it, and a directory, are "undetermined" -- in CSV, JSON and `details` alike (D3b: unless the
       change journal says how the name came there, `test_1132_d3b.py`).
N470   the clean checksum verdict says "no tampering or corruption detected" and that a checksum cannot prove the
       absence of a deliberate edit.
P13    a wrong self-reference is "BOOTSTRAP DAMAGED OR EDITED" (the bytes do not tell which), never "tampering".
C2-1   a superblock copy that passes refs.sys's tests without its SUPB signature is read and said to lack it; its
       reason is never "valid".
WC-2   the orphan scans' coverage line counts the scanned clusters that lie in the image file's holes (exit unchanged),
       or says the host cannot tell.
D50    decision 50: the inline bytes of a live file's earlier row (STILL PRESENT, RENAMED, SAME FILE) are not written;
       the entry stays listed with the reason; a deleted entry's bytes still are.
N472   a sparse file's E86 map that tiles only its allocation is accepted; above 256 MiB `extract` streams the file
       (sparse on disk, bounded memory) -- win11refs8gdedup's DedupIndex.db.
C3-1   a page with another volume's signature counts as an earlier volume's only at the address it names; the others
       (a deduplication index's pages, text) are said apart; `deleted --earlier-volumes` lists ONLY an earlier volume's
       rows, grouped by signature.

Volumes: the synthetic builders of `test_1132_red_b2_deleted.py`, `test_1132_red_c3_scan.py` and
`test_1132_red_a_bootstrap.py` (through `test_1132_red_b_items.py` and `test_1132_red_c2_supb.py`); corpus images
READ-ONLY, skipped when absent.
"""
import csv
import json
import os
import re
import resource
import shutil
import struct
import sys
import tempfile

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21: internal names)
import test_1132_red_b2_deleted as D                     # noqa: E402  (DirVol, rows, the runners)
import test_1132_red_c3_scan as SC                       # noqa: E402  (orphan-page images)
import test_1132_red_b_items as BI                       # noqa: E402  (synthetic volume, runners)
import test_1132_red_c2_supb as S2                       # noqa: E402  (re-sealed superblock plants)

_T, _S = D._T, D._S
_row, _name_key = D._row, D._name_key
_fx = D._fx
CS = 4096
SAMPLE = "win11refstestmftecmd.raw"
BASE = "step1/win11refsmini.raw"                        # battery base A (two copies of the name exist)


def _vol(tmp_path, dirs):
    v = D.DirVol()
    v.objects = v.tree(dirs)
    return v.write(str(tmp_path / "target.raw"))


def _img(name):
    return D._image_or_skip(name)


def _tool(img, *args, timeout=1800, cwd=None):
    r = UW.run([sys.executable, "-B", D.FOREFST, img] + list(args), capture_output=True, text=True,
               timeout=timeout, cwd=cwd or os.path.dirname(img))
    _fx("Traceback" not in r.stderr, r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


# ═══ N468 -- IsMoved ═════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("row,want", [
    ({"home_oid": 0x740, "parent_oid": 0x740, "hard_link_count": 1}, False),
    ({"home_oid": 0x740, "parent_oid": 0x74e, "hard_link_count": 1}, "moved, or hard-linked and the original name removed"),
    ({"home_oid": 0x740, "parent_oid": 0x74e, "hard_link_count": 2}, "undetermined"),
    ({"home_oid": 0x740, "parent_oid": 0x740, "hard_link_count": 3}, False),
    ({"is_dir": True, "oid": 0x750, "parent_oid": 0x600}, "undetermined"),
], ids=["in-home", "one-name-outside", "hardlink-outside", "hardlink-in-home", "directory"])
def test_n468_ismoved_says_what_the_rule_decides(row, want):
    """N468 (decision 49 point 7): False only where the name sits in its creation directory; one name outside it reads
    as a move or as a hard link whose original name was removed; a hard link's name outside it and a directory (no
    creation directory recorded) are undetermined -- never printed as False (85 moved hard-linked files on the sample)
    or True (9 never-moved ones)."""
    assert F._is_moved(row) == want, F._is_moved(row)
    assert (F._is_moved_reason(row) != "") == (want == "undetermined"), F._is_moved_reason(row)


@pytest.fixture(scope="module")
def sample_files():
    img = _img(SAMPLE)
    d = tempfile.mkdtemp(prefix="d3_files_", dir=BI.SCRATCH if os.path.isdir(BI.SCRATCH) else None)
    try:
        c, j = os.path.join(d, "f.csv"), os.path.join(d, "f.json")
        rc1, _o, e1 = _tool(img, "files", "--csv", c)
        rc2, _o, e2 = _tool(img, "files", "--json", j)
        _fx(rc1 == rc2 == 0, e1[-2000:] + e2[-2000:])
        with open(c, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        with open(j, encoding="utf-8") as fh:
            js = json.load(fh)
        yield rows, js
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_n468_image_sample_ismoved_never_prints_an_undecided_value_as_true_or_false(sample_files):
    """N468 on the public sample: no row says True; False only where ParentOID = HomeOID. Outside it, D3b (decision
    51): the change journal's value where it says how the name came there, else the metadata's -- "moved, or
    hard-linked and the original name removed" for a file's one name (49 of the 123), "undetermined" for a hard-linked
    name; a directory is the journal's (in / outside its creation directory) or "undetermined"."""
    rows, _js = sample_files
    vals = {r["IsMoved"] for r in rows}
    assert "True" not in vals and "true" not in vals, vals      # acceptance 1.14.0 (K19: booleans true / false)
    cj = {"moved (change journal)", "a hard link made here (change journal)"}
    for r in rows:
        if r["IsDirectory"] == "true":
            assert r["IsMoved"] in ("undetermined", "moved (change journal)",
                                    "in its creation directory (change journal)"), r
        elif r["ParentOID"] == r["HomeOID"]:
            assert r["IsMoved"] == "false", r
        elif r["HardLinkCount"] not in ("", "1"):
            assert r["IsMoved"] in cj | {"undetermined"}, r
        else:
            assert r["IsMoved"] in cj | {"moved, or hard-linked and the original name removed"}, r
    assert sum(1 for r in rows if r["IsMoved"].startswith("moved, or")) == 49


def test_n468_image_sample_json_carries_the_same_values(sample_files):
    """N468: the JSON form says what the CSV says, row for row (one wording per fact in every form)."""
    rows, js = sample_files
    # acceptance 1.14.0 (O7: `files --json` is the CSV's rows; WAVEE_QUESTIONS: IsMoved a string in JSON too)
    recs = js if isinstance(js, list) else js.get("files", [])
    by, want = {}, {}
    for r in recs:
        by[r["IsMoved"]] = by.get(r["IsMoved"], 0) + 1
    for r in rows:
        want[r["IsMoved"]] = want.get(r["IsMoved"], 0) + 1
    assert by == want and all(isinstance(k, str) for k in by), (by, want)


def test_n468_details_states_the_relocation_without_claiming_a_move():
    """N468: `details` of a hard-linked name outside its creation directory says it is a hard link's or a moved name
    (undetermined), never "hard-link name" or "moved" as facts."""
    src = open(D.FOREFST, encoding="utf-8").read()
    assert "⚠ moved: created here" not in src and "hard-link name — created here" not in src
    # acceptance 1.14.0 E2 (N511, K19: a False IsMoved prints `no`): the value and its reason, one line
    assert "Is moved:           {'no' if _mv is False else _mv}{_is_moved_reason(r)}" in src and "_mv = _is_moved(r)" in src


# ═══ N470 -- the integrity verdict ═══════════════════════════════════════════════════════════════════════════

def _verdicts(out):
    return [l.strip() for l in out.splitlines() if l.strip().startswith("VERDICT:")]


@pytest.mark.parametrize("opt", ["--checksums", "--fullchecksums"])
def test_n470_clean_verdict_says_a_checksum_cannot_prove_the_absence_of_an_edit(opt):
    """N470 (decision 49 point 8): the clean page-checksum verdict says "no tampering or corruption detected" and that a
    checksum cannot prove the absence of a deliberate edit (ReFS checksums take no key); exit unchanged."""
    rc, out, err = _tool(_img(BASE), "integrity", opt)
    v = [x for x in _verdicts(out) if "checksummed pages" in x]
    assert rc == 0 and len(v) == 1, (rc, v, err[-1500:])
    assert ("VERIFIED — no tampering or corruption detected in these pages (a checksum cannot prove the absence of a "
            "deliberate edit)") in v[0], v
    assert not re.search(r"no tampering/corruption", out), [l for l in out.splitlines() if "tampering" in l]


def test_n470_every_no_tampering_line_carries_the_limit():
    """N470: no output line of the tool's source says "no tampering" without "detected" and the checksum's limit."""
    src = open(D.FOREFST, encoding="utf-8").read()
    assert F._NO_TAMPER_DETECTED == "no tampering or corruption detected"
    assert F._CHECKSUM_LIMIT == "(a checksum cannot prove the absence of a deliberate edit)"
    printed = [l for l in src.splitlines() if "no tampering" in l and "print(" in l]
    assert not printed, printed


# ═══ P13 and C2-1 -- the bootstrap words ═════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_p13_a_wrong_self_reference_is_damaged_or_edited_never_tampering(tmp_path, cmd):
    """P13 (decision 49 point 8): a superblock copy whose own LCN (+0x20) is not where it lies (re-sealed) is reported
    "BOOTSTRAP DAMAGED OR EDITED", the bytes not telling which -- not "TAMPERING" / "treat it as deliberate"."""
    v = BI._synthetic_vol(tmp_path)
    lcn = v.geo.backups[0]
    S2._reseal(v, lcn, S2._q(0x20, lcn + 1))
    rc, out, err = BI._vrun(v, BI.FOREFST, cmd)
    assert "** BOOTSTRAP DAMAGED OR EDITED: 1 structure(s) above carry a CORRUPT self-reference" in out, \
        BI._ctx(rc, out, err)
    assert "the bytes do not" in out and "tell which" in out, out
    assert "TAMPERING" not in out and "deliberate tampering" not in out, out


def _unsigned(v, lcn):
    """The copy at `lcn` without its SUPB signature, re-sealed: it passes every test refs.sys makes."""
    S2._reseal(v, lcn, S2._flip_sig_to_zero)
    blk = v.block(lcn)
    with open(v.path, "rb") as fh:
        got = F.supb_validate(blk, CS, lcn, F.volume_clusters(fh, v.geo.ps, CS))
    _fx(got["ok"] and not got["sig_ok"], "the plant is not an unsigned valid copy: %r" % (got,))
    return blk, got


def test_c21_reason_of_an_unsigned_valid_copy_names_the_missing_signature(tmp_path):
    """C2-1 (decision 47; WC-4): the reason of a copy that passes refs.sys's tests without its signature says so --
    1.13.2 returned "valid", so a warning read "holds no valid copy: valid"."""
    v = BI._synthetic_vol(tmp_path)
    blk, got = _unsigned(v, v.geo.backups[1])
    why = F._supb_damage_reason(blk, got)
    assert why != "valid" and "passes refs.sys's superblock tests but carries no SUPB signature" in why, why


def test_c21_an_unsigned_valid_primary_is_read_and_said(tmp_path):
    """C2-1: an unsigned primary that passes refs.sys's tests is read as refs.sys reads it (the files are listed) and
    a warning names the missing signature; exit unchanged (0)."""
    v = BI._synthetic_vol(tmp_path)
    _unsigned(v, v.geo.supb)
    rc, out, err = BI._vrun(v, BI.FOREFST, "files")
    assert rc == 0, BI._ctx(rc, out, err)
    w = [l for l in err.splitlines() if "carries no SUPB signature" in l]
    assert len(w) == 1 and "passes refs.sys's superblock tests: it is read, as refs.sys reads it" in w[0], err[-2000:]


def test_c21_the_redundancy_list_calls_it_damaged_and_says_why(tmp_path):
    """C2-1: `summary`'s redundancy list keeps calling the unsigned copy damaged, with what is wrong with it."""
    v = BI._synthetic_vol(tmp_path)
    _unsigned(v, v.geo.supb)
    rc, out, err = BI._vrun(v, BI.FOREFST, "summary")
    txt = out + err
    assert re.search(r"is missing or damaged \(it passes refs\.sys's superblock tests but carries no SUPB signature",
                     txt), BI._ctx(rc, out, err)


def test_c21_control_a_signed_primary_draws_no_signature_warning(tmp_path):
    v = BI._synthetic_vol(tmp_path)
    rc, out, err = BI._vrun(v, BI.FOREFST, "files")
    assert rc == 0 and "SUPB signature" not in err, BI._ctx(rc, out, err)


# ═══ WC-2 -- the image holes of an orphan scan ═══════════════════════════════════════════════════════════════

def test_wc2_coverage_note_words():
    """WC-2 (decision 47): the clause is added to the line in every form; nothing for none; the host's limit said."""
    assert F._scan_coverage_note(64, 64, False, holes=60) == ("scanned 64 of 64 clusters (100% of the volume); 60 of "
                                                              "them are image holes: no page can be read there")
    assert F._scan_coverage_note(64, 64, False, holes=0) == "scanned 64 of 64 clusters (100% of the volume)"
    assert "could not be checked on this host" in F._scan_coverage_note(64, 64, False, holes=-1)
    n = F._scan_coverage_note(32, 64, True, holes=5)
    assert n.startswith("scanned 32 of 64 clusters (50.00% of the volume); 5 of them are image holes") and \
        "INCOMPLETE: bounded by --max-scan" in n, n


def _own_hole_clusters(path, end):
    """The test's own count of the whole clusters of [0, end) the file stores as holes (None: no hole query)."""
    fd = os.open(path, os.O_RDONLY)
    try:
        n, pos = 0, 0
        while pos < end * CS:
            try:
                a = os.lseek(fd, pos, os.SEEK_DATA)
            except OSError:
                a = end * CS
            n += max(0, (min(a, end * CS) - pos) // CS)
            if a >= end * CS:
                break
            pos = os.lseek(fd, a, os.SEEK_HOLE)
        return n
    except (OSError, AttributeError):
        return None
    finally:
        os.close(fd)


def test_wc2_scan_pages_counts_the_image_holes_it_read(tmp_path, capsys, monkeypatch):
    """WC-2: `--scan-pages`' coverage line over a sparse image counts the clusters it read from holes."""
    path = SC._image(tmp_path, {8: SC._page([(0x200, "early.txt")], listed=[0])})
    want = _own_hole_clusters(path, 64)
    if want is None:
        pytest.skip("this host answers no hole query")
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: SC.VSIG)
    with open(path, "rb") as f, UW.recording() as wrapped:
        F._scan_for_deleted_entries(f, 0, CS, None, set())
    cov = [l for l in UW.unwrap_exact(capsys.readouterr().out, wrapped).splitlines() if "Orphan-page scan: scanned" in l]
    assert want > 0 and cov == ["  Orphan-page scan: scanned 64 of 64 clusters (100% of the volume); " + str(want) +
                                " of them are image holes: no page can be read there"], (want, cov)


def test_wc2_a_host_without_a_hole_query_says_so(tmp_path, capsys, monkeypatch):
    path = SC._image(tmp_path, {8: SC._page([(0x200, "early.txt")], listed=[0])})
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: SC.VSIG)
    monkeypatch.setattr(F, "_hole_ranges_in", lambda fd, a, b: None)
    with open(path, "rb") as f, UW.recording() as wrapped:
        F._scan_for_deleted_entries(f, 0, CS, None, set())
    cov = [l for l in UW.unwrap_exact(capsys.readouterr().out, wrapped).splitlines() if "Orphan-page scan: scanned" in l]
    assert cov and cov[0].endswith("; whether any of them are image holes could not be checked on this host"), cov


def test_wc2_recovery_log_line_is_the_scans_line():
    """WC-2: the recovery log's coverage line is built from the same stats, the hole count included."""
    st = {"scanned_clusters": 100, "total_clusters": 100, "bounded": False, "hole_clusters": 7}
    assert F._scan_cov_line(st) == "scanned 100 of 100 clusters (100% of the volume); 7 of them are image holes: no " \
                                   "page can be read there"


# ═══ decision 50 -- the inline bytes of a live file's earlier row ════════════════════════════════════════════

def _resident_with_data(ct, fid, content):
    """A resident (embedded) file value whose $DATA is inline: $SI times at +0x28, size +0x58, file id at +0x80, and an
    embedded node at +0xA8 holding one single-instance $DATA row (key marker 0x80000001, type 0x80) in the resident
    form `get_resident_data_content` reads (0x0C/0x30 at +0x04, storage type 0 at +0x0C, size +0x1C, bytes +0x38)."""
    dv = bytearray(0x38 + len(content))
    struct.pack_into("<II", dv, 0x04, 0x0C, 0x30)
    struct.pack_into("<Q", dv, 0x1C, len(content))
    dv[0x38:] = content
    dk = struct.pack("<QIBB", 0, 0x80000001, 0x80, 0) + b"\0" * 2
    sub = _row(dk, bytes(dv))
    v = bytearray(0xA8 + 0x28 + len(sub) + 4)
    base, rows_at = 0xA8, 0x28
    struct.pack_into("<I", v, 0, base)
    struct.pack_into("<QQQQ", v, 0x28, ct, ct, ct, ct)
    struct.pack_into("<I", v, 0x48, 0x20)
    struct.pack_into("<QQ", v, 0x58, len(content), (len(content) + 7) & ~7)
    struct.pack_into("<Q", v, 0x80, fid)
    v[base + rows_at:base + rows_at + len(sub)] = sub
    arr_lo = rows_at + len(sub)
    struct.pack_into("<III", v, base + 0x10, arr_lo, 1, 0)
    struct.pack_into("<I", v, base + 0x20, arr_lo + 4)
    struct.pack_into("<HH", v, base + arr_lo, rows_at, 0xFFFF)
    _fx(F.get_resident_data_content(bytes(v), salvage=True) == content, "the planted value does not read inline")
    return bytes(v)


_OLD = b"decision 50: an earlier row of a live file holds these bytes inline. " * 2
_GONE = b"a deleted file's bytes, held inline in its row: written as they are. " * 2


def _d50_volume(tmp_path):
    """/d: a.txt live (resident, fid 5) and a STILL PRESENT copy of it in slack; /B: other.txt live (fid 6) and, in
    slack, zzz.txt with its ordinal and creation time (RENAMED, D1's control shape); gone.txt (fid 99) in /d's slack."""
    return _vol(tmp_path, {0x600: {"name": ""},
                           0x761: {"parent": 0x600, "name": "d",
                                   "files": [_row(_name_key("a.txt"), _resident_with_data(_T, 5, _OLD))],
                                   "slack": [_row(_name_key("a.txt"), _resident_with_data(_T, 5, _OLD)),
                                             _row(_name_key("gone.txt"), _resident_with_data(_T + 9 * _S, 99, _GONE))]},
                           0x762: {"parent": 0x600, "name": "B",
                                   "files": [_row(_name_key("other.txt"),
                                                  _resident_with_data(_T + 50 * _S, 6, _OLD))],
                                   "slack": [_row(_name_key("zzz.txt"),
                                                  _resident_with_data(_T + 50 * _S, 6, _OLD))]}})


@pytest.fixture
def d50(tmp_path):
    path = _d50_volume(tmp_path)
    out_dir = str(tmp_path / "exp")
    rc, out, err = D._syn(path, "export", "deleted", out_dir)
    with open(os.path.join(out_dir, "recovery_manifest.json")) as fh:
        recs = jdoc(json.load(fh), F._DELETED_MANIFEST_KEYS)["records"]                                          # K21 (acceptance 1.14.0)
    return {"rc": rc, "out": out, "err": err, "dir": out_dir, "recs": recs}


def _recs(d, name):
    r = [m for m in d["recs"] if m["name"] == name]
    _fx(r, "%s is not in the manifest" % name + D._ctx(d["rc"], d["out"], d["err"]))
    return r


@pytest.mark.parametrize("name,status", [("a.txt", "still present"), ("zzz.txt", "renamed")])
def test_d50_a_live_files_earlier_inline_bytes_are_not_written(d50, name, status):
    """Decision 50: the entry of a live file's earlier row (STILL PRESENT, RENAMED) is listed with the reason and its
    inline bytes are not written -- no content file; manifest `live_file_inline`, Reliability NONE, still resident."""
    for r in _recs(d50, name):
        assert r["status"] == status, r
        assert r["recoverable"] == "live_file_inline" and not r["content_file"] and r["reliability"] == "NONE", r
        # acceptance 1.14.0 (decision 37, N317): the manifest no longer writes is_resident -- RecoverabilityCode says it
    assert "not written: the same file is live" in r["verdict"], r
    assert not os.path.exists(os.path.join(d50["dir"], "content", name))


def test_d50_control_a_deleted_entrys_inline_bytes_are_written(d50):
    """Control: an entry whose file is not live keeps its inline bytes, written as they are (EXACT)."""
    r = _recs(d50, "gone.txt")
    assert r[0]["status"] not in ("still present", "renamed", "same file, other creation time"), r
    assert r[0]["recoverable"] == "recoverable_inline" and r[0]["reliability"] == "EXACT", r
    with open(os.path.join(d50["dir"], r[0]["content_file"]), "rb") as fh:
        assert fh.read() == _GONE


def test_d50_rollup_counts_the_held_back_bytes_apart(tmp_path):
    """Decision 50 (group 2, PLAN 10.2 E: the roll-up is the table now): a live file's inline rows are counted apart --
    starred, not written -- and `To recover:` counts only the bytes `export deleted` writes."""
    rc, out, err = D._syn(_d50_volume(tmp_path), "deleted")
    rows = {m.group(1): m.group(2).split() for m in re.finditer(r"^    (DELETED, OR RENAMED|DELETED|RENAMED|SAME FILE, OTHER CREATION TIME|STILL PRESENT)[^\d\n]*?((?:\s+\d+\*?){6})\s*$", out, re.M)}
    _fx(len(rows) == 5, "no table" + D._ctx(rc, out, err))
    plain = sum(int(c[0]) for c in rows.values() if not c[0].endswith("*"))
    starred = sum(int(c[0].rstrip("*")) for c in rows.values() if c[0].endswith("*"))
    assert plain == 1 and starred == 2 and rows["STILL PRESENT"][0] == "1*", rows
    assert "* the file is live: those bytes are not written; `extract` gives its current content" in out, out[-2500:]
    assert "To recover: `export deleted DIR` writes the 1 with bytes in the row (as found)." in out, out[-2500:]


# ═══ N472 -- the sparse file whose extent map is an index node; the streamed write ═══════════════════════════

def _n472_stubs(monkeypatch, sparse):
    """A record value (attributes +0x48, size +0x58, allocation +0x60) whose $DATA row's E86 map gives rows tiling 5
    allocated clusters of a 16-cluster file, the $DATA row's +0x30 = the logical size (DedupIndex.db's shape)."""
    kd = bytearray(0x18)
    struct.pack_into("<IHHI", kd, 8, 0x80000002, 0x80, 0, 0x1000)
    val = bytearray(0x100)
    struct.pack_into("<I", val, 0, 0x88)
    struct.pack_into("<Q", val, 0x30, 16 * CS)
    rows = [{"file_vcn": 0, "clusters": 2, "vlcn": 100, "flags": 0x50},
            {"file_vcn": 10, "clusters": 3, "vlcn": 200, "flags": 0x50}]
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None, **k: [(bytes(kd), bytes(val))])
    monkeypatch.setattr(F, "_extent_node_map", lambda *a, **k: [dict(r) for r in rows])
    vd = bytearray(0x100)
    struct.pack_into("<I", vd, 0x48, 0x220 if sparse else 0x20)
    struct.pack_into("<QQ", vd, 0x58, 16 * CS, 5 * CS)
    return bytes(vd)


def test_n472_a_sparse_map_that_tiles_its_allocation_is_accepted(monkeypatch):
    """N472: the rows tile the 5 allocated clusters at their logical positions; the gaps are holes (one complete map
    of the 16-cluster file), and `_decode_holder_extents` keeps that map as it is."""
    vd = _n472_stubs(monkeypatch, sparse=True)
    got = F._embedded_data_extents(vd, CS, (None, 0, CS, None))
    assert [(e["file_vcn"], e["clusters"], bool(e.get("is_hole"))) for e in got] == \
        [(0, 2, False), (2, 8, True), (10, 3, False), (13, 3, True)], got
    assert [(e["file_vcn"], e["plcn"]) for e in got if not e.get("is_hole")] == [(0, 100), (10, 200)]
    again = F._decode_holder_extents(vd, CS, None, (None, 0, CS, None))
    assert [(e["file_vcn"], e["clusters"]) for e in again] == [(e["file_vcn"], e["clusters"]) for e in got], again


def test_n472_control_the_same_map_without_the_sparse_attribute_is_refused(monkeypatch):
    vd = _n472_stubs(monkeypatch, sparse=False)
    assert F._embedded_data_extents(vd, CS, (None, 0, CS, None)) == []


def _stream_image(tmp_path, n=8):
    p = str(tmp_path / "img.raw")
    with open(p, "wb") as fh:
        for i in range(n):
            fh.write(bytes([0x41 + i]) * CS)
    return p


_SEXTS = [{"file_vcn": 0, "clusters": 2, "plcn": 2, "vlcn": 2, "flags": 0x50},
          {"file_vcn": 2, "clusters": 8, "plcn": 0, "vlcn": 0, "is_hole": True, "flags": 0x20},
          {"file_vcn": 10, "clusters": 1, "plcn": 5, "vlcn": 5, "flags": 0x50}]
_SWANT = bytes([0x43]) * CS + bytes([0x44]) * CS + b"\0" * 8 * CS + bytes([0x46]) * CS


def test_n472_streamed_write_is_the_in_memory_bytes_and_sparse_on_disk(tmp_path):
    """N472: `_StreamedContent` writes the bytes the in-memory path builds (data runs read, a hole as zeros) and, into
    a file, holds the hole as a hole (seek, not write)."""
    img = _stream_image(tmp_path)
    out = str(tmp_path / "out.bin")
    with open(img, "rb") as f, open(out, "wb") as o:
        sc = F._StreamedContent(f, 0, CS, _SEXTS, len(_SWANT))
        assert sc.write(o, sparse=True) == len(_SWANT) and not sc.unread
    assert open(out, "rb").read() == _SWANT
    with open(img, "rb") as f, open(str(tmp_path / "dense.bin"), "wb") as o:
        F._StreamedContent(f, 0, CS, _SEXTS, len(_SWANT)).write(o, sparse=False)
    assert open(str(tmp_path / "dense.bin"), "rb").read() == _SWANT


def test_n472_streamed_write_ends_at_a_failed_read_and_records_it(tmp_path, monkeypatch):
    """N472 / N380: a cluster that cannot be read ends the output there (unless --fill-holes) and is recorded; a read the
    image's end cuts short inside the planned length is never padded with zeros."""
    img = _stream_image(tmp_path)
    real = F._seek_read

    def sr(f, off, n):
        if off <= 5 * CS < off + n:
            raise OSError(5, "Input/output error")
        return real(f, off, n)
    monkeypatch.setattr(F, "_seek_read", sr)
    out = str(tmp_path / "out.bin")
    with open(img, "rb") as f, open(out, "wb") as o:
        sc = F._StreamedContent(f, 0, CS, _SEXTS, len(_SWANT))
        sc.write(o, sparse=True)
    assert sc.written == 10 * CS and sc.unread and sc.unread[0][0] == 10 * CS, (sc.written, sc.unread)
    assert open(out, "rb").read() == _SWANT[:10 * CS]
    monkeypatch.setattr(F, "_seek_read", real)
    short = _stream_image(tmp_path, n=5)                                       # cluster 5 is past this image's end
    with open(short, "rb") as f, open(out, "wb") as o:
        sc = F._StreamedContent(f, 0, CS, _SEXTS, len(_SWANT))
        sc.write(o, sparse=True)
    assert sc.written == 10 * CS and isinstance(sc.unread[0][1], EOFError), (sc.written, sc.unread)


DEDUP = "win11refs8gdedup.raw"
DEDUP_INDEX = "System Volume Information/NativeDedup/DedupIndex.db"


def test_n472_image_dedupindex_is_extracted_streamed_and_sparse(tmp_path):
    """N472 on its image: `extract` of DedupIndex.db (2,680,160,256 B, 3,080 clusters allocated) writes the whole file
    -- its size, sparse on disk, under 1 GiB of memory (1.14.0's D2: exit 2, nothing written; in memory it needs about
    5 GB) -- every data cluster the image's, every other byte zero (`fixes/D3_evidence/n472_verify.txt`). Exit 2: 405,504
    of its bytes lie in the image's holes (decision 23's statement and sidecar)."""
    img = _img(DEDUP)
    d = tempfile.mkdtemp(prefix="d3_n472_", dir=BI.SCRATCH if os.path.isdir(BI.SCRATCH) else None)
    try:
        outp = os.path.join(d, "dedupindex.db")
        before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss      # KiB, the peak of earlier children
        rc, out, err = _tool(img, "extract", DEDUP_INDEX, "-o", outp)
        rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        st = os.stat(outp)
        assert rc == 2 and st.st_size == 2680160256, (rc, st.st_size, err[-2000:])
        assert st.st_blocks * 512 < 64 << 20, st.st_blocks * 512
        if before < 1 << 20:                       # measurable only while no earlier child peaked above 1 GiB
            assert rss < 1 << 20, "extract peaked at %d KiB" % rss
        assert "of 2680160256 bytes of 'DedupIndex.db' were written from ranges the image stores as holes" in err, err
        with open(outp + ".holes.json") as fh:
            assert json.load(fh)["Status"] == "holes_present"           # K21 (1.14.0)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_n472_image_dataruns_decodes_every_extent_file_of_the_dedup_volume():
    """N472: `dataruns` on win11refs8gdedup decodes DedupIndex.db too (D2: "With decoded extents: 762" of 763)."""
    rc, out, err = _tool(_img(DEDUP), "dataruns")
    ext = int(re.search(r"Data in extents:\s+(\d+)", out).group(1))
    dec = int(re.search(r"With decoded extents:\s+(\d+)", out).group(1))
    assert rc in (0, 2) and ext == dec == 763, (rc, ext, dec)


# ═══ C3-1 (a) -- an earlier volume's pages ═══════════════════════════════════════════════════════════════════

def _tuple_page(cl, sig, rows=(("theirs.txt",),), at_home=True):
    p = bytearray(SC._page([(0x200 + 0x100 * i, r[0]) for i, r in enumerate(rows)], list(range(len(rows))), sig=sig))
    base = cl if at_home else cl + 0x40
    struct.pack_into("<4Q", p, 0x20, base, base + 1, base + 2, base + 3)
    return bytes(p)


def test_c31_a_page_counts_as_an_earlier_volumes_only_at_its_own_address():
    """C3-1 (a): the page's own LCN tuple (consecutive) names the cluster it lies at -- through the container table
    when there is one; text that merely starts with "MSB+" (win11bidule's forefst.py) and a page elsewhere fail."""
    assert F._page_at_own_address(_tuple_page(16, 0x99)[:0x40], 16, CS, None) is True
    assert F._page_at_own_address(_tuple_page(16, 0x99, at_home=False)[:0x40], 16, CS, None) is False
    text = b'MSB+"\nPAGE_TYPE_MLOG = "MLog"\nPAGE_TYPE_DATA = "' + b"x" * 0x20
    assert F._page_at_own_address(text[:0x40], 16, CS, None) is False


def _scan_said(tmp_path, monkeypatch, capsys, pages):
    path = SC._image(tmp_path, pages)
    monkeypatch.setattr(F, "_orphan_scan_bound", lambda f, ps, cs, m: (64, 64, False, None))
    monkeypatch.setattr(F, "volume_format_magic", lambda f, ps, cs, *_a, **_k: SC.VSIG)
    with open(path, "rb") as f, UW.recording() as wrapped:
        got = F._scan_for_deleted_entries(f, 0, CS, None, set())
    return got, [l for l in UW.unwrap_exact(capsys.readouterr().out, wrapped).splitlines()
                 if "Orphan-page scan:" in l and "signature" in l]


def test_c31_pages_at_their_own_address_are_an_earlier_volumes_formatted_again(tmp_path, monkeypatch, capsys):
    """C3-1 (a), decision 48's words: one signature at its own address = one earlier volume -- "1 earlier ReFS volume
    wrote pages here: the area was formatted again at least 1 time"; their rows are not listed as this volume's."""
    got, said = _scan_said(tmp_path, monkeypatch, capsys, {8: SC._named(SC._page([(0x200, "mine.txt")], [0]), 8),
                                                           16: _tuple_page(16, 0x99), 24: _tuple_page(24, 0x99)})
    assert [e["name"] for e in got] == ["mine.txt"], got
    assert len(said) == 1 and said[0].startswith("  Orphan-page scan: 1 earlier ReFS volume wrote pages here: the area "
                                                 "was formatted again at least 1 time (2 metadata page(s)"), said
    assert "0x99 on 2" in said[0] and "`deleted --earlier-volumes` lists them" in said[0], said


def test_c31_pages_elsewhere_are_never_counted_as_an_earlier_volume(tmp_path, monkeypatch, capsys):
    """C3-1 (a): pages with another signature that do not lie at the address they name (a deduplication index's own
    content: 838 such pages on two corpus volumes) are said apart and never called an earlier volume's."""
    got, said = _scan_said(tmp_path, monkeypatch, capsys, {16: _tuple_page(16, 0x77, at_home=False)})
    assert len(said) == 1 and "do not lie at the address they name, so they are not counted as an earlier volume's" \
        in said[0] and "formatted again" not in said[0] and "another volume's" not in said[0], said


def test_c31_image_labjjournal_earlier_volumes_lists_only_that_volumes_rows():
    """C3-1: `deleted --earlier-volumes` on labJjournal shows ONLY the earlier volume's entries (0x58407e6a, 17 pages
    at their own address): no section of this volume's, no status, the copies of one entry counted once; exit 0."""
    rc, out, err = _tool(_img("labJjournal.raw"), "deleted", "--earlier-volumes")
    assert rc == 0, err[-2000:]
    assert "1 earlier ReFS volume wrote pages here: the area was formatted again at least 1 time." in out, out
    assert "Earlier volume 0x58407e6a: 17 page(s) at their own address, 1 entry" in out, out
    assert re.search(r"Change Journal .*\(\+1 other copy, same times\); page owner 0x520 in that volume", out), out
    assert D.SLACK not in out and "STILL PRESENT" not in out and "DELETED" not in out, out


def test_c31_image_win11bidule_text_is_not_an_earlier_volume():
    """C3-1: win11bidule's one "page" with another signature is a source file's text (0x5f455059 = "YPE_"): `deleted
    --full` says it apart and claims no earlier volume."""
    rc, out, err = _tool(_img("win11bidule.raw"), "deleted", "--full")
    said = [l for l in out.splitlines() if "Orphan-page scan:" in l and "signature" in l]
    assert len(said) == 1 and "0x5f455059 on 1" in said[0] and "not counted as an earlier volume's" in said[0], said
    assert "a signature that is not this volume's" in said[0] and "another volume's" not in said[0], said
    assert "earlier ReFS volume" not in out, said


def test_c31_earlier_volumes_is_a_view_only(tmp_path):
    path = _d50_volume(tmp_path)
    rc, out, err = D._syn(path, "export", "deleted", str(tmp_path / "x"), "--earlier-volumes")
    assert rc == 1 and "--earlier-volumes is a view" in err, (rc, err[-1000:])
