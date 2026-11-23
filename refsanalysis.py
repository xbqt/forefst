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
  python3 refsanalysis.py <image> bootedit repair --dry-run  # check the bootstrap copies, preview restores + fixboot
  python3 refsanalysis.py <image> all                   # run the main structure tools in sequence
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
from pathlib import Path

# Decision 54 (1.14.0; the maintainer, 2026-11-12: "(a), yes, pin it"): refsanalysis runs only with the forefst of its
# own release. A copy of that forefst kept beside it in `refsanalysis_forefst/` (from 1.15.0; 1.14.0 ships none, both
# files being 1.14.0) is the one imported; after the import the two versions are compared (below VERSION).
_PIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "refsanalysis_forefst")
if os.path.isfile(os.path.join(_PIN_DIR, "forefst.py")):
    sys.path.insert(0, _PIN_DIR)
import forefst as _forefst
from forefst import utf8_console                                                            # N489
from forefst import (_walk_storage_word, _data_residency, _record_placement, DATA_UNKNOWN,   # E87: the `files` axes
    
    DEFAULT_DEPTH,
    FILE_ATTR_FLAGS, SUPB_LCN, Translator, _select_ct_root, container_table_read,
    bootstrap, count_snapshots_in_resident, find_refs_partition, get_object_si,
    get_resident_file_size, gpt_partition_detail, le16, le32, le64,
    parse_resident_btree_rows,
    parse_supb as _forefst_parse_supb, parse_vbr as _forefst_parse_vbr, resolve_path,
    validate_image as _validate_image, walk_bplus, walk_directory_tree,
    _guid_str, _hx, _parse_extended_attributes,   # 5.1: single-source helpers (C2-6: the checksum is forefst's boot_sector_checksum)
    _vbr_bytes_per_sector,   # K063 / audit B5: IMPORTED, not re-implemented -- this tool multiplied
                             # total_sectors by a hard-coded 512, so a 4Kn volume read 504.0 MB
                             # instead of 3.9 GiB. A4 fixed forefst.py and left this one; a second
                             # copy of the rule is how that happened, so there is only one.
    _verify_self_checksum,   # A1/K035: `chkp --verify` must verify the page's OWN checksum
    _walk_dir_tree, _filetime_to_str,   # K086: were copies here, each missing what the
                             # other had (cycle guard vs identity fields; real sizes vs ADS context); merged
                             # in forefst.py -- a second copy is how a guard ends up in only one of them
    _skip_note,          # A2: a summary count that silently defaults to 0 reads as "none present"
    # A11: the three facts this tool used to keep its own copies of -- which checkpoint copy is in use, what
    # makes a superblock copy valid, and the exit rule. One definition each, in forefst.py.
    checkpoint_select, supb_validate, rc_escalate,
    # Group 2 (1.13.2): the bootstrap-copy inventory and the ONE redundancy list (A3, decision 25.3), the root-table
    # counts (A3/K044), the 0x520 reading (N246) and the container-size disclosure (N153) -- forefst's, not copies.
    _scan_backup_copies, _print_redundancy_findings,
    usn_state_text, vbr_container_size, 
    CONTAINER_SIZE_DEFAULT_TAG,
    # Decision 27 (1.13.2): the checkpoint conditions that make every command exit 2 (N332, 27.3, N341 -- the set
    # bootstrap says), the wording of a root 0xC/7/8 that does not verify, and A3's count convention for the summary's
    # table counts (N338) -- forefst's, as bootstrap and forefst `summary` use them.
    _view_conditions, _root_fail_text, table_row_count, count_text,
    # G2c (1.13.2): the zero-container-size finding (N354, decision 29) and "this run recorded metadata it could not
    # read" (N345, N348: one test with forefst's) -- forefst's.
    container_size_zero_text, _metadata_incomplete,
    # G2c2 (1.13.2): the roots 0xC/7/8 check of one checkpoint copy, worded once for `supb --verify` and `chkp --verify`
    # (N361, N364 R6), and what was checked on the backup superblock copy read after a fallback (N364 B1) -- forefst's.
    _root_check, _supb_backup_how,
    # Group 3 (1.13.2): a checkpoint copy that was read but carries no CHKP signature (N374): the error a reader records
    # for a copy, and the few words a copy row carries -- forefst's, one text with every form that prints the copy
    _chkp_copy_error, _chkp_unreadable_hole,
    # Wave B (1.13.2, N369): why the volume is not read from the newest checkpoint copy, one text for supb, containers
    # and forefst `deleted`
    _chkp_not_used_why,
    # Wave C (1.14.0, N373): the words of a checkpoint copy refs.sys rejects and the test that it is a copy not in use
    # (V-a) -- forefst's, one wording with every statement of such a copy
    chkp_reject_clause, _chkp_rejected_va,
    # G2c3 (1.13.2): the seek-and-read of an offset computed from an on-disk value (N371): an offset past any file
    # offset is a failed read (an OSError), never CPython's ValueError past every `except (OSError, OverflowError)`
    _seek_read, OffsetTooLarge,
    # Wave C (1.14.0, B3): the one volume length (total sectors x bytes per sector) and its cluster count N -- this
    # tool's `allocators` took the image's length as the volume's
    volume_length, volume_clusters,
    # Wave C (1.14.0, N344 / N142): the boot sector the volume is read from (the primary, or a backup the search finds
    # when the primary fails a boot-sector test), its statement, and the quoted OEM id -- one decision with forefst
    boot_sector_copy, boot_sector_bytes, _say_boot_sector_copy, oem_id_text,
    # Wave B (1.13.2, group 5): what a checkpoint SHA-256 covers, one text with forefst `summary` (F11: one cluster)
    chkp_hash_span_text,
    # Wave B (1.13.2, group 7, N265): the boot sector's version test of forefst `summary`, one definition for the five
    # commands of decision 29's set, and the $VOLUME_INFORMATION row it reads (`boot --verify`)
    version_findings, read_volume_information, VERSION_CONTRADICTED_STATE,
    # Wave C (1.13.2, N434 N-6): the decode of the $VOLUME_INFORMATION row's value (+0x80..+0x83, +0x90, +0xA0), one
    # definition with forefst `fastsummary` and `read_volume_information` (`summary` kept its own copy)
    
    # Wave C (1.13.2, N358 / N427 / N445; Q10, Q11): statements over an Object Table not read in full are worded from
    # its walk's read state -- one set of words and one table of required structures with forefst
    object_table_read_state, object_absent_reason, object_absent_text, table_unread_text, 
    required_structure_missing,
    # Wave B (1.13.2, part 3): two superblock copies that verify and whose payloads differ (N417, one sentence with
    # forefst `summary`), and the volume signature of a GUID (N414, CalculateVolumeSignature) -- forefst's
    supb_payload_reference, supb_payload_differs_text, volume_signature,
    # B15 (wave C): the choice clause, the pair test of N417 / N449, the failures of the copy not read
    supb_pair_verified, SUPB_CHOICE_RULE_TEXT,
    # Wave C (1.13.2, N422; T-CL1): the two system-table pairs as refs.sys opens them (Logfile Information {0xA, 0x9},
    # Upcase {8, 7}) -- the copy read and the redundancy conditions of the copies, one definition with forefst
    system_table_pair, system_table_pair_texts, 
    # B14 (1.14.0): the superblock rebuild of `bootedit repair` (the self-checksum writer), the boot-sector tests of a
    # backup copy and the byte runs a restore changes -- forefst's
    _self_checksum_recipe, _recompute_self_checksum, boot_sector_failures, _boot_sector_ss, _byte_diff_runs,
    _chkp_role,
    alloc_capacity, alloc_decode_row, alloc_read_summary, alloc_row_counts, _ALLOC_TIERS,
)

PROG = "refsanalysis"
VERSION = "1.14.0"
if getattr(_forefst, "VERSION", None) != VERSION:
    # decision 54: the command does not run (exit 1), with the reason on one line
    sys.stderr.write("refsanalysis %s runs only with forefst %s; this forefst is %s (%s)\n"
                     % (VERSION, VERSION, getattr(_forefst, "VERSION", "of no version"),
                        getattr(_forefst, "__file__", "?")))
    sys.exit(1)


# ─── Subcommand definitions ──────────────────────────────────────────
# Each entry: (subcommand, description, extra_args_help)
# Dispatch is handled by HANDLERS dict below all cmd_* definitions.
SUBCOMMANDS = [
    # ── Quick analysis ──
    ("summary",     "Volume overview (version, size, files, containers)",
     ["--json: JSON output"]),
    ("summary++",   "Extended summary with OID 0x500 detail and metrics",
     ["--json: JSON output"]),
    ("all",         "Run the main structure tools in sequence (summary, boot, supb, chkp, schema, objects, "
                    "parentchild, containers, files)", []),

    # ── File system content ──
    ("files",       "List files and directories",
     ["-v: verbose (timestamps, sizes)", "--depth N: recursion depth", "--oid 0xNNN: start OID"]),
    ("attributes",  "File attribute details (EAs, timestamps, sizes)",
     ["-v: verbose", "--oid 0xNNN: start OID", "--depth N: recursion depth",
      "--filter {encrypted,wsl,reparse,snapshot}: filter by type"]),
    ("details",     "Full details for ANY file by PATH (files have no OID)",
     ["<path>: e.g. /dir/file.txt", "--json: JSON output",
      "(decodes the inline $SI, $DATA, ADS, snapshots, $EA, reparse of a file whose record is embedded;",
      " the extents of a file whose data is in extents — addresses files by path, since files have no OID)"]),

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
    ("allocators",  "Allocator tables (free/used space accounting)",
     ["-v: per-row detail", "-vv: every row", "--json: machine-readable"]),
    ("upcase",      "Unicode upcase table",
     ["-v: verbose", "-vv: all mappings", "--verify: consistency checks", "-H: header fields"]),
    ("oid30",       "OID 0x30, the heat engine table (I/O by 10-minute generation)",
     ["-v: verbose"]),

    # ── Boot sector repair ──
    ("bootedit",    "[DANGEROUS] Boot sector editor and repair",
     ["read: display boot sector (read-only)",
      "export -o FILE: export VBR to binary file",
      # B14 (1.14.0): the copy restore ships; the help says what it restores and what it does not
      "repair [--dry-run]: check the two boot sector copies, the three superblock copies and the two",
      "        checkpoint copies; restore a boot sector or superblock copy that fails from a copy that",
      "        passes (checkpoint copies are reported, never restored), each restore logged with",
      "        SHA-256 before and after; else diagnose fixboot damage in the PRIMARY boot sector.",
      "        Default writes a repaired sparse copy; --inplace edits the original.",
      "set --field FIELD --value VALUE [--dry-run]: modify VBR field",
      "import -i FILE [--dry-run]: replace boot sector from a 512-byte file",
      "sparse -o FILE: create sparse image copy",
      "--inplace: modify original image",
      "-o FILE: output path for modified copy"]),
]

# ─── Shared helpers ──────────────────────────────────────────────────

def validate_image(path, partition_start=None):
    _validate_image(path, die_fn=die, partition_start=partition_start)


def _read_at(f, offset, size):
    # N378 (4w): the guarded read (N371). An offset no file can be read at -- a partition start taken from a GPT entry
    # (find_refs_partition's first-Basic-Data fallback) -- ended the run with CPython's "cannot fit 'int' into an
    # offset-sized integer"; it now stops with this tool's message naming the offset (exit 1, cannot run).
    try:
        data = _seek_read(f, offset, size)
    except OffsetTooLarge as e:
        die(f"cannot read {_forefst.count_noun(size, 'byte')} at 0x{offset:x}: {e}")
    if len(data) != size:
        die(f"cannot read {_forefst.count_noun(size, 'byte')} at 0x{offset:x} (got {len(data)})")
    return data



def _read_boot_copy(f, bo):
    """C2-6 (1.14.0): one boot-sector copy, read by forefst's `_boot_copy_read` -- the one definition of how a copy is
    read (512 bytes, and its first +0x14 bytes when +0x14 is above 512; the review S8: this was a second copy of it) --
    with this tool's guard (N378): an offset no file can be read at, or a copy the image ends inside, stops with this
    tool's message (exit 1)."""
    try:
        b = _forefst._boot_copy_read(f, bo)
    except OffsetTooLarge as e:
        die(f"cannot read 512 bytes at 0x{bo:x}: {e}")
    n = le16(b, 0x14) if len(b) >= 0x16 else 0
    want = n if 512 < n <= 0x1000 else 512
    if len(b) != want:
        die(f"cannot read {_forefst.count_noun(want, 'byte')} at 0x{bo:x} (got {len(b)})")
    return b


def _cksum_text(v):
    """C2-6: a computed boot-sector checksum as the tables print it; None (no checksum over the copy's length)."""
    return "0x%04x" % v if v is not None else "not computed (the length at +0x14 is not 88 up to the bytes read)"

def _hexbytes(data, max_len=None):
    if max_len and len(data) > max_len:
        return " ".join(f"{b:02x}" for b in data[:max_len]) + " ..."
    return " ".join(f"{b:02x}" for b in data)


def _ascii_clean(d):
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in d)


_human_size = _forefst._human_size   # K6 (1.14.0): forefst's reading-aid size (IEC units, whole when exact)


def _print_json(obj, keys=None):
    """N497 / K1-K21 (1.14.0): refsanalysis's JSON as forefst writes its own -- UTF-8 (no `\\u` escapes), the identifier
    / LCN / offset / flag fields in hex (`machine_forms`), null for an absent value (`json_null`), forefst's output names
    (`out_keys`; `keys` = the command's overrides)."""
    print(json.dumps(_forefst.out_keys(_forefst.json_null(_forefst.machine_forms(obj)), keys), indent=2,
                     ensure_ascii=False, default=str))


def _hexid(v):
    """K1 / K9 / K10 (1.14.0): forefst's identifier form, `0x2874` (None stays None)."""
    return _forefst.hexid(v)


def _ok(v):
    return "OK" if v else "FAIL"


_guid_to_text = _guid_str          # K4 (1.14.0): forefst's one GUID form (canonical, lower case)



_TABLE_LAST_COL = 80     # N377: the last column wraps here (a root check's reason made one table 203 columns wide)


def _print_table(headers, rows):
    if not rows:
        print("(no rows)"); print(); return
    import textwrap
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    widths[-1] = min(widths[-1], max(_TABLE_LAST_COL, len(headers[-1])))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in widths]))
    for row in rows:
        cells = [str(c) for c in row]
        # N377: a token (a path, a hash) is never split -- a line holds whole words, so the cell is the row's words joined
        last = textwrap.wrap(cells[-1], widths[-1], break_long_words=False, break_on_hyphens=False) or [""]
        print(fmt.format(*(cells[:-1] + [last[0]])))
        for cont in last[1:]:
            print(fmt.format(*([""] * (len(cells) - 1) + [cont])))
    print()


# _filetime_to_str: imported from forefst.py (K086) -- one definition.

def _find_boot_offset(image, partition_start):
    if partition_start is not None:
        return int(partition_start, 0) if isinstance(partition_start, str) else partition_start
    ps, msg = find_refs_partition(image)
    if ps is not None:
        return ps
    die(msg)


# ── C1.8: these three were byte-identical copies of forefst's. The logic now lives ONCE in forefst; the
# wrappers below exist only to pass this tool's PROG, because each body reads the module-level program name
# and importing them bare would make refsanalysis print "forefst: error:". Identical source is not the same
# as interchangeable when the body reads a module global.
def die(msg):
    return _forefst.die(msg, PROG)


def _not_found(what):
    """A3 M-3: a lookup that found nothing. When this run recorded metadata it could not read (a skip or an unreadable
    page), "not found" is not evidence of absence: the command says so and exits 2 (the examiner must look) -- a
    zeroed Object-Table root made `details` and `upcase` exit 1 with a bare "not found". Otherwise it is the plain
    error it always was (exit 1)."""
    if _metadata_incomplete():                 # one test with forefst `details` (N348)
        print(f"{PROG}: error: {what}; part of the metadata could not be read in this run (see the warnings), so "
              f"this is not evidence that it is absent", file=sys.stderr)
        raise SystemExit(2)
    die(what)


def _int_arg(val, name, base=10):
    return _forefst._int_arg(val, name, base, PROG)


def _parse_args(remaining, flags=None, valued=None):
    return _forefst._parse_args(remaining, flags, valued, PROG)


# N288 (1.14.0): the names are forefst's (`_ROOT_LABELS`), one vocabulary for both tools ('Container Index' here was
# 'Container Index Table', and five more carried a 'Table' forefst does not print)
_CHKP_ROOT_INFO = [(_forefst._ROOT_LABELS[_i], _tid, _src) for _i, (_tid, _src) in enumerate([
    (0x02, "CmsObjectTable, GetGlobalTableRoot(0)"),
    (0x21, "CmsVolume::InitializeVolumeAllocator, root 1"),
    (0x20, "CmsVolume::InitializeVolumeAllocator, root 2"),
    (0x01, "CmsSchemaTable::InitializePhase2, root 3"),
    (0x03, "CmsObjectTable::InitializeParentChildTable, root 4"),
    (0x04, "CmsObjectTable failover root, root 5"),
    (0x05, "CmsBlockRefcount::Initialize, root 6"),
    (0x0B, "CmsVolumeContainer::Initialize, root 7 — BOOTSTRAP"),
    (0x0C, "CmsVolumeContainer::Initialize, root 8 — BOOTSTRAP"),
    (0x06, "CmsSchemaTable failover root, root 9"),
    (0x0E, "CmsVolumeContainer::InitializeIndex, root 10"),
    (0x0F, "CmsIntegrityState::GetIntegrityStateTable, root 11"),
    (0x22, "CmsVolume::InitializeGlobalSAATables, root 12"),
])]

# TableId (page+0x48, TableIdLow) -> canonical name. The CHKP root array above is the conventional
# index->TableId order, but the failover pair {0x0B,0x0C} at roots {7,8} (and root 12) is NOT bound to
# a fixed index->TableId order (finding #337): win11refs2tmillionsofactions carries roots 7/8 swapped
# (7->0x0C, 8->0x0B) and root 12 -> 0x0B. The chkp display must read the ON-DISK TableId, not assume it.
_TID_TO_NAME = {tid: name for (name, tid, _) in _CHKP_ROOT_INFO}

_CT_ROOT_INDICES = {7, 8, 12}

# The checkpoint flags are named by forefst's `chkp_flags_decoded` (single source of truth -- audit 4.2: the two tools
# must print the same name for the same checkpoint flag; a divergent copy showed the examiner a discrepancy not on disk).

_KNOWN_OIDS = _forefst._KNOWN_OIDS          # C1-10 (1.14.0): forefst's one table of the system objects' names



def _fs_meta_child_text(ch):
    """Q33 (1.14.0): an OID 0x520 child's details as both listings print them -- its file id (value+0x80 = $SI+0x58)
    and, for the Change Journal, its stream count."""
    parts = []
    if ch.get("file_id") is not None:
        parts.append("file id 0x%x" % ch["file_id"])
    if ch.get("stream_count") is not None:
        parts.append("streams: %d" % ch["stream_count"])
    return "  (%s)" % ", ".join(parts) if parts else ""


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

_CHECKSUM_ALGO_MAP = {0: "none", 2: "CRC64", 4: "SHA-256", 5: "XXH64"}  # K24 (1.14.0): forefst's names; Q7

# N493 (1.14.0): the boot sector's volume flags (+0x2C) in the words of what refs.sys does with each bit (26100.9444:
# RefsSetBreakOnCorrupt sets / clears 0x01, a writable mount sets 0x02, MsKmeUpdateBootSector sets 0x10 when it posts a
# salvage event, InitializeVcbFromBootSector reads the checksum selector at +0x2A only under 0x40 and copies 0x20 into
# the value RefsHardlinksSupported tests (VCB+0x2ACC = 0x38 | bit; 26100.8115 and .9444, review E1, RE1-11),
# RefsMarkVolumeForUpgrade sets 0x80 and RefsUpgradeVersionInBootSector clears it); 0x04 has no reading. One table for
# `boot` and `bootedit read`: the two commands named the bits with two sets of words of their own ("mounted",
# "valid-ReFS", "recovery/dirty", "Win11-boot-behavior" / "base", "format-time", "Win11-cap1", "Win11-cap2").
_VOLUME_FLAG_BITS = {
    0x01: "set / cleared by RefsSetBreakOnCorrupt",
    0x02: "set by a writable mount",
    0x04: "meaning not decoded",
    0x10: "set by MsKmeUpdateBootSector (salvage)",
    0x20: "hard links supported (refs.sys 26100 reads it at mount: RefsHardlinksSupported)",
    0x40: "refs.sys reads the checksum selector at +0x2a",
    0x80: "upgrade requested (RefsMarkVolumeForUpgrade; cleared when the version is upgraded)",
}


# N493 / review RE1-20: a zero container size (+0x40), one text for `boot` and `bootedit read` (N365's reading)
_CONTAINER_ZERO_TEXT = "0x0 (refs.sys uses 64 MiB, and a writable mount writes it here)"


def _checksum_selector_text(algo, flags):
    """N493 / N154 (b): +0x2a as refs.sys reads it -- only when the flags carry 0x40 (InitializeVcbFromBootSector,
    26100.8115 / .9444, Insider 29574; 17134 does not read +0x2a; no 3.7-3.10 driver was read); otherwise those drivers'
    selector is 2 (CRC64) whatever the field holds."""
    name = _CHECKSUM_ALGO_MAP.get(algo, "unknown")
    if flags & 0x40:
        return "0x%x (%s)" % (algo, name)
    return ("0x%x (not read: flags bit 0x40 is clear, so refs.sys 26100 and Insider 29574 use selector 2, CRC64; "
            "17134 does not read +0x2a)" % algo)


def _extended_guid_text(guid_raw):
    """N493: +0x48. Zero: none recorded -- a volume formatted before 3.10 carries none (and keeps none when upgraded).
    refsutil fixboot zeroes it too, which `bootedit repair` diagnoses: a display of a healthy volume does not name it."""
    if guid_raw != b"\x00" * 16:
        return _guid_to_text(guid_raw)
    return _guid_to_text(guid_raw) + " (none recorded: a volume formatted before ReFS 3.10 carries none)"     # K4

# N288 (1.14.0): the root names of `summary --json` are forefst's list (this was a copy of it)
_ROOT_LABELS = _forefst._ROOT_LABELS



# N543 (c) (1.14.0): the bits' names for the flag-word form (K14: `0x66 (WritableMount|0x4|...)`), from what refs.sys
# does with each (`_VOLUME_FLAG_BITS`, which `boot -v`'s meaning line keeps); 0x04 has no reading, so no name
_VOLUME_FLAG_NAMES = {0x01: "BreakOnCorrupt", 0x02: "WritableMount", 0x10: "SalvageEvent", 0x20: "HardLinksSupported",
                      0x40: "ChecksumSelectorRead", 0x80: "UpgradeRequested"}


def _volume_flags_text(value):
    """N543 (c): the volume flags in the flag-word form."""
    return _forefst.flag_text(value, _VOLUME_FLAG_NAMES)


def _volume_flags_description(value):
    """N493: each bit set, with what refs.sys does with it (`_VOLUME_FLAG_BITS`); a bit outside the table is said."""
    parts = [f"0x{1 << i:x} {_VOLUME_FLAG_BITS.get(1 << i, 'not catalogued')}" for i in range(32) if value & (1 << i)]
    return "; ".join(parts) if parts else "none"


def _bit_list(value):
    bits = [f"0x{(1 << i):x}" for i in range(32) if value & (1 << i)]
    return ", ".join(bits) if bits else "none"


# ═══════════════════════════════════════════════════════════════════════
#  SUMMARY — Volume overview
# ═══════════════════════════════════════════════════════════════════════

_summary_human_size = _forefst._human_size   # K6 (1.14.0): one reading-aid size for both tools

# NOTE: the file-system-content counts for `summary` now come from forefst.fs_content_summary (single
# source of truth: correct F5+B2 is_resident + FN_LINK_002 hard-link grouping). The former local
# `_count_dir_entries` walk — a duplicate with the old length-only is_resident — was removed.


# CB-4 (1.14.0, the conformance batch): the policy's format number names a codec by the numbering of the driver that
# writes the volume's format, and the two drivers read number them differently (read twice, KNOWLEDGE_INTAKE A66):
# 17134 (ReFS 3.4) 2 LZNT1, 3 XPRESS, 4 XPRESS_HUFF, 5 LZX; 26100.x and Insider 29574 (ReFS 3.14) 1 LZ4, 2 ZSTD,
# 3 LZ4QAT. 1.13.1 named 2 "Zstd" on every volume. No driver of ReFS 3.5-3.10 was read, so there the number is given
# as it is. Measured 2026-11-05: on the corpus only v3.14 volumes carry a format other than 0 (1 on 7, 2 on 3).
_COMP_FMT_BY_DRIVER = {(3, 4): {0: "none", 2: "LZNT1", 3: "XPRESS", 4: "XPRESS_HUFF", 5: "LZX"},
                       (3, 14): {0: "none", 1: "LZ4", 2: "ZSTD", 3: "LZ4QAT"}}


def _comp_fmt_name(fmt, vmaj, vmin):
    """CB-4: the codec a compression policy's format number names on a ReFS `vmaj`.`vmin` volume (`_COMP_FMT_BY_DRIVER`)."""
    if fmt == 0:
        return "none"
    table = _COMP_FMT_BY_DRIVER.get((3, 14) if (vmaj, vmin) >= (3, 14) else (vmaj, vmin))
    if table is None:
        return "format %d (no ReFS %d.%d driver was read: the codec it numbers %d is not known)" % (fmt, vmaj, vmin, fmt)
    return table.get(fmt, "unknown (0x%x)" % fmt)


def _ct_policy(page, root=None, lcn=None, digest_ok=None):
    """N215: the compression policy record of a Container-Table root page -> (policy dict, None) or (None, why).

    The record (format u16 +0xa4, level i16 +0xa6, chunk size u32 +0xa8, then +0xd4..+0xe0) is read whatever the
    word at +0xa0 holds: that word is a FLAGS word (E90: 0x07 on v3.4, 0x0f on v3.7+; the driver sets bit 3 above
    volume version 0x306), not a marker that a policy exists. `summary` and `containers` read the policy only when
    it was 0x0f, so a v3.4 volume -- and any volume whose flags word differs -- printed "Compression: Not configured"
    without reading the policy at all.
    The record lies in the root page's descriptor (page+0x50 up to the index header at 0x50 + le32(page, 0x50)). Where
    the descriptor ends before +0xe4 the record is not there, and nothing is read. N352: the reason then says what was
    read -- the root the page was read for, its LCN and table id (page+0x48), and (`digest_ok`, from the caller)
    whether the page matches the digest the checkpoint copy in use records for that root -- and states no cause. On the
    four 2 TiB volumes of the corpus both root pages fail the copy in use's digest (CB-11: the page read is root 7's,
    table id 0xc; 1.13.1 read root 8's, 0xb, whose descriptor ends at +0x58); why is not established (the root page of
    their sibling volume v2 is an inner node too, and its policy reads), so no cause is given."""
    if len(page) >= 0xE4 and 0x50 + le32(page, 0x50) >= 0xE4:
        return {"format": le16(page, 0xA4), "level": struct.unpack_from("<h", page, 0xA6)[0],
                "chunk": le32(page, 0xA8)}, None
    what = "the Container-Table root page"
    if root is not None and lcn is not None and len(page) >= 0x50:
        what += " read for root %d (LCN 0x%x, table id 0x%x)" % (root, lcn, le64(page, 0x48))
    why = (what + " is shorter than the policy record" if len(page) < 0xE4 else
           what + " holds no policy record where this tool reads it (its descriptor ends at +0x%x)"
           % (0x50 + le32(page, 0x50)))
    if digest_ok is False:
        why += "; the page does not match the digest the checkpoint copy in use records for root %d" % root
    return None, why


def _ct_root_read(roots, ct_vlcns, copy):
    """N352: (root, lcn, digest_ok) for `_ct_policy` -- which root (7 or 8) the Container-Table root page was read for
    (`_select_ct_root`: the copy refs.sys reads, CB-11), its first LCN, and whether it matches the digest `copy` (the checkpoint
    copy in use, from checkpoint_select) records for that root: False when listed in its `root_fail`, None when the
    root could not be checked or is not known."""
    lcn = ct_vlcns[0] if ct_vlcns else None
    ri = next((i for i in (7, 8) if i < len(roots) and roots[i] and list(roots[i]) == list(ct_vlcns)), None)
    if ri is None or copy is None:
        return ri, lcn, None
    if ri in {i for i, _w in copy["root_fail"]}:
        return ri, lcn, False
    return ri, lcn, (None if ri in copy["root_unchecked"] else True)


