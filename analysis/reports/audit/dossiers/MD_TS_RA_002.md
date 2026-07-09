# Dossier — MD_TS_RA_002 (PURE-RD-LAYOUT)

**Claim (this audit tests):** Write operations update both Last Write Time (M offset 0x30) and Last Access Time (A offset 0x40) simultaneously to the same value. A write implies access.

**Canonical claim (reference_table.csv):** Metadata: Write operations update both Last Write Time (M offset 0x30) and Last Access Time (A offset 0x40) simultaneously to the same value. A write implies access.

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — M (mod) at $SI+0x08 (type-0x10) / value+0x30 (resident index entry) and A (access) at $SI+0x18 / value+0x40 both exist and are sane FILETIMEs corpus-wide (res_times_sane 409401/409514). On probed files M==A==metachange==create for freshly-written files (e.g. all 4 equal on win11refs2gtargeted OID 0x705).

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (timestamp updates). M=$SI+0x08, C=$SI+0x10 (disk-proven MD_FTBL_002/003). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_TS_RA_002.csv`
- corrected registry note: Observed in manual timestamp tests on win11refs8gtest4timestamps.raw. See ra_step4_17_4th_timestamp_report.md | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): The 'write updates both M and A to the same value' is behavioral; partially visible (equal timestamps on written files) but a controlled write-vs-read experiment is needed to assert causation. Offsets confirmed.

## Proof links
- `proofs/validation/MD_TS_RA_002.csv` (matrix) — 
