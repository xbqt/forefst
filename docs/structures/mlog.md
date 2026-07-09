# Metadata Log (MLog)

The MLog implements write-ahead logging for atomic metadata updates. It is **redo-only**: on crash
recovery, committed transactions are replayed and there is no undo mechanism — copy-on-write keeps prior
pages intact, so undo is unnecessary. Each MLog data page is one *LogCore data record* nesting four
layers: a record header, an entry header, a redo block, and the inner redo records that carry the
operations of a single transaction.

## Record structure — four layers

Each MLog data page is a single LogCore data record. The on-disk format is **four nested layers**, not
two. All offsets are version-invariant — the only version difference is the entry-header payload-offset
*value* (Layer 2 +0x28).

```
page/record
 ├─ 0x00 Layer 1: LogCore record header (0x78 = 120 bytes)
 ├─ 0x78 Layer 2: entry header (56 bytes; 64 on Insider)
 ├─ 0xB0 Layer 3: redo block _SmsRedoHeader (0xB8 on Insider)
 └─ Layer 4: _SmsRedoRecord entries
```

### Layer 1 — LogCore record header (`record+0x00`, 120 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Signature | `"MLog"` (0x676f4c4d) |
| 0x04 | 4 | Format magic | **Per-volume constant** (validated by equality), not a checksum |
| 0x08 | 4 | Version | 1 |
| 0x0C | 4 | Log block size | 0x1000 (4K) always — not the volume cluster size |
| 0x10 | 16 | UUID | Log-instance UUID (per volume) |
| 0x20 | 4 | Counter | Small per-record counter |
| 0x24 | 4 | Reserved | 0 |
| 0x28 | 8 | **LSN** | This record's log sequence number = (generation << 32) \| log-block offset |
| 0x30 | 8 | Previous LSN | LSN of the prior record; `prevLSN[n] == LSN[n-1]` until the circular buffer wraps |
| 0x38 | 4 | Total length | Whole record, in **4K log blocks** |
| 0x3C | 4 | Header length | Non-payload span, in 4K log blocks (≤ 0x38) |
| 0x54 | 4 | Entry-header offset | Constant **0x78** (anchor to Layer 2) |

### Layer 2 — entry header (`record+0x78`)

56 bytes on v3.4–v3.14, **64 bytes on Insider 29574**. Offsets are entry-relative (absolute page offset
in parentheses):

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 (0x78) | 8 | LSN | Copy of record+0x28 |
| 0x08 (0x80) | 8 | **Checksum** | 8-byte XOR-fold — the real per-record integrity value; varies per record |
| 0x18 (0x90) | 8 | Previous LSN | Copy of record+0x30 |
| 0x20 (0x98) | 4 | Payload length | Redo-block bytes (control records carry 0xe48) |
| 0x28 (0xA0) | 4 | Payload offset | From entry base = **0x38 (v3.4–v3.14) / 0x40 (Insider)** |
| 0x2C (0xA4) | 4 | Entry region size | Record bytes − 0x78 |
| 0x30 (0xA8) | 4 | **Record type** | **2 = data record** (carries a redo block), **1 = control record** |

The redo block starts at `record + 0x78 + payload_offset` = **record+0xB0** (v3.4–v3.14) /
**record+0xB8** (Insider). Robust, version-safe pointer:
`redo = record + le32(record,0x54) + le32(record + le32(record,0x54), 0x28)`, taken only when the entry
type (== 2) is a data record.

### Layer 3 — redo block `_SmsRedoHeader`

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | total_size (u32) | Total bytes in this block including header |
| 0x04 | 4 | first_record_offset (u32) | Offset to the first inner record (= 8) |

Each data page holds exactly one redo block — typically all records of a single transaction
(start → operations → commit).

### Layer 4 — `_SmsRedoRecord` (minimum 0x38 = 56 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | record_size (u32) | Size of this inner record |
| 0x04 | 4 | opcode (u32) | Redo operation type |
| 0x08 | 4 | table_key_path_length (u32) | 0 = no path, >0 = has table path |
| 0x10 | 4 | value_component_count (u32) | Number of value data segments following key components |
| 0x20 | 8 | object_id (u64) | Target OID (from `ObjectIdFromRedoHelper`) |
| 0x2C | 4 | flags (u32) | Bit 0 = transaction start, bit 1 = commit, bit 16 = special |
| 0x38+ | var | payload | Key data, value data (opcode-specific) |

