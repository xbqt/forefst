"""1.13.2 RED cases, group b2_carve: plan rows B5 and B6 (with N113, N130, N192, N193), and N127, N128.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 2 B (rows B5, B6), the fourth revision at the top (N127, N128
and N130 enter RC1; N130 inside B6), section 5 "RED first", decision 19 (the maintainer's bar: every RED fails on
1.13.1 BECAUSE of the defect, not because of an artefact, and is independently confirmed). N-rows:
`analysis/reports/v1.13.2/RUNNING_LOG.md` (N113 in the plan's B6 row; N127, N128, N130, N192, N193) and
`E2_RC2_CLASSIFICATION.md` (C13 = N127, C14 = N128, V-5 (b) = N130). Report, with the observed or expected failure of
every node: `analysis/reports/v1.13.2/red/RED_b2_carve.md`.

What each RED asserts (the row's Acceptance, or the running-log defect's correction)
------------------------------------------------------------------------------------
B5    CRC-bearing extent rows are carved with their real bytes (kept: a CONTROL records what 1.13.1 does), every
      carved cluster's CRC32-C is verified and each mismatch is reported, and the dead second scan loop and the
      no-op `integrity_checksum` filter are removed.
B6    One predicate: a remnant graded extent-backed ("metadata + carve", BEST-EFFORT) either produces a carve file or
      the output states why not. Every carve reports declared vs read clusters and warns when short. The three
      lab314_main rows (FVE2.{aff97bac...}.1/.2, recycle_me.bin) produce a file or state why not.
N113  (inside B6) a gap inside a recovered inline-holder extent map is reported, the zero-filled clusters counted
      and named, although carved_len equals the declared size.
N130  (inside B6) a misframed row in an inline-holder cover (VLCN 0x2800180050 = a flags word + 0x28) is not blamed
      on the Container Table and is not offered as extent-backed carve input.
N192  (inside B6) a carve over the 256 MiB cap produces no file AND says so.
N193  (inside B6) a carve write that fails partway leaves no truncated file under the carved (evidence) name.
N127  `extract` does not count runs it never reads (flags 0x10 clear, N63) as bytes "written from ranges the image
      stores as holes": no note, no holes sidecar, no refusal under --refuse-holes, no exit 2 for them. A written run
      read from an image hole is still reported (control).
N128  `snapshots --extract` applies N63: a never-written run of a version is zero-filled and never read, so neither
      foreign bytes nor an image-hole note come from it. Class sites found by the rg (live inline-holder reassembly,
      CoW current content, snapshot shared blocks) are REDs of their own, marked as class sites.

Volumes
-------
* ``[synthetic]`` -- a 64-cluster (256 KiB) sparse image in ``tmp_path``, data planted in chosen clusters, and one
  real forefst command (`export deleted --carve`, `deleted`, `extract`, `snapshots --extract`) run in a SUBPROCESS
  by `_DRIVER`. The driver replaces what lies UPSTREAM of the code under test and nothing else: `bootstrap` (a
  Translator whose container 2 maps VLCN 0x1000+n to PLCN n), and the producer of the rows (`_slack_recover`,
  `_analyze_dir_extents`/`resolve_path`, `_find_snapshot_files`). The verdict, the carve, the manifest, the hole
  checks, the writers and the exit-code escalation are the tool's own, and the driver ends exactly as `main()`
  does (fd:16858-16862, `_escalate_rc`). Remnant bytes are built here, in the layouts the tool documents and the
  corpus shows (lab314_main's integrity rows 0x1c00d0/0x2400d0, its hole-only FVE2 holders, winsiderv2's
  misframed row); each case pins its own routing before any assertion.
* ``[image...]`` -- a corpus image opened READ-ONLY, the tool writing only into a directory under
  ``$FOREFST_RED_SCRATCH`` (default: ``forefst_red_scratch`` in the system temp directory) that is deleted by exact path when the
  node or the module ends. Skipped when the image is absent. ``pytest -k "not image"`` runs the rest.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; the fix commit removes the mark and an XPASS fails the
  run. Only a plain ``assert`` states the acceptance.
* Everything else raises ``RedFixtureError`` or ``KeptPropertyBroken`` (NOT AssertionErrors): a fixture that is not
  what the case needs, a remnant routed to another carve path than the one named, a crash, a timeout, a host
  "cannot read image" error, or a property 1.13.1 already has and the fix must keep (the bytes of the written runs,
  the Windows SHA-256 of a LAB-E file, a row still indexed).
* Expected values come from bytes this module plants or reads itself (an independent table CRC32-C, the planted
  cluster contents, the Windows hashes of LAB-E recorded in `_runlogs/e2_verify_2026-09-26.txt` [V4], the golden
  output hashes of the extract rows), never from the tool under test.
* The output matchers are lenient about wording and strict about substance; `test_b2_matchers_*` shows that each
  one rejects 1.13.1's output and accepts a plausible fixed output (an instrument must be able to emit its
  counterexample).
"""
import contextlib
import hashlib
import inspect
import json
import os
import pickle
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21: internal names)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (RedFixtureError, SCRATCH, the CRC32-C)

FOREFST = AB.FOREFST
SCRATCH = AB.SCRATCH
RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
_crc32c = AB._crc32c                                     # independent table CRC32-C (Castagnoli)
IMAGE_TIMEOUT = 1800                                     # winsiderv2 `deleted` took 173 s in E2
SYN_TIMEOUT = 300


def _red(item, why):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason="RED 1.13.2 %s: %s" % (item, why))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Synthetic remnants: the byte layouts, built here
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

CS = 4096
NCL = 64                                  # synthetic image: 64 clusters = 256 KiB, sparse
FT = 133700000000000000                   # a FILETIME in 2024, inside the slack scanner's "sane" window
CT_MAP, CPC = {2: 0}, 0x400               # container 2 -> PLCN 0: VLCN 0x1000 + n translates to PLCN n


def V(plcn):
    """The VLCN that the synthetic Container Table translates to `plcn` (a containerised address, so a reader
    that skipped translation would read the wrong cluster)."""
    return 0x1000 + plcn


W, NW, HOLE, CRCF = 0x0050, 0x0040, 0x0060, 0x00D0     # written / never written (0x10 clear) / sparse hole / CRC


def ext_row(vlcn, fvcn, run, flags=W, crcs=None):
    """One extent row as the driver writes it: VLCN@0, flags@8 (low half) with row_size@0x0A, FVCN@0x0C, run@0x14,
    then one CRC-32C per cluster when `crcs` (row_size 24 + 4*run), padded to 8 (lab314_main: 0x1c00d0 run 1,
    0x2400d0 run 3)."""
    rs = 24 + (4 * run if crcs is not None else 0)
    b = bytearray(struct.pack("<QIIII", vlcn, (flags & 0xFFFF) | (rs << 16), fvcn, 0, run))
    for c in (crcs or []):
        b += struct.pack("<I", c)
    while len(b) % 8:
        b += b"\0"
    return bytes(b)


def holder_value(stream_size, disk_alloc, rows):
    """A 0x10028 $DATA holder: ihdr@0, descriptor 0x10028@4, stream size@0x38, disk alloc@0x48, row count at
    ihdr+0x14, rows from ihdr+0x28 (ihdr 0x88, as on lab314_main)."""
    ihdr = 0x88
    v = bytearray(ihdr + 0x28)
    struct.pack_into("<I", v, 0, ihdr)
    struct.pack_into("<I", v, 4, F.SNAP_DATA_DESC)
    struct.pack_into("<Q", v, 0x38, stream_size)
    struct.pack_into("<Q", v, 0x48, disk_alloc)
    struct.pack_into("<I", v, ihdr + 0x14, len(rows))
    return bytes(v) + b"".join(rows)


def key80(sub_id):
    """The key of a $DATA (0x80) multi-instance row for stream `sub_id` (0x1000 = the current stream)."""
    k = bytearray(0x18)
    k[8:12] = b"\x02\x00\x00\x80"
    k[12] = 0x80
    struct.pack_into("<Q", k, 0x10, sub_id)
    return bytes(k)


def keyb0(name):
    k = bytearray(0x10)
    k[8:12] = b"\x02\x00\x00\x80"
    k[12] = 0xB0
    return bytes(k) + name.encode("utf-16-le")


def snap_value(sub_id, stream_size):
    """A 0xB0 stream-snapshot row value: StreamSummary flags@0x10 == 2 (a snapshot, not an ADS), size@0x20,
    data sub_id@0x44, creation time@0x4C."""
    v = bytearray(0x58)
    struct.pack_into("<H", v, 0x10, 2)
    struct.pack_into("<Q", v, 0x20, stream_size)
    struct.pack_into("<I", v, 0x44, sub_id)
    struct.pack_into("<Q", v, 0x4C, FT)
    return bytes(v)


def long_row(rows, size=0, alloc=0):
    """A long (> 84 B, resident-form) type-0x30 value: the $SI head (node offset@0, times@0x28, attrs@0x48,
    size@0x58, alloc@0x60), then an embedded node whose rows are `rows` [(key, value)], its u16+0xFFFF offset
    array at the end of the value (base 0xA8, as on lab314_main)."""
    base = 0xA8
    head = bytearray(base)
    struct.pack_into("<I", head, 0, base)
    struct.pack_into("<QQQQ", head, 0x28, FT, FT, FT, FT)
    struct.pack_into("<I", head, 0x48, 0x20)
    struct.pack_into("<QQ", head, 0x58, size, alloc)
    node = bytearray(0x28)
    recs, offs, pos = b"", [], 0x28
    for k, v in rows:
        ko, kl = 0x10, len(k)
        vo = (ko + kl + 7) & ~7
        vl = len(v)
        rl = (vo + vl + 7) & ~7
        r = bytearray(rl)
        struct.pack_into("<I6H", r, 0, rl, ko, kl, 0, vo, vl, 0)
        r[ko:ko + kl] = k
        r[vo:vo + vl] = v
        offs.append(pos)
        recs += bytes(r)
        pos += rl
    struct.pack_into("<I", node, 0x10, pos)
    struct.pack_into("<I", node, 0x14, len(rows))
    struct.pack_into("<I", node, 0x20, pos + 4 * len(rows))
    return bytes(head) + bytes(node) + recs + b"".join(struct.pack("<HH", o, 0xFFFF) for o in offs)


def multilevel_row(rows, alloc_cl, size, index=None):
    """The v3.4/upgraded form (no outer node: value+0 = 0): a 0x10028 holder at +0x80 whose extent node (at
    holder + 0x20) names its rows by 0xFFFF-tagged u16 offsets -- the index array `_parse_inline_holder_extents`
    walks. `index` overrides the node-relative offsets the array names (N130 points one of them 8 bytes into a
    row). Returns (value, node offset, [node-relative row offsets])."""
    vd = bytearray(0x200)
    struct.pack_into("<QQQQ", vd, 0x28, FT, FT, FT, FT)
    struct.pack_into("<I", vd, 0x48, 0x20)
    struct.pack_into("<QQ", vd, 0x58, size, alloc_cl * CS)
    holder = 0x80
    struct.pack_into("<I", vd, holder, 0x20)
    struct.pack_into("<I", vd, holder + 4, F.SNAP_DATA_DESC)
    node = holder + 0x20
    pos, offs = node + 0x28, []
    for rb in rows:
        vd[pos:pos + len(rb)] = rb
        offs.append(pos - node)
        pos += len(rb)
    marks = node + 0x100
    _fx(pos <= marks, "multilevel_row: rows overrun the index array")
    for i, o in enumerate(offs if index is None else index):
        struct.pack_into("<HH", vd, marks + 4 * i, o, 0xFFFF)
    return bytes(vd), node, offs


