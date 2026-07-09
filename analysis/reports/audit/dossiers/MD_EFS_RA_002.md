# Dossier — MD_EFS_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Encrypt-decrypt-encrypt cycle fully tracked via USN; each operation generates new EFS0.LOG entry with new OID entry index.

**Canonical claim (reference_table.csv):** Metadata: Encrypt-decrypt-encrypt cycle fully tracked via USN; each operation generates new EFS0.LOG entry with new OID entry index.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — Encrypt-decrypt-encrypt USN tracking is an event-sequence claim across multiple lifecycle images; not a static on-disk byte layout. Requires USN-journal record decode comparing successive lifecycle images. Evidence level N/A.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (EFS via USN). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_EFS_RA_002.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 6.2

## Proof links
- `proofs/validation/MD_EFS_RA_002.csv` (matrix) — 
