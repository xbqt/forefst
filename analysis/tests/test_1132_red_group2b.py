"""1.13.2 RED cases for decision 25's additions to fix group 2 (Bootstrap): the 18 items of the group-2b brief.

Brief: `analysis/reports/v1.13.2/red/GROUP2B_RED_BRIEF.md`. Context: `fixes/G2_CONTEXT.md` ("Added 2026-10-02 --
decision 25"), `CONSISTENCY_DEDUP_2026-10-02.md` s.2.1 (items 2-24, code sites and RED shapes), `RUNNING_LOG.md` rows
N238, N239, N242-N253, PLAN decisions 21, 22 and 25. Report, with every node's observed failure:
`analysis/reports/v1.13.2/red/RED_group2b.md`. Measured on the current dev tools (forefst b7765bab, refsanalysis
c7fb9e8d).

What each RED asserts
---------------------
 1 N239 backup    a backup boot sector that fails its checksum: summary/fastsummary/integrity name it as failed,
                  no PASS, exit 2 (today: 'DIFFERS' / 'checksum?', NOTE, PASS, exit 0)
 2 N239 primary   a primary boot sector that fails its checksum: no 'sig OK' / 'sig-ok, checksum?', named, exit 2
 3 N238 CHKP      an unknown checksum type in the checkpoint's self-descriptor (the one CHKP+0x58 declares):
                  'cannot be verified' with the type, never "FAILED (CRC64)", exit 2 (decision 22)
 4 N238 SUPB      the same for a superblock copy (the descriptor SUPB+0x78 declares): never 'signature OK'
 5 A1 widening    a ZEROED primary superblock: integrity not '3 intact', not PASS, JSON clean not true; the JSON
                  `ok` of every superblock copy is that copy's validated verdict (today: the signature, or True)
 6 A3 widening a  refsanalysis summary reports the shared redundancy findings and exits 2 (decision 25.3)
 7 A3 widening b  an exception in a root walk: refsanalysis summary says unreadable, not '0 rows', exit 2
 8 A4 + 25.2      boot --verify / supb --verify exit 2 on any FAIL row; bare `boot` exits 2 on a checksum FAIL
 9 B1 (X-11)      deleted's 'Checkpoints: N (VC: ...)' header marks the failed copy or lists the copy in use first
10 N242           each SUPB line carries its own copy's hash; the JSON names the copy `supb_sha256` hashes
11 N243           integrity counts one condition once
12 N244           `chkp -v` prints the GUID of a verified superblock copy
13 N245           mapped containers are not presented as usage; the old `utilization_pct` keeps its value (kept)
14 N246           'unknown'/null, not 'Inactive', when the 0x520 table was not read
15 N247           summary++ keeps the walk's extended counts when the 0x500 table yields no detail
16 N249           summary++ snapshot count at full depth (reproduced: RC1 candidate)
17 N250-N253      one redundancy list; byte offsets on integrity's lines; '(tied clock)' on summary's CHKP lines
                  (group 5's reader still matches); a checkpoint read error in `deleted` worded as such
18 help strings   `chkp --verify` help names the checks that decide its exit code (RED); `supb --verify`'s
                  '7-check' is right today and can only go stale: a control-shaped node
19 decision 26    (added 2026-10-02, group 2 review F1 / R1) the primary superblock fails its self-checksum and no
                  backup verifies: the volume is read from the primary anyway, the finding is said, exit 2 (never 1),
                  no `--partition-start` hint while the SUPB signature is present (today: exit 1 in every command)

Volumes
-------
* ``[synthetic]`` / ``[image]`` -- the a_bootstrap `vol` fixture, re-exported (imported by name, never `import *`).
* Read-only corpus images: win10to11refs4g.raw (item 1's control: an upgraded volume whose backup boot sector
  differs and passes), win11refs2tsnapshots.raw (item 16 copies one real snapshotted file row into a synthetic tree).
* Scratch carves: win11refs2g_disableheatgathering.raw (item 15; about 10 MB allocated), made under
  ``$FOREFST_RED_SCRATCH`` and deleted by exact path.
* Synthetic deep trees (item 16) from `test_1132_red_b2_deleted.DirVol`, in pytest's tmp dir.
* ``pytest -k "not image"`` runs the synthetic half.

Discipline (as in test_1132_red_group2.py): ``@_red`` = ``xfail(strict=True, raises=AssertionError)``; only a plain
``assert`` states the defect; ``_fx`` for a fixture that is not what the case needs, ``_keep`` for a property the
current tool already has; every RED has a control that passes now.
"""
import functools
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jget, jint, jdoc# noqa: E402  (K21 readers)

import test_1132_red_a_bootstrap as _AB                   # noqa: E402
from test_1132_red_a_bootstrap import (                  # noqa: E402
    RedFixtureError, _fx, _keep, _ctx, damage_chkp, damage_supb, make_tie, zero_ot_root, _root_list,
    _own_digest, _FAIL, _lcn_re, _lines, FOREFST, REFSANALYSIS, CS, CHKP_DESC, SUPB_DESC, GUID, GUID_RAW,
    CLOCK_OLD, CLOCK_NEW, _named_failed, _reads_checkpoint, _guid, _virtual_clock)
from test_1132_red_group2 import (                       # noqa: E402
    IMAGE_ONLY, _statements, _addr_re, _UNVERIFIED, _backup_vbr_offset, _flip_boot_sector)
from test_1132_red_b_items import apply_b1_case          # noqa: E402
from test_1132_red_b2_refsanalysis import _seal_vbr, _vbr_ok  # noqa: E402
from test_1132_red_mlog_chkp import summary_chkp_rows    # noqa: E402  (group 5's reader of summary's CHKP lines)
import test_1132_red_b2_deleted as _BD                    # noqa: E402  (DirVol, _row, _page)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module


def _run(tool, path, *args, cwd, env=None, cli=()):
    """A tool run outside the `vol` fixture: (rc, stdout + stderr). A crash or a timeout is a fixture error."""
    cmd = [sys.executable, "-B", tool, path] + list(args) + list(cli)
    try:
        r = UW.run(cmd, capture_output=True, text=True, timeout=_AB.TIMEOUT, cwd=cwd, env=env)
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed:\n" + r.stderr[-3000:])
    return r.returncode, r.stdout + "\n" + r.stderr


def _json_text(out, what):
    i = out.find("{")
    _fx(i >= 0, "%s printed no JSON" % what)
    try:
        return jdoc(json.JSONDecoder().raw_decode(out[i:])[0], F._SUMMARY_KEYS)      # K21: internal names
    except ValueError as e:
        raise RedFixtureError("%s: unparsable JSON (%s)" % (what, e))


def _vjson(v, tool, *args):
    rc, out = v.run(tool, *args)
    return rc, out, _json_text(out, " ".join(args))


def _image_or_skip(name):
    p = _corpus_image(name)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return p


def _own_rows(out, role):
    """Lines of ONE boot-sector copy, matched on that copy's own label -- 'VBR primary', 'primary boot sector',
    'Boot sector (primary)' -- not on any line that merely contains the role word ('DIFFERS from primary'; critic R1).
    C2 bounds_b (decision 44's pre-sanctioned form edit, N344): decision 36 Q3 A's statement -- "the primary boot
    sector ... is damaged ...; the volume was read from the backup boot sector found at offset ..." -- is about the
    choice between the copies, not a line of one copy: a line that names both copies and a read verb, or says a backup
    is read ("read from the backup ...", the statement wrapped, whose driver clause ends "... sector 0 fails"), is no
    row of either. A row of one copy that names the other ('VBR backup ... DIFFERS from the primary VBR, checksum
    FAILED') stays the row of the copy named first (critic C2 bounds_b; R1's protection kept)."""
    def _label(r):
        return re.compile(r"(?i)\bVBR\s+%s\b|\b%s\s+(?:boot sector|VBR)\b|\bboot sector\s*\(%s\)" % (r, r, r))
    rx, other = _label(role), _label("backup" if role == "primary" else "primary")
    rows = []
    for ln in out.splitlines():
        m, o = rx.search(ln), other.search(ln)
        if not m or (o and _READS.search(ln)) or _READ_FROM_BACKUP.search(ln) or (o and o.start() < m.start()):
            continue
        rows.append(ln)
    return rows


_READS = re.compile(r"(?i)\b(?:read|reads|reading|used|uses|using)\b")
_READ_FROM_BACKUP = re.compile(r"(?i)\b(?:read|reads|reading|used|uses|using)\b[^.;\n]{0,60}\bbackup\b")


def _read_line_blames(out, role, rows):
    """C2 RED re-check (escalation, 2026-10-23): the lines `_own_rows` leaves out of `role`'s rows because they are
    about the copy read (both copies named with a read verb, or a backup said to be read), that call `role`'s copy
    failed -- a failure word between `role`'s own label and the other copy's label, or the line's end. The bounds_b
    form edit leaves such lines out for the decided statement when the primary fails; where `role`'s copy is intact,
    such a line is the wrong output its rows caught before that edit. A line naming the other copy first without a
    read verb ('VBR backup ... DIFFERS from the primary VBR, checksum FAILED') is not one of them (R1, kept)."""
    def _label(r):
        return re.compile(r"(?i)\bVBR\s+%s\b|\b%s\s+(?:boot sector|VBR)\b|\bboot sector\s*\(%s\)" % (r, r, r))
    rx, ox = _label(role), _label("backup" if role == "primary" else "primary")
    hits = []
    for ln in out.splitlines():
        if ln in rows or not ((ox.search(ln) and _READS.search(ln)) or _READ_FROM_BACKUP.search(ln)):
            continue
        for m in rx.finditer(ln):
            o = ox.search(ln, m.end())
            if _FAIL.search(_VERSION_NOTE.sub("", ln[m.end():o.start() if o else len(ln)])):
                hits.append(ln)
                break
    return hits


_VERSION_NOTE = re.compile(r"(?i)version (mismatch|differs)")


def _boot_failed(rows):
    """Rows that call the copy failed. An upgraded volume's version note ('version mismatch: primary v3.14, backup
    v3.4 -- an UPGRADE ...') is not a checksum failure and does not count."""
    return [ln for ln in rows if _FAIL.search(_VERSION_NOTE.sub("", ln))]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1-2. N239 -- a boot-sector copy that fails its checksum is a finding (backup and primary)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_N239_CMDS = ["summary", "fastsummary", "integrity"]
