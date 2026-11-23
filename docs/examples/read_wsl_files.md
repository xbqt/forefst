# Read What WSL Left on a Volume

**Goal:** find the files the Windows Subsystem for Linux (WSL) wrote through a metadata-enabled mount, and read the
Linux facts they carry (file type, mode, owner, device number), which no Windows tool shows.

## Setup

Image: `win11refs2gtargeted.raw`, a native ReFS 3.14 lab volume. In its `wsltests` directory each kind of Linux file
was created from WSL (the list is on [WSL / Linux Metadata](../concepts/wsl_metadata.md#what-each-kind-of-wsl-file-carries)).
WSL keeps these facts in two places of the file's record:
- a reparse tag gives a special file's type;
- extended attributes (`$LXUID`, `$LXGID`, `$LXMOD`, `$LXDEV`) give its owner, mode and device.

## Step 1: the special files, by reparse tag

```text
$ forefst.py win11refs2gtargeted.raw files --filter wsl | cut -d, -f2,16,35,36
FullPath,FileAttributes,ReparseTag,ReparseTagHex
wsltests/testblk,Archive|ReparsePoint|EA,IO_REPARSE_TAG_LX_BLK,0x80000026
wsltests/testchr,Archive|ReparsePoint|EA,IO_REPARSE_TAG_LX_CHR,0x80000025
wsltests/testfifo,Archive|ReparsePoint|EA,IO_REPARSE_TAG_LX_FIFO,0x80000024
wsltests/testsocket,Archive|ReparsePoint|EA,IO_REPARSE_TAG_AF_UNIX,0x80000023
```

`--filter wsl` selects by reparse tag. It finds a block device, a character device, a FIFO and a socket. Each one
carries the EA bit beside the reparse-point bit.

## Step 2: the Linux facts of one file

```text
$ forefst.py win11refs2gtargeted.raw details /wsltests/testchr
[...]
  Reparse tag:        0x80000025 (IO_REPARSE_TAG_LX_CHR)
[...]
  PackedEaSize:       64
  WSL/Linux metadata:
    Mode:             char rw-rw-rw- (0o0666)
    UID:              0
    GID:              0
    Device:           1,3 (major,minor)
  Extended Attributes (4):
    $LXUID                    4B  00000000
    $LXGID                    4B  00000000
    $LXDEV                    8B  0100000003000000
    $LXMOD                    4B  b6210000
```

`$LXMOD` is a Linux `mode_t`. Its bytes `b6 21` are 0x21B6, or 0o20666: the character-device type bits, then the
permissions `rw-rw-rw-`. The file was made with `mknod c 1 3`, and `$LXDEV` holds that device number, 1,3.

The type in the mode word agrees with the reparse tag. It does so on every record of the corpus that carries
`$LXMOD`. `PackedEaSize` is the size of the four EAs, and the file's `$SI` repeats it.

## Step 3: every file with Linux metadata, by EA

```text
$ refsanalysis.py win11refs2gtargeted.raw attributes --filter wsl
[...]
    WSL metadata:      10
    Reparse points:    5
[...]
  FILE wsltests/file_setuid.txt
[...]
    Attributes:  0x40020 (Archive|EA)
[...]
    WSL Mode:    regular rwxr-xr-x (0o4755)
    WSL UID:     1000
    WSL GID:     1000
```

Selecting by EA finds ten files: the four special files, and six that carry Linux metadata without a WSL tag. Those
six are five regular files and the symlink, whose tag is the Windows symlink tag. A regular file has the EA bit and no
reparse-point bit (0x40020). Here its mode shows a setuid binary (0o4755), owned by Linux user 1000, which Windows
ACLs would never express in Linux terms.

## What to take from it

- The two selections count different sets. By tag finds the special files; by EA finds every file with Linux
  ownership metadata. The [concept page](../concepts/wsl_metadata.md#finding-wsl-files-with-the-tools-by-reparse-tag-or-by-ea)
  explains why the two counts need not match.
- Owner, mode and device are WSL's view of the file, stored beside the Windows security descriptor, not instead of it.
- Finding them shows that WSL wrote to this volume through a mount with metadata enabled.

## Cross-references

- [WSL / Linux Metadata](../concepts/wsl_metadata.md): the two mechanisms, the mode word, the symlink rule.
- [$EA_INFORMATION and $EA](../attributes/EA_INFORMATION.md): the EA records byte by byte.
- [$REPARSE_POINT](../attributes/REPARSE_POINT.md): the reparse tags.
