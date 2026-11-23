"""1.13.2 RED cases, group a_bootstrap: plan rows A1, A2, A3, A4 and N139 (D-1, D-2, D-3).

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 2 A (rows A1-A4), section 5 "RED first", decision 19 (the
maintainer's bar: every RED fails on 1.13.1 BECAUSE of the defect, not because of an artefact, and is independently
confirmed). N139: `RUNNING_LOG.md` N139 and `F1_CHECKPOINT_TIE_READING.md`, "Independent check" section 7. Report,
with the observed and expected failure of every node: `analysis/reports/v1.13.2/red/RED_a_bootstrap.md`.

Two volumes, the same cases
---------------------------
Every case runs the real CLI (`forefst.py` / `refsanalysis.py` in a subprocess) on a damaged volume, twice:

* ``[synthetic]`` -- a 1 MiB ReFS 3.14 volume built from bytes in ``tmp_path``: VBR and backup VBR, three
  superblocks, two checkpoints, thirteen empty root tables whose pages carry real CRC64 digests, and a Container
  Table row, laid out like `win11refsmini` (same field offsets, GUID, clocks, CRC32-C self-checksums). The
  undamaged volume gives `summary`, `integrity --checksums` and refsanalysis `summary`/`supb --verify`/`boot
  --verify` exit 0 with every copy "checksum OK" (the controls below). No corpus image is read.
* ``[image]`` -- a hole-preserving scratch copy of the battery's base A, `win11refsmini.raw`, built under
  ``$FOREFST_RED_SCRATCH`` (default: ``forefst_red_scratch`` in the system temp directory) at test time, damaged
  there and deleted by exact path when the test ends. Skipped when the corpus image is absent. These reproduce
  the measured battery cases (A1_chkp_flip_newest, A3_oid_root_zero, A5_supb_primary_zero, the new A1 SUPB
  cases, and F1's hand-made tie).

``pytest -k "not image"`` runs the synthetic half only.

How a RED can fail only because of its defect
---------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``. The fix commit removes the mark; an XPASS fails the
  run. Only a plain ``assert`` states the defect.
* Everything that is not the defect raises something that is NOT an AssertionError, so a strict xfail can never
  count it as the expected failure:
  - ``RedFixtureError``: the base bytes are not what the case needs (checked BEFORE any damage: signatures,
    self-LCNs, GUID, checkpoint list, clocks, every self-checksum, the Object-Table root), a damage op did not
    land, a re-sealed block does not verify, the tool crashed with a traceback or timed out.
  - ``KeptPropertyBroken``: a property 1.13.1 already has on that case and the fix must keep (for example
    exit 2 on D-1, where only the stated reason is wrong).
* Checksums are re-sealed with ``fd._recompute_self_checksum`` (as F1 section 5 prescribes) and every digest is
  cross-checked against this module's own table-driven CRC32-C, so a fixture cannot agree with the tool merely
  because both use the same code. The digests in the F1 report are not copied.
* Controls (not xfail) pass on 1.13.1 and must keep passing: the undamaged volume, a zeroed primary superblock
  (already detected), an untied failed secondary (already a finding), a tie with nothing damaged (not a
  finding), forefst reporting the same zeroed root that refsanalysis prints as "0 rows". They prove the
  fixture's damage is visible to a sound code path, so the RED's failure is the defect's.
* Nothing here touches checkpoint HASHING (F11 is open): no assertion reads a CHKP SHA-256.
"""
import os
import re
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

FOREFST = os.path.join(REPO, "forefst.py")
REFSANALYSIS = os.path.join(REPO, "refsanalysis.py")
TIMEOUT = 900
SCRATCH = os.environ.get(
    "FOREFST_RED_SCRATCH",
    os.path.join(tempfile.gettempdir(), "forefst_red_scratch"))
BASE_IMAGE = "step1/win11refsmini.raw"    # battery base A (P0.1 golden.json "A"); N386 / LB20: by step path
MAX_SCRATCH_ALLOCATED = 64 << 20          # the carve allocates ~13 MB; refuse anything near a dense 2 GiB copy


class RedFixtureError(Exception):
    """The fixture or the run is not what the case needs. Deliberately NOT an AssertionError."""


class KeptPropertyBroken(Exception):
    """A property 1.13.1 already has on this case, which the fix must keep. NOT an AssertionError."""


def _fx(cond, msg):
    if not cond:
        raise RedFixtureError(msg)


def _keep(cond, msg):
    if not cond:
        raise KeptPropertyBroken(msg)


def _red(item, why):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason="RED 1.13.2 %s: %s" % (item, why))


# ─── an independent CRC32-C (Castagnoli, reflected 0x82F63B78), used only to cross-check the fixture ──────────

_CRC32C = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ (0x82F63B78 if _c & 1 else 0)
    _CRC32C.append(_c)


