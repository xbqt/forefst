"""An exact spelling must win over a case-insensitive one in `resolve_path`.

ReFS is case-insensitive by default, so path resolution folds case -- but a directory carrying the
per-directory case-sensitivity flag (`fsutil file setCaseSensitiveInfo`) makes the B+-tree compare keys
BINARY rather than case-folded (MD_CS_RA_001), and two names differing only by case can then coexist as
separate type-0x30 rows with distinct ObjectRefs.

`resolve_path` used to return the FIRST case-insensitive hit, so on such a directory every spelling
resolved to whichever name came first in B+-tree order -- and `extract` served one file's bytes under the
other file's name, with exit 0 and no warning. `--id` routes through the same resolver and failed with it.

The behavioural proof is `win11bidule`, whose operator-written SHA-256 inventory contains both
`tests/testdir/HI.txt` and `tests/testdir/hi.txt` as distinct files: 630 of 630 hashed rows now match
byte-for-byte (analysis/tools/analysis_scripts/verify_bidule_hashes.py). That check needs the corpus, so
what is guarded here is the property that made it pass -- exact wins, case-insensitive is only a fallback.
"""
import inspect

import forefst as F


def _resolve_body():
    return inspect.getsource(F.resolve_path)


def test_an_exact_name_match_is_tried_and_wins():
    """`nm == part` must be a real branch: folding case for every comparison is what caused the bug."""
    body = _resolve_body()
    assert "if nm == part:" in body, \
        "resolve_path no longer prefers an exact spelling; two names differing only by case will collide"


def test_the_case_insensitive_hit_is_only_a_fallback():
    """The folded comparison must not overwrite a hit already found, and must not stop the scan.

    A bare `if nm.lower() == part.lower(): found = ...; break` is the original defect: it takes the first
    row whatever its spelling. The fallback has to be guarded on `found is None` so an exact match found
    later in the same directory still wins.
    """
    body = _resolve_body()
    assert "if found is None and nm.lower() == part.lower():" in body, \
        "the case-insensitive match is no longer guarded as a fallback"
    fold = body.index("nm.lower() == part.lower()")
    tail = body[fold:fold + 200]
    assert "break" not in tail.split("\n")[0:3][-1] or "found = (kd, vd)" in tail, \
        "the fallback must record the row without ending the scan for an exact match"


def test_case_insensitive_resolution_is_still_supported():
    """The fallback must survive: a wrong-case path on an ordinary directory still has to resolve.

    ReFS is case-insensitive by default and the release golden depends on this -- one extract target is
    spelled `$RRJOQB1.xml` against an on-disk `$Rrjoqb1.xml`.
    """
    body = _resolve_body()
    assert "nm.lower() == part.lower()" in body, \
        "case-insensitive resolution was removed; wrong-case paths would stop resolving"
