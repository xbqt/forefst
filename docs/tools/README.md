# ReFS Forensic Tools — Reference

Two stdlib-only Python tools read a raw ReFS image directly — no driver, no mount, no Windows. They are
the executable counterpart to this reference: everything the [structures](../structures/README.md),
[attributes](../attributes/README.md), and [concepts](../concepts/README.md) pages document, these tools
parse off the disk. Both run version-agnostically across ReFS v3.4 → v3.14 (they read the version from the
VBR and pick the right layout), and both perform the mandatory [virtual-address translation](../concepts/virtual_addressing.md)
so the bytes they report are the file's actual content.

## The two tools, and when to use which

| Tool | What it is | Reach for it when you want… |
|------|------------|------------------------------|
| **[forefst.py](forefst.md)** | The **unified forensic tool** — the ReFS equivalent of MFTECmd for NTFS, plus a full forensic suite. | a CSV / [body-file](forefst.md) / JSON listing of every file (MACB, sizes, owner+group SID, attributes) · deleted-file & CoW recovery · the USN journal, MLog, super-timelines, timestomp detection, file extraction, security descriptors, reparse points, snapshots, integrity checking, and metadata export |
| **[refsanalysis.py](refsanalysis.md)** | The **structure / lab tool** — decode one on-disk structure at a time. | to inspect the VBR, superblock, checkpoint, object/schema/container/parent-child tables, the upcase table, or a lab-format file/attribute view — or to repair a damaged VBR |

Rule of thumb: **`forefst.py` for everything file- and forensics-related (triage, timeline, recovery, logs);
`refsanalysis.py` to drill into one on-disk structure.** For "which command surfaces artifact X", see the
[Tool-to-Artifact Map](../concepts/tool_artifact_map.md).

## `forefst.py` subcommands

`forefst.py <image> <subcommand> [options]` (the default subcommand is `files`).

| Group | Subcommands |
|-------|-------------|
| **Listing & triage** | `files` (+`--filter`) · `summary` · `search` · `details` (any file/object by path or OID) · `specials` (special-attribute files — WSL / reparse / ADS discovery) |
| **Change history** | `usn` ([USN Journal](../structures/usn_journal.md)) · `mlog` ([MLog](../structures/mlog.md)) · `timeline` ([Artifact Timeline](../concepts/artifact_timeline.md)) · `timestomp` ([Timestomping Detection](../concepts/timestomp_detection.md)) |
| **Recovery & content** | `extract` · `deleted` ([Deletion Recovery](../concepts/deletion_recovery.md)) · `recyclebin` (`$RECYCLE.BIN` `$I` metadata) · `snapshots` ([Snapshots](../concepts/snapshots_versioning.md)) · `dataruns` |
| **Security & metadata** | `security` ([Security Descriptors](../structures/security_descriptors.md)) · `reparse` ([Reparse Points](../structures/reparse_points.md)) · `integrity` ([Integrity Streams](../concepts/integrity_streams.md)) · `export` |

## `refsanalysis.py` subcommands

`refsanalysis.py <image> <subcommand> [options]` (the default subcommand is `summary`).

| Group | Subcommands |
|-------|-------------|
| **Quick analysis** | `summary` · `summary++` · `all` |
| **File-system content** | `files` · `attributes` · `details` (lab-format views) |
| **Structure analysis** | `boot` ([VBR](../structures/vbr.md)) · `supb` ([SUPB](../structures/supb.md)) · `chkp` ([CHKP](../structures/chkp.md)) · `objects` ([Object Table](../structures/object_table.md)) · `schema` ([Schema Table](../structures/schema_table.md)) · `parentchild` ([Parent-Child](../structures/parent_child_table.md)) · `containers` ([Container Table](../structures/container_table.md) + allocators) · `upcase` ([Upcase](../structures/upcase_table.md)) · `oid30` |
| **Repair** | `bootedit` — `[DANGEROUS]` VBR read / export / repair / set / import / sparse |

Per-subcommand flags and examples are on the [forefst.py](forefst.md) and [refsanalysis.py](refsanalysis.md)
pages, or from each tool's built-in `--help` (`forefst.py <image> <cmd> --help`).

## Constraints and provenance

Both tools are **Python 3.6+ stdlib only** (no third-party dependencies) and operate read-only on a copy
of the image. They were validated across the same corpus the reference rests on — see
[how this was verified](../methodology.md). Worked, image-specific runs of these tools are in
[examples](../examples/README.md).
