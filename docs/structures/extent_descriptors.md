# Extent Descriptors

Extent descriptors (type 0x40) map a file's logical cluster offsets (VCNs) to virtual LCNs (VLCNs).
A VLCN is not a physical address: it must be translated through the [Container Table](container_table.md)
to obtain the physical cluster where the data actually lives. Every extent — even a single contiguous run —
is a fixed 24-byte entry.

## Extent Entry — 24 bytes

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | Virtual LCN (VLCN) (u64) | Requires Container Table for physical translation |
| 0x08 | 4 | Flags (u32) | See Extent Flags below |
| 0x0C | 4 | File VCN (u32) | Cluster index within file |
| 0x10 | 4 | Padding (u32) | Always zero |
| 0x14 | 4 | Run length (u32) | Number of contiguous clusters |

## Extent Flags

| Value | Meaning |
|-------|---------|
| 0x180040 | Standard data-run extent (variable run_length) |
| 0x180050 | Data-run with bit 0x10 set; the 0x10 bit is **not** run cardinality (meaning unresolved, candidate integrity/checksum-stride bit) |
| 0x1c00d0 | Integrity checksum-page entry (always run_length 1; 32-byte stride: 24-byte entry + 8-byte CRC suffix) |

Run cardinality is carried explicitly by the Run length field at extent+0x14, not by the flag bits:
both 0x180040 and 0x180050 appear with single-cluster and multi-cluster runs. The exact meaning of the
0x10 bit that distinguishes 0x180050 from 0x180040 is unresolved (a candidate is an integrity/checksum-stride
bit; it correlates with the file_attrs 0x8000 flag).

The 0x1c00d0 integrity entries and the 0x180040 data runs share the same table header format, but the
integrity entries use a wider 32-byte stride (the trailing 8 bytes hold a CRC). Both kinds of entry point
at real file data.

## No single-extent "shortcut" form

There is **no** compact 16-byte single-extent form. A contiguous file uses the standard 24-byte extent
entry (one entry, `run_length` = the whole contiguous run). Non-resident files resolve via the 24-byte
stride only; sampled single-extent files content-match (24-byte VLCN@0x00 → PLCN holds the file's bytes).

This 16-byte region is the embedded $DATA sub-record header: the
bytes `02000080 80000e00 …` decode as the multi-instance marker `0x80000002` followed by the $DATA
descriptor `0x000E0080` — i.e. the "VLCN" is the descriptor, not a cluster. See the Embedded $DATA section
below.

## VCN ordering

Extents may be stored **out of order** on disk. A parser must sort by `file_VCN` before reassembling file
content — roughly half of multi-extent entries observed are unsorted.

## VLCN to PLCN translation

A VLCN must be resolved through the Container Table to reach the physical disk address:

```
physical_LCN = container_phys_start + (vlcn & (CPC - 1))
```

Where CPC (clusters per container) is read from the Container Table at `value + 0x18`, and the container
index is computed as `vlcn >> CPC.bit_length()` (shift = 15 for 4 KiB clusters, 11 for 64 KiB).

See [Container Table](container_table.md) for the full address-translation formula and the failover/checksum
details.

## Embedded extent sub-record header — 40 bytes

When $DATA (type 0x80) appears as an embedded multi-instance sub-record in a file value, the extent list is
preceded by two headers. This is the extent-bearing $DATA stream summary (marker `0x80000002`, descriptor
`0x000E0080`) — distinct from the smaller resident-SI $DATA record.

### $DATA sub-record header

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Inner header size (u32) | Typically 0x88 |
| 0x0C | 4 | Summary size (u32) | 0x200 (the resident-SI $DATA record uses 0x30) |
| 0x2C | 4 | Data offset (u32) | 0x28 |
| 0x30 | 8 | Total allocated size (u64) | -- |
| 0x38 | 8 | Stream size (u64) | Logical file size |
| 0x40 | 8 | Valid data length (u64) | -- |
| 0x48 | 8 | Disk allocated size (u64) | 0 = inline; >0 = non-resident |
| 0x50 | 8 | Version count (low 31) + sparse flag (bit 31) (u64) | low31 = stream version count (=1 for a single-version file, N for an N-version snapshotted file); bit 31 = sparse flag |

### Extent sub-record header (at inner_header_size offset)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Sub-record size (u32) | Always 0x28 |
| 0x04 | 4 | Extent area end (u32) | 0x28 + extent_count x 24 |
| 0x0C | 4 | Flags (u32) | 0xe00 = non-resident extents; 0x600 = resident/empty |
| 0x14 | 4 | Extent count (u32) | Number of 24-byte extent entries following |

Extent entries following this header use the same 24-byte format as the [Extent Entry](#extent-entry--24-bytes)
table above. Snapshot and copy-on-write $DATA reuse this identical extent format (the driver routes them
through the same allocation-lookup routine as ordinary file reads).

## Forensic notes

- Two-level translation (VCN → VLCN → PLCN) is fundamental to ReFS. A parser that treats VLCN values as
  direct physical addresses — a common mistake for NTFS-trained tools — will read wrong data.
- Sorting by `file_VCN` is mandatory before content reassembly.
- Every extent (including a single contiguous run) is a 24-byte entry; there is no 16-byte single-extent
  form. A `0x80000002` marker in this region is the embedded $DATA sub-record header, not an extent.

## Cross-references

- [Container Table](container_table.md) — VLCN-to-PLCN translation
- [Directory Entries](directory_entries.md) — non-resident file values link to type 0x40 extent rows
- [Resident Storage](../concepts/resident_storage.md) — small files are stored inline, not in extents

## Evidence

The 24-byte extent entry layout (VLCN@0x00, flags@0x08, file_VCN@0x0C, padding@0x10, run_length@0x14) is
raw-disk decoded (RD) and corroborated in the driver (E2): `CmsStream::LookupAllocation` (with
`AddAllocation` / `DeleteAllocation`) reads run+0x00 VLCN, +0x0C file_vcn, +0x14 run_length. The
VLCN→PLCN translation formula is E2-confirmed in the `CmsVolumeContainer` container subsystem and verified
on disk across the corpus.

The extent-flag meanings are raw-disk verified: 0x180040 is the standard data run, 0x1c00d0 the
integrity checksum-page entry (32-byte stride, run_length 1), and the 0x180050 vs 0x180040 distinction
(bit 0x10) is *not* run cardinality — both flags occur with single- and multi-cluster runs. Every
non-resident file resolves via the single 24-byte extent stride (raw-disk verified; sampled single-extent
files content-match); the 16-byte region at the descriptor is the embedded $DATA sub-record header.
Snapshot/CoW DATA uses the identical 24-byte extent format (E2: same
`CmsStream::LookupAllocation` routine; RD content-recovery confirmed).

Findings: **MD_DATA_RA_001** (24-byte extent entry), **MD_DATA_RA_007** (integrity-stride flags),
**MD_DATA_RA_002** (single-extent shortcut retracted), **MD_DATA_RA_009** (MI $DATA sub-record),
**MD_SNAP_RA_003** / **CT_DRNT_RA_001** (snapshot extents reuse the format), **MD_DATA_RA_011** (version-count
field). See [how this was verified](../methodology.md) to trace these to the exact images and measurements
in `analysis/`.
