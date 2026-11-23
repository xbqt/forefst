# $REPARSE (Reparse Index)
<!-- site: description "The volume's reparse-point index: a system table (OID 0x540 / 0x541) listing which files are reparse points." -->

The reparse index is a system table (table schema 0x160): it is not an attribute and never an embedded sub-record
of an object's record.

- It is the global reparse index ReFS keeps in the system table at OID 0x540, held as a failover
  pair with OID 0x541 (neither copy is a primary; the two hold the same rows on every volume measured).
- It is distinct from [$REPARSE_POINT](REPARSE_POINT.md) (type 0xC0): `$REPARSE` is the *index that lists which
  files are reparse points*, while `$REPARSE_POINT` holds *the per-file reparse data itself*.

| Property | Value |
|----------|-------|
| Table schema | 0x160, the reparse index ([Schema Table](../structures/schema_table.md)) |
| Instances | — not a per-object sub-record: one row per reparse-tagged object in the index table |
| Where it lives | the system table at OID 0x540, a failover pair with OID 0x541 |
| Size | each row: a fixed 24-byte key with a 0-byte value |
| Added in | 3.4 or earlier: present on every format read (3.4, Windows 10 1803, driver 17134, is the oldest held) |

## What it indexes

The reparse index is a pure existence index — each row is a fixed 24-byte key with a 0-byte value, so the key *is*
the entry.

- Every key carries the object's reparse tag and its File ID (the creation directory's OID plus a per-directory
  ordinal; ReFS files have no OID of their own).
- Because the rows are sorted by reparse tag, "list every file that carries reparse tag X" — every symlink,
  junction, mount point, WSL special file, or WOF-compressed file on the volume — becomes a fast range-scan instead
  of a whole-tree walk.

The full 24-byte key layout is documented in [Reparse Points](../structures/reparse_points.md).

## Why it matters forensically

The index is the fastest way to list the redirections and special files on the volume: it enumerates every
reparse-tagged object without walking the directory tree.

- The index holds one row per reparse-bearing object, not per name (the names of a hard-linked file share one row),
  and each row carries the same tag as the object's 0xC0 attribute: a tool can cross-check the index against the
  reparse tags it finds in the records.
- Because each key records the file's creation-directory OID (unchanged even after the file is moved), the index also
  ties every reparse object back to where it was created.

See [Reparse Points](../structures/reparse_points.md) for the per-tag detail and the reparse-tag table.

## Cross-references

- [$REPARSE_POINT](REPARSE_POINT.md) — the per-file reparse data (type 0xC0)
- [Reparse Points](../structures/reparse_points.md) — the OID 0x540 index-table layout and reparse-tag table
- [System OIDs](../structures/system_oids.md) — OID 0x540 / 0x541
- [File IDs](../concepts/file_ids.md) — the creation-OID + ordinal identity carried in each key

## Evidence

Schema 0x160 and the OID 0x540 / 0x541 index are read in the decompiled driver
(`InitializeReparseIndexTable`, which creates the pair with `MsCreateDurableFailoverTableObject`) and measured on the
corpus. The row is inserted once per object by `RefsCreateReparsePointInternal` when the 0xC0 attribute is created,
and deleted by `RefsDeleteReparsePointInternal` / `RefsRemoveReparsePoint`. The page is documented against the
project's claim register. See [how this was verified](../methodology.md).

The measurements behind the text:

- The two copies of the pair hold the same rows on 117 of 117 corpus volumes.

<!-- findings: FS_OTBL_RA_005, FS_REPS_RA_001 -->