# After the critic (R1): a role is read from each copy's OWN label, and the OTHER copy's own lines must carry no
# failure word -- blaming the intact backup ("DIFFERS from primary, checksum FAILED") for a failed primary passed
# item 2's integrity nodes before.


@pytest.mark.parametrize("cmd", _N239_CMDS)
def test_n239_a_backup_boot_sector_that_fails_its_checksum_is_a_finding(vol, cmd):
    _flip_boot_sector(vol, _backup_vbr_offset(vol))
    rc, out = vol.run(FOREFST, cmd)
    rows, other = _own_rows(out, "backup"), _own_rows(out, "primary")
    _keep(rows and other, "both boot-sector copies are listed" + _ctx(vol, rc, out))
    assert _boot_failed(rows), "a line must name the backup boot sector as failed: %r" % rows + _ctx(vol, rc, out)
    assert not _boot_failed(other), "the intact primary is called failed: %r" % other + _ctx(vol, rc, out)
    blamed = _read_line_blames(out, "primary", other)       # C2 RED re-check: the lines the bounds_b form edit left out
    assert not blamed, "a line about the copy read calls the intact primary failed: %r" % blamed + _ctx(vol, rc, out)
    assert not re.search(r"(?i)verdict:\s*pass", out), "the verdict must not be PASS" + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", _N239_CMDS)
def test_n239_a_primary_boot_sector_that_fails_its_checksum_is_a_finding(vol, cmd):
    _flip_boot_sector(vol, vol.geo.vbr)
    rc, out = vol.run(FOREFST, cmd)
    rows, other = _own_rows(out, "primary"), _own_rows(out, "backup")
    _keep(rows and other, "both boot-sector copies are listed" + _ctx(vol, rc, out))
    assert not [ln for ln in rows if re.search(r"(?i)\bsig[- ]ok\b", ln)], \
        "the failed primary is labelled 'sig OK': %r" % rows + _ctx(vol, rc, out)
    assert _boot_failed(rows), "a line must name the primary boot sector as failed: %r" % rows + _ctx(vol, rc, out)
    assert not _boot_failed(other), "the intact backup is called failed: %r" % other + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


def test_n239_control_intact_boot_sectors_are_not_a_finding(vol):
    for cmd in _N239_CMDS:
        rc, out = vol.run(FOREFST, cmd)
        assert rc == 0 and not _boot_failed(_own_rows(out, "backup") + _own_rows(out, "primary")), \
            cmd + _ctx(vol, rc, out)


def test_n239_control_refsanalysis_boot_verify_already_sees_the_flipped_primary(vol):
    """The flip lands where a sound path looks: refsanalysis `boot --verify` reports the checksum row FAIL."""
    _flip_boot_sector(vol, vol.geo.vbr)
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    assert re.search(r"(?im)^checksum_match\s+FAIL", out), _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["fastsummary", "integrity"])
def test_n239_image_control_an_upgraded_volumes_differing_backup_is_not_a_finding(cmd, tmp_path):
    """On an upgraded volume the backup boot sector keeps the birth version: it DIFFERS and passes its checksum.
    The fix must key on the backup's own checksum, never on 'differs' (no false alarm; 143/143 corpus backups pass)."""
    path = _image_or_skip("win10to11refs4g.raw")
    ps, _desc = F.find_refs_partition(path)
    _fx(ps is not None, "no ReFS partition")
    with open(path, "rb") as fh:
        fh.seek(ps)
        p = fh.read(512)
        fh.seek(ps + (struct.unpack_from("<Q", p, 0x18)[0] - 1) * struct.unpack_from("<I", p, 0x20)[0])
        b = fh.read(512)
    _fx(_vbr_ok(p) and _vbr_ok(b) and p != b, "the backup boot sector does not differ-and-pass")
    rc, out = _run(FOREFST, path, cmd, cwd=str(tmp_path))
    rows = _own_rows(out, "backup")
    assert rc == 0 and rows and not _boot_failed(rows), out[-3000:]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 3-4. N238 -- an unknown checksum type in a self-descriptor: "cannot be verified (unknown checksum type 0xNN)"
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Decision 22: read the descriptor the header declares (CHKP+0x58, SUPB+0x78), as the driver does; an unknown type
# -> "checksum cannot be verified (unknown checksum type 0xNN)", exit 2 in summary/integrity; the superblock too.
# Today `_verify_self_checksum` scans past an unknown type: on a CHKP it lands on root reference 0 and reports
# (False, 'CRC64') -- "failed its self-checksum (CRC64)"; on a SUPB it finds nothing and reports "signature OK".
# After the critic (R2): no statement may call the copy failed unless it also says it cannot be verified, and the
# checkpoint copy is not abandoned for the older one (`checkpoint_used_lcn` stays the copy). Returning False with the
# right type name -- "failed its self-checksum (unknown checksum type 0x03) ... read from an OLDER checkpoint" --
# passed every node before.

def plant_unknown_type(v, lcn, decl, t):
    """Set the checksum type byte of the self-descriptor the header declares at `decl` (0x58 CHKP, 0x78 SUPB). The
    byte is inside the window zeroed before hashing, so the stored CRC32-C still equals this module's own."""
    b = bytearray(v.block(lcn))
    desc = F.le32(b, decl)
    _fx(b[desc + 0x23] == 8 and b[desc + 0x22] == 1 and F.le32(b, desc + 0x24) == 4,
        "0x%x: the declared descriptor at +0x%x is not CRC32-C" % (lcn, desc))
    b[desc + 0x22] = t
    v.write(v.at(lcn), bytes(b))
    v.ops.append("0x%x: descriptor +0x%x checksum type 0x%02x" % (lcn, desc, t))
    blk = v.block(lcn)
    _fx(blk[desc + 0x28:desc + 0x2C] == _own_digest(blk, desc), "the block changed outside the hashed window")
    return desc


def _type_re(t):
    return re.compile(r"(?i)\btype\b\D{0,16}(?:0x0*%x|%d)\b" % (t, t))


def _called_failed(out, lcn):
    """Statements naming the copy with a failure word that do not say it cannot be verified (critic R2)."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _FAIL.search(s) and not _UNVERIFIED.search(s)]


def _copy_in_use(v, cmd):
    """The checkpoint copy bootstrap reads, from the command's JSON (`checkpoint_used_lcn`)."""
    _rc, _out, j = _vjson(v, FOREFST, cmd, "--json")
    # acceptance 1.14.0 (K21, K9; N305: integrity carries summary's BootstrapBackups)
    bb = jget(j, "bootstrap_backups") or {}
    _fx(jget(bb, "checkpoint_used_lcn") is not None, "%s --json names no checkpoint in use" % cmd)
    return jint(jget(bb, "checkpoint_used_lcn"))


def _said_unknown_type(out, lcn, t):
    """A statement naming the copy that says its checksum cannot be verified, with the type."""
    return [s for s in _statements(out) if _lcn_re(lcn).search(s) and _UNVERIFIED.search(s) and _type_re(t).search(s)]


@pytest.mark.parametrize("cmd", ["summary", "integrity"])
@pytest.mark.parametrize("t", [0x03, 0x05, 0xFF], ids=["type0x03", "type0x05", "type0xff"])
def test_n238_chkp_unknown_checksum_type_is_cannot_be_verified(vol, t, cmd):
    lcn = vol.geo.lo
    plant_unknown_type(vol, lcn, 0x58, t)
    rc, out = vol.run(FOREFST, cmd)
    _keep(rc == 2, "exit 2 (decision 22)" + _ctx(vol, rc, out))
    crc64 = [s for s in _statements(out) if "CRC64" in s and _FAIL.search(s)]
    assert not crc64, "the copy is called failed under CRC64: %r" % crc64 + _ctx(vol, rc, out)
    assert not _called_failed(out, lcn), "the copy is called failed: %r" % _called_failed(out, lcn) \
        + _ctx(vol, rc, out)
    assert _said_unknown_type(out, lcn, t), \
        "the copy at LCN 0x%x must be said to be unverifiable, unknown checksum type 0x%02x" % (lcn, t) \
        + _ctx(vol, rc, out)
    assert _copy_in_use(vol, cmd) == lcn, "the copy was abandoned for the older one (checkpoint in use 0x%x)" \
        % _copy_in_use(vol, cmd)


@pytest.mark.parametrize("cmd", ["summary", "integrity"])
@pytest.mark.parametrize("t", [0x03, 0xFF], ids=["type0x03", "type0xff"])
@pytest.mark.parametrize("copy", ["primary", "backup"])
def test_n238_supb_unknown_checksum_type_is_cannot_be_verified(vol, copy, t, cmd):
    lcn = vol.geo.supb if copy == "primary" else vol.geo.backups[0]
    plant_unknown_type(vol, lcn, 0x78, t)
    rc, out = vol.run(FOREFST, cmd)
    rows = [ln for ln in _lines(out, lcn) if re.search(r"(?i)SUPB|superblock|\[(primary|backup)", ln)]
    _keep(rows, "the copy is listed" + _ctx(vol, rc, out))
    assert not [ln for ln in rows if re.search(r"(?i)signature OK", ln)], \
        "the copy is labelled 'signature OK': %r" % rows + _ctx(vol, rc, out)
    assert not _called_failed(out, lcn), "the copy is called failed: %r" % _called_failed(out, lcn) \
        + _ctx(vol, rc, out)
    assert _said_unknown_type(out, lcn, t), \
        "the copy at LCN 0x%x must be said to be unverifiable, unknown checksum type 0x%02x" % (lcn, t) \
        + _ctx(vol, rc, out)
    assert rc == 2, "%s must exit 2 (rc=%d)" % (cmd, rc) + _ctx(vol, rc, out)


def test_n238_control_known_checksum_types_are_never_called_unverifiable(vol):
    for cmd in ("summary", "integrity"):
        rc, out = vol.run(FOREFST, cmd)
        lcns = (vol.geo.lo, vol.geo.hi, vol.geo.supb) + vol.geo.backups
        assert rc == 0 and not [s for s in _statements(out) if _UNVERIFIED.search(s)
                                and any(_lcn_re(x).search(s) for x in lcns)], cmd + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 5. A1 widening (VOL-05 a, VOL-06 ii) -- a zeroed primary superblock; the JSON `ok` of each superblock copy
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `supb_validate` returns cksum_ok None without a signature, so a fix keyed on `cksum_ok is False` misses a zeroed
# copy: this RED asserts on what is printed, not on the key.