def _crc32c(data):
    crc = 0xFFFFFFFF
    for b in data:
        crc = _CRC32C[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


CS = 4096
SUPB_DESC, CHKP_DESC, ZERO_WINDOW = 0xD0, 0xE0, 0x2C     # win11refsmini: recipe (0xD0|0xE0, CRC32-C, 4, 0x2C)


def _own_digest(block, desc):
    w = bytearray(block[:CS])
    w[desc:desc + ZERO_WINDOW] = b"\0" * ZERO_WINDOW
    return struct.pack("<I", _crc32c(bytes(w)))


# ─── the two volumes ──────────────────────────────────────────────────────────────────────────────────────────

GUID_RAW = bytes.fromhex("c786f3d26c2a1c49addf8fd1c98ca1ce")
GUID = "d2f386c7-2a6c-491c-addf-8fd1c98ca1ce"            # both volumes; the primary's +0x50 flipped -> ...c6
CLOCK_NEW, CLOCK_OLD = 64, 63                            # CHKP +0x10 == +0x60 on both copies (as on the image)
ALLOC_NEW, ALLOC_OLD = 61, 60


class _Geo:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# "lo" is the lower-LCN checkpoint = slot 0 of the superblock list = the NEWER copy (64); "hi" = slot 1 (63).
# Fixture correction 1.14.0 (N500, Q-D D3): the volume carries what a volume carries -- the root directory (0x600) and
# the MLog's Logfile Information Table pair (0x9, 0xa) are rows of the Object Table, and the log is there (an empty log:
# two control copies, a data area of 0x50 clusters, the least refs.sys opens). The older checkpoint copy moved from
# 0x88 to 0xD8 to give the data area 0x49-0x98 in one run; the Object Table holds 3 rows.
SYN = _Geo(kind="synthetic", ps=0, supb=0x1E, backups=(0xFD, 0xFE), lo=0x48, hi=0xD8,
           ot_root=0xA0 * CS, ot_rows=3, vbr=0, cli=["--partition-start", "0"])
IMG = _Geo(kind="image", ps=0x1000000, supb=0x1E, backups=(0x7BFFD, 0x7BFFE), lo=0x13F8, hi=0xEE34,
           ot_root=0x1C08000, ot_rows=24, vbr=0x1000000, cli=[])

_SYN_CLUSTERS = 256
_SYN_ROOT_BASE = 0xA0     # root table i = the 16 KiB page at LCN 0xA0 + 4i (root 0 = the Object Table)
_SYN_TABLE_IDS = {0: 0x02, 3: 0x03, 5: 0x04, 7: 0x0B, 8: 0x0C}
_VOLSIG = 0x84C1FFCF


def _seal(p, desc):
    struct.pack_into("<4s", p, desc + 0x28, _own_digest(p, desc))


def _syn_vbr():
    b = bytearray(512)
    b[3:7] = b"ReFS"
    b[0x10:0x14] = b"FSRS"
    struct.pack_into("<H", b, 0x14, 512)
    struct.pack_into("<Q", b, 0x18, _SYN_CLUSTERS * CS // 512)
    struct.pack_into("<II", b, 0x20, 512, CS // 512)
    b[0x28], b[0x29] = 3, 14
    struct.pack_into("<H", b, 0x2A, 2)                   # CRC64 metadata checksums
    struct.pack_into("<I", b, 0x2C, 0x66)
    struct.pack_into("<Q", b, 0x38, 0x504A8BA64A8B8804)
    struct.pack_into("<Q", b, 0x40, 0x4000000)
    ck = 0                                               # ROR1+ADD over 0x03..0x1FF, skipping 0x16-0x17
    for off in range(3, 512):
        if off not in (0x16, 0x17):
            ck = (((ck >> 1) | ((ck & 1) << 15)) + b[off]) & 0xFFFF
    struct.pack_into("<H", b, 0x16, ck)
    return bytes(b)


def _syn_supb(own):
    p = bytearray(CS)
    p[0:4] = b"SUPB"
    struct.pack_into("<I", p, 4, 2)
    struct.pack_into("<I", p, 0x0C, _VOLSIG)
    struct.pack_into("<Q", p, 0x20, own)
    p[0x50:0x60] = GUID_RAW
    struct.pack_into("<Q", p, 0x68, 1)
    struct.pack_into("<IIII", p, 0x70, 0xC0, 2, SUPB_DESC, 0x30)
    struct.pack_into("<QQ", p, 0xC0, SYN.lo, SYN.hi)
    struct.pack_into("<Q", p, SUPB_DESC, own)
    p[SUPB_DESC + 0x22], p[SUPB_DESC + 0x23] = 1, 8     # CRC32-C, LcnWithChecksum marker
    struct.pack_into("<I", p, SUPB_DESC + 0x24, 4)
    _seal(p, SUPB_DESC)
    return bytes(p)


_ROOT_PAGES = {}
# The root directory's table (OID 0x600): the first free page after the 13 root tables. The Object Table (root 0) and
# its duplicate (root 5) hold its row, as every volume's do (fixture correction 1.14.0, N500: the volume carries what a
# volume carries -- without the row every walk states that the root directory has no Object Table entry)
_SYN_ROOT_DIR_LCN = 0xD4
# the MLog (an empty log): the data area [0x49, 0x99) -- 0x50 clusters --, the control copies at 0x99 and 0x9A, the
# Logfile Information Table's copies (OID 0xa, OID 0x9) on the pages at 0x9B and 0xDC
_SYN_LOG_DS, _SYN_LOG_DE = 0x49, 0x99
_SYN_LOG_CTRL = (0x99, 0x9A)
_SYN_LIT_LCN = {0xA: 0x9B, 0x9: 0xDC}
_SYN_LOG_UUID = bytes(range(0x10, 0x20))


def _syn_table_page(lcn, table_id, rows):
    p = bytearray(make_msb_page(rows, cluster_size=4 * CS))
    struct.pack_into("<I", p, 0x0C, _VOLSIG)
    struct.pack_into("<4Q", p, 0x20, lcn, lcn + 1, lcn + 2, lcn + 3)
    struct.pack_into("<Q", p, 0x48, table_id)
    return bytes(p)


def _syn_root_dir_page():
    return _syn_table_page(_SYN_ROOT_DIR_LCN, 0x600, [])


def _syn_lit_page(oid):
    """A Logfile Information Table copy: row 1 (4-byte key 1) = data start LCN, data end LCN, data size (clusters),
    control copy 0 PLCN, control copy 1 PLCN, 0 -- the layout InitializeVolumeRedoLog reads (6 u64)."""
    v = struct.pack("<6Q", _SYN_LOG_DS, _SYN_LOG_DE, _SYN_LOG_DE - _SYN_LOG_DS, _SYN_LOG_CTRL[0], _SYN_LOG_CTRL[1], 0)
    return _syn_table_page(_SYN_LIT_LCN[oid], oid, [(struct.pack("<I", 1), v)])


def _syn_log_control():
    """The two control copies of an empty log (MC's codec, test code): log start = log end = generation 1 block 0, the
    payload's range the data area in 4 KiB blocks, the volume's signature as the format magic, sequences 51 / 50."""
    import test_1132_red_mlog_chkp as MC                 # (MC imports this module: imported when a volume is built)
    end = MC.lsn(1, 0)
    return [MC.control_block(_VOLSIG, _SYN_LOG_UUID, s, _SYN_LOG_DS, _SYN_LOG_DE, end, end, 3) for s in (51, 50)]


def _syn_ot_row(oid, lcn, page):
    """An Object Table row: key (0, oid); value with the root page's four LCNs at +0x20 and its CRC64 at +0x48 (length
    8 at +0x44), the digest real volumes carry."""
    v = bytearray(0x98)
    struct.pack_into("<4Q", v, 0x20, lcn, lcn + 1, lcn + 2, lcn + 3)
    struct.pack_into("<I", v, 0x44, 8)
    struct.pack_into("<Q", v, 0x48, F.refs_crc64(page))
    return (struct.pack("<QQ", 0, oid), bytes(v))


def _syn_ot_rows():
    """The Object Table's rows, by key: the Logfile Information Table pair (0x9, 0xa), the root directory (0x600)."""
    return [_syn_ot_row(0x9, _SYN_LIT_LCN[0x9], _syn_lit_page(0x9)),
            _syn_ot_row(0xA, _SYN_LIT_LCN[0xA], _syn_lit_page(0xA)),
            _syn_ot_row(0x600, _SYN_ROOT_DIR_LCN, _syn_root_dir_page())]


def _syn_root_page(i, objects=True):
    """Root table i's page. `objects=False`: the Object Table copies without rows (DirVol builds its own)."""
    if (i, objects) in _ROOT_PAGES:
        return _ROOT_PAGES[(i, objects)]
    rows = _syn_ot_rows() if i in (0, 5) and objects else []      # the Object Table and its duplicate
    if i in (7, 8):                                      # one Container Table row: container 2 -> PLCN 0
        # C3 (N216): the row in the form refs.sys reads, as every corpus row is -- 160 bytes, version byte 1 (+0x10),
        # one mapping range (+0x4C) at 0x50 + 16k, k = 4 -- since the tools refuse any other form. The harness stands in
        # for a volume, so it carries what a volume carries (C2's ST-L2 lesson). Values unchanged: PLCN 0, +0x18 left 0
        v = bytearray(0xA0)
        v[0x10] = 1
        struct.pack_into("<I", v, 0x4C, 1)
        struct.pack_into("<QQ", v, 0x90, 0, 0x4000)      # range 0: PLCN 0 (the boot region), 0x4000 clusters
        rows = [(struct.pack("<QQ", 2, 0), bytes(v))]   # PLCN = the first range's start = le64(value, len-16) = 0
    p = bytearray(make_msb_page(rows, cluster_size=4 * CS))
    struct.pack_into("<I", p, 0x0C, _VOLSIG)
    base = _SYN_ROOT_BASE + 4 * i
    struct.pack_into("<4Q", p, 0x20, base, base + 1, base + 2, base + 3)
    if i in _SYN_TABLE_IDS:
        struct.pack_into("<Q", p, 0x48, _SYN_TABLE_IDS[i])
    _ROOT_PAGES[(i, objects)] = bytes(p)
    return _ROOT_PAGES[(i, objects)]


def _syn_chkp(own, clock, alloc):
    p = bytearray(CS)
    p[0:4] = b"CHKP"
    struct.pack_into("<I", p, 4, 2)
    struct.pack_into("<I", p, 0x0C, _VOLSIG)
    struct.pack_into("<Q", p, 0x10, clock)
    struct.pack_into("<Q", p, 0x20, own)
    struct.pack_into("<HHHH", p, 0x50, 3, 14, 3, 14)
    struct.pack_into("<II", p, 0x58, CHKP_DESC, 0x30)
    struct.pack_into("<QQQ", p, 0x60, clock, alloc, 0x100000092)
    struct.pack_into("<I", p, 0x78, 0x682)
    struct.pack_into("<II", p, 0x88, 0x380, 0x20)
    struct.pack_into("<III", p, 0x90, 13, 0xA8, 0x38)
    for i in range(13):
        ro = 0x110 + 0x30 * i
        base = _SYN_ROOT_BASE + 4 * i
        struct.pack_into("<I", p, 0xA8 + 4 * i, ro)
        struct.pack_into("<4Q", p, ro, base, base + 1, base + 2, base + 3)
        p[ro + 0x22], p[ro + 0x23] = 2, 8                # CRC64 page reference
        struct.pack_into("<I", p, ro + 0x24, 8)
        struct.pack_into("<Q", p, ro + 0x28, F.refs_crc64(_syn_root_page(i)))
    struct.pack_into("<Q", p, CHKP_DESC, own)
    p[CHKP_DESC + 0x22], p[CHKP_DESC + 0x23] = 1, 8
    struct.pack_into("<I", p, CHKP_DESC + 0x24, 4)
    _seal(p, CHKP_DESC)
    return bytes(p)


def _build_synthetic(path):
    with open(path, "wb") as fh:
        fh.truncate(_SYN_CLUSTERS * CS)

        def put(off, data):
            fh.seek(off)
            fh.write(data)
        put(0, _syn_vbr())
        put(_SYN_CLUSTERS * CS - 512, _syn_vbr())        # backup boot sector, last sector
        for lcn in (SYN.supb,) + SYN.backups:
            put(lcn * CS, _syn_supb(lcn))
        put(SYN.lo * CS, _syn_chkp(SYN.lo, CLOCK_NEW, ALLOC_NEW))
        put(SYN.hi * CS, _syn_chkp(SYN.hi, CLOCK_OLD, ALLOC_OLD))
        for i in range(13):
            put((_SYN_ROOT_BASE + 4 * i) * CS, _syn_root_page(i))
        put(_SYN_ROOT_DIR_LCN * CS, _syn_root_dir_page())
        for oid, lcn in _SYN_LIT_LCN.items():
            put(lcn * CS, _syn_lit_page(oid))
        for lcn, c in zip(_SYN_LOG_CTRL, _syn_log_control()):
            put(lcn * CS, c)


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


class Vol:
    """One damaged-to-order volume. Every op checks that it landed; every run refuses a crash or a timeout."""

    def __init__(self, geo, path):
        self.geo, self.path, self.ops = geo, path, []

    # raw access
    def at(self, lcn, off=0):
        return self.geo.ps + lcn * CS + off

    def read(self, off, n):
        with open(self.path, "rb") as fh:
            fh.seek(off)
            return fh.read(n)

    def write(self, off, data):
        with open(self.path, "r+b") as fh:
            fh.seek(off)
            fh.write(data)

    def block(self, lcn):
        return self.read(self.at(lcn), CS)

    def verifies(self, lcn):
        return F._verify_self_checksum(self.block(lcn), CS)[0]

    def refs(self, lcn):
        b = self.block(lcn)
        return [F.le64(b, 0xC0), F.le64(b, 0xC8)]

    def clocks(self, lcn):
        b = self.block(lcn)
        return (F.le64(b, 0x10), F.le64(b, 0x60))

    def pin(self):
        """The bytes every case relies on, checked BEFORE any damage (a drifted base is a fixture error)."""
        g = self.geo
        v = self.read(g.vbr, 512)
        _fx(v[3:7] == b"ReFS" and F._vbr_checksum(v, 512) == F.le16(v, 0x16), "%s: VBR" % g.kind)
        for lcn in (g.supb,) + g.backups:
            b = self.block(lcn)
            _fx(b[:4] == b"SUPB" and F.le64(b, 0x20) == lcn, "%s: SUPB @0x%x" % (g.kind, lcn))
            _fx(b[0x50:0x60] == GUID_RAW, "%s: GUID @0x%x" % (g.kind, lcn))
            _fx(self.refs(lcn) == [g.lo, g.hi], "%s: checkpoint list @0x%x" % (g.kind, lcn))
            _fx(self.verifies(lcn) is True and b[SUPB_DESC + 0x28:SUPB_DESC + 0x2C] == _own_digest(b, SUPB_DESC),
                "%s: SUPB @0x%x self-checksum" % (g.kind, lcn))
        for lcn, clk, alloc in ((g.lo, CLOCK_NEW, ALLOC_NEW), (g.hi, CLOCK_OLD, ALLOC_OLD)):
            b = self.block(lcn)
            _fx(b[:4] == b"CHKP" and self.clocks(lcn) == (clk, clk) and F.le64(b, 0x68) == alloc,
                "%s: CHKP @0x%x clocks" % (g.kind, lcn))
            _fx(self.verifies(lcn) is True and b[CHKP_DESC + 0x28:CHKP_DESC + 0x2C] == _own_digest(b, CHKP_DESC),
                "%s: CHKP @0x%x self-checksum" % (g.kind, lcn))
        ot = self.read(g.ot_root, 0x4000)
        _fx(ot[:4] == b"MSB+" and F.le64(ot, 0x48) == 0x02, "%s: Object-Table root page" % g.kind)

    # damage ops
    def flip(self, off, xor=0x01):
        before = self.read(off, 1)
        self.write(off, bytes([before[0] ^ xor]))
        _fx(self.read(off, 1) != before, "flip did not land at 0x%x" % off)
        self.ops.append("flip 0x%x ^0x%02x" % (off, xor))

    def zero(self, off, n):
        _fx(any(self.read(off, n)), "0x%x+0x%x is already zero: zeroing it would damage nothing" % (off, n))
        self.write(off, b"\0" * n)
        _fx(not any(self.read(off, n)), "zero did not land at 0x%x" % off)
        self.ops.append("zero 0x%x+0x%x" % (off, n))

    def reseal(self, lcn, edit, desc):
        """Edit one bootstrap block and recompute its self-checksum with fd._recompute_self_checksum (F1 s.5),
        cross-checked against this module's own CRC32-C."""
        b = bytearray(self.block(lcn))
        recipe = F._self_checksum_recipe(bytes(b), CS)
        _fx(recipe == (desc, 1, 4, ZERO_WINDOW), "0x%x: unexpected self-checksum recipe %r" % (lcn, recipe))
        edit(b)
        out = F._recompute_self_checksum(b, CS, recipe)
        _fx(bytes(out[desc + 0x28:desc + 0x2C]) == _own_digest(out, desc),
            "0x%x: fd._recompute_self_checksum disagrees with an independent CRC32-C" % lcn)
        self.write(self.at(lcn), bytes(out[:CS]))
        _fx(self.verifies(lcn) is True, "0x%x does not verify after re-sealing" % lcn)
        self.ops.append("reseal 0x%x" % lcn)

    def run(self, tool, *args):
        cmd = [sys.executable, "-B", tool, self.path] + list(args) + list(self.geo.cli)
        try:
            r = UW.run(cmd, capture_output=True, text=True, timeout=TIMEOUT,
                       cwd=os.path.dirname(self.path))
        except subprocess.TimeoutExpired:
            raise RedFixtureError("timeout: %s" % " ".join(cmd))
        if "Traceback (most recent call last)" in r.stderr:
            raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
        return r.returncode, r.stdout + "\n" + r.stderr


# ─── fixtures ─────────────────────────────────────────────────────────────────────────────────────────────────

def _synthetic_vol(tmp_path):
    p = str(tmp_path / "target.raw")                     # neutral name: the tool prints it
    _build_synthetic(p)
    v = Vol(SYN, p)
    v.pin()
    return v


@pytest.fixture(params=["synthetic", "image"])
def vol(request, tmp_path):
    if request.param == "synthetic":
        yield _synthetic_vol(tmp_path)
        return
    from test_image_holes_and_page_refs import _corpus_image
    base = _corpus_image(BASE_IMAGE)
    if base is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % BASE_IMAGE)
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="a_bootstrap_", dir=SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _fx(_sparse_capable(d), "%s cannot hold a sparse file; refusing to write a dense 2 GiB copy" % d)
        _carve(base, p)
        alloc = os.stat(p).st_blocks * 512
        _fx(alloc < MAX_SCRATCH_ALLOCATED, "the scratch copy allocated %d bytes" % alloc)
        v = Vol(IMG, p)
        v.pin()
        yield v
    finally:
        if os.path.exists(p):
            os.unlink(p)
        os.rmdir(d)


# ─── damage recipes (each checks its own evidence) ───────────────────────────────────────────────────────────

def damage_supb(v, which, off=0x50):
    """Flip one byte of a superblock copy (default: the first GUID byte). Its self-checksum then fails."""
    lcn = v.geo.supb if which == "primary" else v.geo.backups[0]
    v.flip(v.at(lcn, off))
    _fx(v.verifies(lcn) is False, "SUPB @0x%x still verifies after the flip" % lcn)
    _fx(all(v.verifies(x) is True for x in (v.geo.supb,) + v.geo.backups if x != lcn), "another SUPB copy failed")
    return lcn


def damage_supb_refs(v, n):
    """Flip the low byte of the first n checkpoint references in the PRIMARY superblock (0x40 -> 0x41, ...)."""
    for i in range(n):
        v.flip(v.at(v.geo.supb, 0xC0 + 8 * i))
    _fx(v.verifies(v.geo.supb) is False, "the primary SUPB still verifies")
    for b in v.geo.backups:
        _fx(v.verifies(b) is True and v.refs(b) == [v.geo.lo, v.geo.hi], "backup SUPB @0x%x is not intact" % b)


def damage_chkp(v, lcn):
    """Flip one byte at CHKP+0x400: past the root descriptors, so only the self-checksum fails (battery A1)."""
    before = _root_list(v.block(lcn))
    v.flip(v.at(lcn, 0x400))
    _fx(v.verifies(lcn) is False, "CHKP @0x%x still verifies after the flip" % lcn)
    _fx(v.block(lcn)[CHKP_DESC + 0x28:CHKP_DESC + 0x2C] != _own_digest(v.block(lcn), CHKP_DESC),
        "CHKP @0x%x: the independent CRC32-C still matches" % lcn)
    _fx(_root_list(v.block(lcn)) == before and len(before) == 13 and all(before), "the flip changed the root list")


def _root_list(chkp):
    """The 13 root references of a CHKP block, read by this module (not by the tool's parser)."""
    flags, count, dlen = F.le32(chkp, 0x78), F.le32(chkp, 0x90), F.le32(chkp, 0x5C)
    olb = F.le32(chkp, 0x94) if flags & 0x200 else 0x94
    out = []
    for i in range(min(count, 32)):
        ro = F.le32(chkp, olb + 4 * i)
        out.append(tuple(F.le64(chkp, ro + 8 * j) for j in range(4)) if ro and ro + dlen <= len(chkp) else None)
    return out


def _swap_refs(b):
    b[0xC0:0xD0] = bytes(b[0xC8:0xD0]) + bytes(b[0xC0:0xC8])


def _t2(b):
    struct.pack_into("<Q", b, 0x10, CLOCK_NEW)
    struct.pack_into("<Q", b, 0x60, CLOCK_NEW)


def make_tie(v, slot0_higher):
    """F1 section 5. T2: raise the older copy's +0x10 and +0x60 to 64 (+0x68 stays 60) and re-seal it.
    slot0_higher (F1 step 1): swap the two references in all three superblocks, so slot 0 is the HIGHER LCN."""
    g = v.geo
    if slot0_higher:
        for lcn in (g.supb,) + g.backups:
            v.reseal(lcn, _swap_refs, SUPB_DESC)
            _fx(v.refs(lcn) == [g.hi, g.lo], "SUPB @0x%x: list not swapped" % lcn)
    v.reseal(g.hi, _t2, CHKP_DESC)
    _fx(v.clocks(g.lo) == v.clocks(g.hi) == (CLOCK_NEW, CLOCK_NEW), "the two copies do not tie at +0x10/+0x60")
    _fx(F.le64(v.block(g.lo), 0x68) != F.le64(v.block(g.hi), 0x68), "T2 keeps the copies distinguishable")
    _fx(v.verifies(g.lo) is True and v.verifies(g.hi) is True, "a tied copy does not verify")


def zero_ot_root(v):
    v.zero(v.geo.ot_root, 0x4000)
    # sanctioned plant edit (the lead, 2026-10-22, C1 objtable ST-1, like C-2): B2 reads the duplicate root, so
    # "the Object Table could not be read" needs the duplicate Object-Table root (root 5) zeroed too
    v.zero(0xB4 * CS if v.geo.kind == "synthetic" else 0x4400000, 0x4000)


# ─── reading the output ───────────────────────────────────────────────────────────────────────────────────────

_FAIL = re.compile(r"(?i)\b(fail(?:s|ed|ing|ure)?|mismatch(?:es|ed)?|damaged|invalid|corrupt(?:ed|ion)?|bad)\b")
_CKWORD = re.compile(r"(?i)checksum|crc")
_CHKP_ROW = re.compile(r"(?i)^\s*(chkp|checkpoint)\b")


def _lcn_re(lcn):
    return re.compile(r"(?i)(?<![0-9a-z])0x0*%x(?![0-9a-z])" % lcn)


def _lines(text, lcn):
    r = _lcn_re(lcn)
    return [ln for ln in text.splitlines() if r.search(ln)]


def _named_failed(text, lcn, *words):
    """Lines that name this copy by LCN, carry each regex in `words` (a role, a structure) and a failure word."""
    return [ln for ln in _lines(text, lcn)
            if _FAIL.search(ln) and all(re.search(w, ln, re.I) for w in words)]


def _chkp_rows(text, lcn):
    return [ln for ln in _lines(text, lcn) if _CHKP_ROW.search(ln)]


def _guid(text):
    m = re.search(r"Volume GUID:\s+(\S+)", text)
    return m.group(1) if m else None


def _virtual_clock(text):
    m = re.search(r"Virtual clock:\s+(\d+)", text)
    return int(m.group(1)) if m else None


def _reads_checkpoint(text, lcn, clock):
    """A checkpoint line naming this LCN as a copy that passed, at this clock: the checkpoint was read."""
    return [ln for ln in _chkp_rows(text, lcn) if "checksum OK" in ln and re.search(r"vclock=%d\b" % clock, ln)]


def _ck_rows(text, result):
    """Rows of a verify table that report a self-checksum (a checksum/CRC word) with this result word."""
    return [ln for ln in text.splitlines() if _CKWORD.search(ln) and re.search(result, ln)]


def _ctx(v, rc, out):
    return "\n[%s] ops: %s | rc=%d\n%s" % (v.geo.kind, "; ".join(v.ops) or "none", rc, out[-6000:])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A1 -- a superblock copy that fails its self-checksum is not a finding; its GUID and checkpoint list are trusted
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_a1_control_undamaged_volume_exits_0_with_every_copy_checksum_ok(vol):
    """A0: the clean control must stay unchanged (exit 0, every superblock copy passes, the right GUID)."""
    for cmd in (("summary",), ("integrity",), ("integrity", "--checksums")):
        rc, out = vol.run(FOREFST, *cmd)
        assert rc == 0, cmd + (_ctx(vol, rc, out),)
        for lcn in (vol.geo.supb,) + vol.geo.backups:
            rows = _lines(out, lcn)
            assert rows and all("checksum OK" in ln for ln in rows), (cmd, hex(lcn), rows)
        if cmd == ("summary",):
            assert _guid(out) == GUID


def test_a1_control_a_zeroed_primary_superblock_is_already_a_finding(vol):
    """A5 shape: with the signature gone, 1.13.1 falls back to a backup, prints its GUID and exits 2. The fixture's
    superblock damage is visible to a sound path; the flip cases below fail only because no checksum is checked."""
    vol.zero(vol.at(vol.geo.supb), CS)
    rc, out = vol.run(FOREFST, "summary")
    assert rc == 2, _ctx(vol, rc, out)
    assert _guid(out) == GUID, _ctx(vol, rc, out)
    assert any(re.search(r"(?i)unreadable|missing|damaged|\bBAD\b", ln) for ln in _lines(out, vol.geo.supb))


def test_a1_summary_names_a_primary_superblock_that_fails_its_checksum_and_exits_2(vol):
    lcn = damage_supb(vol, "primary")
    rc, out = vol.run(FOREFST, "summary")
    assert _named_failed(out, lcn, r"\bprimary\b"), \
        "the failing copy must be named by role and LCN (1.13.1: 'SUPB primary LCN 0x1e ... signature OK')" \
        + _ctx(vol, rc, out)
    assert re.search(r"(?im)^.*\bwarn.*\b(superblock|SUPB)\b", out), "summary must warn about it" + _ctx(vol, rc, out)
    assert rc == 2, "summary must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


def test_a1_summary_takes_the_guid_from_a_verified_superblock_copy(vol):
    damage_supb(vol, "primary")
    rc, out = vol.run(FOREFST, "summary")
    assert _guid(out) == GUID, "GUID %r; the verified copies hold %s" % (_guid(out), GUID) + _ctx(vol, rc, out)


@pytest.mark.parametrize("flags", [(), ("--checksums",)], ids=["plain", "checksums"])
def test_a1_integrity_names_a_primary_superblock_that_fails_its_checksum_and_exits_2(vol, flags):
    lcn = damage_supb(vol, "primary")
    rc, out = vol.run(FOREFST, "integrity", *flags)
    assert _named_failed(out, lcn, r"\bprimary\b"), "the failing copy must be named by role and LCN" + _ctx(vol, rc, out)
    assert not re.search(r"Superblock copies:\s+3 intact", out), "a failed copy is not intact" + _ctx(vol, rc, out)
    assert not re.search(r"(?i)verdict:\s*pass", out), "the verdict must not be PASS" + _ctx(vol, rc, out)
    assert rc == 2, "integrity must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", [("summary",), ("integrity",), ("integrity", "--checksums")],
                         ids=["summary", "integrity", "integrity-checksums"])
def test_a1_a_backup_superblock_that_fails_its_checksum_is_named_and_exits_2(vol, cmd):
    lcn = damage_supb(vol, "backup")
    rc, out = vol.run(FOREFST, *cmd)
    if cmd == ("summary",):
        _keep(_guid(out) == GUID, "the primary is intact: its GUID is printed")
    assert _named_failed(out, lcn, r"\bbackup\b"), "the failing copy must be named by role and LCN" + _ctx(vol, rc, out)
    assert rc == 2, "must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["summary", "integrity"])
def test_a1_one_damaged_checkpoint_reference_boots_from_a_verified_backup(vol, cmd):
    damage_supb_refs(vol, 1)
    rc, out = vol.run(FOREFST, cmd)
    _keep(rc == 2, "1.13.1 already exits 2 here (for the checkpoint at the damaged address); keep it" + _ctx(vol, rc, out))
    assert _named_failed(out, vol.geo.supb, r"\bprimary\b"), \
        "the superblock copy that failed its self-checksum must be named" + _ctx(vol, rc, out)
    assert _reads_checkpoint(out, vol.geo.lo, CLOCK_NEW), \
        "the checkpoint the damaged reference named must be read, from a verified backup's list" + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["summary", "integrity"])