def short_row(size, file_id=0x2A, home=0x701):
    """A short (84 B) non-resident type-0x30 value: file_id@0, home@8, times@0x10, size@0x38, attrs@0x40."""
    v = bytearray(0x54)
    struct.pack_into("<QQ", v, 0, file_id, home)
    struct.pack_into("<QQQQ", v, 0x10, FT, FT, FT, FT)
    struct.pack_into("<Q", v, 0x38, size)
    struct.pack_into("<I", v, 0x40, 0x20)
    return bytes(v)


def t40_backing(size, alloc, rows):
    """A type-0x40 backing value: size@0x58, alloc@0x60, one sub-record from 0xA8 holding an extent-table
    descriptor (start, end, capacity, count) and the rows."""
    body = bytearray(0xA8)
    struct.pack_into("<QQQQ", body, 0x28, FT, FT, FT, FT)
    struct.pack_into("<I", body, 0x48, 0x20)
    struct.pack_into("<QQ", body, 0x58, size, alloc)
    ent = b"".join(rows)
    hdr = bytearray(0x20)
    struct.pack_into("<I", hdr, 0, 0x20)
    struct.pack_into("<I", hdr, 4, 0x20 + len(ent))
    struct.pack_into("<I", hdr, 12, 0x100)
    struct.pack_into("<I", hdr, 20, len(rows))
    rec = hdr + ent
    return bytes(body) + struct.pack("<I", 4 + len(rec)) + bytes(rec) + b"\0" * 8


def entry(name, vd, **kw):
    """One recovered slack row, shaped like `_scan_page_slack` + `_slack_recover` produce it."""
    e = {"name": name, "create_time": FT, "modify_time": FT, "is_dir": False, "owning_path": "/dir",
         "owning_table_oid": 0x701, "vd": vd, "confidence": "high", "tag": "live-slack", "plcn": 5,
         "page_off": 0x100, "is_prior_version": False, "resident": len(vd) > 84, "file_attrs": 0x20,
         "all_owning_paths": ["/dir"]}
    e.update(kw)
    return e


def _tr():
    return F.Translator(dict(CT_MAP), CPC)


def _route(e):
    """Which of `_carve_extent_backed`'s three sources a remnant takes, from the routing facts alone (checked
    BEFORE any assertion, so a remnant that silently took another path is a fixture error)."""
    vd = e["vd"]
    if e.get("t40_backing") is not None and not e.get("resident"):
        return "t40_backing"
    if F._current_stream_extent_backed(vd, salvage=True):
        return "inline_holder"
    if not F.parse_resident_btree_rows(vd, None, salvage=True):
        return "holder_index"
    return "?"


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The synthetic harness: one real forefst command in a subprocess, only its upstream replaced
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_DRIVER = r'''
import copy, os, pickle, signal, sys
spec = pickle.load(open(sys.argv[1], "rb"))
sys.path.insert(0, spec["repo"])
sys.argv = [os.path.join(spec["repo"], "forefst.py"), spec["image"]]
import forefst as F

def _bootstrap(image, partition_start=None):
    # Upstream of the code under test: the volume geometry and its Container Table. Registered in _ALL_TRS
    # exactly as the real bootstrap does (fd:7153), so the at-exit translator caveat fires as it would.
    f = open(image, "rb")
    tr = F.Translator(dict(spec["ct_map"]), spec["cpc"])
    tr._image = os.path.basename(image)
    F._ALL_TRS.append(tr)
    return f, 0, spec["cs"], tr, [], {0x600: []}, 3, 14, []

F.bootstrap = _bootstrap
# The volume length is upstream too (C2 ST-L2, the lead, 2026-10-23): since wave C step C2 (B3, Q16) the tool takes it
# from the boot sector (total sectors x bytes per sector), and this synthetic image holds none. The volume here is the
# image, its every cluster, as the tool measured it before step C2.
_ncl = os.path.getsize(spec["image"]) // spec["cs"]
F.volume_clusters = F._volume_ncl = lambda f, ps, cs: _ncl
mode = spec["mode"]
if mode == "deleted":
    F._scan_trash_table = lambda *a, **k: []
    F._build_live_identity = lambda *a, **k: {}
    F._slack_recover = lambda *a, **k: copy.deepcopy(spec["entries"])
    fn = lambda: F.cmd_deleted(spec["image"], list(spec["args"]), 0)
elif mode == "extract":
    tgt = spec["target"]
    kd = b"\x30\x00\x00\x00" + tgt["name"].encode("utf-16-le")
    F.resolve_path = lambda *a, **k: (0x600, kd, b"")
    F._analyze_dir_extents = lambda *a, **k: [copy.deepcopy(tgt)]
    fn = lambda: F.cmd_extract(spec["image"], list(spec["args"]), 0)
elif mode == "snapshots":
    res = spec["snap_result"]
    F._find_snapshot_files = (lambda f, ps, cs, tr, om, oid, path, d, md, results:
                              results.append(copy.deepcopy(res)))
    fn = lambda: F.cmd_snapshots(spec["image"], list(spec["args"]), 0)
else:
    raise SystemExit("unknown mode %r" % (mode,))
if spec.get("fsize_limit"):
    import resource
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (spec["fsize_limit"], spec["fsize_limit"]))
try:
    try:
        rc = fn()
    except ValueError as e:                       # as main() treats a forensic handler (fd:16858-16862)
        print("%s: error: %s" % (F.PROG, e), file=sys.stderr); rc = 1
    except OSError as e:
        print("%s: error: cannot read image: %s" % (F.PROG, e), file=sys.stderr); rc = 1
    rc = 0 if rc is None else rc
except SystemExit as se:
    c = se.code
    rc = 0 if c is None else (c if isinstance(c, int) else 1)
sys.stdout.flush()
sys.exit(F._escalate_rc(rc))                      # as the tool's own __main__ tail (fd:17399-17410)
'''