def _supb_ok_own(v, lcn):
    """A superblock copy's verdict computed here: signature and the module's own CRC32-C."""
    b = v.block(lcn)
    return b[:4] == b"SUPB" and b[SUPB_DESC + 0x28:SUPB_DESC + 0x2C] == _own_digest(b, SUPB_DESC)


def _supb_json(j):
    sup = jget(jget(j, "bootstrap_backups") or {}, "supb")           # acceptance 1.14.0 (K21; N305)
    _fx(isinstance(sup, list) and sup, "no superblock list in the JSON")
    return [dict(s, lcn=jint(jget(s, "lcn")), ok=jget(s, "ok")) for s in sup]


def test_a1w_a_zeroed_primary_superblock_is_not_intact_and_not_a_pass(vol):
    vol.zero(vol.at(vol.geo.supb), CS)                    # battery A5_supb_primary_zero
    rc, out = vol.run(FOREFST, "integrity")
    _keep(rc == 2, "exit 2" + _ctx(vol, rc, out))
    assert not re.search(r"(?i)superblock copies:\s*3 intact", out), "'3 intact' over a zeroed copy" \
        + _ctx(vol, rc, out)
    assert not re.search(r"(?i)verdict:\s*pass", out), "the verdict must not be PASS" + _ctx(vol, rc, out)
    _rc, _out, j = _vjson(vol, FOREFST, "integrity", "--json")
    assert jget(j, "clean") is not True, "integrity --json says clean: %r" % jget(j, "clean")


@pytest.mark.parametrize("cmd", [("summary", "--json"), ("integrity", "--json")], ids=["summary", "integrity"])
@pytest.mark.parametrize("copy", ["primary", "backup"])
def test_a1w_the_superblock_json_ok_is_the_copys_validated_verdict(vol, copy, cmd):
    damage_supb(vol, copy)
    _rc, _out, j = _vjson(vol, FOREFST, *cmd)
    sup = _supb_json(j)
    for s in sup:
        _fx(_supb_ok_own(vol, s["lcn"]) == F.supb_validate(vol.block(s["lcn"]), CS, s["lcn"])["ok"],
            "supb_validate disagrees with this module's own verdict at 0x%x" % s["lcn"])
    bad = [(hex(s["lcn"]), s.get("ok"), _supb_ok_own(vol, s["lcn"])) for s in sup
           if s.get("ok") != _supb_ok_own(vol, s["lcn"])]
    assert not bad, "JSON ok differs from the copy's verdict (lcn, json ok, verdict): %r" % bad


def test_a1w_control_a_zeroed_primarys_json_ok_is_already_false(vol):
    vol.zero(vol.at(vol.geo.supb), CS)
    for cmd in (("summary", "--json"), ("integrity", "--json")):
        _rc, _out, j = _vjson(vol, FOREFST, *cmd)
        assert [(s["lcn"], s.get("ok")) for s in _supb_json(j)] == \
            [(s["lcn"], _supb_ok_own(vol, s["lcn"])) for s in _supb_json(j)], cmd


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 6. A3 widening (VOL-09, decision 25.3) -- refsanalysis summary reports forefst's shared redundancy findings
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# For the backup-superblock FLIP the shared list itself has no entry today (A1 adds it); that node needs both.
# After the critic (R3): every [WARN] line of forefst summary's "Redundancy findings" section must also appear in
# refsanalysis summary -- decision 25.3 is forefst's SHARED list (one source); a refsanalysis-only list passed before.


def _redundancy_warns(text):
    """The texts of the [WARN] lines of a "Redundancy findings" section (empty when there is none)."""
    lines, out = text.splitlines(), []
    for i, ln in enumerate(lines):
        if ln.strip().startswith("Redundancy findings"):
            for l2 in lines[i + 2:]:
                if l2.strip().startswith("---"):
                    break
                m = re.match(r"\s*\[WARN\]\s*(.+?)\s*$", l2)
                if m:
                    out.append(m.group(1))
            break
    return out

def _damage_a3w(v, case):
    if case == "backup-superblock-flipped":
        return damage_supb(v, "backup")
    if case == "backup-superblock-zeroed":
        v.zero(v.at(v.geo.backups[0]), CS)
        return v.geo.backups[0]
    if case == "older-checkpoint-failed":
        damage_chkp(v, v.geo.hi)
        return v.geo.hi
    raise RedFixtureError("unknown case %s" % case)


_A3W = ["backup-superblock-flipped", "backup-superblock-zeroed", "older-checkpoint-failed"]


def _named_damaged(out, lcn):
    return [ln for ln in _lines(out, lcn) if _FAIL.search(ln) or re.search(r"(?i)\bmissing\b", ln)]


@pytest.mark.parametrize("case", _A3W)
def test_a3w_refsanalysis_summary_reports_the_shared_redundancy_findings(vol, case):
    lcn = _damage_a3w(vol, case)
    _rcf, ff = vol.run(FOREFST, "summary")
    rc, out = vol.run(REFSANALYSIS, "summary")
    missing = [w for w in _redundancy_warns(ff) if w not in out]
    assert not missing, "forefst's shared findings missing from refsanalysis summary: %r" % missing \
        + _ctx(vol, rc, out)
    assert _named_damaged(out, lcn), "refsanalysis summary must name the damaged copy at 0x%x" % lcn \
        + _ctx(vol, rc, out)
    assert rc == 2, "refsanalysis summary must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


@pytest.mark.parametrize("case", ["backup-superblock-zeroed", "older-checkpoint-failed"])
def test_a3w_control_forefst_summary_already_reports_these(vol, case):
    lcn = _damage_a3w(vol, case)
    rc, out = vol.run(FOREFST, "summary")
    assert rc == 2 and _named_damaged(out, lcn), _ctx(vol, rc, out)


def test_a3w_control_refsanalysis_summary_is_quiet_on_the_undamaged_volume(vol):
    rc, out = vol.run(REFSANALYSIS, "summary")
    lcns = (vol.geo.lo, vol.geo.hi) + vol.geo.backups
    assert rc == 0 and not [x for x in lcns if _named_damaged(out, x)], _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 7. A3 widening (VOL-11) -- an exception in a root walk is "0 rows", no skip, exit 0 (ra:398-402)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# In-process inside the tool's own subprocess: a runner patches `forefst.walk_bplus` to raise OSError for one root's
# LCN tuple (root 11, Integrity State: read only by the row-count loop), then runs the tool as __main__. The runner
# writes a marker when it fires, so a planted failure that never fires is a fixture error.

_WALKFAIL = r'''
import os, sys, runpy
repo, tool = sys.argv[1], sys.argv[2]
_t = os.environ.get("G2B_FAIL_VLCNS", "")
target = [int(x, 16) for x in _t.split(",")] if _t else None
sys.path.insert(0, repo)
import forefst
_orig = forefst.walk_bplus
def _walk(f, ps, cs, tr, vlcns, *a, **k):
    if target is not None and list(vlcns) == target:
        open(os.environ["G2B_MARK"], "a").write("fired\n")
        raise OSError(5, "planted read failure (group-2b item 7)")
    return _orig(f, ps, cs, tr, vlcns, *a, **k)
forefst.walk_bplus = _walk
sys.argv = [tool] + sys.argv[3:]
runpy.run_path(tool, run_name="__main__")
'''


def _walkfail(v, tmp_path, args, idx):
    """Run refsanalysis with root `idx`'s walk raising (idx None: the runner patches nothing). (rc, out, fired)."""
    runner, mark = str(tmp_path / "walkfail.py"), str(tmp_path / "walkfail.mark")
    with open(runner, "w") as fh:
        fh.write(_WALKFAIL)
    target = _root_list(v.block(v.geo.lo))[idx] if idx is not None else None
    env = dict(os.environ, G2B_FAIL_VLCNS=",".join("%x" % x for x in target) if target else "", G2B_MARK=mark)
    rc, out = _run(runner, os.path.dirname(REFSANALYSIS), REFSANALYSIS, v.path, *args, cwd=str(tmp_path), env=env,
                   cli=v.geo.cli)
    return rc, out, os.path.exists(mark)


def _root_line(out, label):
    return [ln for ln in out.splitlines() if re.match(r"\s*%s\s{2,}" % re.escape(label), ln)]


@pytest.mark.parametrize("cmd", ["summary", "summary++"])
def test_a3w_an_exception_in_a_root_walk_is_unreadable_and_exits_2(vol, cmd, tmp_path):
    rc, out, fired = _walkfail(vol, tmp_path, [cmd], 11)
    _fx(fired, "the planted walk failure did not fire")
    rows = _root_line(out, "Integrity State")
    _keep(len(rows) == 1, "one 'Integrity State' line" + _ctx(vol, rc, out))
    assert "unreadable" in rows[0].lower() and not re.search(r"\b0 rows\b", rows[0]), "printed %r" % rows[0] \
        + _ctx(vol, rc, out)
    assert rc == 2, "the walk failure must exit 2 (rc=%d)" % rc + _ctx(vol, rc, out)


def test_a3w_control_the_runner_alone_changes_nothing(vol, tmp_path):
    rc0, plain = vol.run(REFSANALYSIS, "summary")
    rc, out, fired = _walkfail(vol, tmp_path, ["summary"], None)
    assert not fired and rc == rc0 == 0 and _root_line(out, "Integrity State") == _root_line(plain, "Integrity State")


def test_a3w_control_the_same_failure_on_the_schema_root_already_records_a_skip(vol, tmp_path):
    """The planted exception reaches exit 2 where a walk records its skip (the schema-name walk, ra:405-413)."""
    rc, out, fired = _walkfail(vol, tmp_path, ["summary"], 3)
    assert fired and rc == 2 and re.search(r"(?i)schema table skipped", out), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 8. A4 + decision 25.2 -- any FAIL row of boot --verify / supb --verify exits 2; bare `boot` on a checksum FAIL
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 512e volumes only (N151's false `bps_is_512` row on 4Kn stays N151's). Every plant keeps the copy's checksum valid,
# so only non-checksum rows fail: the named one, and with it (critic N1) `container_aligned` beside
# `container_nonzero`, `self_desc_matches` beside `self_block_matches`, `all_checkpoints_valid` beside
# `checkpoint_count_is_2`.

def _edit_vbr(v, edit):
    p = bytearray(v.read(v.geo.vbr, 512))
    edit(p)
    v.write(v.geo.vbr, _seal_vbr(p))
    v.ops.append("VBR edited and re-sealed")
    _fx(_vbr_ok(v.read(v.geo.vbr, 512)), "the boot sector does not verify after the edit")


