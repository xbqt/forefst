"""1.13.2 RED cases, group a_coverage: plan rows A5, A6, A8 and A9.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 2 A (rows A5, A6, A8, A9), section 5 "RED first", decision 19
(the maintainer's bar: every RED fails on 1.13.1 BECAUSE of the defect, not because of an artefact, and is
independently confirmed). Report, with the expected failure of every node: `analysis/reports/v1.13.2/red/
RED_a_coverage.md`.

What each RED asserts (the row's Acceptance column)
---------------------------------------------------
A5  N4 re-run. The 8 pages N4 flipped were never recorded, so the set is rebuilt by a stated rule on the battery's
    base A (`win11refsmini.raw`) with N4's split: 1 system-table page (verified by `--checksums`' page walk), 2
    object root pages (verified by `--checksums`' page references) and 5 object-tree child pages (verified by
    neither). Every edit in the set exits 2 under `integrity --checksums`, or the output names its coverage and
    never claims "no tampering" without qualifying it (open decision O1 picks which; both pass).
A6  One extent-index child page and one child page below an embedded attribute index (E73), on
    `win11refstestmftecmd.raw`: a flipped one exits 2 under `integrity --fullchecksums` AND under `--verify-pages`
    on a command that reads it.
A8  An unreadable region inside the scan range: coverage below 100%, INCOMPLETE, exit 2, on the four paths the
    published item names (`deleted`, `deleted --full`, `deleted --scan-pages`, `export deleted`).
    Unit node (2026-09-27): the live-slack loop's own drop, which the image paths mask (the page walk reads the
    page first and records the skip): the walk's read succeeds, the loop's re-read raises EIO, and the loss must
    reach the exit rule and be said.
A9  (1) A Container-Table row flip that maps two containers to the same clusters: `summary`, `dataruns`,
    `integrity` (no `--checksums`) and `refsanalysis containers` warn and exit 2. (2) The re-signed move is
    undetectable by design: the limit is stated in `docs/structures/container_table.md` and in the `integrity`
    section of `docs/tools/forefst.md`, and the battery records the probe as "untestable by design".

Damage and faults
-----------------
* Flips land on a hole-preserving scratch copy of a corpus image under ``$FOREFST_RED_SCRATCH`` (default:
  ``forefst_red_scratch`` in the system temp directory): at most ONE copy on disk at a time, deleted by exact path when the
  next recipe or the module ends. Nothing damaged is ever written into the repo.
* A5 and A6 flips are DIGEST-ONLY: one byte of a live page that no part of the node uses (outside the page and node
  headers, the key index and every row), so the page's content as any reader parses it is unchanged and the only
  thing that can see the edit is a check of the page against the digest its parent recorded. A structural check
  cannot fire on it, so a RED cannot pass (or fail) by accident.
* A read error cannot be made by damaging bytes. A8 runs the real CLI entry point (``runpy`` as ``__main__``, so
  ``_escalate_rc`` runs exactly as from the shell) under a harness that wraps ``open()`` for the image and raises
  EIO on reads overlapping one region -- the K028 instrument's model. The image is opened read-only and never
  copied. The same harness in trace mode counts the reads that touched a region; A6 uses it to prove that the
  command under test really read the damaged page.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; the fix commit removes the mark and an XPASS fails the
  run. Only the final plain ``assert`` states the acceptance.
* Everything that is not the defect raises ``RedFixtureError`` (NOT an AssertionError), which a strict xfail never
  counts as the expected failure: a page the rebuild cannot find, a flip that did not land or did not break the
  parent's digest (checked with this module's own CRC64, not the tool's), a damage the command never read, a copy
  that is not sparse, a crash (traceback) or a timeout.
* Controls (not xfail) pass on 1.13.1 and must keep passing: the undamaged volumes exit 0 on every probed surface,
  the detectors stay quiet on their real output, and each fault region is read only by the scan under test.
* ``pytest --runxfail`` runs the REDs as plain tests and prints each observed value in its assertion message.

Unit-level nodes (no image): ``pytest -k "test_red_ or resigned or live_slack"``.
"""
import atexit
import bisect
import collections
import errno
import functools
import hashlib
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
from conftest import make_msb_page                       # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
REFSANALYSIS = os.path.join(REPO, "refsanalysis.py")
TIMEOUT = 3600
SCRATCH = os.environ.get(
    "FOREFST_RED_SCRATCH",
    os.path.join(tempfile.gettempdir(), "forefst_red_scratch"))
MAX_COPY_ALLOCATED = 1 << 30      # win11refstestmftecmd allocates 381 MB, lab314_main 288 MB, win11refsmini 13 MB
FREE_MARGIN = 1 << 30             # the workspace disk backs the maintainer's VM: never fill it
NULL = (0, 0xFFFFFFFFFFFFFFFF)

BASE_A = "step1/win11refsmini.raw"         # battery base A (P0.1 golden.json "A"); N386: by step path
MFTECMD = "win11refstestmftecmd.raw"       # A6's named volume
LAB = "lab314_main.raw"                    # battery base B; the K013/K014 audit volume


class RedFixtureError(Exception):
    """The fixture or the run is not what the case needs. Deliberately NOT an AssertionError."""


def _fx(cond, msg):
    if not cond:
        raise RedFixtureError(msg)


def _red(item, why):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason="RED 1.13.2 %s: %s" % (item, why))


def _need(name):
    p = _corpus_image(name)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return p


# ─── an independent CRC64 (reflected, poly 0x9A6C9329AC4BC9B5, init/xorout all ones) ─────────────────────────
# Used for every "the parent's digest matches this page" / "the flip broke it" precondition, so a fixture cannot
# agree with the tool merely because both run the tool's code. Cross-checked against F.refs_crc64 in a unit test.

_CRC64 = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0x9A6C9329AC4BC9B5 if _c & 1 else _c >> 1
    _CRC64.append(_c)


