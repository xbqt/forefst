#!/usr/bin/env python3
# Copyright (C) 2026 Baptiste Bonnet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
forefst.py — ReFS forensic file lister (MFTECmd equivalent).

Produces CSV and body file output from ReFS disk images with comprehensive
metadata for each file and directory:
  - Full path, OID, parent OID, filename, extension
  - 4 MACB timestamps (Created, Modified, Changed, Accessed) with sub-second precision
  - File attributes, file size, allocated size
  - SecurityId, Owner SID, USN
  - ADS (Alternate Data Streams) detection
  - Encryption, compression, integrity flags
  - Reparse point target (symlinks, junctions)
  - Deleted file detection: Trash Table + orphan objects + checkpoint comparison
  - Previous file versions via $SNAPSHOT embedded attributes
  - Hard link detection (same OID in multiple directories)
  - ReFS version info

Supports ReFS 3.4 through 3.14+ and Windows Insider builds.

CSV output is designed to be comparable with Eric Zimmerman's MFTECmd
output for NTFS $MFT, enabling side-by-side forensic comparison.

Usage:
  python3 forefst.py <image>                     # CSV to stdout
  python3 forefst.py <image> -o output.csv       # CSV to file
  python3 forefst.py <image> --json               # JSON output (pretty-printed array)
  python3 forefst.py <image> --jsonl              # JSON Lines output (one object per line)
  python3 forefst.py <image> --body               # body file format
  python3 forefst.py <image> fastsummary          # quick volume summary (no directory walk)
  python3 forefst.py <image> summary              # full summary with file statistics
  python3 forefst.py <image> summary --json       # summary as JSON
  python3 forefst.py <image> --deleted            # include deleted files (trash + orphans + chkp diff)
  python3 forefst.py <image> --partition-start 0  # override partition offset
  python3 forefst.py <image> --cow-before <earlier_image>  # forward CoW version recovery

Body file format (Sleuthkit/mactime compatible):
  MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
"""

from __future__ import annotations
import argparse, csv, datetime, hashlib, io, json, os, struct, sys
from typing import Optional

# ─── Shared utilities (formerly in refs_common.py) ───────────────────
SECTOR = 512
SUPB_LCN = 0x1E
GPT_BASIC_DATA = bytes.fromhex("a2a0d0ebe5b9334487c068b6b72699c7")

def le16(b, off): return int.from_bytes(b[off:off+2], "little")
def le32(b, off): return int.from_bytes(b[off:off+4], "little")
def le64(b, off): return int.from_bytes(b[off:off+8], "little")

def find_refs_partition(path):
    """Find the first ReFS partition in a GPT disk image.

    Returns (partition_start_bytes, description_string), or (None, error_message) if no GPT /
    no partition. Each Basic-Data partition's VBR is read and the first one whose signature is
    "ReFS" (VBR offset 3) is returned, so an NTFS/FAT partition that precedes the ReFS one is
    skipped. If NO Basic-Data partition carries a ReFS signature, falls back to the first
    Basic-Data partition (prior behaviour); the caller's parse_vbr then validates/aborts on it.
    """
    with open(path, "rb") as f:
        f.seek(SECTOR)
        hdr = f.read(SECTOR)
        if len(hdr) < 92 or hdr[:8] != b"EFI PART":
            return None, "no GPT partition table found (use --partition-start for raw partitions)"
        plba = le64(hdr, 72)
        np = le32(hdr, 80)
        es = le32(hdr, 84)
        f.seek(plba * SECTOR)
        entries = f.read(np * es)
        first_basic = None
        for i in range(np):
            e = entries[i*es:(i+1)*es]
            if len(e) >= 128 and e[:16] == GPT_BASIC_DATA:
                start = le64(e, 32) * SECTOR
                if first_basic is None:
                    first_basic = (start, f"partition #{i+1}")
                try:
                    f.seek(start + 3)
                    if f.read(4) == b"ReFS":
                        return start, f"partition #{i+1}"
                except OSError:
                    pass
    if first_basic is not None:
        return first_basic
    return None, "no ReFS partition found in GPT (use --partition-start for raw partitions)"

def gpt_partition_detail(path):
    """GPT detail for the first ReFS partition, for informational -vv display.

    Returns {index (1-based), name, first_lba, last_lba, size_bytes, start_bytes}
    or None. Purely descriptive — parsing always uses find_refs_partition();
    never depend on this for the partition offset.
    """
    try:
        with open(path, "rb") as f:
            f.seek(SECTOR)
            hdr = f.read(SECTOR)
            if len(hdr) < 92 or hdr[:8] != b"EFI PART":
                return None
            plba = le64(hdr, 72); np = le32(hdr, 80); es = le32(hdr, 84)
            f.seek(plba * SECTOR)
            entries = f.read(np * es)
        for i in range(np):
            e = entries[i*es:(i+1)*es]
            if len(e) >= 128 and e[:16] == GPT_BASIC_DATA:
                first, last = le64(e, 32), le64(e, 40)
                name = e[56:128].decode("utf-16-le", "replace").rstrip("\x00").strip()
                return {
                    "index": i + 1,
                    "name": name or "(unnamed)",
                    "first_lba": first,
                    "last_lba": last,
                    "size_bytes": (last - first + 1) * SECTOR if last >= first else 0,
                    "start_bytes": first * SECTOR,
                }
    except Exception:
        return None
    return None

def validate_image(path, die_fn=None):
    """Pre-flight check: path is a readable file with ReFS or GPT signature.

    If die_fn is provided, calls die_fn(msg) on error (should not return).
    Otherwise raises ValueError on error.
    Detects: missing files, directories, too-small files, NTFS, BitLocker,
    blank/unrecognized images.
    """
    def fail(msg):
        if die_fn:
            die_fn(msg)
        raise ValueError(msg)

    if not os.path.exists(path):
        fail(f"file not found: {path}")
    if not os.path.isfile(path):
        fail(f"not a regular file: {path}")
    if os.path.getsize(path) < 4096:
        fail(f"file too small to be a disk image: {path}")

    try:
        with open(path, "rb") as f:
            header = f.read(512)
            if len(header) < 512:
                fail(f"cannot read image header: {path}")

            # Direct ReFS VBR at sector 0 (raw partition image)
            if header[3:7] == b"ReFS":
                return
            if b"NTFS" in header[:16]:
                fail("image contains NTFS, not ReFS")
            if b"-FVE-FS-" in header[:16]:
                fail("image is BitLocker-encrypted")

            # Check for GPT at sector 0 or sector 1
            gpt_header = None
            if header[:8] == b"EFI PART":
                gpt_header = header
            else:
                f.seek(SECTOR)
                sec1 = f.read(SECTOR)
                if len(sec1) >= 8 and sec1[:8] == b"EFI PART":
                    gpt_header = sec1

            if gpt_header is None:
                fail("no ReFS or GPT signature found "
                     "(use --partition-start for raw partitions)")

            # GPT found — read first partition's VBR to confirm ReFS
            plba = struct.unpack_from("<Q", gpt_header, 72)[0]
            nparts = struct.unpack_from("<I", gpt_header, 80)[0]
            esz = struct.unpack_from("<I", gpt_header, 84)[0]
            f.seek(plba * SECTOR)
            entries = f.read(min(nparts, 128) * esz)
            for i in range(min(nparts, 128)):
                e = entries[i*esz:(i+1)*esz]
                if len(e) >= 128 and e[:16] == GPT_BASIC_DATA:
                    part_lba = struct.unpack_from("<Q", e, 32)[0]
                    f.seek(part_lba * SECTOR)
                    vbr = f.read(SECTOR)
                    if len(vbr) >= 16:
                        if vbr[3:7] == b"ReFS":
                            return  # Confirmed ReFS partition
                        if b"NTFS" in vbr[:16]:
                            fail("partition contains NTFS, not ReFS")
                        if b"-FVE-FS-" in vbr[:16]:
                            fail("partition is BitLocker-encrypted")
                    break  # Only check first data partition
            # GPT present but couldn't confirm ReFS — let tools try
    except PermissionError:
        fail(f"permission denied: {path}")
    except OSError as e:
        fail(f"cannot read image: {e}")

# ─── Constants ────────────────────────────────────────────────────────
PROG = "forefst"
VERSION = "1.0.0"
# Non-resident directory entries have a short value (OID + timestamps + attrs + size).
# Resident entries (small files) embed full $SI + data inline and are longer.
NON_RESIDENT_MAX_VALUE = 84

# Canonical file-attribute flag table (TitleCase) — SINGLE source of truth; refsanalysis
# imports this and FILE_ATTR_SIMPLE (it deleted its own UPPERCASE copies). EA (0x40000) is
# LEFT EXACTLY AS-IS — do NOT touch the EA flag/handling (errata E22/E36). Virtual/Pinned/
# Unpinned (0x10000/0x80000/0x100000, winnt.h FILE_ATTRIBUTE_*) added 2026-06-29; proven
# DORMANT — 0 of 525,198 corpus files (112 images) carry them, and no on-disk attribute bit
# falls outside this table, so their addition changes no rendered output.
FILE_ATTR_FLAGS = {
    0x0001: "ReadOnly", 0x0002: "Hidden", 0x0004: "System",
    0x0010: "Directory", 0x0020: "Archive", 0x0040: "Device",
    0x0080: "Normal", 0x0100: "Temporary", 0x0200: "SparseFile",
    0x0400: "ReparsePoint", 0x0800: "Compressed", 0x1000: "Offline",
    0x2000: "NotContentIndexed", 0x4000: "Encrypted",
    0x8000: "IntegrityStream", 0x00010000: "Virtual",
    0x00020000: "NoScrubData", 0x00040000: "EA",
    0x00080000: "Pinned", 0x00100000: "Unpinned",
    0x10000000: "Directory_Internal",
}

# Short subset for compact listings (refsanalysis full=False uses this). TitleCase mirror of
# the legacy refsanalysis _FILE_ATTR_SIMPLE; 0x10000000 -> "Directory" (the user-facing
# directory marker), matching that table's intent.
FILE_ATTR_SIMPLE = {
    0x0001: "ReadOnly", 0x0002: "Hidden", 0x0004: "System",
    0x0020: "Archive", 0x0080: "Normal", 0x0400: "ReparsePoint",
    0x0800: "Compressed", 0x2000: "NotContentIndexed",
    0x10000000: "Directory",
}

# Canonical well-known SID name table (richer BUILTIN\ form) — refsanalysis imports this and
# deleted its own copy. Names are the authoritative BUILTIN\/mandatory-level/app-package
# strings (previously only in refsanalysis); surfacing them enriches forefst's OwnerSid.
WELL_KNOWN_SIDS = {
    "S-1-0-0": "Nobody", "S-1-1-0": "Everyone", "S-1-2-0": "LOCAL",
    "S-1-3-0": "CREATOR OWNER", "S-1-3-1": "CREATOR GROUP",
    "S-1-5-7": "ANONYMOUS LOGON", "S-1-5-11": "Authenticated Users",
    "S-1-5-18": "SYSTEM", "S-1-5-19": "LOCAL SERVICE",
    "S-1-5-20": "NETWORK SERVICE",
    "S-1-5-32-544": "BUILTIN\\Administrators", "S-1-5-32-545": "BUILTIN\\Users",
    "S-1-5-32-546": "BUILTIN\\Guests", "S-1-5-32-547": "BUILTIN\\Power Users",
    "S-1-5-32-551": "BUILTIN\\Backup Operators",
    "S-1-15-2-1": "ALL APPLICATION PACKAGES",
    "S-1-15-2-2": "ALL RESTRICTED APPLICATION PACKAGES",
    "S-1-16-0": "Untrusted Mandatory Level",
    "S-1-16-4096": "Low Mandatory Level",
    "S-1-16-8192": "Medium Mandatory Level",
    "S-1-16-8448": "Medium Plus Mandatory Level",
    "S-1-16-12288": "High Mandatory Level",
    "S-1-16-16384": "System Mandatory Level",
}

# Canonical Microsoft reparse-tag name table (ntifs.h / MS-FSCC, full IO_REPARSE_TAG_* names).
# SINGLE source of truth — refsanalysis imports this (it deleted its own _REPARSE_TAGS copy).
# Post-E41/#341: every tag that ACTUALLY occurs on disk in the corpus (MOUNT_POINT, SYMLINK,
# APPEXECLINK, AF_UNIX, LX_FIFO/CHR/BLK) was re-verified correct vs ntifs.h (0x80000024=LX_FIFO
# NOT ONEDRIVE; 0x80000017=WOF; 0x80000018=WCI). H3 verification (2026-06-29) flagged TWO latent
# entries that are ABSENT from the entire 113-image corpus (zero forensic impact, kept as-is to
# avoid an unverifiable change): 0x90001027 WCI_LINK_1 (MS-FSCC canonical value is 0xA0001027) and
# 0x80000016 WOF_DFM (MS-FSCC name is DFM). Both never appear on disk; see DOCS_UPDATE_CHECKLIST.
REPARSE_TAGS = {
    0xA0000003: "IO_REPARSE_TAG_MOUNT_POINT",
    0xC0000004: "IO_REPARSE_TAG_HSM",
    0x80000005: "IO_REPARSE_TAG_DRIVE_EXTENDER",
    0x80000006: "IO_REPARSE_TAG_HSM2",
    0x80000007: "IO_REPARSE_TAG_SIS",
    0x80000008: "IO_REPARSE_TAG_WIM",
    0x80000009: "IO_REPARSE_TAG_CSV",
    0x8000000A: "IO_REPARSE_TAG_DFS",
    0x8000000B: "IO_REPARSE_TAG_FILTER_MANAGER",
    0xA000000C: "IO_REPARSE_TAG_SYMLINK",
    0x80000012: "IO_REPARSE_TAG_DFSR",
    0x80000013: "IO_REPARSE_TAG_DEDUP",
    0x80000014: "IO_REPARSE_TAG_NFS",
    0x80000015: "IO_REPARSE_TAG_FILE_PLACEHOLDER",
    0x80000016: "IO_REPARSE_TAG_WOF_DFM",
    0x80000017: "IO_REPARSE_TAG_WOF",
    0x80000018: "IO_REPARSE_TAG_WCI",
    0x90001018: "IO_REPARSE_TAG_WCI_1",
    0xA0000019: "IO_REPARSE_TAG_GLOBAL_REPARSE",
    0x9000001A: "IO_REPARSE_TAG_CLOUD",
    0x8000001B: "IO_REPARSE_TAG_APPEXECLINK",
    0x9000001C: "IO_REPARSE_TAG_PROJFS",
    0xA000001D: "IO_REPARSE_TAG_LX_SYMLINK",
    0x8000001E: "IO_REPARSE_TAG_STORAGE_SYNC",
    0xA000001F: "IO_REPARSE_TAG_WCI_TOMBSTONE",
    0x80000020: "IO_REPARSE_TAG_UNHANDLED",
    0x80000021: "IO_REPARSE_TAG_ONEDRIVE",
    0xA0000022: "IO_REPARSE_TAG_PROJFS_TOMBSTONE",
    0x80000023: "IO_REPARSE_TAG_AF_UNIX",
    0x80000024: "IO_REPARSE_TAG_LX_FIFO",
    0x80000025: "IO_REPARSE_TAG_LX_CHR",
    0x80000026: "IO_REPARSE_TAG_LX_BLK",
    0xA0000027: "IO_REPARSE_TAG_WCI_LINK",
    0x90001027: "IO_REPARSE_TAG_WCI_LINK_1",
    0xA0000028: "IO_REPARSE_TAG_DATALESS_CIM",
}

def reparse_tag_str(tag):
    """Render a reparse tag as 'IO_REPARSE_TAG_NAME (0xXXXXXXXX)' (or bare hex if unknown)."""
    name = REPARSE_TAGS.get(tag)
    return f"{name} (0x{tag:08x})" if name else f"0x{tag:08x}"

# ─── Helpers ──────────────────────────────────────────────────────────
def filetime_to_iso(ft):
    """Convert FILETIME to ISO 8601 with 7-digit sub-second precision."""
    if ft == 0 or ft >= 0xFFFFFFFFFFFFFFFF:
        return ""
    try:
        epoch_diff = 116444736000000000
        total_100ns = ft - epoch_diff
        seconds = total_100ns // 10000000
        frac = total_100ns % 10000000
        dt = datetime.datetime.fromtimestamp(seconds, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S") + f".{frac:07d}"
    except (OSError, ValueError, OverflowError):
        return ""

def filetime_to_unix(ft):
    if ft == 0 or ft >= 0xFFFFFFFFFFFFFFFF:
        return 0
    try:
        # integer // (not float /) — float division rounds up at ~0.9999999 s, giving a Unix second
        # 1 too high; filetime_to_iso already uses //. (fix 2026-06-20)
        return (ft - 116444736000000000) // 10000000
    except (ValueError, OverflowError):
        return 0

# ── Timestamp-anomaly (timestomp) detection ────────────────────────────────
# A FILETIME tick is 100 ns; one day = 24*3600*1e7 ticks. The default margin
# tolerates normal close-in-time metadata ops while catching the year-scale
# back-dating that timestomping produces.
TS_MARGIN_100NS = 24 * 3600 * 10**7  # 1 day

def _ft_valid(ft):
    return 0 < ft < 0xFFFFFFFFFFFFFFFF

def timestomp_intrinsic_flags(create, modify, change, access,
                              vol_create=0, vol_modify=0, margin=TS_MARGIN_100NS):
    """Intrinsic ($SI-only) timestamp-anomaly indicators for one file.

    Returns a list of short flag strings. These are SUGGESTIVE, not proof. The
    metadata-change time ($SI+0x10) is an ordinary timestamp, but the high-level
    APIs timestomp tools usually use (Win32 SetFileTime, PowerShell, .NET) expose
    only Creation/Write/Access — NOT the change time — so after such a stomp the FS
    leaves the change time at the real write moment while B/M/A are back-dated:
    `change >> max(create, modify)` (CHANGE_LATE) is the tell. This is a heuristic
    against common tooling, NOT tamper-proof: the change time CAN be set via the
    native NtSetInformationFile(FILE_BASIC_INFORMATION.ChangeTime) or a raw-disk
    edit, which defeats CHANGE_LATE. Also trips on a creation-time-preserving copy
    (robocopy /COPY:T, restore) or a legitimate late rename/ACL change on an aged
    file. Corroborate with the USN journal (refsanalysis `timestomp`)."""
    flags = []
    if not _ft_valid(create):
        return flags
    base = max(create, modify) if _ft_valid(modify) else create
    if _ft_valid(change) and change > base + margin:
        flags.append("CHANGE_LATE")        # metadata-change time post-dates created/modified
    if _ft_valid(modify) and create > modify + margin:
        flags.append("CREATE_GT_MODIFY")   # created after last write
    if _ft_valid(vol_create) and create < vol_create - margin:
        flags.append("PRE_FORMAT")         # created before the volume existed
    if _ft_valid(vol_modify) and create > vol_modify + margin:
        flags.append("FUTURE")             # created after the volume's last metadata write
    return flags

def attrs_to_str(attrs, full=True, hex_if_empty=False):
    """Render file-attribute bits as 'Flag|Flag'. full=False uses the short subset.
    hex_if_empty=True renders no-flags as '0x..' (refsanalysis behaviour); the forefst
    default renders no-flags as '' (unchanged)."""
    table = FILE_ATTR_FLAGS if full else FILE_ATTR_SIMPLE
    flags = [name for bit, name in table.items() if attrs & bit]
    if flags:
        return "|".join(flags)
    return f"0x{attrs:x}" if hex_if_empty else ""

def attrs_to_mode(attrs, is_dir):
    if is_dir: return "d/drwxrwxrwx"
    if attrs & 0x400: return "l/lrwxrwxrwx"
    r = "-" if attrs & 0x01 else "r"
    return f"-/{r}rwxrwxrwx"

def parse_sid(data, offset):
    """Parse a SECURITY_DESCRIPTOR SID at offset -> (sid_string, sid_len). On a
    malformed/truncated SID returns the sentinel '(invalid)'/'(truncated)' (single
    canonical behaviour; refsanalysis imports this)."""
    if offset + 8 > len(data): return "(invalid)", 0
    revision = data[offset]
    sub_count = data[offset + 1]
    # A structurally valid SID has revision == 1 (SID_REVISION) and <= 15 sub-authorities
    # (SID_MAX_SUB_AUTHORITIES). Reject impossible values so a corrupt SD can't emit a fake
    # 'S-88-...' into the OwnerSid column (E13). reference_table FS_SECD_RA_001: all SDs revision=1.
    if revision != 1 or sub_count > 15: return "(invalid)", 0
    authority = int.from_bytes(data[offset+2:offset+8], "big")
    sid_len = 8 + sub_count * 4
    if offset + sid_len > len(data): return "(truncated)", sid_len
    subs = [le32(data, offset + 8 + i * 4) for i in range(sub_count)]
    return f"S-{revision}-{authority}" + "".join(f"-{s}" for s in subs), sid_len

def sid_name(sid_str):
    """Friendly NAME for a SID (name only; callers append ' (SID)'). '' = unknown
    (callers then show the raw SID). Domain RIDs keep the RID for non-builtin users."""
    if sid_str in WELL_KNOWN_SIDS:
        return WELL_KNOWN_SIDS[sid_str]
    if sid_str.startswith("S-1-5-21-"):
        rid = sid_str.rsplit("-", 1)[-1]
        try:
            rid_int = int(rid)
            if rid_int == 500: return "Administrator"
            if rid_int == 501: return "Guest"
            if rid_int == 512: return "Domain Admins"
            if rid_int == 513: return "Domain Users"
            if rid_int == 514: return "Domain Guests"
            return f"DomainUser (RID={rid_int})"
        except ValueError: pass
        return "DomainUser"
    return ""

def ext_from_name(name):
    if "." in name:
        e = name.rsplit(".", 1)[-1]
        if len(e) <= 10: return f".{e}"
    return ""

# ─── GPT + VBR + SUPB + CHKP ─────────────────────────────────────────
def parse_vbr(f, ps):
    f.seek(ps); bs = f.read(512)
    if bs[3:7] != b"ReFS":
        sig = bs[3:15].rstrip(b'\x00').decode('ascii', errors='replace')
        if b"NTFS" in bs[:16]:
            raise ValueError(f"partition contains NTFS, not ReFS (signature: '{sig}')")
        elif b"-FVE-FS-" in bs[:16]:
            raise ValueError("partition is BitLocker-encrypted (signature: -FVE-FS-)")
        raise ValueError(f"partition does not contain ReFS (VBR signature: '{sig}')")
    bps = le32(bs, 0x20)
    spc = le32(bs, 0x24)
    cs = bps * spc
    vmaj = bs[0x28]
    vmin = bs[0x29]
    chk_algo = le16(bs, 0x2A)   # C6: VBR 0x2A is a u16 selector (vbr.md); low byte carries 0/2/4, 0x2B==0 on all corpus images
    bpc = le64(bs, 0x40) if le64(bs, 0x40) != 0 else 0x4000000
    return cs, vmaj, vmin, chk_algo, bpc

def parse_supb(f, ps, cs):
    f.seek(ps + SUPB_LCN * cs); data = f.read(cs)
    if data[:4] != b"SUPB": raise ValueError("Bad SUPB")
    off = le32(data, 0x70); cnt = le32(data, 0x74)
    # E9: clamp the on-disk count (doc: always 2). A fuzzed/corrupt cnt (e.g. 0xFFFFFFFF) would build a
    # multi-billion-entry list and hang; also bound to the page so an out-of-range off can't over-read.
    if cnt > 8 or off + cnt * 8 > len(data):
        safe = max(0, min(cnt, 8, (len(data) - off) // 8 if off < len(data) else 0))
        print(f"[{PROG}] WARNING: SUPB checkpoint-ref count {cnt} implausible (doc=2); clamped to {safe}", file=sys.stderr)
        cnt = safe
    return [le64(data, off + i * 8) for i in range(cnt)]

def parse_chkp(f, ps, cs, lcn):
    f.seek(ps + lcn * cs); raw = f.read(4 * cs)
    if raw[:4] != b"CHKP": raise ValueError("Bad CHKP")
    vclock = le64(raw, 0x10)
    flags = le32(raw, 0x78)
    desc_len = le32(raw, 0x5c)
    indirect = bool(flags & 0x200)
    root_count = le32(raw, 0x90)
    # E9: clamp (doc: always 13; capacity field 0x8C = 0x20 = 32). A fuzzed count would loop billions of times.
    if root_count > 32:
        print(f"[{PROG}] WARNING: CHKP root count {root_count} implausible (doc=13, cap=32); clamped to 32", file=sys.stderr)
        root_count = 32
    olb = le32(raw, 0x94) if indirect else 0x94
    roots = []
    for idx in range(root_count):
        oe = olb + idx * 4
        if oe + 4 > len(raw): roots.append([]); continue
        ro = le32(raw, oe)
        if ro == 0 or ro + desc_len > len(raw): roots.append([]); continue
        rec = raw[ro:ro+desc_len]
        slots = [le64(rec, i*8) for i in range(4)]
        roots.append([s for s in slots if s not in (0, 0xFFFFFFFFFFFFFFFF)])
    return vclock, flags, roots

# ─── Container Table + Translator ─────────────────────────────────────
def _select_ct_root(f, ps, cs, roots):
    """Pick the Container Table root by its on-disk Table-ID (0x0B), NOT by assuming root index 7.

    The Container-Table failover pair (roots 7 & 8) is not bound to a fixed index->id order (finding #337):
    on some volumes (e.g. a 2 TB volume) root 7 carries the duplicate (0x0C) and root 8 the primary (0x0B).
    Roots 7/8/12 use REAL physical LCNs, so the table-root page is read directly (no translation needed yet).
    Returns the vlcn-list for the primary CT (id 0x0B); falls back to the duplicate (0x0C), then to index 7.
    """
    def tid_of(ri):
        if ri >= len(roots) or not roots[ri]:
            return None
        try:
            f.seek(ps + roots[ri][0] * cs); pg = f.read(cs)
            return le64(pg, 0x48) if pg[:4] == b"MSB+" else None
        except Exception:
            return None
    ids = {ri: tid_of(ri) for ri in (7, 8)}
    for want in (0x0B, 0x0C):                       # prefer primary 0x0B, then duplicate 0x0C
        for ri in (7, 8):
            if ids.get(ri) == want and roots[ri]:
                return roots[ri]
    return roots[7] if len(roots) > 7 and roots[7] else []   # legacy fallback

def _parse_ct_page(page, f, ps, cs, _depth=0):
    # _depth guard: the Container Table is a shallow B+ tree; 64 bounds a circular/corrupt CT (never trips
    # on valid data) to prevent unbounded recursion. Defaulted kwarg — existing callers are unaffected.
    if page[:4] != b"MSB+" or _depth > 64: return {}
    thoff = 0x50 + le32(page, 0x50)
    if thoff + 40 > len(page): return {}
    tbl = struct.unpack_from("<10I", page, thoff)
    is_inner = bool(tbl[3] & 0x100)
    astart, aend = tbl[4], tbl[8]
    if astart >= aend: return {}
    result = {}
    for i in range((aend - astart) // 4):
        aa = thoff + astart + i * 4
        if aa + 4 > len(page): break
        ro = thoff + le16(page, aa)
        if ro + 16 > len(page): break
        rh = struct.unpack_from("<I6H", page, ro)
        _, ko, kl, _, vo, vl, _ = rh
        kd = page[ro+ko:ro+ko+kl] if kl > 0 else b""
        vd = page[ro+vo:ro+vo+vl] if vl > 0 else b""
        key = le64(kd, 0) if len(kd) >= 8 else 0
        if is_inner:
            if len(vd) >= 32:
                cls = [le64(vd, j*8) for j in range(4)]
                valid = [x for x in cls if x not in (0, 0xFFFFFFFFFFFFFFFF)]
                if valid:
                    cd = b""
                    for l in valid: f.seek(ps + l * cs); cd += f.read(cs)
                    result.update(_parse_ct_page(cd, f, ps, cs, _depth + 1))
        else:
            if len(vd) >= 0x98:
                result[key] = (le64(vd, len(vd) - 16), le32(vd, 0x18))
    return result

class Translator:
    def __init__(self, m, cpc):
        self.map = m; self.cpc = cpc
        # Q9: the shift is bit_length() (= log2(cpc)+1), NOT log2(cpc), and this is CORRECT — not an off-by-one.
        # The driver does exactly this: GetContainerIdFromRealRange adds 1 to the log2 width, and
        # IsValidContainerLcn guarantees the container-boundary bit is 0, so the extra shifted bit is always
        # clear. cpc is a power of two, so mask = cpc-1 recovers the in-container offset. (docs/structures/
        # container_table.md.) Do not "fix" this to bit_length()-1.
        self.shift = cpc.bit_length() if cpc > 0 else 0
        self.mask = cpc - 1 if cpc > 0 else 0
        self.misses = 0   # E11: count VLCNs with no container mapping (unmapped => read as identity)
    def tr(self, vlcn):
        cid = vlcn >> self.shift
        if cid in self.map:
            return self.map[cid] + (vlcn & self.mask)
        # E11: an unmapped container (corrupt/truncated CT, or a wrong-mode read) falls back to identity
        # (VLCN read as PLCN). That silently loses evidence downstream; count it so callers can surface it.
        self.misses += 1
        return vlcn

# ─── B+ tree walker ──────────────────────────────────────────────────
def walk_bplus(f, ps, cs, tr, vlcns, max_depth=5):
    plcns = [tr.tr(v) for v in vlcns] if tr else vlcns
    page = b""
    for p in plcns: f.seek(ps + p * cs); page += f.read(cs)
    return _walk(page, f, ps, cs, tr, max_depth)

def _walk(page, f, ps, cs, tr, depth, visited=None):
    # E10: cycle/re-read protection. A corrupt inner node whose child pointers repeat an ancestor page
    # would otherwise fan out ~4^depth and re-read identical pages. `visited` is a per-walk set keyed on
    # (addressing-mode, head-PLCN) — the mode bit is essential so a translated VLCN and a physical LCN
    # sharing a numeric value are NOT merged (which would drop a real page). On a well-formed tree every
    # child page is referenced exactly once, so this NEVER skips a legitimate page (output unchanged).
    if visited is None: visited = set()
    if depth <= 0 or len(page) < 4 or page[:4] != b"MSB+": return []
    thoff = 0x50 + le32(page, 0x50)
    if thoff + 40 > len(page): return []
    tbl = struct.unpack_from("<10I", page, thoff)
    is_inner = bool(tbl[3] & 0x100)
    astart, aend = tbl[4], tbl[8]
    if astart >= aend: return []
    rows = []
    for i in range((aend - astart) // 4):
        aa = thoff + astart + i * 4
        if aa + 4 > len(page): break
        ro = thoff + le16(page, aa)
        if ro + 16 > len(page): break
        rh = struct.unpack_from("<I6H", page, ro)
        _, ko, kl, _, vo, vl, _ = rh
        kd = page[ro+ko:ro+ko+kl] if kl > 0 else b""
        vd = page[ro+vo:ro+vo+vl] if vl > 0 else b""
        if is_inner:
            if len(vd) >= 32:
                cvs = [le64(vd, j*8) for j in range(4)]
                cvld = [x for x in cvs if x not in (0, 0xFFFFFFFFFFFFFFFF)]
                cps = [tr.tr(v) for v in cvld] if tr else cvld
                head = (tr is not None, cps[0]) if cps else None
                if head is not None and head in visited:
                    continue                     # already-walked / cyclic child page — skip
                if head is not None:
                    visited.add(head)
                cp = b""
                for p in cps: f.seek(ps + p * cs); cp += f.read(cs)
                rows.extend(_walk(cp, f, ps, cs, tr, depth-1, visited))
        else:
            rows.append((kd, vd))
    return rows

# ─── Object Table ────────────────────────────────────────────────────
def build_object_map(f, ps, cs, tr, ot_vlcns):
    rows = walk_bplus(f, ps, cs, tr, ot_vlcns)
    objects = {}
    for kd, vd in rows:
        if len(kd) < 16 or len(vd) < 64: continue
        oid = le64(kd, 8)
        lcns = [le64(vd, 0x20 + j*8) for j in range(4)]
        valid = [s for s in lcns if s not in (0, 0xFFFFFFFFFFFFFFFF)]
        objects[oid] = valid
    return objects

# ─── Security Descriptor Table ────────────────────────────────────────
def build_security_map(f, ps, cs, tr, obj_map):
    """Build SecurityId → (Owner SID, Group SID) mapping from OID 0x530.

    SD table key (16 bytes): [val_size(4)] [pad(4)] [sid_high(4)] [sid_low(4)]
    SecurityId = (sid_high << 32) | sid_low
    SD table value: [hash(4)] [count(4)] [size(4)] [SECURITY_DESCRIPTOR_RELATIVE...]
    Within the SD (= value[12:]): owner_off u32 @SD+4, GROUP_OFF u32 @SD+8 (read
    identically to owner). Group verified on disk (H3, 2026-06-29): 2383/2383 SDs valid,
    distinct from owner ~56% of the time; group_off==0 (no group) handled but never occurs.
    Each value is (owner_sid_str, group_sid_str); '' = absent.
    """
    if 0x530 not in obj_map:
        return {}
    vlcns = obj_map[0x530]
    rows = walk_bplus(f, ps, cs, tr, vlcns)
    sd_map = {}
    for kd, vd in rows:
        # Extract SecurityId from key
        if len(kd) >= 16:
            sid_high = le32(kd, 8)
            sid_low = le32(kd, 12)
            sec_id = (sid_high << 32) | sid_low
        elif len(kd) >= 8:
            sec_id = le64(kd, 0)
        else:
            continue

        # SD value: 12-byte header then SECURITY_DESCRIPTOR_RELATIVE
        SD_HDR = 12
        if len(vd) < SD_HDR + 20:
            continue
        sd_data = vd[SD_HDR:]
        if sd_data[0] != 1:  # Revision must be 1
            continue
        off_owner = le32(sd_data, 4)
        owner_str = ""
        if 0 < off_owner < len(sd_data):
            owner_str, _ = parse_sid(sd_data, off_owner)
        off_group = le32(sd_data, 8)
        group_str = ""
        if 0 < off_group < len(sd_data):
            group_str, _ = parse_sid(sd_data, off_group)
        sd_map[sec_id] = (owner_str, group_str)
    return sd_map

# ─── Trash Table ─────────────────────────────────────────────────────
def build_trash_set(f, ps, cs, tr, obj_map):
    """Get set of OIDs in the Trash Table (OID 0xD)."""
    if 0xD not in obj_map:
        return set()
    vlcns = obj_map[0xD]
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception:
        return set()
    trashed = set()
    for kd, vd in rows:
        if len(kd) >= 16:
            trashed.add(le64(kd, 8))
        elif len(kd) >= 8:
            trashed.add(le64(kd, 0))
    return trashed

# ─── Orphan Object Detection ─────────────────────────────────────────
def find_orphan_objects(f, ps, cs, tr, obj_map, referenced_oids, log_fn=None):
    """Find OIDs in the Object Table that are not referenced from the directory tree.

    These are likely recently deleted files whose Object Table entries
    have not yet been reclaimed by the garbage collector. For each orphan,
    attempts to read its B+ tree to recover filename and timestamps.
    """
    # System OIDs to exclude (known tables, not user files)
    SYSTEM_OIDS = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                   0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x20, 0x21, 0x22,
                   0x30, 0x500, 0x501, 0x520, 0x530, 0x540, 0x541, 0x600}
    orphan_oids = set(obj_map.keys()) - referenced_oids - SYSTEM_OIDS
    # Also exclude very low OIDs (internal system tables)
    orphan_oids = {o for o in orphan_oids if o > 0x600}

    if log_fn:
        log_fn(f"[{PROG}] {len(orphan_oids)} orphan OIDs found in Object Table")

    results = []
    for oid in sorted(orphan_oids):
        vlcns = obj_map.get(oid)
        if not vlcns:
            continue
        try:
            rows = walk_bplus(f, ps, cs, tr, vlcns)
        except Exception:
            continue

        # Try to recover file metadata from the orphan's B+ tree
        name = None
        si_data = {}
        for kd, vd in rows:
            if len(kd) < 2:
                continue
            attr_type = le16(kd, 0)
            if attr_type == 0x10 and len(vd) >= 0x60 and not si_data:
                si_data = {
                    "create_time": le64(vd, 0x28),
                    "modify_time": le64(vd, 0x30),
                    "change_time": le64(vd, 0x38),
                    "access_time": le64(vd, 0x40),
                    "file_attrs": le32(vd, 0x48),
                    "security_id": le64(vd, 0x50),
                    # usn = LastUsn ($SI+0x40 / value+0x68); value+0x58 ($SI+0x30) is unpopulated. E30/E45.
                    "usn": le64(vd, 0x68) if len(vd) >= 0x70 else 0,
                }
            elif attr_type == 0x30 and len(kd) > 4 and name is None:
                try:
                    name = kd[4:].decode("utf-16-le").rstrip("\x00")
                except UnicodeDecodeError:
                    pass

        if not name and not si_data:
            continue

        fa = si_data.get("file_attrs", 0)
        # E7: an orphan OID is in the Object Table, so it is a DIRECTORY (#327: non-resident files have
        # no own OID). Its B+-tree holds its CHILDREN's type-0x30 rows, so the recovered `name` is a
        # child, not the directory itself — label the row by the directory's OID (not the child name),
        # keep the recovered child as a note, and derive is_dir structurally (the masked/absent attrs
        # bit reads False for these). Validated on win11refs2tmillionsofactionsv2 (3 orphan dirs).
        entry = {
            "path": f"$ORPHAN/DIR_OID_0x{oid:x}",
            "parent_path": "$ORPHAN",
            "parent_oid": 0,
            "name": f"DIR_OID_0x{oid:x}",
            "recovered_child": name or "",
            "oid": oid,
            "is_resident": False,
            "is_dir": True,
            "is_deleted": True,
            "deletion_source": "orphan",
            "create_time": si_data.get("create_time", 0),
            "modify_time": si_data.get("modify_time", 0),
            "change_time": si_data.get("change_time", 0),
            "access_time": si_data.get("access_time", 0),
            "file_attrs": fa,
            "internal_flags": si_data.get("internal_flags", 0),
            "security_id": si_data.get("security_id", 0),
            "usn": si_data.get("usn", 0),
            "file_size": 0,
            "is_encrypted": bool(fa & 0x4000),
            "is_compressed": bool(fa & 0x0800),
            "has_integrity": bool(fa & 0x8000),
            "has_ea": bool(fa & 0x00040000),
            "has_reparse": bool(fa & 0x0400),
            "has_ads": False, "ads_names": "",
            "reparse_target": "",
            "snapshot_count": 0,
        }
        results.append(entry)
    return results

# ─── Checkpoint Comparison for Deleted Files ──────────────────────────
def find_chkp_diff_deleted(f, ps, cs, chkp_lcns, current_obj_map, log_fn=None):
    """Compare both CHKP copies to find files present in older but absent from current tree.

    ReFS maintains two checkpoints (A/B). The older one represents the previous
    transaction state. Files deleted in the last transaction appear in the older
    tree but not the current one.
    """
    # Parse both checkpoints
    chkps = []
    for lcn in chkp_lcns:
        try:
            vc, flags, roots = parse_chkp(f, ps, cs, lcn)
            chkps.append((vc, flags, roots, lcn))
        except Exception:
            continue
    if len(chkps) < 2:
        return []

    # Sort by vclock: [0]=older, [1]=newer
    chkps.sort(key=lambda x: x[0])
    older_vc, older_flags, older_roots, _ = chkps[0]
    newer_vc, _, _, _ = chkps[1]

    if older_vc == newer_vc:
        return []  # Same checkpoint, no diff

    if log_fn:
        log_fn(f"[{PROG}] Comparing checkpoints: vclock {older_vc} vs {newer_vc}")

    # Build container table from the OLDER checkpoint — select by Table-ID 0x0B, not index 7 (#337)
    try:
        ct_vlcns = _select_ct_root(f, ps, cs, older_roots)
        ct_page = b""
        for l in ct_vlcns: f.seek(ps + l * cs); ct_page += f.read(cs)
        ct_map_raw = _parse_ct_page(ct_page, f, ps, cs)
        ct_map = {k: v[0] for k, v in ct_map_raw.items()}
        f.seek(ps); bs = f.read(512)
        bpc = le64(bs, 0x40) if le64(bs, 0x40) != 0 else 0x4000000
        cs_val = le32(bs, 0x20) * le32(bs, 0x24)
        cpc = bpc // cs_val
        old_tr = Translator(ct_map, cpc)
    except Exception:
        return []

    # Build object map from older checkpoint
    try:
        ot_vlcns = older_roots[0] if len(older_roots) > 0 else []
        old_obj_map = build_object_map(f, ps, cs, old_tr, ot_vlcns)
    except Exception:
        return []

    # E15: the former `old_files = _collect_dir_entries(... old tree ...)` walk was DEAD (filled, never
    # read — deletions are identified purely by the OID-set difference below). Removed the full extra
    # recursive tree walk and the unused `current_dir_oids` parameter.

    # The current tree's names come from the main walk; deleted files are identified purely by the
    # OID set difference below (the former current_files collection here was computed and never read).
    # Files whose OID is in old_obj_map but NOT in current_obj_map were deleted.
    old_only_oids = set(old_obj_map.keys()) - set(current_obj_map.keys())
    # Exclude system OIDs
    old_only_oids = {o for o in old_only_oids if o > 0x600}

    if log_fn:
        log_fn(f"[{PROG}] {len(old_only_oids)} OIDs in older checkpoint only")

    results = []
    for oid in sorted(old_only_oids):
        vlcns = old_obj_map.get(oid)
        if not vlcns:
            continue
        try:
            rows = walk_bplus(f, ps, cs, old_tr, vlcns)
        except Exception:
            continue

        name = None
        si_data = {}
        for kd, vd in rows:
            if len(kd) < 2: continue
            attr_type = le16(kd, 0)
            if attr_type == 0x10 and len(vd) >= 0x60 and not si_data:
                si_data = {
                    "create_time": le64(vd, 0x28), "modify_time": le64(vd, 0x30),
                    "change_time": le64(vd, 0x38), "access_time": le64(vd, 0x40),
                    "file_attrs": le32(vd, 0x48), "security_id": le64(vd, 0x50),
                    # usn = LastUsn ($SI+0x40 / value+0x68); value+0x58 unpopulated. E30/E45.
                    "usn": le64(vd, 0x68) if len(vd) >= 0x70 else 0,
                }
            elif attr_type == 0x30 and len(kd) > 4 and name is None:
                try: name = kd[4:].decode("utf-16-le").rstrip("\x00")
                except UnicodeDecodeError: pass

        if not name and not si_data:
            continue

        fa = si_data.get("file_attrs", 0)
        entry = {
            # E7: Object Table OID => directory (#327); label by the dir OID, keep the child as a note.
            "path": f"$DELETED_PREV_CHKP/DIR_OID_0x{oid:x}",
            "parent_path": "$DELETED_PREV_CHKP",
            "parent_oid": 0,
            "name": f"DIR_OID_0x{oid:x}",
            "recovered_child": name or "",
            "oid": oid,
            "is_resident": False,
            "is_dir": True,
            "is_deleted": True,
            "deletion_source": "chkp_diff",
            "create_time": si_data.get("create_time", 0),
            "modify_time": si_data.get("modify_time", 0),
            "change_time": si_data.get("change_time", 0),
            "access_time": si_data.get("access_time", 0),
            "file_attrs": fa,
            "internal_flags": 0,
            "security_id": si_data.get("security_id", 0),
            "usn": si_data.get("usn", 0),
            "file_size": 0,
            "is_encrypted": bool(fa & 0x4000),
            "is_compressed": bool(fa & 0x0800),
            "has_integrity": bool(fa & 0x8000),
            "has_ea": bool(fa & 0x00040000),
            "has_reparse": bool(fa & 0x0400),
            "has_ads": False, "ads_names": "",
            "reparse_target": "",
            "snapshot_count": 0,
        }
        results.append(entry)
    return results


# ─── Forward CoW Version Recovery (cross-image comparison) ───────────
def cow_recovery(f_after, ps_a, cs_a, tr_a, obj_map_a,
                 before_image, partition_start_before, log_fn):
    """Recover previous file versions via forward CoW Object Table comparison.

    Compares the Object Table between a BEFORE image and the current (AFTER)
    image. Files whose per-object B+ tree page VLCNs differ were modified;
    files present only in BEFORE were deleted. For each, reads old metadata
    (name, timestamps, size) from the BEFORE image and checks whether old
    B+ tree pages survive on the AFTER image (MSB+ signature).

    This is the forward direction (file -> old clusters): only two Object
    Table walks are needed, no full disk scan.

    Returns list of entry dicts compatible with the main forefst output.
    """
    # Bootstrap BEFORE image
    try:
        f_b, ps_b, cs_b, tr_b, roots_b, obj_map_b, vmaj_b, vmin_b, _ = bootstrap(
            before_image, partition_start_before)
    except (ValueError, OSError) as e:
        log_fn(f"[{PROG}] CoW: cannot open BEFORE image: {e}")
        return []

    try:
        if cs_b != cs_a:
            log_fn(f"[{PROG}] CoW: cluster size mismatch "
                   f"(BEFORE={cs_b}, AFTER={cs_a}), skipping")
            return []

        # Compare object maps (user objects only, OID >= 0x600)
        modified = []
        deleted = []
        for oid in sorted(obj_map_b):
            if oid < 0x600:
                continue
            if oid not in obj_map_a:
                deleted.append(oid)
            elif tuple(obj_map_b[oid]) != tuple(obj_map_a[oid]):
                modified.append(oid)

        created_count = sum(1 for o in obj_map_a if o >= 0x600 and o not in obj_map_b)
        log_fn(f"[{PROG}] CoW: {len(modified)} modified, {len(deleted)} deleted, "
               f"{created_count} created (user objects)")

        if not modified and not deleted:
            log_fn(f"[{PROG}] CoW: no changes detected between images")
            return []

        # Extract old metadata for each modified/deleted object
        results = []
        pages_survived = 0
        pages_total = 0

        for oid in modified + deleted:
            vlcns = obj_map_b[oid]

            # Read per-object B+ tree from BEFORE image
            try:
                rows = walk_bplus(f_b, ps_b, cs_b, tr_b, vlcns)
            except Exception:
                continue

            name = None
            si = {}
            file_size = 0

            for kd, vd in rows:
                if len(kd) < 2:
                    continue
                at = le16(kd, 0)
                if at == 0x30 and len(kd) > 4 and name is None:
                    try:
                        name = kd[4:].decode("utf-16-le").rstrip("\x00")
                    except UnicodeDecodeError:
                        pass
                if at == 0x10 and len(vd) >= 0x60 and not si:
                    si = {
                        "create_time": le64(vd, 0x28),
                        "modify_time": le64(vd, 0x30),
                        "change_time": le64(vd, 0x38),
                        "access_time": le64(vd, 0x40),
                        "file_attrs": le32(vd, 0x48),
                        "internal_flags": le32(vd, 0x4C),
                        "security_id": le64(vd, 0x50),
                        # usn = LastUsn ($SI+0x40 / value+0x68); value+0x58 unpopulated. E30/E45.
                        "usn": le64(vd, 0x68) if len(vd) >= 0x70 else 0,
                    }
                if at == 0x40 and len(vd) >= 0x60:
                    file_size = le64(vd, 0x58)

            if not name and not si:
                continue

            # Check if old B+ tree pages still have MSB+ on AFTER image
            obj_survived = 0
            for vlcn in vlcns:
                pages_total += 1
                try:
                    plcn = tr_b.tr(vlcn)
                    f_after.seek(ps_a + plcn * cs_a)
                    sig = f_after.read(4)
                    if sig == b"MSB+":
                        obj_survived += 1
                        pages_survived += 1
                except Exception:
                    pass

            fa = si.get("file_attrs", 0)
            status = "cow_modified" if oid in obj_map_a else "cow_deleted"

            entry = {
                # E7: Object Table OID => directory (#327); label by the dir OID, keep child as a note.
                "path": f"$COW_PREVIOUS/DIR_OID_0x{oid:x}",
                "parent_path": "$COW_PREVIOUS",
                "parent_oid": 0,
                "name": f"DIR_OID_0x{oid:x}",
                "recovered_child": name or "",
                "oid": oid,
                "is_resident": False,
                "is_dir": True,
                "is_deleted": True,
                "deletion_source": status,
                "create_time": si.get("create_time", 0),
                "modify_time": si.get("modify_time", 0),
                "change_time": si.get("change_time", 0),
                "access_time": si.get("access_time", 0),
                "file_attrs": fa,
                "internal_flags": si.get("internal_flags", 0),
                "security_id": si.get("security_id", 0),
                "usn": si.get("usn", 0),
                "file_size": file_size,
                "is_encrypted": bool(fa & 0x4000),
                "is_compressed": bool(fa & 0x0800),
                "has_integrity": bool(fa & 0x8000),
                "has_ea": bool(fa & 0x00040000),
                "has_reparse": bool(fa & 0x0400),
                "has_ads": False,
                "ads_names": "",
                "reparse_target": "",
                "snapshot_count": 0,
            }
            results.append(entry)

        if pages_total > 0:
            pct = 100 * pages_survived // pages_total
            log_fn(f"[{PROG}] CoW: {pages_survived}/{pages_total} old B+ tree pages "
                   f"still valid on AFTER image ({pct}%)")

        return results
    finally:
        f_b.close()


def _collect_dir_entries(f, ps, cs, tr, obj_map, oid, parent_path, out, visited, depth, max_depth):
    """Helper: collect directory entry names from a tree (for checkpoint comparison)."""
    if depth > max_depth or oid in visited or oid not in obj_map:
        return
    visited.add(oid)
    vlcns = obj_map[oid]
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception:
        return
    for kd, vd in rows:
        if len(kd) < 4 or le16(kd, 0) != 0x30: continue
        try: name = kd[4:].decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError: continue
        full_path = f"{parent_path}/{name}" if parent_path else name
        child_oid = 0
        if len(vd) <= NON_RESIDENT_MAX_VALUE and len(vd) >= 0x10:
            child_oid = le64(vd, 0x08)
        out[(oid, name)] = {"name": name, "path": full_path, "oid": child_oid}
        if child_oid and len(vd) <= NON_RESIDENT_MAX_VALUE and len(vd) >= 0x44:
            if le32(vd, 0x40) & 0x10000000:
                _collect_dir_entries(f, ps, cs, tr, obj_map, child_oid, full_path, out, visited, depth+1, max_depth)


# ─── Inline reparse target extraction (for resident entries) ──────────
def extract_inline_reparse(vd):
    """Extract reparse target from a resident entry's embedded attributes."""
    SYMLINK_TAG = b"\x0c\x00\x00\xa0"
    MOUNT_TAG = b"\x03\x00\x00\xa0"
    LX_SYM_TAG = b"\x1d\x00\x00\xa0"

    for tag_bytes, tag_val in [(SYMLINK_TAG, 0xA000000C), (MOUNT_TAG, 0xA0000003), (LX_SYM_TAG, 0xA000001D)]:
        search_start = 0xA8
        idx = vd.find(tag_bytes, search_start)
        if idx < 0 or idx + 20 > len(vd):
            continue
        data_len = le16(vd, idx + 4)
        if data_len < 4:
            continue

        if tag_val == 0xA000000C:  # SYMLINK
            sub_off = le16(vd, idx + 8)
            sub_len = le16(vd, idx + 10)
            print_off = le16(vd, idx + 12)
            print_len = le16(vd, idx + 14)
            buf_start = idx + 20
            if print_len > 0 and buf_start + print_off + print_len <= len(vd):
                try:
                    return vd[buf_start+print_off:buf_start+print_off+print_len].decode("utf-16-le")
                except UnicodeDecodeError:
                    pass
            if sub_len > 0 and buf_start + sub_off + sub_len <= len(vd):
                try:
                    target = vd[buf_start+sub_off:buf_start+sub_off+sub_len].decode("utf-16-le")
                    if target.startswith("\\??\\"):
                        target = target[4:]
                    return target
                except UnicodeDecodeError:
                    pass
        elif tag_val == 0xA0000003:  # MOUNT_POINT/JUNCTION
            sub_off = le16(vd, idx + 8)
            sub_len = le16(vd, idx + 10)
            print_off = le16(vd, idx + 12)
            print_len = le16(vd, idx + 14)
            buf_start = idx + 16
            if print_len > 0 and buf_start + print_off + print_len <= len(vd):
                try:
                    return vd[buf_start+print_off:buf_start+print_off+print_len].decode("utf-16-le")
                except UnicodeDecodeError:
                    pass
        elif tag_val == 0xA000001D:  # LX_SYMLINK
            # E5 fix: the LX_SYMLINK payload is u32 version(=2) + UTF-8 target; skip the 4-byte
            # version (idx+8 -> idx+12) so it does not prefix the target with "\x02\x00\x00\x00".
            try:
                return vd[idx+12:idx+8+data_len].decode("utf-8").rstrip("\x00")
            except UnicodeDecodeError:
                pass
        return REPARSE_TAGS.get(tag_val, f"0x{tag_val:08X}")
    return ""

def extract_reparse_from_backing(vd):
    """Validated REPARSE_DATA_BUFFER target path embedded in a NON-RESIDENT file's type-0x40
    backing record (v3.14). Scans for the symlink (0xA000000C) / junction (0xA0000003) buffer
    at its VARIABLE offset, decodes Print/Substitute name, and accepts only a real path; the
    +0x7C tag MIRROR (a bare tag dword, no valid buffer) is explicitly skipped so it is never
    mistaken for the buffer. Returns '' when no valid target embeds (e.g. v3.7-v3.10, whose
    live backing carries only the +0x7C mirror). H3-verified 2026-06-29: 100% on native v3.14,
    correctly empty on v3.7-v3.10. Caller selects the file's OWN backing via the verified
    hard-link resolution (home stream), which avoids the file_id-collision wrong-target bug."""
    for tag_bytes, has_flags in ((b"\x0c\x00\x00\xa0", True), (b"\x03\x00\x00\xa0", False)):
        pos = 0
        while True:
            idx = vd.find(tag_bytes, pos)
            if idx < 0:
                break
            pos = idx + 1
            if idx == 0x7C or idx + 0x10 > len(vd):   # 0x7C = the tag mirror, not the buffer
                continue
            sub_off = le16(vd, idx + 0x08); sub_len = le16(vd, idx + 0x0A)
            print_off = le16(vd, idx + 0x0C); print_len = le16(vd, idx + 0x0E)
            buf_start = idx + (0x14 if has_flags else 0x10)   # symlink has a 4-byte Flags field
            if print_len > 0 and buf_start + print_off + print_len <= len(vd):
                try:
                    t = vd[buf_start+print_off:buf_start+print_off+print_len].decode("utf-16-le")
                    if t and ("\\" in t or ":" in t):
                        return t
                except UnicodeDecodeError:
                    pass
            if sub_len > 0 and buf_start + sub_off + sub_len <= len(vd):
                try:
                    t = vd[buf_start+sub_off:buf_start+sub_off+sub_len].decode("utf-16-le")
                    if t.startswith("\\??\\"):
                        t = t[4:]
                    if t and ("\\" in t or ":" in t):
                        return t
                except UnicodeDecodeError:
                    pass
    return ""

# ─── Per-object $SI extraction ────────────────────────────────────────
def get_object_si(f, ps, cs, tr, vlcns):
    """Walk an object's B+ tree and extract $STANDARD_INFORMATION (type 0x10)."""
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception:
        return None
    for kd, vd in rows:
        if len(kd) >= 2 and le16(kd, 0) == 0x10:
            result = {}
            if len(vd) >= 0x60:
                result["create_time"] = le64(vd, 0x28)
                result["modify_time"] = le64(vd, 0x30)
                result["change_time"] = le64(vd, 0x38)
                result["access_time"] = le64(vd, 0x40)
                result["file_attrs"] = le32(vd, 0x48)
                result["internal_flags"] = le32(vd, 0x4C)
                result["security_id"] = le64(vd, 0x50)
                # CORRECTED 2026-06-17 (disk-proven, errata E30 retracted / E45): the file's
                # USN-journal pointer is LastUsn at $SI+0x40 (value+0x68), NOT $SI+0x30 (value+0x58).
                # value+0x58 ($SI+0x30) is 0 on 0/32,629 own-rows corpus-wide — never a populated USN.
                # LastUsn = virtual byte offset of the file's most recent $UsnJrnl:$J record (OID 0x520).
                result["usn"] = le64(vd, 0x68) if len(vd) >= 0x70 else 0
                result["usn_journal_id"] = le64(vd, 0x70) if len(vd) >= 0x78 else 0
            return result
    return None

# ─── ADS detection in per-object B+ tree ──────────────────────────────
def detect_ads(f, ps, cs, tr, vlcns):
    """Check if an object has Alternate Data Streams (type 0x80, marker 0x80000002)."""
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception:
        return False, []
    ads_names = []
    for kd, vd in rows:
        if len(kd) >= 4:
            attr_type = le16(kd, 0)
            if attr_type == 0x80 and len(kd) > 4:
                try:
                    stream_name = kd[4:].decode("utf-16-le").rstrip("\x00")
                    if stream_name:
                        ads_names.append(stream_name)
                except UnicodeDecodeError:
                    pass
    return len(ads_names) > 0, ads_names

# ─── Embedded B+-tree row parser (shared by snapshot/ADS/file-size) ───
_B0_MARKER = b"\x02\x00\x00\x80"  # 0x80000002 little-endian (multi-instance)
_SI_MARKER = b"\x01\x00\x00\x80"  # 0x80000001 little-endian (single-instance)


def parse_resident_btree_rows(vd):
    """Parse embedded B+-tree row offset table in a resident directory entry value.

    Returns list of (key_bytes, value_bytes) tuples for all rows found.
    Row offset table is at the end of vd (4-byte entries: u16 offset + 0xFFFF marker).
    Base offset for the data area is le32(vd, 0).
    """
    if len(vd) < 0xC0:
        return []
    base = le32(vd, 0)
    if base < 0x28 or base >= len(vd) - 0x28:
        return []
    offsets = []
    pos = len(vd) - 4
    while pos >= base:
        if le16(vd, pos + 2) != 0xFFFF:
            break
        offsets.append(le16(vd, pos))
        pos -= 4
    rows = []
    for off in offsets:
        abs_off = base + off
        if abs_off + 16 > len(vd):
            continue
        rh = struct.unpack_from("<I6H", vd, abs_off)
        _, ko, kl, _, vo, vl, _ = rh
        if ko == 0 or kl == 0:
            continue
        key_abs = abs_off + ko
        val_abs = abs_off + vo
        if key_abs + kl > len(vd) or val_abs + vl > len(vd):
            continue
        rows.append((bytes(vd[key_abs:key_abs + kl]),
                      bytes(vd[val_abs:val_abs + vl])))
    return rows


def _is_b0_snapshot_key(kd):
    """True if B+-tree key is a 0xB0 embedded attribute (marker 0x80000002 + type 0xB0)."""
    return (len(kd) >= 14 and kd[8:12] == _B0_MARKER
            and kd[12] == 0xB0 and kd[13] == 0x00)


def _is_snapshot_value(vd):
    """True if the StreamSummary flags at val+0x10 == 2 (snapshot, not ADS).
    C11: the field is a u16 at 0x10 (0=ADS, 2=snapshot; +0x12 reserved-zero). The old le32!=0 read
    worked only by coincidence (0x12==0); le16==2 matches the doc and recover_snapshot_streams."""
    return len(vd) >= 0x14 and le16(vd, 0x10) == 2


def count_snapshots_in_resident(vd):
    """Count true snapshot entries within a resident directory entry value."""
    count = 0
    for kd, vd_row in parse_resident_btree_rows(vd):
        if _is_b0_snapshot_key(kd) and _is_snapshot_value(vd_row):
            count += 1
    return count


# ─── Resident file-size extraction ───────────────────────────────────
def get_resident_file_size(vd):
    """Extract file content size from the $DATA sub-record in a resident value.

    The $DATA row in the embedded B+-tree has key marker 0x80000001 + attr type 0x80.
    Stream size is at value offset 0x20.
    """
    for kd, vd_row in parse_resident_btree_rows(vd):
        if (len(kd) >= 14 and kd[8:12] == _SI_MARKER
                and kd[12] == 0x80 and kd[13] == 0x00):
            if len(vd_row) >= 0x28:
                return le64(vd_row, 0x20)
    # Fallback: a stream-snapshotted / CoW'd resident file has no live 0x80000001 $DATA row — its
    # live stream lives in the type-0x80 descriptor-0x10028 holder keyed by the CURRENT sub_id 0x1000
    # (older snapshots are 0x1001, 0x1002, ...). The current content byte size is at value+0x38.
    # (E2/RD: win11refs2tsnapshots — arg.txt=15, lasttest.txt=201, test.txt=5.)
    for kd, vd_row in parse_resident_btree_rows(vd):
        if (len(kd) >= 0x18 and kd[12] == 0x80 and kd[13] == 0x00
                and len(vd_row) >= 0x40 and le32(vd_row, 4) == SNAP_DATA_DESC
                and le64(kd, 0x10) == 0x1000):
            return le64(vd_row, 0x38)
    return 0


def get_resident_data_content(vd):
    """Q7: inline bytes of the main $DATA stream of a resident file, or None.

    The $DATA row (key marker 0x80000001 + attr type 0x80) carries the SAME stream descriptor as an ADS
    row (see _parse_ads_from_value): locate it by the 0x0C/0x30 signature (hdr=scan-4), read storage_type
    at hdr+0x0C, stream size at hdr+0x1C, and inline content at hdr+0x38. Only storage_type==0 is inline
    (verified on desktop.ini: content '[.ShellClassInfo]...' at hdr+0x38). Returns None for a non-inline
    ($DATA descriptor pointing to extents) or malformed row — the caller falls back to the extent path."""
    for kd, vrow in parse_resident_btree_rows(vd):
        if not (len(kd) >= 14 and kd[8:12] == _SI_MARKER and kd[12] == 0x80 and kd[13] == 0x00):
            continue
        hdr = None
        for scan in range(0, len(vrow) - 8):
            if le32(vrow, scan) == 0x0C and le32(vrow, scan + 4) == 0x30:
                hdr = scan - 4
                break
        if hdr is None or hdr < 0 or hdr + 0x24 > len(vrow):
            return None
        if le32(vrow, hdr + 0x0C) != 0:          # storage_type != 0 => non-inline (extent-backed)
            return None
        stream_size = le64(vrow, hdr + 0x1C)
        content_off = hdr + 0x38
        if content_off + stream_size <= len(vrow) and stream_size <= 0x100000:
            return bytes(vrow[content_off:content_off + stream_size])
        return None
    return None


def _current_stream_extent_backed(vd):
    """F5: True when a file's CURRENT $DATA stream lives in on-disk extents (so the file is NON-RESIDENT even
    though its type-0x30 value is 'long' > 84 B). The live stream is the sub_id-0x1000 holder whose descriptor
    is 0x00010028 (le32 @ holder value+0x04); its on-disk allocation is disk_alloc @ holder value+0x48. Older
    sub_ids (0x1001+) are CoW snapshots and are ignored. A genuine inline/resident file has no such holder
    (its $DATA is a single-instance 0x80000001 descriptor) or disk_alloc==0. (structure_reference §C.6;
    calibrated on win11refs8g.raw: bigsparse/rangefile/stomp_nonres disk_alloc>0 => non-resident,
    test.txt current-stream disk_alloc==0 => resident.)"""
    for kd, vrow in parse_resident_btree_rows(vd):
        if (len(kd) >= 0x18 and kd[12] == 0x80 and kd[13] == 0x00
                and le64(kd, 0x10) == 0x1000 and len(vrow) >= 8 and le32(vrow, 4) == 0x00010028):
            return len(vrow) >= 0x50 and le64(vrow, 0x48) > 0
    return False


def _multilevel_extent_backed_size(vd, cs):
    """B2: on v3.4/v3.9/upgraded framing a 'long' (>84 B) resident type-0x30 value can be a MULTI-LEVEL
    embedded B+-tree — parse_resident_btree_rows reaches only the OUTER level, so no inline $DATA row is
    found (get_resident_file_size == 0) even though the file has on-disk data. Such a file is actually
    NON-RESIDENT / extent-backed; its true FileSize is at value+0x58 and its allocated size at value+0x60.
    Returns the true file_size when the pattern holds, else None.
    Gate: no inline $DATA (get_resident_file_size==0) AND alloc (value+0x60) is a whole number of clusters
    (alloc>0 and alloc % cs == 0 — extents allocate whole clusters) AND 0<size<=alloc. The cluster-alignment
    check is what distinguishes a real extent-backed file (alloc = N*cluster, e.g. xbpt_delta 209311/212992)
    from a small resident file whose value is merely unparseable (e.g. multibig_*.bin 300/304, alloc NOT a
    cluster multiple — NOT extent-backed). A genuine resident file also has an inline $DATA
    (get_resident_file_size>0), so it never reaches this. (Confirmed v3.4/v3.7/v3.9/v3.10/upgraded, 653
    files, all cluster-aligned; excludes the win11refs8g multibig_* resident misfires.)"""
    if len(vd) < 0x68 or cs <= 0:
        return None
    alloc = le64(vd, 0x60)
    if alloc == 0 or alloc % cs != 0 or get_resident_file_size(vd) != 0:
        return None
    size = le64(vd, 0x58)
    if 0 < size <= alloc:
        return size
    return None


# ─── Resident ADS detection ─────────────────────────────────────────
def detect_ads_in_resident(vd):
    """Detect Alternate Data Streams in a resident directory entry value.

    ADS appear as 0xB0 entries (marker 0x80000002) with StreamSummary flags=0
    at val[0x10] in the embedded B+-tree. Stream name is in the key at offset 16+.
    Returns (has_ads, ads_names) matching detect_ads() signature.
    """
    ads_names = []
    for kd, vd_row in parse_resident_btree_rows(vd):
        if _is_b0_snapshot_key(kd) and not _is_snapshot_value(vd_row):
            if len(kd) > 16:
                try:
                    name = kd[16:].decode("utf-16-le").rstrip("\x00")
                    if name:
                        ads_names.append(name)
                except UnicodeDecodeError:
                    pass
    return len(ads_names) > 0, ads_names


# ─── Extended Attributes ($EA) + WSL/Linux metadata ──────────────────────────
# VERIFIED 2026-06-29 (E2 + RD, report wsl_ea_verification_2026-06-29.md). EAs live as TWO embedded
# single-instance sub-records (marker 0x80000001) in the resident value's B+-tree: $EA_INFORMATION
# (type 0xD0, val[0x0C]=PackedEaSize) + $EA (type 0xE0, FILE_FULL_EA_INFORMATION chain at val+0x0C).
# refs.sys (RefsQueryLxMetadataEa) recognises EXACTLY four $LX EAs; all other EA values are opaque
# (name+size+raw only). NEVER source PackedEaSize from the value+0x78 mirror (stale on upgraded vols)
# or read device numbers from the reparse buffer (it has none).
def parse_ea_chain(data):
    """Parse a FILE_FULL_EA_INFORMATION chain -> [{'name','value','flags'}].
    Entry: NextEntryOffset u32@0, Flags u8@4, EaNameLength u8@5, EaValueLength u16@6,
    Name(ASCII)@8 (+1 null), Value@(8+nameLen+1). 0 NextEntryOffset = last."""
    eas = []
    off = 0
    for _ in range(256):
        if off + 8 > len(data):
            break
        nxt = le32(data, off)
        flags = data[off + 4]
        nlen = data[off + 5]
        vlen = le16(data, off + 6)
        name_end = off + 8 + nlen
        if name_end > len(data):
            break
        try:
            name = bytes(data[off + 8:name_end]).decode("ascii")
        except UnicodeDecodeError:
            name = bytes(data[off + 8:name_end]).decode("ascii", "replace")
        vstart = name_end + 1
        vend = vstart + vlen
        if vend > len(data):
            break
        eas.append({"name": name, "value": bytes(data[vstart:vend]), "flags": flags})
        if nxt == 0:
            break
        off += nxt
    return eas

def fetch_t40_backing(f, ps, cs, tr, obj_map, dir_oid, file_id, file_size=None):
    """Raw value bytes of the type-0x40 backing record for (dir_oid, file_id), or None. A non-resident
    file's EAs live in this backing. The per-dir file_id can COLLIDE (hard-link ordinal reuse); when
    several records share it, disambiguate by the file's size (val+0x58) — the same collision-safe rule
    the directory walk uses (#340). (The PackedEaSize==Σ oracle in the caller is the final guard.)"""
    if dir_oid not in obj_map:
        return None
    cands = []
    try:
        for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[dir_oid]):
            if len(kd) >= 0x10 and le16(kd, 0) == 0x40 and le64(kd, 0x08) == file_id:
                cands.append(bytes(vd))
    except Exception:
        return None
    if not cands:
        return None
    if file_size is not None and len(cands) > 1:
        for vd in cands:
            if len(vd) >= 0x60 and le64(vd, 0x58) == file_size:
                return vd
    return cands[0]

def extract_eas_from_value(vd):
    """(ea_list, packed_ea_size) from a resident value's embedded $EA/$EA_INFORMATION sub-records,
    or (None, None) if the file has no EAs ($EA_INFORMATION 0xD0 absent = the gate). packed_ea_size
    is read from the 0xD0 sub-record val[0x0C] (authoritative; never the +0x78 mirror)."""
    ea_info = None
    ea_chain = None
    for kd, vr in parse_resident_btree_rows(vd):
        if len(kd) >= 14 and kd[8:12] == _SI_MARKER and kd[13] == 0x00:
            if kd[12] == 0xD0 and len(vr) >= 0x10:
                ea_info = vr
            elif kd[12] == 0xE0 and len(vr) >= 0x0C:
                ea_chain = vr
    if ea_info is None:
        return None, None
    packed = le32(ea_info, 0x0C)
    eas = parse_ea_chain(ea_chain[0x0C:]) if ea_chain is not None else []
    return eas, packed

# Linux S_IFMT file types (mode & 0o170000) — verified vs lab mknod/chmod ground truth.
_LX_IFMT = {0o140000: "socket", 0o120000: "symlink", 0o100000: "regular", 0o060000: "block",
            0o040000: "directory", 0o020000: "char", 0o010000: "fifo"}

def decode_lx_mode(mode):
    """Decode a Linux mode_t (from $LXMOD) -> 'regular rwxr-xr-x (0o755)' with setuid/setgid/sticky."""
    ft = _LX_IFMT.get(mode & 0o170000, "unknown(0o%o)" % (mode & 0o170000))
    perms = "".join(("r" if (mode >> s) & 4 else "-") + ("w" if (mode >> s) & 2 else "-")
                    + ("x" if (mode >> s) & 1 else "-") for s in (6, 3, 0))
    extra = "".join(t for b, t in ((0o4000, " setuid"), (0o2000, " setgid"), (0o1000, " sticky")) if mode & b)
    return f"{ft} {perms} (0o{mode & 0o7777:04o}){extra}"

def decode_wsl_eas(eas):
    """Decode the FOUR driver-recognised $LX EAs (gated on the exact value lengths refs.sys requires:
    4 for UID/GID/MOD, 8 for DEV). Returns {uid,gid,mode,dev=(major,minor)} for those present."""
    wsl = {}
    for ea in eas:
        n, v = ea["name"], ea["value"]
        if n == "$LXUID" and len(v) == 4: wsl["uid"] = le32(v, 0)
        elif n == "$LXGID" and len(v) == 4: wsl["gid"] = le32(v, 0)
        elif n == "$LXMOD" and len(v) == 4: wsl["mode"] = le32(v, 0)
        elif n == "$LXDEV" and len(v) == 8: wsl["dev"] = (le32(v, 0), le32(v, 4))
    return wsl

# $SI+0x24 internal-flags labels — ONLY the bits with verified semantics (E25/E29/E43). Bits 0x04/0x08
# have a known FCB source (bit 11 / bit 31) but no confident semantic name, so they are left UNLABELLED
# (shown only in the raw hex) rather than guessed.
_INTERNAL_FLAG_LABELS = {0x01: "DeleteDisposition", 0x02: "Dedup/CoW", 0x20: "RedirectionTrust"}

# Checkpoint (CHKP+0x78) flag bits — meanings for the summary decode (Q4). Any bit NOT here is labelled
# 'unknown (uncatalogued)' so a new/unexpected flag is never silently dropped. (structure_reference §A.4a.)
_CHKP_FLAG_BITS = {
    0x002: "always-set",
    0x010: "dedup-bit4",
    0x020: "dedup-bit5",
    0x080: "native-Win11-format (v3.10+)",
    0x100: "dedup-bit8",
    0x200: "indirect-root-list",
    0x400: "metadata-checksum (CRC64/SHA-256)",
    0x2000: "insider-build flag (29574+)",
}

def chkp_flags_decoded(flags):
    """List of 'bit = meaning' strings for a CHKP flags value, incl. any uncatalogued residual bit."""
    out = [f"0x{b:03x} = {name}" for b, name in sorted(_CHKP_FLAG_BITS.items()) if flags & b]
    # OR-fold the catalogued bits into one mask (D7). `sum()` would over-count if any two flags ever
    # shared a bit or a flag became multi-bit; `|` is correct for any bit layout.
    catalogued = 0
    for _b in _CHKP_FLAG_BITS:
        catalogued |= _b
    residual = flags & ~catalogued
    if residual:
        out.append(f"0x{residual:x} = unknown (uncatalogued bit)")
    return out

def internal_flags_str(flags):
    """'0x28 (RedirectionTrust)' — shown ONLY when a confidently-verified bit is set. The common
    value 0x08 (FCB bit 31, no confident semantic) and other un-named bits are NOT surfaced (avoid
    displaying a field whose meaning is unproven)."""
    if not flags:
        return ""
    labels = [n for b, n in _INTERNAL_FLAG_LABELS.items() if flags & b]
    if not labels:
        return ""
    return f"0x{flags:x} ({'|'.join(labels)})"


def resolve_path(f, ps, cs, tr, obj_map, path):
    """Resolve a '/dir/sub/file' path to (parent_oid, key, value) of its type-0x30 row.
    Case-insensitive (ReFS default). Resident files have no OID — they are found inline in the
    parent's row. Returns (None, None, None) if not found."""
    parts = [p for p in path.replace("\\", "/").split("/") if p and p != "."]
    if not parts:
        return (None, None, None)
    oid = 0x600
    for i, part in enumerate(parts):
        if oid not in obj_map:
            return (None, None, None)
        found = None
        try:
            rows = walk_bplus(f, ps, cs, tr, obj_map[oid])
        except Exception:
            return (None, None, None)
        for kd, vd in rows:
            if len(kd) < 4 or le16(kd, 0) != 0x30:
                continue
            try:
                nm = kd[4:].decode("utf-16-le").rstrip("\x00")
            except Exception:
                continue
            if nm.lower() == part.lower():
                found = (kd, vd)
                break
        if found is None:
            return (None, None, None)
        kd, vd = found
        if i == len(parts) - 1:
            return (oid, kd, vd)
        # descend into a child directory: val+0x08 is the child's own OID only when the directory bit is
        # set. A non-resident FILE has the home-dir backref there (a different object), not an OID, so an
        # intermediate path component that is a file (not a directory) is not descendable -> no such path.
        if len(vd) <= NON_RESIDENT_MAX_VALUE and len(vd) >= 0x44 and (le32(vd, 0x40) & 0x10000000):
            oid = le64(vd, 0x08)
        else:
            return (None, None, None)
    return (None, None, None)


def count_snapshots_from_btree(f, ps, cs, tr, vlcns):
    """Count true snapshot entries in a file's own B+-tree (non-resident files)."""
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception:
        return 0
    count = 0
    for kd, vd in rows:
        if _is_b0_snapshot_key(kd) and _is_snapshot_value(vd):
            count += 1
    return count


# ── Snapshot content recovery (CoW prior-content) ───────────────────────
# Chain (E2: SetResidentStreamSummary/RefsCreateStreamSnapshot; RD-verified):
#   snapshot 0xB0 sub-record  val[0x44] = data_sub_id, val[0x20] = stream size
#     -> DATA 0x80 sub-record whose key+0x10 == data_sub_id  (descriptor 0x10028)
#         val[0x00] = inner-header offset (0x88); val[0x48] = on-disk alloc (0 = inline)
#         extent_count = val[ihdr+0x14]; 24-byte extents at val[ihdr+0x28]:
#           +0x00 VLCN(u64)  +0x0C file_vcn(u32)  +0x14 run_length(u32)
#     -> translate VLCN->PLCN (Container Table) -> read run_length clusters -> trim.
# The CURRENT version is data_sub_id 0x1000. Same 24-byte extent format as type-0x40.
SNAP_DATA_DESC = 0x10028


def parse_snapshot_data_entry(v):
    """Parse an embedded type-0x80 DATA entry -> (stream_size, disk_alloc, extents)
    where extents = [(file_vcn, vlcn, run_length), ...] sorted by file_vcn."""
    if len(v) < 0x50:
        return (0, 0, [])
    ihdr = le32(v, 0)
    stream_size = le64(v, 0x38)
    disk_alloc = le64(v, 0x48)
    exts = []
    if ihdr + 0x18 <= len(v):
        ecount = le32(v, ihdr + 0x14)
        eo = ihdr + 0x28
        for i in range(ecount):
            base = eo + i * 24
            if base + 24 > len(v):
                break
            exts.append((le32(v, base + 0x0C), le64(v, base), le32(v, base + 0x14)))
        exts.sort(key=lambda e: e[0])
    return (stream_size, disk_alloc, exts)


def recover_cow_current_content(f, ps_off, cs, tr, vd):
    """Q7/CoW: recover the LIVE content of a resident file whose current stream (sub_id 0x1000) is a 0x10028
    holder with disk_alloc==0 and no own extents — i.e. UNMODIFIED since the last snapshot, so its bytes are
    shared with the newest snapshot. Returns bytes (trimmed to size) or None. STRICTLY the safe case only:
    if the current stream has its OWN allocation (disk_alloc>0 / own extents) this returns None (that is the
    F5 large-non-resident / possibly-sparse case, deferred to `dataruns`). Verified on win11refs2tsnapshots
    (test.txt current 5B == snapshot 0x1004; lasttest.txt 201B == 0x1002)."""
    holders = {}   # sub_id -> (stream_size, disk_alloc, extents)
    for k, v in parse_resident_btree_rows(vd):
        if (len(k) >= 0x18 and k[12] == 0x80 and k[13] == 0x00
                and len(v) >= 0x50 and le32(v, 4) == SNAP_DATA_DESC):
            holders[le64(k, 0x10)] = parse_snapshot_data_entry(v)
    cur = holders.get(0x1000)
    if cur is None:
        return None
    cur_size, cur_alloc, cur_exts = cur
    if cur_alloc != 0 or cur_exts:
        return None   # own allocation => not the safe CoW case (F5 / sparse) — leave to dataruns
    if cur_size == 0:
        return b""
    # the current bytes are the newest snapshot with real extents AND the SAME size (don't guess otherwise).
    candidates = [sid for sid, d in holders.items()
                  if sid > 0x1000 and d[2] and d[0] == cur_size]
    if not candidates:
        return None
    _ssz, _salloc, exts = holders[max(candidates)]
    alloc = max((fv + run) for fv, _vl, run in exts) * cs
    if alloc > 64 * 1024 * 1024:   # CoW resident streams are small; guard anyway
        return None
    buf = bytearray(alloc)
    for fvcn, vlcn, run in sorted(exts, key=lambda e: e[0]):
        for j in range(run):
            try:
                plcn = tr.tr(vlcn + j)
            except Exception:
                plcn = vlcn + j
            f.seek(ps_off + plcn * cs)
            chunk = f.read(cs)
            off = (fvcn + j) * cs
            buf[off:off + cs] = chunk
    return bytes(buf[:cur_size])


def recover_snapshot_streams(f, ps_off, cs, tr, vd):
    """Recover snapshot + current stream content from a resident type-0x30 row.
    Returns a list of {name, sub_id, stream_size, ts, content|None, inline, n_extents}.
    content is None when inline (disk_alloc==0; bytes live in the main 0x30 body) or
    when the referenced DATA entry is absent. The current file version is sub_id 0x1000."""
    snaps = []   # (name, sub_id, stream_size, ts)
    data = {}    # sub_id -> (stream_size, disk_alloc, extents)
    for k, v in parse_resident_btree_rows(vd):
        if len(k) < 0x10:
            continue
        typ = le16(k, 0x0C)
        if typ == 0xB0 and len(v) >= 0x50:
            sub_id = le32(v, 0x44)
            is_snap = (le16(v, 0x10) == 2) or (0x1000 <= sub_id <= 0xFFFF)
            if not is_snap:
                continue
            name = ""
            if len(k) > 0x10:
                try:
                    name = k[0x10:].decode("utf-16-le").rstrip("\x00")
                except Exception:
                    name = k[0x10:].hex()
            snaps.append((name, sub_id, le64(v, 0x20), le64(v, 0x4C)))
        elif typ == 0x80 and len(v) >= 0x50 and le32(v, 4) == SNAP_DATA_DESC:
            data[le64(k, 0x10)] = parse_snapshot_data_entry(v)

    def _read_extents(stream_size, exts):
        buf = b""
        for _fvcn, vlcn, run in exts:
            for j in range(run):
                try:
                    plcn = tr.tr(vlcn + j)
                except Exception:
                    plcn = vlcn + j
                f.seek(ps_off + plcn * cs)
                buf += f.read(cs)
        return buf[:stream_size]

    out = []
    for name, sub_id, ssize, ts in sorted(snaps, key=lambda s: s[1]):
        d = data.get(sub_id)
        if d is None:
            out.append({"name": name, "sub_id": sub_id, "stream_size": ssize,
                        "ts": ts, "content": None, "inline": False, "n_extents": 0})
            continue
        _ds, disk_alloc, exts = d
        if disk_alloc == 0:
            out.append({"name": name, "sub_id": sub_id, "stream_size": ssize,
                        "ts": ts, "content": None, "inline": True, "n_extents": 0})
        else:
            out.append({"name": name, "sub_id": sub_id, "stream_size": ssize, "ts": ts,
                        "content": _read_extents(ssize, exts), "inline": False,
                        "n_extents": len(exts)})
    return out

# ═══════════════════════════════════════════════════════════════════════
# MLog (durable log) parsing — E2 opcode tables from PerformRedo
# ═══════════════════════════════════════════════════════════════════════

# v3.14 redo dispatch — corrected verbatim from CmsLogRedoQueue::PerformRedo (win11 26100,
# refs_win11.decomp.c; per-function copy analysis/static/decompiled_functions/redo_dispatch/
# PerformRedo_win11.c). Opcodes 0x00–0x2B are a CONTIGUOUS dispatched range; the ONLY in-range
# value that returns NTSTATUS 0xC0000427 (generic unhandled-opcode) is 0x17. The earlier table mislabelled six handled
# ops (0x04,0x10,0x14,0x1B,0x20,0x26) as "gaps" and was off-by-one across 0x1A/0x1B and
# 0x1E/0x1F/0x20 and 0x28/0x29; all corrected here (finding #328, all E2).
REDO_OPS_V314 = {
    0x00: "OpenTableFromTablePath",
    0x01: "RedoInsertRow",
    0x02: "RedoDeleteRow",
    0x03: "RedoUpdateRow",
    0x04: "RedoUpdateDataWithRoot",                  # PerformRedo_win11.c:144 (was tagged gap)
    0x05: "RedoReparentTable",
    0x06: "RedoAllocate",
    0x07: "RedoFree",
    0x08: "RedoSetRangeState",                       # shared 0x08/0x09
    0x09: "RedoSetRangeState",
    0x0A: "RedoDuplicateExtents",
    0x0B: "RedoModifyStreamExtent",
    0x0C: "CmsStream::StripAllChecksums",
    0x0D: "CmsBPlusTable::SetIntegrityInformation",
    0x0E: "RedoSetParentId",
    0x0F: "RedoDeleteTable",
    0x10: "CmsBPlusTable::SetObjectRecordPayload",   # :207 (was tagged gap)
    0x11: "RedoAddSchema",
    0x12: "RedoMoveContainer",                       # shared 0x12/0x14/0x15 (LAB_14012eebf)
    0x13: "RedoAddContainer",
    0x14: "RedoMoveContainer",                       # :224 (was gap:unknown_0x14)
    0x15: "RedoMoveContainer",                       # :222 (was "(dispatch flag)")
    0x16: "RedoSetRangeState",                       # :114 range-parse variant (E3, name unconfirmed)
    0x17: "ERROR:0xC0000427",             # :239 explicit error — the only in-range gap
    0x18: "RedoContainerCompaction",
    0x19: "RedoDeleteCompressionUnitOffsets",
    0x1A: "RedoAddCompressionUnitOffsets",           # :256 InsertRow(0x32) (was RedoGhostExtents)
    0x1B: "RedoGhostExtents",                        # :266 (was gap:unknown_0x1b)
    0x1C: "RedoCompactionUnreserve",
    0x1D: "CmsBPlusTable::UnlinkParentObjectId",
    0x1E: "CmsTableSetBase::PrepareEntryForMerge",   # :293 (was RedoUpdateStreamSummary)
    0x1F: "RedoUpdateStreamSummary",                 # :297 (was UpdateStreamUserPayload)
    0x20: "CmsStream::UpdateStreamUserPayload",      # :310 (was gap:unknown_0x20) — handled
    0x21: "RedoStreamPersistFastRunInsertion",
    0x22: "RedoTableSetSummaryUpdate",
    0x23: "RedoTableSetShadowTreeUpdate",
    0x24: "RedoTableSetCommitMerge",
    0x25: "RedoTableSetCallback(+0x08)",             # :340 indirect CmsTableSetBase vtbl call
    0x26: "RedoTableSetStrongRefMerge",              # :348 (was gap:unknown_0x26)
    0x27: "RedoSetDefaultCompressionParameters",
    0x28: "CmsBlockRefcount::BreakWeakReferences",   # :358 (was RedoDuplicateCluster)
    0x29: "RedoDuplicateCluster",                    # :365
    0x2A: "RedoChangeRangeEncryptedState",
    0x2B: "RedoTableSetCallback(+0x18)",             # :381 indirect CmsTableSetBase vtbl call
}

REDO_OPS_V34 = {
    0x00: "OpenTable",
    0x01: "RedoInsertRow",
    0x02: "RedoDeleteRow",
    0x03: "RedoUpdateRow",
    0x04: "RedoUpdateDataWithRoot",
    0x05: "RedoReparentTable",
    0x06: "RedoAllocate",
    0x07: "RedoFree",
    0x08: "RedoSetRangeState",                       # PerformRedo_win10.c:114 (was tagged gap)
    0x09: "RedoSetRangeState",                       # shared 0x08/0x09 (uVar2 < 10 branch)
    0x0A: "RedoDuplicateExtents",
    0x0B: "RedoModifyStreamExtent",
    0x0C: "RedoStripMetadataStreamExtent",
    0x0D: "RedoSetIntegrity",
    0x0E: "RedoSetParentId",
    0x0F: "RedoDeleteTable",
    0x10: "CmsBPlusTable::SetObjectRecordPayload",
    0x11: "RedoAddSchema",
    0x12: "RedoMoveContainer",
    0x13: "RedoAddContainer",
    0x14: "RedoMoveContainer",
    0x15: "RedoMoveContainer",
    0x16: "RedoReadCacheInvalidation",
    0x17: "RedoGenerateChecksum",
    0x18: "RedoContainerCompression",
    0x19: "RedoDeleteCompressionUnitOffsets",
    0x1A: "RedoAddCompressionUnitOffsets",
    0x1B: "RedoGhostExtents",
    0x1C: "RedoCompactionUnreserve",
}

OPCODE_CATEGORIES = {
    "OpenTableFromTablePath": "table", "OpenTable": "table",
    "RedoInsertRow": "btree", "RedoDeleteRow": "btree",
    "RedoUpdateRow": "btree", "RedoUpdateDataWithRoot": "btree",
    "RedoReparentTable": "table", "RedoDeleteTable": "table",
    "RedoAllocate": "alloc", "RedoFree": "alloc",
    "RedoSetRangeState": "alloc",
    "RedoDuplicateExtents": "dedup", "RedoDuplicateCluster": "dedup",
    "RedoGhostExtents": "dedup",
    "RedoModifyStreamExtent": "stream",
    "RedoUpdateStreamSummary": "stream",
    "CmsStream::UpdateStreamUserPayload": "stream",
    "RedoStreamPersistFastRunInsertion": "stream",
    "CmsStream::StripAllChecksums": "integrity",
    "CmsBPlusTable::SetIntegrityInformation": "integrity",
    "RedoSetIntegrity": "integrity",
    "RedoStripMetadataStreamExtent": "integrity",
    "RedoSetParentId": "namespace",
    "CmsBPlusTable::UnlinkParentObjectId": "namespace",
    "RedoAddSchema": "schema",
    "RedoMoveContainer": "container", "RedoAddContainer": "container",
    "RedoContainerCompaction": "container", "RedoContainerCompression": "container",
    "RedoCompactionUnreserve": "container",
    "RedoDeleteCompressionUnitOffsets": "compress",
    "RedoAddCompressionUnitOffsets": "compress",
    "RedoSetDefaultCompressionParameters": "compress",
    "RedoTableSetSummaryUpdate": "tableset",
    "RedoTableSetShadowTreeUpdate": "tableset",
    "RedoTableSetCommitMerge": "tableset",
    "RedoTableSetStrongRefMerge": "tableset",
    "CmsTableSetBase::PrepareEntryForMerge": "tableset",
    "RedoTableSetCallback(+0x08)": "tableset",
    "RedoTableSetCallback(+0x18)": "tableset",
    "RedoReadCacheInvalidation": "cache",
    "RedoGenerateChecksum": "checksum",
    "RedoChangeRangeEncryptedState": "encrypt",
    "CmsBPlusTable::SetObjectRecordPayload": "btree",
    "CmsBlockRefcount::BreakWeakReferences": "dedup",
    "ERROR:0xC0000427": "error",
}

MLOG_SCHEMA_NAMES = {
    0xe010: "Allocator", 0xe030: "ObjectTable", 0xe040: "ParentChild",
    0xe050: "ObjectData", 0xe060: "SchemaTable", 0xe080: "IntegrityState",
    0xe090: "Upcase/Logfile", 0xe0b0: "BlockRefcount",
    0xe0c0: "ContainerTable", 0xe0d0: "TrashTable", 0xe100: "ContainerIndex",
    0xe110: "ReadCache", 0xe120: "DirtyRange", 0xe130: "HeatEngine",
    0x0110: "DirEntryList", 0x0120: "FileStream", 0x0130: "$FILE_NAME",
    0x0140: "$FILE_NAME_long", 0x0150: "$VOLUME_INFO", 0x0160: "ReparseIndex",
    0x0170: "$REPARSE", 0x0180: "$DATA", 0x0190: "$SI",
    0x01A0: "$INDEX_ROOT", 0x01B0: "$SNAPSHOT", 0x01C0: "$REPARSE_v2",
    0x01D0: "$EA_INFO", 0x01E0: "$EA", 0x01F0: "$LOGGED_UTILITY",
    0x0200: "$LOGGED_UTILITY_V2",
}

KNOWN_SYSTEM_OIDS = {
    0x07: "Upcase(pri)", 0x08: "Upcase(dup)", 0x09: "Logfile(pri)",
    0x0A: "Logfile(dup)", 0x0D: "TrashTable", 0x30: "SessionActivity",
    0x500: "VolumeInfo(pri)", 0x501: "VolumeInfo(dup)",
    0x520: "FS Metadata", 0x530: "SecurityDesc",
    0x540: "ReparseIdx(pri)", 0x541: "ReparseIdx(dup)",
    0x600: "/",
}

# R3 (2026-07-03): the old hand-maintained MLOG_OP_SHORT opcode→mnemonic dict was removed — it was dead code
# (no readers) carrying the pre-C4 version-independent short names. op_short is now DERIVED from the
# version-selected long table via _redo_short(), so it can never drift from op_name.

PAGE_TYPE_ZERO = "zero"
PAGE_TYPE_MSBP = "MSB+"
PAGE_TYPE_MLOG = "MLog"
PAGE_TYPE_DATA = "data"

MIN_REDO_SIZE = 0x38

# ── ReFS metadata checksum (page references, cktype 2 = CRC64) ──────────
# REFLECTED CRC64, polynomial 0x9A6C9329AC4BC9B5 (driver global `ClMulCsCrc64`),
# init = xorout = ~0, computed over the FULL metadata page (all page-ref LCN
# slots concatenated, 16 KiB for 4K clusters). E2: ?GenerateChecksum…Crc64_ClMul@
# + RD: matches stored page-reference checksums, 0 mismatches across CRC64/SHA-256/64K.
_REFS_CRC64_POLY = 0x9A6C9329AC4BC9B5
_REFS_CRC64_TBL = []
for _ci in range(256):
    _cc = _ci
    for _ in range(8):
        _cc = (_cc >> 1) ^ _REFS_CRC64_POLY if (_cc & 1) else _cc >> 1
    _REFS_CRC64_TBL.append(_cc & 0xFFFFFFFFFFFFFFFF)
# Collision sentinel the driver remaps (GenerateChecksum: 0x…fffe → 0x…ffff).
REFS_CRC64_SENTINEL = 0xABBAFFFFABBAFFFF


def refs_crc64(data):
    """ReFS metadata CRC64 (cktype 2) over a full metadata page."""
    crc = 0xFFFFFFFFFFFFFFFF
    for b in data:
        crc = _REFS_CRC64_TBL[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return (crc ^ 0xFFFFFFFFFFFFFFFF) & 0xFFFFFFFFFFFFFFFF
# The MLog log block (one LogCore record) is ALWAYS 4 KiB, independent of the
# volume cluster size. On a 64 KiB-cluster volume each data-area cluster holds
# 16 of these 4 KiB log blocks (verified RD; see docs/structures/mlog.md).
MLOG_BLOCK = 0x1000

_FT_EPOCH = datetime.datetime(1601, 1, 1)
_FT_MIN = 130000000000000000
_FT_MAX = 140000000000000000


def _filetime_dt(val):
    if _FT_MIN < val < _FT_MAX:
        return _FT_EPOCH + datetime.timedelta(microseconds=val // 10)
    return None


def _filetime_str(val):
    dt = _filetime_dt(val)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z" if dt else ""


def format_uuid(b):
    if len(b) < 16:
        return b.hex()
    import uuid as _uuid
    return str(_uuid.UUID(bytes_le=bytes(b[:16])))


def _as_vlcn_list(val):
    return val if isinstance(val, (list, tuple)) else [val]


def get_mlog_info(f, ps_off, cs, tr, obj_map):
    """Extract MLog location from OID 0x9 (Logfile Information Table)."""
    for oid in [0x9, 0xA]:
        if oid not in obj_map:
            continue
        rows = list(walk_bplus(f, ps_off, cs, tr, _as_vlcn_list(obj_map[oid])))
        info = {"oid": oid, "rows": len(rows)}
        for kd, vd in rows:
            key = le32(kd, 0) if len(kd) >= 4 else -1
            if key == 0:
                try:
                    info["table_name"] = kd[4:].decode("utf-16-le").rstrip("\x00") \
                        if len(kd) > 4 else vd.decode("ascii", errors="replace").rstrip("\x00")
                except Exception:
                    info["table_name"] = vd[:25].hex()
            elif key == 1 and len(vd) >= 40:
                info["data_start_lcn"] = le64(vd, 0)
                info["data_end_lcn"] = le64(vd, 8)
                info["data_size_clusters"] = le64(vd, 16)
                info["ctrl_plcn_0"] = le64(vd, 24)
                info["ctrl_plcn_1"] = le64(vd, 32)
        if "ctrl_plcn_0" in info:
            return info
    return None


def parse_mlog_control_page(page):
    """Parse a raw MLog control page (4096+ bytes with 'MLog' signature)."""
    if len(page) < 256 or page[:4] != b"MLog":
        return None
    info = {
        "signature": "MLog",
        "format_magic": le32(page, 0x04),  # per-volume constant, NOT a CRC32 (errata E42)
        "version": le32(page, 0x08),
        "sector_size": le32(page, 0x0C),
        "uuid": format_uuid(page[0x10:0x20]),
        "sequence_raw": le64(page, 0x20),
    }
    eh_off = le32(page, 0x54)
    if eh_off == 0 or eh_off + 0x30 > len(page):
        return info
    info["entry_header_offset"] = eh_off
    payload_size = le32(page, eh_off + 0x20)
    payload_off = le32(page, eh_off + 0x28)
    info["payload_size"] = payload_size
    info["payload_offset"] = payload_off
    if payload_size != 0xe48:
        return info
    data_off = eh_off + payload_off
    if data_off + 0xe48 > len(page):
        return info
    d = page[data_off:]
    info["sequence"] = le64(d, 0x00)
    info["data_start_lcn"] = le64(d, 0x08)
    info["data_end_lcn"] = le64(d, 0x10)
    info["lsn_oldest"] = le64(d, 0x18)
    info["generation"] = le32(d, 0x20)
    info["write_counter"] = le32(d, 0x38)
    info["flags"] = le32(d, 0x3C)
    info["total_entries"] = le64(d, 0x48)
    info["ctrl_uuid"] = format_uuid(d[0x50:0x60])
    return info


def read_mlog_control(f, ps_off, cs, mlog_info):
    """Read both MLog control pages and return the more recent one."""
    ctrls = []
    for key in ["ctrl_plcn_0", "ctrl_plcn_1"]:
        plcn = mlog_info.get(key, 0)
        if plcn == 0:
            continue
        f.seek(ps_off + plcn * cs)
        page = f.read(max(cs, 4096))
        parsed = parse_mlog_control_page(page)
        if parsed:
            parsed["plcn"] = plcn
            ctrls.append(parsed)
    if not ctrls:
        return None
    if len(ctrls) == 2:
        s0 = ctrls[0].get("sequence", 0)
        s1 = ctrls[1].get("sequence", 0)
        return ctrls[1] if s1 > s0 else ctrls[0]
    return ctrls[0]


def classify_mlog_page(page):
    if all(b == 0 for b in page[:64]):
        return PAGE_TYPE_ZERO
    sig = page[:4]
    if sig == b"MSB+":
        return PAGE_TYPE_MSBP
    if sig == b"MLog":
        return PAGE_TYPE_MLOG
    return PAGE_TYPE_DATA


def scan_mlog_data_area(f, ps_off, cs, tr, mlog_info, ctrl):
    """Scan the MLog data area and classify each 4 KiB log block.

    The data area is addressed in volume clusters (from OID 0x9), but each MLog
    record is a 4 KiB log block. On a 64 KiB-cluster volume every cluster packs
    16 log blocks, so we iterate 4 KiB blocks within each cluster — otherwise a
    64K-cluster log would expose only 1/16 of its records. On 4K-cluster volumes
    blocks_per_cluster == 1 and the behaviour is identical to a cluster scan."""
    start_plcn = mlog_info.get("data_start_lcn", 0)
    end_plcn = mlog_info.get("data_end_lcn", 0)
    if start_plcn == 0 or end_plcn == 0 or end_plcn <= start_plcn:
        if ctrl:
            start_plcn = ctrl.get("data_start_lcn", 0)
            end_plcn = ctrl.get("data_end_lcn", 0)
    if start_plcn == 0 or end_plcn == 0:
        return
    blocks_per_cluster = max(1, cs // MLOG_BLOCK)
    # Generator: yield one page dict per 4 KiB log block instead of building a list. A 1 GiB log
    # (262k blocks × 4 KiB) would otherwise hold ~1 GB of block bytes resident at once. Single-pass
    # consumers (extract_redo_records / extract_mlog_transactions, timeline) stream this directly;
    # multi-pass callers (mlog --json / default / --raw-scan) wrap it with list().
    for plcn in range(start_plcn, end_plcn):
        f.seek(ps_off + plcn * cs)
        cluster = f.read(cs)
        for bi in range(blocks_per_cluster):
            block = cluster[bi * MLOG_BLOCK:(bi + 1) * MLOG_BLOCK]
            if len(block) < 4:
                break
            ptype = classify_mlog_page(block)
            yield {
                "vlcn": plcn, "plcn": plcn, "block": bi,
                "block_lcn": plcn * blocks_per_cluster + bi,
                "type": ptype,
                "page": block if ptype != PAGE_TYPE_ZERO else None,
            }


def try_parse_redo_block(data, redo_ops):
    """Parse data as _SmsRedoHeader with inner _SmsRedoRecord entries."""
    if len(data) < 8:
        return []
    total_size = le32(data, 0)
    first_off = le32(data, 4)
    if total_size < MIN_REDO_SIZE or total_size > len(data):
        return []
    if first_off < 8 or first_off >= total_size:
        return []
    records = []
    remaining = total_size - first_off
    pos = first_off
    while remaining >= MIN_REDO_SIZE and pos + MIN_REDO_SIZE <= len(data):
        rec_size = le32(data, pos)
        if rec_size < MIN_REDO_SIZE or rec_size > remaining or rec_size == 0:
            break
        opcode = le32(data, pos + 4)
        table_path_len = le32(data, pos + 8) if pos + 12 <= len(data) else 0
        obj_id = le64(data, pos + 0x20) if pos + 0x28 <= len(data) else 0
        flags = le32(data, pos + 0x2C) if pos + 0x30 <= len(data) else 0
        op_name = redo_ops.get(opcode, "UNKNOWN_0x%02x" % opcode)
        records.append({
            "offset": pos, "size": rec_size,
            "opcode": opcode, "op_name": op_name,
            "table_path_len": table_path_len,
            "object_id": obj_id, "flags": flags,
            "txn_start": bool(flags & 1),
            "txn_commit": bool(flags & 2),
        })
        remaining -= rec_size
        pos += rec_size
    return records


def extract_payload_from_mlog_page(page):
    """Extract redo block payload from an MLog-signature data page."""
    if len(page) < 0x60:
        return None
    eh_off = le32(page, 0x54)
    if eh_off == 0 or eh_off + 0x30 > len(page):
        return None
    payload_size = le32(page, eh_off + 0x20)
    payload_off = le32(page, eh_off + 0x28)
    if payload_size == 0 or payload_off == 0:
        return None
    data_start = eh_off + payload_off
    if data_start + payload_size > len(page):
        return None
    return page[data_start:data_start + payload_size]


def parse_mlog_record_header(page):
    """Decode the LogCore data-record header (Layer 1, 0x78 bytes) and entry
    header (Layer 2) of an MLog data page. Returns None for control/other pages.
    Offsets verified static (v3.4/v3.14/Insider) + RD on 10 images; see
    docs/structures/mlog.md. payload_offset is 0x38 on v3.4-v3.14, 0x40 on Insider."""
    if len(page) < 0xB0 or page[:4] != b"MLog":
        return None
    eh_off = le32(page, 0x54)
    if eh_off == 0 or eh_off + 0x34 > len(page):
        return None
    rec_type = le32(page, eh_off + 0x30)        # u32: 2 = data, 1 = control
    if rec_type != 2:
        return None
    return {
        "signature": page[:4].decode("ascii", "replace"),
        "format_magic": le32(page, 0x04),       # per-volume constant, NOT a CRC (E42)
        "version": le32(page, 0x08),
        "log_block_size": le32(page, 0x0C),     # 0x1000 (4K) always
        "uuid": format_uuid(page[0x10:0x20]),
        "counter": le32(page, 0x20),
        "lsn": le64(page, 0x28),                # (generation<<32) | block offset
        "prev_lsn": le64(page, 0x30),
        "total_blocks": le32(page, 0x38),       # 4K log-block units
        "header_blocks": le32(page, 0x3C),
        "entry_header_offset": eh_off,
        "checksum": le64(page, eh_off + 0x08),  # XOR-fold at page+0x80
        "payload_len": le32(page, eh_off + 0x20),
        "payload_offset": le32(page, eh_off + 0x28),
        "record_type": rec_type,
        "redo_block_offset": eh_off + le32(page, eh_off + 0x28),
    }


def extract_redo_records(pages, redo_ops):
    """Extract redo records from MLog data area pages."""
    all_records = []
    for pinfo in pages:
        page = pinfo.get("page")
        if page is None:
            continue
        if pinfo["type"] != PAGE_TYPE_MLOG:
            continue
        payload = extract_payload_from_mlog_page(page)
        if payload is None:
            continue
        recs = try_parse_redo_block(payload, redo_ops)
        if recs:
            for r in recs:
                r["vlcn"] = pinfo["vlcn"]
                r["plcn"] = pinfo["plcn"]
                r["block"] = pinfo.get("block", 0)
                r["block_lcn"] = pinfo.get("block_lcn", pinfo["plcn"])
                r["page_type"] = pinfo["type"]
            all_records.extend(recs)
    return all_records


def _mlog_decode_utf16(raw):
    try:
        txt = raw.decode("utf-16-le").split("\x00")[0]
        if len(txt) >= 1 and all(c.isprintable() or c in "\t" for c in txt):
            return txt[:255]
    except (UnicodeDecodeError, ValueError):
        pass
    return ""


def _mlog_scan_utf16(vdata, start_off):
    for s in range(start_off, min(len(vdata) - 3, 200), 2):
        b0, b1 = vdata[s], vdata[s + 1]
        if 0x20 <= b0 < 0x7F and b1 == 0:
            txt = _mlog_decode_utf16(vdata[s:s + 520])
            if len(txt) >= 2 and txt != "$I30":
                return txt
    return ""


def _mlog_extract_timestamp(rec, rs, opcode, tpl, vc, vbase):
    if opcode == 0x01 and vc >= 2:
        v1p = vbase + 8
        if v1p + 8 <= rs:
            v1_off = le32(rec, v1p)
            v1_len = le32(rec, v1p + 4)
            if v1_off + v1_len <= rs and v1_len >= 0x48:
                for off in (0x30, 0x28, 0x38, 0x40):
                    val = le64(rec, v1_off + off)
                    if _FT_MIN < val < _FT_MAX:
                        return val
    if opcode == 0x04 and vc >= 1:
        if vbase + 8 <= rs:
            v0_off = le32(rec, vbase)
            v0_len = le32(rec, vbase + 4)
            if v0_off + v0_len <= rs and v0_len >= 8:
                for off in range(0, min(v0_len - 7, 0x20), 8):
                    val = le64(rec, v0_off + off)
                    if _FT_MIN < val < _FT_MAX:
                        return val
    if opcode == 0x03 and vc >= 2:
        v1p = vbase + 8
        if v1p + 8 <= rs:
            v1_off = le32(rec, v1p)
            v1_len = le32(rec, v1p + 4)
            if v1_off + v1_len <= rs and v1_len >= 0x20:
                for off in (0x90, 0xa0, 0x30, 0x28, 0x08, 0x00):
                    if off + 8 <= v1_len:
                        val = le64(rec, v1_off + off)
                        if _FT_MIN < val < _FT_MAX:
                            return val
    return 0


def _redo_short(name):
    """C4: compact mnemonic DERIVED from the (version-selected) long redo-op name, so op_short can never
    drift from op_name / the long table. Opcode->name is decompiler-verified for v3.4 (REDO_OPS_V34) and
    v3.14 (REDO_OPS_V314); v3.7-v3.10 have no decompiled driver and reuse the v3.14 table (best-effort —
    surfaced in the mlog caveat). This replaces the old hand-maintained, version-independent MLOG_OP_SHORT."""
    if not name:
        return ""
    if name.startswith("ERROR"):        # R1: the one ERROR:0x… entry — don't mangle it to "E_R"
        return "ERROR"
    n = name.split("::")[-1]            # R1: drop a Namespace:: qualifier (CmsStream::StripAllChecksums -> Strip…)
    if n.startswith("Redo"):
        n = n[4:]
    parts, cur = [], ""                # split CamelCase manually (forefst.py does not import `re`)
    for ch in n:
        if ch.isupper() and cur:
            parts.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        parts.append(cur)
    if not parts:
        return n.upper()[:12]
    # R1: keep WHOLE words (no mid-word truncation), joined with _, within a ~16-char budget so the mnemonic
    # stays readable and compact (RedoInsertRow -> INSERT_ROW, UpdateDataWithRoot -> UPDATE_DATA).
    out = ""
    for w in parts:
        wu = w.upper()
        if out and len(out) + 1 + len(wu) > 16:
            break
        out = wu if not out else out + "_" + wu
    return out or parts[0].upper()[:12]


def parse_mlog_deep_record(rec_bytes, redo_ops):
    """Deep-parse a redo record with key path and value extraction."""
    rs = le32(rec_bytes, 0)
    opcode = le32(rec_bytes, 4)
    tpl = le32(rec_bytes, 8)
    val_count = le32(rec_bytes, 0x10)
    handle = le64(rec_bytes, 0x20)
    flags = le32(rec_bytes, 0x2C)
    r = {
        "size": rs, "opcode": opcode,
        "op_name": redo_ops.get(opcode, "UNK_0x%02x" % opcode),
        # C4: derive from the version-selected long table (not the stale version-independent MLOG_OP_SHORT).
        "op_short": _redo_short(redo_ops.get(opcode)) if opcode in redo_ops else "0x%02x" % opcode,
        "tpl": tpl, "val_count": val_count,
        "handle": handle, "flags": flags,
        "txn_start": bool(flags & 1), "txn_commit": bool(flags & 2),
        "target_oid": 0, "table_schema": 0, "attr_schema": 0,
        "attr_schema2": 0, "filename": "", "timestamp": 0,
    }
    if tpl >= 1:
        if len(rec_bytes) < 0x3C:
            return r
        kc0_off = le32(rec_bytes, 0x38)
        kc0_len = le32(rec_bytes, 0x3C)
        if kc0_off + 28 <= rs and kc0_len >= 28:
            r["table_schema"] = le32(rec_bytes, kc0_off)
            r["attr_schema"] = le32(rec_bytes, kc0_off + 4)
            r["target_oid"] = le64(rec_bytes, kc0_off + 20)
    if tpl >= 2:
        kc1_off = le32(rec_bytes, 0x40)
        kc1_len = le32(rec_bytes, 0x44)
        if kc1_off + 4 <= rs and kc1_len >= 4:
            r["attr_schema2"] = le32(rec_bytes, kc1_off)
    vbase = 0x38 + tpl * 8
    if opcode in (0x01, 0x02):
        if vbase + 8 <= rs:
            v0_off = le32(rec_bytes, vbase)
            v0_len = le32(rec_bytes, vbase + 4)
            if v0_off + v0_len <= rs and 4 < v0_len < 4096:
                vdata = rec_bytes[v0_off:v0_off + v0_len]
                if tpl == 1 and r["attr_schema"] == 0x0130 and v0_len > 6:
                    r["filename"] = _mlog_decode_utf16(vdata[4:])
                elif tpl == 0 and v0_len > 34:
                    r["filename"] = _mlog_scan_utf16(vdata, 16)
    r["timestamp"] = _mlog_extract_timestamp(rec_bytes, rs, opcode, tpl,
                                              val_count, vbase)
    return r


def extract_mlog_transactions(pages, redo_ops):
    """Extract per-page transactions with deep-parsed records."""
    txns = []
    for pinfo in pages:
        page = pinfo.get("page")
        if page is None or pinfo["type"] != PAGE_TYPE_MLOG:
            continue
        payload = extract_payload_from_mlog_page(page)
        if payload is None or len(payload) < 8:
            continue
        _eh = le32(page, 0x54); _dstart = _eh + le32(page, _eh + 0x28)  # payload start within the MLog block
        total_sz = le32(payload, 0)
        first_rec = le32(payload, 4)
        if total_sz < MIN_REDO_SIZE or first_rec < 8 or first_rec >= total_sz:
            continue
        recs = []
        remaining = total_sz - first_rec
        pos = first_rec
        while remaining >= MIN_REDO_SIZE and pos + MIN_REDO_SIZE <= len(payload):
            rec_size = le32(payload, pos)
            if rec_size < MIN_REDO_SIZE or rec_size > remaining or rec_size == 0:
                break
            rec_bytes = payload[pos:pos + rec_size]
            r = parse_mlog_deep_record(rec_bytes, redo_ops)
            r["plcn"] = pinfo["plcn"]
            r["rec_off"] = _dstart + pos  # B3: byte offset within the MLog block; disk = ps + plcn*cs + block*MLOG_BLOCK + rec_off
            r["block"] = pinfo.get("block", 0)
            recs.append(r)
            remaining -= rec_size
            pos += rec_size
        if recs:
            txns.append({"plcn": pinfo["plcn"], "block": pinfo.get("block", 0),
                         "records": recs})
    return txns


#  MLog concrete-action groups. FILE_OPS are user-visible file operations; LOW_LEVEL are B+-tree/metadata
#  redo records that accompany them (kept as facts, not folded away). See docs/structures/mlog.md.
MLOG_FILE_OPS = ("CREATE", "WRITE", "RENAME", "MOVE", "DELETE")
MLOG_LOW_LEVEL = ("MODIFY", "STREAM_UPD", "REPARENT", "ENTRY_REMOVE", "ALLOCATE", "CONTAINER",
                  "DEDUP", "EXTENT_MOD", "UPDATE", "INSERT", "OP")

def _mlog_name_entry_parents(recs, opcode):
    """The set of TARGET OIDs (parent-directory tables) of the name-entry rows of `opcode` in a
    transaction — non-zero only. For a rename/move this is the OLD parent (opcode 0x02 DeleteRow) vs the
    NEW parent (opcode 0x01 InsertRow); comparing the two tells RENAME (same parent) from MOVE (reparent)."""
    return {r["target_oid"] for r in recs
            if r["opcode"] == opcode and r["filename"] and r["filename"] != "$I30" and r["target_oid"]}

def classify_mlog_transaction(recs):
    """Classify a redo transaction into a concrete action.

    Uses the redo opcode SET, and — for name-entry changes — the TARGET OID (parent-directory table) of the
    old vs new entry, so RENAME (same parent) and MOVE (reparented to another directory) are told apart by
    fact, not guessed from opcode presence. Rules that matter forensically:
      * DELETE is returned ONLY when the object's own table is destroyed (RedoDeleteTable, 0x0F). A bare
        DeleteRow (0x02) is the OLD-name removal of a rename/move, or a hard-link unlink — labelled
        ENTRY_REMOVE, never DELETE.
      * CREATE = a new table opened + its name row + parent id set. HARDLINK = a new name row for an
        EXISTING object (insert name, no new table, no delete)."""
    ops = [r["opcode"] for r in recs]
    op_set = set(ops)
    fnames = [r["filename"] for r in recs if r["filename"] and r["filename"] != "$I30"]
    has_open = 0x00 in op_set
    has_insert = 0x01 in op_set
    has_delete = 0x02 in op_set
    has_set_parent = 0x0E in op_set
    has_del_table = 0x0F in op_set
    has_reparent = 0x05 in op_set
    has_alloc = 0x06 in op_set
    has_upd_data = 0x04 in op_set
    has_set_objrec = 0x10 in op_set
    named_ins = bool(_mlog_name_entry_parents(recs, 0x01))
    named_del = bool(_mlog_name_entry_parents(recs, 0x02))

    # Real deletion: the object's own B+-tree table is destroyed.
    if has_del_table:
        return "DELETE"
    # Name-entry change WITH a matching removal: RENAME (same parent OID) vs MOVE (parent OID changed).
    if named_del and named_ins:
        old_par = _mlog_name_entry_parents(recs, 0x02)
        new_par = _mlog_name_entry_parents(recs, 0x01)
        if old_par and new_par:
            if old_par == new_par:
                return "RENAME"
            if not (old_par & new_par):
                return "MOVE"
        return "MOVE" if has_reparent else "RENAME"   # OID inconclusive → reparent opcode decides
    # A NEW name row with no removal = a newly created directory entry (create / copy / hard-link — the
    # last is not reliably separable per-transaction, and is a name-creation regardless; the redo records
    # under -v, e.g. OpenTable vs a pointer to an existing OID, distinguish them for an analyst).
    if named_ins and not has_delete:
        return "CREATE"
    # A create whose name row is in another transaction: this fragment opens the table + sets its parent.
    if has_open and has_set_parent and not has_delete:
        return "CREATE"
    # A reparent record WITHOUT both name entries: it belongs to a move or a rename, but which one cannot be
    # decided from one transaction (the reparent's own target_oid is not reliably the new parent), so it is
    # labelled REPARENT rather than guessed — MOVE/RENAME above are only claimed on the parent-OID evidence.
    if has_reparent:
        return "REPARENT"
    if any(o in (0x1F, 0x20) for o in ops):
        return "STREAM_UPD"
    if any(o in (0x12, 0x13, 0x14, 0x15) for o in ops):
        return "CONTAINER"
    # Write: a data-record change on an EXISTING object (no new name entry — those became CREATE above).
    if has_insert and (has_set_objrec or has_upd_data):
        return "WRITE"
    if has_alloc and not has_insert:
        return "ALLOCATE"
    # Bare DeleteRow with no table destroyed = old-name removal of a rename/move (its InsertRow is in a
    # different transaction) or a hard-link unlink — NOT a file deletion.
    if has_delete and not has_insert:
        return "ENTRY_REMOVE"
    if has_delete and has_insert:
        return "UPDATE"
    if all(o in (0x03, 0x04, 0x08, 0x09, 0x10, 0x0D, 0x16, 0x20) for o in ops):
        return "MODIFY"
    if any(o in (0x28, 0x29) for o in ops):
        return "DEDUP"
    if any(o in (0x0A, 0x0B, 0x21) for o in ops):
        return "EXTENT_MOD"
    if any(o == 0x07 for o in ops):
        return "MODIFY"
    if has_insert and not has_delete and len(ops) <= 2:
        return "INSERT"
    return "OP"


def build_oid_path_map(f, ps_off, cs, tr, obj_map):
    """Build OID -> full path map by walking the directory tree from root."""
    paths = dict(KNOWN_SYSTEM_OIDS)
    paths[0x600] = "/"
    visited = set()

    def _walk(oid, parent_path, depth):
        if depth > 50 or oid in visited or oid not in obj_map:
            return
        visited.add(oid)
        try:
            rows = walk_bplus(f, ps_off, cs, tr,
                              _as_vlcn_list(obj_map[oid]))
        except Exception:
            return
        for kd, vd in rows:
            if len(kd) < 6 or le16(kd, 0) != 0x30:
                continue
            try:
                name = kd[4:].decode("utf-16-le").rstrip("\x00")
            except UnicodeDecodeError:
                continue
            if not name:
                continue
            # value+0x08 is the child's OID for a DIRECTORY entry, but the home-dir BACKREF for a FILE
            # entry (#327) — for root-created files that backref is 0x600, which would overwrite
            # paths[0x600]="/" (corrupting the path of every record whose parent is root). This OID->path
            # map is only meaningful for directory objects (USN/MLog resolve a record's PARENT, always a
            # directory), so index/recurse on directories only. Directory marker = attribute bit
            # 0x10000000 at value+0x40 (errata E32), NOT key_flags 0x04.
            if not (le32(vd, 0x40) & 0x10000000 if len(vd) >= 0x44 else False):
                continue
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            full = "%s/%s" % (parent_path.rstrip("/"), name)
            if child_oid:
                paths[child_oid] = full
                if child_oid in obj_map:
                    _walk(child_oid, full, depth + 1)

    _walk(0x600, "", 0)
    return paths


# ═══════════════════════════════════════════════════════════════════════
# USN (Change) Journal parsing
# ═══════════════════════════════════════════════════════════════════════

USN_REASON_FLAGS = {
    0x00000001: "DATA_OVERWRITE",
    0x00000002: "DATA_EXTEND",
    0x00000004: "DATA_TRUNCATION",
    0x00000010: "NAMED_DATA_OVERWRITE",
    0x00000020: "NAMED_DATA_EXTEND",
    0x00000040: "NAMED_DATA_TRUNCATION",
    0x00000100: "FILE_CREATE",
    0x00000200: "FILE_DELETE",
    0x00000400: "EA_CHANGE",
    0x00000800: "SECURITY_CHANGE",
    0x00001000: "RENAME_OLD_NAME",
    0x00002000: "RENAME_NEW_NAME",
    0x00004000: "INDEXABLE_CHANGE",
    0x00008000: "BASIC_INFO_CHANGE",
    0x00010000: "HARD_LINK_CHANGE",
    0x00020000: "COMPRESSION_CHANGE",
    0x00040000: "ENCRYPTION_CHANGE",
    0x00080000: "OBJECT_ID_CHANGE",
    0x00100000: "REPARSE_POINT_CHANGE",
    0x00200000: "STREAM_CHANGE",
    0x00400000: "TRANSACTED_CHANGE",
    0x00800000: "INTEGRITY_CHANGE",
    0x80000000: "CLOSE",
}

USN_SOURCE_FLAGS = {
    0x00000001: "DATA_MANAGEMENT",
    0x00000002: "AUXILIARY_DATA",
    0x00000004: "REPLICATION_MANAGEMENT",
    0x00000008: "CLIENT_REPLICATION_MANAGEMENT",
}

USN_MIN_RECORD = 0x50
USN_MAX_RECORD = 65536
OID_FS_METADATA = 0x520


def usn_reason_to_str(reason):
    parts = []
    for bit, name in sorted(USN_REASON_FLAGS.items()):
        if reason & bit:
            parts.append(name)
    return " | ".join(parts) if parts else "0x%08x" % reason


def usn_reason_to_short(reason):
    core = reason & ~0x80000000
    parts = []
    for bit, name in sorted(USN_REASON_FLAGS.items()):
        if bit == 0x80000000:
            continue
        if core & bit:
            parts.append(name)
    close = " + CLOSE" if reason & 0x80000000 else ""
    return ("|".join(parts) + close) if parts else "0x%08x" % reason


class UsnRecord:
    __slots__ = (
        "record_length", "major_version", "minor_version",
        "file_oid", "file_idx", "parent_oid", "parent_idx",
        "usn", "timestamp", "reason", "source_info",
        "security_id", "file_attrs", "filename", "offset",
    )

    def __init__(self, data, off):
        self.offset = off
        self.record_length = le32(data, off)
        self.major_version = le16(data, off + 0x04)
        self.minor_version = le16(data, off + 0x06)
        fid_lo = le64(data, off + 0x08)
        fid_hi = le64(data, off + 0x10)
        self.file_idx = fid_lo
        self.file_oid = fid_hi
        pid_lo = le64(data, off + 0x18)
        pid_hi = le64(data, off + 0x20)
        self.parent_idx = pid_lo
        self.parent_oid = pid_hi
        self.usn = le64(data, off + 0x28)
        self.timestamp = le64(data, off + 0x30)
        self.reason = le32(data, off + 0x38)
        self.source_info = le32(data, off + 0x3C)
        self.security_id = le32(data, off + 0x40)
        self.file_attrs = le32(data, off + 0x44)
        name_len = le16(data, off + 0x48)
        name_off = le16(data, off + 0x4A)
        try:
            self.filename = data[off + name_off:off + name_off + name_len].decode("utf-16-le")
        except (UnicodeDecodeError, IndexError):
            self.filename = "<decode error at 0x%x>" % off


_usn_nonv3_warned = False

def _warn_usn_nonv3(versions):
    """One-time light warning when a non-V3 USN record is accepted (N1). ReFS on-disk records are V3;
    the decoder only knows the V3 field layout, so V2/V4 records are parsed with V3 offsets and NOT
    validated. We do not refuse them (per user request) — we flag them once."""
    global _usn_nonv3_warned
    if _usn_nonv3_warned:
        return
    _usn_nonv3_warned = True
    vs = "/".join("V%d" % v for v in sorted(versions))
    print("[%s] NOTE: USN record version(s) %s encountered. ReFS journals are normally V3; the decoder uses "
          "the V3 field layout, so %s records are parsed with V3 offsets and their fields are NOT validated "
          "for that version (V2 is NTFS's 64-bit form, V4 is NTFS-only range tracking — see erratum E58)."
          % (PROG, vs, vs), file=sys.stderr)


def parse_usn_records(j_data):
    records = []
    off = 0
    end = len(j_data)
    nonv3 = set()
    while off < end - USN_MIN_RECORD:
        rec_len = le32(j_data, off)
        if rec_len == 0:
            off += 8; continue
        if rec_len < USN_MIN_RECORD or rec_len > USN_MAX_RECORD or (rec_len & 7) != 0:
            off += 8; continue
        if off + rec_len > end:
            break
        major = le16(j_data, off + 0x04)
        # Accept USN record versions 2, 3 and 4. On a ReFS journal every on-disk record is V3 (128-bit
        # file IDs); V2 (NTFS's 64-bit form) and V4 (USN_RECORD_V4, the NTFS-only range-tracking / extent
        # record — `fsutil usn enablerangetracking` refuses ReFS with "A local NTFS volume is required for
        # this operation", erratum E58) do not occur on ReFS. We still PARSE a V2/V4 record if one appears
        # (a non-ReFS journal, or crafted/corrupt input) rather than refuse it, but we only have the V3
        # field layout — so those records are decoded with V3 offsets and flagged once via _warn_usn_nonv3.
        if major < 2 or major > 4:
            off += 8; continue
        name_off_field = le16(j_data, off + 0x4A)
        name_len_field = le16(j_data, off + 0x48)
        if name_off_field < 0x4C or name_off_field + name_len_field > rec_len:
            off += 8; continue
        records.append(UsnRecord(j_data, off))
        if major != 3:
            nonv3.add(major)
        off += (rec_len + 7) & ~7
    if nonv3:
        _warn_usn_nonv3(nonv3)
    return records


def locate_change_journal(f, ps, cs, tr, obj_map):
    """Find Change Journal entry in OID 0x520 (FS Metadata directory)."""
    if OID_FS_METADATA not in obj_map:
        return None, None
    vlcns = obj_map[OID_FS_METADATA]
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception:
        return None, None
    for kd, vd in rows:
        if len(kd) < 4 or le16(kd, 0) != 0x30:
            continue
        try:
            name = kd[4:].decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError:
            continue
        if name == "Change Journal":
            meta = {}
            if len(vd) >= 0x48:
                meta["stream_count"] = le64(vd, 0x20)
                meta["create_time"] = le64(vd, 0x28)
                meta["modify_time"] = le64(vd, 0x30)
                meta["change_time"] = le64(vd, 0x38)
                meta["access_time"] = le64(vd, 0x40)
            if len(vd) >= 0x60:
                meta["file_attrs"] = le32(vd, 0x48)
                meta["security_id"] = le64(vd, 0x50)
            meta["value_len"] = len(vd)
            return bytes(vd), meta
    return None, None


def _usn_find_subrecord_markers(vd):
    subs = []
    off = 0xA8
    while off < len(vd) - 8:
        marker = le32(vd, off)
        if marker in (0x80000002, 0x80000001):
            stream_size = le32(vd, off + 4) if off + 8 <= len(vd) else 0
            subs.append((off, marker, stream_size))
        off += 4
    return subs


def _usn_scan_extent_tables(vd, tr):
    results = []
    for scan_off in range(0xA8, len(vd) - 24, 4):
        start = le32(vd, scan_off)
        end = le32(vd, scan_off + 4)
        if not (0x10 <= start <= 0x200 and end > start):
            continue
        cap = le32(vd, scan_off + 12)
        count = le32(vd, scan_off + 20)
        if not (count > 0 and count <= 1000 and cap >= 0x100):
            continue
        entry_area = end - start
        if entry_area < count * 24 or entry_area > count * 32 + 16:
            continue
        entries_off = scan_off + start
        extents = []
        for i in range(count):
            eoff = entries_off + i * 24
            if eoff + 24 > len(vd):
                break
            vlcn_lo = le32(vd, eoff)
            vlcn_hi = le32(vd, eoff + 4)
            full_vlcn = vlcn_lo | (vlcn_hi << 32)
            ext_flags = le32(vd, eoff + 8)
            file_vcn = le32(vd, eoff + 12)
            run_len = le32(vd, eoff + 20)
            if run_len > 0 and full_vlcn > 0:
                plcn = tr.tr(full_vlcn) if tr else full_vlcn
                extents.append({
                    "vlcn": full_vlcn, "plcn": plcn,
                    "file_vcn": file_vcn, "clusters": run_len,
                    "flags": ext_flags,
                })
        if extents:
            extents.sort(key=lambda e: e["file_vcn"])
            results.append((scan_off, extents))
    return results


def _usn_parse_single_subrecord(vd, sub_off):
    data_start = sub_off + 8
    next_marker = len(vd)
    for off in range(data_start, len(vd) - 4, 4):
        m = le32(vd, off)
        if m in (0x80000002, 0x80000001):
            next_marker = off
            break
    data_len = next_marker - data_start
    if data_len <= 0:
        return None
    return bytes(vd[data_start:data_start + data_len])


def parse_usn_journal_streams(vd, cs, tr):
    """Parse sub-records and extent tables from the Change Journal value."""
    markers = _usn_find_subrecord_markers(vd)
    extent_tables = _usn_scan_extent_tables(vd, tr)
    multi_markers = [(off, sz) for off, m, sz in markers if m == 0x80000002]
    single_markers = [off for off, m, sz in markers if m == 0x80000001]
    j_extents = []
    j_stream_size = 0
    max_extents = []
    max_stream_size = 0
    if extent_tables:
        best = max(extent_tables, key=lambda t: sum(e["clusters"] for e in t[1]))
        j_extents = best[1]
    if len(multi_markers) >= 1:
        j_stream_size = multi_markers[0][1]
    if len(multi_markers) >= 2:
        max_stream_size = multi_markers[1][1]
        if len(extent_tables) >= 2:
            others = [t for t in extent_tables if t[1] is not j_extents]
            if others:
                max_extents = others[0][1]
    metadata_raw = None
    if single_markers:
        metadata_raw = _usn_parse_single_subrecord(vd, single_markers[0])
    return {
        "j_extents": j_extents, "j_stream_size": j_stream_size,
        "max_extents": max_extents, "max_stream_size": max_stream_size,
        "metadata_raw": metadata_raw, "subrecord_count": len(markers),
    }


def read_usn_j_stream(f_handle, ps, cs, extents, stream_size):
    """Read USN $J data stream from disk following extent descriptors."""
    if not extents:
        return b""
    total_clusters = sum(e["clusters"] for e in extents)
    alloc_size = total_clusters * cs
    if stream_size > alloc_size:   # N5: signal truncation (mirrors the extract short-read warning, E8)
        print(f"[{PROG}] WARNING: USN $J stream declares {stream_size:,} bytes but only {alloc_size:,} are "
              f"allocated in its extents; parsing the truncated journal (records beyond {alloc_size:,} unavailable)",
              file=sys.stderr)
    buf = bytearray(min(alloc_size, stream_size) if 0 < stream_size <= alloc_size else alloc_size)
    for ext in extents:
        file_off = ext["file_vcn"] * cs
        disk_off = ps + ext["plcn"] * cs
        nbytes = ext["clusters"] * cs
        read_end = min(file_off + nbytes, len(buf))
        if file_off >= len(buf):
            continue
        to_read = read_end - file_off
        f_handle.seek(disk_off)
        data = f_handle.read(to_read)
        buf[file_off:file_off + len(data)] = data
    return bytes(buf)


def parse_usn_journal_metadata(streams, f_handle, ps, cs):
    """Parse $Max stream and single-instance metadata."""
    meta = {}
    if streams["metadata_raw"] and len(streams["metadata_raw"]) >= 16:
        raw = streams["metadata_raw"]
        if len(raw) >= 8:
            meta["meta_field_0x00"] = le64(raw, 0)
        if len(raw) >= 16:
            meta["meta_field_0x08"] = le64(raw, 8)
        if len(raw) >= 24:
            meta["meta_field_0x10"] = le64(raw, 16)
        if len(raw) >= 32:
            meta["meta_field_0x18"] = le64(raw, 24)
        meta["metadata_size"] = len(raw)
    if streams["max_extents"]:
        max_data = read_usn_j_stream(f_handle, ps, cs, streams["max_extents"],
                                      streams["max_stream_size"])
        if len(max_data) >= 32:
            meta["max_size"] = le64(max_data, 0)
            meta["allocation_delta"] = le64(max_data, 8)
            meta["journal_id"] = le64(max_data, 16)
            if len(max_data) >= 40:
                meta["lowest_valid_usn"] = le64(max_data, 24)
        meta["max_raw"] = max_data[:64].hex() if max_data else ""
    return meta


# ─── Reparse target extraction ────────────────────────────────────────
def get_reparse_target(f, ps, cs, tr, vlcns):
    """Extract reparse point target from an object's B+ tree (type 0xC0)."""
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception:
        return ""
    for kd, vd in rows:
        if len(kd) >= 2 and le16(kd, 0) == 0xC0 and len(vd) >= 8:
            tag = le32(vd, 0)
            data_len = le16(vd, 4)
            if tag == 0xA000000C and len(vd) >= 0x14:  # SYMLINK
                sub_off = le16(vd, 0x08)
                sub_len = le16(vd, 0x0A)
                print_off = le16(vd, 0x0C)
                print_len = le16(vd, 0x0E)
                buf_start = 0x14
                if print_len > 0 and buf_start + print_off + print_len <= len(vd):
                    try:
                        return vd[buf_start+print_off:buf_start+print_off+print_len].decode("utf-16-le")
                    except UnicodeDecodeError:
                        pass
                if sub_len > 0 and buf_start + sub_off + sub_len <= len(vd):
                    try:
                        return vd[buf_start+sub_off:buf_start+sub_off+sub_len].decode("utf-16-le")
                    except UnicodeDecodeError:
                        pass
            elif tag == 0xA0000003 and len(vd) >= 0x10:  # MOUNT_POINT/JUNCTION
                sub_off = le16(vd, 0x08)
                sub_len = le16(vd, 0x0A)
                print_off = le16(vd, 0x0C)
                print_len = le16(vd, 0x0E)
                buf_start = 0x10
                if print_len > 0 and buf_start + print_off + print_len <= len(vd):
                    try:
                        return vd[buf_start+print_off:buf_start+print_off+print_len].decode("utf-16-le")
                    except UnicodeDecodeError:
                        pass
            elif tag == 0xA000001D and len(vd) > 8:  # LX_SYMLINK
                # E5 fix: skip the 4-byte version (8 -> 12) so it does not prefix the target.
                try:
                    return vd[12:8+data_len].decode("utf-8").rstrip("\x00")
                except UnicodeDecodeError:
                    pass
            return REPARSE_TAGS.get(tag, f"0x{tag:08X}")
    return ""

# ─── Directory tree walk ─────────────────────────────────────────────
def walk_directory_tree(f, ps, cs, tr, obj_map, start_oid, max_depth, enrich, trash_set):
    """Walk the directory tree and collect file metadata."""
    results = []
    visited = set()
    t40_content = {}     # (owner_dir_oid, file_id) -> has_real_content (alloc>0 or size>0); alloc=0 stubs map to False
    nonres_files = []    # non-resident file entries, grouped into hard-link sets in post-processing

    # Reparse existence-index (OID 0x540): {(owner_oid, file_id): tag}. Key = marker(0x80000001)@0,
    # tag@4, file_id@8, owner@0x10 (H3-verified). Used as the ReparseTag source for directory
    # junctions and as the fallback when a non-resident file's backing +0x7C tag is 0.
    reparse_idx = {}
    if enrich and 0x540 in obj_map:
        try:
            for _kd, _vd in walk_bplus(f, ps, cs, tr, obj_map[0x540]):
                if len(_kd) >= 0x18 and le32(_kd, 0) == 0x80000001:
                    reparse_idx[(le64(_kd, 0x10), le64(_kd, 0x08))] = le32(_kd, 0x04)
        except Exception:
            pass

    def _walk_dir(oid, parent_path, parent_oid, depth):
        if depth > max_depth or oid in visited:
            return
        visited.add(oid)
        if oid not in obj_map:
            return

        vlcns = obj_map[oid]
        try:
            rows = walk_bplus(f, ps, cs, tr, vlcns)
        except Exception:
            return

        # Extract this directory's own $SI (type 0x10) if enrichment is on
        dir_si = None
        for kd, vd in rows:
            if len(kd) >= 2 and le16(kd, 0) == 0x10:
                if len(vd) >= 0x60:
                    dir_si = {
                        "security_id": le64(vd, 0x50),
                        # usn = LastUsn ($SI+0x40 / value+0x68), the real journal pointer
                        # (value+0x58 = $SI+0x30 is unpopulated). See E30 retraction / E45.
                        "usn": le64(vd, 0x68) if len(vd) >= 0x70 else 0,
                        "internal_flags": le32(vd, 0x4C),
                    }
                break

        for kd, vd in rows:
            if len(kd) < 4: continue
            attr_type = le16(kd, 0)
            if attr_type == 0x40:
                # Record this file's backing type-0x40 stream as (alloc, size) under (this dir, file_id).
                # The hard-link grouping below resolves each name to the candidate stream (local or home)
                # whose SIZE matches the name's own size (val+0x38): the per-directory ordinal (file_id
                # @key+0x08) collides across files home'd in the same dir, so size is the disambiguator.
                # alloc @val+0x60, size @val+0x58. (#340 / over-merge fix 2026-06-20.)
                if len(kd) >= 0x10:
                    _a = le64(vd, 0x60) if len(vd) >= 0x68 else 0
                    _s = le64(vd, 0x58) if len(vd) >= 0x60 else 0
                    # #327: the backing record IS the file's own $SI/stream-summary, same layout as the
                    # resident type-0x30 value — SecurityId at val+0x50, internal-flags at val+0x4C,
                    # LastUsn at val+0x68 ($SI+0x40), journal-id at val+0x70.
                    _u = le64(vd, 0x68) if len(vd) >= 0x70 else 0
                    _j = le64(vd, 0x70) if len(vd) >= 0x78 else 0
                    _sid = le64(vd, 0x50) if len(vd) >= 0x58 else 0
                    _if = le32(vd, 0x4C) if len(vd) >= 0x50 else 0
                    # H3: reparse tag mirror @val+0x7C (valid only if bit31 set) + the embedded
                    # REPARSE_DATA_BUFFER target (v3.14). Both ride this backing record; the hard-link
                    # resolution below picks the file's OWN backing, so the resolved rec carries the
                    # right tag/target (avoids the file_id-collision wrong-target bug). Target scan is
                    # gated on a symlink/junction tag so non-reparse records are not scanned.
                    _tag = le32(vd, 0x7C) if len(vd) >= 0x80 else 0
                    if not (_tag >> 31) & 1:
                        _tag = 0
                    _tgt = extract_reparse_from_backing(vd) if _tag in (0xA000000C, 0xA0000003) else ""
                    # Backing file_attrs (+0x48): the AUTHORITATIVE attrs for a non-resident file. The
                    # type-0x30 pointer's +0x40 attrs omit the EA bit (0x40000) — proven on disk (only the
                    # EA bit, plus a rare Archive-bit, ever differ). We OR ONLY the EA bit back in post-
                    # processing so HasEA / FileAttributes / --filter ea are correct for non-resident files.
                    _bfa = le32(vd, 0x48) if len(vd) >= 0x4C else 0
                    t40_content[(oid, le64(kd, 0x08))] = (_a, _s, _u, _j, _sid, _if, _tag, _tgt, _bfa)
                continue
            if attr_type != 0x30: continue

            try:
                name = kd[4:].decode("utf-16-le").rstrip("\x00")
            except UnicodeDecodeError:
                name = kd[4:].hex()

            full_path = f"{parent_path}/{name}" if parent_path else name
            entry = {"path": full_path, "parent_path": parent_path if parent_path else ".", "parent_oid": oid, "name": name}

            if len(vd) <= NON_RESIDENT_MAX_VALUE:
                # Non-resident entry (directory or large file)
                file_id = le64(vd, 0x00) if len(vd) >= 8 else 0      # FileId / per-directory child ordinal
                backref = le64(vd, 0x08) if len(vd) >= 0x10 else 0   # val+0x08 (see oid gating below)
                entry["file_id"] = file_id
                entry["create_time"] = le64(vd, 0x10) if len(vd) >= 0x18 else 0
                entry["modify_time"] = le64(vd, 0x18) if len(vd) >= 0x20 else 0
                entry["change_time"] = le64(vd, 0x20) if len(vd) >= 0x28 else 0
                entry["access_time"] = le64(vd, 0x28) if len(vd) >= 0x30 else 0
                entry["file_attrs"] = le32(vd, 0x40) if len(vd) >= 0x44 else 0
                entry["file_size"] = le64(vd, 0x38) if len(vd) >= 0x40 else 0
                entry["is_dir"] = bool(entry["file_attrs"] & 0x10000000)
                entry["is_resident"] = False
                entry["security_id"] = 0
                entry["usn"] = 0
                entry["internal_flags"] = 0
                entry["allocated_size"] = None   # filled from the resolved type-0x40 backing (files) in
                                                 # post-processing; stays None (=> blank) when unresolved,
                                                 # consistent with USN/SecurityId on the same entries.

                # val+0x08 is the object's OWN OID only for a SUBDIRECTORY (dir-bit set). For a
                # non-resident FILE it is the home-dir backref (the OID of the directory the file was
                # first created in) -- a DIFFERENT object's OID, shared by the file's hard-link names.
                # A non-resident file has NO Object-Table OID of its own, so reporting the backref as
                # the file's oid made files collide with real directories (--oid bug, fixed 2026-06-27;
                # master 0x08 home-dir backref / #327 / #335 / #340 / FN_LINK_002).
                if entry["is_dir"]:
                    entry["oid"] = backref          # subdirectory's own OID
                    entry["home_oid"] = 0
                else:
                    entry["oid"] = 0                 # files have no own OID (matches resident files)
                    entry["home_oid"] = backref      # home-dir backref, used only for hard-link grouping

                # Hard-link detection (finding #340): a file's multiple names all resolve to the SAME backing
                # type-0x40 record. Collect the non-resident file entries now; the actual grouping (which uses
                # home_oid + file_id) happens in post-processing once every dir's type-0x40 records have been
                # seen, so each name can be resolved to its true physical object. Files only; directories
                # cannot be hard-linked.
                if backref and file_id and not entry["is_dir"]:
                    nonres_files.append(entry)

                # Enrichment: a non-resident DIRECTORY has its own $SI in its own B+ tree (backref is its own
                # OID). A non-resident FILE does NOT -- backref points at the HOME DIRECTORY, not the file, so
                # reading get_object_si(backref) would attribute the home dir's security_id/internal_flags to
                # the file. The file's usn comes from its own type-0x40 backing record in post-processing; its
                # security_id is not on-disk recoverable from its records (left 0). RD-proven 2026-06-27.
                if enrich and entry["is_dir"] and backref and backref in obj_map:
                    si = get_object_si(f, ps, cs, tr, obj_map[backref])
                    if si:
                        entry["security_id"] = si.get("security_id", 0)
                        entry["usn"] = si.get("usn", 0)
                        entry["internal_flags"] = si.get("internal_flags", 0)
            else:
                # Resident entry (small file)
                entry["oid"] = 0  # No separate OID for resident files
                entry["is_resident"] = True
                entry["is_dir"] = False
                if len(vd) >= 0x60:
                    entry["create_time"] = le64(vd, 0x28)
                    entry["modify_time"] = le64(vd, 0x30)
                    entry["change_time"] = le64(vd, 0x38)
                    entry["access_time"] = le64(vd, 0x40)
                    entry["file_attrs"] = le32(vd, 0x48)
                    entry["internal_flags"] = le32(vd, 0x4C)
                    entry["security_id"] = le64(vd, 0x50)
                    # RE-VERIFIED 2026-06-17 at corpus scale (errata E30 retracted / E45):
                    # the type-0x30 resident value is an INDEX ENTRY (not a verbatim $SI). At value+0x58
                    # it carries FileSize (== embedded-$DATA size on 409,514/409,514 v3.14 files; nonzero
                    # even on USN-inactive images), and value+0x60 = AllocatedSize. There is NO embedded
                    # $SI sub-record (a prior comment claimed so -- wrong). The file's USN-journal pointer
                    # is LastUsn at value+0x68 ($SI+0x40) and UsnJournalId at value+0x70 ($SI+0x48):
                    # LastUsn = virtual byte offset of the file's most recent $UsnJrnl:$J record (OID 0x520),
                    # disk-proven (14/14 then 480/480 LastUsn->$J-record name matches). 0 if journal inactive.
                    entry["usn"] = le64(vd, 0x68) if len(vd) >= 0x70 else 0
                    entry["usn_journal_id"] = le64(vd, 0x70) if len(vd) >= 0x78 else 0
                    entry["allocated_size"] = le64(vd, 0x60)
                else:
                    entry["create_time"] = 0
                    entry["modify_time"] = 0
                    entry["change_time"] = 0
                    entry["access_time"] = 0
                    entry["file_attrs"] = 0
                    entry["internal_flags"] = 0
                    entry["security_id"] = 0
                    entry["usn"] = 0
                    entry["allocated_size"] = 0
                entry["file_size"] = get_resident_file_size(vd)

            # Derived flags
            fa = entry.get("file_attrs", 0)
            entry["is_encrypted"] = bool(fa & 0x4000)
            entry["is_compressed"] = bool(fa & 0x0800)
            entry["has_integrity"] = bool(fa & 0x8000)
            entry["has_ea"] = bool(fa & 0x00040000)
            entry["has_reparse"] = bool(fa & 0x0400)
            entry["is_deleted"] = entry["oid"] in trash_set if entry["oid"] else False
            entry["deletion_source"] = "trash" if entry["is_deleted"] else ""
            entry["snapshot_count"] = 0

            # ADS, reparse, and snapshot enrichment
            entry["has_ads"] = False
            entry["ads_names"] = ""
            entry["reparse_target"] = ""
            if enrich:
                if entry["has_reparse"]:
                    if entry["is_resident"]:
                        entry["reparse_target"] = extract_inline_reparse(vd)
                        # resident reparse tag = the $SI mirror at type-0x30 value+0x7C (H3-verified
                        # 2905/2905 across v3.4..v3.14); validate bit31 (Microsoft reparse tag).
                        if len(vd) >= 0x80:
                            _rt = le32(vd, 0x7C)
                            if (_rt >> 31) & 1:
                                entry["reparse_tag_value"] = _rt
                    elif entry["oid"] and entry["oid"] in obj_map:
                        # non-resident DIRECTORY junction: target via its own 0xC0 attribute; tag via
                        # the reparse index (keyed by parent dir OID + file_id).
                        entry["reparse_target"] = get_reparse_target(f, ps, cs, tr, obj_map[entry["oid"]])
                        _rt = (reparse_idx.get((oid, entry.get("file_id", 0)), 0)
                               or reparse_idx.get((entry["oid"], entry.get("file_id", 0)), 0))
                        if (_rt >> 31) & 1:
                            entry["reparse_tag_value"] = _rt
                    # non-resident FILE reparse: tag + target are set from the resolved backing record
                    # in post-processing (the home stream), which avoids the file_id-collision bug.

                # ADS are embedded 0xB0 sub-records inside the resident (value > 84 B) type-0x30 entry, so a
                # file that HAS an ADS is always is_resident here -- this resident path is complete. Verified
                # corpus-wide 2026-06-28: forefst has_ads == an independent embedded-ADS recount (678 == 678,
                # 0 divergent images) and 0 standalone 0x80/0xB0 stream rows exist on disk. A non-resident
                # file's value is the <=84 B index pointer (no embedded chain) and it has no own OID, so it
                # carries no ADS; the former oid-gated non-resident branch was therefore dead (removed).
                if entry["is_resident"] and not entry["is_dir"]:
                    has_ads, ads_list = detect_ads_in_resident(vd)
                    if has_ads:
                        entry["has_ads"] = True
                        entry["ads_names"] = ";".join(ads_list)

            # Snapshot count -- snapshots are likewise embedded 0xB0 sub-records in the resident (value > 84 B)
            # entry, so this resident path is complete (same corpus proof as ADS above). A non-resident file
            # carries no embedded snapshot record; the former oid-gated non-resident branch was dead (removed).
            if entry["is_resident"] and len(vd) > 0x60:
                entry["snapshot_count"] = count_snapshots_in_resident(vd)

            # F5: a "long value" file we parsed + enriched via the inline path above is actually NON-RESIDENT
            # when its CURRENT $DATA stream is extent-backed (on disk, not inline). ADS/reparse/snapshot were
            # already read from the inline value (correct); only the reported residency must reflect the
            # on-disk truth. Fixes ~209 large files/win11refs8g mislabeled resident (blanked HardLinkCount).
            if entry["is_resident"] and not entry["is_dir"]:
                if _current_stream_extent_backed(vd):
                    entry["is_resident"] = False
                else:
                    # B2: multi-level embedded-tree resident value (v3.4/v3.9/upgraded framing). Its $DATA
                    # lives in a NESTED subtree, so file_size read 0 and residency was mislabeled resident.
                    # The true size (value+0x58) + alloc (value+0x60) are directly readable; when alloc>0
                    # with no inline $DATA the file is extent-backed (NON-resident).
                    _ml_size = _multilevel_extent_backed_size(vd, cs)
                    if _ml_size is not None:
                        entry["file_size"] = _ml_size
                        entry["is_resident"] = False

            results.append(entry)

            # Recurse into directories
            if entry["is_dir"] and entry["oid"] and entry["oid"] in obj_map:
                _walk_dir(entry["oid"], full_path, oid, depth + 1)

    _walk_dir(start_oid, "", start_oid, 0)

    # Post-process: group a file's names by their TRUE physical stream record (owner-dir, file_id).
    # file_id is the per-directory child ordinal (type-0x30 value+0x00), which COLLIDES — a directory
    # can hold the stream of a DIFFERENT file that was home'd there with the same ordinal. The on-disk
    # disambiguator is the name's own size (type-0x30 value+0x38): a name's real content is the candidate
    # stream — local (parent,file_id) or home (home,file_id) — whose 0x40 size EQUALS the name's size.
    # STRICT size-match => 0 over-merge (distinct-size files colliding on the ordinal stay apart); names
    # matching no candidate are not merged (solo, count 1). A hard LINK with an alloc=0 STUB (MD_DATA_RA_006)
    # resolves to its home stream (the stub's size 0 != the name's real size, the home stream's size matches).
    # Validated all-disk 2026-06-20: 0 over-merge / fsutil control [4,2] / genuine groups preserved
    # (winsider 33,104). Replaces the (home,ordinal,size,ctime,mtime) tuple and the presence-based
    # content-aware key, BOTH of which over-merged on the colliding ordinal (the size guard was dropped).
    hl_groups = {}
    for i, e in enumerate(nonres_files):
        P = e["parent_oid"]; fid = e["file_id"]; home = e.get("home_oid", 0); S = e.get("file_size", 0)
        loc = t40_content.get((P, fid))      # (alloc, size, last_usn, journal_id) or None
        rem = t40_content.get((home, fid))
        if loc and loc[1] == S and loc[0] > 0:            # living here: local stream size+alloc match
            sig = ("obj", P, fid); rec = loc
        elif rem and rem[1] == S:                          # content at home: home stream size matches
            sig = ("obj", home, fid); rec = rem
        elif loc and loc[1] == S:                          # local size matches (alloc 0 edge)
            sig = ("obj", P, fid); rec = loc
        elif S == 0 and rem is not None and rem[1] == 0:   # empty file: canonical empty home stream
            sig = ("obj", home, fid, 0); rec = rem
        elif S == 0 and loc is not None and loc[1] == 0:
            sig = ("obj", P, fid, 0); rec = loc
        else:                                              # no size-matching stream -> not a confident member
            sig = ("solo", e["path"], i); rec = None
        # Per-file USN (#327): the file's LastUsn is in its OWN resolved backing record (val+0x68 =
        # $SI+0x40), NOT the home directory's $SI. RD-proven 245/245 vs fsutil + 593/0 five-image;
        # static RefsComputeStandardInformationFromFcb maps $SI+0x40 <- FCB+0xe0 (per-file cursor).
        if rec is not None and len(rec) >= 4:
            e["usn"] = rec[2]; e["usn_journal_id"] = rec[3]
            # Per-file SecurityId / internal-flags (#327, problem.md #3): from the file's OWN resolved
            # backing record (val+0x50 / val+0x4C in the same $SI layout), NOT the home directory's $SI.
            # Disk-proven 2026-06-28: backing +0x50 is the file's real SID (e.g. 7973161277 on
            # win11refs2gtargeted, a member of the resident-file SID set; matches problem.md #3's
            # 295/295 + 448/449 on the 4 GB images). Replaces the honest-but-incomplete 0.
            if len(rec) >= 6:
                if rec[4]: e["security_id"] = rec[4]
                if rec[5]: e["internal_flags"] = rec[5]
            # H3: AllocatedSize = the resolved stream's alloc (val+0x60), read verbatim.
            e["allocated_size"] = rec[0]
            # Fix: the EA bit (0x40000) is in the backing's file_attrs (+0x48), NOT the type-0x30
            # pointer (+0x40) this entry was parsed from. OR it in so HasEA / FileAttributes / --filter
            # ea are correct for non-resident files. (Only the EA bit — the rare Archive-bit diff is left.)
            if len(rec) >= 9 and (rec[8] & 0x40000):
                e["file_attrs"] = e.get("file_attrs", 0) | 0x40000
                e["has_ea"] = True
        # H3: non-resident reparse tag + target. The reparse buffer lives in the file's OWN (home)
        # backing; source from `rem` (home stream) to dodge the file_id-collision wrong-target bug,
        # falling back to the resolved rec, then the 0x540 index for the tag. v3.14: target recovered;
        # v3.7-v3.10: backing is mirror-only so target stays empty (correct).
        if e.get("has_reparse"):
            rsrc = None
            if rem is not None and len(rem) >= 8 and (rem[6] or rem[7]):
                rsrc = rem
            elif rec is not None and len(rec) >= 8:
                rsrc = rec
            if rsrc is not None:
                if rsrc[6]:
                    e["reparse_tag_value"] = rsrc[6]
                if rsrc[7]:
                    e["reparse_target"] = rsrc[7]
            if not e.get("reparse_tag_value"):
                _ft = reparse_idx.get((home, fid), 0) or reparse_idx.get((P, fid), 0)
                if (_ft >> 31) & 1:
                    e["reparse_tag_value"] = _ft
        hl_groups.setdefault(sig, []).append(e)
    for _sig, entries_list in hl_groups.items():
        count = len(entries_list)
        # F1: when a file has >1 name, record the full set of sibling paths so a
        # consumer can enumerate every name of the object (like `fsutil hardlink list`).
        names = sorted(e["path"] for e in entries_list) if count > 1 else None
        for e in entries_list:
            e["hard_link_count"] = count
            if names:
                e["hard_link_names"] = names

    return results

def _volume_times(f, ps, cs, tr, obj_map):
    """(vol_create, vol_modify) FILETIMEs from the volume-info object (OID 0x500,
    key 0x0520, +0x90/+0xA0). Returns (0, 0) if unavailable. Used by --timestomp
    for the PRE_FORMAT / FUTURE intrinsic signals."""
    if 0x500 not in obj_map:
        return (0, 0)
    try:
        for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x500]):
            if le16(kd, 0) == 0x0520 and len(vd) >= 0xA8:
                return (le64(vd, 0x90), le64(vd, 0xA0))
    except Exception:
        pass
    return (0, 0)

def annotate_timestomp(results, f, ps, cs, tr, obj_map, margin=TS_MARGIN_100NS):
    """Attach intrinsic timestomp flags to each non-directory record in place
    (F2). Pure $SI heuristic; corroborate with refsanalysis `timestomp` (USN)."""
    vc, vm = _volume_times(f, ps, cs, tr, obj_map)
    for r in results:
        if r.get("is_dir"):
            continue
        flags = timestomp_intrinsic_flags(
            r.get("create_time", 0), r.get("modify_time", 0),
            r.get("change_time", 0), r.get("access_time", 0),
            vc, vm, margin)
        if flags:
            r["timestomp_flags"] = "|".join(flags)
    return results

# ─── Output formatters ───────────────────────────────────────────────
# H3 (2026-06-29): GroupSid, AllocatedSize, ReparseTag added immediately BEFORE RefsVersion
# (kept last) so column indices 0..27 are unchanged — every existing positional CSV consumer
# (RefsVersion via [-1], SnapshotCount@26) keeps working with no edit.
# N4 (2026-07-03): RecoveredChild added the same way (before RefsVersion, still [-1]) — it carries the
# recovered type-0x30 child name of a deleted-directory orphan (find_orphan_objects/chkp-diff/cow), which
# was captured but previously dropped from every output; empty for all non-orphan rows.
CSV_COLUMNS = [
    "OID", "ParentOID", "ParentPath", "FileName", "Extension",
    "FileSize", "IsDirectory", "IsDeleted", "DeletionSource", "IsResident",
    "Created", "Modified", "Changed", "Accessed",
    "FileAttributes", "SecurityId", "OwnerSid", "USN",
    "HasAds", "AdsNames", "IsEncrypted", "IsCompressed",
    "HasIntegrity", "HasEA", "ReparseTarget",
    "HardLinkCount", "SnapshotCount", "TimestompFlags",
    "GroupSid", "AllocatedSize", "ReparseTag", "RecoveredChild",
    "HardLinkNames", "FileId", "HomeOid", "IsSparse", "InternalFlags", "RefsVersion",
]

def _sid_display(sid):
    """Render a SID as 'Name (SID)', or the bare SID if no friendly name, or '' if empty.
    Matches the long-standing OwnerSid rendering; reused for GroupSid."""
    if not sid:
        return ""
    nm = sid_name(sid)
    return f"{nm} ({sid})" if nm else sid

def _full_path(r):
    """ParentPath/FileName as one column (F11). '.' or empty parent → just the name."""
    pp = r.get("parent_path", "")
    return f"{pp}/{r['name']}" if pp and pp != "." else r["name"]

def emit_csv(results, sd_map, version_str, out, full_path=False):
    writer = csv.writer(out)
    # F11: --full-path-column appends FullPath at the END so the default 0..RefsVersion indices stay stable.
    writer.writerow(CSV_COLUMNS + (["FullPath"] if full_path else []))
    for r in results:
        oid = r["oid"]
        sec_id = r.get("security_id", 0)
        owner_sid, group_sid = sd_map.get(sec_id, ("", "")) if sec_id else ("", "")
        rtag = r.get("reparse_tag_value", 0)

        row = [
            f"0x{oid:x}" if oid else "",
            f"0x{r['parent_oid']:x}" if r.get("parent_oid") else "",
            r.get("parent_path", ""),
            r["name"],
            ext_from_name(r["name"]),
            r.get("file_size", 0),
            r["is_dir"],
            r.get("is_deleted", False),
            r.get("deletion_source", ""),
            r.get("is_resident", False),
            filetime_to_iso(r.get("create_time", 0)),
            filetime_to_iso(r.get("modify_time", 0)),
            filetime_to_iso(r.get("change_time", 0)),
            filetime_to_iso(r.get("access_time", 0)),
            attrs_to_str(r.get("file_attrs", 0)),
            sec_id if sec_id else "",
            _sid_display(owner_sid),
            r.get("usn", 0) if r.get("usn", 0) else "",
            r.get("has_ads", False),
            r.get("ads_names", ""),
            r.get("is_encrypted", False),
            r.get("is_compressed", False),
            r.get("has_integrity", False),
            r.get("has_ea", False),
            r.get("reparse_target", ""),
            r.get("hard_link_count", 1) if not r.get("is_resident") and not r.get("is_dir") else "",
            r.get("snapshot_count", 0) if r.get("snapshot_count", 0) > 0 else "",
            r.get("timestomp_flags", ""),
            _sid_display(group_sid),
            "" if r.get("allocated_size") is None else r.get("allocated_size"),
            reparse_tag_str(rtag) if rtag else "",
            r.get("recovered_child", ""),
            # Q5: hard-link names (;-joined), same gate as HardLinkCount (non-resident files only).
            ";".join(r.get("hard_link_names") or []) if not r.get("is_resident") and not r.get("is_dir") else "",
            # Q2: file_id (low 64 of the USN 128-bit FileID) + home_oid (high 64) — makes files<->usn joinable.
            f"0x{r['file_id']:x}" if r.get("file_id") else "",
            f"0x{r['home_oid']:x}" if r.get("home_oid") else "",
            # F5: sparse from $SI FileAttributes bit FILE_ATTRIBUTE_SPARSE_FILE (0x200) — the definitive signal.
            bool(r.get("file_attrs", 0) & 0x200),
            # Q3: $SI InternalFlags (only confidently-named bits, e.g. 0x01 DeleteDisposition) — blank otherwise.
            internal_flags_str(r.get("internal_flags", 0)),
            version_str,
        ]
        if full_path:
            row.append(_full_path(r))
        writer.writerow(row)

def emit_body(results, out):
    for r in results:
        md5 = "0"
        # Q10: Sleuthkit convention — mark deleted entries so mactime users can filter on " (deleted)".
        name = r["path"] + (" (deleted)" if r.get("is_deleted") else "")
        # Q10: a non-resident file has no own OID; use its file_id as the inode so mactime groups the file's
        # hard-link names (which share one file_id) as a single object instead of many inode-0 rows.
        if r["oid"]:
            inode = f"0x{r['oid']:x}"
        elif r.get("file_id"):
            inode = f"0x{r['file_id']:x}"
        else:
            inode = "0"
        mode = attrs_to_mode(r.get("file_attrs", 0), r["is_dir"])
        size = str(r.get("file_size", 0))
        atime = str(filetime_to_unix(r.get("access_time", 0)))
        mtime = str(filetime_to_unix(r.get("modify_time", 0)))
        ctime = str(filetime_to_unix(r.get("change_time", 0)))
        crtime = str(filetime_to_unix(r.get("create_time", 0)))
        out.write(f"{md5}|{name}|{inode}|{mode}|0|0|{size}|{atime}|{mtime}|{ctime}|{crtime}\n")

def _sid_display_or_none(sid):
    """Like _sid_display but returns None (not '') for an empty SID — JSON convention."""
    if not sid:
        return None
    nm = sid_name(sid)
    return f"{nm} ({sid})" if nm else sid

def _build_record(r, sd_map, version_str):
    oid = r["oid"]
    sec_id = r.get("security_id", 0)
    owner_sid, group_sid = sd_map.get(sec_id, ("", "")) if sec_id else ("", "")
    rtag = r.get("reparse_tag_value", 0)
    return {
        "oid": f"0x{oid:x}" if oid else None,
        "parent_oid": f"0x{r['parent_oid']:x}" if r.get("parent_oid") else None,
        "parent_path": r.get("parent_path", ""),
        "file_name": r["name"],
        "extension": ext_from_name(r["name"]),
        "file_size": r.get("file_size", 0),
        "is_directory": r["is_dir"],
        "is_deleted": r.get("is_deleted", False),
        "deletion_source": r.get("deletion_source", ""),
        "is_resident": r.get("is_resident", False),
        "created": filetime_to_iso(r.get("create_time", 0)),
        "modified": filetime_to_iso(r.get("modify_time", 0)),
        "changed": filetime_to_iso(r.get("change_time", 0)),
        "accessed": filetime_to_iso(r.get("access_time", 0)),
        "file_attributes": attrs_to_str(r.get("file_attrs", 0)),
        "security_id": sec_id if sec_id else None,
        "owner_sid": _sid_display_or_none(owner_sid),
        "usn": r.get("usn", 0) or None,
        "has_ads": r.get("has_ads", False),
        "ads_names": r.get("ads_names", "") or None,
        "is_encrypted": r.get("is_encrypted", False),
        "is_compressed": r.get("is_compressed", False),
        "has_integrity": r.get("has_integrity", False),
        "has_ea": r.get("has_ea", False),
        "reparse_target": r.get("reparse_target", "") or None,
        "hard_link_count": r.get("hard_link_count", 1) if not r.get("is_resident") and not r.get("is_dir") else None,
        "hard_link_names": r.get("hard_link_names") or None,
        "snapshot_count": r.get("snapshot_count", 0) if r.get("snapshot_count", 0) > 0 else None,
        "timestomp_flags": r.get("timestomp_flags", "") or None,
        "group_sid": _sid_display_or_none(group_sid),
        "allocated_size": r.get("allocated_size"),
        "reparse_tag": reparse_tag_str(rtag) if rtag else None,
        "recovered_child": r.get("recovered_child", "") or None,
        # Q2: join keys — file_id (low 64) + home_oid (high 64) reconstruct the USN 128-bit FileID.
        "file_id": f"0x{r['file_id']:x}" if r.get("file_id") else None,
        "home_oid": f"0x{r['home_oid']:x}" if r.get("home_oid") else None,
        # F5: FILE_ATTRIBUTE_SPARSE_FILE (0x200) from $SI FileAttributes.
        "is_sparse": bool(r.get("file_attrs", 0) & 0x200),
        # Q3: $SI InternalFlags (confidently-named bits only, e.g. DeleteDisposition).
        "internal_flags": internal_flags_str(r.get("internal_flags", 0)) or None,
        "refs_version": version_str,
    }

def emit_json(results, sd_map, version_str, out):
    records = [_build_record(r, sd_map, version_str) for r in results]
    json.dump(records, out, indent=2, ensure_ascii=False)
    out.write("\n")

def emit_jsonl(results, sd_map, version_str, out):
    for r in results:
        out.write(json.dumps(_build_record(r, sd_map, version_str), ensure_ascii=False))
        out.write("\n")

# ─── Summary helpers ──────────────────────────────────────────────────
_ROOT_LABELS = [
    "Object ID Table", "Medium Allocator", "Container Allocator",
    "Schema Table", "Parent-Child Table", "Object ID Table dup",
    "Block RefCount", "Container Table", "Container Table dup",
    "Schema Table dup", "Container Index", "Integrity State",
    "Small Allocator",
]

def _human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"

def _guid_str(b):
    if len(b) < 16: return b.hex()
    return f"{le32(b,0):08x}-{le16(b,4):04x}-{le16(b,6):04x}-{b[8:10].hex()}-{b[10:16].hex()}"

def _hash_page(f, offset, size):
    f.seek(offset); return hashlib.sha256(f.read(size)).hexdigest()

def _hash_image(path, log_fn=None):
    size = os.path.getsize(path)
    if size > 50 * 1024**3 and log_fn:
        est_min = size / (1.5 * 1024**3)
        log_fn(f"  Warning: image is {_human_size(size)}, hash will take ~{est_min:.0f} minutes")
    h = hashlib.sha256()
    done = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(64 * 1024 * 1024)
            if not chunk: break
            h.update(chunk)
            done += len(chunk)
            if log_fn and size > 0:
                pct = 100.0 * done / size
                log_fn(f"\r  Hashing: {pct:.0f}%")
    return h.hexdigest()

def cmd_fastsummary(f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns,
                    image_path, plus_mode=False, json_mode=False, hash_image=False, log_fn=None):
    hs = _human_size

    # VBR fields + hash
    f.seek(ps); bs = f.read(512)
    chk_type = le16(bs, 0x2A)
    vol_serial = le64(bs, 0x38)   # F11: volume serial number (VBR 0x38); boot shows it, triage summary didn't
    total_sectors = le64(bs, 0x18)
    bpc = le64(bs, 0x40) if le64(bs, 0x40) != 0 else 0x4000000
    vbr_sha = hashlib.sha256(bs).hexdigest()

    # SUPB + hash
    supb_off = ps + SUPB_LCN * cs
    f.seek(supb_off); supb_data = f.read(cs)
    vol_guid = supb_data[0x50:0x60] if supb_data[:4] == b"SUPB" else b"\x00" * 16
    supb_sha = hashlib.sha256(supb_data).hexdigest()

    # Checkpoint info + hash
    best_vc = 0; best_flags = 0; chkp_sha = ""
    for cl in chkp_lcns:
        try:
            vc, flags, _ = parse_chkp(f, ps, cs, cl)
            if vc >= best_vc:
                best_vc = vc; best_flags = flags
                chkp_sha = _hash_page(f, ps + cl * cs, cs)
        except Exception: pass

    # Root table row counts
    root_counts = {}
    # E3 fix: the real-addressed roots are {7,8,12} (module-level _CT_ROOT_INDICES) — NOT {7,8,10,11}.
    # The old local set read roots 10/11 without translation and root 12 WITH translation, i.e. 3 of
    # 13 root counts from wrong locations. (chkp.md / container_table.md / FS_CHKP_016/017/021, RD.)
    for idx in range(min(13, len(roots))):
        vlcns = roots[idx]
        if not vlcns: root_counts[idx] = 0; continue
        use_tr = None if idx in _CT_ROOT_INDICES else tr
        try: root_counts[idx] = len(list(walk_bplus(f, ps, cs, use_tr, vlcns)))
        except Exception: root_counts[idx] = 0

    # Volume metadata from OID 0x500
    vol_label = ""; vol_detail = {}
    if 0x500 in obj_map:
        try:
            for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x500]):
                kt = le16(kd, 0) if len(kd) >= 2 else 0
                if kt == 0x0510 and len(vd) >= 2:
                    vol_label = vd.decode("utf-16-le", errors="replace").rstrip("\x00")
                elif kt == 0x0520 and len(vd) >= 0xA8:
                    vol_detail["vol_major"] = vd[0x80]
                    vol_detail["vol_minor"] = vd[0x81]
                    vol_detail["drv_major"] = vd[0x82]
                    vol_detail["drv_minor"] = vd[0x83]
                    vol_detail["vol_create_time"] = le64(vd, 0x90)
                    vol_detail["vol_modify_time"] = le64(vd, 0xA0)
        except Exception: pass

    checksum_types = {0: "None", 2: "CRC64", 4: "SHA-256"}
    volume_bytes = total_sectors * 512

    summary = {
        "tool": PROG, "summary_mode": "fastsummary-plus" if plus_mode else "fastsummary",
        "image": os.path.basename(image_path),
        "image_size": os.path.getsize(image_path),
        "refs_version": f"{vmaj}.{vmin}",
        "volume_guid": _guid_str(vol_guid),
        "volume_serial": f"0x{vol_serial:016x}",
        "volume_label": vol_label or "(none)",
        "volume_size": hs(volume_bytes), "volume_size_bytes": volume_bytes,
        "cluster_size": cs, "container_size": bpc,
        "checksum": checksum_types.get(chk_type, f"Unknown({chk_type})"),
        "checkpoint_vc": best_vc, "checkpoint_flags": f"0x{best_flags:x}",
        "containers_mapped": root_counts.get(7, 0),
        "objects": len(obj_map),
        "vbr_sha256": vbr_sha, "supb_sha256": supb_sha, "chkp_sha256": chkp_sha,
        "root_table_rows": {_ROOT_LABELS[i]: root_counts.get(i, 0)
                            for i in range(min(13, len(roots)))},
    }

    if plus_mode:
        if vol_detail:
            summary["volume_version"] = f"{vol_detail.get('vol_major','?')}.{vol_detail.get('vol_minor','?')}"
            summary["driver_version"] = f"{vol_detail.get('drv_major','?')}.{vol_detail.get('drv_minor','?')}"
            summary["volume_create_time"] = filetime_to_iso(vol_detail.get("vol_create_time", 0))
            summary["volume_modify_time"] = filetime_to_iso(vol_detail.get("vol_modify_time", 0))

        # Feature E — upgrade detection. A volume was UPGRADED across versions iff it runs v3.10+
        # without the native-format bit (CHKP+0x78 & 0x080), OR the format-time version (immutable
        # VBR/$VolInfo) differs from the current driver version. (Verified: native v3.14=0x682 bit set;
        # upgraded v3.4→v3.14=0x602 bit clear; native v3.4=0x002 bit clear but minor<10.)
        native_bit = bool(best_flags & 0x080)
        vol_mn = vol_detail.get("vol_minor") if vol_detail else None
        drv_mn = vol_detail.get("drv_minor") if vol_detail else None
        reasons = []
        from_ver = None
        if vmin >= 10 and not native_bit:
            # native bit is set only on natively-formatted v3.10+, so its absence ⇒ formatted pre-v3.10.
            reasons.append("CHKP native-format bit 0x080 is clear on a v3.10+ volume")
            from_ver = "pre-v3.10 (v3.4–v3.9)"
        if isinstance(vol_mn, int) and isinstance(drv_mn, int) and vol_mn != drv_mn:
            # the $VolInfo version stamp usually tracks the current driver after upgrade, but if it lags,
            # it gives the exact original minor.
            reasons.append("format-time v3.%d ≠ driver v3.%d ($VOLUME_INFORMATION stamp)" % (vol_mn, drv_mn))
            from_ver = "v3.%d" % min(vol_mn, drv_mn)
        if reasons:
            summary["volume_state"] = "UPGRADED"
            summary["upgrade_evidence"] = reasons
            summary["upgraded_from"] = from_ver or "an earlier version"
        else:
            summary["volume_state"] = "NATIVE v%s" % summary["refs_version"]

        # Security descriptor count
        sec_count = 0
        if 0x530 in obj_map:
            try: sec_count = len(list(walk_bplus(f, ps, cs, tr, obj_map[0x530])))
            except Exception: pass
        summary["security_descriptors"] = sec_count

        # Reparse index
        reparse_count = 0
        if 0x540 in obj_map:
            try: reparse_count = len(list(walk_bplus(f, ps, cs, tr, obj_map[0x540])))
            except Exception: pass
        summary["reparse_index_entries"] = reparse_count

        # Trash table
        trash_count = 0
        if 0xD in obj_map:
            try: trash_count = len(list(walk_bplus(f, ps, cs, tr, obj_map[0xD])))
            except Exception: pass
        summary["trash_table_entries"] = trash_count

        # Container utilization
        ct_size = root_counts.get(7, 0)
        if tr and ct_size > 0:
            used = sum(1 for c in tr.map.values() if c > 0)
            summary["containers_used"] = used
            summary["containers_free"] = ct_size - used
            summary["utilization_pct"] = round(100.0 * used / ct_size, 1)
            summary["free_space_est"] = hs((ct_size - used) * bpc)

        # FS Metadata directory (OID 0x520)
        fs_meta = {"rows": 0, "children": [], "usn_journal": False}
        if 0x520 in obj_map:
            try:
                for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x520]):
                    fs_meta["rows"] += 1
                    if len(kd) >= 4 and le16(kd, 0) == 0x30:
                        try: name = kd[4:].decode("utf-16-le").rstrip("\x00")
                        except Exception: name = "(decode error)"
                        if name == "Change Journal": fs_meta["usn_journal"] = True
                        fs_meta["children"].append(name)
            except Exception: pass
        summary["fs_metadata"] = fs_meta
        # UsnJournalId (volume-constant journal epoch) is injected by the full `summary` path from the
        # walk (each file's $SI val+0x70 carries it; the $Max stream is unreliable — often no extents).

    if hash_image:
        summary["image_sha256"] = _hash_image(image_path, log_fn)

    # E11: surface unmapped-container misses (0 on well-formed volumes; non-zero => corrupt/truncated
    # container table, so some rows were read as identity and may be missing). stderr, not the summary.
    if tr and getattr(tr, "misses", 0):
        print(f"[{PROG}] WARNING: {tr.misses} VLCN(s) had no container mapping — output may be "
              f"incomplete (corrupt/truncated container table).", file=sys.stderr)
    return summary

def _print_fastsummary(summary, plus_mode=False):
    hs = _human_size
    w = 78
    print("=" * w)
    print(f"ReFS Volume {'Fast ' if not plus_mode else 'Fast Extended '}Summary")
    print("=" * w)
    print(f"  Image:              {summary['image']}")
    print(f"  Image size:         {hs(summary['image_size'])}")
    print(f"  ReFS version:       {summary['refs_version']}")
    print(f"  Volume GUID:        {summary['volume_guid']}")
    print(f"  Volume serial:      {summary.get('volume_serial', '')}")
    print(f"  Volume label:       {summary['volume_label']}")
    print(f"  Volume size:        {summary['volume_size']}")
    print(f"  Cluster size:       0x{summary['cluster_size']:x} ({hs(summary['cluster_size'])})")
    print(f"  Container size:     0x{summary['container_size']:x} ({hs(summary['container_size'])})")
    print(f"  Checksum:           {summary['checksum']}")
    print()
    print("-" * w)
    print("Hashes")
    print("-" * w)
    print(f"  VBR SHA-256:        {summary['vbr_sha256']}")
    print(f"  SUPB SHA-256:       {summary['supb_sha256']}")
    print(f"  CHKP SHA-256:       {summary['chkp_sha256']}")
    if "image_sha256" in summary:
        print(f"  Image SHA-256:      {summary['image_sha256']}")
    print()
    print("-" * w)
    print("Checkpoint")
    print("-" * w)
    print(f"  Virtual clock:      {summary['checkpoint_vc']}")
    print(f"  Flags:              {summary['checkpoint_flags']}")
    try:
        for _line in chkp_flags_decoded(int(str(summary['checkpoint_flags']), 16)):
            print(f"                        · {_line}")
    except (ValueError, TypeError):
        pass
    print(f"  Objects:            {summary['objects']}")
    print(f"  Containers mapped:  {summary['containers_mapped']}")
    print()
    print("-" * w)
    print("Global Root Tables")
    print("-" * w)
    for name, count in summary["root_table_rows"].items():
        print(f"  {name:<28} {count:>6} rows")

    if plus_mode:
        print()
        print("-" * w)
        print("Volume Detail")
        print("-" * w)
        if "volume_version" in summary:
            print(f"  Volume version:     {summary['volume_version']}")
            print(f"  Driver version:     {summary['driver_version']}")
            print(f"  Volume created:     {summary['volume_create_time']}")
            print(f"  Volume modified:    {summary['volume_modify_time']}")
        vstate = summary.get("volume_state", "")
        if vstate == "UPGRADED":
            print(f"  Volume state:       ⚠ APPEARS UPGRADED (formatted {summary.get('upgraded_from','?')}, now running v{summary['refs_version']})")
            for r in summary.get("upgrade_evidence", []):
                print(f"                        • {r}")
        elif vstate:
            print(f"  Volume state:       {vstate}")
        print(f"  Security descs:     {summary.get('security_descriptors', 0)}")
        print(f"  Reparse index:      {summary.get('reparse_index_entries', 0)} entries")
        print(f"  Trash table:        {summary.get('trash_table_entries', 0)} entries")
        if "containers_used" in summary:
            print(f"  Containers used:    {summary['containers_used']} / {summary['containers_mapped']}"
                  f" ({summary['utilization_pct']}%)")
            print(f"  Free space (est):   {summary['free_space_est']}")
        fm = summary.get("fs_metadata", {})
        print(f"  FS Metadata rows:   {fm.get('rows', 0)}")
        print(f"  USN Journal:        {'Active' if fm.get('usn_journal') else 'Inactive'}")
        if "usn_journal_id" in summary:
            print(f"  USN Journal ID:     0x{summary['usn_journal_id']:016x}")

    print()
    if plus_mode:
        print(f"For complete file statistics, use the `summary` subcommand (full directory walk)")

def _print_summary(summary, fast_data, plus_mode=False):
    _print_fastsummary(fast_data, plus_mode=plus_mode)
    w = 78
    print()
    print("-" * w)
    print("File System Content (from directory walk)")
    print("-" * w)
    print(f"  Directories:        {summary['directories']}")
    print(f"  Files:              {summary['files']} ({summary['resident_files']} resident)")
    print(f"  Total file size:    {summary['total_file_size']}")
    print(f"  Oldest timestamp:   {summary['oldest_timestamp']}")
    print(f"  Newest timestamp:   {summary['newest_timestamp']}")
    if plus_mode:
        print(f"  Encrypted files:    {summary.get('encrypted_files', 0)}")
        print(f"  Integrity files:    {summary.get('integrity_files', 0)}")
        print(f"  Compressed files:   {summary.get('compressed_files', 0)}")
        print(f"  Hard links (extra): {summary.get('hardlink_extra', 0)}")
        print(f"  Snapshots:          {summary.get('snapshots', 0)}")
        print(f"  ADS entries:        {summary.get('ads_entries', 0)}")
    print()
    if plus_mode:
        print(f"Tip: the `fastsummary` subcommand gives quick volume metadata without a directory walk")

# ─── OID detail + search ─────────────────────────────────────────────
_ATTR_NAMES = {
    0x10: "$STANDARD_INFORMATION", 0x20: "Reverse Index", 0x30: "Directory Entry",
    0x40: "Extent Descriptor", 0x50: "$VOLUME_INFORMATION", 0x60: "Reparse Index",
    0x70: "$REPARSE_POINT (v1)", 0x80: "$DATA",
    # type 0x90 is OVERLOADED by owning-object schema: $I30_INDEX when embedded in dir entries (#278),
    # but a table payload at the top level of system objects (e.g. the Upcase table on OID 0x7). NOT $SI.
    0x90: "$I30_INDEX / table payload (schema-dependent)",
    0xA0: "$INDEX_ROOT", 0xB0: "$SNAPSHOT/ADS", 0xC0: "$REPARSE_POINT (v2)",
    0xD0: "$EA_INFORMATION", 0xE0: "$EA/WSL", 0xF0: "$LOGGED_UTILITY_STREAM",
    0x100: "$EFS",  # embedded EFS-metadata sub-record ("$CBW4" in prior work is a fabrication — CBW4.md/E35)
}

def _parse_si_full(vd, vmaj, vmin):
    """Parse full $SI from a type 0x10 attribute value. vd starts at the SI base. (Only type 0x10 is $SI —
    type 0x90 is $I30_INDEX / a table payload, never a $SI; see #426.)"""
    si = {}
    if len(vd) < 0x28:
        return si
    # SI base is at vd+0x28 for type 0x10 in an OID's own B+-tree
    # The value starts with 0x28 bytes of attribute header, then SI fields
    base = 0x28
    if len(vd) < base + 0x58:
        return si
    si["create_time"] = filetime_to_iso(le64(vd, base + 0x00))
    si["modify_time"] = filetime_to_iso(le64(vd, base + 0x08))
    si["change_time"] = filetime_to_iso(le64(vd, base + 0x10))
    si["access_time"] = filetime_to_iso(le64(vd, base + 0x18))
    si["file_attrs"] = f"0x{le32(vd, base + 0x20):08x} ({attrs_to_str(le32(vd, base + 0x20))})"
    si["internal_flags"] = f"0x{le32(vd, base + 0x24):02x}"
    si["security_id"] = f"0x{le64(vd, base + 0x28):x}"
    si["si_field_0x30"] = f"0x{le64(vd, base + 0x30):x}"     # raw $SI+0x30: UNPOPULATED (0 on 0/32,629 own-rows) — NOT a USN. The file's USN is last_usn below. E30 retracted / E45.
    si["datasize"] = le64(vd, base + 0x38)   # raw $SI+0x38: 0 on own-rows; the type-0x30 index entry carries FileSize@value+0x58 / AllocSize@value+0x60 instead (E26/E30/E45)
    # 0x40/0x48: USN change-journal fields — the real per-file → journal link (E27)
    si["last_usn"] = f"0x{le64(vd, base + 0x40):x}"          # file's last USN = virtual $UsnJrnl:$J byte offset (proven 14/14, 480/480 record-name matches)
    si["usn_journal_id"] = le64(vd, base + 0x48)             # USN journal instance id (one per volume)
    if len(vd) >= base + 0x58:
        si["packed_ea_size_or_reparse_low"] = le32(vd, base + 0x50)
        si["reparse_tag"] = f"0x{le32(vd, base + 0x54):08x}"
        rt = le32(vd, base + 0x54)
        if rt in REPARSE_TAGS:
            si["reparse_tag"] += f" ({REPARSE_TAGS[rt]})"
    is_win11 = vmin >= 7
    if is_win11 and len(vd) >= base + 0x7C:
        si["next_file_id"] = le64(vd, base + 0x58)            # directory child-creation ordinal (was "VersionRefCount")
        si["external_file_id_2"] = f"0x{le64(vd, base + 0x60):x}"
        si["external_file_id_3"] = f"0x{le64(vd, base + 0x68):x}"
        si["hard_link_count"] = le32(vd, base + 0x70)
        si["next_stream_set_id"] = f"0x{le64(vd, base + 0x74):x}"   # base 0xF000 (was "ExternalFileObjectId")
    elif not is_win11 and len(vd) >= base + 0x74:
        si["next_file_id"] = f"0x{le64(vd, base + 0x58):x}"   # v3.4 "ExternalFileId_1" = same NextFileId ordinal
        si["external_file_id_2"] = f"0x{le64(vd, base + 0x60):x}"
        si["external_file_id_3"] = f"0x{le64(vd, base + 0x68):x}"
        si["hard_link_count"] = le32(vd, base + 0x70)
    return si

def cmd_oid_detail(f, ps, cs, tr, obj_map, vmaj, vmin, target_oid, json_mode=False, log_fn=None):
    """Dump all attributes for a specific OID."""
    if target_oid not in obj_map:
        return None

    vlcns = obj_map[target_oid]
    try:
        rows = walk_bplus(f, ps, cs, tr, vlcns)
    except Exception as e:
        return {"error": str(e)}

    # Group rows by attribute type
    attrs = {}
    for kd, vd in rows:
        if len(kd) < 2:
            continue
        attr_type = le16(kd, 0)
        key_extra = kd[2:] if len(kd) > 2 else b""
        attrs.setdefault(attr_type, []).append({"key": kd, "key_extra": key_extra, "value": vd})

    result = {
        "oid": f"0x{target_oid:x}",
        "vlcns": [f"0x{v:x}" for v in vlcns],
        "attribute_count": len(rows),
        "attribute_types": sorted(attrs.keys()),
        "attributes": {},
    }

    for at in sorted(attrs.keys()):
        type_name = _ATTR_NAMES.get(at, f"Unknown(0x{at:x})")
        # C7: schema = definition code + 0x100 for EVERY type EXCEPT $SI (def 0x10 / embedded 0x90 ->
        # schema 0x190 — the one def!=embedded case). The old (at<<4)+0x100 was wrong for all types incl $DATA.
        schema_id = f"0x{(0x190 if at == 0x10 else at + 0x100):x}" if at <= 0x100 else f"0x{at:x}"
        entries = attrs[at]
        attr_info = {"type": f"0x{at:02x}", "name": type_name, "schema": schema_id, "count": len(entries), "entries": []}

        for ent in entries:
            kd, vd = ent["key"], ent["value"]
            entry_data = {"key_len": len(kd), "value_len": len(vd)}

            if at == 0x10 and len(vd) >= 0x80:   # $SI is type 0x10 only — type 0x90 is $I30_INDEX / a table payload (Upcase on OID 0x7), NOT $SI (#426; 0/215 type-0x90 rows parse as a valid $SI corpus-wide)
                entry_data["si"] = _parse_si_full(vd, vmaj, vmin)
                # Directory/object EAs live in this type-0x10 record (same embedded $EA sub-records).
                _eas, _packed = extract_eas_from_value(vd)
                if _eas is not None and sum(5 + len(e["name"]) + len(e["value"]) for e in _eas) == _packed:
                    entry_data["packed_ea_size"] = _packed
                    entry_data["extended_attributes"] = [{"name": e["name"], "length": len(e["value"]),
                                                          "value_hex": e["value"].hex()} for e in _eas]
                    _w = decode_wsl_eas(_eas)
                    if _w:
                        _wj = dict(_w)
                        if "mode" in _w: _wj["mode_decoded"] = decode_lx_mode(_w["mode"])
                        entry_data["wsl"] = _wj
            elif at == 0x30:
                try:
                    name = kd[4:].decode("utf-16-le").rstrip("\x00")
                except UnicodeDecodeError:
                    name = kd[4:].hex()
                entry_data["filename"] = name
                if len(vd) <= NON_RESIDENT_MAX_VALUE:
                    entry_data["storage"] = "non-resident"
                    entry_data["file_size"] = le64(vd, 0x38) if len(vd) >= 0x40 else 0
                    entry_data["file_attrs"] = f"0x{le32(vd, 0x40):08x}" if len(vd) >= 0x44 else "0x0"
                    # val+0x08 is the child's own OID only for a SUBDIRECTORY (dir-bit set). For a
                    # non-resident FILE it is the home-dir backref (a different object), not the file's
                    # OID -- files have no own OID -- so label it accordingly rather than as "child_oid".
                    if len(vd) >= 0x10:
                        if len(vd) >= 0x44 and (le32(vd, 0x40) & 0x10000000):
                            entry_data["child_oid"] = f"0x{le64(vd, 0x08):x}"
                        else:
                            entry_data["home_backref"] = f"0x{le64(vd, 0x08):x}"
                else:
                    entry_data["storage"] = "resident"
                    entry_data["value_size"] = len(vd)
            elif at == 0x40:
                # A type-0x40 row is a non-resident child's backing/stream record (same layout as the
                # resident type-0x30 value): file_size@0x58, alloc_size@0x60; the data runs live in
                # embedded sub-records at 0xA8+. The low bytes at 0x00/0x08 are descriptor/sentinel
                # header, NOT a vlcn / cluster_count (corrected 2026-06-27; cf. _parse_extents_from_type40).
                entry_data["extent_key"] = kd.hex() if len(kd) > 2 else ""
                if len(vd) >= 0x68:
                    entry_data["backing_size"] = le64(vd, 0x58)
                    entry_data["backing_alloc"] = le64(vd, 0x60)
                    entry_data["cluster_count"] = (le64(vd, 0x60) + cs - 1) // cs if le64(vd, 0x60) else 0
            elif at == 0x80:
                # $DATA sub-records
                if len(kd) > 4:
                    try:
                        stream_name = kd[4:].decode("utf-16-le").rstrip("\x00")
                        entry_data["stream_name"] = stream_name if stream_name else "(default)"
                    except UnicodeDecodeError:
                        entry_data["stream_name"] = kd[4:].hex()
                else:
                    entry_data["stream_name"] = "(default)"
                entry_data["data_size"] = len(vd)
            elif at == 0xC0:
                if len(vd) >= 4:
                    tag = le32(vd, 0)
                    entry_data["reparse_tag"] = f"0x{tag:08x}"
                    if tag in REPARSE_TAGS:
                        entry_data["reparse_tag"] += f" ({REPARSE_TAGS[tag]})"
                    entry_data["target"] = extract_inline_reparse(vd) if len(vd) > 8 else ""
            else:
                entry_data["raw_hex"] = vd[:64].hex() + ("..." if len(vd) > 64 else "")

            attr_info["entries"].append(entry_data)
        result["attributes"][f"0x{at:02x}"] = attr_info

    return result

def _print_oid_detail(detail, path=None):
    w = 78
    print("=" * w)
    print(f"OID Detail: {detail['oid']}")
    print("=" * w)
    if path:
        print(f"  Path:               {path}")
    print(f"  VLCNs:              {', '.join(detail['vlcns'])}")
    print(f"  Total rows:         {detail['attribute_count']}")
    print(f"  Attribute types:    {', '.join(f'0x{t:02x}' for t in detail['attribute_types'])}")

    for at_key, attr_info in detail["attributes"].items():
        print()
        print("-" * w)
        print(f"  Type {attr_info['type']} ({attr_info['name']}) — Schema {attr_info['schema']} — {attr_info['count']} entries")
        print("-" * w)
        for ent in attr_info["entries"]:
            if "si" in ent:
                for k, v in ent["si"].items():
                    print(f"    {k:<30} {v}")
                if "extended_attributes" in ent:
                    print(f"    {'PackedEaSize':<30} {ent['packed_ea_size']}")
                    wsl = ent.get("wsl")
                    if wsl:
                        if "mode_decoded" in wsl: print(f"    {'WSL Mode':<30} {wsl['mode_decoded']}")
                        if "uid" in wsl: print(f"    {'WSL UID':<30} {wsl['uid']}")
                        if "gid" in wsl: print(f"    {'WSL GID':<30} {wsl['gid']}")
                        if "dev" in wsl: print(f"    {'WSL Device':<30} {wsl['dev'][0]},{wsl['dev'][1]} (major,minor)")
                    for ea in ent["extended_attributes"]:
                        hexs = ea["value_hex"][:32] + ("…" if len(ea["value_hex"]) > 32 else "")
                        print(f"    EA {ea['name']:<27} {ea['length']:>4}B  {hexs}")
            elif "filename" in ent:
                print(f"    Filename:         {ent['filename']}")
                print(f"    Storage:          {ent['storage']}")
                if ent.get("child_oid"):
                    print(f"    Child OID:        {ent['child_oid']}")
                if ent.get("home_backref"):
                    print(f"    Home-dir backref: {ent['home_backref']}")
                if "file_size" in ent:
                    print(f"    File size:        {ent['file_size']} ({_human_size(ent['file_size'])})")
                if "file_attrs" in ent:
                    print(f"    File attrs:       {ent['file_attrs']}")
            elif "extent_key" in ent:
                if "backing_size" in ent:
                    print(f"    Backing record:   size {ent['backing_size']} ({_human_size(ent['backing_size'])}), "
                          f"alloc {ent['backing_alloc']} ({ent.get('cluster_count', 0)} clusters); runs in sub-records")
                else:
                    print(f"    Backing record:   value {ent['value_len']}B (no size header)")
            elif "stream_name" in ent:
                print(f"    Stream:           {ent['stream_name']}")
                print(f"    Data size:        {ent['data_size']} bytes")
            elif "reparse_tag" in ent:
                print(f"    Reparse tag:      {ent['reparse_tag']}")
                if ent.get("target"):
                    print(f"    Target:           {ent['target']}")
            else:
                print(f"    Key: {ent['key_len']}B  Value: {ent['value_len']}B")
                if ent.get("raw_hex"):
                    print(f"    Hex:              {ent['raw_hex']}")


def _print_file_detail(r, sd_map, version_str, raw_value=None):
    """Labeled detail view for one FILE resolved by path (F6). Mirrors the `files` field set,
    plus (from raw_value, when resident) Extended Attributes / WSL Linux metadata / internal flags."""
    w = 78
    print("=" * w)
    print(f"File Detail: {r.get('path', '')}")
    print("=" * w)
    oid = r.get("oid", 0)
    sec = r.get("security_id", 0)
    owner, group = sd_map.get(sec, ("", "")) if sec else ("", "")
    fa = r.get("file_attrs", 0)
    al = r.get("allocated_size")
    rtag = r.get("reparse_tag_value", 0)
    # EAs (resident value or non-resident backing). Extract once: drives both the "EA" flag (authoritative
    # via the $EA_INFORMATION sub-record — the file_attrs 0x40000 bit is NOT set on the non-resident
    # type-0x30 pointer) and the detail block below.
    _eas, _packed = extract_eas_from_value(raw_value) if raw_value is not None else (None, None)
    _has_ea = _eas is not None
    print(f"  OID:                {('0x%x' % oid) if oid else '(resident/non-resident file — no own OID)'}")
    print(f"  Parent OID:         {('0x%x' % r['parent_oid']) if r.get('parent_oid') else ''}")
    print(f"  Parent path:        {r.get('parent_path', '')}")
    print(f"  Name:               {r.get('name', '')}")
    print(f"  Extension:          {ext_from_name(r.get('name', ''))}")
    print(f"  Is directory:       {r.get('is_dir', False)}")
    print(f"  Is resident:        {r.get('is_resident', False)}")
    if r.get("is_deleted"):
        print(f"  Is deleted:         True ({r.get('deletion_source', '')})")
    print(f"  File size:          {r.get('file_size', 0)} ({_human_size(r.get('file_size', 0))})")
    print(f"  Allocated size:     {'' if al is None else f'{al} ({_human_size(al)})'}")
    print(f"  Created:            {filetime_to_iso(r.get('create_time', 0))}")
    print(f"  Modified:           {filetime_to_iso(r.get('modify_time', 0))}")
    print(f"  Changed:            {filetime_to_iso(r.get('change_time', 0))}")
    print(f"  Accessed:           {filetime_to_iso(r.get('access_time', 0))}")
    print(f"  File attributes:    0x{fa:08x} ({attrs_to_str(fa)})")
    print(f"  Security ID:        {sec if sec else ''}")
    print(f"  Owner SID:          {_sid_display(owner)}")
    print(f"  Group SID:          {_sid_display(group)}")
    print(f"  USN:                {r.get('usn', 0) or ''}")
    if r.get("has_ads"):
        _adsn = [n for n in str(r.get("ads_names", "")).split(";") if n]
        _pp = r.get("path") or r.get("name")
        print(f"  Alternate streams:  {'; '.join(_adsn)}")
        for _nm in _adsn:
            print(f"                        read one:  export ads \"{_pp}:{_nm}\"")
    flags = [n for n, k in (("Encrypted", "is_encrypted"), ("Compressed", "is_compressed"),
                            ("IntegrityStream", "has_integrity")) if r.get(k)]
    if _has_ea or r.get("has_ea"):
        flags.append("EA")
    if flags:
        print(f"  Flags:              {', '.join(flags)}")
    if r.get("reparse_target"):
        print(f"  Reparse target:     {r['reparse_target']}")
    if rtag:
        print(f"  Reparse tag:        {reparse_tag_str(rtag)}")
    if not r.get("is_resident") and not r.get("is_dir"):
        print(f"  Hard-link count:    {r.get('hard_link_count', 1)}")
        if r.get("hard_link_names"):
            for nm in r["hard_link_names"]:
                print(f"                        {nm}")
    if r.get("snapshot_count", 0) > 0:
        print(f"  Snapshot count:     {r['snapshot_count']}   (preview: snapshots --file {r['name']} --show · extract: export snapshots DIR --file {r['name']})")
    if r.get("timestomp_flags"):
        print(f"  Timestomp flags:    {r['timestomp_flags']}")
    ifl = internal_flags_str(r.get("internal_flags", 0))
    if ifl:
        print(f"  Internal flags:     {ifl}")
    # Extended Attributes + WSL/Linux metadata. PackedEaSize from the $EA_INFORMATION sub-record
    # (authoritative). Only the four driver-recognised $LX EAs are decoded; all other EA values are
    # shown name+size+raw-hex only. (_eas/_packed extracted near the top.)
    if raw_value is not None:
        eas, packed = _eas, _packed
        if eas is not None:
            print(f"  PackedEaSize:       {packed}")
            # Oracle gate: only surface the parsed list/WSL when PackedEaSize == Σ(5+nameLen+valLen).
            # A mismatch means the backing was mis-resolved (file_id collision) — show nothing rather
            # than a wrong EA list (never display an unproven value).
            if sum(5 + len(e["name"]) + len(e["value"]) for e in eas) != packed:
                print(f"    (EA content could not be resolved reliably — not shown)")
            else:
                wsl = decode_wsl_eas(eas)
                if wsl:
                    print(f"  WSL/Linux metadata:")
                    if "mode" in wsl:
                        print(f"    Mode:             {decode_lx_mode(wsl['mode'])}")
                    if "uid" in wsl:
                        print(f"    UID:              {wsl['uid']}")
                    if "gid" in wsl:
                        print(f"    GID:              {wsl['gid']}")
                    if "dev" in wsl:
                        print(f"    Device:           {wsl['dev'][0]},{wsl['dev'][1]} (major,minor)")
                if eas:
                    print(f"  Extended Attributes ({len(eas)}):")
                    for ea in eas:
                        v = ea["value"]
                        hexs = v[:16].hex() + ("…" if len(v) > 16 else "")
                        print(f"    {ea['name']:<22} {len(v):>4}B  {hexs}")
    print(f"  ReFS version:       {version_str}")

def cmd_search(f, ps, cs, tr, obj_map, vmaj, vmin, pattern, regex_mode=False,
               include_deleted=False, trash_set=None, max_results=0):
    """Search for files/directories by name pattern."""
    import re
    if regex_mode:
        try:
            pat = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}
        match_fn = lambda name: pat.search(name)
    else:
        pat_lower = pattern.lower()
        match_fn = lambda name: pat_lower in name.lower()

    results = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, 100, False,
                                  trash_set or set())
    matches = []
    for r in results:
        if not match_fn(r["name"]):
            continue
        if r.get("is_deleted") and not include_deleted:
            continue
        matches.append({
            "oid": f"0x{r['oid']:x}" if r["oid"] else ("(resident)" if r.get("is_resident") else "(non-res)"),
            "parent_oid": f"0x{r['parent_oid']:x}" if r.get("parent_oid") else "",
            "type": "Dir" if r["is_dir"] else "File",
            "file_size": r.get("file_size", 0),
            "is_resident": r.get("is_resident", False),
            "path": r["path"],
            "name": r["name"],
            "is_deleted": r.get("is_deleted", False),
            # F11: the walk already carries MACB — surface Modified/Created so a name hit is time-contextualised.
            "modified": filetime_to_iso(r.get("modify_time", 0)),
            "created": filetime_to_iso(r.get("create_time", 0)),
        })
        if max_results and len(matches) >= max_results:
            break
    return matches

def _print_search(matches, pattern):
    w = 100
    if not matches:
        print(f"No matches for \"{pattern}\"")
        return
    print(f"{'OID':<12} {'Parent':<12} {'Type':<5} {'Size':>12} {'Res':>4}  {'Modified':<19}  Path")
    print(f"{'─'*11}  {'─'*11}  {'─'*4}  {'─'*12} {'─'*4}  {'─'*19}  {'─'*40}")
    for m in matches:
        size_str = _human_size(m["file_size"]) if m["file_size"] else "0"
        res = "Yes" if m["is_resident"] else "No"
        if m["type"] == "Dir":
            res = "—"
        del_mark = " [DEL]" if m.get("is_deleted") else ""
        mod = (m.get("modified") or "")[:19]
        print(f"{m['oid']:<12} {m['parent_oid']:<12} {m['type']:<5} {size_str:>12} {res:>4}  {mod:<19}  {m['path']}{del_mark}")
    print(f"\n{len(matches)} matches. Use --oid <OID> for full detail.")

# ─── Bootstrap ────────────────────────────────────────────────────────
def bootstrap(image_path, partition_start=None):
    """Bootstrap the full ReFS parsing chain.
    Returns (f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns)."""
    if partition_start is not None:
        ps = partition_start
    else:
        ps, desc = find_refs_partition(image_path)
        if ps is None:
            raise ValueError(desc)

    f = open(image_path, "rb")
    try:
        cs, vmaj, vmin, chk_algo, bpc = parse_vbr(f, ps)
        cpc = bpc // cs

        chkp_lcns = parse_supb(f, ps, cs)

        # Get newest checkpoint
        best_vc = 0; best_roots = None; best_flags = 0
        for cl in chkp_lcns:
            try:
                vc, flags, roots = parse_chkp(f, ps, cs, cl)
                if vc >= best_vc:
                    best_vc = vc; best_roots = roots; best_flags = flags
            except Exception:
                continue
        if not best_roots:
            raise ValueError("No valid checkpoint found")

        # Build container table translator — select by Table-ID 0x0B, not by root index 7 (#337)
        ct_vlcns = _select_ct_root(f, ps, cs, best_roots)
        ct_page = b""
        for l in ct_vlcns: f.seek(ps + l * cs); ct_page += f.read(cs)
        ct_map_raw = _parse_ct_page(ct_page, f, ps, cs)
        ct_map = {k: v[0] for k, v in ct_map_raw.items()}
        tr = Translator(ct_map, cpc)

        # Build object map
        ot_vlcns = best_roots[0] if len(best_roots) > 0 else []
        obj_map = build_object_map(f, ps, cs, tr, ot_vlcns)

        return f, ps, cs, tr, best_roots, obj_map, vmaj, vmin, chkp_lcns
    except Exception:
        f.close()
        raise

# ─── Main ─────────────────────────────────────────────────────────────
# forefst uses an `<image> <subcommand> [options]` CLI (mirrors refsanalysis). The default subcommand is
# `files`, so `forefst <image>` still lists files. Functions are positional subcommands; format/behaviour
# modifiers stay as --flags.
# ════════════════════════════════════════════════════════════════════════
#  Migrated forensic commands (Phase 2): usn / mlog / timeline
#  Ported VERBATIM from refsanalysis (datetime refs adapted to forefst's `import datetime`).
#  They reuse the USN/MLog parsing already defined above and bootstrap the image themselves;
#  routed via FORENSIC_HANDLERS before argparse (they use flags argparse doesn't model).
# ════════════════════════════════════════════════════════════════════════

# Import-alias shims: the ported commands reference refsanalysis's `_forefst_*`/`_validate_image`
# aliases for forefst's own functions. Define them so the verbatim-copied bodies resolve identically
# (without these, e.g. cmd_deleted/cmd_integrity's `_forefst_parse_chkp` NameError'd → 0 checkpoints).
_validate_image = validate_image
_forefst_parse_vbr = parse_vbr
_forefst_parse_supb = parse_supb
_forefst_parse_chkp = parse_chkp

def die(msg):
    print(f"{PROG}: error: {msg}", file=sys.stderr)
    sys.exit(1)

def _filetime_to_str(ft):
    if ft == 0 or ft == 0xFFFFFFFFFFFFFFFF: return "(none)"
    try:
        # integer // (not float /): float division rounds up at ~0.9999999 s, displaying a second 1 too
        # high vs filetime_to_iso's // (E12 fix). Whole-second display; format (incl. ' UTC') unchanged.
        ts = (ft - 116444736000000000) // 10000000
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, ValueError):
        return f"0x{ft:x}"

def _parse_args(remaining, flags=None, valued=None):
    flags = flags or []
    valued = valued or []
    result = {f.lstrip("-").replace("-", "_"): False for f in flags}
    result.update({v.lstrip("-").replace("-", "_"): None for v in valued})
    result["_rest"] = []
    i = 0
    while i < len(remaining):
        a = remaining[i]
        if a in flags:
            result[a.lstrip("-").replace("-", "_")] = True
        elif a in valued:
            if i + 1 >= len(remaining):
                die(f"option {a} requires a value")
            result[a.lstrip("-").replace("-", "_")] = remaining[i + 1]; i += 1
        elif a.startswith("-"):
            # reject typos / unsupported flags instead of silently treating them as a positional
            die(f"unknown option: {a}")
        else:
            result["_rest"].append(a)
        i += 1
    return result

def _int_arg(val, name, base=10):
    try:
        return int(val, base) if isinstance(val, str) else int(val)
    except (ValueError, TypeError):
        die(f"invalid value for {name}: '{val}'")

def _check_unknown_flags(remaining, known_flags, valued_flags=()):
    """Reject unrecognised -flags for the manually-parsed commands (usn/mlog), matching the rejection the
    other forensic commands get from _parse_args. A valued flag consumes the next token ONLY when it is a
    real value (does not itself start with '-') — same rule those commands use to read e.g. `--csv FILE`."""
    i = 0
    while i < len(remaining):
        a = remaining[i]
        if a in valued_flags:
            if i + 1 < len(remaining) and not remaining[i + 1].startswith("-"):
                i += 2
            else:
                i += 1
            continue
        if a.startswith("-") and a != "-" and a not in known_flags:
            die(f"unknown option: {a}")     # a bare "-" is the stdout/stdin sentinel, not an unknown flag
        i += 1

_USN_FILE_ATTR_SHORT = {
    0x0001: "R", 0x0002: "H", 0x0004: "S", 0x0010: "D",
    0x0020: "A", 0x0040: "Dev", 0x0080: "N", 0x0100: "Tmp",
    0x0200: "Sparse", 0x0400: "Reparse", 0x0800: "Compress",
    0x1000: "Offline", 0x2000: "NCI", 0x4000: "Encrypt",
    0x8000: "Integrity", 0x00020000: "NoScrub",
    0x10000000: "Dir",
}

def _usn_attrs_short(attrs):
    parts = []
    for bit, name in sorted(_USN_FILE_ATTR_SHORT.items()):
        if attrs & bit:
            parts.append(name)
    return ",".join(parts) if parts else "0x%08x" % attrs

def _usn_filetime_iso(ft):
    if ft == 0:
        return ""
    try:
        us = (ft - 116444736000000000) // 10
        if us < 0:
            return "0x%016x" % ft
        dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=us)
        return dt.strftime("%Y-%m-%dT%H:%M:%S") + ".%03dZ" % (dt.microsecond // 1000)
    except (OverflowError, OSError, ValueError):
        return "0x%016x" % ft

def _usn_filetime_short(ft):
    if ft == 0:
        return ""
    try:
        us = (ft - 116444736000000000) // 10
        if us < 0:
            return "0x%016x" % ft
        dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=us)
        return dt.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
    except (OverflowError, OSError, ValueError):
        return "0x%016x" % ft

def _usn_resolve_path(oid, oid_paths):
    if oid == 0:
        return ""
    if oid in oid_paths:
        return oid_paths[oid]
    if oid < 0x700:
        return "<system 0x%x>" % oid
    return "<oid 0x%x>" % oid

_MLOG_INFO_TEXT = """\
=== MLog Parser — Action Reference ===

ACTIONS (classified from redo opcode sequences)
──────────────────────────────────────────────────────────────────────
  CREATE      New file or directory created (OpenTable + InsertRow +
              SetParentId). The name comes from the InsertRow value.
  DELETE      File or directory deleted — the object's own table is
              destroyed (RedoDeleteTable, opcode 0x0F). A bare DeleteRow
              with no DeleteTable is NOT a deletion (see ENTRY_REMOVE).
  RENAME      Name changed in the same directory: DeleteRow of old name +
              InsertRow of new name under the SAME parent-directory OID.
  MOVE        Moved to a different directory: DeleteRow + InsertRow whose
              parent-directory OIDs DIFFER. (On v3.14 a same-dir rename
              also carries RedoReparentTable, so the parent OID — not the
              reparent opcode — is the move/rename distinguisher.)
  ENTRY_REMOVE  Lone DeleteRow with no matching InsertRow — a name-entry
              removal (e.g. the old-name half of a rename/move), NOT a
              file deletion.
  REPARENT    RedoReparentTable seen without a resolvable rename/move
              name pair.
  WRITE       File data written — typically InsertRow + SetObjectRecord
              or InsertRow + UpdateDataWithRoot.
  MODIFY      Metadata update: UpdateRow, UpdateDataWithRoot,
              SetRangeState, or SetObjectRecordPayload.
  UPDATE      Row replacement: DeleteRow + InsertRow on the same table.
  INSERT      Single InsertRow without other context.
  ALLOCATE    Space allocation or deallocation without row changes.
  STREAM_UPD  Stream-level update (UpdateStreamUserPayload).
  CONTAINER   Container table change (RedoMoveContainer / AddContainer).
  DEDUP       Data deduplication (RedoDuplicateCluster).
  EXTENT_MOD  Extent-level modification.
  OP          Unclassified opcode combination.

__REDO_OPCODES__

TIMESTAMPS
──────────────────────────────────────────────────────────────────────
  MLog records do not have a dedicated timestamp field in their
  header. Timestamps shown in --parse and --csv are extracted from
  the VALUE DATA of records that modify file metadata.

SCHEMA NAMES
──────────────────────────────────────────────────────────────────────
"""

def _gen_redo_opcode_table():
    """R4: render the REDO opcode reference from REDO_OPS_V314 so `mlog --info` cannot go stale — the old
    hand-maintained block stopped at 0x13, omitting 28 of the 44 v3.14 opcodes (MoveContainer, GhostExtents,
    the compression/dedup/encrypt ops, the 0x17 error slot). Generated the same way `op_short` is (C4)."""
    out = ["REDO OPCODES (generated from REDO_OPS_V314 — PerformRedo dispatch, E2; v3.4 uses a 0x00–0x1C subset)",
           "─" * 70]
    for op in sorted(REDO_OPS_V314):
        out.append("  0x%02X  %s" % (op, REDO_OPS_V314[op]))
    return "\n".join(out)

_MLOG_INFO_TEXT = _MLOG_INFO_TEXT.replace("__REDO_OPCODES__", _gen_redo_opcode_table())

def _redo_ops_for_version(vmin):
    """Pick the redo-opcode dispatch table for a ReFS minor version.

    v3.4 → REDO_OPS_V34 (29 ops, 0x00–0x1C). **v3.7 and up → REDO_OPS_V314.** On-disk evidence
    shows v3.7/v3.9/v3.10 all use the v3.14 opcode SUBSET — including the 0x1D–0x1F stream ops that
    are absent from v3.4 — and never emit the version-ambiguous 0x16/0x17, so V314 names them
    correctly. The previous `vmin >= 9` boundary mis-routed v3.7 to V34 and left its 0x1F records
    unresolved (78 on win1121h2test). No v3.7–v3.10 driver exists to decompile; this routing is
    RD-validated to 0 unknown opcodes across the whole corpus. (finding #330)"""
    return REDO_OPS_V314 if vmin >= 7 else REDO_OPS_V34

def _mlog_resolve_txn(txn, oid_paths):
    recs = txn["records"]
    action = classify_mlog_transaction(recs)
    # op_detail: the concrete fact that justifies the label, so the enhancement stays verifiable.
    op_detail = ""
    if action in ("MOVE", "RENAME"):
        _old = sorted(_mlog_name_entry_parents(recs, 0x02))
        _new = sorted(_mlog_name_entry_parents(recs, 0x01))
        if action == "MOVE" and _old and _new:
            op_detail = "parent 0x%x → 0x%x" % (_old[0], _new[0])
        elif action == "RENAME" and _new:
            op_detail = "same parent 0x%x" % _new[0]
    elif action == "DELETE" and any(r["opcode"] == 0x0F for r in recs):
        op_detail = "object table destroyed"
    handle_oids = {}
    for r in recs:
        if r["opcode"] == 0x00 and r["target_oid"] != 0:
            handle_oids[r["handle"]] = r["target_oid"]
        if r["target_oid"] != 0:
            handle_oids.setdefault(r["handle"], r["target_oid"])
    primary_oid = 0
    for r in recs:
        oid = r["target_oid"]
        if oid == 0:
            oid = handle_oids.get(r["handle"], 0)
        if oid >= 0x600 and primary_oid == 0:
            primary_oid = oid
    path = oid_paths.get(primary_oid, "")
    if not path and primary_oid:
        path = "OID 0x%x" % primary_oid
    fnames = [r["filename"] for r in recs if r["filename"]
              and r["filename"] != "$I30"]
    fname = fnames[0] if fnames else ""
    oid_str = "0x%x" % primary_oid if primary_oid else "system"
    if fname and fname not in path:
        label = "%s → %s" % (path, fname) if path else fname
    else:
        label = path or oid_str
    ts = 0
    for r in recs:
        if r["timestamp"] > ts:
            ts = r["timestamp"]
    return {
        "action": action, "op_detail": op_detail, "label": label, "path": path, "name": fname,
        "oid": primary_oid, "timestamp": ts, "ts_str": _filetime_str(ts),
        "plcn": txn["plcn"], "recs": recs,
        "ops_str": " ".join(r["op_short"] for r in recs),
        "handle_oids": handle_oids,
    }

def cmd_mlog(image, remaining, partition_start):
    import csv as _csv

    _check_unknown_flags(remaining,
                         {"-v", "--verbose", "--parse", "--stats", "--json", "--raw-scan", "--info"}, {"--csv"})
    verbose = "-v" in remaining or "--verbose" in remaining
    do_parse = "--parse" in remaining
    do_stats = "--stats" in remaining
    do_json = "--json" in remaining
    do_raw = "--raw-scan" in remaining
    do_info = "--info" in remaining
    csv_arg = None
    for i, a in enumerate(remaining):
        if a == "--csv":
            csv_arg = remaining[i + 1] if i + 1 < len(remaining) and not remaining[i + 1].startswith("-") else "-"
            break

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        redo_ops = _redo_ops_for_version(vmin)
        # C4/C5: redo-opcode NAMES are decompiler-verified only for v3.4 and v3.14. v3.7-v3.13 have no
        # decompiled driver and reuse the v3.14 mapping (RD-validated to 0 unknown opcodes corpus-wide,
        # finding #330 — the opcodes match, but the semantic names are inferred). Surface that (stderr,
        # so --csv/--json output is untouched).
        if 4 < vmin < 14:
            print(f"  NOTE: ReFS v{vmaj}.{vmin} redo-opcode names are inferred from the v3.14 driver "
                  f"(no decompiled driver for this build; opcodes RD-validated, names best-effort).",
                  file=sys.stderr)
        W = 78

        mlog_info = get_mlog_info(f, ps, cs, tr, obj_map)
        if mlog_info is None:
            print("Logfile Information Table (OID 0x9/0xA) not found")
            return 1

        ctrl = read_mlog_control(f, ps, cs, mlog_info)

        if do_info:
            print(_MLOG_INFO_TEXT)
            for sid in sorted(MLOG_SCHEMA_NAMES):
                print("  0x%04x  %s" % (sid, MLOG_SCHEMA_NAMES[sid]))
            print()
            return 0

        if do_parse or csv_arg is not None:
            oid_paths = build_oid_path_map(f, ps, cs, tr, obj_map)
            # Stream the log data area: extract_mlog_transactions consumes the block generator in a
            # single linear pass, so the 1 GiB of log blocks is never materialized, and the redo-record
            # list (unused on this path) is not built — this is what fixes the large-log OOM.
            txns = extract_mlog_transactions(
                scan_mlog_data_area(f, ps, cs, tr, mlog_info, ctrl), redo_ops)
            img_name = os.path.basename(image)

            if csv_arg is not None:
                ts_written = [0]
                def _write_csv(out):
                    w = _csv.writer(out)
                    w.writerow(["seq", "timestamp", "action", "path", "name", "oid",
                                "opcodes", "record_count", "plcn", "image"])
                    for i, txn in enumerate(txns, 1):
                        t = _mlog_resolve_txn(txn, oid_paths)
                        if t["ts_str"]:
                            ts_written[0] += 1
                        w.writerow([
                            i, t["ts_str"], t["action"], t["path"], t["name"],
                            "0x%x" % t["oid"] if t["oid"] else "",
                            t["ops_str"], len(t["recs"]), t["plcn"], img_name,
                        ])
                if csv_arg == "-":
                    _write_csv(sys.stdout)
                else:
                    with open(csv_arg, "w", newline="") as cf:
                        _write_csv(cf)
                    print("Wrote %d transactions to %s (%d carry a timestamp — the rest have an empty"
                          " timestamp column and do not appear in `timeline --source MLOG`)."
                          % (len(txns), csv_arg, ts_written[0]))
            else:
                print("Building OID → path map …")
                print("  %d paths resolved" % len(oid_paths))
                print()
                print("=" * W)
                print("MLog Transactions (parsed)")
                print("=" * W)
                if not txns:
                    print("  No transactions found.")
                else:
                    print("  Total transactions: %d\n" % len(txns))
                    if verbose:
                        print("  (-v: each redo record is shown as  <opcode> <name>  target_oid  @PLCN.blk+offset  "
                              "key — on disk at  ps + PLCN*cluster_size + blk*0x1000 + offset)\n")
                    action_counts = {}
                    ts_count = 0
                    for txn in txns:
                        t = _mlog_resolve_txn(txn, oid_paths)
                        action = t["action"]
                        action_counts[action] = action_counts.get(action, 0) + 1
                        if t["ts_str"]:
                            ts_count += 1
                        ts_part = "  %s" % t["ts_str"] if t["ts_str"] else ""
                        detail_part = "  (%s)" % t["op_detail"] if t["op_detail"] else ""
                        print("  [%-12s] %s%s%s" % (action, t["label"], detail_part, ts_part))
                        if verbose:
                            # -v: per-record byte-level PROOF — opcode, table OID, and the exact PLCN+offset
                            # where the record lives, so an analyst can verify any field against the raw disk.
                            for r in t["recs"]:
                                oid = r["target_oid"] or t["handle_oids"].get(r["handle"], 0)
                                key = ('  key="%s"' % r["filename"]) if r["filename"] and r["filename"] != "$I30" else ""
                                sch = MLOG_SCHEMA_NAMES.get(r["attr_schema"], "")
                                sch = "  schema=%s" % sch if sch else ""
                                print("      0x%02x %-26s target_oid=0x%-8x @PLCN %d.blk%d+0x%x%s%s"
                                      % (r["opcode"], r["op_name"], oid, r["plcn"], r.get("block", 0), r.get("rec_off", 0), key, sch))
                        else:
                            print("    %s" % t["ops_str"])
                            for r in t["recs"]:
                                if r["filename"] and r["filename"] != "$I30":
                                    oid = r["target_oid"] or t["handle_oids"].get(r["handle"], 0)
                                    oid_path = oid_paths.get(oid, "")
                                    schema_name = MLOG_SCHEMA_NAMES.get(r["attr_schema"], "")
                                    detail_parts = []
                                    if oid_path:
                                        detail_parts.append("in %s" % oid_path)
                                    if schema_name:
                                        detail_parts.append(schema_name)
                                    detail = " (%s)" % ", ".join(detail_parts) if detail_parts else ""
                                    print('      name: "%s"%s' % (r["filename"], detail))
                        print()
                    print("-" * W)
                    print("Action summary")
                    print("  File operations (what a user did):")
                    _fo = [a for a in MLOG_FILE_OPS if action_counts.get(a)]
                    for a in _fo:
                        print("    %-14s %6d" % (a, action_counts[a]))
                    if not _fo:
                        print("    (none captured in the log window)")
                    print("  Low-level / metadata records (B+-tree redo that accompanies the above):")
                    _seen = set(MLOG_FILE_OPS)
                    for a in MLOG_LOW_LEVEL + tuple(sorted(k for k in action_counts if k not in _seen and k not in MLOG_LOW_LEVEL)):
                        if action_counts.get(a):
                            print("    %-14s %6d" % (a, action_counts[a]))
                    print()
                    print("  %d of %d transactions carry an embedded timestamp; only those appear in"
                          % (ts_count, len(txns)))
                    print("  `timeline --source MLOG` (an untimestamped transaction cannot be placed on a timeline).")
            return 0

        # json / default / raw-scan iterate the blocks multiple times and display the redo records,
        # so for these paths materialize the block list and the records once.
        pages = list(scan_mlog_data_area(f, ps, cs, tr, mlog_info, ctrl))
        records = extract_redo_records(pages, redo_ops)

        if do_json:
            import json as _json
            output = {
                "version": "%d.%d" % (vmaj, vmin),
                "control": ctrl,
                "mlog_info": {k: v for k, v in (mlog_info or {}).items() if k != "page"},
                "data_area": {"total_pages": len(pages), "page_types": {}},
                "records": records,
            }
            for p in pages:
                t = p["type"]
                output["data_area"]["page_types"][t] = output["data_area"]["page_types"].get(t, 0) + 1
            print(_json.dumps(output, indent=2, default=str))
            return 0

        # Default: control + data summary + records
        print("=" * W)
        print("ReFS MLog Analysis — %s" % os.path.basename(image))
        print("ReFS v%d.%d | cluster_size=0x%x | objects=%d" % (vmaj, vmin, cs, len(obj_map)))
        print("=" * W)
        print()

        # Control area
        print("=" * W)
        print("MLog Control Area")
        print("=" * W)
        if not ctrl:
            print("  No valid MLog control page found.")
        else:
            print("  Control PLCN:      0x%x" % ctrl.get("plcn", 0))
            print("  Signature:         %s" % ctrl.get("signature", "?"))
            print("  Format magic:      0x%08x (per-volume const, NOT a CRC — E42/#343; differs after a reformat)" % ctrl.get("format_magic", 0))
            print("  Version:           %s" % ctrl.get("version", "?"))
            print("  Sector size:       0x%x" % ctrl.get("sector_size", 0))
            print("  UUID:              %s" % ctrl.get("uuid", "?"))
            seq = ctrl.get("sequence", ctrl.get("sequence_raw", "?"))
            print("  Sequence:          %s" % seq)
            print("  Write counter:     %s" % ctrl.get("write_counter", "?"))
            print("  Flags:             0x%x" % ctrl.get("flags", 0))
            print("  Total entries:     %s" % ctrl.get("total_entries", "?"))
            print("  Generation:        %s" % ctrl.get("generation", "?"))
            ds = ctrl.get("data_start_lcn", mlog_info.get("data_start_lcn", 0))
            de = ctrl.get("data_end_lcn", mlog_info.get("data_end_lcn", 0))
            print("  Data area:         0x%x - 0x%x (%d clusters)" % (ds, de, de - ds))
            lsn_o = ctrl.get("lsn_oldest", 0)
            if lsn_o:
                lo = lsn_o & 0xFFFFFFFF
                hi = (lsn_o >> 32) & 0xFFFFFFFF
                print("  LSN oldest:        0x%x.%x" % (lo, hi))
            table = _redo_ops_for_version(vmin)
            print("  Dispatch table:    %s (%d opcodes)" % (
                "v3.4" if vmin < 7 else ("v3.14" if vmin >= 14 else "v3.7+ (v3.14 table)"), len(table)))
        print()

        # Data summary or raw scan
        if do_raw:
            print("=" * W)
            print("Data Area Raw Scan")
            print("=" * W)
            for p in pages:
                if p["type"] == PAGE_TYPE_ZERO:
                    continue
                page = p.get("page", b"")
                sig = page[:4].hex() if page else "----"
                u32_0 = le32(page, 0) if page and len(page) >= 4 else 0
                u32_4 = le32(page, 4) if page and len(page) >= 8 else 0
                blk = ".%02d" % p["block"] if p.get("block") else "    "
                print("  VLCN 0x%06x  PLCN 0x%06x%s  %-5s  sig=%s"
                      "  u32[0]=0x%08x  u32[1]=0x%08x" % (
                          p["vlcn"], p["plcn"], blk, p["type"], sig, u32_0, u32_4))
            print()
        else:
            print("=" * W)
            print("Data Area Summary")
            print("=" * W)
            if not pages:
                print("  No data area pages found.")
            else:
                counts = {}
                for p in pages:
                    t = p["type"]
                    counts[t] = counts.get(t, 0) + 1
                total = len(pages)
                print("  Total pages:       %d" % total)
                for t in [PAGE_TYPE_ZERO, PAGE_TYPE_MSBP, PAGE_TYPE_DATA, PAGE_TYPE_MLOG]:
                    c = counts.get(t, 0)
                    if c > 0:
                        print("  %-20s %6d  (%5.1f%%)" % (t, c, c * 100.0 / total))
            print()

        # Records
        print("=" * W)
        print("Redo Records")
        print("=" * W)
        if not records:
            print("  No redo records found in data area.")
            print("  (Log may be clean — all transactions checkpointed.)")
        else:
            print("  Total records:      %d" % len(records))
            txn_starts = sum(1 for r in records if r["txn_start"])
            txn_commits = sum(1 for r in records if r["txn_commit"])
            print("  Transaction starts: %d" % txn_starts)
            print("  Transaction commits: %d" % txn_commits)
            print()
            if verbose:
                print("  %4s  %6s  %-40s  %10s  %6s  %5s" % (
                    "#", "Opcode", "Name", "OID", "Flags", "Size"))
                print("  %s  %s  %s  %s  %s  %s" % ("─"*4, "─"*6, "─"*40, "─"*10, "─"*6, "─"*5))
                for i, r in enumerate(records):
                    oid_str = "0x%x" % r["object_id"] if r["object_id"] else "—"
                    flag_parts = []
                    if r["txn_start"]:
                        flag_parts.append("S")
                    if r["txn_commit"]:
                        flag_parts.append("C")
                    flag_str = "+".join(flag_parts) if flag_parts else "—"
                    print("  %4d  0x%04x  %-40s  %10s  %6s  %5d" % (
                        i, r["opcode"], r["op_name"], oid_str, flag_str, r["size"]))
                print()

        # LogCore record headers (verbose) — the outer wrapper around each redo block
        if verbose:
            hdrs = []
            for p in pages:
                if p["type"] == PAGE_TYPE_MLOG and p.get("page"):
                    h = parse_mlog_record_header(p["page"])
                    if h:
                        h["plcn"] = p["plcn"]
                        h["block"] = p.get("block", 0)
                        hdrs.append(h)
            if hdrs:
                print("=" * W)
                print("LogCore Record Headers (%d data records)" % len(hdrs))
                print("=" * W)
                print("  %-11s  %-13s  %-13s  %-10s  %4s  %4s" % (
                    "PLCN.blk", "LSN", "prevLSN", "checksum", "type", "poff"))
                print("  %s  %s  %s  %s  %s  %s" % (
                    "─" * 11, "─" * 13, "─" * 13, "─" * 10, "─" * 4, "─" * 4))
                prev = None
                for h in hdrs[:64]:
                    lsn = h["lsn"]
                    plsn = h["prev_lsn"]
                    chain = "" if (prev is None or plsn == prev) else " !chain"
                    prev = lsn
                    print("  0x%06x.%02d  0x%011x  0x%011x  0x%08x  %4d  0x%02x%s" % (
                        h["plcn"], h["block"], lsn, plsn, h["checksum"] & 0xFFFFFFFF,
                        h["record_type"], h["payload_offset"], chain))
                if len(hdrs) > 64:
                    print("  … %d more" % (len(hdrs) - 64))
                magics = sorted(set(h["format_magic"] for h in hdrs))
                print("  format_magic (per-volume const, NOT a CRC — E42): %s" %
                      ", ".join("0x%08x" % m for m in magics))
                print()

        # Stats
        if do_stats and records:
            print("=" * W)
            print("Opcode Frequency")
            print("=" * W)
            freq = {}
            for r in records:
                freq[r["opcode"]] = freq.get(r["opcode"], 0) + 1
            cat_freq = {}
            for r in records:
                cat = OPCODE_CATEGORIES.get(r["op_name"], "other")
                cat_freq[cat] = cat_freq.get(cat, 0) + 1
            total = len(records)
            print("\n  %6s  %6s  %5s  %-40s" % ("Opcode", "Count", "%", "Name"))
            print("  %s  %s  %s  %s" % ("─"*6, "─"*6, "─"*5, "─"*40))
            for op in sorted(freq.keys()):
                name = redo_ops.get(op, "UNKNOWN_0x%02x" % op)
                pct = freq[op] * 100.0 / total
                print("  0x%04x  %6d  %5.1f  %s" % (op, freq[op], pct, name))
            print("\n  %-20s  %6s  %5s" % ("Category", "Count", "%"))
            print("  %s  %s  %s" % ("─"*20, "─"*6, "─"*5))
            for cat in sorted(cat_freq.keys(), key=lambda c: -cat_freq[c]):
                pct = cat_freq[cat] * 100.0 / total
                print("  %-20s  %6d  %5.1f" % (cat, cat_freq[cat], pct))
            unknown = sum(1 for r in records if r["opcode"] not in redo_ops)
            if unknown:
                print("\n  WARNING: %d records with unknown opcodes" % unknown)
            print()

        return 0

    except (struct.error, ValueError, IndexError) as e:
        print("Error parsing MLog data: %s" % e, file=sys.stderr)
        return 1
    finally:
        f.close()

def cmd_usn(image, remaining, partition_start):
    import csv as _csv

    _check_unknown_flags(remaining, {"-v", "--verbose", "--stats", "--json", "--info"}, {"--csv"})
    verbose = "-v" in remaining or "--verbose" in remaining
    do_stats = "--stats" in remaining
    do_json = "--json" in remaining
    do_info = "--info" in remaining
    csv_arg = None
    for i, a in enumerate(remaining):
        if a == "--csv":
            csv_arg = remaining[i + 1] if i + 1 < len(remaining) and not remaining[i + 1].startswith("-") else "-"
            break

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        W = 78
        vd, entry_meta = locate_change_journal(f, ps, cs, tr, obj_map)
        if vd is None:
            print("No Change Journal found in %s" % os.path.basename(image))
            print("  (OID 0x520 %s — journal not activated)" % (
                "present" if OID_FS_METADATA in obj_map else "absent"))
            return 0

        streams = parse_usn_journal_streams(vd, cs, tr)
        if not streams["j_extents"]:
            print("Change Journal entry found but no $J stream extents decoded")
            print("  Value size: %d bytes, sub-records: %d" % (
                len(vd), streams["subrecord_count"]))
            return 1

        j_data = read_usn_j_stream(f, ps, cs, streams["j_extents"],
                                    streams["j_stream_size"])
        records = parse_usn_records(j_data)
        journal_meta = parse_usn_journal_metadata(streams, f, ps, cs)

        oid_paths = build_oid_path_map(f, ps, cs, tr, obj_map)

        if do_info:
            print("=" * W)
            print("USN Journal Information")
            print("=" * W)
            print()
            print("  Change Journal entry in OID 0x520:")
            if entry_meta:
                print("    Value size:     %d bytes" % entry_meta.get("value_len", 0))
                print("    Stream count:   %s" % entry_meta.get("stream_count", "?"))
                ct = entry_meta.get("create_time", 0)
                if ct:
                    print("    Created:        %s" % _usn_filetime_short(ct))
            print()
            print("  $J stream (data):")
            print("    Extents:        %d" % len(streams.get("j_extents", [])))
            print("    Stream size:    %s bytes" % "{:,}".format(streams.get("j_stream_size", 0)))
            if streams.get("j_extents"):
                total_cl = sum(e["clusters"] for e in streams["j_extents"])
                print("    Total clusters: %d" % total_cl)
                for i, ext in enumerate(streams["j_extents"]):
                    print("    [%d] VLCN=0x%x PLCN=0x%x vcn=%d len=%d" % (
                        i, ext["vlcn"], ext["plcn"], ext["file_vcn"], ext["clusters"]))
            print()
            print("  $Max stream (parameters):")
            print("    Extents:        %d" % len(streams.get("max_extents", [])))
            if journal_meta.get("max_size") is not None:
                print("    Max journal:    %s bytes (%.1f MB)" % (
                    "{:,}".format(journal_meta["max_size"]),
                    journal_meta["max_size"] / (1024*1024)))
            if journal_meta.get("allocation_delta") is not None:
                print("    Alloc delta:    %s bytes" % "{:,}".format(journal_meta["allocation_delta"]))
            if journal_meta.get("journal_id") is not None:
                print("    Journal ID:     0x%016x" % journal_meta["journal_id"])
            print()
            print("  Parsed records:")
            print("    Count:          %d" % len(records))
            if records:
                versions = set("%d.%d" % (r.major_version, r.minor_version) for r in records)
                print("    Versions:       %s" % ", ".join(sorted(versions)))
                usn_min = min(r.usn for r in records)
                usn_max = max(r.usn for r in records)
                print("    USN range:      %d — %d" % (usn_min, usn_max))
            print()
            print("  USN_RECORD_V3 layout:")
            print("    Offset  Size  Field")
            for off, sz, name in [
                (0x00, 4, "Record length (u32)"),
                (0x04, 2, "Major version (u16) = 3"),
                (0x06, 2, "Minor version (u16) = 0"),
                (0x08, 16, "File ID (u128)"),
                (0x18, 16, "Parent file ID (u128)"),
                (0x28, 8, "USN (u64)"),
                (0x30, 8, "Timestamp (FILETIME)"),
                (0x38, 4, "Reason (u32)"),
                (0x3C, 4, "Source info (u32)"),
                (0x40, 4, "Security ID (u32)"),
                (0x44, 4, "File attributes (u32)"),
                (0x48, 2, "File name length (u16)"),
                (0x4A, 2, "File name offset (u16)"),
                (0x4C, 0, "File name (UTF-16LE, variable)"),
            ]:
                print("    0x%02X    %-4d  %s" % (off, sz, name))
            print()
            print("  Reason codes:")
            for bit in sorted(USN_REASON_FLAGS.keys()):
                print("    0x%08x  %s" % (bit, USN_REASON_FLAGS[bit]))
            print()
            return 0

        if csv_arg is not None:
            def _write_csv(out):
                w = _csv.writer(out)
                w.writerow(["usn", "timestamp", "reason_hex", "reason", "filename",
                            "file_oid", "file_idx", "parent_oid", "parent_idx", "path",
                            "attrs_hex", "attrs", "security_id", "source_info",
                            "record_length", "version"])
                for r in records:
                    parent_path = _usn_resolve_path(r.parent_oid, oid_paths)
                    full_path = "%s/%s" % (parent_path, r.filename) if parent_path and parent_path != "/" else r.filename
                    w.writerow([
                        r.usn, _usn_filetime_iso(r.timestamp),
                        "0x%08x" % r.reason, usn_reason_to_short(r.reason),
                        r.filename, "0x%x" % r.file_oid, "0x%x" % r.file_idx,
                        "0x%x" % r.parent_oid, "0x%x" % r.parent_idx,
                        full_path, "0x%08x" % r.file_attrs,
                        _usn_attrs_short(r.file_attrs), r.security_id,
                        "0x%08x" % r.source_info, r.record_length,
                        "%d.%d" % (r.major_version, r.minor_version),
                    ])
            if csv_arg == "-":
                _write_csv(sys.stdout)
            else:
                with open(csv_arg, "w", newline="") as cf:
                    _write_csv(cf)
                print("Wrote %d records to %s" % (len(records), csv_arg))
            return 0

        if do_json:
            import json as _json
            entries = []
            for r in records:
                parent_path = _usn_resolve_path(r.parent_oid, oid_paths)
                entries.append({
                    "usn": r.usn, "timestamp": _usn_filetime_iso(r.timestamp),
                    "reason": r.reason, "reason_text": usn_reason_to_short(r.reason),
                    "filename": r.filename, "file_oid": r.file_oid,
                    "file_idx": r.file_idx, "parent_oid": r.parent_oid,
                    "parent_idx": r.parent_idx,
                    "path": "%s/%s" % (parent_path, r.filename) if parent_path and parent_path != "/" else r.filename,
                    "file_attrs": r.file_attrs, "security_id": r.security_id,
                    "source_info": r.source_info, "record_length": r.record_length,
                    "version": "%d.%d" % (r.major_version, r.minor_version),
                })
            obj = {"journal": journal_meta, "record_count": len(entries), "records": entries}
            print(_json.dumps(obj, indent=2))
            return 0

        if do_stats:
            print("=" * W)
            print("USN Journal Statistics (%d records)" % len(records))
            print("=" * W)
            print()
            if not records:
                print("  (no records)")
            else:
                reason_counts = {}
                file_counts = {}
                dir_set = set()
                ts_min = ts_max = None
                for r in records:
                    for bit, name in sorted(USN_REASON_FLAGS.items()):
                        if r.reason & bit:
                            reason_counts[name] = reason_counts.get(name, 0) + 1
                    file_counts[r.filename] = file_counts.get(r.filename, 0) + 1
                    dir_set.add(r.parent_oid)
                    if r.timestamp > 0:
                        if ts_min is None or r.timestamp < ts_min:
                            ts_min = r.timestamp
                        if ts_max is None or r.timestamp > ts_max:
                            ts_max = r.timestamp
                print("  Reason code distribution:")
                for name, cnt in sorted(reason_counts.items(), key=lambda x: -x[1]):
                    print("    %-30s %5d" % (name, cnt))
                print()
                print("  Top files by record count:")
                for name, cnt in sorted(file_counts.items(), key=lambda x: -x[1])[:15]:
                    print("    %-40s %5d" % (name, cnt))
                print()
                print("  Unique filenames:    %d" % len(file_counts))
                print("  Unique parent dirs:  %d" % len(dir_set))
                print("  USN range:           %d — %d" % (
                    min(r.usn for r in records), max(r.usn for r in records)))
                if ts_min and ts_max:
                    print("  Time range:          %s" % _usn_filetime_short(ts_min))
                    print("                    to %s" % _usn_filetime_short(ts_max))
                print()
            return 0

        # Default: list mode
        print("=" * W)
        print("USN Journal Records (%d entries)" % len(records))
        print("=" * W)
        print()
        for r in records:
            parent_path = _usn_resolve_path(r.parent_oid, oid_paths)
            print("  USN %-10d %s" % (r.usn, r.filename))
            print("    Time:    %s" % _usn_filetime_short(r.timestamp))
            print("    Reason:  %s (0x%08x)" % (usn_reason_to_str(r.reason), r.reason))
            print("    FileID:  %04x:%016x" % (r.file_oid, r.file_idx))
            print("    Parent:  %04x:%016x  -> %s" % (
                r.parent_oid, r.parent_idx, parent_path))
            print("    Attrs:   %s" % _usn_attrs_short(r.file_attrs))
            if r.source_info:
                src_parts = []
                for bit, name in sorted(USN_SOURCE_FLAGS.items()):
                    if r.source_info & bit:
                        src_parts.append(name)
                print("    Source:  %s (0x%08x)" % (" | ".join(src_parts), r.source_info))
            if r.security_id:
                print("    SecID:   %d" % r.security_id)
            if verbose:
                print("    RecLen:  %d  Version: %d.%d  StreamOff: 0x%x" % (
                    r.record_length, r.major_version, r.minor_version, r.offset))
            print()

        return 0

    except (struct.error, ValueError, IndexError, OverflowError) as e:
        print("Error parsing USN data: %s" % e, file=sys.stderr)
        return 1
    finally:
        f.close()

def cmd_timeline(image, remaining, partition_start):
    import csv as _csv
    args = _parse_args(remaining, flags=["--csv", "--no-si", "--fast"],
                       valued=["--file", "--oid", "--limit", "--source", "--depth"])
    skip_si = args["no_si"] or args["fast"]   # --fast is a friendly alias for --no-si
    si_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 12
    name_filter = args["file"].lower() if args["file"] else None
    oid_filter = _int_arg(args["oid"], "--oid", 0) if args["oid"] else None
    limit = _int_arg(args["limit"], "--limit") if args["limit"] else 0
    # accept the source token with or without the leading '$' (event labels are "$SI"/"USN"/"MLog";
    # docs/help say "SI") — normalize both sides by stripping a leading '$' so `--source SI` == `--source $SI`.
    src_filter = args["source"].upper().lstrip("$") if args["source"] else None

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        oid_paths = build_oid_path_map(f, ps, cs, tr, obj_map)
        events = []   # (filetime, source, oid, name/path, detail)
        counts = {"USN": 0, "MLog": 0, "$SI": 0}

        # (3-of-3 validated parsers — see report; merge order doesn't matter, we sort by time)

        # (1) $SI MACB — per-file Created/Modified/MFT-Changed/Accessed (always present).
        # enrich=False: the MACB timestamps are cached in each directory entry, so we do NOT need the
        # per-object $SI read that enrich=True does (SecurityId/USN/internal-flags) — those aren't used
        # in the timeline. Dropping enrich removes one B+-tree read PER non-resident object (the former
        # bottleneck: ~26k extra reads on a 35k-object volume).
        if not skip_si:
            for e in walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, si_depth, False, set()):
                oid = e.get("oid", 0); path = e.get("path", e.get("name", ""))
                for fld, lbl in (("create_time", "Created"), ("modify_time", "Modified"),
                                 ("change_time", "Metadata-Changed"), ("access_time", "Accessed")):
                    ts = e.get(fld, 0)
                    if ts:
                        events.append((ts, "$SI", oid, path, lbl)); counts["$SI"] += 1

        # (2) USN — per-record change events (only if the journal is active)
        vd, _em = locate_change_journal(f, ps, cs, tr, obj_map)
        if vd is not None:
            streams = parse_usn_journal_streams(vd, cs, tr)
            if streams["j_extents"]:
                j_data = read_usn_j_stream(f, ps, cs, streams["j_extents"], streams["j_stream_size"])
                for r in parse_usn_records(j_data):
                    nm = getattr(r, "filename", "") or oid_paths.get(r.file_oid, "")
                    events.append((r.timestamp, "USN", r.file_oid, nm,
                                   usn_reason_to_short(r.reason))); counts["USN"] += 1

        # (3) MLog — per-transaction events that carry an embedded timestamp
        redo_ops = _redo_ops_for_version(vmin)
        # MLog events have NO true wall-clock time — the per-transaction time is read from an embedded $SI
        # FILETIME in the redo value (the affected object's birth, which for a RENAME/MOVE is NOT the op time
        # and can be old/stomped). A time that PREDATES the volume's own creation is therefore a provably-wrong
        # mis-extraction (an operation cannot occur before the volume existed): we UNDATE it (so it no longer
        # mis-sorts before real events, e.g. a rename appearing before its create) and mark it. (Fixes the
        # timeline MLog-timestamp misdating, ~1% of MLog rows on win11refstestmftecmd.)
        mlog_info = get_mlog_info(f, ps, cs, tr, obj_map)
        if mlog_info:
            _vol_create, _ = _volume_times(f, ps, cs, tr, obj_map)
            ctrl = read_mlog_control(f, ps, cs, mlog_info)
            # stream the block generator straight into the transaction extractor (single pass) so the
            # full 1 GiB log is never materialized — fixes timeline OOM on very large logs.
            mlog_undated = 0
            for txn in extract_mlog_transactions(
                    scan_mlog_data_area(f, ps, cs, tr, mlog_info, ctrl), redo_ops):
                t = _mlog_resolve_txn(txn, oid_paths)
                if t["timestamp"]:
                    mts = t["timestamp"]; action = t["action"]
                    if _vol_create and mts < _vol_create - TS_MARGIN_100NS:
                        mts = 0; action = t["action"] + " [MLog time unreliable]"; mlog_undated += 1
                    events.append((mts, "MLog", t["oid"], t["path"] or t["name"], action))
                    counts["MLog"] += 1
            if mlog_undated:
                counts["mlog_undated"] = mlog_undated

        # filter
        if oid_filter is not None:
            events = [ev for ev in events if ev[2] == oid_filter]
        if name_filter:
            events = [ev for ev in events if name_filter in str(ev[3]).lower()]
        if src_filter:
            events = [ev for ev in events if ev[1].upper().lstrip("$") == src_filter]
        # chronological sort (undated events — ts==0 — sink to the end)
        events.sort(key=lambda ev: ev[0] if ev[0] else (1 << 63))
        if limit:
            events = events[:limit]

        if args["csv"]:
            w = _csv.writer(sys.stdout)
            w.writerow(["timestamp_utc", "source", "oid", "name", "event"])
            for ts, src, oid, nm, det in events:
                w.writerow([_filetime_to_str(ts), src, "0x%x" % oid if oid else "", nm, det])
            return 0

        W = 78
        print("=" * W)
        print("ReFS Super-Timeline — %s" % os.path.basename(image))
        print("=" * W)
        print("  Sources merged: USN=%d  MLog=%d  $SI-MACB=%d  (joined by OID, sorted by time)" % (
            counts["USN"], counts["MLog"], counts["$SI"]))
        if skip_si:
            print("  MODE: --fast — $SI MACB walk skipped; change-journals only (USN + MLog).")
        elif len(obj_map) > 8000:
            print("  NOTE: the $SI MACB walk visits every file — slow on large volumes. Use --fast")
            print("        (USN + MLog change-journals only) for a quick pass.")
        if counts["USN"] == 0:
            print("  NOTE: USN journal inactive on this image — timeline is $SI + MLog only.")
        print("  Caveat: USN and $SI carry exact FILETIMEs. MLog has NO wall-clock time — an MLog row's time is")
        print("          the affected object's embedded $SI birth (approximate; for a RENAME/MOVE it is the object")
        print("          birth, not the op time). MLog times that predate the volume are undated + marked.")
        if counts.get("mlog_undated"):
            print(f"          ({counts['mlog_undated']} MLog rows had an impossible pre-volume time → undated.)")
        print("-" * W)
        print("  %-23s  %-5s  %-10s  %-26s  %s" % ("Timestamp (UTC)", "Src", "OID", "Name/Path", "Event"))
        print("  %s" % ("-" * (W - 2)))
        for ts, src, oid, nm, det in events:
            tn = (nm[:24] + "…") if nm and len(nm) > 25 else (nm or "")
            print("  %-23s  %-5s  %-10s  %-26s  %s" % (
                _filetime_to_str(ts) if ts else "(undated)", src,
                "0x%x" % oid if oid else "—", tn, det))
        if not events:
            print("  (no events — try without --file/--oid filters)")
        print("-" * W)
        print("  %d events" % len(events))
        return 0
    finally:
        f.close()


# ════════════════════════════════════════════════════════════════════════
#  Migrated forensic commands (Phase 3): timestomp / extract / security
#  Ported VERBATIM from refsanalysis (closure: SD/ACL parsers, extent/data-run readers, _sid_name
#  wrapper + _parse_sid alias over forefst's canonical parse_sid/sid_name). Routed via FORENSIC_HANDLERS.
# ════════════════════════════════════════════════════════════════════════

_ACE_TYPES = {
    0x00: "ACCESS_ALLOWED", 0x01: "ACCESS_DENIED",
    0x02: "SYSTEM_AUDIT", 0x03: "SYSTEM_ALARM",
    0x05: "ACCESS_ALLOWED_COMPOUND",
    0x06: "ACCESS_ALLOWED_OBJECT", 0x07: "ACCESS_DENIED_OBJECT",
    0x09: "ACCESS_ALLOWED_CALLBACK", 0x0A: "ACCESS_DENIED_CALLBACK",
    0x0B: "ACCESS_ALLOWED_CALLBACK_OBJECT",
    0x0C: "ACCESS_DENIED_CALLBACK_OBJECT",
    0x11: "SYSTEM_MANDATORY_LABEL", 0x12: "SYSTEM_RESOURCE_ATTRIBUTE",
    0x13: "SYSTEM_SCOPED_POLICY_ID", 0x14: "SYSTEM_PROCESS_TRUST_LABEL",
    }

_ADS_DESCRIPTOR = 0x000500B0

_DATA_ATTR_MARKER = 0x80000002

_FILE_RIGHTS = {
    0x00000001: "READ_DATA", 0x00000002: "WRITE_DATA",
    0x00000004: "APPEND_DATA", 0x00000008: "READ_EA",
    0x00000010: "WRITE_EA", 0x00000020: "EXECUTE",
    0x00000040: "DELETE_CHILD", 0x00000080: "READ_ATTRIBUTES",
    0x00000100: "WRITE_ATTRIBUTES", 0x00010000: "DELETE",
    0x00020000: "READ_CONTROL", 0x00040000: "WRITE_DAC",
    0x00080000: "WRITE_OWNER", 0x00100000: "SYNCHRONIZE",
    0x01000000: "ACCESS_SYSTEM_SECURITY", 0x02000000: "MAXIMUM_ALLOWED",
    0x10000000: "GENERIC_ALL", 0x20000000: "GENERIC_EXECUTE",
    0x40000000: "GENERIC_WRITE", 0x80000000: "GENERIC_READ",
    }

_MANDATORY_LABEL_RIGHTS = {0x1: "NO_WRITE_UP", 0x2: "NO_READ_UP", 0x4: "NO_EXECUTE_UP"}

_SD_CONTROL_FLAGS = {
    0x0001: "SE_OWNER_DEFAULTED", 0x0002: "SE_GROUP_DEFAULTED",
    0x0004: "SE_DACL_PRESENT", 0x0008: "SE_DACL_DEFAULTED",
    0x0010: "SE_SACL_PRESENT", 0x0020: "SE_SACL_DEFAULTED",
    0x0100: "SE_DACL_AUTO_INHERIT_REQ", 0x0200: "SE_SACL_AUTO_INHERIT_REQ",
    0x0400: "SE_DACL_AUTO_INHERITED", 0x0800: "SE_SACL_AUTO_INHERITED",
    0x1000: "SE_DACL_PROTECTED", 0x2000: "SE_SACL_PROTECTED",
    0x4000: "SE_RM_CONTROL_VALID", 0x8000: "SE_SELF_RELATIVE",
    }

_SIMPLE_ACE_LAYOUT = {0x00, 0x01, 0x02, 0x03, 0x09, 0x0A, 0x0D, 0x0E, 0x11, 0x12, 0x13}

_parse_sid = parse_sid

def _hx(v):
    return f"0x{v:x}" if v is not None else "n/a"

def _sid_name(sid_str):
    n = sid_name(sid_str)
    return f"{n} ({sid_str})" if n else sid_str

def _format_access_mask(mask, ace_type=None):
    if ace_type == 0x11:  # SYSTEM_MANDATORY_LABEL — mask is an integrity policy, not file rights
        flags = [name for bit, name in sorted(_MANDATORY_LABEL_RIGHTS.items()) if mask & bit]
        return "|".join(flags) if flags else _hx(mask)
    if mask == 0x1F01FF: return "FULL_CONTROL"
    if mask == 0x1301BF: return "MODIFY"
    if mask == 0x1200A9: return "READ_EXECUTE"
    if mask == 0x120089: return "READ"
    if mask == 0x120116: return "WRITE"
    flags = [name for bit, name in sorted(_FILE_RIGHTS.items()) if mask & bit]
    return "|".join(flags) if flags else _hx(mask)

def _parse_acl(data, offset):
    if offset == 0 or offset + 8 > len(data): return []
    ace_count = le16(data, offset + 4)
    aces = []
    pos = offset + 8
    for _ in range(ace_count):
        if pos + 4 > len(data): break
        ace_type = data[pos]
        ace_flags = data[pos + 1]
        ace_size = le16(data, pos + 2)
        if pos + ace_size > len(data): break
        ace = {
            "type": _ACE_TYPES.get(ace_type, f"Unknown(0x{ace_type:02x})"),
            "type_id": ace_type, "flags": ace_flags, "size": ace_size,
        }
        if ace_type in _SIMPLE_ACE_LAYOUT and ace_size >= 8:
            ace["mask"] = le32(data, pos + 4)
            ace["mask_str"] = _format_access_mask(ace["mask"], ace_type)
            sid_str, _ = _parse_sid(data, pos + 8)
            ace["sid"] = sid_str
            ace["sid_name"] = _sid_name(sid_str)
        pos += ace_size
        aces.append(ace)
    return aces

def _parse_security_descriptor(sd_data):
    if len(sd_data) < 20:
        return {"error": f"SD too short ({len(sd_data)} bytes)"}
    control = le16(sd_data, 2)
    off_owner = le32(sd_data, 4)
    off_group = le32(sd_data, 8)
    off_sacl = le32(sd_data, 12)
    off_dacl = le32(sd_data, 16)
    result = {
        "revision": sd_data[0], "control": control,
        "control_flags": [name for bit, name in _SD_CONTROL_FLAGS.items() if control & bit],
        "size": len(sd_data),
    }
    if off_owner and off_owner < len(sd_data):
        sid_str, _ = _parse_sid(sd_data, off_owner)
        result["owner"] = sid_str; result["owner_name"] = _sid_name(sid_str)
    else:
        result["owner"] = "(none)"; result["owner_name"] = "(none)"
    if off_group and off_group < len(sd_data):
        sid_str, _ = _parse_sid(sd_data, off_group)
        result["group"] = sid_str; result["group_name"] = _sid_name(sid_str)
    else:
        result["group"] = "(none)"; result["group_name"] = "(none)"
    result["dacl"] = _parse_acl(sd_data, off_dacl) if (control & 0x0004 and off_dacl and off_dacl < len(sd_data)) else []
    result["sacl"] = _parse_acl(sd_data, off_sacl) if (control & 0x0010 and off_sacl and off_sacl < len(sd_data)) else []
    return result

def _parse_sd_stream(f, ps, cs, tr, obj_map):
    if 0x530 not in obj_map:
        return [], "OID 0x530 (Security Descriptor Stream) not found in Object Table"
    rows = walk_bplus(f, ps, cs, tr, obj_map[0x530])
    descriptors = []
    for kd, vd in rows:
        if len(kd) >= 16:
            sid_high = le32(kd, 8); sid_low = le32(kd, 12)
            security_id = (sid_high << 32) | sid_low
        elif len(kd) >= 8:
            security_id = le64(kd, 0)
        else:
            security_id = 0
        SD_HEADER_SIZE = 12
        if len(vd) >= SD_HEADER_SIZE + 20:
            # Wrapper: +0x00 SD hash (=SecurityId low), +0x04 generation (=SecurityId high), +0x08 entry size
            val_hash = le32(vd, 0); val_generation = le32(vd, 4)
            sd_bytes = vd[SD_HEADER_SIZE:]
            sd = _parse_security_descriptor(sd_bytes)
            sd["security_id"] = security_id
            sd["sd_hash"] = val_hash; sd["generation"] = val_generation
            # Tampering check: the stored hash must equal the recomputed content hash
            sd["computed_hash"] = _refs_sd_hash(sd_bytes)
            sd["hash_valid"] = (sd["computed_hash"] == val_hash)
            sd["key_hex"] = kd.hex(); sd["key_len"] = len(kd)
            sd["raw"] = sd_bytes
            descriptors.append(sd)
        else:
            descriptors.append({
                "security_id": security_id, "key_hex": kd.hex(),
                "key_len": len(kd), "value_len": len(vd),
                "value_hex": vd.hex() if len(vd) < 64 else vd[:64].hex() + "...",
                "note": f"Value too short ({len(vd)} bytes, need {SD_HEADER_SIZE + 20}+)",
            })
    return descriptors, None

def _print_sd(sd, verbose=False, index=None):
    prefix = f"[{index}] " if index is not None else ""
    sec_id = sd.get("security_id", 0)
    hash_str = f", hash={_hx(sd['sd_hash'])}" if "sd_hash" in sd else ""
    gen_str = f", gen={sd['generation']}" if "generation" in sd else ""
    valid_str = ""
    if "hash_valid" in sd:
        valid_str = " [hash OK]" if sd["hash_valid"] else f" [HASH MISMATCH: computed {_hx(sd['computed_hash'])}]"
    print(f"  {prefix}SecurityId: {_hx(sec_id)}{hash_str}{gen_str}{valid_str}")
    if "error" in sd:
        print(f"    ERROR: {sd['error']}"); return
    if "note" in sd:
        print(f"    NOTE: {sd['note']} (value_len={sd.get('value_len', 0)})")
        if "value_hex" in sd: print(f"    Value hex: {sd['value_hex']}")
        return
    print(f"    Revision: {sd.get('revision', '?')}, Size: {sd.get('size', '?')} bytes")
    print(f"    Control:  {_hx(sd.get('control', 0))} ({', '.join(sd.get('control_flags', []))})")
    print(f"    Owner:    {sd.get('owner_name', '(none)')}")
    print(f"    Group:    {sd.get('group_name', '(none)')}")
    dacl = sd.get("dacl", [])
    if dacl:
        print(f"    DACL ({len(dacl)} ACEs):")
        for ace in dacl:
            print(f"      {ace.get('type','?')}: {ace.get('sid_name', ace.get('sid','?'))} -> {ace.get('mask_str', _hx(ace.get('mask',0)))}")
    else:
        print(f"    DACL: (none)")
    sacl = sd.get("sacl", [])
    if sacl:
        print(f"    SACL ({len(sacl)} ACEs):")
        for ace in sacl:
            print(f"      {ace.get('type','?')}: {ace.get('sid_name', ace.get('sid','?'))} -> {ace.get('mask_str', _hx(ace.get('mask',0)))}")
    if verbose and "raw" in sd:
        raw = sd["raw"]
        print(f"    Raw SD hex ({len(raw)} bytes):")
        for off in range(0, min(len(raw), 256), 16):
            hexline = " ".join(f"{b:02x}" for b in raw[off:off+16])
            ascii_line = "".join(chr(b) if 32 <= b < 127 else "." for b in raw[off:off+16])
            print(f"      {off:04x}: {hexline:<48} {ascii_line}")
        if len(raw) > 256: print(f"      ... ({len(raw) - 256} more bytes)")

def _refs_sd_hash(sd_data):
    """Recompute the ReFS/NTFS $Secure security-descriptor hash over the SD bytes.
    h = 0; for each little-endian u32 dword d in the SD: h = (d + rol(h,3)) & 0xFFFFFFFF.
    Equals the SecurityId low 32 bits (verified 1113/1113 across v3.4+v3.14). Used to
    detect descriptor tampering: a stored hash != recomputed hash flags corruption."""
    h = 0
    for i in range(0, len(sd_data) - 3, 4):
        d = le32(sd_data, i)
        h = (d + (((h << 3) | (h >> 29)) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return h

def _stream_extent_records(vd):
    """E61: extent lists for NON-RESIDENT (>= 2 KB) streams of a resident type-0x30 value. A large ADS's
    content is NOT inline and NOT in its 0xB0 descriptor — it lives in a separate **type-0x0 sub-record**
    (key type 0x00), one per non-resident stream, using the SAME 24-byte type-0x40 extent format as
    snapshots. Returns {stream_size: [(file_vcn, vlcn, run_length), ...]} keyed by stream_size (the link:
    the 0xB0 descriptor's stream_size == the type-0x0 record's stream_size@0x38). PROVEN byte-exact on 161
    extent-backed ADS (win11refs8g v2 sweep 2 KB..2 MB + multi-ADS). Header: ihdr=le32(v,0);
    extent_count=le32(v,ihdr+0x14); extents at v[ihdr+0x28] (vlcn@+0, file_vcn@+0x0C, run@+0x14)."""
    recs = {}
    for k, v in parse_resident_btree_rows(vd):
        if len(k) <= 12 or k[12] != 0x00 or len(v) < 0x50:
            continue
        ihdr = le32(v, 0)
        if ihdr <= 0 or ihdr + 0x18 > len(v):
            continue
        cnt = le32(v, ihdr + 0x14)
        eo = ihdr + 0x28
        exts = []
        for i in range(cnt):
            b = eo + i * 24
            if b + 24 > len(v):
                break
            vlcn, fvcn, run = le64(v, b), le32(v, b + 0x0C), le32(v, b + 0x14)
            if run == 0 or run > 0x1000000:
                continue
            exts.append((fvcn, vlcn, run))
        if exts:
            recs[le64(v, 0x38)] = sorted(exts)     # keyed by stream_size
    return recs

def _read_vlcn_extents(f, ps_off, cs, tr, exts, size):
    """Reassemble a stream from its (file_vcn, vlcn, run_length) extent list (24-byte type-0x40 format):
    place each run at file_vcn*cs, VLCN->PLCN via the Container Table, trim to `size`. Reuses the proven
    snapshot/CoW read path. Bytes may be stale for a recovered/deleted stream (no freshness check)."""
    if not exts:
        return b""
    alloc = min(max(fv + run for fv, _vl, run in exts) * cs, 512 * 1024 * 1024)
    buf = bytearray(alloc)
    for fvcn, vlcn, run in sorted(exts):
        for j in range(run):
            try:
                plcn = tr.tr(vlcn + j)
            except Exception:
                plcn = vlcn + j
            off = (fvcn + j) * cs
            if off + cs > len(buf):
                break
            f.seek(ps_off + plcn * cs)
            buf[off:off + cs] = f.read(cs)
    return bytes(buf[:size])

def _parse_ads_from_value(vd):
    """Extract Alternate Data Stream entries (name + inline content) from a resident directory-entry value.

    C11a: this now enumerates ADS via the embedded B+-tree ROW TABLE (the same structural walk `files`
    uses via detect_ads_in_resident), NOT a linear byte-scan. The old scanner skipped past each stream's
    content and MISSED every ADS beyond the first on a multi-ADS file. All-disk validation: the row table
    finds 956 ADS vs the scanner's 678; content byte-for-byte MATCHES the scanner on all 678 common ADS and
    recovers 278 more with correct content. Each ADS row's value carries the descriptor at vrow+0x08
    (le32==0x0C, le32+4==0x30 => hdr=vrow+0x04), storage_type at hdr+0x0C, alloc@hdr+0x14, size@hdr+0x1C,
    inline content at hdr+0x38. Snapshots share the 0xB0 key but have StreamSummary flags==2 (excluded via
    _is_snapshot_value). Same entry-dict shape the scanner returned, so callers are unchanged."""
    ads = []
    _ext_recs = _stream_extent_records(vd)     # E61: type-0x0 extent lists for non-resident (>=2KB) ADS
    for kd, vrow in parse_resident_btree_rows(vd):
        if not _is_b0_snapshot_key(kd) or _is_snapshot_value(vrow) or len(kd) <= 16:
            continue
        try:
            stream_name = kd[16:].decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError:
            continue
        if not stream_name:
            continue
        hdr = None
        for scan in range(0, len(vrow) - 8):
            if le32(vrow, scan) == 0x0C and le32(vrow, scan + 4) == 0x30:
                hdr = scan - 4
                break
        if hdr is None or hdr < 0 or hdr + 0x24 > len(vrow):
            ads.append({"name": stream_name, "stream_size": 0, "alloc_size": 0, "storage": "unknown"})
            continue
        storage_type = le32(vrow, hdr + 0x0C)
        alloc_size = le64(vrow, hdr + 0x14)
        stream_size = le64(vrow, hdr + 0x1C)
        # R6: label the storage honestly — a genuinely-INLINE ADS keeps its bytes in the value at hdr+0x38,
        # and stores them packed exactly, so alloc_size == stream_size. If alloc != size, the inline window
        # at hdr+0x38 holds descriptor tail, NOT content, so it must not be emitted as inline content.
        # (E60 added this alloc==size guard.) The guard is ADS-specific: a $DATA main stream legitimately
        # rounds alloc up, so it is NOT applied to get_resident_data_content (there it would reject 221k
        # genuine inline files).
        # E61 (supersedes the earlier E60 "adstest is MLog-only" characterization): an ADS whose content is
        # >= 2 KB — or a small refsutil-streamsnapshot-created ADS like `adstest` — is EXTENT-BACKED. Its
        # content is not inline; the extents live in a type-0x0 sub-record keyed by stream_size (see
        # _stream_extent_records). storage_type stays 0 (still an ADS, not a snapshot). `adstest`
        # (win11refs2tsnapshots: size=30, alloc=4096) IS such an entry: its 30 bytes live in 1 committed
        # extent (vlcn 108101828), recovered byte-exact via the extent path — the MLog page at 0x98c7560 was
        # an ADDITIONAL journaled copy, not the only copy. So: claim inline only when alloc==size AND < 2 KB;
        # otherwise resolve the extent record (extent-backed) and fall back to metadata-only if none exists.
        content_off = hdr + 0x38
        inline = (storage_type == 0 and alloc_size == stream_size
                  and content_off + stream_size <= len(vrow) and stream_size <= 0x100000)
        ext_list = _ext_recs.get(stream_size) if storage_type == 0 else None
        if inline:
            storage = "inline"
        elif ext_list:
            storage = "extent-backed"
        elif storage_type == 0:
            storage = "non-inline (alloc!=size — content not in the record)"
        else:
            storage = "non-inline (type %d)" % storage_type
        entry = {"name": stream_name, "stream_size": stream_size, "alloc_size": alloc_size, "storage": storage}
        if storage == "inline":
            entry["content"] = bytes(vrow[content_off:content_off + stream_size])
        elif storage == "extent-backed":
            entry["extents"] = ext_list          # [(file_vcn, vlcn, run_length), ...] — read via _read_vlcn_extents
        ads.append(entry)
    return ads

def _find_extents_in_subrecord(vd, rec_off, rec_size, needed, tr, cs, result):
    """Search a sub-record for extent table entries."""
    rec_end = rec_off + rec_size
    for scan_off in range(rec_off + 4, rec_end - 24, 4):
        start = le32(vd, scan_off)
        end = le32(vd, scan_off + 4)
        v2 = le32(vd, scan_off + 8)
        cap = le32(vd, scan_off + 12)
        total = le32(vd, scan_off + 16)
        count = le32(vd, scan_off + 20)
        if not (0x10 <= start <= 0x200 and end > start and
                count > 0 and count <= 1000 and cap >= 0x100):
            continue
        entry_area = end - start
        if entry_area < count * 24 or entry_area > count * 32 + 16:
            continue
        entries_off = scan_off + start

        # Fixed 24-byte stride (normal extents)
        total_clusters = 0
        candidate_extents = []
        for i in range(count):
            eoff = entries_off + i * 24
            if eoff + 24 > len(vd): break
            vlcn = le32(vd, eoff)
            vlcn_hi = le32(vd, eoff + 4)
            flags = le32(vd, eoff + 8)
            file_vcn = le32(vd, eoff + 12)
            run_len = le32(vd, eoff + 20)
            full_vlcn = vlcn | (vlcn_hi << 32)
            if run_len > 0 and full_vlcn > 0:
                plcn = tr.tr(full_vlcn)
                candidate_extents.append({
                    "vlcn": full_vlcn, "plcn": plcn, "file_vcn": file_vcn,
                    "clusters": run_len, "flags": flags, "disk_offset": 0,
                })
                total_clusters += run_len
        if total_clusters == needed and candidate_extents:
            result["extents"] = candidate_extents
            return

        # Variable-stride for integrity streams (32-byte checksum entries)
        total_clusters = 0
        candidate_extents = []
        eoff = entries_off
        for i in range(count):
            if eoff + 24 > len(vd): break
            vlcn = le32(vd, eoff)
            vlcn_hi = le32(vd, eoff + 4)
            flags = le32(vd, eoff + 8)
            file_vcn = le32(vd, eoff + 12)
            run_len = le32(vd, eoff + 20)
            full_vlcn = vlcn | (vlcn_hi << 32)
            if run_len > 0 and full_vlcn > 0:
                plcn = tr.tr(full_vlcn)
                candidate_extents.append({
                    "vlcn": full_vlcn, "plcn": plcn, "file_vcn": file_vcn,
                    "clusters": run_len, "flags": flags, "disk_offset": 0,
                    "integrity_checksum": flags == 0x1c00d0,
                })
                total_clusters += run_len
            eoff += 32 if flags == 0x1c00d0 else 24
        if total_clusters == needed and candidate_extents:
            result["extents"] = candidate_extents
            return

    # Fallback: single-extent pattern (0x80000002 marker)
    for scan_off in range(rec_off + 4, rec_end - 16, 4):
        if le32(vd, scan_off) == _DATA_ATTR_MARKER:
            vlcn = le32(vd, scan_off + 4)
            cluster_count = le64(vd, scan_off + 8) if scan_off + 16 <= len(vd) else 0
            if cluster_count == needed and vlcn > 0:
                plcn = tr.tr(vlcn)
                result["extents"] = [{
                    "vlcn": vlcn, "plcn": plcn, "file_vcn": 0,
                    "clusters": cluster_count, "flags": 0, "disk_offset": 0,
                }]
                return

def _parse_extents_from_type40(vd, cs, tr):
    """Parse data extent information from a type 0x40 value."""
    result = {
        "file_size": 0, "alloc_size": 0, "file_attrs": 0,
        "timestamps": [], "extents": [], "val_len": len(vd),
    }
    if len(vd) < 0x68: return result
    result["timestamps"] = [le64(vd, 0x28), le64(vd, 0x30),
                            le64(vd, 0x38), le64(vd, 0x40)]
    result["file_attrs"] = le32(vd, 0x48)
    result["file_size"] = le64(vd, 0x58)
    result["alloc_size"] = le64(vd, 0x60)
    needed = (result["alloc_size"] + cs - 1) // cs if result["alloc_size"] > 0 else 0
    if needed == 0: return result

    off = 0xA8
    while off < len(vd) - 4:
        rec_size = le32(vd, off)
        if rec_size == 0 or rec_size > len(vd) - off or rec_size > 4096: break
        _find_extents_in_subrecord(vd, off, rec_size, needed, tr, cs, result)
        off += rec_size
    return result

def _analyze_dir_extents(f, ps, cs, tr, obj_map, dir_oid):
    """Analyze a directory's B+-tree for file data extent information."""
    if dir_oid not in obj_map: return []
    rows = walk_bplus(f, ps, cs, tr, obj_map[dir_oid])
    files = []
    resident_files = []
    type40_map = {}

    for kd, vd in rows:
        if len(kd) < 4: continue
        attr_type = le16(kd, 0)
        key_flags = le16(kd, 2)
        if attr_type == 0x30:
            name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
            # E4 fix: non-resident value is 72 B on v3.4-v3.9, 84 B on v3.10+ (driver gate
            # RefsAddFileNameIndexEntry: 0x48 when version<0x309, else 0x54). `== 84` skipped every
            # pre-3.10 non-resident file. All reads below are <= 0x40, identical in both layouts (§C.3).
            if key_flags == 0x02 and 0x48 <= len(vd) <= 84:
                stream_idx = le64(vd, 0x00)
                target_oid = le64(vd, 0x08)
                ts = [le64(vd, 0x10), le64(vd, 0x18),
                      le64(vd, 0x20), le64(vd, 0x28)]
                alloc_size = le64(vd, 0x30)
                file_size = le64(vd, 0x38)
                file_attrs = le32(vd, 0x40)
                is_dir = bool(file_attrs & 0x10000000)
                if not is_dir and file_size > 0:
                    files.append((name, stream_idx, target_oid, file_size,
                                  alloc_size, file_attrs, ts))
            elif key_flags == 0x01 and len(vd) > 84:
                resident_files.append((name, bytes(vd)))
        elif attr_type == 0x40 and len(kd) >= 24 and len(vd) >= 0x68:
            stream_idx = le64(kd, 8)
            parent_oid = le64(kd, 16)
            type40_map[(stream_idx, parent_oid)] = _parse_extents_from_type40(vd, cs, tr)

    results = []
    _home_cache = {}   # target_oid -> {stream_idx: ext_info}; authoritative backing streams in the home tree
    def _home_streams(oid):
        if oid not in _home_cache:
            m = {}
            if oid in obj_map:
                for rkd, rvd in walk_bplus(f, ps, cs, tr, obj_map[oid]):
                    if len(rkd) >= 24 and le16(rkd, 0) == 0x40 and len(rvd) >= 0x68:
                        m.setdefault(le64(rkd, 8), _parse_extents_from_type40(rvd, cs, tr))
            _home_cache[oid] = m
        return _home_cache[oid]
    for name, stream_idx, target_oid, file_size, alloc_size, file_attrs, ts in files:
        # B1 fix: a non-resident file's $DATA backing is the type-0x40 stream owned by its HOME object
        # (target_oid = dir-entry value+0x08). Resolve from the home tree; keying by the enclosing
        # dir_oid alone mis-selected a stray colliding-stream_idx record physically stored in the dir.
        ext_info = None
        source = "unresolved"
        if target_oid == dir_oid:
            ext_info = type40_map.get((stream_idx, dir_oid))     # self-hosted: backing is in this dir's tree
            if ext_info: source = "local"
        elif target_oid in obj_map:
            ext_info = _home_streams(target_oid).get(stream_idx)  # resolve from the HOME tree (authoritative)
            if ext_info: source = "remote"
        info = {
            "name": name, "stream_idx": stream_idx, "target_oid": target_oid,
            "file_size": file_size, "alloc_size": alloc_size,
            "file_attrs": file_attrs, "timestamps": ts,
            "extents": ext_info["extents"] if ext_info else [],
            "storage": "non-resident",
            "extent_source": source if ext_info else "unresolved",
            "ads": [],
        }
        for ext in info["extents"]:
            ext["disk_offset"] = ps + ext["plcn"] * cs
        results.append(info)

    for name, vd in resident_files:
        file_size = get_resident_file_size(vd)
        alloc_size = 0
        file_attrs = le32(vd, 0x48) if len(vd) >= 0x4C else 0
        ts = ([le64(vd, 0x28), le64(vd, 0x30), le64(vd, 0x38), le64(vd, 0x40)]
              if len(vd) >= 0x48 else [])
        extents = []
        if alloc_size >= cs and len(vd) > 0xA8:
            needed = (alloc_size + cs - 1) // cs
            ext_info = {"extents": []}
            _find_extents_in_subrecord(vd, 0xA8, len(vd) - 0xA8, needed, tr, cs, ext_info)
            extents = ext_info["extents"]
            for ext in extents:
                ext["disk_offset"] = ps + ext["plcn"] * cs
        ads_list = _parse_ads_from_value(vd) if len(vd) > 0xA8 else []
        entry = {
            "name": name, "file_size": file_size, "alloc_size": alloc_size,
            "storage": "resident", "extents": extents,
            "file_attrs": file_attrs, "timestamps": ts,
            "ads": ads_list,
            # Q7: inline $DATA bytes so `extract` can write a resident file's content (None if non-inline).
            "resident_content": get_resident_data_content(vd),
            # F5: a "long value" whose current stream is extent-backed is really non-resident (its bytes live
            # on disk, held by an inline 0x10028 holder we don't yet reassemble) — flagged so `extract` is
            # honest and consistent with `files` (which reports IsResident=False for it).
            "extent_backed": _current_stream_extent_backed(vd),
            # Q7/CoW: a resident file with no plain-inline $DATA may be UNMODIFIED since a snapshot — its live
            # bytes are shared with the newest snapshot. Recover them (safe case only; None otherwise).
            "cow_content": (recover_cow_current_content(f, ps, cs, tr, vd)
                            if get_resident_data_content(vd) is None
                            and not _current_stream_extent_backed(vd) else None),
        }
        results.append(entry)
    return results

def _parse_dir_entries(f, ps, cs, tr, vlcns):
    """Walk a directory object's B+ tree and extract type-0x30 entries."""
    rows = walk_bplus(f, ps, cs, tr, vlcns)
    entries = []
    for kd, vd in rows:
        if len(kd) < 4: continue
        attr_type = le16(kd, 0)
        if attr_type != 0x30: continue
        flags = le16(kd, 2)
        try: name = kd[4:].decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError: name = kd[4:].hex()

        if len(vd) <= 84:
            file_id = le64(vd, 0x00) if len(vd) >= 8 else 0   # F6: per-dir child ordinal (hard-link grouping)
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            create_time = le64(vd, 0x10) if len(vd) >= 0x18 else 0
            modify_time = le64(vd, 0x18) if len(vd) >= 0x20 else 0
            change_time = le64(vd, 0x20) if len(vd) >= 0x28 else 0
            access_time = le64(vd, 0x28) if len(vd) >= 0x30 else 0
            file_attrs = le32(vd, 0x40) if len(vd) >= 0x44 else 0
            file_size = le64(vd, 0x38) if len(vd) >= 0x40 else 0
            is_dir = bool(file_attrs & 0x10000000)
            resident = False
            # val+0x08 is the child's own OID only for a SUBDIRECTORY; a non-resident FILE has the
            # home-dir backref there (not its own OID -- files have no own OID). Keep child_oid = own
            # OID for dirs (drives recursion); expose 0 for files and keep the backref aside. --oid bug.
            home_oid = 0 if is_dir else child_oid
            if not is_dir:
                child_oid = 0
        else:
            file_id = 0
            child_oid = 0
            home_oid = 0
            create_time = le64(vd, 0x28) if len(vd) >= 0x30 else 0
            modify_time = le64(vd, 0x30) if len(vd) >= 0x38 else 0
            change_time = le64(vd, 0x38) if len(vd) >= 0x40 else 0
            access_time = le64(vd, 0x40) if len(vd) >= 0x48 else 0
            file_attrs = le32(vd, 0x48) if len(vd) >= 0x4C else 0
            file_size = 0
            is_dir = False
            resident = True

        ads_list = _parse_ads_from_value(vd) if resident and len(vd) > 0xA8 else []
        entries.append({
            "name": name, "flags": flags, "child_oid": child_oid, "home_oid": home_oid, "file_id": file_id,
            "create_time": create_time, "modify_time": modify_time,
            "change_time": change_time, "access_time": access_time,
            "file_attrs": file_attrs, "file_size": file_size,
            "is_dir": is_dir, "resident": resident, "value_len": len(vd),
            "raw_value": vd, "ads": ads_list,
        })
    return entries

def _walk_dir_tree(f, ps, cs, tr, obj_map, oid, path, depth, max_depth, results):
    """Recursively walk directory tree, collecting entries."""
    if oid not in obj_map: return
    try: entries = _parse_dir_entries(f, ps, cs, tr, obj_map[oid])
    except Exception: return
    for entry in entries:
        child_path = f"{path}/{entry['name']}" if path else entry["name"]
        entry_type = "DIR " if entry["is_dir"] else "FILE"
        results.append({
            "path": child_path, "type": entry_type,
            "oid": entry["child_oid"], **entry,
        })
        if entry["is_dir"] and depth < max_depth and entry["child_oid"] in obj_map:
            _walk_dir_tree(f, ps, cs, tr, obj_map, entry["child_oid"],
                           child_path, depth + 1, max_depth, results)

def _walk_dir_files_with_sid(f, ps, cs, tr, obj_map, oid, path, depth, max_depth):
    """List {name, security_id, file_attrs, is_dir} for every entry under `oid`.

    Delegates to the shared walk_directory_tree(enrich=True) so SecurityId is resolved correctly for EVERY
    entry type — resident files (value+0x50), **directories** (their own type-0x10 $SI), and **non-resident
    files** (their type-0x40 backing record +0x50). The previous per-row reader unconditionally set
    security_id=0 for every <=84-byte value, i.e. for ALL directories and non-resident files (E006 +
    problem.md #3 fix, 2026-06-28). `path` prefixes the names so the recursive signature stays compatible."""
    if oid not in obj_map:
        return []
    prefix = (path + "/") if path else ""
    out = []
    for e in walk_directory_tree(f, ps, cs, tr, obj_map, oid, max_depth, True, set()):
        out.append({"name": prefix + e["path"],
                    "security_id": e.get("security_id", 0) or 0,
                    "file_attrs": e.get("file_attrs", 0),
                    "is_dir": e.get("is_dir", False)})
    return out

def _ts_vol_times(f, ps, cs, tr, obj_map):
    """Volume creation/last-modify FILETIMEs from OID 0x500, key-type 0x520 (val+0x90/0xA0)."""
    if 0x500 in obj_map:
        try:
            for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x500]):
                if len(kd) >= 2 and le16(kd, 0) == 0x520 and len(vd) >= 0xA8:
                    return le64(vd, 0x90), le64(vd, 0xA0)
        except Exception:
            pass
    return 0, 0

def cmd_timestomp(image, remaining, partition_start):
    """Detect files whose $SI timestamps are inconsistent with the file's real
    history on this volume — the ReFS timestomping check. Combines:
      • intrinsic $SI signals (CHANGE_LATE / PRE_FORMAT / CREATE_GT_MODIFY / FUTURE)
      • the USN journal (authoritative): a standalone BASIC_INFO_CHANGE record is a
        deliberate timestamp/attribute edit with no content change; FILE_CREATE gives
        the true creation time to compare against $SI.
    Confidence tiers HIGH/MEDIUM/LOW reflect how many independent sources agree."""
    import csv as _csv
    args = _parse_args(remaining, flags=["--all", "--json"], valued=["--csv", "--min", "--margin-days", "--depth"])
    do_json = args["json"]
    show_all = args["all"]
    min_conf = (args["min"] or "LOW").upper()
    margin = int(args["margin_days"]) * 24 * 3600 * 10**7 if args["margin_days"] else TS_MARGIN_100NS
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 20
    csv_arg = args["csv"] if args["csv"] is not None else None
    rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        vol_create, vol_modify = _ts_vol_times(f, ps, cs, tr, obj_map)

        # Walk every file (raw MACB).
        results = []
        _walk_dir_tree(f, ps, cs, tr, obj_map, 0x600, "", 0, max_depth, results)
        files = [r for r in results if r.get("type") == "FILE"]

        # USN journal (optional, authoritative when present).
        usn_create = {}        # unique filename -> [FILETIME of FILE_CREATE]
        bic_names = set()      # filenames with a standalone BASIC_INFO_CHANGE (reason == 0x8000)
        name_count = {}
        for r in files:
            name_count[r["name"]] = name_count.get(r["name"], 0) + 1
        journal = False
        try:
            vd, _meta = locate_change_journal(f, ps, cs, tr, obj_map)
            if vd is not None:
                streams = parse_usn_journal_streams(vd, cs, tr)
                if streams.get("j_extents"):
                    j_data = read_usn_j_stream(f, ps, cs, streams["j_extents"], streams["j_stream_size"])
                    recs = parse_usn_records(j_data)
                    journal = True
                    tmp = {}
                    for rec in recs:
                        if rec.reason & 0x00000100:  # FILE_CREATE
                            tmp.setdefault(rec.filename, []).append(rec.timestamp)
                        if rec.reason == 0x00008000 and rec.filename:  # standalone BASIC_INFO_CHANGE
                            bic_names.add(rec.filename)
                    usn_create = tmp
        except Exception:
            journal = False

        # F6: HARDLINK_MACB_MISMATCH — a ReFS-native, JOURNAL-INDEPENDENT timestomp signal. On ReFS $SI is stored
        # per-name-entry (per hard-link), NOT per-inode as on NTFS: a name-scoped SetFileTime rewrites only the
        # opened name (and the shared backing), while sibling hard-link names keep the TRUE birth. So two names of
        # one file (same home_oid + file_id) whose Created diverges reveal the stomp, and the LATEST Created is the
        # authentic birth. We flag only the backdated name(s), never the clean sibling (no false positive).
        # RD-proven on win11refs8g.raw File ID 0x1e: f6.bin Created 2011 vs f6_link.bin Created 2026 (E59 / FN_LINK_003).
        hl_groups = {}
        for r in files:
            if r.get("resident") or r.get("is_dir"):
                continue
            key = (r.get("home_oid", 0), r.get("file_id", 0))
            if key == (0, 0):
                continue
            hl_groups.setdefault(key, []).append(r)
        hl_mismatch = {}     # id(r) -> authentic (latest) Created among its hard-link siblings
        for members in hl_groups.values():
            valid = [m for m in members if _ft_valid(m.get("create_time", 0))]
            if len(valid) < 2:
                continue
            authentic = max(m["create_time"] for m in valid)
            for m in valid:
                if authentic - m["create_time"] > margin:
                    hl_mismatch[id(m)] = authentic

        def _classify(r):
            ct, mt = r.get("create_time", 0), r.get("modify_time", 0)
            chg, acc = r.get("change_time", 0), r.get("access_time", 0)
            flags = timestomp_intrinsic_flags(ct, mt, chg, acc, vol_create, vol_modify, margin)
            evidence = list(flags)
            # F6: sibling hard-link preserves the true birth -> journal-independent structural proof.
            hl_conf = id(r) in hl_mismatch
            if hl_conf:
                evidence.append("HARDLINK_MACB_MISMATCH")
            # USN cross-checks (only when the filename is unambiguous among live files)
            usn_conf = False
            if journal and name_count.get(r["name"], 0) == 1:
                if r["name"] in bic_names and ("CHANGE_LATE" in flags or "PRE_FORMAT" in flags
                                               or "CREATE_GT_MODIFY" in flags):
                    evidence.append("USN_BASIC_INFO_CHANGE")
                    usn_conf = True
                cts = usn_create.get(r["name"])
                if cts and _ft_valid(ct):
                    if min(abs(ct - u) for u in cts) > margin:
                        evidence.append("USN_CREATE_MISMATCH")
                        usn_conf = True
            intrinsic = any(x in flags for x in ("CHANGE_LATE", "PRE_FORMAT", "CREATE_GT_MODIFY", "FUTURE"))
            # Tiering: independent-source agreement = higher confidence.
            if (usn_conf or hl_conf) and intrinsic:
                tier = "HIGH"          # journal / hard-link sibling + intrinsic agree
            elif hl_conf:
                tier = "HIGH"          # F6: a sibling hard-link preserves the true birth (journal-independent proof)
            elif "CHANGE_LATE" in flags and "PRE_FORMAT" in flags:
                tier = "HIGH"          # two independent intrinsic signals
            elif usn_conf:
                tier = "HIGH"          # journal is authoritative
            elif "CHANGE_LATE" in flags or "PRE_FORMAT" in flags:
                tier = "MEDIUM"        # one solid signal (benign-copy caveat applies)
            elif intrinsic:
                tier = "LOW"           # FUTURE / CREATE_GT_MODIFY alone (weak, copy-plausible)
            else:
                tier = "NONE"
            return tier, evidence

        rows = []
        for r in files:
            tier, evidence = _classify(r)
            if tier == "NONE" and not show_all:
                continue
            rows.append({
                "path": r["path"], "oid": _hx(r["oid"]) if r.get("oid") else ("(resident)" if r.get("resident") else "(non-res)"),
                "tier": tier, "signals": evidence,
                "created": _filetime_to_str(r.get("create_time", 0)).replace(" UTC", ""),
                "modified": _filetime_to_str(r.get("modify_time", 0)).replace(" UTC", ""),
                "changed": _filetime_to_str(r.get("change_time", 0)).replace(" UTC", ""),
                "accessed": _filetime_to_str(r.get("access_time", 0)).replace(" UTC", ""),
            })
        # sort by confidence then path
        rows.sort(key=lambda x: (-rank[x["tier"]], x["path"]))
        flagged = [x for x in rows if x["tier"] != "NONE"]
        suspects = [x for x in flagged if rank[x["tier"]] >= rank.get(min_conf, 1)]
        counts = {t: sum(1 for x in flagged if x["tier"] == t) for t in ("HIGH", "MEDIUM", "LOW")}

        if csv_arg is not None:
            def _w(out):
                w = _csv.writer(out)
                w.writerow(["path", "oid", "confidence", "signals", "created", "modified", "changed", "accessed"])
                for x in (rows if show_all else suspects):
                    w.writerow([x["path"], x["oid"], x["tier"], "|".join(x["signals"]),
                                x["created"], x["modified"], x["changed"], x["accessed"]])
            if csv_arg == "-":
                _w(sys.stdout)
            else:
                with open(csv_arg, "w", newline="") as out:
                    _w(out)
                print(f"Wrote {len(suspects)} rows to {csv_arg}")
            return 0

        if do_json:
            print(json.dumps({
                "image": os.path.basename(image), "refs_version": f"{vmaj}.{vmin}",
                "volume_create": _filetime_to_str(vol_create).replace(" UTC", ""),
                "volume_modify": _filetime_to_str(vol_modify).replace(" UTC", ""),
                "journal_present": journal, "files_examined": len(files),
                "counts": counts, "suspects": suspects if not show_all else rows,
            }, indent=2))
            return 0

        W = 78
        print("=" * W)
        print("ReFS Timestamp-Anomaly (Timestomp) Detection")
        print("=" * W)
        print(f"  Image:           {os.path.basename(image)}  (ReFS {vmaj}.{vmin})")
        print(f"  Volume created:  {_filetime_to_str(vol_create).replace(' UTC','')}")
        print(f"  Volume modified: {_filetime_to_str(vol_modify).replace(' UTC','')}")
        print(f"  USN journal:     {'present (authoritative cross-check ON)' if journal else 'absent (intrinsic signals only)'}")
        print(f"  Files examined:  {len(files)}")
        print(f"  Flagged:         {len(flagged)}  (HIGH {counts['HIGH']} / MEDIUM {counts['MEDIUM']} / LOW {counts['LOW']})")
        print()
        print("  This flags timestamps that LOOK anomalous — it is investigative INFORMATION, not proof of")
        print("  tampering. Weigh the BASIS of each row: a journal/hardlink signal is authoritative; an")
        print("  intrinsic ($SI-only) signal is a heuristic that also fires on legitimate timestamp-preserving")
        print("  copies/restores. Tiers: HIGH = >=2 independent signals or 1 authoritative; MEDIUM = 1 strong")
        print("  intrinsic; LOW = a weak/single hint.")
        print()
        if not suspects and not show_all:
            print("  No timestamp anomalies at or above the requested confidence.")
            return 0
        _AUTH_SIGS = {"USN_BASIC_INFO_CHANGE", "USN_CREATE_MISMATCH", "HARDLINK_MACB_MISMATCH"}
        print(f"  {'Conf':<6} {'Basis':<13} {'Claimed birth':<21} {'Last real write':<21} Path")
        print(f"  {'-'*96}")
        for x in (rows if show_all else suspects):
            sigs = x["signals"]
            basis = "journal/link" if any(s in _AUTH_SIGS for s in sigs) else "intrinsic"
            print(f"  {x['tier']:<6} {basis:<13} {x['created']:<21} {x['changed']:<21} {x['path']}")
            print(f"  {'':<6} signals: {', '.join(sigs) or '(none)'}")
        print()
        print("  Signal legend  (AUTHORITATIVE = independent evidence · HEURISTIC = suggestive $SI-only):")
        print("    [AUTHORITATIVE]")
        print("      USN_BASIC_INFO_CHANGE  the USN journal recorded a deliberate basic-info edit (no content change)")
        print("      USN_CREATE_MISMATCH    $SI created differs from the FILE_CREATE journal record (true birth known)")
        print("      HARDLINK_MACB_MISMATCH one hard-link name's $SI created diverges from a sibling's (ReFS per-name")
        print("                             MACB); the LATEST sibling created is the authentic birth — only the")
        print("                             back-dated name is flagged, never the clean sibling")
        print("    [HEURISTIC — $SI only, corroborate]")
        print("      CHANGE_LATE            $SI change-time post-dates created/modified (SetFileTime/PowerShell/.NET")
        print("                             can't reach change-time) — defeated by a native-API/raw-disk stomp")
        print("      PRE_FORMAT / FUTURE    created before the volume existed / after its last write")
        print("      CREATE_GT_MODIFY       created after last write")
        print("  Note: the intrinsic signals also fire on legitimate creation-time-preserving copies")
        print("  (robocopy /COPY:T, restore), so an intrinsic-only HIGH is not proof — corroborate.")
        return 0
    finally:
        f.close()

def cmd_extract(image, remaining, partition_start):
    args = _parse_args(remaining, valued=["--oid", "--depth", "--path", "-o", "--output"])
    # accept a bare name, an absolute /dir/file path, or --path (symmetric with `details`)
    filename = args["path"] or (args["_rest"][0] if args["_rest"] else None)
    start_oid = _int_arg(args["oid"], "--oid", 0) if args["oid"] else 0x600
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 3
    outp = args["o"] or args["output"]

    def _emit(data):
        # Q2 UX: -o FILE saves the bytes; otherwise write to stdout and hint how to save.
        if outp:
            with open(outp, "wb") as _fh:
                _fh.write(data)
            print(f"[{PROG}] wrote {len(data)} bytes to {outp}", file=sys.stderr)
        else:
            sys.stdout.buffer.write(data)
            if data:
                print(f"[{PROG}] ({len(data)} bytes to stdout — add `-o FILE` to save to a file)",
                      file=sys.stderr)

    if not filename:
        die("extract requires a filename argument")

    stream_name = None
    if ":" in filename:
        parts = filename.rsplit(":", 1)
        if parts[1]:
            filename, stream_name = parts[0], parts[1]

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        if start_oid not in obj_map:
            die(f"OID {_hx(start_oid)} not found in Object Table")

        all_results = []

        def process_dir(dir_oid, path, depth):
            results = _analyze_dir_extents(f, ps, cs, tr, obj_map, dir_oid)
            for info in results:
                full_path = f"{path}/{info['name']}" if path else info['name']
                info["path"] = full_path
                all_results.append(info)
            if depth > 0:
                dir_rows = walk_bplus(f, ps, cs, tr, obj_map[dir_oid])
                for kd, vd in dir_rows:
                    if len(kd) >= 4 and le16(kd, 0) == 0x30 and len(vd) >= 0x44:
                        child_attrs = le32(vd, 0x40)
                        if child_attrs & 0x10000000:
                            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
                            if child_oid and child_oid in obj_map:
                                child_name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
                                child_path = f"{path}/{child_name}" if path else child_name
                                process_dir(child_oid, child_path, depth - 1)

        process_dir(start_oid, "", max_depth)

        # strip a leading slash so an absolute /dir/file path matches the stored relative path; match on
        # a component boundary ("/"+fn) so "file.txt" no longer also matches "myfile.txt".
        fn = filename.lstrip("/")
        target = None
        for info in all_results:
            p = info.get("path", "")
            if info["name"] == fn or p == fn or p.endswith("/" + fn):
                target = info
                break

        if not target:
            die(f"file '{filename}' not found")

        if stream_name:
            ads_match = None
            for ads in target.get("ads", []):
                if ads["name"] == stream_name:
                    ads_match = ads
                    break
            if not ads_match:
                die(f"ADS '{stream_name}' not found on '{target['name']}'")
            if ads_match["storage"] == "inline":
                content = ads_match.get("content")
                if content is None:
                    die(f"ADS '{stream_name}' has no extractable content")
                print(f"Extracting '{target['name']}:{stream_name}' ({len(content)} bytes):", file=sys.stderr)
                _emit(content)
                return 0
            if ads_match["storage"] == "extent-backed" and ads_match.get("extents"):
                # E61: a large (>=2 KB) non-resident ADS — content in on-disk extents (type-0x0 record).
                buf = _read_vlcn_extents(f, ps, cs, tr, ads_match["extents"], ads_match["stream_size"])
                print(f"Extracting '{target['name']}:{stream_name}' ({len(buf)} bytes — non-resident ADS, "
                      f"{len(ads_match['extents'])} extents):", file=sys.stderr)
                if target.get("file_attrs", 0) & 0x4000:
                    print(f"[{PROG}] WARNING: host is EFS-encrypted — ADS bytes are CIPHERTEXT.", file=sys.stderr)
                _emit(buf)
                return 0
            die(f"ADS '{stream_name}' storage is '{ads_match['storage']}' — its content is not inline in the "
                f"directory value and no extent list was found, so it cannot be extracted from this record")

        if target["storage"] == "resident" and not target["extents"]:
            if target.get("file_size", 0) == 0:
                print(f"Extracting '{target['name']}' (0 bytes — empty resident file):", file=sys.stderr)
                return 0
            # Q7: resident files store their $DATA inline in the directory value — write those bytes.
            content = target.get("resident_content")
            if content is not None:
                fsz = target.get("file_size", 0)
                print(f"Extracting '{target['name']}' ({len(content)} bytes — resident/inline):", file=sys.stderr)
                if len(content) != fsz:
                    print(f"[{PROG}] WARNING: inline content is {len(content)} bytes but $DATA size is {fsz} "
                          f"— verify before relying on the output.", file=sys.stderr)
                _emit(content)
                return 0
            # Q7/CoW: a resident file unmodified since a snapshot keeps its live bytes shared with the newest
            # snapshot (current 0x10028 holder has disk_alloc==0). Recovered via the tested snapshot extractor.
            cow = target.get("cow_content")
            if cow is not None:
                fsz = target.get("file_size", 0)
                print(f"Extracting '{target['name']}' ({len(cow)} bytes — resident, shared with latest snapshot):",
                      file=sys.stderr)
                if len(cow) != fsz:
                    print(f"[{PROG}] WARNING: recovered {len(cow)} bytes but $DATA size is {fsz} — verify.",
                          file=sys.stderr)
                _emit(cow)
                return 0
            # Fell through: the $DATA is not a plain inline stream.
            if target.get("extent_backed"):
                # Non-resident file whose extent list is held inline in the directory value (0x10028 holder) —
                # consistent with `files` reporting IsResident=False. Reassembly from the inline holder is not
                # yet wired (esp. sparse files); point the examiner at the extent map.
                print(f"File '{target['name']}' is NON-RESIDENT — its $DATA is stored in on-disk extents held "
                      f"inline in the directory value ({target.get('file_size',0)} bytes). Reassembly from the "
                      f"inline extent-list is not yet supported; use `dataruns` for the extent map.", file=sys.stderr)
                return 1
            # A CoW'd / snapshotted resident file keeps its live bytes in a 0x10028 holder.
            print(f"File '{target['name']}' is resident but its $DATA is not a plain inline stream "
                  f"({target.get('file_size',0)} bytes) — for a CoW/snapshotted file use `snapshots --extract`.",
                  file=sys.stderr)
            return 1

        if not target["extents"]:
            die(f"no extents decoded for '{target['name']}'")

        # Q6: EFS guard — extracted bytes of an encrypted file are ciphertext, not plaintext.
        if target.get("file_attrs", 0) & 0x4000:
            print(f"WARNING: '{target['name']}' is EFS-encrypted (FILE_ATTRIBUTE_ENCRYPTED). "
                  "The extracted bytes are CIPHERTEXT — plaintext recovery needs the user's RSA "
                  "private key (off-volume; see docs/attributes/EFS.md).", file=sys.stderr)

        print(f"Extracting '{target['name']}' ({target.get('file_size',0)} bytes):", file=sys.stderr)
        sorted_exts = sorted(target["extents"], key=lambda e: e["file_vcn"])
        file_size = target.get("file_size", 0)
        alloc = max(e["file_vcn"] + e["clusters"] for e in sorted_exts) * cs
        if alloc > 4 * 1024 * 1024 * 1024:
            die(f"file allocation size {alloc} bytes exceeds 4 GiB safety limit")
        buf = bytearray(alloc)
        for ext in sorted_exts:
            plcn = ext["plcn"]
            for i in range(ext["clusters"]):
                f.seek(ps + (plcn + i) * cs)
                chunk = f.read(cs)
                offset = (ext["file_vcn"] + i) * cs
                buf[offset:offset + cs] = chunk
        # E8: signal a short read — the decoded extents cover fewer bytes than the declared file_size.
        # Emitted to stderr (not an error/exit change) because a legitimately SPARSE file also has
        # allocation < size; the examiner must decide. Byte output is unchanged (the covered bytes).
        written = min(file_size, len(buf))
        if written < file_size:
            print(f"[{PROG}] WARNING: extracted {written} of {file_size} declared bytes for "
                  f"'{target['name']}' — decoded extents cover less than the file size (coverage gap "
                  f"or a sparse file). Verify before relying on the output.", file=sys.stderr)
        _emit(bytes(buf[:file_size]))

        return 0

    finally:
        f.close()

# ─── $RECYCLE.BIN ($I metadata) — F8 ─────────────────────────────────────────
def _decode_recycle_i(data):
    """Decode a Windows $I recycle-bin metadata file. Returns a dict or None.
    Format 2 (Win10/11): u64 header(=2)@0x00, u64 original size@0x08, u64 deletion FILETIME@0x10,
    u32 path length in WCHARs incl NUL@0x18, UTF-16LE original path@0x1C.
    Format 1 (Vista-8.1): u64 header(=1)@0x00, size@0x08, deletion FILETIME@0x10, fixed 260-WCHAR path@0x18."""
    if data is None or len(data) < 0x18:
        return None
    header = le64(data, 0x00)
    if header not in (1, 2):
        return None
    size = le64(data, 0x08)
    del_ft = le64(data, 0x10)
    if header == 2:
        if len(data) < 0x1C:
            return None
        nchars = le32(data, 0x18)
        raw = data[0x1C:0x1C + nchars * 2]
    else:
        raw = data[0x18:0x18 + 260 * 2]
    orig = raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]
    return {"header": header, "size": size, "deletion_time": del_ft, "original_path": orig}


def _walk_recycle(f, ps, cs, tr, obj_map, dir_oid, sid, depth, out):
    """Descend the $RECYCLE.BIN subtree, decoding $I rows inline (the SID is the top-level subfolder name)."""
    if depth < 0 or dir_oid not in obj_map:
        return
    child_dirs = []; names_here = set(); i_rows = []
    for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[dir_oid]):
        if len(kd) < 4 or le16(kd, 0) != 0x30:
            continue
        name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
        names_here.add(name)
        # file_attrs live at value+0x40 in the NON-resident (<=84 B) layout but at value+0x48 in the
        # resident (>84 B) layout — the $I metadata files are RESIDENT, so reading +0x40 for them gets
        # garbage and can wrongly set the directory bit (dropped $I6O4T60.md). Use the right offset.
        if len(vd) <= NON_RESIDENT_MAX_VALUE:
            attrs = le32(vd, 0x40) if len(vd) >= 0x44 else 0
        else:
            attrs = le32(vd, 0x48) if len(vd) >= 0x4C else 0
        if attrs & 0x10000000:
            child_dirs.append((le64(vd, 0x08) if len(vd) >= 0x10 else 0, name))
        elif name.startswith("$I"):
            i_rows.append((name, bytes(vd)))
    for name, vd in i_rows:
        meta = _decode_recycle_i(get_resident_data_content(vd)) if len(vd) > 84 else None
        r_name = "$R" + name[2:]
        out.append({"sid": sid, "i_name": name, "r_name": r_name,
                    "r_present": r_name in names_here, "meta": meta})
    for child_oid, cname in child_dirs:
        _walk_recycle(f, ps, cs, tr, obj_map, child_oid, sid or cname, depth - 1, out)


def cmd_recyclebin(image, remaining, partition_start):
    """F8: decode $RECYCLE.BIN $I metadata files -> original path + deletion time + size, and whether the
    $R payload survives. The $I is a small resident file, so its bytes come from the same inline-$DATA path
    as `extract`."""
    args = _parse_args(remaining, flags=["--json"])
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))
    try:
        recycle_oid = None
        if 0x600 in obj_map:
            for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x600]):
                if len(kd) >= 4 and le16(kd, 0) == 0x30 and len(vd) >= 0x10:
                    if kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00") == "$RECYCLE.BIN":
                        recycle_oid = le64(vd, 0x08); break
        recs = []
        if recycle_oid is not None:
            _walk_recycle(f, ps, cs, tr, obj_map, recycle_oid, "", 8, recs)

        if args["json"]:
            out = [{"sid": r["sid"], "i_file": r["i_name"], "r_file": r["r_name"],
                    "r_present": r["r_present"], "decoded": r["meta"] is not None,
                    "original_path": r["meta"]["original_path"] if r["meta"] else None,
                    "deletion_time": filetime_to_iso(r["meta"]["deletion_time"]) if r["meta"] else None,
                    "size": r["meta"]["size"] if r["meta"] else None} for r in recs]
            print(json.dumps(out, indent=2, ensure_ascii=False)); return 0

        print("=" * 78)
        print(f"ReFS $RECYCLE.BIN — deleted-to-recycle-bin items ({os.path.basename(image)})")
        print("=" * 78)
        if recycle_oid is None:
            print("  No $RECYCLE.BIN directory on this volume."); return 0
        if not recs:
            print("  $RECYCLE.BIN present but holds no $I metadata files (recycle bin empty)."); return 0
        recs.sort(key=lambda r: (filetime_to_iso(r["meta"]["deletion_time"]) if r["meta"] else ""))
        for r in recs:
            print(f"\n  {r['i_name']}   (SID {r['sid'] or '?'})")
            m = r["meta"]
            if m:
                print(f"    Original path:  {m['original_path']}")
                print(f"    Deleted:        {filetime_to_iso(m['deletion_time'])}")
                print(f"    Size:           {m['size']:,} bytes")
            else:
                print(f"    ($I content could not be decoded from a plain inline record)")
            print(f"    Payload ({r['r_name']}): {'present' if r['r_present'] else 'MISSING (metadata only)'}")
        print(f"\n  {len(recs)} recycled item(s).")
        return 0
    finally:
        f.close()

def cmd_security(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "--verbose", "--files", "--json", "--audit"], valued=["--sid", "--file"])
    verbose = args["v"] or args["verbose"]

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        descriptors, error = _parse_sd_stream(f, ps, cs, tr, obj_map)
        if error:
            print(f"ERROR: {error}", file=sys.stderr); return 1
        sd_by_id = {sd.get("security_id", 0): sd for sd in descriptors}
        sid_filter = _int_arg(args["sid"], "--sid", 0) if args["sid"] else None

        if args["audit"]:
            # Q4: one-shot content-addressed-hash audit (tamper check) over every descriptor.
            checked = [sd for sd in descriptors if "hash_valid" in sd]
            failures = [sd for sd in checked if not sd["hash_valid"]]
            print("=" * 78)
            print(f"ReFS Security Descriptor Hash Audit — {os.path.basename(image)}")
            print("=" * 78)
            print(f"  Descriptors: {len(descriptors)}  (hash-checked: {len(checked)})")
            if not failures:
                print(f"  VERDICT: CLEAN — 0/{len(checked)} descriptors fail the content-addressed hash")
            else:
                print(f"  VERDICT: *** {len(failures)}/{len(checked)} FAIL the hash — possible tampering ***")
                for sd in failures:
                    print(f"    SecurityId {_hx(sd.get('security_id',0))}: stored {_hx(sd.get('sd_hash',0))} "
                          f"!= computed {_hx(sd.get('computed_hash',0))}")
            return 0 if not failures else 2

        if args["json"]:
            output = {"security_descriptors": [{k: v for k, v in sd.items() if k != "raw"} for sd in descriptors]}
            if args["files"] or args["file"]:
                files = _walk_dir_files_with_sid(f, ps, cs, tr, obj_map, 0x600, "", 0, 10)
                if args["file"]:
                    fl = args["file"].lower()
                    files = [fe for fe in files if fl in fe["name"].lower()]
                output["file_mappings"] = files
            print(json.dumps(output, indent=2, default=str))
            return 0

        print("=" * 78)
        print("ReFS Security Descriptors")
        print("=" * 78)
        print(f"  Image:        {image}")
        print(f"  ReFS version: {vmaj}.{vmin}")

        if sid_filter is not None:
            if sid_filter in sd_by_id:
                print(f"\nSecurity Descriptor for SecurityId {_hx(sid_filter)}:")
                _print_sd(sd_by_id[sid_filter], verbose=verbose)
            else:
                found = False
                for sd in descriptors:
                    if sd.get("security_id") == sid_filter:
                        print(f"\nSecurity Descriptor for SecurityId {_hx(sid_filter)}:")
                        _print_sd(sd, verbose=verbose); found = True; break
                if not found:
                    print(f"\n  SecurityId {_hx(sid_filter)} not found in OID 0x530")
                    print(f"  Available SecurityIds: {', '.join(_hx(sd.get('security_id', 0)) for sd in descriptors[:20])}")
        elif args["files"] or args["file"]:
            files = _walk_dir_files_with_sid(f, ps, cs, tr, obj_map, 0x600, "", 0, 10)
            if args["file"]:
                fl = args["file"].lower()
                files = [fe for fe in files if fl in fe["name"].lower()]
            if not files:
                print(f"\n  No files found" + (f" matching '{args['file']}'" if args["file"] else ""))
            else:
                # Q7: per-owner-SID file-count summary BEFORE the (long) per-file list.
                sid_counts = {}
                for fe in files:
                    sid_counts[fe["security_id"]] = sid_counts.get(fe["security_id"], 0) + 1
                print(f"\n  Files per owner SID ({len(sid_counts)} distinct SID(s)):")
                print(f"    {'SecurityId':<14} {'Files':>7}   Owner")
                print(f"  {'-'*76}")
                for sid, n in sorted(sid_counts.items(), key=lambda kv: (-kv[1], kv[0])):
                    owner = sd_by_id[sid].get("owner_name", "(none)") if sid in sd_by_id else "(unknown)"
                    print(f"    {_hx(sid):<14} {n:>7}   {owner}")
                print(f"  {'-'*76}")
                print(f"    Total: {len(files)} files across {len(sid_counts)} owner SID(s)")

                print(f"\n  {'Name':<40} {'Type':<6} {'SecurityId':<14} {'Owner'}")
                print(f"  {'-'*76}")
                for fe in files:
                    sid = fe["security_id"]
                    ftype = "DIR" if fe["is_dir"] else "FILE"
                    owner = sd_by_id[sid].get("owner_name", "(none)") if sid in sd_by_id else "(unknown)"
                    print(f"  {fe['name']:<40} {ftype:<6} {_hx(sid):<14} {owner}")
                if verbose:
                    unique_sids = set(fe["security_id"] for fe in files)
                    print(f"\n  Referenced Security Descriptors ({len(unique_sids)} unique):")
                    for sid in sorted(unique_sids):
                        if sid in sd_by_id:
                            print(); _print_sd(sd_by_id[sid], verbose=True)
        else:
            print(f"\n  Total security descriptors: {len(descriptors)}\n")
            for i, sd in enumerate(descriptors):
                _print_sd(sd, verbose=verbose, index=i); print()

        if sid_filter is None and not args["file"]:
            unique_owners = set()
            for sd in descriptors:
                owner = sd.get("owner", "")
                if owner and owner != "(none)": unique_owners.add(owner)
            print(f"  Summary:")
            print(f"    Total SDs:        {len(descriptors)}")
            print(f"    Unique owners:    {len(unique_owners)}")
            for owner in sorted(unique_owners):
                print(f"      {_sid_name(owner)}")

        return 0

    finally:
        f.close()


# ════════════════════════════════════════════════════════════════════════
#  Migrated forensic commands (Phase 4): reparse / deleted / snapshots / integrity / export / dataruns
#  Ported VERBATIM from refsanalysis (closure: reparse decoders, deleted/slack scanners, snapshot
#  parsers, page-checksum verifiers, data-run/export readers; _attrs_to_str/_tag_name over forefst's
#  canonical attrs_to_str/REPARSE_TAGS). Routed via FORENSIC_HANDLERS.
# ════════════════════════════════════════════════════════════════════════

_CT_ROOT_INDICES = {7, 8, 12}

_KNOWN_OIDS = {
    0x0007: "Upcase Table",
    0x0008: "Upcase Table (dup)",
    0x0009: "Logfile Information Table",
    0x000A: "Logfile Information (dup)",
    0x000D: "Trash Table",
    0x0030: "Session Activity Table",
    0x0500: "Volume Information",
    0x0501: "Volume Information (dup)",
    0x0520: "FS Metadata",
    0x0530: "Security Descriptor Stream",
    0x0540: "Reparse Point Index",
    0x0541: "Reparse Point Index (dup)",
    0x0600: "Root Directory",
}

_VALID_SIGS = {b"MSB+", b"CHKP", b"SUPB", b"MLog"}

def _attrs_to_str(attrs, full=True):
    # adapter over the canonical helper (hex render on no-flags = legacy refsanalysis behaviour)
    return attrs_to_str(attrs, full=full, hex_if_empty=True)

def _tag_name(tag):
    return REPARSE_TAGS.get(tag, f"Unknown(0x{tag:08x})")

def _decode_symlink(data, offset=0):
    if len(data) < offset + 20: return {"error": "Symlink data too short"}
    sub_off = le16(data, offset); sub_len = le16(data, offset + 2)
    print_off = le16(data, offset + 4); print_len = le16(data, offset + 6)
    flags = le32(data, offset + 8)
    buf_start = offset + 12
    result = {"flags": flags, "relative": bool(flags & 1)}
    if buf_start + sub_off + sub_len <= len(data) and sub_len > 0:
        result["substitute_name"] = data[buf_start+sub_off:buf_start+sub_off+sub_len].decode("utf-16-le", errors="replace")
    if buf_start + print_off + print_len <= len(data) and print_len > 0:
        result["print_name"] = data[buf_start+print_off:buf_start+print_off+print_len].decode("utf-16-le", errors="replace")
    return result

def _decode_mount_point(data, offset=0):
    if len(data) < offset + 16: return {"error": "Mount point data too short"}
    sub_off = le16(data, offset); sub_len = le16(data, offset + 2)
    print_off = le16(data, offset + 4); print_len = le16(data, offset + 6)
    buf_start = offset + 8
    result = {}
    if buf_start + sub_off + sub_len <= len(data) and sub_len > 0:
        result["substitute_name"] = data[buf_start+sub_off:buf_start+sub_off+sub_len].decode("utf-16-le", errors="replace")
    if buf_start + print_off + print_len <= len(data) and print_len > 0:
        result["print_name"] = data[buf_start+print_off:buf_start+print_off+print_len].decode("utf-16-le", errors="replace")
    return result

def _decode_lx_symlink(data, offset=0):
    if len(data) < offset + 4: return {"error": "LX symlink data too short"}
    lx_flags = le32(data, offset)
    target_bytes = data[offset+4:]
    if target_bytes and target_bytes[-1] == 0: target_bytes = target_bytes[:-1]
    try: target = target_bytes.decode("utf-8", errors="replace")
    except Exception: target = target_bytes.hex()
    return {"lx_flags": lx_flags, "target": target}

def _decode_reparse_data(tag, data):
    result = {"tag": tag, "tag_name": _tag_name(tag), "data_len": len(data)}
    if tag == 0xA000000C:
        result.update(_decode_symlink(data))
    elif tag == 0xA0000003:
        result.update(_decode_mount_point(data))
    elif tag == 0xA000001D:
        result.update(_decode_lx_symlink(data))
    elif tag == 0x80000024:
        result["note"] = "WSL LX_FIFO (named pipe)"
        if len(data) >= 8:
            result["dev_major"] = le32(data, 0); result["dev_minor"] = le32(data, 4)
    elif tag in (0x80000025, 0x80000026):
        result["note"] = "WSL special file (LX_CHR/LX_BLK character/block device)"
        if len(data) >= 8:
            result["dev_major"] = le32(data, 0); result["dev_minor"] = le32(data, 4)
    elif tag == 0x80000023:
        result["note"] = "WSL AF_UNIX (Unix domain socket)"
    elif tag == 0x80000013:
        result["note"] = "Data deduplication chunk store reference"
    elif tag == 0x80000017:
        result["note"] = "Windows Overlay Filter (WOF, compressed)"
    elif tag == 0x8000001B:
        result["note"] = "App execution alias (APPEXECLINK) -- Store app package + target exe"
    elif tag == 0x80000018:
        result["note"] = "Windows Container Isolation (WCI)"
    else:
        result["raw_hex"] = data[:64].hex() if data else ""
        if len(data) > 64: result["raw_hex"] += f"... ({len(data)} total bytes)"
    return result

def _extract_reparse_from_resident(vd):
    if len(vd) < 0xA8: return None
    off = 0xA8
    while off < len(vd) - 8:
        marker = le32(vd, off)
        if marker == 0x80000001:
            desc = le32(vd, off + 4)
            if desc == 0xC0:
                # Reparse sub-record: marker(4) + desc(4) + header(12) + REPARSE_DATA_BUFFER
                buf_off = off + 0x14
                if buf_off + 8 > len(vd):
                    break
                tag = le32(vd, buf_off)
                data_len = le16(vd, buf_off + 4)
                if tag in REPARSE_TAGS and 0 < data_len < len(vd) - buf_off - 8:
                    return _decode_reparse_data(tag, vd[buf_off+8:buf_off+8+data_len])
            # Skip to next marker
            off = _next_subrecord(vd, off + 8)
        elif marker == 0x80000002:
            off = _next_subrecord(vd, off + 8)
        else:
            off += 4
    return None

def _parse_reparse_index(f, ps, cs, tr, obj_map):
    if 0x540 not in obj_map:
        return [], "OID 0x540 (Reparse Point Index) not found"
    rows = walk_bplus(f, ps, cs, tr, obj_map[0x540])
    entries = []
    for kd, vd in rows:
        if len(kd) >= 24:
            # 24-byte key (driver-verified 2026-07-05, E2 + disk-verified): u32 marker 0x80000001 @0,
            # ReparseTag @4, then a 16-byte _REFS_FILE_REFERENCE = word0 @8 + OID @0x10. word0 is a small
            # entry ordinal (2..32 observed); the OID @0x10 is the reparse file's CONTAINING-DIRECTORY OID
            # (disk: every index OID matches a reparse file's parent OID — 242/242 across 3 images), NOT the
            # file's own OID (ReFS files have none). Together they are the file's 128-bit reference.
            # See structure_reference §C.8.
            entries.append({
                "reparse_tag": le32(kd, 4), "tag_name": _tag_name(le32(kd, 4)),
                "file_ref_word0": le64(kd, 8), "dir_oid": le64(kd, 16),
                "marker": le32(kd, 0),
                "key_hex": kd.hex(), "value_len": len(vd),
            })
        elif len(kd) >= 8:
            reparse_tag = le32(kd, 4) if len(kd) >= 8 else le32(kd, 0)
            entries.append({
                "reparse_tag": reparse_tag, "tag_name": _tag_name(reparse_tag),
                "key_hex": kd.hex(), "key_len": len(kd), "value_len": len(vd),
            })
    return entries, None

def _walk_dir_for_reparse(f, ps, cs, tr, obj_map, oid, path, depth, max_depth):
    if depth > max_depth or oid not in obj_map: return []
    rows = walk_bplus(f, ps, cs, tr, obj_map[oid])
    files = []
    for kd, vd in rows:
        if len(kd) < 4 or le16(kd, 0) != 0x30: continue
        name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
        full_path = f"{path}/{name}" if path else name
        if len(vd) <= 84:
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            is_dir = bool(le32(vd, 0x40) & 0x10000000) if len(vd) >= 0x44 else False
            if is_dir and child_oid and child_oid in obj_map:
                files.extend(_walk_dir_for_reparse(f, ps, cs, tr, obj_map, child_oid, full_path, depth + 1, max_depth))
            continue
        file_attrs = le32(vd, 0x48) if len(vd) >= 0x4C else 0
        has_reparse = bool(file_attrs & 0x0400)
        is_dir = bool(file_attrs & 0x10000000)
        entry = {
            "name": full_path, "file_attrs": file_attrs, "has_reparse": has_reparse,
            "is_dir": is_dir, "value_len": len(vd), "reparse_data": None, "wsl_eas": {},
        }
        if has_reparse and len(vd) >= 0xA8:
            entry["reparse_data"] = _extract_reparse_from_resident(vd)
        if file_attrs & 0x00040000:
            for search_off in range(0xA0, len(vd) - 20):
                if vd[search_off+8:search_off+11] == b"$LX":
                    eas = _parse_extended_attributes(vd[search_off:])
                    for ea in eas:
                        if ea["name"] == "$LXUID" and len(ea["value"]) >= 4: entry["wsl_eas"]["lxuid"] = le32(ea["value"], 0)
                        elif ea["name"] == "$LXGID" and len(ea["value"]) >= 4: entry["wsl_eas"]["lxgid"] = le32(ea["value"], 0)
                        elif ea["name"] == "$LXMOD" and len(ea["value"]) >= 4:
                            entry["wsl_eas"]["lxmod"] = le32(ea["value"], 0)
                            entry["wsl_eas"]["lxmod_str"] = f"{le32(ea['value'], 0):06o}"
                        elif ea["name"] == "$LXDEV" and len(ea["value"]) >= 8:
                            entry["wsl_eas"]["lxdev_major"] = le32(ea["value"], 0)
                            entry["wsl_eas"]["lxdev_minor"] = le32(ea["value"], 4)
                    break
        files.append(entry)
        if is_dir:
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            if child_oid and child_oid in obj_map:
                files.extend(_walk_dir_for_reparse(f, ps, cs, tr, obj_map, child_oid, full_path, depth + 1, max_depth))
    return files

def _classify_b0_entry(val_data):
    return 'TRUE_SNAPSHOT' if _is_snapshot_value(val_data) else 'ADS'

def _decode_dir_row_value(vd):
    """Decode a type-0x30 directory-entry VALUE into name/MACB/attrs metadata. Resident entries (>84 B)
    carry the inline $SI at value+0x28; non-resident entries carry timestamps at value+0x10."""
    e = {"value_len": len(vd), "resident": len(vd) > 84}
    # E1 fix: discriminate on >84 (NON_RESIDENT_MAX_VALUE), NOT >=0x50 — an 84-byte v3.10+/v3.14
    # NON-resident value (84>=0x50) previously took the resident branch and was mis-decoded with
    # resident offsets. Resident values are always >84; non-resident (72/84 B) use +0x10/+0x40 (§C.3).
    if len(vd) > 84:
        e["create_time"] = le64(vd, 0x28); e["modify_time"] = le64(vd, 0x30)
        e["change_time"] = le64(vd, 0x38); e["access_time"] = le64(vd, 0x40)
        e["file_attrs"] = le32(vd, 0x48); e["is_dir"] = bool(le32(vd, 0x48) & 0x10000000)
    elif len(vd) >= 0x44:
        e["child_oid"] = le64(vd, 0x08) if len(vd) >= 0x10 else 0
        e["create_time"] = le64(vd, 0x10); e["modify_time"] = le64(vd, 0x18)
        e["change_time"] = le64(vd, 0x20); e["access_time"] = le64(vd, 0x28)
        e["file_attrs"] = le32(vd, 0x40); e["is_dir"] = bool(le32(vd, 0x40) & 0x10000000)
    return e

def _next_subrecord(vd, start):
    for pos in range(start, len(vd) - 4, 4):
        m = le32(vd, pos)
        if m in (0x80000001, 0x80000002):
            return pos
    return len(vd)

def _parse_extended_attributes(data):
    """Parse Windows Extended Attributes (EA) chain from raw bytes."""
    eas = []
    offset = 0
    for _ in range(100):
        if offset + 8 > len(data): break
        next_off = le32(data, offset)
        ea_flags = data[offset + 4]
        name_len = data[offset + 5]
        value_len = le16(data, offset + 6)
        if name_len == 0 and value_len == 0: break
        name_start = offset + 8
        name_end = name_start + name_len
        if name_end >= len(data): break
        name = data[name_start:name_end].decode("ascii", errors="replace")
        value_start = name_end + 1
        value_end = value_start + value_len
        if value_end > len(data): break
        value = data[value_start:value_end]
        eas.append({"name": name, "value": value, "flags": ea_flags})
        if next_off == 0: break
        offset += next_off
    return eas

def _parse_snapshot_value(val_data, snap_name):
    info = {"name": snap_name, "raw_len": len(val_data),
            "is_true_snapshot": _classify_b0_entry(val_data) == 'TRUE_SNAPSHOT'}
    if len(val_data) >= 0x28: info["stream_size"] = le64(val_data, 0x20)
    if len(val_data) >= 0x30: info["allocation_size"] = le64(val_data, 0x28)
    if len(val_data) >= 0x38: info["snapshot_alloc"] = le64(val_data, 0x30)
    if len(val_data) >= 0x48: info["data_sub_id"] = le32(val_data, 0x44)
    if len(val_data) >= 0x4C:
        snap_id = le32(val_data, 0x48)
        if 0 < snap_id < 1000: info["snapshot_id"] = snap_id
    for off in [0x50, 0x48, 0x40, 0x58]:
        if off + 8 <= len(val_data):
            ft = le64(val_data, off)
            if 0x01D0000000000000 < ft < 0x01F0000000000000:
                info["creation_time"] = ft; break
    return info

def _parse_snapshots_from_value(vd):
    snapshots = []
    for kd, vd_row in parse_resident_btree_rows(vd):
        snap_name = _extract_snapshot_name(kd)
        if snap_name is not None:
            snapshots.append(_parse_snapshot_value(vd_row, snap_name))
    return snapshots

def _extract_snapshot_name(key_data):
    if len(key_data) < 18: return None
    if (key_data[8:12] == b'\x02\x00\x00\x80' and key_data[12] == 0xB0 and key_data[13] == 0x00 and le32(key_data, 4) == 0):
        name = key_data[16:].decode("utf-16-le", errors="replace").rstrip("\x00")
        if name and '\x00' not in name: return name
    return None

def _find_snapshot_files(f, ps, cs, tr, obj_map, oid, path, depth, max_depth, results):
    if depth > max_depth or oid not in obj_map: return
    rows = walk_bplus(f, ps, cs, tr, obj_map[oid])
    for kd, vd in rows:
        if len(kd) < 4 or le16(kd, 0) != 0x30: continue
        name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
        full_path = f"{path}/{name}" if path else name
        if len(vd) <= 84:
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            is_dir = bool(le32(vd, 0x40) & 0x10000000) if len(vd) >= 0x44 else False
            if is_dir and child_oid and child_oid in obj_map:
                _find_snapshot_files(f, ps, cs, tr, obj_map, child_oid, full_path, depth + 1, max_depth, results)
            # A non-resident FILE has no own OID/tree: val+0x08 is its home-dir backref, so scanning
            # obj_map[backref] returns the HOME DIRECTORY's $SNAPSHOT entries, not the file's -- a
            # file/dir mix. (The file's own CoW versions live in its type-0x40 extents, which this
            # snapshot-named-key scan does not match.) Skip rather than mis-attribute. --oid bug class.
        else:
            snapshots = _parse_snapshots_from_value(vd)
            if snapshots:
                file_info = {"path": full_path, "snapshots": snapshots, "value_len": len(vd), "vd": vd}
                if len(vd) >= 0x50:
                    file_info["create_time"] = le64(vd, 0x28); file_info["modify_time"] = le64(vd, 0x30)
                    file_info["file_size"] = get_resident_file_size(vd)
                results.append(file_info)

def _get_current_files(f, ps, cs, tr, obj_map, oid=0x600, path="", depth=0, max_depth=10):
    files = set()
    if depth > max_depth or oid not in obj_map: return files
    for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[oid]):
        if len(kd) < 4 or le16(kd, 0) != 0x30: continue
        name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
        files.add(name)
        if len(vd) >= 0x44 and len(vd) <= 84:
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            if bool(le32(vd, 0x40) & 0x10000000) and child_oid and child_oid in obj_map:
                full_path = f"{path}/{name}" if path else name
                files.update(_get_current_files(f, ps, cs, tr, obj_map, child_oid, full_path, depth + 1, max_depth))
    return files

def _scan_for_deleted_entries(f, ps, cs, tr, current_plcns, search_name=None, max_scan_clusters=50000):
    found = []
    image_size = f.seek(0, 2)
    vol_clusters = (image_size - ps) // cs
    max_clusters = min(vol_clusters, max_scan_clusters)
    print(f"  Scanning up to {max_clusters} clusters for orphaned MSB+ pages...")
    orphan_count = 0
    for cluster_idx in range(max_clusters):
        plcn = cluster_idx
        try:
            f.seek(ps + plcn * cs); sig = f.read(4)
        except (OSError, OverflowError): continue
        if sig != b"MSB+": continue
        if plcn in current_plcns: continue
        f.seek(ps + plcn * cs); page = f.read(cs)
        if len(page) < 0x54: continue
        thoff = 0x50 + le32(page, 0x50)
        if thoff + 40 > len(page): continue
        tbl = struct.unpack_from("<10I", page, thoff)
        if bool(tbl[3] & 0x100): continue
        orphan_count += 1
        astart, aend = tbl[4], tbl[8]
        if astart >= aend: continue
        for i in range((aend - astart) // 4):
            aa = thoff + astart + i * 4
            if aa + 4 > len(page): break
            ro = thoff + le16(page, aa)
            if ro + 16 > len(page): break
            rh = struct.unpack_from("<I6H", page, ro)
            _, ko, kl, _, vo, vl, _ = rh
            if ko == 0 or kl < 4: continue
            kd = page[ro+ko:ro+ko+kl] if ro+ko+kl <= len(page) else b""
            vd = page[ro+vo:ro+vo+vl] if vo > 0 and vl > 0 and ro+vo+vl <= len(page) else b""
            if le16(kd, 0) == 0x30 and kl > 4:
                name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
                if name and not name.startswith("\x00"):
                    entry = {"name": name, "plcn": plcn, "value_len": len(vd), "vd": bytes(vd)}
                    entry["resident"] = len(vd) > 84
                    # E2 fix: discriminate on >84, not >=0x50 (an 84-byte NON-resident value was
                    # mis-decoded with resident offsets). The non-resident branch now also reads
                    # create/modify from +0x10/+0x18 (§C.3) so the boundary fix does not DROP the
                    # timestamps for recovered 84-byte rows.
                    if len(vd) > 84:
                        entry["create_time"] = le64(vd, 0x28); entry["modify_time"] = le64(vd, 0x30)
                        entry["file_attrs"] = le32(vd, 0x48)
                        entry["is_dir"] = bool(le32(vd, 0x48) & 0x10000000)
                    elif len(vd) >= 0x44:
                        entry["child_oid"] = le64(vd, 0x08) if len(vd) >= 0x10 else 0
                        entry["create_time"] = le64(vd, 0x10) if len(vd) >= 0x18 else 0
                        entry["modify_time"] = le64(vd, 0x18) if len(vd) >= 0x20 else 0
                        entry["file_attrs"] = le32(vd, 0x40)
                        entry["is_dir"] = bool(le32(vd, 0x40) & 0x10000000)
                    if search_name is None or search_name.lower() in name.lower():
                        found.append(entry)
    print(f"  Found {orphan_count} orphaned MSB+ leaf pages")
    return found

def _scan_page_slack(page, plcn, tag):
    """Recover deleted directory entries from B+-tree node SLACK. ReFS deletion
    (`CmsBPlusTable::DeleteFromIndex`) removes only the row's slot in the offset array — the row body is
    NOT scrubbed and persists until a later CoW rewrite. This brute-walks the page for type-0x30 row
    headers that are NOT referenced by the live offset array, validating each (key_off==0x10, key type
    0x30, in-bounds, decodable UTF-16 name). Recovered rows may include partially-overwritten remnants."""
    out = []
    if len(page) < 0x54 or page[:4] != b"MSB+":
        return out
    thoff = 0x50 + le32(page, 0x50)
    if thoff + 40 > len(page):
        return out
    tbl = struct.unpack_from("<10I", page, thoff)
    astart, aend = tbl[4], tbl[8]
    live = set()
    if astart < aend:
        for i in range((aend - astart) // 4):
            aa = thoff + astart + i * 4
            if aa + 2 > len(page):
                break
            live.add(thoff + le16(page, aa))
    for off in range(thoff, len(page) - 16, 4):
        if off in live:
            continue
        rsz, ko, kl, fl, vo, vl, _ = struct.unpack_from("<I6H", page, off)
        # a directory-entry row: key 0x10 past the header, key type 0x30, sane lengths, in-bounds
        if ko != 0x10 or not (4 < kl < 0x400) or not (0 < vl < 0x1000) or vo < 0x10:
            continue
        if off + ko + kl > len(page) or off + vo + vl > len(page):
            continue
        kd = page[off + ko:off + ko + kl]
        if len(kd) < 6 or le16(kd, 0) != 0x30:
            continue
        try:
            name = kd[4:].decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError:
            continue
        if len(name) < 2 or not all(0x20 <= ord(c) < 0xFFFE for c in name):
            continue
        e = _decode_dir_row_value(page[off + vo:off + vo + vl])
        e.update({"name": name, "plcn": plcn, "page_off": off, "tag": tag,
                  "vd": bytes(page[off + vo:off + vo + vl]),
                  # Q6: the page header's TableIdLow (page+0x48) is the OID of the directory that owns this
                  # B+-tree page — i.e. which directory the recovered row was deleted FROM. Resolved to a
                  # path in _slack_recover (0 / unmapped => left blank; never invent a path).
                  "owning_table_oid": le64(page, 0x48) if len(page) >= 0x50 else 0})
        # confidence: a genuine row carries plausible MACB FILETIMEs; remnants/partials do not.
        _SANE = lambda ts: 129037248000000000 < ts < 142000000000000000  # ~2009-11..2050-12 (R5b)
        ct, mt = e.get("create_time", 0), e.get("modify_time", 0)
        e["confidence"] = "high" if (_SANE(ct) and _SANE(mt)) else (
            "medium" if (_SANE(ct) or _SANE(mt)) else "partial")
        out.append(e)
    return out

def _scan_trash_table(f, ps, cs, tr, obj_map):
    if 0xD not in obj_map: return []
    entries = []
    for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0xD]):
        entry = {"key_len": len(kd), "key_hex": kd.hex(),
                 "value_len": len(vd), "value_hex": vd[:64].hex() if len(vd) > 64 else vd.hex()}
        if len(kd) >= 16: entry["oid"] = le64(kd, 8)
        entries.append(entry)
    return entries

def _slack_recover(f, ps, cs, tr, roots, obj_map, max_scan, log):
    """Scan B+-tree node slack across every LIVE metadata page plus orphan MSB+ pages."""
    visited = set(); ptc = []
    for idx, rv in enumerate(roots):
        if rv:
            _walk_btree_pages(f, ps, cs, (None if idx in _CT_ROOT_INDICES else tr), rv, visited, ptc)
    for _oid, vlcns in obj_map.items():
        _walk_btree_pages(f, ps, cs, tr, vlcns, visited, ptc)
    entries = []
    live_plcns = set()
    for head, plcns in ptc:
        live_plcns.add(head)
        data = b""
        ok = True
        for p in plcns:
            try:
                f.seek(ps + p * cs); data += f.read(cs)
            except (OSError, OverflowError):
                ok = False; break
        if ok:
            entries += _scan_page_slack(data, head, "live-slack")
    # orphan MSB+ pages (not referenced by the live tree)
    orphans = 0
    vol_clusters = (f.seek(0, 2) - ps) // cs
    for cl in range(min(vol_clusters, max_scan)):
        if cl in live_plcns:
            continue
        try:
            f.seek(ps + cl * cs); sig = f.read(4)
        except (OSError, OverflowError):
            continue
        if sig != b"MSB+":
            continue
        f.seek(ps + cl * cs); data = f.read(cs)
        ent = _scan_page_slack(data, cl, "orphan-slack")
        if ent:
            orphans += 1; entries += ent
    # Q6: resolve each recovered row's owning-table OID to the directory path it was deleted FROM.
    # build_oid_path_map covers live directories; an unmapped/zero OID stays blank (no invented path).
    oid_paths = build_oid_path_map(f, ps, cs, tr, obj_map)
    for e in entries:
        oto = e.get("owning_table_oid", 0)
        e["owning_path"] = oid_paths.get(oto, "") if oto else ""
    log(f"  Scanned {len(ptc)} live pages + {orphans} orphan pages with recoverable slack rows")
    return entries

def _scan_backup_copies(f, ps, cs, chkp_lcns):
    """Inventory ReFS redundant copies for resilience: the alternating checkpoint pair, the backup
    boot sector (last LBA), and the secondary SUPB copies near the partition end. Verifies presence
    + validity only — it does NOT yet fail over to a backup when the primary is corrupt (future)."""
    import hashlib
    out = {"checkpoints": [], "vbr": None, "supb": []}

    # --- Boot sector (primary @ sector 0) + backup (@ last sector) ---
    f.seek(ps); pv = f.read(512)
    pv_ok = pv[3:7] == b"ReFS"
    pv_cksum_ok = pv_ok and (_vbr_checksum(pv, le16(pv, 0x14)) == le16(pv, 0x16))
    total_sectors = le64(pv, 0x18) if len(pv) >= 0x20 else 0
    vbr = {"primary_ok": pv_ok, "primary_cksum_ok": pv_cksum_ok,
           "total_sectors": total_sectors, "backup": None}
    if total_sectors > 1:
        blba = total_sectors - 1
        try:
            f.seek(ps + blba * 512); bv = f.read(512)
            bv_ok = len(bv) == 512 and bv[3:7] == b"ReFS"
            vbr["backup"] = {
                "lba": blba,
                "present": bv_ok,
                "matches_primary": bv == pv,
                "cksum_ok": bv_ok and _vbr_checksum(bv, le16(bv, 0x14)) == le16(bv, 0x16),
                # the backup boot sector is NOT rewritten on upgrade, so it preserves the original
                # (pre-upgrade) ReFS version — a forensic record of the volume's birth version
                "version": (f"{bv[0x28]}.{bv[0x29]}" if bv_ok else None),
                "primary_version": f"{pv[0x28]}.{pv[0x29]}" if pv_ok else None,
            }
        except (OSError, OverflowError):
            vbr["backup"] = {"lba": blba, "present": False, "error": True}
    out["vbr"] = vbr

    # --- Checkpoint copies (SUPB references the pair; newest virtual clock = current) ---
    best_vc = -1
    for cl in chkp_lcns:
        rec = {"lcn": cl, "sig_ok": False, "vc": None, "roots_ok": False}
        try:
            f.seek(ps + cl * cs); raw = f.read(4 * cs)
            rec["sig_ok"] = raw[:4] == b"CHKP"
            if rec["sig_ok"]:
                rec["vc"] = le64(raw, 0x10)
                try:
                    _vc, _fl, roots = _forefst_parse_chkp(f, ps, cs, cl)
                    rec["roots_ok"] = bool(roots) and any(roots)
                except Exception:
                    rec["roots_ok"] = False
                if rec["vc"] > best_vc:
                    best_vc = rec["vc"]
        except (OSError, OverflowError):
            rec["error"] = True
        out["checkpoints"].append(rec)
    for rec in out["checkpoints"]:
        rec["role"] = ("PRIMARY" if rec.get("vc") == best_vc and best_vc >= 0 else "backup")

    # --- Secondary SUPB copies (primary @ SUPB_LCN; copies sit near the partition end) ---
    out["supb"].append({"lcn": SUPB_LCN, "role": "PRIMARY",
                        "ok": (f.seek(ps + SUPB_LCN * cs), f.read(4))[1] == b"SUPB"})
    if total_sectors > 1:
        end_lcn = (total_sectors * 512) // cs
        for lcn in range(max(0, end_lcn - 64), end_lcn):
            try:
                f.seek(ps + lcn * cs)
                if f.read(4) == b"SUPB":
                    out["supb"].append({"lcn": lcn, "role": "backup", "ok": True})
            except (OSError, OverflowError):
                break
    return out

def _read_full_page(f, ps, cs, slots, use_tr):
    """Read a full metadata page = concatenation of its page-reference LCN slots.
    Returns b'' on any unreadable/untranslatable slot (so checksum verify skips, never crashes)."""
    pg = b""
    for s in slots:
        if s in (0, 0xFFFFFFFFFFFFFFFF):
            break
        try:
            plcn = use_tr.tr(s) if use_tr else s
            if plcn is None or plcn < 0:
                return b""
            f.seek(ps + plcn * cs)
            chunk = f.read(cs)
        except (KeyError, OSError, OverflowError, TypeError, ValueError):
            return b""
        if len(chunk) < cs:
            return b""
        pg += chunk
    return pg

def _check_page(data, lcn, expected_volsig, max_vc, report, verbose):
    report["pages_checked"] += 1
    sig = data[:4]
    detail = {"lcn": lcn, "sig": sig, "issues": []}
    if sig in _VALID_SIGS:
        report["pages_valid_sig"] += 1
    else:
        report["pages_invalid_sig"] += 1
        report["issues"].append(("FAIL", lcn, f"Invalid signature: {sig!r}"))
        detail["issues"].append("bad_sig")
    if len(data) >= 0x10:
        page_volsig = le32(data, 0x0C)
        if page_volsig == expected_volsig or page_volsig == 0:
            report["pages_volsig_match"] += 1
        else:
            report["pages_volsig_mismatch"] += 1
            report["issues"].append(("WARN", lcn, f"Volume sig mismatch: page={_hx(page_volsig)} expected={_hx(expected_volsig)}"))
            detail["issues"].append("volsig_mismatch")
    if len(data) >= 0x18:
        page_vc = le64(data, 0x10)
        if page_vc <= max_vc:
            report["pages_vc_ok"] += 1
        else:
            report["pages_vc_exceed"] += 1
            report["issues"].append(("WARN", lcn, f"VC exceeds checkpoint: page_vc={page_vc} > chkp_vc={max_vc}"))
            detail["issues"].append("vc_exceed")
    if len(data) >= 0x28 and sig == b"MSB+":
        self_lcns = []
        for sl in range(4):
            off = 0x20 + sl * 8
            if off + 8 <= len(data):
                v = le64(data, off)
                if v not in (0, 0xFFFFFFFFFFFFFFFF): self_lcns.append(v)
        if self_lcns:
            if all(self_lcns[i] == self_lcns[0] + i for i in range(len(self_lcns))):
                report["pages_selfaddr_ok"] += 1
            else:
                report["pages_selfaddr_bad"] += 1
                report["issues"].append(("WARN", lcn, f"Self-address tuple not consecutive: {[_hx(x) for x in self_lcns]}"))
                detail["issues"].append("selfaddr_bad")
        else:
            report["pages_selfaddr_ok"] += 1
    if sig == b"MSB+" and len(data) >= 0x80:
        try:
            thoff = 0x50 + le32(data, 0x50)
            if thoff + 40 <= len(data):
                tbl = struct.unpack_from("<10I", data, thoff)
                is_inner = bool(tbl[3] & 0x100)
                astart, aend = tbl[4], tbl[8]
                if astart <= aend:
                    if is_inner: report["btree_inner_ok"] += 1
                    else: report["btree_leaf_ok"] += 1
                else:
                    report["btree_struct_error"] += 1
                    report["issues"].append(("FAIL", lcn, f"B+-tree array bounds invalid: start={astart} > end={aend}"))
                    detail["issues"].append("btree_bounds")
        except Exception:
            report["btree_struct_error"] += 1
            detail["issues"].append("btree_parse_error")
    if verbose: report["page_details"].append(detail)

def _walk_btree_pages(f, ps, cs, tr, vlcns, visited, pages_to_check, depth=5):
    """Enumerate logical metadata pages reachable from `vlcns` — the LCN slots of ONE page.

    A ReFS metadata page = all of its page-reference slot-clusters concatenated (e.g. 4×4 KiB =
    16 KiB). Only the FIRST slot carries the MSB+ header; continuation slots hold the rest of the
    same logical page (often mostly zero padding). They must NOT be validated as standalone pages —
    doing so flagged every clean multi-cluster volume's continuation clusters as 'Invalid signature'.
    Appends (head_plcn, [plcn,...]) per logical page; the caller concatenates + validates the page."""
    plcns = [tr.tr(v) for v in vlcns] if tr else list(vlcns)
    plcns = [p for p in plcns if p not in (0, 0xFFFFFFFFFFFFFFFF)]
    if not plcns:
        return
    head = plcns[0]
    if head in visited:
        return
    visited.add(head)
    pages_to_check.append((head, plcns))
    page = b""
    for p in plcns:
        try:
            f.seek(ps + p * cs); page += f.read(cs)
        except (OSError, OverflowError):
            return
    if page[:4] != b"MSB+" or depth <= 0:
        return
    thoff = 0x50 + le32(page, 0x50)
    if thoff + 40 > len(page): return
    tbl = struct.unpack_from("<10I", page, thoff)
    if not bool(tbl[3] & 0x100): return
    astart, aend = tbl[4], tbl[8]
    if astart >= aend: return
    for i in range((aend - astart) // 4):
        aa = thoff + astart + i * 4
        if aa + 4 > len(page): break
        ro = thoff + le16(page, aa)
        if ro + 16 > len(page): break
        rh = struct.unpack_from("<I6H", page, ro)
        vl = rh[5]
        vd = page[ro + rh[4]:ro + rh[4] + vl] if vl > 0 else b""
        if len(vd) >= 32:
            cvld = [le64(vd, j*8) for j in range(4) if le64(vd, j*8) not in (0, 0xFFFFFFFFFFFFFFFF)]
            _walk_btree_pages(f, ps, cs, tr, cvld, visited, pages_to_check, depth - 1)

def _verify_page_checksums(f, ps, cs, tr, chk, dl, root_count, max_pages=300000, full=True):
    """F1: recompute each metadata page's CRC64 (cktype 2) / SHA-256 (cktype 4) from its
    parent page reference and compare to the stored value.

    `full=False` (--checksums): verify only the CHKP **root tables'** B+-trees (the system metadata —
    Object Table, Container Table, Allocator, etc.; ~tens of pages). Fast.
    `full=True`  (--fullchecksums): additionally cross the Object Table (CHKP root idx 0) leaf rows —
    each leaf value embeds the object root's page reference at value+0x20 — into **every** file/dir/
    stream B+-tree, making it a complete tamper/corruption verifier over the whole metadata Merkle
    structure (can be thousands of pages on a large volume).

    Note on the root offset list: parse_chkp resolves the per-root descriptor offsets via an
    indirect base when CHKP flags bit 0x200 is set (olb = le32(chk,0x94)), else directly at 0x94.
    We replicate that here so root idx 0 maps to the Object Table on every volume layout (the
    indirect form is used by native v3.14)."""
    import hashlib
    st = {"crc64_ok": 0, "crc64_bad": 0, "sha_ok": 0, "sha_bad": 0,
          "none": 0, "pages": 0, "objects": 0, "capped": False, "mismatches": []}
    visited = set()

    def verify_ref(rec, use_tr, is_ot=False, depth=0):
        if st["pages"] >= max_pages:
            st["capped"] = True
            return
        if len(rec) < 0x30 or depth > 96:
            return
        slots = [le64(rec, i * 8) for i in range(4)]
        if slots[0] in (0, 0xFFFFFFFFFFFFFFFF):
            return
        # dedup on (addressing-mode, first-slot): a translated VLCN and a physical LCN may
        # share a numeric value without being the same page.
        key = (use_tr is not None, slots[0])
        if key in visited:
            return
        visited.add(key)
        cktype = rec[0x22]
        pg = _read_full_page(f, ps, cs, slots, use_tr)
        if pg[:4] != b"MSB+":
            return
        st["pages"] += 1
        if cktype == 2:
            stored = le64(rec, 0x28)
            calc = refs_crc64(pg)
            if calc == stored or stored == REFS_CRC64_SENTINEL:
                st["crc64_ok"] += 1
            else:
                st["crc64_bad"] += 1
                st["mismatches"].append((slots[0], "CRC64", _hx(stored), _hx(calc)))
        elif cktype == 4 and len(rec) >= 0x48:
            stored = rec[0x28:0x48]
            calc = hashlib.sha256(pg).digest()
            if calc == stored:
                st["sha_ok"] += 1
            else:
                st["sha_bad"] += 1
                st["mismatches"].append((slots[0], "SHA256", stored.hex()[:16], calc.hex()[:16]))
        else:
            st["none"] += 1
        th = 0x50 + le32(pg, 0x50)
        if th + 40 > len(pg):
            return
        tbl = struct.unpack_from("<10I", pg, th)
        is_inner = bool(tbl[3] & 0x100)
        astart, aend = tbl[4], tbl[8]
        if astart >= aend:
            return
        for i in range((aend - astart) // 4):
            aa = th + astart + i * 4
            if aa + 4 > len(pg):
                break
            r = th + le16(pg, aa)
            if r + 16 > len(pg):
                break
            rh = struct.unpack_from("<I6H", pg, r)
            vd = pg[r + rh[4]:r + rh[4] + rh[5]]
            if is_inner:
                # inner-node child pointer: a bare page reference at value+0 (slots@0, cktype@0x22,
                # checksum@0x28). These use the compact 0x30-byte form even when the CHKP/OT
                # descriptor length `dl` is larger (0x68 on v3.4) — so guard on the checksum's own
                # extent, not `dl`, or whole v3.4 subtrees go undescended. Same VLCN addressing.
                if len(vd) >= 0x30:
                    verify_ref(vd, use_tr, is_ot, depth + 1)
            elif is_ot:
                # Object Table leaf: the object root's page reference is embedded at value+0x20.
                # Its checksum sits at a FIXED ref-internal offset (cktype@+0x22, checksum@+0x28 =>
                # value+0x42 / value+0x48) — independent of the descriptor length `dl`. On v3.4 dl is
                # 0x68 and a `>= 0x20+dl` guard would wrongly skip the (shorter) OT-leaf values,
                # missing every object tree. Guard on the checksum's own extent instead, and hand
                # verify_ref the whole tail. Object B+-trees are VLCN-addressed (translate via tr).
                if len(vd) >= 0x50:
                    st["objects"] += 1
                    verify_ref(vd[0x20:], tr, False, depth + 1)

    flags = le32(chk, 0x78)
    olb = le32(chk, 0x94) if (flags & 0x200) else 0x94
    for idx in range(root_count):
        oe = olb + idx * 4
        if oe + 4 > len(chk):
            continue
        ro = le32(chk, oe)
        if ro == 0 or ro + dl > len(chk):
            continue
        use_tr = None if idx in _CT_ROOT_INDICES else tr
        # full=False stops at the system root tables; full=True crosses the OT (root 0) into objects
        verify_ref(chk[ro:ro + dl], use_tr, is_ot=(idx == 0 and full))
    return st

def _vbr_checksum(sector, vbr_size):
    checksum = 0
    for off in range(0x03, vbr_size):
        if off in (0x16, 0x17): continue
        checksum = ((checksum >> 1) | ((checksum & 1) << 15)) & 0xFFFF
        checksum = (checksum + sector[off]) & 0xFFFF
    return checksum

# ─── Specials umbrella (Q1) — one discoverable home for every special-attribute view ─────────────
# Each entry: (type, one-line description, row predicate). Predicates read fields the enriched files
# walk already produces — this is pure re-homing of `files --filter <type>` + the sparse predicate,
# NO new parsing. The dedicated verbs stay for DEEP ops (reparse --index, snapshots --extract, dataruns,
# extract name:stream); `specials` is the discovery/list layer.
SPECIALS_TYPES = [
    ("ads",        "named data streams",               lambda r: bool(r.get("has_ads"))),
    ("reparse",    "symlinks / junctions / WSL links",  lambda r: bool(r.get("has_reparse"))),
    ("wsl",        "WSL / Linux-metadata links",        lambda r: r.get("reparse_tag_value", 0) in
                     (0x80000023, 0x80000024, 0x80000025, 0x80000026, 0xA000001D)),
    ("hardlink",   "multi-linked files (link groups)",  lambda r: r.get("hard_link_count", 1) > 1
                     and not r.get("is_resident") and not r.get("is_dir")),
    ("sparse",     "allocated < logical size",          lambda r: bool(r.get("file_attrs", 0) & 0x200)),
    ("encrypted",  "EFS-encrypted ($EFS)",              lambda r: bool(r.get("is_encrypted"))),
    ("compressed", "WOF / compressed",                  lambda r: bool(r.get("is_compressed"))),
    ("integrity",  "integrity checksum stream",         lambda r: bool(r.get("has_integrity"))),
    ("ea",         "extended attributes / WSL EA",       lambda r: bool(r.get("has_ea"))),
    ("snapshot",   "CoW prior-version streams",         lambda r: r.get("snapshot_count", 0) > 0),
]
_SPECIALS_BY_NAME = {t[0]: t for t in SPECIALS_TYPES}

def _specials_path(r):
    pp = r.get("parent_path", ""); nm = r["name"]
    return f"{pp}/{nm}" if pp and pp not in ("", ".") else nm

def _specials_print_type(typ, files):
    """Print the type-specific list for one special type; returns the row count."""
    pred = _SPECIALS_BY_NAME[typ][2]
    rows = [r for r in files if pred(r)]
    if typ == "hardlink":
        # group by the shared hard-link name set (one physical file -> one group)
        groups = {}
        for r in rows:
            key = tuple(sorted(r.get("hard_link_names") or [_specials_path(r)]))
            groups.setdefault(key, r)
        print(f"  Hard-link groups ({len(groups)} files, {len(rows)} names):")
        for names, r in sorted(groups.items()):
            print(f"    [{r.get('hard_link_count', len(names))} names] {' | '.join(names)}")
        return len(groups)
    if not rows:
        print("  (none)")
        return 0
    if typ == "ads":
        print(f"  {'STREAMS':<28} HOST FILE")
        for r in rows:
            print(f"    {(r.get('ads_names') or ''):<26} {_specials_path(r)}")
        print(f"\n  Extract one:  forefst IMG export ads \"<file>:<stream>\"")
    elif typ in ("reparse", "wsl"):
        print(f"  {'TAG':<26} {'TARGET':<40} PATH")
        for r in rows:
            tag = reparse_tag_str(r.get("reparse_tag_value", 0)) if r.get("reparse_tag_value") else ""
            print(f"    {tag:<24} {(r.get('reparse_target') or ''):<40} {_specials_path(r)}")
    elif typ == "sparse":
        print(f"  {'LOGICAL':>14} {'ALLOCATED':>14} {'SAVED':>14}  PATH")
        for r in rows:
            fs = r.get("file_size", 0); al = r.get("allocated_size") or 0
            saved = fs - al if fs > al else 0
            print(f"    {fs:>14,} {al:>14,} {saved:>14,}  {_specials_path(r)}")
        print(f"\n  Extent/run map:  forefst IMG dataruns <path>")
    elif typ == "snapshot":
        print(f"  {'PRIORS':>6}  PATH")
        for r in rows:
            print(f"    {r.get('snapshot_count', 0):>6}  {_specials_path(r)}")
        print(f"\n  Extract versions:  forefst IMG export snapshots <dir>")
    else:  # encrypted / compressed / integrity / ea — path (+ owner for encrypted)
        for r in rows:
            extra = f"  [{r.get('owner_sid','')}]" if typ == "encrypted" and r.get("owner_sid") else ""
            print(f"    {_specials_path(r)}{extra}")
    return len(rows)

def cmd_specials(image, remaining, partition_start):
    """Q1: list files carrying a special attribute. No arg = a count summary of every type;
    `specials <type>` = that type's list; `specials all` = every type sectioned. --json for machine output."""
    args = _parse_args(remaining, flags=["--json"])
    sub = args["_rest"][0].lower() if args["_rest"] else None
    if sub is not None and sub != "all" and sub not in _SPECIALS_BY_NAME:
        die(f"specials: unknown type {sub!r}. Types: {', '.join(t[0] for t in SPECIALS_TYPES)} (or 'all')")
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))
    try:
        results = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, 100, True, set())
        files = [r for r in results if not r.get("is_dir")]
        counts = {t[0]: sum(1 for r in files if t[2](r)) for t in SPECIALS_TYPES}
        if args["json"]:
            if sub is None:
                print(json.dumps({"image": os.path.basename(image), "counts": counts}, indent=2)); return 0
            types = [t[0] for t in SPECIALS_TYPES] if sub == "all" else [sub]
            out = {t: [_specials_path(r) for r in files if _SPECIALS_BY_NAME[t][2](r)] for t in types}
            print(json.dumps({"image": os.path.basename(image), "specials": out}, indent=2)); return 0
        if sub is None:                       # summary
            print("=" * 70)
            print(f"ReFS special-attribute inventory — {os.path.basename(image)} (ReFS {vmaj}.{vmin})")
            print("=" * 70)
            print(f"  {'TYPE':<12} {'COUNT':>7}   run `specials <type>` for the list")
            print("  " + "-" * 60)
            for typ, desc, _p in SPECIALS_TYPES:
                print(f"  {typ:<12} {counts[typ]:>7}   {desc}")
            print("  " + "-" * 60)
            distinct = sum(1 for r in files if any(t[2](r) for t in SPECIALS_TYPES))
            print(f"  {distinct} distinct files carry >=1 special attribute.")
            print("  (per-type counts OVERLAP — one file can be several types at once, so the")
            print("   rows above sum to more than this de-duplicated total.)")
            print("  Deep ops: reparse --index · snapshots --extract · dataruns · export ads \"file:stream\"")
            return 0
        for typ in ([t[0] for t in SPECIALS_TYPES] if sub == "all" else [sub]):
            print(f"\n── {typ}  ({counts[typ]}) — {_SPECIALS_BY_NAME[typ][1]} ──")
            _specials_print_type(typ, files)
        return 0
    finally:
        f.close()

def cmd_reparse(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "--verbose", "--index", "--json"], valued=["--tag", "--file"])
    verbose = args["v"] or args["verbose"]
    tag_filter = _int_arg(args["tag"], "--tag", 0) if args["tag"] else None

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        if args["index"]:
            entries, error = _parse_reparse_index(f, ps, cs, tr, obj_map)
            if error: print(f"NOTE: {error}", file=sys.stderr)
            if tag_filter: entries = [e for e in entries if e.get("reparse_tag") == tag_filter]
            if args["json"]:
                print(json.dumps({"reparse_index": entries}, indent=2, default=str)); return 0
            print("=" * 78)
            print("ReFS Reparse Point Index (OID 0x540)")
            print("=" * 78)
            print(f"  Image:        {image}")
            print(f"  ReFS version: {vmaj}.{vmin}")
            print(f"\n  Total entries: {len(entries)}  (rows in the OID 0x540 reparse index table)")
            print("  Note: the driver inserts ONE index row per reparse-bearing OBJECT, when its reparse")
            print("        attribute is first created; extra hard-linked NAMES of that object add no row.")
            print("        The `reparse` command instead counts every REPARSE_POINT-flagged NAME, so its")
            print("        count is >= this row count (they measure different things and need not match).")
            if entries:
                by_tag = {}
                for e in entries: by_tag.setdefault(e.get("reparse_tag", 0), []).append(e)
                print(f"\n  {'Tag':<14} {'Name':<35} {'Count'}")
                print(f"  {'-'*60}")
                for tag in sorted(by_tag.keys()):
                    print(f"  {_hx(tag):<14} {_tag_name(tag):<35} {len(by_tag[tag])}")
                if verbose:
                    print(f"\n  Detailed entries:")
                    for e in entries:
                        oid = e.get("dir_oid", 0)
                        oid_s = _KNOWN_OIDS.get(oid, _hx(oid))
                        print(f"    Tag={_hx(e.get('reparse_tag', 0))} DirOID={oid_s} "
                              f"ordinal={e.get('file_ref_word0', 0)} Key={e.get('key_hex', '')}")
            else:
                print("  (no entries)")
            return 0

        if 0x600 not in obj_map:
            die("Root directory (OID 0x600) not found")
        # Q5 defect 1 fix: source the reparse list from the SHARED enriched walk (same one `files` uses),
        # so it is consistent BY CONSTRUCTION and includes the non-resident / hard-linked reparse points the
        # old dedicated walker dropped (it read file_attrs only from the resident 0x48 layout and skipped
        # every len<=84 file). We still run _walk_dir_for_reparse to MERGE in its rich per-file decode
        # (substitute/print name, LX target, device) for the entries it can fully decode from the value;
        # the rest fall back to the walk's resolved reparse_target + reparse_tag_value (backing-record aware).
        main_entries = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, 100, True, set())
        def _mpath(r):
            pp = r.get("parent_path", "") or ""
            return (pp + "/" + r["name"]).lstrip("/") if pp not in ("", ".") else r["name"]
        rich = {}
        for _e in _walk_dir_for_reparse(f, ps, cs, tr, obj_map, 0x600, "", 0, 100):
            if _e.get("reparse_data") or _e.get("wsl_eas"):
                rich[_e["name"]] = _e
        all_files = []
        for r in main_entries:
            if not r.get("has_reparse"):
                continue
            fp = _mpath(r)
            rf = rich.get(fp)
            all_files.append({
                "name": fp, "is_dir": r.get("is_dir"), "file_attrs": r.get("file_attrs", 0),
                "has_reparse": True,
                "reparse_data": rf.get("reparse_data") if rf else None,
                "wsl_eas": rf.get("wsl_eas", {}) if rf else {},
                "reparse_target": r.get("reparse_target", ""),
                "reparse_tag_value": r.get("reparse_tag_value", 0),
            })
        if args["file"]:
            fl = args["file"].lower()
            results = [fe for fe in all_files if fl in fe["name"].lower()]
        else:
            results = list(all_files)
        if tag_filter:
            results = [fe for fe in results
                       if (fe.get("reparse_data") and fe["reparse_data"].get("tag") == tag_filter)
                       or fe.get("reparse_tag_value") == tag_filter]
        if args["json"]:
            print(json.dumps({"reparse_points": results}, indent=2, default=str)); return 0

        print("=" * 78)
        print("ReFS Reparse Points")
        print("=" * 78)
        print(f"  Image:        {image}")
        print(f"  ReFS version: {vmaj}.{vmin}")
        reparse_count = len(all_files)
        wsl_count = sum(1 for fe in all_files if fe.get("wsl_eas"))
        print(f"\n  Files with REPARSE_POINT flag: {reparse_count}")
        print(f"  Files with WSL EAs: {wsl_count}")
        print(f"  Total files scanned: {len(main_entries)}")
        if results:
            print(f"\n  Showing {len(results)} entries:\n")
            for entry in results:
                print(f"  {entry.get('name', '?')}")
                print(f"    Type:      {'DIR' if entry.get('is_dir') else 'FILE'}")
                print(f"    Attrs:     {_hx(entry.get('file_attrs', 0))}")
                rd = entry.get("reparse_data")
                if rd:
                    print(f"    Reparse:   {rd.get('tag_name', '?')} ({_hx(rd.get('tag', 0))})")
                    if "substitute_name" in rd: print(f"    Target:    {rd['substitute_name']}")
                    if "print_name" in rd: print(f"    Display:   {rd['print_name']}")
                    if "target" in rd: print(f"    LX Target: {rd['target']}")
                    if "relative" in rd: print(f"    Relative:  {rd['relative']}")
                    if "note" in rd: print(f"    Note:      {rd['note']}")
                    if "dev_major" in rd: print(f"    Device:    {rd['dev_major']}:{rd['dev_minor']}")
                    if "error" in rd: print(f"    Error:     {rd['error']}")
                    if verbose and "raw_hex" in rd: print(f"    Raw:       {rd['raw_hex']}")
                elif entry.get("reparse_target") or entry.get("reparse_tag_value"):
                    # non-resident / hard-linked reparse: rich buffer lives in the backing record; show the
                    # resolved tag + target from the shared walk (same values `files --filter reparse` shows).
                    _tv = entry.get("reparse_tag_value", 0)
                    print(f"    Reparse:   {_tag_name(_tv)} ({_hx(_tv)})  [non-resident]")
                    if entry.get("reparse_target"):
                        print(f"    Target:    {entry['reparse_target']}")
                else:
                    print(f"    Reparse:   (tag in attrs but target not recoverable from this record)")
                wsl = entry.get("wsl_eas", {})
                if wsl:
                    print(f"    WSL EAs:")
                    if "lxuid" in wsl: print(f"      UID:  {wsl['lxuid']}")
                    if "lxgid" in wsl: print(f"      GID:  {wsl['lxgid']}")
                    if "lxmod_str" in wsl: print(f"      Mode: {wsl['lxmod_str']}")
                    if "lxdev_major" in wsl: print(f"      Dev:  {wsl['lxdev_major']}:{wsl['lxdev_minor']}")
                print()
        elif args["file"]:
            print(f"\n  No files matching '{args['file']}'")
        else:
            print(f"\n  No reparse points found in root directory")
            print(f"  (Reparse points may exist in subdirectories — use --file or --index)")

        idx_entries, idx_error = _parse_reparse_index(f, ps, cs, tr, obj_map)
        if not idx_error and idx_entries:
            print(f"\n  Reparse Index (OID 0x540): {len(idx_entries)} indexed entries")
            by_tag = {}
            for e in idx_entries: by_tag.setdefault(e.get("reparse_tag", 0), []).append(e)
            for tag in sorted(by_tag.keys()):
                print(f"    {_tag_name(tag)}: {len(by_tag[tag])}")

        return 0

    finally:
        f.close()

# ── Deleted-file recoverability (view verdict) + `export deleted` writer ──────────────────────────
_RECOVER_LABEL = {
    "recoverable_inline": "FULL FILE recoverable (resident — {n} B stored inline in the record)",
    "extent_backed":      "metadata + carve (non-resident — data is in on-disk extents; `export deleted --carve`)",
    "metadata_only":      "metadata only (non-resident — file data is NOT in this remnant)",
    "fragment_only":      "fragment only (Trash-table key/value)",
}

def _extent_backed_carveable(vd):
    """B4: True only when a deleted extent-backed remnant can ACTUALLY be carved — i.e. its 0x1000 holder
    yields a non-empty on-disk extent list (the exact predicate `_carve_extent_backed` uses). On a truncated
    slack remnant the disk_alloc field survives but the extent table is zeroed (ecount==0), so only metadata
    is recoverable and the 'extent_backed / --carve' promise would produce no file."""
    for k, v in parse_resident_btree_rows(vd):
        if (len(k) >= 0x18 and k[12] == 0x80 and k[13] == 0x00 and le64(k, 0x10) == 0x1000
                and len(v) >= 0x50 and le32(v, 4) == SNAP_DATA_DESC):
            stream_size, disk_alloc, exts = parse_snapshot_data_entry(v)
            return bool(disk_alloc > 0 and exts and stream_size > 0)
    return False

def _deleted_recoverability(e):
    """Grade a recovered deleted row (from the scan / slack engines) by whether — and how — its FILE
    CONTENT is reconstructable. Returns (enum, human_label, decoded_or_None). Disk-free (view-time safe):

    - recoverable_inline: a RESIDENT file whose inline $DATA decodes via get_resident_data_content (the
      SAME helper that extracts LIVE resident files). decoded bytes are returned -> `export deleted` writes
      a .recovered. This is the only FULL-FILE recovery from the remnant alone.
    - extent_backed: a NON-RESIDENT file (long value) whose current stream lives in on-disk extents held
      inline in this row (F5, _current_stream_extent_backed). The data is NOT in the remnant, but the extent
      MAP is -> `export deleted --carve` reads those clusters (best-effort; may be reallocated).
    - metadata_only: a non-resident file with no usable data/extent info in the remnant (short <=84 value,
      or a long value that is neither inline nor extent-backed) -> only name/size/timestamps survive here.
    - fragment_only: a Trash-table key/value fragment.

    'recoverable' means the content (or its extent map) is PRESENT in this remnant — NOT that the bytes are
    un-overwritten (there is no allocation/freshness check). EFS content decodes to CIPHERTEXT; sparse files
    short-read; a 'partial'-confidence slack remnant is hedged."""
    vd = e.get("vd") or b""
    if not vd:
        return ("fragment_only", _RECOVER_LABEL["fragment_only"], None)
    if not e.get("resident"):                       # len(vd) <= 84 — non-resident, no data in the row
        return ("metadata_only", _RECOVER_LABEL["metadata_only"], None)
    decoded = get_resident_data_content(vd)
    if decoded is not None:                         # truly resident: $DATA inline in the record
        label = _RECOVER_LABEL["recoverable_inline"].format(n=len(decoded))
        attrs = e.get("file_attrs", 0)
        tags = []
        if attrs & 0x4000: tags.append("CIPHERTEXT — EFS-encrypted")   # FILE_ATTRIBUTE_ENCRYPTED
        if attrs & 0x200:  tags.append("sparse — short read expected")  # FILE_ATTRIBUTE_SPARSE
        if e.get("confidence") == "partial": tags.append("PARTIAL remnant — corroborate")
        if tags:
            label += " [" + "; ".join(tags) + "]"
        return ("recoverable_inline", label, decoded)
    # long value, not inline => NON-RESIDENT. If its current stream is extent-backed (F5) the extent list is
    # in this remnant -> carve candidate; otherwise only metadata survives.
    if _current_stream_extent_backed(vd):
        if _extent_backed_carveable(vd):
            return ("extent_backed", _RECOVER_LABEL["extent_backed"], None)
        return ("metadata_only", _RECOVER_LABEL["metadata_only"], None)   # B4: extent map zeroed -> no carve
    return ("metadata_only", _RECOVER_LABEL["metadata_only"], None)

def _collision_free_path(path):
    """Never clobber an existing file: on collision append .dup1/.dup2/… (user-selected overwrite policy).
    The .row/.recovered names already embed the physical cluster [+page offset], so this fires only across
    sources or across repeated runs into the same directory — never for two rows of one scan."""
    if not os.path.exists(path):
        return path
    i = 1
    while os.path.exists(f"{path}.dup{i}"):
        i += 1
    return f"{path}.dup{i}"

def _carve_extent_backed(f, ps_off, cs, tr, vd):
    """Best-effort content carve for an EXTENT-BACKED (non-resident, F5) deleted remnant: read the current
    stream's on-disk extents held inline in the row and reassemble. Returns (bytes, declared_size) or None.

    The bytes MAY BE STALE — the clusters can be reallocated after deletion; there is no allocation-freshness
    check, so callers must warn. Sparse files legitimately read short / zero-padded. Reuses the validated
    snapshot extent format (parse_snapshot_data_entry) + cmd_extract's fvcn placement/trim (proven on
    win11refs2tsnapshots arg.txt current stream = 'arg ument ation', extent-backed, byte-exact)."""
    holder = None
    for k, v in parse_resident_btree_rows(vd):
        if (len(k) >= 0x18 and k[12] == 0x80 and k[13] == 0x00 and le64(k, 0x10) == 0x1000
                and len(v) >= 0x50 and le32(v, 4) == SNAP_DATA_DESC):
            holder = v
            break
    if holder is None:
        return None
    stream_size, disk_alloc, exts = parse_snapshot_data_entry(holder)
    if disk_alloc == 0 or not exts or stream_size <= 0:
        return None
    alloc = max(fv + run for fv, _vl, run in exts) * cs
    if alloc > 256 * 1024 * 1024:          # safety cap for a best-effort carve
        return None
    buf = bytearray(alloc)
    for fvcn, vlcn, run in sorted(exts, key=lambda x: x[0]):
        for j in range(run):
            try:
                plcn = tr.tr(vlcn + j)
            except Exception:
                plcn = vlcn + j
            f.seek(ps_off + plcn * cs)
            off = (fvcn + j) * cs
            buf[off:off + cs] = f.read(cs)
    return (bytes(buf[:stream_size]), stream_size)

def cmd_deleted(image, remaining, partition_start):
    # `--_from-export` is a private marker set by `export deleted` so the deprecation notice below is only
    # shown for a DIRECT `deleted --extract` call. Strip it before _parse_args (which rejects unknown flags).
    from_export = "--_from-export" in remaining
    remaining = [x for x in remaining if x != "--_from-export"]
    args = _parse_args(remaining, flags=["--trash", "--scan-pages", "--slack", "--no-slack",
                                         "--rows-only", "--content-only", "--carve"],
                       valued=["--search", "--max-scan", "--extract"])
    search_name = args["search"]
    extract_dir = args["extract"]
    rows_only = args["rows_only"]
    content_only = args["content_only"]
    carve = args["carve"]
    if rows_only and content_only:
        die("--rows-only and --content-only are mutually exclusive")
    max_scan = _int_arg(args["max_scan"], "--max-scan") if args["max_scan"] else 50000
    # The B+-tree node-slack scan now runs BY DEFAULT (it is where deleted rows + recoverability live);
    # --no-slack skips it for a fast Trash+checkpoint pass, and --trash returns after the Trash table only.
    do_slack = not args["no_slack"] and not args["trash"]
    do_scan_pages = args["scan_pages"]
    # Accumulators shared by the scan + slack extraction paths (one manifest per run). Two verdict buckets
    # so the roll-up (and the .recovered files export writes) reconcile by category: deleted files vs prior
    # versions of files still present. _rc counts the entries whose inline content actually decodes.
    _manifest = []
    _view_verdicts = []     # deleted files (scan `deleted` + slack d_solid + slack d_partial)
    _prior_verdicts = []    # prior versions of LIVE files (scan still_present + slack p_solid)

    def _emit(base, e, name, source, tag):
        """Write BOTH the raw remnant (.row) AND, when the row is resident and its inline $DATA decodes,
        the recovered content (.recovered) — the user-chosen default for `export deleted`. The raw .row is
        preserved unless --content-only; the decoded .recovered is written unless --rows-only. Names never
        clobber (auto .dupN). Every entry is stamped into the run manifest. `base` is the full path WITHOUT
        extension; keeping it identical to the historical name means --rows-only reproduces byte-for-byte."""
        vd = e.get("vd")
        if not extract_dir or not vd:
            return
        os.makedirs(extract_dir, exist_ok=True)
        venum, vlabel, decoded = _deleted_recoverability(e)
        row_path = content_path = carved_path = None
        carved_len = carved_size = None
        if not content_only:
            row_path = _collision_free_path(base + ".row")
            with open(row_path, "wb") as of:
                of.write(vd)
        if decoded is not None and not rows_only:
            content_path = _collision_free_path(base + ".recovered")
            with open(content_path, "wb") as of:
                of.write(decoded)
        # --carve: best-effort reconstruct a NON-RESIDENT (extent-backed) deleted file from its inline
        # extent map. Bytes may be stale (clusters possibly reallocated) — hence the distinct .carved name.
        if carve and venum == "extent_backed" and not rows_only:
            cres = _carve_extent_backed(f, ps, cs, tr, vd)
            if cres:
                cbytes, carved_size = cres
                carved_len = len(cbytes)
                carved_path = _collision_free_path(base + ".carved")
                with open(carved_path, "wb") as of:
                    of.write(cbytes)
        _manifest.append({
            "name": name, "source": source, "tag": e.get("tag", tag),
            "plcn": e.get("plcn"), "page_off": e.get("page_off"),
            "is_resident": venum == "recoverable_inline", "confidence": e.get("confidence"),   # B5: from verdict
            "value_len": len(vd), "recoverable": venum, "verdict": vlabel,
            "row_file": os.path.basename(row_path) if row_path else None,
            "content_file": os.path.basename(content_path) if content_path else None,
            "decoded_len": len(decoded) if decoded is not None else None,
            "carved_file": os.path.basename(carved_path) if carved_path else None,
            "carved_len": carved_len, "carved_declared_size": carved_size,
        })
        parts = []
        if row_path:
            parts.append(f"row {os.path.basename(row_path)} ({len(vd)} B)")
        if content_path:
            parts.append(f"content {os.path.basename(content_path)} ({len(decoded)} B, {venum})")
        elif decoded is None and not content_only:
            parts.append("no inline $DATA decoded — metadata-only (.row is the evidence)")
        elif decoded is not None and rows_only:
            parts.append("[--rows-only] decoded content withheld")
        elif decoded is None and content_only:
            parts.append("[--content-only] no inline content — nothing written")
        if carved_path:
            short = "  [SHORT/sparse — extents cover fewer bytes]" if (carved_len < carved_size) else ""
            parts.append(f"CARVED {os.path.basename(carved_path)} ({carved_len}/{carved_size} B, "
                         f"may be stale){short}")
        elif carve and venum == "extent_backed":
            parts.append("carve: no readable extents in remnant")
        print("      → wrote " + " + ".join(parts) if parts else "      → (nothing to write)")

    def _write_manifest():
        if extract_dir and _manifest:
            mpath = os.path.join(extract_dir, "recovery_manifest.json")
            n_rec = sum(1 for m in _manifest if m["recoverable"] == "recoverable_inline")
            n_row = sum(1 for m in _manifest if m["row_file"])
            n_content = sum(1 for m in _manifest if m["content_file"])
            n_carved = sum(1 for m in _manifest if m.get("carved_file"))
            with open(mpath, "w") as mf:
                json.dump({"image": image, "entries": len(_manifest),
                           "row_files": n_row, "recovered_files": n_content, "carved_files": n_carved,
                           "recoverable_inline": n_rec,
                           "trust_ranking": ("MOST reliable -> LEAST: (1) '.recovered' — a RESIDENT file's full "
                                    "content is stored INSIDE the metadata remnant, so it is recovered intact. "
                                    "(2) '.carved' — a NON-RESIDENT file has only an extent MAP in metadata; the "
                                    "actual data clusters live elsewhere on the volume and may have been "
                                    "reallocated/overwritten after deletion, so carved bytes are the MOST likely "
                                    "to be stale. (3) metadata-only — no content recoverable at all. '.row' is the "
                                    "raw evidence record, always exact."),
                           "note": ("'.recovered' = full content of a RESIDENT deleted file, decoded from the "
                                    "remnant. '.carved' = a NON-RESIDENT (extent-backed) file reassembled from "
                                    "its inline extent map — BEST-EFFORT, the clusters may have been reallocated "
                                    "(no freshness check); verify before relying on it. Neither guarantees the "
                                    "bytes are un-overwritten. Short-value non-resident files stay metadata-only."),
                           "records": _manifest}, mf, indent=2)
            _cv = f" + {n_carved} .carved" if n_carved else ""
            print(f"\n  Wrote {n_row} .row + {n_content} .recovered{_cv} "
                  f"({len(_manifest)} entr{'y' if len(_manifest)==1 else 'ies'}) "
                  f"+ recovery_manifest.json to {extract_dir}")
            if n_carved:
                print(f"  CAVEAT: the {n_carved} .carved file(s) are NON-RESIDENT — only their extent MAP was in "
                      f"metadata;\n          their data clusters may have been reused since deletion, so .carved "
                      f"bytes are the\n          most likely to be STALE. '.recovered' (resident, in-metadata) is "
                      f"the more reliable class.")

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        # Parse both checkpoints
        checkpoints = []
        for lcn in chkp_lcns:
            try:
                vc, flags, chkp_roots = _forefst_parse_chkp(f, ps, cs, lcn)
                checkpoints.append((vc, chkp_roots, lcn))
            except Exception: pass
        checkpoints.sort(key=lambda x: x[0], reverse=True)

        print("=" * 78)
        print("ReFS Deleted File Finder")
        print("=" * 78)
        print(f"  Image:        {image}")
        print(f"  ReFS version: {vmaj}.{vmin}")
        print(f"  Cluster size: {_hx(cs)}")
        print(f"  Checkpoints:  {len(checkpoints)} (VC: {', '.join(str(c[0]) for c in checkpoints)})")
        print(f"  Objects:      {len(obj_map)}")
        print()

        if extract_dir and not from_export:
            print("  NOTE: 'deleted --extract DIR' is deprecated — 'export deleted DIR' does the same")
            print("        (writes the raw .row AND the decoded .recovered content). Proceeding.\n")

        print("── Trash Table (OID 0xD) ──")
        trash_entries = _scan_trash_table(f, ps, cs, tr, obj_map)
        if trash_entries:
            print(f"  {len(trash_entries)} entries pending cleanup:")
            for te in trash_entries:
                oid_str = f" (OID {_hx(te['oid'])})" if "oid" in te else ""
                print(f"    Key ({te['key_len']}B){oid_str}: {te['key_hex'][:64]}")
                print(f"    Val ({te['value_len']}B): {te['value_hex'][:64]}")
        else:
            print("  Empty (all deletions fully processed)")
        print()

        if args["trash"]:
            return 0

        if len(checkpoints) > 1:
            print("── Checkpoint Comparison ──")
            old_vc, old_roots_raw = checkpoints[1][0], checkpoints[1][1]
            print(f"  Current checkpoint: VC={checkpoints[0][0]}")
            print(f"  Previous checkpoint: VC={old_vc}")
            # The old roots from _forefst_parse_chkp are the raw root list
            # We need to rebuild object table from old checkpoint
            # For simplicity, compare root directory files
            current_files = _get_current_files(f, ps, cs, tr, obj_map)
            # Try building old object map
            try:
                old_ot_vlcns = old_roots_raw[0] if len(old_roots_raw) > 0 else []
                if old_ot_vlcns:
                    old_obj_map = build_object_map(f, ps, cs, tr, old_ot_vlcns)
                    old_files = _get_current_files(f, ps, cs, tr, old_obj_map)
                    removed = old_files - current_files
                    added = current_files - old_files
                    if removed:
                        print(f"  Files in old checkpoint but NOT in current ({len(removed)}):")
                        for name in sorted(removed): print(f"    - {name}")
                    if added:
                        print(f"  Files in current but NOT in old ({len(added)}):")
                        for name in sorted(added): print(f"    + {name}")
                    if not removed and not added:
                        print(f"  Same top-level files in both (change may be in subdirectories or metadata)")
                else:
                    print(f"  Object Table root is identical in both checkpoints (no recent changes)")
            except Exception:
                print(f"  Could not parse old checkpoint's object table")
            print()

        if do_scan_pages:
            print("── Orphaned Page Scan ──")
            current_plcns = set()
            for root_vlcns in roots:
                for v in root_vlcns:
                    plcn = tr.tr(v) if tr else v
                    current_plcns.add(plcn)
            for oid_val, vlcns in obj_map.items():
                for v in vlcns:
                    plcn = tr.tr(v) if tr else v
                    current_plcns.add(plcn)
            print(f"  Current tree references {len(current_plcns)} unique physical clusters")
            current_files = _get_current_files(f, ps, cs, tr, obj_map)
            entries = _scan_for_deleted_entries(f, ps, cs, tr, current_plcns, search_name=search_name, max_scan_clusters=max_scan)
            if entries:
                seen = {}
                for e in entries:
                    if e["name"] not in seen or e.get("value_len", 0) > seen[e["name"]].get("value_len", 0):
                        seen[e["name"]] = e
                deleted = [(n, e) for n, e in sorted(seen.items()) if n not in current_files]
                still_present = [(n, e) for n, e in sorted(seen.items()) if n in current_files]
                def _export(name, e, tag):
                    if not extract_dir or not e.get("vd"):
                        return
                    os.makedirs(extract_dir, exist_ok=True)
                    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
                    base = os.path.join(extract_dir, f"{safe}__{tag}_c{e['plcn']}")
                    _emit(base, e, name, "orphan-scan", tag)

                if deleted:
                    print(f"\n  DELETED entries (not in current directory tree): {len(deleted)}\n")
                    for name, e in deleted:
                        kind = "DIR " if e.get("is_dir", False) else "FILE"
                        _venum, _vlabel, _ = _deleted_recoverability(e)   # B5: header residency from the verdict, not len(vd)>84
                        _hdr_res = "resident" if _venum == "recoverable_inline" else "non-resident"
                        print(f"    {kind} {name}  ({_hdr_res})")
                        if "create_time" in e: print(f"      Created:  {_filetime_to_str(e['create_time'])}")
                        if "modify_time" in e: print(f"      Modified: {_filetime_to_str(e['modify_time'])}")
                        print(f"      Found at: cluster {e['plcn']} (offset {_hx(e['plcn'] * cs)})")
                        _view_verdicts.append(_venum)
                        print(f"      Recoverable: {_vlabel}")
                        _export(name, e, "del")
                if still_present:
                    print(f"\n  Old versions of existing files (orphaned pages): {len(still_present)}")
                    for name, e in still_present:
                        _venum, _vlabel, _ = _deleted_recoverability(e)
                        _prior_verdicts.append(_venum)
                        print(f"    {name} (cluster {e['plcn']}) — {_vlabel}")
                        _export(name, e, "oldver")
            else:
                msg = f"matching '{search_name}'" if search_name else "in scanned area"
                print(f"  No deleted file entries found {msg}")

        if do_slack:
            print("── B+-tree Node Slack Scan (Method 5) ──")
            print("  Recovering deleted directory entries from metadata-page free space")
            print("  (ReFS deletion removes only the row's index slot; the row body persists).")
            current_files = _get_current_files(f, ps, cs, tr, obj_map)
            raw = _slack_recover(f, ps, cs, tr, roots, obj_map, max_scan, print)
            # dedup on (name, create_time, is_dir); keep the longest recovered row
            dedup = {}
            for e in raw:
                k = (e["name"], e.get("create_time", 0), e.get("is_dir", False))
                if k not in dedup or len(e["vd"]) > len(dedup[k]["vd"]):
                    dedup[k] = e
            ent = list(dedup.values())
            if search_name:
                ent = [e for e in ent if search_name.lower() in e["name"].lower()]
            deleted = sorted([e for e in ent if e["name"] not in current_files], key=lambda e: e["name"])
            prior = sorted([e for e in ent if e["name"] in current_files], key=lambda e: e["name"])

            def _export_slack(e, tag):
                if not extract_dir or not e.get("vd"):
                    return
                os.makedirs(extract_dir, exist_ok=True)
                safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in e["name"])[:80]
                base = os.path.join(extract_dir, f"{safe}__slack-{tag}_c{e['plcn']}o{e['page_off']:x}")
                _emit(base, e, e["name"], "slack", tag)

            def _conf_split(lst):
                solid = [e for e in lst if e["confidence"] in ("high", "medium")]
                partial = [e for e in lst if e["confidence"] == "partial"]
                return solid, partial
            d_solid, d_partial = _conf_split(deleted)
            p_solid, p_partial = _conf_split(prior)
            if deleted:
                print(f"\n  DELETED (name not in the live tree): {len(deleted)}  "
                      f"[{len(d_solid)} with valid timestamps, {len(d_partial)} partial remnants]\n")
                for e in d_solid:
                    kind = "DIR " if e.get("is_dir") else "FILE"
                    tsane = "" if e["confidence"] == "high" else "  [one timestamp only]"
                    _hdr_res = "resident" if _deleted_recoverability(e)[0] == "recoverable_inline" else "non-resident"  # B5
                    print(f"    {kind} {e['name']}  ({_hdr_res}, "
                          f"{e['tag']} @ cluster {e['plcn']} off {_hx(e['page_off'])}){tsane}")
                    # Q6: which directory the row was deleted FROM (owning-table OID -> path).
                    if e.get("owning_path"):
                        print(f"      Deleted from: {e['owning_path']}  (table {_hx(e.get('owning_table_oid', 0))})")
                    elif e.get("owning_table_oid"):
                        print(f"      Owning table: {_hx(e['owning_table_oid'])}  (path unresolved)")
                    if e.get("create_time"):
                        print(f"      Created:  {_filetime_to_str(e['create_time'])}")
                    if e.get("modify_time"):
                        print(f"      Modified: {_filetime_to_str(e['modify_time'])}")
                    _venum, _vlabel, _ = _deleted_recoverability(e)
                    _view_verdicts.append(_venum)
                    print(f"      Recoverable: {_vlabel}")
                    _export_slack(e, "del")
                if d_partial:
                    print(f"\n    + {len(d_partial)} partial remnants (name fragment only, no valid "
                          f"timestamps — corroborate before use):")
                    for e in d_partial[:30]:
                        print(f"      {e['name']!r}  ({e['tag']} c{e['plcn']} o{_hx(e['page_off'])})")
                    if len(d_partial) > 30:
                        print(f"      … and {len(d_partial) - 30} more")
                    for e in d_partial:
                        _view_verdicts.append(_deleted_recoverability(e)[0])
                        _export_slack(e, "del-partial")
            if prior:
                print(f"\n  PRIOR VERSIONS of files still present (CoW slack remnants): {len(prior)}  "
                      f"[{len(p_solid)} with valid timestamps]")
                for e in p_solid:
                    _venum, _vlabel, _ = _deleted_recoverability(e)
                    _prior_verdicts.append(_venum)
                    print(f"    {e['name']}  ({e['tag']} @ cluster {e['plcn']} off {_hx(e['page_off'])}) — {_vlabel}")
                    _export_slack(e, "prior")
            if not deleted and not prior:
                print("  No recoverable type-0x30 rows found in slack"
                      + (f" matching '{search_name}'" if search_name else "") + ".")
            print("\n  NOTE: slack rows are unindexed remnants. 'with valid timestamps' rows decode a full")
            print("        $SI (high confidence); 'partial remnants' are name fragments from a row whose")
            print("        body was partly overwritten — always corroborate before relying on one entry.")

        # Methods note: reflect the current defaults (slack runs by default) + how to change scope.
        print("── Recovery methods ──")
        _ran = ["Trash table (0xD)", "checkpoint diff"]
        if do_slack:      _ran.append("B+-tree node-slack scan (deleted rows + recoverability)")
        if do_scan_pages: _ran.append("orphaned-page scan")
        print(f"  Ran: {', '.join(_ran)}.")
        if do_slack:
            print("  Options: --no-slack (fast Trash+checkpoint only) · --scan-pages (also orphaned pages) ·")
            print("           --search SUB (filter) · `export deleted DIR [--carve]` (write files out).")
        else:
            print("  Slack scan SKIPPED (--no-slack). Run without it (the default) to recover deleted rows.")
        print("  (Windows Recycle Bin is separate: see the `recyclebin` command.)")
        print()

        # Recoverability roll-up, split by category so it reconciles with the files `export deleted` writes.
        if _view_verdicts or _prior_verdicts:
            _rc = lambda lst: sum(1 for v in lst if v == "recoverable_inline")
            _ec = lambda lst: sum(1 for v in lst if v == "extent_backed")
            if _view_verdicts:
                print(f"  DELETED files: {_rc(_view_verdicts)} of {len(_view_verdicts)} are RESIDENT with full "
                      f"content recoverable; {_ec(_view_verdicts)} are non-resident (carve-able with --carve).")
            if _prior_verdicts:
                print(f"  PRIOR versions of live files: {_rc(_prior_verdicts)} of {len(_prior_verdicts)} "
                      f"decode to a file.")
            print("  Restorability: a RESIDENT deleted file's FULL content is recoverable from the remnant")
            print("       (written as .recovered). A NON-RESIDENT file keeps its data in on-disk extents — if the")
            print("       extent map survives in the remnant ('extent_backed'), `export deleted --carve`")
            print("       reconstructs it best-effort (bytes may be stale); otherwise only METADATA survives")
            print("       (name/size/timestamps). See the `export deleted` docs.")
            if not extract_dir:
                print("  Next: `export deleted <DIR>` writes each entry's raw .row (evidence) + a .recovered for")
                print("        resident files; add --carve to also reconstruct non-resident (extent-backed) files.")
        _write_manifest()

        print()
        return 0

    finally:
        f.close()

def cmd_snapshots(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "--verbose", "--json", "--show"],
                       valued=["--file", "--depth", "--extract", "--snapshot"])
    verbose = args["v"] or args["verbose"]
    do_show = args["show"]
    extract_dir = args["extract"]
    snap_sel = args["snapshot"]              # select ONE version: name substring, or 1-based index number
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 10

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        results = []
        _find_snapshot_files(f, ps, cs, tr, obj_map, 0x600, "", 0, max_depth, results)

        true_snap_results = []
        ads_results = []
        for r in results:
            true_snaps = [s for s in r["snapshots"] if s.get("is_true_snapshot", True)]
            ads = [s for s in r["snapshots"] if not s.get("is_true_snapshot", True)]
            if true_snaps: true_snap_results.append({**r, "snapshots": true_snaps})
            if ads: ads_results.append({**r, "snapshots": ads})
        total_true = sum(len(r["snapshots"]) for r in true_snap_results)
        total_ads = sum(len(r["snapshots"]) for r in ads_results)

        if args["json"]:
            json_out = {
                "image": image, "refs_version": f"{vmaj}.{vmin}", "cluster_size": cs,
                "files_with_snapshots": len(true_snap_results), "total_snapshots": total_true,
                "files": [],
            }
            for r in true_snap_results:
                fentry = {"path": r["path"],
                          "create_time": _filetime_to_str(r.get("create_time", 0)),
                          "modify_time": _filetime_to_str(r.get("modify_time", 0)),
                          "resident_bytes": r["value_len"], "snapshots": []}
                for s in r["snapshots"]:
                    sentry = {"name": s["name"], "stream_size": s.get("stream_size", 0),
                              "allocation_size": s.get("allocation_size", 0),
                              "snapshot_id": s.get("snapshot_id", None)}
                    ct = s.get("creation_time", 0)
                    if ct: sentry["creation_time"] = _filetime_to_str(ct)
                    fentry["snapshots"].append(sentry)
                json_out["files"].append(fentry)
            print(json.dumps(json_out, indent=2)); return 0

        print("=" * 78)
        print("ReFS Stream Snapshot Analysis")
        print("=" * 78)
        print(f"  Image:        {image}")
        print(f"  ReFS version: {vmaj}.{vmin}")
        print(f"  Cluster size: {_hx(cs)}")
        print(f"  Objects:      {len(obj_map)}")
        print()
        print(f"  Files with snapshots: {len(true_snap_results)}")
        print(f"  Total snapshots:      {total_true}")

        if not true_snap_results:
            print("\n  No files with stream snapshots found."
                  "  (Alternate data streams are listed by `specials ads` / `export ads`.)"); return 0

        print(f"\n{'-'*78}")
        file_filter = args["file"]
        display_list = true_snap_results
        if file_filter:
            display_list = [r for r in display_list if file_filter in r["path"]]
            if not display_list:
                print(f"  No snapshot files matching '{file_filter}'"); return 0

        # --snapshot: pick ONE version per file — a 1-based index number (as shown in the [N] listing),
        # or a case-insensitive substring of the version name. Returns the set of matching names, or None
        # (= all versions). Applied to BOTH the listing and the recovered/extracted streams (matched by
        # name, so the listing index and the recovery stay in lock-step).
        def _sel_names(snaps):
            if not snap_sel: return None
            if snap_sel.lstrip("-").isdigit():
                n = int(snap_sel)
                return {snaps[n - 1]["name"]} if 1 <= n <= len(snaps) else set()
            s = snap_sel.lower()
            return {sn["name"] for sn in snaps if s in (sn.get("name", "") or "").lower()}

        any_sel_match = False
        for r in display_list:
            sel = _sel_names(r["snapshots"])
            if sel is not None and not sel:
                continue                              # this file has no version matching --snapshot
            any_sel_match = any_sel_match or sel is None or bool(sel)
            shown = [s for s in r["snapshots"] if sel is None or s["name"] in sel]
            print(f"\n  FILE {r['path']}")
            if "create_time" in r: print(f"    Created:      {_filetime_to_str(r['create_time'])}")
            if "modify_time" in r: print(f"    Modified:     {_filetime_to_str(r['modify_time'])}")
            print(f"    Resident:     {r['value_len']} bytes")
            if sel is None:
                print(f"    Snapshots:    {len(r['snapshots'])}\n")
            else:
                print(f"    Snapshots:    {len(shown)} of {len(r['snapshots'])} (--snapshot {snap_sel})\n")
            for i, s in enumerate(r["snapshots"]):
                if s["name"] not in [sh["name"] for sh in shown]:
                    continue                          # keep original [N] numbering, show only the selected
                print(f"    [{i+1}] \"{s['name']}\"")
                ct = s.get("creation_time", 0)
                if ct: print(f"        Created:       {_filetime_to_str(ct)}")
                print(f"        Stream size:   {s.get('stream_size', 0)} bytes")
                if verbose:
                    print(f"        Alloc size:    {s.get('allocation_size', 0)} bytes")
                    print(f"        Snap alloc:    {s.get('snapshot_alloc', 0)} bytes")
                    print(f"        Snapshot ID:   {s.get('snapshot_id', '?')}")
                    print(f"        Raw val len:   {s['raw_len']}")

            # Content recovery via the extent chain (CoW prior content)
            if (do_show or extract_dir) and r.get("vd") is not None:
                recs = recover_snapshot_streams(f, ps, cs, tr, r["vd"])
                if sel is not None:
                    recs = [rec for rec in recs if rec["name"] in sel]
                if recs:
                    print(f"\n    Recovered content ({len(recs)} version(s)):")
                for rec in recs:
                    content = rec["content"]
                    if rec["inline"]:
                        status = "inline (in 0x30 body — current version)"
                    elif content is None:
                        status = "no DATA extent"
                    else:
                        status = f"{len(content)} bytes, {rec['n_extents']} extent(s)"
                    print(f"      [{rec['name']}] sub_id=0x{rec['sub_id']:x} "
                          f"size={rec['stream_size']} -> {status}")
                    if content is not None and do_show:
                        preview = content[:120]
                        try:
                            txt = preview.decode("utf-8")
                            shown = txt if all(c.isprintable() or c in "\r\n\t" for c in txt) else preview.hex()
                        except UnicodeDecodeError:
                            shown = preview.hex()
                        print(f"          {shown!r}")
                    if content is not None and extract_dir:
                        safe = (r["path"].strip("/").replace("/", "_") + "__" + rec["name"])
                        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in safe)
                        os.makedirs(extract_dir, exist_ok=True)
                        outp = os.path.join(extract_dir, safe)
                        with open(outp, "wb") as of:
                            of.write(content)
                        print(f"          -> wrote {outp}")

        if snap_sel and not any_sel_match:
            print(f"\n  No snapshot version matched --snapshot {snap_sel!r} "
                  f"(use a 1-based [N] index or part of a version name).")
        return 0

    finally:
        f.close()

def cmd_integrity(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "--verbose", "--checksums", "--fullchecksums"],
                       valued=["--scan-range", "--max-pages"])
    verbose = args["v"] or args["verbose"]
    # fidelity override: raise the full-tree page cap on very large volumes (default 300000)
    max_pages = _int_arg(args["max_pages"], "--max-pages") if args["max_pages"] else 300000
    do_full = args["fullchecksums"]            # entire metadata tree (all object B+-trees)
    do_checksums = args["checksums"] or do_full  # --fullchecksums implies checksum verification

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        # Get volume sig and VC from CHKP
        best_vc = 0; best_volsig = 0; chk_type = 0; best_chk = None
        for cl in chkp_lcns:
            try:
                f.seek(ps + cl * cs); raw = f.read(4 * cs)
                if raw[:4] == b"CHKP":
                    vc = le64(raw, 0x10)
                    if vc >= best_vc:
                        best_vc = vc; best_volsig = le32(raw, 0x0C); best_chk = raw
            except Exception: pass
        f.seek(ps); bs = f.read(512)
        chk_type = le16(bs, 0x2A)
        chk_types = {0: "None", 2: "CRC64", 4: "SHA-256"}

        report = {
            "pages_checked": 0, "pages_valid_sig": 0, "pages_invalid_sig": 0,
            "pages_volsig_match": 0, "pages_volsig_mismatch": 0,
            "pages_vc_ok": 0, "pages_vc_exceed": 0,
            "pages_selfaddr_ok": 0, "pages_selfaddr_bad": 0,
            "btree_inner_ok": 0, "btree_leaf_ok": 0, "btree_struct_error": 0,
            "issues": [], "page_details": [],
        }

        if args["scan_range"]:
            parts = args["scan_range"].split("-")
            try:
                start_lcn = int(parts[0], 0)
                end_lcn = int(parts[1], 0) if len(parts) > 1 else start_lcn + 1
            except (ValueError, IndexError):
                die(f"--scan-range: expected an LCN or A-B range (0x hex ok), got {args['scan_range']!r}")
            # raw forensic scan: each LCN is one standalone cluster to inspect
            pages_to_check = [(lcn, [lcn]) for lcn in range(start_lcn, end_lcn)]
        else:
            visited = set()
            pages_to_check = []
            for idx, root_vlcns in enumerate(roots):
                if not root_vlcns: continue
                use_tr = None if idx in _CT_ROOT_INDICES else tr
                _walk_btree_pages(f, ps, cs, use_tr, root_vlcns, visited, pages_to_check)
            for oid_val, vlcns in obj_map.items():
                _walk_btree_pages(f, ps, cs, tr, vlcns, visited, pages_to_check)

        ct_entries = len(tr.map) if tr else 0
        for head, plcns in pages_to_check:
            try:
                data = b""
                for p in plcns:
                    f.seek(ps + p * cs); data += f.read(cs)
                _check_page(data, head, best_volsig, best_vc, report, verbose)
            except (OSError, OverflowError): pass

        print("=" * 78)
        print("ReFS Metadata Integrity Report")
        print("=" * 78)
        print(f"  Image:           {image}")
        print(f"  ReFS version:    {vmaj}.{vmin}")
        print(f"  Cluster size:    {_hx(cs)}")
        print(f"  Checksum type:   {chk_types.get(chk_type, f'Unknown({chk_type})')}")
        print(f"  Checkpoint VC:   {best_vc}")
        print(f"  Volume sig:      {_hx(best_volsig)}")
        print(f"  Container map:   {ct_entries} entries")
        print()
        print("-" * 78)
        print("Page Statistics")
        print("-" * 78)
        print(f"  Pages checked:           {report['pages_checked']}")
        print(f"  Valid signatures:        {report['pages_valid_sig']}")
        print(f"  Invalid signatures:      {report['pages_invalid_sig']}")
        print(f"  Volume sig matches:      {report['pages_volsig_match']}")
        print(f"  Volume sig mismatches:   {report['pages_volsig_mismatch']}")
        print(f"  VC within bounds:        {report['pages_vc_ok']}")
        print(f"  VC exceeds checkpoint:   {report['pages_vc_exceed']}")
        print(f"  Self-address valid:      {report['pages_selfaddr_ok']}")
        print(f"  Self-address invalid:    {report['pages_selfaddr_bad']}")
        print(f"  B+-tree inner nodes OK:  {report['btree_inner_ok']}")
        print(f"  B+-tree leaf nodes OK:   {report['btree_leaf_ok']}")
        print(f"  B+-tree struct errors:   {report['btree_struct_error']}")
        print()

        # F1: cryptographic page-checksum verification (CRC64 / SHA-256)
        ck_stats = None
        if do_checksums and best_chk is not None:
            dl = le32(best_chk, 0x5C); rc = le32(best_chk, 0x90)
            ck_stats = _verify_page_checksums(f, ps, cs, tr, best_chk, dl, rc,
                                              max_pages=max_pages, full=do_full)
            print("-" * 78)
            scope = "ENTIRE metadata tree" if do_full else "root-table metadata"
            print(f"Page Checksum Verification — {scope} (recomputed vs stored)")
            print("-" * 78)
            tot_ok = ck_stats["crc64_ok"] + ck_stats["sha_ok"]
            tot_bad = ck_stats["crc64_bad"] + ck_stats["sha_bad"]
            if do_full:
                print(f"  Coverage:                full metadata tree "
                      f"(system roots + {ck_stats['objects']} object B+-trees)")
            else:
                print(f"  Coverage:                system root tables only "
                      f"(run --fullchecksums for every object B+-tree)")
            print(f"  Pages verified:          {ck_stats['pages']}")
            print(f"  CRC64  match / mismatch: {ck_stats['crc64_ok']} / {ck_stats['crc64_bad']}")
            print(f"  SHA256 match / mismatch: {ck_stats['sha_ok']} / {ck_stats['sha_bad']}")
            if ck_stats["none"]:
                print(f"  Unchecksummed pages:     {ck_stats['none']}")
            if ck_stats.get("capped"):
                print(f"  NOTE: page cap ({max_pages}) reached — coverage truncated; "
                      f"rerun with --max-pages N for full fidelity")
            if tot_bad:
                print(f"  *** {tot_bad} CHECKSUM MISMATCH(ES) — page content altered/corrupt ***")
                for s0, kind, stored, calc in ck_stats["mismatches"][:20]:
                    print(f"    LCN {_hx(s0)} [{kind}]: stored {stored} != computed {calc}")
            else:
                print(f"  VERDICT: all {tot_ok} checksummed pages VERIFIED — no tampering/corruption")
            print()

        # Redundancy inventory: ReFS keeps a backup boot sector (last LBA), an alternating
        # checkpoint pair, and secondary SUPB copies. Verify they are present + valid so a future
        # recovery mode could fall back to a backup if the primary is corrupt.
        bk = _scan_backup_copies(f, ps, cs, chkp_lcns)
        backup_warn = []
        print("-" * 78)
        print("Redundancy / Backup Copies")
        print("-" * 78)
        v = bk["vbr"]
        pmark = "OK" if v["primary_cksum_ok"] else ("sig-ok, checksum?" if v["primary_ok"] else "BAD")
        print(f"  Boot sector (primary):   LBA 0 — {pmark}")
        if v["backup"] is None:
            print(f"  Boot sector (backup):    not located (no volume-size field)")
        elif v["backup"].get("present"):
            same = "identical to primary" if v["backup"]["matches_primary"] else "DIFFERS from primary"
            ck = "checksum OK" if v["backup"]["cksum_ok"] else "checksum?"
            print(f"  Boot sector (backup):    LBA {v['backup']['lba']} — present, {same}, {ck}")
            if not v["backup"]["matches_primary"]:
                bvr, pvr = v["backup"].get("version"), v["backup"].get("primary_version")
                if bvr and pvr and bvr != pvr:
                    print(f"      ↳ version mismatch: primary v{pvr}, backup v{bvr} — an UPGRADE "
                          f"(the backup keeps the ORIGINAL pre-upgrade version) or VBR tampering.")
                    print(f"        The driver does NOT reconcile the two copies (no cross-copy "
                          f"checksum/clock); the backup is consulted only if the primary fails to READ.")
                    backup_warn.append(f"boot-sector version differs: primary v{pvr} vs backup v{bvr}")
                else:
                    backup_warn.append("backup boot sector differs from primary")
        else:
            print(f"  Boot sector (backup):    LBA {v['backup'].get('lba','?')} — MISSING/unreadable")
            backup_warn.append("backup boot sector missing")
        for rec in bk["checkpoints"]:
            vc = rec.get("vc"); status = "valid" if (rec["sig_ok"] and rec["roots_ok"]) else "INVALID"
            print(f"  Checkpoint [{rec['role']:7}]:   LCN {_hx(rec['lcn'])} — {status}"
                  + (f", vclock={vc}" if vc is not None else ""))
            if rec["role"] == "backup" and status != "valid":
                backup_warn.append(f"backup checkpoint @ {_hx(rec['lcn'])} invalid")
        n_supb = len(bk["supb"])
        supb_lcns = ", ".join(_hx(s["lcn"]) for s in bk["supb"])
        print(f"  Superblock copies:       {n_supb} (LCN {supb_lcns})")
        if n_supb < 2:
            backup_warn.append("fewer than 2 SUPB copies located")
        print()

        has_fail = any(s == "FAIL" for s, _, _ in report["issues"])
        has_warn = any(s == "WARN" for s, _, _ in report["issues"]) or bool(backup_warn)
        ck_bad = (ck_stats["crc64_bad"] + ck_stats["sha_bad"]) if ck_stats else 0
        if backup_warn:
            for w in backup_warn:
                print(f"  [WARN] redundancy: {w}")
        if has_fail or ck_bad:
            verdict = "FAIL — " + ("structural corruption" if has_fail else "") + \
                      (f"{' + ' if has_fail else ''}{ck_bad} checksum mismatch(es)" if ck_bad else "")
        elif has_warn:
            nwarn = sum(1 for s, _, _ in report['issues'] if s == 'WARN') + len(backup_warn)
            verdict = f"WARN — {nwarn} warning(s)" + (" (incl. redundancy)" if backup_warn else "")
        elif ck_stats: verdict = f"PASS — structurally valid AND {ck_stats['crc64_ok']+ck_stats['sha_ok']} page checksums verified"
        else: verdict = "PASS — all metadata pages structurally valid (run --checksums / --fullchecksums to verify CRC64/SHA-256)"
        print("-" * 78)
        print(f"Verdict: {verdict}")
        print("-" * 78)

        if report["issues"]:
            print("\nIssues:")
            for severity, lcn, msg in report["issues"][:50]:
                print(f"  [{severity}] LCN {_hx(lcn)}: {msg}")
            if len(report["issues"]) > 50:
                print(f"  ... and {len(report['issues']) - 50} more issues")

        if verbose and report["page_details"]:
            print(f"\n{'-'*78}\nPage Details\n{'-'*78}")
            for d in report["page_details"][:200]:
                sig_s = d["sig"].decode("ascii", errors="replace") if d["sig"] in _VALID_SIGS else d["sig"].hex()
                status = " ".join(d["issues"]) if d["issues"] else "OK"
                print(f"  LCN {_hx(d['lcn']):<10} {sig_s:<5} {status}")

        # Scriptable exit status: 2 = integrity failure (structural and/or checksum), 0 = clean.
        return 2 if (has_fail or ck_bad) else 0

    finally:
        f.close()

def cmd_export_metadata(image, remaining, partition_start):
    """Export ReFS bootstrap + metadata structures as raw, hash-verified artifacts (the ReFS analogue of
    dumping a raw $MFT): VBR (primary+backup), both checkpoints, SUPB copies, the MLog control+log pages,
    the USN $J stream, and the full object B+-tree forest — plus manifest.json + sha256sums.txt."""
    import hashlib, json as _json
    args = _parse_args(remaining, flags=[],
                       valued=["-o", "--out", "--what", "--btree-mode", "--max-scan"])
    outdir = args["o"] or args["out"]
    if not outdir:
        die("export requires -o OUTDIR")
    what = set((args["what"] or "all").lower().replace(" ", "").split(","))
    def want(x): return "all" in what or x in what
    btree_mode = (args["btree_mode"] or "packed").lower()
    max_scan = _int_arg(args["max_scan"], "--max-scan") if args["max_scan"] else 2000000

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        os.makedirs(outdir, exist_ok=True)
        manifest = {"image": os.path.basename(image), "partition_start_bytes": ps, "cluster_size": cs,
                    "refs_version": f"{vmaj}.{vmin}", "artifacts": []}
        sha_lines = []

        def emit(name, data, source, **meta):
            if not data:
                return
            with open(os.path.join(outdir, name), "wb") as of:
                of.write(data)
            h = hashlib.sha256(data).hexdigest()
            manifest["artifacts"].append(dict(file=name, bytes=len(data), sha256=h, source=source, **meta))
            sha_lines.append(f"{h}  {name}")
            print(f"  + {name:32s} {len(data):>13,d} B  {source}")

        def rd(lcn, nclu=1):
            f.seek(ps + lcn * cs); return f.read(nclu * cs)

        print("=" * 78)
        print(f"ReFS Metadata Export — {os.path.basename(image)} (v{vmaj}.{vmin})")
        print("=" * 78)

        f.seek(ps); vbr = f.read(512)
        total_sectors = le64(vbr, 0x18) if len(vbr) >= 0x20 else 0

        if want("vbr"):
            emit("vbr_primary.bin", vbr, "boot sector @ LBA 0", lba=0)
            if total_sectors > 1:
                try:
                    f.seek(ps + (total_sectors - 1) * 512)
                    emit("vbr_backup.bin", f.read(512), "backup boot sector @ last LBA",
                         lba=total_sectors - 1)
                except (OSError, OverflowError):
                    pass

        if want("chkp"):
            for i, cl in enumerate(chkp_lcns):
                try:
                    d = rd(cl, 4)
                    role = "current" if i == 0 else "alternate"
                    emit(f"checkpoint_{i}_lcn{cl:x}.bin", d, f"CHKP ({role})", lcn=cl)
                except (OSError, OverflowError):
                    pass

        if want("supb"):
            try:
                emit("supb_primary.bin", rd(SUPB_LCN), "SUPB primary @ LCN 0x1e", lcn=SUPB_LCN)
            except (OSError, OverflowError):
                pass
            if total_sectors > 1:
                end_lcn = (total_sectors * 512) // cs
                for lcn in (end_lcn - 2, end_lcn - 3):
                    try:
                        d = rd(lcn)
                        if d[:4] == b"SUPB":
                            emit(f"supb_backup_lcn{lcn:x}.bin", d, "SUPB backup", lcn=lcn)
                    except (OSError, OverflowError):
                        pass

        if want("mlog"):
            try:
                mi = get_mlog_info(f, ps, cs, tr, obj_map)
            except Exception:
                mi = None
            if mi:
                for k in ("ctrl_plcn_0", "ctrl_plcn_1"):
                    if mi.get(k):
                        try:
                            emit(f"mlog_{k}.bin", rd(mi[k]), f"MLog control page ({k})", lcn=mi[k])
                        except (OSError, OverflowError):
                            pass
                # live log pages only (the data area is mostly zero — dump the MLog-signature blocks).
                # The data area is addressed by PHYSICAL LCN (NOT container-translated; structure_reference
                # §E + LogLibraryReadFromCopy reads the raw offset with a NULL table identity), and each
                # cluster packs cs//4096 4 KiB log blocks (16 on 64K volumes). So reuse the validated
                # scan_mlog_data_area (untranslated + per-4 KiB-block) — the same scanner mlog/usn/timeline
                # use — instead of tr.tr()-ing the start (which lands on the wrong cluster: 0 pages on
                # targeted/winsider) and reading one cluster per page (which misses 15/16 blocks on 64K).
                try:
                    ctrl = read_mlog_control(f, ps, cs, mi)
                    blob = bytearray(); idx = []
                    for pg in scan_mlog_data_area(f, ps, cs, tr, mi, ctrl):
                        blk = pg.get("page")
                        if blk and blk[:4] == b"MLog":
                            idx.append((pg["block_lcn"], len(blob))); blob += blk
                            if len(blob) >= max_scan * cs:   # bound the dump
                                break
                    if blob:
                        emit("mlog_log_pages.bin", bytes(blob),
                             f"{len(idx)} live MLog data pages (concatenated)")
                        emit("mlog_log_index.csv",
                             ("block_lcn,byte_offset\n" + "\n".join(f"0x{p:x},{o}" for p, o in idx)).encode(),
                             "index for mlog_log_pages.bin")
                except (OSError, OverflowError, KeyError):
                    pass

        if want("usn"):
            try:
                vd, _em = locate_change_journal(f, ps, cs, tr, obj_map)
                if vd is not None:
                    st = parse_usn_journal_streams(vd, cs, tr)
                    if st.get("j_extents"):
                        jd = read_usn_j_stream(f, ps, cs, st["j_extents"], st["j_stream_size"])
                        emit("usn_J.bin", jd, "USN $J change-journal stream (reassembled)")
            except Exception:
                pass

        if want("btree"):
            # the raw-metadata analogue: every reachable metadata page (system roots + every object tree)
            visited = set(); ptc = []
            for idx, rv in enumerate(roots):
                if rv:
                    _walk_btree_pages(f, ps, cs, (None if idx in _CT_ROOT_INDICES else tr),
                                      rv, visited, ptc)
            # object_table.bin = root 0's pages
            ot_heads = set()
            if roots and roots[0]:
                otv = set(); otp = []
                _walk_btree_pages(f, ps, cs, tr, roots[0], otv, otp)
                ot_heads = {h for h, _ in otp}
            for _oid, vlcns in obj_map.items():
                _walk_btree_pages(f, ps, cs, tr, vlcns, visited, ptc)
            if btree_mode == "per-object":
                # one file per object OID (its tree pages concatenated)
                for oid_val, vlcns in obj_map.items():
                    ov = set(); op = []
                    _walk_btree_pages(f, ps, cs, tr, vlcns, ov, op)
                    blob = bytearray()
                    for head, plcns in op:
                        for p in plcns:
                            blob += rd(p)
                    emit(f"object_{oid_val:x}.btree", bytes(blob), f"OID 0x{oid_val:x} B+-tree", oid=oid_val)
            else:
                blob = bytearray(); idx = ["head_plcn,n_clusters,byte_offset,owner"]
                for head, plcns in ptc:
                    off = len(blob)
                    for p in plcns:
                        blob += rd(p)
                    owner = "object_table" if head in ot_heads else "metadata"
                    idx.append(f"0x{head:x},{len(plcns)},{off},{owner}")
                emit("metadata_pages.bin", bytes(blob), f"{len(ptc)} metadata pages (packed)")
                emit("metadata_index.csv", ("\n".join(idx) + "\n").encode(),
                     "index for metadata_pages.bin")

        with open(os.path.join(outdir, "manifest.json"), "w") as mf:
            _json.dump(manifest, mf, indent=2)
        sha_lines.append(f"{hashlib.sha256(_json.dumps(manifest, indent=2).encode()).hexdigest()}  manifest.json")
        with open(os.path.join(outdir, "sha256sums.txt"), "w") as sf:
            sf.write("\n".join(sha_lines) + "\n")
        print(f"\n  {len(manifest['artifacts'])} artifacts + manifest.json + sha256sums.txt → {outdir}")
        print(f"  Verify later with:  sha256sum -c sha256sums.txt")
        return 0
    finally:
        f.close()

def cmd_dataruns(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "--verbose"], valued=["--oid", "--depth"])
    verbose = args["v"] or args["verbose"]
    start_oid = _int_arg(args["oid"], "--oid", 0) if args["oid"] else 0x600
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 3

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        print("=" * 78)
        print("ReFS File Data Extent Analysis")
        print("=" * 78)
        print(f"  Image:        {image}")
        print(f"  ReFS version: {vmaj}.{vmin}")
        print(f"  Cluster size: {_hx(cs)} ({cs} bytes)")
        print(f"  Containers:   {len(tr.map) if tr else 0}")
        print(f"  Start OID:    {_hx(start_oid)}")
        print()

        if start_oid not in obj_map:
            die(f"OID {_hx(start_oid)} not found in Object Table")

        total_files = 0
        total_resident = 0
        total_nonresident = 0
        total_with_extents = 0
        all_results = []

        def process_dir(dir_oid, path, depth):
            nonlocal total_files, total_resident, total_nonresident, total_with_extents
            results = _analyze_dir_extents(f, ps, cs, tr, obj_map, dir_oid)
            for info in results:
                total_files += 1
                full_path = f"{path}/{info['name']}" if path else info['name']
                info["path"] = full_path
                if info["storage"] == "resident":
                    total_resident += 1
                else:
                    total_nonresident += 1
                    if info["extents"]:
                        total_with_extents += 1
                all_results.append(info)
            if depth > 0:
                dir_rows = walk_bplus(f, ps, cs, tr, obj_map[dir_oid])
                for kd, vd in dir_rows:
                    if len(kd) >= 4 and le16(kd, 0) == 0x30 and len(vd) >= 0x44:
                        child_attrs = le32(vd, 0x40)
                        if child_attrs & 0x10000000:
                            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
                            if child_oid and child_oid in obj_map:
                                child_name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
                                child_path = f"{path}/{child_name}" if path else child_name
                                process_dir(child_oid, child_path, depth - 1)

        process_dir(start_oid, "", max_depth)

        print(f"  Summary:")
        print(f"    Total files analyzed:   {total_files}")
        print(f"    Resident (inline):      {total_resident}")
        print(f"    Non-resident (extents): {total_nonresident}")
        print(f"    With decoded extents:   {total_with_extents}")
        print()

        print("=" * 78)
        print("File Data Locations")
        print("=" * 78)

        for info in all_results:
            if info["storage"] == "resident":
                if verbose:
                    print(f"  RESIDENT  {info['path']}")
                    print(f"            size={info['file_size']} (data inline in directory entry)")
            else:
                if info["extents"]:
                    total_ext_clusters = sum(e["clusters"] for e in info["extents"])
                    print(f"  EXTENT    {info['path']}")
                    print(f"            size={info.get('file_size',0)}, "
                          f"attrs={_attrs_to_str(info['file_attrs'], full=False)}, "
                          f"extents={len(info['extents'])}, "
                          f"clusters={total_ext_clusters}")
                    if info.get("timestamps"):
                        print(f"            created={_filetime_to_str(info['timestamps'][0]).replace(' UTC', '')}")
                    if verbose:
                        for ext in info["extents"]:
                            print(f"            run: fvcn={ext['file_vcn']} "
                                  f"VLCN={_hx(ext['vlcn'])} "
                                  f"PLCN={_hx(ext['plcn'])} "
                                  f"clusters={ext['clusters']} "
                                  f"disk={_hx(ext['disk_offset'])}")
                        src = info.get("extent_source", "?")
                        if src == "remote":
                            print(f"            (extents in remote OID {_hx(info.get('target_oid', 0))})")
                elif verbose:
                    print(f"  NOEXTENT  {info['path']}")
                    print(f"            size={info.get('file_size',0)} "
                          f"(extents not decoded — may be in remote OID {_hx(info.get('target_oid', 0))})")

        return 0

    finally:
        f.close()


SUBCOMMANDS = {
    "files":       "List files and directories (default)",
    "summary":     "Extended volume summary — full directory walk + all metrics",
    "search":      "Search files/directories by name (PATTERN; add --regex)  [alias: find]",
    "details":     "All attributes for one object by path or OID (/path | 0xOID | --path | --oid)",
}
# Still callable + documented (`fastsummary --help`), but hidden from --list/overview to reduce option
# overload — `summary` is a strict content superset. (Q7.)
HIDDEN_SUBCOMMANDS = {
    "fastsummary": "Extended quick summary — volume metrics, no directory walk (hidden alias of a fast summary)",
}
# Command-token aliases resolved to their canonical name at dispatch (Phase 0). Nothing is removed — the
# canonical spellings keep working; these are friendlier / clearer synonyms.
SUBCOMMAND_ALIASES = {
    "find": "search",       # friendlier name for the name search
    "snapshot": "snapshots", # singular convenience alias for the analysis command (distinct from `export snapshot`)
}
# ─── Export umbrella (Q8 + the user's "export command" idea) — one home for "get data out" ────────
def _safe_relpath(path):
    """Turn a stored '/dir/sub/file' path into a safe on-disk relative name."""
    parts = [p for p in path.replace("\\", "/").split("/") if p and p not in (".", "..")]
    return os.path.join(*[("".join(c if (c.isalnum() or c in " ._-") else "_" for c in p)) for p in parts]) if parts else "unnamed"

def cmd_export_resident(image, remaining, partition_start):
    """export resident-all <dir>: write every RESIDENT file's inline $DATA (and CoW-shared resident content)
    to <dir>, preserving the directory tree. Reuses the same content path as `extract` (get_resident_data_content
    / recover_cow_current_content); skips 0-byte and non-inline entries."""
    args = _parse_args(remaining, valued=["--oid", "--depth"])
    out_dir = args["_rest"][0] if args["_rest"] else None
    if not out_dir:
        die("export resident-all requires an output directory")
    start_oid = _int_arg(args["oid"], "--oid", 0) if args["oid"] else 0x600
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 8
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))
    try:
        os.makedirs(out_dir, exist_ok=True)
        written = 0; skipped = 0
        def walk(dir_oid, path, depth):
            nonlocal written, skipped
            for info in _analyze_dir_extents(f, ps, cs, tr, obj_map, dir_oid):
                if info.get("storage") != "resident":
                    continue
                content = info.get("resident_content")
                if content is None:
                    content = info.get("cow_content")
                if content is None or len(content) == 0:
                    skipped += 1; continue
                rel = _safe_relpath(f"{path}/{info['name']}" if path else info["name"])
                dest = os.path.join(out_dir, rel)
                os.makedirs(os.path.dirname(dest) or out_dir, exist_ok=True)
                with open(dest, "wb") as o:
                    o.write(content)
                written += 1
            if depth > 0:
                for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[dir_oid]):
                    if len(kd) >= 4 and le16(kd, 0) == 0x30 and len(vd) >= 0x44 and (le32(vd, 0x40) & 0x10000000):
                        child = le64(vd, 0x08) if len(vd) >= 0x10 else 0
                        if child and child in obj_map:
                            nm = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
                            walk(child, f"{path}/{nm}" if path else nm, depth - 1)
        if start_oid not in obj_map:
            die(f"OID {_hx(start_oid)} not found")
        walk(start_oid, "", max_depth)
        print(f"[{PROG}] export resident-all: wrote {written} resident files to {out_dir} "
              f"({skipped} skipped: 0-byte or non-inline). source: inline $DATA / CoW-shared.", file=sys.stderr)
        return 0
    finally:
        f.close()

def cmd_export_recyclebin(image, remaining, partition_start):
    """export recyclebin <dir>: write each surviving $R payload from $RECYCLE.BIN to <dir>, named by its
    decoded original filename ($I). Reuses the recyclebin walk + the resident/extent content path."""
    args = _parse_args(remaining, valued=[])
    out_dir = args["_rest"][0] if args["_rest"] else None
    if not out_dir:
        die("export recyclebin requires an output directory")
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))
    try:
        recycle_oid = None
        if 0x600 in obj_map:
            for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x600]):
                if len(kd) >= 4 and le16(kd, 0) == 0x30 and len(vd) >= 0x10 and \
                        kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00") == "$RECYCLE.BIN":
                    recycle_oid = le64(vd, 0x08); break
        if recycle_oid is None:
            print(f"[{PROG}] no $RECYCLE.BIN on this volume", file=sys.stderr); return 0
        recs = []
        _walk_recycle(f, ps, cs, tr, obj_map, recycle_oid, "", 8, recs)
        os.makedirs(out_dir, exist_ok=True)
        written = 0
        # map $R name -> its content by walking each SID dir's $R rows through _analyze_dir_extents
        r_content = {}
        def collect(dir_oid, sid):
            for info in _analyze_dir_extents(f, ps, cs, tr, obj_map, dir_oid):
                if info["name"].startswith("$R"):
                    c = info.get("resident_content") or info.get("cow_content")
                    if c is None and info.get("extents"):
                        buf = bytearray()
                        for e in sorted(info["extents"], key=lambda x: x["file_vcn"]):
                            for i in range(e["clusters"]):
                                f.seek(ps + (e["plcn"] + i) * cs); buf += f.read(cs)
                        c = bytes(buf[:info.get("file_size", len(buf))])
                    if c is not None:
                        r_content[(sid, info["name"])] = c
            for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[dir_oid]):
                if len(kd) >= 4 and le16(kd, 0) == 0x30 and len(vd) >= 0x44 and (le32(vd, 0x40) & 0x10000000):
                    child = le64(vd, 0x08) if len(vd) >= 0x10 else 0
                    if child and child in obj_map:
                        nm = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
                        collect(child, sid or nm)
        collect(recycle_oid, "")
        for r in recs:
            content = r_content.get((r["sid"], r["r_name"]))
            if content is None:
                continue
            orig = r["meta"]["original_path"] if r.get("meta") else r["r_name"]
            dest = os.path.join(out_dir, _safe_relpath(orig.replace("\\", "/").split("/")[-1] or r["r_name"]))
            with open(dest, "wb") as o:
                o.write(content)
            written += 1
        print(f"[{PROG}] export recyclebin: wrote {written} recovered payload(s) to {out_dir}.", file=sys.stderr)
        return 0
    finally:
        f.close()

# `snapshots` is the primary name for extracting stream snapshots (0xB0, storage_type≠0, sub_id≥0x1000 —
# true CoW snapshot versions). `snapshot` and the older `prior-versions` are kept as aliases.
def cmd_export_reparse(image, remaining, partition_start):
    """export reparse [--json] [-o FILE]: the reparse-point inventory (decoded targets/tags/kind). Prints the
    human-readable TEXT view by default (same as the `reparse` command); add --json for the machine-readable
    form. Reparse data is metadata, not bulk content, so it prints to the screen (add -o FILE to save)."""
    args = _parse_args(remaining, flags=["--json"], valued=["-o", "--output"])
    outp = args["o"] or args["output"]
    inner = ["--json"] if args["json"] else []
    fmt = "JSON" if args["json"] else "text"
    if outp:
        with open(outp, "w") as fh:
            _old = sys.stdout
            sys.stdout = fh
            try:
                cmd_reparse(image, inner, partition_start)
            finally:
                sys.stdout = _old
        print(f"[{PROG}] reparse inventory ({fmt}) written to {outp}", file=sys.stderr)
        return 0
    rc = cmd_reparse(image, inner, partition_start)
    print(f"[{PROG}] (reparse inventory above, {fmt} — add `--json` for machine-readable, `-o FILE` to save)", file=sys.stderr)
    return rc

def _auto_export_dir(what):
    """Timestamped output dir for a bulk export when the user omits one (Q2 UX: bulk content can't go to the
    screen, so land it in a predictable folder instead of erroring). Named forefst_export_<what>_<stamp>."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"forefst_export_{what}_{stamp}"

# subverbs that write into a DIRECTORY (bulk); file/ads/reparse/metadata print to stdout or -o instead.
_EXPORT_BULK = ("resident-all", "snapshots", "snapshot", "prior-versions", "deleted", "recyclebin")
_EXPORT_SUBVERBS = ("file", "ads", "reparse", "resident-all", "snapshots", "snapshot", "prior-versions",
                    "deleted", "recyclebin", "metadata")
def cmd_export(image, remaining, partition_start):
    """export <what> — one home for getting data out. Subverbs: file <path> · ads <path:stream> · reparse ·
    resident-all [dir] · snapshots [dir] · deleted [dir] · recyclebin [dir] · metadata [-o dir]. A bulk
    subverb with NO directory auto-creates a timestamped one; `extract …` = `export file`; bare `export -o
    DIR` = `export metadata`; `snapshot`/`prior-versions` alias `snapshots`."""
    if remaining and remaining[0] in _EXPORT_SUBVERBS:
        what, rest = remaining[0], remaining[1:]
        if what in ("file", "ads"):
            return cmd_extract(image, rest, partition_start)
        if what == "reparse":
            return cmd_export_reparse(image, rest, partition_start)
        if what == "metadata":
            return cmd_export_metadata(image, rest, partition_start)
        # bulk (directory) subverbs. The output dir is the FIRST bare positional; we skip the VALUE of a
        # valued flag (e.g. `--max-scan 6000`) so 6000 is not mistaken for the dir. If the user gave NO dir,
        # auto-create a timestamped one (Q2 UX) instead of erroring — bulk content cannot go to the screen.
        _VALUED = {"--search", "--max-scan", "--file", "--depth", "--oid", "--snapshot"}
        out_idx, skip = None, False
        for i, a in enumerate(rest):
            if skip:
                skip = False; continue
            if a in _VALUED:
                skip = True; continue
            if not a.startswith("-"):
                out_idx = i; break
        if out_idx is None:
            out_dir = _auto_export_dir(what)
            passthrough = list(rest)
            print(f"[{PROG}] no output directory given — writing to ./{out_dir}/", file=sys.stderr)
        else:
            out_dir = rest[out_idx]
            passthrough = rest[:out_idx] + rest[out_idx + 1:]
        if what == "resident-all":
            return cmd_export_resident(image, [out_dir] + passthrough, partition_start)
        if what == "recyclebin":
            return cmd_export_recyclebin(image, [out_dir] + passthrough, partition_start)
        if what in ("snapshots", "snapshot", "prior-versions"):
            return cmd_snapshots(image, ["--extract", out_dir] + passthrough, partition_start)
        if what == "deleted":
            return cmd_deleted(image, ["--extract", out_dir, "--_from-export"] + passthrough, partition_start)
    # no recognized subverb (or a bare -o …) => the metadata bundle (back-compat with the old `export`)
    return cmd_export_metadata(image, remaining, partition_start)

# Delegated forensic subcommands (Phase 2) — own option parsing; routed before argparse.
FORENSIC_SUBCOMMANDS = {
    "usn":       "USN (Change) Journal parser — file change records (-v/--stats/--json/--info/--csv FILE)",
    "mlog":      "MLog (durable log) parser — redo records and transactions (-v/--parse/--stats/--json/--raw-scan/--info)",
    "timeline":  "Super-timeline — merge USN + MLog + $SI MACB, sorted by time (--csv/--no-si/--file/--oid/--limit/--source/--depth)",
    "timestomp": "Timestamp-anomaly detection — $SI MACB vs USN, flags back-dating (--all/--json/--csv/--min/--margin-days/--depth)",
    "extract":   "Extract a file's content to stdout by path or --oid (--oid/--depth)",
    "security":  "Security descriptors / ACLs per object (-v/--files/--json/--audit/--sid/--file)",
    "specials":  "Special-attribute files — ads/reparse/wsl/hardlink/sparse/encrypted/compressed/integrity/ea/snapshot (specials [type|all])",
    "reparse":   "Reparse points — symlinks/junctions/WSL + the reparse index (-v/--index/--json/--tag/--file)",
    "deleted":   "Deleted-file VIEW + recoverability verdict — slack scan runs by default (--no-slack/--trash/--scan-pages; write with `export deleted`)",
    "recyclebin": "Decode $RECYCLE.BIN $I metadata — original path, deletion time, size, $R payload (--json)",
    "snapshots": "Stream snapshots (CoW versions) — list / preview / extract (-v/--json/--show/--extract)",
    "integrity": "Verify metadata-page checksums (-v/--checksums/--fullchecksums)",
    "export":    "Get data out — export file|ads|reparse|resident-all|snapshots|deleted|recyclebin|metadata (screen or -o/auto-dir)",
    "dataruns":  "File data extents / data-runs per object (-v/--oid/--depth)",
}
FORENSIC_HANDLERS = {"usn": cmd_usn, "mlog": cmd_mlog, "timeline": cmd_timeline,
                     "timestomp": cmd_timestomp, "extract": cmd_extract, "security": cmd_security,
                     "reparse": cmd_reparse, "deleted": cmd_deleted, "snapshots": cmd_snapshots,
                     "recyclebin": cmd_recyclebin, "specials": cmd_specials,
                     "integrity": cmd_integrity, "export": cmd_export, "dataruns": cmd_dataruns}

# F13: `files --filter <category>` subsets the listing by attribute category (folds in / retires the
# old `attributes` command). Field-based and EA-SAFE — WSL is detected via the reparse tag, NOT the
# EA-derived lx_mode. Output stays forefst's normal files CSV/JSON, just the matching rows.
# `files --filter <type>` predicates. The 10 types that also exist as `specials <type>` DELEGATE to the
# single SPECIALS_TYPES definition (via _SPECIALS_BY_NAME) so the two commands can never drift apart (D2);
# the 3 view-only types (directory/resident/deleted) have no `specials` equivalent and live here.
FILE_FILTERS = {name: pred for name, _desc, pred in SPECIALS_TYPES}
FILE_FILTERS.update({
    "directory":  lambda r: bool(r.get("is_dir")),
    "resident":   lambda r: bool(r.get("is_resident")),
    "deleted":    lambda r: bool(r.get("is_deleted")),
})
VERSION_NOTE = ("Validated on ReFS 3.14 (24H2). All versions 3.4-3.14 parse, but some enriched fields "
                "(e.g. non-resident symlink targets) may be incomplete on 3.4-3.10.")

# ── Output-field provenance: which emitted values are NOT 100% certain, and why ──────────────────
# Honesty layer for `forefst --provenance`. Each entry is a DOCUMENTED FACT with a citation into the
# verified reference (errata E-NN / structure_reference §/finding), NOT a guess. `certainty`:
#   CONDITIONAL     — correct only under a stated condition (a bit/version); may be wrong otherwise
#   METHOD-DEPENDENT— correct only if a secondary record resolves; under-reports if it doesn't
#   BOUNDED         — a heuristic with an explicit validity window; blind outside it
#   NOT-EMITTED     — deliberately omitted because the underlying fact is UNCONFIRMED on disk
# This table changes NO parsed value; it only lets the tool state where its own output is uncertain.
FIELD_PROVENANCE = {
    "HasEA / FileAttributes(EA bit)": (
        "METHOD-DEPENDENT",
        "For a NON-resident file the base file_attrs are read from the type-0x30 pointer (+0x40), which "
        "UNDER-reports the EA bit (0x40000); forefst then OR's the EA bit back in from the type-0x40 backing "
        "(+0x48) when that backing resolves. If the backing does NOT resolve, HasEA can be under-reported "
        "(never over-reported).",
        "errata E56 (pointer +0x40 vs backing +0x48; winsider: pointer omits EA on 8,140 files)"),
    "ReparseTag": (
        "CONDITIONAL",
        "The type-0x40 backing +0x7C ReparseTag mirror is valid ONLY when its bit31 is set; when bit31 is "
        "clear the mirror is 0 and the authoritative tag lives in the type-0xC0 reparse sub-record.",
        "structure_reference §C.3 (+0x7C 'valid only when bit31 set') / §C.8"),
    "IsDirectory": (
        "CONDITIONAL",
        "Derived from file_attrs bit 0x10000000, which is MASKED on Win10 / ReFS v3.4 (preserved on Win11). "
        "On a v3.4 volume a real directory can read IsDirectory=False.",
        "docs/attributes/STANDARD_INFORMATION.md ($SI+0x20 'bit 28 masked on Win10')"),
    "USN (per-file LastUsn)": (
        "CONDITIONAL",
        "Read from $SI+0x40; meaningful only against its journal epoch ($SI+0x48 UsnJournalId). Nonzero only "
        "on volumes captured with an ACTIVE USN journal; a re-created journal makes an old LastUsn stale.",
        "errata E27 / E45 (LastUsn @ $SI+0x40, UsnJournalId @ +0x48; nonzero on 9/111 corpus images)"),
    "TimestompFlags (MLog/slack corroboration)": (
        "BOUNDED",
        "The scan-based timestamp corroboration only recognises FILETIMEs inside 2012-12-14..2044-08-23 "
        "(_FT window) and grades slack rows sane only inside 2009-11-26..2050-12-24 (_SANE). Back-dating "
        "outside those windows is invisible to those channels.",
        "forefst.py symbols _FT_MIN/_FT_MAX and _SANE — measured bounds (grep the names)"),
    "SparseGhosted (NOT emitted)": (
        "NOT-EMITTED",
        "forefst deliberately emits NO per-file sparse/ghosted column: the candidate sparse flag (DATA "
        "value+0x50 bit31) is UNCONFIRMED (0/31,678 set in the corpus; no sparse non-resident file exists to "
        "positively test it). Emitting it would risk a false forensic signal.",
        "structure_reference § DATA value+0x50 (finding #307, marked UNCONFIRMED)"),
    "TimestompFlags / deleted --slack (confidence tier)": (
        "CONDITIONAL",
        "These commands already print an explicit HIGH/MEDIUM/LOW (timestomp) or high/medium/partial "
        "(slack) confidence per row — read that column; a lower tier means fewer independent sources agreed.",
        "forefst.py symbols cmd_timestomp tiering / _scan_page_slack _SANE grading (grep the names)"),
}


def _print_field_provenance():
    """`forefst --provenance` — list every emitted field whose value is NOT 100% certain, with the
    condition and a citation into the verified reference. Needs no image; changes no parsed output."""
    print("forefst output-field provenance — where the tool's own output is NOT 100% certain")
    print("(each is a documented fact with a citation; certainty classes: CONDITIONAL / METHOD-DEPENDENT /")
    print(" BOUNDED / NOT-EMITTED). Fields not listed here are disk-confirmed (RD) in the reference register.\n")
    for field, (certainty, why, cite) in FIELD_PROVENANCE.items():
        print(f"  {field}")
        print(f"      certainty : {certainty}")
        print(f"      condition : {why}")
        print(f"      cite      : {cite}\n")
    print(f"{len(FIELD_PROVENANCE)} field-provenance notes. Everything else forefst emits is RD-confirmed.")


# ── Hand-written per-command help ────────────────────────────────────────────
# Each entry: tagline, a short description, the option list (flag, help), and runnable examples.
# Rendered by `forefst <image> <cmd> --help` / `forefst help <cmd>`; the option text mirrors what the
# command actually parses. Global format flags shared by the native commands: --json/--jsonl/--body/-o.
GLOBAL_HELP = ("Native subcommands (files/summary/fastsummary/search/details) take -o/--output FILE, "
               "--json, --jsonl, --body, -q/--quiet (silence stderr progress). --partition-start BYTES "
               "works on any subcommand; each forensic subcommand has its own flags (see its --help).")

CMD_HELP = {
 "files": {
  "tag": "List files and directories (the default subcommand) as enriched rows",
  "desc": ["Walks the directory B+-tree from the root object (OID 0x600) and emits one row per file/",
           "directory: timestamps, attributes, owner+group SID, ADS, EA, reparse, integrity,",
           "compression, encryption, hard-link names & counts, snapshot counts, USN, allocated size,",
           "FileId/HomeOid join keys, IsSparse. The ReFS equivalent of an MFT listing/bodyfile. Default",
           "output is a 38-column CSV (OID..RefsVersion)."],
  "opts": [("--json | --jsonl | --body", "output format instead of CSV (mutually exclusive)"),
           ("-o, --output FILE", "write to FILE instead of stdout"),
           ("--full-path-column", "append a FullPath column (ParentPath/FileName) to the CSV"),
           ("--filter CATEGORY", "keep only one category: reparse, encrypted, compressed, integrity, ea,"),
           ("", "ads, wsl, sparse, snapshot, directory, resident, deleted, hardlink"),
           ("--deleted", "also recover deleted files (Trash + orphans + checkpoint diff)"),
           ("--cow-before IMAGE", "recover prior CoW versions by diffing against an earlier image"),
           ("--timestomp", "add the TimestompFlags column ($SI heuristic; corroborate with `timestomp`)"),
           ("--depth N", "max directory recursion depth (default 100)"),
           ("-q, --quiet", "suppress stderr progress")],
  "ex": [("files -o listing.csv", "full CSV file listing to a file"),
         ("files --filter hardlink", "only entries with more than one hard link"),
         ("files --filter ea --json", "non-resident & resident EA-bearing files as JSON"),
         ("files --deleted --body -o timeline.body", "bodyfile incl. recovered deleted files (mactime)")],
 },
 "summary": {
  "tag": "Full volume triage report (identity + integrity + content census)",
  "desc": ["One-shot triage: volume identity (version, GUID/label, cluster/container size, checksum",
           "type), anchoring VBR/SUPB/CHKP hashes, on-disk state (original/upgraded/native), the 13",
           "root-table row counts, USN-journal status + UsnJournalId, then a full directory walk for",
           "file/dir/resident counts, total size, MACB extremes, and encrypted/integrity/compressed/",
           "hard-link/snapshot/ADS tallies. Extended-by-default."],
  "opts": [("--json", "emit one JSON object instead of the text report"),
           ("--hash-image", "also SHA-256 the whole image (chain-of-custody; streams the image)"),
           ("--depth N", "max recursion depth for the content census (default 100)"),
           ("-q, --quiet", "suppress stderr progress")],
  "ex": [("summary", "full text triage report"),
         ("summary --json", "same data as one JSON object for jq/pipelines"),
         ("summary --hash-image", "add a full-image SHA-256 for evidence integrity")],
 },
 "fastsummary": {
  "tag": "Fast volume profile — metrics only, no directory walk",
  "desc": ["Everything `summary` reports about volume identity, layout, root-table counts and anchoring",
           "hashes, but WITHOUT the directory walk — so it returns in seconds on large images. Use it",
           "to triage before committing to a full `files`/`summary` pass."],
  "opts": [("--json", "emit one JSON object instead of the text report"),
           ("--hash-image", "also SHA-256 the whole image"),
           ("-q, --quiet", "suppress stderr progress")],
  "ex": [("fastsummary", "fast volume profile"),
         ("fastsummary --json", "machine-readable profile"),
         ("fastsummary --hash-image --json", "profile + full-image SHA-256")],
 },
 "search": {
  "tag": "Find files/directories by name",
  "desc": ["Case-insensitive substring match on the file/directory name across the whole tree (add",
           "--regex for a Python regex against the basename). Prints a table by default."],
  "opts": [("PATTERN", "(positional) the name substring, or regex with --regex"),
           ("--regex", "treat PATTERN as a case-insensitive regular expression"),
           ("--deleted", "also include Trash-table (OID 0xD) objects (matches marked [DEL]); use the `deleted` command for full orphan/checkpoint recovery"),
           ("--json | --jsonl", "emit matches as JSON / JSON Lines"),
           ("-q, --quiet", "suppress stderr progress")],
  "ex": [("search report", "names containing 'report'"),
         ("search '^link\\d+_to' --regex", "regex on the basename"),
         ("search secret --deleted", "include deleted/Trash objects")],
 },
 "details": {
  "tag": "All attributes for ONE object, by path or OID",
  "desc": ["Full record for a single file, directory or object: timestamps, attributes (incl. EA),",
           "SecurityId/owner, USN, reparse target, and — for resident files — the inline sub-records",
           "($DATA, ADS, $EA/WSL metadata, snapshots). Address it by /path, 0xOID, or --path/--oid."],
  "opts": [("/path", "(positional) e.g. /dir/file.txt — a leading slash means path"),
           ("0xOID", "(positional) e.g. 0x705 — a 0x prefix means OID"),
           ("--path P / --oid O", "explicit addressing (same as the positional forms)"),
           ("--json", "emit the full record as JSON")],
  "ex": [("details /wsltests/lxsymlink", "inspect a reparse/WSL file by path"),
         ("details 0x705", "inspect a directory object by OID"),
         ("details /dir/file.txt --json", "machine-readable full record")],
 },
 "usn": {
  "tag": "USN (Change) Journal — file change records",
  "desc": ["Parses the $UsnJrnl:$J change journal: per-record USN, timestamp, reason flags, resolved",
           "file name and FileID. Use --info for journal health, --stats for an activity summary."],
  "opts": [("-v, --verbose", "add RecLen/Version/StreamOffset per record (list mode)"),
           ("--info", "journal metadata instead of records ($J extents, $Max, record count)"),
           ("--stats", "activity summary: reason-code distribution, busiest files, time range"),
           ("--csv FILE", "export all records to a 16-column CSV"),
           ("--json", "emit {journal, record_count, records[]}")],
  "ex": [("usn", "list every change record"),
         ("usn --info", "journal layout & health"),
         ("usn --stats", "reason-code & busiest-file summary"),
         ("usn --csv usn.csv", "export records to CSV")],
 },
 "mlog": {
  "tag": "MLog (durable transaction log) — redo records & concrete actions",
  "desc": ["Parses the durable logfile: control header, data-area page census, and the redo records.",
           "--parse groups the low-level redo opcodes of each transaction into a CONCRETE ACTION and",
           "resolves the object. MOVE vs RENAME is decided by FACT — the parent-directory OID of the old",
           "name entry vs the new one (same parent = RENAME, changed = MOVE, shown as 'parent 0x.. -> 0x..').",
           "DELETE is only reported when the object's own table is destroyed (RedoDeleteTable); a bare row",
           "removal is ENTRY_REMOVE, and a reparent record that can't be resolved to move-or-rename is",
           "REPARENT. Actions are grouped into file operations (CREATE/WRITE/RENAME/MOVE/DELETE) vs the",
           "low-level B+-tree/metadata records that accompany them. -v prints each redo record with its",
           "opcode, target OID and PLCN+offset so every field is verifiable against the raw disk bytes."],
  "opts": [("-v, --verbose", "byte-level proof: each redo record as opcode/name/target_oid/@PLCN+offset/key"),
           ("--parse", "reconstruct concrete actions (CREATE/WRITE/RENAME/MOVE/DELETE + low-level groups)"),
           ("--stats", "opcode-frequency section"),
           ("--raw-scan", "per-page raw dump instead of the data-area summary"),
           ("--info", "static opcode/action reference text only"),
           ("--csv FILE", "export transactions (action + opcodes + oid + plcn) to CSV"),
           ("--json", "emit version/control/mlog_info/data_area/records as JSON")],
  "ex": [("mlog", "control header + page census + redo counts"),
         ("mlog --parse", "concrete file operations + low-level records, with MOVE/RENAME parent OIDs"),
         ("mlog --parse -v", "same, plus the per-record byte-level proof (opcode/OID/@PLCN+offset)"),
         ("mlog --csv mlog_txns.csv", "export the action timeline")],
 },
 "timeline": {
  "tag": "Super-timeline — merge USN + MLog + $SI MACB, time-sorted",
  "desc": ["Merges three event sources (USN journal, MLog transactions, $SI MACB timestamps) into one",
           "chronological timeline. --fast/--no-si skips the slow per-file $SI walk (USN+MLog only)."],
  "opts": [("--fast / --no-si", "skip the $SI MACB walk (USN + MLog only — much faster)"),
           ("--csv", "emit CSV to stdout (timestamp_utc,source,oid,name,event)"),
           ("--source S", "keep only one source: USN / MLOG / SI"),
           ("--file SUB", "keep events whose name/path contains SUB"),
           ("--oid O", "keep only events for object O (0x hex or decimal)"),
           ("--limit N", "keep only the first N events after filtering+sorting"),
           ("--depth N", "max recursion depth for the $SI walk (default 12)")],
  "ex": [("timeline --fast --limit 50", "first 50 USN+MLog events (quick)"),
         ("timeline --csv > timeline.csv", "full super-timeline as CSV"),
         ("timeline --file hello.txt", "all events touching hello.txt"),
         ("timeline --source USN --oid 0x701", "one object's USN history")],
 },
 "timestomp": {
  "tag": "Timestamp-anomaly detection — investigative info, not proof",
  "desc": ["Flags timestamps that LOOK anomalous (investigative INFORMATION, NOT proof of tampering). Each",
           "row shows a BASIS: an AUTHORITATIVE signal (USN journal FILE_CREATE / BASIC_INFO_CHANGE, or the",
           "ReFS-native HARDLINK_MACB_MISMATCH where two names of one file have divergent Created — only the",
           "back-dated name is flagged, the sibling keeps the true birth) vs a HEURISTIC $SI-only signal",
           "(CHANGE_LATE / PRE_FORMAT / CREATE_GT_MODIFY / FUTURE) that also fires on legitimate timestamp-",
           "preserving copies. Tiers HIGH/MEDIUM/LOW by how many independent sources agree. The `files",
           "--timestomp` column shows only the $SI heuristic; this subcommand adds the authoritative checks."],
  "opts": [("--all", "include every file, even those with no anomaly (NONE tier)"),
           ("--min LEVEL", "minimum confidence to report: HIGH | MEDIUM | LOW (default LOW)"),
           ("--margin-days N", "comparison tolerance in days (default 1)"),
           ("--csv FILE", "write CSV (use '-' for stdout)"),
           ("--json", "emit a JSON report to stdout"),
           ("--depth N", "max recursion depth (default 20)")],
  "ex": [("timestomp", "list all flagged files (LOW and up)"),
         ("timestomp --min HIGH", "high-confidence suspects only"),
         ("timestomp --csv suspects.csv --min MEDIUM", "export medium+ suspects")],
 },
 "extract": {
  "tag": "Extract a file's content (or one ADS) to stdout",
  "desc": ["Recovers a file's bytes and writes them to stdout (redirect to a file): non-resident files from",
           "their extents, RESIDENT files from their inline $DATA, and CoW resident files unmodified since a",
           "snapshot from the shared latest-snapshot blocks. Address by bare name, absolute /path, or --path;",
           "use name:stream for an inline ADS. (Large sparse/extent-backed files: use `dataruns` for the map.)"],
  "opts": [("filename | /path", "(positional) the file to extract"),
           ("--path P", "address the file by path (symmetric with details)"),
           ("--oid O", "re-root the search at object O (0x hex or decimal)"),
           ("--depth N", "max recursion depth for locating the file (default 3)")],
  "ex": [("extract /specials/gamma.bak > out.bak", "carve a file by absolute path"),
         ("extract report.dat:hidden_6247 > s.bin", "extract one inline ADS"),
         ("extract deep.log --oid 0x73c --depth 5", "scope the search to a subtree")],
 },
 "security": {
  "tag": "Security descriptors / ACLs per object",
  "desc": ["Lists each security descriptor (owner, group, control flags, DACL/SACL ACEs). --files maps",
           "every file to its SecurityId+owner; --audit recomputes the $Secure hash to detect tampering."],
  "opts": [("-v, --verbose", "include the raw SD hex dump (list / --sid mode)"),
           ("--files", "map every file/dir to its SecurityId and owning SID"),
           ("--file SUB", "like --files, filtered to names containing SUB"),
           ("--sid ID", "print only the descriptor for SecurityId ID (0x hex or decimal)"),
           ("--audit", "tamper check: recompute each SD's content hash"),
           ("--json", "machine-readable output")],
  "ex": [("security", "list all security descriptors"),
         ("security --files", "map files to owners"),
         ("security --audit", "verify SD hashes (tamper check)"),
         ("security --sid 0x1db3cc93d -v", "one descriptor + raw hex")],
 },
 "reparse": {
  "tag": "Reparse points — symlinks/junctions/WSL + the reparse index",
  "desc": ["Audits reparse points: walks the tree for files with the REPARSE_POINT attribute and decodes",
           "each buffer (tag, target, WSL UID/GID/mode). --index dumps the reparse index object (0x540)."],
  "opts": [("-v, --verbose", "include the raw reparse-buffer hex / index key bytes"),
           ("--index", "switch to the reparse INDEX view (OID 0x540) keyed by tag"),
           ("--tag T", "filter to one reparse tag (0x hex or decimal)"),
           ("--file SUB", "default mode: filter to names containing SUB"),
           ("--json", "machine-readable output")],
  "ex": [("reparse", "list all reparse points + decoded targets"),
         ("reparse --index -v", "dump the reparse index with raw keys"),
         ("reparse --tag 0xa000000c --json", "only IO_REPARSE_TAG_SYMLINK, as JSON")],
 },
 "deleted": {
  "tag": "Deleted-file VIEW + recoverability verdict (writing = `export deleted`)",
  "desc": ["Read-only view of deleted entries. BY DEFAULT it runs the Trash table (0xD) + checkpoint diff +",
           "the B+-tree node-slack scan (deleted rows still in tree free space), bounded by --max-scan.",
           "--no-slack skips the slack scan for a fast metadata-only pass; --trash returns after the Trash",
           "table. Each entry carries a RECOVERABLE verdict: 'FULL FILE recoverable' (RESIDENT — content is",
           "inline in the record) / 'extent_backed' (NON-RESIDENT — data is in on-disk extents; the extent MAP",
           "survives, so `export deleted --carve` can reconstruct it best-effort) / 'metadata only' (only",
           "name/size/timestamps survive). Slack rows also show the directory they were deleted FROM. To WRITE",
           "files out, use `export deleted DIR`. 'recoverable' means present & decodable, NOT un-overwritten."],
  "opts": [("--no-slack", "skip the slack scan (fast: Trash table + checkpoint diff only)"),
           ("--trash", "only the Trash table, then return (fastest)"),
           ("--scan-pages", "ALSO scan orphaned metadata pages (slower)"),
           ("--slack", "run the slack scan (already the default; kept for symmetry)"),
           ("--carve", "with `export deleted`: also reconstruct NON-RESIDENT files best-effort — the resulting "
                       ".carved bytes are the MOST likely to be stale (clusters may be reused); .recovered "
                       "(resident, in-metadata) is more reliable"),
           ("--search SUB", "filter recovered entries by name substring"),
           ("--max-scan N", "max clusters to scan (default 50000)"),
           ("--extract DIR", "DEPRECATED — use `export deleted DIR` (same result: .row + .recovered [+ .carved])")],
  "ex": [("deleted", "Trash + checkpoint + slack scan (default) with recoverability verdicts"),
         ("deleted --no-slack", "fast: Trash table + checkpoint diff only"),
         ("deleted --trash", "fastest: Trash-only check"),
         ("deleted --search report", "only deleted entries named like 'report'")],
 },
 "recyclebin": {
  "tag": "Decode $RECYCLE.BIN $I metadata (original path, deletion time)",
  "desc": ["Walks $RECYCLE.BIN/<SID>/ and decodes each $I metadata file — the original full path, deletion",
           "time, and logical size of a recycled item — and reports whether its $R payload still survives.",
           "Filesystem-agnostic Windows format ($I header 1=Vista-8.1, 2=Win10/11)."],
  "opts": [("--json", "machine-readable output")],
  "ex": [("recyclebin", "list every recycled item with its original path + deletion time"),
         ("recyclebin --json", "same, as JSON")],
 },
 "specials": {
  "tag": "Special-attribute files — one discoverable home for every special type",
  "desc": ["Lists files carrying a special attribute. No argument prints a COUNT SUMMARY of every type;",
           "`specials <type>` prints that type's list with type-specific columns; `specials all` prints every",
           "section. Types: ads, reparse, wsl, hardlink, sparse, encrypted, compressed, integrity, ea, snapshot.",
           "This is the discovery/list layer — for deep ops use reparse --index / snapshots --extract /",
           "dataruns / export ads. (Equivalent to `files --filter <type>`, which also still works.)"],
  "opts": [("<type>", "one of: ads reparse wsl hardlink sparse encrypted compressed integrity ea snapshot"),
           ("all", "print every type's list, sectioned"),
           ("--json", "machine-readable output (counts, or per-type file lists)")],
  "ex": [("specials", "count summary of every special type"),
         ("specials ads", "every named data stream + its host file"),
         ("specials hardlink", "hard-link groups (all names of each multi-linked file)"),
         ("specials sparse", "sparse files with logical vs allocated size")],
 },
 "export": {
  "tag": "Get data out — one home for every extraction path",
  "desc": ["Exports content or artifacts. SINGLE-value subverbs print to the screen (add `-o FILE` to save):",
           "`file <path>` (one file, = extract) · `ads <path:stream>` (one inline ADS) · `reparse` (the reparse",
           "inventory as text, or --json). BULK subverbs write to a directory — and if you omit it they auto-create a",
           "timestamped `forefst_export_<what>_<stamp>/`: `resident-all` (every resident file's inline $DATA) ·",
           "`snapshots` (all stream-snapshot versions; alias `prior-versions`) · `deleted` (.row + .recovered",
           "[+ --carve .carved]) · `recyclebin` ($R payloads) · `metadata` (the VBR/CHKP/SUPB/MLog/USN/B+-tree",
           "bundle). Bare `export -o DIR` = metadata."],
  "opts": [("file <path> [-o FILE] | --oid O", "carve ONE file's bytes (stdout, or -o FILE to save)"),
           ("ads <path:stream> [-o FILE]", "carve ONE inline alternate data stream (stdout, or -o FILE)"),
           ("reparse [--json] [-o FILE]", "the reparse-point inventory (targets/tags/kind) — text, or --json (stdout, or -o FILE)"),
           ("resident-all [dir]", "every resident file's inline content, tree preserved (auto-dir if omitted)"),
           ("snapshots [dir]", "each stream-snapshot version (alias: snapshot / prior-versions; auto-dir if omitted)"),
           ("deleted [dir] [--carve] [--rows-only|--content-only]",
            "deleted remnants: raw .row + .recovered (resident) [+ .carved non-resident with --carve] + manifest"),
           ("recyclebin [dir]", "surviving $R payloads, named by their decoded original filename (auto-dir if omitted)"),
           ("metadata -o <dir>", "the hash-verified metadata bundle (--what vbr,chkp,supb,mlog,usn,btree · --btree-mode packed|per-object)")],
  "ex": [("export file /dir/report.docx -o out.docx", "one file, saved"),
         ("export ads \"notes.txt:hidden\"", "one ADS to the screen (add -o to save)"),
         ("export snapshots", "every snapshot version -> an auto-created timestamped folder"),
         ("export deleted ./rec/ --carve", "recover deleted rows + reconstruct non-resident files"),
         ("export recyclebin ./recovered/", "recover the recycle-bin payloads"),
         ("export metadata -o ./bundle/", "the metadata bundle (= the old `export`)")],
 },
 "snapshots": {
  "tag": "Volume snapshots / block-clone (CoW) streams",
  "desc": ["Inventories files carrying stream snapshots (CoW prior versions) and can recover/preview or",
           "extract each prior version's content via its extent chain."],
  "opts": [("-v, --verbose", "per-snapshot allocation/id/value details"),
           ("--show", "recover & preview each snapshot's prior CoW content"),
           ("--file SUB", "only files whose path contains SUB (a fuller path disambiguates same-named files)"),
           ("--snapshot SEL", "only ONE version: a 1-based [N] index, or part of a version name"),
           ("--depth N", "max recursion depth (default 10)"),
           ("--extract DIR", "write each recovered version into DIR"),
           ("--json", "machine-readable inventory")],
  "ex": [("snapshots", "list files with snapshots"),
         ("snapshots --file lasttest.txt --show -v", "preview one file's prior versions"),
         ("snapshots --file lasttest.txt --snapshot first --show", "preview just the version named 'first'"),
         ("export snapshots ./v --file report.txt --snapshot 2", "extract only version [2] of report.txt"),
         ("snapshots --extract ./recovered --depth 12", "carve all recoverable versions")],
 },
 "integrity": {
  "tag": "Verify metadata-page checksums",
  "desc": ["Structural audit of metadata pages. By default a fast verdict; --checksums verifies the",
           "system root tables, --fullchecksums extends to every object B-tree (CRC64 or SHA-256)."],
  "opts": [("-v, --verbose", "per-page details (capped 200)"),
           ("--checksums", "verify the system root tables' checksums"),
           ("--fullchecksums", "verify every object B-tree (implies --checksums)"),
           ("--scan-range A-B", "raw mode: inspect each LCN in the range standalone"),
           ("--max-pages N", "cap the checksum crawl (default 300000)")],
  "ex": [("integrity", "fast structural verdict"),
         ("integrity --checksums", "verify system-root checksums"),
         ("integrity --fullchecksums -v", "full sweep + page details")],
 },
 "dataruns": {
  "tag": "File data extents / data-runs per object",
  "desc": ["Maps non-resident files to their on-disk extents (data-runs). Default lists extent-backed",
           "files; -v adds resident/no-extent files and every decoded run (fvcn/lcn/length)."],
  "opts": [("-v, --verbose", "include resident/no-extent files and every decoded run"),
           ("--oid O", "start at object O (0x hex or decimal; default 0x600)"),
           ("--depth N", "max recursion depth (default 3)")],
  "ex": [("dataruns", "map extent-backed files under the root"),
         ("dataruns -v --depth 5", "full per-file run dump, deeper"),
         ("dataruns --oid 0x705 -v", "scope to one directory subtree")],
 },
}

def _render_cmd_help(cmd):
    h = CMD_HELP.get(cmd)
    if not h:
        print(f"{PROG}: no help for {cmd!r}. Run `{PROG} --help`.", file=sys.stderr); return
    forensic = cmd in FORENSIC_SUBCOMMANDS
    print(f"{PROG} <image> {cmd} — {h['tag']}\n")
    print(f"  usage: {PROG} <image> {cmd} [options]" + ("" if forensic else "") + "\n")
    for line in h["desc"]:
        print(f"  {line}")
    print("\n  Options:")
    for flag, desc in h["opts"]:
        print(f"    {flag:26} {desc}" if flag else f"    {'':26} {desc}")
    print("\n  Examples:")
    for ex, note in h["ex"]:
        print(f"    {PROG} disk.raw {ex}")
        print(f"        {note}")
    print()

def _print_overview():
    print(f"{PROG} v{VERSION} — ReFS forensic analysis (MFTECmd-equivalent file lister + forensic suite)\n")
    print(f"usage: {PROG} <image> [subcommand] [options]")
    print(f"       {PROG} <image>                 # defaults to `files`")
    print(f"       {PROG} <image> <cmd> --help    # detailed help for one subcommand")
    print(f"       {PROG} --list                  # one-line index of all subcommands\n")
    print("Native subcommands:")
    for k, v in SUBCOMMANDS.items():
        print(f"  {k:12} {v}")
    print("\nForensic subcommands:")
    for k in FORENSIC_SUBCOMMANDS:
        print(f"  {k:12} {CMD_HELP[k]['tag']}")
    print(f"\n{GLOBAL_HELP}\n")
    print("Examples (grouped by what you want to do):")
    _EXAMPLE_GROUPS = (
        ("List / inventory", (
            ("files -o listing.csv",        "full 38-column inventory -> CSV (the bodyfile)"),
            ("find report --regex",         "find files by name (alias of `search`)"),
            ("details /dir/file.txt",       "everything about ONE file (or 0xOID)"),
        )),
        ("Special files", (
            ("specials",                    "count table of every special type"),
            ("specials ads",                "list all files with alternate data streams"),
            ("specials hardlink",           "list hard-linked files, grouped"),
        )),
        ("Get data out", (
            ("export ads \"file:stream\"",    "extract one alternate data stream"),
            ("export resident-all out/",    "dump every resident file's inline data"),
            ("export snapshots out/",       "extract all stream-snapshot versions"),
        )),
        ("Deleted / recovery", (
            ("deleted",                     "list deleted files + a recoverability verdict (slack by default)"),
            ("export deleted out/ --carve", "recover them: .row + .recovered + carved non-resident"),
            ("recyclebin",                  "report the Windows $RECYCLE.BIN"),
        )),
        ("Timeline / anomalies", (
            ("timeline --fast --limit 50",  "USN+MLog+$SI merged super-timeline"),
            ("timestomp",                   "flag backdated / anomalous timestamps"),
            ("summary",                     "volume summary (version, checkpoint, flags)"),
        )),
    )
    for title, rows in _EXAMPLE_GROUPS:
        print(f"  {title}:")
        for ex, note in rows:
            print(f"    {PROG} disk.raw {ex:30}  # {note}")
    print(f"\n{VERSION_NOTE}")

# Every option that consumes the FOLLOWING token as its value (across argparse + the forensic commands).
# Used so a help token that is actually a value (e.g. `extract --path --help`) is NOT mistaken for a
# help request.
_VALUED_OPTS = {"-o", "--output", "--oid", "--path", "--filter", "--depth", "--partition-start",
                "--cow-before", "--btree-mode", "--csv", "--extract", "--file", "--limit",
                "--margin-days", "--max-pages", "--max-scan", "--min", "--out", "--scan-range",
                "--search", "--sid", "--source", "--tag", "--what"}

def _help_requested(toks):
    """True if -h/--help appears as a real help request — i.e. NOT as the value of a valued option."""
    for i, t in enumerate(toks):
        if t in ("-h", "--help") and not (i > 0 and toks[i - 1] in _VALUED_OPTS):
            return True
    return False

def main():
    _ALL_CMDS = set(SUBCOMMANDS) | set(HIDDEN_SUBCOMMANDS) | set(FORENSIC_SUBCOMMANDS)
    # Resolve a command-token alias (e.g. `find` -> `search`) to canonical BEFORE any dispatch/help, so all
    # downstream (help, argparse, forensic routing) sees the real name. The alias applies to the subcommand
    # token, which is sys.argv[2] (sys.argv[1] is the image).
    if len(sys.argv) >= 3 and sys.argv[2] in SUBCOMMAND_ALIASES:
        sys.argv[2] = SUBCOMMAND_ALIASES[sys.argv[2]]
    _argv = sys.argv
    # ── help handling (before any dispatch / argparse) ──
    if len(_argv) == 1 or (len(_argv) >= 2 and _argv[1] in ("-h", "--help", "help")):
        if len(_argv) >= 3 and _argv[2] in _ALL_CMDS:
            _render_cmd_help(_argv[2])
        else:
            _print_overview()
        return
    # `forefst <image> help [<cmd>]` → general overview, or targeted per-command help when a command
    # follows (`forefst disk.raw help mlog`, `… help details`). `help` here is the subcommand token
    # (sys.argv[2]); sys.argv[1] is the image. Mirrors the `forefst help <cmd>` (no-image) form above.
    if len(_argv) >= 3 and _argv[2] == "help":
        _hcmd = _argv[3] if len(_argv) >= 4 else None
        if _hcmd in SUBCOMMAND_ALIASES:
            _hcmd = SUBCOMMAND_ALIASES[_hcmd]
        if _hcmd and _hcmd in _ALL_CMDS:
            _render_cmd_help(_hcmd)
        elif _hcmd:
            print(f"[{PROG}] no such subcommand: '{_hcmd}' — showing the overview.\n")
            _print_overview()
        else:
            _print_overview()
        return
    # `forefst <image> [<cmd>] --help/-h` → per-command or overview help (but not when -h/--help is the
    # value of a valued option, e.g. `extract --path --help`)
    if len(_argv) >= 3 and _help_requested(_argv[2:]):
        _cmd = next((a for a in _argv[2:] if a in _ALL_CMDS), None)
        if _cmd:
            _render_cmd_help(_cmd)
        else:
            _print_overview()
        return

    # `forefst --list` / `-l`: list subcommands (no image needed)
    if len(sys.argv) >= 2 and sys.argv[1] in ("--list", "-l"):
        print("forefst subcommands (usage: forefst <image> <subcommand> [options]):")
        for _k, _v in SUBCOMMANDS.items():
            print(f"  {_k:13} {_v}")
        print("forensic subcommands:")
        for _k, _v in FORENSIC_SUBCOMMANDS.items():
            print(f"  {_k:13} {_v}")
        print("\n  --provenance   list which emitted fields are NOT 100% certain (with citations)")
        print(f"\n{VERSION_NOTE}")
        return

    # `forefst --provenance`: list which emitted fields are NOT 100% certain (needs no image;
    # changes no other output). The honesty layer for uncertain output values.
    if len(sys.argv) >= 2 and sys.argv[1] in ("--provenance", "--provenance-notes"):
        _print_field_provenance()
        return

    # Delegated forensic subcommands: parse like refsanalysis (raw remaining args + own flags),
    # since they use options argparse doesn't model (--parse/--raw-scan/--no-si/--source/...).
    if len(sys.argv) >= 3 and sys.argv[2] in FORENSIC_HANDLERS:
        image = sys.argv[1]
        remaining = sys.argv[3:]
        part_start = None
        filtered = []
        i = 0
        while i < len(remaining):
            if remaining[i] == "--partition-start" and i + 1 < len(remaining):
                try:
                    part_start = int(remaining[i + 1], 0)
                except ValueError:
                    print(f"{PROG}: error: invalid --partition-start value: {remaining[i + 1]}", file=sys.stderr)
                    sys.exit(1)
                i += 2
            else:
                filtered.append(remaining[i]); i += 1
        if not os.path.exists(image):
            print(f"{PROG}: error: file not found: {image}", file=sys.stderr); sys.exit(1)
        if not os.path.isfile(image):
            print(f"{PROG}: error: not a regular file: {image}", file=sys.stderr); sys.exit(1)
        try:
            validate_image(image)
        except (ValueError, OSError) as e:
            print(f"{PROG}: error: {e}", file=sys.stderr); sys.exit(1)
        sys.exit(FORENSIC_HANDLERS[sys.argv[2]](image, filtered, part_start))

    ap = argparse.ArgumentParser(prog=PROG,
                                 description="ReFS forensic file lister (MFTECmd equivalent)",
                                 epilog=VERSION_NOTE)
    ap.add_argument("--version", action="version", version=f"forefst.py v{VERSION} — ReFS forensic file lister")
    ap.add_argument("image", help="Path to disk image")
    ap.add_argument("command", nargs="?", choices=list(SUBCOMMANDS) + list(HIDDEN_SUBCOMMANDS), default=None,
                    help="subcommand (default: files); run `forefst --list` to see all")
    ap.add_argument("target", nargs="?", default=None,
                    help="search PATTERN, or details /path | 0xOID")
    ap.add_argument("-o", "--output", help="Output file (default: stdout)")
    ap.add_argument("--body", action="store_true", help="files: body-file output (default CSV)")
    ap.add_argument("--full-path-column", action="store_true",
                    help="files CSV: append a FullPath column (ParentPath/FileName)")
    ap.add_argument("--json", action="store_true", help="JSON output (pretty-printed array)")
    ap.add_argument("--jsonl", action="store_true", help="JSON Lines output (one object per line)")
    ap.add_argument("--hash-image", action="store_true",
                    help="summary: include SHA-256 hash of the full disk image")
    ap.add_argument("--oid", type=lambda x: int(x, 0), default=None,
                    help="details: address the object by OID (e.g. 0x705)")
    ap.add_argument("--path", default=None,
                    help="details: address the object by path (e.g. /dir/file.txt)")
    ap.add_argument("--regex", action="store_true",
                    help="search: treat PATTERN as a regular expression")
    ap.add_argument("--filter", default=None, metavar="CATEGORY",
                    help="files: subset by attribute category — " + "/".join(FILE_FILTERS))
    ap.add_argument("--deleted", action="store_true",
                    help="files/search: include deleted files (Trash + orphans + checkpoint diff + B+-tree slack)")
    ap.add_argument("--max-scan", type=int, default=50000,
                    help="files --deleted: max clusters for the B+-tree slack scan (default 50000)")
    ap.add_argument("--timestomp", action="store_true",
                    help="files: add the TimestompFlags column — a $SI-only HEURISTIC (investigative "
                         "information, NOT proof); the `timestomp` subcommand adds the authoritative USN + "
                         "hard-link cross-checks and a per-row basis.")
    ap.add_argument("--depth", type=int, default=100, help="Max directory recursion depth")
    ap.add_argument("--partition-start", type=lambda x: int(x, 0), default=None,
                    help="Override partition start offset in bytes")
    ap.add_argument("--cow-before", metavar="IMAGE",
                    help="files: earlier disk image for forward CoW version recovery")
    ap.add_argument("--cow-partition-start", type=lambda x: int(x, 0), default=None,
                    help="files: partition offset for the --cow-before image (default: auto-detect its own "
                         "GPT). C16: use when the before-image has a DIFFERENT layout than the main image "
                         "(otherwise both auto-detect). NOTE: the CoW-recovery path is lightly tested.")
    ap.add_argument("-q", "--quiet", action="store_true", help="Suppress progress to stderr")
    args = ap.parse_args()
    if args.command is None:
        args.command = "files"

    def log(msg):
        if not args.quiet:
            print(msg, file=sys.stderr)

    def die(msg):
        print(f"{PROG}: error: {msg}", file=sys.stderr)
        sys.exit(1)

    # Output format mutual exclusion
    fmt_count = sum([args.body, args.json, args.jsonl])
    if fmt_count > 1:
        die("--body, --json, and --jsonl are mutually exclusive")

    # Input validation
    if not os.path.exists(args.image):
        die(f"file not found: {args.image}")
    if not os.path.isfile(args.image):
        die(f"not a regular file: {args.image}")
    if args.depth < 1:
        die(f"--depth must be >= 1 (got {args.depth})")
    if args.partition_start is not None and args.partition_start < 0:
        die(f"--partition-start must be >= 0 (got {args.partition_start})")
    if args.cow_before:
        if not os.path.isfile(args.cow_before):
            die(f"--cow-before: file not found: {args.cow_before}")
        if os.path.abspath(args.cow_before) == os.path.abspath(args.image):
            die("--cow-before image must be different from the main image")
        if args.command != "files":
            die("--cow-before is only valid with the 'files' subcommand")
    # Subcommand flag scoping (clean break: these belong to specific subcommands)
    if (args.oid is not None or args.path) and args.command != "details":
        die("--oid/--path are only valid with the 'details' subcommand")
    if args.filter is not None:
        if args.command != "files":
            die("--filter is only valid with the 'files' subcommand")
        if args.filter not in FILE_FILTERS:
            die(f"--filter: unknown category {args.filter!r}. Choices: {', '.join(sorted(FILE_FILTERS))}")

    # Bootstrap
    log(f"[{PROG}] Opening {os.path.basename(args.image)}...")
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(args.image, args.partition_start)
    except ValueError as e:
        die(str(e))
    except OSError as e:
        die(f"cannot read image: {e}")
    version_str = f"{vmaj}.{vmin}"
    usn_active = False
    if 0x520 in obj_map:
        try:
            for kd, _vd in walk_bplus(f, ps, cs, tr, obj_map[0x520]):
                if len(kd) >= 4 and le16(kd, 0) == 0x30:
                    try:
                        nm = kd[4:].decode("utf-16-le").rstrip("\x00")
                        if nm == "Change Journal": usn_active = True; break
                    except Exception: pass
        except Exception: pass
    usn_tag = " | USN: active" if usn_active else ""
    log(f"[{PROG}] ReFS {version_str} | {len(obj_map)} objects | cluster_size={cs}{usn_tag}")
    if (vmaj, vmin) < (3, 14):
        log(f"[{PROG}] note: ReFS {version_str} (<3.14) — some enriched fields may be incomplete (see --list)")

    # summary / fastsummary subcommands (both extended-by-default)
    if args.command in ("summary", "fastsummary"):
        is_fast = (args.command == "fastsummary")
        is_plus = True
        log(f"[{PROG}] Running {'fast ' if is_fast else ''}summary++...")
        fast_data = cmd_fastsummary(f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns,
                                     args.image, plus_mode=is_plus, hash_image=args.hash_image, log_fn=log)
        if is_fast:
            if args.json:
                print(json.dumps(fast_data, indent=2, ensure_ascii=False))
            else:
                _print_fastsummary(fast_data, plus_mode=is_plus)
            f.close()
            return

        # Full summary: needs directory walk (enriched, so ADS/SecurityId/reparse counts are correct)
        log(f"[{PROG}] Walking directory tree for full summary...")
        results = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, args.depth, True, set())
        ndirs = sum(1 for r in results if r["is_dir"])
        nfiles = sum(1 for r in results if not r["is_dir"])
        nresident = sum(1 for r in results if r.get("is_resident"))
        total_size = sum(r.get("file_size", 0) for r in results)
        times = [r.get("create_time", 0) for r in results] + [r.get("modify_time", 0) for r in results]
        times = [t for t in times if t and t > 0]
        oldest = filetime_to_iso(min(times)) if times else "(none)"
        newest = filetime_to_iso(max(times)) if times else "(none)"
        walk_summary = {
            "directories": ndirs, "files": nfiles, "resident_files": nresident,
            "total_file_size": _human_size(total_size), "total_file_size_bytes": total_size,
            "oldest_timestamp": oldest, "newest_timestamp": newest,
        }
        if is_plus:
            walk_summary["encrypted_files"] = sum(1 for r in results if r.get("is_encrypted"))
            walk_summary["integrity_files"] = sum(1 for r in results if r.get("has_integrity"))
            walk_summary["compressed_files"] = sum(1 for r in results if r.get("is_compressed"))
            # C9: "extra" = names beyond the first = N-1 per physical object. The old sum counted every
            # NAME of multi-name files (N, not N-1). Group rows by their shared hard_link_names set, subtract.
            _hl = [r for r in results if r.get("hard_link_count", 1) > 1]
            _hl_groups = {tuple(sorted(r.get("hard_link_names") or [f"oid:{r.get('oid')}"])) for r in _hl}
            walk_summary["hardlink_extra"] = len(_hl) - len(_hl_groups)
            walk_summary["snapshots"] = sum(r.get("snapshot_count", 0) for r in results)
            walk_summary["ads_entries"] = sum(1 for r in results if r.get("has_ads"))
        # UsnJournalId: the volume-constant journal epoch carried by every file's $SI val+0x70
        # (reliable, unlike the $Max stream). Take the most common non-zero value.
        _jids = {}
        for r in results:
            _j = r.get("usn_journal_id", 0)
            if _j:
                _jids[_j] = _jids.get(_j, 0) + 1
        if _jids:
            fast_data["usn_journal_id"] = max(_jids, key=_jids.get)
        combined = {**fast_data, **walk_summary}
        combined["summary_mode"] = "summary-plus" if is_plus else "summary"
        if args.json:
            print(json.dumps(combined, indent=2, ensure_ascii=False))
        else:
            _print_summary(walk_summary, fast_data, plus_mode=is_plus)
        f.close()
        return

    # details subcommand — inspect ONE object by OID or path
    if args.command == "details":
        det_oid, det_path = None, None
        if args.oid is not None and args.path:
            die("details: use --oid OR --path, not both")
        if args.target is not None and (args.oid is not None or args.path):
            die("details: give a target OR --oid/--path, not both")
        if args.oid is not None:
            det_oid = args.oid
        elif args.path:
            det_path = args.path
        elif args.target is not None:
            t = args.target
            if t.startswith("/"):
                det_path = t
            elif t[:2].lower() == "0x":
                try:
                    det_oid = int(t, 16)
                except ValueError:
                    die(f"details: invalid OID {t!r}")
            else:
                die("details: target must start with '/' (path) or '0x' (OID), or use --path/--oid")
        else:
            die("details: provide a /path, a 0xOID, or --path/--oid")
        if det_oid is None:
            # path mode: a directory has its own OID (-> OID detail below); a FILE has none, so we
            # show its full record (F6) by walking to the matching entry (full enrichment, consistent
            # with `files`). Sub-directories keep the richer OID/$SI view.
            _poid, _pkd, _pvd = resolve_path(f, ps, cs, tr, obj_map, det_path)
            if _pkd is None:
                print(f"path not found: {det_path}", file=sys.stderr); f.close(); sys.exit(1)
            # A directory is ALWAYS non-resident (value <= 84 B) with the dir-bit at value+0x40.
            # A resident entry (>84 B) is always a FILE — its +0x40 is access_time, not file_attrs,
            # so the dir-bit must NOT be tested there (that mis-routed resident files as dirs).
            if (len(_pvd) <= NON_RESIDENT_MAX_VALUE and len(_pvd) >= 0x44
                    and (le32(_pvd, 0x40) & 0x10000000)):
                det_oid = le64(_pvd, 0x08)
            else:
                # FILE by path (F6): find the enriched entry in the walk, print/JSON its detail.
                norm = det_path.lstrip("/")
                log(f"[{PROG}] Resolving file {det_path}...")
                results = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, args.depth, True, set())
                match = next((r for r in results if r.get("path") == norm), None)
                if match is None:
                    print(f"path not found: {det_path}", file=sys.stderr); f.close(); sys.exit(1)
                sd_map = build_security_map(f, ps, cs, tr, obj_map)
                # EA source: the resident value carries the embedded $EA sub-records directly; a
                # non-resident file's EAs are in its type-0x40 backing (fetched by home/parent + file_id).
                if match.get("is_resident"):
                    ea_src = _pvd
                else:
                    _fsz = match.get("file_size")
                    ea_src = (fetch_t40_backing(f, ps, cs, tr, obj_map, match.get("home_oid") or 0, match.get("file_id") or 0, _fsz)
                              or fetch_t40_backing(f, ps, cs, tr, obj_map, match.get("parent_oid") or 0, match.get("file_id") or 0, _fsz))
                if args.json:
                    rec = _build_record(match, sd_map, version_str)
                    eas, packed = extract_eas_from_value(ea_src) if ea_src is not None else (None, None)
                    if eas is not None:
                        rec["packed_ea_size"] = packed
                        # oracle gate (see _print_file_detail): only emit the list/WSL when it reconciles.
                        if sum(5 + len(e["name"]) + len(e["value"]) for e in eas) == packed:
                            rec["extended_attributes"] = [{"name": e["name"], "length": len(e["value"]),
                                                           "value_hex": e["value"].hex()} for e in eas]
                            wsl = decode_wsl_eas(eas)
                            if wsl:
                                wj = dict(wsl)
                                if "mode" in wsl: wj["mode_decoded"] = decode_lx_mode(wsl["mode"])
                                rec["wsl"] = wj
                        else:
                            rec["extended_attributes"] = None
                    _ifl = internal_flags_str(match.get("internal_flags", 0))
                    if _ifl:
                        rec["internal_flags"] = _ifl
                    print(json.dumps(rec, indent=2, ensure_ascii=False))
                else:
                    _print_file_detail(match, sd_map, version_str, raw_value=ea_src)
                f.close()
                return
        log(f"[{PROG}] Looking up OID 0x{det_oid:x}...")
        detail = cmd_oid_detail(f, ps, cs, tr, obj_map, vmaj, vmin, det_oid, log_fn=log)
        if detail is None:
            print(f"OID 0x{det_oid:x} not found in object table ({len(obj_map)} objects).", file=sys.stderr)
            print(f"Use `forefst <image> search <name>` to find files by name.", file=sys.stderr)
            f.close()
            sys.exit(1)
        if "error" in detail:
            print(f"Error reading OID 0x{det_oid:x}: {detail['error']}", file=sys.stderr)
            f.close()
            sys.exit(1)
        if args.json:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
        else:
            _print_oid_detail(detail)
        f.close()
        return

    # search subcommand
    if args.command == "search":
        pattern = args.target
        if not pattern:
            die("search: provide a PATTERN (forefst <image> search PATTERN)")
        log(f"[{PROG}] Searching for \"{pattern}\"...")
        trash_set = set()
        if args.deleted:
            trash_set = build_trash_set(f, ps, cs, tr, obj_map)
        matches = cmd_search(f, ps, cs, tr, obj_map, vmaj, vmin, pattern,
                             regex_mode=args.regex, include_deleted=args.deleted, trash_set=trash_set)
        if isinstance(matches, dict) and "error" in matches:
            print(matches["error"], file=sys.stderr)
            f.close()
            sys.exit(1)
        if args.json:
            print(json.dumps(matches, indent=2, ensure_ascii=False))
        elif args.jsonl:
            for m in matches:
                print(json.dumps(m, ensure_ascii=False))
        else:
            _print_search(matches, pattern)
        f.close()
        return

    # Build security descriptor map — always: SecurityId->Owner SID is part of the standard listing now
    # (the former --enrich-only resolution is unconditional; see walk_directory_tree enrichment).
    log(f"[{PROG}] Building security descriptor map...")
    sd_map = build_security_map(f, ps, cs, tr, obj_map)
    log(f"[{PROG}] {len(sd_map)} security descriptors loaded")

    # Build trash set
    trash_set = set()
    if args.deleted:
        log(f"[{PROG}] Scanning Trash Table...")
        trash_set = build_trash_set(f, ps, cs, tr, obj_map)
        log(f"[{PROG}] {len(trash_set)} trashed entries found")

    # Walk directory tree
    log(f"[{PROG}] Walking directory tree...")
    results = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, args.depth,
                                  True, trash_set)
    if args.timestomp:
        annotate_timestomp(results, f, ps, cs, tr, obj_map)
    ndirs = sum(1 for r in results if r["is_dir"])
    nfiles = sum(1 for r in results if not r["is_dir"])
    nresident = sum(1 for r in results if r.get("is_resident"))
    nsnapshots = sum(r.get("snapshot_count", 0) for r in results)
    nhard = sum(1 for r in results if r.get("hard_link_count", 1) > 1)
    log(f"[{PROG}] {ndirs} dirs, {nfiles} files ({nresident} resident, {nhard} hard-linked, {nsnapshots} snapshots)")

    # Deleted file detection: orphans + checkpoint diff
    if args.deleted:
        referenced_oids = {r["oid"] for r in results if r["oid"]}
        referenced_oids.add(0x600)  # Root dir

        # Orphan detection
        log(f"[{PROG}] Scanning for orphan objects...")
        orphans = find_orphan_objects(f, ps, cs, tr, obj_map, referenced_oids, log)
        if orphans:
            log(f"[{PROG}] {len(orphans)} deleted files recovered from orphan objects")
            results.extend(orphans)

        # Checkpoint comparison
        log(f"[{PROG}] Comparing checkpoint copies...")
        try:
            chkp_deleted = find_chkp_diff_deleted(f, ps, cs, chkp_lcns, obj_map, log)
            if chkp_deleted:
                log(f"[{PROG}] {len(chkp_deleted)} deleted files found via checkpoint diff")
                results.extend(chkp_deleted)
        except Exception as e:
            log(f"[{PROG}] Checkpoint comparison failed: {e}")

        # Q5 defect 2 fix: also run the B+-tree node-slack scan (the same engine `deleted` runs by default),
        # so the files view's IsDeleted/DeletionSource are consistent with the `deleted` command instead of
        # blind to slack-recovered deletions. Only DELETED rows (name not in the live tree) are added, as
        # deletion_source="slack"; prior-version remnants of still-present files are excluded. Bounded by
        # --max-scan. Rows carry the same schema as orphan/chkp rows so CSV/JSON output is unchanged.
        log(f"[{PROG}] Scanning B+-tree node slack for deleted rows...")
        try:
            # Use the SAME live-name basis the `deleted` command uses (_get_current_files) so the two
            # reconcile exactly — walk_directory_tree's deeper set would exclude a few more prior-versions
            # and diverge from `deleted` on deep images.
            live_names = _get_current_files(f, ps, cs, tr, obj_map)
            _raw_slack = _slack_recover(f, ps, cs, tr, roots, obj_map, args.max_scan, log)
            _dedup = {}
            for e in _raw_slack:
                k = (e["name"], e.get("create_time", 0), e.get("is_dir", False))
                if k not in _dedup or len(e.get("vd", b"")) > len(_dedup[k].get("vd", b"")):
                    _dedup[k] = e
            slack_rows = []
            for e in _dedup.values():
                if e["name"] in live_names:
                    continue
                fa = e.get("file_attrs", 0)
                op = e.get("owning_path", "") or ""
                _, vlabel, _ = _deleted_recoverability(e)
                slack_rows.append({
                    "path": (op + "/" + e["name"]).lstrip("/") if op else e["name"],
                    "parent_path": op, "parent_oid": e.get("owning_table_oid", 0), "name": e["name"],
                    "recovered_child": "", "oid": 0,
                    "is_resident": bool(e.get("resident")), "is_dir": bool(e.get("is_dir")),
                    "is_deleted": True, "deletion_source": "slack",
                    "create_time": e.get("create_time", 0), "modify_time": e.get("modify_time", 0),
                    "change_time": e.get("change_time", 0), "access_time": e.get("access_time", 0),
                    "file_attrs": fa, "internal_flags": 0, "security_id": 0, "usn": 0, "file_size": 0,
                    "is_encrypted": bool(fa & 0x4000), "is_compressed": bool(fa & 0x0800),
                    "has_integrity": bool(fa & 0x8000), "has_ea": bool(fa & 0x00040000),
                    "has_reparse": bool(fa & 0x0400), "has_ads": False, "ads_names": "",
                    "reparse_target": "", "snapshot_count": 0, "recovery_verdict": vlabel,
                })
            if slack_rows:
                log(f"[{PROG}] {len(slack_rows)} deleted files recovered from B+-tree slack")
                results.extend(slack_rows)
        except Exception as e:
            log(f"[{PROG}] Slack scan failed: {e}")

    # Forward CoW version recovery (cross-image comparison)
    if args.cow_before:
        log(f"[{PROG}] Performing forward CoW version recovery...")
        # C16: the before-image's partition offset is its OWN (--cow-partition-start), not the main
        # image's args.partition_start (which was wrongly forced onto the before-image). Default None =>
        # auto-detect the before-image's GPT. NOTE: the CoW-recovery path is lightly tested.
        cow_entries = cow_recovery(f, ps, cs, tr, obj_map,
                                    args.cow_before, args.cow_partition_start, log)
        if cow_entries:
            # For modified files, use the current path from the main walk
            oid_to_path = {r["oid"]: r["path"] for r in results if r.get("oid")}
            oid_to_name = {r["oid"]: r["name"] for r in results if r.get("oid")}
            for ce in cow_entries:
                if ce["deletion_source"] == "cow_modified" and ce["oid"] in oid_to_path:
                    current_path = oid_to_path[ce["oid"]]
                    ce["path"] = f"$COW_PREVIOUS/{current_path}"
                    parent = os.path.dirname(current_path)
                    ce["parent_path"] = f"$COW_PREVIOUS/{parent}" if parent else "$COW_PREVIOUS"
                    # Recover name from current tree if B+ tree had no 0x30 entry
                    if ce["name"].startswith("OID_0x") and ce["oid"] in oid_to_name:
                        ce["name"] = oid_to_name[ce["oid"]]
            log(f"[{PROG}] {len(cow_entries)} previous-version entries recovered via CoW")
            results.extend(cow_entries)

    # F13: --filter — subset the listing by attribute category (after deleted/CoW so the filter
    # applies to the full set). Output stays the normal files format, just the matching rows.
    if args.filter:
        _pred = FILE_FILTERS[args.filter]
        results = [r for r in results if _pred(r)]
        log(f"[{PROG}] --filter {args.filter}: {len(results)} matching entries")

    # Output
    if args.output:
        out = open(args.output, "w", newline="", encoding="utf-8")
    else:
        out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="")

    try:
        if args.body:
            emit_body(results, out)
            fmt = "body"
        elif args.json:
            emit_json(results, sd_map, version_str, out)
            fmt = "JSON"
        elif args.jsonl:
            emit_jsonl(results, sd_map, version_str, out)
            fmt = "JSONL"
        else:
            emit_csv(results, sd_map, version_str, out, full_path=args.full_path_column)
            fmt = "CSV"
    finally:
        if args.output:
            out.close()
        f.close()

    ndeleted = sum(1 for r in results if r.get("is_deleted"))
    dest = args.output if args.output else "(stdout)"
    log(f"[{PROG}] Done. {len(results)} entries ({ndeleted} deleted) -> {fmt} {dest}")

if __name__ == "__main__":
    main()
