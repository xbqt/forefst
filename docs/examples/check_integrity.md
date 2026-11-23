# Check that it is intact

[A first examination](first_examination.md), 6 of 6 · previous: [Look for what was deleted](look_for_deleted_files.md)

ReFS checksums its metadata: each reference to a page carries the page's CRC64 or SHA-256, and the boot sector,
superblock and checkpoint records carry their own. Files can also carry an **integrity stream**, a CRC-32C for each
data cluster. `integrity` checks the structure of the metadata pages; `integrity --checksums` also verifies checksums:
those of the system tables' pages, and of every file that carries a stream (`--fullchecksums` extends the page check
to every object's tree):

```
$ forefst.py win11refstestmftecmd.raw integrity --checksums
[...]
  Files with a stream:     189 (and 151 with no data in clusters: nothing to verify)
  Clusters carrying a CRC: 55586
  Clusters checked:        55586 (55586 OK, 0 FAILED)
  Never written:           46723 (clusters of these files in runs marked allocated but never
                           written: no data, read as zeros, nothing to verify)
  VERDICT: every checksummed file cluster matches its stored CRC-32C.
```

A checksum tells you the bytes are what the volume recorded, which catches corruption and a careless edit; it does
not prove nobody changed them, since a deliberate edit can rewrite the checksum too. A file without an integrity
stream has nothing on the volume that says what its bytes should be.

One rule runs through every command: **exit 0** means nothing was flagged; **exit 1** a usage error, an input that
could not be read or an output that could not be written; **exit 2** a finding, or work the command could not
complete, with the reason printed. A listing over a table that could not be read in full says so, and exits 2.

Deeper: [Checksum architecture](../concepts/checksum_architecture.md) · [Integrity streams](../concepts/integrity_streams.md) ·
[Exit codes](../tools/forefst.md#exit-codes)
