# Version Evolution

ReFS is not one format but a family of closely related ones, and the differences between them decide
whether a parser reads a volume correctly or silently misreads it. Across six known versions — v3.4
(Windows 10 1803) through the Insider preview — Microsoft changed the size of a
[page reference](../structures/page_references.md), switched on metadata checksums, added and retired
[schemas](../structures/schema_table.md), and altered the [checkpoint](../structures/chkp.md) flag word.
A tool that assumes a single layout will be wrong on some fraction of the corpus. This page is the
canonical record of *what* changed at each transition; its companion
[Version Detection](version_detection.md) covers *how* to classify a given volume — including the crucial
distinction between a natively formatted v3.14 volume and an older one that was upgraded in place.

## Version timeline

The version is a packed `major.minor` value at [VBR](../structures/vbr.md) offset 0x28, and it tracks
the Windows release that formatted the volume:

| Version | Windows build | Release | Key change |
|---------|--------------|---------|------------|
| 3.4 | Win10 1803 | 2018 | Earliest version covered here |
| 3.7 | Win11 21H2 | 2021 | +3 attribute schemas |
| 3.9 | Win11 22H2 | 2022 | +Candidate Table |
| 3.10 | Win11 23H2 | 2023 | Compact page references, CRC64 declared, native-format marker |
| 3.14 | Win11 24H2 | 2024 | CRC64 verification active, indirect root list |
| 3.14+ | Insider preview | Pre-release | Boot volume, TPM attestation |

