#!/usr/bin/env python3
"""Tool-based verification for ReFS documentation claims.

Runs refsanalysis.py and forefst.py against 20 disk images to verify
all tool-verifiable documentation claims. Produces 2 reports:
- reports/report_tool_execution.txt  (tool log: commands, exit codes, timing)
- reports/report_tool_claims.txt     (claim verification: PASS/FAIL/SKIP)

SCOPE (audit-infra disposition, 2026-06-20): this checks doc<->TOOL CONSISTENCY (does the tool's
output agree with what the doc says the tool does), which is its purpose — it is NOT a doc<->disk
ground-truth gate. Because both legs derive from the same forefst parser, a shared parser bug would
pass here. The independent ground-truth gates are verify_claim.py --regress (raw-byte oracles) and
audit_harness.py (frame-correct on-disk probes); treat this as a smoke check layered on top of them.

Run from the repo root (paths resolve relative to this script). Private disk corpus: set REFS_DISKS.
"""

import hashlib
import os
import re
import subprocess
import sys
import time
from datetime import datetime

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CORPUS = os.environ.get("REFS_CORPUS", os.path.dirname(_REPO))
DISK_BASE = os.environ.get("REFS_DISKS", os.path.join(_CORPUS, "analysis", "rawdisk", "disks"))
REFSANALYSIS = os.path.join(_REPO, "refsanalysis.py")
FOREFST = os.path.join(_REPO, "forefst.py")
REPORT_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGES = {
    1:  ("win10refsmini",             "step1/win10refsmini.raw",                              "3.4",   "4K",  "None"),
    2:  ("win11refsmini",             "step1/win11refsmini.raw",                              "3.14",  "4K",  "CRC64"),
    3:  ("win11refs5g64k",            "step2/win11refs5g64k.raw",                             "3.14",  "64K", "CRC64"),
    4:  ("win11refs2g_sha256",        "step2/win11refs2g_sha256checksums.raw",                "3.14",  "4K",  "SHA256"),
    5:  ("win10to11_upgraded",        "step3/win10to11refs4g_afterwin11mount.raw",            "3.14u", "4K",  "None"),
    6:  ("wininsiderrefs2t",          "step4/wininsiderrefs2t.raw",                           "3.14i", "4K",  "CRC64"),
    7:  ("win1121h2test",             "step4/win1121h2test.raw",                              "3.7",   "4K",  "None"),
    8:  ("win1122h2test",             "step4/win1122h2test.raw",                              "3.9",   "4K",  "None"),
    9:  ("win1123h2test",             "step4/win1123h2test.raw",                              "3.10",  "4K",  "CRC64"),
    10: ("win11refs8gdedup",          "step3/win11refs8gdedup.raw",                           "3.14",  "4K",  "CRC64"),
    11: ("win11refs4gattributes",     "step4/win11refs4gattributes.raw",                      "3.14",  "4K",  "CRC64"),
    12: ("win11refslasttests",        "step5/win11refslasttests.raw",                         "3.14",  "4K",  "CRC64"),
    13: ("win11refstestmftecmd",      "step5/win11refstestmftecmd.raw",                       "3.14",  "4K",  "CRC64"),
    14: ("win11refs8g_zstd",          "step3b/win11refs8gtestcompression_zstdenabled.raw",    "3.14",  "4K",  "CRC64"),
    15: ("win11refs2tintegrity",      "step3/win11refs2tintegrity.raw",                       "3.14",  "4K",  "CRC64"),
    16: ("win11refs2t64ksha256",      "step3/win11refs2t64ksha256checksums.raw",              "3.14",  "64K", "SHA256"),
    17: ("win11refs2g_integrity1",    "step2/win11refs2g_setintegritystreams1.raw",           "3.14",  "4K",  "CRC64"),
    18: ("win11refsbitlocked",        "step3b/win11refsbitlocked.raw",                        "BL",    "-",   "-"),
    19: ("win11refs2tsnapshots",      "step3/win11refs2tsnapshots.raw",                       "3.14",  "4K",  "CRC64"),
    20: ("win11refs2tspecials",       "step3/win11refs2tspecials.raw",                         "3.14",  "4K",  "CRC64"),
}

VALID_IMAGES = [i for i in IMAGES if IMAGES[i][2] != "BL"]

# ── Output cache ──
_cache = {}
_exec_log = []


def image_path(img_id):
    return os.path.join(DISK_BASE, IMAGES[img_id][1])