> **Note (the equally-sized 56-byte structures):** the Layer 2 entry header and the Layer 4
> `_SmsRedoRecord` are *both* 56 bytes but are distinct. The **entry header carries the per-record
> checksum (at +0x08)**; the `_SmsRedoRecord` does not (it starts with record_size/opcode). The
> literature's "56-byte log record header with checksum" is the entry header; the "120-byte entry
> header" is the Layer 1 record header.

### Iteration logic (from `ForEachRedoInBlock`)

```
remaining = total_size - first_record_offset
ptr = header + first_record_offset
if (total_size < first_record_offset + 8) or (total_size < 0x38): error
while (record.size <= remaining) and (record.size != 0):
 process(record)
 remaining -= record.size
 if remaining < 0x38: break
 ptr += record.size
```

## Overall layout

The MLog is split into a control area and a data area.

| Component | Description |
|-----------|-------------|
| Control area | Two alternating control pages (identified by the `MLog` signature) with log metadata: head/tail pointers, sequence numbers, data-area bounds |
| Data area | Circular buffer of 4 KiB log blocks, each carrying one redo block (one transaction) |

## MLog location

| Version | Physical LCN | Notes |
|---------|-------------|-------|
| v3.4 | 0x30 (cluster 48) | Immediately after SUPB |
| v3.14 | 0x8000 (cluster 32,768) | 128 MiB offset for 4 KiB clusters; container-aligned for I/O locality |

The MLog is located by its fixed physical LCN, not by file path. The MLog Logfile Information Table
(OID 0x9, accessed via the Object Table, plus duplicate OID 0xA — see [System OIDs](system_oids.md))
stores the control and data area LCN range.

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

## Control page layout — ~252 bytes (18 fields decoded)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Signature | `"MLog"` ASCII (0x676f4c4d) |
| 0x04 | 4 | Format magic | **Per-volume constant** (copied from the log handle, validated by equality), not a checksum. Identical for every control page and data record in a volume; differs between volumes. The real per-record checksum is the XOR-fold at the entry header +0x08 (page+0x80). |
| 0x08 | 4 | Version | Always 1 |
| 0x0C | 4 | Log block size | **0x1000 (4K) always** — the log's I/O unit, **NOT the volume cluster size** (it stays 0x1000 even on 64K-cluster volumes). |
| 0x10 | 16 | UUID | Volume-specific log instance identifier |
| 0x20 | 8 | Sequence number (u64) | Alternation counter (increments each write) |
| 0x28-0x37 | 16 | *Zero* | All-zero |
| 0x38 | 8 | Two `0x1` dwords | Constant `01 00 00 00 01 00 00 00` (likely a {state,version} pair) |
| 0x40-0x53 | 20 | *Zero* | All-zero |
| 0x54 | 4 | `0x78` constant | Entry-header offset (=120); the payload is reached via this (see below) |
| 0x58-0x7F | 40 | *Zero* | All-zero |
| 0x80 | 4 | Valid checksum | Validation field (per-volume value) |
| 0x84-0xAF | -- | *Zero* | All-zero up to the payload base |
| *payload (~0xB0)* | | *Variable-offset payload fields* | Located via entry header at 0x54 |

The remaining fields are NOT at fixed page offsets. They live in a payload block accessed by reading
`entry_header_offset` at page+0x54, then `payload_offset` at entry_header+0x28. The field offsets below
are relative to the payload base (`data_off = entry_header_offset + payload_offset`):

| Payload+Offset | Size | Field | Description |
|----------------|------|-------|-------------|
| +0x00 | 8 | Sequence | Log sequence counter |
| +0x08 | 8 | Data start LCN | Physical start of data area |
| +0x10 | 8 | Data end LCN | Physical end of data area |
| +0x18 | 8 | LSN oldest | Oldest active LSN |
| +0x20 | 8 | Generation | Log generation counter |
| +0x38 | 8 | Write counter | Cumulative write operations |
| +0x48 | 8 | Total entries | Cumulative entries since format |
| +0x50 | 16 | Control UUID | Secondary UUID (matches header UUID) |