class Result(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # what a reader sees: both streams (a reason or a warning may be printed on either)
        out = self.out if isinstance(self.out, str) else ""
        self.text = self.err + "\n" + out

    def ctx(self):
        return "\nrc=%s\n--- stdout (tail) ---\n%s\n--- stderr ---\n%s" % (self.rc, self.out[-3000:], self.err[-4000:])


class Syn(object):
    """A sparse 64-cluster image in `tmp_path`, clusters planted on demand, and the driver."""

    def __init__(self, tmp_path):
        self.dir = str(tmp_path)
        self.path = os.path.join(self.dir, "target.raw")
        with open(self.path, "wb") as fh:
            fh.truncate(NCL * CS)
        self._n = 0

    def put(self, plcn, data):
        _fx(0 <= plcn < NCL and len(data) <= CS, "put: cluster %d outside the synthetic image" % plcn)
        with open(self.path, "r+b") as fh:
            fh.seek(plcn * CS)
            fh.write(data)
        with open(self.path, "rb") as fh:
            fh.seek(plcn * CS)
            _fx(fh.read(len(data)) == data, "put: cluster %d did not land" % plcn)

    def is_hole(self, plcn):
        fd = os.open(self.path, os.O_RDONLY)
        try:
            n = F._hole_bytes_in(fd, plcn * CS, (plcn + 1) * CS)
        finally:
            os.close(fd)
        _fx(n is not None, "this host cannot answer SEEK_DATA/SEEK_HOLE for the scratch image")
        return n == CS

    def run(self, mode, args, fsize=None, **spec):
        self._n += 1
        drv = os.path.join(self.dir, "driver.py")
        with open(drv, "w") as fh:
            fh.write(_DRIVER)
        sp = os.path.join(self.dir, "spec%d.pkl" % self._n)
        spec = dict(spec, repo=REPO, cs=CS, ct_map=CT_MAP, cpc=CPC, image=self.path, mode=mode, args=list(args),
                    fsize_limit=fsize)
        with open(sp, "wb") as fh:
            pickle.dump(spec, fh)
        try:
            r = subprocess.run([sys.executable, "-B", drv, sp], capture_output=True, text=True,
                               timeout=SYN_TIMEOUT, cwd=self.dir)
        except subprocess.TimeoutExpired:
            raise RedFixtureError("timeout: synthetic %s" % mode)
        if "Traceback (most recent call last)" in r.stderr:
            raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
        if "error: cannot read image" in r.stderr:
            raise RedFixtureError("the host refused a read of the scratch image (a host artefact, not the defect):\n"
                                  + r.stderr[-2000:])
        return r.returncode, r.stdout, r.stderr

    def export_deleted(self, entries, extra=(), fsize=None):
        out = os.path.join(self.dir, "out%d" % (self._n + 1))
        rc, so, se = self.run("deleted", ["--extract", out, "--_from-export", "--carve"] + list(extra),
                              fsize=fsize, entries=entries)
        man = None
        mp = os.path.join(out, "recovery_manifest.json")
        if os.path.exists(mp):
            with open(mp) as fh:
                man = jdoc(json.load(fh), F._DELETED_MANIFEST_KEYS)                              # K21: internal names
        files = {}
        cd = os.path.join(out, "content")
        if os.path.isdir(cd):
            for n in os.listdir(cd):
                with open(os.path.join(cd, n), "rb") as fh:
                    files[n] = fh.read()
        recs = {}
        for r in (man or {}).get("records", []):
            recs.setdefault(r["name"], []).append(r)
        return Result(rc=rc, out=so + _side_text(out), err=se, manifest=man, records=recs, files=files, dir=out)

    def deleted_view(self, entries):
        jp = os.path.join(self.dir, "view%d.json" % (self._n + 1))
        rc, so, se = self.run("deleted", ["--json", jp], entries=entries)
        rows = []
        if os.path.exists(jp):
            with open(jp) as fh:
                rows = json.load(fh)
        return Result(rc=rc, out=so, err=se, rows=rows)

    def extract(self, target, extra=()):
        o = os.path.join(self.dir, "x%d.bin" % (self._n + 1))
        rc, so, se = self.run("extract", ["d/" + target["name"], "-o", o] + list(extra), target=target)
        data = None
        if os.path.exists(o):
            with open(o, "rb") as fh:
                data = fh.read()
        side = None
        if os.path.exists(o + ".holes.json"):
            with open(o + ".holes.json") as fh:
                side = json.load(fh)
        return Result(rc=rc, out=so, err=se, data=data, sidecar=side)

    def snapshots(self, snap_result):
        out = os.path.join(self.dir, "snap%d" % (self._n + 1))
        rc, so, se = self.run("snapshots", ["--extract", out], snap_result=snap_result)
        files = {}
        if os.path.isdir(out):
            for n in os.listdir(out):
                with open(os.path.join(out, n), "rb") as fh:
                    files[n] = fh.read()
        return Result(rc=rc, out=so, err=se, files=files, dir=out)


def _side_text(out_dir):
    """The recovery log and every sidecar JSON except the manifest and the index, as text lines: a reason or a
    CRC result written only there is still written (a line must name the file to count)."""
    parts = []
    if os.path.isdir(out_dir):
        for n in sorted(os.listdir(out_dir)):
            if n in ("recovery_manifest.json", "deleted_files.json", "deleted_files.csv"):
                continue
            p = os.path.join(out_dir, n)
            if os.path.isfile(p) and (n.endswith(".json") or n.endswith(".txt")) and os.path.getsize(p) < (8 << 20):
                with open(p, encoding="utf-8", errors="replace") as fh:
                    t = fh.read()
                if n.endswith(".json"):
                    try:
                        t = "\n".join(json.dumps(x) for x in (lambda j: j if isinstance(j, list) else
                                                             j.get("records", j.get("streams", [j])))(json.loads(t)))
                    except (ValueError, AttributeError) as e:
                        # N204: kept as raw text, and said so -- a line then names its file only if the raw
                        # JSON puts the name and the reason on one line, so a miss here is the reader's to see
                        print("side text: %s is not a records document (%s: %s); searched as raw text"
                              % (p, type(e).__name__, e))
                parts.append(t)
    return ("\n" + "\n".join(parts)) if parts else ""


def _text_of(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


@pytest.fixture
def syn(tmp_path, monkeypatch):
    # C2 ST-L2 (the lead, 2026-10-23): the in-process calls get the volume length the subprocess driver gets -- the
    # synthetic image holds no boot sector, so its volume is the image, all NCL clusters (B3 reads it from the boot sector).
    # raising=False (ST-L3, REVIEW_C2_tests N-2): tools from before C2 have no volume_clusters; the file stays runnable
    # against a pre-step snapshot.
    monkeypatch.setattr(F, "volume_clusters", lambda f, ps, cs: NCL, raising=False)
    monkeypatch.setattr(F, "_volume_ncl", lambda f, ps, cs: NCL, raising=False)
    return Syn(tmp_path)


@contextlib.contextmanager
def _registers_restored():
    """In-process calls append to forefst's module registers; restore them so no other test sees the residue."""
    names = ("_CONTENT_HOLES", "_CONTENT_UNDET", "_SKIP_FINDING", "_FINDINGS", "_DEFERRALS")
    saved = {n: list(getattr(F, n)) for n in names}
    notes = dict(F._SKIP_NOTES)
    try:
        yield
    finally:
        for n, v in saved.items():
            getattr(F, n)[:] = v
        F._SKIP_NOTES.clear()
        F._SKIP_NOTES.update(notes)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Output matchers (lenient about wording, strict about substance; see test_b2_matchers_*)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# The keys 1.13.1 writes into every recovery_manifest.json record (fd:14034-14064). A NEW key is how a fix is
# expected to add a reason or a count; the old ones mean what they say today and are not re-read as one.
_MANIFEST_KEYS_1131 = frozenset((
    "name", "source", "tag", "category", "plcn", "page_off", "is_resident", "confidence", "value_len",
    "recoverable", "verdict", "reliability", "row_file", "content_file", "decoded_len", "carved_len",
    "carved_declared_size", "unwritten_zero_filled_bytes", "unwritten_nonzero_on_disk_bytes",
    "refused_all_unwritten", "unwritten_runs", "hole_runs", "declared_size", "later_file", "confidence_reason"))
_LABELS_1131 = (F._RECOVER_LABEL["extent_backed"], F._T40_CARVE_LABEL)

_WHY_KEY = re.compile(r"(?i)(reason|why|refus|not_?carved|no_?carve|no_?file|skip|declin|withh|cap|limit|error|fail)")
_WHY_TEXT = re.compile(r"(?i)(no (carve|carved|file|content|bytes)|not (carved|written)|nothing (to carve|readable|"
                       r"was read|could be read)|withheld|refus|declin|skipp|too large|exceed|\bcap\b|limit|past the "
                       r"end|outside the (image|volume)|unreadable|could not be (read|written)|every run|sparse hole|"
                       r"no data|misframed|illegal row|not a valid extent)")
_CRC_WORD = re.compile(r"(?i)(crc|checksum|integrity)")
_MISMATCH_WORD = re.compile(r"(?i)(mismatch|fail|bad|does not match|do not match|differ)")
_ZERO_BAD = re.compile(r"(?i)\b(0|no|zero) (crc |checksum )?(mismatch\w*|fail\w*|bad\w*)")
_VERIFIED_WORD = re.compile(r"(?i)(verif|match|\bok\b|checked|pass)")
# 1.13.1's two hole phrasings: extract's NOTE ("were/would be written from ranges the image stores as holes") and
# content_holes' WARNING ("come from ranges the image stores as HOLES"). A fix's note that merely mentions holes
# (e.g. "none of these bytes were read from holes") does not match.
_HOLES_NOTE = re.compile(r"(?i)((were|would be) written from|come from) ranges the image stores as holes")
# 1.13.1's two ways of blaming the Container Table; a note that says it is NOT at fault does not match.
_NOT_CT = re.compile(r"(?i)\bnot (a |the )?(corrupt|container|fault)")
_CT_BLAME = re.compile(r"(?i)(container table has no mapping|(corrupt|truncated|damaged)\W*(/\W*truncated\W*)?"
                       r"container table)")


def _flatten(d, prefix=""):
    out = {}
    for k, v in (d or {}).items():
        kk = "%s%s" % (prefix, k)
        if isinstance(v, dict):
            out.update(_flatten(v, kk + "."))
        else:
            out[kk] = v
    return out


def _lines_naming(text, name):
    """Lines that name the file, with the name itself masked, so a word inside a file NAME ("short.bin",
    "gap.bin") can never satisfy a matcher."""
    return [l.replace(name, "<FILE>") for l in text.splitlines() if name in l]


def _states_why_not(rec, err, name):
    """True when the output says why an extent-backed remnant has no carve file: 1.13.1's own refusal flag, a new
    manifest field naming a reason, a verdict label changed to carry one, or a stderr line naming the file."""
    if rec.get("refused_all_unwritten"):
        return True
    for k, v in _flatten({k: v for k, v in rec.items() if k not in _MANIFEST_KEYS_1131}).items():
        if _WHY_KEY.search(k) and (v is True or (isinstance(v, str) and v.strip())
                                   or (isinstance(v, (list, dict)) and v)):
            return True
    lab = rec.get("verdict") or ""
    if lab and lab not in _LABELS_1131 and _WHY_TEXT.search(lab):
        return True
    return any(_WHY_TEXT.search(l) for l in _lines_naming(err, name))


def _cluster_report(rec):
    """(declared, read) from a manifest record, in one unit (clusters, or bytes), or None when the record does not
    carry both. 1.13.1 carries a declared size (bytes) and the length written, but never what was READ."""
    flat = {k.lower(): v for k, v in _flatten(rec).items()
            if isinstance(v, int) and not isinstance(v, bool)}
    for rk, rv in flat.items():
        if "read" not in rk:
            continue
        unit = "cluster" if "cluster" in rk else ("byte" if ("byte" in rk or "size" in rk) else None)
        if unit is None:
            continue
        for dk, dv in flat.items():
            if dk == rk:
                continue
            if unit == "cluster" and "cluster" in dk and re.search(r"declared|alloc|expected|total|needed", dk):
                return dv, rv
            if unit == "byte" and (dk in ("carved_declared_size", "declared_size")
                                   or ("byte" in dk and re.search(r"declared|alloc|expected|total", dk))):
                return dv, rv
    return None


def _warns_short(err, name):
    pat = re.compile(r"(?i)(short|fewer|missing|not read|could not be read|of \d+ (declared |allocated )?clusters?|"
                     r"incomplete|gap|uncovered|not covered)")
    return any(pat.search(l) for l in _lines_naming(err, name))


def _crc_statement(rec, err, name, want):
    """True when the output carries a per-file CRC statement of the kind `want`: "mismatch", or ("verified", n)
    with the count n. Per file: a NEW manifest field whose key names the CRC/integrity check, or an output line
    naming the carve. "0 mismatches" is neither a mismatch nor a failure of the verified statement."""
    kind, n = (want, None) if isinstance(want, str) else want
    for k, v in _flatten({k: v for k, v in rec.items() if k not in _MANIFEST_KEYS_1131}).items():
        if not _CRC_WORD.search(k):
            continue
        s = json.dumps(v)
        if kind == "mismatch":
            if (_MISMATCH_WORD.search(k) or _MISMATCH_WORD.search(s)) and (v is True or re.search(r"[1-9]", s)):
                return True
        elif not _MISMATCH_WORD.search(k) and (_VERIFIED_WORD.search(k) or _VERIFIED_WORD.search(s)) \
                and re.search(r"\b%d\b" % n, s):
            return True
    return any(_crc_line(l, kind, n) for l in _lines_naming(err, name))


def _crc_line(line, kind, n):
    # Critic fix (2026-09-27): mask path tokens first. lab314_main's CRC files live in `t19_integrity`, so a
    # recovery-log line naming big10k.bin carries the word "integrity" in its DIRECTORY; with a B6 read count
    # ("3 of 3 declared clusters read, size matches") that line satisfied this matcher with no CRC content.
    l2 = _ZERO_BAD.sub("", re.sub(r"(?<!\S)/\S*", "<PATH>", line))
    if not _CRC_WORD.search(l2):
        return False
    if kind == "mismatch":
        return bool(_MISMATCH_WORD.search(l2))
    return bool(_VERIFIED_WORD.search(l2.replace("mismatch", "")) and not _MISMATCH_WORD.search(l2)
                and re.search(r"\b%d\b" % n, l2))


def _crc_statement_anon(err, want):
    """For a run that carves ONE file: a stderr CRC line need not repeat the name (the tool's `_integrity_report`
    prints "integrity: 3/3 clusters CRC32-C-verified" without one)."""
    kind, n = (want, None) if isinstance(want, str) else want
    return any(_crc_line(l, kind, n) for l in err.splitlines())


def _gap_named(rec, err, name, fvcn, n):
    """True when a map gap of `n` clusters at file VCN `fvcn` is counted AND named: a new manifest field holding
    [fvcn, n] (or {file_vcn, clusters}), or a stderr line naming the file, a gap word and the VCN."""
    pair = re.compile(r"\[\s*%d\s*,\s*%d\s*\]" % (fvcn, n))
    for k, v in _flatten({k: v for k, v in rec.items() if k not in _MANIFEST_KEYS_1131}).items():
        s = json.dumps(v)
        if pair.search(s) or (re.search(r'"(file_)?vcn"\s*:\s*%d\b' % fvcn, s)
                              and re.search(r'"clusters"\s*:\s*%d\b' % n, s)):
            return True
    gapw = re.compile(r"(?i)(gap|missing|not covered|uncovered|unmapped|no extent|zero.filled|not in the map)")
    vcnw = re.compile(r"(?i)\b(fvcn|file_vcn|file vcn|vcn|cluster)[ =:#]*%d\b" % fvcn)
    return any(gapw.search(l) and vcnw.search(l) for l in _lines_naming(err, name))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Harness and matcher self-tests (controls: pass on 1.13.1 and after the fix)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_b2_independent_crc32c_agrees_with_the_tool():
    for data in (b"123456789", b"A" * CS, bytes(range(256)) * 16):
        assert _crc32c(data) == F._crc32c(data)
    assert _crc32c(b"123456789") == 0xE3069283


def _plain_rows(syn, n=3, base=10):
    blobs = []
    for i in range(n):
        b = bytes([0x41 + i]) * CS
        syn.put(base + i, b)
        blobs.append(b)
    return blobs


def _remnant(path, name, rows, size, alloc_cl, file_id=0x2A):
    """One remnant whose current stream is `rows`, routed to the named carve source."""
    if path == "inline_holder":
        vd = long_row([(key80(0x1000), holder_value(size, alloc_cl * CS, rows))], size=size, alloc=alloc_cl * CS)
        e = entry(name, vd)
    elif path == "t40_backing":
        e = entry(name, short_row(size, file_id=file_id), t40_backing=t40_backing(size, alloc_cl * CS, rows),
                  t40_extent_count=len(rows))
    elif path == "holder_index":
        e = entry(name, multilevel_row(rows, alloc_cl, size)[0])
    else:
        raise RedFixtureError("unknown path %r" % path)
    _fx(_route(e) == path, "%s: routed to %r, not %r" % (name, _route(e), path))
    return e


PATHS = ("inline_holder", "t40_backing", "holder_index")


@pytest.mark.parametrize("path", PATHS)
def test_b2_harness_control_plain_carve_is_byte_exact(syn, path):
    """Positive control: a plain written map on each source is carved byte-exact, rc 0 -- so a RED below that
    fails on the same harness fails on its defect, not on the harness."""
    blobs = _plain_rows(syn)
    e = _remnant(path, "plain.bin", [ext_row(V(10), 0, 3, W)], 3 * CS, 3)
    r = syn.export_deleted([e])
    rec = r.records.get("plain.bin", [{}])[0]
    _fx(rec.get("recoverable") == "extent_backed", "not graded extent-backed" + r.ctx())
    assert r.rc == 0, r.ctx()
    assert r.files.get("plain.bin.carved") == b"".join(blobs), r.ctx()


def test_b2_matchers_can_emit_their_counterexamples():
    """Each matcher rejects what 1.13.1 writes and accepts a plausible fixed output."""
    old = {k: None for k in _MANIFEST_KEYS_1131}
    old.update(name="x.bin", recoverable="extent_backed", verdict=_LABELS_1131[0], refused_all_unwritten=False,
               carved_len=12288, carved_declared_size=12288, declared_size=12288, hole_runs=[[0, 1]],
               unwritten_runs=[], confidence_reason=None)
    # states-why
    assert not _states_why_not(old, "", "x.bin")
    assert not _states_why_not(old, "[forefst] WARNING: extent cover (unmappable VLCN) skipped 1 of 1 addresses", "x.bin")
    assert _states_why_not(dict(old, no_carve_reason="allocation exceeds the 256 MiB carve cap"), "", "x.bin")
    assert _states_why_not(dict(old, refused_all_unwritten=True), "", "x.bin")
    assert _states_why_not(old, "[forefst] NOTE: no carve for 'x.bin': every run is a sparse hole", "x.bin")
    assert not _states_why_not(dict(old, declared_clusters=3, read_clusters=0), "", "x.bin")
    # declared vs read
    assert _cluster_report(old) is None
    assert _cluster_report(dict(old, declared_clusters=3, read_clusters=1)) == (3, 1)
    assert _cluster_report(dict(old, clusters={"allocated": 3, "read": 3})) == (3, 3)
    assert _cluster_report(dict(old, read_bytes=4096)) == (12288, 4096)
    # short warning
    assert not _warns_short("", "x.bin")
    assert not _warns_short("[forefst] WARNING: 8192 byte(s) of carved 'x.bin' come from ranges the image stores "
                            "as HOLES", "x.bin")
    assert _warns_short("[forefst] WARNING: carved 'x.bin' is SHORT: 3 of 5 declared clusters read", "x.bin")
    # CRC statements
    assert not _crc_statement(old, "", "x.bin", "mismatch")
    assert not _crc_statement(old, "", "x.bin", ("verified", 3))
    assert _crc_statement(dict(old, crc_mismatches=[[1, 11, 0x1, 0x2]]), "", "x.bin", "mismatch")
    assert _crc_statement(dict(old, integrity={"checked": 3, "ok": 3, "bad_count": 0}), "", "x.bin", ("verified", 3))
    assert _crc_statement(old, "[forefst] carved 'x.bin': 3/3 clusters CRC32-C-verified", "x.bin", ("verified", 3))
    assert _crc_statement(old, "[forefst] WARNING: carved 'x.bin': CRC32-C mismatch on 1 of 3", "x.bin", "mismatch")
    assert not _crc_statement(old, "[forefst] carved 'x.bin': CRC32-C: 1 of 3 clusters failed", "x.bin",
                              ("verified", 3))
    assert _crc_statement_anon("[forefst] integrity: 3/3 clusters CRC32-C-verified.", ("verified", 3))
    assert _crc_statement_anon("[forefst] integrity: 3/3 clusters CRC32-C-verified, 0 mismatches.", ("verified", 3))
    assert not _crc_statement_anon("[forefst] integrity: 3/3 clusters CRC32-C-verified, 0 mismatches.", "mismatch")
    assert _crc_statement(dict(old, integrity={"checked": 3, "ok": 2, "bad_count": 1}), "", "x.bin", "mismatch")
    assert not _crc_statement(dict(old, integrity={"checked": 3, "ok": 3, "bad_count": 0}), "", "x.bin", "mismatch")
    assert not _crc_statement(dict(old, crc_mismatches=3), "", "x.bin", ("verified", 3))
    assert not _crc_statement_anon("", "mismatch")
    # a CRC word in the file's DIRECTORY is not a CRC statement (lab314_main: t19_integrity/big10k.bin)
    assert not _crc_statement(old, "  x.bin  | remnant in /LAB_0906/t19_integrity | carved: 3 of 3 declared "
                                   "clusters read, size matches", "x.bin", ("verified", 3))
    assert not _crc_statement(old, "  x.bin  | deleted from /LAB_0906/t19_integrity | 1 cluster failed to read",
                              "x.bin", "mismatch")
    assert _crc_statement(old, "[forefst] /out/content/x.bin.carved: CRC32-C 3/3 clusters verified", "x.bin",
                          ("verified", 3))
    # gap
    assert not _gap_named(old, "", "x.bin", 1, 1)
    assert _gap_named(dict(old, gap_runs=[[1, 1]]), "", "x.bin", 1, 1)
    assert _gap_named(old, "[forefst] WARNING: carved 'x.bin': map gap at fvcn 1 (1 cluster) zero-filled", "x.bin", 1, 1)
    assert not _gap_named(dict(old, hole_runs=[[1, 1]]), "", "x.bin", 1, 1)       # a hole is not a gap
    # container-table blame and the hole note
    assert _CT_BLAME.search("ValueError: container table has no mapping")
    assert _CT_BLAME.search("output may be incomplete (corrupt/truncated container table).")
    assert _HOLES_NOTE.search("were written from ranges the image stores as holes, which read back")
    assert _HOLES_NOTE.search("come from ranges the image stores as HOLES and read back as zeros")
    assert not _HOLES_NOTE.search("4022272 bytes were zero-filled (never written); none was read from ranges the image "
                                  "stores as holes")
    assert _NOT_CT.search("extent row misframed (no legal row size) -- not a Container Table fault")
    assert not _NOT_CT.search("output may be incomplete (corrupt/truncated container table).")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B5 -- CRC-bearing rows are carved with no CRC check; a dead loop and a no-op filter
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Three clusters A B C are "written" with their CRC-32C stored in the row (row_size 36, flags 0x2400d0 -- the
# shape of lab314_main's big10k.bin). In the mismatch case the middle cluster's bytes on disk are then changed
# (the clusters were reused after the deletion -- the case O3 says the CRCs discriminate).

def _crc_case(syn, path, tamper, name):
    orig = [bytes([0x41 + i]) * CS for i in range(3)]
    crcs = [_crc32c(b) for b in orig]
    now = list(orig)
    if tamper:
        now[1] = b"X" * CS
    for i, b in enumerate(now):
        syn.put(10 + i, b)
    _fx((_crc32c(now[1]) != crcs[1]) == tamper, "the tamper did not change the middle cluster's CRC")
    e = _remnant(path, name, [ext_row(V(10), 0, 3, CRCF, crcs)], 3 * CS, 3)
    return e, now


@pytest.mark.parametrize("path", PATHS)
def test_b5_control_crc_rows_are_carved_with_their_real_bytes(syn, path):
    """Step 1 of B5, recorded as a kept property: on every source a CRC-bearing row is KEPT and its clusters are
    READ (not zero-filled), whatever their CRC. 1.13.1 does this; the fix must keep it."""
    e, now = _crc_case(syn, path, True, "crcfile.bin")
    r = syn.export_deleted([e])
    rec = r.records.get("crcfile.bin", [{}])[0]
    _fx(rec.get("recoverable") == "extent_backed", "not graded extent-backed" + r.ctx())
    _keep(r.files.get("crcfile.bin.carved") == b"".join(now),
          "the CRC-bearing clusters are no longer carved with their bytes" + r.ctx())


@pytest.mark.parametrize("path", PATHS)
# B5: green in wave D step D2 (RED until then: a carved cluster whose stored CRC32-C does not match is not reported (the carve runs no CRC check))
def test_b5_carve_reports_each_crc_mismatch(syn, path):
    e, now = _crc_case(syn, path, True, "crcfile.bin")
    r = syn.export_deleted([e])
    rec = r.records.get("crcfile.bin", [{}])[0]
    _keep(r.files.get("crcfile.bin.carved") == b"".join(now), "the CRC-bearing rows are no longer carved" + r.ctx())
    assert _crc_statement(rec, r.text, "crcfile.bin", "mismatch") or _crc_statement_anon(r.text, "mismatch"), (
        "1 of 3 carved clusters fails its stored CRC32-C and nothing says so" + r.ctx()
        + "\n--- record ---\n" + json.dumps(rec, indent=1))


@pytest.mark.parametrize("path", PATHS)
# B5: green in wave D step D2 (RED until then: a carve of CRC-bearing rows states no CRC32-C result at all (3 of 3 clusters verifiable))
def test_b5_carve_states_crc_verification_of_every_cluster(syn, path):
    e, now = _crc_case(syn, path, False, "crcfile.bin")
    r = syn.export_deleted([e])
    rec = r.records.get("crcfile.bin", [{}])[0]
    _keep(r.files.get("crcfile.bin.carved") == b"".join(now), "the CRC-bearing rows are no longer carved" + r.ctx())
    assert (_crc_statement(rec, r.text, "crcfile.bin", ("verified", 3))
            or _crc_statement_anon(r.text, ("verified", 3))), (
        "3 CRC-bearing clusters carved, 3 CRCs match, and the output says nothing about them" + r.ctx()
        + "\n--- record ---\n" + json.dumps(rec, indent=1))
    assert not (_crc_statement(rec, r.text, "crcfile.bin", "mismatch") or _crc_statement_anon(r.text, "mismatch")), (
        "a mismatch reported where every CRC matches" + r.ctx())


def _subrecord_value(rows, needed_cl):
    return t40_backing(needed_cl * CS, needed_cl * CS, rows)


def test_b5_control_no_accepted_extent_ever_carries_the_integrity_flag():
    """DF02, as evidence: the second scan loop in `_find_extents_in_subrecord` walks the same rows with the same
    step and the same inclusion test as the first, so it can never accept a set the first declined, and
    `integrity_checksum` (set only there) never reaches an accepted extent -- the carve's filter at fd:13716 is a
    no-op. Meaningful only while the filter exists; once B5 removes it the node skips (a fix may legitimately
    keep a CRC marker on the extents it now verifies)."""
    if not re.search(r"if not x\.get\([\"']integrity_checksum[\"']\)", inspect.getsource(F._carve_extent_backed)):
        pytest.skip("the integrity_checksum filter is gone (B5 fixed); nothing left to prove a no-op")
    tr = _tr()
    fixed = [
        [ext_row(V(10), 0, 1, CRCF, [1])],
        [ext_row(V(10), 0, 3, CRCF, [1, 2, 3])],
        [ext_row(V(10), 0, 1, CRCF, [1]), ext_row(V(20), 1, 2, W)],
        [ext_row(V(10), 0, 2, W), ext_row(V(20), 2, 3, CRCF, [1, 2, 3])],
    ]
    for rows in fixed:
        need = sum(struct.unpack_from("<I", r, 0x14)[0] for r in rows)
        info = F._parse_extents_from_type40(_subrecord_value(rows, need), CS, tr)
        _fx(info["extents"], "a CRC-bearing map did not decode: %r" % (rows,))
        assert not any(x.get("integrity_checksum") for x in info["extents"]), info["extents"]
    rnd = random.Random(1132)
    accepted = 0
    for _ in range(3000):
        rows, fv = [], 0
        for _j in range(rnd.randint(1, 4)):
            run = rnd.randint(1, 5)
            kind = rnd.choice((W, NW, CRCF, CRCF))
            rows.append(ext_row(V(rnd.randint(1, 50)), fv, run, kind,
                                [rnd.getrandbits(32) for _ in range(run)] if kind == CRCF else None))
            fv += run
        need = fv + rnd.choice((0, 0, 0, 1, -1))
        if need <= 0:
            continue
        info = F._parse_extents_from_type40(_subrecord_value(rows, need), CS, tr)
        if info["extents"]:
            accepted += 1
            assert not any(x.get("integrity_checksum") for x in info["extents"])
    _fx(accepted > 1000, "the fuzz accepted only %d maps; it proves nothing" % accepted)


# B5: green in wave D step D2 (RED until then: the dead second scan loop and the no-op integrity_checksum filter are still in the code)
def test_b5_dead_loop_and_noop_filter_are_removed():
    """The row's own words: 'The dead loop and the no-op filter are removed.' A dead loop has no behaviour to
    test, so this reads the source: one extent-row loop in `_find_extents_in_subrecord`, no filter on
    `integrity_checksum` in `_carve_extent_backed`."""
    src_find = inspect.getsource(F._find_extents_in_subrecord)
    src_carve = inspect.getsource(F._carve_extent_backed)
    loops = len(re.findall(r"for i in range\(count\)", src_find))
    assert loops <= 1, "_find_extents_in_subrecord still walks the extent rows %d times (fd:8888-8952)" % loops
    assert not re.search(r"if not x\.get\([\"']integrity_checksum[\"']\)", src_carve), (
        "_carve_extent_backed still filters on integrity_checksum (fd:13716), which no accepted extent carries")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B6 -- one carveable predicate; declared vs read clusters; short carves; N113, N130, N192, N193
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _nofile_case(syn, case):
    """Remnants graded extent-backed on 1.13.1 whose carve returns no file and no reason (observed; see report)."""
    _plain_rows(syn)
    if case == "hole_only_holder":
        # lab314_main's three rows, byte for byte in shape: row size 512, alloc 4096; the 0x1000 holder has
        # stream size 0, disk alloc 0 and ONE row: VLCN 0, flags 0x180060 (a sparse hole), fvcn 0, run 1.
        hv = holder_value(0, 0, [ext_row(0, 0, 1, HOLE)])
        e = entry("recycle_me.bin", long_row([(key80(0x1000), hv)], size=512, alloc=CS))
        _fx(_route(e) == "?" and not F._current_stream_extent_backed(e["vd"], salvage=True),
            "hole-only holder: expected neither source 1 nor a plain holder_index route")
        return e
    if case == "unmappable_holder":
        # the verdict's legacy decode (no translator) accepts the row; the carve's decode does not
        hv = holder_value(2 * CS, 2 * CS, [ext_row(0x5000000, 0, 2, W)])
        e = entry("unmap.bin", long_row([(key80(0x1000), hv)], size=2 * CS, alloc=2 * CS))
        _fx(not F._vlcn_mappable(_tr(), 0x5000000), "the VLCN is mappable")
        return e
    if case == "outside_the_file":
        # a holder_index cover whose every cluster lies past the end of the image: nothing readable
        return _remnant("holder_index", "outside.bin", [ext_row(V(200), 0, 2, W)], 2 * CS, 2)
    raise RedFixtureError(case)


@pytest.mark.parametrize("case", ("hole_only_holder", "unmappable_holder", "outside_the_file"))
# B6: green in wave D step D2 (RED until then: a remnant graded extent-backed (BEST-EFFORT, 'metadata + carve') gets no carve file and no reason)
def test_b6_every_extent_backed_row_produces_a_file_or_states_why(syn, case):
    e = _nofile_case(syn, case)
    r = syn.export_deleted([e])
    recs = r.records.get(e["name"])
    _fx(recs, "the remnant is not in the manifest" + r.ctx())
    rec = recs[0]
    if rec.get("recoverable") != "extent_backed":
        return                                   # one predicate: no longer promised a carve
    carved = rec.get("content_file")
    assert carved or _states_why_not(rec, r.text, e["name"]), (
        "graded %r (%s) but no carve file and no stated reason" % (rec.get("reliability"), rec.get("verdict"))
        + r.ctx() + "\n--- record ---\n" + json.dumps(rec, indent=1))


@pytest.mark.parametrize("path", ("t40_backing", "holder_index"))
# N192: green in wave D step D2 (RED until then: a carve over the 256 MiB cap returns no file and neither the manifest nor stderr says why)
def test_n192_carve_over_the_cap_states_why_there_is_no_file(syn, path):
    n = 256 * 1024 * 1024 // CS + 1                      # 65,537 clusters: one over the cap (fd:13675/:13722/:13749)
    e = _remnant(path, "huge.bin", [ext_row(V(10), 0, n, W)], n * CS, n)
    r = syn.export_deleted([e])
    rec = r.records.get("huge.bin", [{}])[0]
    _fx(rec, "the remnant is not in the manifest" + r.ctx())
    if rec.get("recoverable") != "extent_backed":
        return
    assert rec.get("content_file") or _states_why_not(rec, r.text, "huge.bin"), (
        "no carve file for a %d-cluster allocation and no reason given" % n + r.ctx()
        + "\n--- record ---\n" + json.dumps(rec, indent=1))


@pytest.mark.parametrize("path", PATHS)
# B6: green in wave D step D2 (RED until then: a carve does not report how many of its declared clusters were actually read)
def test_b6_carve_reports_declared_and_read_clusters(syn, path):
    _plain_rows(syn)
    e = _remnant(path, "full.bin", [ext_row(V(10), 0, 3, W)], 3 * CS, 3)
    r = syn.export_deleted([e])
    rec = r.records.get("full.bin", [{}])[0]
    _fx(rec.get("content_file"), "no carve file" + r.ctx())
    rep = _cluster_report(rec)
    assert rep is not None, "no declared-vs-read count in the manifest record:\n" + json.dumps(rec, indent=1)
    assert rep[0] == rep[1], "a complete carve reports declared %r vs read %r" % rep


@pytest.mark.parametrize("path", PATHS)
# B6: green in wave D step D2 (RED until then: a carve whose clusters lie past the end of the image reports no read count below the declared one)
def test_b6_carve_past_eof_reports_fewer_read_clusters(syn, path):
    syn.put(10, b"A" * CS)
    e = _remnant(path, "past.bin", [ext_row(V(10), 0, 1, W), ext_row(V(100), 1, 2, W)], 3 * CS, 3)
    _fx(100 > NCL, "the second run is inside the image")
    r = syn.export_deleted([e])
    rec = r.records.get("past.bin", [{}])[0]
    _fx(rec.get("recoverable") == "extent_backed", "not graded extent-backed" + r.ctx())
    rep = _cluster_report(rec)
    assert rep is not None, "no declared-vs-read count in the manifest record:\n" + json.dumps(rec, indent=1) + r.ctx()
    assert rep[1] < rep[0], "2 of 3 declared clusters could not be read, yet declared %r vs read %r" % rep


# B6/K023: green in wave D step D2 (RED until then: a carve whose inline-holder map covers 3 of 5 allocated clusters is not flagged as short)
def test_b6_short_inline_holder_carve_warns(syn):
    _plain_rows(syn)
    hv = holder_value(5 * CS, 5 * CS, [ext_row(V(10), 0, 3, W)])       # disk_alloc 5 clusters, rows cover 3
    e = entry("k023.bin", long_row([(key80(0x1000), hv)], size=5 * CS, alloc=5 * CS))
    _fx(_route(e) == "inline_holder", "not routed to source 1")
    r = syn.export_deleted([e])
    rec = r.records.get("k023.bin", [{}])[0]
    _fx(rec.get("recoverable") == "extent_backed", "not graded extent-backed" + r.ctx())
    if not rec.get("content_file"):
        assert _states_why_not(rec, r.text, "k023.bin"), "no file and no reason" + r.ctx()
        return
    assert _warns_short(r.text, "k023.bin"), (
        "carved %r of %r declared bytes from 3 of 5 allocated clusters, with no warning"
        % (rec.get("carved_len"), rec.get("carved_declared_size")) + r.ctx())


# N113: green in wave D step D2 (RED until then: a gap inside a recovered inline-holder extent map is zero-filled with carved_len == declared size and no note)
def test_n113_gap_in_inline_holder_map_is_counted_and_named(syn):
    syn.put(10, b"A" * CS)
    syn.put(11, b"B" * CS)                      # what a reader of the gap must NOT take: no row maps VCN 1 here
    syn.put(12, b"C" * CS)
    hv = holder_value(3 * CS, 3 * CS, [ext_row(V(10), 0, 1, W), ext_row(V(12), 2, 1, W)])
    e = entry("gap.bin", long_row([(key80(0x1000), hv)], size=3 * CS, alloc=3 * CS))
    _fx(_route(e) == "inline_holder", "not routed to source 1")
    r = syn.export_deleted([e])
    rec = r.records.get("gap.bin", [{}])[0]
    data = r.files.get("gap.bin.carved")
    _fx(rec.get("recoverable") == "extent_backed", "not graded extent-backed" + r.ctx())
    if data is not None:
        _keep(data[:CS] == b"A" * CS and data[2 * CS:3 * CS] == b"C" * CS, "the mapped clusters changed" + r.ctx())
        _keep(b"B" not in data[CS:2 * CS], "the gap was filled from an unmapped cluster" + r.ctx())
    else:
        assert _states_why_not(rec, r.text, "gap.bin"), "no file and no reason" + r.ctx()
        return
    assert _gap_named(rec, r.text, "gap.bin", 1, 1), (
        "a 1-cluster gap at file VCN 1 was zero-filled (carved_len %r == declared %r) and not reported"
        % (rec.get("carved_len"), rec.get("carved_declared_size")) + r.ctx()
        + "\n--- record ---\n" + json.dumps(rec, indent=1))


def _misframed(syn):
    """winsiderv2's N130 shape: a holder_index cover with row 1 (VLCN, fvcn 0, run 1) and an index entry that
    points 8 bytes INTO a real row 2 (fvcn 40, run 1, then u32 40), so the decoder reads VLCN = row 2's flags word
    0x00180050 + (0x28 << 32) = 0x2800180050, flags 0, fvcn 1, run 40: 1 + 40 = 41 = the allocation."""
    syn.put(10, b"A" * CS)
    r1 = ext_row(V(10), 0, 1, W)
    r2 = ext_row(V(11), 40, 1, W) + b"\0" * 4 + struct.pack("<I", 40)
    vd, node, offs = multilevel_row([r1, r2], 41, 41 * CS)
    vd, node, offs2 = multilevel_row([r1, r2], 41, 41 * CS, index=[offs[0], offs[1] + 8])
    o = node + offs[1] + 8                                     # pin the misframe with an independent read
    _fx(struct.unpack_from("<QIIII", vd, o) == (0x2800180050, 0, 1, 0, 40),
        "the misframed row does not read as (0x2800180050, flags 0, fvcn 1, run 40)")
    _fx(not F._vlcn_mappable(_tr(), 0x2800180050), "the misframed VLCN is mappable")
    e = entry("misframed.bin", vd)
    _fx(_route(e) == "holder_index", "not routed to the holder index")
    return e


# N130: green in wave D step D2 (RED until then: a misframed inline-holder row (VLCN 0x2800180050) is blamed on a corrupt Container Table)
def test_n130_misframed_cover_is_not_blamed_on_the_container_table(syn):
    e = _misframed(syn)
    r = syn.deleted_view([e])
    _fx(any(row.get("FileName") == "misframed.bin" for row in r.rows), "the remnant is not listed" + r.ctx())
    blamed = [l for l in r.text.splitlines() if _CT_BLAME.search(l) and not _NOT_CT.search(l)]
    assert not blamed, "the Container Table is blamed for a misframed extent row:\n" + "\n".join(blamed)


# N130: green in wave D step D2 (RED until then: a misframed inline-holder cover is still offered as extent-backed carve input (BEST-EFFORT))
def test_n130_misframed_cover_is_not_a_carve_candidate(syn):
    e = _misframed(syn)
    r = syn.deleted_view([e])
    rows = [row for row in r.rows if row.get("FileName") == "misframed.bin"]
    _fx(rows, "the remnant is not listed" + r.ctx())
    assert rows[0].get("Reliability") != "BEST-EFFORT", (
        "graded %r (%r): a cover that holds a misframed row is carve input" % (rows[0].get("Reliability"),
                                                                              rows[0].get("Recoverability")))


def _big_remnant(syn, n=32):
    blobs = []
    for i in range(n):
        b = bytes([0x41 + (i % 26)]) * CS
        syn.put(10 + i, b)
        blobs.append(b)
    hv = holder_value(n * CS, n * CS, [ext_row(V(10), 0, n, W)])
    e = entry("big.bin", long_row([(key80(0x1000), hv)], size=n * CS, alloc=n * CS))
    _fx(_route(e) == "inline_holder", "not routed to source 1")
    return e, b"".join(blobs)


def test_n193_control_a_carve_under_the_limit_is_whole(syn):
    e, want = _big_remnant(syn, 8)
    r = syn.export_deleted([e], fsize=64 * 1024)
    assert r.files.get("big.bin.carved") == want, r.ctx()


# N193: green in wave D step D2 (RED until then: a carve write that fails partway leaves a truncated file under the carved (evidence) name)
def test_n193_failed_carve_write_leaves_no_truncated_file_under_the_evidence_name(syn):
    e, want = _big_remnant(syn, 32)                  # 128 KiB carve, 64 KiB file-size limit (EFBIG, as V4 of E4_IMPLEMENTATION.md)
    r = syn.export_deleted([e], fsize=64 * 1024)
    fails = os.path.join(r.dir, "_extract_failures.json")
    _fx(os.path.exists(fails) and "big.bin.carved" in _text_of(fails),
        "the file-size limit did not fail the carve write (fixture did not reproduce the fault)" + r.ctx())
    got = r.files.get("big.bin.carved")
    assert got is None or got == want, (
        "content/big.bin.carved left at %d of %d bytes under the name a complete carve uses" % (len(got), len(want))
        + r.ctx())


# N193: green in wave D step D2 (RED until then: after a failed carve write the summary says 'the data did not survive')
def test_n193_summary_does_not_blame_the_data_for_a_failed_write(syn):
    e, _want = _big_remnant(syn, 32)
    r = syn.export_deleted([e], fsize=64 * 1024)
    fails = os.path.join(r.dir, "_extract_failures.json")
    _fx(os.path.exists(fails), "the file-size limit did not fail the carve write" + r.ctx())
    bad = [l for l in r.out.splitlines() if re.search(r"(?i)did not survive", l)]
    assert not bad, "the carve's data was read in full; the WRITE failed, yet:\n" + "\n".join(bad)


_GUARDED_UNIT = r'''
import json, resource, signal, sys
sys.path.insert(0, sys.argv[3])
import forefst as F
dest, lim = sys.argv[1], int(sys.argv[2])
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (lim, lim))
fails = []
ret = F._guarded_extract_write(dest, b"x" * (3 * lim), fails)
print(json.dumps({"ret": ret, "fails": fails}))
'''


# N193: green in wave D step D2 (RED until then: _guarded_extract_write leaves the partial file when the write fails (fd:13579-13585))
def test_n193_guarded_write_leaves_no_partial_file(tmp_path):
    dest = str(tmp_path / "content" / "f.carved")
    lim = 64 * 1024
    r = subprocess.run([sys.executable, "-B", "-c", _GUARDED_UNIT, dest, str(lim), REPO],
                       capture_output=True, text=True, timeout=120)
    _fx(r.returncode == 0 and r.stdout.strip(), "the unit driver failed: " + r.stderr[-2000:])
    res = json.loads(r.stdout.strip().splitlines()[-1])
    _fx(res["fails"], "the file-size limit did not fail the write (fixture did not reproduce the fault)")
    _keep(res["ret"] is None, "a failed write is reported as written")
    assert not os.path.exists(dest) or os.path.getsize(dest) == 3 * lim, (
        "%d of %d bytes left under the destination name after the write failed" % (os.path.getsize(dest), 3 * lim))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N127 -- extract counts never-written runs, which it never reads, as bytes from image holes
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# One written cluster W at file VCN 0 (read), then a two-cluster run at VCN 1-2 whose flags say "allocated,
# never written" (0x10 clear): extract zero-fills it WITHOUT reading it (fd:11449-11450). Its clusters are image
# holes (the labE/xbpt shape) or hold foreign bytes (the win11refs15t64k shape).

def _xt(plcn, fvcn, run, flags):
    return {"vlcn": V(plcn) if plcn else 0, "plcn": plcn, "file_vcn": fvcn, "clusters": run,
            "flags": (flags & 0xFFFF) | (24 << 16), "disk_offset": 0, "is_hole": bool(flags & 0x20)}


def _n127_target(syn, second, foreign=False):
    syn.put(10, b"W" * CS)
    if foreign:
        syn.put(20, b"F" * CS)
        syn.put(21, b"G" * CS)
    else:
        _fx(syn.is_hole(20) and syn.is_hole(21), "clusters 20-21 are not image holes")
    size = 3 * CS - 100
    exts = [_xt(10, 0, 1, W), _xt(20, 1, 2, second)]
    _fx(F._ext_skip_read(exts[1]) == (second == NW), "the reader's own floor does not see the run as intended")
    return {"name": "e1.bin", "storage": "non-resident", "file_size": size, "file_attrs": 0x20,
            "raw_value": b"", "ads": [], "extents": exts}, b"W" * CS + b"\0" * (size - CS)


# N127: green in wave D step D2 (RED until then: _extent_hole_ranges reports a never-written run it never reads as a hole range (fd:10948))
def test_n127_hole_ranges_skip_runs_the_reader_never_reads(syn):
    tgt, _want = _n127_target(syn, NW)
    with open(syn.path, "rb") as fh:
        got = F._extent_hole_ranges(fh, 0, CS, tgt["extents"], tgt["file_size"])
    assert got == [], "hole ranges %r lie only in a run extract never reads" % (got,)


# N127: green in wave D step D2 (RED until then: _extent_hole_bytes counts a never-written run it never reads as hole bytes (fd:10988))
def test_n127_hole_bytes_skip_runs_the_reader_never_reads(syn):
    tgt, _want = _n127_target(syn, NW)
    with open(syn.path, "rb") as fh:
        got = F._extent_hole_bytes(fh, 0, CS, tgt["extents"])
    assert got == 0, "%r hole bytes counted in a run the reader never reads" % (got,)


def test_n127_control_a_written_run_in_a_hole_is_still_counted(syn):
    """The genuine disclosure (C05, LAB-E e5) must stay: a WRITTEN run read from an image hole is counted."""
    tgt, _want = _n127_target(syn, W)
    with open(syn.path, "rb") as fh:
        assert F._extent_hole_ranges(fh, 0, CS, tgt["extents"], tgt["file_size"]) == [(CS, tgt["file_size"] - CS)]
        assert F._extent_hole_bytes(fh, 0, CS, tgt["extents"]) == 2 * CS


# N127: green in wave D step D2 (RED until then: extract exits 2 with a 'stores as holes' note for bytes it never read (a C13 false alarm))
def test_n127_extract_exits_0_without_a_hole_note_when_only_unread_runs_are_holes(syn):
    tgt, want = _n127_target(syn, NW)
    r = syn.extract(tgt)
    _keep(r.data == want, "the extracted bytes changed (W then zeros)" + r.ctx())
    notes = [l for l in r.err.splitlines() if _HOLES_NOTE.search(l)]
    assert not notes, "a hole note for bytes never read:\n" + "\n".join(notes)
    assert not (r.sidecar and r.sidecar.get("Status") == "holes_present"), "sidecar: %r" % (r.sidecar,)
    assert r.rc == 0, "rc %d for a correct extract whose only holes lie in never-read runs" % r.rc + r.ctx()


# N127: green in wave D step D2 (RED until then: --refuse-holes refuses a file whose only 'holes' lie in runs extract never reads)
def test_n127_refuse_holes_writes_a_file_whose_only_holes_are_unread_runs(syn):
    tgt, want = _n127_target(syn, NW)
    r = syn.extract(tgt, extra=["--refuse-holes"])
    assert r.data == want, "nothing written (or wrong bytes) under --refuse-holes" + r.ctx()
    assert r.rc == 0, r.ctx()


def test_n127_control_written_run_in_a_hole_keeps_the_note_and_exit_2(syn):
    tgt, want = _n127_target(syn, W)
    r = syn.extract(tgt)
    assert r.data == want, r.ctx()
    assert r.rc == 2 and any(_HOLES_NOTE.search(l) for l in r.err.splitlines()), r.ctx()


def test_n127_control_unread_run_over_foreign_bytes_is_zero_filled_and_clean(syn):
    """The win11refs15t64k shape: the never-written run's clusters hold foreign bytes; extract never reads them."""
    tgt, want = _n127_target(syn, NW, foreign=True)
    r = syn.extract(tgt)
    assert r.data == want and r.rc == 0, r.ctx()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N128 -- snapshot versions read never-written runs; and the class sites the rg found
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Version 0x1001 'copiedversion': cluster W written at VCN 0, then a 17-cluster... here a 2-cluster run at VCN 1-2
# with flags 0x40 (never written), the shape E2 [V6] found on win11refs2tsnapshots. Its clusters hold foreign
# bytes F/G, or are image holes.

def _snap_vd(syn, foreign):
    syn.put(10, b"W" * CS)
    if foreign:
        syn.put(21, b"F" * CS)
        syn.put(22, b"G" * CS)
    else:
        _fx(syn.is_hole(21) and syn.is_hole(22), "clusters 21-22 are not image holes")
    size = 3 * CS - 100
    hv = holder_value(size, 3 * CS, [ext_row(V(10), 0, 1, W), ext_row(V(21), 1, 2, NW)])
    vd = long_row([(keyb0("copiedversion"), snap_value(0x1001, size)), (key80(0x1001), hv)], size=size, alloc=3 * CS)
    return vd, size


def _snap_result(vd, size):
    return {"path": "d/snap.txt", "snapshots": [{"name": "copiedversion", "stream_size": size,
                                                 "is_true_snapshot": True, "raw_len": 0}],
            "value_len": len(vd), "vd": vd, "create_time": FT, "modify_time": FT}


def _version(recs):
    got = [r for r in recs if r["sub_id"] == 0x1001]
    _fx(len(got) == 1, "version 0x1001 not recovered once: %r" % ([(r["name"], r["sub_id"]) for r in recs],))
    return got[0]


# N128: green in wave D step D2 (RED until then: a snapshot version reads its never-written run and returns the clusters' foreign bytes)
def test_n128_snapshot_version_zero_fills_never_written_runs(syn):
    vd, size = _snap_vd(syn, True)
    with _registers_restored(), open(syn.path, "rb") as fh:
        rec = _version(F.recover_snapshot_streams(fh, 0, CS, _tr(), vd))
    c = rec["content"]
    _keep(c is not None and c[:CS] == b"W" * CS, "the version's written cluster is no longer recovered: %r"
          % (None if c is None else c[:8],))
    assert len(c) == size and not any(c[CS:]), (
        "version 0x1001 carries %d foreign byte(s) from its never-written run" % sum(1 for b in c[CS:] if b))


# N128: green in wave D step D2 (RED until then: a snapshot version asks the image about clusters of a never-written run it should never read)
def test_n128_snapshot_version_does_not_count_unread_runs_as_holes(syn):
    vd, size = _snap_vd(syn, False)
    with _registers_restored(), open(syn.path, "rb") as fh:
        n0 = len(F._CONTENT_HOLES)
        rec = _version(F.recover_snapshot_streams(fh, 0, CS, _tr(), vd))
        new = list(F._CONTENT_HOLES[n0:])
    _keep(rec["content"] is not None and rec["content"][:CS] == b"W" * CS, "the written cluster is lost")
    assert not new, "hole bytes recorded for clusters of a never-written run: %r" % (new,)


# N128: green in wave D step D2 (RED until then: snapshots --extract writes the never-written run's foreign bytes as the version's content)
def test_n128_snapshots_extract_writes_zeros_not_foreign_bytes(syn):
    vd, size = _snap_vd(syn, True)
    r = syn.snapshots(_snap_result(vd, size))
    f = r.files.get("d_snap.txt__copiedversion")
    _fx(f is not None, "the version file was not written" + r.ctx())
    _keep(f[:CS] == b"W" * CS, "the written cluster changed" + r.ctx())
    assert not any(f[CS:]), "foreign bytes %r written as the version's content" % (sorted(set(f[CS:])),)


# N128: green in wave D step D2 (RED until then: snapshots --extract exits 2 with a HOLES warning for a never-written run it should never read (C14))
def test_n128_snapshots_extract_exits_0_when_only_unread_runs_are_holes(syn):
    vd, size = _snap_vd(syn, False)
    r = syn.snapshots(_snap_result(vd, size))
    f = r.files.get("d_snap.txt__copiedversion")
    _keep(f is not None and f == b"W" * CS + b"\0" * (size - CS), "the version file changed" + r.ctx())
    warn = [l for l in r.err.splitlines() if _HOLES_NOTE.search(l) and "copiedversion" in l]
    assert not warn, "hole warning for a never-read run:\n" + "\n".join(warn)
    assert r.rc == 0, r.ctx()


def test_n128_control_version_without_unwritten_runs_is_read_and_clean(syn):
    syn.put(10, b"W" * CS)
    syn.put(11, b"X" * CS)
    size = 2 * CS - 10
    hv = holder_value(size, 2 * CS, [ext_row(V(10), 0, 2, W)])
    vd = long_row([(keyb0("copiedversion"), snap_value(0x1001, size)), (key80(0x1001), hv)], size=size, alloc=2 * CS)
    r = syn.snapshots(_snap_result(vd, size))
    assert r.files.get("d_snap.txt__copiedversion") == (b"W" * CS + b"X" * CS)[:size] and r.rc == 0, r.ctx()


# Class sites (PLAN section 5, "search the whole code base for the class"): three more readers decode a holder
# WITHOUT its flags and read every block, so N63 is not applied. Not in the running-log row; RED so that the
# decision on their scope is explicit (report section 4).

def _foreign_nw(syn):
    syn.put(10, b"W" * CS)
    syn.put(21, b"F" * CS)
    syn.put(22, b"G" * CS)
    syn.put(30, b"S" * CS)
    size = 3 * CS - 100
    return size, holder_value(size, 3 * CS, [ext_row(V(10), 0, 1, W), ext_row(V(21), 1, 2, NW)])


# N128 (class site): green in wave D step D2 (RED until then: _recover_inline_extent_content (live extract / get_file_content) reads a never-written run)
def test_n128_class_live_inline_holder_reassembly_does_not_read_never_written_runs(syn):
    size, hv = _foreign_nw(syn)
    vd = long_row([(key80(0x1000), hv)], size=size, alloc=3 * CS)
    with _registers_restored(), open(syn.path, "rb") as fh:
        b = F._recover_inline_extent_content(fh, 0, CS, _tr(), vd)
    assert b is None or not any(b[CS:]), "live content carries foreign bytes %r from a never-written run" % (
        sorted(set(b[CS:])),)


# N128 (class site): green in wave D step D2 (RED until then: recover_cow_current_content reads the newest snapshot's never-written run)
def test_n128_class_cow_current_content_does_not_read_never_written_runs(syn):
    size, hv_snap = _foreign_nw(syn)
    vd = long_row([(keyb0("v1"), snap_value(0x1001, size)), (key80(0x1000), holder_value(size, 0, [])),
                   (key80(0x1001), hv_snap)], size=size, alloc=3 * CS)
    with _registers_restored(), open(syn.path, "rb") as fh:
        b = F.recover_cow_current_content(fh, 0, CS, _tr(), vd)
    _fx(b is None or b[:CS] == b"W" * CS, "the shared written cluster is not what was planted")
    assert b is None or not any(b[CS:]), "CoW current content carries foreign bytes %r" % (sorted(set(b[CS:])),)


# N128 (class site): green in wave D step D2 (RED until then: _snapshot_shared_blocks offers a snapshot's never-written run as shared blocks)
def test_n128_class_shared_blocks_do_not_include_never_written_runs(syn):
    size, hv_snap = _foreign_nw(syn)
    vd = long_row([(keyb0("v1"), snap_value(0x1001, size)),
                   (key80(0x1000), holder_value(size, CS, [ext_row(V(30), 0, 1, W)])),
                   (key80(0x1001), hv_snap)], size=size, alloc=3 * CS)
    with _registers_restored(), open(syn.path, "rb") as fh:
        b = F._recover_inline_extent_content(fh, 0, CS, _tr(), vd)
    _fx(b is None or b[:CS] == b"S" * CS, "the current stream's own cluster is not what was planted")
    assert b is None or not any(b[CS:]), "shared blocks from a never-written run carry %r" % (sorted(set(b[CS:])),)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Image-based REDs (the serial runner; each skips when its image is absent)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _disk(relpath):
    """A corpus image by its path under analysis/rawdisk/disks, READ-ONLY; skipped when absent."""
    p = _corpus_image(relpath)                      # N386: by its step path
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % relpath)
    _fx(p.replace(os.sep, "/").endswith("/" + relpath), "%s resolved to %s" % (relpath, p))
    return p


@contextlib.contextmanager
def _scratch(tag):
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="b2_carve_%s_" % tag, dir=SCRATCH)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _limit_fsize(n):
    def _pre():
        import resource
        resource.setrlimit(resource.RLIMIT_FSIZE, (n, n))
    return _pre


def _img_run(image, args, cwd, fsize=None, binary=False):
    pre = _limit_fsize(fsize) if fsize else None
    try:
        r = subprocess.run([sys.executable, "-B", FOREFST, image] + list(args), capture_output=True,
                           timeout=IMAGE_TIMEOUT, cwd=cwd, preexec_fn=pre)
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s %s" % (os.path.basename(image), " ".join(args)))
    err = r.stderr.decode("utf-8", "replace")
    if "Traceback (most recent call last)" in err:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + err[-3000:])
    out = r.stdout if binary else r.stdout.decode("utf-8", "replace")
    return r.returncode, out, err


