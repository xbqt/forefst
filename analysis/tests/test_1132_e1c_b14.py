"""Wave E step E1c, B14 (1.14.0, `analysis/reports/v1.13.2/fixes/WAVEE_PLAN.md`; PLAN_1.13.2 B14, decision 13): the copy
restore of refsanalysis `bootedit repair`, shipped, and N402 (its report's words).

The expected offsets and bytes come from this module's own reading of the boot sector (`_oracle`: total sectors at
+0x18, bytes per sector at +0x20, sectors per cluster at +0x24; the superblock copies at LCN 0x1E, N-2 and N-3, N the
volume's clusters), never from the tool. Every write case compares the whole output with the damaged input and allows a
difference only inside the copies the case expects restored (`_changed`), so a restore written anywhere else -- the
held code's `lba * 512` on a 4Kn volume -- is caught; `test_b14_oracle_catches_a_restore_written_at_a_wrong_offset`
shows that it is.

What each group asserts
-----------------------
VBR      a boot-sector copy is one sector of the VBR's bytes per sector (refs.sys reads and writes the boot sector as one
         sector, RefsWriteBootSector 26100.9444): a backup that fails is restored from a primary that passes; a primary
         that fails is restored from the backup the volume is read from -- unless the two record different versions
         (refs.sys writes a version upgrade to sector 0 only, so the backup can keep the earlier one).
SUPB     the copies at 0x1E, N-2, N-3 that fail refs.sys's tests are rebuilt from the copy the volume is read from (its
         own LCN set, its self-checksum recomputed), with or without their signature; never one the image ends before;
         a checksum type the tool does not compute is "cannot be verified", and nothing is rebuilt from such a source.
CHKP     reported only; a copy whose root fails its digest, or that was not read, is never "OK" (N402).
Safety   the input is never modified (SHA-256) by default; --dry-run writes nothing; --inplace needs the typed YES; each
         restore is logged (source, target, offset, length, SHA-256 before and after); the exit code is 2 when a copy
         fails; the post-repair check names the copies that still fail.
Release  no held region left; the help says what is restored and what is not; forefst's messages do not send a volume
         with no usable superblock or checkpoint copy to the copy restore.
"""
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys

import pytest

from _repo import REPO                                   # noqa: F401  layout-independent; see _repo.py
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (the synthetic volume, carve, scratch)
import test_1132_red_b2_refsanalysis as R                # noqa: E402  (the native / upgraded volume builders)
import test_1132_red_b2_journal as BJ                    # noqa: E402  (data ranges, the hole-keeping carve)

RA = os.path.join(REPO, "refsanalysis.py")
FF = os.path.join(REPO, "forefst.py")
_SYN = ["--partition-start", "0"]
_4KN = "step6/lab314_4kn.raw"
_ROOT_FAIL = "step5/testchecksums/win11refslasttests_baseline_corrupted.raw"
_JUNK = b"\xDE\xAD" * 8


# ── the oracle: where the copies are, from the boot sector's own bytes ───────────────────────────────────────────

def _oracle(path, ps=0):
    v = R._read(path, ps, 512)
    t = struct.unpack_from("<Q", v, 0x18)[0]
    bps = struct.unpack_from("<I", v, 0x20)[0]
    spc = struct.unpack_from("<I", v, 0x24)[0]
    cs = bps * spc
    n = t * bps // cs
    return {"bps": bps, "cs": cs, "n": n, "vbr_primary": (ps, bps), "vbr_backup": (ps + (t - 1) * bps, bps),
            "supb": {0x1E: (ps + 0x1E * cs, cs), n - 2: (ps + (n - 2) * cs, cs), n - 3: (ps + (n - 3) * cs, cs)}}


def _ranges(path):
    return BJ._data_ranges(path, 0, os.path.getsize(path))


def _changed(a, b):
    """The byte runs where files a and b differ (both read over the union of their data ranges; outside it both are
    holes). A size difference is a run from the shorter end."""
    sa, sb = os.path.getsize(a), os.path.getsize(b)
    spans = sorted(_ranges(a) + _ranges(b))
    out = []
    with open(a, "rb") as fa, open(b, "rb") as fb:
        pos = 0
        for lo, hi in spans:
            lo = max(lo, pos)
            while lo < hi:
                n = min(4 << 20, hi - lo)
                fa.seek(lo)
                fb.seek(lo)
                x, y = fa.read(n), fb.read(n)
                if x != y:
                    m = max(len(x), len(y))
                    x, y = x.ljust(m, b"\0"), y.ljust(m, b"\0")
                    i = 0
                    while i < m:
                        if x[i] != y[i]:
                            j = i
                            while j < m and x[j] != y[j]:
                                j += 1
                            out.append((lo + i, j - i))
                            i = j
                        else:
                            i += 1
                lo += n
            pos = max(pos, hi)
    if sa != sb:
        out.append((min(sa, sb), abs(sa - sb)))
    return out


