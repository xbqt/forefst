"""1.13.2 RED cases for fix group G2c3 (group 2's third close-out): N371, N372, N375, and the coverage of group 2's
shared helpers.

Context: `analysis/reports/v1.13.2/fixes/G2c3_CONTEXT.md` (PLAN_1.13.2 decisions 20-30, `G2_CONTEXT.md`,
`G2c_CONTEXT.md` and `G2c2_CONTEXT.md` bind), RUNNING_LOG rows N371, N372, N375; sources `fixes/GOLDEN_G2c2_critic.md`
(K-1, K-4, K-6), `fixes/REVIEW_G2c2_correctness.md` (C1, C3, the coverage gaps), `fixes/REVIEW_G2c2_tests.md` (T2, T3),
`fixes/GOLDEN_G2c2_challenge.md` (O1). Report, with every node's observed failure before the fix:
`analysis/reports/v1.13.2/fixes/FIX_G2c3.md`.

What each RED asserts
---------------------
 1 N371  an offset computed from an on-disk value (an LCN, an LBA) that is too large to seek -- CPython raises
         ValueError for 2**63 and more, which the handlers written for a failed read (`except (OSError,
         OverflowError)`) do not catch -- never escapes: no traceback, no exit 1, no CPython "cannot fit 'int'" text.
         On the critic's plants:
         * root 7's reference LCN of the checkpoint copy NOT in use garbled (one bit flipped, not re-sealed; or set to
           2**60 and re-sealed): every command gives the exit code it gives when that root is readable but does not
           match its digest (V-a, decision 20.3: `files` 0, `summary` 2), and the commands that say that condition
           say instead that root 7 cannot be read, naming the LCN its reference holds;
         * the same on the copy IN use: N205 (decisions 20.8, 21) -- read if it can be read, every command exits 2
           and says root 7 cannot be read;
         * the superblock's second checkpoint reference set to 0x7fffffffffffffff (re-sealed): a recorded skip and a
           condition naming the copy that could not be read, never exit 1 (decisions 20.8, 26: a volume that can be
           read is read).
         The class: no raw seek of a non-constant offset reaches -- in its own try or up the call chain, also through
         an import alias -- a handler that catches OSError/OverflowError but not ValueError (an AST lint node over
         both tools), and every handler
         of the critic's list (K-1: fd:84, 791, 961, 1029, 1399, 12979, 13286, 13604, 13701, 13709, 13860, 15854,
         16358, 16376, 16398, 16407, 16432; ra:825, 1514, 1526 of `prefix_G2c3`) reads through the shared guard; the
         hole query (`_hole_bytes_in`, `_hole_ranges_in`: `os.lseek` raises OverflowError there) says what it says
         for an offset past the end of the image.
 2 N372  (C1) when no checkpoint copy can be used as it is and one of them passes its self-checksum but has no root
         list that can be read, no statement says "no checkpoint copy passes its self-checksum"; one statement says,
         for each copy, why it cannot be used; it claims nothing about the driver and does not call the copy in use
         "the newest" when a newer copy exists; the same in refsanalysis `chkp` and `containers`. (C3) an older copy
         without a root list that also fails its self-checksum, or whose checksum cannot be verified, has that in the
         redundancy list too, not only "its root list could not be read".
 3 N375  (O1) the help paths of `verify-bundle` tell the user to run `summary` on the bundle for what it does not
         check; (K-4) the help texts and the docstrings do not say that "the copies the volume is not read from" are
         not checked (the view conditions about those copies ARE counted: control), and say what is not checked: the
         redundancy findings of `summary` and `integrity`; (T3) `_supb_backup_how` words a copy whose self-checksum
         FAILED as failed, never as "cannot be verified".
 4 coverage  controls (they pass before and after) for branches of group 2's shared helpers no test pinned:
         `_root_check`'s read-error branch (the critic's K-6 plant through the CLI, with the file system that refuses
         its offset modelled in the tool's process so it runs on every host, and an in-process form that wraps the
         file object), the role word "newest" on N361's shape, N362's other "cannot be verified" reasons, and
         `_supb_backup_how`'s "cannot be verified" branch.

N371's runner: the RED helpers `Vol.run` / `_run_split` raise RedFixtureError on a traceback, so N371's cases use
`_run_whole`, which returns the traceback for the plain assert to state (a timeout stays a fixture error).

Volumes and discipline: as test_1132_red_g2c2.py -- the a_bootstrap `vol` fixture (``[synthetic]`` / ``[image]``,
imported by name), ``@_red`` = ``xfail(strict=True, raises=AssertionError)``, only a plain ``assert`` states the defect,
``_fx`` for a fixture that is not what the case needs, ``_keep`` for a property the current tool already has, every RED
has a control that passes now, and every oracle is checked first on the undamaged volume (or, for N371, on the readable
equivalent of the same plant, in the same node). The marks were removed when the fix landed (FIX_G2c3.md): the
unmarked file fails against the step's pre-fix tools (`fixes/prefix_G2c3/`) at the REDs' plain asserts and passes on
the fixed tree. The plants are the critic's (`crit_g2c2/probe.py`: `flipbit_hi`, `hugeroot_hi`, `readerr_hi`,
`readerr2_hi`) and the reviewers' (C1's p6, C3's p12), rebuilt with the RED files' own helpers.
"""
import ast
import errno
import os
import re
import struct
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

import test_1132_red_a_bootstrap as _AB                   # noqa: E402
from test_1132_red_a_bootstrap import (                  # noqa: E402
    RedFixtureError, _fx, _keep, _ctx, damage_supb, damage_chkp, _root_list, _FAIL, _lcn_re, FOREFST,
    REFSANALYSIS, CS, CHKP_DESC, SUPB_DESC, CLOCK_OLD, CLOCK_NEW)
from test_1132_red_group2 import (                       # noqa: E402
    IMAGE_ONLY, _statements, _n205_said, _root_named, _root_ref_offset, plant_root_failure, _UNVERIFIED)
from test_1132_red_group2b import plant_unknown_type      # noqa: E402
from test_1132_red_g2c import (                          # noqa: E402
    plant_no_root_list, plant_root_failure_on, _n343_said, _export_bundle, _verify_bundle, _run_split)
from test_1132_red_g2c2 import (                         # noqa: E402
    plant_clock_divergence, _clock_said, _n361b_plant, _CANNOT_VERIFY)

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module

_MAX_OFF = (1 << 63) - 1          # the largest offset a seek takes (a signed 64-bit file offset)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. N371 -- an offset too large to seek never escapes
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Measured before the fix (the critic's K-1, re-measured here on both volumes): one flipped bit (bit 60) in root 7's
# reference LCN of the checkpoint copy not in use makes `_chkp_root_failures` seek to an offset past 2**63; CPython
# 3.12 raises ValueError ("cannot fit 'int' into an offset-sized integer"), which its `except (OSError,
# OverflowError)` does not catch, so it escapes `checkpoint_select` into every command: forefst exits 1 with that text,
# refsanalysis `supb`/`chkp`/`containers` end in a traceback. The same at the checkpoint read itself for a superblock
# reference that large. 1.13.1 read those volumes (`files` 0, `summary` 2).

def _run_whole(v, tool, *args):
    """(rc, stdout + stderr, traceback?) of one run. Unlike Vol.run, a traceback is NOT a fixture error here: N371's
    defect IS the escape, so it is returned for the plain assert to state. A timeout is still a fixture error."""
    cmd = [sys.executable, "-B", tool, v.path] + list(args) + list(v.geo.cli)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=_AB.TIMEOUT, cwd=os.path.dirname(v.path))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    return r.returncode, r.stdout + "\n" + r.stderr, "Traceback (most recent call last)" in r.stderr


_CPYTHON_SEEK = re.compile(r"cannot fit 'int' into an offset-sized integer|int too large to convert to C long")


def _assert_no_escape(form, v, rc, out, tb):
    assert not tb, "%s: a traceback -- the offset escaped every handler" % form + _ctx(v, rc, out)
    assert not _CPYTHON_SEEK.search(out), ("%s: CPython's own error for an offset too large to seek reached the user"
                                           % form) + _ctx(v, rc, out)
    assert rc != 1, "%s: exit 1 -- a volume that can be read is refused" % form + _ctx(v, rc, out)


_HUGE_LCN = 1 << 60


