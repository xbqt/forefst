# Driver transitions — what changes a file's storage, per version

Two different things get called "making a file non-resident", and they are decided by different code in
the driver. This page lists the functions that actually change a file's storage, what each one changes,
which builds have it, and the on-disk witness for it.

- **Record placement** — is the object's record embedded in its name row, or split out into its own
  type-0x40 backing record? Moves and links change this.
- **Data residency** — are the stream's bytes inline in that record, or in extents? Writes, snapshots,
  integrity and encryption change this.

Neither implies the other. See [Resident vs Non-Resident Storage](resident_storage.md) for the two axes.

## The functions

| Function | Changes | Builds | Confirmed on disk |
|---|---|---|---|
| `RefsMoveFile` | **placement only** | all | yes — controlled before/after move |
| `RefsAddLink` / `RefsRemoveLink` / `RefsSetLinkInfo` | **placement only** | all | yes — a hard-linked pair, both names inline |
| `RefsAddAllocationForResidentWrite` | **residency** — the gate itself | all | yes — inline ceiling 2,047 B corpus-wide |
| `RefsConvertToNonResident` | **residency** — inline → extents | v3.14-era only; **absent from win10 17134** | — |
| `RefsCreateStreamSnapshot` | residency (snapshot) | v3.14-era | yes — 12 small snapshotted streams |
| `RefsChangeResidentStreamIntegrity` | residency (integrity) | all | yes — controlled integrity on/off pair |
| `RefsSetEncryption` | residency (EFS) | v3.14-era | yes — 13 encrypted files, all extent-backed |
| `RefsDuplicateExtents` | residency (block clone) | v3.14-era | — |
| `RefsCascadesSetFileRemote` | residency (tiering) | v3.14-era | — |
| `RefsSetFileStrictlySequential` | residency | v3.14-era | — |
| `RefsSetAllocationInfo` / `RefsSetEndOfFileInfo` | residency | v3.14-era | not yet — hypothesis, see below |
| `RefsReplaceDataAttribute` | residency | v3.14-era | — |
| `RefsTelemetryUnsupportedADS` | none — reports the 128 KiB **named-stream** cap | win10 17134 | — |
| `RefsCheckValidResidentDataAttribute` | none — validates a resident `$DATA` | v3.14-era only | — |

The rows marked "residency" are exactly the callers of `RefsConvertToNonResident` — the complete set, taken
from every call site in the v3.14 decompilation. **No rename, move or link function is in it**: 0 of 17
(win11 26100) and 0 of 18 (win10 17134) such function bodies contain a call, a scan control-tested against
six known callers. There is no `ConvertToResident` in any build: the conversion runs one way.

## The gate

`RefsAddAllocationForResidentWrite` branches on the **volume's** format version, read from the VCB at
`+0x318`/`+0x319` and compared against `0x30b` (3.11):

```c
if (volume_format < 0x30b && 0x20000 < new_size)   // < 3.11 and > 128 KiB
    raise STATUS_FILE_SYSTEM_LIMITATION;           //   = the NAMED-STREAM cap
if (volume_format < 0x30b || new_size < 0x800)     // < 3.11, or < 2048 bytes
    stay inline;
else
    convert to extents;
```

Because the field is the volume's, a current driver mounting an older volume takes the older path — and an
upgrade changes only future writes. On a v3.4 volume upgraded to v3.14, 0 of 262 pre-existing files changed
residency.

## What is measured, and what is not

**The split mechanism is measured, not explained.** That a move or a hard link forces the record split is
established directly: on a controlled before/after move of a whole volume, 5 files changed placement and 0
changed residency. *Why* the split is required is a different claim. The usual explanation — that only the
split layout has the `value+0x08` field carrying the frozen creation-directory home — is an **inference**.
`RefsMoveFile` (win11 26100 @`1400e9500`, 277 lines) calls `MsReparentChildTable`, `RefsCreateFileId2`,
`RefsDeleteFileId2`, `RefsConvertToStandardInfoExternalId` and `RefsPersistNextFileId`; it references no
such offset, and — contrary to a summary that circulated earlier — contains no call to `RefsAddLink` or
`RefsRemoveLink` at all. The observation stands; the mechanism does not yet have a driver citation.

**One trigger is a hypothesis.** On format 3.11+ volumes, 44 of the 86 sub-2 KiB extent-backed main streams
have no identified trigger.
Their composition is suggestive rather than random — ETW `.etl` loggers, `Diagnostic.log`, browser-cache
entries, and a uniform 128-byte generator series — which is what a writer that sets allocation or
end-of-file *before* writing would leave, and both of those are in the caller list. It is recorded as a
hypothesis until a controlled test settles it.

## Cross-references

- [Resident vs Non-Resident Storage](resident_storage.md) — the two axes and the format gate
- [Driver Architecture](driver_architecture.md) — where these functions sit
- [Copy-on-Write](copy_on_write.md) and [Integrity Streams](integrity_streams.md) — two of the triggers
- [Hard Links](hard_links.md) — what the split means for a link group
- [$DATA](../attributes/DATA.md) / [$NAMED_DATA](../attributes/NAMED_DATA.md) — the descriptor forms

## Evidence

Static (E2): `refs.sys` win10 17134 (v3.4), win11 26100 and 26100.8521 (v3.14), Insider 29574 — the
caller set is taken from every call site in the v3.14 decompilation, and the absence scan was
control-tested against six known callers. Raw disk (RD): 79 distinct volumes. The controlled witnesses are
a before/after cross-directory move, a hard-linked 300-byte pair whose two names resolve to one backing,
and an integrity-streams on/off pair built from the same base volume; the snapshot and encryption
witnesses are file populations rather than controlled pairs. Findings `MD_DATA_RA_025`, `FS_MOVE_RA_002`, `FS_RESD_SA_001`,
`FS_RESD_SA_002`, `GN_VCB_SA_001`, `MD_ADS_RA_003`.
