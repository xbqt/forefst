# Volume Redundancy — Boot Sector, Superblock, Checkpoint copies

Every ReFS volume keeps redundant copies of the three structures it needs to mount — the
[boot sector](../structures/vbr.md), the [superblock](../structures/supb.md), and the
[checkpoint](../structures/chkp.md) — but it does **not** maintain them the same way, and that
difference is what makes them useful to a forensic analyst.

- The superblock and the checkpoint carry a strong self-checksum and an ordering value (the superblock's
  generation, the checkpoint's virtual clock), so the driver can tell which copy to read and silently fall back
  when one is corrupt.
- The boot sector carries only a weak 16-bit self-checksum and no ordering value, so its backup can drift out of
  sync with the primary and preserve the volume's *original* state.

This page explains how each redundant copy is located, validated, and selected, and what each one lets an analyst
recover.

## Three structures, three redundancy policies

The bootstrap anchors sit at the front of the [bootstrap chain](bootstrap_chain.md): the parser reads
the boot sector, follows it to the superblock, and follows the superblock to the checkpoint that holds
the 13 table roots. Each of the three is replicated, but with a different locating, validation, and
selection rule.

| Structure | Copies | Located by | Validation | Selection | Rewritten when… |
|-----------|--------|-----------|-----------|-----------|-----------------|
| **Boot sector (VBR)** | 2 — sector 0 + the volume's **last sector** | written at `T−1` (`T` = `VBR+0x18`); read at mount at sector ⌊P / 64 MiB⌋ × (64 MiB / sector size) − 1 of the partition (P its length) | self-contained: signature + **0x16 ROR1+ADD u16 checksum** + geometry sanity. **No CRC64, no clock.** | primary unless its **read physically fails** | dual-write on a normal (non-SMR) volume; **but observed to skip the backup on upgrade** (see below) |
| **Superblock (SUPB)** | 3 — **LCN 0x1E** + `VolSize−2` + `VolSize−3` | computed from volume size (not pointed-to) | **cluster-size-dependent self-checksum** + structure (`+0x74`==2 checkpoint count, `+0x70` list, self-LCN check); generation `+0x68` | **the primary at LCN 0x1E when it passes its tests**; otherwise the valid backup with the higher `+0x68` | **self-healed at a writable mount** when the copies disagree; on volume grow (`MoveSuperBlock`: the backups only, generation + 1) |
| **Checkpoint (CHKP)** | 2 alternating slots | LCNs from the `SUPB+0x70` list | **cluster-size-dependent self-checksum** + structure + clock `+0x60` | **slot order; a later valid copy only on a strictly higher `+0x60`** (a tie keeps slot 0) | **alternated on every flush** (other slot, clock+1); the just-read record is refreshed at mount |

Each **superblock and checkpoint** copy carries a strong self-checksum and an ordering value, so each copy can be
checked and ordered on its own. The **boot sector** carries only a weak self-checksum and no ordering value. Every
forensic consequence below follows from this difference.

## Boot sector: which copy is read

`RefsReadBootSector` (`ReadBootSectorForMount` on Insider) reads sector 0, and the backup only when that
read fails. The fallback loop breaks on the **first successful READ**, so the backup is consulted **only when
the primary read physically fails** (an I/O error) — *not* when the primary reads successfully but is
semantically wrong. Whichever copy is read is then handed to `RefsIsBootSectorOurs`, which validates it
with the **0x16 self-checksum** — a rotate-right-1-then-add u16 over bytes 3..end, skipping the two
checksum bytes at 0x16/0x17, exactly the algorithm `forefst._vbr_checksum` reimplements — plus a
geometry sanity check on the sector/cluster fields.

There is **no cross-copy checksum and no virtual clock** on the boot sector. The driver has
no way to compare the two copies and decide which is newer; it takes whichever it reads first,
provided it passes its own self-check. The two copies are therefore **never reconciled against each
other**, which is why the backup can preserve a stale version. (The [VBR](../structures/vbr.md)
page documents the byte layout, including the `totalSectors` field at 0x18 that fixes where the backup is
written, and the version field at 0x28 that the backup can preserve.)

On the corpus the two copies differ on a few volumes: on the upgraded volumes at the checksum and the version only,
and on the hand-edited volumes at the version, the Extended GUID and the flags (counts in Evidence).

## Superblock — self-checksummed, primary-first, self-healed

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

The driver takes the **first copy that passes validation** in the order LCN 0x1E, `VolSize−2`,
`VolSize−3`; a later valid copy replaces it only when the chosen copy is a backup and the later one's
generation at `+0x68` is strictly higher. So a primary that passes is read **whatever the backups hold**,
and `+0x68` orders only the two backups. A copy that fails its self-checksum never participates, so a
corrupt primary **silently falls back** to a backup with no visible error. After the choice the driver
**self-heals**: it rewrites every other copy from the chosen one, re-stamping the `SUPB` header and
recomputing the self-checksum, unless both other copies validate with the same `+0x68` as the chosen one
or the device is write-protected.

This is the mechanism behind the "silent repair" an analyst sees after hand-editing a superblock byte — the edit
fails that copy's checksum, the copy is dropped, and mount overwrites it with the chosen copy.

## Checkpoint: which copy is chosen

`CmsVolume::ReadLatestCheckpoint` reads the two checkpoint slots (whose LCNs come from the superblock's
`+0x70` list) the same way, validating with `ValidateCheckpointRecordCallback` and choosing in its own slot loop
(17134 calls `ChooseCheckpointRecord` there; the 26100 and Insider builds compare inline). Each slot carries the
**same cluster-size-dependent self-checksum** as the superblock. The rule:

- the slots are read in the order of the superblock's list, and a copy whose self-checksum fails is skipped;
- a later copy replaces the one kept only when its virtual clock at `+0x60` is **strictly greater**, so a tie
  between two valid copies keeps slot 0 and an invalid higher-clock slot is skipped in favour of the valid one;
- on the 26100 builds a first pass also rejects a copy whose root 0xC, 7 or 8 fails to read or verify (Insider
  29574, 29659 and 29683: only a read error rejects; 17134 makes no root check); only when neither copy passes does
  a second pass run without the root check;
- a copy a build rejects for its record is not read: the root count (`+0x90`: more than 4, at most a quarter of the
  record size), the indirect offset table (flag 0x200 at `+0x78`: `+0x94` / `+0x98` inside the record, at least 4
  bytes per root; ReFS 3.11 and later), a root descriptor, or the area at `+0x88` / `+0x8C`;
- if **both** slots fail, mount fails with a disk-corrupt status (`0xC0000032`).

The copy choice is read on 17134, 26100.8115 to .9974 and Insider 29574, and also on Insider 29659 and 29683.

The alternation is what makes the checkpoint useful to an examiner. Every flush writes the **other**
slot with `clock+1`, so the just-superseded slot is left intact carrying the **previous consistent
state** — the metadata roots as they stood before the last flush — until the next flush overwrites it.
That alternation is the atomic commit point of the volume; the [Transactional
Crash-Consistency](transactions_crash_consistency.md) page covers how it pairs with the redo log, and
[Copy-on-Write](copy_on_write.md) explains why the prior roots are still readable (the old B+-tree pages
were never overwritten in place).

## Forensic value

Besides keeping the volume mountable, each of the three policies leaves a recoverable artifact.

- **The backup boot sector is a record of the volume's original state.** Because it is not reliably
  rewritten and is never reconciled against the primary, a divergent backup VBR is a forensic signal. On
  a genuine **upgrade**, the backup retains the **original pre-upgrade version** (for example primary
  v3.14 with a backup still reading v3.4, or v3.14 with a v3.9 backup) — recovering the *exact* original
  version where [Version Detection](version_detection.md) from `$VolInfo` alone could only say
  "pre-v3.10". On **VBR tampering**, the same divergence exposes it: the backup holds the authentic
  version while the primary carries an altered one (for example a primary reading v6.66, which no ReFS
  version has ever been, or v3.15, which is the maximum a preview driver can *write* but which no
  volume is formatted with — over an authentic v3.14 backup). The driver cannot detect either case, because the
  boot sector has no cross-copy check.

  **But this exposes only tampering the driver leaves alone.** A version set *below* the volume's true
  format is rewritten upward the next time the volume is mounted, and the boot sector's own checksum is
  recomputed with it. The correction writes **both** copies — the backup first, then the primary — so a
  volume edited to an older version and then mounted once carries a boot sector byte-for-byte identical to
  an untouched one, and there is no divergence left for the check above to find. A consistent version field
  is therefore not evidence that the field was never altered; only an edit the driver does not correct
  (a higher version, or an impossible one) survives to be caught this way.

  A genuine *upgrade* behaves differently from this correction: the measured upgrades left the pre-upgrade
  version behind in the backup, while the correction rewrites both copies. Which write path the upgrade takes is
  not stated in the records read for this page.

- **The lower-clock checkpoint is a rollback target.** It holds the metadata roots from before the last
  flush — recoverable prior-tree state. On a *cleanly* shut volume the two checkpoints usually decode to
  the **same** 13-root list (on the images measured and on all but one of the volumes of the blind audit; on that
  ReFS 3.4 volume five roots differ), so the alternate checkpoint yields no new whole-tree state there.
  - The two records still differ in their own LCN, their self-descriptor's LCN, their checksums and their allocator
    clock, and usually in their virtual clocks.
  - A different tree appears only in an image taken between two checkpoint writes that changed a root table.
  - Prior states on a clean volume come instead from [snapshots](snapshots_versioning.md) and superseded pages (see
    [Deletion Recovery](deletion_recovery.md)).

- **A tool can detect corruption the driver tolerates.** Because the superblock and checkpoint carry a
  verifiable **self-checksum** (cktype byte at descriptor+0x22, digest at +0x28; zero the descriptor,
  hash one cluster), an analysis tool can independently confirm — or refute — the integrity of each copy,
  catching a corrupt block that the driver would repair without reporting it. The boot sector has
  only its weak 0x16 self-checksum and no cross-copy reconciliation, so the driver does not see a divergence
  there, but a tool that compares the two copies directly does.

## What `forefst.py integrity` reports

The **Redundancy / Backup Copies** section verifies all three structures: the backup boot sector (0x16
self-checksum plus a byte-compare to the primary, flagging a version mismatch as "upgrade or
tampering"), the checkpoint pair (signature, virtual clock, the self-checksum, and the roots 0xC, 7 and 8 of
each copy against that copy's digests; each copy named by its role, `in use`, `newest`, `superseded` or `tied`; a
copy that fails is a finding, and a newer copy whose root list cannot be read is named, the view then stale), and
the superblock copies (located, self-checksum-verified, and their payloads compared with the copy read, each
copy's own LCN and self-checksum left out: two copies that both pass and differ are a redundancy finding, exit 2,
naming both and the differing bytes).

## Repairing a corrupt copy — `refsanalysis bootedit repair`

Because each copy can be checked on its own, a copy that fails can be **restored from a copy that
passes** — for the superblock this is what the driver itself does when it reads the volume, done here
offline, on a copy of the image. `refsanalysis.py <image> bootedit repair` checks every redundant copy of
the bootstrap and plans one restore per failing boot-sector or superblock copy:

- **Boot sector.** A copy is one whole sector — the boot sector's bytes per sector, 4096 on a 4Kn disk,
  the unit the driver reads and writes. A primary that fails the boot-sector tests is restored from the
  backup the volume is read from; a backup that carries the ReFS signature and fails is restored from the
  primary. The primary is **not** restored from a backup that records another version than the primary,
  or an earlier one than the volume's own records show (its checkpoint and `$VOLUME_INFORMATION`): a
  version upgrade rewrites sector 0 only, so the backup can keep the pre-upgrade version (see above), and
  which version is the volume's cannot be decided from the copies. A position that holds no boot sector is not written.
- **Superblock.** A copy at LCN 0x1E, `VolSize−2` or `VolSize−3` that fails the superblock tests — with or
  without its `SUPB` signature — is rebuilt from the copy the volume is read from: the cluster is copied,
  its own LCN is set at `+0x20` and at the start of the self-descriptor, and its self-checksum is
  recomputed. The rebuilt copy must pass the same tests at its own LCN before it is written. Rebuilt this
  way from any copy that passes, a cluster equals every other copy that passes on the corpus volumes, byte
  for byte (every pair measured; every copy's self-descriptor is at `+0xD0` and starts with the copy's own LCN).
  The driver's own rewrite also stamps the header clocks of that moment (`+0x10`, `+0x18`), which this restore
  keeps from the source. A copy whose checksum type the tool does not compute is not
  rebuilt.
- **Checkpoint.** Each slot is its own record of the volume's state, not a copy of the other (their
  clocks usually differ, and two slots with the same clock are still two records), so a corrupt slot
  cannot be reconstructed from the other. It is reported — with what fails: its
  self-checksum, a root that does not match the digest the copy records for it, or why it could not be
  read — and never rewritten.

