# Common Metadata Page Header

Every ReFS metadata page -- SUPB, CHKP, and MSB+ (B+-tree) -- begins with a common 80-byte header.

This layout is identical across every format (v3.4 through v3.14, including the volumes Insider builds wrote) and
configuration studied.

MLog records also carry a signature at offset 0x00, `"MLog"`, but their header has a different layout (see
[MLog](mlog.md)).

## Field Layout (80 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Signature (ASCII) | Page type: `"SUPB"`, `"CHKP"`, `"MSB+"`, or `"MLog"` |
| 0x04 | 4 | Page header version (u32) | Always `0x00000002` |
| 0x08 | 1 | Failed tree-update count (u8) | The volume's count of failed tree-update cycles since the last checkpoint, capped at 255; 0 on every page of the test corpus |
| 0x09 | 3 | Reserved | 0 |
| 0x0C | 4 | Volume signature (u32) | XOR of four 32-bit words of the Volume GUID (SUPB+0x50); 1 when that XOR is 0 |
| 0x10 | 8 | Checkpoint virtual clock (u64) | The volume's checkpoint clock when the page was written: the clock the checkpoint stores at +0x60, so a page of the tree a checkpoint names carries at most that checkpoint's value; on a SUPB copy, the clock when that copy was written ([below](#superblock-clocks-0x10-and-0x18)) |
| 0x18 | 8 | Tree update clock (u64) | The volume's count of tree updates since the last checkpoint when the page was written (0 after each checkpoint); a volume-wide counter, not the table's, and kept in no checkpoint field, so it does not order pages across checkpoints; on a SUPB copy, the value when that copy was written |
| 0x20 | 8 | LCN slot 0 -- self-block (u64) | First cluster of this page, as the reference that reached it addresses it ([below](#lcn-quadruple-0x20---0x38)) |
| 0x28 | 8 | LCN slot 1 (u64) | MSB+ only: second cluster (self+1) on a 16 KiB page; 0 on a 64 KiB page |
| 0x30 | 8 | LCN slot 2 (u64) | MSB+ only: third cluster (self+2) on a 16 KiB page; 0 on a 64 KiB page |
| 0x38 | 8 | LCN slot 3 (u64) | MSB+ only: fourth cluster (self+3) on a 16 KiB page; 0 on a 64 KiB page |
| 0x40 | 8 | Table OID -- high half (TableIdHigh) (u64) | MSB+ only: high 8 bytes of the 16-byte owning-table OID. **Always 0 in practice** (table OIDs are small ints). 0 for SUPB/CHKP |
| 0x48 | 8 | Table OID -- low half (TableIdLow) (u64) | MSB+ only: **the numeric table OID** the driver uses -- the well-known TableIds are **Object ID Table = 0x02, Block Refcount = 0x05**, other system tables 0x01--0x22, user objects >=0x500. 0 for SUPB/CHKP |

The two 8-byte halves at 0x40 and 0x48 together form the 16-byte owning-table OID (high+low). The driver reads and
compares only the low half at 0x48; the high half at 0x40 is the OID qualifier and is always 0 because table OIDs are
small integers.

## Page Signatures

| Signature | Structure | Role |
|-----------|-----------|------|
| `SUPB` | [Superblock](supb.md) | Fixed-location volume anchor pointing to checkpoints |
| `CHKP` | [Checkpoint](chkp.md) | Atomic commit point holding the 13 root pointers |
| `MSB+` | Minstore B+-tree page | A node of any B+-tree -- global table or per-object |
| `MLog` | [Metadata log](mlog.md) | Write-ahead transaction log (different header layout) |

## Key Fields Explained

### Volume Signature (0x0C)

Every page of the live tree carries the volume's own signature, derived from the SUPB Volume GUID (on every volume
measured). A page with another value is not this volume's.

On the corpus, such pages were:

- an earlier volume's pages, left in place after a format;
- the content of a Data Deduplication index, which stores its data in this page form with its own value here;
- rarely, a live file's never-written run or a text file.

### Superblock clocks (0x10 and 0x18)

On a SUPB copy the two clocks are those of the moment the driver wrote that copy (`FormatSuperPageHeader`): 0 on a
copy written at format and not since. The driver rewrites copies (the post-choice rewrite at mount, a volume
extension), so they are not fixed values.

### LCN Quadruple (0x20 - 0x38)

The page's own address: four 8-byte slots recording the clusters of the page **as the reference that reached it
addresses them**:

- the **virtual** LCNs for a page read through the Container Table (never the physical ones);
- the **physical** LCNs for the pages of roots 7, 8 and 12.

On every page walked the slots (NULLs dropped) equal the LCNs of the page reference that reached the page, so a page
whose slots name another address belongs to another table. The driver can compare them with the page's address
(`CmsBPlusTable::CheckPage`, read once on 26100.9444); that check runs only when a global flag is set.

For SUPB/CHKP, only slot 0 is meaningful. For MSB+ pages the slots list the page's clusters: four on a 16 KiB page
(4 KiB clusters), one on a 64 KiB page (slots 1-3 are 0).

### Table Identifier (0x40 - 0x48)

MSB+ pages only. The 16-byte owning-table OID spans 0x40-0x4F:

- the **high** half (0x40) is `TableIdHigh` and is **always 0** in practice (OIDs are small integers);
- the **low** half (0x48) is `TableIdLow` = **the numeric table OID** the driver actually reads and compares
  (`FormatPageHeaderInternal` writes it from the well-known-object id whose high half is 0).

This has direct forensic value: a page the current tree no longer references keeps its table identifier, so it still
names the table (a system table, or a directory's OID) it was part of.

## Forensic Use

- Signature scanning for `MSB+` pages across a disk image finds pages of earlier states (old CoW-discarded pages);
  check each one's volume signature first, since another volume's pages and deduplication index content use the same
  form
- The volume signature provides a quick check to confirm a page belongs to the volume under analysis
- The table identifier on orphaned MSB+ pages reveals which table they belonged to

## Cross-references

- [VBR](vbr.md) -- provides cluster size and other format parameters
- [Superblock (SUPB)](supb.md) -- contains the Volume GUID used to derive the volume signature
- [Checkpoint (CHKP)](chkp.md) -- uses this header with `"CHKP"` signature
- [Page References](page_references.md) -- encode checksums of child pages, chaining into a Merkle tree

## Evidence

The four page signatures appear as binary string literals; the full field layout is corroborated in the decompiled
driver -- `FormatPageHeaderInternal` writes the OID high/low halves at page+0x40/0x48 -- and re-measured on disk
across the corpus.

The Table OID semantics (high half always 0, low half = numeric table OID with Object ID Table = 0x02 and Block
Refcount = 0x05) were confirmed by an all-disk re-measure showing page+0x40 == 0 on every MSB+ page plus SUPB/CHKP.
The two halves together form the 16-byte high+low identifier.

The counts behind the text:

- page+0x40 = 0 on 137,444 of 137,444 MSB+ pages, all versions and cluster sizes;
- the volume signature: 65,630 of 65,630 page visits (65,406 distinct pages) of the live trees of the 124 ReFS
  volumes of the corpus carry the volume's own; 3,547 pages of 9 other signatures on 36 images were an earlier
  volume's, and the other 933 with another value were deduplication index content, a live file's never-written run
  (24) or a text file (1);
- the LCN slots equal the reaching reference's LCNs on 66,153 of 66,153 pages walked on 117 volumes (51,921 virtual,
  14,232 physical); slots 1-3 are 0 on 9,693 of 9,693 own pages of nine 64 KiB volumes.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_SUPB_RA_001, FS_SUPB_RA_004, GN_PAGE_001, GN_PAGE_002, GN_PAGE_003, GN_PAGE_004,
               GN_PAGE_005, GN_PAGE_006, GN_PAGE_007, GN_PAGE_RA_001, GN_PAGE_RA_002 -->