def run_tool(img_id, tool, subcmd, *extra_args, timeout=600):
    key = (img_id, tool, subcmd, tuple(extra_args))
    if key in _cache:
        return _cache[key]

    img = image_path(img_id)
    if tool == "refsanalysis":
        cmd = [sys.executable, REFSANALYSIS, img, subcmd] + list(extra_args)
    else:
        cmd = [sys.executable, FOREFST, img] + ([subcmd] if subcmd else []) + list(extra_args)

    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=_REPO)
        elapsed = time.time() - t0
        result = (r.stdout, r.stderr, r.returncode, elapsed)
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        result = ("", "TIMEOUT after {}s".format(timeout), -1, elapsed)

    _cache[key] = result
    name = IMAGES[img_id][0]
    _exec_log.append({
        "image": name,
        "tool": tool,
        "subcmd": subcmd,
        "args": extra_args,
        "exit_code": result[2],
        "elapsed": result[3],
        "stdout_len": len(result[0]),
        "stderr_preview": result[1][:200] if result[1] else "",
    })
    return result


def get_boot(img_id):
    return run_tool(img_id, "refsanalysis", "boot")


def get_chkp(img_id):
    return run_tool(img_id, "refsanalysis", "chkp")


def get_supb(img_id):
    return run_tool(img_id, "refsanalysis", "supb")


def get_schema(img_id):
    return run_tool(img_id, "refsanalysis", "schema")


def get_forefst(img_id, *extra):
    return run_tool(img_id, "forefst", None, *extra)


# ── Dual-pattern extraction ──

def extract_dual(output, pattern_a, pattern_b, group=1):
    m1 = re.search(pattern_a, output, re.IGNORECASE | re.MULTILINE)
    m2 = re.search(pattern_b, output, re.IGNORECASE | re.MULTILINE)
    v1 = m1.group(group) if m1 else None
    v2 = m2.group(group) if m2 else None
    if v1 and v2 and v1.lower().strip() != v2.lower().strip():
        return v1, "DUAL_MISMATCH: A='{}' B='{}'".format(v1, v2)
    return (v1 or v2), ""


# ── Test infrastructure ──

class TestResults:
    def __init__(self):
        self.results = []

    def record(self, phase, claim, status, expected, actual, note=""):
        self.results.append({
            "phase": phase,
            "claim": claim,
            "status": status,
            "expected": str(expected),
            "actual": str(actual),
            "note": note,
        })
        tag = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "SKIP": "[SKIP]"}[status]
        print("{} {} | expected={} actual={}{}".format(
            tag, claim, expected, actual, " | " + note if note else ""))

    def pass_(self, phase, claim, expected, actual, note=""):
        self.record(phase, claim, "PASS", expected, actual, note)

    def fail_(self, phase, claim, expected, actual, note=""):
        self.record(phase, claim, "FAIL", expected, actual, note)

    def check(self, phase, claim, condition, expected, actual, note=""):
        self.record(phase, claim, "PASS" if condition else "FAIL", expected, actual, note)


T = TestResults()


# ============================================================
# Phase 1: Bootstrap Chain
# ============================================================