_BOOT_ROWS = {"container_nonzero": lambda p: struct.pack_into("<Q", p, 0x40, 0),        # N153's fixboot shape
              "reserved_0x0B_zero": lambda p: p.__setitem__(0x0B, 1)}
_SUPB_ROWS = {"self_block_matches": lambda b: struct.pack_into("<Q", b, 0x20, F.le64(b, 0x20) + 1),
              "checkpoint_count_is_2": lambda b: struct.pack_into("<I", b, 0x74, 3),
              "self_desc_known_size": lambda b: struct.pack_into("<I", b, 0x7C, 0x40)}


def _row_fails(out, row):
    return re.search(r"(?m)^%s\s+FAIL\b" % re.escape(row), out)


# Decision 29 (G2c, a matcher edit sanctioned by the lead): VBR+0x40 = 0 is ONE finding, worded neutrally (never FAIL),
# so `container_nonzero`'s kept property is "boot --verify has one row for that condition, and it does not read OK or
# PASS" -- satisfied by the FAIL row before decision 29 and by its finding row after it.
_VBR40_ROW = re.compile(r"(?i)container_nonzero|VBR\+0x40|container[ _]size")


def _vbr40_row_not_ok(out):
    rows = [ln for ln in out.splitlines() if re.match(r"^[a-z][a-z0-9_]+\s{2,}\S", ln) and _VBR40_ROW.search(ln)]
    return len(rows) == 1 and not re.search(r"(?<![\w-])(?:OK|PASS)(?![\w-])", rows[0])


@pytest.mark.parametrize("row", sorted(_BOOT_ROWS))
def test_a4w_boot_verify_exits_2_on_a_non_checksum_fail_row(vol, row):
    _edit_vbr(vol, _BOOT_ROWS[row])
    rc, out = vol.run(REFSANALYSIS, "boot", "--verify")
    _keep((_vbr40_row_not_ok(out) if row == "container_nonzero" else _row_fails(out, row))      # decision 29
          and re.search(r"(?m)^checksum_match\s+OK\b", out),
          "the %s row reads FAIL and the checksum row OK" % row + _ctx(vol, rc, out))
    assert rc == 2, "boot --verify must exit 2 on a FAIL row (rc=%d)" % rc + _ctx(vol, rc, out)


@pytest.mark.parametrize("row", sorted(_SUPB_ROWS))
def test_a4w_supb_verify_exits_2_on_a_non_checksum_fail_row(vol, row):
    vol.reseal(vol.geo.supb, _SUPB_ROWS[row], SUPB_DESC)  # the copy still passes its self-checksum
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    _keep(_row_fails(out, row), "the %s row reads FAIL" % row + _ctx(vol, rc, out))
    assert rc == 2, "supb --verify must exit 2 on a FAIL row (rc=%d)" % rc + _ctx(vol, rc, out)


def test_a4w_bare_boot_exits_2_when_it_prints_a_checksum_fail(vol):
    _flip_boot_sector(vol, vol.geo.vbr)
    rc, out = vol.run(REFSANALYSIS, "boot")
    _keep(re.search(r"(?im)^Checksum\s.*\[FAIL\]", out), "the checksum line reads [FAIL]" + _ctx(vol, rc, out))
    assert rc == 2, "boot must exit 2 when it prints a checksum FAIL (rc=%d)" % rc + _ctx(vol, rc, out)


def test_a4w_control_the_undamaged_volume_verifies_with_exit_0(vol):
    for args in (("boot",), ("boot", "--verify"), ("supb", "--verify")):
        rc, out = vol.run(REFSANALYSIS, *args)
        assert rc == 0 and not re.search(r"\bFAIL\b", out), args + (_ctx(vol, rc, out),)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 9. B1 (X-11) -- `deleted`'s header lists a failed copy unmarked
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _deleted_header(out):
    rows = [ln for ln in out.splitlines() if re.match(r"\s*Checkpoints:", ln)]
    _keep(len(rows) == 1, "one 'Checkpoints:' header line")
    tail = rows[0].split("VC", 1)[1] if "VC" in rows[0] else ""
    return rows[0], [int(x) for x in re.findall(r"\d+", tail)]


def test_b1w_deleted_header_marks_the_failed_copy_or_lists_the_copy_in_use_first(vol):
    damage_chkp(vol, vol.geo.lo)                          # battery A1_chkp_flip_newest
    rc, out = vol.run(FOREFST, "deleted")
    line, vcs = _deleted_header(out)
    assert _FAIL.search(line) or (vcs and vcs[0] == CLOCK_OLD), \
        "the header must mark the failed copy or list the copy in use (VC %d) first: %r" % (CLOCK_OLD, line)


def test_b1w_control_the_undamaged_header_is_unmarked_newest_first(vol):
    rc, out = vol.run(FOREFST, "deleted")
    line, vcs = _deleted_header(out)
    assert not _FAIL.search(line) and vcs[:1] == [64], line


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 10. N242 -- after a fallback, the primary's SUPB line carries the BACKUP's hash; the JSON does not name the copy
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _own_supb_hashes(v):
    return {lcn: hashlib.sha256(v.block(lcn)).hexdigest() for lcn in (v.geo.supb,) + v.geo.backups}


def _supb_line_hashes(out):
    """{lcn: hash or None}: each `SUPB <role> LCN 0x..` line and the hash on the line right after it, if any."""
    lines, res = out.splitlines(), {}
    for i, ln in enumerate(lines):
        m = re.match(r"\s*SUPB\s+\S+\s+LCN\s+0x([0-9a-f]+)\b", ln, re.I)
        if m:
            h = re.match(r"^\s+([0-9a-f]{64})\s*$", lines[i + 1]) if i + 1 < len(lines) else None
            res[int(m.group(1), 16)] = h.group(1) if h else None
    return res


def _keys_naming_supb_lcn(j, path=""):
    """(key path, value) of every key that names an LCN under a path that names the superblock -- 'supb_used_lcn',
    'superblock_used_lcn', 'supb_hashed_copy.lcn' -- outside the per-copy lists (`bootstrap_backups`, `redundancy`).
    After the critic (S1): the plan's `supb_used_lcn` is an example, not the required name."""
    found = []
    if isinstance(j, dict):
        for k, val in j.items():
            p = path + "." + k
            if re.search(r"(?i)bootstrap_?backups|redundancy", k):
                continue
            if re.search(r"(?i)lcn", k) and re.search(r"(?i)supb|superblock", p) and not isinstance(val, (dict, list)):
                found.append((p, val))
            found += _keys_naming_supb_lcn(val, p)
    elif isinstance(j, list):
        for n, val in enumerate(j):
            found += _keys_naming_supb_lcn(val, "%s[%d]" % (path, n))
    return found


def test_n242_each_superblock_line_carries_its_own_copys_hash(vol):
    vol.zero(vol.at(vol.geo.supb), CS)                    # battery A5_supb_primary_zero
    rc, out = vol.run(FOREFST, "summary")
    own, rows = _own_supb_hashes(vol), _supb_line_hashes(out)
    _fx(set(rows) == set(own), "summary does not list the three superblock copies: %r" % rows)
    bad = ["0x%x carries %s... (%s)" % (lcn, h[:16], ", ".join("0x%x's" % x for x, oh in own.items() if oh == h)
                                        or "no copy's") for lcn, h in rows.items() if h is not None and h != own[lcn]]
    assert not bad, "a SUPB line carries another copy's hash: %r" % bad + _ctx(vol, rc, out)


def test_n242_the_json_names_the_superblock_copy_it_hashed(vol):
    vol.zero(vol.at(vol.geo.supb), CS)
    _rc, _out, j = _vjson(vol, FOREFST, "summary", "--json")
    own = _own_supb_hashes(vol)
    hashed = [lcn for lcn, h in own.items() if h == jget(j, "supb_sha256", F._SUMMARY_KEYS)]
    _fx(len(hashed) == 1, "supb_sha256 is no copy's hash")
    named = _keys_naming_supb_lcn(j)
    assert [p for p, val in named if jint(val) == hashed[0]], \
        "no key names the copy supb_sha256 hashes (LCN 0x%x); keys found: %r" % (hashed[0], named)


def test_n242_control_the_undamaged_volume(vol):
    rc, out = vol.run(FOREFST, "summary")
    own = _own_supb_hashes(vol)
    assert _supb_line_hashes(out).get(vol.geo.supb) == own[vol.geo.supb], _ctx(vol, rc, out)
    _rc, _out, j = _vjson(vol, FOREFST, "summary", "--json")
    assert jget(j, "supb_sha256", F._SUMMARY_KEYS) == own[vol.geo.supb]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 11. N243 -- integrity counts one condition twice (a K041 note defeats the 40-character prefix de-duplication)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _warn_lines(out):
    return [ln for ln in out.splitlines() if "[WARN]" in ln]


def _verdict_count(out):
    m = re.search(r"Verdict:\s*WARN\s*\W+\s*(\d+)\s+warning", out)
    return int(m.group(1)) if m else None


def test_n243_integrity_counts_one_condition_once(vol):
    hi = vol.geo.hi
    vol.write(vol.at(hi, 0x20), b"\0" * 8)
    vol.ops.append("CHKP 0x%x +0x20 zeroed" % hi)
    b = bytearray(vol.block(hi))
    _fx(vol.verifies(hi) is False, "the copy still verifies")
    b[0x20:0x28] = struct.pack("<Q", hi)
    _fx(_own_digest(b, CHKP_DESC) == bytes(vol.block(hi)[CHKP_DESC + 0x28:CHKP_DESC + 0x2C]), "not the K041 shape")
    rc, out = vol.run(FOREFST, "integrity")
    warns = _warn_lines(out)
    same = [ln for ln in warns if _lcn_re(hi).search(ln)]
    _keep(same and _verdict_count(out) is not None, "the copy is a finding" + _ctx(vol, rc, out))
    assert len(same) == 1, "one damaged copy, %d warnings: %r" % (len(same), same) + _ctx(vol, rc, out)
    assert _verdict_count(out) == len(warns), "the verdict counts %r, %d listed" % (_verdict_count(out), len(warns))


