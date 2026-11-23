# Format support

Which ReFS formats each area of this project has been **confirmed on**: a number is how many
statements in that area a measurement on an image of that format confirmed. It is not which
formats a statement is *about* — a statement can describe a format no image here was checked
against, and this table will not say so. It is deliberately a **floor**: nothing is inferred from
what a statement asserts, only from what was measured. Blank means nothing in that area was
confirmed on that format, which is a gap in the evidence, not a statement that ReFS differs.

The last two columns count the area's statements that no format cell holds: **format not
recorded** — confirmed on an image, but the record does not say which format; **not confirmed on
an image** — read from the driver, inferred, not yet tested on an image, or contradicted by a
measurement.

| Area | 3.4 | 3.7 | 3.9 | 3.10 | 3.14 | format not recorded | not confirmed on an image |
|---|---|---|---|---|---|---|---|
| File records & attributes | 41 | 15 | 14 | 14 | 71 | 25 | 21 |
| Journals & log | 17 | 3 | 1 | 2 | 22 | 7 | 48 |
| B+-tree structure | 48 | 14 | 10 | 13 | 53 | 2 | 2 |
| Object & container tables | 41 | 6 | 6 | 7 | 41 | 5 | 8 |
| Boot & volume | 32 | 5 | 5 | 7 | 34 | 3 | 10 |
| Checkpoints | 27 | 1 | 1 | 1 | 21 | 3 | 0 |
| Architecture & driver | 7 |  |  |  | 6 | 3 | 19 |
| Security & links | 8 | 4 | 2 | 3 | 17 | 3 | 3 |
| Deletion & recovery | 2 |  |  |  | 3 | 4 | 4 |
| Snapshots & CoW |  |  |  |  | 6 | 0 | 2 |
| Other | 2 |  |  |  | 2 | 0 | 4 |

Of 503 statements, **382 were confirmed on an image**; 55 of them without a
recorded format, and **121 are not confirmed on an image**. Both are counted in their columns
rather than dropped: leaving them out would make coverage look strongest exactly where it is least
documented. A statement confirmed on two formats is counted under each.

Formats 3.11 to 3.13 appear nowhere because no image of them exists in this project's corpus.
A boundary such as *"this applies from 3.11"* is a statement about where behaviour changes,
not a measurement taken there.
