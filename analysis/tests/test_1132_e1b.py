"""Wave E step E1b (1.14.0, `analysis/reports/v1.13.2/fixes/WAVEE_PLAN.md`): `timeline` selection and help, `snapshots`.

What each group asserts
-----------------------
C8 / I2  the `timeline` help says what --oid, --file and --fileref cover (a file stays under its home directory after
         a move; --file matches an MLog row by its directory's path); --fileref's note gives no advice that does not
         work ("use --file NAME to see them").
N256     `timeline --fileref OID:0x0` (a directory, as `files` prints its ObjectRef) keeps the directory's $SI events.
C2 / I5 / N320  `snapshots`: the record value is not called "Resident"; +0x28 is the valid data length, +0x30 the
         allocation; the version's time (+0x4C) is printed; no "Snapshot ID ?"; the JSON keys say the same.
N321     `snapshots` and `files`' SnapshotCount read one record's snapshots alike.
"""
import csv
import io
import json
import os
import re

import pytest

from _repo import REPO                                   # noqa: F401  layout-independent; see _repo.py

import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21: internal names)
import test_1132_red_b2_wording as W                     # noqa: E402  (the volumes and the runners)

_SNAPS = "step3/win11refs2tsnapshots.raw"


@pytest.fixture(scope="module")
def dvol(tmp_path_factory):
    return W._DelVol(tmp_path_factory.mktemp("e1b"))


def _help(cmd, tmp):
    rc, out, err = W._run([os.path.join(W.REPO, "forefst.py"), "--help", cmd], cwd=str(tmp))
    return out


def test_c8_timeline_help_says_what_each_selector_covers(tmp_path):
    h = re.sub(r"\s+", " ", _help("timeline", tmp_path))
    assert "a file stays under its home directory after a move" in h, h
    # acceptance 1.14.0 (Q-C): an MLog row carries its object's path today (`mlog`'s PathToday), so --file finds a
    # file's MLog events; the help says what --file matches
    assert "keep events whose path today (a USN row: its name) contains SUB" in h, h
    assert "OID:0x0 for a directory" in h, h


def test_i2_fileref_note_gives_no_advice_that_does_not_work():
    src = open(os.path.join(W.REPO, "forefst.py"), encoding="utf-8").read()
    assert "use --file NAME to see them" not in src


def test_n256_fileref_of_a_directory_keeps_its_si_events(dvol, tmp_path):
    rc, out, err = dvol.run("files", "-q", "--csv")
    d = next(r for r in csv.DictReader(io.StringIO(out)) if r["FileName"] == "d")
    rc, out, err = dvol.run("timeline", "--csv", "-", "--fileref", d["ObjectRef"], "--source", "SI")
    rows = list(csv.DictReader(io.StringIO(out)))
    assert rows and all(r["Source"] == "$SI" for r in rows), W._ctx(rc, out, err)      # K21 (acceptance 1.14.0)


def test_n256_control_fileref_of_a_file(dvol, tmp_path):
    rc, out, err = dvol.run("timeline", "--csv", "-", "--fileref", "0x761:0x2", "--source", "SI")
    assert list(csv.DictReader(io.StringIO(out))), W._ctx(rc, out, err)


def test_c2_i5_n320_snapshots_text_names_its_fields(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _SNAPS, "snapshots", "-v")
    assert rc == 0 and "Resident:" not in out and "Snapshot ID" not in out and "Alloc size" not in out, out[:1500]
    assert re.search(r"Record value: +\d+ bytes", out) and re.search(r"Valid data length: +\d+ bytes", out), out[:1500]
    m = re.search(r'\[1\] "test2"\n\s+Created:\s+(2026-05-16T17:00:20\.\d{7}Z)', out)        # K5 (1.14.0)
    assert m, "the version's own time is not printed:\n" + out[:1500]


def test_n320_snapshots_json_keys(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _SNAPS, "snapshots", "--json")
    j = json.loads(out)
    # acceptance 1.14.0 (K21): the output names of those fields
    k = F.out_key
    s = j[k("files")][0][k("snapshots")][0]
    assert {k("valid_data_length"), k("allocated_size"), k("data_sub_id")} <= set(s), s
    assert not {k("allocation_size"), k("snapshot_id"), "allocation_size", "snapshot_id"} & set(s) \
        and k("resident_bytes") not in j[k("files")][0], s


def test_n320_the_version_time_is_the_one_snapshot_meta_reads(tmp_path):
    img = W._image_or_skip(_SNAPS)
    f, ps, cs, tr, roots, om, vmaj, vmin, _c = F.bootstrap(img, None)
    try:
        res = []
        F._find_snapshot_files(f, ps, cs, tr, om, 0x600, "", 0, F.DEFAULT_DEPTH, res)
        assert res
        for r in res:
            meta = {n: ts for n, _sid, ts in F._snapshot_meta(r["vd"], (f, ps, cs, tr))}
            for s in r["snapshots"]:
                if s["is_true_snapshot"]:
                    assert s.get("creation_time", 0) == meta.get(s["name"]), (r["path"], s, meta)
    finally:
        f.close()


def test_n321_one_reader_for_snapshots_and_snapshot_count(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _SNAPS, "files", "-q", "--csv")
    want = {r["FullPath"]: int(r["SnapshotCount"] or 0) for r in csv.DictReader(io.StringIO(out))
            if int(r["SnapshotCount"] or 0)}
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _SNAPS, "snapshots", "--json")
    got = {f_["path"]: len(f_["snapshots"]) for f_ in jdoc(json.loads(out))["files"]}
    assert got == want, (got, want)


# ── N257: one wording for the change journal's state ───────────────────────────────────────────────────────────────

_NOJ = "step3/win11refs2tsnapshots.raw"                 # a volume whose system metadata table holds no journal


@pytest.mark.parametrize("args", [("usn",), ("timestomp",), ("timeline", "--fast", "--limit", "1"), ("summary",)],
                         ids=["usn", "timestomp", "timeline", "summary"])
def test_n257_inactive_in_summarys_words(tmp_path, args):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _NOJ, *args)
    assert re.search(r"USN [Jj]ournal:\s+Inactive\b", out), W._ctx(rc, out[:3000], err)
    for old in ("journal not activated", "inactive on this image", "absent or unreadable"):
        assert old not in out + err, old


def test_n257_timestomp_json_says_the_state(tmp_path):
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _NOJ, "timestomp", "--json")
    assert jdoc(json.loads(out))["journal_state"] == "Inactive"


@pytest.mark.parametrize("args, rc_want", [(("usn",), 2), (("timestomp",), None), (("summary",), None)],
                         ids=["usn", "timestomp", "summary"])
def test_n257_unknown_where_the_system_metadata_table_is_not_there(dvol, args, rc_want):
    """The synthetic volume has no OID 0x520: whether there is a journal is not known (`summary` said so already)."""
    rc, out, err = dvol.run(*args)
    text = out + err
    assert re.search(r"(USN [Jj]ournal:\s+unknown|not determined)", text) and "Inactive" not in text, W._ctx(rc, out, err)
    assert rc_want is None or rc == rc_want, W._ctx(rc, out, err)