def test_a1_two_damaged_checkpoint_references_boot_from_a_verified_backup(vol, cmd):
    damage_supb_refs(vol, 2)
    rc, out = vol.run(FOREFST, cmd)
    assert rc == 2, "bootstrap must proceed from a verified backup and exit 2 (1.13.1: exit 1)" + _ctx(vol, rc, out)
    assert _named_failed(out, vol.geo.supb, r"\bprimary\b"), "the failing superblock copy must be named" + _ctx(vol, rc, out)
    assert _reads_checkpoint(out, vol.geo.lo, CLOCK_NEW), "the newest checkpoint must be read" + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A2 -- a checkpoint that fails its checksum is labelled "valid"; on a tie a failed copy draws no warning
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cmd", [("integrity", "--checksums"), ("summary",)], ids=["integrity-checksums", "summary"])
def test_a2_a_checkpoint_that_fails_its_checksum_is_labelled_failed(vol, cmd):
    damage_chkp(vol, vol.geo.lo)                          # battery A1_chkp_flip_newest
    rc, out = vol.run(FOREFST, *cmd)
    _keep(rc == 2, "1.13.1 already exits 2 on this case" + _ctx(vol, rc, out))
    rows = _chkp_rows(out, vol.geo.lo)
    _keep(rows, "the failed copy is listed" + _ctx(vol, rc, out))
    assert not [ln for ln in rows if re.search(r"(?i)\bvalid\b", ln)], "labelled valid: %r" % rows
    assert all(_FAIL.search(ln) for ln in rows), "each line listing the copy must say it failed: %r" % rows


