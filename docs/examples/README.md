# Examples

Investigator walkthroughs and raw tool dumps.

Each walkthrough pairs a goal → tool command → annotated output → byte-level reasoning → cross-references, so an
analyst can follow a real ReFS task end to end.

Every command runs on a named image of the test corpus, and its output is re-run against the development tool before
a release.

## Start here

| Example | Goal |
|---------|------|
| [first_examination.md](first_examination.md) | A first examination, in six pages read in order: |
| [know_the_volume.md](know_the_volume.md) | 1. Know the volume: version, redundant copies, files and names, the change journal |
| [identify_each_file.md](identify_each_file.md) | 2. Identify each file properly: its reference, its record placement and data residency |
| [read_the_times.md](read_the_times.md) | 3. Read the times with care: the four times, one decoded by hand, and what to watch |
| [follow_the_history.md](follow_the_history.md) | 4. Follow the history: the change journal and the MLog |
| [look_for_deleted_files.md](look_for_deleted_files.md) | 5. Look for what was deleted: where deleted metadata lingers, and what can be recovered |
| [check_integrity.md](check_integrity.md) | 6. Check that it is intact: metadata checksums, integrity streams, exit codes |

## To go deeper

| Example | Goal |
|---------|------|
| [find_a_deleted_file.md](find_a_deleted_file.md) | Run the deletion-recovery methods (Trash Table, checkpoint comparison, node-slack scan, orphan-page scan; stream snapshots where a volume has them) on one image |
| [detect_timestomping.md](detect_timestomping.md) | Find back-dated files and corroborate each with the USN journal or a second hard-link name |
| [read_a_hard_link_group.md](read_a_hard_link_group.md) | Resolve every name of one physical object via the home back-reference + child ordinal, checked by size and the backing's back-pointers |
| [track_a_file_across_moves.md](track_a_file_across_moves.md) | Follow one file through a rename and a cross-directory move — the FileRef `(HomeOID, FileID)` stays fixed while name and parent change |
| [identify_native_vs_upgraded.md](identify_native_vs_upgraded.md) | Classify volume state from CHKP flags (0x002 / 0x602 / 0x682) and the VBR fields an upgrade leaves unchanged |
| [read_wsl_files.md](read_wsl_files.md) | Find the files WSL wrote and read their Linux type, mode, owner and device number, by reparse tag and by EA |
| [read_the_change_journal.md](read_the_change_journal.md) | Know how far back the change journal reaches, whether it has wrapped, and which records came after the last checkpoint |
| [recover_credentials_and_prior_versions.md](recover_credentials_and_prior_versions.md) | One investigation end to end — recover deleted and renamed credential files, list every alternate data stream, read a file's earlier versions from its snapshots, and see where carving fails |

## By hand

| Example | Goal |
|---------|------|
| [decode_vbr_by_hand.md](decode_vbr_by_hand.md) | Read every VBR field from a hexdump → version, cluster size, checksum algorithm, container size (no tool) |

## Raw tool dumps

Reference output of the tools on known images (for comparison when validating your own parse):
`vbr_win10.txt`, `vbr_win11.txt`, `schema_win11.txt`, `summary_win10.txt`, `summary_win11.txt` -- the standard
output of refsanalysis 1.14.0: `boot` and `summary` on `win10refs2tspecials` (ReFS 3.4) and `win11refs2tspecials`
(ReFS 3.14), `schema` on `win11refs2tspecials`.

The volumes behind these dumps are described in [test_baseline_images.md](../test_baseline_images.md).

See also: [forensic analysis workflow](../concepts/forensic_analysis_workflow.md) ·
[tool → artifact map](../tools/tool_artifact_map.md) · [root index](../README.md)
