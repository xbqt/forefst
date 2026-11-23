# A first examination

You have an image of a ReFS volume and a case to work. This example walks through a first examination in six steps, one
page each, in the order you will meet them, with what `forefst` shows at each step and what not to conclude from it. Each step
ends with the pages that go deeper.

The [Forensic Analysis Workflow](../concepts/forensic_analysis_workflow.md) gives the same examination as a
seven-stage runbook, with the structures behind each stage.

Every example below is real output, from the sample images that ship with the repository
(`analysis/samples/disks/`), so you can run the same commands and compare. Lines are cut where marked `[...]`.

**ReFS has no MFT.** ReFS (the Resilient File System) is built differently from NTFS. There is no `$MFT`, no
`$FILE_NAME` attribute, no short names. All of its metadata is held in **tables**: B+-trees of rows, each row a key
and a value. Each directory is a table whose rows are its entries, and a file is a row in its directory's table.

Three more differences matter in the steps below:

- **Tables are not overwritten in place.** A changed table page is written to a new location (copy-on-write), and
  the old page stays on disk until its space is reused, one of the places where deleted metadata survives (see
  [Look for what was deleted](look_for_deleted_files.md)).
- **Addresses are virtual.** Most cluster numbers in the metadata are translated through a Container Table before
  they mean a place on the disk.
- **The format is versioned.** Windows 10 1803 writes 3.4; Windows 11 24H2 writes 3.14, with 3.7, 3.9 and 3.10 in
  between, so the first thing to establish is which one you have.

On a Windows 11 machine, a ReFS volume may be a *Dev Drive*. Whether it was trusted is kept in that machine's
registry, not on the volume: collect the registry with the image.

Deeper: [What ReFS Is](../concepts/what_is_refs.md) · [NTFS vs ReFS](../concepts/ntfs_comparison.md) ·
[Architecture](../concepts/architecture.md) · [Copy-on-Write](../concepts/copy_on_write.md) ·
[Virtual addressing](../concepts/virtual_addressing.md) · [Version evolution](../concepts/version_evolution.md)

## The six steps

1. [Know the volume](know_the_volume.md)
2. [Identify each file properly](identify_each_file.md)
3. [Read the times with care](read_the_times.md)
4. [Follow the history](follow_the_history.md)
5. [Look for what was deleted](look_for_deleted_files.md)
6. [Check that it is intact](check_integrity.md)

## Where to go next

- To go deeper, each of the other examples follows one task: [a deleted file](find_a_deleted_file.md),
  [a backdated file](detect_timestomping.md), [a hard-link group](read_a_hard_link_group.md),
  [a file across a rename and a move](track_a_file_across_moves.md), and
  [credentials and earlier file versions on one volume](recover_credentials_and_prior_versions.md).
- The [Tool-to-Artifact Map](../tools/tool_artifact_map.md): which command surfaces which artifact.
- The [forefst reference](../tools/forefst.md): every command and option.
- The [glossary](../glossary.md), for the ReFS terms used here.