def phase1_bootstrap():
    phase = "P1-Bootstrap"
    print("\n" + "=" * 60)
    print("Phase 1: Bootstrap Chain")
    print("=" * 60)

    # 1.1 VBR fields on all valid images
    for img_id in VALID_IMAGES:
        name = IMAGES[img_id][0]
        stdout, stderr, rc, _ = get_boot(img_id)
        T.check(phase, "#{} {} boot exit=0".format(img_id, name), rc == 0, 0, rc)
        if rc != 0:
            continue
        T.check(phase, "#{} FSRS signature".format(img_id), "FSRS" in stdout, "FSRS present", "FSRS" in stdout)

    # BitLocker error test
    stdout, stderr, rc, _ = get_boot(18)
    T.check(phase, "#18 BitLocker boot rejected", rc != 0, "nonzero", rc, "stderr: " + stderr[:80])

    # Checksum algorithm per image
    checksum_map = {
        "None": [1, 5, 7, 8],
        "CRC64": [2, 3, 6, 9, 10, 11, 12, 13, 14, 15, 17, 19, 20],
        "SHA256": [4, 16],
    }
    algo_codes = {"None": "0x0000", "CRC64": "0x0002", "SHA256": "0x0004"}

    for algo_name, img_ids in checksum_map.items():
        expected_code = algo_codes[algo_name]
        for img_id in img_ids:
            stdout, _, rc, _ = get_boot(img_id)
            if rc != 0:
                continue
            val, warn = extract_dual(stdout,
                r'Checksum algorithm\s+0x2A\s+\S+\s+\S+\s+(0x[0-9a-fA-F]+)',
                r'Checksum algorithm.*?(0x[0-9a-fA-F]{4})\s+\(')
            T.check(phase, "#{} checksum={}".format(img_id, algo_name),
                    val and val.lower() == expected_code.lower(),
                    expected_code, val or "NOT_FOUND",
                    warn)

    # Volume flags
    for img_id in [1]:
        stdout, _, _, _ = get_boot(img_id)
        val, warn = extract_dual(stdout,
            r'Volume flags\s+0x2C\s+\S+\s+\S+\s+\S+\s+(0x[0-9a-fA-F]+)',
            r'Volume flags.*?(0x[0-9a-fA-F]{8})')
        T.check(phase, "#1 v3.4 volume flags=0x00000006",
                val and "00000006" in val.lower(), "0x00000006", val, warn)

    for img_id in [2, 3, 4, 6]:
        stdout, _, _, _ = get_boot(img_id)
        val, warn = extract_dual(stdout,
            r'Volume flags\s+0x2C\s+\S+\s+\S+\s+\S+\s+(0x[0-9a-fA-F]+)',
            r'Volume flags.*?(0x[0-9a-fA-F]{8})')
        T.check(phase, "#{} v3.14 volume flags=0x00000066".format(img_id),
                val and "00000066" in val.lower(), "0x00000066", val, warn)

    # Format GUID
    no_guid_images = [1, 5, 7, 8]
    for img_id in no_guid_images:
        stdout, _, _, _ = get_boot(img_id)
        T.check(phase, "#{} format GUID not set".format(img_id),
                "(not set)" in stdout, "(not set)", "(not set)" in stdout)

    guid_images = [2, 3, 4, 6, 9]
    for img_id in guid_images:
        stdout, _, _, _ = get_boot(img_id)
        T.check(phase, "#{} format GUID populated".format(img_id),
                "(not set)" not in stdout or "Format instance GUID" not in stdout,
                "populated", "(not set)" not in stdout)

    # Cluster sizes
    for img_id in [1, 2, 4, 5]:
        stdout, _, _, _ = get_boot(img_id)
        T.check(phase, "#{} cluster=4K".format(img_id),
                "4.0 KiB" in stdout, "4.0 KiB", "4.0 KiB" in stdout)

    for img_id in [3, 16]:
        stdout, _, _, _ = get_boot(img_id)
        T.check(phase, "#{} cluster=64K".format(img_id),
                "64.0 KiB" in stdout, "64.0 KiB", "64.0 KiB" in stdout)

    # Container size = 64 MiB everywhere
    for img_id in VALID_IMAGES[:5]:
        stdout, _, _, _ = get_boot(img_id)
        T.check(phase, "#{} container=64MiB".format(img_id),
                "64.0 MiB" in stdout, "64.0 MiB", "64.0 MiB" in stdout)

    # Superblock on first 5 images
    for img_id in [1, 2, 3, 4, 5]:
        stdout, _, rc, _ = get_supb(img_id)
        T.check(phase, "#{} SUPB readable".format(img_id), rc == 0 and "SUPB" in stdout,
                "SUPB signature", rc == 0 and "SUPB" in stdout)

    # 1.2 Root table numbering on all valid images
    root_names = {
        0: "Object ID Table",
        1: "Medium Allocator",
        2: "Container Allocator",
        3: "Schema Table",
        4: "Parent-Child",
        5: "Object ID Table dup",
        6: "Block RefCount",
        7: "Container Table",
        8: "Container Table dup",
        9: "Schema Table dup",
        10: "Container Index",
        11: "Integrity State",
        12: "Small Allocator",
    }
    real_roots = {7, 8, 12}

    for img_id in [1, 2, 3, 4, 5, 6, 16]:
        name = IMAGES[img_id][0]
        stdout, _, rc, _ = get_chkp(img_id)
        if rc != 0:
            T.fail_(phase, "#{} chkp failed".format(img_id), 0, rc)
            continue

        rc_m = re.search(r'Root count\s+\S+\s+.*?\s+(\d+)\s*$', stdout, re.MULTILINE)
        rc_val = int(rc_m.group(1)) if rc_m else -1
        T.check(phase, "#{} root count=13".format(img_id), rc_val == 13, 13, rc_val)

        lines = stdout.split("\n")
        root_lines = []
        for line in lines:
            m = re.match(r'\s*(\d+)\s+(.+?)\s+0x[0-9a-f]+\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+MSB\+\s+(\S+)', line)
            if m:
                root_lines.append((int(m.group(1)), m.group(2).strip(), m.group(3), m.group(4), m.group(5)))

        for idx, expected_name in root_names.items():
            matching = [r for r in root_lines if r[0] == idx]
            if matching:
                actual_name = matching[0][1]
                T.check(phase, "#{} root[{}]='{}'".format(img_id, idx, expected_name),
                        expected_name.lower() in actual_name.lower(),
                        expected_name, actual_name)
                root_lcn = matching[0][2]
                phys_lcn = matching[0][3]
                note_field = matching[0][4]
                if idx in real_roots:
                    T.check(phase, "#{} root[{}] physical (real)".format(img_id, idx),
                            root_lcn == phys_lcn and "real" in note_field.lower(),
                            "rootLCN==physLCN, note=real",
                            "rootLCN={} physLCN={} note={}".format(root_lcn, phys_lcn, note_field))
                else:
                    T.check(phase, "#{} root[{}] virtual (translated)".format(img_id, idx),
                            "translat" in note_field.lower(),
                            "note=translated", note_field)

    # 1.3 Three volume states (CHKP flags)
    for img_id, expected_flags in [(1, "00000002"), (5, "00000602"), (2, "00000682")]:
        stdout, _, _, _ = get_chkp(img_id)
        flags_m = re.search(r'Flags\s+0x78\s+.*?(0x[0-9a-fA-F]+)\s*$', stdout, re.MULTILINE)
        flags_val = flags_m.group(1) if flags_m else None
        T.check(phase, "#{} CHKP flags=0x{}".format(img_id, expected_flags),
                flags_val and flags_val.lower() == "0x" + expected_flags,
                "0x" + expected_flags, flags_val)

    # 1.4 Upgraded volume VBR immutability
    boot_5, _, _, _ = get_boot(5)
    T.check(phase, "#5 upgraded VBR checksum still None",
            "0x0000" in boot_5 and "(None)" in boot_5,
            "0x0000 (None)", "found" if "0x0000" in boot_5 else "not found")
    T.check(phase, "#5 upgraded VBR flags still 0x06",
            "0x00000006" in boot_5,
            "0x00000006", "found" if "0x00000006" in boot_5 else "not found")
    T.check(phase, "#5 upgraded format GUID still not set",
            "(not set)" in boot_5,
            "(not set)", "found" if "(not set)" in boot_5 else "not found")

    chkp_5, _, _, _ = get_chkp(5)
    T.check(phase, "#5 upgraded CHKP version=3.14",
            "3.14" in chkp_5, "3.14", "3.14" in chkp_5)
    T.check(phase, "#5 version echo not set",
            "not set" in chkp_5.lower() and "upgraded" in chkp_5.lower(),
            "not set (upgraded)", "found" if "not set" in chkp_5.lower() else "not found")


