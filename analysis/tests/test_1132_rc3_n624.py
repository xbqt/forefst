"""N624 (1.14.0 RC3): two degenerate bundles of win11refsmini, exported from a scratch copy.

(a) `--btree-mode per-object`: each object's pages without their addresses -- read back as a volume of 0 objects while
    its banner claimed the files' names. The reader must refuse it (exit 1) with the reason; its manifest says what it
    is. (b) `--what vbr,chkp,supb,mlog,usn` (no B+-tree page, so no Container Table): the Object Table's roots were read
    and named at an untranslated PLCN; they must be said to be unverifiable, named by VLCN. RED on forefst 1eb4c582.
"""
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

BASE, CAP = "step1/win11refsmini.raw", 64 << 20


def _flat(t):
    return " ".join(t.split())


def _bundle(args, cmd):
    with MC.scratch_copy(BASE, CAP) as (src, p):
        d = tempfile.mkdtemp(prefix="rc3_n624_", dir=os.path.dirname(p))
        out = os.path.join(d, "bundle")
        try:
            MC.run_tool(MC.FOREFST, p, "export", "metadata", "-o", out, *args)
            MC._fx(os.path.isfile(os.path.join(out, "manifest.json")), "no bundle was written")
            man = json.load(open(os.path.join(out, "manifest.json"), encoding="utf-8"))
            names = set(os.listdir(out))
            rc, text = MC.run_tool(MC.FOREFST, out, *cmd)
        finally:
            shutil.rmtree(d)
    return names, man, rc, text


def test_n624_a_per_object_bundle_is_refused_as_a_volume():
    names, man, rc, text = _bundle(["--btree-mode", "per-object"], ["summary"])
    MC._fx(any(n.startswith("object_") and n.endswith(".btree") for n in names)
           and not any(n.startswith("metadata_pages") for n in names), "not a per-object bundle")
    t = _flat(text)
    assert rc == 1 and re.search(r"per-object", t) and "cannot be read back as a volume" in t \
        and not re.search(r"\b0 objects\b", t), "a per-object bundle cannot be rehydrated: refused, exit 1" \
        + MC._ctx(rc, text[-1500:])
    carries = " ".join(man.get("carries") or man.get("Carries") or [])
    assert "without the pages' addresses" in carries, "the manifest says what the bundle is: %r" % carries


def test_n624_b_object_table_roots_without_a_container_table_are_unverifiable_by_vlcn():
    names, man, rc, text = _bundle(["--what", "vbr,chkp,supb,mlog,usn"], ["summary"])
    MC._fx(not any(n.startswith(("metadata_", "object_")) for n in names), "the bundle carries B+-tree pages")
    t = _flat(text)
    assert not re.search(r"Object Table: [^.]*root [05] \(PLCN 0x", t) \
        and re.search(r"Object Table: [^.]*root 0 \(VLCN 0x[0-9a-f]+\)[^.]*cannot be translated", t), \
        "no Container Table: the Object Table's roots are unverifiable, named by VLCN" + MC._ctx(rc, text[-2500:])


def test_n624_control_a_packed_bundle_reads_as_its_volume():
    names, man, rc, text = _bundle([], ["summary"])
    t = _flat(text)
    assert rc == 0 and "per-object" not in t and not re.search(r"cannot be translated", t), \
        "the default (packed) bundle reads as the volume, as before" + MC._ctx(rc, text[-1500:])
