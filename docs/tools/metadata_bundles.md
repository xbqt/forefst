# Metadata bundle

A **bundle** is what `export metadata` writes: a hash-sealed directory holding the structures of one ReFS
volume. It exists so a volume can be analysed later, elsewhere, without the disk — and so evidence can be
handed to someone else in a form they can check.

```sh
forefst.py disk.raw export metadata ./bundle     # on the machine with the disk
forefst.py ./bundle verify-bundle                # is it whole?
forefst.py ./bundle files --csv                  # anywhere, later, without the disk
```

## What a bundle holds

| | |
|---|---|
| Volume boot record | primary and backup |
| Both checkpoints, every superblock copy | the redundancy pair, as found: each checkpoint copy as its one-cluster record (4 KiB, or 64 KiB on a 64 KiB-cluster volume), its SHA-256 the one `summary` prints, the manifest naming its role (`in use`, `newest`, `superseded` or `tied`) and its clock |
| The object B+-tree forest | every reachable metadata page, packed, with an index of their addresses |
| The MLog | control pages and every live log page, with an index |
| The USN change journal | the `$J` stream and an index of its addresses |
| **Inline file content** | see below — this is the part that surprises people |

## A bundle is not "metadata only"

ReFS keeps a **small stream inside the record**. A file under the inline ceiling has its bytes in the
metadata page, not in separate clusters — and so does a small alternate data stream. Reparse targets,
extended attributes and `$RECYCLE.BIN` records are in there too.

**A bundle therefore gives its recipient that content**, and more. Beside the inline
bytes, a bundle carries:

- with the metadata pages: every file's and directory's name, times and attributes, the security descriptors (owner
  and group SIDs), the reparse targets and the Recycle Bin's `$I` records (original paths), and the free space of those
  pages, which can hold the rows of deleted files;
- with the journal: its records (file names, times, reasons);
- with the MLog: its records;
- in every bundle: the source image's path and the host it was made on.

`manifest.json` lists what this bundle carries (`Carries`), and the export, the reader's banner and `verify-bundle`
say it. Every bundle also states the inline amount, in `manifest.json` and again in the banner every time it is
opened (a bundle of a small test volume):

```
[forefst]   File CONTENT is not in a bundle except what ReFS stores inline: 8 stream(s), 254 byte(s). Extent-backed content is absent, and reads of it are refused rather than returned as zeros.
```

There is no redaction option. Locating payloads by searching for their bytes does not remove them reliably: on a
test volume it zeroed only a quarter of them and left the rest, because short payloads occur many times — A switch
that left content behind while reporting that it removed it would mislead, so there is none.

Treat a bundle as carrying the inline content it declares — and not only in the records: the same bytes can sit in
the MLog pages and in the free space of metadata pages, which the bundle carries too (on the volume of the banner
above, the bytes of every one of its inline payloads also occur in its MLog pages).

## What a bundle does not hold

**Extent-backed content.** A file whose bytes live in on-disk clusters has those clusters left behind. The
bundle holds the *map* — you can see the file, its size, its timestamps, its owner, its runs — but not the
bytes.

Asking for them is refused rather than answered with zeros:

```
$ forefst.py ./bundle extract /test/xbpt_config_log_714507.md     # a bundle of a test volume
...
Extracting 'xbpt_config_log_714507.md' (440919 bytes):
[forefst] NOTE: 8192 of 440919 bytes of 'xbpt_config_log_714507.md' would be written from ranges this bundle does not carry, which read back as zeros: 0-4095, 425984-430079. A metadata bundle carries file content only where ReFS stores it inline; extent-backed bytes were never exported, so these zeros were not read from the volume — read this stream from the source image.
[forefst] --refuse-holes: nothing written.
$ echo $?
2
```

The file has 108 clusters; only its two data clusters are counted: the other 106 are sparse runs, zeros by
the file's own extent map, which no image is read for.

This is a **different statement** from the one a sparse disk image produces. There, zeros might be the
file's own content or a range the acquisition never captured, and the tool says it cannot tell. In a bundle
the absence is known, so the tool says so and writes nothing.

For the same reason, `deleted` and `snapshots` print a line saying their verdicts describe the **records**:
the rows the bundle's pages hold, not the content. A bundle carries the pages of the live tree, so the deletion
evidence in their slack is there; the old pages elsewhere on the volume are not, so `deleted --full` and
`deleted --scan-pages` read only the clusters the bundle carries, say so and exit 2. Run them on the image.

## Where it came from

Every manifest records provenance, because a derived artefact has to name what it was derived from:

