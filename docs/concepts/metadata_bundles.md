# Metadata bundles — what they contain, and what they do not

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
| Both checkpoints, every superblock copy | the redundancy pair, as found |
| The object B+-tree forest | every reachable metadata page, packed, with an index of their addresses |
| The MLog | control pages and every live log page, with an index |
| The USN change journal | the `$J` stream and an index of its addresses |
| **Inline file content** | see below — this is the part that surprises people |

## A bundle is not "metadata only"

ReFS keeps a **small stream inside the record**. A file under the inline ceiling has its bytes in the
metadata page, not in separate clusters — and so does a small alternate data stream. Reparse targets,
extended attributes and `$RECYCLE.BIN` records are in there too.

**Handing someone a bundle therefore hands them that content.** Every bundle states the amount, in
`manifest.json` and again in the banner every time it is opened:

```
[forefst]   File CONTENT is not in a bundle except what ReFS stores inline: 4037 stream(s), 1215305 byte(s).
```

There is no redaction option. One was attempted and withdrawn: locating payloads by searching for their
bytes zeroed 2 of 8 on a test volume and left the rest, because short payloads occur many times — and a
switch that leaves content behind while reporting that it removed it is worse than no switch. Treat a
bundle as carrying the inline content it declares.

## What a bundle does not hold

**Extent-backed content.** A file whose bytes live in on-disk clusters has those clusters left behind. The
bundle holds the *map* — you can see the file, its size, its timestamps, its owner, its runs — but not the
bytes.

Asking for them is refused rather than answered with zeros:

```
$ forefst.py ./bundle extract /copydrivers/drivers/acpi.sys
[forefst] WARNING: 873960 byte(s) ... are NOT IN THIS BUNDLE ... read this stream from the source image.
[forefst] --refuse-holes: nothing written.
$ echo $?
2
```

This is a **different statement** from the one a sparse disk image produces. There, zeros might be the
file's own content or a range the acquisition never captured, and the tool says it cannot tell. In a bundle
the absence is known, so the tool says so and writes nothing.

For the same reason, `deleted` and `snapshots` print a line saying their verdicts describe the **records**:
the evidence that a file existed and was deleted is complete in a bundle; its content is not.

## Where it came from

Every manifest records provenance, because a derived artefact has to name what it was derived from:

| field | |
|---|---|
| `tool`, `tool_version` | what wrote it |
| `source_path`, `source_size_bytes`, `source_content_pin` | which image, identified by content rather than by name |
| `exported_utc`, `host` | when and where |
| `absent_pages` | pages that could **not** be read at export time — already missing before the bundle existed |
| `source_holes` | ranges the source image stored as holes when it was read |
| `warnings` | anything that failed during export, such as a journal that could not be read |

`absent_pages` and `source_holes` are always present, including when empty — an empty list is a claim, and
a claim should be visible.

## Checking a bundle

```sh
forefst.py ./bundle verify-bundle
```

Verifies the sha256 seal, the manifest's required fields, that every index row lies inside the blob it
indexes, and that the bundle rehydrates and bootstraps. Exit **0** when whole, **2** when not. Declared
absences are reported as notes, not failures — they describe the volume, not damage to the bundle.

A bundle that fails its seal is also **refused on open**, so a damaged one cannot be half-read.

## How it is read

The bundle is rehydrated into a **sparse** image — every structure placed back at its own address — and
then read by the ordinary code path. That is deliberate: the alternative, teaching the reader to address
bytes a second way, is the shape that produced the 1.12.0 decoder defect, where a second reading of the
same structure answered first and returned another file's clusters. One addressing path, one set of
answers.

The practical consequence is that a bundle and its source volume give **identical output**. Measured on six
volumes spanning format 3.4 and 3.14, 4 KiB and 64 KiB clusters, SHA-256 checksums and snapshots: the
`files --csv` listing from the bundle is byte-identical to the listing from the volume.

Rehydration never materialises a dense file. A bundle from a 2 TB volume reconstructs a 2 TB apparent image
holding a few tens of megabytes.

## Evidence

Bundle round-trip equality, the refusal behaviour and the corruption cases are covered by
`analysis/tests/test_bundle.py`, which runs from a clone.
