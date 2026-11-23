# WSL / Linux Metadata on ReFS

When the Windows Subsystem for Linux (WSL) accesses a ReFS volume through a DrvFs mount with
`-o metadata`, it persists Linux ownership, permission, and special-file identity directly on disk.

It does this with two mechanisms it did *not* invent:

- standard NT **extended attributes** (the `$LX*` family);
- standard NT **reparse tags** (the `LX_*` family).

For an analyst these artifacts are a strong sign that WSL wrote to the volume, and they show
ownership / mode / device facts that no native Windows tool shows.

## Why WSL writes these

A Linux file carries identity that the Windows file model has no slot for: a numeric uid/gid, a
`mode_t` permission word, and — for character/block devices — a major:minor device number. There is
also no Windows equivalent of a FIFO, a Unix-domain socket, or a Linux device node. Rather than invent a
new on-disk format, WSL borrows two NT extension points that ReFS already stores opaquely:

- **Ownership, permission, and device number** go into **extended attributes** — the `$EA` body, decoded
  byte-by-byte in [$EA_INFORMATION and $EA](../attributes/EA_INFORMATION.md).
- **Special-file *type*** (FIFO, socket, char/block device) goes into a **reparse tag** in
  [$REPARSE_POINT](../attributes/REPARSE_POINT.md), where the tag value itself is the marker.

For the analyst, the two differ in who reads them:

- The special-file **reparse tags** are opaque to `refs.sys`: it stores and returns them, and their WSL meaning
  comes from the WslFs / lxcore minifilters (the 17134, 26100 and Insider drivers read have no code for these tag
  values).
- The **`$LX*` EAs** are read by `refs.sys` itself on the 26100.8115 and Insider 29574 drivers read
  (`RefsQueryLxMetadataEa`: it checks that `$LXDEV` is 8 bytes and splits the major and minor numbers); the 17134
  driver has no such code.

Either way they survive intact on disk, and a forensic decode can read them without the WSL stack being present.

## The two artifact families

A WSL-touched file carries some combination of the following. Each row is **decoded byte-by-byte** in the
linked attribute page; the compact view here is for recognition and forensic meaning.

**Extended attributes — uid/gid/mode/device** (the `$EA` chain, type 0xE0; size index
`$EA_INFORMATION`, type 0xD0):

| EA name | Size | Meaning |
|---------|------|---------|
| `$LXUID` | 4 B | Linux owner UID |
| `$LXGID` | 4 B | Linux group GID |
| `$LXMOD` | 4 B | Linux `mode_t` — the `S_IFMT` type bits OR'd with the permission bits |
| `$LXDEV` | **8 B** | Device number = u32 *major* followed by u32 *minor* |

`$LXUID` / `$LXGID` / `$LXMOD` appear on the files WSL writes through a metadata-enabled mount. On the volume
measured, `$LXDEV` appears **only on device nodes** (character/block specials) — not on the FIFO, the socket or
a symlink.

The exact `FILE_FULL_EA_INFORMATION` field math and the `FILE_STAT_LX_INFORMATION` destination offsets are in
[$EA_INFORMATION and $EA](../attributes/EA_INFORMATION.md).

**Reparse tags — special-file *type*** (the `$REPARSE_POINT` attribute, type 0xC0). A
Linux special file has no regular Windows equivalent, so WSL marks its type with a reparse tag whose
`REPARSE_DATA_BUFFER` is essentially empty — the **tag value is the payload** (a FIFO's reparse data
length is 0):

| Tag | Symbolic name | WSL object |
|-----|---------------|------------|
| `0x80000023` | `IO_REPARSE_TAG_AF_UNIX` | Unix-domain socket |
| `0x80000024` | `IO_REPARSE_TAG_LX_FIFO` | named pipe / FIFO |
| `0x80000025` | `IO_REPARSE_TAG_LX_CHR` | character device |
| `0x80000026` | `IO_REPARSE_TAG_LX_BLK` | block device |

