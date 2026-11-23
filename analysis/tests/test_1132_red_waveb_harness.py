"""1.13.2 (ships as 1.14.0) RED cases, wave B stage 2b: the harness items N386, N385, N399 (b) and E-5.

Read first: `analysis/reports/v1.13.2/fixes/WAVEB_PREP.md` (LB6 and LB20 for N386; LB21 and LB23 for E-5; the harness
items), `fixes/WAVEB_CENSUS.md` section 2.12 (N386's lookup census), the running-log rows N385, N386 (with its "Widened
2026-10-14" note) and N399, and PLAN_1.13.2 row E-5. Report: `analysis/reports/v1.13.2/red/RED_waveB_rest.md` (with
test_1132_red_waveb_rest.py); amended 2026-10-15 after the RED critic (D1, D12, D13) and LB20-LB23, and again after
LB34-LB35: `red/RED_waveB_amend.md`.

  N386     (LB6, LB20) no test names an image by a basename that exists twice in the corpus; the shared lookups refuse
           such a name, accept a step path, and keep resolving a unique bare name; BASE_IMAGE is step1/win11refsmini.raw
           and test_exit_codes' clean volume step2/win11refs8g.raw.
  N385     gate 6 does not depend on the host's temp filesystem: no host-probe skip remains (sites found by their
           probes), or the skip ceiling is computed from the probes' results and the gate line prints the ceiling AND
           those results (the two branches of N385's row; LB35).
  N399 (b) golden_gen.sh fingerprints `integrity --json` (one form per image).
  E-5      (LB21, LB23, LB34) golden_gen.sh, when GOLDEN_STREAMS_OUT names a file, appends one line
           `<image>|<command>|stdout=<sha256>|stderr=<sha256>` per row of every emitter, `extract` included (its
           stdout hash is the row's content hash, its stderr hash the statements the row discards: LB34); the parent
           sorts it at the end; the golden's own 4-field rows are unchanged (the merged hash stays the chain key), and
           with the variable unset nothing changes.

The golden nodes run golden_gen.sh in its `--one` mode with a FAKE tool directory (a forefst.py / refsanalysis.py that
print one known stdout line and one known stderr line): the form list and the hashing are measured without running the
real tool on any image (about 1 s per run). The harness files are read, never written.
Conventions as test_1132_red_a_bootstrap.py: ``xfail(strict=True, raises=AssertionError)``; RedFixtureError /
KeptPropertyBroken for a fixture that is not what the case needs / a property the harness has today.
"""
import ast
import hashlib
import importlib
import inspect
import io
import os
import re
import subprocess
import sys
import tokenize

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions)
import test_1132_red_mlog_chkp as MC                     # noqa: E402  (corpus, _red)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
_red = MC._red

HERE = os.path.dirname(os.path.abspath(__file__))
OWN = {"test_1132_red_waveb_harness.py", "test_1132_red_waveb_rest.py"}
_WS = os.path.dirname(REPO) if os.path.basename(REPO) == "forefstdev" else REPO
VERIFICATION = os.environ.get("G2C_VERIFICATION_DIR") or os.path.join(_WS, "analysis", "verification")


