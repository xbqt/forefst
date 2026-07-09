# Dossier — MD_ATTR_008 (ABSENCE)

**Claim (this audit tests):** $REPARSE_POINT: reparse metadata for symlinks/junctions. Type code 0xC0 (NTFS-equivalent). Stored as separate attribute in per-file B+ tree, not inline in 0x30 directory entry. Schema 0x1c0 (v3.7+), schema 0x170 = Reparse Point tree type.

**Canonical claim (reference_table.csv):** Metadata: $REPARSE_POINT: reparse metadata for symlinks/junctions. Type code 0xC0 (NTFS-equivalent). Stored as separate attribute in per-file B+ tree, not inline in 0x30 directory entry. Schema 0x1c0 (v3.7+), schema 0x170 = Reparse Point tree type.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Reparse data stored as a separate 0xC0 sub-record (NOT inline in the 0x30 dir entry): 2099 occurrences of type 0xC0 across the corpus, each a REPARSE_DATA_BUFFER at val[0x0C]. The type code on disk is 0xC0 (not NTFS's 0xC0... matches). Reparse FLAG 0x400 appears in dirent value+0x40 (e.g. 0x420, 2047 files).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- 0xC0 reparse disk-proven in MD_ATTR_RA_010 (marker 0x80000001). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_008.csv`
- corrected registry note: REPARSE_POINT flag (0x400) on symlink files. Schema 0x170 = Reparse Point. No 0xC0 entries visible in directory B+ trees (data in per-file attribute set)

## Proof links
- `proofs/validation/MD_ATTR_008.csv` (matrix) — 
