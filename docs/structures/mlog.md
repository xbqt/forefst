# Metadata Log (MLog)

The MLog implements write-ahead logging for atomic metadata updates.

It is **redo-only**: the log holds redo records, crash recovery replays committed transactions, and there is no
undo pass — copy-on-write keeps prior pages intact, so undo is unnecessary.

Each MLog data record (one 4 KiB log block) is a *LogCore data record* nesting four layers:

1. a record header;
2. an entry header;
3. one or more merged redo blocks;
4. the inner redo records that carry the operations.

refs.sys sets the commit flag on the last record of each transaction; on the volumes measured each redo block held
one transaction.

## Record structure — four layers

Each MLog data record is a single LogCore data record, in one 4 KiB log block. It is not a metadata page: it does
not begin with the common page header. The on-disk format is **four nested layers**. All
offsets are version-invariant — the only version difference is the entry-header payload-offset *value*
(Layer 2 +0x28).

```text
record
 ├─ 0x00 Layer 1: LogCore record header (0x78 = 120 bytes)
 ├─ 0x78 Layer 2: entry header (56 bytes; 64 on Insider)
 ├─ 0xB0 Layer 3: redo block _SmsRedoHeader (0xB8 on Insider)
 └─ Layer 4: _SmsRedoRecord entries
```

### Layer 1 — LogCore record header (`record+0x00`, 120 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Signature | `"MLog"` (0x676f4c4d) |
| 0x04 | 4 | Format magic | The volume signature, tested by equality; not a checksum |
| 0x08 | 4 | Constant 1 | 1 on every data record and control copy of the corpus volumes; `LogValidateEntryHeader`, which tests every record's header, does not read it (the log version refs.sys checks is the control payload's +0x40) |
| 0x0C | 4 | Log block size | 0x1000 (4K) always — not the volume cluster size |
| 0x10 | 16 | UUID | Log-instance UUID (per volume) |
| 0x20 | 4 | Log open count | The control area's +0x38 when the record was written: 1 when the log is created, +1 at each read-write open of the log, so a record names the session that wrote it |
| 0x24 | 4 | Reserved | 0 |
| 0x28 | 8 | **LSN** | This record's log sequence number = (generation << 32) \| log-block offset |
| 0x30 | 8 | Previous LSN | LSN of the previous record; 0 in the first record of a mount session. A wrap keeps the chain |
| 0x38 | 4 | Total length | Whole record, in **4K log blocks** |
| 0x3C | 4 | Header length | Non-payload span, in 4K log blocks (≤ 0x38) |
| 0x54 | 4 | Entry-header offset | Constant **0x78** (anchor to Layer 2) |

### Layer 2 — entry header (`record+0x78`)

56 bytes on v3.4–v3.14, **64 bytes on Insider 29574**. Offsets are entry-relative (the record offset
in parentheses):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 (0x78) | 8 | LSN | Copy of record+0x28 |
| 0x08 (0x80) | 8 | **Record integrity value** | The per-record integrity value, an interleaved u64 XOR-fold. **Reproducible:** zero this field, then for each log block of `le32(rec, 0x0C)` bytes (`0x1000` on every volume, independent of cluster size) fold each little-endian u64 into `acc[i mod 4]`, take `v = acc0^acc1^acc2^acc3` and reduce it to `(v >> 32) ^ (v & 0xFFFFFFFF)`. Blocks chain: the next block's `acc[0]` is seeded with a **rotate-left-1** of the previous block's result. `forefst mlog --stats` recomputes and verifies it |
| 0x18 (0x90) | 8 | Previous LSN | Copy of record+0x30 |
| 0x20 (0x98) | 4 | Payload length | Redo-block bytes (control records carry 0xe48) |
| 0x28 (0xA0) | 4 | Payload offset | From entry base = **0x38 (v3.4–v3.14) / 0x40 (Insider)** |
| 0x2C (0xA4) | 4 | Entry region size | Record bytes − 0x78 on a data record; 0 on a control record |
| 0x30 (0xA8) | 4 | **Record type** | **2 = data record** (carries a redo block), **1 = control record** |