18 field positions decoded (16 with assigned meaning). The payload base typically falls around page
offset 0xB0 (the entry-header offset at 0x54 is `0x78`/120) but is not fixed — always dereference via the
entry header.

**The control area is a compact header.** Although the control area reserves `0xE48` (3656) bytes
(self-described by the `0x98` length word), it is populated only through ≈byte `0xF8`; **everything from
~`0xF8` to `0xE48` (≈93% of the area) is zero.** Those bytes are not hidden fields — they are the zero
gaps between the small fixed descriptors above plus the zero tail. The header is **stable per volume**
(magic@0x04, UUID@0x10 echoed at payload+0x28, area-length@0x98, the data-area bounds, and the
LSN/generation pair do not change between captures of the same volume); the dynamic log progression lives
in the data-area records, not the control header.

## Redo opcodes

The opcode is read at `_SmsRedoRecord + 0x04` and dispatched by `CmsLogRedoQueue::PerformRedo`. Opcode
counts vary by version.

| Version | Handlers | Opcode values | Range | Non-handler values |
|---------|----------|--------------|-------|--------------------|
| v3.4 (Win10 17134) | 26 | 29 | 0x00–0x1C (contiguous) | none |
| v3.14 (Win11 26100) | ~39 | 44 | 0x00–0x2B (contiguous) | 1 (0x17 → explicit error) |

The dispatched opcode ranges are **contiguous**; the only in-range value that is not a handler is v3.14
0x17 (returns NTSTATUS `0xC0000427`, the same generic unhandled-opcode error as out-of-range opcodes).
Every in-range value branches to a named handler; the only in-range value that is not a handler is v3.14 0x17, which returns the generic unhandled-opcode error.

Cross-version: the v3.4 core (0x00–0x1C) carries forward almost unchanged (4 renamed, 0x17 turned into an
error, 0 removed); v3.14 adds 0x1D–0x2B (15 new values, mainly stream / table-set / refcount).

### v3.14 dispatch table (44 opcode values, ~39 handlers)

| Opcode | Handler | Category |
|--------|---------|----------|
| 0x00 | OpenTableFromTablePath | Table mgmt |
| 0x01 | RedoInsertRow | B+-tree core |
| 0x02 | RedoDeleteRow | B+-tree core |
| 0x03 | RedoUpdateRow | B+-tree core |
| 0x04 | RedoUpdateDataWithRoot | B+-tree core |
| 0x05 | RedoReparentTable | Table mgmt |
| 0x06 | RedoAllocate | Allocator |
| 0x07 | RedoFree | Allocator |
| 0x08 | RedoSetRangeState | Allocator |
| 0x09 | RedoSetRangeState (shared) | Allocator |
| 0x0A | RedoDuplicateExtents | Dedup/clone |
| 0x0B | RedoModifyStreamExtent | Stream |
| 0x0C | CmsStream::StripAllChecksums | Integrity |
| 0x0D | CmsBPlusTable::SetIntegrityInformation | Integrity |
| 0x0E | RedoSetParentId | Namespace |
| 0x0F | RedoDeleteTable | Table mgmt |
| 0x10 | CmsBPlusTable::SetObjectRecordPayload | B+-tree core |
| 0x11 | RedoAddSchema | Schema |
| 0x12 | RedoMoveContainer (shared) | Container |
| 0x13 | RedoAddContainer | Container |
| 0x14 | RedoMoveContainer (shared) | Container |
| 0x15 | RedoMoveContainer (shared) | Container |
| 0x16 | RedoSetRangeState (range variant) | Allocator |
| 0x17 | ERROR (NTSTATUS 0xC0000427, generic unhandled-opcode) | -- |
| 0x18 | RedoContainerCompaction | Container |
| 0x19 | RedoDeleteCompressionUnitOffsets | Compression |
| 0x1A | RedoAddCompressionUnitOffsets | Compression |
| 0x1B | RedoGhostExtents | Dedup/clone |
| 0x1C | RedoCompactionUnreserve | Container |
| 0x1D | CmsBPlusTable::UnlinkParentObjectId | Hard links |
| 0x1E | CmsTableSetBase::PrepareEntryForMerge | Table set |
| 0x1F | RedoUpdateStreamSummary | Stream |
| 0x20 | CmsStream::UpdateStreamUserPayload | Stream |
| 0x21 | RedoStreamPersistFastRunInsertion | Stream |
| 0x22 | RedoTableSetSummaryUpdate | Table set |
| 0x23 | RedoTableSetShadowTreeUpdate | Table set |
| 0x24 | RedoTableSetCommitMerge | Table set |
| 0x25 | RedoTableSet callback (vtbl +0x08) | Table set |
| 0x26 | RedoTableSetStrongRefMerge | Table set |
| 0x27 | RedoSetDefaultCompressionParameters | Compression |
| 0x28 | CmsBlockRefcount::BreakWeakReferences | Dedup/clone |
| 0x29 | RedoDuplicateCluster | Dedup/clone |
| 0x2A | RedoChangeRangeEncryptedState | Encryption |
| 0x2B | RedoTableSet callback (vtbl +0x18) | Table set |

