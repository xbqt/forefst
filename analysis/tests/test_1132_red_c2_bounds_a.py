"""1.13.2 (ships as 1.14.0) RED cases, wave C step C2, area `bounds_a`: B3 (the volume length) and N378 (4), (4w) (a
GPT Basic-Data entry whose start cannot be read).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (settlements Q16-Q18, Q24), `fixes/WAVEC_INVENTORY.md` and
`fixes/WAVEC_CENSUS.md` (rows B3, N378), `fixes/WAVEC_READING_bounds.md` sections 3 ("B3 length / tail / truncated /
scans, capacity") and 4.1 (the closure table). Report: `analysis/reports/v1.13.2/fixes/RED_C2_bounds_a.md`.

B3's earlier RED nodes stay where they are (`test_1132_red_b_items.py`, the B3 block: orphan scans stop at the volume
end, `summary` names the tail, `summary --json` capacity, the truncation wording in `summary` / `integrity`, the orphan
coverage of a truncated image, refsanalysis `allocators`). This file adds only what they do not assert:

  B3 (Q16)  every consumer of the volume length takes T x bytes-per-sector // cluster size: `fastsummary --json` and
            refsanalysis `summary++ --json` capacity (`alloc_capacity`, the census escalation), and `_volume_ncl`.
  B3 (Q17)  the image tail in two parts: inside the partition after the volume (P - T x bps, P from the GPT entry AT
            the partition start, not the first Basic-Data entry) and after the partition; decimal bytes; not a finding.
  B3 (Q18)  a truncated image: the statement carries the image end and the volume end (hex offsets, absolute) and the
            bytes missing (decimal); exit 2 in a scan whose read meets the image end; a command whose reads stay inside
            the image exits 0 and states it on stderr.
  N378 (4)  refsanalysis `validate_image` stops every command with exit 1 'cannot read image' on a Basic-Data entry
            whose start no file can be read at, though the ReFS partition is the next entry (forefst's
            `find_refs_partition` skips that entry and reads the volume).
  N378 (4w) when that entry is the only Basic-Data entry, `find_refs_partition`'s `first_basic` fallback returns its
            start and a raw seek (`parse_vbr`; `integrity`'s own VBR read) prints CPython's text (`cannot fit 'int'
            into an offset-sized integer`); the decided output names the entry that could not be read, exit 1.

Critic (2026-10-23, RED_C2_bounds_a_critic.md): matchers widened to every form the settlements allow (a tail part under
a block heading, a truncation block of up to five lines, the entry named by its number), controls and the (4w) class
extended; B3's earlier nodes in test_1132_red_b_items.py accept Q17's two-part tail and bounds section 3's sentence.

Volumes: the 1 MiB synthetic ReFS 3.14 volume of `test_1132_red_a_bootstrap.py` and a hole-preserving scratch copy of
the battery's base A (`step1/win11refsmini.raw`), both through `test_1132_red_b_items.py`'s helpers (one builder, one
set of pins). Base A's geometry, read by this module from the bytes (MR-V, 2026-10-23): partition #2 = LBA
0x8000..0x3fff7f (P = 2130640896 bytes, start 0x1000000), T x bps = 0x7c000000 (507904 clusters of 4 KiB), image
0x80000000 bytes: 50266112 bytes inside the partition after the volume, 65536 after the partition.

Conventions (test_1132_red_a_bootstrap.py): every RED is ``xfail(strict=True, raises=AssertionError)``; fixture
problems raise RedFixtureError, a property the tool already has and must keep raises KeptPropertyBroken (neither is an
AssertionError); expected values are computed here from the bytes; controls (no mark) pass now and must keep passing.
Value matchers accept a decimal with or without thousands separators and a hex offset in either case or zero-padded:
they test the value, the one-form rules (K10, K15, K16, K28) bind the fixer independently.
"""
import contextlib
import json
import os
import re
import struct
import sys
import zlib

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402
import test_1132_red_b_items as BI                       # noqa: E402  (B3 volumes, plants, runners, matchers)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, BI._red
FOREFST, REFSANALYSIS, CS = BI.FOREFST, BI.REFSANALYSIS, BI.CS
_vrun, _ctx, _json_of = BI._vrun, BI._ctx, BI._json_of

