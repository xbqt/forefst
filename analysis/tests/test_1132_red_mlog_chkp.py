"""1.13.2 RED cases, group mlog_chkp: plan rows A7 and C6, running-log rows N137, N144 and N190, and F11/E118.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` rows A7 and C6 (section 2), the fourth revision (top), section 5
"RED first" and decision 19 (the maintainer's bar: every RED fails on 1.13.1 BECAUSE of the defect, not because of
an artefact, and is independently confirmed). Binding labels and errata drafts: `DEEP_CHECK_VERDICT.md` (sections
6-8). Running log: N136, N137, N141, N143, N144, N190. Report, with the observed or expected failure of every node:
`analysis/reports/v1.13.2/red/RED_mlog_chkp.md`.

What each RED asserts (the row's acceptance, as the fourth revision and the deep check set it)
------------------------------------------------------------------------------------------------
A7    `mlog --stats` compares the tail of the CURRENT log instance with control +0x20 (the log end). Records missing
      from blocks that were actually written -> exit 2 with a finding that names the MLog and the LSN(s); records
      missing inside image holes -> exit 2 too, the hole stated with the cause left open ("not captured, or zero on
      the disk"; C8 = B, the maintainer, 2026-10-01, replacing "unreadable, not exit 2"); log space BELOW the log
      start is not needed and is no finding. Records whose format magic or UUID
      differ from the control area's do not count (an earlier instance must not mask the loss). The finding never
      calls the records "destroyed" (DEEP_CHECK_VERDICT section 6 "must not be written", item 4).
C6    The control area prints +0x18 as "Log start" and +0x20 as "Log end", each with its full LSN; "Generation" is
      not printed for +0x20's low half (the block offset); +0x38 is the "Log open count"; no "LSN oldest", "Write
      counter" or "tail" label; mlog.md labels the same fields the same way, the record header and control-page
      header +0x20 as the open count; errata record the relabel; the published Known issues stop calling +0x18 the
      tail.
N137  `mlog -v`, `mlog --csv`, `mlog --json`, `mlog --parse -v` and `timeline --source MLOG` present only records of
      the control area's log instance (format magic AND UUID).
N144  `mlog --stats` prints an intact MLog control copy as verified on 64 KiB-cluster volumes.
F11   (E118) every checkpoint hash row (`summary`, `fastsummary --json`, refsanalysis `chkp`) hashes ONE cluster.
N190  (E118) `export metadata` writes one cluster per checkpoint, so a 64K bundle carries no user-file clusters.
E118  chkp.md states the record/allocation split; an erratum records it; the published advice stops telling the
      examiner to hash max(16 KiB, cluster size) bytes.

Kinds of node
-------------
* unit -- in-process, on synthetic bytes. The MLog cases build a log area from bytes in ``tmp_path`` with this
  module's own codec (control copies, data records, the XOR fold of LogChecksumBlock) and run ``F.cmd_mlog``
  in-process with three volume-layer functions patched: ``bootstrap`` (returns the synthetic file),
  ``get_mlog_info`` (returns where the log is) and ``build_oid_path_map`` (no directory tree). Everything the
  item changes -- control parse, block scan, record parse, verification, printing, the exit rule -- is the real
  code. A guard checks the patched functions were called, so a refactor that bypasses them is a fixture error,
  not a pass. The doc cases read `docs/` and `analysis/errata.md` statically.
* ``[synthetic]`` -- the real CLI in a subprocess on the 1 MiB ReFS 3.14 volume of `test_1132_red_a_bootstrap.py`
  (imported, not copied). No corpus image is read.
* ``..._on_image_...`` / ``[image-...]`` -- the real CLI on a corpus image, read-only, or on a hole-preserving
  scratch copy damaged to order under ``$FOREFST_RED_SCRATCH`` (default: ``forefst_red_scratch`` in the system temp directory)
  and deleted by exact path when the test ends. Skipped when the image is absent.

``pytest -k "not image"`` runs the unit and synthetic nodes only.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``. The fix commit removes the mark; an XPASS fails the
  run. Only a plain ``assert`` states the acceptance.
* Anything else raises ``RedFixtureError`` or ``KeptPropertyBroken`` (not AssertionErrors): a base that is not what
  the case needs (checked from the bytes BEFORE any damage, and the damage checked after), a crash or a timeout,
  a patched layer the tool no longer calls, or a property 1.13.1 already has and the fix must keep.
* Expected values come from this module's own reads: LSNs, magics and UUIDs from the log blocks, the fold from
  its own implementation of LogChecksumBlock (refs_win11.decomp.c:86831-86866), hashes from its own reads of each
  checkpoint cluster. Nothing expected is taken from the tool under test.
* Controls (not xfail) pass on 1.13.1 and must keep passing. They show the fixture's damage is visible to a sound
  code path, and they stop a RED from being passed by a blanket message (a finding on every log, "verified"
  printed for a damaged copy, a hash row that was always one cluster).
"""
import contextlib
import csv
import hashlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import traceback
import uuid
from collections import Counter

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (synthetic volume, carve, exceptions)
from test_1132_red_a_verdicts import _fresh_registers, _rc_escalate   # noqa: E402  (one register list)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
FOREFST, REFSANALYSIS = AB.FOREFST, AB.REFSANALYSIS
SCRATCH = AB.SCRATCH
TIMEOUT = 1800                                           # millionsofactions is 2 TiB logical


def _red(item, why):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason="RED 1.13.2 %s: %s" % (item, why))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# An MLog codec of this module's own (the tool's code is not used to build or to check a fixture)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

MLOG_BLK = 0x1000
MAGIC_A, MAGIC_B = 0x5E524606, 0x6D790647                 # the two instances of win11refs2gtargeted_reformated
UUID_A = uuid.UUID("050d8f95-0000-4000-8000-00000000000a").bytes_le
UUID_B = uuid.UUID("c2fb82a9-0000-4000-8000-00000000000b").bytes_le


