"""The code half, group 4 (summary / help / UX), 1.14.0: PLAN 10.2 G1, G2, A2, A3, A7, A9, A10, B2, C1, F, G5, H1 -- the
draft `analysis/reports/v1.13.2/RC1D/G4/DRAFT.md` as the maintainer approved it (2026-11-15; G2's `summary` line says
"seems") -- and RUNNING_LOG N115, N529, N530, N541.

Written RED before the fix (the run is recorded in `analysis/reports/v1.13.2/RC1D/G4/`). Volumes: win11refsmini (step1),
the public sample (its measured figures: 1,225 files, 1,507 names, 168 hard-linked files with 450 names, 50 files read
after their last change), win11refs2tmillionsofactions (statements on a damaged view).
"""
import csv
import datetime
import io
import json
import os
import re
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
MINI314 = "step1/win11refsmini.raw"
SAMPLE = "step5/win11refstestmftecmd.raw"
MILLIONS = "step3/win11refs2tmillionsofactions.raw"
CMDS = ("files", "summary", "fastsummary", "search", "details", "usn", "mlog", "timeline", "timestomp", "extract",
        "security", "specials", "ads", "reparse", "deleted", "recyclebin", "snapshots", "integrity", "export",
        "dataruns", "verify-bundle")
_RUNS = {}


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _run(argv, timeout=3600, cwd=None):
    key = (tuple(argv), cwd)
    if cwd is None and key in _RUNS:
        return _RUNS[key]
    r = subprocess.run([sys.executable, "-B"] + argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if cwd is None:
        _RUNS[key] = r
    return r


def _help(*words):
    r = _run([FOREFST] + list(words), timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


def _summary(rel):
    r = _run([FOREFST, _img(rel), "summary"])
    assert r.returncode in (0, 2), r.stderr[-1500:]
    return r.stdout


def _joined(out, label):
    """The text of a labelled field, its wrapped continuation lines joined with one space."""
    lines = out.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("  %s:" % label):
            parts = [ln.split(":", 1)[1].strip()]
            for nx in lines[i + 1:]:
                if nx.startswith(" " * 22) and nx.strip() and ":" not in nx[:22]:
                    parts.append(nx.strip())
                else:
                    break
            return " ".join(parts)
    return None


# ═══ G1: what the output is ═══════════════════════════════════════════════════════════════════════════════════════

_GROUPS = ["What the output is:",
           "  read from the volume       every subcommand not named below",
           "  inferred or recovered      mlog --parse, timeline, timestomp, deleted -- corroborate before relying on it"]


@pytest.mark.parametrize("words", [("list",), ("--help",)], ids=["list", "help"])
def test_g1_the_overview_and_the_list_state_the_output_groups(words):
    out = _help(*words)
    i = out.find(_GROUPS[0])
    assert i >= 0, out[-2000:]
    assert out[i:].splitlines()[:3] == _GROUPS


@pytest.mark.parametrize("cmd,want", [
    ("files", "Output: read from the volume."), ("summary", "Output: read from the volume."),
    ("usn", "Output: read from the volume."), ("integrity", "Output: read from the volume."),
    ("timeline", "Output: inferred or recovered -- corroborate before relying on it."),
    ("timestomp", "Output: inferred or recovered -- corroborate before relying on it."),
    ("deleted", "Output: inferred or recovered -- corroborate before relying on it."),
])
def test_g1_each_command_help_says_what_its_output_is(cmd, want):
    out = _help("help", cmd)
    assert "  " + want in out, out[:600]


def test_g1_mlog_help_says_parse_is_inferred():
    flat = " ".join(_help("help", "mlog").split())
    assert "Output: read from the volume; the actions of --parse are inferred -- corroborate before relying on them." \
        in flat


@pytest.mark.parametrize("cmd", ["extract", "export", "verify-bundle"])
def test_g1_extract_export_verify_bundle_have_no_output_group(cmd):
    assert "Output:" not in _help("help", cmd)


# ═══ N115, N529, N530 ═════════════════════════════════════════════════════════════════════════════════════════════

def test_n115_files_is_not_the_default_subcommand():
    assert "default subcommand" not in _help("help", "files")
    assert not re.search(r"^\s+files\s+.*\(default\)", _help("--help"), re.M)
    assert "defaults to `summary`" in _help("--help")


def test_n529_help_mlog_names_the_csv_columns_as_written():
    r = _run([FOREFST, _img(MINI314), "mlog", "--csv"])
    assert r.returncode in (0, 2), r.stderr[-800:]
    header = next(csv.reader(io.StringIO(r.stdout)))
    flat = " ".join(_help("help", "mlog").split())
    assert ",".join(header) in flat.replace(", ", ","), header
    assert "Seq,Timestamp,Action,FullPath" not in flat and "@PLCN+offset" not in flat
    assert "@PLCN.blk+offset" in flat


def test_n530_help_summary_has_no_joined_words():
    assert "andencrypted" not in _help("help", "summary")


# ═══ N541, G5: verify-bundle ══════════════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("g4b") / "fb")
    r = subprocess.run([sys.executable, "-B", FOREFST, _img(MINI314), "export", "metadata", "-o", d],
                       capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stderr[-800:]
    return d


def test_n541_the_three_help_forms_print_one_text(bundle):
    texts = []
    for argv in ([FOREFST, bundle, "verify-bundle", "--help"], [FOREFST, "help", "verify-bundle"],
                 [FOREFST, bundle, "help", "verify-bundle"]):
        r = subprocess.run([sys.executable, "-B"] + argv, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, (argv, r.stderr[-600:])
        texts.append(r.stdout)
    assert texts[0] == texts[1] == texts[2], [t[:200] for t in texts]
    assert "usage: forefst <bundle-dir> verify-bundle" in texts[0]
    assert "forefst ./bundle verify-bundle" in texts[0] and "disk.raw verify-bundle" not in texts[0]


def test_g5_the_bundle_comes_first(bundle):
    r = subprocess.run([sys.executable, "-B", FOREFST, "verify-bundle", bundle], capture_output=True, text=True,
                       timeout=300)
    assert r.returncode == 1, r.returncode
    assert "the bundle comes first: forefst <bundle-dir> verify-bundle" in r.stderr, r.stderr[-800:]
    assert "usage: forefst [-h]" not in r.stderr + r.stdout


def test_g5_an_image_given_to_verify_bundle_is_told_the_form():
    r = _run([FOREFST, _img(MINI314), "verify-bundle"], timeout=300)
    assert r.returncode == 2 and "is not a bundle (no manifest.json)" in r.stdout, (r.returncode, r.stdout[-600:])
    assert "forefst <bundle-dir> verify-bundle" in r.stdout


# ═══ A2, A7, A9, A10, G2: summary ═════════════════════════════════════════════════════════════════════════════════

def test_a2_the_image_tail_is_one_line():
    out = _summary(SAMPLE)
    m = re.search(r"^  Image tail:         (\d+) bytes \([^)]*\) after the volume, not read \((\S+ \S+) of it in "
                  r"partition #(\d+)\)$", out, re.M)
    assert m, [ln for ln in out.splitlines() if "tail" in ln.lower()] + out.splitlines()[:12]
    j = json.loads(_run([FOREFST, _img(SAMPLE), "summary", "--json"]).stdout)["ImageTail"]
    assert int(m.group(1)) == j["Bytes"] == j["InPartitionBytes"] + j["AfterPartitionBytes"]
    assert m.group(2) == F.size_aid_text(j["InPartitionBytes"])
    i = out.splitlines().index(m.group(0))
    assert not out.splitlines()[i + 1].startswith(" " * 22), "a continuation line under the image tail"


def test_a7_files_and_names_are_two_lines():
    out = _summary(SAMPLE)
    assert re.search(r"^  Files:              1225 \(214 inline, 1011 extents\)$", out, re.M), \
        [ln for ln in out.splitlines() if "Files:" in ln]
    assert "  Names:              1507 (1225 files, plus 282 more names: 168 hard-linked files have 450 names)" \
        in out.splitlines()


def test_a7_refsanalysis_summary_prints_the_names_line():
    r = _run([RA, _img(SAMPLE), "summary"])
    assert r.returncode in (0, 2), r.stderr[-800:]
    assert re.search(r"^  Names:\s+1507 \(", r.stdout, re.M), r.stdout[-2000:]


def test_a9_the_file_contents_sentence():
    out = _summary(SAMPLE)
    assert "  File contents:      not read -- every figure above comes from the volume's metadata." in out
    assert "File data:" not in out


def test_a10_summary_ends_with_a_closing_rule():
    lines = [ln for ln in _summary(SAMPLE).splitlines() if ln.strip()]
    assert lines[-1] == "=" * 78, lines[-3:]


def _read_after_change(rel):
    """The count by an independent reading: `files --csv`, one row per file (ObjectRef), Accessed > max(Modified,
    Changed) + 1 s."""
    r = _run([FOREFST, _img(rel), "files", "--csv"])
    seen, n = set(), 0
    for row in csv.DictReader(io.StringIO(r.stdout)):
        if row["IsDirectory"] == "true" or row["ObjectRef"] in seen:
            continue
        seen.add(row["ObjectRef"])
        t = [datetime.datetime.strptime(row[k][:26], "%Y-%m-%dT%H:%M:%S.%f") if row[k] else None
             for k in ("Accessed", "Modified", "Changed")]
        if all(t) and (t[0] - max(t[1], t[2])).total_seconds() > 1:
            n += 1
    return n


def test_g2_summary_counts_the_files_read_after_their_last_change():
    want = _read_after_change(SAMPLE)
    assert want == 50, "premise: the measured count"
    txt = _joined(_summary(SAMPLE), "Last access")
    assert txt == ("50 files read after their last change: last-access updating seems to have been on at some time "
                   "(a program can also set an Accessed time)"), txt
    j = json.loads(_run([FOREFST, _img(SAMPLE), "summary", "--json"]).stdout)
    assert j["FilesAccessedAfterChange"] == want


def test_g2_unit_the_zero_case_proves_nothing():
    assert F.accessed_after_change_text(0) == ("no file read after its last change -- this does not tell whether "
                                               "last-access updating was on")
    assert F._accessed_after_change({"access_time": 30000001, "modify_time": 20000000, "change_time": 20000000})
    assert not F._accessed_after_change({"access_time": 30000000, "modify_time": 20000000, "change_time": 20000000})
    assert not F._accessed_after_change({"access_time": 0, "modify_time": 20000000, "change_time": 20000000})


def test_g2_details_says_when_accessed_is_updated():
    r = _run([FOREFST, _img(MINI314), "details", "/test/ok.txt"])
    assert r.returncode in (0, 2), r.stderr[-800:]
    lines = r.stdout.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith("  Accessed:"))
    assert lines[i + 1].strip() == ("(updated only while last-access updating is on: a Windows setting, not on the "
                                    "volume)"), lines[i:i + 2]


def test_g2_help_files_and_the_timeline_caveat_say_it_too():
    assert "Accessed is updated only while last-access updating is on" in " ".join(_help("help", "files").split())
    r = _run([FOREFST, _img(MINI314), "timeline"])
    assert "An $SI Accessed event exists only while last-access updating was on." in r.stdout, r.stdout[-1500:]


# ═══ A3: prose wrapped at about 100 characters ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("words", [("list",), ("--help",)] + [("help", c) for c in CMDS],
                         ids=lambda w: " ".join(w))
def test_a3_no_help_line_is_longer_than_110(words):
    long = [ln for ln in _help(*words).splitlines() if len(ln) > 110]
    assert not long, long[:5]


@pytest.mark.parametrize("rel,cmd", [(SAMPLE, "summary"), (SAMPLE, "fastsummary"), (SAMPLE, "mlog"),
                                     (SAMPLE, "usn"), (SAMPLE, "integrity"), (SAMPLE, "integrity --checksums"),
                                     (MILLIONS, "summary"), (MILLIONS, "integrity"), (MILLIONS, "mlog")])
def test_a3_the_text_views_wrap_their_prose(rel, cmd):
    """Views of prose and fields: no stdout line over 110 but their data rows -- the boot-sector, superblock and
    checkpoint copy rows (`VBR` / `SUPB` / `CHKP primary|secondary|backup`, `Checkpoint [...]`), never wrapped."""
    r = _run([FOREFST, _img(rel)] + cmd.split())
    assert r.returncode in (0, 2), r.stderr[-800:]
    copy_row = re.compile(r"^  (VBR|SUPB|CHKP) (primary|secondary|backup)\s|^  Checkpoint \[")
    long = [ln for ln in r.stdout.splitlines() if len(ln) > 110 and not copy_row.match(ln)]
    assert not long, long[:4]


_DATA_ROW = {
    "deleted": re.compile(r"^\s{4,6}(bytes in row\*?|carve|metadata only|directory|empty)\s{2}"),
    "timestomp": re.compile(r"^  (HIGH|MEDIUM|LOW|INFO)\s|^\s+signals: "),
    "timeline": re.compile(r"^  (\d{4}-\d\d-\d\dT|\(none\))"),
}


@pytest.mark.parametrize("cmd", sorted(_DATA_ROW))
def test_a3_views_with_data_rows_wrap_only_their_prose(cmd):
    r = _run([FOREFST, _img(SAMPLE), cmd])
    assert r.returncode in (0, 2), r.stderr[-800:]
    long = [ln for ln in r.stdout.splitlines() if len(ln) > 110 and not _DATA_ROW[cmd].match(ln)]
    assert not long, long[:4]


def test_a3_control_data_rows_and_stderr_lines_are_never_wrapped():
    r = _run([FOREFST, _img(SAMPLE), "ads"])
    rows = [ln for ln in r.stdout.splitlines() if re.match(r"^  0x[0-9a-f]+:0x[0-9a-f]+\s", ln)]
    assert rows and max(len(x) for x in rows) > 150, "an ads row keeps its length (data rows are never wrapped)"
    u = _run([FOREFST, _img(SAMPLE), "usn"])
    notes = [ln for ln in u.stderr.splitlines() if ln.startswith("[forefst] note: USN journal:")]
    assert notes and len(notes[0]) > 150, "a stderr note stays one line"


def test_a3_unit_the_hanging_indent_is_under_the_label():
    ln = "  Coverage:                " + " ".join(["word%d" % i for i in range(40)])
    out = F._wrap_lines(ln)
    assert len(out) > 1 and all(len(x) <= 100 for x in out)
    assert all(x.startswith(" " * 27) and x[27] != " " for x in out[1:])
    assert " ".join(" ".join(out).split()) == " ".join(ln.split())
    assert F._wrap_lines("x" * 105) == ["x" * 105]                      # about 100: up to 110 is left as written
    assert F._wrap_lines("  " + "y" * 150) == ["  " + "y" * 150]        # a word is never broken


# ═══ B2, C1, F ════════════════════════════════════════════════════════════════════════════════════════════════════

def test_b2_ads_has_a_legend():
    out = _run([FOREFST, _img(SAMPLE), "ads"]).stdout.splitlines()
    i = next(k for k, ln in enumerate(out) if ln.lstrip().startswith("OBJECTREF ") and "HOST FILE" in ln)
    assert out[i - 1] == ("  OBJECTREF = the host file's reference (HomeOID:FileID); RESIDENCY = where the stream's "
                          "bytes are"), out[i - 2:i + 1]


def test_c1_rules_are_78_wide():
    out = _run([FOREFST, _img(MINI314), "specials"]).stdout.splitlines()
    rules = [x for x in out if x.strip() and set(x.strip()) <= {"=", "-"}]
    assert rules == ["=" * 78, "=" * 78, "  " + "-" * 76, "  " + "-" * 76], rules
    info = _run([FOREFST, _img(MINI314), "mlog", "--info"]).stdout.splitlines()
    assert "─" * 78 in info and "─" * 70 not in info


def test_f_details_of_a_directory_drops_the_empty_storage_and_decodes_embedded_files():
    r = _run([FOREFST, _img(MINI314), "details", "/test"])        # ok.txt embedded, t1-t3 subdirectories
    assert r.returncode in (0, 2), r.stderr[-800:]
    lines = r.stdout.splitlines()
    assert not [ln for ln in lines if re.match(r"^\s+Storage:\s*$", ln)], "an empty Storage: line"
    blocks, cur = [], []
    for ln in lines:
        if ln.startswith("    Filename:"):
            cur = [ln]
            blocks.append(cur)
        elif cur and ln.startswith("    ") and not ln.startswith("    Filename:"):
            cur.append(ln)
        elif cur:
            cur = []
    emb = [b for b in blocks if any(x.strip() == "Record:           embedded" for x in b)]
    assert emb, "premise: an embedded file in /test"
    for b in emb:
        assert any(x.startswith("    File size:") for x in b), b
        assert any(re.match(r"^    File attrs:\s+0x[0-9a-f]+ \(", x) for x in b), b


# ═══ H1: export file / ads ════════════════════════════════════════════════════════════════════════════════════════

def test_h1_export_file_writes_the_file_under_its_name_and_never_over_one(tmp_path):
    img = _img(MINI314)
    a = _run([FOREFST, img, "export", "file", "/test/ok.txt"], cwd=str(tmp_path))
    assert a.returncode in (0, 2), a.stderr[-800:]
    s = subprocess.run([sys.executable, "-B", FOREFST, img, "extract", "/test/ok.txt"], capture_output=True, timeout=600)
    assert open(str(tmp_path / "ok.txt"), "rb").read() == s.stdout and len(s.stdout) == 4
    b = _run([FOREFST, img, "export", "file", "/test/ok.txt"], cwd=str(tmp_path))
    assert b.returncode in (0, 2) and os.path.exists(str(tmp_path / "ok.txt.dup1")), (os.listdir(str(tmp_path)),
                                                                                       b.stderr[-600:])
    assert "ok.txt.dup1" in b.stderr and "exists" in b.stderr, b.stderr[-600:]


def test_h1_export_file_into_a_directory_and_to_the_screen(tmp_path):
    img = _img(MINI314)
    d = tmp_path / "case42"
    d.mkdir()
    a = _run([FOREFST, img, "export", "file", "/test/ok.txt", "-o", str(d) + "/"])
    assert a.returncode in (0, 2) and os.path.getsize(str(d / "ok.txt")) == 4, (a.stderr[-600:], os.listdir(str(d)))
    s = subprocess.run([sys.executable, "-B", FOREFST, img, "export", "file", "/test/ok.txt", "-o", "-"],
                       capture_output=True, timeout=600)
    assert len(s.stdout) == 4


def test_h1_a_name_the_host_cannot_keep_is_said(tmp_path):
    img = _img(SAMPLE)
    name = "FVE2.{8252fd17-a486-4ad4-b1ca-f4fe64d23218}"
    r = _run([FOREFST, img, "export", "file", "/System Volume Information/" + name], cwd=str(tmp_path))
    assert r.returncode in (0, 2), r.stderr[-800:]
    safe = F._safe_filename(name)
    assert os.path.exists(str(tmp_path / safe)), os.listdir(str(tmp_path))
    assert ("on the volume: %s" % name) in r.stderr, r.stderr[-600:]


def test_h1_export_ads_writes_file__stream(tmp_path):
    img = _img(SAMPLE)
    r = _run([FOREFST, img, "export", "ads", "/test/xbpt_tango_archive_828215.dat:hidden_1514"], cwd=str(tmp_path))
    assert r.returncode in (0, 2), r.stderr[-800:]
    assert os.path.exists(str(tmp_path / "xbpt_tango_archive_828215.dat__hidden_1514")), os.listdir(str(tmp_path))


def test_h1_help_export_says_extract_not_carve():
    h = _help("help", "export")
    assert "carve ONE" not in h and "./<its name>" in " ".join(h.split())


# ═══ A3's missed prose sites (2026-11-15; the shared golden's preview and the widened census `g4_longlines2`) ════════
# Each statement below printed one line of 119-216 characters. Wrapped, every line of it is within the tolerance and
# its continuation sits under its hanging indent; the entries and rows around it stay one line each.

MOVED = ("/test/elvis_dir_index_149423/elvis_dir_victor_121923/elvis_dir_hotel_670324/elvis_dir_output_358165/"
         "elvis_dir_oscar_874075/xbpt_delta_victor_412034.ini")      # the public sample: a moved name


def _starts(out, heads):
    """For each line that starts with one of `heads` (after its indent): (the line, the line after it)."""
    lines = out.split("\n")
    return [(ln, lines[k + 1] if k + 1 < len(lines) else "") for k, ln in enumerate(lines)
            if any(ln.lstrip().startswith(h) for h in heads)]


@pytest.fixture(scope="module")
def sample_deleted():
    img = _img(SAMPLE)
    return {k: _run([FOREFST, img, "deleted"] + a) for k, a in (("full", ["--full"]), ("v", ["-v"]),
                                                                ("pages", ["--scan-pages"]))}


def test_a3_deleted_full_closing_line_is_wrapped(sample_deleted):
    p = _starts(sample_deleted["full"].stdout, ["This was `--full`"])
    assert p and all(len(ln) <= F._WRAP_TOLERANCE for ln, _ in p) and p[0][1].startswith("  ") \
        and p[0][1].strip(), p


def test_a3_deleted_status_heads_mode_and_scan_lines_are_wrapped(sample_deleted):
    heads = [_starts(sample_deleted["v"].stdout, [h]) for h in ("DELETED --", "RENAMED --", "STILL PRESENT --")]
    assert all(heads) and all(len(ln) <= F._WRAP_TOLERANCE for h in heads for ln, _ in h), heads
    out = sample_deleted["pages"].stdout
    for h in ("Mode:", "Orphan-page scan: scanned"):
        p = _starts(out, [h])
        assert p and all(len(ln) <= F._WRAP_TOLERANCE for ln, _ in p), (h, p)


def test_a3_deleted_entries_stay_one_line(sample_deleted):
    """The listing's entries are data: a row over 110 is kept as printed (the census's control)."""
    rows = [ln for ln in sample_deleted["full"].stdout.split("\n") if re.match(r"^\s{4}\S.*\s{2}\d{4}-\d\d-\d\dT", ln)]
    assert rows and any(len(ln) > 110 for ln in rows), len(rows)


def test_a3_export_deleted_statements_are_wrapped(tmp_path):
    r = _run([FOREFST, _img(SAMPLE), "export", "deleted", str(tmp_path / "x"), "--carve"])
    assert r.returncode in (0, 2), r.stderr[-800:]
    for h in ("Content recovered:", "Carves read from extent maps:", "Runs zero-filled because"):
        p = _starts(r.stdout, [h])
        assert p and all(len(ln) <= F._WRAP_TOLERANCE for ln, _ in p), (h, p)
    # the export directory is one word: with a long one the first line ends at the arrow
    p = [x for x in _starts(r.stdout, [""]) if re.search(r"\bentr(?:y|ies) indexed →", x[0])]
    assert p and all(len(ln) <= F._WRAP_TOLERANCE for ln, _ in p), p


def test_a3_details_moved_name_values_are_wrapped():
    r = _run([FOREFST, _img(SAMPLE), "details", MOVED])
    assert r.returncode in (0, 2), r.stderr[-800:]
    for h in ("Is moved:", "Home directory:"):
        p = _starts(r.stdout, [h])
        assert p and all(len(ln) <= F._WRAP_TOLERANCE for ln, _ in p), (h, p)
        if len(" ".join(p[0][0].split())) > 80:
            assert p[0][1].startswith(" " * 22) and p[0][1].strip(), p     # the continuation under the value


# ═══ A3's last missed sites (2026-11-16; the shared golden's long lines kept): bullets and sub-lines of findings ═════

def _wrapped_lines_of(out, head, hang):
    """The line starting with `head` (after its indent) and its continuation lines (indented `hang`)."""
    lines = out.split("\n")
    k = next((n for n, ln in enumerate(lines) if ln.lstrip().startswith(head)), None)
    assert k is not None, (head, out[-2500:])
    got = [lines[k]]
    for ln in lines[k + 1:]:
        if len(ln) - len(ln.lstrip(" ")) != hang or not ln.strip():
            break
        got.append(ln)
    return got


@pytest.mark.parametrize("rel,cmd,head,hang", [
    ("step4/wininsiderrefs8gtest2.raw", "summary", "· 0x2000 = attestation HMAC", 26),
    ("step4continuing/win11refsmini_afterchangingversion.raw", "summary", "• $VOLUME_INFORMATION says", 8),
    ("step3/win10to11refs4g.raw", "integrity", "↳ version mismatch:", 8),
], ids=["checkpoint-flag-bullet", "version-evidence-bullet", "backup-vbr-sub-line"])
def test_a3_finding_bullets_and_sub_lines_are_wrapped(rel, cmd, head, hang):
    r = _run([FOREFST, _img(rel), cmd])
    assert r.returncode in (0, 2), r.stderr[-800:]
    got = _wrapped_lines_of(r.stdout, head, hang)
    assert len(got) >= 2 and all(len(ln) <= F._WRAP_TOLERANCE for ln in got), got
