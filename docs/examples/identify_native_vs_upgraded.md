# Identify a Native vs Upgraded ReFS Volume

**Goal:** Decide whether a v3.14 ReFS volume was *freshly formatted* as 3.14 (Windows 11 24H2 or later) or
*upgraded* from an older v3.4 volume. Both report version 3.14, so the answer comes from the checkpoint flags and the
VBR fields an upgrade leaves unchanged — not the version number. `forefst.py <image> summary` states it in one line
(`Volume state:`); the steps below show what that line rests on and what it cannot tell.

`forefst summary` gives the answer in one line, `Volume state:`. This page shows that line first, then the fields it
rests on, read by hand.

## Setup

Two images from the lab corpus:

| Image | State | Metadata checksum | Path |
|-------|-------|-------------------|------|
| `win11refsmini.raw` | `native` | `CRC64` | `analysis/rawdisk/disks/step1/win11refsmini.raw` |
| `win10to11refs4g.raw` | `upgraded` | `CRC64` (VBR `0x2A` = 0, not read) | `analysis/rawdisk/disks/step3/win10to11refs4g.raw` |

The upgraded image was formatted on Win10 (v3.4) and later mounted read-write on Win11, which raised its version to
3.14. The version field reads v3.14 on both; this example shows how to tell them apart.

## The answer in one line: `forefst summary`

On the native volume:

```
$ forefst.py win11refsmini.raw summary
[...]
  Volume state:       NATIVE ReFS 3.14
[...]
```

On the upgraded one, the same line names the state and its reason, and a note on the boot sector's backup copy names
the version the volume was formatted with:

```
$ forefst.py win10to11refs4g.raw summary
[...]
  note: boot-sector version differs: primary ReFS 3.14 vs backup ReFS 3.4 (an upgrade leaves the
        backup at the version the volume was formatted with; an edit of the primary's version looks
        the same)
[...]
  Volume state:       ⚠ APPEARS UPGRADED (formatted before ReFS 3.10 (ReFS 3.4–3.9), now running ReFS 3.14)
      • CHKP native-format bit 0x080 is clear on a ReFS 3.10+ volume
[...]
```

What the line rests on, and what it cannot tell:

- It reads the checkpoint's native-format flag 0x080, which a volume formatted at 3.10 or later carries and an
  upgraded older volume lacks, and the two version stamps of `$VOLUME_INFORMATION`.
- By that rule, a volume formatted at 3.10 or later and upgraded later would keep 0x080 and read `NATIVE`; the test
  corpus holds no such volume.
- "Formatted before ReFS 3.10" does not say which older format: the backup boot sector's version does (3.4 here).

## Going deeper: the evidence, read by hand

The steps below read the same evidence with `refsanalysis`, and the boot-sector fields `summary` does not use for the
verdict (0x2A, 0x48 and the format bits of 0x2C), which confirm it.

### Step 1 — Extended summary of the NATIVE volume

The output, trimmed to the discriminating sections:

```text
$ refsanalysis.py win11refsmini.raw summary++
[...]
  Image:              win11refsmini.raw
  ReFS version:       3.14
  Volume GUID:        d2f386c7-2a6c-491c-addf-8fd1c98ca1ce
  Volume label:       minirefs
  Volume size:        2080374784 bytes (1.9 GiB)
  Cluster size:       4 KiB
  Container size:     64 MiB
  Checksum:           CRC64
[...]
------------------------------------------------------------------------------
Checkpoint
------------------------------------------------------------------------------
  Virtual clock:      64
  Copy in use:        LCN 0x13f8
  Flags:              0x682
  Containers mapped:  31
[...]
```

The checkpoint **Flags: 0x682** carries the native-format marker bit `0x0080`:

- `0x002` — the base flag;
- `0x080` — native format (a volume formatted at 3.10 or later);
- `0x600` — `0x200` (indirect roots, set from version 3.11) + `0x400` (the record carries the rollback-protection
  fields, set from version 3.13).

