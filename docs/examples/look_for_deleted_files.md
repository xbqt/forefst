# Look for what was deleted

[A first examination](first_examination.md), 5 of 6 · previous: [Follow the history](follow_the_history.md) · next: [Check that it is intact](check_integrity.md)

Deleted metadata remains in several places. `deleted` reads them all and says, for every entry, what it is and what
decided it:

- **the Trash table**, which holds deleted directories and files only when their data stream set holds two or
  more tables (a file with a stream snapshot, for one), until they are removed: most deletes skip
  it, so it is usually empty;
- **the checkpoint comparison**: the tree of the volume against the tree of its other checkpoint copy, often the same
  tree: on most volumes measured both copies point to the same root pages;
- **the free space of live pages**: deleting a row removes its slot from the page's index and leaves its bytes;
- with `--full`, **old pages** the live tree no longer points to, over the whole volume.

Every row found is checked against the live tree before it is called deleted: a row whose file still exists, under
the same or another name, is `STILL PRESENT` or `RENAMED`, not a deletion. The first table tells you what you have:

```
$ forefst.py win11refstestmftecmd.raw deleted
[...]
                                    bytes in  carve     metadata  directory  empty  total
                                    the row   possible  only
    DELETED                               0        15        27         18      0     60
    DELETED, OR RENAMED                   0        17        49          0      3     69
    RENAMED                               0         0       121         58      4    183
    SAME FILE, OTHER CREATION TIME        0         0        24          0      0     24
    STILL PRESENT (the file is live)      4*        0       643         55    110    812
```

The tool states the limits of each recovery. Small files whose bytes sat in the row come back as the row holds them. Larger
ones can be *carved* from the clusters their old extent map names (`export deleted DIR --carve`), best effort: those
clusters may hold other data since, and the entry says so; where a cluster carries a checksum, the carve is checked
against it.

The journal can also hold records of a file that no page holds any more: the file followed in [Follow the history](follow_the_history.md) is in the journal, deleted, and
not among these rows.

Deeper: [Deletion recovery](../concepts/deletion_recovery.md) · [What survives](../concepts/what_survives.md) ·
[Snapshots](../concepts/snapshots_versioning.md)
