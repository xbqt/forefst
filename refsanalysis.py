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
refsanalysis.py — ReFS disk-image STRUCTURE / lab analysis tool.

The forensic file-level commands (usn/mlog/timeline/timestomp/extract/security/reparse/
deleted/snapshots/integrity/export/dataruns) now live in forefst — run them there
(e.g. `forefst.py <image> usn`). refsanalysis keeps the structure/lab tools and its own
lab-format file views; it imports the shared parsers from forefst.

Usage:
  python3 refsanalysis.py <image> summary              # quick volume overview
  python3 refsanalysis.py <image> summary++ --json      # extended summary, JSON output
  python3 refsanalysis.py <image> files -v              # list files with timestamps
  python3 refsanalysis.py <image> attributes --filter wsl    # find WSL files
  python3 refsanalysis.py <image> details /dir/file.txt # full per-file details by path
  python3 refsanalysis.py <image> objects               # object-ID table
  python3 refsanalysis.py <image> schema                # schema table
  python3 refsanalysis.py <image> containers            # container table / allocator
  python3 refsanalysis.py <image> bootedit repair --dry-run  # diagnose fixboot damage
  python3 refsanalysis.py <image> all                   # run all structure tools
  python3 refsanalysis.py --list                        # list all subcommands

All subcommands accept --partition-start <offset> to override GPT detection.
"""

from __future__ import annotations
import hashlib
import json
import os
import struct
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from forefst import (
    FILE_ATTR_FLAGS, SUPB_LCN, Translator, _is_snapshot_value, _parse_ads_from_value, _select_ct_root, attrs_to_str,
    bootstrap, count_snapshots_in_resident, find_refs_partition, get_object_si,
    get_resident_file_size, gpt_partition_detail, le16, le32, le64,
    parse_chkp as _forefst_parse_chkp, parse_resident_btree_rows,
    parse_supb as _forefst_parse_supb, parse_vbr as _forefst_parse_vbr, resolve_path,
    validate_image as _validate_image, walk_bplus
)

PROG = "refsanalysis"
VERSION = "1.0.0"




# ─── Subcommand definitions ──────────────────────────────────────────
# Each entry: (subcommand, description, extra_args_help)
# Dispatch is handled by HANDLERS dict below all cmd_* definitions.
SUBCOMMANDS = [
    # ── Quick analysis ──
    ("summary",     "Volume overview (version, size, files, containers)",
     ["--json: JSON output"]),
    ("summary++",   "Extended summary with OID 0x500 detail and metrics",
     ["--json: JSON output"]),
    ("all",         "Run all structure tools in sequence", []),

    # ── File system content ──
    ("files",       "List files and directories",
     ["-v: verbose (timestamps, sizes)", "--depth N: recursion depth", "--oid 0xNNN: start OID"]),
    ("attributes",  "File attribute details (EAs, timestamps, sizes)",
     ["-v: verbose", "--oid 0xNNN: start OID", "--depth N: recursion depth",
      "--filter {encrypted,wsl,reparse,snapshot}: filter by type"]),
    ("details",     "Full details for ANY file by PATH (resident files have no OID)",
     ["<path>: e.g. /dir/file.txt", "--json: JSON output",
      "(decodes inline $SI, $DATA, ADS, snapshots, $EA, reparse for resident files;",
      " own B+-tree for non-resident — addresses resident files that have no OID)"]),

    # ── Security and metadata ──

    # ── Forensic tools ──

    # ── Log analysis ──

    # ── Structure analysis ──
    ("boot",        "Boot sector (VBR) analysis",
     ["-v: verbose", "-vv: detailed", "--verify: consistency checks",
      "--raw: hex dump", "-H: header fields"]),
    ("supb",        "Superblock (SUPB) analysis",
     ["-v: verbose", "-vv: detailed", "--verify: consistency checks",
      "--raw: hex dump", "-H: header fields"]),
    ("chkp",        "Checkpoint (CHKP) with container translation",
     ["-v: verbose", "-vv: extra verbose", "--verify: consistency checks", "--raw: hex dump"]),
    ("objects",     "Object ID table (OID to LCN mapping)",
     ["-v: verbose", "-vv: detailed object entries", "--verify: consistency checks"]),
    ("schema",      "Schema table (table type definitions)",
     ["-v: verbose", "-vv: raw values", "--verify: consistency checks", "-H: header fields"]),
    ("parentchild", "Parent-child relationship table",
     ["-v: tree visualization", "-vv: raw row data", "--verify: consistency checks"]),
    ("containers",  "Container table and allocator analysis",
     ["-v: show container details"]),
    ("upcase",      "Unicode upcase table",
     ["-v: verbose", "-vv: all mappings", "--verify: consistency checks", "-H: header fields"]),
    ("oid30",       "OID 0x30 session activity analysis",
     ["-v: verbose"]),

    # ── Boot sector repair ──
    ("bootedit",    "[DANGEROUS] Boot sector editor and repair",
     ["read: display boot sector (read-only)",
      "export -o FILE: export VBR to binary file",
      "repair [--dry-run]: diagnose and repair fixboot damage",
      "set --field FIELD --value VALUE [--dry-run]: modify VBR field",
      "import -i FILE [--dry-run]: replace boot sector from a 512-byte file",
      "sparse -o FILE: create sparse image copy",
      "--inplace: modify original image",
      "-o FILE: output path for modified copy"]),
]

# ─── Shared helpers ──────────────────────────────────────────────────

def die(msg):
    print(f"{PROG}: error: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_image(path):
    _validate_image(path, die_fn=die)


def _read_at(f, offset, size):
    f.seek(offset)
    data = f.read(size)
    if len(data) != size:
        die(f"cannot read {size} bytes at 0x{offset:x} (got {len(data)})")
    return data


def _hexbytes(data, max_len=None):
    if max_len and len(data) > max_len:
        return " ".join(f"{b:02x}" for b in data[:max_len]) + " ..."
    return " ".join(f"{b:02x}" for b in data)


def _ascii_clean(d):
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in d)


def _human_size(n):
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if n < 1024 or unit == "TiB":
            return f"{int(n)} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _ok(v):
    return "OK" if v else "FAIL"


def _guid_to_text(raw16):
    return str(uuid.UUID(bytes_le=bytes(raw16)))


def _guid_str(b):
    if len(b) < 16: return b.hex()
    return f"{le32(b,0):08x}-{le16(b,4):04x}-{le16(b,6):04x}-{b[8:10].hex()}-{b[10:16].hex()}"


def _print_table(headers, rows):
    if not rows:
        print("(no rows)"); print(); return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in widths]))
    for row in rows:
        print(fmt.format(*row))
    print()


def _filetime_to_str(ft):
    if ft == 0 or ft == 0xFFFFFFFFFFFFFFFF: return "(none)"
    try:
        # integer // (not float /): float division rounds up at ~0.9999999 s (E12 fix, matches forefst).
        ts = (ft - 116444736000000000) // 10000000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, ValueError):
        return f"0x{ft:x}"


def _find_boot_offset(image, partition_start):
    if partition_start is not None:
        return int(partition_start, 0) if isinstance(partition_start, str) else partition_start
    ps, msg = find_refs_partition(image)
    if ps is not None:
        return ps
    die(msg)


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
            # reject typos / unsupported flags instead of silently dropping them (matches forefst)
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


_CHKP_ROOT_INFO = [
    ("Object ID Table",           0x02, "CmsObjectTable, GetGlobalTableRoot(0)"),
    ("Medium Allocator Table",    0x21, "CmsVolume::InitializeVolumeAllocator, root 1"),
    ("Container Allocator Table", 0x20, "CmsVolume::InitializeVolumeAllocator, root 2"),
    ("Schema Table",              0x01, "CmsSchemaTable::InitializePhase2, root 3"),
    ("Parent-Child Table",        0x03, "CmsObjectTable::InitializeParentChildTable, root 4"),
    ("Object ID Table dup",       0x04, "CmsObjectTable failover root, root 5"),
    ("Block RefCount Table",      0x05, "CmsBlockRefcount::Initialize, root 6"),
    ("Container Table",           0x0B, "CmsVolumeContainer::Initialize, root 7 — BOOTSTRAP"),
    ("Container Table dup",       0x0C, "CmsVolumeContainer::Initialize, root 8 — BOOTSTRAP"),
    ("Schema Table dup",          0x06, "CmsSchemaTable failover root, root 9"),
    ("Container Index Table",     0x0E, "CmsVolumeContainer::InitializeIndex, root 10"),
    ("Integrity State Table",     0x0F, "CmsIntegrityState::GetIntegrityStateTable, root 11"),
    ("Small Allocator Table",     0x22, "CmsVolume::InitializeGlobalSAATables, root 12"),
]

# TableId (page+0x48, TableIdLow) -> canonical name. The CHKP root array above is the conventional
# index->TableId order, but the failover pair {0x0B,0x0C} at roots {7,8} (and root 12) is NOT bound to
# a fixed index->TableId order (finding #337): win11refs2tmillionsofactions carries roots 7/8 swapped
# (7->0x0C, 8->0x0B) and root 12 -> 0x0B. The chkp display must read the ON-DISK TableId, not assume it.
_TID_TO_NAME = {tid: name for (name, tid, _) in _CHKP_ROOT_INFO}

_CT_ROOT_INDICES = {7, 8, 12}

_CHKP_FLAG_BITS = {
    0x002: "always-set",
    0x010: "dedup-bit4",
    0x020: "dedup-bit5",
    0x080: "native-Win11-format",
    0x100: "dedup-bit8",
    0x200: "indirect-root-list",
    0x400: "metadata-checksum",
    0x2000: "insider-flag (Windows Insider build 29574+)",
}

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


def _hx(v):
    return f"0x{v:x}" if v is not None else "n/a"


def _sig_str(b):
    if not b: return "(empty)"
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b[:4])


def _hexdump_lines(data, base=0, width=16):
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        h = " ".join(f"{x:02x}" for x in chunk)
        a = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"    {base+i:08x}  {h:<{width*3}}  {a}")
    return "\n".join(lines)




# ─── VBR constants (shared by boot + bootedit) ──────────────────────

_VBR_FIELDS = [
    ("jump",            0x00, 3,  "Jump instruction"),
    ("fs_name",         0x03, 8,  "FS name (ReFS)"),
    ("reserved_0b",     0x0B, 5,  "Reserved"),
    ("fsrs_id",         0x10, 4,  "FSRS identifier"),
    ("vbr_size",        0x14, 2,  "VBR size"),
    ("checksum",        0x16, 2,  "Checksum"),
    ("total_sectors",   0x18, 8,  "Total sector count"),
    ("bytes_per_sect",  0x20, 4,  "Bytes per sector"),
    ("sects_per_clust", 0x24, 4,  "Sectors per cluster"),
    ("version",         0x28, 2,  "Version"),
    ("checksum_algo",   0x2A, 2,  "Checksum algorithm"),
    ("volume_flags",    0x2C, 4,  "Volume flags"),
    ("reserved_30",     0x30, 8,  "Reserved"),
    ("serial",          0x38, 8,  "Volume serial"),
    ("container_size",  0x40, 8,  "Bytes per container"),
    ("format_guid",     0x48, 16, "Extended GUID"),
]

_CHECKSUM_ALGO_MAP = {0: "None", 2: "CRC64", 4: "SHA256"}

_VOLUME_FLAG_BITS = {
    0x02: "mounted", 0x04: "valid-ReFS", 0x10: "recovery/dirty",
    0x20: "Win11-boot-behavior", 0x40: "checksum-algo-gate",
}

_ROOT_LABELS = [
    "Object ID Table", "Medium Allocator", "Container Allocator",
    "Schema Table", "Parent-Child Table", "Object ID Table dup",
    "Block RefCount", "Container Table", "Container Table dup",
    "Schema Table dup", "Container Index", "Integrity State",
    "Small Allocator",
]


def _vbr_checksum(sector, vbr_size):
    checksum = 0
    for off in range(0x03, vbr_size):
        if off in (0x16, 0x17): continue
        checksum = ((checksum >> 1) | ((checksum & 1) << 15)) & 0xFFFF
        checksum = (checksum + sector[off]) & 0xFFFF
    return checksum


def _volume_flags_description(value):
    parts = [f"0x{bit:02x}={name}" for bit, name in sorted(_VOLUME_FLAG_BITS.items()) if value & bit]
    return ", ".join(parts) if parts else "none"


def _bit_list(value):
    bits = [f"0x{(1 << i):08x}" for i in range(32) if value & (1 << i)]
    return ", ".join(bits) if bits else "none"


# ═══════════════════════════════════════════════════════════════════════
#  SUMMARY — Volume overview
# ═══════════════════════════════════════════════════════════════════════

def _summary_human_size(n):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def _count_dir_entries(f, ps, cs, tr, obj_map, oid, depth=0, max_depth=50, ext=None):
    empty = (0, 0, 0, 0, None, None)
    if oid not in obj_map or depth > max_depth:
        return empty
    try:
        rows = walk_bplus(f, ps, cs, tr, obj_map[oid])
    except Exception:
        return empty
    ndirs = nfiles = nresident = 0; total_size = 0
    oldest = newest = None
    for kd, vd in rows:
        if len(kd) < 4: continue
        _kt = le16(kd, 0)
        if _kt == 0x40:
            # backing type-0x40 stream as (alloc, size) under (this dir, file_id). The finalize step
            # resolves each name to the candidate stream (local or home) whose size matches the name's
            # own size — the per-directory ordinal (file_id @key+0x08) collides, so size is the
            # disambiguator. alloc @val+0x60, size @val+0x58. (#340 / over-merge fix 2026-06-20.)
            if ext is not None and len(kd) >= 0x10:
                _a = le64(vd, 0x60) if len(vd) >= 0x68 else 0
                _s = le64(vd, 0x58) if len(vd) >= 0x60 else 0
                ext["_t40"][(oid, le64(kd, 0x08))] = (_a, _s)
            continue
        if _kt != 0x30: continue
        if len(vd) <= 84:
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            create_time = le64(vd, 0x10) if len(vd) >= 0x18 else 0
            modify_time = le64(vd, 0x18) if len(vd) >= 0x20 else 0
            file_attrs = le32(vd, 0x40) if len(vd) >= 0x44 else 0
            file_size = le64(vd, 0x38) if len(vd) >= 0x40 else 0
            is_dir = bool(file_attrs & 0x10000000)
        else:
            child_oid = 0; create_time = le64(vd, 0x28) if len(vd) >= 0x30 else 0
            modify_time = le64(vd, 0x30) if len(vd) >= 0x38 else 0
            file_attrs = le32(vd, 0x48) if len(vd) >= 0x4C else 0
            file_size = get_resident_file_size(vd); is_dir = False; nresident += 1  # C10: real size, not 0
        if ext is not None:
            if file_attrs & 0x4000: ext["encrypted"] += 1
            if file_attrs & 0x8000: ext["integrity"] += 1
            if file_attrs & 0x0800: ext["compressed"] += 1
            if file_attrs & 0x0400: ext["reparse"] += 1
            if child_oid and not is_dir:
                # Defer hard-link grouping: collect (parent dir, file_id, home-backref, size, ctime,
                # mtime) and resolve each name to its true backing type-0x40 record after the full walk
                # (finalize in cmd_summary). The old (home, ordinal, size, ctime, mtime) tuple
                # false-merged distinct files that collided on it (fixed 2026-06-19; §J).
                file_id = le64(vd, 0x00) if len(vd) >= 8 else 0
                if file_id:
                    ext["_links"].append((oid, file_id, child_oid, file_size, create_time, modify_time))
        if is_dir:
            ndirs += 1
            if child_oid and child_oid in obj_map:
                sd, sf, sr, ss, so, sn = _count_dir_entries(f, ps, cs, tr, obj_map, child_oid, depth+1, max_depth, ext)
                ndirs += sd; nfiles += sf; nresident += sr; total_size += ss
                if so and (oldest is None or so < oldest): oldest = so
                if sn and (newest is None or sn > newest): newest = sn
        else:
            nfiles += 1; total_size += file_size
        for t in [create_time, modify_time]:
            if t and t != 0xFFFFFFFFFFFFFFFF:
                if oldest is None or t < oldest: oldest = t
                if newest is None or t > newest: newest = t
    return ndirs, nfiles, nresident, total_size, oldest, newest


def cmd_summary(image, remaining, partition_start, plus_mode=False):
    args = _parse_args(remaining, flags=["--json"])

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        # Read additional VBR fields
        f.seek(ps); bs = f.read(512)
        chk_type = le16(bs, 0x2A)
        total_sectors = le64(bs, 0x18)
        bpc = le64(bs, 0x40) if le64(bs, 0x40) != 0 else 0x4000000

        # Volume GUID from SUPB
        f.seek(ps + SUPB_LCN * cs); supb_data = f.read(cs)
        vol_guid = supb_data[0x50:0x60] if supb_data[:4] == b"SUPB" else b"\x00" * 16

        # Checkpoint info
        best_vc = 0; best_flags = 0
        for cl in chkp_lcns:
            try:
                vc, flags, _ = _forefst_parse_chkp(f, ps, cs, cl)
                if vc >= best_vc: best_vc = vc; best_flags = flags
            except Exception: pass

        # Root table row counts
        root_counts = {}
        for idx, vlcns in enumerate(roots):
            if not vlcns: root_counts[idx] = 0; continue
            use_tr = None if idx in _CT_ROOT_INDICES else tr
            try: root_counts[idx] = len(walk_bplus(f, ps, cs, use_tr, vlcns))
            except Exception: root_counts[idx] = 0

        # Schema table names
        schema_names = {}
        if len(roots) > 3 and roots[3]:
            try:
                for kd, vd in walk_bplus(f, ps, cs, tr, roots[3]):
                    if len(kd) >= 4 and len(vd) >= 4:
                        # C15: the schema value is an 80-byte BINARY definition, not UTF-16 text; only the
                        # count of distinct schema ids is consumed ('schema_tables' below). Don't decode.
                        schema_names[le32(kd, 0)] = None
            except Exception: pass

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
                        vol_detail["raw_0x520"] = vd
                    elif kt == 0x0540 and len(vd) >= 8:
                        vol_detail["schema_count"] = le32(vd, 0)
                        vol_detail["vol_flags_540"] = le32(vd, 4) if len(vd) >= 8 else 0
            except Exception: pass

        # File/dir counts (extended counters in plus_mode)
        ext = {"encrypted": 0, "integrity": 0, "compressed": 0, "reparse": 0,
               "hardlinks": 0, "_t40": {}, "_links": []} if plus_mode else None
        ndirs, nfiles, nresident, total_size, oldest, newest = _count_dir_entries(f, ps, cs, tr, obj_map, 0x600, ext=ext)

        # Finalize hard-link count: group each name by its TRUE physical stream (owner-dir, file_id).
        # The per-directory ordinal (file_id) collides, so resolve each name to the candidate stream —
        # local (parent,file_id) or home (home,file_id) — whose 0x40 size EQUALS the name's own size
        # (the on-disk disambiguator). STRICT size-match => 0 over-merge; names matching no candidate
        # are not merged (solo). extra-names = sum(group_size - 1). Validated all-disk 2026-06-20.
        if ext is not None:
            _hl = {}
            for _i, (_P, _fid, _home, _S, _ct, _mt) in enumerate(ext["_links"]):
                _loc = ext["_t40"].get((_P, _fid)); _rem = ext["_t40"].get((_home, _fid))  # (alloc,size) or None
                if _loc and _loc[1] == _S and _loc[0] > 0:           # living here: local size+alloc match
                    _sg = ("obj", _P, _fid)
                elif _rem and _rem[1] == _S:                          # content at home: home size matches
                    _sg = ("obj", _home, _fid)
                elif _loc and _loc[1] == _S:                          # local size matches (alloc 0 edge)
                    _sg = ("obj", _P, _fid)
                elif _S == 0 and _rem is not None and _rem[1] == 0:   # empty file: canonical empty home stream
                    _sg = ("obj", _home, _fid, 0)
                elif _S == 0 and _loc is not None and _loc[1] == 0:
                    _sg = ("obj", _P, _fid, 0)
                else:                                                 # no size-matching stream -> solo
                    _sg = ("solo", _i)
                _hl[_sg] = _hl.get(_sg, 0) + 1
            ext["hardlinks"] = sum(c - 1 for c in _hl.values() if c > 1)

        # Security descriptor count
        sec_count = 0
        if 0x530 in obj_map:
            try: sec_count = len(walk_bplus(f, ps, cs, tr, obj_map[0x530]))
            except Exception: pass

        # Container table size
        ct_size = root_counts.get(7, 0)

        # Compression config from container table page (select CT by Table-ID 0x0B, not index 7 — #337)
        compression = None
        _ct_root = _select_ct_root(f, ps, cs, roots)
        if _ct_root:
            use_tr = None
            try:
                ct_abs = ps + _ct_root[0] * cs
                f.seek(ct_abs)
                ct_page = f.read(cs)
                if len(ct_page) >= 0xB0:
                    prefix = le32(ct_page, 0xA0)
                    if prefix == 0x0F:
                        fmt_map = {0: "None", 1: "LZ4", 2: "Zstd", 3: "LZ4QAT"}
                        comp_fmt = le16(ct_page, 0xA4)
                        compression = fmt_map.get(comp_fmt, f"Unknown({comp_fmt})")
            except Exception:
                pass

        checksum_types = {0: "None", 2: "CRC64", 4: "SHA-256"}
        volume_bytes = total_sectors * 512

        hs = _summary_human_size
        summary = {
            "image": os.path.basename(image),
            "refs_version": f"{vmaj}.{vmin}",
            "volume_guid": _guid_str(vol_guid),
            "volume_label": vol_label or "(none)",
            "volume_size": hs(volume_bytes),
            "volume_size_bytes": volume_bytes,
            "cluster_size": cs,
            "container_size": bpc,
            "checksum": checksum_types.get(chk_type, f"Unknown({chk_type})"),
            "compression": compression or "Not configured",
            "checkpoint_vc": best_vc,
            "checkpoint_flags": f"0x{best_flags:x}",
            "containers_mapped": ct_size,
            "objects": len(obj_map),
            "directories": ndirs,
            "files": nfiles,
            "resident_files": nresident,
            "total_file_size": hs(total_size),
            "total_file_size_bytes": total_size,
            "security_descriptors": sec_count,
            "schema_tables": len(schema_names),
            "oldest_timestamp": _filetime_to_str(oldest) if oldest else "(none)",
            "newest_timestamp": _filetime_to_str(newest) if newest else "(none)",
            "root_table_rows": {_ROOT_LABELS[i]: root_counts.get(i, 0)
                                for i in range(min(13, len(roots)))},
        }

        if plus_mode and vol_detail:
            vv = vol_detail
            summary["volume_version"] = f"{vv.get('vol_major','?')}.{vv.get('vol_minor','?')}"
            summary["driver_version"] = f"{vv.get('drv_major','?')}.{vv.get('drv_minor','?')}"
            summary["volume_create_time"] = _filetime_to_str(vv.get("vol_create_time", 0))
            summary["volume_modify_time"] = _filetime_to_str(vv.get("vol_modify_time", 0))
            summary["schema_count_500"] = vv.get("schema_count", 0)

            # Reparse index count
            reparse_count = 0
            if 0x540 in obj_map:
                try: reparse_count = len(walk_bplus(f, ps, cs, tr, obj_map[0x540]))
                except Exception: pass
            summary["reparse_index_entries"] = reparse_count

            # Trash table
            trash_count = 0
            if 0xD in obj_map:
                try: trash_count = len(walk_bplus(f, ps, cs, tr, obj_map[0xD]))
                except Exception: pass
            summary["trash_table_entries"] = trash_count

            # FS Metadata directory (OID 0x520)
            fs_meta = {"rows": 0, "children": [], "usn_journal": False}
            if 0x520 in obj_map:
                try:
                    for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x520]):
                        fs_meta["rows"] += 1
                        if len(kd) >= 4 and le16(kd, 0) == 0x30:
                            try: name = kd[4:].decode("utf-16-le").rstrip("\x00")
                            except Exception: name = "(decode error)"
                            flags = le32(vd, 0x80) if len(vd) >= 0x84 else 0
                            child = {"name": name, "flags": flags}
                            if name == "Change Journal":
                                fs_meta["usn_journal"] = True
                                if len(vd) >= 0x28:
                                    child["stream_count"] = le64(vd, 0x20)
                            fs_meta["children"].append(child)
                except Exception:
                    pass
            summary["fs_metadata"] = fs_meta

            # Container utilization
            if tr and ct_size > 0:
                used = sum(1 for c in tr.map.values() if c > 0)
                summary["containers_used"] = used
                summary["containers_free"] = ct_size - used
                summary["utilization_pct"] = round(100.0 * used / ct_size, 1)
                summary["free_space_est"] = hs((ct_size - used) * bpc)

            # Extended file attribute counts
            if ext is not None:
                summary["encrypted_files"] = ext["encrypted"]
                summary["integrity_files"] = ext["integrity"]
                summary["compressed_files"] = ext["compressed"]
                summary["reparse_files"] = ext["reparse"]
                summary["hardlink_extra"] = ext["hardlinks"]

            # Symlink count from reparse index (tag at key offset 4)
            symlink_count = 0
            if 0x540 in obj_map:
                try:
                    for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x540]):
                        if len(kd) >= 8 and le32(kd, 4) == 0xA000000C:
                            symlink_count += 1
                except Exception: pass
            summary["symlinks"] = symlink_count

            # Snapshot + ADS counts
            snap_results = []
            try:
                _find_snapshot_files(f, ps, cs, tr, obj_map, 0x600, "", 0, 10, snap_results)
            except Exception: pass
            total_snaps = total_ads = 0
            for r in snap_results:
                for s in r.get("snapshots", []):
                    if s.get("is_true_snapshot", True): total_snaps += 1
                    else: total_ads += 1
            summary["snapshots"] = total_snaps
            summary["ads_entries"] = total_ads

        if args["json"]:
            print(json.dumps(summary, indent=2))
            return 0

        w = 78
        print("=" * w)
        print("ReFS Volume Summary" + (" (extended)" if plus_mode else ""))
        print("=" * w)
        print(f"  Image:              {summary['image']}")
        print(f"  ReFS version:       {summary['refs_version']}")
        print(f"  Volume GUID:        {summary['volume_guid']}")
        print(f"  Volume label:       {summary['volume_label']}")
        print(f"  Volume size:        {summary['volume_size']}")
        print(f"  Cluster size:       0x{cs:x} ({hs(cs)})")
        print(f"  Container size:     0x{bpc:x} ({hs(bpc)})")
        print(f"  Checksum:           {summary['checksum']}")
        print(f"  Compression:        {summary['compression']}")
        print()
        print("-" * w)
        print("Checkpoint")
        print("-" * w)
        print(f"  Virtual clock:      {summary['checkpoint_vc']}")
        print(f"  Flags:              {summary['checkpoint_flags']}")
        print(f"  Containers mapped:  {summary['containers_mapped']}")
        print()
        print("-" * w)
        print("File System Content")
        print("-" * w)
        print(f"  Objects:            {summary['objects']}")
        print(f"  Directories:        {summary['directories']}")
        print(f"  Files:              {summary['files']} ({summary['resident_files']} resident)")
        print(f"  Total file size:    {summary['total_file_size']}")
        print(f"  Security descs:     {summary['security_descriptors']}")
        print(f"  Oldest timestamp:   {summary['oldest_timestamp']}")
        print(f"  Newest timestamp:   {summary['newest_timestamp']}")
        print()
        print("-" * w)
        print("Global Root Tables")
        print("-" * w)
        for name, count in summary["root_table_rows"].items():
            print(f"  {name:<28} {count:>6} rows")

        if plus_mode:
            print()
            print("-" * w)
            print("Volume Detail (OID 0x500)")
            print("-" * w)
            if "volume_version" in summary:
                print(f"  Volume version:     {summary['volume_version']}")
                print(f"  Driver version:     {summary['driver_version']}")
                print(f"  Volume created:     {summary['volume_create_time']}")
                print(f"  Volume modified:    {summary['volume_modify_time']}")
                if summary.get("schema_count_500"):
                    print(f"  Schema count:       {summary['schema_count_500']}")
            else:
                print("  (no volume detail data in OID 0x500)")
            print()
            print("-" * w)
            print("FS Metadata Directory (OID 0x520)")
            print("-" * w)
            fm = summary.get("fs_metadata", {})
            print(f"  Rows:               {fm.get('rows', 0)}")
            fm_children = fm.get("children", [])
            if fm_children:
                _DEGENERATE_FLAGS = {0x100: "DASD", 0x200: "Security", 0x400: "Reparse"}
                for ch in fm_children:
                    tag = _DEGENERATE_FLAGS.get(ch.get("flags", 0), "")
                    extra = f"  (degenerate: {tag})" if tag else ""
                    sc = ch.get("stream_count")
                    if sc is not None:
                        extra = f"  (streams: {sc})"
                    print(f"    {ch['name']}{extra}")
            else:
                print("  Children:           (none)")
            print(f"  USN Journal:        {'Active' if fm.get('usn_journal') else 'Inactive'}")
            print()
            print("-" * w)
            print("Extended Metrics")
            print("-" * w)
            print(f"  Reparse index:      {summary.get('reparse_index_entries', 0)} entries")
            print(f"  Symlinks:           {summary.get('symlinks', 0)}")
            print(f"  Snapshots:          {summary.get('snapshots', 0)}")
            print(f"  ADS entries:        {summary.get('ads_entries', 0)}")
            print(f"  Hard links (extra): {summary.get('hardlink_extra', 0)}")
            print(f"  Encrypted files:    {summary.get('encrypted_files', 0)}")
            print(f"  Integrity files:    {summary.get('integrity_files', 0)}")
            print(f"  Compressed files:   {summary.get('compressed_files', 0)}")
            print(f"  Trash table:        {summary.get('trash_table_entries', 0)} entries")
            if "containers_used" in summary:
                print(f"  Containers used:    {summary['containers_used']} / {summary['containers_mapped']}"
                      f" ({summary['utilization_pct']}%)")
                print(f"  Free space (est):   {summary['free_space_est']}")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  BOOT — VBR analysis
# ═══════════════════════════════════════════════════════════════════════



def cmd_boot(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify", "--raw", "-H"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    verify = args["verify"]
    show_header = args["H"] or verbose >= 1

    bo = _find_boot_offset(image, partition_start)
    with open(image, "rb") as f:
        sector = _read_at(f, bo, 512)

    if sector[0x03:0x07] != b"ReFS" or sector[0x10:0x14] != b"FSRS":
        if b"-FVE-FS-" in sector[:0x40]:
            die(f"partition at 0x{bo:x} is BitLocker-encrypted")
        die(f"no ReFS boot sector at offset 0x{bo:x}")

    sha = hashlib.sha256(sector).hexdigest()
    vbr_size = struct.unpack("<H", sector[0x14:0x16])[0]
    stored_chk = struct.unpack("<H", sector[0x16:0x18])[0]
    computed_chk = _vbr_checksum(sector, vbr_size)
    chk_ok = stored_chk == computed_chk
    total_sectors = le64(sector, 0x18)
    bps = le32(sector, 0x20); spc = le32(sector, 0x24)
    cluster_size = bps * spc; volume_size = total_sectors * bps
    major = sector[0x28]; minor = sector[0x29]
    chk_algo = struct.unpack("<H", sector[0x2A:0x2C])[0]
    flags = le32(sector, 0x2C)
    serial = le64(sector, 0x38)
    bpc = le64(sector, 0x40)
    guid_raw = sector[0x48:0x58]
    algo_name = _CHECKSUM_ALGO_MAP.get(chk_algo, f"unknown(0x{chk_algo:04x})")
    guid_text = _guid_to_text(guid_raw) if guid_raw != b"\x00" * 16 else "(not set)"
    cpc = bpc // cluster_size if bpc and cluster_size else None
    container_count = volume_size // bpc if bpc else None

    def _emit_verify():
        # --verify consistency table. Factored out so it runs on EVERY render path (it used to be
        # unreachable without -v, because the verbose==0 paths return before it — contract bug fix 2026-06-20).
        checks = [
            ["jump_is_zero", _ok(sector[0:3] == b"\x00\x00\x00"), f"stored={_hexbytes(sector[0:3])}"],
            ["fs_name_is_ReFS", _ok(sector[3:7] == b"ReFS"), f"stored={_ascii_clean(sector[3:0xB])}"],
            ["reserved_0x0B_zero", _ok(sector[0xB:0x10] == b"\x00" * 5), f"stored={_hexbytes(sector[0xB:0x10])}"],
            ["fsrs_is_FSRS", _ok(sector[0x10:0x14] == b"FSRS"), f"stored={_ascii_clean(sector[0x10:0x14])}"],
            ["vbr_size_is_512", _ok(vbr_size == 512), f"stored={vbr_size}"],
            ["bps_is_512", _ok(bps == 512), f"stored={bps}"],
            ["checksum_match", _ok(chk_ok), f"stored=0x{stored_chk:04X}, computed=0x{computed_chk:04X}"],
            ["container_nonzero", _ok(bpc != 0), f"stored=0x{bpc:x}"],
            ["container_aligned", _ok(bpc != 0 and cluster_size != 0 and bpc % cluster_size == 0),
             f"container=0x{bpc:x}, cluster=0x{cluster_size:x}"],
        ]
        print("Verification")
        print("-" * 72)
        _print_table(["Check", "Result", "Details"], checks)

    if args["raw"]:
        print(f"\nReFS Boot Sector at offset 0x{bo:X}")
        print(f"SHA-256: {sha}\n")
        for row_off in range(0, len(sector), 16):
            chunk = sector[row_off:row_off + 16]
            h = " ".join(f"{b:02x}" for b in chunk)
            a = _ascii_clean(chunk)
            print(f"  {row_off:04x}  {h:<48s}  |{a}|")
        print(); return 0

    if verbose == 0 and not show_header:
        print(f"\nReFS Boot Sector at offset 0x{bo:X}")
        print(f"SHA-256: {sha}\n")
        rows = [
            ["Jump instruction",    "0x00", _hexbytes(sector[0:3]), ""],
            ["FS name (ReFS)",      "0x03", _hexbytes(sector[3:0xB]), _ascii_clean(sector[3:0xB])],
            ["Reserved",            "0x0B", _hexbytes(sector[0xB:0x10]), ""],
            ["FSRS identifier",     "0x10", _hexbytes(sector[0x10:0x14]), _ascii_clean(sector[0x10:0x14])],
            ["VBR size",            "0x14", _hexbytes(sector[0x14:0x16]), f"{vbr_size} (0x{vbr_size:04X})"],
            ["Checksum",            "0x16", _hexbytes(sector[0x16:0x18]), f"0x{stored_chk:04X} [{_ok(chk_ok)}]"],
            ["Total sector count",  "0x18", _hexbytes(sector[0x18:0x20]), f"{total_sectors} ({_human_size(volume_size)})"],
            ["Bytes per sector",    "0x20", _hexbytes(sector[0x20:0x24]), f"{bps}"],
            ["Sectors per cluster", "0x24", _hexbytes(sector[0x24:0x28]), f"{spc} (cluster = {_human_size(cluster_size)})"],
            ["Version",             "0x28", _hexbytes(sector[0x28:0x2A]), f"{major}.{minor}"],
            ["Checksum algorithm",  "0x2A", _hexbytes(sector[0x2A:0x2C]), f"0x{chk_algo:04X} ({algo_name})"],
            ["Volume flags",        "0x2C", _hexbytes(sector[0x2C:0x30]), f"0x{flags:08X}"],
            ["Reserved",            "0x30", _hexbytes(sector[0x30:0x38]), ""],
            ["Volume serial",       "0x38", _hexbytes(sector[0x38:0x40]), f"0x{serial:016X}"],
            ["Bytes per container", "0x40", _hexbytes(sector[0x40:0x48]), f"{_human_size(bpc)}" if bpc else "0"],
            ["Format instance GUID","0x48", _hexbytes(guid_raw), guid_text],
            ["Reserved (trailing)", "0x58", "424 bytes", "NON-ZERO" if any(b != 0 for b in sector[0x58:]) else "all zero"],
        ]
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], rows)
        if verify: _emit_verify()
        return 0

    if show_header:
        print(f"\nReFS Boot Sector / FSRS")
        print("=" * 72)
        print(f"Image:        {image}")
        print(f"Image size:   {_human_size(os.path.getsize(image))} ({os.path.getsize(image)} bytes)")
        print(f"VBR SHA-256:  {sha}")
        print(f"VBR offset:   0x{bo:x}")
        print()

    if verbose == 0:
        rows = [
            ["Jump instruction",    "0x00", _hexbytes(sector[0:3]), ""],
            ["FS name (ReFS)",      "0x03", _hexbytes(sector[3:0xB]), _ascii_clean(sector[3:0xB])],
            ["Reserved",            "0x0B", _hexbytes(sector[0xB:0x10]), ""],
            ["FSRS identifier",     "0x10", _hexbytes(sector[0x10:0x14]), _ascii_clean(sector[0x10:0x14])],
            ["VBR size",            "0x14", _hexbytes(sector[0x14:0x16]), f"{vbr_size} (0x{vbr_size:04X})"],
            ["Checksum",            "0x16", _hexbytes(sector[0x16:0x18]), f"0x{stored_chk:04X} [{_ok(chk_ok)}]"],
            ["Total sector count",  "0x18", _hexbytes(sector[0x18:0x20]), f"{total_sectors} ({_human_size(volume_size)})"],
            ["Bytes per sector",    "0x20", _hexbytes(sector[0x20:0x24]), f"{bps}"],
            ["Sectors per cluster", "0x24", _hexbytes(sector[0x24:0x28]), f"{spc} (cluster = {_human_size(cluster_size)})"],
            ["Version",             "0x28", _hexbytes(sector[0x28:0x2A]), f"{major}.{minor}"],
            ["Checksum algorithm",  "0x2A", _hexbytes(sector[0x2A:0x2C]), f"0x{chk_algo:04X} ({algo_name})"],
            ["Volume flags",        "0x2C", _hexbytes(sector[0x2C:0x30]), f"0x{flags:08X}"],
            ["Reserved",            "0x30", _hexbytes(sector[0x30:0x38]), ""],
            ["Volume serial",       "0x38", _hexbytes(sector[0x38:0x40]), f"0x{serial:016X}"],
            ["Bytes per container", "0x40", _hexbytes(sector[0x40:0x48]), f"{_human_size(bpc)}" if bpc else "0"],
            ["Format instance GUID","0x48", _hexbytes(guid_raw), guid_text],
        ]
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], rows)
        if verify: _emit_verify()
        return 0

    if verbose >= 1:
        interpreted = [
            ["fs_name", _ascii_clean(sector[3:0xB])],
            ["fsrs_identifier", _ascii_clean(sector[0x10:0x14])],
            ["vbr_size", f"0x{vbr_size:04X} ({vbr_size})"],
            ["format_version", f"{major}.{minor}"],
            ["checksum_algorithm", f"0x{chk_algo:04X} ({algo_name})"],
            ["format_instance_guid", guid_text],
            ["cluster_size", f"{bps} * {spc} = {cluster_size} ({_human_size(cluster_size)})"],
            ["volume_size", f"{total_sectors} * {bps} = {volume_size} ({_human_size(volume_size)})"],
            ["container_size", f"{_human_size(bpc)} ({cpc} clusters)" if bpc and cpc else "0"],
            ["container_count", f"{container_count}" if container_count else "n/a"],
            ["volume_flags", f"0x{flags:08X} [{_volume_flags_description(flags)}]"],
            ["volume_serial", f"0x{serial:016X}"],
            ["checksum_stored", f"0x{stored_chk:04X}"],
            ["checksum_computed", f"0x{computed_chk:04X} [{_ok(chk_ok)}]"],
        ]
        print("Interpreted values")
        print("-" * 72)
        _print_table(["Field", "Value"], interpreted)

        structure_rows = []
        for name, offset, size, desc in _VBR_FIELDS:
            end = offset + size - 1
            structure_rows.append([f"0x{offset:02x}-0x{end:02x}", desc, _hexbytes(sector[offset:offset+size])])
        print("Boot sector structure")
        print("-" * 72)
        _print_table(["Byte range", "Description", "Raw value"], structure_rows)

    if verify:
        _emit_verify()

    if verbose >= 2:
        print("Verbose calculations")
        print("-" * 72)
        print(f"  VBR offset     = 0x{bo:x}")
        print(f"  VBR SHA-256    = {sha}")
        print(f"\n  cluster_size   = {bps} * {spc} = {cluster_size} ({_human_size(cluster_size)})")
        print(f"  volume_size    = {total_sectors} * {bps} = {volume_size} ({_human_size(volume_size)})")
        if bpc:
            print(f"\n  container_size = 0x{bpc:x} ({_human_size(bpc)})")
            print(f"  clusters/cont  = {cpc}")
            print(f"  container_cnt  = {container_count}")
        print(f"\n  volume_flags   = 0x{flags:08X}")
        print(f"  bits set       = {_bit_list(flags)}")
        print(f"  meaning        = {_volume_flags_description(flags)}")
        print(f"\n  checksum algo  = ROR1+ADD over 0x03..{vbr_size}, skip 0x16-0x17")
        print(f"  stored         = 0x{stored_chk:04X}")
        print(f"  computed       = 0x{computed_chk:04X}")
        print(f"\n  format GUID    = {guid_text}")
        if guid_raw == b"\x00" * 16:
            print("  (not set — Win10-formatted or fixboot-repaired)")
        _gp = gpt_partition_detail(image)
        if _gp:
            print(f"\n  GPT partition  = #{_gp['index']} '{_gp['name']}'")
            print(f"  partition LBA  = {_gp['first_lba']}-{_gp['last_lba']}")
            print(f"  partition size = {_gp['size_bytes']} ({_human_size(_gp['size_bytes'])})")
        print()

    return 0


# ═══════════════════════════════════════════════════════════════════════
#  SUPB — Superblock analysis
# ═══════════════════════════════════════════════════════════════════════

def cmd_supb(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify", "--raw", "-H"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    verify = args["verify"]
    show_header = args["H"] or verbose >= 1

    bo = _find_boot_offset(image, partition_start)
    img_size = os.path.getsize(image)

    with open(image, "rb") as f:
        sector = _read_at(f, bo, 512)
        if sector[0x03:0x07] != b"ReFS": die("not ReFS")
        bps = le32(sector, 0x20); spc = le32(sector, 0x24)
        cs = bps * spc

        supb_abs = bo + SUPB_LCN * cs
        supb_page = _read_at(f, supb_abs, cs)
        supb_sha = hashlib.sha256(supb_page).hexdigest()

        if supb_page[:4] != b"SUPB": die("SUPB signature mismatch")

        raw_guid = supb_page[0x50:0x60]
        guid_text = _guid_to_text(raw_guid) if raw_guid != b"\x00" * 16 else "(not set)"
        x1, x2, x3, x4 = [le32(raw_guid, i*4) for i in range(4)]
        guid_xor = x1 ^ x2 ^ x3 ^ x4

        sb_version = le64(supb_page, 0x68)
        chkp_off = le32(supb_page, 0x70)
        chkp_cnt = le32(supb_page, 0x74)
        self_off = le32(supb_page, 0x78)
        self_len = le32(supb_page, 0x7C)
        self_block = le64(supb_page, 0x20)
        expected_self = (supb_abs - bo) // cs

        checkpoints = []
        _cnt = chkp_cnt
        if _cnt > 8:   # N3/E9: clamp a fuzzed/corrupt count (doc: 2) — an unbounded loop would hang the tool
            print(f"[{PROG}] WARNING: SUPB checkpoint-ref count {chkp_cnt} implausible (doc=2); scanning 8", file=sys.stderr)
            _cnt = 8
        for i in range(_cnt):
            block = le64(supb_page, chkp_off + i * 8)
            resolved = bo + block * cs
            chkp_hdr = {}
            if resolved + 0x80 <= img_size:
                h = _read_at(f, resolved, 0x80)
                chkp_hdr = {
                    "signature": h[0:4], "virtual_clock": le64(h, 0x10),
                    "self_block": le64(h, 0x20), "alloc_clock": le64(h, 0x68),
                    "major": struct.unpack("<H", h[0x54:0x56])[0],
                    "minor": struct.unpack("<H", h[0x56:0x58])[0],
                }
            checkpoints.append({"index": i+1, "block": block, "resolved": resolved, "chkp": chkp_hdr})

        valid_chkp = [c for c in checkpoints if c["chkp"].get("signature") == b"CHKP"]
        latest = max(valid_chkp, key=lambda c: c["chkp"]["virtual_clock"]) if valid_chkp else None

        self_desc_raw = _read_at(f, supb_abs + self_off, self_len) if self_off + self_len <= cs else b""
        self_first_qw = le64(self_desc_raw, 0) if len(self_desc_raw) >= 8 else None

    def _emit_verify():
        # --verify consistency table — runs on every render path (used to be unreachable without -v/-H;
        # contract bug fix 2026-06-20).
        checks = [
            ["signature_is_SUPB", _ok(supb_page[:4] == b"SUPB"), f"stored={supb_page[:4]!r}"],
            ["self_block_matches", _ok(self_block == expected_self),
             f"stored=0x{self_block:x}, expected=0x{expected_self:x}"],
            ["checkpoint_count_is_2", _ok(chkp_cnt == 2), f"count={chkp_cnt}"],
            ["all_checkpoints_valid", _ok(all(c["chkp"].get("signature") == b"CHKP" for c in checkpoints)),
             ", ".join(f"#{c['index']}={_ascii_clean(c['chkp'].get('signature', b'??'))}" for c in checkpoints)],
            ["latest_identified", _ok(latest is not None),
             f"#{latest['index']} vc={latest['chkp']['virtual_clock']}" if latest else "n/a"],
            ["self_desc_matches", _ok(self_first_qw == self_block),
             f"desc=0x{self_first_qw:x}, block=0x{self_block:x}" if self_first_qw is not None else "n/a"],
            # C14: SHA-256 volumes use a 0x48 self-descriptor (0x68 v3.4 / 0x30 v3.14 CRC64 / 0x48 SHA-256,
            # structure_reference §A + chkp.md). Omitting 0x48 made supb --verify FAIL on clean SHA-256 volumes.
            ["self_desc_known_size", _ok(self_len in (0x30, 0x48, 0x68)), f"0x{self_len:x}"],
        ]
        print("Verification")
        print("-" * 72)
        _print_table(["Check", "Result", "Details"], checks)

    if args["raw"]:
        print(f"\nReFS Superblock (SUPB) at offset 0x{supb_abs:X}")
        print(f"SHA-256: {supb_sha}\n")
        for row_off in range(0, min(len(supb_page), 0x200), 16):
            chunk = supb_page[row_off:row_off + 16]
            h = " ".join(f"{b:02x}" for b in chunk)
            a = _ascii_clean(chunk)
            print(f"  {row_off:04x}  {h:<48s}  |{a}|")
        print(); return 0

    if verbose == 0 and not show_header:
        print(f"\nReFS Superblock (SUPB) at offset 0x{supb_abs:X}")
        print(f"SHA-256: {supb_sha}\n")

    if show_header and verbose == 0:
        print(f"\nReFS Superblock (SUPB)")
        print("=" * 72)
        print(f"Image:            {image}")
        print(f"SUPB SHA-256:     {supb_sha}")
        print(f"SUPB offset:      0x{supb_abs:x}")
        print(f"Cluster size:     0x{cs:x}")
        print()

    compact_rows = [
        ["Signature",             "0x00", _hexbytes(supb_page[0:4]),              _ascii_clean(supb_page[0:4])],
        ["Page header",           "0x00", _hexbytes(supb_page[0:16]) + " ...",   ""],
        ["Volume GUID",           "0x50", _hexbytes(raw_guid),                   guid_text],
        ["GUID XOR (vol sig)",    "   -", "",                                    f"0x{guid_xor:08X}"],
        ["Superblock version",    "0x68", _hexbytes(supb_page[0x68:0x70]),       f"{sb_version}"],
        ["Checkpoint refs offset","0x70", _hexbytes(supb_page[0x70:0x74]),       f"SUPB+0x{chkp_off:X}"],
        ["Checkpoint refs count", "0x74", _hexbytes(supb_page[0x74:0x78]),       f"{chkp_cnt}"],
        ["Self-desc offset",      "0x78", _hexbytes(supb_page[0x78:0x7C]),       f"SUPB+0x{self_off:X}"],
        ["Self-desc length",      "0x7C", _hexbytes(supb_page[0x7C:0x80]),       f"0x{self_len:X} ({self_len})"],
    ]

    if verbose == 0:
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], compact_rows)
        for c in checkpoints:
            ch = c["chkp"]
            marker = " *" if latest and c["index"] == latest["index"] else ""
            vc = ch.get("virtual_clock", "?"); ac = ch.get("alloc_clock", "?")
            print(f"  CHKP #{c['index']}: cluster 0x{c['block']:X} -> 0x{c['resolved']:X}  vc={vc} ac={ac}{marker}")
        if latest: print("  (* = active checkpoint)")
        if verify: _emit_verify()
        print(); return 0

    if show_header:
        print(f"\nReFS Superblock (SUPB)")
        print("=" * 72)
        print(f"Image:            {image}")
        print(f"SUPB SHA-256:     {supb_sha}")
        print(f"SUPB offset:      0x{supb_abs:x}")
        print(f"Cluster size:     0x{cs:x}")
        print()

    if verbose >= 1:
        latest_val = "n/a"
        if latest:
            ch = latest["chkp"]
            latest_val = f"checkpoint #{latest['index']} @ 0x{latest['resolved']:x} (vc={ch['virtual_clock']}, ac={ch['alloc_clock']})"
        interp = [
            ["signature", _ascii_clean(supb_page[0:4])],
            ["self_block", f"0x{self_block:x}"],
            ["expected_self_block", f"0x{expected_self:x}"],
            ["self_block_matches", str(self_block == expected_self)],
            ["volume_guid", guid_text],
            ["guid_xor", f"0x{guid_xor:08x}"],
            ["superblock_version", f"{sb_version}"],
            ["checkpoint_count", f"{chkp_cnt}"],
            ["latest_checkpoint", latest_val],
            ["self_desc_length_profile",
             "0x68 (v3.4)" if self_len == 0x68 else "0x30 (v3.14)" if self_len == 0x30 else f"0x{self_len:x}"],
        ]
        print("Interpreted values")
        print("-" * 72)
        _print_table(["Field", "Value"], interp)

        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], compact_rows)

        print("Checkpoint references")
        print("-" * 72)
        for c in checkpoints:
            ch = c["chkp"]
            marker = " <- active" if latest and c["index"] == latest["index"] else ""
            sig = _ascii_clean(ch.get("signature", b"????"))
            vc = ch.get("virtual_clock", "?"); ac = ch.get("alloc_clock", "?")
            ver = f"{ch.get('major','?')}.{ch.get('minor','?')}"
            print(f"  #{c['index']}: cluster 0x{c['block']:X} -> 0x{c['resolved']:X}")
            print(f"       sig={sig} vc={vc} ac={ac} ver={ver}{marker}")
        print()

    if verify:
        _emit_verify()

    if verbose >= 2:
        print("Verbose calculations")
        print("-" * 72)
        print(f"  SUPB offset     = 0x{supb_abs:x}")
        print(f"  partition start = 0x{bo:x}")
        print(f"  relative offset = 0x{supb_abs - bo:x}")
        print(f"  expected self   = 0x{expected_self:x}")
        print(f"  stored self     = 0x{self_block:x}")
        print(f"\n  GUID raw        = {_hexbytes(raw_guid)}")
        print(f"  GUID text       = {guid_text}")
        print(f"  GUID XOR        = 0x{guid_xor:08x}")
        print()
        for c in checkpoints:
            ch = c["chkp"]
            print(f"  Checkpoint #{c['index']}: block=0x{c['block']:x} -> 0x{c['resolved']:x}")
            if ch:
                print(f"    sig={ch.get('signature',b'?')!r} vc={ch.get('virtual_clock','?')} ac={ch.get('alloc_clock','?')}")
                print(f"    self_block=0x{ch.get('self_block',0):x} ver={ch.get('major','?')}.{ch.get('minor','?')}")
            print()
        print(f"  Self-descriptor: offset=0x{self_off:x} len=0x{self_len:x}")
        if self_desc_raw:
            print(f"  Raw: {_hexbytes(self_desc_raw)}")
        print()

    return 0


# ═══════════════════════════════════════════════════════════════════════
#  SCHEMA — Schema table reader
# ═══════════════════════════════════════════════════════════════════════

_TABLE_TYPE_NAMES = {
    0x4: "Allocator Medium Table (legacy)", 0x6: "Allocator Large Table (legacy)",
    0x110: "Directory Entry List", 0x120: "File Stream",
    0x130: "$FILE_NAME (dir entry)", 0x140: "$FILE_NAME (long)",
    0x150: "Volume Information", 0x160: "Reparse Index",
    0x170: "Reparse Point", 0x180: "$DATA",
    0x190: "$STANDARD_INFORMATION", 0x1a0: "$INDEX_ROOT",
    0x1b0: "Stream Snapshot ($SNAPSHOT)", 0x1c0: "$REPARSE_POINT (v3.7+)",
    0x1d0: "$EA_INFORMATION (v3.7+)", 0x1e0: "$EA (v3.14+)",
    0x1f0: "$LOGGED_UTILITY_STREAM (v3.14+)", 0x200: "$LOGGED_UTILITY_STREAM_V2 ($EFS)",
    0xe010: "Allocator Table", 0xe030: "Object ID Table",
    0xe040: "Parent-Child Table", 0xe050: "Object Data Table (legacy)",
    0xe060: "Schema Table", 0xe070: "Reserved / Placeholder (legacy)",
    0xe080: "Integrity State Table", 0xe090: "Upcase / Logfile Info Table",
    0xe0b0: "Block RefCount Table", 0xe0c0: "Container Table",
    0xe0d0: "Trash Table", 0xe0e0: "System Directory Entry List (legacy)",
    0xe0f0: "System File Stream (legacy)", 0xe100: "Container Index Table",
    0xe110: "Read Cache Metadata", 0xe120: "Candidate Table (Dirty Ranges)",
    0xe130: "Heat Engine Persistence", 0xe140: "Volume Attestation Table (Insider)",
}


def cmd_schema(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify", "-H"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    show_header = args["H"] or verbose >= 1

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        if len(roots) <= 3 or not roots[3]:
            die("Schema Table root not found")

        entries = []
        for kd, vd in walk_bplus(f, ps, cs, tr, roots[3]):
            if len(kd) >= 4:
                entries.append((le32(kd, 0), vd))

        attr_entries = [(k, v) for k, v in entries if k < 0xe000]
        sys_entries = [(k, v) for k, v in entries if k >= 0xe000]

        if show_header:
            print("=" * 78)
            print("ReFS Schema Table")
            print("=" * 78)
            print(f"  Image:             {image}")
            print(f"  ReFS version:      {vmaj}.{vmin}")
            print(f"  Cluster size:      0x{cs:x}")
            print(f"  Total entries:     {len(entries)}")
            print()
        else:
            print(f"\nReFS Schema Table\n")

        fmt = "  {:<8} {:<32} {:>10} {:>6}"
        print("-" * 78)
        print(f"System table schemas ({len(sys_entries)} entries)")
        print("-" * 78)
        print(fmt.format("TypeID", "Name", "u32[8]", "SelfID"))
        print("  " + "-" * 60)
        for key, vd in sorted(sys_entries):
            name = _TABLE_TYPE_NAMES.get(key, f"Unknown (0x{key:x})")
            props = le32(vd, 32) if len(vd) >= 36 else 0
            level = le32(vd, 36) if len(vd) >= 40 else 0
            print(fmt.format(f"0x{key:x}", name, str(props), str(level)))

        print()
        print("-" * 78)
        print(f"Attribute table schemas ({len(attr_entries)} entries)")
        print("-" * 78)
        print(fmt.format("TypeID", "Name", "u32[8]", "SelfID"))
        print("  " + "-" * 60)
        for key, vd in sorted(attr_entries):
            name = _TABLE_TYPE_NAMES.get(key, f"Unknown (0x{key:x})")
            props = le32(vd, 32) if len(vd) >= 36 else 0
            level = le32(vd, 36) if len(vd) >= 40 else 0
            print(fmt.format(f"0x{key:x}", name, str(props), str(level)))

        if verbose >= 1:
            print(f"\n{'-'*78}\nSchema entry details\n{'-'*78}")
            for key, vd in sorted(entries):
                name = _TABLE_TYPE_NAMES.get(key, f"Unknown (0x{key:x})")
                print(f"\n  0x{key:x} — {name}")
                if len(vd) >= 80:
                    vals = struct.unpack_from("<20I", vd)
                    print(f"    descriptor_size:     0x{vals[0]:x} ({vals[0]})")
                    print(f"    key_desc_size:       0x{vals[1]:x} ({vals[1]})")
                    # C8: u32[7] = key-comparison-rules SELECTOR (a table index, not an offset/bitfield —
                    # errata E50); u32[9] = self schema id (u32[10] is a duplicate that coincides on disk).
                    print(f"    key_rules_selector:  0x{vals[7]:x} ({vals[7]})")
                    print(f"    property_count:      {vals[8]}")
                    print(f"    self_schema_id:      0x{vals[9]:x}")
                    print(f"    self_schema_id(dup): 0x{vals[10]:x}")

        if verbose >= 2:
            print(f"\n{'-'*78}\nRaw schema values\n{'-'*78}")
            for key, vd in sorted(entries):
                name = _TABLE_TYPE_NAMES.get(key, f"Unknown (0x{key:x})")
                print(f"\n  0x{key:x} — {name} ({len(vd)} bytes)")
                if len(vd) >= 80:
                    vals = struct.unpack_from("<20I", vd)
                    print(f"    u32[0..9]:  {' '.join(f'0x{v:x}' for v in vals[:10])}")
                    print(f"    u32[10..19]: {' '.join(f'0x{v:x}' for v in vals[10:])}")
                for i in range(0, len(vd), 16):
                    chunk = vd[i:i+16]
                    print(f"    {i:08x}  {_hexbytes(chunk)}")

        if args["verify"]:
            print(f"\n{'='*78}\nVerification\n{'='*78}")
            ok_cnt = total = 0
            total += 1
            if len(entries) > 0: print(f"  [OK] {len(entries)} entries"); ok_cnt += 1
            else: print("  [FAIL] empty")
            for tid in sorted([0xe030, 0xe040, 0xe060, 0xe0c0]):
                total += 1
                if any(k == tid for k, _ in entries):
                    print(f"  [OK] System type 0x{tid:x} ({_TABLE_TYPE_NAMES.get(tid,'')})"); ok_cnt += 1
                else:
                    print(f"  [WARN] Missing 0x{tid:x}")
            for tid in sorted([0x110, 0x150, 0x200]):
                total += 1
                if any(k == tid for k, _ in entries):
                    print(f"  [OK] Attribute type 0x{tid:x} ({_TABLE_TYPE_NAMES.get(tid,'')})"); ok_cnt += 1
                else:
                    print(f"  [WARN] Missing 0x{tid:x}")
            total += 1
            # C8: check the canonical self-schema-id field u32[9] (byte 0x24), not u32[10]; they coincide
            # on all corpus rows (173/173), so this is behavior-preserving but points at the right field.
            mismatches = sum(1 for k, vd in entries if len(vd) >= 40 and le32(vd, 36) != k)
            if mismatches == 0: print("  [OK] All self_schema_id fields match keys"); ok_cnt += 1
            else: print(f"  [WARN] {mismatches} self_schema_id mismatches")
            total += 1
            if all(len(vd) == 80 for _, vd in entries): print("  [OK] All values 80 bytes"); ok_cnt += 1
            else: print(f"  [INFO] Sizes: {set(len(vd) for _, vd in entries)}")
            print(f"\n  Result: {ok_cnt}/{total} checks passed")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  UPCASE — Unicode upcase table reader
# ═══════════════════════════════════════════════════════════════════════



def cmd_upcase(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify", "-H"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    show_header = args["H"] or verbose >= 1

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        if 0x07 not in obj_map:
            die("OID 0x07 (Upcase Table) not found")

        table_name = ""; total_entries = 0; data_rows = []
        for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x07]):
            if len(kd) < 4: continue
            key = le32(kd, 0)
            if key == 0: table_name = vd.decode("utf-8", errors="replace").rstrip("\x00")
            elif key == 1: total_entries = le32(vd, 0) if len(vd) >= 4 else 0
            else: data_rows.append((key, bytes(vd)))

        has_dup = 0x08 in obj_map

        raw = b""
        for _, vd in sorted(data_rows, key=lambda x: x[0]):
            raw += vd
        if len(raw) % 2: raw = raw[:-1]
        n = len(raw) // 2
        upcase = list(struct.unpack(f"<{n}H", raw))
        n_diffs = sum(1 for cp, uc in enumerate(upcase) if cp != uc)
        total_data_bytes = sum(len(vd) for _, vd in data_rows)
        n_data = len(data_rows)

        total_leaf_rows = n_data + 2
        # Row payload size is cluster-size-dependent (341 B on 4K pages, 5461 B on 64K), so read the
        # ACTUAL sizes from the data rows rather than hardcoding 341 (which printed a nonsense
        # last_row_size of 122888 on 64K volumes — bigger than a cluster).
        _row_sizes = [len(vd) for _, vd in sorted(data_rows, key=lambda x: x[0])]
        last_row_size = _row_sizes[-1] if _row_sizes else 0
        common_row_size = _row_sizes[0] if len(_row_sizes) > 1 else last_row_size

        if show_header:
            print("=" * 78)
            print("ReFS Upcase Table")
            print("=" * 78)
            print(f"  Image:             {image}")
            print(f"  ReFS version:      {vmaj}.{vmin}")
            print(f"  Upcase OID:        0x7")
            if has_dup: print(f"  Duplicate (0x08):  present")
            print()
        else:
            print("\nReFS Upcase Table\n")

        print("-" * 78)
        print("Upcase Table Summary")
        print("-" * 78)
        print(f"  Table name:              \"{table_name}\"")
        print(f"  Declared total entries:  {total_entries}")
        print(f"  Data rows:               {n_data}")
        print(f"  Total leaf rows:         {total_leaf_rows}")
        print(f"  Total data bytes:        {total_data_bytes} ({total_data_bytes // 1024} KiB)")
        print(f"  Row value sizes:         {n_data - 1} × {common_row_size} bytes + 1 × {last_row_size} bytes")
        print(f"  Actual mapped entries:   {n}")
        if n > 0: print(f"  Coverage:                U+0000 to U+{n-1:04X}")
        print(f"  Non-identity mappings:   {n_diffs}")
        print(f"  Identity mappings:       {n - n_diffs}")
        print()

        if verbose >= 1:
            print("-" * 78)
            print("Sample Case Mappings")
            print("-" * 78)
            samples = [
                (0x61, "Latin Small A → A"), (0x7A, "Latin Small Z → Z"),
                (0xE0, "A with Grave"), (0xE9, "E with Acute"),
                (0xFC, "U with Diaeresis"), (0x0430, "Cyrillic A"),
                (0x03B1, "Greek Alpha"), (0xFF41, "Fullwidth A"),
            ]
            for cp, desc in samples:
                if cp < len(upcase):
                    uc = upcase[cp]
                    ch_from = chr(cp) if cp < 0xD800 or cp > 0xDFFF else "?"
                    ch_to = chr(uc) if uc < 0xD800 or uc > 0xDFFF else "?"
                    diff = " (CHANGED)" if cp != uc else ""
                    print(f"  U+{cp:04X} ({ch_from:>2}) → U+{uc:04X} ({ch_to:>2})  {desc}{diff}")
            print()
            print("-" * 78)
            print("Coverage by Unicode Block")
            print("-" * 78)
            blocks = [
                (0x0000, 0x007F, "Basic Latin"), (0x0080, 0x00FF, "Latin-1 Supplement"),
                (0x0100, 0x017F, "Latin Extended-A"), (0x0180, 0x024F, "Latin Extended-B"),
                (0x0370, 0x03FF, "Greek and Coptic"), (0x0400, 0x04FF, "Cyrillic"),
                (0x1E00, 0x1EFF, "Latin Extended Additional"), (0x1F00, 0x1FFF, "Greek Extended"),
                (0xFF00, 0xFFEF, "Halfwidth and Fullwidth Forms"),
            ]
            for bstart, bend, bname in blocks:
                nd = sum(1 for cp in range(bstart, min(bend+1, len(upcase))) if upcase[cp] != cp)
                print(f"  U+{bstart:04X}-U+{bend:04X}  {bname:<40}  {nd:>5} diffs")

        if verbose >= 2:
            print(f"\n{'-'*78}\nAll Non-Identity Mappings\n{'-'*78}")
            cnt = 0
            for cp, uc in enumerate(upcase):
                if cp != uc:
                    ch_from = chr(cp) if 32 <= cp < 0xD800 else ""
                    ch_to = chr(uc) if 32 <= uc < 0xD800 else ""
                    print(f"  U+{cp:04X} {ch_from:>2} → U+{uc:04X} {ch_to:>2}")
                    cnt += 1
            print(f"\n  Total: {cnt} non-identity mappings")

        if args["verify"]:
            print(f"\n{'='*78}\nVerification\n{'='*78}")
            ok_cnt = total = 0
            total += 1
            if n_data > 0: print(f"  [OK] {n_data} data rows"); ok_cnt += 1
            else: print("  [FAIL] No data rows")
            total += 1
            if total_entries > 0 and n == total_entries:
                print(f"  [OK] Entries match declared ({total_entries})"); ok_cnt += 1
            else: print(f"  [WARN] Mapped {n}, declared {total_entries}")
            total += 1
            if len(upcase) > 0x7A and upcase[0x61] == 0x41 and upcase[0x7A] == 0x5A:
                print("  [OK] ASCII case mapping: a→A, z→Z"); ok_cnt += 1
            else: print("  [FAIL] ASCII mapping wrong")
            total += 1
            digits_ok = all(upcase[cp] == cp for cp in list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) if cp < len(upcase))
            if digits_ok: print("  [OK] Identity for digits+uppercase"); ok_cnt += 1
            else: print("  [FAIL] Non-identity in digits/uppercase")
            total += 1
            if has_dup: print("  [OK] Duplicate (OID 0x08) found"); ok_cnt += 1
            else: print("  [WARN] No duplicate (OID 0x08)")
            total += 1
            if table_name == "Upcase Table": print(f"  [OK] Name = \"{table_name}\""); ok_cnt += 1
            elif table_name: print(f"  [INFO] Name = \"{table_name}\""); ok_cnt += 1
            else: print("  [WARN] No name")
            print(f"\n  Result: {ok_cnt}/{total} checks passed")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
    #  OID30 — OID 0x30 session activity analysis
# ═══════════════════════════════════════════════════════════════════════

_OID30_SUB_LABELS = {
    0x00: "Session summary", 0x01: "IO counters (detailed)",
    0x05: "Category A", 0x06: "Category B", 0x07: "Category C",
    0x14: "Category D (v3.14+)", 0x15: "Category E (v3.14+)",
    0x23: "Category F (v3.10)", 0x25: "Category G (v3.10)", 0x27: "Category H (v3.10)",
    }




def cmd_oid30(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v"])
    verbose = args["v"]

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        if 0x30 not in obj_map:
            print(f"\n{'='*78}")
            print(f"Image: {os.path.basename(image)}  (ReFS {vmaj}.{vmin}, {len(obj_map)} objects)")
            print(f"{'='*78}")
            print("  OID 0x30: NOT PRESENT")
            return 0

        oid30_vlcns = obj_map[0x30]
        oid30_vlcn = oid30_vlcns[0] if oid30_vlcns else 0
        try:
            oid30_plcn = tr.tr(oid30_vlcn) if tr else oid30_vlcn
        except Exception:
            oid30_plcn = 0

        decoded_rows = []
        for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x30]):
            r = {}
            if len(kd) >= 16:
                r["timestamp_raw"] = le64(kd, 0)
                r["timestamp_str"] = _filetime_to_str(r["timestamp_raw"])
                r["sub_id"] = le64(kd, 8)
            elif len(kd) >= 8:
                r["timestamp_raw"] = le64(kd, 0)
                r["timestamp_str"] = _filetime_to_str(r["timestamp_raw"])
                r["sub_id"] = 0
            else:
                continue
            r["value_size"] = len(vd)
            r["sub_id_label"] = _OID30_SUB_LABELS.get(r["sub_id"], f"Unknown (0x{r['sub_id']:x})")
            if len(vd) >= 96:
                r["fields_u64"] = [le64(vd, 16 + i*8) for i in range(10) if 16 + i*8 + 8 <= len(vd)]
                r["record_type"] = "extended"
            elif len(vd) >= 44:
                r["fields_u64"] = [le64(vd, 16 + i*8) for i in range((len(vd) - 16) // 8) if 16 + i*8 + 8 <= len(vd)]
                remainder = (len(vd) - 16) % 8
                if remainder == 4: r["trailing_u32"] = le32(vd, len(vd) - 4)
                r["record_type"] = "standard"
            else:
                r["record_type"] = "short"
            decoded_rows.append(r)

        sessions = {}
        for r in decoded_rows:
            ts = r.get("timestamp_raw", 0)
            if ts not in sessions: sessions[ts] = {"str": r["timestamp_str"], "sub_ids": []}
            sessions[ts]["sub_ids"].append(r.get("sub_id", -1))

        print(f"\n{'='*78}")
        print(f"Image: {os.path.basename(image)}  (ReFS {vmaj}.{vmin}, {len(obj_map)} objects)")
        print(f"{'='*78}")
        print(f"  OID 0x30: PRESENT at VLCN 0x{oid30_vlcn:x} / PLCN 0x{oid30_plcn:x}")
        print(f"  Total rows: {len(decoded_rows)}")
        print(f"  Sessions: {len(sessions)}")

        for ts, info in sorted(sessions.items()):
            sids = sorted(info["sub_ids"])
            print(f"\n  Session: {info['str']}")
            print(f"    Sub-IDs: {', '.join(f'0x{s:x}' for s in sids)}")

        if verbose:
            print(f"\n  {'─'*74}\n  Detailed rows:")
            for r in sorted(decoded_rows, key=lambda x: (x.get("timestamp_raw", 0), x.get("sub_id", 0))):
                sid = r.get("sub_id", 0)
                print(f"\n    Sub-ID 0x{sid:x} ({r['sub_id_label']}) — {r['value_size']} bytes ({r['record_type']})")
                for i, fv in enumerate(r.get("fields_u64", [])):
                    print(f"      field[{i}]: {fv:>12} (0x{fv:x})")
                if "trailing_u32" in r:
                    print(f"      trailing_u32: {r['trailing_u32']} (0x{r['trailing_u32']:x})")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  CHKP — Checkpoint analysis with container translation
    #  Source: refs_chkp.py (full bootstrap chain, root table, flags)
# ═══════════════════════════════════════════════════════════════════════



def cmd_chkp(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify", "--raw"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    verify = args["verify"]

    ps = _find_boot_offset(image, partition_start)
    validate_image(image)
    img_size = os.path.getsize(image)

    with open(image, "rb") as f:
        cs, vmaj, vmin, chk_algo, bpc = _forefst_parse_vbr(f, ps)
        cpc_vbr = bpc // cs
        chkp_lcns = _forefst_parse_supb(f, ps, cs)

        best_raw = None; best_vc = -1; best_off = 0
        for lcn in chkp_lcns:
            off = ps + lcn * cs
            try:
                raw = _read_at(f, off, 4 * cs)
                if raw[:4] != b"CHKP": continue
                vc = le64(raw, 0x10)
                if vc > best_vc:
                    best_raw = raw; best_vc = vc; best_off = off
            except (OSError, SystemExit):
                continue
        if best_raw is None:
            die("no valid CHKP found")

        raw = best_raw
        chkp_sha = hashlib.sha256(raw).hexdigest()

        ver_echo_major = le16(raw, 0x50); ver_echo_minor = le16(raw, 0x52)
        ver_major = le16(raw, 0x54); ver_minor = le16(raw, 0x56)
        tbl_desc_end = le32(raw, 0x58); self_desc_len = le32(raw, 0x5c)
        vclock_body = le64(raw, 0x60); alloc_clock = le64(raw, 0x68)
        oldest_log_off = le32(raw, 0x70); oldest_log_seg = le32(raw, 0x74)
        chkp_flags = le32(raw, 0x78)
        reserved_7c = le32(raw, 0x7C); reserved_80 = le32(raw, 0x80); reserved_84 = le32(raw, 0x84)
        data_area_end = le32(raw, 0x88); max_root_cap = le32(raw, 0x8C)
        root_count = le32(raw, 0x90)
        _rc = min(root_count, 32)   # N3/E9: bound the root loops (doc: 13, cap 0x20=32) against a fuzzed count
        if root_count > 32:
            print(f"[{PROG}] WARNING: CHKP root count {root_count} implausible (doc=13, cap=32); scanning 32", file=sys.stderr)
        indirect = bool(chkp_flags & 0x200)

        olb = le32(raw, 0x94) if indirect else 0x94
        roots = []
        for idx in range(_rc):
            oe = olb + idx * 4
            if oe + 4 > len(raw): roots.append([]); continue
            ro = le32(raw, oe)
            if ro == 0 or ro + self_desc_len > len(raw): roots.append([]); continue
            rec = raw[ro:ro + self_desc_len]
            slots = [le64(rec, i * 8) for i in range(4)]
            roots.append([s for s in slots if s not in (0, 0xFFFFFFFFFFFFFFFF)])

        ct_vlcns = _select_ct_root(f, ps, cs, roots)   # CT by Table-ID 0x0B, not index 7 (#337)
        ct_map = {}; cpc_ct = cpc_vbr
        if ct_vlcns:
            for kd, vd in walk_bplus(f, ps, cs, None, ct_vlcns):
                if len(vd) >= 0x98 and len(kd) >= 8:
                    ct_map[le64(kd, 0)] = le64(vd, len(vd) - 16)
                    cpc_ct = le32(vd, 0x18)
        tr = Translator(ct_map, cpc_ct)

        root_data = []
        for idx in range(_rc):
            label, tid, evidence = _CHKP_ROOT_INFO[idx] if idx < len(_CHKP_ROOT_INFO) else (f"Unknown({idx})", 0xFF, "")
            vlcns = roots[idx] if idx < len(roots) else []
            phys = []; sig = b""; note = ""
            if not vlcns:
                note = "NULL"
            elif idx in _CT_ROOT_INDICES:
                phys = list(vlcns); note = "real (bootstrap)"
            else:
                phys = [tr.tr(v) for v in vlcns]
                cid = vlcns[0] >> (cpc_ct.bit_length() if cpc_ct > 0 else 0)
                note = "translated" if cid in ct_map else "real (fallback)"
            if phys:
                abs_off = ps + phys[0] * cs
                if 0 <= abs_off + 0x50 <= img_size:
                    f.seek(abs_off); hdr = f.read(0x50); sig = hdr[:4]
                    # Use the ON-DISK TableId (page+0x48, TableIdLow) for the Name/TID columns, not the
                    # hardcoded index->TableId (which lies on swapped-failover/anomalous volumes, #337).
                    if sig == b"MSB+":
                        ondisk_tid = le64(hdr, 0x48)
                        if ondisk_tid != tid:
                            note = (note + "; " if note else "") + \
                                   f"on-disk TID 0x{ondisk_tid:x} ({_TID_TO_NAME.get(ondisk_tid, '?')}) != slot-expected 0x{tid:x}"
                            label = _TID_TO_NAME.get(ondisk_tid, label)
                            tid = ondisk_tid
                elif 0 <= abs_off + 4 <= img_size:
                    f.seek(abs_off); sig = f.read(4)
            root_data.append((idx, label, tid, evidence, vlcns, phys, sig, note))

        supb_page = _read_at(f, ps + SUPB_LCN * cs, cs) if verbose >= 1 else b""

    def _emit_verify():
        # --verify consistency table — runs on every render path (was unreachable without -v; contract fix 2026-06-20).
        print()
        print("=" * 78)
        print("Verification")
        print("=" * 78)
        ok = 0; total = 0
        total += 1
        if root_count == 13:
            print("  [OK] Root count = 13"); ok += 1
        else:
            print(f"  [WARN] Root count = {root_count}, expected 13")
        total += 1
        ct_sig = root_data[7][6] if len(root_data) > 7 else b""
        if ct_sig == b"MSB+":
            print("  [OK] Container Table signature = MSB+"); ok += 1
        else:
            print(f"  [FAIL] Container Table signature = {ct_sig!r}")
        total += 1
        if ct_map:
            print(f"  [OK] Container map has {len(ct_map)} entries"); ok += 1
        else:
            print("  [FAIL] Container map is empty")
        for _idx, _label, _tid, _ev, _vlcns, _phys, _sig, _note in root_data:
            if _vlcns and _sig:
                total += 1
                if _sig == b"MSB+": ok += 1
                else: print(f"  [WARN] Root {_idx} ({_label}): sig={_sig!r}, expected MSB+")
        total += 1
        if cpc_ct == cpc_vbr:
            print(f"  [OK] CPC from Container Table (0x{cpc_ct:x}) matches VBR (0x{cpc_vbr:x})"); ok += 1
        else:
            print(f"  [WARN] CPC mismatch: Container Table=0x{cpc_ct:x}, VBR=0x{cpc_vbr:x}")
        print(f"\n  Result: {ok}/{total} checks passed")

    if args["raw"]:
        print()
        print(f"ReFS Checkpoint (CHKP) at offset 0x{best_off:X}")
        print(f"SHA-256: {chkp_sha}")
        print()
        for row_off in range(0, min(len(raw), 0x400), 16):
            chunk = raw[row_off:row_off + 16]
            h = " ".join(f"{x:02x}" for x in chunk)
            a = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
            print(f"  {row_off:04x}  {h:<48s}  |{a}|")
        print()
        return 0

    if verbose == 0:
        self_block = le64(raw, 0x20)
        ph_version = le32(raw, 0x04); ph_vol_sig = le32(raw, 0x0C)
        ver_echo_str = f"{ver_echo_major}.{ver_echo_minor}" if (ver_echo_major or ver_echo_minor) else "(not set — upgraded or legacy)"
        offset_list_str = f"0x{le32(raw, 0x94):X} (indirect offset list)" if indirect else "(direct root offsets follow)"
        reserved_zero = reserved_7c == 0 and reserved_80 == 0 and reserved_84 == 0

        print()
        print(f"ReFS Checkpoint (CHKP) at offset 0x{best_off:X}")
        print(f"SHA-256: {chkp_sha}")
        print()

        rows = [
            ["Signature",            "0x00", _hexbytes(raw[0x00:0x04]),     _sig_str(raw[0:4])],
            ["Page hdr version",     "0x04", _hexbytes(raw[0x04:0x08]),     f"0x{ph_version:X}"],
            ["Volume signature",     "0x0C", _hexbytes(raw[0x0C:0x10]),     f"0x{ph_vol_sig:08X}"],
            ["Virtual clock",        "0x10", _hexbytes(raw[0x10:0x18]),     str(best_vc)],
            ["Self-block LCN",       "0x20", _hexbytes(raw[0x20:0x28]),     _hx(self_block)],
            ["Version echo",         "0x50", _hexbytes(raw[0x50:0x54]),     ver_echo_str],
            ["Version",              "0x54", _hexbytes(raw[0x54:0x58]),     f"{ver_major}.{ver_minor}"],
            ["Table desc end",       "0x58", _hexbytes(raw[0x58:0x5C]),     f"0x{tbl_desc_end:X}"],
            ["Ref size (self-desc)", "0x5C", _hexbytes(raw[0x5C:0x60]),     f"0x{self_desc_len:X} ({self_desc_len} bytes)"],
            ["Virtual clock (body)", "0x60", _hexbytes(raw[0x60:0x68]),     str(vclock_body)],
            ["Allocator clock",      "0x68", _hexbytes(raw[0x68:0x70]),     str(alloc_clock)],
            ["Oldest log ref",       "0x70", _hexbytes(raw[0x70:0x78]),     f"offset=0x{oldest_log_off:X}, segment={oldest_log_seg}"],
            ["Flags",                "0x78", _hexbytes(raw[0x78:0x7C]),     f"0x{chkp_flags:08X}"],
            ["Reserved",             "0x7C", _hexbytes(raw[0x7C:0x88]),     "zero" if reserved_zero else "NON-ZERO"],
            ["Data area end",        "0x88", _hexbytes(raw[0x88:0x8C]),     f"0x{data_area_end:X} ({data_area_end} bytes)"],
            ["Max root capacity",    "0x8C", _hexbytes(raw[0x8C:0x90]),     str(max_root_cap)],
            ["Root count",           "0x90", _hexbytes(raw[0x90:0x94]),     str(root_count)],
            ["Offset list pointer",  "0x94", _hexbytes(raw[0x94:0x98]),     offset_list_str],
        ]
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], rows)

        active = [(b, n) for b, n in sorted(_CHKP_FLAG_BITS.items()) if chkp_flags & b]
        if active:
            print(f"  Checkpoint flags (0x{chkp_flags:X}):")
            for bit, name in active:
                print(f"    0x{bit:03X} = {name}")
        else:
            print(f"  Checkpoint flags: none (0x{chkp_flags:X})")
        print()
        print(f"  Container entries: {len(ct_map)}, CPC: {cpc_ct}")
        print()

        fmt = "  {:<3} {:<26} {:>6} {:>12} {:>12} {:>6} {}"
        print(fmt.format("Idx", "Table Name", "TID", "Root LCN", "Physical LCN", "Sig", "Note"))
        print("  " + "-" * 76)
        for idx, label, tid, ev, vlcns, phys, sig, note in root_data:
            print(fmt.format(idx, label, f"0x{tid:02x}",
                             _hx(vlcns[0]) if vlcns else "NULL",
                             _hx(phys[0]) if phys else "n/a",
                             _sig_str(sig) if sig else "n/a", note))
        print()
        if verify: _emit_verify()
        return 0

    # -v / -vv verbose
    print()
    print("=" * 78)
    print("ReFS Checkpoint Analysis with Container-Table Translation")
    print("=" * 78)
    kv = lambda k, v: print(f"  {k:<30} {v}")
    kv("Image", image)
    kv("Image size", f"{img_size} bytes ({img_size / (1024**3):.2f} GiB)")
    kv("CHKP SHA-256", chkp_sha)
    kv("Partition start", _hx(ps))
    kv("Cluster size", f"{_hx(cs)} ({cs} bytes)")
    kv("ReFS version", f"{vmaj}.{vmin}")
    kv("Bytes per container", f"{_hx(bpc)} ({bpc // (1024*1024)} MiB)")
    kv("Clusters per container", f"{_hx(cpc_vbr)} ({cpc_vbr})")
    if verbose >= 2:
        _gp = gpt_partition_detail(image)
        if _gp:
            kv("GPT partition", f"#{_gp['index']} '{_gp['name']}' LBA {_gp['first_lba']}-{_gp['last_lba']} ({_human_size(_gp['size_bytes'])})")

    print()
    print("SUPB")
    print("-" * 78)
    kv("Volume GUID", supb_page[0x50:0x60].hex() if len(supb_page) >= 0x60 else "n/a")
    kv("Superblock version", str(le64(supb_page, 0x68)) if len(supb_page) >= 0x70 else "n/a")
    kv("Checkpoint references", str(len(chkp_lcns)))

    ver_echo_str = f"{ver_echo_major}.{ver_echo_minor}" if (ver_echo_major or ver_echo_minor) else "(not set)"
    print()
    print("CHKP (latest)")
    print("-" * 78)
    kv("CHKP offset", _hx(best_off))
    kv("Version echo", ver_echo_str)
    kv("Version", f"{ver_major}.{ver_minor}")
    kv("Virtual clock", str(best_vc))
    kv("Allocator clock", str(alloc_clock))
    kv("Flags", f"0x{chkp_flags:X}")
    kv("Indirect root list", str(indirect))
    kv("Global root count", str(root_count))
    kv("Root reference size", f"{_hx(self_desc_len)} ({self_desc_len} bytes)")

    active = [(b, n) for b, n in sorted(_CHKP_FLAG_BITS.items()) if chkp_flags & b]
    if active:
        print()
        print("  Flag bits:")
        for bit, name in active:
            print(f"    0x{bit:03X} = {name}")

    print()
    print("Container Table")
    print("-" * 78)
    if len(root_data) > 7:
        rd7 = root_data[7]
        kv("Source root", f"index {rd7[0]} ({rd7[1]})")
        kv("Root LCN tuple", ", ".join(_hx(x) for x in rd7[4]))
    kv("Entries", str(len(ct_map)))
    kv("CPC (from rows)", f"{_hx(cpc_ct)} ({cpc_ct})")
    kv("CPC shift", str(cpc_ct.bit_length() if cpc_ct > 0 else 0))

    if verbose >= 2 and ct_map:
        print()
        print("  Container map:")
        for k in sorted(ct_map.keys()):
            print(f"    container {k:#5x} -> physical start {ct_map[k]:#10x}")

    print()
    print("=" * 78)
    print("13 Global Root Tables")
    print("=" * 78)

    fmt = "  {:<3} {:<26} {:>8} {:>12} {:>12} {:>6} {}"
    print(fmt.format("Idx", "Table Name", "TableID", "Root LCN", "Physical LCN", "Sig", "Translation"))
    print("  " + "-" * 76)
    for idx, label, tid, ev, vlcns, phys, sig, note in root_data:
        print(fmt.format(idx, label, f"0x{tid:02x}",
                         _hx(vlcns[0]) if vlcns else "NULL",
                         _hx(phys[0]) if phys else "n/a",
                         _sig_str(sig) if sig else "n/a", note))

    if verbose >= 2:
        print()
        print("Detailed root records")
        print("-" * 78)
        for idx, label, tid, ev, vlcns, phys, sig, note in root_data:
            print(f"\n  [{idx}] {label}")
            if vlcns:
                print(f"    Virtual LCN tuple:  {', '.join(_hx(x) for x in vlcns)}")
                if phys:
                    print(f"    Physical LCN tuple: {', '.join(_hx(x) for x in phys)}")
                    print(f"    Absolute offset:    {_hx(ps + phys[0] * cs)}")
                print(f"    Signature:          {_sig_str(sig) if sig else 'n/a'}")
                print(f"    Translation:        {note}")
                print(f"    Evidence:           {ev}")
            else:
                print("    (null/empty)")

    if verify:
        _emit_verify()

    return 0


# ═══════════════════════════════════════════════════════════════════════
#  OBJECTS — Object ID Table reader
#  Source: refs_object_table.py (OID → LCN mapping with signatures)
# ═══════════════════════════════════════════════════════════════════════

def cmd_objects(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    verify = args["verify"]

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        ot_vlcns = roots[0] if roots and roots[0] else []
        img_size = os.path.getsize(image)

        entries = []
        for kd, vd in walk_bplus(f, ps, cs, tr, ot_vlcns):
            oid = le64(kd, 8) if len(kd) >= 16 else (le64(kd, 0) if len(kd) >= 8 else 0)
            vlcns = []
            if len(vd) >= 64:
                for j in range(4):
                    v = le64(vd, 0x20 + j * 8)
                    if v not in (0, 0xFFFFFFFFFFFFFFFF): vlcns.append(v)
            name = _KNOWN_OIDS.get(oid, "")
            if not name and oid >= 0x700: name = f"Directory/File (0x{oid:x})"
            extra = len(vd) - 80 if len(vd) > 80 else 0
            entries.append({"oid": oid, "vlcns": vlcns, "name": name, "extra": extra,
                            "key_raw": kd, "value_raw": vd, "phys": [], "sig": b""})

        for e in entries:
            if e["vlcns"]:
                e["phys"] = [tr.tr(v) for v in e["vlcns"]]
                abs_off = ps + e["phys"][0] * cs
                if 0 <= abs_off + 4 <= img_size:
                    f.seek(abs_off); e["sig"] = f.read(4)

        entries.sort(key=lambda e: e["oid"])

        if verbose >= 1:
            print("=" * 78)
            print("ReFS Object ID Table")
            print("=" * 78)
            print(f"  {'Image:':<18}{image}")
            print(f"  {'Partition start:':<18}{_hx(ps)}")
            print(f"  {'Cluster size:':<18}{_hx(cs)}")
            print(f"  {'ReFS version:':<18}{vmaj}.{vmin}")
            ot_phys = [tr.tr(v) for v in ot_vlcns] if ot_vlcns else []
            print(f"  {'CPC:':<18}{_hx(tr.cpc)} (shift={tr.cpc.bit_length() if tr.cpc > 0 else 0})")
            print(f"  {'Container entries:':<18}{len(tr.map)}")
            print(f"  {'OID Table root:':<18}[{', '.join(_hx(x) for x in ot_vlcns)}]")
            print(f"  {'OID Table phys:':<18}[{', '.join(_hx(x) for x in ot_phys)}]")
            print()
        else:
            print()
            print("ReFS Object ID Table")
            print()

        print(f"Total objects: {len(entries)}")
        print()

        if verbose >= 1:
            fmt = "  {:<8} {:<28} {:>12} {:>12} {:>6} {:>5}"
            print(fmt.format("OID", "Name", "Root LCN", "Physical LCN", "Sig", "Extra"))
            print("  " + "-" * 76)
        else:
            fmt = "  {:<8} {:<28} {:>12}"
            print(fmt.format("OID", "Name", "Root LCN"))
            print("  " + "-" * 50)

        for e in entries:
            vlcn_str = _hx(e["vlcns"][0]) if e["vlcns"] else "n/a"
            if verbose >= 1:
                plcn_str = _hx(e["phys"][0]) if e["phys"] else "n/a"
                sig_s = _sig_str(e["sig"]) if e["sig"] else "n/a"
                extra_s = f"+{e['extra']}" if e["extra"] > 0 else ""
                print(fmt.format(f"0x{e['oid']:x}", e["name"], vlcn_str, plcn_str, sig_s, extra_s))
            else:
                print(fmt.format(f"0x{e['oid']:x}", e["name"], vlcn_str))

        if verbose >= 2:
            print()
            print("Detailed object entries")
            print("-" * 78)
            for e in entries:
                print(f"\n  OID 0x{e['oid']:x} — {e['name']}")
                print(f"    Key (raw):  {e['key_raw'].hex()}")
                if e["vlcns"]:
                    print(f"    VLCN tuple: [{', '.join(_hx(x) for x in e['vlcns'])}]")
                    print(f"    PLCN tuple: [{', '.join(_hx(x) for x in e['phys'])}]")
                    print(f"    Absolute:   {_hx(ps + e['phys'][0] * cs)}")
                    print(f"    Signature:  {_sig_str(e['sig'])}")
                print(f"    Value size: {len(e['value_raw'])} bytes (standard=80, extra={e['extra']})")
                if len(e["value_raw"]) >= 80:
                    info = struct.unpack_from("<8I", e["value_raw"])
                    print(f"    u32[0..7]:  {' '.join(f'0x{x:x}' for x in info)}")
                if e["extra"] > 0:
                    print(f"    Extra bytes ({e['extra']}):")
                    print(_hexdump_lines(e["value_raw"][80:], base=80))

        if verify:
            print()
            print("=" * 78)
            print("Verification")
            print("=" * 78)
            ok = 0; total = 0
            for e in entries:
                if e["vlcns"]:
                    total += 1
                    if e["sig"] == b"MSB+": ok += 1
                    else: print(f"  [WARN] OID 0x{e['oid']:x} ({e['name']}): sig={e['sig']!r}, expected MSB+")
            for oid in (0x600, 0x520, 0x500, 0x7, 0x9):
                total += 1
                found = any(e["oid"] == oid for e in entries)
                nm = _KNOWN_OIDS.get(oid, "")
                if found:
                    print(f"  [OK] Found expected OID 0x{oid:x} ({nm})"); ok += 1
                else:
                    print(f"  [WARN] Missing expected OID 0x{oid:x} ({nm})")
            print(f"\n  Result: {ok}/{total} checks passed")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  PARENTCHILD — Parent-Child relationship table
    #  Source: refs_parentchild.py (directory hierarchy from root #4)
# ═══════════════════════════════════════════════════════════════════════

_PC_OID_NAMES = {
    0x0007: "Upcase Table", 0x0008: "Upcase Table (dup)",
    0x0009: "Logfile Info Table", 0x000A: "Logfile Info (dup)",
    0x000D: "Trash Table", 0x0030: "Session Activity Table",
    0x0500: "Volume Information", 0x0501: "Volume Info (dup)",
    0x0520: "FS Metadata", 0x0530: "Security Descriptors",
    0x0540: "Reparse Index", 0x0541: "Reparse Index (dup)",
    0x0600: "Root Directory",
    }


def _pc_oid_name(oid):
    if oid in _PC_OID_NAMES: return _PC_OID_NAMES[oid]
    if 0x700 <= oid <= 0x7FF: return f"Dir/File (0x{oid:x})"
    return f"Object 0x{oid:x}"




def cmd_parentchild(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    verify = args["verify"]

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        pc_vlcns = roots[4] if len(roots) > 4 and roots[4] else []
        if not pc_vlcns:
            die("Parent-Child Table root not found (root #4)")

        pc_plcns = [tr.tr(v) for v in pc_vlcns]
        f.seek(ps + pc_plcns[0] * cs); page_sig = f.read(4)

        entries = []
        for kd, vd in walk_bplus(f, ps, cs, tr, pc_vlcns):
            parent = le64(kd, 8) if len(kd) >= 16 else 0
            child = le64(kd, 24) if len(kd) >= 32 else 0
            entries.append({"parent_oid": parent, "child_oid": child,
                            "key_raw": kd, "val_raw": vd})

        children_of = {}; parents_of = {}
        all_parents = set(); all_children = set()
        for e in entries:
            children_of.setdefault(e["parent_oid"], []).append(e["child_oid"])
            parents_of.setdefault(e["child_oid"], []).append(e["parent_oid"])
            all_parents.add(e["parent_oid"]); all_children.add(e["child_oid"])
        root_nodes = all_parents - all_children
        all_oids = all_parents | all_children

        if verbose >= 1:
            print("=" * 78)
            print("ReFS Parent-Child Table")
            print("=" * 78)
            print(f"  {'Image:':<18}{image}")
            print(f"  {'Partition start:':<18}{_hx(ps)}")
            print(f"  {'Cluster size:':<18}{_hx(cs)}")
            print(f"  {'ReFS version:':<18}{vmaj}.{vmin}")
            print(f"  {'CPC:':<18}{_hx(tr.cpc)} (shift={tr.cpc.bit_length() if tr.cpc > 0 else 0})")
            print(f"  {'PC Table root:':<18}[{', '.join(_hx(x) for x in pc_vlcns)}]")
            print(f"  {'PC Table phys:':<18}[{', '.join(_hx(x) for x in pc_plcns)}]")
            print(f"  {'Page signature:':<18}{_sig_str(page_sig)}")
            print()
        else:
            print()
            print("ReFS Parent-Child Table")
            print()

        print("-" * 78)
        print("Parent-Child Relationships")
        print("-" * 78)
        print(f"  {'Total entries:':<20}{len(entries)}")
        print(f"  {'Unique parents:':<20}{len(all_parents)}")
        print(f"  {'Unique children:':<20}{len(all_children)}")
        print(f"  {'Unique OIDs:':<20}{len(all_oids)}")
        print(f"  {'Tree roots:':<20}{', '.join(hex(x) for x in sorted(root_nodes))}")
        print()

        fmt = "  {:<14} → {:<14}   {:<25} → {}"
        print(fmt.format("Parent", "Child", "Parent Name", "Child Name"))
        print("  " + "-" * 72)
        for e in entries:
            print(fmt.format(hex(e["parent_oid"]), hex(e["child_oid"]),
                             _pc_oid_name(e["parent_oid"]), _pc_oid_name(e["child_oid"])))

        if verbose >= 1:
            print()
            print("-" * 78)
            print("Directory Tree")
            print("-" * 78)

            def _print_tree(oid, depth=0):
                prefix = "  " + "│   " * depth
                name = _pc_oid_name(oid)
                nc = len(children_of.get(oid, []))
                extra = f" ({nc} children)" if nc > 0 else ""
                if depth == 0:
                    print(f"  {_hx(oid)} {name}{extra}")
                else:
                    print(f"{prefix}├── {_hx(oid)} {name}{extra}")
                for child in sorted(children_of.get(oid, [])):
                    _print_tree(child, depth + 1)

            for root in sorted(root_nodes):
                _print_tree(root)
                print()

            print("-" * 78)
            print("Per-Parent Summary")
            print("-" * 78)
            for parent in sorted(children_of.keys()):
                kids = sorted(children_of[parent])
                print(f"  {_hx(parent):>10} {_pc_oid_name(parent):<25} → {len(kids)} children: [{', '.join(_hx(c) for c in kids)}]")

            # FS Metadata directory children
            if 0x520 in obj_map:
                _FS_FLAGS = {0x100: "DASD", 0x200: "Security", 0x400: "Reparse"}
                print()
                print("-" * 78)
                print("FS Metadata Children (OID 0x520 B+-tree entries)")
                print("-" * 78)
                try:
                    _fm_rows = list(walk_bplus(f, ps, cs, tr, obj_map[0x520]))
                    _fm_names = []
                    for kd, vd in _fm_rows:
                        if len(kd) >= 4 and le16(kd, 0) == 0x30:
                            try: nm = kd[4:].decode("utf-16-le").rstrip("\x00")
                            except Exception: nm = "(decode error)"
                            fl = le32(vd, 0x80) if len(vd) >= 0x84 else 0
                            tag = _FS_FLAGS.get(fl)
                            label = f"  {nm}"
                            if tag: label += f"  [degenerate: {tag}, flags=0x{fl:x}]"
                            elif nm == "Change Journal":
                                sc = le64(vd, 0x20) if len(vd) >= 0x28 else 0
                                label += f"  [USN Journal, streams={sc}]"
                            _fm_names.append(label)
                    print(f"  Total rows: {len(_fm_rows)}  (filename entries: {len(_fm_names)})")
                    for n in _fm_names: print(n)
                    if not _fm_names: print("  (no children)")
                except Exception as ex:
                    print(f"  Error walking OID 0x520: {ex}")

        if verbose >= 2:
            print()
            print("-" * 78)
            print("Raw Row Data")
            print("-" * 78)
            for i, e in enumerate(entries):
                print(f"  Row {i}:")
                print(f"    Key (hex):   {e['key_raw'].hex()}")
                print(f"    Value (hex): {e['val_raw'].hex()}")
                if len(e["key_raw"]) >= 32:
                    k = struct.unpack_from("<4Q", e["key_raw"])
                    print(f"    Key parsed:  [{k[0]}, {_hx(k[1])}, {k[2]}, {_hx(k[3])}]")
                if len(e["val_raw"]) >= 32:
                    v = struct.unpack_from("<4Q", e["val_raw"])
                    print(f"    Val parsed:  [{v[0]}, {_hx(v[1])}, {v[2]}, {_hx(v[3])}]")
                print(f"    Key == Value: {e['key_raw'] == e['val_raw']}")

        if verify:
            print()
            print("=" * 78)
            print("Verification")
            print("=" * 78)
            ok = 0; total = 0

            total += 1
            if page_sig == b"MSB+":
                print("  [OK] Parent-Child root page signature is MSB+"); ok += 1
            else:
                print(f"  [FAIL] Page signature: {page_sig!r}")

            total += 1
            if entries:
                print(f"  [OK] Parent-Child Table has {len(entries)} entries"); ok += 1
            else:
                print("  [FAIL] Parent-Child Table is empty")

            total += 1
            if all(e["key_raw"] == e["val_raw"] for e in entries):
                print(f"  [OK] Key equals Value for all {len(entries)} entries"); ok += 1
            else:
                n_diff = sum(1 for e in entries if e["key_raw"] != e["val_raw"])
                print(f"  [WARN] Key != Value for {n_diff} entries")

            total += 1
            struct_ok = True
            for e in entries:
                if len(e["key_raw"]) >= 32:
                    k0 = le64(e["key_raw"], 0); k2 = le64(e["key_raw"], 16)
                    if k0 != 0 or k2 != 0: struct_ok = False; break
            if struct_ok:
                print(f"  [OK] All keys have structure [0, parent, 0, child]"); ok += 1
            else:
                print("  [WARN] Some keys have non-zero padding fields")

            total += 1
            if 0x600 in root_nodes:
                print(f"  [OK] Root Directory (0x600) is a tree root with {len(children_of.get(0x600, []))} children"); ok += 1
            elif 0x600 in all_oids:
                print("  [WARN] Root Directory (0x600) exists but is not a tree root")
            else:
                print("  [WARN] Root Directory (0x600) not found in table")

            total += 1
            child_counts = {}
            for e in entries:
                child_counts[e["child_oid"]] = child_counts.get(e["child_oid"], 0) + 1
            multi = {c: n for c, n in child_counts.items() if n > 1}
            if not multi:
                print("  [OK] No multi-parent entries (tree structure)"); ok += 1
            else:
                print(f"  [INFO] {len(multi)} OIDs have multiple parents"); ok += 1

            print(f"\n  Result: {ok}/{total} checks passed")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  CONTAINERS — Container table and allocator analysis
#  Source: refs_container.py (container map, allocator metrics)
# ═══════════════════════════════════════════════════════════════════════



def cmd_containers(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v"])
    verbose = args["v"]

    ps = _find_boot_offset(image, partition_start)
    validate_image(image)

    with open(image, "rb") as f:
        cs, vmaj, vmin, chk_algo, bpc = _forefst_parse_vbr(f, ps)
        cpc = bpc // cs
        chkp_lcns = _forefst_parse_supb(f, ps, cs)

        best_vc = 0; best_roots = None
        for cl in chkp_lcns:
            try:
                vc, fl, rts = _forefst_parse_chkp(f, ps, cs, cl)
                if vc >= best_vc: best_vc = vc; best_roots = rts
            except Exception:
                pass
        if not best_roots:
            die("no valid checkpoint found")

        ct_vlcns = _select_ct_root(f, ps, cs, best_roots)   # CT by Table-ID 0x0B, not index 7 (#337)
        ct_page = b""
        for l in ct_vlcns:
            f.seek(ps + l * cs); ct_page += f.read(cs)

        ct_full = {}
        for kd, vd in walk_bplus(f, ps, cs, None, ct_vlcns):
            if len(vd) >= 0x98 and len(kd) >= 8:
                key = le64(kd, 0)
                phys = le64(vd, len(vd) - 16)
                ct_flags = le32(vd, 0x14) if len(vd) >= 0x18 else 0
                row_cpc = le32(vd, 0x18) if len(vd) >= 0x1C else 0
                free_cl = le64(vd, 0x20) if len(vd) >= 0x28 else 0
                free_med = le64(vd, 0x28) if len(vd) >= 0x30 else 0
                ct_full[key] = (phys, ct_flags, row_cpc, free_cl, free_med, len(vd))

        ct_map = {k: row[0] for k, row in ct_full.items()}
        tr = Translator(ct_map, cpc)
        total_sectors = le64(_read_at(f, ps, 512), 0x18)
        volume_bytes = total_sectors * 512

        alloc_root_map = {1: "Medium Allocator", 2: "Container Allocator", 12: "Small Allocator"}
        allocator_info = {}
        for root_idx, alloc_name in alloc_root_map.items():
            if root_idx >= len(best_roots) or not best_roots[root_idx]:
                allocator_info[alloc_name] = 0; continue
            vlcns = best_roots[root_idx]
            use_tr = None if root_idx in _CT_ROOT_INDICES else tr
            allocator_info[alloc_name] = len(walk_bplus(f, ps, cs, use_tr, vlcns))

        ci_rows = 0
        if len(best_roots) > 10 and best_roots[10]:
            ci_rows = len(walk_bplus(f, ps, cs, tr, best_roots[10]))

        compression = None
        if len(ct_page) >= 0xB0:
            prefix = le32(ct_page, 0xA0)
            if prefix == 0x0F:
                compression = {
                    "format": le16(ct_page, 0xA4),
                    "level": struct.unpack_from("<h", ct_page, 0xA6)[0],
                    "chunk": le32(ct_page, 0xA8),
                }

    total_containers = volume_bytes // bpc if bpc > 0 else 0

    print("=" * 78)
    print("ReFS Container & Allocator Analysis")
    print("=" * 78)
    print(f"  {'Image:':<20}{image}")
    print(f"  {'ReFS version:':<20}{vmaj}.{vmin}")
    print(f"  {'Cluster size:':<20}{_hx(cs)} ({_summary_human_size(cs)})")
    print(f"  {'Container size:':<20}{_hx(bpc)} ({_summary_human_size(bpc)})")
    print(f"  {'Clusters/container:':<20}{cpc}")
    print(f"  {'Checkpoint VC:':<20}{best_vc}")
    print()

    print("-" * 78)
    print("Volume Capacity")
    print("-" * 78)
    print(f"  {'Total volume size:':<20}{_summary_human_size(volume_bytes)}")
    print(f"  {'Total containers:':<20}{total_containers} (theoretical from volume size)")
    print(f"  {'Container Table:':<20}{len(ct_full)} mapped containers")
    print()

    print("-" * 78)
    print("Allocator Tables")
    print("-" * 78)
    for name, rows in allocator_info.items():
        print(f"  {name:<25} {rows} rows")
    print(f"  {'Container Index Table':<25} {ci_rows} rows")
    print()

    if compression:
        print("-" * 78)
        print("Compression Configuration (from Container Table header)")
        print("-" * 78)
        fmt_map = {0: "None", 1: "LZ4", 2: "Zstd", 3: "LZ4QAT"}
        cfmt = compression["format"]
        print(f"  {'Format:':<13}{fmt_map.get(cfmt, f'Unknown({cfmt})')}")
        print(f"  {'Level:':<13}{compression['level']}")
        if compression["chunk"] > 0:
            print(f"  {'Chunk size:':<13}{_hx(compression['chunk'])} ({_summary_human_size(compression['chunk'])})")
        else:
            print(f"  {'Chunk size:':<13}0 (default)")
        print()

    _CT_FLAGS = {0x0001: "META", 0x0040: "DATA", 0x0200: "TIER",
                  0x2000: "FREE", 0x4000: "ALLOC"}

    if verbose and ct_full:
        sentinel = 0xFFFFFFFFFFFFFFFF
        real_free = [r[3] for r in ct_full.values() if r[3] != sentinel]
        total_cap = sum(r[2] for r in ct_full.values())
        print("-" * 78)
        print("Container Table Entries")
        print("-" * 78)
        if real_free:
            total_free = sum(real_free)
            print(f"  Free clusters tracked: {total_free:,} / {total_cap:,} ({total_free*cs/(1024*1024*1024):.2f} GiB free)")
        else:
            print(f"  Total capacity: {total_cap:,} clusters ({total_cap*cs/(1024*1024*1024):.1f} GiB)")
            print(f"  Free cluster tracking: not populated")
        n_meta = sum(1 for r in ct_full.values() if r[1] & 0x0001)
        n_data = sum(1 for r in ct_full.values() if r[1] & 0x0040)
        n_free = sum(1 for r in ct_full.values() if r[1] & 0x2000)
        print(f"  By type: {n_meta} metadata, {n_data} data, {n_free} free/unalloc")
        print()
        print(f"  {'ID':<8} {'Phys LCN':<14} {'Flags':<8} {'Row':>5} {'Type'}")
        print(f"  {'-'*8} {'-'*14} {'-'*8} {'-'*5} {'-'*20}")
        for cid in sorted(ct_full.keys()):
            phys, flags, row_cpc, free_cl, free_med, vlen = ct_full[cid]
            flag_names = [n for b, n in _CT_FLAGS.items() if flags & b]
            fstr = "|".join(flag_names) if flag_names else _hx(flags)
            print(f"  {_hx(cid):<8} {_hx(phys):<14} {_hx(flags):<8} {vlen:>5} {fstr}")

    return 0


# ═══════════════════════════════════════════════════════════════════════
#  Content subcommand shared helpers
# ═══════════════════════════════════════════════════════════════════════

# File-attribute tables now live ONCE in forefst (FILE_ATTR_FLAGS / FILE_ATTR_SIMPLE,
# TitleCase). refsanalysis imports them; _attrs_to_str/_attrs_to_list below are thin
# adapters so existing call sites are unchanged. (Output: UPPERCASE -> TitleCase.)

# $SI+0x24 internal_flags decode (FCB+0x08 bit extraction). NOTE (#342/E43):
# bit0 (0x01) = FCB bit 27 = a delete-disposition/EFS transient state, NOT integrity
# (the integrity-stream marker is file_attrs 0x8000, never reflected here).
_INTERNAL_FLAGS = {
    # C2: 0x04/0x08/0x10 have NO confident semantic (driver builds them from generic FCB bits, no EA
    # logic; disk: 0x08 set on many ordinary files, 0 with EA). Leave them UNLABELLED, matching
    # forefst._INTERNAL_FLAG_LABELS. Only 0x01/0x02/0x20 are confidently named.
    0x01: "DeleteDisposition", 0x02: "Dedup/CoW", 0x20: "RedirectionTrust",
}



def _attrs_to_str(attrs, full=True):
    # adapter over the canonical helper (hex render on no-flags = legacy refsanalysis behaviour)
    return attrs_to_str(attrs, full=full, hex_if_empty=True)


def _attrs_to_list(attrs):
    return [name for bit, name in FILE_ATTR_FLAGS.items() if attrs & bit]


def _iflags_to_list(iflags):
    return [name for bit, name in _INTERNAL_FLAGS.items() if iflags & bit]


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
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0
            create_time = le64(vd, 0x10) if len(vd) >= 0x18 else 0
            modify_time = le64(vd, 0x18) if len(vd) >= 0x20 else 0
            change_time = le64(vd, 0x20) if len(vd) >= 0x28 else 0
            access_time = le64(vd, 0x28) if len(vd) >= 0x30 else 0
            file_attrs = le32(vd, 0x40) if len(vd) >= 0x44 else 0
            file_size = le64(vd, 0x38) if len(vd) >= 0x40 else 0
            file_id = le64(vd, 0x00) if len(vd) >= 8 else 0
            is_dir = bool(file_attrs & 0x10000000)
            resident = False
            # val+0x08 is the child's own OID only for a SUBDIRECTORY; a non-resident FILE has the
            # home-dir backref there (not its own OID -- files have no own OID). Keep child_oid = own
            # OID for dirs (drives recursion); expose 0 for files and keep the backref aside. --oid bug.
            home_oid = 0 if is_dir else child_oid
            if not is_dir:
                child_oid = 0
        else:
            child_oid = 0
            home_oid = 0
            file_id = 0
            create_time = le64(vd, 0x28) if len(vd) >= 0x30 else 0
            modify_time = le64(vd, 0x30) if len(vd) >= 0x38 else 0
            change_time = le64(vd, 0x38) if len(vd) >= 0x40 else 0
            access_time = le64(vd, 0x40) if len(vd) >= 0x48 else 0
            file_attrs = le32(vd, 0x48) if len(vd) >= 0x4C else 0
            file_size = get_resident_file_size(vd)  # C10: real resident size, not 0
            is_dir = False
            resident = True

        ads_list = _parse_ads_from_value(vd) if resident and len(vd) > 0xA8 else []
        entries.append({
            "name": name, "flags": flags, "child_oid": child_oid, "home_oid": home_oid,
            "file_id": file_id,
            "create_time": create_time, "modify_time": modify_time,
            "change_time": change_time, "access_time": access_time,
            "file_attrs": file_attrs, "file_size": file_size,
            "is_dir": is_dir, "resident": resident, "value_len": len(vd),
            "raw_value": vd, "ads": ads_list,
        })
    return entries


def _build_backing_index(f, ps, cs, tr, obj_map):
    """{(owner_dir_oid, file_id): [(size@0x58, file_attrs@0x48), ...]} over every directory's type-0x40
    backing records. A non-resident file's AUTHORITATIVE file_attrs live in this backing (+0x48); the
    type-0x30 pointer's +0x40 attrs OMIT the EA bit (0x40000). One pass (~1s on the largest image)."""
    idx = {}
    for oid, vlcns in obj_map.items():
        try: rows = walk_bplus(f, ps, cs, tr, vlcns)
        except Exception: continue
        for kd, vd in rows:
            if len(kd) >= 0x10 and le16(kd, 0) == 0x40 and len(vd) >= 0x60:
                idx.setdefault((oid, le64(kd, 0x08)), []).append((le64(vd, 0x58), le32(vd, 0x48)))
    return idx


