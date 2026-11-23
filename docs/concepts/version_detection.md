# Version Detection

A parser needs a ReFS volume's version before it reads any other structure. Many structures
change layout, size, or behaviour across versions:

- the checkpoint's [page references](../structures/page_references.md) shrink from 104 to 48 bytes;
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) grows from 116 to 124 bytes at v3.7, and its field
  at +0x50 changes meaning at v3.10;
- the boot sector's [checksum](checksum_architecture.md) selector counts only on volumes formatted at v3.10 or later.

A parser that interprets any structure before establishing the version will decode it with the wrong layout.

This page is the *classification procedure*: how to read a volume's version and, more importantly, how to tell a
freshly-formatted native volume from an old one that was upgraded in place, because those two histories leave
different traces on disk even when they report the same version number.

The companion page, [Version Evolution](version_evolution.md), is the canonical record of *what* changes
at each transition (the per-version schema, flag, and structure differences). This page covers a
narrower point: how to read, from an image, the volume's version and whether it was upgraded.

## The version field and the format-time fields

ReFS records its version in two places that can differ after an upgrade, and the detection procedure is based
on that difference.

- The **[VBR](../structures/vbr.md) version field (offset 0x28)** is rewritten on upgrade. On the v3.4 volume
  measured, its first Windows 11 mount changed this field from `0x0304` to `0x030E` (3.4 to 3.14), so on its own it
  tells you the *current* version but hides the volume's origin.
- The **VBR format-time fields** — the checksum-algorithm selector at **0x2A** and the Extended GUID at
  **0x48** — are written at format: no boot-sector write path of refs.sys 26100.9444 assigns them (`refsutil
  fixboot` rewrites both), and both kept their values across the two upgrades measured (3.4 to 3.14, 3.9 to 3.14).
  They record how the volume was formatted.
- The volume flags at **0x2C** are not one of them: refs.sys writes them at run time, although their format bits 0x20
  and 0x40 kept their values across both upgrades.

This difference reveals an upgrade. An upgraded volume reports the new version at 0x28 but still carries the old
format-time fields at 0x2A and 0x48, so comparing the rewritten field against the format-time ones exposes
the upgrade. This matters because some capabilities depend on the *original* format, not the
current version (see the native-vs-upgraded markers below) — an analyst who reads only 0x28 will conclude
a volume supports features it does not.

## The detection procedure

Read four fields, in order, and classify from their combination:

1. **VBR version (0x28)** — the current, possibly-upgraded version: the major byte at 0x28, the minor byte at 0x29
   (two bytes, not a little-endian u16). Written as major/minor: `0x0304` = v3.4, `0x0307` = v3.7, `0x0309` = v3.9,
   `0x030A` = v3.10, `0x030E` = v3.14.

   The version is tested at mount by `RefsMountVolume`, not by the boot-sector check `RefsIsBootSectorOurs`: major 3
   and a minor of at most 4 on refs.sys 17134, at most 0xE on 26100.9444 (one driver reading). A volume outside that
   range does not mount.
2. **VBR checksum-algorithm selector (0x2A)** — set at format time: no boot-sector write path of refs.sys 26100.9444
   assigns it, and it kept its value across the two upgrades measured (`refsutil fixboot` does rewrite it). Values:
   - `0x0000` on the volumes formatted at 3.4 to 3.9 (not read there: their pages carry CRC64);
   - `0x0002` = CRC64;
   - `0x0004` = SHA-256.

   The 26100 and Insider drivers read it only when the flags at 0x2C carry 0x40, and otherwise use CRC64 whatever 0x2A
   holds; 17134 never reads it. Because an upgrade leaves it as it was, it is a good discriminator of the original
   format era.
3. **VBR volume flags (0x2C)** — its bits 0x20 and 0x40 come from the format and were the same before and after the
   two upgrades measured; refs.sys sets and clears other bits at run time (0x02 at a writable mount; 0x01, 0x10,
   0x80). The combined value grows with the format era:
   `0x06` (v3.4), `0x26` (v3.7/v3.9, bit `0x20` = hard-link support), `0x66` (v3.10+, bit `0x40` gates the
   checksum).
4. **[CHKP](../structures/chkp.md) flags (offset 0x78)** — the runtime feature-activation register,
   maintained by the driver and read at mount by `ValidateCheckpointRecord`. This is where the
   native-vs-upgraded distinction is decided.

### Quick classification