def cmd_summary(image, remaining, partition_start, plus_mode=False):
    # PLAN section 10.2 A1 (1.14.0): the MLog section of forefst's `summary` document, with its option and default
    args = _parse_args(remaining, flags=["--json", "--mlog", "-v", "--verbose"])

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        # N306 (1.14.0, decision 36 Q8 B): the facts are forefst `summary`'s document -- one builder
        # (`summary_document`) for both tools' `summary` -- and this command adds its own fields to it (compression,
        # the schema tables, the 0x500 verify block's location, symlinks). It computed each fact again and left out a dozen
        # (the serial, the image size, the hashes, the backups, the journal ids, the version evidence).
        _fast, red, _walk, doc = _forefst.summary_document(f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns,
                                                           image, plus=True,
                                                           mlog=bool(args["mlog"] or args["v"] or args["verbose"]))
        summary = dict(doc)
        bpc = summary["container_size"]
        bpc_from_vbr = summary.get("container_size_from") == "VBR+0x40"
        _cu = list(summary.get("counts_unreadable") or [])        # N338/N345: the counts that are not a full count

        # Schema table count: the distinct schema ids of root 3 (C15: the value is an 80-byte BINARY definition, not
        # UTF-16 text; it is not decoded). N345: A3's convention (`table_row_count`).
        schema_tables = 0
        if len(roots) > 3 and roots[3]:
            schema_tables, _bad = table_row_count(
                lambda: {le32(kd, 0) for kd, vd in walk_bplus(f, ps, cs, tr, roots[3]) if len(kd) >= 4 and len(vd) >= 4},
                "summary: schema table", "table 3")
            if _bad:
                _cu.append("schema_tables")
        summary["schema_tables"] = schema_tables

        # E178 (1.14.0): the 0x540 key of the volume information (OID 0x500) locates the verify block, a copy of the
        # 448-byte volume-information blob: u64 +0x00 its first cluster, u64 +0x08 its cluster count
        # (`InitializeVerifyBlock`, 26100.9444 :483918-483958). 1.13.1 printed +0x00 (a u32) as a "Schema count".
        _dmg500, _n500 = _forefst._walk_damage_count(), 0
        _vblock = None
        if 0x500 in obj_map:
            try:
                for kd, vd in walk_bplus(f, ps, cs, tr, obj_map[0x500]):
                    _n500 += 1
                    if len(kd) >= 2 and le16(kd, 0) == 0x0540 and len(vd) >= 16:
                        _vblock = (le64(vd, 0), le64(vd, 8))
            except Exception as _e: _skip_note("summary: volume info", "table 0x540", _e)
        _vd_why = (object_absent_reason(obj_map, 0x500) if 0x500 not in obj_map else
                   table_unread_text("the volume information table (OID 0x500)", _dmg500, _n500))

        # Compression policy from the Container-Table root page (the copy refs.sys reads, `container_table_copy`, CB-11).
        # N215: read whatever the flags word at +0xA0 holds (E90: 0x07 on v3.4, 0x0F on v3.7+ -- a flags word, not
        # a policy marker); it is not read only where the root page carries no policy record (`_ct_policy`).
        compression = "unknown: the Container-Table root page could not be read"
        _sel = checkpoint_select(f, ps, cs, chkp_lcns, require_roots=True)
        _cp = _sel["in_use"]
        _ct_root = _select_ct_root(f, ps, cs, roots, _cp["raw"] if _cp else None)      # CB-11: bootstrap's copy
        if _ct_root:
            try:
                _pol, _why = _ct_policy(_seek_read(f, ps + _ct_root[0] * cs, cs),                  # N371
                                        *_ct_root_read(roots, _ct_root, _cp))                      # N352
                compression = _comp_fmt_name(_pol["format"], vmaj, vmin) if _pol else \
                    "unknown: " + _why
            except Exception as _e:
                _skip_note("summary: compression format", "container table page", _e)
        summary["compression"] = compression

        vcontra = list(summary.get("version_contradiction") or [])
        notes = list(summary.get("redundancy_notes") or [])

        if plus_mode:
            if _vblock:
                # K1 (decisions 35, 38): an LCN in JSON is a hex string; the count an integer
                summary["verify_block_lcn"], summary["verify_block_clusters"] = "0x%x" % _vblock[0], _vblock[1]
            # Symlink count from the reparse index (tag at key offset 4). N345: A3's convention, as the reparse-index
            # count -- this second walk of the same table printed "Symlinks: 0" under "Reparse index: unreadable".
            symlink_count = 0
            if 0x540 in obj_map:
                symlink_count, _bad = table_row_count(
                    lambda: [1 for kd, _vd in walk_bplus(f, ps, cs, tr, obj_map[0x540])
                             if len(kd) >= 8 and le32(kd, 4) == 0xA000000C],
                    "summary: symlink count", "table 0x540")
                if _bad:
                    _cu.append("symlinks")
            elif _metadata_incomplete():
                symlink_count = None
                _cu.append("symlinks")
            summary["symlinks"] = symlink_count
        summary["counts_unreadable"] = sorted(set(_cu))
        hs = _summary_human_size

        _rc = 2 if (red or vcontra) else 0
        if args["json"]:
            _print_json(summary, _forefst._SUMMARY_KEYS)
            return _rc

        w = 78
        print("=" * w)
        print("ReFS Volume Summary" + (" (extended)" if plus_mode else ""))
        print("=" * w)
        print(f"  Image:              {summary['image']}")
        print(f"  ReFS version:       {summary['refs_version']}")
        if vcontra:
            # N265 / N409: forefst `summary`'s state and sentences, in its form
            print(f"  Volume state:       {VERSION_CONTRADICTED_STATE}")
            for _t in vcontra:
                print(f"      • {_t}")
        print(f"  Volume GUID:        {summary['volume_guid']}")
        print("  Volume label:       %s" % (summary["volume_label"] if summary.get("volume_label") is not None else
                                             "not determined: %s" % summary.get("VolumeLabelUndetermined", "")))
        print(f"  Volume size:        {_forefst.bytes_text(summary['volume_size_bytes'])}")
        print(f"  Cluster size:       {_forefst.size_text(cs)}")                                     # K7
        print(f"  Container size:     {_forefst.size_text(bpc)}" + ("" if bpc_from_vbr else CONTAINER_SIZE_DEFAULT_TAG))
        print(f"  Checksum:           {summary['checksum']}"
              + (f" ({summary['ChecksumSelectorNote']})" if summary.get('ChecksumSelectorNote') else ""))   # E136
        print(f"  Compression:        {summary['compression']}")
        print()
        print("-" * w)
        print("Checkpoint")
        print("-" * w)
        print(f"  Virtual clock:      {summary['checkpoint_vc']}")
        if _cp is not None:
            print(f"  Copy in use:        LCN 0x{_cp['lcn']:x}")
        print(f"  Flags:              {summary['checkpoint_flags']}")
        print(f"  Containers mapped:  {'unreadable' if summary['containers_mapped'] is None else summary['containers_mapped']}")
        print()
        print("-" * w)
        print("File System Content")
        print("-" * w)
        print(f"  Directories:        {summary['directories']}")
        print(f"  Files:              {_forefst.files_count_text(summary)}")          # N149 / C3: forefst's line
        print(f"  Names:              {_forefst.names_count_text(summary)}")          # PLAN 10.2 A7: forefst's line
        print(f"  Total file size:    {_forefst.bytes_text(summary['total_file_size_bytes'])}")
        print(f"  Security descs:     {count_text(summary, 'security_descriptors')}")          # N338
        print(f"  Oldest timestamp:   {summary['oldest_timestamp'] or '(none)'}")
        print(f"  Newest timestamp:   {summary['newest_timestamp'] or '(none)'}")
        print()
        print("-" * w)
        print("Global Root Tables")
        print("-" * w)
        _unread = set(summary["root_tables_unreadable"])
        for name, count in summary["root_table_rows"].items():
            if count is None or name in _unread:
                # A3: this table's pages could not be read; "0 rows" reported a destroyed table as an empty one
                print(f"  {name:<28} {'unreadable':>10}  (pages could not be read — NOT an empty table)")
            else:
                print(f"  {name:<28} {count:>6} {'row' if count == 1 else 'rows'}")          # N596

        if plus_mode:
            print()
            print("-" * w)
            print("Volume Detail (OID 0x500)")
            print("-" * w)
            if "volume_version" in summary:
                print(f"  Volume version:     {summary['volume_version']}")
                print(f"  Driver version:     {summary['driver_version']}")
                print(f"  Volume created:     {summary['volume_create_time'] or '(none)'}")
                print(f"  Last mount (rw):    {summary['volume_last_writable_mount_time'] or '(none)'}")
                if summary.get("verify_block_lcn") is not None:
                    print(f"  Verify block:       LCN {summary['verify_block_lcn']}, "
                          f"{_forefst.count_noun(summary['verify_block_clusters'], 'cluster')} (a copy of the volume information)")
            elif _vd_why:
                # N358 (Q11): OID 0x500 not read -- not determined, not "no data"
                print(f"  (not determined: {_vd_why})")
            else:
                print("  (no volume detail data in OID 0x500)")
            print()
            print("-" * w)
            print("FS Metadata Directory (OID 0x520)")
            print("-" * w)
            fm = summary.get("fs_metadata", {})
            # N358: no row of a table that was not read is "unknown", not 0 (the reason is on the Children line)
            print("  Rows:               %s" % ("unknown" if fm.get("usn_journal") is None and not fm.get("rows")
                                                else fm.get("rows", 0)))
            fm_children = fm.get("children", [])
            if fm_children:
                # Q33 (1.14.0): value+0x80 is the child's file id ($SI+0x58), not a flag word (fs_metadata_read)
                for ch in fm_children:
                    print(f"    {ch['name']}{_fs_meta_child_text(ch)}")
            elif fm.get("usn_journal") is None:
                # N358: the table was not read (fs_metadata_read's `not_read`) -- unknown, not "(none)"
                print("  Children:           unknown: %s"
                      % fm.get("not_read", "the system metadata table could not be read"))
            else:
                print("  Children:           (none)")
            print(f"  USN Journal:        {usn_state_text(fm)}")          # N246
            print()
            print("-" * w)
            print("Extended Metrics")
            print("-" * w)
            print(f"  Reparse index:      {count_text(summary, 'reparse_index_entries', ' entries')}")
            print(f"  Symlinks:           {count_text(summary, 'symlinks')}")                # N345
            print(f"  Snapshot versions:  {summary.get('snapshots', 0)} (across "
                  f"{_forefst.count_noun(summary.get('snapshot_files', 0), 'file')})")             # N596
            print(f"  ADS host files:     {summary.get('ads_entries', 0)}")
            print(f"  Hard-linked:        {_forefst.count_noun(summary.get('hardlink_groups', 0), 'file')} sharing "
                  f"{summary.get('hardlink_names', 0)} names")
            print(f"  Encrypted files:    {summary.get('encrypted_files', 0)}")
            print(f"  Integrity files:    {summary.get('integrity_files', 0)}")
            print(f"  Compressed files:   {summary.get('compressed_files', 0)}")
            print(f"  Trash table:        {count_text(summary, 'trash_table_entries', ' entries')}")
            if "containers_mapped_nonboot" in summary:
                # N245: was "Containers used: 30 / 31 (96.8%)" -- the mapped count read as usage
                _boot = summary.get("containers_mapped_boot_region", 0)
                print(f"  Containers:         {summary['containers_mapped']} mapped "
                      f"({summary['containers_mapped_nonboot']} outside the boot region"
                      + ("; the first is at PLCN 0x0)" if _boot == 1 else "; %d at PLCN 0x0)" % _boot if _boot else ")"))
            if summary.get("capacity"):
                _cc = summary["capacity"]
                print(f"  Space used:         {hs(_cc['used_bytes'])} of {hs(_cc['allocator_covered_bytes'])} "
                      f"({_cc['used_pct']}%) - {hs(_cc['not_allocated_bytes'])} not allocated")
                print("                      (Windows reports less as free: it keeps part in reserve)")
                if _cc.get("length_disagreement"):                         # CB-7
                    print(f"                      NOTE: {_cc['length_disagreement']}")

        print()
        _forefst._print_mlog_section(summary.get("mlog"), w)       # N416 / Q-D D3: forefst `summary`'s MLog section
        for _n in notes:
            print(f"  note: {_n}")
        _print_redundancy_findings(red)
        return _rc

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
        # N344: forefst's boot_sector_copy decides which copy the volume is read from (the primary, or the backup the
        # search finds when the primary fails a boot-sector test: said, exit 2). `boot` decodes sector 0 when it carries
        # the ReFS signature -- the table and `--verify` show what fails in it -- and otherwise the backup read.
        try:
            _bsc = boot_sector_copy(f, bo, fresh=True)
        except OSError as _e:
            die(f"cannot read 512 bytes at 0x{bo:x}: {_e}")
        _prim = _bsc["primary"][:512]
        if _bsc["bytes"] is None and _bsc["error"] and not _bsc["foreign"]:
            die(_bsc["error"])                                  # Q20: no copy found, the range searched named
        _say_boot_sector_copy(_bsc)
        _from_backup = _bsc["source"] == "backup" and _prim[0x03:0x07] != b"ReFS"
        sector, vo = (_bsc["bytes"], _bsc["offset"]) if _from_backup else (_prim, bo)
        # C2-6 (1.14.0): the decoded copy as read for its checksum -- +0x14 bytes when above 512 (`bytes` holds 512)
        _ck_copy = _forefst._boot_copy_read(f, vo) if _from_backup else _bsc["primary"]
        # A4 (decision 20.7): the other copy is examined too, each copy with its own row -- the backup boot sector (the
        # copy read when it is a backup, else sector 0's own last sector: the place forefst's redundancy scan reads
        # it), or, when the backup is the copy decoded, sector 0
        _bk_off = bo if _from_backup else _bsc["backup_offset"]
        _bk_lba = 0 if _from_backup else (
            (_bk_off - bo) // _vbr_bytes_per_sector(_bsc["bytes"] if _bsc["bytes"] is not None else sector)
            if _bk_off is not None else None)
        backup = b""
        if _bk_off is not None:
            try:
                backup = _forefst._boot_copy_read(f, _bk_off)   # N371; C2-6: +0x14 bytes when above 512
            except (OSError, OverflowError) as _e:
                _skip_note("boot", "the backup boot sector", _e)
        _gv = _bsc["bytes"] if _bsc["bytes"] is not None else sector
        if _gv[0x03:0x07] == b"ReFS" and len(_gv) >= 0x28:
            _forefst._say_volume_truncation(f, bo, le32(_gv, 0x20) * le32(_gv, 0x24))    # B3 (Q18)

    if sector[0x03:0x07] != b"ReFS" or sector[0x10:0x14] != b"FSRS":
        if b"-FVE-FS-" in sector[:0x40]:
            die(f"partition at 0x{bo:x} is BitLocker-encrypted")
        die(f"no ReFS boot sector at offset 0x{bo:x}")

    sha = hashlib.sha256(sector).hexdigest()
    vbr_size = struct.unpack("<H", sector[0x14:0x16])[0]
    # C2-6 (1.14.0): forefst's one checksum of a copy, over its own +0x14 bytes (the copy as read: +0x14 bytes when
    # above 512); 1.13.1 summed the 512 bytes of `sector` (IndexError when +0x14 is above 512)
    stored_chk, computed_chk = _forefst.boot_sector_checksum(_ck_copy)
    chk_ok = computed_chk is not None and stored_chk == computed_chk
    total_sectors = le64(sector, 0x18)
    bps = le32(sector, 0x20); spc = le32(sector, 0x24)
    cluster_size = bps * spc; volume_size = total_sectors * bps
    major = sector[0x28]; minor = sector[0x29]
    chk_algo = struct.unpack("<H", sector[0x2A:0x2C])[0]
    flags = le32(sector, 0x2C)
    serial = le64(sector, 0x38)
    bpc = le64(sector, 0x40)
    guid_raw = sector[0x48:0x58]
    algo_text = _checksum_selector_text(chk_algo, flags)                       # N493
    guid_text = _extended_guid_text(guid_raw)                                  # N493
    cpc = bpc // cluster_size if bpc and cluster_size else None
    container_count = volume_size // bpc if bpc else None

    def _backup_row():
        # A4 (decision 20.7): the backup boot sector's own checksum row -- a copy that fails its checksum is named.
        # N344: when the backup is the copy decoded above, this is sector 0's row.
        _name, _role = ("checksum_primary", "primary") if _from_backup else ("checksum_backup", "backup")
        if _bk_off is None:
            return [_name, "FAIL", "backup not located: the primary declares no volume size"]
        if len(backup) < 512:
            # N377: the image ends before it -- not read, rather than "no ReFS boot sector"
            return [_name, "FAIL", f"{_role} (LBA {_bk_lba}, offset 0x{_bk_off:x}): not read (the image ends before "
                                   f"it)"]
        if backup[0x03:0x07] != b"ReFS":
            return [_name, "FAIL", f"{_role} (LBA {_bk_lba}, offset 0x{_bk_off:x}): no ReFS boot sector"]
        _bs, _bc = _forefst.boot_sector_checksum(backup)                      # C2-6: over its own +0x14
        return [_name, _ok(_bc is not None and _bs == _bc),
                f"{_role} (LBA {_bk_lba}, offset 0x{_bk_off:x}): stored=0x{_bs:04x}, computed={_cksum_text(_bc)}"]

    _failed = []                        # decision 25.2 / N354: any row that does not pass (FAIL or WARN) exits 2

    def _version_check():
        # N265 (decision 29's command set): the boot sector's version as forefst `summary` tests it (`version_findings`,
        # one definition): plausibility from this boot sector, corroboration against $VOLUME_INFORMATION and the
        # checkpoint copy in use's native-format bit, read through forefst's bootstrap -- so a condition of the volume
        # view is said (stderr) and exits 2 here as in every command that reads it. When the volume cannot be read
        # (a boot sector alone, a damaged superblock chain), the corroboration is not made, and the output says so.
        why, vi, flags = None, {}, 0
        try:
            _bf, _bps, _bcs, _btr, _broots, _bom, _bvmaj, _bvmin, _bcl = bootstrap(image, bo)
        except (ValueError, OSError) as _e:
            why = str(_e)
        else:
            try:
                _bsel = checkpoint_select(_bf, _bps, _bcs, _bcl, require_roots=True)
                flags = _bsel["in_use"]["flags"] if _bsel["in_use"] is not None else 0
                vi = read_volume_information(_bf, _bps, _bcs, _btr, _bom, "boot --verify")
                if not vi and 0x500 not in _bom and object_table_read_state(_bom):
                    # N358 (Q11): OID 0x500 not among the rows of an Object Table read in part -- not determined, not
                    # "the volume holds no ... row"
                    why = object_absent_text(_bom, 0x500, "the $VOLUME_INFORMATION row's table")[1]
                elif not vi:
                    why = "the volume holds no readable $VOLUME_INFORMATION row (OID 0x500, key 0x0520)"
            finally:
                _bf.close()
        return version_findings(major, minor, flags, vi), why

    def _emit_verify():
        # --verify consistency table. Factored out so it runs on EVERY render path (it used to be
        # unreachable without -v, because the verbose==0 paths return before it — contract bug fix 2026-06-20).
        checks = [
            ["jump_is_zero", _ok(sector[0:3] == b"\x00\x00\x00"), f"stored={_hexbytes(sector[0:3])}"],
            ["fs_name_is_ReFS", _ok(sector[3:7] == b"ReFS"), f"stored={_ascii_clean(sector[3:0xB])}"],
            ["reserved_0x0B_zero", _ok(sector[0xB:0x10] == b"\x00" * 5), f"stored={_hexbytes(sector[0xB:0x10])}"],
            ["fsrs_is_FSRS", _ok(sector[0x10:0x14] == b"FSRS"), f"stored={_ascii_clean(sector[0x10:0x14])}"],
            ["vbr_size_is_512", _ok(vbr_size == 512), f"stored={vbr_size}"],
            # N151: the driver's own boot-sector test accepts 512..4096-byte sectors (RefsIsBootSectorOurs:
            # bps - 0x200 < 0xe01, in every decompiled build from 17134 to 29574). `bps_is_512` failed every
            # healthy 4Kn volume, which with an exit code on FAIL would be a false finding on each of them.
            ["bps_in_driver_range", _ok(512 <= bps <= 4096), f"stored={bps} (the driver accepts 512..4096)"],
            ["checksum_match", _ok(chk_ok),
             (f"backup (LBA {(vo - bo) // _vbr_bytes_per_sector(sector)}, offset 0x{vo:x})" if _from_backup else
              f"primary (LBA 0, offset 0x{bo:x})") + f": stored=0x{stored_chk:04x}, computed={_cksum_text(computed_chk)}"],
            _backup_row(),
        ] + ([
            # N354 (decision 29): VBR+0x40 = 0 is ONE finding, worded neutrally with forefst's shared text (a WARN row:
            # exit 2), not two FAIL rows -- whether a zero is aligned is no second condition. N364 (T4): the text is
            # printed below the table, so the table is not padded to its width.
            ["container_nonzero", "WARN", "stored=0x0 (the finding is printed below the table)"],
        ] if bpc == 0 else [
            ["container_nonzero", _ok(bpc != 0), f"stored=0x{bpc:x}"],
            ["container_aligned", _ok(bpc != 0 and cluster_size != 0 and bpc % cluster_size == 0),
             f"container={bpc}, cluster={cluster_size}"],
        ])
        # N265: the version rows; a sentence is printed below the table (N364 T4: the table is not padded to it)
        _vf, _why = _version_check()
        checks.append(["version_plausible", "WARN" if _vf["implausible"] else "OK",
                       f"ReFS {major}.{minor}" + (" (the finding is printed below the table)" if _vf["implausible"] else
                                              " (3.x, minor at most 14)")])
        if _vf["corroborated_by"] is not None:
            checks.append(["version_corroborated", "WARN" if _vf["uncorroborated"] else "OK",
                           f"$VOLUME_INFORMATION ReFS {_vf['corroborated_by']}"
                           + (" (the finding is printed below the table)" if _vf["uncorroborated"] else
                              "" if _vf["corroborated_by"] == f"{major}.{minor}" else
                              " (the difference is explained by upgrade evidence)")])
        _failed.extend(c[0] for c in checks if c[1] != "OK")
        print("Verification")
        print("-" * 78)
        _print_table(["Check", "Result", "Details"], checks)
        if bpc == 0:
            print(f"container_nonzero: {container_size_zero_text(vo)}.")
            print()
        _below = [("version_plausible", _vf["implausible"]), ("version_corroborated", _vf["uncorroborated"])]
        for _name, _t in _below:
            if _t:
                print(f"{_name}: {_t}.")
        if _vf["corroborated_by"] is None:
            print(f"version_corroborated: not checked -- the boot sector's version could not be compared with "
                  f"$VOLUME_INFORMATION: {_why}.")
        if any(_t for _n, _t in _below) or _vf["corroborated_by"] is None:
            print()
        for _t in _vf["contradiction"]:
            if _t not in _forefst._VERSION_CONTRADICTED:
                _forefst._VERSION_CONTRADICTED.append(_t)

    def _rc():
        # decision 25.2: `--verify` exits 2 on any row that does not pass (N354: the WARN row of a zero container
        # size too); bare `boot` exits 2 when it prints a checksum FAIL
        return 2 if (_failed or not chk_ok) else 0

    if args["raw"]:
        print(f"\nReFS Boot Sector at offset 0x{vo:x}" + (" (the backup boot sector the volume is read from)"
                                                       if _from_backup else ""))
        print(f"SHA-256: {sha}\n")
        for row_off in range(0, len(sector), 16):
            chunk = sector[row_off:row_off + 16]
            h = " ".join(f"{b:02x}" for b in chunk)
            a = _ascii_clean(chunk)
            print(f"  {row_off:04x}  {h:<48s}  |{a}|")
        print(); return 0

    if verbose == 0 and not show_header:
        print(f"\nReFS Boot Sector at offset 0x{vo:x}" + (" (the backup boot sector the volume is read from)"
                                                       if _from_backup else ""))
        print(f"SHA-256: {sha}\n")
        rows = [
            ["Jump instruction",    "0x0", _hexbytes(sector[0:3]), ""],
            ["FS name (ReFS)",      "0x3", _hexbytes(sector[3:0xB]), _ascii_clean(sector[3:0xB])],
            ["Reserved",            "0xb", _hexbytes(sector[0xB:0x10]), ""],
            ["FSRS identifier",     "0x10", _hexbytes(sector[0x10:0x14]), _ascii_clean(sector[0x10:0x14])],
            ["VBR size",            "0x14", _hexbytes(sector[0x14:0x16]), f"{vbr_size}"],
            ["Checksum",            "0x16", _hexbytes(sector[0x16:0x18]), f"0x{stored_chk:04x} [{_ok(chk_ok)}]"],
            ["Total sector count",  "0x18", _hexbytes(sector[0x18:0x20]), f"{total_sectors} ({_human_size(volume_size)})"],
            ["Bytes per sector",    "0x20", _hexbytes(sector[0x20:0x24]), f"{bps}"],
            ["Sectors per cluster", "0x24", _hexbytes(sector[0x24:0x28]), f"{spc} (cluster = {_human_size(cluster_size)})"],
            ["Version",             "0x28", _hexbytes(sector[0x28:0x2A]), f"{major}.{minor}"],
            ["Checksum algorithm",  "0x2a", _hexbytes(sector[0x2A:0x2C]), algo_text],
            ["Volume flags",        "0x2c", _hexbytes(sector[0x2C:0x30]), _volume_flags_text(flags)],
            ["Reserved",            "0x30", _hexbytes(sector[0x30:0x38]), ""],
            ["Volume serial",       "0x38", _hexbytes(sector[0x38:0x40]), f"0x{serial:016x}"],
            ["Bytes per container", "0x40", _hexbytes(sector[0x40:0x48]), f"{_human_size(bpc)}" if bpc else
             _CONTAINER_ZERO_TEXT],
            ["Extended GUID",       "0x48", _hexbytes(guid_raw), guid_text],
            ["Reserved (trailing)", "0x58", "424 bytes", "NON-ZERO" if any(b != 0 for b in sector[0x58:]) else "all zero"],
        ]
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], rows)
        if verify: _emit_verify()
        return _rc()

    if show_header:
        print("\nReFS Boot Sector / FSRS")
        print("=" * 78)
        print(f"Image:        {_forefst._display_image(image)}")
        print(f"Image size:   {_forefst.bytes_text(os.path.getsize(image))}")             # R2
        print(f"VBR SHA-256:  {sha}")
        print(f"VBR offset:   0x{vo:x}")
        print()

    if verbose == 0:
        rows = [
            ["Jump instruction",    "0x0", _hexbytes(sector[0:3]), ""],
            ["FS name (ReFS)",      "0x3", _hexbytes(sector[3:0xB]), _ascii_clean(sector[3:0xB])],
            ["Reserved",            "0xb", _hexbytes(sector[0xB:0x10]), ""],
            ["FSRS identifier",     "0x10", _hexbytes(sector[0x10:0x14]), _ascii_clean(sector[0x10:0x14])],
            ["VBR size",            "0x14", _hexbytes(sector[0x14:0x16]), f"{vbr_size}"],
            ["Checksum",            "0x16", _hexbytes(sector[0x16:0x18]), f"0x{stored_chk:04x} [{_ok(chk_ok)}]"],
            ["Total sector count",  "0x18", _hexbytes(sector[0x18:0x20]), f"{total_sectors} ({_human_size(volume_size)})"],
            ["Bytes per sector",    "0x20", _hexbytes(sector[0x20:0x24]), f"{bps}"],
            ["Sectors per cluster", "0x24", _hexbytes(sector[0x24:0x28]), f"{spc} (cluster = {_human_size(cluster_size)})"],
            ["Version",             "0x28", _hexbytes(sector[0x28:0x2A]), f"{major}.{minor}"],
            ["Checksum algorithm",  "0x2a", _hexbytes(sector[0x2A:0x2C]), algo_text],
            ["Volume flags",        "0x2c", _hexbytes(sector[0x2C:0x30]), _volume_flags_text(flags)],
            ["Reserved",            "0x30", _hexbytes(sector[0x30:0x38]), ""],
            ["Volume serial",       "0x38", _hexbytes(sector[0x38:0x40]), f"0x{serial:016x}"],
            ["Bytes per container", "0x40", _hexbytes(sector[0x40:0x48]), f"{_human_size(bpc)}" if bpc else
             _CONTAINER_ZERO_TEXT],
            ["Extended GUID",       "0x48", _hexbytes(guid_raw), guid_text],
        ]
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], rows)
        if verify: _emit_verify()
        return _rc()

    if verbose >= 1:
        interpreted = [
            ["fs_name", _ascii_clean(sector[3:0xB])],
            ["fsrs_identifier", _ascii_clean(sector[0x10:0x14])],
            ["vbr_size", f"{vbr_size}"],
            ["format_version", f"{major}.{minor}"],
            ["checksum_algorithm", algo_text],
            ["extended_guid", guid_text],
            ["cluster_size", f"{bps} * {spc} = {cluster_size} ({_human_size(cluster_size)})"],
            ["volume_size", f"{total_sectors} * {bps} = {volume_size} ({_human_size(volume_size)})"],
            ["container_size", f"{_human_size(bpc)} ({_forefst.count_noun(cpc, 'cluster')})" if bpc and cpc else _CONTAINER_ZERO_TEXT],
            ["container_count", f"{container_count}" if container_count else "n/a"],
            ["volume_flags", _volume_flags_text(flags)],                                   # N543 (c)
            ["volume_flags_meaning", _volume_flags_description(flags)],         # what refs.sys does with each bit
            ["volume_serial", f"0x{serial:016x}"],
            ["checksum_stored", f"0x{stored_chk:04x}"],
            ["checksum_computed", f"{_cksum_text(computed_chk)} [{_ok(chk_ok)}]"],
        ]
        print("Interpreted values")
        print("-" * 78)
        _print_table(["Field", "Value"], interpreted)

        structure_rows = []
        for name, offset, size, desc in _VBR_FIELDS:
            end = offset + size - 1
            structure_rows.append([f"0x{offset:x}-0x{end:x}", desc, _hexbytes(sector[offset:offset+size])])
        print("Boot sector structure")
        print("-" * 78)
        _print_table(["Byte range", "Description", "Raw value"], structure_rows)

    if verify:
        _emit_verify()

    if verbose >= 2:
        print("Verbose calculations")
        print("-" * 78)
        print(f"  VBR offset     = 0x{vo:x}")
        print(f"  VBR SHA-256    = {sha}")
        print(f"\n  cluster_size   = {bps} * {spc} = {cluster_size} ({_human_size(cluster_size)})")
        print(f"  volume_size    = {total_sectors} * {bps} = {volume_size} ({_human_size(volume_size)})")
        if bpc:
            print(f"\n  container_size = {_forefst.size_text(bpc)}")            # R3
            print(f"  clusters/cont  = {cpc}")
            print(f"  container_cnt  = {container_count}")
        print(f"\n  volume_flags   = {_volume_flags_text(flags)}")
        print(f"  bits set       = {_bit_list(flags)}")
        print(f"  meaning        = {_volume_flags_description(flags)}")
        print(f"\n  checksum algo  = ROR1+ADD over 0x3..{vbr_size}, skip 0x16-0x17")   # R4 (review S4)
        print(f"  stored         = 0x{stored_chk:04x}")
        print(f"  computed       = {_cksum_text(computed_chk)}")
        print(f"\n  format GUID    = {guid_text}")
        _gp = gpt_partition_detail(image)
        if _gp:
            print(f"\n  GPT partition  = #{_gp['index']} '{_gp['name']}'")
            print(f"  partition LBA  = {_gp['first_lba']}-{_gp['last_lba']}")
            print(f"  partition size = {_forefst.bytes_text(_gp['size_bytes'])}")           # R2
        print()

    return _rc()


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
        # N344: the boot sector the volume is read from (forefst's boot_sector_copy: the primary, or the backup the
        # search finds when the primary fails a boot-sector test -- said, exit 2); none: exit 1 naming the range searched
        try:
            _bsc = boot_sector_copy(f, bo, fresh=True)
        except OSError as _e:
            die(str(_e))
        if _bsc["bytes"] is None:
            die(_bsc["error"] if _bsc["error"] else str(_bsc.get("primary_exc") or "not ReFS"))
        _say_boot_sector_copy(_bsc)
        sector = _bsc["bytes"]
        try:
            cs = _forefst.vbr_cluster_size(sector, _bsc["offset"])   # N383: parse_vbr's bound, a clean exit 1
        except ValueError as _e:
            die(str(_e))
        _forefst._say_volume_truncation(f, bo, cs)                     # B3 (Q18): stderr, once per run

        # C25 / A1: the superblock copy shown is the one the volume is read from -- forefst's parse_supb, which
        # falls back to refs.sys's choice of backup when the primary fails supb_validate (B15: ValidateSuperBlock's
        # tests) and registers it (exit 2). This stopped with "SUPB signature mismatch" (exit 1) on a zeroed
        # primary although both backups were intact. N346: `say=False` -- the condition is said once, by this
        # command's own NOTE below; parse_supb said it on stderr as well.
        try:
            _chkp_list = _forefst_parse_supb(f, bo, cs, say=False)
        except ValueError as _e:
            die(str(_e))
        _supb_lcn = _forefst._SUPB_FELL_BACK.get("used_lcn", SUPB_LCN)
        supb_abs = bo + _supb_lcn * cs
        supb_page = _read_at(f, supb_abs, cs)
        supb_sha = hashlib.sha256(supb_page).hexdigest()
        _fell_back = None
        # N426: this view's findings -- parse_supb above started the view; the run's list also holds the findings of
        # every volume read earlier in the process, which are not this volume's NOTE
        _none_verifies = _forefst._view_findings(_forefst._SUPB_NONE_VERIFIES)
        _unverified = _forefst._view_findings(_forefst._SUPB_UNVERIFIED)
        if _none_verifies:
            # Decisions 26 and 27.1: no copy is valid; parse_supb read a copy that is not (the primary, or the first
            # signed backup) and recorded the finding (exit 2). Checked first: 27.1 is also a fallback.
            _fell_back = "NOTE: %s. Shown below is that copy." % _none_verifies[-1]
        elif _forefst._SUPB_FELL_BACK:
            _fb = _forefst._SUPB_FELL_BACK
            _fell_back = (f"NOTE: the primary superblock at LCN 0x{SUPB_LCN:x} (offset 0x{bo + SUPB_LCN * cs:x}) is "
                          f"not usable ({_fb.get('reason', 'damaged')}); shown below is the "
                          f"backup copy at LCN 0x{_supb_lcn:x} (offset 0x{supb_abs:x}), the copy the volume is "
                          f"read from, "
                          # N364 (B1): what was checked on that copy, as parse_supb said it before N346 moved the
                          # statement here; decision 27.3: a backup whose checksum cannot be verified is said to be one;
                          # B15: a backup without the signature (C2 S-F), and the +0x68 clause of two valid backups
                          + _supb_backup_how(_fb.get("cksum_ok", True), _fb.get("ckname", "-"), _fb.get("sig_ok", True))
                          + ("; " + _fb["rank"] if _fb.get("rank") else "") + ".")
        elif _unverified and not verify:
            # Decision 27.3: the primary is read and its checksum cannot be verified (exit 2 through the finding).
            _fell_back = "NOTE: %s." % _unverified[-1]
        # N346 (1.14.0): with --verify the copy's own WARN row says it (below), with what follows from it -- the NOTE said
        # the same condition a second time
        _unverified_row = bool(_unverified) and verify and not _fell_back
        # A4: every superblock and checkpoint copy with its own self-checksum (forefst's inventory, the same one
        # `summary` and `integrity` read); `--verify` prints one row per copy and exits 2 on any that does not pass.
        _bk = _scan_backup_copies(f, bo, cs, _chkp_list)
        # B15 (Q4; C2 S-E: no exit): the primary is read, and a backup that passes its self-checksum carries another
        # +0x68 -- what refs.sys does with that, as a NOTE (summary, fastsummary and integrity say it in N449's sentence,
        # which `--verify` prints below its table, so the NOTE is left out there: said once)
        _g68_notes = []
        _prim = next((x for x in _bk.get("supb") or [] if x.get("role") == "PRIMARY"), None)
        if _prim is not None and _prim.get("used") and not _fell_back and not verify \
                and _prim.get("Generation") is not None:
            for _x in _bk.get("supb") or []:
                if _x.get("role") != "PRIMARY" and _x.get("cksum_ok") is True and _x.get("Generation") is not None \
                        and _x["Generation"] != _prim["Generation"]:
                    _g68_notes.append("NOTE: +0x68 is %d in the backup superblock (SUPB) at LCN 0x%x (offset 0x%x), "
                                      "which passes its self-checksum, and %d in the primary: %s."
                                      % (_x["Generation"], _x["lcn"], _x.get("byte_offset", 0), _prim["Generation"],
                                         SUPB_CHOICE_RULE_TEXT))
        # B15 (closure B-4.1; ST-S1 (b)): the primary superblock when the volume is read from a backup because the primary
        # passes its self-checksum but fails another superblock test -- `--verify` keeps that primary's FAIL row
        _prim_v = None
        if _supb_lcn != SUPB_LCN and _prim is not None and _prim.get("sig_ok") and _prim.get("cksum_ok") is not False:
            _prim_page = _read_at(f, bo + SUPB_LCN * cs, cs)
            _prim_v = {"self_block": le64(_prim_page, 0x20), "count": le32(_prim_page, 0x74),
                       "where": f"the primary at LCN 0x{SUPB_LCN:x} (offset 0x{bo + SUPB_LCN * cs:x}), not the copy read"}

        raw_guid = supb_page[0x50:0x60]
        guid_text = _guid_to_text(raw_guid) + (" (not set)" if raw_guid == b"\x00" * 16 else "")      # K4
        # N414 (class): the volume signature is forefst's `volume_signature` (CalculateVolumeSignature: the XOR of the
        # GUID's four u32, 1 when that is 0) -- this row computed the XOR alone, 0 where the driver holds 1
        guid_xor = volume_signature(raw_guid)

        sb_version = le64(supb_page, 0x68)
        chkp_off = le32(supb_page, 0x70)
        chkp_cnt = le32(supb_page, 0x74)
        self_off = le32(supb_page, 0x78)
        self_len = le32(supb_page, 0x7C)
        self_block = le64(supb_page, 0x20)
        expected_self = (supb_abs - bo) // cs

        checkpoints = []
        _cnt = chkp_cnt
        if _cnt > 8:   # N3, review E9: clamp a fuzzed/corrupt count (doc: 2) — an unbounded loop would hang the tool
            print(f"[{PROG}] WARNING: SUPB checkpoint-ref count {chkp_cnt} implausible (doc=2); scanning 8", file=sys.stderr)
            _cnt = 8
        for i in range(_cnt):
            block = le64(supb_page, chkp_off + i * 8)
            resolved = bo + block * cs
            chkp_hdr = {}
            if resolved + 0x80 <= img_size:
                h = _read_at(f, resolved, 0x80)
                chkp_hdr = {
                    # N287 (1.14.0): `vc` is +0x60, the clock checkpoint_select compares (it showed +0x10 beside a
                    # marker chosen by +0x60); the page header's +0x10 is its own field
                    "signature": h[0:4], "virtual_clock": le64(h, 0x60), "page_clock": le64(h, 0x10),
                    "self_block": le64(h, 0x20), "alloc_clock": le64(h, 0x68),
                    "major": struct.unpack("<H", h[0x54:0x56])[0],
                    "minor": struct.unpack("<H", h[0x56:0x58])[0],
                }
            checkpoints.append({"index": i+1, "block": block, "resolved": resolved, "chkp": chkp_hdr})

        # A11: the active copy is forefst's checkpoint_select -- the copy the driver uses: superblock slot order,
        # a later copy only if its +0x60 is strictly greater, and never a copy that fails its self-checksum.
        # This used max() over the +0x10 clock of copies it never checked, so a newest copy that FAILED its
        # checksum was marked active while every volume reader used the other one.
        _sel = checkpoint_select(f, bo, cs, [c["block"] for c in checkpoints], require_roots=True)
        # N332 / 27.3 / N341: every condition bootstrap says and exits 2 for (a root 0xC/7/8 of the copy in use that
        # does not verify, a copy in use whose checksum cannot be verified, a +0x10/+0x60 divergence, ...), in
        # forefst's words, recorded (exit 2). The FAILED copies themselves this command marks on its copy lines (N207)
        # -- except in the --raw layout, a hex dump with no such line, where forefst's sentence says them.
        _view = _view_conditions(_sel, cs, said_failed=not args["raw"])
        for c, _c in zip(checkpoints, _sel["copies"]):
            # N374 (T1a): a copy that was read but carries no CHKP signature has no field to decode -- not its clocks,
            # not a version, not a signature rendered as dots: its line says what it is (forefst's shared text)
            # N394 (Q25): also a copy whose read failed -- its line says so with the cause, no `vc=? ac=?` placeholder
            c["unreadable"] = _c.get("unreadable")
            if c["unreadable"]:
                c["chkp"] = {}
            c["cksum_failed"] = _c["cksum_ok"] is False
            # N343 (V-a, as a copy not in use that fails its self-checksum): a copy NOT in use whose root 0xC, 7 or 8
            # does not verify is marked on its line and exits 2; the copy in use's is a `view` condition, said above.
            c["roots_failed"] = (_root_fail_text(_c["root_fail"])
                                 if _c["root_fail"] and _c is not _sel["in_use"] else None)
            # N373 (V-a, C2 N-1 (b)): a copy not in use that refs.sys rejects (forefst `_chkp_rejected_va`, the
            # condition's one test) is marked on its line and exits 2; the rejected newest copy of a stale view and no
            # copy valid are `view` conditions, said above in forefst's words
            c["rejected"] = chkp_reject_clause(_c["record_tests"]) if _chkp_rejected_va(_sel, _c) else None
        latest = checkpoints[_sel["in_use"]["slot"]] if _sel["in_use"] is not None else None
        # N369 (LB19): the newest copy when the volume is not read from it -- a stale view (it FAILED its self-checksum)
        # or N361's shape (its root list cannot be read) -- named by latest_checkpoint (-v) AND latest_identified
        # (--verify), as every other site names it; `_chkp_not_used_why` says why, one text with containers and deleted
        _auth = _sel["authoritative"]
        _newer = checkpoints[_auth["slot"]] if (_auth is not None and _sel["in_use"] is not None
                                                 and _auth is not _sel["in_use"]) else None
        _newer_why = _chkp_not_used_why(_sel, _auth) if _newer is not None else None

        self_desc_raw = _read_at(f, supb_abs + self_off, self_len) if self_off + self_len <= cs else b""
        self_first_qw = le64(self_desc_raw, 0) if len(self_desc_raw) >= 8 else None

    def _ck_row(name, ok, ckname, where):
        # one self-checksum row per copy: OK, FAIL, or WARN when the checksum cannot be verified (N238)
        res = "OK" if ok is True else "FAIL" if ok is False else "WARN"
        what = (ckname or "-") if ok is not None else "cannot be verified (%s)" % (ckname or "-")
        return [name, res, f"{where}: {what}"]

    def _copy_rows():
        rows = []
        for sp in _bk.get("supb") or []:
            _role = "primary" if sp.get("role") == "PRIMARY" else "backup"
            _where = f"LCN 0x{sp['lcn']:x} (offset 0x{sp.get('byte_offset', 0):x})"
            if sp.get("damaged") and sp.get("found_signature") is None:
                # N377 (1.14.0): nothing was read there (the image ends before it): "not read", not "no signature"
                rows.append([f"supb_{_role}_checksum", "FAIL", f"{_where}: not read (no bytes at that address in "
                                                               f"the image)"])
            elif sp.get("damaged"):
                rows.append([f"supb_{_role}_checksum", "FAIL", f"{_where}: no SUPB signature"])
            else:
                rows.append(_ck_row(f"supb_{_role}_checksum", sp.get("cksum_ok"), sp.get("ckname"), _where))
                if _unverified_row and sp.get("used") and sp.get("cksum_ok") is None:
                    rows[-1][2] += ("; the volume is read from this copy, so the volume GUID and the checkpoint list it "
                                    "supplies are not verified")
                if sp.get("FailedTests"):
                    # B15 (Q2): the copy passes its self-checksum but fails another superblock test -- not valid
                    rows.append([f"supb_{_role}_valid", "FAIL", f"{_where}: " + "; ".join(sp["FailedTests"])])
        for i, rec in enumerate(_bk.get("checkpoints") or [], 1):
            _where = f"LCN 0x{rec['lcn']:x} (offset 0x{rec.get('byte_offset', 0):x})"
            if not rec.get("sig_ok") and rec.get("Unreadable"):
                # N374: a hole cannot be verified (its bytes are not in the image: C8 = B); zeros or other bytes fail
                _hole = _chkp_unreadable_hole(rec["Unreadable"]) is not None
                rows.append([f"chkp_{i}_checksum", "WARN" if _hole else "FAIL",
                             f"{_where}: unreadable: {rec['Unreadable']}"])
            elif not rec.get("sig_ok"):
                rows.append([f"chkp_{i}_checksum", "FAIL", f"{_where}: no CHKP signature"])
            else:
                rows.append(_ck_row(f"chkp_{i}_checksum", rec.get("cksum_ok"), rec.get("ckname"), _where))
        # N343 / N361: roots 0xC, 7 and 8 of EVERY checkpoint copy against that copy's digests, one row each -- a copy
        # whose root list cannot be read, or that carries no CHKP signature, gets a row that says so (its checksum row
        # can read OK, so skipping it hid the copy). The result and the words are forefst's `_root_check`, shared with
        # `chkp --verify` (N364, R6: one wording for one check).
        for i, _c in enumerate(_sel["copies"], 1):
            _res, _txt = _root_check(_c)
            rows.append([f"chkp_{i}_roots", _res, f"LCN 0x{_c['lcn']:x} (offset 0x{bo + _c['lcn'] * cs:x}): {_txt}"])
        return rows

    _failed = []                                # decision 25.2: any row that does not pass exits 2

    def _sig_row():
        # the signature of every listed checkpoint copy. G3b (review round 1): a copy that could not be read has no
        # signature to show -- it is said to be unreadable, never shown as '??' -- and the row takes the verdict of that
        # copy's own row: WARN for a hole (its bytes are not in the image, so it cannot be verified: C8 = B), FAIL
        # otherwise (N374: one condition, one verdict)
        res, toks = "OK", []
        for c in checkpoints:
            sig = c["chkp"].get("signature")
            if sig == b"CHKP":
                toks.append(f"#{c['index']}=CHKP")
            elif sig is not None:
                toks.append(f"#{c['index']}={_ascii_clean(sig)}")
                res = "FAIL"
            else:
                toks.append(f"#{c['index']} could not be read")
                if _chkp_unreadable_hole(c.get("unreadable") or "") is None:
                    res = "FAIL"
                elif res == "OK":
                    res = "WARN"
        return ["all_checkpoint_signatures", res, ", ".join(toks)]

    _below = []             # N437: sentences printed below the --verify table (`_payload_row`)

    def _payload_row():
        # N417 / LB50 (A13's comparison, forefst's inventory): every superblock copy that carries a signature against
        # the copy the volume is read from, each with its own LCN and self-checksum masked. A copy whose payload differs
        # fails the row (exit 2, decision 25.2), named with forefst's sentence; two copies that VERIFY and disagree are
        # the redundancy condition LB50 names, and a differing copy that fails its checksum fails its own row as well.
        _sp = _bk.get("supb") or []
        _ref = supb_payload_reference(_sp)
        _diff = [x for x in _sp if x.get("PayloadMatches") is False]
        _cmp = [x for x in _sp if x.get("PayloadMatches") is not None]
        if _ref is None or len(_cmp) < 2:
            return None             # fewer than two signed copies: nothing to compare (the copy rows say why)
        if _diff:
            # N437 (U-5; N364 T4's class): the shared sentence is printed below the table, so the table is not padded
            # to its width (it held the whole sentence: every row of the table 323 columns on the aftercorruption
            # volumes)
            _below.extend("supb_payloads_match: %s." % supb_payload_differs_text(
                x, _ref, verified=supb_pair_verified(x, _ref), extend=bool(_bk.get("SuperblockExtendPattern")))
                for x in _diff)
            return ["supb_payloads_match", "FAIL", "%d of %d copies differ from the copy read (the finding is printed "
                    "below the table)" % (len(_diff), len(_cmp))]
        return ["supb_payloads_match", "OK", "%d copies, equal payloads (each copy's own LCN and self-checksum left out)"
                % len(_cmp)]

    def _emit_verify():
        # --verify consistency table — runs on every render path (used to be unreachable without -v/-H;
        # contract bug fix 2026-06-20).
        _sbm = ["self_block_matches", _ok(self_block == expected_self),
                f"stored=0x{self_block:x}, expected=0x{expected_self:x}"]
        _cc2 = ["checkpoint_count_is_2", _ok(chkp_cnt == 2), f"count={chkp_cnt}"]
        if _prim_v is not None:
            # B15: the copy shown is a backup; a rejected primary that fails the row's test fails the row, named
            if _prim_v["self_block"] != SUPB_LCN:
                _sbm[1] = "FAIL"
                _sbm[2] += f"; {_prim_v['where']}: stored=0x{_prim_v['self_block']:x}, expected=0x{SUPB_LCN:x}"
            if _prim_v["count"] != 2:
                _cc2[1] = "FAIL"
                _cc2[2] += f"; {_prim_v['where']}: count={_prim_v['count']}"
        checks = [
            ["signature_is_SUPB", _ok(supb_validate(supb_page, cs)["sig_ok"]), f"stored={supb_page[:4]!r}"],
            _sbm,
            _cc2,
            # signatures only: each copy's self-checksum is its own row below (was "all_checkpoints_valid", which
            # read OK over a checkpoint that failed its checksum)
            _sig_row(),
            ["in_use_identified", _ok(latest is not None),                        # N355
             (f"#{latest['index']} vc={latest['chkp']['virtual_clock']}"
              + (f" (in use); the newer #{_newer['index']} vc={_newer['chkp'].get('virtual_clock', '?')} "
                 f"is not used: {_newer_why}" if _newer else "")) if latest else "n/a"],
            ["self_desc_matches", _ok(self_first_qw == self_block),
             f"desc=0x{self_first_qw:x}, block=0x{self_block:x}" if self_first_qw is not None else "n/a"],
            # C14: SHA-256 volumes use a 0x48 self-descriptor (0x68 v3.4 / 0x30 v3.14 CRC64 / 0x48 SHA-256,
            # structure_reference §A + chkp.md). Omitting 0x48 made supb --verify FAIL on clean SHA-256 volumes.
            ["self_desc_known_size", _ok(self_len in (0x30, 0x48, 0x68)), f"0x{self_len:x}"],
        ] + [r for r in (_payload_row(),) if r] + _copy_rows()
        _failed.extend(c[0] for c in checks if c[1] != "OK")
        print("Verification")
        print("-" * 78)
        _print_table(["Check", "Result", "Details"], checks)
        for _t in _below:
            print(_t)

    def _rc():
        # N207 (decision 21): a copy said to have FAILED exits 2; decision 25.2: so does any --verify row that did
        # not pass; N332 / 27.3 / N341: so does a `view` condition of the checkpoint pair (`_view`). A superblock
        # fallback exits 2 through its register, and decisions 26, 27.1 and 27.3 through forefst's `_FINDINGS` (both
        # in forefst rc_escalate).
        return 2 if (_failed or _view or any(c.get("cksum_failed") or c.get("roots_failed") or c.get("rejected")
                                             for c in checkpoints)) else 0

    if _fell_back:
        print(_fell_back)
    for _t in _g68_notes:
        print(_t)
    for _t in _view:
        print("WARNING: %s." % _t)
    if args["raw"]:
        print(f"\nReFS Superblock (SUPB) at offset 0x{supb_abs:x}")
        print(f"SHA-256: {supb_sha}\n")
        for row_off in range(0, min(len(supb_page), 0x200), 16):
            chunk = supb_page[row_off:row_off + 16]
            h = " ".join(f"{b:02x}" for b in chunk)
            a = _ascii_clean(chunk)
            print(f"  {row_off:04x}  {h:<48s}  |{a}|")
        print(); return 0

    if verbose == 0 and not show_header:
        print(f"\nReFS Superblock (SUPB) at offset 0x{supb_abs:x}")
        print(f"SHA-256: {supb_sha}\n")

    if show_header and verbose == 0:
        print("\nReFS Superblock (SUPB)")
        print("=" * 78)
        print(f"Image:            {_forefst._display_image(image)}")
        print(f"SUPB SHA-256:     {supb_sha}")
        print(f"SUPB offset:      0x{supb_abs:x}")
        print(f"Cluster size:     {_forefst.size_text(cs)}")
        print()

    compact_rows = [
        ["Signature",             "0x0", _hexbytes(supb_page[0:4]),              _ascii_clean(supb_page[0:4])],
        ["Page header",           "0x0", _hexbytes(supb_page[0:16]) + " ...",   ""],
        ["Volume GUID",           "0x50", _hexbytes(raw_guid),                   guid_text],
        ["GUID XOR (vol sig)",    "   -", "",                                    f"0x{guid_xor:08x}"],
        ["Superblock version",    "0x68", _hexbytes(supb_page[0x68:0x70]),       f"{sb_version}"],
        ["Checkpoint refs offset","0x70", _hexbytes(supb_page[0x70:0x74]),       f"SUPB+0x{chkp_off:x}"],
        ["Checkpoint refs count", "0x74", _hexbytes(supb_page[0x74:0x78]),       f"{chkp_cnt}"],
        ["Self-desc offset",      "0x78", _hexbytes(supb_page[0x78:0x7C]),       f"SUPB+0x{self_off:x}"],
        ["Self-desc length",      "0x7c", _hexbytes(supb_page[0x7C:0x80]),       f"0x{self_len:x} ({self_len})"],
    ]

    def _failed_note(c):
        return ("  (self-checksum FAILED)" if c.get("cksum_failed") else "") + \
            ("  (%s)" % c["roots_failed"] if c.get("roots_failed") else "") + \
            ("  (%s)" % c["rejected"] if c.get("rejected") else "")                              # N343, N373

    if verbose == 0:
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], compact_rows)
        for c in checkpoints:
            ch = c["chkp"]
            marker = " *" if latest and c["index"] == latest["index"] else ""
            if c.get("unreadable"):
                print(f"  CHKP #{c['index']}: cluster 0x{c['block']:x} -> 0x{c['resolved']:x}  unreadable: "
                      f"{c['unreadable']}")
                continue
            vc = ch.get("virtual_clock", "?"); ac = ch.get("alloc_clock", "?")
            print(f"  CHKP #{c['index']}: cluster 0x{c['block']:x} -> 0x{c['resolved']:x}  vc={vc} ac={ac}{marker}"
                  f"{_failed_note(c)}")
        if latest: print("  (* = the checkpoint copy in use)")                  # N355
        if verify: _emit_verify()
        print(); return _rc()

    if show_header:
        print("\nReFS Superblock (SUPB)")
        print("=" * 78)
        print(f"Image:            {_forefst._display_image(image)}")
        print(f"SUPB SHA-256:     {supb_sha}")
        print(f"SUPB offset:      0x{supb_abs:x}")
        print(f"Cluster size:     {_forefst.size_text(cs)}")
        print()

    if verbose >= 1:
        latest_val = "n/a"
        if latest:
            ch = latest["chkp"]
            latest_val = f"checkpoint #{latest['index']} @ 0x{latest['resolved']:x} (vc={ch['virtual_clock']}, ac={ch['alloc_clock']})"
            if _newer:
                latest_val += (f"; the newer checkpoint #{_newer['index']} @ 0x{_newer['resolved']:x} "
                               + (_newer_why if _newer_why.startswith("FAILED") else
                                  f"(vc={_newer['chkp'].get('virtual_clock', '?')}) is not used: {_newer_why}"))
        interp = [
            ["signature", _ascii_clean(supb_page[0:4])],
            ["self_block", f"0x{self_block:x}"],
            ["expected_self_block", f"0x{expected_self:x}"],
            ["self_block_matches", "yes" if self_block == expected_self else "no"],      # K19 / R11
            ["volume_guid", guid_text],
            ["guid_xor", f"0x{guid_xor:08x}"],
            ["superblock_version", f"{sb_version}"],
            ["checkpoint_count", f"{chkp_cnt}"],
            ["checkpoint_in_use", latest_val],                                    # N355
            ["self_desc_length_profile",
             "0x68 (ReFS 3.4)" if self_len == 0x68 else "0x30 (ReFS 3.14)" if self_len == 0x30 else f"0x{self_len:x}"],
        ]
        print("Interpreted values")
        print("-" * 78)
        _print_table(["Field", "Value"], interp)

        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], compact_rows)

        print("Checkpoint references")
        print("-" * 78)
        for c in checkpoints:
            ch = c["chkp"]
            marker = " <- in use" if latest and c["index"] == latest["index"] else ""   # N355
            print(f"  #{c['index']}: cluster 0x{c['block']:x} -> 0x{c['resolved']:x}")
            if c.get("unreadable"):
                print(f"       unreadable: {c['unreadable']}")
                continue
            sig = _ascii_clean(ch.get("signature", b"????"))
            vc = ch.get("virtual_clock", "?"); ac = ch.get("alloc_clock", "?")
            ver = f"{ch.get('major','?')}.{ch.get('minor','?')}"
            print(f"       sig={sig} vc={vc} ac={ac} ver={ver}{marker}{_failed_note(c)}")
        print()

    if verify:
        _emit_verify()

    if verbose >= 2:
        print("Verbose calculations")
        print("-" * 78)
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
            if c.get("unreadable"):
                print(f"    unreadable: {c['unreadable']}")
            elif ch:
                print(f"    sig={ch.get('signature',b'?')!r} vc={ch.get('virtual_clock','?')} ac={ch.get('alloc_clock','?')}")
                print(f"    self_block=0x{ch.get('self_block',0):x} ver={ch.get('major','?')}.{ch.get('minor','?')}")
            print()
        print(f"  Self-descriptor: offset=0x{self_off:x} len=0x{self_len:x}")
        if self_desc_raw:
            print(f"  Raw: {_hexbytes(self_desc_raw)}")
        print()

    return _rc()