def _backing_file_attrs(idx, home_oid, file_id, size):
    """Authoritative +0x48 file_attrs for a non-resident file, via its HOME dir (val+0x08 backref) and
    file_id. Single candidate wins; the per-dir file_id can collide across hard-links, so size (val+0x58)
    disambiguates (#340). None if no backing found (leaves the pointer attrs untouched)."""
    cands = idx.get((home_oid, file_id))
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0][1]
    for sz, fa in cands:
        if sz == size:
            return fa
    return cands[0][1]


def _apply_backing_ea(results, idx):
    """OR the authoritative EA bit (0x40000) back into non-resident files whose type-0x30 pointer dropped
    it (proven: only the EA bit, plus a rare benign Archive bit, ever differ from the backing). Mirrors
    forefst's walk_directory_tree fix so files/attributes/details agree across both tools."""
    for r in results:
        is_res = r.get("is_resident", r.get("resident", False))
        if r.get("is_dir") or is_res or (r.get("file_attrs", 0) & 0x40000):
            continue
        bfa = _backing_file_attrs(idx, r.get("home_oid", 0), r.get("file_id", 0), r.get("file_size", 0))
        if bfa is not None and (bfa & 0x40000):
            r["file_attrs"] = r.get("file_attrs", 0) | 0x40000
            r["has_ea"] = True


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


