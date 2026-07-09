# Dossier — MD_ATTR_RA_003 (PURE-RD-LAYOUT)

**Claim (this audit tests):** FileAttributes flag 0x40000 indicates Extended Attributes present — undocumented by Microsoft

**Canonical claim (reference_table.csv):** Metadata: FileAttributes flag 0x40000 indicates Extended Attributes present — undocumented by Microsoft

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — FileAttributes 0x40000 (EA-present) observed at dirent value+0x40: combos 0x40020=14181, 0x40000=10, 0x40021=15, 0x42020=1, 0x10040000=2, 0x10040020=3. The 0x40000 bit co-occurs with EA-bearing files (WSL $LX*, $KERNEL.PURGE.* etc.).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- EA flag in FileAttributes; EA disk-proven (MD_ATTR_RA_011). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_RA_003.csv`
- corrected registry note: Discovered during refs_attributes.py development. WSL files with $LXMOD/$LXUID/$LXGID have this flag set

## Proof links
- `proofs/validation/MD_ATTR_RA_003.csv` (matrix) — 
