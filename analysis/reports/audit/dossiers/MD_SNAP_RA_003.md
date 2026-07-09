# Dossier — MD_SNAP_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Non-resident snapshot extents use same VLCN format as type 0x40 data runs. Standard extent resolution applies to snapshot data recovery.

**Canonical claim (reference_table.csv):** Metadata: Non-resident snapshot extents use same VLCN format as type 0x40 data runs. Standard extent resolution applies to snapshot data recovery.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — CONFIRMED 2026-06-18 (overturns prior UNCONFIRMABLE): non-resident snapshot DATA uses the type-0x40 24-byte VLCN extent format. 29/30 true snapshots non-resident across 8 images; content byte-exact recovered (arg.txt/test2='arg ument 1'; 3.2MB versionmodified across 8 extents). Static: snapshot path reuses CmsStream::LookupAllocation (the type-0x40 extent routine). The prior re-verify conflated the 116-byte 0xB0-record residency with the linked 0x80-DATA residency.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Snapshot extents reuse 0x40 format (disk-proven MD_DATA_RA_004). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SNAP_RA_003.csv`
- corrected registry note: CONFIRMED ALL-DISK 2026-06-18: 29 of 30 true snapshots are NON-RESIDENT across 8 images; content byte-exact recovered (arg.txt/test2='arg ument 1', 1 extent; xbpt_beta_sierra_570651.json/versionmodified=3,202,036 B across 8 extents, header GFSAREPLAY). Extent format identical to type-0x40 (C.4). The prior UNCONFIRMABLE re-verify conflated the 116-byte 0xB0-record residency with the linked 0x80-DATA-record residency. See structure_reference C.6.

## Proof links
- `proofs/validation/MD_SNAP_RA_003.csv` (matrix) — 
