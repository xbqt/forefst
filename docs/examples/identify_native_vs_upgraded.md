# Identify a Native vs Upgraded ReFS Volume

**Goal:** Decide whether a v3.14 ReFS volume was *freshly formatted* under Win11 24H2 or *upgraded* from an older v3.4 volume. Both report version 3.14, so the answer comes from the checkpoint flags and the immutable VBR format-time fields — not the version number.

## Setup

Two images from the lab corpus (volume `state` shown):

| Image | corpus `state` | corpus `checksum` | Path |
|-------|----------------|-------------------|------|
| `win11refsmini.raw` | `native` | `CRC64` | `win11refsmini.raw` |
| `win10to11refs4g.raw` | `upgraded` | `None` | `win10to11refs4g.raw` |

The upgraded image was formatted on Win10 (v3.4) and later mounted on Win11, which bumped its version to 3.14. Both are v3.14 to the version field — the trap this example defuses.

## Steps

### Step 1 — Extended summary of the NATIVE volume

```
$ python3 refsanalysis.py win11refsmini.raw summary++
```

Actual output (trimmed to the discriminating sections):

```
 Image: win11refsmini.raw
 ReFS version: 3.14
 Cluster size: 0x1000 (4.0 KB)
 Checksum: CRC64

------------------------------------------------------------------------------
Checkpoint
------------------------------------------------------------------------------
 Virtual clock: 64
 Flags: 0x682
 Containers mapped: 31
```

The checkpoint **Flags: 0x682** carries the native-format marker bit `0x0080`. `0x682 = 0x002 (base) + 0x080 (native format) + 0x600 (indirect roots + CRC64)`. The driver reports CRC64 because the volume was *born* on v3.14.

### Step 2 — Extended summary of the UPGRADED volume

```
$ python3 refsanalysis.py win10to11refs4g.raw summary++
```

Actual output (same sections):

```
 Image: win10to11refs4g.raw
 ReFS version: 3.14
 Cluster size: 0x1000 (4.0 KB)
 Checksum: None

------------------------------------------------------------------------------
Checkpoint
------------------------------------------------------------------------------
 Virtual clock: 68
 Flags: 0x602
 Containers mapped: 63
```

Same `ReFS version: 3.14`, but **Flags: 0x602** — the `0x0080` native bit is *missing*. `0x602 = 0x002 + 0x600`. The `0x600` (indirect roots + CRC64-capable) was added when Win11 upgraded the volume, but `0x080` is only ever written at native format time, never during upgrade. The reported `Checksum: None` is the original v3.4 setting carried through.

### Step 3 — Read the VBR format-time fields by hand (both images)

The checkpoint flags are *runtime* state. To confirm provenance, read the VBR fields that are fixed at format time and never rewritten on upgrade. The ReFS partition starts at GPT offset `0x1000000` on both images; the VBR is at the start of the partition. Fields: `0x28` version (u16), `0x2A` checksum selector (u16), `0x2C` volume flags (u32), `0x48` Extended GUID (16 bytes).

```python
import struct
PART = 0x1000000
IMAGES = [("NATIVE", "win11refsmini.raw"),
 ("UPGRADED", "win10to11refs4g.raw")]
FIELDS = [("0x28 version", 0x28, "H"),
 ("0x2A checksum selector", 0x2A, "H"),
 ("0x2C volume flags", 0x2C, "I")]
WIDTH = {"H": 4, "I": 8}; SIZE = {"H": 2, "I": 4}

for tag, img in IMAGES:
 vbr = open(img, "rb").read()[PART:PART+512] # seek to partition, read VBR
 print("=== %s %s ===" % (tag, img))
 for label, off, fmt in FIELDS:
 val = struct.unpack_from("<" + fmt, vbr, off)[0]
 raw = vbr[off:off+SIZE[fmt]].hex()
 print(" %-22s = 0x%0*X raw=%s" % (label, WIDTH[fmt], val, raw))
 guid = vbr[0x48:0x58]
 print(" %-22s = %s all-zero? %s" % ("0x48 extended GUID", guid.hex(),
 all(b == 0 for b in guid)))
 print()
```