GPT_BASIC_DATA = F.GPT_BASIC_DATA
HUGE_LBA = 1 << 60                                       # x 512 = 2**69: past the largest file offset on every host
HUGE_OFF = HUGE_LBA * 512


@contextlib.contextmanager
def _vol(kind, tmp_path):
    if kind == "image":
        with BI._image_vol() as v:
            yield v
    else:
        yield BI._synthetic_vol(tmp_path)


@pytest.fixture(params=["synthetic", "image"])
def b3vol(request, tmp_path):
    with _vol(request.param, tmp_path) as v:
        yield v


# ─── geometry read here from the bytes ────────────────────────────────────────────────────────────────────────

def _gpt(v):
    """The entries of the primary GPT at LBA 1 (512-byte sectors), checked first: signature and both CRC32s."""
    h = v.read(512, 92)
    _fx(h[:8] == b"EFI PART", "no GPT header at LBA 1")
    hs, crc = struct.unpack_from("<II", h, 12)
    w = bytearray(v.read(512, hs))
    w[16:20] = b"\0" * 4
    _fx(zlib.crc32(bytes(w)) == crc, "GPT header CRC32")
    plba, n, es, ecrc = struct.unpack_from("<QIII", h, 72)
    arr = v.read(plba * 512, n * es)
    _fx(zlib.crc32(arr) == ecrc, "GPT entry-array CRC32")
    return [arr[i * es:(i + 1) * es] for i in range(n)]


def _partition_at_ps(v):
    """(start, end) in bytes of the GPT entry that starts at the volume's partition start (P = end - start)."""
    for e in _gpt(v):
        if e[:16] == GPT_BASIC_DATA and F.le64(e, 32) * 512 == v.geo.ps:
            return v.geo.ps, (F.le64(e, 40) + 1) * 512
    raise RedFixtureError("no Basic-Data entry starts at 0x%x" % v.geo.ps)


def _set_gpt_entry(v, idx, type_guid=None, first=None, last=None):
    """Rewrite entry `idx` (1-based) in the primary AND the backup GPT, both CRC32s recomputed: a well-formed GPT."""
    hdr_lbas = [1, F.le64(v.read(512, 92), 32)]
    for hl in hdr_lbas:
        h = bytearray(v.read(hl * 512, 92))
        _fx(h[:8] == b"EFI PART", "no GPT header at LBA %d" % hl)
        plba, n, es = struct.unpack_from("<QII", h, 72)
        arr = bytearray(v.read(plba * 512, n * es))
        e = (idx - 1) * es
        if type_guid is not None:
            arr[e:e + 16] = type_guid
        if first is not None:
            struct.pack_into("<Q", arr, e + 32, first)
        if last is not None:
            struct.pack_into("<Q", arr, e + 40, last)
        v.write(plba * 512, bytes(arr))
        struct.pack_into("<I", h, 88, zlib.crc32(bytes(arr)))
        h[16:20] = b"\0" * 4
        struct.pack_into("<I", h, 16, zlib.crc32(bytes(h[:92])))
        v.write(hl * 512, bytes(h))
    ent = _gpt(v)[idx - 1]                                  # re-read: landed, CRCs valid
    _fx(type_guid is None or ent[:16] == type_guid, "entry %d type did not land" % idx)
    _fx(first is None or F.le64(ent, 32) == first, "entry %d first LBA did not land" % idx)
    v.ops.append("GPT entry %d: type %s first 0x%x last 0x%x (both copies, CRCs recomputed)" % (
        idx, ent[:16].hex(), F.le64(ent, 32), F.le64(ent, 40)))


def _plant_first_entry(v, how):
    """Entry 1 (Microsoft reserved, LBA 34..32767 on base A) becomes a Basic-Data entry before the ReFS partition:
    `readable` keeps its LBAs (a readable partition that is not ReFS), `unreadable` moves it to LBA 2**60."""
    _fx(v.geo.kind == "image", "the GPT plants need base A")
    _fx(_gpt(v)[0][:16] != GPT_BASIC_DATA and _gpt(v)[1][:16] == GPT_BASIC_DATA, "base A's entries 1/2")
    if how == "unreadable":
        _set_gpt_entry(v, 1, GPT_BASIC_DATA, HUGE_LBA, HUGE_LBA + 0xFF)
    else:
        _set_gpt_entry(v, 1, GPT_BASIC_DATA)
        _fx(v.read(F.le64(_gpt(v)[0], 32) * 512 + 3, 4) != b"ReFS", "entry 1 holds a ReFS signature")