Nothing is written past the end of the image. By default the repair writes a **repaired sparse copy**
and never touches the original; `--inplace` edits the image directly (after a typed `YES`), and
`--dry-run` previews the plan without writing. Each restore is printed and appended to
`<output>.repair.log` with its source copy, offset, length and the SHA-256 of the bytes there before and
after, and every copy is then checked again on the result. The command exits 2 when a copy fails,
whether or not it was restored.

## Cross-references

- [VBR](../structures/vbr.md) — the boot-sector byte layout, the `totalSectors` field (0x18) that fixes where the backup is written, and the version field (0x28) the backup preserves
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
and matched on the raw-disk corpus, as is the backup-VBR divergence on upgrade and on tampering. The
superblock and checkpoint mechanics — self-checksum, the selection rules above, auto-fallback, and superblock
self-heal — are decompiled via `CmsVolume::ReadSuperBlock` / `ValidateSuperBlock` and
`CmsVolume::ReadLatestCheckpoint` / `ValidateCheckpointRecordCallback`. The cluster-size-dependent self-checksum
(CRC32-C 4 B on 4K, CRC64 8 B on 64K, SHA-256 32 B on SHA-256) is **proven by recomputation** against the stored
digest across the corpus. The checkpoint copies' root lists are compared on disk on the volumes named above.

The counts behind the text:

- the boot-sector copies differ on 10 of 117 ReFS volumes: on the three upgraded volumes at the checksum and the
  version only, and on seven hand-edited volumes at the version, the Extended GUID and the flags; the backup sits at
  (T−1) × bytes per sector on all 117;
- the downward-version correction rests on the driver reading and on post-mount captures only (the corpus holds no
  pre-mount image of such an edit);
- the checkpoint copies decode to the same root list on 25 of the 26 volumes of the first blind audit;
- a superblock copy rebuilt from any copy that passes equals every other passing copy on 694 of 694 pairs on 117
  volumes, and every copy's self-descriptor is at `+0xD0` and starts with its own LCN on 351 of 351.

See [how this was verified](../methodology.md) for the method.

<!-- findings: CT_MISC_001, FS_CHKP_005, FS_CHKP_RA_014, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_003, FS_VBR_RA_013, FS_VBR_RA_014 -->
