# Dossier — MD_LK_RA_008 (STRUCTURAL)

**Claim (this audit tests):** v3.4 $OBJ_LINK (type 0x38): uses 12B common header. Parent OID at val[0x14], 4 timestamps at val[0x1C-0x3C], file_attrs at val[0x3C], filename at val[0x5E]. Verified on win10refsmini (6 entries).

**Canonical claim (reference_table.csv):** Metadata: v3.4 $OBJ_LINK (type 0x38): uses 12B common header. Parent OID at val[0x14], 4 timestamps at val[0x1C-0x3C], file_attrs at val[0x3C], filename at val[0x5E]. Verified on win10refsmini (6 entries).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — v3.4 0x38 value layout: 12-byte common header signature (bytes 8-11 == 0c 00 01 00) on 528/538 entries; parent_oid@0x14 resolves to a real OID 538/538; filename@0x5E decodes UTF-16LE 538/538; 4 FILETIMEs@0x1C present (sane) on 498/538. The 40 timestamp misses and 10 header misses are all system objects (root 0x600, SVI, File System Metadata) with zeroed timestamps/variant headers, not real misses.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ObjLink v3.4 structure. Feature-gated; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_008.csv`
- corrected registry note: 6 entries decoded. Parent OIDs and filenames match directory tree.

## Proof links
- `proofs/validation/MD_LK_RA_008.csv` (matrix) — 
