# Dossier — FS_OTBL_SA_009 (BEHAVIORAL)

**Claim (this audit tests):** CmsObjectTable::DeleteIdentifier: removes OID from Object Table B+-tree. DOES NOT decrement counter — guarantees OIDs are never reused after deletion. 30 bytes (Insider, thin wrapper around DeleteRow).

**Canonical claim (reference_table.csv):** File System: CmsObjectTable::DeleteIdentifier: removes OID from Object Table B+-tree. DOES NOT decrement counter — guarantees OIDs are never reused after deletion. 30 bytes (Insider, thin wrapper around DeleteRow).

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — No direct on-disk byte for 'DeleteIdentifier does not decrement counter'. Disk corroboration: winsider.raw shows min user OID 0x75e with no 0x701-0x75d (deleted, never reappear) and OID gaps throughout (density <1.0), consistent with 'OIDs never reused after deletion'. The 'counter not decremented' claim is the static E2 mechanism.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsObjectTable::DeleteIdentifier. CmsObjectTable::DeleteIdentifier: removes OID from Object Table B+-tree. DOES NOT decrement counter — guarante. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_SA_009.csv`
- corrected registry note: See ObjectIdLifecycle.md | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): The observable consequence (no OID reuse, gaps=deletions) is CONFIRMED-ALLDISK via RA_006/RA_007; the function-internal 'no decrement' assertion is INFERRED from those plus E2 static.

## Proof links
- `proofs/validation/FS_OTBL_SA_009.csv` (matrix) — 
