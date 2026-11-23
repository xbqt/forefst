"""Wave E step E1a (1.14.0, `analysis/reports/v1.13.2/fixes/WAVEE_PLAN.md`): forefst wording and usage.

What each group asserts
-----------------------
N147   a word a command does not take is a usage error (exit 1, the word named, nothing run or written): every
       command that takes options only, and one more word after a command that takes one (`specials TYPE`,
       `extract PATH`, `export <bulk> DIR`); the documented positional forms keep working (controls).
N276   `deleted --csv / --json / --jsonl [FILE]`: without a FILE, stdout holds the records alone (the report goes to
       stderr); with a FILE, the FILE holds the records and stdout the report; two formats are refused.
N147   `reparse --json FILE` writes the JSON to FILE (the FILE was a stray word and the JSON went to the screen).

Volumes: the synthetic volumes of `test_1132_red_b2_wording.py` (one directory `d` with `a.txt`, a remnant
`gone.txt` in the page slack).
"""
import csv
import io
import json
import os
import re
import struct

import pytest

from _repo import REPO                                   # noqa: F401  layout-independent; see _repo.py

import test_1132_red_b2_wording as W                     # noqa: E402  (the volumes and the runners)


@pytest.fixture(scope="module")
def dvol(tmp_path_factory):
    return W._DelVol(tmp_path_factory.mktemp("e1a"))


_STRAY = "zz_stray_word"

# every command that takes options only, and the commands that take one word, given one word more
_OPTIONS_ONLY = ["files", "summary", "fastsummary", "integrity", "usn", "mlog", "timeline", "timestomp", "recyclebin",
                 "security", "reparse", "snapshots", "dataruns", "deleted"]
_ONE_WORD = [("specials", "ads"), ("ads", None), ("extract", "/d/a.txt"), ("export", "resident-all", "OUT"),
             ("export", "recyclebin", "OUT"), ("export", "metadata", "OUT"), ("export", "reparse"),
             ("export", "snapshots", "OUT"), ("export", "deleted", "OUT")]


def _refused_naming(rc, out, err, word):
    return rc == 1 and re.search(r"unexpected argument: '%s'" % re.escape(word), err)


@pytest.mark.parametrize("cmd", _OPTIONS_ONLY)
def test_n147_a_command_that_takes_options_only_refuses_a_stray_word(dvol, tmp_path, cmd):
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, cmd, _STRAY)
    assert _refused_naming(rc, out, err, _STRAY), "`%s %s`" % (cmd, _STRAY) + W._ctx(rc, out, err)
    assert not wrote, "`%s %s` was refused but wrote %r" % (cmd, _STRAY, wrote)


@pytest.mark.parametrize("words", _ONE_WORD, ids=lambda w: "-".join(x for x in w if x))
def test_n147_a_command_that_takes_one_word_refuses_a_second(dvol, tmp_path, words):
    args = [w for w in words if w] + [_STRAY]
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, *args)
    assert _refused_naming(rc, out, err, _STRAY), "`%s`" % " ".join(args) + W._ctx(rc, out, err)
    assert not wrote, "`%s` was refused but wrote %r" % (" ".join(args), wrote)


@pytest.mark.parametrize("args, rc_ok", [(("search", "a"), (0,)), (("details", "/d/a.txt"), (0,)),
                                         (("extract", "/d/a.txt"), (2,)), (("specials", "ads"), (0,)),
                                         (("usn", "--csv", "-"), (0, 2)), (("deleted", "--log", "LOG.txt"), (0,)),
                                         (("export", "-o", "BUNDLE"), (0,))],
                         ids=["search", "details", "extract", "specials", "usn-csv-stdout", "deleted-log",
                              "export-o"])