The summary reports CRC64 because the volume was formatted as 3.14: its boot sector's flags carry 0x40, so refs.sys
reads the selector at 0x2A, which is 0x02.

### Step 2 — Extended summary of the UPGRADED volume

The same sections:

```text
$ refsanalysis.py win10to11refs4g.raw summary++
[...]
  Image:              win10to11refs4g.raw
  ReFS version:       3.14
  Volume GUID:        9161b91f-82af-4478-8e87-58643b488005
  Volume label:       win10to11refs4g
  Volume size:        4227858432 bytes (3.9 GiB)
  Cluster size:       4 KiB
  Container size:     64 MiB
  Checksum:           CRC64 (the boot sector's checksum selector, +0x2a = 0x0, is not read: its flags, +0x2c = 0x6, lack 0x40, so refs.sys 26100 and Insider 29574 use CRC64)
[...]
------------------------------------------------------------------------------
Checkpoint
------------------------------------------------------------------------------
  Virtual clock:      68
  Copy in use:        LCN 0x2874
  Flags:              0x602
  Containers mapped:  63
[...]
```

Same `ReFS version: 3.14`, but **Flags: 0x602** — the `0x0080` native bit is *missing*. `0x602 = 0x002 + 0x600`.

- The `0x600` (indirect roots + the rollback-protection fields) was added when Win11 upgraded the volume.
- The upgrade did not add `0x080`: it marks a volume formatted at 3.10 or later, and the volume upgraded from 3.4
  does not carry it.
- The checksum selector at `0x2A` still holds the original v3.4 value, 0, but the flags at `0x2C` lack 0x40, so
  refs.sys does not read it and uses CRC64 — which the summary says.

### Step 3 — Read the VBR format-time fields by hand (both images)

The checkpoint flags are *runtime* state. To confirm provenance, read the VBR fields an upgrade did not rewrite on
the two upgrades measured.

The ReFS partition starts at GPT offset `0x1000000` on both images; the VBR is at the start of the partition.
Fields: `0x28` version (u16), `0x2A` checksum selector (u16), `0x2C` volume flags (u32), `0x48` Extended GUID
(16 bytes).

```python
import struct
PART = 0x1000000
IMAGES = [("NATIVE", "win11refsmini.raw"),
          ("UPGRADED", "win10to11refs4g.raw")]
FIELDS = [("0x28 version", 0x28, "H"),
          ("0x2A checksum selector", 0x2A, "H"),
          ("0x2C volume flags", 0x2C, "I")]
WIDTH = {"H": 4, "I": 8}
SIZE = {"H": 2, "I": 4}

for tag, img in IMAGES:
    with open(img, "rb") as f:
        f.seek(PART)                     # the partition start: the VBR is its first sector
        vbr = f.read(512)
    print("=== %s %s ===" % (tag, img))
    for label, off, fmt in FIELDS:
        val = struct.unpack_from("<" + fmt, vbr, off)[0]
        raw = vbr[off:off + SIZE[fmt]].hex()
        print(" %-22s = 0x%0*X raw=%s" % (label, WIDTH[fmt], val, raw))
    guid = vbr[0x48:0x58]
    print(" %-22s = %s all-zero? %s" % ("0x48 extended GUID", guid.hex(),
                                        all(b == 0 for b in guid)))
    print()
```

Its output (run in the folder that holds the two images):

```text
=== NATIVE win11refsmini.raw ===
 0x28 version           = 0x0E03 raw=030e
 0x2A checksum selector = 0x0002 raw=0200
 0x2C volume flags      = 0x00000066 raw=66000000
 0x48 extended GUID     = ffc86039e7a4f04981cb4563786e1a86 all-zero? False

=== UPGRADED win10to11refs4g.raw ===
 0x28 version           = 0x0E03 raw=030e
 0x2A checksum selector = 0x0000 raw=0000
 0x2C volume flags      = 0x00000006 raw=06000000
 0x48 extended GUID     = 00000000000000000000000000000000 all-zero? True
```