def _export_carve(image, d, fsize=None, extra=()):
    out = os.path.join(d, "out")
    rc, so, se = _img_run(image, ["export", "deleted", "--carve", out] + list(extra), d, fsize=fsize)
    mp = os.path.join(out, "recovery_manifest.json")
    _fx(os.path.exists(mp), "no recovery_manifest.json (rc %d)\n%s" % (rc, se[-3000:]))
    try:
        with open(mp) as fh:
            man = jdoc(json.load(fh), F._DELETED_MANIFEST_KEYS)                              # K21: internal names
    except ValueError as e:
        # a manifest the run could not write whole (a file-size limit below its size) is the harness's problem, not
        # the defect under test: the limit must fail the carve only (N460, the writer-failure shape, is wave E's)
        raise RedFixtureError("recovery_manifest.json is not whole (%s; %d bytes, rc %d)\n%s"
                              % (e, os.path.getsize(mp), rc, se[-2000:]))
    recs = {}
    for r in man["Records"]:                                                     # K21 (acceptance 1.14.0)
        recs.setdefault(r["name"], []).append(r)
    return Result(rc=rc, out=so + _side_text(out), err=se, manifest=man, records=recs, dir=out)


@pytest.fixture(scope="module")
def lab314_export():
    """ONE `export deleted --carve` of step6/lab314_main.raw, shared by the B5/B6 image REDs; its output directory
    (about 5 MB) is deleted when the module ends."""
    img = _disk("step6/lab314_main.raw")
    with _scratch("lab314") as d:
        yield _export_carve(img, d)


