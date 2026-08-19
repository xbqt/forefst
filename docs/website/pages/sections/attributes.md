The per-attribute reference — the metadata an object can carry, by embedded type code.

The ones that matter most forensically: [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) (timestamps, file
attributes, the USN / LastUsn link) and [$DATA](DATA.md) (file content — resident inline or non-resident
extents). Unlike NTFS, ReFS has **no `$FILE_NAME` attribute** — a name is a directory-entry row, not a
per-file attribute — and no 8.3 short-name twin; a directory's child index is the embedded
[$I30_INDEX](I30_INDEX.md). Reparse points (symlinks / junctions), WSL / Linux metadata (`$LX*`), extended
attributes, alternate data streams, stream snapshots, and EFS encryption metadata are documented here too.
