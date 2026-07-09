# Dossier — FS_OTBL_RA_006 (BEHAVIORAL)

**Claim (this audit tests):** OID monotonic assignment: user OIDs start at 0x700 (hardcoded in MsSetMinimumNewObjectId) and increment sequentially via atomic GenerateIdentifier. OIDs are NEVER reused after deletion (DeleteIdentifier never decrements counter). Gaps = deleted objects. Confirmed on 66+ images and by static analysis across 3 driver versions (128 OID functions decompiled, see FS_OTBL_SA_001-010).

**Canonical claim (reference_table.csv):** File System: OID monotonic assignment: user OIDs start at 0x700 (hardcoded in MsSetMinimumNewObjectId) and increment sequentially via atomic GenerateIdentifier. OIDs are NEVER reused after deletion (DeleteIdentifier never decrements counter). Gaps = deleted objects. Confirmed on 66+ images and by static analysis across 3 driver versions (128 OID functions decompiled, see FS_OTBL_SA_001-010).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — User OID boundary measured on 113/113: OID 0x700 itself is NEVER present (0/113 — it is the reserved hardcoded minimum); the first allocated user OID is 0x701 on 112/113 images; the lone exception (winsider.raw, a heavily-worked Insider volume) has min user OID 0x75e (lower ones deleted), consistent with 'never reused; gaps=deletions'. All system OIDs are <0x700: {0x7,0x8,0x9,0xa,0xd,0x30,0x40(Insider only),0x500,0x501,0x520,0x530,0x540,0x541,0x600}. No system OID >= 0x700 anywhere.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 1/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/MsSetMinimumNewObjectId__decomp.txt
- Static driver evidence: MsSetMinimumNewObjectId. OID monotonic assignment: user OIDs start at 0x700 (hardcoded in MsSetMinimumNewObjectId) and increment sequen. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/FS_OTBL_RA_006.csv`
- corrected registry note: Static proof: GenerateIdentifier(SA_001) atomically increments counter; DeleteIdentifier(SA_009) never decrements; MsSetMinimumNewObjectId(SA_004) hardcodes 0x700 boundary

## Proof links
- `proofs/static/MsSetMinimumNewObjectId__decomp.txt` (static) — MsSetMinimumNewObjectId
- `proofs/validation/FS_OTBL_RA_006.csv` (matrix) — 