def le32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def le64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def _fold(block):
    """LogChecksumBlock over ONE 4 KiB log block with the chain seed 0 (a one-block record): four u64 lanes XORed,
    folded to 32 bits, the 8-byte field at entry header +0x08 zeroed first (LogVerifyChecksumEntryHeader)."""
    eh = le32(block, 0x54)
    w = bytearray(block[:MLOG_BLK])
    struct.pack_into("<Q", w, eh + 8, 0)
    lanes = [0, 0, 0, 0]
    for i in range(MLOG_BLK // 8):
        lanes[i & 3] ^= struct.unpack_from("<Q", w, i * 8)[0]
    v = lanes[0] ^ lanes[1] ^ lanes[2] ^ lanes[3]
    return (v >> 32) ^ (v & 0xFFFFFFFF)


def _block_header(magic, uid, opens, lsn, prev):
    b = bytearray(MLOG_BLK)
    b[0:4] = b"MLog"
    struct.pack_into("<III", b, 4, magic, 1, MLOG_BLK)
    b[0x10:0x20] = uid
    struct.pack_into("<IIQQII", b, 0x20, opens, 0, lsn, prev, 1, 1)     # +0x20 open count, +0x28 LSN, +0x30 prev
    struct.pack_into("<I", b, 0x54, 0x78)
    return b


def _seal(b):
    struct.pack_into("<Q", b, 0x78 + 8, _fold(b))
    return bytes(b)


def control_block(magic, uid, seq, ds, de, start, end, opens):
    """A type-1 control record laid out like win11refsmini's (payload at page+0xB0, length 0xE48)."""
    b = _block_header(magic, uid, opens, 0, 0)
    struct.pack_into("<I", b, 0x78 + 0x20, 0xE48)
    struct.pack_into("<I", b, 0x78 + 0x28, 0x38)
    struct.pack_into("<I", b, 0x78 + 0x30, 1)
    p = 0xB0
    struct.pack_into("<QQQQQ", b, p, seq, ds, de, start, end)            # +0x18 log start, +0x20 log end
    b[p + 0x28:p + 0x38] = uid
    struct.pack_into("<IIII", b, p + 0x38, opens, 1, 1, 0x3E)            # +0x38 open count, +0x3C flags
    return _seal(b)


def data_block(magic, uid, opens, lsn, prev, opcode=0x04):
    """A type-2 data record carrying one redo block with one committed redo record (start+commit flags)."""
    b = _block_header(magic, uid, opens, lsn, prev)
    rec = bytearray(0x38)
    struct.pack_into("<II", rec, 0, 0x38, opcode)
    struct.pack_into("<I", rec, 0x2C, 3)
    payload = struct.pack("<II", 0x38, 8) + bytes(rec)                   # total_size, first_off, the record
    struct.pack_into("<Q", b, 0x78, lsn)
    struct.pack_into("<Q", b, 0x78 + 0x18, prev)
    struct.pack_into("<I", b, 0x78 + 0x20, len(payload))
    struct.pack_into("<I", b, 0x78 + 0x28, 0x38)
    struct.pack_into("<I", b, 0x78 + 0x30, 2)
    b[0xB0:0xB0 + len(payload)] = payload
    return _seal(b)


def lsn(gen, off):
    return (gen << 32) | off


def parse_block(b):
    """This module's reader for one 4 KiB MLog block (used on the corpus images as well)."""
    if len(b) < 0x100 or b[:4] != b"MLog":
        return None
    eh = le32(b, 0x54)
    if eh + 0x34 > len(b):
        return None
    d = {"magic": le32(b, 4), "uuid": bytes(b[0x10:0x20]), "opens": le32(b, 0x20), "lsn": le64(b, 0x28),
         "prev": le64(b, 0x30), "type": le32(b, eh + 0x30), "stored": le64(b, eh + 8), "fold": _fold(b)}
    if d["type"] == 1:
        p = eh + le32(b, eh + 0x28)
        d.update(seq=le64(b, p), ds=le64(b, p + 8), de=le64(b, p + 0x10), start=le64(b, p + 0x18),
                 end=le64(b, p + 0x20), open_count=le32(b, p + 0x38))
    return d


# ─── a synthetic log area ─────────────────────────────────────────────────────────────────────────────────────

ZERO = b"\0" * MLOG_BLK


class SynLog:
    """Control copies at clusters 1 and 2; the data area at clusters [16, 16 + 128 blocks); data-area block k holds
    the record whose LSN offset is k (the driver's invariant lo(LSN) == block index, 885,709/885,709 in F5).
    Every block that is neither a record nor a hole is WRITTEN as zeros, as a zero-initialised log area is."""
    DS = 16
    NBLK = 0x80

    def __init__(self, path, cs=0x1000):
        self.path, self.cs = str(path), cs
        self.bpc = cs // MLOG_BLK
        self.de = self.DS + -(-self.NBLK // self.bpc)
        self.blocks = {}
        self.ctrl = None

    def run(self, first, last, gen, opens=3, magic=MAGIC_A, uid=UUID_A, session_start=False):
        for k in range(first, last + 1):
            prev = 0 if (k == first and session_start) else lsn(gen, k - 1)
            self.blocks[k] = data_block(magic, uid, opens, lsn(gen, k), prev)
        return self

    def zero(self, first, last):
        for k in range(first, last + 1):
            self.blocks[k] = ZERO
        return self

    def hole(self, first, last):
        for k in range(first, last + 1):
            self.blocks[k] = None
        return self

    def control(self, start, end, opens=3, magic=MAGIC_A, uid=UUID_A):
        self.ctrl = [control_block(magic, uid, s, self.DS * self.bpc, self.de * self.bpc, start, end, opens)
                     for s in (51, 50)]                       # the payload's range in 4 KiB blocks, as the volumes hold it
        return self

    def block_off(self, k):
        return self.DS * self.cs + k * MLOG_BLK

    def cluster_of(self, k):
        return self.DS + k // self.bpc

    @property
    def info(self):
        return {"oid": 9, "rows": 2, "data_start_lcn": self.DS, "data_end_lcn": self.de,
                "data_size_clusters": self.de - self.DS, "ctrl_plcn_0": 1, "ctrl_plcn_1": 2}

    def write(self):
        _fx(self.ctrl is not None, "SynLog: no control area")
        with open(self.path, "wb") as fh:
            fh.truncate((self.de + 2) * self.cs)
            for i, c in enumerate(self.ctrl):
                fh.seek((1 + i) * self.cs)
                fh.write(c + b"\0" * (self.cs - len(c)))              # a control cluster: 4 KiB + written zeros
            for k in range(self.NBLK):
                b = self.blocks.get(k, ZERO)
                if b is None:
                    continue
                fh.seek(self.block_off(k))
                fh.write(b)
        for k, b in self.blocks.items():                                 # the layout is what the case says
            layout = _holes(self.path, self.block_off(k), MLOG_BLK)
            _fx((layout == [(self.block_off(k), self.block_off(k) + MLOG_BLK)]) == (b is None),
                "block %d: hole layout %r does not match the case" % (k, layout))
        return self


def _holes(path, off, n):
    """[(a, b)] image-hole ranges inside [off, off+n), by SEEK_DATA/SEEK_HOLE."""
    fd = os.open(path, os.O_RDONLY)
    out, pos, end = [], off, off + n
    try:
        while pos < end:
            try:
                d = os.lseek(fd, pos, os.SEEK_DATA)
            except OSError:
                out.append((pos, end))
                break
            if d >= end:
                out.append((pos, end))
                break
            if d > pos:
                out.append((pos, d))
            pos = min(os.lseek(fd, d, os.SEEK_HOLE), end)
    finally:
        os.close(fd)
    return out


# ─── running cmd_mlog in-process on a SynLog ──────────────────────────────────────────────────────────────────

class _IdentityTr:
    def tr(self, x):
        return x


def mlog_inproc(monkeypatch, log, *args):
    """(escalated rc, stdout + stderr) of `mlog <args>` on the synthetic log area."""
    calls = Counter()

    def _boot(image, partition_start=None):
        calls["bootstrap"] += 1
        return open(log.path, "rb"), 0, log.cs, _IdentityTr(), [], {}, 3, 14, []

    def _info(f, ps, cs, tr, obj_map):
        calls["get_mlog_info"] += 1
        return dict(log.info)

    monkeypatch.setattr(F, "bootstrap", _boot)
    monkeypatch.setattr(F, "get_mlog_info", _info)
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: {})
    _fresh_registers(monkeypatch)
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = F.cmd_mlog(log.path, list(args), None)
    except SystemExit as e:
        raise RedFixtureError("cmd_mlog exited through die() (%r):\n%s" % (e.code, err.getvalue()[-2000:]))
    except Exception:
        raise RedFixtureError("cmd_mlog crashed (a crash is never the defect under test):\n" + traceback.format_exc())
    _fx(calls["bootstrap"] == 1 and calls["get_mlog_info"] >= 1,
        "cmd_mlog no longer reaches the patched volume layer (%r): adapt mlog_inproc" % dict(calls))
    rc = _rc_escalate()(0 if rc is None else rc)
    return rc, out.getvalue() + "\n" + err.getvalue()


def _json_of(text, what):
    i = text.find("{")
    _fx(i >= 0, "%s printed no JSON object" % what)
    try:
        return json.JSONDecoder().raw_decode(text[i:])[0]
    except ValueError as e:
        raise RedFixtureError("%s: unparsable JSON (%s)" % (what, e))


def _ctx(rc, text):
    return "\n| rc=%s\n%s" % (rc, text[-5000:])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Matchers (exercised by the non-xfail self-tests at the end of the A7/C6 sections)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def lsn_re(value):
    """An LSN written as generation:offset (hex or decimal), as the full u64, as 0xG_OOOOOOOO, or as "generation G
    offset O". NOT the 1.13.1 form "0xOFF.GEN" (low half first), which the deep check replaces."""
    g, o = value >> 32, value & 0xFFFFFFFF
    alts = [
        r"(?<![0-9A-Za-z_.:])(?:0x)?0*%x\s*:\s*(?:0x)?0*%x(?![0-9A-Fa-f])(?!\s*:\d)" % (g, o),
        r"(?<![0-9A-Za-z_.:])%d\s*:\s*%d(?![0-9])(?!\s*:\d)" % (g, o),
        r"(?<![0-9A-Za-z_])0x0*%x(?![0-9A-Fa-f_.])" % value,
        r"(?<![0-9A-Za-z_])0x0*%x_%08x(?![0-9A-Fa-f])" % (g, o),
        r"(?<![0-9])%d(?![0-9])" % value,
        r"\b(?:generation|gen|segment)\s*:?\s*(?:0x)?0*%x\b[^0-9A-Fa-f\n]{1,16}"
        r"(?:offset|off|block)\s*:?\s*(?:0x)?0*%x(?![0-9A-Fa-f])" % (g, o),
    ]
    return re.compile("|".join("(?:%s)" % a for a in alts), re.I)


_LOGWORD = re.compile(r"(?i)\bMLog\b|\blog\b|\bredo\b")
_MISSING = re.compile(r"(?i)\bmissing\b|\babsent\b|\bnot (?:present|found)\b|\bno longer present\b|\blost\b"
                      r"|\bexpected\b[^.\n]{0,60}\b(?:no|not)\b")
_HOLE = re.compile(r"(?i)\bholes?\b|\bsparse\b")
# C8 = B: the hole is stated with the cause left open (the same wording test as the journal REDs')
_HOLE_CAUSE = re.compile(r"(?i)\bnot captured\b|\bzeros? on (?:the )?disk\b|\bcan ?not be told\b|"
                         r"\b(?:cannot|can ?not|could not) (?:tell|say|show) (?:which|whether)\b")
_DESTROYED = re.compile(r"(?i)\bdestroy\w*|\boverwritten\b|\bwiped\b|\btamper\w*")


def a7_lines(text):
    """Lines that state MLog records are missing (the A7 finding), with the line after each (a continuation)."""
    lines = text.splitlines()
    out = []
    for i, ln in enumerate(lines):
        if _LOGWORD.search(ln) and _MISSING.search(ln):
            out.append(ln + ("\n" + lines[i + 1] if i + 1 < len(lines) else ""))
    return out


def a7_named(text, lsns):
    """The A7 lines that name at least one of the given LSNs."""
    res = [lsn_re(v) for v in lsns]
    return [ln for ln in a7_lines(text) if any(r.search(ln) for r in res)]


def _statement(lines, i, cap=8):
    """N576 (1.14.0): line i and the lines after it up to a blank line (at most `cap`): one statement as the tool wraps
    it. A two-line window tied the matcher to where prose wraps at 100 columns: a longer first sentence put the LSNs
    and the hole sentence of one statement in different windows."""
    out = [lines[i]]
    for ln in lines[i + 1:i + cap]:
        if not ln.strip():
            break
        out.append(ln)
    return "\n".join(out)


def a7_hole_stated(text, lsns):
    """Statements (a line and its continuation up to a blank line) that say MLog records up to one of `lsns` lie in an
    image hole, cause open."""
    res = [lsn_re(v) for v in lsns]
    lines = text.splitlines()
    out = []
    for i, ln in enumerate(lines):
        blob = _statement(lines, i)
        if _LOGWORD.search(blob) and _HOLE.search(blob) and _HOLE_CAUSE.search(blob) and any(r.search(blob) for r in res):
            out.append(blob)
    return out


def destroyed_claims(text):
    return [ln for ln in text.splitlines() if _LOGWORD.search(ln) and _DESTROYED.search(ln)]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A7 -- destroyed newest records read as healthy (K058); the hole rule; an earlier instance must not mask a loss
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# The synthetic log: records k = 1..0x20 at generation 1 (the tail is 1:0x21), control +0x18 = +0x20 = 1:0x21 (a
# start advance to the end with nothing logged after it -- the state of 112 of 117 corpus images, F5 section 4.1).

END = lsn(1, 0x21)


def _intact(tmp_path, cs=0x1000):
    return SynLog(tmp_path / "log.raw", cs).run(1, 0x20, 1, session_start=True).control(END, END)


def _assert_a7_finding(rc, text, lsns):
    named = a7_named(text, lsns)
    assert rc == 2, "records missing from written blocks: `mlog --stats` must exit 2" + _ctx(rc, text)
    assert named, "no finding names the MLog records missing up to the log end %s" % (
        ", ".join("%x:%x" % (v >> 32, v & 0xFFFFFFFF) for v in lsns)) + _ctx(rc, text)
    bad = [ln for ln in a7_lines(text) if _DESTROYED.search(ln)]
    assert not bad, "the finding must say the records are missing, not that they were destroyed " \
                    "(DEEP_CHECK_VERDICT section 6, 'must not be written' item 4): %r" % bad


def test_a7_zeroed_newest_records_exit_2_with_a_named_finding(monkeypatch, tmp_path):
    log = _intact(tmp_path).zero(0x19, 0x20).write()                    # the newest 8 records, written zeros
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    _assert_a7_finding(rc, text, [END, lsn(1, 0x19), lsn(1, 0x18)])


def test_a7_newest_records_in_a_sparse_hole_are_stated_as_a_hole_and_exit_2(monkeypatch, tmp_path):
    log = _intact(tmp_path).hole(0x19, 0x20).write()
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    found = a7_hole_stated(text, [END, lsn(1, 0x19), lsn(1, 0x18)])
    assert found, "records expected up to the log end 1:21 lie in an image hole: the output must say so, with the " \
                  "cause left open (not captured, or zero on the disk)" + _ctx(rc, text)
    assert rc == 2, "records the log needs are missing inside an image hole: exit 2 (C8 = B)" + _ctx(rc, text)
    assert not destroyed_claims(text), destroyed_claims(text)


def test_a7_an_earlier_instance_does_not_mask_zeroed_newest_records(monkeypatch, tmp_path):
    # as on win11refs2gtargeted_reformated: the old instance's records lie after the current tail, at higher LSNs
    log = (_intact(tmp_path).zero(0x19, 0x20)
           .run(0x21, 0x30, 2, magic=MAGIC_B, uid=UUID_B).write())
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    _assert_a7_finding(rc, text, [END, lsn(1, 0x19), lsn(1, 0x18)])


def test_a7_a_record_with_the_same_magic_but_another_uuid_does_not_mask_the_loss(monkeypatch, tmp_path):
    log = (_intact(tmp_path).zero(0x19, 0x20)
           .run(0x21, 0x30, 2, magic=MAGIC_A, uid=UUID_B).write())
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    _assert_a7_finding(rc, text, [END, lsn(1, 0x19), lsn(1, 0x18)])


# controls: a sound check stays silent on these (all pass on 1.13.1 and must keep passing)

def _assert_silent(rc, text):
    _keep(rc == 0, "a healthy log must exit 0" + _ctx(rc, text))
    _keep(not a7_lines(text), "no MLog record is missing here: %r" % a7_lines(text))
    _keep(not destroyed_claims(text), destroyed_claims(text))


def test_a7_control_an_intact_log_raises_no_finding(monkeypatch, tmp_path):
    rc, text = mlog_inproc(monkeypatch, _intact(tmp_path).write(), "--stats")
    _assert_silent(rc, text)


def test_a7_control_records_past_the_log_end_raise_no_finding(monkeypatch, tmp_path):
    """Two committed records after the last control write (the four millionsofactions copies; 642 on
    labFbeforereboot): the tail is beyond +0x20, which F5 found on 5 of 117 images with nothing lost."""
    log = SynLog(tmp_path / "log.raw").run(1, 0x22, 1, session_start=True).control(END, END).write()
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    _assert_silent(rc, text)


def test_a7_control_a_new_mount_session_raises_no_finding(monkeypatch, tmp_path):
    """A remount starts a session at (generation + 1, start offset) with previous LSN 0 (DEEP_CHECK section 1)."""
    end = lsn(2, 0x21)
    log = (SynLog(tmp_path / "log.raw").run(1, 0x10, 1, opens=2, session_start=True)
           .run(0x11, 0x20, 2, opens=3, session_start=True).control(end, end, opens=3).write())
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    _assert_silent(rc, text)


def test_a7_control_an_earlier_instance_alone_is_not_a_finding(monkeypatch, tmp_path):
    """Intact current log plus an earlier instance's records (the reformatted image, golden rc 0): excluding them is
    not damage. (An interpretation of N137's "keep only"; see the report.)"""
    log = _intact(tmp_path).run(0x21, 0x30, 2, magic=MAGIC_B, uid=UUID_B).write()
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    _keep(rc != 2, "records of an earlier log instance are not damage" + _ctx(rc, text))
    _keep(not destroyed_claims(text), destroyed_claims(text))


def test_a7_matchers_accept_a_sound_finding_and_reject_the_1131_lines():
    good = "  MLog: records 1:0x19 .. 1:0x20 are missing: the newest record is 1:0x18, the log end is 1:0x21"
    assert a7_named(good, [END]) and a7_named(good, [lsn(1, 0x18)])
    hole = ("  MLog: records up to the log end 0x100000021 lie in an image hole: not captured, or zero on the disk; "
            "the cause cannot be told from the image")
    assert a7_hole_stated(hole, [END]) and not a7_named(hole, [END])
    # the fourth revision's wording ("unreadable", no cause) no longer meets C8 = B
    assert not a7_hole_stated("  MLog: records up to the log end 0x100000021 lie in an image hole and are unreadable",
                              [END])
    bad = ("  Generation:        33\n  LSN oldest:        0x21.1\n  Records checked:    24\n  Verified:           24\n"
           "  Failed:             0\n  (Log may be clean — all transactions checkpointed.)")
    assert not a7_lines(bad) and not a7_hole_stated(bad, [END])
    assert destroyed_claims("MLog records were destroyed after 1:0x18")
    for form in ("1:0x21", "0x1:0x21", "1:33", "0x100000021", "0x1_00000021", "4294967329",
                 "generation 1, offset 0x21", "segment 1 offset 0x21"):
        assert lsn_re(END).search("log end " + form), form
    for form in ("0x21.1", "33", "01:21:33", "0x1000000210"):
        assert not lsn_re(END).search("x " + form + " y"), form


# ─── A7 on corpus images (scratch copies damaged to order) ───────────────────────────────────────────────────

def _disks_root():
    seen = set()
    for start in (os.getcwd(), REPO):
        d = os.path.abspath(start)
        while d not in seen:
            seen.add(d)
            root = os.path.join(d, "analysis", "rawdisk", "disks")
            if os.path.isdir(root):
                return root
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


def corpus(rel):
    """The corpus image at analysis/rawdisk/disks/<rel> (a path, not a basename: basenames repeat across steps)."""
    root = _disks_root()
    p = os.path.join(root, rel) if root else None
    if not p or not os.path.isfile(p):
        pytest.skip("%s not in this tree (a clone ships no images)" % rel)
    return p


def _refs_ps(path):
    with open(path, "rb") as fh:
        if fh.read(8)[3:7] == b"ReFS":
            return 0
        fh.seek(512)
        h = fh.read(512)
        _fx(h[:8] == b"EFI PART", "%s: no GPT and no VBR at 0" % path)
        lba, n, es = le64(h, 72), le32(h, 80), le32(h, 84)
        fh.seek(lba * 512)
        ents = fh.read(min(n, 128) * es)
        for i in range(min(n, 128)):
            first = le64(ents, i * es + 32)
            if first:
                fh.seek(first * 512)
                if fh.read(8)[3:7] == b"ReFS":
                    return first * 512
    raise RedFixtureError("%s: no ReFS partition" % path)


def _cluster_size(path, ps):
    with open(path, "rb") as fh:
        fh.seek(ps)
        v = fh.read(512)
    return le32(v, 0x20) * le32(v, 0x24)


def read_block(path, off, n=MLOG_BLK):
    with open(path, "rb") as fh:
        fh.seek(off)
        return fh.read(n)


def data_ranges(path, a, b):
    fd = os.open(path, os.O_RDONLY)
    out, pos = [], a
    try:
        while pos < b:
            try:
                d = os.lseek(fd, pos, os.SEEK_DATA)
            except OSError:
                break
            if d >= b:
                break
            h = min(os.lseek(fd, d, os.SEEK_HOLE), b)
            out.append((d, h))
            pos = h
    finally:
        os.close(fd)
    return out


def scan_records(path, a, b):
    """{image offset: parsed type-2 block} over the allocated parts of [a, b) (4 KiB aligned from a)."""
    recs = {}
    with open(path, "rb") as fh:
        for d, h in data_ranges(path, a, b):
            d0 = d - (d - a) % MLOG_BLK
            fh.seek(d0)
            buf = fh.read(h - d0)
            for o in range(0, len(buf) - MLOG_BLK + 1, MLOG_BLK):
                if buf[o:o + 4] == b"MLog":
                    p = parse_block(buf[o:o + MLOG_BLK])
                    if p and p["type"] == 2:
                        recs[d0 + o] = p
    return recs


def _carve_omitting(src, dst, omit=None):
    """Hole-preserving copy (as test_1132_red_a_bootstrap._carve) that also leaves [omit) as an image hole. `omit` is
    one (start, end) range or, since wave C (C-2, the sanctioned plant edit of LB68's A4 copy), a sequence of them."""
    omits = [] if not omit else ([tuple(omit)] if isinstance(omit[0], int) else [tuple(r) for r in omit])
    size = os.path.getsize(src)
    with open(src, "rb") as fi, open(dst, "wb") as out:
        out.truncate(size)
        for d, h in data_ranges(src, 0, size):
            pieces = [(d, h)]
            for oa, ob in omits:
                pieces = [q for (a, b) in pieces for q in ((a, min(b, oa)), (max(a, ob), b))]
            for a, b in pieces:
                if b <= a:
                    continue
                fi.seek(a)
                out.seek(a)
                rem = b - a
                while rem > 0:
                    chunk = fi.read(min(4 << 20, rem))
                    if not chunk:
                        break
                    out.write(chunk)
                    rem -= len(chunk)


@contextlib.contextmanager
def scratch_copy(rel, max_alloc, omit=None):
    """A hole-preserving scratch copy of a corpus image, deleted by its exact path afterwards."""
    src = corpus(rel)
    src_alloc = os.stat(src).st_blocks * 512
    _fx(src_alloc < max_alloc, "%s allocates %d bytes, above this case's cap %d" % (rel, src_alloc, max_alloc))
    os.makedirs(SCRATCH, exist_ok=True)
    _fx(AB._sparse_capable(SCRATCH), "%s cannot hold a sparse file; refusing a dense copy" % SCRATCH)
    _fx(shutil.disk_usage(SCRATCH).free > src_alloc + (512 << 20),
        "not enough free space for a %d-byte scratch copy (the disk backs the maintainer's VM)" % src_alloc)
    d = tempfile.mkdtemp(prefix="mlog_chkp_", dir=SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _carve_omitting(src, p, omit)
        _fx(os.stat(p).st_blocks * 512 <= max_alloc, "the scratch copy allocated %d bytes (not sparse?)"
            % (os.stat(p).st_blocks * 512))
        yield src, p
    finally:
        if os.path.exists(p):
            os.unlink(p)
        os.rmdir(d)


def run_tool(tool, image, *args, cwd=None):
    """(rc, stdout + stderr). A traceback or a timeout is a fixture error, never the defect under test."""
    cmd = [sys.executable, "-B", tool, image] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=cwd or os.path.dirname(image))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout + "\n" + r.stderr


_RUNS = {}


def corpus_run(tool, rel, *args):
    """A read-only run on a corpus image, cached per process (one run per tool, image and arguments)."""
    img = corpus(rel)
    key = (tool, img, args)
    if key not in _RUNS:
        _RUNS[key] = run_tool(tool, img, *args, cwd=REPO)
    return _RUNS[key]


class ImageLog:
    """What this module reads itself about one image's log: the control copy the tool shows (highest sequence
    among the copies whose own fold verifies) and the data-area records."""

    def __init__(self, path, ctrl_offs, ds_off, de_off):
        self.path = path
        ctrls = []
        for o in ctrl_offs:
            c = parse_block(read_block(path, o))
            _fx(c is not None and c["type"] == 1 and c["fold"] == c["stored"],
                "%s: no intact MLog control record at 0x%x" % (path, o))
            ctrls.append(c)
        self.ctrl = max(ctrls, key=lambda c: c["seq"])
        self.ds_off, self.de_off = ds_off, de_off

    def records(self):
        return scan_records(self.path, self.ds_off, self.de_off)


# (rel, control offsets, data-area [start, end) offsets) -- read back and checked at test time
MINI = ("step1/win11refsmini.raw", (0x9000000, 0x9001000), 0x11000000, 0x21000000)
LAB314 = ("step6/lab314_main.raw", (0x19000000, 0x19001000), 0x9000000, 0x19000000)
REFORMATED = ("step6/win11refs2gtargeted_reformated.raw", (0x9000000, 0x9001000), 0x11000000, 0x21000000)


def _check_premise(path, img, lo_k, hi_k, end_expected):
    """Before damage: the control end is `end_expected`; blocks lo_k..hi_k hold the current instance's intact records
    with LSN offsets lo_k..hi_k at the end's generation; the newest current-instance record is hi_k, so the tail
    IS the log end (margin 0, as F5 R11 measured for the K058 base)."""
    rel, ctrl_offs, ds_off, de_off = img
    L = ImageLog(path, ctrl_offs, ds_off, de_off)
    c = L.ctrl
    _fx(c["end"] == end_expected, "%s: control +0x20 is 0x%x, not 0x%x" % (rel, c["end"], end_expected))
    recs = L.records()
    cur = {o: r for o, r in recs.items() if r["magic"] == c["magic"] and r["uuid"] == c["uuid"]}
    g = end_expected >> 32
    for k in range(lo_k, hi_k + 1):
        r = cur.get(ds_off + k * MLOG_BLK)
        _fx(r is not None and r["lsn"] == lsn(g, k) and r["fold"] == r["stored"],
            "%s: block 0x%x is not the current instance's intact record %x:%x" % (rel, k, g, k))
    _fx(not [r for r in cur.values() if r["lsn"] >= end_expected],
        "%s: a current-instance record lies at or beyond the log end: the tail is not the log end" % rel)
    _fx(max(r["lsn"] for r in cur.values()) == lsn(g, hi_k), "%s: block 0x%x is not the newest record" % (rel, hi_k))
    return L, recs, cur


def _zero_range(path, off, n):
    with open(path, "r+b") as fh:
        fh.seek(off)
        fh.write(b"\0" * n)
    _fx(read_block(path, off, n) == b"\0" * n, "the zeroing did not land")
    _fx(_holes(path, off, n) == [], "the zeroed range is not written data (it must not be a hole)")


def _run_a7_zeroed(img, lo_k, hi_k, end, max_alloc, extra_check=None):
    rel, ctrl_offs, ds_off, de_off = img
    with scratch_copy(rel, max_alloc) as (src, p):
        L, recs, cur = _check_premise(p, img, lo_k, hi_k, end)
        if extra_check:
            extra_check(recs, cur, L)
        _zero_range(p, ds_off + lo_k * MLOG_BLK, (hi_k - lo_k + 1) * MLOG_BLK)
        rc, text = run_tool(FOREFST, p, "mlog", "--stats")
    g = end >> 32
    _assert_a7_finding(rc, text, [end, lsn(g, lo_k), lsn(g, lo_k - 1)])


def _run_a7_hole(img, lo_k, hi_k, end, max_alloc):
    rel, ctrl_offs, ds_off, de_off = img
    a, b = ds_off + lo_k * MLOG_BLK, ds_off + (hi_k + 1) * MLOG_BLK
    src = corpus(rel)
    _check_premise(src, img, lo_k, hi_k, end)                          # premise read on the SOURCE (read-only)
    with scratch_copy(rel, max_alloc, omit=(a, b)) as (src, p):
        _fx(_holes(p, a, b - a) == [(a, b)], "the omitted range is not an image hole in the copy")
        _fx(read_block(p, a - MLOG_BLK)[:4] == b"MLog", "the record before the hole did not survive the copy")
        rc, text = run_tool(FOREFST, p, "mlog", "--stats")
    g = end >> 32
    found = a7_hole_stated(text, [end, lsn(g, lo_k), lsn(g, lo_k - 1)])
    assert found, "records up to the log end %x:%x lie in an image hole: the output must say so, with the cause " \
                  "left open" % (g, end & 0xFFFFFFFF) + _ctx(rc, text)
    assert rc == 2, "records the log needs are missing inside an image hole: exit 2 (C8 = B)" + _ctx(rc, text)
    assert not destroyed_claims(text), destroyed_claims(text)


def test_a7_k058_newest_1024_records_zeroed_exit_2_on_image_lab314_main():
    _run_a7_zeroed(LAB314, 0x2904, 0x2D03, lsn(4, 0x2D04), 400 << 20)


def test_a7_k058_range_in_an_image_hole_is_stated_as_a_hole_and_exits_2_on_image_lab314_main():
    _run_a7_hole(LAB314, 0x2904, 0x2D03, lsn(4, 0x2D04), 400 << 20)


def test_a7_newest_64_records_zeroed_exit_2_on_image_win11refsmini():
    _run_a7_zeroed(MINI, 0x52, 0x91, lsn(1, 0x92), 64 << 20)


def test_a7_newest_64_records_in_an_image_hole_are_stated_as_a_hole_and_exit_2_on_image_win11refsmini():
    _run_a7_hole(MINI, 0x52, 0x91, lsn(1, 0x92), 64 << 20)


def test_a7_earlier_instance_does_not_mask_zeroed_records_on_image_win11refs2gtargeted_reformated():
    def _masking(recs, cur, L):
        other = [r for r in recs.values() if (r["magic"], r["uuid"]) != (L.ctrl["magic"], L.ctrl["uuid"])]
        _fx(other and max(r["lsn"] for r in other) > L.ctrl["end"],
            "no earlier-instance record above the log end: the case would not test masking")
    _run_a7_zeroed(REFORMATED, 0x45, 0x54, lsn(2, 0x55), 200 << 20, extra_check=_masking)


# Negative controls on real images, read-only: the golden `mlog --stats` exit code of 1.13.1 (golden.txt) and no
# claim that log records were destroyed or are missing from written blocks. millionsofactions exits 2 today
# for another cause (E2 C01: zero root pages in image holes) and carries 28,404 zeroed log blocks in image holes
# below the log start (F5-verify D7); its tail is beyond the log end, so A7 has nothing to report there.
A7_CONTROLS = [
    ("step7/labFbeforereboot.raw", 0),                   # tail 642 records beyond +0x20; copies differ
    ("step7/labEnotdetached.raw", 0),                    # copy 0 has +0x18 != +0x20
    ("step6/win11refs2gtargeted_reformated.raw", 0),     # an earlier instance's records after the tail
    ("step6/lab314_main.raw", 0),                        # the K058 base, undamaged
    ("step5/win11refstestmftecmd.raw", 0),
    ("step4/wininsiderrefs8gtest2.raw", 0),              # 64K, Insider layout; N144 prints FAILED control copies
    ("step2/win10refs5g64k.raw", 0),                     # 64K, v3.4
    ("step3/win11refs2tmillionsofactions.raw", 2),       # C01; holes below the log start
]


@pytest.mark.parametrize("rel,golden_rc", A7_CONTROLS,
                         ids=["image-" + os.path.basename(r)[:-4] for r, _ in A7_CONTROLS])
def test_a7_control_no_missing_record_claim_on_known_good_images(rel, golden_rc):
    rc, text = corpus_run(FOREFST, rel, "mlog", "--stats")
    _keep(rc == golden_rc, "%s: `mlog --stats` exit %d, golden %d (E2: 0 new rc-2 rows)" % (rel, rc, golden_rc))
    claims = [ln for ln in a7_lines(text) if not (_HOLE.search(ln) and _HOLE_CAUSE.search(ln))]
    _keep(not claims, "%s: MLog records claimed missing from written blocks: %r" % (rel, claims))
    if os.path.basename(rel).startswith("win11refs2tmillionsofactions"):
        # C8 = B: its 28,404 zeroed log blocks in image holes lie BELOW the log start -- space the log no longer
        # needs, so no MLog hole finding at all (its exit 2 is C01's, the zero root pages)
        holes = [ln for ln in text.splitlines() if _LOGWORD.search(ln) and _HOLE.search(ln)]
        _keep(not holes, "%s: log space below the log start reported: %r" % (rel, holes[:3]))
    _keep(not destroyed_claims(text), "%s: %r" % (rel, destroyed_claims(text)))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# C6 -- the control header's labels (DEEP_CHECK_VERDICT section 7)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Synthetic control: +0x18 = 1:0x21 (log start) != +0x20 = 1:0x28 (log end), so a swapped label is visible; seven
# records logged since the start advance (records 1..0x27: the tail is the log end); +0x38 = 3.

C6_START, C6_END, C6_OPENS = lsn(1, 0x21), lsn(1, 0x28), 3


def _c6_log(tmp_path):
    return (SynLog(tmp_path / "log.raw").run(1, 0x27, 1, opens=C6_OPENS, session_start=True)
            .control(C6_START, C6_END, opens=C6_OPENS).write())


def labelled(text, label):
    """The value part of the lines whose label is `label` (case-insensitive, at the start of the line)."""
    r = re.compile(r"(?i)^\s*%s\b\s*(?:\([^)]*\))?\s*[:=]?\s*(.*)$" % re.escape(label))
    return [m.group(1) for m in (r.match(ln) for ln in text.splitlines()) if m]


def _first_int(s):
    m = re.search(r"(?i)0x[0-9a-f]+|\d+", s)
    return int(m.group(0), 0) if m else None


def _assert_c6_labels(text, start, end, opens):
    s, e = labelled(text, "Log start"), labelled(text, "Log end")
    assert s and any(lsn_re(start).search(v) for v in s), "+0x18 must be printed as 'Log start' with its LSN " \
        "%x:%x; got %r" % (start >> 32, start & 0xFFFFFFFF, s) + _ctx("-", text)
    assert e and any(lsn_re(end).search(v) for v in e), "+0x20 must be printed as 'Log end' with its LSN " \
        "%x:%x; got %r" % (end >> 32, end & 0xFFFFFFFF, e)
    assert not [v for v in s + e if re.search(r"(?i)\btail\b", v)], "no 'tail' on the start/end lines: %r" % (s + e)
    gen = labelled(text, "Generation")
    assert not [v for v in gen if _first_int(v) == (end & 0xFFFFFFFF)], \
        "'Generation' printed for +0x20's low half, the log end's block offset (%d): %r" % (end & 0xFFFFFFFF, gen)
    oc = labelled(text, "Log open count")
    assert oc and _first_int(oc[0]) == opens, "+0x38 must be printed as 'Log open count' = %d; got %r" % (opens, oc)
    assert not re.search(r"(?i)\bwrite counter\b", text), "the retired label 'Write counter' is printed"
    assert not re.search(r"(?i)\bLSN oldest\b", text), "the retired label 'LSN oldest' is printed"


@pytest.mark.parametrize("mode", [(), ("--stats",), ("-v",)], ids=["default", "stats", "verbose"])
def test_c6_control_area_labels_log_start_log_end_and_open_count(monkeypatch, tmp_path, mode):
    rc, text = mlog_inproc(monkeypatch, _c6_log(tmp_path), *mode)
    _assert_c6_labels(text, C6_START, C6_END, C6_OPENS)


def test_c6_json_control_carries_log_start_log_end_and_open_count(monkeypatch, tmp_path):
    """Additive by design: the old keys may stay (a patch release does not break JSON readers, cf. O5); the full
    values must be present under their correct names."""
    rc, text = mlog_inproc(monkeypatch, _c6_log(tmp_path), "--json")
    ctrl = _ci(_json_of(text, "mlog --json"), "control") or {}
    _fx(isinstance(ctrl, dict) and _ci(ctrl, "sequence") == 51, "mlog --json has no control object: %r" % ctrl)

    def has(word, value):
        return [k for k, v in ctrl.items() if word in k.lower() and
                (v == value or (isinstance(v, str) and lsn_re(value).search(v)))]
    assert has("start", C6_START), "no control key naming the log start carries 0x%x: %r" % (C6_START, ctrl)
    assert has("end", C6_END), "no control key naming the log end carries 0x%x: %r" % (C6_END, ctrl)
    assert [k for k, v in ctrl.items() if "open" in k.lower() and v == C6_OPENS], \
        "no control key names the log open count (%d): %r" % (C6_OPENS, ctrl)


def test_c6_control_the_synthetic_control_area_is_parsed(monkeypatch, tmp_path):
    """The C6 REDs fail on the LABELS, not because the control area went unparsed: the payload (length 0xE48) is
    read, so its sequence (51, unaffected by C6) is printed and no 'No valid MLog control page' line appears."""
    rc, text = mlog_inproc(monkeypatch, _c6_log(tmp_path))
    _keep(rc == 0 and re.search(r"(?m)^\s*Sequence:\s+51\s*$", text) and "No valid MLog control page" not in text,
          "control area not parsed" + _ctx(rc, text))


def test_c6_label_matcher_rejects_the_1131_control_area():
    t = ("  Write counter:     3\n  Generation:        40\n  LSN oldest:        0x21.1\n")
    with pytest.raises(AssertionError):
        _assert_c6_labels(t, C6_START, C6_END, C6_OPENS)
    good = ("  Log start:         1:0x21\n  Log end:           1:0x28\n  Log open count:    3\n")
    _assert_c6_labels(good, C6_START, C6_END, C6_OPENS)


def test_c6_labels_on_image_labFbeforereboot():
    rel = "step7/labFbeforereboot.raw"
    img = corpus(rel)
    L = ImageLog(img, (0x19000000, 0x19001000), 0x9000000, 0x19000000)
    c = L.ctrl
    _fx((c["seq"], c["start"], c["end"], c["open_count"]) == (143, lsn(8, 0x89C), lsn(8, 0x4B41), 9),
        "labFbeforereboot: the selected control copy is not seq 143 / 8:89c / 8:4b41 / 9: %r" % c)
    rc, text = corpus_run(FOREFST, rel, "mlog", "--stats")
    _assert_c6_labels(text, c["start"], c["end"], c["open_count"])


# ─── C6 docs and truth layer ─────────────────────────────────────────────────────────────────────────────────

def repo_text(rel):
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p):
        pytest.skip("%s is not in this layout" % rel)
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def md_section(text, heading_re):
    """The lines of the first section whose heading matches, up to the next heading of the same or higher level."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^(#+)\s", ln)
        if m and re.search(heading_re, ln):
            lvl = len(m.group(1))
            out = []
            for l2 in lines[i + 1:]:
                m2 = re.match(r"^(#+)\s", l2)
                if m2 and len(m2.group(1)) <= lvl:
                    break
                out.append(l2)
            return out
    raise RedFixtureError("no section matching %r (the page was restructured: adapt the locator)" % heading_re)


def md_row(lines, offset_re):
    rows = [ln for ln in lines if re.match(r"^\|\s*%s\s*(?:\([^)|]*\))?\s*\|" % offset_re, ln)]
    _fx(len(rows) == 1, "expected one table row for %r, found %d (restructured page?)" % (offset_re, len(rows)))
    return [c.strip() for c in rows[0].strip().strip("|").split("|")]


# RED 1.13.2 C6: mlog.md:221-223 label +0x18 'LSN oldest', +0x20 'LSN (duplicate of +0x18)', +0x38 'Write counter' (8 B) -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_c6_mlog_md_control_payload_rows_carry_the_new_labels():
    sec = md_section(repo_text("docs/structures/mlog.md"), r"(?i)control page")
    r18, r20, r38 = md_row(sec, r"(?:payload\s*)?\+0x18"), md_row(sec, r"(?:payload\s*)?\+0x20"), \
        md_row(sec, r"(?:payload\s*)?\+0x38")
    assert re.search(r"(?i)\blog start\b", r18[2]), "+0x18 row: %r" % r18
    assert re.search(r"(?i)\blog end\b", r20[2]), "+0x20 row: %r" % r20
    assert not re.search(r"(?i)\btail\b|LSN oldest|duplicate", " ".join(r18 + r20)), (r18, r20)
    assert re.search(r"(?i)\bopen count\b", r38[2]) and r38[1] == "4", "+0x38 row: %r" % r38
    assert not re.search(r"(?i)write counter", "\n".join(sec)), "'Write counter' still on the page"


# RED 1.13.2 C6: mlog.md:32 'Counter | Small per-record counter'; :202 'Sequence number (u64) | Alternation counter' -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_c6_mlog_md_record_and_control_page_header_0x20_is_the_open_count():
    text = repo_text("docs/structures/mlog.md")
    rec = md_row(md_section(text, r"(?i)Layer 1"), r"0x20")
    ctl = md_row(md_section(text, r"(?i)control page"), r"0x20")
    assert re.search(r"(?i)\bopen count\b", " ".join(rec[2:])), "record header +0x20: %r" % rec
    assert re.search(r"(?i)\bopen count\b", " ".join(ctl[2:])), "control-page header +0x20: %r" % ctl
    assert not re.search(r"(?i)increments each write|per-record counter", " ".join(rec + ctl)), (rec, ctl)


def errata_titles():
    text = repo_text("analysis/errata.md")
    return [(int(m.group(1)), m.group(0)) for m in re.finditer(r"(?m)^##\s+E(\d+)\b.*$", text)]


# RED 1.13.2 C6: green with E116's filing (1.14.0, after Q39's reading of the LAB-F images; the strict xfail mark removed)
def test_c6_the_relabel_is_recorded_by_errata():
    t = [s for n, s in errata_titles() if n >= 116]
    assert [s for s in t if "0x18" in s and re.search(r"(?i)log start", s)], "no erratum on +0x18 = log start"
    assert [s for s in t if "0x38" in s and re.search(r"(?i)open count", s)], "no erratum on +0x38 = open count"


# RED 1.13.2 C6: docs/tools/forefst.md:84 (published Known issues) says +0x18 'is the log's tail' -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_c6_known_issues_no_longer_call_0x18_the_tail():
    # RC3 (1.14.0): the Known issues moved to docs/tools/known_issues.md; both pages are read
    lines = [ln for p in ("docs/tools/forefst.md", "docs/tools/known_issues.md") for ln in repo_text(p).splitlines()
             if "0x18" in ln and re.search(r"(?i)\btail\b", ln)]
    assert not lines, lines


_REFUTED = re.compile(r"(?i)\brestart LSN\b|\bLSN (?:that )?restart (?:reads|starts)|\bmount count\b")


def test_c6_control_no_refuted_wording_in_the_tool_or_mlog_md(monkeypatch, tmp_path):
    """DEEP_CHECK_VERDICT section 6 'must not be written': +0x18 is not the restart LSN (replay starts at the chosen
    checkpoint's +0x70), and +0x38 is a log OPEN count, not an unqualified mount count. Absent on 1.13.1; the
    relabel must not bring them in (RUNNING_LOG N136/N143 and RC1_DEPS section 3 carry them as provenance)."""
    log = _c6_log(tmp_path)
    for mode in ((), ("--stats",), ("-v",), ("--json",)):
        rc, text = mlog_inproc(monkeypatch, log, *mode)
        _keep(not _REFUTED.search(text), "mlog %s: %r" % (" ".join(mode), _REFUTED.findall(text)))
    _keep(not _REFUTED.search(repo_text("docs/structures/mlog.md")), "mlog.md carries refuted wording")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N137 -- records of an earlier log instance presented as current
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Synthetic: the current instance (MAGIC_A, UUID_A) holds blocks 1..0x20; an earlier instance holds blocks
# 0x21..0x30 at higher LSNs (generation 2), as on win11refs2gtargeted_reformated (current 0x1-0x54, old 0x55-0xcb).

N137_CUR, N137_OLD = range(1, 0x21), range(0x21, 0x31)


def _n137_log(tmp_path, magic=MAGIC_B, uid=UUID_B):
    return (SynLog(tmp_path / "log.raw").run(1, 0x20, 1, session_start=True)
            .run(0x21, 0x30, 2, magic=magic, uid=uid).control(END, END).write())


def _csv_rows(text):
    """The rows of `mlog --csv` in the 1.13.1 layout these nodes index (seq, timestamp, action, path, name, oid,
    opcodes, record_count, plcn -- the PLCN as a decimal string). LB11 (wave B, reader only): the header is found by its
    PLCN column in any case and the cells are read by name, so the decided forms (PascalCase, LB3; FullPath/ParentPath,
    LB27; hex PLCN, K9; OpcodesHex/Block, N260/N311) are read the same way; what the nodes assert is unchanged."""
    lines = text.splitlines()
    i = next((j for j, ln in enumerate(lines)
              if any(c.strip().lower() == "plcn" for c in next(csv.reader([ln]), []))), None)
    _fx(i is not None, "mlog --csv printed no header")
    hdr = [h.strip().lower() for h in next(csv.reader([lines[i]]))]
    col = {h: k for k, h in enumerate(hdr)}

    def cell(fields, *names):
        for n in names:
            if n in col and col[n] < len(fields):
                return fields[col[n]]
        return ""
    rows = []
    for fields in csv.reader(lines[i + 1:]):
        if not fields or not fields[0].isdigit():
            continue
        name = cell(fields, "name")
        path = cell(fields, "path") or (cell(fields, "parentpath") if name else cell(fields, "fullpath"))
        rows.append([fields[0], cell(fields, "timestamp"), cell(fields, "action"), path, name, cell(fields, "oid"),
                     cell(fields, "opcodes"), cell(fields, "record_count", "recordcount"),
                     str(int(cell(fields, "plcn"), 0))])
    return rows


def _ci(d, name, default=None):
    """LB11 (reader only): a JSON key looked up in any case (the decided keys are PascalCase, LB3)."""
    for k, v in (d or {}).items():
        if k.lower() == name.lower():
            return v
    return default


def _jint(v):
    """LB11 (reader only): a JSON PLCN as an integer, whether written as an integer or as a hex string (K9)."""
    return int(v, 0) if isinstance(v, str) else v


def _parse_v_plcns(text):
    """PLCNs of the -v per-record lines of `mlog --parse -v`, up to any section about another instance. LB11 (reader
    only): the PLCN is read in hex (K9, N311) or decimal."""
    out = []
    for ln in text.splitlines():
        if re.search(r"(?i)earlier (?:log )?instance|previous (?:log )?instance|other (?:log )?instance|excluded", ln):
            break
        m = re.search(r"@PLCN (0x[0-9a-fA-F]+|\d+)\.blk(\d+)\+0x", ln)
        if m:
            out.append(int(m.group(1), 0))
    return out


@pytest.mark.parametrize("which", ["magic+uuid", "uuid-only"])
def test_n137_mlog_v_counts_only_the_current_instances_records(monkeypatch, tmp_path, which):
    log = _n137_log(tmp_path, *((MAGIC_B, UUID_B) if which == "magic+uuid" else (MAGIC_A, UUID_B)))
    rc, text = mlog_inproc(monkeypatch, log, "-v")
    m = re.search(r"LogCore Record Headers \((\d+) data records", text)
    _fx(m, "mlog -v printed no LogCore header section" + _ctx(rc, text))
    assert int(m.group(1)) == len(N137_CUR), "headers counted: %s, current instance: %d" % (m.group(1), len(N137_CUR))


def test_n137_mlog_csv_has_no_transaction_of_an_earlier_instance(monkeypatch, tmp_path):
    log = _n137_log(tmp_path)
    rc, text = mlog_inproc(monkeypatch, log, "--csv")
    plcns = [int(r[8]) for r in _csv_rows(text)]
    cur, old = {log.cluster_of(k) for k in N137_CUR}, {log.cluster_of(k) for k in N137_OLD}
    _keep(cur <= set(plcns), "current-instance transactions went missing: %r" % sorted(cur - set(plcns)))
    leaked = sorted(set(plcns) & old)
    assert not leaked, "%d transaction rows from earlier-instance blocks: %s" % (
        sum(1 for p in plcns if p in old), [hex(p) for p in leaked[:8]])


def test_n137_mlog_json_records_are_the_current_instances(monkeypatch, tmp_path):
    log = _n137_log(tmp_path)
    rc, text = mlog_inproc(monkeypatch, log, "--json")
    recs = _ci(_json_of(text, "mlog --json"), "records") or []
    plcns = {_jint(_ci(r, "plcn")) for r in recs}
    cur, old = {log.cluster_of(k) for k in N137_CUR}, {log.cluster_of(k) for k in N137_OLD}
    _keep(cur <= plcns, "current-instance records went missing from --json")
    assert not plcns & old, "--json records from earlier-instance blocks: %s" % sorted(hex(p) for p in plcns & old)


def test_n137_mlog_parse_v_names_no_earlier_instance_block(monkeypatch, tmp_path):
    log = _n137_log(tmp_path)
    rc, text = mlog_inproc(monkeypatch, log, "--parse", "-v")
    plcns = _parse_v_plcns(text)
    old = {log.cluster_of(k) for k in N137_OLD}
    _keep({log.cluster_of(k) for k in N137_CUR} <= set(plcns), "current-instance records went missing")
    assert not set(plcns) & old, "--parse -v records at earlier-instance PLCNs: %s" % sorted(
        hex(p) for p in set(plcns) & old)


# ─── N137 on the reformatted image (read-only) ───────────────────────────────────────────────────────────────

class _Reformated:
    """This module's own map of win11refs2gtargeted_reformated's log: which data-area blocks belong to which
    instance (F5 section 4.2: 84 current, 119 of the pre-reformat instance, magic 0x6d790647 / UUID c2fb82a9)."""
    rel = REFORMATED[0]

    def __init__(self):
        img = corpus(self.rel)
        rel, ctrl_offs, ds_off, de_off = REFORMATED
        L = ImageLog(img, ctrl_offs, ds_off, de_off)
        recs = L.records()
        c = L.ctrl
        self.cur = {(o - ds_off) // MLOG_BLK for o, r in recs.items() if (r["magic"], r["uuid"]) == (c["magic"], c["uuid"])}
        self.old = {(o - ds_off) // MLOG_BLK for o, r in recs.items() if (r["magic"], r["uuid"]) != (c["magic"], c["uuid"])}
        _fx((len(self.cur), len(self.old)) == (84, 119) and c["magic"] == MAGIC_A,
            "the reformatted image's log is not 84 current + 119 earlier records: %d + %d" % (len(self.cur), len(self.old)))
        self.ds_lcn = (ds_off - _refs_ps(img)) // _cluster_size(img, _refs_ps(img))
        self.old_plcn = {self.ds_lcn + k for k in self.old}
        self.cur_plcn = {self.ds_lcn + k for k in self.cur}


def test_n137_mlog_v_counts_only_the_current_instance_on_image_win11refs2gtargeted_reformated():
    R = _Reformated()
    rc, text = corpus_run(FOREFST, R.rel, "mlog", "-v")
    m = re.search(r"LogCore Record Headers \((\d+) data records", text)
    _fx(m, "mlog -v printed no LogCore header section" + _ctx(rc, text))
    assert int(m.group(1)) == len(R.cur), "headers counted %s, current instance %d" % (m.group(1), len(R.cur))


def test_n137_mlog_csv_and_json_carry_no_earlier_instance_on_image_win11refs2gtargeted_reformated():
    R = _Reformated()
    rc, text = corpus_run(FOREFST, R.rel, "mlog", "--csv")
    csv_plcns = [int(r[8]) for r in _csv_rows(text)]
    rc2, text2 = corpus_run(FOREFST, R.rel, "mlog", "--json")
    json_plcns = [_jint(_ci(r, "plcn")) for r in _ci(_json_of(text2, "mlog --json"), "records") or []]
    _keep(set(csv_plcns) & R.cur_plcn, "no current-instance transaction in --csv")
    assert not set(csv_plcns) & R.old_plcn, "--csv: %d rows from pre-reformat blocks" % sum(
        1 for p in csv_plcns if p in R.old_plcn)
    assert not set(json_plcns) & R.old_plcn, "--json: %d records from pre-reformat blocks" % sum(
        1 for p in json_plcns if p in R.old_plcn)


def test_n137_mlog_parse_v_names_no_earlier_instance_block_on_image_win11refs2gtargeted_reformated():
    R = _Reformated()
    rc, text = corpus_run(FOREFST, R.rel, "mlog", "--parse", "-v")
    # LB11: a premise, so the node cannot pass vacuously -- the current instance's records are listed and read
    _keep(R.cur_plcn <= set(_parse_v_plcns(text)), "--parse -v lists none (or not all) of the current instance's "
          "records: %d of %d PLCNs read" % (len(R.cur_plcn & set(_parse_v_plcns(text))), len(R.cur_plcn)))
    leaked = set(_parse_v_plcns(text)) & R.old_plcn
    assert not leaked, "--parse -v records at %d pre-reformat PLCNs" % len(leaked)


def _timeline_mlog_rows(text):
    lines = text.splitlines()
    # acceptance 1.14.0 (K21, P9, Q-C): the header is Timestamp,TimeSource,Source,OID,Name,PathToday,Event
    i = next((j for j, ln in enumerate(lines) if ln.startswith("Timestamp,TimeSource,Source,")), None)
    _fx(i is not None, "timeline --csv printed no header")
    hdr = next(csv.reader(lines[i:i + 1]))
    si = hdr.index("Source")
    return [f for f in csv.reader(lines[i + 1:]) if len(f) == len(hdr) and f[si] == "MLog"]


def test_n137_timeline_has_only_current_instance_events_on_image_win11refs2gtargeted_reformated():
    """timeline builds its MLog events from the same transactions as `mlog --csv` (fd:8401-8410 / :7664-7672): one
    event per transaction with a timestamp. The control below shows the two agree on a single-instance volume."""
    R = _Reformated()
    rc, text = corpus_run(FOREFST, R.rel, "mlog", "--csv")
    rows = _csv_rows(text)
    old_ts = [r for r in rows if r[1] and int(r[8]) in R.old_plcn]
    cur_ts = [r for r in rows if r[1] and int(r[8]) not in R.old_plcn]
    if [r for r in rows if int(r[8]) in R.old_plcn]:                    # 1.13.1: the old rows are there
        _fx(old_ts, "no pre-reformat transaction carries a timestamp: the timeline cannot show the defect")
    rc2, text2 = corpus_run(FOREFST, R.rel, "timeline", "--csv", "--source", "MLOG")
    tl = _timeline_mlog_rows(text2)
    assert len(tl) == len(cur_ts), "timeline MLog events %d; timestamped current-instance transactions %d " \
                                   "(%d more are pre-reformat)" % (len(tl), len(cur_ts), len(old_ts))


def test_n137_control_timeline_and_mlog_csv_agree_on_image_lab314_main():
    """On a single-instance volume every timestamped `mlog --csv` transaction is one `timeline` MLog event: the
    relation the timeline RED above rests on."""
    rel = LAB314[0]
    rc, text = corpus_run(FOREFST, rel, "mlog", "--csv")
    ts_rows = [r for r in _csv_rows(text) if r[1]]
    rc2, text2 = corpus_run(FOREFST, rel, "timeline", "--csv", "--source", "MLOG")
    _keep(ts_rows, "lab314_main has no timestamped MLog transaction: the control shows nothing")
    _keep(len(_timeline_mlog_rows(text2)) == len(ts_rows),
          "timeline %d vs mlog --csv %d timestamped" % (len(_timeline_mlog_rows(text2)), len(ts_rows)))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N144 -- intact control copies printed FAILED on 64 KiB-cluster volumes
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_CTRL_LINE = re.compile(r"Control copy (\d) \(PLCN 0x([0-9a-f]+)\):\s*(\S+)(.*)")


def control_verdicts(text):
    return {int(m.group(1)): (int(m.group(2), 16), m.group(3), m.group(4)) for m in _CTRL_LINE.finditer(text)}


def test_n144_intact_control_copies_verify_on_a_64k_volume(monkeypatch, tmp_path):
    log = _intact(tmp_path, cs=0x10000).write()
    for plcn in (1, 2):
        c = parse_block(read_block(log.path, plcn * log.cs))
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"], "control copy at cluster %d is not intact" % plcn)
        _fx(read_block(log.path, plcn * log.cs + MLOG_BLK, log.cs - MLOG_BLK) == b"\0" * (log.cs - MLOG_BLK),
            "the rest of the control cluster is not zero (as on every 64K image read)")
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    v = control_verdicts(text)
    _fx(set(v) == {0, 1}, "no 'Control copy' lines" + _ctx(rc, text))
    assert all(s == "verified" for _p, s, _r in v.values()), "intact control copies: %r" % v


def test_n144_control_intact_copies_verify_on_a_4k_volume(monkeypatch, tmp_path):
    rc, text = mlog_inproc(monkeypatch, _intact(tmp_path).write(), "--stats")
    v = control_verdicts(text)
    _keep(set(v) == {0, 1} and all(s == "verified" for _p, s, _r in v.values()), "4K control copies: %r" % v)


def test_n144_control_a_damaged_control_copy_still_fails_on_a_64k_volume(monkeypatch, tmp_path):
    """A fix must not print 'verified' blindly: one flipped byte inside copy 0's own 4 KiB is still FAILED."""
    log = _intact(tmp_path, cs=0x10000).write()
    with open(log.path, "r+b") as fh:
        fh.seek(log.cs + 0x200)
        b = fh.read(1)
        fh.seek(log.cs + 0x200)
        fh.write(bytes([b[0] ^ 0x01]))
    c = parse_block(read_block(log.path, log.cs))
    _fx(c["fold"] != c["stored"], "the flip did not change the fold")
    rc, text = mlog_inproc(monkeypatch, log, "--stats")
    v = control_verdicts(text)
    _keep(0 in v and v[0][1] != "verified", "a damaged control copy printed %r" % (v.get(0),))


def test_n144_control_intact_64k_control_copies_raise_no_finding(monkeypatch, tmp_path):
    """If A7 routes the control check into a finding, the N144 fold must not turn it into a false exit 2."""
    rc, text = mlog_inproc(monkeypatch, _intact(tmp_path, cs=0x10000).write(), "--stats")
    _keep(rc != 2, "intact 64K log: exit 2" + _ctx(rc, text))


N144_IMAGES = ["step4/wininsiderrefs8gtest2.raw", "step2/win10refs5g64k.raw", "step2/win11refs5g64k.raw",
               "step3/win11refs2t64ksha256checksums.raw", "step6/lab314_64k.raw"]


def _check_control_premise(img, v):
    ps = _refs_ps(img)
    cs = _cluster_size(img, ps)
    for i, (plcn, _s, _r) in v.items():
        blk = read_block(img, ps + plcn * cs, cs)
        c = parse_block(blk)
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"],
            "%s: the control copy at PLCN 0x%x is not an intact control record (own fold)" % (img, plcn))
    return cs