Reading the bytes:

- **0x28 version is identical (`03 0e`) on both** — the LE u16 is `0x0E03`, the master's packed `major.minor`
  notation `0x030E` (major `0x03`, minor `0x0E` = 14).
  - The version field records *mount history*, not the original format version (see [VBR](../structures/vbr.md)).
  - A v3.4 volume mounted read-write by a Windows that writes 3.14 is stamped 0x030E.
- **0x2A checksum selector** — native `0x0002` (CRC64), upgraded `0x0000` (not read).
  - This field is set at format time and an upgrade does not change it (both upgrades measured).
  - It still holds 0 on the upgraded volume, where the driver uses CRC64: the flags at 0x2C lack 0x40, so the
    driver does not read 0x2A.
- **0x2C volume flags** — native `0x66`, upgraded `0x06`.
  - Native carries bits `0x20` (hard-link support) + `0x40` (formatted at 3.10 or later: the driver reads the
    checksum selector at 0x2A only with it).
  - The upgraded volume keeps its original v3.4 `0x06` and is *not* rewritten to `0x66`.
- **0x48 Extended GUID** — populated on native, all-zero on upgraded. On the corpus it is populated only on volumes
  formatted at 3.10 or later.

## What this tells you

`win11refsmini.raw` is **natively formatted v3.14**; `win10to11refs4g.raw` is **upgraded from v3.4**. Every marker agrees:

| Marker | Native (`win11refsmini`) | Upgraded (`win10to11refs4g`) | What it shows |
|--------|--------------------------|------------------------------|---------------|
| VBR version (0x28) | 0x030E | 0x030E | **identical: no use for provenance** |
| CHKP flags | `0x682` (has 0x080) | `0x602` (no 0x080) | the native-format bit `summary` reads |
| VBR checksum sel. (0x2A) | `0x0002` (CRC64) | `0x0000` (not read: CRC64 used) | a format-time field, unchanged by the upgrade |
| VBR volume flags (0x2C) | `0x66` | `0x06` | the format bits 0x20 / 0x40, unchanged by the upgrade |
| VBR Extended GUID (0x48) | populated | all-zero | a format-time field: populated only when formatted at 3.10 or later |

The single most decisive bit is **CHKP flag `0x0080`** (native-format marker): set on a volume formatted at 3.10 or
later, and not added by the upgrade of the 3.4 volume.

The VBR fields corroborate it: `0x2A` and `0x48` are format-time fields, and the format bits of `0x2C` (0x20, 0x40)
kept their values on the two upgrades measured (`0x2C` itself is written at run time: a writable mount sets 0x02).

CHKP flag values you may see: `0x002` legacy v3.4–v3.9, `0x082` native v3.10, `0x602` upgraded v3.14, `0x682`
native v3.14, `0x07b2` dedup, `0x2682` Insider.

Practical consequences:

- An upgraded volume uses CRC64 (the tool summary says so) while its VBR still reads `0x0000` at 0x2A: the driver
  does not read that field when the flags at 0x2C lack 0x40. A parser takes the checksum from each page reference,
  not from VBR `0x2A`.
- Forensically, a volume upgraded from 3.4 also has no hard-link support: refs.sys gates it on the boot-sector
  flags' bit 0x20, clear on its `0x06` (the one volume of the corpus upgraded from 3.9 kept the bit).

## See also

- [Version detection](../concepts/version_detection.md) — the three upgrade states and the discriminating bits (`0x0080` / `0x0600`)
- [Volume Boot Record (VBR)](../structures/vbr.md) — field layout, version-vs-mount-history caveat, format-time fields
- [Checkpoint (CHKP)](../structures/chkp.md) — flag bit table (`0x0080` native marker) and observed composite values
- [Decode the VBR by hand](decode_vbr_by_hand.md) — full field-by-field VBR walkthrough
