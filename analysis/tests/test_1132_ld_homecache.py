"""The labs-and-driver batch (1.14.0): `deleted`'s cost on the largest volumes (the maintainer, 2026-11-08: "Do complete
verification, be sure to avoid introducing regression").

`_analyze_dir_extents` resolves a split file's backing from its HOME tree (`_home_streams`), with a cache that lived for
one call -- one directory. `dataruns` walks directory by directory, and `deleted`'s live-cluster map (Q-B) calls it for
every object, so a home tree that files of many directories point at was walked and its backings decoded again for each
of them (winsider: 209,256 holder decodes; 74 % of the map's build). A caller now keeps one `home_cache` over its walk.

What must not change: anything the tool prints, or any count it keeps. A decode can record things besides its result --
a skip note, a finding, a damaged page, a translation miss, a marker-scan map -- and the run prints those counts at exit.
So a home tree's decoded streams are kept only when decoding them recorded nothing (`_run_state_mark` equal before and
after), and each call gets objects of its own (a deep copy), as a decode gives them.

Written RED on the dev tool before the change (17384e42). Images: the public sample (91 home trees decoded again 360
times by the map over its 250 objects), win10refs5g64k (one home tree, 19 times).
"""
import collections
import contextlib
import copy
import hashlib
import io
import json
import os
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

_fx = AB._fx
FOREFST = os.path.join(REPO, "forefst.py")
SAMPLE = "step5/win11refstestmftecmd.raw"
IMG64K = "step2/win10refs5g64k.raw"


def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _fresh(monkeypatch):
    """Every module register fresh (restored afterwards), so an in-process run starts from nothing."""
    for name in F._MODULE_REGISTERS:
        cur = vars(F).get(name)
        if name == "_PAGE_VERIFY":
            monkeypatch.setattr(F, name, {"checked": 0, "ok": 0, "bad": [], "no_digest": 0, "unreadable": 0,
                                          "_seen": set()})
        elif isinstance(cur, F._DamageList):
            monkeypatch.setattr(F, name, type(cur)())
        elif isinstance(cur, (list, dict, set)):
            monkeypatch.setattr(F, name, type(cur)())


def _boot(path):
    with contextlib.redirect_stderr(io.StringIO()):
        return F.bootstrap(path, None)


def _remote_homes(boot):
    """{home oid: [the directories whose files' backings it holds]} -- from the results' own words (extent_source
    'remote', target_oid), every object of the Object Table, no cache."""
    f, ps, cs, tr, _r, om = boot[:6]
    homes = collections.defaultdict(set)
    with contextlib.redirect_stderr(io.StringIO()):
        for oid in list(om):
            for info in F._analyze_dir_extents(f, ps, cs, tr, om, oid):
                if info.get("extent_source") == "remote":
                    homes[info["target_oid"]].add(oid)
    return {h: sorted(d) for h, d in homes.items()}


# ═══ the mark: every register a decode can change ═════════════════════════════════════════════════════════════

def _bump(name, v):
    """Change register `v` the way a recording does (append / add / count), in place; returns an undo."""
    if isinstance(v, F._DamageList):
        v.total += 1
        return lambda: setattr(v, "total", v.total - 1)
    if name in ("_SKIP_NOTES", "_SKIP_EXPECTED"):
        v[("x", "y")] = 1                                # a key first (len), then its count: both must be seen
        return lambda: v.pop(("x", "y"))
    if name == "_PAGE_VERIFY":
        v["no_digest"] += 1
        return lambda: v.__setitem__("no_digest", v["no_digest"] - 1)
    if name == "_HELD":
        v.append([])
        return v.pop
    if isinstance(v, list):
        v.append(object())
        return v.pop
    if isinstance(v, set):
        o = object()
        v.add(o)
        return lambda: v.discard(o)
    if isinstance(v, dict):
        o = object()
        v[o] = 1
        return lambda: v.pop(o)
    return None