def _harness_file(name):
    p = os.path.join(VERIFICATION, name)
    if not os.path.isfile(p):
        pytest.skip("the verification harness (%s) is not in this tree" % name)
    return p


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N386 (LB6) -- images by step path; a bare duplicated basename refused
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Six basenames occur twice in the corpus (census 2.12; two of them on byte-identical copies, four on different
# volumes). A lookup by bare name returns whichever copy the directory walk meets first: on the USB key
# win11refs8g.raw resolves to step6 (not step2), and the two `test_exit_codes` nodes fail (USB_BASELINE_G3 section 5).
# LB6: every test addresses an image by its step path (or a pinned hash); the shared lookups refuse a bare basename
# that exists twice. The static node reads string literals only (comments and this wave's two RED files excluded).

DUP_CENSUS = {"win10refsmini.raw", "win11refsmini.raw", "win11refs8g.raw", "win11ntfs.raw", "win11refslasttests.raw",
              "win11refslasttests_baseline.raw"}       # WAVEB_CENSUS 2.12; the scan below adds any the corpus shows


def _dups():
    root = MC._disks_root()
    names = {}
    if root:
        for d, _s, fs in os.walk(root):
            for fn in fs:
                if fn.endswith(".raw"):
                    names.setdefault(fn, []).append(os.path.relpath(os.path.join(d, fn), root))
    return root, {k: sorted(v) for k, v in names.items() if len(v) > 1}


def _literal_sites(names):
    hits = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn in OWN:
            continue
        with open(os.path.join(HERE, fn), encoding="utf-8") as fh:
            src = fh.read()
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type != tokenize.STRING:
                continue
            try:
                v = ast.literal_eval(tok.string)
            except (ValueError, SyntaxError) as e:      # LB45: 0 such tokens in the suite today; never skipped silently
                raise RedFixtureError("%s:%d: a string token that is not a literal (%r): the scan cannot read it"
                                      % (fn, tok.start[0], e))
            if isinstance(v, str) and v in names:
                hits.append("%s:%d %r" % (fn, tok.start[0], v))
    return hits


# RED 1.13.2 N386: green with wave B part 3's fix (the strict xfail mark removed)
def test_n386_no_test_names_an_image_by_a_duplicated_basename():
    root, dups = _dups()
    hits = _literal_sites(DUP_CENSUS | set(dups))
    assert not hits, "%d site(s) name an image by a duplicated bare basename (LB6: by step path):\n  %s" % (
        len(hits), "\n  ".join(hits))


# The name-resolving lookups (each wrapper resolves through `_corpus_image` or a glob of its own). `_scratch_copy`
# (b2_journal, b2_refsanalysis) and `_sample_run` (test_1131_held_items) resolve through them -- pinned by the control
# below -- and copy or run an image, so they are not called here.
_LOOKUPS = [("test_image_holes_and_page_refs", "_corpus_image"), ("test_exit_codes", "_find"),
            ("test_decoder_order_1114", "_image"), ("test_1132_red_group2b", "_image_or_skip"),
            ("test_1132_red_b2_wording", "_image_or_skip"), ("test_1132_red_b2_refsanalysis", "_image_or_skip"),
            ("test_1132_red_b_items", "_image_or_skip"), ("test_1132_red_b2_deleted", "_image_or_skip"),
            ("test_1132_red_a_coverage", "_need"), ("test_1132_red_a_verdicts", "_corpus")]
_LOOKUP_IDS = ["%s.%s" % (m[len("test_"):], f) for m, f in _LOOKUPS]
_GLOB_LOOKUPS = {("test_exit_codes", "_find"), ("test_decoder_order_1114", "_image")}


def _outcome(fn, name):
    """('returned', value) | ('skipped', why) | ('refused', the exception)."""
    try:
        return "returned", fn(name)
    except pytest.skip.Exception as e:
        return "skipped", str(e)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as e:                           # pytest.fail's Failed is a BaseException
        return "refused", repr(e)


def _corpus_or_skip():
    root, dups = _dups()
    if not root:
        pytest.skip("no image corpus here: a duplicated basename cannot occur")
    _fx(dups, "the corpus holds no duplicated basename (census: six)")
    return root, dups


# RED 1.13.2 N386: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("mod,fn", _LOOKUPS, ids=_LOOKUP_IDS)
def test_n386_a_shared_lookup_refuses_a_duplicated_basename(mod, fn):
    root, dups = _corpus_or_skip()
    name = next((n for n in sorted(dups) if n.startswith("win11refs8g")), sorted(dups)[0])
    kind, what = _outcome(getattr(importlib.import_module(mod), fn), name)
    assert kind == "refused", "%s.%s(%r) %s %r; the name exists as %s (LB6: refuse)" % (
        mod, fn, name, kind, what, " and ".join(dups[name]))


_STEP_REL = "step2/win11refs5g64k.raw"                    # a unique basename, addressed by its step path


# RED 1.13.2 N386: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("mod,fn", [x for x in _LOOKUPS if x not in _GLOB_LOOKUPS],
                         ids=[i for x, i in zip(_LOOKUPS, _LOOKUP_IDS) if x not in _GLOB_LOOKUPS])
def test_n386_a_shared_lookup_accepts_a_step_path(mod, fn):
    _corpus_or_skip()
    want = os.path.realpath(MC.corpus(_STEP_REL))
    kind, what = _outcome(getattr(importlib.import_module(mod), fn), _STEP_REL)
    assert kind == "returned" and what and os.path.realpath(what) == want, "%s.%s(%r) %s %r" % (
        mod, fn, _STEP_REL, kind, what)


@pytest.mark.parametrize("mod,fn", sorted(_GLOB_LOOKUPS), ids=["exit_codes._find", "decoder_order_1114._image"])
def test_n386_control_the_glob_lookups_already_accept_a_step_path(mod, fn):
    """Not a RED. The two glob-based lookups take a step path today (glob <root>/**/<step path>)."""
    _corpus_or_skip()
    kind, what = _outcome(getattr(importlib.import_module(mod), fn), _STEP_REL)
    assert kind == "returned" and os.path.realpath(what) == os.path.realpath(MC.corpus(_STEP_REL)), (kind, what)


@pytest.mark.parametrize("mod,fn", _LOOKUPS, ids=_LOOKUP_IDS)
def test_n386_control_a_unique_bare_basename_still_resolves(mod, fn):
    """Not a RED. LB6 refuses only a basename that exists twice: a unique bare name (56 such sites today) keeps
    resolving to its one file."""
    _corpus_or_skip()
    base = os.path.basename(_STEP_REL)
    kind, what = _outcome(getattr(importlib.import_module(mod), fn), base)
    assert kind == "returned" and os.path.realpath(what) == os.path.realpath(MC.corpus(_STEP_REL)), (kind, what)


# LB20 (critic D13): the two volumes the lead named, each by its step path -- battery base A, and the clean volume of
# test_exit_codes (what its nodes reached on the originals; step6's copy exits 2 since G3).
_LB20 = {"a_bootstrap.BASE_IMAGE": "step1/win11refsmini.raw", "exit_codes.refs_image": "step2/win11refs8g.raw"}


