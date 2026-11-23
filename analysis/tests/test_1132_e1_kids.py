"""E1 (1.14.0): wrong-verdict findings of the blind audit fixed in 1.13.0 without a test that names them; each test
here is RED on v1.12.3 (FOREFST_REPO=analysis/verification/versions/v1.12.3) and GREEN on the development tool.

K070: the $J stream's declared lengths (the Change Journal entry's stream row, value +0x30 / +0x38 / +0x40 / +0x48:
allocated size, size, valid data length, disk allocation) were never read, so shrinking them changed no output. On
step6/lab314_main.raw the four fields are at image offset 0x1e08848 (the audit's repro; inside the system metadata
table's root page, 0x1e08000), each 0x2000000, the extents' allocated size. The test shrinks size and VDL to 0x1000000
on a hole-preserving scratch copy and requires `usn --info` to name both as disagreeing with the allocated size.

K077: `timestomp` caught any exception from its journal read and went on with `journal = False`, so a journal that
could not be read printed as "absent (intrinsic signals only)" and exited 0: the corroboration was lost and nothing
said so. The test plants a read error in `read_usn_j_stream` in a real `timestomp` run on lab314_main (which has a
journal) and requires exit 2, the error named, and no "absent".

K075: `timestomp`'s journal corroboration was keyed by file NAME behind a uniqueness gate, so a backdate followed by
a rename, or a backdate of one of two live namesakes, lost its HIGH. The lab built for it, step7/labA_image1.raw
(its own action log, `LABA/log/laba_actions.csv`), holds both: A2 `beta_renamed.bin` and A3 `dir1/gamma.bin` must be
HIGH; A3's unstomped namesake `dir2/gamma.bin` must not be (measured in the plan v11 record of the fix: 1.12.3 gave
INFO, INFO, none).

K042: a checkpoint's allocator clock (+0x68, the log time of the allocator state it describes) above its own virtual
clock (+0x60), or a pair whose copy with the higher virtual clock carries the lower allocator clock, was never
flagged (`refsanalysis chkp --verify` printed both clocks and passed). On the bootstrap harness's volumes (synthetic
and a win11refsmini copy, `test_1132_red_a_bootstrap.vol`), the in-use copy's +0x68 is edited and re-sealed, so the
page verifies and is wrong only in the clock.

K059: `mlog --parse` / `--csv` and `timeline` dated a volume-information update (redo opcode 0x03) by the value's
+0x90, the volume's FORMAT time, before +0xA0, the time it was written, so those events sorted to the volume's birth
(23 on lab314_main_step3_dirty, all at its `Volume created`). The test gives `_mlog_extract_timestamp`, which both
commands use for the time of a record, an opcode-0x03 record whose value carries both times and requires the
written one.

K020: `export metadata` caught an I/O error in its MLog branch and went on (`except ...: pass`): the bundle lacked the
MLog log pages and their index with no manifest warning, exit 0, and `verify-bundle` passed it. The test plants an
OSError in `scan_mlog_data_area` during the export of win11refsmini (whose MLog is exported in full otherwise) and
requires the export to exit 2 and `verify-bundle` to fail the bundle, naming the failed MLog export.

K189: `verify-bundle`'s rehydrate-and-bootstrap check ran only when no other problem had been found, and passed a bundle
that rehydrates to a volume with no Object Table entry (bootstrap accepts an empty object map). The test exports
win11refsmini with `--what vbr,supb,chkp` (no metadata page; 1.12.3: "verify-bundle: PASS", exit 0, measured
2026-11-18) and requires the bundle to fail as empty, also when one seal line is altered (1.12.3 names the seal line
only).

K018: hole coverage has three states, holes present, none, and "this host cannot say", and the third was reported as
"none" on every content path but `extract`'s main loop: `--refuse-holes` wrote the stream and holes.json said none.
The test exports the 4 snapshot versions of step4/win11refs4gattributes.raw with os.SEEK_DATA / SEEK_HOLE removed in the
tool's process (1.12.3: exit 0, "none", the 4 streams written under --refuse-holes; measured 2026-11-18) and requires
"undeterminable", exit 2 and no stream written under --refuse-holes. N611 (found by it, 1.14.0): the refusal said the
bytes "would have come from image holes" when their coverage had not been checked.
"""
import os
import csv
import json
import re
import struct
import subprocess
import sys

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402

