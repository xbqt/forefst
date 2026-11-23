"""1.13.2 RED cases, group b_items: plan rows B1, B3, B4 (FUTURE retired) and B11.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 2 B (rows B1, B3, B4, B11), section 5 "RED first", decision 19
(the maintainer's bar: every RED fails on 1.13.1 BECAUSE of the defect, not because of an artefact, and is
independently confirmed). B1 follows F1 (`F1_CHECKPOINT_TIE_READING.md`: on a +0x60 tie the driver keeps SLOT 0,
the checkpoint listed first in the superblock, whatever its LCN). Report, with the observed or expected failure of
every node: `analysis/reports/v1.13.2/red/RED_b_items.md`.

What each RED asserts (the row's Acceptance column)
---------------------------------------------------
B1  `summary`/`fastsummary` show the clock and hash of the checkpoint IN USE (the valid copy; on a valid tie the
    driver's slot 0; ranked by +0x60, not +0x10), every `CHKP` line carries its own copy's hash, `deleted`'s
    checkpoint comparison does not compare a copy with itself or with a failed copy without saying so, the natural
    tie on win11refs2tmillionsofactions names one copy, and `docs/structures/chkp.md` states the slot-0 tie rule.
B3  The volume length comes from the VBR (total_sectors x bytes_per_sector), not the image length: the orphan-page
    scans stop at the volume end, capacity is the volume's, the image tail is reported separately, a truncated image
    is reported as truncated, and refsanalysis `allocators` counts the volume.
B4  FUTURE is retired: no FUTURE flag, no tier reached through it, no `FUTURE` / "last metadata write" in either tool
    or the docs outside retired-claim text, no Known-issues item, and 7j retired-claim rows that fire 0 times.
B11 A second `export metadata` bundle into a directory that holds one keeps the first seal and is written to
    `<dir>_2` with its own seal (decision 22's O2: not refused, never overwriting, the path printed); every bulk
    exporter records a forced rename in a source -> written path index (ObjectRef, SHA-256, rename reason).

Volumes
-------
* ``[synthetic]`` -- the 1 MiB ReFS 3.14 volume of `test_1132_red_a_bootstrap.py` (imported, not copied: one
  builder, one set of pins), written into ``tmp_path``. No corpus image is read.
* ``[image...]`` -- a hole-preserving scratch copy of the battery's base A (`win11refsmini.raw`), made under
  ``$FOREFST_RED_SCRATCH`` (default: ``forefst_red_scratch`` in the system temp directory) and deleted by exact path when the test
  ends; or a corpus image opened READ-ONLY (the natural tie, the bulk exporters, the second metadata source).
  Skipped when the image is absent. ``pytest -k "not image"`` runs the synthetic and unit half only.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; the fix commit removes the mark and an XPASS fails
  the run. Only a plain ``assert`` states the acceptance.
* Everything else raises ``RedFixtureError`` or ``KeptPropertyBroken`` (NOT AssertionErrors): a base that is not
  what the case needs (checked before any damage), a damage op that did not land, a crash (traceback) or timeout,
  or a property 1.13.1 already has and the fix must keep.
* Expected values are computed by this module from bytes it reads itself (hashes of each checkpoint copy, the VBR's
  total_sectors, Windows' own SHA-256 of a recycled file), never taken from the tool under test.
* Controls (not xfail) pass on 1.13.1 and must keep passing; several exist to stop a RED from being passed by a
  blanket message (a failure word printed on every run, a tail or truncation line printed for every image).
* Nothing here asserts a checkpoint HASH LENGTH (F11 is open): a copy's hash is accepted over one cluster or over
  max(16 KiB, cluster) bytes, and never over the other copy's bytes.
"""
import contextlib
import hashlib
import importlib.util
import inspect
import io
import itertools
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from collections import Counter

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jget, jint, jdoc# noqa: E402  (K21 readers)
from conftest import make_msb_page                       # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (synthetic volume, carve, Vol, make_tie)

FOREFST, REFSANALYSIS = AB.FOREFST, AB.REFSANALYSIS
TIMEOUT = 1800                                           # the natural-tie image is 2 TiB logical
SCRATCH = AB.SCRATCH
CS = AB.CS
RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
_FAIL = AB._FAIL


def _red(item, why):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason="RED 1.13.2 %s: %s" % (item, why))


# ─── running the tools ────────────────────────────────────────────────────────────────────────────────────────

def _run(tool, image, *args, cli=(), cwd=None):
    """(rc, stdout, stderr). A traceback or a timeout is a fixture error, never the defect under test."""
    cmd = [sys.executable, "-B", tool, image] + list(args) + list(cli)
    try:
        r = UW.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


def _vrun(v, tool, *args):
    return _run(tool, v.path, *args, cli=v.geo.cli, cwd=os.path.dirname(v.path))


def _json_of(stdout, what):
    i = stdout.find("{")
    _fx(i >= 0, "%s printed no JSON object" % what)
    try:
        return jdoc(json.JSONDecoder().raw_decode(stdout[i:])[0], F._SUMMARY_KEYS)   # K21: internal names
    except ValueError as e:
        raise RedFixtureError("%s: unparsable JSON (%s)" % (what, e))


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ctx(rc, out, err="", ops=()):
    return "\nops: %s | rc=%s\n%s\n--- stderr ---\n%s" % ("; ".join(ops) or "none", rc, out[-5000:], err[-2500:])


@contextlib.contextmanager
def _scratch(tag):
    """A private directory under SCRATCH, removed by its exact path afterwards."""
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="b_items_%s_" % tag, dir=SCRATCH)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _image_or_skip(name):
    p = _corpus_image(name)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return p


@contextlib.contextmanager
def _image_vol():
    """A damage-ready carve of the battery's base A (win11refsmini.raw), pinned before any op."""
    base = _image_or_skip(AB.BASE_IMAGE)
    with _scratch("vol") as d:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file; refusing a dense 2 GiB copy" % d)
        p = os.path.join(d, "target.raw")
        AB._carve(base, p)
        alloc = os.stat(p).st_blocks * 512
        _fx(alloc < AB.MAX_SCRATCH_ALLOCATED, "the scratch copy allocated %d bytes" % alloc)
        v = AB.Vol(AB.IMG, p)
        v.pin()
        yield v


def _synthetic_vol(tmp_path, sub="vol"):
    d = tmp_path / sub
    d.mkdir()
    return AB._synthetic_vol(d)


@pytest.fixture(params=["synthetic", "image"])
def cvol(request, tmp_path):
    if request.param == "synthetic":
        yield _synthetic_vol(tmp_path)
        return
    with _image_vol() as v:
        yield v


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B1 -- summary / fastsummary / deleted pick the checkpoint by +0x10 with their own tie rules
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# "lo" is the lower-LCN copy (slot 0 in the corpus order, the newer one: 64/64); "hi" the other (63/63).
# Each case returns the copy IN USE: the newest copy that passes its self-checksum, ranked by +0x60, and on a tie
# the one in slot 0 (F1). Its two clocks are equal in every case, so its clock is unambiguous.

B1_CASES = ("clean", "newest_failed", "newest_zeroed", "older_failed", "tie_slot0_lower", "tie_slot0_higher",
            "clock_divergence")


def _divergence(b):
    struct.pack_into("<Q", b, 0x10, AB.CLOCK_NEW + 1)          # +0x10 = 65 above the other copy; +0x60 stays 63


def apply_b1_case(v, case):
    """Apply one checkpoint case; return (lcn in use, its clock). Each op checks that it landed."""
    g = v.geo
    if case == "clean":
        pass
    elif case == "newest_failed":                              # battery A1_chkp_flip_newest
        AB.damage_chkp(v, g.lo)
    elif case == "newest_zeroed":                              # battery A2_chkp_zero_newest
        v.zero(v.at(g.lo), 0x4000)
    elif case == "older_failed":
        AB.damage_chkp(v, g.hi)
    elif case == "tie_slot0_lower":                            # the natural tie's shape: slot 0 = lower LCN
        AB.make_tie(v, slot0_higher=False)
    elif case == "tie_slot0_higher":                           # F1 section 5: slot 0 = higher LCN
        AB.make_tie(v, slot0_higher=True)
        return g.hi, AB.CLOCK_NEW
    elif case == "clock_divergence":                           # +0x10 and +0x60 disagree, CRC recomputed
        v.reseal(g.hi, _divergence, AB.CHKP_DESC)
        _fx(v.clocks(g.hi) == (AB.CLOCK_NEW + 1, AB.CLOCK_OLD), "divergence did not land: %r" % (v.clocks(g.hi),))
        _fx(v.verifies(g.lo) is True and v.verifies(g.hi) is True, "a copy fails after the divergence reseal")
    else:
        raise RedFixtureError("unknown case %s" % case)
    if case in ("newest_failed", "newest_zeroed"):
        return g.hi, AB.CLOCK_OLD
    return g.lo, AB.CLOCK_NEW


def _own_hashes(v, lcn):
    """The hashes that may stand for this copy: one cluster, or max(16 KiB, cluster) (F11 is open)."""
    return {_sha(v.read(v.at(lcn), n)) for n in (CS, max(0x4000, CS))}


_CHKP_TXT = re.compile(r"^\s*CHKP\s+\S+\s+LCN\s+0x([0-9a-f]+)\b", re.I)
_HASH_TXT = re.compile(r"^\s+([0-9a-f]{64})\s*$")