_LAB314_NOFILE = ("FVE2.{aff97bac-a69b-45da-aba1-2cfbce434750}.1", "FVE2.{aff97bac-a69b-45da-aba1-2cfbce434750}.2",
                  "recycle_me.bin")
_LAB314_CRC = (("big10k.bin", 3), ("small500.bin", 1))   # row_size 36 / 28, flags 0x2400d0 / 0x1c00d0 (page 12360)


# B6: green in wave D step D2 (RED until then: lab314_main: FVE2.{aff97bac...}.1/.2 and recycle_me.bin are graded 'metadata + carve' and get no carve file and no reason; the blind audit's K024, RED on 1.13.1 in red/RED_BATCH2_SERIAL_RUN.md, 2026-09-28)
def test_b6_image_lab314_the_three_rows_produce_a_file_or_state_why(lab314_export):
    """The row's own words: 'Each of the 3 lab314_main rows either produces a file or states why not.'"""
    r = lab314_export
    silent = []
    for n in _LAB314_NOFILE:
        _keep(n in r.records, "%s is no longer indexed in the manifest" % n)
        for rec in r.records[n]:
            if rec.get("recoverable") == "extent_backed" and not rec.get("content_file") \
                    and not _states_why_not(rec, r.text, n):
                silent.append(n)
    assert not silent, "extent-backed with no carve file and no reason: %r" % (silent,)