LAB314 = "step6/lab314_main.raw"
CAP = 400 << 20                                          # the base allocates about 205 MiB
J_LENGTHS = 0x1E08848                                    # alloc, size, VDL, disk allocation: four u64
J_ALLOC = 0x2000000

_MISMATCH = re.compile(r"\*\*\* MISMATCH: size, vdl disagree with the 33554432 bytes the extents allocate")


def test_k070_usn_info_reads_the_declared_lengths_of_j():
    with MC.scratch_copy(LAB314, CAP) as (src, p):
        MC._fx(MC._holes(p, J_LENGTHS, 32) == [], "the four length fields are a hole in the copy")
        MC._fx(struct.unpack_from("<4Q", MC.read_block(p, J_LENGTHS, 32)) == (J_ALLOC,) * 4,
               "the four declared lengths are not the audit's 0x2000000 each: not the row the audit read")
        with open(p, "r+b") as fh:
            fh.seek(J_LENGTHS + 8)
            fh.write(struct.pack("<2Q", 0x1000000, 0x1000000))      # size and VDL halved
        rc, text = MC.run_tool(MC.FOREFST, p, "usn", "--info")
    assert rc == 2 and _MISMATCH.search(text), \
        "size and VDL shrunk to 0x1000000: usn --info must say they disagree with the allocated size, exit 2" \
        + MC._ctx(rc, text[-3000:])


def test_k070_control_the_undamaged_volume():
    """The base itself (read only): exit 0, no mismatch (passes on v1.12.3 too)."""
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(LAB314), "usn", "--info")
    assert rc == 0 and "MISMATCH" not in text, "undamaged lab314_main" + MC._ctx(rc, text[-1500:])


_PLANTED_JOURNAL_READ = r"""
import sys
sys.path.insert(0, %r)
import forefst as F
def _fail(*a, **k):
    raise OSError("planted K077 read error")
F.read_usn_j_stream = _fail
sys.argv = ["forefst.py", %r, "timestomp"]
F.main()
"""


def test_k077_timestomp_says_the_journal_could_not_be_read():
    r = subprocess.run([sys.executable, "-B", "-c", _PLANTED_JOURNAL_READ % (REPO, MC.corpus(LAB314))],
                       capture_output=True, text=True, timeout=MC.TIMEOUT)
    text = r.stdout + "\n" + r.stderr
    MC._fx("Traceback (most recent call last)" not in r.stderr, "the tool crashed:\n" + r.stderr[-3000:])
    assert r.returncode == 2 and "planted K077 read error" in text \
        and not re.search(r"(?i)USN journal:\s+absent", text), \
        "a journal that could not be read: exit 2, the error named, never 'absent'" + MC._ctx(r.returncode, text[-3000:])


def test_k077_control_timestomp_reads_the_journal_of_lab314_main():
    """The same run without the planted error (passes on v1.12.3 too): the journal is read."""
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(LAB314), "timestomp")
    assert "planted" not in text and not re.search(r"(?i)USN journal:\s+(absent|unknown)", text), \
        "undamaged lab314_main: the journal is read" + MC._ctx(rc, text[-1500:])


LABA = "step7/labA_image1.raw"
vol = AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module


def _timestomp_tiers(tmp_path, rel):
    """{path: tier} from `timestomp --all --csv FILE` (every file, NONE included); the path and tier columns by name,
    either release's. Paths are volume paths without the leading separator (`LABA/dir1/gamma.bin`)."""
    dest = str(tmp_path / "ts.csv")
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(rel), "timestomp", "--all", "--csv", dest)
    MC._fx(os.path.isfile(dest), "timestomp wrote no CSV" + MC._ctx(rc, text[-1500:]))
    rows = list(csv.DictReader(open(dest, encoding="utf-8", newline="")))
    MC._fx(rows, "timestomp wrote an empty CSV")
    pk = [k for k in rows[0] if k.lower() in ("path", "fullpath")]
    tk = [k for k in rows[0] if k.lower() == "confidence"]
    MC._fx(len(pk) == 1 and len(tk) == 1, "no single path / confidence column in %r" % list(rows[0]))
    return {r[pk[0]].replace("\\", "/").lstrip("/"): r[tk[0]].upper() for r in rows}


