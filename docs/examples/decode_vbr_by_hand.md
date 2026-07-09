# Decode a ReFS VBR by Hand

**Goal:** Read every field of a ReFS Volume Boot Record straight out of a raw hexdump -- no parser -- and derive cluster size, container size, version, and checksum mode, then confirm the by-hand values against the tool.

## Setup

Two images, both GPT-partitioned, so we can contrast a 4 KiB-cluster volume with a 64 KiB-cluster volume:

- **4 KiB:** a v3.14 4 KiB-cluster image
- **64 KiB:** a v3.14 64 KiB-cluster image

The VBR lives at sector 0 *of the ReFS partition*, not sector 0 of the disk image. Find the partition first.

## Steps

### Step 1 -- Locate the ReFS partition start

The image opens with a GPT protective MBR (partition type `0xEE`), so the real partition table is the GPT array at LBA 2. Read the second GPT entry (the "Basic data partition").

```python
import struct
with open("image.raw", "rb") as f:  # the 4 KiB v3.14 image
 f.seek(512) # LBA 1: GPT header
 hdr = f.read(512)
 part_lba = struct.unpack_from("<Q", hdr, 72)[0] # array LBA
 f.seek(part_lba * 512)
 f.seek(128, 1) # skip MSR entry, read 2nd entry
 e = f.read(128)
 first_lba = struct.unpack_from("<Q", e, 32)[0]
print(first_lba, first_lba * 512)
```

Output:

```
32768 16777216
```

Annotation: the ReFS partition starts at **LBA 32768 = byte offset 0x1000000 (16 MiB)**. Every VBR offset below is added to this base. The 64 KiB image reports the same start (`32768`), so the partition geometry is identical -- only the format parameters differ.

### Step 2 -- Hexdump the first 96 bytes of the VBR

```python
PART = 32768 * 512
with open("image.raw", "rb") as f:  # the 4 KiB v3.14 image
 f.seek(PART); vbr = f.read(512)
for off in range(0, 0x60, 16):
 print(f"{off:04x} " + " ".join(f"{b:02x}" for b in vbr[off:off+16]))
```

Output (4 KiB image):

```
0000 00 00 00 52 65 46 53 00 00 00 00 00 00 00 00 00
0010 46 53 52 53 00 02 89 54 00 00 3e 00 00 00 00 00
0020 00 02 00 00 08 00 00 00 03 0e 02 00 66 00 00 00
0030 00 00 00 00 00 00 00 00 04 88 8b 4a a6 8b 4a 50
0040 00 00 00 04 00 00 00 00 ff c8 60 39 e7 a4 f0 49
0050 81 cb 45 63 78 6e 1a 86 00 00 00 00 00 00 00 00
```

Annotation: bytes `52 65 46 53` at +0x03 spell `ReFS`; `46 53 52 53` at +0x10 spell `FSRS`. Those two ASCII tags are the structural fingerprint -- if either is missing, you are not looking at a ReFS VBR. The jump instruction at +0x00 is `00 00 00` (ReFS pre-Insider is not BIOS-bootable).

### Step 3 -- Decode each scalar field (little-endian)

Per [vbr.md](../structures/vbr.md), unpack the fields at their fixed offsets:

```python
import struct
g = lambda fmt, off: struct.unpack_from(fmt, vbr, off)[0]
print("fs name @0x03 :", vbr[0x03:0x0B])
print("FSRS @0x10 :", vbr[0x10:0x14])
print("VBR cksum @0x16 :", hex(g("<H", 0x16)))
print("total sectors @0x18:", g("<Q", 0x18))
print("bytes/sector @0x20 :", g("<I", 0x20))
print("sectors/clus @0x24 :", g("<I", 0x24))
print("version @0x28 :", f"v{vbr[0x28]}.{vbr[0x29]}", "packed", hex((vbr[0x28]<<8)|vbr[0x29]))
print("cksum alg @0x2A :", hex(g("<H", 0x2A)))
print("vol flags @0x2C :", hex(g("<I", 0x2C)))
print("serial @0x38 :", hex(g("<Q", 0x38)))
print("bytes/container@0x40:", g("<Q", 0x40))
print("GUID @0x48 :", vbr[0x48:0x58].hex())
```

Output (4 KiB image):

```
fs name @0x03 : b'ReFS\x00\x00\x00\x00'
FSRS @0x10 : b'FSRS'
VBR cksum @0x16 : 0x5489
total sectors @0x18: 4063232
bytes/sector @0x20 : 512
sectors/clus @0x24 : 8
version @0x28 : v3.14 packed 0x30e
cksum alg @0x2A : 0x2
vol flags @0x2C : 0x66
serial @0x38 : 0x504a8ba64a8b8804
bytes/container@0x40: 67108864
GUID @0x48 : ffc86039e7a4f04981cb4563786e1a86
```

Annotation: version is decoded **byte-wise** -- major = byte at 0x28 (`0x03`), minor = byte at 0x29 (`0x0E` = 14), giving packed `0x030E` = v3.14, which matches the version table in [vbr.md](../structures/vbr.md). Do *not* read 0x28 as a single little-endian u16 (that yields the misleading `0x0E03`). Checksum selector `0x0002` = CRC64; volume flags `0x66` = native v3.10+ format (bits `0x02|0x04|0x20|0x40`).

### Step 4 -- Derive cluster size and container size

