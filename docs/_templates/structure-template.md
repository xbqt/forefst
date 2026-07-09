<!-- TEMPLATE: on-disk structure page. Copy into structures/, fill in, delete these comments.
 Rule: intro sentences FIRST, then the field-layout table near the top (like vbr.md).
 Every byte-level claim must match structure_reference.md (the audited master) — cite the section. -->

# <Structure Name> (<ABBR>)

<1–3 sentences: what this structure is, where it lives (fixed LCN / computed / which root / embedded in which value), and what depends on it. State the size in bytes if fixed.>

## Location

<Optional — only if the location is fixed or computed. e.g. "SUPB is at LCN 0x1E (physical). Its backups are at VolSize−2 and VolSize−3." Omit for embedded/derived structures.>

## Field Layout

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | n | <field> | <meaning; units; constants> |
| … | … | … | … |

<!-- For keyed B+-tree rows, use "## Key Format" + "## Value Format" instead (one table per variant). -->

## <Detail sections>

<Flags / bit-fields / enums / observed-value distributions as their own small tables. e.g. "## CHKP Flags", "## Subtable: per-cluster refcount bit fields".>

## Version Differences

<Consolidate all per-version variation here: legacy vs compact layouts, fields added/removed per version, size changes. Use a small `| Version | … |` table where it helps.>

## Forensic Relevance

<Why an investigator cares: what it proves, what it recovers, common mis-reads to avoid.>

## Parsing Notes

<Ordered steps or gotchas a parser must respect (endianness, container translation, key-flag dispatch, padding/alignment).>

## Static-Analysis Evidence

<Optional — the driver function(s) that read/write this structure, with build + address. e.g. "`RefsSetupUsnJournal` (win11 @1402acf6c) creates the type-0xF0 attribute." Keep to a function table or a short C snippet (5–10 lines).>

## Cross-References

- [<related page>](<rel/path.md>) — <why>
- Master reference: `structure_reference.md` §<X.Y>

## Evidence

<Prose: the driver functions (E2) and/or raw-disk measurements (RD) that back this page's claims; name the key finding IDs.>

<!-- No provenance footer. Add this page's row to ../audit_dates.tsv
     (page · status · evidence · findings · last_audited · note) — provenance lives there, not on the page. -->
