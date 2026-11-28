# Page References

A page reference binds a child page's address to a checksum of that child's contents.

Every B+-tree parent stores a page reference for each child, chaining the whole metadata tree into a Merkle tree
anchored at the [checkpoint](chkp.md).

The page reference exists in three sizes, which differ only in what follows the 0x28-byte header:

- a B+-tree node's inner rows hold 48-byte (CRC64) or 72-byte (SHA-256) references;
- a checkpoint stores its root references at the size it declares at `CHKP+0x5C`: from 3.10, 48 bytes, or 72 on a
  SHA-256 volume; 104 bytes on a volume formatted at ReFS 3.4 to 3.9.

Reading one at the wrong size misaligns every field that follows.

## 48 bytes (0x30), CRC64: every inner B+-tree row, and a checkpoint's root references from ReFS 3.10

<!-- site: hexfig "page_ref_crc64_win11refstestmftecmd" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | LCN slot 0 (u64) | First cluster |
| 0x08 | 8 | LCN slot 1 (u64) | Second cluster |
| 0x10 | 8 | LCN slot 2 (u64) | Third cluster |
| 0x18 | 8 | LCN slot 3 (u64) | Fourth cluster |
| 0x20 | 2 | Flags (u16) | 0x0000 |
| 0x22 | 1 | Checksum type (u8) | 0x02 (CRC-64/NVME — not ECMA-182) |
| 0x23 | 1 | Checksum data offset (u8) | 0x08 |
| 0x24 | 4 | Checksum data length (u32) | 8 |
| 0x28 | 8 | CRC64 checksum | Computed over the child page |

**Total**: 48 bytes (0x30).

## 72 bytes (0x48), SHA-256: the same references on a SHA-256 volume (ReFS 3.14)

<!-- site: hexfig "page_ref_sha256_wininsiderrefs8gtest2" -->

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | LCN slot 0 (u64) | First cluster |
| 0x08 | 8 | LCN slot 1 (u64) | Second cluster |
| 0x10 | 8 | LCN slot 2 (u64) | Third cluster |
| 0x18 | 8 | LCN slot 3 (u64) | Fourth cluster |
| 0x20 | 2 | Flags (u16) | 0x0000 |
| 0x22 | 1 | Checksum type (u8) | 0x04 (SHA-256) |
| 0x23 | 1 | Checksum data offset (u8) | 0x08 |
| 0x24 | 4 | Checksum data length (u32) | 32 |
| 0x28 | 32 | SHA-256 digest | Computed over child page |

**Total**: 72 bytes (0x48)

## 104 bytes (0x68): a checkpoint's root references on a volume formatted at ReFS 3.4 to 3.9

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | LCN slot 0 (u64) | First cluster of referenced page |
| 0x08 | 8 | LCN slot 1 (u64) | Second cluster |
| 0x10 | 8 | LCN slot 2 (u64) | Third cluster |
| 0x18 | 8 | LCN slot 3 (u64) | Fourth cluster |
| 0x20 | 2 | Flags (u16) | 0x0000 |
| 0x22 | 1 | Checksum type (u8) | See Checksum Type Codes below |
| 0x23 | 1 | Checksum data offset (u8) | 0x08 |
| 0x24 | 4 | Checksum data length (u32) | 8 (CRC64) |
| 0x28 | 8 | CRC64 checksum | Computed over the child page |
| 0x30 | 56 | Padding | Zero-filled |

**Total**: 104 bytes (0x68): the 48-byte reference followed by 56 zero bytes.

On every corpus volume formatted at 3.4, 3.7 or 3.9, every root reference in the checkpoint in use is CRC64 with
its digest at 0x28 matching the root page, and bytes 0x30–0x67 are zero.

The Windows 10 driver (build 17134) writes the 104-byte size as a constant and copies each root reference at that
size, whatever the digest length; no driver of ReFS 3.7 or 3.9 was read. The inner B+-tree rows on these volumes are
48-byte references (above).

