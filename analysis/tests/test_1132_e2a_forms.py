"""Wave E step E2a (1.14.0, `analysis/reports/v1.13.2/fixes/E2a_NOTES.md`): one form per kind of value (decisions 35
and 38, `fixes/CONSISTENCY_CHOICES.md`), S9's shape: one property test per kind over EVERY output form of both tools.

How it works
------------
`_FORMS` is every output form of both tools (the E2a census list: each command, each format, the files an export
writes). Each test runs the whole list once per volume (module cache) and scans every output for the form the
decisions retire; the failure names the form and the line. Each kind has a control: the scanner finds the retired form
in a planted line (it can emit its counterexample), and the decided form occurs in the outputs (the test is not empty).

Volumes: win11refstestmftecmd (the public sample: an active change journal, streams, hard links, reparse points,
deleted remnants), win11refs2tsnapshots (snapshots), win10refsmini (ReFS 3.4).

Kinds (the rule sheet, E2a_NOTES section 0): K5 date-times (+ B10's unit tests); K6 sizes; K7 cluster size; K1, K9,
K10, K14 hex in machine outputs; K15 hex case; K19 booleans; K20 absent values; K28 separators; K29 version label; K24
checksum names; K13 LSNs; K11 USNs; K4 GUIDs; K2 a directory's reference; K22 paths; K25 lists (+ E-4); N167 the
bodyfile.
"""
import csv
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
REFSANALYSIS = os.path.join(REPO, "refsanalysis.py")
TIMEOUT = 1800