def plant_root_lcn_huge(v, lcn, idx, seal):
    """The critic's K-1 plants: root `idx`'s reference LCN (slot 0) in the checkpoint copy at `lcn` made too large to
    seek. seal=False (`flipbit`): bit 60 flipped, the copy NOT re-sealed, so it also fails its self-checksum;
    seal=True (`hugeroot`): set to 2**60 and re-sealed. Checked: its byte offset is past 2**63 - 1, the other copy's
    root list is untouched, the copy's self-checksum is as planned. Returns the LCN the reference now holds."""
    g = v.geo
    blk = v.block(lcn)
    ro = _root_ref_offset(blk, idx)
    old = F.le64(blk, ro)
    _fx(old and old < (1 << 40) and _root_list(blk)[idx] and _root_list(blk)[idx][0] == old,
        "root %d of 0x%x: slot 0 holds 0x%x" % (idx, lcn, old))
    other = g.hi if lcn == g.lo else g.lo
    before = _root_list(v.block(other))
    if seal:
        def edit(b):
            struct.pack_into("<Q", b, ro, _HUGE_LCN)
        v.reseal(lcn, edit, CHKP_DESC)
    else:
        v.flip(v.at(lcn, ro + 7), 0x10)
        _fx(v.verifies(lcn) is False, "the copy at 0x%x still verifies after the flip" % lcn)
    new = F.le64(v.block(lcn), ro)
    _fx(new == (_HUGE_LCN if seal else old | _HUGE_LCN) and g.ps + new * CS > _MAX_OFF,
        "root %d of 0x%x now holds 0x%x" % (idx, lcn, new))
    _fx(_root_list(v.block(other)) == before, "the other copy's root list changed")
    return new


def plant_supb_ref(v, value):
    """Every superblock copy's second checkpoint reference (+0xC8) set to `value`, each copy re-sealed (the critic's
    `readerr_hi`: 0x7fffffffffffffff; K-6's `readerr2_hi`: 2**38).
    C2 ST-S1 (c) (fixes/C2_LEAD_SETTLEMENTS.md): the plant goes into ALL THREE copies, its values kept. Such a reference
    is outside [0x1F, N - 3], so no copy passes ValidateSuperBlock (closure B-4.1 row 8); decision 26 reads the primary
    with its finding (exit 2), so the reference is still read and N371's recorded skip stays reachable. (In the primary
    alone, B15 reads end-2's list and the reference is never read.)"""
    g = v.geo

    def edit(b):
        struct.pack_into("<Q", b, 0xC8, value)
    for lcn in (g.supb,) + tuple(g.backups):
        v.reseal(lcn, edit, SUPB_DESC)
        _fx(v.refs(lcn) == [g.lo, value] and v.verifies(lcn) is True,
            "the checkpoint list of the superblock copy at 0x%x is %r" % (lcn, v.refs(lcn)))


def _snapshot(v):
    g = v.geo
    return {off: v.read(off, CS) for off in (v.at(g.supb), v.at(g.lo), v.at(g.hi))}


def _restore(v, saved):
    for off, b in saved.items():
        v.write(off, b)
    _fx(all(v.read(off, CS) == b for off, b in saved.items()), "the restore did not land")
    _fx(v.verifies(v.geo.lo) is True and v.verifies(v.geo.hi) is True and v.verifies(v.geo.supb) is True,
        "a copy does not verify after the restore")
    v.ops.append("restored")


# The K-1 shapes, each with its readable equivalent (the same root failing its digest instead of failing to read):
# shape -> (copy, seal, equivalent plant, the copy whose root it is is in use)
def _eq_flip_hi(v):
    plant_root_failure_on(v, v.geo.hi, 7)
    damage_chkp(v, v.geo.hi)


_K1_SHAPES = {
    "flipbit-not-in-use": ("hi", False, _eq_flip_hi, False),
    "hugeroot-not-in-use": ("hi", True, lambda v: plant_root_failure_on(v, v.geo.hi, 7), False),
    "hugeroot-in-use": ("lo", True, lambda v: plant_root_failure(v, 7), True),
}

_K1_FORMS = {
    "fd-files": (FOREFST, ("files",)), "fd-search": (FOREFST, ("search", "ok")),
    "fd-timeline": (FOREFST, ("timeline",)), "fd-deleted": (FOREFST, ("deleted",)),
    "fd-summary": (FOREFST, ("summary",)), "fd-fastsummary": (FOREFST, ("fastsummary",)),
    "fd-integrity": (FOREFST, ("integrity",)), "fd-integrity-checksums": (FOREFST, ("integrity", "--checksums")),
    "ra-files": (REFSANALYSIS, ("files",)), "ra-summary": (REFSANALYSIS, ("summary",)),
    "ra-supb": (REFSANALYSIS, ("supb",)), "ra-supb-v": (REFSANALYSIS, ("supb", "-v")),
    "ra-supb-verify": (REFSANALYSIS, ("supb", "--verify")), "ra-chkp": (REFSANALYSIS, ("chkp",)),
    "ra-chkp-verify": (REFSANALYSIS, ("chkp", "--verify")), "ra-containers": (REFSANALYSIS, ("containers",)),
    "ra-all": (REFSANALYSIS, ("all",)),
}


def _unreadable_root_said(out, copy_lcn, idx, root_lcn):
    """A statement naming the checkpoint copy (its LCN), root `idx`, that it cannot be read, and the LCN its
    reference holds."""
    return [s for s in _statements(out) if _lcn_re(copy_lcn).search(s) and _root_named(s, idx)
            and re.search(r"(?i)\bcannot be read\b", s) and _lcn_re(root_lcn).search(s)]


def _eq_said(out, v, in_use):
    """What the readable equivalent says: N205 for the copy in use, N343's statement for the copy not in use."""
    return _n205_said(out, v.geo.lo, 7) if in_use else _n343_said(out, v.geo.hi, 7)


_K1 = [(s, f) for s in sorted(_K1_SHAPES) for f in sorted(_K1_FORMS)]


@pytest.mark.parametrize("shape,form", _K1, ids=["%s-%s" % p for p in _K1])
def test_n371_a_root_lcn_too_large_to_seek_is_reported_as_the_readable_equivalent_is(vol, shape, form):
    which, seal, equivalent, in_use = _K1_SHAPES[shape]
    tool, args = _K1_FORMS[form]
    lcn = getattr(vol.geo, which)
    saved = _snapshot(vol)
    equivalent(vol)                                  # the same root, readable but not matching its digest
    rc_eq, out_eq, tb_eq = _run_whole(vol, tool, *args)
    _fx(not tb_eq and rc_eq in (0, 2), "%s on the readable equivalent: rc=%d" % (form, rc_eq) + _ctx(vol, rc_eq, out_eq))
    said_eq = bool(_eq_said(out_eq, vol, in_use))
    _restore(vol, saved)
    root_lcn = plant_root_lcn_huge(vol, lcn, 7, seal)
    rc, out, tb = _run_whole(vol, tool, *args)
    _assert_no_escape(form, vol, rc, out, tb)
    assert rc == rc_eq, ("%s: exit %d, but %d when the same root is readable and does not match its digest (V-a for "
                         "the copy not in use, N205 for the copy in use)" % (form, rc, rc_eq)) + _ctx(vol, rc, out)
    said = _unreadable_root_said(out, lcn, 7, root_lcn)
    assert bool(said) == said_eq, ("%s must %ssay that root 7 of the checkpoint copy at LCN 0x%x cannot be read, naming "
                                   "the LCN its reference holds (0x%x), as it %ssays the readable equivalent"
                                   % (form, "" if said_eq else "not ", lcn, root_lcn, "" if said_eq else "not ")) \
        + _ctx(vol, rc, out)


@pytest.mark.parametrize("shape,form", _K1, ids=["%s-%s" % p for p in _K1])
def test_n371_control_the_readable_equivalent_is_v_a_or_n205(vol, shape, form):
    """The oracle of the RED above, pinned: on the readable equivalent the copy not in use is V-a (the bootstrap-only
    commands keep the undamaged exit code and say nothing; `summary`, `fastsummary`, `integrity`, refsanalysis
    `summary`, `supb`, `supb --verify` and `deleted` (N578: its comparison reads that copy) say it and exit 2; refsanalysis `all` too since wave E step E1c -- N209: it
    returns its sections' most serious result, and its `summary` and `supb` sections exit 2 here; it exited 0) and
    the copy in use is N205 (every command says it and exits 2)."""
    _which, _seal, equivalent, in_use = _K1_SHAPES[shape]
    tool, args = _K1_FORMS[form]
    rc0, _out0, _tb0 = _run_whole(vol, tool, *args)
    equivalent(vol)
    rc, out, tb = _run_whole(vol, tool, *args)
    said = bool(_eq_said(out, vol, in_use))
    if in_use:
        assert not tb and rc == 2 and said, "%s (rc=%d)" % (form, rc) + _ctx(vol, rc, out)
    elif form in ("fd-summary", "fd-fastsummary", "fd-integrity", "fd-integrity-checksums", "ra-summary", "ra-supb",
                  "ra-supb-v", "ra-supb-verify", "ra-all", "fd-deleted"):      # N578: deleted's comparison reads the copy
        assert not tb and rc == 2 and said, "%s (rc=%d)" % (form, rc) + _ctx(vol, rc, out)
    elif form == "ra-chkp-verify" and shape == "flipbit-not-in-use":
        # N580 (O3): `--verify` checks the other copy's self-checksum, which this shape breaks (exit 2); that copy's root
        # failure stays `supb --verify`'s, so it is not said here
        assert not tb and rc == 2 and not said, "%s (rc=%d)" % (form, rc) + _ctx(vol, rc, out)
    else:
        assert not tb and rc == rc0 and not said, "%s: %d -> %d" % (form, rc0, rc) + _ctx(vol, rc, out)


