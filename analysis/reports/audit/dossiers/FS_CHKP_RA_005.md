# Dossier — FS_CHKP_RA_005 (PURE-RD-LAYOUT)

**Claim (this audit tests):** CHKP 0x88-0x8B: data area end offset. Value = first_root_offset + root_count * ref_size. 0x680 for 3.4 (13x104B refs from 0x138), 0x380 for 3.14 (13x48B refs from 0x110)

**Canonical claim (reference_table.csv):** File System: CHKP 0x88-0x8B: data area end offset. Value = first_root_offset + root_count * ref_size. 0x680 for 3.4 (13x104B refs from 0x138), 0x380 for 3.14 (13x48B refs from 0x110)

**Re-verification verdict (all-disk, 2026-06-18):** **CONTRADICTED** — CHKP+0x88 data-area-end is NOT 'first_root_offset + root_count*ref_size'. v3.4: disk=0x680 but 0x94+13*0x68=0x5dc (mismatch). v3.14: disk=0x380/0x388 but 0x94+13*0x30=0x274. The headline VALUES (0x680 v3.4, ~0x380 v3.14, ~0x4d0 SHA256) are correct, but the FORMULA in the claim is wrong. 0x88 is version/cksum-keyed (0x680@refsize0x68, 0x370-0x388@refsize0x30, 0x4d0-0x4d8@refsize0x48), 16-byte granular, and 0x0 on 3 native-v3.14 images.

**Original audit verdict:** CONTRADICTED (disk held 84/112 at audit time) · **Registry status:** CONTRADICTED · **Evidence:** E2

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/parse_chkp__forefst.txt
- Tests CHKP+0x88 non-zero. CONTESTED BY DESIGN: 0x0 on the SAME 28 v3.14-native images that zero 0x8C (FS_CHKP_RA_012) — the checkpoint 0x88-0x8F region co-varies populated-vs-zeroed per checkpoint. Finding #339.

## Raw-disk proof
- probe `field_plausible` ; validation matrix: `proofs/validation/FS_CHKP_RA_005.csv`
- corrected registry note: Mathematically verified: 3.4: 0x138+13*104=0x680. 3.14: 0x110+13*48=0x380. Serves as bounds check for driver. See report_checkpoint_deep_analysis.md | RE-VERIFIED 2026-06-18 (all-disk): CHKP+0x88 data-area-end is NOT 'first_root_offset + root_count*ref_size'. v3.4: disk=0x680 but 0x94+13*0x68=0x5dc (mismatch). v3.14: disk=0x380/0x388 but 0x94+13*0x30=0x274. The headline VALUES (0x680 v3.4, ~0x380 v3.14, ~0x4d0 SHA256) are 

## Proof links
- `proofs/static/parse_chkp__forefst.txt` (static) — parse_chkp
- `proofs/validation/FS_CHKP_RA_005.csv` (matrix) — 