_F, _R = "f", "r"
# (tool, form id, args); {FILE} a file path of the volume, {DIR} a directory path, {OUT} an export directory
_FORMS = [
    (_F, "files", ["files"]), (_F, "files-csv", ["files", "--csv"]), (_F, "files-json", ["files", "--json"]),
    (_F, "files-jsonl", ["files", "--jsonl"]), (_F, "files-body", ["files", "--body"]),
    (_F, "summary", ["summary"]), (_F, "summary-json", ["summary", "--json"]),
    (_F, "fastsummary", ["fastsummary"]), (_F, "fastsummary-json", ["fastsummary", "--json"]),
    (_F, "search", ["search", "a"]), (_F, "search-csv", ["search", "a", "--csv"]),
    (_F, "search-json", ["search", "a", "--json"]), (_F, "search-jsonl", ["search", "a", "--jsonl"]),
    (_F, "details-file", ["details", "{FILE}"]), (_F, "details-file-json", ["details", "{FILE}", "--json"]),
    (_F, "details-file-csv", ["details", "{FILE}", "--csv"]), (_F, "details-file-jsonl", ["details", "{FILE}", "--jsonl"]),
    (_F, "details-dir", ["details", "{DIR}"]), (_F, "details-dir-json", ["details", "{DIR}", "--json"]),
    (_F, "details-oid", ["details", "0x701"]), (_F, "details-oid-json", ["details", "0x701", "--json"]),
    (_F, "usn", ["usn"]), (_F, "usn-v", ["usn", "-v"]), (_F, "usn-csv", ["usn", "--csv"]),
    (_F, "usn-json", ["usn", "--json"]), (_F, "usn-info", ["usn", "--info"]), (_F, "usn-stats", ["usn", "--stats"]),
    (_F, "mlog", ["mlog"]), (_F, "mlog-v", ["mlog", "-v"]), (_F, "mlog-parse", ["mlog", "--parse"]),
    (_F, "mlog-parse-v", ["mlog", "--parse", "-v"]), (_F, "mlog-csv", ["mlog", "--csv"]),
    (_F, "mlog-json", ["mlog", "--json"]), (_F, "mlog-stats", ["mlog", "--stats"]), (_F, "mlog-info", ["mlog", "--info"]),
    (_F, "mlog-raw", ["mlog", "--raw-scan"]),
    (_F, "security", ["security"]), (_F, "security-v", ["security", "-v"]), (_F, "security-files", ["security", "--files"]),
    (_F, "security-json", ["security", "--json"]), (_F, "security-audit", ["security", "--audit"]),
    (_F, "security-audit-json", ["security", "--audit", "--json"]),
    (_F, "specials", ["specials"]), (_F, "specials-json", ["specials", "--json"]), (_F, "specials-csv", ["specials", "--csv"]),
    (_F, "specials-jsonl", ["specials", "--jsonl"]), (_F, "specials-ads", ["specials", "ads"]),
    (_F, "specials-reparse", ["specials", "reparse"]), (_F, "specials-hardlink", ["specials", "hardlink"]),
    (_F, "specials-hardlink-json", ["specials", "hardlink", "--json"]), (_F, "specials-sparse", ["specials", "sparse"]),
    (_F, "specials-snapshot", ["specials", "snapshot"]),
    (_F, "ads", ["ads"]), (_F, "ads-csv", ["ads", "--csv"]), (_F, "ads-json", ["ads", "--json"]),
    (_F, "ads-jsonl", ["ads", "--jsonl"]),
    (_F, "reparse", ["reparse"]), (_F, "reparse-v", ["reparse", "-v"]), (_F, "reparse-index", ["reparse", "--index"]),
    (_F, "reparse-index-v", ["reparse", "--index", "-v"]), (_F, "reparse-json", ["reparse", "--json"]),
    (_F, "reparse-index-json", ["reparse", "--index", "--json"]),
    (_F, "deleted", ["deleted"]), (_F, "deleted-csv", ["deleted", "--csv"]), (_F, "deleted-json", ["deleted", "--json"]),
    (_F, "deleted-jsonl", ["deleted", "--jsonl"]),
    (_F, "recyclebin", ["recyclebin"]), (_F, "recyclebin-json", ["recyclebin", "--json"]),
    (_F, "recyclebin-csv", ["recyclebin", "--csv"]),
    (_F, "snapshots", ["snapshots"]), (_F, "snapshots-v", ["snapshots", "-v"]), (_F, "snapshots-json", ["snapshots", "--json"]),
    (_F, "integrity", ["integrity"]), (_F, "integrity-v", ["integrity", "-v"]), (_F, "integrity-json", ["integrity", "--json"]),
    (_F, "dataruns", ["dataruns"]), (_F, "dataruns-v", ["dataruns", "-v"]), (_F, "dataruns-csv", ["dataruns", "--csv"]),
    (_F, "dataruns-json", ["dataruns", "--json"]),
    (_F, "timeline", ["timeline", "--limit", "400"]), (_F, "timeline-csv", ["timeline", "--csv", "--limit", "400"]),
    (_F, "timeline-json", ["timeline", "--json", "--limit", "400"]),
    (_F, "timeline-jsonl", ["timeline", "--jsonl", "--limit", "400"]),
    (_F, "timestomp", ["timestomp"]), (_F, "timestomp-all", ["timestomp", "--all"]),
    (_F, "timestomp-csv", ["timestomp", "--csv"]), (_F, "timestomp-json", ["timestomp", "--json"]),
    (_F, "export-reparse", ["export", "reparse"]),
    (_F, "export-deleted", ["export", "deleted", "{OUT}", "--carve"]),
    (_F, "export-metadata", ["export", "metadata", "{OUT}"]),
    (_F, "export-snapshots", ["export", "snapshots", "{OUT}"]),
    (_F, "export-resident-all", ["export", "resident-all", "{OUT}"]),
    (_R, "ra", []), (_R, "ra-summary-json", ["summary", "--json"]), (_R, "ra-summarypp", ["summary++"]),
    (_R, "ra-summarypp-json", ["summary++", "--json"]),
    (_R, "ra-boot", ["boot"]), (_R, "ra-boot-v", ["boot", "-v"]), (_R, "ra-boot-vv", ["boot", "-vv"]),
    (_R, "ra-boot-verify", ["boot", "--verify"]),
    (_R, "ra-supb", ["supb"]), (_R, "ra-supb-v", ["supb", "-v"]), (_R, "ra-supb-vv", ["supb", "-vv"]),
    (_R, "ra-supb-verify", ["supb", "--verify"]),
    (_R, "ra-chkp", ["chkp"]), (_R, "ra-chkp-v", ["chkp", "-v"]), (_R, "ra-chkp-vv", ["chkp", "-vv"]),
    (_R, "ra-chkp-verify", ["chkp", "--verify"]),
    (_R, "ra-schema", ["schema"]), (_R, "ra-upcase", ["upcase"]), (_R, "ra-objects", ["objects"]),
    (_R, "ra-parentchild", ["parentchild"]), (_R, "ra-parentchild-vv", ["parentchild", "-vv"]),   # review S4 / M3
    (_R, "ra-containers", ["containers"]), (_R, "ra-allocators", ["allocators"]),
    (_R, "ra-allocators-json", ["allocators", "--json"]), (_R, "ra-files", ["files"]), (_R, "ra-files-v", ["files", "-v"]),
    (_R, "ra-attributes", ["attributes"]), (_R, "ra-details", ["details", "{FILE}"]),
    (_R, "ra-details-json", ["details", "{FILE}", "--json"]), (_R, "ra-details-dir", ["details", "{DIR}"]),
    (_R, "ra-oid30", ["oid30"]), (_R, "ra-bootedit-read", ["bootedit", "read"]),
    (_R, "ra-bootedit-repair", ["bootedit", "repair", "--dry-run"]),
]