# B6: green in wave D step D2 (RED until then: lab314_main: rows graded 'metadata + carve' get no carve file and no reason (one predicate); the blind audit's K024, RED on 1.13.1 with 15 rows in red/RED_BATCH2_SERIAL_RUN.md)
def test_b6_image_lab314_every_extent_backed_row_produces_a_file_or_states_why(lab314_export):
    r = lab314_export
    silent = []
    for name, recs in sorted(r.records.items()):
        for rec in recs:
            if rec.get("recoverable") == "extent_backed" and not rec.get("content_file") \
                    and not _states_why_not(rec, r.text, name):
                silent.append(name)
    assert not silent, "%d extent-backed row(s) with no carve file and no reason: %r" % (len(silent), silent)


# B6: green in wave D step D2 (RED until then: lab314_main: no carve reports how many of its declared clusters were read)
def test_b6_image_lab314_every_carve_reports_declared_and_read_clusters(lab314_export):
    r = lab314_export
    carved = [(n, rec) for n, recs in r.records.items() for rec in recs
              if (rec.get("content_file") or "").endswith(".carved")]
    _fx(carved, "no carve on lab314_main")
    missing = [n for n, rec in carved if _cluster_report(rec) is None]
    assert not missing, "%d of %d carves carry no declared-vs-read count, e.g. %r" % (
        len(missing), len(carved), missing[:5])


