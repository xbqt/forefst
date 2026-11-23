# Identify each file properly

[A first examination](first_examination.md), 2 of 6 · previous: [Know the volume](know_the_volume.md) · next: [Read the times with care](read_the_times.md)

`files` lists every name with its metadata (CSV, JSON or a body file); `details` shows one file in full. Two ideas
make the output readable.

**A file's identity is its reference, not its path.** ReFS gives every file a reference, which `forefst` prints as
`ObjectRef` in the form `HomeOID:FileID`: the object id of the directory it was created in, and an ordinal within
that directory. Ordinals are never reused, and the reference does not change when the file is renamed or moved. It
is the value the change journal records, so it is how you follow one file through its history. Directories are
objects of their own: the root is `0x600`, the others have ids from `0x701` up.

**Where the record is and where the data is are two separate properties.** A file's record either sits inside its name
row (*embedded*) or, on a volume that supports hard links, once the file gets a second name or moves to another
directory, is split out into a record of its own in its home directory (*split*). Independently of that, its bytes are
either inline in the record or in extents on the disk. `forefst` reports both as `RecordPlacement` and
`DataResidency`.

A hard-linked file on the special-files sample:

```
$ forefst.py win11refs2tspecials.raw details --path "test/[...]/xbpt_romeo_output_531365.cfg"
[...]
  ObjectRef:          0x7e6:0x8   (FileRef = HomeOID:FileID, the directory the file was CREATED in)
[...]
  Created:            2022-08-02T07:16:28.1705690Z
  Modified:           2026-05-16T16:41:30.2089469Z
  Changed:            2026-05-16T16:41:30.3005024Z
  Accessed:           2026-05-16T16:41:30.2089469Z
                      (updated only while last-access updating is on: a Windows setting, not on the volume)
[...]
  Record placement:   split
  Data residency:     extents
  Is moved:           undetermined (the file has 2 names; a name outside the creation directory may
                      be a hard link's or a moved name)
[...]
  Hard-link count:    2
```

Note the last two lines. The metadata cannot always tell a hard link from a move; where it cannot, `forefst` says
`undetermined` rather than guessing; where a change journal can be read, its records of the file's moves are used
too.

Deeper: [File identifiers](../concepts/file_ids.md) · [Object IDs](../concepts/object_ids.md) ·
[Record placement and data residency](../concepts/placement_and_residency.md) · [Hard links](../concepts/hard_links.md)