def _raw_literals_in(path, func):
    """The '.raw' string literals inside the function `func` of a test file (read, not imported)."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            return [c.value for c in ast.walk(n) if isinstance(c, ast.Constant) and isinstance(c.value, str)
                    and c.value.endswith(".raw")]
    raise RedFixtureError("%s has no function %s" % (os.path.basename(path), func))


# RED 1.13.2 N386: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("site", sorted(_LB20))
def test_n386_lb20_the_two_named_volumes_are_addressed_by_their_step_paths(site):
    if site == "a_bootstrap.BASE_IMAGE":
        got = [AB.BASE_IMAGE]
    else:
        got = _raw_literals_in(os.path.join(HERE, "test_exit_codes.py"), "refs_image")
    assert got == [_LB20[site]], "%s names %r; LB20: %r" % (site, got, _LB20[site])


@pytest.mark.parametrize("mod,fn", [("test_1132_red_b2_journal", "_scratch_copy"),
                                    ("test_1132_red_b2_refsanalysis", "_scratch_copy"),
                                    ("test_1131_held_items", "_sample_run")],
                         ids=["b2_journal._scratch_copy", "b2_refsanalysis._scratch_copy", "1131_held_items._sample_run"])
def test_n386_control_the_copying_lookups_resolve_through_a_shared_lookup(mod, fn):
    """Not a RED. These copy or run an image, so the refusal reaches them only through the lookup they call: each calls
    `_corpus_image` or `_image_or_skip` (read in its source) -- today and after the fix."""
    src = inspect.getsource(getattr(importlib.import_module(mod), fn))
    assert re.search(r"\b(?:_corpus_image|_image_or_skip)\(", src), src[:400]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N385 -- gate 6 does not depend on the host's temp filesystem
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Five skip sites probe the host's temp filesystem (SEEK_DATA support: test_image_holes_and_page_refs.py:43, :55, :374;
# a 300-byte name: test_extraction_safety.py:25, :65); gate 6 fails above PYTEST_MAX_SKIP=21 (verify.sh:231), so on a
# host whose /tmp lacks SEEK_DATA or accepts long names the gate fails with no defect (up to 26 skips). N385's row:
# "the host-dependent skips made host-independent, or the ceiling computed from the host's probes and reported". The
# node accepts either branch (LB35: either way the row allows). Critic D12: the sites are found by their PROBES, not by
# the skip's message words -- an `if` that tests a probe's result (or a name bound to it) and skips; a module-level
# helper that calls a probe is a probe too. LB35 settles "reported": if the ceiling is computed, the GATE LINE (gate
# 6's `ck` line, which prints `${PYTEST_MAX_SKIP}` today) prints the ceiling AND the probe results it rests on -- every
# variable the ceiling is computed from that verify.sh builds with a command (directly, or through a variable printed
# on that line). A probe result printed on another line, or the ceiling alone, is not enough.

_PROBES = {"_fs_enforces_name_limit", "_hole_bytes_in", "_extent_hole_ranges"}


def _calls_any(node, names):
    for c in ast.walk(node):
        if isinstance(c, ast.Call):
            f = c.func
            if (isinstance(f, ast.Name) and f.id in names) or (isinstance(f, ast.Attribute) and f.attr in names):
                return True
    return False


def _skips(stmts):
    return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "skip"
               for s in stmts for c in ast.walk(s))


def _probe_skip_sites(src):
    """Line numbers of the `if <probe result>: pytest.skip(...)` sites of one test file."""
    tree = ast.parse(src)
    probes = set(_PROBES)
    grown = True
    while grown:                                         # a module-level helper that calls a probe is a probe
        grown = False
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name not in probes and _calls_any(n, probes):
                probes.add(n.name)
                grown = True
    sites = []
    for fnode in ast.walk(tree):
        if not isinstance(fnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        bound = set()
        for n in ast.walk(fnode):
            if isinstance(n, ast.Assign) and _calls_any(n.value, probes):
                bound |= {x.id for t in n.targets for x in ast.walk(t) if isinstance(x, ast.Name)}
        for n in ast.walk(fnode):
            if isinstance(n, ast.If) and _skips(n.body) and (
                    _calls_any(n.test, probes) or {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)} & bound):
                sites.append(n.lineno)
    return sorted(set(sites))


def _assigned(vsh_text):
    """{name: [right-hand side, ...]} of verify.sh's shell assignments."""
    out = {}
    for m in re.finditer(r"^\s*(?:export\s+|local\s+)?([A-Za-z_]\w*)=(.*)$", vsh_text, re.M):
        out.setdefault(m.group(1), []).append(m.group(2))
    return out


def _names_in(rhs):
    """The variables a right-hand side reads: `$x` / `${x...}`, and the bare names of bash arithmetic `$(( ... ))`."""
    refs = set(re.findall(r"\$\{?([A-Za-z_]\w*)", rhs))
    for arith in re.findall(r"\$\(\((.*?)\)\)", rhs):
        refs |= set(re.findall(r"\b[A-Za-z_]\w*\b", arith))
    return refs


