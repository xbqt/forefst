# ReFS Claim Audit — COMPLETE (all 409 reference_table claims)

**Date:** 2026-06-13 (**updated 2026-06-14**: +4 step6 findings registered — FN_LINK_002, FS_REPS_RA_003,
MD_INTG_RA_001, AP_LGFL_RA_008 — and the 2 step6 images added to the corpus; 3 stale specs corrected:
MD_SI_RA_006 integrity-bit label, MD_SI_RA_009 hard-link framing, MD_UNSUP_RA_001 hard-link-enum scope.)
**Result:** Every one of the **409 claims in `reference_table.csv` is audited** — each has a spec with a
verified ref_id↔claim correspondence, a proof (disk validation matrix, exported static function, or sourced
citation), and a corpus-aware verdict. This is the "big report + claim→proof linkage" deliverable requested.

## The numbers

| | count |
|---|---|
| **Claims audited** | **409 / 409 (100%)** |
| CONFIRMED (disk, ≥3 independent groups) | 118 |
| STATIC-CONFIRMED (exported decompiled function) | 73 |
| STATIC-CITED (behavioral/literature, sourced) | 212 |
| RD-LIMITED (1 group) | 1 |
| **CONTESTED-by-design** (documented corrections) | **5** |
| Disk probe shapes built | 28 |
| Static-function artifacts exported | 33 |
| Per-claim validation matrices | 409 |
| Generated dossiers | 409 |
| proof_links rows (many-to-many) | 576 |

Disk-validated against **112 ReFS images** (70 independent samples / 50 lineage groups), per-image,
output-parsed (never exit-code). (2026-06-14: corpus grew 110→112 with the two step6 images; the expansion
introduced **no new FAILs** — the 5 CONTESTED are the same pre-existing documented corrections.)

## Deliverables (all in `analysis/reports/audit/`)

- **`proof_index.csv`** — THE master table: every claim → class, verdict, n_pass/n_applicable,
 correspondence, canonical claim text, static artifact, disk probe, validation matrix.
- **`proof_links.csv`** — many-to-many claim ↔ proof artifact (a function/matrix backs multiple claims).
- **`dossiers/<ref_id>.md`** — per-claim: claim tested vs canonical claim, correspondence, verdict, static
 proof, raw-disk proof, confirmation ledger.
- **`proofs/static/`** — exported decompiled driver functions + forefst functions.
- **`proofs/validation/<ref_id>.csv`** — the corpus validation matrix per claim.
- **`specs.jsonl`** — all 409 authored specs. **`audit_harness.py`** — the harness (28 probe shapes).
- **`images.csv`** — the corpus manifest. **`batch{1,2,3}_claims.csv`** — the audited batches.
- **`proof_index.csv`** / **`proof_links.csv`** — the per-claim verdict tables. **`dossiers/<ref_id>.md`**, **`proofs/validation/<ref_id>.csv`** — per-claim proof. This file is the headline summary.

## The two mandatory gates (both held for all 409)

1. **ref_id↔claim correspondence** — every dossier shows the canonical reference_table claim beside the probe
 target; a CONFIRMED verdict is rejected if the probe tests a different claim. *Found 3 mislabels in the
 pilot itself.*
2. **Contradiction protocol** — every CONTESTED was investigated against bytes, never auto-flipped: resolved
 as a probe bug (fixed), a documented scoped exception (mechanism + knowledge-link), or a genuine correction.

## The 5 CONTESTED-by-design (the audit doing its job, not failures)

- **CT_CTBL_010** — Lee's "CSC at value+0xA0" is wrong; CSC is at value[len-16] (0x90/0xD0). Finding #338.
- **FS_CHKP_RA_012 / RA_005** — CHKP 0x8C ("max root cap = 0x20") and 0x88 are 0 on 28 v3.14-native images;
 the 0x88-0x8F region co-varies. Finding #339.
- **FS_CHKP_RA_013** — the volume-state flags have more states than the 3-value {0x002,0x602,0x682} model.
 Finding #339.
- **MD_DATA_RA_005** — file_size@0x58 is solid, but alloc_size@0x60 cluster-alignment fails on ~20% of Insider
 extent rows (undecoded 0x40 value variant). PARTIAL.

## Bugs the audit caught *in itself* (and fixed)

- **HardLinkCount** read `vd+0x70` (usn_journal_id) not the real field at `vd+0x98` — a vacuous pass.
- **Versions compared as floats** (3.10 < 3.4); now (major,minor) tuples from string thresholds.
- **otbl_value / index_node** read one cluster, not the full 16 KiB page; off-by-one in the object loop.
- A size-filter regression briefly hid the CT_CTBL_010 mislabel — caught and restored.

Each was found by going byte-deep per probe group before trusting a green verdict — the discipline the audit
exists to enforce.

## New findings added to the register (now 343)

#337 (Container-Table failover pair roots 7/8 not index-bound), #338 (CT CSC offset correction),
#339 (CHKP 0x88-0x8F region co-varies + flags >3 states + 0x8C not constant). Plus scoped, *not-elevated*
single-image observations (Insider $EFS 732B vs 676) kept out of the register per the no-single-sample rule.
**2026-06-14 (step6/win11refs2gtargeted):** #340 hard-link mechanism, #341 WSL reparse tags + `$LXDEV`=8B,
#342 integrity = file_attrs 0x8000 (+ E43: `$SI+0x24` bit0 is delete-disposition, NOT integrity), #343 MLog
per-volume magic via reformat — registered as FN_LINK_002 / FS_REPS_RA_003 / MD_INTG_RA_001 / AP_LGFL_RA_008.

## Maintenance

Re-run `python3 analysis/reports/audit/audit_harness.py` to regenerate all matrices/dossiers/index from
`specs.jsonl` against the current corpus (~70 s). Add a claim by appending one spec line; the correspondence
gate flags any ref_id not in reference_table.
