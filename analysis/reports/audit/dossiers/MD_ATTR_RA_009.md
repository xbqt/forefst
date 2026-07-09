# Dossier — MD_ATTR_RA_009 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Common sub-record VALUE header: 12-byte prefix [4B padding=0][4B data_area_size][4B constant=0x0C]. Shared by all embedded attribute types (0x80 SI, 0xB0, 0xC0, 0xD0, 0xE0). Invariant across v3.4-Insider.

**Canonical claim (reference_table.csv):** Metadata: Common sub-record VALUE header: 12-byte prefix [4B padding=0][4B data_area_size][4B constant=0x0C]. Shared by all embedded attribute types (0x80 SI, 0xB0, 0xC0, 0xD0, 0xE0). Invariant across v3.4-Insider.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — The genuine 12-byte-header invariant is const@offset8 == 0x0C: holds 378222/378222 (100%) across SI_0x80(367356), 0xB0(985), 0xC0(2099), 0xD0(3900), 0xE0(3875), 0x100(7). The 'padding=0' (offset 0) part holds 100% for 0x80/0xC0/0xD0/0xE0/0x100 but NOT for 30 of 985 0xB0 ADS records, which carry stream flags 0x1c000000 in the first 4 bytes. The offset-4 'data_area_size' does NOT equal summary@0x0C in general.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 48/48 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Embedded sub-records of 0xC0/0xD0/0xE0/0x100 begin their value with a 12-byte common header whose first 4 bytes are 0 (data-area offset follows). Byte-verified 100% on the attributes image. N/A where the features are absent.

## Raw-disk proof
- probe `subrec` ; validation matrix: `proofs/validation/MD_ATTR_RA_009.csv`
- corrected registry note: All sub-record values across 110 images share this prefix. 0 violations.

## Proof links
- `proofs/validation/MD_ATTR_RA_009.csv` (matrix) — 