def test_hc_mark_sees_every_register(monkeypatch):
    """Each register of `_MODULE_REGISTERS` but `_OBJ_ROOT_VERIFIED` -- changed as a recording changes it -- changes
    the mark; so do a count of an existing key, a note kept in a held reading, and the translator's miss count and its
    'said' set. A register this test cannot change is named, so a new kind of register is not silently unseen."""
    _fresh(monkeypatch)
    tr = F.Translator({2: 0x100}, 0x40)
    base = F._run_state_mark(tr)
    unseen, unchangeable = [], []
    for name in F._MODULE_REGISTERS:
        if name == "_OBJ_ROOT_VERIFIED":
            continue
        v = vars(F).get(name)
        if isinstance(v, (bool, int, type(None))) and not isinstance(v, F._DamageList):
            old = v
            monkeypatch.setattr(F, name, (not v) if isinstance(v, bool) else (object() if v is None else v + 1))
            if F._run_state_mark(tr) == base:
                unseen.append(name)
            monkeypatch.setattr(F, name, old)
            continue
        undo = _bump(name, v)
        if undo is None:
            unchangeable.append(name)
            continue
        if F._run_state_mark(tr) == base:
            unseen.append(name)
        undo()
        assert F._run_state_mark(tr) == base, name
    assert not unseen, "a change of these registers leaves the mark equal: %s" % unseen
    assert not unchangeable, "registers of a kind this test cannot change: %s" % unchangeable
    # a count of a key already present (the length alone would not change)
    F._SKIP_NOTES[("stage", "ValueError")] = 1
    m = F._run_state_mark(tr)
    F._SKIP_NOTES[("stage", "ValueError")] = 2
    assert F._run_state_mark(tr) != m
    # a note kept in a held reading, a translation miss, a container said once
    F._HELD.append([])
    m = F._run_state_mark(tr)
    F._HELD[-1].append("a note")
    assert F._run_state_mark(tr) != m
    F._HELD.pop()
    m = F._run_state_mark(tr)
    tr.misses += 1
    assert F._run_state_mark(tr) != m
    m = F._run_state_mark(tr)
    tr._said.add(7)
    assert F._run_state_mark(tr) != m


def test_hc_mark_leaves_out_root_verification_only(monkeypatch):
    """`_OBJ_ROOT_VERIFIED` is left out: a root page is verified once per view, so a walk repeated after it finds the
    object verified and records nothing; a failed verification is a finding, which the mark sees."""
    _fresh(monkeypatch)
    tr = F.Translator({2: 0x100}, 0x40)
    m = F._run_state_mark(tr)
    F._OBJ_ROOT_VERIFIED.add(0x701)
    assert F._run_state_mark(tr) == m
    F._finding("page-reference mismatch", "planted")
    assert F._run_state_mark(tr) != m


# ═══ one cache per walk: the callers ══════════════════════════════════════════════════════════════════════════

def _spy_calls(monkeypatch):
    calls = []
    orig = F._analyze_dir_extents

    def spy(*a, **k):
        calls.append(k.get("home_cache"))
        return orig(*a, **k)
    monkeypatch.setattr(F, "_analyze_dir_extents", spy)
    return calls


def test_hc_dataruns_keeps_one_cache_over_its_walk(monkeypatch):
    path = _img(SAMPLE)
    _fresh(monkeypatch)
    calls = _spy_calls(monkeypatch)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        F.cmd_dataruns(path, [], None)
    _fx(len(calls) > 1, "dataruns made %d call(s)" % len(calls))
    assert all(c is not None for c in calls), "a call of dataruns' walk was given no cache"
    assert len({id(c) for c in calls}) == 1, "dataruns' walk used more than one cache"


def test_hc_live_cluster_map_keeps_one_cache(monkeypatch):
    boot = _boot(_img(SAMPLE))
    f, ps, cs, tr, _r, om = boot[:6]
    _fresh(monkeypatch)
    calls = _spy_calls(monkeypatch)
    with contextlib.redirect_stderr(io.StringIO()):
        F._build_live_cluster_index(f, ps, cs, tr, om, lambda d, n: "%x/%s" % (d, n))
    assert len(calls) == len(om)
    assert all(c is not None for c in calls) and len({id(c) for c in calls}) == 1


def test_hc_each_home_tree_decoded_once_on_the_sample(monkeypatch):
    """The sample: with one cache, each home tree is walked once for the map (it was walked once per directory)."""
    boot = _boot(_img(SAMPLE))
    f, ps, cs, tr, _r, om = boot[:6]
    homes = _remote_homes(boot)
    _fx(sum(len(d) for d in homes.values()) > len(homes), "the sample has no home tree two directories share")
    walks = collections.Counter()
    orig = F.walk_bplus

    def counting(*a, **k):
        walks[k.get("oid")] += 1
        return orig(*a, **k)
    monkeypatch.setattr(F, "walk_bplus", counting)
    hc = {}
    with contextlib.redirect_stderr(io.StringIO()):
        for oid in list(om):
            F._analyze_dir_extents(f, ps, cs, tr, om, oid, home_cache=hc)
    assert set(hc) == set(homes), "a home tree whose decode recorded nothing was not kept"
    for h in homes:
        assert walks[h] == 2, (hex(h), walks[h])         # its own directory walk + one home decode