def test_n147_control_the_documented_words_still_run(dvol, tmp_path, args, rc_ok):
    """`extract` exits 2 here: this volume's a.txt is a split row without a backing row, which 1.14.0 reports as a
    recorded skip ("the record holding its data ... was not found", WE-2; before: "not found", exit 1); the control is
    that the word is read as the path, not refused."""
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, *args)
    assert rc in rc_ok and "unexpected argument" not in err, "`%s`" % " ".join(args) + W._ctx(rc, out, err)


@pytest.mark.parametrize("fmt", ["csv", "json", "jsonl"])
def test_n276_deleted_records_on_stdout_alone(dvol, tmp_path, fmt):
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, "deleted", "--" + fmt)
    assert rc == 0 and not wrote, "`deleted --%s`" % fmt + W._ctx(rc, out, err)
    assert "Deleted File Finder" not in out and "Deleted File Finder" in err, (
        "the report is not on stderr alone" + W._ctx(rc, out, err))
    if fmt == "csv":
        rows = list(csv.DictReader(io.StringIO(out)))
        assert rows and out.startswith("FileName,") and any(r["FileName"] == "gone.txt" for r in rows), out[:800]
    elif fmt == "json":
        rows = json.loads(out)
        assert any(r.get("FileName") == "gone.txt" for r in rows), out[:800]
    else:
        rows = [json.loads(l) for l in out.splitlines() if l.strip()]
        assert any(r.get("FileName") == "gone.txt" for r in rows), out[:800]


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_n276_deleted_records_to_a_file_and_the_report_on_stdout(dvol, tmp_path, fmt):
    rc, out, err, wrote, d = dvol.run_in(tmp_path, "deleted", "--" + fmt, "REC")
    assert rc == 0 and wrote == ["REC"], "`deleted --%s REC` wrote %r" % (fmt, wrote) + W._ctx(rc, out, err)
    assert "Deleted File Finder" in out, "the report is not on stdout" + W._ctx(rc, out, err)
    with open(os.path.join(d, "REC"), encoding="utf-8") as fh:
        text = fh.read()
    assert "gone.txt" in text and (text.startswith("FileName,") if fmt == "csv" else json.loads(text)), text[:400]


def test_n276_two_formats_are_refused(dvol, tmp_path):
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, "deleted", "--csv", "--json")
    assert rc == 1 and "choose one output format" in err and not wrote, W._ctx(rc, out, err)


def test_n147_reparse_json_file_writes_the_file(dvol, tmp_path):
    rc, out, err, wrote, d = dvol.run_in(tmp_path, "reparse", "--json", "REP.json")
    assert rc == 0 and wrote == ["REP.json"], "`reparse --json REP.json` wrote %r" % wrote + W._ctx(rc, out, err)
    with open(os.path.join(d, "REP.json"), encoding="utf-8") as fh:
        assert "reparse_points" in jdoc(json.load(fh))                  # K21: internal names


def test_n147_control_reparse_json_to_stdout(dvol, tmp_path):
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, "reparse", "--json")
    assert rc == 0 and not wrote and "reparse_points" in jdoc(json.loads(out)), W._ctx(rc, out, err)


# ── C3 / N149 class sites: the other per-file counts of `summary`, and N279 / N280 ──────────────────────────────

class _FlaggedScenario(W._Scenario):
    """W's N149 rows (b1.txt and b2.txt: two names of one file, 0x761:0x3) with the fields `flags` sets on rows."""

    def __init__(self, tmp, flags):
        super().__init__(tmp, W._N149_ROWS)
        for n, fields in flags.items():
            self.spec[n].update(fields)
        with open(os.path.join(self.tmp, "walk_spec.json"), "w") as fh:
            json.dump(self.spec, fh)


_ALL_FLAGS = {"is_encrypted": True, "has_integrity": True, "is_compressed": True, "has_ads": True,
              "snapshot_count": 2}


@pytest.fixture(scope="module")
def linked_flags(tmp_path_factory):
    return _FlaggedScenario(tmp_path_factory.mktemp("n149f"), {"b1.txt": _ALL_FLAGS, "b2.txt": _ALL_FLAGS})