def test_a2_control_an_untied_failed_secondary_is_already_a_finding(vol):
    """Without a tie 1.13.1 names a failed secondary and exits 2: the tie is what hides it below."""
    damage_chkp(vol, vol.geo.hi)
    for cmd in (("integrity",), ("summary",)):
        rc, out = vol.run(FOREFST, *cmd)
        assert rc == 2, _ctx(vol, rc, out)
        assert _named_failed(out, vol.geo.hi, r"chkp|checkpoint"), _ctx(vol, rc, out)


@pytest.mark.parametrize("slot0_higher", [False, True], ids=["slot0-lower-lcn", "slot0-higher-lcn"])
def test_a2_control_a_tie_with_both_copies_valid_is_not_a_finding(vol, slot0_higher):
    """The hand-made tie itself (F1 s.5, both copies re-sealed and verifying) gives exit 0: the RED's exit 2 can
    only come from the damaged copy."""
    make_tie(vol, slot0_higher)
    for cmd in (("integrity",), ("summary",)):
        rc, out = vol.run(FOREFST, *cmd)
        assert rc == 0, _ctx(vol, rc, out)


@pytest.mark.parametrize("slot0_higher", [False, True], ids=["slot0-lower-lcn", "slot0-higher-lcn"])
@pytest.mark.parametrize("cmd", [("integrity",), ("summary",)], ids=["integrity", "summary"])
def test_a2_a_tie_with_a_failed_copy_exits_2_and_names_it(vol, slot0_higher, cmd):
    make_tie(vol, slot0_higher)
    damage_chkp(vol, vol.geo.hi)
    rc, out = vol.run(FOREFST, *cmd)
    assert _named_failed(out, vol.geo.hi, r"chkp|checkpoint"), \
        "a finding must name the failed copy (1.13.1: '... — valid, vclock=64 (tied clock)')" + _ctx(vol, rc, out)
    assert not re.search(r"(?i)verdict:\s*pass", out), "the verdict must not be PASS" + _ctx(vol, rc, out)
    assert rc == 2, "must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A3 -- refsanalysis summary: checkpoint by +0x10 unchecked, "0 rows" for an unreadable root, never exit 2
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_a3_control_undamaged_volume_refsanalysis_summary(vol):
    """An EMPTY table is 0 rows (synthetic) and a full one its count (image); exit 0; the newest clock, 64."""
    rc, out = vol.run(REFSANALYSIS, "summary")
    assert rc == 0, _ctx(vol, rc, out)
    assert re.search(r"(?m)^\s*Object ID Table\s+%d rows" % vol.geo.ot_rows, out), _ctx(vol, rc, out)
    assert _virtual_clock(out) == CLOCK_NEW and _guid(out) == GUID, _ctx(vol, rc, out)