def _decode_lx_mode(mode_val):
    """Decode Linux mode_t to human-readable string."""
    file_types = {
        0o140000: "socket", 0o120000: "symlink", 0o100000: "regular",
        0o060000: "block", 0o040000: "directory", 0o020000: "char",
        0o010000: "fifo",
    }
    ft = mode_val & 0o170000
    ftype = file_types.get(ft, f"unknown({oct(ft)})")
    perms = ""
    for shift in (6, 3, 0):
        bits = (mode_val >> shift) & 7
        perms += "r" if bits & 4 else "-"
        perms += "w" if bits & 2 else "-"
        perms += "x" if bits & 1 else "-"
    return f"{ftype} {perms} ({oct(mode_val & 0o7777)})"


def _extract_file_attributes(vd, name):
    """Extract all attributes from a directory entry value (files + attributes)."""
    result = {"name": name, "value_len": len(vd), "is_resident": len(vd) > 84}
    if len(vd) <= 84:
        result["child_oid"] = le64(vd, 0x08) if len(vd) >= 0x10 else 0
        result["file_id"] = le64(vd, 0x00) if len(vd) >= 8 else 0
        result["create_time"] = le64(vd, 0x10) if len(vd) >= 0x18 else 0
        result["modify_time"] = le64(vd, 0x18) if len(vd) >= 0x20 else 0
        result["change_time"] = le64(vd, 0x20) if len(vd) >= 0x28 else 0
        result["access_time"] = le64(vd, 0x28) if len(vd) >= 0x30 else 0
        result["file_attrs"] = le32(vd, 0x40) if len(vd) >= 0x44 else 0
        result["file_size"] = le64(vd, 0x38) if len(vd) >= 0x40 else 0
        result["is_dir"] = bool(result["file_attrs"] & 0x10000000)
        # val+0x08 is the child's own OID only for a directory; a non-resident FILE has the home-dir
        # backref there (not its own OID -- files have no own OID). Keep child_oid = own OID for dirs
        # (drives recursion); expose 0 for files and keep the backref aside. --oid collision fix.
        if not result["is_dir"]:
            result["home_oid"] = result["child_oid"]
            result["child_oid"] = 0
        # derive the attribute-flag booleans here too (the >84-byte branch does this below);
        # otherwise non-resident files' encryption/compression/reparse/EA are silently dropped
        # from the summary counters and --filter (file_attrs is valid at 0x40 on this branch).
        result["is_encrypted"] = bool(result["file_attrs"] & 0x4000)
        result["is_compressed"] = bool(result["file_attrs"] & 0x0800)
        result["has_reparse"] = bool(result["file_attrs"] & 0x0400)
        result["has_ea"] = bool(result["file_attrs"] & 0x00040000)
        return result
    result["is_dir"] = False
    if len(vd) >= 0x60:
        result["create_time"] = le64(vd, 0x28)
        result["modify_time"] = le64(vd, 0x30)
        result["change_time"] = le64(vd, 0x38)
        result["access_time"] = le64(vd, 0x40)
        result["file_attrs"] = le32(vd, 0x48)
        result["internal_flags"] = le32(vd, 0x4C)
        result["security_id"] = le64(vd, 0x50)
        # CORRECTED 2026-06-17 (E30 retracted / E45): value+0x58 is FileSize, NOT a USN. The type-0x30
        # resident value is an index entry; the file's USN is LastUsn at value+0x68 ($SI+0x40), the
        # virtual $UsnJrnl:$J byte offset (0 if journal inactive). value+0x58 ($SI+0x30) is never a USN.
        result["usn"] = le64(vd, 0x68) if len(vd) >= 0x70 else 0
    result["is_encrypted"] = bool(result.get("file_attrs", 0) & 0x4000)
    result["is_compressed"] = bool(result.get("file_attrs", 0) & 0x0800)
    result["has_reparse"] = bool(result.get("file_attrs", 0) & 0x0400)
    result["has_ea"] = bool(result.get("file_attrs", 0) & 0x00040000)
    ea_data = None
    for search_off in range(0xA0, len(vd) - 20):
        if vd[search_off+8:search_off+11] == b"$LX":
            ea_data = vd[search_off:]
            break
        if search_off + 16 <= len(vd):
            next_off = le32(vd, search_off)
            name_len = vd[search_off + 5] if search_off + 5 < len(vd) else 0
            if next_off in (0, 0x14, 0x18, 0x1C, 0x20) and name_len in (5, 6, 7):
                potential_name = vd[search_off+8:search_off+8+name_len]
                if potential_name.startswith(b"$LX"):
                    ea_data = vd[search_off:]
                    break
    if ea_data:
        eas = _parse_extended_attributes(ea_data)
        if eas:
            result["extended_attributes"] = eas
            for ea in eas:
                if ea["name"] == "$LXMOD" and len(ea["value"]) >= 4:
                    result["lx_mode"] = le32(ea["value"], 0)
                elif ea["name"] == "$LXUID" and len(ea["value"]) >= 4:
                    result["lx_uid"] = le32(ea["value"], 0)
                elif ea["name"] == "$LXGID" and len(ea["value"]) >= 4:
                    result["lx_gid"] = le32(ea["value"], 0)
                elif ea["name"] == "$LXDEV" and len(ea["value"]) >= 8:
                    # $LXDEV = 8 bytes: u32 major + u32 minor (RD-confirmed on
                    # win11refs2gtargeted: testchr 1:3, testblk 7:0 — #341/E41).
                    result["lx_dev"] = (le32(ea["value"], 0), le32(ea["value"], 4))
    if count_snapshots_in_resident(vd) > 0:
        result["possible_snapshots"] = True
    return result




