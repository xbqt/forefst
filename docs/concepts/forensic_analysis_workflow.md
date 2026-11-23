# Forensic Analysis Workflow

This is the end-to-end runbook for examining a ReFS volume: a fixed order of steps that takes an analyst from
checking that the volume is ReFS, through version/state classification, structural bootstrap, live-file enumeration,
deleted/prior-version recovery, timeline construction, and tamper checking.

The order matters. Every later step assumes the version and the bootstrap chain established by the earlier
ones, because most ReFS addresses and several structure layouts are version- and checksum-gated, and a tool that
parses with the wrong assumptions returns wrong values that look plausible, not an error.

For the same examination worked on a sample image, command by command, see
[A first examination](../examples/first_examination.md).

## The seven stages

Steps 1–3 are mandatory preconditions for everything else; steps 4–7 are the actual investigation and
can be run in any order once the volume is bootstrapped. Each step names the structure or concept it
depends on and the exact `forefst.py` / `refsanalysis.py` command that surfaces it.

```text
1. Detect ReFS      VBR "ReFS"/"FSRS"                       → is this a ReFS partition?
2. Classify version VBR 0x28/0x2A/0x2C + CHKP               → which layouts apply, native vs upgraded?
3. Bootstrap        VBR→SUPB→CHKP→13 roots→Container Table  → reach the Object Table
4. Enumerate        live Object Table → file B+-trees       → what is on the volume now?
5. Recover deleted  5 methods (trash/diff/orphan/snapshot/slack) → what was removed?
6. Build timeline   $SI MACB + USN + MLog                   → when did things happen?
7. Tamper check     $SI vs USN vs volume-create             → were timestamps forged?
```

### Step 1 — Detect ReFS

A ReFS partition is identified at the **first sector of the partition** by two signatures in the
[VBR](../structures/vbr.md): the ASCII string `"ReFS\0\0\0\0"` at offset 0x03 (file-system name) and the
`"FSRS"` identifier at offset 0x10. The 3-byte jump field at 0x00 is `00 00 00` — do not expect an x86
jump as in NTFS; the corpus's Insider 29574 boot volume holds `00 00 00` too.

Confirm the VBR is intact with its **ROR1+ADD self-checksum** at offset 0x16 — the algorithm the driver itself uses in
`RefsIsBootSectorOurs`, computed from byte 3 to the end of the boot sector's declared length (`+0x14`; 512 bytes on
every corpus volume), excluding 0x16–0x17. A mismatch means a damaged boot sector.

A boot sector `refsutil fixboot` rewrote passes its checksum; it shows in its fields instead, a container size
(`+0x40`) of 0 until a writable mount writes the 64 MiB default back (see step 7).

```sh
python3 refsanalysis.py <image> boot -vv   # field-by-field VBR decode + checksum verify
```

### Step 2 — Classify version + native/upgraded state

The version must be **known before parsing** — the [`$SI`](../attributes/STANDARD_INFORMATION.md)
layout, the [page-reference](../structures/page_references.md) size, and the
[Container Table](../structures/container_table.md) row size all change with it, so getting this wrong
silently corrupts every later step.

`forefst summary` prints the result: its `Volume state:` line says `NATIVE ReFS 3.14` or that the volume appears
upgraded, with the reason (see [Identify a native vs upgraded volume](../examples/identify_native_vs_upgraded.md)).
By hand, read four fields:

