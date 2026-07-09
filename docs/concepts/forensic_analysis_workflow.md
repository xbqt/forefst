# Forensic Analysis Workflow

This is the end-to-end runbook for examining a ReFS volume: a fixed, ordered triage that takes an
analyst from "is this even ReFS?" through version/state classification, structural bootstrap, live-file
enumeration, deleted/prior-version recovery, timeline construction, and tamper checking. The ordering is
load-bearing — every later step assumes the version and the bootstrap chain established by the earlier
ones, because most ReFS addresses and several structure layouts are version- and checksum-gated, and a
tool that parses with the wrong assumptions returns plausible garbage rather than an error.

## The seven stages

Steps 1–3 are mandatory preconditions for everything else; steps 4–7 are the actual investigation and
can be run in any order once the volume is bootstrapped. Each step names the structure or concept it
depends on and the exact `forefst.py` / `refsanalysis.py` command that surfaces it.

```
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
`"FSRS"` identifier at offset 0x10. The 3-byte jump field at 0x00 is `00 00 00` — ReFS is not bootable
(except the Insider build), so do not expect an x86 jump like NTFS. Confirm the VBR is authentic with its
**ROR1+ADD self-checksum** at offset 0x16 (computed over bytes 3..511 excluding 0x16–0x17, the algorithm
the driver itself uses in `RefsIsBootSectorOurs`) — a mismatch means a damaged or
`refsutil fixboot`-wiped boot sector, which is itself an evidentiary finding (see step 7).

```
python3 refsanalysis.py <image> boot -vv   # field-by-field VBR decode + checksum verify
```

### Step 2 — Classify version + native/upgraded state

The version is a **parsing precondition, not a label** — the [`$SI`](../structures/object_table.md)
layout, the [page-reference](../structures/page_references.md) size, and the
[Container Table](../structures/container_table.md) row size all change with it, so getting this wrong
silently corrupts every later step. Read four fields:

| Field | Offset | Meaning | Master |
|-------|--------|---------|--------|
| VBR version (packed major.minor) | 0x28 | Current version, e.g. 0x0304 = v3.4, 0x030E = v3.14 | §A.1a |
| VBR checksum algorithm | 0x2A | 0x0000 None, 0x0002 CRC64, 0x0004 SHA-256 | §A.1b |
| VBR volume flags | 0x2C | 0x06 v3.4, 0x26 v3.7/3.9, 0x66 v3.10+ | §A.1c |
| CHKP flags | 0x78 | Runtime feature register (see below) | §A.4a |

The **CHKP flags** field at [checkpoint](../structures/chkp.md) offset 0x78 discriminates the upgrade
state. The three common values are **0x0002** (original v3.4–v3.9), **0x0602** (upgraded v3.4→v3.14), and
**0x0682** (native v3.14) — but this is **not** an exact 3-value enum: also observed are 0x0082 (native
v3.10), 0x2602/0x2682 (Insider adds bit 0x2000), and 0x07b2 (dedup adds bits 0x130). The *discriminating*
bits are stable: **0x0080** = native-format marker (set only at native format time, **never** added
during upgrade) and **0x0600** = upgrade / CRC64 + indirect-roots. Bit 0x0002 is universally set.

The decisive native-vs-upgraded test is the set of **format-time fields that are never modified during an
upgrade**: VBR 0x2A, VBR flags 0x2C, and the VBR Extended GUID at 0x48 keep their original values even
after a v3.4 volume is mounted on Win11 and its version field at 0x28 is rewritten to 0x030E. So an
*upgraded* volume reads **version 0x030E but flags 0x06, checksum 0x0000, all-zero Extended GUID, and
CHKP flag 0x0080 clear**, while a *native* v3.14 volume reads flags 0x66, checksum 0x0002, a populated
Extended GUID, and CHKP flag 0x0080 set. This matters forensically: POSIX unlink/rename and
[hard links](../concepts/hard_links.md) require CHKP flag 0x0080, so an upgraded volume *cannot* carry
them — their absence on an upgraded volume is expected, not evidence of scrubbing. See
[Version Detection](version_detection.md) for the full marker table.

```
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
  mount, and holds the two CHKP LCN pointers (SUPB+0xC0/0xC8). Selection among the three copies is by
  highest virtual clock (SUPB+0x68) among those that pass validation — the primary copy is **not**
  privileged, so a corrupt primary silently falls back to a backup.