def test_a3_control_forefst_summary_already_reports_the_zeroed_root_as_unreadable(vol):
    """The same damage through forefst: 'unreadable', exit 2. The fixture is sound; refsanalysis is the defect."""
    zero_ot_root(vol)
    rc, out = vol.run(FOREFST, "summary")
    assert rc == 2, _ctx(vol, rc, out)
    assert re.search(r"(?m)^\s*Object ID Table\s+unreadable", out), _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["summary", "summary++"])
def test_a3_refsanalysis_summary_shows_the_checkpoint_in_use(vol, cmd):
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(REFSANALYSIS, cmd)
    _keep(_named_failed(out, vol.geo.lo),
          "forefst's bootstrap (imported by refsanalysis) names the failed newest copy" + _ctx(vol, rc, out))
    assert _virtual_clock(out) == CLOCK_OLD, "Virtual clock %r" % _virtual_clock(out) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["summary", "summary++"])
def test_a3_refsanalysis_summary_exits_2_when_the_newest_checkpoint_failed(vol, cmd):
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(REFSANALYSIS, cmd)
    assert rc == 2, "refsanalysis %s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


def test_a3_refsanalysis_summary_prints_unreadable_not_0_rows(vol):
    zero_ot_root(vol)                                     # battery A3_oid_root_zero
    rc, out = vol.run(REFSANALYSIS, "summary")
    rows = [ln for ln in out.splitlines() if re.match(r"\s*Object ID Table\s", ln) and " copy 2" not in ln]   # RC3b: the second copy's label
    _keep(len(rows) == 1, "one 'Object ID Table' line" + _ctx(vol, rc, out))
    assert "unreadable" in rows[0].lower() and not re.search(r"\b0 rows\b", rows[0]), "printed %r" % rows[0]


