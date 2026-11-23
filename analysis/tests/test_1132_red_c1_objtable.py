"""1.13.2 (ships as 1.14.0) RED cases, wave C step C1, area `objtable`: B2, N358, N427, N445 (a), (d), (e).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (settlements Q8, Q10, Q11), `fixes/WAVEC_INVENTORY.md` and
`fixes/WAVEC_CENSUS.md` (the item rows), `fixes/WAVEC_READING_bootstrap.md` section 4.3 (closure table B-4.3: the
Object-Table root -> duplicate), `fixes/LATER_GROUPS_TOLD.md` "Added 2026-10-21 -- wave B closed" (C-2: the A4 plant of
test_1132_red_waveb_mlog.py punches the duplicate root too, applied before these REDs), RUNNING_LOG N358 / N427 / N445.
Report, with the failure line of every node observed on the current tree: `analysis/reports/v1.13.2/fixes/RED_C1.md`.

  B2    (Q8; B-4.3; decision 1, 39) the Object Table's duplicate root -- the other root of the checkpoint pair
        {roots[0], roots[5]}; on step1/win11refsmini root 5, table id 0x04, PLCN 0x3400 -- is read only when the
        primary's root page fails its digest (the checkpoint's root 0 reference) or cannot be read; the note names the
        failed primary (its PLCN), exit 2. Both fail: LB68's statement ("the Object Table could not be read") names both
        roots, exit 2. Controls: an undamaged volume and a volume whose duplicate alone is punched read the primary,
        output as on the undamaged volume.
  N358  (Q11) a reader that finds an OID missing from an Object Table read IN PART says "not determined: the Object
        Table was read in part" (security, `files`' security map, `reparse --index`, the journal lookup, the
        $VOLUME_INFORMATION read, the Trash Table, ra `oid30`, the volume label), never an absence; exit unchanged (2).
  N427  (Q10) a required structure absent from an Object Table read IN FULL (or a checkpoint root the command needs)
        is a finding: exit 2, not 1 (`security`, `reparse`, `dataruns`, ra `upcase`, ra `schema`); over a table read in
        part it is "not determined" (fd `details`, fd `reparse`, ra `parentchild --verify` one table down).
  N445  (a) `usn --info` and `export metadata` over an Object Table that could not be read state no absent journal;
        (d) `_usn_resolve_path`'s "the directory is gone" label `<oid 0x..>` is not given over a map read in part;
        (e) `object_table_read_state` has its `single_source.tsv` row.

Fixtures (each checks its premise; the images are read-only; a planted copy is a hole-preserving scratch copy under
$FOREFST_RED_SCRATCH, deleted by its exact path):
  * B2: scratch copies of step1/win11refsmini with the primary root page (0x1C08000-0x1C0C000) an image hole, or one
    byte of its free space flipped (written data: the page reads, its CRC64 no longer matches the checkpoint's root 0
    reference), or the duplicate's page (0x4400000-0x4404000) a hole, or both.
  * PARTIAL (N358, N427, N445): step3b/win11refs2tmillionsofactionsv2, whose Object Table is a root over 5 leaves; in
    the tool's process the four clusters of the leaf at PLCN 0x424 read as zeros (the GBb critic's C-8 fixture,
    `GBb_critic_evidence/rerun_2026-10-21/scripts/partial_leaf.py`): 404 of 512 objects are read, every system OID
    (0x7-0xA, 0xD, 0x30, 0x500, 0x501, 0x520, 0x530, 0x540, 0x541, 0x600, 0x701) is on the unread leaf. The image is
    not modified: a driver script patches the tool's `_seek_read` and runs the real CLI (`main()` / refsanalysis's
    `__main__`) in its own process, with the real exit rule.
  * ABSENT (N427): step1/win11refsmini in the same driver, with OIDs removed from the object map bootstrap builds (the
    walk read the whole table: `object_table_read_state` stays None) -- an Object Table that holds no such row.
  * NONE (N445 (a)): the C-2 shape, both Object-Table roots of step1/win11refsmini image holes.

Conventions (those of test_1132_red_a_bootstrap.py / test_1132_red_mlog_chkp.py, whose helpers are imported): every RED
is ``xfail(strict=True, raises=AssertionError)`` and fails at a plain ``assert``; a fixture problem is RedFixtureError
and a broken kept property KeptPropertyBroken (both FAIL the node). Wordings that are not settled are matched as
properties: "not determined" (Q11's words) with the table and its read state; a finding as exit 2 plus a line that
names the structure.
"""
import contextlib
import csv
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                                # noqa: E402  (K21: internal names)
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions, synthetic volume, reseal)
import test_1132_red_mlog_chkp as MC                     # noqa: E402  (corpus paths, scratch copies, holes)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
FOREFST, REFSANALYSIS = AB.FOREFST, AB.REFSANALYSIS
TIMEOUT = 1800


def _red(item, why):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason="RED 1.13.2 %s: %s" % (item, why))


def _lcn_re(lcn):
    return re.compile(r"(?i)(?<![0-9a-z])0x0*%x(?![0-9a-z])" % lcn)


def _ctx(rc, out, err=""):
    return "\n| rc=%s\n| stdout: %s\n| stderr: %s" % (rc, out[-2500:], err[-2500:])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Runners
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def run_cli(tool, image, *args, cwd=None):
    """(rc, stdout, stderr) of the real CLI. A traceback or a timeout is a fixture error."""
    cmd = [sys.executable, "-B", tool, image] + list(args)
    try:
        r = UW.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=cwd or REPO,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


