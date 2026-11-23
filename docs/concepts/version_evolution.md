# Version Evolution

ReFS has several closely related formats. A parser that ignores the differences between them silently misreads
some volumes.

Across the five formats read here — v3.4 (Windows 10 1803) through v3.14 (Windows 11 24H2, and the Insider builds,
which write v3.14 too) — Microsoft changed:

- the size of the checkpoint's [page references](../structures/page_references.md);
- the boot sector, which gained a checksum selector;
- the set of [schemas](../structures/schema_table.md), adding and retiring some;
- the [checkpoint](../structures/chkp.md) flag word.

A tool that assumes a single layout will be wrong on some fraction of the corpus.

This page is the canonical record of *what* changed at each transition; its companion
[Version Detection](version_detection.md) covers *how* to classify a given volume — including how to tell
a natively formatted v3.14 volume from an older one that was upgraded in place.

## Version timeline

The version is a `major.minor` pair of bytes at [VBR](../structures/vbr.md) offset 0x28. It names the format the
volume is at: the Windows release that formatted it, or the one that upgraded it:

| Version | Windows build | Release | Key change |
|---------|--------------|---------|------------|
| 3.4 | Win10 1803 | 2018 | Earliest version covered here |
| 3.7 | Win11 21H2 | 2021 | +3 attribute schemas |
| 3.9 | Win11 22H2 | 2022 | +Candidate Table |
| 3.10 | Win11 23H2 | 2023 | Compact page references, checksum selector in the boot sector, native-format marker |
| 3.14 | Win11 24H2 | 2024 | Indirect root list, rollback-protection fields |
| 3.14 | Insider (29574 and later) | Pre-release | Same format; boot volume, TPM attestation |