_IMAGES = ["win11refstestmftecmd.raw", "win11refs2tsnapshots.raw", "step1/win10refsmini.raw"]
_RUNS = {}


def _run(tool, img, args, cwd):
    exe = FOREFST if tool == _F else REFSANALYSIS
    try:
        p = subprocess.run([sys.executable, "-B", exe, img] + args, cwd=cwd, capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "", ""
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def _pick_paths(img, cwd):
    """A file with a named stream and data (else any file with data), and a top-level directory, from `files --csv`
    (the column names of either side of the key rename)."""
    rc, out, err = _run(_F, img, ["files", "-q", "--csv"], cwd)
    rows = list(csv.DictReader(io.StringIO(out)))
    def g(r, *ks):
        for k in ks:
            if k in r:
                return r[k]
        return ""
    def isdir(r):
        return g(r, "IsDirectory").lower() == "true"
    fpath = dpath = None
    for r in rows:
        p = g(r, "FullPath")
        if isdir(r) and dpath is None and "/" not in p and not p.startswith("$"):
            dpath = "/" + p
        if not isdir(r) and fpath is None and g(r, "HasADS").lower() == "true" and int(g(r, "FileSize") or 0) > 0:
            fpath = "/" + p
    if fpath is None:
        fpath = next(("/" + g(r, "FullPath") for r in rows if not isdir(r) and int(g(r, "FileSize") or 0) > 0), None)
    return fpath, dpath


def _outputs(name, tmp_factory):
    """{form id: (rc, stdout, stderr)} plus, for an export, {form id + '/' + relpath: (None, text, '')} for every
    .json / .csv / .txt / .log file it wrote (content files are not read). One run per volume per session."""
    if name in _RUNS:
        return _RUNS[name]
    img = _corpus_image(name)
    if img is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    cwd = str(tmp_factory.mktemp("e2a_" + os.path.basename(name).split(".")[0]))
    fpath, dpath = _pick_paths(img, cwd)
    res = {}
    for tool, fid, args in _FORMS:
        if (any("{FILE}" in a for a in args) and not fpath) or (any("{DIR}" in a for a in args) and not dpath):
            continue
        exp = os.path.join(cwd, fid + ".dir")
        a = [x.replace("{FILE}", fpath or "").replace("{DIR}", dpath or "").replace("{OUT}", exp) for x in args]
        res[fid] = _run(tool, img, a, cwd)
        if os.path.isdir(exp):
            for root, _dirs, files in os.walk(exp):
                for fn in files:
                    p = os.path.join(root, fn)
                    if re.search(r"\.(json|csv|txt|log)$", fn) and "content" not in os.path.relpath(p, exp).split(os.sep)[0]:
                        with open(p, encoding="utf-8", errors="replace") as fh:
                            res[fid + "/" + os.path.relpath(p, exp)] = (None, fh.read(), "")
            shutil.rmtree(exp, ignore_errors=True)
    _RUNS[name] = res
    return res


@pytest.fixture(scope="module", params=_IMAGES, ids=lambda n: os.path.basename(n).split(".")[0])
def outs(request, tmp_path_factory):
    return _outputs(request.param, tmp_path_factory)


def _is_json_form(fid):
    return fid.endswith(".json") or bool(re.search(r"json(l)?$", fid))


def _is_csv_form(fid):
    return fid.endswith(".csv") or fid.endswith("-csv")


def _texts(outs, streams=("out", "err")):
    """(where, text) for every stream of every form: stdout, stderr and the files an export wrote."""
    for fid, (rc, out, err) in outs.items():
        if "out" in streams:
            yield (fid if rc is None else fid + ":stdout"), fid, out
        if "err" in streams and rc is not None:
            yield fid + ":stderr", fid, err


def _hits(outs, rx, streams=("out", "err"), where=None, limit=12):
    bad = []
    for w, fid, t in _texts(outs, streams):
        if where and not where(fid, w):
            continue
        for m in rx.finditer(t):
            s = t.rfind("\n", 0, m.start()) + 1
            e = t.find("\n", m.end())
            bad.append("%s: %s" % (w, t[s:e if e >= 0 else None].strip()[:200]))
            if len(bad) >= limit:
                return bad
    return bad


def _json_docs(text):
    t = text.strip()
    if not t:
        return []
    try:
        return [json.loads(t)]
    except ValueError:
        docs = []
        for ln in t.splitlines():
            ln = ln.strip()
            if ln[:1] in "{[":
                try:
                    docs.append(json.loads(ln))
                except ValueError:
                    pass
        return docs


def _jwalk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "/" + str(k), str(k), v
            yield from _jwalk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for v in o:
            yield from _jwalk(v, path + "[]")


def _json_items(outs):
    for fid, (rc, out, err) in outs.items():
        if _is_json_form(fid):
            for doc in _json_docs(out):
                for path, k, v in _jwalk(doc):
                    yield fid, path, k, v


def _csv_tables(outs):
    for fid, (rc, out, err) in outs.items():
        if _is_csv_form(fid) and out.strip():
            rows = list(csv.reader(io.StringIO(out)))
            if rows:
                yield fid, rows


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# K5 date-times + B10 (one FILETIME converter)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

_OLD_TIME = re.compile(r"\b\d{4}-\d\d-\d\d \d\d:\d\d:\d\d"                      # a space between date and time
                       r"|\b\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?!\.\d{7}Z)"          # ISO without the 7 digits and Z
                       r"|\d\d:\d\d:\d\d(\.\d+)? UTC\b")                         # the ' UTC' suffix
_NEW_TIME = re.compile(r"\b\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}Z")


def test_k5_control_the_scanner_finds_each_retired_time_form():
    for planted in ("2026-05-16 16:55:20.9805996", "2026-05-16 16:55:20 UTC", "2026-05-16T16:55:20.980Z",
                    "2026-05-16T16:55:20Z"):
        assert _OLD_TIME.search(planted), planted
    assert not _OLD_TIME.search("2026-05-16T16:55:20.9805996Z")


def test_k5_every_date_time_is_iso_with_seven_digits_and_z(outs):
    bad = _hits(outs, _OLD_TIME)
    assert not bad, "a date-time not written 2026-05-16T16:55:20.9805996Z:\n  " + "\n  ".join(bad)


def test_k5_control_the_decided_form_occurs(outs):
    assert _hits(outs, _NEW_TIME, limit=1), "no output carries a date-time at all (the scan above would be empty)"


_EPOCH = datetime.datetime(1601, 1, 1)


def _ft(*a):
    d = datetime.datetime(*a) - _EPOCH
    return (d.days * 86400 + d.seconds) * 10 ** 7 + d.microseconds * 10


@pytest.mark.parametrize("ft, want", [
    (0, None), (0xFFFFFFFFFFFFFFFF, None),
    (1, "1601-01-01T00:00:00.0000001Z"),
    (_ft(1969, 12, 31, 23, 59, 59) + 9999999, "1969-12-31T23:59:59.9999999Z"),
    (_ft(2026, 5, 16, 16, 55, 20) + 9805996, "2026-05-16T16:55:20.9805996Z"),
    (_ft(9999, 12, 31, 23, 59, 59) + 9999999, "9999-12-31T23:59:59.9999999Z"),
    (_ft(9999, 12, 31, 23, 59, 59) + 10 ** 7, "0x%016x" % (_ft(9999, 12, 31, 23, 59, 59) + 10 ** 7)),
    (0xFFFFFFFFFFFFFFFE, "0xfffffffffffffffe"),
], ids=["zero", "all-ones", "one", "pre-1970", "sample", "year-9999", "year-10000", "all-ones-minus-1"])
def test_b10_the_one_filetime_converter_at_its_edges(ft, want):
    assert F.ft_iso(ft) == want


def test_b10_every_converter_in_both_tools_is_the_one_converter():
    """B10: the old converters are gone or return the one converter's string (absent: '', '(none)' or None by form)."""
    import refsanalysis as RA
    edge = [0, 1, _ft(1969, 12, 31, 23, 59, 59), _ft(2026, 5, 16, 16, 55, 20) + 9805996, 0xFFFFFFFFFFFFFFFE,
            0xFFFFFFFFFFFFFFFF]
    names = [n for n in ("filetime_to_iso", "_filetime_to_str", "_usn_filetime_iso", "_usn_filetime_short")
             if hasattr(F, n)] + ["RA." + n for n in ("_filetime_to_str",) if hasattr(RA, n)]
    bad = []
    for n in names:
        fn = getattr(RA, n[3:]) if n.startswith("RA.") else getattr(F, n)
        for v in edge:
            want = F.ft_iso(v)
            got = fn(v)
            if (want is None and got not in ("", "(none)", None)) or (want is not None and got != want):
                bad.append("%s(0x%x) = %r, want %r" % (n, v, got, want))
    assert not bad, "\n".join(bad)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# K6 sizes, K7 / K8 cluster and container size
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

_OLD_UNIT = re.compile(r"\b\d+(\.\d+)? ?(KB|MB|GB|TB|PB)\b")


def test_k6_control_the_scanner_finds_the_retired_units():
    assert _OLD_UNIT.search("4.0 KB") and _OLD_UNIT.search("64.0 MB") and _OLD_UNIT.search("3 GB")
    assert not _OLD_UNIT.search("4 KiB") and not _OLD_UNIT.search("5176 bytes (5.1 KiB)")


@pytest.mark.parametrize("n, want", [(4096, "4 KiB"), (65536, "64 KiB"), (64 << 20, "64 MiB"), (512, "512 bytes"),
                                     (5176, "5.1 KiB"), (4227858432, "3.9 GiB"), (2 << 40, "2 TiB")])
def test_k6_the_reading_aid_is_whole_when_exact(n, want):
    assert F._human_size(n) == want


def test_k6_sizes_use_iec_units(outs):
    bad = _hits(outs, _OLD_UNIT)
    assert not bad, "a size in KB/MB, or 'N.0 KiB' for an exact size:\n  " + "\n  ".join(bad)


_HUMAN = re.compile(r"^\d+(\.\d+)? ?(B|KiB|MiB|GiB|TiB|KB|MB|GB|TB|bytes)$")


def test_k6_json_carries_integer_bytes_not_human_strings(outs):
    bad = ["%s %s=%r" % (fid, p, v) for fid, p, k, v in _json_items(outs) if isinstance(v, str) and _HUMAN.match(v)]
    assert not bad, "a human size string in JSON (the integer bytes belong there):\n  " + "\n  ".join(bad[:12])


_CLUSTER_HEX = re.compile(r"(?i)cluster[ _-]?size\W{0,4}0x|\bcluster=0x|cluster[^\n]{0,24}\b0x10{3,4} \(")


def test_k7_cluster_size_is_never_hex(outs):
    bad = _hits(outs, _CLUSTER_HEX)
    assert not bad, "a cluster size in hex (text `4 KiB`, machine and key=value `4096`):\n  " + "\n  ".join(bad)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# K1, K9, K10, K14 (machine): identifiers, LCNs, offsets, flags and tags are lower-case 0x strings
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

_HEX_KEY = re.compile(r"(?i)(^|_|[a-z])(oid|lcn|plcn|vlcn|vcn|offset|off|fileid|file_id|ref|securityid|security_id|"
                      r"attrs|attributes|flags|tag|serial|signature|journalid|journal_id|lsn|mask|control|magic|"
                      r"checksum|cksum|hash|crc|stored|computed|marker)"   # N539 / N553 (d) (1.14.0): a checksum,
                                                                                 # a hash, a marker word
                      r"(s)?($|_|[A-Z])")    # N533 (1.14.0): no key names a handle (+0x20 is AllocatorClock, decimal)
_NOT_HEX_KEY = re.compile(r"(?i)count|size|len|bytes|clusters|total|num|pct|names|text|word|words|rows|blocks|pages|"
                          r"entries|records|files|version|delta|_ok$|ok$|valid|present|has_|^has|is_|^is|"
                          r"slot$")      # a slot number (a key ENDING in Slot) is an index: summary MLog ControlCopySlot


def test_k1_k9_k10_k14_control_the_key_rule():
    for k in ("oid", "HomeOID", "lcn", "checkpoint_used_lcn", "disk_offset", "file_attrs", "security_id",
              "SecurityId", "dir_oid", "reparse_tag", "control", "journal_id", "PageOffset",
              "PrimaryChecksumStored", "ChecksumComputed", "sd_hash", "Marker"):
        assert _HEX_KEY.search(k) and not _NOT_HEX_KEY.search(k), k
    for k in ("file_size", "extent_count", "covered_clusters", "has_reparse", "pages_valid_sig", "data_len"):
        assert not (_HEX_KEY.search(k) and not _NOT_HEX_KEY.search(k)), k


# The bundle's manifest.json changes with its reader and `verify-bundle` in step E2b (E-2: the BundleFormat key, the
# PascalCase keys, a bundle of 1.12.1-1.13.1 refused clearly), so this E2a kind leaves it out; E2b's tests cover it.
_E2B_BUNDLE = "export-metadata/manifest.json"


def test_k1_k9_k10_k14_json_identifiers_lcns_offsets_flags_are_hex_strings(outs):
    bad = []
    for fid, p, k, v in _json_items(outs):
        if fid == _E2B_BUNDLE:
            continue
        if not (_HEX_KEY.search(k) and not _NOT_HEX_KEY.search(k)):
            continue
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, bool) or isinstance(x, (dict, list)) or x is None:
                continue
            if isinstance(x, int):
                bad.append("%s %s=%r" % (fid, p, x))
    assert not bad, "an identifier, LCN, offset or flag word as a JSON integer (`\"0x...\"`):\n  " + "\n  ".join(
        sorted(set(bad))[:15])


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# K15 hex case, K28 separators, K29 version label, K24 checksum names, K13 LSNs, K11 USNs, K4 GUIDs
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

