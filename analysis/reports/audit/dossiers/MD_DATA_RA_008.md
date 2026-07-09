# Dossier — MD_DATA_RA_008 (BEHAVIORAL)

**Claim (this audit tests):** SI $DATA (0x80): 60-byte stream summary + inline content at val[0x3C]. file_size at val[0x20]. summary_size constant 0x30. stream_flags=2 (resident). Minimum 60B (empty file), max observed 320B.

**Canonical claim (reference_table.csv):** Metadata: SI $DATA (0x80): 60-byte stream summary + inline content at val[0x3C]. file_size at val[0x20]. summary_size constant 0x30. stream_flags=2 (resident). Minimum 60B (empty file), max observed 320B.

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — SI $DATA (marker 0x80000001) summary_size@0x0C == 0x30 on 367,347/367,347 v3.14 + 9/9 v3.15 = 100% on v3.14+. BUT on v3.4/v3.7/v3.9/v3.10 there are ZERO marker-0x80000001 SI $DATA records (3,169 v3.4 + 442 v3.7 + 1,402 v3.9 + 500 v3.10 resident files, all 0 SI). v3.4 resident $DATA uses a different encoding (summary@0x0C == 0x1a0, file_size in content area, value+0x58 still = file size).

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- E2/RD: the single-instance $DATA (marker 0x80000001) carries a 60-byte stream summary; 534 such 60-byte values observed. Detailed marker-filtered structure; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_008.csv`
- corrected registry note: All resident files across 110 images: content at val[0x3C], size at val[0x20]. 100% consistent. | RE-VERIFIED 2026-06-18 (all-disk): claimed version scope 'both 3.4;3.14;insider' and 'summary_size constant 0x30'; disk shows the 0x30-summary marker-0x80000001 SI $DATA is a v3.14+ structure ONLY. The byte layout (summary 0x30, content@0x3C, size@0x20) is CONFIRMED on v3.14

## Proof links
- `proofs/validation/MD_DATA_RA_008.csv` (matrix) — 