# The driver runs ONE tool process with the plant applied in that process; everything else is the real code:
#   zero   clusters (volume LCNs) every read through forefst's `_seek_read` returns as zeros;
#   edit   [lcn, offset in the cluster, hex bytes]: bytes replaced when read;
#   drop   OIDs removed from the object map of the in-use Object Table (the first `build_object_map(register=True)`);
#   reref  OIDs whose root-page digest in the tool's register (`_OBJ_ROOT_REF`) is recomputed from the (edited) bytes,
#          as an Object Table resealed after the edit would record it.
# The partition offset and the cluster size are taken from the tool's own `parse_vbr` call.
DRIVER = r'''
import json, runpy, sys
REPO, TOOL, SPEC = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, REPO)
import forefst as F
spec = json.load(open(SPEC))
zero = set(spec.get("zero", []))
edits = {}
for lcn, off, hx in spec.get("edit", []):
    edits.setdefault(lcn, []).append((off, bytes.fromhex(hx)))
drop, reref, geo, state = set(spec.get("drop", [])), spec.get("reref", []), {}, {"done": False}
_vbr = F.parse_vbr
def parse_vbr(f, ps, *a, **k):
    r = _vbr(f, ps, *a, **k)
    geo.setdefault("ps", ps)
    geo.setdefault("cs", r[0])
    return r
F.parse_vbr = parse_vbr
_rd = F._seek_read
def _seek_read(f, off, n):
    data = _rd(f, off, n)
    ps, cs = geo.get("ps"), geo.get("cs")
    if ps is None or off < ps or not (zero or edits) or not data:
        return data
    first, last = (off - ps) // cs, (off - ps + len(data) - 1) // cs
    if not any(c in zero or c in edits for c in range(first, last + 1)):
        return data
    b = bytearray(data)
    for c in range(first, last + 1):
        lo, hi = max(0, ps + c * cs - off), min(len(b), ps + (c + 1) * cs - off)
        if c in zero:
            b[lo:hi] = bytes(hi - lo)
        for eo, eb in edits.get(c, ()):
            p = ps + c * cs + eo - off
            if 0 <= p and p + len(eb) <= len(b):
                b[p:p + len(eb)] = eb
    return bytes(b)
F._seek_read = _seek_read
_bom = F.build_object_map
def build_object_map(f, ps, cs, tr, ot, register=True):
    m = _bom(f, ps, cs, tr, ot, register)
    if register and not state["done"]:
        state["done"] = True
        for o in drop:
            m.pop(o, None)
        for o in reref:
            if o in m:
                pg = b"".join(F._seek_read(f, ps + tr.tr(v) * cs, cs) for v in m[o])
                F._OBJ_ROOT_REF[o] = (8, F.refs_crc64(pg).to_bytes(8, "little"))
    return m
F.build_object_map = build_object_map
sys.argv = [TOOL] + sys.argv[4:]
if TOOL.endswith("refsanalysis.py"):
    runpy.run_path(TOOL, run_name="__main__")
else:
    try:
        rc = F.main()
        rc = F.rc_escalate(0 if rc is None else rc)
    except SystemExit as e:
        c = 0 if e.code is None else e.code
        rc = F.rc_escalate(c) if isinstance(c, int) else 1
    sys.exit(rc)
'''


def run_planted(tmp_path, tool, image, args, spec):
    """(rc, stdout, stderr) of `tool image args` in one process of its own with the plant `spec` applied (DRIVER)."""
    drv, sp = tmp_path / "c1_driver.py", tmp_path / "c1_spec.json"
    drv.write_text(DRIVER)
    sp.write_text(json.dumps(spec))
    cmd = [sys.executable, "-B", str(drv), REPO, tool, str(sp), image] + list(args)
    try:
        r = UW.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=REPO,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


@contextlib.contextmanager
def planted_copy(rel, holes=(), flips=(), max_alloc=64 << 20):
    """A hole-preserving scratch copy of a corpus image: each [a, b) of `holes` left as an image hole, each byte offset
    of `flips` XORed with 0x01 (written data). Every plant is read back."""
    with MC.scratch_copy(rel, max_alloc, omit=list(holes) or None) as (_src, p):
        for a, b in holes:
            _fx(MC.read_block(p, a, b - a) == bytes(b - a) and not MC.data_ranges(p, a, b),
                "0x%x-0x%x is not an image hole of the copy" % (a, b))
        for off in flips:
            before = MC.read_block(p, off, 1)
            with open(p, "r+b") as fh:
                fh.seek(off)
                fh.write(bytes([before[0] ^ 0x01]))
            _fx(MC.read_block(p, off, 1) != before and MC.data_ranges(p, off, off + 1),
                "the flip at 0x%x did not land as written data" % off)
        yield p


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Shared matchers (also used by test_1132_red_c1_mlog.py)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_NOT_DET = re.compile(r"(?i)\bnot\s+determined\b")
_READ_STATE = re.compile(r"(?i)\bread\s+in\s+part\b|\bnot\s+(?:be\s+)?read\s+in\s+full\b|\bcould\s+not\s+be\s+read\b"
                         r"|\bwas\s+not\s+read\b|\bunread\b")


def undetermined_lines(text, table=r"Object\s+Table", also=None):
    """Lines that say Q11's "not determined", name `table` and its read state (read in part / could not be read),
    and match `also` when given."""
    t = re.compile(r"(?i)\b" + table + r"\b")
    a = re.compile(also) if isinstance(also, str) else also
    return [ln for ln in text.splitlines()
            if _NOT_DET.search(ln) and t.search(ln) and _READ_STATE.search(ln) and (a is None or a.search(ln))]


def test_c1_matcher_undetermined_lines_accepts_the_settled_words_and_rejects_absences():
    """Not a RED. The matcher accepts Q11's wording and rejects the current absence statements."""
    ok = "security descriptors: not determined: the Object Table was read in part (1 page could not be read)"
    assert undetermined_lines(ok) and undetermined_lines(ok, also=r"(?i)security")
    assert undetermined_lines("OID 0x30: not determined -- the Object Table could not be read in full")
    for bad in ("  OID 0x30: NOT PRESENT", "  (OID 0x520 absent — journal not activated)",
                "ERROR: OID 0x530 (Security Descriptor Stream) not found in Object Table",
                "not determined", "the Object Table was read in part"):
        assert not undetermined_lines(bad), bad


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B2 -- the Object Table's duplicate root (B-4.3)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The driver (WAVEC_READING_bootstrap O1-O6, read once, internals text only): roots[0] and roots[5] are one failover
# pair; refs.sys opens both and works from the duplicate when the primary's open fails with a corruption status
# (0xC00001A8), repairing it on a writable mount. Measured here (fixture premises, below): on step1/win11refsmini the
# two roots' tables hold the same 24 objects; root 0 (PLCN 0xc08) and root 5 (PLCN 0x3400) each match the CRC64 the
# checkpoint copy in use records for them.

BASE = "step1/win11refsmini.raw"
B2_PS = 0x1000000
B2_PRI, B2_DUP = 0xC08, 0x3400                    # PLCN of roots[0] and roots[5] (16 KiB pages)
B2_PRI_HOLE = (B2_PS + B2_PRI * 0x1000, B2_PS + B2_PRI * 0x1000 + 0x4000)
B2_DUP_HOLE = (B2_PS + B2_DUP * 0x1000, B2_PS + B2_DUP * 0x1000 + 0x4000)
B2_FLIP = B2_PRI_HOLE[0] + 0x2000                 # inside the page's free space (zeros 0xd81-0x3fa0 on this image)
_B2_RUNS = {}


