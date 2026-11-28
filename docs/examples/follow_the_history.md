# Follow the history

[A first examination](first_examination.md), 4 of 6 · previous: [Read the times with care](read_the_times.md) · next: [Look for what was deleted](look_for_deleted_files.md)

ReFS keeps two histories, and they record different things.

**The change journal** (`$UsnJrnl`, when it is active) is a ring of records of each change: which file (by its
reference), when, and why (created, data written, renamed, deleted...). It outlives the files it describes. `usn`
lists and summarises it; `timeline --id` follows one file through it. Here is one file of the sample, created,
renamed and deleted: the journal still holds all of it, though the file is gone from its directory:

```
$ forefst.py win11refstestmftecmd.raw timeline --id 0x779:0x2
[...]
  Timestamp (UTC)               Src    OID         Path today / USN name       Event
  ----------------------------------------------------------------------------
[...]
  2026-05-23T07:38:44.4449016Z  USN    0x779       xbpt_papa_mike_179747.ini   FILE_CREATE
[...]
  2026-05-23T07:38:44.5402625Z  USN    0x779       xbpt_papa_mike_179747.ini   RENAME_OLD_NAME
  2026-05-23T07:38:44.5402625Z  USN    0x779       xbpt_echo_backup_965317.…   RENAME_NEW_NAME
[...]
  2026-05-23T07:38:45.4087587Z  USN    0x779       xbpt_echo_backup_965317.…   FILE_DELETE|CLOSE
[...]
------------------------------------------------------------------------------
  50 events
```

**The MLog** is the volume's transaction log: the metadata changes the driver commits, as redo records, kept so that a
crash can be replayed.

It has no wall-clock time of its own (`forefst` dates a record by the times embedded in it), and it names tables, not
files, but it can show changes that the committed tree does not hold yet, and records of an earlier volume's log can
survive a reformat (`mlog --earlier-logs` shows them).

`mlog --stats` gives an overview, `mlog --parse` groups the records into actions.

`timeline` merges both with the `$SI` times; it does not join rows across sources, and it tells you which source
each row came from.

Deeper: [USN journal](../structures/usn_journal.md) · [MLog](../structures/mlog.md) ·
[Artifact timeline](../concepts/artifact_timeline.md)
