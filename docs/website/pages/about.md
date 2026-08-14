---
title: "About"
description: "About forefst — an open-source forensic reference and toolset for Microsoft's Resilient File System (ReFS), versions 3.4–3.14."
---

<p align="center"><img src="https://xbpt.gitlab.io/images/forefst.png" alt="forefst" width="360"></p>

# About this project

This reference and its tools come from a master's thesis — *"Forensic analysis of the Resilient File
System (ReFS) version 3.14"* (University of Mons, 2026). The aim was to bring public ReFS forensic
knowledge up to the version shipping today and to give an analyst tooling they can actually run.

## Why it exists

ReFS is Microsoft's modern, increasingly deployed file system: it is the default for Storage Spaces
and Dev Drives and underlies large Windows Server deployments. Yet open forensic documentation and
tooling lagged years behind the format — the most widely-cited public work described ReFS 3.4 (2019),
while Windows 11 now ships 3.14. An investigator facing a ReFS volume had little to work with. This
project re-derives the on-disk structures up to ReFS 3.14 (plus an Insider build, 29574) and ships two
tools to parse them.

## How it was built

The format was reconstructed from two independent directions, so that neither stands alone:

- **Static analysis** of the `refs.sys` driver across several Windows builds — Windows 10 (v3.4),
  Windows 11 24H2 (v3.14), and an Insider build (v3.14+) — using the public PDB symbols to read the
  decompiled code that writes and reads each structure.
- **Raw-disk analysis** of a controlled corpus of ReFS images generated in a lab across versions,
  cluster sizes, checksum types, and feature configurations — comparing what the driver code *says*
  with what actually lands on disk.

## Coverage

The reference and tools are validated against **ReFS 3.4 through 3.14**; the latest Windows build tested
is **26100.8521 (24H2)**. All versions parse; the richest enrichment is on 3.10+ and 3.14.

## How it was verified

![The verification loop](verification-loop.svg)

Every structural claim was cross-checked before it was accepted: it had to hold both in the driver
code and in the real disk bytes, and the tools are regression-tested against the whole image corpus.

Behind each statement is a small **confidence grade**, recorded in the source repository so any fact
can be audited later:

- **String literal** — the driver binary names the structure or field directly.
- **Decompiled code** — read from the reverse-engineered driver, tied to a specific Windows build.
- **Structural inference** — deduced from call graphs and observed patterns; the weakest grade, and
  always corroborated before use.
- **Raw-disk** — observed physically on the image corpus, independent of the code.

A fact is strongest when the code and the disk agree. (In the repository these grades are written
`E1`–`E3` and `RD`.) They are an analysis aid and are deliberately kept off the reference pages, which
simply state what was established. See the **[Methodology](verification.md)** page for how every claim was
verified, and how to follow any one of them to its evidence.

## The tools

- **[`forefst.py`](https://github.com/xbqt/forefst/blob/main/forefst.py)** — the forensic tool, the
  ReFS counterpart of MFTECmd for NTFS: a full file listing (CSV / body-file / JSON) plus deleted-file and
  copy-on-write recovery, the USN and MLog journals, super-timelines, timestomp detection, security
  descriptors, reparse points, and stream snapshots.
- **[`refsanalysis.py`](https://github.com/xbqt/forefst/blob/main/refsanalysis.py)** — an interactive
  structural analyser: it decodes one on-disk structure at a time — the boot sector, superblock, and
  checkpoint; the object, schema, container, and parent-child tables; the upcase table — and includes a
  boot-sector inspect/repair mode.

Both are pure Python (3.7+ standard library, no dependencies) and read a raw image or volume. See the
**[forefst.py](forefst.md)** and **[refsanalysis.py](refsanalysis.md)** pages for usage on this site, or **[the repository](https://github.com/xbqt/forefst)**
to download them.

## Source, full data, and reproducing the analysis

The tools, the complete claim register with its per-claim proofs, and the lab procedures to regenerate
an equivalent image corpus all live in the source repository.

{{< github-note >}}

---

Written by **Baptiste Bonnet** and released under the GNU General Public License v3.0 or later — see
[LICENSE](https://github.com/xbqt/forefst/blob/main/LICENSE).

*This site uses [GoatCounter](https://www.goatcounter.com/) for anonymous, cookie-less visitor counts — no personal data, no cross-site tracking.*