# ─── matchers ─────────────────────────────────────────────────────────────────────────────────────────────────

def _dec(n):
    """A whole decimal `n`, with or without thousands separators."""
    forms = sorted({str(n), "{:,}".format(n)}, key=len, reverse=True)
    return re.compile(r"(?<![0-9A-Za-z.,])(?:%s)(?![0-9A-Za-z]|[.,][0-9])" % "|".join(re.escape(f) for f in forms))


def _hex(n):
    """A hex offset `n` (0x..., either case, optionally zero-padded)."""
    return re.compile(r"(?<![0-9A-Za-z])0[xX]0*%s(?![0-9A-Fa-f])" % ("%x" % n), re.I)


def _part_lines(text, n):
    """Lines that state a tail part of `n` bytes: the decimal byte count on a line that is not the allocator's `beyond
    the last container` line, with the word `partition` on that line, the line after it or one of the two lines before
    it (critic: a block heading such as `Image tail (partition #2 ends at 0x7fff0000):` over `after it: 65536 bytes`
    is a form Q17 allows; the byte counts stay the discriminating values)."""
    d = _dec(n)
    lines = text.splitlines()
    return [ln for i, ln in enumerate(lines) if d.search(ln) and not re.search(r"(?i)container|allocator", ln)
            and re.search(r"(?i)\bpartition\b", "\n".join(lines[max(0, i - 2):i + 2]))]


# a line of bounds section 3's sentence (`the image ends at offset X, before the volume's end at offset Y (...): Z bytes
# of the volume ... are not in the image`), wherever the sentence wraps
_TRUNC_ANCHOR = re.compile(r"(?i)\bimage\s+(?:file\s+)?ends\b|\bbefore\s+the\s+volume(?:'s)?\s+end\b|"
                           r"\bnot\s+in\s+the\s+image\b")
_TRUNC_PHRASE = re.compile(r"(?i)truncat|\bbefore\s+the\s+volume(?:'s)?\s+end\b")   # what no untruncated image may print


def _trunc_windows(text):
    """Each truncation statement -- a line BI._truncation_lines accepts, or a line of bounds section 3's sentence --
    with the two lines before it and the four after it (a wrapped sentence, or a block of up to five lines such as
    `Truncated image:` over `image end`, `volume end`, `missing` lines; critic)."""
    lines = text.splitlines()
    hits = set(BI._truncation_lines(text))
    return ["\n".join(lines[max(0, i - 2):i + 5]) for i, ln in enumerate(lines)
            if ln in hits or _TRUNC_ANCHOR.search(ln)]


_CPYTHON = re.compile(r"(?i)cannot fit 'int'|offset-sized integer|index-sized integer|Python int too large|"
                      r"OverflowError|signed integer is greater than maximum")


def _names_the_unreadable_entry(text, idx):
    """The run names the entry it could not read: its byte offset (2**69) or its first LBA (2**60), in hex, or its
    number `idx` in the partition table (`partition #2`, the label find_refs_partition already returns, or `GPT entry
    2`; critic: naming the entry is what the item asks, not one form of the name)."""
    return bool(_hex(HUGE_OFF).search(text) or _hex(HUGE_LBA).search(text)
                or re.search(r"(?i)\b(?:partition|entry)\s*(?:#\s*)?%d(?![0-9])" % idx, text))


def _cap_key(cap, *names):
    for k in names:
        if k in cap:
            return cap[k]
    return None