@pytest.mark.parametrize("rel", N144_IMAGES, ids=["image-" + os.path.basename(r)[:-4] for r in N144_IMAGES])
def test_n144_intact_control_copies_verify_on_64k_images(rel):
    rc, text = corpus_run(FOREFST, rel, "mlog", "--stats")
    v = control_verdicts(text)
    _fx(set(v) == {0, 1}, "%s: no 'Control copy' lines" % rel + _ctx(rc, text))
    cs = _check_control_premise(corpus(rel), v)
    _fx(cs == 0x10000, "%s is not a 64K volume" % rel)
    assert all(s == "verified" for _p, s, _r in v.values()), "%s: %r" % (rel, v)


@pytest.mark.parametrize("rel", ["step5/win11refstestmftecmd.raw", "step6/lab314_main.raw"],
                         ids=["image-win11refstestmftecmd", "image-lab314_main"])
def test_n144_control_4k_images_verify(rel):
    rc, text = corpus_run(FOREFST, rel, "mlog", "--stats")
    v = control_verdicts(text)
    _keep(set(v) == {0, 1} and all(s == "verified" for _p, s, _r in v.values()), "%s: %r" % (rel, v))
    _check_control_premise(corpus(rel), v)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# F11 / E118 / N190 -- the checkpoint RECORD is one cluster
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def chkp_lcns(path, ps, cs):
    """The superblock's checkpoint list, read here (SUPB at LCN 0x1E; +0x70 = list offset, +0x74 = count)."""
    s = read_block(path, ps + 0x1E * cs, cs)
    _fx(s[:4] == b"SUPB", "%s: no SUPB at LCN 0x1E" % path)
    off, n = le32(s, 0x70), le32(s, 0x74)
    _fx(n == 2, "%s: %d checkpoint references" % (path, n))
    lst = [le64(s, off + 8 * i) for i in range(n)]
    for lcn in lst:
        _fx(read_block(path, ps + lcn * cs, 4)[:4] == b"CHKP", "%s: no CHKP at 0x%x" % (path, lcn))
    return lst


