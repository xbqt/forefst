---
title: "About"
description: "About forefst — an open-source forensic reference and toolset for Microsoft's Resilient File System (ReFS), versions 3.4–3.14."
---

<p align="center"><img src="https://xbpt.gitlab.io/images/forefst.png" alt="forefst" width="360"></p>

# About this project

This began as my master's thesis at the University of Mons in 2026 — and then kept growing after I handed it
in. I picked ReFS forensics for a simple reason: it's a genuinely interesting file system to take apart, and
the public forensic knowledge about it had quietly fallen years behind the file system itself. Most of what you could find still described ReFS 3.4 from 2019, while the Windows 11 machine on
your desk is already writing 3.14 — so anyone handed a ReFS volume to examine was largely on their own. I
wanted to change that: to work out what modern ReFS really puts on disk, and to make that knowledge something
you can read, use, and check for yourself.

So the project is really three things that lean on one another — a **byte-level reference** to the on-disk
format from ReFS 3.4 through 3.14 (plus an Insider build, 29574), two **open-source tools** that read a raw
image directly, and the **evidence** behind every claim. The reference makes the tools explainable, the tools
make the reference useful, and the evidence makes both auditable. That is the whole idea.

Nothing here is taken on trust. Every structural fact had to line up from two independent directions before I
accepted it: the decompiled `refs.sys` driver — what the code is written to do — and the raw bytes of a
controlled lab image corpus — what a real volume actually contains. Each claim carries a graded piece of
evidence and is regression-tested across the whole corpus. The **[Methodology](verification.md)** page shows
exactly how a fact travels from a hypothesis to a verified entry, and how to trace any one of them back to its
proof.

I'll be upfront about one thing: a lot of the searching and the code was done with heavy LLM assistance. That
let me cover far more ground — thousands of decompiled functions, a hundred-plus images — but it also means
mistakes are possible. Everything load-bearing was confirmed on both the code and the disk before it went in,
and all of the evidence is public, so if you spot something wrong please
[open an issue](https://github.com/xbqt/forefst/issues) — corrections are genuinely welcome.

Both tools are pure Python (3.7+ standard library, no dependencies) and read a raw image or volume with no
driver and no mount. **[`forefst.py`](forefst.md)** is the forensic tool — the ReFS counterpart of MFTECmd: a
full file listing (CSV / body-file / JSON) with deleted-file and copy-on-write recovery, the USN and MLog
journals, super-timelines, timestomp detection, security descriptors, reparse points, and stream snapshots.
**[`refsanalysis.py`](refsanalysis.md)** is the structural analyser — it decodes one on-disk structure at a
time, from the boot sector and superblock to the B+-tree system tables, and includes a boot-sector
inspect/repair mode.

The tools, the complete claim register with its per-claim proofs, and the lab procedures to regenerate an
equivalent image corpus all live in the [source repository](https://github.com/xbqt/forefst).

{{< github-note >}}

---

Written by **Baptiste Bonnet** and released under the GNU General Public License v3.0 or later — see
[LICENSE](https://github.com/xbqt/forefst/blob/main/LICENSE).

*This site uses [GoatCounter](https://www.goatcounter.com/) for anonymous, cookie-less visitor counts — no personal data, no cross-site tracking.*