The full reparse-tag table, the verbatim-storage behaviour, and the per-tag payload notes are on
[$REPARSE_POINT](../attributes/REPARSE_POINT.md). A device node therefore carries **both** families at
once: the `LX_CHR` / `LX_BLK` reparse tag *and* an `$EA` chain whose `$LXMOD` repeats the type in its
`S_IFMT` bits and whose `$LXDEV` carries the major:minor pair.

## What each kind of WSL file carries

Measured on the lab volume, where each file was created in WSL through a metadata-enabled mount (`forefst details`
on each):

| File, as created in WSL | Reparse tag (`$REPARSE_POINT`) | WSL EAs (`$EA`) | `$LXMOD`: type, mode |
|---|---|---|---|
| regular file (`touch`, `chmod 755`) | none | `$LXUID`, `$LXGID`, `$LXMOD` | regular, 0o755 |
| regular file, setuid (`chmod 4755`) | none | `$LXUID`, `$LXGID`, `$LXMOD` | regular, 0o4755 |
| symlink to a relative name (`ln -s targetfile.txt`) | `0xA000000C`, a Windows symlink | `$LXUID`, `$LXGID`, `$LXMOD` | symlink, 0o777 |
| FIFO (`mkfifo`) | `0x80000024` `LX_FIFO` | `$LXUID`, `$LXGID`, `$LXMOD` | fifo, 0o644 |
| socket (a Python `AF_UNIX` bind) | `0x80000023` `AF_UNIX` | `$LXUID`, `$LXGID`, `$LXMOD` | socket, 0o755 |
| character device (`mknod c 1 3`) | `0x80000025` `LX_CHR` | `$LXUID`, `$LXGID`, `$LXMOD`, `$LXDEV` (1,3) | char, 0o666 |
| block device (`mknod b 7 0`) | `0x80000026` `LX_BLK` | `$LXUID`, `$LXGID`, `$LXMOD`, `$LXDEV` (7,0) | block, 0o660 |

How the three attributes relate:

- The EAs are kept in two attributes of the file's record that always come as a pair: `$EA_INFORMATION` (type
  0xD0), the 20-byte size summary, and `$EA` (type 0xE0), the list itself.
- The reparse tag is a third attribute of the same record, `$REPARSE_POINT` (type 0xC0).
- The file's `$STANDARD_INFORMATION` mirrors both: `$SI+0x50` holds the EAs' packed size (64 bytes on the character
  device) and `$SI+0x54` the reparse tag, and its file attributes carry the EA bit 0x40000 and the reparse-point bit
  0x400 (0x40020 on the regular files above, 0x40420 on the others).
- So a regular file WSL wrote has EAs and no reparse point; a special file has both; and a WSL symlink to a
  Windows-resolvable name has a Windows tag beside WSL's EAs.

## Reading the mode word

`$LXMOD` carries the most information of these fields: it is a Linux `mode_t`, so the high `S_IFMT` bits encode
the file *type* and the low bits encode the permission triad plus the setuid / setgid / sticky bits. The
type bits agree with the reparse tag, so the two can be checked against each other: on the volume measured, the
character device reads `0o20666`, the block device `0o60660` and the FIFO `0o10644`. On the corpus they agree on every
record that carries `$LXMOD` (23, on the three WSL volumes): a FIFO, character or block device or socket carries its
WSL tag, the symlink the Windows symlink tag, and a regular file or a directory no tag; `$SI+0x54` repeats the tag on
all 23. No write measured left a record where they disagree.
The permission and special bits show an examiner the privileges an executable was meant to run with (a setuid-root
binary, say) that Windows ACLs would never express in Linux terms.

## The symlink rule — which kind WSL writes

`IO_REPARSE_TAG_LX_SYMLINK` (`0xA000001D`) *is* produced by WSL on ReFS — but only for symlinks whose target
is not representable as a Windows path. WSL decides by the target:

- **A relative name that resolves** (`ln -s targetfile.txt`) becomes an ordinary **Windows** symlink — tag
  `IO_REPARSE_TAG_SYMLINK` (`0xA000000C`) with a UTF-16LE target.
