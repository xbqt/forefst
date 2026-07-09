# Dossier — CT_CTBL_010 (PURE-RD-LAYOUT)

**Claim (this audit tests):** 0xA0-0xA7: CSC starting position (Lee)

**Canonical claim (reference_table.csv):** Content: 0xA0-0xA7: CSC starting position (Lee)

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — value+0xA0 is OUT OF BOUNDS for 160B (4K) rows (last offset 0x9F). For 224B rows, value[0xA0:0xA8]=zeros. The actual CSC (Container Start Cluster) is at value[len-16]=0x90(160B)/0xD0(224B), NOT 0xA0. The CT-root-PAGE header+0xA0 holds a small count (0xf/0x7), not a CSC.

**Original audit verdict:** CONTRADICTED (disk held 0/112 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- Lee labels CSC at value+0xA0. This probe tests whether value+0xA0 holds the physical start (== value[len-16]). EXPECTED TO FAIL: byte-dump shows value+0xA0 == 0 on both 160B and 224B rows; the CSC/physical-start is at value+0x90 (160B) / +0xD0 (224B) = value[len-16], NOT 0xA0. A CONTESTED verdict here SURFACES a source mislabel (Lee) — see correction finding.

## Raw-disk proof
- probe `ct_row` ; validation matrix: `proofs/validation/CT_CTBL_010.csv`
- corrected registry note: PT: Field exists at 0xA0 in 224B CT rows (SHA-256 image). Value=0 on test images. Not present in 160B (CRC64-only) format. | RE-VERIFIED 2026-06-18 (all-disk): value+0xA0 is OUT OF BOUNDS for 160B (4K) rows (last offset 0x9F). For 224B rows, value[0xA0:0xA8]=zeros. The actual CSC (Container Start Cluster) is at value[len-16]=0x90(160B)/0xD0(224B), NOT 0xA0. The CT-root-PAGE header+0xA0 holds a sma

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_010.csv` (matrix) — 