def _crc64(data):
    crc = 0xFFFFFFFFFFFFFFFF
    for b in data:
        crc = _CRC64[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFFFFFFFFFF


def _matches(dlen, stored, page):
    if not page or dlen not in (8, 32) or len(stored) != dlen:
        return False
    return (struct.pack("<Q", _crc64(page)) if dlen == 8 else hashlib.sha256(page).digest()) == stored


def _ref_digest(ref):
    """(len, digest) of a 48/72-byte page reference: length at +0x24, digest at +0x28 (F._page_ref_digest)."""
    if len(ref) < 0x30:
        return None
    dlen = F.le32(ref, 0x24)
    if dlen not in (8, 32) or len(ref) < 0x28 + dlen:
        return None
    return dlen, bytes(ref[0x28:0x28 + dlen])


def _ot_digest(vd):
    """(len, digest) an Object-Table row records for its object's root page: length at +0x44, digest at +0x48."""
    dlen = F.le32(vd, 0x44) if len(vd) >= 0x48 else 0
    if dlen not in (8, 32) or 0x48 + dlen > len(vd):
        return None
    return dlen, bytes(vd[0x48:0x48 + dlen])


# ─── pages ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _node(page):
    """(is_inner, rows) of one MSB+ node, read the way the tool's `_walk` reads it. rows: (ro, ko, kl, vo, vl, key,
    value). (None, []) when `page` is not a node."""
    if len(page) < 0x54 or page[:4] != b"MSB+":
        return None, []
    thoff = 0x50 + F.le32(page, 0x50)
    if thoff + 40 > len(page):
        return None, []
    tbl = struct.unpack_from("<10I", page, thoff)
    is_inner = bool(tbl[3] & 0x100)
    astart, aend = tbl[4], tbl[8]
    rows = []
    if astart < aend:
        for i in range((aend - astart) // 4):
            aa = thoff + astart + 4 * i
            if aa + 4 > len(page):
                break
            ro = thoff + F.le16(page, aa)
            if ro + 16 > len(page):
                break
            _sz, ko, kl, _r, vo, vl, _x = struct.unpack_from("<I6H", page, ro)
            if (kl and ro + ko + kl > len(page)) or (vl and ro + vo + vl > len(page)):
                continue
            rows.append((ro, ko, kl, vo, vl, bytes(page[ro + ko:ro + ko + kl]), bytes(page[ro + vo:ro + vo + vl])))
    return is_inner, rows


def _unused_offset(page):
    """The highest byte of an MSB+ page that no part of the node uses: outside the page and node headers, the
    key-index array and every row the index names (by its size field and by its key and value extents). A flip
    there changes the page's digest and nothing any reader parses. None when there is no such byte."""
    if len(page) < 0x54 or page[:4] != b"MSB+":
        return None
    thoff = 0x50 + F.le32(page, 0x50)
    if thoff + 40 > len(page):
        return None
    tbl = struct.unpack_from("<10I", page, thoff)
    astart, aend = tbl[4], tbl[8]
    used = [(0, thoff + 40)]
    if astart < aend:
        used.append((thoff + astart, thoff + aend))
        for i in range((aend - astart) // 4):
            aa = thoff + astart + 4 * i
            if aa + 4 > len(page):
                used.append((aa, len(page)))
                break
            ro = thoff + F.le16(page, aa)
            if ro + 16 > len(page):
                used.append((min(ro, len(page)), len(page)))
                continue
            sz, ko, kl, _r, vo, vl, _x = struct.unpack_from("<I6H", page, ro)
            end = max(ro + 16, ro + ko + kl, ro + vo + vl, ro + sz if sz <= len(page) - ro else ro + 16)
            used.append((ro, min(end, len(page))))
    used.sort()
    if max(e for _s, e in used) < len(page):
        return len(page) - 1
    merged = []
    for s, e in used:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    for (_s0, e0), (s1, _e1) in reversed(list(zip(merged, merged[1:]))):
        if e0 < s1:
            return s1 - 1
    return None


def _plcns(slots, use_tr):
    out = []
    for s in slots:
        if s in NULL:
            break
        out.append(use_tr.tr(s) if use_tr else s)
    return out


def _flip_at(ps, cs, plcns, page):
    """Absolute image offset of `_unused_offset(page)` for a page read from `plcns`, or None."""
    off = _unused_offset(page)
    if off is None or off // cs >= len(plcns):
        return None
    return ps + plcns[off // cs] * cs + off % cs


def _read_page(path, ps, cs, plcns):
    page = b""
    with open(path, "rb") as fh:
        for p in plcns:
            fh.seek(ps + p * cs)
            page += fh.read(cs)
    return page


def _integrity_walk(f, ps, cs, tr, roots, obj_map):
    """(head, plcns) of every page `integrity` enumerates: the system root tables, then every object tree."""
    visited, ptc = set(), []
    for idx, rv in enumerate(roots):
        if rv:
            F._walk_btree_pages(f, ps, cs, None if idx in F._CT_ROOT_INDICES else tr, rv, visited, ptc)
    for _oid, vl in sorted(obj_map.items()):
        F._walk_btree_pages(f, ps, cs, tr, vl, visited, ptc)
    return ptc


def _extent_index_refs(buf, n):
    """Child-page references of the extent node at buf[n:] when it is an INDEX node (as `_extent_leaf_rows`)."""
    level, offs = F._extent_node_rows(buf, n)
    if level in (None, 0):
        return []
    out = []
    for ro in offs:
        if ro + 16 > len(buf):
            continue
        _sz, _ko, _kl, _fl, vo, vl, _x = struct.unpack_from("<I6H", buf, ro)
        if vl >= 0x30 and ro + vo + vl <= len(buf):
            out.append(bytes(buf[ro + vo:ro + vo + vl]))
    return out


def _embedded_index_refs(vd, base):
    """Child-page references of an E73 embedded INDEX node at vd[base:] (as `_descend_embedded_index`)."""
    if base + 0x24 > len(vd):
        return []
    astart, aend = F.le32(vd, base + 0x10), F.le32(vd, base + 0x20)
    if not (0 < astart < aend) or base + aend > len(vd):
        return []
    out, pos = [], base + astart
    while pos + 4 <= base + aend and pos + 4 <= len(vd):
        ab = base + F.le16(vd, pos)
        pos += 4
        if ab + 16 > len(vd):
            continue
        _sz, _ko, _kl, _fl, vo, vl, _x = struct.unpack_from("<I6H", vd, ab)
        if vl >= 0x30 and ab + vo + vl <= len(vd):
            out.append(bytes(vd[ab + vo:ab + vo + vl]))
    return out


def _is_current_data(akd, aval):
    """The current stream's $DATA row holding its extent map in a nested node (as `_embedded_data_extents`)."""
    return (len(akd) >= 0x14 and F.le32(akd, 8) == 0x80000002 and F.le16(akd, 0x0C) == 0x0080
            and F.le32(akd, 0x10) == 0x1000 and len(aval) > 0x88 + 0x28 and F.le32(aval, 0) == 0x88)


# ─── scratch copies (one at a time) ───────────────────────────────────────────────────────────────────────────

def _carve(src, dst):
    """Hole-preserving copy (SEEK_DATA/SEEK_HOLE): only the source's allocated ranges are written."""
    size = os.path.getsize(src)
    fi = os.open(src, os.O_RDONLY)
    try:
        with open(dst, "wb") as out:
            out.truncate(size)
            pos = 0
            while pos < size:
                try:
                    d = os.lseek(fi, pos, os.SEEK_DATA)
                except OSError:
                    break
                try:
                    h = min(os.lseek(fi, d, os.SEEK_HOLE), size)
                except OSError:
                    h = size
                os.lseek(fi, d, os.SEEK_SET)
                out.seek(d)
                rem = h - d
                while rem > 0:
                    chunk = os.read(fi, min(4 << 20, rem))
                    if not chunk:
                        break
                    out.write(chunk)
                    rem -= len(chunk)
                pos = h
    finally:
        os.close(fi)


def _sparse_capable(d):
    probe = os.path.join(d, "sparse.probe")
    try:
        with open(probe, "wb") as fh:
            fh.truncate(64 << 20)
        return os.stat(probe).st_blocks * 512 < (1 << 20)
    finally:
        if os.path.exists(probe):
            os.unlink(probe)


class _OneCopy(object):
    """At most ONE damaged copy on disk: asking for another recipe deletes the previous copy first."""

    def __init__(self):
        self.key = self.dir = self.path = None

    def get(self, key, base, flips):
        if key == self.key and self.path and os.path.exists(self.path):
            return self.path
        self.drop()
        alloc = os.stat(base).st_blocks * 512
        _fx(alloc <= MAX_COPY_ALLOCATED, "%s allocates %d bytes: too much for a scratch copy" % (base, alloc))
        os.makedirs(SCRATCH, exist_ok=True)
        free = shutil.disk_usage(SCRATCH).free
        _fx(free > alloc + FREE_MARGIN, "only %d bytes free under %s for a %d-byte copy" % (free, SCRATCH, alloc))
        self.dir = tempfile.mkdtemp(prefix="a_coverage_", dir=SCRATCH)
        _fx(_sparse_capable(self.dir), "%s cannot hold a sparse file; refusing a dense copy" % self.dir)
        self.path = os.path.join(self.dir, "target.raw")      # neutral name: the tool prints it
        _carve(base, self.path)
        got = os.stat(self.path).st_blocks * 512
        _fx(got <= alloc + (16 << 20), "the scratch copy allocated %d bytes for a %d-byte source" % (got, alloc))
        with open(self.path, "r+b") as fh:
            for off, xor in flips:
                fh.seek(off)
                before = fh.read(1)
                _fx(len(before) == 1, "flip offset 0x%x is past the end of %s" % (off, base))
                fh.seek(off)
                fh.write(bytes([before[0] ^ xor]))
                fh.flush()
                fh.seek(off)
                _fx(fh.read(1) != before, "flip did not land at 0x%x" % off)
        self.key = key
        return self.path

    def drop(self):
        if self.path and os.path.exists(self.path):
            os.unlink(self.path)
        if self.dir and os.path.isdir(self.dir):
            os.rmdir(self.dir)
        self.key = self.dir = self.path = None


_COPY = _OneCopy()
atexit.register(_COPY.drop)       # N568: other modules import _COPY; the fixture below runs for this module's tests only


@pytest.fixture(scope="module", autouse=True)
def _one_copy_at_a_time():
    yield
    _COPY.drop()


# ─── running the tools ────────────────────────────────────────────────────────────────────────────────────────

# The read harness. argv: TOOL IMAGE MODE OFFSET LENGTH REPORT [tool args...]. MODE "eio" raises EIO on every read
# of IMAGE that overlaps [OFFSET, OFFSET+LENGTH); "trace" only counts them. The tool runs as __main__ via runpy,
# so its own exit path (`_escalate_rc`, atexit reports, os._exit) is the command line's. Writes {"rc", "hits"}.
_HARNESS = r'''
import builtins, errno, json, os, runpy, sys
tool, img, mode, off, ln, rep = (sys.argv[1], os.path.realpath(sys.argv[2]), sys.argv[3], int(sys.argv[4]),
                                 int(sys.argv[5]), sys.argv[6])
rest = sys.argv[7:]
real_open = builtins.open
hits = []


class Wrapped(object):
    def __init__(self, fh):
        object.__setattr__(self, "_fh", fh)

    def read(self, n=-1):
        fh = object.__getattribute__(self, "_fh")
        pos = fh.tell()
        end = pos + n if (n is not None and n >= 0) else float("inf")
        if pos < off + ln and end > off:
            hits.append(pos)
            if mode == "eio":
                raise OSError(errno.EIO, "Input/output error (injected by the RED harness)")
        return fh.read(n)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_fh"), name)

    def __iter__(self):
        return iter(object.__getattribute__(self, "_fh"))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return object.__getattribute__(self, "_fh").__exit__(*exc)


def wrapped_open(file, *a, **k):
    fh = real_open(file, *a, **k)
    m = a[0] if a else k.get("mode", "r")
    try:
        same = isinstance(file, str) and os.path.realpath(file) == img
    except Exception:
        same = False
    if same and "b" in m and not any(c in m for c in "wax+"):
        return Wrapped(fh)
    return fh


builtins.open = wrapped_open
sys.argv = [tool, img] + rest
sys.path.insert(0, os.path.dirname(os.path.abspath(tool)))
code = 0
try:
    runpy.run_path(tool, run_name="__main__")
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
finally:
    with real_open(rep, "w") as fh:
        json.dump({"rc": code, "hits": len(hits), "first": ["0x%x" % h for h in hits[:8]]}, fh)
sys.exit(code)
'''


def _decode(p):
    return (p.stdout or b"").decode("utf-8", "replace") + "\n" + (p.stderr or b"").decode("utf-8", "replace")


def _run(tool, image, args, harness=None):
    """-> (rc, stdout+stderr, hits). `harness` = (mode, offset, length) runs the CLI under the read harness."""
    prog = FOREFST if tool == "forefst" else REFSANALYSIS
    os.makedirs(SCRATCH, exist_ok=True)
    rep = None
    if harness is None:
        cmd = [sys.executable, "-B", prog, image] + list(args)
    else:
        mode, off, ln = harness
        fd, rep = tempfile.mkstemp(prefix="harness_", suffix=".json", dir=SCRATCH)
        os.close(fd)
        cmd = [sys.executable, "-B", "-c", _HARNESS, prog, image, mode, "%d" % off, "%d" % ln, rep] + list(args)
    try:
        try:
            p = UW.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT, cwd=SCRATCH)
        except subprocess.TimeoutExpired:
            raise RedFixtureError("timeout after %ds: %s %s" % (TIMEOUT, os.path.basename(prog), " ".join(args)))
        text = _decode(p)
        if "Traceback (most recent call last)" in text:
            raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + text[-3000:])
        hits = None
        if rep is not None:
            try:
                with open(rep) as fh:
                    hits = json.load(fh)["hits"]
            except (OSError, ValueError, KeyError):
                raise RedFixtureError("the read harness wrote no report:\n" + text[-2000:])
        return p.returncode, text, hits
    finally:
        if rep is not None and os.path.exists(rep):
            os.unlink(rep)


_RUNS = {}


def _run_cached(tool, image, args):
    """An undamaged ORIGINAL image, read-only: the same run is never repeated in one session."""
    key = (tool, image, tuple(args))
    if key not in _RUNS:
        _RUNS[key] = _run(tool, image, args)
    return _RUNS[key]


# ─── detectors (each can emit its counterexample: see test_red_detectors_*) ──────────────────────────────────

_MISMATCH = re.compile(r"CHECKSUM MISMATCH|Mismatched:\s+[1-9]|mismatch:\s+\d+\s*/\s*[1-9]")
_QUALIFIED = re.compile(r"(?i)(\bonly\b|outside|not (verified|covered|checked)|coverage|--fullchecksums|\bexcept"
                        r"|excluding)")


def _clean_claims(text):
    """Lines claiming "no tampering" without saying what they cover (1.13.1: "VERDICT: all 15 checksummed pages
    VERIFIED — no tampering/corruption")."""
    return [l.strip() for l in text.splitlines() if re.search(r"(?i)no tampering", l) and not _QUALIFIED.search(l)]


_N_OF_M = re.compile(r"(\d[\d,]*)\s+of\s+(\d[\d,]*)")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_COV_SUBJECT = re.compile(r"(?i)\b(pages?|clusters?|blocks?|bytes)\b")
_COV_VERB = re.compile(r"(?i)(scan|coverage|covered|\bread\b|examined|checked)")


def _coverage_lines(text):
    return [l.strip() for l in text.splitlines()
            if _COV_SUBJECT.search(l) and _COV_VERB.search(l) and (_N_OF_M.search(l) or _PCT.search(l))]


def _coverage_below_full(text):
    for l in _coverage_lines(text):
        for a, b in _N_OF_M.findall(l):
            a, b = int(a.replace(",", "")), int(b.replace(",", ""))
            if 0 <= a < b:
                return True
        for p in _PCT.findall(l):
            if float(p) < 100.0:
                return True
    return False


_FOOTER_HINT = "stops the orphan scan early"      # `deleted`'s static footer: "... the run is then INCOMPLETE"


def _incomplete_lines(text):
    return [l.strip() for l in text.splitlines() if re.search(r"(?i)\bincomplete\b", l) and _FOOTER_HINT not in l]


_CT_WARN = re.compile(r"(?i)(inconsisten|overlap|collid|collision|same (physical )?(cluster|range|location|address"
                      r"|start|lcn)|both map|mapped (twice|more than once)|non-?injective|not injective|conflict)")


def _ct_warnings(text):
    return [l.strip() for l in text.splitlines() if re.search(r"(?i)container", l) and _CT_WARN.search(l)]


def _page_alarms(text):
    return [l.strip() for l in text.splitlines()
            if re.search(r"(?i)(did not match|does not match|mismatch|altered)", l)
            and re.search(r"(?i)(page|digest|checksum)", l)]


def _states_resigned_limit(text):
    """True when `text` says a Container Table rewritten with re-signed/recomputed digests cannot be detected."""
    t = re.sub(r"\s+", " ", text)
    for m in re.finditer(r"(?i)re-?sign|re-?comput|recomput", t):
        w = t[max(0, m.start() - 400):m.end() + 400]
        if re.search(r"(?i)container", w) and re.search(
                r"(?i)(cannot|can ?not|not) (be )?detect|undetectable|not detectable", w):
            return True
    return False


# ═══ unit level: the instruments themselves (no image) ═══════════════════════════════════════════════════════

def test_red_harness_injects_eio_and_counts_reads(tmp_path):
    """The read harness raises EIO exactly on reads overlapping its region, counts them, and keeps the tool's own
    exit code -- in trace mode it changes nothing."""
    data = tmp_path / "vol.bin"
    data.write_bytes(bytes(range(256)) * 256)                        # 64 KiB
    tool = tmp_path / "tool.py"
    tool.write_text(
        "import sys\n"
        "if __name__ == '__main__':\n"
        "    out = []\n"
        "    with open(sys.argv[1], 'rb') as fh:\n"
        "        for off in (0, 8192, 16384):\n"
        "            fh.seek(off)\n"
        "            try:\n"
        "                out.append('%d:%d' % (off, len(fh.read(4096))))\n"
        "            except OSError as e:\n"
        "                out.append('%d:EIO%d' % (off, e.errno))\n"
        "    print(' '.join(out))\n"
        "    sys.exit(3)\n")
    import errno
    rep = str(tmp_path / "rep.json")
    for mode, want in (("eio", "0:4096 8192:EIO%d 16384:4096" % errno.EIO), ("trace", "0:4096 8192:4096 16384:4096")):
        p = subprocess.run([sys.executable, "-B", "-c", _HARNESS, str(tool), str(data), mode, "10000", "1", rep],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        assert p.returncode == 3, _decode(p)
        assert p.stdout.decode().split() == want.split(), (mode, _decode(p))
        with open(rep) as fh:
            assert json.load(fh)["hits"] == 1, mode


def test_red_crc64_is_independent_of_the_tool_and_agrees_with_it():
    for data in (b"", b"123456789", bytes(range(256)) * 64, make_msb_page([(b"K" * 8, b"V" * 40)])):
        assert _crc64(data) == F.refs_crc64(data)
    assert _crc64(b"123456789") == 0xAE8B14860A799888                 # CRC-64/NVME check value


def test_red_unused_offset_lies_outside_every_part_of_the_node():
    page = make_msb_page([(b"K" * 8, b"V" * 40)] * 3, cluster_size=4 * 4096)
    off = _unused_offset(page)
    assert off is not None
    thoff = 0x50 + F.le32(page, 0x50)
    inner, rows = _node(page)
    assert inner is False and len(rows) == 3
    assert off >= thoff + 40
    for ro, ko, kl, vo, vl, _k, _v in rows:
        assert not (ro <= off < ro + max(16, ko + kl, vo + vl))
    flipped = bytearray(page)
    flipped[off] ^= 0x01
    flipped = bytes(flipped)
    assert _crc64(flipped) != _crc64(page)                            # the digest sees the flip ...
    assert F._walk(flipped, None, 0, 4096, None, 1) == F._walk(page, None, 0, 4096, None, 1)   # ... no reader does
    # a page whose last row runs to the very end: the flip goes into the highest GAP, never into a row
    full = bytearray(page)
    last = max(r[0] for r in rows)
    struct.pack_into("<I", full, last, len(full) - last)             # that row's size field reaches the page end
    off2 = _unused_offset(bytes(full))
    assert off2 is not None and thoff + 40 <= off2 < last
    for ro, ko, kl, vo, vl, _k, _v in rows:
        assert not (ro <= off2 < ro + max(16, ko + kl, vo + vl))
    # every row's size reaching the page end: the only unused bytes left lie between the key index and the first
    # row, and that is where the flip goes -- never into a row
    solid = bytearray(page)
    for ro, _ko, _kl, _vo, _vl, _k, _v in rows:
        struct.pack_into("<I", solid, ro, len(solid) - ro)
    off3 = _unused_offset(bytes(solid))
    assert off3 is not None and thoff + 40 <= off3 < min(r[0] for r in rows)


def test_red_refs_parsers_find_the_child_references():
    """The two child-reference parsers read the frames the tool's walkers read (E86 extent node, E73 index)."""
    ref = struct.pack("<4Q", 0x1000, 0x1001, 0x1002, 0x1003) + b"\0" * 4 + struct.pack("<I", 8) \
        + struct.pack("<Q", 0x1122334455667788)
    assert len(ref) == 0x30 and _ref_digest(ref) == (8, struct.pack("<Q", 0x1122334455667788))
    # E86: an extent INDEX node at value+0x88
    n = 0x88
    buf = bytearray(n + 0x200)
    struct.pack_into("<I", buf, n, 0x28)
    buf[n + 0x0C] = 1                                               # level 1: an index node
    struct.pack_into("<I6H", buf, n + 0x28, 0x40, 0x10, 0, 0, 0x10, 0x30, 0)
    buf[n + 0x38:n + 0x68] = ref
    struct.pack_into("<HH", buf, n + 0x80, 0x28, 0xFFFF)
    struct.pack_into("<I", buf, n + 0x10, 0x80)
    struct.pack_into("<I", buf, n + 0x14, 1)
    struct.pack_into("<I", buf, n + 0x20, 0x84)
    assert F._extent_node_rows(bytes(buf), n)[0] == 1
    assert _extent_index_refs(bytes(buf), n) == [ref]
    buf[n + 0x0C] = 0
    assert _extent_index_refs(bytes(buf), n) == []                  # a leaf holds extents, not references
    # E73: an embedded attribute INDEX node at value+base
    base = 0x40
    vd = bytearray(0x200)
    struct.pack_into("<I", vd, 0, base)
    vd[base + 0x0C], vd[base + 0x0D] = 1, 1
    struct.pack_into("<I", vd, base + 0x10, 0x80)
    struct.pack_into("<I", vd, base + 0x20, 0x84)
    struct.pack_into("<HH", vd, base + 0x80, 0x28, 0xFFFF)
    struct.pack_into("<I6H", vd, base + 0x28, 0x40, 0x10, 0, 0, 0x10, 0x30, 0)
    vd[base + 0x38:base + 0x68] = ref
    assert _embedded_index_refs(bytes(vd), base) == [ref]


def test_red_detectors_can_emit_their_counterexamples():
    verdict_1131 = "  VERDICT: all 15 checksummed pages VERIFIED \u2014 no tampering/corruption"   # A0.integrity.out:45
    assert _clean_claims(verdict_1131) == [verdict_1131.strip()]
    assert not _clean_claims("  VERDICT: no tampering in the 15 pages checked; child pages are outside this "
                             "coverage (run --fullchecksums)")
    full = "  Orphan-page scan: scanned 520,192 of 520,192 clusters (100% of the volume)"         # fd:12166
    assert _coverage_lines(full) and not _coverage_below_full(full)
    assert _coverage_below_full("  Orphan-page scan: read 516,096 of 520,192 clusters (99.21%) -- INCOMPLETE")
    assert _coverage_below_full("  Live-page slack: 58 of 59 pages read -- INCOMPLETE: 1 page unreadable")
    assert not _coverage_below_full("  DELETED files: 3 of 5 are INLINE with full content recoverable; 2 are "
                                    "extent-backed (carve-able with --carve).")
    assert not _coverage_below_full("  Scanned 59 live pages (orphan-page scan skipped \u2014 add --full to also "
                                    "scan the freed pages of older deletions) with recoverable slack rows")
    footer = ("  --max-scan N stops the orphan scan early (faster, but the run is then INCOMPLETE); `help deleted` "
              "lists what each option costs.")                                           # fd:14431, every run
    assert not _incomplete_lines(footer)
    assert _incomplete_lines("  WARNING: 4,096 clusters could not be read; this run is INCOMPLETE")
    assert _ct_warnings("[forefst] WARNING: Container Table: containers 3 and 18 map to the same clusters")
    assert not _ct_warnings("  Container Table copy 2        63 rows")
    assert _MISMATCH.search("  CRC64  match / mismatch: 14 / 1") and not _MISMATCH.search(
        "  CRC64  match / mismatch: 15 / 0")
    assert _page_alarms("[forefst] WARNING: 1 page(s) DID NOT match their parent's digest")
    assert not _page_alarms("[forefst] --verify-pages: 12/12 metadata page(s) matched the digest in their parent "
                            "reference.")
    assert _states_resigned_limit("The Container Table is not checked ... A table rewritten with re-computed "
                                  "checksums cannot be detected from the volume alone.")      # forefst.md:74-75
    assert not _states_resigned_limit("Container Table rows map a container to its physical clusters.")


# ═══ A5 — `--checksums` coverage: the N4 8-page experiment on 1.13.1 ══════════════════════════════════════════

_N4_SLOTS = ("S0", "P0", "P1", "C0", "C1", "C2", "C3", "C4")
_S_PREFERENCE = (4, 3, 6, 9, 10, 11, 1, 2)   # Parent-Child, Schema, Block RefCount, ...; never the Object Table (0)
                                             # or the Container Table (7, 8, 12), which bootstrap itself reads


def _spread(items, k):
    if len(items) < k:
        return None
    if k == 1:
        return [items[0]]
    return [items[i * (len(items) - 1) // (k - 1)] for i in range(k)]


@functools.lru_cache(maxsize=None)
def _n4_pages(image):
    """N4's 8 pages, rebuilt by rule (N4 recorded no LCNs): {slot: {cls, what, head, abs, check}}. Every page is
    LIVE and its flip is digest-only. `check` = (dlen, digest, plcns) of the digest the parent recorded, verified
    here with this module's CRC64 -- the independent half of the "detectable in principle" precondition."""
    f, ps, cs, tr, roots, obj_map, _vmaj, _vmin, _chkp = F.bootstrap(image, None)
    try:
        sys_heads = set()
        for idx, rv in enumerate(roots):
            if rv:
                ptc = []
                F._walk_btree_pages(f, ps, cs, None if idx in F._CT_ROOT_INDICES else tr, rv, set(), ptc)
                sys_heads.update(h for h, _pl in ptc)
        ot = F._select_ot_root(f, ps, cs, tr, roots)
        rows = [(kd, vd) for kd, vd in F.walk_bplus(f, ps, cs, tr, ot) if len(kd) >= 16 and len(vd) >= 0x50]
        last = {}
        for i, (kd, _vd) in enumerate(rows):
            last[F.le64(kd, 8)] = i                    # the row the reader uses: the LAST per object
        objs = []
        for i, (kd, vd) in enumerate(rows):
            oid = F.le64(kd, 8)
            if last[oid] != i:
                continue
            slots = [F.le64(vd, 0x20 + 8 * j) for j in range(4)]
            pl = _plcns(slots, tr)
            dg = _ot_digest(vd)
            page = F._read_full_page(f, ps, cs, slots, tr) if pl else None
            if page and page[:4] == b"MSB+" and dg and _matches(dg[0], dg[1], page):
                objs.append((oid, pl, page, dg))
        root_heads = {pl[0] for _oid, pl, _pg, _dg in objs}
        P, C, seen = [], [], set()
        for oid, pl, page, dg in objs:
            if pl[0] in sys_heads:
                continue
            at = _flip_at(ps, cs, pl, page)
            if at is not None:
                P.append({"cls": "P", "what": "root page of object 0x%x" % oid, "head": pl[0], "abs": at,
                          "check": (dg[0], dg[1], tuple(pl))})
            stack = [(page, 0)]
            while stack:
                pg, depth = stack.pop()
                inner, nrows = _node(pg)
                if not inner or depth >= 8:
                    continue
                for _ro, _ko, _kl, _vo, _vl, _kd, vd in nrows:
                    rd = _ref_digest(vd)
                    cslots = [F.le64(vd, 8 * j) for j in range(4)] if len(vd) >= 32 else []
                    cpl = _plcns(cslots, tr)
                    if not cpl or cpl[0] in seen:
                        continue
                    seen.add(cpl[0])
                    child = F._read_full_page(f, ps, cs, cslots, tr)
                    if not child or child[:4] != b"MSB+":
                        continue
                    stack.append((child, depth + 1))
                    if cpl[0] in sys_heads or cpl[0] in root_heads or not rd or not _matches(rd[0], rd[1], child):
                        continue
                    at = _flip_at(ps, cs, cpl, child)
                    if at is not None:
                        C.append({"cls": "C", "what": "child page (depth %d) of object 0x%x" % (depth + 1, oid),
                                  "head": cpl[0], "abs": at, "check": (rd[0], rd[1], tuple(cpl))})
        S = None
        for idx in _S_PREFERENCE:
            rv = roots[idx] if idx < len(roots) else None
            if not rv:
                continue
            use_tr = None if idx in F._CT_ROOT_INDICES else tr
            pl = _plcns(rv, use_tr)
            page = F._read_full_page(f, ps, cs, rv, use_tr) if pl else None
            if not page or page[:4] != b"MSB+" or pl[0] in root_heads:
                continue
            at = _flip_at(ps, cs, pl, page)
            if at is not None:
                label = F._ROOT_LABELS[idx] if idx < len(F._ROOT_LABELS) else "?"
                S = {"cls": "S", "what": "root page of system table %d (%s)" % (idx, label), "head": pl[0],
                     "abs": at, "check": None}
                break
    finally:
        f.close()
    out = {"_counts": "system page %s, object roots %d, object child pages %d" % (bool(S), len(P), len(C)),
           "_ps": ps, "_cs": cs}
    if S:
        out["S0"] = S
    ps_ = _spread(sorted(P, key=lambda x: x["head"]), 2)
    if ps_:
        out["P0"], out["P1"] = ps_
    cs_ = _spread(sorted(C, key=lambda x: x["head"]), 5)
    if cs_:
        for i, c in enumerate(cs_):
            out["C%d" % i] = c
    return out


def _a5_param(slot):
    # RED 1.13.2 A5: green with step C4 (decision 22's O1; the strict xfail mark of the C slots removed)
    return pytest.param(slot, id=slot)


def _verdicts(out):
    """The VERDICT lines of the page-checksum section."""
    return [l.strip() for l in out.splitlines() if l.strip().startswith("VERDICT:") and "checksummed pages" in l]


def test_a5_control_the_undamaged_volume_exits_0():
    img = _need(BASE_A)
    for args in (("integrity", "--checksums"), ("integrity", "--fullchecksums")):
        rc, out, _ = _run_cached("forefst", img, args)
        assert rc == 0 and not _MISMATCH.search(out), "%s on the undamaged %s: rc %d" % (" ".join(args), BASE_A, rc)


@pytest.mark.parametrize("slot", [_a5_param(s) for s in _N4_SLOTS])
def test_a5_n4_page_edit_exits_2_or_the_verdict_names_its_coverage(slot):
    img = _need(BASE_A)
    pages = _n4_pages(img)
    _fx(slot in pages, "the N4 rebuild could not fill %s on %s (%s)" % (slot, BASE_A, pages["_counts"]))
    pg = pages[slot]
    path = _COPY.get(("a5", slot), img, [(pg["abs"], 0x01)])
    if pg["check"]:
        dlen, digest, plcns = pg["check"]
        _fx(not _matches(dlen, digest, _read_page(path, pages["_ps"], pages["_cs"], plcns)),
            "%s: the flip at 0x%x left the page matching its parent's digest" % (slot, pg["abs"]))
    rc_full, out_full, _ = _run("forefst", path, ["integrity", "--fullchecksums"])
    _fx(rc_full == 2 and _MISMATCH.search(out_full),
        "%s (%s): --fullchecksums does not see the edit (rc %d), so it is not a page edit a digest check can see"
        % (slot, pg["what"], rc_full))
    rc, out, _ = _run("forefst", path, ["integrity", "--checksums"])
    claims = _clean_claims(out)
    print("A5 N4 %s | %s | PLCN 0x%x | flip 0x%x | --checksums rc %d, claims %r | --fullchecksums rc %d"
          % (slot, pg["what"], pg["head"], pg["abs"], rc, claims, rc_full))
    # O1 (decision 22; tightened before the fix, RED_a_coverage caveat 1): the edit is detected (exit 2, a mismatch), or
    # the VERDICT line ITSELF names its coverage and points to --fullchecksums -- the Coverage line two lines above
    # does not count -- and no line says "no tampering" without its scope
    v = _verdicts(out)
    assert (rc == 2 and _MISMATCH.search(out)) or (
        not claims and v and all("system root tables" in x and "not covered" in x and "--fullchecksums" in x
                                 for x in v)), (
        "%s (%s, PLCN 0x%x, byte 0x%x flipped): `integrity --checksums` exits %d and says %r; verdict %r"
        % (slot, pg["what"], pg["head"], pg["abs"], rc, claims, v))


# ═══ A6 — extent-index and embedded-index child pages ════════════════════════════════════════════════════════

_A6_IMAGES = (MFTECMD, "win1122h2test.raw")     # the plan names the first; the second is E73's witness volume


def _a6_scan(img):
    f, ps, cs, tr, roots, obj_map, _vmaj, _vmin, _chkp = F.bootstrap(img, None)
    try:
        walk = {h for h, _pl in _integrity_walk(f, ps, cs, tr, roots, obj_map)}
        ctx = (f, ps, cs, tr)
        cands = {"extent": [], "embedded": []}
        seen = set()
        skips = collections.Counter()   # N204: what the scan could not read, by stage and exception type

        def consider(kind, oid, name, ref):
            rd = _ref_digest(ref)
            slots = [F.le64(ref, 8 * j) for j in range(4)]
            try:
                pl = _plcns(slots, tr)
            except Exception as e:
                skips[("child-ref translate", type(e).__name__)] += 1
                return
            if not rd or not pl or (kind, pl[0]) in seen:
                return
            seen.add((kind, pl[0]))
            if pl[0] in walk:
                return                     # a page the integrity walk already reaches is not this defect
            page = F._read_full_page(f, ps, cs, slots, tr)
            if not page or page[:4] != b"MSB+" or not _matches(rd[0], rd[1], page):
                return
            at = _flip_at(ps, cs, pl, page)
            if at is not None:
                cands[kind].append({"kind": kind, "image": img, "owner": oid, "name": name, "head": pl[0],
                                    "plcns": tuple(pl), "abs": at, "check": rd, "ps": ps, "cs": cs})

        for oid in sorted(obj_map):
            try:
                rows = F.walk_bplus(f, ps, cs, tr, obj_map[oid])
            except Exception as e:
                skips[("table walk", type(e).__name__)] += 1
                continue
            for kd, vd in rows:
                if len(kd) < 4 or F.le16(kd, 0) not in (0x30, 0x40) or len(vd) < 0xC0:
                    continue
                name = (kd[4:].decode("utf-16-le", "replace").rstrip("\x00") if F.le16(kd, 0) == 0x30
                        else "(type-0x40 record)")
                base = F.le32(vd, 0)
                if 0x28 <= base < len(vd) - 0x28 and base + 0x24 <= len(vd) and vd[base + 0x0D] & 0x01:
                    for ref in _embedded_index_refs(vd, base):
                        consider("embedded", oid, name, ref)
                try:
                    attrs = F.parse_resident_btree_rows(vd, ctx)
                except Exception as e:
                    skips[("attribute rows", type(e).__name__)] += 1
                    attrs = []
                for akd, aval in attrs:
                    if _is_current_data(akd, aval):
                        for ref in _extent_index_refs(aval, 0x88):
                            consider("extent", oid, name, ref)
    finally:
        f.close()
    return {k: sorted(v, key=lambda c: c["head"])[0] for k, v in cands.items() if v}, dict(skips)


@functools.lru_cache(maxsize=None)
def _a6_targets():
    found, notes = {}, []
    for name in _A6_IMAGES:
        img = _corpus_image(name)
        if img is None:
            notes.append("%s absent" % name)
            continue
        got, skips = _a6_scan(img)
        notes.append("%s: %s%s" % (name, sorted(got) or "none",
                                   (" (unreadable: %s)" % ", ".join("%s %s x%d" % (st, ex, n) for (st, ex), n
                                                                   in sorted(skips.items()))) if skips else ""))
        for kind, t in got.items():
            found.setdefault(kind, t)
        if len(found) == 2:
            break
    return found, tuple(notes)


def _a6_target(kind):
    if _corpus_image(MFTECMD) is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % MFTECMD)
    found, notes = _a6_targets()
    _fx(kind in found, "no %s child page outside the integrity walk with a verifying parent digest: %s"
        % (kind, "; ".join(notes)))
    t = found[kind]
    # the commands that read the page under --verify-pages, first one that actually reads it wins
    probes = [["dataruns", "--oid", "0x%x" % t["owner"], "--depth", "0"]]
    if kind == "embedded":
        probes.append(["files", "--csv"])
    return t, probes


def _read_by(image, t, probes):
    """Run the probes under the trace harness until one reads the target byte: (args, rc, text, hits)."""
    res = None
    for args in probes:
        a = list(args) + ["--verify-pages"]
        rc, text, hits = _run("forefst", image, a, harness=("trace", t["abs"], 1))
        res = (a, rc, text, hits)
        if hits:
            break
    return res


@pytest.mark.parametrize("kind", ["extent", "embedded"])
def test_a6_control_the_undamaged_child_page_is_read_and_verifies(kind):
    t, probes = _a6_target(kind)
    rc, out, _ = _run_cached("forefst", t["image"], ("integrity", "--fullchecksums"))
    assert rc == 0 and not _MISMATCH.search(out), "--fullchecksums on the undamaged %s: rc %d" % (t["image"], rc)
    args, rc, out, hits = _read_by(t["image"], t, probes)
    _fx(hits, "%s child page PLCN 0x%x (object 0x%x, %s): none of %s reads it"
        % (kind, t["head"], t["owner"], t["name"], probes))
    assert rc == 0 and not _page_alarms(out), "%s on the undamaged volume: rc %d, %r" % (" ".join(args), rc,
                                                                                        _page_alarms(out))


def _a6_case(kind, probe):
    t, probes = _a6_target(kind)
    path = _COPY.get(("a6", kind), t["image"], [(t["abs"], 0x01)])
    dlen, digest = t["check"]
    _fx(not _matches(dlen, digest, _read_page(path, t["ps"], t["cs"], t["plcns"])),
        "the flip at 0x%x left the %s child page matching its parent's digest" % (t["abs"], kind))
    where = "%s child page PLCN 0x%x (object 0x%x, %s; byte 0x%x flipped) on %s" % (
        kind, t["head"], t["owner"], t["name"], t["abs"], os.path.basename(t["image"]))
    if probe == "fullchecksums":
        rc, out, _ = _run("forefst", path, ["integrity", "--fullchecksums"])
        claims = _clean_claims(out)
        print("A6 %s | %s | integrity --fullchecksums rc %d, claims %r" % (kind, where, rc, claims))
        assert rc == 2 and not claims, "%s: `integrity --fullchecksums` exits %d and says %r" % (where, rc, claims)
    else:
        args, rc, out, hits = _read_by(path, t, probes)
        _fx(hits, "%s: no probe read the damaged page (%s)" % (where, probes))
        alarms = _page_alarms(out)
        print("A6 %s | %s | %s rc %d, alarms %r" % (kind, where, " ".join(args), rc, alarms))
        assert rc == 2 and alarms, "%s: `%s` read the page (%d reads) and exits %d, alarms %r" % (
            where, " ".join(args), hits, rc, alarms)


# RED 1.13.2 A6: green with step C4 (the strict xfail marks removed)
_A6_PROBES = [pytest.param("fullchecksums", id="fullchecksums"), pytest.param("verify-pages", id="verify-pages")]


@pytest.mark.parametrize("probe", _A6_PROBES)
def test_a6_extent_index_child_flip_is_detected(probe):
    _a6_case("extent", probe)


@pytest.mark.parametrize("probe", _A6_PROBES)
def test_a6_embedded_index_child_flip_is_detected(probe):
    _a6_case("embedded", probe)


# ═══ A8 — a read error inside the scan range ═════════════════════════════════════════════════════════════════

def _largest_hole(path, lo, hi):
    fd = os.open(path, os.O_RDONLY)
    best = None
    try:
        pos = lo
        while pos < hi:
            try:
                h = os.lseek(fd, pos, os.SEEK_HOLE)
            except OSError:
                break
            if h >= hi:
                break
            try:
                d = min(os.lseek(fd, h, os.SEEK_DATA), hi)
            except OSError:
                d = hi
            if best is None or d - h > best[1] - best[0]:
                best = (h, d)
            pos = max(d, h + 1)
    finally:
        os.close(fd)
    return best


@functools.lru_cache(maxsize=None)
def _a8_faults(image):
    """Two regions. `live` = the head cluster of a system table's root page (Parent-Child first), which in
    `deleted` only the slack scan reads: its page walk (`_walk_btree_pages`, which records a skip) and then its
    live-page loop (fd:12437, which does not). `orphan` = one cluster in the middle of the largest image hole
    inside the volume, which only the orphan-page scans read (fd:12130). A control below checks each claim."""
    f, ps, cs, tr, roots, obj_map, _vmaj, _vmin, _chkp = F.bootstrap(image, None)
    try:
        size = f.seek(0, 2)
        vol = (size - ps) // cs
        live = None
        for idx in _S_PREFERENCE:
            rv = roots[idx] if idx < len(roots) else None
            if not rv:
                continue
            use_tr = None if idx in F._CT_ROOT_INDICES else tr
            pl = _plcns(rv, use_tr)
            page = F._read_full_page(f, ps, cs, rv, use_tr) if pl else None
            if page and page[:4] == b"MSB+":
                live = {"off": ps + pl[0] * cs, "len": cs, "what": "root page of system table %d, PLCN 0x%x"
                        % (idx, pl[0])}
                break
    finally:
        f.close()
    hole = _largest_hole(image, ps, ps + vol * cs)
    orphan = None
    if hole and hole[1] - hole[0] >= 64 * cs:
        off = ps + (((hole[0] + hole[1]) // 2 - ps) // cs) * cs
        orphan = {"off": off, "len": cs, "what": "cluster 0x%x, inside the image hole 0x%x-0x%x"
                  % ((off - ps) // cs, hole[0], hole[1])}
    return {"live": live, "orphan": orphan}


_A8_PATHS = (("deleted-default", "live", ("deleted",)),
             ("export-deleted", "live", ("export", "deleted", "{OUT}")),
             ("deleted-full", "orphan", ("deleted", "--full")),
             ("deleted-scan-pages", "orphan", ("deleted", "--scan-pages")))


def _a8_run(img, where, args):
    fault = _a8_faults(img)[where]
    _fx(fault, "no %s fault region on %s" % (where, BASE_A))
    out_dir = None
    if "{OUT}" in args:
        os.makedirs(SCRATCH, exist_ok=True)
        out_dir = tempfile.mkdtemp(prefix="a8_export_", dir=SCRATCH)
        args = tuple(out_dir if a == "{OUT}" else a for a in args)
    try:
        rc, text, hits = _run("forefst", img, args, harness=("eio", fault["off"], fault["len"]))
        if out_dir and os.path.exists(os.path.join(out_dir, "recovery_log.txt")):
            with open(os.path.join(out_dir, "recovery_log.txt"), encoding="utf-8", errors="replace") as fh:
                text += "\n" + fh.read()
    finally:
        if out_dir and os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
    return rc, text, hits, fault


def test_a8_control_the_clean_scans_exit_0_and_claim_full_coverage():
    img = _need(BASE_A)
    for args in (("deleted",), ("deleted", "--full"), ("deleted", "--scan-pages")):
        rc, text, _ = _run_cached("forefst", img, args)
        assert rc == 0, "%s on the undamaged %s: rc %d" % (" ".join(args), BASE_A, rc)
        assert not _incomplete_lines(text) and not _coverage_below_full(text), (args, _incomplete_lines(text),
                                                                                 _coverage_lines(text))
        if len(args) > 1:
            assert _coverage_lines(text), "%s printed no coverage line the detector can read" % " ".join(args)


# N634 (1.14.0 RC3): since D (N622) every command checks each checkpoint root's page when it starts, so the `live`
# region (a system table's root page) is read once more than the scan reads it: by that root check, which names the
# root it cannot read and exits 2. The control states that baseline exactly; the live paths below must read the
# region beyond it (the scan under test meets the error itself) and still say INCOMPLETE with coverage below full.
_A8_ROOT_CHECK_READS = {"live": 1, "orphan": 0}
_A8_ROOT_CHECK_SAID = re.compile(r"the root page of checkpoint root \d+ \([^)]*\) cannot be read")


def test_a8_control_each_fault_region_is_read_only_by_the_scan_under_test():
    img = _need(BASE_A)
    for where, args in (("orphan", ("deleted",)), ("live", ("deleted", "--no-slack"))):
        rc, text, hits, fault = _a8_run(img, where, args)
        base = _A8_ROOT_CHECK_READS[where]
        assert hits == base, "%s (%s) was read %d time(s) by `%s`, which runs no scan of it (expected %d: %s)" % (
            where, fault["what"], hits, " ".join(args), base, "the root check" if base else "none")
        if base:
            assert _A8_ROOT_CHECK_SAID.search(text) and rc == 2, (
                "`%s` with the %s fault: the root check's read is not stated (rc %d)" % (" ".join(args), where, rc))
        else:
            assert rc == 0, "`%s` with the %s fault: rc %d" % (" ".join(args), where, rc)


@pytest.mark.parametrize("where,args", [pytest.param(w, a, id=i) for i, w, a in _A8_PATHS])   # A8: green in C3
def test_a8_unreadable_region_is_reported_on_every_scan_path(where, args):
    img = _need(BASE_A)
    rc, text, hits, fault = _a8_run(img, where, args)
    _fx(hits > _A8_ROOT_CHECK_READS[where], "the injected read error (%s) was never hit by `%s` beyond the root "
        "check's %d read(s)" % (fault["what"], " ".join(args), _A8_ROOT_CHECK_READS[where]))
    problems = []
    if rc != 2:
        problems.append("exit %d, not 2" % rc)
    if not _incomplete_lines(text):
        problems.append("no INCOMPLETE statement")
    if not _coverage_below_full(text):
        problems.append("no coverage figure below 100%% (coverage lines: %r)" % _coverage_lines(text)[:3])
    print("A8 %s | %s | %d failed read(s) | rc %d | %s" % (" ".join(args), fault["what"], hits, rc,
                                                          "; ".join(problems) or "accepted"))
    assert not problems, "`%s` with an unreadable %s (%d reads failed): %s" % (
        " ".join(args), fault["what"], hits, "; ".join(problems))


# ─── A8, unit level: the live-slack loop's own drop (added 2026-09-27) ───────────────────────────────────────
# On the image paths above the fault is persistent, so `_walk_btree_pages` reads the page FIRST and records the
# skip; that record masks the live-slack loop's own silent drop (fd:12430-12441: `except (OSError,
# OverflowError): ok = False; break`, then `if ok:` -- no note, no register). Here the page reads cleanly for the
# walk and raises EIO for every later reader, so only the loop meets the error. The unit is `_slack_recover` on
# the default `deleted` path (scan_orphans=False, as `deleted` and `export deleted` call it). If a fix records the
# loss one level up (in `cmd_deleted`, from a stats counter) instead of in the loop, re-point this node at the
# caller; if a fix stops re-reading the page at all, the fixture check below raises RedFixtureError, loudly.

_A8U_CS = 4096                    # 4 KiB clusters: a metadata page is 4 slot clusters (16 KiB)
_A8U_SLOTS = 4
_A8U_PS = 0
_A8U_HEAD = 0x1400                # the image nodes' live fault: head cluster of system table 4's root page
_A8U_OWNER = 0x600                # page+0x48, the owning table: the root directory
_A8U_GONE = "deleted_report.docx"  # the row in the page's slack (deleted: its key-index slot was removed)
_A8U_ERR = "Input/output error (injected by the A8 unit RED)"
_A8U_SAID = re.compile(r"(?i)(injected by the A8 unit RED|\b0x%x\b|\b%d\b|unread|could ?not (be )?read"
                       r"|cannot (be )?read|not (be(en)? )?read\b|failed to read|read error|\bincomplete\b)"
                       % (_A8U_HEAD, _A8U_HEAD))


def _a8u_page():
    """One 16 KiB MSB+ leaf page: a live row, and a deleted row whose key-index slot was removed (ReFS deletion,
    `CmsBPlusTable::DeleteFromIndex`) so its body stays in the page's slack."""
    def row(name, ct):
        v = bytearray(0x68)                                   # > 84 bytes: the resident form (_decode_dir_row_value)
        struct.pack_into("<QQQQ", v, 0x28, ct, ct, ct, ct)    # create/modify/change/access
        struct.pack_into("<I", v, 0x48, 0x20)                 # FILE_ATTRIBUTE_ARCHIVE
        return struct.pack("<HH", 0x30, 0) + name.encode("utf-16-le"), bytes(v)
    page = bytearray(make_msb_page([row("kept.txt", 133000000000000000), row(_A8U_GONE, 133100000000000000)],
                                   cluster_size=_A8U_CS * _A8U_SLOTS))
    thoff = 0x50 + F.le32(page, 0x50)
    tbl = list(struct.unpack_from("<10I", page, thoff))
    tbl[8] = tbl[4] + 4                                       # key index: the first row only
    struct.pack_into("<10I", page, thoff, *tbl)
    struct.pack_into("<Q", page, 0x48, _A8U_OWNER)
    # the page's own address (+0x20..+0x3F: the LCNs it was written for), as every page of a volume carries it: since
    # 1.14.0 (WC-5) `_walk_btree_pages` makes A9's test too, and a page recording no address is not the one asked for
    struct.pack_into("<%dQ" % _A8U_SLOTS, page, 0x20, *[_A8U_HEAD + i for i in range(_A8U_SLOTS)])
    page = bytes(page)
    rec = F._scan_page_slack(page, _A8U_HEAD, "live-slack")
    _fx([e["name"] for e in rec] == [_A8U_GONE], "the synthetic page's slack does not hold exactly the deleted "
                                                 "row: %r" % [e.get("name") for e in rec])
    return page


def _a8u_reader():
    """Who is reading, from forefst's frames on the call stack (however many helpers sit in between):
    "walk" while `_walk_btree_pages` runs (it is called from `_slack_recover`, so it is tested first),
    "slack-loop" while `_slack_recover` runs outside the walk (its live-page loop), else "other"."""
    names = set()
    fr = sys._getframe(1)
    while fr is not None:
        if fr.f_globals is vars(F):
            names.add(fr.f_code.co_name)
        fr = fr.f_back
    if "_walk_btree_pages" in names:
        return "walk"
    return "slack-loop" if "_slack_recover" in names else "other"


class _A8uVolume(object):
    """A read-only image holding one page at PLCN _A8U_HEAD (zeros elsewhere). Reads that overlap the page's head
    cluster succeed while `_walk_btree_pages` is on the stack; with `fail`, every other read of it raises EIO. So
    the walk reads the page cleanly and the next reader of it (the live-slack loop) meets the error."""

    def __init__(self, page, fail):
        self._off = _A8U_PS + _A8U_HEAD * _A8U_CS
        self._page = page
        self._size = self._off + len(page) + 16 * _A8U_CS
        self._pos = 0
        self.fail = fail
        self.order = []                 # _a8u_reader() of each read of the head cluster, in order
        self.failed_by = []             # _a8u_reader() of each read that raised EIO, in order

    def seek(self, off, whence=0):
        self._pos = off if whence == 0 else (self._pos + off if whence == 1 else self._size + off)
        return self._pos

    def tell(self):
        return self._pos

    def read(self, n=-1):
        pos = self._pos
        end = self._size if n is None or n < 0 else min(self._size, pos + n)
        if pos < self._off + _A8U_CS and end > self._off:
            who = _a8u_reader()
            self.order.append(who)
            if self.fail and who != "walk":
                self.failed_by.append(who)
                raise OSError(errno.EIO, _A8U_ERR)
        out = bytearray(max(0, end - pos))
        lo, hi = max(pos, self._off), min(end, self._off + len(self._page))
        if lo < hi:
            out[lo - pos:hi - pos] = self._page[lo - self._off:hi - self._off]
        self._pos = end
        return bytes(out)


def _a8u_rc_fn():
    """The single exit rule: `rc_escalate` once A11 lands, `_escalate_rc` on 1.13.1."""
    fn = getattr(F, "rc_escalate", None) or getattr(F, "_escalate_rc", None)
    _fx(callable(fn), "neither rc_escalate nor _escalate_rc exists in forefst.py")
    return fn


def _a8u_fresh(monkeypatch):
    """Fresh, empty values for every register the exit rule reads (taken from its own code, so a register a fix
    adds is included) and for the skip-note machinery; monkeypatch restores the module afterwards."""
    names = set(_a8u_rc_fn().__code__.co_names) | {
        "_SKIP_NOTES", "_SKIP_EXPECTED", "_SKIP_FINDING", "_SKIP_SUMMARY_DONE", "_FINDINGS", "_WALK_DAMAGE",
        "_WALK_DAMAGE_REPORTED", "_DEFERRALS"}
    for name in sorted(names):
        cur = vars(F).get(name)
        if isinstance(cur, (list, dict, set)):
            monkeypatch.setattr(F, name, type(cur)())


def _a8u_scan(monkeypatch, capsys, fail):
    """Run the default-path slack scan over the synthetic volume. -> dict of what it returned and said."""
    _a8u_fresh(monkeypatch)
    rc_fn = _a8u_rc_fn()
    _fx(rc_fn(0) == 0, "the exit registers are not clean before the scan")
    capsys.readouterr()
    vol = _A8uVolume(_a8u_page(), fail)
    roots = [None] * 5
    roots[4] = [_A8U_HEAD + i for i in range(_A8U_SLOTS)]     # tr=None: the slots are physical LCNs
    log, stats = [], {}
    try:
        entries = F._slack_recover(vol, _A8U_PS, _A8U_CS, None, roots, {}, None, log.append,
                                   scan_orphans=False, live_identity={}, stats=stats)
    except Exception as e:                                     # a crash is never the acceptance
        raise RedFixtureError("_slack_recover raised %s: %s" % (type(e).__name__, e))
    said = capsys.readouterr().err.splitlines()
    for name in ("_skip_summary", "_walk_damage_summary", "_defer_summary"):   # what the run prints at exit
        fn = getattr(F, name, None)
        if callable(fn):
            fn()
    said += capsys.readouterr().err.splitlines()
    lines = [l.strip() for l in said + log if l.strip()]
    return {"vol": vol, "entries": entries, "rc": rc_fn(0), "lines": lines, "log": log, "stats": stats,
            "named": [l for l in lines if _A8U_SAID.search(l) or _coverage_below_full(l)]}


def test_a8_control_live_slack_scan_with_no_read_error_records_nothing(monkeypatch, capsys):
    """No read fails: the walk reads the page, the live-slack loop reads it a SECOND time (the premise of the RED),
    recovers the deleted row from its slack, and nothing is recorded (exit rule 0, no line the RED's detector
    reads). Then the same instruments fire on what a recorded skip looks like, so the RED's zero can be a zero."""
    r = _a8u_scan(monkeypatch, capsys, fail=False)
    v = r["vol"]
    assert v.order[:1] == ["walk"] and "slack-loop" in v.order[1:] and not v.failed_by, \
        "reads of the page, in order: %r" % v.order
    assert [e["name"] for e in r["entries"]] == [_A8U_GONE], r["entries"]
    assert r["rc"] == 0 and not r["named"], (r["rc"], r["named"], r["lines"])
    # the instruments can emit their counterexample: a skip recorded by the tool's own machinery for this error
    _a8u_fresh(monkeypatch)
    capsys.readouterr()
    F._skip_note("_slack_recover", "a live page", OSError(errno.EIO, _A8U_ERR))
    note = [l.strip() for l in capsys.readouterr().err.splitlines() if l.strip()]
    assert _a8u_rc_fn()(0) == 2, "the exit rule does not see a recorded skip"
    assert [l for l in note if _A8U_SAID.search(l)], note
    assert _coverage_below_full("  Scanned 0 of 1 live pages with recoverable slack rows")
    assert not _coverage_below_full("  Scanned 1 of 1 live pages with recoverable slack rows")


def test_a8_live_slack_read_error_is_recorded_not_dropped(monkeypatch, capsys):
    r = _a8u_scan(monkeypatch, capsys, fail=True)
    v = r["vol"]
    _fx(v.order[:1] == ["walk"], "the page walk did not read the page first: %r" % v.order)
    _fx(v.failed_by[:1] == ["slack-loop"],
        "the first failed read of the page was not the live-slack loop's (reads, in order: %r; failed: %r); "
        "the RED's premise is gone" % (v.order, v.failed_by))
    problems = []
    if r["rc"] != 2:
        problems.append("the exit rule gives %d, not 2 (no register records the unread page)" % r["rc"])
    if not r["named"]:
        problems.append("nothing on stderr, in the log or in the end-of-run summaries names the unread page or "
                        "gives a coverage figure below 100%")
    print("A8 unit | live page PLCN 0x%x read by the walk, then %d read(s) raised EIO | rc %d | %d of 1 slack "
          "row(s) recovered | %s" % (_A8U_HEAD, len(v.failed_by), r["rc"], len(r["entries"]),
                                      "; ".join(problems) or "accepted"))
    assert not problems, "live page PLCN 0x%x read cleanly by the walk, then %d read(s) by the live-slack loop " \
                         "raised EIO: %s. Rows recovered: %r (the page's slack holds %r). Everything said: %r" % (
                             _A8U_HEAD, len(v.failed_by), "; ".join(problems),
                             [e.get("name") for e in r["entries"]], _A8U_GONE, r["lines"])


# ═══ A9 — Container-Table consistency ════════════════════════════════════════════════════════════════════════

def _ct_row_field(f, ps, cs, slots, cid, depth=0):
    """Absolute offset of container `cid`'s physical-start field (value[len-16], as `_parse_ct_page` reads it),
    following the table from its root; the LAST match wins, as in `_parse_ct_page`."""
    pl = [s for s in slots if s not in NULL]
    if not pl or depth > 8:
        return None
    page = b""
    for s in pl:
        f.seek(ps + s * cs)
        page += f.read(cs)
    inner, rows = _node(page)
    hit = None
    for ro, _ko, _kl, vo, vl, kd, vd in rows:
        if inner:
            if len(vd) >= 32:
                r = _ct_row_field(f, ps, cs, [F.le64(vd, 8 * j) for j in range(4)], cid, depth + 1)
                if r is not None:
                    hit = r
        elif len(kd) >= 8 and F.le64(kd, 0) == cid and len(vd) >= 0x98:
            off = ro + vo + vl - 16
            hit = ps + pl[off // cs] * cs + off % cs
    return hit


@functools.lru_cache(maxsize=None)
def _a9_recipe(image):
    """One byte of one Container-Table row that makes container A map onto container B's clusters (a
    non-injective table, K013's shape without re-signing). A holds no live metadata page, so nothing the
    structural walk reads moves: only a consistency check can see it. Prefers the audit's (3 -> 18)."""
    f, ps, cs, tr, roots, obj_map, _vmaj, _vmin, _chkp = F.bootstrap(image, None)
    try:
        m, cpc = dict(tr.map), tr.cpc
        live = sorted(p for _h, pl in _integrity_walk(f, ps, cs, tr, roots, obj_map) for p in pl)

        def holds_metadata(cid):
            i = bisect.bisect_left(live, m[cid])
            return i < len(live) and live[i] < m[cid] + cpc

        pairs = []
        for a in sorted(m):
            if holds_metadata(a):
                continue
            for b in sorted(m):
                x = m[a] ^ m[b]
                if a == b or not x:
                    continue
                k = (x.bit_length() - 1) // 8
                if x & ~(0xFF << (8 * k)):
                    continue
                pairs.append(((a, b) != (3, 18), a, b, k, (x >> (8 * k)) & 0xFF))
        if not pairs:
            return {"why": "no data-only container whose physical start differs from another's in one byte"}
        pairs.sort()
        _pref, a, b, k, xor = pairs[0]
        # CB-11 (1.14.0): the row is flipped in BOTH copies of the table (roots 7 and 8). The tool reads the copy
        # refs.sys reads: root 8 when root 7 fails its check, so a flip of root 7 alone is read past (the intact copy
        # is used and the map is not broken); with both flipped, both fail and the first is read as it is
        fields = []
        for ri in F._CT_ROOT_PAIR:
            field = _ct_row_field(f, ps, cs, roots[ri], a)
            if field is None:
                return {"why": "container %d's row was not found in the Container Table's root %d" % (a, ri)}
            f.seek(field)
            cur = F.le64(f.read(8), 0)
            if cur != m[a]:
                return {"why": "container %d's field at 0x%x (root %d) holds 0x%x, the translator 0x%x"
                        % (a, field, ri, cur, m[a])}
            fields.append(field)
        return {"a": a, "b": b, "phys_a": m[a], "phys_b": m[b], "abs": fields[0] + k, "xor": xor, "field": fields[0],
                "patches": [(fd + k, xor) for fd in fields]}
    finally:
        f.close()


_A9_SURFACES = (("summary", "forefst", ("summary",)),
                ("dataruns", "forefst", ("dataruns",)),
                ("integrity", "forefst", ("integrity",)),
                ("refsanalysis-containers", "refsanalysis", ("containers",)))
_A9_MAPS = {}


def _a9_damaged():
    img = _need(LAB)
    r = _a9_recipe(img)
    _fx("abs" in r, "A9 recipe on %s: %s" % (LAB, r.get("why")))
    path = _COPY.get(("a9",), img, r["patches"])
    if path not in _A9_MAPS:                        # independently of every verdict surface: the map IS broken
        res = F.bootstrap(path, None)
        res[0].close()
        _A9_MAPS[path] = (res[3].map.get(r["a"]), res[3].map.get(r["b"]))
    _fx(_A9_MAPS[path] == (r["phys_b"], r["phys_b"]), "the flip did not map container %d onto container %d: %r"
        % (r["a"], r["b"], _A9_MAPS[path]))
    return path, r


def test_a9_control_the_undamaged_table_exits_0_without_a_container_warning():
    img = _need(LAB)
    for sid, tool, args in _A9_SURFACES:
        rc, out, _ = _run_cached(tool, img, args)
        assert rc == 0 and not _ct_warnings(out), "%s on the undamaged %s: rc %d, %r" % (sid, LAB, rc,
                                                                                         _ct_warnings(out))


@pytest.mark.parametrize("tool,args", [pytest.param(t, a, id=i) for i, t, a in _A9_SURFACES])   # A9: green in C3
def test_a9_ct_row_flip_warns_and_exits_2(tool, args):
    path, r = _a9_damaged()
    rc, out, _ = _run(tool, path, list(args))
    warns = _ct_warnings(out)
    what = "container %d's physical start 0x%x -> 0x%x (= container %d's; byte 0x%x ^ 0x%02x)" % (
        r["a"], r["phys_a"], r["phys_b"], r["b"], r["abs"], r["xor"])
    print("A9 %s %s | %s | rc %d, warnings %r" % (tool, " ".join(args), what, rc, warns))
    assert rc == 2 and warns, "%s %s with %s: exit %d, container warnings %r" % (tool, " ".join(args), what, rc,
                                                                                  warns)


def _docs(*parts):
    # docs/ ships in BOTH trees (forefstdev and the published forefst), so a missing page can only mean it was
    # renamed or moved (D14 may do that). A skip there would turn this strict RED into a silent skip; fail loudly
    # instead, so the node is re-pointed at the page that now carries the limit. (Critic's change, 2026-09-27.)
    p = os.path.join(REPO, "docs", *parts)
    if not os.path.exists(p):
        raise RedFixtureError("%s is not in this tree: renamed or moved? Re-point this A9 node at the page that "
                              "now documents the Container Table / integrity coverage" % os.path.join("docs", *parts))
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _md_section(md, head):
    i = md.find(head)
    if i < 0:
        return ""
    ends = [x for x in (md.find("\n### ", i + len(head)), md.find("\n## ", i + len(head))) if x > 0]
    return md[i:min(ends)] if ends else md[i:]


@pytest.mark.parametrize("where", [                         # A9: green in C3 (the docs state the limit)
    pytest.param("container_table.md", id="container_table.md"),
    pytest.param("forefst.md#integrity", id="forefst.md-integrity"),
])
def test_a9_resigned_move_limit_is_stated_in_the_docs(where):
    if where == "container_table.md":
        text = _docs("structures", "container_table.md")
    else:
        text = _md_section(_docs("tools", "forefst.md"), "### `integrity`")
        _fx(text, "forefst.md has no `integrity` section")
    assert _states_resigned_limit(text), "%s: no statement that a Container Table moved with re-signed digests " \
                                         "cannot be detected (%d characters read)" % (where, len(text))


def _find_up(rel):
    seen = set()
    for start in (os.getcwd(), REPO):
        d = os.path.abspath(start)
        while d not in seen:
            seen.add(d)
            p = os.path.join(d, rel)
            if os.path.exists(p):
                return p
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


def test_a9_resigned_move_probe_is_recorded_untestable_by_design(tmp_path):     # A9: green at wave C's close
    g = _find_up(os.path.join("analysis", "verification", "phase0", "P0.1_damaged_golden", "golden.json"))
    if g is None:
        pytest.skip("the damaged-volume battery (P0.1 golden.json) is not in this tree")
    with open(g, encoding="utf-8") as fh:
        cases = json.load(fh).get("cases", [])
    rec = [c for c in cases if "K013" in c.get("findings", []) and c.get("untestable") == "by design"
           and re.search(r"(?i)untestable by design", c.get("rationale", ""))]
    assert len(rec) == 1, "no case in %s records the K013 re-signed move as 'untestable by design' (%d cases)" % (
        g, len(cases))
    assert rec[0]["probes"] == [] and rec[0]["damage"] == [], rec[0]
    # the runner records it and carves nothing: no damaged copy, no probe output
    work, out = tmp_path / "work", tmp_path / "out"
    p = subprocess.run([sys.executable, os.path.join(os.path.dirname(g), "run_golden.py"), "--case", rec[0]["id"],
                        "--work", str(work), "--out", str(out)], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0 and "untestable by design (K013): no probe" in p.stdout, (p.returncode, p.stdout,
                                                                                        p.stderr)
    assert "0 probe(s)" in p.stdout and not list(work.iterdir()), (p.stdout, list(work.iterdir()))