- **[CHKP](../structures/chkp.md)** — read both copies and select the one with the **higher virtual
  clock** at offset 0x60. The two checkpoints alternate each flush, so the lower-clock slot is the
  *previous consistent state* (a rollback target). The CHKP carries **13 root page references** (root
  count at CHKP+0x90 is always 13).
- **Roots 7, 8, and 12** (Container Table primary/duplicate, Small Allocator) use **real physical LCNs**
  and are read directly; **all other roots use virtual LCNs** that must be translated through the
  Container Table. This bootstrap exception is the one place a cluster number in a ReFS root *is* a disk
  offset — see [Virtual Addressing](virtual_addressing.md) for why every other address needs translation.
  Load the [Container Table](../structures/container_table.md) first (root 7), then the
  [Object Table](../structures/object_table.md) at root 0.

```
python3 refsanalysis.py <image> chkp        # confirm winning checkpoint + root LCNs
python3 refsanalysis.py <image> containers  # Container Table (VLCN→PLCN map)
python3 refsanalysis.py <image> objects     # Object Table: OID → VLCN, system OIDs named
```

### Step 4 — Enumerate live files

With the Object Table loaded, walk the directory forest. Each file's metadata lives in its own B+-tree;
**resident** content is stored inline (key flags 0x01) and **non-resident** content is described by
type-0x40 [extent entries](../structures/extent_descriptors.md) (VCN→VLCN→PLCN). Whether a given stream
is inline or extent-based — and the byte-layout difference that follows — is on
[Resident vs Non-Resident Storage](resident_storage.md). User objects start at OID 0x701; system OIDs
occupy 0x00–0x6FF (0x700 is the boundary, never assigned; the allocation rule is on
[Object IDs and File IDs](object_ids_fileids.md)).

```
python3 forefst.py <image> files -o files.csv       # full file listing (CSV: SID, ADS, reparse, snapshots)
python3 refsanalysis.py <image> files -v            # tree view with MACB + sizes
python3 forefst.py <image> extract <name> > out     # extract content (resident + extents + ADS)
python3 forefst.py <image> dataruns -v         # extent map with physical offsets
```

### Step 5 — Recover deleted / orphan / prior-version files

ReFS offers **five** recovery methods, all rooted in [copy-on-write](copy_on_write.md) and asynchronous
deletion — CoW is the reason prior pages survive long enough to be carved at all, so it is the load-
bearing mechanism behind every method below (full detail in [Deletion Recovery](deletion_recovery.md)):

1. **[Trash Table](../structures/trash_table.md)** (OID 0x0D) — files reparented for deferred deletion,
   not yet reclaimed by the background cleaner (`MsReparentFileToTrash` queues them;
   `TrashCleanerWorkItemMethod` frees the data later, so there is a recovery window).
2. **Checkpoint differential** — diff the two checkpoints' decoded root lists. This yields nothing on any
   clean or remountable volume: both checkpoints always decode to identical 13-root pointer lists, and
   only the virtual clock and per-page checksums differ. A genuine mid-transaction crash capture is
   required for this method to produce anything — comparing raw CHKP *bytes* is actively misleading
   because the clock and checksums always differ even when the trees are identical.
3. **Orphan MSB+ scan** — carve `MSB+` pages, find OIDs present in B+-tree pages but absent from the live
   Object Table. Works on cleanly-unmounted volumes; depends on the old pages not yet being reallocated.
4. **[Stream snapshots](snapshots_versioning.md)** (`$SNAPSHOT`, type 0xB0) — the strongest single-image
   path: each `$SNAPSHOT` sub-record points at a `$DATA` sub-record whose extents reconstruct the
   **exact prior bytes** deterministically. Distinct from VM/disk snapshots.
