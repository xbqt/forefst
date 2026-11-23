# Security Descriptors

ReFS uses a centralised, content-addressed security model:

- a SecurityId stored with each file maps directly to OID 0x530, the Security Descriptors table, where the
  actual `SECURITY_DESCRIPTOR` structures reside;
- identical permission sets share a single descriptor entry rather than being duplicated per file.

## SD table key — 16 bytes

OID 0x530 is a B+-tree table of schema 0x140, the schema the driver gives it when it creates it
(`RefsSecurityInitialize`). Each entry is keyed by the 16-byte structure below. (Schema 0x160 is the Reparse Point
Index's, not this table's.)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Value length (u64) | The row's value length (the key echoes it) |
| 0x08 | 4 | Security ID high (u32) | Collision generation (see below) |
| 0x0C | 4 | Security ID low (u32) | SD content hash (see below) |

## Value layout — 12-byte wrapper + SECURITY_DESCRIPTOR_RELATIVE

The value is a 12-byte ReFS wrapper followed by a standard Windows self-relative security descriptor:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | SD hash (u32) | Hash of the `SECURITY_DESCRIPTOR` content; **equals the SecurityId low 32 bits** |
| 0x04 | 4 | Generation (u32) | **Equals the SecurityId high 32 bits**; starts at 1, incremented only to disambiguate hash collisions |
| 0x08 | 4 | Entry size (u32) | Total value length (= key[0x00]) |
| 0x0C | var | SECURITY_DESCRIPTOR_RELATIVE | Standard Windows self-relative SD (see below) |

### SECURITY_DESCRIPTOR_RELATIVE (at value+0x0C)

Standard Windows self-relative format. Offsets are relative to the SD start (= value+0x0C):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 1 | Revision | Always 1 |
| 0x01 | 1 | Sbz1 | 0 |
| 0x02 | 2 | Control (u16) | `SE_*` flags (`SE_SELF_RELATIVE` 0x8000 always set; `SE_DACL_PRESENT` 0x0004; `SE_DACL_PROTECTED` 0x1000; `SE_SACL_PRESENT` 0x0010; ...) |
| 0x04 | 4 | Owner offset (u32) | Offset to owner SID (0 = none) |
| 0x08 | 4 | Group offset (u32) | Offset to group SID |
| 0x0C | 4 | SACL offset (u32) | Offset to SACL (present iff `SE_SACL_PRESENT`) |
| 0x10 | 4 | DACL offset (u32) | Offset to DACL (present iff `SE_DACL_PRESENT`) |

**SID** (at an offset): `Revision(1) + SubAuthorityCount(1) + IdentifierAuthority(6, big-endian) + SubAuthority[count](4 each)`, rendered as `S-1-<auth>-<sub...>`.

**ACL** (DACL/SACL): `Revision(1) + Sbz1(1) + AclSize(2) + AceCount(2) + Sbz2(2)`, followed by `AceCount` ACEs.

**ACE**: `AceType(1) + AceFlags(1) + AceSize(2) + AccessMask(4) + TrusteeSID`. Common types:
ACCESS_ALLOWED (0x00), ACCESS_DENIED (0x01), SYSTEM_AUDIT (0x02). AccessMask 0x001F01FF = full control.

## Resolution chain

A file reaches its descriptor through its SecurityId. Where that SecurityId lives depends on where the
file's record sits — embedded in its name row, or split out into a type-0x40 backing by a move or a hard link:

```text
Embedded record: directory entry value offset 0x50 (SecurityId, u64)
Split record:    type-0x40 backing record value offset 0x50 (SecurityId, u64)
 -> OID 0x530 (Security Descriptors table)
 -> SECURITY_DESCRIPTOR (Owner SID, Group SID, DACL, SACL)
```

A file whose record is embedded carries the SecurityId inline at value offset 0x50. A split record carries it
in the file's own **type-0x40 backing record** — the file's `$SI` / stream-summary, keyed by (home-dir OID +
FileID) — at backing value offset 0x50, **not** through the Object Table (a file has no Object-Table OID of its
own).

This is a single-table model. `RefsSecurityInitialize` opens only OID 0x530
(`MsInitializeWellKnownObjectId(0x530, ...)`). The security load/cache/find functions
(`RefsLoadSecurityDescriptor`, `RefsCacheSharedSecurityBySecurityId`, `RefsSecurityGetDescriptorById`)
resolve a SecurityId directly in OID 0x530 via VCB+0xb0. OID 0x520 (the FS Metadata directory) is not
involved in security resolution.