Only v3.14 0x17 falls through to NTSTATUS 0xC0000427 (the same generic unhandled-opcode error as
out-of-range opcodes). Opcodes 0x25/0x2B dispatch through the `CmsTableSetBase` v-table (indirect;
concrete handler not statically resolvable).

Full dispatch tables with cross-version mapping are maintained in the project's redo-opcode reference.

## Transaction structure

Each MLog data page holds one redo block containing the records for a single atomic transaction. A
transaction typically follows the pattern: start (flags bit 0) → operations → commit (flags bit 1).

### Concrete actions — grouping redo opcodes into what a user did

One file operation is **not** one redo record. ReFS writes a file operation as a cluster of low-level B+-tree
redo opcodes (open a table, insert a row, set a parent id, update a stream summary, allocate clusters…), often
split across several transactions. `forefst mlog --parse` groups the opcodes of each transaction into a single
**concrete action**, and decides the ambiguous ones from **facts in the record** (parent OIDs, which table is
destroyed) — not from opcode presence alone. Every action is still backed by its raw redo records; `mlog --parse
-v` prints each one as `opcode  name  target_oid  @PLCN+offset  key`, so any field can be verified against the
raw disk bytes. Actions are reported in two groups.

**File operations — what a user did:**

| Action | How it is decided | Notes |
|--------|-------------------|-------|
| CREATE | a NEW name row is inserted (`RedoInsertRow` of a `$FILE_NAME` entry, no matching removal) — or the fragment that opens the table and sets its parent | new files, new directories, copies. A hard link also inserts a name and is not separable from CREATE per-transaction (the `-v` records distinguish it). |
| WRITE | a data-record change on an EXISTING object (non-name `InsertRow` + `SetObjectRecordPayload`/`UpdateDataWithRoot`) | pure data updates with no row insert show as MODIFY. |
| RENAME | old name entry removed **and** new name entry inserted, with the **SAME** parent-directory OID | shown as `(same parent 0x..)`. See "MOVE vs RENAME" below. |
| MOVE | old name entry removed and new name entry inserted, with a **DIFFERENT** parent OID | shown as `(parent 0x<old> → 0x<new>)`. |
| DELETE | the object's **own B+-tree table is destroyed** (`RedoDeleteTable`, 0x0F) | shown as `(object table destroyed)`. See "DELETE vs a row removal" below. |

**Low-level / metadata records — the B+-tree redo that accompanies the file operations (kept as facts):**