| Field | Offset | Meaning |
|-------|--------|---------|
| VBR version (packed major.minor) | 0x28 | Current version, e.g. 0x0304 = v3.4, 0x030E = v3.14 |
| VBR checksum algorithm selector | 0x2A | 0x0002 CRC64, 0x0004 SHA-256; 0x0000 on volumes formatted before 3.10 (and on the corpus's one volume whose boot sector `refsutil fixboot` rewrote), where refs.sys does not read it (they use CRC64) |
| VBR volume flags | 0x2C | 0x06 v3.4, 0x26 v3.7/3.9, 0x66 v3.10+ |
| CHKP flags | 0x78 | Runtime feature register (see below) |

The **CHKP flags** field at [checkpoint](../structures/chkp.md) offset 0x78 discriminates the upgrade
state. The three common values are **0x0002** (original v3.4–v3.9), **0x0602** (upgraded v3.4→v3.14), and
**0x0682** (native v3.14) — but this is **not** an exact 3-value enum: also observed are 0x0082 (native
v3.10), 0x2602/0x2682 (Insider adds bit 0x2000), and 0x07b2 (0x0682 with dedup 0x010, weak references 0x020
and dirty-state tracking 0x100). The *discriminating* bits are stable:

- **0x0080** = native-format marker (set on volumes formatted at 3.10 or later; clear on 3.4–3.9 volumes and on
  the upgraded volumes measured);
- **0x0600** = set on every v3.14 volume measured (0x0200 the indirect root list; 0x0400 the record's
  rollback-protection fields, which refs.sys sets on a volume of version 3.13 or later);
- bit 0x0002 is set on every record.

The decisive native-vs-upgraded test is the set of **format-time fields an upgrade does not change**: VBR 0x2A,
the format bits of the VBR flags at 0x2C (0x20, 0x40) and the VBR Extended GUID at 0x48 keep their original values
(the two upgrades measured) even after a v3.4 volume is mounted on Win11 and its version field at 0x28 is rewritten
to 0x030E.

- A volume *upgraded* from 3.4 reads **version 0x030E but flags 0x06, checksum 0x0000, all-zero Extended GUID, and
  CHKP flag 0x0080 clear**.
- A *native* v3.14 volume reads flags 0x66, checksum 0x0002 (0x0004 with SHA-256), a populated Extended GUID, and
  CHKP flag 0x0080 set.

This matters forensically: refs.sys supports [hard links](../concepts/hard_links.md) on a volume exactly when its
boot-sector flags (`+0x2C`) carry 0x20 (`InitializeVcbFromBootSector` / `RefsHardlinksSupported`, 26100.9444 and
.8115; 17134 has no such switch). That format-time bit is set on every corpus volume formatted at 3.7 or later (but
one whose boot sector `refsutil fixboot` rewrote), and clear on 3.4 volumes and on those upgraded from 3.4.

A volume upgraded from 3.4 therefore cannot carry hard links — their absence there is expected, not evidence of
scrubbing — while one upgraded from 3.7 or 3.9 keeps the bit and can.

See [Version Detection](version_detection.md) for the full marker table.

```sh
python3 refsanalysis.py <image> summary       # version, size, file/dir counts
python3 refsanalysis.py <image> supb --verify # version echo + consistency
python3 refsanalysis.py <image> chkp -vv      # CHKP flags + root pointers + translation mode
```

### Step 3 — Bootstrap to the Object Table

Every table read requires walking the fixed chain `GPT → VBR → SUPB → CHKP → Container Table → target`
(the full sequence and why each link is required is on the [Bootstrap Chain](bootstrap_chain.md) page).
The non-obvious steps:

- **[SUPB](../structures/supb.md)** is always at **LCN 0x1E** (fixed), with two backup copies near the
  partition end at `total_clusters − 2` and `total_clusters − 3`. It carries a cluster-size-dependent
  self-checksum (CRC32-C/4B on 4K-cluster, CRC64/8B on 64K, SHA-256/32B on SHA-256 volumes) verified at
  mount, and holds the two CHKP LCN pointers (SUPB+0xC0/0xC8). refs.sys reads the primary whenever it passes
  validation, whatever the backups hold; `+0x68` orders only the two backups, so a corrupt primary silently falls
  back to the backup with the higher `+0x68` (a tie keeps `total_clusters − 2`).
- **[CHKP](../structures/chkp.md)** — read both copies in the superblock list's order, skip one that fails
  validation, and switch to the other only when its virtual clock at offset 0x60 is **strictly greater** (a tie
  keeps slot 0). The two checkpoints alternate each flush, so the lower-clock slot is the
  *previous consistent state* (a rollback target). The CHKP carries **13 root page references** (root
  count at CHKP+0x90 is always 13).
- **Roots 7, 8, and 12** (the Container Table's two failover copies, and the Small Allocator) use **real physical
  LCNs** and are read directly; **all other roots use virtual LCNs** that must be translated through the Container
  Table. This bootstrap exception is the one place a cluster number in a ReFS root *is* a disk offset — see
  [Virtual Addressing](virtual_addressing.md) for why every other address needs translation.

  Load the [Container Table](../structures/container_table.md) first (roots 7 / 8; neither copy is a "primary"),
  then the [Object Table](../structures/object_table.md) at root 0.

```sh
python3 refsanalysis.py <image> chkp        # confirm winning checkpoint + root LCNs
python3 refsanalysis.py <image> containers  # Container Table (VLCN→PLCN map)
python3 refsanalysis.py <image> objects     # Object Table: OID → VLCN, system OIDs named
```

### Step 4 — Enumerate live files

With the Object Table loaded, walk the directory forest. Each **directory** has its own B+-tree, while a **file**'s
metadata lives as rows inside a directory's tree (files have no tree of their own). Two separate properties decide how
a file is read:

- **Placement** — where its record sits: embedded in its name row (`key_flags` 0x01), or split out into a type-0x40
  backing record (`key_flags` 0x02) after a move or a hard link.
- **Residency** — where its data sits: inline in the `$DATA` value, or in extents, whose map is a B+-tree node
  inside the `$DATA` value whose leaf rows are the 24-byte [extent entries](../structures/extent_descriptors.md)
  (VCN→VLCN→PLCN).

See [Placement and residency](placement_and_residency.md) and
[Record placement and data residency](placement_and_residency.md) for the byte layouts.

User objects start at OID 0x701; system OIDs occupy 0x00–0x6FF (0x700 seeds the counter and is never assigned; the
allocation rule is on [Object IDs](object_ids.md)).

```sh
python3 forefst.py <image> files --csv files.csv    # full file listing (CSV: SID, ADS, reparse, snapshots)
python3 refsanalysis.py <image> files -v            # tree view with MACB + sizes
python3 forefst.py <image> extract <name> > out     # extract content (resident + extents + ADS)
python3 forefst.py <image> dataruns -v         # extent map with physical offsets
```

### Step 5 — Recover deleted / orphan / prior-version files

ReFS offers **five** recovery methods, all based on [copy-on-write](copy_on_write.md) and on a deletion that
zeroes nothing. CoW is why prior pages survive long enough to be carved, so every method below depends on it (full
detail in [Deletion Recovery](deletion_recovery.md)):

1. **[Trash Table](../structures/trash_table.md)** (OID 0x0D) — objects reparented for deferred deletion,
   not yet reclaimed by the background cleaner (the delete paths call `MsReparentFileToTrash` only for an object whose data
   stream set holds two or more tables, or on two rarer conditions; `TrashCleanerWorkItemMethod` frees the data later, so there is a recovery
   window for those; every other delete is done in place).
2. **Checkpoint differential** — compare the two checkpoints' trees. This usually yields nothing: the two
   copies' 13-root lists are identical on the images measured and on all but one of the volumes of the blind audit
   (on that ReFS 3.4 volume five roots differ). A capture between two checkpoint writes that changed a root table is
   needed for this method to produce anything — and comparing raw CHKP *bytes* is misleading, because the copies
   differ in their clocks (unless the two tie), their allocator clock, their own LCN and their checksums even when the
   trees are identical.
3. **Orphan-object scan** (`deleted --orphans`, opt-in, low confidence) — lists OIDs still in the Object Table but
   unreachable from the directory tree: a directory whose tree link was removed before its entry was reclaimed.
4. **[Stream snapshots](snapshots_versioning.md)** (`$SNAPSHOT`, type 0xB0) — the strongest single-image
   path: each `$SNAPSHOT` sub-record names a version whose bytes are read by resolving each file VCN across the
   file's streams (a block unchanged since a snapshot is held once, shared), which reconstructs the **exact prior
   bytes** deterministically. Distinct from VM/disk snapshots.
5. **B+-tree node slack** — deletion (`CmsBPlusTable::DeleteFromIndex`) removes the row's
   offset-array slot, marks the row as removed from the index, and queues *delayed* compaction, so the row body (name + inline `$SI` MACB +
   attributes) survives in node slack until a CoW rewrite reuses it. This is recoverable by **no other
   method** — the orphan-page name scan (`deleted --scan-pages`) and the tools' ordinary B+-tree iterators follow only
   the *live* offset array and never read a page's slack (about 13 KB of a 16 KiB page on the volume first measured).

OID gaps are deletion evidence that lasts: a new OID is always above every live one, an OID below one in use is
**never issued again**, and only directories draw user OIDs, so a missing OID between two present ones is a deleted directory
or a directory creation that failed. This evidence lasts longer than on NTFS, whose MFT records are reused.

```sh
python3 forefst.py <image> deleted                        # recovery (default): trash + diff + live-page slack
python3 forefst.py <image> deleted --full                 # complete: + whole-volume orphan-page scan + carve (slow: 25.5 min for 2 TiB measured)
python3 forefst.py <image> export deleted DIR             # write the index + recovered content (content/)
python3 forefst.py <image> snapshots -v                   # Method 4: list $SNAPSHOT streams
python3 forefst.py <image> files --cow-before earlier.raw # compare with an earlier image of the volume
```

### Step 6 — Build the timeline

ReFS keeps one `$SI` timestamp set per **file**, in the file's own record (Created/Modified/Changed
(metadata)/Accessed), and each name's index entry caches it; it has no `$FILE_NAME` attribute. For a single-named
file there is no `$FILE_NAME` twin to compare, so NTFS's classic $SI-vs-$FN cross-check does not apply (step 7
replaces it).