# --- the superblock's checkpoint reference too large to read ---

_READERR_KEEP = ("ra-supb", "ra-supb-v")     # bare `supb` lists the copy and keeps its exit code (G2c2 open item 4)


# `_st_s1` (C2 ST-S1's RED mark for the nodes B15's decided output changed) removed in step C2, area supb


# RED 1.13.2 B15 (C2 ST-S1 c) on the _READERR_KEEP forms: the out-of-range reference is in all three copies, so no
# superblock copy is valid (row 8): decision 26 reads the primary with its finding and every command exits 2 (the strict
# xfail marks removed: fixed in step C2, area supb)
_K1_FORMS_ST_S1 = sorted(_K1_FORMS)
_READERR_SAY = ("fd-summary", "fd-fastsummary", "fd-integrity", "fd-integrity-checksums", "ra-summary")
_READERR_REF = 0x7FFFFFFFFFFFFFFF


def _copy_unreadable_said(out, lcn):
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and re.search(r"(?i)\bcould not be read\b", s)]


@pytest.mark.parametrize("form", _K1_FORMS_ST_S1)
def test_n371_a_superblock_checkpoint_reference_too_large_to_read_is_a_recorded_skip(vol, form):
    tool, args = _K1_FORMS[form]
    rc0, out0, tb0 = _run_whole(vol, tool, *args)
    _fx(not tb0 and not _copy_unreadable_said(out0, _READERR_REF), "%s on the undamaged volume" % form
        + _ctx(vol, rc0, out0))
    plant_supb_ref(vol, _READERR_REF)
    rc, out, tb = _run_whole(vol, tool, *args)
    _assert_no_escape(form, vol, rc, out, tb)
    if form in _READERR_KEEP:
        # C2 ST-S1 (c): no copy is valid -> decision 26's finding, exit 2 in every command (was rc == rc0)
        assert rc == 2, "%s: no superblock copy is valid: exit 2 (decision 26), rc=%d" % (form, rc) + _ctx(vol, rc, out)
        return
    assert rc == 2, "%s must exit 2: the copy that could not be read is a recorded skip (rc=%d)" % (form, rc) \
        + _ctx(vol, rc, out)
    if form in _READERR_SAY:
        assert _copy_unreadable_said(out, _READERR_REF), ("%s must say that the checkpoint copy at LCN 0x%x could not "
                                                          "be read" % (form, _READERR_REF)) + _ctx(vol, rc, out)


# --- a file system that cannot hold the offset (the critic's K-6), the same on every host ---
# Measured on the gate host (ext4 under overlayfs, 4 KiB blocks): a seek to 2**44 - 4096 succeeds, one byte further
# fails with OSError EINVAL before any I/O. tmpfs (/dev/shm, measured) accepts the same seek and reads 0 bytes, as any
# file system with a larger offset limit does. SEEK_DATA / SEEK_HOLE past the end of the file give ENXIO on both, so
# only the plain seek depends on the host. `_run_refusing` runs the tool with that seek modelled in its own process:
# every `open(<image>, "rb")` returns a real BufferedReader whose `seek` to an offset past _FS_MAX_OFFSET (and at most
# 2**63 - 1, where CPython's own error comes first) raises OSError(EINVAL) before any I/O, as ext4's lseek does. The
# tools read the image only through `open(path, "rb")` (no os.pread, mmap or raw fd read; the hole queries' own fd is
# answered by the host as above) and start no child process. A later change that reads the planted copy another way
# is not a silent pass: the node requires the model to have refused the copy's offset (a fixture error otherwise).
_FS_MAX_OFFSET = (1 << 44) - 4096

_REFUSING_FS = r'''
import builtins, errno, io, os, runpy, sys
image, limit, log, tool = os.path.realpath(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
sys.argv = sys.argv[4:]
sys.path[0] = os.path.dirname(os.path.realpath(tool))
real_open = builtins.open


def note(line):
    with real_open(log, "a") as fh:
        fh.write(line + "\n")


class RefusingReader(io.BufferedReader):
    def seek(self, off, whence=0):
        if whence == 0:
            target = off
        elif whence == 1:
            target = self.tell() + off
        else:
            target = os.fstat(self.fileno()).st_size + off
        if limit < target <= (1 << 63) - 1:
            note("refused 0x%x" % target)
            raise OSError(errno.EINVAL, os.strerror(errno.EINVAL))
        return super().seek(off, whence)


def refusing_open(file, mode="r", buffering=-1, *args, **kwargs):
    if mode == "rb" and buffering == -1 and not args and not kwargs and isinstance(file, str) \
            and os.path.realpath(file) == image:
        raw = io.FileIO(file, "r")
        size = os.fstat(raw.fileno()).st_blksize
        note("opened")
        return RefusingReader(raw, size if size > 1 else io.DEFAULT_BUFFER_SIZE)
    return real_open(file, mode, buffering, *args, **kwargs)


builtins.open = refusing_open
runpy.run_path(tool, run_name="__main__")
'''


def _run_refusing(v, tool, *args):
    """`_run_whole` with the image served by a file system that cannot hold an offset past _FS_MAX_OFFSET, whatever
    this host's file system is: (rc, stdout + stderr, traceback?, [refused offset, ...]). A run that did not open
    the image through the model is a fixture error, never a pass."""
    log = os.path.join(os.path.dirname(v.path), "refusing_fs.log")
    _fx(not os.path.exists(log), "a stale %s" % log)
    cmd = [sys.executable, "-B", "-c", _REFUSING_FS, v.path, str(_FS_MAX_OFFSET), log, tool, v.path] + list(args) \
        + list(v.geo.cli)
    try:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=_AB.TIMEOUT, cwd=os.path.dirname(v.path))
        except subprocess.TimeoutExpired:
            raise RedFixtureError("timeout: %s %s" % (tool, " ".join(args)))
        lines = []
        if os.path.exists(log):
            with open(log) as fh:
                lines = fh.read().split()
    finally:
        if os.path.exists(log):
            os.unlink(log)
    _fx("opened" in lines, "%s %s did not open the image through the refusing file system" % (tool, " ".join(args)))
    refused = [int(x, 16) for x in lines if x.startswith("0x")]
    return r.returncode, r.stdout + "\n" + r.stderr, "Traceback (most recent call last)" in r.stderr, refused


_K6_REF = 1 << 38


def _k6_offset(v):
    """The byte offset of the K-6 plant's copy, checked against the model: past its largest offset, the image below."""
    off = v.geo.ps + _K6_REF * CS
    _fx(os.path.getsize(v.path) <= _FS_MAX_OFFSET < off <= _MAX_OFF, "the K-6 copy at 0x%x, the image 0x%x bytes"
        % (off, os.path.getsize(v.path)))
    return off


@pytest.mark.parametrize("form", _K1_FORMS_ST_S1)
def test_n371_control_a_superblock_reference_this_host_cannot_read_is_a_recorded_skip(vol, form):
    """The critic's K-6 plant (`readerr2_hi`): a reference at LCN 2**38, whose offset (about 2**50) a file system
    that cannot hold it refuses with OSError (EINVAL) -- the same condition by another cause, already handled: the
    oracle of the RED above. The file system is modelled in the tool's process (`_run_refusing`), so the node runs on
    every host; the planted copy's offset must be refused in the run."""
    tool, args = _K1_FORMS[form]
    off = _k6_offset(vol)
    rc0, _out0, _tb0, refused0 = _run_refusing(vol, tool, *args)
    _fx(not refused0, "%s refused %r on the undamaged volume" % (form, refused0))
    plant_supb_ref(vol, _K6_REF)
    rc, out, tb, refused = _run_refusing(vol, tool, *args)
    _fx(off in refused, "%s: the planted copy's offset 0x%x was never refused (%r)" % (form, off, refused))
    assert not tb and rc != 1, form + _ctx(vol, rc, out)
    assert rc == 2, form + _ctx(vol, rc, out)    # C2 ST-S1 (c): decision 26, every form (was rc == rc0 for _READERR_KEEP)
    if form in _READERR_SAY:
        assert _copy_unreadable_said(out, _K6_REF), form + _ctx(vol, rc, out)