| Group | Opcodes | Meaning |
|-------|---------|---------|
| STREAM_UPD | UpdateStreamSummary / UserPayload (0x1F/0x20) | stream size/summary touch — accompanies almost every change |
| REPARENT | RedoReparentTable (0x05) without both name entries | a reparent that belongs to a move OR a rename — undecidable from one transaction (see below) |
| ENTRY_REMOVE | RedoDeleteRow (0x02), no table destroyed, no matching insert | the OLD-name removal of a rename/move, or a hard-link unlink — **not** a file deletion |
| ALLOCATE | RedoAllocate/Free (0x06/0x07) | cluster (de)allocation |
| CONTAINER | Move/AddContainer (0x12–0x15) | container-table change |
| DEDUP | BreakWeakReferences / DuplicateCluster (0x28/0x29) | block-clone / dedup |
| EXTENT_MOD | DuplicateExtents / ModifyStreamExtent / FastRunInsertion (0x0A/0x0B/0x21) | extent-level change |
| MODIFY | UpdateRow / UpdateData / SetRangeState / SetObjectRecordPayload / … | metadata-or-data update with no new/removed name row (includes timestamp changes) |
| UPDATE / INSERT / OP | a non-name row swap / a lone insert / an unclassified combination | |

#### MOVE vs RENAME — decided by the parent OID, not by an opcode

A rename and a move look almost identical in the log: both remove the old name entry (`RedoDeleteRow`) and insert
the new one (`RedoInsertRow`), and ReFS emits `RedoReparentTable` for **both** — so a reparent opcode does *not*
mean "move". forefst instead compares the **parent-directory table OID** carried by the two name-entry records
(`parse_mlog_deep_record` reads it at key-component[0] + 0x14):

- old-name `DeleteRow`.target_oid **==** new-name `InsertRow`.target_oid → **RENAME** (renamed in place)
- old-name `DeleteRow`.target_oid **≠** new-name `InsertRow`.target_oid → **MOVE** (reparented to another directory)

This is a fact from the bytes (verifiable with `-v`), so the label is trustworthy. When only one of the two name
entries is present in a transaction, the parent cannot be compared and the record is reported as **REPARENT**
rather than guessed. Validated against an independent operation log (Generate-FSActivity replay + the USN
journal): on that single validation run, MOVE and RENAME agreed with ground truth on every resolvable object.

#### DELETE vs a rename/move's row removal

`RedoDeleteRow` removes a single B+-tree row — and it fires on the OLD name entry of a rename and the source of a
move, not only on a real deletion. A bare `DeleteRow` is therefore **not** evidence a file was deleted. A real
deletion destroys the object's **own table** with `RedoDeleteTable` (0x0F). forefst reports **DELETE only when
`RedoDeleteTable` is present**; a `DeleteRow` with no table destroyed is **ENTRY_REMOVE** (the old-name cleanup of
a rename/move, or a hard-link unlink). Reading a `[DELETE]` as "the file was deleted" without this rule is a
classic false conclusion — the tool now makes the distinction explicit.

### Timestamp extraction

MLog records do not have a dedicated timestamp field in their headers. Timestamps are embedded in the
value data of records that modify file metadata:

| Record type | Location | Fields |
|-------------|----------|--------|
| InsertRow (0x01) | v1 at offsets 0x28-0x40 | create_time, modify_time, access_time, change_time |
| UpdateDataWithRoot (0x04) | v0 at offsets 0x00-0x18 | Timestamp update payload |
| UpdateRow (0x03) | v1 at offsets 0x90, 0xA0, 0x30, 0x28, 0x08, 0x00 | $SI timestamp fields (multiple fallback positions) |

Timestamps are Windows FILETIME format (100-ns intervals since 1601-01-01). Not all transactions contain
timestamps — system-level operations (allocator, container table) typically have no embedded time.
Timestamps reflect the file operation time, not the log write time.

### Key component layout

InsertRow records carry structured key data. Component[0] of the key path has this 28-byte layout:

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | schema0 (u32) — table schema (e.g. 0xe030 = ObjectTable) |
| 0x04 | 4 | schema1 (u32) — attribute schema (e.g. 0x0130 = $FILE_NAME) |
| 0x08 | 12 | zeros |
| 0x14 | 8 | target OID (u64) — the object being modified |

The schema pair identifies which table and attribute type the record targets. Common pairs: 0xe030/0x0130
(ObjectTable/$FILE_NAME), 0xe030/0x0160 (ObjectTable/ReparseIndex).