def test_c2_bounds_a_matchers_accept_the_decided_forms_and_reject_the_1131_lines():
    """Unit level: no RED below asks for something no correct output could print, and none is met by 1.13.1's lines."""
    # Q17 tail parts (base A as-is)
    assert _part_lines("  Image tail:  50266112 bytes (47.9 MiB) inside the partition after the volume", 50266112)
    assert _part_lines("    65536 bytes (64 KiB) after the partition (end of the image)", 65536)
    assert _part_lines("  tail: 50,266,112 bytes in the partition after the volume; 65,536 bytes after the partition",
                       65536)
    assert not _part_lines("      • 48.0 MB lies beyond the last container,", 50266112)               # 1.13.1
    assert not _part_lines("  partition starts at 0x1000000; 650266112 bytes", 50266112)
    assert not _part_lines("  Image size:         2.0 GB", 65536)
    block = ("  Image tail (not this volume's; partition #2 ends at offset 0x7fff0000):\n"
             "    inside the partition, after the volume:  50266112 bytes (47.9 MiB)\n"
             "    after it, to the end of the image:          65536 bytes (64 KiB)")                    # critic
    assert _part_lines(block, 50266112) and _part_lines(block, 65536)
    assert not _part_lines("  Image tail:  50331648 bytes (48 MiB) after the volume", 50266112)      # the total only
    # Q18 truncation statement (base A truncated at 0x7c000000)
    stmt = ("  [WARN] the image ends at offset 0x7c000000, before the volume's end at offset 0x7d000000 (total sectors\n"
            "         x bytes per sector): 16777216 bytes of the volume, with its backup superblocks and backup boot\n"
            "         sector, are not in the image (truncated image)")
    w = _trunc_windows(stmt)
    assert w and _hex(0x7C000000).search(w[0]) and _hex(0x7D000000).search(w[0]) and _dec(16777216).search(w[0])
    plain = ("the image ends at offset 0x7c000000, before the volume's end at offset 0x7d000000 (total sectors x bytes "
             "per sector): 16777216 bytes of the volume, with its backup superblocks and backup boot sector, are not in "
             "the image")                                                     # bounds section 3, no `truncat`
    w = _trunc_windows("  Volume size:  1.9 GiB\n  " + plain)
    assert w and _hex(0x7C000000).search(w[0]) and _hex(0x7D000000).search(w[0]) and _dec(16777216).search(w[0])
    old = ("  [WARN] the backup boot sector at LBA 4063231 (offset 0x7cfffe00) is missing or unreadable\n"
           "  [WARN] the backup superblock (SUPB) at LCN 0x7bffd (offset 0x7cffd000) is missing or damaged (unreadable)")
    assert not _trunc_windows(old)                                                                       # 1.13.1
    assert not _hex(0x7C000000).search("offset 0x7cfffe00") and not _dec(16777216).search("167772160")
    blk = ("  [WARN] Truncated image:\n         image end:    offset 0x7c000000\n"
           "         volume end:   offset 0x7d000000 (total sectors x bytes per sector)\n"
           "         not in the image: 16777216 bytes (16 MiB), with the backup superblocks and boot sector")  # critic
    w = _trunc_windows(blk)
    assert w and _hex(0x7C000000).search(w[0]) and _hex(0x7D000000).search(w[0]) and _dec(16777216).search(w[0])
    assert not _TRUNC_PHRASE.search("      • 48.0 MB lies beyond the last container,\n  Image size: 2.0 GB")  # 1.13.1
    assert _TRUNC_PHRASE.search(plain)
    # N378 (4w)
    assert _CPYTHON.search("forefst: error: cannot fit 'int' into an offset-sized integer")                 # 1.13.1
    assert not _CPYTHON.search("refsanalysis: error: cannot read image: offset 0x200000000000000000 is beyond the "
                               "largest file offset, 0x7fffffffffffffff")
    assert _names_the_unreadable_entry("offset 0x200000000000000000 is beyond the largest file offset", 2)
    assert _names_the_unreadable_entry("partition #2 (first LBA 0x1000000000000000) cannot be read", 2)
    assert _names_the_unreadable_entry("no ReFS volume: GPT entry 2 starts beyond the end of any file", 2)  # critic
    assert not _names_the_unreadable_entry("GPT entry 12 starts beyond the end of any file", 2)
    assert not _names_the_unreadable_entry("forefst: error: cannot fit 'int' into an offset-sized integer", 2)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B3 (Q16) -- every consumer of the volume length takes the boot sector's
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_CAP_RUNS = {"fastsummary-json": (FOREFST, ("fastsummary", "--json", "-")),
             "ra-summary++-json": (REFSANALYSIS, ("summary++", "--json"))}


