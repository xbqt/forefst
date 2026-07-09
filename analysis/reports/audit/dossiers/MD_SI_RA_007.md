# Dossier — MD_SI_RA_007 (BEHAVIORAL)

**Claim (this audit tests):** ExternalFileId_2/3 populated ONLY for cross-volume operations. RefsConvertToStandardInfoExternalId compares source volume with current; zeros if same. ExtFid3=source parent OID (0x700+ range).

**Canonical claim (reference_table.csv):** Metadata: ExternalFileId_2/3 populated ONLY for cross-volume operations. RefsConvertToStandardInfoExternalId compares source volume with current; zeros if same. ExtFid3=source parent OID (0x700+ range).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — ExternalFileId_2 ($SI+0x60) = 0 on 32629/32629 own-rows across ALL 113 images (incl v3.4 and upgraded win10to11); ExternalFileId_3 ($SI+0x68) also 0/32629. No cross-volume-copy file exists in the corpus.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsConvertToStandardInfoExternalId__decomp.txt
- RefsConvertToStandardInfoExternalId writes $SI+0x60/0x68 only when source volume != destination (finding #336). Proof is the decompiled function; RD-corroborated on upgrade images.

## Raw-disk proof
- probe `static_dossier` ; validation matrix: `proofs/validation/MD_SI_RA_007.csv`
- corrected registry note: 603/525165 non-zero ExtFid_2 entries. All on v3.4 images or upgraded. Zero on all native v3.14.

## Proof links
- `proofs/static/RefsConvertToStandardInfoExternalId__decomp.txt` (static) — RefsConvertToStandardInfoExternalId
- `proofs/validation/MD_SI_RA_007.csv` (matrix) — 