def _chkp_line_hashes(out):
    """[(lcn, hash or None, line)] for every `CHKP <role> LCN 0x..` line and the hash printed under it."""
    lines, res = out.splitlines(), []
    for i, ln in enumerate(lines):
        m = _CHKP_TXT.match(ln)
        if m:
            h = _HASH_TXT.match(lines[i + 1]) if i + 1 < len(lines) else None
            res.append((int(m.group(1), 16), h.group(1) if h else None, ln.strip()))
    return res


def _check_json_in_use(v, j, lcn, clock):
    """Messages for every way the JSON disagrees with the copy in use (empty = right)."""
    bad = []
    # acceptance 1.14.0 (K21, K9): the summary's output names, the LCN a hex string
    bb = jget(j, "bootstrap_backups") or {}
    used = jint(jget(bb, "checkpoint_used_lcn"))
    sha = jget(j, "chkp_sha256", F._SUMMARY_KEYS)
    if used != lcn:
        bad.append("checkpoint_used_lcn = %r, the copy in use is 0x%x" % (used, lcn))
    if sha not in _own_hashes(v, lcn):
        other = [x for x in (v.geo.lo, v.geo.hi) if x != lcn][0]
        bad.append("chkp_sha256 = %s is %s, not the copy in use 0x%x" % (
            (sha or "")[:16], "the OTHER copy's (0x%x)" % other if sha in _own_hashes(v, other) else "no copy's", lcn))
    vc = jget(j, "checkpoint_vc", F._SUMMARY_KEYS)
    if vc != clock:
        bad.append("checkpoint_vc = %r, the copy in use has clock %d" % (vc, clock))
    return bad


def _check_text_line_hashes(v, out):
    rows = _chkp_line_hashes(out)
    _fx({r[0] for r in rows} >= {v.geo.lo, v.geo.hi}, "the output does not list both checkpoint copies: %r" % rows)
    return ["`%s` is followed by %s..., which is not this copy's hash" % (ln, h[:16])
            for lcn, h, ln in rows if h is not None and h not in _own_hashes(v, lcn)]


_B1_RED_JSON = ("newest_failed", "tie_slot0_lower", "tie_slot0_higher", "clock_divergence")


@pytest.mark.parametrize("cmd", ["fastsummary", "summary"])
@pytest.mark.parametrize("case", _B1_RED_JSON)
def test_b1_checkpoint_hash_and_clock_name_the_checkpoint_in_use(cvol, case, cmd):
    lcn, clock = apply_b1_case(cvol, case)
    rc, out, err = _vrun(cvol, FOREFST, cmd, "--json", "-")
    bad = _check_json_in_use(cvol, _json_of(out, cmd), lcn, clock)
    assert not bad, "; ".join(bad) + _ctx(rc, out[:3000], err, cvol.ops)


@pytest.mark.parametrize("cmd", ["fastsummary", "summary"])
@pytest.mark.parametrize("case", ["clean", "older_failed", "newest_zeroed"])
def test_b1_control_checkpoint_hash_and_clock_already_right(cvol, case, cmd):
    """The same assertions hold on 1.13.1 where the +0x10 rank and the in-use copy agree (battery A2 included)."""
    lcn, clock = apply_b1_case(cvol, case)
    rc, out, err = _vrun(cvol, FOREFST, cmd, "--json", "-")
    bad = _check_json_in_use(cvol, _json_of(out, cmd), lcn, clock)
    assert not bad, "; ".join(bad) + _ctx(rc, out[:3000], err, cvol.ops)
    rc, out, err = _vrun(cvol, FOREFST, cmd)
    assert AB._virtual_clock(out) == clock, _ctx(rc, out, err, cvol.ops)
    assert not _check_text_line_hashes(cvol, out), _ctx(rc, out, err, cvol.ops)


@pytest.mark.parametrize("cmd", ["fastsummary", "summary"])
@pytest.mark.parametrize("case", ["tie_slot0_lower", "clock_divergence"])
def test_b1_each_chkp_line_carries_its_own_copys_hash(cvol, case, cmd):
    apply_b1_case(cvol, case)
    rc, out, err = _vrun(cvol, FOREFST, cmd)
    bad = _check_text_line_hashes(cvol, out)
    assert not bad, "; ".join(bad) + _ctx(rc, out, err, cvol.ops)


@pytest.mark.parametrize("case", ["newest_failed", "tie_slot0_higher"])
def test_b1_control_chkp_lines_already_carry_their_own_hash(cvol, case):
    apply_b1_case(cvol, case)
    rc, out, err = _vrun(cvol, FOREFST, "summary")
    assert not _check_text_line_hashes(cvol, out), _ctx(rc, out, err, cvol.ops)


@pytest.mark.parametrize("cmd", ["fastsummary", "summary"])
@pytest.mark.parametrize("case", ["newest_failed", "clock_divergence"])
def test_b1_checkpoint_section_shows_the_clock_of_the_checkpoint_in_use(cvol, case, cmd):
    _lcn, clock = apply_b1_case(cvol, case)
    rc, out, err = _vrun(cvol, FOREFST, cmd)
    assert AB._virtual_clock(out) == clock, "Virtual clock: %r, the copy in use has %d" % (
        AB._virtual_clock(out), clock) + _ctx(rc, out, err, cvol.ops)


def _cmp_section(out):
    """The body of `deleted`'s `── Checkpoint Comparison ──` section, or None when it is absent."""
    lines = out.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().startswith("──") and "Checkpoint Comparison" in ln:
            body = []
            for l2 in lines[i + 1:]:
                if l2.strip().startswith("──"):
                    break
                body.append(l2)
            return "\n".join(body)
    return None


def _cmp_vc(section, which):
    m = re.search(r"(?i)%s checkpoint:\s*VC\s*=\s*(\d+)" % which, section or "")
    return int(m.group(1)) if m else None


# wave D (N146): the differential compares the two trees by ObjectRef and words its results anew
_CMP_RESULT = re.compile(r"(?i)same files and paths in both|in the (?:previous|newer) checkpoint's tree|"
                         r"in the current tree, not|"
                         r"renamed, moved, or a hard-link name|identical in both|could not parse")


@pytest.mark.parametrize("case", ["newest_failed", "older_failed"])
def test_b1_deleted_comparison_says_when_a_copy_failed(cvol, case):
    apply_b1_case(cvol, case)
    rc, out, err = _vrun(cvol, FOREFST, "deleted")
    sec = _cmp_section(out)
    # the warning may sit in the section, or on any line that speaks of the comparison (skipped or limited)
    notes = [ln for ln in (out + "\n" + err).splitlines() if re.search(r"(?i)compar", ln) and _FAIL.search(ln)]
    assert (sec is not None and _FAIL.search(sec)) or notes, (
        "the checkpoint comparison names no failed copy:\n%s" % sec) + _ctx(rc, out, err, cvol.ops)


def test_b1_deleted_current_checkpoint_is_the_copy_in_use_when_clocks_diverge(cvol):
    _lcn, clock = apply_b1_case(cvol, "clock_divergence")
    rc, out, err = _vrun(cvol, FOREFST, "deleted")
    sec = _cmp_section(out) or ""
    cur, prev = _cmp_vc(sec, "Current"), _cmp_vc(sec, "(?:Previous|Newer)")        # N579: the other copy's label
    compared_right = cur == clock and prev is not None and prev != clock
    said = [ln for ln in (sec + "\n" + out + "\n" + err).splitlines()
            if re.search(r"(?i)compar", ln) and re.search(r"(?i)mismatch|tamper|diverg|fail", ln)]
    refused = not _CMP_RESULT.search(sec) and (re.search(r"(?i)mismatch|tamper|diverg|fail", sec) or said)
    assert compared_right or refused, ("Current VC=%r / Previous VC=%r; the copy in use has %d and the other copy "
                                       "is not it:\n%s" % (cur, prev, clock, sec)) + _ctx(rc, out, err, cvol.ops)


@pytest.mark.parametrize("case", ["clean", "tie_slot0_lower", "tie_slot0_higher"])
def test_b1_control_deleted_comparison_raises_no_alarm_when_both_copies_pass(cvol, case):
    """Stops the RED above from being passed by a warning printed on every run: two valid copies, tied or not, are
    compared quietly (a tie is a normal state)."""
    apply_b1_case(cvol, case)
    rc, out, err = _vrun(cvol, FOREFST, "deleted")
    sec = _cmp_section(out)
    assert sec is not None and _CMP_RESULT.search(sec) and not _FAIL.search(sec), _ctx(rc, out, err, cvol.ops)
    if case == "clean":
        assert (_cmp_vc(sec, "Current"), _cmp_vc(sec, "Previous")) == (AB.CLOCK_NEW, AB.CLOCK_OLD), sec


# ─── B1 on the natural tie (win11refs2tmillionsofactions, read-only) ─────────────────────────────────────────

NAT_IMAGE = "win11refs2tmillionsofactions.raw"
NAT_PS, NAT_SLOT0, NAT_SLOT1, NAT_CLOCK = 0x1000000, 0x51EB04, 0x3D702AC, 662