# --- export metadata: two more handlers of the class (`_source_pin`, the export's own reads) ---

_EXPORT_SHAPES = ["hugeroot-not-in-use", "superblock-reference"]


@IMAGE_ONLY                 # the synthetic volume's Object Table is empty: its bundle is refused as EMPTY
@pytest.mark.parametrize("shape", _EXPORT_SHAPES)
def test_n371_export_metadata_reads_past_an_offset_too_large_to_seek(vol, shape, tmp_path):
    saved = _snapshot(vol)
    if shape == "superblock-reference":
        rc_eq = 2                      # a recorded skip, as for every bootstrapping command (the RED above)
    else:
        plant_root_failure_on(vol, vol.geo.hi, 7)
        b0 = str(tmp_path / "eq")
        rc_eq, _o, _e = _run_split(FOREFST, vol.path, "export", "metadata", b0, cwd=str(tmp_path), cli=vol.geo.cli)
        _fx(rc_eq in (0, 2) and os.path.exists(os.path.join(b0, "manifest.json")), "the equivalent's export")
        _restore(vol, saved)
    if shape == "superblock-reference":
        plant_supb_ref(vol, _READERR_REF)
    else:
        plant_root_lcn_huge(vol, vol.geo.hi, 7, True)
    b = str(tmp_path / "bundle")
    rc, out, tb = _run_whole(vol, FOREFST, "export", "metadata", b)
    _assert_no_escape("export metadata", vol, rc, out, tb)
    assert rc == rc_eq and os.path.exists(os.path.join(b, "manifest.json")), \
        "export metadata: rc=%d (the readable equivalent: %d), bundle written: %s" \
        % (rc, rc_eq, os.path.exists(os.path.join(b, "manifest.json"))) + _ctx(vol, rc, out)


# --- the guard itself, and the hole query ---

def _syn_file(tmp_path):
    p = str(tmp_path / "target.raw")
    _AB._build_synthetic(p)
    return p


def test_n371_the_shared_guard_raises_an_oserror_for_an_offset_past_2_63(tmp_path):
    p = _syn_file(tmp_path)
    assert hasattr(F, "_seek_read"), "forefst has no shared seek-and-read guard (`_seek_read`)"
    with open(p, "rb") as fh:
        try:
            F._seek_read(fh, _MAX_OFF + 1, 16)
            got = None
        except Exception as e:          # noqa: BLE001 -- the type is what is asserted
            got = e
    assert isinstance(got, OSError), "an offset past 2**63 - 1 must raise an OSError (a failed read): %r" % (got,)
    assert isinstance(got, ValueError), ("and stay a ValueError, as CPython's own error was, so a handler that caught "
                                         "that keeps catching it: %r" % (got,))
    assert re.search(r"(?i)0x%x\b" % (_MAX_OFF + 1), str(got)), "the message names the offset: %r" % str(got)
    with open(p, "rb") as fh:
        assert F._seek_read(fh, CS * 0x1E, 4) == b"SUPB", "an ordinary offset is read as before"


def test_n371_control_cpython_raises_valueerror_for_a_seek_past_2_63(tmp_path):
    """The cause, measured on the gate's interpreter: a buffered file's seek(2**63) raises ValueError (not OSError,
    not OverflowError), and 2**63 - 1 fails with OSError or reads nothing (host-dependent)."""
    p = _syn_file(tmp_path)
    with open(p, "rb") as fh:
        with pytest.raises(ValueError):
            fh.seek(_MAX_OFF + 1)
        try:
            fh.seek(_MAX_OFF)
            got = fh.read(1)
        except OSError as e:
            got = e
        assert got == b"" or isinstance(got, OSError), got


def _hole_query(fn, p, start, n):
    fd = os.open(p, os.O_RDONLY)
    try:
        return fn(fd, start, start + n)
    except Exception as e:              # noqa: BLE001 -- returned for the plain assert
        return e
    finally:
        os.close(fd)


@pytest.mark.parametrize("fn", ["_hole_bytes_in", "_hole_ranges_in"])
def test_n371_the_hole_query_answers_for_an_offset_past_2_63_as_past_the_image_end(fn, tmp_path):
    p = _syn_file(tmp_path)
    f = getattr(F, fn)
    near = _hole_query(f, p, _MAX_OFF + 1 - 2 * CS, CS)       # past the image end, below the limit
    _fx(not isinstance(near, Exception), "%s below the limit raised %r" % (fn, near))
    got = _hole_query(f, p, _MAX_OFF + 1, CS)
    assert not isinstance(got, Exception), "%s raised %r for an offset past 2**63 - 1" % (fn, got)
    want = CS if fn == "_hole_bytes_in" else [(_MAX_OFF + 1, _MAX_OFF + 1 + CS)]
    assert got == want, "%s: %r (past the image end it answers %r)" % (fn, got, near)


@pytest.mark.parametrize("fn", ["_hole_bytes_in", "_hole_ranges_in"])
def test_n371_control_the_hole_query_past_the_image_end_below_the_limit(fn, tmp_path):
    """Past the image end, below 2**63: os.lseek gives ENXIO and the query answers "hole / past the end"."""
    p = _syn_file(tmp_path)
    start = _MAX_OFF + 1 - 2 * CS
    got = _hole_query(getattr(F, fn), p, start, CS)
    assert got == (CS if fn == "_hole_bytes_in" else [(start, start + CS)]), got


# --- the class: an AST lint over both tools ---

_GUARD = "_seek_read"
_NARROW = {"OSError", "OverflowError", "IOError", "EnvironmentError", "PermissionError"}
_WIDE = {"ValueError", "Exception", "BaseException", "<bare>"}


def _tname(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return n.attr
    return "?"


def _try_types(t):
    out = set()
    for h in t.handlers:
        if h.type is None:
            out.add("<bare>")
        elif isinstance(h.type, ast.Tuple):
            out |= {_tname(e) for e in h.type.elts}
        else:
            out.add(_tname(h.type))
    return out


def _is_raw_seek(call, fn):
    """A `.seek(x)` whose offset is not a constant (a constant cannot be too large), outside the guard itself."""
    return (isinstance(call.func, ast.Attribute) and call.func.attr == "seek" and fn != _GUARD and call.args
            and not isinstance(call.args[0], ast.Constant))


_TOOL_MODULES = ("forefst", "refsanalysis")
_MODULE_NAMES = ("F", "_forefst", "forefst")    # the module names the lint followed before it resolved aliases (kept)


def _aliases(trees):
    """The names that stand for a tool module or for a function, over all `trees` (the lint matches calls by name
    across the sources, so the aliases are pooled the same way): (module names, {alias: {original name, ...}}).
    module names -- every name an `import forefst` / `import forefst as A` binds, anywhere in a source, plus F,
                    _forefst and forefst;
    aliases      -- `from forefst import x as y` (anywhere in a source), and a module-level `y = x` or `y = A.x` (A a
                    module name), followed through chains (`z = y`).
    Not followed: getattr, a function passed as an argument or stored in a container, an alias assigned inside a
    function body."""
    mods = set(_MODULE_NAMES)
    for tree in trees:
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.asname or a.name for a in n.names if a.name in _TOOL_MODULES}
    direct = {}
    for tree in trees:
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module in _TOOL_MODULES:
                for a in n.names:
                    if a.asname and a.asname != a.name:
                        direct.setdefault(a.asname, set()).add(a.name)
        for n in tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                y, v = n.targets[0].id, n.value
                if isinstance(v, ast.Name) and v.id != y:
                    direct.setdefault(y, set()).add(v.id)
                elif isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id in mods \
                        and v.attr != y:
                    direct.setdefault(y, set()).add(v.attr)
    resolved = {}
    for y in direct:
        seen, todo = set(), [y]
        while todo:
            for x in direct.get(todo.pop(), ()):
                if x != y and x not in seen:
                    seen.add(x)
                    todo.append(x)
        resolved[y] = seen
    return mods, resolved


