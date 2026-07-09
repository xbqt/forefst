#!/usr/bin/env python3
"""
verify_static.py — Static analysis verification of reference_table.csv entries

Searches decompiled refs.sys code, function catalog, and Ghidra exports to find
static evidence for the 106 SA=NOT_TESTED entries in reference_table.csv.

Produces a report with per-entry verdicts: CONFIRMED / PARTIAL / NOT_FOUND / SKIPPED.
Run from the repo root. Function catalog (not bundled): set REFS_FUNC_CATALOG.

No dependencies on forefst.py — uses rg and grep via subprocess.
"""
import subprocess
import csv
import os
import sys
import re
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ANALYSIS_ROOT = os.path.abspath(os.path.join(REPO_ROOT, "..", "analysis"))

DECOMP_WIN11 = os.path.join(ANALYSIS_ROOT, "static", "decompiled", "win11_4b0558f6", "refs_win11.decomp.c")
DECOMP_WIN10 = os.path.join(ANALYSIS_ROOT, "static", "decompiled", "win10_e38fe4ac", "refs_win10.decomp.c")
DECOMP_INSIDER = os.path.join(ANALYSIS_ROOT, "static", "decompiled", "insider_67a922ae", "winsider-refs.decomp.c")
INDEX_WIN11 = os.path.join(ANALYSIS_ROOT, "static", "decompiled", "win11_4b0558f6", "refs_win11.decomp.index.tsv")
INDEX_WIN10 = os.path.join(ANALYSIS_ROOT, "static", "decompiled", "win10_e38fe4ac", "refs_win10.decomp.index.tsv")
INDEX_INSIDER = os.path.join(ANALYSIS_ROOT, "static", "decompiled", "insider_67a922ae", "winsider-refs.decomp.index.tsv")
FUNC_CATALOG = os.environ.get("REFS_FUNC_CATALOG", os.path.join(REPO_ROOT, "analysis", "function_catalog.csv"))
GHIDRA_EXPORTS = os.path.join(ANALYSIS_ROOT, "static", "ghidra", "exports")
STRINGS_WIN11 = os.path.join(GHIDRA_EXPORTS, "refs_win11_strings.txt")
STRINGS_WIN10 = os.path.join(GHIDRA_EXPORTS, "refs_win10_strings.txt")
DECOMP_FUNCS = os.path.join(ANALYSIS_ROOT, "static", "decompiled_functions")
CSV_PATH = os.path.join(REPO_ROOT, "analysis", "reference_table.csv")

# ── Search helpers ──────────────────────────────────────────────────────────

def rg(pattern, filepath, context=3, max_count=20, case_insensitive=False):
    """Run ripgrep, return list of matching lines (with context)."""
    cmd = ["rg", "-n", f"-C{context}", f"-m{max_count}"]
    if case_insensitive:
        cmd.append("-i")
    cmd += [pattern, filepath]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip().split("\n") if r.stdout.strip() else []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

def rg_count(pattern, filepath, case_insensitive=False):
    """Count matches for a pattern."""
    cmd = ["rg", "-c"]
    if case_insensitive:
        cmd.append("-i")
    cmd += [pattern, filepath]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return int(r.stdout.strip()) if r.stdout.strip() else 0
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return 0

def grep_catalog(pattern, binary_filter=None):
    """Search function_catalog.csv for function names matching pattern."""
    cmd = ["grep", "-iE", pattern, FUNC_CATALOG]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        lines = r.stdout.strip().split("\n") if r.stdout.strip() else []
        if binary_filter:
            lines = [l for l in lines if binary_filter in l]
        return lines
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

