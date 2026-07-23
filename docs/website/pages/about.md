---
title: "About"
description: "About forefst — an open-source forensic reference and toolset for Microsoft's Resilient File System (ReFS), grown from a 2026 master's thesis by Baptiste Bonnet."
---

# About this project

This reference and its tools come from a master's thesis — *"Forensic analysis of the Resilient File
System (ReFS) version 3.14"* (University of Mons, 2026). The aim was to bring public ReFS forensic
knowledge up to the version shipping today and to give an analyst tooling they can actually run.

*forefst and this reference are the work of **Baptiste Bonnet**.*

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

- **[`forefst.py`](https://github.com/xbqt/forefst/blob/main/forefst.py)** — a forensic file lister,
  the ReFS counterpart of MFTECmd for NTFS: CSV / body-file / JSON output, with deleted-file and
  copy-on-write recovery.
- **[`refsanalysis.py`](https://github.com/xbqt/forefst/blob/main/refsanalysis.py)** — an interactive
  structural analyser: boot / checkpoint / superblock, the B+-tree tables, security, reparse points,
  the USN journal, the durable log, snapshots, timelines, and more.

Both are pure Python (3.7+ standard library, no dependencies) and read a raw image or volume. See the
**[forefst.py](forefst.md)** and **[refsanalysis.py](refsanalysis.md)** pages for usage on this site, or **[the repository](https://github.com/xbqt/forefst)**
to download them.

## Source, full data, and reproducing the analysis

The tools, the complete claim register with its per-claim proofs, and the lab procedures to regenerate
an equivalent image corpus all live in the source repository.

{{< github-note >}}

---

*This site uses [GoatCounter](https://www.goatcounter.com/) for anonymous, cookie-less visitor counts — no personal data, no cross-site tracking.*
