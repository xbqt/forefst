# Volume Redundancy — Boot Sector, Superblock, Checkpoint copies

Every ReFS volume keeps redundant copies of the three structures it needs to mount — the
[boot sector](../structures/vbr.md), the [superblock](../structures/supb.md), and the
[checkpoint](../structures/chkp.md) — but it does **not** maintain them the same way, and that
difference is what makes them useful to a forensic analyst. Two of the three carry a self-checksum and a
virtual clock, so the driver can tell which copy is current and silently fall back when one is corrupt.
The third — the boot sector — has neither, so its backup can drift out of sync with the primary and
preserve the volume's *original* state. This page explains how each redundant copy is located,
validated, and selected, and turns those mechanics into recovery leverage.

## Three structures, three redundancy policies

The bootstrap anchors sit at the front of the [bootstrap chain](bootstrap_chain.md): the parser reads
the boot sector, follows it to the superblock, and follows the superblock to the checkpoint that holds
the 13 table roots. Each of the three is replicated, but with a different locating, validation, and
selection rule.

| Structure | Copies | Located by | Validation | Selection | Rewritten when… |
|-----------|--------|-----------|-----------|-----------|-----------------|
| **Boot sector (VBR)** | 2 — sector 0 + **last LBA** | last LBA = `totalSectors−1` (from `VBR+0x18`) | self-contained: signature + **0x16 ROR1+ADD u16 checksum** + geometry sanity. **No CRC64, no clock.** | primary unless its **read physically fails** | dual-write on a normal (non-SMR) volume; **but observed to skip the backup on upgrade** (see below) |
| **Superblock (SUPB)** | 3 — **LCN 0x1E** + `VolSize−2` + `VolSize−3` | computed from volume size (not pointed-to) | **cluster-size-dependent self-checksum** + structure (`+0x74`==2 checkpoint count, `+0x70` list, self-LCN check) + clock `+0x68` | **highest virtual clock among VALIDATING copies** (primary 0x1E not privileged) | **self-healed at mount** when the 3 copies disagree; on volume grow (`MoveSuperBlock`, clock+1); on scrub |
| **Checkpoint (CHKP)** | 2 alternating slots | LCNs from the `SUPB+0x70` list | **cluster-size-dependent self-checksum** + structure + clock `+0x60` | **highest virtual clock among VALIDATING copies** | **alternated on every flush** (other slot, clock+1); the just-read record is refreshed at mount |

The pattern to keep in mind: the **superblock and checkpoint are self-aware** (each copy proves its own
integrity and dates itself), while the **boot sector is not**. That single asymmetry drives every
forensic consequence below.

## Boot sector — read first, validated last, never reconciled

`RefsReadBootSector` (`ReadBootSectorForMount` on Insider) reads sector 0, then the last LBA. The
fallback loop breaks on the **first successful READ**, so the last-sector backup is consulted **only when
the primary read physically fails** (an I/O error) — *not* when the primary reads successfully but is
semantically wrong. Whichever copy is read is then handed to `RefsIsBootSectorOurs`, which validates it
with the **0x16 self-checksum** — a rotate-right-1-then-add u16 over bytes 3..end, skipping the two
checksum bytes at 0x16/0x17, exactly the algorithm `forefst._vbr_checksum` reimplements — plus a
geometry sanity check on the sector/cluster fields.

Critically, there is **no cross-copy checksum and no virtual clock** on the boot sector. The driver has
no way to compare the two copies and decide which is newer; it simply takes whichever it reads first,
provided it passes its own self-check. The two copies are therefore **never reconciled against each
other**, which is precisely why the backup can preserve a stale version. (The [VBR](../structures/vbr.md)
page documents the byte layout, including the `totalSectors` field at 0x18 that fixes the backup's LBA,
and the version field at 0x28 that the backup can preserve.)

## Superblock — self-checksummed, clock-selected, self-healed