# RED 1.13.2 B3: alloc_capacity takes the volume as (image size - ps) // cs (fd:1583): `fastsummary --json` and
# refsanalysis `summary++ --json` give capacity.volume_bytes 2130706432 and outside_allocator_bytes 50331648 on base A
# (the volume is 2080374784 bytes, all of it covered); on a truncated image the allocator summary is rejected (covered
# 507904 > the image's 503808 clusters) and no capacity is given (the strict xfail mark removed: fixed in step C2,
# area bounds_a)
@pytest.mark.parametrize("state", ["as-is", "truncated"])
@pytest.mark.parametrize("run", sorted(_CAP_RUNS))
def test_b3_every_capacity_consumer_counts_the_volume(run, state):
    tool, args = _CAP_RUNS[run]
    with BI._image_vol() as v:
        vcl, _end = BI._geometry(v)
        vol_bytes = vcl * CS
        if state == "truncated":
            BI.truncate_inside_volume(v)
        rc, out, err = _vrun(v, tool, *args)
        j = _json_of(out, run)
        _keep(j.get("volume_size_bytes", j.get("VolumeSizeBytes")) == vol_bytes, "volume_size_bytes != %d" % vol_bytes)
        cap = j.get("capacity") or j.get("Capacity")
        assert cap, "%s gives no capacity (the allocator summary was rejected)" % run + _ctx(rc, "", err, v.ops)
        covered = _cap_key(cap, "allocator_covered_bytes", "AllocatorCoveredBytes")
        assert _cap_key(cap, "volume_bytes", "VolumeBytes") == vol_bytes, "capacity volume_bytes %r, the volume is %d" % (
            _cap_key(cap, "volume_bytes", "VolumeBytes"), vol_bytes)
        assert _cap_key(cap, "outside_allocator_bytes", "OutsideAllocatorBytes") == vol_bytes - covered, (
            "outside_allocator_bytes %r; the volume %d minus the allocator's %r" % (
                _cap_key(cap, "outside_allocator_bytes", "OutsideAllocatorBytes"), vol_bytes, covered))


# RED 1.13.2 B3: _volume_ncl (fd:3926) counts the clusters from the partition start to the IMAGE end: 520192 on base A
# as it is (507904 in the volume), 503808 on a copy cut inside the volume (the strict xfail mark removed: fixed in
# step C2, area bounds_a)
@pytest.mark.parametrize("state", ["as-is", "truncated"])
def test_b3_volume_ncl_is_the_volume_length(state):
    """The plausibility bound of every decoded run (N217, wave D, is told) is the boot sector's volume length. A fix that
    removes `_volume_ncl` in favour of the one definition passes here; its callers then use that definition."""
    with BI._image_vol() as v:
        vcl, _end = BI._geometry(v)
        if state == "truncated":
            BI.truncate_inside_volume(v)
        fn = getattr(F, "_volume_ncl", None)
        if fn is None:
            assert "_volume_ncl" not in open(os.path.join(REPO, "forefst.py"), encoding="utf-8").read()
            return
        with open(v.path, "rb") as f:
            f.seek(0x123)
            got = fn(f, v.geo.ps, CS)
            _keep(f.tell() == 0x123, "_volume_ncl moved the file position")
        assert got == vcl, "_volume_ncl = %d; the volume has %d clusters (T x bps // cs)" % (got, vcl)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B3 (Q17) -- the image tail in two parts, not a finding
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _tail_parts(v):
    """(inside the partition after the volume, after the partition), in bytes, from the GPT entry at ps and the VBR."""
    _vcl, vol_end = BI._geometry(v)
    _s, p_end = _partition_at_ps(v)
    size = os.path.getsize(v.path)
    _fx(vol_end <= p_end <= size, "volume end 0x%x, partition end 0x%x, image end 0x%x" % (vol_end, p_end, size))
    return p_end - vol_end, size - p_end


def _entry_at_ps(v):
    """The 1-based number of the GPT entry that starts at the volume's partition start."""
    for k, e in enumerate(_gpt(v), 1):
        if e[:16] == GPT_BASIC_DATA and F.le64(e, 32) * 512 == v.geo.ps:
            return k
    raise RedFixtureError("no Basic-Data entry starts at 0x%x" % v.geo.ps)