class Chkp:
    """Per checkpoint copy: the one-cluster hash (E118) and the page hash (E102's reading), read here."""

    def __init__(self, path, ps=None, cs=None):
        self.path = path
        self.ps = _refs_ps(path) if ps is None else ps
        self.cs = _cluster_size(path, self.ps) if cs is None else cs
        self.lcns = chkp_lcns(path, self.ps, self.cs)
        self.one = {l: hashlib.sha256(read_block(path, self.ps + l * self.cs, self.cs)).hexdigest() for l in self.lcns}
        self.page = {l: hashlib.sha256(read_block(path, self.ps + l * self.cs, max(16384, self.cs))).hexdigest()
                     for l in self.lcns}

    def cluster(self, lcn):
        return read_block(self.path, self.ps + lcn * self.cs, self.cs)


def summary_chkp_rows(text):
    """{lcn: printed hash} of the `CHKP primary/secondary LCN 0x..` lines of `summary` (the hash on the next line)."""
    lines = text.splitlines()
    out = {}
    for i, ln in enumerate(lines):
        m = re.search(r"CHKP (?:primary|secondary)\s+LCN (0x[0-9a-f]+)", ln)
        if m:
            h = next((re.search(r"\b[0-9a-f]{64}\b", l2) for l2 in lines[i + 1:i + 3]
                      if re.search(r"\b[0-9a-f]{64}\b", l2)), None)
            out[int(m.group(1), 16)] = h.group(0) if h else None
    return out


