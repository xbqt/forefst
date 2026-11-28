# Dossier — FS_VBR_RA_005 (BEHAVIORAL)

**Claim (this audit tests):** refsutil fixboot zeroes VBR fields 0x2A-0x57 (serial/container/GUID) — preserves only geometry (sector/cluster/count/version)

**Canonical claim (reference_table.csv):** File System: refsutil fixboot zeroes VBR fields 0x2A-0x57 (serial/container/GUID) — preserves only geometry (sector/cluster/count/version)

**Re-verification verdict (all-disk, 2026-06-18):** **INFERRED** — Disk corroboration on the 1 fixboot image: win11refs2tmillionsofactions_aftersalvage_fixboottest.raw has serial=0 (0x38), container=0 (0x40), GUID=0 (0x48), 0x2A=0, flags=0x04; geometry (0x18 sectors, 0x20 bps, 0x24 spc, 0x28 version=3.14) preserved; VBR checksum recomputed and valid.

**Original audit verdict:** INFERRED (disk held 0/1 at audit time) · **Registry status:** INFERRED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- refsutil.exe (NOT refs.sys) behavior: CFixBoot::Execute zeroes the listed VBR fields. RD-confirmed on the fixboot-test image (the scoped exception in FS_VBR_006/010/011). structure_reference.md:90.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FS_VBR_RA_005.csv`
- corrected registry note: Documented from fixboot test. 29 bytes differ. Container size=0 makes mounting impossible | DOWNGRADED to INFERRED 2026-06-18 (all-disk re-verify: offset/value RD-confirmed, semantic label not disk-checkable — was CONFIRMED): Behavioral STATIC-CITED claim. I cannot run refsutil, but the single fixboot artifact on disk matches every asserted effect (zeroes 0x2A-0x57 incl serial/container/GUID, preserves geometry). Single-image, so INFERRED rather than A

## Proof links
- `proofs/validation/FS_VBR_RA_005.csv` (matrix) — 