@pytest.fixture(scope="module")
def single_flags(tmp_path_factory):
    return _FlaggedScenario(tmp_path_factory.mktemp("n149c"), {"c.txt": _ALL_FLAGS})


def _content_values(out):
    block = out                     # forefst prints these in its content block, refsanalysis in a later one
    got = {}
    for label in ("Encrypted files", "Integrity files", "Compressed files", "ADS host files", "Snapshot versions"):
        m = re.search(r"^\s*%s:\s*(\d+)(?: \(across (\d+) files?\))?" % re.escape(label), block, re.M)
        assert m, "no %r line:\n%s" % (label, block)
        got[label] = (int(m.group(1)), m.group(2) and int(m.group(2)))
    return got


def _summary_args(tool):
    return ("summary++",) if tool.endswith("refsanalysis.py") else ("summary",)     # refsanalysis: the extended form


@pytest.mark.parametrize("tool", W._TOOLS)
def test_n149_the_flag_counts_count_a_hard_linked_file_once(linked_flags, tool):
    rc, out, err = linked_flags.run(tool, *_summary_args(tool))
    assert rc == 0, W._ctx(rc, out, err)
    got = _content_values(out)
    want = {"Encrypted files": (1, None), "Integrity files": (1, None), "Compressed files": (1, None),
            "ADS host files": (1, None), "Snapshot versions": (2, 1)}
    assert got == want, "a file with two names is counted per name: %r" % got


@pytest.mark.parametrize("tool", W._TOOLS)
def test_n149_control_a_file_with_one_name(single_flags, tool):
    rc, out, err = single_flags.run(tool, *_summary_args(tool))
    assert rc == 0, W._ctx(rc, out, err)
    got = _content_values(out)
    assert got == {"Encrypted files": (1, None), "Integrity files": (1, None), "Compressed files": (1, None),
                   "ADS host files": (1, None), "Snapshot versions": (2, 1)}, got


def test_n149_summary_json_counts_files_and_names(linked_flags):
    rc, out, err = linked_flags.run(W.FOREFST, "summary", "--json")
    j = jdoc(json.loads(out), F._SUMMARY_KEYS)                         # K21: internal names
    # acceptance 1.14.0 (N305 / K17): resident_files / non_resident_files were removed -- Residency counts every category
    assert (j["files"], j["file_names"]) == (3, 4), {k: j.get(k) for k in ("files", "file_names")}
    assert j["residency"] == {"inline": 1, "extents": 2, "snapshot-shared": 0, "unallocated": 0, "unknown": 0}, j


# a.txt of the deleted-view volume is a split name whose backing row the walk does not find
def _csv_row(out, name):
    return next(r for r in csv.DictReader(io.StringIO(out)) if r["FileName"] == name)


def test_n279_files_and_search_say_unknown_for_a_file_whose_data_record_is_not_found(dvol):
    rc, out, err = dvol.run("files", "-q", "--csv")
    a, d = _csv_row(out, "a.txt"), _csv_row(out, "d")
    assert a["RecordPlacement"] == "split" and a["DataResidency"] == "unknown", a
    assert d["DataResidency"] == "", "a directory has no data residency: %r" % d["DataResidency"]
    rc, out, err = dvol.run("search", "a", "--json")
    # acceptance 1.14.0 (K21, decision 37): search's JSON rows take `files`' names -- FileName, DataResidency
    hit = [r for r in json.loads(out) if r.get("FileName") == "a.txt"]
    assert hit and hit[0]["DataResidency"] == "unknown", hit


def test_n279_details_says_unknown_not_directory(dvol):
    rc, out, err = dvol.run("details", "/d/a.txt")
    m = re.search(r"^\s*Data residency:\s*(.+)$", out, re.M)
    assert m and m.group(1).strip() == "unknown", W._ctx(rc, out, err)


