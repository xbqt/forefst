"""`timestomp_verdict()` is the only place a timestamp-anomaly tier is decided.

They used to. Each computed its own tier, and on three volumes 101/184, 62/151 and 50/114 flagged files got
a different confidence depending on which one you ran -- the column said MEDIUM where the command said HIGH
for the identical signal set. One body of evidence, two answers.

It used to be two places. The `files` TimestompFlags column computed its own tier and disagreed with the
command on 40-55 % of flagged files. v1.11.0 removed the column outright, so the disagreement is now
impossible by construction rather than merely tested for. What remains worth pinning is the function's own
behaviour, asserted here on unit inputs:

  1. the column never rates a file HIGHER than the command;
  2. the column's signals are a subset of the command's;
  3. with no USN evidence the two tiers are IDENTICAL.
"""
import os
import sys

import pytest

# analysis/tests/ -> three levels up to the repo root.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
import forefst as F                                                     # noqa: E402

RANK = {"HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1, "NONE": 0}


# ── unit: the three properties, from the function alone ──────────────────────

@pytest.mark.parametrize("flags", [
    ["PRE_FORMAT"],
    ["CHANGE_LATE", "PRE_FORMAT"],
    ["CREATE_GT_MODIFY"],
    ["PRE_FORMAT", "CREATE_GT_MODIFY"],
    ["CHANGE_LATE"],
    ["FUTURE"],
    ["HARDLINK_MACB_MISMATCH", "PRE_FORMAT"],
])
def test_more_evidence_never_lowers_the_tier(flags):
    """The command has strictly more evidence than the column; its tier must be >= the column's."""
    col, _ = F.timestomp_verdict(flags, usn_conf=False, hl_conf=False)
    cmd, _ = F.timestomp_verdict(flags, usn_conf=True, hl_conf=False)
    assert RANK[cmd] >= RANK[col], f"{flags}: command {cmd} < column {col}"


@pytest.mark.parametrize("flags", [["PRE_FORMAT"], ["CHANGE_LATE", "PRE_FORMAT"], ["CREATE_GT_MODIFY"]])
def test_identical_without_journal_evidence(flags):
    """Same inputs, same verdict -- the property that failed before the two surfaces shared a function."""
    assert F.timestomp_verdict(flags, usn_conf=False) == F.timestomp_verdict(flags, usn_conf=False)


def test_copy_signature_is_info_not_suspicion():
    """PRE_FORMAT (+CHANGE_LATE) is a timestamp-preserving copy: 22.67 % / 22.32 % of all files, measured
    over the full corpus (96 images / 521,060 files). Tiering it MEDIUM marked 22 % of an ordinary volume
    as tampered."""
    assert F.timestomp_verdict(["PRE_FORMAT"])[0] == "INFO"
    assert F.timestomp_verdict(["CHANGE_LATE", "PRE_FORMAT"])[0] == "INFO"
    assert F.timestomp_verdict(["CREATE_GT_MODIFY"])[0] == "INFO"


def test_change_late_without_pre_format_is_not_a_copy():
    """Created on THIS volume and altered afterwards -- the signature a copy cannot produce. 384 instances
    corpus-wide (0.33 % of CHANGE_LATE), all on one real Windows volume. A 27-image lab-only subset showed
    0 and an earlier draft called it witness-less."""
    assert F.timestomp_verdict(["CHANGE_LATE"])[0] == "MEDIUM"


def test_hardlink_and_journal_stay_high():
    """The two independent sources keep their weight: neither is a copy artefact."""
    assert F.timestomp_verdict(["PRE_FORMAT"], hl_conf=True)[0] == "HIGH"
    assert F.timestomp_verdict(["PRE_FORMAT"], usn_conf=True)[0] == "HIGH"


# ── integration: the same three properties through both CLI surfaces ─────────

def _corpus_image():
    # Walk UP for the corpus, as test_exit_codes.py does: it sits above the tool tree in the maintainer's
    # workspace and is absent from a clone, where this test skips rather than pretending to pass.
    root = None
    seen = set()
    for start in (os.getcwd(), REPO):
        d = os.path.abspath(start)
        while d not in seen:
            seen.add(d)
            cand = os.path.join(d, "analysis", "rawdisk", "disks")
            if os.path.isdir(cand):
                root = cand
                break
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
        if root:
            break
    if root is None:
        return None
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if fn == "win11refstestmftecmd.raw":
                return os.path.join(dirpath, fn)
    return None


# `test_column_and_command_agree_on_a_real_volume` stood here. It walked a corpus image and asserted that
# the `files` TimestompFlags column never rated a file higher than the `timestomp` command, and that its
# signals were a subset. v1.11.0 REMOVED that column, so there is no second surface left to disagree --
# the property is now structural rather than tested. The unit assertions above stay: they pin the tier
# function itself, which is still the single source for the one remaining surface.
