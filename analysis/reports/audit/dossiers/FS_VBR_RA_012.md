# Dossier — FS_VBR_RA_012 (PURE-RD-LAYOUT)

**Claim (this audit tests):** VBR+0x48 Extended GUID populated on ALL native v3.10+ volumes (93/113 images). ZERO on v3.4/v3.7/v3.9 and upgraded volumes. Boundary is v3.10 (not v3.14). VBR is format-time only — upgrade never rewrites it. 4 zero-GUID v3.14 images identifiable by chksum_algo=0x0000 (pre-v3.14 format).

**Canonical claim (reference_table.csv):** File System: VBR+0x48 Extended GUID populated on ALL native v3.10+ volumes (93/113 images). ZERO on v3.4/v3.7/v3.9 and upgraded volumes. Boundary is v3.10 (not v3.14). VBR is format-time only — upgrade never rewrites it. 4 zero-GUID v3.14 images identifiable by chksum_algo=0x0000 (pre-v3.14 format).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — ExtGUID populated 93/113, v3.10+ boundary

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 85/85 at audit time) · **Registry status:** CONFIRMED · **Evidence:** RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_vbr__forefst.txt
- VBR+0x48 Extended GUID is populated (non-zero) on NATIVE v3.10+ volumes (upgraded volumes keep it 0 per structure_reference.md:30). applicability native + version>=3.10. Byte-verified.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_VBR_RA_012.csv`
- corrected registry note: 113 images surveyed. 2 v3.10 images confirm v3.10 boundary. Original structure_reference.md claim 'pre-v3.10' was correct. Report: report_extended_guid_static.txt

## Proof links
- `proofs/static/parse_vbr__forefst.txt` (static) — parse_vbr
- `proofs/validation/FS_VBR_RA_012.csv` (matrix) — 
