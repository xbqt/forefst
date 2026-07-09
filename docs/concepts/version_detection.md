# Version Detection

A ReFS volume's version is a parsing precondition, not a label you can read once and set aside. Many
structures change layout, size, or behaviour across versions — the [page reference](../structures/page_references.md)
shrinks from 104 to 48 bytes, [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) is
re-laid-out at v3.14, the [checksum](checksum_architecture.md) flips from a stub to CRC64 — so a parser
that interprets any structure before establishing the version will decode it with the wrong frame. This
page is the *classification procedure*: how to read a volume's version and, more importantly, how to tell
a freshly-formatted native volume from an old one that was upgraded in place, because those two histories
leave different forensic fingerprints even when they report the same version number.

The companion page, [Version Evolution](version_evolution.md), is the canonical record of *what* changes
at each transition (the per-version schema, flag, and structure differences). This page answers the
narrower question: *given an image, which version and which upgrade history am I looking at?*

## Two fields decide it, and one of them never lies about history

ReFS records its version in two places that drift apart over a volume's life, and that drift is the whole
basis of the detection procedure.

- The **[VBR](../structures/vbr.md) version field (offset 0x28)** is rewritten on upgrade. A v3.4 volume
  mounted on Windows 11 has this field changed from `0x0304` to `0x030E`, so on its own it tells you the
  *current* version but hides the volume's origin.
- The **VBR format-time fields** — the checksum-algorithm selector at **0x2A**, the volume flags at
  **0x2C**, and the Extended GUID at **0x48** — are written once, at format, and are *never* touched again,
  not even by an in-place upgrade. They are the volume's birth certificate.

This asymmetry is the lever. An upgraded volume reports the new version at 0x28 but still carries the old
format-time fields at 0x2A/0x2C/0x48, so comparing the rewritten field against the immutable ones exposes
the upgrade. The discipline matters because some capabilities depend on the *original* format, not the
current version (see the native-vs-upgraded markers below) — an analyst who reads only 0x28 will conclude
a volume supports features it does not.

## The detection procedure

Read four fields, in order, and classify from their combination:

1. **VBR version (0x28)** — the current, possibly-upgraded version. `0x0304` = v3.4, `0x0307` = v3.7,
   `0x0309` = v3.9, `0x030A` = v3.10, `0x030E` = v3.14. Validated at mount by `RefsIsBootSectorOurs`;
   an invalid value prevents the volume from mounting at all.
2. **VBR checksum-algorithm selector (0x2A)** — format-time, never modified. `0x0000` = none (the older
   stub), `0x0002` = CRC64, `0x0004` = SHA-256. Because this is immutable, it is the most reliable single
   discriminator of original format era.
3. **VBR volume flags (0x2C)** — format-time, never modified. The composite climbs across format eras:
   `0x06` (v3.4), `0x26` (v3.7/v3.9, bit `0x20` = "Win11 format"), `0x66` (v3.10+, bit `0x40` gates the
   checksum).
4. **[CHKP](../structures/chkp.md) flags (offset 0x78)** — the runtime feature-activation register,
   maintained by the driver and read at mount by `ValidateCheckpointRecord`. This is where the
   native-vs-upgraded distinction is decided.

### Quick classification

| VBR flags (0x2C) | VBR 0x2A | CHKP flag 0x080 | Classification |
|------------------|----------|-----------------|----------------|
| 0x06 | 0x0000 | Not set | Original v3.4, or upgraded v3.4-to-v3.14 |
| 0x26 | 0x0000 | Not set | Original v3.7 / v3.9 |
| 0x66 | 0x0002 | Set | Native v3.10+ |
| 0x66 | 0x0004 | Set | Native v3.14 with SHA-256 |

The first row is the one that needs the deeper check: `0x06` + `0x0000` is ambiguous between an
*original* v3.4 volume (version 0x28 still reads `0x0304`) and one *upgraded* to v3.14 (0x28 reads
`0x030E`). The VBR version field separates those two, and the markers below confirm it.

## The three upgrade states and the bit that defines them

The CHKP flags discriminate the volume's history. The three states an analyst meets most often are:

| State | CHKP flags | What it means |
|-------|-----------|---------------|
| **Original** (v3.4-v3.9) | 0x0002 | Formatted and only ever used on its original OS version |
| **Upgraded** (v3.4 to v3.14) | 0x0602 | Born on v3.4, later mounted on Windows 11 and upgraded in place |
| **Native v3.14** | 0x0682 | Freshly formatted under Windows 11 24H2 |

The single bit that separates *upgraded* from *native* is **0x0080 — the native-format marker**. It is set
exactly once, at native-format time, by the format path, and it is **never added during an upgrade**.
That is what makes it forensically decisive: an upgraded volume can acquire every other v3.14 flag at
runtime (CRC64 `0x0400`, indirect roots `0x0200`) and end up at `0x0602`, but it can never grow the
`0x0080` bit, so `0x0682` minus `0x0080` = `0x0602` is the permanent signature of an in-place upgrade.

The flags field takes more than these three common values, and a parser must mask the *discriminating*
bits rather than match the whole word: also observed are **0x0082** (native v3.10), **0x2682** / **0x2602**
(Insider adds bit `0x2000`), and **0x07b2** (deduplication/compression adds bits `0x0130`). The
discriminating bits are stable across all of these: **0x0080** is the native-format marker and **0x0600**
is the upgrade/CRC64-plus-indirect-roots pair. The full bit decomposition lives on the
[Checkpoint](../structures/chkp.md) page (subtable A.4a); this page uses only the bits that classify.