_ADS_DESCRIPTOR = 0x000500B0
_DATA_DESCRIPTOR = 0x000E0080

# N2 fix (2026-07-03): the local ADS byte-scanner (found only the FIRST ADS on multi-ADS files, undercounting
# 278 corpus-wide) is REPLACED by forefst's row-table _parse_ads_from_value (imported above). Same entry shape;
# `files` ADS counts now match forefst. See analysis/reports/forefstdev_audit_verification_2026-07-03.md (N2).






# ═══════════════════════════════════════════════════════════════════════
#  FILES — Directory tree listing
# ═══════════════════════════════════════════════════════════════════════

def cmd_files(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v"], valued=["--depth", "--oid"])
    verbose = args["v"]
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 20
    start_oid = _int_arg(args["oid"], "--oid", 0) if args["oid"] else 0x600

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        print("=" * 78)
        print("ReFS Directory Tree")
        print("=" * 78)
        start_name = _KNOWN_OIDS.get(start_oid, f"OID {_hx(start_oid)}")
        print(f"  Image:           {image}")
        print(f"  ReFS version:    {vmaj}.{vmin}")
        print(f"  Cluster size:    {_hx(cs)}")
        print(f"  Objects:         {len(obj_map)}")
        print(f"  Start OID:       {_hx(start_oid)}")
        print(f"  Start name:      {start_name}")
        print()

        results = []
        _walk_dir_tree(f, ps, cs, tr, obj_map, start_oid, "", 0, max_depth, results)
        # Non-resident files' EA bit (0x40000) lives in the type-0x40 backing (+0x48), not the type-0x30
        # pointer (+0x40) the walk read -- OR it back in so the Attrs column is correct (matches forefst).
        _apply_backing_ea(results, _build_backing_index(f, ps, cs, tr, obj_map))

        n_dirs = sum(1 for r in results if r["type"] == "DIR ")
        n_files = sum(1 for r in results if r["type"] == "FILE")
        n_ads = sum(len(r.get("ads", [])) for r in results)
        ads_note = f", {n_ads} ADS" if n_ads else ""
        print(f"  Total entries:   {len(results)} ({n_dirs} directories, {n_files} files{ads_note})")
        print()

        if verbose:
            print(f"  {'Type':<5} {'OID':<12} {'Attrs':<10} {'Size':>10} {'Modified':<20} {'Path'}")
            print(f"  {'-'*100}")
            for r in results:
                mod = _filetime_to_str(r["modify_time"]).replace(" UTC", "")
                a = _attrs_to_str(r["file_attrs"], full=False)
                sz = r["file_size"] if r["type"] == "FILE" else ""
                oid_str = _hx(r['oid']) if r['oid'] else ("(resident)" if r.get("resident") else "(non-res)")
                print(f"  {r['type']:<5} {oid_str:<12} {a:<10} {sz:>10} {mod:<20} {r['path']}")
                for ads in r.get("ads", []):
                    sz_ads = ads["stream_size"]
                    print(f"   ADS  {'':12} {'':10} {sz_ads:>10} {'':20} {r['path']}:{ads['name']}")
        else:
            print(f"  {'Type':<5} {'OID':<12} {'Path'}")
            print(f"  {'-'*60}")
            for r in results:
                oid_str = _hx(r['oid']) if r['oid'] else ("(resident)" if r.get("resident") else "(non-res)")
                print(f"  {r['type']:<5} {oid_str:<12} {r['path']}")
                for ads in r.get("ads", []):
                    print(f"   ADS  {'':12} {r['path']}:{ads['name']}  ({ads['stream_size']}B)")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  ATTRIBUTES — File attribute deep dive
# ═══════════════════════════════════════════════════════════════════════

def _analyze_dir_attributes(f, ps, cs, tr, obj_map, oid, path, depth, max_depth, results, filt):
    """Recursively analyze a directory's file attributes."""
    if depth > max_depth or oid not in obj_map: return
    rows = walk_bplus(f, ps, cs, tr, obj_map[oid])
    for kd, vd in rows:
        if len(kd) < 4 or le16(kd, 0) != 0x30: continue
        name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
        full_path = f"{path}/{name}" if path else name
        attrs = _extract_file_attributes(vd, name)
        attrs["path"] = full_path
        include = True
        if filt:
            if filt == "encrypted" and not attrs.get("is_encrypted"): include = False
            elif filt == "wsl" and "lx_mode" not in attrs: include = False
            elif filt == "reparse" and not attrs.get("has_reparse"): include = False
            elif filt == "snapshot" and not attrs.get("possible_snapshots"): include = False
        if include:
            results.append(attrs)
        if attrs.get("is_dir") and not attrs.get("is_resident"):
            child_oid = attrs.get("child_oid", 0)
            if child_oid and child_oid in obj_map:
                _analyze_dir_attributes(f, ps, cs, tr, obj_map, child_oid,
                                        full_path, depth + 1, max_depth, results, filt)




def cmd_attributes(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v"], valued=["--oid", "--depth", "--filter"])
    verbose = args["v"]
    start_oid = _int_arg(args["oid"], "--oid", 0) if args["oid"] else 0x600
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else 10
    filt = args["filter"]
    if filt == "wsl":
        # C16: refsanalysis `--filter wsl` selects files carrying the WSL ownership/mode metadata EA
        # ($LX* -> lx_mode). This differs, intentionally, from forefst `files --filter wsl`, which selects
        # by the WSL reparse TAG. A file can have one without the other (the $LX* EAs need a `-o metadata`
        # DrvFs mount), so the two counts need not match — they answer different questions.
        print(f"  NOTE: this selects files with WSL metadata EAs (lx_mode); forefst `--filter wsl` selects "
              f"by reparse tag instead — the two can differ (see docs).", file=sys.stderr)

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        print("=" * 78)
        print("ReFS File Attribute Analysis")
        print("=" * 78)
        print(f"  Image:        {image}")
        print(f"  ReFS version: {vmaj}.{vmin}")
        print(f"  Cluster size: {_hx(cs)}")
        print(f"  Start OID:    {_hx(start_oid)}")
        if filt:
            print(f"  Filter:       {filt}")
        print()

        results = []
        _analyze_dir_attributes(f, ps, cs, tr, obj_map, start_oid, "", 0, max_depth, results, filt)
        # OR the authoritative EA bit (type-0x40 backing +0x48) back into non-resident files; the
        # type-0x30 pointer (+0x40) this walk read drops it. Keeps Attributes/has_ea correct (= forefst).
        _apply_backing_ea(results, _build_backing_index(f, ps, cs, tr, obj_map))

        total = len(results)
        dirs = sum(1 for r in results if r.get("is_dir"))
        files = total - dirs
        resident = sum(1 for r in results if r.get("is_resident"))
        encrypted = sum(1 for r in results if r.get("is_encrypted"))
        wsl = sum(1 for r in results if "lx_mode" in r)
        reparse = sum(1 for r in results if r.get("has_reparse"))
        snapshots = sum(1 for r in results if r.get("possible_snapshots"))

        print(f"  Summary:")
        print(f"    Total entries:     {total}")
        print(f"    Directories:       {dirs}")
        print(f"    Files:             {files}")
        print(f"    Resident files:    {resident}")
        print(f"    EFS encrypted:     {encrypted}")
        print(f"    WSL metadata:      {wsl}")
        print(f"    Reparse points:    {reparse}")
        print(f"    With snapshots:    {snapshots}")
        print(f"\n{'='*78}")
        print("Detailed Attributes")
        print("=" * 78)

        for r in results:
            path = r.get("path", r.get("name", "?"))
            is_dir = r.get("is_dir", False)
            prefix = "DIR " if is_dir else "FILE"
            print(f"\n  {prefix} {path}")
            if "create_time" in r:
                print(f"    Created:     {_filetime_to_str(r['create_time'])}")
                print(f"    Modified:    {_filetime_to_str(r['modify_time'])}")
                print(f"    Changed:     {_filetime_to_str(r['change_time'])}")
            fa = r.get("file_attrs", 0)
            if fa:
                flag_list = _attrs_to_list(fa)
                print(f"    Attributes:  {' | '.join(flag_list)} ({_hx(fa)})")
            iflags = r.get("internal_flags", 0)
            if iflags:
                iflag_names = _iflags_to_list(iflags)
                print(f"    IntFlags:    {' | '.join(iflag_names)} ({_hx(iflags)})")
            if "security_id" in r and r["security_id"]:
                print(f"    SecurityId:  {_hx(r['security_id'])}")
            if "usn" in r and r["usn"]:
                print(f"    USN:         {r['usn']}")
            if r.get("is_resident"):
                print(f"    Storage:     RESIDENT ({r['value_len']} bytes)")
            elif not is_dir:
                print(f"    Storage:     NON-RESIDENT (no own OID)")
            if r.get("is_encrypted"):
                print(f"    *** EFS ENCRYPTED ***")
            if "lx_mode" in r:
                print(f"    WSL Mode:    {_decode_lx_mode(r['lx_mode'])}")
            if "lx_uid" in r:
                print(f"    WSL UID:     {r['lx_uid']}")
            if "lx_gid" in r:
                print(f"    WSL GID:     {r['lx_gid']}")
            if "lx_dev" in r:
                _maj, _min = r["lx_dev"]
                print(f"    WSL Dev:     {_maj},{_min} (major,minor)")
            if r.get("has_reparse"):
                print(f"    *** REPARSE POINT (symlink/WSL special file) ***")
            if r.get("possible_snapshots"):
                print(f"    *** STREAM SNAPSHOTS (large embedded data: {r['value_len']} bytes) ***")
            if verbose and "extended_attributes" in r:
                print(f"    Extended Attributes:")
                for ea in r["extended_attributes"]:
                    val_hex = ea["value"].hex() if len(ea["value"]) <= 16 else ea["value"][:16].hex() + "..."
                    print(f"      {ea['name']:12s} = {val_hex} ({len(ea['value'])} bytes)")

        print()
        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  DATARUNS — File data extent analysis
# ═══════════════════════════════════════════════════════════════════════






# ═══════════════════════════════════════════════════════════════════════
#  EXTRACT — File content extraction
# ═══════════════════════════════════════════════════════════════════════



def _resolve_nonresident_usn(f, ps, cs, tr, obj_map, parent_oid, child_oid, file_id, file_size):
    """Per-file LastUsn/UsnJournalId for a non-resident file (#327): read from its OWN backing
    type-0x40 record (val+0x68/+0x70 = $SI+0x40/+0x48), NOT the home directory's $SI. The backing
    record lives in the parent OR home object's tree keyed by file_id; the colliding ordinal is
    disambiguated by size (same strict size-match as the hard-link grouping). Returns
    (last_usn, usn_journal_id) or None. RD-proven: type-0x40 val+0x68 == journal LastUsn 245/245
    (fsutil) + 593/0 (5 images, 0 mismatch)."""
    def _find(owner):
        if not owner or owner not in obj_map:
            return None
        try:
            rows = walk_bplus(f, ps, cs, tr, obj_map[owner])
        except Exception:
            return None
        for kd, vd in rows:
            if len(kd) >= 0x10 and le16(kd, 0) == 0x40 and le64(kd, 0x08) == file_id and len(vd) >= 0x70:
                return (le64(vd, 0x60), le64(vd, 0x58), le64(vd, 0x68),
                        le64(vd, 0x70) if len(vd) >= 0x78 else 0)   # (alloc, size, last_usn, journal_id)
        return None
    loc = _find(parent_oid)
    rem = _find(child_oid)
    rec = None
    if loc and loc[1] == file_size and loc[0] > 0:
        rec = loc
    elif rem and rem[1] == file_size:
        rec = rem
    elif loc and loc[1] == file_size:
        rec = loc
    elif file_size == 0 and rem is not None and rem[1] == 0:
        rec = rem
    elif file_size == 0 and loc is not None and loc[1] == 0:
        rec = loc
    if rec is None:
        return None
    return (rec[2], rec[3])


def cmd_details(image, remaining, partition_start):
    """Feature A: full details for ANY file by PATH (resident files have no OID)."""
    args = _parse_args(remaining, flags=["--json"], valued=[])
    path = args["_rest"][0] if args["_rest"] else None
    if not path:
        die("details requires a file path, e.g.  details /dir/file.txt")
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))
    try:
        parent_oid, kd, vd = resolve_path(f, ps, cs, tr, obj_map, path)
        if vd is None:
            die(f"path not found: {path}")
        resident = len(vd) > 84
        name = path.replace("\\", "/").rstrip("/").split("/")[-1]
        info = {"path": path, "name": name, "parent_oid": parent_oid,
                "storage": "resident" if resident else "non-resident", "value_len": len(vd)}

        if resident:
            info["oid"] = None
            if len(vd) >= 0x60:
                info.update({
                    "created": _filetime_to_str(le64(vd, 0x28)),
                    "modified": _filetime_to_str(le64(vd, 0x30)),
                    "changed": _filetime_to_str(le64(vd, 0x38)),
                    "accessed": _filetime_to_str(le64(vd, 0x40)),
                    "file_attrs": le32(vd, 0x48), "internal_flags": le32(vd, 0x4C),
                    # usn = LastUsn (value+0x68); value+0x58 is FileSize, not a USN (E30/E45)
                    "security_id": le64(vd, 0x50), "usn": le64(vd, 0x68) if len(vd) >= 0x70 else 0})
            if len(vd) >= 0x80:
                info.update({
                    "data_size_alloc": le64(vd, 0x60), "last_usn": le64(vd, 0x68),
                    "usn_journal_id": le64(vd, 0x70), "packed_ea_size": le32(vd, 0x78),
                    "reparse_tag": le32(vd, 0x7C)})
            info["file_size"] = get_resident_file_size(vd)
            subs = {"data": [], "ads": [], "snapshots": [], "ea": [], "reparse": []}
            for k, v in parse_resident_btree_rows(vd):
                if len(k) < 0x0E:
                    continue
                typ = le16(k, 0x0C)
                nm = ""
                if len(k) > 0x10:
                    try: nm = k[0x10:].decode("utf-16-le").rstrip("\x00")
                    except Exception: nm = k[0x10:].hex()
                if typ == 0x80:
                    # skip internal snapshot-extent holders (descriptor 0x10028, binary stream-idx names)
                    if len(v) >= 8 and le32(v, 4) == 0x10028:
                        continue
                    printable = all(c.isprintable() for c in nm) if nm else True
                    dname = (nm if printable else "(default)") or "(default)"
                    dsize = le64(v, 0x20) if len(v) >= 0x28 else 0
                    # the default-stream summary row reads 0 for snapshot-bearing files; the live size
                    # is the (already-resolved) file_size from the 0x1000 holder — keep them consistent
                    if dname == "(default)" and not dsize:
                        dsize = info["file_size"]
                    subs["data"].append({"name": dname, "size": dsize})
                elif typ == 0xB0:
                    if len(v) >= 0x12 and le16(v, 0x10) == 2:
                        subs["snapshots"].append({"name": nm,
                            "size": le64(v, 0x20) if len(v) >= 0x28 else 0,
                            "stream_idx": le32(v, 0x44) if len(v) >= 0x48 else 0,
                            "time": _filetime_to_str(le64(v, 0x4C)) if len(v) >= 0x54 else ""})
                    else:
                        subs["ads"].append({"name": nm, "size": le64(v, 0x20) if len(v) >= 0x28 else 0})
                elif typ == 0xE0:
                    subs["ea"].append({"name": nm, "len": len(v)})
                elif typ == 0xC0:
                    # REPARSE_DATA_BUFFER.ReparseTag sits at v+0x0C (after a 12-byte ReFS sub-record
                    # descriptor: reserved u32 @0, length @4, 0x0C marker @8). Disk-proven to equal the
                    # header +0x7C mirror on every reparse file (symlink 0xa000000c, WSL $LX nodes
                    # 0x80000023..26). The old le32(v,0) read the reserved zero -> always 0x00000000.
                    subs["reparse"].append({"name": nm, "tag": le32(v, 0x0C) if len(v) >= 0x10 else 0})
            info["subrecords"] = subs
        else:
            child_oid = le64(vd, 0x08) if len(vd) >= 0x10 else 0   # val+0x08 (own OID for dirs / home backref for files)
            if len(vd) >= 0x44:
                info.update({
                    "created": _filetime_to_str(le64(vd, 0x10)),
                    "modified": _filetime_to_str(le64(vd, 0x18)),
                    "changed": _filetime_to_str(le64(vd, 0x20)),
                    "accessed": _filetime_to_str(le64(vd, 0x28)),
                    "file_attrs": le32(vd, 0x40),
                    "file_size": le64(vd, 0x38) if len(vd) >= 0x40 else 0})
                info["is_dir"] = bool(info["file_attrs"] & 0x10000000)
            # val+0x08 is the child's own OID only for a DIRECTORY; for a non-resident FILE it is the
            # home-dir backref (not the file's OID -- files have no own OID). #327 / --oid collision fix.
            if info.get("is_dir"):
                info["oid"] = child_oid
            else:
                info["oid"] = 0
                info["home_backref"] = child_oid
            # value+0x08 is the child OID for a DIRECTORY (resolve its own $SI), but the home-dir BACKREF
            # for a non-resident FILE (#327) — resolving the backref would report the HOME DIRECTORY's
            # security/usn as the file's. So resolve the child $SI only for directories; a non-resident
            # file's SecurityId/USN are not stored in its dir entry and are reported as not-available.
            if info.get("is_dir") and child_oid in obj_map:
                si = get_object_si(f, ps, cs, tr, obj_map[child_oid])
                if si:
                    info["security_id"] = si.get("security_id", 0)
                    info["usn"] = si.get("usn", 0)
                    info["internal_flags"] = si.get("internal_flags", 0)
            elif not info.get("is_dir"):
                info["security_unavailable"] = True   # SecurityId not in the dir entry (still n/a)
                _fid = le64(vd, 0x00) if len(vd) >= 8 else 0
                _u = _resolve_nonresident_usn(f, ps, cs, tr, obj_map, parent_oid, child_oid,
                                              _fid, info.get("file_size", 0))
                if _u is not None:
                    info["last_usn"], info["usn_journal_id"] = _u
                # OR the authoritative EA bit (type-0x40 backing +0x48) into a non-resident file's attrs —
                # the +0x40 pointer this branch read drops it. Targeted lookup in the file's HOME dir so
                # the Attributes line agrees with files/attributes and forefst (#329 EA-bit fix).
                if child_oid in obj_map:
                    _idx = {}
                    for _bk, _bv in walk_bplus(f, ps, cs, tr, obj_map[child_oid]):
                        if len(_bk) >= 0x10 and le16(_bk, 0) == 0x40 and len(_bv) >= 0x60:
                            _idx.setdefault((child_oid, le64(_bk, 0x08)), []).append(
                                (le64(_bv, 0x58), le32(_bv, 0x48)))
                    _bfa = _backing_file_attrs(_idx, child_oid, _fid, info.get("file_size", 0))
                    if _bfa is not None and (_bfa & 0x40000):
                        info["file_attrs"] = info.get("file_attrs", 0) | 0x40000

        if args["json"]:
            print(json.dumps(info, indent=2, default=str)); return 0

        W = 78
        print("=" * W); print(f"File Details — {path}"); print("=" * W)
        print(f"  Name:           {name}")
        if resident:
            print(f"  Storage:        RESIDENT (inline in parent dir row — no OID of its own)")
        elif info.get("is_dir"):
            print(f"  Storage:        non-resident directory  (OID {_hx(info['oid'])}, own B+-tree)")
        else:
            print(f"  Storage:        non-resident file  (no OID of its own; data in out-of-line extents)")
        print(f"  Parent OID:     {_hx(parent_oid)}")
        if "is_dir" in info and info["is_dir"]:
            print(f"  Type:           DIRECTORY")
        print(f"  File size:      {info.get('file_size', 0)} bytes")
        if "data_size_alloc" in info:
            print(f"  DataSize (alloc): {info['data_size_alloc']} bytes ($SI+0x38; 8-aligned $DATA alloc)")
        fa = info.get("file_attrs", 0)
        # Decode via the canonical attrs_to_str (same helper cmd_attributes uses) so EVERY bit shows
        # (EA/Compressed/IntegrityStream/Sparse/... ), not the 6 the old hand-rolled list covered.
        _decoded = attrs_to_str(fa, full=True, hex_if_empty=False)
        print(f"  Attributes:     0x{fa:08x}" + (f"  {_decoded}" if _decoded else ""))
        if "created" in info:
            print(f"  Created:        {info['created']}")
            print(f"  Modified:       {info['modified']}")
            print(f"  MFT-Changed:    {info['changed']}")
            print(f"  Accessed:       {info['accessed']}")
        if info.get("security_unavailable"):
            print(f"  SecurityId:     n/a (non-resident file — not stored in the directory entry)")
        else:
            print(f"  SecurityId:     {info.get('security_id', 0)}  (resolves in OID 0x530)")
        if "last_usn" in info:
            print(f"  LastUsn:        {info['last_usn']}  ($UsnJrnl:$J byte offset)")
            print(f"  UsnJournalId:   {info['usn_journal_id']}")
            if info.get("reparse_tag"):
                print(f"  ReparseTag:     0x{info['reparse_tag']:08x}")
            if info.get("packed_ea_size"):
                print(f"  PackedEaSize:   {info['packed_ea_size']}")
        if resident:
            s = info["subrecords"]
            print()
            print(f"  Sub-records:    {len(s['data'])} $DATA, {len(s['ads'])} ADS, "
                  f"{len(s['snapshots'])} snapshot(s), {len(s['ea'])} $EA, {len(s['reparse'])} reparse")
            for d in s["data"]:
                print(f"    $DATA  {d['name']:<20} {d['size']} bytes")
            for a in s["ads"]:
                print(f"    ADS    {a['name']:<20} {a['size']} bytes")
            for sn in s["snapshots"]:
                print(f"    SNAP   {sn['name']:<20} {sn['size']} bytes  idx=0x{sn['stream_idx']:x}  {sn['time']}")
            if s["snapshots"]:
                print(f"    → export snapshot versions with:  snapshots --file {name} --extract DIR")
            for e in s["ea"]:
                print(f"    $EA    {e['name']:<20} {e['len']} bytes")
            for rp in s["reparse"]:
                print(f"    REPARSE tag=0x{rp['tag']:08x}")
        elif info.get("snapshot_count"):
            print(f"  Snapshots:      {info['snapshot_count']} (non-resident — use snapshots --file {name})")
        print("=" * W)
        return 0
    finally:
        f.close()