def _nat_pinned():
    """The natural tie, read with this module's own reads: both copies 662/662, both verify, slot 0 = 0x51EB04."""
    p = _image_or_skip(NAT_IMAGE)
    hashes = {}
    with open(p, "rb") as fh:
        fh.seek(NAT_PS)
        vbr = fh.read(512)
        _fx(vbr[3:7] == b"ReFS" and F.le32(vbr, 0x20) * F.le32(vbr, 0x24) == CS, "natural tie: VBR/cluster size")
        fh.seek(NAT_PS + 0x1E * CS)
        s = fh.read(CS)
        _fx(s[:4] == b"SUPB" and [F.le64(s, 0xC0), F.le64(s, 0xC8)] == [NAT_SLOT0, NAT_SLOT1],
            "natural tie: superblock list")
        _fx(F._verify_self_checksum(s, CS)[0] is True and s[AB.SUPB_DESC + 0x28:AB.SUPB_DESC + 0x2C]
            == AB._own_digest(s, AB.SUPB_DESC), "natural tie: superblock self-checksum")
        for lcn in (NAT_SLOT0, NAT_SLOT1):
            fh.seek(NAT_PS + lcn * CS)
            b = fh.read(0x4000)
            _fx(b[:4] == b"CHKP" and (F.le64(b, 0x10), F.le64(b, 0x60)) == (NAT_CLOCK, NAT_CLOCK),
                "natural tie: CHKP 0x%x clocks" % lcn)
            _fx(F._verify_self_checksum(b, CS)[0] is True and b[AB.CHKP_DESC + 0x28:AB.CHKP_DESC + 0x2C]
                == AB._own_digest(b, AB.CHKP_DESC), "natural tie: CHKP 0x%x self-checksum" % lcn)
            hashes[lcn] = {_sha(b[:CS]), _sha(b)}
    _fx(not (hashes[NAT_SLOT0] & hashes[NAT_SLOT1]), "natural tie: the two copies hash alike")
    return p, hashes


def test_b1_natural_tie_image_fastsummary_hash_names_summarys_active_checkpoint(tmp_path):
    p, hashes = _nat_pinned()
    rc, out, err = _run(FOREFST, p, "summary", "--json", "-", cwd=str(tmp_path))
    js = _json_of(out, "summary")
    used = jint(jget(jget(js, "bootstrap_backups") or {}, "checkpoint_used_lcn"))   # acceptance 1.14.0 (K21, K9)
    # kept: 1.13.1 already reads the volume from slot 0 = 0x51EB04, which is the driver's copy (F1)
    _keep(used == NAT_SLOT0, "summary's active checkpoint is %r, not slot 0 (0x%x)" % (used, NAT_SLOT0))
    rc, out, err = _run(FOREFST, p, "fastsummary", "--json", "-", cwd=str(tmp_path))
    h = jget(_json_of(out, "fastsummary"), "chkp_sha256", F._SUMMARY_KEYS)
    assert h in hashes[used], "fastsummary's checkpoint hash %s... is %s, not the active copy 0x%x" % (
        (h or "")[:16], "0x%x's" % NAT_SLOT1 if h in hashes[NAT_SLOT1] else "no copy's", used) + _ctx(rc, "", err)


def test_b1_natural_tie_image_each_chkp_line_carries_its_own_copys_hash(tmp_path):
    p, hashes = _nat_pinned()
    rc, out, err = _run(FOREFST, p, "summary", cwd=str(tmp_path))
    rows = _chkp_line_hashes(out)
    _fx({r[0] for r in rows} >= {NAT_SLOT0, NAT_SLOT1}, "summary does not list both copies: %r" % rows)
    bad = ["`%s` is followed by %s..." % (ln, h[:16]) for lcn, h, ln in rows if h is not None and h not in hashes[lcn]]
    assert not bad, "; ".join(bad) + _ctx(rc, out, err)


# ─── B1 documentation: the tie rule in docs/structures/chkp.md ──────────────────────────────────────────────

def _sentences(text):
    """Sentences with hard wraps joined (the retired-claims gate's rule)."""
    paras, buf = [], []
    for line in text.split("\n"):
        if not line.strip():
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(line.strip())
    if buf:
        paras.append(" ".join(buf))
    return [s.strip() for p in paras for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()]


# Only the REFUTED half of chkp.md:29 is forbidden. F1 section 1.2: the chooser DOES return a distinct value
# (GenericEqual) on a tie rather than naming a winner -- that is true and a corrected page may say it; what is false
# is that the tie is signalled / not silently resolved (every caller treats it as "keep slot 0", with no signal).
# (Critic, 2026-09-27: narrowed from a pattern that also forbade "distinct third value", "rather than naming a
# winner" and "tie sentinel", which would have failed an F1-correct page.)
_OLD_TIE_RULE = re.compile(r"(?i)tie\s+is\s+signal|not\s+silently\s+resolved")
_SLOT0 = re.compile(r"(?i)slot\s*0|first[- ]listed|listed\s+first|earlier\s+slot|first\s+slot|"
                    r"first\s+(checkpoint\s+)?(reference|entry)")


# RED 1.13.2 B1: docs/structures/chkp.md:29 says the tie is signalled, not silently resolved; F1: the caller keeps slot 0 and signals nothing -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_b1_chkp_doc_states_the_slot0_tie_rule():
    path = os.path.join(REPO, "docs", "structures", "chkp.md")
    _fx(os.path.isfile(path), "%s missing" % path)
    sents = _sentences(open(path, encoding="utf-8").read())
    old = [s for s in sents if _OLD_TIE_RULE.search(s)]
    new = [s for s in sents if re.search(r"(?i)\b(tie|tied|equal)\b", s) and _SLOT0.search(s)]
    assert not old, "chkp.md still states the refuted tie rule: %r" % [s[:160] for s in old]
    assert new, "chkp.md states no tie rule naming slot 0 (the copy listed first in the superblock)"


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B3 -- the image length is used as the volume length (K064, N113)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_PLANT_NAMED, _PLANT_SLACK = "B3TAILNAMED.txt", "B3TAILSLACK.txt"


def _dirrow_value():
    v = bytearray(0x60)
    struct.pack_into("<Q", v, 0x08, 0x1234)
    struct.pack_into("<QQQQ", v, 0x10, *([133000000000000000] * 4))
    struct.pack_into("<I", v, 0x40, 0x20)
    return bytes(v)


def _dirkey(name):
    return struct.pack("<HH", 0x30, 0) + name.encode("utf-16-le")


def planted_cluster(cs=CS, vsig=0, cl=None):
    """One MSB+ leaf cluster that neither scan can miss: a live (offset-array) name row for the --scan-pages name
    scan, and an unreferenced name row in its slack for the --full slack scan.
    C3 (N197): `vsig` is the volume signature the page carries at +0x0C, as every page of a volume does -- the orphan
    scans leave out a page that carries another (so a plant without it would be "absent" for that reason, and B3's
    RED would pass without testing the volume end).
    Wave D's close (N474): `cl`, the cluster the page is planted at -- its address tuple (+0x20) names the four 4 KiB
    clusters it fills from there, as every page of a volume does: the orphan scans read a page of this volume only at
    the address it names (so a plant without it would be "absent" for that reason)."""
    val = _dirrow_value()
    p = bytearray(make_msb_page([(_dirkey(_PLANT_NAMED), val)], cluster_size=cs))
    struct.pack_into("<I", p, 0x0C, vsig)
    sk, off = _dirkey(_PLANT_SLACK), cs - 0x200
    struct.pack_into("<I6H", p, off, 0x10 + len(sk) + len(val), 0x10, len(sk), 0, 0x10 + len(sk), len(val), 0)
    p[off + 0x10:off + 0x10 + len(sk)] = sk
    p[off + 0x10 + len(sk):off + 0x10 + len(sk) + len(val)] = val
    if cl is not None:
        struct.pack_into("<4Q", p, 0x20, *[cl + i for i in range(4)])
    return bytes(p)


def _geometry(v):
    """(volume clusters, volume end offset) from the VBR, read here: total_sectors x bytes_per_sector (E100)."""
    vbr = v.read(v.geo.ps, 512)
    ts, bps, spc = F.le64(vbr, 0x18), F.le32(vbr, 0x20), F.le32(vbr, 0x24)
    _fx(bps * spc == CS, "cluster size")
    vol_bytes = ts * bps
    _fx(vol_bytes % CS == 0, "volume length is not whole clusters")
    return vol_bytes // CS, v.geo.ps + vol_bytes


# where each volume's recipes put things (volume-relative clusters)
_B3_GEO = {
    "synthetic": dict(extend=16 * CS, plant_out=260, trunc=0xE0000, plant_in=0x30,
                      lost_ok=[(0xFD000, 0xFF000), (0xFFE00, 0x100000)]),
    "image": dict(extend=64 << 20, plant_out=0x7C100, trunc=0x7C000000, plant_in=0x3F000,
                  lost_ok=[(0x7CFFD000, 0x7D000000)]),
}


def _vsig(v):
    """The volume signature, read here from the checkpoint copy in use (+0x0C; equal to the superblock GUID's XOR on 240
    of 240 corpus copies, N414) -- not from the tool under test."""
    return F.le32(v.block(v.geo.lo), 0x0C)


def _plant(v, cl):
    off = v.geo.ps + cl * CS
    _fx(off + CS <= os.path.getsize(v.path), "plant at 0x%x is past the image end" % off)
    _fx(not any(v.read(off, CS)), "cluster 0x%x is not free (non-zero)" % cl)
    page = planted_cluster(vsig=_vsig(v), cl=cl)
    _fx(F.le32(page, 0x0C) != 0, "no volume signature for the plant")
    v.write(off, page)
    _fx(v.read(off, CS) == page, "plant did not land at 0x%x" % off)
    v.ops.append("plant MSB+ at cluster 0x%x" % cl)


def extend_and_plant(v):
    """Extend the image past the volume end (sparse) and plant one MSB+ cluster past the volume end."""
    g = _B3_GEO[v.geo.kind]
    _vcl, vol_end = _geometry(v)
    size = os.path.getsize(v.path)
    with open(v.path, "r+b") as fh:
        fh.truncate(size + g["extend"])
    v.ops.append("extend +0x%x" % g["extend"])
    _fx(v.geo.ps + g["plant_out"] * CS >= vol_end, "the plant is not past the volume end")
    _plant(v, g["plant_out"])
    return os.path.getsize(v.path) - vol_end               # the image tail, in bytes


