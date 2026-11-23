# Integrity Streams

An *integrity stream* is a per-file, opt-in feature that protects a file's **data** with per-block
checksums, so the driver can detect — and, on a mirror or parity [storage space](redundancy.md), repair —
silent corruption or out-of-band tampering of file content.

An analyst needs to know *which* files were checksum-protected and *where* on disk that is recorded. A file is
protected when a **single bit**, `FILE_ATTRIBUTE_INTEGRITY_STREAM` (0x8000), is set in its Win32 attribute word; the
checksums themselves are kept in a per-block checksum store.

This page explains the mechanism, the per-file marker to test, and two places that look like per-file integrity records
but hold *no* per-file integrity signal.

## Per-file opt-in, not per-volume

Integrity is a per-object state, never a volume-wide switch. A file becomes an integrity stream either through
the format-time setting (`format /fs:ReFS /i enable`, i.e. `-SetIntegrityStreams 1`, which new files then inherit),
per object (`Set-FileIntegrity`), or by inheriting the setting from its parent directory at create time.

Once a file is marked, the driver checksums its data clusters (not every run carries checksums on the volumes
measured: see below). On read, a mismatch makes the driver read every copy the storage reports (at most 3: the
copies of a mirrored space, not a second ReFS copy of the data) and check each one; when one verifies, the driver has
the device rewrite the bad copies from it and returns the good data, and when none does the read fails, except on a stream whose table entry carries a flag the reading did not
trace (bit 4 of entry byte +0x0F; 26100.9444).

Because the setting is inherited at create time rather than applied dynamically, the flag is a per-file
*historical* fact, not a live volume property. Disabling a directory's integrity does **not** clear the
flag on files already created underneath it, so the only reliable way to know a file's status is to read
that file's own attribute word — never infer it from the directory or the volume.

## The per-file marker