A **hard-linked** file carries one cached copy per name, and those copies **can** diverge (NTFS's hard links share
one `$SI`; each NTFS link has its own `$FILE_NAME`, with its own times):

- a divergence of the names' Created times is evidence to follow up;
- their Changed times diverge routinely (a hard link added later carries the time it was added);
- **agreement is not** evidence, because the file's own record takes the new time for every name at once and each
  name's entry is only a cache of it, refreshed when the file is opened, read and closed through that name (see step 7 and
  [Hard Links](hard_links.md)).

A super-timeline merges three event sources, which are not independent of each other: **$SI MACB**, the
**[USN change journal](../structures/usn_journal.md)** (the `$J` stream, under OID 0x520), and **MLog** durable-log
payloads.

- USN and $SI carry exact FILETIMEs; an MLog row is one log payload, whose time is the latest time its records
  carry (a payload can merge several redo blocks).
- The rows are merged by time, not joined across sources: a file is listed under its home directory's OID in $SI
  and USN, and MLog names the table it changes.
- The [MLog](../structures/mlog.md) redo dispatch is version-aware, all through `CmsLogRedoQueue::PerformRedo`: the
  v3.4 driver (17134) dispatches a 29-value opcode range (0x00–0x1C), the 26100 drivers a 44-value range
  (0x00–0x2B), and the Insider builds read up to 0x2C or 0x2D — so the parser must pick the table by version before
  it can name an operation.