@pytest.fixture(scope="module")
def split_vol(tmp_path_factory):
    """d/a.txt as a split name row (key flags 0x02, the 84-byte value) whose backing row is nowhere."""
    BD = W._bd()
    v = BD.DirVol()
    key = struct.pack("<HH", 0x30, 2) + "a.txt".encode("utf-16-le")
    v.objects = v.tree({0x600: {"name": ""},
                        0x761: {"parent": 0x600, "name": "d", "files": [BD._row(key, BD._file_value(2, 0x761, BD._T))]}})
    return v.write(str(tmp_path_factory.mktemp("n279") / "split.raw"))


def test_n279_dataruns_does_not_count_it_as_extents(split_vol, tmp_path):
    rc, out, err = W._tool(W.FOREFST, split_vol, "dataruns", cli=W._SYN, cwd=str(tmp_path))
    assert re.search(r"Total files analyzed:\s*1\b", out), W._ctx(rc, out, err)
    assert re.search(r"Not determined \(the record holding the data was not found\):\s*1\b", out), W._ctx(rc, out, err)
    assert re.search(r"Data in extents:\s*0\b", out), W._ctx(rc, out, err)


def test_n280_summary_names_itself(dvol):
    rc, out, err = dvol.run("summary")
    assert "ReFS Volume Summary" in out and "Fast Extended Summary" not in out, out[:400]


def test_n280_control_fastsummary_title(dvol):
    rc, out, err = dvol.run("fastsummary")
    assert "ReFS Volume Fast Extended Summary" in out, out[:400]


# ── N277: counts of objects, names beside them (oracle: the same tool's `files --csv`, one row per name) ─────────────

import ast                                               # noqa: E402

import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21 / K10 readers)
from conftest import jget                                 # noqa: E402  (K21 readers)

_SPECIALS = "win11refs2tspecials.raw"


def _files_rows(tmp):
    rc, out, err = W._image_run(tmp, W.FOREFST, _SPECIALS, "files", "-q", "--csv")
    return list(csv.DictReader(io.StringIO(out)))


def _objects(rows, pred):
    hit = [r for r in rows if pred(r)]
    return len({r["ObjectRef"] for r in hit}), len(hit)


def test_n277_specials_counts_objects_and_names(tmp_path):
    rows = _files_rows(tmp_path)
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _SPECIALS, "specials")
    got = {m.group(1): (int(m.group(2)), int(m.group(3)))
           for m in re.finditer(r"^\s+(ads|reparse|hardlink)\s+(\d+)\s+(\d+)\s", out, re.M)}
    # acceptance 1.14.0 (K19): a CSV boolean is true / false
    want = {"ads": _objects(rows, lambda r: r["HasADS"] == "true"),
            "reparse": _objects(rows, lambda r: bool(r["ReparseTag"])),
            "hardlink": _objects(rows, lambda r: r["IsDirectory"] == "false" and int(r["HardLinkCount"] or 1) > 1)}
    assert got == want, "specials (objects, names) %r, files --csv gives %r" % (got, want)
    assert want["ads"][0] < want["ads"][1], "the sample has no object with two names and a stream: nothing tested"


