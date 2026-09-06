# Resident vs Non-Resident Storage

The single most consequential question a ReFS recovery tool can get wrong is *where a file's bytes
actually are*. ReFS stores file content in one of two modes, chosen per file: **resident**
content lives **inline**, packed into the file's own row inside a directory's
[B+-tree](../structures/directory_entries.md); **non-resident** content lives in separate clusters
reached through a [type 0x40 extent row](../structures/extent_descriptors.md). A carver that only follows
extents — the NTFS reflex — never sees the resident files at all, and on the small-file workloads that
dominate most volumes those are the majority. The change runs one way only: every driver examined has a
`RefsConvertToNonResident` and **none has a `ConvertToResident`**, so nothing brings a stream back inline.
This page explains how the two modes are encoded, what
makes the driver move a file from one to the other, and why
[alternate data streams](../attributes/README.md) are a permanent exception.

## What `key_flags` actually encodes — and what it does not

`key_flags`, a `u16` at offset 0x02 of a directory entry's key, takes only **two** values on disk. It is
tempting to read them as "resident" and "non-resident", and that reading is **wrong**. What the field says
is *where the file's record lives*, not where its data lives:

| key_flags | The name row is… | Value size |
|-----------|------------------|------------|
| **0x01** | an **embedded record** — the file's own metadata header follows in this row | > 84 bytes (> 72 on v3.4–v3.9) |
| **0x02** | an **index entry** — a pointer whose record was split out into a [type 0x40 row](../structures/extent_descriptors.md) in the file's home directory | 84 bytes (v3.10+) / 72 bytes (v3.4–v3.9) |

**A `key_flags` 0x01 row can perfectly well hold a file whose data is in extents.** Measured across the
corpus, every kf=0x01 *file* row is extent-backed on ReFS **3.4, 3.7, 3.9 and 3.10** — 1,120 / 250 / 386 /
236 rows, **none** inline. On **3.14** the balance reverses and most are inline (219,960 of 236,769, about
93 %), but 16,809 are still extent-backed. So the flag predicts residency on no version.

**Residency is a property of the `$DATA` attribute**, and the only reliable way to determine it is to read
that attribute's storage: inline content in the row, or an allocation pointing at clusters. That is what
`forefst` does, and it is why its `IsResident` column means *"the current `$DATA` stream is inline"* rather
than *"key_flags is 0x01"*.

### Two independent axes

It is worth separating them explicitly, because a single flag cannot express both:

| | |
|---|---|
| **Record placement** | Is the object's record *embedded in this name row* (`key_flags 0x01`), or *split out* into a separate backing record (`0x02`)? A move or a hard link forces the split. |
| **Data residency** | Are the file's bytes *inline in that record*, or *on disk in extents*? |

A split-out record still holds its own `$DATA` attribute, and for a small file that attribute is commonly
the **inline** kind — so the bytes live in the backing record, not on disk. Across the image corpus
**16,191 of 83,485 split-record rows keep their data this way** — about one in five — and on one real
Windows volume 14,580 of them. (That count includes 0-byte records whose descriptor is the inline form;
the rule is always *what the descriptor says*, for empty records as much as for full ones.) Reading the attribute is the only way to tell: the inline form carries the
byte count and the content directly, the other form carries an extent list instead, and no record has both.

The practical consequence for a reader: a hard-linked file can legitimately show **resident storage together
with a link count above one**, and a file addressed through such a name has its content available without
touching the data area at all.

### What a 0x02 file row does tell you

A kf=0x02 row on a **file** is a fingerprint: the object has been **moved or hard-linked**, so its record
was split out of the name row into a type-0x40 backing in its home directory. On the audited 2 TB volume
this held for **51 of 51** such rows (49 moved, 2 hard-linked). It is also version-scoped: the form does
not exist at all on ReFS **3.4**, where every file row is kf=0x01 and there are **no type-0x40 rows**.
Directories are a separate matter — they use the 0x02 layout on every version and are identified by the
directory attribute bit `0x10000000`, not by the flag.

There is no third value. A census across the corpus finds `{0x01, 0x02}` and nothing else — in
particular there is **no** `0x04 = directory` flag, despite older accounts. A directory is stored with
key_flags **0x02** (it uses the same compact non-resident layout, pointing at its own per-directory
B+-tree through an [object ID](object_ids.md)) and is told apart from a non-resident *file* only
by the **directory attribute bit `0x10000000`** in its file attributes at value+0x40. Reading key_flags
alone cannot distinguish a directory from a non-resident file; the attribute bit is mandatory for that
decision.