```sh
python3 forefst.py <image> timeline --csv > timeline.csv  # merged $SI + USN + MLog
python3 forefst.py <image> timeline --fast              # USN + MLog only (skips the $SI walk), large vols
python3 forefst.py <image> usn --stats                  # USN reason-code distribution
python3 forefst.py <image> mlog --parse                 # MLog log payloads, with the action each reads as
python3 forefst.py <image> files --body timeline.body   # body file for mactime
```

### Step 7 — Tamper / timestomp check

Although ReFS lacks the `$SI`-vs-`$FILE_NAME` cross-check NTFS uses, timestomping is still detectable through
three sources that NTFS's method does not use (full method on [Timestomp Detection](timestomp_detection.md)):

- the metadata-change time is not reachable through the high-level `SetFileTime` APIs most timestomp tools use;
- the **USN journal records the edit itself** (`BASIC_INFO_CHANGE`) and the true `FILE_CREATE` time, when the volume
  has a journal that covers the period;
- the **volume creation time is a floor** for a file created on the volume (a copy or a restore that keeps its
  creation time brings an older one).

Cross-check the structural integrity in the same pass: `integrity --fullchecksums` verifies the checksum of every
object B+-tree page (CRC64 or SHA-256) against its reference, up to 300,000 pages unless `--max-pages` raises the cap
(the output says when it is reached), exiting with code 2 on a finding.

```sh
python3 forefst.py <image> timestomp                  # combine the three sources, score suspects
python3 forefst.py <image> integrity --fullchecksums  # whole-tree tamper/corruption check
```

## Forensic implications

- **Skipping steps 1–2 corrupts every later step.** Page-reference size (104/48/72 B) is gated on version
  *and* checksum mode, Container Table row size (160/224 B) on checksum mode *and* cluster size, and the `$SI` layout
  on version. Parsing a v3.14 SHA-256 volume with v3.4 assumptions silently yields wrong values, not an error.
- **Native vs upgraded decides what the volume can hold.** Hard-link support is the boot-sector
  flags' format-time bit 0x20, which an upgrade does not set, so a volume upgraded from 3.4 cannot carry hard
  links — their absence is expected; a hard link on a volume whose bit is clear needs explaining (a `refsutil
  fixboot` rewrite clears it: its flags read 0x04).
