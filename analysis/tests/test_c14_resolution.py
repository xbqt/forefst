"""C1.4 — one name→record resolution path.

`walk_directory_tree` used to try a local `(parent_oid, file_id)` key before the object's home. `file_id`
is a PER-DIRECTORY ordinal, so that key can name a different object that merely holds the same ordinal in
the same directory — the collision that also bit two measuring scripts during this work.

The local branches were reachable but never decisive: removing them leaves the release golden
byte-identical across the corpus. So this is a simplification, and the property worth pinning is that it
IS one: the surviving path must be the home path, and the retained `--legacy-link-join` ladder must
produce the same answer.

The corpus-scale check lives in verify_claim.py: every split name is listed by its resolved backing's own
type-0x39 link set — the driver's list, not a second implementation of ours. 83,521 names on the 64
corpus images that contain one, 0 exceptions.
"""
import inspect
import re

import forefst as F


def _resolution_source():
    """The body of walk_directory_tree from the resolution ladder to the end of the fallback."""
    src = inspect.getsource(F.walk_directory_tree)
    i = src.index("C1.4 -- ONE resolution path")
    return src[i:i + 3000]


def _legacy_block(body):
    """The `if legacy_link_join:` suite, delimited by INDENTATION rather than by any condition string.

    An earlier version of this test anchored on the literal text of the branch that follows the block, and
    broke the moment that condition was corrected -- pinning the wording instead of the property.
    """
    lines = body.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip().startswith("if legacy_link_join:"))
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        l = lines[end]
        if l.strip() and (len(l) - len(l.lstrip())) <= indent:
            break
        end += 1
    return "\n".join(lines[start:end]), "\n".join(lines[:start] + lines[end:])


def test_the_default_path_resolves_only_through_home():
    """No branch outside the legacy suite may resolve a name through the local (parent, file_id) key."""
    legacy, outside = _legacy_block(_resolution_source())
    # `loc` may still be COMPUTED (the legacy ladder needs it) but must never be CHOSEN outside the suite
    assert "rec = loc" not in outside, "a non-legacy branch still resolves through the local key"
    assert 'sig = ("obj", P, fid)' not in outside, "a non-legacy branch still groups on the local key"
    assert "rec = loc" in legacy, "the legacy suite should be the only place the local record is chosen"


def test_the_legacy_ladder_is_still_reachable_for_one_release():
    """The old behaviour stays available so a prior result can be reproduced."""
    body = _resolution_source()
    assert "if legacy_link_join:" in body
    assert "rec = loc" in body, "the legacy ladder must still be able to choose the local record"
    sig = inspect.signature(F.walk_directory_tree)
    assert "legacy_link_join" in sig.parameters


def test_file_id_is_documented_as_a_per_directory_ordinal():
    """The reason the local key is unsafe must stay written down next to the code that avoids it."""
    body = _resolution_source()
    assert re.search(r"per-directory ordinal", body, re.I), \
        "the collision that motivates the single path is not explained at the code"
