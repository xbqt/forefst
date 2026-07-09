# Integrity Streams

An *integrity stream* is a per-file, opt-in feature that protects a file's **data** with per-block
checksums, so the driver can detect — and, on a mirror or parity [storage space](redundancy.md), repair —
silent corruption or out-of-band tampering of file content. For an analyst the two questions that matter
are: *which* files were checksum-protected, and *where* on disk that fact is recorded. Both reduce to a
**single bit** — `FILE_ATTRIBUTE_INTEGRITY_STREAM` (0x8000) in the file's Win32 attribute word — plus a
per-block checksum store. This page explains the mechanism, the one authoritative on-disk marker, and the
several places an analyst is tempted to look that hold *no* per-file integrity signal.

## Per-file opt-in, not per-volume

Integrity is enabled per object, never volume-wide. A file becomes an integrity stream either at format
time (`format /fs:ReFS /i enable`, i.e. `-SetIntegrityStreams 1`), per object (`Set-FileIntegrity`), or by
inheriting the setting from its parent directory at create time. Once a file is marked, the driver keeps a
checksum for every data block; on read, a stored-vs-recomputed mismatch is surfaced as corruption and is
self-healed wherever a redundant copy exists.

Because the setting is inherited at create time rather than applied dynamically, the flag is a per-file
*historical* fact, not a live volume property. Disabling a directory's integrity does **not** clear the
flag on files already created underneath it, so the only reliable way to know a file's status is to read
that file's own attribute word — never infer it from the directory or the volume.

## The one authoritative marker