@pytest.mark.parametrize("cmd", ["summary", "files", "objects", "attributes"])
def test_a3_refsanalysis_exits_2_on_every_command_that_recorded_a_skip(vol, cmd):
    zero_ot_root(vol)
    rc, out = vol.run(REFSANALYSIS, cmd)
    _keep(re.search(r"(?i)could not be read|unreadable", out), "the skip is recorded and reported" + _ctx(vol, rc, out))
    assert rc == 2, "refsanalysis %s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("damage", ["primary-flip", "primary-zeroed"])
def test_a3_refsanalysis_summary_takes_the_guid_from_a_verified_superblock_and_exits_2(vol, damage):
    if damage == "primary-flip":
        damage_supb(vol, "primary")
    else:
        vol.zero(vol.at(vol.geo.supb), CS)                # battery A5_supb_primary_zero
    rc, out = vol.run(REFSANALYSIS, "summary")
    assert _guid(out) == GUID, "GUID %r" % _guid(out) + _ctx(vol, rc, out)
    assert rc == 2, "refsanalysis summary must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A4 -- refsanalysis supb --verify / boot --verify: no self-checksum rows, always exit 0
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cmd", ["supb", "boot"])
def test_a4_control_undamaged_volume_verifies_with_exit_0(vol, cmd):
    rc, out = vol.run(REFSANALYSIS, cmd, "--verify")
    assert rc == 0, _ctx(vol, rc, out)
    assert not re.search(r"\bFAIL", out), _ctx(vol, rc, out)