## Data area sizing

| Metric | Observed range |
|--------|---------------|
| Log size | 1 MiB (minimal) to 4 MiB (heavy use) |
| Record count | tens of records (fresh mini volume) up to many thousands per scan on heavily used volumes |

## Recovery process

The `CmsRestarter` class performs:

1. **Analysis pass**: Scans from oldest needed LSN (stored at CHKP+0x70) to identify dirty pages and active transactions
2. **Redo pass**: Replays all committed redo records in LSN order

There is no undo pass. Copy-on-write ensures uncommitted transactions never overwrote prior state.

## Forensic value

- The MLog does **not** carry pre-images (unlike NTFS $LogFile), so it cannot directly reconstruct previous file states
- Opcodes reveal what operations occurred (inserts, deletes, modifications)
- The LSN range and record count indicate volume activity level
- The oldest log record ref in the CHKP ties the current checkpoint to the log
- Transaction classification maps opcode sequences to human-readable actions (CREATE, DELETE, RENAME, MOVE, WRITE, etc.)
- OID-to-path resolution links redo records to specific files and directories
- Embedded timestamps in InsertRow and UpdateRow value data provide approximate operation times (most, but not all, transactions carry timestamps)
- CSV export enables bulk analysis and timeline correlation with other forensic artifacts

## Tooling

MLog parsing is integrated into `forefst.py` (parsing + display). Available
modes via `forefst.py <image> mlog`:

| Mode | Description |
|------|-------------|
| Default | Control area summary + record statistics |
| `-v` | Per-record detail (opcode + OID) **plus a LogCore Record Headers table** — per-record LSN, prevLSN, checksum, type, and payload offset, with `!chain` markers where `prevLSN[n] != LSN[n-1]` (circular-buffer wrap or a 64K-cluster multi-block page) |
| `--parse` | Decoded transactions: action classification, file paths, timestamps |
| `--csv [FILE]` | Transaction export as CSV (seq, timestamp, action, path, name, oid, opcodes) |
| `--stats` | Opcode frequency histogram |
| `--json` | Machine-readable JSON output |
| `--info` | Reference: all actions, opcodes, timestamps, schema names |
| `--raw-scan` | Raw page classification (debug) |

Validated across v3.4 / v3.7 / v3.9 / v3.10 / v3.14 / Insider volumes — all PASS the LogCore framing
check (entry header @0x78, type 2, single per-volume magic). The 4 KiB-block scanner gives full coverage
on 64K-cluster volumes.

## Cross-references

- [Checkpoint (CHKP)](chkp.md) — oldest log record ref at CHKP+0x70
- [Page Header](page_header.md) — MLog pages share the `"MLog"` signature at offset 0x00 but use a distinct header layout (per-volume format magic at 0x04 — not a CRC — not the common 80-byte format)
- [Copy-on-Write](../concepts/copy_on_write.md) — why redo-only logging is sufficient
- [System OIDs](system_oids.md) — OID 0x9/0xA (Logfile Information Table) stores the MLog LCN range

## Evidence

The four-layer record format was decoded byte-for-byte from `LogCoreWriteDataRecord` (write),
`LogCoreScanDataRecord` / `LogValidateEntryHeader` (read/validate) and `LogInitializeEntryHeader`,
cross-confirmed in v3.4 (Win10), v3.14 (Win11) and Insider 29574, and raw-disk verified across the corpus
(RD). The fixed log-block size (0x1000) is set by `MlLogOpenLog`. The redo opcode dispatch (each value
branching to a PDB-named handler) is decompiled from `CmsLogRedoQueue::PerformRedo` (E2); the 64K-cluster
4 KiB-block packing and the compact-control-header (≈93% zero) results are raw-disk decoded (RD). The
recovery passes come from the `CmsRestarter` class (E2). Findings: **AP_REDO_001–040** (contiguous opcode ranges), **AP_LGFL_RA_008** (compact control header). The format magic is a per-volume
constant, not a CRC. See [how this was verified](../methodology.md) to trace these to the exact images
and measurements in `analysis/`.
