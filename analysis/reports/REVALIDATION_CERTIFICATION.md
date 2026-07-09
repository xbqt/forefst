# forefst v3.6.0 — Re-validation Certification

**Date:** 2026-07-04 · **Tools:** `forefst.py` + `refsanalysis.py` **v3.6.0** · **Supersedes:** the v3.5.0
`CERTIFICATION.md` (CLI-migration scope).

## Scope
The v3.6.0 first-audit enhancement set — the `recyclebin` subcommand, the 38-column files CSV (HardLinkNames,
FileId, HomeOid, IsSparse, InternalFlags), resident + CoW file extraction, the `deleted --slack` owning-path, the
`is_resident` residency fix, and the per-name-MACB hard-link timestomp signal (`HARDLINK_MACB_MISMATCH`,
finding `FN_LINK_003`) — re-validated across the corpus, with a full reference ↔ docs ↔ help ↔ output ↔ disk
cross-consistency pass.

## Verdict: CERTIFIED SOUND.
Every tool option runs correctly — structurally and, where it emits content, byte-for-byte — across the corpus; the
tool, the documentation, the finding register, the in-tool help, the samples, the website, and the version metadata
are mutually consistent. The re-validation found only documentation-currency gaps (now corrected); the tool code
required no change.

## Evidence
- **Option matrix:** the full `forefst` (20) + `refsanalysis` (11) subcommand set, with every applicable option, on
  75 diverse images (ReFS 3.4–3.14, insider, 4K/64K clusters, CRC64/SHA-256, dedup, compression, WSL, EFS, hard-link,
  snapshot, integrity-stream) plus the negative controls, and a bounded pass over 16 further large images (up to 15 TB).
  Result: 0 crashes on ReFS volumes; the negative controls (NTFS / BitLocker / non-ReFS) are refused gracefully.
- **Content correctness:** `extract` writes exactly the declared file size on resident, CoW, and non-resident files
  (byte-compared to a direct cluster read); `recyclebin` decodes `$I` original-path / deletion-time / size verified
  against the raw `$I` bytes.
- **Cross-journal consistency:** the USN journal, the durable metadata log (MLog), and the per-file `$SI` timestamps
  are three independent records of the same events; they agree across the corpus. The only observed USN-vs-`$SI`
  differences are benign write-lag (a few seconds between the create event and the timestamp), not tampering.
- **Reference ↔ tool ↔ docs:** the code matches the finding register byte-for-byte (residency predicate, the
  per-name-MACB signal, the extract paths, the column set); the redo-opcode and schema tables match the reference;
  the documentation and help match the tool and the register.

## Gates (all green)
`verify_docs_tools` 452 / 0 · `verify_tool_tables` 22 / 0 · `check_links` 0 broken · docs index up-to-date ·
`verify_claim --regress` 14 / 14 · fixture 10 / 10 · finding register 433 rows across all three copies ·
website 79 pages / 0 artifacts · both tools report v3.6.0.
