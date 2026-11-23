# Checksum Architecture

ReFS protects its metadata with a Merkle-tree variant: every B+-tree parent stores a checksum of each
child page, so corruption is caught the moment the child is read by recomputing the checksum and
comparing it to the value the parent recorded.

For a forensic tool this has two consequences:

- A checksum you can recompute shows that a metadata page holds what the volume recorded for it, which catches
  corruption and a torn write. It does not prove that nobody edited the page: the checksums are not keyed, and an
  editor can recompute them up the tree.
- Each reference names its own algorithm, so a verifier reads it from the reference instead of assuming it from the
  version: the references of a v3.4 volume declare CRC64 too, and the v3.4 driver checks a page it reads from disk
  against its reference.

## The Merkle tree, level by level

The integrity model spans four levels, from the volume root down to individual metadata pages. Each
level uses a different algorithm suited to its role, and the parent of each level is what stores the
child's checksum:

```text
VBR
 └─ ROR1+ADD self-checksum (offset 0x16)
 └─ SUPB
     └─ self-checksum (LcnWithChecksum @SUPB+0xD0, digest @+0x28) — cluster-size-dependent:
        CRC32-C/4B (4K) · CRC64/8B (64K) · SHA-256/32B (SHA vol) — verified at mount + self-healed
        └─ CHKP
            └─ self-checksum (LcnWithChecksum) — same cluster-size-dependent rule — verified at mount
                ├─ Root page (e.g., Container Table)
                │   └─ CRC64 (or SHA-256) stored in CHKP page reference
                │     ├─ Internal node
                │     │   └─ CRC64 stored in parent's page reference
                │     └─ Leaf node
                │         └─ CRC64 stored in parent's page reference
                └─ Root page (e.g., Object Table)
                    └─ CRC64 stored in CHKP page reference
```

| Layer | Algorithm | Stored where | Purpose |
|-------|-----------|--------------|---------|
| [VBR](../structures/vbr.md) | ROR1+ADD (custom rotate-add, offset 0x16) | in the VBR itself | Boot-sector self-check |
| [SUPB](../structures/supb.md) | self-checksum (`LcnWithChecksum` @+0xD0): cluster-size-dependent | in the SUPB itself | Superblock integrity — verified at mount + self-healed |
| [CHKP](../structures/chkp.md) | self-checksum (`LcnWithChecksum`): same rule | in the CHKP itself | Checkpoint self-integrity; this is the Merkle root — verified at mount |
| B+-tree pages | CRC64/NVME or SHA-256 | in the **parent's** page reference | All metadata pages below the checkpoint |

The [checkpoint (CHKP)](../structures/chkp.md) is the root of the tree, and that is what makes the SUPB
and CHKP special. Below the checkpoint, every page's checksum lives in its *parent*, so a child can
be verified once its parent is verified, and so on up to the checkpoint. But the checkpoint
has no parent to hold its checksum, so it (and the superblock above it) must carry its **own**
checksum instead: a `LcnWithChecksum` self-descriptor. The cktype byte at descriptor+0x22 selects the
algorithm, and that algorithm is **cluster-size-dependent** — CRC32-C 4-byte on 4 KiB-cluster volumes,
CRC64 8-byte on 64 KiB-cluster volumes, SHA-256 32-byte on SHA-256 volumes — computed over **exactly one
cluster** with the descriptor zeroed first. `ComputeOrVerifySelfChecksumBlock` does the zero-and-compute,
and the result is verified at mount by `ValidateSuperBlock` and `ValidateCheckpointRecord`. Note that this
self-checksum selector is *separate* from the page-reference data checksum below it: a 4 KiB-cluster
CRC64 volume uses CRC32-C for its SUPB/CHKP self-descriptor but CRC64 for its page references.

## The page reference: address and checksum in one structure

Every B+-tree parent stores a [page reference](../structures/page_references.md) for each child. This one
structure holds both location and integrity data: it carries both the child's address (four VLCN
slots) and a checksum of the child page's data. The same structure does the
[virtual-to-physical addressing](virtual_addressing.md) and the corruption detection, which is why a
parser that mis-sizes it gets both wrong at once.

