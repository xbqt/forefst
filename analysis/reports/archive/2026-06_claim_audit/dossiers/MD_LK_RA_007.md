# Dossier — MD_LK_RA_007 (STRUCTURAL)

**Claim (this audit tests):** $OBJ_LINK value format (v3.7+): +0x00=marker(4B) +0x04=type(2B) +0x06=subtype(2B) +0x08=parent_oid(le32) +0x0C=reserved(12B zeros) +0x18=filename(UTF-16LE). Total varies with filename length (26-82 bytes observed).

**Canonical claim (reference_table.csv):** Metadata: $OBJ_LINK value format (v3.7+): +0x00=marker(4B) +0x04=type(2B) +0x06=subtype(2B) +0x08=parent_oid(le32) +0x0C=reserved(12B zeros) +0x18=filename(UTF-16LE). Total varies with filename length (26-82 bytes observed).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — v3.7+ 0x39 value layout exact on 32204/32204 entries: +0x00 marker=0x80000002 (32204/32204), +0x04 type=0x39 (32204/32204), +0x06 subtype=0x0d (observed constant), +0x08 parent_oid le32 in obj_map (32204/32204), +0x0C reserved = 12 bytes of zero (32204/32204), +0x18 filename UTF-16LE decodes (32204/32204). Observed value lengths 26-82 bytes (varies with filename), matching claim's '26-82 bytes observed'.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- ObjLink value layout. Feature-gated; cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_LK_RA_007.csv`
- corrected registry note: 32077 entries parsed: parent_oid at +0x08 matches directory walk parent. Filename at +0x18 matches type 0x30 key. Reserved bytes +0x0C always zero.

## Proof links
- `proofs/validation/MD_LK_RA_007.csv` (matrix) — 
