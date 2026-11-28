# Dossier — MD_ATTR_010 (STRUCTURAL)

**Claim (this audit tests):** $EA_INFORMATION (0xD0) + $EA (0xE0): Extended Attributes. Two-phase lookup: 0xD0 header (sizes/counts), then 0xE0 data body. NTFS-equivalent type codes. Schema 0x1d0 (v3.7+), 0x1e0 (v3.14+). Schema 0x1a0 = EA tree type.

**Canonical claim (reference_table.csv):** Metadata: $EA_INFORMATION (0xD0) + $EA (0xE0): Extended Attributes. Two-phase lookup: 0xD0 header (sizes/counts), then 0xE0 data body. NTFS-equivalent type codes. Schema 0x1d0 (v3.7+), 0x1e0 (v3.14+). Schema 0x1a0 = EA tree type.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Two-phase EA: 0xD0 ($EA_INFO header, 20B fixed) + 0xE0 ($EA body) both present as separate sub-records and ALWAYS co-occur per file (3875/3875 containers, 0 orphans). 0xD0 carries sizes at val[0x0C]/val[0x10]; 0xE0 carries a FILE_FULL_EA_INFORMATION chain at val[0x0C] (3875/3875 parse cleanly).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (win11+)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Disk-proven in MD_ATTR_RA_011/012/013. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_010.csv`
- corrected registry note: Schema 0x1a0 = Extended Attributes in both versions. WSL $LX* EAs found inline in 0x30 value data on disk images. Separate 0xD0/0xE0 attribute entries in per-file attribute set, not visible in directory B+ tree

## Proof links
- `proofs/validation/MD_ATTR_010.csv` (matrix) — 