5. **B+-tree node slack** — deletion (`CmsBPlusTable::DeleteFromIndex`) removes only the row's
   offset-array slot and queues *delayed* compaction, so the row body (name + inline `$SI` MACB +
   attributes) survives in node slack until a CoW rewrite reuses it. This is recoverable by **no other
   method** — the orphan scan and both tools' B+-tree iterators follow only the *live* offset array and
   never read the ~13 KB of slack in a page.

OID gaps are permanent deletion evidence: OIDs are monotonically increasing and **never reused**, so a
missing OID between two present ones proves a create-then-delete — a stronger long-window signal than
NTFS's reusable MFT records.

```
python3 forefst.py <image> deleted --slack --scan-pages   # Methods 5 + 3 (+ trash, diff)
python3 forefst.py <image> deleted --slack --extract DIR  # write recovered rows
python3 forefst.py <image> snapshots -v                   # Method 4: list $SNAPSHOT streams
python3 forefst.py <image> files --deleted -o deleted.csv      # deleted entries in the file listing
python3 forefst.py <image> files --cow-before earlier.raw      # forward CoW version recovery (two images)
```

### Step 6 — Build the timeline

ReFS carries one `$SI` timestamp set per **name** (Created/Modified/MFT-Changed/Accessed), not the two
sets NTFS keeps per inode. For a single-named file there is no `$FILE_NAME` twin to compare, so NTFS's
classic $SI-vs-$FN cross-check does not apply (step 7 replaces it). A **hard-linked** file, however, holds
one independent timestamp copy per name, and a name-scoped timestomp leaves the sibling names at the true
birth — so comparing MACB across a file's names is a ReFS-specific tamper check (journal-independent, and
stronger than NTFS's $SI-vs-$FN, where all hard links share one `$SI` and cannot diverge; see step 7). A
super-timeline merges three independent event sources: per-name **$SI MACB**, the
**[USN change journal](../structures/usn_journal.md)** (the `$J` stream, under OID 0x520), and **MLog**
durable-log transactions. USN and $SI carry exact FILETIMEs and join by OID; MLog times are embedded
per-transaction and join by **path**. The [MLog](../structures/mlog.md) redo dispatch is version-aware —
the v3.4 driver dispatches a 29-value opcode range (0x00–0x1C) and the v3.14 driver a 44-value range
(0x00–0x2B), all through `CmsLogRedoQueue::PerformRedo` — so the parser must pick the table by version
before it can name an operation.

```
python3 forefst.py <image> timeline --csv > timeline.csv  # merged $SI + USN + MLog
python3 forefst.py <image> timeline --fast              # change-journal-only (USN+MLog), large vols
python3 forefst.py <image> usn --stats                  # USN reason-code distribution
python3 forefst.py <image> mlog --parse                 # MLog transactions as file ops
python3 forefst.py <image> files --body -o timeline.body     # body file for mactime
```

### Step 7 — Tamper / timestomp check

Although ReFS lacks the `$SI`-vs-`$FILE_NAME` cross-check NTFS uses, timestomping is still detectable
through three anchors that NTFS's method doesn't use (full method on
[Timestomp Detection](timestomp_detection.md)): the metadata-change time is not reachable through the
high-level `SetFileTime` APIs most timestomp tools use; the **USN journal records the tampering operation
itself** (`BASIC_INFO_CHANGE`) and the true `FILE_CREATE` time; and the **volume creation time is a hard
lower bound** on any file's creation. Cross-check the structural integrity in the same pass: `integrity`
walks every reachable page and (with `--fullchecksums`) recomputes every B+-tree page's CRC64/SHA-256
against the stored value, exiting with code 2 on any mismatch.

```
python3 forefst.py <image> timestomp                  # combine the three anchors, score suspects
python3 forefst.py <image> integrity --fullchecksums  # whole-tree tamper/corruption check
```

## Forensic implications