def test_k075_timestomp_keeps_the_high_of_a_renamed_file_and_of_one_of_two_namesakes(tmp_path):
    t = _timestomp_tiers(tmp_path, LABA)
    names = ("LABA/dir1/beta_renamed.bin", "LABA/dir1/gamma.bin", "LABA/dir2/gamma.bin")
    got = {n: t.get(n, "(no row)") for n in names}
    MC._fx(all(v != "(no row)" for v in got.values()), "--all lists every file: a LAB-A file has no row %r" % got)
    assert got[names[0]] == "HIGH" and got[names[1]] == "HIGH" and got[names[2]] != "HIGH", \
        "LAB-A A2 / A3: the renamed backdate and the stomped namesake are HIGH, the other namesake is not: %r" % got


def _alloc_clock(value):
    def edit(b):
        struct.pack_into("<Q", b, 0x68, value)
    return edit


def test_k042_an_allocator_clock_ahead_of_the_virtual_clock_is_a_finding(vol):
    g = vol.geo
    vol.reseal(g.lo, _alloc_clock(AB.CLOCK_NEW + 617), AB.CHKP_DESC)
    rc, text = vol.run(AB.FOREFST, "summary")
    rc_ra, ra = vol.run(AB.REFSANALYSIS, "chkp", "-v", "--verify")
    assert rc == 2 and re.search(r"allocator clock %d is AHEAD of the virtual clock %d" % (AB.CLOCK_NEW + 617,
                                                                                         AB.CLOCK_NEW), text), \
        "summary: the in-use copy's allocator clock 681 above its virtual clock 64" + MC._ctx(rc, text[-2500:])
    assert rc_ra == 2 and re.search(r"\[FAIL\] Allocator clock %d is AHEAD" % (AB.CLOCK_NEW + 617), ra), \
        "refsanalysis chkp --verify" + MC._ctx(rc_ra, ra[-2500:])


def test_k042_an_inverted_checkpoint_pair_is_a_finding(vol):
    g = vol.geo
    vol.reseal(g.lo, _alloc_clock(AB.ALLOC_OLD - 1), AB.CHKP_DESC)    # the newer copy's allocator clock below the older's
    rc, text = vol.run(AB.FOREFST, "summary")
    assert rc == 2 and "the checkpoint pair is INVERTED" in text, \
        "summary: the copy with the higher virtual clock (64) carries the lower allocator clock" + MC._ctx(rc, text[-2500:])


def _filetime(y, mo, d, h, mi, sec):
    import datetime
    return int((datetime.datetime(y, mo, d, h, mi, sec) - datetime.datetime(1601, 1, 1)).total_seconds()) * 10 ** 7


def test_k059_a_volume_information_update_is_dated_when_it_was_written():
    sys.path.insert(0, REPO)
    import forefst as F
    formatted, written = _filetime(2026, 9, 6, 16, 17, 19), _filetime(2026, 9, 12, 17, 21, 28)
    vbase, v1_off, v1_len = 0x40, 0x80, 0xA8
    rec = bytearray(v1_off + v1_len)
    struct.pack_into("<II", rec, vbase + 8, v1_off, v1_len)            # the record's value 1: offset, length
    struct.pack_into("<Q", rec, v1_off + 0x90, formatted)              # the volume's format time
    struct.pack_into("<Q", rec, v1_off + 0xA0, written)                # the time this update was written
    got = F._mlog_extract_timestamp(bytes(rec), len(rec), 0x03, None, 2, vbase)
    assert got == written, "opcode 0x03: dated %r, want the written time %r (not the format time %r)" % (
        got, written, formatted)


MINI314 = "step1/win11refsmini.raw"