The redo block starts at `record + 0x78 + payload_offset` = **record+0xB0** (v3.4–v3.14) /
**record+0xB8** (Insider). Robust, version-safe pointer:
`redo = record + le32(record,0x54) + le32(record + le32(record,0x54), 0x28)`, taken only when the entry
type (== 2) is a data record.

### Layer 3 — redo block `_SmsRedoHeader`

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | total_size (u32) | Bytes of the block's records, the header excluded; the block occupies first_record_offset + total_size bytes |
| 0x04 | 4 | first_record_offset (u32) | Offset to the first inner record (= 8) |

A data record's payload holds one or more of these blocks, merged (up to 15; see *Iteration logic* below). On
the volumes measured each block held the records of one transaction (start → operations → commit).

### Layer 4 — `_SmsRedoRecord` (minimum 0x38 = 56 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | record_size (u32) | Size of this inner record |
| 0x04 | 4 | opcode (u32) | Redo operation type |
| 0x08 | 4 | table_key_path_length (u32) | > 0: the record names its table by a key path (component 0 = the table's object id). 0: it applies to the redo pass's current table (below) |
| 0x10 | 4 | value_component_count (u32) | Number of value data segments following key components |
| 0x18 | 8 | virtual clock (u64) | The volume's checkpoint virtual clock when the record was added (`CmsTxMemLog::AddRedoRecord`; the checkpoint's +0x60 counts the same clock) |
| 0x20 | 8 | allocator clock (u64) | The volume's allocator clock when the record was added (`CmsTxMemLog::AddRedoRecord`; the checkpoint's +0x68 holds the same clock). Not an object id, and not a table: records of different tables carry the same value |
| 0x2C | 4 | flags (u32) | Bit 0 = transaction start, bit 1 = commit (`CmsMemLog::MergeTxLog`); bit 2 = the first record of a block merged into the previous one; bit 12 or 13 on a transaction's first record (the choice not traced); bit 16 makes the redo pass drop the record's last value, and no writer of it was found |
| 0x38+ | var | payload | Key data, value data (opcode-specific) |

