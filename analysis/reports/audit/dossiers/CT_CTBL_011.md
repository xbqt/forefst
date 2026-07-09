# Dossier — CT_CTBL_011 (LITERATURE)

**Claim (this audit tests):** 0xA8-0xAC: CPC clusters per container (Lee)

**Canonical claim (reference_table.csv):** Content: 0xA8-0xAC: CPC clusters per container (Lee)

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — value+0xA8 (u32) == 0 on 278873/278873 224-byte rows (CPC@0xA8 never matches the real CPC 16384/1024). CPC is at value+0x18 (and trailing copy at 0x98/0xD8). 0xA8 is out of bounds for 160B rows.

**Original audit verdict:** CONTRADICTED (disk held 0/1 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- LITERATURE (Lee). NOTE: the audit places CPC at value+0x18 (CT_CTBL_002/RA_006); the Lee 0xA8 label is likely incorrect (cf. the 0xA0 CSC mislabel, #338). Cited with correction.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/CT_CTBL_011.csv`
- corrected registry note: CPC is at offset 0x18 universally (not 0xA8 as Lee claims). Confirmed across all 39 images including 64K clusters and SHA256. Merged from CT_CTBL_RA_001 | RE-VERIFIED 2026-06-18 (all-disk): value+0xA8 (u32) == 0 on 278873/278873 224-byte rows (CPC@0xA8 never matches the real CPC 16384/1024). CPC is at value+0x18 (and trailing copy at 0x98/0xD8). 0xA8 is out of bounds for 160B rows.

## Proof links
- `proofs/validation/CT_CTBL_011.csv` (matrix) — 