_UPPER_HEX = re.compile(r"\b0x[0-9a-fA-F]*[A-F][0-9a-fA-F]*\b")


def test_k15_hex_digits_are_lower_case(outs):
    bad = _hits(outs, _UPPER_HEX)
    assert not bad, "upper-case hex digits after 0x:\n  " + "\n  ".join(bad)


_SEPARATED = re.compile(r"(?<![\w.:,/\\-])\d{1,3}(,\d{3})+(?![\d\w])")


def test_k28_control():
    assert _SEPARATED.search("journal 9,371 records") and _SEPARATED.search("134,217,728 bytes")
    assert not _SEPARATED.search("v3,831cab") and not _SEPARATED.search("0x1,0x2")


def test_k28_counts_have_no_thousands_separators(outs):
    bad = _hits(outs, _SEPARATED, where=lambda fid, w: not _is_csv_form(fid) and not _is_json_form(fid))
    assert not bad, "a count with thousands separators:\n  " + "\n  ".join(bad)


_VLABEL = re.compile(r"(?<![\w.])v3\.\d+\b|\bReFS v\d|\(v\d\.\d+\+?\)")


def test_k29_the_version_label_is_refs_x_y(outs):
    bad = _hits(outs, _VLABEL)
    assert not bad, "a version written vX.Y (the label is `ReFS 3.14`):\n  " + "\n  ".join(bad)


