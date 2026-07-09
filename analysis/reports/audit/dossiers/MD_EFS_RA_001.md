# Dossier — MD_EFS_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** EFS encryption lifecycle: EFS0.LOG created in system metadata directory (OID 0x701). Encryption change reason code 0x00040000 in USN.

**Canonical claim (reference_table.csv):** Metadata: EFS encryption lifecycle: EFS0.LOG created in system metadata directory (OID 0x701). Encryption change reason code 0x00040000 in USN.

**Re-verification verdict (all-disk, 2026-06-18):** **NEEDS-STATIC** — EFS metadata exists on disk ($EFS 0x100 sub-record, see EFS_RA_005). But 'EFS0.LOG in OID 0x701' and 'USN change-reason 0x00040000' are event/log-sequence claims, not static byte-layout: would require parsing the USN journal stream and the system-metadata directory listing on the encrypted-lifecycle images. Evidence level N/A.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (EFS lifecycle). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_EFS_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 6.1

## Proof links
- `proofs/validation/MD_EFS_RA_001.csv` (matrix) — 
