<!-- TEMPLATE: attribute / embedded sub-record page. Copy into attributes/, fill in, delete these comments.
 Preamble block in FIXED order. Cross-References is mandatory (even on stubs) to avoid island pages. -->

# $<NAME> <(disambiguation if the NTFS name misleads)>

**Type ID:** 0x<NN> · **Schema:** 0x<NNN> · **Versions:** <v3.x+ / v3.4–Insider / etc.> · **Evidence Level:** <E1/E2/E3/RD>

## Description

<What the attribute holds and its role. For NTFS-convention-only / name-mapping attributes with no ReFS
on-disk structure, say so explicitly and point to the real attribute (e.g. INDEX_ALLOCATION → INDEX_ROOT).>

## Sub-record Identification

| Field | Value |
|-------|-------|
| Marker | 0x80000001 (single-instance) / 0x80000002 (multi-instance) |
| Type code | 0x00<NN> |

<!-- Omit this section for attributes that are not embedded sub-records. -->

## Value Format

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | n | <field> | <meaning> |

<!-- Add "## Key Format" above if the attribute is a keyed table row. Omit both on pure name-only stubs. -->

## <Variant / version sections>

<Per-tag, per-version, or observed-value tables (e.g. reparse tag list, $LX* EA names).>

## Forensic Application

<Optional — what an analyst extracts from this attribute and how.>

## Cross-References

- [<related page>](<rel/path.md>) — <why>
- Master reference: `structure_reference.md` §<C.x / F.2>

## Evidence

<Prose: the driver functions (E2) and/or raw-disk measurements (RD) that back this page's claims; name the key finding IDs.>

<!-- No provenance footer. Add this page's row to ../audit_dates.tsv
     (page · status · evidence · findings · last_audited · note) — provenance lives there, not on the page. -->
