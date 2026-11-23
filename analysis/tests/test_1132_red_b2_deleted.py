"""1.13.2 RED cases, group b2_deleted: plan row B8 and the running-log items N129, N145, N146.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 2 B (row B8), section 5 "RED first", the fourth revision
and decision 19 (the maintainer's bar: every RED fails on 1.13.1 BECAUSE of the defect, not because of an artefact,
and is independently confirmed). N129: `RC1_DEPS_CHECKPOINT.md` table 2 and `E2_RC2_CLASSIFICATION.md` V-5 / N-m.
N145, N146: `RUNNING_LOG.md` (with the IC-2 and IC-3 corrections). Report, with the observed or expected failure of
every node: `analysis/reports/v1.13.2/red/RED_b2_deleted.md`.

What each RED asserts
---------------------
B8   (Acceptance column) a remnant whose file was renamed is shown as a former name of the live file's FileRef, not
     as DELETED; where the tool cannot decide (the remnant keeps no FileRef and no journal record names it) the row
     says "deleted, or renamed", never DELETED alone; the win11refstestmftecmd probe records its before/after counts.
N129 (no plan row; the item text in RC1_DEPS table 2, E2 N-m, and D5 "removes a false exit 2") the page-slack scan
     does not read inside live rows, does not take `$OBJ_LINK` sub-record keys for name rows (so a parent OID in
     0xD800-0xDFFF is no decode skip and no exit 2 on a healthy volume), and does not drop those keys silently.
N145 (no plan row; RUNNING_LOG N145 as corrected by IC-2) the `partial` grade tests only the creation and
     modification times against ~2009-11..2050-12, so the output must not call such a row a name fragment or a
     partly overwritten row, must say what the grade tests, and a count labelled "with valid timestamps" must not
     include a row with one time outside the window.
N146 (no plan row; RUNNING_LOG N146 as widened by IC-3) `deleted --scan-pages` classifies a remnant by the file's
     identity at any depth (the slack path's rule), not by its bare name among names collected to depth 10, and
     does not collapse two remnants that share a name; the checkpoint differential reports a removal below depth
     10 and a removal whose name survives in another directory, instead of "Same top-level files in both".
LEAD (found while building N146's fixture; no N-number yet) the differential rebuilds the older checkpoint's
     Object Table with `build_object_map`, which overwrites the module-global root digests, so a later walk of a
     directory deeper than 10 levels that changed between the checkpoints is reported ALTERED and `deleted` exits 2
     on a healthy volume.

Volumes
-------
* ``[synthetic]`` -- a 1 MiB ReFS 3.14 volume written into pytest's tmp dir: the VBR, superblocks and root tables of
  `test_1132_red_a_bootstrap.py` (imported, one builder), with a populated Object Table and directory pages
  built by this module (live rows in the offset array, remnant rows in the page's free space, orphan pages outside
  the tree, and, for the differential, a second Object Table under the older checkpoint). No corpus image is read.
  `test_b2_fixture_builder_is_sound` checks the bytes independently of the tool.
* ``[image]`` -- a corpus image opened READ-ONLY (never damaged, never copied): win11refs8gtestmove_aftermove (B8),
  win11refstestmftecmd (B8 probe, N145), winsiderv2 and its control winsider (N129). Skipped when absent. The B8
  probe's oracle is Windows' own `fsutil usn readjournal` export shipped with the sample
  (`analysis/samples/disks/win11refstestmftecmd/provenance/usn_readjournal_export.txt`), bounded to the records
  the image holds (USN <= 917,280, provenance/commands.md section 3). ``pytest -k "not image"`` runs the rest.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; the fix commit removes the mark and an XPASS fails the
  run. Only a plain ``assert`` states the acceptance.
* A fixture that is not what the case needs, a crash or a timeout raises ``RedFixtureError``; a property 1.13.1
  already has and the fix must keep raises ``KeptPropertyBroken``. Neither is an AssertionError.
* Each synthetic RED has a control that differs from it in the defect's trigger only and passes on 1.13.1 (the
  surrogate OID against an ordinary one; a renamed remnant against a CoW remnant of an unrenamed file; a removal
  below depth 10 against identical checkpoints; digests with a deep change against digests with a shallow one).
"""
import csv
import datetime
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
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (VBR/SUPB/root pages, CRC32-C, exceptions)

FOREFST = AB.FOREFST
TIMEOUT = 1800                                           # winsiderv2 is 60 GB logical
SCRATCH = AB.SCRATCH
CS = AB.CS
PAGE = 4 * CS
RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, AB._red


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The synthetic volume
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_T = 134000000000000000          # 2025-08-18 14:13:20 UTC: inside the tool's plausible window
_S = 10 ** 7                     # one second in FILETIME units
_N = 256                         # clusters (the geometry of AB's synthetic volume: same VBR, SUPB list, backups)
_LO, _HI = AB.SYN.lo, AB.SYN.hi  # newer checkpoint (clock 64) at 0x48, older (63) at 0x88
_OT_LCN = 0xA0                   # root 0 = the Object Table, as in AB
_RESERVED = {0x1E, _LO, _HI, _N - 3, _N - 2, _N - 1} | set(range(0xA0, 0xA0 + 13 * 4))
_FREE_PAGES = [l for l in range(0x20, _N - 4, 4) if not any(x in _RESERVED for x in range(l, l + 4))]


def _ft(y, m, d):
    return int((datetime.datetime(y, m, d) - datetime.datetime(1601, 1, 1)).total_seconds()) * 10 ** 7


def _r8(n):
    return (n + 7) & ~7


def _row(key, value):
    """A B+-tree row: <I6H header (size, key off 0x10, key len, flags, value off, value len), key, value."""
    ko, kl, vl = 0x10, len(key), len(value)
    vo = _r8(ko + kl)
    size = _r8(vo + vl)
    b = bytearray(size)
    struct.pack_into("<I6H", b, 0, size, ko, kl, 0, vo, vl, 0)
    b[ko:ko + kl] = key
    b[vo:vo + vl] = value
    return bytes(b)


def _name_key(name):
    return struct.pack("<HH", 0x30, 0) + name.encode("utf-16-le")


def _file_value(fid, home, ct, mt=None):
    """The 84-byte (v3.14) non-resident name-row value: FileRef = home:fid at +0x08/+0x00, times at +0x10.."""
    v = bytearray(0x54)
    mt = ct if mt is None else mt
    struct.pack_into("<QQQQQQ", v, 0, fid, home, ct, mt, mt, mt)
    struct.pack_into("<Q", v, 0x38, 100)
    struct.pack_into("<I", v, 0x40, 0x20)                 # Archive
    return bytes(v)


def _dir_value(oid, ct=_T):
    v = bytearray(0x54)
    struct.pack_into("<QQQQQQ", v, 0, 0, oid, ct, ct, ct, ct)
    struct.pack_into("<I", v, 0x40, 0x10000010)           # bit 28 = directory
    return bytes(v)


def _objlink_subrow(parent_oid, name12):
    """An embedded $OBJ_LINK sub-record row (structure_reference.md:714-725): key = le64(value length) + value,
    value = marker 0x80000002, type 0x39, sub-type 0x0D, parent OID, 12 zero bytes, the name. A 12-character
    name gives a value length of 0x30 -- the value the slack scanner reads as key type 0x30 (E2 V-5)."""
    _fx(len(name12) == 12, "an $OBJ_LINK key reads as type 0x30 only with a 12-character name")
    val = struct.pack("<IHHI", 0x80000002, 0x39, 0x0D, parent_oid) + b"\0" * 12 + name12.encode("utf-16-le")
    key = struct.pack("<Q", len(val)) + val
    size = _r8(0x10 + len(key))
    b = bytearray(size)
    struct.pack_into("<I6H", b, 0, size, 0x10, len(key), 0, 0x18, len(val), 0)   # value overlaps the key
    b[0x10:0x10 + len(key)] = key
    return bytes(b)


def _resident_value(ct, fid, parent_oid, name12):
    """A resident (embedded) file value: $SI times at +0x28, file id at +0x80, and an embedded node at +0xA8
    holding one $OBJ_LINK sub-record, addressed by the node's own row array (parse_resident_btree_rows' layout)."""
    v = bytearray(0x120)
    base, rows_at = 0xA8, 0x28
    struct.pack_into("<I", v, 0, base)
    struct.pack_into("<QQQQ", v, 0x28, ct, ct, ct, ct)
    struct.pack_into("<I", v, 0x48, 0x20)
    struct.pack_into("<Q", v, 0x80, fid)
    sub = _objlink_subrow(parent_oid, name12)
    v[base + rows_at:base + rows_at + len(sub)] = sub
    arr_lo = rows_at + len(sub)
    struct.pack_into("<III", v, base + 0x10, arr_lo, 1, 0)
    struct.pack_into("<I", v, base + 0x20, arr_lo + 4)
    struct.pack_into("<HH", v, base + arr_lo, rows_at, 0xFFFF)
    return bytes(v)


