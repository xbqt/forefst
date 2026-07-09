# Dossier — FN_LINK_001 (ABSENCE)

**Claim (this audit tests):** Hard links abolished in ReFS 3.4 (Win10); fully supported in ReFS 3.14 (Win11 native, CHKP flag 0x080 required)

**Canonical claim (reference_table.csv):** File Name: Hard links abolished in ReFS 3.4 (Win10); fully supported in ReFS 3.14 (Win11 native, CHKP flag 0x080 required)

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Disk layer confirms the version delta: v3.4 non-resident type-0x30 = key_flags 0x02 / 72-byte value; v3.14 = key_flags 0x02 / 84-byte value (the +12B carries the home backref + ordinal hard-link fields). v3.14 images contain genuine hard-link groups (multiple names sharing home+ordinal); v3.4 images contain none. 'Hard links abolished in v3.4 / supported in v3.14' is consistent with the on-disk evidence.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral/version. HardLinkCount<=1 disk-proven (MD_SI_RA_009). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FN_LINK_001.csv`
- corrected registry note: Win11 specials: 182 hardlink files, 33 shared-OID groups; the '110 true hard links' count was a PARSER ARTIFACT (RETRACTED #292/E33 — non-resident type-0x30 value+0x08 is the home-dir backref shared by siblings). Genuine hard links use the non-resident mechanism in FN_LINK_002/#340. Win10 specials: 0 hardlink files (CreateHardLink fails). Upgraded 3.4->3.14: no hard links (flag 0x080 absent) | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was ENRICHED): The specific 'CHKP flag 0x080 required' part is a checkpoint/driver gate (E2), not measured here - it is INFERRED at the disk layer. The supported-vs-abolished behavior is disk-consistent.

## Proof links
- `proofs/validation/FN_LINK_001.csv` (matrix) — 
