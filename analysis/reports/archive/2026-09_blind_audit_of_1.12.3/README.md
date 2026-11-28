# The blind audit of release 1.12.3: the answer (archived)

The blind audit of September 2026 recorded 215 findings against release 1.12.3. These two files, generated at release
1.14.0, answer it:

- [`AUDIT_RESPONSE.md`](AUDIT_RESPONSE.md): every finding and where its answer can be checked (a test, a battery case,
  an oracle probe, an erratum);
- [`WRONG_VERDICT_COVERAGE.md`](WRONG_VERDICT_COVERAGE.md): the findings where a tool gave a wrong verdict, and the
  evidence that would now fail if the defect came back.

They describe releases 1.12.3 to 1.14.0; later corrections are in the changelog and the errata.