- **Comparing the two checkpoints usually shows no difference.** On a cleanly-unmounted or remountable volume they
  usually decode to identical root lists; prior whole-tree state on a clean volume comes from snapshots and
  superseded CoW pages, not the alternate checkpoint. Decode and compare the root page-refs, never the
  raw CHKP bytes.
- **OID gaps are lasting evidence** that survives even full page reallocation, because a new OID is always
  above every live one and an OID below one in use is never issued again: a gap is a deleted directory or a failed directory
  creation.
- **Recovery success is image-dependent.** Methods 3 and 5 find only what has not been reclaimed yet — an Object-Table entry, un-rewritten slack
  or, with `--full`, an orphan page not yet reallocated; a single recovered slack row should always be corroborated (timestamps,
  surrounding rows) before relying on it. Method 4 (snapshots) is the only fully deterministic content
  path.
- **Run integrity before trusting any parse.** On the volume measured, `refsutil fixboot` zeroed the container
  size, volume serial, checksum selector and Extended GUID of the boot sector and rewrote its volume flags (0x04
  where the volume carried 0x66), under a valid self-checksum — so the checksum does not reveal it;
  `refsanalysis.py <image> bootedit repair --dry-run` diagnoses it.

## Version / state differences

| Concern | v3.4 (original) | v3.4→v3.14 (upgraded) | v3.14 (native) |
|---------|-----------------|-----------------------|----------------|
| VBR version (0x28) | 0x0304 | 0x030E | 0x030E |
| VBR flags (0x2C) | 0x06 | 0x06 (unchanged) | 0x66 |
| VBR checksum (0x2A) | 0x0000 | 0x0000 (unchanged) | 0x0002 / 0x0004 |
| VBR Extended GUID (0x48) | all-zero | all-zero (unchanged) | populated |
| CHKP flags (0x78) | 0x0002 | 0x0602 | 0x0682 |
| CHKP flag 0x0080 | clear | clear | set |
| VBR flags bit 0x20 (hard-link support) | clear | clear | set |
| Checkpoint root-reference size (CHKP+0x5C) | 104 B (CRC64) | 48 B | 48 / 72 B |

The "common" three CHKP values are not exhaustive (see step 2).

## Tooling

| Step | Primary command |
|------|-----------------|
| 1 Detect | `refsanalysis.py <image> boot -vv` |
| 2 Classify | `refsanalysis.py <image> summary` / `chkp -vv` |
| 3 Bootstrap | `refsanalysis.py <image> chkp` / `containers` / `objects` |
| 4 Enumerate | `forefst.py <image> files` / `refsanalysis.py <image> files -v` |
| 5 Recover | `forefst.py <image> deleted` (add `--full` for the complete scan) / `snapshots -v` |
| 6 Timeline | `forefst.py <image> timeline --csv > timeline.csv` |
| 7 Tamper | `forefst.py <image> timestomp` / `integrity --fullchecksums` |

`refsanalysis.py <image> all` runs summary, boot, supb, chkp, schema, objects, parentchild, containers and files
in sequence (steps 1–4 in one pass).
`forefst.py <image> export -o DIR` dumps hash-verified raw metadata (VBR, both CHKP, SUPB copies,
MLog, USN `$J`, and the whole B+-tree forest) — the ReFS analogue of a raw `$MFT` capture.

## Cross-references

- [Version Detection](version_detection.md) — step 2: the full native-vs-upgraded marker table
- [Bootstrap Chain](bootstrap_chain.md) — step 3: VBR→SUPB→CHKP→Container→Object Table, link by link
- [Virtual Addressing](virtual_addressing.md) — step 3: why all but roots 7/8/12 need VLCN→PLCN translation
- [Deletion Recovery](deletion_recovery.md) — step 5: the five recovery methods in detail
- [Copy-on-Write](copy_on_write.md) — why prior versions and orphan pages survive to be recovered
- [Snapshots & Versioning](snapshots_versioning.md) — step 5 Method 4: deterministic prior-content reconstruction
- [Record placement and data residency](placement_and_residency.md) — step 4: inline vs extent-based content
- [Object IDs](object_ids.md) — step 4: OID 0x701 boundary and the OID counter
- [Hard Links](hard_links.md) — step 2: the capability gated on the boot-sector flags' bit 0x20
- [Timestomp Detection](timestomp_detection.md) — step 7: the three sources to check a time against
- [VBR](../structures/vbr.md), [SUPB](../structures/supb.md), [Checkpoint (CHKP)](../structures/chkp.md),
  [Object Table](../structures/object_table.md), [Container Table](../structures/container_table.md),
  [Trash Table](../structures/trash_table.md), [USN Journal](../structures/usn_journal.md),
  [MLog](../structures/mlog.md) — the structures touched along the chain

