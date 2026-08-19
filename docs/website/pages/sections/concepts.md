How ReFS works — the mechanisms behind the on-disk format, from first principles to deep internals.

**Background & context** sets the scene: what a file system is, where ReFS sits in the Windows I/O path, and
Carrier's five data categories that organise every artifact. **General** orients you to ReFS itself — how it
differs from NTFS, how to read a volume's version, and the two-layer driver that produces everything on disk.
**On-disk mechanics** is the load-bearing model: the bootstrap chain, virtual addressing, clusters and pages,
resident vs non-resident storage, and the copy-on-write policy that makes history recoverable. **Integrity &
redundancy** covers the checksums, integrity streams, and failover copies that detect and heal corruption.
**Files, metadata & features** is object and file identity, attributes, hard links, stream snapshots, WSL
metadata, compression, deduplication, and tiering. **Forensics & recovery** is the payoff — deletion recovery,
what survives, timestomp detection, timeline reconstruction, and how the tools map to each artifact.