def _tail_said(v, inside, after):
    """PLAN 10.2 A2 (1.14.0; the maintainer's answer to group 4's draft, 2026-11-15): `summary` gives the image tail on
    ONE line -- its byte count and, as a reading aid, how much of it lies in the volume's partition (and which entry
    that is); the two exact parts are the JSON's `ImageTail.InPartitionBytes` / `AfterPartitionBytes`. Returns
    (failure text or None, rc, out, err) for the text view, then checks the JSON."""
    rc, out, err = _vrun(v, FOREFST, "summary")
    lines = [ln for ln in out.splitlines() if ln.strip().startswith("Image tail:")]
    want = "%s after the volume, not read (%s of it in partition #%d)" % (F.bytes_text(inside + after),
                                                                          F.size_aid_text(inside), _entry_at_ps(v))
    if len(lines) != 1 or lines[0].split(":", 1)[1].strip() != want or not _dec(inside + after).search(lines[0]):
        return "the image tail is not the one line %r: %r" % (want, lines), rc, out, err
    rcj, jout, jerr = _vrun(v, FOREFST, "summary", "--json")
    i = jout.find("{")
    _fx(i >= 0, "summary --json printed no JSON object")
    t = json.JSONDecoder().raw_decode(jout[i:])[0].get("ImageTail") or {}
    got = (t.get("Bytes"), t.get("InPartitionBytes"), t.get("AfterPartitionBytes"), t.get("PartitionEntry"))
    if got != (inside + after, inside, after, _entry_at_ps(v)):
        return "the JSON's ImageTail is %r, not %r" % (got, (inside + after, inside, after, _entry_at_ps(v))), \
            rcj, jout, jerr
    return None, rc, out, err


# RED 1.13.2 B3: summary has no line for either part of the image tail: the 50266112 bytes inside the partition after
# the volume and the 65536 after it are folded into the allocator's `48.0 MB lies beyond the last container` (the
# strict xfail mark removed: fixed in step C2, area bounds_a). 1.14.0 (A2): one text line, the exact parts in the JSON.
@pytest.mark.parametrize("state", ["as-is", "extended"])
def test_b3_summary_reports_the_tail_in_two_parts(state):
    with BI._image_vol() as v:
        if state == "extended":
            BI.extend_and_plant(v)
        inside, after = _tail_parts(v)
        _fx(inside > 0 and after > 0, "the image has no two-part tail")
        bad, rc, out, err = _tail_said(v, inside, after)
        assert bad is None, bad + _ctx(rc, out, err, v.ops)


# RED 1.13.2 B3: the partition length must come from the GPT entry at the partition start (closure 4.1 row 1); summary
# states no tail part at all today, and `gpt_partition_detail` (fd:150) returns the FIRST Basic-Data entry, here a
# partition that is not this volume's (the strict xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("first", ["readable", "unreadable"])
def test_b3_tail_parts_come_from_the_gpt_entry_at_the_partition_start(first):
    with BI._image_vol() as v:
        inside, after = _tail_parts(v)
        _plant_first_entry(v, first)
        _fx(_tail_parts(v) == (inside, after), "the plant moved the ReFS partition")
        bad, rc, out, err = _tail_said(v, inside, after)
        _keep(rc == 0, "summary rc %s on a GPT with a Basic-Data entry before the ReFS one" % rc)
        assert bad is None, ("the tail parts are not %d inside the partition and %d after it: " % (inside, after)) + \
            bad + _ctx(rc, out, err, v.ops)


@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity", "deleted --scan-pages", "deleted --full"])
def test_b3_control_the_tail_is_not_a_finding_and_not_a_truncation(cmd):
    """Base A as it is (a 48 MiB tail after the volume): exit 0, nothing says `truncated` or `before the volume's end`
    (Q17: the tail is not a finding; guards the Q18 REDs against a statement printed for every image with a tail).
    Critic: integrity (a V-a command) and `deleted --full` (the other orphan scan) added; both exit 0 today."""
    with BI._image_vol() as v:
        rc, out, err = _vrun(v, FOREFST, *cmd.split())
        out, err = _scrub(out, v), _scrub(err, v)
        assert rc == 0, "%s exits %s on base A as it is" % (cmd, rc) + _ctx(rc, out, err)
        assert not _TRUNC_PHRASE.search(out + err), _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B3 (Q18) -- a truncated image
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _scrub(text, v):
    """The image's own path out of the text: a pytest tmp_path named after a test (`..._truncation_...`) would otherwise
    meet the truncation matcher on an `Image: <path>` line."""
    return text.replace(v.path, "<image>").replace(os.path.dirname(v.path), "<dir>")