_SHA_NAME = re.compile(r"\bSHA256\b(?!\s*[:=,\"])|\bsha256\b(?!sum)|(?i:checksum)[^\n]{0,24}\bNone\b")


def test_k24_checksum_algorithms_have_one_name_each(outs):
    bad = _hits(outs, _SHA_NAME, where=lambda fid, w: not _is_csv_form(fid) and not _is_json_form(fid))
    assert not bad, "an algorithm named other than SHA-256 / CRC64 / CRC32-C / none:\n  " + "\n  ".join(bad)


def test_k13_lsns_are_the_full_u64(outs):
    bad = _hits(outs, re.compile(r"\b0x[0-9a-f]+\.\d+\b(?!\.)"))
    assert not bad, "an LSN as low.high:\n  " + "\n  ".join(bad)


def test_k11_usns_are_decimal(outs):
    bad = _hits(outs, re.compile(r"\bUSN:? +0x"))
    assert not bad, "a USN in hex:\n  " + "\n  ".join(bad)


_GUIDISH = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_RAW_GUID = re.compile(r"(?i)guid[^\n]{0,40}?\b[0-9a-f]{32}\b")


def test_k4_guids_are_canonical(outs):
    bad = _hits(outs, _RAW_GUID)
    for w, fid, t in _texts(outs):
        for m in _GUIDISH.finditer(t):
            if re.search(r"[A-F]", m.group(0)):
                bad.append("%s: %s" % (w, m.group(0)))
                break
    assert not bad, "a GUID as raw bytes or in upper case:\n  " + "\n  ".join(bad[:12])


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# K19 booleans, K20 absent values
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_k19_csv_booleans_are_true_false(outs):
    bad = []
    for fid, rows in _csv_tables(outs):
        for r in rows[1:]:
            if "True" in r or "False" in r:
                bad.append("%s: %s" % (fid, ",".join(r)[:160]))
                break
    assert not bad, "a CSV boolean written True/False:\n  " + "\n  ".join(bad)


