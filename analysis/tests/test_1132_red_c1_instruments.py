"""1.13.2 (ships as 1.14.0) RED cases, wave C step C1, area `instruments`: N433 (instruments that read keys wave B
renamed or removed now read nothing or fail).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md`, `fixes/WAVEC_PREP.md` section 3 Q14 (settled: LIVE
instruments read the new keys and check their keys exist; frozen copies and report evidence are history and are not
edited), `fixes/WAVEC_CENSUS.md` (the N433 row), `fixes/FIX_GB_part1b.md` section 5 (N411's class: the instruments
named for the lead) and the migration tables of wave B (`FIX_GB_part1.md` 1.2, `FIX_GB_part1b.md` 1.2.1,
`FIX_GB_part3.md` 1.1). Report: `analysis/reports/v1.13.2/fixes/RED_C1.md`.

What wave B removed from the tool's MLog dictionaries (decision 33, corrected in place; measured here by reading the
current `parse_mlog_control_page` / `scan_mlog_data_area` / `_mlog_resolve_txn` against the keys below, a control):
  * `parse_mlog_control_page` (and `read_mlog_control`, which returns its dict): `total_entries` (+0x48) and
    `ctrl_uuid` (+0x50) -- fields the driver does not have there (N411: `host_info` +0x44, `payload_uuid` +0x28) --,
    `lsn_oldest` (-> `log_start`), `generation` (-> `log_end`), `write_counter` (-> `log_open_count`), `sequence_raw`
    (-> `header_open_count`), `sector_size` (-> `log_block_size`);
  * `scan_mlog_data_area`'s pages: `block_lcn`, `vlcn` (N259: `block_index`);
  * `_mlog_resolve_txn`'s row: `ops_str`.
(`data_start_lcn` / `data_end_lcn` left the control dict too, but stay keys of `get_mlog_info`'s row, so a read of
them cannot be told apart by name; they are not searched.)

The live instruments (Q14): `analysis/verification/` (without the external audit's `audit_oracle/` and the frozen
`phase0/P0.5_audit_oracle/demo/` copies), `analysis/tools/`, `forefstdev/analysis/` (without the tests), `forefstdev/
scripts/`, `analysis/reports/v1.13.2/d42/`. Report evidence (`analysis/reports/**`, e.g.
`fixes/waveB_prep_evidence/census/census_one.py`) is history: it is the scan's planted counterexample, not a site.

  N433-1  the class scan: no live instrument that calls one of those functions reads a key of its removed set (it
          would read None, or raise). On the current tree: `analysis/tools/analysis_scripts/refs_mlog.py`.
  N433-2  `refs_mlog.py`'s control parser reads the fields wave B corrected: none of the removed keys, and the payload
          UUID (+0x28) and the u64 at +0x44 under the tool's names, with the tool's values (step1/win11refsmini).
  N433-3  `refs_mlog.py`'s text view prints no "Total entries" (+0x48, 0 on 240 of 240 corpus copies, N411).
  N433-4  (Q14's second clause, "check their keys exist") `refs_mlog.py`, handed a control dict whose keys it does not
          know (every key renamed), does not print its control area with placeholders and exit 0: it fails, or names
          the missing keys.
The instrument is measured against the DEV tool's forefst (the tree wave B changed and 1.14.0 publishes): the
subprocess nodes import forefstdev's forefst before running refs_mlog.py, whose own `sys.path` insert would otherwise
pick the published 1.13.1 tree (critic, RED_C1_critic.md I-2).
C1-1 (1.14.0, the conformance batch): refs_mlog.py is retired (analysis/archive/retired_instruments/README.md); N433-2..4's
nodes are replaced by `test_c1_1_refs_mlog_is_retired_not_a_live_instrument`.
"""
import contextlib
import importlib.util
import io
import os
import re
import subprocess
import sys

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402
import test_1132_red_mlog_chkp as MC                     # noqa: E402
import test_1132_red_c1_objtable as OT                   # noqa: E402

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
_red = OT._red

