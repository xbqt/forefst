---
title: "About"
description: "About forefst — an open-source forensic reference and toolset for Microsoft's Resilient File System (ReFS), versions 3.4–3.14."
---

<p align="center"><img src="https://xbpt.gitlab.io/images/forefst.png" alt="forefst" width="360"></p>

# About this project

This reference and its two tools grew out of a master's thesis — *"Forensic analysis of the Resilient
File System (ReFS) version 3.14"* (University of Mons, 2026). ReFS is Microsoft's modern, increasingly
deployed file system — the default for Storage Spaces and Dev Drives, and the backbone of large Windows
Server installations — yet the public forensic record had fallen years behind it: the most widely-cited
work still described ReFS 3.4 from 2019, while Windows 11 now ships 3.14. An analyst facing a ReFS volume
had very little to work with. This project re-derives the on-disk format from ReFS 3.4 through 3.14 (plus
an Insider build, 29574) and ships tooling to read it directly — the latest Windows build tested is
26100.8521 (24H2).

The format was reconstructed from two independent directions that had to agree before anything was
accepted: the decompiled `refs.sys` driver — what the code is written to do — and the raw bytes of a
controlled lab image corpus — what a real volume actually contains. Every structural claim carries a
graded piece of evidence and is regression-tested against the whole corpus. The
**[Methodology](verification.md)** page explains exactly how each fact was verified and how to trace any
one of them back to its evidence.

Two tools ship with the reference, both pure Python (3.7+ standard library, no dependencies), reading a
raw image or volume with no driver and no mount. **[`forefst.py`](forefst.md)** is the forensic tool —
the ReFS counterpart of MFTECmd: a full file listing (CSV / body-file / JSON) with deleted-file and
copy-on-write recovery, the USN and MLog journals, super-timelines, timestomp detection, security
descriptors, reparse points, and stream snapshots. **[`refsanalysis.py`](refsanalysis.md)** is the
structural analyser — it decodes one on-disk structure at a time, from the boot sector and superblock to
the B+-tree system tables, and includes a boot-sector inspect/repair mode.

The tools, the complete claim register with its per-claim proofs, and the lab procedures to regenerate an
equivalent image corpus all live in the [source repository](https://github.com/xbqt/forefst).

{{< github-note >}}

---

Written by **Baptiste Bonnet** and released under the GNU General Public License v3.0 or later — see
[LICENSE](https://github.com/xbqt/forefst/blob/main/LICENSE).

*This site uses [GoatCounter](https://www.goatcounter.com/) for anonymous, cookie-less visitor counts — no personal data, no cross-site tracking.*