# ═══ nothing changes: results, every register, the output ═══════════════════════════════════════════════════

_RUN = r'''
import collections, contextlib, hashlib, io, json, sys
sys.path.insert(0, sys.argv[1])
import forefst as F
mode, img = sys.argv[2], sys.argv[3]

def canon(x):
    if isinstance(x, dict):
        return sorted([canon(k), canon(v)] for k, v in x.items())
    if isinstance(x, (set, frozenset)):
        return sorted(canon(v) for v in x)
    if isinstance(x, (list, tuple)):
        return [canon(v) for v in x] + ([["total", x.total], ["pages", canon(x.pages)]] if hasattr(x, "pages") else [])
    if isinstance(x, (bytes, bytearray)):
        return hashlib.sha256(bytes(x)).hexdigest()
    if isinstance(x, (int, float, str, bool, type(None))):
        return x
    if isinstance(x, F.Translator):
        return ["Translator", x.misses, canon(x._said)]
    return type(x).__name__

out, err = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
    f, ps, cs, tr, roots, om = F.bootstrap(img, None)[:6]
    hc = {}
    res = []
    for oid in list(om):
        try:
            r = (F._analyze_dir_extents(f, ps, cs, tr, om, oid, home_cache=hc) if mode == "shared"
                 else F._analyze_dir_extents(f, ps, cs, tr, om, oid))
        except Exception as e:
            r = "raised " + repr(e)
        res.append([oid, canon(r)])
state = {n: hashlib.sha256(json.dumps(canon(vars(F).get(n)), sort_keys=True).encode()).hexdigest()
         for n in F._MODULE_REGISTERS}
print(json.dumps({"results": hashlib.sha256(json.dumps(res, sort_keys=True).encode()).hexdigest(),
                  "n": len(res), "state": state, "tr": canon(tr), "out": out.getvalue(), "err": err.getvalue()}))
'''


def _run_mode(mode, image):
    env = dict(os.environ, PYTHONHASHSEED="0")
    r = subprocess.run([sys.executable, "-B", "-c", _RUN, REPO, mode, image], capture_output=True, text=True,
                       timeout=1800, env=env)
    _fx(r.returncode == 0 and r.stdout.strip(), "the %s run failed:\n%s" % (mode, r.stderr[-3000:]))
    return json.loads(r.stdout.strip().splitlines()[-1]), r.stderr


@pytest.mark.parametrize("rel", [SAMPLE, IMG64K])
def test_hc_every_object_same_results_and_same_run_state(rel):
    """`_analyze_dir_extents` over every object with one cache and without: the same results, the same value of
    every register (every count the run prints at exit), the translator's counts, the same output, at exit too."""
    path = _img(rel)
    a, a_exit = _run_mode("percall", path)
    b, b_exit = _run_mode("shared", path)
    assert a["n"] == b["n"] and a["results"] == b["results"]
    assert {n for n in a["state"] if a["state"][n] != b["state"].get(n)} == set()
    assert a["tr"] == b["tr"] and a["out"] == b["out"] and a["err"] == b["err"] and a_exit == b_exit


_MAIN = r'''
import sys
sys.path.insert(0, sys.argv[1])
import forefst as F
if sys.argv[2] == "off":
    F._run_state_mark = lambda tr: object()          # never equal: nothing kept, every home tree decoded again
sys.argv = [sys.argv[1] + "/forefst.py"] + sys.argv[3:]
F.main()
'''