WS = os.path.dirname(REPO)                               # the workspace (or the USB mirror) holding forefstdev/
IMG = "step1/win11refsmini.raw"

REMOVED = {
    "parse_mlog_control_page": ("total_entries", "ctrl_uuid", "lsn_oldest", "generation", "write_counter",
                                "sequence_raw", "sector_size"),
    "read_mlog_control": ("total_entries", "ctrl_uuid", "lsn_oldest", "generation", "write_counter",
                          "sequence_raw", "sector_size"),
    "scan_mlog_data_area": ("block_lcn", "vlcn"),
    "_mlog_resolve_txn": ("ops_str",),
}
LIVE_ROOTS = ("analysis/verification", "analysis/tools", "forefstdev/analysis", "forefstdev/scripts",
              "analysis/reports/v1.13.2/d42")
HISTORY = re.compile(r"(?:^|/)(?:audit_oracle|P0\.5_audit_oracle/demo|tests|__pycache__|reports/audit)(?:/|$)"
                     r"|plant_copy")
REFS_MLOG = os.path.join(WS, "analysis", "tools", "analysis_scripts", "refs_mlog.py")
CENSUS_ONE = os.path.join(WS, "analysis", "reports", "v1.13.2", "fixes", "waveB_prep_evidence", "census",
                          "census_one.py")


