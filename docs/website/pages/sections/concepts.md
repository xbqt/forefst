How ReFS works — the mechanisms behind the on-disk format, grouped from orientation to deep internals.

**New to ReFS?** Start with **General** — [NTFS vs ReFS](ntfs_comparison.md), [Version Detection](version_detection.md),
and [Version Evolution](version_evolution.md) give you the lay of the land.

For a forensic investigation the load-bearing concepts are the bootstrap and addressing model
([Bootstrap Chain](bootstrap_chain.md), [Virtual Addressing](virtual_addressing.md)), the copy-on-write
update policy that makes history recoverable ([Copy-on-Write](copy_on_write.md)), and the recovery and
timeline techniques ([Deletion Recovery](deletion_recovery.md), [Timestomping Detection](timestomp_detection.md),
[What Survives](what_survives.md)).