def test_n277_security_files_counts_files_dirs_and_names(tmp_path):
    rows = _files_rows(tmp_path)
    files = len({r["ObjectRef"] for r in rows if r["IsDirectory"] == "false"})       # K19 (1.14.0)
    dirs = sum(1 for r in rows if r["IsDirectory"] == "true")
    rc, out, err = W._image_run(tmp_path, W.FOREFST, _SPECIALS, "security", "--files")
    m = re.search(r"Total: (\d+) files? and (\d+) director(?:y|ies) \((\d+) names?\) across (\d+) SecurityId", out)
    assert m and (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (files, dirs, len(rows)), (
        m and m.group(0), (files, dirs, len(rows)))
    assert "owner SID" not in out.split("Name ")[0], "the grouping is by SecurityId, not by owner SID"


def test_n155_security_and_reparse_walk_the_whole_tree():
    src = open(os.path.join(W.REPO, "forefst.py"), encoding="utf-8").read()
    assert "_walk_dir_files_with_sid(f, ps, cs, tr, obj_map, 0x600, \"\", 0, 10)" not in src
    assert "walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, 100, True)" not in src
    assert "_walk_dir_for_reparse(f, ps, cs, tr, obj_map, 0x600, \"\", 0, 100)" not in src


# ── N220 / N303 / N297: `details <file>` ─────────────────────────────────────────────────────────────────────────────

def test_n220_details_gives_both_axes_and_every_files_link_count(dvol):
    rc, out, err = dvol.run("details", "/d/a.txt")
    assert re.search(r"^\s*Record placement:\s+split$", out, re.M), W._ctx(rc, out, err)
    assert re.search(r"^\s*Hard-link count:\s+1$", out, re.M), W._ctx(rc, out, err)
    assert len(re.findall(r"^\s*Internal flags:", out, re.M)) <= 1, W._ctx(rc, out, err)


def test_n220_control_a_directory_has_no_placement_line(dvol):
    rc, out, err = dvol.run("details", "/d")
    assert "Record placement:" not in out and "Hard-link count:" not in out, out[:600]


# ── N281 / N156 / N161 / N282 / N293 / N275: words and one source ───────────────────────────────────────────────────

def test_n281_prior_version_is_not_a_stream_snapshot(dvol):
    for args in (("--help", "snapshots"), ("--help", "specials"), ("--help", "export"), ("--help", "deleted")):
        rc, out, err = W._run([os.path.join(W.REPO, "forefst.py")] + list(args), cwd=dvol.tmp)
        assert not re.search(r"(?i)prior[ -]versions?\b", out), "%s: %s" % (args, re.findall(r"(?i).{40}prior.{40}", out))


def test_n156_internal_flag_0x02_is_case_sensitive():
    assert F.internal_flags_str(0x02) == "0x2 (CaseSensitive)"
    import refsanalysis as RA
    assert RA._INTERNAL_FLAGS is F._INTERNAL_FLAG_LABELS


_BARE = re.compile(r"(?i)(?<![\w-])(?:non-?)?resident(?![\w-])")
# the bare words still in printed text, each with the step that removes it
_BARE_LEFT = {"    Resident:     ": "C2, step E1b", "ads, wsl, sparse, snapshot, directory, resident, hardlink":
              "the `--filter resident` alias, removed with IsResident in E2"}


def test_n161_no_bare_resident_word_in_forefst_text():
    tree = ast.parse(open(os.path.join(W.REPO, "forefst.py"), encoding="utf-8").read())
    parents = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    bad = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str) and _BARE.search(n.value)):
            continue
        p = parents.get(n)
        if isinstance(p, ast.Expr):
            continue                                     # a docstring
        if n.value in _BARE_LEFT or re.fullmatch(r"(non-)?resident", n.value):
            continue                                     # a key the code compares, not text
        bad.append((n.lineno, n.value[:90]))
    assert not bad, "bare 'resident' words in forefst text:\n  %s" % "\n  ".join("fd:%d %r" % b for b in bad)


def test_n282_named_streams_use_the_data_residency_words(tmp_path):
    """step6/win11refs8g: 179 streams in extents (the 2 KB..2 MB sweep), 28 inline; 1.13.1 called the first
    'extent-backed'."""
    rc, out, err = W._image_run(tmp_path, W.FOREFST, "step6/win11refs8g.raw", "specials", "ads")
    words = {}
    # acceptance 1.14.0 (N292): the rows lead with the ObjectRef; the residency is read under its header's column
    lines = out.splitlines()
    hi = next((i for i, ln in enumerate(lines) if "RESIDENCY" in ln and "STREAM" in ln), None)
    col = lines[hi].index("RESIDENCY") if hi is not None else None
    for ln in (lines[hi + 1:] if hi is not None else []):
        if not ln.strip() or ln.startswith("──"):
            break
        w = ln[col:].split()[:1]
        if w:
            words[w[0]] = words.get(w[0], 0) + 1
    assert words.get("extents") and set(words) <= {"inline", "extents", "unknown"}, words