def removed_reads(path):
    """[(function, key, line)] -- reads (`["key"]` or `.get("key"`) of a key removed from a function's dict, in a file
    that imports forefst and names that function."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    if not re.search(r"(?m)^\s*(?:import\s+forefst|from\s+forefst\s+import)", src):
        return []
    out = []
    for fn, keys in REMOVED.items():
        if not re.search(r"\b%s\b" % re.escape(fn), src):
            continue
        for k in keys:
            for m in re.finditer(r"""\[\s*["']%s["']\s*\]|\.get\(\s*["']%s["']""" % (k, k), src):
                out.append((fn, k, src.count("\n", 0, m.start()) + 1))
    return out


def live_instruments():
    out = []
    for r in LIVE_ROOTS:
        base = os.path.join(WS, r)
        for d, _ds, fs in os.walk(base):
            for fn in fs:
                p = os.path.join(d, fn)
                rel = os.path.relpath(p, WS)
                if fn.endswith(".py") and not HISTORY.search(rel):
                    out.append(p)
    _fx(len(out) > 50, "only %d live instruments found under %s" % (len(out), WS))
    return out


def test_n433_control_the_removed_keys_are_gone_from_the_tool():
    """Not a RED: the premise. The current tool's control dict (both copies of step1/win11refsmini) carries none of the
    removed keys and carries their replacements; a data-area page carries `block_index`, not `block_lcn` / `vlcn`."""
    out = io.StringIO()
    with contextlib.redirect_stderr(out):
        f, ps, cs, tr, roots, om, *_r = F.bootstrap(MC.corpus(IMG), None)
    try:
        mi = F.get_mlog_info(f, ps, cs, tr, om)
        ctrls = []
        for key in ("ctrl_plcn_0", "ctrl_plcn_1"):
            ctrls.append(F.parse_mlog_control_page(F._seek_read(f, ps + mi[key] * cs, max(cs, 4096))))
        page = next(iter(F.scan_mlog_data_area(f, ps, cs, tr, mi, F.read_mlog_control(f, ps, cs, mi))))
    finally:
        f.close()
    _keep(all(c and not set(REMOVED["parse_mlog_control_page"]) & set(c)
              and {"host_info", "payload_uuid", "log_start", "log_end", "log_open_count"} <= set(c) for c in ctrls),
          "the tool's control dicts: %r" % [sorted(c or ()) for c in ctrls])
    _keep("block_index" in page and not {"block_lcn", "vlcn"} & set(page), "a data-area page: %r" % sorted(page))


def test_n433_control_the_scan_emits_its_counterexample_on_the_waveb_census_instrument():
    """Not a RED: the scan can fail. Report evidence (history, Q14: not edited) -- `census_one.py` reads
    `total_entries` / `ctrl_uuid` from `parse_mlog_control_page`, so the scan names it."""
    _fx(os.path.isfile(CENSUS_ONE), "census_one.py not found at %s" % CENSUS_ONE)
    hits = {(fn, k) for fn, k, _ln in removed_reads(CENSUS_ONE)}
    _keep({("parse_mlog_control_page", "total_entries"), ("parse_mlog_control_page", "ctrl_uuid")} <= hits,
          "the scan does not see census_one.py's reads: %r" % sorted(hits))


# RED 1.13.2 N433: a live instrument (refs_mlog.py) reads keys wave B removed from the tool's MLog dictionaries -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n433_no_live_instrument_reads_a_key_wave_b_removed():
    found = {}
    for p in live_instruments():
        hits = removed_reads(p)
        if hits:
            found[os.path.relpath(p, WS)] = sorted({"%s[%r] (line %d)" % (fn, k, ln) for fn, k, ln in hits})[:6]
    assert not found, "live instruments read keys wave B removed (decision 33) -- they read None, or raise (N433; Q14: " \
        "each reads the new keys): %s" % "; ".join("%s: %s" % (p, ", ".join(v)) for p, v in sorted(found.items()))


# C1-1 (1.14.0, the conformance batch): refs_mlog.py, the instrument N433-2..N433-4 measured, is RETIRED -- a pre-E97
# MLog parser (137 records / 0 commits on win11refsmini against the driver framing's 746 / 362) -- and kept in
# analysis/archive/retired_instruments/ with mlog_differential.py (built on it) and test_all_tools.py (dead paths), each
# with its reason. The four nodes that ran it are replaced by this one: it is not a live instrument any more.
RETIRED = os.path.join(WS, "analysis", "archive", "retired_instruments")


def test_c1_1_refs_mlog_is_retired_not_a_live_instrument():
    assert not os.path.exists(REFS_MLOG), "refs_mlog.py is among the live instruments again (%s)" % REFS_MLOG
    for fn in ("refs_mlog.py", "mlog_differential.py", "test_all_tools.py", "README.md"):
        assert os.path.isfile(os.path.join(RETIRED, fn)), "%s is not kept in %s" % (fn, RETIRED)
    with open(os.path.join(RETIRED, "README.md"), encoding="utf-8") as fh:
        readme = fh.read()
    assert "refs_mlog.py" in readme and "forefst <image> mlog" in readme, "the README says neither why nor what instead"


def _instrument(name):
    p = os.path.join(WS, "analysis", "tools", "analysis_scripts", name)
    _fx(os.path.isfile(p), "%s not found at %s" % (name, p))
    spec = importlib.util.spec_from_file_location(name[:-3] + "_c1", p)
    mod = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = saved
    return mod


def test_n433_the_mlog_csv_instruments_read_the_tools_column_names():
    """The class beyond the RED scan (FIX_C1_instruments.md section 5): two live instruments read `mlog --parse --csv`
    by its 1.13.1 column names (`timestamp`, `path`, `name`) and so read nothing. Their columns are the tool's
    (`MLOG_CSV_COLUMNS`, the one definition of the header), and a header without them stops the run, named."""
    mwc, t21 = _instrument("mlog_window_coverage.py"), _instrument("t21_fill_truth_table.py")
    for mod in (mwc, t21):
        assert set(mod.MLOG_COLUMNS) <= set(F.MLOG_CSV_COLUMNS), \
            "%s reads %r; the tool's header: %r" % (mod.__name__, mod.MLOG_COLUMNS, F.MLOG_CSV_COLUMNS)
    try:
        mwc.csv_rows("seq,timestamp,action,path,name\n1,2026-05-14T06:26:07.050Z,CREATE,a,b\n", mwc.MLOG_COLUMNS,
                     "mlog --parse --csv")
    except SystemExit as e:
        said = str(e)
    else:
        said = ""
    assert "Timestamp" in said and "Name" in said, "a 1.13.1 header was read without a word: %r" % said