def _chkp_root_ref(img, idx):
    """(slots, checksum type, digest bytes) of root `idx` in the checkpoint copy in use (the higher +0x60 of the two
    that the primary superblock lists), read by this module."""
    with open(img, "rb") as fh:
        fh.seek(B2_PS + 0x1E * 0x1000)
        sb = fh.read(0x1000)
        best = None
        for lcn in (F.le64(sb, 0xC0), F.le64(sb, 0xC8)):
            fh.seek(B2_PS + lcn * 0x1000)
            c = fh.read(0x1000)
            if c[:4] == b"CHKP" and (best is None or F.le64(c, 0x60) > F.le64(best, 0x60)):
                best = c
    _fx(best is not None, "no checkpoint copy read")
    olb = F.le32(best, 0x94) if F.le32(best, 0x78) & 0x200 else 0x94
    ro, dl = F.le32(best, olb + 4 * idx), F.le32(best, 0x5C)
    rec = best[ro:ro + dl]
    slots = [s for s in (F.le64(rec, 8 * i) for i in range(4)) if s not in (0, 0xFFFFFFFFFFFFFFFF)]
    return slots, rec[0x22], bytes(rec[0x28:0x28 + F.le32(rec, 0x24)])


def _b2_premise(img):
    """The pair as this module reads it: root 0 and root 5 at the PLCNs above, MSB+ with table ids 0x02 / 0x04, each
    page matching the CRC64 its checkpoint reference records."""
    for idx, plcn, tid in ((0, B2_PRI, 0x02), (5, B2_DUP, 0x04)):
        slots, ck, digest = _chkp_root_ref(img, idx)
        with open(img, "rb") as fh:
            fh.seek(B2_PS + plcn * 0x1000)
            pg = fh.read(0x4000)
        _fx(ck == 2 and len(digest) == 8 and pg[:4] == b"MSB+" and F.le64(pg, 0x48) == tid,
            "root %d: checksum type %r, signature %r, table id 0x%x" % (idx, ck, pg[:4], F.le64(pg, 0x48)))
        _fx(F.refs_crc64(pg) == F.le64(digest, 0), "root %d (PLCN 0x%x) does not match its checkpoint digest" % (idx, plcn))
        _fx(slots and (slots[0] & 0xFFFF) == (plcn & 0xFFFF), "root %d's reference names 0x%x" % (idx, slots[0]))


def _base_files():
    """`files --csv` on the undamaged base, once per process."""
    if "base" not in _B2_RUNS:
        img = MC.corpus(BASE)
        _b2_premise(img)
        _B2_RUNS["base"] = run_cli(FOREFST, img, "files", "--csv")
    rc, out, err = _B2_RUNS["base"]
    rows = list(csv.reader(io.StringIO(out)))
    _fx(rc == 0 and len(rows) == 21, "the undamaged base: files --csv rc %s, %d lines" % (rc, len(rows)))
    return rows


def _names_the_object_table(text, *lcns):
    """Lines that name the Object Table ("Object Table" or "Object-Table", critic O-1: the plan's own spelling of the
    root is "Object-Table root") and every PLCN of `lcns`."""
    return [ln for ln in text.splitlines()
            if re.search(r"(?i)\bObject[\s-]+Table\b", ln) and all(_lcn_re(x).search(ln) for x in lcns)]


def test_b2_control_the_undamaged_volume_reads_the_primary_and_says_nothing_of_a_duplicate():
    """Not a RED. The base: exit 0, its 20 files, no line that names the Object Table with either root's PLCN."""
    rows = _base_files()
    rc, out, err = _B2_RUNS["base"]
    _keep(len(rows) == 21 and not _names_the_object_table(out + err, B2_PRI)
          and not _names_the_object_table(out + err, B2_DUP), "the base: %d rows" % len(rows) + _ctx(rc, out, err))


def test_b2_control_a_duplicate_root_that_is_a_hole_changes_nothing():
    """Not a RED. The duplicate is read only when the primary fails (Q8): with the duplicate's page an image hole and
    the primary sound, `files --csv` is the base's, exit 0, and no line names the duplicate."""
    base = _base_files()
    with planted_copy(BASE, holes=[B2_DUP_HOLE]) as p:
        rc, out, err = run_cli(FOREFST, p, "files", "--csv")
    _keep(rc == 0 and list(csv.reader(io.StringIO(out))) == base and not _lcn_re(B2_DUP).search(out + err),
          "a hole in the duplicate root changed the output" + _ctx(rc, out, err))


# RED 1.13.2 B2: a primary Object-Table root in an image hole is not read from the duplicate root (root 5, PLCN 0x3400) -- green with wave C step C1's fix (the strict xfail mark removed)
def test_b2_a_primary_root_in_an_image_hole_is_read_from_the_duplicate_on_image_win11refsmini():
    base = _base_files()
    with planted_copy(BASE, holes=[B2_PRI_HOLE]) as p:
        rc, out, err = run_cli(FOREFST, p, "files", "--csv")
    rows = list(csv.reader(io.StringIO(out)))
    said = _names_the_object_table(out + "\n" + err, B2_PRI)
    assert rows == base and rc == 2 and said, "the primary root page (PLCN 0xc08) is an image hole and the duplicate " \
        "(root 5, PLCN 0x3400) holds the same Object Table: `files --csv` must list the base's %d rows (%d listed), " \
        "exit 2 (exit %s) and name the failed primary's PLCN in a line about the Object Table (%d such line(s); Q8)" \
        % (len(base) - 1, max(0, len(rows) - 1), rc, len(said)) + _ctx(rc, out[-600:], err)


