# $REPARSE (Reparse Index)

`$REPARSE` (embedded type 0x60, schema 0x160) is the **reparse-point index** — the schema behind the global
reparse index ReFS keeps in the system table at **OID 0x540**, with a byte-identical failover mirror at
**0x541**. It is distinct from [$REPARSE_POINT](REPARSE_POINT.md) (type 0xC0): `$REPARSE` is the *index that
lists which files are reparse points*, while `$REPARSE_POINT` holds *the per-file reparse data itself*.

## What it indexes

The reparse index is a **pure existence index** — each row is a fixed **24-byte key with a 0-byte value**,
so the key *is* the entry. Every key carries the object's **reparse tag** and its **File ID** (the creation
directory's OID plus a per-directory ordinal; ReFS files have no OID of their own). Because the rows are
**sorted by reparse tag**, "list every file that carries reparse tag X" — every symlink, junction, mount
point, WSL special file, or WOF-compressed file on the volume — becomes a fast range-scan instead of a
whole-tree walk. The full 24-byte key layout is documented in
[Reparse Points](../structures/reparse_points.md).

## Why it matters forensically

The index is the single fastest way to answer *"what redirections and special files exist on this volume?"*
— it enumerates every reparse-tagged object without walking the directory tree. The tag multiset in the
index always matches the actual on-disk reparse tags, an invariant a tool can cross-check the two against.
And because each key records the file's **creation-directory OID** (frozen even after the file is moved),
the index also ties every reparse object back to where it was created. See
[Reparse Points](../structures/reparse_points.md) for the per-tag detail and the reparse-tag table.

## Cross-references

- [$REPARSE_POINT](REPARSE_POINT.md) — the per-file reparse data (type 0xC0)
- [Reparse Points](../structures/reparse_points.md) — the OID 0x540 index-table layout and reparse-tag table
- [System OIDs](../structures/system_oids.md) — OID 0x540 / 0x541
- [File IDs](../concepts/file_ids.md) — the creation-OID + ordinal identity carried in each key

## Evidence

Schema 0x160 / type 0x60 and the OID 0x540 / 0x541 index are confirmed in the decompiled driver (E2 —
`InitializeReparseIndexTable`) and on the raw-disk corpus (RD). Finding: **FS_REPS_RA_001, FS_OTBL_RA_005**. See
[how this was verified](../methodology.md).