def test_a4_control_boot_verify_already_reports_the_mismatch_in_its_table(vol):
    """The VBR flip lands and the table already says FAIL on 1.13.1: only the exit code is the defect."""
    vol.flip(vol.geo.vbr + 0x38)                          # volume serial: inside the checksummed range
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    assert re.search(r"(?im)checksum.*\bFAIL\b", out), _ctx(vol, rc, out)


def test_a4_supb_verify_prints_a_self_checksum_row_for_every_superblock_and_checkpoint_copy(vol):
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    _keep(rc == 0, "the undamaged volume verifies with exit 0" + _ctx(vol, rc, out))
    rows = _ck_rows(out, r"\bOK\b")
    assert len(rows) >= 5, "3 superblock + 2 checkpoint copies need 5 self-checksum rows, found %d: %r" \
        % (len(rows), rows) + _ctx(vol, rc, out)


@pytest.mark.parametrize("case", ["primary-superblock", "backup-superblock", "newest-checkpoint"])
def test_a4_supb_verify_names_a_copy_that_fails_its_checksum_and_exits_2(vol, case):
    if case == "newest-checkpoint":
        lcn = vol.geo.lo
        damage_chkp(vol, lcn)
    else:
        lcn = damage_supb(vol, "primary" if case == "primary-superblock" else "backup")
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    assert _ck_rows(out, r"(?i)\bFAIL"), \
        "a self-checksum row must read FAIL for the damaged copy 0x%x" % lcn + _ctx(vol, rc, out)
    assert rc == 2, "supb --verify must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


def test_a4_boot_verify_exits_2_on_a_boot_sector_checksum_mismatch(vol):
    vol.flip(vol.geo.vbr + 0x38)
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    _keep(re.search(r"(?im)checksum.*\bFAIL\b", out), "the mismatch is in the table" + _ctx(vol, rc, out))
    assert rc == 2, "boot --verify must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N139 -- bootstrap misreports on damaged checkpoint copies (F1-b section 7: D-1, D-2, D-3)
# The driver takes the valid copy on a tie whatever its slot and LCN (F1-b section 3); with no valid copy it refuses
# to mount (0xC0000032). Exit 2 is right on D-1/D-2; the stated reason is not.
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("slot0_higher", [False, True], ids=["slot0-lower-lcn", "slot0-higher-lcn"])
@pytest.mark.parametrize("cmd", ["files", "summary"])
def test_n139_d1_a_tie_whose_lower_lcn_copy_failed_is_not_called_older_or_stale(vol, slot0_higher, cmd):
    make_tie(vol, slot0_higher)
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(FOREFST, cmd)
    if cmd == "summary":      # a damaged copy is a redundancy finding there (as for an untied one): keep both
        _keep(rc == 2, "exit 2 is right: a copy is damaged" + _ctx(vol, rc, out))
        _keep(_named_failed(out, vol.geo.lo), "the failed copy is named" + _ctx(vol, rc, out))
    bad = [ln for ln in out.splitlines() if re.search(r"(?i)checkpoint", ln)
           and re.search(r"(?i)\bolder\b|\bstale\b", ln)]
    assert not bad, "both copies carry vclock %d; neither is older and the view is not stale: %r" % (CLOCK_NEW, bad)


@pytest.mark.parametrize("slot0_higher", [False, True], ids=["slot0-lower-lcn", "slot0-higher-lcn"])
@pytest.mark.parametrize("cmd", ["summary", "integrity"])
def test_n139_d2_a_failed_tied_copy_is_not_called_the_copy_the_driver_would_use(vol, slot0_higher, cmd):
    make_tie(vol, slot0_higher)
    damage_chkp(vol, vol.geo.lo)
    rc, out = vol.run(FOREFST, cmd)
    _keep(rc == 2, "exit 2 is right: a copy is damaged" + _ctx(vol, rc, out))
    bad = [ln for ln in out.splitlines() if re.search(r"(?i)driver would use", ln) and _FAIL.search(ln)]
    assert not bad, "false claim about the driver's copy: %r" % bad


def test_n139_d3_control_summary_already_says_the_newest_copy_failed(vol):
    """With both copies failed, summary (through the redundancy scanner) already exits 2; the bootstrap-only
    command below is the defect."""
    damage_chkp(vol, vol.geo.lo)
    damage_chkp(vol, vol.geo.hi)
    rc, out = vol.run(FOREFST, "summary")
    assert rc == 2, _ctx(vol, rc, out)


def test_n139_d3_no_valid_checkpoint_is_reported_by_a_bootstrap_only_command(vol):
    damage_chkp(vol, vol.geo.lo)
    damage_chkp(vol, vol.geo.hi)
    rc, out = vol.run(FOREFST, "files")
    assert _says_no_checkpoint_passed(out, (vol.geo.lo, vol.geo.hi)), \
        "files must say that no checkpoint copy passed its self-checksum" + _ctx(vol, rc, out)
    assert rc in (1, 2), "refuse (1) or report (2), never exit 0" + _ctx(vol, rc, out)


# Critic fix (2026-09-27): the first matcher, `checkpoint[^\n]*(fail|invalid|no valid|damaged|corrupt)`, required the
# failure word AFTER "checkpoint", so it rejected its own message ("no checkpoint copy passed its self-checksum") and
# every "no valid checkpoint ..." wording. Order-free now; 1.13.1's `files` output has no checkpoint line at all.
# Second critic fix (2026-10-01, group-2 critic M2): a line with "checkpoint" and ANY failure word was accepted, so a
# warning that only the NEWEST copy failed ("the newest checkpoint (LCN ..) failed its self-checksum") passed although
# the older copy failed too. The line must now say that NO copy passed, or every listed copy must be named as failed.
# Re-check (R1, 2026-10-01): a copy counts as named-failed only from a statement that names exactly ONE of the listed
# copies -- the STALE line names the failed newest copy AND the older copy it was read from, and passed as "both named
# as failed" although it never says the older copy failed.
_NO_VALID = re.compile(r"(?i)\bno (valid |usable |good )?(checkpoint|copy|copies)\b|\bneither\b|\bnone of\b"
                       r"|\b(both|all (the |of the )?(checkpoint )?(copies|checkpoints))\b[^.;]*"
                       r"\b(fail|invalid|damaged|corrupt|mismatch)")
_CHKP_WORD = re.compile(r"(?i)\bchkp\b|checkpoint")


