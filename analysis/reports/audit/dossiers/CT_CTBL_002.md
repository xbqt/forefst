# Dossier — CT_CTBL_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Translation: Container_ID = LCN >> CPC_BitCount

**Canonical claim (reference_table.csv):** Content: Translation: Container_ID = LCN >> CPC_BitCount

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Translator: container_index = vlcn >> shift, shift=CPC.bit_length()=15(4K)/11(64K). Verified by translating cid<<shift back to phys start: addr_translate ok on 113/113 images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/_parse_ct_page__forefst.txt
- structure_reference.md:246 CT row CPC at value+0x18 = 16384 (4K) / 1024 (64K). The translation shift = CPC.bit_length() (15/11, errata E18), fully determined by CPC; the cpc probe verifies CPC, hence the shift. A constant-offset probe cannot test a formula — CPC is the load-bearing geometry constant. Cluster-discriminated.

## Raw-disk proof
- probe `cpc` ; validation matrix: `proofs/validation/CT_CTBL_002.csv`
- corrected registry note: Formula verified: Container_ID = VLCN >> shift; shift=15 for 4K / 11 for 64K (corrected per E18 — prior 14/10 omitted the +1). Tested on all 39 images

## Proof links
- `proofs/static/_parse_ct_page__forefst.txt` (static) — _parse_ct_page
- `proofs/validation/CT_CTBL_002.csv` (matrix) — 