_CMD_SUB = re.compile(r"\$\((?!\()|`")                    # a command substitution; `$(( ... ))` is arithmetic, not one


def _probe_vars(vsh_text):
    """N385 (b): the variables PYTEST_MAX_SKIP is computed from (not itself) that rest on a command -- assigned with a
    command substitution, or computed from such a variable. [] when the ceiling is a fixed number, a self-default, or
    a command whose results no variable holds."""
    asg = _assigned(vsh_text)

    def from_cmd(v, seen):
        if v in seen:
            return False
        return any(_CMD_SUB.search(rhs) or any(from_cmd(w, seen | {v}) for w in _names_in(rhs) - {v})
                   for rhs in asg.get(v, []))
    out = set()
    for rhs in asg.get("PYTEST_MAX_SKIP", []):
        out |= {v for v in _names_in(rhs) - {"PYTEST_MAX_SKIP"} if from_cmd(v, set())}
    return sorted(out)


_PATH_TOKEN = re.compile(r"(?<![\w$])/[\w.+-]+(?:/[\w.+-]+)+")


def _paths_of(v, asg, seen=()):
    """The file paths `v`'s computation names (e.g. the probe's output file), through the variables it reads."""
    out = set()
    for rhs in asg.get(v, []):
        out |= set(_PATH_TOKEN.findall(rhs))
        for w in _names_in(rhs) - {v} - set(seen):
            out |= _paths_of(w, asg, tuple(seen) + (v,))
    return out


def _gate_line(vsh_text, probes):
    """LB35: the `ck` line that prints the ceiling `${PYTEST_MAX_SKIP}` and every probe result in `probes` -- each
    directly, through a variable printed there whose assignment reads it, or through a command substitution on the
    line that reads the file the probe's computation reads (verify.sh's own `$(tail -1 /tmp/v_x.txt)` style) -- or
    None."""
    asg = _assigned(vsh_text)
    for ln in re.findall(r"^\s*ck\b.*$", vsh_text, re.M):
        printed = set(re.findall(r"\$\{?([A-Za-z_]\w*)", ln))
        via = {w for p in printed - {"PYTEST_MAX_SKIP"} for rhs in asg.get(p, []) for w in _names_in(rhs)}
        shown = set(_PATH_TOKEN.findall(" ".join(re.findall(r"\$\((?!\()([^)]*)\)", ln))))
        if "PYTEST_MAX_SKIP" in printed and all(v in printed or v in via or _paths_of(v, asg) & shown
                                                for v in probes):
            return ln.strip()
    return None


_PY_SCRIPT = re.compile(r"([\w$.{}/-]*\.py)\b")


def _probe_scripts(vsh_text, pv):
    """M6 (RED_waveB_recheck, the fixer's tightening of branch (b), wave B part 3): every probe result rests on a script
    that runs the nodes' OWN probes -- the variable is computed, directly or from a file verify.sh writes, by a command
    that runs a .py file whose source calls a probe of `_PROBES`. `_hs=$(nproc)` is a command and printed on the gate
    line, but it probes nothing the skips depend on. Returns the variables of `pv` that do NOT rest on such a script."""
    asg = _assigned(vsh_text)
    bad = []
    for v in pv:
        texts = list(asg.get(v, []))
        for path in _paths_of(v, asg):
            texts += [ln for ln in vsh_text.splitlines() if re.search(r">\s*%s(?![\w.])" % re.escape(path), ln)]
        found = False
        for t in texts:
            for sc in _PY_SCRIPT.findall(t):
                rel = re.sub(r"^\$\{?VDIR\}?/", "", sc)
                cand = os.path.join(VERIFICATION, rel) if rel != sc else os.path.join(_WS, sc)
                if os.path.isfile(cand):
                    with open(cand, encoding="utf-8") as fh:
                        if _calls_any(ast.parse(fh.read()), _PROBES):
                            found = True
        if not found:
            bad.append(v)
    return bad


def _ceiling_computed_and_reported(vsh_text):
    """N385's branch (b) under LB35: the probe results the ceiling is computed from, when the gate line prints the
    ceiling and all of them; [] otherwise."""
    pv = _probe_vars(vsh_text)
    return pv if pv and _gate_line(vsh_text, pv) else []


# RED 1.13.2 N385: green with wave B part 3's fix (the strict xfail mark removed)
def test_n385_gate_6_does_not_depend_on_the_hosts_temp_filesystem():
    vsh = _harness_file("verify.sh")
    sites = []
    for fn in sorted(os.listdir(HERE)):
        if fn.endswith(".py") and fn not in OWN:
            with open(os.path.join(HERE, fn), encoding="utf-8") as fh:
                sites += ["%s:%d" % (fn, i) for i in _probe_skip_sites(fh.read())]
    with open(vsh, encoding="utf-8") as fh:
        text = fh.read()
    assigns = re.findall(r"^\s*PYTEST_MAX_SKIP=(\S*)", text, re.M)
    _fx(assigns, "verify.sh assigns no PYTEST_MAX_SKIP")
    if not sites:
        return                                           # branch (a): no host-probe skip remains
    pv = _probe_vars(text)
    assert pv, ("host-probe skip sites %r with a ceiling PYTEST_MAX_SKIP=%s that is not computed from the probes' "
                "results (branch b) -- and the sites remain (branch a)" % (sites, assigns))
    assert _gate_line(text, pv), ("the ceiling is computed from %r, but no gate line prints the ceiling AND those probe "
                                  "results (LB35)" % pv)
    assert not _probe_scripts(text, pv), ("the ceiling's probe result(s) %r do not rest on a script that runs the "
                                          "nodes' own probes %s (M6)" % (_probe_scripts(text, pv), sorted(_PROBES)))


