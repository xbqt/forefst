"""U14 (1.14.1, the maintainer 2026-11-27: export recyclebin with the payloads' named streams): `export recyclebin` writes
each recycled payload's named streams beside it as `<name>__<stream>`, each with its own row in `export_index.csv`
(written before 1.14.1's release check found the index itself missing: N681). Volume: win11bidule (step6), whose recycle
bin holds three payloads, each with a `Zone.Identifier` stream (inline, 55 bytes) -- so this test exercises the inline
form only. The streams expected are read independently, from `ads --json`; each written stream is compared with
`export ads` of the same stream."""
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
RB = "step6/win11bidule.raw"


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(argv, cwd=None, text=True):
    return subprocess.run([sys.executable, "-B", FOREFST] + argv, capture_output=True, text=text, timeout=1800,
                          cwd=cwd)


def _recycled_streams(img):
    """(FullPath, Stream) of every named stream of a file under $RECYCLE.BIN/<SID>/$R*, from `ads --json`."""
    r = _run([img, "ads", "--json"])
    assert r.returncode == 0, r.stderr[-600:]
    out = set()
    for row in json.loads(r.stdout):
        parts = row["FullPath"].split("/")
        if (not row.get("IsDirectory") and len(parts) == 3 and parts[0] == "$RECYCLE.BIN"
                and parts[2].startswith("$R")):
            out.add((row["FullPath"], row["Stream"]))
    return out


def test_u14_each_payloads_named_streams_are_written_beside_it_and_indexed(tmp_path):
    img = _img(RB)
    want = _recycled_streams(img)
    assert len(want) == 3, want                      # the volume as measured 2026-11-27: one Zone.Identifier per payload
    d = str(tmp_path / "out")
    try:
        r = _run([img, "export", "recyclebin", d], cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr[-800:]
        assert "wrote 3 recovered payload(s) and 3 named stream(s)" in r.stderr, r.stderr[-800:]
        with open(os.path.join(d, "export_index.csv"), newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        payload = {x["FullPath"]: x for x in rows if ":" not in x["FullPath"]}
        streams = {tuple(x["FullPath"].rsplit(":", 1)): x for x in rows if ":" in x["FullPath"]}
        assert set(streams) == want, (sorted(streams), sorted(want))
        on_disk = sorted(n for n in os.listdir(d) if n not in ("export_index.csv", "holes.json"))
        assert sorted(x["ContentFile"] for x in rows) == on_disk, (rows, on_disk)
        for (fp, st), x in sorted(streams.items()):
            p = payload.get(fp)
            assert p, "no payload row for %s" % fp
            assert x["ContentFile"] == p["ContentFile"] + "__" + st, (x, p)
            assert x["ObjectRef"] == p["ObjectRef"] and x["ObjectRef"], (x, p)
            data = open(os.path.join(d, x["ContentFile"]), "rb").read()
            assert hashlib.sha256(data).hexdigest() == x["SHA256"], x
            ref = _run([img, "export", "ads", "%s:%s" % (fp, st), "-o", "-"], text=False)
            assert ref.returncode == 0 and ref.stdout == data, (fp, st, ref.returncode, ref.stdout[:80], data[:80])
    finally:
        shutil.rmtree(d, ignore_errors=True)          # the export writes about 52 MB