## Native vs upgraded: the forensic markers

When the quick table lands on the ambiguous `0x06` / `0x0000` row, these five markers settle it. Each one
is an immutable format-time field or a format-only flag, so each independently distinguishes a genuine
native v3.14 from a v3.4 volume dragged up to v3.14:

| Marker | Upgraded v3.4 to v3.14 | Native v3.14 |
|--------|------------------------|--------------|
| VBR flags (0x2C) | 0x06 | 0x66 |
| VBR checksum algorithm (0x2A) | 0x0000 | 0x0002 |
| VBR Extended GUID (0x48) | All-zero | Populated |
| CHKP flag 0x080 | Not set | Set |
| CHKP version echo (0x50) | 0x00000000 | 0x000E0003 |

The five agree by construction — none of them is rewritten by the upgrade path — so in practice they
corroborate one another, and a volume that shows even one "native" marker while reporting v3.14 at 0x28
without the others should be treated as suspect (a sign of tampering or of a tool that rewrote the boot
sector). The **CHKP version echo at 0x50** is a particularly clean tell: native v3.10+ volumes pack the
version there (`minor << 16 | major`, e.g. `0x000E0003` for v3.14), while upgraded and legacy volumes
leave it zero — so the field both confirms the native format and restates the version independently of
0x28.

This native-vs-upgraded split has a direct capability consequence: **POSIX unlink/rename and hard links
require the native-format marker (CHKP flag 0x080)**. An upgraded volume reports support for them through
`fsutil`, but the on-disk format cannot carry them, so a tool that trusts the driver's reported
capabilities will overstate what an upgraded volume actually supports. The full capability comparison is
on the [Version Evolution](version_evolution.md) page.

## Features are declared before they are activated

A subtlety that trips up version-gated parsers: ReFS sometimes lays a structure on disk one version before
it begins *using* it, so the presence of a structure is not proof the feature is live. The clearest case
is the metadata checksum:

| Feature | Declared | Activated |
|---------|----------|-----------|
| CRC64 metadata verification | v3.10 (VBR 0x2A = 0x02) | v3.14 (CHKP flag 0x400) |
| Compact page references | v3.10 (0x30-byte references) | v3.10 |
| Indirect root list | — | v3.14 (CHKP flag 0x200) |

CRC64 is *declared* at v3.10 — the format-time selector at VBR 0x2A is set to `0x02` and the
[page references](../structures/page_references.md) shrink to their 48-byte form to make room for the
digest — but the driver does not *verify* against those checksums until v3.14 sets CHKP flag `0x0400`.
The forensic reading: VBR 0x2A tells you which checksum the volume was *formatted* for; the CHKP flag
tells you whether the driver is *enforcing* it. The [Checksum Architecture](checksum_architecture.md) page
covers the verification mechanism and why an upgraded volume can have CRC64 active (CHKP `0x0400` set) even
though its immutable VBR 0x2A still reads `0x0000`.

## Cross-references

- [Version Evolution](version_evolution.md) — the canonical record of *what* changes at each transition (this page classifies a volume; that page is the change log, including the full capability and schema-gating matrices)
- [VBR](../structures/vbr.md) — the version (0x28), checksum-selector (0x2A), volume-flags (0x2C), and Extended-GUID (0x48) fields this procedure reads
- [Checkpoint (CHKP)](../structures/chkp.md) — the full CHKP-flags bit decomposition (subtable A.4a) and the version echo at 0x50; the runtime feature register that decides native vs upgraded
- [Checksum Architecture](checksum_architecture.md) — why CRC64 is declared at v3.10 but only enforced at v3.14, and how upgraded volumes activate it at runtime
- [Page References](../structures/page_references.md) — the reference format (104 / 48 / 72 bytes) is gated by version and checksum mode, so it must not be parsed before the version is known
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — the $SI layout changes non-backward-compatibly at v3.14, a structure that mis-parses if the version is wrong
- [Bootstrap Chain](bootstrap_chain.md) — where reading the VBR and checkpoint sits in the parse order

## Evidence

The three discriminable volume states (original `0x002`, upgraded `0x602`, native `0x682`) and the
native-format marker bit `0x080` are decompiled from the driver (E2) and re-measured across the raw-disk
corpus (RD): the CHKP-flags decomposition is read by `ValidateCheckpointRecord` (flags at CHKP+0x78,
tested for `0x200` indirect-root mode and the other feature bits), the VBR version and signature are
validated by `RefsIsBootSectorOurs` (read by `ReadBootSectorForMount`, geometry extracted by
`InitializeVcbFromBootSector`), and checkpoint selection is performed by `ChooseCheckpointRecord`. The
flag patterns were confirmed invariant within each category across the corpus, and the wider flag set
(`0x0082`, `0x07b2`, `0x2682` / `0x2602`) was observed but does not disturb the discriminating bits.
Findings: **FS_CHKP_RA_013** (the three forensically distinguishable states), **FS_CHKP_RA_001** (the
full CHKP-flags decomposition). See [how this was verified](../methodology.md) to trace these to the exact images and
measurements in `analysis/`.
