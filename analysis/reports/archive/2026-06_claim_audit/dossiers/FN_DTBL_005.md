# Dossier — FN_DTBL_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** key_flags is u16 at key+0x02, NOT first 4 bytes of row header. Values 0x68/0x2a8 are row sizes. CORRECTION: key_flags take ONLY {0x01=resident, 0x02=non-resident}; 0x04 NEVER appears. Directories are key_flags 0x02 with the directory attribute bit 0x10000000 set in the value attribute word (value+0x40), NOT a separate 0x04 flag. Distribution 111 images/525K entries: {0x01: 409483 ; 0x02: 115682 ; 0x04: 0}. Errata E15/E17 "0x04=directory" was wrong.

**Canonical claim (reference_table.csv):** File Name: key_flags is u16 at key+0x02, NOT first 4 bytes of row header. Values 0x68/0x2a8 are row sizes. CORRECTION: key_flags take ONLY {0x01=resident, 0x02=non-resident}; 0x04 NEVER appears. Directories are key_flags 0x02 with the directory attribute bit 0x10000000 set in the value attribute word (value+0x40), NOT a separate 0x04 flag. Distribution 111 images/525K entries: {0x01: 409483 ; 0x02: 115682 ; 0x04: 0}. Errata E15/E17 "0x04=directory" was wrong.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — type-0x30 key_flags at key+0x02 across 525,178 entries on 111 images: {0x01: 409,496 ; 0x02: 115,682 ; 0x04: 0}. 0x04 NEVER appears. Directories are kf=0x02 with directory bit 0x10000000 at value+0x40.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- E-correction: key_flags is the u16 at key+0x02, not the first 4 bytes. Byte-verified every 0x30 key has key_flags in {1,2}.

## Raw-disk proof
- probe `dirkey` ; validation matrix: `proofs/validation/FN_DTBL_005.csv`
- corrected registry note: key_flags distribution {0x01:409483, 0x02:115682, 0x04:0} across 111 images. Directories: kf=0x02 + attrs bit 0x10000000 at value+0x40 (e.g. $RECYCLE.BIN kf=0x02 attrs=0x10000006).

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/FN_DTBL_005.csv` (matrix) — 
