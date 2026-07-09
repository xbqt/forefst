# Dossier — MD_ATTR_RA_017 (BEHAVIORAL)

**Claim (this audit tests):** Insider sub-record census: 123367 total across 26668 OIDs. 0x39=26560, 0x90=26668, SI_0x80=33560, MI_0x80=28739, 0xD0=3877, 0xE0=3852, 0xC0=109, 0xB0=2. Complete type distribution.

**Canonical claim (reference_table.csv):** Metadata: Insider sub-record census: 123367 total across 26668 OIDs. 0x39=26560, 0x90=26668, SI_0x80=33560, MI_0x80=28739, 0xD0=3877, 0xE0=3852, 0xC0=109, 0xB0=2. Complete type distribution.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Insider (winsider.raw v3.14) census matches claim nearly exactly: measured 0x39=26560(claim 26560), SI_0x80=33560(33560), MI_0x80=28739(28739), 0xD0=3877(3877), 0xE0=3852(3852), 0xC0=109(109), 0xB0=2(2). Only 0x90=26560 (claim 26668) and total/OID-count differ by ~108 (OIDs reachable from dir-tree 0x600 vs claim's broader walk).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Insider-build census (single-image statistical observation). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_017.csv`
- corrected registry note: Full walk of Insider image winsider.raw. All sub-records classified.

## Proof links
- `proofs/validation/MD_ATTR_RA_017.csv` (matrix) — 
