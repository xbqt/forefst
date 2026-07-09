# Schema Table

The Schema Table (roots #3/#9, schema 0xe060) is self-describing: it contains one entry per table type used by the volume. Each entry fixes the key-comparison rules that let the generic B+-tree engine order rows without knowing their meaning.

## Key format — 8 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Schema ID (u32) | Unique schema identifier |
| 0x04 | 4 | Zero padding (u32) | Always 0 |

## Value — schema definition (80 bytes, 20 × u32)

Each entry's value is an 80-byte definition (20 × u32) describing the table's layout. It is byte-identical across versions for a given schema ID. Notable fields:

| Field | Byte | Meaning |
|-------|------|---------|
| `u32[0]` | +0x00 | Definition size (0x50) |
| `u32[1]` | +0x04 | Key-descriptor size (0x18, constant) |
| `u32[6]` | +0x18 | Value-descriptor size (0x38, constant) |
| `u32[7]` | +0x1C | Key-comparison-rules selector (see below) |
| `u32[9]` | +0x24 | Self schema ID |
| `u32[18]` | +0x48 | System flag (0x01) |

The field that fixes "the key-comparison rules" is **`u32[7]` (byte +0x1C) — the key-comparison-rules selector**, a small enum (disk-observed 1..0x11 across schemas), **not a bitfield**. The driver bounds-checks it `< 0x15` and uses it to index a key-rules dispatch table. For 0xe040 (Parent-Child Table) it is `8` → `CmsRulesPARENT_CHILD_LINK`; for 0xe0c0 (Container Table) it is `10`; for 0xe130 (Heat Engine) it is `17`. The schema object is registered by `RegisterSchema`; the rules table is read by `GetKeyRulesInternal`.

## Total schema count

Across all versions, there are **36 distinct schema IDs** (18 system + 18 attribute). Any single volume has fewer, since schemas are added and retired across versions.

### Entry counts by version

| Version | System schemas | Attribute schemas | Total |
|---------|---------------|-------------------|-------|
| v3.4 | 15 | 12 | 27 |
| v3.7 | 15 | 15 | 30 |
| v3.9 | 16 | 15 | 31 |
| v3.10 | 15 | 15 | 30 |
| v3.14 | 13 | 16 | 29 |
| Insider | 14 | 16 | 30 |
| Upgraded (union) | up to 18 | up to 18 | up to 36 |

Totals are the on-disk schema-table leaf-row count (system ID ≥ 0xe000, attribute ID < 0xe000). The pre-3.14 attribute count includes **two legacy schemas `0x04` and `0x06`** (present on every v3.4–v3.10 volume, retired at v3.14): v3.4 = 0x04,0x06 + 0x110–0x1A0 (10) = 12; v3.7/v3.9/v3.10 = 0x04,0x06 + 13 = 15. Upgraded v3.4→v3.14 volumes keep 0x04/0x06, so a "union" volume can reach 36.

## System schemas (18 distinct)

| Schema ID | Name | Purpose | Versions Present |
|-----------|------|---------|------------------|
| 0xe010 | Allocator Table | Three-tier allocator (roots 1, 2, 12) | v3.4-Insider |
| 0xe030 | Object ID Table | OID-to-LCN mapping (roots 0, 5) | v3.4-Insider |
| 0xe040 | Parent-Child Table | Directory relationships (root 4) | v3.4-Insider |
| 0xe050 | Object Data Table | Vestigial (legacy) | v3.4-v3.9 |
| 0xe060 | Schema Table | Self-describing schemas (roots 3, 9) | v3.4-Insider |
| 0xe070 | Reserved / Placeholder | Vestigial (legacy) | v3.4-v3.10 |
| 0xe080 | Integrity State | Per-extent integrity tracking (root 11) | v3.4-Insider |
| 0xe090 | Upcase / Logfile Info | Unicode case mapping + MLog metadata | v3.4-Insider |
| 0xe0b0 | Block Refcount | Shared block reference counts (root 6) | v3.4-Insider |
| 0xe0c0 | Container Table | Virtual-to-physical mapping (roots 7, 8) | v3.4-Insider |
| 0xe0d0 | Trash Table | Async deletion queue (OID 0x0D) | v3.4-Insider |
| 0xe0e0 | System Directory Entry List | Vestigial (legacy) | v3.4-v3.10 |
| 0xe0f0 | System File Stream | Vestigial (legacy) | v3.4-v3.9 |
| 0xe100 | Container Index | Container lookup by state (root 10) | v3.4-Insider |
| 0xe110 | Read Cache Metadata | Read-ahead caching metadata | v3.4-Insider |
| 0xe120 | Candidate Table (Dirty Range) | Dirty page tracking for checkpoint | v3.9-Insider |
| 0xe130 | Heat Engine | Block tier classification (hot/warm/cold) | v3.10-Insider |
| 0xe140 | Volume Attestation Table | TPM-bound attestation data | Insider only |

## Attribute schemas (18 distinct)

| Schema ID | Embedded Type | Since | Attribute / Role |
|-----------|--------------|-------|-----------------|
| 0x110 | 0x10 | v3.4 | Directory Entry List |
| 0x120 | 0x20 | v3.4 | File Stream |
| 0x130 | 0x30 | v3.4 | $FILE_NAME — directory entry, keyed by the full long name (ReFS has **no** 8.3 short names) |
| 0x140 | 0x40 | v3.4 | $FILE_NAME (long-name entries; the largest attribute population) |
| 0x150 | 0x50 | v3.4 | $VOLUME_INFORMATION (label, version, flags) |
| 0x160 | 0x60 | v3.4 | Reparse Index |
| 0x170 | 0x70 | v3.4 | $REPARSE_POINT (per-file reparse data) |
| 0x180 | 0x80 | v3.4 | $DATA (file data streams, extent references) |
| 0x190 | 0x90 | v3.4 | $STANDARD_INFORMATION |
| 0x1A0 | 0xA0 | v3.4 | $INDEX_ROOT |
| 0x1B0 | 0xB0 | v3.7 | $SNAPSHOT (stream snapshot metadata) |
| 0x1C0 | 0xC0 | v3.7 | $REPARSE_POINT (v3.7+ format) |
| 0x1D0 | 0xD0 | v3.7 | $EA_INFORMATION |
| 0x1E0 | 0xE0 | v3.14 | $EA body (WSL $LXUID/$LXGID/$LXMOD/$LXDEV) |
| 0x1F0 | 0xF0 | v3.14 | $LOGGED_UTILITY_STREAM data |
| 0x200 | 0x100 | v3.14 | $LOGGED_UTILITY_STREAM ($EFS metadata; the name $CBW4 in prior work is a fabrication, see [$EFS](../attributes/EFS.md)) |
| 0x004 | -- | v3.4-v3.10 | Legacy fixed-format (descriptor_size=0x50) |
| 0x006 | -- | v3.4-v3.10 | Legacy variable-format (anomalous properties) |

## Naming rule

For attribute schemas: **schema ID = embedded type code + 0x100**.

Example: embedded code 0x80 ($DATA) yields schema 0x180.

The `$FILE_NAME` schemas (0x130, 0x140) are retained-numbering entries that carry the directory-entry /
long filename. **ReFS has no 8.3 short names** — there is no separate short-name entry and no short-name
field (refs.sys has no 8.3-generation code; all `8dot3`/`ShortName` code lives in fsutil.exe; `fsutil file
setshortname` returns "A local NTFS volume is required"). Directory entries carry only the long name. ReFS
also does **not** duplicate the four MACB timestamps in a name entry the way NTFS does in `$FILE_NAME`, so
the NTFS `$SI`-vs-`$FILE_NAME` timestomp cross-check does **not** exist on ReFS **for a single-named file**. A
**hard-linked** file is the exception: each name is a separate type-0x30 row carrying its own MACB (value
+0x10/+0x18/+0x20/+0x28), so a name-scoped timestomp leaves the sibling names at the true birth — a ReFS-only,
journal-independent cross-check (`FN_LINK_003`; forefst's `HARDLINK_MACB_MISMATCH` signal). *(The exact embedded-code
mapping of 0x130/0x140 — the +0x100 rule vs. the 0x38/0x39 retained-numbering exception — is discussed in
the thesis $FILE_NAME section; it is not resolved here.)*

## Four concepts to keep separate

1. **Attribute name** -- the Unicode string (`$STANDARD_INFORMATION`, `$DATA`)
2. **Definition (Type) code** -- the in-driver lookup handle (e.g., 0x10 for $SI)
3. **Embedded code** -- the on-disk key prefix (e.g., 0x90 for $SI)
4. **Schema identifier** -- the Schema Table key (e.g., 0x190 for $SI)

The Definition code and Embedded code are independent numbering systems. For $DATA they coincide (both 0x80); for $STANDARD_INFORMATION they differ (0x10 vs 0x90).

## Schema names

These schema functions are version-independent — the schemas have always had the same function across v3.4 through Insider.

| Schema | Prior Name | Correct Name | Notes |
|--------|-----------|-------------|-------|
| 0x160 | "Security Descriptor" | **Reparse Index** | `InitializeReparseIndexTable` creates OIDs 0x540/0x541 with schema 0x160. |
| 0x1B0 | "Index Root" | **$SNAPSHOT** | PDB symbol; introduced at v3.7 with snapshot support. |

Schema 0x160 indexes reparse points (symlinks, junctions, WSL device nodes) globally — it has no relationship to security descriptors. The actual security descriptors reside in OID 0x530, which is a schema-less stream-type table (see [Security Descriptors](security_descriptors.md)).

The 36 distinct schema IDs were named using three sources: PDB symbols for 24, string literals for the attribute names, and structural inference for 4 legacy schemas.

## Failover

Root #3 (table ID 0x01) and root #9 (table ID 0x06) form a failover pair.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) -- roots #3 and #9 in the root pointer list
- [Object Table](object_table.md) -- schema 0xe030 governs its key comparison
- [Container Table](container_table.md) -- schema 0xe0c0
- [Container Index](container_index.md) -- schema 0xe100
- [System OIDs](system_oids.md) -- OIDs for system tables referencing these schemas

## Evidence

The Schema Table identity (roots #3/#9, table IDs 0x01/0x06, schema 0xe060, virtual addressing) is decompiled
from the `CmsSchemaTable` class (E2) and parsed on every analysed image (RD). The key/value layout and the
`u32[7]` key-comparison-rules selector are decompiled from `RegisterSchema` / `GetKeyRulesInternal` (E2) and
corroborated against the driver's baked-in schema table, which reproduces the disk values exactly (RD). `u32[7]` is a key-comparison-rules enum (disk-observed 1..0x11), bounds-checked `< 0x15` and used to index the key-rules dispatch table. The 36 distinct schema IDs, the per-version
entry counts, and the naming corrections (0x160 = Reparse Index, 0x1B0 = $SNAPSHOT) are raw-disk re-measured
across the corpus (RD) and named from PDB symbols and string literals (E1/E2). The "no 8.3 short names" and
"no `$SI`-vs-`$FILE_NAME` timestomp cross-check for a single-named file" facts are decompiled (E2); the per-name
hard-link exception (each name carries its own MACB, so hard-link names can diverge) is `FN_LINK_003` (RD). See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

Findings: **FS_SCHM_RA_008, FS_SECD_RA_003, FS_SCHM_RA_005, FS_SCHM_RA_010** (naming corrections 0x160/0x1B0), **MD_TS_RA_005, MD_UNSUP_RA_001** (no 8.3 short names), **FS_SCHM_001**,
**FS_SCHM_RA_008** (36 schema IDs), **FS_PCTB_RA_001** (`u32[7]` key-rules selector).