`CmsVolume::ReadSuperBlock` reads all three copies through `ReadAndRepairSelfChecksumBlock`, validates
each with `ValidateSuperBlock`, and selects with `ChooseSuperBlock`. The three positions are **computed
from the volume size** — primary at LCN 0x1E, backups at `VolSize−2` and `VolSize−3` — not stored as
pointers, so a parser locates all three from the volume geometry alone.

Each copy must pass a **self-checksum** (see [Checksum Architecture](checksum_architecture.md) for how
this differs from the per-page Merkle checksum). The superblock sits *outside* the page-reference Merkle
tree — no parent page holds its checksum — so it carries its own. The algorithm is **cluster-size
dependent**, named by a cktype byte in a `LcnWithChecksum` self-descriptor at SUPB+0xD0: **CRC32-C
(4 bytes)** on 4K-cluster volumes, **CRC64 (8 bytes)** on 64K-cluster volumes, and **SHA-256 (32 bytes)**
on SHA-256 volumes. To verify it by hand: zero the whole descriptor, then hash exactly one cluster
`[block, block+cluster_size)` and compare against the digest stored at descriptor+0x28.

Among the copies that pass validation, the winner is the one with the **highest virtual clock at
`+0x68`** — LCN 0x1E carries **no priority**. A copy that fails its self-checksum never participates, so
a corrupt primary **silently falls back** to a backup with no visible error. When the three copies
disagree at mount on a writable volume, the driver **self-heals**: it copies the winner over each stale
copy, re-stamps the `SUPB` header, recomputes the self-checksum, and writes it back. This is the
mechanism behind the "silent repair" an analyst sees after hand-editing a superblock byte — the edit
fails that copy's checksum, the copy is dropped, and mount overwrites it with the healthy winner.

## Checkpoint — alternating slots, the loser is a rollback target

`CmsVolume::ReadLatestCheckpoint` reads the two checkpoint slots (whose LCNs come from the superblock's
`+0x70` list) the same way, validating with `ValidateCheckpointRecordCallback` and selecting with
`ChooseCheckpointRecord`. Each slot carries the **same cluster-size-dependent self-checksum** as the
superblock. The slot with the **highest virtual clock at `+0x60`** among those that validate is the
current one; an invalid higher-clock slot is **skipped automatically** in favour of the lower-clock valid
slot. If **both** slots fail validation, mount fails with a disk-corrupt status (`-0x3fffffce`).

The alternation is what makes the checkpoint forensically interesting. Every flush writes the **other**
slot with `clock+1`, so the just-superseded slot is left intact carrying the **previous consistent
state** — the metadata roots as they stood before the last flush — until the next flush overwrites it.
That alternation is the atomic commit point of the volume; the [Transactional
Crash-Consistency](transactions_crash_consistency.md) page covers how it pairs with the redo log, and
[Copy-on-Write](copy_on_write.md) explains why the prior roots are still readable (the old B+-tree pages
were never overwritten in place).

## Forensic value

The redundancy is not just resilience — each of the three policies leaves a recoverable artifact.

- **The backup boot sector is a record of the volume's original state.** Because it is not reliably
  rewritten and is never reconciled against the primary, a divergent backup VBR is a forensic signal. On
  a genuine **upgrade**, the backup retains the **original pre-upgrade version** (for example primary
  v3.14 with a backup still reading v3.4, or v3.14 with a v3.9 backup) — recovering the *exact* original
  version where [Version Detection](version_detection.md) from `$VolInfo` alone could only say
  "pre-v3.10". On **VBR tampering**, the same divergence exposes it: the backup holds the authentic
  version while the primary carries an altered one (for example an impossible v6.66 or v3.15 primary over
  an authentic v3.14 backup). The driver cannot detect either case, because the boot sector has no
  cross-copy check.

