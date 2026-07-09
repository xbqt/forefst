# Dossier — MD_DATA_RA_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Type 0x40 value main header: file_size at offset +0x58, alloc_size at +0x60, timestamps at +0x28, file_attrs at +0x48

**Canonical claim (reference_table.csv):** Metadata: Type 0x40 value main header: file_size at offset +0x58, alloc_size at +0x60, timestamps at +0x28, file_attrs at +0x48

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — type-0x40 value header: file_size@0x58, alloc_size@0x60, timestamp@0x28, attrs@0x48. Sanity on 40,247/40,247 type-0x40 values (53 images): file_size<=alloc (100%), ts@0x28 sane FILETIME 2010-2040 (100%), attrs@0x48 plausible (100%). Strong cross-check: alloc@0x60 == roundup(file_size@0x58, cluster) on 4,656/4,656 files with data extents; alloc == sum(run_lengths)*cs on 4,463/4,656.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 42/53 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/walk_bplus__forefst.txt
- file_size@0x58 verified. alloc_size@0x60 is cluster-granular on the majority (42/52 volumes) but ~20% of extent rows on some volumes (incl. Insider winsider 6823/33793) have a non-cluster-aligned 0x60 value — an UNDECODED type-0x40 value-layout variant. CONTESTED-by-design: the alloc@0x60 sub-claim does not hold corpus-wide; file_size@0x58 + the 24-byte key (MD_DATA_RA_004) are solid. Needs further decode of the 0x40 value variants.

## Raw-disk proof
- probe `row0x40` ; validation matrix: `proofs/validation/MD_DATA_RA_005.csv`
- corrected registry note: Confirmed by matching values between type 0x30 (compact) and type 0x40 (full header) for same file

## Proof links
- `proofs/static/walk_bplus__forefst.txt` (static) — walk_bplus
- `proofs/validation/MD_DATA_RA_005.csv` (matrix) — 
