# Probe menu — the fixed contract for authoring claim specs

Every claim is audited by mapping it to ONE probe from this menu plus its arguments. A spec row in
`specs.jsonl` (one JSON object per line) has:

```json
{"ref_id":"<id from reference_table.csv>","class":"STRUCTURAL|PURE-RD-LAYOUT|ABSENCE|BEHAVIORAL|LITERATURE",
 "desc":"<one-line restatement of the claim being tested>","axis":"cluster|version|checksum|corpus|none",
 "static_fn":"<forefst fn or driver fn, or null>","probe":["<name>",<args...>],
 "applicability":{"checksum":"CRC64|SHA256|None","cluster":4096|65536,"version_min":3.4},
 "scoped_exceptions":{"<basename>":"<reason + knowledge-link>"},
 "explanation":"<why this probe proves the claim; cite the structure_reference.md line / decomp>",
 "links":["#NNN","E27"]}
```

`applicability` is optional (omit = all ReFS images). `scoped_exceptions` and `links` optional.

## Probes

| probe | args | tests | use for |
|---|---|---|---|
| `vbr_u64` | `off, expected` | VBR u64 at `off` == `expected` | VBR 8-byte fields |
| `vbr_int` | `off, size, expected` | VBR int (size∈{1,2,4,8}) at `off` == `expected` | any VBR field |
| `chkp_int` | `off, size, expected` | newest CHKP page int at `off` == `expected` | checkpoint header fields |
| `page_const` | `off, expected` | OT-root MSB+ page u32 at `off` == `expected` | page-header layout constants |
| `cpc` | — | clusters-per-container == 16384 (4K) / 1024 (64K) | container geometry |
| `si_zero` | `off, size` | $SI field at `off` is **0 on every** user object | "field X unused/always 0" ABSENCE |
| `si_aggmax` | `off, size, bound, plaus_hi` | max **plausible** (≤`plaus_hi`) $SI field ≤ `bound`; bigger reads discarded as field-overlap | bounded-count ABSENCE (e.g. HardLinkCount≤1) |
| `hlc_max` | — | specialization of `si_aggmax` for HardLinkCount | hard-link absence |
| `absent` | `needle` | UTF-16LE `needle` occurs **0×** across all metadata pages | "name/string is not on disk" ABSENCE |
| `cite` | — | no on-disk obligation; proof = the cited source in proof_links | LITERATURE |

## Rules for authoring (enforced by review)

1. **The probe must test the SPECIFIC asserted value**, never a tautology. A probe that passes regardless of
 the claim is invalid. Quote the byte/decomp evidence in `explanation`.
2. **Offsets are verified against `structure_reference.md` (or decomp) before authoring** — do not guess. If
 the offset is version-dependent, set `version_min` / `applicability` accordingly, or split into two specs.
3. **Plausibility guards are mandatory for aggregate probes** — a raw offset read is not a probe (the HLC bug:
 `$SI+0x70` overlapped a USN-shaped field → billions). Use `si_aggmax` with a `plaus_hi`, never raw max.
4. **A CONTESTED verdict is a stop sign, not a result.** Investigate against bytes: is it a probe bug
 (fix probe), a scoped degenerate image (add `scoped_exceptions` with reason + knowledge-link), or a real
 contradiction (escalate per the contradiction protocol — one test does not overturn the thesis)?
5. **No single-sample claims.** A claim needs the probe to hold across ≥3 independent groups (CONFIRMED) or
 ≥2 + static (CORROBORATED). The dossier states `n_confirmations` and, if short, `to_confirm`.

## Verdict ladder (computed by the harness)

`SATURATED` (all applicable pass, every one independent) · `CONFIRMED` (≥3 independent groups) ·
`CORROBORATED` (2 groups) · `RD-LIMITED` (1 group) · `CONTESTED` (any non-scoped FAIL) ·
`UNTESTED` (no applicable images) · `CITED` (literature).

## Axis (drives applicability + how "independent" is counted)

`cluster` (4K vs 64K discriminates) · `version` (3.4 vs 3.14 vs insider) · `checksum` (CRC64 vs SHA256 vs none) ·
`corpus` (must hold everywhere) · `none` (invariant).
