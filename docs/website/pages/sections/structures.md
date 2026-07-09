The byte-level on-disk layouts — every metadata structure decoded during the analysis, field by field.

The structures you touch in almost any analysis: the [VBR](vbr.md) (boot sector → version and cluster
size), the [Checkpoint](chkp.md) and [Superblock](supb.md) that bootstrap the volume, the
[Object Table](object_table.md) (the "where is object N" map — ReFS's closest thing to an `$MFT`),
[Directory Entries](directory_entries.md) (the per-file rows), and the generic
[B+-tree Node](btree_node.md) every table is built from.
