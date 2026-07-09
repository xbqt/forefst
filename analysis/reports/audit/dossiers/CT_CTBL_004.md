# Dossier — CT_CTBL_004 (STRUCTURAL)

**Claim (this audit tests):** Translation: PCN = CSC + CN

**Canonical claim (reference_table.csv):** Content: Translation: PCN = CSC + CN

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — physical_LCN = container_map[cid] + (vlcn & mask). tr(cid<<shift)==container_phys_start on 113/113 images. Container Allocator root#2 untranslated page=zeros, translated page=MSB+ on 113/113.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/Translator__forefst.txt
- structure_reference.md VLCN->PLCN: physical_LCN = container_phys_start + (vlcn & (CPC-1)). Verified by reconstructing the OT-root page: tr(vlcn) == CT_phys_start[cid] + (vlcn & mask) AND the result is a valid MSB+ page.

## Raw-disk proof
- probe `ct_translate` ; validation matrix: `proofs/validation/CT_CTBL_004.csv`
- corrected registry note: PLCN = container_map[container_id] + offset. Verified by successful page reads on all images

## Proof links
- `proofs/static/Translator__forefst.txt` (static) — Translator
- `proofs/validation/CT_CTBL_004.csv` (matrix) — 
