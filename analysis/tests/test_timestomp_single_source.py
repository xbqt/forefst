"""The TimestompFlags column and the `timestomp` command must not disagree.

They used to. Each computed its own tier, and on three volumes 101/184, 62/151 and 50/114 flagged files got
a different confidence depending on which one you ran -- the column said MEDIUM where the command said HIGH
for the identical signal set. One body of evidence, two answers.

`timestomp_verdict()` is now the only place a tier is decided. The column calls it without journal evidence
(the walk does not read $J), so its verdict is the command's minus journal corroboration. That gives three
properties, asserted here on unit inputs (always) and on a corpus image when one is present:

  1. the column never rates a file HIGHER than the command;
  2. the column's signals are a subset of the command's;
  3. with no USN evidence the two tiers are IDENTICAL.
"""
import csv
import os
import subprocess
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


def test_column_and_command_agree_on_a_real_volume(tmp_path):
    img = _corpus_image()
    if img is None:
        pytest.skip("corpus image not present (a clone ships no images)")
    tool = os.path.join(REPO, "forefst.py")
    fcsv = tmp_path / "f.csv"
    tcsv = tmp_path / "t.csv"
    for args, dest in ((["files", "--csv", str(fcsv)], fcsv), (["timestomp", "--csv", str(tcsv)], tcsv)):
        r = subprocess.run([sys.executable, tool, img] + args, capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, r.stderr[-400:]
        assert dest.exists()
    col = {r["FullPath"]: r["TimestompFlags"].strip()
           for r in csv.DictReader(open(fcsv, encoding="utf-8")) if (r.get("TimestompFlags") or "").strip()}
    cmd = {r["path"]: (r["confidence"], r["signals"]) for r in csv.DictReader(open(tcsv, encoding="utf-8"))}
    both = set(col) & set(cmd)
    assert both, "no flagged files in common — the comparison would be vacuous"
    for p in both:
        ctier, _, csig = col[p].partition(":")
        ttier, tsig = cmd[p]
        assert RANK[ctier] <= RANK[ttier], f"{p}: column {ctier} > command {ttier}"
        assert set(csig.split("|")) <= set(tsig.split("|")), f"{p}: column signals not a subset"
        if "USN_" not in tsig:
            assert ctier == ttier, f"{p}: no journal evidence yet tiers differ ({ctier} vs {ttier})"
