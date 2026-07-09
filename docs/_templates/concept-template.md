<!-- TEMPLATE: concept / mechanism / forensic page. Copy into concepts/, fill in, delete these comments.
 Concepts explain HOW and WHY (not just byte layouts). Every factual claim must be traceable to
 structure_reference.md, a finding, or the decompilation — cite it. -->

# <Concept>

<1–3 sentences stating the idea in plain terms and why it matters to a ReFS forensic analyst.>

## How It Works

<The mechanism. Prose + an ASCII diagram or pseudocode where it clarifies (CoW chains, Merkle tree,
VLCN→PLCN translation). Reference the underlying structures by link rather than re-documenting their bytes.>

## Forensic Implications

<What this means for an investigation: what it lets you recover/prove, what artifacts it produces, what
mistakes it causes (e.g. the $SI+0x70-as-hard-link-counter trap). This section is mandatory for concept pages.>

## Version / State Differences

<Optional — how the concept differs across v3.4 / v3.7 / v3.10 / v3.14 / Insider, or native vs upgraded.>

## Comparison with NTFS

<Optional — the recurring NTFS-vs-ReFS contrast table, where relevant.>

## Static-Analysis Evidence

<Optional but encouraged for mechanism pages — the driver function(s) that implement the concept, with
build + address, and a 5–10 line decompiled snippet where it settles a claim (e.g. the CRC64 poly, the
allocate-new-then-propagate CoW path).>

## Tooling

<Optional — which forefst.py / refsanalysis.py subcommand surfaces this, with an example invocation.>

## Cross-References

- [<related page>](<rel/path.md>) — <why>
- Master reference: `structure_reference.md` §<X.Y>

## Evidence

<Prose: the driver functions (E2) and/or raw-disk measurements (RD) that back this page's claims; name the key finding IDs.>

<!-- No provenance footer. Add this page's row to ../audit_dates.tsv
     (page · status · evidence · findings · last_audited · note) — provenance lives there, not on the page. -->