## Evidence

The bootstrap chain, version markers, and recovery mechanisms are confirmed both in the driver and on the raw-disk
corpus. Specifically:

- **VBR detection / checksum** (driver): the ROR1+ADD self-checksum is the algorithm in `RefsIsBootSectorOurs`;
  verified on every parseable corpus image.
- **Native-vs-upgraded markers and the fields an upgrade does not change**: VBR 0x2A, 0x48 and the format bits
  (0x20, 0x40) of the flags at 0x2C, and CHKP flag 0x0080, confirmed across the corpus; the hard-link switch read in the driver (twice on 26100.9444,
  once on 26100.8115) and measured on 115 volumes.
- **CHKP selection / SUPB self-heal** (driver and disk): the rules of step 3, read in `CmsVolume::ReadSuperBlock` /
  `ChooseSuperBlock` and `ReadLatestCheckpoint` / `ChooseCheckpointRecord`, which locate the copies; SUPB/CHKP self-checksums are cluster-size-dependent and
  validated at mount.
- **Checkpoint-differential limitation** (disk): the two CHKP copies decode to identical 13-root lists on
  clean/corrupted/busy/pre-salvage images and on 25 of the 26 blind-audit volumes; their bytes still differ (18
  volumes byte-compared).
- **B+-tree node-slack recovery** (driver and disk): `CmsBPlusTable::DeleteFromIndex` removes
  the offset-array slot, marks the row as removed from the index and queues delayed compaction; a slack scan recovered stale type-0x30 rows
  absent from the live tree, with no false positives on the clean baseline.
- **CHKP-flags non-enum and the +0x88/+0x8C field-pair** (disk): the {0x002,0x602,0x682}
  model is not exhaustive; additional states (0x082, 0x2602/0x2682, 0x7b2) are observed.
- **Trash / orphan / deletion flow** (driver): `RefsDeleteFile` → `DeleteFileOnDisk` (or a directory delete path) →
  `MsReparentFileToTrash`, when `RefsCheckDataSetsForDeletion` sends the object there → the `CmsTrashTable` queue →
  `TrashCleanerWorkItemMethod` (26100.8115, .9444, .9549, .9711 and Insider 29574; 17134 reparents through
  `MsReparentChildTableToTrash`).
- **Stream-snapshot recovery** (driver and disk): `RefsCreateStreamSnapshot` builds the stream summary; resolving
  each VCN across the streams reconstructs prior bytes byte-for-byte (8 of 8 current files and 20 of 20 prior
  versions of a lab family, against the generator's specification).
- **USN ↔ file link** (disk): `$UsnJrnl:$J` lives under OID 0x520; the per-file LastUsn (`$SI`+0x40) is the
  virtual byte offset of a `$J` record naming that file (its file offset until the journal wraps).
- **MLog redo dispatch** (driver): opcode at `_SmsRedoRecord`+0x04, dispatched by `CmsLogRedoQueue::PerformRedo`;
  contiguous ranges 0x00–0x1C (29 values) on 17134 and 0x00–0x2B (44 values) on 26100; Insider 29574 / 29659 up to
  0x2C, Insider 29683 up to 0x2D (a table deletion).
- **Per-name MACB** (driver and disk): each name's type-0x30 row carries a cached copy of the file's four
  FILETIMEs; the file's own record holds them once. Divergence *has* been observed on disk, and it lives in the
  per-name cache: an open, a read and a close through a name refresh its entry (a directory listing does not), so an
  un-opened sibling keeps its pre-stomp times until something opens and reads the file through it. A lab measurement found both rows
  byte-identical after a `SetFileTime` through one name because the lab's inventory pass had then opened both
  names. **It is not a reliable timestomp cross-check on its own:** equal times on the other names prove nothing.

The count behind the text: the checkpoint copies decode to the same root list on 25 of the 26 volumes of the first blind audit.

See [how this was verified](../methodology.md) to trace these statements to the exact images and measurements in
`analysis/`.

<!-- findings: FN_LINK_003, FS_CHKP_005, FS_CHKP_RA_001, FS_CHKP_RA_012, FS_CHKP_RA_013, FS_CHKP_RA_014,
               FS_DEL_RA_005, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_003, FS_SUPB_RA_005,
               MD_TS_RA_008 -->