The reason the resident value is *larger* than the non-resident one is simply that it carries the data.
A non-resident row stores fixed metadata plus a pointer to extents, so its size is constant; a resident
row stores that same metadata **followed by the file's bytes**, so its size grows with the content. That
size relationship is itself a reliable detector — see [the detection rule](#a-reliable-detection-rule)
below.

## What decides where the bytes go

The decision is made in `RefsAddAllocationForResidentWrite`, and it is gated on the **volume's format
version** — read from the VCB at `+0x318`/`+0x319` and compared against `0x30b`, the packed encoding of
v3.11. It is the *volume's* format, not the driver's build: a current driver mounting an older volume
takes the older path.

```c
if (volume_format < 0x30b && 0x20000 < new_size)   // < 3.11 and > 128 KiB
    raise STATUS_FILE_SYSTEM_LIMITATION;
if (volume_format < 0x30b || new_size < 0x800)     // < 3.11, or < 2048 bytes
    stay inline;
else
    convert to extents;
```

Two things follow, and they differ by **stream kind**:

| | format ≤ 3.10 | format ≥ 3.11 |
|---|---|---|
| **main `$DATA`** | **never inline.** Even a 5-byte file gets a whole 4 KiB cluster | inline while under **2 KiB** (0x800), then extents |
| **named stream (ADS)** | always inline, up to a hard **128 KiB** cap — past it the write fails | inline while under **2 KiB**, then extents |

The `0x20000` (128 KiB) branch is the **named-stream** limit, not a file-data threshold. The v3.4 driver
reaches it through a routine Microsoft named `RefsTelemetryUnsupportedADS`, and that driver has no
`RefsConvertToNonResident` at all — there is nothing there to convert a resident stream out of line, which
is the driver-side counterpart of main `$DATA` never being inline on those formats.

### Size is not the only trigger — but a move is not one of them

Several operations convert an inline stream to extents **regardless of size**. They are exactly the callers
of `RefsConvertToNonResident`: taking a **stream snapshot**, enabling **integrity streams**, block-clone
(`RefsDuplicateExtents`), **encryption**, remote/tiering, strictly-sequential, and an explicit
set-allocation or set-end-of-file.

**A move or a hard link is not among them.** No rename, move or link function calls
`RefsConvertToNonResident` in any driver build examined. What those operations force is the **record
split** — `key_flags` 0x01 → 0x02 — which says nothing at all about where the bytes live. A moved file can be,
and often is, still inline: on a controlled before/after move of a whole volume, **5 files changed
placement and 0 changed residency**, and the moved file's `$DATA` record was byte-identical either side.

### An upgrade does not convert anything

Because the gate reads the volume's format at write time, upgrading a volume changes only what happens to
**future** writes. On a v3.4 volume upgraded to v3.14, **0 of 262 pre-existing files changed residency**;
the single inline file on it is one of three names created *after* the upgrade.

## Alternate data streams: inline while small, extent-backed when large

The threshold below is the **format 3.11 and later** rule. On **format 3.10 and earlier** a named stream
is always inline instead, up to a hard 128 KiB cap — see
[Named data streams](../attributes/NAMED_DATA.md#residency) for both. Which rule applies is a property of
the *volume's* format, not of the driver reading it.

On format 3.11+, [alternate data streams](../attributes/README.md) (ADS) are **inline while their content
stays below 2 KiB** — which covers the overwhelming majority (typical ADS are tens of bytes). An ADS record *is* a
type-0xB0 entry (type 0xB0 is shared with `$SNAPSHOT`/`$NAMED_DATA`), and `RefsConvertToNonResident`
accepts 0xB0 at that same 2 KiB threshold on this format. A small ADS usually never reaches it, so it stays inline (StreamSummary flags 0 at val+0x10 — the same
field reads 2 for a snapshot entry) regardless of the file's own mode. The attribute-flags bit **0x1000**
at `val+0x02` is the discriminator, and it means the opposite of what an earlier reading of this page said:
across 8,238 named streams it is set on **exactly** the 844 that are *not* inline and clear on **exactly**
the 7,509 that are, with no exceptions. (The neighbouring val+0x38 is the integrity/checksum-type selector — 0x02 on
None/CRC64, 0x04 on SHA-256 — and has nothing to do with residency.)

Still on format 3.11+, a **large ADS (>= 2 KiB) is extent-backed**: its descriptor becomes a fixed 116-byte record
(`val[0x04] = 0x68`, no inline content), and its bytes move to on-disk **extents** — stored in a separate
type-0x0 sub-record of the same directory value, using the standard type-0x40 extent format. So the "ADS
ceiling" is not the page size; it is the **2 KiB conversion threshold**, above which the stream spills to
extents exactly like a large `$DATA` stream. `forefst` reconstructs such an ADS from its extents
(byte-exact, verified on a 256 B → 2 MB size sweep with the boundary at 2 KiB).

This matters forensically two ways: an inline ADS lives in the metadata tree (carve it there), while a
large ADS lives in clusters (recover it via its extent list) — and a tool that assumes *all* ADS are
inline will miss the large ones.

Finally, keep two separate questions apart: *where the stream's bytes live* (inline vs extents, above) and
*where the record describing the stream lives*. The second can also move — when a file accumulates enough
attributes, the directory value's inline sub-record tree gains a level and the records themselves relocate to
a child page, leaving the value holding only an index node. A reader that stops at the inline table then sees
nothing and reports "no alternate data streams" for a file that has plenty. See
[Directory Entries](../structures/directory_entries.md).

## The forensic stakes

A tool that assumes every file's content lives in external clusters will **silently fail to recover small
files**, because their bytes are not in any cluster it would carve — they are inside the directory's
metadata tree. On the small-file workloads that make up the bulk of many volumes, that is the single most
likely cause of under-recovery in practice, and it is silent: the tool reports success while quietly
omitting most of the data. The discipline is to read the `$DATA` attribute and follow whichever storage it
names — inline bytes in the row, or [extents](../structures/extent_descriptors.md) — and **never** to decide
that from `key_flags`, which answers a different question (above). The same split governs
[deletion recovery](deletion_recovery.md): a deleted resident file's bytes survive or perish *with its
metadata row*, while a deleted non-resident file's bytes can persist in unreferenced clusters long after
the row is gone — two very different recovery problems sharing one on-disk encoding.

## A detection rule (size is a first cut, not the final word)

A parser classifies a directory entry from key_flags + the value length, then **confirms residency from the
`$DATA` allocation**:

- An **84-byte value** — 72 if a pre-v3.10 driver wrote the entry — is a **non-resident file** or a
  **directory**, separated by the directory attribute bit `0x10000000` at value+0x40. The length is fixed
  when the entry is written and never rewritten, so an upgraded volume carries both forms at once; read it
  from the row, not from the volume version.
- A value **larger than 84 bytes** is a **long value with inline metadata** — usually a
  resident file, **but not always**: if its current `$DATA` stream is extent-backed on disk, the file is
  **non-resident** despite the long value.

So size gives you a *candidate*, not the verdict. Residency is the **disk-allocated size of the `$DATA`
stream at value+0x48** (see [Extent Descriptors](../structures/extent_descriptors.md)): `disk_alloc == 0`
→ inline / **resident**; `disk_alloc > 0` → **non-resident** (content lives in extents). A long inline value
whose `$DATA` is extent-backed therefore reads non-resident. The long value still mirrors the
[resident value layout](../structures/directory_entries.md) — timestamps,
[security ID](../structures/security_descriptors.md), size — read inline; only the residency verdict comes
from the allocation.

On **v3.4–v3.10 and upgraded** volumes this long-value-but-non-resident form is common, and the extent map is
frequently held **inline inside the long value itself** rather than in a separate extent row: the file keeps a
full resident-style metadata header while its bytes live in on-disk clusters listed within the same value. Two
fixed fields carry the truth even when the inline metadata tree is too deep to walk directly — the true content
size at **value+0x58** and the cluster-aligned on-disk allocation at **value+0x60** — and `forefst` uses them to
report the file as non-resident and to decode the inline extent list. That list is a small B+-tree node, so even a
**fragmented** file (many separate runs) decodes: `forefst` reads the node's row directory to enumerate the true
data extents, skipping the coarse summary rows that a naive scan would double-count. `dataruns` and `extract`
reassemble these files **byte-exact**. Every recovery is gated by a self-check — the extents must tile the file's
clusters exactly once, with no gap or overlap — so a misread can never be written out as file content: if the check
fails (for instance a file whose extent tree is large enough to spill onto separate metadata pages), `extract`
stops with a clear message and recovers **no** bytes rather than partial or wrong ones. The same decoder and
self-check apply to non-resident files that use a separate backing record instead of an inline one, so recovery is
uniform across storage layouts.

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

- [Driver Transitions](driver_transitions.md) — the functions behind the gate, and the complete conversion-trigger list

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
- [Object IDs](object_ids.md) — the OID a directory's key_flags-0x02 row points at

## Evidence

The two key_flags values and the `{0x01, 0x02}`-only census, the directory-bit discriminator, and the
embedded/index-entry value sizes are raw-disk decoded (RD) across the corpus, correcting the earlier
`0x04 = directory` reading. The size thresholds and the v3.11
version gate are confirmed in the driver (E2): `RefsAddAllocationForResidentWrite` checks `version < 0x30b`
against the 0x800 / 0x20000 limits, and `RefsConvertToNonResident` accepts types 0x80 and 0xB0. A small
ADS (< 2 KiB) is inline; a large ADS (>= 2 KiB) is extent-backed via a type-0x0 record (E2 + RD, reconstructed
byte-exact across a 256 B → 2 MB size sweep). The val+0x38 field is a checksum-type selector, not a
residency field.
See [how this was verified](../methodology.md) to trace these to the exact images and measurements in the
analysis archive.