def _page(lcn, table_oid, live=(), slack=()):
    """A 16 KiB MSB+ leaf page. Live rows are addressed by the offset array; slack rows are written in the data
    area with no array entry, as a deletion leaves them (CmsBPlusTable::DeleteFromIndex removes the slot and marks the row, E181).
    Everything sits in the first cluster, so an orphan copy of the page is reachable by the orphan scans too."""
    p = bytearray(PAGE)
    p[0:4] = b"MSB+"
    struct.pack_into("<I", p, 0x0C, AB._VOLSIG)
    struct.pack_into("<4Q", p, 0x20, lcn, lcn + 1, lcn + 2, lcn + 3)
    struct.pack_into("<Q", p, 0x48, table_oid)
    thoff = 0x60
    struct.pack_into("<I", p, 0x50, thoff - 0x50)
    pos, offs = 0xA0, []
    for kind, r in [("L", r) for r in live] + [("S", r) for r in slack]:
        p[pos:pos + len(r)] = r
        if kind == "L":
            offs.append(pos - thoff)
        pos = _r8(pos + len(r))
    astart = pos - thoff
    aend = astart + 4 * len(offs)
    for i, o in enumerate(offs):
        struct.pack_into("<I", p, thoff + astart + 4 * i, o)
    tbl = [0] * 10
    tbl[4], tbl[8] = astart, aend
    struct.pack_into("<10I", p, thoff, *tbl)
    _fx(thoff + aend < CS, "the page's rows and array do not fit its first cluster")
    return bytes(p)


def _ot(lcn, objects, digests):
    """The Object Table page: key (0, oid), value with the root page's four LCNs at +0x20 and, when `digests`,
    the CRC64 of that page at +0x48 with its length (8) at +0x44 -- the digest real volumes carry."""
    rows = []
    for oid in sorted(objects):
        plcn, pg = objects[oid]
        v = bytearray(0x98)
        struct.pack_into("<4Q", v, 0x20, plcn, plcn + 1, plcn + 2, plcn + 3)
        if digests:
            struct.pack_into("<I", v, 0x44, 8)
            struct.pack_into("<Q", v, 0x48, F.refs_crc64(pg))
        rows.append(_row(struct.pack("<QQ", 0, oid), bytes(v)))
    return _page(lcn, 0x02, rows)


def _chkp(own, clock, alloc, ot_lcn, ot_page):
    """AB._syn_chkp with root 0 pointing at this module's Object Table (and its CRC64). Roots 1-12 are AB's."""
    p = bytearray(CS)
    p[0:4] = b"CHKP"
    struct.pack_into("<I", p, 4, 2)
    struct.pack_into("<I", p, 0x0C, AB._VOLSIG)
    struct.pack_into("<Q", p, 0x10, clock)
    struct.pack_into("<Q", p, 0x20, own)
    struct.pack_into("<HHHH", p, 0x50, 3, 14, 3, 14)
    struct.pack_into("<II", p, 0x58, AB.CHKP_DESC, 0x30)
    struct.pack_into("<QQQ", p, 0x60, clock, alloc, 0x100000092)
    struct.pack_into("<I", p, 0x78, 0x682)
    struct.pack_into("<II", p, 0x88, 0x380, 0x20)
    struct.pack_into("<III", p, 0x90, 13, 0xA8, 0x38)
    for i in range(13):
        ro = 0x110 + 0x30 * i
        base, pg = (ot_lcn, ot_page) if i == 0 else (0xA0 + 4 * i, AB._syn_root_page(i, objects=False))      # its own Object Table (root 5: no rows, as before)
        struct.pack_into("<I", p, 0xA8 + 4 * i, ro)
        struct.pack_into("<4Q", p, ro, base, base + 1, base + 2, base + 3)
        p[ro + 0x22], p[ro + 0x23] = 2, 8
        struct.pack_into("<I", p, ro + 0x24, 8)
        struct.pack_into("<Q", p, ro + 0x28, F.refs_crc64(pg))
    struct.pack_into("<Q", p, AB.CHKP_DESC, own)
    p[AB.CHKP_DESC + 0x22], p[AB.CHKP_DESC + 0x23] = 1, 8
    struct.pack_into("<I", p, AB.CHKP_DESC + 0x24, 4)
    AB._seal(p, AB.CHKP_DESC)
    return bytes(p)


class DirVol:
    """A synthetic volume with a directory tree. `dirs` maps oid -> {"parent", "name", "files", "slack"}; files and
    slack are row lists. The newer checkpoint sees `self.objects`; the older one `self.old_objects` (the same
    unless a case changes a page between the two)."""

    def __init__(self, log=False):
        """`log` (1.14.0, Q-D D3): the volume carries a_bootstrap's empty MLog (the Logfile Information Table pair in
        the Object Table, two control copies, a data area of 0x50 clusters) for the nodes that run `summary`, which
        reads the log; its pages are taken out of the free list."""
        self.log = log
        taken = set()
        if log:
            taken = set(range(AB._SYN_LOG_DS, AB._SYN_LOG_DE)) | set(AB._SYN_LOG_CTRL)
            for lcn in AB._SYN_LIT_LCN.values():
                taken |= set(range(lcn, lcn + 4))
        self.free = [l for l in _FREE_PAGES if not any(x in taken for x in range(l, l + 4))]
        self.objects, self.old_objects, self.orphans = {}, None, {}
        self.digests = False

    def alloc(self):
        _fx(self.free, "the synthetic volume ran out of free pages")
        return self.free.pop(0)

    def tree(self, dirs):
        objs = {}
        for oid, d in dirs.items():
            live = [_row(_name_key(cd["name"]), _dir_value(c)) for c, cd in dirs.items() if cd.get("parent") == oid]
            live += list(d.get("files", ()))
            live.sort(key=lambda r: r[0x10:0x10 + struct.unpack_from("<H", r, 6)[0]])
            lcn = self.alloc()
            objs[oid] = (lcn, _page(lcn, oid, live, d.get("slack", ())))
        return objs

    def orphan(self, table_oid, rows):
        lcn = self.alloc()
        self.orphans[lcn] = _page(lcn, table_oid, rows)
        return lcn

    def write(self, path):
        if self.log:
            for objs in [self.objects] + ([self.old_objects] if self.old_objects is not None else []):
                for oid, lcn in AB._SYN_LIT_LCN.items():
                    objs.setdefault(oid, (lcn, AB._syn_lit_page(oid)))
            self.digests = True                          # the log's table pages carry their CRC64, as AB's do
        old = self.objects if self.old_objects is None else self.old_objects
        new_ot = _ot(_OT_LCN, self.objects, self.digests)
        old_lcn = _OT_LCN if old is self.objects else self.alloc()
        old_ot = new_ot if old is self.objects else _ot(old_lcn, old, self.digests)
        with open(path, "wb") as fh:
            fh.truncate(_N * CS)

            def put(off, data):
                fh.seek(off)
                fh.write(data)
            put(0, AB._syn_vbr())
            put(_N * CS - 512, AB._syn_vbr())
            for lcn in (AB.SYN.supb,) + AB.SYN.backups:
                put(lcn * CS, AB._syn_supb(lcn))
            put(_LO * CS, _chkp(_LO, AB.CLOCK_NEW, AB.ALLOC_NEW, _OT_LCN, new_ot))
            put(_HI * CS, _chkp(_HI, AB.CLOCK_OLD, AB.ALLOC_OLD, old_lcn, old_ot))
            for i in range(1, 13):
                put((0xA0 + 4 * i) * CS, AB._syn_root_page(i, objects=False))      # its own Object Table (root 5: no rows, as before)
            put(_OT_LCN * CS, new_ot)
            put(old_lcn * CS, old_ot)
            for objs in (old, self.objects):
                for lcn, pg in objs.values():
                    put(lcn * CS, pg)
            for lcn, pg in self.orphans.items():
                put(lcn * CS, pg)
            if self.log:
                for lcn, c in zip(AB._SYN_LOG_CTRL, AB._syn_log_control()):
                    put(lcn * CS, c)
        return path


# ─── running the tool ─────────────────────────────────────────────────────────────────────────────────────────

def _run(image, *args, cli=(), cwd=None):
    """(rc, stdout, stderr). A traceback or a timeout is a fixture error, never the defect under test."""
    cmd = [sys.executable, "-B", FOREFST, image] + list(args) + list(cli)
    try:
        r = UW.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=cwd or os.path.dirname(image))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


def _syn(path, *args):
    return _run(path, *args, cli=["--partition-start", "0"])


