# $NAMED_DATA
<!-- site: description "Alternate data streams (ADS): one sub-record per named stream in the file's record, inline or in extents." -->

`$NAMED_DATA` is ReFS's named (alternate) data stream — ADS.

- Unlike NTFS, which uses named `$DATA` attributes, ReFS stores each ADS as a type-0xB0 sub-record of the file's
  record: the name row's value when the record is embedded, the type-0x40 backing when it is split, and a child page
  of either when the attribute tree has grown a level.
- On a format 3.11 or later volume a small ADS (content below 2 KiB) is inline — its bytes sit in the record —
  unless a conversion moved it to extents; one that reaches 2 KiB is in on-disk extents, the same as any large
  stream.
- On format 3.10 and earlier the rule is different: a named stream is always inline, up to a 128 KiB cap.
- The type-0xB0 code is shared with `$SNAPSHOT`; the two are told apart by the StreamSummary flag (below).

| Property | Value |
|----------|-------|
| Type code | 0xB0 (subtype 0x0005), shared with [$SNAPSHOT](SNAPSHOT.md) |
| Instances | multi-instance (marker 0x80000002) in the 3.7 and later key form; the 3.4 key carries no marker |
| Where it lives | the file's record: the embedded node of its name row (from `value+0xA8`) or of its type-0x40 backing when the record is split; often in a child node of that tree |
| Size | variable: 0x3C bytes + the inline content; a fixed 116-byte descriptor when the content is in extents |
| Added in | 3.4 or earlier: type-0xB0 stream rows are read on 3.4 (in the marker-less key form) |