# ═══════════════════════════════════════════════════════════════════════
        #  Forensic subcommand constants
# ═══════════════════════════════════════════════════════════════════════

# SID name table now lives ONCE in forefst (WELL_KNOWN_SIDS, imported above).




# SYSTEM_MANDATORY_LABEL (ACE type 0x11) mask bits are an integrity-policy field, NOT file rights.

# ACE types whose layout is [type, flags, size, mask(u32), SID, ...] — mask at +4, SID at +8. Covers the
# basic + CALLBACK + RESOURCE_ATTRIBUTE + SCOPED_POLICY ACEs. OBJECT ACEs (0x05-0x08/0x0B/0x0C/0x0F) are
# EXCLUDED: their SID follows object_flags(4)+up-to-two GUIDs, so SID is NOT at +8.

# Reparse-tag name table now lives ONCE in forefst (REPARSE_TAGS, imported above; post-E41,
# H3-verified 2026-06-29). _REPARSE_TAGS copy deleted.
# Cloud (OneDrive) variants share the 0x...1A suffix: 0x9000NN1A for NN=01..0F.



























# ═══════════════════════════════════════════════════════════════════════
#  SECURITY — Security descriptor parser (OID 0x530)
# ═══════════════════════════════════════════════════════════════════════









# ═══════════════════════════════════════════════════════════════════════
#  REPARSE — Reparse point parser
# ═══════════════════════════════════════════════════════════════════════








