# Dossier — MD_SNAP_RA_001 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Stream snapshots: snapshot name stored inline as UTF-16LE in sub-record body. Created via refsutil streamsnapshot /c.

**Canonical claim (reference_table.csv):** Metadata: Stream snapshots: snapshot name stored inline as UTF-16LE in sub-record body. Created via refsutil streamsnapshot /c.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — On win11refs2tsnapshots.raw the snapshot 0xB0 sub-record stores its name inline as UTF-16LE in the sub-record key starting at key[16] (decoded names: test2, sameaslastversion, first, v3, v2, last, firstversion, beforeads, versionmodified, copiedversion). Each snapshot value is 116 bytes with flags@val[0x10]==2.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** NEW · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Snapshot structure (0xB0, finding S7). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_SNAP_RA_001.csv`
- corrected registry note: See ra_step4_18_deep_attribute_analysis_report.md Section 10.1

## Proof links
- `proofs/validation/MD_SNAP_RA_001.csv` (matrix) — 