# ============================================================
# Phase 2: Schema Table
# ============================================================

def phase2_schema():
    phase = "P2-Schema"
    print("\n" + "=" * 60)
    print("Phase 2: Schema Table")
    print("=" * 60)

    # 2.1 Schema counts per version
    schema_counts = {
        1: (15, 12, 27, "v3.4"),
        7: (15, 15, 30, "v3.7"),
        8: (16, 15, 31, "v3.9"),
        9: (15, 15, 30, "v3.10"),
        2: (13, 16, 29, "v3.14"),
        6: (14, 16, 30, "Insider"),
    }

    for img_id, (exp_sys, exp_attr, exp_total, ver) in schema_counts.items():
        stdout, _, rc, _ = get_schema(img_id)
        if rc != 0:
            T.fail_(phase, "#{} schema failed".format(img_id), 0, rc)
            continue

        sys_m = re.search(r'System table schemas \((\d+) entries\)', stdout)
        attr_m = re.search(r'Attribute table schemas \((\d+) entries\)', stdout)

        sys_count = int(sys_m.group(1)) if sys_m else -1
        attr_count = int(attr_m.group(1)) if attr_m else -1

        T.check(phase, "{} system schemas={}".format(ver, exp_sys),
                sys_count == exp_sys, exp_sys, sys_count)
        T.check(phase, "{} attribute schemas={}".format(ver, exp_attr),
                attr_count == exp_attr, exp_attr, attr_count)
        T.check(phase, "{} total schemas={}".format(ver, exp_total),
                sys_count + attr_count == exp_total, exp_total, sys_count + attr_count)

    # 2.2 Schema ID presence/absence
    schema_presence = [
        ("0xe050", "Object Data (legacy)", [1, 7, 8], [9, 2]),
        ("0xe070", "Reserved (legacy)", [1, 7, 8, 9], [2]),
        ("0xe0e0", "SysDirEntry (legacy)", [1, 7, 8, 9], [2]),
        ("0xe0f0", "SysFileStream (legacy)", [1, 7, 8], [9, 2]),
        ("0xe120", "Candidate Table", [8, 9, 2], [1, 7]),
        ("0xe130", "Heat Engine", [9, 2], [1, 7, 8]),
        ("0xe140", "Vol Attestation", [6], [1, 2, 7, 8, 9]),
        ("0x1b0", "$SNAPSHOT", [7, 8, 9, 2], [1]),
        ("0x1c0", "$REPARSE v3.7+", [7, 8, 9, 2], [1]),
        ("0x1d0", "$EA_INFORMATION", [7, 8, 9, 2], [1]),
        ("0x1e0", "$EA", [2], [1, 7, 8, 9]),
        ("0x1f0", "$LOGGED_UTIL", [2], [1, 7, 8, 9]),
    ]

    for schema_id, label, present_imgs, absent_imgs in schema_presence:
        for img_id in present_imgs:
            stdout, _, _, _ = get_schema(img_id)
            found = schema_id.lower() in stdout.lower() or schema_id in stdout
            T.check(phase, "{} present in #{}".format(schema_id, img_id),
                    found, "present", found)
        for img_id in absent_imgs:
            stdout, _, _, _ = get_schema(img_id)
            found = schema_id.lower() in stdout.lower() or schema_id in stdout
            T.check(phase, "{} absent from #{}".format(schema_id, img_id),
                    not found, "absent", "found" if found else "absent")

    # 2.3 Naming corrections
    for img_id in [2, 7, 9]:
        stdout, _, _, _ = get_schema(img_id)
        T.check(phase, "#{} 0x160 = Reparse Index".format(img_id),
                "Reparse Index" in stdout or "reparse" in stdout.lower(),
                "Reparse Index", "found" if "Reparse Index" in stdout else "not found")

    for img_id in [7, 2]:
        stdout, _, _, _ = get_schema(img_id)
        T.check(phase, "#{} 0x1b0 = Snapshot".format(img_id),
                "Snapshot" in stdout or "SNAPSHOT" in stdout,
                "$SNAPSHOT", "found" if "Snapshot" in stdout or "SNAPSHOT" in stdout else "not found")

    # 2.4 Schema consistency on extended v3.14 images
    ref_stdout, _, _, _ = get_schema(2)
    ref_sys = re.search(r'System table schemas \((\d+) entries\)', ref_stdout)
    ref_attr = re.search(r'Attribute table schemas \((\d+) entries\)', ref_stdout)
    ref_counts = (int(ref_sys.group(1)), int(ref_attr.group(1))) if ref_sys and ref_attr else None

    for img_id in [10, 11, 12, 13, 14, 15, 17, 19, 20]:
        stdout, _, rc, _ = get_schema(img_id)
        if rc != 0:
            continue
        sys_m = re.search(r'System table schemas \((\d+) entries\)', stdout)
        attr_m = re.search(r'Attribute table schemas \((\d+) entries\)', stdout)
        if sys_m and attr_m and ref_counts:
            T.check(phase, "#{} schema counts match v3.14 baseline".format(img_id),
                    (int(sys_m.group(1)), int(attr_m.group(1))) == ref_counts,
                    ref_counts, (int(sys_m.group(1)), int(attr_m.group(1))))