# ═══════════════════════════════════════════════════════════════════════
#  DELETED — Deleted file recovery
# ═══════════════════════════════════════════════════════════════════════
















# ═══════════════════════════════════════════════════════════════════════
#  SNAPSHOTS — Stream snapshots and ADS
# ═══════════════════════════════════════════════════════════════════════

def _extract_snapshot_name(key_data):
    if len(key_data) < 18: return None
    if (key_data[8:12] == b'\x02\x00\x00\x80' and key_data[12] == 0xB0 and key_data[13] == 0x00 and le32(key_data, 4) == 0):
        name = key_data[16:].decode("utf-16-le", errors="replace").rstrip("\x00")
        if name and '\x00' not in name: return name
    return None


def _classify_b0_entry(val_data):
    return 'TRUE_SNAPSHOT' if _is_snapshot_value(val_data) else 'ADS'


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







# ═══════════════════════════════════════════════════════════════════════
#  INTEGRITY — Metadata page integrity verification
# ═══════════════════════════════════════════════════════════════════════


















# ═══════════════════════════════════════════════════════════════════════
#  MLOG — MLog (durable log) analysis
# ═══════════════════════════════════════════════════════════════════════







# ═══════════════════════════════════════════════════════════════════════
#  USN — Change Journal analysis
# ═══════════════════════════════════════════════════════════════════════













