# Common Metadata Page Header

Every ReFS metadata page -- SUPB, CHKP, and MSB+ (B+-tree) -- begins with a common 80-byte header. This layout is identical across every version (v3.4 through v3.14 and Insider) and configuration studied. MLog pages use the same `"MLog"` signature at offset 0x00 but have a different header layout (see [MLog](mlog.md)).

## Field Layout (80 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Signature (ASCII) | Page type: `"SUPB"`, `"CHKP"`, `"MSB+"`, or `"MLog"` |
| 0x04 | 4 | Page header version (u32) | Always `0x00000002` |
| 0x08 | 4 | Reserved (u32) | Always 0 |
| 0x0C | 4 | Volume signature (u32) | XOR of four 32-bit words of the Volume GUID (SUPB+0x50) |
| 0x10 | 8 | Virtual allocator clock (u64) | 0 for SUPB (immutable); increments for CHKP/MSB+ |
| 0x18 | 8 | Tree update clock (u64) | Last modification clock for this page's table |
| 0x20 | 8 | LCN slot 0 -- self-block (u64) | Primary cluster LCN of this page |
| 0x28 | 8 | LCN slot 1 (u64) | MSB+ only: second cluster (self+1) |
| 0x30 | 8 | LCN slot 2 (u64) | MSB+ only: third cluster (self+2) |
| 0x38 | 8 | LCN slot 3 (u64) | MSB+ only: fourth cluster (self+3) |
| 0x40 | 8 | Table OID -- high half (TableIdHigh) (u64) | MSB+ only: high 8 bytes of the 16-byte owning-table OID. **Always 0 in practice** (table OIDs are small ints). 0 for SUPB/CHKP |
| 0x48 | 8 | Table OID -- low half (TableIdLow) (u64) | MSB+ only: **the numeric table OID** the driver uses -- the well-known TableIds are **Object ID Table = 0x02, Block Refcount = 0x05**, other system tables 0x01--0x22, user objects >=0x500. 0 for SUPB/CHKP |

The two 8-byte halves at 0x40 and 0x48 together form the 16-byte owning-table OID (high+low). The driver reads and compares only the low half at 0x48; the high half at 0x40 is the OID qualifier and is always 0 because table OIDs are small integers.

## Page Signatures

| Signature | Structure | Role |
|-----------|-----------|------|
| `SUPB` | [Superblock](supb.md) | Fixed-location volume anchor pointing to checkpoints |
| `CHKP` | [Checkpoint](chkp.md) | Atomic commit point holding the 13 root pointers |
| `MSB+` | Minstore B+-tree page | A node of any B+-tree -- global table or per-object |
| `MLog` | [Metadata log](mlog.md) | Write-ahead transaction log (different header layout) |

## Key Fields Explained

### Volume Signature (0x0C)
Enables fast corruption detection: if a page's volume signature does not match the expected value (derived from SUPB Volume GUID), the page does not belong to this volume.

### LCN Quadruple (0x20 - 0x38)
The page's self-descriptor: four 8-byte values recording the page's own logical cluster number. The driver confirms that a page read from a given location actually belongs there -- a misdirected or stale read is caught when the self-descriptor disagrees with the fetch address.

For SUPB/CHKP, only slot 0 is meaningful. For MSB+ pages, all four slots may be used (a page spans up to 4 clusters on 4 KiB cluster volumes).

### Table Identifier (0x40 - 0x48)
MSB+ pages only. The 16-byte owning-table OID spans 0x40-0x4F: the **high** half (0x40) is `TableIdHigh` and is **always 0** in practice (OIDs are small integers); the **low** half (0x48) is `TableIdLow` = **the numeric table OID** the driver actually reads and compares (`FormatPageHeaderInternal` writes it from the well-known-object id whose high half is 0). This has direct forensic value: a CoW-discarded page keeps its table identifier, so an OID (read at 0x48) found in a page no longer referenced by the current Object Table flags it as a stale or deleted structure.

## Forensic Use

- Signature scanning for `MSB+` pages across a disk image recovers historical file-system states (old CoW-discarded pages)
- The volume signature provides a quick check to confirm a page belongs to the volume under analysis
- The table identifier on orphaned MSB+ pages reveals which table they belonged to

## Cross-references

- [VBR](vbr.md) -- provides cluster size and other format parameters
- [Superblock (SUPB)](supb.md) -- contains the Volume GUID used to derive the volume signature
- [Checkpoint (CHKP)](chkp.md) -- uses this header with `"CHKP"` signature
- [Page References](page_references.md) -- encode checksums of child pages, chaining into a Merkle tree

## Evidence

The four page signatures appear as binary string literals (E1); the full field layout is corroborated in the decompiled driver (E2) -- `FormatPageHeaderInternal` writes the OID high/low halves at page+0x40/0x48 -- and re-measured on disk across the corpus (RD). The Table OID semantics (high half always 0, low half = numeric table OID with Object ID Table = 0x02 and Block Refcount = 0x05) were confirmed by an all-disk re-measure showing page+0x40 == 0 on every MSB+ page plus SUPB/CHKP. The two halves together form the 16-byte high+low identifier. Findings: **GN_PAGE_001**--**GN_PAGE_007**, **GN_PAGE_RA_001**, **GN_PAGE_RA_002**, **FS_SUPB_RA_001**. See [how this was verified](../methodology.md) to trace these to the exact images and measurements in `analysis/`.