**The table a record applies to.** With a path, component 0 of the path is the object id of the outermost table,
where `ObjectIdFromRedoHelper` reads it; further components name a table embedded in it. With a path length of 0,
the record applies to the table the redo pass keeps current, normally the previous record's: the record's writer
leaves the path out when the table is the previous record's in the same transaction. The records after which no
table is current, and how the current table carries from one redo block to the next, are under
[MOVE vs RENAME](mlog_redo.md#move-vs-rename--read-from-the-files-own-records) on the redo-records page.

**The allocator clock at mount.** A redo block whose first record starts a transaction and names table 0x1, 0xB or
0xE is redone only if that record's `+0x20` is at or above the chosen checkpoint's allocator clock
(`ShouldPerformRedo`; 17134, 26100, Insider 29574).

> **Note (the equally-sized 56-byte structures):** the Layer 2 entry header and the Layer 4
> `_SmsRedoRecord` are *both* 56 bytes but are distinct. The **entry header carries the per-record
> checksum (at +0x08)**; the `_SmsRedoRecord` does not (it starts with record_size/opcode). The
> literature's "56-byte log record header with checksum" is the entry header; the "120-byte entry
> header" is the Layer 1 record header.

### Iteration logic

A log payload holds a **chain of merged redo blocks** — up to 15 — and each block's records are budgeted
by that block's own `total_size`. Both loops are taken from the driver.

**The chain (`ForEachBlockInMergedBlock`):**

```text
remaining = payload_length
if remaining < 8: error
while (block.total_size != 0) and (block.total_size <= remaining):
 process(block)
 remaining -= block.first_record_offset + block.total_size
 if remaining < 8: stop
 ptr += block.first_record_offset + block.total_size      # the NEXT block
```

**The records inside one block (`ForEachRedoInBlock`):**

```text
if (total_size + first_record_offset < 8) or (total_size < 0x38): error
budget = total_size                    # first_record_offset locates the first record;
ptr    = header + first_record_offset  # it is NOT subtracted from the budget
while (record.size <= budget) and (record.size != 0):
 process(record)
 budget -= record.size
 if budget < 0x38: stop
 ptr += record.size
```

The **last record of a block carries the commit flag** (bit 1 at `_SmsRedoRecord+0x2C`) on the volumes
measured: refs.sys sets it on the last record of each transaction (`CmsMemLog::MergeTxLog`), and each measured
block held one transaction. Measured on a dirty lab volume: every one of its redo blocks (in chains of up to 15)
closes exactly under this budget, and the last record of every one carries the commit flag.

## Overall layout

The MLog is split into a control area and a data area.

| Component | Description |
|-----------|-------------|
| Control area | Two control copies, each one 4K log block with the `MLog` signature: the log start and end, the write sequence, the log open count, the data-area bounds (see *Control page layout*) |
| Data area | Circular buffer of data records in 4 KiB log blocks; each record carries one or more merged redo blocks |

**A record's LSN** is (generation << 32) | the offset of its first 4 KiB block in the data area. The generation goes up
by one in two cases: at a wrap, where the offset restarts at 0 (`LogCoreWriteDataRecord`; the scan then looks for the
next record at the next generation's block 0), and when a log is begun to follow an earlier one, which keeps the
offset (`MlLogOpenLog`; refs.sys 26100.9818). So a generation is not a count of laps: on one sample volume
generations 1 to 4 lie side by side in a log that never wrapped, the offsets running on at each change.

## MLog location

refs.sys does not find the MLog by a path or a fixed address: it reads the log's place from the Logfile
Information Table, a failover pair of OID 0xA and OID 0x9 in the Object Table (see [System OIDs](system_oids.md)
and [How refs.sys finds, reads and opens the log](#how-refssys-finds-reads-and-opens-the-log) below).

The place varies by volume, not by format version:

- the second control copy's LCN alone varies from volume to volume, and is 0x31 on v3.4 and v3.14 volumes
  alike;
- the data area starts, for example, at cluster 0x10000 on a v3.4 volume, at 0x8000 on v3.14 volumes with 4 KiB
  clusters and at 0xC00 on a 64 KiB-cluster volume.

Read the table, never assume an LCN.

**Data area addressing is physical.** Unlike most ReFS structures, MLog data area LCNs (from the Logfile
Information Table key=1 row) are physical cluster addresses — no container translation is needed.

**Data-area block packing (4 KiB log blocks).** The data area is *addressed* in volume clusters, but the
MLog's own I/O unit — the **log block**, which is exactly one LogCore record — is **4 KiB always**,
independent of the cluster size (it is `record+0x0C`, hard-set to `0x1000` by `MlLogOpenLog`).
Consequences:

| Volume cluster | Log blocks per cluster | LSN low-32 |
|----------------|------------------------|------------|
| 4 KiB | 1 (block = cluster) | = cluster offset within the data area |
| 64 KiB | **16** (cluster = 16 log blocks) | = the **4 KiB-block** index within the data area |

On a 64K-cluster volume each cluster holds 16 consecutive log records with consecutive LSNs, so a scanner
must iterate **4 KiB blocks**, not clusters — otherwise a 64K-cluster log exposes only 1/16 of its
records. On 4 KiB-cluster volumes the two are identical.

### How refs.sys finds, reads and opens the log

Read on 26100.8115 (`InitializeVolumeRedoLog`, `CmsDurableLog::Start`, `LogCoreReadControlArea`,
`LogValidateEntryHeader`, `MlLogOpenLog`); 17134, 26100.9444 and Insider 29574 make the same tests unless a build is
named.

1. **The Logfile Information Table.** refs.sys opens OID 0xA and OID 0x9 as a failover pair: it needs both object
   records (with either missing it does not start the log) and reads the table from OID 0xA, or from OID 0x9 when
   OID 0xA's copy fails. The row with the 4-byte key 1 gives the log, in u64 values: [0] the data area's first LCN,
   [1] its end LCN, [2] its size in clusters, [3] and [4] the two control copies' LCNs. refs.sys
   takes [0], [2], [3] and [4], never [1]: the data area is [start, start + size). It does not start the log without
   that row, with a value shorter than 0x30 bytes, or with a size below 0x50 clusters, and it refuses a size in bytes
   of 8 KiB or less or not 4 KiB-aligned. On every corpus volume measured: both OIDs, one row 1 with a 4-byte key
   and a 48-byte value, a size of at least 0x50 clusters, and [1] = [0] + [2].
2. **Reading a control copy.** Each copy is read as one 4 KiB log block at the LCN the row gives (an LCN of 0
   included), and its record header is tested before its integrity value: +0x04 equal to the volume's signature,
   +0x0C = 0x1000, +0x54 at least 0x78 and inside both the record's blocks and the 4 KiB read, +0x3C not more than
   +0x38, and the blocks +0x3C asks for inside the 4 KiB read; the payload length must be 0xE48. 17134 makes neither
   test against the 4 KiB read; 26100.8972, .9444 and .9549 add one behind a feature switch of the system
   (0x1000 − +0x54 > 0x37). A copy that fails a test, or whose integrity value does not verify, is not used; which of
   the copies that pass is used is under *Control record layout*.
3. **Opening.** `MlLogOpenLog` opens an existing log only when the copy in use holds log version 1 (+0x40), a data
   area (+0x08 / +0x10) equal to the table's range, flags bit 0 set, and — on the 26100 and Insider builds, not on
   17134 — a log start (+0x18) at or before the chosen checkpoint's +0x70. Insider 29574, 29659 and 29683 also require flags bit 0x20
   (HMAC-protected records) when the mounting system asks for it, a setting of that system, not of the volume.
4. **The log end and the data area.** A record's LSN offset (its low 32 bits) is its 4 KiB block in the data area,
   so a log end (+0x20) whose offset lies past the data area names no block of the log.

On every corpus volume measured, both control copies pass every test of points 2 and 3, the newer copy is the one
in use, and the log end lies inside the data area.

**What the tools do.** `mlog`, `timeline` and `summary --mlog` make the same tests and use the same copy.

- A test the volume fails is stated with the value read and what refs.sys requires, and the command exits 2; the
  tools still read what they can.
- When no control copy can be read, every mode says so and exits 2; when none verifies, the newest readable copy is
  read, called unverified, and the command exits 2.
- A test whose input the image does not hold (the mount state, the system's HMAC setting, test hooks, the other
  copies of a mirrored device) is not made.

The tools also compare the tail of this log — its newest record plus that record's length — with the log end: the
records in between were allocated and are missing, a finding worded as missing, never as destroyed (a crash can
leave an allocated record unwritten). The log start does not bound that range, and records written after the
control area's last write are not covered.

Only this log instance's records count (its format magic and UUID). With no readable control copy, records with
another format magic are left out and counted, and an earlier log of the same volume cannot be told from the
current one.

## Verifying a record

Every log record — control record and data record alike — carries an 8-byte integrity value at **entry header
+0x08** (= record+0x80, the entry-header offset at record+0x54 being 0x78). The driver recomputes it before
replaying a record, and it can be recomputed from the record alone:

```text
field_off = le32(rec, 0x54) + 8           # the integrity value's own position
block     = le32(rec, 0x0C)               # 0x1000 on every volume, whatever the cluster size
zero the 8 bytes at field_off
result = 0
for each block of `block` bytes:
    acc = [rotate_left_1(result), 0, 0, 0]     # chain seed; 0 for the first block
    for i, word in enumerate(little-endian u64 words of the block):
        acc[i mod 4] ^= word
    v      = acc[0] ^ acc[1] ^ acc[2] ^ acc[3]
    result = (v >> 32) ^ (v & 0xFFFFFFFF)
```

A record is exactly one log block, so the chain seed is 0 in practice. The record **type** at entry header
+0x30 says which kind of record it is — **1** for a control record, **2** for a data record; no other value
occurs on disk.

Across the image corpus (ReFS 3.4 → 3.14, 4 K and 64 K clusters) this reproduces the stored value on every data
record and every control copy.

> **An integrity check, not a signature.** It detects any single altered bit — a flip at any of a record's
> 4,096 offsets is caught — but for a one-block record the value is the XOR of all the record's 32-bit words, so it
> is blind to any reordering of those words and to any set of changes whose XOR cancels. It happens without any
> tampering: on one corpus volume (64 KiB clusters) the two control copies differ in two bits, the write sequence and a
> host-information field each one apart, and both store the same value. Equal stored values do not mean equal copies.

`forefst <image> mlog --stats` runs this over every record in the data area and over both control copies. It lists
the failing records with their stored and recomputed values (only the first ones when there are many), and a
failing record is a finding: the command exits 2.


## Control record layout

The control area holds two copies of one control record, each one 4K log block. Of the copies whose integrity value
verifies, refs.sys uses the newer (payload +0x00; a tie keeps the first copy), except that a copy with flags bit 1
set (payload +0x3C) is taken whatever its sequence. A control record has the record header (Layer 1) and the entry
header (Layer 2) of a data record, with these values:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Signature | `"MLog"` ASCII (0x676f4c4d) |
| 0x04 | 4 | Format magic | The volume signature (copied from the log handle, validated by equality), not a checksum. The same in every record this volume's log writes; differs between volumes. A reformatted volume can still hold records of an earlier log with the earlier value. The real per-record checksum is the XOR-fold at the entry header +0x08 (record+0x80). |
| 0x08 | 4 | Constant 1 | Written as 1 and never read by refs.sys; the log version refs.sys checks is payload +0x40 |
| 0x0C | 4 | Log block size | **0x1000 (4K) always** — the log's I/O unit, **NOT the volume cluster size** (it stays 0x1000 even on 64K-cluster volumes). |
| 0x10 | 16 | UUID | The log instance's UUID (equal to payload +0x28) |
| 0x20 | 4 | Log open count | The open count of the session that wrote the record: equal to payload +0x38 |
| 0x24-0x37 | 20 | *Zero* | A data record's LSN (0x28) and previous LSN (0x30) are 0 in a control record |
| 0x38 | 4 | Total length | 1: the record is one 4K log block |
| 0x3C | 4 | Header length | 1 |
| 0x40-0x53 | 20 | *Zero* | |
| 0x54 | 4 | Entry-header offset | 0x78 (=120); the payload is reached through it (see below) |
| 0x58-0x7F | 40 | *Zero* | Includes the entry header's LSN (0x78) |
| 0x80 | 8 | **Record integrity value** | The record's own XOR fold, at entry header +0x08. Per **record**, not per volume: it changes with the record's content. Only the low 4 bytes are ever used — the upper 4 are zero on every record measured. See *Verifying a record* above. |
| 0x88-0x97 | 16 | *Zero* | Includes the entry header's previous LSN (0x90) |
| 0x98 | 4 | Payload length | 0xE48: refs.sys takes no record with another length as a control record |
| 0xA0 | 4 | Payload offset | From the entry header: 0x38 (v3.4–v3.14) or 0x40 (Insider 29574), so the payload starts at record offset 0xB0 or 0xB8 |
| 0xA4 | 4 | Entry region size | 0 |
| 0xA8 | 4 | Record type | 1 = control record |

Measured on the 248 control copies of the 124 ReFS volumes of the test corpus (v3.4 to Insider 29574, 4K and 64K
clusters): every constant and zero range above holds on each copy, and header +0x20 equals payload +0x38 on each.

The payload is reached by reading the entry-header offset at record+0x54, then the payload offset at
entry_header+0x28 (`data_off = entry_header_offset + payload_offset`). It is a byte copy of the log's in-memory
handle:

| Payload+Offset | Size | Field | Description |
|----------------|------|-------|-------------|
| +0x00 | 8 | Sequence | The control-area write sequence: +1 at every control write |
| +0x08 | 8 | Data area start | In **4K log blocks** from the volume start (= clusters on a 4K volume; 16 per cluster on a 64K volume) |
| +0x10 | 8 | Data area end | Same unit |
| +0x18 | 8 | Log start | Where the log starts, as of the last control-area write. It is not the end of the newest record, and replay after an unclean shutdown does not begin here: it begins at the chosen checkpoint's +0x70 |
| +0x20 | 8 | Log end | The LSN the next record takes, as of the last control-area write (on Insider 29574: the last write that refreshed the staged copy; its two HMAC writers write without refreshing it). A field of its own, advanced when a record is allocated |
| +0x28 | 16 | Log UUID | The log instance's UUID; once the log is open, refs.sys rejects a record whose header UUID (+0x10) differs from it |
| +0x38 | 4 | Log open count (u32) | 1 when the log is created, +1 each time the log is opened read-write; each record's header +0x20 carries it, so a record names the session that wrote it. It counts opens, not writes (the write sequence is +0x00) |
| +0x3C | 4 | Log flags (u32) | bit 0 = per-record XOR checksums; bit 1 = the log was re-created from a checkpoint LSN and its end is not yet set (cleared when it is set); bit 5 (0x20, Insider 29574 only) = HMAC-protected records. Bit 0 alone on every control copy measured |
| +0x40 | 4 | Log version (u32) | refs.sys opens the log only when it is 1 |
| +0x44 | 8 | Host info (u64, unaligned) | Written when the log start advances: refs.sys stores its checkpoint virtual clock minus 1 |
| +0x4C–+0xE47 | — | *Zero* | No field is known: refs.sys zeroes +0x4C–+0xE43 at every start advance |

**The control area is a compact header.** It reserves 0xE48 (3,656) bytes (the payload length at record+0x98) and is
populated only up to payload +0x4C; the rest is zero. The log start and end advance with the log; the format magic,
the UUIDs, the area length and the data-area bounds stay the same between captures of the same volume. On most
volumes measured the log start, the log end and the end of the newest record are equal; two v3.14 log instances
(4K clusters) separate them. The driver readings are those of 17134, 26100 and Insider 29574; no 3.7–3.10 driver was
read.

## Redo records

What each redo opcode does, how a log payload's records are grouped into one action, and the time a row
carries are on [MLog redo records](mlog_redo.md).

## Data area sizing

| Metric | Observed range |
|--------|---------------|
| Data area | 256 MiB to 1 GiB on the volumes measured |
| Log records | about 150 on a fresh mini volume, up to a full data area on a heavily used one (262,144 records of 4 KiB in a 1 GiB log, which wraps); each holds one or more redo blocks |

## Recovery process

The `CmsRestarter` class performs:

1. **Analysis pass**: starts at the chosen checkpoint's log position (CHKP+0x70). It collects the log position of each
   tree-update record (opcode 0x12) older than the checkpoint's allocator clock, the first and last position of the
   committed transactions, and the container ranges committed transactions reserved; it keeps no dirty-page table,
   and the ranges of an uncommitted last transaction are dropped (17134, 26100.9444). On the 26100 and Insider builds
   the log is not opened when its start (control payload +0x18) is past that position (17134 does not test it)
2. **Redo pass**: replays the committed transactions' records in log order; a redo block whose first record starts
   a transaction on table 0x1, 0xB or 0xE is replayed only when its allocator clock is at or above the checkpoint's
   (see *Layer 4* above)

There is no undo pass. Copy-on-write ensures uncommitted transactions never overwrote prior state.

## Forensic value

The MLog is the **durable transaction log** — the on-disk record of committed activity. It matters forensically
because the committed metadata tree (what `files` and `summary` read) can **omit the most recent pending
activity**: an operation that has been written to the log but not yet folded into a checkpoint is present in the
MLog while it is still absent from the committed tree. Reading the MLog can therefore surface recent file
operations that the tree listing does not yet show.

- The MLog carries no before-images (unlike NTFS $LogFile), so it cannot undo a change; its older records do keep
  the values written at the time (a file's creation time, for instance), for as long as they survive in the circular
  buffer
- A small inline file's bytes are in the row update that wrote them, and the record outlives the file's deletion
  while it survives: on a lab volume three deleted inline files were recovered from the log byte for byte. `mlog` does
  not extract them.
- Opcodes reveal what operations occurred (inserts, deletes, modifications)
- The LSN range and record count indicate volume activity level
- The checkpoint's log position (CHKP+0x70) ties the checkpoint to the log: replay after an unclean shutdown starts there
- Payload classification maps each log payload's records to a derived action (CREATE, DATA_OR_REPARSE_WRITE, RENAME,
  MOVE, DELETE, and the low-level groups)
- OID-to-path resolution names the directory a record acts in (the table's object id), and a name row names the file
  in it
- Embedded timestamps in the InsertRow, UpdateDataWithRoot and UpdateRow values give a row its time; on the public
  samples most rows carry one (from about seven rows in ten to almost all)
- CSV export enables bulk analysis and timeline correlation with other forensic artifacts

**Tying the log to the Windows event log.** The machine that mounted the volume records each mount in its
`Microsoft-Windows-ReFS/Operational` log as event 4. Its fields include `LogRestartStartLsn` and `LogRestartLastLsn`
(generation:offset), a checkpoint clock, `LastShutdownWasDirty`, `MountStartTimeUtc` and `VolumeCorrelationId`, which
equals the volume's GPT partition GUID. On the two lab volumes whose event logs were kept:

- on one, each log session after the format starts at `LogRestartStartLsn`'s generation + 1 and its offset (4 of 4
  sessions), and the control area's open count less one equals the number of event-4 records for the partition after
  the format, so an event log and an image can be matched mount by mount;
- on the other, the one dirty mount held, `LogRestartStartLsn` is the chosen checkpoint's log position, where the
  replay started; the event's checkpoint clock and `LogRestartLastLsn` there are past the values the image holds, so
  what those two fields record is not settled.

## Tooling

MLog parsing is integrated into `forefst.py` (parsing + display). Available
modes via `forefst.py <image> mlog`:

| Mode | Description |
|------|-------------|
| Default | Control area summary + record statistics |
| `-v` | Per-record detail (opcode, name, allocator clock, flags, size) **plus a LogCore Record Headers table** for the first 64 log records in disk order — LSN, prevLSN, integrity value, type and payload offset, with `!chain` where `prevLSN[n] != LSN[n-1]` (the first record of a mount session, the wrap point, or a record of another log or a gap between them) |
| `--parse` | Decoded log payloads: the derived action, file paths, timestamps (a row is a log payload, which can merge up to 15 redo blocks; its time is the latest its records carry) |
| `--csv [FILE]` | One row per log payload: `Seq`, `Timestamp`, `TimeSource`, `DerivedAction`, `PathToday`, `ParentPathToday`, `Name`, `OID`, `Opcodes`, `OpcodesHex`, `RecordCount`, `PLCN`, `Block` |
| `--stats` | Record-integrity verdict (every data record + both control copies) followed by the opcode frequency histogram |
| `--json` | One document: `ReFSVersion`, `View`, `LogInstance`, `Control`, `ControlCopies`, `MLogInfo`, `EarlierLogs`, `DataArea`, `Integrity` (the same verdict as `--stats`), `Records` (every redo record once: its place, fields and decoded key) and `Transactions` (one entry per log payload with the `--csv` row's fields and values, plus `FirstRecordIndex` into `Records`; `Opcodes` / `OpcodesHex` are lists where the CSV joins them with `;`) |
| `--info` | Reference: all actions, opcodes, timestamps, schema names |
| `--raw-scan` | Raw page classification (debug) |

Validated across v3.4 / v3.7 / v3.9 / v3.10 / v3.14 / Insider volumes — all PASS the LogCore framing
check (entry header @0x78, type 2, one format magic per log; a reformatted volume can still hold records of an
earlier log with another), and every record's integrity value recomputes:
every data record and both control copies of every corpus volume, no mismatches. The 4 KiB-block scanner gives full coverage
on 64K-cluster volumes.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — the checkpoint's log position at CHKP+0x70, where replay starts
- [Page Header](page_header.md) — MLog records carry the `"MLog"` signature at offset 0x00 and a header layout of their own (the format magic at 0x04 is not a CRC), not the common 80-byte page header
- [Copy-on-Write](../concepts/copy_on_write.md) — why redo-only logging is sufficient
- [System OIDs](system_oids.md) — OID 0x9/0xA (Logfile Information Table) stores the MLog LCN range

## What the log physically contains

The data area holds LogCore records carrying redo blocks — the logged row inserts, deletes and updates described
above — not page images. Ordinary metadata pages found by a scan outside the data area are not part of the log.

## Evidence

The four-layer record format was decoded byte-for-byte from `LogCoreWriteDataRecord` (write),
`LogCoreScanDataRecord` / `LogValidateEntryHeader` (read/validate) and `LogInitializeEntryHeader`,
cross-confirmed in v3.4 (Win10), v3.14 (Win11) and Insider 29574, and verified on disk across the corpus. The
fixed log-block size (0x1000) is set by `MlLogOpenLog`. The
64K-cluster 4 KiB-block packing and the compact control header (about 98 % of its 3,656 bytes zero) are decoded
from the disk. The recovery passes come from the `CmsRestarter` class. The format magic is the volume signature,
not a CRC. The
compact control header, the second control entry's LCN and the page's other field-level statements are registered
findings, each with its own evidence
tier and witness in the claim register.

The counts behind the text:

- the record integrity value and the constant 1 at `+0x08`: all 886,932 data records and the 248 control copies of
  the 124 corpus volumes, no mismatch;
- the control-copy tests and the copy in use: the same 248 copies; the log end lies at most at 0.61 of the data
  area, on one Insider volume;
- the MLog's place: the second control copy's LCN takes eight values on 13 volumes; the data areas quoted are
  `win10refsmini` (0x10000-0x30000) and the four public samples (`forefst mlog`: 0x8000 on the three v3.14 4 KiB
  volumes, 0xC00 on the 64 KiB Insider volume); their sizes are 256 MiB, 512 MiB and 1 GiB;
- the redo-block budget and the commit flag: `lab314_main_step3_dirty`, whose payloads hold 75,693 redo blocks;
- the generations side by side: `win11refstestmftecmd`, generations 1 to 4 at blocks 0x1-0x5c, 0x5d-0x73,
  0x74-0x12d1 and 0x12d2-0x12d8;
- the Logfile Information Table row: 120 corpus volumes measured;
- rows with a time: 71.5 % to 97.3 % of the `mlog --csv` rows of the four public samples;
- the event-log match: 4 of 4 sessions.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.

<!-- findings: AP_LGFL_RA_012, AP_LGFL_003, AP_LGFL_004, AP_LGFL_RA_005, AP_LGFL_RA_006, AP_LGFL_RA_008, AP_LGFL_RA_010, AP_LGFL_RA_011, AP_LGTB_001, AP_LGTB_002, AP_LGTB_003, AP_LGTB_005 -->