```text
+0x00  8 bytes   LCN slot 0 (first cluster)
+0x08  8 bytes   LCN slot 1
+0x10  8 bytes   LCN slot 2
+0x18  8 bytes   LCN slot 3
────── 32 bytes: location ──────
+0x20  2 bytes   Flags (0x0000)
+0x22  1 byte    Checksum type: 0x00=None, 0x01=CRC32-C, 0x02=CRC64, 0x04=SHA-256
                 (the driver's dispatch also maps 0x05 to XXH64 -- read in 26100.8115, .9711 and Insider 29574;
                 seen on no volume measured, and not computed by the tools; 0x03 has no algorithm)
+0x23  1 byte    Checksum data offset (0x08)
+0x24  4 bytes   Checksum data length (4=CRC32-C, 8=CRC64, 32=SHA-256)
+0x28  N bytes   Checksum value
────── variable: checksum blob ──────
```

The total size of the page reference depends on where it is stored and on the checksum, and assuming the
wrong size misaligns every field that follows it in a checkpoint root list or B+-tree node:

| Configuration | Total size | Checksum bytes | Notes |
|---------------|-----------|----------------|-------|
| Checkpoint root references, volumes at v3.4, 3.7 or 3.9 | 104 bytes (0x68) | 8 | 56 bytes zero-padding after checksum |
| CRC64: inner rows on every version, checkpoint roots from v3.10 | 48 bytes (0x30) | 8 | No padding |
| v3.14 SHA-256 | 72 bytes (0x48) | 32 | No padding |

The checkpoint's root references drop the 56-byte padding from v3.10 on, shrinking from 104 to 48 bytes (a volume
upgraded to 3.14 is rewritten at 48) — a layout change that doubles as a [version signal](version_detection.md). The
inner B+-tree rows of a 3.4 volume are 48 bytes already. The full byte layout and the
size-detection logic live on the [Page References](../structures/page_references.md) page.

## The checksum algorithms

### CRC64 — this is CRC-64/NVME (Rocksoft), not ECMA-182

This is the primary metadata checksum (page-reference `cktype = 2`), applied to every B+-tree page whose
page reference declares it. The single most important fact for a verifier is that it is **not** ECMA-182:

- **Polynomial `0xAD93D23594C93659` (normal) / `0x9A6C9329AC4BC9B5` (reflected)** — the driver global
  `ClMulCsCrc64`. The polynomial is not ECMA-182's `0x42F0E1EBA9EA3693` (reflected
  `0xC96C5795D7870F42`); recomputing with the wrong polynomial fails on every page.
- **Reflected**, init = xorout = `0xFFFFFFFFFFFFFFFF`.
- Computed over the **full metadata page** (all of the page reference's LCN slots concatenated — 16 KiB
  on a 4 KiB-cluster volume), as one block.
- Collision sentinel: a computed result of `0xABBAFFFFABBAFFFE` is stored as `0xABBAFFFFABBAFFFF`. A
  faithful reimplementation must apply the same substitution or it will report a false mismatch on the
  one page that happens to hash to the sentinel.
- Stored in the **parent's page reference** (`rec+0x28`), never in the page itself.

It is a **named, standard CRC**, so it does not need a bespoke implementation: ReFS uses **CRC-64/NVME**
(also catalogued as CRC-64/Rocksoft) — polynomial `0xAD93D23594C93659` (reflected
`0x9A6C9329AC4BC9B5`), init and xorout `0xFFFFFFFFFFFFFFFF`, reflected in and out. The catalogue check
value for that CRC is `0xAE8B14860A799888`, and this reader's own implementation returns exactly that for
`"123456789"` — so any `crc64_nvme` / `crc64_rocksoft` library reproduces ReFS metadata checksums
directly.

The computation is the carry-less-multiply `Crc64_ClMul` instantiation of `GenerateChecksum`, and
SHA-256 pages (`cktype = 4`) are plain `sha256(full_page)`. Recomputing CRC64 this way matches every
stored page-reference checksum across the corpus with zero mismatches.