The on-disk marker is established by the driver function `RefsSetIntegrity`, which sets or clears
**bit 15 (0x8000) at `SCB+0x98`** in the stream control block. That bit is then reflected into the file's
Win32 attribute word at **`$SI+0x20`** as `FILE_ATTRIBUTE_INTEGRITY_STREAM` (0x8000). The attribute bit in
[`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) is the *only* authoritative on-disk signal
that a given file is an integrity stream:

```
RefsSetIntegrity ──sets──▶ SCB+0x98 bit15 (0x8000)
                              │ reflected to
                              ▼
                 $SI+0x20 file_attrs |= 0x8000   ← THE marker
                 (FILE_ATTRIBUTE_INTEGRITY_STREAM)
```

The decisive test for "was this file checksum-protected?" is therefore `$SI+0x20 & 0x8000`. A file enabled
this way carries the bit alongside whatever other Win32 attributes it has — an integrity-marked test file,
for example, reads `0x8020` (integrity 0x8000 ORed with archive 0x20).

## Where the checksum machinery lives

Two distinct stores hold the actual checksum data, and neither is the per-file roster:

- **Per-block data checksums.** With integrity enabled, the driver computes **CRC32 per data block** — note
  CRC32, *not* the CRC64 used for metadata page references. The selected checksum type is also reflected in
  the file's `$DATA` stream summary: the **stream-flags `u32` at `val+0x38`** uses its low byte to select the
  algorithm (0x02 = CRC, 0x04 = SHA-256), with **bit 0x10000 = integrity**. This selector tracks the
  *volume's* checksum configuration (0x02 on None/CRC64 volumes, 0x04 on SHA-256 volumes), so it follows the
  format choice rather than identifying individual files — see [`$DATA`](../attributes/DATA.md) for the
  stream-summary layout.
- **Integrity State Table (root #11, schema 0xe080).** A **volume-level** B+-tree (`CmsIntegrityState`) that
  tracks integrity-stream coverage by LCN range, reusing the same row format as the
  [allocator tables](../structures/allocators.md). It is present on **every** volume regardless of whether
  any file uses integrity streams, and on baseline images carries exactly **one row** spanning the whole
  volume. See [Integrity State Table](../structures/integrity_state.md) for the byte layout. It is *not* a
  per-file lookup — per-file status lives only in the 0x8000 attribute bit.

The block checksums themselves are reached through the ordinary
[page-reference](../structures/page_references.md) / Merkle machinery, but note the orthogonality: the
page-reference checksum-type byte (cktype 0x01/0x02/0x04) governs **metadata** verification and is entirely
separate from whether a file's *data* is an integrity stream. See
[Checksum Architecture](checksum_architecture.md) for the metadata side of the same coin.

## Two places that hold no per-file integrity signal

Both of the structures below look like plausible per-file integrity rosters and are not.

- **`$SI+0x24` (internal flags) carries no integrity bit.** Its bit 0 (0x01) is the
  **delete-disposition / EFS transient state**, derived from `FCB+0x08` bit 27 (set in the driver's
  `DeleteDirectoryOnDisk` path). It is *not* an integrity flag. The proof that the integrity bit cannot appear in this field is structural —
  `RefsComputeStandardInformationInternalFromFcb` builds `$SI+0x24` from `FCB+0x08` bits only and never reads
  `SCB+0x98`, where the integrity bit lives. On disk, an integrity-enabled volume with ~6,000 integrity
  files shows that bit set on **zero** of them. Use `$SI+0x20` bit 0x8000, never `$SI+0x24`.
- **The Integrity State Table is not a per-file roster.** Root #11 is volume-level and invariant — the same
  single whole-volume row whether or not any file is an integrity stream, and across CRC64 versus SHA-256
  metadata configurations. Reading it expecting a list of protected files yields nothing.

## Forensic consequences

The integrity marker hands the analyst two distinct capabilities. First, it is the authoritative
per-file answer to "was this checksum-protected?" — a single bit, read per file. Second, because an
integrity stream carries a per-block CRC32 over its content, a stored-vs-recomputed mismatch on an
integrity-marked file is strong evidence the data was altered out-of-band: an offline edit, bit-rot, or a
write that bypassed the driver. On a *non*-integrity file there is no per-block data checksum at all, so
content tampering leaves no equivalent on-disk trace — the presence of the 0x8000 marker is what makes
after-the-fact tamper detection possible in the first place.

## Version and state differences

The `FILE_ATTRIBUTE_INTEGRITY_STREAM` (0x8000) marker and the Integrity State Table (root #11) are present
across all studied versions, from Win10 v3.4 through Insider. The marker test is therefore version-agnostic.

By contrast, the `$SI+0x24` internal-flags word — the field one might wrongly key an integrity test on — is
**zero on v3.4 through v3.10** and only becomes populated on **v3.14+**, so a test built on it would produce
no signal at all on older volumes regardless of correctness. The `$SI+0x20` bit 0x8000 marker works on every
version.

Finally, the per-file data-block integrity checksum is **CRC32** and is independent of the volume *metadata*
checksum type (None / CRC64 / SHA-256). The metadata type is fixed at format and reported through VBR offset
0x2A and the checkpoint flags (see [Checksum Architecture](checksum_architecture.md)); the per-file data CRC32
is a separate mechanism layered on top.

## Reading the marker with the tools

The integrity marker is read directly from the `$SI` attribute word surfaced by the file-enumeration path of
`forefst.py` / `refsanalysis.py` — test `file_attrs & 0x8000`. Do not confuse this with
`forefst.py integrity --checksums`, which exercises the page-reference *metadata* checksum machinery
(CRC64, not the per-file data CRC32) and verifies root-table metadata — a separate mechanism from per-file
integrity streams.

## Cross-references

- [Integrity State Table](../structures/integrity_state.md) — root #11 byte layout, the volume-level tracker (not a per-file roster)
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the `$SI+0x20` attribute word holding the 0x8000 marker, and the corrected `$SI+0x24` internal flags that do *not*
- [$DATA](../attributes/DATA.md) — the stream summary whose `val+0x38` flags carry the checksum-type / integrity selector
- [Checksum Architecture](checksum_architecture.md) — the metadata CRC64 / SHA-256 page references, distinct from per-file data CRC32
- [Page References](../structures/page_references.md) — the Merkle-tree checksum carriers and the cktype byte
- [Allocators](../structures/allocators.md) — the row format the Integrity State Table reuses
- [Redundancy](redundancy.md) — the mirror / parity self-healing that integrity checksums enable

## Evidence

The marker mechanism is confirmed in the driver (E2): `RefsSetIntegrity` sets/clears `SCB+0x98` bit 0x8000
and reflects it to `$SI+0x20`, and `RefsComputeStandardInformationInternalFromFcb` builds `$SI+0x24` from
`FCB+0x08` bits only — the static proof that integrity can never appear in the internal-flags field. The
`CmsIntegrityState` class backs the Integrity State Table: `Initialize` reads root #11 at mount,
`SetClearIntegrityState` sets/clears a stream's state, and `GetIntegrityStateTable` / `GetRangeBitmap` read
the per-range checksum bitmap. On the raw-disk corpus (RD), the 0x8000 attribute bit was set on every
integrity file across the two v3.14 integrity images (the only integrity images in the corpus), while the
`$SI+0x24` bit 0 was set on none of them, and
the Integrity State Table's single whole-volume row was invariant across checksum configurations. Findings:
**MD_INTG_RA_001** (the integrity-bit marker), **CT_INTS_001** (Integrity State Table invariance), **MD_DATA_RA_010** (the
`$DATA` stream-flags selector), **GN_PREF_002** (metadata vs data checksum distinction), **CT_INTS_002** (inheritance not
cleared on disable). See [how this was verified](../methodology.md) to trace these to the exact images and
measurements in `analysis/`.