def _check_restore(inp, out, expect):
    """Problems with a restore: `expect` = [(offset, bytes)] the output must hold; every byte that differs from the input
    must lie inside one of them. [] = the restore is exactly what was expected."""
    probs = []
    for off, data in expect:
        got = R._read(out, off, len(data))
        if got != data:
            probs.append("0x%x: the %d bytes there are not the expected copy" % (off, len(data)))
    for off, n in _changed(inp, out):
        if not any(o <= off and off + n <= o + len(d) for o, d in expect):
            probs.append("0x%x+0x%x changed outside every expected copy" % (off, n))
    return probs


# ── running ───────────────────────────────────────────────────────────────────────────────────────────────────────

def _ra(path, *args, cli=_SYN, stdin="", cwd):
    cmd = [sys.executable, "-B", RA, path] + list(args) + list(cli)
    r = subprocess.run(cmd, capture_output=True, text=True, input=stdin, timeout=1800, cwd=str(cwd))
    assert "Traceback (most recent call last)" not in r.stderr, r.stderr[-3000:]
    return r.returncode, r.stdout, r.stderr


def _ctx(rc, out, err=""):
    return "\n| rc=%s\n%s\n--- stderr ---\n%s" % (rc, out[-4000:], err[-2000:])


def _repair(inp, tmp_path, *extra, cli=_SYN):
    out = str(tmp_path / "repaired.raw")
    rc, so, se = _ra(inp, "bootedit", "repair", "-o", out, *extra, cli=cli, cwd=tmp_path)
    return out, rc, so, se


def _native(tmp_path, name="in.raw"):
    return R._native_volume(str(tmp_path / name))


def _copy_lines(out):
    """The report's per-copy lines: the first block after its header (not the proposals, the refusals or the post-repair
    check)."""
    blk = out.split("Redundant copies", 1)[-1].split("\n\n", 1)[0]
    return [l for l in blk.splitlines() if re.match(r"^  (VBR|SUPB|CHKP) ", l)]


def _line(out, kind, needle):
    ls = [l for l in _copy_lines(out) if l.startswith("  " + kind) and needle in l]
    assert ls, "no %s line naming %r:\n%s" % (kind, needle, "\n".join(_copy_lines(out)))
    return ls[0]


# ── VBR ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_b14_vbr_backup_is_restored_from_the_primary(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    boff, bps = o["vbr_backup"]
    R._write(p, boff + 0x40, _JUNK)
    before = R._sha(p)
    out, rc, so, se = _repair(p, tmp_path)
    assert R._sha(p) == before, "the input image was modified"
    assert not _check_restore(p, out, [(boff, R._read(p, 0, bps))]), _check_restore(p, out, [(boff, R._read(p, 0, bps))])
    assert rc == 2, _ctx(rc, so, se)


