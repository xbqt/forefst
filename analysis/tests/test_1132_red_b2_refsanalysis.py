"""1.13.2 RED cases, group b2_refsanalysis: running-log items N150, N151, N152, N153 and N154.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 5 "RED first", the fourth revision and decision 19 (the
maintainer's bar: every RED fails on 1.13.1 BECAUSE of the defect, not because of an artefact, and is independently
confirmed). The items have no plan row of their own; their rows are `RUNNING_LOG.md` N150-N154 and
`D14/W1W2_DEFECTS_DEDUP.md` (the same rows, with the independent check IC-4, IC-5 and IC-6 and its section A).
Report, with the observed or expected failure of every node: `analysis/reports/v1.13.2/red/RED_b2_refsanalysis.md`.

What each RED asserts (the row's acceptance, as the running log and the independent check state it)
-------------------------------------------------------------------------------------------------------
N150  `refsanalysis details` of a split (hard-linked) name prints the OBJECT's size -- the size `files` (both
      tools) prints for it -- not the name row's cached copy; in the text and in `--json`.
N151  `refsanalysis boot --verify` passes every row on a healthy 4Kn boot sector (bytes per sector 4096) and exits 0;
      a 512e sector keeps passing and a sector size ReFS never uses keeps failing a row (the row still
      discriminates). Lands with A4: once A4 gives `boot --verify` an exit 2, a FAIL row on a healthy volume is a
      false exit 2.
N152  (tier questioned by IC-4; this file writes the RED the task names: the constant `return 0`) `schema`,
      `upcase`, `objects` and `parentchild --verify` exit 2 when a check of theirs fails, as `chkp --verify` does,
      and the "Result:" line does not read as a pass over a failed check. The negative control IC-4 asks for
      first (the N151 lesson): the same four commands exit 0 on healthy synthetic and healthy corpus volumes.
N153  a zero VBR container size (the `refsutil fixboot` signature) is not reported as the VBR's 64 MiB: every
      site that prints the container size (forefst `summary`, refsanalysis `summary`, `containers`, `chkp -v`)
      states the zero or the default, the `summary --json` of both tools does not carry 64 MiB without saying so,
      and `chkp --verify` does not print "[OK] CPC ... matches VBR" over a VBR field that holds 0.
N154  `bootedit repair` proposes no byte that differs from the volume's true value: nothing on a healthy
      upgraded v3.14 boot sector (selector 0 and GUID 0 are its format-time values), and not CRC64 over a
      SHA-256 volume's selector; and its diagnosis of a fixboot sector names the volume flags (0x66 -> 0x04).
      (c) -- the checksum-mismatch check never fires on fixboot damage -- is not a tool defect: fixboot writes a
      valid checksum, the check is right to pass, and the diagnosis already fires on the zeroed fields. See
      the report.

Volumes
-------
* ``[synthetic]`` -- 1 MiB ReFS 3.14 volumes in pytest's tmp dir, from the a_bootstrap builders (VBR, superblocks,
  checkpoints, root tables; imported, not copied) and, for directory trees and objects, the b2_deleted `DirVol`
  (imported lazily: a missing builder is a `RedFixtureError`, never a collection error). This module adds only
  what its cases need, each re-sealed and cross-checked: a split hard-linked name and its type-0x40 backing
  with type-0x39 link sub-records (N150), populated schema, parent-child, upcase and object tables (N152), a
  Container-Table row that carries its clusters-per-container (N153), an upgraded boot sector and checkpoint
  (N154), and the fixboot recipe read off the corpus witness pair (29 bytes: selector, flags 0x66 -> 0x04,
  serial, container size, GUID, a valid checksum). A 4Kn and an odd-sector boot sector are VBR-only files.
* ``[image]`` -- corpus images, READ-ONLY (never damaged, never copied): win11refs2tspecials (N150),
  lab314_4kn / lab314_4kn_step2 (N151), eight healthy volumes of every format (N152's negative control), the
  fixboot witness `win11refs2tmillionsofactions_aftersalvage_fixboottest` and its sibling (N153, N154), the three
  healthy upgraded volumes of IC-6 (N154). And hole-preserving SCRATCH copies (the battery recipe style,
  `damage.py`): win11refsmini with one table emptied or one page zeroed (N152) or the fixboot recipe applied
  (N153), and win11refs2g_sha256checksums with the fixboot recipe applied (N154: the hand-made SHA-256 fixboot
  copy the row asks for). A scratch copy is made under ``$FOREFST_RED_SCRATCH`` (default:
  ``forefst_red_scratch`` in the system temp directory), bounded to 64 MiB allocated, and deleted by exact path when the test ends.
  Skipped when an image is absent. ``pytest -k "not image"`` runs the rest.
* `bootedit repair` is only ever run with ``--dry-run`` on a corpus image or a scratch copy: without it the command
  writes a copy next to its input. Its write path is exercised on a synthetic volume only, into pytest's tmp dir.
* N152's edits record NO skip (asserted: nothing on stderr says WARNING), so the exit code the RED asks for can
  only come from N152's own fix, not from A3/A11's escalation of recorded skips: the schema and parent-child
  root nodes are emptied and their checkpoint digests re-sealed, the upcase node is emptied, the root
  directory's page is zeroed (`objects` reads only its signature). One recipe serves the synthetic volume and
  the win11refsmini copy.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; the fix commit removes the mark and an XPASS fails the
  run. Only a plain ``assert`` states the acceptance.
* A fixture that is not what the case needs, a crash or a timeout raises ``RedFixtureError``; a property 1.13.1
  already has and the fix must keep raises ``KeptPropertyBroken``. Neither is an AssertionError.
* Each RED has a control that passes on 1.13.1 and differs from it only in the defect's trigger: the primary name
  whose cache is current (N150), a 512e sector (N151), the undamaged volume (N152), the undamaged VBR (N153), a
  healthy native sector and the CRC64 fixboot witness whose proposal matches its sibling (N154).
  `test_b2r_matchers` runs every reader on 1.13.1's own lines and on lines a fix could print.
"""
import contextlib
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import make_msb_page, jdoc# noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (VBR/SUPB/CHKP/root pages, exceptions)

FOREFST, REFSANALYSIS = AB.FOREFST, AB.REFSANALYSIS
TIMEOUT = 1800                                           # the 2 TB fixboot witness walks a large tree
CS = AB.CS
PAGE = 4 * CS
SCRATCH = AB.SCRATCH
RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, AB._red
_SYN = ["--partition-start", "0"]
_VBR_BYTES = 512


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Running the tools
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _run(tool, image, *args, cli=(), cwd, timeout=TIMEOUT):
    """(rc, stdout, stderr). A traceback or a timeout is a fixture error, never the defect under test. `cwd` is
    always a temporary directory, so nothing a command might write can land beside a corpus image."""
    cmd = [sys.executable, "-B", tool, image] + list(args) + list(cli)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


def _ctx(rc, out, err=""):
    return "\n| rc=%s\n%s\n--- stderr ---\n%s" % (rc, out[-5000:], err[-2500:])


def _bd():
    """The b2_deleted volume builder (one builder for the batch). Missing -> a fixture error, never a skip."""
    try:
        import test_1132_red_b2_deleted as BD
        for a in ("DirVol", "_row", "_name_key", "_file_value", "_page", "_T", "_r8"):
            getattr(BD, a)
    except (ImportError, AttributeError) as e:
        raise RedFixtureError("the b2_deleted volume builder is not available: %r" % (e,))
    return BD


def _image_or_skip(name):
    p = _corpus_image(name)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return p


@contextlib.contextmanager
def _scratch_copy(name, prefix):
    """A hole-preserving scratch copy of a corpus image (the battery's carve), deleted by exact path on exit."""
    base = _image_or_skip(name)
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix=prefix, dir=SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file; refusing a dense copy" % d)
        AB._carve(base, p)
        alloc = os.stat(p).st_blocks * 512
        _fx(alloc < AB.MAX_SCRATCH_ALLOCATED, "the scratch copy allocated %d bytes" % alloc)
        yield p
    finally:
        if os.path.exists(p):
            os.unlink(p)
        os.rmdir(d)


def _read(path, off, n):
    with open(path, "rb") as fh:
        fh.seek(off)
        return fh.read(n)


def _write(path, off, data):
    with open(path, "r+b") as fh:
        fh.seek(off)
        fh.write(data)
    _fx(_read(path, off, len(data)) == bytes(data), "a write did not land at 0x%x" % off)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Boot sectors: an independent checksum, the fixboot recipe, where a volume's two copies sit
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _vbr_ck(b):
    """ROR1+ADD over 0x03..size-1, skipping 0x16-0x17 (structures/vbr.md). Written here, not taken from the tool."""
    size = struct.unpack_from("<H", b, 0x14)[0]
    c = 0
    for off in range(3, size):
        if off in (0x16, 0x17):
            continue
        c = (((c >> 1) | ((c & 1) << 15)) + b[off]) & 0xFFFF
    return c


def _seal_vbr(b):
    b = bytearray(b)
    struct.pack_into("<H", b, 0x16, _vbr_ck(b))
    _fx(F._vbr_checksum(bytes(b), 512) == struct.unpack_from("<H", b, 0x16)[0],
        "fd._vbr_checksum disagrees with an independent VBR checksum")
    return bytes(b)


