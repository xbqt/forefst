# Dossier — MD_ATTR_009 (PURE-RD-LAYOUT)

**Claim (this audit tests):** $USN_INFO: Change Journal org metadata (unofficial name)

**Canonical claim (reference_table.csv):** Metadata: $USN_INFO: Change Journal org metadata (unofficial name)

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — The '$USN_INFO' name is analyst-assigned (not on disk, not in PDB). The USN $Max attribute IS on disk as a 0xF0 sub-record (44B, SI marker) on OID 0x520 'FS Metadata' in 9 USN-active images. No byte signal validates the specific name '$USN_INFO'.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- 0xF0 USN $Max disk-proven in MD_USN_RA_004. Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_ATTR_009.csv`
- corrected registry note: verify_usn_claims.py: OID 0x520 confirmed as journal metadata container ("FS Metadata" directory). Type 0x10 descriptor = organizational metadata. "$USN_INFO" name is analyst-assigned, not found in binary or PDB symbols. Actual name in parent-child table: "FS Metadata". | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was ENRICHED): Pure semantic-name claim (confidence Low, evidence N/A). The underlying 0xF0/OID-0x520 mechanism is disk-confirmed (see RA_016).

## Proof links
- `proofs/validation/MD_ATTR_009.csv` (matrix) — 