The tool implements it as `refs_crc64()`, exposed through:

- `integrity --checksums` — the system root tables;
- `integrity --fullchecksums` — the entire metadata tree, reached by crossing the Object-Table leaf rows whose
  values embed each object root's page reference at value+0x20.

### CRC32-C (Castagnoli)

CRC32-C is checksum **type 0x01**. It is used in two places:

- the **SUPB/CHKP self-checksum** on 4 KiB-cluster volumes that are not SHA-256: the self-descriptor's checksum-type
  byte at +0x22 reads 0x01, and the 4-byte digest covers the one cluster;
- the **per-cluster checksums of integrity-stream data** on 4 KiB-cluster CRC64 volumes (below).

It is never a volume's metadata page checksum: the driver refuses type 1 as the metadata type.

- Polynomial: Castagnoli (`0x1EDC6F41` normal, `0x82F63B78` reflected), init/xorout `0xFFFFFFFF`, reflected.

### SHA-256

SHA-256 is a format-time option. Every SHA-256 volume measured is v3.14, and they are not Insider-only: the
corpus holds SHA-256 volumes formatted by Windows 11 builds that are not Insider. It is declared by VBR offset
0x2A = 0x04 (read because those volumes' flags carry 0x40), fills the same
Merkle-tree role as CRC64 but with a 32-byte checksum value per page reference, and therefore uses
72-byte page references instead of 48-byte. The driver delegates SHA-256 to the imported `cng.sys`/BCrypt
provider (`CmsBCrypt`) rather than computing it in-line as it does for CRC64.

### ROR1+ADD

A custom rotate-right-by-1-then-add algorithm used only for the [VBR](../structures/vbr.md) boot-sector
self-checksum at offset 0x16. It runs over bytes 3 to (+0x14) − 1 of the VBR (3..511 on every volume measured),
skipping the two checksum bytes themselves, and is validated during volume recognition by `RefsIsBootSectorOurs`;
a mismatch prevents the volume from mounting.

## Checksums outside the Merkle tree

The four-level Merkle model above does **not** cover every checksum on the volume. Three further checksum
families exist in parallel, none stored in B+-tree page references, and a forensic verifier that only
implements the Merkle tree will silently skip them.

### MLog log-record checksum (XOR-fold)

Each [MLog](../structures/mlog.md) log record carries its own integrity value — an **8-byte XOR-fold**
(not a CRC) of the record body, stored in the entry header at +0x08 (= page+0x80). It is written by
`LogCoreWriteDataRecord` and verified by `LogVerifyChecksumEntryHeader` on recovery.

**The algorithm.** Zero the 8-byte field itself, then fold the log block: for each 8-byte little-endian word
of the block, XOR it into one of **four** accumulators chosen by its index modulo 4; XOR the four accumulators
together; and fold that 64-bit result down to 32 bits as `(v >> 32) ^ (v & 0xFFFFFFFF)`. The block size is the
value at page+0x0C — `0x1000` on every volume, independent of the cluster size. Where a record spans several
blocks they chain: the next block's first accumulator starts from the previous block's result rotated left by
one bit. A record is exactly one block, so in practice the chain starts at zero.

The same value guards **both** kinds of log record — the control page and the data record — distinguished by
the type field at entry header +0x30 (1 and 2 respectively; no other type occurs).

`forefst mlog --stats` recomputes it for every record and reports the verdict, so a torn or edited record is
named rather than parsed in silence. Across the image corpus — ReFS 3.4 through 3.14, 4 K and 64 K clusters —
every data record and every control copy recomputes exactly.

> **It is an integrity check, not a signature.** It catches any single altered bit — a flip at any of the
> 4,096 offsets in a record is detected — but for a one-block record the value is the XOR of all the record's 32-bit
> words, so it is blind to any reordering of those words and to any set of changes whose XOR cancels. Treat a
> verified record as undamaged, not as authenticated.

The dword at MLog page **+0x04 is NOT a CRC32**: it is a per-volume constant format/log-instance magic,
identical for every control page and data record in a volume and validated only by equality. Reading +0x04 as
a per-record checksum (a common mistake) finds the same value on every record; the real per-record value is
the XOR-fold at +0x80.

### Container-compression per-unit checksums

[Container compression](compression.md) on the 26100 builds carries an integrity domain **outside** the metadata
Merkle tree, covering a compressed container's units. The `_SmsContainerCompressionHeader` field at
**+0x3C** is a checksum-type selector (0 = none); when nonzero, **per-unit checksums** follow the
per-unit length array, and each unit is verified by `VerifyContainerCompressionHeaderChecksums` against the volume
checksum object at `volume+0xdd8 + (type × 8)` (read on 26100.9444; the function is absent from 17134). This reuses
the volume's CRC64/SHA-256 machinery but keys it per compression unit rather than per page. No volume measured holds
a compressed container.

### Integrity-stream per-cluster checksums (data files)

When a file is placed on an **integrity stream** (`fsutil`/Storage Spaces integrity, or `Set-FileIntegrity`),
ReFS checksums its *data* clusters too — separately from metadata. On a 4 KiB-cluster CRC64 volume (v3.4 and v3.14
measured) this checksum lives **inline in the file's own extent map**:

- the extent row carrying the clusters is followed by **one 4-byte CRC32-C per cluster**, and declares it in its
  row size at +0x0A (24 + 4 × run);
- the next row starts at the 8-byte boundary, so the common single-cluster row occupies 32 bytes — 24 of extent,
  4 of checksum, and 4 up to the boundary that are not part of the checksum;
- the algorithm is **CRC32-C** (Castagnoli, `0x82F63B78`) over the full 4096-byte cluster.

Not every run of an integrity file carries CRCs: most integrity files measured also hold runs whose rows (flags
0x40, row size 24) have none — typically the first cluster is checksummed and the rest of the file is one run
without. A file's CRC check covers only its checksummed clusters.

`extract` recomputes and verifies each one as it recovers the file, and flags any mismatch as corruption or
tampering. SHA-256 and 64 KiB-cluster volumes keep their data checksums out of line (a 32-byte SHA-256 cannot fit
the inline slot), so there is nothing to verify inline on those.

> So the volume has four kinds of checksum: **Merkle tree** (VBR → SUPB → CHKP → B+-tree pages) **+ MLog
> record XOR-folds + container-compression per-unit checksums + integrity-stream per-cluster CRC32-C.** A
> complete verifier must handle all four.

## Verification flow at mount time

When Windows mounts a ReFS volume, the driver checks the chain from the superblock down:

1. Read the superblock (the first copy that validates) and the two checkpoint copies it lists.
2. Verify each checkpoint copy's self-checksum (CRC32-C on 4 KiB-cluster CRC64 volumes, CRC64 on 64 KiB-cluster,
   SHA-256 on SHA-256 volumes) and record tests (`ValidateCheckpointRecord`).
