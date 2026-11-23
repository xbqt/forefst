# Checkpoint (CHKP)

The Checkpoint is the atomic commit point of a ReFS volume. A volume keeps two alternating checkpoints.

Each checkpoint record is one cluster (4 KiB on 4K-cluster volumes, 64 KiB on 64K-cluster volumes): refs.sys reads,
self-checksums and writes it as one cluster.

Its allocation is one metadata page:

- on 4K-cluster volumes the allocator reserves four consecutive clusters for it and the record uses the first;
- on 64K-cluster volumes the allocation is the record's own cluster.

The checkpoint's own page reference lists one LCN.

The valid copy with the higher virtual clock is the current one, and the other copy is the previous consistent state
(a rollback target until the next flush).

## Field Layout

<!-- site: hexfig "chkp_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 80 | Page header | Common metadata page header (see [Page Header](page_header.md)) with signature `"CHKP"` |
| 0x50 | 4 | Version echo (u32) | Packed `minor<<16 | major` on native v3.10+; 0 on upgraded/legacy |
| 0x54 | 2 | Major version (u16) | Always 3 |
| 0x56 | 2 | Minor version (u16) | 4, 7, 9, 10, or 14 |
| 0x58 | 4 | **Self-descriptor offset** (u32) | In-page offset of the checkpoint's **own** page reference: 0xE0 on v3.14, 0xE8 on the records an Insider build wrote, 0xD0 on v3.4–v3.10 ([the self-descriptor](#the-self-descriptor)) |
| 0x5C | 4 | Page reference size (u32) | 0x68 (formats 3.4–3.9), 0x30 (CRC64), 0x48 (SHA-256) |
| 0x60 | 8 | Virtual clock (u64) | Matches header at 0x10; the checkpoint sequence counter — increments on every committed checkpoint. refs.sys uses the valid copy with the higher value (see *Checkpoint selection* below). |
| 0x68 | 8 | Allocator clock (u64) | The volume's allocator clock: **≤ the virtual clock** on every volume measured, typically a few below it ([the allocator clock](#the-allocator-clock)) |
| 0x70 | 8 | Log position (LSN, u64) | Where replay of the [MLog](mlog.md) after an unclean shutdown begins: high 32 bits = generation, low 32 bits = log-block offset |
| 0x78 | 4 | CHKP flags (u32) | See CHKP Flags below |
| 0x7C | 12 | Reserved | Always zero |
| 0x88 | 4 | Optional area: offset (u32) | The in-record offset of a 32-byte area placed right after the 13 root references (so it equals their end: 0x680 on 3.4–3.9, 0x380 on most v3.14 records); 0 when there is no area. Its content is the change journal's position at the checkpoint ([below](#the-change-journal-cursor-at-0x88)) |
| 0x8C | 4 | Optional area: length (u32) | 0x20 (32 bytes) on every corpus record that has the area; 0 when it has none (some records formatted at 3.14) |
| 0x90 | 4 | Root count (u32) | 13 on every checkpoint copy of the corpus; refs.sys accepts more than 4 and at most the record size / 4 |
| 0x94 | var | Root pointer list | **Direct** (flag 0x0200 clear): the 13 `u32` root offsets themselves. **Indirect** (0x0200 set): the `u32` in-record offset of the root-offset table: 0xA8 on v3.14, 0xB0 on the records an Insider build wrote ([direct and indirect](#direct-vs-indirect-root-access)) |
| 0x98 | 4 | Root-offset table length (u32, with flag 0x0200) | The table's length in bytes: (4n + 0xB) & ~7 for n roots, 0x38 (56) for 13, on every flag-0x0200 corpus record. Without flag 0x0200 (v3.4 to v3.10) the root offsets themselves start at 0x94, so 0x98 to 0xC7 hold root offsets there |
| 0x9C | 4 | Rollback-protection blob: offset (u32, with flag 0x0400) | 0 when there is no blob (every corpus record) |
| 0xA0 | 4 | Rollback-protection blob: length (u32, with flag 0x0400) | At least 0x50 bytes when present; 0 on every corpus record |
| 0xA4 | 4 | Attestation HMAC structure: offset (u32, with flag 0x2000; Insider) | On every corpus record that has it, the structure follows the 32-byte area at 0x88: +0xA4 = +0x88 + 0x20 (0x3A8 or 0x4F8) |
| 0xA8 | 4 | Attestation HMAC structure: length (u32, with flag 0x2000; Insider) | 0x48, or 0x48 + 2^n when the attestation object's own flag is set; 0x48 on every corpus record that has it |

### The self-descriptor

The field at 0x58 is the in-page offset of the checkpoint's **own** page reference: the descriptor whose first LCN
slot is the checkpoint page itself.

- The writer places it right after the root-offset table ([below](#how-refssys-lays-out-the-record)): 0xE0 on v3.14
  (0xA8 + 0x38), 0xE8 on the records an Insider build wrote (0xB0 + 0x38), 0xD0 on v3.4–v3.10.
- Verified by reading the reference at this offset and comparing its slot 0 with the checkpoint's own LCN, on every
  corpus image, every version.
- Where the 0x88 area is present, `0x88 == 0x58 + 14 × (u32@CHKP+0x5C)`: the self-descriptor plus the 13 root
  references.

### The allocator clock

The field at 0x68 is the volume's allocator clock, which `FormatCheckpointRecord` writes next to the virtual clock;
the mount loads both back from the copy it chooses.

- The driver stamps it, with the virtual clock, into every redo record it adds to the [MLog](mlog.md). At replay, a
  log block whose first record names object 0x1, 0xB or 0xE is replayed only when that record's allocator clock is
  at or above the checkpoint's.
- On every volume measured it is at most the virtual clock, typically a few below it, and the two copies of a
  checkpoint differ in it by exactly 1 on the volumes byte-compared.
- What advances it, operation by operation, is not established.

### The change journal cursor at 0x88

The 32-byte area that +0x88 / +0x8C locate holds the change journal's position when the checkpoint was written: four
u64.

| Area offset | Field | Meaning |
|-------------|-------|---------|
| +0x00 | First USN | the lowest USN still in the journal (0 until the journal wraps) |
| +0x08 | Next USN | the USN the next journal record will get: the end of the last record written |
| +0x10 | Wrap base | the USN at file offset 0 of `$J` (0 until the journal wraps) |
| +0x18 | Wrap size | the ring's length when it wrapped (0 until it wraps) |

For an examiner:

- **Records written after the checkpoint.** A journal record whose USN is at or past the area's Next USN was written
  after this checkpoint (within one journal instance: a re-created journal restarts its USNs).
- **No journal, or no area.** The area is all zero on a volume without a journal. Some checkpoints carry no area at
  all (+0x8C = 0); those say nothing about the journal.

`forefst usn` reads the journal itself; the cursor is a second, independent record of where it stood.

## How refs.sys lays out the record

`FormatCheckpointRecord` writes the parts of the record in order, each one where the previous one ends (rounded up to
8 bytes), and records each part's place in the header:

1. **The root-offset table**, on a volume at version 3.11 or later (the version test 0x30B; the writer then also
   sets flag 0x0200):
   - its offset at +0x94: **0xA8** on the 26100 builds read, **0xB0** on the Insider builds read;
   - its length at +0x98: (4n + 0xB) & ~7 bytes for n roots, so **0x38** (56) for 13 roots.
2. **The checkpoint's own page reference**, at the table's end: +0x58 = the table's offset + its length, so 0xE0 on
   a 26100 build and 0xE8 on an Insider build.
3. **The 13 root references**, each `u32@CHKP+0x5C` bytes long, one after the other from there; the table lists
   their offsets.
4. **The optional area** at +0x88 / +0x8C, when the writer's caller passes one (both 0 otherwise); 32 bytes on every
   corpus record that has it.
5. **The rollback-protection blob** at +0x9C / +0xA0 (flag 0x0400), when there is one.
6. On Insider, **the attestation HMAC structure** at +0xA4 / +0xA8 (flag 0x2000); 0x48 bytes on the corpus.

What the corpus records hold follows that layout:

- every record with flag 0x0200 and without flag 0x2000 reads +0x94 = 0xA8, +0x98 = 0x38 and +0x58 = 0xE0, on 4K- and
  64K-cluster volumes alike;
- the records an Insider build wrote (flag 0x2000, on the few volumes an Insider build mounted) read instead:
  +0x94 = 0xB0 and +0x58 = 0xE8. Their header also carries the HMAC pair at +0xA4 / +0xA8, which the 8 extra
  bytes before the table make room for (consistent with the layout; the link is not read in the driver);
- on those records no rollback blob is present, so the HMAC structure starts right after the 32-byte optional area
  (+0xA4 = +0x88 + 0x20), with +0xA8 = 0x48;
- the records without flag 0x0200 (formats 3.4 to 3.10) read +0x58 = 0xD0.

Read on 26100.8115, .9444 and .9818 and on Insider 29574, 29659 and 29683 (the 0xA8 / 0xB0 offset and the
table-length formula, the same in all six); the order of the areas after the root references on 26100.9818 and
Insider 29683. The counts are in the Evidence section.

## Checkpoint selection and fallback

Each CHKP carries a **self-checksum verified at mount**, the same mechanism the [Superblock](supb.md) uses. The
algorithm is cluster-size-dependent: 4-byte CRC32-C on 4K-cluster, 8-byte CRC64 on 64K-cluster, 32-byte SHA-256 on
SHA-256 volumes.

At mount, refs.sys (`CmsVolume::ReadLatestCheckpoint`) reads the two copies in the order the superblock lists them,
slot 0 first:

- a copy that cannot be read or fails validation (its self-checksum, the bounds of its root list) is skipped;
- the first valid copy is kept, and the other replaces it only when its virtual clock at **CHKP+0x60** is strictly
  greater (an unsigned 64-bit comparison);
- **on a tie the copy in slot 0, the one listed first in the superblock, is used**; the LCN plays no part, and nothing
  reports the tie.

Because each flush writes the *other* slot with clock+1, the slot that is not used holds the previous consistent
state.

On the 26100 builds the first pass also rejects a copy whose root 0xC, 7 or 8 cannot be read or fails its own
checksum (on Insider 29574, 29659 and 29683 only a read error rejects it; 17134 makes no root check). Only when
neither copy passes does a second pass run without the root check; when neither passes that either, the mount fails
(0xC0000032, STATUS_DISK_CORRUPT_ERROR).

The rule as 26100.8115 implements it, written out from the decompilation (17134, 26100.8521 to .9974 and Insider
29574, 29659 and 29683 make the same choice between two valid copies):

```
strict = 1
best = none
repeat:
  for i in (0, 1):                        # superblock list order
    read slot i's record                  # a total device failure fails the mount here
    if the read failed or the record is not valid: skip it
                                          # valid: self-checksum, bounds; while strict, roots 0xC, 7, 8
    if best is none: best = i
    elif clock(i) > clock(best): best = i # CHKP+0x60, unsigned, strictly greater
  if best is not none: stop
  if strict == 0: fail the mount (0xC0000032)
  strict = 0                              # second pass, without the root check
use best; the next checkpoint is written to the other slot
```

The selection clock is **CHKP+0x60**, not the page-header clock at +0x10: the slot loop and
`ChooseCheckpointRecord<0>` (win11 10.0.26100.8115, `1401051b0`) both compare `*(unsigned long long *)(record +
0x60)` only.

`ChooseCheckpointRecord<0>` is a three-way comparator that returns GenericEqual on a tie. On the 26100 and Insider
builds it chooses between the data copies of one slot on mirrored or parity storage, and every caller treats an equal
result as "keep the current choice".

A tie is a normal state (two equally current copies), not corruption:

- a volume in the corpus exhibits one naturally, with both copies at clock 662, in the shape the driver's own
  mount-time rewrite of the checkpoint leaves (the copies differ only in their self-address fields and checksum);
- on every ReFS volume of the test corpus slot 0 also holds the lower LCN, so "slot 0" and "lowest LCN" pick the same
  copy there.

Because selection is keyed on +0x60, a copy whose +0x10 and +0x60 disagree is worth attention: the two match on every
corpus volume measured, so a divergence is not a normal state.

The tools make the same choice (slot order, the copy's own checksum and record tests, a strictly greater +0x60). They
also check roots 0xC, 7 and 8 of each copy, and when a 26100 build's first pass would reject the copy in use they say
so and exit 2, but they still read it.

**What "valid" means: the record tests.** Every pass tests each copy (`ValidateCheckpointRecord`), before and
independently of the first pass's root reads; the record is one cluster:

- its self-checksum;
- the root count n at +0x90: more than 4 and at most the record size / 4;
- with flag 0x0200 (the indirect root-offset table; 26100 and Insider builds only): the volume version 3.11 or later,
  the table (offset +0x94, length +0x98) inside the record, +0x98 at least 4 and at least 4n;
- each of the n root offsets: at least 4n + K (K = 0x98 on 17134, 0xA8 on 26100, 0xB0 on Insider 29574), 8-byte
  aligned, the 0x28-byte descriptor and its digest (length at descriptor +0x24) inside the record;
- the area at +0x88 / +0x8C:
  - on 26100 and Insider, length 0, or starting at or after 4n + K and ending inside the record;
  - on 17134, offset and length each inside the record, starting at or after 4n + K unless the length is 0, and
    ending inside it.

26100.8972, .9444, .9549 and .9711 add two tests, each behind a feature switch the volume does not record: fewer than
0x1B roots, and every root digest at most 0x20 bytes. The tools state them when a copy fails one, and they take no
part in the choice.

17134's tests apply only to the volumes it mounts (version 3.4 and lower). Read on 17134, 26100.8115, .8972, .9549
and Insider 29574.

## CHKP Flags (offset 0x78)

| Bit | Mask | Meaning | First Version |
|-----|------|---------|---------------|
| 1 | 0x0002 | Base flag (set on every record measured) | v3.4 |
| 7 | 0x0080 | Native format marker (not set on upgraded volumes) | v3.10 |
| 9 | 0x0200 | Indirect root list mode: the root-offset table at +0x94 (offset) / +0x98 (length) | 3.11 (written by the driver from 3.11; the corpus has it on 3.14) |
| 10 | 0x0400 | The record carries the rollback-protection fields at +0x9C / +0xA0 ([below](#flags-0x0400-and-0x2000)) | 3.13 (the corpus: 3.14) |
| 4 | 0x0010 | Deduplication enabled | v3.14 (the dedup volumes) |
| 5 | 0x0020 | Weak references enabled | v3.14 (the dedup volumes) |
| 6 | 0x0040 | Developer volume | — |
| 8 | 0x0100 | Dirty-state tracking enabled | v3.14 (the dedup volumes) |
| 13 | 0x2000 | The record carries Insider's attestation HMAC structure at +0xA4 / +0xA8 ([below](#flags-0x0400-and-0x2000)) | Insider |

### Flags 0x0400 and 0x2000

**0x0400** marks the rollback-protection fields: +0x9C = the protection blob's offset, +0xA0 its length, both 0 when
there is no blob.

- The driver sets the flag on a volume of format 3.13 or later; the mount checks the blob when there is one.
- It is set on every v3.14 record measured, with both fields 0, and on none formatted at 3.4 to 3.10.

**0x2000** marks Insider's attestation HMAC structure: +0xA4 = its offset, +0xA8 its length (0x48 on every corpus
record that has the flag).

- It is written by the Insider drivers read (29574, 29659, 29683); no 26100 build read has this code.

### Composite Flag Values by Version

| Version | Flags (hex) | Flags (binary) | Key Bits |
|---------|-------------|---------------|----------|
| v3.4 | 0x0002 | `0000 0000 0010` | Base |
| v3.7 | 0x0002 | `0000 0000 0010` | Same |
| v3.9 | 0x0002 | `0000 0000 0010` | Same |
| v3.10 | 0x0082 | `0000 1000 0010` | +native format |
| v3.14 native | 0x0682 | `0110 1000 0010` | +indirect roots +0x400 |
| v3.14 upgraded | 0x0602 | `0110 0000 0010` | +indirect +0x400, missing native |
| v3.14 dedup | 0x07b2 | `0111 1011 0010` | 0x0682 + dedup (0x010) + weak references (0x020) + dirty-state tracking (0x100) |
| Insider (native) | 0x2682 | `0010 0110 1000 0010` | native v3.14 + attestation HMAC (0x2000) |
| Insider (upgraded) | 0x2602 | `0010 0110 0000 0010` | upgraded (no 0x080) + attestation HMAC (0x2000) |

On the volumes measured, the **0x0080 bit separates native-formatted v3.10+ volumes (set) from upgraded volumes
(clear: those upgraded from 3.4 and from 3.9)** — a second signal next to the
[volume information](../attributes/VOLUME_INFORMATION.md) driver-version stamp.

## Direct vs Indirect Root Access

The 13 root table pointers have two encodings, selected by flag bit 0x0200:

- **Without 0x0200 (direct)**: CHKP+0x94 holds **13 `u32` in-page offsets**, one per root. Each names a
  position *within the same checkpoint page* where that root's page reference sits; the reference is
  `desc_len` bytes long (`desc_len` from CHKP+0x5C). The offsets are at 0x94 — the page references are not.
- **With 0x0200 (indirect)**: CHKP+0x94 holds the u32 **offset within the same checkpoint record** of the
  root-offset table, and +0x98 its length; the table's 13 `u32` entries each give the in-record offset of one root's
  page reference. It is not a pointer to a separate page: the value (0xA8 or 0xB0) is far smaller than one page.
- **In both modes** the references are `u32@CHKP+0x5C` bytes long (104, 48 or 72), and they follow one another; that
  size equals the spacing on every checkpoint copy measured, and a literal 92-byte (0x5C) spacing occurs on none.

**Critical**: A parser must read the flag bit **before** decoding the root list. Reading an indirect-mode checkpoint
as direct (or vice versa) yields 13 wrong root addresses.

## 13 Root Table Pointers

| Index | Table | Table ID | Schema | Addressing | Failover Pair |
|-------|-------|----------|--------|------------|---------------|
| 0 | Object ID Table | 0x02 | 0xe030 | Virtual | #5 |
| 1 | Medium Allocator | 0x21 | 0xe010 | Virtual | -- |
| 2 | Container Allocator | 0x20 | 0xe010 | Virtual | -- |
| 3 | Schema Table | 0x01 | 0xe060 | Virtual | #9 |
| 4 | Parent-Child Table | 0x03 | 0xe040 | Virtual | -- |
| 5 | Object ID Table (second copy) | 0x04 | 0xe030 | Virtual | #0 |
| 6 | Block Refcount | 0x05 | 0xe0b0 | Virtual | -- |
| 7 | Container Table | 0x0B | 0xe0c0 | **Real (physical)** | #8 |
| 8 | Container Table (second copy) | 0x0C | 0xe0c0 | **Real (physical)** | #7 |
| 9 | Schema Table (second copy) | 0x06 | 0xe060 | Virtual | #3 |
| 10 | Container Index | 0x0E | 0xe100 | Virtual | -- |
| 11 | Integrity State | 0x0F | 0xe080 | Virtual | -- |
| 12 | Small Allocator | 0x22 | 0xe010 | **Real (physical)** | -- |

Roots 7, 8, and 12 use real (physical) LCNs as a bootstrap exception; every other root uses
[virtual addressing](../concepts/virtual_addressing.md) (VLCN → PLCN via the Container Table).

**Failover pairs**: 0/5 (Object ID), 3/9 (Schema), 7/8 (Container). Block Refcount (#6) has no failover pair.

Each pair is two copies of one table, each checked against its own reference in the checkpoint; neither copy is a
"primary" or a "duplicate":

- the Container Table pair is opened by slot: refs.sys reads root 7 (slot 0) unless it fails, then root 8 (one
  reading);
- which copy of the Object ID and Schema pairs the driver reads first was not read;
- the tools read roots 0 and 3, and the Object ID Table from root 5 when root 0 fails.

The Container-Table failover pair (roots 7 & 8) is the **set** {0x0B, 0x0C} at roots {7, 8}: the common ordering is
root 7 = 0x0B / root 8 = 0x0C, but on one volume measured the two are swapped, so the invariant is the set, not a
fixed index→Table-ID order.

## Version Echo (offset 0x50)

| Scenario | Value |
|----------|-------|
| Native v3.14 | 0x000E0003 (minor=14, major=3) |
| Upgraded volumes | 0x00000000 |
| v3.4 through v3.9 | 0x00000000 |

The version echo distinguishes natively formatted v3.10+ volumes from upgraded ones.

After choosing a copy, refs.sys 26100 and Insider fail the mount when its version (+0x50, +0x52) is above the
version the boot sector records, or when either half is above 0xFF (0 on an upgraded volume passes). The tools read
such a volume anyway and say so: a condition of the view, exit 2 in every command.

## Virtual clock values

The clock at +0x60 counts committed checkpoints, not file operations: how fast it grows depends on how often the
volume checkpoints, so its value does not tell how many operations a volume saw.

On the corpus volumes the clock of the copy in use runs from a few dozen to about ten thousand; an upgrade to 3.14
advanced it by a few dozen checkpoints on the upgraded volumes measured.

## Parsing Sequence

1. Read 80-byte page header; verify signature is `"CHKP"`
2. Read version at 0x54/0x56
3. Read page reference size at 0x5C (the length of each root reference)
4. Read CHKP flags at 0x78
5. Check bit 0x0200 to determine direct vs indirect root mode
6. Parse the 13 root pointers at 0x94 — directly when flag 0x0200 is clear, otherwise follow the `u32`
   there to the table of 13 in-page offsets — and read one page reference at each offset (`u32@CHKP+0x5C` bytes)
7. Optional cross-check: the reference at the offset in **0x58** is the checkpoint's own self-descriptor —
   its first LCN slot equals the checkpoint's LCN. A mismatch means the page is not the checkpoint you
   think it is
8. For each root, use the appropriate addressing mode (virtual for most, physical for roots 7, 8, 12)

## Cross-references

- [Superblock (SUPB)](supb.md) -- the SUPB stores pointers to the two CHKP locations
- [Page References](page_references.md) -- the page reference size at CHKP+0x5C selects the format
- [Object Table](object_table.md) -- root 0 (and failover root 5)
- [Container Table](container_table.md) -- root 7 (and failover root 8)
- [Container Index](container_index.md) -- root 10
- [Allocators](allocators.md) -- roots 1, 2, 12
- [Schema Table](schema_table.md) -- root 3 (and failover root 9)

## Evidence

The page header signature, the 13 root-table identities, the version fields, and the page-reference sizes are
confirmed in the decompiled driver and the binary string literals. `ValidateCheckpointRecord` checks the flag bits at
CHKP+0x78; the highest-clock selection is made in `ReadLatestCheckpoint`'s slot loop (17134 calls
`ChooseCheckpointRecord` there; the 26100 and Insider builds compare inline).

The flag composites, the version echo, the real-LCN bootstrap exception for roots 7/8/12, and the field offsets were
re-measured directly on disk across the corpus.

The counts behind the text:

- the self-descriptor at +0x58: verified on 95 of 95 corpus images (every version); `0x88 == 0x58 + 14 × 0x5C` on
  76 of 95;
- the root-reference spacing equals `u32@CHKP+0x5C` on 226 of 226 checkpoint copies: 104 (0x68) on 32 copies, 48
  (0x30) on 186, 72 (0x48) on 8; a literal 92-byte spacing on 0;
- the root count is 13 on all 248 checkpoint copies of the 124 corpus volumes;
- the flag composites, on those 248 records: 0x0682 on 198, 0x0002 on 24, 0x2682 on 8, 0x0602 on 6, 0x07B2 on 6,
  0x0082 on 4 and 0x2602 on 2 (both copies of `win1122h2test_afteropenedwithinsider`);
- the Container-Table pair swapped (root 7 = 0x0C, root 8 = 0x0B) on the 2 TB `win11refs2tmillionsofactions`;
- the allocator clock: the two copies differ in it by exactly 1 on 18 of 18 volumes byte-compared;
- the record layout (`analysis/reports/v1.13.2/DRIVERS_10_1/chkp_0x400_census.jsonl`, 2026-11-12; both copies of
  the 124 ReFS volumes of the corpus, 248 records): flag 0x0200 on 220 records of 108 volumes, all v3.14 (three of
  those volumes carry a hand-edited version field). +0x94 = 0xA8, +0x98 = 0x38, +0x58 = 0xE0 on 210 of them (200 on
  4K-cluster volumes, 10 on 64K); +0x94 = 0xB0, +0x98 = 0x38, +0x58 = 0xE8 on the other 10 (8 on 4K, 2 on 64K),
  which are the records with flag 0x2000: both copies of `winsider`, `winsiderv2`, `wininsiderrefs2t`,
  `wininsiderrefs8gtest2` and `win1122h2test_afteropenedwithinsider`. On those 10, +0xA4 = +0x88 + 0x20 (0x3A8
  with +0x88 = 0x388 on 8 records, 0x4F8 with +0x88 = 0x4D8 on 2), +0xA8 = 0x48, and +0x9C / +0xA0 are 0. The 28
  records without flag 0x0200 (formats 3.4, 3.7, 3.9 and 3.10) read +0x58 = 0xD0. +0x88 / +0x8C are both 0 on 44
  records formatted at 3.14;
- the writers: `FormatCheckpointRecord` on 26100.9818 (`analysis/static/decompiled/win11_26100_9818_7113ffc2/refs.decomp.c`
  :217004-217013: the table length, the version test 0x30B, +0x94 / +0x98, +0x58), 26100.8115 (:217423) and
  26100.9444 (:216656) write +0x94 = 0xA8; Insider 29574 (`insider_67a922ae/winsider-refs.decomp.c` :193783),
  29659 (`insider_29659_7a55449a` :39498) and 29683 (`insider_29683_7f35b697` :156459) write +0x94 = 0xB0 and
  +0x58 = 0xB0 + the table length. The HMAC structure's writer is the Insider builds'
  `CmsVolumeAttestation::CreateEmptyHmacStructure`;
- the clock of the copy in use runs from 27 to 10,618 on the 124 corpus volumes; an upgrade to 3.14 advanced it by
  35 to 41 checkpoints on the upgraded volumes measured;
- slot 0 holds the lower LCN on all 124 ReFS volumes of the corpus.

- The change journal cursor: `RefsCheckpointVolume` passes the volume's journal position to the checkpoint writer, and
  `RefsSetupUsnJournal` reads it back at mount. On the corpus (124 volumes, both checkpoint copies) the Next USN equals
  the journal's next USN on 66 copies of 33 volumes; on the two wrapped journals (`winsider`, `winsiderv2`) the First
  USN is the oldest record's and the wrap fields map it just past the write head; on the 6 volumes where records lie at
  or past the Next USN, the journal was re-created and those records belong to the earlier journal: no record of the
  current journal lies at or past it on any of the 40 volumes whose checkpoint copy in use carries the area; the area is zero on every volume without a journal, and absent on 44
  copies (both copies of 19 journal-less 3.14 volumes, and of three volumes imaged while mounted or rebuilt).

See [how this was verified](../methodology.md) for the method.

<!-- findings: MD_USN_SA_002, CT_ALLC_002, FS_CHKP_001, FS_CHKP_002, FS_CHKP_003, FS_CHKP_004, FS_CHKP_006, FS_CHKP_007, FS_CHKP_008, FS_CHKP_011, FS_CHKP_013, FS_CHKP_021, FS_CHKP_RA_001, FS_CHKP_RA_002, FS_CHKP_RA_005, FS_CHKP_RA_008, FS_CHKP_RA_009, FS_CHKP_RA_011, FS_CHKP_RA_012, FS_CHKP_RA_013, FS_CHKP_RA_015, FS_CHKP_RA_016, FS_VBR_RA_009 -->