def _main(mode, *argv):
    r = subprocess.run([sys.executable, "-B", "-c", _MAIN, REPO, mode] + list(argv), capture_output=True,
                       text=True, timeout=3600)
    _fx("Traceback (most recent call last)" not in r.stderr, "the tool crashed:\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


@pytest.mark.parametrize("rel,args", [
    (SAMPLE, ["dataruns"]), (SAMPLE, ["dataruns", "-v"]), (SAMPLE, ["dataruns", "--csv"]),
    (SAMPLE, ["deleted"]), (IMG64K, ["deleted"]), (IMG64K, ["dataruns", "--json"]),
])
def test_hc_command_output_unchanged(rel, args):
    """The commands that keep a cache, with it and with nothing kept: the same exit code, stdout and stderr."""
    path = _img(rel)
    assert _main("on", path, *args) == _main("off", path, *args)


# ═══ the planted counterexamples ══════════════════════════════════════════════════════════════════════════════

def _planted_note_runs(monkeypatch, boot, home, shared, mark=None):
    """Every object's `_analyze_dir_extents`, with a skip note planted in each decode of `home`'s backings; returns
    how many notes the run counted."""
    f, ps, cs, tr, _r, om = boot[:6]
    monkeypatch.setattr(F, "_SKIP_EXPECTED", {})
    cur = {"oid": None}
    walk, dec = F.walk_bplus, F._decode_holder_extents

    def walk_(*a, **k):
        cur["oid"] = k.get("oid")
        return walk(*a, **k)

    def dec_(*a, **k):
        if cur["oid"] == home:
            F._skip_note("planted", "a backing of home 0x%x" % home, ValueError("planted"), expected=True)
        return dec(*a, **k)
    monkeypatch.setattr(F, "walk_bplus", walk_)
    monkeypatch.setattr(F, "_decode_holder_extents", dec_)
    if mark is not None:
        monkeypatch.setattr(F, "_run_state_mark", mark)
    hc = {}
    with contextlib.redirect_stderr(io.StringIO()):
        for oid in list(om):
            if shared:
                F._analyze_dir_extents(f, ps, cs, tr, om, oid, home_cache=hc)
            else:
                F._analyze_dir_extents(f, ps, cs, tr, om, oid)
    monkeypatch.setattr(F, "walk_bplus", walk)
    monkeypatch.setattr(F, "_decode_holder_extents", dec)
    return sum(F._SKIP_EXPECTED.values()), hc


@pytest.fixture(scope="module")
def sample_boot():
    return _boot(_img(SAMPLE))


@pytest.fixture(scope="module")
def shared_home(sample_boot):
    homes = _remote_homes(sample_boot)
    h = max(homes, key=lambda x: (len(homes[x]), -x))
    _fx(len(homes[h]) >= 2, "no home tree two directories share")
    return h, homes[h]


def test_hc_a_decode_that_records_is_done_again(monkeypatch, sample_boot, shared_home):
    """A home tree whose decode records a note is decoded again for every directory, as before: the run counts the
    same notes with one cache as without, and the tree is not kept."""
    home, dirs = shared_home
    n_ref, _ = _planted_note_runs(monkeypatch, sample_boot, home, shared=False)
    n_hc, hc = _planted_note_runs(monkeypatch, sample_boot, home, shared=True)
    _fx(n_ref > 0, "the planted note fired 0 times")
    assert n_hc == n_ref and home not in hc


def test_hc_counterexample_a_cache_without_the_mark_loses_counts(monkeypatch, sample_boot, shared_home):
    """The instrument can emit its counterexample: with a mark that never sees a change, the same run counts FEWER
    notes (the tree kept after its first decode) -- the change the mark prevents."""
    home, dirs = shared_home
    n_ref, _ = _planted_note_runs(monkeypatch, sample_boot, home, shared=False)
    n_bad, hc = _planted_note_runs(monkeypatch, sample_boot, home, shared=True, mark=lambda tr: 0)
    assert home in hc and n_bad < n_ref


def test_hc_a_reuse_gives_objects_of_its_own(sample_boot, shared_home):
    """A call that changes what it was given (an extent's field, the extent list) changes nothing a later call is
    given: each call gets its own copy, as a decode gives it; the kept copy is the decode's own."""
    home, dirs = shared_home
    f, ps, cs, tr, _r, om = sample_boot[:6]
    hc = {}
    with contextlib.redirect_stderr(io.StringIO()):
        first = F._analyze_dir_extents(f, ps, cs, tr, om, dirs[0], home_cache=hc)
        _fx(home in hc, "the home tree was not kept")
        kept = copy.deepcopy(hc[home])
        touched = 0
        for info in first:
            if info.get("target_oid") == home and info.get("extents"):
                for x in info["extents"]:
                    x["plcn"] = -7
                info["extents"].append({"planted": 1})
                touched += 1
        _fx(touched, "no file of 0x%x has extents from 0x%x" % (dirs[0], home))
        again = F._analyze_dir_extents(f, ps, cs, tr, om, dirs[1], home_cache=hc)
        fresh = F._analyze_dir_extents(f, ps, cs, tr, om, dirs[1])
    assert hc[home] == kept
    assert again == fresh
