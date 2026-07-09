# Documentation Conventions

These rules keep `docs/` consistent and forensically trustworthy. Pages are the human-readable layer over the
audited master reference; they must never diverge from it.

## Source of truth

- **`structure_reference.md`** (the project's upstream byte-level reference; not bundled in this repo) is the single byte-level source of truth. Every
 offset/size/constant/version-gate on any page must match it. If you find a discrepancy, the *master* is right
 and the page is wrong (fix the page) — unless you re-verify against disk/decompilation and correct both.
- Claims are graded by **evidence level**: `E1` (string literal), `E2` (decompiled / PDB symbol), `E3`
 (structural inference), `RD` (raw-disk verified). State the level; prefer E2/RD for load-bearing claims.
- Reference audited claims by their
 `reference_table.csv` ref_id where useful.

## Page structure

Use the matching template in [`_templates/`](_templates/):
[structure](_templates/structure-template.md) · [concept](_templates/concept-template.md) ·
[attribute](_templates/attribute-template.md).

- **Intro first, then the field-layout table near the top** — 1–3 introductory sentences, then the
 `| Offset | Size | Field | Description |` table (the "at a glance" block, as in
 [vbr.md](structures/vbr.md)). Registry/prose intros must not push the layout table far down the page.
- Pages carry **no provenance footer**. All per-page provenance — verification status, evidence level,
 key `reference_table.csv` finding ids, and the last-audited date — lives centrally in
 **[`audit_dates.tsv`](audit_dates.tsv)** (one row per page), which is what `KNOWLEDGE_MAP.md` keys off.
 Add a row there for every new page, and update it when a page is re-audited. Pages should keep a body
 **`## Evidence`** section (prose: which driver functions / disk measurements back the page).
- **Cross-References is mandatory** on every page (prevents "island" pages with no inbound/outbound links).

## House style

- `--` for em-dash; little-endian assumed for all on-disk integers; hex offsets lower-case `0x..`.
- When you correct a page, **replace the wrong value with the correct one** — state only the current
 value and its proof. Do **not** leave a callout or inline note naming the old value ("previously X",
 "corrected from Y", "was mislabelled"); that error history goes in the session report under
 `analysis/reports/` (with the before→after and evidence), not in the doc.
- Use **relative** markdown links (`../concepts/x.md`); run the link check before publishing.
- One directory = one `README.md` index; add a page's row to its directory README when you create it.

## Where things live

| Kind | Directory |
|------|-----------|
| On-disk byte structures | `structures/` |
| Attribute / embedded sub-record types | `attributes/` |
| Mechanisms, forensic methodology, version evolution | `concepts/` |
| Worked investigator walkthroughs + raw tool dumps | `examples/` |
| Tool capability references | `tools/` |
| The audit programs (claim audit + structure-ref audits) | `audit/` |
| Regenerated gate outputs | `reports/` |
| Central topic→file index | `KNOWLEDGE_MAP.md` |

See [`KNOWLEDGE_MAP.md`](KNOWLEDGE_MAP.md) to find which file documents any given topic before adding a new one.
