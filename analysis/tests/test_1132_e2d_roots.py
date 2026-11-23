"""E2d (1.14.0): N432 + N501 -- the one root resolution of the instruments, and the gate check that read no image.

  N432-1  no live instrument puts an absolute path on sys.path (the live set of test_1132_red_c1_instruments, the
          scanner of test_1132_red_waveb_mlog's LB13 node).
  N432-2  no live instrument names a `/workspace/refs` path outside a docstring: every tree and image path comes from
          `analysis/tools/refs_root.py`.
  N432-3  refs_root: a path through a mirror's links resolves to the mirror's root (abspath, not realpath);
          FOREFST_REPO names the tool tree (the suite's convention) and only the tool tree; `disks()` refuses an empty
          image root -- with the reason -- instead of handing a glob nothing to measure.
  N432-C  control: N432-2's scanner emits its counterexample (a planted literal), and skips a docstring.
  N501-1  `verify.sh` check 5 passes only when verify_claim exits 0 and its line says every assertion passed: "0/29
          assertions PASS" (no image found) passed the gate.
"""
import ast
import os
import re
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_c1_instruments as C1                # noqa: E402  (live_instruments, WS)
import test_1132_red_waveb_mlog as WB                    # noqa: E402  (_sys_path_literals)

WS = C1.WS
REFS_ROOT = os.path.join(WS, "analysis", "tools", "refs_root.py")
VERIFY_SH = os.path.join(WS, "analysis", "verification", "verify.sh")
PREFIX = "/workspace/refs"


def hard_coded_paths(src):
    """(line, value) of every string constant naming a /workspace/refs path, docstrings left out."""
    tree = ast.parse(src)
    doc = set()
    for n in ast.walk(tree):
        body = getattr(n, "body", None)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body \
                and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            doc.add(id(body[0].value))
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith(PREFIX)
            and id(n) not in doc]


# The driver-analysis programme's studies (`analyze_brc*.py`): they read that workspace's own reader and images
# (/workspace/driversanalysis), not this project's tools -- another tree by design, listed by name.
OTHER_WORKSPACE = re.compile(r"(?:^|/)analysis/tools/analysis_scripts/analyze_brc[\w]*\.py$")


def _scan(fn):
    found = {}
    for p in C1.live_instruments():
        if OTHER_WORKSPACE.search(p):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                hits = fn(fh.read())
        except SyntaxError:
            continue                                     # not Python 3 (an archived Python 2 probe): not run
        if hits:
            found[os.path.relpath(p, WS)] = hits[:3]
    return found


def test_n432_no_live_instrument_puts_an_absolute_path_on_sys_path():
    found = _scan(WB._sys_path_literals)
    assert not found, "instruments that put a hard-coded tree on sys.path (N432): %s" % "; ".join(
        "%s %r" % kv for kv in sorted(found.items()))


def test_n432_no_live_instrument_names_a_workspace_path():
    found = _scan(hard_coded_paths)
    assert not found, "instruments that name a hard-coded workspace path (N432; refs_root resolves them): %s" % \
        "; ".join("%s %r" % kv for kv in sorted(found.items()))


def test_n432_control_the_scanner_emits_its_counterexample():
    planted = ('"""Doc naming /workspace/refs/forefstdev."""\nimport glob\n'
               'IMGS = glob.glob("/workspace/refs/analysis/rawdisk/disks/**/*.raw")\n'
               'def f():\n    """/workspace/refs in a docstring"""\n    return "/workspace/refs/forefst"\n')
    assert hard_coded_paths(planted) == [(3, "/workspace/refs/analysis/rawdisk/disks/**/*.raw"),
                                         (6, "/workspace/refs/forefst")]


