# $BITMAP

`$BITMAP` is **not** a ReFS per-file attribute. No object carries a `$BITMAP` attribute and there is no
`$BITMAP` type code in the attribute set — the string appears only as a diagnostic/debug label. An
analyst arriving from NTFS, where `$Bitmap` (MFT entry 6) is the volume free-space map, will look for an
equivalent attribute here and find none.

The role NTFS gives to `$Bitmap` is played in ReFS not by an attribute but by the **three-tier
allocator**. Free and allocated clusters are tracked by the allocator tables (Medium / Container /
Small), whose on-disk row is a 24-byte header followed by a 2,048-byte bitmap — 1 bit per cluster,
`1 = allocated`, with the invariant `free_count = range_length − popcount(bitmap)`. That row layout is
documented in full on the [Allocators](../structures/allocators.md) structure page, and the conceptual
model — how the three tiers divide the volume and how the recently-deallocated set widens the carving
window — is on [Space Allocation](allocation_space_mgmt.md).

## Cross-references

- [Allocators](../structures/allocators.md) — the allocator bitmap row layout (the real free-space map)
- [Space Allocation](allocation_space_mgmt.md) — the three-tier allocator concept and its forensic use
- [NTFS vs ReFS](ntfs_comparison.md) — why NTFS's `$Bitmap` has no ReFS attribute counterpart

## Evidence

That no `$BITMAP` per-file attribute exists is raw-disk confirmed: no `$BITMAP` type code appears in the
attribute census across the corpus. The allocator bitmap row it is commonly confused with is decompiled
(E2) and raw-disk decoded (RD) on the [Allocators](../structures/allocators.md) page. See
[how this was verified](../methodology.md).