def _assert_summary_rows(ck, text, where):
    rows = summary_chkp_rows(text)
    _fx(set(rows) == set(ck.lcns) and all(rows.values()), "%s: summary printed CHKP rows %r" % (where, rows))
    for lcn, h in rows.items():
        _fx(h in (ck.one[lcn], ck.page[lcn]), "%s: the CHKP 0x%x row hashes neither span of that copy" % (where, lcn))
    wrong = {hex(l): h[:16] for l, h in rows.items() if h != ck.one[l]}
    assert not wrong, "%s: CHKP rows not over one cluster (%d B): %r" % (where, ck.cs, wrong)


def _json_chkp_hashes(j, lcns):
    """Every (lcn, sha256) pair in the JSON whose lcn is a checkpoint's, plus the top-level chkp_sha256."""
    pairs = []

    def walk(o):
        if isinstance(o, dict):
            # acceptance 1.14.0 (K21, K9): LCN a hex string, SHA256
            lcn = o.get("LCN")
            lcn = int(lcn, 16) if isinstance(lcn, str) else lcn
            if lcn is not None and "SHA256" in o and lcn in lcns:
                pairs.append((lcn, o["SHA256"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(j)
    return pairs


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_summary_chkp_rows_hash_one_cluster(tmp_path):
    v = AB._synthetic_vol(tmp_path)
    ck = Chkp(v.path, ps=0, cs=AB.CS)
    rc, out = v.run(FOREFST, "summary")
    _assert_summary_rows(ck, out, "synthetic summary")


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_fastsummary_json_chkp_hashes_are_one_cluster(tmp_path):
    v = AB._synthetic_vol(tmp_path)
    ck = Chkp(v.path, ps=0, cs=AB.CS)
    rc, out = v.run(FOREFST, "fastsummary", "--json")
    j = _json_of(out, "fastsummary --json")
    top = j.get(AB.F.out_key("chkp_sha256", AB.F._SUMMARY_KEYS))       # acceptance 1.14.0 (K21)
    pairs = _json_chkp_hashes(j, set(ck.lcns))
    _fx(top and pairs, "fastsummary --json carries no checkpoint hash")
    _fx(top in set(ck.one.values()) | set(ck.page.values()), "chkp_sha256 hashes no span of either copy")
    assert top in ck.one.values(), "chkp_sha256 %s.. is not a one-cluster hash" % top[:16]
    wrong = [(hex(l), h[:16]) for l, h in pairs if h != ck.one[l]]
    assert not wrong, "checkpoints[].sha256 not over one cluster: %r" % wrong


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_refsanalysis_chkp_hash_is_one_cluster(tmp_path):
    v = AB._synthetic_vol(tmp_path)
    ck = Chkp(v.path, ps=0, cs=AB.CS)
    rc, out = v.run(REFSANALYSIS, "chkp")
    hs = re.findall(r"SHA-256:?\s+([0-9a-f]{64})", out)
    _fx(hs, "refsanalysis chkp printed no SHA-256" + _ctx(rc, out))
    _fx(set(hs) <= set(ck.one.values()) | set(ck.page.values()), "refsanalysis chkp hashes no span of a copy")
    assert set(hs) <= set(ck.one.values()), "refsanalysis chkp hash(es) not over one cluster: %r" % [
        h[:16] for h in hs]


def _export_chkp(image, outdir, cli=(), cwd=None):
    rc, out = run_tool(FOREFST, image, "export", "metadata", outdir, "--what", "chkp", *cli, cwd=cwd)
    files = {int(m.group(1), 16): os.path.join(outdir, n) for n in os.listdir(outdir)
             for m in [re.match(r"checkpoint_\d+_lcn([0-9a-f]+)\.bin$", n)] if m}
    _fx(files, "export metadata wrote no checkpoint file" + _ctx(rc, out))
    man = {}
    mp = os.path.join(outdir, "manifest.json")
    if os.path.isfile(mp):
        # acceptance 1.14.0 (E-2, K21): read as the bundle reader reads it (internal names)
        man = {a.get("file"): a for a in AB.F.read_bundle_manifest(outdir).get("artifacts", [])}
    return rc, out, files, man


def _assert_export_one_cluster(ck, files, man, where):
    _fx(set(files) == set(ck.lcns), "%s: exported checkpoints %r, expected %r" % (where, sorted(files), ck.lcns))
    sizes = {hex(l): os.path.getsize(p) for l, p in files.items()}
    assert all(s == ck.cs for s in sizes.values()), "%s: checkpoint files %r, one cluster is %d B" % (
        where, sizes, ck.cs)
    for l, p in files.items():
        with open(p, "rb") as fh:
            assert fh.read() == ck.cluster(l), "%s: checkpoint_*_lcn%x.bin is not that cluster's bytes" % (where, l)
        a = man.get(os.path.basename(p))
        if a is not None:
            assert a.get("bytes") == ck.cs, "%s: the manifest records %r bytes" % (where, a.get("bytes"))


# RED 1.13.2 N190: green with wave B part 2's fix (the strict xfail mark removed)
def test_n190_export_metadata_writes_one_cluster_per_checkpoint(tmp_path):
    v = AB._synthetic_vol(tmp_path)
    ck = Chkp(v.path, ps=0, cs=AB.CS)
    d = str(tmp_path / "bundle")
    rc, out, files, man = _export_chkp(v.path, d, cli=v.geo.cli, cwd=str(tmp_path))
    _assert_export_one_cluster(ck, files, man, "synthetic")


# ─── F11 / N190 on corpus images (read-only; the export writes a small bundle into scratch) ─────────────────

# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_chkp_hash_rows_are_one_cluster_on_image_win11refsmini():
    rel = MINI[0]
    ck = Chkp(corpus(rel))
    _fx(ck.cs == 0x1000 and ck.lcns == [0x13F8, 0xEE34], "win11refsmini: unexpected geometry %r" % ck.lcns)
    rc, out = corpus_run(FOREFST, rel, "summary")
    _assert_summary_rows(ck, out, rel)
    rc, out = corpus_run(FOREFST, rel, "fastsummary", "--json")
    j = _json_of(out, "fastsummary --json")
    top = j.get(AB.F.out_key("chkp_sha256", AB.F._SUMMARY_KEYS))       # acceptance 1.14.0 (K21)
    _fx(top in set(ck.one.values()) | set(ck.page.values()), "chkp_sha256 hashes no span of a copy")
    assert top in ck.one.values(), "chkp_sha256 %s.. is not one cluster" % top[:16]
    rc, out = corpus_run(REFSANALYSIS, rel, "chkp")
    hs = re.findall(r"SHA-256:?\s+([0-9a-f]{64})", out)
    assert hs and set(hs) <= set(ck.one.values()), "refsanalysis chkp: %r" % [h[:16] for h in hs]


def test_f11_control_64k_hash_rows_are_already_one_cluster_on_image_win11refs5g64k():
    """On 64K the page is one cluster, so 1.13.1 already hashes one cluster (E118: '64K rows do not change'). The 4K
    REDs therefore fail on the span, not on which bytes are read."""
    rel = "step2/win11refs5g64k.raw"
    ck = Chkp(corpus(rel))
    rc, out = corpus_run(FOREFST, rel, "summary")
    rows = summary_chkp_rows(out)
    _keep(set(rows) == set(ck.lcns) and all(rows[l] == ck.one[l] for l in rows), "64K CHKP rows: %r" % rows)


N190_IMAGES = ["step6/lab314_64k.raw", "step4/wininsiderrefs8gtest2.raw", "step1/win11refsmini.raw"]


# RED 1.13.2 N190: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("rel", N190_IMAGES, ids=["image-" + os.path.basename(r)[:-4] for r in N190_IMAGES])
def test_n190_export_metadata_writes_one_cluster_per_checkpoint_on_images(rel):
    img = corpus(rel)
    ck = Chkp(img)
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="mlog_chkp_export_", dir=SCRATCH)
    try:
        rc, out, files, man = _export_chkp(img, os.path.join(d, "bundle"), cwd=REPO)
        _assert_export_one_cluster(ck, files, man, rel)
        rc2, out2 = corpus_run(FOREFST, rel, "summary")
        rows = summary_chkp_rows(out2)
        for l, p in files.items():                     # audit_oracle F5 cmp_boot.py:30: export hash == summary hash
            with open(p, "rb") as fh:
                assert hashlib.sha256(fh.read()).hexdigest() == rows.get(l), \
                    "%s: exported checkpoint 0x%x does not hash to its summary row" % (rel, l)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ─── E118 docs and truth layer ───────────────────────────────────────────────────────────────────────────────

# RED 1.13.2 E118: chkp.md:3 sizes the checkpoint as one metadata page and never says the record is one cluster -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_e118_chkp_md_states_record_one_cluster_and_allocation_one_page():
    text = repo_text("docs/structures/chkp.md")
    assert re.search(r"(?i)\brecord\b[^.\n]{0,100}\b(?:one|1|a single) cluster\b", text), \
        "chkp.md does not state that the checkpoint record is one cluster"
    assert re.search(r"(?i)\ballocation\b[^.\n]{0,100}\b(?:page|4 clusters|four clusters)\b", text), \
        "chkp.md does not state that the allocation is one metadata page"


def test_e118_an_erratum_records_the_checkpoint_record_size():
    # GREEN since wave C's close (2026-10-24): E118 filed in errata.md (the RED mark removed; the node XPASSed)
    t = [s for n, s in errata_titles() if n >= 116]
    assert [s for s in t if re.search(r"(?i)checkpoint", s) and re.search(r"(?i)one cluster", s)], \
        "no erratum on the checkpoint record = one cluster"


# RED 1.13.2 E118: docs/tools/forefst.md:48 tells the examiner to hash max(16 KiB, cluster size) bytes of a checkpoint -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_e118_published_advice_no_longer_hashes_a_16k_checkpoint():
    lines = [ln for ln in repo_text("docs/tools/forefst.md").splitlines()
             if re.search(r"(?i)max\(\s*16 KiB", ln)]
    assert not lines, lines