def _cut(v):
    """Truncate inside the volume; (image end, volume end, bytes missing), absolute offsets."""
    _vcl, vol_end = BI._geometry(v)
    BI.truncate_inside_volume(v)
    end = os.path.getsize(v.path)
    return end, vol_end, vol_end - end


# RED 1.13.2 B3: nothing states the truncation: summary/fastsummary/integrity report only the backup copies as
# `missing or unreadable` / `missing or damaged (unreadable)`, with no image end, volume end or count of bytes missing
# (the strict xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity"])
def test_b3_truncation_statement_gives_the_two_ends_and_the_bytes_missing(b3vol, cmd):
    end, vol_end, missing = _cut(b3vol)
    rc, out, err = _vrun(b3vol, FOREFST, cmd)
    out, err = _scrub(out, b3vol), _scrub(err, b3vol)
    wins = _trunc_windows(out + "\n" + err)
    assert any(_hex(end).search(w) and _hex(vol_end).search(w) and _dec(missing).search(w) for w in wins), (
        "no truncation statement gives the image end 0x%x, the volume end 0x%x and %d bytes missing; statements: %r" % (
            end, vol_end, missing, wins)) + _ctx(rc, out, err, b3vol.ops)


@pytest.mark.parametrize("cmd", ["summary", "fastsummary", "integrity"])
def test_b3_control_a_truncated_image_exits_2_in_the_v_a_commands(b3vol, cmd):
    """Q18: exit 2 in summary, fastsummary and integrity (the missing backup copies, decision 27.3's V-a scope). They
    exit 2 now; the fix keeps it."""
    _cut(b3vol)
    rc, out, err = _vrun(b3vol, FOREFST, cmd)
    assert rc == 2, _ctx(rc, out, err, b3vol.ops)


# RED 1.13.2 B3: the orphan-page scans of a truncated image exit 0: the scan stops at the image end and calls that
# 100% of the volume, so nothing tells the examiner that clusters of the volume were never scanned (the strict xfail
# mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("mode", sorted(BI._SCAN_MODES))
def test_b3_a_scan_that_meets_the_image_end_exits_2(b3vol, mode):
    _cut(b3vol)
    rc, out, err = _vrun(b3vol, FOREFST, *BI._SCAN_MODES[mode])
    assert rc == 2, "deleted %s exits %s on an image that ends inside the volume" % (BI._SCAN_MODES[mode][1], rc) + \
        _ctx(rc, out, err, b3vol.ops)


_INSIDE_RUNS = {"files": (FOREFST, ("files",)), "ra-containers": (REFSANALYSIS, ("containers",))}


# RED 1.13.2 B3: a command whose reads stay inside the image says nothing about the truncation (Q18: exit 0 with the
# statement on stderr) (the strict xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("run", sorted(_INSIDE_RUNS))
def test_b3_a_command_that_stays_inside_the_image_states_the_truncation_on_stderr(b3vol, run):
    tool, args = _INSIDE_RUNS[run]
    end, _vol_end, _missing = _cut(b3vol)
    rc, out, err = _vrun(b3vol, tool, *args)
    out, err = _scrub(out, b3vol), _scrub(err, b3vol)
    _keep(rc == 0, "%s exits %s on a truncated image whose live data is all present" % (run, rc))
    assert any(_hex(end).search(w) for w in _trunc_windows(err)), (
        "stderr does not state that the image ends at 0x%x, inside the volume" % end) + _ctx(rc, out[-800:], err,
                                                                                               b3vol.ops)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N378 (4), (4w) -- a GPT Basic-Data entry whose start cannot be read
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _subsequence(want, got):
    it = iter(got)
    return all(any(g == w for g in it) for w in want)


