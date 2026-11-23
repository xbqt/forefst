"""The code half, group 6 (comments and instruments), 1.14.0: RUNNING_LOG N170 (what is left of it: E151 / N232's
inline-holder docstring, E78's Record Integrity preamble), I6 (what a metadata bundle carries), the lab26h2 exclusion
(PLAN section 10.2's last paragraph). Written RED before the fix (`analysis/reports/v1.13.2/RC1D/G6/`). Volume:
win11refsmini (step1)."""
import json
import os
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
MINI314 = "step1/win11refsmini.raw"
VERIF = os.path.join(os.path.dirname(REPO), "analysis", "verification")


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(argv, timeout=1800):
    return subprocess.run([sys.executable, "-B"] + argv, capture_output=True, text=True, timeout=timeout)


# ═══ the lab26h2 exclusion ════════════════════════════════════════════════════════════════════════════════════════

def test_exclusion_lab26h2_is_never_read_by_a_corpus_glob():
    if not os.path.isfile(os.path.join(VERIF, "corpus_exclusions.py")):
        pytest.skip("analysis/verification is not in this tree")
    sys.path.insert(0, VERIF)
    import corpus_exclusions as CE
    import io
    CE._SAID.discard("lab26h2.raw")
    buf = io.StringIO()
    assert CE.keep(["a/x.raw", "a/step9blindaudit/lab26h2.raw"], stream=buf) == ["a/x.raw"]
    assert "excluded by name: lab26h2.raw" in buf.getvalue()


def test_exclusion_gate_1n_passes_and_names_both():
    gate = os.path.join(VERIF, "check_corpus_exclusions.py")
    if not os.path.isfile(gate):
        pytest.skip("analysis/verification is not in this tree")
    r = _run([gate], timeout=300)
    assert r.returncode == 0 and "PASS" in r.stdout, r.stdout[-1500:]
    assert "blindaudit2.raw" in r.stdout and "lab26h2.raw" in r.stdout, r.stdout[-600:]


# ═══ E151 / N232 and E78: comments and the preamble say what the code does ════════════════════════════════════════

def test_e151_the_inline_holder_docstring_reads_the_key_index_first():
    doc = F._parse_inline_holder_extents.__doc__
    assert "aggregate/fence" not in doc and "key index" in doc and "superseded" in doc, doc[:900]
    assert "aggregate/fence" not in open(FOREFST, encoding="utf-8").read()


def test_e78_the_record_integrity_preamble_names_the_32_bit_fold():
    r = _run([FOREFST, _img(MINI314), "mlog", "--stats"])
    assert r.returncode in (0, 2), r.stderr[-800:]
    flat = " ".join(r.stdout.split())
    assert "it is the XOR of the record's 32-bit words: any reordering of those words, or changes whose XOR " \
           "cancels, keep the value" in flat, flat[:2000]
    assert "the same bits changed in two words" not in flat


def test_e78_the_fold_docstring_and_help_mlog_name_the_32_bit_blind_spot():
    """E78's amendment: the fold's docstring and `help mlog` go with the preamble. The value is the XOR of the record's
    32-bit words, so a reordering of those words, or changes that cancel, keep it; 'catches edits' overstates it."""
    doc = " ".join((F.mlog_verify_record.__doc__ or "").split())
    assert "32-bit words" in doc and "any reordering of those words" in doc, doc[-1400:]
    r = _run([FOREFST, _img(MINI314), "help", "mlog"])
    assert r.returncode == 0, r.stderr[-800:]
    flat = " ".join(r.stdout.split())
    assert "catches damage and edits" not in flat, flat[-1500:]
    assert "a single changed bit or byte is caught, a reordering of the record's 32-bit words or changes that " \
           "cancel are not" in flat, flat[-1500:]


# ═══ I6: what a metadata bundle carries ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def bundles(tmp_path_factory):
    out = {}
    for name, what in (("full", None), ("boot", "vbr,chkp,supb")):
        d = str(tmp_path_factory.mktemp("g6") / name)
        r = _run([FOREFST, _img(MINI314), "export", "metadata", "-o", d] + (["--what", what] if what else []))
        assert r.returncode == 0, r.stderr[-800:]
        out[name] = (d, r, json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8")))
    return out


def test_i6_the_manifest_says_what_the_bundle_carries(bundles):
    d, r, man = bundles["full"]
    c = man.get("Carries")
    assert c, sorted(man)
    flat = " | ".join(c)
    for word in ("name, times and attributes", "SIDs", "$I records", "inline", "free space",
                 "the path of the source image and the name of the host"):
        assert word in flat, (word, c)


def test_i6_a_boot_only_bundle_says_only_what_it_carries(bundles):
    d, r, man = bundles["boot"]
    assert man.get("Carries") == ["the boot sector, superblock and checkpoint copies",
                                  "the path of the source image and the name of the host the bundle was made on"], \
        man.get("Carries")


def test_i6_the_export_reader_and_verify_bundle_say_it(bundles):
    d, r, man = bundles["full"]
    assert "It carries:" in r.stdout, r.stdout[-1200:]
    s = _run([FOREFST, d, "summary"])
    assert "It carries:" in s.stderr, s.stderr[:1500]
    v = _run([FOREFST, d, "verify-bundle"])
    assert "note: carries:" in v.stdout, v.stdout[-1500:]