3. On the 26100 builds a first pass also rejects a copy whose root 0xC, 7 or 8 fails to read or verify against the
   checkpoint's page reference (Insider 29574, 29659 and 29683: only a read error rejects; 17134 makes no root check).
4. Choose the copy with the strictly greater virtual clock (a tie keeps slot 0); if no copy passes, a second pass
   runs without the root check, and the mount fails only when that fails too.
5. Every other page is checked against its parent's page reference when it is read.

For tables with failover pairs — Object Table roots 0/5, Schema Table roots 3/9, Container Table roots
7/8 — the driver reads one copy (slot 0 first) and fails over to the other when it fails, and a writable mount
rebuilds the failed copy from the good one. Because this [redundancy](redundancy.md) works silently, a
volume can mount cleanly even though one copy of a root is corrupt, so the absence of an error does not mean every
metadata copy is intact.

## When checksums are actually enforced

Two fields look like switches for checksum verification, and neither is one:

| Field | Location | What it is |
|-------|----------|------------|
| Checksum selector | VBR offset 0x2A | The volume's checksum type (0x02 = CRC64, 0x04 = SHA-256). The Windows 11 driver reads it only when the boot sector's flags at 0x2C carry 0x40 and uses CRC64 otherwise; the Windows 10 driver does not read it |
| CHKP flag 0x400 | CHKP offset 0x78 | Set on every ReFS 3.14 volume measured, upgraded ones included, and on none formatted at 3.4 to 3.10. It marks the record's rollback-protection fields (+0x9C / +0xA0), not a checksum setting: refs.sys sets it on a volume of version 3.13 or later |

