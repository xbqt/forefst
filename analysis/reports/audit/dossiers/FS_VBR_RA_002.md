# Dossier — FS_VBR_RA_002 (BEHAVIORAL)

**Claim (this audit tests):** 0x48-0x57: Extended GUID (per InitializeVcbFromBootSector → VCB+0x33F0). Unique GUID generated per format event. First appears at v3.10 (Win11 23H2). Zero on v3.4/v3.7/v3.9 and upgraded volumes. Same disk formatted twice → different GUIDs confirmed.

**Canonical claim (reference_table.csv):** File System: 0x48-0x57: Extended GUID (per InitializeVcbFromBootSector → VCB+0x33F0). Unique GUID generated per format event. First appears at v3.10 (Win11 23H2). Zero on v3.4/v3.7/v3.9 and upgraded volumes. Same disk formatted twice → different GUIDs confirmed.

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — VBR[0x48:0x58] Extended GUID nonzero by version: v3.4 0/13, v3.7 0/1, v3.9 0/2, v3.10 2/2, v3.14 88/92 (4 zero are all upgraded volumes), v3.15 1/1, v6.66 2/2. First-nonzero boundary is exactly v3.10.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2 (all)

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- [VBR] 0x48-0x57: Extended GUID (per InitializeVcbFromBootSector → VCB+0x33F0). Unique GUID generated per format even — E2/RD claim from the thesis analysis; cited (not corpus-disk-probeable as a single field).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_RA_002.csv`
- corrected registry note: Verified on 80+ images: all Win10 zeros; 30+ Win11 unique GUIDs; user dual-format test confirms per-format generation; stable across mount/unmount. Static analysis: InitializeVcbFromBootSector copies to VCB+0x33F0

## Proof links
- `proofs/validation/FS_VBR_RA_002.csv` (matrix) — 