def _seek_class(sources):
    """The N371 class over `sources` ({tag: source text}): (sites, narrow, guarded).
    sites   {(tag, function, try line): {(tag, seek line)}} -- a try whose handlers catch a failed read (OSError,
            OverflowError, ...) but not ValueError (nor Exception, BaseException, a bare except), reached -- in its own
            body or up the call chain (calls by name, transitively; a call through an alias, `_aliases`, counts as a
            call of the alias and of each name it stands for) -- by a raw seek;
    narrow  {(tag, function): [try line, ...]} -- every such try, reached or not;
    guarded {(tag, function, try line)} -- the narrow tries whose body reaches the guard `_seek_read`."""
    trees = {tag: ast.parse(src) for tag, src in sources.items()}
    mods, aliases = _aliases(list(trees.values()))
    events = {}                                   # (tag, fn) -> [(kind, name/line, tries innermost first)]
    narrow = {}

    def walk(node, key, tries):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            key = (key[0], node.name)
            tries = []
            events.setdefault(key, [])
        if isinstance(node, ast.Try):
            ts = _try_types(node)
            if ts & _NARROW and not ts & _WIDE:
                narrow.setdefault(key, []).append(node.lineno)
            for ch in node.body:
                walk(ch, key, [(node.lineno, _try_types(node))] + tries)
            for ch in node.handlers + node.orelse + node.finalbody:
                walk(ch, key, tries)
            return
        if isinstance(node, ast.Call):
            name = None
            if _is_raw_seek(node, key[1]):
                events.setdefault(key, []).append(("seek", node.lineno, tries))
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id in mods:
                name = node.func.attr
            if name is not None:
                for n in [name] + sorted(aliases.get(name, ())):
                    events.setdefault(key, []).append(("call", n, tries))
        for ch in ast.iter_child_nodes(node):
            walk(ch, key, tries)
    for tag, tree in trees.items():
        walk(tree, (tag, "<module>"), [])
    byname = {}
    for key in events:
        byname.setdefault(key[1], []).append(key)

    def first(tries):
        for ln, ts in tries:
            if ts & _WIDE:
                return ("wide", ln)
            if ts & _NARROW:
                return ("narrow", ln)
        return None
    escapes = {k: set() for k in events}
    uses_guard = {k: False for k in events}
    for key, evs in events.items():
        for kind, what, tries in evs:
            if kind == "seek" and first(tries) is None:
                escapes[key].add((key[0], what))
            if kind == "call" and what == _GUARD:
                uses_guard[key] = True
    changed = True
    while changed:
        changed = False
        for key, evs in events.items():
            for kind, what, tries in evs:
                if kind != "call":
                    continue
                for callee in byname.get(what, ()):
                    if first(tries) is None and not escapes[callee] <= escapes[key]:
                        escapes[key] |= escapes[callee]
                        changed = True
                    if uses_guard[callee] and not uses_guard[key]:
                        uses_guard[key] = True
                        changed = True
    sites, guarded = {}, set()
    for key, evs in events.items():
        for kind, what, tries in evs:
            c = first(tries)
            if c is None or c[0] != "narrow":
                continue
            site = (key[0], key[1], c[1])
            if kind == "seek":
                sites.setdefault(site, set()).add((key[0], what))
            else:
                for callee in byname.get(what, ()):
                    if escapes[callee]:
                        sites.setdefault(site, set()).update(escapes[callee])
                    if what == _GUARD or uses_guard[callee]:
                        guarded.add(site)
    return sites, narrow, guarded


def _tool_sources():
    out = {}
    for tag, path in (("fd", FOREFST), ("ra", REFSANALYSIS)):
        with open(path, encoding="utf-8") as fh:
            out[tag] = fh.read()
    return out


# The critic's list (GOLDEN_G2c2_critic.md K-1): the function of each handler and how many of its handlers are on the
# list. alloc_capacity's try holds `f.seek(0, 2)` only (the image size: no on-disk offset), so it needs no guard.
_CRITIC = {("fd", "_read_gpt_header"): 1, ("fd", "parse_supb"): 1, ("fd", "_chkp_root_failures"): 1,
           ("fd", "checkpoint_select"): 1, ("fd", "alloc_capacity"): 1, ("fd", "_iter_msb_clusters"): 1,
           ("fd", "_slack_recover"): 1, ("fd", "_scan_backup_copies"): 3, ("fd", "_walk_btree_pages"): 1,
           ("fd", "cmd_integrity"): 1, ("fd", "cmd_export_metadata"): 5, ("ra", "cmd_boot"): 1,
           ("ra", "_alloc_walk_tier"): 2}
_NO_GUARD_NEEDED = {("fd", "alloc_capacity")}


def test_n371_control_the_lint_emits_its_counterexample():
    """The instrument can see the class: a raw seek in a narrow handler, directly and through a callee, is a site; the
    guard, a constant offset, a ValueError handler and an Exception handler are not."""
    src = '''
def _seek_read(f, off, n):
    f.seek(off); return f.read(n)
def callee(f, x):
    f.seek(x * 4096)
def direct(f, x):
    try:
        f.seek(x)
    except (OSError, OverflowError) as e:
        x = e
def chained(f, x):
    try:
        callee(f, x)
    except OSError as e:
        x = e
def guarded(f, x):
    try:
        _seek_read(f, x, 1)
    except (OSError, OverflowError) as e:
        x = e
def constant(f):
    try:
        f.seek(0, 2)
    except OSError as e:
        x = e
def wide(f, x):
    try:
        f.seek(x)
    except Exception as e:
        x = e
def valueerror(f, x):
    try:
        callee(f, x)
    except (OSError, ValueError) as e:
        x = e
'''
    sites, narrow, guarded = _seek_class({"t": src})
    assert {(s[1]) for s in sites} == {"direct", "chained"}, sites
    assert {k[1] for k in narrow} == {"direct", "chained", "guarded", "constant"}, narrow
    assert {s[1] for s in guarded} == {"guarded"}, guarded


# N6 (review 1) = T4 (review 2): the tools call functions through aliases -- refsanalysis `from forefst import
# parse_supb as _forefst_parse_supb` (and `parse_vbr`, `validate_image`), forefst's own module-level
# `_forefst_parse_supb = parse_supb`, `import forefst as _forefst`. A raw seek reached only through such an alias must
# be a site, and the guard reached only through one must count as the guard. In each synthetic source below the raw
# seek (`reader`, in the `lib` source) is reached only through the alias the case names.
_ALIAS_LIB = '''
def _seek_read(f, off, n):
    f.seek(off)
    return f.read(n)
def reader(f, x):
    f.seek(x * 4096)
    return f.read(1)
'''
_ALIAS_USERS = {
    "from-import-as": '''
from forefst import reader as _forefst_reader, _seek_read as _guard
def aliased(f, x):
    try:
        return _forefst_reader(f, x)
    except (OSError, OverflowError) as e:
        x = e
def guarded(f, x):
    try:
        return _guard(f, x, 1)
    except OSError as e:
        x = e
''',
    "import-module-as": '''
import forefst as _tool
def aliased(f, x):
    try:
        return _tool.reader(f, x)
    except OSError as e:
        x = e
def guarded(f, x):
    try:
        return _tool._seek_read(f, x, 1)
    except OSError as e:
        x = e
''',
    "module-assignment": '''
_rd = reader
_rd_again = _rd
_guard = _seek_read
def aliased(f, x):
    try:
        return _rd_again(f, x)
    except OSError as e:
        x = e
def guarded(f, x):
    try:
        return _guard(f, x, 1)
    except OSError as e:
        x = e
''',
}


@pytest.mark.parametrize("form", sorted(_ALIAS_USERS))
def test_n371_control_the_lint_follows_import_aliases(form):
    """The lint follows a call made through an alias: `from forefst import x as y`, `import forefst as A` + `A.x`, and a
    module-level `y = x` (also through a chain, `z = y`). The raw seek reached only through the alias is a site; the
    guard reached only through one is the guard."""
    user = _ALIAS_USERS[form]
    if form == "module-assignment":
        sources = {"lib": _ALIAS_LIB + user}             # forefst's own form: the alias beside the function
    else:
        sources = {"lib": _ALIAS_LIB, "user": user}      # refsanalysis' form: the alias in the importing module
    sites, narrow, guarded = _seek_class(sources)
    assert {s[1] for s in sites} == {"aliased"}, "%s: a raw seek reached only through an alias: %r" % (form, sites)
    assert {k[1] for k in narrow} == {"aliased", "guarded"}, narrow
    assert {s[1] for s in guarded} == {"guarded"}, "%s: the guard reached only through an alias: %r" % (form, guarded)


def test_n371_no_raw_seek_reaches_a_handler_written_for_a_failed_read():
    sites, _narrow, _guarded = _seek_class(_tool_sources())
    listed = ["%s:%d %s <- %s" % (s[0], s[2], s[1], ", ".join("%s:%d" % x for x in sorted(v)))
              for s, v in sorted(sites.items())]
    assert not sites, ("%d handler(s) written for a failed read are reached by a raw seek (an offset past 2**63 - 1 "
                       "raises ValueError there, which they do not catch):\n  " % len(sites)) + "\n  ".join(listed)