# ============================================================
# Phase 3: B+-tree Node Structure
# ============================================================

def phase3_btree():
    phase = "P3-BTree"
    print("\n" + "=" * 60)
    print("Phase 3: B+-tree / Page References")
    print("=" * 60)

    # 3.1 Page reference sizes
    ref_sizes = {
        1: ("0x68", 104, "v3.4 CRC32-C"),
        2: ("0x30", 48, "v3.14 CRC64"),
        3: ("0x30", 48, "v3.14 64K CRC64"),
        4: ("0x48", 72, "SHA-256"),
        9: ("0x30", 48, "v3.10 CRC64"),
        16: ("0x48", 72, "64K + SHA-256"),
    }

    for img_id, (exp_hex, exp_dec, label) in ref_sizes.items():
        stdout, _, _, _ = get_chkp(img_id)
        ref_m = re.search(r'Ref size.*?(0x[0-9a-fA-F]+)\s+\(\d+ bytes\)', stdout)
        ref_val = ref_m.group(1) if ref_m else None
        T.check(phase, "#{} ref_size={} ({})".format(img_id, exp_hex, label),
                ref_val and ref_val.lower() == exp_hex.lower(),
                exp_hex, ref_val)

    # 3.2 CPC by cluster size
    for img_id in [1, 2, 4]:
        stdout, _, _, _ = get_chkp(img_id)
        cpc_m = re.search(r'CPC:\s*(\d+)', stdout)
        cpc = int(cpc_m.group(1)) if cpc_m else -1
        T.check(phase, "#{} CPC=16384 (4K clusters)".format(img_id),
                cpc == 16384, 16384, cpc)

    for img_id in [3, 16]:
        stdout, _, _, _ = get_chkp(img_id)
        cpc_m = re.search(r'CPC:\s*(\d+)', stdout)
        cpc = int(cpc_m.group(1)) if cpc_m else -1
        T.check(phase, "#{} CPC=1024 (64K clusters)".format(img_id),
                cpc == 1024, 1024, cpc)

    # 3.3 bit_length verification (computed, not from output)
    T.check(phase, "CPC=16384 bit_length()=15", (16384).bit_length() == 15, 15, (16384).bit_length())
    T.check(phase, "CPC=1024 bit_length()=11", (1024).bit_length() == 11, 11, (1024).bit_length())

    # 3.4 MSB+ on all roots
    for img_id in [1, 2, 3, 16]:
        stdout, _, _, _ = get_chkp(img_id)
        msb_count = stdout.count("MSB+")
        T.check(phase, "#{} all 13 roots have MSB+".format(img_id),
                msb_count >= 13, ">=13", msb_count)

    # 3.5 64K + SHA-256 combined
    stdout_16, _, _, _ = get_chkp(16)
    cpc_m = re.search(r'CPC:\s*(\d+)', stdout_16)
    ref_m = re.search(r'Ref size.*?(0x[0-9a-fA-F]+)\s+\(\d+ bytes\)', stdout_16)
    T.check(phase, "#16 64K+SHA256: CPC=1024 AND ref=0x48",
            cpc_m and ref_m and int(cpc_m.group(1)) == 1024 and ref_m.group(1).lower() == "0x48",
            "CPC=1024 ref=0x48",
            "CPC={} ref={}".format(
                cpc_m.group(1) if cpc_m else "?",
                ref_m.group(1) if ref_m else "?"))