## SecurityId = (generation << 32) | hash32(SD) — content-addressed dedup

The 64-bit SecurityId is **not opaque**: its low 32 bits are a content hash of the security descriptor,
and its high 32 bits are a collision generation. Because the SecurityId embeds the SD hash, security
dedup is **content-addressed** — identical descriptors produce the same SecurityId low half on every volume, and
the same SecurityId wherever no hash collision raised the generation.

Distinct descriptors that appear on multiple images carry the *same* SecurityId-low on all of them —
only possible if the low 32 bits are a deterministic content hash, not a per-volume counter. The high
32 bits stay constant at 1 unless a hash collision forces the generation to increment.

The hash is the NTFS `$Secure` SD-hash, not zlib-CRC32 — ReFS reuses the NTFS descriptor hash:

```text
h = 0
for each little-endian u32 dword d in the SECURITY_DESCRIPTOR:
    h = (d + ROL(h, 3)) & 0xFFFFFFFF
```

`GetSecurityIdFromSecurityDescriptorUnsafe` returns a `_SECURITY_HASH_KEY` and calls
`RefsSecurityFindMatchingDescriptor` (the dedup lookup against VCB+0xb0, the OID 0x530 table): a new SD
is hashed and matched against existing entries before a new SecurityId is created.

### Worked example (SecurityId 0x10a9f9562)

```text
key:   size=88 pad=0 secid_hi=0x01 secid_lo=0x0a9f9562
value: hash=0x0a9f9562 generation=1 size=88 | SD:
       rev=1 control=0x8004 (SE_DACL_PRESENT|SE_SELF_RELATIVE)
       owner = S-1-5-32-544 (BUILTIN\Administrators)
       group = S-1-5-18 (SYSTEM)
       DACL  = 1 ACE: ACCESS_ALLOWED, mask=0x001F01FF (full control), trustee S-1-5-18
```

`hash32(SD) = 0x0a9f9562` via the ROL-3 algorithm above — matching both the SecurityId low and the
wrapper hash.

## Centralized model and forensic value

This is the same centralized, content-addressed security model NTFS uses (`$Secure`): identical
permission sets share a single descriptor entry, keyed by the SD hash, rather than being duplicated per
file. Because the SecurityId embeds the SD hash, the *same permissions yield the same SecurityId on any
ReFS volume* (unless a hash collision raised the generation there), so a SecurityId identifies a permission set across volumes. A SecurityId can be
matched to a known descriptor without reading the descriptor body. The stored hash equals the hash recomputed
over the descriptor's bytes on every descriptor of the corpus (4,405 on 124 volumes), so a descriptor where the two
differ was not left that way by any write measured: treat it as damaged or edited.
Changing a file's permissions either reuses an existing SecurityId (if the new descriptor hashes to an
existing entry) or creates a new one.

The default descriptor applied to new objects at format time is built by
`InitializeDefaultSecurityDescriptor`.

## Cross-references

- [Directory Entries](directory_entries.md) — an embedded record carries the SecurityId at value offset 0x50; a split record carries it in its type-0x40 backing record at value offset 0x50 (not via the Object Table)
- [System OIDs](system_oids.md) — OID 0x520 and OID 0x530
- [Object Table](object_table.md) — OID resolution for 0x520 and 0x530

## Evidence

The single-table model and the OID 0x530 key/value structure are read in the decompiled driver and decoded from the disk
across the corpus: `RefsSecurityInitialize` opens OID 0x530 (via `MsInitializeWellKnownObjectId(0x530, …)`) and
`CmsHashTable` backs the descriptor lookup, while the SecurityId resolves through `RefsLoadSecurityDescriptor` /
`RefsSecurityGetDescriptorById`; the key, the 12-byte wrapper, the self-relative SD layout, the content-hash identity
(SecurityId-low = SD hash, ROL-3 NTFS algorithm), and the per-file compound SecurityId `(generation << 32) | hash32(SD)`
are all confirmed byte-for-byte on disk: on the 124 ReFS volumes of the corpus, the 4,405 descriptors' stored hash, key
low half and recomputed hash are equal on every one, and the key high half equals the generation, 1 on all 4,405. The
table's schema 0x140 is read in `RefsSecurityInitialize` and at the table's root on a 3.4, a 3.7 and a 3.14 volume. Each
is a registered finding with its own evidence tier and witness in the claim register.

See [how this was verified](../methodology.md) to trace these to
the exact images and measurements in `analysis/`.

<!-- findings: FS_OTBL_SA_006, MD_DDIR_006 -->
