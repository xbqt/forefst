# Dossier — CT_CTBL_RA_004 (STRUCTURAL)

**Claim (this audit tests):** Container Allocator (root #2, Table ID 0x20) uses VIRTUAL addressing on ALL versions — contradicts Prade suggestion of real addressing for 3.4

**Canonical claim (reference_table.csv):** Content: Container Allocator (root #2, Table ID 0x20) uses VIRTUAL addressing on ALL versions — contradicts Prade suggestion of real addressing for 3.4

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Container Allocator root#2: untranslated page@vlcn=0x00000000, translated page@plcn=MSB+ on 113/113 images, INCLUDING v3.4 (win10refs8g, win10refs5g64k). Both cluster sizes.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- structure_reference.md:203 root 2 = Container Allocator, Table ID 0x20, Virtual. Verified: root[2] table-root page +0x48 == 0x20. Virtual addressing follows because root 2 is NOT one of the real-LCN bootstrap roots {7,8,12} (structure_reference.md:214).

## Raw-disk proof
- probe `chkp_root_table` ; validation matrix: `proofs/validation/CT_CTBL_RA_004.csv`
- corrected registry note: Tested on all images: root #2 VLCNs resolve through Container Table and differ from PLCNs. Only roots 7+8+12 use real addressing

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/CT_CTBL_RA_004.csv` (matrix) — 
