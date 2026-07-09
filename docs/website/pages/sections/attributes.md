The per-attribute reference — the metadata an object can carry, by embedded type code.

The ones that matter most forensically: [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) (timestamps,
file attributes, the USN / LastUsn link), [$DATA](DATA.md) (file content — resident inline or
non-resident extents), $FILE_NAME, and $INDEX_ROOT. Reparse points
(symlinks / junctions), WSL / Linux metadata (`$LX*`), extended attributes, and EFS encryption metadata
are documented here too.
