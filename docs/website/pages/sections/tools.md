Two open-source, pure-Python tools that read a raw ReFS image directly — no driver, no mount, no
dependencies — plus worked, end-to-end examples against real disk images.

**forefst.py** is the forensic tool, the ReFS answer to MFTECmd: a full file listing (CSV / body file /
JSON) with deleted-file and copy-on-write recovery, the USN and MLog journals, super-timelines, timestomp
detection, security descriptors, reparse points, and stream snapshots. **refsanalysis.py** is the
structural analyser — it decodes one on-disk structure at a time (boot sector, superblock, checkpoint, the
B+-tree system tables, the upcase table, and more) and includes a boot-sector inspect/repair mode, for
learning the format and validating the forensic tool against new ReFS builds. The **Examples** below are
step-by-step forensic walkthroughs.
