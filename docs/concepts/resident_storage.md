# Resident vs Non-Resident Storage

The single most consequential question a ReFS recovery tool can get wrong is *where a file's bytes
actually are*. ReFS stores file content in one of two modes, chosen per file and reversible: **resident**
content lives **inline**, packed into the file's own row inside a directory's
[B+-tree](../structures/directory_entries.md); **non-resident** content lives in separate clusters
reached through a [type 0x40 extent row](../structures/extent_descriptors.md). A carver that only follows
extents — the NTFS reflex — never sees the resident files at all, and on the small-file workloads that
dominate most volumes those are the majority. This page explains how the two modes are encoded, what
makes the driver promote a file from one to the other, and why
[alternate data streams](../attributes/README.md) are a permanent exception.

## How the two modes are encoded

The mode is carried in a single field — `key_flags`, a `u16` at offset 0x02 of a directory entry's
key — and only **two** values ever appear on disk:

| Mode | key_flags | Where the content is | Value size |
|------|-----------|----------------------|------------|
| **Resident** | 0x01 | Inline in the B+-tree row, after the file's metadata header | > 84 bytes (> 72 bytes on v3.4) |
| **Non-resident** | 0x02 | Separate clusters, via a type 0x40 extent row | 84 bytes (v3.10+) / 72 bytes (v3.4–v3.9) |

There is no third value. A census across the corpus finds `{0x01, 0x02}` and nothing else — in
particular there is **no** `0x04 = directory` flag, despite older accounts. A directory is stored with
key_flags **0x02** (it uses the same compact non-resident layout, pointing at its own per-directory
B+-tree through an [object ID](object_ids_fileids.md)) and is told apart from a non-resident *file* only
by the **directory attribute bit `0x10000000`** in its file attributes at value+0x40. Reading key_flags
alone cannot distinguish a directory from a non-resident file; the attribute bit is mandatory for that
decision.

The reason the resident value is *larger* than the non-resident one is simply that it carries the data.
A non-resident row stores fixed metadata plus a pointer to extents, so its size is constant; a resident
row stores that same metadata **followed by the file's bytes**, so its size grows with the content. That
size relationship is itself a reliable detector — see [the detection rule](#a-reliable-detection-rule)
below.

## What triggers promotion to non-resident

A file does not choose its mode up front; the driver promotes it from resident to non-resident the moment
its content outgrows a version-specific threshold. The decision is made in
`RefsAddAllocationForResidentWrite`, and the threshold changed dramatically at the v3.11 feature epoch:

| Version | Threshold | Behaviour |
|---------|-----------|-----------|
| v3.4 – v3.10 | **128 KiB** (0x20000) | Hard cap; a resident write past it returns `STATUS_FILE_SYSTEM_LIMITATION` |
| v3.11+ (incl. v3.14) | **2 KiB** (0x800) | Convert to non-resident once the data reaches 2 KiB |

The driver gates this on the packed version: in effect `if (version < 0x30b || alloc_size < 0x800) stay
resident, else convert to non-resident` — where `0x30b` is the packed encoding of v3.11. The threshold
applies to the **data/allocation portion**, not to the total row size, so the small fixed metadata header
does not count against it.

The practical effect is a sharp behavioural split between Windows generations. On a v3.4 volume the
128 KiB cap is larger than almost any ordinary file, so content stays resident as a matter of course; on a
v3.14 volume the 2 KiB threshold is crossed by anything but the smallest files, so non-resident storage is
common. The practical consequence is a clear version split rather than a precise ratio. On an **original
v3.4–v3.10** volume ordinary files are almost all resident: the 128 KiB cap exceeds typical content (and
every file in the small-file test corpus is resident there — a property of the cap meeting the workload,
not evidence that v3.4 lacks non-resident storage; a file past 128 KiB *would* spill to extents). On a
**v3.14** volume the 2 KiB threshold is crossed by anything but the smallest files, so non-resident
storage is common, and the resident fraction falls as files get larger and more numerous. The forensic
takeaway is that **version detection drives carving strategy**: on an upgraded or native v3.14 volume you
must expect both modes side by side, while on an original v3.4 volume almost everything is inline.

## Alternate data streams: inline while small, extent-backed when large

[Alternate data streams](../attributes/README.md) (ADS) are **inline while their content stays below
2 KB** — which covers the overwhelming majority (typical ADS are tens of bytes). An ADS record *is* a
type-0xB0 entry (type 0xB0 is shared with `$SNAPSHOT`/`$NAMED_DATA`), and `RefsConvertToNonResident`
accepts 0xB0 at a ~2 KB threshold. A small ADS never reaches it, so it stays inline (StreamSummary flag 0
at val+0x10) regardless of the file's own mode — even an ADS on a snapshot-bearing file (attribute flag
0x1000) is inline. (The neighbouring val+0x38 is the integrity/checksum-type selector — 0x02 on
None/CRC64, 0x04 on SHA-256 — and has nothing to do with residency.)