- **Skipping steps 1–2 corrupts everything downstream.** Page-reference size (104/48/72 B), Container
  Table row size (160/224 B), and `$SI` layout are all gated on version *and* checksum mode. Parsing a
  v3.14 SHA-256 volume with v3.4 assumptions silently yields garbage, not an error.
- **Native vs upgraded is a capability statement, not a cosmetic one.** Because CHKP flag 0x0080 is never
  set during an upgrade, an upgraded v3.4→v3.14 volume cannot carry hard links or POSIX unlink/rename
  artifacts — their absence is expected, and their presence proves native format.
- **The two checkpoints are not a free differential.** On any cleanly-unmounted or remountable volume
  they decode to identical root lists; prior whole-tree state on a clean volume comes from snapshots and
  superseded CoW pages, not the alternate checkpoint. Decode and compare the root page-refs, never the
  raw CHKP bytes.
- **OID gaps are permanent deletion evidence** that survives even full page reallocation, because OIDs
  are monotonically increasing and never reused.
- **Recovery success is image-dependent.** Methods 3 and 5 find only what survives in un-reallocated
  pages / un-rewritten slack; a single recovered slack row should always be corroborated (timestamps,
  surrounding rows) before relying on it. Method 4 (snapshots) is the only fully deterministic content
  path.
- **Run integrity before trusting any parse.** A `refsutil fixboot`-damaged VBR zeroes the container
  size, volume serial, checksum selector, Extended GUID, and volume flags — detectable by the failed VBR
  self-checksum, and diagnosable with `bootedit repair --dry-run`.

## Version / state differences

| Concern | v3.4 (original) | v3.4→v3.14 (upgraded) | v3.14 (native) |
|---------|-----------------|-----------------------|----------------|
| VBR version (0x28) | 0x0304 | 0x030E | 0x030E |
| VBR flags (0x2C) | 0x06 | 0x06 (unchanged) | 0x66 |
| VBR checksum (0x2A) | 0x0000 | 0x0000 (unchanged) | 0x0002 / 0x0004 |
| VBR Extended GUID (0x48) | all-zero | all-zero (unchanged) | populated |
| CHKP flags (0x78) | 0x0002 | 0x0602 | 0x0682 |
| CHKP flag 0x0080 | clear | clear | set |
| Hard links / POSIX unlink | no | no | yes |
| Metadata page-ref size | 104 B (None) | 48 B (CRC64 active) | 48 / 72 B |

The "common" three CHKP values are not exhaustive (see step 2).

## Tooling

| Step | Primary command |
|------|-----------------|
| 1 Detect | `refsanalysis.py <image> boot -vv` |
| 2 Classify | `refsanalysis.py <image> summary` / `chkp -vv` |
| 3 Bootstrap | `refsanalysis.py <image> chkp` / `containers` / `objects` |
| 4 Enumerate | `forefst.py <image>` / `refsanalysis.py <image> files -v` |
| 5 Recover | `forefst.py <image> deleted --slack --scan-pages` / `snapshots -v` |
| 6 Timeline | `forefst.py <image> timeline --csv > timeline.csv` |
| 7 Tamper | `forefst.py <image> timestomp` / `integrity --fullchecksums` |

`refsanalysis.py <image> all` runs summary, boot, supb, chkp, schema, objects, parentchild, containers,
files, security, reparse, integrity, mlog, usn in sequence (steps 1–4 + integrity in one pass).
`forefst.py <image> export -o DIR` dumps hash-verified raw metadata (VBR, both CHKP, SUPB copies,
MLog, USN `$J`, and the whole B+-tree forest) — the ReFS analogue of a raw `$MFT` capture.

## Cross-references