| Volume | VBR 0x2A | CHKP 0x400 | Page references measured |
|--------|----------|------------|--------------|
| Formatted at v3.4, 3.7 or 3.9 | 0x0000 (not read) | Not set | CRC64 |
| Upgraded from them to v3.14 | 0x0000 (not read) | Set | CRC64 |
| Formatted at v3.10 | 0x0002 | Not set | CRC64 |
| Native v3.14 (Win11 24H2) | 0x0002 | Set | CRC64 |
| v3.14 SHA-256 (Win11 24H2+) | 0x0004 | Set | SHA-256 |

The Windows 10 driver (build 17134) checks a page it reads from disk against the type its own page reference
declares. Its metadata checksum table holds a CRC32-C verifier at type 1 and a CRC64 verifier at type 2, and the
CRC64 one recomputes the digest over the page and compares it. `CmsChecksumNone`, whose check always returns
success, is the type-0 entry of the driver's *stream* checksum table (integrity streams), not of the metadata
table. This was read in the decompiled driver and again in its instructions. No test with a corrupted metadata
page on Windows 10 is held, and what that driver does after a mismatch has not been read.

The Windows 11 driver gives the volume the type at VBR 0x2A when the flags carry 0x40, and CRC64 otherwise; it
refuses type 1 as a volume's metadata type, and gives type 3 or a value above 5 no checksum (read on 26100.8115,
.9711 and Insider 29574).

The rule for a tool is the same on every volume: verify each page against the type and digest its own reference
carries. A tool that decides "checksums off" from VBR 0x2A = 0x0000 is wrong on every such volume measured — those
formatted at 3.4 to 3.9, those upgraded from them, and one whose boot sector `refsutil fixboot` rewrote: their
references carry CRC64. This is why
[version detection](version_detection.md) does not read the boot sector alone.

## The superblock's place in the chain

The [superblock (SUPB)](../structures/supb.md) sits between the VBR and the checkpoint but is
**outside** the Merkle tree — no parent stores a checksum of it. Instead, **each of the three SUPB copies
carries its own cluster-size-dependent self-checksum** (`LcnWithChecksum` @SUPB+0xD0: read the cktype
byte at descriptor+0x22 → CRC32-C/4B on 4 KiB-cluster, CRC64/8B on 64 KiB, SHA-256/32B on SHA-256
volumes), and it **is** validated at mount by `ValidateSuperBlock` → `ComputeOrVerifySelfChecksumBlock`.
The driver reads the copies in the order primary (LCN 0x1E), `VolSize−2`, `VolSize−3` and takes the first
that passes validation; the generation at SUPB+0x68 decides only between the two backups. A valid primary is
read whatever the backups hold, and a corrupt primary silently falls back to a backup.

This self-checksum is also what drives the volume's **self-heal**. Corrupting a single SUPB byte and
mounting on Win11 causes the driver to mount the volume, silently repair the byte, and bump the
checkpoint clock: the modified copy fails its self-checksum, is dropped, and the chosen copy is
memcpy'd over it and re-checksummed. An image taken after a Windows 10 (17134) mount of a volume whose primary
superblock had one byte flipped shows the same repair. The repair happens because the self-checksum caught the corruption (on a
4 KiB-cluster volume the digest that caught it is CRC32-C, not CRC64), and the driver acts on the result. The forensic consequence is that mounting a corrupted ReFS volume read-write can
**overwrite the evidence of corruption**; see [Redundancy](redundancy.md) for the full self-heal
mechanism and why imaging must precede any mount.

## Cross-references

