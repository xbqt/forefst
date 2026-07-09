# Dossier — MD_TS_RA_006 (BEHAVIORAL)

**Claim (this audit tests):** win11refs8gtest4timestamps.raw volume structure: 244 objects OID range 0x7-0x823. Root OID=0x600 newtests=0x741 viascript3=0x742 v2=0x7AC test=0x707.

**Canonical claim (reference_table.csv):** Metadata: win11refs8gtest4timestamps.raw volume structure: 244 objects OID range 0x7-0x823. Root OID=0x600 newtests=0x741 viascript3=0x742 v2=0x7AC test=0x707.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — win11refs8gtest4timestamps.raw (v3.14): obj_map OID count = 244 (matches '244 objects'); OID range min=0x7, max=0x823 (matches '0x7-0x823'); root OID=0x600. Name resolution: test=0x707 (parent 0x600), newtests=0x741 (parent 0x600), viascript3=0x742 (parent newtests/0x741), v2=0x7AC (parent newtests/0x741) - all match the claim exactly.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Single-image structural observation (object count). Cited; not a corpus-wide invariant.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_TS_RA_006.csv`
- corrected registry note: Verified via refs_dataruns.py on win11refs8gtest4timestamps.raw. See ra_step4_17_4th_timestamp_report.md

## Proof links
- `proofs/validation/MD_TS_RA_006.csv` (matrix) — 
