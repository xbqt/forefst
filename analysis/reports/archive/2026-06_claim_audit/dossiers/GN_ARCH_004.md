# Dossier — GN_ARCH_004 (BEHAVIORAL)

**Claim (this audit tests):** Metadata checksums: None (3.4), CRC64 (3.14 default), SHA256 (optional). User data checksums: opt-in via integrity streams

**Canonical claim (reference_table.csv):** General: Metadata checksums: None (3.4), CRC64 (3.14 default), SHA256 (optional). User data checksums: opt-in via integrity streams

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — VBR 0x2A selector 0=None/2=CRC64/4=SHA256, 4 on 4 SHA images

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Static driver evidence: CmsCrc32. Metadata checksums: None (3.4), CRC64 (3.14 default), SHA256 (optional). User data checksums: opt-in via integ. Proof is the decompiled function.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/GN_ARCH_004.csv`
- corrected registry note: VBR 0x2A selector: 0=None(3.4), 2=CRC64(3.14), 4=SHA256. Win10 CONFIRMED no metadata checksums (fsutil: CHECKSUM_TYPE_NONE, CHKP bit 0x400 not set). Upgraded 3.4→3.14 gains CRC64 at CHKP level despite VBR 0x2A remaining 0x00. See report_checksum_investigation.md

## Proof links
- `proofs/validation/GN_ARCH_004.csv` (matrix) — 
