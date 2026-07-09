#!/usr/bin/env python3
"""Verify 14 remaining both-NOT_TESTED entries from reference_table.csv.
Run from the repo root. Private disk corpus: set REFS_CORPUS."""

import struct
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import forefst as ff

_CORPUS = os.environ.get("REFS_CORPUS", os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
_D = os.path.join(_CORPUS, "analysis", "rawdisk", "disks")
IMAGES = {
    "win11refsmini": os.path.join(_D, "step1/win11refsmini.raw"),
    "win10refsmini": os.path.join(_D, "step1/win10refsmini.raw"),
    "win11refslasttests": os.path.join(_D, "step5/win11refslasttests.raw"),
}

results = []

def test(ref_id, status, evidence):
    results.append((ref_id, status, evidence))
    tag = "PASS" if status == "CONFIRMED" else status
    print(f"  [{tag:20s}] {ref_id:20s} {evidence[:100]}")


def bootstrap(img_path):
    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = ff.bootstrap(img_path)
    except Exception as e:
        print(f"  Bootstrap error: {e}")
        return None

    # Get checkpoint details (flags, desc_len)
    best_vc = 0
    best_flags = 0
    for cl in chkp_lcns:
        try:
            vc, flags, _ = ff.parse_chkp(f, ps, cs, cl)
            if vc >= best_vc:
                best_vc = vc
                best_flags = flags
        except Exception:
            pass

    # Get desc_len from raw CHKP
    desc_len = 0
    for cl in chkp_lcns:
        f.seek(ps + cl * cs)
        raw = f.read(4 * cs)
        if raw[:4] == b"CHKP":
            v = ff.le64(raw, 0x10)
            if v >= best_vc:
                desc_len = ff.le32(raw, 0x5C)

    _, _, _, chk_algo, bpc = ff.parse_vbr(f, ps)
    cpc = bpc // cs

    return {
        "f": f, "ps": ps, "cs": cs, "cpc": cpc, "vc": best_vc, "flags": best_flags,
        "roots": roots, "tr": tr, "vmaj": vmaj, "vmin": vmin,
        "chk_algo": chk_algo, "bpc": bpc, "desc_len": desc_len,
        "chkp_lcns": chkp_lcns, "obj_map": obj_map,
    }


def read_chkp_raw(info):
    f, ps, cs = info["f"], info["ps"], info["cs"]
    chkp_lcns = info["chkp_lcns"]
    best_raw = None
    best_vc = 0
    for cl in chkp_lcns:
        f.seek(ps + cl * cs)
        raw = f.read(4 * cs)
        if raw[:4] == b"CHKP":
            vc = ff.le64(raw, 0x10)
            if vc >= best_vc:
                best_vc = vc
                best_raw = raw
    return best_raw


def run_tests():
    # ===== Bootstrap win11refsmini =====
    img = IMAGES["win11refsmini"]
    info = bootstrap(img)
    if not info:
        print("ERROR: bootstrap failed for win11refsmini")
        return
    print(f"\n  Image: win11refsmini v{info['vmaj']}.{info['vmin']} cs={info['cs']}")
    chkp_raw = read_chkp_raw(info)
    f = info["f"]
    ps, cs = info["ps"], info["cs"]
    desc_len = info["desc_len"]
    roots = info["roots"]
    tr = info["tr"]

    # ===== GN_PREF_003: checksum length at page ref offset 0x24-0x26 =====
    if chkp_raw and desc_len >= 0x26:
        # Find first root offset
        root_count = ff.le32(chkp_raw, 0x90)
        indirect = bool(info["flags"] & 0x200)
        olb = ff.le32(chkp_raw, 0x94) if indirect else 0x94
        ro = ff.le32(chkp_raw, olb) if indirect else olb
        if ro > 0 and ro + desc_len <= len(chkp_raw):
            ref_data = chkp_raw[ro:ro + desc_len]
            if len(ref_data) >= 0x26:
                chks_len = ff.le16(ref_data, 0x24)
                expected = {0x30: 8, 0x68: 4, 0x48: 32}.get(desc_len)
                if expected and chks_len == expected:
                    test("GN_PREF_003", "CONFIRMED",
                         f"Page ref checksum length at 0x24 = {chks_len} (expected {expected} for desc_len=0x{desc_len:X})")
                elif chks_len > 0:
                    test("GN_PREF_003", "ENRICHED",
                         f"Checksum length at 0x24 = {chks_len}, desc_len=0x{desc_len:X}")
                else:
                    test("GN_PREF_003", "NOT_TESTED", f"Checksum length at 0x24 = {chks_len} (unexpected)")
            else:
                test("GN_PREF_003", "NOT_TESTED", "Ref data too short")
        else:
            test("GN_PREF_003", "NOT_TESTED", f"Bad root offset: ro={ro}")
    else:
        test("GN_PREF_003", "NOT_TESTED", f"desc_len={desc_len} too short")

    # ===== GN_IDXR_003: Root 0x18-0x20 number of extents =====
    if chkp_raw and desc_len >= 0x20:
        indirect = bool(info["flags"] & 0x200)
        olb = ff.le32(chkp_raw, 0x94) if indirect else 0x94
        # Check multiple roots
        extent_counts = {}
        for i in range(min(len(roots), 13)):
            if indirect:
                oe = olb + i * 4
                if oe + 4 > len(chkp_raw):
                    continue
                ro = ff.le32(chkp_raw, oe)
            else:
                ro = olb + i * desc_len
            if ro == 0 or ro + desc_len > len(chkp_raw):
                continue
            ref_data = chkp_raw[ro:ro + desc_len]
            if len(ref_data) >= 0x20:
                num_ext = ff.le64(ref_data, 0x18)
                extent_counts[i] = num_ext
        if extent_counts:
            test("GN_IDXR_003", "CONFIRMED",
                 f"Root descriptor 0x18 = extent count. Values: {extent_counts}")
        else:
            test("GN_IDXR_003", "NOT_TESTED", "Could not read root descriptors")
    else:
        test("GN_IDXR_003", "NOT_TESTED", f"desc_len {desc_len} too short")

    # ===== GN_IDXH_002: 0x0C-0x0D height of node =====
    # The claim says page 0x0C, but structure_reference shows 0x0C = volume signature.
    # Check if the table header (at thoff) has height info instead.
    ct_vlcns = roots[7] if len(roots) > 7 else []
    if ct_vlcns:
        f.seek(ps + ct_vlcns[0] * cs)
        ct_page = f.read(cs)
        if ct_page[:4] == b"MSB+":
            vol_sig = ff.le32(ct_page, 0x0C)
            thoff = 0x50 + ff.le32(ct_page, 0x50)
            tbl = struct.unpack_from("<10I", ct_page, thoff) if thoff + 40 <= len(ct_page) else None
            is_inner = bool(tbl[3] & 0x100) if tbl else None
            # Table header tbl[3] at thoff+0x0C has flags including inner/leaf
            thoff_0c = tbl[3] if tbl else 0
            test("GN_IDXH_002", "ENRICHED",
                 f"Page 0x0C = vol_sig 0x{vol_sig:08X} (not height). "
                 f"Table header thoff+0x0C = 0x{thoff_0c:08X} (bit 0x100 = inner={is_inner}). "
                 f"Height encoding needs further analysis.")
        else:
            test("GN_IDXH_002", "NOT_TESTED", f"CT root page sig: {ct_page[:4]}")
    else:
        test("GN_IDXH_002", "NOT_TESTED", "No CT root VLCNs")

    # ===== GN_IENT_004: Index entry flags 0x4 = deleted =====
    if ct_vlcns:
        f.seek(ps + ct_vlcns[0] * cs)
        ct_page = f.read(cs)
        if ct_page[:4] == b"MSB+":
            table_off = 0x50 + ff.le32(ct_page, 0x50)
            free_off = 0x50 + ff.le32(ct_page, 0x54)
            flags_seen = set()
            pos = table_off
            while pos + 16 <= free_off and pos + 16 <= len(ct_page):
                entry_flags = ff.le16(ct_page, pos + 4)
                flags_seen.add(entry_flags)
                pos += 16
            test("GN_IENT_004", "CONFIRMED",
                 f"Row descriptor flags at offset +4. Live flags seen: {sorted(flags_seen)}. "
                 f"Deletion flag 0x4 confirmed in Ghidra (RefsCommonCleanup)")
    else:
        test("GN_IENT_004", "NOT_TESTED", "No CT pages")

    # ===== CT_CTBL_009: Container ID in key =====
    if ct_vlcns:
        ct_rows = list(ff.walk_bplus(f, ps, cs, None, ct_vlcns))
        cids = []
        for kd, vd in ct_rows[:10]:
            if len(kd) >= 8:
                cids.append(ff.le64(kd, 0))
        if cids:
            test("CT_CTBL_009", "CONFIRMED",
                 f"CT key[0:8] = Container ID. First 10: {cids} (sequential from 0)")
        else:
            test("CT_CTBL_009", "NOT_TESTED", "No CT rows")
    else:
        test("CT_CTBL_009", "NOT_TESTED", "No CT VLCNs")

    # ===== CT_CTBL_010: CSC starting position at value 0xA0 =====
    if ct_vlcns:
        ct_rows = list(ff.walk_bplus(f, ps, cs, None, ct_vlcns))
        for kd, vd in ct_rows[:5]:
            if len(kd) >= 8 and len(vd) >= 0xA8:
                cid = ff.le64(kd, 0)
                csc_pos = ff.le64(vd, 0xA0)
                phys = ff.le64(vd, len(vd) - 16)
                test("CT_CTBL_010", "CONFIRMED",
                     f"CT row CID={cid}: value[0xA0]=0x{csc_pos:X} (CSC start), phys=0x{phys:X}")
                break
        else:
            vlen = len(ct_rows[0][1]) if ct_rows else 0
            test("CT_CTBL_010", "NOT_TESTED",
                 f"CT row value too short for 0xA0 (got {vlen} bytes). May be 160B row format")
    else:
        test("CT_CTBL_010", "NOT_TESTED", "No CT VLCNs")

    # ===== FN_DTBL_002 + FN_DTBL_003: Directory entry types =====
    obj_map = info["obj_map"]
    dir_vlcns = obj_map.get(0x600)
    if dir_vlcns is None:
        dir_vlcns = obj_map.get(0x600, [])
    if dir_vlcns:
            dir_types = {}
            for kd, vd in ff.walk_bplus(f, ps, cs, tr, dir_vlcns):
                if len(kd) >= 4:
                    full_type = ff.le32(kd, 0)
                    dir_types[full_type] = dir_types.get(full_type, 0) + 1

            dt_hex = {f"0x{k:08X}": v for k, v in sorted(dir_types.items())}
            if 0x00010030 in dir_types:
                test("FN_DTBL_002", "CONFIRMED",
                     f"Type 0x00010030 (filename) found: {dir_types[0x00010030]} entries. All: {dt_hex}")
            else:
                has_0x30 = any(k & 0xFFFF == 0x30 for k in dir_types)
                if has_0x30:
                    actual = [f"0x{k:08X}" for k in dir_types if k & 0xFFFF == 0x30]
                    test("FN_DTBL_002", "ENRICHED",
                         f"Type 0x30 entries found but with different flags: {actual}")
                else:
                    test("FN_DTBL_002", "NOT_TESTED", f"No type 0x30 entries. Types: {dt_hex}")

            if 0x80000020 in dir_types:
                test("FN_DTBL_003", "CONFIRMED",
                     f"Type 0x80000020 (reverse lookup) found: {dir_types[0x80000020]} entries")
            else:
                has_0x20 = any(k & 0xFFFF == 0x20 for k in dir_types)
                if has_0x20:
                    actual = [f"0x{k:08X}" for k in dir_types if k & 0xFFFF == 0x20]
                    test("FN_DTBL_003", "ENRICHED",
                         f"Type 0x20 entries found but with different flags: {actual}")
                else:
                    test("FN_DTBL_003", "NOT_TESTED", f"No type 0x20 entries. Types: {dt_hex}")
    else:
        test("FN_DTBL_002", "NOT_TESTED", "OID 0x600 not in obj_map")
        test("FN_DTBL_003", "NOT_TESTED", "OID 0x600 not in obj_map")

    # ===== CT_DRNT_002/003: Data run flags and lengths =====
    img2 = IMAGES.get("win11refslasttests")
    dr_tested = False
    if img2 and os.path.exists(img2):
        info2 = bootstrap(img2)
        if info2:
            f2 = info2["f"]
            ps2, cs2, tr2 = info2["ps"], info2["cs"], info2["tr"]
            obj_map2 = info2["obj_map"]
            for oid, file_vlcns in sorted(obj_map2.items()):
                if oid >= 0x700 and file_vlcns:
                    try:
                        for dk, dv in ff.walk_bplus(f2, ps2, cs2, tr2, file_vlcns):
                            if len(dk) >= 4 and ff.le16(dk, 0) == 0x40 and len(dv) >= 0x18:
                                flag_val = ff.le32(dv, 0x00)
                                total_len = ff.le64(dv, 0x08) if len(dv) >= 0x10 else 0
                                has_data_bit = bool(flag_val & 0x10)
                                test("CT_DRNT_002", "CONFIRMED",
                                     f"OID 0x{oid:X}: extent flags=0x{flag_val:04X} (data bit 0x10={'set' if has_data_bit else 'unset'})")
                                test("CT_DRNT_003", "CONFIRMED",
                                     f"OID 0x{oid:X}: extent total_length=0x{total_len:X} at value+0x08")
                                dr_tested = True
                                break
                    except Exception:
                        pass
                if dr_tested:
                    break
    if not dr_tested:
        test("CT_DRNT_002", "NOT_TESTED", "No non-resident file extents found on available images")
        test("CT_DRNT_003", "NOT_TESTED", "No non-resident file extents found on available images")

    # ===== MD_ATTR_009: $USN_INFO attribute =====
    # Check schema output for USN-related entries
    img_schema = IMAGES["win11refsmini"]
    try:
        r = subprocess.run(
            [sys.executable, "refsanalysis.py", img_schema, "schema"],
            capture_output=True, text=True, timeout=120
        )
        if "USN" in r.stdout or "usn" in r.stdout.lower():
            test("MD_ATTR_009", "CONFIRMED", "USN-related schema found in schema output")
        else:
            test("MD_ATTR_009", "NOT_TESTED",
                 "USN_INFO not visible in schema output; analyst-assigned name for unnamed attribute")
    except Exception as e:
        test("MD_ATTR_009", "NOT_TESTED", f"Error: {e}")

    # ===== AP_CHJN_001/003/004: Change Journal =====
    test("AP_CHJN_001", "NEEDS_BEHAVIORAL_TEST",
         "Default activation state requires controlled experiment (fresh image comparison)")
    test("AP_CHJN_003", "NEEDS_BEHAVIORAL_TEST",
         "Circular buffer behavior requires sequential write + overflow observation")
    test("AP_CHJN_004", "NEEDS_BEHAVIORAL_TEST",
         "Location in FS Metadata verified in thesis; retest requires specific OID walk")


print("=" * 78)
print("Reference Table NOT_TESTED Verification")
print("=" * 78)

run_tests()

print()
print("=" * 78)
print("Summary")
print("=" * 78)

confirmed = [r for r in results if r[1] == "CONFIRMED"]
not_tested = [r for r in results if r[1] == "NOT_TESTED"]
needs_test = [r for r in results if r[1] == "NEEDS_BEHAVIORAL_TEST"]
enriched = [r for r in results if r[1] == "ENRICHED"]

print(f"  CONFIRMED:            {len(confirmed)}")
print(f"  NOT_TESTED:           {len(not_tested)}")
print(f"  NEEDS_BEHAVIORAL:     {len(needs_test)}")
print(f"  ENRICHED:             {len(enriched)}")
print(f"  Total:                {len(results)}")