- **An absolute Linux path** (`ln -s /etc/passwd`), or an **ext4 symlink copied in with `cp -a`**, becomes a
  **Linux** symlink — tag `IO_REPARSE_TAG_LX_SYMLINK` (`0xA000001D`) with a UTF-8 target.

The LX_SYMLINK reparse buffer is a `u32` version (observed value `2`) followed by the UTF-8 target with no NUL,
so the target begins **4 bytes into the reparse data** (buffer +0x0C). The forensic consequence: a Linux symlink
that points at a Windows-resolvable *relative* name is indistinguishable on disk from a native Windows symlink,
and a scan that filters only for `LX_*` tags will miss those — but a symlink to an absolute Linux path (or a
copied ext4 symlink) is a genuine `0xA000001D`, and its UTF-8 target is recoverable.

## Forensic implications

- **Points to WSL.** Any `$LX*` EA, or one of the three `LX_*` special-file tags (`LX_FIFO`, `LX_CHR`, `LX_BLK`),
  is a strong sign the volume was written by WSL through a metadata-enabled DrvFs mount: on the lab volume WSL wrote
  every one of them, and no refs.sys build read has code for these tag values.
  - The `AF_UNIX` tag (0x80000023) was written by WSL on the lab volume too (a socket bound through the mount).
    Whether other Windows programs create the same tag on a ReFS volume was not tested, so on its own it is a weaker
    sign than the `LX_*` tags.
- **Recovers Linux identity.** `$LXUID` / `$LXGID` / `$LXMOD` reconstruct the Linux ownership and
  permission model — including the file-type class and the setuid/setgid/sticky bits — for files that
  Windows ACLs would otherwise describe only in Windows terms. This can attribute a file to a specific
  Linux account or show the privileges an executable was meant to run with.
- **Reads files invisible to Windows tools.** Character/block specials and FIFOs/sockets are reparse
  points with (near-)empty data; Windows Explorer and most Windows-side tools either skip them or
  mis-render them. Decoding `$LXDEV` recovers the exact device the node addresses — identity a
  Windows-only examiner would miss entirely.
- **Tag-to-file enumeration.** Because each special file also registers in the global **Reparse Index**
  (OID 0x540 / 0x541), an analyst can range-scan that index by tag to enumerate every WSL special on the
  volume without walking every directory.
- **Pitfall — some WSL symlinks look like Windows symlinks.** A WSL symlink to a *Windows-resolvable relative
  name* surfaces as a normal Windows symlink (`0xA000000C`), not `0xA000001D`; a symlink to an *absolute Linux
  path* (or a copied ext4 symlink) is a true `0xA000001D`. Filtering only for `LX_*` tags catches the latter but
  silently skips the former.
- **Pitfall — off-by-one tag labels.** Use the mapping above, the values the lab volume holds: AF_UNIX =
  `0x80000023`, `LX_FIFO` = `0x80000024`, `LX_CHR` = `0x80000025`, `LX_BLK` = `0x80000026`. A table that
  shifts these by one — labeling `0x80000024` as `AF_UNIX` — mis-identifies every WSL special.

## Version and state differences

`$LX*` EA parsing is a property of the driver build, not of the volume format. The decode function
`RefsQueryLxMetadataEa` is present in the Windows 11 (26100) and Insider drivers but **absent from the Windows 10
17134 driver** (the v3.4 one), which stores these EAs as opaque blobs without interpreting them.

The reparse-tag *values* `0x80000023`–`0x80000026` match no constant in **any** `refs.sys` build examined: the
file-system driver carries no code for them at all, confirming they are minifilter-owned and opaque to ReFS
itself.

The decode is performed by `RefsQueryLxMetadataEa`, which locates each EA by name and gates it on its
exact value length before copying it into `_FILE_STAT_LX_INFORMATION` — the length check is the on-disk
size proof for "`$LXDEV` is 8 bytes":