_PLANTED_MLOG_EXPORT = r"""
import sys
sys.path.insert(0, %r)
import forefst as F
def _fail(*a, **k):
    raise OSError("planted K020 read error")
F.scan_mlog_data_area = _fail
sys.argv = ["forefst.py", %r, "export", "metadata", "-o", %r]
F.main()
"""


def test_k020_a_failed_mlog_export_fails_the_bundle(tmp_path):
    b = str(tmp_path / "bundle")
    r = subprocess.run([sys.executable, "-B", "-c", _PLANTED_MLOG_EXPORT % (REPO, MC.corpus(MINI314), b)],
                       capture_output=True, text=True, timeout=MC.TIMEOUT)
    MC._fx("Traceback (most recent call last)" not in r.stderr, "the export crashed:\n" + r.stderr[-3000:])
    MC._fx(os.path.isdir(b), "the export wrote no bundle" + MC._ctx(r.returncode, (r.stdout + r.stderr)[-1500:]))
    rc_v, v = MC.run_tool(MC.FOREFST, b, "verify-bundle")
    assert r.returncode == 2, "the export whose MLog branch failed must exit 2" + MC._ctx(r.returncode, r.stderr[-2000:])
    assert rc_v not in (0, None) and re.search(r"(?i)export FAILED.*mlog|mlog.*export FAILED", v) \
        and not re.search(r"verify-bundle: PASS", v), \
        "verify-bundle must fail the bundle and name the failed MLog export" + MC._ctx(rc_v, v[-2500:])


def test_k020_control_the_bundle_of_win11refsmini_passes(tmp_path):
    """The same export without the planted error (passes on v1.12.3 too): the bundle verifies."""
    b = str(tmp_path / "bundle")
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(MINI314), "export", "metadata", "-o", b)
    rc_v, v = MC.run_tool(MC.FOREFST, b, "verify-bundle")
    assert rc == 0 and rc_v == 0 and os.path.isfile(os.path.join(b, "mlog_log_pages.bin")), \
        "export rc %s, verify-bundle rc %s" % (rc, rc_v) + MC._ctx(rc_v, v[-1500:])


_EMPTY = re.compile(r"bootstraps but is EMPTY \(0 object-table entries")


def _bootstrap_only_bundle(tmp_path):
    """`export metadata --what vbr,supb,chkp` of win11refsmini: a bundle carrying the boot sector, superblock and
    checkpoint copies and no metadata page (no Object Table, no Container Table)."""
    b = str(tmp_path / "bundle")
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(MINI314), "export", "metadata", "-o", b, "--what", "vbr,supb,chkp")
    MC._fx(rc == 0 and os.path.isfile(os.path.join(b, "sha256sums.txt")), "the export wrote no bundle"
           + MC._ctx(rc, text[-1500:]))
    MC._fx(not [n for n in os.listdir(b) if n.startswith("metadata_pages")], "the bundle carries metadata pages")
    return b


def test_k189_a_bundle_with_no_metadata_pages_does_not_pass(tmp_path):
    b = _bootstrap_only_bundle(tmp_path)
    rc, v = MC.run_tool(MC.FOREFST, b, "verify-bundle")
    assert rc == 2 and _EMPTY.search(v) and "verify-bundle: PASS" not in v, \
        "a bundle that rehydrates to an empty volume is not whole" + MC._ctx(rc, v[-2500:])


def test_k189_the_rehydrate_check_runs_beside_another_problem(tmp_path):
    """One seal line altered (the backup boot sector's recorded hash): the bundle fails on it, and the rehydrate check
    still runs and names the empty volume."""
    b = _bootstrap_only_bundle(tmp_path)
    p = os.path.join(b, "sha256sums.txt")
    lines = open(p, encoding="utf-8").read().splitlines(True)
    i = [k for k, ln in enumerate(lines) if ln.rstrip().endswith("vbr_backup.bin")]
    MC._fx(len(i) == 1, "no single seal line for vbr_backup.bin")
    lines[i[0]] = ("0" if lines[i[0]][0] != "0" else "1") + lines[i[0]][1:]
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("".join(lines))
    rc, v = MC.run_tool(MC.FOREFST, b, "verify-bundle")
    MC._fx(re.search(r"vbr_backup\.bin: content does not match its recorded hash", v), "the altered seal line is not "
           "named: not the case under test" + MC._ctx(rc, v[-2500:]))
    assert rc == 2 and _EMPTY.search(v), \
        "the rehydrate check must run when another problem is found, and name the empty volume" + MC._ctx(rc, v[-2500:])


