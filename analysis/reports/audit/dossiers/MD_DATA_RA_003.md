# Dossier — MD_DATA_RA_003 (BEHAVIORAL)

**Claim (this audit tests):** Hardlinked files share a single type 0x40 extent entry in the original directory's B+-tree [SUPERSEDED by FN_LINK_002/#340: the type-0x30 value+0x00 is a per-directory child ordinal (not a stream_index) and value+0x08 is the home-dir backref]

**Canonical claim (reference_table.csv):** Metadata: Hardlinked files share a single type 0x40 extent entry in the original directory's B+-tree [SUPERSEDED by FN_LINK_002/#340: the type-0x30 value+0x00 is a per-directory child ordinal (not a stream_index) and value+0x08 is the home-dir backref]

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Hard-link behavior is non-resident type-0x30 + type-0x40 extent sharing; SUPERSEDED by FN_LINK_002/#340. On disk hard-linked files share extents in the home directory's tree (home-dir backref at type-0x30 value+0x08).

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (hardlink storage). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_003.csv`
- corrected registry note: Remote resolution: follow the home-dir backref (value+0x08) from type 0x30 to find type 0x40 with matching stream_index in that tree | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): This is a behavioral/superseded claim, not a pure byte-layout assertion. The corrected model (value+0x00 = per-dir child ordinal, value+0x08 = home backref) is in FN_LINK_002. Marking INFERRED — the superseding claim FN_LINK_002 i

## Proof links
- `proofs/validation/MD_DATA_RA_003.csv` (matrix) — 