# B5: green in wave D step D2 (RED until then: lab314_main: big10k.bin and small500.bin are carved from CRC-bearing rows with no CRC32-C statement)
def test_b5_image_lab314_integrity_carves_state_their_crc_result(lab314_export):
    """Re-scoped in wave D step D2 (acceptance change, D2_NOTES): big10k.bin and small500.bin are STILL PRESENT entries
    -- prior versions of live files -- and decision 48 (WC-3) offers no carve of a live file's map (its clusters may
    hold the current content), so they are not carved and say why. Every carve that IS made and whose map carries a
    CRC-32C states its result. B5 on real data is witnessed on the public sample (test_1132_d2_carve_extract.py: one
    carve whose CRC matches, one whose cluster differs)."""
    r = lab314_export
    for name, ncrc in _LAB314_CRC:
        recs = r.records.get(name, [])
        _keep(recs, "%s is no longer indexed" % name)
        for rec in recs:
            if rec.get("status") == "still present":
                assert not rec.get("content_file") and "live" in (rec.get("no_carve_reason") or ""), rec
            elif (rec.get("content_file") or "").endswith(".carved"):
                assert (_crc_statement(rec, r.text, name, "mismatch")
                        or _crc_statement(rec, r.text, name, ("verified", ncrc))), (
                    "%s: %d CRC-bearing cluster(s) carved, no per-file CRC32-C result:\n%s"
                    % (name, ncrc, json.dumps(rec, indent=1)))
    for name, recs in r.records.items():
        for rec in recs:
            c = (rec.get("carve") or {}).get("crc")
            if (rec.get("content_file") or "").endswith(".carved") and c:
                assert c["checked"] + c["unset"] + c["unchecked"] == c["clusters_with_crc"], rec


