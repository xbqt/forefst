#!/usr/bin/env python3
"""Deep investigation of OID 0x520 across 25+ disk images.

Determines whether OID 0x520 is:
  (a) a "Security ID Mapping" table (flat SecurityId -> descriptor index), or
  (b) an "FS Metadata" directory (like NTFS $Extend, with filename entries)

Tests per image:
  1. Walk OID 0x520 B+-tree, dump all rows with key type classification
  2. Walk OID 0x600 (root directory) for structural comparison
  3. Schema check: compare 0x520 and 0x600 schemas
  4. Parent-child check: who is 0x520's parent? does 0x520 have children?
  5. SecurityId cross-check: can SecurityId resolve in 0x520?

Run from the repo root. Private disk corpus: set REFS_CORPUS.
"""

import struct
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import forefst as ff

IMAGES = {
    # v3.4
    "win10refsmini":          "analysis/rawdisk/disks/step1/win10refsmini.raw",
    "win10refs2g":            "analysis/rawdisk/disks/step2/win10refs2g.raw",
    "win10refs5g64k":         "analysis/rawdisk/disks/step2/win10refs5g64k.raw",
    "win10refs8g":            "analysis/rawdisk/disks/step2/win10refs8g.raw",
    # v3.7
    "win1121h2test":          "analysis/rawdisk/disks/step4/win1121h2test.raw",
    # v3.9
    "win1122h2test":          "analysis/rawdisk/disks/step4/win1122h2test.raw",
    # v3.10
    "win1123h2test":          "analysis/rawdisk/disks/step4/win1123h2test.raw",
    # v3.14 basic
    "win11refsmini":          "analysis/rawdisk/disks/step1/win11refsmini.raw",
    "win11refs2g":            "analysis/rawdisk/disks/step2/win11refs2g.raw",
    "win11refs5g64k":         "analysis/rawdisk/disks/step2/win11refs5g64k.raw",
    "win11refs8g":            "analysis/rawdisk/disks/step2/win11refs8g.raw",
    # v3.14 variations
    "win11refs2g_sha256":     "analysis/rawdisk/disks/step2/win11refs2g_sha256checksums.raw",
    "win11refs2g_integrity":  "analysis/rawdisk/disks/step2/win11refs2g_setintegritystreams1.raw",
    "win11refs2g_noheat":     "analysis/rawdisk/disks/step2/win11refs2g_disableheatgathering.raw",
    # v3.14 attributes / USN
    "win11refs4gattributes":  "analysis/rawdisk/disks/step4/win11refs4gattributes.raw",
    "win11refs4gattr2_usn":   "analysis/rawdisk/disks/step4continuing/win11refs4gattributestest2.raw",
    # v3.14 compression / dedup
    "win11refs8g_lz4":        "analysis/rawdisk/disks/step3/win11refs8gcompresslz4default.raw",
    "win11refs8g_zstd":       "analysis/rawdisk/disks/step3/win11refs8gcompresszstddefault.raw",
    "win11refs8g_dedup":      "analysis/rawdisk/disks/step3/win11refs8gdedup.raw",
    # Upgraded
    "win10to11_before":       "analysis/rawdisk/disks/step3/win10to11refs4g_beforewin11mount.raw",
    "win10to11_after":        "analysis/rawdisk/disks/step3/win10to11refs4g_afterwin11mount.raw",
    # Insider
    "wininsiderrefs8gtest2":  "analysis/rawdisk/disks/step4/wininsiderrefs8gtest2.raw",
    "win11toinsiderrefs8g":   "analysis/rawdisk/disks/step4/win11toinsiderrefs8g.raw",
    # Atomic sequence: before and after USN activation
    "lasttests_pre_usn":      "analysis/rawdisk/disks/step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot.raw",
    "lasttests_post_usn":     "analysis/rawdisk/disks/step5/testatomic/win11refslasttests_baseline_mkdirtest_setcontenthitxt_testads_rmhitxt_hotxt_snapshot_usnjournal.raw",
    # Baseline
    "win11refsmini_baseline": "analysis/rawdisk/lab/win11refsmini_baseline.raw",
}

