# Dossier — FN_DTBL_004 (STRUCTURAL)

**Claim (this audit tests):** Directory Link row: type 0x00020030 + dirname

**Canonical claim (reference_table.csv):** File Name: Directory Link row: type 0x00020030 + dirname

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Directory-link rows are type-0x30 entries (key 0x0030 + key_flags); the '0x00020030' = key_flags 0x02 (non-resident/dir) + type 0x30. dirname decodes as UTF-16LE.

**Original audit verdict:** INFERRED (disk held 112/112 at audit time) · **Registry status:** INFERRED · **Evidence:** E1

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- 0x30 keys with key_flags=0x0002 are directory-link rows. Byte-verified present.

## Raw-disk proof
- probe `dirkey` ; validation matrix: `proofs/validation/FN_DTBL_004.csv`
- corrected registry note: Directory names extracted from B+-tree walking in refs_dirfiles.py | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): E1 (string $DIR_LINK). On disk these are indistinguishable from other kf=0x02 type-0x30 entries except by the directory attribute bit (FN_DTBL_005). Semantic 'Directory Link' label is literature; byte layout confirmed.

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/FN_DTBL_004.csv` (matrix) — 
