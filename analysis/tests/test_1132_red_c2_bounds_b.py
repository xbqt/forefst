"""1.13.2 (ships as 1.14.0) RED cases, wave C step C2, area `bounds_b`: N344 (a), (b) (a damaged primary boot sector:
the volume is read from a verified, self-consistent backup boot sector) and N142 (the refusal text quotes the 8-byte
OEM id only).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (settlements Q19-Q21, Q23, Q-M2 = decision 43),
`fixes/WAVEC_INVENTORY.md` and `fixes/WAVEC_CENSUS.md` (rows N344, N142), `fixes/WAVEC_READING_bounds.md` section 3
("N344 damaged / position / statement / class") and 4.2 (the closure table), PLAN_1.13.2 decision 36 Q3 A.
Report: `analysis/reports/v1.13.2/fixes/RED_C2_bounds_b.md`.

  N344 (a)  a primary that keeps its signature but fails a `RefsIsBootSectorOurs` test an image can answer (V4: bytes
            3..10 `ReFS\\0\\0\\0\\0`; 0x57 < +0x14 <= ss; the ROR1+ADD checksum over 3..(+0x14)-1; 0x200 <= +0x20 <= 0x1000;
            +0x24 in {1,4,...,512}; 0 < +0x18 <= the partition in ss-sectors rounded down to 64 MiB) is not used: the
            volume -- every boot-sector field, the volume length, the backup superblock slots -- is read from the
            verified backup; the output says the primary is damaged, names the failed test and the backup's offset;
            every command exits 2 (Q19-Q21; decisions 36 Q3 A, 27.2).
  N344 (b)  a zeroed primary: the backup is found by Q20's search -- (1) the driver's mount-read position
            ps + floor(P / 64 MiB) x 64 MiB - ss (P = the GPT entry at ps, else the image after ps; ss = the GPT LBA
            size, else 512), (2) a readable primary's own T-1, (3) every 64 MiB boundary below (1), top down, at -512
            and -4096 -- accepting only a copy that passes the same tests AND is self-consistent (ps + (T'-1) x bps' =
            its offset); found: the statement, exit 2; none: exit 1 naming the range searched.
  Q-M2      (decision 43) a backup older than the volume: its version printed as recorded, decoded as 3.14 when
            $VOLUME_INFORMATION and the checkpoint's 0x600 flags show 3.14, with the reason.
  N142      (Q23) the refusal text quotes the 8-byte OEM id only (`bs[3:11]`), never bytes 0x0B.. (a NUL, 0x02, 0x08 on
            NTFS); exit 1 unchanged. Class: forefst `parse_vbr` (both refusal branches), refsanalysis `_validate_vbr`.

Default applied (follows from Q18 and decisions 26/27.1; RED_C2_bounds_b.md section 0): the T <= partition test is
made only where a GPT entry records the partition length. A raw image's length is not its partition's length (an image
that ends before the volume is B3's "truncated", Q18, and bounds_a keeps exit 0 for `files` on the truncated raw
synthetic volume), so on a raw image (2) applies and the 1 MiB synthetic volume -- which the driver's rounding would
refuse -- stays an intact volume read from its primary (controls below).

Volumes: hole-preserving scratch copies of the battery's base A (`step1/win11refsmini.raw`, GPT, through
`test_1132_red_b_items.py`'s carve), a raw partition image carved from base A's partition #2 (no GPT,
`--partition-start 0`), the 1 MiB synthetic ReFS 3.14 volume of `test_1132_red_a_bootstrap.py`, and a carve of
`step6/lab314_4kn.raw` (4Kn, GPT LBA 4096). Base A's geometry, read by this module from the bytes and pinned (MR-V
bounds_census.jsonl agrees): partition #2 at 0x1000000, LBA 0x8000..0x3fff7f (P = 2130640896 bytes); T = 0x3e0000
sectors of 512 = 0x7c000000 = 31 x 64 MiB, so the driver's mount-read position and the primary's T-1 are both
0x7cfffe00, where an identical backup sits. The raw carve: 0x7bfffe00. The 4Kn carve: 0xfcfff000. The 64 MiB boundary
below base A's: 0x78fffe00.

Conventions (test_1132_red_a_bootstrap.py): every RED is ``xfail(strict=True, raises=AssertionError)``; fixture
problems raise RedFixtureError, a property the tool already has and must keep raises KeptPropertyBroken (neither is an
AssertionError); expected values are computed here from the bytes (an independent ROR1+ADD, cross-checked against
forefst's); controls (no mark) pass now and must keep passing. Matchers test values and the decided content, not one
wording: a hex offset in either case or zero-padded, a statement on one line or wrapped over up to four lines, in
either order.

After the critic (RED_C2_bounds_b_critic.md): a statement is the fewest consecutive lines that carry its elements, plus
the lines that continue it (indented deeper), never a neighbouring row of other output -- `files` prints
"cluster_size=4096" and summary "partition starts at" next to where the statement goes, which named a failed test for
any statement; the failed test must be named in the primary's clause (from "primary" / "sector 0" to the next
"backup"), so a "how it was found" text ("the partition's end rounded down to 64 MiB") does not name it either. The
+0x20 test has its plant; Q-M2's decoding is checked through `mlog` (the `files` listing does not depend on the
version); a copy found by the search must say so (Q20); the class nodes reach integrity's own boot-sector read,
refsanalysis `summary`, and `chkp` / `containers` (which call parse_vbr unguarded and stop with a traceback today).
"""
import contextlib
import os
import re
import struct
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402
import test_1132_red_b_items as BI                       # noqa: E402  (base A carve, runners, scratch)
import test_1132_red_group2b as G2B                      # noqa: E402  (N239's per-copy row matcher, see the unit test)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, BI._red
FOREFST, REFSANALYSIS = BI.FOREFST, BI.REFSANALYSIS
_vrun, _ctx = BI._vrun, BI._ctx

