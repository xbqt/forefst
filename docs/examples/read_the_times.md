# Read the times with care

[A first examination](first_examination.md), 3 of 6 · previous: [Identify each file properly](identify_each_file.md) · next: [Follow the history](follow_the_history.md)

> Every file and directory carries four times in its `$STANDARD_INFORMATION`: **Created**, **Modified** (the data),
> **Changed** (the metadata) and **Accessed**. `forefst` prints them in UTC with all seven digits of the fraction, so
> they sort as text.
>
> Two cautions before you build a timeline on them:
>
> - **Accessed is usually not maintained.** Windows does not update it on read unless last-access updating is turned
>   on, a setting of the machine, not of the volume. Treat it as weak, and look at whether it ever moves past Modified and
>   Changed (`summary` tells you when some files show it was on at some point).
> - **Times can be set by a program.** `timestomp` looks for the traces a backdating leaves: a Created time before the
>   volume existed (a copy that keeps its times leaves it too), a Changed time later than the others in a way a copy
>   does not produce, the journal recording a change of basic information, or the names of a hard-linked file
>   disagreeing on their Created time. It grades what it finds; its strongest grade needs corroboration from the journal
>   or a second name, and its weakest findings are leads, not conclusions.

## Reading one time by hand

Each of the four times is a Windows FILETIME: a 64-bit count of 100-nanosecond intervals since
1601-01-01 00:00:00 UTC. That is why `forefst` prints seven digits after the second: a second holds 10,000,000 such
intervals, and seven digits keep every one.

Take the file whose `$STANDARD_INFORMATION` is drawn byte by byte on the
[$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) page. `details` shows its four times:

```
$ forefst.py win11refstestmftecmd.raw details --path testspecials/dir_romeo_413583/dir_kilo_704584/dir_report_123351/xbpt_quebec_cache_515604.cfg
[...]
  Created:            2024-09-02T07:42:02.9958300Z
  Modified:           2024-09-02T07:42:02.9958300Z
  Changed:            2026-05-23T07:44:23.2970720Z
  Accessed:           2024-09-02T07:42:02.9958300Z
[...]
```

Created is the first 8 bytes of that `$STANDARD_INFORMATION`, stored least significant byte first. Decoded by hand:

```text
the 8 bytes at $SI+0x00                9c f4 ef 99 0b fd da 01
read as a little-endian u64            0x01DAFD0B99EFF49C = 133,697,365,229,958,300
divided by 10,000,000                  13,369,736,522 seconds, remainder 9,958,300
1601-01-01 00:00:00 + 13,369,736,522 s = 2024-09-02 07:42:02
the remainder, as seven digits         .9958300
                                       2024-09-02T07:42:02.9958300Z
```

Three things to watch when you compare times from different sources:

- **On disk the time is UTC.** Windows Explorer and many tools show local time: convert before you compare.
- **The precision is 100 ns.** A tool that prints seconds or microseconds has cut the value, so two times that look
  equal there can differ on disk. A Created and a Modified time that are both whole seconds (`.0000000`) are worth a
  look: `timestomp` reports them, because a program that sets times often writes whole seconds.
- **A name can hold an older copy.** The name row of a file whose record is split (a hard link, or a move on a volume
  with hard-link support) keeps its own copy of the four times, refreshed when the file is opened, read and closed through that name; the file's own record holds the
  current ones ([Directory Entries](../structures/directory_entries.md)).

Deeper: [$STANDARD_INFORMATION](../attributes/STANDARD_INFORMATION.md) ·
[Timestomp detection](../concepts/timestomp_detection.md) · [Artifact timeline](../concepts/artifact_timeline.md)