def truncate_inside_volume(v):
    """Cut the image before the volume end. Only the backup copies may be lost (checked byte by byte)."""
    g = _B3_GEO[v.geo.kind]
    _vcl, vol_end = _geometry(v)
    cut = g["trunc"]
    _fx(v.geo.ps < cut < vol_end, "the cut is not inside the volume")
    pos = cut
    while pos < vol_end:
        n = min(1 << 20, vol_end - pos)
        b = v.read(pos, n)
        for i in range(0, len(b), 512):
            if any(b[i:i + 512]) and not any(a <= pos + i < e for a, e in g["lost_ok"]):
                raise RedFixtureError("the cut loses data at 0x%x that is not a backup copy" % (pos + i))
        pos += n
    os.truncate(v.path, cut)
    v.ops.append("truncate at 0x%x" % cut)
    return (cut - v.geo.ps) // CS                           # clusters the image still holds


def _coverage_numbers(out):
    lines = [ln for ln in out.splitlines() if re.search(r"(?i)orphan-page scan", ln) and re.search(r"\d", ln)]
    _fx(lines, "no orphan-page coverage line")
    return lines[0].strip(), [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", lines[0])]


_SCAN_MODES = {"scan-pages": ("deleted", "--scan-pages"), "full": ("deleted", "--full")}


@pytest.fixture(params=["synthetic", "image"])
def b3vol(request, tmp_path):
    if request.param == "synthetic":
        yield _synthetic_vol(tmp_path)
        return
    with _image_vol() as v:
        yield v


# RED 1.13.2 B3: the orphan-page scans run to the image end ((image size - ps) // cs, fd:12178, fd:12445) and report
# pages that are not this volume's (the strict xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("mode", sorted(_SCAN_MODES))
def test_b3_orphan_page_scans_stop_at_the_volume_end(b3vol, mode):
    vcl, _end = _geometry(b3vol)
    extend_and_plant(b3vol)
    rc, out, err = _vrun(b3vol, FOREFST, *_SCAN_MODES[mode])
    line, nums = _coverage_numbers(out)
    planted = [ln.strip() for ln in (out + err).splitlines() if "B3TAIL" in ln]
    assert vcl in nums and max(nums) <= vcl, "coverage `%s`; the volume has %d clusters" % (line, vcl) + _ctx(
        rc, out, err, b3vol.ops)
    assert not planted, "a page past the volume end was reported: %r" % planted


# RED 1.13.2 B3: on base A as it is (48 MiB of GPT tail after the volume) the orphan scan claims 520,192 clusters as
# `100% of the volume` (507,904) (the strict xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("mode", sorted(_SCAN_MODES))
def test_b3_image_as_is_orphan_scan_covers_only_the_volume(mode):
    with _image_vol() as v:
        vcl, _end = _geometry(v)
        rc, out, err = _vrun(v, FOREFST, *_SCAN_MODES[mode])
        line, nums = _coverage_numbers(out)
        assert vcl in nums and max(nums) <= vcl, "coverage `%s`; the volume has %d clusters" % (line, vcl) + _ctx(
            rc, out, err)


@pytest.mark.parametrize("mode", sorted(_SCAN_MODES))
def test_b3_control_a_page_planted_inside_the_volume_is_found(b3vol, mode):
    """The same plant, inside the volume on a free cluster, IS reported: the scans can see it, so its absence in the
    RED above can only mean the scan stopped at the volume end."""
    _plant(b3vol, _B3_GEO[b3vol.geo.kind]["plant_in"])
    rc, out, err = _vrun(b3vol, FOREFST, *_SCAN_MODES[mode])
    want = _PLANT_NAMED if mode == "scan-pages" else _PLANT_SLACK
    assert want in out, _ctx(rc, out, err, b3vol.ops)


_TAIL_WORD = re.compile(r"(?i)\b(tail|beyond|after|past|outside|trailing|extra|remainder|following)\b")


def _size_forms(n):
    forms = {str(n), "{:,}".format(n), hex(n), F._human_size(n)}
    for unit, sh in (("MiB", 20), ("KiB", 10)):
        if n >= (1 << sh):
            forms |= {"%.1f %s" % (n / float(1 << sh), unit), "%d %s" % (n >> sh, unit)}
    return forms


def _tail_lines(out, n):
    forms = [re.compile(r"(?<![0-9A-Za-z.,])%s(?![0-9A-Za-z])" % re.escape(f)) for f in _size_forms(n)]
    return [ln for ln in out.splitlines() if _TAIL_WORD.search(ln) and not re.search(r"(?i)container|allocator", ln)
            and any(f.search(ln) for f in forms)]


_DEC_BYTES = re.compile(r"(?<![0-9A-Za-z.,])(\d{1,3}(?:,\d{3})+|\d+)(?![0-9A-Za-z]|[.,][0-9])")


def _two_part_tail(out, tail):
    """Wave C Q17 (two parts: inside the partition after the volume; after the partition): two decimal byte counts, on
    one line or two, each line (or one of the two lines above it) naming the tail or the partition, adding up to `tail`.
    Added by the C2 RED critic (2026-10-23): the node's value, the tail, is unchanged; Q17's form is accepted."""
    lines, found = out.splitlines(), []
    for i, ln in enumerate(lines):
        ctx = "\n".join(lines[max(0, i - 2):i + 1])
        if re.search(r"(?i)container|allocator", ln) or not (
                _TAIL_WORD.search(ctx) or re.search(r"(?i)\bpartition\b", ctx)):
            continue
        found += [(i, int(m.replace(",", ""))) for m in _DEC_BYTES.findall(ln)]
    return any(a[1] > 0 and b[1] > 0 and a[1] + b[1] == tail for a, b in itertools.combinations(found, 2))


# RED 1.13.2 B3: summary has no line for the image tail: the space after the volume is folded into the allocator's
# `beyond the last container` figure (fd:6521-6523) or not mentioned at all (the strict xfail mark removed: fixed in
# step C2, area bounds_a)
@pytest.mark.parametrize("state", ["synthetic-extended", "image-as-is", "image-extended"])
def test_b3_summary_reports_the_tail_after_the_volume_separately(state, tmp_path):
    """On base A the tail spans the partition's end: one line with the whole tail, or Q17's two parts (wave C) adding
    up to it, are both accepted (the parts' own values: test_1132_red_c2_bounds_a.py)."""
    kind, how = state.split("-", 1)
    with (_image_vol() if kind == "image" else contextlib.nullcontext(_synthetic_vol(tmp_path))) as v:
        _vcl, vol_end = _geometry(v)
        tail = extend_and_plant(v) if how == "extended" else os.path.getsize(v.path) - vol_end
        _fx(tail > 0, "no image tail to report")
        rc, out, err = _vrun(v, FOREFST, "summary")
        assert _tail_lines(out, tail) or (kind == "image" and _two_part_tail(out, tail)), (
            "no line reports the %d-byte (%s) image tail after the volume end, nor two parts adding up to it" % (
                tail, F._human_size(tail))) + _ctx(rc, out, err, v.ops)


# RED 1.13.2 B3: alloc_capacity takes the volume as (image size - ps) // cs (fd:790-802): the tail counts as `beyond
# the last container`, and on a truncated image the allocator's own summary is rejected (covered > image) (the strict
# xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("state", ["as-is", "extended", "truncated"])
def test_b3_image_capacity_comes_from_the_volume_not_the_image(state):
    with _image_vol() as v:
        vcl, _end = _geometry(v)
        vol_bytes = vcl * CS
        if state == "extended":
            extend_and_plant(v)
        elif state == "truncated":
            truncate_inside_volume(v)
        rc, out, err = _vrun(v, FOREFST, "summary", "--json", "-")
        j = _json_of(out, "summary")
        _keep(j.get("volume_size_bytes") == vol_bytes, "volume_size_bytes %r != %d" % (j.get("volume_size_bytes"),
                                                                                        vol_bytes))
        cap = j.get("capacity")
        assert cap, "summary reports no capacity (the allocator summary was rejected)" + _ctx(rc, "", err, v.ops)
        assert cap.get("outside_allocator_bytes") == vol_bytes - cap.get("allocator_covered_bytes", -1), (
            "outside_allocator_bytes = %r; the volume (%d B) minus the allocator's %r B is %r" % (
                cap.get("outside_allocator_bytes"), vol_bytes, cap.get("allocator_covered_bytes"),
                vol_bytes - cap.get("allocator_covered_bytes", 0)))
        assert cap.get("volume_bytes", vol_bytes) == vol_bytes, "capacity.volume_bytes = %r, the volume is %d" % (
            cap.get("volume_bytes"), vol_bytes)
        rc, out, err = _vrun(v, FOREFST, "summary")
        wrong = [ln.strip() for ln in out.splitlines() if "beyond the last container" in ln]
        assert not wrong or cap["outside_allocator_bytes"] > 0, "%r printed for a volume that ends at its last " \
                                                                "container" % wrong


def _truncation_lines(text):
    """A line that states a truncation. The third alternative (C2 RED critic, 2026-10-23) accepts wave C's decided
    sentence (WAVEC_READING_bounds section 3: `the image ends at offset X, before the volume's end at offset Y ...`),
    which need not carry the word `truncated`, on whichever line it wraps."""
    return [ln for ln in text.splitlines()
            if (re.search(r"(?i)truncat", ln) and re.search(r"(?i)\b(image|volume|file)\b", ln))
            or re.search(r"(?i)image\s+(ends|is\s+shorter)\s+(before|than)", ln)
            or re.search(r"(?i)\bimage\s+(?:file\s+)?ends\s+at\b.*\bbefore\b|\bbefore\s+the\s+volume(?:'s)?\s+end\b", ln)]


def test_b1_b3_matchers_accept_corrected_wording_and_reject_the_1131_lines():
    """Unit level: no RED asks for something no correct output could print, and none is met by 1.13.1's lines."""
    # B3 image tail and truncation
    # acceptance 1.14.0 (K6): IEC units, the exact bytes first ("48.0 MB" is a retired form)
    assert _tail_lines("  Image tail:         50331648 bytes (48 MiB) after the volume end (not this volume's)", 48 << 20)
    assert _tail_lines("  Image tail:         48 MiB after the volume end (not this volume's)", 48 << 20)
    assert _tail_lines("  50,331,648 bytes follow the volume end (image tail)", 48 << 20)
    assert not _tail_lines("      • 48.0 MB lies beyond the last container,", 48 << 20)          # 1.13.1
    assert not _tail_lines("  Image size:         2.0 GB", 48 << 20)
    assert _truncation_lines("  [WARN] the image is truncated: it ends 16.0 MB before the volume end")
    assert not _truncation_lines("  [WARN] SUPB copy at 0xfd is missing or damaged (all zeros)\n"
                                 "  [WARN] backup boot sector missing")                        # 1.13.1
    # wave C (C2 RED critic): bounds section 3's sentence, wrapped or not; Q17's two-part tail adding up to the tail
    assert _truncation_lines("  [WARN] the image ends at offset 0x7c000000, before the volume's end at offset "
                             "0x7d000000: 16777216 bytes of the volume are not in the image")
    assert _truncation_lines("  [WARN] the image ends at offset 0x7c000000,\n         before the volume's end at "
                             "offset 0x7d000000")
    assert not _truncation_lines("  65536 bytes after the partition (the image ends at offset 0x80000000)")
    two = ("  Image tail:    50266112 bytes (47.9 MiB) inside the partition after the volume\n"
           "                 65536 bytes (64 KiB) after the partition")
    assert _two_part_tail(two, 48 << 20) and not _two_part_tail(two, (48 << 20) + 1)
    assert not _two_part_tail("      • 48.0 MB lies beyond the last container,\n"
                              "        so no allocator tracks it — it is neither used nor free", 48 << 20)   # 1.13.1
    assert not _two_part_tail("  Image tail:    50331648 bytes after the volume", 48 << 20)   # one line: _tail_lines'
    assert _two_part_tail("  tail: 50,266,112 bytes in the partition after the volume; 65,536 bytes after the "
                          "partition", 48 << 20)
    # B3 coverage
    line = "  Orphan-page scan: scanned 224 of 256 clusters (87.50% of the volume) -- INCOMPLETE: the image ends"
    _l, nums = _coverage_numbers(line)
    assert 256 in nums and max(nums) <= 256 and nums[0] <= 224
    _l, nums = _coverage_numbers("  Orphan-page scan: scanned 224 of 224 clusters (100% of the volume)")   # 1.13.1
    assert 256 not in nums
    _l, nums = _coverage_numbers("  Orphan-page scan: the volume has 256 clusters; the image ends after 224 of them, "
                                 "all 224 scanned (87.50%)")                                    # C2 RED critic
    assert 256 in nums and max(nums) <= 256 and nums[0] > 224 and 224 in nums
    # C2 RED re-check (escalation): the node's whole test -- the decided forms pass, a claim of more than the image
    # holds is refused in either word order (the critic's `held in nums` alone accepted the last two)
    for ln, ok in (("  Orphan-page scan: scanned 224 of 256 clusters (87.50% of the volume) -- INCOMPLETE: the image "
                    "ends", True),
                   ("  Orphan-page scan: the volume has 256 clusters; the image ends after 224 of them, all 224 scanned "
                    "(87.50%)", True),
                   ("  Orphan-page scan: scanned 224 of 224 clusters (100% of the volume)", False),       # 1.13.1
                   ("  Orphan-page scan: scanned 256 of 256 clusters (100% of the volume); the image ends after 224 "
                    "clusters", False),
                   ("  Orphan-page scan: scanned all 256 clusters -- the image holds 224", False)):
        _l, nums = _coverage_numbers(ln)
        assert _scan_coverage_ok(_l, nums, 256, 224) is ok, ln
    # B1 deleted
    old = ("── Checkpoint Comparison ──\n  Current checkpoint: VC=64\n  Previous checkpoint: VC=63\n"
           "  Same top-level files in both (change may be in subdirectories or metadata)\n\n── B+-tree ──")
    assert not _FAIL.search(_cmp_section(old))                                                   # 1.13.1
    new = ("── Checkpoint Comparison ──\n  Current checkpoint: VC=63 (LCN 0x88)\n"
           "  Previous checkpoint: VC=64 (LCN 0x48) FAILED its self-checksum -- not compared\n── B+-tree ──")
    assert _FAIL.search(_cmp_section(new)) and _cmp_vc(_cmp_section(new), "Current") == 63
    # B1 CHKP lines
    rows = _chkp_line_hashes("  CHKP primary     LCN 0x13f8 (offset 0x23f8000)  — checksum OK, vclock=64\n"
                             "      " + "ab" * 32 + "\n  CHKP secondary   LCN 0xee34 (offset 0xfe34000)  — BAD\n")
    assert rows == [(0x13F8, "ab" * 32, rows[0][2]), (0xEE34, None, rows[1][2])]
    # B1 chkp.md tie rule: the 1.13.1 sentence is refused; an F1-correct sentence that still names the chooser's
    # distinct return value is accepted and names slot 0 (critic, 2026-09-27)
    old_doc = ("On an equal +0x60 it returns a **distinct third value rather than naming a winner** — the tie is "
               "signalled, not silently resolved.")
    f1_doc = ("`ChooseCheckpointRecord<0>` returns a distinct third value (GenericEqual) on a tie rather than naming a "
              "winner, but its caller keeps the current choice, so on an equal +0x60 the driver keeps slot 0, the "
              "copy listed first in the superblock, and the tie is resolved without any signal.")
    assert _OLD_TIE_RULE.search(old_doc)                                                          # 1.13.1
    assert not _OLD_TIE_RULE.search(f1_doc) and _SLOT0.search(f1_doc) and re.search(r"(?i)\btie\b", f1_doc)


# RED 1.13.2 B3: a truncated image is reported only as missing backup copies (`missing or damaged (all zeros)`) (the
# strict xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("cmd", ["summary", "integrity"])
def test_b3_a_volume_cut_short_is_reported_as_truncated(b3vol, cmd):
    truncate_inside_volume(b3vol)
    rc, out, err = _vrun(b3vol, FOREFST, cmd)
    _keep(rc != 0, "%s exits 0 on an image that lost the backup copies" % cmd)
    assert _truncation_lines(out + "\n" + err), "nothing says the image is truncated" + _ctx(rc, out, err, b3vol.ops)


_SCANNED_COUNT = re.compile(r"(?i)\bscanned\s+(?:all\s+(?:of\s+)?)?(?:the\s+)?(\d[\d,]*)"
                            r"|(\d[\d,]*)\s+(?:clusters?\s+)?(?:were\s+)?scanned\b")


def _scan_claims_more_than_held(line, held):
    """C2 RED re-check (escalation, 2026-10-23): the coverage line says more was scanned than the image holds --
    `100% of the volume`, or a count named as scanned (`scanned N`, `scanned all N`, `N scanned`) above `held`."""
    return bool(re.search(r"(?i)\b100(?:\.0+)?\s*%\s*of\s+the\s+volume\b", line)) or any(
        int((m.group(1) or m.group(2)).replace(",", "")) > held for m in _SCANNED_COUNT.finditer(line))


def _scan_coverage_ok(line, nums, vcl, held):
    """The volume's N clusters named, no count above N, and the clusters scanned: the line's first count (`scanned X of
    Y`), or -- in any order of the line -- exactly the clusters the image holds, min(N, the image's clusters) of
    WAVEC_READING_bounds section 3 (C2 RED critic); never a claim of more than the image holds (the re-check: the
    critic's `held in nums` alone accepted `scanned 256 of 256 clusters (100% of the volume); the image ends after
    224`, the defect this RED names)."""
    return (vcl in nums and max(nums) <= vcl and (nums[0] <= held or held in nums)
            and not _scan_claims_more_than_held(line, held))


# RED 1.13.2 B3: on a truncated image the orphan scan counts the clusters the image holds as the volume and claims
# `100% of the volume` (the strict xfail mark removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("mode", sorted(_SCAN_MODES))
def test_b3_orphan_scan_of_a_volume_cut_short_does_not_claim_all_of_it(b3vol, mode):
    """The clusters scanned: see `_scan_coverage_ok` (the C2 RED critic's widened form, the re-check's refusal of a
    claim of more than the image holds)."""
    vcl, _end = _geometry(b3vol)
    held = truncate_inside_volume(b3vol)
    rc, out, err = _vrun(b3vol, FOREFST, *_SCAN_MODES[mode])
    line, nums = _coverage_numbers(out)
    assert _scan_coverage_ok(line, nums, vcl, held), (
        "coverage `%s`: the volume has %d clusters and the image holds %d" % (line, vcl, held)) + _ctx(
        rc, out, err, b3vol.ops)


# RED 1.13.2 B3: refsanalysis allocators takes volume_clusters from the image length (ra:1348) (the strict xfail mark
# removed: fixed in step C2, area bounds_a)
@pytest.mark.parametrize("state", ["synthetic-extended", "synthetic-truncated", "image-as-is"])
def test_b3_refsanalysis_allocators_counts_the_volume_not_the_file_length(state, tmp_path):
    kind, how = state.split("-", 1)
    with (_image_vol() if kind == "image" else contextlib.nullcontext(_synthetic_vol(tmp_path))) as v:
        vcl, _end = _geometry(v)
        if how == "extended":
            extend_and_plant(v)
        elif how == "truncated":
            truncate_inside_volume(v)
        rc, out, err = _vrun(v, REFSANALYSIS, "allocators", "--json")
        got = _json_of(out, "allocators").get("volume_clusters")
        assert got == vcl, "volume_clusters = %r, the volume has %d" % (got, vcl) + _ctx(rc, out[:1500], err, v.ops)


def test_b3_control_a_file_that_ends_at_the_volume_end_reports_no_tail_and_no_truncation(tmp_path):
    """The synthetic volume ends exactly at the image end. Guards the REDs above against a line printed for every
    image: no tail line, no truncation line, coverage = the volume, allocators = the volume."""
    v = _synthetic_vol(tmp_path)
    vcl, vol_end = _geometry(v)
    _fx(os.path.getsize(v.path) == vol_end, "the synthetic image does not end at the volume end")
    rc, out, err = _vrun(v, FOREFST, "summary")
    assert not re.search(r"(?i)truncat", out + err), _ctx(rc, out, err)
    assert not [ln for ln in out.splitlines() if _TAIL_WORD.search(ln) and re.search(r"(?i)\bimage\b", ln)], out
    rc, out, err = _vrun(v, FOREFST, "deleted", "--scan-pages")
    line, nums = _coverage_numbers(out)
    assert vcl in nums and max(nums) <= vcl, line
    rc, out, err = _vrun(v, REFSANALYSIS, "allocators", "--json")
    assert _json_of(out, "allocators").get("volume_clusters") == vcl


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B4 -- FUTURE retired (K080, decision section 7.4); unit level, no image
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_VOL_CREATE, _VOL_MODIFY = 132000000000000000, 133000000000000000      # FILETIMEs, 2019 and 2022
_M = F.TS_MARGIN_100NS


def _intrinsic(create, modify, change, access):
    """Call timestomp_intrinsic_flags with the volume times it still accepts (the fix may drop vol_modify)."""
    params = inspect.signature(F.timestomp_intrinsic_flags).parameters
    kw = {k: val for k, val in (("vol_create", _VOL_CREATE), ("vol_modify", _VOL_MODIFY)) if k in params}
    return F.timestomp_intrinsic_flags(create, modify, change, access, **kw)


# RED 1.13.2 B4: green with step C4 (the strict xfail mark removed)
def test_b4_timestomp_emits_no_future_flag():
    ct = _VOL_MODIFY + 2 * _M                                 # created after the volume time, nothing else odd
    flags = _intrinsic(ct, ct, ct, ct)
    assert "FUTURE" not in flags, "flags for a file created after the volume time: %r" % flags


# RED 1.13.2 B4: green with step C4 (the strict xfail mark removed)
def test_b4_created_after_the_volume_time_does_not_raise_a_tier():
    ct = _VOL_MODIFY + 2 * _M
    alone = F.timestomp_verdict(_intrinsic(ct, ct, ct, ct))
    with_cgm = F.timestomp_verdict(_intrinsic(ct, ct - 2 * _M, ct, ct))
    assert alone[0] == "NONE", "Created after the volume time and nothing else: %r" % (alone,)
    assert with_cgm[0] == "INFO", "CREATE_GT_MODIFY plus a late Created: %r" % (with_cgm,)


def test_b4_control_the_other_intrinsic_signals_still_fire():
    """Guards the retirement against removing more than FUTURE."""
    assert "PRE_FORMAT" in _intrinsic(_VOL_CREATE - 2 * _M, _VOL_CREATE - 2 * _M, _VOL_CREATE, 0)
    ct = _VOL_CREATE + 10 * _M
    assert "CHANGE_LATE" in _intrinsic(ct, ct, ct + 5 * _M, 0)
    assert "CREATE_GT_MODIFY" in _intrinsic(ct, ct - 2 * _M, ct, 0)
    assert F.timestomp_verdict(["CHANGE_LATE"])[0] == "MEDIUM"
    assert F.timestomp_verdict(["PRE_FORMAT", "CHANGE_LATE"])[0] == "INFO"


def _rc_module():
    """The retired-claims gate (7j) as shipped beside the tests (analysis/verification in both trees)."""
    p = os.path.join(REPO, "analysis", "verification", "check_retired_claims.py")
    if not os.path.isfile(p):
        pytest.skip("check_retired_claims.py not in this tree")
    spec = importlib.util.spec_from_file_location("b_items_check_retired_claims", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _b4_scope():
    """`rg` scope of the row: both tools and docs/, without changelog.md and website/content/."""
    files = [os.path.join(REPO, t) for t in ("forefst.py", "refsanalysis.py")]
    docs = os.path.join(REPO, "docs")
    for dp, dn, fn in os.walk(docs):
        rel = os.path.relpath(dp, docs).replace(os.sep, "/")
        if rel == "website/content" or rel.startswith("website/content/") or "__pycache__" in rel:
            continue
        files += [os.path.join(dp, n) for n in fn if n != "changelog.md"]
    return files


def _read_bytes(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as e:
        raise RedFixtureError("cannot read %s: %s" % (path, e))


def _utf8(raw):
    """(text, None), or (None, the UnicodeDecodeError) when RAW is not UTF-8. Whether the file is text is this
    helper's answer, not a skipped read: a read error raises (N204)."""
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError as e:
        return None, e


def _scope_text(path):
    """A file of the row's `rg` scope as text, or None for a binary file (one holding a NUL byte, which `rg` skips).
    A file that is neither UTF-8 nor binary is not skipped: it raises, because `rg` would still search it (N204)."""
    raw = _read_bytes(path)
    text, err = _utf8(raw)
    if text is None and b"\x00" not in raw:
        raise RedFixtureError("%s is not UTF-8 and not binary (%s): the scan cannot read it as rg would" % (path, err))
    return text


def _hits(pattern, files, flags=0):
    """Sentences matching `pattern`, except retired-claim text: a sentence that some 7j row's pattern AND its
    `unless` both match (text stating the correction). Mirrors check_retired_claims.py."""
    m = _rc_module()
    spec = m.load_spec()
    out = []
    for path in files:
        text = _scope_text(path)
        if text is None:
            continue                        # binary (the site's fonts): rg skips it too
        lines = text.split("\n")
        seen = set()
        for sent, ln in m.sentences(text):
            if not re.search(pattern, sent, flags):
                continue
            if any(re.search(e["pattern"], sent, re.I) and e["unless"] and re.search(e["unless"], sent, re.I)
                   for e in spec):
                continue
            # report the exact lines, as `rg` would: a line of this paragraph whose sentence-piece holding the match
            # is part of this sentence (a match wrapped across two lines is reported at the paragraph start)
            exact, i = [], ln - 1
            while i < len(lines) and lines[i].strip():
                if any(re.search(pattern, p, flags) and p in sent
                       for p in re.split(r"(?<=[.!?])\s+", lines[i].strip())):
                    exact.append(i)
                i += 1
            for i in (exact or [ln - 1]):
                if i not in seen:
                    seen.add(i)
                    out.append("%s:%d  %s" % (os.path.relpath(path, REPO), i + 1, lines[i].strip()[:120]))
    return out


# RED 1.13.2 B4: green with step C4 (the strict xfail mark removed)
def test_b4_future_is_not_named_in_either_tool():
    hits = _hits(r"\bFUTURE\b", [p for p in _b4_scope() if p.endswith(".py") and os.path.dirname(p) == REPO])
    assert not hits, "%d line(s):\n%s" % (len(hits), "\n".join(hits))


# RED 1.13.2 B4: green with step C4 (the strict xfail mark removed)
def test_b4_future_is_not_named_in_the_docs():
    hits = _hits(r"\bFUTURE\b", [p for p in _b4_scope() if not os.path.dirname(p) == REPO])
    assert not hits, "%d line(s):\n%s" % (len(hits), "\n".join(hits))


# RED 1.13.2 B4: green with step C4 (the strict xfail mark removed)
def test_b4_last_metadata_write_is_not_said_in_either_tool_or_the_docs():
    hits = _hits(r"last\s+metadata\s+write", _b4_scope(), re.I)
    assert not hits, "%d line(s):\n%s" % (len(hits), "\n".join(hits))


# RED 1.13.2 B4: green with step C4 (the strict xfail mark removed)
def test_b4_known_issues_list_has_no_future_item():
    # RC3 (1.14.0): the Known issues have their own page, docs/tools/known_issues.md (the maintainer's review)
    text = open(os.path.join(REPO, "docs", "tools", "known_issues.md"), encoding="utf-8").read() + "\n## end\n"
    m = re.search(r"(?ms)^# Known issues.*?(?=^## end)", text)
    _fx(m, "tools/known_issues.md has no Known issues heading")
    assert "FUTURE" not in m.group(0), [ln for ln in m.group(0).splitlines() if "FUTURE" in ln]


# the retired claims as 1.13.1 prints and publishes them (fd:10139, fd:16329, concepts/timestomp_detection.md:111)
_CANARY_LMW = "             or FUTURE (created after the volume's last metadata write)."
_CANARY_FUTURE = "a count of heuristic signals never reaches it. MEDIUM is CHANGE_LATE without PRE_FORMAT, or FUTURE."
_CANARY_TABLE = "| **FUTURE** | Created after the volume's last metadata write | intrinsic + volume | medium\\* |"


# RED 1.13.2 B4: green with step C4 (the strict xfail mark removed)
def test_b4_retired_claims_gate_has_live_rows_for_future_and_last_metadata_write():
    m = _rc_module()
    spec = m.load_spec()

    def fires(row, text):
        return re.search(row["pattern"], text, re.I) and not (row["unless"] and re.search(row["unless"], text, re.I))
    lmw = [r["id"] for r in spec if fires(r, _CANARY_LMW) or fires(r, _CANARY_TABLE)]
    fut = [r["id"] for r in spec if fires(r, _CANARY_FUTURE)]
    assert lmw, "no 7j row fires on the 'last metadata write' claim (%d rows: %s)" % (len(spec), [r["id"] for r in spec])
    assert fut, "no 7j row fires on the FUTURE tier claim"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = m.main()
    assert rc == 0, "the retired-claims gate does not pass:\n" + buf.getvalue()[-3000:]


def _intrinsic_signal_set():
    names = re.findall(r'flags\.append\("([A-Z_]+)"\)', inspect.getsource(F.timestomp_intrinsic_flags))
    _fx(len(names) >= 3, "cannot derive the intrinsic signal set from timestomp_intrinsic_flags")
    return names


def test_b4_control_low_tier_statement_matches_the_code_enumeration():
    """O6 (open): LOW is kept or removed. Either way the page must agree with the code. Today it does (256 inputs,
    HIGH 223 / MEDIUM 20 / INFO 11 / NONE 2 / LOW 0); once FUTURE goes this fails until `:170` is re-derived."""
    doc = open(os.path.join(REPO, "docs", "concepts", "timestomp_detection.md"), encoding="utf-8").read()
    low_rows = [ln for ln in doc.splitlines() if re.match(r"\|\s*\*\*LOW\*\*\s*\|", ln)]
    if "LOW" not in F.TIMESTOMP_TIERS:
        assert not low_rows, "LOW was removed from the code but the page still has a LOW tier row"
        return
    assert len(low_rows) == 1, "the page must state the LOW tier once: %r" % low_rows
    row = low_rows[0]
    sigs = _intrinsic_signal_set() + ["ROUND_TIMESTAMPS", "HARDLINK_MACB_MISMATCH"]   # the pipeline adds both
    code = Counter()
    for bits in itertools.product((0, 1), repeat=len(sigs)):
        fl = [s for s, b in zip(sigs, bits) if b]
        for usn in (False, True):
            for hl in (False, True):
                code[F.timestomp_verdict(fl, usn_conf=usn, hl_conf=hl)[0]] += 1
    n = re.search(r"(\d+)\s+(?:pipeline-constructible\s+)?inputs", row)
    stated = {t: int(c) for t, c in re.findall(r"\b(HIGH|MEDIUM|INFO|NONE|LOW)\*{0,2}\s+(\d+)", row)}
    assert n and int(n.group(1)) == sum(code.values()), "inputs: page %s, code %d" % (
        n.group(1) if n else None, sum(code.values()))
    assert stated == {t: code.get(t, 0) for t in stated} and set(code) <= set(stated), (
        "page %r vs code %r" % (stated, dict(code)))
    unreachable = bool(re.search(r"(?i)unreachable|no input reaches|no current signal", row))
    assert unreachable == (code.get("LOW", 0) == 0), "the page's reachability claim disagrees with the code"


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# B11 -- export collisions: the metadata bundle's seal, and the bulk exporters' missing index
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _snapshot_dir(d):
    out = {}
    for dp, dn, fn in os.walk(d):
        for n in fn:
            p = os.path.join(dp, n)
            out[os.path.relpath(p, d).replace(os.sep, "/")] = _file_sha(p)
    return out


def _seal_failures(seal_path):
    """Lines of a sha256sum-style seal that do not verify against the files beside it."""
    base, bad, n = os.path.dirname(seal_path), [], 0
    for line in open(seal_path, encoding="utf-8").read().splitlines():
        if not line.strip():
            continue
        n += 1
        h, name = line.split(None, 1)
        p = os.path.join(base, name.lstrip("*").strip())
        if not os.path.isfile(p) or _file_sha(p) != h.lower():
            bad.append(name.strip())
    return bad if n else ["(empty seal)"]


def _seals(d):
    return [os.path.join(dp, n) for dp, dn, fn in os.walk(d) for n in fn
            if re.match(r"(?i)sha256sums.*\.txt$", n) or n.lower().endswith(".sha256")]


def _refs_ps(path):
    """Partition start of the ReFS volume in an image, read here (GPT, or a bare volume at 0)."""
    with open(path, "rb") as fh:
        fh.seek(0)
        if fh.read(8)[3:7] == b"ReFS":
            return 0
        fh.seek(512)
        h = fh.read(512)
        _fx(h[:8] == b"EFI PART", "%s: no GPT and no VBR at 0" % path)
        lba, n, es = F.le64(h, 72), F.le32(h, 80), F.le32(h, 84)
        fh.seek(lba * 512)
        ents = fh.read(min(n, 128) * es)
        for i in range(min(n, 128)):
            first = F.le64(ents, i * es + 32)
            if first:
                fh.seek(first * 512)
                if fh.read(8)[3:7] == b"ReFS":
                    return first * 512
    raise RedFixtureError("%s: no ReFS partition" % path)


def _serial_changed(v):
    """Source 2 of the synthetic case: the same volume with another serial in both boot sectors (re-checksummed)."""
    for off in (0, os.path.getsize(v.path) - 512):
        b = bytearray(v.read(off, 512))
        struct.pack_into("<Q", b, 0x38, 0x1111222233334444)
        struct.pack_into("<H", b, 0x16, F._vbr_checksum(bytes(b), 512))
        v.write(off, bytes(b))
    _fx(F._vbr_checksum(v.read(0, 512), 512) == F.le16(v.read(0, 512), 0x16), "re-checksummed VBR does not verify")
    v.ops.append("serial changed")
    return v


@contextlib.contextmanager
def _metadata_sources(kind, tmp_path):
    """(source 1 path, its cli, source 2 path, its cli, source 2's VBR sha256, bundle dir)."""
    if kind == "synthetic":
        v1, v2 = _synthetic_vol(tmp_path, "s1"), _serial_changed(_synthetic_vol(tmp_path, "s2"))
        d = str(tmp_path / "bundle")
        yield v1.path, v1.geo.cli, v2.path, v2.geo.cli, _sha(v2.read(0, 512)), d
        return
    p1, p2 = _image_or_skip(AB.BASE_IMAGE), _image_or_skip("step1/win10refsmini.raw")
    ps2 = _refs_ps(p2)
    with open(p2, "rb") as fh:
        fh.seek(ps2)
        vbr2 = fh.read(512)
    _fx(vbr2[3:7] == b"ReFS", "win10refsmini: no VBR at 0x%x" % ps2)
    with _scratch("bundle") as d:
        yield p1, [], p2, [], _sha(vbr2), os.path.join(d, "bundle")


@pytest.mark.parametrize("kind", ["synthetic", "image"])
def test_b11_a_second_metadata_bundle_keeps_the_first_seal_and_seals_its_own(kind, tmp_path):
    with _metadata_sources(kind, tmp_path) as (p1, cli1, p2, cli2, vbr2_sha, d):
        rc1, out1, err1 = _run(FOREFST, p1, "export", "metadata", d, cli=cli1, cwd=str(tmp_path))
        _fx(os.path.isfile(os.path.join(d, "sha256sums.txt")), "the first export wrote no seal" + _ctx(rc1, out1, err1))
        _fx(not _seal_failures(os.path.join(d, "sha256sums.txt")), "the first bundle's seal does not verify")
        s1 = _snapshot_dir(d)
        rc2, out2, err2 = _run(FOREFST, p2, "export", "metadata", d, cli=cli2, cwd=str(tmp_path))
        s2 = _snapshot_dir(d)
        ctx = _ctx(rc2, out2, err2)
        # decision 22's O2 (tightened before the fix): not refused; the first bundle's folder exactly as it was (no
        # file added, changed or removed); the second bundle in `<dir>_2` with its own seal; the path printed
        assert rc2 != 1, "refused (O2 as decided: a second bundle is not refused)" + ctx
        assert s2 == s1, "the first bundle's folder changed: %r" % sorted(set(s1) ^ set(s2) | {
            k for k in s1 if s2.get(k) != s1[k]}) + ctx
        d2 = d + "_2"
        assert d2 in out2 + err2, "the folder used is not printed" + ctx
        seals2 = _seals(d2) if os.path.isdir(d2) else []
        good = []
        for s in seals2:
            if _seal_failures(s):
                continue
            base = os.path.dirname(s)
            names = [ln.split(None, 1)[1].lstrip("*").strip() for ln in open(s).read().splitlines() if ln.strip()]
            if any(_file_sha(os.path.join(base, n)) == vbr2_sha for n in names):
                good.append(s)
        assert good, "no second seal verifies and covers the second source's boot sector: new seals %r" % [
            (os.path.relpath(s, d), _seal_failures(s)) for s in seals2] + ctx


@pytest.mark.parametrize("kind", ["synthetic", "image"])
def test_b11_control_one_metadata_bundle_seals_itself(kind, tmp_path):
    """One export into an empty directory: its seal verifies and covers the source's boot sector (the verifier and
    the independent VBR hash used by the RED above are sound)."""
    with _metadata_sources(kind, tmp_path) as (p1, cli1, p2, cli2, vbr2_sha, d):
        rc, out, err = _run(FOREFST, p2, "export", "metadata", d, cli=cli2, cwd=str(tmp_path))
        seal = os.path.join(d, "sha256sums.txt")
        assert os.path.isfile(seal) and not _seal_failures(seal), _ctx(rc, out, err)
        names = [ln.split(None, 1)[1].strip() for ln in open(seal).read().splitlines() if ln.strip()]
        assert any(_file_sha(os.path.join(d, n)) == vbr2_sha for n in names)


# ─── bulk exporters: a forced collision must leave a source -> written-path record ──────────────────────────

_REASON = re.compile(r"(?i)collision|collid|exist|dup|renam|clash|conflict|taken|occupied")
_OBJREF = re.compile(r"(?i)0x[0-9a-f]+:0x[0-9a-f]+")


def _index_records(d):
    """Candidate index records in an export directory: the scalar VALUES of every dict (any depth) of a .json file
    (key names are not evidence), every line of a .jsonl file, every line of any other small text file."""
    for dp, dn, fn in os.walk(d):
        for n in fn:
            p = os.path.join(dp, n)
            if os.path.getsize(p) > (4 << 20):
                continue
            text, _not_utf8 = _utf8(_read_bytes(p))
            if text is None:
                continue                    # not UTF-8: an exported file's content, never an index record
            if n.lower().endswith(".json"):
                try:
                    stack = [json.loads(text)]
                except ValueError:
                    stack = []
                while stack:
                    o = stack.pop()
                    if isinstance(o, dict):
                        yield " | ".join(str(x) for x in o.values() if not isinstance(x, (dict, list)))
                        stack.extend(o.values())
                    elif isinstance(o, list):
                        stack.extend(o)
                continue
            for line in text.splitlines():
                yield line


def _find_index_record(d, written_rel, sha, objref=None):
    """A record naming the written file (relative path or basename), its SHA-256, the source ObjectRef (exact, or
    any ObjectRef when None) and a rename reason. The reason is looked for with the file names taken out, so a
    `.dup1` suffix is not itself a reason."""
    forms = sorted({written_rel, written_rel.replace("/", os.sep), os.path.basename(written_rel)}, key=len,
                   reverse=True)
    ref_re = re.compile(r"(?i)(?<![0-9a-fx])%s(?![0-9a-f])" % re.escape(objref)) if objref else _OBJREF
    for rec in _index_records(d):
        if not any(f in rec for f in forms) or sha.lower() not in rec.lower() or not ref_re.search(rec):
            continue
        bare = rec
        for f in forms + [os.path.basename(written_rel).split(".dup")[0]]:
            bare = bare.replace(f, " ")
        if _REASON.search(bare):
            return rec
    return None


def test_b11_index_matcher_accepts_a_plausible_index_and_rejects_the_1131_directory(tmp_path):
    """The matcher is neither blind nor trivially satisfied (unit level)."""
    sha = "ab" * 32
    d = tmp_path / "exp"
    (d / "test").mkdir(parents=True)
    (d / "test" / "ok.txt").write_bytes(b"planted")
    (d / "test" / "ok.txt.dup1").write_bytes(b"real")
    assert _find_index_record(str(d), "test/ok.txt.dup1", sha, "0x702:0x2") is None       # 1.13.1: no index
    (d / "export_index.json").write_text(json.dumps({"entries": [
        {"object_ref": "0x702:0x2", "written": "test/ok.txt.dup1", "sha256": sha,
         "renamed_because": "test/ok.txt already existed"}]}))
    assert _find_index_record(str(d), "test/ok.txt.dup1", sha, "0x702:0x2")
    for miss in ({"sha256": "cd" * 32}, {"object_ref": "0x702:0x3"}, {"object_ref": "0x702:0x20"},
                 {"renamed_because": ""}, {"written": "x"}):
        rec = {"object_ref": "0x702:0x2", "written": "test/ok.txt.dup1", "sha256": sha,
               "renamed_because": "test/ok.txt already existed"}
        rec.update(miss)
        (d / "export_index.json").write_text(json.dumps([rec]))
        assert _find_index_record(str(d), "test/ok.txt.dup1", sha, "0x702:0x2") is None, miss
    (d / "export_index.json").unlink()
    (d / "index.csv").write_text("ObjectRef,Written,SHA256,Reason\n0x702:0x2,test/ok.txt.dup1,%s,name collision\n"
                                 % sha)
    assert _find_index_record(str(d), "test/ok.txt.dup1", sha, "0x702:0x2")


# base A's /test/ok.txt: ObjectRef 0x702:0x2, 4 bytes (battery A0 files.csv, forefst 1.13.1)
_RES_OBJREF, _RES_REL, _RES_SIZE = "0x702:0x2", "test/ok.txt", 4
# win11bidule's recycled jpg: $RWQ96ME.jpg, SHA-256 measured by Windows (win11bidules-logs/allfileswithhashes.csv)
_RB_IMAGE, _RB_NAME = "win11bidule.raw", "jpginrecyclebin.jpg"
_RB_WIN_SHA = "2bbc2c538dfe8746f432b75f5691f04714c412da20766672277d68af300776ed"
# win11refs2tsnapshots: testsnapshots/arg.txt, ObjectRef 0x73c:0x2, one version "test2" (samples, forefst 1.13.1)
_SN_IMAGE, _SN_PREFIX, _SN_OBJREF = "win11refs2tsnapshots.raw", "testsnapshots_arg.txt__", "0x73c:0x2"
_PLANTED = b"B11 planted: an examiner's file that happens to carry this name\n"


def test_b11_image_resident_all_records_a_forced_rename_in_an_index(tmp_path):
    img = _image_or_skip(AB.BASE_IMAGE)
    with _scratch("resident") as s:
        d = os.path.join(s, "out")
        os.makedirs(os.path.join(d, "test"))
        planted = os.path.join(d, "test", "ok.txt")
        open(planted, "wb").write(_PLANTED)
        before = _snapshot_dir(d)
        rc, out, err = _run(FOREFST, img, "export", "resident-all", d, cwd=s)
        _keep(open(planted, "rb").read() == _PLANTED, "resident-all overwrote the examiner's file")
        new = [n for n in os.listdir(os.path.join(d, "test")) if os.path.isfile(os.path.join(d, "test", n))
               and "test/" + n not in before and os.path.getsize(os.path.join(d, "test", n)) == _RES_SIZE]
        _keep(len(new) == 1, "resident-all did not write /test/ok.txt under another name: %r" % new)
        rel = "test/" + new[0]
        rec = _find_index_record(d, rel, _file_sha(os.path.join(d, rel)), _RES_OBJREF)
        assert rec, "no index record names %s with its SHA-256, ObjectRef %s and a rename reason; files: %r" % (
            rel, _RES_OBJREF, sorted(_snapshot_dir(d))) + _ctx(rc, out, err)


def test_b11_image_recyclebin_records_a_forced_rename_in_an_index(tmp_path):
    img = _image_or_skip(_RB_IMAGE)
    with _scratch("recycle") as s:                          # the export writes about 52 MB; removed at the end
        d = os.path.join(s, "out")
        os.makedirs(d)
        planted = os.path.join(d, _RB_NAME)
        open(planted, "wb").write(_PLANTED)
        before = _snapshot_dir(d)
        rc, out, err = _run(FOREFST, img, "export", "recyclebin", d, cwd=s)
        after = _snapshot_dir(d)
        _keep(open(planted, "rb").read() == _PLANTED, "recyclebin overwrote the examiner's file")
        new = [k for k, h in after.items() if k not in before and h == _RB_WIN_SHA]
        _keep(len(new) == 1, "the recycled jpg (Windows SHA-256 %s...) was not written exactly once: %r" % (
            _RB_WIN_SHA[:16], sorted(after)))
        rec = _find_index_record(d, new[0], _RB_WIN_SHA)
        assert rec, "no index record names %s with its SHA-256, an ObjectRef and a rename reason; files: %r" % (
            new[0], sorted(after)) + _ctx(rc, out, err)


def test_b11_image_snapshots_never_overwrite_and_record_a_forced_rename(tmp_path):
    img = _image_or_skip(_SN_IMAGE)
    with _scratch("snap") as s:
        d1, d2 = os.path.join(s, "first"), os.path.join(s, "second")
        rc, out, err = _run(FOREFST, img, "export", "snapshots", d1, cwd=s)
        names = [n for n in (os.listdir(d1) if os.path.isdir(d1) else []) if n.startswith(_SN_PREFIX)]
        _fx(len(names) == 1, "export snapshots did not write exactly one version of arg.txt: %r" % names
            + _ctx(rc, out, err))
        version = open(os.path.join(d1, names[0]), "rb").read()
        _fx(version != _PLANTED, "the planted bytes equal the version")
        os.makedirs(d2)
        planted = os.path.join(d2, names[0])
        open(planted, "wb").write(_PLANTED)
        before = _snapshot_dir(d2)
        rc, out, err = _run(FOREFST, img, "export", "snapshots", d2, cwd=s)
        after = _snapshot_dir(d2)
        assert open(planted, "rb").read() == _PLANTED, "export snapshots OVERWROTE %s (%d bytes of the version " \
                                                       "replaced the examiner's file)" % (names[0], len(version))
        new = [k for k, h in after.items() if k not in before and h == _sha(version)]
        assert len(new) == 1, "the version was not written under another name: %r" % sorted(after)
        rec = _find_index_record(d2, new[0], _sha(version), _SN_OBJREF)
        assert rec, "no index record names %s with its SHA-256, ObjectRef %s and a rename reason" % (
            new[0], _SN_OBJREF) + _ctx(rc, out, err)