MIB64 = 64 << 20
GPT_BASIC_DATA = F.GPT_BASIC_DATA
PS_A = 0x1000000                                         # base A: partition #2
P_A = 2130640896                                         # its GPT entry: LBA 0x8000..0x3fff7f
T_A = 0x3E0000                                           # boot sector +0x18 (x 512 = 0x7c000000 = 31 x 64 MiB)
BK_A = PS_A + T_A * 512 - 512                            # 0x7cfffe00: mount-read position (1) = the primary's T-1 (2)
STALE_A = PS_A + 30 * MIB64 - 512                        # 0x78fffe00: the next 64 MiB boundary down, at -512
T_STALE = 30 * MIB64 // 512                              # a copy self-consistent at STALE_A
BK_RAW = (P_A // MIB64) * MIB64 - 512                    # 0x7bfffe00 in the raw partition image
KN_IMAGE = "step6/lab314_4kn.raw"
KN_MAX_ALLOCATED = 256 << 20                             # the 4Kn carve allocates ~173 MB (measured 2026-10-23)
CMDS = {"summary": (FOREFST, "summary"), "files": (FOREFST, "files"),
        "ra-boot": (REFSANALYSIS, "boot"), "ra-supb": (REFSANALYSIS, "supb"),
        "integrity": (FOREFST, "integrity"), "ra-summary": (REFSANALYSIS, "summary"),
        "mlog-csv": (FOREFST, "mlog", "--csv")}


# ─── the boot-sector tests, this module's own (WAVEC_READING_bounds V4) ───────────────────────────────────────

_SPC = {1, 4, 8, 16, 32, 64, 128, 256, 512}


def _ror_add(b, n):
    ck = 0
    for off in range(3, n):
        if off not in (0x16, 0x17):
            ck = (((ck >> 1) | ((ck & 1) << 15)) + b[off]) & 0xFFFF
    return ck


def _v4_failures(b, ss, rounded):
    """The `RefsIsBootSectorOurs` tests an image can answer, in the driver's order (the checksum is evaluated only
    over a valid +0x14). `rounded` = the partition length in ss-sectors rounded down to 64 MiB, None when no GPT entry
    records the partition length (this module's default, see the docstring)."""
    out = []
    if b[3:11] != b"ReFS\0\0\0\0":
        out.append("oem")
    n = F.le16(b, 0x14)
    if not (0x57 < n <= ss):
        out.append("length")
    elif _ror_add(b, n) != F.le16(b, 0x16):
        out.append("checksum")
    if not (0x200 <= F.le32(b, 0x20) <= 0x1000):
        out.append("bytes_per_sector")
    if F.le32(b, 0x24) not in _SPC:
        out.append("sectors_per_cluster")
    t = F.le64(b, 0x18)
    if not (0 < t and (rounded is None or t <= rounded)):
        out.append("total_sectors")
    return out


def _seal(b):
    n = min(F.le16(b, 0x14), len(b))
    struct.pack_into("<H", b, 0x16, _ror_add(b, n))
    _fx(n != 512 or F._vbr_checksum(b, 512) == F.le16(b, 0x16), "fd._vbr_checksum disagrees with this module's")
    return b


def _self_consistent_at(b, ps, off):
    return ps + (F.le64(b, 0x18) - 1) * F.le32(b, 0x20) == off


# name: (edit, re-seal, the one V4 test the primary then fails)
PRIMARY_PLANTS = {
    "checksum": (lambda b: b.__setitem__(0x100, b[0x100] ^ 0x01), False, "checksum"),
    "serial": (lambda b: b.__setitem__(0x38, b[0x38] ^ 0x01), False, "checksum"),
    "oem": (lambda b: b.__setitem__(0x07, 0x20), True, "oem"),
    "length": (lambda b: struct.pack_into("<H", b, 0x14, 0x50), True, "length"),
    "bytes_per_sector": (lambda b: struct.pack_into("<I", b, 0x20, 0x100), True, "bytes_per_sector"),
    "sectors_per_cluster": (lambda b: struct.pack_into("<I", b, 0x24, 3), True, "sectors_per_cluster"),
    "total_sectors_zero": (lambda b: struct.pack_into("<Q", b, 0x18, 0), True, "total_sectors"),
    "total_sectors_over": (lambda b: struct.pack_into("<Q", b, 0x18, F.le64(b, 0x18) + 0x80), True, "total_sectors"),
}


# ─── volumes ──────────────────────────────────────────────────────────────────────────────────────────────────

def _gpt_entry_at(read, ps):
    """(GPT LBA size, partition length P) of the Basic-Data entry starting at ps, or (None, None) without a GPT."""
    for lba in (512, 4096):
        h = read(lba, 92)
        if h[:8] == b"EFI PART":
            plba, n, es = struct.unpack_from("<QII", h, 72)
            arr = read(plba * lba, min(n, 128) * es)
            for i in range(min(n, 128)):
                e = arr[i * es:(i + 1) * es]
                if e[:16] == GPT_BASIC_DATA and F.le64(e, 32) * lba == ps:
                    return lba, (F.le64(e, 40) + 1) * lba - ps
            raise RedFixtureError("no Basic-Data entry starts at 0x%x" % ps)
    return None, None


def _geometry(v):
    """ss, P, rounded and the expected backup offset of a volume, read from its bytes."""
    ss, p = _gpt_entry_at(v.read, v.geo.ps)
    prim = v.read(v.geo.ps, 512)
    if ss is None:                                       # raw image: P = the image after ps, no T test (default)
        ss, p, rounded = 512, os.path.getsize(v.path) - v.geo.ps, None
    else:
        rounded = (p // MIB64) * (MIB64 // ss)
    mount_read = v.geo.ps + (p // MIB64) * MIB64 - ss if p >= MIB64 else None
    t_minus_1 = v.geo.ps + (F.le64(prim, 0x18) - 1) * F.le32(prim, 0x20)
    return {"ss": ss, "P": p, "rounded": rounded, "mount_read": mount_read, "t_minus_1": t_minus_1,
            "backup": mount_read if mount_read is not None else t_minus_1}


def _pin_boot(v, expect_backup):
    """Primary passes every V4 test; an identical, self-consistent backup sits where this module expects it."""
    g = _geometry(v)
    _fx(g["backup"] == expect_backup, "%s: expected the backup at 0x%x, the geometry gives 0x%x"
        % (v.geo.kind, expect_backup, g["backup"]))
    prim, bk = v.read(v.geo.ps, 512), v.read(expect_backup, 512)
    _fx(_v4_failures(prim, g["ss"], g["rounded"]) == [], "%s: the primary boot sector fails %r"
        % (v.geo.kind, _v4_failures(prim, g["ss"], g["rounded"])))
    _fx(bk == prim and _self_consistent_at(bk, v.geo.ps, expect_backup), "%s: no identical self-consistent backup "
        "boot sector at 0x%x" % (v.geo.kind, expect_backup))
    return g


def _plant_primary(v, name, g):
    edit, reseal, test = PRIMARY_PLANTS[name]
    b = bytearray(v.read(v.geo.ps, 512))
    edit(b)
    v.write(v.geo.ps, bytes(_seal(b) if reseal else b))
    got = _v4_failures(v.read(v.geo.ps, 512), g["ss"], g["rounded"])
    _fx(got == [test], "%s: the planted primary fails %r, not only %r" % (name, got, test))
    _fx(v.read(v.geo.ps + 3, 4) == b"ReFS", "%s: the signature did not survive" % name)
    v.ops.append("primary boot sector: %s (fails the %s test)" % (name, test))
    return test


def _zero_primary(v):
    v.zero(v.geo.ps, 512)
    return "zeroed"


RAW = AB._Geo(kind="raw", ps=0, supb=AB.IMG.supb, backups=AB.IMG.backups, lo=AB.IMG.lo, hi=AB.IMG.hi,
              ot_root=AB.IMG.ot_root - AB.IMG.ps, ot_rows=AB.IMG.ot_rows, vbr=0, cli=["--partition-start", "0"])
KN = AB._Geo(kind="4kn", ps=0x1000000, cli=[])


def _carve_range(src, dst, start, length):
    """Hole-preserving copy of src[start:start+length] to dst (SEEK_DATA/SEEK_HOLE)."""
    fi = os.open(src, os.O_RDONLY)
    try:
        with open(dst, "wb") as out:
            out.truncate(length)
            pos, end = start, start + length
            while pos < end:
                try:
                    d = os.lseek(fi, pos, os.SEEK_DATA)
                except OSError:
                    break
                if d >= end:
                    break
                h = min(os.lseek(fi, d, os.SEEK_HOLE), end)
                os.lseek(fi, d, os.SEEK_SET)
                out.seek(d - start)
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


@contextlib.contextmanager
def _image_vol():
    with BI._image_vol() as v:
        _pin_boot(v, BK_A)
        yield v


@contextlib.contextmanager
def _raw_vol():
    """Base A's partition #2 as a raw partition image (no GPT): the image IS the partition, read at offset 0."""
    base = BI._image_or_skip(AB.BASE_IMAGE)
    with BI._scratch("raw") as d:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
        p = os.path.join(d, "target.raw")
        _carve_range(base, p, PS_A, P_A)
        _fx(os.stat(p).st_blocks * 512 < AB.MAX_SCRATCH_ALLOCATED, "the raw carve allocated too much")
        v = AB.Vol(RAW, p)
        v.pin()
        _pin_boot(v, BK_RAW)
        yield v


@contextlib.contextmanager
def _kn_vol():
    src = BI._image_or_skip(KN_IMAGE)
    with BI._scratch("4kn") as d:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
        p = os.path.join(d, "target.raw")
        AB._carve(src, p)
        alloc = os.stat(p).st_blocks * 512
        _fx(alloc < KN_MAX_ALLOCATED, "the 4Kn carve allocated %d bytes" % alloc)
        v = AB.Vol(KN, p)
        g = _geometry(v)
        _fx(g["ss"] == 4096 and F.le32(v.read(v.geo.ps, 512), 0x20) == 4096, "lab314_4kn is not a 4Kn GPT volume")
        _pin_boot(v, 0xFCFFF000)
        yield v


@contextlib.contextmanager
def _vol(kind, tmp_path=None):
    if kind == "image":
        with _image_vol() as v:
            yield v
    elif kind == "raw":
        with _raw_vol() as v:
            yield v
    else:
        v = BI._synthetic_vol(tmp_path, sub="syn")
        _pin_boot(v, v.geo.ps + (2048 - 1) * 512)       # 1 MiB, no 64 MiB boundary: the backup is at T-1 (2)
        yield v


_BASELINE = {}


def _baseline(kind, cmd):
    """(rc, stdout, stderr) of `cmd` on the volume as-is (one run per process)."""
    if (kind, cmd) not in _BASELINE:
        with _vol(kind) as v:
            _BASELINE[(kind, cmd)] = _vrun(v, *CMDS[cmd])
        _keep(_BASELINE[(kind, cmd)][0] == 0, "%s on %s as-is exits %d" % (cmd, kind, _BASELINE[(kind, cmd)][0]))
    return _BASELINE[(kind, cmd)]


# ─── matchers ─────────────────────────────────────────────────────────────────────────────────────────────────

def _hex_re(off):
    return re.compile(r"(?i)(?<![0-9a-z])0x0*%x(?![0-9a-z])" % off)


_PRIMARY = re.compile(r"(?i)\bprimary\b")
_BOOT = re.compile(r"(?i)\bboot[ -]sector\b|\bVBR\b")
_BACKUP = re.compile(r"(?i)\bbackup\b")
_READ = re.compile(r"(?i)\b(?:read|reads|reading|used|uses|using)\b")
_DAMAGED = re.compile(r"(?i)\b(?:damaged|fails?|failed|failing|unusable|not usable|invalid|zeroed|unreadable|"
                      r"cannot be (?:read|used)|does not pass|not a ReFS|not ReFS|no ReFS)\b")
_WOULD_NOT_MOUNT = re.compile(r"(?i)\bwould\s+not\s+mount\b")
_TEST_WORDS = {
    "checksum": r"checksum",
    "oem": r"\boem\b|signature|file.?system name|fs name|bytes? 3|\+0x0?3\b|\b0x03\b",
    "length": r"\+0x14\b|\b0x14\b|vbr size|boot.?sector size|checksummed|\blength\b|\bsize\b",
    "bytes_per_sector": r"\+0x20\b|\b0x20\b|bytes?\s*(?:per|/)\s*sector|sector size",
    "sectors_per_cluster": r"\+0x24\b|\b0x24\b|sectors? per cluster|cluster",
    "total_sectors": r"\+0x18\b|\b0x18\b|total sectors|sector count|volume (?:size|length)|partition",
    "zeroed": r"\boem\b|signature|zero|file.?system name|fs name|\+0x0?3\b|\b0x03\b|\bReFS\b",
}
_CLAUSE_START = re.compile(r"(?i)\bprimary\b|\bsector 0\b")
_SPAN_MAX = 4                                            # lines a wrapped statement or a short block may take
# how a copy found by Q20's search (3) was found: any of these words in the statement (Q20: "the output says how")
_HOW_SEARCH = re.compile(r"(?i)search|boundar|64\s*MiB|\bbelow\b|\bscan|\blower\b|\bdown\b|\bolder\b|\bstale\b|"
                         r"\bearlier\b|\bextend|\bbefore\b|\bprevious\b|\bprior\b|\bback\b")


def _indent(ln):
    return len(ln) - len(ln.lstrip(" "))


def _spans(text, need, max_lines=_SPAN_MAX):
    """Statements: for each line, the fewest consecutive lines from it (at most `max_lines`) that carry every item of
    `need` (a regex, or a predicate on the text), kept only when they do not hold without that first line -- so a
    neighbouring row of other output is never part of one -- then extended by up to 3 lines that continue it (indented
    deeper than its first line)."""
    lines = text.splitlines()

    def ok(i, j):
        s = "\n".join(lines[i:j + 1])
        return all((rx(s) if callable(rx) else rx.search(s)) for rx in need)

    out = []
    for i in range(len(lines)):
        j = next((j for j in range(i, min(i + max_lines, len(lines))) if ok(i, j)), None)
        if j is None or (i < j and ok(i + 1, j)):
            continue
        k = j
        while k + 1 < len(lines) and k - j < 3 and lines[k + 1].strip() and _indent(lines[k + 1]) > _indent(lines[i]):
            k += 1
        out.append("\n".join(lines[i:k + 1]))
    return out


def _primary_clauses(span):
    """The parts of a statement about the primary: from each 'primary' / 'sector 0' to the next 'backup' (or the end).
    The failed test is named there; "how the backup was found" follows the backup and is not part of it."""
    out = []
    for m in _CLAUSE_START.finditer(span):
        b = _BACKUP.search(span, m.end())
        out.append(span[m.start():b.start() if b else len(span)])
    return out


def n344_statements(text, offset, test=None):
    """Statements that say the primary boot sector is damaged and the volume was read from the backup boot sector at
    `offset` -- and, given `test`, name the failed test in the primary's clause (Q21)."""
    sp = _spans(text, (_hex_re(offset), _PRIMARY, _BOOT, _BACKUP, _READ, _DAMAGED))
    if test:
        tw = re.compile(_TEST_WORDS[test], re.I)
        sp = [s for s in sp if any(tw.search(c) for c in _primary_clauses(s))]
    return sp


_NOT_FOUND = re.compile(r"(?i)\bno\b[^.;\n]{0,60}\bfound\b|\bnot\s+found\b|\bnone\b[^.;\n]{0,30}\bfound\b|"
                        r"\bfound\s+none\b|\bcould\s+not\s+(?:find|locate)\b|\bcannot\s+(?:find|locate)\b")
_HEX_ANY = re.compile(r"(?i)(?<![0-9a-z])0x([0-9a-f]+)(?![0-9a-z])")


def none_found_statement(text, lo, hi):
    """The decided 'none found' output (Q20): the primary (or sector 0) named damaged, no backup boot sector found, and
    the range searched (at least two offsets inside the partition [lo, hi]), in one statement."""
    def range_named(s):
        return len({int(m.group(1), 16) for m in _HEX_ANY.finditer(s) if lo <= int(m.group(1), 16) <= hi}) >= 2
    return bool(_spans(text, (_CLAUSE_START, _BOOT, _DAMAGED, _BACKUP, _NOT_FOUND, range_named)))


_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _quoted_ids(text):
    """Quoted strings on the error lines (the refusal's signature / OEM id)."""
    return [q for ln in text.splitlines() if re.search(r"(?i)\berror\b", ln) for q in re.findall(r"'([^'\n]*)'", ln)]


def _past_the_oem_id(ids, oem):
    """Quoted strings that start with the OEM id and carry more than its 8 bytes (trailing blanks of the id aside)."""
    return [q for q in ids if q.startswith(oem) and len(q.rstrip(" ")) > len(oem.rstrip(" "))]


_V34 = re.compile(r"(?<![\d.])3\.4(?![\d.])")
_V314 = re.compile(r"(?<![\d.])3\.14(?![\d])")


def recorded_version_lines(text):
    return [ln for ln in text.splitlines() if _V34.search(ln) and re.search(r"(?i)version", ln)]


def decode_reason(text):
    return _spans(text, (_V314, re.compile(r"(?i)volume.?information|checkpoint|chkp"),
                         re.compile(r"(?i)\bbackup\b|boot[ -]sector")))


def _label_of(line):
    """A row's label: its text before the ':' or the column gap ('Volume serial')."""
    m = re.match(r"\s*([A-Za-z][A-Za-z ()/-]*?)\s*(?::|\s{2,})", line)
    _fx(m, "no label on %r" % line)
    return m.group(1)


def _labelled(out, label):
    return [ln for ln in out.splitlines() if re.match(r"\s*%s\b" % re.escape(label), ln, re.I)]


def _first_hex(line, label):
    m = _HEX_ANY.search(line, re.match(r"\s*%s" % re.escape(label), line, re.I).end())
    return int(m.group(1), 16) if m else None


def _bootstrap_rows(out, kinds=("SUPB", "CHKP")):
    """The superblock and checkpoint rows of summary's bootstrap section, each with its hash line."""
    lines, rows = out.splitlines(), []
    for i, ln in enumerate(lines):
        if re.match(r"\s*(%s)\s" % "|".join(kinds), ln):
            rows.append(ln.rstrip())
            if i + 1 < len(lines) and re.match(r"\s+[0-9a-f]{64}\s*$", lines[i + 1]):
                rows.append(lines[i + 1].strip())
    return rows


def _csv_rows(out):
    return [ln for ln in out.splitlines() if not re.search(r"(?i)boot[ -]sector|\bVBR\b", ln)]


def _why(rc, out, err, v):
    return _ctx(rc, out, err, v.ops)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N344 (a) -- a primary that fails a boot-sector test the image can answer is not used
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_A_CASES = [("checksum", c) for c in ("summary", "files", "ra-boot", "ra-supb")] + \
           [(p, c) for p in ("oem", "length", "bytes_per_sector", "sectors_per_cluster", "total_sectors_zero",
                             "total_sectors_over")
            for c in ("files", "ra-boot")]


# RED 1.13.2 N344(a): a primary boot sector that keeps its signature but fails a RefsIsBootSectorOurs test the image
# can answer (Q19) is not used: the output says the primary is damaged, names the failed test and that the volume was
# read from the backup boot sector found at offset 0x7cfffe00, and every command exits 2 (Q21; 36 Q3 A; 27.2); today
# the damaged primary is read (rc 0, or rc 1 on the implausible cluster size and on +0x20 = 0x100, where the
# superblock is looked for at the wrong offset) and nothing says so (the strict xfail mark removed: fixed in step C2,
# area bounds_b)
@pytest.mark.parametrize("plant,cmd", _A_CASES, ids=["%s-%s" % c for c in _A_CASES])
def test_n344a_a_primary_failing_a_boot_sector_test_is_replaced_by_the_backup(plant, cmd):
    with _image_vol() as v:
        test = _plant_primary(v, plant, _geometry(v))
        rc, out, err = _vrun(v, *CMDS[cmd])
    st = n344_statements(out + "\n" + err, BK_A, test)
    assert st, "%s: no statement says the primary boot sector is damaged (%s test) and the volume was read from the " \
        "backup boot sector at 0x%x" % (cmd, test, BK_A) + _why(rc, out, err, v)
    assert not _WOULD_NOT_MOUNT.search("\n".join(st)), "the statement carries the read-once 'would not mount' " \
        "clause (Q21): %r" % st
    assert rc == 2, "%s must exit 2 when the volume is read from the backup boot sector (rc=%d)" % (cmd, rc) + \
        _why(rc, out, err, v)


def _serial_label():
    rows = [ln for ln in _baseline("image", "summary")[1].splitlines() if re.search(r"(?i)\bserial\b", ln)
            and _HEX_ANY.search(ln)]
    _fx(len(rows) == 1, "base A's summary prints one serial row: %r" % rows)
    return _label_of(rows[0])


# RED 1.13.2 N344(a): the boot-sector fields come from the copy the volume is read from: with the primary's serial
# byte flipped (its checksum fails) summary prints the backup's serial 0x504a8ba64a8b8804; today it prints the damaged
# primary's 0x504a8ba64a8b8805 (the strict xfail mark removed: fixed in step C2, area bounds_b)
def test_n344a_summary_prints_the_backup_boot_sectors_fields():
    label = _serial_label()                              # the as-is row's label (critic: not the first 'serial' line)
    with _image_vol() as v:
        good = F.le64(v.read(PS_A, 512), 0x38)
        _plant_primary(v, "serial", _geometry(v))
        bad = F.le64(v.read(PS_A, 512), 0x38)
        rc, out, err = _vrun(v, FOREFST, "summary")
    serial = _labelled(out, label)
    _keep(serial, "summary prints the %r row" % label + _why(rc, out, err, v))
    assert all(_first_hex(ln, label) == good for ln in serial), \
        "the %r row shows the damaged primary's 0x%x, not the backup's 0x%x: %r" % (label, bad, good, serial)


# RED 1.13.2 N344(a): the volume length comes from the boot sector the volume is read from (B3 Q16 with N344): a
# primary whose total sectors exceed the 64 MiB-rounded partition is not used, so summary's superblock and checkpoint
# rows are the volume's as-is (backup superblocks at LCN 0x7bffd, 0x7bffe); today the primary's length puts them at
# 0x7c000d and 0x7c000e and calls both missing (the strict xfail mark removed: fixed in step C2, area bounds_b)
def test_n344a_the_volume_length_comes_from_the_backup_boot_sector():
    base = _bootstrap_rows(_baseline("image", "summary")[1])
    _fx(len([r for r in base if r.lstrip().startswith("SUPB")]) == 3 and any("0x7bffd" in r for r in base),
        "base A's summary lists 3 superblock rows: %r" % base)
    with _image_vol() as v:
        _plant_primary(v, "total_sectors_over", _geometry(v))
        rc, out, err = _vrun(v, FOREFST, "summary")
    got = _bootstrap_rows(out)
    assert got == base, "superblock/checkpoint rows differ from the volume's as-is:\n%s\nexpected:\n%s" % (
        "\n".join(got), "\n".join(base)) + _why(rc, out, err, v)


# RED 1.13.2 N344(a): on a raw image smaller than 64 MiB the mount-read position does not exist; the backup is the
# damaged primary's own T-1 (Q20 position 2: 0xffe00 on the 1 MiB synthetic volume) and the volume is read from it:
# the statement and exit 2; today the damaged primary is read with exit 0 and nothing says so (the strict xfail mark
# removed: fixed in step C2, area bounds_b)
@pytest.mark.parametrize("cmd", ["files", "ra-supb"])
def test_n344a_raw_image_backup_at_the_primarys_own_last_sector(cmd, tmp_path):
    with _vol("synthetic", tmp_path) as v:
        test = _plant_primary(v, "checksum", _geometry(v))
        rc, out, err = _vrun(v, *CMDS[cmd])
    assert n344_statements(out + "\n" + err, 0xFFE00, test), "%s: no statement names the backup boot sector at " \
        "0xffe00 as the copy read" % cmd + _why(rc, out, err, v)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _why(rc, out, err, v)


# RED 1.13.2 Q-M2 (N344, decision 43): a volume read from a backup whose version (3.4) predates the volume's: the
# version is printed as recorded (3.4) and, since $VOLUME_INFORMATION and the checkpoint's 0x600 flags show 3.14, the
# volume is decoded as 3.14 with the reason stated; today the damaged primary's 3.14 is printed and the backup's
# version appears nowhere (the strict xfail mark removed: fixed in step C2, area bounds_b)
def test_n344_qm2_an_older_backup_prints_its_version_and_says_why_3_14_decodes():
    with _image_vol() as v:
        _plant_primary(v, "checksum", _geometry(v))
        b = bytearray(v.read(BK_A, 512))
        b[0x29] = 4
        v.write(BK_A, bytes(_seal(b)))
        _fx(_v4_failures(v.read(BK_A, 512), 512, T_A) == [], "the 3.4 backup does not pass")
        v.ops.append("backup boot sector: version 3.4, re-sealed")
        rc, out, err = _vrun(v, FOREFST, "summary")
    text = out + "\n" + err
    assert recorded_version_lines(text), "no line prints the version recorded in the backup boot sector (3.4)" + \
        _why(rc, out, err, v)
    assert decode_reason(text), "no statement says the volume is decoded as 3.14 and why ($VOLUME_INFORMATION / " \
        "the checkpoint flags)" + _why(rc, out, err, v)


def test_n344_qm2_control_the_listing_decodes_as_3_14():
    """Decoded as 3.14 (decision 43): `files` lists what it lists on the volume as-is. Today the damaged 3.14 primary
    is read; after the fix the 3.4 backup is, and this listing must not change. (Critic: on base A the listing does
    not depend on the version -- a valid 3.4 primary gives the same rows, probe2 -- so the decoding itself is
    checked through `mlog` below.)"""
    base = _baseline("image", "files")
    with _image_vol() as v:
        _plant_primary(v, "checksum", _geometry(v))
        b = bytearray(v.read(BK_A, 512))
        b[0x29] = 4
        v.write(BK_A, bytes(_seal(b)))
        rc, out, err = _vrun(v, FOREFST, "files")
    assert _csv_rows(out) == _csv_rows(base[1]) and len(_csv_rows(out)) > 10, _why(rc, out, err, v)


def test_n344_qm2_control_mlog_decodes_with_the_3_14_redo_table():
    """Decision 43 names the decoding: the MLog redo tables. `mlog --csv` on the volume read from the 3.4 backup lists
    what it lists as-is (the 3.14 opcode names). It discriminates: read with the 3.4 table (a valid 3.4 primary), 77
    of base A's 146 rows change (`OPEN_TABLE_FROM_TABLE_PATH` -> `OPEN_TABLE`; critic probe1). Today the damaged 3.14
    primary is read; after the fix the 3.4 backup is, decoded as 3.14. Statements go to stderr in an export (LB10)."""
    base = _baseline("image", "mlog-csv")
    with _image_vol() as v:
        _plant_primary(v, "checksum", _geometry(v))
        b = bytearray(v.read(BK_A, 512))
        b[0x29] = 4
        v.write(BK_A, bytes(_seal(b)))
        rc, out, err = _vrun(v, *CMDS["mlog-csv"])
    assert len(_csv_rows(out)) > 100 and _csv_rows(out) == _csv_rows(base[1]), \
        "mlog is not decoded as on the volume as-is (the 3.14 redo table)" + _why(rc, out, err, v)


@pytest.mark.parametrize("cmd", ["summary", "ra-boot", "files"])
def test_n344_control_a_valid_primary_that_differs_from_its_backup_is_read(cmd):
    """The primary passes every test but differs from the backup (its serial byte flipped, re-sealed): the primary
    is the copy read (refs.sys reads sector 0, K1) -- its serial is shown, no N344 statement, never exit 1. Guards a
    fix that prefers the backup whenever the copies differ."""
    with _image_vol() as v:
        g = _geometry(v)
        b = bytearray(v.read(PS_A, 512))
        b[0x38] ^= 0x01
        v.write(PS_A, bytes(_seal(b)))
        _fx(_v4_failures(v.read(PS_A, 512), g["ss"], g["rounded"]) == [], "the re-sealed primary must pass")
        mine = F.le64(v.read(PS_A, 512), 0x38)
        theirs = F.le64(v.read(BK_A, 512), 0x38)
        v.ops.append("primary: serial byte flipped, re-sealed (valid, differs from the backup)")
        rc, out, err = _vrun(v, *CMDS[cmd])
    assert rc != 1 and not n344_statements(out + "\n" + err, BK_A), _why(rc, out, err, v)
    if cmd != "files":                                   # both tools label the row 'Volume serial'
        rows = _labelled(out, _serial_label())
        assert rows and all(_hex_re(mine).search(ln) and not _hex_re(theirs).search(ln) for ln in rows), \
            "the serial shown is not the primary's 0x%x: %r" % (mine, rows) + _why(rc, out, err, v)


@pytest.mark.parametrize("kind,cmd", [("image", "summary"), ("image", "files"), ("image", "ra-boot"),
                                      ("raw", "files"), ("synthetic", "files"), ("synthetic", "ra-supb")])
def test_n344_control_an_intact_primary_is_read_and_raises_no_backup_statement(kind, cmd, tmp_path):
    """Intact copies: exit 0, no N344 statement. On the raw images (no GPT) this pins the default: the T test is not
    made against the image length, so the 1 MiB synthetic volume stays intact."""
    with _vol(kind, tmp_path) as v:
        bk = _geometry(v)["backup"]
        rc, out, err = _vrun(v, *CMDS[cmd])
    assert rc == 0 and not n344_statements(out + "\n" + err, bk), _why(rc, out, err, v)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N344 (b) -- a zeroed primary: the bounded search for a self-consistent backup (decision 36 Q3 A, Q20)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_B_CASES = [(k, c) for k in ("image", "raw") for c in ("summary", "files", "ra-boot", "ra-supb")] + \
           [("image", "integrity"), ("image", "ra-summary")]     # critic: two more commands on the class's path


def _vrun_tb(v, tool, *args):
    """As _vrun, but a traceback is returned, not raised: refsanalysis `chkp` and `containers` call parse_vbr without
    a guard (ra cmd_chkp, cmd_containers), so on a zeroed primary today's defect IS a traceback."""
    cmd = [sys.executable, "-B", tool, v.path] + list(args) + list(v.geo.cli)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=BI.TIMEOUT, cwd=os.path.dirname(v.path))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    return r.returncode, r.stdout, r.stderr


_TRACEBACK = "Traceback (most recent call last)"


# RED 1.13.2 N344(b): a zeroed primary boot sector is replaced by the backup Q20's search finds at the driver's mount-
# read position (ps + floor(P / 64 MiB) x 64 MiB - 512; P from the GPT entry, else the image after ps): the statement
# names the primary damaged, the failed test and the backup's offset (0x7cfffe00; 0x7bfffe00 in the raw partition
# image), every command exits 2; today every command stops with exit 1 ('partition does not contain ReFS', 'no ReFS
# boot sector', 'not ReFS', 'no ReFS or GPT signature') (the strict xfail mark removed: fixed in step C2, area
# bounds_b)
@pytest.mark.parametrize("kind,cmd", _B_CASES, ids=["%s-%s" % c for c in _B_CASES])
def test_n344b_a_zeroed_primary_is_replaced_by_the_backup_the_search_finds(kind, cmd):
    with _vol(kind) as v:
        bk = _geometry(v)["backup"]
        _fx(bk == (BK_A if kind == "image" else BK_RAW), "backup position")
        test = _zero_primary(v)
        rc, out, err = _vrun(v, *CMDS[cmd])
    st = n344_statements(out + "\n" + err, bk, test)
    assert st, "%s: no statement says the primary boot sector is damaged and the volume was read from the backup boot " \
        "sector at 0x%x" % (cmd, bk) + _why(rc, out, err, v)
    assert not _WOULD_NOT_MOUNT.search("\n".join(st)), "the read-once 'would not mount' clause (Q21): %r" % st
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _why(rc, out, err, v)


# RED 1.13.2 N344(b): the volume read from the backup boot sector is the volume as-is: `files` lists exactly what it
# lists on the unplanted volume (statement lines aside); today exit 1 and no listing (the strict xfail mark removed:
# fixed in step C2, area bounds_b)
def test_n344b_the_listing_read_from_the_backup_is_the_volumes():
    base = _baseline("image", "files")
    with _image_vol() as v:
        _zero_primary(v)
        rc, out, err = _vrun(v, FOREFST, "files")
    assert len(_csv_rows(out)) > 10 and _csv_rows(out) == _csv_rows(base[1]), \
        "the listing differs from the volume's as-is" + _why(rc, out, err, v)


# RED 1.13.2 N344(b): the backup superblock slots come from the boot sector the volume is read from (fd
# _supb_backup_lcns and _scan_backup_copies read T from the primary at ps): summary's superblock and checkpoint rows
# equal the volume's as-is; today exit 1 and no rows (the strict xfail mark removed: fixed in step C2, area bounds_b)
def test_n344b_superblock_backups_are_located_from_the_backup_boot_sector():
    base = _bootstrap_rows(_baseline("image", "summary")[1])
    with _image_vol() as v:
        _zero_primary(v)
        rc, out, err = _vrun(v, FOREFST, "summary")
    got = _bootstrap_rows(out)
    assert got == base, "superblock/checkpoint rows:\n%s\nexpected:\n%s" % ("\n".join(got), "\n".join(base)) + \
        _why(rc, out, err, v)


# RED 1.13.2 N344(b): integrity's own boot-sector read (fd cmd_integrity: `f.seek(ps); bs = f.read(512)`, the checksum
# type at +0x2A) takes the copy the volume is read from: with the primary zeroed its 'Checksum type' row is the as-is
# one (CRC64), not the zeroed sector's; today exit 1 and no row (the strict xfail mark removed: fixed in step C2, area
# bounds_b)
def test_n344b_integrity_takes_the_checksum_type_from_the_backup_boot_sector():
    rx = re.compile(r"(?i)^\s*checksum type\b")
    want = [ln.strip() for ln in _baseline("image", "integrity")[1].splitlines() if rx.match(ln)]
    _fx(len(want) == 1 and "CRC64" in want[0], "base A's integrity prints one CRC64 checksum-type row: %r" % want)
    with _image_vol() as v:
        _zero_primary(v)
        rc, out, err = _vrun(v, *CMDS["integrity"])
    got = [ln.strip() for ln in out.splitlines() if rx.match(ln)]
    value = want[0].split(":", 1)[1].split()[0]          # 'CRC64': the value, not the row's form
    assert got and all((r.split(":", 1)[1].split() or [""])[0] == value for r in got if ":" in r), \
        "checksum-type rows %r, expected the value %r" % (got, value) + _why(rc, out, err, v)


# RED 1.13.2 N344(b): refsanalysis `chkp` and `containers` read the boot sector through parse_vbr without a guard:
# with a zeroed primary both stop with a Python traceback (ValueError 'partition does not contain ReFS'); decided: the
# volume is read from the backup boot sector at 0x7cfffe00, the statement, exit 2 (every command) (the strict xfail
# mark removed: fixed in step C2, area bounds_b)
@pytest.mark.parametrize("cmd", ["chkp", "containers"])
def test_n344b_refsanalysis_chkp_and_containers_read_the_backup(cmd):
    with _image_vol() as v:
        _zero_primary(v)
        rc, out, err = _vrun_tb(v, REFSANALYSIS, cmd)
    assert _TRACEBACK not in err, "ra %s stops with a traceback on a zeroed primary: %s" % (cmd, err[-600:])
    assert n344_statements(out + "\n" + err, BK_A, "zeroed"), "ra %s: no statement names the backup boot sector at " \
        "0x%x as the copy read" % (cmd, BK_A) + _why(rc, out, err, v)
    assert rc == 2, "ra %s must exit 2 (rc=%d)" % (cmd, rc) + _why(rc, out, err, v)


# RED 1.13.2 N344(b): 4Kn: the mount-read position uses the GPT's 4096-byte LBA (ss = the GPT LBA size, Q20): on
# lab314_4kn the backup at ps + 63 x 64 MiB - 4096 = 0xfcfff000 is found and read, exit 2; today exit 1 (the strict
# xfail mark removed: fixed in step C2, area bounds_b)
def test_n344b_4kn_the_backup_at_the_4096_byte_mount_read_position():
    with _kn_vol() as v:
        _zero_primary(v)
        rc, out, err = _vrun(v, FOREFST, "files")
    assert n344_statements(out + "\n" + err, 0xFCFFF000, "zeroed"), "no statement names the backup boot sector at " \
        "0xfcfff000 as the copy read" + _why(rc, out, err, v)
    assert rc == 2, "rc=%d" % rc + _why(rc, out, err, v)


KN_RAW = AB._Geo(kind="raw4kn", ps=0, cli=["--partition-start", "0"])
KN_RAW_BK = 0xFBFFF000                                   # floor(P / 64 MiB) x 64 MiB - 4096 = the copy's own T-1


# RED 1.13.2 N344(b): Q20's '-512 and -4096' where no GPT gives the sector size: lab314_4kn's partition as a raw image
# (P = 0xfef00000), primary zeroed: the 512-byte position 0xfbfffe00 holds nothing and the backup at 0xfbfff000
# (-4096) is found and read, exit 2; today exit 1 (the strict xfail mark removed: fixed in step C2, area bounds_b)
def test_n344b_raw_4kn_image_the_backup_at_minus_4096():
    src = BI._image_or_skip(KN_IMAGE)
    with open(src, "rb") as fh:
        ss, p = _gpt_entry_at(lambda o, n: (fh.seek(o), fh.read(n))[1], 0x1000000)
    _fx(ss == 4096 and (p // MIB64) * MIB64 - 4096 == KN_RAW_BK,
        "lab314_4kn's partition geometry (ss %r, P %r)" % (ss, p))
    with BI._scratch("raw4kn") as d:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
        path = os.path.join(d, "target.raw")
        _carve_range(src, path, 0x1000000, p)
        _fx(os.stat(path).st_blocks * 512 < KN_MAX_ALLOCATED, "the raw 4Kn carve allocated too much")
        v = AB.Vol(KN_RAW, path)
        prim = v.read(0, 512)
        _fx(_v4_failures(prim, 4096, None) == [] and v.read(KN_RAW_BK, 512) == prim
            and _self_consistent_at(prim, 0, KN_RAW_BK) and not any(v.read(KN_RAW_BK + 4096 - 512, 512)),
            "no identical self-consistent backup at 0x%x, or the -512 position is not free" % KN_RAW_BK)
        rc0, out0, err0 = _vrun(v, FOREFST, "files")
        _keep(rc0 == 0, "files on the raw 4Kn image as-is exits %d" % rc0 + _why(rc0, out0, err0, v))
        _zero_primary(v)
        rc, out, err = _vrun(v, FOREFST, "files")
    assert n344_statements(out + "\n" + err, KN_RAW_BK, "zeroed"), "no statement names the backup boot sector at " \
        "0x%x as the copy read" % KN_RAW_BK + _why(rc, out, err, v)
    assert rc == 2, "rc=%d" % rc + _why(rc, out, err, v)


def _plant_stale(v, inconsistent):
    """A self-consistent copy one 64 MiB boundary down (an extend's old backup, N-3); at (1) either nothing (zeroed)
    or a copy that passes every test but is not self-consistent (its T' ends 16 MiB earlier)."""
    good = v.read(BK_A, 512)
    _fx(not any(v.read(STALE_A, 512)), "0x%x is not free on base A" % STALE_A)
    _zero_primary(v)
    if inconsistent:
        b = bytearray(good)
        struct.pack_into("<Q", b, 0x18, T_A - 0x8000)
        v.write(BK_A, bytes(_seal(b)))
        b = v.read(BK_A, 512)
        _fx(_v4_failures(b, 512, T_A) == [] and not _self_consistent_at(b, PS_A, BK_A), "the copy at (1) must pass "
            "every test and not be self-consistent")
        v.ops.append("copy at 0x%x: T' = 0x%x (not self-consistent)" % (BK_A, T_A - 0x8000))
    else:
        v.zero(BK_A, 512)
    b = bytearray(good)
    struct.pack_into("<Q", b, 0x18, T_STALE)
    v.write(STALE_A, bytes(_seal(b)))
    b = v.read(STALE_A, 512)
    _fx(_v4_failures(b, 512, T_A) == [] and _self_consistent_at(b, PS_A, STALE_A), "stale copy")
    v.ops.append("self-consistent copy at 0x%x (T' = 0x%x)" % (STALE_A, T_STALE))


# RED 1.13.2 N344(b): Q20 position (3): with sector 0 and the copy at the mount-read position zeroed, the search goes
# down the 64 MiB boundaries and reads the self-consistent copy at 0x78fffe00, and says it was found by the search
# (Q20: the output says how), exit 2; today exit 1 (the strict xfail mark removed: fixed in step C2, area bounds_b)
def test_n344b_the_search_goes_down_the_64_mib_boundaries():
    with _image_vol() as v:
        _plant_stale(v, inconsistent=False)
        rc, out, err = _vrun(v, FOREFST, "summary")
    st = n344_statements(out + "\n" + err, STALE_A, "zeroed")
    assert st, "no statement names the copy at 0x%x as the one read" % STALE_A + _why(rc, out, err, v)
    assert any(_HOW_SEARCH.search(s) for s in st), "the statement does not say the copy was found by the search " \
        "below the mount-read position (Q20: the output says how it was found): %r" % st
    assert rc == 2, "rc=%d" % rc + _why(rc, out, err, v)


# RED 1.13.2 N344(b): Q20: only a self-consistent copy is accepted -- the copy at the mount-read position passes every
# test but its T' puts its own last sector at 0x7bfffe00, so it is refused and the volume is read from the self-
# consistent copy at 0x78fffe00 (the statement says how it was found), whose length places the backup superblocks at
# LCN 0x77ffd/0x77ffe; today exit 1 (the strict xfail mark removed: fixed in step C2, area bounds_b)
def test_n344b_a_copy_that_is_not_self_consistent_is_refused():
    with _image_vol() as v:
        _plant_stale(v, inconsistent=True)
        rc, out, err = _vrun(v, FOREFST, "summary")
    st = n344_statements(out + "\n" + err, STALE_A, "zeroed")
    assert st, "no statement names the copy at 0x%x as the one read" % STALE_A + _why(rc, out, err, v)
    assert any(_HOW_SEARCH.search(s) for s in st), "the statement does not say how the copy was found (Q20): %r" % st
    slots = [ln for ln in out.splitlines() if re.search(r"(?i)\bSUPB\b|superblock", ln) and _hex_re(0x77FFD).search(ln)]
    assert slots, "the superblock slots are not the read copy's (LCN 0x77ffd)" + _why(rc, out, err, v)


# RED 1.13.2 N344(b): no copy anywhere (sector 0 and the backup zeroed): exit 1 (kept), and the error says the primary
# boot sector is damaged, that no backup boot sector was found, and the range searched (Q20); today 'partition does
# not contain ReFS (VBR signature: '')' (the strict xfail mark removed: fixed in step C2, area bounds_b)
@pytest.mark.parametrize("cmd", ["summary", "files"])
def test_n344b_none_found_names_the_range_searched(cmd):
    with _image_vol() as v:
        _zero_primary(v)
        v.zero(BK_A, 512)
        rc, out, err = _vrun(v, *CMDS[cmd])
    _keep(rc == 1, "%s exits 1 when no copy is found (rc=%d)" % (cmd, rc) + _why(rc, out, err, v))
    assert none_found_statement(err + "\n" + out, PS_A, PS_A + P_A), "the error does not say the primary is damaged, " \
        "no backup was found and the range searched" + _why(rc, out, err, v)


# RED 1.13.2 N344(b): no copy anywhere, refsanalysis `chkp` / `containers`: exit 1 and the none-found error (Q20), not
# a Python traceback; today both stop with a traceback (parse_vbr unguarded) (the strict xfail mark removed: fixed in
# step C2, area bounds_b)
@pytest.mark.parametrize("cmd", ["chkp", "containers"])
def test_n344b_none_found_refsanalysis_chkp_and_containers_exit_1_without_a_traceback(cmd):
    with _image_vol() as v:
        _zero_primary(v)
        v.zero(BK_A, 512)
        rc, out, err = _vrun_tb(v, REFSANALYSIS, cmd)
    assert _TRACEBACK not in err, "ra %s stops with a traceback: %s" % (cmd, err[-600:])
    assert rc == 1, "ra %s must exit 1 when no copy is found (rc=%d)" % (cmd, rc) + _why(rc, out, err, v)
    assert none_found_statement(err + "\n" + out, PS_A, PS_A + P_A), "the error does not say the primary is damaged, " \
        "no backup was found and the range searched" + _why(rc, out, err, v)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N142 -- the refusal text quotes the 8-byte OEM id only (Q23)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# RED 1.13.2 N142: the NTFS refusal quotes the 8-byte OEM id ('NTFS    ', bs[3:11]); today it quotes bs[3:15] and
# prints a NUL and the bytes 0x02 0x08 (bytes per sector and sectors per cluster); exit 1 unchanged (Q23) (the strict
# xfail mark removed: fixed in step C2, area bounds_b)
@pytest.mark.parametrize("image", ["step3c/win11ntfs.raw", "step5/win11ntfstestmftecmd.raw"])
def test_n142_the_ntfs_refusal_quotes_the_8_byte_oem_id(image, tmp_path):
    path = BI._image_or_skip(image)
    rc, out, err = BI._run(FOREFST, path, "summary", cwd=str(tmp_path))
    _keep(rc == 1 and re.search(r"\bNTFS\b", err), "summary refuses the NTFS partition with exit 1 (rc=%d): %r"
          % (rc, err[-400:]))
    assert not _CTRL.search(out + err), "control bytes reach the examiner: %r" % _CTRL.findall(out + err)
    ids = _quoted_ids(err)
    assert not _past_the_oem_id(ids, "NTFS"), "the quoted id runs past the 8-byte OEM id: %r" % ids


# RED 1.13.2 N142: the class: a non-ReFS, non-NTFS boot sector (a FAT OEM id 'MSDOS5.0' followed by 00 02 08 20) with
# no backup is quoted by its 8-byte OEM id only, without control bytes, by forefst (parse_vbr's other branch) and
# refsanalysis (`_validate_vbr`, bootedit read); today both print bs[3:15]: 'MSDOS5.0\x00\x02\x08 ' (the strict xfail
# mark removed: fixed in step C2, area bounds_b)
@pytest.mark.parametrize("cmd", ["forefst-summary", "ra-bootedit-read"])
def test_n142_class_a_foreign_boot_sector_is_quoted_by_its_oem_id_only(cmd):
    with _image_vol() as v:
        b = bytearray(v.read(PS_A, 512))
        b[3:15] = b"MSDOS5.0\x00\x02\x08\x20"
        v.write(PS_A, bytes(b))
        v.zero(BK_A, 512)
        v.ops.append("primary: FAT OEM id; backup zeroed")
        rc, out, err = (_vrun(v, FOREFST, "summary") if cmd == "forefst-summary"
                        else _vrun(v, REFSANALYSIS, "bootedit", "read"))
    _keep(rc == 1, "%s refuses the volume with exit 1 (rc=%d)" % (cmd, rc) + _why(rc, out, err, v))
    assert not _CTRL.search(out + err), "control bytes reach the examiner: %r" % _CTRL.findall(out + err)
    ids = _quoted_ids(err)
    assert not _past_the_oem_id(ids, "MSDOS5.0"), "the quoted id runs past the 8-byte OEM id: %r" % ids


def test_n142_control_refsanalysis_refuses_ntfs_without_control_bytes(tmp_path):
    path = BI._image_or_skip("step3c/win11ntfs.raw")
    rc, out, err = BI._run(REFSANALYSIS, path, "boot", cwd=str(tmp_path))
    assert rc == 1 and re.search(r"\bNTFS\b", err) and not _CTRL.search(out + err), (rc, out[-400:], err[-400:])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The matchers accept the decided forms and refuse today's lines
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_c2_bounds_b_matchers_accept_the_decided_forms_and_reject_the_1131_lines():
    decided = ("[forefst] WARNING: the primary boot sector at offset 0x1000000 is damaged (it fails its checksum); "
               "the volume was read from the backup boot sector found at offset 0x7cfffe00 (the position refs.sys "
               "reads it at); refs.sys reads the backup boot sector only when reading sector 0 fails")
    assert n344_statements(decided, BK_A, "checksum") and n344_statements(decided.upper(), BK_A, "checksum")
    wrapped = ("  [WARN] primary boot sector damaged (bytes 3..10 are not the ReFS OEM id);\n"
               "         the volume was read from the backup boot sector found at offset 0x7CFFFE00\n"
               "         (by the search at 64 MiB boundaries)")
    assert n344_statements(wrapped, BK_A, "zeroed") and n344_statements(wrapped, BK_A, "oem")
    assert not n344_statements(decided, STALE_A) and not n344_statements(decided, BK_A, "sectors_per_cluster")
    assert _WOULD_NOT_MOUNT.search("refs.sys uses the backup only when sector 0 cannot be read, so it would not mount")
    today = ("  VBR primary      LBA 0 (offset 0x1000000)  — checksum FAILED (stored 0x5489, computed 0x548B)\n"
             "      6759cfa525f38b9a043ebb52f83ffcfcdc7994f0652f027a6b687b3ea37ba73f\n"
             "  VBR backup       LBA 4063231 (offset 0x7cfffe00)  — DIFFERS, checksum OK\n"
             "  [WARN] the primary boot sector (VBR) at LBA 0 (offset 0x1000000) fails its checksum (stored 0x5489, "
             "computed 0x548B)\n"
             "  VBR backup       LBA 4063231 (offset 0x7cfffe00)  — = primary, checksum OK\n"
             "  [WARN] the backup boot sector at LBA 65011839 (offset 0x7c100fe00) is missing or unreadable\n"
             "forefst: error: partition does not contain ReFS (VBR signature: '')\n"
             "refsanalysis: error: no ReFS boot sector at offset 0x1000000")
    assert not n344_statements(today, BK_A) and not none_found_statement(today, PS_A, PS_A + P_A)
    # critic: a neighbouring row of other output names no test ('cluster_size=4096' after the statement in `files`)
    generic = ("[forefst] WARNING: the primary boot sector is damaged (it fails a RefsIsBootSectorOurs test); the "
               "volume was read from the backup boot sector found at offset 0x7cfffe00\n"
               "[forefst] ReFS 3.14 | 24 objects | cluster_size=4096")
    assert n344_statements(generic, BK_A) and not n344_statements(generic, BK_A, "sectors_per_cluster")
    # ... nor does "how it was found", after the backup: the test is named in the primary's clause
    how = ("  [WARN] the primary boot sector is damaged; the volume was read from the backup boot sector found at "
           "offset 0x7cfffe00 (the partition length rounded down to 64 MiB, minus one sector)")
    assert n344_statements(how, BK_A) and not n344_statements(how, BK_A, "total_sectors") \
        and not n344_statements(how, BK_A, "length")
    # either order, a short block, a deeper-indented continuation; the summary heading above is not part of it
    after = ("  (offsets below are ABSOLUTE in the image file; partition starts at 0x1000000)\n"
             "  [WARN] the volume was read from the backup boot sector found at offset 0x7cfffe00: the primary boot "
             "sector fails its total sectors (+0x18) test")
    assert n344_statements(after, BK_A, "total_sectors") and len(n344_statements(after, BK_A)[0].splitlines()) == 1
    assert not n344_statements(after.splitlines()[0] + "\n  [WARN] the primary boot sector is damaged; the volume "
                               "was read from the backup boot sector found at offset 0x7cfffe00", BK_A, "total_sectors")
    block = ("  Boot sector:\n"
             "    primary at offset 0x1000000: damaged, +0x20 bytes per sector 0x100 out of range\n"
             "    the volume was read from the backup\n"
             "    found at offset 0x7cfffe00 (the mount-read position)")
    assert n344_statements(block, BK_A, "bytes_per_sector") and not n344_statements(block, BK_A, "checksum")
    # a copy found by the search says so (Q20); the mount-read wording alone does not
    stale = ("  [WARN] the primary boot sector is damaged (zeroed); the volume was read from the backup boot sector "
             "found at offset 0x78fffe00\n            (by the search down the 64 MiB boundaries)")
    assert any(_HOW_SEARCH.search(s) for s in n344_statements(stale, STALE_A, "zeroed"))
    assert not any(_HOW_SEARCH.search(s) for s in n344_statements(decided.replace("0x7cfffe00", "0x78fffe00"),
                                                                   STALE_A))
    none_wrapped = ("forefst: error: the primary boot sector at offset 0x1000000 is damaged (it is zeroed) and no "
                    "backup boot sector was found;\n    searched 0x7cfffe00 and each 64 MiB boundary down to 0x1000000")
    assert none_found_statement(none_wrapped, PS_A, PS_A + P_A)
    none = ("forefst: error: the primary boot sector at offset 0x1000000 is damaged (bytes 3..10 are zero); no backup "
            "boot sector was found: searched 0x7cfffe00, 0x7cfff000 and every 64 MiB boundary down to 0x1000000")
    assert none_found_statement(none, PS_A, PS_A + P_A)
    # N142
    assert _CTRL.search("forefst: error: partition contains NTFS, not ReFS (signature: 'NTFS    \x00\x02\x08')")
    assert _quoted_ids("forefst: error: partition contains NTFS, not ReFS (signature: 'NTFS    ')") == ["NTFS    "]
    assert not _past_the_oem_id(["NTFS    "], "NTFS") and not _past_the_oem_id(["NTFS", "ReFS"], "NTFS")
    assert not _past_the_oem_id(["MSDOS5.0", "ReFS"], "MSDOS5.0")
    assert _past_the_oem_id(["NTFS    \x00\x02\x08"], "NTFS") and _past_the_oem_id(["MSDOS5.0\x00\x02\x08 "], "MSDOS5.0")
    assert not _CTRL.search("forefst: error: partition contains NTFS, not ReFS (signature: 'NTFS')\n")
    # Q-M2
    vers = ("  ReFS version:       3.4 (as recorded in the backup boot sector)\n"
            "  [NOTE] decoded as ReFS 3.14: $VOLUME_INFORMATION and the checkpoint flags (0x600) show 3.14; the backup "
            "boot sector keeps the version from before an upgrade")
    assert recorded_version_lines(vers) and decode_reason(vers)
    assert not recorded_version_lines("  ReFS version:       3.14\n  Volume version:     3.14\n  ReFS 3.40")
    assert not decode_reason("  ReFS version:       3.14\n  Flags:              0x682\n  Volume state:       NATIVE v3.14")
    # group2b's per-copy rows (N239): the N344 statement names both copies, so it is no row of either copy; today's
    # own-label rows are unchanged (decision 44's pre-sanctioned form edit, RED_C2_bounds_b.md section 4)
    assert G2B._own_rows(decided, "backup") == [] and G2B._own_rows(decided, "primary") == []
    assert G2B._own_rows(today, "backup") == [ln for ln in today.splitlines()
                                              if re.search(r"VBR backup|the backup boot sector", ln)]
    assert len(G2B._own_rows(today, "primary")) == 2
    # critic: the decided statement wrapped -- its second line names only the backup and carries the driver clause's
    # "fails" -- is no row of the backup; a backup row that names the primary VBR and fails stays the backup's (R1)
    wrapped2 = ("  [WARN] the primary boot sector at offset 0x0 is damaged (it fails its checksum);\n"
                "  the volume was read from the backup boot sector found at offset 0xffe00 (refs.sys reads the backup "
                "boot sector only when reading sector 0 fails)")
    assert G2B._own_rows(wrapped2, "backup") == [] and len(G2B._own_rows(wrapped2, "primary")) == 1
    r1 = "  VBR backup       LBA 2047 (offset 0xffe00)  — DIFFERS from the primary VBR, checksum FAILED"
    assert G2B._own_rows(r1, "backup") == [r1] and G2B._own_rows(r1, "primary") == []


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The fixer's nodes (C2 bounds_b fixer; fixes/C2_LEAD_SETTLEMENTS.md S-B and S-C): they pass with the fix
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cmd", ["summary", "ra-supb"])
def test_s_b_an_unreadable_entry_before_a_damaged_primary_leaves_the_backup_search_to_run(cmd):
    """S-B (Q24 extended to the fallback): GPT entry 1 becomes a Basic-Data entry no file can be read at (LBA 2**60,
    bounds_a's plant), and the ReFS partition #2 after it has a zeroed primary boot sector, so no entry carries a ReFS
    signature. The fallback is the first Basic-Data entry that was READ (#2, not #1), so N344's search runs there:
    the volume is read from the backup at 0x7cfffe00, the statement, exit 2. 1.13.1 and the pre-step tree fell back to
    entry #1 and stopped (exit 1)."""
    import test_1132_red_c2_bounds_a as BA
    with _image_vol() as v:
        BA._plant_first_entry(v, "unreadable")
        _zero_primary(v)
        v.ops.append("GPT entry 1: Basic-Data at LBA 2**60; partition #2: primary boot sector zeroed")
        rc, out, err = _vrun(v, *CMDS[cmd])
    assert n344_statements(out + "\n" + err, BK_A, "zeroed"), "%s: no statement names the backup boot sector at " \
        "0x%x as the copy read" % (cmd, BK_A) + _why(rc, out, err, v)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _why(rc, out, err, v)


_READ_ANYWAY = re.compile(r"(?i)\bread\b[^.\n]{0,40}\bprimary\b[^.\n]{0,40}\banyway\b")


@pytest.mark.parametrize("cmd", ["files", "ra-supb"])
def test_s_c_a_signed_primary_failing_a_test_without_a_backup_is_read_and_said(cmd):
    """S-C (decision 26's rule at the boot sector): the primary keeps its signature and fails its checksum, and no
    backup copy passes (the backup at 0x7cfffe00 zeroed). The primary is read (never exit 1 for a readable volume),
    the statement names the failed test and the range searched and says the volume is read from the primary anyway,
    exit 2; `files` lists what it lists on the volume as-is."""
    with _image_vol() as v:
        _plant_primary(v, "checksum", _geometry(v))
        v.zero(BK_A, 512)
        v.ops.append("backup boot sector zeroed")
        rc, out, err = _vrun(v, *CMDS[cmd])
    text = out + "\n" + err
    assert none_found_statement(text, PS_A, PS_A + P_A) and _READ_ANYWAY.search(text), \
        "%s: no statement says the primary is damaged, no backup was found (the range searched) and the primary is " \
        "read anyway" % cmd + _why(rc, out, err, v)
    assert any(re.search(_TEST_WORDS["checksum"], s, re.I)
               for s in _spans(text, (_PRIMARY, _BOOT, _DAMAGED, _NOT_FOUND))), "the failed test is not named"
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _why(rc, out, err, v)
    if cmd == "files":
        assert _csv_rows(out) == _csv_rows(_baseline("image", "files")[1]), "the listing differs from the as-is one"