- **The lower-clock checkpoint is a rollback target.** It holds the metadata roots from before the last
  flush — recoverable prior-tree state. On a *cleanly* shut volume the two checkpoints usually decode to
  the **same** 13-root list (only the clock and per-page checksums differ), so the alternate checkpoint
  yields no new whole-tree state there; meaningful divergence appears around an **in-progress flush** or
  a mid-transaction crash. Prior states on a clean volume come instead from
  [snapshots](snapshots_versioning.md) and superseded pages (see [Deletion
  Recovery](deletion_recovery.md)).

- **A tool can detect corruption the driver tolerates.** Because the superblock and checkpoint carry a
  verifiable **self-checksum** (cktype byte at descriptor+0x22, digest at +0x28; zero the descriptor,
  hash one cluster), an analysis tool can independently confirm — or refute — the integrity of each copy,
  catching a silently-corrupted-but-healable block the driver would simply heal past. The boot sector has
  only its weak 0x16 self-checksum and no cross-copy reconciliation, so divergence there is invisible to
  the driver but plain to a tool that compares the two copies directly.

## What `forefst.py integrity` reports

The **Redundancy / Backup Copies** section verifies all three structures: the backup boot sector (0x16
self-checksum plus a byte-compare to the primary, flagging a version mismatch honestly as "upgrade or
tampering"), the checkpoint pair (signature, virtual clock, and valid roots, labelling the copies
PRIMARY/backup by clock), and the superblock copies (located and signature-checked). Failover — actually
*using* a backup when the primary is corrupt, the way the driver does — is documented but not yet
implemented in the tool.

## Cross-references

- [VBR](../structures/vbr.md) — the boot-sector byte layout, the `totalSectors` field (0x18) that fixes the backup LBA, and the version field (0x28) the backup preserves
- [Superblock (SUPB)](../structures/supb.md) — the structure replicated three times, with the self-descriptor at +0xD0 and the clock at +0x68
- [Checkpoint (CHKP)](../structures/chkp.md) — the alternating commit record, with the clock at +0x60 and the 13 table roots
- [Bootstrap Chain](bootstrap_chain.md) — the parse order in which these three anchors are read
- [Checksum Architecture](checksum_architecture.md) — why the self-checksum is distinct from the per-page Merkle checksum
- [Version Detection](version_detection.md) — how the backup VBR recovers the exact original version on an upgrade
- [Transactional Crash-Consistency](transactions_crash_consistency.md) — the checkpoint alternation as the atomic commit point
- [Copy-on-Write](copy_on_write.md) — why the lower-clock checkpoint's prior roots are still readable
- [Snapshots & Versioning](snapshots_versioning.md) — the other source of recoverable prior state
- [Deletion Recovery](deletion_recovery.md) — superseded pages as a prior-state source

## Evidence

The boot-sector read/validate/fallback path (`RefsReadBootSector` / `ReadBootSectorForMount`,
`RefsIsBootSectorOurs`) and the absence of any cross-copy boot-sector check are confirmed in the driver
(E2) and matched on the raw-disk corpus (RD); the backup-VBR divergence on upgrade and on tampering is
finding **FS_VBR_RA_013**. The superblock and checkpoint mechanics — self-checksum, clock-based selection
(`ChooseSuperBlock` at SUPB+0x68, `ChooseCheckpointRecord` at CHKP+0x60), auto-fallback, and superblock
self-heal — are decompiled (E2) via `CmsVolume::ReadSuperBlock` / `ValidateSuperBlock` and
`CmsVolume::ReadLatestCheckpoint` / `ValidateCheckpointRecordCallback`, with finding **FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003**. The
cluster-size-dependent self-checksum (CRC32-C 4 B on 4K, CRC64 8 B on 64K, SHA-256 32 B on SHA-256) is
**proven by recomputation** against the stored digest across the corpus (RD). The clean-volume result
that the two checkpoints decode to identical roots is finding **FS_CHKP_RA_014**. See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