The same driver checks a page it reads from disk against the checksum type its reference declares: type 2 selects a
CRC64 verifier that recomputes the digest over the page and compares it.

Its `CmsChecksumNone` class, whose check always succeeds, is the type-0 entry of its *stream* checksum table
(integrity streams), not a metadata verifier. This was read in the decompiled driver and again in its instructions;
no test with a corrupted metadata page is held for that driver.

## Checksum Type Codes (offset +0x22)

| Value | Algorithm | Notes |
|-------|-----------|-------|
| 0x00 | None | No verification; no root reference of the corpus declares it |
| 0x01 | CRC32-C | The SUPB/CHKP self-descriptor on 4 KiB-cluster volumes without SHA-256; refused by the Windows 11 driver as a volume's metadata type |
| 0x02 | CRC-64/NVME (reflected poly 0x9A6C9329AC4BC9B5, not ECMA-182) | Standard metadata verification; also the SUPB/CHKP self-descriptor on 64 KiB-cluster volumes without SHA-256 |
| 0x03 | (none) | No algorithm: a volume whose checksum type is 3 gets the no-checksum objects; how a reference declaring 3 is checked was not read |
| 0x04 | SHA-256 | 32-byte digest, on SHA-256 volumes |
| 0x05 | XXH64 | In the Windows 11 driver's dispatch; on no volume measured, and not computed by the tools |

## What the checksum covers

The digest is taken over the **whole referenced page** — the cluster bytes of every valid LCN slot,
concatenated in slot order and read *after* container translation. Nothing is excluded, not even the page header.

Reproducing it is therefore a complete integrity check on a metadata page, independent of whether the mounting
driver performs one.

How many slots are in use is decided by the **cluster size**, not by the version:

| Cluster size | Slots used | Page |
|---|---|---|
| 4 KiB | 4 | 16 KiB |
| 64 KiB | 1 | 64 KiB |

An object table can hold **more than one row for the same object** — an earlier generation and a current
one — and a reader keeps the current one. Only that row is meaningful: a superseded row may point at a page
that has since been freed or reallocated, so whether its digest still matches says nothing about the volume.

Scoped that way the check is exact. Across every Object-Table page reference of the volumes measured, under both
algorithms, none skipped, the digest of the row the reader uses matches on **every one**, on every volume, with no
exception and no tolerance.

Of the remaining references, all of them superseded rows, most still match and a few do not; duplicate rows occur on
a few images.

Because an Object-Table row's page reference begins at **value+0x20**, the LCN slots sit at
value+0x20…0x38 and the checksum at **value+0x48**.

## Which size a reference has

Every reference states its own digest length at 0x24. A checkpoint's root references are spaced at the size the
[CHKP](chkp.md) declares at offset 0x5C; inner B+-tree rows follow the volume's checksum. Measured on the corpus:

| Volume | [VBR](vbr.md) 0x2A | CHKP 0x5C (root references) | Inner rows |
|--------|----------|-----------|------------|
| Formatted at 3.10 or later, CRC64 | 0x0002 | 0x30 | 48-byte (CRC64) |
| Formatted at 3.14, SHA-256 | 0x0004 | 0x48 | 72-byte (SHA-256) |
| **Upgraded to 3.14 from 3.4, 3.7 or 3.9** | **0x0000 (not read by the driver)** | **0x30** | **48-byte (CRC64)** |
| Formatted at 3.4, 3.7 or 3.9 | 0x0000 (not read by the driver) | 0x68 | 48-byte (CRC64) |

Readers most often get the upgraded volume wrong. A volume created at 3.4 and upgraded still carries `0x0000` at
VBR 0x2A (it kept its value across both upgrades in the corpus) while its checkpoint has moved to the 48-byte CRC64
reference.

The Windows 11 driver reads 0x2A only when the boot sector's flags at 0x2C carry 0x40, and uses CRC64 otherwise (17134
never reads it). The volumes formatted at 3.4 to 3.9, those upgraded from them, and a boot sector that
`refsutil fixboot` rewrote all lack 0x40.

