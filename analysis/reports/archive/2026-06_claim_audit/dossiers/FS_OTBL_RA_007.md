# Dossier — FS_OTBL_RA_007 (BEHAVIORAL)

**Claim (this audit tests):** OID chronology analysis: 400 objects in range 0x700-0x8F9 on test image (76.6% density). 128-bit File IDs encode table OID (upper 8B) + sequential entry index (lower 8B). Generation counter at Object Table value offset 0x18 = checkpoint virtual clock at creation/last update. ReFS provides stronger chronological guarantees than NTFS (no record reuse)

**Canonical claim (reference_table.csv):** File System: OID chronology analysis: 400 objects in range 0x700-0x8F9 on test image (76.6% density). 128-bit File IDs encode table OID (upper 8B) + sequential entry index (lower 8B). Generation counter at Object Table value offset 0x18 = checkpoint virtual clock at creation/last update. ReFS provides stronger chronological guarantees than NTFS (no record reuse)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID density over the user range (>=0x700) across 113 images: min 0.311, median 0.813, max 1.000 (fresh volumes 100%, worked volumes lower). The specific cited test image reproduced EXACTLY: win11refs4gattributestest2 has 387 user objects, density 0.7663 (=76.6%), OID span 0x700-0x8F9 — matching the claim's '400 objects 0x700-0x8F9, 76.6% density'. Lower OID = earlier creation, gaps = deletions (confirmed via winsider min=0x75e).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Observational (OID allocation): user OIDs start 0x701 and increase monotonically (oid_allocation_mechanism). Cross-image observation, not a single-field probe.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_OTBL_RA_007.csv`
- corrected registry note: See ra_step4_20_refs_chronology_analysis.md

## Proof links
- `proofs/validation/FS_OTBL_RA_007.csv` (matrix) — 