def test_n385_control_the_probe_readers():
    """Not a RED. The readers: today's 5 sites are found by their probes (message-independent, through a helper too),
    and a fixed or self-defaulted ceiling is not 'computed'."""
    src = ("import pytest, forefst as F\n"
           "def _probe(p):\n    return F._hole_bytes_in(p, 0, 1)\n"
           "def test_a(tmp_path):\n    n = _probe(tmp_path)\n    if n is None:\n        pytest.skip('whatever')\n"
           "def test_b(tmp_path):\n    if not _fs_enforces_name_limit(tmp_path):\n        pytest.skip('x')\n"
           "def test_c():\n    n = 3\n    if n is None:\n        pytest.skip('corpus image not present')\n")
    assert _probe_skip_sites(src) == [6, 9]
    ok = _ceiling_computed_and_reported
    gate = 'ck $? "pytest (ceiling ${PYTEST_MAX_SKIP} skipped; host probes %s)"\n'
    assert not ok("PYTEST_MAX_SKIP=21\n" + gate % "")
    assert not ok("PYTEST_MAX_SKIP=${PYTEST_MAX_SKIP:-21}\n" + gate % "")
    for form in ("$((21 + _hs))", "$((21 + $_hs))", "$(( 21 + ${_hs} ))"):
        assert ok('_hs=$(python3 probe.py)\nPYTEST_MAX_SKIP=%s\n' % form + gate % "${_hs}") == ["_hs"], form
    # LB35: the gate line prints the ceiling AND the probe results
    probe = '_hs=$(python3 probe.py)\nPYTEST_MAX_SKIP=$((21 + _hs))\n'
    assert not ok(probe)                                                              # nothing printed
    assert not ok(probe + gate % "")                                                  # the ceiling alone
    assert not ok(probe + 'echo "host probes ${_hs}"\n' + gate % "")                  # results on another line
    assert not ok(probe + 'ck $? "pytest (host probes ${_hs})"\n')                    # results without the ceiling
    assert not ok('PYTEST_MAX_SKIP=$(python3 ceiling.py)\n' + gate % "")              # no result held to print
    two = '_sk=$(python3 a.py)\n_nl=$(python3 b.py)\nPYTEST_MAX_SKIP=$((21 + _sk + _nl))\n'
    assert ok(two + gate % "${_sk} ${_nl}") == ["_nl", "_sk"] and not ok(two + gate % "${_sk}")
    assert ok('_a=$(python3 p.py)\n_hs=$((_a * 1))\nPYTEST_MAX_SKIP=$((21 + _hs))\n' + gate % "${_hs}") == ["_hs"]
    assert ok(probe + '_hd="seek=${_hs}"\n' + gate % "${_hd}") == ["_hs"]             # printed through a variable
    # verify.sh's own style: the probe writes a file, the count is read from it, the gate line prints the file
    pf = '$PY host_probe.py > /tmp/v_hostprobe.txt 2>&1\n_hs=$(grep -c SKIP /tmp/v_hostprobe.txt)\n' \
         'PYTEST_MAX_SKIP=$((21 + _hs))\n'
    assert ok(pf + gate % "$(tail -2 /tmp/v_hostprobe.txt)") == ["_hs"]
    assert not ok(pf + gate % "$(tail -1 /tmp/v_pytest.txt)")                          # another file: not the results
    # not a command: a number, or bash arithmetic `$(( ))` (which the old `\$\(` reading took for one)
    assert not ok('_hs=5\nPYTEST_MAX_SKIP=$((21 + _hs))\n' + gate % "${_hs}")
    assert not ok('_hs=$((5))\nPYTEST_MAX_SKIP=$((21 + _hs))\n' + gate % "${_hs}")
    # M6 (the fixer's tightening): a command that probes nothing the skips depend on is not a probe result
    assert _probe_scripts('_hs=$(nproc)\nPYTEST_MAX_SKIP=$((21 + _hs))\n' + gate % "${_hs}", ["_hs"]) == ["_hs"]
    assert _probe_scripts('$PY $VDIR/no_such_probe.py > /tmp/v_hp.txt\n_hs=$(tail -1 /tmp/v_hp.txt)\n', ["_hs"]) == \
        ["_hs"]
    with open(_harness_file("verify.sh"), encoding="utf-8") as fh:
        vtext = fh.read()
    _keep(_gate_line(vtext, []) and "PYTEST_MAX_SKIP" in _gate_line(vtext, []),
          "verify.sh's gate 6 line no longer prints the ceiling ${PYTEST_MAX_SKIP}")
    found = {}
    for fn in ("test_extraction_safety.py", "test_image_holes_and_page_refs.py"):
        with open(os.path.join(HERE, fn), encoding="utf-8") as fh:
            found[fn] = _probe_skip_sites(fh.read())
    _keep(sum(len(v) for v in found.values()) >= 5, "the probe sites found today: %r" % found)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N399 (b) and E-5 -- golden_gen.sh's form list and its hashes, measured with a fake tool
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N399 (b): G3 moved `integrity --json` machine values (severity 'HOLE', pages_invalid_sig, coverage_complete) with no
# golden row; wave B adds the form. E-5: golden_gen.sh captures stdout and stderr together (`2>&1`), so a stderr line can
# land inside a JSON token; decided: the two streams hashed separately, ADDED beside the merged hash, which stays the
# chain key (WAVEB_PREP harness item). LB21 + LB23 (critic D1, T1): in a SIDE FILE -- when GOLDEN_STREAMS_OUT names a
# path, every emitter that captures both streams (emit, details, the two file emitters, `deleted --full`, the carve)
# appends `<image>|<command>|stdout=<sha256>|stderr=<sha256>` to it under the carve lock's flock pattern, and the parent
# sorts it at the end; the golden's 4-field rows are unchanged, and with the variable unset nothing changes. LB34:
# `extract` too -- its golden row hashes stdout only (golden_gen.sh:174-179, stderr to /dev/null) and stays so; its side
# line carries that stdout hash (the row's content hash) and the stderr hash, so its statements (hole warnings) are no
# longer invisible.
# The fake tool writes "<OUT> <args>" to stdout, flushes, then "<ERR> <args>" to stderr, so the merged text is known;
# three variants (OUT/ERR = X/E1, X/E2, Y/E1) tell a stdout hash (equal for X/E1 and X/E2, different for Y/E1) from a
# stderr hash (the other way round) whatever its normalisation.

