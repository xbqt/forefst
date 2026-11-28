# Dossier — FN_DTBL_006 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Directory key has no Reserved(4) field at 0x04. Correct: Type(2)+key_flags(2)+Filename(var) starting at offset 0x04. Errata E16.

**Canonical claim (reference_table.csv):** File Name: Directory key has no Reserved(4) field at 0x04. Correct: Type(2)+key_flags(2)+Filename(var) starting at offset 0x04. Errata E16.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — type-0x30 key = Type(2)@0x00 + key_flags(2)@0x02 + Filename(var)@0x04. Filenames decode 525,178/525,178 from key[4:] as UTF-16LE; no 4-byte Reserved field at 0x04.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 112/112 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- Correction: the 0x30 key is Type(2)@0 + key_flags(2)@2 + UTF-16 name (no reserved field). Byte-verified every key: type 0x30, (len-4) even.

## Raw-disk proof
- probe `dirkey` ; validation matrix: `proofs/validation/FN_DTBL_006.csv`
- corrected registry note: Row size proof: coucou=6 chars -> key=4+12=16B; with Reserved(4) it would be 20B giving 108 not 104=0x68

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/FN_DTBL_006.csv` (matrix) — 
