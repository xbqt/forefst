# Dossier — MD_ATTR_001 (STRUCTURAL)

**Claim (this audit tests):** $STANDARD_INFORMATION: present, role moved to fixed metadata

**Canonical claim (reference_table.csv):** Metadata: $STANDARD_INFORMATION: present, role moved to fixed metadata

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — $STANDARD_INFORMATION present as the type-0x10 own-row value across 32605 user OIDs on all 107 ReFS images (the $SI body lives at value+0x28..+0xA3). Semantic 'role moved to fixed metadata' is an E2/static label, not a byte-decidable on-disk fact.

**Original audit verdict:** INFERRED (disk held 112/112 at audit time) · **Registry status:** INFERRED · **Evidence:** E2 (win10)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/build_object_map__forefst.txt
- Type 0x10 = $SI own-row. Verified present on every user object's B+-tree.

## Raw-disk proof
- probe `attr_types` ; validation matrix: `proofs/validation/MD_ATTR_001.csv`
- corrected registry note: Individual attribute extraction not yet implemented | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was NOT_TESTED): Offset/presence disk-confirmed; the prose label is static-cited (E2 win10). No contradiction.

## Proof links
- `proofs/static/build_object_map__forefst.txt` (static) — build_object_map
- `proofs/validation/MD_ATTR_001.csv` (matrix) — 