def test_n293_the_text_views_do_not_split_the_joined_stream_names():
    src = open(os.path.join(W.REPO, "forefst.py"), encoding="utf-8").read()
    assert 'r.get("ads_names", "")).split(";")' not in src and '(r.get("ads_names") or "").split(";")' not in src


def test_n275_one_image_name_rule(monkeypatch):
    assert F._display_image("/a/b/vol.raw") == "vol.raw"
    monkeypatch.setattr(F, "_BUNDLE", {"dir": "/x/bundle"})
    assert F._display_image("/tmp/forefst_bundle_q/rehydrated.raw") == "/x/bundle (metadata bundle)"
    src = open(os.path.join(W.REPO, "forefst.py"), encoding="utf-8").read()
    assert not re.search(r"print\([^\n]*os\.path\.basename\((image|args\.image)\)", src), (
        re.findall(r".{30}print\([^\n]*os\.path\.basename\((?:image|args\.image)\).{20}", src))


# ── N291: one UTF-8 path for every machine writer ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def u8_vol(tmp_path_factory):
    """d/naïve_é.txt live and d/gône_ü.txt as a remnant in the page slack."""
    return W._dir_volume(str(tmp_path_factory.mktemp("n291") / "u8.raw"), [("naïve_é.txt", 2)], [("gône_ü.txt", 9)])


def _run_ascii_stdout(image, tmp_path, *args):
    import subprocess, sys
    env = dict(os.environ, PYTHONIOENCODING="ascii")       # a console that cannot encode the names
    r = subprocess.run([sys.executable, "-B", os.path.join(W.REPO, "forefst.py"), image] + list(args) + W._SYN,
                       capture_output=True, cwd=str(tmp_path), env=env, timeout=300)
    return r.returncode, r.stdout, r.stderr.decode("utf-8", "replace")


@pytest.mark.parametrize("args, name", [(("deleted", "--csv"), "gône_ü.txt"), (("deleted", "--json"), "gône_ü.txt"),
                                        (("specials", "--jsonl"), None), (("files", "--csv"), "naïve_é.txt"),
                                        (("timestomp", "--csv", "--all"), "naïve_é.txt")],
                         ids=["deleted-csv", "deleted-json", "specials-jsonl", "files-csv", "timestomp-csv"])
def test_n291_machine_output_on_stdout_is_utf8_whatever_the_console(u8_vol, tmp_path, args, name):
    rc, out, err = _run_ascii_stdout(u8_vol, tmp_path, *args)
    assert rc in (0, 2) and "Traceback" not in err and "UnicodeEncodeError" not in err, err[-1500:]
    text = out.decode("utf-8")                              # raises if it is not UTF-8
    assert name is None or name in text, text[:800]


def test_n291_every_file_a_tool_writes_as_text_is_utf8():
    for tool in ("forefst.py",):
        src = open(os.path.join(W.REPO, tool), encoding="utf-8").read()
        bad = [l.strip() for l in src.splitlines()
               if re.search(r'\bopen\(.*,\s*"[wax]"', l) and "encoding=" not in l and not l.strip().startswith("#")]
        assert not bad, "%s writes text without an encoding:\n  %s" % (tool, "\n  ".join(bad))


@pytest.mark.parametrize("tool, args", [("forefst.py", ("summary",)), ("forefst.py", ("search", "a")),
                                        ("forefst.py", ("deleted",)), ("refsanalysis.py", ("summary",))],
                         ids=["summary", "search", "deleted", "ra-summary"])