- [VBR](../structures/vbr.md) — the ROR1+ADD self-checksum (0x16) and the checksum-algorithm selector (0x2A)
- [Checkpoint (CHKP)](../structures/chkp.md) — the Merkle root: self-descriptor, root page references, and flags
- [Page References](../structures/page_references.md) — the location+checksum building block, full layout and the 104/48/72-byte size variants
- [Version Detection](version_detection.md) — why the version and the checksum cannot be read from the boot sector alone
- [Copy-on-Write](copy_on_write.md) — CoW rewrites a child, so its checksum must be recomputed and propagated up the parent chain
- [Redundancy](redundancy.md) — failover pairs, clock-based copy selection, and the SUPB/CHKP self-heal
- [MLog](../structures/mlog.md) — the per-record XOR-fold checksum (entry+0x08) outside the Merkle tree
- [Compression](compression.md) — the 24H2 container-compression per-unit checksums, a parallel integrity domain

## Evidence

The CRC64 page-checksum logic is the `Crc64_ClMul` instantiation of `CmsChecksumBase::GenerateChecksum`
(Win11 driver). It iterates the page in stride-sized blocks, calling `ClMulCrcBase<ClMulCrc64>::Compute`
per block and applying the `0xABBAFFFFABBAFFFE → 0xABBAFFFFABBAFFFF` collision sentinel. The polynomial is
**not** ECMA-182 — it lives in the `ClMulCrc64` carry-less-multiply tables (the reflected
`0x9A6C9329AC4BC9B5` / normal `0xAD93D23594C93659` driver global `ClMulCsCrc64`):

```c
// GenerateChecksum  (Crc64_ClMul instantiation; Win11 driver)
// param_1 = ClMulCrcBase<ClMulCrc64> * (the CRC64 engine, NOT ECMA-182)
uVar7 = (ulonglong)*(uint *)(param_1 + 0x10);  // block stride
CVar2 = param_1[0x16];                          // collision-sentinel enable
for (lVar5 = param_2[1]; (p_Var4 != p_Var1 && (lVar5 != 0)); lVar5 = lVar5 - uVar7) {
    _Var3 = ClMulCrcBase<class_ClMulCrc64>::Compute(param_1, pvVar6, uVar7, 0);
    *p_Var4 = _Var3;
    if ((CVar2 != 0) && (_Var3 == 0xabbaffffabbafffe))   // collision sentinel
        *p_Var4 = 0xabbaffffabbaffff;
    pvVar6 = (void *)((longlong)pvVar6 + uVar7);
    p_Var4 = p_Var4 + 1;
}
```

`Compute` uses the SSE `PCLMULQDQ` carry-less multiply over the `ClMulCrc64` constants; the engine
selection alone — distinct from the `Crc32C_*` and `XXH64` siblings in the same vtable family — rules out
ECMA-182. The CRC64 page checksums and SHA-256 (`cktype 4`) are confirmed on disk by recomputation matching
every stored page-reference checksum with zero mismatches across v3.4 / v3.14 / 64 KiB / SHA-256 images,
and the full-tree walk gives full-coverage parity with zero false positives.

The SUPB/CHKP self-checksum's cluster-size-dependent rule (CRC32-C/4B · CRC64/8B · SHA-256/32B), its mount-time
validation, and the self-heal are read in the driver (`ComputeOrVerifySelfChecksumBlock` / `ValidateSuperBlock` /
`ValidateCheckpointRecord`) and proven by recomputation across all cluster sizes. The MLog +0x04 field is a format
magic, not a CRC. The verification classes are `CmsChecksumBase` / `CmsSimpleChecksum` on the 26100 builds and
`CmsCrc64` on 17134.

The counts behind the text:

- the MLog record integrity value recomputes on all 886,932 data records and all 248 control copies of the 124
  corpus volumes;
- the integrity-stream CRCs: 391 of 391 elements match in the first disk test (no other CRC variant matches), and
  3,929 of 3,929 clusters on a v3.4 volume; runs without CRCs are held by 204 of 209 and 214 of 259 integrity files
  on two volumes.

See [how this was verified](../methodology.md) for the method.

<!-- findings: FS_CHKP_005, FS_SUPB_001, FS_SUPB_005, FS_SUPB_007, FS_SUPB_RA_002, FS_SUPB_RA_003, GN_PREF_002 -->