def test_n371_each_handler_of_the_critics_list_reads_through_the_guard():
    sites, narrow, guarded = _seek_class(_tool_sources())
    for key, n in sorted(_CRITIC.items()):
        _fx(len(narrow.get(key, ())) >= n, "%s:%s has %d narrow handler(s), the critic lists %d"
            % (key[0], key[1], len(narrow.get(key, ())), n))
    reached = sorted("%s:%s:%d" % s for s in sites if (s[0], s[1]) in _CRITIC)
    assert not reached, "handlers of the critic's list still reached by a raw seek: %r" % reached
    unguarded = sorted("%s:%s:%d" % (k[0], k[1], ln) for k in _CRITIC if k not in _NO_GUARD_NEEDED
                       for ln in narrow[k] if (k[0], k[1], ln) not in guarded)
    assert not unguarded, "handlers of the critic's list that do not read through `_seek_read`: %r" % unguarded


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 2. N372 -- the none-passes text (C1) and an older copy without a root list that also fails (C3)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# C1 (review 1, probe p6), re-measured here: the newest copy (lo, vclock 64) has no root list and passes its
# self-checksum; the older copy (hi, vclock 63) fails its self-checksum. Every bootstrapping command says "no checkpoint
# copy passes its self-checksum (LCN 0xee34): the driver would refuse to mount this volume; this view is read from the
# newest copy (LCN 0xee34, vclock 63) anyway" beside "the newest checkpoint copy (LCN 0x13f8, vclock 64) passes its
# self-checksum, but its root list could not be read ..."; refsanalysis `chkp` ("...; no checkpoint copy passes its
# self-checksum.") and `containers` say the same. C3 (review 1, probe p12): the older copy without a root list ALSO fails
# its self-checksum -- the redundancy list says only "its root list could not be read".

def plant_c1(v, both_fail):
    """lo (the newer copy, vclock 64) without a root list -- passing its self-checksum, or (both_fail) failing it --
    and hi (vclock 63, its root list intact) failing its self-checksum. Checked through checkpoint_select: no copy is
    chosen, the copy in use is hi, lo is no candidate."""
    g = v.geo
    plant_no_root_list(v, g.lo)
    if both_fail:
        v.flip(v.at(g.lo, 0x400))
        _fx(v.verifies(g.lo) is False, "lo still verifies")
    else:
        _fx(v.verifies(g.lo) is True, "lo does not verify")
    damage_chkp(v, g.hi)
    with open(v.path, "rb") as fh:
        sel = F.checkpoint_select(fh, g.ps, CS, F.parse_supb(fh, g.ps, CS), require_roots=True)
    _fx(sel["chosen"] is None and sel["in_use"]["lcn"] == g.hi and [c["lcn"] for c in sel["cands"]] == [g.hi],
        "the plant is not C1's shape")


_NO_COPY_PASSES = re.compile(r"(?i)\bno checkpoint copy passes its self-checksum\b")


def _c1_each_said(out, v, both_fail):
    """One statement naming BOTH copies, each with why it cannot be used: lo's root list (and, both_fail, its failed
    self-checksum), hi's failed self-checksum."""
    g = v.geo
    hits = []
    for s in _statements(out):
        mlo, mhi = _lcn_re(g.lo).search(s), _lcn_re(g.hi).search(s)
        if not (mlo and mhi):
            continue
        a, b = sorted((mlo.start(), mhi.start()))
        part = {g.lo: None, g.hi: None}
        part[g.lo if a == mlo.start() else g.hi] = s[a:b]
        part[g.hi if a == mlo.start() else g.lo] = s[b:]
        lo_ok = re.search(r"(?i)\broot list\b", part[g.lo]) and (not both_fail or _FAIL.search(part[g.lo]))
        hi_ok = _FAIL.search(part[g.hi]) and re.search(r"(?i)self-checksum", part[g.hi])
        if lo_ok and hi_ok:
            hits.append(s)
    return hits


_C1_FORMS = {"fd-files": (FOREFST, ("files",)), "fd-summary": (FOREFST, ("summary",)),
             "ra-supb": (REFSANALYSIS, ("supb",)), "ra-chkp": (REFSANALYSIS, ("chkp",)),
             "ra-chkp-verify": (REFSANALYSIS, ("chkp", "--verify")), "ra-containers": (REFSANALYSIS, ("containers",))}
_C1 = [(s, f) for s in ("lo-passes", "lo-fails") for f in sorted(_C1_FORMS)]


@pytest.mark.parametrize("shape,form", _C1, ids=["%s-%s" % p for p in _C1])
def test_n372_c1_no_copy_usable_says_which_copies_cannot_be_used_and_why(vol, shape, form):
    tool, args = _C1_FORMS[form]
    both_fail = shape == "lo-fails"
    rc0, out0 = vol.run(tool, *args)
    _fx(not _NO_COPY_PASSES.search(out0) and not _c1_each_said(out0, vol, both_fail), "%s on the undamaged volume"
        % form + _ctx(vol, rc0, out0))
    plant_c1(vol, both_fail)
    rc, out = vol.run(tool, *args)
    _keep(rc == 2, "every command exits 2 (no copy can be used as it is)" + _ctx(vol, rc, out))
    g = vol.geo
    if not both_fail:
        false = [s for s in _statements(out) if _NO_COPY_PASSES.search(s)]
        assert not false, "%s: 'no checkpoint copy passes its self-checksum', but LCN 0x%x passes it: %r" \
            % (form, g.lo, false) + _ctx(vol, rc, out)
    each = _c1_each_said(out, vol, both_fail)
    assert each, ("%s must say, for each copy, why it cannot be used (LCN 0x%x: its root list; LCN 0x%x: its failed "
                  "self-checksum)" % (form, g.lo, g.hi)) + _ctx(vol, rc, out)
    assert not [s for s in each if re.search(r"(?i)\bdriver\b", s)], \
        "a claim about the driver beside a copy without a root list (not read a second time): %r" % each
    newest_old = [s for s in _statements(out) if re.search(r"(?i)\bnewest copy \(LCN 0x0*%x\b" % g.hi, s)]
    assert not newest_old, ("%s calls LCN 0x%x 'the newest copy', but LCN 0x%x has a higher clock: %r"
                            % (form, g.hi, g.lo, newest_old)) + _ctx(vol, rc, out)


@pytest.mark.parametrize("form", sorted(_C1_FORMS))
def test_n372_control_no_copy_passing_with_both_root_lists_keeps_its_text(vol, form):
    """The classic shape (both copies fail their self-checksum, both root lists intact): forefst says 'no checkpoint
    copy passes its self-checksum (...): the driver would refuse to mount this volume' -- unchanged -- and the
    refsanalysis commands say a copy failed; every command exits 2."""
    tool, args = _C1_FORMS[form]
    damage_chkp(vol, vol.geo.lo)
    damage_chkp(vol, vol.geo.hi)
    rc, out = vol.run(tool, *args)
    assert rc == 2, form + _ctx(vol, rc, out)
    if form.startswith("fd-"):
        assert [s for s in _statements(out) if _NO_COPY_PASSES.search(s) and "would refuse to mount" in s], \
            form + _ctx(vol, rc, out)
    else:
        assert [s for s in _statements(out) if _FAIL.search(s) and _lcn_re(vol.geo.lo).search(s)], \
            form + _ctx(vol, rc, out)


def plant_c3(v, how):
    """hi (the older copy) without a root list, and its self-checksum failing (how='fails') or not verifiable
    (how='unverifiable', checksum type 3)."""
    g = v.geo
    plant_no_root_list(v, g.hi)
    if how == "fails":
        v.flip(v.at(g.hi, 0x400))
        _fx(v.verifies(g.hi) is False, "hi still verifies")
    else:
        plant_unknown_type(v, g.hi, 0x58, 0x03)
        _fx(v.verifies(g.hi) is None, "hi's checksum is still verifiable")


_C3_LIST = {"fd-summary": (FOREFST, ("summary",)), "fd-fastsummary": (FOREFST, ("fastsummary",)),
            "fd-integrity": (FOREFST, ("integrity",)), "ra-summary": (REFSANALYSIS, ("summary",))}
_C3 = [(h, f) for h in ("fails", "unverifiable") for f in sorted(_C3_LIST)]


def _c3_checksum_said(out, lcn, how):
    """A statement naming the copy and its self-checksum state, not only its root list."""
    want = (lambda s: _FAIL.search(s) and re.search(r"(?i)self-checksum", s)) if how == "fails" else \
        (lambda s: _CANNOT_VERIFY.search(s) and re.search(r"(?i)checksum", s))
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and want(s)
            and not re.search(r"(?i)^\s*CHKP\b|Checkpoint \[", s)]