def test_n489_text_views_do_not_stop_on_a_console_that_cannot_encode(u8_vol, tmp_path, tool, args):
    import subprocess, sys
    env = dict(os.environ, PYTHONIOENCODING="ascii")
    r = subprocess.run([sys.executable, "-B", os.path.join(W.REPO, tool), u8_vol] + list(args) + W._SYN,
                       capture_output=True, cwd=str(tmp_path), env=env, timeout=300)
    err = r.stderr.decode("utf-8", "replace")
    assert r.returncode in (0, 2) and "UnicodeEncodeError" not in err and "codec can't encode" not in err, err[-800:]
    r.stdout.decode("utf-8")                                # the text is UTF-8


# ── N159 / N329 / N221 / N158: one reader each, the driver's names ─────────────────────────────────────────────────

import struct as _st                                     # noqa: E402


def test_n159_packed_ea_size_is_a_u16(monkeypatch):
    """$EA_INFORMATION's value: u16 PackedEaSize, u16 NeedEaCount, u32 unpacked size (RefsReplaceFileEas)."""
    kd = bytes(8) + F._SI_MARKER + bytes([0xD0, 0])
    vr = bytes(0x0C) + _st.pack("<HHI", 0x30, 1, 0x40)
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None, **k: [(kd, vr)])
    eas, packed = F.extract_eas_from_value(b"x")
    assert packed == 0x30, "PackedEaSize read as %#x (a FILE_NEED_EA count must not be added)" % packed


def test_n329_reparse_and_details_decode_wsl_metadata_alike(tmp_path):
    img = "step6/win11refs2gtargeted.raw"
    rc, out, err = W._image_run(tmp_path, W.FOREFST, img, "reparse", "--json")
    # acceptance 1.14.0 (K21; N322: ReparsePoints by FullPath, WSLEAs)
    pts = {p["FullPath"]: p for p in json.loads(out)["ReparsePoints"]}
    blk = pts.get("wsltests/testblk")
    eas = jget(blk, "wsl_eas") or {}
    assert blk and jget(eas, "mode") == 0o60660 and jget(eas, "dev") == [7, 0], blk
    rc, out, err = W._image_run(tmp_path, W.FOREFST, img, "details", "/wsltests/testblk", "--json")
    d = json.loads(out)
    d = d[0] if isinstance(d, list) else d
    wsl = jget(d, "wsl") or {}
    assert {k: jget(wsl, k) for k in ("uid", "gid", "mode", "dev")} == \
        {k: jget(eas, k) for k in ("uid", "gid", "mode", "dev")}, (wsl, eas)
    assert F.out_key("lxuid") not in eas and "lxuid" not in eas, "the reparse walk's own key set is gone"


def test_n221_checkpoint_flags_carry_the_drivers_names():
    got = F.chkp_flags_decoded(0x172)
    # acceptance 1.14.0 (K16): a flag value unpadded
    assert got == ["0x2 = always-set", "0x10 = dedup enabled", "0x20 = weak references enabled",
                   "0x40 = developer volume", "0x100 = dirty-state tracking enabled"], got


def test_n158_type_0xf0_is_the_change_journal_parameters():
    assert "$Max" in F._ATTR_NAMES[0xF0] and "LOGGED_UTILITY" not in F._ATTR_NAMES[0xF0]
    assert "LOGGED_UTILITY_STREAM" in F._ATTR_NAMES[0x100]
    # E167 (RC3a; RC3b item 13): a schema id names a TABLE by format era, not an attribute type + 0x100 -- 0x1F0 is the
    # table in a directory's own row (format 3.11+), 0x200 a data stream's table (3.11+); the attribute TYPES above stay
    assert F.MLOG_SCHEMA_NAMES[0x1F0] == "DirOwnRow(3.11+)" and F.MLOG_SCHEMA_NAMES[0x200] == "DataStream(3.11+)"
    assert F.MLOG_SCHEMA_NAMES[0x190] != "$SI", "type 0x90 is not $SI (the type map says so)"
