"""E1 (1.14.0): two wording findings of the blind audit fixed without a test that names them (AUDIT_RESPONSE: UNTRIAGED
until this file). Each test is RED on v1.12.3 (FOREFST_REPO=analysis/verification/versions/v1.12.3), GREEN on dev.

K190: `_volume_times`' docstring said 'Used by --timestomp' while only `timeline` called it; `timestomp` had a second
copy (`_ts_vol_times`), and both returned (0, 0) in silence when the volume information could not be read. Now one
reader, `volume_information_read`, serves both commands and says why when it cannot read.

K194: `timestomp`'s help cited a removed `files --timestomp` column and described `--margin-days` as a tolerance of the
intrinsic signals only, though it gates the journal comparison too; the docs' JSON example carried fields the tool did not
emit. The help now names no such column and says the tolerance applies to `USN_CREATE_MISMATCH`; the documented row
(docs/examples/detect_timestomping.md, step 3) has exactly the fields `timestomp --json` writes for a row.
"""
import inspect
import json
import os
import re
import sys

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "examples", "detect_timestomping.md")
MFT = "step5/win11refstestmftecmd.raw"


def _tool():
    sys.path.insert(0, REPO)
    import forefst as F
    return F


def test_k190_one_reader_of_the_volume_times():
    F = _tool()
    assert not hasattr(F, "_volume_times") and not hasattr(F, "_ts_vol_times"), \
        "two copies of the volume-times reader, each silent on failure (K190)"
    for fn in (F.cmd_timestomp, F.cmd_timeline):
        assert "volume_information_read(" in inspect.getsource(fn), "%s does not use the one reader" % fn.__name__


def test_k194_timestomp_help_names_no_removed_column_and_scopes_margin_days():
    F = _tool()
    h = F.CMD_HELP["timestomp"]
    txt = repr(h)
    assert "files --timestomp" not in txt, "the help cites the removed `files --timestomp` column (K194)"
    md = [o for o in h["opts"] if o[0].startswith("--margin-days")]
    assert len(md) == 1 and "USN_CREATE_MISMATCH" in md[0][1], \
        "--margin-days is described as an intrinsic-only tolerance; it gates the journal comparison too (K194)"


def test_k194_the_documented_json_row_has_the_emitted_fields(tmp_path):
    text = open(DOC, encoding="utf-8").read()
    # N633 (1.14.0 RC3): the page shows the row as console output (gate 7r: the command, then "[...]" around the one
    # object it quotes); the object is read back from between those lines
    m = re.search(r"flagged row[^\n]*\n\n```(?:json|text)\n(.*?)\n```", text, re.S)
    MC._fx(m, "the documented JSON row is not found in %s" % DOC)
    body = "\n".join(ln for ln in m.group(1).splitlines()
                     if not ln.startswith("$ ") and ln.strip() != "[...]").strip().rstrip(",")
    documented = set(json.loads(body))
    out = str(tmp_path / "ts.json")
    rc, log = MC.run_tool(MC.FOREFST, MC.corpus(MFT), "timestomp", "--json", out)
    MC._fx(os.path.isfile(out), "timestomp --json wrote no file" + MC._ctx(rc, log[-1500:]))
    doc = json.load(open(out, encoding="utf-8"))
    # 1.14.0 lists the rows under `Rows`; an older release wrote them under another key or as a bare list
    rows = doc if isinstance(doc, list) else next(
        (v for k, v in sorted(doc.items(), key=lambda kv: kv[0] != "Rows") if isinstance(v, list) and v
         and isinstance(v[0], dict)), None)
    MC._fx(rows, "timestomp --json wrote no row on win11refstestmftecmd")
    emitted = set(rows[0])
    assert documented == emitted, "documented fields %s, emitted %s (K194)" % (
        sorted(documented ^ emitted & documented), sorted(emitted - documented))