def search_function_body(func_pattern, offset_pattern, decomp_file, index_file):
    """Find a function by name pattern in the index, then search its body for an offset."""
    try:
        with open(index_file, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)
            entries = []
            for row in reader:
                if len(row) >= 3 and re.search(func_pattern, row[0], re.IGNORECASE):
                    entries.append((row[0], int(row[2])))
    except (FileNotFoundError, StopIteration):
        return []

    hits = []
    for func_name, start_line in entries:
        cmd = ["sed", "-n", f"{start_line},{start_line+200}p", decomp_file]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            body = r.stdout
            for line_no, line in enumerate(body.split("\n"), start=start_line):
                if re.search(offset_pattern, line, re.IGNORECASE):
                    hits.append(f"  {func_name}:{line_no}: {line.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return hits[:10]

def search_strings(pattern, strings_file=None):
    """Search binary strings for a pattern."""
    f = strings_file or STRINGS_WIN11
    return rg(pattern, f, context=0, max_count=10, case_insensitive=True)

def check_decompiled_func_doc(doc_name, search_pattern):
    """Check an existing decompiled function analysis doc for a pattern."""
    path = os.path.join(DECOMP_FUNCS, doc_name)
    if not os.path.exists(path):
        return []
    return rg(search_pattern, path, context=1, max_count=5, case_insensitive=True)

# ── Claim definitions ──────────────────────────────────────────────────────
#
# Each claim: (ref_id, method, search_spec)
# method: "offset"   — search decompiled code for offset in function context
#         "constant" — search for hex constant broadly
#         "catalog"  — search function catalog
#         "crossref" — check existing decompiled function doc
#         "combined" — multiple searches, any hit counts
#         "skip"     — MLog-deferred or not testable

CLAIMS = []

# ── Group 1: B+-tree / page structure (General) ────────────────────────────

CLAIMS += [
    ("GN_PREF_003", "offset", {
        "desc": "0x24-0x26: checksum length in page reference",
        "func_pattern": r"PageReference|ValidatePage|ChecksumLength|VerifyChecksum",
        "offset_pattern": r"0x24|0x26|ChecksumLen",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("GN_IDXR_001", "offset", {
        "desc": "Root 0x00-0x04: size of index root",
        "func_pattern": r"InitializeRoot|OpenTable|RootPage|IndexRoot",
        "offset_pattern": r"IndexRoot|RootSize|root.*size",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("GN_IDXR_002", "offset", {
        "desc": "Root 0x0C-0x0E: schema of table",
        "func_pattern": r"InitializeRoot|OpenTable|Schema|GetSchema",
        "offset_pattern": r"0x0c|0x0e|[Ss]chema",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("GN_IDXR_003", "offset", {
        "desc": "Root 0x18-0x20: number of extents",
        "func_pattern": r"InitializeRoot|ExtentCount|NumExtent|RootPage",
        "offset_pattern": r"0x18|0x20|[Ee]xtent.*[Cc]ount|[Nn]um.*[Ee]xtent",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("GN_IDXR_004", "offset", {
        "desc": "Root 0x20-0x28: number of rows",
        "func_pattern": r"InitializeRoot|RowCount|NumRow|TotalRow",
        "offset_pattern": r"0x20|0x28|[Rr]ow.*[Cc]ount|[Nn]um.*[Rr]ow",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("GN_IDXH_002", "combined", {
        "desc": "0x0C: volume signature (corrected from 'height')",
        "searches": [
            ("offset", r"PageHeader|ValidatePage|MSB_PLUS", r"0x0c|0x0C|[Ss]ignature|[Vv]olume.*[Ss]ig"),
            ("crossref", "CmsVolumeCheckpoint.md", r"0x0[Cc]|signature"),
        ],
    }),
    ("GN_IDXH_003", "combined", {
        "desc": "0x0D-0x0E: flags (0x1 inner, 0x2 root, 0x4 stream)",
        "searches": [
            ("constant", r"0x100.*inner|inner.*0x100|IsInnerNode|tbl\[3\].*0x100"),
            ("offset", r"PageFlags|InnerNode|IsLeaf|IsRoot", r"0x0[dD]|flags|0x100"),
        ],
    }),
    ("GN_IENT_004", "combined", {
        "desc": "0x08-0x0A: entry flags (0x4 deleted)",
        "searches": [
            ("constant", r"Delet.*0x4|0x4.*[Dd]elet|ENTRY_FLAG.*DELETE|IsDeleted"),
            ("offset", r"EntryFlags|MarkDeleted|SetEntryFlag", r"0x08|0x0[aA]|flags.*0x4|0x4.*flag"),
        ],
    }),
]

# ── Group 2: Superblock / Checkpoint (File System) ────────────────────────

CLAIMS += [
    ("FS_SUPB_006", "combined", {
        "desc": "SUPB 0x78-0x7C: self-descriptor offset/length",
        "searches": [
            ("offset", r"SuperBlock|ParseSuperBlock|ReadSuperBlock|InitializeSuperBlock", r"0x78|0x7[cC]|[Dd]escriptor"),
            ("constant", r"SuperBlock.*0x78|0x78.*SuperBlock"),
        ],
    }),
    ("FS_SUPB_007", "combined", {
        "desc": "Two backup copies near end of partition",
        "searches": [
            ("catalog", r"BackupSuperBlock|SuperBlock.*Backup|ReadBackup"),
            ("offset", r"SuperBlock|ReadBootSector|FindSuperBlock", r"[Bb]ackup|[Cc]opy|[Mm]irror"),
        ],
    }),
    ("FS_CHKP_004", "combined", {
        "desc": "CHKP 0x58-0x5C: self-descriptor offset",
        "searches": [
            ("offset", r"Checkpoint|ParseCheckpoint|InitCheckpoint", r"0x58|0x5[cC]|[Dd]escriptor"),
            ("crossref", "CmsVolumeCheckpoint.md", r"0x58|descriptor"),
        ],
    }),
    ("FS_CHKP_019", "combined", {
        "desc": "Global table 0x0E: Container Index Table",
        "searches": [
            ("constant", r"0x0[eE].*Container.*Index|Container.*Index.*Table|CONTAINER_INDEX"),
            ("offset", r"Checkpoint|GlobalTable|SchemaTable", r"0x0[eE]|[Cc]ontainer.*[Ii]ndex"),
        ],
    }),
    ("FS_OTBL_002", "combined", {
        "desc": "Object Table value: page ref + durable LSN + variable buffer",
        "searches": [
            ("crossref", "CmsObjectTableGetRecord.md", r"[Pp]age.*[Rr]ef|LSN|[Gg]eneration|[Cc]lock"),
            ("offset", r"ObjectTable|GetObjectRecord|ObjectEntry", r"[Pp]age[Rr]ef|LSN|[Vv]irtual.*[Cc]lock"),
        ],
    }),
    ("FS_VINF_002", "combined", {
        "desc": "Volume info: creation/mount times, version",
        "searches": [
            ("offset", r"VolumeInformation|VolumeInfo|InitializeVcb", r"[Cc]reation|[Mm]ount|[Vv]ersion|[Tt]ime"),
            ("crossref", "InitializeVcbFromBootSector.md", r"creation|mount|version|VolumeInfo"),
        ],
    }),
    ("FS_VINF_003", "combined", {
        "desc": "Volume info backup block row (key 0x540)",
        "searches": [
            ("constant", r"0x540|BackupBlock|KEY_BACKUP"),
            ("offset", r"VolumeInformation|BackupBlock|VolumeKey", r"0x540|[Bb]ackup"),
        ],
    }),
]

# ── Group 3: Container Table (Content) ────────────────────────────────────

CLAIMS += [
    ("CT_CTBL_009", "combined", {
        "desc": "Container row 0x10-0x17: Container ID",
        "searches": [
            ("offset", r"ContainerEntry|ContainerRow|GetContainer", r"0x10|[Cc]ontainer.*[Ii][Dd]|[Cc]ontainer.*[Ii]dentif"),
            ("constant", r"ContainerId.*0x10|0x10.*ContainerId"),
        ],
    }),
    ("CT_CTBL_010", "combined", {
        "desc": "Container row 0xA0-0xA7: CSC starting position",
        "searches": [
            ("offset", r"ContainerEntry|ContainerRow|CompactionState|CSC", r"0x[aA]0|CSC|[Cc]ompaction.*[Ss]tart"),
            ("constant", r"0xa0.*[Cc]ontainer|[Cc]ontainer.*0xa0"),
        ],
    }),
    ("CT_DRNT_002", "combined", {
        "desc": "Data run flags: 0x0010=data, 0x0080=CRC32, 0x0100=CRC64",
        "searches": [
            ("constant", r"0x0010|0x0080|0x0100"),
            ("offset", r"DataRun|ExtentFlag|ClusterFlag|StreamExtent", r"0x0010|0x0080|0x0100|CRC32|CRC64"),
        ],
    }),
    ("CT_DRNT_003", "combined", {
        "desc": "Total length of data run",
        "searches": [
            ("offset", r"DataRun|ExtentLength|RunLength|TotalLength", r"[Tt]otal.*[Ll]ength|[Rr]un.*[Ll]ength|[Ll]ength.*[Rr]un"),
            ("catalog", r"DataRun|RunLength"),
        ],
    }),
    ("CT_CNTX_001", "catalog", {
        "desc": "Container context: named but no field layout",
        "pattern": r"ContainerContext|CmsContainerContext",
    }),
]

# ── Group 4: Directory / File Name ────────────────────────────────────────

CLAIMS += [
    ("FN_DTBL_001", "combined", {
        "desc": "Directory descriptor row: type 0x10",
        "searches": [
            ("constant", r"0x10.*[Dd]irectory.*[Dd]escriptor|DIRECTORY_DESCRIPTOR|attr_type.*0x10"),
            ("offset", r"DirectoryDescriptor|InsertDescriptor|DirRow", r"0x10|[Dd]escriptor"),
        ],
    }),
    ("FN_DTBL_002", "combined", {
        "desc": "File row: type 0x00020030 (corrected from 0x00010030)",
        "searches": [
            ("constant", r"0x00020030|0x20030|0x10030|0x30.*file"),
            ("offset", r"InsertRow|FileRow|DirectoryEntry|FileName.*Entry", r"0x30|0x0002|[Ff]ile.*[Rr]ow"),
        ],
    }),
    ("FN_DTBL_003", "combined", {
        "desc": "ID2 entry: type 0x80000020 (reverse lookup)",
        "searches": [
            ("constant", r"0x80000020"),
            ("offset", r"ReverseIndex|ReverseLookup|ID2|StreamIndex", r"0x80000020|0x20.*reverse|reverse.*0x20"),
        ],
    }),
    ("FN_ADDR_001", "combined", {
        "desc": "128-bit key: directory_id | file_id; root=0x600",
        "searches": [
            ("constant", r"0x600.*root|ROOT_DIRECTORY.*0x600|root.*0x600"),
            ("offset", r"DirectoryId|ParentId|FileKey|RootDir", r"0x600|128.*bit|[Dd]irectory.*[Ii][Dd]"),
        ],
    }),
]

# ── Group 5: Log Table (Application) ─────────────────────────────────────

CLAIMS += [
    ("AP_LGTB_001", "offset", {
        "desc": "Log table 0x10/0x8: start offset of data area",
        "func_pattern": r"LogArea|TxLog|LogTable|InitializeLog",
        "offset_pattern": r"0x10.*[Ss]tart|[Ss]tart.*0x10|[Dd]ata.*[Aa]rea.*0x10",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("AP_LGTB_002", "offset", {
        "desc": "Log table 0x18/0x8: end offset of data area",
        "func_pattern": r"LogArea|TxLog|LogTable|InitializeLog",
        "offset_pattern": r"0x18.*[Ee]nd|[Ee]nd.*0x18|[Dd]ata.*[Aa]rea.*0x18",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("AP_LGTB_003", "offset", {
        "desc": "Log table 0x20/0x8: size of data area",
        "func_pattern": r"LogArea|TxLog|LogTable|InitializeLog",
        "offset_pattern": r"0x20.*[Ss]ize|[Ss]ize.*0x20|[Dd]ata.*[Ss]ize",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("AP_LGTB_004", "offset", {
        "desc": "Log table 0x28/0x8: LCN of first control entry",
        "func_pattern": r"LogArea|TxLog|LogTable|LogControl|InitializeLog",
        "offset_pattern": r"0x28|[Cc]ontrol.*[Ee]ntry|LCN.*[Cc]ontrol",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("AP_LGTB_005", "offset", {
        "desc": "Log table 0x30/0x8: LCN of second control entry",
        "func_pattern": r"LogArea|TxLog|LogTable|LogControl|InitializeLog",
        "offset_pattern": r"0x30|[Ss]econd.*[Cc]ontrol",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("AP_LGFL_004", "combined", {
        "desc": "Control data: sequence number, start/end, next LSN, UUID",
        "searches": [
            ("offset", r"LogControl|LogHeader|CmsRestarter|RecoveryArea", r"[Ss]equence|LSN|UUID|[Cc]ontrol.*[Dd]ata"),
            ("crossref", "CmsRestarter.md", r"sequence|LSN|control"),
        ],
    }),
]

# ── Group 6: MLog-deferred (SKIP) ────────────────────────────────────────

for ref_id in ["AP_LGFL_002", "AP_EVNT_001", "AP_EVNT_002", "AP_EVNT_003",
               "AP_EVNT_004", "AP_EVNT_005", "AP_EVNT_006", "AP_EVNT_007",
               "AP_WIPE_001"]:
    CLAIMS.append((ref_id, "skip", {"reason": "DEFERRED_MLOG"}))

# ── Group 7: Change Journal ───────────────────────────────────────────────

CLAIMS += [
    ("MD_ATTR_009", "catalog", {
        "desc": "$USN_INFO: Change Journal org metadata",
        "pattern": r"UsnInfo|USN_INFO|UsnJournal.*Info|ChangeJournal.*Info",
    }),
    ("AP_CHJN_001", "catalog", {
        "desc": "Change Journal deactivated by default",
        "pattern": r"DeactivateUsn|DeactivateJournal|DisableUsn",
    }),
    ("AP_CHJN_003", "skip", {
        "reason": "Behavioral observation (circular buffer); no direct code manifestation",
    }),
    ("AP_CHJN_004", "combined", {
        "desc": "Change Journal located in FS Metadata path",
        "searches": [
            ("catalog", r"UsnJournal|ChangeJournal"),
            ("offset", r"UsnJournal|CreateUsn|InitializeUsn", r"[Mm]etadata|[Pp]ath|[Ll]ocation"),
        ],
    }),
]

# ── Group 8: VBR / Boot / Upgrade (File System RA) ───────────────────────

CLAIMS += [
    ("FS_CHKP_RA_003", "combined", {
        "desc": "3.4→3.14 upgrade: CHKP flags 0x002→0x602, ref_size changes",
        "searches": [
            ("constant", r"0x602|0x002|0x200|0x400"),
            ("offset", r"UpgradeVolume|MigrateVersion|VersionUpgrade|CheckpointFlag", r"0x602|0x002|0x200|0x400|[Uu]pgrade"),
            ("catalog", r"Upgrade|MigrateVersion|VersionTransition"),
        ],
    }),
    ("FS_VBR_RA_005", "offset", {
        "desc": "refsutil fixboot zeroes VBR fields 0x2A-0x57",
        "func_pattern": r"FixBoot|RepairBoot|FixVolume|RefsUtilFix",
        "offset_pattern": r"0x2[aA]|0x57|[Zz]ero|[Cc]lear.*VBR",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("FS_VBR_RA_006", "offset", {
        "desc": "refsutil fixboot sets container_size=0 at 0x40",
        "func_pattern": r"FixBoot|RepairBoot|FixVolume",
        "offset_pattern": r"0x40|[Cc]ontainer.*[Ss]ize",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("FS_VBR_RA_007", "offset", {
        "desc": "refsutil fixboot changes checksum selector at 0x2A",
        "func_pattern": r"FixBoot|RepairBoot|FixVolume",
        "offset_pattern": r"0x2[aA]|[Cc]hecksum.*[Ss]elector",
        "decomp": DECOMP_WIN11, "index": INDEX_WIN11,
    }),
    ("GN_ARCH_RA_002", "combined", {
        "desc": "NTFS and ReFS both reject ADS on symlink targets",
        "searches": [
            ("offset", r"AlternateData|ADS|NamedStream|ReparsePoint", r"[Rr]eparse|[Ss]ymlink|ADS|[Rr]eject|STATUS_"),
            ("catalog", r"AlternateData|AdsOnReparse|NamedStream"),
        ],
    }),
]

# ── Group 9: Metadata data run format (MD_DATA_RA) ───────────────────────

CLAIMS += [
    ("MD_DATA_RA_001", "combined", {
        "desc": "Non-resident extent entry: 24 bytes (VLCN+flags+VCN+pad+length)",
        "searches": [
            ("constant", r"0x18.*extent|extent.*24|EXTENT_ENTRY_SIZE"),
            ("offset", r"ParseExtent|ReadExtent|ExtentEntry|DataRun", r"0x18|24.*byte|VLCN|VCN|[Rr]un.*[Ll]ength"),
        ],
    }),
    ("MD_DATA_RA_002", "combined", {
        "desc": "RETRACTED 2026-06-18: the '16-byte single-extent shortcut' is NOT real — it was a misread of the $DATA sub-record header (marker 0x80000002 + descriptor 0x000E0080). Single-extent files use the standard 24-byte extent entry. All-image: 31,523 via 24-byte / 0 via any 16-byte form / 400-400 content matches. See structure_reference §C.4.",
        "searches": [
            ("constant", r"0x80000002"),
            ("offset", r"0x000E0080|0xe0080|24-byte|RETRACTED|phantom", r"0x80000002|descriptor|24-byte|RETRACTED"),
        ],
    }),
    ("MD_DATA_RA_003", "combined", {
        "desc": "Hardlinked files share type 0x40 entry via stream_index",
        "searches": [
            ("constant", r"0x40.*[Hh]ardlink|[Hh]ardlink.*0x40|0x0040.*stream"),
            ("offset", r"HardLink|StreamIndex|SharedExtent", r"0x40|0x0040|[Ss]tream.*[Ii]ndex"),
            ("catalog", r"HardLink|CreateLink"),
        ],
    }),
    ("MD_DATA_RA_004", "combined", {
        "desc": "Type 0x40 key: 24 bytes (attr_type+flags+reserved+stream_index+parent_oid)",
        "searches": [
            ("constant", r"0x0040|attr_type.*0x40|0x40.*attr"),
            ("offset", r"ExtentKey|DataRunKey|StreamKey", r"0x0040|[Ss]tream.*[Ii]ndex|[Pp]arent.*[Oo][Ii][Dd]"),
        ],
    }),
    ("MD_DATA_RA_005", "combined", {
        "desc": "Type 0x40 value: file_size at +0x58, alloc_size at +0x60, timestamps at +0x28",
        "searches": [
            ("offset", r"FileSize|AllocSize|ExtentValue|DataRunValue|StreamValue", r"0x58|0x60|0x28|[Ff]ile.*[Ss]ize|[Aa]lloc.*[Ss]ize"),
            ("crossref", "RefsComputeStandardInformationFromFcb.md", r"0x58|0x60|file_size|alloc_size"),
        ],
    }),
    ("MD_DATA_RA_006", "combined", {
        "desc": "Hardlink stub with alloc_size=0 and file_size=0",
        "searches": [
            ("offset", r"HardLink|LinkStub|CreateLink|SharedStream", r"[Aa]lloc.*0|[Ff]ile.*[Ss]ize.*0|[Ss]tub"),
            ("catalog", r"HardLink|CreateHardLink"),
        ],
    }),
    ("MD_DATA_RA_007", "combined", {
        "desc": "Integrity stream: variable-stride entries, checksum + data pages",
        "searches": [
            ("constant", r"0x1c00d0|0x180040|[Ii]ntegrity.*[Ss]tream"),
            ("offset", r"IntegrityStream|ChecksumPage|IntegrityExtent", r"0x1c00d0|0x180040|[Cc]hecksum.*[Pp]age|[Ss]tride"),
            ("catalog", r"IntegrityStream|IntegrityCheck"),
        ],
    }),
]

# ── Group 10: USN Journal (MD_USN_RA) ────────────────────────────────────

CLAIMS += [
    ("MD_USN_RA_001", "combined", {
        "desc": "USN Journal v3 record format with 128-bit File IDs",
        "searches": [
            ("constant", r"USN_RECORD_V3|USN.*[Vv]ersion.*3|[Vv]3.*USN"),
            ("offset", r"UsnRecord|UsnJournal|WriteUsn|PostUsn", r"128.*bit|[Ff]ile.*[Ii][Dd]|FILE_ID_128"),
            ("catalog", r"UsnRecord|WriteUsn|PostUsn"),
        ],
    }),
    ("MD_USN_RA_002", "combined", {
        "desc": "128-bit File ID: upper=table OID, lower=entry index",
        "searches": [
            ("offset", r"FileId|FileReference|ObjectId.*Entry", r"[Tt]able.*OID|[Ee]ntry.*[Ii]ndex|128.*[Ff]ile"),
            ("crossref", "RefsOpenFcbById.md", r"FileId|128|OID|entry.*index"),
        ],
    }),
    ("MD_USN_RA_003", "combined", {
        "desc": "USN reason code catalog for ReFS operations",
        "searches": [
            ("constant", r"0x100000|USN_REASON|FILE_CREATE.*0x100|RENAME_.*NEW"),
            ("offset", r"UsnReason|PostUsn|WriteUsn|UsnChange", r"[Rr]eason|0x100000|[Rr]eparse.*[Cc]hange"),
        ],
    }),
]

# ── Group 11: Sparse files (MD_SF_RA) ────────────────────────────────────

CLAIMS += [
    ("MD_SF_RA_001", "catalog", {
        "desc": "Sparse file 3-step process on ReFS",
        "pattern": r"Sparse|SetSparse|SparseFile",
    }),
    ("MD_SF_RA_002", "combined", {
        "desc": "Sparse flag: attribute 0x20→0x220 (adds 0x200)",
        "searches": [
            ("constant", r"0x200.*SPARSE|SPARSE.*0x200|FILE_ATTRIBUTE_SPARSE"),
            ("offset", r"SetSparse|SparseFlag|BasicInfo", r"0x200|0x220|SPARSE"),
        ],
    }),
    ("MD_SF_RA_004", "combined", {
        "desc": "Fully sparse files: alloc_size=0, no clusters",
        "searches": [
            ("offset", r"Sparse|ZeroData|SetSparse|AllocSize", r"[Aa]lloc.*0|[Nn]o.*[Cc]luster|[Zz]ero.*[Aa]lloc"),
            ("catalog", r"SparseFile|ZeroData|SetZero"),
        ],
    }),
]

# ── Group 12: Deletion / Recycle Bin (MD_DEL_RA) ─────────────────────────

CLAIMS += [
    ("MD_DEL_RA_001", "skip", {
        "reason": "OS-level behavior ($RECYCLE.BIN creation); no driver code manifestation",
    }),
    ("MD_DEL_RA_002", "combined", {
        "desc": "Explorer deletion: $R/$I entry structure",
        "searches": [
            ("catalog", r"Recycle|RecycleBin|DeleteFile"),
            ("offset", r"DeleteFile|Recycle|Unlink|RemoveEntry", r"\\$R|\\$I|[Tt]arget.*[Oo][Ii][Dd]|[Rr]ecycle"),
        ],
    }),
    ("MD_DEL_RA_003", "combined", {
        "desc": "PowerShell Remove-Item permanently deletes (USN 0x80000200)",
        "searches": [
            ("constant", r"0x80000200|FILE_DELETE|USN.*DELETE"),
            ("offset", r"DeleteFile|UnlinkFile|RemoveFile|Cleanup", r"0x80000200|[Pp]ermanent|[Dd]elete"),
        ],
    }),
]

# ── Group 13: EFS Encryption (MD_EFS_RA) ─────────────────────────────────

CLAIMS += [
    ("MD_EFS_RA_001", "combined", {
        "desc": "EFS encryption lifecycle: EFS0.LOG, reason code 0x00040000",
        "searches": [
            ("constant", r"0x00040000|0x40000.*[Ee]ncrypt|[Ee]ncrypt.*0x40000"),
            ("catalog", r"Encrypt|Efs|EncryptFile"),
        ],
    }),
    ("MD_EFS_RA_002", "combined", {
        "desc": "Encrypt-decrypt-encrypt tracked via USN",
        "searches": [
            ("catalog", r"Encrypt|Decrypt|Efs"),
            ("offset", r"Encrypt|Decrypt|EfsStream", r"USN|[Rr]eason|[Tt]rack"),
        ],
    }),
    ("MD_EFS_RA_003", "combined", {
        "desc": "Encrypted files: stream_count=3, $EFS named stream, attr 0x4020",
        "searches": [
            ("constant", r"0x4020|\\$EFS|EFS.*[Ss]tream"),
            ("offset", r"Encrypt|EfsStream|NamedStream|StreamCount", r"0x4020|\\$EFS|[Ss]tream.*[Cc]ount.*3"),
            ("catalog", r"EfsStream|EncryptedStream"),
        ],
    }),
]

# ── Group 14: Case Sensitivity (MD_CS_RA) ────────────────────────────────

CLAIMS += [
    ("MD_CS_RA_001", "combined", {
        "desc": "Per-directory case sensitivity changes B+-tree comparison",
        "searches": [
            ("catalog", r"CaseSensitive|CaseFlag|SetCaseSensitive"),
            ("offset", r"CaseSensitive|CompareKey|KeyCompare", r"[Cc]ase|CASE_SENSITIVE"),
        ],
    }),
    ("MD_CS_RA_002", "combined", {
        "desc": "Case-sensitive files: distinct OIDs and stream indices",
        "searches": [
            ("offset", r"CaseSensitive|InsertRow|CompareKey", r"OID|[Ss]tream.*[Ii]ndex|[Dd]istinct"),
            ("catalog", r"CaseSensitive"),
        ],
    }),
]

# ── Group 15: Links / Symlinks (MD_LK_RA) ────────────────────────────────

CLAIMS += [
    ("MD_LK_RA_001", "catalog", {
        "desc": "Junctions, directory symlinks, file symlinks all supported",
        "pattern": r"Symlink|Junction|ReparsePoint|MountPoint|CreateSymbolicLink",
    }),
    ("MD_LK_RA_002", "combined", {
        "desc": "Symlinks as resident entries with 0x420/0x10000400 attrs",
        "searches": [
            ("constant", r"0x420|0x10000400|REPARSE_POINT"),
            ("offset", r"ReparsePoint|Symlink|SetReparse|CreateReparse", r"0x420|0x10000400|[Rr]esident|[Rr]eparse"),
        ],
    }),
    ("MD_LK_RA_003", "combined", {
        "desc": "ADS cannot be set on symlink/reparse files",
        "searches": [
            ("offset", r"AlternateStream|NamedStream|Reparse|Symlink", r"STATUS_|[Rr]eject|[Ff]ail|[Dd]eny|[Rr]eparse"),
            ("constant", r"STATUS_REPARSE_ATTRIBUTE|ADS.*[Rr]eparse|[Rr]eparse.*ADS"),
        ],
    }),
    ("MD_LK_RA_004", "combined", {
        "desc": "USN 0x100000 for reparse point change / link creation",
        "searches": [
            ("constant", r"0x100000.*[Rr]eparse|[Rr]eparse.*0x100000"),
            ("offset", r"PostUsn|WriteUsn|UsnReason|ReparsePoint", r"0x100000|REPARSE_POINT_CHANGE"),
        ],
    }),
]

# ── Group 16: Stream Snapshots (MD_SNAP_RA) ──────────────────────────────

CLAIMS += [
    ("MD_SNAP_RA_001", "combined", {
        "desc": "Snapshot name stored inline as UTF-16LE",
        "searches": [
            ("offset", r"Snapshot|StreamSnapshot|SnapshotName", r"UTF.*16|[Uu]nicode|[Nn]ame|[Ii]nline"),
            ("catalog", r"StreamSnapshot|SnapshotStream|SnapshotName"),
        ],
    }),
    ("MD_SNAP_RA_002", "combined", {
        "desc": "Snapshots preserve complete extent descriptors",
        "searches": [
            ("offset", r"Snapshot|SnapshotDelta|PreserveExtent", r"[Ee]xtent|[Dd]elta|[Pp]reserve|[Rr]ecover"),
            ("catalog", r"SnapshotDelta|LookupSnapshotDelta"),
        ],
    }),
    ("MD_SNAP_RA_003", "combined", {
        "desc": "Snapshot extents use same VLCN format as type 0x40 data runs",
        "searches": [
            ("offset", r"Snapshot|SnapshotExtent|SnapshotDelta", r"VLCN|0x40|[Ee]xtent|[Dd]ata.*[Rr]un"),
            ("catalog", r"SnapshotExtent|SnapshotData"),
        ],
    }),
    ("MD_SNAP_RA_004", "combined", {
        "desc": "Snapshot sub-record format: size + header + UTF-16 name + metadata + extents",
        "searches": [
            ("offset", r"Snapshot|SnapshotRecord|StreamSnapshot", r"[Ss]ize|[Hh]eader|[Nn]ame|[Mm]etadata|[Ee]xtent"),
            ("catalog", r"StreamSnapshot|SnapshotStream"),
        ],
    }),
]

# ── Group 17: Attribute catalog / bit map (MD_ATTR_RA) ───────────────────

CLAIMS += [
    ("MD_ATTR_RA_001", "combined", {
        "desc": "Complete attribute values catalog (0x10, 0x16, 0x20, etc.)",
        "searches": [
            ("constant", r"FILE_ATTRIBUTE_DIRECTORY|0x10000000|FILE_ATTRIBUTE_ARCHIVE|0x20"),
            ("offset", r"FileAttributes|SetAttributes|BasicInfo|StandardInfo", r"0x10|0x16|0x20|0x220|0x420|0x4020"),
        ],
    }),
    ("MD_ATTR_RA_002", "combined", {
        "desc": "File attribute bit map (bit 10=REPARSE, bit 9=SPARSE)",
        "searches": [
            ("constant", r"0x400.*REPARSE|REPARSE_POINT.*0x400|0x200.*SPARSE|SPARSE.*0x200"),
            ("offset", r"FileAttributes|AttributeFlag|SetAttribute", r"0x400|0x200|REPARSE|SPARSE"),
        ],
    }),
    ("MD_ATTR_RA_003", "combined", {
        "desc": "FileAttributes flag 0x40000 = Extended Attributes present",
        "searches": [
            ("constant", r"0x40000.*EA|EA.*0x40000|EXTENDED_ATTRIBUTES|FILE_EA"),
            ("offset", r"ExtendedAttributes|SetEA|QueryEA|FileAttributes", r"0x40000|EA|[Ee]xtended.*[Aa]ttribut"),
        ],
    }),
    ("MD_ATTR_RA_004", "combined", {
        "desc": "WSL FIFOs: REPARSE_POINT with $LXMOD, FIFO = S_IFIFO 0o010000",
        "searches": [
            ("constant", r"LXMOD|LX_MOD|010000|WSL|LxFs|LxFifo"),
            ("catalog", r"Lx|WSL|Linux"),
            ("offset", r"ReparsePoint|Lx|WSL", r"LXMOD|FIFO|010000"),
        ],
    }),
]

# ── Group 18: Unsupported features ───────────────────────────────────────

CLAIMS += [
    ("MD_UNSUP_RA_001", "combined", {
        "desc": "Object IDs, short names, DAX not supported; hard-link enumeration not supported on v3.4 (IS supported on native v3.14 — fsutil hardlink list works, #340)",
        "searches": [
            ("constant", r"STATUS_NOT_SUPPORTED|STATUS_INVALID_DEVICE_REQUEST"),
            ("catalog", r"ObjectId|ShortName|DaxVolume|8dot3"),
            ("offset", r"ObjectId|ShortName|Dax|8dot3", r"STATUS_NOT_SUPPORTED|STATUS_INVALID|[Nn]ot.*[Ss]upport"),
        ],
    }),
]

# ── Group 19: Disk structure observations (MD_DISK_RA) ───────────────────

CLAIMS += [
    ("MD_DISK_RA_003", "combined", {
        "desc": "Resident type 0x30: stream_count at +0x20, file_attrs at +0x48, file_size at +0x58",
        "searches": [
            ("offset", r"InsertRow|FileRow|RowValue|StreamAttribute|RefsCompute", r"0x20|0x48|0x58|[Ss]tream.*[Cc]ount|[Ff]ile.*[Aa]ttr|[Ff]ile.*[Ss]ize"),
            ("crossref", "RefsComputeStandardInformationFromFcb.md", r"0x20|0x48|0x58|stream_count|file_attr|file_size"),
        ],
    }),
    ("MD_DISK_RA_004", "combined", {
        "desc": "Stream count semantics: 1=normal, 2=sparse/link, 3=EFS, 4-6=snapshots",
        "searches": [
            ("offset", r"StreamCount|NumberOfStreams|ScbCount", r"[Ss]tream.*[Cc]ount|[Nn]umber.*[Ss]tream"),
            ("catalog", r"StreamCount|NumberOfStreams"),
        ],
    }),
    ("MD_DISK_RA_006", "combined", {
        "desc": "EFS files: stream_count=3, sub-record #4 = $EFS named stream",
        "searches": [
            ("constant", r"\\$EFS|EFS.*[Ss]tream|EfsStream"),
            ("offset", r"EfsStream|EncryptedStream|NamedStream", r"\\$EFS|[Ss]tream.*[Cc]ount|[Ss]ub.*[Rr]ecord"),
        ],
    }),
    ("MD_DISK_RA_008", "combined", {
        "desc": "$RECYCLE.BIN: $R/$I entry structure on disk",
        "searches": [
            ("catalog", r"Recycle|RecycleBin"),
            ("constant", r"\\$RECYCLE|RECYCLE.*BIN"),
        ],
    }),
    ("MD_DISK_RA_009", "combined", {
        "desc": "Case-sensitive directory: both case variants coexist as separate keys",
        "searches": [
            ("offset", r"CaseSensitive|CompareKey|InsertRow", r"[Cc]ase|CASE_SENSITIVE|[Dd]istinct"),
            ("catalog", r"CaseSensitive"),
        ],
    }),
    ("MD_DISK_RA_010", "combined", {
        "desc": "Type 0x20 entries (kf=0x8000): reverse lookup stream_index→filename",
        "searches": [
            ("constant", r"0x8000.*0x20|0x0020.*0x8000|0x80000020"),
            ("offset", r"ReverseIndex|StreamIndex|ReverseLookup|ID2Entry", r"0x8000|0x0020|[Rr]everse|[Ss]tream.*[Ii]ndex"),
        ],
    }),
]

# ── Group 20: Timestamp behavior (MD_TS_RA) ──────────────────────────────

CLAIMS += [
    ("MD_TS_RA_001", "combined", {
        "desc": "Last access time at 0x40 updated on read when policy allows",
        "searches": [
            ("crossref", "RefsComputeStandardInformationFromFcb.md", r"0x40|LastAccess|AccessTime"),
            ("offset", r"LastAccessUpdate|DisableLastAccess|UpdateAccess|StandardInformation", r"0x40|[Ll]ast.*[Aa]ccess|[Aa]ccess.*[Tt]ime"),
            ("constant", r"DisableLastAccessUpdate|RefsDisableLastAccess"),
        ],
    }),
    ("MD_TS_RA_002", "combined", {
        "desc": "Write updates both LastWrite (0x30) and LastAccess (0x40)",
        "searches": [
            ("crossref", "RefsComputeStandardInformationFromFcb.md", r"0x30|0x40|LastWrite|LastAccess"),
            ("offset", r"UpdateStandardInformation|WriteTime|ModifyTime", r"0x30|0x40|[Ww]rite.*[Tt]ime|[Aa]ccess.*[Tt]ime"),
        ],
    }),
    ("MD_TS_RA_003", "combined", {
        "desc": "ADS writes update parent file timestamps",
        "searches": [
            ("offset", r"AlternateData|NamedStream|ADS|WriteStream", r"[Tt]imestamp|[Pp]arent|[Uu]pdate.*[Tt]ime"),
            ("catalog", r"AlternateData|NamedStream|UpdateTimestamp"),
        ],
    }),
    ("MD_TS_RA_004", "combined", {
        "desc": "Attribute change updates only metadata change time at 0x38",
        "searches": [
            ("crossref", "RefsComputeStandardInformationFromFcb.md", r"0x38|[Cc]hange.*[Tt]ime|[Mm]etadata.*[Cc]hange"),
            ("offset", r"ChangeTime|MetadataChange|AttributeChange|StandardInformation", r"0x38|[Cc]hange.*[Tt]ime"),
        ],
    }),
    ("MD_TS_RA_006", "skip", {
        "reason": "Per-image OID range statistics; observation, not structural claim",
    }),
]

# ── Group 21: SUPB behavior (MD_SUPB_RA) ─────────────────────────────────

CLAIMS += [
    ("MD_SUPB_RA_001", "combined", {
        "desc": "SUPB HAS a cluster-size-dependent self-checksum (LcnWithChecksum @SUPB+0xD0): CRC32-C/4B (4K) | CRC64/8B (64K) | SHA-256/32B (SHA vol); verified at mount (ValidateSuperBlock). Offset 0x08 is the version field, not the checksum. PROVEN by recomputation 2026-06-18 (#332).",
        "searches": [
            ("offset", r"SuperBlock|ValidateSuperBlock|ChecksumSuperBlock", r"0x08|[Cc]hecksum|self-check"),
            ("crossref", "CmsVolumeCheckpoint.md", r"SuperBlock|SUPB|checksum"),
        ],
    }),
    ("MD_SUPB_RA_002", "combined", {
        "desc": "SUPB corruption repaired during mount (CoW write)",
        "searches": [
            ("offset", r"RepairSuperBlock|FixSuperBlock|WriteSuperBlock|RefreshSuperBlock", r"[Rr]epair|[Rr]efresh|CoW|[Mm]ount"),
            ("catalog", r"RepairSuperBlock|RefreshSuperBlock|WriteSuperBlock"),
        ],
    }),
    ("MD_SUPB_RA_003", "combined", {
        "desc": "SUPB Volume GUID at 0x50 non-critical for bootstrap",
        "searches": [
            ("offset", r"SuperBlock|ParseSuperBlock|ReadSuperBlock|VolumeGuid", r"0x50|GUID|[Nn]on.*[Cc]ritical"),
            ("crossref", "ReadBootSectorForMount.md", r"GUID|0x50|SuperBlock"),
        ],
    }),
    ("MD_SUPB_RA_004", "combined", {
        "desc": "CHKP LCN pointers at SUPB 0xC0/0xC8 are bootstrap-critical",
        "searches": [
            ("offset", r"SuperBlock|ParseSuperBlock|ReadSuperBlock|CheckpointLcn", r"0x[Cc]0|0x[Cc]8|CHKP|[Cc]heckpoint.*LCN"),
            ("constant", r"0xC0.*[Cc]heckpoint|[Cc]heckpoint.*0xC0|0xC8.*[Cc]heckpoint"),
        ],
    }),
    ("MD_SUPB_RA_005", "skip", {
        "reason": "Mount checkpoint count observation; behavioral, not structural",
    }),
]

# ── Group 22: Upgrade / Post-Thesis ──────────────────────────────────────

CLAIMS += [
    ("FS_UPGD_RA_001", "combined", {
        "desc": "SUPB NOT modified during version upgrade; only VBR and CHKP modified",
        "searches": [
            ("offset", r"UpgradeVolume|MigrateVersion|VersionTransition", r"SuperBlock|SUPB|[Nn]ot.*[Mm]odif|VBR|CHKP"),
            ("catalog", r"UpgradeVolume|MigrateVersion|VersionUpgrade"),
        ],
    }),
    ("FS_VINF_RA_001", "combined", {
        "desc": "Volume label (key 0x510): raw UTF-16LE, null-terminated",
        "searches": [
            ("constant", r"0x510|VOLUME_LABEL|VolumeLabel"),
            ("offset", r"VolumeLabel|VolumeName|SetLabel|QueryLabel", r"0x510|UTF.*16|[Uu]nicode|[Ll]abel"),
        ],
    }),
    ("MD_ATTR_RA_003_bis", "skip", {"reason": "Already handled as MD_ATTR_RA_003"}),
    ("FS_REPS_RA_001", "combined", {
        "desc": "Reparse Index (OID 0x540/0x541 schema 0x160) key structure",
        "searches": [
            ("constant", r"0x540|0x541|0x160|[Rr]eparse.*[Ii]ndex"),
            ("offset", r"ReparseIndex|ReparseTable|ReparseKey|EnumerateReparse", r"0x540|0x541|0x160|[Rr]eparse.*[Tt]ag"),
            ("catalog", r"ReparseIndex|ReparseTable|EnumerateReparse"),
        ],
    }),
    ("FS_VBR_RA_011", "combined", {
        "desc": "VBR format-time fields (0x2A, 0x2C, 0x48) never modified during upgrade",
        "searches": [
            ("crossref", "InitializeVcbFromBootSector.md", r"0x2[aA]|0x2[cC]|0x48|[Ff]ormat.*[Tt]ime|[Uu]pgrade"),
            ("offset", r"InitializeVcb|ReadBootSector|BootSector", r"0x2[aA]|0x2[cC]|0x48|[Ff]ormat"),
        ],
    }),
    ("FS_CHKP_RA_013", "combined", {
        "desc": "Three volume states via CHKP flags: 0x002 / 0x602 / 0x682",
        "searches": [
            ("constant", r"0x682|0x602|0x002"),
            ("offset", r"CheckpointFlags|VolumeState|InitCheckpoint", r"0x682|0x602|0x002|[Vv]olume.*[Ss]tate"),
        ],
    }),
]

# ── Group 23: Compression ────────────────────────────────────────────────

CLAIMS += [
    ("CT_COMP_RA_001", "combined", {
        "desc": "Compression config NOT visible via fsutil or raw metadata",
        "searches": [
            ("catalog", r"Compress|Lz4|Zstd|Decompres"),
            ("offset", r"Compress|Lz4|Zstd|CompressionFormat", r"[Cc]onfig|[Pp]arameter|[Ss]etting"),
        ],
    }),
    ("CT_COMP_RA_002", "skip", {
        "reason": "Operational behavior (requires dedup engine); not testable via static analysis",
    }),
    ("CT_CTBL_RA_003", "combined", {
        "desc": "SHA256 and 64K clusters both cause CT row size 160→224",
        "searches": [
            ("constant", r"160|224|0xa0|0xe0"),
            ("offset", r"ContainerEntry|ContainerRow|ContainerSize|RowSize", r"160|224|0xa0|0xe0|SHA.*256|64.*[Kk]"),
        ],
    }),
]

# ── Remove duplicates (some ref_ids appear in groups above that overlap) ──
seen = set()
unique_claims = []
for c in CLAIMS:
    if c[0] not in seen and c[0] != "MD_ATTR_RA_003_bis":
        seen.add(c[0])
        unique_claims.append(c)
CLAIMS = unique_claims

# ── Execution engine ────────────────────────────────────────────────────────

def run_single_search(search_type, spec):
    """Execute one search and return (hit_count, evidence_lines)."""
    evidence = []
    if search_type == "offset":
        func_pat = spec if isinstance(spec, str) else spec[0]
        off_pat = spec[1] if isinstance(spec, tuple) else spec
        decomp = DECOMP_WIN11
        idx = INDEX_WIN11
        hits = search_function_body(func_pat, off_pat, decomp, idx)
        evidence.extend(hits)
    elif search_type == "constant":
        pat = spec if isinstance(spec, str) else spec
        lines = rg(pat, DECOMP_WIN11, context=1, max_count=5)
        evidence.extend(lines[:5])
    elif search_type == "catalog":
        pat = spec if isinstance(spec, str) else spec
        lines = grep_catalog(pat, "refs_win11")
        if not lines:
            lines = grep_catalog(pat)
        evidence.extend([f"  CATALOG: {l.strip()}" for l in lines[:5]])
    elif search_type == "crossref":
        doc_name = spec[0] if isinstance(spec, tuple) else spec
        search_pat = spec[1] if isinstance(spec, tuple) else "."
        lines = check_decompiled_func_doc(doc_name, search_pat)
        evidence.extend([f"  DOC: {l.strip()}" for l in lines[:5]])
    return len(evidence), evidence

def evaluate_claim(ref_id, method, spec):
    """Evaluate a single claim. Returns (verdict, evidence_lines)."""
    if method == "skip":
        return "SKIPPED", [f"  Reason: {spec.get('reason', 'deferred')}"]

    # STRONG vs WEAK evidence (audit fix 2026-06-20): a CONFIRMED verdict requires a FUNCTION-SCOPED
    # match — the claimed offset/token found INSIDE the named function body (search_function_body) — not
    # merely N broad co-occurrences of a common token (a bare "0x20" appears thousands of times, so the
    # old `total_hits>=3 -> CONFIRMED` rubber-stamped any claim citing a common token). Broad file-wide
    # `constant`, function-name `catalog`, and doc `crossref` hits are co-occurrence only -> at most
    # PARTIAL (CITED, needs the function-scoped offset to confirm). The decomp/binary is taken from the
    # spec (decomp/index/binary) so win10/insider claims are not searched against the win11 decomp.
    strong = 0; weak = 0
    all_evidence = []
    decomp = spec.get("decomp", DECOMP_WIN11); index = spec.get("index", INDEX_WIN11)
    binary = spec.get("binary", "refs_win11")

    if method == "offset":
        hits = search_function_body(spec["func_pattern"], spec["offset_pattern"], decomp, index)
        strong += len(hits); all_evidence = hits

    elif method == "constant":
        pat = spec.get("pattern", spec.get("patterns", [""])[0])
        lines = rg(pat, decomp, context=1, max_count=5)
        weak += len(lines); all_evidence = lines[:5]

    elif method == "catalog":
        pat = spec["pattern"]
        lines = grep_catalog(pat, binary) or grep_catalog(pat)
        weak += len(lines); all_evidence = [f"  CATALOG: {l.strip()}" for l in lines[:5]]

    elif method == "crossref":
        lines = check_decompiled_func_doc(spec["doc"], spec["pattern"])
        weak += len(lines); all_evidence = [f"  DOC: {l.strip()}" for l in lines[:5]]

    elif method == "combined":
        for s in spec["searches"]:
            stype = s[0]
            if stype == "offset":
                hits = search_function_body(s[1], s[2], spec.get("decomp", DECOMP_WIN11), spec.get("index", INDEX_WIN11))
                strong += len(hits); all_evidence.extend(hits)
            elif stype == "constant":
                lines = rg(s[1], spec.get("decomp", DECOMP_WIN11), context=1, max_count=5)
                weak += len(lines); all_evidence.extend(lines[:5])
            elif stype == "catalog":
                lines = grep_catalog(s[1], binary) or grep_catalog(s[1])
                weak += len(lines); all_evidence.extend([f"  CATALOG: {l.strip()}" for l in lines[:5]])
            elif stype == "crossref":
                lines = check_decompiled_func_doc(s[1], s[2])
                weak += len(lines); all_evidence.extend([f"  DOC: {l.strip()}" for l in lines[:5]])

    # CONFIRMED requires a function-scoped (strong) match; broad co-occurrence alone is CITED -> PARTIAL.
    if strong >= 1:
        verdict = "CONFIRMED"
    elif (strong + weak) >= 1:
        verdict = "PARTIAL"
    else:
        verdict = "NOT_FOUND"

    return verdict, all_evidence[:8]

# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"Static Analysis Verification of reference_table.csv")
    print(f"=" * 60)
    print(f"Claims to test: {len(CLAIMS)}")
    print(f"Decompiled code: {os.path.basename(DECOMP_WIN11)}")
    print(f"Function catalog: {os.path.basename(FUNC_CATALOG)}")
    print()

    for path in [DECOMP_WIN11, INDEX_WIN11, FUNC_CATALOG]:
        if not os.path.exists(path):
            print(f"ERROR: Missing {path}")
            sys.exit(1)

    results = []
    counts = defaultdict(int)

    for ref_id, method, spec in CLAIMS:
        desc = spec.get("desc", spec.get("reason", ""))
        verdict, evidence = evaluate_claim(ref_id, method, spec)
        counts[verdict] += 1
        results.append((ref_id, verdict, desc, evidence))
        status_char = {"CONFIRMED": "+", "PARTIAL": "~", "NOT_FOUND": "-", "SKIPPED": "S"}[verdict]
        print(f"  [{status_char}] {ref_id:20s} {verdict:12s} {desc[:60]}")

    print()
    print(f"Summary")
    print(f"-" * 40)
    for v in ["CONFIRMED", "PARTIAL", "NOT_FOUND", "SKIPPED"]:
        print(f"  {v:12s}: {counts[v]:3d}")
    print(f"  {'TOTAL':12s}: {sum(counts.values()):3d}")

    report_path = os.path.join(SCRIPT_DIR, "report_static_verification.txt")
    with open(report_path, "w") as f:
        f.write("Static Analysis Verification Report\n")
        f.write(f"{'=' * 60}\n")
        f.write(f"Generated by verify_static.py\n")
        f.write(f"Claims tested: {len(CLAIMS)}\n\n")

        for verdict_type in ["CONFIRMED", "PARTIAL", "NOT_FOUND", "SKIPPED"]:
            entries = [(r, v, d, e) for r, v, d, e in results if v == verdict_type]
            if not entries:
                continue
            f.write(f"\n{'=' * 60}\n")
            f.write(f"{verdict_type} ({len(entries)} entries)\n")
            f.write(f"{'=' * 60}\n\n")
            for ref_id, verdict, desc, evidence in entries:
                f.write(f"  {ref_id}\n")
                f.write(f"    Claim: {desc}\n")
                if evidence:
                    f.write(f"    Evidence:\n")
                    for e in evidence:
                        f.write(f"      {e}\n")
                f.write("\n")

        f.write(f"\n{'=' * 60}\n")
        f.write(f"Summary: ")
        for v in ["CONFIRMED", "PARTIAL", "NOT_FOUND", "SKIPPED"]:
            f.write(f"{v}={counts[v]} ")
        f.write(f"TOTAL={sum(counts.values())}\n")

    print(f"\nReport written to: {report_path}")

    csv_updates = [(r, v) for r, v, d, e in results if v in ("CONFIRMED", "PARTIAL")]
    if csv_updates:
        print(f"\nCSV update candidates ({len(csv_updates)} entries):")
        for ref_id, verdict in csv_updates:
            sa_new = "CONFIRMED" if verdict == "CONFIRMED" else "ENRICHED"
            print(f"  {ref_id}: SA=NOT_TESTED → SA={sa_new}")

    return counts

if __name__ == "__main__":
    main()