A **large ADS (>= 2 KB) is promoted to non-resident**: its descriptor becomes a fixed 116-byte record
(`val[0x04] = 0x68`, no inline content), and its bytes move to on-disk **extents** — stored in a separate
type-0x0 sub-record of the same directory value, using the standard type-0x40 extent format. So the "ADS
ceiling" is not the page size; it is the **2 KB conversion threshold**, above which the stream spills to
extents exactly like a large `$DATA` stream. `forefst` reconstructs such an ADS from its extents
(byte-exact, verified on a 256 B → 2 MB size sweep with the boundary at 2 KB).

This matters forensically two ways: an inline ADS lives in the metadata tree (carve it there), while a
large ADS lives in clusters (recover it via its extent list) — and a tool that assumes *all* ADS are
inline will miss the large ones.

## The forensic stakes

A tool that assumes every file's content lives in external clusters will **silently fail to recover small
files**, because their bytes are not in any cluster it would carve — they are inside the directory's
metadata tree. On the small-file workloads that make up the bulk of many volumes, that is the single most
likely cause of under-recovery in practice, and it is silent: the tool reports success while quietly
omitting most of the data. The discipline is to read content from the row when key_flags is 0x01 and to
follow [extents](../structures/extent_descriptors.md) only when it is 0x02. The same split governs
[deletion recovery](deletion_recovery.md): a deleted resident file's bytes survive or perish *with its
metadata row*, while a deleted non-resident file's bytes can persist in unreferenced clusters long after
the row is gone — two very different recovery problems sharing one on-disk encoding.

## A reliable detection rule

A parser can classify any directory entry by combining key_flags with the value length:

- A value **larger than 84 bytes** (72 on v3.4) is necessarily a **resident file** — only inline content
  makes a row that big.
- An **84-byte value** (72 on v3.4–v3.9) is either a **non-resident file** or a **directory**, separated
  by the directory attribute bit `0x10000000` at value+0x40.

Size alone gets you to resident-vs-non-resident; the directory bit completes the classification. This
mirrors the [resident value layout](../structures/directory_entries.md), where the same value also carries
the file's timestamps, [security ID](../structures/security_descriptors.md), and file size.

## Raw example

`forattributes/bla.txt` on a v3.14 4 KiB-cluster image holds the 7 bytes `hello\r\n`, stored **inline** in the directory record — it has no data clusters at all. The embedded `$DATA` sub-record, at offsets relative to the file record's value-data (`vd`):

```text
vd+0x0e8:  01 00 00 80                <- embedded marker 0x80000001 (single-instance)
vd+0x0ec:  80 00 00 00                <- sub-record type 0x80 = $DATA
vd+0x118:  07 00 00 00                <- content length = 7
vd+0x12c:  68 65 6c 6c 6f 0d 0a       <- "hello\r\n"  (the file content, inline)
```

The file's entire content lives in the parent directory's B+-tree leaf row — a direct demonstration that ReFS stores small files resident, contradicting the prior "always non-resident" assumption.

## Cross-references

- [Directory Entries](../structures/directory_entries.md) — the byte-level resident and non-resident value
  layouts this page summarises, and the key where `key_flags` lives
- [Extent Descriptors](../structures/extent_descriptors.md) — the type 0x40 rows a non-resident file points
  at; where the content actually is once it leaves the row
- [Attributes — Forensic Reference](../attributes/README.md) — alternate data streams and the stream types
  `RefsConvertToNonResident` will and will not promote
- [Cluster and Page Size](cluster_page_size.md) — the page size that fixes the structural ADS ceiling
- [Version Detection](version_detection.md) — distinguishing v3.4 (128 KiB cap) from v3.11+ (2 KiB) before
  choosing a carving strategy
- [Deletion Recovery](deletion_recovery.md) — why resident and non-resident deletes are different recovery
  problems
- [Object IDs and File IDs](object_ids_fileids.md) — the OID a directory's key_flags-0x02 row points at

## Evidence

The two key_flags values and the `{0x01, 0x02}`-only census, the directory-bit discriminator, and the
resident/non-resident value sizes are raw-disk decoded (RD) across the corpus, correcting the earlier
`0x04 = directory` reading. The promotion thresholds and the v3.11
version gate are confirmed in the driver (E2): `RefsAddAllocationForResidentWrite` checks `version < 0x30b`
against the 0x800 / 0x20000 limits, and `RefsConvertToNonResident` accepts types 0x80 and 0xB0. A small
ADS (< 2 KB) is inline; a large ADS (>= 2 KB) is extent-backed via a type-0x0 record (E2 + RD, reconstructed
byte-exact across a 256 B → 2 MB size sweep). The val+0x38 field is a checksum-type selector, not a
residency field.
See [how this was verified](../methodology.md) to trace these to the exact images and measurements in the
analysis archive.
