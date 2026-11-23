# Know the volume

[A first examination](first_examination.md), 1 of 6 · next: [Identify each file properly](identify_each_file.md)

Start with `summary`. It follows the chain the driver reads at mount (boot sector, superblock, checkpoint) and tells
you what you are holding:

```
$ forefst.py win11refstestmftecmd.raw summary
[...]
  ReFS version:       3.14
  Volume GUID:        bf9b2e6e-46dc-4e9d-b577-b16058d3fe3b
  Volume serial:      0xb2c21231c211f9f5
  Volume label:       win11refstestmftecmd
  Volume size:        4227858432 bytes (3.9 GiB)
  Cluster size:       4 KiB
  Container size:     64 MiB
  Checksum:           CRC64
[...]
  CHKP primary     LCN 0x1e3f4 (offset 0x1f3f4000; 1 cluster, 4 KiB)  — checksum OK, vclock=617, in use
[...]
  CHKP secondary   LCN 0x2874 (offset 0x3874000; 1 cluster, 4 KiB)  — checksum OK, vclock=616, superseded
[...]
  USN Journal:        Active
[...]
  Files:              1225 (214 inline, 1011 extents)
  Names:              1507 (1225 files, plus 282 more names: 168 hard-linked files have 450 names)
```

What to take from it:

- **The version** decides how everything else is read; `forefst` reads it from the boot sector and picks the layout.
- **The redundant copies.** The boot sector, the superblock and the checkpoint each exist more than once. The
  checkpoint has two copies, and the volume is read from the newest one that passes its checks; the other is an
  earlier state of the whole volume, one step back. A copy that fails is reported, and the exit code says so (2).
- **Files and names are not the same count.** A hard-linked file has several names; `forefst` counts files once
  and tells you how many names they have.
- **Whether a change journal exists.** If it says `Active`, you have a history of changes to work with (see [Follow the history](follow_the_history.md)).

**Work on the image, never on the volume mounted by Windows.** A read-write mount changes it: a newer Windows
upgrades an older volume to its own format version, and the driver rewrites a copy that fails its check from a good
one and can remove corrupt data from the namespace. `forefst` opens the image read-only.

Deeper: [Bootstrap chain](../concepts/bootstrap_chain.md) · [Redundancy](../concepts/redundancy.md) · [the `summary` command](../tools/forefst.md)