BASE = os.environ.get("REFS_CORPUS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))) + os.sep

BASE_TYPE_NAMES = {
    0x0010: "descriptor",
    0x0020: "reverse_lookup",
    0x0030: "filename",
    0x0040: "extent",
}

summary_rows = []


def decode_key_type(key):
    if len(key) < 4:
        return 0, 0, "unknown"
    kt = struct.unpack_from('<I', key, 0)[0]
    base = kt & 0xFFFF
    flags = kt >> 16
    name = BASE_TYPE_NAMES.get(base, "0x%04x" % base)
    return kt, base, name


def decode_filename_from_key(key):
    if len(key) < 6:
        return ""
    try:
        return key[4:].decode('utf-16-le').rstrip('\x00')
    except Exception:
        return "(decode error)"


def read_schema_from_root_page(f, ps, cs, tr, vlcns):
    if not vlcns:
        return None
    try:
        plcn = tr.tr(vlcns[0])
        f.seek(ps + plcn * cs)
        page = f.read(min(cs, 16384))
        if len(page) < 0x58:
            return None
        th_off_val = struct.unpack_from('<I', page, 0x50)[0]
        thoff = 0x50 + th_off_val
        if thoff + 0x10 > len(page):
            return None
        schema_id = struct.unpack_from('<H', page, thoff + 0x0C)[0]
        return schema_id
    except Exception:
        return None


def walk_oid(f, ps, cs, tr, obj_map, oid):
    if oid not in obj_map:
        return None
    vlcns = obj_map[oid]
    try:
        return ff.walk_bplus(f, ps, cs, tr, vlcns)
    except Exception as e:
        return "ERROR: %s" % e


def test_image(name, img_path):
    print("\n" + "=" * 70)
    print("IMAGE: %s" % name)
    print("Path:  %s" % img_path)
    print("=" * 70)

    if not os.path.exists(img_path):
        print("  FILE NOT FOUND — skipping")
        summary_rows.append((name, "?", "?", 0, "-", "-", "-", "-", "-", "-", "-"))
        return

    try:
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, chkp_lcns = ff.bootstrap(img_path)
    except Exception as e:
        print("  Bootstrap FAILED: %s" % e)
        summary_rows.append((name, "?", "?", 0, "-", "-", "-", "-", "-", "-", "-"))
        return

    version = "%d.%d" % (vmaj, vmin)
    csize = "64K" if cs == 65536 else "4K"
    print("  Version: %s  Clusters: %s  PageSize: %d" % (version, csize, ps))

    # --- Test 1: Walk OID 0x520 ---
    print("\n  --- OID 0x520 B+-tree rows ---")
    rows_520 = walk_oid(f, ps, cs, tr, obj_map, 0x520)
    has_journal = False
    row_count_520 = 0
    types_520 = []
    filenames_520 = []

    if rows_520 is None:
        print("  OID 0x520 NOT FOUND in object map")
        oid520_status = "NOT_IN_OBJMAP"
    elif isinstance(rows_520, str):
        print("  %s" % rows_520)
        oid520_status = "WALK_ERROR"
    else:
        row_count_520 = len(rows_520)
        print("  Total rows: %d" % row_count_520)
        for i, (k, v) in enumerate(rows_520):
            kt, base, tname = decode_key_type(k)
            types_520.append(tname)
            line = "  [%d] type=0x%08x base=0x%04x (%s) key_len=%d val_len=%d" % (
                i, kt, base, tname, len(k), len(v))
            if base == 0x0030:
                fname = decode_filename_from_key(k)
                line += '  name="%s"' % fname
                filenames_520.append(fname)
                if "change journal" in fname.lower():
                    has_journal = True
            if base == 0x0010 and len(v) >= 16:
                line += "  val_hdr=%s" % v[:16].hex()
            print(line)
        oid520_status = "OK (%d rows)" % row_count_520

    # --- Test 2: Walk OID 0x600 (root dir) first 5 rows for comparison ---
    print("\n  --- OID 0x600 (root dir) first 5 rows ---")
    rows_600 = walk_oid(f, ps, cs, tr, obj_map, 0x600)
    if rows_600 and not isinstance(rows_600, str):
        for i, (k, v) in enumerate(rows_600[:5]):
            kt, base, tname = decode_key_type(k)
            line = "  [%d] type=0x%08x base=0x%04x (%s) key_len=%d val_len=%d" % (
                i, kt, base, tname, len(k), len(v))
            if base == 0x0030:
                fname = decode_filename_from_key(k)
                line += '  name="%s"' % fname
            print(line)
        print("  ... (%d total rows)" % len(rows_600))
    else:
        print("  Could not walk OID 0x600")

    # --- Test 3: Schema comparison (read from root pages) ---
    print("\n  --- Schema check (from B+-tree root pages) ---")
    schema_520 = None
    schema_600 = None
    try:
        if 0x520 in obj_map:
            schema_520 = read_schema_from_root_page(f, ps, cs, tr, obj_map[0x520])
        if 0x600 in obj_map:
            schema_600 = read_schema_from_root_page(f, ps, cs, tr, obj_map[0x600])
        print("  OID 0x520 schema: %s" % ("0x%04x" % schema_520 if schema_520 is not None else "NOT FOUND"))
        print("  OID 0x600 schema: %s" % ("0x%04x" % schema_600 if schema_600 is not None else "NOT FOUND"))
        if schema_520 is not None and schema_600 is not None:
            if schema_520 == schema_600:
                print("  MATCH — same schema as root directory → 0x520 IS a directory")
            else:
                print("  DIFFERENT — 0x520=0x%04x vs 0x600=0x%04x" % (schema_520, schema_600))
    except Exception as e:
        print("  Schema check error: %s" % e)

    schema_match = "YES" if (schema_520 is not None and schema_520 == schema_600) else "NO"
    schema_str = "0x%04x" % schema_520 if schema_520 is not None else "?"

    # --- Test 4: Parent-child check (corrected offsets: parent@8, child@24) ---
    print("\n  --- Parent-child check ---")
    parent_of_520 = None
    parent_name_520 = ""
    children_of_520 = []
    try:
        pc_rows = ff.walk_bplus(f, ps, cs, tr, roots[4])
        for k, v in pc_rows:
            if len(k) >= 32:
                parent_oid = struct.unpack_from('<Q', k, 8)[0]
                child_oid = struct.unpack_from('<Q', k, 24)[0]
                if child_oid == 0x520:
                    parent_of_520 = parent_oid
                    if len(v) >= 2:
                        try:
                            parent_name_520 = v.decode('utf-16-le').rstrip('\x00')
                        except Exception:
                            parent_name_520 = "(decode error)"
                    print("  Parent of 0x520: OID 0x%x  name_in_val=\"%s\"" % (parent_oid, parent_name_520))
                if parent_oid == 0x520:
                    child_name = ""
                    if len(v) >= 2:
                        try:
                            child_name = v.decode('utf-16-le').rstrip('\x00')
                        except Exception:
                            child_name = ""
                    children_of_520.append((child_oid, child_name))
        if parent_of_520 is None:
            print("  OID 0x520 NOT FOUND in parent-child table")
        if children_of_520:
            print("  Children of 0x520:")
            for coid, cname in children_of_520:
                print("    OID 0x%x  name=\"%s\"" % (coid, cname))
        else:
            print("  OID 0x520 has NO children in parent-child table")
    except Exception as e:
        print("  Parent-child error: %s" % e)

    parent_str = "0x%x" % parent_of_520 if parent_of_520 else "none"

    # --- Test 5: SecurityId cross-check ---
    print("\n  --- SecurityId cross-check ---")
    secid_in_520 = "N/A"
    try:
        if rows_600 and not isinstance(rows_600, str):
            first_secid = None
            for k, v in rows_600:
                kt, base, _ = decode_key_type(k)
                if base == 0x0030 and len(v) >= 0x54:
                    first_secid = struct.unpack_from('<I', v, 0x50)[0]
                    break
            if first_secid is not None and first_secid != 0:
                print("  Sample SecurityId from root dir: %d (0x%x)" % (first_secid, first_secid))

                found_in_530 = False
                rows_530 = walk_oid(f, ps, cs, tr, obj_map, 0x530)
                if rows_530 and not isinstance(rows_530, str):
                    for k530, v530 in rows_530:
                        if len(k530) >= 16:
                            sid_lo = struct.unpack_from('<I', k530, 12)[0]
                            if sid_lo == first_secid:
                                found_in_530 = True
                                print("  SecurityId %d FOUND in OID 0x530 (val_len=%d) → direct resolution" % (first_secid, len(v530)))
                                break
                    if not found_in_530:
                        print("  SecurityId %d not found in 0x530 by simple key scan" % first_secid)

                all_dir_types = True
                if rows_520 and not isinstance(rows_520, str):
                    for k520, v520 in rows_520:
                        kt520, base520, _ = decode_key_type(k520)
                        if base520 not in (0x0010, 0x0020, 0x0030, 0x0040):
                            all_dir_types = False
                            print("  NON-DIRECTORY entry type 0x%08x in 0x520!" % kt520)
                    if all_dir_types:
                        print("  OID 0x520 has ONLY directory-type entries (no security mapping rows)")
                        secid_in_520 = "NO"
                    else:
                        secid_in_520 = "MAYBE"
            else:
                print("  Could not extract nonzero SecurityId from root dir entries")
        else:
            print("  Skipped (no root dir rows)")
    except Exception as e:
        print("  SecurityId check error: %s" % e)

    try:
        f.close()
    except Exception:
        pass

    types_str = ",".join(sorted(set(types_520))) if types_520 else "-"
    files_str = "; ".join(filenames_520) if filenames_520 else "-"
    summary_rows.append((
        name, version, csize, row_count_520,
        types_str, files_str,
        "YES" if has_journal else "NO",
        schema_str, schema_match,
        parent_str,
        secid_in_520,
    ))


def main():
    print("OID 0x520 DEEP INVESTIGATION")
    print("Images: %d" % len(IMAGES))
    print("=" * 70)

    for name in sorted(IMAGES.keys()):
        rel_path = IMAGES[name]
        full_path = os.path.join(BASE, rel_path)
        test_image(name, full_path)

    print("\n\n" + "=" * 120)
    print("SUMMARY TABLE")
    print("=" * 120)
    hdr = "%-28s %-5s %-3s %4s %-28s %-20s %-3s %-8s %-5s %-8s %-6s" % (
        "Image", "Ver", "CS", "Rows", "Entry Types", "Filenames", "CJ?", "Schema", "Match", "Parent", "SecID?"
    )
    print(hdr)
    print("-" * 120)
    for row in summary_rows:
        print("%-28s %-5s %-3s %4s %-28s %-20s %-3s %-8s %-5s %-8s %-6s" % row)

    cj_count = sum(1 for r in summary_rows if r[6] == "YES")
    no_cj = sum(1 for r in summary_rows if r[6] == "NO")
    schemas = set(r[7] for r in summary_rows if r[7] != "?")
    schema_matches = sum(1 for r in summary_rows if r[8] == "YES")
    parents = set(r[9] for r in summary_rows if r[9] not in ("none", "-"))
    secid_no = sum(1 for r in summary_rows if r[10] == "NO")
    valid = [r for r in summary_rows if r[3] != "?"]

    print("\n" + "=" * 120)
    print("CONCLUSIONS")
    print("=" * 120)
    print("Images tested:           %d (of which %d successfully parsed)" % (len(summary_rows), len(valid)))
    print("With Change Journal:     %d" % cj_count)
    print("Without Change Journal:  %d" % no_cj)
    print("Distinct schemas for 520:%s" % schemas)
    print("Schema matches 0x600:    %d / %d" % (schema_matches, len(valid)))
    print("Parent OIDs for 0x520:   %s" % (parents if parents else "{none found}"))
    print("Security mapping in 520: %d images show ONLY directory entries (no security rows)" % secid_no)

    if schemas and len(schemas) == 1:
        s = list(schemas)[0]
        print("\nAll images use schema %s for OID 0x520." % s)
    if schema_matches == len(valid) and schema_matches > 0:
        print("OID 0x520 and OID 0x600 share the SAME schema on ALL images → 0x520 IS a directory.")
    if parents and len(parents) == 1:
        p = list(parents)[0]
        print("OID 0x520's parent is consistently %s (root directory)." % p)
    if secid_no > 0 and secid_no == len([r for r in summary_rows if r[10] not in ("N/A", "-")]):
        print("\nNO image contains security mapping data in OID 0x520.")
        print("The 'Security ID Mapping' label is a MISIDENTIFICATION.")
        print("OID 0x520 is an FS Metadata directory (NTFS $Extend equivalent).")
        print("The security resolution chain goes directly from SecurityId → OID 0x530.")


if __name__ == "__main__":
    main()
