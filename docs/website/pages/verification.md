---
title: "Methodology"
description: "How the ReFS on-disk facts in this reference were checked — against the driver code and the raw disk wherever both can be read — how each is graded, and the evidence published on GitHub."
---

# How these ReFS facts were verified

This reference decodes what ReFS actually writes to disk. Each byte-level claim on the structure,
attribute, and concept pages is checked against **two independent sources** wherever both can be read, and the
claim register records, finding by finding, which of them supports it — so you can see what a claim rests on,
and audit the evidence yourself.

## Two independent sources, wherever both can be read

Each claim is checked against the **decompiled `refs.sys` driver** (what the code is written to do) and the
**raw on-disk bytes** (what a real volume actually contains), as far as both can be read.

Where only one can — a code path no image here exercises, a format with no driver of its own to read — or where
the claim is an inference, the claim rests on what there is, and the register records which source supports it.

Code alone can mislead (dead paths, version drift); one disk image alone can mislead (it is not the whole
population). Both, across many images and several Windows builds, is what makes a claim trustworthy, and it is the
aim for every claim.

## Where the facts come from

The facts rest on two bodies of evidence — the **driver**, read statically, and a **lab corpus of real
volumes**, read byte by byte — plus a central register that records, for every claim, the result of each check
(including "not tested").

### Versions tested

**The driver, read statically.** `refs.sys` is decompiled with its public PDB symbols where Microsoft publishes
them; Microsoft's `refsutil` (Windows 10 and Windows 11) was decompiled alongside as a cross-check.

- The builds read: Windows 10 1803 (17134, format 3.4), eight builds of the Windows 11 26100 line (26100.8115 to
  26100.9974, format 3.14) and three Insider builds (29574, 29659 and 29683).
- The formats 3.7, 3.9 and 3.10 are read on disk only: the drivers of their Windows releases are not held.
- The list, with how each build was read and the volumes each is known to have written, is on
  [Driver builds analysed](/verification/driver_builds/).

**The volumes, read byte by byte.** A controlled corpus of 124 readable ReFS images (97 distinct once
byte-identical copies are set aside).

- The **3.14** volumes include volumes formatted at 3.14 and volumes upgraded to it from 3.4 and 3.9.
- The intermediate formats (**3.7, 3.9, 3.10**) are one volume each, validated on disk only.
- **Both cluster sizes** (4 KiB and 64 KiB) are exercised on 3.4 and 3.14; the 3.7, 3.9 and 3.10 volumes use
  4 KiB.
- The **metadata checksum** is CRC64 on every format, and SHA-256 on four 3.14 volumes formatted with it.
- Five unreadable images — three NTFS volumes and two BitLocker-encrypted ReFS volumes — are kept as negative
  controls, to catch false positives.

### The register

Beyond those two bodies of evidence, a **central claim register** records the findings as rows — each with its
finding ID, both checks and an evidence grade — so a claim resolves to the code, the disk, or both behind it. The
byte-level master reference and the errata complete it, and an erratum overrides both.

## Confidence grades

A finding carries a grade on each axis that was checked — kept off the reference pages themselves and recorded with the finding
(written `E1`–`E3` and `RD` in the register):

- **String** (`E1`) — the driver binary names the structure or field.
- **Decompiled** (`E2`) — read from the reverse-engineered driver code.
- **Inference** (`E3`) — deduced from the code but not stated outright; the weakest grade, always
  corroborated before use.
- **Raw-disk** (`RD`) — measured physically on the image corpus, independent of the code.

A fact is strongest when the code and the disk agree.

## How corrections are recorded

The analysis revised both prior work and itself. Where a fact changed, the correction is recorded as an
erratum and folded into the register and the pages, which state **only** the current value; the history lives in
the repository, not in the prose. Where a page still disagrees with an erratum, the erratum is right, and the page
is a bug worth reporting.

## How the method grew

The method above was not complete when the work began. It grew in six steps, each added after a kind of error got
through the steps before it.

**Two readings of one structure.** The work began as a master's thesis. Every structural claim the earlier
literature made was written down as something to test. The driver was read first: `refs.sys` decompiled with
its public symbols, giving the functions, the classes, the field offsets and the paths that differ between
versions. That map was then checked against the bytes of lab volumes made for the purpose, and every new question
the bytes raised went back to the driver.

One example: schema 0xe130, which the literature had not named, was present on a 3.14 volume and absent on 3.4. Volumes
formatted by the Windows versions in between date it to format 3.10 (absent on 3.7 and 3.9, present from 3.10), and the
driver function that creates it, `CmsVolumeHeatEngine::Initialize`, names it: the heat engine's table. This step
catches a claim the code or the bytes do not bear out.

**One protocol for every claim.** The errors that survived the thesis shared one cause: a layout trusted from a
citation, or proven on too narrow a sample. From then on, every claim is confirmed or contradicted the same way:
every earlier statement of it is read first, the driver is read, and the claim is measured again across the whole
corpus, not one image.

One example: the length of a structure's self-checksum, once proven on one cluster size, turned out to depend on
the cluster size. This step catches a rule proven on one geometry.