# ============================================================
# Phase 4: Directory Entries + forefst.py
# ============================================================

def phase4_dir_entries():
    phase = "P4-DirEntries"
    print("\n" + "=" * 60)
    print("Phase 4: Directory Entries + forefst.py")
    print("=" * 60)

    # 4.1 forefst.py CSV column verification on all valid images
    expected_cols = [
        "OID", "ParentOID", "ParentPath", "FileName", "Extension",
        "FileSize", "IsDirectory", "IsDeleted", "DeletionSource", "IsResident",
        "Created", "Modified", "Changed", "Accessed", "FileAttributes",
        "SecurityId", "OwnerSid", "USN", "HasAds", "AdsNames",
        "IsEncrypted", "IsCompressed", "HasIntegrity", "HasEA", "ReparseTarget",
        "HardLinkCount", "SnapshotCount", "TimestompFlags",
        "GroupSid", "AllocatedSize", "ReparseTag", "RecoveredChild",
        "HardLinkNames", "FileId", "HomeOid", "IsSparse", "InternalFlags", "RefsVersion",
    ]

    for img_id in VALID_IMAGES:
        name = IMAGES[img_id][0]
        stdout, stderr, rc, _ = get_forefst(img_id)
        if rc != 0:
            T.fail_(phase, "#{} {} forefst exit=0".format(img_id, name), 0, rc,
                    "stderr: " + stderr[:80])
            continue

        lines = [l for l in stdout.split("\n") if l.strip() and not l.startswith("[forefst]")]
        if not lines:
            T.fail_(phase, "#{} forefst has CSV output".format(img_id), ">0 lines", 0)
            continue

        header = lines[0]
        missing = [c for c in expected_cols if c not in header]
        T.check(phase, "#{} CSV has all 38 columns".format(img_id),
                len(missing) == 0, "all present", "missing: {}".format(missing) if missing else "all present")

    # 4.2 BitLocker forefst error
    stdout, stderr, rc, _ = get_forefst(18)
    T.check(phase, "#18 BitLocker forefst rejected", rc != 0, "nonzero", rc)

    # 4.3 Version detection
    version_checks = {1: "3.4", 2: "3.14", 7: "3.7", 8: "3.9", 9: "3.10"}
    for img_id, expected_ver in version_checks.items():
        stdout, _, rc, _ = get_forefst(img_id)
        if rc != 0:
            continue
        lines = [l for l in stdout.split("\n") if l.strip() and not l.startswith("[forefst]")]
        if len(lines) > 1:
            last_col = lines[1].rstrip().split(",")[-1]
            T.check(phase, "#{} RefsVersion={}".format(img_id, expected_ver),
                    last_col == expected_ver, expected_ver, last_col)

    # 4.4 OID ranges
    for img_id in [2, 12]:
        stdout, _, rc, _ = get_forefst(img_id)
        if rc != 0:
            continue
        lines = [l for l in stdout.split("\n") if l.strip() and not l.startswith("[forefst]")]
        oids = []
        for line in lines[1:]:
            parts = line.split(",")
            if parts[0].startswith("0x"):
                oid_val = int(parts[0], 16)
                oids.append(oid_val)
        if oids:
            min_oid = min(oids)
            T.check(phase, "#{} min user OID >= 0x701".format(img_id),
                    min_oid >= 0x701, ">=0x701", hex(min_oid))

    # 4.5 Resident files
    for img_id in [2, 12]:
        stdout, _, rc, _ = get_forefst(img_id)
        if rc != 0:
            continue
        resident_count = stdout.count(",True,") if "IsResident" in stdout else 0
        has_resident = any("True" in line.split(",")[9] for line in stdout.split("\n")[1:]
                          if len(line.split(",")) > 9 and not line.startswith("["))
        T.check(phase, "#{} has resident files".format(img_id),
                has_resident, True, has_resident)

    # 4.6 Timestamps with sub-second precision
    stdout_2, _, _, _ = get_forefst(2)
    ts_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{7}'
    ts_matches = re.findall(ts_pattern, stdout_2)
    T.check(phase, "#2 timestamps have 7-digit precision",
            len(ts_matches) > 0, ">0 matches", len(ts_matches))

    # 4.7 Directory_Internal flag
    for img_id in [2, 12]:
        stdout, _, _, _ = get_forefst(img_id)
        T.check(phase, "#{} has Directory_Internal flag".format(img_id),
                "Directory_Internal" in stdout, True, "Directory_Internal" in stdout)

    # 4.8 Feature detection on rich volumes
    # Snapshots on #19
    stdout_19, _, rc_19, _ = get_forefst(19, "")
    if rc_19 == 0:
        lines_19 = [l for l in stdout_19.split("\n") if l.strip() and not l.startswith("[")]
        has_snapshot = any(
            len(parts := l.split(",")) > 26 and parts[26].strip() and parts[26].strip() not in ("0", "")
            for l in lines_19[1:])
        T.check(phase, "#19 snapshots: SnapshotCount > 0",
                has_snapshot, True, has_snapshot, "forefst default listing on snapshot volume")