# ═══════════════════════════════════════════════════════════════════════
#  TIMELINE — merge USN + MLog + $SI MACB into one chronological stream
# ═══════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════
#  TIMESTOMP — multi-source timestamp-anomaly detection
# ═══════════════════════════════════════════════════════════════════════





# ═══════════════════════════════════════════════════════════════════════
#  ALL — Run integrated subcommands in sequence
# ═══════════════════════════════════════════════════════════════════════



def cmd_all(image, remaining, partition_start):
    # Structure/lab tools refsanalysis still owns (the forensic sections moved to forefst).
    sections = [
        "summary", "boot", "supb", "chkp", "schema", "objects",
        "parentchild", "containers", "files",
    ]
    for name in sections:
        print(f"\n{'='*78}")
        print(f"  refsanalysis: {name}")
        print(f"{'='*78}\n")
        handler = _HANDLERS.get(name)
        if handler:
            try:
                handler(image, [], partition_start)
            except SystemExit:
                print(f"\n  [{name}] failed", file=sys.stderr)
    return 0


# ═══════════════════════════════════════════════════════════════════════
#  HANDLERS — dispatch table for integrated subcommands
# ═══════════════════════════════════════════════════════════════════════



_HANDLERS = {
    "summary": cmd_summary,
    "boot": cmd_boot,
    "supb": cmd_supb,
    "chkp": cmd_chkp,
    "schema": cmd_schema,
    "objects": cmd_objects,
    "parentchild": cmd_parentchild,
    "containers": cmd_containers,
    "upcase": cmd_upcase,
    "oid30": cmd_oid30,
    "files": cmd_files,
    "attributes": cmd_attributes,
    "details": cmd_details,
    "all": cmd_all,
    "bootedit": None,  # set after _bootedit_main is defined
}
# The 12 byte-identical forensic commands moved to forefst (proven identical, P2-P4 + the extensive test).
# refsanalysis keeps only what forefst doesn't reproduce (lab/structure + the lab-format files/attributes/
# details/summary). Invoking a moved command points the user to forefst.
MOVED_TO_FOREFST = {"usn", "mlog", "timeline", "timestomp", "extract", "security", "reparse",
                    "deleted", "snapshots", "integrity", "export", "dataruns"}


# ═══════════════════════════════════════════════════════════════════════
#  BOOTEDIT — VBR editor (integrated, no external subprocess)
# ═══════════════════════════════════════════════════════════════════════

def _u16le(d): return struct.unpack("<H", d)[0]
def _u32le(d): return struct.unpack("<I", d)[0]
def _u64le(d): return struct.unpack("<Q", d)[0]

def _text_to_guid(text):
    return uuid.UUID(text).bytes_le

def _validate_vbr(sector, offset):
    """Check VBR has ReFS/FSRS signatures."""
    if sector[0x03:0x07] != b"ReFS" or sector[0x10:0x14] != b"FSRS":
        sig = sector[3:15].rstrip(b'\x00').decode('ascii', errors='replace')
        if b"NTFS" in sector[:16]:
            die(f"partition at 0x{offset:x} contains NTFS, not ReFS")
        if b"-FVE-FS-" in sector[:16]:
            die(f"partition at 0x{offset:x} is BitLocker-encrypted")
        die(f"no ReFS boot sector at offset 0x{offset:x} (signature: '{sig}')")

def _display_vbr(sector):
    """Display VBR fields in a readable table."""
    fields = {n: sector[o:o+s] for n, o, s, _ in _VBR_FIELDS}
    vbr_size = _u16le(fields["vbr_size"])
    stored_csum = _u16le(fields["checksum"])
    computed_csum = _vbr_checksum(sector, vbr_size)
    algo = _u16le(fields["checksum_algo"])
    algo_name = {0: "None", 2: "CRC64", 4: "SHA256"}.get(algo, f"unknown(0x{algo:04x})")
    ver = f"{fields['version'][0]}.{fields['version'][1]}"
    vol_flags = _u32le(fields["volume_flags"])
    serial = _u64le(fields["serial"])
    container = _u64le(fields["container_size"])
    guid_raw = fields["format_guid"]
    guid_str = _guid_to_text(guid_raw) if guid_raw != b"\x00" * 16 else "(not set — Win10 or upgraded)"

    flag_parts = []
    if vol_flags & 0x02: flag_parts.append("base")
    if vol_flags & 0x04: flag_parts.append("format-time")
    if vol_flags & 0x20: flag_parts.append("Win11-cap1")
    if vol_flags & 0x40: flag_parts.append("Win11-cap2")
    flag_desc = f" ({'+'.join(flag_parts)})" if flag_parts else ""

    print()
    print("  Field                   Offset   Raw bytes                                    Interpreted")
    print("  " + "-" * 110)
    for name, offset, size, desc in _VBR_FIELDS:
        raw = _hexbytes(sector[offset:offset + size])
        if name == "fs_name":       interp = _ascii_clean(fields[name])
        elif name == "fsrs_id":     interp = _ascii_clean(fields[name])
        elif name == "vbr_size":    interp = f"{vbr_size} decimal (0x{vbr_size:04x})"
        elif name == "checksum":
            m = "OK" if stored_csum == computed_csum else f"MISMATCH (computed=0x{computed_csum:04x})"
            interp = f"0x{stored_csum:04x} [{m}]"
        elif name == "version":         interp = ver
        elif name == "checksum_algo":   interp = f"{algo} decimal = 0x{algo:04x} ({algo_name})"
        elif name == "volume_flags":    interp = f"0x{vol_flags:08x}{flag_desc}"
        elif name == "serial":          interp = f"0x{serial:016x}"
        elif name == "container_size":
            interp = f"0x{container:x} ({_human_size(container)})" if container else "0x0 (will default to 64 MiB)"
        elif name == "format_guid":     interp = guid_str
        elif name == "total_sectors":
            ts = _u64le(fields[name])
            interp = f"{ts} decimal ({_human_size(ts * _u32le(fields['bytes_per_sect']))})"
        elif name == "bytes_per_sect":
            bps = _u32le(fields[name])
            interp = f"{bps} decimal (0x{bps:x})"
        elif name == "sects_per_clust":
            spc = _u32le(fields[name])
            bps = _u32le(fields["bytes_per_sect"])
            interp = f"{spc} decimal (cluster = {_human_size(spc * bps)})"
        else: interp = ""
        print(f"  {desc:<25s} 0x{offset:02x}     {raw:<44s} {interp}")
    print()

def _diagnose_fixboot(sector):
    """Detect refsutil fixboot damage. Returns list of issues."""
    issues = []
    container = _u64le(sector[0x40:0x48])
    if container == 0:
        issues.append(("container_size is zero", 0x40, 8, sector[0x40:0x48],
            "refsutil fixboot zeroes this field. Driver defaults to 64 MiB but mount may fail."))
    serial = _u64le(sector[0x38:0x40])
    if serial == 0:
        issues.append(("volume_serial is zero", 0x38, 8, sector[0x38:0x40],
            "refsutil fixboot zeroes the serial. Volume may not be recognized."))
    guid = sector[0x48:0x58]
    minor_v = sector[0x29]
    if guid == b"\x00" * 16 and minor_v >= 14:
        issues.append(("format_guid is zero on a 3.14 volume", 0x48, 16, guid,
            "Expected non-zero on native Win11 format. May indicate fixboot damage or upgraded volume."))
    algo = _u16le(sector[0x2A:0x2C])
    if minor_v >= 14 and algo == 0:
        issues.append(("checksum_algo=None on a 3.14 volume", 0x2A, 2, sector[0x2A:0x2C],
            "Native 3.14 expects CRC64 (2) or SHA256 (4). Value 0 may indicate fixboot or upgrade."))
    flags = _u32le(sector[0x2C:0x30])
    if minor_v >= 14 and flags == 0:
        issues.append(("volume_flags is zero on a 3.14 volume", 0x2C, 4, sector[0x2C:0x30],
            "Expected non-zero flags on any valid volume. Likely fixboot damage."))
    elif minor_v < 14 and flags not in (0x02, 0x06):
        issues.append((f"unexpected flags 0x{flags:08x} for 3.4 volume", 0x2C, 4, sector[0x2C:0x30],
            "Expected 0x02 or 0x06 for Win10 format."))
    vbr_size = _u16le(sector[0x14:0x16])
    stored = _u16le(sector[0x16:0x18])
    computed = _vbr_checksum(sector, vbr_size)
    if stored != computed:
        issues.append(("checksum mismatch", 0x16, 2, sector[0x16:0x18],
            f"Stored=0x{stored:04x} vs computed=0x{computed:04x}. VBR modified without recalculating."))
    return issues

def _propose_repair(sector):
    """Propose fixboot repair actions."""
    repairs = []
    if _u64le(sector[0x40:0x48]) == 0:
        repairs.append({"field": "container_size", "offset": 0x40, "size": 8,
            "current": sector[0x40:0x48], "proposed": struct.pack("<Q", 0x4000000),
            "reason": "Restore default container size: 0x4000000 = 64 MiB."})
    minor_v = sector[0x29]
    if minor_v >= 14 and _u16le(sector[0x2A:0x2C]) == 0:
        repairs.append({"field": "checksum_algo", "offset": 0x2A, "size": 2,
            "current": sector[0x2A:0x2C], "proposed": struct.pack("<H", 2),
            "reason": "Restore CRC64 (value 2, default for native 3.14)."})
    if minor_v >= 14 and _u32le(sector[0x2C:0x30]) == 0:
        repairs.append({"field": "volume_flags", "offset": 0x2C, "size": 4,
            "current": sector[0x2C:0x30], "proposed": struct.pack("<I", 0x66),
            "reason": "Restore typical Win11 native flags: 0x66."})
    return repairs

def _make_sparse_copy(source, output):
    """Create a sparse copy of a disk image."""
    out = Path(output)
    if out.exists():
        die(f"output file already exists: {out}")
    src_size = Path(source).stat().st_size
    BS = 1024 * 1024
    zero_block = b"\x00" * BS
    written = 0
    total = (src_size + BS - 1) // BS
    print(f"  Creating sparse copy: {source} -> {out}")
    print(f"  Source size: {src_size:,} bytes ({_human_size(src_size)})")
    with open(source, "rb") as src_f, open(out, "wb") as dst_f:
        dst_f.truncate(src_size)
        offset = 0
        while offset < src_size:
            remaining = min(BS, src_size - offset)
            data = src_f.read(remaining)
            if not data: break
            if data != zero_block[:len(data)]:
                dst_f.seek(offset)
                dst_f.write(data)
                written += 1
            offset += remaining
    print(f"  Done: {written}/{total} blocks written ({written * 100 // max(total, 1)}% density)")
    try:
        disk = os.stat(out).st_blocks * 512
        print(f"  Logical: {src_size:,} bytes, Disk: {disk:,} bytes ({disk * 100 // src_size}%)")
    except Exception: pass
    return out

def _auto_output(image):
    p = Path(image)
    return str(p.parent / f"{p.stem}_modified{p.suffix}")

def _bootedit_prepare_write(image, args):
    """Prepare write target. Returns (target_path, boot_offset)."""
    ps = args.get("partition_start")
    if args.get("inplace"):
        if not os.access(image, os.W_OK):
            print(f"  ERROR: --inplace requested but the image is not writable: {image}", file=sys.stderr)
            print("  (read-only file/mount; omit --inplace to work on a safe copy instead)", file=sys.stderr)
            sys.exit(2)
        print("\n  [--inplace] Modifying the ORIGINAL image directly.")
        return image, _find_boot_offset(image, ps)
    out = args.get("output") or _auto_output(image)
    print(f"\n  [SAFE MODE] Original image will NOT be modified.")
    _make_sparse_copy(image, out)
    print(f"  Working on copy: {out}\n")
    return out, _find_boot_offset(out, ps)

def _bootedit_main(image, remaining, partition_start):
    """Handle bootedit subcommand internally."""
    if not remaining:
        print("Usage: refsanalysis.py <image> bootedit <action> [options]", file=sys.stderr)
        print("Actions: read, export, repair, set, import, sparse", file=sys.stderr)
        print("Example: refsanalysis.py disk.raw bootedit read", file=sys.stderr)
        return 1

    action = remaining[0]
    if action in ("--help", "-h", "help"):
        _render_cmd_help("bootedit"); return 0
    rest = remaining[1:]

    # Parse common flags from rest
    args = {"partition_start": partition_start, "dry_run": False,
            "inplace": False, "output": None}
    filtered = []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--dry-run":        args["dry_run"] = True
        elif a == "--inplace":      args["inplace"] = True
        elif a in ("-o", "--output") and i + 1 < len(rest):
            args["output"] = rest[i + 1]; i += 1
        elif a == "--partition-start" and i + 1 < len(rest):
            args["partition_start"] = rest[i + 1]; i += 1
        elif a == "--offset" and i + 1 < len(rest):
            args["partition_start"] = rest[i + 1]; i += 1
        elif a == "--field" and i + 1 < len(rest):
            args["field"] = rest[i + 1]; i += 1
        elif a == "--value" and i + 1 < len(rest):
            args["value"] = rest[i + 1]; i += 1
        elif a in ("-i", "--input") and i + 1 < len(rest):
            args["input"] = rest[i + 1]; i += 1
        elif a in ("--help", "-h"):
            _bootedit_help(); return 0
        else:
            filtered.append(a)
        i += 1

    try:
        if action == "read":
            bo = _find_boot_offset(image, args["partition_start"])
            with open(image, "rb") as f: sector = _read_at(f, bo, 512)
            _validate_vbr(sector, bo)
            sha = hashlib.sha256(sector).hexdigest()
            print(f"\nReFS Boot Sector at offset 0x{bo:x}")
            print(f"SHA-256: {sha}")
            _display_vbr(sector)

        elif action == "export":
            if not args["output"]:
                die("export requires -o FILE")
            bo = _find_boot_offset(image, args["partition_start"])
            with open(image, "rb") as f: sector = _read_at(f, bo, 512)
            _validate_vbr(sector, bo)
            Path(args["output"]).write_bytes(sector)
            print(f"Exported 512 bytes from offset 0x{bo:x} to {args['output']}")
            print(f"SHA-256: {hashlib.sha256(sector).hexdigest()}")

        elif action == "sparse":
            if not args["output"]:
                die("sparse requires -o FILE")
            _make_sparse_copy(image, args["output"])

        elif action == "repair":
            bo = _find_boot_offset(image, args["partition_start"])
            with open(image, "rb") as f: sector = bytearray(_read_at(f, bo, 512))
            _validate_vbr(sector, bo)
            sha = hashlib.sha256(bytes(sector)).hexdigest()
            print(f"\nDiagnosing boot sector at offset 0x{bo:x}")
            print(f"SHA-256: {sha}")
            _display_vbr(sector)

            issues = _diagnose_fixboot(sector)
            if not issues:
                print("No fixboot damage detected. Boot sector appears healthy.")
                return 0

            print(f"Found {len(issues)} issue(s):")
            for desc, off, sz, cur, problem in issues:
                print(f"\n  [{desc}]")
                print(f"    Offset: 0x{off:02x}-0x{off + sz - 1:02x}")
                print(f"    Current: {_hexbytes(cur)}")
                print(f"    Problem: {problem}")

            repairs = _propose_repair(sector)
            if not repairs:
                print("\nNo automatic repairs available.")
                return 0

            print(f"\n{'='*72}\nProposed repairs ({len(repairs)}):\n{'='*72}")
            modified = bytearray(sector)
            for r in repairs:
                print(f"\n  {r['field']} (0x{r['offset']:02x}):")
                print(f"    Current:  {_hexbytes(r['current'])}")
                print(f"    Proposed: {_hexbytes(r['proposed'])}")
                print(f"    Reason:   {r['reason']}")
                modified[r["offset"]:r["offset"] + r["size"]] = r["proposed"]

            vbr_size = _u16le(modified[0x14:0x16])
            new_cs = _vbr_checksum(bytes(modified), vbr_size)
            old_cs = _u16le(modified[0x16:0x18])
            modified[0x16:0x18] = struct.pack("<H", new_cs)
            print(f"\n  checksum (0x16): 0x{old_cs:04x} -> 0x{new_cs:04x}")

            if args["dry_run"]:
                print(f"\n[DRY RUN] No changes written.")
                print(f"Would-be SHA-256: {hashlib.sha256(bytes(modified)).hexdigest()}")
                return 0

            target, target_bo = _bootedit_prepare_write(image, args)
            if args["inplace"]:
                confirm = input("\nApply repairs to ORIGINAL image? Type 'YES': ")
                if confirm != "YES":
                    print("Aborted."); return 1
            with open(target, "r+b") as f:
                f.seek(target_bo); f.write(bytes(modified))
            print(f"Repairs applied at 0x{target_bo:x} in {target}")
            print(f"New SHA-256: {hashlib.sha256(bytes(modified)).hexdigest()}")

        elif action == "set":
            if "field" not in args or "value" not in args:
                die("set requires --field FIELD --value VALUE")
            bo = _find_boot_offset(image, args["partition_start"])
            with open(image, "rb") as f: sector = bytearray(_read_at(f, bo, 512))
            _validate_vbr(sector, bo)

            field, val_str = args["field"], args["value"]
            valid_fields = ["checksum_algo", "volume_flags", "container_size",
                            "format_guid", "version", "serial"]
            if field not in valid_fields:
                die(f"unknown field '{field}'. Available: {', '.join(valid_fields)}")

            if field == "checksum_algo":
                off, sz = 0x2A, 2; val = int(val_str, 0)
                if val not in (0, 2, 4):
                    print(f"WARNING: {val} is not a known algo (0=None, 2=CRC64, 4=SHA256).")
                new_b = struct.pack("<H", val)
                print(f"\n  checksum_algo: {val} decimal = 0x{val:04x}")
            elif field == "volume_flags":
                off, sz = 0x2C, 4; val = int(val_str, 0)
                new_b = struct.pack("<I", val)
                print(f"\n  volume_flags: 0x{val:08x}")
            elif field == "container_size":
                off, sz = 0x40, 8; val = int(val_str, 0)
                new_b = struct.pack("<Q", val)
                print(f"\n  container_size: 0x{val:x} ({_human_size(val)})")
            elif field == "format_guid":
                off, sz = 0x48, 16
                if val_str.lower() == "zero":
                    new_b = b"\x00" * 16; print("\n  format_guid: zeroed")
                elif val_str.lower() == "random":
                    new_b = uuid.uuid4().bytes_le
                    print(f"\n  format_guid: {_guid_to_text(new_b)} (random)")
                else:
                    new_b = _text_to_guid(val_str)
                    print(f"\n  format_guid: {_guid_to_text(new_b)}")
            elif field == "version":
                off, sz = 0x28, 2
                parts = val_str.split(".")
                if len(parts) != 2: die("version must be 'major.minor' (e.g. '3.14')")
                new_b = bytes([int(parts[0]), int(parts[1])])
                print(f"\n  version: {parts[0]}.{parts[1]}")
            elif field == "serial":
                off, sz = 0x38, 8; val = int(val_str, 0)
                new_b = struct.pack("<Q", val)
                print(f"\n  serial: 0x{val:016x}")

            old_b = sector[off:off + sz]
            if old_b == new_b:
                print(f"  Field '{field}' already has the requested value."); return 0

            print(f"  Field:    {field} (offset 0x{off:02x}, {sz} bytes)")
            print(f"  Current:  {_hexbytes(old_b)}")
            print(f"  New:      {_hexbytes(new_b)}")
            sector[off:off + sz] = new_b
            vbr_size = _u16le(sector[0x14:0x16])
            new_cs = _vbr_checksum(bytes(sector), vbr_size)
            old_cs = _u16le(sector[0x16:0x18])
            sector[0x16:0x18] = struct.pack("<H", new_cs)
            print(f"  Checksum: 0x{old_cs:04x} -> 0x{new_cs:04x}")

            if args["dry_run"]:
                print(f"\n[DRY RUN] No changes written.")
                print(f"Would-be SHA-256: {hashlib.sha256(bytes(sector)).hexdigest()}")
                return 0

            target, target_bo = _bootedit_prepare_write(image, args)
            if args["inplace"]:
                confirm = input(f"\nApply change to ORIGINAL image? Type 'YES': ")
                if confirm != "YES":
                    print("Aborted."); return 1
            with open(target, "r+b") as f:
                f.seek(target_bo); f.write(bytes(sector))
            print(f"Change applied at 0x{target_bo:x} in {target}")
            print(f"New SHA-256: {hashlib.sha256(bytes(sector)).hexdigest()}")

        elif action == "import":
            if "input" not in args:
                die("import requires -i FILE")
            inp = Path(args["input"])
            if not inp.exists(): die(f"input file not found: {inp}")
            new_sector = inp.read_bytes()
            if len(new_sector) != 512: die(f"input must be 512 bytes, got {len(new_sector)}")
            if new_sector[0x03:0x07] != b"ReFS" or new_sector[0x10:0x14] != b"FSRS":
                die("input is not a valid ReFS boot sector (missing ReFS/FSRS)")

            if args["dry_run"]:
                bo = _find_boot_offset(image, args["partition_start"])
                with open(image, "rb") as f: old = _read_at(f, bo, 512)
                print(f"\n[DRY RUN] Would import {inp} to offset 0x{bo:x}")
                for off in range(512):
                    if old[off] != new_sector[off]:
                        print(f"  0x{off:03x}: 0x{old[off]:02x} -> 0x{new_sector[off]:02x}")
                return 0

            target, target_bo = _bootedit_prepare_write(image, args)
            if args["inplace"]:
                confirm = input("\nWrite to ORIGINAL image? Type 'YES': ")
                if confirm != "YES":
                    print("Aborted."); return 1
            with open(target, "r+b") as f:
                f.seek(target_bo); f.write(new_sector)
            print(f"Boot sector written at 0x{target_bo:x} in {target}")

        else:
            print(f"Unknown bootedit action: {action}", file=sys.stderr)
            print("Actions: read, export, repair, set, import, sparse", file=sys.stderr)
            return 1

    except SystemExit:
        raise
    except Exception as e:
        die(str(e))
    return 0