def _syn_csv(path, *args):
    """`deleted --csv FILE` on a synthetic volume: (rc, stdout, stderr, csv rows)."""
    dest = path + ".deleted.csv"
    rc, out, err = _syn(path, *args, "--csv", dest)
    _fx(os.path.exists(dest), "deleted --csv wrote no file:\n" + err[-2000:])
    with open(dest, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    os.unlink(dest)
    return rc, out, err, rows


def _ctx(rc, out, err=""):
    return "\n| rc=%s\n%s\n--- stderr ---\n%s" % (rc, out[-6000:], err[-2500:])


# ─── reading `deleted` output ─────────────────────────────────────────────────────────────────────────────────

SLACK, SCAN, CHKP = "── B+-tree Node Slack Scan", "── Orphaned Page Scan", "── Checkpoint Comparison"


def _section(out, title):
    """The text of the section whose title line starts with `title`, up to the next '── ' title."""
    i = out.find(title)
    _fx(i >= 0, "no %r section in the output" % title)
    j = out.find("\n── ", i + len(title))
    return out[i:j if j >= 0 else len(out)]


def _report(out):
    """Every section of the `deleted` report before its methods footer: B8's fix may list a renamed remnant in a
    section of its own, so B8 looks for the remnant anywhere in the report, not only in the slack section."""
    i = out.find("── Recovery methods")
    return out[:i] if i >= 0 else out


def _name_rx(name):
    return re.compile(r"(?<![\w.\-])" + re.escape(name) + r"(?![\w.\-])")


def _indent(ln):
    return len(ln) - len(ln.lstrip(" "))


def _mentions(section, name):
    """Every entry of `section` that names `name`: [(header, sub-header, block)]. The header is the nearest line at
    indent 2 above it (a list heading such as 'DELETED (...)' or 'Old versions of existing files'), the
    sub-header a '+ N partial remnants (...)' line at indent 4, the block the entry line with its deeper lines."""
    lines, rx, out = section.splitlines(), _name_rx(name), []
    header = sub = ""
    for i, ln in enumerate(lines):
        s, ind = ln.strip(), _indent(ln)
        if not s:
            continue
        if ind <= 2:
            header, sub = s, ""
            continue
        if ind == 4:
            sub = s if s.startswith("+") else ""
        if rx.search(ln):
            blk = [ln]
            for nx in lines[i + 1:]:
                if not nx.strip() or _indent(nx) <= ind:
                    break
                blk.append(nx)
            out.append((header, sub, "\n".join(blk)))
    return out


_DELETED_H = re.compile(r"\bdeleted\b", re.I)
_PRIOR_H = re.compile(r"old version|still present|existing file|prior version", re.I)
_HEDGE = re.compile(r"renamed|former name", re.I)
_OR_RENAMED = re.compile(r"deleted,?\s+or\s+renamed", re.I)
_FILEREF = re.compile(r"0x[0-9a-f]+:0x[0-9a-f]+", re.I)


def _is_deleted_list(header):
    return bool(_DELETED_H.search(header)) and not _PRIOR_H.search(header)


def _deleted_alone(m):
    """An entry presented as a plain deletion: under a DELETED list, with no 'renamed' / 'former name' anywhere in
    its heading or its lines."""
    header, sub, block = m
    return _is_deleted_list(header) and not _HEDGE.search(" ".join((header, sub, block)))


def _mention_ctx(m):
    return " | ".join(x for x in m if x)


_OLD_REPORT = """── B+-tree Node Slack Scan (Method 5) ──
  Scanned 15 live pages

  DELETED (no live file with this name + creation time remains on the volume): 2  [2 with valid timestamps, 0 partial remnants]

    FILE movesamedir.txt  (non-resident, live-slack @ cluster 36 off 0x130)
      Deleted from: /testmove1  (table 0x761)
      Created:  2025-08-18 14:13:21 UTC
    FILE gone.txt  (non-resident, live-slack @ cluster 36 off 0x1b8)
      Deleted from: /testmove1  (table 0x761)

  STILL PRESENT — a live file with this name + creation time exists (CoW remnants, and former locations of moved/renamed files): 1  [1 with valid timestamps]
    same.txt  (live-slack @ cluster 36 off 0x240) — metadata only
── Orphaned Page Scan ──
  DELETED entries (not in current directory tree): 1

    FILE dup.txt  (non-resident)
      Found at: cluster 96 (offset 0x60000)

  Old versions of existing files (orphaned pages): 1
    notes.txt (cluster 96) — metadata only
── Recovery methods ──
  DELETED files: 0 of 2 are INLINE
"""
_FIXED_REPORT = """── B+-tree Node Slack Scan (Method 5) ──
  DELETED (FileRef live nowhere): 1
    FILE gone.txt  (live-slack @ cluster 36 off 0x1b8)
      Deleted from: /testmove1  (table 0x761)
  DELETED, OR RENAMED (no FileRef and no journal record): 1
    FILE oldname.txt  (live-slack @ cluster 36 off 0x160)
── Former names of live files ──
  RENAMED (the FileRef is live): 1
    FILE movesamedir.txt  (live-slack @ cluster 36 off 0x130) — former name of 0x761:0x4 (/testmove1/movedsamedir.txt)
── Recovery methods ──
"""


def test_b2_matchers():
    """Control: the report readers on 1.13.1's own layout and on a layout a fix could print."""
    old = _mentions(_report(_OLD_REPORT), "movesamedir.txt")
    _keep(len(old) == 1 and _deleted_alone(old[0]), "1.13.1's DELETED entry is not read as DELETED alone")
    _keep(not _mentions(_report(_OLD_REPORT), "movedsamedir.txt"), "a longer name matched a shorter one")
    _keep(_PRIOR_H.search(_mentions(_OLD_REPORT, "same.txt")[0][0]) and
          not _deleted_alone(_mentions(_OLD_REPORT, "same.txt")[0]), "STILL PRESENT read as deleted")
    _keep(_is_deleted_list(_mentions(_section(_OLD_REPORT, SCAN), "dup.txt")[0][0]) and
          _clusters(_mentions(_section(_OLD_REPORT, SCAN), "dup.txt")[0][2]) == {96}, "scan-pages DELETED entry")
    _keep(_PRIOR_H.search(_mentions(_section(_OLD_REPORT, SCAN), "notes.txt")[0][0]), "scan-pages old version")
    new = _mentions(_report(_FIXED_REPORT), "movesamedir.txt")
    _keep(new and not any(_deleted_alone(m) for m in new) and "0x761:0x4" in _mention_ctx(new[0]).lower(),
          "a fixed 'former name of 0x761:0x4' entry is not accepted")
    und = _mentions(_report(_FIXED_REPORT), "oldname.txt")
    _keep(und and _OR_RENAMED.search(_mention_ctx(und[0])) and not _deleted_alone(und[0]),
          "a fixed 'deleted, or renamed' entry is not accepted")
    dead = _mentions(_report(_FIXED_REPORT), "gone.txt")
    _keep(dead and _is_deleted_list(dead[0][0]) and not _OR_RENAMED.search(_mention_ctx(dead[0])),
          "a decided deletion is not read as a plain deletion")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The builder, checked independently of the tool
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_b2_fixture_builder_is_sound(tmp_path):
    """Control. The bytes the REDs stand on, read back with this module's own parsing: self-checksums by an
    independent CRC32-C, the checkpoints' root CRC64s, the Object Table map, the live/slack split of a page."""
    v = DirVol()
    live = _row(_name_key("a.txt"), _file_value(2, 0x761, _T))
    dead = _row(_name_key("b.txt"), _file_value(3, 0x761, _T + _S))
    v.objects = v.tree({0x600: {"name": ""}, 0x761: {"parent": 0x600, "name": "d", "files": [live],
                                                     "slack": [dead]}})
    path = v.write(str(tmp_path / "t.raw"))
    with open(path, "rb") as fh:
        img = fh.read()
    blk = lambda l: img[l * CS:(l + 1) * CS]                                   # noqa: E731
    for lcn, desc in ((AB.SYN.supb, AB.SUPB_DESC), (_LO, AB.CHKP_DESC), (_HI, AB.CHKP_DESC)):
        b = blk(lcn)
        _keep(b[desc + 0x28:desc + 0x2C] == AB._own_digest(b, desc), "self-checksum of 0x%x" % lcn)
    for lcn in (_LO, _HI):
        c = blk(lcn)
        ro = 0x110
        _keep(F.le64(c, ro) == _OT_LCN and F.le64(c, ro + 0x28) == F.refs_crc64(img[_OT_LCN * CS:_OT_LCN * CS + PAGE]),
              "checkpoint 0x%x root 0 reference" % lcn)
    ot = img[_OT_LCN * CS:_OT_LCN * CS + PAGE]
    thoff = 0x50 + F.le32(ot, 0x50)
    astart, aend = F.le32(ot, thoff + 16), F.le32(ot, thoff + 32)
    got = {}
    for i in range((aend - astart) // 4):
        ro = thoff + F.le16(ot, thoff + astart + 4 * i)
        _s, ko, kl, _f, vo, vl, _p = struct.unpack_from("<I6H", ot, ro)
        got[F.le64(ot, ro + ko + 8)] = F.le64(ot, ro + vo + 0x20)
    _keep(got == {o: l for o, (l, _p) in v.objects.items()}, "Object Table map %r" % got)
    lcn = v.objects[0x761][0]
    pg = img[lcn * CS:lcn * CS + PAGE]
    thoff = 0x50 + F.le32(pg, 0x50)
    astart, aend = F.le32(pg, thoff + 16), F.le32(pg, thoff + 32)
    live_offs = {thoff + F.le16(pg, thoff + astart + 4 * i) for i in range((aend - astart) // 4)}
    _keep(pg.find(_name_key("a.txt")) - 0x10 in live_offs, "a.txt is a live row")
    _keep(pg.find(_name_key("b.txt")) - 0x10 not in live_offs and pg.find(_name_key("b.txt")) > 0,
          "b.txt is in the page but not in the offset array")
    rc, out, err = _syn(path, "files", "-q")
    _keep(rc == 0 and "d/a.txt" in out and "b.txt" not in out, "files lists the live tree only" + _ctx(rc, out, err))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B8 -- a renamed file's old name is listed as DELETED (identity = name + exact creation time)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# One volume, the measured case rebuilt: testmove1 (0x761) holds the live `movedsamedir.txt` (0x761:0x4) and, in
# its page's free space, the old-name row `movesamedir.txt` with the same value (same creation time, same FileRef:
# a same-directory rename, as on win11refs8gtestmove_aftermove). Beside it: a remnant with no FileRef (undecidable
# without a journal; the volume has none), a remnant whose FileRef is live nowhere (a deletion the tool can
# decide), and a CoW remnant of an unrenamed live file.

_B8 = {}


def _b8(tmp_path_factory):
    if "run" not in _B8:
        v = DirVol()
        ct = _T + _S
        files = [_row(_name_key("movedsamedir.txt"), _file_value(4, 0x761, ct)),
                 _row(_name_key("res_new1.txt"), _resident_value(_T + 5 * _S, 6, 0x761, "res_new1.txt")),
                 _row(_name_key("same.txt"), _file_value(5, 0x761, _T + 4 * _S))]
        slack = [_row(_name_key("movesamedir.txt"), _file_value(4, 0x761, ct)),        # renamed: FileRef kept
                 _row(_name_key("res_old1.txt"), _resident_value(_T + 5 * _S, 6, 0x761, "res_old1.txt")),
                 _row(_name_key("oldname.txt"), _file_value(0, 0, _T + 2 * _S)),       # no FileRef, no journal
                 _row(_name_key("gone.txt"), _file_value(9, 0x761, _T + 3 * _S)),      # FileRef live nowhere
                 _row(_name_key("same.txt"), _file_value(5, 0x761, _T + 4 * _S))]      # CoW remnant, unrenamed
        v.objects = v.tree({0x600: {"name": ""},
                            0x761: {"parent": 0x600, "name": "testmove1", "files": files, "slack": slack}})
        path = v.write(str(tmp_path_factory.mktemp("b8") / "target.raw"))
        rc, out, err = _syn(path, "files", "-q")
        _fx(rc == 0 and re.search(r"^0x761:0x4,testmove1/movedsamedir\.txt,", out, re.M)
            and re.search(r"^0x761:0x6,testmove1/res_new1\.txt,", out, re.M)
            and re.search(r"^0x761:0x5,testmove1/same\.txt,", out, re.M)
            and not re.search(r"movesamedir\.txt|res_old1\.txt|gone\.txt|oldname\.txt", out),
            "the live tree is not 0x761:0x4 movedsamedir.txt, 0x761:0x6 res_new1.txt, 0x761:0x5 same.txt"
            + _ctx(rc, out, err))
        _B8["run"] = _syn_csv(path, "deleted", "-v")          # group 2: the blocks are under -v
    return _B8["run"]


@pytest.fixture(scope="module")
def b8(tmp_path_factory):
    return _b8(tmp_path_factory)


_B8_RENAMES = [pytest.param("movesamedir.txt", "0x761:0x4", id="short-row"),     # FileRef at value+0x08:+0x00
               pytest.param("res_old1.txt", "0x761:0x6", id="resident-row")]      # table OID : value+0x80


# B8: green in wave D step D1 (RED until then: a same-directory rename's old name is listed as DELETED (identity = name + exact creation time, fd:12391-12403, :12510); it must be shown as a form...)
@pytest.mark.parametrize("old, ref", _B8_RENAMES)
def test_b8_same_dir_rename_is_a_former_name_of_the_live_fileref(b8, old, ref):
    rc, out, err, _rows = b8
    ms = _mentions(_report(out), old)
    _fx(ms, "the remnant %s is not shown at all (1.13.1 lists it; a fix must too)" % old + _ctx(rc, out, err))
    alone = [_mention_ctx(m) for m in ms if _deleted_alone(m)]
    assert not alone, "listed as DELETED although its FileRef %s is live:\n  " % ref + "\n  ".join(alone)
    assert any(ref in _mention_ctx(m).lower() for m in ms), \
        "not shown as a former name of %s:\n  " % ref + "\n  ".join(_mention_ctx(m) for m in ms)


# B8: green in wave D step D1 (RED until then: deleted --csv exports the renamed file's old name as a plain deletion row (_deleted_rows over the DELETED list, fd:13791))
@pytest.mark.parametrize("old, ref", _B8_RENAMES)
def test_b8_same_dir_rename_is_not_exported_as_a_plain_deletion(b8, old, ref):
    rc, out, err, rows = b8
    mine = [r for r in rows if r.get("FileName") == old]
    plain = [r for r in mine if not any(_HEDGE.search(str(c)) or ref in str(c).lower() for c in r.values())]
    assert not plain, "exported as a deletion with no link to %s: %r" % (ref, plain)


# B8: green in wave D step D1 (RED until then: a remnant with no FileRef and no journal record is listed as DELETED alone; the row must say 'deleted, or renamed' as the published advice does)
def test_b8_remnant_without_fileref_or_journal_says_deleted_or_renamed(b8):
    rc, out, err, _rows = b8
    ms = _mentions(_report(out), "oldname.txt")
    _fx(ms, "the remnant is not shown at all (1.13.1 lists it; a fix must too)" + _ctx(rc, out, err))
    bad = [_mention_ctx(m) for m in ms if not _OR_RENAMED.search(_mention_ctx(m))]
    assert not bad, "the undecidable remnant does not say 'deleted, or renamed':\n  " + "\n  ".join(bad)


def test_b8_control_remnant_whose_fileref_is_dead_stays_deleted(b8):
    """Control (passes on 1.13.1, must keep passing): a remnant whose FileRef (0x761:0x9) no live file carries is a
    deletion the tool can decide -- FileIds are never re-used (E66) and a rename or move keeps them (N77) -- so it
    stays in a DELETED list without the 'or renamed' hedge. Stops RED 3 from being passed by a blanket hedge."""
    rc, out, err, rows = b8
    ms = _mentions(_report(out), "gone.txt")
    _keep(ms and all(_is_deleted_list(m[0]) for m in ms), "gone.txt is not in a DELETED list" + _ctx(rc, out, err))
    _keep(not any(_OR_RENAMED.search(_mention_ctx(m)) for m in ms), "a decidable deletion is hedged 'or renamed'")
    _keep(any(r.get("FileName") == "gone.txt" for r in rows), "gone.txt missing from the deleted CSV")


def test_b8_control_cow_remnant_of_an_unrenamed_file_stays_still_present(b8):
    """Control: a remnant with the live file's name, creation time and FileRef is a prior version, not a deletion
    (1.13.1 already gets this right; the fix must keep it)."""
    rc, out, err, rows = b8
    ms = _mentions(_report(out), "same.txt")
    _keep(ms and all(_PRIOR_H.search(m[0]) for m in ms), "same.txt is not a still-present remnant" + _ctx(rc, out, err))
    # acceptance 1.14.0 (E-1 / N315): every entry the view prints is a row, with its Status -- the remnant's row says
    # "still present", never a deletion
    _keep(all(r.get("Status") == "still present" for r in rows if r.get("FileName") == "same.txt"),
          "same.txt exported as a deletion: %r" % [r.get("Status") for r in rows if r.get("FileName") == "same.txt"])
    _keep(rc == 0, "the healthy synthetic volume does not exit 0 (rc=%s)" % rc)


# ─── B8 on the corpus ─────────────────────────────────────────────────────────────────────────────────────────

_IMAGE_RUNS = {}


def _image_or_skip(name):
    p = _corpus_image(name)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return p


def _image_deleted(name, *args):
    """`deleted [args] --csv FILE` on a READ-ONLY corpus image, once per session: (rc, out, err, csv rows). The CSV
    goes to a private directory under SCRATCH, removed by its exact path."""
    key = (name,) + args
    if key not in _IMAGE_RUNS:
        img = _image_or_skip(name)
        os.makedirs(SCRATCH, exist_ok=True)
        d = tempfile.mkdtemp(prefix="b2_deleted_", dir=SCRATCH)
        try:
            dest = os.path.join(d, "deleted.csv")
            # group 2 (1.14.0): the entry blocks these readers parse are printed under -v (PLAN 10.2 E)
            rc, out, err = _run(img, "deleted", "-v", *args, "--csv", dest, cwd=d)
            _fx(os.path.exists(dest), "deleted --csv wrote no file:\n" + err[-2000:])
            with open(dest, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        _IMAGE_RUNS[key] = (rc, out, err, rows)
    return _IMAGE_RUNS[key]


# B8: green in wave D step D1 (RED until then: on win11refs8gtestmove_aftermove `movesamedir.txt` is listed DELETED (FULL FILE recoverable) while its renamed self testmove1/movedsamedir.txt (0x7...)
def test_b8_image_aftermove_movesamedir_is_a_former_name_of_0x761_0x4():
    rc, out, err, rows = _image_deleted("win11refs8gtestmove_aftermove.raw")
    _fx(os.path.getsize(_image_or_skip("win11refs8gtestmove_aftermove.raw")) == 8 << 30 and "3.14" in out,
        "not the 8 GiB v3.14 aftermove volume" + _ctx(rc, out, err))
    ms = _mentions(_report(out), "movesamedir.txt")
    # the record the plan asks for first ("measure whether slack remnants keep the FileRef fields"): the remnant's
    # own bytes, read from the image at the cluster and offset the tool printed, independently of the tool
    img = _image_or_skip("win11refs8gtestmove_aftermove.raw")
    for _h, _s, blk in ms:
        mm = re.search(r"@ cluster (\d+) off (0x[0-9a-f]+)", blk)
        if not mm:
            continue
        with open(img, "rb") as fh:            # partition at 16 MiB (0x1000000), as on the other corpus images
            fh.seek(0x1000000 + int(mm.group(1)) * CS + int(mm.group(2), 16))
            hdr = fh.read(0x800)
        _sz, ko, kl, _f, vo, vl, _p = struct.unpack_from("<I6H", hdr, 0)
        if hdr[ko + 4:ko + kl] != "movesamedir.txt".encode("utf-16-le") or vo + vl > len(hdr):
            print("[B8 record] the bytes at cluster %s off %s are not the remnant row" % mm.groups())
            continue
        val = hdr[vo:vo + vl]
        fid = F.le64(val, 0x80) if vl > 0x88 else F.le64(val, 0)
        home = "owning table (page+0x48)" if vl > 0x88 else "0x%x" % F.le64(val, 8)
        print("[B8 record] remnant movesamedir.txt @ cluster %s off %s: value %d bytes (%s); FileRef = %s:0x%x"
              % (mm.group(1), mm.group(2), vl, "resident" if vl > 0x88 else "short", home, fid))
    _fx(ms, "movesamedir.txt is not shown at all (1.13.1 lists it DELETED; a fix must still show it)"
        + _ctx(rc, out, err))
    alone = [_mention_ctx(m) for m in ms if _deleted_alone(m)]
    assert not alone, "listed as DELETED although 0x761:0x4 is live:\n  " + "\n  ".join(alone)
    assert any("0x761:0x4" in _mention_ctx(m).lower() for m in ms), \
        "not shown as a former name of 0x761:0x4:\n  " + "\n  ".join(_mention_ctx(m) for m in ms)


MFTECMD = "win11refstestmftecmd.raw"
_EXPORT = os.path.join(REPO, "analysis", "samples", "disks", "win11refstestmftecmd", "provenance",
                       "usn_readjournal_export.txt")
_IMAGE_LAST_USN = 917280          # provenance/commands.md s.3: image and export agree record-for-record to here
_RENAME_OLD, _FILE_DELETE = 0x1000, 0x200


def _windows_journal():
    """Windows' own `fsutil usn readjournal` export, parsed: [{usn, name, reason, ref, parent}] bounded to the
    records the image holds. ref = HomeOID:FileID as `files` prints ObjectRef; parent = the parent's home OID."""
    if not os.path.exists(_EXPORT):
        pytest.skip("the win11refstestmftecmd sample's journal export is not in this tree")
    with open(_EXPORT, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    _fx("USN Journal ID    : 0x01dcea86b624a787" in text, "not the win11refstestmftecmd journal export")
    recs = []
    for blk in text.split("\n\n"):
        d = {}
        for ln in blk.splitlines():
            k, sep, val = ln.partition(" : ")
            if sep:
                d[k.strip()] = val.strip()
        if "Usn" in d and "File ID" in d and "Parent file ID" in d:
            fid, par = d["File ID"], d["Parent file ID"]
            recs.append({"usn": int(d["Usn"]), "name": d.get("File name", ""),
                         "reason": int(d["Reason"].split(":")[0], 16),
                         "ref": "0x%x:0x%x" % (int(fid[:16], 16), int(fid[16:], 16)), "parent": int(par[:16], 16)})
    _fx(len(recs) == 9367 and any(r["usn"] == _IMAGE_LAST_USN for r in recs),
        "the export does not hold the 9,367 records and the image's last USN")
    return [r for r in recs if r["usn"] <= _IMAGE_LAST_USN]


def _journal_verdicts(recs):
    """{(name, parent OID): 'renamed-live' | 'deleted'} from the image-bounded journal. renamed-live: a
    RENAME_OLD_NAME record carries the name in that directory and EVERY file that ever carried the name there is
    still live at the image's last record; deleted: every such file's last record is FILE_DELETE."""
    last = {}
    for r in sorted(recs, key=lambda r: r["usn"]):
        last[r["ref"]] = r
    alive = {ref for ref, r in last.items() if not r["reason"] & _FILE_DELETE}
    by = {}
    for r in recs:
        by.setdefault((r["name"], r["parent"]), []).append(r)
    out = {}
    for key, rs in by.items():
        refs = {r["ref"] for r in rs}
        if any(r["reason"] & _RENAME_OLD for r in rs) and refs <= alive:
            out[key] = "renamed-live"
        elif not refs & alive:
            out[key] = "deleted"
    return out


def _slack_entries_with_table(out):
    """Every entry of the slack section that names an owning table: [(name, table OID, mention)]."""
    sec = _section(out, SLACK)
    res = []
    lines = sec.splitlines()
    for i, ln in enumerate(lines):
        mm = re.match(r"^    (?:FILE|DIR )?\s*(\S.*?)  \(", ln)
        if not mm or _indent(ln) != 4:
            continue
        blk = [ln]
        for nx in lines[i + 1:]:
            if not nx.strip() or _indent(nx) <= 4:
                break
            blk.append(nx)
        t = re.search(r"table (0x[0-9a-f]+)", "\n".join(blk))
        if t:
            name = mm.group(1)
            for m in _mentions(sec, name):
                if m[2].startswith(ln):
                    res.append((name, int(t.group(1), 16), m))
    return res


# B8: green in wave D step D1 (RED until then: on win11refstestmftecmd (the 101's running case) 78 remnants that Windows' own journal shows to be the old names of renamed files still live are li...)
def test_b8_image_mftecmd_journal_resolved_renames_are_not_deleted_alone():
    verdict = _journal_verdicts(_windows_journal())
    rc, out, err, _rows = _image_deleted(MFTECMD)
    _fx(re.search(r"Objects:\s+250\b", out) and re.search(r"\b617\b", out) and "3.14" in out,
        "not the win11refstestmftecmd image the export belongs to (250 objects, checkpoint 617)" + _ctx(rc, out, err))
    ents = _slack_entries_with_table(out)
    _fx(ents, "no slack entry names its owning table" + _ctx(rc, out, err))
    alone = [(n, t, m) for n, t, m in ents if _deleted_alone(m)]
    bad = sorted({(n, t) for n, t, m in alone if verdict.get((n, t)) == "renamed-live"})
    ren_all = sorted({(n, t) for n, t, m in ents if verdict.get((n, t)) == "renamed-live"})
    print("[B8 probe] win11refstestmftecmd `deleted`: %d slack entries name a table, %d are DELETED alone; Windows' "
          "journal (USN <= %d) resolves %d (name, directory) pairs to renamed files still live, %d of them DELETED "
          "alone (1.13.1: 78 of 318). N113's '140 of 256' used name-only matching and records past the image."
          % (len(ents), len(alone), _IMAGE_LAST_USN, len(ren_all), len(bad)))
    assert not bad, "%d remnants resolved by the journal to a live renamed file are DELETED alone, e.g. %s" % (
        len(bad), ", ".join("%s (table 0x%x)" % x for x in bad[:8]))


def test_b8_control_image_mftecmd_journal_confirmed_deletions_stay_deleted():
    """Control: every remnant whose (name, directory) Windows' journal shows deleted -- every file that carried
    it there ends with FILE_DELETE by the image's last record -- is still listed as deleted (hedged or not), and
    never as a still-present or former-name remnant. 1.13.1: 34 such entries."""
    verdict = _journal_verdicts(_windows_journal())
    rc, out, err, _rows = _image_deleted(MFTECMD)
    ents = [(n, t, m) for n, t, m in _slack_entries_with_table(out) if verdict.get((n, t)) == "deleted"]
    _fx(len(ents) >= 20, "fewer journal-confirmed deletions than 1.13.1 lists (34): %d" % len(ents))
    moved = [(n, t) for n, t, m in ents if not _is_deleted_list(m[0]) or re.search(r"former name", _mention_ctx(m), re.I)]
    _keep(not moved, "journal-confirmed deletions reclassified as live: %r" % moved[:8])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N129 -- the page-slack scan reads inside live rows and takes $OBJ_LINK keys for name rows
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# A directory whose OID is 0xD826 (the parent OID of the dumped winsiderv2 key) holds a resident file whose
# embedded record carries an $OBJ_LINK sub-record naming that parent. `_scan_page_slack` steps through the page
# 4 bytes at a time skipping only live row STARTS (fd:12241-12250), finds the sub-record, reads its value length
# 0x30 as key type 0x30 (fd:12258) and decodes the name from key+4, where the parent OID is a lone surrogate:
# a decode skip, then exit 2 (E2's evidence line, verbatim: "position 12-13: illegal UTF-16 surrogate").
# The same key with an ordinary OID (0x761) decodes and is dropped by the printable filter (fd:12262), silently.

_DECODE_SKIP = re.compile(r"filename decode|illegal UTF-16 surrogate", re.I)


def _n129_volume(path, dir_oid, where, n_keys=1):
    """where = 'live': the $OBJ_LINK key is inside a live row; 'slack': inside deleted rows in the free space."""
    v = DirVol()
    if where == "live":
        files = [_row(_name_key("report12.txt"), _resident_value(_T + _S, 2, dir_oid, "report12.txt"))]
        slack = []
    else:
        files = [_row(_name_key("keep.txt"), _file_value(3, dir_oid, _T))]
        slack = [_row(_name_key(n), _resident_value(_T + (4 + i) * _S, 4 + i, dir_oid, n))
                 for i, n in enumerate(("gone12ab.txt", "gone12cd.txt", "gone12ef.txt")[:n_keys])]
    v.objects = v.tree({0x600: {"name": ""}, dir_oid: {"parent": 0x600, "name": "inbox", "files": files,
                                                       "slack": slack}})
    return v.write(path)


# N129: green in wave D step D1 (RED until then: an $OBJ_LINK key inside a LIVE row, parent OID 0xD826, is decoded as a name: a filename-decode skip and exit 2 on a healthy volume)
def test_n129_objlink_key_inside_a_live_row_is_not_a_decode_skip(tmp_path):
    path = _n129_volume(str(tmp_path / "target.raw"), 0xD826, "live")
    rc, out, err = _syn(path, "deleted")
    assert not _DECODE_SKIP.search(err), "a decode skip from inside a live row:" + _ctx(rc, "", err)
    assert rc == 0, "exit %s on a healthy volume" % rc + _ctx(rc, out, err)


# N129: green in wave D step D1 (RED until then: an $OBJ_LINK sub-record inside a deleted row in slack is taken for a name row: a decode skip and exit 2 (142 of winsiderv2's 467 are not inside liv...)
def test_n129_objlink_key_in_slack_is_not_a_decode_skip(tmp_path):
    path = _n129_volume(str(tmp_path / "target.raw"), 0xD826, "slack", n_keys=3)
    rc, out, err = _syn(path, "deleted")
    ms = _mentions(_section(out, SLACK), "gone12ab.txt")
    _keep(ms and all(_is_deleted_list(m[0]) for m in ms), "the deleted row itself is no longer recovered")
    assert not _DECODE_SKIP.search(err), "a decode skip from an $OBJ_LINK key in slack:" + _ctx(rc, "", err)
    assert rc == 0, "exit %s on a healthy volume" % rc + _ctx(rc, out, err)


@pytest.mark.parametrize("where", ["live", "slack"])
def test_n129_control_objlink_key_with_an_ordinary_oid_exits_0(tmp_path, where):
    """Control: the same volumes with the directory at OID 0x761. 1.13.1 exits 0 (the key decodes and the
    printable filter drops it), so the only difference from the two REDs above is the OID's value."""
    path = _n129_volume(str(tmp_path / "target.raw"), 0x761, where, n_keys=3)
    rc, out, err = _syn(path, "deleted")
    _keep(rc == 0 and not _DECODE_SKIP.search(err), "the control does not exit 0 cleanly" + _ctx(rc, out, err))
    if where == "slack":
        _keep(all(_mentions(_section(out, SLACK), n) for n in ("gone12ab.txt", "gone12cd.txt", "gone12ef.txt")),
              "the three deleted rows are not listed" + _ctx(rc, out, err))


# N129: green in wave D step D1 (RED until then: the slack scan recovers a row from INSIDE a live row's bytes (it skips only live row starts, fd:12241-12250) and lists it as DELETED)
def test_n129_no_remnant_is_recovered_from_inside_a_live_row(tmp_path):
    """Constructed (no corpus row has this shape): a live resident row whose value holds bytes shaped like a
    directory-entry row with a printable name. The live row owns those bytes, so no remnant can be there."""
    v = DirVol()
    inner = _row(_name_key("phantom.txt"), _file_value(9, 0x761, _T + 9 * _S))
    val = bytearray(0x200)
    struct.pack_into("<QQQQ", val, 0x28, _T + _S, _T + _S, _T + _S, _T + _S)
    struct.pack_into("<I", val, 0x48, 0x20)
    struct.pack_into("<Q", val, 0x80, 2)
    val[0xB0:0xB0 + len(inner)] = inner
    v.objects = v.tree({0x600: {"name": ""}, 0x761: {"parent": 0x600, "name": "inbox",
                                                     "files": [_row(_name_key("carrier.txt"), bytes(val))]}})
    path = v.write(str(tmp_path / "target.raw"))
    rc, out, err = _syn(path, "deleted")
    _keep(rc == 0, "exit %s" % rc + _ctx(rc, out, err))
    ms = _mentions(_section(out, SLACK), "phantom.txt")
    assert not ms, "a remnant recovered from inside the live row carrier.txt:\n  " + "\n  ".join(map(_mention_ctx, ms))


# N129: green in wave D step D1 (RED until then: the $OBJ_LINK keys the slack scan meets are dropped by its printable filter without a count (18,397 on winsiderv2); acceptance inferred from the it...)
def test_n129_objlink_keys_set_aside_are_counted(tmp_path):
    """Re-scoped at wave D (DECISION_SCAN_WAVES_B_E N129 settlement, node 18): the keys are EXCLUDED BY STRUCTURE --
    the scan does not read inside a row it recovered, where the three $OBJ_LINK sub-records sit -- and what it set
    aside is counted on the scan's line (the instrument rule: a filter says what it dropped). The line names them as
    records inside another row (an embedded record's sub-records), 3 of them, and no name of theirs is listed."""
    path = _n129_volume(str(tmp_path / "target.raw"), 0x761, "slack", n_keys=3)
    rc, out, err = _syn(path, "deleted")
    text = out + "\n" + err
    counted = [ln for ln in text.splitlines()
               if re.search(r"\$?OBJ_LINK|sub-?record", ln, re.I) and re.search(r"(?<![\w.])3(?![\w.])", ln)]
    assert counted, "the 3 $OBJ_LINK keys the scan set aside are not counted anywhere in the output"
    assert re.search(r"set aside by structure: .*\b3 row-shaped record\(s\) inside another row", text), counted


# N129: green in wave D step D1 (RED until then: deleted on winsiderv2 records 467 filename-decode skips: $OBJ_LINK keys whose parent OID is in 0xD800-0xDFFF (325 inside live rows))
def test_n129_image_winsiderv2_deleted_records_no_filename_decode_skip():
    rc, out, err, _rows = _image_deleted("winsiderv2.raw")
    _fx(os.path.getsize(_image_or_skip("winsiderv2.raw")) == 60 << 30 and "3.14" in out,
        "not the 60 GiB v3.14 winsiderv2 volume" + _ctx(rc, out, err))
    hits = [ln for ln in err.splitlines() if _DECODE_SKIP.search(ln)]
    assert not hits, "filename-decode skips on a healthy volume:\n  " + "\n  ".join(hits[:6])


# N129+N130: green in wave D step D2 (RED until then: deleted exits 2 on winsiderv2 (a healthy real installation): N129's 467 decode skips and N130's 3 misframed holder extents (B6); exit 0 needs both ...)
def test_n129_image_winsiderv2_deleted_exits_0():
    rc, out, err, _rows = _image_deleted("winsiderv2.raw")
    assert rc == 0, "exit %s on winsiderv2; skips:\n  %s" % (
        rc, "\n  ".join(ln for ln in err.splitlines() if "x " in ln and "[forefst]" in ln)[:3000])


def test_n129_control_image_winsider_deleted_exits_0_with_no_decode_skip():
    """Control: winsider, the same installation before the update (10,203 keys of the same shape, none with a
    parent OID in the surrogate range): exit 0 and no decode skip on 1.13.1, and after the fix."""
    rc, out, err, _rows = _image_deleted("winsider.raw")
    _keep(rc == 0 and not _DECODE_SKIP.search(err), "winsider does not exit 0 cleanly" + _ctx(rc, out, err))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N145 -- every `partial` row is called a name fragment; the grade tests only the two timestamps
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# The grade (fd:12271-12275): high = creation AND modification time in ~2009-11..2050-12, medium = one of them,
# partial = neither. The output (fd:14347-14348, :14370-14372) says of every partial row "name fragment only, no
# valid timestamps", and that partial remnants are "name fragments from a row whose body was partly
# overwritten"; the "[N with valid timestamps]" counts include medium rows (fd:14300-14308, :14357-14358).

_N145 = {}


def _n145(tmp_path_factory):
    if "run" not in _N145:
        v = DirVol()
        files = [_row(_name_key("keep.txt"), _file_value(2, 0x761, _T))]
        slack = [_row(_name_key("Q2_report_2005.docx"), _file_value(3, 0x761, _ft(2005, 6, 1), _ft(2005, 6, 2))),
                 _row(_name_key("both_ok.txt"), _file_value(4, 0x761, _T + _S)),
                 _row(_name_key("one_time_only.txt"), _file_value(5, 0x761, _T + 2 * _S, 0)),
                 _row(_name_key("keep.txt"), _file_value(2, 0x761, _T, 0))]        # CoW remnant, one time
        v.objects = v.tree({0x600: {"name": ""}, 0x761: {"parent": 0x600, "name": "docs", "files": files,
                                                         "slack": slack}})
        path = v.write(str(tmp_path_factory.mktemp("n145") / "target.raw"))
        _N145["run"] = _syn(path, "deleted", "-v")            # group 2: the blocks are under -v
    return _N145["run"]


@pytest.fixture(scope="module")
def n145(tmp_path_factory):
    return _n145(tmp_path_factory)


_FRAG = re.compile(r"fragment|partly overwritten|partially overwritten", re.I)
_HEDGED = re.compile(r"\b(may|might|can|could|possibly|perhaps|not|cannot|isn't|unless)\b", re.I)


def _claims_fragment(text):
    """True when the text states, without a hedge in the same clause, that a row IS a name fragment or partly
    overwritten. A clause starts after the last '.', ';', '(', ',' or dash before the word."""
    t = " ".join(text.split())
    for m in _FRAG.finditer(t):
        start = max(t.rfind(c, 0, m.start()) for c in ".;(,—") + 1
        if not _HEDGED.search(t[start:m.start()]):
            return True
    return False


def _states_window(text):
    t = " ".join(text.split())
    return bool((re.search(r"2009", t) and re.search(r"2050", t))
                or re.search(r"\b(outside|out of|beyond)\b.{0,40}\b(range|window|plausible|expected)", t, re.I))


def _note(section):
    lines = section.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().startswith("NOTE:"):
            blk = [ln]
            for nx in lines[i + 1:]:
                if not nx.strip() or _indent(nx) <= 2:
                    break
                blk.append(nx)
            return " ".join(x.strip() for x in blk)
    return ""


def test_n145_matchers():
    """Control: the matchers on 1.13.1's own sentences and on sentences a fix could print."""
    old_head = "+ 1 partial remnants (name fragment only, no valid timestamps — corroborate before use):"
    old_note = ("NOTE: slack rows are unindexed remnants. 'with valid timestamps' rows decode a full $SI (high "
                "confidence); 'partial remnants' are name fragments from a row whose body was partly overwritten — "
                "always corroborate before relying on one entry.")
    _keep(_claims_fragment(old_head) and _claims_fragment(old_note), "the matcher misses 1.13.1's claims")
    _keep(not _states_window(old_head) and not _states_window(old_note), "1.13.1 does not state the window")
    new = ("+ 1 with both times outside 2009-11..2050-12 (the name may be complete; the times may be preserved "
           "or backdated):")
    _keep(not _claims_fragment(new) and _states_window(new), "the matcher rejects a correct wording")
    _keep(not _claims_fragment("the name is not necessarily a fragment"), "a negated clause read as a claim")


# N145: green in wave D step D1 (RED until then: an intact name whose two times are outside ~2009-2050 is labelled 'name fragment only' (fd:14347-14348); the grade never looks at the name)
def test_n145_intact_name_with_out_of_window_times_is_not_called_a_fragment(n145):
    rc, out, err = n145
    ms = _mentions(_section(out, SLACK), "Q2_report_2005.docx")
    _keep(ms, "the remnant is not listed" + _ctx(rc, out, err))
    claims = [_mention_ctx(m) for m in ms if _claims_fragment(_mention_ctx(m))]
    assert not claims, "an intact name is called a fragment:\n  " + "\n  ".join(claims)


# N145: green in wave D step D1 (RED until then: the NOTE says partial remnants 'are name fragments from a row whose body was partly overwritten' (fd:14370-14372); the grade tests only two timestamps)
def test_n145_note_does_not_call_partial_rows_overwritten_fragments(n145):
    rc, out, err = n145
    note = _note(_section(out, SLACK))
    _keep(note, "no NOTE in the slack section" + _ctx(rc, out, err))
    assert not _claims_fragment(note), "the NOTE: " + note


# N145: green in wave D step D1 (RED until then: nothing says what the partial grade tests: creation and modification time outside ~2009-11..2050-12 (fd:12271-12275))
def test_n145_partial_grade_is_described_by_its_timestamp_window(n145):
    rc, out, err = n145
    sec = _section(out, SLACK)
    ms = _mentions(sec, "Q2_report_2005.docx")
    _keep(ms, "the remnant is not listed" + _ctx(rc, out, err))
    text = " ".join(_mention_ctx(m) for m in ms) + " " + _note(sec)
    assert _states_window(text), "the partial row's description never states the timestamp window: " + text


# N145: green in wave D step D1 (RED until then: the '[N with valid timestamps]' counts include rows with one timestamp outside the window (medium, fd:14300-14302): DELETED says 2 for 1, STILL PRE...)
def test_n145_valid_timestamp_counts_exclude_one_timestamp_rows(n145):
    rc, out, err = n145
    sec = _section(out, SLACK)
    want = {"deleted": 1, "still present": 0}            # both_ok.txt; the one-time keep.txt CoW remnant
    got = {}
    for ln in sec.splitlines():
        m = re.search(r"(\d+) with valid timestamps", ln)
        if m and _indent(ln) == 2:
            kind = "still present" if _PRIOR_H.search(ln) else ("deleted" if _DELETED_H.search(ln) else ln.strip())
            got[kind] = int(m.group(1))
    wrong = {k: (got[k], want.get(k)) for k in got if got[k] != want.get(k)}
    assert not wrong, "'with valid timestamps' counts (printed, true): %r" % wrong


def test_n145_control_row_with_both_times_in_window_is_listed_with_them(n145):
    """Control: a row whose two times are in the window is listed by name with both times (1.13.1 and after)."""
    rc, out, err = n145
    ms = _mentions(_section(out, SLACK), "both_ok.txt")
    _keep(ms and all(_is_deleted_list(m[0]) and "Created:" in m[2] and "Modified:" in m[2] for m in ms),
          "both_ok.txt is not listed with its times" + _ctx(rc, out, err))
    _keep(rc == 0, "the healthy synthetic volume does not exit 0 (rc=%s)" % rc)


# N145: green in wave D step D1 (RED until then: on win11refstestmftecmd the complete name 'elvis_dir_sync_708268' (Windows' journal carries it) is listed under 'name fragment only' (the public sa...)
def test_n145_image_mftecmd_journal_attested_name_is_not_called_a_fragment():
    names = {r["name"] for r in _windows_journal()}
    rc, out, err, _rows = _image_deleted(MFTECMD)
    sec = _section(out, SLACK)
    partial_lines = [ln for ln in sec.splitlines() if re.match(r"^      (['\"]).*\1  \(", ln)]
    whole = []
    for ln in partial_lines:
        nm = re.match(r"^      (['\"])(.*)\1  \(", ln).group(2)
        if nm in names:
            whole.extend(m for m in _mentions(sec, nm) if m[2].strip() == ln.strip())
    _fx(whole, "no partial row carries a name Windows' journal attests" + _ctx(rc, out, err))
    claims = [_mention_ctx(m) for m in whole if _claims_fragment(_mention_ctx(m))]
    assert not claims, "complete names called fragments:\n  " + "\n  ".join(claims[:6])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N146 -- `deleted --scan-pages` and the checkpoint differential classify by bare name to depth 10
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# --scan-pages (fd:14216-14228) collapses remnants by bare name (keeping one), then tests the name against
# `_get_current_files` (fd:12099, max_depth=10): a set of bare names. The checkpoint differential (fd:14176-14200)
# compares two such sets and prints "Same top-level files in both". The slack path classifies by (name, creation
# time) over the whole object map (fd:12391-12406, :12509).

def _chain(dirs, first_oid, n, parent=0x600):
    oids = [first_oid + i for i in range(n)]
    for i, o in enumerate(oids):
        dirs[o] = {"parent": parent if i == 0 else oids[i - 1], "name": "d%02d" % (i + 1)}
    return oids


_N146 = {}


def _n146_scan(tmp_path_factory):
    """Live: A(0x761)/notes.txt [0x761:0x2], A/shallow.txt [0x761:0x3]; d01/../d11/deep.txt [0x77a:0x7] (depth
    11). Orphan pages (old versions of directory pages, outside the tree): B's with a DIFFERENT deleted notes.txt
    [0x762:0x5], a deleted dup.txt [0x762:0x6] and only_here.txt [0x762:0x8]; C's with another deleted dup.txt
    [0x763:0x9]; d11's with deep.txt itself and A's with shallow.txt itself (same creation time, same FileRef)."""
    if "run" not in _N146:
        v = DirVol()
        dirs = {0x600: {"name": ""},
                0x761: {"parent": 0x600, "name": "A", "files": [
                    _row(_name_key("notes.txt"), _file_value(2, 0x761, _T + 2 * _S)),
                    _row(_name_key("shallow.txt"), _file_value(3, 0x761, _T + 7 * _S))]},
                0x762: {"parent": 0x600, "name": "B"}, 0x763: {"parent": 0x600, "name": "C"}}
        chain = _chain(dirs, 0x770, 11)
        dirs[chain[-1]]["files"] = [_row(_name_key("deep.txt"), _file_value(7, chain[-1], _T + 3 * _S))]
        v.objects = v.tree(dirs)
        pb = v.orphan(0x762, [_row(_name_key("dup.txt"), _file_value(6, 0x762, _T + 6 * _S)),
                              _row(_name_key("notes.txt"), _file_value(5, 0x762, _T + 5 * _S)),
                              _row(_name_key("only_here.txt"), _file_value(8, 0x762, _T + 8 * _S))])
        pc = v.orphan(0x763, [_row(_name_key("dup.txt"), _file_value(9, 0x763, _T + 9 * _S))])
        pd = v.orphan(chain[-1], [_row(_name_key("deep.txt"), _file_value(7, chain[-1], _T + 3 * _S))])
        pa = v.orphan(0x761, [_row(_name_key("shallow.txt"), _file_value(3, 0x761, _T + 7 * _S))])
        path = v.write(str(tmp_path_factory.mktemp("n146") / "target.raw"))
        rc, out, err = _syn(path, "files", "-q")
        _fx(rc == 0 and "d01/d02/d03/d04/d05/d06/d07/d08/d09/d10/d11/deep.txt" in out and "A/notes.txt" in out
            and "A/shallow.txt" in out and "dup.txt" not in out and "only_here.txt" not in out,
            "the live tree is not as built" + _ctx(rc, out, err))
        # group 2: the blocks are under -v
        _N146["run"] = _syn(path, "deleted", "--scan-pages", "-v") + ({"A": pa, "B": pb, "C": pc, "d11": pd},)
    return _N146["run"]


@pytest.fixture(scope="module")
def n146(tmp_path_factory):
    return _n146_scan(tmp_path_factory)


def _clusters(text):
    return {int(x) for x in re.findall(r"cluster (\d+)", text)} | {int(x, 16) for x in re.findall(r"cluster (0x[0-9a-f]+)", text)}


# N146's --scan-pages half: green in C3 (the identity rule of `--full`, N211 / decision 22)
def test_n146_scan_pages_deleted_file_sharing_a_live_name_is_not_an_old_version(n146):
    rc, out, err, pages = n146
    ms = [m for m in _mentions(_section(out, SCAN), "notes.txt")]
    _keep(ms, "the orphan-page remnant notes.txt is not listed at all" + _ctx(rc, out, err))
    prior = [_mention_ctx(m) for m in ms if _PRIOR_H.search(m[0])]
    assert not prior, "a deletion listed as an old version of the live A/notes.txt:\n  " + "\n  ".join(prior)
    assert any(_is_deleted_list(m[0]) for m in ms), "notes.txt (0x762:0x5) is not listed as deleted"


# N146's --scan-pages half: green in C3 (the identity rule of `--full`, N211 / decision 22)
def test_n146_scan_pages_old_version_of_a_file_below_depth_10_is_not_deleted(n146):
    rc, out, err, pages = n146
    ms = _mentions(_section(out, SCAN), "deep.txt")
    _keep(ms, "the orphan-page remnant deep.txt is not listed at all" + _ctx(rc, out, err))
    dele = [_mention_ctx(m) for m in ms if _is_deleted_list(m[0])]
    assert not dele, "an old version of a live file listed as DELETED:\n  " + "\n  ".join(dele)


# N146's --scan-pages half: green in C3 (the identity rule of `--full`, N211 / decision 22)
def test_n146_scan_pages_two_deleted_files_sharing_a_name_are_both_listed(n146):
    rc, out, err, pages = n146
    ms = _mentions(_section(out, SCAN), "dup.txt")
    _keep(ms, "no dup.txt listed" + _ctx(rc, out, err))
    seen = set()
    for m in ms:
        seen |= _clusters(m[2])
    assert {pages["B"], pages["C"]} <= seen, "dup.txt listed %d time(s), clusters %s; want both %d and %d" % (
        len(ms), sorted(seen), pages["B"], pages["C"])


def test_n146_control_scan_pages_file_live_nowhere_is_deleted(n146):
    """Control: only_here.txt (no live file of that name or identity anywhere) is DELETED, 1.13.1 and after."""
    rc, out, err, pages = n146
    ms = _mentions(_section(out, SCAN), "only_here.txt")
    _keep(ms and all(_is_deleted_list(m[0]) for m in ms), "only_here.txt is not DELETED" + _ctx(rc, out, err))
    _keep(rc == 0, "the healthy synthetic volume does not exit 0 (rc=%s)" % rc)


def test_n146_control_scan_pages_old_version_at_depth_1_is_an_old_version(n146):
    """Control for the depth RED: the same kind of remnant one level down (A/shallow.txt's own old page) is listed
    as an old version of an existing file by 1.13.1 -- the only difference from deep.txt is the depth."""
    rc, out, err, pages = n146
    ms = _mentions(_section(out, SCAN), "shallow.txt")
    _keep(ms and all(_PRIOR_H.search(m[0]) for m in ms), "shallow.txt is not an old version" + _ctx(rc, out, err))


def _diff_volume(path, case, digests=False):
    """Two checkpoints over one tree; the newer one lacks a file the older one has.
    deep:    d01/../d11/lost.txt removed (depth 11);          shallow: d01/lost.txt removed (depth 1)
    elsewhere: A/report.txt removed while B/report.txt stays; same: nothing changed (one Object Table)."""
    v = DirVol()
    v.digests = digests
    dirs = {0x600: {"name": ""}}
    if case in ("deep", "shallow", "same"):
        chain = _chain(dirs, 0x770, 11)
        where = chain[-1] if case != "shallow" else chain[0]
        dirs[where]["files"] = [_row(_name_key("lost.txt"), _file_value(7, where, _T + 3 * _S)),
                                _row(_name_key("stay.txt"), _file_value(8, where, _T + 4 * _S))]
        v.old_objects = v.tree(dirs)
        v.objects = dict(v.old_objects)
        if case != "same":
            lcn = v.alloc()
            v.objects[where] = (lcn, _page(lcn, where, [_row(_name_key("stay.txt"),
                                                             _file_value(8, where, _T + 4 * _S))]))
        else:
            v.old_objects = None
    else:
        dirs[0x761] = {"parent": 0x600, "name": "A", "files": [_row(_name_key("report.txt"),
                                                                    _file_value(2, 0x761, _T + 2 * _S))]}
        dirs[0x762] = {"parent": 0x600, "name": "B", "files": [_row(_name_key("report.txt"),
                                                                    _file_value(3, 0x762, _T + 3 * _S))]}
        v.old_objects = v.tree(dirs)
        v.objects = dict(v.old_objects)
        lcn = v.alloc()
        v.objects[0x761] = (lcn, _page(lcn, 0x761))
    return v.write(path)


# N146: green in wave D step D1 (RED until then: the checkpoint differential compares bare names to depth 10: d01/../d11/lost.txt, removed by the newer checkpoint, gives 'Same top-level files in b...)
def test_n146_checkpoint_diff_reports_a_removal_below_depth_10(tmp_path):
    rc, out, err = _syn(_diff_volume(str(tmp_path / "target.raw"), "deep"), "deleted")
    _keep(rc == 0, "exit %s" % rc + _ctx(rc, out, err))
    sec = _section(out, CHKP)
    assert _name_rx("lost.txt").search(sec), "the removal is not reported:\n" + sec
    assert "Same top-level files" not in sec, sec


# N146: green in wave D step D1 (RED until then: the checkpoint differential compares bare-name sets: A/report.txt, removed while B/report.txt stays, gives 'Same top-level files in both')
def test_n146_checkpoint_diff_reports_a_removal_whose_name_survives_elsewhere(tmp_path):
    rc, out, err = _syn(_diff_volume(str(tmp_path / "target.raw"), "elsewhere"), "deleted")
    _keep(rc == 0, "exit %s" % rc + _ctx(rc, out, err))
    sec = _section(out, CHKP)
    assert _name_rx("report.txt").search(sec), "the removal of A/report.txt is not reported:\n" + sec
    assert "Same top-level files" not in sec, sec


def test_n146_control_identical_checkpoints_report_no_change(tmp_path):
    """Control: both checkpoints over the same tree -- no file is reported removed or added (1.13.1 and after)."""
    rc, out, err = _syn(_diff_volume(str(tmp_path / "target.raw"), "same"), "deleted")
    sec = _section(out, CHKP)
    _keep(rc == 0 and not _name_rx("lost.txt").search(sec) and not _name_rx("stay.txt").search(sec),
          "a change reported between identical checkpoints" + _ctx(rc, out, err))


def test_n146_control_shallow_removal_is_reported(tmp_path):
    """Control: the same removal one level down (d01/lost.txt) IS reported by 1.13.1 -- the differential works on
    this fixture, so the depth-11 RED fails because of the depth limit."""
    rc, out, err = _syn(_diff_volume(str(tmp_path / "target.raw"), "shallow"), "deleted")
    sec = _section(out, CHKP)
    _keep(rc == 0 and _name_rx("lost.txt").search(sec), "the shallow removal is not reported" + _ctx(rc, out, err))


def test_n146_lead_old_checkpoint_digests_raise_no_false_alteration(tmp_path):
    """The volume of test_n146_checkpoint_diff_reports_a_removal_below_depth_10 with the root-page digests real
    volumes carry in their Object Table rows. Every page matches its own checkpoint's digest: `files` and
    `integrity --checksums` exit 0 on it (checked first)."""
    path = _diff_volume(str(tmp_path / "target.raw"), "deep", digests=True)
    for args in (("files", "-q"), ("integrity", "--checksums")):
        rc, out, err = _syn(path, *args)
        _fx(rc == 0 and "does not match" not in err, "%s does not pass on the healthy volume" % " ".join(args)
            + _ctx(rc, out, err))
    rc, out, err = _syn(path, "deleted")
    assert "does not match its recorded checksum" not in err and "ALTERED" not in err, \
        "a false alteration on a healthy volume:" + _ctx(rc, "", err)
    assert rc == 0, "exit %s on a healthy volume" % rc


def test_n146_control_digests_with_a_shallow_change_exit_0(tmp_path):
    """Control for the lead: digests on, the change at depth 1 (verified before the older table is built) --
    1.13.1 exits 0 with no alteration, so the lead's trigger is the depth, not the digests."""
    path = _diff_volume(str(tmp_path / "target.raw"), "shallow", digests=True)
    rc, out, err = _syn(path, "deleted")
    _keep(rc == 0 and "does not match" not in err, "the shallow-change control does not exit 0" + _ctx(rc, out, err))