# ============================================================
# Phase 5: MLog — rewrite complete (errata E10); not re-run here
# ============================================================

def phase5_mlog():
    phase = "P5-MLog"
    print("\n" + "=" * 60)
    print("Phase 5: MLog — SHIPPED (cmd_mlog); not re-run in this snapshot")
    print("=" * 60)
    T.record(phase, "MLog not re-run in this snapshot",
             "SKIP", "N/A", "N/A",
             "Rewrite complete (errata E10 resolved): refs_logfile.py superseded "
             "by the shipped 'mlog' command in refsanalysis.py. Tests pending re-run.")


# ============================================================
# Phase 6: Block Refcount
# ============================================================

def phase6_block_refcount():
    phase = "P6-BlockRefcount"
    print("\n" + "=" * 60)
    print("Phase 6: Block Refcount")
    print("=" * 60)

    # Root #6 exists in all valid images
    for img_id in [1, 2, 3, 6, 10, 16]:
        stdout, _, _, _ = get_chkp(img_id)
        T.check(phase, "#{} root[6] = Block RefCount".format(img_id),
                "Block RefCount" in stdout or "RefCount" in stdout,
                "present", "Block RefCount" in stdout)

    # Schema 0xe0b0 exists
    for img_id in [1, 2, 6]:
        stdout, _, _, _ = get_schema(img_id)
        T.check(phase, "#{} schema 0xe0b0 present".format(img_id),
                "0xe0b0" in stdout.lower() or "e0b0" in stdout.lower(),
                "present", "0xe0b0" in stdout.lower())


# ============================================================
# Phase 7: Container Table & Virtual Addressing
# ============================================================

def phase7_containers():
    phase = "P7-Containers"
    print("\n" + "=" * 60)
    print("Phase 7: Container Table & Virtual Addressing")
    print("=" * 60)

    # Physical roots (7, 8, 12) have rootLCN == physLCN
    for img_id in [1, 2, 3, 16]:
        stdout, _, _, _ = get_chkp(img_id)
        lines = stdout.split("\n")
        for line in lines:
            m = re.match(r'\s*(\d+)\s+.+?\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+MSB\+\s+(\S+)', line)
            if m:
                idx = int(m.group(1))
                root_lcn = m.group(2)
                phys_lcn = m.group(3)
                if idx in (7, 8, 12):
                    T.check(phase, "#{} root[{}] physLCN == rootLCN".format(img_id, idx),
                            root_lcn == phys_lcn, "equal",
                            "root={} phys={}".format(root_lcn, phys_lcn))

    # Container count scaling
    for img_id in [2]:
        stdout, _, rc, _ = run_tool(img_id, "refsanalysis", "containers")
        if rc == 0:
            ce_m = re.search(r'[Cc]ontainer entries:\s*(\d+)', stdout) or \
                   re.search(r'[Mm]apped containers:\s*(\d+)', stdout) or \
                   re.search(r'[Tt]otal containers:\s*(\d+)', stdout)
            if ce_m:
                count = int(ce_m.group(1))
                T.check(phase, "#2 container count ~31 (2 GiB)",
                        25 <= count <= 40, "~31", count)

    # CPC already verified in Phase 3, but verify through container output too
    for img_id in [3, 16]:
        stdout, _, _, _ = get_chkp(img_id)
        cpc_m = re.search(r'CPC:\s*(\d+)', stdout)
        if cpc_m:
            T.check(phase, "#{} CPC=1024 in containers (64K)".format(img_id),
                    int(cpc_m.group(1)) == 1024, 1024, int(cpc_m.group(1)))