_FAKE = '''import os, sys
VERSION = "9.9.9"
o, e = os.environ.get("FAKE_OUT", "OUT"), os.environ.get("FAKE_ERR", "ERR")
if os.environ.get("FAKE_LOG"):                      # M5: one line per invocation, so a test can count the runs
    with open(os.environ["FAKE_LOG"], "a") as _fh:
        _fh.write(" ".join(sys.argv[2:]) + "\\n")
sys.stdout.write("%s %s\\n" % (o, " ".join(sys.argv[2:])))
sys.stdout.flush()
sys.stderr.write("%s %s\\n" % (e, " ".join(sys.argv[2:])))
sys.stderr.flush()
'''
_FAKE_IMG = "fake/none.raw"
# An image key golden_gen.sh lists for an `extract` target (extract_targets.tsv) AND both E-4 rows (e4_carve_images.txt):
# with the fake tool its `--one` run reaches every emitter -- emit, extract, details, the two file emitters, `deleted
# --full`, the carve. The fake tool never opens it; it is a row key only.
_ALL_EMITTERS_IMG = "analysis/rawdisk/disks/step1/win10refsmini.raw"
_GG = {}


def _fake_tools(tmp_path_factory):
    gg = _harness_file("golden_gen.sh")
    with open(gg, encoding="utf-8") as fh:
        m = re.search(r"^ROOT=(\S+)$", fh.read(), re.M)
    if not m or not os.path.isdir(m.group(1)):
        pytest.skip("golden_gen.sh's ROOT is not on this host")
    d = tmp_path_factory.mktemp("golden_fake_tools")
    for name in ("forefst.py", "refsanalysis.py"):
        (d / name).write_text(_FAKE)
    return gg, d


def _rows_of(stdout, imgs):
    rows = {}
    for ln in stdout.splitlines():
        p = ln.split("|")
        _fx(len(p) >= 4 and p[0] in imgs and p[2].startswith("rc="), "an unexpected row: %r" % ln)
        rows[(p[0], p[1])] = p
    return rows