def _refs_root():
    import importlib.util
    spec = importlib.util.spec_from_file_location("refs_root_t", REFS_ROOT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_n432_refs_root_resolves_the_tree_it_is_run_from(tmp_path, monkeypatch):
    assert os.path.isfile(REFS_ROOT), REFS_ROOT
    RR = _refs_root()
    real = tmp_path / "real"
    for d in ("forefstdev", "analysis/tools/analysis_scripts", "analysis/rawdisk/disks"):
        (real / d).mkdir(parents=True)
    (real / "analysis/tools/analysis_scripts/probe.py").write_text("")
    mirror = tmp_path / "mirror"
    (mirror / "analysis/rawdisk/disks").mkdir(parents=True)
    (mirror / "forefstdev").mkdir()
    os.symlink(real / "analysis" / "tools", mirror / "analysis" / "tools")
    (mirror / "analysis/rawdisk/disks/a.raw").write_text("")
    monkeypatch.delenv("FOREFST_REPO", raising=False)
    via_mirror = str(mirror / "analysis/tools/analysis_scripts/probe.py")
    assert RR.root(via_mirror) == str(mirror)
    assert RR.tool_tree(via_mirror) == str(mirror / "forefstdev")
    assert RR.tool_tree(via_mirror, "forefst.py", published=True) == str(mirror / "forefst" / "forefst.py")
    assert RR.disks(via_mirror, "**", "*.raw") == str(mirror / "analysis/rawdisk/disks/**/*.raw")
    assert RR.path(via_mirror, "forefstdev", "docs") == str(mirror / "forefstdev" / "docs")
    monkeypatch.setenv("FOREFST_REPO", str(tmp_path / "snap"))
    assert RR.tool_tree(via_mirror, "forefst.py") == str(tmp_path / "snap" / "forefst.py")
    assert RR.path(via_mirror, "forefstdev", "docs") == str(mirror / "forefstdev" / "docs")   # docs: not the snapshot
    # the real tree's image root is empty: refused with the reason, nothing returned
    direct = str(real / "analysis/tools/analysis_scripts/probe.py")
    with pytest.raises(SystemExit) as ei:
        RR.disks(direct, "**", "*.raw")
    assert "no image under" in str(ei.value) and "mirror" in str(ei.value)


def test_n501_gate_check_5_requires_every_assertion_and_the_exit_status(tmp_path):
    """Check 5's lines run against three verify_claim outputs: all PASS (passes), 0/29 with no FAIL (fails), all PASS
    but exit 1 (fails)."""
    with open(VERIFY_SH, encoding="utf-8") as fh:
        sh = fh.read()
    m = re.search(r'(?ms)^echo "== 5\. structural regression assertions =="\n(.*?)^echo "== ', sh)
    assert m, "verify.sh has no check 5"
    block = m.group(1)
    assert "verify_claim.py --regress" in block

    def run(out, rc):
        fake = tmp_path / "fake_vc.sh"
        fake.write_text("#!/bin/bash\ncat <<'X'\n%s\nX\nexit %d\n" % (out, rc))
        fake.chmod(0o755)
        script = ("ck(){ [ \"$1\" -eq 0 ] && echo GATE_PASS || echo GATE_FAIL; }\nPY=bash\n"
                  + block.replace("analysis/tools/analysis_scripts/verify_claim.py", str(fake))
                  .replace("/tmp/v_regress.txt", str(tmp_path / "v_regress.txt")))
        return subprocess.run(["bash", "-c", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True, cwd=str(tmp_path)).stdout
    allpass = "[PASS] a\n" * 3 + "=" * 72 + "\n3/3 assertions PASS"
    nothing = "[n/a] a\n" * 3 + "=" * 72 + "\n0/3 assertions PASS"
    assert "GATE_PASS" in run(allpass, 0)
    assert "GATE_FAIL" in run(nothing, 1), "0/3 assertions PASS passed check 5"
    assert "GATE_FAIL" in run(nothing, 0), "0/3 assertions PASS passed check 5 when the exit status says 0"
    assert "GATE_FAIL" in run(allpass, 1), "check 5 ignored verify_claim's exit status"