# ═══════════════════════════════════════════════════════════════════════
#  SCHEMA — Schema table reader
# ═══════════════════════════════════════════════════════════════════════

_TABLE_TYPE_NAMES = {
    # N158 / E167 (1.14.0): a schema describes a TABLE, not an attribute: the ids below 0xe000 are the tables a file,
    # a directory and a data stream hold, by format era (structures/schema_table.md). 1.13.1 named them after
    # attributes ($FILE_NAME, $DATA, $EA ...), which the driver's schema set contradicts.
    0x4: "Legacy fixed-format", 0x6: "Legacy variable-format",
    0x110: "File record table, older set (17134)",
    0x120: "Data stream table, older set (17134)",
    0x130: "Directory (the B+-tree of its names)", 0x140: "Security-descriptor table",
    0x150: "Volume-information table", 0x160: "Reparse index",
    0x170: "Directory own-row table, older set (17134)",
    0x180: "File record table (format < 3.6)", 0x190: "Directory own-row table (format < 3.6)",
    0x1a0: "Data stream table (format < 3.11)", 0x1b0: "Role not read (file-record shape)",
    0x1c0: "File record table (format 3.6-3.10)", 0x1d0: "Directory own-row table (format 3.6-3.10)",
    0x1e0: "File record table (format 3.11+)", 0x1f0: "Directory own-row table (format 3.11+)",
    0x200: "Data stream table (format 3.11+)",
    0xe010: "Allocator Table", 0xe030: "Object ID Table",
    0xe040: "Parent-Child Table", 0xe050: "Object Data Table (legacy)",
    0xe060: "Schema Table", 0xe070: "Reserved / Placeholder (legacy)",
    0xe080: "Integrity State Table", 0xe090: "Upcase / Logfile Info Table",
    0xe0b0: "Block RefCount Table", 0xe0c0: "Container Table",
    0xe0d0: "Trash Table", 0xe0e0: "System Directory Entry List (legacy)",
    0xe0f0: "System File Stream (legacy)", 0xe100: "Container Index Table",
    0xe110: "Read Cache Metadata", 0xe120: "Candidate Table (Dirty Ranges)",
    0xe130: "Heat Engine Table", 0xe140: "Volume Attestation Table (Insider)",
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
            # N427 (Q10): a checkpoint root this command needs -- a finding (exit 2), not "cannot run" (exit 1)
            return required_structure_missing("schema", prog=PROG)

        # N338 (1.14.0): a walk that raises is said and recorded (exit 2), never a traceback; a walk that met a page it
        # could not read gives no total (A3's convention: the count says "unreadable", the entries read are listed)
        _unread = "unreadable (pages could not be read — NOT an empty table)"
        _before = _forefst._walk_damage_count()
        try:
            _rows = list(walk_bplus(f, ps, cs, tr, roots[3]))
        except Exception as _e:
            _skip_note("schema", "the Schema Table (checkpoint root 3)", _e)
            print(f"\nReFS Schema Table: {_unread}\n")
            return 2
        _partial = _forefst._walk_damage_count() > _before
        entries = []
        for kd, vd in _rows:
            if len(kd) >= 4:
                entries.append((le32(kd, 0), vd))

        attr_entries = [(k, v) for k, v in entries if k < 0xe000]
        sys_entries = [(k, v) for k, v in entries if k >= 0xe000]

        if show_header:
            print("=" * 78)
            print("ReFS Schema Table")
            print("=" * 78)
            print(f"  Image:             {_forefst._display_image(image)}")
            print(f"  ReFS version:      {vmaj}.{vmin}")
            print(f"  Cluster size:      {_forefst.size_text(cs)}")
            print(f"  Total entries:     {_unread + '; %d read' % len(entries) if _partial else len(entries)}")
            print()
        else:
            print("\nReFS Schema Table\n")

        # N288 (1.14.0): one name for u32[8] in both views -- its meaning is not established, so not "property_count"
        # (`-v`'s word; on win11refsmini the Allocator schema holds 0xe010, its own id, there); the self id in hex
        # review RE1-20 / 1.14.0: the name column as wide as the longest name
        _nw = max([40] + [len(v) for v in _TABLE_TYPE_NAMES.values()])
        fmt = "  {:<8} {:<%d} {:>10} {:>8}" % _nw
        print("-" * 78)
        print(f"System table schemas ({_forefst.count_noun(len(sys_entries), 'entry', 'entries')})")
        print("-" * 78)
        print(fmt.format("TypeID", "Name", "u32[8]", "SelfID"))
        print("  " + "-" * (len(fmt.format("", "", "", "")) - 2))
        for key, vd in sorted(sys_entries):
            name = _TABLE_TYPE_NAMES.get(key, f"Unknown (0x{key:x})")
            props = le32(vd, 32) if len(vd) >= 36 else 0
            level = le32(vd, 36) if len(vd) >= 40 else 0
            print(fmt.format(f"0x{key:x}", name, str(props), f"0x{level:x}"))

        print()
        print("-" * 78)
        print(f"Object and table schemas ({_forefst.count_noun(len(attr_entries), 'entry', 'entries')})")
        print("-" * 78)
        print(fmt.format("TypeID", "Name", "u32[8]", "SelfID"))
        print("  " + "-" * (len(fmt.format("", "", "", "")) - 2))
        for key, vd in sorted(attr_entries):
            name = _TABLE_TYPE_NAMES.get(key, f"Unknown (0x{key:x})")
            props = le32(vd, 32) if len(vd) >= 36 else 0
            level = le32(vd, 36) if len(vd) >= 40 else 0
            print(fmt.format(f"0x{key:x}", name, str(props), f"0x{level:x}"))

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
                    print(f"    u32[8] (+0x20):      {vals[8]}")                     # N288: one name
                    print(f"    self_schema_id:      0x{vals[9]:x}")
                    print(f"    self_schema_id(dup): 0x{vals[10]:x}")

        if verbose >= 2:
            print(f"\n{'-'*78}\nRaw schema values\n{'-'*78}")
            for key, vd in sorted(entries):
                name = _TABLE_TYPE_NAMES.get(key, f"Unknown (0x{key:x})")
                print(f"\n  0x{key:x} — {name} ({_forefst.count_noun(len(vd), 'byte')})")
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
            if len(entries) > 0: print(f"  [OK] {_forefst.count_noun(len(entries), 'entry', 'entries')}"); ok_cnt += 1
            else: print("  [FAIL] empty")
            for tid in sorted([0xe030, 0xe040, 0xe060, 0xe0c0]):
                total += 1
                if any(k == tid for k, _ in entries):
                    print(f"  [OK] System type 0x{tid:x} ({_TABLE_TYPE_NAMES.get(tid,'')})"); ok_cnt += 1
                else:
                    print(f"  [WARN] Missing 0x{tid:x}")
            # N152 (1.14.0): 0x200 (a data stream's table, formats 3.11+; E167) is a format 3.14 schema: measured 2026-10-28 on
            # the corpus, present on all 103 3.14 volumes and absent on all 14 of 3.4 / 3.7 / 3.9 / 3.10 -- expecting it
            # everywhere made every older healthy volume fail `schema --verify`
            for tid in sorted([0x110, 0x150] + ([0x200] if (vmaj, vmin) >= (3, 14) else [])):
                total += 1
                if any(k == tid for k, _ in entries):
                    print(f"  [OK] Object schema 0x{tid:x} ({_TABLE_TYPE_NAMES.get(tid,'')})"); ok_cnt += 1
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
            return _verify_result(ok_cnt, total)                        # N152

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  UPCASE — Unicode upcase table reader
# ═══════════════════════════════════════════════════════════════════════



def _alloc_walk_tier(f, ps, cs, tr, roots, root_idx, want_id):
    """Every allocator row under one tier root, WITH the table id of the page it sat on.

    A tier is not identified by its root index: on a damaged volume root 12 has been seen carrying the
    Container Table (0x0b) rather than the Small allocator, and an id-correct root's subtree can still
    descend into pages belonging to other tables. So each row is tagged with its page's own id and the
    caller reports anything foreign instead of silently averaging it into a total (E74).
    """
    rows, foreign = [], 0
    if root_idx >= len(roots) or not roots[root_idx]:
        return rows, foreign, None
    real = root_idx in _CT_ROOT_INDICES
    root_id = None
    try:
        l0 = roots[root_idx][0]
        p0 = l0 if real else tr.tr(l0)
        pg = _seek_read(f, ps + p0 * cs, cs)                            # N371
        if pg[:4] == b"MSB+":
            root_id = le64(pg, 0x48)
    except (OSError, OverflowError) as _e:
        _skip_note("_alloc_walk_tier", "an allocator row", _e)
    seen = set(); stack = [(list(roots[root_idx]), 0)]
    while stack:
        lcns, depth = stack.pop()
        if depth > 8:
            continue
        data = b""
        try:
            for v in lcns:
                p = v if real else tr.tr(v)
                data += _seek_read(f, ps + p * cs, cs)                      # N371
        except (OSError, OverflowError) as _e:
            _skip_note("_alloc_walk_tier", "an allocator row", _e)
            continue
        if data[:4] != b"MSB+" or len(data) < 0x54:
            continue
        tid = le64(data, 0x48)
        thoff = 0x50 + le32(data, 0x50)
        if thoff + 40 > len(data):
            continue
        tbl = struct.unpack_from("<10I", data, thoff)
        is_index = bool(tbl[3] & 0x100); astart, aend = tbl[4], tbl[8]
        if astart >= aend:
            continue
        for i in range((aend - astart) // 4):
            aa = thoff + astart + i * 4
            if aa + 4 > len(data):
                break
            ro = thoff + le16(data, aa)
            if ro + 16 > len(data):
                break
            _, ko, kl, _, vo, vl, _ = struct.unpack_from("<I6H", data, ro)
            if ro + vo + vl > len(data):
                continue
            val = data[ro + vo:ro + vo + vl]
            if is_index:
                ch = tuple(c for c in (le64(val, j * 8) for j in range(4))
                           if c not in (0, 0xFFFFFFFFFFFFFFFF)) if vl >= 32 else ()
                if ch and ch not in seen:
                    seen.add(ch); stack.append((list(ch), depth + 1))
            elif tid != want_id:
                foreign += 1
            else:
                r = alloc_decode_row(val)
                if r:
                    rows.append(r)
    return rows, foreign, root_id


def cmd_allocators(image, remaining, partition_start):
    """Allocator tables (schema 0xe010): per-tier rows, totals, and the volume's own persisted summary."""
    args = _parse_args(remaining, flags=["-v", "-vv", "--json"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))
    try:
        vol = volume_clusters(f, ps, cs)        # B3: the volume's N clusters, not the image's length
        out = {"image": os.path.basename(_forefst._src_name(image)), "refs_version": f"{vmaj}.{vmin}", "cluster_size": cs,
               "volume_clusters": vol, "tiers": []}
        if not args["json"]:
            print(f"── Allocator Tables (schema 0xe010) — {_forefst._display_image(image)} ──")
            print(f"  ReFS {vmaj}.{vmin}, cluster {_forefst.count_noun(cs, 'byte')}, volume {_forefst.count_noun(vol, 'cluster')} ({_summary_human_size(vol * cs)})")
            print()
        for root_idx, name, tid in _ALLOC_TIERS:
            rows, foreign, root_id = _alloc_walk_tier(f, ps, cs, tr, roots, root_idx, tid)
            alloc = free = span = 0
            nbitmap = ncompact = 0
            for r in rows:
                a, fr = alloc_row_counts(r)
                alloc += a; free += fr; span += int(r["length"])
                if r["bitmap"] is None: ncompact += 1
                else: nbitmap += 1
            summ = alloc_read_summary(f, ps, cs, tr, roots, root_idx, table_id=tid, volume_clusters=vol)
            t = {"tier": name, "root_index": root_idx, "table_id": f"0x{tid:x}",
                 "root_page_table_id": None if root_id is None else f"0x{root_id:x}",
                 # How this tier's TABLE PAGES are reached. NOT how its rows are keyed: a row's
                 # range_start is a PHYSICAL cluster number (E74) whichever way the pages are addressed.
                 "addressing": "real" if root_idx in _CT_ROOT_INDICES else "virtual",
                 "rows": len(rows), "bitmap_rows": nbitmap, "compact_rows": ncompact,
                 "foreign_rows_rejected": foreign,
                 "span_clusters": span, "allocated_clusters": alloc, "free_clusters": free,
                 "summary_covered_clusters": None if not summ else summ[1],
                 "summary_free_clusters": None if not summ else summ[2],
                 "summary_format": None if not summ else summ[0]}
            t["summary_agrees"] = bool(summ and summ[1] == span and summ[2] == free)
            out["tiers"].append(t)
            if args["json"]:
                continue
            idmark = "" if root_id is None or root_id == tid else f"  [!] root page claims 0x{root_id:x}, not 0x{tid:x}"
            print(f"  {name} tier (root {root_idx}, table 0x{tid:x}, pages via {t['addressing']} LCNs; "
                  f"rows keyed by physical cluster){idmark}")
            print(f"    rows: {len(rows)}  ({nbitmap} bitmap, {ncompact} compact)"
                  + (f"   [!] {foreign} row(s) on foreign pages REJECTED" if foreign else ""))
            if not rows and not summ:
                print("    this tier could not be read here — nothing is reported for it rather than a "
                      "number taken from another table's page")
                print(); continue
            print(f"    from rows:    span {_forefst.count_noun(span, 'cluster')}   allocated {alloc} ({_summary_human_size(alloc * cs)})   "
                  f"not allocated {free} ({_summary_human_size(free * cs)})")
            if summ:
                print(f"    from summary: span {_forefst.count_noun(summ[1], 'cluster')}   not allocated {summ[2]} ({_summary_human_size(summ[2] * cs)})   "
                      f"[{'agrees' if t['summary_agrees'] else 'DIFFERS from the rows'}]")
                if not t["summary_agrees"]:
                    print("      • a difference is a finding, not a parse error: on ReFS 3.4 the tiers are strictly")
                    print("        separated so the Medium rows span less than the summary, and a truncated")
                    print("        container table makes both numbers disagree. Compare with `containers`.")
            else:
                print("    from summary: (not readable — the root page does not carry this tier's table)")
            if verbose:
                for r in rows[:(None if verbose >= 2 else 12)]:
                    a, fr = alloc_row_counts(r)
                    kind = "compact" if r["bitmap"] is None else "bitmap "
                    print(f"      {kind} start {r['start']:>13}  len {int(r['length']):>9}  "
                          f"alloc {a:>9}  unalloc {fr:>9}  flags 0x{r['flags']:x}  fmt {r['format']}")
                if verbose == 1 and len(rows) > 12:
                    print(f"      ... {len(rows) - 12} more (use -vv)")
            print()
        _cap_st = {}
        cap = alloc_capacity(f, ps, cs, tr, roots, status=_cap_st)
        out["capacity"] = cap
        if not args["json"]:
            if cap:
                print("  Volume capacity (from the Medium tier's persisted summary):")
                print(f"    used {_summary_human_size(cap['used_clusters'] * cs)} of {_summary_human_size(cap['covered_clusters'] * cs)} "
                      f"({100.0 * cap['used_clusters'] / cap['covered_clusters']:.1f}%), "
                      f"{_summary_human_size(cap['free_clusters'] * cs)} not allocated")
                print("    (not Windows' free figure: Windows keeps part of it in reserve, which the volume does not record)")
                if cap.get("length_disagreement"):
                    # CB-7 (1.14.0): the summary and the boot sector disagree on the volume's length -- said as that
                    print(f"    NOTE: {cap['length_disagreement']}")
            else:
                print("  Volume capacity: not available (%s)" % (_cap_st.get("reason") or "allocator summary unreadable"))
        else:
            _print_json(out)
        return 0
    finally:
        f.close()


def cmd_upcase(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify", "-H"])
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    show_header = args["H"] or verbose >= 1

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        if 0x07 not in obj_map and 0x08 not in obj_map:
            # N427 (Q10): the Upcase Table -- neither copy of the pair -- is a structure this command needs: a finding
            # (exit 2), or not determined over an Object Table read in part; 1.13.1 said "not found" (exit 1)
            return required_structure_missing("upcase", obj_map, prog=PROG)
        # N422 (T-CL1 rows 2-5): the pair as InitializeUpcaseTable opens it -- OID 0x8 first, OID 0x7 when 0x8's copy
        # fails -- and the rows from that copy alone; 1.13.1 read OID 0x7 (and said "not found", exit 1, without it)
        pair = system_table_pair(f, ps, cs, tr, obj_map, "upcase")
        use = pair["in_use"]
        if use is None:
            # no copy can be used: the table could not be read -- a structure this command needs (N427's class)
            return required_structure_missing("upcase", obj_map, prog=PROG, pair=pair)
        if pair.get("as_is"):
            # the maintainer's rule (2026-11-06): no copy passes, refs.sys does not open the table; the rows shown come
            # from a copy read as it is -- a finding of this command (exit 2), the statement on stderr
            _forefst._finding("system table copy", _forefst.system_table_as_is_text(pair))
            print(f"[{PROG}] WARNING: {_forefst.system_table_as_is_text(pair)}.", file=sys.stderr)
        _pair_texts = [t for _k, t in system_table_pair_texts(pair, absent=True, obj_map=obj_map)
                       if not pair.get("as_is")]
        for _text in _pair_texts:
            # a failed, flagged or differing copy that is not the one read: a redundancy condition (V-a: exit 2 in
            # summary / fastsummary / integrity), stated here, exit unchanged; --verify makes it a check of its own
            print(f"[{PROG}] NOTE: {_text}.", file=sys.stderr)
        other = next(c for c in pair["copies"] if c is not use)

        table_name = ""; total_entries = 0; data_rows = []
        for kd, vd in use["rows"]:
            if len(kd) < 4: continue
            key = le32(kd, 0)
            if key == 0: table_name = vd.decode("utf-8", errors="replace").rstrip("\x00")
            elif key == 1: total_entries = le32(vd, 0) if len(vd) >= 4 else 0
            else: data_rows.append((key, bytes(vd)))

        has_other = other["state"] != "absent"

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
            print(f"  Image:             {_forefst._display_image(image)}")
            print(f"  ReFS version:      {vmaj}.{vmin}")
            print(f"  Upcase OID:        0x{use['oid']:x} (the copy read; refs.sys opens OID 0x8 first, then OID 0x7)")
            print(f"  Other copy:        OID 0x{other['oid']:x}" + ("" if has_other else " (not in the Object Table)"))
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
        print(f"  Row value sizes:         {n_data - 1} × {_forefst.count_noun(common_row_size, 'byte')} + 1 × {_forefst.count_noun(last_row_size, 'byte')}")
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
                print(f"  U+{bstart:04X}-U+{bend:04X}  {bname:<40}  {nd:>5} {'diff' if nd == 1 else 'diffs'}")

        if verbose >= 2:
            print(f"\n{'-'*78}\nAll Non-Identity Mappings\n{'-'*78}")
            cnt = 0
            for cp, uc in enumerate(upcase):
                if cp != uc:
                    ch_from = chr(cp) if 32 <= cp < 0xD800 else ""
                    ch_to = chr(uc) if 32 <= uc < 0xD800 else ""
                    print(f"  U+{cp:04X} {ch_from:>2} → U+{uc:04X} {ch_to:>2}")
                    cnt += 1
            print(f"\n  Total: {_forefst.count_noun(cnt, 'non-identity mapping')}")

        if args["verify"]:
            print(f"\n{'='*78}\nVerification\n{'='*78}")
            ok_cnt = total = 0
            total += 1
            if n_data > 0: print(f"  [OK] {_forefst.count_noun(n_data, 'data row')}"); ok_cnt += 1
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
            # N422: the pair's check -- both copies in the Object Table, the other copy readable and equal to the copy
            # read (a copy that fails, a flagged root descriptor, copies that differ: `system_table_pair_texts`)
            if not has_other: print(f"  [WARN] Only one copy found (OID 0x{use['oid']:x})")
            elif _pair_texts:
                for _text in _pair_texts:
                    print(f"  [FAIL] {_text}")
            else: print("  [OK] Both copies found (OID 0x8, OID 0x7), with equal rows"); ok_cnt += 1
            total += 1
            if table_name == "Upcase Table": print(f"  [OK] Name = \"{table_name}\""); ok_cnt += 1
            elif table_name: print(f"  [INFO] Name = \"{table_name}\""); ok_cnt += 1
            else: print("  [WARN] No name")
            return _verify_result(ok_cnt, total)                        # N152

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
    #  OID30 — OID 0x30, the heat engine's table (E174, 1.14.0)
# ═══════════════════════════════════════════════════════════════════════
# `CmsVolumeHeatEngine::Persist` (26100.9444) writes per 10-minute generation two 80-byte rows (+0x00 the generation,
# +0x08 0 or 1, seven u64 of the generation's totals) and a 44-byte row per tracked container and direction (+0x00 the
# generation, +0x08 the container x 2 + the RWType bit, +0x10 / +0x18 two counters, a 32-bit map at +0x28). The key is
# the value's first 16 bytes. 1.13.1 called the generations "sessions" and the rows "Session summary", "IO counters"
# and "Category A-H": no driver reading supports those names.


def _oid30_row_label(key8, size):
    """What a row of object 0x30 is, from its key's +0x08 and its size (E174)."""
    if size == 80:
        return "generation totals (+0x8 = %d)" % key8
    if size == 44:
        return "container %d, RWType bit %d" % (key8 >> 1, key8 & 1)
    return "not decoded (%d bytes)" % size




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
            print(f"Image: {_forefst._display_image(image)}  (ReFS {vmaj}.{vmin}, {_forefst.count_noun(len(obj_map), 'object')})")
            print(f"{'='*78}")
            _why = object_absent_reason(obj_map, 0x30)
            if _why:
                # N358 (Q11): not among the rows of an Object Table read in part -- not determined, not "NOT PRESENT"
                print(f"  OID 0x30: not determined: {_why}")
                return 2
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
            r["sub_id_label"] = _oid30_row_label(r["sub_id"], len(vd))
            if len(vd) >= 44:
                r["fields_u64"] = [le64(vd, 16 + i*8) for i in range((len(vd) - 16) // 8) if 16 + i*8 + 8 <= len(vd)]
                remainder = (len(vd) - 16) % 8
                if remainder == 4: r["trailing_u32"] = le32(vd, len(vd) - 4)
            decoded_rows.append(r)

        generations = {}
        for r in decoded_rows:
            ts = r.get("timestamp_raw", 0)
            if ts not in generations: generations[ts] = {"str": r["timestamp_str"], "sub_ids": []}
            generations[ts]["sub_ids"].append(r.get("sub_id", -1))

        print(f"\n{'='*78}")
        print(f"Image: {_forefst._display_image(image)}  (ReFS {vmaj}.{vmin}, {_forefst.count_noun(len(obj_map), 'object')})")
        print(f"{'='*78}")
        print(f"  OID 0x30: PRESENT at VLCN 0x{oid30_vlcn:x} / PLCN 0x{oid30_plcn:x}")
        print(f"  Total rows: {len(decoded_rows)}")
        print(f"  Generations: {len(generations)}  (10-minute periods in which the volume had I/O)")

        for ts, info in sorted(generations.items()):
            sids = sorted(info["sub_ids"])
            print(f"\n  Generation: {info['str']}")
            print(f"    Key +0x8: {', '.join(f'0x{s:x}' for s in sids)}")

        if verbose:
            print(f"\n  {'─'*74}\n  Detailed rows:")
            for r in sorted(decoded_rows, key=lambda x: (x.get("timestamp_raw", 0), x.get("sub_id", 0))):
                sid = r.get("sub_id", 0)
                print(f"\n    Key +0x8 0x{sid:x} ({r['sub_id_label']}) — {_forefst.count_noun(r['value_size'], 'byte')}")
                for i, fv in enumerate(r.get("fields_u64", [])):
                    print(f"      field[{i}]: {fv:>12} (0x{fv:x})")
                if "trailing_u32" in r:
                    print(f"      map (u32 at +0x28): {r['trailing_u32']} (0x{r['trailing_u32']:x})")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  CHKP — Checkpoint analysis with container translation
    #  Source: refs_chkp.py (full bootstrap chain, root table, flags)
# ═══════════════════════════════════════════════════════════════════════



def cmd_chkp(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v", "-vv", "--verify", "--raw"])
    # A1/K035: a --verify run that found a corrupt checkpoint must say so in its EXIT CODE too, so a
    # script branching on the status can see it. Populated by the self-checksum check below.
    _chkp_failed = []
    verbose = 2 if args["vv"] else (1 if args["v"] else 0)
    verify = args["verify"]

    ps = _find_boot_offset(image, partition_start)
    validate_image(image, partition_start)                  # C2-5
    img_size = os.path.getsize(image)

    with open(image, "rb") as f:
        try:
            cs, vmaj, vmin, chk_algo, bpc = _forefst_parse_vbr(f, ps)
        except (ValueError, OSError) as _e:      # N378 (4w): e.g. a partition start no file can be read at
            die(str(_e))
        _bpc_from_vbr = vbr_container_size(boot_sector_bytes(f, ps))[1]    # N153 (N344: the copy read)
        cpc_vbr = bpc // cs
        chkp_lcns = _forefst_parse_supb(f, ps, cs)

        # A11: the copy is forefst's checkpoint_select (+0x60, superblock slot order on a tie), not a `>` over
        # the +0x10 clock kept here. It is the NEWEST copy, as before -- `chkp` inspects the newest checkpoint,
        # and `--verify` must still fail on it when it is damaged -- but a newest copy that fails its
        # self-checksum is now SAID to have failed, with the copy a volume reader uses instead.
        # N353 (A11, one selection rule): selected as bootstrap and every other caller select (`require_roots=True`),
        # so the copy in use and the conditions said below are bootstrap's. A copy whose root list cannot be read is
        # then no candidate, and `chkp` shows the newest copy a volume reader can use: selected without it, such a
        # copy was shown as newest AND in use while bootstrap read the other copy, whose conditions (a root 0xC/7/8
        # that does not verify) went unsaid. The copy itself is listed by the summaries (its root list could not be read).
        _sel = checkpoint_select(f, ps, cs, chkp_lcns, require_roots=True)
        # N384 / N394 (Q25): a copy whose read fails is forefst's `unreadable` view condition, named with its cause in
        # the block of unreadable copies below (exit 2) -- no longer an anonymous skip "cmd_chkp skipped a checkpoint"
        _cp = _sel["newest"]
        if _cp is None:
            die("no valid CHKP found")
        best_raw = _cp["raw"]; best_vc = _cp["vc_page"]; best_off = ps + _cp["lcn"] * cs
        _in_use = _sel["in_use"]
        _failed_note = None
        # N372 (C1): when a copy whose root list cannot be read is among the copies that cannot be used, forefst's shared
        # text (said below: `said_failed` does not drop it) names each copy and why; "no checkpoint copy passes its
        # self-checksum" would be false when that copy passes it. N373: so it would when a copy refs.sys rejects passes
        # it (`none-valid`, said below in the same way)
        _none_usable = any(_k in (("chkp", "none-usable"), ("chkp", "none-valid"))
                           for _k, _l, _t in _forefst._checkpoint_conditions(_sel, cs))
        if _cp["cksum_ok"] is False:
            _failed_note = (f"NOTE: this checkpoint copy (LCN 0x{_cp['lcn']:x}, offset 0x{best_off:x}) FAILED its "
                            f"self-checksum ({_cp['ckname']})"
                            + (f"; a volume reader uses the copy at LCN 0x{_in_use['lcn']:x} "
                               f"(offset 0x{ps + _in_use['lcn'] * cs:x}, vclock {_in_use['vc']}) instead."
                               if _in_use is not None and _in_use is not _cp else
                               "." if _none_usable else "; no checkpoint copy passes its self-checksum."))
            # N207 (decision 21): a command that says a copy FAILED exits 2, as forefst `summary` does
            _chkp_failed.append(best_off)
        # N332 / 27.3 / N341: every condition bootstrap says and exits 2 for (a root 0xC/7/8 of the copy in use that
        # does not verify, a checksum that cannot be verified, a +0x10/+0x60 divergence, ...) in forefst's words
        # (`_view_conditions`), said in every layout below and recorded (exit 2). `chkp` showed the 13 roots of that
        # copy and said nothing. A failed newest copy (stale view, or no copy passing) is `_failed_note`'s (N207): not
        # said twice.
        _view = _view_conditions(_sel, cs, said_failed=_failed_note is not None)
        if _view:
            _chkp_failed.append(best_off)
        # N374 (T1, T1a): `chkp` decodes one copy -- the newest a volume reader can use -- and never named a copy it
        # could not read. That copy is a `view` condition (exit 2), said here in its own block, apart from the notes
        # about the copy decoded below, so that no field printed for the copy decoded is read as belonging to it.
        _unreadable_texts = [_t for _k, _l, _t in _forefst._checkpoint_conditions(_sel, cs)
                             if _k[2:] == ("unreadable",) and _l == "view"]
        _view = [_t for _t in _view if _t not in _unreadable_texts]
        _notes = ([_failed_note] if _failed_note else []) + ["WARNING: %s." % _t for _t in _view]
        _unreadable_notes = ["WARNING: %s." % _t for _t in _unreadable_texts]

        raw = best_raw
        # F11 (LB2, LB25): the SHA-256 of the one cluster checkpoint_select read -- the record (E118), not the 16 KiB
        # page -- and the label after the hash names what it covers, one text with forefst `summary`
        chkp_sha = hashlib.sha256(raw).hexdigest()
        chkp_sha_text = "%s (%s)" % (chkp_sha, chkp_hash_span_text(len(raw), cs))

        ver_echo_major = le16(raw, 0x50); ver_echo_minor = le16(raw, 0x52)
        ver_major = le16(raw, 0x54); ver_minor = le16(raw, 0x56)
        tbl_desc_end = le32(raw, 0x58); self_desc_len = le32(raw, 0x5c)
        vclock_body = le64(raw, 0x60); alloc_clock = le64(raw, 0x68)
        oldest_log_off = le32(raw, 0x70); oldest_log_seg = le32(raw, 0x74)
        chkp_flags = le32(raw, 0x78)
        reserved_7c = le32(raw, 0x7C); reserved_80 = le32(raw, 0x80); reserved_84 = le32(raw, 0x84)
        # N554 (1.14.0, E159): +0x88 / +0x8C locate an optional area of the record (offset, length; 32 bytes where
        # present, the pair zero where not); 1.13.1 called them "Data area end" and "Max root capacity"
        area_off = le32(raw, 0x88); area_len = le32(raw, 0x8C)
        root_count = le32(raw, 0x90)
        _rc = min(root_count, 32)   # N3, review E9: bound the root loops against a fuzzed count (13 read; 32 is this tool's bound)
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

        # CB-11 (1.14.0): the copy refs.sys reads (`container_table_copy`: root 7, root 8 when root 7 fails), checked
        # against the checkpoint copy IN USE -- bootstrap's, whose roots 7 / 8 are the ones read -- not the newest this
        # command displays (the review S1: they differ when the newest copy is not used); what bootstrap says of it, said
        # here too (this command does not bootstrap)
        if _in_use is not None and _in_use is not _cp:
            _ct_raw, _ct_roots = _in_use["raw"], _in_use["roots"]      # checkpoint_select's own record of the copy
        else:
            _ct_raw, _ct_roots = raw, roots
        _ctc = _forefst.container_table_copy(f, ps, cs, _ct_raw, _ct_roots)
        if _ctc["text"]:
            _forefst._finding("container table copy", _ctc["text"])
            print(f"[{PROG}] WARNING: {_ctc['text']}.", file=sys.stderr)
        for _t in _ctc["flags"]:                                       # CB-3 / the review S3: V-a, a note here
            print(f"[{PROG}] note: {_t}.", file=sys.stderr)
        ct_vlcns = _ctc["vlcns"]
        # N216 (1.14.0): forefst's one Container Table reader and its checks; the translation uses the VBR's clusters
        # per container, as bootstrap does. `cpc_ct` stays the capacity a row records (+0x18; the last row read), which
        # the checks below compare with the VBR's
        _ct = container_table_read(f, ps, cs, ct_vlcns, cpc_vbr)
        ct_map = _ct["map"]; cpc_ct = cpc_vbr
        for _r in _ct["rows"].values():
            cpc_ct = _r["capacity"]
        tr = Translator(ct_map, cpc_vbr, _ct["skipped"], _ct["first_id"])

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
                cid = vlcns[0] >> tr.shift
                note = ("translated" if cid in ct_map else "not translated (see the warning)" if cid in tr.skipped
                        else "real (fallback)")
            if phys:
                abs_off = ps + phys[0] * cs
                if 0 <= abs_off + 0x50 <= img_size:
                    hdr = _seek_read(f, abs_off, 0x50); sig = hdr[:4]          # N371
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
                    sig = _seek_read(f, abs_off, 4)                            # N371
            root_data.append((idx, label, tid, evidence, vlcns, phys, sig, note))

        # N244: the GUID comes from the superblock copy parse_supb USED -- a verified copy (A1); this read the
        # primary raw, so it printed all zeros after a fallback and a damaged primary's GUID after a flip.
        supb_page = _read_at(f, ps + _forefst._SUPB_FELL_BACK.get("used_lcn", SUPB_LCN) * cs, cs) \
            if verbose >= 1 else b""

    def _emit_verify():
        # --verify consistency table — runs on every render path (was unreachable without -v; contract fix 2026-06-20).
        print()
        print("=" * 78)
        print("Verification")
        print("=" * 78)
        ok = 0; total = 0
        not_made = 0          # N333: checks that could not be made -- not passed, not FAILED either
        # A1/K035: `--verify` ran 17 structural checks and reported "17/17 checks passed" on a checkpoint
        # whose page had been corrupted -- it never verified the CHKP page's OWN self-checksum, which is
        # the one check that would have caught it. A checkpoint that fails its checksum is not a healthy
        # checkpoint no matter how well its root list parses.
        # K042: both clocks were PRINTED one line apart and neither was ever compared -- a copy whose
        # allocator clock was 617 ahead of its virtual clock still reported "17/17 checks passed". The
        # allocator state cannot be newer than the checkpoint that describes it. Measured over 117 images
        # / 234 copies before the rule was written: `virtual - allocator` is always 3..31, never <= 0.
        total += 1
        _vc_sel = le64(raw, 0x60)
        _ac = le64(raw, 0x68)
        if _ac <= _vc_sel:
            print(f"  [OK] Allocator clock {_ac} <= virtual clock {_vc_sel}"); ok += 1
        else:
            print(f"  [FAIL] Allocator clock {_ac} is AHEAD of the virtual clock {_vc_sel} — the "
                  f"allocator state cannot be newer than the checkpoint describing it; one of the two "
                  f"was edited")
            _chkp_failed.append(best_off)
        total += 1
        _ck_ok, _ck_name = _verify_self_checksum(raw, cs)
        if _ck_ok is True:
            print(f"  [OK] CHKP self-checksum ({_ck_name})"); ok += 1
        elif _ck_ok is False:
            # F11 / E118: the self-checksum covers the checkpoint record, one cluster -- not a 16 KiB page
            print(f"  [FAIL] CHKP self-checksum ({_ck_name}) does NOT match the record's contents (one cluster) — "
                  f"this checkpoint is corrupt or was tampered with")
            _chkp_failed.append(best_off)
        else:
            # N238: a check that could not be made is not a pass ("[SKIP] ... no algorithm" counted as passed)
            print(f"  [WARN] CHKP self-checksum cannot be verified ({_ck_name})")
            not_made += 1
        # N580 (1.14.0, the auditor's RC1 check O3): each OTHER copy's own self-checksum, one row per copy. RC1 checked
        # the copy it decodes only, so with the other copy damaged `--verify` said nothing and exited 0, while forefst
        # `summary` says it and exits 2 (a copy not in use that fails its self-checksum, decision 20.3). A copy without
        # a CHKP signature, or one that could not be read, is said in the block of unreadable copies (exit 2).
        for _oc in _sel["copies"]:
            if _oc is _cp or not _oc["sig_ok"]:
                continue
            total += 1
            _ow = "Other checkpoint copy (LCN 0x%x, vclock %s): self-checksum (%s)" % (
                _oc["lcn"], _oc["vc"], _oc["ckname"] or "-")
            if _oc["cksum_ok"] is True:
                print(f"  [OK] {_ow}"); ok += 1
            elif _oc["cksum_ok"] is False:
                print(f"  [FAIL] {_ow} does NOT match the record's contents (one cluster)")
                _chkp_failed.append(ps + _oc["lcn"] * cs)
            else:
                print(f"  [WARN] {_ow} cannot be verified")
                not_made += 1
        total += 1
        # N332 (decision 27.5): roots 0xC, 7 and 8 of this copy against the digests it records -- the check the 26100
        # driver's first (strict) pass makes (forefst `checkpoint_select` -> `_chkp_root_failures`). `--verify` printed
        # "19/19 checks passed" over a copy whose Container Table did not match its digest.
        # N364 (R6): the result and the words are forefst's `_root_check`, as in `supb --verify`'s roots rows (this line
        # said "(the 26100 driver's first pass rejects such a copy)" after a failure; for the copy in use that is the
        # N205/N332 WARNING printed above, in the conditions' own words).
        _rres, _rtxt = _root_check(_cp)
        print(f"  [{_rres}] {_rtxt[:1].upper()}{_rtxt[1:]}")
        if _rres == "OK":
            ok += 1
        elif _rres == "FAIL":
            _chkp_failed.append(best_off)
        else:
            not_made += 1
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
            print(f"  [OK] Container map has {_forefst.count_noun(len(ct_map), 'entry', 'entries')}"); ok += 1
        else:
            print("  [FAIL] Container map is empty")
        for _idx, _label, _tid, _ev, _vlcns, _phys, _sig, _note in root_data:
            if _vlcns and _sig:
                total += 1
                if _sig == b"MSB+": ok += 1
                else: print(f"  [WARN] Root {_idx} ({_label}): sig={_sig!r}, expected MSB+")
        total += 1
        if not _bpc_from_vbr:
            # N153: VBR+0x40 holds 0 (the `refsutil fixboot` signature); comparing with the 64 MiB default it is
            # replaced by would report a match the volume does not record.
            print(f"  [WARN] CPC from Container Table ({cpc_ct}) cannot be compared: VBR+0x40 is zero, so the "
                  f"VBR's 0x{cpc_vbr:x} is the driver's 64 MiB default, not a value read from the volume")
            not_made += 1
        elif cpc_ct == cpc_vbr:
            print(f"  [OK] CPC from Container Table ({cpc_ct}) matches VBR ({cpc_vbr})"); ok += 1   # K28: a count
        else:
            print(f"  [WARN] CPC mismatch: Container Table={cpc_ct}, VBR={cpc_vbr}")          # K28: a count
        if ok == total:
            # N370 (1.14.0): the exit can come from a checkpoint condition stated above the table (the copy in use
            # stale, root-less, a clock divergence, a copy that cannot be verified): the Result line names it
            # ... or from a condition the run recorded elsewhere (pages it could not read: win11refsmini_aftercorruption
            # printed "20/20 checks passed" and exited 2), said on stderr
            print(f"\n  Result: {ok}/{_forefst.count_noun(total, 'check')} passed"
                  + ("; exit 2 for the checkpoint condition stated above" if _chkp_failed else
                     "; exit 2 for the condition said on stderr" if _forefst.rc_escalate(0) == 2 else ""))
        else:
            # "N/M checks passed" reads as a pass summary even when M-N of them failed; say what failed. N333: a check
            # that could not be made (an unknown checksum type, a VBR+0x40 of zero, a root that cannot be checked) is
            # counted apart -- it did not pass, and it did not fail.
            print(f"\n  Result: {total - ok - not_made} check(s) FAILED"
                  + (f", {not_made} could not be made" if not_made else "") + f" ({ok}/{total} passed)")
            # N240 (decision 21): `--verify` exits 2 on ANY failed check, not only the self-checksum and
            # allocator-clock ones (a zeroed Object-Table root printed "1 check(s) FAILED" and exited 0)
            _chkp_failed.append(best_off)

    if _unreadable_notes:
        print()
        for _n in _unreadable_notes:
            print(_n)
    if args["raw"]:
        print()
        print(f"ReFS Checkpoint (CHKP) at offset 0x{best_off:x}")
        print(f"SHA-256: {chkp_sha_text}")
        for _n in _notes: print(_n)
        print()
        for row_off in range(0, min(len(raw), 0x400), 16):
            chunk = raw[row_off:row_off + 16]
            h = " ".join(f"{x:02x}" for x in chunk)
            a = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
            print(f"  {row_off:04x}  {h:<48s}  |{a}|")
        print()
        return 2 if _chkp_failed else 0

    if verbose == 0:
        self_block = le64(raw, 0x20)
        ph_version = le32(raw, 0x04); ph_vol_sig = le32(raw, 0x0C)
        ver_echo_str = f"{ver_echo_major}.{ver_echo_minor}" if (ver_echo_major or ver_echo_minor) else "(not set — upgraded or legacy)"
        offset_list_str = f"0x{le32(raw, 0x94):x} (indirect offset list)" if indirect else "(direct root offsets follow)"
        reserved_zero = reserved_7c == 0 and reserved_80 == 0 and reserved_84 == 0

        print()
        print(f"ReFS Checkpoint (CHKP) at offset 0x{best_off:x}")
        print(f"SHA-256: {chkp_sha_text}")
        for _n in _notes: print(_n)
        print()

        rows = [
            ["Signature",            "0x0", _hexbytes(raw[0x00:0x04]),     _sig_str(raw[0:4])],
            ["Page hdr version",     "0x4", _hexbytes(raw[0x04:0x08]),     f"0x{ph_version:x}"],
            ["Volume signature",     "0xc", _hexbytes(raw[0x0C:0x10]),     f"0x{ph_vol_sig:08x}"],
            ["Page header clock",    "0x10", _hexbytes(raw[0x10:0x18]),     str(best_vc)],     # N287
            ["Self-block LCN",       "0x20", _hexbytes(raw[0x20:0x28]),     _hx(self_block)],
            ["Version echo",         "0x50", _hexbytes(raw[0x50:0x54]),     ver_echo_str],
            ["Version",              "0x54", _hexbytes(raw[0x54:0x58]),     f"{ver_major}.{ver_minor}"],
            ["Table desc end",       "0x58", _hexbytes(raw[0x58:0x5C]),     f"0x{tbl_desc_end:x}"],
            ["Ref size (self-desc)", "0x5c", _hexbytes(raw[0x5C:0x60]),     f"0x{self_desc_len:x} ({_forefst.count_noun(self_desc_len, 'byte')})"],
            ["Virtual clock",        "0x60", _hexbytes(raw[0x60:0x68]),     str(vclock_body)],     # N287
            ["Allocator clock",      "0x68", _hexbytes(raw[0x68:0x70]),     str(alloc_clock)],
            ["Oldest log ref",       "0x70", _hexbytes(raw[0x70:0x78]),     f"offset=0x{oldest_log_off:x}, segment={oldest_log_seg}"],
            ["Flags",                "0x78", _hexbytes(raw[0x78:0x7C]),     f"0x{chkp_flags:x}"],
            ["Reserved",             "0x7c", _hexbytes(raw[0x7C:0x88]),     "zero" if reserved_zero else "NON-ZERO"],
            ["Area offset",          "0x88", _hexbytes(raw[0x88:0x8C]),
             f"0x{area_off:x} (in the record)" if area_len else f"0x{area_off:x} (no area: length 0)"],
            ["Area length",          "0x8c", _hexbytes(raw[0x8C:0x90]),     f"{_forefst.count_noun(area_len, 'byte')}"],
            ["Root count",           "0x90", _hexbytes(raw[0x90:0x94]),     str(root_count)],
            ["Offset list pointer",  "0x94", _hexbytes(raw[0x94:0x98]),     offset_list_str],
        ]
        # N554 (1.14.0, E158 / E159): the other optional areas, each an (offset, length) pair, present when its flag is
        # set (without 0x200 the root references start at +0x94 and these offsets hold them)
        if indirect:
            rows.append(["Offset list length", "0x98", _hexbytes(raw[0x98:0x9C]), f"{_forefst.count_noun(le32(raw, 0x98), 'byte')}"])
        for _bit, _name, _o in ((0x400, "Rollback-protection", 0x9C), (0x2000, "Attestation HMAC", 0xA4)):
            if chkp_flags & _bit:
                rows.append([f"{_name} offset", f"0x{_o:x}", _hexbytes(raw[_o:_o + 4]), f"0x{le32(raw, _o):x}"])
                rows.append([f"{_name} length", f"0x{_o + 4:x}", _hexbytes(raw[_o + 4:_o + 8]),
                             f"{_forefst.count_noun(le32(raw, _o + 4), 'byte')}"])
        _print_table(["Field", "Offset", "Raw bytes", "Interpreted"], rows)

        # N289 / N221 (1.14.0): forefst's decoder -- the driver's names, and any uncatalogued bit said (it was dropped)
        active = _forefst.chkp_flags_decoded(chkp_flags)
        if active:
            print(f"  Checkpoint flags (0x{chkp_flags:x}):")
            for line in active:
                print(f"    {line}")
        else:
            print(f"  Checkpoint flags: none (0x{chkp_flags:x})")
        print()
        print(f"  Container entries: {len(ct_map)}, CPC: {cpc_ct}")
        print()

        fmt = "  {:<3} {:<26} {:>6} {:>12} {:>12} {:>6} {}"
        print(fmt.format("Idx", "Table Name", "TID", "Root LCN", "Physical LCN", "Sig", "Note"))
        print("  " + "-" * 76)
        for idx, label, tid, ev, vlcns, phys, sig, note in root_data:
            print(fmt.format(idx, label, f"0x{tid:x}",
                             _hx(vlcns[0]) if vlcns else "NULL",
                             _hx(phys[0]) if phys else "n/a",
                             _sig_str(sig) if sig else "n/a", note))
        print()
        if verify: _emit_verify()
        return 2 if _chkp_failed else 0

    # -v / -vv verbose
    print()
    print("=" * 78)
    print("ReFS Checkpoint Analysis with Container-Table Translation")
    print("=" * 78)
    kv = lambda k, v: print(f"  {k:<30} {v}")
    kv("Image", image)
    kv("Image size", _forefst.bytes_text(img_size))                                  # R2
    kv("CHKP SHA-256", chkp_sha_text)
    kv("Partition start", _hx(ps))
    kv("Cluster size", _forefst.size_text(cs))
    kv("ReFS version", f"{vmaj}.{vmin}")
    kv("Bytes per container", _forefst.size_text(bpc) + ("" if _bpc_from_vbr else CONTAINER_SIZE_DEFAULT_TAG))   # R3
    kv("Clusters per container", str(cpc_vbr))                                        # K28: a count
    if verbose >= 2:
        _gp = gpt_partition_detail(image)
        if _gp:
            kv("GPT partition", f"#{_gp['index']} '{_gp['name']}' LBA {_gp['first_lba']}-{_gp['last_lba']} ({_human_size(_gp['size_bytes'])})")

    print()
    print("SUPB")
    print("-" * 78)
    kv("Volume GUID", _guid_to_text(supb_page[0x50:0x60]) if len(supb_page) >= 0x60 else "n/a")      # K4
    kv("Superblock version", str(le64(supb_page, 0x68)) if len(supb_page) >= 0x70 else "n/a")
    kv("Checkpoint references", str(len(chkp_lcns)))

    ver_echo_str = f"{ver_echo_major}.{ver_echo_minor}" if (ver_echo_major or ver_echo_minor) else "(not set)"
    print()
    print("CHKP (the copy in use)")                    # N287 / N355: decision 25.4's words; it is the copy in use
    print("-" * 78)
    kv("CHKP offset", _hx(best_off))
    for _n in _notes: print(f"  {_n}")
    kv("Version echo", ver_echo_str)
    kv("Version", f"{ver_major}.{ver_minor}")
    kv("Virtual clock", str(vclock_body))               # N287: +0x60, the clock the copy in use is chosen by
    kv("Page header clock", str(best_vc))
    kv("Allocator clock", str(alloc_clock))
    kv("Flags", f"0x{chkp_flags:x}")
    kv("Indirect root list", "yes" if indirect else "no")                            # K19 / R11: a word
    kv("Global root count", str(root_count))
    kv("Root reference size", "%d bytes" % self_desc_len)                            # R2: a size in bytes

    active = _forefst.chkp_flags_decoded(chkp_flags)                 # N289 / N221: forefst's decoder
    if active:
        print()
        print("  Flag bits:")
        for line in active:
            print(f"    {line}")

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
        print(fmt.format(idx, label, f"0x{tid:x}",
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

    return 2 if _chkp_failed else 0


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
        # B2 (1.14.0): the Object Table copy bootstrap read (`object_table_copy`): the primary, or its duplicate
        # (root 5) when the primary's page fails its digest or cannot be read -- the table this listing describes
        ot_vlcns = getattr(obj_map, "root_vlcns", None) or (roots[0] if roots and roots[0] else [])
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
                    e["sig"] = _seek_read(f, abs_off, 4)                        # N371

        entries.sort(key=lambda e: e["oid"])

        if verbose >= 1:
            print("=" * 78)
            print("ReFS Object ID Table")
            print("=" * 78)
            print(f"  {'Image:':<18}{_forefst._display_image(image)}")
            print(f"  {'Partition start:':<18}{_hx(ps)}")
            print(f"  {'Cluster size:':<18}{_forefst.size_text(cs)}")
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
                print(f"    Value size: {_forefst.count_noun(len(e['value_raw']), 'byte')} (standard=80, extra={e['extra']})")
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
            return _verify_result(ok, total)                            # N152

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  PARENTCHILD — Parent-Child relationship table
    #  Source: refs_parentchild.py (directory hierarchy from root #4)
# ═══════════════════════════════════════════════════════════════════════

# C1-10 (1.14.0): the names are forefst's one table (`SYSTEM_OID_NAMES`); this listing kept a fourth copy, with
# its own spellings and the unread "(dup)" labels of OID 0x501 and 0x541


def _pc_oid_name(oid):
    if oid in _KNOWN_OIDS: return _KNOWN_OIDS[oid]
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
            # N427 (Q10): as `schema`'s root 3
            return required_structure_missing("parent_child", prog=PROG)

        pc_plcns = [tr.tr(v) for v in pc_vlcns]
        page_sig = _seek_read(f, ps + pc_plcns[0] * cs, 4)               # N371

        entries = []
        _pc_dmg = _forefst._walk_damage_count()
        for kd, vd in walk_bplus(f, ps, cs, tr, pc_vlcns):
            parent = le64(kd, 8) if len(kd) >= 16 else 0
            child = le64(kd, 24) if len(kd) >= 32 else 0
            entries.append({"parent_oid": parent, "child_oid": child,
                            "key_raw": kd, "val_raw": vd})
        # N427 / N445's class one table down (Q11): an absence from this table is stated only when it was read in full
        _pc_unread = table_unread_text("the Parent-Child Table", _pc_dmg, len(entries))

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
            print(f"  {'Image:':<18}{_forefst._display_image(image)}")
            print(f"  {'Partition start:':<18}{_hx(ps)}")
            print(f"  {'Cluster size:':<18}{_forefst.size_text(cs)}")
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
        print("  " + "-" * 76)
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

            # FS Metadata directory children -- Q33 (1.14.0): read by forefst's one reader (`fs_metadata_read`); a child's
            # value+0x80 is its file id, not a flag word (1.13.1 named three whole-word values DASD / Security / Reparse)
            if 0x520 in obj_map:
                print()
                print("-" * 78)
                print("FS Metadata Children (OID 0x520 B+-tree entries)")
                print("-" * 78)
                _fm = _forefst.fs_metadata_read(f, ps, cs, tr, obj_map, "parentchild", detail=True)
                _why = _fm.get("not_read") if _fm.get("usn_journal") is None else None
                if _why and not _fm["rows"]:
                    print(f"  Total rows: unknown: {_why}")
                else:
                    print(f"  Total rows: {_fm['rows']}  (filename entries: {len(_fm['children'])})"
                          + (f"; INCOMPLETE: {_why}" if _why else ""))
                    for ch in _fm["children"]:
                        print(f"  {ch['name']}{_fs_meta_child_text(ch)}")
                    if not _fm["children"] and not _why:
                        print("  (no children)")

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
                print(f"    Key == Value: {'yes' if e['key_raw'] == e['val_raw'] else 'no'}")   # K19 / R11: a word

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

            # C1-9 (c) (1.14.0): over a table read in part a count, an "all" and a "no" hold for the rows read only --
            # each says so and is a [WARN], not an [OK]
            _part = f"; {_pc_unread}: among the rows read only" if _pc_unread else ""
            total += 1
            if entries and _pc_unread:
                print(f"  [WARN] Parent-Child Table: {_forefst.count_noun(len(entries), 'entry', 'entries')} read{_part}")
            elif entries:
                print(f"  [OK] Parent-Child Table has {_forefst.count_noun(len(entries), 'entry', 'entries')}"); ok += 1
            elif _pc_unread:
                print(f"  [WARN] Parent-Child Table: not determined: {_pc_unread}")
            else:
                print("  [FAIL] Parent-Child Table is empty")

            total += 1
            if all(e["key_raw"] == e["val_raw"] for e in entries) and _pc_unread:
                print(f"  [WARN] Key equals Value for all {_forefst.count_noun(len(entries), 'entry', 'entries')} read{_part}")
            elif all(e["key_raw"] == e["val_raw"] for e in entries):
                print(f"  [OK] Key equals Value for all {_forefst.count_noun(len(entries), 'entry', 'entries')}"); ok += 1
            else:
                n_diff = sum(1 for e in entries if e["key_raw"] != e["val_raw"])
                print(f"  [WARN] Key != Value for {_forefst.count_noun(n_diff, 'entry', 'entries')}")

            total += 1
            struct_ok = True
            for e in entries:
                if len(e["key_raw"]) >= 32:
                    k0 = le64(e["key_raw"], 0); k2 = le64(e["key_raw"], 16)
                    if k0 != 0 or k2 != 0: struct_ok = False; break
            if struct_ok and _pc_unread:
                print(f"  [WARN] All keys read have structure [0, parent, 0, child]{_part}")
            elif struct_ok:
                print("  [OK] All keys have structure [0, parent, 0, child]"); ok += 1
            else:
                print("  [WARN] Some keys have non-zero padding fields")

            total += 1
            if 0x600 in root_nodes:
                print(f"  [OK] Root Directory (0x600) is a tree root with {len(children_of.get(0x600, []))} children"); ok += 1
            elif 0x600 in all_oids:
                print("  [WARN] Root Directory (0x600) exists but is not a tree root")
            elif _pc_unread:
                print(f"  [WARN] Root Directory (0x600): not determined: {_pc_unread}, and no row read names it")
            else:
                print("  [WARN] Root Directory (0x600) not found in table")

            total += 1
            child_counts = {}
            for e in entries:
                child_counts[e["child_oid"]] = child_counts.get(e["child_oid"], 0) + 1
            multi = {c: n for c, n in child_counts.items() if n > 1}
            if not multi and _pc_unread:
                print(f"  [WARN] No multi-parent entry among the rows read{_part}")
            elif not multi:
                print("  [OK] No multi-parent entries (tree structure)"); ok += 1
            else:
                print(f"  [INFO] {len(multi)} OIDs have multiple parents"); ok += 1

            return _verify_result(ok, total)                            # N152

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
    validate_image(image, partition_start)                  # C2-5

    with open(image, "rb") as f:
        try:
            cs, vmaj, vmin, chk_algo, bpc = _forefst_parse_vbr(f, ps)
        except (ValueError, OSError) as _e:      # N378 (4w): e.g. a partition start no file can be read at
            die(str(_e))
        _bpc_from_vbr = vbr_container_size(boot_sector_bytes(f, ps))[1]    # N153 (N344: the copy read)
        cpc = bpc // cs
        chkp_lcns = _forefst_parse_supb(f, ps, cs)

        # A11: the roots come from the checkpoint copy IN USE -- forefst's checkpoint_select, the copy the
        # driver uses (superblock slot order, a later copy only if its +0x60 is strictly greater, never one
        # that fails its self-checksum). This used a `>=` over the +0x10 clock of copies it never checked, and
        # did not say which copy it had read.
        best_vc = 0; best_roots = None
        _sel = checkpoint_select(f, ps, cs, chkp_lcns, require_roots=True)
        for _c in _sel["copies"]:
            _err = _chkp_copy_error(_c)             # N374: a copy without a signature is the view condition, said once
            if _err is not None:
                _skip_note("containers: checkpoint", f"lcn 0x{_c['lcn']:x}", _err)
        _cp = _sel["in_use"]
        if _cp is not None:
            best_vc = _cp["vc"]; best_roots = _cp["roots"]
        if not best_roots:
            die("no valid checkpoint found")
        _chkp_line = f"LCN {_hx(_cp['lcn'])}"
        _chkp_note = None
        if _sel["stale"] and _sel["newest"]["cksum_ok"] is not False:
            # N373: the newest copy passes its self-checksum but refs.sys rejects it -- never "FAILED its self-checksum"
            _chkp_note = (f"the newest checkpoint copy (LCN {_hx(_sel['newest']['lcn'])}, VC {_sel['newest']['vc']}) "
                          f"is not used: {_chkp_not_used_why(_sel, _sel['newest'])}; the tables below are read from "
                          f"LCN {_hx(_cp['lcn'])}")
        elif _sel["stale"]:
            _chkp_note = (f"the newest checkpoint copy (LCN {_hx(_sel['newest']['lcn'])}, VC {_sel['newest']['vc']}) "
                          f"FAILED its self-checksum; the tables below are read from LCN {_hx(_cp['lcn'])}")
        elif _sel["authoritative"] is not None and _sel["authoritative"] is not _cp:
            # N369: N361's shape -- the newest copy is not used because its root list could not be read; the note names
            # it as the stale view's does (the full condition is the WARNING below, forefst's words)
            _a = _sel["authoritative"]
            _chkp_note = (f"the newest checkpoint copy (LCN {_hx(_a['lcn'])}, VC {_a['vc']}) is not used: "
                          f"{_chkp_not_used_why(_sel, _a)}; the tables below are read from LCN {_hx(_cp['lcn'])}")
        elif _cp["cksum_ok"] is False:
            # N372 (C1): with a copy whose root list cannot be read among the copies that cannot be used, forefst's
            # shared text (said below) names each copy and why; "no checkpoint copy passes" may be false then
            _chkp_note = (f"the tables below are read from LCN {_hx(_cp['lcn'])}, which FAILED its self-checksum"
                          if any(_k in (("chkp", "none-usable"), ("chkp", "none-valid")) for _k, _l, _t in
                                 _forefst._checkpoint_conditions(_sel, cs)) else
                          f"no checkpoint copy passes its self-checksum; the tables below are read from "
                          f"LCN {_hx(_cp['lcn'])}, which FAILED it")
        # N332 / 27.3 / N341: every condition bootstrap says and exits 2 for, in forefst's words; a failed copy in use
        # or a failed newest copy is `_chkp_note`'s (N207), not said twice
        _view = _view_conditions(_sel, cs, said_failed=_chkp_note is not None)

        # CB-11 (1.14.0): the copy refs.sys reads, checked against the checkpoint copy in use, and what bootstrap says of
        # it (this command does not bootstrap)
        _ctc = _forefst.container_table_copy(f, ps, cs, _cp["raw"] if _cp else None, best_roots)
        if _ctc["text"]:
            _forefst._finding("container table copy", _ctc["text"])
            print(f"[{PROG}] WARNING: {_ctc['text']}.", file=sys.stderr)
        for _t in _ctc["flags"]:                                       # CB-3 / the review S3: V-a, a note here
            print(f"[{PROG}] note: {_t}.", file=sys.stderr)
        ct_vlcns = _ctc["vlcns"]
        ct_page = b""
        for l in ct_vlcns:
            ct_page += _seek_read(f, ps + l * cs, cs)                   # N371

        # N216 / A9 (1.14.0): forefst's one Container Table reader and its checks (`container_table_read`): the rows,
        # the containers the tools do not translate (listed below), and two containers on overlapping clusters (a
        # condition of the view, said in the header as bootstrap says it, exit 2)
        _ct = container_table_read(f, ps, cs, ct_vlcns, cpc)
        ct_rows = _ct["rows"]
        for _t in _ct["conditions"]:
            _forefst._finding("container table", _t)
        tr = Translator(_ct["map"], cpc, _ct["skipped"], _ct["first_id"])
        volume_bytes = volume_length(boot_sector_bytes(f, ps)) or 0     # K063, B3: the one length (N344: copy read)

        # N338 (1.14.0): a count over a walk that raised or met a page it could not read prints "unreadable", in A3's
        # convention (`table_row_count`; the skip or the damage is recorded, exit 2), never a traceback or a short count
        def _count(vlcns, use_tr, what):
            n, bad = table_row_count(lambda: walk_bplus(f, ps, cs, use_tr, vlcns), "containers", what)
            return None if bad else n
        alloc_root_map = {1: "Medium Allocator", 2: "Container Allocator", 12: "Small Allocator"}
        allocator_info = {}
        for root_idx, alloc_name in alloc_root_map.items():
            if root_idx >= len(best_roots) or not best_roots[root_idx]:
                allocator_info[alloc_name] = 0; continue
            vlcns = best_roots[root_idx]
            use_tr = None if root_idx in _CT_ROOT_INDICES else tr
            allocator_info[alloc_name] = _count(vlcns, use_tr, "the %s" % alloc_name)

        ci_rows = 0
        if len(best_roots) > 10 and best_roots[10]:
            ci_rows = _count(best_roots[10], tr, "the Container Index Table")

        # N215: the policy is read whatever the flags word at +0xA0 holds (`_ct_policy`; E90)
        compression, _comp_why = _ct_policy(ct_page, *_ct_root_read(best_roots, ct_vlcns, _cp))   # N352

    total_containers = volume_bytes // bpc if bpc > 0 else 0

    print("=" * 78)
    print("ReFS Container & Allocator Analysis")
    print("=" * 78)
    print(f"  {'Image:':<20}{_forefst._display_image(image)}")
    print(f"  {'ReFS version:':<20}{vmaj}.{vmin}")
    print(f"  {'Cluster size:':<20}{_forefst.size_text(cs)}")
    print(f"  {'Container size:':<20}{_forefst.size_text(bpc)}"                                        # R3
          + ("" if _bpc_from_vbr else CONTAINER_SIZE_DEFAULT_TAG))
    print(f"  {'Clusters/container:':<20}{cpc}")
    print(f"  {'Checkpoint VC:':<20}{best_vc}  (checkpoint {_chkp_line})")
    if _chkp_note:
        print(f"  {'':<20}{_chkp_note}")
    for _t in _view + _ct["conditions"]:
        print(f"  WARNING: {_t}.")          # N356: its own line, not a continuation of the `Checkpoint VC:` line
    print()

    print("-" * 78)
    print("Volume Capacity")
    print("-" * 78)
    print(f"  {'Total volume size:':<20}{_forefst.bytes_text(volume_bytes)}")       # N542: the count, then the aid
    print(f"  {'Total containers:':<20}{total_containers} (theoretical from volume size)")
    print(f"  {'Container Table:':<20}{_forefst.count_noun(len(ct_rows), 'mapped container')}"
          + (f", {len(_ct['skipped'])} of them not translated by the tools" if _ct["skipped"] else ""))
    for _i, _w in sorted(_ct["skipped"].items()):                   # N216: listed with the reason
        print(f"  {'':<20}container {_hx(_i)} is not translated: {_w}")
    print()

    _unread = "unreadable (pages could not be read — NOT an empty table)"
    print("-" * 78)
    print("Allocator Tables")
    print("-" * 78)
    for name, rows in allocator_info.items():
        print(f"  {name:<25} {_unread if rows is None else _forefst.count_noun(rows, 'row')}")          # N596
    print(f"  {'Container Index Table':<25} {_unread if ci_rows is None else _forefst.count_noun(ci_rows, 'row')}")
    print()

    if compression:
        print("-" * 78)
        print("Compression Configuration (from Container Table header)")
        print("-" * 78)
        cfmt = compression["format"]
        print(f"  {'Format:':<13}{_comp_fmt_name(cfmt, vmaj, vmin)}")     # R14: `summary`'s form; CB-4
        print(f"  {'Level:':<13}{compression['level']}")
        if compression["chunk"] > 0:
            print(f"  {'Chunk size:':<13}{_forefst.size_text(compression['chunk'])}")                   # R2 / R3
        else:
            print(f"  {'Chunk size:':<13}0 (default)")
        print()
    else:
        print(f"  Compression policy not read: {_comp_why}")       # N215: said, not left out silently
        print()

    # N264 (1.14.0): only the flags whose meaning refs.sys was read twice for (17134, 26100.9444; WAVEC_READING_tables
    # CL-2 row 11) are named; the Flags column shows every bit in hex. The categories of the state line do not overlap
    # and add up to the rows. The row's +0x20 is not "free clusters" (the driver counts ALLOCATED clusters there, a
    # reading made once), so no free-cluster figure is printed from it.
    _CT_FLAG_NAMES = ((0x0002, "compressed"), (0x0008, "compacted"), (0x0880, "index row missing"),
                      (0x4000, "all allocated"))

    if verbose and ct_rows:
        total_cap = sum(r["capacity"] for r in ct_rows.values())
        print("-" * 78)
        print("Container Table Entries")
        print("-" * 78)
        print(f"  Total capacity: {_forefst.count_noun(total_cap, 'cluster')} ({total_cap*cs/(1024*1024*1024):.1f} GiB), the sum of the "
              f"rows' capacities")
        _why = {}
        for _w in _ct["skipped"].values():
            _why[_w] = _why.get(_w, 0) + 1
        print(f"  By state: {len(_ct['map'])} translated, {len(_ct['skipped'])} not translated"
              + "".join(f"; {n} because {w}" for w, n in sorted(_why.items())))
        print()
        print(f"  {'ID':<8} {'Phys LCN':<14} {'Flags':<8} {'Row':>5} {'Type'}")
        print(f"  {'-'*8} {'-'*14} {'-'*8} {'-'*5} {'-'*20}")
        for cid in sorted(ct_rows):
            r = ct_rows[cid]
            names = [n for b, n in _CT_FLAG_NAMES if r["flags"] & b]
            phys = _hx(r["base"]) if r["base"] is not None else "-"
            print(f"  {_hx(cid):<8} {phys:<14} {_hx(r['flags']):<8} {r['len']:>5} {'|'.join(names) or '-'}")

    # N207 (decision 21): the command says the checkpoint copy it would read FAILED -> exit 2, as forefst `summary`;
    # N332 / decision 27.3: so does a condition of the copy in use
    return 2 if (_chkp_note or _view or _ct["conditions"]) else 0


# ═══════════════════════════════════════════════════════════════════════
#  Content subcommand shared helpers
# ═══════════════════════════════════════════════════════════════════════

# File-attribute tables live ONCE in forefst (FILE_ATTR_FLAGS / FILE_ATTR_SIMPLE, TitleCase); a flag word is rendered by
# forefst's flag_text / flag_names (K14, 1.14.0).

# $SI+0x24 internal_flags decode (FCB+0x08 bit extraction). NOTE (#342/E43):
# bit0 (0x01) = FCB bit 27 = a delete-disposition/EFS transient state, NOT integrity
# (the integrity-stream marker is file_attrs 0x8000, never reflected here).
# C2: 0x04/0x08/0x10 have NO confident semantic (driver builds them from generic FCB bits, no EA logic; disk: 0x08 set
# on many ordinary files, 0 with EA), so they stay unlabelled. N156 (1.14.0): forefst's table itself (0x02 is the
# case-sensitive directory bit; this copy said "Dedup/CoW").
_INTERNAL_FLAGS = _forefst._INTERNAL_FLAG_LABELS




def _verify_result(ok, total, not_made=0):
    """N152 (1.14.0): a `--verify` command's Result line and its exit code -- 2 when a check did not pass (decision 21 as
    extended by 25.2: every failed check), "N/M checks passed" only when all passed: `schema`, `upcase`, `objects` and
    `parentchild --verify` printed "N/M checks passed" over failed checks and returned 0. `chkp --verify`'s wording
    (N333): a check that could not be made is counted apart."""
    if ok == total:
        # N370's class: a run that recorded unreadable pages exits 2 whatever the checks found -- said here
        print(f"\n  Result: {ok}/{_forefst.count_noun(total, 'check')} passed"
              + ("; exit 2 for the condition said on stderr" if _forefst.rc_escalate(0) == 2 else ""))
        return 0
    print(f"\n  Result: {total - ok - not_made} check(s) FAILED" + (f", {not_made} could not be made" if not_made else "")
          + f" ({ok}/{total} passed)")
    return 2





# _parse_dir_entries: imported from forefst.py (K086) -- one definition.

def _build_backing_index(f, ps, cs, tr, obj_map):
    """{(owner_dir_oid, file_id): [(size@0x58, file_attrs@0x48), ...]} over every directory's type-0x40
    backing records. A non-resident file's AUTHORITATIVE file_attrs live in this backing (+0x48); the
    type-0x30 pointer's +0x40 attrs OMIT the EA bit (0x40000). One pass (~1s on the largest image)."""
    idx = {}
    for oid, vlcns in obj_map.items():
        try: rows = walk_bplus(f, ps, cs, tr, vlcns)
        except Exception as _e:
            _skip_note("_build_backing_index", "a backing record", _e)
            continue
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
    # Require a SIZE match (val+0x58) even for a single candidate: the per-dir file_id COLLIDES, so a lone
    # candidate can belong to a DIFFERENT file (e.g. a size-0 stub whose only same-ordinal backing is another
    # file's, winsider). forefst's walk (hl_groups) resolves strictly by size and leaves attrs untouched on
    # no match; mirror that -> return None (no bogus EA bit). #327 stub fix.
    for sz, fa in cands:
        if sz == size:
            return fa
    return None


# _walk_dir_tree: imported from forefst.py (K086) -- one definition.

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
# 278 corpus-wide) is REPLACED by forefst's row-table _parse_ads_from_value (used via the merged walker). Same entry shape;
# `files` ADS counts now match forefst. See analysis/reports/forefstdev_audit_verification_2026-07-03.md (N2).






# ═══════════════════════════════════════════════════════════════════════
#  FILES — Directory tree listing
# ═══════════════════════════════════════════════════════════════════════

def cmd_files(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v"], valued=["--depth", "--oid"])
    verbose = args["v"]
    # Full-depth by default (matches forefst; --depth N overrides). Cycle-guarded + recursion limit raised.
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else DEFAULT_DEPTH
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
        print(f"  Image:           {_forefst._display_image(image)}")              # N290: forefst's one rule
        print(f"  ReFS version:    {vmaj}.{vmin}")
        print(f"  Cluster size:    {_forefst.size_text(cs)}")
        print(f"  Objects:         {len(obj_map)}")
        print(f"  Start OID:       {_hx(start_oid)}")
        print(f"  Start name:      {start_name}")
        print()

        results = []
        _walk_dir_tree(f, ps, cs, tr, obj_map, start_oid, "", 0, max_depth, results)
        # K097: a file's size and attributes come from forefst's AUTHORITATIVE walk_directory_tree, as they
        # already do for `attributes` and `details`. The walk above reads the NAME row, and a split name's
        # size there is a cached copy that goes stale on hard-linked names (`papa_victor_867137.csv`: 293,302
        # cached, 479,429 the object's own). The local backing lookup this replaces could not correct it --
        # it keyed on that same cached size -- and it re-implemented the resolution forefst's walk owns.
        _ffp = {r["path"]: r for r in
                walk_directory_tree(f, ps, cs, tr, obj_map, start_oid, max_depth, True)}
        for r in results:
            a = _ffp.get(r["path"]) if r["type"] == "FILE" else None
            if a is not None:
                r["file_size"] = a.get("file_size", r["file_size"])
                r["file_attrs"] = a.get("file_attrs", r["file_attrs"])
                r["_ref"] = "0x%x:0x%x" % (a.get("home_oid") or 0, a.get("file_id") or 0)
                r["_objkey"] = _forefst._object_key(a)                          # review RE1-4: the file, once
                r["_residency"] = _data_residency(a)
                if not r.get("ads") and a.get("has_ads") and not a.get("record_embedded"):
                    # N284 (1.14.0): a split record's streams are in its backing (T9), which this walk never read
                    _rec = _forefst.ea_record(f, ps, cs, tr, obj_map, a)
                    if _rec is not None:
                        r["ads"] = _forefst._parse_ads_from_value(bytes(_rec), (f, ps, cs, tr))

        n_dirs = sum(1 for r in results if r["type"] == "DIR ")
        n_files = sum(1 for r in results if r["type"] == "FILE")
        n_ads = sum(len(r.get("ads", [])) for r in results)
        ads_note = (f", {_forefst.count_noun(n_ads, 'named-stream entry', 'named-stream entries')} (listed under each name)"
                    if n_ads else "")
        print(f"  Total entries:   {len(results)} ({_forefst.count_noun(n_dirs, 'directory', 'directories')}, "
              f"{_forefst.count_noun(n_files, 'file name')}{ads_note})")
        # E1 close (review RE1-4; C3 / N149's class): the files counted once each -- this line called 1,333 names
        # "1333 files" where `summary` (both tools) says 980 files under 1,333 names (win11refs2tspecials)
        _fo = {}
        for r in results:
            if r["type"] == "FILE":
                _fo.setdefault(r.get("_objkey") or ("row", id(r)), r.get("_residency") or DATA_UNKNOWN)
        _res = {}
        for _v in _fo.values():
            _res[_v] = _res.get(_v, 0) + 1
        print(f"  Files:           {_forefst.files_count_text({'files': len(_fo), 'file_names': n_files, 'residency': _res})}")
        print(f"  Names:           {_forefst.names_count_text({'files': len(_fo), 'file_names': n_files})}")   # A7
        print()

        # C1 (1.14.0): the column headed "OID" held a residency word for a file ("(snapshot-shared)", 17 characters in
        # a 12-wide column): one column for the identity (`files`' ObjectRef: a directory's OID:0x0, a file's
        # HomeOID:FileID) and one for where a file's data is
        def _ident(r):
            return ("0x%x:0x0" % r["oid"]) if r["oid"] else r.get("_ref") or "?"

        def _data(r):
            return "" if r["type"] == "DIR " else _walk_storage_word(r).strip("()")
        _w = max([len(_ident(r)) for r in results] + [9])
        if verbose:
            print(f"  {'Type':<5} {'ObjectRef':<{_w}} {'Data':<15} {'Attrs':<10} {'Size':>10} {'Modified':<20} {'Path'}")
            print(f"  {'-'*100}")
            for r in results:
                mod = _filetime_to_str(r["modify_time"])
                a = _forefst.flag_text(r["file_attrs"], FILE_ATTR_FLAGS)   # N200 (a), K14: hex then the names
                sz = r["file_size"] if r["type"] == "FILE" else ""
                print(f"  {r['type']:<5} {_ident(r):<{_w}} {_data(r):<15} {a:<10} {sz:>10} {mod:<20} {r['path']}")
                for ads in r.get("ads", []):
                    sz_ads = ads["stream_size"]
                    print(f"   ADS  {'':<{_w}} {ads.get('storage', ''):<15} {'':10} {sz_ads:>10} {'':20} "
                          f"{r['path']}:{ads['name']}")
        else:
            print(f"  {'Type':<5} {'ObjectRef':<{_w}} {'Data':<15} {'Path'}")
            print(f"  {'-'*60}")
            for r in results:
                print(f"  {r['type']:<5} {_ident(r):<{_w}} {_data(r):<15} {r['path']}")
                for ads in r.get("ads", []):
                    print(f"   ADS  {'':<{_w}} {ads.get('storage', ''):<15} {r['path']}:{ads['name']}  "
                          f"({ads['stream_size']}B)")

        return 0

    finally:
        f.close()



# ═══════════════════════════════════════════════════════════════════════
#  ATTRIBUTES — File attribute deep dive
# ═══════════════════════════════════════════════════════════════════════

def _analyze_dir_attributes(f, ps, cs, tr, obj_map, oid, path, depth, max_depth, results, filt, _visited=None):
    """Recursively analyze a directory's file attributes."""
    if depth > max_depth or oid not in obj_map: return
    # Cycle guard (full-depth default): never revisit an OID; well-formed trees don't, so nothing is dropped.
    if _visited is None: _visited = set()
    if oid in _visited: return
    _visited.add(oid)
    rows = walk_bplus(f, ps, cs, tr, obj_map[oid])
    for kd, vd in rows:
        if len(kd) < 4 or le16(kd, 0) != 0x30: continue
        name = kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
        full_path = f"{path}/{name}" if path else name
        attrs = _extract_file_attributes(vd, name)
        attrs["path"] = full_path
        attrs["_vd"] = bytes(vd)            # N329: the name row's value, for the one WSL decoder (cmd_attributes)
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
                                        full_path, depth + 1, max_depth, results, filt, _visited)




def cmd_attributes(image, remaining, partition_start):
    args = _parse_args(remaining, flags=["-v"], valued=["--oid", "--depth", "--filter"])
    verbose = args["v"]
    start_oid = _int_arg(args["oid"], "--oid", 0) if args["oid"] else 0x600
    # Full-depth by default (matches forefst; --depth N overrides). Cycle-guarded + recursion limit raised.
    max_depth = _int_arg(args["depth"], "--depth") if args["depth"] else DEFAULT_DEPTH
    filt = args["filter"]
    if filt == "wsl":
        # C16: refsanalysis `--filter wsl` selects files carrying the WSL ownership/mode metadata EA
        # ($LX* -> lx_mode). This differs, intentionally, from forefst `files --filter wsl`, which selects
        # by the WSL reparse TAG. A file can have one without the other (the $LX* EAs need a `-o metadata`
        # DrvFs mount), so the two counts need not match — they answer different questions.
        print("  NOTE: this selects files with WSL metadata EAs (lx_mode); forefst `--filter wsl` selects "
              "by reparse tag instead — the two can differ (see docs).", file=sys.stderr)

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = bootstrap(image, partition_start)
    except (ValueError, OSError) as e:
        die(str(e))

    try:
        print("=" * 78)
        print("ReFS File Attribute Analysis")
        print("=" * 78)
        print(f"  Image:        {_forefst._display_image(image)}")
        print(f"  ReFS version: {vmaj}.{vmin}")
        print(f"  Cluster size: {_forefst.size_text(cs)}")
        print(f"  Start OID:    {_hx(start_oid)}")
        if filt:
            print(f"  Filter:       {filt}")
        print()

        results = []
        # N329 / N321 (1.14.0): `--filter wsl` and `--filter snapshot` select on the walk record's values (below)
        _analyze_dir_attributes(f, ps, cs, tr, obj_map, start_oid, "", 0, max_depth, results,
                                None if filt in ("wsl", "snapshot") else filt)
        # Consistency (findings #1-4): source the residency verdict, the EA-corrected FileAttributes, and the
        # backing-resolved SecurityId/USN/IntFlags for non-resident files from forefst's AUTHORITATIVE
        # walk_directory_tree (which resolves the type-0x40 backing via the collision-safe hl_groups pass) --
        # so `attributes` agrees with forefst/summary/details. The local walk still supplies WSL/timestamps/
        # ADS (walk_directory_tree does not surface WSL metadata). One extra walk; correctness over speed.
        _ffp = {r["path"]: r for r in
                walk_directory_tree(f, ps, cs, tr, obj_map, start_oid, max_depth, True)}
        for r in results:
            a = _ffp.get(r.get("path"))
            if a is None:
                continue
            r["is_resident"] = a.get("is_resident", r.get("is_resident"))
            r["_objkey"] = _forefst._object_key(a)                                  # review RE1-4: the object, once
            # E87: the Storage line states both axes in the words `files` uses for them. It printed RESIDENT /
            # NON-RESIDENT from the walk's raw flag, which is "embedded AND inline", so every split file whose
            # bytes are inline (278 on win11refs2tspecials) read NON-RESIDENT while `files` said inline.
            r["data_residency"] = _data_residency(a)
            r["placement"] = _record_placement(a)
            r["file_attrs"] = a.get("file_attrs", r.get("file_attrs", 0))
            for _flag in ("is_encrypted", "is_compressed", "has_reparse", "has_ea"):
                r[_flag] = a.get(_flag, r.get(_flag))
            # SecurityId/USN/IntFlags from forefst for EVERY entry: a directory's come from its own $SI, a
            # non-resident file's from the type-0x40 backing (both resolved by the walk); for resident files
            # this is a no-op (identical inline value). refsanalysis' local walk omitted them off-resident.
            for _bk in ("security_id", "usn", "internal_flags"):
                r[_bk] = a.get(_bk, r.get(_bk, 0))
            # N329 (1.14.0): the one WSL decoder (forefst `wsl_metadata`: exact lengths, the PackedEaSize oracle) on the
            # record that holds the EAs -- a split file's backing too; this tool scanned the name row for "$LX" with
            # `>=` length gates and read no backing
            for _k in ("lx_mode", "lx_uid", "lx_gid", "lx_dev"):
                r.pop(_k, None)
            if a.get("has_ea"):
                # the embedded row's own value (the walk record keeps no bytes), or a split file's backing
                _rec = r.get("_vd") if a.get("record_embedded") else _forefst.ea_record(f, ps, cs, tr, obj_map, a)
                _w = (_forefst.wsl_metadata(_rec or b"", (f, ps, cs, tr)) or {}).get("wsl") or {}
                for _src, _dst in (("mode", "lx_mode"), ("uid", "lx_uid"), ("gid", "lx_gid"), ("dev", "lx_dev")):
                    if _src in _w:
                        r[_dst] = tuple(_w[_src]) if _src == "dev" else _w[_src]
            # N321's class: the snapshot count `files` gives (this tool counted its own way, without page context)
            r["possible_snapshots"] = (a.get("snapshot_count") or 0) > 0
            # N286 (1.14.0): the access time and the named streams, from the same record (`files` and both `details`
            # carry them; this command printed neither)
            r["access_time"] = a.get("access_time", r.get("access_time", 0))
            if a.get("has_ads"):
                _ast = a.get("ads_storage") or {}
                r["ads_list"] = [(n, _ast.get(n, DATA_UNKNOWN)) for n in a.get("ads_list") or []]
        if filt == "wsl":
            results = [r for r in results if "lx_mode" in r]
        elif filt == "snapshot":
            results = [r for r in results if r.get("possible_snapshots")]

        # E1 close (review RE1-4; C3 / N149's class): every count is of objects -- a file with several names is one
        # file (its FileRef, `_object_key`), as in `summary`; the names are said beside the files
        total = len(results)
        dirs = sum(1 for r in results if r.get("is_dir"))
        _objs = {}
        for r in results:
            _objs.setdefault(r.get("_objkey") or ("row", id(r)), r)
        _fobjs = [r for r in _objs.values() if not r.get("is_dir")]
        _res = {}
        for r in _fobjs:
            _v = r.get("data_residency") or DATA_UNKNOWN
            _res[_v] = _res.get(_v, 0) + 1
        encrypted = sum(1 for r in _objs.values() if r.get("is_encrypted"))
        wsl = sum(1 for r in _objs.values() if "lx_mode" in r)
        reparse = sum(1 for r in _objs.values() if r.get("has_reparse"))
        snapshots = sum(1 for r in _objs.values() if r.get("possible_snapshots"))

        print("  Summary:")
        print(f"    Total entries:     {total} names")
        print(f"    Directories:       {dirs}")
        print(f"    Files:             "
              f"{_forefst.files_count_text({'files': len(_fobjs), 'file_names': total - dirs, 'residency': _res})}")
        print(f"    Names:             {_forefst.names_count_text({'files': len(_fobjs), 'file_names': total - dirs})}")  # A7
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
                print(f"    Accessed:    {_filetime_to_str(r.get('access_time', 0))}")       # N286
            for _an, _ar in r.get("ads_list") or []:
                print(f"    ADS:         {_an} ({_ar})")                                    # N286
            # K14 / E-3 (1.14.0): forefst's flag form -- `0x20 (Archive|Directory)`, `0x0 (none set)` for a word read
            # as zero, an unnamed bit as its hex (it was dropped from the names: "(0x8)")
            if "file_attrs" in r:
                print(f"    Attributes:  {_forefst.flag_text(r['file_attrs'] or 0, FILE_ATTR_FLAGS)}")
            iflags = r.get("internal_flags")
            if iflags is not None:                        # Q-B answered B1 (1.14.0): every value read, 0 included
                print(f"    IntFlags:    {_forefst.internal_flags_str(iflags)}")
            if "security_id" in r and r["security_id"]:
                print(f"    SecurityId:  {_forefst.security_id_text(r['security_id'])}")     # N543 (a): K3
            if "usn" in r and r["usn"]:
                print(f"    USN:         {r['usn']}")
            if not is_dir:
                _pl = r.get("placement") or ("embedded" if r.get("value_len", 0) > 84 else "split")
                print(f"    Storage:     {r.get('data_residency') or DATA_UNKNOWN} (record {_pl}"
                      + (f", {_forefst.count_noun(r['value_len'], 'byte')})" if _pl == "embedded" else ")"))
            elif r.get("is_resident"):
                # C7 / N161 (1.14.0): a directory has no data residency; its row's placement
                print(f"    Storage:     directory (record embedded, {_forefst.count_noun(r['value_len'], 'byte')})")
            if r.get("is_encrypted"):
                print("    *** EFS ENCRYPTED ***")
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
                print("    *** REPARSE POINT (symlink/WSL special file) ***")
            if r.get("possible_snapshots"):
                print(f"    *** STREAM SNAPSHOTS (large embedded data: {_forefst.count_noun(r['value_len'], 'byte')}) ***")
            if verbose and "extended_attributes" in r:
                print("    Extended Attributes:")
                for ea in r["extended_attributes"]:
                    val_hex = ea["value"].hex() if len(ea["value"]) <= 16 else ea["value"][:16].hex() + "..."
                    print(f"      {ea['name']:12s} = {val_hex} ({_forefst.count_noun(len(ea['value']), 'byte')})")

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
        except Exception as _e:
            _skip_note("_resolve_nonresident_usn", "the USN journal stream", _e)
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
    """Feature A: full details for ANY file by PATH (files have no OID)."""
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
            _not_found(f"path not found: {path}")
        resident = len(vd) > 84
        name = path.replace("\\", "/").rstrip("/").split("/")[-1]
        # K22 (1.14.0): `files`' FullPath form (no leading '/'), as the path is printed everywhere else
        info = {"path": path.replace("\\", "/").strip("/"), "name": name, "parent_oid": parent_oid,
                "storage": DATA_UNKNOWN, "value_len": len(vd)}     # C7 / N161: no retired words (set below)

        if resident:
            info["oid"] = None
            if len(vd) >= 0x60:
                info.update({
                    "created": _forefst.ft_iso(le64(vd, 0x28)),
                    "modified": _forefst.ft_iso(le64(vd, 0x30)),
                    "changed": _forefst.ft_iso(le64(vd, 0x38)),
                    "accessed": _forefst.ft_iso(le64(vd, 0x40)),
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
            # N213 (1.14.0): with page context, so the rows of an embedded index node (E73) are read too
            for k, v in parse_resident_btree_rows(vd, (f, ps, cs, tr)):
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
                            "time": _forefst.ft_iso(le64(v, 0x4C)) if len(v) >= 0x54 else ""})
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
                    "created": _forefst.ft_iso(le64(vd, 0x10)),
                    "modified": _forefst.ft_iso(le64(vd, 0x18)),
                    "changed": _forefst.ft_iso(le64(vd, 0x20)),
                    "accessed": _forefst.ft_iso(le64(vd, 0x28)),
                    "file_attrs": le32(vd, 0x40),
                    "file_size": le64(vd, 0x38) if len(vd) >= 0x40 else 0})
                info["is_dir"] = bool(info["file_attrs"] & 0x10000000)
            # val+0x08 is the child's own OID only for a DIRECTORY; for a non-resident FILE it is the
            # home-dir backref (not the file's OID -- files have no own OID). #327 / --oid collision fix.
            if info.get("is_dir"):
                info["oid"] = child_oid
            else:
                info["oid"] = None                     # K1 / N285 (1.14.0): a file has no OID of its own (was 0)
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

        # Consistency with forefst: forefst's OWN `details` resolves a FILE via walk_directory_tree and uses
        # that record. Do the same so residency (F5/B2), SecurityId and USN match files/attributes/summary
        # exactly -- the record carries the collision-safe backing resolution we must not re-derive by hand.
        _m = None
        if not info.get("is_dir"):
            # Keyed on what resolve_path RESOLVED (parent OID + the entry's own name), not on the typed string:
            # resolve_path accepts another letter case, '//' and '/./', and an exact-string lookup then missed
            # the record and fell back to the name row's copies and the old storage words.
            _nm = (kd[4:].decode("utf-16-le", errors="replace").rstrip("\x00")
                   if kd is not None and len(kd) > 4 else name)
            # N155 (1.14.0): the whole tree (a depth of 100 left a deeper file to the name row's copies)
            _walk = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, DEFAULT_DEPTH, True)
            _m = next((r for r in _walk
                       if not r.get("is_dir") and r.get("parent_oid") == parent_oid and r.get("name") == _nm), None)
            if _m is None:
                # the walk does not list it: say so rather than guess the data residency from the row length
                info["storage"] = DATA_UNKNOWN
                info["record_placement"] = "embedded" if len(vd) > 84 else "split"
            if _m is not None:
                resident = _m.get("is_resident", resident)
                # E87: `storage` is the data residency `files` reports; it held the name row's length test
                # (placement) in JSON and the walk's raw flag in text -- two meanings in one command.
                info["storage"] = _data_residency(_m) or DATA_UNKNOWN
                info["record_placement"] = _record_placement(_m)
                info["file_attrs"] = _m.get("file_attrs", info.get("file_attrs", 0))
                info["snapshot_count"] = _m.get("snapshot_count", info.get("snapshot_count", 0))
                # N150 (1.14.0): the OBJECT's size -- a split hard-link name's row caches a copy that goes stale -- and
                # its streams and reparse point, from the record `files` and forefst `details` use
                info["file_size"] = _m.get("file_size", info.get("file_size", 0))
                if _m.get("allocated_size") is not None:
                    info["allocated_size"] = _m["allocated_size"]
                if _m.get("has_ads"):
                    _ast = _m.get("ads_storage") or {}
                    info["ads"] = [{"name": n, "residency": _ast.get(n, DATA_UNKNOWN)} for n in _m.get("ads_list") or []]
                if _m.get("reparse_tag_value"):
                    info["reparse_tag"] = _m["reparse_tag_value"]
                    info["reparse_target"] = _m.get("reparse_target", "")
                if _m.get("security_id"):
                    info["security_id"] = _m["security_id"]
                    info.pop("security_unavailable", None)
                if _m.get("usn"):
                    info["last_usn"] = _m["usn"]
                    info.setdefault("usn_journal_id", info.get("usn_journal_id", 0))

        if info.get("is_dir"):
            # C7 / N161 (1.14.0): a directory has no data residency (`files` leaves it blank); its row's placement
            info["storage"] = ""
            info["record_placement"] = "embedded" if len(vd) > 84 else "split"
        if args["json"]:
            # N285 / N497 (1.14.0, Q8 B): forefst's record -- the `files` row of the object (its ObjectRef, HomeOID,
            # FileID, times, attributes, SecurityId, owner, residency and placement, under `files`' names and in its
            # forms), then what this command adds: the row's value length and its sub-records, the streams ONCE
            # (name, size, residency; they were listed twice). 1.13.1 wrote its own dialect: decimal OIDs and
            # attribute words, times in whole seconds, no identity, `oid` 0 for a split record.
            _rec = None
            if info.get("is_dir"):
                _walk = walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, DEFAULT_DEPTH, True)
                _m = next((r for r in _walk if r.get("is_dir") and r.get("oid") == info.get("oid")), None)
            if _m is not None:
                _rec = _forefst._build_record(_m, _forefst.build_security_map(f, ps, cs, tr, obj_map),
                                              "%d.%d" % (vmaj, vmin), _forefst._build_oid2path(_walk))
                _subs = info.get("subrecords") or {}
                _sizes = {a["name"]: a["size"] for a in _subs.get("ads", [])}
                _rec["ValueLength"] = info.get("value_len")
                # N553 (b) (1.14.0): what the text prints, null when this command did not read it -- the journal id
                # (K12's form) and the packed EA size
                _rec["USNJournalID"] = ("0x%016x" % info["usn_journal_id"]
                                        if info.get("last_usn") and info.get("usn_journal_id") is not None else None)
                _rec["PackedEASize"] = info.get("packed_ea_size")
                _rec["Streams"] = [{"Name": a["name"], "Size": _sizes.get(a["name"]),
                                    "DataResidency": a["residency"]} for a in info.get("ads") or []] or \
                    [{"Name": n, "Size": z, "DataResidency": None} for n, z in _sizes.items()]
                if _subs:
                    _rec["SubRecords"] = {k: v for k, v in _subs.items() if k != "ads"}
            _print_json(_rec if _rec is not None else info, {"name": "FileName", "storage": "DataResidency",
                                                              "home_backref": "HomeOID", "value_len": "ValueLength",
                                                              "data_size_alloc": "AllocatedSize"})
            return 0

        W = 78
        print("=" * W); print(f"File Details — {path}"); print("=" * W)
        print(f"  Name:           {name}")
        if _m is not None:
            print(f"  Storage:        {info['storage']} (record "
                  + ("embedded in the parent directory row" if info["record_placement"] == "embedded"
                     else "split out to its own type-0x40 record") + "; no OID of its own)")
        elif not info.get("is_dir"):
            print(f"  Storage:        {DATA_UNKNOWN} (record {info['record_placement']}; the directory walk did not "
                  f"list this path)")
        elif resident:
            print("  Storage:        directory (record embedded in the parent directory row)")       # C7 / N161
        else:
            print(f"  Storage:        directory (OID {_hx(info['oid'])}, its own B+-tree)")
        # FileRef identity (matches forefst `details` and `files` ObjectRef): HomeOid:FileId. home_oid is the
        # CREATION directory, frozen -- so home_oid != current parent flags a relocated (moved) or
        # cross-directory hard-linked name. Taken from the walk record `files` uses; only a SPLIT row carries
        # it at value+0x08/+0x00. Gating that read on the walk's raw is_resident flag ("embedded AND inline")
        # sent every embedded file whose bytes are in extents down it, printing two unrelated fields of the
        # long row as a FileRef ('0x1e000000001:0x10028000000a8') and a false "relocated" line.
        if not info.get("is_dir"):
            _hb = _fi = 0
            if _m is not None:
                _hb, _fi = _m.get("home_oid") or 0, _m.get("file_id") or 0
            elif vd is not None and 0x10 <= len(vd) <= 84:
                _hb, _fi = le64(vd, 0x08), le64(vd, 0x00)
            if _hb and _fi:
                print(f"  ObjectRef:      0x{_hb:x}:0x{_fi:x}   (HomeOID:FileID, the stable file reference)")   # N497
                if _hb != parent_oid:
                    print(f"  Home directory: 0x{_hb:x}   created here; current parent 0x{parent_oid:x} (relocated/hard-linked)")
        print(f"  Parent OID:     {_hx(parent_oid)}")
        if "is_dir" in info and info["is_dir"]:
            print("  Type:           DIRECTORY")
            if info.get("oid"):
                print(f"  ObjectRef:      {_hx(info['oid'])}:0x0   (a directory is its own home, ordinal 0)")   # K2
        print(f"  File size:      {_forefst.count_noun(info.get('file_size', 0), 'byte')}")
        # N498 (1.14.0): one label for the allocated size, whatever the record's placement (the walk record's value
        # where it is known, else the row's $SI+0x38)
        _al = info.get("allocated_size") if info.get("allocated_size") is not None else info.get("data_size_alloc")
        if _al is not None:
            print(f"  Allocated size: {_forefst.count_noun(_al, 'byte')}")
        fa = info.get("file_attrs", 0)
        # K14 (1.14.0): forefst's text form, every bit -- `0x20 (Archive)`, `0x0 (none set)`
        print(f"  Attributes:     {_forefst.flag_text(fa, FILE_ATTR_FLAGS)}")
        if "created" in info:
            print(f"  Created:        {info['created'] or '(none)'}")
            print(f"  Modified:       {info['modified'] or '(none)'}")
            print(f"  Changed:        {info['changed'] or '(none)'}")                                   # K21: `files`' word
            print(f"  Accessed:       {info['accessed'] or '(none)'}")
            print(f"                  {_forefst._ACCESSED_NOTE}")                                 # PLAN 10.2 G2
        if info.get("security_unavailable"):
            print("  SecurityId:     n/a (a split record: not stored in the directory entry)")       # C7 / N161
        else:
            print(f"  SecurityId:     {_forefst.security_id_text(info.get('security_id', 0))}  (resolves in OID 0x530)")   # K3
        if "last_usn" in info:
            # N543 (b) (1.14.0): 0 is no journal record -- `(none)`, as forefst `details` and the JSON (null) say it
            if info["last_usn"]:
                print(f"  USN:            {info['last_usn']}  ($UsnJrnl:$J byte offset)")                 # K21: `files`' word
                print(f"  USN journal ID: 0x{info['usn_journal_id']:016x}")                              # K12
            else:
                print("  USN:            (none)")
            if info.get("reparse_tag"):
                print(f"  ReparseTag:     {_forefst.reparse_tag_str(info['reparse_tag'])}")      # review RE1-6
            if info.get("packed_ea_size"):
                print(f"  PackedEaSize:   {info['packed_ea_size']}")
        if "subrecords" in info:
            # Show the inline sub-records for ANY long-value entry (len>84): a file whose residency was just
            # corrected to NON-RESIDENT (F5) still carries its ADS/snapshot/EA/reparse chain inline, so keep
            # listing it -- only the Storage LABEL above changed, not the on-disk inline record.
            s = info["subrecords"]
            print()
            print(f"  Sub-records:    {len(s['data'])} $DATA, {len(s['ads'])} ADS, "
                  f"{len(s['snapshots'])} snapshot(s), {len(s['ea'])} $EA, {len(s['reparse'])} reparse")
            for d in s["data"]:
                print(f"    $DATA  {d['name']:<20} {_forefst.count_noun(d['size'], 'byte')}")
            for a in s["ads"]:
                print(f"    ADS    {a['name']:<20} {_forefst.count_noun(a['size'], 'byte')}")
            for sn in s["snapshots"]:
                print(f"    SNAP   {sn['name']:<20} {_forefst.count_noun(sn['size'], 'byte')}  idx=0x{sn['stream_idx']:x}  {sn['time'] or '(none)'}")
            if s["snapshots"]:
                print(f"    → export snapshot versions with:  snapshots --file {name} --extract DIR")
            for e in s["ea"]:
                print(f"    $EA    {e['name']:<20} {_forefst.count_noun(e['len'], 'byte')}")
            for rp in s["reparse"]:
                # N498 (1.14.0): the tag once -- the ReparseTag line above carries it when it was printed
                print("    REPARSE" + ("" if info.get("reparse_tag") and "last_usn" in info else
                                       f" tag=0x{rp['tag']:08x}"))
        elif info.get("snapshot_count"):
            print(f"  Snapshots:      {info['snapshot_count']} (use snapshots --file {name})")
        if info.get("ads") and "subrecords" not in info:
            # N150 / N284: a split record's streams are in its backing (the walk reads them, T9)
            print(f"  Streams:        {len(info['ads'])}")
            for a in info["ads"]:
                print(f"    ADS    {a['name']:<20} {a['residency']}")
        if info.get("reparse_target"):
            # E1 close (review RE1-6): an embedded record's target too (it was printed only without sub-records)
            print(f"  Reparse target: {info['reparse_target']}")
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
    # N209 (1.14.0, decision 22): the most serious section result -- `all` returned 0 whatever its sections found
    # (`summary` printing "Redundancy findings (exit code 2)" on labFbeforereboot; every section dying on a partition
    # image read without --partition-start). 2 when a section exits 2, or when some sections die while others read
    # the volume (it is readable: work not completed, decision 26); 1 only when every section dies.
    rcs = []
    for name in sections:
        print(f"\n{'='*78}")
        print(f"  refsanalysis: {name}")
        print(f"{'='*78}\n")
        handler = _HANDLERS.get(name)
        if handler:
            try:
                rc = handler(image, [], partition_start)
                rcs.append(0 if rc is None else rc)
            except SystemExit as e:
                rcs.append(e.code if isinstance(e.code, int) else 1)
                print(f"\n  [{name}] failed (exit {rcs[-1]})", file=sys.stderr)
    if rcs and all(r == 1 for r in rcs):
        return 1
    return 2 if any(r for r in rcs) else 0


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
    "allocators": cmd_allocators,
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
        sig = oem_id_text(sector)            # N142 (Q23): the 8-byte OEM id only, no control byte
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
    computed_csum = _forefst.boot_sector_checksum(bytes(sector))[1]        # C2-6: over the copy's own +0x14
    algo = _u16le(fields["checksum_algo"])
    ver = f"{fields['version'][0]}.{fields['version'][1]}"
    vol_flags = _u32le(fields["volume_flags"])
    serial = _u64le(fields["serial"])
    container = _u64le(fields["container_size"])
    guid_raw = fields["format_guid"]
    guid_str = _extended_guid_text(guid_raw)                                   # N493: one text with `boot`

    print()
    print("  Field                   Offset   Raw bytes                                    Interpreted")
    print("  " + "-" * 110)
    for name, offset, size, desc in _VBR_FIELDS:
        raw = _hexbytes(sector[offset:offset + size])
        if name == "fs_name":       interp = _ascii_clean(fields[name])
        elif name == "fsrs_id":     interp = _ascii_clean(fields[name])
        elif name == "vbr_size":    interp = f"{vbr_size}"
        elif name == "checksum":
            m = "OK" if stored_csum == computed_csum else f"MISMATCH (computed={_cksum_text(computed_csum)})"
            interp = f"0x{stored_csum:04x} [{m}]"
        elif name == "version":         interp = ver
        elif name == "checksum_algo":   interp = _checksum_selector_text(algo, vol_flags)
        elif name == "volume_flags":    interp = _volume_flags_text(vol_flags)            # N543 (c)
        elif name == "serial":          interp = f"0x{serial:016x}"
        elif name == "container_size":
            interp = (_forefst.size_text(container) if container else _CONTAINER_ZERO_TEXT)            # R3
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
            interp = f"{spc} (cluster = {_human_size(spc * bps)})"
        else: interp = ""
        print(f"  {desc:<25s} 0x{offset:<6x} {raw:<44s} {interp}")
        if name == "volume_flags" and vol_flags:      # N493: what refs.sys does with each bit, under the value
            print(f"  {'':<25s} {'':<8s} {'':<44s} {_volume_flags_description(vol_flags)}")
    print()

def _diagnose_fixboot(sector):
    """Detect refsutil fixboot damage. Returns list of issues."""
    issues = []
    container = _u64le(sector[0x40:0x48])
    if container == 0:
        # N365 (1.14.0, read twice: 26100.8115/.9549 and 26100.9444, 17134): the driver puts 64 MiB there when it
        # mounts the volume, and a writable mount writes it back; nothing read supports "mount may fail"
        issues.append(("container_size is zero", 0x40, 8, sector[0x40:0x48],
            "refsutil fixboot zeroes this field. When it mounts the volume the driver puts 64 MiB (0x4000000) in its "
            "copy, and a writable mount writes that back to the boot sector."))
    serial = _u64le(sector[0x38:0x40])
    if serial == 0:
        issues.append(("volume_serial is zero", 0x38, 8, sector[0x38:0x40],
            "refsutil fixboot zeroes the serial."))
    guid = sector[0x48:0x58]
    major_v = sector[0x28]
    minor_v = sector[0x29]
    # B8/K050: an implausible version is itself damage, AND it corrupts every check below it. The field
    # is read one byte at a time, so a hand-edited 0x6666 reads as minor 0x66 = 102, every `minor_v >= 14`
    # branch is taken, and an edited volume_flags then passes as a valid 3.14 value. ReFS formats seen in
    # the corpus are 3.4 / 3.7 / 3.9 / 3.10 / 3.14; major is always 3.
    if major_v != 3 or minor_v > 20:
        # N444 (1.14.0): the formats known, not a corpus count (and 3.15 is no volume format, E96)
        issues.append((f"implausible version {major_v}.{minor_v}", 0x28, 2, sector[0x28:0x2A],
            "ReFS volumes are 3.x: the formats known are 3.4, 3.7, 3.9, 3.10 and 3.14 (3.15 is the drivers' version "
            "stamp). A version outside that range is damage or a hand edit, and it also makes every version-gated "
            "check below unreliable."))
    if guid == b"\x00" * 16 and minor_v >= 14 and container == 0:
        # an upgraded volume keeps the GUID it was formatted with (0 before 3.14): a zero GUID is fixboot's only beside
        # its other marks
        issues.append(("format_guid is zero on a 3.14 volume", 0x48, 16, guid,
            "refsutil fixboot zeroes this field (a volume upgraded to 3.14 also carries 0 here)."))
    algo = _u16le(sector[0x2A:0x2C])
    flags = _u32le(sector[0x2C:0x30])
    # N154 (b) (1.14.0; InitializeVcbFromBootSector, 26100.8115 / .9444 / Insider 29574 alike): the checksum selector the
    # driver uses is +0x2A only when the flags carry 0x40, and 2 (CRC64) otherwise; 17134 does not read +0x2A. So 0
    # there is what a healthy upgraded volume carries (flags 0x06): it is a finding only when 0x40 says it is read.
    if minor_v >= 14 and algo == 0 and flags & 0x40:
        issues.append(("checksum_algo is 0 while the flags say it is read (0x40)", 0x2A, 2, sector[0x2A:0x2C],
            "With flags bit 0x40 the driver takes the checksum selector from here: 0 names no algorithm."))
    if minor_v >= 14 and container == 0:
        # N154 (a): fixboot rewrites the flags too (0x66 -> 0x04 on the witness); without 0x40 the driver checks pages
        # with CRC64 whatever +0x2A holds -- which a volume whose pages carry SHA-256 does not pass
        issues.append((f"volume_flags 0x{flags:x} beside fixboot's other marks", 0x2C, 4, sector[0x2C:0x30],
            "refsutil fixboot rewrites the flags (0x04 where the volume carried 0x66). Without bit 0x40 the driver "
            "uses checksum selector 2 (CRC64) whatever +0x2a holds; the flags a volume carried are not known from "
            "this sector, so no value is proposed."))
    elif minor_v >= 14 and flags == 0:
        issues.append(("volume_flags is zero on a 3.14 volume", 0x2C, 4, sector[0x2C:0x30],
            "A writable mount sets 0x02 in this field (RefsMountVolume): 0 means no writable mount since it was "
            "cleared."))
    # E1 close (review RE1-1): no flags expectation for a format before 3.14. The branch called every such volume "3.4"
    # and required 0x02 or 0x06, so the healthy 3.7 / 3.9 (0x26) and 3.10 (0x66) volumes were diagnosed -- and, with
    # B14's exit rule, exited 2; the flags are the volume's format and run-time state, no reading names a valid set
    stored, computed = _forefst.boot_sector_checksum(bytes(sector))       # C2-6: over the copy's own +0x14
    if computed is not None and stored != computed:
        issues.append(("checksum mismatch", 0x16, 2, sector[0x16:0x18],
            f"Stored=0x{stored:04x} vs computed=0x{computed:04x}. VBR modified without recalculating."))
    return issues

def _propose_repair(sector):
    """Propose fixboot repair actions -- only bytes the driver's own reading supports (N154, 1.14.0): the container size
    the driver itself puts there (64 MiB, N365). No checksum selector and no flags: the values a volume carried are not
    known from this sector -- the selector 2 proposed for every 3.14 sector holding 0 was wrong on a healthy upgraded
    volume (it carries 0, flags 0x06, and the driver then uses 2) and on a SHA-256 volume (4), and the flags 0x66
    proposed for a zero field was a guess. A sibling copy that verifies is the source for those (`bootedit repair`'s
    copy restore)."""
    repairs = []
    if _u64le(sector[0x40:0x48]) == 0:
        repairs.append({"field": "container_size", "offset": 0x40, "size": 8,
            "current": sector[0x40:0x48], "proposed": struct.pack("<Q", 0x4000000),
            "reason": "The value the driver puts there when it mounts the volume: 0x4000000 = 64 MiB."})
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
    print(f"  Source size: {_forefst.count_noun(src_size, 'byte')} ({_human_size(src_size)})")
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
    print(f"  Done: {written}/{_forefst.count_noun(total, 'block')} written ({written * 100 // max(total, 1)}% density)")
    try:
        disk = os.stat(out).st_blocks * 512
        print(f"  Logical: {_forefst.count_noun(src_size, 'byte')}, Disk: {_forefst.count_noun(disk, 'byte')} ({disk * 100 // src_size}%)")
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
    print("\n  [SAFE MODE] Original image will NOT be modified.")
    _make_sparse_copy(image, out)
    print(f"  Working on copy: {out}\n")
    return out, _find_boot_offset(out, ps)

# B14 (1.14.0; PLAN_1.13.2 decision 13): the copy restore of `bootedit repair`. It was held back (dev-only) from 1.11.3 to
# 1.13.2, and in that form it read and wrote the backup boot sector at `lba * 512` (on lab314_4kn, 4096 bytes per sector,
# offset 0x207ffe00 instead of 0xfcfff000), restored a primary from a backup that keeps an older version, called a copy
# "OK" whose root fails its digest or whose checksum cannot be verified, said "BAD-signature" for a checkpoint copy it
# could not read, and "ALL COPIES VERIFY" over a checkpoint copy it does not restore.
_CHKP_REPORT_ONLY = ("a checkpoint copy is not restored: each copy is its own record of the volume's state, so the "
                     "other copy's bytes are no source for it; `chkp -v` and forefst `integrity` show what fails")


def _image_end(f):
    """The image's length (the file's end): no restore writes past it."""
    pos = f.tell()
    f.seek(0, 2)
    n = f.tell()
    f.seek(pos)
    return n


def _vbr_runs_text(old, new):
    """The byte runs a boot-sector restore changes, each with the VBR fields it covers (`_VBR_FIELDS`)."""
    out = []
    for o, n in _byte_diff_runs(old, new, limit=16):
        names = [nm for nm, fo, fs, _d in _VBR_FIELDS if fo < o + n and o < fo + fs]
        out.append(("0x%x" % o if n == 1 else "0x%x-0x%x" % (o, o + n - 1))
                   + (" (%s)" % ", ".join(names) if names else ""))
    return ", ".join(out) if out else "none"


def _plan_redundancy_repairs(f, ps, cs, chkp_lcns):
    """Check every redundant copy of the bootstrap -- the two boot sectors, the three superblocks, the two checkpoints --
    and plan the restores that can be made from a copy that passes. Returns {"lines": the report, "repairs": [{label,
    source, byte_off, length, new_bytes, note}], "refused": [(label, why)] for the failing copies that are not
    restored, "failing": the labels of the copies that fail (or could not be read or checked)}.

    VBR. One copy is one sector of the VBR's bytes per sector: refs.sys reads and writes the boot sector as one sector of
    the device's sector size (RefsWriteBootSector, 26100.9444 @140099c20: VCB+0x114 bytes at T-1, then at 0, from one
    buffer; RefsPerformVerifyOperation requires +0x20 to equal VCB+0x114), so on a 4Kn volume the whole 4096-byte
    sector is restored (lab314_4kn: its bytes after +0x200 are not zero, and equal in the two copies). A primary that
    fails a boot-sector test (`boot_sector_copy`) is restored from the backup the volume is read from -- the first copy
    found that passes every test and ends at its own last sector -- unless the two record different versions, or the
    backup records a version below 3.14 where the volume's own records show 3.14 ($VOLUME_INFORMATION and the checkpoint
    flags, `boot_sector_decode_version`; or the checkpoint copy in use alone, flags 0x600): refs.sys writes a version
    upgrade to sector 0 only (RefsUpgradeVersionInBootSector runs before the volume object that gates the backup write
    exists), so such a backup keeps the earlier version (win10to11refs4g: 3.4 behind a 3.14 primary), and which version
    is the volume's is not decided here. A backup at T-1 that carries the ReFS signature and fails
    is restored from a primary that passes: refs.sys writes the two copies from one buffer. A position without the
    signature is not written: refs.sys writes the backup boot sector only under conditions an image does not record.

    SUPB. The copies at LCN 0x1e, N-2 and N-3 (N the volume's clusters) that fail refs.sys's ValidateSuperBlock tests
    (`supb_validate`) are rebuilt from the copy the volume is read from when that copy passes them: refs.sys's
    ReadSuperBlock rewrites every other copy from the copy it chose. The rebuilt cluster is the source's with its own
    LCN set to the target's (+0x20 and the first u64 of the self-descriptor its +0x78 declares, which holds the copy's
    own LCN on every superblock copy of the corpus, 345 of 345) and the self-checksum recomputed; it must pass the same
    tests at the target LCN before it is planned. Measured on the corpus (2026-10-29, 115 ReFS volumes): rebuilt from
    each copy that passes, the cluster equals every other copy that passes byte for byte (682 of 682 pairs). refs.sys's
    own rewrite stamps the copy with the clocks of that moment (+0x10, +0x18), so a copy the driver rewrote can differ
    there. A checksum type the tool does not compute cannot be rebuilt (no digest).

    CHKP. Reported only (`_CHKP_REPORT_ONLY`).

    No restore writes past the end of the image."""
    bk = _scan_backup_copies(f, ps, cs, chkp_lcns)
    end = _image_end(f)
    lines, repairs, refused, failing = [], [], [], []
    bsc = boot_sector_copy(f, ps)
    geo = bsc["geometry"]
    prim = bsc["primary"] or b""
    sel = checkpoint_select(f, ps, cs, chkp_lcns, require_roots=True)
    _ckf = (sel.get("in_use") or {}).get("flags")

    # ---- VBR ----
    read_bytes = bsc["bytes"] if bsc["bytes"] is not None else prim
    bps = _vbr_bytes_per_sector(read_bytes)
    vb = (bk.get("vbr") or {}).get("backup")
    p_fail = bsc["failures"]
    lines.append("  VBR  primary  sector 0 (offset 0x%x): %s"
                 % (ps, "OK" if not p_fail else "FAILS: " + "; ".join(t for _k, t in p_fail)))
    b_off = vb["byte_offset"] if vb else None
    b_state, b_bytes = None, None
    if b_off is None:
        lines.append("  VBR  backup   not located: the boot sector the volume is read from declares no volume size")
        failing.append("VBR backup")
        refused.append(("VBR backup", "not located: the boot sector the volume is read from declares no volume size"))
    else:
        _where = "sector %d (offset 0x%x)" % ((b_off - ps) // bps, b_off)
        try:
            b_bytes = _seek_read(f, b_off, bps)
        except OSError as e:
            b_bytes, b_state = b"", "not read (%s)" % e
        if b_state is None and len(b_bytes) < 512:
            b_state = "not read (the image ends before it)"
        elif b_state is None and len(b_bytes) < bps:
            # E1 close (review RE1-12): one copy is one sector; a 4Kn image that ends inside it holds part of it only
            b_state = "not read in full (the image ends inside it: %d of %d bytes)" % (len(b_bytes), bps)
        elif b_state is None and b_bytes[3:7] != b"ReFS":
            b_state = "no ReFS boot sector there" + (" (all zeros)" if not any(b_bytes) else "")
        elif b_state is None:
            _bf = boot_sector_failures(b_bytes, _boot_sector_ss(geo, b_bytes), geo["rounded"])
            b_state = "OK" if not _bf else "FAILS: " + "; ".join(t for _k, t in _bf)
            if not _bf and not p_fail and b_bytes[:512] != prim[:512]:
                b_state += " (its bytes differ from the primary's at %s)" % _vbr_runs_text(prim[:512], b_bytes[:512])
        lines.append("  VBR  backup   %s: %s" % (_where, b_state))
        if not b_state.startswith("OK"):
            failing.append("VBR backup")
    if p_fail:
        failing.append("VBR primary")
        if bsc["source"] == "backup" and bsc["bytes"] is not None and len(_seek_read(f, bsc["offset"], bps)) < bps:
            refused.append(("VBR primary sector 0", "the backup boot sector the volume is read from is not in the image "
                                                    "in full (the image ends inside its sector)"))
        elif bsc["source"] == "backup" and bsc["bytes"] is not None:
            src_off = bsc["offset"]
            src = _seek_read(f, src_off, bps)
            _src_name = "the backup boot sector at offset 0x%x (the copy the volume is read from)" % src_off
            _why = None
            if prim[3:7] == b"ReFS" and len(prim) >= 0x2A and prim[0x28:0x2A] != src[0x28:0x2A]:
                _why = ("the primary records version %d.%d and %s version %d.%d: refs.sys writes a version upgrade to "
                        "sector 0 only, so a backup boot sector can keep an earlier version, and which of the two is the "
                        "volume's is not decided from the two copies" % (prim[0x28], prim[0x29], _src_name, src[0x28],
                                                                        src[0x29]))
            elif (bsc.get("decoded") or {}).get("reason"):
                _why = bsc["decoded"]["reason"]
            elif (src[0x28], src[0x29]) < (3, 14) and _ckf is not None and (_ckf & 0x600) == 0x600:
                # E1 close: the checkpoint in use alone shows a 3.14 volume ($VOLUME_INFORMATION, the decode rule's
                # second witness, may be unreadable): a backup with an earlier version is not the primary's content
                _why = ("%s records version %d.%d, and the checkpoint copy in use (flags 0x%x, 0x600 set) shows a 3.14 "
                        "volume: refs.sys writes a version upgrade to sector 0 only, so a backup boot sector can keep an "
                        "earlier version" % (_src_name, src[0x28], src[0x29], _ckf))
            elif ps + bps > end:
                _why = "the image ends inside sector 0"
            if _why:
                refused.append(("VBR primary sector 0", _why))
            else:
                repairs.append({"label": "VBR primary sector 0", "source": _src_name, "byte_off": ps, "length": bps,
                                "new_bytes": src,
                                "note": "the restore changes %s" % _vbr_runs_text(prim[:512], src[:512])})
        else:
            refused.append(("VBR primary sector 0", "no backup boot sector passes the boot-sector tests"))
    if b_off is not None and not b_state.startswith("OK"):
        if b_state.startswith("not read"):
            refused.append(("VBR backup", "the image ends before it or inside it: this command does not extend the "
                                          "image"))
        elif b_bytes[3:7] != b"ReFS":
            refused.append(("VBR backup", "no ReFS boot sector there: this command writes no backup boot sector where "
                                          "none is (refs.sys writes it only under conditions an image does not record)"))
        elif p_fail:
            refused.append(("VBR backup", "the primary boot sector fails too: no copy passes the boot-sector tests"))
        elif b_off + bps > end:
            refused.append(("VBR backup", "the image ends inside it: this command does not extend the image"))
        else:
            src = _seek_read(f, ps, bps)
            repairs.append({"label": "VBR backup sector %d" % ((b_off - ps) // bps),
                            "source": "the primary boot sector (sector 0, offset 0x%x)" % ps, "byte_off": b_off,
                            "length": bps, "new_bytes": src,
                            "note": "the restore changes %s" % _vbr_runs_text(b_bytes[:512], src[:512])})

    # ---- SUPB ----
    n = volume_length(read_bytes) // cs
    positions = (SUPB_LCN, n - 2, n - 3)
    supb = bk.get("supb", [])
    src_rec = next((r for r in supb if r.get("used") and r.get("ok")), None)
    blocks = {}
    for r in supb:
        lcn = r["lcn"]
        _name = "SUPB %-8s LCN 0x%x" % ("primary" if lcn == SUPB_LCN else "backup", lcn)
        if r.get("damaged") and r.get("found_signature") is None:
            st, blk = "not read (no bytes at that address in the image)", None
        else:
            blk = _seek_read(f, r["byte_offset"], cs)
            if len(blk) < cs:
                st = "not read in full (the image ends inside it)"
            elif r.get("damaged"):
                st = "no SUPB signature" + (" (all zeros)" if r.get("all_zero") else "")
            else:
                v = supb_validate(blk, cs, lcn, n)
                if v["ok"] and v["cksum_ok"]:
                    st = "OK (%s)" % v["ckname"]
                elif v["ok"]:
                    st = ("its self-checksum cannot be verified (%s); it passes refs.sys's other superblock tests"
                          % v["ckname"])
                else:
                    st = "FAILS: " + "; ".join(t for _k, t in v["failures"])
        if lcn not in positions:
            lines.append("  %s: %s (not a superblock position: 0x1e, N-2 or N-3)" % (_name, st))
            continue
        lines.append("  %s: %s%s" % (_name, st, " (the copy the volume is read from)" if r.get("used") else ""))
        if r.get("ok"):
            if not st.startswith("OK"):
                failing.append(" ".join(_name.split()))             # cannot be verified: work not complete
            continue
        failing.append(" ".join(_name.split()))
        label = " ".join(_name.split())
        if blk is None or len(blk) < cs or r["byte_offset"] + cs > end:
            refused.append((label, "the image ends before it: this command does not extend the image"))
            continue
        if src_rec is None:
            refused.append((label, "no superblock copy the volume is read from passes refs.sys's superblock tests"))
            continue
        src_blk = blocks.get(src_rec["lcn"]) or _seek_read(f, src_rec["byte_offset"], cs)
        blocks[src_rec["lcn"]] = src_blk
        recipe = _self_checksum_recipe(src_blk, cs)
        if recipe is None or recipe[0] != le32(src_blk, 0x78):
            refused.append((label, "the self-checksum of the source copy (LCN 0x%x) cannot be computed here (%s)"
                            % (src_rec["lcn"], src_rec.get("ckname") or "-")))
            continue
        t = bytearray(src_blk)
        t[0x20:0x28] = int(lcn).to_bytes(8, "little")
        t[recipe[0]:recipe[0] + 8] = int(lcn).to_bytes(8, "little")
        fixed = bytes(_recompute_self_checksum(bytes(t), cs, recipe))[:cs]
        vv = supb_validate(fixed, cs, lcn, n)
        if not vv["ok"]:
            refused.append((label, "the rebuilt copy would fail: " + "; ".join(x for _k, x in vv["failures"])))
            continue
        repairs.append({"label": label, "source": "SUPB LCN 0x%x (the copy the volume is read from)" % src_rec["lcn"],
                        "byte_off": r["byte_offset"], "length": cs, "new_bytes": fixed,
                        "note": "its own LCN set to 0x%x (+0x20 and the self-descriptor) and its self-checksum "
                                "recomputed" % lcn})

    # ---- CHKP (reported only) ----
    bad_chkp = False
    for c in sel["copies"]:
        role = _chkp_role(sel, c)
        head = "  CHKP          LCN 0x%x%s%s" % (c["lcn"], " vclock=%d" % c["vc"] if c.get("vc") is not None else "",
                                                 " (%s)" % role if role else "")
        if c.get("unreadable") or not c["sig_ok"]:
            st, ok = c.get("unreadable") or "it carries no CHKP signature", False
        elif c["cksum_ok"] is False:
            st, ok = "its self-checksum FAILED (%s)" % c["ckname"], False
        elif c["cksum_ok"] is None:
            st, ok = "its self-checksum cannot be verified (%s)" % c["ckname"], False
        else:
            res, txt = _root_check(c)
            st, ok = ("OK (%s; %s)" % (c["ckname"], txt), True) if res == "OK" else \
                ("self-checksum OK (%s); %s" % (c["ckname"], txt), False)
        if c.get("rejected_by"):
            st, ok = st + "; " + chkp_reject_clause(c["record_tests"]), False
        lines.append("%s: %s" % (head, st))
        if not ok:
            bad_chkp = True
            failing.append("CHKP LCN 0x%x" % c["lcn"])
    if bad_chkp:
        lines.append("    NOTE: " + _CHKP_REPORT_ONLY + ".")
    return {"lines": lines, "repairs": repairs, "refused": refused, "failing": failing}


def _apply_copy_restores(target, repairs, image, log_path):
    """Write each planned restore into `target` (the repaired copy, or the image itself with --inplace), read it back,
    and log it -- source, target offset and length, SHA-256 of the bytes there before and after -- on stdout and in
    `log_path` (appended, UTF-8). Returns the log lines."""
    log = ["refsanalysis %s bootedit repair, %s" % (VERSION, _forefst.now_iso()),          # K5 (1.14.0)
           "  input:  %s" % os.path.abspath(image), "  output: %s" % os.path.abspath(target)]
    with open(target, "r+b") as wf:
        for i, r in enumerate(repairs, 1):
            wf.seek(r["byte_off"])
            before = wf.read(r["length"])
            wf.seek(r["byte_off"])
            wf.write(r["new_bytes"])
            wf.flush()
            wf.seek(r["byte_off"])
            after = wf.read(r["length"])
            if after != r["new_bytes"]:
                die("the restore of %s did not land at offset 0x%x in %s" % (r["label"], r["byte_off"], target))
            log += ["  restore %d: %s" % (i, r["label"]),
                    "    source: %s" % r["source"],
                    "    target: offset 0x%x, %s" % (r["byte_off"], _forefst.count_noun(r["length"], "byte")),
                    "    before: SHA-256 %s" % hashlib.sha256(before).hexdigest(),
                    "    after:  SHA-256 %s" % hashlib.sha256(after).hexdigest(),
                    "    %s" % r["note"]]
    try:
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write("\n".join(log) + "\n")
        log.append("  (logged in %s)" % log_path)
    except OSError as e:
        print("[%s] WARNING: the restore log could not be written to %s: %s" % (PROG, log_path, e), file=sys.stderr)
        _forefst._finding("output not written", "the restore log %s could not be written" % log_path)   # N570: exit 2
    return log

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
            with open(image, "rb") as f: sector = _read_boot_copy(f, bo)          # C2-6
            _validate_vbr(sector, bo)
            sha = hashlib.sha256(sector[:512]).hexdigest()
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
            # --- Phase 1 (B14): check the redundant copies; restore a failing VBR / SUPB copy from one that passes ---
            plan, rc1 = None, 0
            try:
                gf, gps, gcs, gtr, groots, gom, gvmaj, gvmin, gchkp = bootstrap(image, args["partition_start"])
                try:
                    plan = _plan_redundancy_repairs(gf, gps, gcs, gchkp)
                finally:
                    gf.close()
            except (ValueError, OSError) as e:
                print(f"\n  (the copy check was not made: the volume could not be read: {e})")
                rc1 = 2
            if plan is not None:
                print("\nRedundant copies (VBR / SUPB / CHKP):")
                for ln in plan["lines"]: print(ln)
                rc1 = 2 if plan["failing"] else 0
                if plan["repairs"]:
                    print(f"\n{'='*72}\nProposed copy restores ({len(plan['repairs'])}):\n{'='*72}")
                    for r in plan["repairs"]:
                        print(f"  {r['label']}: offset 0x{r['byte_off']:x}, {_forefst.count_noun(r['length'], 'byte')}, from {r['source']};"
                              f" {r['note']}")
                if plan["refused"]:
                    print(f"\nNot restored ({len(plan['refused'])}):")
                    for lab, why in plan["refused"]:
                        print(f"  {lab}: {why}")
            if plan is not None and plan["repairs"]:
                _prim_restored = any(r["byte_off"] == gps and r["label"].startswith("VBR")
                                     for r in plan["repairs"])
                if args["dry_run"]:
                    print("\n[DRY RUN] No changes written.")
                    if _prim_restored:
                        return rc1
                else:
                    if args["inplace"]:
                        if not os.access(image, os.W_OK):
                            print(f"  ERROR: --inplace requested but the image is not writable: {image}",
                                  file=sys.stderr)
                            return 2
                        if input("\nApply the restores to the ORIGINAL image? Type 'YES': ") != "YES":
                            print("Aborted."); return 1
                        target = image; print("\n  [--inplace] Modifying the ORIGINAL image directly.")
                    else:
                        target = args.get("output") or _auto_output(image)
                        print("\n  [SAFE MODE] Original image will NOT be modified.")
                        _make_sparse_copy(image, target); print(f"  Working on copy: {target}")
                    log = _apply_copy_restores(target, plan["repairs"], image, target + ".repair.log")
                    print(f"\nApplied {len(plan['repairs'])} restore(s) to {target}:")
                    for ln in log[3:]: print(ln)
                    try:
                        vf, vps, vcs, vtr, vroots, vom, vvmaj, vvmin, vchkp = bootstrap(target,
                                                                                        args["partition_start"])
                        try:
                            vplan = _plan_redundancy_repairs(vf, vps, vcs, vchkp)
                        finally:
                            vf.close()
                        print("\nPost-repair check of the copies:")
                        for ln in vplan["lines"]: print(ln)
                        if vplan["failing"]:
                            print(f"\n  {len(vplan['failing'])} copy/copies still fail or cannot be checked: "
                                  f"{', '.join(vplan['failing'])}")
                        else:
                            print("\n  Every copy passes its tests.")
                    except (ValueError, OSError) as e:
                        print(f"\n  (the post-repair check was not made: {e})")
                        return 2
                    if not _prim_restored:
                        print(f"\n  The fixboot diagnosis of the primary boot sector is not made in a run that writes"
                              f" restores: run `refsanalysis.py {target} bootedit repair --dry-run` for it.")
                    return rc1
            # --- Phase 2: fixboot VBR-field repair (no redundant copy could restore the primary VBR) ---
            bo = _find_boot_offset(image, args["partition_start"])
            with open(image, "rb") as f: sector = bytearray(_read_boot_copy(f, bo))     # C2-6
            if plan is not None and bytes(sector[3:7]) != b"ReFS":
                # E1 close (review RE1-13): the copies are reported above; the fixboot checks read the fields of a ReFS
                # boot sector, and this primary carries no ReFS signature (`_validate_vbr` stopped with exit 1 here)
                print("\nThe fixboot diagnosis is not made: the primary boot sector carries no ReFS signature.")
                return 2
            _validate_vbr(sector, bo)
            sha = hashlib.sha256(bytes(sector)).hexdigest()
            print(f"\nDiagnosing boot sector at offset 0x{bo:x}")
            print(f"SHA-256: {sha}")
            _display_vbr(sector)

            issues = _diagnose_fixboot(sector)
            if not issues:
                # B8/K050: this used to read "Boot sector appears healthy" -- a whole-volume claim from
                # six fields of ONE sector. The backup VBR, the superblock copies and the checkpoints are
                # not read here at all, so a volume damaged anywhere else was pronounced healthy.
                print("No fixboot damage detected in the checks this command performs.")
                print("  Checked: the PRIMARY boot sector only -- container size, volume serial, format")
                print("           GUID, checksum algorithm, volume flags, version plausibility and the")
                print("           VBR checksum.")
                if plan is not None:
                    # E1 close (review RE1-3): phase 1 checked and reported every bootstrap copy above
                    # review RE1-23: the bootstrap reads more than the copies (the Object Table, the root pages),
                    # but nothing else of the volume is checked here
                    print("  The boot sector, superblock and checkpoint copies are reported above; nothing")
                    print("           else of the volume was checked. This is NOT a clean bill of health for")
                    print("           the volume -- run `forefst.py <image> integrity` for that.")
                else:
                    print("  NOT checked: the backup boot sector, the superblock copies, the checkpoints, or")
                    print("           any metadata beyond this sector. This is NOT a clean bill of health for")
                    print("           the volume -- run `forefst.py <image> integrity` for that.")
                return rc1

            print(f"Found {len(issues)} issue(s):")
            for desc, off, sz, cur, problem in issues:
                print(f"\n  [{desc}]")
                print(f"    Offset: 0x{off:x}-0x{off + sz - 1:x}")
                print(f"    Current: {_hexbytes(cur)}")
                print(f"    Problem: {problem}")

            repairs = _propose_repair(sector)
            if not repairs:
                print("\nNo automatic repairs available.")
                return 2

            print(f"\n{'='*72}\nProposed repairs ({len(repairs)}):\n{'='*72}")
            modified = bytearray(sector)
            for r in repairs:
                print(f"\n  {r['field']} (0x{r['offset']:x}):")
                print(f"    Current:  {_hexbytes(r['current'])}")
                print(f"    Proposed: {_hexbytes(r['proposed'])}")
                print(f"    Reason:   {r['reason']}")
                modified[r["offset"]:r["offset"] + r["size"]] = r["proposed"]

            new_cs = _forefst.boot_sector_checksum(bytes(modified))[1]          # C2-6
            if new_cs is None:
                die("the copy's length at +0x14 is not 88 up to the bytes read: no checksum can be written for it")
            old_cs = _u16le(modified[0x16:0x18])
            modified[0x16:0x18] = struct.pack("<H", new_cs)
            print(f"\n  checksum (0x16): 0x{old_cs:04x} -> 0x{new_cs:04x}")

            if args["dry_run"]:
                print("\n[DRY RUN] No changes written.")
                print(f"Would-be SHA-256: {hashlib.sha256(bytes(modified)).hexdigest()}")
                return 2

            target, target_bo = _bootedit_prepare_write(image, args)
            if args["inplace"]:
                confirm = input("\nApply repairs to ORIGINAL image? Type 'YES': ")
                if confirm != "YES":
                    print("Aborted."); return 1
            with open(target, "r+b") as f:
                f.seek(target_bo); f.write(bytes(modified))
            print(f"Repairs applied at 0x{target_bo:x} in {target}")
            print(f"New SHA-256: {hashlib.sha256(bytes(modified)).hexdigest()}")
            return 2

        elif action == "set":
            if "field" not in args or "value" not in args:
                die("set requires --field FIELD --value VALUE")
            bo = _find_boot_offset(image, args["partition_start"])
            with open(image, "rb") as f: sector = bytearray(_read_boot_copy(f, bo))     # C2-6
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
                print(f"\n  checksum_algo: 0x{val:x}")
            elif field == "volume_flags":
                off, sz = 0x2C, 4; val = int(val_str, 0)
                new_b = struct.pack("<I", val)
                print(f"\n  volume_flags: 0x{val:x}")
            elif field == "container_size":
                off, sz = 0x40, 8; val = int(val_str, 0)
                new_b = struct.pack("<Q", val)
                print(f"\n  container_size: {_forefst.size_text(val)}")             # R3
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

            print(f"  Field:    {field} (offset 0x{off:x}, {_forefst.count_noun(sz, 'byte')})")
            print(f"  Current:  {_hexbytes(old_b)}")
            print(f"  New:      {_hexbytes(new_b)}")
            sector[off:off + sz] = new_b
            new_cs = _forefst.boot_sector_checksum(bytes(sector))[1]            # C2-6
            if new_cs is None:
                die("the copy's length at +0x14 is not 88 up to the bytes read: no checksum can be written for it")
            old_cs = _u16le(sector[0x16:0x18])
            sector[0x16:0x18] = struct.pack("<H", new_cs)
            print(f"  Checksum: 0x{old_cs:04x} -> 0x{new_cs:04x}")

            if args["dry_run"]:
                print("\n[DRY RUN] No changes written.")
                print(f"Would-be SHA-256: {hashlib.sha256(bytes(sector)).hexdigest()}")
                return 0

            target, target_bo = _bootedit_prepare_write(image, args)
            if args["inplace"]:
                confirm = input("\nApply change to ORIGINAL image? Type 'YES': ")
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
                        print(f"  0x{off:x}: 0x{old[off]:02x} -> 0x{new_sector[off]:02x}")
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
  repair [--dry-run]             Restore a failing boot sector / superblock copy from one that
                                 passes (checkpoints reported only); else diagnose fixboot damage
  set --field F --value V [--dry-run]  Modify a VBR field
  import -i FILE [--dry-run]     Import a boot sector from binary file
  sparse -o FILE                 Create a sparse copy of the image

Write options:
  --inplace                      DANGEROUS: modify original image directly
  -o FILE                        Output path for modified copy
                                 (default: <image>_modified.<ext>; repair logs its restores in
                                 <output>.repair.log)
  --dry-run                      Show changes without writing

Fields for 'set' (hex 0x.. or decimal):
  checksum_algo    VBR+0x2a  0=None, 2=CRC64, 4=SHA256
  volume_flags     VBR+0x2c  hex recommended (e.g. 0x66)
  container_size   VBR+0x40  hex (e.g. 0x4000000 = 64 MiB)
  format_guid      VBR+0x48  UUID string, 'zero', or 'random'
  version          VBR+0x28  'major.minor' (e.g. '3.14')
  serial           VBR+0x38  hex (e.g. 0x1234abcd)""")


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
   "opts": [("--json", "emit the summary as a JSON object"),
            ("--mlog", "also read the MLog (forefst `summary --mlog`'s section: one pass over the log)"),
            ("-v, --verbose", "the same as --mlog")],
   "ex": [("summary", "quick volume triage"), ("summary++", "extended overview (OID 0x500 detail)"),
          ("summary++ --json", "machine-readable extended summary")]},
 "summary++": {"tag": "Extended volume summary (OID 0x500 detail + metrics)",
   "desc": ["The extended triage report: everything `summary` shows plus OID 0x500 volume detail and",
            "additional metrics. (forefst's `summary` subcommand is the forensic-grade equivalent.)"],
   "opts": [("--json", "emit the summary as a JSON object"),
            ("--mlog", "also read the MLog (forefst `summary --mlog`'s section: one pass over the log)"),
            ("-v, --verbose", "the same as --mlog")],
   "ex": [("summary++", "extended human-readable report"), ("summary++ --json", "machine-readable")]},
 "all": {"tag": "Run the main structure tools in sequence",
   "desc": ["One-shot structural dump: runs nine structure tools (summary, boot, supb, chkp, schema, objects,",
            "parentchild, containers, files) back-to-back -- not upcase, allocators, oid30, attributes or",
            "details. Redirect to a file to keep it. It exits with its most serious section's result (2 when",
            "a section exits 2 or some sections cannot read the volume while others can; 1 when none can).",
            "Its summary does not read the MLog (`summary --mlog` does), so no MLog finding sets its exit."],
   "opts": [],
   "ex": [("all", "full structural dump"), ("all > structure_dump.txt", "capture the whole report")]},
 "files": {"tag": "List files and directories (lab-format tree)",
   "desc": ["Flat namespace listing from the root (or --oid subtree). -v adds a wide table with decoded",
            "attributes, sizes and modified-times. (forefst's `files` is the forensic CSV/JSON equivalent.)",
            "Metadata only: no file's data is read, so a clean listing says nothing about file contents."],
   "opts": [("-v", "verbose table (Attrs, Size, Modified)"),
            ("--oid 0xNNN", "start the walk at this directory OID (default 0x600)"),
            ("--depth N", "max recursion depth (default: full -- the whole tree)")],
   "ex": [("files", "flat namespace listing"), ("files -v", "verbose table with attributes"),
          ("files --oid 0x705", "list only the subtree under OID 0x705")]},
 "attributes": {"tag": "File attribute deep-dive (EA / WSL / timestamps / flags)",
   "desc": ["Per-file attribute analysis: decoded flags, internal flags, timestamps, EFS/reparse/WSL.",
            "-v adds the decoded Extended-Attributes block ($LXMOD/$LXUID/...). --filter narrows by type."],
   "opts": [("-v", "also decode the Extended Attributes block (WSL $LX*)"),
            ("--filter T", "one of: encrypted, wsl, reparse, snapshot"),
            ("--oid 0xNNN", "start OID (default 0x600)"),
            ("--depth N", "max recursion depth (default: full -- the whole tree)")],
   "ex": [("attributes --filter wsl", "files carrying WSL/Linux metadata"),
          ("attributes -v --filter reparse", "reparse points with decoded buffers"),
          ("attributes -v", "full attribute dump incl. EAs")]},
 "details": {"tag": "Full details for ANY file by path (files have no OID)",
   "desc": ["Complete per-file record addressed by PATH: timestamps, attributes, SecurityId, and the",
            "inline sub-records of a file whose record is embedded ($DATA, ADS, snapshots, $EA, reparse)."],
   "opts": [("/path", "(positional) e.g. /dir/file.txt"), ("--json", "emit the record as JSON")],
   "ex": [("details /hello.txt", "full record of a file whose record is embedded"),
          ("details /dir/bigfile.bin", "a file whose data is in extents"),
          ("details /hello.txt --json", "machine-readable record")]},
 "boot": {"tag": "Boot sector (VBR) analysis",
   "desc": ["Decode the ReFS Volume Boot Record: signature, version, cluster/container size, serial,",
            "checksum. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "verbose / detailed (geometry arithmetic)"),
            ("--verify", "consistency table: the primary's fields, and the checksum of the primary and the backup "
                         "boot sector (the last sector), one row each; the version: 3.x with a minor of at most 14 "
                         "(3.14 is the newest volume format known), and the same as $VOLUME_INFORMATION's unless an upgrade "
                         "explains it (read through the volume, as "
                         "`summary` reads it; not compared when the volume cannot be read); exits 2 on any FAIL row "
                         "(an implausible version is one), "
                         "on a container size (VBR+0x40) of 0, the value `refsutil fixboot` writes, and on a version "
                         "that is not corroborated. Because it reads the volume, it also exits 2 on a condition of the "
                         "volume view, as every command that reads the view does (stated on stderr): the volume read "
                         "from a backup superblock, a checkpoint copy in use whose roots do not match its digests, "
                         "metadata pages that cannot be read"),
            ("--raw", "512-byte hex+ASCII dump"), ("-H", "header banner (SHA-256, offset)")],
   "ex": [("boot", "confirm ReFS + read version/geometry (exits 2 if the checksum fails)"),
          ("boot --verify", "VBR integrity triage"),
          ("boot -vv", "full forensic VBR dump")]},
 "supb": {"tag": "Superblock (SUPB) analysis",
   "desc": ["Decode the superblock: GUID, version, self-descriptor, checkpoint pointers. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "verbose / detailed"),
            ("--verify", "consistency table of the copy shown, plus the self-checksum of every superblock and "
                         "checkpoint copy and the roots 0xc, 7 and 8 of every checkpoint copy against its digests, "
                         "one row each; exits 2 on any row that does not pass"),
            ("--raw", "hex dump of the SUPB page"), ("-H", "header banner")],
   "ex": [("supb", "superblock snapshot: the copy the volume is read from (a backup when the primary is not "
                   "usable; a copy said to have failed when no copy verifies). Exits 2 when it shows such a copy or "
                   "one whose checksum cannot be verified, when it marks a checkpoint copy FAILED, one whose root 0xc, "
                   "7 or 8 does not verify or one refs.sys rejects, and when the "
                   "checkpoint copy in use cannot be verified or has a root 0xc, 7 or 8 that does not verify or cannot "
                   "be verified, when a checkpoint copy with a higher clock than the copy in use has no root list that "
                   "can be read or that refs.sys rejects (the view is then stale), when refs.sys rejects every "
                   "checkpoint copy, when a checkpoint copy cannot be read (its read fails, it lies past the end of "
                   "the image, or it carries no CHKP signature), or a checkpoint copy's +0x10 and +0x60 clocks "
                   "differ"),
          ("supb --verify", "consistency table + per-copy self-checksums"),
          ("supb -vv", "full forensic detail")]},
 "chkp": {"tag": "Checkpoint (CHKP) with container translation",
   "desc": ["Decode the checkpoint copy in use and the 13 global root tables, with VLCN→PLCN container",
            "translation. -v switches to the container-translation layout. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "container-translation layout / + GPT & full detail"),
            ("--verify", "checks: the copy's self-checksum and each other checkpoint copy's, allocator clock <= "
                         "virtual clock, roots 0xc, 7 and 8 against the digests the copy records, root count == 13, "
                         "root page signatures, the "
                         "Container Table, CPC against the VBR; exits 2 on any check that failed or could not be "
                         "made"),
            ("--raw", "hex dump of the first 1 KiB of the checkpoint record (one cluster)")],
   "ex": [("chkp", "decode the checkpoint copy in use + roots; exits 2 when it says a checkpoint copy FAILED its "
                   "self-checksum, when the checkpoint copy in use cannot be verified or has a root 0xc, 7 or 8 "
                   "that does not verify or cannot be verified, when a checkpoint copy with a higher clock than the "
                   "copy in use has no root list that can be read (the view is then stale), when refs.sys rejects "
                   "the newest checkpoint copy or every copy (its root count, offset table, root offsets or area), "
                   "when a checkpoint copy cannot be read (its read fails, it lies past the end of the image, or it "
                   "carries no CHKP signature), when a checkpoint copy's +0x10 and +0x60 clocks differ, and when the "
                   "superblock copy the volume is read from is a backup (the primary is not usable), a copy that "
                   "FAILED its self-checksum (no superblock copy verifies), or one whose checksum cannot be verified"),
          ("chkp --verify", "decode + consistency checks"),
          ("chkp -vv", "full forensic dump")]},
 "objects": {"tag": "Object ID table (OID → LCN mapping)",
   "desc": ["List every object (OID) with its friendly name and root LCN. -v adds physical LCNs and page",
            "signatures; -vv dumps the raw per-object entries. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "header + LCNs / full per-object raw dump"),
            ("--verify", "check every object's root page signature")],
   "ex": [("objects", "compact OID table"), ("objects -v", "+ physical LCNs & page sizes"),
          ("objects -vv --verify", "raw entries + verification")]},
 "schema": {"tag": "Schema table (table-type definitions)",
   "desc": ["List the table schemas: the system tables' and the object tables' (a file's, a directory's, a data",
            "stream's, by format era), with their key rules and value layouts. -vv prints the",
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
            "container table (ID, Phys LCN, Flags, Row, Type); the capacity is the total line above it."],
   "opts": [("-v", "full per-container table")],
   "ex": [("containers", "geometry + allocator summary; exits 2 when it says the checkpoint copy it reads (or the "
                         "newest copy) FAILED its self-checksum, when the checkpoint copy in use cannot be verified or "
                         "has a root 0xc, 7 or 8 that does not verify or cannot be verified, when a checkpoint copy "
                         "with a higher clock than the copy in use has no root list that can be read (the view is then "
                         "stale), when refs.sys rejects the newest checkpoint copy or every copy (its root count, offset "
                         "table, root offsets or area), when a checkpoint copy cannot be read (its read fails, it lies "
                         "past the end of the image, or it carries no CHKP signature), when a checkpoint copy's +0x10 "
                         "and +0x60 clocks differ, and when the superblock copy the volume is read from is a backup "
                         "(the primary is not usable), a copy that FAILED its self-checksum, or one whose checksum "
                         "cannot be verified"),
          ("containers -v", "+ per-container table")]},
 "allocators": {"tag": "Allocator tables — the volume's own free/used accounting",
   "desc": ["Decode the three allocator tiers (schema 0xe010) and report, per tier, what the ROWS say and",
            "what the volume's own PERSISTED SUMMARY says — then the volume capacity.",
            "",
            "Tiers: Medium (root 1, table 0x21, virtual LCNs — the whole mapped volume), Container (root 2,",
            "table 0x20, virtual — the container table's own pages) and Small (root 12, table 0x22, REAL",
            "physical LCNs — the bootstrap structures).",
            "",
            "Two numbers are printed for each tier because they can legitimately differ, and the difference",
            "is itself evidence:",
            "  • from rows    — recomputed here from every allocation bitmap (popcount), the slow, exact way.",
            "  • from summary — the 416-byte block ReFS maintains in the tier's own root page.",
            "On ReFS 3.4 the tiers are strictly separated, so the Medium rows span LESS than the summary while",
            "the free counts still match exactly. A difference in BOTH numbers instead points at a damaged",
            "volume (a truncated container table); compare with `containers`.",
            "",
            "Rows are accepted only from pages that claim this tier's own table id, and the summary only from",
            "a root page that does. A root INDEX is not a tier: on a damaged volume root 12 has been seen",
            "carrying the container table. Anything rejected is reported, never averaged into a total.",
            "",
            "Capacity covers the whole volume: the allocator's summary counts the volume's own length. What",
            "an image holds after the volume is the image's (summary's Image tail), not free space."],
   "opts": [("-v", "per-row detail (first 12 rows per tier)"), ("-vv", "every row"),
            ("--json", "machine-readable output")],
   "ex": [("allocators", "per-tier totals + volume capacity"),
          ("allocators -v", "+ the individual allocation ranges"),
          ("allocators --json", "machine-readable")]},
 "upcase": {"tag": "Unicode upcase table",
   "desc": ["Decode the Unicode upcase (case-folding) table. -v shows sample mappings; -vv dumps every",
            "non-identity mapping. " + _VERB_LADDER + "."],
   "opts": [("-v / -vv", "sample mappings / every non-identity mapping"),
            ("--verify", "six consistency checks"), ("-H", "header banner")],
   "ex": [("upcase", "table summary"), ("upcase -v", "+ sample case mappings"),
          ("upcase -vv", "dump all non-identity mappings")]},
  "oid30": {"tag": "OID 0x30, the heat engine table",
   "desc": ["Inspect the OID 0x30 object, the heat engine's table: per 10-minute generation in which the volume had I/O,",
            "two rows of the generation's totals and a row per tracked container and direction (v3.10+). -v dumps",
            "every row's u64 fields."],
   "opts": [("-v", "detailed per-row dump")],
   "ex": [("oid30", "the generations and their rows"), ("oid30 -v", "+ per-row u64 fields")]},
 "bootedit": {"tag": "[DANGEROUS] Boot sector editor & repair",
   "desc": ["Inspect or repair the ReFS VBR. ACTIONS: read (display), export -o FILE, repair, set --field F",
            "--value V, import -i FILE, sparse -o FILE (sparse image copy).",
            "repair checks every redundant copy of the bootstrap: the primary and backup boot sector copies,",
            "the three superblock copies (LCN 0x1e, N-2, N-3) and the two checkpoint copies. A boot sector or",
            "superblock copy that fails is restored from a copy that passes: a boot sector copy is one whole",
            "sector (its bytes per sector), from the copy the volume is read from, never from a backup that",
            "records another version than the primary; a superblock copy is rebuilt from the copy the volume",
            "is read from, with its own LCN and self-checksum. Checkpoint copies are reported, never restored",
            "(the two are two states of the volume, not copies of one). Nothing is written past the end of",
            "the image. Each restore is printed and logged in <output>.repair.log with its source, offset,",
            "length and SHA-256 before and after, then every copy is checked again. When no copy is",
            "restored, repair diagnoses refsutil fixboot damage in the PRIMARY boot sector.",
            "Writes go to a repaired SPARSE COPY unless --inplace is given (it asks for a typed YES); ALWAYS",
            "preview with --dry-run."],
   "opts": [("read | export | repair | set | import | sparse", "the action (positional)"),
            ("--field F / --value V", "set: which VBR field and its new value"),
            ("-i FILE / -o FILE", "import input / export-sparse-write output path"),
            ("--dry-run", "repair/set/import: preview byte changes, write nothing"),
            ("--inplace", "DANGEROUS: modify the original image instead of a copy")],
   "ex": [("bootedit read", "display & validate the VBR (read-only)"),
          ("bootedit repair --dry-run", "scan the VBR/SUPB/CHKP copies + preview any restore"),
          ("bootedit set --field checksum_algo --value 2 --dry-run", "preview a field change")]},
 "forefst": {"tag": "Run any forefst subcommand (passthrough to the forensic tool)",
   "desc": ["`refsanalysis <image> forefst <cmd> [options]` delegates to forefst — so every forefst",
            "subcommand is reachable without leaving refsanalysis (`... forefst --list` lists them all). Run",
            "`... forefst --help` for forefst's own help, or `... forefst <cmd> --help` for one command."],
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
    # N359 (1.14.0): every entry states its exit codes (forefst's contract, one text)
    print("\n  Exit codes:")
    for code, what in _forefst._EXIT_CODE_LINES:
        print(f"    {code}  {what}")

def main():
    utf8_console()                          # N489: text output in UTF-8 on every platform, as forefst's
    # Global `--partition-start N` works in ANY position: relocate it to the END of argv so a flag placed
    # BEFORE the subcommand (`IMG --partition-start 0 supb`) doesn't occupy the subcommand slot (argv[2]).
    # No-op when already last; only the first occurrence moves. (The `--partition-start`-only, no-subcommand
    # case stays handled by the default-`summary` branch below.)
    for _pi in range(2, len(sys.argv) - 1):
        if sys.argv[_pi] == "--partition-start":
            sys.argv = sys.argv[:_pi] + sys.argv[_pi + 2:] + [sys.argv[_pi], sys.argv[_pi + 1]]
            break
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
    validate_image(image, True if "--partition-start" in sys.argv[2:] else None)      # C2-5

    # ── forefst passthrough ──  refsanalysis <image> forefst <cmd> [opts]  →  forefst <image> <cmd> [opts]
    # Delegates to forefst's full dispatch, so every forefst subcommand (files/summary/search/details + the
    # 12 forensic commands) and its --help are reachable from refsanalysis without leaving the tool. forefst
    # is already imported at module load; no code is duplicated.
    if len(sys.argv) >= 3 and sys.argv[2] == "forefst":
        import forefst as _forefst
        sys.argv = [sys.argv[0], image] + sys.argv[3:]   # drop the 'forefst' token; keep image + the rest
        # N171: before this tool raises its own recursion limit (below), so forefst runs with the limit forefst.py
        # sets itself (max(current, 4000): a crafted tree deeper than that is a catchable RecursionError, not the
        # SIGSEGV a 40,000 limit can give on a small C stack); the closed-pipe handling is the __main__ block's
        return _forefst.main()

    # Full-depth default walks (cmd_files/cmd_attributes) can recurse as deep as a real directory tree; raise
    # the limit well above any plausible depth (the walks are cycle-guarded, so this only covers genuine depth).
    # N171: set after the forefst passthrough above, which keeps forefst.py's own limit.
    sys.setrecursionlimit(40000)

    if len(sys.argv) < 3:
        subcmd, remaining = "summary", []
    elif sys.argv[2].startswith("-") and sys.argv[2] not in ("-h", "--help", "--version"):
        # No subcommand given — argv[2] is a leading GLOBAL flag (e.g. --partition-start / --json) for the
        # default `summary` subcommand. Without this, `refsanalysis IMG --partition-start 0` mis-reads the flag
        # as the subcommand ("unknown subcommand: --partition-start"). -h/--help/--version stay handled below.
        subcmd, remaining = "summary", sys.argv[2:]
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
        sys.exit(rc_escalate(cmd_summary(image, remaining, partition_start, plus_mode=True)))

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

    # A11: every command's exit code passes through forefst's rc_escalate, as forefst's own commands do, so a
    # run that recorded unreadable metadata or a finding does not exit 0 here while exiting 2 there.
    sys.exit(rc_escalate(handler(image, remaining, partition_start)))


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
  refsanalysis.py disk.raw bootedit repair --dry-run  # check the bootstrap copies, preview restores + fixboot
  refsanalysis.py disk.raw all                        # run the main structure tools in sequence
  refsanalysis.py disk.raw forefst usn --stats        # run any forefst command via the passthrough

Note: the forensic commands (usn/mlog/timeline/timestomp/extract/security/reparse/deleted/
snapshots/integrity/export/dataruns, and forefst's others) are forefst's — run `forefst.py <image> <cmd>`, or reach them
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
                                "parentchild", "containers", "allocators", "upcase", "oid30"]),
        ("Boot sector repair", ["bootedit"]),
    ]
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
    _forefst._install_pipe_guards(sys.argv[1:])         # N538 / decision 56: forefst's guards
    # A11: main()'s return value (the `forefst` passthrough returns forefst's) and every SystemExit code go
    # through rc_escalate -- the exit rule forefst.py's own __main__ applies. A message (a str code) is left
    # alone: rc_escalate escalates only a success code.
    try:
        _main_rc = main()
        _exit_code = rc_escalate(0 if _main_rc is None else _main_rc)
    except SystemExit as _se:
        _exit_code = rc_escalate(0 if _se.code is None else _se.code)
    except BrokenPipeError:
        # N171: a closed pipe ends as forefst.py's does (forefst's handler): no traceback -- for this tool's own commands
        # and for the forefst passthrough, which died here with a BrokenPipeError traceback (exit 1); N538 / decision 56:
        # the exit code of what the run recorded before the close (2 for a finding or a skip, else 0)
        _forefst._quiet_closed_pipe()
        sys.exit(rc_escalate(0))
    except OSError as _oe:
        # final check F2 (review S5): a write failure (a file-size limit, a full disk, stdout on /dev/full) or a read
        # error ends as forefst.py's __main__ ends it (N194: the error line, exit 1), not with a traceback -- for this
        # tool's own commands and for the forefst passthrough, which runs forefst.main() under this block
        print(f"{PROG}: error: {_forefst._oserror_text(_oe, sys.argv[1] if len(sys.argv) > 1 else '')}", file=sys.stderr)
        _forefst._flush_stdout()    # the text already printed, or stdout pointed at devnull (no second failure at exit)
        sys.exit(1)
    except KeyboardInterrupt:
        # N171: as forefst.py: an interrupted run exits 130, not with a traceback
        sys.exit(130)
    _forefst._exit_flushed(_exit_code, PROG)     # final check F2: a buffered write failure is reported, not lost
