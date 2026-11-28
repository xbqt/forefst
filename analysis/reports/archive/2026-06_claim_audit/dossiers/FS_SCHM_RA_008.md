# Dossier — FS_SCHM_RA_008 (BEHAVIORAL)

**Claim (this audit tests):** Complete schema identification: 36 distinct schema IDs (18 system + 18 attribute; corrected from 37/19 — phantom 0xe020/0xe0a0 absent from all disk images). 28 confirmed with name (4 attribute via E2 static analysis, 4 legacy system via E3 structural inference). Naming corrections: 0x160=Reparse Index; 0x1b0=$SNAPSHOT; 0x1c0=$REPARSE_POINT; 0x1d0=$EA_INFORMATION; 0x1e0=$EA; 0x1f0=$LOGGED_UTILITY_STREAM. 4 legacy system schemas named via vdo matching: 0xe050=Object Data Table, 0xe070=Reserved/Placeholder, 0xe0e0=System Directory Entry List, 0xe0f0=System File Stream. 2 schemas remain unknown (2 legacy attribute 0x4/0x6). Schema 0xe140 resolved: Volume Attestation Table (E2: CmsVolumeAttestation::InitializeAttestationTable via MsCreateDurableTableObject; 61 functions in class; confirmed via Insider decompilation 2026-05-25)

**Canonical claim (reference_table.csv):** File System: Complete schema identification: 36 distinct schema IDs (18 system + 18 attribute; corrected from 37/19 — phantom 0xe020/0xe0a0 absent from all disk images). 28 confirmed with name (4 attribute via E2 static analysis, 4 legacy system via E3 structural inference). Naming corrections: 0x160=Reparse Index; 0x1b0=$SNAPSHOT; 0x1c0=$REPARSE_POINT; 0x1d0=$EA_INFORMATION; 0x1e0=$EA; 0x1f0=$LOGGED_UTILITY_STREAM. 4 legacy system schemas named via vdo matching: 0xe050=Object Data Table, 0xe070=Reserved/Placeholder, 0xe0e0=System Directory Entry List, 0xe0f0=System File Stream. 2 schemas remain unknown (2 legacy attribute 0x4/0x6). Schema 0xe140 resolved: Volume Attestation Table (E2: CmsVolumeAttestation::InitializeAttestationTable via MsCreateDurableTableObject; 61 functions in class; confirmed via Insider decompilation 2026-05-25)

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — Union of all schema-table keys across 111 images = exactly 36 distinct IDs = 18 system (0xe010,e030,e040,e050,e060,e070,e080,e090,e0b0,e0c0,e0d0,e0e0,e0f0,e100,e110,e120,e130,e140) + 18 attribute (0x004,0x006,0x110-0x200). Phantom 0xe020 and 0xe0a0 present on 0/111 images.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** ENRICHED · **Evidence:** E2 (insider)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [Schema Table] Complete schema identification: 36 distinct schema IDs (18 system + 18 attribute; corrected from 37/19 — phant — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_SCHM_RA_008.csv`
- corrected registry note: See ra_step4_22 + ra_step4_8b. 28/37 schemas now named. Legacy schemas confirmed vestigial via exhaustive binary search + CHKP root analysis

## Proof links
- `proofs/validation/FS_SCHM_RA_008.csv` (matrix) — 