def _vbr_ok(b):
    return b[3:7] == b"ReFS" and b[0x10:0x14] == b"FSRS" and _vbr_ck(b) == struct.unpack_from("<H", b, 0x16)[0]


def _fixboot(b):
    """What `refsutil fixboot` did to the one witness (step3b sibling -> step3c, 29 bytes differ): checksum
    selector 0x2A -> 0, volume flags 0x66 -> 0x04, serial 0x38 -> 0, container size 0x40 -> 0, format GUID
    0x48 -> 0, and a VALID checksum recomputed over the result."""
    b = bytearray(b)
    struct.pack_into("<H", b, 0x2A, 0)
    struct.pack_into("<I", b, 0x2C, 0x04)
    b[0x38:0x58] = b"\0" * 0x20
    return _seal_vbr(b)


_FIXBOOT_DIFF = [0x16, 0x17, 0x2A, 0x2C] + list(range(0x38, 0x40)) + [0x43] + list(range(0x48, 0x58))


def _volume_vbrs(path, ps):
    """(primary offset, backup offset): the backup is the volume's last sector (total_sectors x bytes/sector)."""
    v = _read(path, ps, 512)
    _fx(v[3:7] == b"ReFS", "no ReFS boot sector at 0x%x" % ps)
    bps = struct.unpack_from("<I", v, 0x20)[0]
    total = struct.unpack_from("<Q", v, 0x18)[0]
    return ps, ps + total * bps - bps


def _apply_fixboot(path, ps):
    """The fixboot recipe on both copies (fixboot rewrote the backup too: on the witness it is byte-identical to
    the damaged primary). Returns the undamaged primary, the witness of every byte's true value."""
    prim, back = _volume_vbrs(path, ps)
    orig = _read(path, prim, 512)
    _fx(_vbr_ok(orig) and _read(path, back, 512) == orig, "the base's two boot sectors are not a verified pair")
    _fx(struct.unpack_from("<Q", orig, 0x40)[0] == 0x4000000 and any(orig[0x38:0x40]),
        "the base does not hold a container size and a serial for fixboot to zero")
    dmg = _fixboot(orig)
    _fx([i for i in range(512) if dmg[i] != orig[i]] == [i for i in _FIXBOOT_DIFF if dmg[i] != orig[i]],
        "the recipe changed a byte fixboot does not touch")
    for off in (prim, back):
        _write(path, off, dmg)
    _fx(_vbr_ok(_read(path, prim, 512)), "the fixboot copy's checksum does not verify (fixboot writes a valid one)")
    return orig


def _gpt_ps(path):
    """The first partition that holds a ReFS boot sector (sector 512 or 4096), read here, not by the tool."""
    with open(path, "rb") as fh:
        for ss in (512, 4096):
            fh.seek(ss)
            h = fh.read(92)
            if h[:8] != b"EFI PART":
                continue
            lba, n, es = struct.unpack_from("<Q", h, 72)[0], struct.unpack_from("<I", h, 80)[0], \
                struct.unpack_from("<I", h, 84)[0]
            fh.seek(lba * ss)
            ents = fh.read(min(n, 128) * es)
            for i in range(min(n, 128)):
                e = ents[i * es:(i + 1) * es]
                if e[:16] == b"\0" * 16:
                    continue
                first = struct.unpack_from("<Q", e, 32)[0]
                fh.seek(first * ss)
                if fh.read(8)[3:7] == b"ReFS":
                    return first * ss
    raise RedFixtureError("%s: no GPT partition with a ReFS boot sector" % path)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Synthetic volumes
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_VOL_BYTES = AB._SYN_CLUSTERS * CS
_GUID_RAW = bytes.fromhex("ffc86039e7a4f04981cb4563786e1a86")   # win11refsmini's format GUID


def _set_vbrs(path, primary, backup=None):
    _write(path, 0, primary)
    _write(path, _VOL_BYTES - 512, primary if backup is None else backup)


def _native_volume(path):
    """AB's synthetic volume with a format GUID in both boot sectors (AB leaves it 0): a healthy native v3.14."""
    AB._build_synthetic(path)
    v = bytearray(_read(path, 0, 512))
    _fx(_vbr_ok(v) and struct.unpack_from("<H", v, 0x2A)[0] == 2 and struct.unpack_from("<I", v, 0x2C)[0] == 0x66,
        "AB's boot sector is not the CRC64 / flags 0x66 sector this module expects")
    v[0x48:0x58] = _GUID_RAW
    _set_vbrs(path, _seal_vbr(v))
    return path


def _root_ref(i):
    return 0x110 + 0x30 * i                              # AB._syn_chkp: root i's reference; digest at +0x28


def _replace_root(path, i, page):
    """Write root table i's page (AB's layout: LCN 0xA0 + 4i) and re-seal both checkpoints over its CRC64."""
    vol = AB.Vol(AB.SYN, path)
    lcn = AB._SYN_ROOT_BASE + 4 * i
    old = vol.read(vol.at(lcn), PAGE)
    for c in (AB.SYN.lo, AB.SYN.hi):
        _fx(F.le64(vol.block(c), _root_ref(i) + 0x28) == F.refs_crc64(old),
            "CHKP @0x%x does not hold root %d's digest" % (c, i))
    _fx(page[:4] == b"MSB+" and len(page) == PAGE, "root %d: not a 16 KiB MSB+ page" % i)
    vol.write(vol.at(lcn), page)
    dig = F.refs_crc64(page)
    for c in (AB.SYN.lo, AB.SYN.hi):
        vol.reseal(c, lambda b: struct.pack_into("<Q", b, _root_ref(i) + 0x28, dig), AB.CHKP_DESC)
        _fx(F.le64(vol.block(c), _root_ref(i) + 0x28) == dig, "CHKP @0x%x: root %d digest not updated" % (c, i))


def _root_page(i, rows):
    """AB's root page i with these rows (header fields copied from AB's own page: volume signature, self-LCNs,
    table id)."""
    p = bytearray(make_msb_page(rows, cluster_size=PAGE))
    base = AB._syn_root_page(i)
    p[0x0C:0x10] = base[0x0C:0x10]
    p[0x20:0x40] = base[0x20:0x40]
    p[0x48:0x50] = base[0x48:0x50]
    return bytes(p)


# ── N153: a Container-Table row that carries clusters-per-container, as a real row does (+0x18) ────────────────

_CPC = 0x4000000 // CS                                    # 0x4000 = 64 MiB / 4 KiB


def _ct_rows():
    # C3 (N216): the row in the form refs.sys reads (160 bytes, version byte 1, one range at 0x90), as AB's
    v = bytearray(0xA0)
    v[0x10] = 1
    struct.pack_into("<I", v, 0x18, _CPC)
    struct.pack_into("<I", v, 0x4C, 1)
    struct.pack_into("<QQ", v, 0x90, 0, _CPC)
    return [(struct.pack("<QQ", 2, 0), bytes(v))]        # container 2 -> PLCN 0 (the first range's start), as AB's


def _n153_volume(path, fixboot):
    """The native volume (AB's, with a format GUID) with the CT rows' clusters-per-container set (AB leaves 0, so
    `chkp --verify` would WARN a CPC mismatch on the undamaged volume) and, when `fixboot`, the fixboot recipe on
    both boot sectors."""
    _native_volume(path)
    for i in (7, 8):                                      # the Container Table and its duplicate
        _replace_root(path, i, _root_page(i, _ct_rows()))
    return _apply_fixboot(path, 0) if fixboot else None


# ── N151: VBR-only files (`boot` reads the boot sector and nothing else) ──────────────────────────────────────

