# Dossier — MD_ATTR_RA_012 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $EA (0xE0): FILE_FULL_EA_INFORMATION chain at val[0x0C]. Standard NT format. Common EAs: $KERNEL.PURGE.ESBCACHE (30B), $LXUID/$LXGID/$LXMOD (4B each), $LXDEV (8B = u32 major + u32 minor, #341). 3854 entries, 44-209B values.

**Canonical claim (reference_table.csv):** Metadata: $EA (0xE0): FILE_FULL_EA_INFORMATION chain at val[0x0C]. Standard NT format. Common EAs: $KERNEL.PURGE.ESBCACHE (30B), $LXUID/$LXGID/$LXMOD (4B each), $LXDEV (8B = u32 major + u32 minor, #341). 3854 entries, 44-209B values.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — 0xE0 $EA: FILE_FULL_EA_INFORMATION chain at val[0x0C] parses cleanly on 3875/3875 records using standard NextEntryOffset traversal. Value lengths 36-244B. EA names observed: $CI.CATALOGHINT(2182), $KERNEL.PURGE.ESBCACHE(1664), $KERNEL.PURGE.APPXFICACHE(1659), $LXMOD/$LXUID/$LXGID(23 each), APPLICENSING(3), $LXDEV(2).

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 4/4 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- $EA (0xE0) sub-records carry marker 0x80000001 (FILE_FULL_EA_INFORMATION chain at val[0x0C]). Byte-verified 4/4. N/A where no EAs.

## Raw-disk proof
- probe `subrec` ; validation matrix: `proofs/validation/MD_ATTR_RA_012.csv`
- corrected registry note: 3854 entries decoded. EA chain parses correctly using standard NextEntryOffset traversal.

## Proof links
- `proofs/validation/MD_ATTR_RA_012.csv` (matrix) — 