Actual output:

```
=== NATIVE win11refsmini.raw ===
 0x28 version = 0x0E03 raw=030e
 0x2A checksum selector = 0x0002 raw=0200
 0x2C volume flags = 0x00000066 raw=66000000
 0x48 extended GUID = ffc86039e7a4f04981cb4563786e1a86 all-zero? False

=== UPGRADED win10to11refs4g.raw ===
 0x28 version = 0x0E03 raw=030e
 0x2A checksum selector = 0x0000 raw=0000
 0x2C volume flags = 0x00000006 raw=06000000
 0x48 extended GUID = 00000000000000000000000000000000 all-zero? True
```

Reading the bytes:

- **0x28 version is identical (`03 0e`) on both** — the LE u16 is `0x0E03`, the master's packed `major.minor` notation `0x030E` (major `0x03`, minor `0x0E` = 14). This is the trap: the version field records *mount history*, not the original format version (vbr.md, §A.1a). A v3.4 volume mounted on Win11 gets stamped 0x030E.
- **0x2A checksum selector** — native `0x0002` (CRC64), upgraded `0x0000` (None). This field is set at format time and **never modified on upgrade** (§H.5 "Fields Unchanged"). It still says None on the upgraded volume even though the driver activates CRC64 via the CHKP flags.
- **0x2C volume flags** — native `0x66`, upgraded `0x06`. Native carries bits `0x20` (Win11 format) + `0x40` (native v3.10+ format); the upgraded volume keeps its original v3.4 `0x06` and is *not* rewritten to `0x66`.
- **0x48 Extended GUID** — populated on native, all-zero on upgraded. Populated only at native v3.10+ format time (§H.6).

## What this tells you

`win11refsmini.raw` is **natively formatted v3.14**; `win10to11refs4g.raw` is **upgraded from v3.4**. Every marker agrees:

| Marker | Native (`win11refsmini`) | Upgraded (`win10to11refs4g`) | Source |
|--------|--------------------------|------------------------------|--------|
| VBR version (0x28) | 0x030E | 0x030E | **identical — useless for provenance** |
| CHKP flags | `0x682` (has 0x080) | `0x602` (no 0x080) | §H.6 |
| VBR checksum sel. (0x2A) | `0x0002` (CRC64) | `0x0000` (None) | §H.5 |
| VBR volume flags (0x2C) | `0x66` | `0x06` | §H.6 |
| VBR Extended GUID (0x48) | populated | all-zero | §H.6 |

The single most decisive bit is **CHKP flag `0x0080`** (native-format marker): set only at native format time, never added during upgrade. The VBR `0x2A` / `0x2C` / `0x48` fields corroborate it because the upgrade path never touches them. (CHKP flag values you may see: `0x002` legacy v3.4–v3.9, `0x082` native v3.10, `0x602` upgraded v3.14, `0x682` native v3.14, `0x07b2` dedup, `0x2682` Insider.)

Practical consequence: an upgraded volume reports CRC64 to `fsutil`/the tool summary, but its VBR still declares `None` — so a parser must read the **CHKP flags**, not VBR `0x2A`, to know the runtime checksum algorithm. Forensically, an upgraded volume also lacks native-only capabilities gated on flag `0x080` (POSIX unlink/rename, hard links — §H.7).

## See also

- [Version detection](../concepts/version_detection.md) — the three upgrade states and the discriminating bits (`0x0080` / `0x0600`)
- [Volume Boot Record (VBR)](../structures/vbr.md) — field layout, version-vs-mount-history caveat, format-time immutable fields
- [Checkpoint (CHKP)](../structures/chkp.md) — flag bit table (`0x0080` native marker) and observed composite values
- [Decode the VBR by hand](decode_vbr_by_hand.md) — full field-by-field VBR walkthrough
- Master thesis appendix **§A.1** (VBR layout), **§H.5** (upgrade behaviour: fields changed vs unchanged), **§H.6** (native vs upgraded forensic markers)