def _vbr_file(path, bps, spc):
    """A 1 MiB file: AB's boot sector re-geometried to bps x spc (same volume size), at 0 and in the last sector."""
    v = bytearray(AB._syn_vbr())
    struct.pack_into("<Q", v, 0x18, _VOL_BYTES // bps)
    struct.pack_into("<II", v, 0x20, bps, spc)
    v = _seal_vbr(v)
    with open(path, "wb") as fh:
        fh.truncate(_VOL_BYTES)
    _write(path, 0, v)
    _write(path, _VOL_BYTES - bps, v)
    return path


# ── N154: a healthy UPGRADED v3.14 volume (win10to11refs4g's shape) ───────────────────────────────────────────

def _upgraded_volume(path):
    """AB's volume made to look like a volume formatted on Windows 10 and upgraded to 3.14, byte for byte where
    it matters (read off win10to11refs4g, IC-6): the primary boot sector says 3.14 with selector 0, GUID 0 and
    flags 0x6 (format-time fields, never modified by an upgrade); the backup keeps version 3.4 with its own valid
    checksum; both checkpoints carry flags 0x602 and a zero version echo at +0x50. Page references stay CRC64,
    as they are on win10to11refs4g."""
    AB._build_synthetic(path)
    v = bytearray(_read(path, 0, 512))
    struct.pack_into("<H", v, 0x2A, 0)
    struct.pack_into("<I", v, 0x2C, 0x6)
    v[0x48:0x58] = b"\0" * 16
    prim = _seal_vbr(v)
    v[0x29] = 4
    back = _seal_vbr(v)
    _set_vbrs(path, prim, back)
    vol = AB.Vol(AB.SYN, path)

    def upgraded(b):
        struct.pack_into("<HH", b, 0x50, 0, 0)
        struct.pack_into("<I", b, 0x78, 0x602)
    for c in (AB.SYN.lo, AB.SYN.hi):
        vol.reseal(c, upgraded, AB.CHKP_DESC)
    vol.pin()
    return prim


# ── N150: a split, hard-linked name whose cached size is stale ────────────────────────────────────────────────

_N150_SIZE, _N150_STALE, _N150_ALLOC = 479429, 293302, 483328   # the witness's numbers (0x702:0x5)
_HOME, _OTHER, _FID = 0x701, 0x702, 0x5


def _split_value(fid, home, size):
    """The 84-byte split name row (FileRef home:fid at +0x08/+0x00) with this cached size at +0x38."""
    BD = _bd()
    v = bytearray(BD._file_value(fid, home, BD._T))
    struct.pack_into("<Q", v, 0x38, size)
    return bytes(v)


def _backing_key(fid):
    return struct.pack("<HHIQQ", 0x40, 0, 0, fid, 0)    # type 0x40 at +0, the file id at +0x08 (24 bytes)


def _link_subrow(parent, name):
    """A type-0x39 hard-link sub-record: the object's own list of its names (parent OID @value+0x08, UTF-16 name
    @value+0x18); key = le64(value length) + value, so key[12] is the type."""
    val = struct.pack("<IHHI", 0x80000002, 0x39, 0x0D, parent) + b"\0" * 12 + name.encode("utf-16-le")
    key = struct.pack("<Q", len(val)) + val
    BD = _bd()
    size = BD._r8(0x10 + len(key))
    b = bytearray(size)
    struct.pack_into("<I6H", b, 0, size, 0x10, len(key), 0, 0x18, len(val), 0)
    b[0x10:0x10 + len(key)] = key
    return bytes(b)


def _backing_value(size, alloc, links):
    """A type-0x40 backing: attrs @+0x48, size @+0x58, allocation @+0x60, and an embedded leaf node (offset
    @+0x00) holding one 0x39 sub-record per name, addressed by the node's own row array."""
    BD = _bd()
    subs = [_link_subrow(p, n) for p, n in links]
    base, rows_at = 0xA8, 0x28
    body = b"".join(subs)
    arr_lo = rows_at + len(body)
    v = bytearray(BD._r8(base + arr_lo + 4 * len(subs) + 8))
    struct.pack_into("<I", v, 0, base)
    struct.pack_into("<QQQQ", v, 0x28, BD._T, BD._T, BD._T, BD._T)
    struct.pack_into("<I", v, 0x48, 0x20)
    struct.pack_into("<QQ", v, 0x58, size, alloc)
    v[base + rows_at:base + rows_at + len(body)] = body
    struct.pack_into("<III", v, base + 0x10, arr_lo, len(subs), 0)
    struct.pack_into("<I", v, base + 0x20, arr_lo + 4 * len(subs))
    off = rows_at
    for i, s in enumerate(subs):
        struct.pack_into("<HH", v, base + arr_lo + 4 * i, off, 0xFFFF)
        off += len(s)
    return bytes(v)


def _n150_volume(path):
    """root -> home (0x701) holding orig.csv, whose cached size is current, and the object's backing (size
    479,429, names (0x701, orig.csv) and (0x702, link.csv)); root -> other (0x702) holding link.csv, a second name
    of the same object (FileRef 0x701:0x5) whose cached size is the stale 293,302."""
    BD = _bd()
    v = BD.DirVol()
    home_rows = [BD._row(BD._name_key("orig.csv"), _split_value(_FID, _HOME, _N150_SIZE)),
                 BD._row(_backing_key(_FID), _backing_value(_N150_SIZE, _N150_ALLOC,
                                                            [(_HOME, "orig.csv"), (_OTHER, "link.csv")]))]
    other_rows = [BD._row(BD._name_key("link.csv"), _split_value(_FID, _HOME, _N150_STALE))]
    v.objects = v.tree({0x600: {"name": ""},
                        _HOME: {"parent": 0x600, "name": "home", "files": home_rows},
                        _OTHER: {"parent": 0x600, "name": "other", "files": other_rows}})
    v.write(path)
    return v


# ── N152: populated schema, parent-child, upcase and object tables ────────────────────────────────────────────

_SCHEMA_TYPES = (0xE030, 0xE040, 0xE060, 0xE0C0, 0x110, 0x150, 0x200)   # the seven `schema --verify` expects
_UPCASE_N = 0x80


def _schema_rows():
    rows = []
    for tid in _SCHEMA_TYPES:
        v = bytearray(80)
        struct.pack_into("<I", v, 0, 80)
        struct.pack_into("<I", v, 36, tid)               # u32[9] = self schema id
        rows.append((struct.pack("<I", tid), bytes(v)))
    return rows


def _pc_rows():
    rows = []
    for parent, child in ((0x600, 0x701),):
        k = struct.pack("<4Q", 0, parent, 0, child)
        rows.append((k, k))                               # key == value on every real row
    return rows


def _upcase_rows():
    BD = _bd()
    table = [c - 0x20 if 0x61 <= c <= 0x7A else c for c in range(_UPCASE_N)]
    return [BD._row(struct.pack("<Q", 0), b"Upcase Table"),
            BD._row(struct.pack("<Q", 1), struct.pack("<I", _UPCASE_N)),
            BD._row(struct.pack("<Q", 2), struct.pack("<%dH" % _UPCASE_N, *table))]


def _n152_volume(path):
    """DirVol: root 0x600 -> d (0x701); objects 0x7 and 0x8 (the upcase table and its duplicate), 0x9, 0x500 and
    0x520 (empty tables); the Object Table carries every root page's CRC64 (as real volumes do); root 3 (schema)
    and root 4 (parent-child) populated and re-sealed."""
    BD = _bd()
    v = BD.DirVol()
    v.digests = True
    v.objects = v.tree({0x600: {"name": ""}, 0x701: {"parent": 0x600, "name": "d"}})
    for oid, rows in ((0x7, _upcase_rows()), (0x8, _upcase_rows()), (0x9, ()), (0x500, ()), (0x520, ())):
        lcn = v.alloc()
        v.objects[oid] = (lcn, BD._page(lcn, oid, rows))
    v.write(path)
    _replace_root(path, 3, _root_page(3, _schema_rows()))
    _replace_root(path, 4, _root_page(4, _pc_rows()))


def _empty_node(page):
    """The node with its row-offset array emptied (end = start, count 0): a well-formed MSB+ node that holds no
    rows. The walker returns no rows for it and records nothing (fd:1067 `if astart >= aend: return []`)."""
    p = bytearray(page)
    _fx(p[:4] == b"MSB+", "not an MSB+ page")
    thoff = 0x50 + struct.unpack_from("<I", p, 0x50)[0]
    astart, aend = struct.unpack_from("<I", p, thoff + 0x10)[0], struct.unpack_from("<I", p, thoff + 0x20)[0]
    _fx(astart < aend, "the node holds no rows to remove")
    struct.pack_into("<I", p, thoff + 0x14, 0)
    struct.pack_into("<I", p, thoff + 0x20, astart)
    return bytes(p)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Readers (each one checked by test_b2r_matchers on 1.13.1's own lines and on lines a fix could print)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# ── N150 ──────────────────────────────────────────────────────────────────────────────────────────────────────

def _details_size(out):
    m = re.search(r"(?m)^\s*File size:\s+([\d,]+)\s+bytes", out)
    return int(m.group(1).replace(",", "")) if m else None


def _csv_sizes(out):
    """{FullPath: FileSize} from `files --csv`."""
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(out)))
    return {r["FullPath"]: int(r["FileSize"]) for r in rows if r.get("FileSize", "").isdigit()}


# ── N151 / N152: verification tables ──────────────────────────────────────────────────────────────────────────

def _fail_rows(out):
    """Rows of a `--verify` table that read FAIL (`boot`: a table cell; the others: an `[FAIL]` tag)."""
    return [ln for ln in out.splitlines() if re.search(r"(?<![\w-])FAIL(?![\w-])|\[FAIL\]", ln)]


# Decision 29 (G2c, a matcher edit sanctioned by the lead): VBR+0x40 = 0 is ONE finding, worded neutrally (never FAIL),
# so the N153 controls keep the property "boot --verify has one row for that condition, and it does not read OK or
# PASS" -- satisfied by the FAIL row before decision 29 and by its finding row after it.
_VBR40_ROW = re.compile(r"(?i)container_nonzero|VBR\+0x40|container[ _]size")


def _vbr40_row_not_ok(out):
    rows = [ln for ln in out.splitlines() if re.match(r"^[a-z][a-z0-9_]+\s{2,}\S", ln) and _VBR40_ROW.search(ln)]
    return len(rows) == 1 and not re.search(r"(?<![\w-])(?:OK|PASS)(?![\w-])", rows[0])