| VBR flags (0x2C) | VBR 0x2A | CHKP flag 0x080 | Classification |
|------------------|----------|-----------------|----------------|
| 0x06 | 0x0000 | Not set | Original v3.4, or upgraded v3.4-to-v3.14 |
| 0x26 | 0x0000 | Not set | Original v3.7 / v3.9, or upgraded from them to v3.14 |
| 0x66 | 0x0002 | Set | Native v3.10+ |
| 0x66 | 0x0004 | Set | Native, SHA-256 (v3.14 on every volume measured) |

The first two rows are the ones that need the deeper check: `0x06` + `0x0000` is ambiguous between an
*original* v3.4 volume (version 0x28 still reads `0x0304`) and one *upgraded* to v3.14 (0x28 reads
`0x030E`), and `0x26` + `0x0000` the same way for v3.7 and v3.9. The VBR version field separates those two, and the
markers below confirm it.

A boot sector rewritten by `refsutil fixboot` falls outside the table: on the one such volume measured, a native v3.14
volume, it read flags `0x04` and `0x2A` = `0x0000`. Its checkpoint flags still classify it.

## The three upgrade states and the bit that defines them

The CHKP flags discriminate the volume's history. The three states an analyst meets most often are:

| State | CHKP flags | What it means |
|-------|-----------|---------------|
| **Original** (v3.4-v3.9) | 0x0002 | Formatted and only ever used on its original OS version |
| **Upgraded** (v3.4 to v3.14) | 0x0602 | Born on v3.4, later mounted on Windows 11 and upgraded in place |
| **Native v3.14** | 0x0682 | Freshly formatted under Windows 11 24H2 |

The single bit that separates *upgraded* from *native* is **0x0080 — the native-format marker**. It is set at
native-format time (from v3.10). No upgraded volume measured carries it.

That is what makes it forensically decisive: an upgraded volume acquires the other v3.14 flags at runtime (`0x0400`,
indirect roots `0x0200`) and ends up at `0x0602`, but on the upgrades measured it does not grow the `0x0080` bit, so
`0x0682` minus `0x0080` = `0x0602` is the signature of an in-place upgrade.

The flags field takes more than these three common values, and a parser must mask the *discriminating* bits rather
than match the whole word. Also observed:

- **0x0082** (native v3.10);
- **0x2682** / **0x2602** (an Insider build adds bit `0x2000`);
- **0x07b2** (`0x0682` with dedup `0x0010`, weak references `0x0020` and dirty-state tracking `0x0100`).