# RED 1.13.2 N378 (4): refsanalysis `validate_image` (fd:186, called by ra main for every command) reads every Basic-
# Data entry's VBR through the guard and turns its OffsetTooLarge into `cannot read image: offset 0x200000000000000000
# is beyond the largest file offset`, exit 1, before reaching the ReFS partition that is the next entry (the strict
# xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("cmd", ["boot", "supb", "chkp"])
def test_n378_4_refsanalysis_reads_the_refs_partition_after_an_unreadable_entry(cmd):
    with BI._image_vol() as v:
        rc0, out0, err0 = _vrun(v, REFSANALYSIS, cmd)
        _fx(rc0 == 0, "ra %s rc %s on the unplanted copy" % (cmd, rc0))
        _plant_first_entry(v, "unreadable")
        rc, out, err = _vrun(v, REFSANALYSIS, cmd)
        assert rc == rc0, "ra %s exits %s (%s without the plant)" % (cmd, rc, rc0) + _ctx(rc, out, err, v.ops)
        assert _subsequence(out0.splitlines(), out.splitlines()), (
            "ra %s does not print what it prints without the plant" % cmd) + _ctx(rc, out, err, v.ops)


def test_n378_4_control_forefst_skips_the_unreadable_entry():
    """forefst never calls validate_image; `find_refs_partition` skips the entry (`except OSError: pass`) and reads
    partition #2. Kept: the same summary as without the plant (lines in order; a note about the entry is allowed)."""
    with BI._image_vol() as v:
        rc0, out0, _e0 = _vrun(v, FOREFST, "summary")
        _fx(rc0 == 0, "summary rc %s on the unplanted copy" % rc0)
        _plant_first_entry(v, "unreadable")
        rc, out, err = _vrun(v, FOREFST, "summary")
        assert rc == rc0 and _subsequence(out0.splitlines(), out.splitlines()), _ctx(rc, out, err, v.ops)


# RED 1.13.2 N378 (4w): find_refs_partition's `first_basic` fallback (fd:146-147) returns the start whose guarded read
# just failed, and a raw `f.seek(ps)` (parse_vbr fd:575; integrity's own VBR read fd:19251) ends the run with
# CPython's `cannot fit 'int' into an offset-sized integer`, naming no entry and no offset (the strict xfail mark
# removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("cmd", ["summary", "files", "integrity"])
def test_n378_4w_forefst_names_the_entry_it_cannot_read(cmd):
    """Critic: `integrity` added -- it reads the VBR through its own raw seek (fd:19251), so a guard in parse_vbr alone
    leaves it printing CPython's text (the class, RED report N-4)."""
    with BI._image_vol() as v:
        _set_gpt_entry(v, 2, None, HUGE_LBA, HUGE_LBA + 0xFF)       # the ReFS partition's entry, now unreadable
        _fx(not any(e[:16] == GPT_BASIC_DATA and F.le64(e, 32) != HUGE_LBA for e in _gpt(v)), "another Basic-Data entry")
        rc, out, err = _vrun(v, FOREFST, cmd)
        _keep(rc == 1, "%s exits %s: no volume can be read (exit 1, cannot run)" % (cmd, rc))
        assert not _CPYTHON.search(out + err), "CPython's own error text reached the examiner" + _ctx(rc, out, err, v.ops)
        assert _names_the_unreadable_entry(out + err, 2), "the message names no entry or offset" + _ctx(
            rc, out, err, v.ops)


@pytest.mark.parametrize("cmd", ["boot", "supb", "chkp"])
def test_n378_4w_control_refsanalysis_names_the_entry_it_cannot_read(cmd):
    """refsanalysis today: `validate_image` stops with `cannot read image: offset 0x200000000000000000 is beyond the
    largest file offset`, exit 1. Kept once (4) lets validate_image skip the entry: the run must then not reach the
    `first_basic` raw seek either. Critic: `chkp` added (it runs validate_image again inside the command)."""
    with BI._image_vol() as v:
        _set_gpt_entry(v, 2, None, HUGE_LBA, HUGE_LBA + 0xFF)
        rc, out, err = _vrun(v, REFSANALYSIS, cmd)
        assert rc == 1 and not _CPYTHON.search(out + err) and _names_the_unreadable_entry(out + err, 2), _ctx(
            rc, out, err, v.ops)
