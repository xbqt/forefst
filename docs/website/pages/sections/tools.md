Two open-source, pure-Python tools that read a raw ReFS image directly — no driver, no mount, no
dependencies — plus worked, end-to-end examples against real disk images.

- **forefst.py** is the forensic tool, the ReFS counterpart of MFTECmd: a full file listing (CSV / body file / JSON),
  and commands for deleted-file and copy-on-write recovery, the USN and MLog journals, super-timelines and timestomp
  detection (both experimental), security descriptors, reparse points, and stream snapshots.
- **refsanalysis.py** is the structural analyser — it decodes one on-disk structure at a time (boot sector,
  superblock, checkpoint, the B+-tree system tables, the upcase table, and more) and includes a boot-sector
  inspect/repair mode, for learning the format. It imports its parsing layer from forefst.py.
- Beside the two help pages: the internals of forefst.py, migrating between releases, the known issues of this
  release, and the list of releases.

The **Examples** below are step-by-step forensic walkthroughs: a first examination, then deeper ones, and a boot
sector decoded by hand.