```c
RtlInitString(&local_270,"$LXUID");
cVar4 = RefsLocateEaByName(p_Var2, uVar1, &local_270, &local_278);
if ((cVar4 != '\0') && (*(short *)(p_Var2 + local_278 + 6) == 4)) { // EaValueLength == 4
    *(undefined4 *)(param_5 + 0x4c) = ...; // STAT_LX uid
    *(uint *)(param_5 + 0x48) |= 1;
}
/* $LXGID -> +0x50 (|=2), $LXMOD -> +0x54 (|=4), each gated on length == 4 */

RtlInitString(&local_270,"$LXDEV");
cVar4 = RefsLocateEaByName(p_Var2, uVar1, &local_270, &local_278);
if ((cVar4 != '\0') && (*(short *)(p_Var2 + local_278 + 6) == 8)) { // EaValueLength == 8
    *(undefined4 *)(param_5 + 0x58) = ... ; // major (first u32)
    *(undefined4 *)(param_5 + 0x5c) = ... ; // minor (second u32)
    *(uint *)(param_5 + 0x48) |= 8;
}
```

The byte-level mechanics of this read — the `EaValueLength` at entry `+0x06`, the value start after the
name, and the `_FILE_STAT_LX_INFORMATION` destination offsets — are documented on
[$EA_INFORMATION and $EA](../attributes/EA_INFORMATION.md).

## Cross-references

- [$EA_INFORMATION and $EA](../attributes/EA_INFORMATION.md) — the `$EA` chain that carries
  `$LXUID` / `$LXGID` / `$LXMOD` / `$LXDEV`, with the `FILE_FULL_EA_INFORMATION` and
  `FILE_STAT_LX_INFORMATION` field math decoded byte-by-byte.
- [$REPARSE_POINT](../attributes/REPARSE_POINT.md) — the reparse attribute that carries the WSL
  special-file *type* tags, with the full tag table and the verbatim-storage behaviour.
- [Reparse Points](../structures/reparse_points.md) — the on-disk `$REPARSE_POINT` structure and the
  OID 0x540 / 0x541 Reparse Index used to enumerate WSL specials.
- [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) — where the reparse tag and the packed
  EA size are mirrored, enabling presence detection without reading the body.

## Evidence

`RefsQueryLxMetadataEa` reads the four EAs out of the `$EA` chain and copies them into
`_FILE_STAT_LX_INFORMATION`, gating each `$LX*` on its exact value length (E2) — present in the 26100 and
Insider drivers, absent from the 17134 driver. The four `$LX*` EAs (4/4/4/8 bytes), the four `LX_*` / `AF_UNIX`
reparse tags, the `$LXMOD` `S_IFMT` modes (chr `0o20666`, blk `0o60660`, fifo `0o10644`), the `$LXDEV`
major:minor encoding, the device-node-only `$LXDEV` rule, and the LX_SYMLINK producibility rule (an
absolute-Linux-path or copied ext4 symlink writes `0xA000001D` with a UTF-8 target at buffer +0x0C; a
Windows-resolvable relative name writes `0xA000000C`) are all raw-disk decoded (RD; the device nodes
and the socket on one v3.14 volume, LX_SYMLINK on a v3.14 8 GiB image, 2026-07-03).

See [how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.


## Finding WSL files with the tools: by reparse tag or by EA

The two mechanisms above mean there are **two distinct ways to select "WSL files"**, and the tools use one
each on purpose:

- **By reparse tag** — selects files whose *type* is a WSL special file (the `LX_*` / `AF_UNIX` tags). This
  is what `forefst files --filter wsl` uses.
- **By WSL metadata EA** — selects files that carry the `$LX*` ownership/mode EAs (surfaced as the Linux
  mode). This is what `refsanalysis attributes --filter wsl` uses.

They select different sets of files, and **the two counts need not match**: a special file always has a reparse
tag, but the `$LX*` EAs are only written when the volume was mounted with `-o metadata`, and a plain file
edited under WSL-metadata can carry `$LX*` EAs without any reparse tag. Use the reparse-tag filter to enumerate
special files, and the EA filter to find files with Linux ownership metadata.

<!-- findings: FS_SCHM_RA_006 -->