**A register and its errata.** Each claim became one row of a register, with what the driver and the disk each
say of it and how strongly. A correction is an erratum, and the erratum wins over every other statement of the
claim; the pages state only the current value. This makes every claim auditable, and a change to it visible.

**Fixed outputs and gates.** The tools run a fixed set of commands on every image of the corpus, and the
fingerprint of every output is kept. A change to any of them must be accounted for; in this release each one is
predicted, in writing, before the run that shows it. The pages have gates of their own:

- a claim once retracted cannot reappear in any wording the gate knows;
- numbers repeated across pages must agree;
- every function the internals page names must exist;
- every change in what the listing and verdict commands print on the public samples since the last release must
  be announced;
- every change to a register row's claim, status or build scope since the last release must name the record
  behind it.

This step catches an unintended change, and a page drifting from the register.

**Reviews in other sessions.** Every review of the project has been made by other language-model sessions — run
with other models or in other contexts, and given only the published material, or a package prepared for the
review. They are part of the project's own method: no person or organisation outside the project has reviewed it.

In July 2026 the project had re-checked its own tools twice and reported them sound (the two self-validations
kept in `analysis/reports/`, with what each covered). Reviews in other sessions then tested the tool and the
reference, and found what those checks had missed. The largest was the blind audit of release 1.12.3 (September
2026, 215 findings). Its session had no history in the project and was given:

- the published tool and pages;
- the images, and ground truth that Windows or an operator produced;
- another open-source ReFS implementation;
- the driver builds.

Every statement of the project was to be treated as a claim, and the project's own reports were withheld until
its report was written.

A rule came out of it: a check counts only once it has been shown catching a planted error. One rule for reading
a file's extent map had been taken from the weaker of two signs that were always seen together, and confirmed by
a count that could not have shown it wrong.

**Every fix starts with a failing test.** The rule of this release is that a defect is first reproduced as a test that fails, then
fixed until the test passes. Each group of fixes is closed by a review in another session, and each release
candidate is checked, as a package, in another session before the release.

Two errors of this release added the last rule: a statement says exactly what was read, over exactly the set it
was read on. A driver statement names only the builds actually read, and a figure is written from the full
distribution of what was measured, never from examples.

## Scope

**The focus is the latest format: ReFS 3.14 today.** Most of the corpus volumes are 3.14, and every driver
build read except the Windows 10 one is a 26100 or Insider build.

The reference covers ReFS **3.4 through 3.14**, plus the Insider builds read (29574 and later); facts are
versioned where a change between formats is known. 3.14 is the newest format any released Windows writes. A
preview driver reports a maximum supported version of **3.15** and stamps that number in the volume's driver
field once it has mounted it, but no volume here — or, as far as this project can tell, anywhere — is
*formatted* 3.15, so nothing is claimed about it.

Where neither the code nor the disk settles a question, it is listed as an open question rather than asserted,
and a statement that rests on neither is graded as such in the register.

Coverage is not uniform. **[Format
support](format_support.md)** shows, per area of the reference, which formats a measurement on an image
actually confirmed it on — with the statements confirmed without a recorded format, and those not
confirmed on an image at all, in columns of their own. It lists only the formats a measurement confirmed: a fact can also be
true of a format no image here covers, and the table does not claim it.

## LLM-assisted work

The analysis was **LLM-assisted**: a language model accelerated the search across thousands of decompiled
functions and disk images, and much of the code was written with its help. Every claim it surfaced was checked on
the code, the disk, or both, and the register records which — the model sped up coverage, it did not establish
facts.

The reviews described above were language-model sessions too (*How the method grew*): checks within the project,
not an outside certification. The two tools (`forefst.py`, `refsanalysis.py`) are conventional, dependency-free
Python that reproduce the on-disk measurements directly.

## See the published evidence on GitHub

The published apparatus — the method, the claim register and the project's own claim audit of June 2026 — lives
in the source repository:

- **[Full methodology](https://github.com/xbqt/forefst/blob/main/docs/methodology.md)** — the protocol,
  the evidence model, and a worked example following one fact from hypothesis to register.
- **[The claim register](https://github.com/xbqt/forefst/blob/main/analysis/reference_table.csv)** — one
  row per fact: the claim, the static and raw-disk checks, and the evidence grade.
- **[Knowledge map](https://github.com/xbqt/forefst/blob/main/docs/KNOWLEDGE_MAP.md)** — the index between
  the two, generated from the pages and the register with nothing typed by hand: for each documentation
  page, the findings behind it and their evidence level; for each finding, every page that cites it; and
  the register rows no page cites yet. Useful for checking that a correction reached all of them, and for
  seeing what is measured but not yet written up.
- **[Claim audit record, June 2026 (archived)](https://github.com/xbqt/forefst/blob/main/analysis/reports/archive/2026-06_claim_audit/README.md)** —
  the project's own first audit of every claim of that time (409 rows), with its per-claim dossiers and proofs; it
  does not describe the current release: the current evidence of each finding is its register row.