SNAP = "step4/win11refs4gattributes.raw"                 # 2 files with snapshot versions: 4 version streams
_SIDECARS = ("holes.json", "export_index.csv")

_NO_HOLE_QUERY = r"""
import os, sys
sys.path.insert(0, %r)
import forefst as F
for _n in ("SEEK_DATA", "SEEK_HOLE"):
    if hasattr(os, _n):
        delattr(os, _n)
sys.argv = ["forefst.py", %r] + %r
F.main()
"""


def _export_snapshots(tmp_path, *extra, hole_query=True):
    """(rc, text, {holes.json, keys lowercased without '_'}, [version files written]) of `export snapshots DIR`; with
    hole_query=False, os.SEEK_DATA / SEEK_HOLE are removed in the tool's process (a host that cannot answer)."""
    out = str(tmp_path / "snaps")
    if hole_query:
        rc, text = MC.run_tool(MC.FOREFST, MC.corpus(SNAP), "export", "snapshots", out, *extra)
    else:
        r = subprocess.run([sys.executable, "-B", "-c",
                            _NO_HOLE_QUERY % (REPO, MC.corpus(SNAP), ["export", "snapshots", out] + list(extra))],
                           capture_output=True, text=True, timeout=MC.TIMEOUT)
        rc, text = r.returncode, r.stdout + "\n" + r.stderr
        MC._fx("Traceback (most recent call last)" not in r.stderr, "the tool crashed:\n" + r.stderr[-3000:])
    hp = os.path.join(out, "holes.json")
    MC._fx(os.path.isfile(hp), "no holes.json" + MC._ctx(rc, text[-1500:]))
    doc = {k.lower().replace("_", ""): v for k, v in json.load(open(hp, encoding="utf-8")).items()}
    files = sorted(n for n in os.listdir(out) if n not in _SIDECARS)
    return rc, text, doc, files


def test_k018_control_export_snapshots_is_checked_and_clean(tmp_path):
    """The host answers the hole query (passes on v1.12.3 too): 4 version streams, holes.json 'none', exit 0."""
    rc, text, doc, files = _export_snapshots(tmp_path)
    assert rc == 0 and doc.get("status") == "none" and len(files) == 4, \
        "rc %s, status %r, %d file(s)" % (rc, doc.get("status"), len(files)) + MC._ctx(rc, text[-1500:])


def test_k018_unchecked_hole_coverage_is_not_none(tmp_path):
    rc, text, doc, files = _export_snapshots(tmp_path, hole_query=False)
    assert rc == 2 and doc.get("status") == "undeterminable" and doc.get("streamsundeterminable") == len(files) == 4, \
        "coverage not checked: holes.json must say 'undeterminable' for the 4 streams and the export exit 2; got rc " \
        "%s, %r" % (rc, {k: doc.get(k) for k in ("status", "streamsundeterminable")}) + MC._ctx(rc, text[-1500:])


def test_k018_n611_refuse_holes_withholds_unchecked_streams_and_says_why(tmp_path):
    """K018: --refuse-holes writes no stream whose coverage could not be checked. N611: the refusal says why -- the
    coverage was not checked -- not that the bytes would have come from image holes (none was found)."""
    rc, text, doc, files = _export_snapshots(tmp_path, "--refuse-holes", hole_query=False)
    assert rc == 2 and not files and len(doc.get("refused") or []) == 4, \
        "--refuse-holes over unchecked coverage: nothing written, 4 refused, exit 2; got rc %s, files %r" % (rc, files) \
        + MC._ctx(rc, text[-1500:])
    assert re.search(r"4 output stream\(s\) were NOT written because their hole coverage could not be checked", text) \
        and "would have come from image holes" not in text, \
        "the refusal must give its cause" + MC._ctx(rc, text[-1500:])
