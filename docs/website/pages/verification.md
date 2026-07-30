---
title: "Methodology"
description: "How the ReFS on-disk facts in this reference were verified — a dual-evidence method (driver code and raw disk), graded evidence, and the full proof on GitHub."
---

# How these ReFS facts were verified

This reference decodes what ReFS actually writes to disk. Every byte-level claim on the structure,
attribute, and concept pages had to survive **two independent checks** before it was published — so you can
rely on what you read here, and audit the evidence yourself.

## Two independent sources must agree

A claim is accepted only when the **decompiled `refs.sys` driver** (what the code is written to do) and the
**raw on-disk bytes** (what a real volume actually contains) agree. A pattern the code implies but the disk
cannot show — or a byte the code does not explain — is held back, not stated as fact. Code alone can
mislead (dead paths, version drift); one disk image alone can mislead (it is not the whole population).
Requiring both, across many images and several Windows builds, is what makes a claim trustworthy.

## Where the facts come from

- **The driver.** `refs.sys` decompiled across several Windows builds spanning ReFS 3.4 → 3.14 (plus an
  Insider preview), with Microsoft's `refsutil` utility as a cross-check.
- **A lab image corpus.** Over a hundred controlled ReFS volumes generated across versions, both cluster
  sizes, and all three metadata-checksum modes — so any on-disk feature could be produced on demand and
  then re-measured at scale.
- **A central claim register.** Every fact is one row, carrying its finding ID, both checks, and an
  evidence grade.

## Confidence grades

Each fact carries a grade — kept off the reference pages themselves and recorded with the finding
(written `E1`–`E3` and `RD` in the register):

- **String** (`E1`) — the driver binary names the structure or field.
- **Decompiled** (`E2`) — read from the reverse-engineered driver code.
- **Inference** (`E3`) — deduced from the code but not stated outright; the weakest grade, always
  corroborated before use.
- **Raw-disk** (`RD`) — measured physically on the image corpus, independent of the code.

A fact is strongest when the code and the disk agree.

## Corrections are tracked, not hidden

The analysis revised both prior work and itself. Where a fact changed, the correction folds into the
register and the page states **only** the current, corrected value; the history lives in the repository,
not in the prose.

## Scope

The reference covers ReFS **3.4 through 3.14** plus an Insider preview; facts are versioned where they
change. Where neither the code nor the disk could settle a question, it is left as an open question rather
than asserted — and no claim rests on a single image.

## A note on tooling

The analysis was **LLM-assisted**: a language model accelerated the search across thousands of decompiled
functions and disk images. But every claim it surfaced was independently confirmed on the code and the disk
before it entered the register — the model sped up coverage, it did not establish facts. The two tools
(`forefst.py`, `refsanalysis.py`) are conventional, dependency-free Python that reproduce the on-disk
measurements directly.

## See the full evidence on GitHub

The complete apparatus — the written protocol, the claim register, and the per-claim proofs — lives in the
source repository:

- **[Full methodology](https://github.com/xbqt/forefst/blob/main/docs/methodology.md)** — the complete
  protocol, the evidence model, and a worked example following one fact from hypothesis to register.
- **[The claim register](https://github.com/xbqt/forefst/blob/main/analysis/reference_table.csv)** — one
  row per fact: the claim, the static and raw-disk checks, and the evidence grade.
- **[Audit &amp; verification](https://github.com/xbqt/forefst/blob/main/analysis/reports/audit/README.md)** —
  how the claims and tools were independently audited, with links onward to the per-claim dossiers and the
  measured proofs.
