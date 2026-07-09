# Dossier — GN_IDXR_002 (BEHAVIORAL)

**Claim (this audit tests):** Root 0x0C-0x0E: schema of table

**Canonical claim (reference_table.csv):** General: Root 0x0C-0x0E: schema of table

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CONFIRMED 2026-06-19 (was INFERRED, wrong frame): _SmsIndexRoot descriptor+0x0C (page+0x50+0x0C) = table schema id (0xe0c0/0xe030/0x130...) on 34203/34207 tables; static CreateIndex win10 @73106 from RegisterSchema. The INFERRED 'not a schema' read the per-node header thoff+0x0C (node-type). Prade correct.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Index Root] Root 0x0C-0x0E: schema of table — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/GN_IDXR_002.csv`
- corrected registry note: CONFIRMED ALL-DISK 2026-06-19: desc+0x0C (page+0x50+0x0C) is a valid schema id (0xe0c0 CT, 0xe030 OT, 0x130 dir, ...) on 34,203/34,207 tables. PRADE CORRECT. The audit-2 INFERRED 'not a schema' read the per-node header thoff+0x0C (node-type) - the wrong structure. See structure_reference A.2b. Was INFERRED.

## Proof links
- `proofs/validation/GN_IDXR_002.csv` (matrix) — 