| field | |
|---|---|
| `BundleFormat` | the manifest's format, first; a bundle written by forefst 1.12.1–1.13.1 has none and is refused with a message (read it with forefst 1.13.1; its seal and files are unchanged), as is a newer format than the tool knows |
| `Provenance`: `Tool`, `ToolVersion` | what wrote it |
| `Provenance`: `SourcePath`, `SourceSize`, `SourceContentPin` | which image — the pin is a SHA-256 over the image size, its first 64 KiB (MBR/GPT), the primary superblock and both checkpoint clusters, so two states of one volume (before/after activity) produce different pins; it is a bootstrap-state fingerprint, not a whole-image hash |
| `Provenance`: `Exported`, `Host` | when and where |
| `AbsentPages` | pages that could **not** be read at export time — already missing before the bundle existed |
| `SourceHoles` | clusters the source image stored as holes when it was read: of the metadata pages, the `$J` stream and the MLog data area (`SourceHolesCover` names the three) |
| `PartitionStart`, `BytesPerSector` | where the volume starts in the source image, and the sector size the boot sectors' `lba` count |
| `Warnings` | each condition the export declares, and anything that failed: a journal that could not be read, each backup superblock slot that holds no valid copy (`the backup superblock slot at LCN 0x7bffd holds no valid copy: all zeros`, also on stderr; the export still exits 0), and an Object Table that could not be read in full when neither OID 0x9 nor OID 0xa is among its rows read — the Logfile Information Table could not be looked up, so no MLog is exported (a declared condition, not a failure) |
| `InlineContent` | the inline file content the bundle carries: `Streams`, `Bytes` |
| `Carries` | what the bundle carries, read from the parts it holds (a part asked for that the volume did not have, such as a change journal, is not listed) |

`AbsentPages` and `SourceHoles` are always present, including when empty — an empty list is written out too: it
says nothing was found missing, and a warning names what the tool could not check. A bundle without `SourceHolesCover` (made before 1.14.0) lists the holes of its
metadata pages only; reading it says so, because zeros in its `$J` and MLog data are then read as written.

`manifest.json` and `sha256sums.txt` are written as bytes, and the seal is made from the bytes written, so a
bundle made on Windows verifies anywhere. The index files (`metadata_index.csv`: `HeadPLCN,Clusters,ByteOffset,Owner`;
`usn_J_index.csv`: `PLCN,ByteOffset,Clusters`; `mlog_log_index.csv`: `BlockIndex,ByteOffset`) name their columns in
one form; the reader also reads the names older bundles carry.

## Checking a bundle

```sh
forefst.py ./bundle verify-bundle
```

Verifies the sha256 seal, the manifest's required fields, that every index row lies inside the blob it
indexes, and that the bundle rehydrates and bootstraps. Exit **0** when the bundle is whole and reading its
bootstrap structures recorded no finding; **2** when it is not whole, or when it is whole and reading its bootstrap
structures recorded a finding (the report says the bundle is whole and names each one). Declared absences are
reported as notes, not failures — they describe the volume, not damage to the bundle — except what a partial bundle
(`--what`) leaves out of the bootstrap: a root page or table the volume's view needs and the bundle does not carry is
a WARNING (`not carried by this bundle`), and the command exits 2. The redundancy findings of `summary` and
`integrity` (a checkpoint copy not in use that fails, a backup boot sector or superblock copy that fails its
checksum) are not checked here: run `summary` on the bundle for those.

A bundle that fails its seal is also **refused on open**, so a damaged one cannot be half-read.

## How it is read

The bundle is rehydrated into a **sparse** image — every structure placed back at its own address, the volume
starting where it starts in the source image — and then read by the ordinary code path. That is deliberate: a second
way of addressing the same bytes could give a different result for the same structure, so only one addressing path
is used.

A bundle written with `--btree-mode per-object` holds each object's B+-tree pages as one file per object, without
their addresses. It can be checked (`verify-bundle`), but it cannot be placed back as a volume, so the tools refuse it
as input (exit 1) and say why; the default packed mode writes a bundle the tools read.

As a result, a bundle that carries everything (the default: no `--what`) and its source volume
give **identical output**. Measured on six volumes spanning format 3.4 and 3.14, 4 KiB and 64 KiB clusters, SHA-256
checksums and snapshots: the `files --csv` listing from the bundle is byte-identical to the listing from the volume.

Every offset a command prints or writes from a bundle is the source image's, and `summary` says so:
`(offsets are the source image's: the bundle's volume is read where its partition starts there, at 0x1000000)`. A
bundle whose manifest does not record where the partition starts gives offsets in its rehydrated volume, which starts
at 0, and says that instead.

Holes and missing ranges are told apart:

- a range the manifest lists as a hole of the source image is stated as the image's readers state it, of the source
  image (`usn`, `timeline`, `timestomp` and `mlog` exit 2 there as on the image);
- a range the bundle does not carry is said to be not carried by this bundle.

`summary --hash` hashes nothing in bundle mode: the file read is the tool's own rehydration, and the bundle's files
are sealed by its `sha256sums.txt`.

An address in the manifest or an index that is not a file offset is an artefact that could not be placed:
`verify-bundle` reports it (exit 2) and opening the bundle names it.

Rehydration never materialises a dense file. A bundle from a 2 TB volume reconstructs a 2 TB apparent image
holding a few tens of megabytes.

## Evidence

Bundle round-trip equality, the refusal behaviour and the corruption cases are covered by
`analysis/tests/test_bundle.py`, which runs from a clone.

The counts behind the text: searching for the payloads' bytes zeroed 2 of the 8 inline payloads of its test volume;
on `win11refsmini` (the banner's sample) all 8 inline payloads also occur in its MLog pages, and its bundle's
`summary --json` / `integrity --json` (partition at 16 MiB) differ from the image's only in `image`, which names the
bundle; the extract example is a bundle of `win11refstestmftecmd`; the identical-output test covered six volumes.