See [Residency](#residency) for both rules.

## Value layout

Key layout (3.7 and later; offsets from `key+0x08`, `key+0x00` holding the value length as a u64):

<!-- site: hexfig "attr_named_data_win11refs2tspecials" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Marker | 0x80000002 |
| 0x04 | 4 | Descriptor | 0x000500B0 |
| 0x08 | var | Stream name | UTF-16LE, not NUL-terminated — its length comes from the key length (no terminator on any name measured) |
| — | 0–6 | Alignment padding | to `(offset − marker_start) % 8 == 4` |

### The key has two forms, and ReFS 3.4 uses the other one

The row's key identifies the attribute, and its layout changed with the instance marker:

| Version | key+0x08 | Attribute type | Stream name starts at |
|---------|----------|----------------|-----------------------|
| 3.7 and later | instance marker (`0x80000002` / `0x80000001`) | key+0x0C | key+0x10 |
| 3.4 | *(no marker)* | key+0x08 | key+0x0C |

A reader that matches only the marker form finds no alternate data streams at all on a ReFS 3.4 volume — not
because there are none, but because every key fails the test. The same marker-less rows also survive on volumes
upgraded from 3.4, so the form has to be decided per record rather than from the volume version.

On the 3.4 volumes measured these rows are not at the outer level of the embedded tree either: they sit in a
[child node](../structures/directory_entries.md#when-the-sub-record-table-moves-into-a-child-node), so a reader must
descend before it can even see them.

### The value

The type-0xB0 value header, shared with `$SNAPSHOT`:

<!-- site: hexfig-rows "attr_named_data_win11refs2tspecials" "value" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 2 | Padding | 0 |
| 0x02 | 2 | Attribute flags | 0x0000 for an inline ADS; bit 0x1000 marks the extent-backed form (see [ADS vs snapshot](#ads-vs-snapshot)) |
| 0x04 | 4 | Data-area size | value length − 12 |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Summary size | 0x30 (48) |
| 0x10 | 2 | StreamSummary flags | 0 = ADS, 2 = snapshot — the discriminator (see below) |
| 0x12 | 6 | Reserved | 0 |
| 0x18 | 8 | Allocated size | equal to the stream size for an inline ADS (its bytes are stored packed); the allocation of an extent-backed one |
| 0x20 | 8 | Stream size | logical content length |
| 0x28 | 8 | Valid data length | equal to the stream size on every type-0xB0 row of the corpus (5,578) |
| 0x30 | 8 | Total allocated | usually equals allocated size |
| 0x38 | 2 | Checksum type | as for [$DATA](DATA.md#checksum-fields); not a residency flag. 0 on v3.4 |
| 0x3A | 2 | Integrity algorithm | as for [$DATA](DATA.md#checksum-fields) |
| 0x3C | var | Inline content | the ADS content bytes (stream_size long) — present only for an inline ADS: below 2 KiB on format 3.11 and later, up to 128 KiB on 3.10 and earlier |

Most ADS are small (tens of bytes) and inline. On format 3.11 and later an ADS of 2 KiB or more has no inline content:
its value becomes a fixed 116-byte descriptor (`val[0x04] = 0x68`, `val[0x02]` bit 0x1000 set) and its data lives in
extents — see [Residency](#residency). Two corpus files carry both a named stream and a snapshot: on one the stream is
inline; on the other (`adstest`, 30 bytes) it is in extents, with a whole 4 KiB cluster allocated.

## ADS vs snapshot

ADS and snapshot streams share descriptor 0x000500B0 (under marker 0x80000002 in the 3.7 and later key form). Two
reliable discriminators, which agree on every type-0xB0 entry measured:

| Method | ADS | Snapshot |
|--------|-----|----------|
| StreamSummary flags at `val[0x10]` | 0x0000 | 0x0002 |
| Attribute flags at `val[0x02]` | 0x0000 (inline), or 0x1000 / 0x5000 (extent-backed) | 0x1C00 (bit 0x0400 = HasSnapshot) |

On an ADS row, the attribute-flags bit 0x1000 marks the extent-backed form exactly: every ADS row carrying it is the
fixed 116-byte descriptor (`val[0x04] = 0x68`) with no inline content and its data in extents, and every ADS row
without it is inline (or empty), with no counterexample either way.

A snapshot entry carries bit 0x1000 too (its content is never in the 0xB0 row), and bit 0x0400 (HasSnapshot) is set
only on snapshot entries.

The StreamSummary-flags method (`val[0x10]`) is preferred. The stream index at `val[0x44]` is not a reliable
discriminator: every extent-backed ADS reads `val[0x44] = 0x1000` (the live main-stream id), and on an inline ADS
offset 0x44 falls inside the content. `forefst.py` uses `val[0x10]`.

## Residency

The rule differs by volume format:

| format | named stream |
|---|---|
| ≥ 3.11 | extents at 2 KiB (`0x800`) or more — the same constant the driver applies to main `$DATA`; below it inline, unless a conversion moved it to extents |
| ≤ 3.10 | always inline, up to a hard 128 KiB (`0x20000`) cap: a write past it fails with `STATUS_FILE_SYSTEM_LIMITATION` (see below) |

The 128 KiB cap: the v3.4 driver reaches that branch through a routine named `RefsTelemetryUnsupportedADS`, which
is what identifies the limit as a *named-stream* limit rather than a file-data one.

On ≥ 3.11 the boundary is exact in one direction: on the 3.14 volumes measured no inline named stream reaches
2,048 bytes, and the extent-backed ones of 2 KiB or more begin at exactly 2,048.

Below 2 KiB a stream is inline unless a conversion moved it to extents, for example a stream snapshot (an
allocation of 2 KiB or more set before the write forces extents on a main stream on format 3.11 and later; on a named
stream it is untested).

Of the three such streams in the corpus, one was created by a stream snapshot; for the other two the cause is not
established.
Each reads `alloc != size` (an inline stream stores its bytes packed).

A stream that reaches 2 KiB is moved to extents, as a large `$DATA` stream is:

- The 0xB0 descriptor stays an ADS (`val[0x10] = 0`) and becomes a fixed 116-byte record with `val[0x04] = 0x68`
  and no inline content. It sets `val[0x02]` bit 0x1000, which is the reliable discriminator on 3.7 to 3.14: across
  the marker-form 0xB0 rows of those volumes the bit is set on exactly the rows that are not inline (extent-backed
  streams and snapshot entries) and clear on exactly those that are, with no exception.
- The extent list is in a separate extent record of the same file record — its key is 0x50 bytes with attribute
  type 0x0003 at `key+0x08` — not in the 0xB0 descriptor and not reached through a stream index. Its map is the same
  extent node as a `$DATA` record's (24-byte extent rows). The ADS is linked to its extent record by matching stream
  size (`val[0x20]`).
- `forefst` reconstructs the content by translating those extents (VLCN → PLCN) and reading the clusters — verified
  byte-exact on a 256 B → 2 MB size sweep on a format 3.14 volume (the boundary sits exactly at 2 KiB: 1920-byte
  content is inline, 2048-byte content is extent-backed).

The `val[0x38]` field is the checksum-type selector, not a residency flag.

### Where the ADS *record* lives

Residency above describes the stream's content. Independently of it, the record that describes the stream can
move. A file's record keeps its sub-records in a small B+-tree, and once the file carries enough attributes that
tree gains a level: the value then holds only an *index* node and the ADS records sit in a child page. Reading just
the inline table in that case returns no streams at all — so a file can genuinely carry many alternate data streams
while a naive read reports none.

See [Directory Entries → When the sub-record table moves into a child node](../structures/directory_entries.md)
for how to tell the two cases apart and follow the child.

## Where a split record keeps its streams

On a volume with hard-link support, a move or a hard link splits a file's record out of its name row. The `0xB0`
stream sub-records go with it, into the
[type-0x40 backing record](../structures/directory_entries.md#relocated-files--the-entry-moves-the-identity-does-not)
— not into the name row that stays behind. A reader that enumerates streams from the directory entry alone
therefore reports a moved or hard-linked file as having none, however many it has.

Measured on a purpose-built volume: a 500-byte file with a 500-byte stream, moved to another directory, keeps the
stream in its backing and reads back byte-for-byte from there.

## Cross-references

- [Directory Entries](../structures/directory_entries.md) — the sub-record chain layout
- [$DATA](DATA.md) — the default data stream uses the same stream-summary format
- [$SNAPSHOT](SNAPSHOT.md) — snapshot entries share the type-0xB0 code; the snapshot value format and the discriminators

## Evidence

Type 0xB0 / descriptor 0x000500B0 and the value layout are read in the decompiled driver (`RefsCreateStreamSnapshot`,
`RefsUpdateScbFromAttribute`, `RefsConvertToNonResident`) and decoded on disk across the corpus, among them the ADS
census and the reading of `val[0x38]` as the checksum selector, not residency.

The extent-backed (>= 2 KiB, format 3.11+) ADS layout — the 2 KiB threshold and the extent record — was decoded and
reconstructed byte-exact on 161 large ADS (256 B → 2 MB size sweep). A named stream on a split record lives in the
type-0x40 backing, not in the name row (measured on a format 3.14 lab volume) — the case a stream enumeration that
reads only the name row cannot see. The page is documented against the project's claim register. See
[how this was verified](../methodology.md).

The measurements behind the text:

- Stream names: 0 of 254 type-0xB0 stream names and 0 of 3,830 reverse-index names carry a terminator. Worked case
  (`win11refs2g`, 38-byte key): `6a00…` value_length, marker `0x80000002`, type `0xB0` subtype `0x0005`, then 22
  bytes of name ending `34 00` with no NUL.
- The attribute-flags bit 0x1000: over 5,667 ADS rows, 763 of 763 rows carrying it take the extent-backed form and
  4,904 of 4,904 without it are variable-length with inline content; over the 8,353 marker-form 0xB0 rows (57
  images), the bit is set on exactly the 844 that are not inline (729 extent-backed + 115 snapshot entries) and clear
  on exactly the 7,509 that are. 0x5000 is read on 12 extent-backed SmartScreen rows (two streams on six copies of
  one volume).
- `val[0x44] = 0x1000` on 729 of 729 extent-backed ADS rows.
- The 2 KiB boundary: 8,238 named streams (7,505 inline, 4 empty, 729 extent-backed); 6,367 of them on format 3.14
  volumes, where no inline stream reaches 2,048 bytes; the 1,871 on formats 3.7, 3.9 and 3.10 are all of 47 bytes or
  less.
- Below 2 KiB and extent-backed: 13 rows, three distinct streams — `adstest` (created by a stream snapshot) and the
  SmartScreen streams of `hadlinkgit.exe` and `Git-2.54.0-64-bit.exe`, repeated on six copies of
  `win11refslasttests`.

<!-- findings: FS_SNAP_RA_001, MD_ADS_RA_001, MD_ADS_RA_002, MD_ADS_RA_003, MD_ADS_RA_004, MD_ADS_RA_005, MD_ATTR_007,
               MD_ATTR_RA_018, MD_DATA_RA_010, MD_DATA_RA_027, MD_FTBL_007, MD_INTG_RA_005, MD_SNAP_RA_005 -->