The discriminating bits are stable across all of these: **0x0080** is the native-format marker, and **0x0600** is set
on every v3.14 volume measured (`0x0200` the indirect root list; `0x0400` the record's rollback-protection fields,
which refs.sys sets on a volume of version 3.13 or later). The full bit decomposition lives on the
[Checkpoint](../structures/chkp.md#chkp-flags-offset-0x78) page; this page uses only the bits that classify.

## Native vs upgraded: the forensic markers

When the quick table lands on the ambiguous `0x06` / `0x0000` row, these five markers settle it. Each one is set at
format and kept by the upgrades measured (the 0x2C flags through their format bits), so each distinguishes a genuine
native v3.14 from a v3.4 volume upgraded to v3.14:

| Marker | Upgraded v3.4 to v3.14 | Native v3.14 |
|--------|------------------------|--------------|
| VBR flags (0x2C) | 0x06 | 0x66 |
| VBR checksum algorithm (0x2A) | 0x0000 | 0x0002 |
| VBR Extended GUID (0x48) | All-zero | Populated |
| CHKP flag 0x080 | Not set | Set |
| CHKP version echo (0x50) | 0x00000000 | 0x000E0003 |

The five agreed on both upgrades measured — none of them was rewritten by the upgrade — so in practice they
corroborate one another. A volume that shows even one "native" marker while reporting v3.14 at 0x28 without the
others should be treated as suspect (a sign of tampering or of a tool that rewrote the boot sector, as
`refsutil fixboot` does).

The **CHKP version echo at 0x50** is a particularly clear marker: native v3.10+ volumes pack the version there
(`minor << 16 | major`, e.g. `0x000E0003` for v3.14), while upgraded and legacy volumes leave it zero — so the field
both confirms the native format and restates the version independently of 0x28.

The format a volume was created at also decides a capability, though not through the checkpoint flag: refs.sys 26100
supports **hard links** exactly when the boot-sector flags (`+0x2C`) carry bit 0x20 (`InitializeVcbFromBootSector` /
`RefsHardlinksSupported`, read on 26100.9444 and .8115; 17134 has no such switch). On the corpus the bit is:

- set on every volume natively formatted at 3.7 or later, except one whose boot sector `refsutil fixboot` rewrote;
- clear on 3.4 volumes and on those upgraded from 3.4;
- kept on the corpus volume upgraded from 3.9.

The full capability comparison is on the [Version Evolution](version_evolution.md) page.

The tools also test the boot sector's version: one that is not 3.x with a minor of at most 14, or that
`$VOLUME_INFORMATION` does not corroborate on a volume with no upgrade evidence, makes `summary` state the volume
`VERSION CONTRADICTED - the boot sector is not corroborated` and exit 2 (`fastsummary`, `integrity` and
`refsanalysis boot --verify` make the same test; the other commands read the volume the same way and keep their
exit code).

## Features are declared before they are activated

Version-gated parsers often get this wrong: a field that names a feature is not proof of where the
feature starts. The clearest case is the metadata checksum:

| Feature | Where it shows | From |
|---------|----------------|------|
| CRC64 page references | checksum type 2 at reference +0x22 | v3.4 (every root reference read on the volumes formatted at 3.4 to 3.9) |
| Checksum selector at VBR 0x2A | `0x02` / `0x04`, read only with flags `0x40` | v3.10 |
| Compact checkpoint root references | `CHKP+0x5C` = 0x30 | v3.10 |
| Indirect root list | CHKP flag 0x200 | v3.14 |

A volume formatted at 3.4 to 3.9 carries `0x0000` at VBR 0x2A, and its page references are CRC64 all the
same: the Windows 11 driver does not read 0x2A without flag `0x40` and uses CRC64, and the Windows 10 driver
checks each page against the type its own reference names. The [Checksum Architecture](checksum_architecture.md)
page covers how each driver chooses the checksum, and why an upgraded volume still reads `0x0000` at 0x2A
while its references carry CRC64.

## Cross-references

- [Version Evolution](version_evolution.md) — the canonical record of *what* changes at each transition (this page classifies a volume; that page is the change log, including the full capability and schema-gating matrices)
- [VBR](../structures/vbr.md) — the version (0x28), checksum-selector (0x2A), volume-flags (0x2C), and Extended-GUID (0x48) fields this procedure reads
- [Checkpoint (CHKP)](../structures/chkp.md) — the full CHKP-flags bit decomposition and the version echo at 0x50; the runtime feature register that decides native vs upgraded
- [Checksum Architecture](checksum_architecture.md) — the checksum selector at VBR 0x2A, when the driver reads it, and what each format's page references carry
- [Page References](../structures/page_references.md) — the reference format (104 / 48 / 72 bytes) is gated by version and checksum mode, so it must not be parsed before the version is known
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — 116 bytes on v3.4, 124 bytes from v3.7, and its +0x50 field changes meaning at v3.10: a structure that mis-parses if the version is wrong
- [Bootstrap Chain](bootstrap_chain.md) — where reading the VBR and checkpoint sits in the parse order

## Evidence

- **The three volume states** (original `0x002`, upgraded `0x602`, native `0x682`) and the native-format marker bit
  `0x080` are read in the driver and re-measured across the corpus. The CHKP flags at CHKP+0x78 are read by
  `ValidateCheckpointRecord` (tested for `0x200` indirect-root mode and the other feature bits), and the checkpoint
  is selected in `ReadLatestCheckpoint` (17134 calls `ChooseCheckpointRecord` there).
- **The boot sector** is checked by `RefsIsBootSectorOurs` (signature, checksum and geometry bounds; read by
  `ReadBootSectorForMount`, geometry extracted by `InitializeVcbFromBootSector`); the version is tested in
  `RefsMountVolume`.
- **The flag patterns** were confirmed invariant within each category across the corpus, and the wider flag set
  (`0x0082`, `0x07b2`, `0x2682` / `0x2602`) was observed but does not disturb the discriminating bits.
- **The CRC64 page references** of the volumes formatted at 3.4 to 3.9: all 156 root references of the 12 such
  volumes in the corpus declare checksum type 2.
- **The upgrade markers** come from two upgrades: one from 3.4 to 3.14, one from 3.9 to 3.14.

See [how this was verified](../methodology.md) to trace these statements to the exact
images and measurements in `analysis/`.

<!-- findings: FS_CHKP_RA_001, FS_CHKP_RA_007, FS_CHKP_RA_013, MD_ATTR_RA_002 -->