The version field alone does not tell the whole story. A v3.4 volume that has been mounted on Windows 11
reports version 0x030E (v3.14) in the VBR but retains v3.4-era structures internally — see
[Upgrade behavior](#upgrade-behavior) below and [Version Detection](version_detection.md) for how to tell
the two apart.

## Per-transition changes

### v3.4 to v3.7

Three new attribute schemas appear; no system schemas change. This is also where the volume-flags byte
gains the Windows 11 format marker.

| Addition | Details |
|----------|---------|
| Schema 0x1B0 | `$SNAPSHOT` — stream snapshot support |
| Schema 0x1C0 | `$REPARSE_POINT` (v3.7+ format) |
| Schema 0x1D0 | `$EA_INFORMATION` |
| VBR flags (0x2C) | 0x06 → 0x26 (bit 5 set: Win11 format) |

### v3.7 to v3.9

A single new system schema: the Candidate Table, which tracks dirty page ranges for the checkpoint
mechanism.

| Addition | Details |
|----------|---------|
| Schema 0xe120 | Candidate Table (dirty range tracking) |

### v3.9 to v3.10

The most consequential single transition. Three things happen together that change how every metadata
page is read: the page reference shrinks from 104 to 48 bytes, CRC64 is *declared* in the VBR, and a
native-format marker is set in the checkpoint. None of these is reversible on an existing volume.

| Change | Details |
|--------|---------|
| Schema 0xe130 | Heat Engine (`CmsVolumeHeatEngine`) — tier classification |
| OID 0x30 | Session Activity Table — mount-session forensics |
| VBR 0x48 | Extended GUID populated (all-zero on older or upgraded volumes) |
| VBR flags (0x2C) | 0x26 → 0x66 (bit 6 set: native v3.10+ format, gates checksum) |
| CHKP flag 0x0080 | Native-format marker (set only at format time) |
| VBR 0x2A | CRC64 declared (0x02) at format time |
| Page reference size | 104 bytes (0x68) → 48 bytes (0x30) — padding eliminated |
| CHKP +0x50 | Version-echo field (zero on older or upgraded volumes) |
| Removed | Legacy schemas 0xe050 and 0xe0f0 dropped |

The page-reference shrink is the change most likely to break a parser: the structure that anchors the
[checksum Merkle tree](checksum_architecture.md) has a different size before and after v3.10, and the
correct size depends on the checksum type as well as the version — see
[Page References](../structures/page_references.md). Declaring CRC64 here (0x2A = 0x02) does not yet mean
the checksums are *verified*; that happens at v3.14.

### v3.10 to v3.14

CRC64 verification becomes active, and the checkpoint can store its root list indirectly rather than
inline. Three more attribute schemas appear, including the EFS encryption stream.

| Change | Details |
|--------|---------|
| Schema 0x1E0 | `$EA` (WSL extended-attribute body) |
| Schema 0x1F0 | `$LOGGED_UTILITY_STREAM` (USN `$Max` metadata) |
| Schema 0x200 | `$LOGGED_UTILITY_STREAM` (`$EFS`) |
| CHKP flag 0x0200 | Indirect root list mode |
| CHKP flag 0x0400 | CRC64 metadata verification **activated** |
| Rollback protection | `CmsRollbackProtection` — present on v3.14 as well as Insider |
| SHA-256 option | VBR 0x2A = 0x04, page reference size 72 bytes (0x48) — available on v3.14 |
| Removed | Legacy schemas 0xe070, 0xe0e0; legacy attribute schemas 0x004, 0x006 |

Two flags distinguish v3.14 from v3.10 in the [checkpoint](../structures/chkp.md): 0x0200 selects
indirect root storage (the checkpoint holds a pointer to a separate root-list page instead of 13 inline
[page references](../structures/page_references.md) at CHKP+0x94), and 0x0400 means CRC64 is being
*enforced* on read, not merely declared. The retirement of the 0x004 and 0x006 legacy attribute schemas
is why a freshly formatted v3.14 volume has a smaller schema table than its predecessors even though it
gained new attributes.

### Insider-only features

The Insider preview is the first ReFS that can host a boot volume, and it adds TPM-bound attestation.

| Feature | Details |
|---------|---------|
| CHKP flag 0x2000 | Insider-only flag |
| Schema 0xe140 | Volume Attestation Table (`CmsVolumeAttestation`) |
| Boot volume | First ReFS version that is bootable |
| TPM attestation | `CmsVolumeAttestation` — certificate / HMAC-key material |

## CHKP flag evolution

The [checkpoint](../structures/chkp.md) flag word at CHKP+0x78 is the single most useful discriminator
between versions and between native and upgraded volumes, because flags accumulate and are never cleared.
[Version Detection](version_detection.md) keys off the composite values in this table.

| Version | Flags (hex) | Key additions |
|---------|-------------|---------------|
| v3.4 | 0x0002 | Base flag (always set) |
| v3.7–v3.9 | 0x0002 | Unchanged |
| v3.10 | 0x0082 | +native format (0x0080) |
| v3.14 native | 0x0682 | +indirect roots (0x0200), +CRC64 (0x0400) |
| v3.14 upgraded | 0x0602 | Same as native but **missing** native marker (0x0080) |
| Insider | 0x2682 | +Insider flag (0x2000) |

The decisive detail is the native-format marker (0x0080): it is set **only at format time** and never
during an in-place upgrade. That single missing bit is what separates a native v3.14 volume (0x0682) from
an upgraded one (0x0602), and it gates the capabilities listed under
[Capability differences](#capability-differences).

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

The Session Activity Table (OID 0x30) is the version-gated entry to watch in the
[Object Table](../structures/object_table.md): it is absent on v3.4–v3.9 and appears at v3.10, where it is
also synthesized during upgrade of a pre-v3.10 volume. It records per-mount-session I/O and allocation
statistics, which makes its presence both a version marker and a source of mount-session forensics.

| Version | System OIDs | Notes |
|---------|-------------|-------|
| v3.4–v3.7 | base set | No OID 0x30 |
| v3.10 | +OID 0x30 | Session Activity Table appears |
| v3.14 | full set | Includes OID 0x30 |

## Upgrade behavior

When a pre-v3.14 volume is first mounted on Windows 11, the driver performs an **irreversible** in-place
upgrade. It rewrites the version, recalculates the VBR checksum, adds the new schemas (as a union with the
old), bumps the [checkpoint](../structures/chkp.md) flags, and advances the virtual clock — but it
deliberately leaves the format-time fields alone. The result is a volume that *reports* v3.14 yet lacks
the native-format marker, and this asymmetry is what every version-detection routine exploits.

### Fields modified

| Field | Before | After |
|-------|--------|-------|
| VBR version (0x28) | 0x0304 | 0x030E |
| VBR checksum (0x16) | Old | Recalculated |
| CHKP flags | 0x002 | 0x602 |
| Schema Table | 27 entries | 29+ entries (union) |
| Virtual clock | format-time value | + transactions for the upgrade work |

### Fields unchanged (immutable format-time fields)

These are written once, at format time, and are **never** touched by an upgrade. They are the bedrock of
upgrade detection, because they preserve the original format identity even after the version field has
been rewritten.

| Field | Stays at |
|-------|----------|
| VBR checksum algorithm (0x2A) | 0x0000 (no CRC64) |
| VBR volume flags (0x2C) | 0x06 (no Win11/native bits) |
| VBR Extended GUID (0x48) | All-zero |
| Volume serial number (0x38) | Original value |

A native v3.14 volume, by contrast, has 0x2A = 0x02 (CRC64), 0x2C = 0x66, and a populated Extended GUID —
so the VBR alone distinguishes the two even before the checkpoint is read.

### Capability differences

The missing native-format marker (CHKP flag 0x0080) is not cosmetic: two capabilities are gated on it and
are therefore **unavailable** on an upgraded volume even though it otherwise behaves as v3.14.

| Capability | Upgraded v3.4→v3.14 | Native v3.14 |
|-----------|---------------------|-------------|
| Stream Snapshots | Yes | Yes |
| Case-Sensitive Directories | Yes | Yes |
| EFS Encryption | Yes | Yes |
| Extended Attributes | Yes | Yes |
| POSIX Unlink/Rename | **No** | Yes |
| [Hard Links](hard_links.md) | **No** | Yes |

POSIX unlink/rename and hard links both require the native-format marker (0x0080), which an upgrade never
sets. For a forensic analyst this means the *absence* of hard links on an apparently-v3.14 volume is not
proof they were never used — it may simply be an upgraded volume where the feature was never available.

## Cross-references

- [Version Detection](version_detection.md) — the procedure that uses these tables to classify a volume's
  version and upgrade state
- [Checkpoint (CHKP)](../structures/chkp.md) — the flag word (CHKP+0x78) whose evolution this page tracks
- [VBR](../structures/vbr.md) — the version field (0x28) and the immutable format-time fields that survive
  upgrade
- [Schema Table](../structures/schema_table.md) — the self-describing schema registry whose entry set this
  page version-gates
- [Page References](../structures/page_references.md) — the structure whose size changed at v3.10 (104 → 48
  bytes) and again with SHA-256 (72 bytes)
- [Checksum Architecture](checksum_architecture.md) — CRC64 declared at v3.10, enforced at v3.14
- [Object Table](../structures/object_table.md) — where the version-gated Session Activity Table (OID 0x30)
  lives
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the $SI layout that changes
  non-backward-compatibly at v3.14
- [Hard Links](hard_links.md) — a capability gated on the native-format marker an upgrade never sets

## Evidence

The VBR version field (0x28), checksum selector (0x2A), and volume flags (0x2C) are confirmed on disk
across the version corpus (RD) and in the driver (E2). The CHKP flag composites (0x002 / 0x082 / 0x682 /
0x602 / 0x2682) and the native-format-marker behavior are raw-disk-confirmed (RD) and corroborated by the
checkpoint code path (E2). The schema version-gating matrix and the per-version entry counts are
raw-disk-measured (RD) — the v3.4 = 27 / v3.7 = 30 / v3.9 = 31 / v3.10 = 30 / v3.14 = 29
/ Insider = 30 counts include the legacy
0x004 / 0x006 attribute schemas (these counts are format-deterministic, but the v3.7/v3.9/v3.10 figures each rest on only 1–2 images). The Session Activity Table (OID 0x30) as a v3.10+ marker is raw-disk and
static-confirmed (RD/E2). The three version-specific driver subsystems named here — `CmsVolumeHeatEngine`
(v3.10+), `CmsRollbackProtection` (v3.14+), and `CmsVolumeAttestation` (Insider) — are present in the
decompiled driver (E2). The upgrade virtual-clock advance and the union schema set are raw-disk-confirmed
(RD). See [how this was verified](../methodology.md) to trace these to the exact images and measurements
in `analysis/`.
