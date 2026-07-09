# $REPARSE (Reparse Index)

`$REPARSE` (schema 0x160, embedded type 0x60) is the **reparse-point index attribute** — the schema for
the global reparse index stored in the system table at **OID 0x540 / 0x541**. It is distinct from
[$REPARSE_POINT](REPARSE_POINT.md) (type 0xC0), which holds the actual per-file reparse data.

## What it indexes

The reparse index is a **system table** (OID 0x540, with a byte-identical mirror at 0x541), keyed by
**key type 0x01**. Each entry maps a **reparse tag + object OID** pair, giving a fast lookup of every
file that carries a given reparse type. It does **not** appear as an embedded sub-record in user objects
— it is the index, not the per-file data. The entry count is volume-dependent. The full on-disk table
layout is documented in [Reparse Points](../structures/reparse_points.md).

## Cross-references

- [$REPARSE_POINT](REPARSE_POINT.md) — the per-file reparse data (type 0xC0)
- [Reparse Points](../structures/reparse_points.md) — the OID 0x540 index-table layout
- [System OIDs](../structures/system_oids.md) — OID 0x540 / 0x541

## Evidence

Schema 0x160 / type 0x60 and the OID 0x540/0x541 index are confirmed in the decompiled driver (E2 —
`InitializeReparseIndexTable`) and on the raw-disk corpus (RD). Finding: **FS_REPS_RA_001, FS_OTBL_RA_005**. See
[how this was verified](../methodology.md).
