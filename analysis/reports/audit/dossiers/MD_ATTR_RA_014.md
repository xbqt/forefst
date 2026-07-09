# Dossier — MD_ATTR_RA_014 (BEHAVIORAL)

**Claim (this audit tests):** Sub-record value format cross-version: ALL layouts identical across v3.4/v3.7/v3.9/v3.10/v3.14/Insider. Only KEY format differs (v3.4 no markers, v3.7+ markers at key[8:12]).

**Canonical claim (reference_table.csv):** Metadata: Sub-record value format cross-version: ALL layouts identical across v3.4/v3.7/v3.9/v3.10/v3.14/Insider. Only KEY format differs (v3.4 no markers, v3.7+ markers at key[8:12]).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Sub-record VALUE format identical across versions: the const@8=0x0C 12-byte header and per-type value layouts hold on v3.4, v3.7, v3.9, v3.10, v3.14, v3.15(Insider) - 378222/378222 const=0x0C. KEY format differs as claimed: v3.4 has NO marker (type code at key[8:10], e.g. 0x90/0x38), v3.7+ has marker 0x80000001/0x80000002 at key[8:12] with type at key[12:14]. Directly verified by dumping raw embedded keys on v3.4 vs v3.7 vs v3.14.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Cross-version structural-identity meta-claim (RD across the corpus). The per-type structures (RA_009-013, EFS_005, SNAP_006) are disk-verified on v3.14; format identity across versions cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_014.csv`
- corrected registry note: Compared sub-record values across 6 version groups. 0 format deviations.

## Proof links
- `proofs/validation/MD_ATTR_RA_014.csv` (matrix) — 
