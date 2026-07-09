# Dossier — MD_DATA_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** RETRACTED 2026-06-18: the "single-extent inline shortcut (0x80000002 marker + VLCN@0x04 + cluster_count@0x08)" is NOT a real structure — it is a misread of the $DATA sub-record header (marker 0x80000002 + descriptor 0x000E0080). Single-extent files use the standard 24-byte extent entry (MD_DATA_RA_001).

**Canonical claim (reference_table.csv):** Metadata: RETRACTED 2026-06-18: the "single-extent inline shortcut (0x80000002 marker + VLCN@0x04 + cluster_count@0x08)" is NOT a real structure — it is a misread of the $DATA sub-record header (marker 0x80000002 + descriptor 0x000E0080). Single-extent files use the standard 24-byte extent entry (MD_DATA_RA_001).

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — 16-byte single-extent shortcut is a phantom (24-byte stride 31523/0)

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Inline single-extent encoding. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_002.csv`
- corrected registry note: Phantom: 31,523 files resolve via the 24-byte stride / 0 via any 16-byte form / 400/400 content matches; the 1 "hit" had "VLCN"=0xE0080 = the descriptor 0x000E0080.

## Proof links
- `proofs/validation/MD_DATA_RA_002.csv` (matrix) — 
