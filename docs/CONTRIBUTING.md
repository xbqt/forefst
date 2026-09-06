# Contributing to forefst

Thanks for your interest. **forefst** is an open, auditable forensic toolkit for Microsoft's ReFS —
`forefst.py` (the file lister + forensic suite) and `refsanalysis.py` (the structure-level
lab) — backed by a byte-level reference whose every claim is graded by evidence. Contributions of all kinds are
welcome: bug reports, new test volumes, format findings, documentation fixes, and code.

## Running the tools

The only requirement is **Python 3.7+, standard library only** — no `pip install`, no dependencies, no build
step. Clone and run, on Linux, macOS, or Windows:

```sh
python3 forefst.py --list                       # every subcommand
python3 forefst.py disk.raw summary             # volume overview
python3 forefst.py disk.raw -o files.csv        # full file listing
python3 forefst.py <image> help <subcommand>    # detailed help for one subcommand
```

Both tools open the input strictly **read-only**, so pointing either at evidence is safe. The input can be a raw
ReFS image, a raw disk/partition device, or an E01 exported to raw; forefst finds the ReFS partition inside a
full-disk image automatically.

## Reporting a bug

Open a [GitHub issue](https://github.com/xbqt/forefst/issues). A good report includes:

- the exact command and the `forefst.py --version` / `refsanalysis.py` version,
- the ReFS version and volume shape if known (`summary` prints version, cluster size, checksum type),
- what you expected vs what you got (paste the output, or attach a **small** sample image if you can share one),
- for a parsing error, the offending offset/structure if you have it.

Because ReFS changes across Windows builds, the single most useful thing you can attach is a **controlled test
volume** that reproduces the issue.

## Submitting a change

1. Fork, branch, and open a pull request against `main`.
2. **Keep it standard-library-only.** No third-party imports in `forefst.py` / `refsanalysis.py` — the "clone and
   run, audit line by line" promise depends on it.
3. Match the surrounding style (little-endian `struct.unpack_from`, lower-case hex, `--` for em-dashes) and keep
   changes focused.
4. If your change alters a command's **output**, regenerate the affected fixtures under `analysis/samples/`
   and include the diff so reviewers can see exactly what moved.
5. Describe how you verified it (which image, which command, before/after).

## The evidence standard

forefst's trust model is that **every structural fact holds in two independent places** — the decompiled
`refs.sys` driver and a raw-disk lab corpus — before a tool relies on it. Claims are graded:

- **E1** — a binary string literal,
- **E2** — a decompiled function / PDB symbol,
- **E3** — structural inference,
- **RD** — parsed and confirmed on real volumes.

Load-bearing claims should be **E2 and/or RD**. The published claim register is `analysis/reference_table.csv`
(one row per finding, with its evidence level and verification status). If you add or change a format claim, cite the evidence (a driver function name, a
disk measurement, or a `reference_table.csv` finding id); "it looked right" is not enough. A full byte-level
master reference is maintained upstream and is the source the published register is derived from — if you hit a
discrepancy between a doc page and the tool, flag it in an issue and we'll reconcile it against the master.

## Documentation style

The pages under `docs/` are the human-readable layer over the audited reference; they must stay consistent with
it. When you edit a page:

- **Use the templates** in [`_templates/`](_templates/) (structure / concept / attribute). Lead with 1–3
  sentences, then the `| Offset | Size | Field | Description |` "at a glance" table near the top.
- **State only the current, correct value and its proof.** When you fix a wrong value, *replace* it — do not
  leave a "previously X" / "was mislabelled" note in the page; that history belongs in the change description,
  not the reader-facing doc.
- Keep a body **`## Evidence`** section (which driver functions / disk measurements back the page) and a
  **Cross-References** section (no orphan pages). Per-page provenance — status, evidence level, finding ids,
  last-audited date — lives centrally in [`audit_dates.tsv`](audit_dates.tsv); add a row for every new page.
- Use **relative** markdown links and run the link check before opening the PR.
- One directory = one `README.md` index; add your page's row when you create it. Use
  [`KNOWLEDGE_MAP.md`](KNOWLEDGE_MAP.md) to find where a topic already lives before adding a new page.

## Keeping the docs in sync with the tools

The reference (this documentation and the website) and the tools must not drift. **When a change alters a
command's output** — a new or renamed column, a changed default, a new flag, a different default subcommand —
update the docs in the *same* change:

1. Fix the affected `tools/` and any structure/concept page so every documented flag, default, and column
   matches the tool's real behaviour (the tool is the source of truth — run it and compare).
2. Run the site gates: `python3 docs/website/build.py` (rebuilds the site and fails on any leak/artifact) and
   the link checker; both must pass with zero broken links.
3. If a captured sample's output changed, regenerate the sample bundles and confirm the diff is legitimate.
4. Keep the reference counts current (the claim-register size, errata count, column count) wherever they are
   quoted, and check that no page still cites the old value.

A tool change that leaves the docs stale is an incomplete change.

## Where things live

| Kind | Directory |
|------|-----------|
| On-disk byte structures | `structures/` |
| Attribute / embedded sub-record types | `attributes/` |
| Mechanisms, methodology, version evolution | `concepts/` |
| Worked investigator walkthroughs + tool dumps | `examples/` |
| Tool capability references | `tools/` |
| Central topic→file index | `KNOWLEDGE_MAP.md` |