```python
bps, spc, bpc = g("<I",0x20), g("<I",0x24), g("<Q",0x40)
cluster = bps * spc
cpc = bpc // cluster
print("cluster size :", cluster, f"({cluster//1024} KiB)")
print("clusters/contnr:", cpc)
print("volume size :", g("<Q",0x18)*512 / 2**30, "GiB")
```

Output (4 KiB image):

```
cluster size : 4096 (4 KiB)
clusters/contnr: 16384
volume size : 1.9375 GiB
```

Annotation: cluster size = `512 * 8 = 4096`. Container size is the invariant `0x04000000` (64 MiB), so clusters-per-container = `67108864 / 4096 = 16384` -- the exact CPC value the [vbr.md](../structures/vbr.md) "Derived Values" table predicts for 4 KiB clusters.

### Step 5 -- Verify the VBR self-checksum

The stored u16 at 0x16 is a ROR-1 + ADD over bytes 3..511, skipping 0x16-0x17 (`RefsIsBootSectorOurs`):

```python
cs = 0
for i in range(3, 512):
 if i in (0x16, 0x17): continue
 cs = ((cs >> 1) | (cs << 15)) & 0xFFFF
 cs = (cs + vbr[i]) & 0xFFFF
print(hex(cs), "==", hex(g("<H",0x16)), "->", cs == g("<H",0x16))
```

Output (4 KiB image):

```
0x5489 == 0x5489 -> True
```

Annotation: the computed value equals the stored value, so this VBR is intact. A mismatch here is one of the few conditions that hard-blocks mount.

### Step 6 -- Contrast with the 64 KiB image

Running Steps 2-5 against the 64 KiB v3.14 image yields:

```
0020 00 02 00 00 80 00 00 00 03 0e 02 00 66 00 00 00
bytes/sector @0x20 : 512
sectors/clus @0x24 : 128
version @0x28 : v3.14 packed 0x30e
cksum alg @0x2A : 0x2
bytes/container@0x40: 67108864
cluster size : 65536 (64 KiB)
clusters/contnr: 1024
0x97a4 == 0x97a4 -> True
```

Annotation: the *only* changed format byte is sectors-per-cluster at 0x24 (`80` = 128 instead of `08` = 8), which lifts the cluster to 64 KiB and drops CPC to `67108864 / 65536 = 1024`. Container size, version, and checksum mode are identical. This is the entire difference between a "4K" and a "64K" ReFS volume at the VBR level.

### Step 7 -- Cross-check with the tool

```
$ python3 refsanalysis.py image.raw   # the 4 KiB v3.14 image
```

Output (excerpt):

```
 ReFS version: 3.14
 Cluster size: 0x1000 (4.0 KB)
 Container size: 0x4000000 (64.0 MB)
 Checksum: CRC64
```

And for the 64 KiB image:

```
 ReFS version: 3.14
 Cluster size: 0x10000 (64.0 KB)
 Container size: 0x4000000 (64.0 MB)
 Checksum: CRC64
```

Annotation: the tool's `version`, `cluster size`, `container size`, and `checksum` exactly match the values we hand-decoded -- 0x1000 vs 0x10000 cluster, 0x4000000 container, CRC64, v3.14. One subtlety worth noting: the tool's reported **Volume GUID** (`d2f386c7-...`) is *not* the VBR GUID at 0x48 (`ffc86039-...`); the tool sources the volume identity from the superblock/checkpoint, while 0x48 is the VBR's own extended GUID. They are different fields.

## What this tells you

- The VBR is self-describing and self-validating: from two ASCII tags (`ReFS` at +0x03, `FSRS` at +0x10), four scalars, and one checksum you can fully characterize a volume's geometry without any higher-level parser.
- **Cluster size is the master parameter.** A single byte at 0x24 distinguishes 4 KiB from 64 KiB volumes and propagates into clusters-per-container (16384 vs 1024), which every later virtual-to-physical address translation depends on.
- The version byte order is a classic trap: major/minor are *two bytes* (0x28, 0x29), not one little-endian u16. Read them byte-wise to get `0x030E` = v3.14.
- VBR 0x2A (`0x0002` = CRC64) is the *format-time* checksum selector and is never rewritten on upgrade -- on a v3.4 volume upgraded to v3.14 this byte would still read `0x0000`, and you would have to consult the checkpoint flags to learn the *runtime* checksum mode. Both images here were natively formatted, so VBR and runtime agree.
- A passing VBR checksum (Step 5) tells you the boot sector has not been tampered with by `refsutil fixboot`, which zeroes the container size, serial, checksum selector, GUID, and flags.

## See also

- [VBR structure](../structures/vbr.md) -- field-by-field layout this walkthrough decodes
- [Superblock (SUPB)](../structures/supb.md) -- where the VBR points next in the bootstrap chain
- [Checkpoint (CHKP)](../structures/chkp.md) -- the runtime checksum/version source for upgraded volumes
- [Page References](../structures/page_references.md) -- reference size keys off the VBR 0x2A selector (104/48/72 bytes)
- [Cluster and page size](../concepts/cluster_page_size.md) -- why 0x24 is the master geometry parameter
- [Checksum architecture](../concepts/checksum_architecture.md) -- CRC64 vs SHA-256 vs none
- [Bootstrap chain](../concepts/bootstrap_chain.md) -- VBR to SUPB to CHKP to Object Table
- [Version detection](../concepts/version_detection.md) -- VBR version vs mount history caveat
- Master thesis appendix **§A.1** (VBR layout)