def _golden_one(tmp_path_factory, out, err, img=_FAKE_IMG, streams=False, log=None):
    """{"<tool> <cmd>": row} of `golden_gen.sh LST <fake tool dir> --one IMG` (cached per variant), and, with
    `streams`, the lines the run appended to the file GOLDEN_STREAMS_OUT names (None when it wrote no such file).
    `log`: a file the fake tool appends one line per invocation to (M5)."""
    key = (out, err, img, streams, log)
    if key in _GG:
        return _GG[key]
    gg, d = _fake_tools(tmp_path_factory)
    env = dict(os.environ, FAKE_OUT=out, FAKE_ERR=err)
    env.pop("GOLDEN_STREAMS_OUT", None)
    env.pop("FAKE_LOG", None)
    if log:
        env["FAKE_LOG"] = log
    sp = None
    if streams:
        sp = str(tmp_path_factory.mktemp("golden_streams") / "streams.txt")       # not created: the run appends
        env["GOLDEN_STREAMS_OUT"] = sp
    r = subprocess.run(["bash", gg, os.devnull, str(d), "--one", img], capture_output=True, text=True, env=env,
                       timeout=300)
    _fx(r.returncode == 0 and r.stdout.strip(), "golden_gen.sh --one failed (rc %d):\n%s" % (r.returncode, r.stderr[-2000:]))
    rows = {c: p for (_i, c), p in _rows_of(r.stdout, {img}).items()}
    lines = None
    if sp and os.path.isfile(sp):
        with open(sp, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    _GG[key] = (rows, lines) if streams else rows
    return _GG[key]


def _merged(out, err, cmd):
    """The merged text golden_gen.sh hashes for a generic row: `$( ... 2>&1)` drops the trailing newline."""
    args = cmd.split(" ", 1)[1]
    return ("%s %s\n%s %s\n" % (out, args, err, args)).rstrip("\n")


def _generic(rows):
    """The rows whose 4th field hashes the merged text of the command they name (not the file emitters, the carve,
    `extract` -- stdout only -- or `details`, whose row names a target, not its arguments)."""
    return {c: p for c, p in rows.items()
            if not re.search(r"export resident-all|snapshots --extract|export deleted --carve| extract <target:"
                             r"| details (?:--\S+ )*<target:", c)}          # N635: `details --json <target:..>` too


def test_e5_control_the_fake_run_reproduces_each_generic_rows_merged_hash(tmp_path_factory):
    """Not a RED (the instrument's check, and the chain key E-5 keeps). One row per FE_CMDS/RA_CMDS form and the two file
    emitters (41 today); each generic row's merged hash is SHA-256 of the merged text the fake wrote -- today and after
    E-5, which adds hashes beside it."""
    rows = _golden_one(tmp_path_factory, "X", "E1")
    gen = _generic(rows)
    _fx(len(rows) >= 41 and len(gen) >= 39, "%d rows, %d generic" % (len(rows), len(gen)))
    bad = [c for c, p in gen.items() if p[3] != hashlib.sha256(_merged("X", "E1", c).encode()).hexdigest()]
    assert not bad, "rows whose 4th field is not the merged hash: %r" % bad


# RED 1.13.2 N399: green with wave B part 3's fix (the strict xfail mark removed)
def test_n399b_golden_gen_fingerprints_integrity_json(tmp_path_factory):
    rows = _golden_one(tmp_path_factory, "X", "E1")
    _keep("forefst.py integrity" in rows and "forefst.py integrity --checksums" in rows, "the integrity forms: %r" % [
        c for c in rows if "integrity" in c])
    assert "forefst.py integrity --json" in rows, "forms with integrity: %r" % [c for c in rows if "integrity" in c]


_STREAM_LINE = re.compile(r"^([^|]+)\|([^|]+)\|stdout=([0-9a-f]{64})\|stderr=([0-9a-f]{64})$")   # LB23's line
_EXTRACT_ROW = re.compile(r" extract <target:")          # LB34: a side line too; its stdout hash = the row's hash
_EMITTER_KINDS = re.compile(r" extract <target:| details <target:|export resident-all|snapshots --extract|deleted --full"
                            r"|export deleted --carve")


def _stream_index(lines, imgs):
    """({(image, command): (stdout hash, stderr hash)}, the lines not in LB23's form or given twice)."""
    idx, bad = {}, []
    for ln in lines or []:
        m = _STREAM_LINE.match(ln)
        if not m or m.group(1) not in imgs or (m.group(1), m.group(2)) in idx:
            bad.append(ln)
            continue
        idx[(m.group(1), m.group(2))] = (m.group(3), m.group(4))
    return idx, bad


# RED 1.13.2 E-5: green with wave B part 3's fix (the strict xfail mark removed)
def test_e5_lb23_golden_streams_out_holds_a_stdout_and_a_stderr_hash_per_row(tmp_path_factory):
    img = _ALL_EMITTERS_IMG
    a, la = _golden_one(tmp_path_factory, "X", "E1", img, streams=True)
    b, lb = _golden_one(tmp_path_factory, "X", "E2", img, streams=True)        # stderr differs
    c, lc = _golden_one(tmp_path_factory, "Y", "E1", img, streams=True)        # stdout differs
    plain = _golden_one(tmp_path_factory, "X", "E1", img)                      # GOLDEN_STREAMS_OUT unset
    _fx(set(a) == set(b) == set(c) == set(plain), "the four runs emitted different forms")
    _fx(len({_EMITTER_KINDS.search(k).group(0) for k in a if _EMITTER_KINDS.search(k)}) == 6,
        "the fake run of %s did not reach every emitter kind: %r" % (img, sorted(a)))
    xrows = sorted(k for k in a if _EXTRACT_ROW.search(k))
    _keep(all(len(p) == 4 for rows in (a, b, c, plain) for p in rows.values()),
          "LB21: the golden's rows keep their 4 fields (the side file carries the stream hashes)")
    _keep(a == plain, "LB21/LB23: setting GOLDEN_STREAMS_OUT changes no golden row")
    # M5 (RED_waveB_recheck; the fixer's tightening, wave B part 3): "when it is unset nothing changes" asserted
    # directly -- with the variable unset every row's command runs exactly once (no side run, nothing written for it)
    flog = str(tmp_path_factory.mktemp("golden_fake_log") / "invocations.txt")
    plain_logged = _golden_one(tmp_path_factory, "X", "E1", img, log=flog)
    with open(flog, encoding="utf-8") as fh:
        nruns = len(fh.read().splitlines())
    _keep(plain_logged == plain and nruns == len(plain),
          "LB23: with GOLDEN_STREAMS_OUT unset the run must be today's: %d invocation(s) for %d row(s)"
          % (nruns, len(plain)))
    _keep(all(p[3] == hashlib.sha256(_merged("X", "E1", k).encode()).hexdigest() for k, p in _generic(a).items()),
          "the merged hash stays the 4th field, the chain key")
    # LB34: "the golden row stays as it is" -- extract's row still hashes stdout alone (equal when only stderr differs)
    _keep(all(a[k][3] == b[k][3] != c[k][3] for k in xrows),
          "LB34: the extract rows' hash no longer follows stdout alone: %r" % [(k, a[k][3][:8], b[k][3][:8], c[k][3][:8])
                                                                              for k in xrows][:2])
    assert None not in (la, lb, lc), "GOLDEN_STREAMS_OUT=<file>: golden_gen.sh wrote no side file (LB23)"
    (ia, bad_a), (ib, bad_b), (ic, bad_c) = (_stream_index(x, {img}) for x in (la, lb, lc))
    bad = bad_a + bad_b + bad_c
    assert not bad, "side-file lines not in LB23's form `<image>|<command>|stdout=<sha256>|stderr=<sha256>`, or given " \
                    "twice: %r" % bad[:3]
    want = {(img, k) for k in a}                         # every row, `extract` included (LB34)
    missing = sorted(k for _i, k in want - set(ia))
    assert not missing, "%d of %d golden rows have no side line (LB23; LB34: extract too): %r" % (
        len(missing), len(want), missing[:4])
    extra = sorted(k for _i, k in set(ia) - want)
    assert not extra, "side lines for commands with no golden row: %r" % extra[:4]
    wrong = []
    for k in sorted(want):
        (oa, ea), (ob, eb), (oc, ec) = ia[k], ib[k], ic[k]
        if not (oa == ob and oa != oc):
            wrong.append((k[1], "stdout"))
        if not (ea == ec and ea != eb):
            wrong.append((k[1], "stderr"))
    assert not wrong, "side hashes that do not follow their own stream (and only it): %r" % wrong[:4]
    # LB34: extract's side stdout hash IS the row's content hash (the same bytes, hashed from the same file form)
    xwrong = [(k, run) for k in xrows for run, rows, idx in (("X/E1", a, ia), ("X/E2", b, ib), ("Y/E1", c, ic))
              if idx[(img, k)][0] != rows[k][3]]
    assert not xwrong, "extract side lines whose stdout hash is not the row's content hash (LB34): %r" % xwrong[:4]


# RED 1.13.2 E-5: green with wave B part 3's fix (the strict xfail mark removed)
def test_e5_lb23_the_parent_run_sorts_the_streams_file(tmp_path_factory):
    gg, d = _fake_tools(tmp_path_factory)
    w = tmp_path_factory.mktemp("golden_parent")
    imgs = [_FAKE_IMG, _ALL_EMITTERS_IMG]
    (w / "two.lst").write_text("\n".join(imgs) + "\n")
    sp = str(w / "streams.txt")
    env = dict(os.environ, FAKE_OUT="X", FAKE_ERR="E1", GOLDEN_JOBS="2", GOLDEN_MIN_FREE_MB="0",
               GOLDEN_STREAMS_OUT=sp)
    r = subprocess.run(["bash", gg, str(w / "two.lst"), str(d)], capture_output=True, text=True, env=env, timeout=600)
    _fx(r.returncode == 0 and r.stdout.strip(), "golden_gen.sh (parent, 2 images, 2 jobs) failed (rc %d):\n%s"
        % (r.returncode, r.stderr[-2000:]))
    rows = _rows_of(r.stdout, set(imgs))
    _fx({i for i, _c in rows} == set(imgs), "the parent run's rows cover %r" % sorted({i for i, _c in rows}))
    _keep(all(len(p) == 4 for p in rows.values()), "LB21: the golden's rows keep their 4 fields")
    assert os.path.isfile(sp), "GOLDEN_STREAMS_OUT=<file>: the parent run wrote no side file (LB23)"
    with open(sp, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    srt = subprocess.run(["sort"], input="".join(ln + "\n" for ln in lines), capture_output=True, text=True,
                         env=env).stdout.splitlines()
    assert lines == srt, "the side file is not sorted (LB23: the parent sorts it at the end)"
    idx, bad = _stream_index(lines, set(imgs))
    want = set(rows)                                     # one line per row, `extract` included (LB34)
    assert not bad and set(idx) == want, ("side file: %d lines for %d rows of the two images (%d malformed or twice; "
                                          "one line per row, extract included, appends serialised)"
                                          % (len(lines), len(want), len(bad)))