@pytest.mark.parametrize("how,form", _C3, ids=["%s-%s" % p for p in _C3])
def test_n372_c3_an_older_copy_without_a_root_list_has_its_checksum_state_listed(vol, how, form):
    tool, args = _C3_LIST[form]
    rc0, out0 = vol.run(tool, *args)
    _fx(rc0 == 0 and not _c3_checksum_said(out0, vol.geo.hi, how), "%s on the undamaged volume" % form
        + _ctx(vol, rc0, out0))
    plant_c3(vol, how)
    rc, out = vol.run(tool, *args)
    _keep(rc == 2 and [s for s in _statements(out) if _lcn_re(vol.geo.hi).search(s)
                       and re.search(r"(?i)\broot list\b", s)], "the root list is listed, exit 2" + _ctx(vol, rc, out))
    assert _c3_checksum_said(out, vol.geo.hi, how), ("%s must list that the older copy (LCN 0x%x) %s, not only that its "
                                                     "root list could not be read"
                                                     % (form, vol.geo.hi, "failed its self-checksum" if how == "fails"
                                                        else "has a checksum that cannot be verified")) \
        + _ctx(vol, rc, out)


_C3_QUIET = {"fd-files": (FOREFST, ("files",)), "fd-search": (FOREFST, ("search", "ok")),
             "ra-files": (REFSANALYSIS, ("files",)), "ra-chkp": (REFSANALYSIS, ("chkp",)),
             "ra-containers": (REFSANALYSIS, ("containers",))}


@pytest.mark.parametrize("form", sorted(_C3_QUIET))
def test_n372_control_c3_is_v_a_for_the_bootstrap_only_commands(vol, form):
    """V-a: the copy is older and not in use; the commands that only read through the copy in use keep their exit
    code."""
    tool, args = _C3_QUIET[form]
    rc0, _out0 = vol.run(tool, *args)
    plant_c3(vol, "fails")
    rc, out = vol.run(tool, *args)
    assert rc == rc0, "%s: %d -> %d" % (form, rc0, rc) + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 3. N375 -- verify-bundle's help (O1, K-4) and `_supb_backup_how` (T3)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# O1 (challenge): `CMD_HELP["verify-bundle"]["notes"]` ("... run `summary` on the bundle for those") is printed by no
# help path: `_render_cmd_help` prints tag/desc/opts/ex. K-4 (critic): the notes and the docstring say "the redundancy
# checks of `summary` and `integrity` (the copies the volume is not read from) are not run"; the view conditions about
# those copies ARE counted (control). T3 (review 2): `_supb_backup_how` takes any falsy cksum_ok, False included, as
# "cannot be verified".

_RUN_SUMMARY = re.compile(r"(?i)\brun `?summary`? on the bundle\b")
_NOT_READ_FROM = re.compile(r"(?i)the copies the volume is not read from")


def _help_outputs(tmp_path):
    """The three help paths: `help verify-bundle`, `<path> help verify-bundle` (CMD_HELP), `<path> verify-bundle -h`."""
    x = str(tmp_path / "nothing")
    out = {}
    for name, argv in (("help", ["help", "verify-bundle"]), ("path-help", [x, "help", "verify-bundle"]),
                       ("-h", [x, "verify-bundle", "-h"])):
        rc, so, se = _run_split(FOREFST, *argv, cwd=str(tmp_path))
        _fx(rc == 0 and "verify-bundle" in so, "%s: rc=%d %s" % (name, rc, se[-500:]))
        out[name] = " ".join(so.split())
    return out


def test_n375_o1_every_help_path_says_to_run_summary_for_what_is_not_checked(tmp_path):
    out = _help_outputs(tmp_path)
    missing = sorted(k for k, t in out.items() if not _RUN_SUMMARY.search(t))
    assert not missing, "help paths that do not tell the user to run `summary` on the bundle: %r\n%r" % (missing, out)


def _k4_texts(tmp_path):
    h = F.CMD_HELP["verify-bundle"]
    out = _help_outputs(tmp_path)
    return {"notes": " ".join(" ".join(h.get("notes") or []).split()), "-h": out["-h"], "path-help": out["path-help"],
            "doc cmd_verify_bundle": " ".join((F.cmd_verify_bundle.__doc__ or "").split()),
            "doc _escalation_texts": " ".join((F._escalation_texts.__doc__ or "").split())}


def test_n375_k4_the_texts_name_what_is_not_checked_precisely(tmp_path):
    texts = _k4_texts(tmp_path)
    bad = sorted(k for k, t in texts.items() if _NOT_READ_FROM.search(t))
    assert not bad, "said not checked, but their view conditions are counted: %r" % {k: texts[k] for k in bad}
    for k in ("notes", "-h", "path-help"):
        t = texts[k]
        assert re.search(r"(?i)redundancy findings", t) and re.search(r"(?i)checkpoint copy not in use", t) \
            and re.search(r"(?i)\bbackup\b", t), "%s must name what is not checked (the redundancy findings of " \
            "`summary` and `integrity`, e.g. a checkpoint copy not in use, a backup copy): %r" % (k, t)


@IMAGE_ONLY
def test_n375_control_a_view_condition_of_the_copy_not_in_use_is_counted(vol, tmp_path):
    """K-4's measurement, pinned: a +0x10/+0x60 divergence on the copy NOT in use (decision 28: a view condition) is
    counted by verify-bundle (exit 2, named) -- so 'the copies the volume is not read from are not checked' is false."""
    plant_clock_divergence(vol, vol.geo.hi, roots=True)
    b = str(tmp_path / "bundle")
    _export_bundle(vol, b)
    rc, out, err = _verify_bundle(b)
    assert rc == 2 and _clock_said(out, vol.geo.hi, CLOCK_OLD), out + err


@IMAGE_ONLY
def test_n375_control_a_backup_superblock_that_fails_is_not_counted(vol, tmp_path):
    """What is NOT counted, pinned on one example the new text gives: a backup superblock copy that fails its
    self-checksum -- verify-bundle PASS, exit 0; `summary` on the bundle exits 2 and names it."""
    lcn = damage_supb(vol, "backup")
    b = str(tmp_path / "bundle")
    _export_bundle(vol, b)
    rc, out, err = _verify_bundle(b)
    assert rc == 0 and re.search(r"(?m)^verify-bundle: PASS\b", out), out + err
    rcs, outs, _errs = _run_split(FOREFST, b, "summary", cwd=str(tmp_path))
    assert rcs == 2 and [s for s in _statements(outs) if _lcn_re(lcn).search(s) and _FAIL.search(s)], outs[-3000:]


def test_n375_t3_supb_backup_how_words_a_failed_copy_as_failed():
    t = F._supb_backup_how(False, "CRC32-C")
    assert not _UNVERIFIED.search(t), "a copy whose self-checksum FAILED is worded as one that cannot be verified: %r" % t
    assert _FAIL.search(t) and "CRC32-C" in t, "it must say the copy failed its self-checksum: %r" % t


def test_n375_control_supb_backup_how_passes_and_cannot_be_verified():
    assert re.search(r"passes its self-checksum \(CRC32-C\)", F._supb_backup_how(True, "CRC32-C"))
    t = F._supb_backup_how(None, "unknown checksum type 0x3")
    assert _CANNOT_VERIFY.search(t) and "0x3" in t and not re.search(r"(?i)\bpasses\b", t), t     # K16: unpadded


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 4. Coverage -- branches of group 2's shared helpers no test pinned (controls: they pass before and after)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

class _RefusingFile:
    """A file object whose seek refuses one offset with OSError(EINVAL), as a file system refuses an offset it cannot
    hold: the host-independent form of the critic's K-6 plant."""

    def __init__(self, fh, bad):
        self._fh, self._bad = fh, bad

    def seek(self, off, whence=0):
        if whence == 0 and off == self._bad:
            raise OSError(errno.EINVAL, "Invalid argument")
        return self._fh.seek(off, whence)

    def __getattr__(self, name):
        return getattr(self._fh, name)


def test_cov_root_check_read_error_branch_host_independent(tmp_path):
    p = _syn_file(tmp_path)
    g = _AB.SYN
    with open(p, "rb") as fh:
        lcns = F.parse_supb(fh, g.ps, CS)
        _fx(lcns == [g.lo, g.hi], "checkpoint list %r" % lcns)
        sel = F.checkpoint_select(_RefusingFile(fh, g.ps + g.hi * CS), g.ps, CS, lcns, require_roots=True)
    c = {x["lcn"]: x for x in sel["copies"]}[g.hi]
    assert isinstance(c["read_error"], OSError), c["read_error"]
    res, text = F._root_check(c)
    assert res == "WARN" and re.search(r"(?i)cannot be verified: this copy could not be read", text), (res, text)
    conds = [(k, lvl, t) for k, lvl, t in F._checkpoint_conditions(sel, CS) if _lcn_re(g.hi).search(t)]
    # C2 ST-B1 (the lead, 2026-10-23): Q25 (N394) makes a checkpoint copy that cannot be read a "view" condition
    # (exit 2 in every command); the level was "redundancy" before step C2. The node's other checks are unchanged.
    assert [x for x in conds if x[1] == "view" and "could not be read" in x[2]], conds
    assert sel["in_use"]["lcn"] == g.lo


