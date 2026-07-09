# Dossier — FS_OTBL_005 (BEHAVIORAL)

**Claim (this audit tests):** File System Metadata ID = 0x520 (like NTFS $Extend)

**Canonical claim (reference_table.csv):** File System: File System Metadata ID = 0x520 (like NTFS $Extend)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — OID 0x520 present in Object Table on 113/113 images and is directory-structured (on v3.4 win10refsmini its own tree holds type-0x30 children 'Reparse Index','Security Descriptor Stream','Volume Direct IO File'; on fresh v3.14 it is degenerate/empty per F.4c). FS-metadata role confirmed.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Object Table] File System Metadata ID = 0x520 (like NTFS $Extend) — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_OTBL_005.csv`
- corrected registry note: OID 0x520 = File System Metadata present in all images

## Proof links
- `proofs/validation/FS_OTBL_005.csv` (matrix) — 
