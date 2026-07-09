# Dossier — MD_INTG_RA_001 (STRUCTURAL)

**Claim (this audit tests):** Integrity-stream marker on a file = file_attrs bit 0x8000 (FILE_ATTRIBUTE_INTEGRITY_STREAM) ONLY. $SI+0x24 internal_flags has NO integrity-specific bit: its bit0 (0x01) = FCB+0x08 bit 27, a delete-disposition/EFS transient-state flag (set in DeleteDirectoryOnDisk), NOT integrity. Corrects the prior 'bit0=INTEGRITY(FCB bit 27)' label (E-integrity-bit / supersedes the gloss in MD_SI_RA_006).

**Canonical claim (reference_table.csv):** Metadata: Integrity-stream marker on a file = file_attrs bit 0x8000 (FILE_ATTRIBUTE_INTEGRITY_STREAM) ONLY. $SI+0x24 internal_flags has NO integrity-specific bit: its bit0 (0x01) = FCB+0x08 bit 27, a delete-disposition/EFS transient-state flag (set in DeleteDirectoryOnDisk), NOT integrity. Corrects the prior 'bit0=INTEGRITY(FCB bit 27)' label (E-integrity-bit / supersedes the gloss in MD_SI_RA_006).

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CONFIRMED**

**Original audit verdict:** STATIC-CONFIRMED (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsSetIntegrity__decomp.txt
- E2+RD. Static (win11_4b0558f6 + insider): RefsSetIntegrity @1402840a8 toggles SCB+0x98 bit 0x8000 (-> $SI+0x20); RefsComputeStandardInformationInternalFromFcb builds $SI+0x24 from FCB+0x08 bits only (bit0<-bit27), never SCB+0x98; FCB bit27 set in DeleteDirectoryOnDisk. RD: 4 v3.14 integrity images, file_attrs 0x8000 = 100% of integrity files; setintegritystreams1 has 5953 integrity files, 0 with $SI+0x24 bit0 set. Corrects the MD_SI_RA_006 bit0 label (E43). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_INTG_RA_001.csv`
- corrected registry note: 4 v3.14 integrity images: file_attrs 0x8000 = 100% correlation with Get-FileIntegrity Enabled; win11refs2g_setintegritystreams1 has 5953 integrity files, 0 with $SI+0x24 bit0 set. integritytest.txt: attrs 0x00008020 (0x8000 set), internal_flags 0x08 (bit0 clear).

## Proof links
- `proofs/static/RefsSetIntegrity__decomp.txt` (static) — RefsSetIntegrity
- `proofs/validation/MD_INTG_RA_001.csv` (matrix) — 