def test_cov_root_check_read_error_branch_k6_plant(vol):
    """The critic's K-6 plant (`readerr2_hi`) through the CLI: `supb --verify`'s roots row of that copy is WARN, 'this
    copy could not be read', exit 2. The file system that cannot hold the offset is modelled in the tool's process
    (`_run_refusing`), so the node runs on every host."""
    off = _k6_offset(vol)
    plant_supb_ref(vol, _K6_REF)
    rc, out, tb, refused = _run_refusing(vol, REFSANALYSIS, "supb", "--verify")
    _fx(not tb, "the tool crashed (a crash is never the defect under test):\n" + out[-3000:])     # as Vol.run
    _fx(off in refused, "the planted copy's offset 0x%x was never refused (%r)" % (off, refused))
    # wave E step E1c (N377): the details column wraps; the row is read with its continuation lines
    from conftest import unwrap_table_rows
    rows = [ln for ln in unwrap_table_rows(out).splitlines() if re.match(r"^chkp_2_roots\s+WARN\s", ln)]
    assert rc == 2 and rows and re.search(r"(?i)this copy could not be read", rows[0]), _ctx(vol, rc, out)


def test_cov_role_word_newest_on_n361s_shape(vol):
    """N361 (b): the newer copy whose root list cannot be read is 'newest' on summary's CHKP line."""
    _n361b_plant(vol, "verifies")
    rc, out = vol.run(FOREFST, "summary")
    line = [ln for ln in out.splitlines() if re.match(r"^\s*CHKP\b", ln) and _lcn_re(vol.geo.lo).search(ln)]
    assert rc == 2 and line and re.search(r"vclock=%d, newest\b" % CLOCK_NEW, line[0]), _ctx(vol, rc, out)


def _n362_reason_plant(v, reason):
    """Root 7's reference in the copy NOT in use (hi), re-sealed: 'nolcn' -- its four LCN slots 0; 'digestlen' -- its
    digest length 0x40 (past the 0x30-byte reference); 'pastpage' -- its offset-table entry points 8 bytes before the
    end of the page, so the reference runs past it; 'offtable' -- the copy's root offset table (+0x94) starts 4 bytes
    before the end of the page, so the entries of roots 0xC, 7 and 8 lie past it (the copy keeps a root list: one
    empty entry per root)."""
    g = v.geo
    blk = v.block(g.hi)
    olb = F.le32(blk, 0x94) if F.le32(blk, 0x78) & 0x200 else 0x94
    ro = _root_ref_offset(blk, 7)
    page = F._page_bytes(CS)

    def edit(b):
        if reason == "nolcn":
            b[ro:ro + 32] = b"\0" * 32
        elif reason == "digestlen":
            struct.pack_into("<I", b, ro + 0x24, 0x40)
        elif reason == "offtable":
            _fx(F.le32(b, 0x78) & 0x200, "the copy's root offset table is not indirect")
            struct.pack_into("<I", b, 0x94, page - 4)
        else:
            struct.pack_into("<I", b, olb + 4 * 7, page - 8)
    v.reseal(g.hi, edit, CHKP_DESC)
    with open(v.path, "rb") as fh:
        sel = F.checkpoint_select(fh, g.ps, CS, F.parse_supb(fh, g.ps, CS), require_roots=True)
    c = {x["lcn"]: x for x in sel["copies"]}[g.hi]
    _fx(c["root_unchecked"] == ([0xC, 7, 8] if reason == "offtable" else [7]) and not c["root_fail"]
        and sel["in_use"]["lcn"] == g.lo, "%s: unchecked %r, failing %r" % (reason, c["root_unchecked"],
                                                                            c["root_fail"]))
    return dict(c["root_unchecked_why"])[7]


_N362_REASONS = {"nolcn": r"its reference holds no LCN",
                 "digestlen": r"its reference's digest length \(64 bytes\) runs past the reference",
                 # LB47 (wave B part 3, the sanctioned reader edit): N369 / E118 -- the checkpoint record is one cluster,
                 # so the reason names the record ("runs past the checkpoint record"), not the page; still stated
                 "pastpage": r"its reference runs past the checkpoint record",
                 "offtable": r"this copy's table of root offsets runs past the checkpoint record"}


@pytest.mark.parametrize("reason", sorted(_N362_REASONS))
def test_cov_n362_other_reasons_a_root_cannot_be_verified(vol, reason):
    why = _n362_reason_plant(vol, reason)
    assert re.search(_N362_REASONS[reason], why), why
    rc, out = vol.run(FOREFST, "summary")
    said = [s for s in _statements(out) if _lcn_re(vol.geo.hi).search(s) and _root_named(s, 7)
            and _CANNOT_VERIFY.search(s) and re.search(_N362_REASONS[reason], s)]
    assert rc == 2 and said, _ctx(vol, rc, out)


# RED 1.13.2 B15 (C2 ST-S1 a2): the plant aimed at the copy read after the primary fails moves to end-2 (Q3); the
# tool reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_cov_supb_backup_how_cannot_be_verified_branch(vol):
    """B1's other branch: the primary fails its self-checksum and end-2's checksum cannot be verified (type 3);
    the volume is read from end-2, and both forefst's statement and refsanalysis `supb`'s NOTE say its checksum
    cannot be verified -- never that it passes. C2 ST-S1 (a2): end-2 is the copy read after a primary fallback (Q3);
    the plant was on end-3, the tool's first backup before B15."""
    damage_supb(vol, "primary")
    plant_unknown_type(vol, vol.geo.backups[1], 0x78, 0x03)
    b0 = vol.geo.backups[1]
    for tool, args in ((FOREFST, ("files",)), (REFSANALYSIS, ("supb",))):
        rc, out = vol.run(tool, *args)
        said = [s for s in _statements(out) if _lcn_re(b0).search(s) and re.search(r"(?i)\bread from\b", s)
                and re.search(r"(?i)its checksum cannot be verified \(unknown checksum type 0x3\)", s)]   # K16 (1.14.0)
        assert rc == 2 and said and not [s for s in said if re.search(r"(?i)passes its self-checksum", s)], \
            _ctx(vol, rc, out)


def test_matchers():
    """The oracles above, on hand-written lines (no tool run)."""
    s = ("  [WARN] the superseded checkpoint copy at LCN 0xee34 (vclock 63): root 7 (Container Table) cannot be read "
         "(LCN 0x1000000000004800: offset 0x1000000000004801000000 is beyond the largest file offset)")
    assert _unreadable_root_said(s, 0xee34, 7, 0x1000000000004800)
    assert not _unreadable_root_said(s.replace("cannot be read", "does not match"), 0xee34, 7, 0x1000000000004800)
    assert not _unreadable_root_said(s, 0x13f8, 7, 0x1000000000004800)
    assert _CPYTHON_SEEK.search("forefst: error: cannot fit 'int' into an offset-sized integer")
    g = _AB.IMG

    class _V:
        geo = g
    c1 = ("[forefst] WARNING: no checkpoint copy both passes its self-checksum and has a root list that can be read: "
          "the copy at LCN 0x13f8 (vclock 64) passes its self-checksum, but its root list could not be read (no root "
          "references); the copy at LCN 0xee34 (vclock 63) failed its self-checksum (CRC32-C); this view is read from "
          "the copy at LCN 0xee34 (vclock 63) anyway")
    assert _c1_each_said(c1, _V, False) and not _c1_each_said(c1, _V, True)
    old = ("[forefst] WARNING: no checkpoint copy passes its self-checksum (LCN 0xee34): the driver would refuse to "
           "mount this volume; this view is read from the newest copy (LCN 0xee34, vclock 63) anyway")
    assert _NO_COPY_PASSES.search(old) and not _c1_each_said(old, _V, False)
    assert _c3_checksum_said("  [WARN] the checkpoint copy at LCN 0xee34 (vclock 63) failed its self-checksum "
                             "(CRC32-C)", 0xee34, "fails")
    assert not _c3_checksum_said("  [WARN] the checkpoint copy at LCN 0xee34: its root list could not be read (no "
                                 "root references)", 0xee34, "fails")
    assert not _c3_checksum_said("  CHKP secondary   LCN 0xee34 (offset 0xfe34000)  — checksum FAILED (CRC32-C)",
                                 0xee34, "fails")
    assert _RUN_SUMMARY.search("run `summary` on the bundle for those") and _NOT_READ_FROM.search(
        "(the copies the volume is not read from)")
