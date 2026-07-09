# Dossier — MD_ATTR_RA_004 (PURE-RD-LAYOUT)

**Claim (this audit tests):** WSL FIFOs stored as REPARSE_POINT with $LXMOD upper bits encoding file type (FIFO = S_IFIFO 0o010000; observed $LXMOD 0o10644)

**Canonical claim (reference_table.csv):** Metadata: WSL FIFOs stored as REPARSE_POINT with $LXMOD upper bits encoding file type (FIFO = S_IFIFO 0o010000; observed $LXMOD 0o10644)

**Re-verification verdict (all-disk, 2026-06-18):** **UNCONFIRMABLE** — WSL device/FIFO EAs present on disk ($LXDEV=2, $LXMOD/$LXUID/$LXGID=23 each) and LX reparse tags observed (LX_FIFO=0x80000024 x3, AF_UNIX=0x80000023 x1, LX_CHR=0x80000025 x1, LX_BLK=0x80000026 x1). But the specific 'FIFO mode bits 0o010000 inside $LXMOD' is a value-interpretation not isolable to a single corpus file via this harness.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- WSL reparse encoding; reparse tags disk-proven (MD_SI_RA_001). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_004.csv`
- corrected registry note: Confirmed on win11refs4gattributes.raw. FIFO type encoded in mode bits within $LXMOD EA value

## Proof links
- `proofs/validation/MD_ATTR_RA_004.csv` (matrix) — 