def _bad_rows(out):
    """`[FAIL]` and `[WARN]` rows: every check that did not pass (an `[INFO]` row is not a failure)."""
    return [ln for ln in out.splitlines() if re.search(r"^\s*\[(FAIL|WARN)\]", ln)]


def _result_line(out):
    ms = re.findall(r"(?m)^\s*Result:\s*(.*)$", out)
    return ms[-1].strip() if ms else None


def _result_counts(line):
    m = re.search(r"(\d+)\s*/\s*(\d+)", line or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


_RESULT_FAILWORD = re.compile(r"(?i)\bfail|\bwarn|\bnot passed|\bdid not pass|\berror|\bproblem|\bissue")


def _result_names_failure(line):
    return bool(line and _RESULT_FAILWORD.search(line))


# ── N153: the container size ──────────────────────────────────────────────────────────────────────────────────

_CS_LINE = re.compile(r"(?i)container[ _-]?size|bytes[ _-]per[ _-]container")
_64M = re.compile(r"(?i)0x0*4000000\b|\b64(?:\.0)?\s*Mi?B\b|\b67,?108,?864\b")
_QUAL = re.compile(r"(?i)default|assum|not set|unset|\bzero\b|\bis 0\b|=\s*0\b|:\s*0x0\b|\b0x0\b(?!0*[1-9a-f])"
                   r"|fixboot|missing|substitut|absent|\bnone\b")


def _silent_default_lines(text):
    """Lines that print the container size as 64 MiB with no word saying it is not the VBR's own value."""
    return [ln for ln in text.splitlines() if _CS_LINE.search(ln) and _64M.search(ln) and not _QUAL.search(ln)]


def _zero_disclosed(text):
    return [ln for ln in text.splitlines() if _CS_LINE.search(ln) and _QUAL.search(ln)]


def _container_size_honest(text):
    """No container-size line presents the 64 MiB default as read from the VBR -- or a container-size line (the
    value's own, or a note) says the VBR field is zero / the value is the default."""
    return not _silent_default_lines(text) or bool(_zero_disclosed(text))


def _flatten(j, path=""):
    if isinstance(j, dict):
        for k, v in j.items():
            yield from _flatten(v, "%s.%s" % (path, k) if path else str(k))
    elif isinstance(j, list):
        for i, v in enumerate(j):
            yield from _flatten(v, "%s[%d]" % (path, i))
    else:
        yield path, j


def _json_container_honest(j):
    """`container_size` is the VBR's value (0), or some key/value about the container size says it is a default."""
    if j.get("container_size") not in (0x4000000, "0x4000000"):
        return True
    for path, val in _flatten(j):
        sval = val if isinstance(val, str) else ""
        if re.search(r"(?i)container", path) and (_QUAL.search(path) or _QUAL.search(sval)):
            return True
        if re.search(r"(?i)container", sval) and _QUAL.search(sval):
            return True
    return False


def _cpc_ok_rows(text):
    """`chkp --verify` rows that pass the clusters-per-container comparison against the VBR."""
    return [ln for ln in text.splitlines()
            if re.search(r"\[OK\]", ln) and re.search(r"\bCPC\b", ln) and re.search(r"(?i)match", ln)]


# ── N154: bootedit repair ─────────────────────────────────────────────────────────────────────────────────────

def _proposals(out):
    """[(offset, bytes)] of the 'Proposed repairs' block: a `name (0xOFF):` header and its `Proposed:` hex."""
    parts = re.split(r"(?i)proposed repairs", out, maxsplit=1)
    if len(parts) < 2:
        return []
    props, cur = [], None
    for ln in parts[1].splitlines():
        m = re.match(r"\s+\S.*\(0x([0-9a-fA-F]+)\)\s*:\s*$", ln)
        if m:
            cur = int(m.group(1), 16)
            continue
        m = re.match(r"\s+Proposed\s*:\s*((?:[0-9a-fA-F]{2}\s*)+)$", ln)
        if m and cur is not None:
            props.append((cur, bytes.fromhex(m.group(1).replace(" ", ""))))
            cur = None
    return props


def _proposed_sector(out, sector):
    """The sector the proposal would write: the parsed repairs applied and the checksum recomputed. When the tool
    prints its own would-be SHA-256, the reader must reproduce it, or it has misread the proposal (a fixture
    error, never the defect)."""
    props = _proposals(out)
    new = bytearray(sector)
    for off, data in props:
        new[off:off + len(data)] = data
    new = bytearray(_seal_vbr(new)) if props else new
    m = re.search(r"Would-be SHA-256:\s*([0-9a-f]{64})", out)
    if m:
        _fx(hashlib.sha256(bytes(new)).hexdigest() == m.group(1),
            "the proposal as read here does not reproduce the tool's would-be SHA-256: the reader misread it")
    elif props:
        _fx("Would-be SHA-256" not in out, "a would-be SHA-256 line this reader cannot parse")
    return bytes(new), props


def _wrong_bytes(out, current, truth):
    """Every byte the proposal would CHANGE (the checksum aside) that is not the volume's true byte:
    [(offset, proposed, true)]. A damaged field the tool leaves alone is not counted; a byte it writes is."""
    new, _ = _proposed_sector(out, current)
    return [(o, new[o], truth[o]) for o in range(3, 512)
            if o not in (0x16, 0x17) and new[o] != current[o] and new[o] != truth[o]]


def _issue_blocks(out):
    """[(description, offset line)] of the diagnosis ('  [desc]' then '    Offset: 0x..-0x..')."""
    blocks, cur = [], None
    for ln in out.splitlines():
        m = re.match(r"^\s{2}\[(.+)\]\s*$", ln)
        if m:
            cur = [m.group(1), ""]
            blocks.append(cur)
            continue
        m = re.match(r"^\s+Offset:\s*(.+)$", ln)
        if m and cur is not None and not cur[1]:
            cur[1] = m.group(1)
    return [tuple(b) for b in blocks]


def _names_flags(out):
    return [b for b in _issue_blocks(out)
            if re.search(r"(?i)flag", b[0]) or re.search(r"(?i)\b0x2c\b", b[1])]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The readers can go GREEN: a plausible corrected line is accepted, the 1.13.1 line is rejected
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_b2r_matchers():
    # N150
    assert _details_size("  File size:      293302 bytes") == 293302
    assert _details_size("  File size:      479,429 bytes") == 479429
    # N151: 1.13.1's row fails, a renamed row that passes does not
    assert _fail_rows("bps_is_512          FAIL    stored=4096")
    assert not _fail_rows("bytes_per_sector    OK      stored=4096 (4Kn)")
    assert not _fail_rows("checksum_match      OK      stored=0x510D, computed=0x510D")
    # N152
    assert _result_line("\n  Result: 3/6 checks passed\n") == "3/6 checks passed"
    assert not _result_names_failure("3/6 checks passed")
    assert _result_names_failure("3 check(s) FAILED (3/6 passed)")
    assert _result_names_failure("3/6 checks passed, 2 FAILED, 1 WARN")
    assert _result_counts("3 check(s) FAILED (3/6 passed)") == (3, 6)
    assert _bad_rows("  [FAIL] empty\n  [WARN] Missing 0xe030\n  [INFO] Sizes: {80}\n  [OK] x") == \
        ["  [FAIL] empty", "  [WARN] Missing 0xe030"]
    # N153: the 1.13.1 lines are silent defaults; corrected lines are not
    for old in ("  Container size:     0x4000000 (64.0 MB)",
                "  Container size:     0x4000000 (64.0 MiB)",
                "  Container size:     0x4000000 (64.0 MB)",
                "  Bytes per container            0x4000000 (64 MiB)"):
        assert _silent_default_lines(old) and not _container_size_honest(old), old
    for new in ("  Container size:     0x0 (VBR field is zero; the driver assumes 64 MiB)",
                "  Container size:     0x4000000 (64.0 MB)  [default: VBR+0x40 is 0 -- refutil fixboot?]",
                "  Container size:     0 (not set in the boot sector)",
                "  Container size:     0x4000000 (64.0 MB)\n  [!] container size not set in the VBR (0);"
                " 64 MiB assumed"):
        assert _container_size_honest(new), new
    assert not _silent_default_lines("  Clusters per container         0x4000 (16384)")
    assert not _json_container_honest({"container_size": 67108864, "containers_mapped": 1})
    assert _json_container_honest({"container_size": 0})
    assert _json_container_honest({"container_size": 67108864, "container_size_source": "default (VBR 0)"})
    assert _json_container_honest({"container_size": 67108864, "warnings": ["container size is zero in the VBR"]})
    assert _cpc_ok_rows("  [OK] CPC from Container Table (0x4000) matches VBR (0x4000)")
    assert not _cpc_ok_rows("  [WARN] CPC: the VBR's container size is 0 (fixboot); nothing to compare")
    assert not _cpc_ok_rows("  [SKIP] CPC vs VBR -- VBR+0x40 is zero")
    # N154
    v131 = """Found 2 issue(s):

  [format_guid is zero on a 3.14 volume]
    Offset: 0x48-0x57
    Current: 00 00
    Problem: Expected non-zero on native Win11 format.

  [checksum_algo=None on a 3.14 volume]
    Offset: 0x2a-0x2b
    Current: 00 00
    Problem: Native 3.14 expects CRC64 (2) or SHA256 (4).

========================================================================
Proposed repairs (1):
========================================================================

  checksum_algo (0x2a):
    Current:  00 00
    Proposed: 02 00
    Reason:   Restore CRC64 (value 2, default for native 3.14).

  checksum (0x16): 0xf11d -> 0xf21d
"""
    assert _proposals(v131) == [(0x2A, b"\x02\x00")]
    assert [b[0] for b in _issue_blocks(v131)] == ["format_guid is zero on a 3.14 volume",
                                                   "checksum_algo=None on a 3.14 volume"]
    assert not _names_flags(v131)
    assert _names_flags("  [volume_flags 0x04 is fixboot's value (0x66 before)]\n    Offset: 0x2c-0x2f\n")
    assert _names_flags("  [unexpected volume flags]\n    Offset: 0x2c-0x2f\n")
    assert not _proposals("No fixboot damage detected in the checks this command performs.")
    sec = bytearray(AB._syn_vbr())
    struct.pack_into("<H", sec, 0x2A, 0)
    sec = _seal_vbr(sec)
    new, props = _proposed_sector(v131, sec)
    assert props and new[0x2A] == 2 and _wrong_bytes(v131, sec, sec) == [(0x2A, 2, 0)]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The fixtures are what they claim, read by this module (not by the tool)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_b2r_fixture_builders_are_sound(tmp_path):
    # N150: the stale and the current cached sizes, the backing's size and its two 0x39 names
    p = str(tmp_path / "n150.raw")
    v = _n150_volume(p)
    home_lcn, other_lcn = v.objects[_HOME][0], v.objects[_OTHER][0]
    home, other = _read(p, home_lcn * CS, CS), _read(p, other_lcn * CS, CS)
    assert "link.csv".encode("utf-16-le") in other and struct.pack("<Q", _N150_STALE) in other
    assert struct.pack("<QQ", _N150_SIZE, _N150_ALLOC) in home
    assert "orig.csv".encode("utf-16-le") in home and "link.csv".encode("utf-16-le") in home
    bv = _backing_value(_N150_SIZE, _N150_ALLOC, [(_HOME, "orig.csv"), (_OTHER, "link.csv")])
    subs = F.parse_resident_btree_rows(bv)
    assert [(F.le64(sv, 8), sv[0x18:].decode("utf-16-le")) for sk, sv in subs if sk[12] == 0x39] == \
        [(_HOME, "orig.csv"), (_OTHER, "link.csv")]
    # N151: the two geometries verify
    for bps, spc in ((4096, 1), (512, 8), (8192, 1)):
        q = _vbr_file(str(tmp_path / ("v%d.raw" % bps)), bps, spc)
        s = _read(q, 0, 512)
        assert _vbr_ok(s) and struct.unpack_from("<II", s, 0x20) == (bps, spc)
        assert _read(q, _VOL_BYTES - bps, 512) == s
    # N153: the fixboot recipe reproduces the witness diff and keeps a valid checksum
    q = str(tmp_path / "n153.raw")
    orig = _n153_volume(q, fixboot=True)
    dmg = _read(q, 0, 512)
    diff = [i for i in range(512) if dmg[i] != orig[i]]
    assert _vbr_ok(dmg) and set(diff) <= set(_FIXBOOT_DIFF) and set(_FIXBOOT_DIFF) - set(diff) <= {0x16, 0x17}
    assert struct.unpack_from("<Q", dmg, 0x40)[0] == 0 and struct.unpack_from("<I", dmg, 0x2C)[0] == 0x04
    # N154: the upgraded volume's two boot sectors verify and differ only in the version
    q = str(tmp_path / "n154.raw")
    prim = _upgraded_volume(q)
    back = _read(q, _VOL_BYTES - 512, 512)
    assert _vbr_ok(prim) and _vbr_ok(back) and back[0x29] == 4 and prim[0x29] == 14
    assert set(i for i in range(512) if prim[i] != back[i]) - {0x16, 0x17} == {0x29}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N150 -- `refsanalysis details` prints a split name's CACHED size, not the object's
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def n150(tmp_path_factory):
    d = tmp_path_factory.mktemp("n150")
    p = str(d / "target.raw")
    _n150_volume(p)
    rc, out, err = _run(FOREFST, p, "files", "--csv", cli=_SYN, cwd=d)
    sizes = _csv_sizes(out)
    _fx(sizes.get("home/orig.csv") == _N150_SIZE and "other/link.csv" in sizes,
        "forefst files does not list the two names of the synthetic object" + _ctx(rc, out, err))
    return p, d, sizes


def test_n150_control_forefst_files_reports_the_objects_size_for_both_names(n150):
    """The oracle: the walk resolves the stale name to its object's backing (via the object's 0x39 name list)."""
    p, d, sizes = n150
    assert sizes["other/link.csv"] == _N150_SIZE and sizes["home/orig.csv"] == _N150_SIZE, sizes


def test_n150_control_refsanalysis_files_v_already_prints_the_objects_size(n150):
    """K097's fix: refsanalysis's own `files -v` has the object's size; `details` is the site left over."""
    p, d, _ = n150
    rc, out, err = _run(REFSANALYSIS, p, "files", "-v", cli=_SYN, cwd=d)
    row = [ln for ln in out.splitlines() if ln.rstrip().endswith("other/link.csv")]
    assert len(row) == 1 and re.search(r"\s%d\s" % _N150_SIZE, row[0]), row or _ctx(rc, out, err)


def test_n150_control_details_of_the_name_whose_cache_is_current(n150):
    p, d, _ = n150
    rc, out, err = _run(REFSANALYSIS, p, "details", "/home/orig.csv", cli=_SYN, cwd=d)
    assert rc == 0 and _details_size(out) == _N150_SIZE, _ctx(rc, out, err)


# N150: green in wave E step E1c (RED until then: details prints the split name row's cached size (ra:3096), never the walk record's)
def test_n150_details_prints_the_objects_size_for_a_split_hardlink_name(n150):
    p, d, _ = n150
    rc, out, err = _run(REFSANALYSIS, p, "details", "/other/link.csv", cli=_SYN, cwd=d)
    _keep(rc == 0 and "ObjectRef:      0x%x:0x%x" % (_HOME, _FID) in out,
          "details resolves the name to its object (0x701:0x5)" + _ctx(rc, out, err))
    got = _details_size(out)
    _fx(got is not None, "no 'File size:' line" + _ctx(rc, out, err))
    assert got == _N150_SIZE, "details must print the object's size %d, not %d" % (_N150_SIZE, got) + \
        _ctx(rc, out, err)


# N150: green in wave E step E1c (RED until then: details --json carries the split name row's cached size)
def test_n150_details_json_file_size_is_the_objects_size(n150):
    p, d, _ = n150
    rc, out, err = _run(REFSANALYSIS, p, "details", "/other/link.csv", "--json", cli=_SYN, cwd=d)
    try:
        j = jdoc(json.loads(out), F._SUMMARY_KEYS)                    # K21: internal names
    except ValueError:
        raise RedFixtureError("details --json is not JSON" + _ctx(rc, out, err))
    assert j.get("file_size") == _N150_SIZE, "file_size=%r" % j.get("file_size") + _ctx(rc, out, err)


_N150_PATH = ("/testspecials/dir_gamma_163068/dir_echo_659970/dir_cache_507104/dir_india_623599/dir_index_446416/"
              "papa_victor_867137.csv")


# N150: green in wave E step E1c (RED until then: on win11refs2tspecials details prints the cached 293,302 for papa_victor_867137.csv (0x702:0x5))
@pytest.mark.parametrize("fmt", ["text", "json"])
def test_n150_image_details_papa_victor_prints_the_objects_size(fmt, tmp_path):
    """The running log's RA-M1. The object's size, 479,429, is the published `files.csv:454` value, the extracted
    byte count (RC3_1.13.0/CORRECTIONS.md:699) and what `refsanalysis files -v` prints (test_k097)."""
    img = _image_or_skip("win11refs2tspecials.raw")
    rc, out, err = _run(REFSANALYSIS, img, "details", _N150_PATH, *(["--json"] if fmt == "json" else []),
                        cwd=tmp_path)
    _keep(rc == 0, "details resolves the path" + _ctx(rc, out, err))
    if fmt == "json":
        got = jdoc(json.loads(out)).get("file_size")                   # K21: internal names
    else:
        _keep("ObjectRef:      0x702:0x5" in out, "the name resolves to 0x702:0x5" + _ctx(rc, out, err))
        got = _details_size(out)
    assert got == 479429, "details must print the object's size 479429, not %r" % got + _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N151 -- `boot --verify`'s bps_is_512 row fails every healthy 4Kn volume
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _boot_verify(path, cwd, cli=_SYN):
    rc, out, err = _run(REFSANALYSIS, path, "boot", "--verify", cli=cli, cwd=cwd)
    # The table must be there; its checksum row may be named per copy after A4 (decision 20.7: one row per boot-sector
    # copy, e.g. checksum_primary / checksum_backup), so any row about the checksum counts -- not the literal
    # 1.13.1 name `checksum_match` (group-2 RED critic C4).
    # Searched only after "Verification" and with a status on the row: the field table above it has "Checksum 0x16 ..."
    # lines, which a whole-output search took for the row (group-2 RED critic, final check F.3).
    _fx("Verification" in out
        and re.search(r"(?im)^\s*\S*checksum\S*\s+(OK|FAIL)\b", out[out.find("Verification"):]) is not None,
        "no verification table with a checksum row" + _ctx(rc, out, err))
    return rc, out, err


def test_n151_control_a_512e_boot_sector_passes_every_row(tmp_path):
    p = _vbr_file(str(tmp_path / "e512.raw"), 512, 8)
    rc, out, err = _boot_verify(p, tmp_path)
    assert rc == 0 and not _fail_rows(out), _ctx(rc, out, err)


def test_n151_control_a_sector_size_refs_never_uses_still_fails_a_sector_row(tmp_path):
    """Kept: the row must still discriminate. 8,192-byte sectors x 1: the driver's own boot-sector check refuses
    them (`RefsIsBootSectorOurs`: `bps - 0x200 < 0xe01`, i.e. 512..4096, in all seven decompiled builds from
    10.0.17134 to 29574), and the container stays aligned, so only the sector row can object. (Independent
    confirmation 2026-09-28: the value was 1,024, which that same driver check ACCEPTS, so a fix that follows the
    driver's range would have failed this control.)"""
    p = _vbr_file(str(tmp_path / "s8192.raw"), 8192, 1)
    rc, out, err = _boot_verify(p, tmp_path)
    assert [ln for ln in _fail_rows(out) if re.search(r"(?i)bps|sector", ln)], _ctx(rc, out, err)


def test_n151_boot_verify_passes_every_row_on_a_healthy_4kn_boot_sector(tmp_path):
    p = _vbr_file(str(tmp_path / "k4.raw"), 4096, 1)
    rc, out, err = _boot_verify(p, tmp_path)
    _keep(rc == 0, "boot --verify exits 0 on a healthy boot sector" + _ctx(rc, out, err))
    assert not _fail_rows(out), "a healthy 4Kn boot sector must pass every row: %r" % _fail_rows(out) + \
        _ctx(rc, out, err)


@pytest.mark.parametrize("name", ["lab314_4kn.raw", "lab314_4kn_step2.raw"])
def test_n151_image_boot_verify_passes_every_row_on_a_healthy_4kn_volume(name, tmp_path):
    img = _image_or_skip(name)
    ps = _gpt_ps(img)
    s = _read(img, ps, 512)
    _fx(_vbr_ok(s) and struct.unpack_from("<II", s, 0x20) == (4096, 1), "%s: not a healthy 4Kn boot sector" % name)
    rc, out, err = _boot_verify(img, tmp_path, cli=())
    _keep(rc == 0, "boot --verify exits 0" + _ctx(rc, out, err))
    assert not _fail_rows(out), "a healthy 4Kn volume must pass every row: %r" % _fail_rows(out) + _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N152 -- `schema`, `upcase`, `objects`, `parentchild --verify`: "N/M checks passed" and a constant `return 0`
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_N152_CMDS = ["schema", "upcase", "objects", "parentchild"]


@pytest.fixture(scope="module")
def n152(tmp_path_factory):
    """The healthy volume and, per command, a copy with that command's check-failing edit."""
    d = tmp_path_factory.mktemp("n152")
    healthy = str(d / "healthy.raw")
    _n152_volume(healthy)
    rc, out, err = _run(FOREFST, healthy, "integrity", "--checksums", cli=_SYN, cwd=d)
    _fx(rc == 0, "forefst integrity --checksums does not pass the undamaged volume" + _ctx(rc, out, err))
    damaged = {}
    for cmd in _N152_CMDS:
        p = str(d / ("damaged_%s.raw" % cmd))
        with open(healthy, "rb") as src, open(p, "wb") as dst:
            dst.write(src.read())
        _n152_damage(p, cmd, AB.SYN, 0)
        damaged[cmd] = p
    return d, healthy, damaged


@pytest.mark.parametrize("cmd", _N152_CMDS)
def test_n152_control_healthy_synthetic_volume_passes_every_check_with_exit_0(n152, cmd):
    d, healthy, _ = n152
    rc, out, err = _run(REFSANALYSIS, healthy, cmd, "--verify", cli=_SYN, cwd=d)
    line = _result_line(out)
    c = _result_counts(line)
    assert rc == 0 and c and c[0] == c[1] and not _bad_rows(out), _ctx(rc, out, err)


def _n152_damaged_run(path, cmd, cwd, cli):
    rc, out, err = _run(REFSANALYSIS, path, cmd, "--verify", cli=cli, cwd=cwd)
    _fx(not re.search(r"\bWARNING\b", err), "the edit made the tool record a skip or unreadable page, so an exit "
        "code would not isolate N152 from A3/A11's skip escalation" + _ctx(rc, out, err))
    line = _result_line(out)
    c = _result_counts(line)
    _keep(line is not None and c is not None, "%s --verify printed its Result line" % cmd + _ctx(rc, out, err))
    _keep(_bad_rows(out) and c[0] < c[1], "%s --verify reports the edit as a failed check" % cmd +
          _ctx(rc, out, err))
    return rc, out, err, line


# N152: green in wave E step E1c (RED until then: the four --verify commands return 0 whatever their checks found (ra:1256, :1569, :2146, :2377))
@pytest.mark.parametrize("cmd", _N152_CMDS)
def test_n152_verify_exits_2_when_a_check_fails(n152, cmd):
    d, _, damaged = n152
    rc, out, err, line = _n152_damaged_run(damaged[cmd], cmd, d, _SYN)
    assert rc == 2, "%s --verify must exit 2 when a check fails (rc=%d)" % (cmd, rc) + _ctx(rc, out, err)


# N152: green in wave E step E1c (RED until then: the Result line reads 'N/M checks passed' when M-N checks failed)
@pytest.mark.parametrize("cmd", _N152_CMDS)
def test_n152_verify_result_line_does_not_read_as_a_pass(n152, cmd):
    d, _, damaged = n152
    rc, out, err, line = _n152_damaged_run(damaged[cmd], cmd, d, _SYN)
    assert _result_names_failure(line), "the Result line must say checks failed: %r" % line + _ctx(rc, out, err)


def _pages_of(path, ps, cs, tr, vlcns):
    """The logical page (its four clusters, each translated) and the clusters' offsets."""
    offs = [ps + tr.tr(v) * cs for v in vlcns]
    return b"".join(_read(path, o, cs) for o in offs), offs


def _n152_damage(path, cmd, geo, partition_start):
    """One check-failing edit per command that records NO skip, so an exit code cannot come from A3/A11's skip
    escalation instead of N152's fix: the schema (root 3) and parent-child (root 4) root nodes emptied and every
    checkpoint whose reference names that page re-sealed over its new CRC64 (fd._recompute_self_checksum,
    cross-checked by a_bootstrap's own CRC32-C); the upcase table's (0x7) node emptied, its Object-Table digest
    left as it was (`upcase` does not verify it); the root directory's (0x600) page zeroed (`objects` reads only
    its signature). The page is located with forefst's bootstrap on the copy itself; the same code damages the
    synthetic volume (geo AB.SYN) and the scratch copy of win11refsmini (geo AB.IMG)."""
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = F.bootstrap(path, partition_start)
    try:
        if cmd in ("schema", "parentchild"):
            i = 3 if cmd == "schema" else 4
            vl = list(roots[i])
        else:
            vl = list(obj_map.get(0x7 if cmd == "upcase" else 0x600) or [])
        _fx(len(vl) == 4, "%s: the page's four clusters were not found" % cmd)
        page, offs = _pages_of(path, ps, cs, tr, vl)
    finally:
        f.close()
    _fx(page[:4] == b"MSB+", "%s: not an MSB+ page" % cmd)
    if cmd == "objects":
        for o in offs:                                    # the page is not zero (MSB+ above); every cluster is
            _write(path, o, b"\0" * cs)
        return
    new = _empty_node(page)
    for k, o in enumerate(offs):
        if new[k * cs:(k + 1) * cs] != page[k * cs:(k + 1) * cs]:
            _write(path, o, new[k * cs:(k + 1) * cs])
    if cmd == "upcase":
        return
    _fx(ps == geo.ps and cs == CS, "the volume's geometry is not %s's" % geo.kind)
    vol = AB.Vol(geo, path)
    old_dig, new_dig, sealed = F.refs_crc64(page), F.refs_crc64(new), 0
    for c in chkp_lcns:
        blk = vol.block(c)
        refs = AB._root_list(blk)
        if i >= len(refs) or refs[i] is None or list(refs[i]) != vl:
            continue
        flags, olb = F.le32(blk, 0x78), 0x94
        if flags & 0x200:
            olb = F.le32(blk, 0x94)
        ro = F.le32(blk, olb + 4 * i)
        _fx(blk[ro + 0x22] == 2 and F.le32(blk, ro + 0x24) == 8 and F.le64(blk, ro + 0x28) == old_dig,
            "CHKP @0x%x: root %d's reference is not a CRC64 of this page" % (c, i))
        vol.reseal(c, lambda b: struct.pack_into("<Q", b, ro + 0x28, new_dig), AB.CHKP_DESC)
        sealed += 1
    _fx(sealed >= 1, "no checkpoint references root %d's page with its CRC64" % i)


@contextlib.contextmanager
def _n152_image_case(cmd):
    with _scratch_copy("step1/win11refsmini.raw", "n152_%s_" % cmd) as p:
        _n152_damage(p, cmd, AB.IMG, None)
        yield p


# N152: green in wave E step E1c (RED until then: on win11refsmini with a table emptied (or the root directory's page zeroed), --verify prints [FAIL]/[WARN] rows and exits 0)
@pytest.mark.parametrize("cmd", _N152_CMDS)
def test_n152_image_verify_exits_2_when_a_check_fails(cmd, tmp_path):
    with _n152_image_case(cmd) as p:
        rc, out, err, line = _n152_damaged_run(p, cmd, tmp_path, ())
    assert rc == 2, "%s --verify must exit 2 when a check fails (rc=%d)" % (cmd, rc) + _ctx(rc, out, err)


# N152: green in wave E step E1c (RED until then: on win11refsmini with a table emptied (or the root directory's page zeroed), the Result line reads 'N/M checks passed')
@pytest.mark.parametrize("cmd", _N152_CMDS)
def test_n152_image_verify_result_line_does_not_read_as_a_pass(cmd, tmp_path):
    with _n152_image_case(cmd) as p:
        rc, out, err, line = _n152_damaged_run(p, cmd, tmp_path, ())
    assert _result_names_failure(line), "the Result line must say checks failed: %r" % line + _ctx(rc, out, err)


_HEALTHY = ["step1/win10refsmini.raw", "win1121h2test.raw", "win1122h2test.raw", "win1123h2test.raw",
            "step1/win11refsmini.raw", "win11refs5g64k.raw", "lab314_4kn.raw", "wininsiderrefs8gtest2.raw"]


@pytest.mark.parametrize("name", _HEALTHY, ids=[os.path.basename(n) for n in _HEALTHY])   # N386: ids unchanged
def test_n152_control_image_healthy_volumes_exit_0_on_every_verify(name, tmp_path):
    """IC-4's negative control, needed before any exit code is attached (the N151 lesson): v3.4, 3.7, 3.9, 3.10,
    3.14 at 4 KiB and 64 KiB, 4Kn and Insider. 1.13.1 returns 0 unconditionally, so this passes today; after
    the fix it fails if a check that fires on a healthy volume is escalated."""
    img = _image_or_skip(name)
    bad = []
    for cmd in _N152_CMDS:
        rc, out, err = _run(REFSANALYSIS, img, cmd, "--verify", cwd=tmp_path)
        if rc != 0 or _result_line(out) is None:
            bad.append((cmd, rc, _result_line(out), _bad_rows(out), err[-800:]))
    assert not bad, bad


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N153 -- a zero VBR container size is reported as the VBR's 64 MiB
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_N153_TEXT = {"forefst-summary": (FOREFST, ("summary",)),
              "refsanalysis-summary": (REFSANALYSIS, ("summary",)),
              "refsanalysis-containers": (REFSANALYSIS, ("containers",)),
              "refsanalysis-chkp-v": (REFSANALYSIS, ("chkp", "-v"))}
_N153_JSON = {"forefst-summary": (FOREFST, ("summary", "--json")),
              "refsanalysis-summary": (REFSANALYSIS, ("summary", "--json"))}


@pytest.fixture(scope="module")
def n153(tmp_path_factory):
    d = tmp_path_factory.mktemp("n153")
    good, bad = str(d / "undamaged.raw"), str(d / "fixboot.raw")
    _n153_volume(good, fixboot=False)
    _n153_volume(bad, fixboot=True)
    return d, good, bad


def _json_of(out, rc, err):
    try:
        return jdoc(json.loads(out), F._SUMMARY_KEYS)                 # K21: read by internal names
    except ValueError:
        raise RedFixtureError("not JSON" + _ctx(rc, out, err))


@pytest.mark.parametrize("site", sorted(_N153_TEXT))
def test_n153_control_undamaged_volume_prints_the_vbrs_container_size(n153, site):
    """The readers find each site's container-size line, and it shows the VBR's own 64 MiB."""
    d, good, _ = n153
    tool, args = _N153_TEXT[site]
    rc, out, err = _run(tool, good, *args, cli=_SYN, cwd=d)
    lines = [ln for ln in out.splitlines() if _CS_LINE.search(ln)]
    assert lines and all(_64M.search(ln) for ln in lines), _ctx(rc, out, err)


def test_n153_control_undamaged_volume_cpc_row_passes(n153):
    d, good, _ = n153
    rc, out, err = _run(REFSANALYSIS, good, "chkp", "--verify", cli=_SYN, cwd=d)
    assert rc == 0 and _cpc_ok_rows(out) and "checks passed" in (_result_line(out) or ""), _ctx(rc, out, err)


def test_n153_control_boot_verify_already_fails_container_nonzero(n153):
    """The damage is visible to a sound path: `boot --verify` reads the field and fails `container_nonzero`."""
    d, _, bad = n153
    rc, out, err = _boot_verify(bad, d)
    assert _vbr40_row_not_ok(out), _ctx(rc, out, err)                                    # decision 29


@pytest.mark.parametrize("site", sorted(_N153_TEXT))
def test_n153_zero_container_size_is_not_printed_as_the_vbrs_64_mib(n153, site):
    d, _, bad = n153
    tool, args = _N153_TEXT[site]
    rc, out, err = _run(tool, bad, *args, cli=_SYN, cwd=d)
    _fx([ln for ln in out.splitlines() if _CS_LINE.search(ln)], "no container-size line" + _ctx(rc, out, err))
    assert _container_size_honest(out + "\n" + err), \
        "the zero VBR field must be stated: %r" % _silent_default_lines(out) + _ctx(rc, out, err)


@pytest.mark.parametrize("site", sorted(_N153_JSON))
def test_n153_zero_container_size_is_not_a_silent_64_mib_in_json(n153, site):
    d, _, bad = n153
    tool, args = _N153_JSON[site]
    rc, out, err = _run(tool, bad, *args, cli=_SYN, cwd=d)
    j = _json_of(out, rc, err)
    _fx("container_size" in j, "no container_size key" + _ctx(rc, out, err))
    assert _json_container_honest(j), "container_size=%r with no note" % j.get("container_size") + _ctx(rc, out, err)


def test_n153_chkp_verify_does_not_match_the_cpc_against_a_zero_vbr_field(n153):
    d, _, bad = n153
    rc, out, err = _run(REFSANALYSIS, bad, "chkp", "--verify", cli=_SYN, cwd=d)
    _fx(re.search(r"\bCPC\b", out), "no CPC row" + _ctx(rc, out, err))
    assert not _cpc_ok_rows(out), "the CPC row must not pass against a zero VBR field: %r" % _cpc_ok_rows(out) + \
        _ctx(rc, out, err)


# ── the image half: the fixboot witness (read-only) and win11refsmini with the recipe applied (scratch) ───────

_WITNESS = "win11refs2tmillionsofactions_aftersalvage_fixboottest.raw"
_SIBLING = "win11refs2tmillionsofactions_aftersalvage.raw"


@contextlib.contextmanager
def _n153_image(which):
    if which == "fixboot-witness":
        img = _image_or_skip(_WITNESS)
        s = _read(img, _gpt_ps(img), 512)
        _fx(_vbr_ok(s) and struct.unpack_from("<Q", s, 0x40)[0] == 0 and not any(s[0x38:0x40]),
            "the witness does not hold fixboot's zero container size and serial")
        yield img
    else:
        with _scratch_copy("step1/win11refsmini.raw", "n153_") as p:
            _apply_fixboot(p, _gpt_ps(p))
            yield p


_N153_IMAGES = ["fixboot-witness", "win11refsmini-fixboot-recipe"]


@pytest.mark.parametrize("which", _N153_IMAGES)
def test_n153_control_image_boot_verify_fails_container_nonzero(which, tmp_path):
    with _n153_image(which) as img:
        rc, out, err = _boot_verify(img, tmp_path, cli=())
    assert _vbr40_row_not_ok(out), _ctx(rc, out, err)                                    # decision 29


@pytest.mark.parametrize("which", _N153_IMAGES)
@pytest.mark.parametrize("site", sorted(_N153_TEXT))
def test_n153_image_zero_container_size_is_not_printed_as_the_vbrs_64_mib(which, site, tmp_path):
    tool, args = _N153_TEXT[site]
    with _n153_image(which) as img:
        rc, out, err = _run(tool, img, *args, cwd=tmp_path)
    _fx([ln for ln in out.splitlines() if _CS_LINE.search(ln)], "no container-size line" + _ctx(rc, out, err))
    assert _container_size_honest(out + "\n" + err), \
        "the zero VBR field must be stated: %r" % _silent_default_lines(out) + _ctx(rc, out, err)


@pytest.mark.parametrize("which", _N153_IMAGES)
@pytest.mark.parametrize("site", sorted(_N153_JSON))
def test_n153_image_zero_container_size_is_not_a_silent_64_mib_in_json(which, site, tmp_path):
    tool, args = _N153_JSON[site]
    with _n153_image(which) as img:
        rc, out, err = _run(tool, img, *args, cwd=tmp_path)
    j = _json_of(out, rc, err)
    _fx("container_size" in j, "no container_size key" + _ctx(rc, out, err))
    assert _json_container_honest(j), "container_size=%r with no note" % j.get("container_size") + _ctx(rc, out, err)


@pytest.mark.parametrize("which", _N153_IMAGES)
def test_n153_image_chkp_verify_does_not_match_the_cpc_against_a_zero_vbr_field(which, tmp_path):
    with _n153_image(which) as img:
        rc, out, err = _run(REFSANALYSIS, img, "chkp", "--verify", cwd=tmp_path)
    _fx(re.search(r"\bCPC\b", out), "no CPC row" + _ctx(rc, out, err))
    assert not _cpc_ok_rows(out), "the CPC row must not pass against a zero VBR field: %r" % _cpc_ok_rows(out) + \
        _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N154 -- `bootedit repair`: wrong bytes proposed (selector 2 where 0 or 4 is true), flags 0x04 unreported
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _repair(path, cwd, *extra, cli=_SYN):
    rc, out, err = _run(REFSANALYSIS, path, "bootedit", "repair", *extra, cli=cli, cwd=cwd)
    _fx("Diagnosing boot sector" in out, "Phase 2 (the fixboot diagnosis) did not run" + _ctx(rc, out, err))
    return rc, out, err


def test_n154_control_healthy_native_boot_sector_has_no_finding_and_no_proposal(tmp_path):
    p = _native_volume(str(tmp_path / "native.raw"))
    rc, out, err = _repair(p, tmp_path, "--dry-run")
    assert rc == 0 and not _issue_blocks(out) and not _proposals(out), _ctx(rc, out, err)


def test_n154_control_fixboot_damage_is_diagnosed_and_every_proposed_byte_is_the_original(tmp_path):
    """On a CRC64 native volume (the witness's kind) 1.13.1's proposal -- container 64 MiB, selector 2 -- writes
    only bytes the undamaged sector holds. A fix must keep proposing nothing that contradicts the volume."""
    p = _native_volume(str(tmp_path / "fixboot.raw"))
    orig = _apply_fixboot(p, 0)
    dmg = _read(p, 0, 512)
    rc, out, err = _repair(p, tmp_path, "--dry-run")
    assert _issue_blocks(out), _ctx(rc, out, err)
    assert not _wrong_bytes(out, dmg, orig), _ctx(rc, out, err)


# N154 (b): green in wave E step E1c (RED until then: on a healthy upgraded v3.14 boot sector the repair proposes selector 2 at 0x2A (0 is right))
def test_n154_dry_run_proposes_no_wrong_byte_on_a_healthy_upgraded_boot_sector(tmp_path):
    p = str(tmp_path / "upgraded.raw")
    prim = _upgraded_volume(p)
    rc, out, err = _repair(p, tmp_path, "--dry-run")
    wrong = _wrong_bytes(out, prim, prim)
    assert not wrong, "proposed (offset, byte, true byte): %r" % wrong + _ctx(rc, out, err)


# N154 (b): green in wave E step E1c (RED until then: without --dry-run the repair writes selector 2 into a healthy upgraded boot sector)
def test_n154_repair_writes_nothing_to_a_healthy_upgraded_boot_sector(tmp_path):
    """The write path itself (safe mode: a copy; the input is never touched). Every byte it writes into the copy's
    boot sector must be the healthy sector's own."""
    p = str(tmp_path / "upgraded.raw")
    prim = _upgraded_volume(p)
    before = _sha(p)
    out_path = str(tmp_path / "repaired.raw")
    rc, out, err = _repair(p, tmp_path, "-o", out_path)
    _keep(_sha(p) == before, "the input image is never modified" + _ctx(rc, out, err))
    written = _read(out_path, 0, 512) if os.path.exists(out_path) else prim
    diff = [(o, written[o], prim[o]) for o in range(512) if written[o] != prim[o]]
    assert not diff, "bytes written into a healthy boot sector (offset, new, old): %r" % diff + _ctx(rc, out, err)


# N154 (a): green in wave E step E1c (RED until then: fixboot's volume flags 0x66 -> 0x04 are not reported (only a zero flags field is))
def test_n154_diagnosis_names_the_volume_flags_on_a_fixboot_boot_sector(tmp_path):
    p = _native_volume(str(tmp_path / "fixboot.raw"))
    _apply_fixboot(p, 0)
    rc, out, err = _repair(p, tmp_path, "--dry-run")
    _keep([b for b in _issue_blocks(out) if "container_size" in b[0]], "the fixboot damage is diagnosed" +
          _ctx(rc, out, err))
    assert _names_flags(out), "the diagnosis must name the volume flags (0x2C: 0x04 where fixboot found 0x66): " \
        "%r" % _issue_blocks(out) + _ctx(rc, out, err)


# ── the image half ────────────────────────────────────────────────────────────────────────────────────────────

_UPGRADED = ["win10to11refs4g.raw", "win10to11refs4g_afterwin11mount.raw", "win1122h2test_afteropenedwithinsider.raw"]


# N154 (b): green in wave E step E1c (RED until then: on the three healthy upgraded v3.14 volumes of IC-6 the repair proposes selector 2 (0 is right))
@pytest.mark.parametrize("name", _UPGRADED)
def test_n154_image_dry_run_proposes_no_wrong_byte_on_a_healthy_upgraded_volume(name, tmp_path):
    img = _image_or_skip(name)
    s = _read(img, _gpt_ps(img), 512)
    _fx(_vbr_ok(s) and s[0x28:0x2A] == b"\x03\x0e" and struct.unpack_from("<H", s, 0x2A)[0] == 0
        and not any(s[0x48:0x58]) and any(s[0x38:0x40]) and struct.unpack_from("<Q", s, 0x40)[0] == 0x4000000,
        "%s: not IC-6's healthy upgraded boot sector (v3.14, selector 0, GUID 0, serial and container set)" % name)
    rc, out, err = _repair(img, tmp_path, "--dry-run", cli=())
    wrong = _wrong_bytes(out, s, s)
    assert not wrong, "proposed (offset, byte, true byte): %r" % wrong + _ctx(rc, out, err)


# N154 (b): green in wave E step E1c (RED until then: on a SHA-256 volume after fixboot the repair proposes CRC64 (selector 2; the volume's is 4))
def test_n154_image_dry_run_proposes_no_wrong_byte_on_a_sha256_fixboot_copy(tmp_path):
    """The hand-made SHA-256 fixboot copy the row asks for: win11refs2g_sha256checksums (selector 4, page
    references of checksum type 4 with 32-byte digests), the fixboot recipe applied to both boot sectors. Only
    the bytes the proposal would change are compared with the undamaged sector."""
    with _scratch_copy("win11refs2g_sha256checksums.raw", "n154_sha256_") as p:
        ps = _gpt_ps(p)
        orig = _apply_fixboot(p, ps)
        _fx(struct.unpack_from("<H", orig, 0x2A)[0] == 4, "the base is not a SHA-256 volume")
        dmg = _read(p, ps, 512)
        rc, out, err = _repair(p, tmp_path, "--dry-run", cli=())
    _keep(_issue_blocks(out), "the fixboot damage is diagnosed" + _ctx(rc, out, err))
    wrong = _wrong_bytes(out, dmg, orig)
    assert not wrong, "proposed (offset, byte, true byte): %r" % wrong + _ctx(rc, out, err)


def test_n154_control_image_fixboot_witness_proposal_matches_the_sibling(tmp_path):
    """IC-6: on the CRC64 witness the proposal (64 MiB, CRC64) is what the pre-fixboot sibling holds."""
    img, sib = _image_or_skip(_WITNESS), _image_or_skip(_SIBLING)
    dmg, orig = _read(img, _gpt_ps(img), 512), _read(sib, _gpt_ps(sib), 512)
    _fx([i for i in range(512) if dmg[i] != orig[i]] == _FIXBOOT_DIFF, "the witness pair does not differ as recorded")
    rc, out, err = _repair(img, tmp_path, "--dry-run", cli=())
    assert _issue_blocks(out), _ctx(rc, out, err)
    assert not _wrong_bytes(out, dmg, orig), _ctx(rc, out, err)


# N154 (a): green in wave E step E1c (RED until then: on the fixboot witness the flags (0x04, 0x66 on the sibling) are not in the diagnosis)
def test_n154_image_fixboot_witness_diagnosis_names_the_volume_flags(tmp_path):
    img = _image_or_skip(_WITNESS)
    s = _read(img, _gpt_ps(img), 512)
    _fx(struct.unpack_from("<I", s, 0x2C)[0] == 0x04, "the witness's flags are not 0x04")
    rc, out, err = _repair(img, tmp_path, "--dry-run", cli=())
    _keep([b for b in _issue_blocks(out) if "container_size" in b[0]], "the fixboot damage is diagnosed" +
          _ctx(rc, out, err))
    assert _names_flags(out), "the diagnosis must name the volume flags: %r" % _issue_blocks(out) + _ctx(rc, out, err)