The on-disk marker is established by the driver function `RefsSetIntegrity`, which sets or clears
**bit 15 (0x8000) at `SCB+0x98`** in the stream control block. That bit is then reflected into the file's
Win32 attribute word at **`$SI+0x20`** as `FILE_ATTRIBUTE_INTEGRITY_STREAM` (0x8000). The attribute bit in
[`$STANDARD_INFORMATION`](../attributes/STANDARD_INFORMATION.md) is the per-file signal to test that a given file is
an integrity stream (the file's `$DATA` stream flags carry an integrity bit too, below):

```text
RefsSetIntegrity ──sets──▶ SCB+0x98 bit15 (0x8000)
                              │ reflected to
                              ▼
                 $SI+0x20 file_attrs |= 0x8000   ← THE marker
                 (FILE_ATTRIBUTE_INTEGRITY_STREAM)
```

So the test for whether a file was checksum-protected is `$SI+0x20 & 0x8000`. A file enabled
this way carries the bit alongside whatever other Win32 attributes it has — an integrity-marked test file,
for example, reads `0x8020` (integrity 0x8000 ORed with archive 0x20).

## Where the checksum machinery lives

Two distinct stores hold the actual checksum data, and neither is the per-file roster:

- **Per-cluster data checksums.** With integrity enabled, the driver checksums each data cluster with the
  volume's data-checksum algorithm — **CRC32-C** (Castagnoli, poly `0x82f63b78`, 4 bytes) on 4 KiB-cluster CRC64
  volumes, CRC64 (8 bytes) on 64 KiB-cluster volumes, SHA-256 (32 bytes) on SHA-256 volumes.
  - On a 4 KiB-cluster CRC64 volume (v3.4 and v3.14 measured) the checksum is stored **inline in the file's own
    extent map**: an extent row whose size declares it (24 + 4 × run; flags bit `0x80` set) is followed by **one
    4-byte CRC32-C per cluster of its run**, and the next row starts at the 8-byte boundary (a single-cluster row
    therefore occupies 32 bytes). `forefst extract` recomputes and verifies each one.
  - **Not every run carries them**: beside the checksummed rows (flags 0xD0) an integrity file's map can hold rows
    flagged 0x40, 24 bytes long, with no CRC slot. On the two integrity volumes measured, most integrity files hold
    such a run (more than nine in ten on one, about four in five on the other), typically the first cluster
    checksummed and the rest of the file in one run without CRCs (why the driver leaves those runs unchecksummed
    was not read). `extract` says how many of a file's clusters are in rows without a CRC-32C and are not verified.
  - An inline `$DATA` value's stream summary reflects it in two u16 fields: `val+0x38`, the table's checksum type,
    tracks the *volume's* configuration (2 on CRC64 and checksum-none volumes, 4 on SHA-256 volumes) rather than
    identifying individual files, and `val+0x3A` is the stream's integrity algorithm, 0 without integrity; a file
    whose `$DATA` is in extents records its integrity in its table descriptor's +0x16 instead — see
    [`$DATA`](../attributes/DATA.md#checksum-fields).
- **Integrity State Table (root #11, schema 0xe080).** A **volume-level** B+-tree (`CmsIntegrityState`) that
  tracks integrity-stream coverage by LCN range, reusing the same row format as the
  [allocator tables](../structures/allocators.md). It is present on **every** volume regardless of whether
  any file uses integrity streams, and on baseline images carries exactly **one row** spanning the whole
  volume. It is *not* a per-file lookup — per-file status lives in the file's own record (the 0x8000 attribute
  bit).

  See [Integrity State Table](../structures/integrity_state.md) for the byte layout.

The per-cluster data checksums above live **inline in the file's extent map**, separate from the metadata
Merkle tree. The [page-reference](../structures/page_references.md) checksum-type
byte (cktype 0x01/0x02/0x04) governs **metadata** verification and is entirely separate from whether a file's
*data* is an integrity stream.

See [Checksum Architecture](checksum_architecture.md) for the metadata
checksums.

## Two places that hold no per-file integrity signal

Both of the structures below look like plausible per-file integrity rosters and are not.

- **`$SI+0x24` (internal flags) carries no integrity bit.** Its bit 0 (0x01) is the
  **delete-disposition / EFS transient state**, derived from `FCB+0x08` bit 27 (set in the driver's
  `DeleteDirectoryOnDisk` path). It is *not* an integrity flag. The proof that the integrity bit cannot appear in
  this field is structural — `RefsComputeStandardInformationInternalFromFcb` builds `$SI+0x24` from `FCB+0x08` bits only and never reads
  `SCB+0x98`, where the integrity bit lives. On disk, an integrity-enabled volume with thousands of integrity
  files shows that bit set on **none** of them. Use `$SI+0x20` bit 0x8000, never `$SI+0x24`.
- **The Integrity State Table is not a per-file roster.** Root #11 is volume-level — on nearly every volume
  measured the same single whole-volume row whether or not any file is an integrity stream, and across CRC64
  versus SHA-256 metadata configurations (two large v3.4 volumes carry three rows). Reading it expecting a list of
  protected files yields nothing.

## Forensic consequences

The integrity marker gives the analyst two things:

- It shows, for each file, whether the file was checksum-protected: a single bit, read per file.
- Because an integrity stream carries a per-cluster CRC32-C over the clusters its checksummed rows cover, a
  stored-vs-recomputed mismatch on an integrity-marked file is strong evidence the data was altered out-of-band: an
  offline edit, bit-rot, or a write that bypassed the driver.

On a *non*-integrity file there is no per-block data checksum at all, so content tampering leaves no equivalent
on-disk trace — the presence of the 0x8000 marker is what makes after-the-fact tamper detection
possible.

A match proves less: CRC-32C, CRC64 and SHA-256 take no key, so whoever edits the data offline can recompute the
stored values, and a run without a CRC is not checked at all.

## Version and state differences

The `FILE_ATTRIBUTE_INTEGRITY_STREAM` (0x8000) marker and the Integrity State Table (root #11) are present
across all studied versions, from Win10 v3.4 through Insider. The marker test is therefore version-agnostic.

By contrast, the `$SI+0x24` internal-flags word — the field one might wrongly key an integrity test on — is
**zero on v3.4 through v3.10** and only becomes populated on **v3.14+**, so a test built on it would produce
no signal at all on older volumes regardless of correctness. The `$SI+0x20` bit 0x8000 marker works on every
version.

Finally, whether a file is an integrity stream is a **per-file** choice (the 0x8000 bit), but the **algorithm**
its data checksums use is **volume-wide** and tracks the volume's checksum type and cluster size — CRC32-C
(4 bytes) on 4 KiB-cluster volumes, CRC64 (8 bytes) on 64 KiB, SHA-256 (32 bytes) on SHA-256 volumes — the same
configuration set at format (VBR offset 0x2A records it where the volume flags carry 0x40, the only case in which
refs.sys reads it; see [Checksum Architecture](checksum_architecture.md)). The data checksums are a **separate store** (inline in the
file's extent map) from the metadata page-reference checksums, not a separate algorithm independent of the
volume's choice.

## Reading the marker with the tools

The integrity marker is read directly from the `$SI` attribute word surfaced by the file-enumeration path of
`forefst.py` / `refsanalysis.py`: `files` names it `IntegrityStream` in `FileAttributes` (bit `0x8000` of
`FileAttributesHex`). Do not confuse this with
`forefst.py integrity --checksums`, which exercises the page-reference *metadata* checksum machinery
(CRC64 or SHA-256, not the per-file data CRC32-C) and verifies root-table metadata — a separate mechanism from
per-file integrity streams. The per-file data CRCs are verified by `extract`.

## Cross-references

- [Driver Evolution](driver_evolution.md) — enabling integrity on an existing stream leaves it inline; a file
  created under integrity starts in extents

- [Integrity State Table](../structures/integrity_state.md) — root #11 byte layout, the volume-level tracker (not a per-file roster)
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the `$SI+0x20` attribute word holding the 0x8000 marker, and the corrected `$SI+0x24` internal flags that do *not*
- [$DATA](../attributes/DATA.md) — the stream summary whose `val+0x38` flags carry the checksum-type / integrity selector
- [Checksum Architecture](checksum_architecture.md) — the metadata CRC64 / SHA-256 page references, distinct from per-file data CRC32-C
- [Page References](../structures/page_references.md) — the Merkle-tree checksum carriers and the cktype byte
- [Allocators](../structures/allocators.md) — the row format the Integrity State Table reuses
- [Redundancy](redundancy.md) — the mirror / parity self-healing that integrity checksums enable

## Evidence

The marker mechanism is confirmed in the driver: `RefsSetIntegrity` sets/clears `SCB+0x98` bit 0x8000
and reflects it to `$SI+0x20`, and `RefsComputeStandardInformationInternalFromFcb` builds `$SI+0x24` from
`FCB+0x08` bits only — the static proof that integrity can never appear in the internal-flags field. The
`CmsIntegrityState` class backs the Integrity State Table: `Initialize` reads root #11 at mount,
`SetClearIntegrityState` sets/clears a stream's state, and `GetIntegrityStateTable` / `GetRangeBitmap` read
the per-range checksum bitmap. On the raw-disk corpus, the 0x8000 attribute bit matched `Get-FileIntegrity` on
every file of four v3.14 integrity images, while the `$SI+0x24` bit 0 was set on none of them, and the Integrity
State Table's single whole-volume row was invariant across checksum configurations.

The per-cluster **data** checksum algorithm is CRC32-C (Castagnoli, poly `0x82f63b78`), confirmed in the
driver: the `crc32c_4096` kernels reached via `ComputeOneChecksum` (which takes the 4096-byte path only
for a one-cluster span), and recomputed on the raw-disk corpus, with a cross-algorithm control ruling out plain
CRC-32 and CRC64.

The counts behind the text:

- the inline CRCs: 391 of 391 elements match on two v3.14 volumes (249 and 142), and 3,929 of 3,929 clusters on a
  v3.4 volume (257 files verify the same way on a second v3.4 volume); no inline element on the SHA-256, 64 KiB
  and integrity-off control volumes;
- the runs without CRC slots: 204 of 209 integrity files (69,960 clusters) and 214 of 259 (25,338 clusters) on the
  two integrity volumes measured;
- the `$SI+0x24` check is on a volume with 264 integrity files (and 38 integrity directories), the bit set on 0;
- where a file records its integrity, over every file of the 124 corpus volumes: a file whose data is in extents
  records it in its table's descriptor (+0x16 = 1 on 4,034 of the 4,037 files with the integrity attribute), a file
  whose data is inline in its `$DATA` value (+0x3A = 1 on the other 3, and 0 on every inline file without the
  attribute);
- the Integrity State Table: one whole-volume row on 83 of 85 volumes, three rows on two large v3.4 volumes.

See [how this was verified](../methodology.md) for the method.

<!-- findings: CT_DRNT_004, CT_INTS_001, CT_INTS_002, GN_PREF_002, MD_DATA_RA_010, MD_DATA_RA_013,
               MD_INTG_RA_001, MD_SI_RA_006 -->