_N193_CARVE = "FVE2.{c9ca54a3-6983-46b7-8684-a7e5e23499e3}.1"      # lab314_main's largest DELETED carve: 266,240 B


# N193: green in wave D step D2 (RED until then: lab314_main: a carve write a file-size limit fails leaves content/<name>.carved truncated)
def test_n193_image_lab314_failed_write_leaves_no_truncated_carve():
    """Re-scoped in wave D step D2 (D2_NOTES): 0906.zip is a STILL PRESENT entry and is no longer carved (WC-3), and
    every carve left on the volume is smaller than the run's manifest, so a file-size limit cannot fail a carve write
    alone. `--search` narrows the export to one deleted file whose 266,240-byte carve a 100,000-byte limit fails, while
    the index files stay under it: 1.13.1 and the pre-step tree leave content/<name>.carved at 100,000 bytes."""
    img = _disk("step6/lab314_main.raw")
    with _scratch("lab314_fsize") as d:
        r = _export_carve(img, d, fsize=100000, extra=["--search", _N193_CARVE])
        fails = os.path.join(r.dir, "_extract_failures.json")
        cname = F._safe_filename(_N193_CARVE) + ".carved"            # the content file's name ({ } -> _)
        _fx(os.path.exists(fails) and cname in _text_of(fails), "the limit did not fail the %s carve" % _N193_CARVE)
        recs = [rec for rec in r.records.get(_N193_CARVE, []) if rec.get("carved_len")]
        _fx(recs, "no %s carve record" % _N193_CARVE)
        want = recs[0]["carved_len"]
        _fx(want > 100000, "the carve is not larger than the limit")
        p = os.path.join(r.dir, "content", cname)
        got = os.path.getsize(p) if os.path.exists(p) else None
        assert got is None or got == want, "content/%s is %d of %d bytes" % (cname, got, want)


# N127: the golden rows (C13) and LAB-E, with their controls

_LABE_SHA = {  # Windows SHA-256 of each file (LABE/log/labe_expected.csv on the volume; E2 runlog [V4])
    "e1_setlength_4096k.bin": ("8f761032", "16ee"),
    "e1_setlength_8k.bin": ("9e0075dd", "4912"),
    "e3_farwrite_4096k.bin": ("cb949f80", "c4ce"),
    "e5_control_realzeros.bin": ("c3502047", "0479"),
}


def _extract_stdout(relimg, target):
    img = _disk(relimg)
    with _scratch("x") as d:
        rc, data, err = _img_run(img, ["extract", target], d, binary=True)
    return rc, data, err


def _hole_note_bytes(err):
    m = [re.search(r"NOTE: (\d+) of (\d+) bytes of", l) for l in err.splitlines() if _HOLES_NOTE.search(l)]
    m = [x for x in m if x]
    return int(m[0].group(1)) if m else 0


@pytest.mark.parametrize("fname", ("e1_setlength_4096k.bin", "e1_setlength_8k.bin", "e3_farwrite_4096k.bin"))
# N127: green in wave D step D2 (RED until then: labE: extract exits 2 and reports never-read bytes as written from image holes)
def test_n127_image_labE_unread_runs_are_not_hole_bytes(fname):
    rc, data, err = _extract_stdout("step7/labE.raw", "LABE/" + fname)
    h = hashlib.sha256(data).hexdigest()
    pre, suf = _LABE_SHA[fname]
    _keep(h.startswith(pre) and h.endswith(suf), "%s: output SHA-256 %s is not the Windows value %s...%s"
          % (fname, h, pre, suf))
    assert _hole_note_bytes(err) == 0, "hole note for bytes never read:\n" + err[-1500:]
    assert rc == 0, "rc %d\n%s" % (rc, err[-1500:])


def test_n127_image_control_labE_real_zeros_keep_exit_2():
    """e5: zeros that were WRITTEN (flags 0x50) and are stored as image holes: 32,768 bytes, a real disclosure."""
    rc, data, err = _extract_stdout("step7/labE.raw", "LABE/e5_control_realzeros.bin")
    h = hashlib.sha256(data).hexdigest()
    pre, suf = _LABE_SHA["e5_control_realzeros.bin"]
    assert h.startswith(pre) and h.endswith(suf)
    assert rc == 2 and _hole_note_bytes(err) == 32768, "rc %d\n%s" % (rc, err[-1500:])


_XBPT = ("test/elvis_dir_index_149423/elvis_dir_victor_121923/elvis_dir_hotel_670324/elvis_dir_output_358165/"
         "elvis_dir_oscar_874075/xbpt_delta_victor_412034.ini")
_ZERO = "hello/ciao/g_001/g_002/g_003/g_004/g_005/g_006/p_001/p_002/p_003/p_004/p_005/zero.bin"
_GOLDEN_OUT = {   # analysis/verification/golden.txt, the extract rows' output hashes (bytes kept by the fix)
    "xbpt": "56887373ca63b750a8ce410bce39fa3f7ebadd4e48edcc67d97fded9d259418a",
    "zero": "d339d7f934b3f317239728ad1fa2522191a8d41a8c242325f821749bac8c23ee",
}


@pytest.mark.parametrize("relimg,target,key", (
    ("step2/win11refs2g.raw", _XBPT, "xbpt"),
    ("step3b/win11refs2tmillionsofactionsv2.raw", _ZERO, "zero"),
), ids=("win11refs2g-xbpt", "millionsofactionsv2-zero.bin"))
# N127: green in wave D step D2 (RED until then: golden C13 rows: extract exits 2 over bytes it never read (205,215 / 52,341,582 'hole' bytes))
def test_n127_image_golden_c13_rows_exit_0(relimg, target, key):
    rc, data, err = _extract_stdout(relimg, target)
    _keep(hashlib.sha256(data).hexdigest() == _GOLDEN_OUT[key], "the output bytes changed")
    assert _hole_note_bytes(err) == 0, err[-1500:]
    assert rc == 0, "rc %d\n%s" % (rc, err[-1500:])


# N127: green in wave D step D2 (RED until then: win11refs5g64k xbpt: the hole figure counts the unread run (205,215) where 61,440 were read from holes)
def test_n127_image_64k_figure_counts_only_bytes_read_from_holes():
    rc, data, err = _extract_stdout("step2/win11refs5g64k.raw", _XBPT)
    _keep(hashlib.sha256(data).hexdigest() == _GOLDEN_OUT["xbpt"], "the output bytes changed")
    _keep(rc == 2, "rc %d: 61,440 bytes of the written 64 KiB cluster ARE read from image holes" % rc)
    assert _hole_note_bytes(err) == 61440, err[-1500:]


def test_n127_image_control_15t64k_counts_the_read_holes_only():
    """The never-written run holds foreign bytes here, so 1.13.1 already reports only the 61,440 read-hole bytes."""
    rc, data, err = _extract_stdout("step3/win11refs15t64k.raw", _XBPT)
    assert hashlib.sha256(data).hexdigest() == _GOLDEN_OUT["xbpt"]
    assert rc == 2 and _hole_note_bytes(err) == 61440, err[-1500:]


# N128: green in wave D step D2 (RED until then: win11refs2tsnapshots: 'copiedversion' (0x1001) is read through its never-written run -> HOLES warning, rc 2 (C14))
def test_n128_image_snapshots_extract_does_not_read_the_never_written_run():
    img = _disk("step3/win11refs2tsnapshots.raw")
    with _scratch("snap") as d:
        out = os.path.join(d, "out")
        rc, so, se = _img_run(img, ["snapshots", "--extract", out], d)
        names = os.listdir(out) if os.path.isdir(out) else []
    _keep(any(n.endswith("__copiedversion") for n in names), "the copiedversion file is no longer written: %r"
          % (names,))
    warn = [l for l in se.splitlines() if _HOLES_NOTE.search(l) and "copiedversion" in l]
    assert not warn, "\n".join(warn)
    assert rc == 0, "rc %d\n%s" % (rc, se[-2000:])


# N130: green in wave D step D2 (RED until then: winsiderv2 `deleted`: the misframed row 0x2800180050 is reported as 'container table has no mapping')
def test_n130_image_winsiderv2_misframe_is_not_blamed_on_the_container_table():
    img = _disk("step7/winsiderv2.raw")
    with _scratch("wsv2") as d:
        rc, so, se = _img_run(img, ["deleted"], d)
    blamed = [l for l in se.splitlines() if "2800180050" in l and _CT_BLAME.search(l) and not _NOT_CT.search(l)]
    assert not blamed, "\n".join(blamed[:3])