# RED 1.13.2 B2: a primary Object-Table root that fails its checkpoint digest is read and trusted, nothing said, exit 0 -- green with wave C step C1's fix (the strict xfail mark removed)
def test_b2_a_primary_root_that_fails_its_digest_is_read_from_the_duplicate_on_image_win11refsmini():
    base = _base_files()
    with planted_copy(BASE, flips=[B2_FLIP]) as p:
        slots, _ck, digest = _chkp_root_ref(p, 0)
        pg = MC.read_block(p, B2_PRI_HOLE[0], 0x4000)
        _fx(pg[:4] == b"MSB+" and F.refs_crc64(pg) != F.le64(digest, 0),
            "the flipped primary page still matches its checkpoint digest")
        rc, out, err = run_cli(FOREFST, p, "files", "--csv")
    rows = list(csv.reader(io.StringIO(out)))
    said = _names_the_object_table(out + "\n" + err, B2_PRI)
    assert rows == base and rc == 2 and said, "the primary root page (PLCN 0xc08) no longer matches the CRC64 the " \
        "checkpoint records for root 0: the Object Table is read from the duplicate (root 5) -- the base's rows " \
        "(%s), exit 2 (exit %s), a line about the Object Table naming the failed primary's PLCN (%d line(s); Q8)" \
        % ("equal" if rows == base else "differ", rc, len(said)) + _ctx(rc, out[-600:], err)


# RED 1.13.2 B2: with the primary root unread, the Object Table (and the MLog through it) is not read from the duplicate -- green with wave C step C1's fix (the strict xfail mark removed)
def test_b2_primary_unread_duplicate_read_in_full_the_mlog_is_located_on_image_win11refsmini():
    """LATER_GROUPS_TOLD C-2: B2's own node for "primary unread, duplicate read in full". The Logfile Information Table
    (OID 0x9 / 0xA) is found through the duplicate's map, so `mlog --stats` shows the control area as on the base
    (control copy PLCN 0x8001 in use) and never LB68's "the Object Table could not be read"."""
    with planted_copy(BASE, holes=[B2_PRI_HOLE]) as p:
        rc, out, err = run_cli(FOREFST, p, "mlog", "--stats")
    # critic O-3: LB68's consequence (the log not looked up / not located), not the words "Object Table could not be
    # read", which B2's own note about the failed primary may use
    unread = re.search(r"(?i)could\s+not\s+be\s+looked\s+up|no\s+log\s+record\s+can\s+be\s+located", out + err)
    located = re.search(r"(?im)^\s*Control PLCN:\s+0x8001\b", out)
    assert located and not unread and rc == 2, "the duplicate root's map holds OID 0x9 and 0xA: `mlog --stats` must " \
        "locate the log through it (control PLCN 0x8001: %s), not state LB68's outcome (the log could not be looked " \
        "up / no log record located: %s), and " \
        "exit 2 for the failed primary (exit %s)" % (bool(located), bool(unread), rc) + _ctx(rc, out[:1500], err)


# RED 1.13.2 B2: bootstrap's object map is empty (state 'none') when only the primary Object-Table root is unreadable -- green with wave C step C1's fix (the strict xfail mark removed)
def test_b2_bootstrap_maps_the_duplicates_objects_and_its_read_state_is_the_duplicates(monkeypatch):
    """In-process: `bootstrap` on the primary-hole copy returns the base's 24 objects, and `object_table_read_state`
    describes the walk whose map is used (the duplicate's, read in full: None). Every run register fresh and restored."""
    import test_1132_red_waveb_rest as WR
    WR._n425_fresh(monkeypatch)
    for name in ("_OBJ_ROOT_REF", "_OBJ_ROOT_LCNS"):
        monkeypatch.setattr(F, name, {})
    monkeypatch.setattr(F, "_OBJ_ROOT_VERIFIED", set())
    img = MC.corpus(BASE)
    f0, ps0, cs0, tr0, roots0, om0, *_r = F.bootstrap(img, None)
    f0.close()
    _fx(len(om0) == 24 and F.object_table_read_state(om0) is None, "the base map: %d objects" % len(om0))
    with planted_copy(BASE, holes=[B2_PRI_HOLE]) as p:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            f, ps, cs, tr, roots, om, *_r = F.bootstrap(p, None)
        f.close()
    assert dict(om) == dict(om0) and F.object_table_read_state(om) is None, "the primary root is a hole and the " \
        "duplicate holds the same table: bootstrap's map has %d objects (the base: 24) and read state %r (the " \
        "duplicate's walk, read in full: None)" % (len(om), F.object_table_read_state(om))


