How ReFS works — the mechanisms behind the on-disk format, from first principles to deep internals.

- **Background & context** covers what a file system is, where ReFS sits in the Windows I/O path, what ReFS
  is and why Microsoft built it, and Carrier's five data categories that organise every artifact.
- **General** orients you to ReFS itself — how it differs from NTFS, how to read a volume's version, and the
  two-layer driver that produces everything on disk.
- **On-disk mechanics** is the core model: the bootstrap chain, virtual addressing, clusters and pages,
  inline vs extent storage, and the copy-on-write policy that makes history recoverable.
- **Integrity & redundancy** covers the checksums that detect corruption, the integrity streams that protect file
  data, and the redundant copies the driver reads when one fails and repairs from.
- **Files, metadata & features** is object and file identity, attributes, hard links, stream snapshots, WSL
  metadata, compression, deduplication, and tiering.
- **Forensics & recovery** applies all of this: deletion recovery, what survives, timestomp detection, timeline
  reconstruction, the analysis workflow, and how the tools map to each artifact.