def test_k19_control_csv_booleans_occur(outs):
    assert any(("true" in r or "false" in r) for fid, rows in _csv_tables(outs) for r in rows[1:]) or \
        any("True" in r for fid, rows in _csv_tables(outs) for r in rows[1:]), "no CSV boolean at all"


_ABSENT_TOKENS = ("", "(none)", "n/a", "?", "-", "\u2014", "(undated)", "(unknown)", "None")


def test_k20_json_absent_values_are_null(outs):
    bad = sorted({"%s %s=%r" % (fid, re.sub(r"\[\]", "", p), v) for fid, p, k, v in _json_items(outs)
                  if isinstance(v, str) and v in _ABSENT_TOKENS})
    assert not bad, "an absent value written as a token in JSON (null belongs there):\n  " + "\n  ".join(bad[:20])


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# K3 SecurityId, K2 a directory's reference, K22 paths, K25 lists
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_k3_csv_security_ids_are_hex(outs):
    bad = []
    for fid, rows in _csv_tables(outs):
        hdr = rows[0]
        for i, h in enumerate(hdr):
            if re.fullmatch(r"(?i)security_?id", h):
                for r in rows[1:]:
                    if i < len(r) and r[i] and not re.fullmatch(r"0x[0-9a-f]+", r[i]):
                        bad.append("%s %s=%r" % (fid, h, r[i]))
                        break
    assert not bad, "a SecurityId not in hex in a CSV:\n  " + "\n  ".join(bad)