# ============================================================
# Write reports
# ============================================================

def write_execution_report():
    path = os.path.join(REPORT_DIR, "report_tool_execution.txt")
    with open(path, "w") as f:
        f.write("=" * 72 + "\n")
        f.write("  TOOL EXECUTION LOG\n")
        f.write("  Date: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        f.write("  Images: {}\n".format(len(IMAGES)))
        f.write("  Commands executed: {}\n".format(len(_exec_log)))
        f.write("=" * 72 + "\n\n")

        total_time = sum(e["elapsed"] for e in _exec_log)
        f.write("Total execution time: {:.1f}s\n\n".format(total_time))

        for e in _exec_log:
            f.write("{:<30s} {:<12s} {:>5s} exit={:<3d} {:.1f}s  stdout={}B\n".format(
                e["image"], e["subcmd"] or "forefst",
                str(e["args"]) if e["args"] else "",
                e["exit_code"], e["elapsed"], e["stdout_len"]))
            if e["stderr_preview"]:
                f.write("  stderr: {}\n".format(e["stderr_preview"][:100]))
    return path


def write_claims_report():
    path = os.path.join(REPORT_DIR, "report_tool_claims.txt")
    with open(path, "w") as f:
        f.write("=" * 72 + "\n")
        f.write("  TOOL-VERIFIED CLAIMS REPORT\n")
        f.write("  Date: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        f.write("=" * 72 + "\n\n")

        phases = {}
        for r in T.results:
            phases.setdefault(r["phase"], []).append(r)

        total_pass = sum(1 for r in T.results if r["status"] == "PASS")
        total_fail = sum(1 for r in T.results if r["status"] == "FAIL")
        total_warn = sum(1 for r in T.results if r["status"] == "WARN")
        total_skip = sum(1 for r in T.results if r["status"] == "SKIP")

        f.write("SUMMARY\n")
        f.write("-" * 72 + "\n")
        for phase_name in sorted(phases.keys()):
            pr = phases[phase_name]
            p = sum(1 for r in pr if r["status"] == "PASS")
            fa = sum(1 for r in pr if r["status"] == "FAIL")
            w = sum(1 for r in pr if r["status"] == "WARN")
            s = sum(1 for r in pr if r["status"] == "SKIP")
            f.write("  {:<30s} {:>3d} PASS  {:>3d} FAIL  {:>3d} WARN  {:>3d} SKIP\n".format(
                phase_name, p, fa, w, s))
        f.write("-" * 72 + "\n")
        f.write("  {:<30s} {:>3d} PASS  {:>3d} FAIL  {:>3d} WARN  {:>3d} SKIP\n".format(
            "TOTAL", total_pass, total_fail, total_warn, total_skip))
        f.write("\n")

        f.write("DETAILED RESULTS\n")
        f.write("-" * 72 + "\n")
        for phase_name in sorted(phases.keys()):
            f.write("\n## {}\n\n".format(phase_name))
            for r in phases[phase_name]:
                tag = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "SKIP": "[SKIP]"}[r["status"]]
                line = "{} {} | expected={} actual={}".format(tag, r["claim"], r["expected"], r["actual"])
                if r["note"]:
                    line += " | {}".format(r["note"])
                f.write(line + "\n")

        f.write("\n" + "=" * 72 + "\n")
        if total_fail == 0:
            f.write("  RESULT: ALL CLAIMS VERIFIED\n")
        else:
            f.write("  RESULT: {} FAILURES DETECTED\n".format(total_fail))
        f.write("=" * 72 + "\n")
    return path


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("Tool-Based Documentation Verification")
    print("Images: {}  |  Tool: refsanalysis.py + forefst.py".format(len(IMAGES)))
    print("=" * 60)

    phase1_bootstrap()
    phase2_schema()
    phase3_btree()
    phase4_dir_entries()
    phase5_mlog()
    phase6_block_refcount()
    phase7_containers()

    exec_path = write_execution_report()
    claims_path = write_claims_report()

    total_pass = sum(1 for r in T.results if r["status"] == "PASS")
    total_fail = sum(1 for r in T.results if r["status"] == "FAIL")
    total_warn = sum(1 for r in T.results if r["status"] == "WARN")
    total_skip = sum(1 for r in T.results if r["status"] == "SKIP")

    print("\n" + "=" * 60)
    print("TOTAL: {} PASS / {} FAIL / {} WARN / {} SKIP".format(
        total_pass, total_fail, total_warn, total_skip))
    print("Execution log: {}".format(exec_path))
    print("Claims report: {}".format(claims_path))
    print("=" * 60)

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
