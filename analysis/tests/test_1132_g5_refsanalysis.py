"""The code half, group 5 (refsanalysis's last update), 1.14.0: PLAN decision 54 (the pin), RUNNING_LOG N542, N543, and
what group 4's approved draft gave refsanalysis (G2's `details` line, C1's rules). A1 already reaches `refsanalysis
summary` (group 1). Written RED before the fix (`analysis/reports/v1.13.2/RC1D/G5/`). Volumes: win11refsmini (step1),
the public sample."""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
MINI314 = "step1/win11refsmini.raw"
SAMPLE = "step5/win11refstestmftecmd.raw"


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(argv, timeout=1800, cwd=None):
    return subprocess.run([sys.executable, "-B"] + argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)


def _version_of(path):
    return re.search(r'^VERSION = "([^"]+)"', open(path, encoding="utf-8").read(), re.M).group(1)


def _forefst_with_version(dst, version):
    s = open(FOREFST, encoding="utf-8").read()
    s = re.sub(r'^VERSION = "[^"]+"', 'VERSION = "%s"' % version, s, count=1, flags=re.M)
    open(dst, "w", encoding="utf-8").write(s)


# ═══ decision 54: refsanalysis runs only with the forefst of its release ══════════════════════════════════════════

def test_d54_another_forefst_version_is_refused(tmp_path):
    shutil.copy(RA, str(tmp_path / "refsanalysis.py"))
    _forefst_with_version(str(tmp_path / "forefst.py"), "9.9.9")
    r = _run([str(tmp_path / "refsanalysis.py"), "--list"], cwd=str(tmp_path))
    v = _version_of(RA)
    assert r.returncode == 1, (r.returncode, r.stderr[-600:])
    assert ("refsanalysis %s runs only with forefst %s; this forefst is 9.9.9" % (v, v)) in r.stderr, r.stderr[-600:]


def test_d54_the_pinned_copy_beside_it_is_the_one_imported(tmp_path):
    """A `refsanalysis_forefst/forefst.py` of the right version is imported before a wrong one on the path."""
    shutil.copy(RA, str(tmp_path / "refsanalysis.py"))
    _forefst_with_version(str(tmp_path / "forefst.py"), "9.9.9")
    (tmp_path / "refsanalysis_forefst").mkdir()
    shutil.copy(FOREFST, str(tmp_path / "refsanalysis_forefst" / "forefst.py"))
    r = _run([str(tmp_path / "refsanalysis.py"), "--list"], cwd=str(tmp_path))
    assert r.returncode == 0 and "runs only with" not in r.stderr, (r.returncode, r.stderr[-600:])


def test_d54_control_the_release_pair_runs():
    r = _run([RA, "--list"])
    assert r.returncode == 0 and "runs only with" not in r.stderr, r.stderr[-600:]


# ═══ N542: containers ═════════════════════════════════════════════════════════════════════════════════════════════

def test_n542_help_containers_names_the_columns_printed():
    h = " ".join(_run([RA, "help", "containers"]).stdout.split())
    assert "(ID, Phys LCN, Flags, Row, Type)" in h and "free/capacity" not in h, h[:600]
    r = _run([RA, _img(MINI314), "containers", "-v"])
    assert re.search(r"^\s+ID\s+Phys LCN\s+Flags\s+Row\s+Type$", r.stdout, re.M), r.stdout[-1500:]


def test_n542_total_volume_size_is_the_count_then_the_aid():
    r = _run([RA, _img(MINI314), "containers"])
    m = re.search(r"Total volume size:\s+(.*)$", r.stdout, re.M)
    assert m and re.fullmatch(r"\d+ bytes \([\d.]+ [KMGT]iB\)", m.group(1)), m and m.group(1)


# ═══ N543 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n543_a_refsanalysis_attributes_securityid_has_the_decimal():
    r = _run([RA, _img(MINI314), "attributes"])
    ids = re.findall(r"SecurityId:\s+(\S+(?: \(\d+\))?)", r.stdout)
    assert ids and all(re.fullmatch(r"0x[0-9a-f]+ \(\d+\)|\(none\)", x) for x in ids), ids[:5]


def test_n543_a_forefst_security_lists_securityids_with_the_decimal():
    r = _run([FOREFST, _img(MINI314), "security", "--files"])
    rows = [ln for ln in r.stdout.splitlines() if re.match(r"^    0x[0-9a-f]+ ", ln)]
    assert rows and all(re.match(r"^    0x[0-9a-f]+ \(\d+\)\s", ln) for ln in rows), rows[:3]


def test_n543_a_forefst_security_descriptor_lines_have_the_decimal():
    """The descriptor listing (`_print_sd`, also `--sid` and `--files -v`): `SecurityId: 0x103 (259)`."""
    r = _run([FOREFST, _img(MINI314), "security"])
    ids = re.findall(r"^\s+(?:\[\d+\] )?SecurityId: (0x[0-9a-f]+(?: \(\d+\))?)", r.stdout, re.M)
    assert ids and all(re.fullmatch(r"0x[0-9a-f]+ \(\d+\)", x) for x in ids), ids[:5]


def test_n543_b_no_journal_record_is_none_not_zero():
    img = _img(MINI314)
    t = _run([RA, img, "details", "/test/ok.txt"])
    assert "  USN:            (none)" in t.stdout and "USN journal ID: 0x0000000000000000" not in t.stdout, \
        t.stdout[-1200:]
    j = json.loads(_run([RA, img, "details", "/test/ok.txt", "--json"]).stdout)
    assert j.get("USN") in (None, "") and j.get("USNJournalID") is None, (j.get("USN"), j.get("USNJournalID"))


def test_n543_c_boot_volume_flags_in_the_flag_word_form():
    r = _run([RA, _img(MINI314), "boot"])
    m = re.search(r"Volume flags\s+0x2c\s+.*?\s(0x[0-9a-f]+(?: \([^)]*\))?)\s*$", r.stdout, re.M)
    assert m and re.fullmatch(r"0x[0-9a-f]+ \([A-Za-z|0-9x]+\)", m.group(1)), (m and m.group(1), r.stdout[:1500])
    v = _run([RA, _img(MINI314), "boot", "-v"]).stdout
    assert re.search(r"^volume_flags\s+0x[0-9a-f]+ \([A-Za-z|0-9x]+\)\s*$", v, re.M), v[-2000:]
    # what refs.sys does with each bit stays at -v, on its own row (it was the bracket after the value)
    assert re.search(r"^volume_flags_meaning\s+0x2 ", v, re.M), v[-2000:]
    vv = _run([RA, _img(MINI314), "boot", "-vv"]).stdout
    assert re.search(r"volume_flags   = 0x[0-9a-f]+ \([A-Za-z|0-9x]+\)$", vv, re.M), vv[-2000:]
    assert "meaning        = " in vv


# ═══ G2, C1 (group 4's draft) ═════════════════════════════════════════════════════════════════════════════════════

def test_g2_refsanalysis_details_says_when_accessed_is_updated():
    lines = _run([RA, _img(MINI314), "details", "/test/ok.txt"]).stdout.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith("  Accessed:"))
    assert lines[i + 1].strip() == ("(updated only while last-access updating is on: a Windows setting, not on the "
                                    "volume)"), lines[i:i + 2]


def test_c1_refsanalysis_rules_are_78_wide():
    out = _run([RA, _img(MINI314), "boot", "-vv"]).stdout.splitlines()
    rules = [x for x in out if x.strip() and set(x.strip()) <= {"=", "-"} and len(x) < 100]   # a table's own rule kept
    assert rules and all(len(x) == 78 for x in rules), sorted({len(x) for x in rules})