def test_k3_text_security_ids_are_hex_with_the_decimal(outs):
    # 1.14.0 group 5 (N543 a): a decimal alone, or the hex without its decimal, is refused
    bad = _hits(outs, re.compile(r"(?i)\bsecurity ?id\b[ :=]+(?:(?!0x)\d|0x[0-9a-f]+(?![0-9a-f])(?! \(\d+\)))"), streams=("out",),
                where=lambda fid, w: not _is_csv_form(fid) and not _is_json_form(fid))
    assert not bad, "a SecurityId not as `0x103 (259)` in text:\n  " + "\n  ".join(bad)


def _dir_records(outs):
    """(form, record) for every JSON record that says it is a directory (either side of the key rename)."""
    for fid, (rc, out, err) in outs.items():
        if not _is_json_form(fid):
            continue
        for doc in _json_docs(out):
            for v in _all_dicts(doc):
                if any(v.get(x) is True for x in ("is_directory", "IsDirectory", "is_dir")):
                    yield fid, v


def _all_dicts(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _all_dicts(v)
    elif isinstance(o, list):
        for v in o:
            yield from _all_dicts(v)


def test_k2_a_directorys_reference_is_oid_colon_0x0(outs):
    bad = []
    for fid, rec in _dir_records(outs):
        for key in ("id", "ObjectRef", "object_ref", "file_ref"):
            v = rec.get(key)
            if isinstance(v, str) and v and not re.fullmatch(r"0x[0-9a-f]+:0x0", v):
                bad.append("%s %s=%r" % (fid, key, v))
    assert not bad, "a directory's reference not written `0x701:0x0`:\n  " + "\n  ".join(sorted(set(bad))[:12])


_PATH_KEY = re.compile(r"(?i)^(path|full_?path|parent_?path|creation_?dir|recovered_?from|owning_?path|live_?file)$")


def test_k22_machine_paths_have_no_leading_slash(outs):
    bad = sorted({"%s %s=%r" % (fid, k, v) for fid, p, k, v in _json_items(outs)
                  if _PATH_KEY.match(k) and isinstance(v, str) and v.startswith("/")})
    for fid, rows in _csv_tables(outs):
        for i, h in enumerate(rows[0]):
            if _PATH_KEY.match(h):
                for r in rows[1:]:
                    if i < len(r) and r[i].startswith("/"):
                        bad.append("%s %s=%r" % (fid, h, r[i][:80]))
                        break
    assert not bad, "a path with a leading '/' (the files FullPath form has none):\n  " + "\n  ".join(bad[:12])


_LIST_KEY = re.compile(r"^(ads_names|hard_link_names|snapshot_names|ADSNames|HardLinkNames|SnapshotNames)$")


def test_k25_json_name_lists_are_lists(outs):
    bad = sorted({"%s %s=%r" % (fid, k, v) for fid, p, k, v in _json_items(outs)
                  if _LIST_KEY.match(k) and v is not None and not isinstance(v, list)})
    assert not bad, "a list of names written as a string in JSON:\n  " + "\n  ".join(bad[:12])


@pytest.mark.parametrize("names, cell", [(["a", "b"], "a;b"), (["a;b", "c"], "a\\;b;c"), (["x\\y"], "x\\\\y"),
                                         ([], "")])
def test_e4_a_csv_list_cell_escapes_the_separator(names, cell):
    assert F.csv_list_cell(names) == cell


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N167 the bodyfile
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n167_the_bodyfile_inode_is_the_objectref_and_unique(outs):
    rc, out, err = outs["files-body"]
    rows = [ln.split("|") for ln in out.splitlines() if ln.count("|") == 10]
    assert rows, "no bodyfile rows"
    bad = [r for r in rows if not re.fullmatch(r"0x[0-9a-f]+:0x[0-9a-f]+", r[2])]
    assert not bad, "an inode that is not the ObjectRef: %r" % [r[1:4] for r in bad[:5]]
    by_inode = {}
    for r in rows:
        by_inode.setdefault(r[2], set()).add(r[1])
    # one inode per object: the names of one inode are hard links of one file (same size, same times)
    rc2, out2, err2 = outs["files-csv"]
    refs = {}
    for r in csv.DictReader(io.StringIO(out2)):
        refs.setdefault(r.get("ObjectRef"), set()).add(r.get("FullPath"))
    clash = [i for i, names in by_inode.items() if len(names) > 1 and len(refs.get(i, ())) < len(names)]
    assert not clash, "an inode shared by different objects: %r" % clash[:5]


def test_n167_the_bodyfile_mode_follows_tsk():
    assert F.attrs_to_mode(0x20, False) == "r/rrwxrwxrwx"
    assert F.attrs_to_mode(0x21, False) == "r/rr-xr-xr-x"          # the meta type, then the 9 permission bits
    assert F.attrs_to_mode(0x10, True) == "d/drwxrwxrwx"
    assert F.attrs_to_mode(0x420, False) == "l/lrwxrwxrwx"



# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# E2 close (review S4 b): the text properties the rule sheet states and no node checked -- K19 (a boolean in text is a
# word), R4 (identifiers / offsets / flag words unpadded; fixed-width words keep their width), K14 / R9 (a flag word's
# hex first, its names in parentheses)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

_TEXT_BOOL = re.compile(r"(?m)(?:[:=]|\s{2,})\s*(True|False)\s*$")


def test_k19_control_the_text_boolean_scanner():
    assert _TEXT_BOOL.search("    Relative:  False") and _TEXT_BOOL.search("    Key == Value: True")
    assert not _TEXT_BOOL.search("    Relative:  no") and not _TEXT_BOOL.search("  the file is True to its name")


def test_k19_a_boolean_in_text_is_a_word(outs):
    bad = _hits(outs, _TEXT_BOOL, where=lambda fid, w: not _is_json_form(fid) and not _is_csv_form(fid))
    assert not bad, "a Python boolean in text:\n  " + "\n  ".join(bad)


_PADDED_HEX = re.compile(r"\b0x0[0-9a-f]+\b")
# R4: the fixed-width words keep their width -- serial / journal id / LSN / raw FILETIME / log positions (16 digits),
# signature / tag / format magic / NTSTATUS / CRC-32 (8), a 16-bit checksum (4, on a line naming the checksum), a byte
# (2, in a byte listing or an `old -> new` byte change)
_CKSUM_LINE = re.compile(r"(?i)checksum|cksum|stored|computed|crc")


def _padded_ok(tok, line):
    n = len(tok) - 2
    return n in (8, 16) or (n == 4 and _CKSUM_LINE.search(line)) or (n == 2 and "->" in line)


def test_r4_control_the_padding_scanner():
    assert [m.group(0) for m in _PADDED_HEX.finditer("  0   Object ID Table   0x02   0x10c08")] == ["0x02"]
    assert not _padded_ok("0x02", "  0   Object ID Table   0x02") and _padded_ok("0x0000000a", "tag 0x0000000a")
    assert _padded_ok("0x0a", "  0x14: 0x0a -> 0x0b") and not _padded_ok("0x00", "Signature   0x00   53 55 50 42")


def test_r4_text_identifiers_offsets_and_flag_words_are_unpadded(outs):
    bad = []
    for w, fid, t in _texts(outs):
        if _is_json_form(fid) or _is_csv_form(fid):
            continue
        for ln in t.splitlines():
            if any(not _padded_ok(m.group(0), ln) for m in _PADDED_HEX.finditer(ln)):
                bad.append("%s: %s" % (w, ln.strip()[:160]))
                break
    assert not bad, "a padded identifier / offset / flag word in text (R4):\n  " + "\n  ".join(bad[:15])


_NAMES_FIRST = re.compile(r"\b[A-Z][A-Z0-9_]{2,}(?:\s*\|\s*[A-Z][A-Z0-9_]+)*\s*\(0x[0-9a-f]+\)")


def test_k14_control_the_order_scanner():
    assert _NAMES_FIRST.search("    Source:  DATA_MANAGEMENT (0x00000001)")
    assert not _NAMES_FIRST.search("    Source:  0x1 (DATA_MANAGEMENT)")


def test_k14_a_flag_words_hex_comes_first_in_text(outs):
    bad = _hits(outs, _NAMES_FIRST, where=lambda fid, w: not _is_json_form(fid) and not _is_csv_form(fid))
    assert not bad, "a flag word's names before its hex (R9 says `0xH (names)`):\n  " + "\n  ".join(bad)