def _says_no_checkpoint_passed(text, lcns=()):
    """Lines (each joined with its deeper-indented continuation lines) that name checkpoint/CHKP and say that NO
    copy passed (`_NO_VALID`); or, when `lcns` is given, checkpoint lines that together name EVERY listed copy with a
    failure word, each from a line that names exactly ONE of the listed copies (a per-copy row or warning). A line
    about one copy failing is not enough, nor one that names a failed copy and the copy read instead."""
    joined, cur, ind = [], None, 0
    for ln in text.splitlines():
        i = len(ln) - len(ln.lstrip())
        if cur is not None and ln.strip() and i > ind and not ln.strip().startswith("["):
            cur += " " + ln.strip()
            continue
        if cur is not None:
            joined.append(cur)
        cur, ind = (ln.strip(), i) if ln.strip() else (None, 0)
    if cur is not None:
        joined.append(cur)
    said = [s for s in joined if _CHKP_WORD.search(s) and _NO_VALID.search(s)]
    per_copy = [(s, [lcn for lcn in lcns if _lcn_re(lcn).search(s)]) for s in joined
                if _CHKP_WORD.search(s) and _FAIL.search(s)]
    per_copy = [(s, hit[0]) for s, hit in per_copy if len(hit) == 1]
    if lcns and {lcn for _s, lcn in per_copy} == set(lcns):
        said += [s for s, _lcn in per_copy]
    return said


# ─── the matchers can go GREEN: a plausible corrected line is accepted, the 1.13.1 line is rejected ─────────────
# A RED whose assertion no correct output could satisfy would fail for the instrument's sake, not the defect's.

def test_red_matchers_accept_corrected_wording_and_reject_the_1131_lines():
    fixed_supb = "  SUPB primary     LCN 0x1e (offset 0x101e000)  — checksum FAILED (CRC32-C)"
    fixed_backup = "      [backup ] LCN 0x7bffd (offset 0x7bffd000) — self-checksum MISMATCH"
    fixed_tied = "  Checkpoint [secondary]:   LCN 0xee34 — checksum FAILED, vclock=64 (tied clock)"
    assert _named_failed(fixed_supb, 0x1E, r"\bprimary\b")
    assert _named_failed(fixed_backup, 0x7BFFD, r"\bbackup\b")
    assert _named_failed(fixed_tied, 0xEE34, r"chkp|checkpoint")
    assert _chkp_rows(fixed_tied, 0xEE34) and all(_FAIL.search(ln) for ln in _chkp_rows(fixed_tied, 0xEE34))
    for old, lcn, role in (("  SUPB primary     LCN 0x1e (offset 0x101e000)  — signature OK", 0x1E, r"\bprimary\b"),
                           ("      [PRIMARY] LCN 0x1e (offset 0x1e000) — signature OK", 0x1E, r"\bprimary\b"),
                           ("      [backup ] LCN 0x7bffd (offset 0x7bffd000) — signature OK", 0x7BFFD, r"\bbackup\b"),
                           ("  Checkpoint [secondary]:   LCN 0xee34 — valid, vclock=64 (tied clock)", 0xEE34,
                            r"chkp|checkpoint")):
        assert not _named_failed(old, lcn, role), old
    # an address is matched whole: 0x1e is not the start of 0x1e000 or 0x101e000, and zero padding is allowed
    assert not _lines("offset 0x1e000 and 0x101e000", 0x1E) and _lines("LCN 0x001E", 0x1E)
    assert _reads_checkpoint("  CHKP primary     LCN 0x13f8 (offset 0x23f8000)  — checksum OK, vclock=64", 0x13F8, 64)
    assert not _reads_checkpoint("  CHKP primary     LCN 0x13f8 (offset 0x23f8000)  — signature OK, vclock=64",
                                 0x13F8, 64)
    assert not _reads_checkpoint("  Checkpoint [PRIMARY  ]:   LCN 0xee34 — checksum OK, vclock=63", 0xEE34, 64)
    row_ok = "self_checksum_supb_backup   OK      LCN 0x7bffd CRC32-C stored=9886cef5 computed=9886cef5"
    row_fail = "self_checksum_chkp_#1        FAIL    LCN 0x13f8 CRC32-C stored=1f8af323 computed=0badf00d"
    assert _ck_rows(row_ok, r"\bOK\b") and _ck_rows(row_fail, r"(?i)\bFAIL") and not _ck_rows(row_ok, r"(?i)\bFAIL")
    # none of the seven 1.13.1 supb --verify rows is a checksum row
    v1131 = """signature_is_SUPB      OK      stored=b'SUPB'
self_block_matches     OK      stored=0x1e, expected=0x1e
checkpoint_count_is_2  OK      count=2
all_checkpoints_valid  OK      #1=CHKP, #2=CHKP
latest_identified      OK      #1 vc=64
self_desc_matches      OK      desc=0x1e, block=0x1e
self_desc_known_size   OK      0x30"""
    assert not _ck_rows(v1131, r"\bOK\b")
    assert _guid("  Volume GUID:        d2f386c7-2a6c-491c-addf-8fd1c98ca1ce  (from backup LCN 0x7bffd)") == GUID
    assert _virtual_clock("  Virtual clock:      63") == CLOCK_OLD
    # D-3: any order of "checkpoint" and the failure; the 1.13.1 `files` lines (no checkpoint line) are rejected
    both = (0x13F8, 0xEE34)
    for said in ("[forefst] WARNING: no checkpoint copy passed its self-checksum; the driver would refuse to mount",
                 "error: no valid checkpoint copy (both failed their self-checksum)",
                 "  [WARN] neither checkpoint copy passes its self-checksum",
                 "  CHKP primary     LCN 0x13f8 (offset 0x23f8000)  — checksum FAILED, vclock=64\n"
                 "  CHKP secondary   LCN 0xee34 (offset 0xfe34000)  — checksum FAILED, vclock=63",
                 "  Checkpoint [PRIMARY  ]:   LCN 0x13f8 — checksum FAILED\n"
                 "  Checkpoint [secondary]:   LCN 0xee34 — checksum FAILED",
                 "[forefst] WARNING: checkpoints 0x13f8 and 0xee34 both failed their self-checksum",
                 "[forefst] WARNING: no checkpoint copy passes its self-checksum (LCN 0x13f8, 0xee34): the driver "
                 "would refuse to mount this volume"):
        assert _says_no_checkpoint_passed(said, both), said
    # ... but a statement about ONE copy failing is not "no copy passed" (group-2 critic M2)
    for one in ("  CHKP primary     LCN 0x13f8 (offset 0x23f8000)  — checksum FAILED, vclock=64",
                "[forefst] WARNING: the newest checkpoint (LCN 0x13f8, vclock 64) failed its self-checksum (CRC32-C)",
                # R1: names both copies, but only the newest as failed (the older one is the copy read)
                "[forefst] WARNING: the newest checkpoint (LCN 0x13f8, vclock 64) failed its self-checksum (CRC32-C); "
                "the volume was read from an OLDER checkpoint (LCN 0xee34, vclock 63), so this view is STALE -- "
                "changes committed after that older checkpoint are not reflected"):
        assert not _says_no_checkpoint_passed(one, both), one
    assert not _says_no_checkpoint_passed("[forefst] ReFS 3.14 | 24 objects | cluster_size=4096\n"
                                          "[forefst] Done. 20 entries (0 deleted) -> CSV (stdout)\n"
                                          "ObjectRef,FullPath,FileName,Extension,FileSize,Created,Modified")