def test_n243_control_an_intact_self_reference_is_counted_once(vol):
    damage_chkp(vol, vol.geo.hi)
    rc, out = vol.run(FOREFST, "integrity")
    warns = _warn_lines(out)
    assert len([ln for ln in warns if _lcn_re(vol.geo.hi).search(ln)]) == 1 and _verdict_count(out) == len(warns), \
        _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 12. N244 -- `chkp -v` prints the primary superblock's GUID read raw and unvalidated (ra:1810, :1973)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _guid_lines(out):
    return [ln for ln in out.splitlines() if re.search(r"(?i)volume guid", ln)]


def _is_volume_guid(ln):
    return GUID_RAW.hex() in ln.lower() or GUID in ln.lower()


@pytest.mark.parametrize("case", ["primary-zeroed", "primary-flipped"])
def test_n244_chkp_v_prints_the_guid_of_a_verified_superblock(vol, case):
    if case == "primary-zeroed":
        vol.zero(vol.at(vol.geo.supb), CS)                # battery A5_supb_primary_zero
    else:
        damage_supb(vol, "primary")                       # the A1 primary flip (GUID byte +0x50)
    rc, out = vol.run(REFSANALYSIS, "chkp", "-v")
    rows = _guid_lines(out)
    _keep(rows, "chkp -v prints a Volume GUID" + _ctx(vol, rc, out))
    assert all(_is_volume_guid(ln) for ln in rows), "printed %r; the verified copies hold %s" % (rows, GUID)


def test_n244_control_the_undamaged_volume(vol):
    rc, out = vol.run(REFSANALYSIS, "chkp", "-v")
    rows = _guid_lines(out)
    assert rows and all(_is_volume_guid(ln) for ln in rows), _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 13. N245 -- mapped containers presented as usage (win11refsmini: 'Containers used: 30 / 31 (96.8%)')
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Decision 25.5: the correct keys are ADDED now and the old `utilization_pct` keeps its value until 1.14 (kept).
# The values are those of win11refsmini, measured on the current tools: 31 Container Table rows, 30 of them mapped
# away from the boot region, utilization_pct 96.8.

_MAPPED_NONBOOT, _UTIL_PCT = 30, 96.8
_OLD_CONTAINER_KEYS = {"containers_used", "containers_free", "utilization_pct", "containers_mapped", "container_size"}
_N245_JSON = {"forefst-summary": (FOREFST, ("summary", "--json")),
              "refsanalysis-summary-plus": (REFSANALYSIS, ("summary++", "--json"))}


@IMAGE_ONLY
def test_n245_summary_plus_does_not_present_mapped_containers_as_usage(vol):
    rc, out = vol.run(REFSANALYSIS, "summary++")
    _keep(rc == 0, "exit 0" + _ctx(vol, rc, out))
    used = [ln for ln in out.splitlines() if re.match(r"(?i)\s*containers used\b", ln)]
    assert not used, "the mapped-container count is labelled usage: %r" % used


@IMAGE_ONLY
@pytest.mark.parametrize("which", sorted(_N245_JSON))
def test_n245_the_json_adds_a_key_naming_the_mapped_container_count(vol, which):
    tool, args = _N245_JSON[which]
    _rc, _out, j = _vjson(vol, tool, *args)
    # acceptance 1.14.0 (N245): utilization_pct, containers_used and containers_free are removed with 1.14 (decision
    # 25.5's date); the mapped count keeps its added key
    assert jget(j, "utilization_pct") is None and jget(j, "containers_used") is None, sorted(j)
    old = {F.out_key(k) for k in _OLD_CONTAINER_KEYS}
    added = [k for k, val in j.items() if k not in old and "container" in k.lower() and val == _MAPPED_NONBOOT]
    assert added, "no added key carries the mapped container count %d: %r" % (
        _MAPPED_NONBOOT, {k: val for k, val in j.items() if "container" in k.lower()})


@IMAGE_ONLY
def test_n245_control_forefst_text_already_names_the_boot_region_and_the_mapped_count(vol):
    rc, out = vol.run(FOREFST, "summary")
    _rc, _out, j = _vjson(vol, FOREFST, "summary", "--json")
    assert re.search(r"(?i)boot region", out) and jget(j, "containers_mapped") == _MAPPED_NONBOOT + 1, \
        _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 14. N246 -- 'USN Journal: Inactive' and usn_journal false when the 0x520 table was not read
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def plant_unreadable_520(v):
    """Zero the root page of the system-metadata table (OID 0x520), located through the tool's bootstrap (only to
    find it; the page is checked here: MSB+, its own address)."""
    f, ps, cs, tr, _roots, obj_map, _a, _b, _c = F.bootstrap(v.path, v.geo.ps)
    try:
        _fx(0x520 in obj_map, "no OID 0x520 on this volume")
        plcn = tr.tr(obj_map[0x520][0])
    finally:
        f.close()
    pg = v.read(v.geo.ps + plcn * CS, 0x4000)
    _fx(pg[:4] == b"MSB+", "the 0x520 root page is not an MSB+ page")
    v.zero(v.geo.ps + plcn * CS, 0x4000)


# After the critic (R4): a "USN Journal:" line must exist and say the state is unknown / was not read -- omitting the
# line passed before. S5: the JSON must carry `fs_metadata.usn_journal` = null. For refsanalysis on the
# object-table-root-zeroed case `fs_metadata` is absent today because of N247 (no `vol_detail`), so that node also
# needs N247 (same group); on the 0x520-root-zeroed case the key is present today (false) and checked as it is.
# For the fixer (critic N3): a zeroed 0x520 root page does not raise; "not read" must come from the skip/damage
# registers, not only from an exception or a missing 0x520.
_N246_CASES = {"object-table-root-zeroed": zero_ot_root, "0x520-root-zeroed": plant_unreadable_520}
_USN_UNKNOWN = re.compile(r"(?i)\bunknown\b|not read|could not be read|unreadable")
_N246_TOOLS = {"forefst-summary": (FOREFST, "summary"), "refsanalysis-summary-plus": (REFSANALYSIS, "summary++")}


def _usn_lines(out):
    return [ln for ln in out.splitlines() if re.match(r"\s*USN Journal:", ln)]


@IMAGE_ONLY
@pytest.mark.parametrize("which", sorted(_N246_TOOLS))
@pytest.mark.parametrize("case", sorted(_N246_CASES))
def test_n246_the_usn_state_is_unknown_when_the_metadata_tree_was_not_read(vol, case, which):
    _N246_CASES[case](vol)
    tool, cmd = _N246_TOOLS[which]
    rc, out = vol.run(tool, cmd)
    _keep(re.search(r"(?i)could not be read|unreadable", out), "the unread pages are recorded" + _ctx(vol, rc, out))
    usn = _usn_lines(out)
    bad = [ln for ln in usn if re.search(r"(?i)\binactive\b", ln)]
    assert not bad, "the journal state is printed as a fact over an unread table: %r" % bad + _ctx(vol, rc, out)
    assert usn and all(_USN_UNKNOWN.search(ln) for ln in usn), \
        "a 'USN Journal:' line must say the state is unknown / not read: %r" % usn + _ctx(vol, rc, out)
    _rc, _out, j = _vjson(vol, tool, cmd, "--json")
    fm = jget(j, "fs_metadata")
    assert isinstance(fm, dict) and F.out_key("usn_journal") in fm and jget(fm, "usn_journal") is None, \
        "JSON fs_metadata = %r (usn_journal must be present and null)" % (fm,)


@IMAGE_ONLY
@pytest.mark.parametrize("which", sorted(_N246_TOOLS))
def test_n246_control_a_readable_metadata_tree_gives_the_state_it_holds(vol, which):
    tool, cmd = _N246_TOOLS[which]
    rc, out = vol.run(tool, cmd)
    _rc, _out, j = _vjson(vol, tool, cmd, "--json")
    assert rc == 0 and [ln for ln in _usn_lines(out) if re.search(r"(?i)\binactive\b", ln)] \
        and jget(jget(j, "fs_metadata") or {}, "usn_journal") is False, _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 15. N247 -- summary++ prints 0 for the walk's extended counts when the 0x500 table yields no detail
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# win11refs2g_disableheatgathering: 2 ADS host files, 1 file sharing 2 names, 3 reparse points. With the 0x500
# table's root page zeroed, summary++ prints 0 for each and drops their JSON keys, although `fs_content_summary`
# computed them (ra:439-447). forefst's summary on the same damaged copy is the oracle (fd:6309-6314 gates only the
# version/time fields on the 0x500 table).

_N247_IMAGE = "win11refs2g_disableheatgathering.raw"
_EXT_KEYS = ("ads_entries", "hardlink_extra", "hardlink_names", "hardlink_groups", "encrypted_files",
             "integrity_files", "compressed_files", "snapshots", "snapshot_files")
def _sk(d, name, default=None):
    """A summary key by its internal name (K21, with summary's overrides: ads_entries -> ADSHostFiles)."""
    return jget(d, name, F._SUMMARY_KEYS, default)


_EXT_LABELS = ("ADS host files", "Hard-linked", "Encrypted files", "Integrity objects", "Compressed files",
               "Snapshot versions")