The version field alone is not enough. A v3.4 volume that has been mounted on Windows 11
reports version 0x030E (v3.14) in the VBR but retains v3.4-era structures internally — see
[Upgrade behavior](#upgrade-behavior) below and [Version Detection](version_detection.md) for how to tell
the two apart.

### The driver builds read

The `refs.sys` builds read for this reference are those of Windows 10 1803 (17134, format 3.4), eight builds of
the Windows 11 26100 line (26100.8115 to 26100.9974, format 3.14) and three Insider builds (29574, 29659 and 29683). The
formats 3.7, 3.9 and 3.10 are read on disk only: the drivers of their Windows releases are not held.

- The list, with how each build was read and the volumes each is known to have written:
  [Driver builds analysed](../methodology/driver_builds.md).
- What changed from one build to the next: [Driver Evolution](driver_evolution.md).

## Per-transition changes

### v3.4 to v3.7

Three new table schemas appear in the schema table; no system schemas change. This is also where the volume-flags byte
gains the hard-link support flag (bit 0x20).

| Addition | Details |
|----------|---------|
| Schemas 0x1C0, 0x1D0 | the tables of a file's record and of a directory's own row from format 3.6: new objects get them, and an older object moves to them when it is opened ([Schema Table](../structures/schema_table.md#which-id-a-record-carries)) |
| Schema 0x1B0 | registered; no driver code read uses it and no corpus object carries it |
| VBR flags (0x2C) | 0x06 → 0x26 (bit 5 set: hard-link support) |

### v3.7 to v3.9

A single new system schema: the Candidate Table, which tracks dirty page ranges for the checkpoint
mechanism.

| Addition | Details |
|----------|---------|
| Schema 0xe120 | Candidate Table (dirty range tracking) |

### v3.9 to v3.10

The most consequential single transition. Three things happen together that change how a volume is read:

- the checkpoint's root page references shrink from 104 to 48 bytes (the references inside the trees are 48 bytes on
  every format);
- CRC64 is *declared* in the VBR;
- a native-format marker is set in the checkpoint.

Of the three, an upgrade of an older volume makes only the first (it rewrites the checkpoint's root references to 48
bytes) and sets neither marker.

| Change | Details |
|--------|---------|
| Schema 0xe130 | Heat Engine (`CmsVolumeHeatEngine`) — the schema of its I/O metrics table (OID 0x30) |
| OID 0x30 | Heat engine table — when the volume had I/O, in 10-minute generations |
| VBR 0x48 | Extended GUID populated (all-zero on older or upgraded volumes) |
| VBR flags (0x2C) | 0x26 → 0x66 (bit 0x40: native v3.10+ format; the driver reads 0x2A only with it) |
| CHKP flag 0x0080 | Native-format marker (set only at format time) |
| VBR 0x2A | Checksum selector, 0x02 (CRC64) at format time |
| Checkpoint root reference size | 104 bytes (0x68) → 48 bytes (0x30), `CHKP+0x5C` — the 56 zero bytes dropped |
| CHKP +0x50 | Version-echo field (zero on older or upgraded volumes) |
| Removed | Legacy schemas 0xe050 and 0xe0f0 dropped |

The page-reference shrink is the change most likely to break a parser: the structure that anchors the
[checksum Merkle tree](checksum_architecture.md) has a different size before and after v3.10, and the
correct size depends on the checksum type as well as the version — see
[Page References](../structures/page_references.md).

The selector names the algorithm the earlier formats already used: their page references carry CRC64 too, and the
Windows 10 driver checks a page against its reference when it reads it from disk.

### v3.10 to v3.14

The checkpoint can reach its root list through a table of offsets (the indirect mode, below). Three more table
schemas appear.

| Change | Details |
|--------|---------|
| Schemas 0x1E0, 0x1F0, 0x200 | the tables of a file's record, of a directory's own row and of a data stream from format 3.11 |
| CHKP flag 0x0200 | Indirect root list mode |
| CHKP flag 0x0400 | The record carries the rollback-protection fields (+0x9C / +0xA0); set on a volume of version 3.13 or later |
| Rollback protection | `CmsRollbackProtection` — present in the 26100 and Insider drivers, absent from 17134 |
| SHA-256 option | VBR 0x2A = 0x04, page reference size 72 bytes (0x48) — every SHA-256 volume measured is v3.14 |
| Removed | Legacy schemas 0xe070, 0xe0e0; legacy attribute schemas 0x004, 0x006 |

Two flags distinguish v3.14 from v3.10 in the [checkpoint](../structures/chkp.md):

- 0x0200 selects indirect root storage (used from version 3.11 in the driver);
- 0x0400 marks the record's rollback-protection fields (set from version 3.13).

No 3.11–3.13 volume is in the corpus.

Either way the root [page references](../structures/page_references.md) are reached through 13 `u32` in-record
offsets, never stored inline at `0x94`:

- without 0x0200, `CHKP+0x94` holds the 13 offsets themselves;
- with it, `CHKP+0x94` is the offset of a table of those 13 offsets inside the same record.

Measured over the direct-mode checkpoint copies (flag 0x0200 clear) of the corpus: **every one** resolves when the
13 words are read as offsets.

The retirement of the 0x004 and 0x006 legacy attribute schemas is why a freshly formatted v3.14 volume has a smaller
schema table than its predecessors even though it gained new attributes.

### Insider-only features

Windows Server Insider builds (29574 and later) can install on and boot from a ReFS volume, as Microsoft announced
in February 2026 ([Announcing ReFS Boot for Windows Server Insiders](https://techcommunity.microsoft.com/blog/windowsservernewsandbestpractices/announcing-refs-boot-for-windows-server-insiders/4496592)). The test corpus holds one such boot
volume, the C: drive of a Windows Server Insider 29574 machine. The Insider drivers also add a volume attestation by
TPM or certificate.

| Feature | Details |
|---------|---------|
| CHKP flag 0x2000 | Marks the record's attestation HMAC area; set on the volumes an Insider build mounted |
| Schema 0xe140 | Volume Attestation Table (`CmsVolumeAttestation`) |
| Boot volume | Windows (Server Insider) can be installed on and boot from a ReFS volume |
| TPM attestation | `CmsVolumeAttestation` (in the Insider driver only) — certificate / HMAC-key material |

## CHKP flag evolution

The [checkpoint](../structures/chkp.md) flag word at CHKP+0x78 is the single most useful discriminator
between versions and between native and upgraded volumes, because the format and upgrade bits accumulate.
[Version Detection](version_detection.md) keys off the composite values in this table.

| Version | Flags (hex) | Key additions |
|---------|-------------|---------------|
| v3.4 | 0x0002 | Base flag (always set) |
| v3.7–v3.9 | 0x0002 | Unchanged |
| v3.10 | 0x0082 | +native format (0x0080) |
| v3.14 native | 0x0682 | +indirect roots (0x0200), +rollback-protection fields (0x0400) |
| v3.14 upgraded | 0x0602 | Same as native but **missing** native marker (0x0080) |
| Insider | 0x2682 | +attestation HMAC (0x2000) |

The decisive detail is the native-format marker (0x0080): it is set **only at format time**, and no upgraded volume
measured carries it. That single missing bit is what separates a native v3.14 volume (0x0682) from an upgraded one
(0x0602). The capabilities listed under [Capability differences](#capability-differences) follow the boot-sector
flags, not this bit.

## Schema version-gating matrix

These tables show which [schemas](../structures/schema_table.md) exist on each version. `Y` = present,
`—` = absent. The schema table is self-describing, so a parser can read it directly rather than hard-coding
these — but knowing the expected set is what lets you spot an upgraded volume (which carries the *union* of
old and new) or a corrupted one.

### Attribute schemas

| Schema | Name | v3.4 | v3.7 | v3.9 | v3.10 | v3.14 | Insider |
|--------|------|:----:|:----:|:----:|:-----:|:-----:|:-------:|
| 0x004 | (legacy) | Y | Y | Y | Y | — | — |
| 0x006 | (legacy) | Y | Y | Y | Y | — | — |
| 0x110–0x1A0 | Core attributes | Y | Y | Y | Y | Y | Y |
| 0x1B0 | $SNAPSHOT | — | Y | Y | Y | Y | Y |
| 0x1C0 | $REPARSE_POINT | — | Y | Y | Y | Y | Y |
| 0x1D0 | $EA_INFORMATION | — | Y | Y | Y | Y | Y |
| 0x1E0 | $EA | — | — | — | — | Y | Y |
| 0x1F0 | $LOGGED_UTILITY_STREAM | — | — | — | — | Y | Y |
| 0x200 | $EFS | — | — | — | — | Y | Y |

### System schemas

| Schema | Name | v3.4 | v3.7 | v3.9 | v3.10 | v3.14 | Insider |
|--------|------|:----:|:----:|:----:|:-----:|:-----:|:-------:|
| 0xe010–0xe040 | Core system | Y | Y | Y | Y | Y | Y |
| 0xe050 | (legacy) | Y | Y | Y | — | — | — |
| 0xe060 | Schema Table | Y | Y | Y | Y | Y | Y |
| 0xe070 | (legacy) | Y | Y | Y | Y | — | — |
| 0xe080–0xe090 | Integrity / Upcase | Y | Y | Y | Y | Y | Y |
| 0xe0b0–0xe0d0 | Refcount / Container / Trash | Y | Y | Y | Y | Y | Y |
| 0xe0e0 | (legacy) | Y | Y | Y | Y | — | — |
| 0xe0f0 | (legacy) | Y | Y | Y | — | — | — |
| 0xe100–0xe110 | Container Index / Read Cache | Y | Y | Y | Y | Y | Y |
| 0xe120 | Candidate Table | — | — | Y | Y | Y | Y |
| 0xe130 | Heat Engine | — | — | — | Y | Y | Y |
| 0xe140 | Volume Attestation | — | — | — | — | — | Y |

### Schema table entry counts

The leaf-row count of the schema table is itself a version signature. The dip at v3.14 (29, down from 30
at v3.7) is real: v3.14 gains three attribute schemas but retires the two legacy attribute schemas
(0x004, 0x006) and several legacy system schemas, for a net loss of one row.

| Version | System | Attribute | Total |
|---------|--------|-----------|-------|
| v3.4 | 15 | 12 | 27 |
| v3.7 | 15 | 15 | 30 |
| v3.9 | 16 | 15 | 31 |
| v3.10 | 15 | 15 | 30 |
| v3.14 | 13 | 16 | 29 |
| Insider | 14 | 16 | 30 |
| Upgraded (union) | up to 18 | up to 18 | up to 36 |

An upgraded volume retains every legacy schema alongside the new ones, producing a union set larger than
any natively formatted version. A schema-table count above 31 is therefore a strong upgrade indicator.

## Object table entry counts

The heat engine table (OID 0x30) is the version-gated entry to watch in the
[Object Table](../structures/object_table.md): it is absent on v3.4–v3.9 and appears at v3.10; on an upgraded volume
the first mount by a 26100 or Insider driver creates it (no 3.10 driver is held). It holds the heat engine's I/O metrics in 10-minute generations,
which makes its presence a version marker and its generation times a record of when the volume had I/O.

| Version | System OIDs | Notes |
|---------|-------------|-------|
| v3.4–v3.9 | base set | No OID 0x30 |
| v3.10 | +OID 0x30 | Heat engine table appears |
| v3.14 | full set | Includes OID 0x30 |

## Upgrade behavior

On the two volumes measured (a 3.4 and a 3.9 volume), the first Windows 11 mount upgraded the volume in place to
v3.14. The driver:

- rewrites the version and recalculates the VBR checksum;
- adds the new schemas (as a union with the old);
- bumps the [checkpoint](../structures/chkp.md) flags;
- advances the virtual clock by the checkpoints it writes.

It leaves the format-time fields alone. The result is a volume that *reports* v3.14 yet lacks the native-format
marker, and every version-detection routine relies on this difference.

### Fields modified

| Field | Before | After |
|-------|--------|-------|
| VBR version (0x28) | 0x0304 | 0x030E |
| VBR checksum (0x16) | Old | Recalculated |
| CHKP flags | 0x002 | 0x602 |
| Schema Table | 27 entries | 29+ entries (union) |
| Virtual clock | its value before the mount | + the checkpoints written during the upgrade (41 and 35 on the two upgrades measured) |

The table shows the 3.4 volume's values; the 3.9 volume's version went from 3.9 to 3.14 in the same way.

### Fields unchanged (format-time fields)

These are set at format time and kept their values across the two upgrades measured:

- no boot-sector write path of refs.sys 26100.9444 assigns 0x2A or 0x48 (`refsutil fixboot` rewrites both);
- of the flags at 0x2C only the bits 0x20 and 0x40 come from the format, the driver setting the others at run time.

They are the basis of upgrade detection, because they keep the original format's identity after the version field
has been rewritten.

| Field | Stays at |
|-------|----------|
| VBR checksum algorithm (0x2A) | 0x0000 (not read: the page references carry CRC64) |
| VBR volume flags (0x2C), bits 0x20 and 0x40 | clear on a 3.4 volume (0x06) |
| VBR Extended GUID (0x48) | All-zero |
| Volume serial number (0x38) | Original value |

A native v3.14 volume, by contrast, has 0x2A = 0x02 (CRC64) or 0x04 (SHA-256), 0x2C = 0x66, and a populated
Extended GUID — so the VBR alone distinguishes the two even before the checkpoint is read (unless `refsutil fixboot`
rewrote it).

### Capability differences

The format a volume was created at decides a capability: refs.sys supports hard links on a volume exactly when its
boot-sector flags (`+0x2C`) carry bit 0x20 (26100.9444 and .8115; 17134 has no such switch). On the corpus that format-time bit is set on every volume natively
formatted at 3.7 or later (except one whose boot sector `refsutil fixboot` rewrote) and clear on 3.4 volumes, and the
upgrades measured did not set it.

A volume upgraded from 3.4 therefore has **no** hard links even though it otherwise behaves as v3.14; the one upgraded
from 3.9 measured kept the bit.

| Capability | Upgraded v3.4→v3.14 | Native v3.14 |
|-----------|---------------------|-------------|
| Stream Snapshots | Yes | Yes |
| Case-Sensitive Directories | Yes | Yes |
| EFS Encryption | Yes | Yes |
| Extended Attributes | Yes | Yes |
| [Hard Links](hard_links.md) | **No** | Yes |

For a forensic analyst this means the *absence* of hard links on an apparently-v3.14 volume is not proof they were
never used — it may be a volume upgraded from 3.4, where the feature was never available. (Whether POSIX
unlink and rename depend on the format was not read in the driver.)

## Cross-references

- [Version Detection](version_detection.md) — the procedure that uses these tables to classify a volume's
  version and upgrade state
- [Checkpoint (CHKP)](../structures/chkp.md) — the flag word (CHKP+0x78) whose evolution this page tracks
- [VBR](../structures/vbr.md) — the version field (0x28) and the format-time fields an upgrade keeps
- [Schema Table](../structures/schema_table.md) — the self-describing schema registry whose entry set this
  page version-gates
- [Page References](../structures/page_references.md) — the structure whose size changed at v3.10 (the
  checkpoint's root references, 104 → 48 bytes) and again with SHA-256 (72 bytes)
- [Checksum Architecture](checksum_architecture.md) — the checksum algorithms, the selector at VBR 0x2A,
  and what the drivers check
- [Object Table](../structures/object_table.md) — where the version-gated heat engine table (OID 0x30)
  lives
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — 116 bytes on v3.4, 124 bytes from v3.7, its +0x50
  field changing meaning at v3.10
- [Hard Links](hard_links.md) — a capability gated on the boot-sector flags' bit 0x20, which an upgrade does not set
- [Driver builds analysed](../methodology/driver_builds.md) — the `refs.sys` builds read, and what changed from one to the next

## Evidence

- **The VBR fields** — version (0x28), checksum selector (0x2A) and volume flags (0x2C) — are confirmed on disk across
  the version corpus and in the driver.
- **The CHKP flag composites** (0x002 / 0x082 / 0x682 / 0x602 / 0x2682) and the native-format-marker behaviour are
  measured on disk and corroborated by the checkpoint code path.
- **The schema version-gating matrix** and the per-version entry counts are measured on disk: the v3.4 = 27 / v3.7 =
  30 / v3.9 = 31 / v3.10 = 30 / v3.14 = 29 / Insider = 30 counts include the legacy 0x004 / 0x006 attribute schemas
  (these counts are format-deterministic, but the v3.7/v3.9/v3.10 figures each rest on only 1–2 images).
- **The heat engine table** (OID 0x30) as a v3.10+ marker is measured on disk (present on all 112 corpus volumes of
  3.10 and later, absent on the 12 of 3.4–3.9) and read in the driver.
- **The version-specific driver subsystems** named here: `CmsVolumeHeatEngine` and `CmsRollbackProtection` are in the
  26100 and Insider drivers and not in 17134; `CmsVolumeAttestation` is in the Insider driver only.
- **The upgrade**: the virtual-clock advance (+41 checkpoints on one measured upgrade, +35 on the other) and the union
  schema set are measured on disk.
- **The root offsets**: on the 12 corpus volumes formatted at 3.4, 3.7 or 3.9 (direct mode), all 156 root references
  read through the 13 offsets verify against their root pages; flag 0x0200 is set on the 206 checkpoint copies of
  volumes at 3.11 or later and on none of the 28 copies of 3.4–3.10 volumes.

See [how this was verified](../methodology.md) to trace these to the exact images and measurements
in `analysis/`.
