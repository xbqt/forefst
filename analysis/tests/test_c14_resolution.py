"""C1.4 — one name→record resolution path.

`walk_directory_tree` used to try a local `(parent_oid, file_id)` key before the object's home. `file_id`
is a PER-DIRECTORY ordinal, so that key can name a different object that merely holds the same ordinal in
the same directory — the collision that also bit two measuring scripts during this work.

The local branches were reachable but never decisive: removing them left the release golden byte-identical
across the corpus. 1.11.0 kept them behind `--legacy-link-join`; 1.11.1 deleted both the flag and the
ladder, so the home path is now the only one and there is nothing left to fall back to.

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


def test_no_branch_resolves_through_the_local_key():
    """The local (parent_oid, file_id) key must not be consulted at all.

    Until 1.11.1 this had to carve out the `if legacy_link_join:` suite, which was the only place allowed
    to choose the local record. The flag and the suite are gone, so the property is now the simple one:
    nothing chooses `loc`, and `loc` is not even computed.
    """
    body = _resolution_source()
    assert "rec = loc" not in body, "a branch still resolves through the local key"
    assert 'sig = ("obj", P, fid)' not in body, "a branch still groups on the local key"
    assert "loc = t40_content.get((P, fid))" not in body, \
        "the local lookup is dead once nothing chooses it; leaving it invites a branch back"


def test_the_legacy_flag_is_gone():
    """1.11.0 promised the flag for exactly one release. It must not outlive that."""
    assert "legacy_link_join" not in inspect.getsource(F.walk_directory_tree)
    assert "legacy_link_join" not in inspect.signature(F.walk_directory_tree).parameters
    assert not hasattr(F, "LEGACY_LINK_JOIN")


def test_file_id_is_documented_as_a_per_directory_ordinal():
    """The reason the local key is unsafe must stay written down next to the code that avoids it."""
    body = _resolution_source()
    assert re.search(r"per-directory ordinal", body, re.I), \
        "the collision that motivates the single path is not explained at the code"
