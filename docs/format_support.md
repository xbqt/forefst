# Format support

Verified means a measurement was made on an image of that format and recorded with the claim.
It is deliberately a **floor**: a statement can be true of a format nobody here has an image of,
and this table will not say so. Nothing is inferred from what a claim asserts — only from what
was checked.

Which ReFS formats each area of this project has been **verified on** — not which formats a
statement is *about*. A claim can describe a format that no image here was ever checked against;
this table counts only measurements actually made, so it is a floor, not a ceiling.

A number is how many verified statements in that area cover that format. Blank means nothing in
that area was checked on it — which is a gap in the evidence, not a statement that ReFS differs.

| Area | 3.4 | 3.7 | 3.9 | 3.10 | 3.14 | 3.15 | insider | scope not recorded |
|---|---|---|---|---|---|---|---|---|
| File records & attributes | 57 | 12 | 10 | 10 | 77 | 2 | 11 | 23 |
| Journals & log | 49 | 3 | 1 | 2 | 55 | 1 | 2 | 7 |
| B+-tree structure | 45 | 8 | 5 | 8 | 46 | 2 | 22 | 3 |
| Object & container tables | 39 | 1 | 1 | 2 | 37 |  | 11 | 11 |
| Boot & volume | 33 | 1 | 1 | 3 | 39 |  | 6 | 3 |
| Checkpoints | 27 |  |  |  | 18 |  | 3 | 2 |
| Other | 4 |  |  |  | 18 |  |  | 10 |
| Security & links | 8 | 2 |  | 1 | 21 |  | 5 | 3 |
| Architecture & driver | 12 |  |  |  | 11 |  |  | 4 |
| Deletion & recovery | 3 |  |  |  | 6 |  |  | 4 |
| Snapshots & CoW |  |  |  |  | 8 |  |  | 0 |

**70 statements have no recorded verification scope.** They are counted in the last
column rather than dropped: leaving them out would make coverage look strongest exactly where it
is least documented. Most are older entries whose record kept the date of the check but not the
volumes it ran on.

Formats 3.11 to 3.13 appear nowhere because no image of them exists in this project's corpus.
A boundary such as *"this applies from 3.11"* is a statement about where behaviour changes,
not a measurement taken there.
