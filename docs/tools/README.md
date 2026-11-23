# ReFS Forensic Tools — Reference

Two stdlib-only Python tools read a raw ReFS image directly — no driver, no mount, no Windows.

They are the executable counterpart to this reference: most of what the [structures](../structures/README.md),
[attributes](../attributes/README.md) and [concepts](../concepts/README.md) pages document, these tools read
from the disk.

Both read the ReFS formats 3.4 to 3.14: they read the version from the VBR and pick the layout it needs. They are
validated mainly on 3.14; 3.4, 3.7, 3.9 and 3.10 are read too (no 3.11-3.13 volume was available to test), and some
enriched fields (for example the target of a symlink whose record is split) may be incomplete on 3.4-3.10.

Both translate virtual cluster addresses through the Container Table
([virtual-address translation](../concepts/virtual_addressing.md)); without it, the bytes read would belong to other
data. Content carved for a deleted file can still come from clusters reused since.

## The two tools, and when to use which

| Tool | What it is | Reach for it when you want… |
|------|------------|------------------------------|
| **[forefst.py](forefst.md)** | The **forensic tool** — a per-file metadata lister for ReFS, plus commands for recovery, logs and timelines. | a CSV / [body-file](forefst.md#body-file-format) / JSON listing of every file (MACB, sizes, owner+group SID, attributes) · deleted-file & CoW recovery · the USN journal, MLog, super-timelines and timestomp detection (these two are experimental), file extraction, security descriptors, reparse points, snapshots, integrity checking, and metadata export |
| **[refsanalysis.py](refsanalysis.md)** | The **structure / lab tool** — decode one on-disk structure at a time. | to inspect the VBR, superblock, checkpoint, object/schema/container/parent-child tables, the allocators, the upcase table, or a lab-format file/attribute view — or to check the boot-sector and superblock copies and restore a failing one from a good one (`bootedit repair`) |

In short: **`forefst.py` for everything file- and forensics-related (triage, timeline, recovery, logs);
`refsanalysis.py` to drill into one on-disk structure.**

For "which command surfaces artifact X", see the [Tool-to-Artifact Map](tool_artifact_map.md). What an
`export metadata` bundle holds, and what it leaves out, is on [Metadata bundle](metadata_bundles.md).

How the two tools are built, and which driver behaviour each step follows: [Internals](internals.md).

## `forefst.py` subcommands

`forefst.py <image> <subcommand> [options]` (the default subcommand is `summary`).

| Group | Subcommands |
|-------|-------------|
| **Listing & triage** | `files` (+`--filter`) · `summary` · `search` · `details` (one object) · `specials` (special-attribute files — WSL / reparse / ADS discovery) · `ads` (named streams; a shortcut for `specials ads`) |
| **Change history** | `usn` ([USN Journal](../structures/usn_journal.md)) · `mlog` ([MLog](../structures/mlog.md)) · `timeline` ([Artifact Timeline](../concepts/artifact_timeline.md)) · `timestomp` ([Timestomping Detection](../concepts/timestomp_detection.md)) |
| **Recovery & content** | `extract` · `deleted` ([Deletion Recovery](../concepts/deletion_recovery.md)) · `recyclebin` (`$RECYCLE.BIN` `$I` metadata) · `snapshots` ([Snapshots](../concepts/snapshots_versioning.md)) · `dataruns` |
| **Security & metadata** | `security` ([Security Descriptors](../structures/security_descriptors.md)) · `reparse` ([Reparse Points](../structures/reparse_points.md)) · `integrity` ([Integrity Streams](../concepts/integrity_streams.md)) · `export` · `verify-bundle` (check an `export metadata` bundle) |

`details` addresses a file by path or by its FileRef (`--id HomeOID:FileID`), and a directory or system object by path
or OID.

## `refsanalysis.py` subcommands

`refsanalysis.py <image> <subcommand> [options]` (the default subcommand is `summary`).

| Group | Subcommands |
|-------|-------------|
| **Quick analysis** | `summary` · `summary++` · `all` |
| **File-system content** | `files` · `attributes` · `details` (lab-format views) |
| **Structure analysis** | `boot` ([VBR](../structures/vbr.md)) · `supb` ([SUPB](../structures/supb.md)) · `chkp` ([CHKP](../structures/chkp.md)) · `objects` ([Object Table](../structures/object_table.md)) · `schema` ([Schema Table](../structures/schema_table.md)) · `parentchild` ([Parent-Child](../structures/parent_child_table.md)) · `containers` ([Container Table](../structures/container_table.md)) · `allocators` (allocator tables: free / used space) · `upcase` ([Upcase](../structures/upcase_table.md)) · `oid30` |
| **Repair** | `bootedit` — `[DANGEROUS]` VBR read / export / repair / set / import / sparse |
| **forefst passthrough** | `forefst <cmd>` — runs a forefst command on the image |

Per-subcommand flags and examples are on the [forefst.py](forefst.md) and [refsanalysis.py](refsanalysis.md)
pages, or from each tool's built-in `--help` (`forefst.py <image> <cmd> --help`). What the tools do not read or do not
check in this release, with what to do: [Known issues in 1.14.0](known_issues.md). What a script that reads their
output must change from one release to the next: [Migrating between releases](migration.md).

## Constraints and provenance

Both tools are **Python 3.7+ stdlib only** (no third-party dependencies).

What they write:

- `forefst.py` never writes to the image; its exports write to a directory you name.
- `refsanalysis.py` only reads, except three `bootedit` commands: `repair` (when it restores a copy or fixes the boot
  sector), `set` and `import`. These write to a sparse copy by default, and to the original image only with
  `--inplace`.

Work on a copy of the evidence regardless.

They are exercised across the same corpus the reference rests on. Every release runs a fixed set of commands on every
image of that corpus (129 disk images for 1.14.0):

- 36 `forefst.py` command lines (the `files` listings, `summary`, `deleted`, the USN and MLog commands, `timeline`,
  `timestomp`, `integrity` and others, most in text and JSON) and 17 `refsanalysis.py` ones;
- `extract` and `details` (text and JSON) of chosen files, `export resident-all` and `snapshots --extract`;
- `deleted --full` and `export deleted --carve` on a listed part of the corpus (`deleted --full` reads the whole
  volume).

Each command's output and exit code are compared with a committed baseline, so an unintended change in the output
of those commands is caught; a command or an option outside the set is not covered.

That is a REGRESSION guarantee (the output did not change unnoticed), not a proof of correctness: it cannot detect an
answer that has been wrong since the baseline was taken.

Where a claim is independently checked against ground truth this codebase did not produce, the page says so — see
[how this was verified](../methodology.md).

Worked, image-specific runs of these tools are in [examples](../examples/README.md).