- [Version Detection](version_detection.md) — step 2: the full native-vs-upgraded marker table
- [Bootstrap Chain](bootstrap_chain.md) — step 3: VBR→SUPB→CHKP→Container→Object Table, link by link
- [Virtual Addressing](virtual_addressing.md) — step 3: why all but roots 7/8/12 need VLCN→PLCN translation
- [Deletion Recovery](deletion_recovery.md) — step 5: the five recovery methods in detail
- [Copy-on-Write](copy_on_write.md) — why prior versions and orphan pages survive to be recovered
- [Snapshots & Versioning](snapshots_versioning.md) — step 5 Method 4: deterministic prior-content reconstruction
- [Resident vs Non-Resident Storage](resident_storage.md) — step 4: inline vs extent-based content
- [Object IDs and File IDs](object_ids_fileids.md) — step 4: OID 0x701 boundary and the never-reused rule
- [Hard Links](hard_links.md) — step 2: the capability gated on CHKP flag 0x0080
- [Timestomp Detection](timestomp_detection.md) — step 7: the three tamper anchors
- [VBR](../structures/vbr.md), [SUPB](../structures/supb.md), [Checkpoint (CHKP)](../structures/chkp.md),
  [Object Table](../structures/object_table.md), [Container Table](../structures/container_table.md),
  [Trash Table](../structures/trash_table.md), [USN Journal](../structures/usn_journal.md),
  [MLog](../structures/mlog.md) — the structures touched along the chain

## Evidence

The bootstrap chain, version markers, and recovery mechanisms are confirmed both in the driver (E2) and
on the raw-disk corpus (RD). Specifically:

- **VBR detection / checksum** (E2): the ROR1+ADD self-checksum is the algorithm in `RefsIsBootSectorOurs`;
  verified on every parseable corpus image.
- **Native-vs-upgraded markers and the upgrade-immutable fields**: VBR 0x2A/0x2C/0x48
  and CHKP flag 0x0080 confirmed across the corpus.
- **CHKP selection / SUPB self-heal** (E2 + RD, finding **FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003**): `ChooseSuperBlock` / `ChooseCheckpointRecord`
  select by highest virtual clock among validating copies; `CmsVolume::ReadSuperBlock` /
  `ReadLatestCheckpoint` locate the copies; SUPB/CHKP self-checksums are cluster-size-dependent and
  validated at mount.
- **Checkpoint-differential limitation** (RD, finding **FS_CHKP_RA_014**): the two CHKP copies decode to identical
  13-root lists on clean/corrupted/busy/pre-salvage images; only the clock and checksums differ.
- **B+-tree node-slack recovery** (E2 + RD, finding **FS_DEL_RA_005**): `CmsBPlusTable::DeleteFromIndex` removes
  only the offset-array slot and queues delayed compaction; a slack scan recovered stale type-0x30 rows
  absent from the live tree, with no false positives on the clean baseline.
- **CHKP-flags non-enum and the +0x88/+0x8C field-pair** (RD, finding **FS_CHKP_RA_012, FS_CHKP_RA_001, FS_CHKP_RA_013**): the {0x002,0x602,0x682}
  model is not exhaustive; additional states (0x082, 0x2602/0x2682, 0x7b2) are observed.
- **Trash / orphan / deletion flow** (E2): `RefsDeleteFile` → `MsDeleteRow` → `MsReparentFileToTrash` →
  the `CmsTrashTable` queue → `TrashCleanerWorkItemMethod`.
- **Stream-snapshot recovery** (E2 + RD): `RefsCreateStreamSnapshot` builds the stream summary; the
  $SNAPSHOT→$DATA extent chain reconstructs prior bytes byte-for-byte.
- **USN ↔ file link** (RD): `$UsnJrnl:$J` lives under OID 0x520; the per-file LastUsn (`$SI`+0x40) is an
  exact byte offset into a `$J` record naming that file.
- **MLog redo dispatch** (E2): opcode at `_SmsRedoRecord`+0x04, dispatched by `CmsLogRedoQueue::PerformRedo`;
  contiguous ranges v3.4 0x00–0x1C (29 values) and v3.14 0x00–0x2B (44 values).
- **Per-name `$SI` MACB and the hard-link cross-check** (RD, finding **FN_LINK_003 / E59**): each name is
  an independent type-0x30 row with its own four FILETIMEs; a name-scoped timestomp rewrites only the
  opened name, so sibling hard-link names retain the true birth and diverge from the stomped one.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
