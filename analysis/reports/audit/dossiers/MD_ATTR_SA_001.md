# Dossier — MD_ATTR_SA_001 (BEHAVIORAL)

**Claim (this audit tests):** 8 new Win11 attributes: $EFS, $LXUID, $LXGID, $LXMOD, $LXDEV, $SNAPSHOT, $OBJ_LINK, $PAGE. Total: 17->25.

**Canonical claim (reference_table.csv):** Metadata: 8 new Win11 attributes: $EFS, $LXUID, $LXGID, $LXMOD, $LXDEV, $SNAPSHOT, $OBJ_LINK, $PAGE. Total: 17->25.

**Re-verification verdict (all-disk, 2026-06-18):** **STATIC-CITED**

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Win11-introduced attributes catalogued from the schema table + decompilation; individual attributes are disk-verified elsewhere (e.g. MD_EFS_RA_004 $CBW4 correction). Catalog-level claim cited here.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_SA_001.csv`
- corrected registry note: CORRECTED 2026-06-19 (E35): $CBW4 removed — it is a fabrication (0 on disk, 0 as a binary string; the ~140 'CBW4' decomp hits are mangled span<4 byte> template names). Was '9 new / 17->26'. | Win11 schema table has 4 more attribute schemas (0x1c0-0x200) than Win10; may correspond to subsets of these 9 new attributes

## Proof links
- `proofs/validation/MD_ATTR_SA_001.csv` (matrix) — 
