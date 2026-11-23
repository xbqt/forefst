# Driver builds analysed

Every structural claim on this site is checked against the `refs.sys` driver as well as against disks. This
page records **which builds of that driver have been read**, how each was read, and which test volumes each is known
to have written.

It matters for two reasons:

- A feature visible on disk has a code path that created it, so knowing which builds were examined tells you how far
  the evidence reaches.
- When Microsoft services the driver, an examiner needs to know only one thing: whether anything changed in how a
  volume is written or read.

For every Windows 11 26100 build below, nothing did: the changes are servicing work, and the on-disk format is
untouched. The Insider builds change how a few records are written. What changed in each build, and what it means
for reading a volume, is on [Driver Evolution](../concepts/driver_evolution.md).

## The builds

Two kinds of evidence reach a driver build, and the table keeps them apart:

- **Read** is the static evidence: the driver's code, decompiled with Microsoft's published symbols (so the functions
  named on this site are the driver's own names), or, where no symbols are published, compared by its machine code
  with the nearest build that has them.
- **Volumes it wrote** is the disk evidence: test volumes known to have been written by that build.

A volume does not record which build wrote it (it keeps the driver's ReFS version, 3.14 or 3.15, not its build
number), so this column names only volumes whose build was recorded when they were made.

| Windows | ReFS format | Driver version | Read | Volumes it wrote in the test corpus | Notable |
|---|---|---|---|---|---|
| Windows 10 1803 | 3.4 | `10.0.17134.1` | decompiled, symbols | the 3.4 volumes were formatted by Windows 10 1803; the servicing build is not recorded | The v3.4 baseline. Main data never inline, no backing records. |
| Windows 11 21H2 / 22H2 / 23H2 | 3.7 / 3.9 / 3.10 | 22000 / 22621 / 22631 | not read | the 3.7 and 3.9 volumes (formatted fresh by 22000 and 22621) and the 3.10 volumes (a 3.10 format's boot-sector flags); the servicing builds are not recorded | These formats are checked on disk only. |
| Windows 11 24H2 | 3.14 | `10.0.26100.8115` | decompiled, symbols | none recorded | The v3.14 reference used throughout this site. |
| Windows 11 24H2 | 3.14 | `10.0.26100.8521` | decompiled, symbols | none recorded | A fix found by fuzzing; two feature flags graduated. |
| Windows 11 24H2 | 3.14 | `10.0.26100.8972` | decompiled, symbols | none recorded | The largest servicing change in this range. |
| Windows 11 24H2 | 3.14 | `10.0.26100.9444` | decompiled, symbols | none recorded | A security fix in the memory-mapped read path. |
| Windows 11 24H2 | 3.14 | `10.0.26100.9549` | decompiled, symbols | two lab volumes (the change-journal and EFS experiments); their logs are evidence, the volumes are not in the test corpus | No code change from .9444. |
| Windows 11 (26100 line) | 3.14 | `10.0.26100.9711` | decompiled, symbols | the volumes of the hard-link and move experiments | A mount policy for external disks; input validation. |
| Windows 11 (26100 line) | 3.14 | `10.0.26100.9818` | decompiled, symbols | none (it read one lab volume, read-only) | A merge on deletion is paced and retried. |
| Windows 11 (26100 line) | 3.14 | `10.0.26100.9974` | machine code compared with .9818 (no symbols published) | none recorded | One function changed. |
| Windows Insider | 3.14 | `10.0.29574.1000` | decompiled, symbols | the volumes an Insider build formatted or mounted; which Insider build is not recorded | Subsystems absent from production 24H2. |
| Windows Insider | 3.14 | `10.0.29659.1000` | decompiled, symbols | none recorded | Widely rebuilt; one replay test changed. |
| Windows Insider | 3.14 | `10.0.29683.1000` | decompiled, symbols | none recorded | Logs a table deletion with a new record number. |

The main data of a v3.4 volume is always in extents (a named stream can be inline), and the v3.4 volumes measured hold
no backing record.

So a fact this site states for a build is a reading of that build's code; it was also seen on a volume that build
wrote only for the builds whose column above names volumes. Whether a fact was also measured on the test corpus as a
whole, whatever wrote it, is counted per area and format in [Format Support](../format_support.md).

## Cross-references

- [Driver Evolution](../concepts/driver_evolution.md): what changed from one build to the next, and the
  functions that change a file's storage
- [Version Evolution](../concepts/version_evolution.md): the on-disk formats
- [Format Support](../format_support.md): which ReFS formats each area's statements were confirmed on