# RED 1.13.2 B2: with both Object-Table roots unreadable, no statement names both roots (0xc08 and 0x3400) -- green with wave C step C1's fix (the strict xfail mark removed)
def test_b2_neither_root_readable_is_stated_naming_both_roots_on_image_win11refsmini():
    """Q8: both fail -- LB68's statement ("the Object Table could not be read") naming both roots, exit 2."""
    with planted_copy(BASE, holes=[B2_PRI_HOLE, B2_DUP_HOLE]) as p:
        rc, out, err = run_cli(FOREFST, p, "files", "--csv")
    # critic O-2: B-4.3 row 3's own words ("neither copy could be read") are accepted too
    both = [ln for ln in _names_the_object_table(out + "\n" + err, B2_PRI, B2_DUP)
            if re.search(r"(?i)could\s+not\s+be\s+read|unreadable|cannot\s+be\s+read|not\s+readable"
                         r"|\bneither\b[^.]*\b(?:could|can)\s+be\s+read|\bfail", ln)]
    assert rc == 2 and both, "neither copy of the Object Table can be read: exit 2 (exit %s) and a statement that the " \
        "Object Table could not be read naming both roots, PLCN 0xc08 and 0x3400 (%d such line(s); Q8)" \
        % (rc, len(both)) + _ctx(rc, out[-600:], err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The PARTIAL fixture (N358, N427, N445): millionsofactionsv2 with its Object-Table leaf 0x424 unread
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

V2 = "step3b/win11refs2tmillionsofactionsv2.raw"
V2_LEAF = 0x424
PARTIAL = {"zero": [V2_LEAF + i for i in range(4)]}
V2_ON_LEAF = (0x7, 0x8, 0x9, 0xA, 0xD, 0x30, 0x500, 0x501, 0x520, 0x530, 0x540, 0x541, 0x600, 0x701)
_LEAF_SAID = re.compile(r"(?i)plcn 0x424 reads as all zeros")


def test_c1_control_the_partial_fixture_reads_the_object_table_in_part(monkeypatch):
    """Not a RED: the fixture's premise. Unplanted, the walk reads 512 objects in full, the system OIDs among them;
    with leaf 0x424 read as zeros the walk is partial (`object_table_read_state` 'partial', 404 objects) and every
    OID of V2_ON_LEAF is missing. In-process; every register fresh and restored."""
    import test_1132_red_waveb_rest as WR
    WR._n425_fresh(monkeypatch)
    for name in ("_OBJ_ROOT_REF", "_OBJ_ROOT_LCNS"):
        monkeypatch.setattr(F, name, {})
    monkeypatch.setattr(F, "_OBJ_ROOT_VERIFIED", set())
    img = MC.corpus(V2)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        f, ps, cs, tr, roots, om, *_r = F.bootstrap(img, None)
    try:
        _fx(len(om) == 512 and F.object_table_read_state(om) is None and all(o in om for o in V2_ON_LEAF),
            "unplanted: %d objects, state %r" % (len(om), F.object_table_read_state(om)))
        real = F._seek_read
        bad = set(PARTIAL["zero"])
        monkeypatch.setattr(F, "_seek_read", lambda fh, off, n: bytes(n) if (off - ps) // cs in bad else real(fh, off, n))
        with contextlib.redirect_stderr(err):
            m = F.build_object_map(f, ps, cs, tr, F._select_ot_root(f, ps, cs, tr, roots), register=False)
    finally:
        f.close()
    _keep(len(m) == 404 and F.object_table_read_state(m) == "partial" and not any(o in m for o in V2_ON_LEAF),
          "planted: %d objects, state %r, on-leaf OIDs present %r" % (
              len(m), F.object_table_read_state(m), [hex(o) for o in V2_ON_LEAF if o in m]))


def _partial(tmp_path, tool, *args):
    rc, out, err = run_planted(tmp_path, tool, MC.corpus(V2), args, PARTIAL)
    _fx(_LEAF_SAID.search(err), "the run does not say the Object-Table leaf 0x424 reads as zeros" + _ctx(rc, out, err))
    return rc, out, err


# ─── N358: readers over an Object Table read in part ──────────────────────────────────────────────────────────────

# RED 1.13.2 N358: `security` over an Object Table read in part says OID 0x530 is 'not found in Object Table', exit 1 -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_security_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, FOREFST, "security")
    absent = [ln for ln in (out + "\n" + err).splitlines() if re.search(r"(?i)not\s+found\s+in\s+(?:the\s+)?Object", ln)]
    said = undetermined_lines(out + "\n" + err)
    assert rc == 2 and said and not absent, "OID 0x530 sits on the unread leaf: `security` must exit 2 (exit %s) and " \
        "say 'not determined: the Object Table was read in part' (%d line(s)), never 'not found in Object Table' " \
        "(%r; Q10/Q11)" % (rc, len(said), absent[:1]) + _ctx(rc, out, err)


# RED 1.13.2 N358: `files` says '0 security descriptors loaded' over an Object Table read in part (build_security_map) -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_files_security_map_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, FOREFST, "files", "--csv")
    zero = [ln for ln in err.splitlines() if re.search(r"(?i)\b0 security descriptors? loaded\b", ln)
            and not _NOT_DET.search(ln)]
    said = undetermined_lines(err, also=r"(?i)security")
    assert said and not zero and rc == 2, "the security descriptor table (OID 0x530) was not read: `files` must say " \
        "the descriptors are not determined because the Object Table was read in part (%d line(s)), not '0 " \
        "security descriptors loaded' (%r), exit 2 (exit %s)" % (len(said), zero[:1], rc) + _ctx(rc, out[:300], err)


# RED 1.13.2 N358: `usn --info` says '(OID 0x520 absent — journal not activated)' over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_usn_info_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, FOREFST, "usn", "--info")
    # critic O-4: a "not determined" line may name the absence it does not state ("whether OID 0x520 is absent")
    claim = [ln for ln in (out + "\n" + err).splitlines() if re.search(r"(?i)not\s+activated|\babsent\b", ln)
             and not _NOT_DET.search(ln)]
    said = undetermined_lines(out + "\n" + err)
    assert said and not claim and rc == 2, "OID 0x520 sits on the unread leaf: `usn --info` must say the journal is " \
        "not determined, the Object Table read in part (%d line(s)), never that it is absent or was not activated " \
        "(%r), exit 2 (exit %s)" % (len(said), claim[:1], rc) + _ctx(rc, out, err)


# RED 1.13.2 N358: `reparse --index` prints 'Total entries: 0' / '(no entries)' over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_reparse_index_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, FOREFST, "reparse", "--index")
    claim = [ln for ln in (out + "\n" + err).splitlines()
             if re.search(r"(?i)\(no entries\)|not\s+found\b", ln) and not _NOT_DET.search(ln)]
    said = undetermined_lines(out + "\n" + err)
    assert said and not claim and rc == 2, "the Reparse Point Index (OID 0x540) sits on the unread leaf: `reparse " \
        "--index` must say it is not determined (%d line(s)), not '(no entries)' / 'not found' (%r), exit 2 (exit %s)" \
        % (len(said), claim[:2], rc) + _ctx(rc, out, err)


# RED 1.13.2 N358: `deleted --trash` says 'Empty (all deletions fully processed)' over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_trash_table_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, FOREFST, "deleted", "--trash")
    claim = [ln for ln in out.splitlines() if re.search(r"(?i)\bEmpty\b.*fully processed", ln)]
    said = undetermined_lines(out + "\n" + err)
    assert said and not claim and rc == 2, "the Trash Table (OID 0xD) sits on the unread leaf: `deleted --trash` must " \
        "say it is not determined (%d line(s)), not 'Empty (all deletions fully processed)' (%r), exit 2 (exit %s)" \
        % (len(said), claim[:1], rc) + _ctx(rc, out[-1500:], err)


# RED 1.13.2 N358: refsanalysis `oid30` prints 'OID 0x30: NOT PRESENT' over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_ra_oid30_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, REFSANALYSIS, "oid30")
    claim = [ln for ln in out.splitlines() if re.search(r"(?i)NOT PRESENT", ln)]
    said = undetermined_lines(out + "\n" + err)
    assert said and not claim and rc == 2, "OID 0x30 sits on the unread leaf: `oid30` must say it is not determined " \
        "(%d line(s)), not 'NOT PRESENT' (%r), exit 2 (exit %s)" % (len(said), claim[:1], rc) + _ctx(rc, out, err)


# RED 1.13.2 N358: refsanalysis `boot --verify` says the volume 'holds no readable $VOLUME_INFORMATION row' over a part-read table -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_volume_information_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    """`read_volume_information` (OID 0x500): the version row `version_corroborated` of ra `boot --verify`."""
    rc, out, err = _partial(tmp_path, REFSANALYSIS, "boot", "--verify")
    claim = [ln for ln in out.splitlines() if re.search(r"(?i)holds\s+no\s+(?:readable\s+)?\$?VOLUME_INFORMATION", ln)]
    said = undetermined_lines(out + "\n" + err, also=r"(?i)VOLUME_INFORMATION|version")
    assert said and not claim and rc == 2, "OID 0x500 sits on the unread leaf: the version comparison is not " \
        "determined because the Object Table was read in part (%d line(s)), not 'the volume holds no readable " \
        "$VOLUME_INFORMATION row' (%r), exit 2 (exit %s)" % (len(said), claim[:1], rc) + _ctx(rc, out, err)


# RED 1.13.2 N358: `fastsummary` prints 'Volume label: (none)' over an Object Table read in part (OID 0x500 not read) -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n358_volume_label_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    """The class search (census N358: every 'OID not in obj_map' reader): the label row (OID 0x500, key 0x510)."""
    rc, out, err = _partial(tmp_path, FOREFST, "fastsummary")
    claim = [ln for ln in out.splitlines() if re.search(r"(?i)^\s*Volume label:\s*\(none\)", ln)]
    said = undetermined_lines(out + "\n" + err, also=r"(?i)label|VOLUME_INFORMATION|0x500")
    assert said and not claim and rc == 2, "the volume information object (OID 0x500) sits on the unread leaf: the " \
        "label is not determined (%d line(s)), not '(none)' (%r), exit 2 (exit %s)" % (len(said), claim[:1], rc) \
        + _ctx(rc, out[:2000], err)


# ─── N427 over a table read in part: the lookups that `die()` ────────────────────────────────────────────────────────

# RED 1.13.2 N427: `reparse` dies 'Root directory (OID 0x600) not found' (exit 1) over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_reparse_root_directory_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, FOREFST, "reparse")
    said = undetermined_lines(out + "\n" + err)
    assert rc == 2 and said, "the root directory (OID 0x600) sits on the unread leaf: `reparse` must exit 2 (exit %s) " \
        "with 'not determined: the Object Table was read in part' (%d line(s)), not die with 'not found'" \
        % (rc, len(said)) + _ctx(rc, out, err)


# RED 1.13.2 N427: `details 0x600` says 'not found in object table' and exits 1 over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_details_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    rc, out, err = _partial(tmp_path, FOREFST, "details", "0x600")
    said = undetermined_lines(out + "\n" + err)
    assert rc == 2 and said, "OID 0x600 sits on the unread leaf: `details` must exit 2 (exit %s) and say it is not " \
        "determined, the Object Table read in part (%d line(s); fd:20905's 'not found in object table' is an absence " \
        "from the map worded as one from the table)" % (rc, len(said)) + _ctx(rc, out, err)


# RED 1.13.2 N427: `dataruns` dies 'OID 0x600 not found in Object Table' (exit 1) over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_dataruns_start_directory_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    """The census's user-OID lookups (fd:14508 `extract`, fd:19289 `dataruns`), with the default start, OID 0x600."""
    rc, out, err = _partial(tmp_path, FOREFST, "dataruns")
    said = undetermined_lines(out + "\n" + err)
    assert rc == 2 and said, "OID 0x600 sits on the unread leaf: `dataruns` must exit 2 (exit %s) and say the start " \
        "directory is not determined (%d line(s))" % (rc, len(said)) + _ctx(rc, out, err)


# RED 1.13.2 N427: `extract` dies 'OID 0x600 not found in Object Table' (exit 1) over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_extract_start_directory_over_an_object_table_read_in_part_is_not_determined(tmp_path):
    """Critic O-6: the census's other user-OID lookup (fd:14508 `extract`, the twin of fd:19289 `dataruns`), with a
    full path (resolved from the default start, OID 0x600)."""
    rc, out, err = _partial(tmp_path, FOREFST, "extract", "/c1_no_such_file.txt")
    said = undetermined_lines(out + "\n" + err)
    assert rc == 2 and said, "OID 0x600 sits on the unread leaf: `extract` must exit 2 (exit %s) and say the start " \
        "directory is not determined (%d line(s)), not die with 'not found in Object Table'" % (rc, len(said)) \
        + _ctx(rc, out[:600], err)


V2_PC_LEAF = 0x300378          # the Parent-Child Table (root 4) of millionsofactionsv2: root 0x303db8 over leaves
                               # 0x300378 and 0x3024c8; the first holds the rows that name OID 0x600 as a parent


# RED 1.13.2 N427: ra `parentchild --verify` says 'Root Directory (0x600) not found in table' over a table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_parentchild_verify_over_a_table_read_in_part_is_not_determined(tmp_path):
    """One table down (Q11 "the same for each table one level down"; ra:2811): the Parent-Child Table's leaf 0x300378
    reads as zeros; the table is read in part (218 of 500 rows)."""
    spec = {"zero": [V2_PC_LEAF + i for i in range(4)]}
    rc, out, err = run_planted(tmp_path, REFSANALYSIS, MC.corpus(V2), ["parentchild", "--verify"], spec)
    # critic O-7: the premise is the damage note and the 218 rows read; not the line "[OK] Parent-Child Table has 218
    # entries", itself a statement over a table read in part (RED_C1 N-4) that the fix may reword
    _fx(re.search(r"(?i)plcn 0x300378 reads as all zeros", err) and re.search(r"(?<![\d,.])218(?![\d,])", out),
        "the Parent-Child leaf did not read as zeros" + _ctx(rc, out, err))
    claim = [ln for ln in out.splitlines() if re.search(r"(?i)0x600\)? not found in (?:the )?table", ln)]
    said = undetermined_lines(out + "\n" + err, table=r"Parent-Child\s+Table", also=r"0x600")
    assert said and not claim and rc == 2, "the Parent-Child Table was read in part: whether the root directory is " \
        "in it is not determined (%d line(s)), not 'not found in table' (%r), exit 2 (exit %s)" \
        % (len(said), claim[:1], rc) + _ctx(rc, out[-2000:], err)


# ─── N427 over a table read in full: absence is a finding (exit 2, not 1) ────────────────────────────────────────

def _absent(tmp_path, tool, drop, *args):
    rc, out, err = run_planted(tmp_path, tool, MC.corpus(BASE), args, {"drop": list(drop)})
    _fx("could not be read" not in err, "the base's run read something only in part" + _ctx(rc, out, err))
    return rc, out, err


def _names(text, *pats):
    return [ln for ln in text.splitlines() if all(re.search(p, ln) for p in pats)]


# RED 1.13.2 N427: `security` exits 1 when the Object Table, read in full, holds no Security Descriptor Stream (OID 0x530) -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_security_without_oid_0x530_is_a_finding(tmp_path):
    rc, out, err = _absent(tmp_path, FOREFST, [0x530], "security")
    said = _names(out + "\n" + err, r"(?i)0x530", r"(?i)Object\s+Table|Security\s+Descriptor")
    assert rc == 2 and said, "a required structure absent from an Object Table read in full is a finding: exit 2 (exit " \
        "%s; 1 is 'cannot run'), with a statement naming OID 0x530 (%d line(s); Q10)" % (rc, len(said)) \
        + _ctx(rc, out, err)


# RED 1.13.2 N427: `reparse` dies 'Root directory (OID 0x600) not found' (exit 1) when the Object Table holds no OID 0x600 -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_reparse_without_the_root_directory_is_a_finding(tmp_path):
    rc, out, err = _absent(tmp_path, FOREFST, [0x600], "reparse")
    said = _names(out + "\n" + err, r"(?i)0x600", r"(?i)Object\s+Table|root\s+directory")
    assert rc == 2 and said, "the root directory absent from an Object Table read in full: exit 2 (exit %s) with a " \
        "statement naming OID 0x600 (%d line(s); Q10)" % (rc, len(said)) + _ctx(rc, out, err)


# RED 1.13.2 N427: `dataruns` dies 'OID 0x600 not found in Object Table' (exit 1) when the Object Table holds no OID 0x600 -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_dataruns_without_the_root_directory_is_a_finding(tmp_path):
    rc, out, err = _absent(tmp_path, FOREFST, [0x600], "dataruns")
    said = _names(out + "\n" + err, r"(?i)0x600", r"(?i)Object\s+Table|root\s+directory")
    assert rc == 2 and said, "the default start directory (OID 0x600) absent from an Object Table read in full: exit 2 " \
        "(exit %s) with a statement naming it (%d line(s); Q10)" % (rc, len(said)) + _ctx(rc, out, err)


# RED 1.13.2 N427: `extract` dies 'OID 0x600 not found in Object Table' (exit 1) when the Object Table holds no OID 0x600 -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_extract_without_the_root_directory_is_a_finding(tmp_path):
    """Critic O-6: fd:14508, the twin of `dataruns`' lookup."""
    rc, out, err = _absent(tmp_path, FOREFST, [0x600], "extract", "/c1_no_such_file.txt")
    said = _names(out + "\n" + err, r"(?i)0x600", r"(?i)Object\s+Table|root\s+directory")
    assert rc == 2 and said, "the default start directory (OID 0x600) absent from an Object Table read in full: exit 2 " \
        "(exit %s) with a statement naming it (%d line(s); Q10)" % (rc, len(said)) + _ctx(rc, out[:600], err)


# RED 1.13.2 N427: ra `upcase` dies 'OID 0x07 (Upcase Table) not found' (exit 1) when the Object Table holds neither copy -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_ra_upcase_without_either_upcase_copy_is_a_finding(tmp_path):
    """The Upcase Table is the failover pair {OID 0x8, OID 0x7} (InitializeUpcaseTable, N422): both removed."""
    rc, out, err = _absent(tmp_path, REFSANALYSIS, [0x7, 0x8], "upcase")
    said = _names(out + "\n" + err, r"(?i)Upcase", r"(?i)0x0?7|0x0?8|Object\s+Table")
    assert rc == 2 and said, "the Upcase Table absent from an Object Table read in full: exit 2 (exit %s), with a " \
        "statement naming it (%d line(s); Q10)" % (rc, len(said)) + _ctx(rc, out, err)


def _drop_schema_root(v):
    """Both checkpoint copies of the synthetic volume without a reference for root 3 (the Schema Table): the root's
    entry of the indirect offset table set to 0, the copy resealed."""
    def edit(b):
        olb = F.le32(b, 0x94)
        struct.pack_into("<I", b, olb + 4 * 3, 0)
    for lcn in (v.geo.lo, v.geo.hi):
        v.reseal(lcn, edit, AB.CHKP_DESC)
        _fx(AB._root_list(v.block(lcn))[3] is None, "CHKP 0x%x still references root 3" % lcn)


# RED 1.13.2 N427: ra `schema` dies 'Schema Table root not found' (exit 1) when the checkpoint holds no root 3 -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n427_ra_schema_without_the_schema_table_root_is_a_finding(tmp_path):
    v = AB._synthetic_vol(tmp_path)
    _drop_schema_root(v)
    rc, text = v.run(REFSANALYSIS, "schema")
    said = _names(text, r"(?i)Schema\s+Table")
    assert rc == 2 and said, "the Schema Table's root is a structure the command needs; its absence is a finding: " \
        "exit 2 (exit %s; 1 is 'cannot run'), with a statement naming it (%d line(s); Q10)" % (rc, len(said)) \
        + "\n| " + text[-2000:]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N445 -- statements of absence over a table not read in full
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

NONE_HOLES = [B2_PRI_HOLE, B2_DUP_HOLE]           # the C-2 shape: neither copy of the Object Table can be read


# RED 1.13.2 N445: (a) `usn --info` says '(OID 0x520 absent — journal not activated)' over an Object Table not read -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n445_a_usn_info_over_an_object_table_that_could_not_be_read_on_image_win11refsmini():
    with planted_copy(BASE, holes=NONE_HOLES) as p:
        rc, out, err = run_cli(FOREFST, p, "usn", "--info")
    claim = [ln for ln in (out + "\n" + err).splitlines() if re.search(r"(?i)not\s+activated|\babsent\b", ln)
             and not _NOT_DET.search(ln)]                # critic O-4
    said = undetermined_lines(out + "\n" + err)
    assert said and not claim and rc == 2, "neither Object-Table root can be read: `usn --info` must say whether a " \
        "journal exists is not determined (%d line(s)), never 'absent -- journal not activated' (%r), exit 2 (exit " \
        "%s)" % (len(said), claim[:1], rc) + _ctx(rc, out, err)


# RED 1.13.2 N445: (a) `export metadata`'s manifest says 'usn: no change journal on this volume' over an unread Object Table -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n445_a_export_manifest_over_an_object_table_that_could_not_be_read_on_image_win11refsmini(tmp_path):
    outdir = str(tmp_path / "bundle")
    with planted_copy(BASE, holes=NONE_HOLES) as p:
        rc, out, err = run_cli(FOREFST, p, "export", "metadata", "-o", outdir)
    man = os.path.join(outdir, "manifest.json")
    _fx(os.path.isfile(man), "export metadata wrote no manifest" + _ctx(rc, out, err))
    with open(man) as fh:
        warns = [w for w in (jdoc(json.load(fh), F._BUNDLE_KEYS).get("warnings") or []) if w.get("what") == "usn"]
    reasons = " | ".join(str(w.get("reason")) for w in warns)
    assert warns and not re.search(r"(?i)no change journal on this volume", reasons) \
        and undetermined_lines(reasons), "the manifest's usn warning over an Object Table that could not be read: %r " \
        "-- it must say the journal is not determined (the Object Table could not be read), not that the volume has " \
        "none" % reasons


_V2_MANIFEST = {}


def partial_v2_manifest(tmp_path):
    """(rc, manifest warnings) of `export metadata` on the PARTIAL fixture, once per process. The bundle (about 350 MB)
    is written to the scratch directory and deleted by its exact path as soon as the manifest is read."""
    if "w" not in _V2_MANIFEST:
        os.makedirs(MC.SCRATCH, exist_ok=True)
        d = tempfile.mkdtemp(prefix="c1_v2_bundle_", dir=MC.SCRATCH)
        outdir = os.path.join(d, "bundle")
        try:
            rc, out, err = run_planted(tmp_path, FOREFST, MC.corpus(V2), ["export", "metadata", "-o", outdir], PARTIAL)
            _fx(_LEAF_SAID.search(err), "the export did not read leaf 0x424 as zeros" + _ctx(rc, out, err))
            with open(os.path.join(outdir, "manifest.json")) as fh:
                _V2_MANIFEST["w"] = (rc, jdoc(json.load(fh), F._BUNDLE_KEYS).get("warnings") or [])   # K21 readers
        finally:
            if os.path.isdir(outdir):
                shutil.rmtree(outdir)
            os.rmdir(d)
    return _V2_MANIFEST["w"]


# RED 1.13.2 N445: (a) the manifest says 'usn: no change journal on this volume' over an Object Table read in part -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n445_a_export_manifest_over_an_object_table_read_in_part_on_image_millionsofactionsv2(tmp_path):
    rc, warns = partial_v2_manifest(tmp_path)
    usn = " | ".join(str(w.get("reason")) for w in warns if w.get("what") == "usn")
    assert usn and not re.search(r"(?i)no change journal on this volume", usn) and undetermined_lines(usn), \
        "OID 0x520 sits on the unread leaf: the manifest's usn warning %r must say the journal is not determined (the " \
        "Object Table was read in part), not that the volume has none (N445 (a), N358's class)" % usn


def _partial_map():
    """The REAL build_object_map over a walk that reads ONE object row (OID 0x701) and records one page it could not
    read (as test_1132_red_waveb_mlog's LB68 partial map): an Object Table read in part."""
    import test_1132_red_waveb_mlog as WM
    with open(MC.corpus(BASE), "rb") as fh:
        return WM._lb68_partial_map(fh)


# RED 1.13.2 N445: (d) `_usn_resolve_path` labels an OID missing from a map read in part '<oid 0x..>' (the directory is gone) -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n445_d_the_gone_label_is_not_given_over_a_map_read_in_part(monkeypatch):
    import test_1132_red_waveb_rest as WR
    WR._n425_fresh(monkeypatch)
    om = _partial_map()
    _fx(F.object_table_read_state(om) == "partial", "the map is not partial: %r" % F.object_table_read_state(om))
    lab = F._usn_resolve_path(0x7ff, {}, om)
    assert lab and not lab.startswith("<oid ") and _lcn_re(0x7ff).search(lab), "OID 0x7ff is missing from an Object " \
        "Table read in part: its label %r says the directory is gone (`<oid 0x..>`, K072's 'the directory is gone'); " \
        "it must be a label that holds the OID and does not claim the directory no longer exists" % lab


def test_n445_d_control_the_gone_label_over_a_map_read_in_full():
    """Not a RED. Over a map read in full (a plain dict: read state None) an OID missing from it keeps `<oid 0x..>`,
    and one in the map keeps `<unlinked 0x..>`."""
    _keep(F._usn_resolve_path(0x7ff, {}, {0x701: [1]}) == "<oid 0x7ff>"
          and F._usn_resolve_path(0x701, {}, {0x701: [1]}) == "<unlinked 0x701>", "the full-map labels moved")


def _single_source_copies():
    """[(path, rows)] of every copy of single_source.tsv: the workspace's `analysis/verification/` and, when it is
    another file, the dev tree's `forefstdev/analysis/verification/` (critic O-5: as test_1132_red_g2c2's R5 nodes, a
    row is asked of both copies, so a fix that edits either one alone is seen)."""
    paths = [os.path.join(os.path.dirname(REPO), "analysis", "verification", "single_source.tsv")]
    dev = os.path.join(REPO, "analysis", "verification", "single_source.tsv")
    if os.path.isfile(dev) and os.path.realpath(dev) != os.path.realpath(paths[0]):
        paths.append(dev)
    out = []
    for p in paths:
        _fx(os.path.isfile(p), "single_source.tsv not found at %s" % p)
        with open(p, encoding="utf-8") as fh:
            out.append((p, [ln.rstrip("\n").split("\t") for ln in fh if ln.strip() and not ln.startswith("#")
                            and not ln.startswith("@allow")]))
    return out


def _single_source_rows():
    """The rows of the workspace's copy (the one `analysis/verification/check_single_source.py` reads)."""
    return _single_source_copies()[0][1]


# RED 1.13.2 N445: (e) single_source.tsv has no row for object_table_read_state -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n445_e_object_table_read_state_has_its_single_source_row():
    bad = []
    for p, rows in _single_source_copies():
        mine = [r for r in rows if len(r) >= 3 and r[1] == "object_table_read_state"]
        if not (mine and mine[0][2].endswith("forefst.py")):
            bad.append("%s: %r" % (p, mine))
    assert not bad, "object_table_read_state (LB68, one test of an Object Table walk's read state for both tools) has " \
        "no single_source.tsv row (O5 / Q11), in every copy: %s" % "; ".join(bad)