def _bootedit_help():
    print("""refsanalysis.py <image> bootedit <action> [options]

Actions (read-only):
  read                           Display the boot sector
  export -o FILE                 Export VBR to binary file

Actions (write — safe by default, creates sparse copy):
  repair [--dry-run]             Diagnose and repair fixboot damage
  set --field F --value V [--dry-run]  Modify a VBR field
  import -i FILE [--dry-run]     Import a boot sector from binary file
  sparse -o FILE                 Create a sparse copy of the image

Write options:
  --inplace                      DANGEROUS: modify original image directly
  -o FILE                        Output path for modified copy
                                 (default: <image>_modified.<ext>)
  --dry-run                      Show changes without writing

Fields for 'set' (hex 0x.. or decimal):
  checksum_algo    VBR+0x2A  0=None, 2=CRC64, 4=SHA256
  volume_flags     VBR+0x2C  hex recommended (e.g. 0x66)
  container_size   VBR+0x40  hex (e.g. 0x4000000 = 64 MiB)
  format_guid      VBR+0x48  UUID string, 'zero', or 'random'
  version          VBR+0x28  'major.minor' (e.g. '3.14')
  serial           VBR+0x38  hex (e.g. 0x1234ABCD)""")


# ─── Main ────────────────────────────────────────────────────────────

_HANDLERS["bootedit"] = _bootedit_main

# ── Hand-written per-command help ────────────────────────────────────────────
# Rendered by `refsanalysis help <cmd>` / `refsanalysis <image> <cmd> --help`. Most STRUCTURE commands
# share a verbosity ladder: -v (verbose) / -vv (detailed) / --verify (consistency checks) / --raw (hex
# dump) / -H (header banner). Per-command entries list which apply and what the command decodes.
_VERB_LADDER = "verbosity: -v / -vv, plus --verify / --raw / -H where supported (see Options)"
CMD_HELP = {
 "summary": {"tag": "Volume overview (version, size, files, containers)",
   "desc": ["Quick triage of the volume: ReFS version, GUID/label, cluster & container size, checksum",
            "type, checkpoint state, and the root-table counts. `summary++` adds OID 0x500 volume detail."],
   "opts": [("--json", "emit the summary as a JSON object")],
   "ex": [("summary", "quick volume triage"), ("summary++", "extended overview (OID 0x500 detail)"),
          ("summary++ --json", "machine-readable extended summary")]},
 "summary++": {"tag": "Extended volume summary (OID 0x500 detail + metrics)",
   "desc": ["The extended triage report: everything `summary` shows plus OID 0x500 volume detail and",
            "additional metrics. (forefst's `summary` subcommand is the forensic-grade equivalent.)"],
   "opts": [("--json", "emit the summary as a JSON object")],
   "ex": [("summary++", "extended human-readable report"), ("summary++ --json", "machine-readable")]},
 "all": {"tag": "Run all structure tools in sequence",
   "desc": ["One-shot structural dump: runs every owned structure tool (summary, boot, supb, chkp,",
            "schema, objects, parentchild, containers, files) back-to-back. Redirect to a file to keep it."],
   "opts": [],
   "ex": [("all", "full structural dump"), ("all > structure_dump.txt", "capture the whole report")]},
 "files": {"tag": "List files and directories (lab-format tree)",
   "desc": ["Flat namespace listing from the root (or --oid subtree). -v adds a wide table with decoded",
            "attributes, sizes and modified-times. (forefst's `files` is the forensic CSV/JSON equivalent.)"],
   "opts": [("-v", "verbose table (Attrs, Size, Modified)"),
            ("--oid 0xNNN", "start the walk at this directory OID (default 0x600)"),
            ("--depth N", "max recursion depth (default 20)")],
   "ex": [("files", "flat namespace listing"), ("files -v", "verbose table with attributes"),
          ("files --oid 0x705", "list only the subtree under OID 0x705")]},
 "attributes": {"tag": "File attribute deep-dive (EA / WSL / timestamps / flags)",
   "desc": ["Per-file attribute analysis: decoded flags, internal flags, timestamps, EFS/reparse/WSL.",
            "-v adds the decoded Extended-Attributes block ($LXMOD/$LXUID/...). --filter narrows by type."],
   "opts": [("-v", "also decode the Extended Attributes block (WSL $LX*)"),
            ("--filter T", "one of: encrypted, wsl, reparse, snapshot"),
            ("--oid 0xNNN", "start OID (default 0x600)"), ("--depth N", "max recursion depth (default 10)")],
   "ex": [("attributes --filter wsl", "files carrying WSL/Linux metadata"),
          ("attributes -v --filter reparse", "reparse points with decoded buffers"),
          ("attributes -v", "full attribute dump incl. EAs")]},
 "details": {"tag": "Full details for ANY file by path (resident files have no OID)",
   "desc": ["Complete per-file record addressed by PATH: timestamps, attributes, SecurityId, and the",
            "inline sub-records for resident files ($DATA, ADS, snapshots, $EA, reparse)."],
   "opts": [("/path", "(positional) e.g. /dir/file.txt"), ("--json", "emit the record as JSON")],
   "ex": [("details /hello.txt", "full record for a resident file"),
          ("details /dir/bigfile.bin", "a non-resident file"),
          ("details /hello.txt --json", "machine-readable record")]},
 "boot": {"tag": "Boot sector (VBR) analysis",
   "desc": ["Decode the ReFS Volume Boot Record: signature, version, cluster/container size, serial,",
            "checksum. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "verbose / detailed (geometry arithmetic)"), ("--verify", "VBR consistency table"),
            ("--raw", "512-byte hex+ASCII dump"), ("-H", "header banner (SHA-256, offset)")],
   "ex": [("boot", "confirm ReFS + read version/geometry"), ("boot --verify", "VBR integrity triage"),
          ("boot -vv", "full forensic VBR dump")]},
 "supb": {"tag": "Superblock (SUPB) analysis",
   "desc": ["Decode the superblock: GUID, version, self-descriptor, checkpoint pointers. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "verbose / detailed"), ("--verify", "7-check consistency table"),
            ("--raw", "hex dump of the SUPB page"), ("-H", "header banner")],
   "ex": [("supb", "superblock snapshot"), ("supb --verify", "7-check consistency table"),
          ("supb -vv", "full forensic detail")]},
 "chkp": {"tag": "Checkpoint (CHKP) with container translation",
   "desc": ["Decode the latest checkpoint and the 13 global root tables, with VLCN→PLCN container",
            "translation. -v switches to the container-translation layout. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "container-translation layout / + GPT & full detail"),
            ("--verify", "consistency checks (root count == 13, CTR translation)"),
            ("--raw", "hex dump of the CHKP page")],
   "ex": [("chkp", "decode the latest checkpoint + roots"), ("chkp --verify", "decode + consistency checks"),
          ("chkp -vv", "full forensic dump")]},
 "objects": {"tag": "Object ID table (OID → LCN mapping)",
   "desc": ["List every object (OID) with its friendly name and root LCN. -v adds physical LCNs and page",
            "signatures; -vv dumps the raw per-object entries. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "header + LCNs / full per-object raw dump"),
            ("--verify", "check every object's root page signature")],
   "ex": [("objects", "compact OID table"), ("objects -v", "+ physical LCNs & page sizes"),
          ("objects -vv --verify", "raw entries + verification")]},
 "schema": {"tag": "Schema table (table-type definitions)",
   "desc": ["List the schema/attribute table-type definitions (key rules, value layouts). -vv prints the",
            "raw schema values. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "boxed header / + raw schema values"),
            ("--verify", "self-consistency checks"), ("-H", "header banner")],
   "ex": [("schema", "list table-type definitions"), ("schema --verify", "list + consistency check"),
          ("schema -vv", "+ raw schema values")]},
 "parentchild": {"tag": "Parent-child relationship table",
   "desc": ["List the directory parent→child relationships (the 0x600-area index). -v draws an ASCII tree;",
            "-vv dumps raw rows. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "header + ASCII tree / + raw row hex"),
            ("--verify", "6 structural checks")],
   "ex": [("parentchild", "relationship list + counts"), ("parentchild -v", "+ ASCII directory tree"),
          ("parentchild -vv --verify", "raw rows + verification")]},
 "containers": {"tag": "Container table and allocator analysis",
   "desc": ["Volume geometry, mapped-container counts and allocator state. -v appends the full per-",
            "container table (ID, physical LCN, free/capacity)."],
   "opts": [("-v", "full per-container table")],
   "ex": [("containers", "geometry + allocator summary"), ("containers -v", "+ per-container table")]},
 "upcase": {"tag": "Unicode upcase table",
   "desc": ["Decode the Unicode upcase (case-folding) table. -v shows sample mappings; -vv dumps every",
            "non-identity mapping. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "sample mappings / every non-identity mapping"),
            ("--verify", "six consistency checks"), ("-H", "header banner")],
   "ex": [("upcase", "table summary"), ("upcase -v", "+ sample case mappings"),
          ("upcase -vv", "dump all non-identity mappings")]},
 "oid30": {"tag": "OID 0x30 session-activity analysis",
   "desc": ["Inspect the OID 0x30 object (session/activity rows). -v dumps every row's decoded fields."],
   "opts": [("-v", "detailed per-row dump")],
   "ex": [("oid30", "session-activity summary"), ("oid30 -v", "+ per-row decoded fields")]},
 "bootedit": {"tag": "[DANGEROUS] Boot sector editor & repair",
   "desc": ["Inspect or repair the ReFS VBR. ACTIONS: read (display), export -o FILE (dump VBR), repair",
            "(fix refsutil fixboot damage), set --field F --value V (edit one field), import -i FILE,",
            "sparse -o FILE (sparse image copy). Writes go to a SPARSE COPY unless --inplace is given.",
            "ALWAYS preview with --dry-run first; --inplace modifies the ORIGINAL image."],
   "opts": [("read | export | repair | set | import | sparse", "the action (positional)"),
            ("--field F / --value V", "set: which VBR field and its new value"),
            ("-i FILE / -o FILE", "import input / export-sparse-write output path"),
            ("--dry-run", "repair/set/import: preview byte changes, write nothing"),
            ("--inplace", "DANGEROUS: modify the original image instead of a copy")],
   "ex": [("bootedit read", "display & validate the VBR (read-only)"),
          ("bootedit repair --dry-run", "diagnose fixboot damage, preview the fix"),
          ("bootedit set --field checksum_algo --value 2 --dry-run", "preview a field change")]},
 "forefst": {"tag": "Run any forefst subcommand (passthrough to the forensic tool)",
   "desc": ["`refsanalysis <image> forefst <cmd> [options]` delegates to forefst — so every forefst",
            "subcommand is reachable without leaving refsanalysis: the file lister (files/summary/",
            "fastsummary/search/details) and the forensic suite (usn/mlog/timeline/timestomp/extract/",
            "security/reparse/deleted/snapshots/integrity/export/dataruns). Run `... forefst --help`",
            "for forefst's own help, or `... forefst <cmd> --help` for one command."],
   "opts": [("<cmd> [options]", "any forefst subcommand and its flags (forwarded verbatim)")],
   "ex": [("forefst usn --stats", "forefst's USN activity summary"),
          ("forefst files --filter ea --json", "forefst's file listing, EA-only, as JSON"),
          ("forefst --help", "forefst's full subcommand list")]},
}

def _render_cmd_help(cmd):
    if cmd == "summary++":
        key = "summary++"
    else:
        key = cmd
    h = CMD_HELP.get(key)
    if not h:
        print(f"{PROG}: no help for {cmd!r}. Run `{PROG} --list`.", file=sys.stderr); return
    print(f"{PROG} <image> {cmd} — {h['tag']}\n")
    print(f"  usage: {PROG} <image> {cmd} [options]\n")
    for line in h["desc"]:
        print(f"  {line}")
    if h["opts"]:
        print("\n  Options:")
        for flag, desc in h["opts"]:
            print(f"    {flag:34} {desc}" if flag else f"    {'':34} {desc}")
    print("\n  Examples:")
    for ex, note in h["ex"]:
        print(f"    {PROG} disk.raw {ex}")
        print(f"        {note}")
    print("\n  Global: --partition-start BYTES (override volume offset), --json (where supported).")

def main():
    _ALL_CMDS = set(_HANDLERS) | {"summary++"}
    _argv = sys.argv
    # ── help handling (before any dispatch) ──
    if len(_argv) >= 2 and _argv[1] in ("help",):
        if len(_argv) >= 3 and (_argv[2] in _ALL_CMDS or _argv[2] == "forefst"):
            _render_cmd_help(_argv[2]); sys.exit(0)
        print_usage(); sys.exit(0)
    # `refsanalysis <image> <cmd> --help/-h` → per-command help (bootedit keeps its own action help)
    if len(_argv) >= 4 and ("-h" in _argv[3:] or "--help" in _argv[3:]) and _argv[2] in _ALL_CMDS \
            and _argv[2] != "bootedit":
        _render_cmd_help(_argv[2]); sys.exit(0)

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    if sys.argv[1] in ("--list", "-l"):
        print_list(); sys.exit(0)
    if sys.argv[1] in ("--help", "-h"):
        print_usage(); sys.exit(0)
    if sys.argv[1] == "--version":
        print(f"refsanalysis.py v{VERSION} — ReFS disk image analysis suite")
        sys.exit(0)

    image = sys.argv[1]
    valid_subcmd_names = {n for n, _, _ in SUBCOMMANDS}
    if image in valid_subcmd_names and not os.path.exists(image):
        die(f"'{image}' looks like a subcommand, not an image file. "
            f"Usage: refsanalysis.py <image> {image}")
    validate_image(image)

    # ── forefst passthrough ──  refsanalysis <image> forefst <cmd> [opts]  →  forefst <image> <cmd> [opts]
    # Delegates to forefst's full dispatch, so every forefst subcommand (files/summary/search/details + the
    # 12 forensic commands) and its --help are reachable from refsanalysis without leaving the tool. forefst
    # is already imported at module load; no code is duplicated.
    if len(sys.argv) >= 3 and sys.argv[2] == "forefst":
        import forefst as _forefst
        sys.argv = [sys.argv[0], image] + sys.argv[3:]   # drop the 'forefst' token; keep image + the rest
        return _forefst.main()

    if len(sys.argv) < 3:
        subcmd, remaining = "summary", []
    else:
        subcmd, remaining = sys.argv[2], sys.argv[3:]

    # Extract --partition-start from remaining args (global option)
    partition_start = None
    filtered = []
    i = 0
    while i < len(remaining):
        if remaining[i] == "--partition-start" and i + 1 < len(remaining):
            try:
                partition_start = int(remaining[i + 1], 0)
            except ValueError:
                die(f"invalid --partition-start value: {remaining[i + 1]}")
            i += 2
        else:
            filtered.append(remaining[i]); i += 1
    remaining = filtered

    if subcmd in ("--help", "-h"):
        print_usage(); sys.exit(0)

    # ── summary++ shortcut ──
    if subcmd == "summary++":
        sys.exit(cmd_summary(image, remaining, partition_start, plus_mode=True))

    # ── moved-to-forefst commands ──
    if subcmd in MOVED_TO_FOREFST:
        die(f"'{subcmd}' moved to forefst — run:  forefst.py {image} {subcmd} {' '.join(remaining)}".rstrip()
            + f"\n         or, via refsanalysis:  refsanalysis.py {image} forefst {subcmd} {' '.join(remaining)}".rstrip())

    # ── Resolve subcommand (exact match or prefix) ──
    handler = _HANDLERS.get(subcmd)
    if handler is None and subcmd not in _HANDLERS:
        matches = [n for n in _HANDLERS if n.startswith(subcmd)]
        if len(matches) == 1:
            subcmd = matches[0]; handler = _HANDLERS[subcmd]
        elif len(matches) > 1:
            die(f"ambiguous subcommand '{subcmd}'. Matches: {', '.join(sorted(matches))}")
        else:
            # a prefix that only matches moved-to-forefst commands → point to forefst
            moved_pref = sorted(n for n in MOVED_TO_FOREFST if n.startswith(subcmd))
            if moved_pref:
                die(f"'{subcmd}' matches {', '.join(moved_pref)} — moved to forefst "
                    f"(run: forefst.py {image} {moved_pref[0]})")
            die(f"unknown subcommand: {subcmd}. Run 'refsanalysis.py --list' for help.")

    if handler is None:
        die(f"subcommand '{subcmd}' is not yet integrated")

    sys.exit(handler(image, remaining, partition_start))


def print_usage():
    print(f"""refsanalysis.py v{VERSION} — ReFS disk image analysis suite

Usage:
  refsanalysis.py <image> <subcommand> [options]
  refsanalysis.py <image>                             (quick summary)
  refsanalysis.py <image> summary++                   (extended summary)
  refsanalysis.py <image> <subcommand> --help         (detailed help for one subcommand)
  refsanalysis.py help <subcommand>                   (same, without an image)
  refsanalysis.py --list                              (list all subcommands)

Examples:
  refsanalysis.py disk.raw                            # quick volume summary
  refsanalysis.py disk.raw summary++ --json           # extended JSON summary
  refsanalysis.py disk.raw files -v                   # list files with timestamps
  refsanalysis.py disk.raw attributes --filter wsl    # find WSL files
  refsanalysis.py disk.raw details /dir/file.txt      # full per-file details by path
  refsanalysis.py disk.raw objects                    # object-ID table
  refsanalysis.py disk.raw schema                     # schema table
  refsanalysis.py disk.raw bootedit repair --dry-run  # diagnose fixboot damage
  refsanalysis.py disk.raw all                        # run all structure tools
  refsanalysis.py disk.raw forefst usn --stats        # run any forefst command via the passthrough

Note: the forensic commands (usn/mlog/timeline/timestomp/extract/security/reparse/deleted/
snapshots/integrity/export/dataruns) moved to forefst — run `forefst.py <image> <cmd>`, or reach them
without leaving refsanalysis via the passthrough: `refsanalysis.py <image> forefst <cmd> [options]`.

Global options:
  --partition-start <offset>   Override GPT partition detection (bytes, hex OK)
  --list, -l                   List all subcommands with options
  --help, -h                   Show this help
  --version                    Show version""")


def print_list():
    print(f"refsanalysis.py v{VERSION} — available subcommands\n")
    categories = [
        ("Quick analysis", ["summary", "summary++", "all"]),
        ("File system content", ["files", "attributes", "details"]),
        ("Structure analysis", ["boot", "supb", "chkp", "objects", "schema",
                                "parentchild", "containers", "upcase", "oid30"]),
        ("Boot sector repair", ["bootedit"]),
    ]
    integrated = set(_HANDLERS.keys()) | {"summary++"}
    cmd_map = {name: (desc, args) for name, desc, args in SUBCOMMANDS}
    for cat_name, cmd_names in categories:
        print(f"  {cat_name}:")
        for name in cmd_names:
            if name in cmd_map:
                desc, extra = cmd_map[name]
                print(f"    {name:<14} {desc}")
                for a in extra:
                    print(f"    {'':<14}   {a}")
        print()
    print("  forefst passthrough:")
    print(f"    {'forefst':<14} Run any forefst subcommand — refsanalysis.py <image> forefst <cmd> [options]")
    print(f"    {'':<14}   (files/summary/search/details + usn/mlog/timeline/timestomp/extract/security/")
    print(f"    {'':<14}    reparse/deleted/snapshots/integrity/export/dataruns). See `help forefst`.")
    print()


if __name__ == "__main__":
    main()
