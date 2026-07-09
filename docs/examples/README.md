# Examples

Worked investigator walkthroughs and raw tool dumps. The walkthroughs pair a goal → tool command → annotated
output → byte-level reasoning → cross-references, so an analyst can follow a real ReFS task end to end.

## Worked examples

| Example | Goal |
|---------|------|
| [decode_vbr_by_hand.md](decode_vbr_by_hand.md) | Read every VBR field from a hexdump → version, cluster size, checksum algorithm, container size (no tool) |
| [find_a_deleted_file.md](find_a_deleted_file.md) | Run the deletion-recovery methods (Trash Table, orphan scan, OID density, CoW prior-content) on one image |
| [detect_timestomping.md](detect_timestomping.md) | Cross `$SI` change-time vs USN journal vs volume-creation bound to flag a tampered timestamp |
| [read_a_hard_link_group.md](read_a_hard_link_group.md) | Resolve every name of one physical object via the home-backref + child-ordinal + content fingerprint |
| [identify_native_vs_upgraded.md](identify_native_vs_upgraded.md) | Classify volume state from CHKP flags (0x002 / 0x602 / 0x682) and the immutable VBR format-time fields |

## Raw tool dumps

Reference output of the tools on known images (for comparison when validating your own parse):
`vbr_win10.txt`, `vbr_win11.txt`, `schema_win11.txt`, `summary_win10.txt`, `summary_win11.txt`.

The volumes behind these dumps are described in [test_baseline_images.md](../test_baseline_images.md).

See also: [forensic analysis workflow](../concepts/forensic_analysis_workflow.md) ·
[tool → artifact map](../concepts/tool_artifact_map.md) · [root index](../README.md)
