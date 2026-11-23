---
title: "About"
description: "About forefst — an open-source forensic reference and toolset for Microsoft's Resilient File System (ReFS). Tested mainly on ReFS 3.14 volumes, and on 3.4, 3.7, 3.9 and 3.10 (one volume each of 3.7, 3.9 and 3.10; no 3.11–3.13 volume was available)."
---

<p align="center"><img src="https://xbpt.gitlab.io/images/forefst.png" alt="forefst" width="360"></p>

# About this project

This began as my master's thesis at the University of Mons in 2026 — and then kept growing after I handed it
in. I picked ReFS forensics for a simple reason: it's a genuinely interesting file system to take apart, and
the public forensic knowledge about it was years out of date. Most of what you
could find still described ReFS 3.4 from 2018, while a current Windows 11 machine (24H2 and later) already writes
3.14 — so an examiner given a ReFS volume had little published material to rely on.

I wanted to change that: to work out what modern ReFS really puts on disk, and to make that knowledge something
you can read, use, and check for yourself.

The project has three parts that depend on one another:

- a **byte-level reference** to the on-disk format from ReFS 3.4 through 3.14 (plus the Insider builds read,
  29574 and later);
- two **open-source tools** that read a raw image directly;
- the **evidence** behind every claim, recorded claim by claim in a register.

The reference explains what the tools print, the tools apply the reference to an image, and the evidence lets a
reader check both.

Each claim is checked against the decompiled `refs.sys` driver and the raw bytes of a controlled lab image corpus
wherever both can be read, and graded by which of the two supports it. The tools run a fixed set of commands on
every image of that corpus, and any change in what they print must be accounted for.

The **[Methodology](/verification/)** page shows how, and how to trace a claim back to its proof.

A lot of the searching and the code was done with heavy LLM assistance, and the
reviews of the project were language-model sessions too, so mistakes are possible
([how that work is checked](/verification/#llm-assisted-work)). The claim register, the errata and the lab
procedures are public, so if you spot something wrong please [open an issue](https://github.com/xbqt/forefst/issues)
— corrections are genuinely welcome.

Both tools are pure Python (3.7+ standard library, no dependencies) and read a raw disk or partition image with no
driver and no mount.

- **[`forefst.py`](forefst.md)** is the forensic tool — the ReFS counterpart of MFTECmd: a full file listing
  (CSV / body file / JSON), and commands for deleted-file and copy-on-write recovery, the USN and MLog journals,
  super-timelines and timestomp detection (both experimental), security descriptors, reparse points, and stream
  snapshots.
- **[`refsanalysis.py`](refsanalysis.md)** is the structural analyser — it decodes one on-disk structure at a
  time, from the boot sector and superblock to the B+-tree system tables, and includes a boot-sector
  inspect/repair mode.

The tools, the complete claim register, the per-claim proofs of the June 2026 claim audit, and the lab procedures
used to make the corpus images live in the [source repository](https://github.com/xbqt/forefst).

{{< github-note >}}

---

Written by **Baptiste Bonnet** and released under the GNU General Public License v3.0 or later — see
[LICENSE](https://github.com/xbqt/forefst/blob/main/LICENSE).

*This site uses [GoatCounter](https://www.goatcounter.com/) for anonymous, cookie-less visitor counts — no personal data, no cross-site tracking.*