**`CHKP 0x5C` and each reference's own 0x24 decide the size.**

See [VBR](vbr.md).

## Verification Behavior by Version

| Property | Win11 (v3.14) | Win10 (v3.4) |
|----------|---------------|-------------|
| VBR 0x2A | 0x0002 (CRC64) | 0x0000 (not read by the driver) |
| CHKP flags bit 0x400 | Set (the record carries the rollback-protection fields; refs.sys sets it on a volume of version 3.13 or later) | Not set |
| Verification class | `CmsChecksumBase` / `CmsSimpleChecksum` (a real CRC64 computation) | The CRC64 entry (`CmsCrc64`) of the metadata checksum table, chosen by the reference's type |
| CRC64 in page refs | Written and verified | Written; checked on a page read from disk *(read from the driver; no corruption test held)* |

On a volume upgraded from 3.4 or 3.9 to 3.14, VBR 0x2A stays 0x0000 and CHKP flag 0x0400 is set. Neither decides the
checksum: the Windows 11 driver uses CRC64 because the boot sector's flags lack 0x40, and the Windows 10 driver checks
each page against its reference's own type.

## Checkpoint Self-Checksum

The SUPB/CHKP **block** carries a **cluster-size-dependent self-checksum**: a `LcnWithChecksum` self-descriptor (at
SUPB+0xD0; in a CHKP, at the offset its +0x58 holds), computed over one cluster with the descriptor zeroed. The
algorithm is named by the cktype byte at descriptor+0x22:

- **CRC32-C / 4 B on 4K-cluster** volumes;
- **CRC64 / 8 B on 64K**;
- **SHA-256 / 32 B on SHA-256** volumes.

It **is verified at mount**: a copy that fails is not chosen, and the superblock's other copies are rewritten from
the one chosen ([Superblock](supb.md), [Checkpoint](chkp.md#checkpoint-selection-and-fallback)).

## Cross-references

- [VBR](vbr.md) -- the checksum selector at offset 0x2A, and when the driver reads it
- [Checkpoint (CHKP)](chkp.md) -- page reference size at CHKP+0x5C; checkpoint is Merkle root
- [Page Header](page_header.md) -- the 80-byte header precedes page reference areas in B+-tree nodes

## Evidence

The three formats, the field layout, the checksum-type codes, and the format-selection rule are confirmed in the
decompiled driver. The CRC64 is **CRC-64/NVME** (reflected poly 0x9A6C9329AC4BC9B5, check value 0xAE8B14860A799888)
— not ECMA-182.

On the Windows 10 driver a page read from disk is checked through the metadata checksum table, indexed by the
reference's type, whose CRC64 entry recomputes and compares; `CmsChecksumNone`, whose check always succeeds, is the
type-0 entry of the stream checksum table. That was read in the decompiled driver and again in its instructions; no
test with a corrupted metadata page on that driver is held. The 26100 builds verify through `CmsChecksumBase` /
`CmsSimpleChecksum`.

The 104-byte root references are measured on the corpus volumes formatted at 3.4 to 3.9 and read in the Windows 10
driver's checkpoint writer. What the digest covers — the whole page, all slots, after translation — is reproduced
from the bytes across the corpus; that reproduction is independent of the driver-code reading about when
verification happens.

The counts behind the text:

- the 104-byte root references: 156 of 156 verify, on the 12 corpus volumes formatted at 3.4 (9), 3.7 (1) and 3.9 (2);
- the Object-Table page references measured are 34,311, on 89 volumes; the digest of the row the reader uses matches
  on 33,883 of 33,883; of the remaining references (all superseded rows) 408 still match and 20 do not; duplicate rows
  occur on 4 of the 89 images.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_CHKP_004, FS_SUPB_006, FS_SUPB_RA_003, GN_PREF_002, GN_PREF_003, GN_PREF_RA_004 -->