@pytest.fixture
def n247vol(request):
    src = _image_or_skip(_N247_IMAGE)
    os.makedirs(_AB.SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="g2b_n247_", dir=_AB.SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _fx(_AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
        _AB._carve(src, p)
        _fx(os.stat(p).st_blocks * 512 < _AB.MAX_SCRATCH_ALLOCATED, "the scratch copy is too large")
        if request.param == "0x500-root-zeroed":
            f, ps, cs, tr, _r, obj_map, _a, _b, _c = F.bootstrap(p)
            try:
                _fx(0x500 in obj_map, "no OID 0x500")
                off = ps + tr.tr(obj_map[0x500][0]) * cs
            finally:
                f.close()
            with open(p, "r+b") as fh:
                fh.seek(off)
                _fx(fh.read(4) == b"MSB+", "the 0x500 root page is not an MSB+ page")
                fh.seek(off)
                fh.write(b"\0" * 0x4000)
        yield request.param, p, d
    finally:
        if os.path.exists(p):
            os.unlink(p)
        os.rmdir(d)


def _label_values(out):
    return {lab: m.group(1).strip() for lab in _EXT_LABELS
            for m in [re.search(r"(?m)^\s*%s:\s*(.+)$" % re.escape(lab), out)] if m}


def _n247_runs(p, d):
    _rc, ff_text = _run(FOREFST, p, "summary", cwd=d)
    _rc, ff_json = _run(FOREFST, p, "summary", "--json", cwd=d)
    rc, ra_text = _run(REFSANALYSIS, p, "summary++", cwd=d)
    _rc, ra_json = _run(REFSANALYSIS, p, "summary++", "--json", cwd=d)
    ffj, raj = _json_text(ff_json, "forefst summary --json"), _json_text(ra_json, "summary++ --json")
    _fx(_sk(ffj, "ads_entries") == 2 and _sk(ffj, "hardlink_names") == 2, "the volume's extended counts are not "
        "the measured ones (ads 2, hard-link names 2): %r" % {k: _sk(ffj, k) for k in _EXT_KEYS})
    return rc, ff_text, ffj, ra_text, raj


@pytest.mark.parametrize("n247vol", ["0x500-root-zeroed"], indirect=True)
def test_n247_image_summary_plus_keeps_the_walks_extended_counts(n247vol):
    _case, p, d = n247vol
    rc, ff_text, ffj, ra_text, raj = _n247_runs(p, d)
    want, got = _label_values(ff_text), _label_values(ra_text)
    assert got == want, "summary++ text %r, forefst %r" % (got, want)
    assert {k: _sk(raj, k, "missing") for k in _EXT_KEYS} == {k: _sk(ffj, k) for k in _EXT_KEYS}, \
        "summary++ JSON %r, forefst %r" % ({k: _sk(raj, k, "missing") for k in _EXT_KEYS},
                                           {k: _sk(ffj, k) for k in _EXT_KEYS})


@pytest.mark.parametrize("n247vol", ["undamaged"], indirect=True)
def test_n247_image_control_counts_agree_where_the_0x500_table_is_read(n247vol):
    _case, p, d = n247vol
    rc, ff_text, ffj, ra_text, raj = _n247_runs(p, d)
    assert rc == 0 and _label_values(ra_text) == _label_values(ff_text) and \
        {k: _sk(raj, k) for k in _EXT_KEYS} == {k: _sk(ffj, k) for k in _EXT_KEYS}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 16. N249 -- summary++'s snapshot count stops at depth 10 (`_find_snapshot_files`, fd:12220-12231)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A synthetic chain of directories with one real snapshotted file row at the bottom: /testsnapshots/arg.txt of
# win11refs2tsnapshots.raw (read-only; a 1,096-byte resident value with one snapshot), copied as it is. An OID 0x500
# table with one 0x0540 row gives summary++ its `vol_detail` -- without it N247 hides N249 (summary++ prints 0 at
# every depth). Reproduced: at depth 11 and 12 summary++ says 0 where forefst says 1; at depth 9-10 both say 1.
# RESIDUAL (critic S3): DirVol builds at most depth 18 (deeper, its object page overflows), so a fix that only raises
# `_find_snapshot_files`' depth limit (to 20, say) passes this RED. FOR GROUP 2'S CRITIC: check in the diff that
# summary++ takes forefst's own full-walk count (`ext["snapshots"]`, as `ads_entries` already does, ra:615-618) --
# the only fix that also removes the walker's other restriction (directory values of at most 84 bytes).

@functools.lru_cache(maxsize=1)
def _snapshot_row():
    src = _corpus_image("win11refs2tsnapshots.raw")
    if src is None:
        return None
    f, ps, cs, tr, _r, obj_map, _a, _b, _c = F.bootstrap(src)
    try:
        def child(oid, name):
            for kd, vd in F.walk_bplus(f, ps, cs, tr, obj_map[oid], oid=oid):
                if len(kd) > 4 and F.le16(kd, 0) == 0x30 and kd[4:].decode("utf-16-le", "replace") == name:
                    return kd, vd
            raise RedFixtureError("%s not found under 0x%x" % (name, oid))
        _kd, dv = child(0x600, "testsnapshots")
        return child(F.le64(dv, 0x08), "arg.txt")
    finally:
        f.close()


def _deep_volume(path, depth, row):
    kd, vd = row
    snaps = F._parse_snapshots_from_value(vd)
    _fx(len(snaps) == 1 and snaps[0].get("is_true_snapshot", True), "arg.txt does not carry one true snapshot")
    v = _BD.DirVol(log=True)                 # `summary` reads the log (Q-D D3): the volume carries one
    dirs, parent = {0x600: {"name": ""}}, 0x600
    for i in range(depth):
        dirs[0x701 + i] = {"parent": parent, "name": "d%02d" % (i + 1)}
        parent = 0x701 + i
    dirs[parent]["files"] = [_BD._row(kd, vd)]
    v.objects = v.tree(dirs)
    lcn = v.alloc()
    v.objects[0x500] = (lcn, _BD._page(lcn, 0x500, [_BD._row(struct.pack("<HH", 0x540, 0), struct.pack("<II", 0, 0))]))
    return v.write(path)


def _snapshot_counts(path, d):
    _rc, ff = _run(FOREFST, path, "summary", cwd=d, cli=["--partition-start", "0"])
    rc, ra = _run(REFSANALYSIS, path, "summary++", cwd=d, cli=["--partition-start", "0"])
    pick = lambda o: (re.search(r"(?m)^\s*Snapshot versions:\s*(.+)$", o) or [None, None])[1]  # noqa: E731
    _fx(pick(ff) == "1 (across 1 file)",      # N596: the noun takes the count's number
        "forefst does not count the snapshot: %r" % pick(ff))
    return rc, pick(ff), pick(ra), ra


def test_n249_image_summary_plus_counts_snapshots_at_full_depth(tmp_path):
    row = _snapshot_row()
    if row is None:
        pytest.skip("win11refs2tsnapshots.raw not in this tree")
    p = _deep_volume(str(tmp_path / "deep12.raw"), 12, row)
    rc, ff, ra, out = _snapshot_counts(p, str(tmp_path))
    assert ra == ff, "summary++ %r, forefst %r" % (ra, ff) + "\n" + out[-2500:]


def test_n249_image_control_depth_10_agrees(tmp_path):
    row = _snapshot_row()
    if row is None:
        pytest.skip("win11refs2tsnapshots.raw not in this tree")
    p = _deep_volume(str(tmp_path / "deep10.raw"), 10, row)
    rc, ff, ra, out = _snapshot_counts(p, str(tmp_path))
    assert rc == 0 and ra == ff, out[-2500:]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 17. N250, N251, N252, N253 (lands if green)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _norm_warns(out, lcn):
    """The [WARN] lines naming this copy, without the tag and integrity's "redundancy: " prefix (critic S4: one
    builder gives one wording, so the two commands' lines for one condition must be equal)."""
    return [re.sub(r"^\s*\[WARN\]\s*(redundancy:\s*)?", "", ln).strip() for ln in _warn_lines(out)
            if _lcn_re(lcn).search(ln)]


def test_n250_summary_and_integrity_list_each_condition_once(vol):
    apply_b1_case(vol, "clock_divergence")               # B1's shape: +0x10 = 65 on the older copy, re-sealed
    rc, s = vol.run(FOREFST, "summary")
    rc2, i = vol.run(FOREFST, "integrity")
    sw = _norm_warns(s, vol.geo.hi)
    iw = _norm_warns(i, vol.geo.hi)
    _keep(iw, "integrity names the divergence" + _ctx(vol, rc2, i))
    assert len(sw) == len(iw) == 1, "summary %r / integrity %r" % (sw, iw)
    assert sw == iw, "the same condition, two builders: summary %r / integrity %r" % (sw, iw)


def test_n250_control_one_failed_copy_is_listed_once_by_both(vol):
    damage_chkp(vol, vol.geo.hi)
    _rc, s = vol.run(FOREFST, "summary")
    _rc, i = vol.run(FOREFST, "integrity")
    sw, iw = _norm_warns(s, vol.geo.hi), _norm_warns(i, vol.geo.hi)
    assert len(sw) == 1 and sw == iw, (sw, iw)


def _n251_lines(out, ps, backup_off):
    ck = [(ln, int(m.group(1), 16)) for ln in out.splitlines()
          for m in [re.match(r"\s*(?:Checkpoint \[|CHKP\s).*?LCN\s+0x([0-9a-f]+)", ln, re.I)] if m]
    bb = [ln for ln in out.splitlines() if re.search(r"(?i)(boot sector \(backup\)|VBR backup)", ln)]
    ck_ok = ck and all(_addr_re(lcn * CS, ps + lcn * CS).search(ln) for ln, lcn in ck)
    bb_ok = bb and all(_addr_re(backup_off, backup_off - ps).search(ln) for ln in bb)
    return ck, bb, bool(ck_ok), bool(bb_ok)


def test_n251_integrity_checkpoint_and_backup_boot_sector_lines_carry_byte_offsets(vol):
    rc, out = vol.run(FOREFST, "integrity")
    ck, bb, ck_ok, bb_ok = _n251_lines(out, vol.geo.ps, _backup_vbr_offset(vol))
    _keep(ck and bb, "integrity lists the checkpoint and backup boot-sector lines" + _ctx(vol, rc, out))
    assert ck_ok, "a checkpoint line has no byte offset: %r" % [x[0] for x in ck]
    assert bb_ok, "the backup boot-sector line has no byte offset: %r" % bb


def test_n251_control_summary_already_prints_those_offsets(vol):
    rc, out = vol.run(FOREFST, "summary")
    ck, bb, ck_ok, bb_ok = _n251_lines(out, vol.geo.ps, _backup_vbr_offset(vol))
    assert ck_ok and bb_ok, _ctx(vol, rc, out)


def _summary_chkp_lines(out):
    return [ln for ln in out.splitlines() if re.match(r"\s*CHKP\s", ln)]


@pytest.mark.parametrize("slot0_higher", [False, True], ids=["slot0-lower-lcn", "slot0-higher-lcn"])
def test_n252_summary_chkp_lines_show_the_tie(vol, slot0_higher):
    make_tie(vol, slot0_higher)
    rc, out = vol.run(FOREFST, "summary")
    _keep(set(summary_chkp_rows(out)) == {vol.geo.lo, vol.geo.hi},
          "group 5's reader (test_1132_red_mlog_chkp.summary_chkp_rows) reads both CHKP lines" + _ctx(vol, rc, out))
    rows = _summary_chkp_lines(out)
    assert len(rows) == 2 and all(re.search(r"(?i)\btied\b", ln) for ln in rows), rows


def test_n252_control_untied_chkp_lines_say_no_tie_and_are_read_by_group_5(vol):
    rc, out = vol.run(FOREFST, "summary")
    assert set(summary_chkp_rows(out)) == {vol.geo.lo, vol.geo.hi} and \
        not [ln for ln in _summary_chkp_lines(out) if re.search(r"(?i)\btied\b", ln)], _ctx(vol, rc, out)


def test_n253_a_checkpoint_read_error_in_deleted_is_worded_as_such(vol):
    vol.zero(vol.at(vol.geo.lo), 0x4000)                  # battery A2_chkp_zero_newest
    rc, out = vol.run(FOREFST, "deleted")
    _keep(rc == 2, "the recorded skip exits 2 (unchanged by N253)" + _ctx(vol, rc, out))
    bad = [ln for ln in out.splitlines() if "deleted-file candidate" in ln and re.search(r"(?i)\bCHKP\b|checkpoint", ln)]
    assert not bad, "a checkpoint copy's read error is called a deleted-file candidate: %r" % bad


def test_n253_control_no_such_line_on_the_undamaged_volume(vol):
    rc, out = vol.run(FOREFST, "deleted")
    assert rc == 0 and "deleted-file candidate" not in out, _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 18. Help strings (VOL-38; ra:4164-4166, :4172)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _help(cmd, tmp_path):
    rc, out = _run(REFSANALYSIS, "help", cmd, cwd=str(tmp_path))
    _fx(rc == 0 and "--verify" in out, "no help for %s" % cmd)
    return out


def test_help_chkp_verify_names_the_checks_that_decide_its_exit_code(tmp_path):
    out = _help("chkp", tmp_path)
    assert re.search(r"(?i)self-?checksum", out) and re.search(r"(?i)alloc\w*\W+clock", out), out


def test_help_control_chkp_verify_does_run_those_checks(vol):
    rc, out = vol.run(REFSANALYSIS, "chkp", "--verify")
    assert re.search(r"(?im)^\s*\[OK\] CHKP self-checksum", out) and re.search(r"(?im)^\s*\[OK\] Allocator clock", out), \
        _ctx(vol, rc, out)


def test_help_control_supb_verify_row_count_matches_its_help(vol, tmp_path):
    """Control-shaped (the brief): '7-check consistency table' is right today and can only go stale when A4 adds
    rows. IF the help states a count, it must equal the rows `supb --verify` prints on the undamaged volume; a help
    reworded without a number passes (critic S2)."""
    counts = {int(n) for n in re.findall(r"(\d+)-check", _help("supb", tmp_path))}
    rc, out = vol.run(REFSANALYSIS, "supb", "--verify")
    rows = [ln for ln in out.splitlines() if re.match(r"^[A-Za-z][A-Za-z0-9_]+\s+(OK|FAIL|WARN)\b", ln)]
    assert rc == 0 and rows and (not counts or counts == {len(rows)}), (counts, len(rows), rows)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The matchers can go GREEN: a plausible corrected line is accepted, today's line is rejected
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_group2b_matchers_accept_corrected_wording_and_reject_the_current_lines():
    # 1-2: a boot-sector copy named as failed; an upgraded volume's version note is not a failure
    assert not _boot_failed(_own_rows("  VBR backup       LBA 2047 (off 0xffe00)  — DIFFERS", "backup"))
    assert not _boot_failed(_own_rows("  Boot sector (backup):    LBA 2047 — present, DIFFERS from primary, "
                                      "checksum?", "backup"))
    assert not _own_rows("      ↳ version mismatch: primary v3.14, backup v3.4 — an UPGRADE (the backup keeps the "
                         "ORIGINAL pre-upgrade version) or VBR tampering.", "backup")
    assert _boot_failed(_own_rows("  VBR backup       LBA 2047 (off 0xffe00)  — checksum FAILED", "backup"))
    assert _boot_failed(_own_rows("  Boot sector (primary):   LBA 0 — checksum FAILED", "primary"))
    assert _boot_failed(_own_rows("  [WARN] the primary boot sector (LBA 0) failed its checksum", "primary"))
    # R1: the critic's wrong fix -- the intact backup blamed -- is not the primary's line
    wrong = ("  Boot sector (primary):   LBA 0 — checksum?\n"
             "  Boot sector (backup):    LBA 2047 — present, DIFFERS from primary, checksum FAILED")
    assert not _boot_failed(_own_rows(wrong, "primary")) and _boot_failed(_own_rows(wrong, "backup"))
    # C2 RED re-check: a statement about the copy read that blames the primary is caught although `_own_rows` leaves
    # it out; one that blames only the backup, and R1's backup row, are not
    false = "  [WARN] the primary boot sector at offset 0x0 is damaged; the volume was read from the backup boot sector"
    assert not _own_rows(false, "primary") and _read_line_blames(false, "primary", _own_rows(false, "primary"))
    fine = "  [WARN] the backup boot sector failed its checksum; the volume is read from the primary boot sector"
    assert not _read_line_blames(fine, "primary", _own_rows(fine, "primary"))
    assert not _read_line_blames(wrong, "primary", _own_rows(wrong, "primary"))
    # R2: a failure statement about the copy that does not say "cannot be verified"
    assert _called_failed("[WARN] the newest checkpoint (LCN 0x48, vclock 64) failed its self-checksum (unknown "
                          "checksum type 0x3); the volume was read from an OLDER checkpoint (LCN 0x88)", 0x48)
    assert not _called_failed("  CHKP primary     LCN 0x48 (offset 0x48000)  — checksum cannot be verified "
                              "(unknown checksum type 0x3)", 0x48)
    # R3: the [WARN] lines of forefst's section
    assert _redundancy_warns("x\nRedundancy findings (exit code 2)\n" + "-" * 78 + "\n  [WARN] a b\n  [WARN] c\n"
                             + "-" * 78 + "\n  [WARN] later") == ["a b", "c"]
    assert _redundancy_warns("no section") == []
    # S4: two wordings of one condition are not equal; integrity's prefix is ignored
    assert _norm_warns("  [WARN] redundancy: secondary checkpoint @ 0x88 invalid", 0x88) == \
        _norm_warns("  [WARN] secondary checkpoint @ 0x88 invalid", 0x88)
    # 3-4: "cannot be verified" with the type, on a statement naming the copy
    fixed = "  CHKP primary     LCN 0x48 (offset 0x48000)  — checksum cannot be verified (unknown checksum type 0x3)"
    assert _said_unknown_type(fixed, 0x48, 3) and not _said_unknown_type(fixed, 0x48, 5)
    assert _said_unknown_type(fixed.replace("0x3)", "0xff)"), 0x48, 0xFF)
    assert not _said_unknown_type("  SUPB primary     LCN 0x1e (offset 0x1e000)  — signature OK", 0x1E, 3)
    # 10: the hash right under each SUPB line; keys that name the hashed copy
    txt = ("  SUPB primary     LCN 0x1e (offset 0x1e000)  — BAD\n      " + "a" * 64 +
           "\n  CHKP primary     LCN 0x48 (offset 0x48000)  — checksum OK\n      " + "b" * 64)
    assert _supb_line_hashes(txt) == {0x1E: "a" * 64}
    assert _supb_line_hashes(txt.replace("\n      " + "a" * 64, "", 1)) == {0x1E: None}
    assert _keys_naming_supb_lcn({"supb_sha256": "x", "supb_used_lcn": 253}) == [(".supb_used_lcn", 253)]
    assert _keys_naming_supb_lcn({"superblock_used_lcn": 253}) == [(".superblock_used_lcn", 253)]
    assert _keys_naming_supb_lcn({"supb_hashed_copy": {"lcn": 253}}) == [(".supb_hashed_copy.lcn", 253)]
    assert not _keys_naming_supb_lcn({"supb_sha256": "x", "bootstrap_backups": {"supb": [{"lcn": 253}],
                                                                                "checkpoint_used_lcn": 136}})
    # 9: the deleted header
    assert _deleted_header("  Checkpoints:  2 (VC: 63, 64)")[1] == [63, 64]
    # 11: the verdict count
    assert _verdict_count("Verdict: WARN — 2 warning(s) (incl. redundancy)") == 2
    # 15: the extended-count labels
    assert _label_values("  ADS host files:     2\n  Hard-linked:        1 file sharing 2 names") == \
        {"ADS host files": "2", "Hard-linked": "1 file sharing 2 names"}
    # 17 (N251): an offset on a checkpoint line and on the backup boot-sector line
    ck, bb, ck_ok, bb_ok = _n251_lines("  Checkpoint [PRIMARY  ]:   LCN 0x48 (offset 0x48000) — checksum OK\n"
                                       "  Boot sector (backup):    LBA 2047 (offset 0xffe00) — checksum OK", 0, 0xFFE00)
    assert ck_ok and bb_ok
    ck, bb, ck_ok, bb_ok = _n251_lines("  Checkpoint [PRIMARY  ]:   LCN 0x48 — checksum OK\n"
                                       "  Boot sector (backup):    LBA 2047 — checksum OK", 0, 0xFFE00)
    assert not ck_ok and not bb_ok


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 19. Decision 26 (group 2 review F1 / R1) -- no superblock copy verifies: read the primary anyway, exit 2
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The primary's +0x50 (one GUID bit) is flipped: its signature and checkpoint list are intact, its self-checksum
# fails. Both backups are zeroed, so no copy verifies (a partial acquisition that lacks the end of the volume looks
# the same). 1.13.1 read this volume (`files` rc 0); group 2's A1 refuses it in every command with exit 1 and a
# `--partition-start` hint, the diagnostic `supb -v` included (`parse_supb` raises, fd:744-749). PLAN_1.13.2
# decision 26: read the primary anyway (as decision 20.8 does for checkpoints), report "no superblock copy passes its
# self-checksum; read from the primary, which failed", exit 2 -- never 1 for a volume that can be read -- and give no
# `--partition-start` hint while the SUPB signature is present.
#
# Each node first runs the same command on the UNDAMAGED volume and requires its "the volume is read" oracle there
# (`_fx`), so the oracle cannot be vacuous; `files` must list exactly what it listed before the damage.

_D26_RUNS = {
    "files": (FOREFST, ("files",)),
    "summary": (FOREFST, ("summary",)),
    "integrity": (FOREFST, ("integrity",)),
    "ra-supb-v": (REFSANALYSIS, ("supb", "-v")),
    "ra-summary": (REFSANALYSIS, ("summary",)),
}
_PS_HINT = re.compile(r"--partition-start")
_NO_SUPB_VERIFIES = re.compile(r"(?i)\b(?:no|none of the)\s+(?:superblock|SUPB)(?:\s*\(SUPB\))?\s+cop(?:y|ies)\s+"
                               r"(?:pass(?:es)?|verif(?:y|ies))\b")
_ZERO_GUID = "00000000-0000-0000-0000-000000000000"


def _d26_statements(out):
    """Statements that say decision 26's finding: no superblock copy passes (verifies), the volume is READ from the
    primary, and that copy failed."""
    return [s for s in _statements(out) if _NO_SUPB_VERIFIES.search(s) and re.search(r"(?i)\bprimary\b", s)
            and re.search(r"(?i)\bread\b", s) and _FAIL.search(s)]


def _files_listing(out):
    """`files`' CSV on stdout: the header and every ObjectRef row (the log lines on stderr are not part of it)."""
    return [ln for ln in out.splitlines() if ln.startswith("ObjectRef,") or re.match(r"^0x[0-9a-f]+:0x[0-9a-f]+,", ln)]


def _d26_reads(v, key, out, before):
    """[(property, holds)] -- what shows that the volume was READ, per command. `before` is the same command's output
    on the undamaged volume."""
    g = v.geo
    if key == "files":
        return [("the same CSV listing as on the undamaged volume", _files_listing(out) == _files_listing(before)),
                ("the same entry count", re.findall(r"Done\. (\d+) entr(?:y|ies)", out) ==
                 re.findall(r"Done\. (\d+) entr(?:y|ies)", before))]
    if key in ("summary", "integrity"):
        return [("the newest checkpoint is read (vclock %d, checksum OK)" % CLOCK_NEW,
                 bool(_reads_checkpoint(out, g.lo, CLOCK_NEW)))]
    if key == "ra-supb-v":
        return [("the superblock shown is the primary (the copy read)",
                 bool(re.search(r"(?m)^SUPB offset:\s+0x%x\s*$" % v.at(g.supb), out))),
                ("its checkpoint list is read",
                 bool(re.search(r"checkpoint_in_use\s+checkpoint #1 @ 0x%x \(vc=%d\b" % (v.at(g.lo), CLOCK_NEW), out)))]
    if key == "ra-summary":
        return [("the checkpoint in use is read", _virtual_clock(out) == CLOCK_NEW
                 and bool(re.search(r"Copy in use:\s+LCN 0x%x\b" % g.lo, out)))]
    raise RedFixtureError("no oracle for %s" % key)


def _d26_before(v, key):
    tool, args = _D26_RUNS[key]
    rc, before = v.run(tool, *args)
    _fx(rc == 0, "%s: the undamaged volume does not exit 0 (rc=%d)" % (key, rc) + _ctx(v, rc, before))
    _fx(all(ok for _p, ok in _d26_reads(v, key, before, before)), "%s: the read oracle fails on the undamaged "
        "volume: %r" % (key, _d26_reads(v, key, before, before)) + _ctx(v, rc, before))
    _fx(not _PS_HINT.search(before) and not _d26_statements(before), "%s: the undamaged output already carries a "
        "hint or the finding" % key + _ctx(v, rc, before))
    if key == "files" and v.geo.kind == "image":
        _fx(len(_files_listing(before)) > 1, "files lists no entry on the undamaged image")
    return before


def damage_d26(v):
    """Flip the primary's +0x50 (one GUID bit) and zero both backups: no superblock copy verifies, and the primary
    keeps its signature and its checkpoint list."""
    g = v.geo
    v.flip(v.at(g.supb, 0x50))
    for b in g.backups:
        v.zero(v.at(b), CS)
    p = v.block(g.supb)
    _fx(p[:4] == b"SUPB" and v.refs(g.supb) == [g.lo, g.hi], "the primary lost its signature or checkpoint list")
    _fx(v.verifies(g.supb) is False and not _supb_ok_own(v, g.supb), "the primary still verifies")
    _fx(all(not any(v.block(b)) and not F.supb_validate(v.block(b), CS, b)["ok"] for b in g.backups),
        "a backup copy still verifies")


@pytest.mark.parametrize("key", sorted(_D26_RUNS))
def test_d26_no_verified_superblock_copy_reads_the_primary_says_so_and_exits_2(vol, key):
    tool, args = _D26_RUNS[key]
    before = _d26_before(vol, key)
    damage_d26(vol)
    rc, out = vol.run(tool, *args)
    _keep(_named_failed(out, vol.geo.supb, r"\bprimary\b"), "the failed primary is named by role and LCN"
          + _ctx(vol, rc, out))
    assert rc == 2, "decision 26: a volume readable from its primary superblock exits 2, never 1 (rc=%d)" % rc \
        + _ctx(vol, rc, out)
    assert not _PS_HINT.search(out), "no --partition-start hint while the SUPB signature is present" \
        + _ctx(vol, rc, out)
    assert _d26_statements(out), "the finding must be said: no superblock copy passes its self-checksum; read from " \
        "the primary, which failed" + _ctx(vol, rc, out)
    missing = [p for p, ok in _d26_reads(vol, key, out, before) if not ok]
    assert not missing, "the volume must be read: %r" % missing + _ctx(vol, rc, out)
    if key in ("summary", "ra-summary"):
        assert _guid(out) not in (None, _ZERO_GUID), "a zeroed GUID is not the volume's GUID: the view is read from " \
            "the primary (%r)" % _guid(out) + _ctx(vol, rc, out)


# `_st_s1` (C2 ST-S1's RED mark for the nodes B15's decided output changed) removed in step C2, area supb


# RED 1.13.2 B15 (C2 ST-S1 a2): both backups verify with equal +0x68: the volume is read from end-2 (Q3); the tool
# reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
@pytest.mark.parametrize("key", sorted(_D26_RUNS))
def test_d26_control_backups_that_verify_are_still_the_copy_read(vol, key):
    """A1, kept: the primary fails its self-checksum, both backups verify -- the volume is read from end-2 (C2 ST-S1
    (a2): Q3, equal +0x68; it was the tool's first backup, end-3), exit 2, no decision-26 statement, no hint, the
    verified GUID."""
    tool, args = _D26_RUNS[key]
    b0 = vol.geo.backups[1]                                      # C2 ST-S1 (a2): end-2
    damage_supb(vol, "primary")
    rc, out = vol.run(tool, *args)
    assert rc == 2, _ctx(vol, rc, out)
    assert [s for s in _statements(out) if _lcn_re(b0).search(s) and re.search(r"(?i)\bbackup\b", s)
            and re.search(r"(?i)\bread\b", s)], "the backup copy read is named" + _ctx(vol, rc, out)
    assert not _d26_statements(out) and not _PS_HINT.search(out), _ctx(vol, rc, out)
    if key in ("summary", "ra-summary"):
        assert _guid(out) == GUID, _ctx(vol, rc, out)
    if key == "ra-supb-v":
        assert re.search(r"(?m)^SUPB offset:\s+0x%x\s*$" % vol.at(b0), out), _ctx(vol, rc, out)


def test_d26_control_an_intact_primary_with_both_backups_zeroed(vol):
    """The backups' damage alone: read from the primary as before (`files` and `supb -v` exit 0; the summaries and
    `integrity` exit 2 for the missing backups, as today), never the decision-26 statement, never the hint."""
    befores = {k: _d26_before(vol, k) for k in _D26_RUNS}
    for b in vol.geo.backups:
        vol.zero(vol.at(b), CS)
    _fx(vol.verifies(vol.geo.supb) is True, "the primary does not verify")
    want = {"files": 0, "ra-supb-v": 0, "summary": 2, "integrity": 2, "ra-summary": 2}
    for key, (tool, args) in sorted(_D26_RUNS.items()):
        rc, out = vol.run(tool, *args)
        assert rc == want[key], key + _ctx(vol, rc, out)
        assert not _d26_statements(out) and not _PS_HINT.search(out), key + _ctx(vol, rc, out)
        missing = [p for p, ok in _d26_reads(vol, key, out, befores[key]) if not ok]
        assert not missing, key + " %r" % missing + _ctx(vol, rc, out)


def test_d26_control_no_superblock_signature_anywhere_still_exits_1_with_the_hint(vol):
    """Out of decision 26's scope, and kept: with no SUPB signature at any copy there is no checkpoint list to read;
    the run stops with exit 1 and the --partition-start hint."""
    vol.zero(vol.at(vol.geo.supb), CS)
    for b in vol.geo.backups:
        vol.zero(vol.at(b), CS)
    for tool, args in ((FOREFST, ("files",)), (REFSANALYSIS, ("supb", "-v"))):
        rc, out = vol.run(tool, *args)
        assert rc == 1 and _PS_HINT.search(out) and not _d26_statements(out), _ctx(vol, rc, out)


def test_d26_matchers_accept_the_decided_wording_and_reject_todays_lines():
    ok = ["[forefst] WARNING: no superblock copy passes its self-checksum (backups: LCN 0xfd: no SUPB signature); "
          "this view is read from the primary at LCN 0x1e (offset 0x1e000), which FAILED its self-checksum (CRC32-C)",
          "no SUPB copy verifies; read from the primary, which failed",
          "  [WARN] the primary superblock (SUPB) at LCN 0x1e (offset 0x1e000) failed its self-checksum (CRC32-C); "
          "no superblock copy passes its self-checksum, so the volume is read from this copy",
          "none of the superblock copies pass; the view is read from the primary superblock, which failed"]
    for s in ok:
        assert _d26_statements(s), s
    bad = ["forefst: error: the primary superblock (SUPB) at LCN 0x1e (offset 0x1e000) is not usable (self-checksum "
           "FAILED (CRC32-C)), and no usable backup superblock was found (LCN 0xfd: no SUPB signature; LCN 0xfe: no "
           "SUPB signature). If this is a raw partition image, check --partition-start",
           "  [WARN] the primary superblock (SUPB) at LCN 0x1e (offset 0x1e000) failed its self-checksum (CRC32-C); "
           "the volume is read from the backup copy at LCN 0xfd",
           "  [WARN] the backup superblock (SUPB) at LCN 0xfd (offset 0xfd000) is missing or damaged (all zeros)",
           "  [WARN] fewer than 2 intact SUPB copies located",
           "no superblock copy passes its self-checksum; the volume cannot be read"]
    for s in bad:
        assert not _d26_statements(s), s
    assert _PS_HINT.search(bad[0])
    csv = "ObjectRef,FullPath\n0x709:0x0,test/t3/tb\n[forefst] Done. 1 entries\n0x70a:0x2,a"
    assert _files_listing(csv) == ["ObjectRef,FullPath", "0x709:0x0,test/t3/tb", "0x70a:0x2,a"]
