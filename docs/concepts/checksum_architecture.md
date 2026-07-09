# Checksum Architecture

ReFS protects its metadata with a Merkle-tree variant: every B+-tree parent stores a checksum of each
child page, so corruption is caught the moment the child is read by recomputing the checksum and
comparing it to the value the parent recorded. For a forensic tool this has two consequences. First, a
checksum you can recompute is a way to *prove* a metadata page is the original on-disk content and not a
tampered or torn write. Second — and this is the trap — the checksums are not always *enforced*: on
older volumes they are written but never checked, so the same byte that the driver would reject on a
v3.14 volume mounts silently on a v3.4 one. A verifier has to know both the algorithm and whether the
volume actually validates it.

## The Merkle tree, level by level

The integrity model spans four levels, from the volume root down to individual metadata pages. Each
level uses a different algorithm suited to its role, and the parent of each level is what stores the
child's checksum:

```
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
| [SUPB](../structures/page_header.md) | self-checksum (`LcnWithChecksum` @+0xD0): cluster-size-dependent | in the SUPB itself | Superblock integrity — verified at mount + self-healed |
| [CHKP](../structures/chkp.md) | self-checksum (`LcnWithChecksum`): same rule | in the CHKP itself | Checkpoint self-integrity; this is the Merkle root — verified at mount |
| B+-tree pages | CRC64 (custom poly) or SHA-256 | in the **parent's** page reference | All metadata pages below the checkpoint |

The [checkpoint (CHKP)](../structures/chkp.md) is the root of the tree, and that is what makes the SUPB
and CHKP special. Below the checkpoint, every page's checksum lives in its *parent*, so verifying a
child only requires already trusting the parent — the trust chains all the way up. But the checkpoint
has no parent to hold its checksum, so it (and the superblock above it) must carry its **own**
checksum instead: a `LcnWithChecksum` self-descriptor. The cktype byte at descriptor+0x22 selects the
algorithm, and that algorithm is **cluster-size-dependent** — CRC32-C 4-byte on 4 KiB-cluster volumes,
CRC64 8-byte on 64 KiB-cluster volumes, SHA-256 32-byte on SHA-256 volumes — computed over **exactly one
cluster** with the descriptor zeroed first. `ComputeOrVerifySelfChecksumBlock` does the zero-and-compute,
and the result is verified at mount by `ValidateSuperBlock` and `ChooseCheckpointRecord`. Note that this
self-checksum selector is *separate* from the page-reference data checksum below it: a 4 KiB-cluster
CRC64 volume uses CRC32-C for its SUPB/CHKP self-descriptor but CRC64 for its page references.

## The page reference — the integrity building block

Every B+-tree parent stores a [page reference](../structures/page_references.md) for each child. This is
the single structure that ties location to integrity: it carries both the child's address (four VLCN
slots) and a checksum of the child page's data. The same structure does the
[virtual-to-physical addressing](virtual_addressing.md) and the corruption detection, which is why a
parser that mis-sizes it gets both wrong at once.

```
+0x00  8 bytes   LCN slot 0 (first cluster)
+0x08  8 bytes   LCN slot 1
+0x10  8 bytes   LCN slot 2
+0x18  8 bytes   LCN slot 3
────── 32 bytes: location ──────
+0x20  2 bytes   Flags (0x0000)
+0x22  1 byte    Checksum type: 0x00=None, 0x01=CRC32-C, 0x02=CRC64, 0x04=SHA-256
+0x23  1 byte    Checksum data offset (0x08)
+0x24  4 bytes   Checksum data length (4=CRC32-C, 8=CRC64, 32=SHA-256)
+0x28  N bytes   Checksum value
────── variable: checksum blob ──────
```

The total size of the page reference is version- and checksum-dependent, and assuming the wrong size
misaligns every field that follows it in a checkpoint root list or B+-tree node:

| Configuration | Total size | Checksum bytes | Notes |
|---------------|-----------|----------------|-------|
| v3.4 (CRC64, padded) | 104 bytes (0x68) | 8 | 56 bytes zero-padding after checksum |
| v3.10+ CRC64 (compact) | 48 bytes (0x30) | 8 | No padding |
| v3.14 SHA-256 | 72 bytes (0x48) | 32 | No padding |

The v3.10 transition eliminated the 56-byte padding, shrinking the page reference from 104 to 48 bytes —
a layout change that doubles as a [version signal](version_detection.md). The full byte layout and the
size-detection logic live on the [Page References](../structures/page_references.md) page.

## The checksum algorithms

### CRC64 (custom polynomial — NOT ECMA-182)

This is the primary metadata checksum (page-reference `cktype = 2`), applied to every B+-tree page when
CRC64 verification is active. The single most important fact for a verifier is that it is **not**
ECMA-182:

- **Polynomial `0xAD93D23594C93659` (normal) / `0x9A6C9329AC4BC9B5` (reflected)** — the driver global
  `ClMulCsCrc64`. This is a custom polynomial, not ECMA-182 (`0x42F0E1EBA9EA3693`); recomputing with the
  wrong polynomial fails on every page.
- **Reflected**, init = xorout = `0xFFFFFFFFFFFFFFFF`.
- Computed over the **full metadata page** (all of the page reference's LCN slots concatenated — 16 KiB
  on a 4 KiB-cluster volume), as one block.
- Collision sentinel: a computed result of `0xABBAFFFFABBAFFFE` is stored as `0xABBAFFFFABBAFFFF`. A
  faithful reimplementation must apply the same substitution or it will report a false mismatch on the
  one page that happens to hash to the sentinel.
- Stored in the **parent's page reference** (`rec+0x28`), never in the page itself.

The computation is the carry-less-multiply `Crc64_ClMul` instantiation of `GenerateChecksum`, and
SHA-256 pages (`cktype = 4`) are plain `sha256(full_page)`. Recomputing CRC64 this way matches every
stored page-reference checksum across the corpus with zero mismatches; the production verifier
implements it as `refs_crc64()`, exposed through `integrity --checksums` (root tables) and
`--fullchecksums`, which walks the entire metadata tree by crossing the Object-Table leaf rows whose
values embed each object root's page reference at value+0x20.

### CRC32-C (Castagnoli)

CRC32-C appears as page-reference checksum **type 0x01**, used on the **CHKP/SUPB self-descriptor** — not
as a page-reference data checksum (those use CRC64). It is also distinct from the SUPB/CHKP block-integrity
*self-checksum* described above, even though that self-checksum is CRC32-C on 4 KiB-cluster volumes:
the self-checksum's algorithm is chosen by the cluster-size rule (the cktype byte at descriptor+0x22),
whereas this type-0x01 code is the descriptor's own format tag.

- Polynomial: Castagnoli (`0x1EDC6F41`), init/xorout `0xFFFFFFFF`, reflected.
- Computed over the page-referenced structure's content.
- Stored in the page-reference descriptor (checksum-type byte = 0x01).

### SHA-256

SHA-256 is a format-time option on **Win11 24H2 (v3.14) and later** — it is not Insider-only; v3.14
non-Insider SHA-256 volumes exist in the corpus. It is declared by VBR offset 0x2A = 0x04, fills the same
Merkle-tree role as CRC64 but with a 32-byte checksum value per page reference, and therefore uses
72-byte page references instead of 48-byte. The driver delegates SHA-256 to the imported `cng.sys`/BCrypt
provider (`CmsBCrypt`) rather than computing it in-line as it does for CRC64.

### ROR1+ADD

A custom rotate-right-by-1-then-add algorithm used only for the [VBR](../structures/vbr.md) boot-sector
self-checksum at offset 0x16. It runs over the VBR content (skipping the two checksum bytes themselves)
and is validated during volume recognition by `RefsIsBootSectorOurs`; a mismatch prevents the volume
from mounting.

## Checksums outside the Merkle tree

The four-level Merkle model above is **not** the complete integrity picture. Two further checksum
families exist in parallel, neither stored in B+-tree page references, and a forensic verifier that only
implements the Merkle tree will silently skip both.

### MLog log-record checksum (XOR-fold)

Each [MLog](../structures/mlog.md) log record carries its own integrity value — an **8-byte XOR-fold**
(not a CRC) of the record body, stored in the entry header at +0x08 (= page+0x80). It is written by
`LogCoreWriteDataRecord` and verified by `LogVerifyChecksumEntryHeader` on recovery. The dword at MLog
page **+0x04 is NOT a CRC32**: it is a per-volume constant format/log-instance magic, identical for every
control page and data record in a volume and validated only by equality. Reading +0x04 as a per-record
checksum (a common mistake) finds the same value on every record; the real per-record value is the
XOR-fold at +0x80.

### Container-compression per-unit checksums (24H2)

ReFS 24H2 [volume compression](compression.md) introduces an integrity domain **outside** the metadata
Merkle tree, covering *file-data* compression units. The `_SmsContainerCompressionHeader` field at
**+0x3C** is a checksum-type selector (0 = none); when nonzero, **per-unit checksums** follow the
per-unit length array, and each decompressed unit is verified by
`VerifyContainerCompressionHeaderChecksums` against the volume checksum object at
`volume+0xdd8 + (type × 8)` before use. This reuses the volume's CRC64/SHA-256 machinery but keys it
per compression unit rather than per page.

> The full integrity surface is therefore: **Merkle tree** (VBR → SUPB → CHKP → B+-tree pages) **+ MLog
> record XOR-folds + container-compression per-unit checksums.** A complete verifier must handle all
> three.

## Verification flow at mount time

When Windows mounts a ReFS volume with active checksums, the chain unwinds from the superblock down:

1. Read the checkpoint (CHKP) from the location stored in the superblock.
2. Verify the CHKP self-descriptor (CRC32-C on 4 KiB-cluster None/CRC64 volumes, CRC64 on 64 KiB-cluster,
   SHA-256 on SHA-256 volumes).
3. For each root page reference stored in the checkpoint:
   - Read the root page from disk.
   - Compute CRC64 (or SHA-256) over the page data.
   - Compare against the checksum stored in the CHKP page reference.
4. On mismatch, try the duplicate (failover pair).
5. If both copies fail, the mount fails.

For tables with failover pairs — Object Table roots 0/5, Schema Table roots 3/9, Container Table roots
7/8 — single-copy corruption triggers silent recovery from the duplicate. This silent
[redundancy](redundancy.md) is a forensic subtlety: a volume can mount cleanly even though one copy of a
root is corrupt, so the absence of an error does not mean every metadata copy is intact.

## When checksums are actually enforced

Checksum verification is **not always active**, and this is the most consequential point for an analyst.
Two fields control the behaviour, and they can disagree:

| Field | Location | Meaning |
|-------|----------|---------|
| Checksum algorithm | VBR offset 0x2A | Format-time declaration: 0x00=None, 0x02=CRC64, 0x04=SHA-256 |
| CHKP flag 0x400 | CHKP offset 0x78 | Runtime activation: checksums are verified only when this bit is set |

| Volume | VBR 0x2A | CHKP 0x400 | Verification |
|--------|----------|------------|--------------|
| v3.4 (Win10) | 0x0000 | Not set | CRC64 values written but **never verified** |
| Upgraded v3.4-to-v3.14 | 0x0000 | Set | CRC64 **verified** at runtime |
| Native v3.14 (Win11 24H2) | 0x0002 | Set | CRC64 **verified** |
| v3.14 SHA-256 (Win11 24H2+) | 0x0004 | Set | SHA-256 **verified** |

On v3.4 volumes the driver instantiates `CmsChecksumNone`, whose `VerifyChecksum` method unconditionally
returns `TRUE`. CRC64 values are still computed and stored in page references, but they are never checked
on read — so a tampered metadata page on a v3.4 volume mounts without complaint, and the stored checksum
is useful to the analyst (it still detects the tamper on recompute) even though the driver ignores it.

The critical wrinkle is the upgraded volume. After upgrade to v3.14 the driver activates real
verification via the `CmsChecksum` class and sets CHKP flag 0x400 — **even though VBR 0x2A remains
0x0000**, because that field is an immutable format-time value never rewritten by the upgrade. The driver
keys runtime verification off the **CHKP flags, not VBR 0x2A**, so a tool that decides "checksums off"
purely from VBR 0x2A will be wrong on every upgraded volume. This is why [version detection](version_detection.md)
must read the CHKP flags, not just the boot sector.

## The superblock's place in the chain

The [superblock (SUPB)](../structures/page_header.md) sits between the VBR and the checkpoint but is
**outside** the Merkle tree — no parent stores a checksum of it. Instead, **each of the three SUPB copies
carries its own cluster-size-dependent self-checksum** (`LcnWithChecksum` @SUPB+0xD0: read the cktype
byte at descriptor+0x22 → CRC32-C/4B on 4 KiB-cluster, CRC64/8B on 64 KiB, SHA-256/32B on SHA-256
volumes), and it **is** validated at mount by `ValidateSuperBlock` → `ComputeOrVerifySelfChecksumBlock`.
The authoritative copy is the one with the highest virtual clock (SUPB+0x68) among the copies that pass
validation — the primary at LCN 0x1E is not privileged, so a corrupt primary silently falls back to a
backup.

This self-checksum is also what drives the volume's **self-heal**. Corrupting a single SUPB byte and
mounting on Win11 causes the driver to mount the volume, silently repair the byte, and bump the
checkpoint clock: the modified copy fails its self-checksum, is dropped, and the surviving winner is
memcpy'd over it and re-checksummed. The repair happens *precisely because* the self-checksum caught the
corruption — on a 4 KiB-cluster volume the digest that caught it is CRC32-C, not CRC64 — and it is
enforced, not advisory. The forensic consequence is that mounting a corrupted ReFS volume read-write can
**overwrite the evidence of corruption**; see [Redundancy](redundancy.md) for the full self-heal
mechanism and why imaging must precede any mount.

## Cross-references

- [VBR](../structures/vbr.md) — the ROR1+ADD self-checksum (0x16) and the checksum-algorithm selector (0x2A)
- [Checkpoint (CHKP)](../structures/chkp.md) — the Merkle root: self-descriptor, root page references, and flag 0x400
- [Page References](../structures/page_references.md) — the location+checksum building block, full layout and the 104/48/72-byte size variants
- [Version Detection](version_detection.md) — why checksum activation must be read from CHKP flags, not VBR 0x2A
- [Copy-on-Write](copy_on_write.md) — CoW rewrites a child, so its checksum must be recomputed and propagated up the parent chain
- [Redundancy](redundancy.md) — failover pairs, clock-based copy selection, and the SUPB/CHKP self-heal
- [MLog](../structures/mlog.md) — the per-record XOR-fold checksum (entry+0x08) outside the Merkle tree
- [Compression](compression.md) — the 24H2 container-compression per-unit checksums, a parallel integrity domain

## Evidence

The CRC64 page-checksum logic is the `Crc64_ClMul` instantiation of `CmsChecksumBase::GenerateChecksum`
(Win11 v3.14 driver). It iterates the page in stride-sized blocks, calling `ClMulCrcBase<ClMulCrc64>::Compute`
per block and applying the `0xABBAFFFFABBAFFFE → 0xABBAFFFFABBAFFFF` collision sentinel. The polynomial is
**not** ECMA-182 — it lives in the `ClMulCrc64` carry-less-multiply tables (the reflected
`0x9A6C9329AC4BC9B5` / normal `0xAD93D23594C93659` driver global `ClMulCsCrc64`), confirming **GN_PREF_002**:

```c
// GenerateChecksum  (Crc64_ClMul instantiation; Win11 v3.14 driver)
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
ECMA-182. The CRC64 page checksums and SHA-256 (`cktype 4`) are RD-confirmed by recomputation matching
every stored page-reference checksum with zero mismatches across v3.4 / v3.14 / 64 KiB / SHA-256 images,
and the full-tree walk gives full-coverage parity with zero false positives (**GN_PREF_002**). The
SUPB/CHKP self-checksum's cluster-size-dependent rule (CRC32-C/4B · CRC64/8B · SHA-256/32B), its mount-time
validation, and the self-heal are E2 from `ComputeOrVerifySelfChecksumBlock` / `ValidateSuperBlock` /
`ChooseCheckpointRecord` and RD-proven by recomputation across all cluster sizes (**FS_SUPB_001, FS_SUPB_007, FS_CHKP_005, FS_SUPB_005, FS_SUPB_RA_003**). The MLog
+0x04 field is a format magic, not a CRC. The verification class is `CmsChecksum` on v3.14, not
`CmsCrc64` — that class is v3.4-only. See [how this was verified](../methodology.md)
to trace these to the exact images and measurements in `analysis/`.