def test_b14_vbr_primary_is_restored_from_the_backup(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    boff, bps = o["vbr_backup"]
    good = R._read(p, boff, bps)
    R._write(p, 0x40, _JUNK)
    out, rc, so, se = _repair(p, tmp_path)
    assert not _check_restore(p, out, [(0, good)]), _check_restore(p, out, [(0, good)]) + [_ctx(rc, so, se)]


def test_b14_vbr_primary_is_not_restored_from_a_backup_with_another_version(tmp_path):
    """The upgraded shape (win10to11refs4g): the primary records 3.14, the backup 3.4. A damaged primary is not
    replaced by the backup: refs.sys writes a version upgrade to sector 0 only."""
    p = str(tmp_path / "up.raw")
    R._upgraded_volume(p)
    R._write(p, 0x40, _JUNK)
    before = R._sha(p)
    out, rc, so, se = _repair(p, tmp_path)
    assert R._sha(p) == before
    assert not os.path.exists(out) or R._read(out, 0, 512) == R._read(p, 0, 512), "the primary was replaced" + \
        _ctx(rc, so, se)
    ln = _line(so, "VBR", "primary")
    # the refusal itself (its list "Not restored (N):" and the VBR line naming both versions). Until 1.14.0 a
    # case-sensitive "not restored" was met by the CHECKPOINT line instead: the record tests took the version from the
    # backup (3.4) and rejected every copy (C2-2), so no CHKP refusal is expected now
    refusal = so.split("Not restored (", 1)[-1] if "Not restored (" in so else ""
    assert re.search(r"VBR primary sector 0: the primary records version 3\.14 and the backup boot sector .*version "
                     r"3\.4\b", refusal), _ctx(rc, so, se)
    assert "a checkpoint copy is not restored" not in so, _ctx(rc, so, se)
    assert rc == 2, _ctx(rc, so, se)


# ── SUPB ────────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("which", ["backup_n2", "backup_n3", "primary"])
def test_b14_supb_copy_is_rebuilt_from_the_copy_read(tmp_path, which):
    p = _native(tmp_path)
    o = _oracle(p)
    lcn = {"backup_n2": o["n"] - 2, "backup_n3": o["n"] - 3, "primary": 0x1E}[which]
    off, cs = o["supb"][lcn]
    pristine = R._read(p, off, cs)
    R._write(p, off + 0x40, _JUNK)
    out, rc, so, se = _repair(p, tmp_path)
    probs = _check_restore(p, out, [(off, pristine)])
    assert not probs, probs + [_ctx(rc, so, se)]
    assert rc == 2, _ctx(rc, so, se)


def test_b14_supb_backup_without_its_signature_is_rebuilt(tmp_path):
    """refs.sys's ReadSuperBlock rewrites every other copy from the copy it chose: a zeroed copy at N-2 is one."""
    p = _native(tmp_path)
    o = _oracle(p)
    off, cs = o["supb"][o["n"] - 2]
    pristine = R._read(p, off, cs)
    R._write(p, off, b"\0" * cs)
    out, rc, so, se = _repair(p, tmp_path)
    probs = _check_restore(p, out, [(off, pristine)])
    assert not probs, probs + [_ctx(rc, so, se)]


def test_b14_no_copy_the_image_ends_before_is_written(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    off, cs = o["supb"][o["n"] - 3]
    with open(p, "r+b") as fh:
        fh.truncate(off)                                 # both backup superblocks and the backup boot sector are gone
    size = os.path.getsize(p)
    out, rc, so, se = _repair(p, tmp_path)
    assert not os.path.exists(out) or os.path.getsize(out) == size, "the restore extended the image" + _ctx(rc, so, se)
    for l in [l for l in _copy_lines(so) if l.startswith("  SUPB backup")]:
        assert "not read" in l and "signature" not in l, l
    assert "not read" in _line(so, "VBR", "backup"), _ctx(rc, so, se)
    assert rc == 2, _ctx(rc, so, se)


def test_b14_unknown_checksum_type_is_cannot_be_verified_and_no_source(tmp_path):
    """Every superblock copy declares checksum type 3 (no algorithm); the backup at N-2 also fails the count test. The
    copies are "cannot be verified", never OK or BAD; the failing copy is not rebuilt (no digest can be computed)."""
    p = _native(tmp_path)
    o = _oracle(p)
    for lcn, (off, cs) in o["supb"].items():
        d = struct.unpack_from("<I", R._read(p, off, 0x80), 0x78)[0]
        R._write(p, off + d + 0x22, b"\x03")
    off, cs = o["supb"][o["n"] - 2]
    R._write(p, off + 0x74, struct.pack("<I", 3))
    before = R._sha(p)
    out, rc, so, se = _repair(p, tmp_path)
    prim = _line(so, "SUPB", "0x1e")
    assert "cannot be verified" in prim and "OK" not in prim and "BAD" not in prim, prim
    assert not os.path.exists(out) or R._read(out, off, cs) == R._read(p, off, cs), "a copy was rebuilt" + \
        _ctx(rc, so, se)
    assert R._sha(p) == before and rc == 2, _ctx(rc, so, se)


# ── CHKP (N402) ─────────────────────────────────────────────────────────────────────────────────────────────────

def test_n402_a_checkpoint_copy_whose_root_fails_is_not_ok(tmp_path):
    img = R._image_or_skip(_ROOT_FAIL)
    rc, so, se = _ra(img, "bootedit", "repair", "--dry-run", cli=(), cwd=tmp_path)
    bad = [l for l in _copy_lines(so) if l.startswith("  CHKP") and "root" in l and "does not match" in l]
    assert bad and not [l for l in bad if re.search(r":\s*OK\s*$", l)], "\n".join(_copy_lines(so))
    assert rc == 2, _ctx(rc, so, se)


@pytest.mark.parametrize("plant", ["zeros", "hole"])
def test_n402_an_unreadable_checkpoint_copy_is_said_with_its_cause(tmp_path, plant):
    p = _native(tmp_path, "base.raw")
    at = AB.SYN.hi * AB.CS
    if plant == "zeros":
        q = p
        R._write(q, at, b"\0" * AB.CS)
    else:
        q = str(tmp_path / "in.raw")
        BJ._carve_except(p, q, [(at, AB.CS)])
        assert BJ._is_hole(q, at, AB.CS)
    rc, so, se = _ra(q, "bootedit", "repair", "--dry-run", cwd=tmp_path)
    ln = _line(so, "CHKP", "0x%x" % AB.SYN.hi)
    assert "BAD" not in ln and "None" not in ln, ln
    assert ("as a hole" in ln) if plant == "hole" else ("all zeros" in ln and "hole" not in ln), ln
    assert rc == 2, _ctx(rc, so, se)


def test_b14_post_repair_check_names_the_copies_that_still_fail(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    off, cs = o["supb"][o["n"] - 2]
    R._write(p, off + 0x40, _JUNK)
    R._write(p, AB.SYN.hi * AB.CS, b"\0" * AB.CS)       # a checkpoint copy: reported, never restored
    out, rc, so, se = _repair(p, tmp_path)
    post = so.split("Post-repair", 1)[-1]
    assert "ALL COPIES VERIFY" not in so and "0x%x" % AB.SYN.hi in post and "still" in post, _ctx(rc, so, se)


# ── safety ──────────────────────────────────────────────────────────────────────────────────────────────────────

def test_b14_control_a_healthy_volume_exits_0_and_plans_nothing(tmp_path):
    p = _native(tmp_path)
    rc, so, se = _ra(p, "bootedit", "repair", "--dry-run", cwd=tmp_path)
    assert rc == 0 and "Proposed" not in so, _ctx(rc, so, se)


def test_b14_dry_run_writes_nothing_and_exits_2(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    off, cs = o["supb"][o["n"] - 2]
    R._write(p, off + 0x40, _JUNK)
    before = R._sha(p)
    out, rc, so, se = _repair(p, tmp_path, "--dry-run")
    assert not os.path.exists(out) and R._sha(p) == before, _ctx(rc, so, se)
    assert rc == 2, _ctx(rc, so, se)


def test_b14_inplace_needs_the_typed_yes(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    off, cs = o["supb"][o["n"] - 2]
    pristine = R._read(p, off, cs)
    R._write(p, off + 0x40, _JUNK)
    before = R._sha(p)
    rc, so, se = _ra(p, "bootedit", "repair", "--inplace", stdin="no\n", cwd=tmp_path)
    assert rc == 1 and R._sha(p) == before, _ctx(rc, so, se)
    rc, so, se = _ra(p, "bootedit", "repair", "--inplace", stdin="YES\n", cwd=tmp_path)
    assert R._read(p, off, cs) == pristine, _ctx(rc, so, se)


def test_b14_each_restore_is_logged_with_its_hashes(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    off, cs = o["supb"][o["n"] - 2]
    R._write(p, off + 0x40, _JUNK)
    damaged = R._read(p, off, cs)
    out, rc, so, se = _repair(p, tmp_path)
    logs = [f for f in os.listdir(str(tmp_path)) if f.startswith("repaired.raw") and f.endswith(".log")]
    assert logs, "no restore log beside the output: %r" % os.listdir(str(tmp_path))
    log = open(str(tmp_path / logs[0]), encoding="utf-8").read()
    assert hashlib.sha256(damaged).hexdigest() in log and hashlib.sha256(R._read(out, off, cs)).hexdigest() in log, log
    assert "0x%x" % off in log and "0x1e" in log, log          # the target's offset and the source copy


# ── the oracle itself ───────────────────────────────────────────────────────────────────────────────────────────

def test_b14_oracle_catches_a_restore_written_at_a_wrong_offset(tmp_path):
    """The planted wrong offset: the right bytes written one sector off (the 4Kn backup at `lba * 512` is the same
    mistake at another distance) must be reported, both as a missing copy and as a change outside it."""
    p = _native(tmp_path)
    o = _oracle(p)
    boff, bps = o["vbr_backup"]
    R._write(p, boff + 0x40, _JUNK)
    bad = str(tmp_path / "bad.raw")
    shutil.copyfile(p, bad)
    R._write(bad, boff - bps, R._read(p, 0, bps))
    probs = _check_restore(p, bad, [(boff, R._read(p, 0, bps))])
    assert [x for x in probs if "not the expected copy" in x] and [x for x in probs if "outside" in x], probs


# ── 4Kn (lab314_4kn: 4096 bytes per sector) ─────────────────────────────────────────────────────────────────────

def _4kn_copy(tmp_path):
    base = R._image_or_skip(_4KN)
    p = str(tmp_path / "in.raw")
    assert AB._sparse_capable(str(tmp_path))
    AB._carve(base, p)
    return p, R._gpt_ps(p)


@pytest.mark.parametrize("which", ["vbr_backup", "vbr_primary", "supb_backup"])
def test_b14_4kn_restores_land_at_the_sector_size_offsets(tmp_path, which):
    p, ps = _4kn_copy(tmp_path)
    try:
        o = _oracle(p, ps)
        assert o["bps"] == 4096
        boff, bps = o["vbr_backup"]
        if which == "vbr_backup":
            R._write(p, boff + 0x40, _JUNK)
            expect = [(boff, R._read(p, ps, bps))]
        elif which == "vbr_primary":
            expect = [(ps, R._read(p, boff, bps))]
            R._write(p, ps + 0x40, _JUNK)
        else:
            off, cs = o["supb"][o["n"] - 2]
            expect = [(off, R._read(p, off, cs))]
            R._write(p, off + 0x40, _JUNK)
        before = R._sha(p)
        out, rc, so, se = _repair(p, tmp_path, cli=())
        assert R._sha(p) == before, "the input image was modified"
        probs = _check_restore(p, out, expect)
        assert not probs, probs + [_ctx(rc, so, se)]
    finally:
        for f in ("in.raw", "repaired.raw"):
            if os.path.exists(str(tmp_path / f)):
                os.unlink(str(tmp_path / f))


# ── the release: no held region; help; forefst's messages ───────────────────────────────────────────────────────

def test_b14_no_held_region_is_left():
    src = open(RA, encoding="utf-8").read()
    assert "HELD-BEGIN" not in src and "HELD-END" not in src and "(dev build)" not in src and "dev build" not in src


def test_b14_help_says_what_is_restored_and_what_is_not(tmp_path):
    r = subprocess.run([sys.executable, "-B", RA, "help", "bootedit"], capture_output=True, text=True, cwd=str(tmp_path))
    h = r.stdout
    assert re.search(r"(?i)checkpoint", h) and re.search(r"(?i)report", h) and "--inplace" in h, h
    assert re.search(r"(?i)superblock", h) and re.search(r"(?i)backup boot sector|boot sector cop", h), h


@pytest.mark.parametrize("what", ["superblock", "checkpoint"])
def test_b14_forefst_does_not_send_an_unrestorable_volume_to_the_copy_restore(tmp_path, what):
    """No superblock copy that can be read (all three zeroed), or no checkpoint copy (both zeroed): the copy restore has
    no source, so the message must not send the examiner to it."""
    p = _native(tmp_path)
    o = _oracle(p)
    if what == "superblock":
        for off, cs in o["supb"].values():
            R._write(p, off, b"\0" * cs)
    else:
        for lcn in (AB.SYN.lo, AB.SYN.hi):
            R._write(p, lcn * AB.CS, b"\0" * AB.CS)
    r = subprocess.run([sys.executable, "-B", FF, p, "summary"] + _SYN, capture_output=True, text=True,
                       cwd=str(tmp_path), timeout=600)
    assert r.returncode == 1, (r.returncode, r.stderr[-1500:])
    assert "bootedit repair" not in r.stderr, r.stderr[-1500:]


# ── E1 close: the review's findings (`fixes/REVIEW_WAVEE1.md`) ────────────────────────────────────────────────────────

def test_re1_2_the_checkpoint_note_holds_when_the_copies_tie(tmp_path):
    img = R._image_or_skip("step3/win11refs2tmillionsofactions.raw")
    rc, so, se = _ra(img, "bootedit", "repair", "--dry-run", cli=(), cwd=tmp_path)
    clocks = re.findall(r"^  CHKP .*vclock=(\d+)", so, re.M)
    assert len(clocks) == 2 and clocks[0] == clocks[1], clocks                 # the natural tie (662)
    assert "different clocks" not in so and "NOTE: a checkpoint copy is not restored" in so, _ctx(rc, so, se)


def test_re1_3_the_healthy_report_does_not_say_the_copies_were_not_checked(tmp_path):
    p = _native(tmp_path)
    rc, so, se = _ra(p, "bootedit", "repair", "--dry-run", cwd=tmp_path)
    assert rc == 0 and "NOT checked: the backup boot sector" not in so and "reported above" in so, _ctx(rc, so, se)


def test_re1_9_a_repair_that_writes_prints_no_deprecation_warning(tmp_path):
    p = _native(tmp_path)
    o = _oracle(p)
    off, cs = o["supb"][o["n"] - 2]
    R._write(p, off + 0x40, _JUNK)
    cmd = [sys.executable, "-B", "-W", "default", RA, p, "bootedit", "repair", "-o", str(tmp_path / "r.raw")] + _SYN
    r = subprocess.run(cmd, capture_output=True, text=True, input="", cwd=str(tmp_path), timeout=600)
    assert "DeprecationWarning" not in r.stderr and os.path.exists(str(tmp_path / "r.raw.repair.log")), r.stderr[-1500:]


_BASIC_DATA = bytes.fromhex("a2a0d0ebe5b9334487c068b6b72699c7")      # EBD0A0A2-B9E5-4433-87C0-68B6B72699C7


def _in_gpt(vol, path):
    """`vol` (a synthetic volume file) as GPT partition #1 at LBA 2048 of a 64 MiB partition (sparse): the boot-sector
    search reads the partition's length from the GPT (a raw image's sector 0 must carry a signature, so a primary
    without one is reached only through a partition table)."""
    from conftest import make_gpt
    first, n = 2048, (64 << 20) // 512
    with open(path, "wb") as fh:
        fh.write(make_gpt(num_parts=4, partitions=[(_BASIC_DATA, first, first + n - 1, "refs")]))
        fh.truncate((first + n) * 512)
        fh.seek(first * 512)
        fh.write(open(vol, "rb").read())
    return path, first * 512


def test_re1_13_an_unsigned_primary_over_a_newer_volume_is_refused_and_exits_2(tmp_path):
    """The upgraded shape (backup 3.4, checkpoint flags 0x602) with the primary's OEM id destroyed: the primary carries no
    signature (no version to compare), the synthetic volume has no $VOLUME_INFORMATION, and the checkpoint alone shows
    3.14 -- not restored; the fixboot step needs a ReFS signature and is not made (it stopped with exit 1)."""
    v = str(tmp_path / "up.raw")
    R._upgraded_volume(v)
    p, ps = _in_gpt(v, str(tmp_path / "disk.raw"))
    os.unlink(v)
    R._write(p, ps + 3, b"\0" * 8)
    before = R._sha(p)
    out, rc, so, se = _repair(p, tmp_path, "--dry-run", cli=())
    tail = so.split("Not restored", 1)
    assert len(tail) == 2 and "VBR primary sector 0" in tail[1] and "0x602" in tail[1], _ctx(rc, so, se)
    assert rc == 2 and "fixboot diagnosis is not made" in so and R._sha(p) == before, _ctx(rc, so, se)


def test_re1_12_a_4kn_image_that_ends_inside_its_backup_sector(tmp_path):
    p, ps = _4kn_copy(tmp_path)
    try:
        o = _oracle(p, ps)
        boff, bps = o["vbr_backup"]
        R._write(p, ps + 0x40, _JUNK)                    # the primary fails; the backup is the only source
        with open(p, "r+b") as fh:
            fh.truncate(boff + 768)                      # the image ends 768 bytes into the backup's 4096-byte sector
        before = R._sha(p)
        out, rc, so, se = _repair(p, tmp_path, "--dry-run", cli=())
        assert "not read in full" in _line(so, "VBR", "backup") and R._sha(p) == before, _ctx(rc, so, se)
        tail = so.split("Not restored", 1)
        assert len(tail) == 2 and "VBR primary sector 0" in tail[1] and rc == 2, _ctx(rc, so, se)
        assert "Proposed copy restores" not in so or "VBR primary" not in so.split("Proposed copy restores", 1)[1] \
            .split("Not restored", 1)[0], _ctx(rc, so, se)
    finally:
        for f in ("in.raw", "repaired.raw"):
            if os.path.exists(str(tmp_path / f)):
                os.unlink(str(tmp_path / f))
