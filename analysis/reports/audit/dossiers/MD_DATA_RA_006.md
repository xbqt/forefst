# Dossier — MD_DATA_RA_006 (BEHAVIORAL)

> **SUPERSEDED 2026-06-19 — MD_DATA_RA_006 is CONFIRMED (content-aware re-verification).** The 2026-06-18
> UNCONFIRMABLE verdict below is overturned: the local `alloc=0/size=0` type-0x40 **stub IS a real on-disk
> form** (synthetic/attributes images, e.g. `xbpt_` — 29 on win11refs2tspecials, 7 on attributes), with the
> real extents in the home dir; the fsutil-created case (win11refs2gtargeted) has NO local 0x40 and is reached
> via the home backref. Both forms are valid — the stub is not refuted. See
> `analysis/reports/hardlink_false_positive_verification_2026-06-19.md` + master §J. (Dated body kept below.)


**Claim (this audit tests):** Hardlink directories contain local type 0x40 stub with alloc_size=0 and file_size=0 — extent data only in original directory

**Canonical claim (reference_table.csv):** Metadata: Hardlink directories contain local type 0x40 stub with alloc_size=0 and file_size=0 — extent data only in original directory

**Re-verification verdict (all-disk, 2026-06-18):** **UNCONFIRMABLE** — Hard-link 'local stub with alloc_size=0/file_size=0' — could not isolate a hard-link stub vs. real entry deterministically in the corpus; the only real-hardlink image (win11refs2gtargeted) has the FN_LINK_002 model where each name is a separate non-resident type-0x30 entry (84B value), not a distinct zero-size type-0x40 stub. Hard-link framing predates FN_LINK_002/#340.

**Original audit verdict:** STATIC-CITED (disk held 0/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** N/A

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- N/A
- Behavioral (hardlink stub). Cited.

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/MD_DATA_RA_006.csv`
- corrected registry note: Stub serves as placeholder; real extents obtained via remote OID lookup. Both stubs and real entries share the type-0x40 extent key. [Hard-link framing predates FN_LINK_002/#340; the type-0x30 value+0x00 is a per-directory child ordinal]

## Proof links
- `proofs/validation/MD_DATA_RA_006.csv` (matrix) — 
