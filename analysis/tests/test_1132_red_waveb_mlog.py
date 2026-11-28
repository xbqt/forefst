"""1.13.2 (ships as 1.14.0) RED cases, wave B group 4 (MLog): what the confirmed MLog REDs do not pin yet.

Read first: `analysis/reports/v1.13.2/fixes/WAVEB_PREP.md` (items, the lead's settlements LB1-LB38 and LB4a),
`fixes/WAVEB_CENSUS.md` (stage 1, section 2.13 = the forms table), `fixes/CONSISTENCY_CHOICES.md` (the K kinds),
`fixes/DECISION_SCAN_WAVES_B_E.md` "Wave B" (the N144 settlement for a copy that really fails), PLAN_1.13.2 decisions
33-38, and the running-log rows named per section. Report, with the failure line of every node observed on the
current tree: `analysis/reports/v1.13.2/red/RED_waveB_group4.md`; amended 2026-10-15 after the RED critic
(`red/RED_waveB_critic.md` D1-D14) and LB11-LB29, again after LB30-LB37, and a third time after LB38:
`red/RED_waveB_amend.md`.

The confirmed REDs of `test_1132_red_mlog_chkp.py` (A7, C6, N137, N144, F11, N190, E118) stay as they are. This file
adds:

  A7 F-1   log start below log end: a check keyed on +0x18 must not pass (RED_mlog_chkp.md critic F-1).
  N137 F-2 default `mlog` counts only the current instance's records (critic F-2).
  LB1      `mlog --earlier-logs` shows ONLY the records of an earlier volume's log, every output mode, exit 0;
           default `mlog` and `timeline` leave them out and state the count with the option's name, exit 0; the
           count is in the unit of the command's own listing, named (LB14): `mlog` LOG RECORDS, `timeline` ROWS.
           `--raw-scan` is in that set (LB36): it leaves out and counts the earlier volume's records, and
           `--earlier-logs --raw-scan` lists only them.
  N138     the control copy in use is the newest copy that verifies.
  N144     (the decision scan's settlement for a copy that really fails) a failed copy not in use: `--stats` and
           `--json` report it and exit 2, other modes 0; the copy in use failing: every `mlog` mode exits 2,
           `--raw-scan` and `--info` included (LB33), and so does `timeline`, whose MLog source reads that copy (LB24);
           each such exit 2 comes with a statement naming the failed control copy, its failure, and that the copy
           in use is affected -- on stderr in export modes, in the text view otherwise (LB38). A copy not in use
           failing leaves the other modes and `timeline` at 0 with no such statement (controls).
  N133     `mlog --json` raises the "MLog page verification" finding and exits 2; it carries each control copy's verdict.
  N218     _SmsRedoRecord+0x20 is a handle, never an "OID"; `--parse -v` says what target_oid is.
  N259     no `vlcn`; no `block_lcn`, each JSON record carries `BlockIndex` = PLCN x blocks-per-cluster + Block
           (LB22) as a lower-case hex string, `"0x123"` (LB32: the form of K9 and of the bundle column); a failing
           record is located one way in every mode.
  N260     one mnemonic per driver handler (LB4/LB4a, the canonical `redo_opcode_complete.md`), the FULL handler name
           for every opcode of both tables (LB29, the decided strings below), the long names one per handler too
           (LB15), the opcode numbers in the CSV (';'-joined, unpadded), one label for an unknown opcode.
  N310     `mlog --json` carries the CSV's transactions, with the same values.
  N311     a CSV row carries its 4 KiB block; the PLCN is hex; one offset base for a record.
  I3/C57   a payload count is not called a transaction count; the transaction starts are printed; a MOVE whose two
           parents cannot be told apart is not printed as a move into the same directory, and is counted.
  N189     the row time is stated for what it is: the latest embedded time of the log payload.
  I1       `timeline`: no "correlated by name/path" claim, a header that says the rows are sorted by time and not
           joined; the undated MLog count is stated in ROWS (LB28; stderr in export modes, LB10); the caveat says
           what the extractor does.
  N173     the A2 framing instrument counts no control page and names a block it flags, and hard-codes no tree on
           sys.path (LB13); the tool counts no control record as redo records; the refuted framing figures leave
           forefst.py.
  N170 B   the fold docstring and the USN parser's docstring/comment say what the code does.
  C6 (LB3) the JSON control area in the decided form, the retired keys removed (decision 33); the control page
           header +0x20 is not named a sequence (N143); N410 (LB12): the control payload's data range on 64 KiB
           volumes is in 4 KiB blocks -- named and used in that unit, the scan's fallback included.
  LB3      mlog's forms, one node per form kind: K21 names (PascalCase, upper-case acronyms: LB26; product names in
           their own spelling, `MLog`, `ReFS`: LB31), hex in machine output, K16 padding, K15 case, K13 LSN, K5
           date-times, K29 version label (`ReFSVersion`, LB31), K6/K7 sizes, K20 absent values, K14 flags, K25 lists
           (every list column), K22 paths (`_usn_resolve_path`'s labels; `timeline`'s MLog rows too, LB16), the CSV
           path split into FullPath + ParentPath (LB27), ParentPath on a row without a name = the object's own parent,
           empty when unknown (LB37); and a control that counts stay decimal.
  N411     (LB40, part 1b, written first) the control payload's fields read at their offsets: the u64 at +0x44 under a
           name for what it holds, never "Total entries"; the payload UUID from +0x28, never +0x50; bytes where no
           field is known shown raw with their offset.
  N412     (LB41, part 1b, written first) no readable control copy: exit 2 in every mode of LB24's set, with a
           statement that no copy could be read and what that means for the listing (stderr in export modes).
  N413     (LB42, part 3, written first) the control header +0x08 (a constant the driver writes and never reads) shown
           raw with its offset, never as "Version"; payload +0x40, the version MlLogOpenLog checks, under its name.
  N414     (LB43, part 3, written first) the earlier-volume filter keys on the volume's format magic and the payload's
           +0x28 UUID (LogValidateEntryHeader), not on the control record header.
  N415     (LB46, part 3, written first) a copy in use whose log version (payload +0x40) is not 1 -- the driver would
           not open the log -- is stated and exits 2 in every mode of LB24's set and `timeline`'s MLog source.
  N418     (LB51, part 3b, written first) a control copy whose header +0x04 is not the volume's signature is refused,
           as LogValidateEntryHeader refuses it: never the copy in use; a failed copy (LB39), or, both refused, N412.
  N419     (LB52, part 3b, written first) MlLogOpenLog's other open tests on the copy in use -- the data range equal to
           the handle's (OID 0x9's start and start + size, in 4 KiB blocks), flags bit 0 set, the log start at or before
           the checkpoint's +0x70 -- each stated and exit 2 in LB24's set and `timeline`'s MLog source, as N415.
  LB53     (part 3b, written first) two cases: another format magic = an earlier volume's log; this volume's signature
           with another UUID = an earlier log of this volume; each counted and named; `mlog --earlier-logs` (LB1's
           option, renamed -- the sanctioned rename is applied in this file) labels each record with its case.

Conventions (those of test_1132_red_mlog_chkp.py, whose codec and runners are imported, not copied)
-------------------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)`` and fails on the current tree at a plain ``assert`` for
  the reason in its mark. Anything else is ``RedFixtureError`` / ``KeptPropertyBroken`` (not AssertionErrors), so a
  fixture problem or a broken kept property FAILS the node instead of passing it as xfail.
* Expected values come from this module's own reads: the synthetic logs are built by this module and
  test_1132_red_mlog_chkp's codec, record counts on the image by this module's own walker of the driver's framing,
  handler identity from `forclaude/intelligence/redo_opcode_complete.md`. Two image constants are measured values
  cited where they are used (61 MOVE rows; the reformatted image's instance split, re-read here).
* Where a wording or a name is not settled, the node asserts the property and says so (the report lists them).
* unit nodes run ``cmd_mlog`` / ``cmd_timeline`` in-process on a synthetic log area with ``bootstrap``,
  ``get_mlog_info`` and ``build_oid_path_map`` patched (as ``mlog_inproc`` does), stdout and stderr kept apart;
  ``..._on_image_...`` nodes run the real CLI on a corpus image, read-only, addressed by its step path (or on a
  hole-preserving scratch copy under ``$FOREFST_RED_SCRATCH``, deleted by exact path).

``pytest -k "not image"`` runs the unit and static nodes only.
"""
import ast
import contextlib
import csv
import datetime
import importlib.util
import inspect
import io
import itertools
import json
import os
import re
import struct
import subprocess
import sys
import traceback
import uuid
from collections import Counter

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21: internal names)
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions, tool paths)
import test_1132_red_mlog_chkp as MC                     # noqa: E402  (MLog codec, SynLog, A7 matchers, corpus)
from test_1132_red_a_verdicts import _fresh_registers, _rc_escalate   # noqa: E402  (one register list)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
FOREFST = AB.FOREFST
SynLog, lsn, le32, le64 = MC.SynLog, MC.lsn, MC.le32, MC.le64
MAGIC_A, MAGIC_B, UUID_A, UUID_B = MC.MAGIC_A, MC.MAGIC_B, MC.UUID_A, MC.UUID_B
END, MLOG_BLK = MC.END, MC.MLOG_BLK
UUID_B_STR = str(uuid.UUID(bytes_le=UUID_B))
_red = MC._red


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Builders (this module's own; the tool's code is not used to build or to check a fixture)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_EPOCH = datetime.datetime(1601, 1, 1)


def filetime(y, mo, d, h, mi, s, frac7):
    """A FILETIME with a 7-digit fraction (100 ns units)."""
    return ((datetime.datetime(y, mo, d, h, mi, s) - _EPOCH) // datetime.timedelta(seconds=1)) * 10 ** 7 + frac7


FT_A, FT_A_ISO = filetime(2026, 5, 16, 16, 55, 20, 9805996), "2026-05-16T16:55:20.9805996Z"
FT_B, FT_B_ISO = filetime(2026, 5, 16, 17, 1, 2, 1234567), "2026-05-16T17:01:02.1234567Z"


def redo_rec(opcode, flags=3, handle=0, ft=None):
    """One _SmsRedoRecord: size at +0, opcode at +4, handle at +0x20, flags at +0x2C (bit 0 start, bit 1 commit).
    With `ft`, a one-value record whose value 0 holds that FILETIME: value count at +0x10, value 0 (offset, length)
    at +0x38, the layout an opcode-0x04 record's embedded time is read from (`_mlog_extract_timestamp`)."""
    if ft is None:
        r = bytearray(0x38)
    else:
        r = bytearray(0x48)
        struct.pack_into("<I", r, 0x10, 1)
        struct.pack_into("<II", r, 0x38, 0x40, 8)
        struct.pack_into("<Q", r, 0x40, ft)
    struct.pack_into("<II", r, 0, len(r), opcode)
    struct.pack_into("<Q", r, 0x20, handle)
    struct.pack_into("<I", r, 0x2C, flags)
    return bytes(r)


def payload_block(magic, uid, opens, lsn_, prev, redo_blocks):
    """A type-2 LogCore record whose payload is a chain of merged redo blocks (CmsRestarter::ForEachBlockInMergedBlock),
    each given as [record, ...] with total_size = the records' sizes and first_off = 8."""
    b = MC._block_header(magic, uid, opens, lsn_, prev)
    payload = b"".join(struct.pack("<II", sum(len(r) for r in recs), 8) + b"".join(recs) for recs in redo_blocks)
    _fx(0xB0 + len(payload) <= MLOG_BLK, "the payload does not fit one 4 KiB log block")
    struct.pack_into("<Q", b, 0x78, lsn_)
    struct.pack_into("<Q", b, 0x78 + 0x18, prev)
    struct.pack_into("<I", b, 0x78 + 0x20, len(payload))
    struct.pack_into("<I", b, 0x78 + 0x28, 0x38)
    struct.pack_into("<I", b, 0x78 + 0x30, 2)
    b[0xB0:0xB0 + len(payload)] = payload
    return MC._seal(b)


def build_log(path, payloads, cs=0x1000, magic=MAGIC_A, uid=UUID_A, gen=1, opens=3, start_k=1):
    """A SynLog (not yet written) whose data-area blocks start_k, start_k + 1, ... hold `payloads` (each a list of
    redo blocks) at LSN (gen, k); control start = end = the next LSN, so the tail is the log end."""
    log = SynLog(path, cs)
    for i, rb in enumerate(payloads):
        k = start_k + i
        log.blocks[k] = payload_block(magic, uid, opens, lsn(gen, k), lsn(gen, k - 1) if i else 0, rb)
    end = lsn(gen, start_k + len(payloads))
    return log.control(end, end, opens=opens)


# the log of the I3 / C57 / N189 / N310 / LB3 nodes: 4 log payloads holding 8 transactions (two merged redo blocks
# each); payload 1's two transactions carry different own times (FT_A, then FT_B), so its row time is FT_B
P_TXN, S_TXN = 4, 8


def _txn_log(tmp_path):
    p1 = [[redo_rec(0x04, 3, 0x177, FT_A)], [redo_rec(0x04, 3, 0x176, FT_B)]]
    rest = [[[redo_rec(0x04)], [redo_rec(0x03)]] for _ in range(P_TXN - 1)]
    return build_log(tmp_path / "log.raw", [p1] + rest).write()


def _handle_log(tmp_path):
    """Two payloads of one record each: handle (+0x20) 0x177, then 0 (an absent handle)."""
    return build_log(tmp_path / "log.raw", [[[redo_rec(0x04, 3, 0x177)]], [[redo_rec(0x04, 3, 0)]]]).write()


def _damaged_record_log(tmp_path, cs=0x1000, k=0x10, last=0x30):
    """Records 1..last at generation 1 (tail = log end); record k gets one flipped byte outside its payload, so its
    fold fails while every parsed field stays intact."""
    log = SynLog(tmp_path / "log.raw", cs).run(1, last, 1, session_start=True)
    log.control(lsn(1, last + 1), lsn(1, last + 1))
    b = bytearray(log.blocks[k])
    b[0x300] ^= 1
    log.blocks[k] = bytes(b)
    log.write()
    p = MC.parse_block(MC.read_block(log.path, log.block_off(k)))
    _fx(p and p["type"] == 2 and p["fold"] != p["stored"], "the flipped record still folds to its stored value")
    return log


def _ctrl_damaged(tmp_path, which):
    """Intact records 1..0x20 (tail = log end 1:21); control copy 0 (sequence 51) and copy 1 (sequence 50); each copy
    in `which` gets one flipped byte inside its own 4 KiB, past the parsed payload fields (its fold fails)."""
    log = SynLog(tmp_path / "log.raw").run(1, 0x20, 1, session_start=True).control(END, END)
    for i in which:
        c = bytearray(log.ctrl[i])
        c[0x200] ^= 1
        log.ctrl[i] = bytes(c)
    log.write()
    for i in range(2):
        p = MC.parse_block(MC.read_block(log.path, (1 + i) * log.cs))
        _fx(p and p["type"] == 1 and (p["fold"] == p["stored"]) == (i not in which) and p["seq"] == 51 - i,
            "control copy %d is not what the case needs: %r" % (i, p))
    return log


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Runners
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_EXTRA_REGS = ("_SKIP_NOTES", "_SKIP_EXPECTED", "_WALK_DAMAGE_REPORTED", "_SKIP_SUMMARY_DONE", "_DEFERRALS",
               "_OT_MAX_LSN", "_INTEGRITY_FAILED")


@pytest.fixture(autouse=True)
def _volume_information(monkeypatch):
    """Every synthetic volume of this file holds the $VOLUME_INFORMATION a real volume does: the harnesses' empty object
    maps are read as Object Tables read in full, whose missing OID 0x500 is a finding since the conformance batch's
    review (N6). Created well before every record of these logs, so no MLog row is undated by it."""
    monkeypatch.setattr(F, "volume_information_read",
                        lambda *a, **k: ({"vol_create_time": filetime(2020, 1, 1, 0, 0, 0, 0), "vol_modify_time": 0}, None))


def inproc(monkeypatch, log, cmd, *args, vmin=14, paths=None):
    """(rc, stdout, stderr) of `forefst <log> <cmd> <args>` in-process on a synthetic log area: rc through the exit
    rule, or the code `die()` exited with. Three volume-layer functions are patched (bootstrap, get_mlog_info,
    build_oid_path_map); everything else is the real code. A guard checks the patched layer was reached, except
    for an unknown option (the only `die()` before the volume is read; LB1's defect)."""
    calls = Counter()

    def _boot(image, partition_start=None):
        calls["bootstrap"] += 1
        return open(log.path, "rb"), 0, log.cs, MC._IdentityTr(), [], {}, 3, vmin, []

    def _info(f, ps, cs, tr, obj_map):
        calls["get_mlog_info"] += 1
        return dict(log.info)

    monkeypatch.setattr(F, "bootstrap", _boot)
    monkeypatch.setattr(F, "get_mlog_info", _info)
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: dict(paths or {}))
    _fresh_registers(monkeypatch)
    for name in _EXTRA_REGS:
        cur = getattr(F, name, None)
        if isinstance(cur, (list, dict)):
            monkeypatch.setattr(F, name, type(cur)())
    fn = {"mlog": F.cmd_mlog, "timeline": F.cmd_timeline}[cmd]
    out, err = io.StringIO(), io.StringIO()
    exited = None
    try:
        with UW.recording() as wrapped, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn(log.path, list(args), None)
    except SystemExit as e:
        exited = e.code
    except Exception:
        raise RedFixtureError("%s %s crashed (a crash is never the defect under test):\n%s"
                              % (cmd, " ".join(args), traceback.format_exc()))
    o, e = UW.unwrap_exact(out.getvalue(), wrapped), err.getvalue()
    if exited is not None:
        _fx(calls["bootstrap"] == 0 and "unknown option" in e,
            "%s %s exited through die() (%r) for another reason:\n%s" % (cmd, " ".join(args), exited, e[-2000:]))
        return exited, o, e
    _fx(calls["bootstrap"] == 1 and calls["get_mlog_info"] >= 1,
        "%s no longer reaches the patched volume layer (%r): adapt inproc" % (cmd, dict(calls)))
    return _rc_escalate()(0 if rc is None else rc), o, e


_CLI = {}


def cli(rel, *args):
    """(rc, stdout, stderr) of the real forefst CLI on a corpus image addressed by its step path, read-only, once
    per process. A traceback or a timeout is a fixture error; `die()` (exit 1, one line) is returned."""
    img = MC.corpus(rel)
    key = (img, args)
    if key not in _CLI:
        cmd = [sys.executable, "-B", FOREFST, img] + list(args)
        try:
            r = UW.run(cmd, capture_output=True, text=True, timeout=MC.TIMEOUT, cwd=REPO)
        except subprocess.TimeoutExpired:
            raise RedFixtureError("timeout: %s" % " ".join(cmd))
        if "Traceback (most recent call last)" in r.stderr:
            raise RedFixtureError("the tool crashed (never the defect under test):\n" + r.stderr[-3000:])
        _CLI[key] = (r.returncode, r.stdout, r.stderr)
    return _CLI[key]


def _ctx(rc, out, err=""):
    return "\n| rc=%s\n| stdout: %s\n| stderr: %s" % (rc, out[-3000:], err[-1500:])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Readers (layout-tolerant: the forms change in this wave, so every reader finds by content, not by column)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def labelled_int(text, label):
    m = re.search(r"(?im)^\s*%s\s*:\s*(\d+)\s*$" % re.escape(label), text)
    return int(m.group(1)) if m else None


def redo_records(text):
    """The listing's count of redo records. Wave C step C1 (N437, U-5: one unit word per count) renamed the label
    `Total records` to `Redo records`; both are read (C1_LEAD_SETTLEMENTS C-5: the value checks are unchanged)."""
    for label in ("Redo records", "Total records"):
        v = labelled_int(text, label)
        if v is not None:
            return v
    return None


def _has_num(line, n):
    return re.search(r"(?<![\d,.xX])%d(?![\d,])" % n, line) is not None


# LB45 (wave B part 3): what `int(v, 0)` accepts, matched first, so the reader needs no `except ValueError: return None`
_INT_LITERAL = re.compile(r"\s*[-+]?(?:0[xX](?:_?[0-9a-fA-F])+|0[oO](?:_?[0-7])+|0[bB](?:_?[01])+|0(?:_?0)*"
                          r"|[1-9](?:_?[0-9])*)\s*\Z")


def _as_int(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 0) if _INT_LITERAL.match(v) else None
    return None


def _walk(o, path=""):
    """(path, key, value) for every key of every dict, at any depth."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield path, k, v
            for t in _walk(v, "%s/%s" % (path, k)):
                yield t
    elif isinstance(o, list):
        for i, v in enumerate(o):
            for t in _walk(v, "%s[%d]" % (path, i)):
                yield t


def _scalars(o):
    if isinstance(o, dict):
        for v in o.values():
            for s in _scalars(v):
                yield s
    elif isinstance(o, list):
        for v in o:
            for s in _scalars(v):
                yield s
    else:
        yield o


def _dicts(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            for d in _dicts(v):
                yield d
    elif isinstance(o, list):
        for v in o:
            for d in _dicts(v):
                yield d


def _list_elements(o):
    """Every dict that is an element of a list, at any depth (records, transactions, failures, copies)."""
    if isinstance(o, dict):
        for v in o.values():
            for d in _list_elements(v):
                yield d
    elif isinstance(o, list):
        for v in o:
            if isinstance(v, dict):
                yield v
            for d in _list_elements(v):
                yield d


def _ci_get(d, name, default=None):
    for k, v in (d or {}).items():
        if k.lower() == name.lower():
            return v
    return default


def _keys_matching(o, pattern):
    r = re.compile(pattern)
    return sorted({"%s/%s" % (p, k) for p, k, _v in _walk(o) if r.search(k)})


def _load_json(out, what="mlog --json"):
    """stdout as ONE JSON document (an export to stdout holds the export only)."""
    try:
        return json.loads(out)
    except ValueError as e:
        raise AssertionError("%s: stdout is not one JSON document (%s): %r" % (what, e, out[:300]))


def _data_records(j):
    """The redo records of an mlog JSON: list elements that carry an `opcode` key (any case)."""
    return [d for d in _list_elements(j) if any(k.lower() == "opcode" for k in d)]


def _data_plcns(j, lo, hi):
    """PLCN values held by list elements under a key named `plcn` (any case), inside the data area [lo, hi)."""
    out = []
    for d in _list_elements(j):
        for k, v in d.items():
            if k.lower() == "plcn":
                n = _as_int(v)
                if n is not None and lo <= n < hi:
                    out.append(n)
    return out


_VERDICT_KEY = re.compile(r"(?i)verif|valid|^ok$|status|verdict|integrity|pass")


def _copy_verdicts(j, plcns=(1, 2)):
    """{control PLCN: True/False}: the objects of the JSON that carry a control copy's PLCN and a verdict."""
    out = {}
    for d in _dicts(j):
        pl = [_as_int(v) for k, v in d.items() if re.search(r"(?i)plcn", k)]
        hit = [p for p in pl if p in plcns]
        if not hit:
            continue
        for k, v in d.items():
            if not _VERDICT_KEY.search(k):
                continue
            if isinstance(v, bool):
                out[hit[0]] = v
            elif isinstance(v, str) and re.fullmatch(r"(?i)verified|ok|pass(?:ed)?|valid", v):
                out[hit[0]] = True
            elif isinstance(v, str) and re.search(r"(?i)fail|bad|invalid|mismatch", v):
                out[hit[0]] = False
    return out


def csv_table(text, key=r"(?i)^plcn$"):
    """(header, rows, index of the header line among stdout's non-empty lines) of an mlog CSV."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        cells = next(csv.reader([ln]))
        if any(re.search(key, c) for c in cells):
            return cells, [r for r in csv.reader(lines[i + 1:])], i
    raise RedFixtureError("no CSV header with a column matching %r on stdout: %r" % (key, text[:400]))


def _col(hdr, pattern):
    idx = [i for i, h in enumerate(hdr) if re.search(pattern, h)]
    _fx(len(idx) == 1, "expected one CSV column matching %r in %r" % (pattern, hdr))
    return idx[0]


def _section(text, title):
    """The lines of the `====`-framed section whose title line contains `title`."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if title in ln and i + 1 < len(lines) and lines[i + 1].startswith("===="):
            out = []
            for l2 in lines[i + 2:]:
                if l2.startswith("===="):
                    break
                out.append(l2)
            return out
    return []


def _redo_table(text):
    """(header, rows) of `mlog -v`'s redo-record table: the lines after the header that names Opcode, Name, Size."""
    lines = text.splitlines()
    i = next((j for j, ln in enumerate(lines)
              if re.search(r"\bOpcode\b", ln) and re.search(r"\bName\b", ln) and re.search(r"\bSize\b", ln)), None)
    _fx(i is not None, "mlog -v printed no redo-record table:\n" + text[-2000:])
    rows = []
    for ln in lines[i + 2:]:
        if not ln.strip():
            break
        rows.append(ln)
    _fx(rows, "the redo-record table has no row")
    return lines[i], rows


def _parse_rows(text):
    """[(row line, the line after it)] of `mlog --parse`: each transaction row and its mnemonic line."""
    lines = text.splitlines()
    return [(ln, lines[i + 1] if i + 1 < len(lines) else "") for i, ln in enumerate(lines)
            if re.match(r"^  \[[^\]]+\]", ln) and not re.match(r"^  \[CLASS\] is DERIVED", ln)]   # P8's legend line


_PLCN_V = re.compile(r"@PLCN (0x[0-9a-fA-F]+|\d+)\.blk(\d+)")


def _parse_v_plcns(text):
    return [int(m.group(1), 0) for m in _PLCN_V.finditer(text)]


# LB36: a `--raw-scan` page row starts with its locator -- today 'VLCN 0x000011  PLCN 0x000011', after N259/N311 the
# one block form ('0x11.blk0', with or without a 'PLCN' label). Read over the WHOLE stdout, so a row moved to another
# section is still a row listed (a statement or a 'Control PLCN:' line starts with a word, not a locator).
_RAW_ROW = re.compile(r"^\s+(?:VLCN\s+0x[0-9a-fA-F]+\s+)?(?:PLCN[\s:=]+)?(0x[0-9a-fA-F]+)(?:\.(?:blk)?\d+)?\s")


def _raw_rows(text):
    """[(PLCN, line)] of the page rows `mlog --raw-scan` printed."""
    return [(int(m.group(1), 16), ln) for ln in text.splitlines() for m in [_RAW_ROW.match(ln)] if m]


def earlier_statement(text, counts):
    """LB1: lines (or two-line windows) that name `--earlier-logs` and give one of `counts` as the number left out."""
    lines = text.splitlines()
    out = []
    for i in range(len(lines)):
        for blob in (lines[i], " ".join(lines[i:i + 2])):
            if "--earlier-logs" in blob and any(_has_num(blob, n) for n in counts):
                out.append(blob)
                break
    return out


def _states_latest_payload_time(text):
    """N189 / I1: a line (or two-line window) that says the time shown is the LATEST embedded time of the payload."""
    lines = text.splitlines()
    for i in range(len(lines)):
        blob = " ".join(lines[i:i + 2])
        if (re.search(r"(?i)\blatest\b", blob) and re.search(r"(?i)\bpayloads?\b|\blog records?\b", blob)
                and re.search(r"(?i)\btimes?\b|timestamp|filetime", blob)):
            return blob
    return None


def _says_sorted_not_joined(text):
    """I1 (critic D11): a line (or two-line window) of the header saying the rows are sorted by time and NOT joined
    (correlated, matched) across sources. The wording is not settled: the property only."""
    lines = text.splitlines()
    for i in range(len(lines)):
        blob = " ".join(lines[i:i + 2])
        if (re.search(r"(?i)\bsort\w*", blob) and re.search(r"(?i)\btime\b", blob)
                and re.search(r"(?i)\bnot\b[^.;]{0,40}\b(?:join|correlat|match|link)\w*"
                              r"|\bno\b[^.;]{0,20}\b(?:join|correlat)\w*|\b(?:un|non-)(?:joined|correlated)\b", blob)):
            return blob
    return None


_UNIT_RECORDS = re.compile(r"(?i)\brecords?\b|\brecord\(s\)")       # LB14: `mlog` names its unit, log records
_UNIT_ROWS = re.compile(r"(?i)\brows?\b|\brow\(s\)")                # LB14 / LB28: `timeline` names its unit, rows


def stated_count(text, n, wrong, unit):
    """LB14: (the statements that give `n` with the option's name and the unit word, the statements that give one
    of the `wrong` counts -- another unit's -- without `n`)."""
    hits = [h for h in earlier_statement(text, (n,)) if unit.search(h)]
    other = [h for h in earlier_statement(text, wrong) if not _has_num(h, n)]
    return hits, other


# K22 A: an unresolved directory takes `_usn_resolve_path`'s labels; the OID in the label is the row's own OID
_RESOLVE_LABEL = re.compile(r"^<(?:oid|unlinked|system) 0x([0-9a-f]+)>")
# K21 + LB26: acronyms are upper case in a PascalCase name (PLCN, OID, UUID, LSN, LCN, VCN, SID, CRC); "MLog" is a name
_MIXED_ACRONYM = re.compile(r"(?:Plcn|Oid|Uuid|Lsn|Lcn|Vcn|Sid|Crc)(?![a-z])")
# LB31 (and LB26's "MLog stays MLog"): a product name keeps its own spelling inside a field name -- `ReFSVersion`,
# `MLogInfo`; `RefsVersion` / `MlogInfo` re-spell it. ("Refs" is refused only at the start of a name, before a capital,
# where it can only be the product: an English plural such as `PageRefs` is not touched.)
_PRODUCT_CASE = re.compile(r"^Refs(?=[A-Z0-9]|$)|^REFS(?=[A-Z0-9]|$)|Mlog(?![a-z])|MLOG(?![a-z])")


def _tl_mlog_rows(out, mode):
    """M2: `timeline`'s MLog rows for any output mode -- text, --csv (`_timeline_mlog_rows`), --json, --jsonl."""
    if mode in (("--json",), ("--jsonl",)):
        try:
            recs = (json.loads(out) if mode == ("--json",)
                    else [json.loads(ln) for ln in out.splitlines() if ln.strip()])
        except ValueError as e:
            raise AssertionError("timeline %s: stdout is not the export (%s): %r" % (mode[0], e, out[:300]))
        if isinstance(recs, dict):                 # acceptance 1.14.0 (N312): `--json` is an envelope; its Events
            recs = recs.get("Events") or []
        return [r for r in recs if isinstance(r, dict) and (r.get("Source") or r.get("source")) == "MLog"]
    return _timeline_mlog_rows(out, bool(mode))


def _timeline_mlog_rows(out, csv_mode):
    """`timeline`'s MLog rows: CSV rows (lists) whose source is MLog, or the text rows -- a time (or '(undated)')
    first, then the source MLog (not the header's 'MLog=4' or the caveat's '... + MLog only')."""
    if csv_mode:
        lines = [ln for ln in out.splitlines() if ln.strip()]
        # acceptance 1.14.0 (P9): the Source column found by its header -- TimeSource now precedes it
        hdr = next(csv.reader(lines[:1]), [])
        si = hdr.index("Source") if "Source" in hdr else 1
        return [r for r in csv.reader(lines[1:]) if len(r) > si and r[si] == "MLog"]
    return [ln for ln in out.splitlines() if re.match(r"^\s+(?:\d{4}-\d\d-\d\d|\(undated\))[^\n]*?\sMLog\s", ln)]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A7 F-1 -- log start below log end (RED_mlog_chkp.md critic F-1)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_a7_records_missing_between_log_start_and_log_end_exit_2(monkeypatch, tmp_path):
    start, end = lsn(1, 0x21), lsn(1, 0x28)
    log = (SynLog(tmp_path / "log.raw").run(1, 0x27, 1, session_start=True)
           .control(start, end).zero(0x22, 0x27).write())                # tail 1:22 = just above the log start
    rc, text = MC.mlog_inproc(monkeypatch, log, "--stats")
    MC._assert_a7_finding(rc, text, [end, lsn(1, 0x22), lsn(1, 0x21)])


LABF = ("step7/labFbeforereboot.raw", (0x19000000, 0x19001000), 0x9000000, 0x19000000)


def test_a7_records_missing_below_the_log_end_exit_2_on_image_labFbeforereboot():
    rel, ctrl_offs, ds_off, de_off = LABF
    lo, hi = 0x4B00, 0x4DC2
    with MC.scratch_copy(rel, 200 << 20) as (src, p):
        L = MC.ImageLog(p, ctrl_offs, ds_off, de_off)
        c = L.ctrl
        _fx((c["start"], c["end"]) == (lsn(8, 0x89C), lsn(8, 0x4B41)),
            "labFbeforereboot: control start/end are 0x%x/0x%x, not 8:89c/8:4b41" % (c["start"], c["end"]))
        cur = {o: r for o, r in L.records().items() if (r["magic"], r["uuid"]) == (c["magic"], c["uuid"])}
        for k in range(lo - 1, hi + 1):
            r = cur.get(ds_off + k * MLOG_BLK)
            _fx(r is not None and r["lsn"] == lsn(8, k) and r["fold"] == r["stored"],
                "labFbeforereboot: block 0x%x is not the intact record 8:%x" % (k, k))
        _fx(max(r["lsn"] for r in cur.values()) == lsn(8, hi), "labFbeforereboot: 8:4dc2 is not the newest record")
        MC._zero_range(p, ds_off + lo * MLOG_BLK, (hi - lo + 1) * MLOG_BLK)
        rc, text = MC.run_tool(FOREFST, p, "mlog", "--stats")
    MC._assert_a7_finding(rc, text, [c["end"], lsn(8, lo), lsn(8, lo - 1)])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N137 F-2 -- default `mlog` counts (RED_mlog_chkp.md critic F-2)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("which", ["magic+uuid", "uuid-only"])
def test_n137_default_mlog_counts_only_the_current_instances_records(monkeypatch, tmp_path, which):
    log = MC._n137_log(tmp_path, *((MAGIC_B, UUID_B) if which == "magic+uuid" else (MAGIC_A, UUID_B)))
    rc, out, err = inproc(monkeypatch, log, "mlog")
    tot, starts = redo_records(out), labelled_int(out, "Transaction starts")
    _fx(tot is not None and starts is not None, "default mlog printed no record counts" + _ctx(rc, out, err))
    assert (tot, starts) == (32, 32), "Total records %s / Transaction starts %s; the current instance holds 32 / 32" \
                                      % (tot, starts)


def payload_of(block):
    eh = le32(block, 0x54)
    return block[eh + le32(block, eh + 0x28): eh + le32(block, eh + 0x28) + le32(block, eh + 0x20)]


def driver_records(payload):
    """[(offset, size, opcode, flags)] of one log payload, by the driver's two loops
    (CmsRestarter::ForEachBlockInMergedBlock, then ForEachRedoInBlock with the block's own total_size as budget)."""
    out, base, remaining = [], 0, len(payload)
    while remaining >= 8 and base + 8 <= len(payload):
        total, first = le32(payload, base), le32(payload, base + 4)
        if total == 0 or total > remaining:
            break
        if total + first >= 8 and total >= 0x38:
            p, budget = base + first, total
            while p + 4 <= len(payload):
                sz = le32(payload, p)
                if sz == 0 or sz > budget or p + sz > len(payload):
                    break
                out.append((p, sz, le32(payload, p + 4), le32(payload, p + 0x2C) if p + 0x30 <= len(payload) else 0))
                budget -= sz
                if budget < 0x38:
                    break
                p += sz
        step = first + total
        if step <= 0:
            break
        remaining -= step
        base += step
    return out


def _own_redo_counts(img, ds_off, ks):
    n = starts = 0
    for k in ks:
        for _p, _sz, _op, flags in driver_records(payload_of(MC.read_block(img, ds_off + k * MLOG_BLK))):
            n += 1
            starts += flags & 1
    return n, starts


def test_n137_default_mlog_counts_only_the_current_instance_on_image_win11refs2gtargeted_reformated():
    R = MC._Reformated()
    n, s = _own_redo_counts(MC.corpus(R.rel), MC.REFORMATED[2], sorted(R.cur))
    _fx((n, s) == (386, 190), "this module's walker reads %d / %d current-instance records / starts, not the "
                              "census's 386 / 190" % (n, s))
    rc, out, err = cli(R.rel, "mlog", "--stats")
    got = (redo_records(out), labelled_int(out, "Transaction starts"))
    assert got == (n, s), "Total records / Transaction starts %r; the current instance holds %r" % (got, (n, s))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# LB1 -- `mlog --earlier-logs`, and the statement in default `mlog` and `timeline` (Q1 A, decision 36)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# The synthetic log of N137 (test_1132_red_mlog_chkp._n137_log): the current instance holds blocks 1..0x20, an
# earlier volume's log blocks 0x21..0x30 (16 records, one per payload) at higher LSNs; "uuid-only" keeps the magic.

N_OLD = 16


def _lb1(tmp_path, which):
    return MC._n137_log(tmp_path, *((MAGIC_B, UUID_B) if which == "magic+uuid" else (MAGIC_A, UUID_B)))


def _old_clusters(log):
    return {log.cluster_of(k) for k in MC.N137_OLD}


def _names_the_earlier_instance(text_or_cells, which):
    """The UUID that differs is shown, and on the magic+uuid log the magic too (hex or decimal)."""
    blob = text_or_cells if isinstance(text_or_cells, str) else " ".join(text_or_cells)
    ok = UUID_B_STR in blob
    if which == "magic+uuid":
        ok = ok and re.search(r"(?i)(?<![0-9a-fx])(?:0x0*%x|%d)(?![0-9a-f])" % (MAGIC_B, MAGIC_B), blob) is not None
    return ok


@pytest.mark.parametrize("which", ["magic+uuid", "uuid-only"])
def test_lb1_earlier_volume_text_counts_only_the_earlier_volumes_records(monkeypatch, tmp_path, which):
    rc, out, err = inproc(monkeypatch, _lb1(tmp_path, which), "mlog", "--earlier-logs")
    assert rc == 0, "`mlog --earlier-logs` must exit 0 (LB1)" + _ctx(rc, out, err)
    tot = redo_records(out)
    assert tot == N_OLD, "Total records %r: the earlier volume's log holds %d records" % (tot, N_OLD)
    assert _names_the_earlier_instance(out, which), "the magic/UUID that differ are not shown" + _ctx(rc, out, err)


@pytest.mark.parametrize("which", ["magic+uuid", "uuid-only"])
def test_lb1_earlier_volume_csv_rows_are_the_earlier_volumes_payloads(monkeypatch, tmp_path, which):
    log = _lb1(tmp_path, which)
    rc, out, err = inproc(monkeypatch, log, "mlog", "--earlier-logs", "--csv")
    assert rc == 0, "`mlog --earlier-logs --csv` must exit 0 (LB1)" + _ctx(rc, out, err)
    hdr, rows, at = csv_table(out)
    assert at == 0, "stdout carries the export only: the CSV header must be its first line" + _ctx(rc, out, err)
    pc = _col(hdr, r"(?i)^plcn$")
    plcns = [_as_int(r[pc]) for r in rows]
    assert sorted(plcns) == sorted(_old_clusters(log)), "rows at PLCNs %r; the earlier volume's records are at %r" \
        % (sorted(set(plcns)), sorted(_old_clusters(log)))
    bad = [r for r in rows if not _names_the_earlier_instance(r, which)]
    assert not bad, "rows without the magic/UUID that differ (LB1: the same columns plus those): %r" % bad[:2]


def test_lb1_earlier_volume_json_holds_only_the_earlier_volumes_records(monkeypatch, tmp_path):
    log = _lb1(tmp_path, "magic+uuid")
    rc, out, err = inproc(monkeypatch, log, "mlog", "--earlier-logs", "--json")
    assert rc == 0, "`mlog --earlier-logs --json` must exit 0 (LB1)" + _ctx(rc, out, err)
    j = _load_json(out)
    got = set(_data_plcns(j, log.DS, log.de))
    assert got == _old_clusters(log), "JSON records at PLCNs %r; the earlier volume's records are at %r" \
        % (sorted(got), sorted(_old_clusters(log)))
    assert _names_the_earlier_instance(" ".join(str(s) for s in _scalars(j)), "magic+uuid"), \
        "the JSON does not carry the earlier volume's magic and UUID"


def test_lb1_earlier_volume_parse_lists_only_the_earlier_volumes_records(monkeypatch, tmp_path):
    log = _lb1(tmp_path, "magic+uuid")
    rc, out, err = inproc(monkeypatch, log, "mlog", "--earlier-logs", "--parse", "-v")
    assert rc == 0, "`mlog --earlier-logs --parse -v` must exit 0 (LB1)" + _ctx(rc, out, err)
    got = set(_parse_v_plcns(out))
    assert got == _old_clusters(log), "--parse -v records at PLCNs %r; the earlier volume's are at %r" \
        % (sorted(got), sorted(_old_clusters(log)))
    assert _names_the_earlier_instance(out, "magic+uuid"), "the magic/UUID that differ are not shown"


# LB36: `--raw-scan` is in LB1's set (it leaves out and counts the earlier volume's records, like every other mode)
_LB1_MODES = [(), ("--stats",), ("-v",), ("--parse",), ("--csv",), ("--json",), ("--raw-scan",)]
_LB1_IDS = ["default", "stats", "verbose", "parse", "csv", "json", "raw-scan"]

# LB14: each command counts in the unit of its own listing and names it. The synthetic logs below keep the units
# apart (critic D3): the earlier volume's 16 log records hold 3 redo records each (48), so a count of redo records
# cannot pass for the count of log records.
N_OLD_REDO = 3 * N_OLD


def _lb1_units_log(tmp_path):
    """Current instance: blocks 1..0x20, one redo record each (as _n137_log); an earlier volume's log: 16 log records
    at blocks 0x21..0x30 (generation 2, MAGIC_B / UUID_B), each a payload of THREE redo records (three
    transactions) -- 16 log records, 48 redo records."""
    log = SynLog(tmp_path / "log.raw").run(1, 0x20, 1, session_start=True)
    for k in MC.N137_OLD:
        log.blocks[k] = payload_block(MAGIC_B, UUID_B, 3, lsn(2, k), lsn(2, k - 1),
                                      [[redo_rec(0x04)], [redo_rec(0x03)], [redo_rec(0x01)]])
    log.control(END, END).write()
    old = [driver_records(payload_of(MC.read_block(log.path, log.block_off(k)))) for k in MC.N137_OLD]
    _fx(len(old) == N_OLD and sum(len(x) for x in old) == N_OLD_REDO,
        "the earlier volume's log does not hold %d log records / %d redo records" % (N_OLD, N_OLD_REDO))
    return log


@pytest.mark.parametrize("mode", _LB1_MODES, ids=_LB1_IDS)
def test_lb1_default_mlog_states_the_count_left_out_with_the_options_name(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _lb1_units_log(tmp_path), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    hits, other = stated_count(err if export else out + "\n" + err, N_OLD, (N_OLD_REDO,), _UNIT_RECORDS)
    assert hits, "no statement gives the %d log records left out, named as records, with `mlog --earlier-logs`%s" % (
        N_OLD, " on stderr (export to stdout)" if export else "") + _ctx(rc, out, err)
    assert not other, "a statement counts the %d redo records, not the %d log records (LB14): %r" % (
        N_OLD_REDO, N_OLD, other)
    assert rc == 0, "records of an earlier volume's log are not a finding (Q1 A): exit 0" + _ctx(rc, out, err)
    if mode == ("--csv",):
        assert csv_table(out)[2] == 0, "stdout carries the export only (the CSV header first)"
    if mode == ("--json",):
        _load_json(out)


@pytest.mark.parametrize("which", ["magic+uuid", "uuid-only"])
def test_lb36_raw_scan_leaves_out_the_earlier_volumes_records(monkeypatch, tmp_path, which):
    log = _lb1(tmp_path, which)
    rc, out, err = inproc(monkeypatch, log, "mlog", "--raw-scan")
    rows = {p for p, _ln in _raw_rows(out)}
    cur = {log.cluster_of(k) for k in MC.N137_CUR}
    _keep(cur <= rows, "--raw-scan no longer lists this volume's own %d pages: missing %r" % (
        len(cur), sorted(cur - rows)[:4]) + _ctx(rc, out, err))
    kept = sorted(rows & _old_clusters(log))
    assert not kept, "--raw-scan lists %d page(s) of the earlier volume's log, e.g. PLCN %s (LB36: left out)" % (
        len(kept), ", ".join(hex(p) for p in kept[:3]))
    _keep(rc == 0, "records of an earlier volume's log are not a finding (Q1 A): exit %d" % rc)


@pytest.mark.parametrize("which", ["magic+uuid", "uuid-only"])
def test_lb36_earlier_volume_raw_scan_lists_only_the_earlier_volumes_records(monkeypatch, tmp_path, which):
    log = _lb1(tmp_path, which)
    rc, out, err = inproc(monkeypatch, log, "mlog", "--earlier-logs", "--raw-scan")
    assert rc == 0, "`mlog --earlier-logs --raw-scan` must exit 0 (LB1, LB36)" + _ctx(rc, out, err)
    rows = _raw_rows(out)
    got = sorted({p for p, _ln in rows})
    assert got == sorted(_old_clusters(log)), "--earlier-logs --raw-scan rows at PLCNs %r; the earlier volume's " \
        "records are at %r" % ([hex(p) for p in got], [hex(p) for p in sorted(_old_clusters(log))])
    bad = [ln.strip() for _p, ln in rows if not _names_the_earlier_instance(ln, which)]
    assert not bad, "rows without the magic/UUID that differ (LB1: the same columns plus those): %r" % bad[:2]


def _two_volume_dated_log(tmp_path):
    """Current instance: 4 dated payloads (generation 1). An earlier volume's log (generation 2): 4 dated payloads
    and 1 undated one, two redo records each -- 4 rows `timeline` would have printed, 5 log records, 10 redo
    records (LB14 / LB28: `timeline` counts its rows)."""
    log = SynLog(tmp_path / "log.raw")
    for k in range(1, 5):
        log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_A + k)]])
    for k in range(5, 9):
        log.blocks[k] = payload_block(MAGIC_B, UUID_B, 7, lsn(2, k), lsn(2, k - 1) if k > 5 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_B + k)], [redo_rec(0x03)]])
    log.blocks[9] = payload_block(MAGIC_B, UUID_B, 7, lsn(2, 9), lsn(2, 8), [[redo_rec(0x04)], [redo_rec(0x03)]])
    return log.control(lsn(1, 5), lsn(1, 5)).write()


@pytest.mark.parametrize("mode", [(), ("--csv",)], ids=["text", "csv"])
def test_lb1_timeline_states_the_mlog_count_left_out_with_the_options_name(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _two_volume_dated_log(tmp_path), "timeline", "--fast", *mode)
    hits, other = stated_count(err if mode else out + "\n" + err, 4, (5, 10), _UNIT_ROWS)
    assert hits, "no statement gives the 4 earlier-volume rows left out, named as rows, with `mlog --earlier-logs`" \
        + _ctx(rc, out, err)
    assert not other, "a statement counts the earlier volume's log records (5) or redo records (10), not its 4 rows " \
                      "(LB14): %r" % other
    assert rc == 0, "exit 0 (Q1 A)" + _ctx(rc, out, err)
    if mode:
        lines = [ln for ln in out.splitlines() if ln.strip()]
        _fx(lines, "timeline --csv wrote nothing to stdout")
        assert "source" in lines[0].lower(), "stdout carries the export only (the CSV header first): %r" % lines[0]
    rows = _timeline_mlog_rows(out, bool(mode))
    assert len(rows) == 4, "%d MLog rows; the current instance has 4 dated payloads" % len(rows)


REF_UUID_OLD, REF_MAGIC_OLD = "c2fb82a9-3974-41e9-a14f-f18d38af84c8", 0x6D790647


def test_lb1_earlier_volume_csv_lists_the_earlier_volumes_payloads_on_image_win11refs2gtargeted_reformated():
    R = MC._Reformated()
    rc, out, err = cli(R.rel, "mlog", "--earlier-logs", "--csv")
    assert rc == 0, "`mlog --earlier-logs --csv` must exit 0" + _ctx(rc, out, err)
    hdr, rows, at = csv_table(out)
    plcns = [_as_int(r[_col(hdr, r"(?i)^plcn$")]) for r in rows]
    assert sorted(plcns) == sorted(R.old_plcn), "%d rows at %d PLCNs; the earlier log's 119 payloads are at %d" \
        % (len(plcns), len(set(plcns)), len(R.old_plcn))
    bad = [r for r in rows if REF_UUID_OLD not in r or REF_MAGIC_OLD not in [_as_int(c) for c in r]]
    assert not bad, "rows without the earlier log's magic 0x6d790647 / UUID c2fb82a9-...: %r" % bad[:2]


@pytest.mark.parametrize("form", ["mlog-stats", "mlog-raw-scan", "timeline-csv"])
def test_lb1_mlog_and_timeline_state_the_count_left_out_on_image_win11refs2gtargeted_reformated(form):
    R = MC._Reformated()
    if form.startswith("mlog-"):
        rc, out, err = cli(R.rel, "mlog", "--" + form[len("mlog-"):])
        text, n, wrong, unit = out + "\n" + err, 119, (677,), _UNIT_RECORDS
    else:
        rc, out, err = cli(R.rel, "timeline", "--csv")
        text, n, wrong, unit = err, 96, (119, 677), _UNIT_ROWS
        first = next((ln for ln in out.splitlines() if ln.strip()), "")
        _keep("source" in first.lower(), "timeline --csv: stdout must start with the CSV header: %r" % first)
    _keep(rc == 0, "golden rc 0 (Q1 A keeps it): rc %d" % rc)
    hits, other = stated_count(text, n, wrong, unit)
    assert hits, "no statement gives the %d %s left out with `mlog --earlier-logs` (LB14)" % (
        n, "log records" if n == 119 else "rows") + _ctx(rc, out[-400:], err)
    assert not other, "a statement gives another unit's count (%r) instead of %d (LB14): %r" % (wrong, n, other)


@pytest.mark.parametrize("view", ["default", "earlier-logs"])
def test_lb36_raw_scan_leaves_out_the_earlier_volumes_records_on_image_win11refs2gtargeted_reformated(view):
    R = MC._Reformated()
    args = ("mlog", "--raw-scan") if view == "default" else ("mlog", "--earlier-logs", "--raw-scan")
    rc, out, err = cli(R.rel, *args)
    if view == "default":
        _keep(rc == 0, "golden rc 0 (Q1 A keeps it): rc %d" % rc)
        rows = {p for p, _ln in _raw_rows(out)}
        _keep(R.cur_plcn <= rows, "--raw-scan no longer lists the %d pages of this volume's log: %d missing" % (
            len(R.cur_plcn), len(R.cur_plcn - rows)))
        kept = sorted(rows & R.old_plcn)
        assert not kept, "--raw-scan lists %d of the earlier log's %d pages, e.g. PLCN %s (LB36: left out)" % (
            len(kept), len(R.old_plcn), ", ".join(hex(p) for p in kept[:3]))
    else:
        assert rc == 0, "`mlog --earlier-logs --raw-scan` must exit 0" + _ctx(rc, out[-400:], err)
        rows = _raw_rows(out)
        got = {p for p, _ln in rows}
        assert got == R.old_plcn, "%d rows at %d PLCNs; the earlier log's 119 pages are at %d" % (
            len(rows), len(got), len(R.old_plcn))
        bad = [ln.strip() for _p, ln in rows
               if REF_UUID_OLD not in ln or not re.search(r"(?i)0x0*%x\b" % REF_MAGIC_OLD, ln)]
        assert not bad, "rows without the earlier log's magic 0x6d790647 / UUID c2fb82a9-...: %r" % bad[:2]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N138 and N144's settlement for a control copy that really fails (decision scan, Wave B, N144 row)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n138_the_control_copy_in_use_is_the_newest_copy_that_verifies(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _ctrl_damaged(tmp_path, (0,)), "mlog")
    seq = labelled_int(out, "Sequence")
    _fx(seq is not None, "default mlog printed no 'Sequence' line" + _ctx(rc, out, err))
    assert seq == 50, "the control area shown is sequence %d (copy 0, which fails its fold); copy 1 (50) verifies" \
                      % seq


@pytest.mark.parametrize("mode", ["--stats", "--json"])
@pytest.mark.parametrize("which", [(1,), (0,)], ids=["older-copy-fails", "newer-copy-fails"])
def test_n144_a_failed_control_copy_not_in_use_is_reported_and_exits_2(monkeypatch, tmp_path, mode, which):
    rc, out, err = inproc(monkeypatch, _ctrl_damaged(tmp_path, which), "mlog", mode)
    bad = 1 + which[0]
    if mode == "--json":
        v = _copy_verdicts(_load_json(out))
        assert v.get(bad) is False, "--json carries no failed verdict for the copy at PLCN 0x%x: %r" % (bad, v)
    else:
        v = MC.control_verdicts(out)
        assert which[0] in v and v[which[0]][1] != "verified", "--stats does not report copy %d failed: %r" \
            % (which[0], v)
    assert rc == 2, "a control copy failed: `mlog %s` exits 2" % mode + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--parse",), ("--csv",), ("--info",)], ids=["default", "parse", "csv", "info"])
@pytest.mark.parametrize("which", [(1,), (0,)], ids=["older-copy-fails", "newer-copy-fails"])
def test_n144_control_a_failed_copy_not_in_use_leaves_the_other_modes_at_exit_0(monkeypatch, tmp_path, mode, which):
    """The settlement's other half: only `--stats` and `--json` report a copy not in use (the V-a pattern). With
    N138, the copy in use is the one that verifies, so the newer copy failing is a copy not in use too. `--info`
    (LB33) exits 2 only when the copy IN USE fails, so a copy not in use leaves it at 0 too. LB38's statement is
    for the copy in use: none is printed here, on either stream."""
    rc, out, err = inproc(monkeypatch, _ctrl_damaged(tmp_path, which), "mlog", *mode)
    _keep(rc == 0, "`mlog %s` with only a copy not in use failing: exit %d" % (" ".join(mode), rc) + _ctx(rc, out, err))
    said = lb38_statements(out + "\n" + err, which)
    _keep(not said, "`mlog %s` with only a copy not in use failing says the copy in use is affected (LB38 is for "
                    "the copy in use): %r" % (" ".join(mode), said[:2]))


# LB38: every exit 2 of N144 / LB24 / LB33 comes with a statement naming the failed MLog control copy -- which copy,
# that it failed its fold, that the copy in use is affected -- on stderr in export modes (LB10), in the text view
# otherwise. The wording is not settled, so the reader takes the property. A statement is a line and the next two
# lines of its paragraph. In it: the control area is named ("control" or "MLog"); a failed copy is named, by its
# index ("copy 0") or its PLCN (copy i is at PLCN 1 + i in these logs, as `_ctrl_damaged` reads it); a failure is
# stated; and the copy in use is said to be affected. That last part is an "in use" / "used" / "selected" phrase
# that is not negated, in a clause that neither says the copy verifies nor names a copy that did not fail; or "both
# / every copy ... fail", "no / neither copy ... verifies".
_LB38_AREA = re.compile(r"(?i)\bcontrol\b|\bmlog\b")
_LB38_FAIL = re.compile(r"(?i)\bfail(?:s|ed|ure|ing)?\b|\bdo(?:es)?\s*(?:not|n't)\s+verify\b|\bnot\s+verified\b|"
                        r"\bunverified\b|\bmismatch")
_LB38_IN_USE = re.compile(r"(?i)\bin[ -]use\b|\b(?:is|are|was|were|being)\s+used\b|\bused\s+(?:by|for|to)\b|"
                          r"\bcopy\s+used\b|\bused\s+copy\b|\b(?:selected|chosen)\b|"
                          r"\b(?:current|active)\s+(?:control\s+)?copy\b|\bread\s+(?:from|through)\b")
_LB38_ALL_FAIL = re.compile(r"(?i)\b(?:both|all|every|each)\s+(?:\w+\s+){0,2}cop(?:y|ies)\b(?:(?!verif)[^.;\n]){0,40}"
                            r"\bfail|\b(?:neither|no|none\s+of\s+the)\s+(?:\w+\s+){0,2}cop(?:y|ies)\b[^.;\n]{0,30}"
                            r"\b(?:verif|pass|is\s+valid)")
_LB38_NEG = re.compile(r"(?i)(?:\bnot|n't|\bno\s+longer|\bnever)\W+(?:\w+\W+){0,2}$")
# M1 (RED_waveB_recheck, tightened by the group-4 fixer): a negation AFTER the in-use phrase -- "the copy in use is
# not affected", "... is unaffected", "the copy in use (copy 1) is not affected" -- says the copy in use is NOT
# affected, so it does not count as an LB38 statement either (LB39's statement is exactly that sentence)
_LB38_NEG_AFTER = re.compile(r"(?i)^[^.;\n]{0,30}?(?:\b(?:not|never|no\s+longer)\s+(?:\w+\s+){0,2}affected\b|"
                             r"n't\s+(?:\w+\s+){0,2}affected\b|\bunaffected\b)")
_LB38_OK = re.compile(r"(?i)\bverif(?:ies|ied)\b|\bpasses\b|\bis\s+(?:valid|intact)\b")
_LB38_COPY = re.compile(r"(?i)\b(?:cop(?:y|ies)|slot)\s*#?\s*(\d+)\b")
_LB38_PLCN = re.compile(r"(?i)\bP?LCN\b\W{0,3}(0x[0-9a-f]+|\d+)\b")


def _lb38_copies_named(text):
    """{copy index} named in `text`, by index or by PLCN (copy i at PLCN 1 + i)."""
    got = {int(m.group(1)) for m in _LB38_COPY.finditer(text)}
    for m in _LB38_PLCN.finditer(text):
        v = m.group(1)
        got.add((int(v, 16) if v.lower().startswith("0x") else int(v)) - 1)
    return got


def _lb38_unnegated(rx, clause, after=False):
    return [m for m in rx.finditer(clause) if not _LB38_NEG.search(clause[:m.start()][-24:])
            and not (after and _LB38_NEG_AFTER.search(clause[m.end():]))]


def _lb38_in_use_affected(window, failed, copies=(0, 1)):
    if _LB38_ALL_FAIL.search(window):
        return True
    sound = set(copies) - set(failed)
    for clause in re.split(r"[.;\n]", window):
        if (_lb38_unnegated(_LB38_IN_USE, clause, after=True) and not _lb38_unnegated(_LB38_OK, clause)
                and not (_lb38_copies_named(clause) & sound)):
            return True
    return False


def lb38_statements(text, failed, copies=(0, 1)):
    """The LB38 statements in `text` about the control copies `failed` (indices): see the comment above."""
    failed = set(failed)
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if (_LB38_AREA.search(w) and _lb38_copies_named(w) & failed and _LB38_FAIL.search(w)
                    and _lb38_in_use_affected(w, failed, copies)):
                hits.append(w)
    return hits


def _lb38_where(export):
    return "on stderr (export to stdout)" if export else "in its text view (stdout)"


# every `mlog` mode reads the control copy before it branches (fd:9057): --raw-scan included (critic D4, LB24), and
# `--info`, which reads it before it prints the static reference (fd:9057-9064; LB33)
_N144_MODES = _LB1_MODES + [("--info",)]


@pytest.mark.parametrize("mode", _N144_MODES, ids=_LB1_IDS + ["info"])
def test_n144_the_control_copy_in_use_failing_makes_every_mlog_mode_exit_2(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _ctrl_damaged(tmp_path, (0, 1)), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = lb38_statements(err if export else out, (0, 1))
    assert rc == 2 and said, "the control copy in use fails its fold: `mlog %s` must exit 2 (exit %s) and state it " \
        "%s, naming the failed copy, its failure and that the copy in use is affected (LB38; statement: %s)" % (
            " ".join(mode), rc, _lb38_where(export), "found" if said else "none") + _ctx(rc, out, err)


def _dated_ctrl_log(tmp_path, which):
    """4 dated payloads (blocks 1..4, generation 1; log start = end = 1:5); each control copy in `which` gets one
    flipped byte inside its own 4 KiB, past the parsed payload fields (its fold fails), as in _ctrl_damaged."""
    log = SynLog(tmp_path / ("dated_ctrl_%s.raw" % ("".join(map(str, which)) or "intact")))
    for k in range(1, 5):
        log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_A + k)]])
    log.control(lsn(1, 5), lsn(1, 5))
    for i in which:
        c = bytearray(log.ctrl[i])
        c[0x200] ^= 1
        log.ctrl[i] = bytes(c)
    log.write()
    for i in range(2):
        p = MC.parse_block(MC.read_block(log.path, (1 + i) * log.cs))
        _fx(p and p["type"] == 1 and (p["fold"] == p["stored"]) == (i not in which),
            "control copy %d is not what the case needs: %r" % (i, p))
    return log


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--jsonl",)], ids=["text", "csv", "json", "jsonl"])
def test_n144_lb24_the_control_copy_in_use_failing_makes_timeline_exit_2(monkeypatch, tmp_path, mode):
    # M2 (RED_waveB_recheck, added by the group-4 fixer): LB24 covers every mode of timeline's MLog source, so
    # --json and --jsonl are run too; `_tl_mlog_rows` reads their rows for the premise
    rc0, out0, err0 = inproc(monkeypatch, _dated_ctrl_log(tmp_path, ()), "timeline", "--fast", *mode)
    _fx(rc0 == 0 and len(_tl_mlog_rows(out0, mode)) == 4,
        "the intact log: timeline must list its 4 MLog rows and exit 0 (the premise that its MLog source reads this "
        "log)" + _ctx(rc0, out0, err0))
    rc, out, err = inproc(monkeypatch, _dated_ctrl_log(tmp_path, (0, 1)), "timeline", "--fast", *mode)
    said = lb38_statements(err if mode else out, (0, 1))
    assert rc == 2 and said, "the control copy in use fails its fold: `timeline %s` must exit 2 (exit %s; LB24) and " \
        "state it %s, naming the failed copy, its failure and that the copy in use is affected (LB38; statement: " \
        "%s)" % (" ".join(mode), rc, _lb38_where(bool(mode)), "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",)], ids=["text", "csv"])
@pytest.mark.parametrize("which", [(1,), (0,)], ids=["older-copy-fails", "newer-copy-fails"])
def test_n144_lb38_control_a_failed_copy_not_in_use_leaves_timeline_at_exit_0(monkeypatch, tmp_path, mode, which):
    """LB24's other half: `timeline` exits 2 only when the copy IN USE fails (the settlement reports a copy not in use
    in `mlog --stats` / `--json` only), keeps its 4 MLog rows, and says nothing of the copy in use (LB38), on either
    stream. With N138 the newer copy (sequence 51) failing is a copy not in use too."""
    rc, out, err = inproc(monkeypatch, _dated_ctrl_log(tmp_path, which), "timeline", "--fast", *mode)
    _keep(rc == 0, "`timeline %s` with only a copy not in use failing: exit %d" % (" ".join(mode), rc)
          + _ctx(rc, out, err))
    n = len(_timeline_mlog_rows(out, bool(mode)))
    _keep(n == 4, "`timeline %s` with only a copy not in use failing lists %d MLog rows, not the 4 the log holds"
          % (" ".join(mode), n) + _ctx(rc, out, err))
    said = lb38_statements(out + "\n" + err, which)
    _keep(not said, "`timeline %s` with only a copy not in use failing says the copy in use is affected (LB38 is for "
                    "the copy in use): %r" % (" ".join(mode), said[:2]))


# LB39 (S10; decision 20.3, V-a), written by the group-4 fixer before its fix: a failed control copy NOT in use is a
# redundancy condition. It exits 2 only in the commands that report redundancy -- `mlog --stats` and `mlog --json` --
# and nowhere else says anything of it (rc 0, no statement: the controls below and the third pass's). In `--stats` the
# FAILED verdict is the statement; in `--json`, besides the verdict field, stderr names the copy, says it failed and
# that the copy in use is NOT affected. Neither may read as LB38's "the copy in use is affected" (with M1's reader).
_LB39_NOT_AFFECTED = re.compile(r"(?i)\bnot\s+(?:\w+\s+){0,2}affected\b|\bunaffected\b")


def lb39_statements(text, failed):
    """LB39: statements (a line and the next two of its paragraph) that name the MLog control area, a failed copy (by
    index or PLCN, as `_lb38_copies_named`), its failure, the copy in use, and that the copy in use is NOT affected."""
    failed = set(failed)
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if (_LB38_AREA.search(w) and _lb38_copies_named(w) & failed and _LB38_FAIL.search(w)
                    and re.search(r"(?i)\bin[ -]use\b", w) and _LB39_NOT_AFFECTED.search(w)):
                hits.append(w)
    return hits


@pytest.mark.parametrize("which", [(1,), (0,)], ids=["older-copy-fails", "newer-copy-fails"])
def test_lb39_json_states_a_failed_copy_not_in_use_and_that_the_copy_in_use_is_not_affected(monkeypatch, tmp_path,
                                                                                           which):
    rc, out, err = inproc(monkeypatch, _ctrl_damaged(tmp_path, which), "mlog", "--json")
    j = _load_json(out)
    said = lb39_statements(err, which)
    assert rc == 2 and said, "a control copy not in use fails its fold: `mlog --json` must exit 2 (exit %s) and state " \
        "on stderr the copy, its failure and that the copy in use is not affected (LB39; statement: %s)" % (
            rc, "found" if said else "none") + _ctx(rc, out[-300:], err)
    assert _copy_verdicts(j).get(1 + which[0]) is False, "--json carries no failed verdict for the copy at PLCN 0x%x" \
        % (1 + which[0])
    wrong = lb38_statements(out + "\n" + err, which)
    assert not wrong, "a copy not in use is said to affect the copy in use (LB39: it does not): %r" % wrong[:2]


@pytest.mark.parametrize("which", [(1,), (0,)], ids=["older-copy-fails", "newer-copy-fails"])
def test_lb39_stats_reports_the_failed_copy_not_in_use_by_its_verdict(monkeypatch, tmp_path, which):
    rc, out, err = inproc(monkeypatch, _ctrl_damaged(tmp_path, which), "mlog", "--stats")
    v = MC.control_verdicts(out)
    verdict = which[0] in v and v[which[0]][1] != "verified"
    assert rc == 2 and verdict, "a control copy not in use fails its fold: `mlog --stats` must exit 2 (exit %s) with " \
        "its FAILED verdict (LB39; verdicts %r)" % (rc, v) + _ctx(rc, out, err)
    wrong = lb38_statements(out + "\n" + err, which)
    assert not wrong, "a copy not in use is said to affect the copy in use (LB39: it does not): %r" % wrong[:2]


@pytest.mark.parametrize("mode", [("-v",), ("--raw-scan",)], ids=["verbose", "raw-scan"])
@pytest.mark.parametrize("which", [(1,), (0,)], ids=["older-copy-fails", "newer-copy-fails"])
def test_lb39_control_a_failed_copy_not_in_use_leaves_verbose_and_raw_scan_at_exit_0(monkeypatch, tmp_path, mode,
                                                                                     which):
    """Not a RED (M3: the modes the third pass's controls left out). Only `--stats` and `--json` report a copy not in
    use; `-v` and `--raw-scan` exit 0 and say nothing of it -- neither LB38's statement nor LB39's."""
    rc, out, err = inproc(monkeypatch, _ctrl_damaged(tmp_path, which), "mlog", *mode)
    _keep(rc == 0, "`mlog %s` with only a copy not in use failing: exit %d" % (mode[0], rc) + _ctx(rc, out, err))
    said = lb38_statements(out + "\n" + err, which) + lb39_statements(out + "\n" + err, which)
    _keep(not said, "`mlog %s` with only a copy not in use failing states it: %r" % (mode[0], said[:2]))


@pytest.mark.parametrize("mode", [("--json",), ("--jsonl",)], ids=["json", "jsonl"])
@pytest.mark.parametrize("which", [(1,), (0,)], ids=["older-copy-fails", "newer-copy-fails"])
def test_lb39_control_a_failed_copy_not_in_use_leaves_timeline_json_at_exit_0(monkeypatch, tmp_path, mode, which):
    """Not a RED (M3). `timeline --json` / `--jsonl` with only a copy not in use failing: exit 0, the 4 MLog rows
    kept, nothing said of the copy on either stream."""
    rc, out, err = inproc(monkeypatch, _dated_ctrl_log(tmp_path, which), "timeline", "--fast", *mode)
    _keep(rc == 0, "`timeline %s` with only a copy not in use failing: exit %d" % (mode[0], rc) + _ctx(rc, out, err))
    n = len(_tl_mlog_rows(out, mode))
    _keep(n == 4, "`timeline %s` lists %d MLog rows, not the 4 the log holds" % (mode[0], n) + _ctx(rc, out, err))
    said = lb38_statements(out + "\n" + err, which) + lb39_statements(out + "\n" + err, which)
    _keep(not said, "`timeline %s` with only a copy not in use failing states it: %r" % (mode[0], said[:2]))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N411 / LB40 -- the control payload's fields read at their offsets (wave B part 1b; RED written first)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# DEEP_MLOG_CONTROL_STATIC section 1 (17134, 26100.x, Insider 29574): the payload is a byte copy of the MLog log
# handle. +0x28 is the log-instance UUID (16 bytes; copied into every record header +0x10); +0x44 is a u64 that
# MlLogAdvanceLogStart writes from its fourth argument and MlLogGetHostInfo reads back -- refs.sys passes the checkpoint
# virtual clock minus 1 (CmsDurableLog::AdvanceLogStart); +0x4C..+0xE43 are zeroed at every log-start advance. Measured
# on every corpus control area before these REDs were written (`fixes/waveB_fix_evidence/part1b/n411_summary.txt`: 240
# copies on 120 volumes): the newest copy's +0x44 = the highest checkpoint clock (+0x60) - 1 on 120/120, the older
# copy's = the newest's - 1 on 120/120, +0x28 = header +0x10 on 240/240, +0x4C..+0xE47 all zero on 240/240.
# 1.13.1 and part 1 printed "Total entries" / `TotalEntries` = le64(+0x48) (the high half of +0x44 and four bytes of
# the zeroed range: 0 on 240/240) and `PayloadUUID` = +0x50..+0x5F (inside the zeroed range: all zero on 240/240).
#
# The REDs pin properties, not the fixer's names: the u64 at +0x44 is carried whole, under a name for what it holds
# (the driver's "host info", or the clock it holds) and never one for a count of entries; the UUID shown for the
# payload is the one at +0x28; bytes where no field is known are shown raw, with their offset, never under a name.

N411_HOST = (7 << 32) | 0x63            # a u64 whose high half is not zero: a u32 read, or a read at +0x48, misses it
UUID_P = uuid.UUID("5e5e5e5e-0000-4000-8000-0000000000aa").bytes_le          # a payload UUID unlike the header's
N411_RUNS = ((0x50, UUID_B), (0xE44, b"\xef\xbe\xad\xde"))  # bytes planted where no field is known (+0x50: 1.13.1's
                                                             # "Control UUID"; +0xE44: past the driver's memset)
_HOST_NAME = re.compile(r"(?i)host|clock")
_ENTRIES_NAME = re.compile(r"(?i)entries")
_UUID_VAL = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def _payload_at(blk):
    """Where a control record's payload starts in its block: entry header (+0x54) + payload offset (eh+0x28)."""
    eh = le32(blk, 0x54)
    return eh + le32(blk, eh + 0x28)


def _n411_log(tmp_path, p28=None, host=N411_HOST, runs=()):
    """Intact records 1..0x20 (tail = log end); both control copies (sequence 51 and 50) carry `host` - slot at +0x44
    (the older copy one less, as the driver leaves them), `p28` (or the header's UUID) at +0x28 and the `runs`
    planted in the payload; each copy is re-sealed, so its own fold verifies."""
    log = SynLog(tmp_path / "n411.raw").run(1, 0x20, 1, session_start=True).control(END, END)
    for i in range(2):
        b = bytearray(log.ctrl[i])
        p = _payload_at(b)
        struct.pack_into("<Q", b, p + 0x44, host - i)
        if p28 is not None:
            b[p + 0x28:p + 0x38] = p28
        for off, data in runs:
            b[p + off:p + off + len(data)] = data
        log.ctrl[i] = MC._seal(b)
    log.write()
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs)
        c, p = MC.parse_block(blk), _payload_at(blk)
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and c["seq"] == 51 - i and le64(blk, p + 0x44) == host - i
            and bytes(blk[p + 0x28:p + 0x38]) == (p28 or UUID_A) and le32(blk, 0x78 + 0x20) == 0xE48,
            "control copy %d is not what the case needs" % i)
    return log


def _json_control(j):
    c = _ci_get(j, "Control")
    _fx(isinstance(c, dict), "mlog --json carries no Control object: %r" % (sorted(j)[:16],))
    return c


def _text_labelled(text, rx):
    """(label, value) of the `  Label:  value` lines whose label matches `rx`."""
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"(?m)^\s*([A-Za-z][^:\n]{0,40}):\s+(\S.*)$", text)
            if rx.search(m.group(1))]


def _control_uuids(c):
    return {k: v.lower() for k, v in c.items() if isinstance(v, str) and _UUID_VAL.match(v.lower())}


def _raw_entries(c):
    """(offset, hex) pairs held by any object inside Control that carries an offset-named key and a hex string."""
    out = []
    for d in _dicts(c):
        offs = [_as_int(v) for k, v in d.items() if re.search(r"(?i)off", k)]
        hexes = [v.lower() for v in d.values() if isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{2,}", v)]
        out += [(o, h) for o in offs if o is not None for h in hexes]
    return out


def test_n411_json_control_carries_the_u64_at_0x44_under_its_name_not_total_entries(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _n411_log(tmp_path), "mlog", "--json")
    c = _json_control(_load_json(out))
    entries = [k for k in c if _ENTRIES_NAME.search(k)]
    named = [k for k, v in c.items() if _HOST_NAME.search(k) and isinstance(v, int) and not isinstance(v, bool)
             and v == N411_HOST]
    assert not entries and named, "Control: keys named for entries %r (+0x48 holds no count); the u64 at +0x44 (%d) " \
        "as an integer under a name for what it holds (host info / the clock): %r; Control = %r" % (
            entries, N411_HOST, named, c)


@pytest.mark.parametrize("mode", [(), ("--stats",)], ids=["default", "stats"])
def test_n411_text_prints_the_u64_at_0x44_under_its_name_not_total_entries(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _n411_log(tmp_path), "mlog", *mode)
    ent = _text_labelled(out, _ENTRIES_NAME)
    host = [(lab, v) for lab, v in _text_labelled(out, _HOST_NAME) if _has_num(v, N411_HOST)]
    assert not ent and host, "`mlog %s`: lines labelled for entries %r; the u64 at +0x44 (%d, decimal) under a label " \
        "for what it holds (host info / the clock): %r" % (" ".join(mode), ent, N411_HOST, host) + _ctx(rc, out, err)


def test_n411_json_every_uuid_of_an_intact_control_area_is_the_logs_uuid(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _n411_log(tmp_path), "mlog", "--json")
    uu = _control_uuids(_json_control(_load_json(out)))
    _fx(uu, "Control carries no UUID at all")
    want = str(uuid.UUID(bytes_le=UUID_A))
    bad = {k: v for k, v in uu.items() if v != want}
    assert not bad, "UUIDs in Control that are not the log's (header +0x10 = payload +0x28 = %s): %r" % (want, bad)


def test_n411_json_payload_uuid_is_the_one_at_0x28(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _n411_log(tmp_path, p28=UUID_P), "mlog", "--json")
    uu = _control_uuids(_json_control(_load_json(out)))
    want = str(uuid.UUID(bytes_le=UUID_P))
    assert want in uu.values() and ZERO_UUID not in uu.values(), "the payload's UUID at +0x28 (%s, unlike the " \
        "header's) is not in Control, or a UUID read where the payload is zero is: %r" % (want, uu)


def test_n411_text_shows_a_payload_uuid_that_differs_from_the_header_uuid(monkeypatch, tmp_path):
    """The fixer's settlement of LB40 for the text view: the payload's +0x28 is read; where it differs from the record
    header's UUID (never on the corpus: 240/240 equal), the text shows it -- otherwise the one UUID line stands."""
    rc, out, err = inproc(monkeypatch, _n411_log(tmp_path, p28=UUID_P), "mlog")
    want = str(uuid.UUID(bytes_le=UUID_P))
    assert want in out.lower(), "the payload's UUID at +0x28 (%s) differs from the header's and is not shown" % want \
        + _ctx(rc, out, err)


def test_n411_json_bytes_where_no_field_is_known_are_raw_bytes_with_their_offset(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _n411_log(tmp_path, runs=N411_RUNS), "mlog", "--json")
    c = _json_control(_load_json(out))
    named = [k for k, v in c.items() if isinstance(v, str) and v.lower() == str(uuid.UUID(bytes_le=UUID_B))]
    raw = _raw_entries(c)
    missing = ["+0x%x %s" % (off, data.hex()) for off, data in N411_RUNS
               if not any(o == off and data.hex() in h for o, h in raw)]
    assert not named and not missing, "bytes planted where no field is known: shown under a name %r; not shown as " \
        "raw bytes with their offset: %r (raw entries %r)" % (named, missing, raw)


def test_n411_text_bytes_where_no_field_is_known_are_raw_bytes_with_their_offset(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _n411_log(tmp_path, runs=N411_RUNS), "mlog")
    missing = []
    for off, data in N411_RUNS:
        at = re.compile(r"(?i)(?<![0-9a-fx])0x0*%x(?![0-9a-f])" % off)
        if not any(at.search(ln) and data.hex() in re.sub(r"[\s:]", "", ln).lower() for ln in out.splitlines()):
            missing.append("+0x%x %s" % (off, data.hex()))
    assert not missing, "bytes planted where no field is known are not shown raw with their offset: %r" % missing \
        + _ctx(rc, out, err)


N411_IMAGES = ["step1/win11refsmini.raw", "step4/wininsiderrefs8gtest2.raw", "step1/win10refsmini.raw"]
_N411_IDS = ["image-win11refsmini", "image-wininsiderrefs8gtest2", "image-win10refsmini"]


def _own_control(rel, plcn):
    """This module's own read of the control copy at `plcn` and of the checkpoint clocks (the measured relation is
    the premise: +0x44 = the highest checkpoint clock - 1 on the copy in use, as on 120/120 volumes)."""
    img = MC.corpus(rel)
    ps = MC._refs_ps(img)
    cs = MC._cluster_size(img, ps)
    blk = MC.read_block(img, ps + plcn * cs)
    c, p = MC.parse_block(blk), _payload_at(blk)
    _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and le32(blk, le32(blk, 0x54) + 0x20) == 0xE48,
        "%s: no intact control record at PLCN 0x%x" % (rel, plcn))
    clocks = [le64(MC.read_block(img, ps + l * cs, 0x80), 0x60) for l in MC.chkp_lcns(img, ps, cs)]
    own = {"host": le64(blk, p + 0x44), "uuid": str(uuid.UUID(bytes_le=bytes(blk[p + 0x28:p + 0x38]))),
           "hdr_uuid": str(uuid.UUID(bytes_le=bytes(blk[0x10:0x20])))}
    _fx(own["host"] == max(clocks) - 1 and own["uuid"] == own["hdr_uuid"] and not any(blk[p + 0x4C:p + 0xE48]),
        "%s: the measured layout does not hold here (+0x44 %d, clocks %r, UUIDs %s / %s)" % (
            rel, own["host"], clocks, own["uuid"], own["hdr_uuid"]))
    return own


@pytest.mark.parametrize("rel", N411_IMAGES, ids=_N411_IDS)
def test_n411_json_control_fields_on_image(rel):
    rc, out, err = cli(rel, "mlog", "--json")
    c = _json_control(_load_json(out))
    plcn = _as_int(_ci_get(c, "PLCN"))
    _fx(plcn, "%s: Control carries no PLCN" % rel)
    own = _own_control(rel, plcn)
    named = [k for k, v in c.items() if _HOST_NAME.search(k) and isinstance(v, int) and not isinstance(v, bool)
             and v == own["host"]]
    entries = [k for k in c if _ENTRIES_NAME.search(k)]
    uu = set(_control_uuids(c).values())
    assert named and not entries and uu == {own["uuid"]}, "%s: the u64 at +0x44 (%d) under its name: %r; keys named " \
        "for entries: %r; UUIDs in Control %r, the log's (+0x28 = header +0x10) %s" % (
            rel, own["host"], named, entries, sorted(uu), own["uuid"])


@pytest.mark.parametrize("rel", N411_IMAGES, ids=_N411_IDS)
def test_n411_text_control_fields_on_image(rel):
    rc, out, err = cli(rel, "mlog", "--stats")
    m = re.search(r"(?m)^\s*Control PLCN:\s+(0x[0-9a-f]+)", out)
    _fx(m, "%s: no 'Control PLCN' line" % rel)
    own = _own_control(rel, int(m.group(1), 16))
    ent = _text_labelled(out, _ENTRIES_NAME)
    host = [(lab, v) for lab, v in _text_labelled(out, _HOST_NAME) if _has_num(v, own["host"])]
    assert not ent and host, "%s: lines labelled for entries %r; the u64 at +0x44 (%d) under its label: %r" % (
        rel, ent, own["host"], host)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N412 / LB41 -- an MLog with NO readable control copy (wave B part 1b; RED written first)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Without a control copy the log instance (format magic and UUID) is unknown, so an earlier volume's records cannot be
# left out (N137 / LB1). LB41: a view condition, as LB24 and T1 -- exit 2 in every mode of LB24's set (`mlog` in all
# modes, `--raw-scan`, `--info` (LB33) and `--earlier-logs` included, and `timeline`'s MLog source), with a statement
# that no control copy could be read and what that means for the listing, on stderr in export modes. 0 corpus
# volumes. Three ways for both copies to be unreadable: zero bytes (no signature), image holes, and a signed record
# whose own fold verifies but whose payload length is not 0xE48 (LogReadControlRecord refuses it: 26100.8115
# refs_win11.decomp.c LogReadControlRecord, `*(int *)(_Dst + lVar8 + 0x20) == 0xe48` else 0xC03D0202).

_N412_HOW = ["zeroed", "hole", "not-a-control-payload"]


def _write_without_control(log):
    """SynLog.write minus the two control clusters, which stay image holes."""
    with open(log.path, "wb") as fh:
        fh.truncate((log.de + 2) * log.cs)
        for k in range(log.NBLK):
            b = log.blocks.get(k, MC.ZERO)
            if b is None:
                continue
            fh.seek(log.block_off(k))
            fh.write(b)
    _fx(MC._holes(log.path, log.cs, 2 * log.cs) == [(log.cs, 3 * log.cs)],
        "the two control clusters are not image holes on this filesystem")
    return log


def _unreadable_control(log, how):
    """Both control copies of `log` made unreadable in the way `how` names; checked with this module's reader."""
    if how == "zeroed":
        log.ctrl = [MC.ZERO, MC.ZERO]
        log.write()
    elif how == "hole":
        _write_without_control(log)
    else:
        for i in range(2):
            b = bytearray(log.ctrl[i])
            struct.pack_into("<I", b, le32(b, 0x54) + 0x20, 0x100)
            log.ctrl[i] = MC._seal(b)
        log.write()
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs)
        if how == "not-a-control-payload":
            c = MC.parse_block(blk)
            _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and le32(blk, le32(blk, 0x54) + 0x20) == 0x100,
                "control copy %d: not the signed, sealed record with a refused payload length the case needs" % i)
        else:
            _fx(blk == MC.ZERO, "control copy %d is not all zero" % i)
    return log


def _n412_log(tmp_path, how):
    log = SynLog(tmp_path / ("noctrl_%s.raw" % how)).run(1, 0x20, 1, session_start=True).control(END, END)
    return _unreadable_control(log, how)


def _n412_dated_log(tmp_path, how, unreadable=True):
    """4 dated payloads (blocks 1..4, generation 1), as `_dated_ctrl_log`; both control copies unreadable."""
    log = SynLog(tmp_path / ("noctrl_dated_%s_%d.raw" % (how, unreadable)))
    for k in range(1, 5):
        log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_A + k)]])
    log.control(lsn(1, 5), lsn(1, 5))
    return _unreadable_control(log, how) if unreadable else log.write()


# The statement: a line and the next two of its paragraph that name the control area, say no control copy could be
# read, and say what that means for the listing -- the log instance / an earlier volume's records cannot be told, so
# none is left out (every record listed), or the earlier view shows none.
_N412_AREA = re.compile(r"(?i)\bcontrol\b")
_N412_NONE = re.compile(
    r"(?i)\bno\s+(?:mlog\s+)?control\s+(?:cop(?:y|ies)|area|records?|pages?)\b[^.;\n]{0,40}?\b(?:read|readable)\b"
    r"|\bno\s+readable\s+(?:mlog\s+)?control\b"
    r"|\b(?:neither|none\s+of\s+the)\b[^.;\n]{0,20}\bcop(?:y|ies)\b[^.;\n]{0,40}\b(?:read|readable)\b"
    r"|\b(?:both|all|every)\s+(?:\w+\s+){0,3}cop(?:y|ies)\b[^.;\n]{0,40}"
    r"\b(?:unreadable|not\s+(?:\w+\s+){0,2}readable|(?:cannot|can't|could\s+not)\s+be\s+read)\b")
_N412_INSTANCE = re.compile(r"(?i)\binstance|\bearlier\s+volume|\banother\s+volume")
_N412_LISTING = re.compile(
    r"(?i)\bevery\s+(?:\w+\s+){0,4}(?:records?|payloads?|rows?)\b|\bnot\s+(?:be\s+)?left\s+out\b"
    r"|\b(?:none|no\s+record|nothing)\b[^.;\n]{0,30}\b(?:left\s+out|shown|lists?|listed)\b"
    r"|\bcannot\s+(?:\w+\s+){0,2}(?:told|left\s+out|separated)\b")


def n412_statements(text):
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if (_N412_AREA.search(w) and _N412_NONE.search(w) and _N412_INSTANCE.search(w)
                    and _N412_LISTING.search(w)):
                hits.append(w)
    return hits


_N412_MLOG_MODES = _N144_MODES + [("--earlier-logs",)]
_N412_MLOG_IDS = _LB1_IDS + ["info", "earlier-logs"]


@pytest.mark.parametrize("mode", _N412_MLOG_MODES, ids=_N412_MLOG_IDS)
@pytest.mark.parametrize("how", _N412_HOW)
def test_n412_no_readable_control_copy_makes_every_mlog_mode_exit_2_with_a_statement(monkeypatch, tmp_path, how, mode):
    rc, out, err = inproc(monkeypatch, _n412_log(tmp_path, how), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = n412_statements(err if export else out)
    assert rc == 2 and said, "no control copy can be read (%s): `mlog %s` must exit 2 (exit %s; LB41) and state %s " \
        "that no control copy could be read and what that means for the listing (statement: %s)" % (
            how, " ".join(mode), rc, _lb38_where(export), "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--jsonl",)], ids=["text", "csv", "json", "jsonl"])
@pytest.mark.parametrize("how", _N412_HOW)
def test_n412_no_readable_control_copy_makes_timeline_exit_2_with_a_statement(monkeypatch, tmp_path, how, mode):
    rc0, out0, err0 = inproc(monkeypatch, _n412_dated_log(tmp_path, how, unreadable=False), "timeline", "--fast", *mode)
    _fx(rc0 == 0 and len(_tl_mlog_rows(out0, mode)) == 4,
        "the intact log: timeline must list its 4 MLog rows and exit 0 (the premise)" + _ctx(rc0, out0, err0))
    rc, out, err = inproc(monkeypatch, _n412_dated_log(tmp_path, how), "timeline", "--fast", *mode)
    _keep(len(_tl_mlog_rows(out, mode)) == 4, "with no control copy the MLog rows are no longer listed (the listing "
          "keeps every record: LB41 states it, it does not drop them)" + _ctx(rc, out, err))
    said = n412_statements(err if mode else out)
    assert rc == 2 and said, "no control copy can be read (%s): `timeline %s` must exit 2 (exit %s; LB41) and state " \
        "%s that no control copy could be read and what that means for the listing (statement: %s)" % (
            how, " ".join(mode), rc, _lb38_where(bool(mode)), "found" if said else "none") + _ctx(rc, out, err)


class _NoControlNamed(SynLog):
    """A log whose Logfile Information row names no control copy (both control PLCNs 0)."""

    @property
    def info(self):
        d = dict(SynLog.info.fget(self))
        d["ctrl_plcn_0"] = d["ctrl_plcn_1"] = 0
        return d


@pytest.mark.parametrize("mode", [(), ("--json",)], ids=["default", "json"])
def test_n412_no_control_copy_named_exits_2_with_a_statement(monkeypatch, tmp_path, mode):
    """The edge of LB41's condition: OID 0x9 names no control copy at all, so none can be read either."""
    log = _NoControlNamed(tmp_path / "noname.raw").run(1, 0x20, 1, session_start=True).control(END, END).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
    said = n412_statements(err if mode else out)
    assert rc == 2 and said, "OID 0x9 names no control copy: `mlog %s` must exit 2 (exit %s; LB41) and state %s that " \
        "no control copy could be read and what that means for the listing (statement: %s)" % (
            " ".join(mode), rc, _lb38_where(bool(mode)), "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("-v",), ("--parse",), ("--csv",), ("--raw-scan",), ("--info",)],
                         ids=["default", "verbose", "parse", "csv", "raw-scan", "info"])
@pytest.mark.parametrize("slot", [0, 1], ids=["copy0-unreadable", "copy1-unreadable"])
def test_n412_control_one_readable_copy_is_not_the_no_copy_condition(monkeypatch, tmp_path, slot, mode):
    """Not a RED. One copy unreadable, the other intact: the copy in use is readable, so N412 does not apply -- exit
    0 in these modes (a copy not in use failing exits 2 only in `--stats` / `--json`, LB39) and no N412 statement."""
    log = SynLog(tmp_path / "onectrl.raw").run(1, 0x20, 1, session_start=True).control(END, END)
    log.ctrl[slot] = MC.ZERO
    log.write()
    rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
    _keep(rc == 0, "`mlog %s` with one readable control copy: exit %d" % (" ".join(mode), rc) + _ctx(rc, out, err))
    said = n412_statements(out + "\n" + err)
    _keep(not said, "`mlog %s` with one readable control copy says no copy can be read: %r" % (" ".join(mode),
                                                                                            said[:2]))


@pytest.mark.parametrize("mode", [(), ("--csv",)], ids=["text", "csv"])
@pytest.mark.parametrize("slot", [0, 1], ids=["copy0-unreadable", "copy1-unreadable"])
def test_n412_control_one_readable_copy_leaves_timeline_at_exit_0(monkeypatch, tmp_path, slot, mode):
    """Not a RED. `timeline` with one readable control copy: exit 0, its 4 MLog rows, no N412 statement."""
    log = _n412_dated_log(tmp_path, "zeroed", unreadable=False)
    with open(log.path, "r+b") as fh:
        fh.seek((1 + slot) * log.cs)
        fh.write(MC.ZERO)
    rc, out, err = inproc(monkeypatch, log, "timeline", "--fast", *mode)
    _keep(rc == 0 and len(_timeline_mlog_rows(out, bool(mode))) == 4,
          "`timeline %s` with one readable control copy: exit %d" % (" ".join(mode), rc) + _ctx(rc, out, err))
    _keep(not n412_statements(out + "\n" + err), "`timeline %s` with one readable control copy states N412"
          % " ".join(mode))


def test_n411_n412_matchers_accept_a_sound_output_and_reject_others():
    """The readers of the N411 / N412 REDs: each accepts a sound form and rejects what it must refuse."""
    assert _text_labelled("  Host info:         30064771171 (the checkpoint virtual clock minus 1)", _HOST_NAME)
    assert not _text_labelled("  Total entries:     7", _HOST_NAME)
    assert _text_labelled("  Total entries:     7", _ENTRIES_NAME)
    assert not [k for k in ("EntryHeaderOffset", "PayloadOffset", "LogOpenCount") if _ENTRIES_NAME.search(k)]
    assert _raw_entries({"UndecodedBytes": [{"Offset": "0x50", "Length": 16, "Bytes": UUID_B.hex()}]}) == \
        [(0x50, UUID_B.hex())]
    assert _raw_entries({"EntryHeaderOffset": "0x78", "FormatMagic": "0x5e524606", "UUID": UUID_B_STR}) == []
    sound = ("[forefst] MLog control: no control copy can be read -- copy 0 (PLCN 0x1): it carries no MLog signature; "
             "copy 1 (PLCN 0x2): it carries no MLog signature. Without one the log instance (format magic and UUID) is "
             "unknown, so records of an earlier volume's log cannot be told from this volume's: none is left out, "
             "every record of the data area is listed.")
    part1 = ("  No control area could be read, so the log instance of the records cannot be told: every record of the "
             "data area is listed.")
    for s in (sound, part1, "  Neither control copy can be read: the log instance is unknown, so an earlier volume's "
                            "records are not left out."):
        assert n412_statements(s), s
    for s in ("  MLog control: both copies fail their integrity check -- copy 0 (PLCN 0x1, sequence 51): stored=0x1, "
              "computed=0x2; copy 1 (PLCN 0x2, sequence 50): stored=0x3, computed=0x4. The copy in use, copy 0 (the "
              "newer), is unverified: the log start, log end and data range shown come from a copy that fails its "
              "check.",
              "  Control copy 0 (PLCN 0x1): FAILED  not a readable control record\n"
              "  Control copy 1 (PLCN 0x2): FAILED  not a readable control record",
              "  16 record(s) of an earlier volume's log are left out; `mlog --earlier-logs` shows them",
              "  No control copy verifies: the log instance of the records cannot be told: every record is listed",
              "  No control copy can be read."):                                     # nothing about the listing
        assert not n412_statements(s), s


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N133 widening -- `mlog --json` and the page-verification finding; the control copies in the JSON
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n133_mlog_json_raises_the_page_verification_finding_and_exits_2(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _damaged_record_log(tmp_path), "mlog", "--json")
    j = _load_json(out)
    failed = [v for p, k, v in _walk(j) if k.lower() == "failed"]
    _keep(failed and failed[0] == 1, "--json no longer carries the failed-record count: %r" % failed)
    assert rc == 2, "an MLog record failed its verification: `mlog --json` exits 2, as `--stats` does" \
        + _ctx(rc, out[-600:], err)


def test_n133_control_mlog_stats_exits_2_on_the_same_log(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _damaged_record_log(tmp_path), "mlog", "--stats")
    _keep(rc == 2 and "torn or altered" in out, "`mlog --stats` no longer raises the finding" + _ctx(rc, out, err))


def test_n133_mlog_json_carries_each_control_copy_with_its_verdict(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, MC._intact(tmp_path).write(), "mlog", "--json")
    v = _copy_verdicts(_load_json(out))
    assert v == {1: True, 2: True}, "control-copy verdicts in --json: %r (both copies at PLCN 0x1/0x2 verify)" % v


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N218 -- _SmsRedoRecord+0x20 is a table handle
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n218_mlog_v_heads_the_record_handle_as_a_handle(monkeypatch, tmp_path):
    """N533 (1.14.0) replaced N218's reading: +0x20 is the allocator clock (E147), not a table handle. The -v table heads
    it as the clock and prints it in decimal (0x177 = 375); no column is headed OID or handle."""
    rc, out, err = inproc(monkeypatch, _handle_log(tmp_path), "mlog", "-v")
    hdr, rows = _redo_table(out)
    _fx([r for r in rows if re.search(r"(?<![0-9a-fx])375(?![0-9])", r)], "the clock 375 is not printed: %r" % rows)
    assert not re.search(r"\bOID\b", hdr), "the -v table heads the clock column 'OID': %r" % hdr
    assert not re.search(r"(?i)handle", hdr) and re.search(r"AllocClock", hdr), \
        "the -v table does not head +0x20 as the allocator clock: %r" % hdr


def test_n218_mlog_json_names_the_record_handle_a_handle(monkeypatch, tmp_path):
    """N533 (1.14.0): the --json key of +0x20 is AllocatorClock, an integer; no key names a handle or an object id."""
    rc, out, err = inproc(monkeypatch, _handle_log(tmp_path), "mlog", "--json")
    j = _load_json(out)
    recs = _data_records(j)
    _fx(recs, "mlog --json carries no redo record" + _ctx(rc, out, err))
    assert not _keys_matching(j, r"(?i)^object_?id$|handle"), "a key still names a handle or an object id: %r" \
        % _keys_matching(j, r"(?i)^object_?id$|handle")[:3]
    vals = [r.get("AllocatorClock") for r in recs]
    assert sorted(vals) == [0, 0x177], "AllocatorClock values %r; the records carry 0x177 and 0" % vals


def test_n218_mlog_parse_v_says_what_target_oid_is(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _handle_log(tmp_path), "mlog", "--parse", "-v")
    if "target_oid" in out:
        legend = [ln for ln in out.splitlines() if "target_oid" in ln and not re.search(r"target_oid=0x", ln)]
        ok = [ln for ln in legend
              if re.search(r"(?i)target_oid\s*(?:=|:|is|means|names|--|—)\s*[^\n]{0,100}\b(?:table|key)\b", ln)]
        assert ok, "no line says what target_oid is: %r" % legend
    else:
        assert re.search(r"(?i)\btable\w*\s*[=:]\s*0x", out), "the record lines name no table" + _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N259 -- locators named by their unit
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("mode", ["--json", "--raw-scan"])
def test_n259_no_vlcn_field(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, MC._intact(tmp_path).write(), "mlog", mode)
    if mode == "--json":
        assert not _keys_matching(_load_json(out), r"(?i)vlcn"), "--json keys named vlcn: %r" \
            % _keys_matching(_load_json(out), r"(?i)vlcn")[:3]
    else:
        rows = [ln for ln in _section(out, "Data Area Raw Scan") if ln.strip()]
        _fx(rows, "--raw-scan printed no row" + _ctx(rc, out, err))
        assert not [r for r in rows if re.search(r"(?i)\bVLCN\b", r)], "--raw-scan prints a VLCN column: %r" % rows[0]


K_BAD = 0x23     # 64 KiB clusters: data-area cluster 16 + 2 = 0x12, 4 KiB block 3 inside it; 4 KiB index 0x12*16+3 = 291
_LOC = re.compile(r"(?i)(?<![0-9a-fx])0x0*12(?:\.blk|[^\s0-9a-z]{1,3})0*3(?![0-9])")


def test_n259_a_failing_record_is_located_one_way_in_every_text_mode(monkeypatch, tmp_path):
    log = _damaged_record_log(tmp_path, cs=0x10000, k=K_BAD)
    locs = {}
    rc, out, err = inproc(monkeypatch, log, "mlog", "--stats")
    fl = [ln for ln in _section(out, "Record Integrity") if re.search(r"(?i)stored", ln)]
    _fx(fl, "--stats printed no failure line" + _ctx(rc, out, err))
    m = _LOC.search(" ".join(fl))
    assert m, "the --stats failure line %r does not locate the record by its PLCN 0x12 and 4 KiB block 3" % fl
    locs["--stats"] = m.group(0)
    rc, out, err = inproc(monkeypatch, log, "mlog", "-v")
    row = [ln for ln in _section(out, "LogCore Record Headers")
           if lsn(1, K_BAD) in [int(t, 16) for t in re.findall(r"0x[0-9a-fA-F]+", ln)]]
    _fx(row, "-v printed no LogCore row for 1:%x" % K_BAD)
    m = _LOC.search(row[0])
    assert m, "-v's LogCore row %r does not locate the record by PLCN 0x12 and block 3" % row[0]
    locs["-v"] = m.group(0)
    rc, out, err = inproc(monkeypatch, log, "mlog", "--raw-scan")
    ms = [m.group(0) for ln in _section(out, "Data Area Raw Scan") for m in [_LOC.search(ln)] if m]
    assert len(ms) == 1, "--raw-scan rows locating PLCN 0x12 block 3: %r" % ms
    locs["--raw-scan"] = ms[0]
    rc, out, err = inproc(monkeypatch, log, "mlog", "--parse", "-v")
    ms = [m.group(0) for m in _LOC.finditer(out)]
    assert ms, "--parse -v does not locate the record by PLCN 0x12 and block 3 (it prints the PLCN in decimal)"
    locs["--parse -v"] = ms[0]
    assert len(set(locs.values())) == 1, "one block, several forms: %r" % locs


def test_n259_json_names_no_block_index_an_lcn(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _damaged_record_log(tmp_path, cs=0x10000, k=K_BAD), "mlog", "--json")
    j = _load_json(out)
    assert not _keys_matching(j, r"(?i)block_?lcn"), "keys named block_lcn: %r" % _keys_matching(j, r"(?i)block_?lcn")[:3]
    # LB22 (critic D2 b): `BlockIndex`, the name of the bundle column, on every record; its value is the 4 KiB block's
    # index from the volume start. LB32: the value is a lower-case hex string, "0x123" -- the form of K9 and of the
    # bundle column (`0x%x`, fd:17258): one form for one information. An integer, padding or upper case is refused.
    bpc = 0x10000 // MLOG_BLK
    recs = _data_records(j)
    _fx(recs, "mlog --json carries no redo record" + _ctx(rc, out[-600:], err))
    bad = []
    for r in recs:
        pl, bl = _as_int(_ci_get(r, "plcn")), _as_int(_ci_get(r, "block"))
        _fx(pl is not None and bl is not None, "a record without its PLCN and its block: %r" % sorted(r))
        if r.get("BlockIndex") != "0x%x" % (pl * bpc + bl):
            bad.append((hex(pl), bl, r.get("BlockIndex")))
    assert not bad, "records whose BlockIndex is missing or is not the string '0x%%x' of PLCN x %d + Block " \
                    "(LB22, LB32): %r" % (bpc, bad[:3])
    assert [r for r in recs if r["BlockIndex"] == "0x%x" % (0x12 * bpc + 3)], \
        "no record at BlockIndex '0x%x' (PLCN 0x12, block 3, the failing record)" % (0x12 * bpc + 3)
    fails = [v for p, k, v in _walk(j) if k.lower() == "failures" and isinstance(v, list)]
    _fx(fails and len(fails[0]) == 1, "--json carries no failures list with the one failing record: %r" % fails)
    e = fails[0][0]
    # a positional triple names nothing (named keys or a triple is the lead's pick, WAVEB_CENSUS section 6); a named
    # entry must locate the record by PLCN and block, or name the 4 KiB index as an index
    if isinstance(e, dict):
        vals = {k.lower(): _as_int(v) for k, v in e.items()}
        by_pb = 0x12 in vals.values() and 3 in vals.values()
        by_index = [k for k, v in vals.items() if v == 291 and "index" in k]
        assert by_pb or by_index, "the failure entry %r neither gives PLCN 0x12 and block 3 nor names the 4 KiB " \
                                  "index as an index" % e


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N260 -- one mnemonic per driver handler (LB4, LB4a), opcode numbers, one unknown label
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def canonical_handlers(version):
    """{opcode: handler} of `version` ('v3.14' / 'v3.4') from the canonical dispatch tables
    (forclaude/intelligence/redo_opcode_complete.md, "Complete vX dispatch table")."""
    p = os.path.join(os.path.dirname(REPO), "forclaude", "intelligence", "redo_opcode_complete.md")
    if not os.path.isfile(p):
        pytest.skip("the canonical redo table is not in this layout")
    with open(p, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"(?m)^## Complete %s dispatch table.*$" % re.escape(version), text)
    _fx(m, "no '%s' dispatch table in redo_opcode_complete.md" % version)
    out = {}
    for ln in text[m.end():].splitlines():
        if ln.startswith("## ") or ln.startswith("---"):
            break
        r = re.match(r"^\|\s*\**0x([0-9A-Fa-f]{2})\**\s*\|\s*([^|]+?)\s*\|", ln)
        if r:
            out[int(r.group(1), 16)] = r.group(2).strip("* ").strip()
    _fx(len(out) == {"v3.14": 44, "v3.4": 29}[version], "%s table: %d rows" % (version, len(out)))
    return out


N260_OPS_V314 = [0x08, 0x09, 0x16, 0x0A, 0x29, 0x12, 0x14, 0x15, 0x1F, 0x20, 0x22, 0x25, 0x2B, 0x0D, 0x18]
N260_OPS_V34 = [0x08, 0x09, 0x12, 0x14, 0x15, 0x16, 0x17, 0x18, 0x0C, 0x0D]


def _mnemonics(monkeypatch, tmp_path, ops, mode, vmin):
    """{opcode: the mnemonic `mlog` prints} on a log of one single-record payload per opcode. In `--parse` the
    mnemonic line may gain the opcode numbers (N260's row allows them there): a `0x..` token is not the mnemonic."""
    log = build_log(tmp_path / ("ops%d.raw" % vmin), [[[redo_rec(op)]] for op in ops]).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", mode, vmin=vmin)
    if mode == "--csv":
        hdr, rows, _at = csv_table(out)
        c = _col(hdr, r"(?i)^opcodes$")
        cells = [r[c] for r in rows]
    else:
        cells = [" ".join(t for t in re.split(r"[\s;,()\[\]]+", nxt) if t and not re.fullmatch(r"0x[0-9a-fA-F]+", t))
                 for _row, nxt in _parse_rows(out)]
    _fx(len(cells) == len(ops), "%d rows for %d payloads" % (len(cells), len(ops)) + _ctx(rc, out, err))
    return dict(zip(ops, cells))


def _handler_mismatches(mn, handlers):
    bad = []
    for a, b in itertools.combinations(sorted(mn), 2):
        if (handlers[a] == handlers[b]) != (mn[a] == mn[b]):
            bad.append("0x%02x %s -> %s / 0x%02x %s -> %s" % (a, handlers[a], mn[a], b, handlers[b], mn[b]))
    return bad


@pytest.mark.parametrize("mode", ["--csv", "--parse"])
def test_n260_each_v314_handler_has_its_own_mnemonic(monkeypatch, tmp_path, mode):
    mn = _mnemonics(monkeypatch, tmp_path, N260_OPS_V314, mode, 14)
    bad = _handler_mismatches(mn, canonical_handlers("v3.14"))
    assert not bad, "mnemonic != handler (one mnemonic per handler, redo_opcode_complete.md):\n  " + "\n  ".join(bad)


@pytest.mark.parametrize("mode", ["--csv", "--parse"])
def test_n260_control_v34_mnemonics_are_one_per_handler(monkeypatch, tmp_path, mode):
    """v3.4 has no merge today (0x08/0x09 share a handler, and their mnemonic; 0x12 and 0x15 call none, E123); the fix
    must not merge any."""
    mn = _mnemonics(monkeypatch, tmp_path, N260_OPS_V34, mode, 4)
    bad = _handler_mismatches(mn, canonical_handlers("v3.4"))
    _keep(not bad, "v3.4 mnemonics no longer one per handler:\n  " + "\n  ".join(bad))


# LB29 (critic T7): every opcode's mnemonic is its FULL canonical handler name -- the handler column of
# redo_opcode_complete.md with the namespace and the `Redo` prefix dropped, CamelCase turned into UPPER_SNAKE, no
# truncation -- per dispatch table (LB15). LB4a's derived names stand for the lines whose handler name the table
# marks unconfirmed (v3.14 0x16; N554 named 0x25 and 0x2b by their handlers, E160), and 0x17 (v3.14) is the
# error branch. The strings were proposed in
# RED_waveB_group4.md section 3 and checked by the critic against the canonical table (RED_waveB_critic.md section 4);
# `_decided_mnemonics` re-derives them from the table and refuses to run if the table and these strings part.
# N461 (E123, wave C's close): 0x12 and 0x15 call no handler (the table's rows say so); 0x12 is TREE_UPDATE_RECORD
# after the event the analysis pass raises for it (TreeUpdateRecordFound), 0x15 NO_HANDLER -- the maintainer's
# option (a), 2026-10-24 (1.13.1 and the tool to ed5c4082 printed MOVE_CONTAINER, 0x14's, for both).
N260_V314 = {
    0x00: "OPEN_TABLE_FROM_TABLE_PATH", 0x01: "INSERT_ROW", 0x02: "DELETE_ROW", 0x03: "UPDATE_ROW",
    0x04: "UPDATE_DATA_WITH_ROOT", 0x05: "REPARENT_TABLE", 0x06: "ALLOCATE", 0x07: "FREE",
    0x08: "SET_RANGE_STATE", 0x09: "SET_RANGE_STATE", 0x0A: "DUPLICATE_EXTENTS", 0x0B: "MODIFY_STREAM_EXTENT",
    0x0C: "STRIP_ALL_CHECKSUMS", 0x0D: "SET_INTEGRITY_INFORMATION", 0x0E: "SET_PARENT_ID", 0x0F: "DELETE_TABLE",
    0x10: "SET_OBJECT_RECORD_PAYLOAD", 0x11: "ADD_SCHEMA", 0x12: "TREE_UPDATE_RECORD", 0x13: "ADD_CONTAINER",
    0x14: "MOVE_CONTAINER", 0x15: "NO_HANDLER", 0x16: "SET_RANGE_STATE_RANGE", 0x17: "ERROR",
    0x18: "CONTAINER_COMPACTION", 0x19: "DELETE_COMPRESSION_UNIT_OFFSETS", 0x1A: "ADD_COMPRESSION_UNIT_OFFSETS",
    0x1B: "GHOST_EXTENTS", 0x1C: "COMPACTION_UNRESERVE", 0x1D: "UNLINK_PARENT_OBJECT_ID",
    0x1E: "PREPARE_ENTRY_FOR_MERGE", 0x1F: "UPDATE_STREAM_SUMMARY", 0x20: "UPDATE_STREAM_USER_PAYLOAD",
    0x21: "STREAM_PERSIST_FAST_RUN_INSERTION", 0x22: "TABLE_SET_SUMMARY_UPDATE", 0x23: "TABLE_SET_SHADOW_TREE_UPDATE",
    0x24: "TABLE_SET_COMMIT_MERGE", 0x25: "TABLE_SET_WEAK_REF_PURGE", 0x26: "TABLE_SET_STRONG_REF_MERGE",
    0x27: "SET_DEFAULT_COMPRESSION_PARAMETERS", 0x28: "BREAK_WEAK_REFERENCES", 0x29: "DUPLICATE_CLUSTER",
    0x2A: "CHANGE_RANGE_ENCRYPTED_STATE", 0x2B: "TABLE_SET_STRONG_REF_MERGE_SINGLE"}
N260_V34 = {
    0x00: "OPEN_TABLE", 0x01: "INSERT_ROW", 0x02: "DELETE_ROW", 0x03: "UPDATE_ROW", 0x04: "UPDATE_DATA_WITH_ROOT",
    0x05: "REPARENT_TABLE", 0x06: "ALLOCATE", 0x07: "FREE", 0x08: "SET_RANGE_STATE", 0x09: "SET_RANGE_STATE",
    0x0A: "DUPLICATE_EXTENTS", 0x0B: "MODIFY_STREAM_EXTENT", 0x0C: "STRIP_METADATA_STREAM_EXTENT",
    0x0D: "SET_INTEGRITY", 0x0E: "SET_PARENT_ID", 0x0F: "DELETE_TABLE", 0x10: "SET_OBJECT_RECORD_PAYLOAD",
    0x11: "ADD_SCHEMA", 0x12: "TREE_UPDATE_RECORD", 0x13: "ADD_CONTAINER", 0x14: "MOVE_CONTAINER", 0x15: "NO_HANDLER",
    0x16: "READ_CACHE_INVALIDATION", 0x17: "GENERATE_CHECKSUM", 0x18: "CONTAINER_COMPRESSION",
    0x19: "DELETE_COMPRESSION_UNIT_OFFSETS", 0x1A: "ADD_COMPRESSION_UNIT_OFFSETS", 0x1B: "GHOST_EXTENTS",
    0x1C: "COMPACTION_UNRESERVE"}
_N260_DERIVED = {"RedoSetRangeState (range variant)": "SET_RANGE_STATE_RANGE",       # LB4a: its own dispatch line
                 "ERROR": "ERROR",                                                    # the error branch (0xC0000427)
                 # N461 / E123: the two rows whose branch calls no handler
                 "(no handler: the epilogue; a tree-update record, acted on by PreAnalyzeOneRecord)": "TREE_UPDATE_RECORD",
                 "(no handler: the epilogue)": "NO_HANDLER"}


def _rule_mnemonic(handler):
    if handler in _N260_DERIVED:
        return _N260_DERIVED[handler]
    n = handler.split("::")[-1]
    n = n[4:] if n.startswith("Redo") else n
    return "_".join(p.upper() for p in re.findall(r"[A-Z][a-z0-9]*", n))


def _decided_mnemonics(version):
    """LB29's strings for `version`, checked against the canonical table (a fixture error if they part)."""
    table = {"v3.14": N260_V314, "v3.4": N260_V34}[version]
    derived = {op: _rule_mnemonic(h) for op, h in canonical_handlers(version).items()}
    _fx(derived == table, "%s: redo_opcode_complete.md no longer gives LB29's strings: %r" % (version, {
        "0x%02x" % op: (derived.get(op), table.get(op)) for op in sorted(set(derived) | set(table))
        if derived.get(op) != table.get(op)}))
    return table


@pytest.mark.parametrize("mode", ["--csv", "--parse"])
@pytest.mark.parametrize("version", ["v3.14", "v3.4"])
def test_n260_lb29_every_opcode_prints_its_full_handler_mnemonic(monkeypatch, tmp_path, version, mode):
    want = _decided_mnemonics(version)
    ops = sorted(want)
    mn = _mnemonics(monkeypatch, tmp_path, ops, mode, {"v3.14": 14, "v3.4": 4}[version])
    bad = ["0x%02x %s (decided %s)" % (op, mn[op], want[op]) for op in ops if mn[op] != want[op]]
    assert not bad, "%s %s: %d of %d opcodes do not print their full handler mnemonic (LB29):\n  %s" % (
        version, mode, len(bad), len(ops), "\n  ".join(bad))


def _long_names(monkeypatch, tmp_path, ops, vmin):
    """({opcode: the long name `mlog --json` gives it}, `mlog -v`'s redo-table rows) on a log of one single-record
    payload per opcode."""
    log = build_log(tmp_path / ("long%d.raw" % vmin), [[[redo_rec(op)]] for op in ops]).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--json", vmin=vmin)
    names = {}
    for r in _data_records(_load_json(out)):
        nm = [v for k, v in r.items() if re.fullmatch(r"(?i)op_?name", k)]
        _fx(nm, "a --json record carries no op_name / OpName: %r" % sorted(r))
        names.setdefault(_as_int(_ci_get(r, "opcode")), set()).add(nm[0])
    _fx(set(names) == set(ops) and all(len(v) == 1 for v in names.values()),
        "--json long names per opcode: %r" % names)
    rc, vout, verr = inproc(monkeypatch, log, "mlog", "-v", vmin=vmin)
    hdr, rows = _redo_table(vout)
    _fx(len(rows) == len(ops), "-v: %d rows for %d records" % (len(rows), len(ops)))
    return {op: v.pop() for op, v in names.items()}, rows


def test_n260_lb15_each_v314_handler_has_its_own_long_name(monkeypatch, tmp_path):
    ops = sorted(canonical_handlers("v3.14"))
    names, rows = _long_names(monkeypatch, tmp_path, ops, 14)
    _keep(names[0x08] == names[0x09], "0x08 and 0x09 (one handler) no longer share their long name: %r / %r"
          % (names[0x08], names[0x09]))
    bad = _handler_mismatches(names, canonical_handlers("v3.14"))
    assert not bad, "long name != handler (one long name per handler, LB15):\n  " + "\n  ".join(bad)
    off = [(hex(op), names[op], row) for op, row in zip(ops, rows) if names[op] not in row]
    assert not off, "-v prints another long name than --json: %r" % off[:3]


def test_n260_lb15_control_v34_long_names_are_one_per_handler(monkeypatch, tmp_path):
    """Not a RED. v3.4's long names are one per handler today (0x08/0x09 share theirs; 0x12 and 0x15, which call no
    handler, have their own, E123); after the fix too, and `-v` prints the --json name."""
    ops = sorted(canonical_handlers("v3.4"))
    names, rows = _long_names(monkeypatch, tmp_path, ops, 4)
    bad = _handler_mismatches(names, canonical_handlers("v3.4"))
    _keep(not bad and all(names[op] in row for op, row in zip(ops, rows)),
          "v3.4 long names no longer one per handler, or -v and --json part:\n  " + "\n  ".join(bad))


def test_n260_mlog_csv_carries_each_records_opcode_number(monkeypatch, tmp_path):
    log = build_log(tmp_path / "log.raw", [[[redo_rec(0x1F), redo_rec(0x20)]], [[redo_rec(0x0A)], [redo_rec(0x29)]]])
    rc, out, err = inproc(monkeypatch, log.write(), "mlog", "--csv")
    hdr, rows, _at = csv_table(out)
    want = [[0x1F, 0x20], [0x0A, 0x29]]
    cols = []
    for i in range(len(hdr)):
        toks = [re.split(r"[;\s]+", r[i].strip()) if i < len(r) else [] for r in rows]
        if all(t and all(re.fullmatch(r"0x[0-9a-fA-F]+", x) for x in t) for t in toks) and \
                [[int(x, 16) for x in t] for t in toks] == want:
            cols.append(i)
    assert cols, "no CSV column holds each row's opcodes as hex in record order: %r" % hdr
    # critic D9: the list form and the padding are decided -- ';'-joined (K25 A), lower-case unpadded (K15 A, K16 A)
    exact = [";".join("0x%x" % op for op in w) for w in want]
    good = [hdr[i] for i in cols if [r[i] for r in rows] == exact]
    assert good, "the opcode-number column %r is not ';'-joined unpadded lower-case hex: %r; decided %r" % (
        [hdr[i] for i in cols], [[r[i] for r in rows] for i in cols], exact)


def test_n260_one_label_for_an_unknown_opcode_in_every_mode(monkeypatch, tmp_path):
    log = build_log(tmp_path / "log.raw", [[[redo_rec(0x3C)]]]).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--csv")
    hdr, rows, _at = csv_table(out)
    label = rows[0][_col(hdr, r"(?i)^opcodes$")]
    assert re.search(r"(?i)unknown", label), "the CSV labels opcode 0x3c %r: the label must say it is unknown" % label
    pat = re.compile(r"(?<![\w])%s(?![\w])" % re.escape(label))
    for mode in (("-v",), ("--stats",), ("--parse", "-v")):
        rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
        assert pat.search(out), "`mlog %s` does not label opcode 0x3c %r" % (" ".join(mode), label) + _ctx(rc, out, err)
    rc, out, err = inproc(monkeypatch, log, "mlog", "--json")
    names = [v for r in _data_records(_load_json(out)) for v in r.values() if isinstance(v, str)]
    assert label in names, "`mlog --json` labels opcode 0x3c %r, not %r" % (names, label)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N310 -- `mlog --json` carries the CSV's transactions
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _norm(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return ";".join(_norm(x) for x in v)
    return str(v)


def test_n310_mlog_json_carries_the_csv_transactions_with_the_same_values(monkeypatch, tmp_path):
    log = _txn_log(tmp_path)
    rc, out, err = inproc(monkeypatch, log, "mlog", "--csv")
    hdr, rows, _at = csv_table(out)
    rc, out, err = inproc(monkeypatch, log, "mlog", "--json")
    j = _load_json(out)
    lists = []
    for p, k, v in _walk(j):
        if isinstance(v, list) and len(v) == len(rows) and all(isinstance(d, dict) for d in v) and \
                all({h.lower() for h in hdr} <= {x.lower() for x in d} for d in v):
            lists.append(v)
    assert lists, "no list of %d objects in --json carries the CSV's fields %r" % (len(rows), hdr)
    bad = []
    for i, (d, row) in enumerate(zip(lists[0], rows)):
        dl = {x.lower(): y for x, y in d.items()}
        for h, cell in zip(hdr, row):
            if _norm(dl[h.lower()]) != cell:
                bad.append((i, h, dl[h.lower()], cell))
    assert not bad, "JSON value != CSV value: %r" % bad[:6]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N311 -- one location, one form
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n311_csv_rows_carry_the_4k_block_within_their_cluster(monkeypatch, tmp_path):
    log = SynLog(tmp_path / "log.raw", 0x10000).run(1, 0x30, 1, session_start=True)
    log.control(lsn(1, 0x31), lsn(1, 0x31)).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--csv")
    hdr, rows, _at = csv_table(out)
    ks = list(range(1, 0x31))
    pc = _col(hdr, r"(?i)^plcn$")
    _keep([_as_int(r[pc]) for r in rows] == [log.cluster_of(k) for k in ks], "the PLCN column changed its values")
    cols = [hdr[i] for i in range(len(hdr)) if i != pc and not re.search(r"(?i)seq|count", hdr[i])
            and [_as_int(r[i]) for r in rows] == [k % 16 for k in ks]]
    assert cols, "no CSV column gives the 4 KiB block within the cluster (0..15): %r" % hdr


@pytest.mark.parametrize("mode", ["--csv", "--parse-v"])
def test_n311_plcn_is_lowercase_hex_in_csv_and_parse_v(monkeypatch, tmp_path, mode):
    log = MC._intact(tmp_path).write()
    want = ["0x%x" % log.cluster_of(k) for k in range(1, 0x21)]
    if mode == "--csv":
        rc, out, err = inproc(monkeypatch, log, "mlog", "--csv")
        hdr, rows, _at = csv_table(out)
        got = [r[_col(hdr, r"(?i)^plcn$")] for r in rows]
    else:
        rc, out, err = inproc(monkeypatch, log, "mlog", "--parse", "-v")
        got = [m.group(1) for m in _PLCN_V.finditer(out)]
    assert got == want, "PLCNs printed %r; K9: %r" % (got[:4], want[:4])


def test_n311_one_offset_base_for_a_record_in_json_and_parse_v(monkeypatch, tmp_path):
    log = build_log(tmp_path / "log.raw", [[[redo_rec(0x04)]]]).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--parse", "-v")
    _keep(re.search(r"\.blk0\+0xb8\b", out), "--parse -v no longer gives the block-relative offset +0xb8" + _ctx(rc, out))
    rc, out, err = inproc(monkeypatch, log, "mlog", "--json")
    recs = _data_records(_load_json(out))       # the one record; N310 may list it twice (top level, and nested)
    _fx(recs and all(_as_int(_ci_get(r, "opcode")) == 0x04 for r in recs), "--json: no record of the log's one record")
    for r in recs:
        offs = {k: _as_int(v) for k, v in r.items() if re.search(r"(?i)off", k)}
        assert 0xB8 in offs.values() and 8 not in offs.values(), "the record's offsets in --json: %r; the " \
                                                                 "block-relative offset is 0xb8 (--parse -v)" % offs


def test_n311_csv_rows_have_a_unique_location_on_image_wininsiderrefs8gtest2():
    rc, out, err = cli("step4/wininsiderrefs8gtest2.raw", "mlog", "--csv")
    hdr, rows, _at = csv_table(out)
    pc = _col(hdr, r"(?i)^plcn$")
    plcns = [r[pc] for r in rows]
    _fx(len(rows) > 1000 and max(Counter(plcns).values()) > 1, "the 64K image's CSV does not repeat a PLCN: "
                                                              "the case shows nothing")
    cols = []
    for i, h in enumerate(hdr):
        if i == pc or re.search(r"(?i)seq|count|time", h):
            continue
        v = [_as_int(r[i]) if i < len(r) else None for r in rows]
        if all(x is not None and 0 <= x < 16 for x in v) and len(set(zip(plcns, v))) == len(rows):
            cols.append(h)
    assert cols, "no CSV column makes (PLCN, block) unique over the %d rows: %r" % (len(rows), hdr)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# I3 / C57 -- payloads are not transactions; MOVE rows whose parents cannot be told apart
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_i3_parse_labels_the_payload_count_and_prints_the_transaction_starts(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", "--parse")
    assert not re.search(r"(?im)^\s*total transactions\s*:\s*%d\s*$" % P_TXN, out), \
        "the %d log payloads are labelled 'Total transactions'" % P_TXN
    assert [ln for ln in out.splitlines() if re.search(r"(?i)payload|log record", ln) and _has_num(ln, P_TXN)], \
        "no line gives the %d log payloads as payloads (log records)" % P_TXN + _ctx(rc, out[:1500])
    assert [ln for ln in out.splitlines() if re.search(r"(?i)transaction", ln) and _has_num(ln, S_TXN)], \
        "the %d transaction starts are not printed" % S_TXN


@pytest.mark.parametrize("site", ["parse-footer", "csv-file-line"])
def test_c57_a_payload_count_is_not_called_a_transaction_count(monkeypatch, tmp_path, site):
    log = _txn_log(tmp_path)
    if site == "parse-footer":
        rc, out, err = inproc(monkeypatch, log, "mlog", "--parse")
        _keep(re.search(r"(?i)\d+ of \d+[^\n]*\btime", out), "the footer ('N of M ... carry an embedded timestamp') "
                                                              "is gone" + _ctx(rc, out[-800:]))
    else:
        dest = str(tmp_path / "t.csv")
        rc, out, err = inproc(monkeypatch, log, "mlog", "--csv", dest)
        _keep([ln for ln in (out + err).splitlines() if re.search(r"(?i)wrote", ln) and dest in ln],
              "the FILE confirmation is gone" + _ctx(rc, out, err))
    hits = [ln for ln in (out + "\n" + err).splitlines()
            if re.search(r"(?<![\d,])%d\s+transactions?\b" % P_TXN, ln)]
    assert not hits, "the %d log payloads are counted as transactions: %r" % (P_TXN, hits)


_I3_MOVE_UNDETERMINED_1_13_1 = 133     # PLAN_1.13.2 I3 (the published sample) and WAVEB_CENSUS 2.9 (the key): 61 of 313;
# wave C step C1, N431 (Q13: both parent sets, never a pick): every MOVE whose name rows name more than one directory on
# a side -- I3's 61 + 38 overlapping sets whose lowest OIDs differ + 34 disjoint sets of several (RED_C1 N-2) = 133.
# Group 1 (1.14.0, decision 53): the 99 overlapping ones and 30 RENAME rows are MOVE_OR_RENAME (129); 34 MOVE stay
# Group 1b (1.14.0, decision 55): every move and rename of the sample is read from the file's own records -- none is left
# undetermined, and no line may say otherwise (the statement itself: test_1132_g1b_mlog r14)
MOVE_UNDETERMINED, MOVE_OR_RENAME_UNDETERMINED = 0, 0


def test_i3_a_move_whose_parents_cannot_be_told_apart_is_stated_on_image_win11refstestmftecmd():
    rc, out, err = cli("step5/win11refstestmftecmd.raw", "mlog", "--parse")
    moves = [ln for ln in out.splitlines() if re.match(r"^\s+\[MOVE(?:_AND_RENAME)?\s*\]", ln)]
    _fx(len(moves) >= 200, "%d MOVE / MOVE_AND_RENAME rows: not the sample's 295" % len(moves))
    same = [ln for ln in out.splitlines()
            for m in [re.search(r"(0x[0-9a-fA-F]+)\s*(?:→|->)\s*(0x[0-9a-fA-F]+)", ln)]
            if m and re.search(r"(?i)parent", ln) and int(m.group(1), 16) == int(m.group(2), 16)]
    assert not same, "%d rows print a move from a directory into itself, e.g. %r" % (len(same), same[0])
    if not (MOVE_UNDETERMINED or MOVE_OR_RENAME_UNDETERMINED):
        told = [ln for ln in (out + "\n" + err).splitlines() if "cannot be told apart" in ln]
        assert not told, "the sample has no undetermined move, yet a line says so: %r" % told[:2]
        return
    stated = [ln for ln in (out + "\n" + err).splitlines()
              if re.search(r"(?i)parent", ln) and _has_num(ln, MOVE_UNDETERMINED)
              and _has_num(ln, MOVE_OR_RENAME_UNDETERMINED) and "MOVE_OR_RENAME" in ln]
    assert stated, "no line gives the %d MOVE and %d MOVE_OR_RENAME rows whose parents could not be told apart" % (
        MOVE_UNDETERMINED, MOVE_OR_RENAME_UNDETERMINED)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N189 / I1 -- what an MLog row's time is; the timeline header, its undated count, its caveat
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n189_parse_states_that_a_row_time_is_its_payloads_latest_time(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", "--parse")
    _keep("2026-05-16T17:01:02.123" in out, "the row no longer shows the payload's latest time" + _ctx(rc, out[:1500]))
    assert _states_latest_payload_time(out), "no line says the time shown is the latest embedded time of the log " \
                                             "payload (its merged transactions may carry others)"


def test_i1_n189_timeline_caveat_states_what_an_mlog_row_time_is(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "timeline", "--fast")
    _keep(re.search(r"(?m)\sMLog\s", out), "no MLog row in the timeline" + _ctx(rc, out, err))
    assert not re.search(r"(?i)embedded \$SI birth", out), "the caveat still says 'embedded $SI birth'"
    assert _states_latest_payload_time(out), "the caveat does not say the time is the payload's latest embedded time"


def test_i1_timeline_header_claims_no_name_or_path_correlation(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "timeline", "--fast")
    _keep(re.search(r"(?m)\sMLog\s", out), "no MLog row in the timeline" + _ctx(rc, out, err))
    assert not re.search(r"(?i)correlated by name", out), "the header claims a name/path correlation"
    # critic D11: I1's acceptance is "the header states what is actually joined" -- deleting the header passes no more
    assert _says_sorted_not_joined(out), "no header line says the rows are sorted by time and not joined across " \
                                         "sources" + _ctx(rc, out[:1500])


@pytest.mark.parametrize("mode", [(), ("--csv",)], ids=["text", "csv"])
def test_i1_timeline_states_how_many_undated_mlog_records_it_left_out(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "timeline", "--fast", *mode)
    where = err if mode else out + "\n" + err
    hits = [ln for ln in where.splitlines() if re.search(r"(?i)\bmlog\b", ln) and re.search(r"(?i)time|date", ln)
            and _has_num(ln, P_TXN - 1) and _UNIT_ROWS.search(ln)]
    assert hits, "no statement%s gives the 3 undated MLog rows left out, named as rows (LB28)" \
        % (" on stderr" if mode else "") + _ctx(rc, out, err)
    other = [ln for ln in where.splitlines() if re.search(r"(?i)\bmlog\b", ln) and re.search(r"(?i)time|date", ln)
             and _has_num(ln, 2 * (P_TXN - 1)) and re.search(r"(?i)transaction", ln) and not _has_num(ln, P_TXN - 1)]
    assert not other, "the undated count is given in transactions (6), not rows (3; LB28): %r" % other
    if mode:
        first = next((ln for ln in out.splitlines() if ln.strip()), "")
        assert "source" in first.lower(), "stdout carries the export only (the CSV header first): %r" % first


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N173 -- the A2 framing instrument, the tool's own twin, and the refuted figures
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _framing_red_path():
    p = os.path.join(os.path.dirname(REPO), "analysis", "verification", "phase0", "A2_mlog_framing", "framing_red.py")
    if not os.path.isfile(p):
        pytest.skip("the A2 framing instrument is not in this layout")
    return p


def _framing_red():
    p = _framing_red_path()
    spec = importlib.util.spec_from_file_location("_waveb_framing_red", p)
    mod = importlib.util.module_from_spec(spec)
    saved, saved_bc = list(sys.path), sys.dont_write_bytecode
    sys.dont_write_bytecode = True                       # critic D14: no __pycache__ in the real analysis tree
    try:
        spec.loader.exec_module(mod)                     # it puts its own forefstdev path first; undone below
    finally:
        sys.path[:] = saved
        sys.dont_write_bytecode = saved_bc
    _fx(getattr(mod, "F", None) is F, "the instrument did not import the forefst module under test")
    return mod


def _sys_path_literals(src):
    """(line, value) of every absolute-path string the source puts on sys.path: a literal argument of a
    `sys.path.insert/append/extend` call or a `sys.path[...] =` assignment, or a module-level name bound to one."""
    tree = ast.parse(src)
    bound = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    bound[t.id] = n.value.value

    def on_sys_path(node):
        return (isinstance(node, ast.Attribute) and node.attr == "path" and isinstance(node.value, ast.Name)
                and node.value.id == "sys")

    hits = []
    for n in ast.walk(tree):
        args = []
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("insert", "append",
                                                                                             "extend"):
            if on_sys_path(n.func.value):
                args = n.args
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Subscript) and on_sys_path(t.value)
                                               for t in n.targets):
            args = [n.value]
        for a in args:
            for x in ast.walk(a):
                v = x.value if isinstance(x, ast.Constant) else bound.get(x.id) if isinstance(x, ast.Name) else None
                if isinstance(v, str) and os.path.isabs(v):
                    hits.append((x.lineno, v))
    return hits


def test_n173_lb13_the_instrument_hard_codes_no_tree_on_sys_path():
    with open(_framing_red_path(), encoding="utf-8") as fh:
        hits = _sys_path_literals(fh.read())
    assert not hits, "absolute paths the instrument puts on sys.path: %r" % hits


def _n173_log(tmp_path, uncommitted=None):
    """3 committed data records (blocks 1..3); the two control copies carry write sequences 275/274, which the
    instrument parses as a redo block's total_size (N173's witness); block `uncommitted` gets a record whose commit
    bit is clear."""
    log = SynLog(tmp_path / "log.raw").run(1, 3, 1, session_start=True)
    end = lsn(1, 4)
    log.ctrl = [MC.control_block(MAGIC_A, UUID_A, s, log.DS, log.de, end, end, 3) for s in (275, 274)]
    if uncommitted:
        k = uncommitted
        log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1), [[redo_rec(0x04, flags=1)]])
    return log.write()


def _instrument(monkeypatch, log):
    mod = _framing_red()
    monkeypatch.setattr(F, "bootstrap", lambda *a, **k: (open(log.path, "rb"), 0, log.cs, MC._IdentityTr(), [], {},
                                                         3, 14, []))
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            stats = mod.main(log.path)
    except Exception:
        raise RedFixtureError("the instrument crashed:\n" + traceback.format_exc())
    _fx(isinstance(stats, dict) and {"payloads", "blocks", "recs_driver", "last_commit"} <= set(stats),
        "the instrument returns %r: adapt the reader" % (stats,))
    return stats, out.getvalue()


def test_n173_the_instrument_counts_no_control_page(monkeypatch, tmp_path):
    stats, text = _instrument(monkeypatch, _n173_log(tmp_path))
    got = (stats["payloads"], stats["blocks"], stats["recs_driver"])
    assert got == (3, 3, 3), "payloads / blocks / records %r; the log holds 3 data records\n%s" % (got, text)


def test_n173_the_instrument_names_a_block_whose_last_record_has_no_commit_flag(monkeypatch, tmp_path):
    log = _n173_log(tmp_path, uncommitted=2)
    stats, text = _instrument(monkeypatch, log)
    off, plcn = log.block_off(2), log.cluster_of(2)
    _fx(stats["last_commit"] == 2, "the planted uncommitted block is not what the instrument counts: %r" % stats)
    assert re.search(r"(?i)(?<![0-9a-fx])(?:0x0*%x|%d)(?![0-9a-f])|plcn\s*0x0*%x\b" % (off, off, plcn), text), \
        "the instrument does not name the block at 0x%x (PLCN 0x%x) whose last record lacks the commit flag:\n%s" \
        % (off, plcn, text)


def test_n173_control_the_instrument_counts_every_data_record_and_its_commit(monkeypatch, tmp_path):
    stats, text = _instrument(monkeypatch, _n173_log(tmp_path))
    _keep(stats["last_commit"] == 3 and stats["recs_driver"] >= 3, "the instrument lost a data record: %r" % stats)


@pytest.mark.parametrize("mode", [(), ("--json",), ("--parse", "-v")], ids=["default", "json", "parse-v"])
def test_n173_the_tool_counts_no_control_record_in_the_data_area_as_redo(monkeypatch, tmp_path, mode):
    log = MC._intact(tmp_path)
    log.blocks[0x30] = MC.control_block(MAGIC_A, UUID_A, 275, log.DS, log.de, END, END, 3)
    log.write()
    ctl_plcn = log.cluster_of(0x30)
    rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
    if not mode:
        tot = redo_records(out)
        assert tot == 0x20, "Total records %r; the data area holds 32 data records and one control record" % tot
    elif mode == ("--json",):
        assert ctl_plcn not in _data_plcns(_load_json(out), log.DS, log.de), \
            "--json lists a redo record at the control record's PLCN 0x%x" % ctl_plcn
    else:
        assert ctl_plcn not in _parse_v_plcns(out), "--parse -v lists a record at the control record's PLCN 0x%x" \
                                                    % ctl_plcn


_N173_REFUTED = ("75,695", "364/364", "2 of 11,868", "128,216", "362 of 364")


def test_n173_the_refuted_framing_figures_are_gone_from_forefst():
    with open(F.__file__, encoding="utf-8") as fh:
        src = fh.read().splitlines()
    hits = ["fd:%d %s" % (i + 1, ln.strip()[:100]) for i, ln in enumerate(src) if any(s in ln for s in _N173_REFUTED)]
    assert not hits, "refuted figures in forefst.py:\n  " + "\n  ".join(hits)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N170, B part -- docstrings that misstate the code
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_n170_the_fold_docstring_states_what_was_verified_and_its_blind_spot():
    doc = F.mlog_verify_record.__doc__ or ""
    _keep("LogChecksumBlock" in doc, "the docstring no longer documents the fold")
    assert "95 control pages" not in doc, "the docstring still cites '95 control pages' verified on 4K and 64K"
    assert not re.search(r"(?i)in its own lane", doc), "the blind spot is limited to lane-keeping reorderings"
    assert re.search(r"(?i)\b(?:any|every)\b[^.]{0,80}\b(?:reorder\w*|permut\w*)", doc), \
        "the docstring does not say the fold is blind to any reordering of 8-byte words"


def test_n170_the_usn_parser_docstring_and_comment_match_the_code():
    src = inspect.getsource(F.parse_usn_records)
    _keep(re.search(r"nonv3\[major\]", src), "the code no longer refuses V2/V4 records")
    assert "decoded with V3 offsets" not in src, "the comment says V2/V4 records are decoded with V3 offsets"
    stale = [s for s in ("9,371 of 9,378", "33,379 of 33,381", "one genuine") if s in src]
    assert not stale, "the docstring's outlier figures: %r" % stale


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# C6 under decision 33 / LB3 -- the JSON control area
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def test_c6_json_control_is_logstart_logend_logopencount_with_no_retired_key(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, MC._c6_log(tmp_path), "mlog", "--json")
    ctrl = _ci_get(_load_json(out), "control")
    _fx(isinstance(ctrl, dict) and _ci_get(ctrl, "sequence") == 51, "no control object: %r" % ctrl)
    got = (ctrl.get("LogStart"), ctrl.get("LogEnd"), ctrl.get("LogOpenCount"))
    want = ("0x%016x" % MC.C6_START, "0x%016x" % MC.C6_END, MC.C6_OPENS)
    assert got == want, "LogStart / LogEnd / LogOpenCount %r; decided %r" % (got, want)
    retired = [k for k in ctrl if re.sub(r"[_\s]", "", k).lower() in ("lsnoldest", "generation", "writecounter")]
    assert not retired, "retired control keys still present: %r" % retired


def test_c6_n143_json_names_the_control_page_header_0x20_no_sequence(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, MC._c6_log(tmp_path), "mlog", "--json")
    ctrl = _ci_get(_load_json(out), "control")
    _fx(isinstance(ctrl, dict) and _ci_get(ctrl, "sequence") == 51, "no control object: %r" % ctrl)
    bad = sorted(k for k, v in ctrl.items() if re.search(r"(?i)seq", k) and v == MC.C6_OPENS)
    assert not bad, "the page header's open count (%d) is named a sequence: %r" % (MC.C6_OPENS, bad)


@pytest.mark.parametrize("mode", ["text", "json"])
def test_c6_the_control_data_range_is_not_called_clusters_on_a_64k_volume(monkeypatch, tmp_path, mode):
    log = SynLog(tmp_path / "log.raw", 0x10000).run(1, 0x20, 1, session_start=True)
    bpc = 0x10000 // MLOG_BLK
    log.ctrl = [MC.control_block(MAGIC_A, UUID_A, s, log.DS * bpc, log.de * bpc, END, END, 3) for s in (51, 50)]
    log.write()                                          # the payload range in 4 KiB blocks, as the 64K images hold it
    n_cl, n_blk = log.de - log.DS, (log.de - log.DS) * bpc
    if mode == "text":
        rc, out, err = inproc(monkeypatch, log, "mlog")
        line = " ".join(v for v in MC.labelled(out, "Data area") if "0x" in v)      # not the "Data Area Summary" title
        _fx(line, "no 'Data area' line" + _ctx(rc, out, err))
        assert not re.search(r"\b%d clusters\b" % n_blk, line) and (
            re.search(r"\b%d clusters\b" % n_cl, line) or re.search(r"(?i)\b%d\b[^\n]*\bblocks?\b" % n_blk, line)), \
            "the data area is %d clusters (%d 4 KiB blocks): %r" % (n_cl, n_blk, line)
    else:
        rc, out, err = inproc(monkeypatch, log, "mlog", "--json")
        ctrl = _ci_get(_load_json(out), "control") or {}
        vals = {log.DS * bpc, log.de * bpc}
        bad = sorted(k for k, v in ctrl.items() if re.search(r"(?i)lcn", k) and _as_int(v) in vals)
        assert not bad, "4 KiB-block values named as LCNs: %r" % bad
        # critic D8 (c): removing the two values must not pass -- they stay, under keys that name their unit (blocks)
        named = {_as_int(v) for k, v in ctrl.items() if re.search(r"(?i)block", k) and _as_int(v) in vals}
        assert named == vals, "the control payload's data range 0x%x - 0x%x (4 KiB blocks) is not in --json under " \
                              "keys that name blocks: %r" % (log.DS * bpc, log.de * bpc, sorted(ctrl))


class _NoOid9RangeLog(SynLog):
    """A log whose OID 9 row gives no data range (start = end = 0), so `scan_mlog_data_area` falls back to the
    control payload's +0x08/+0x10 (fd:4589-4594)."""

    @property
    def info(self):
        d = SynLog.info.fget(self)
        d.update(data_start_lcn=0, data_end_lcn=0, data_size_clusters=0)
        return d


def _fallback_log(tmp_path, cs):
    log = _NoOid9RangeLog(tmp_path / ("fallback_%x.raw" % cs), cs).run(1, 0x20, 1, session_start=True)
    bpc = cs // MLOG_BLK
    log.ctrl = [MC.control_block(MAGIC_A, UUID_A, s, log.DS * bpc, log.de * bpc, END, END, 3) for s in (51, 50)]
    return log.write()                                   # the control range in 4 KiB blocks (= clusters on 4K)


@pytest.mark.parametrize("mode", [(), ("--json",)], ids=["default", "json"])
def test_n410_the_scan_fallback_reads_the_control_range_in_its_unit(monkeypatch, tmp_path, mode):
    log = _fallback_log(tmp_path, 0x10000)
    rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
    want = {log.cluster_of(k) for k in range(1, 0x21)}
    if not mode:
        tot = redo_records(out)
        assert tot == 0x20, "Total records %r (None: 'No redo records found'): the data area, found through the " \
                            "control range, holds 32" % tot + _ctx(rc, out[-1500:], err)
    else:
        got = set(_data_plcns(_load_json(out), log.DS, log.de))
        assert got == want, "--json records at PLCNs %r; the 32 records are at %r" % (sorted(got), sorted(want))


@pytest.mark.parametrize("mode", [(), ("--json",)], ids=["default", "json"])
def test_n410_control_the_scan_fallback_finds_every_record_on_a_4k_volume(monkeypatch, tmp_path, mode):
    """Not a RED. On 4K a 4 KiB block is a cluster: the fallback finds all 32 records today, and must after the fix."""
    log = _fallback_log(tmp_path, 0x1000)
    rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
    if not mode:
        _keep(redo_records(out) == 0x20, "4K fallback: Total records" + _ctx(rc, out[-1500:], err))
    else:
        got = set(_data_plcns(_load_json(out), log.DS, log.de))
        _keep(got == {log.cluster_of(k) for k in range(1, 0x21)}, "4K fallback: --json PLCNs %r" % sorted(got))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# LB3 -- mlog's forms, one node per form kind (decisions 35 and 38; WAVEB_CENSUS 2.13)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@pytest.mark.parametrize("mode", ["--csv", "--json"])
def test_lb3_mlog_field_names_are_pascalcase(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", mode)
    if mode == "--csv":
        names = csv_table(out)[0]
    else:
        names = []
        for p, k, v in _walk(_load_json(out)):
            if not re.search(r"(?i)page_?types?$", p):          # a map keyed by page-type NAMES (data, not fields)
                names.append(k)
    bad = sorted({n for n in names if not _PASCAL.match(n)})
    assert not bad, "field names not in PascalCase: %r" % bad[:12]
    mixed = sorted({n for n in names if _MIXED_ACRONYM.search(n)})
    assert not mixed, "acronyms not in upper case (LB26: PLCN, OID, UUID, ...): %r" % mixed[:12]
    respelt = sorted({n for n in names if _PRODUCT_CASE.search(n)})
    assert not respelt, "product names not in their own spelling (LB31: ReFS, MLog): %r" % respelt[:12]


_HEXKEY = re.compile(r"(?i)plcn|lcn|magic|flags|offset|oid|handle|blockindex")      # LB32: BlockIndex too
_NOT_HEX = re.compile(r"(?i)size|len|count|clusters|truncated|txn")


def _names_fields(o):
    """(dict, 'Flags') of each redo record's flag word written as names + FlagsHex (K14 A: the review's S3)."""
    if isinstance(o, dict):
        if isinstance(o.get("FlagsHex"), str):      # the redo record's flag word (Opcodes / OpcodesHex are lists)
            yield o, "Flags"
        for v in o.values():
            yield from _names_fields(v)
    elif isinstance(o, list):
        for v in o:
            yield from _names_fields(v)


def test_lb3_mlog_json_identifiers_lcns_offsets_and_flags_are_lowercase_hex_strings(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", "--json")
    doc = _load_json(out)
    # acceptance 1.14.0 E2 close (review S3, K14 A): a redo record's Flags is the names of the word, FlagsHex the word
    # in hex -- the hex rule holds for FlagsHex; Flags must be the names of that word in the tool's table
    named = list(_names_fields(doc))
    assert named and all(d[k] == (F.flag_names(int(d[k + "Hex"], 16), F._REDO_FLAGS) or "0x0") for d, k in named), \
        [(k, d[k], d[k + "Hex"]) for d, k in named[:5]]
    names_keys = {k for d, k in named}
    bad = []
    for p, k, v in _walk(doc):
        if k in names_keys and isinstance(v, str) and not v.startswith("0x"):
            continue                                     # a names field (checked above)
        if (_HEXKEY.search(k) or k.lower() == "opcode") and not _NOT_HEX.search(k):
            for x in (v if isinstance(v, list) else [v]):
                if x is not None and not (isinstance(x, str) and re.fullmatch(r"0x[0-9a-f]+", x)):
                    bad.append("%s/%s=%r" % (p, k, x))
    assert not bad, "not a lower-case 0x string: %r" % bad[:10]


def test_lb3_mlog_text_identifiers_are_not_zero_padded(monkeypatch, tmp_path):
    log = MC._intact(tmp_path).write()                   # opcode 0x04 records in clusters 0x11..0x30
    ident = {0x4} | {log.cluster_of(k) for k in range(1, 0x21)}
    bad = []
    for mode in (("-v", "--stats"), ("--raw-scan",)):
        rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
        bad += sorted({t for t in re.findall(r"0x[0-9a-fA-F]+", out) if int(t, 16) in ident and t != "0x%x" % int(t, 16)})
    assert not bad, "zero-padded identifiers: %r" % bad[:10]


def test_lb3_mlog_hex_digits_are_lower_case(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, MC._intact(tmp_path).write(), "mlog", "--info")
    _keep("0x" in out, "mlog --info printed no hex value" + _ctx(rc, out, err))
    up = sorted(set(re.findall(r"\b0x[0-9a-fA-F]*[A-F][0-9a-fA-F]*\b", out)))
    assert not up, "upper-case hex digits: %r" % up[:10]


def test_lb3_n259_text_lsns_are_the_full_u64_in_hex(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, MC._c6_log(tmp_path), "mlog", "-v")
    for label, v in (("Log start", MC.C6_START), ("Log end", MC.C6_END)):
        want = "0x%016x (generation %d, offset 0x%x)" % (v, v >> 32, v & 0xFFFFFFFF)
        assert [x for x in MC.labelled(out, label) if want in x], "no '%s: %s' line" % (label, want) + _ctx(rc, out[:2000])
    short = sorted({t for t in re.findall(r"0x[0-9a-f]+", out) if int(t, 16) >> 32 and len(t) != 18})
    assert not short, "LSN-sized values not printed as the full u64: %r" % short[:6]


def test_lb3_n259_json_lsns_are_the_full_u64_hex_string(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, MC._c6_log(tmp_path), "mlog", "--json")
    sc = list(_scalars(_load_json(out)))
    for v in (MC.C6_START, MC.C6_END):
        assert "0x%016x" % v in sc, "the LSN 0x%016x is not in --json as that string" % v
    assert not [x for x in sc if isinstance(x, int) and not isinstance(x, bool) and x in (MC.C6_START, MC.C6_END)], \
        "an LSN is still an integer"
    assert not [x for x in sc if isinstance(x, str) and "generation" in x.lower()], "the text aid leaked into JSON"


@pytest.mark.parametrize("mode", ["--csv", "--parse", "--json"])
def test_lb3_mlog_date_times_carry_all_seven_digits(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", mode)
    if mode == "--csv":
        hdr, rows, _at = csv_table(out)
        got = rows[0][_col(hdr, r"(?i)^timestamp$")]
        assert got == FT_B_ISO, "row 1's time %r; decided %r" % (got, FT_B_ISO)
    elif mode == "--parse":
        assert FT_B_ISO in out, "the --parse row does not print %r" % FT_B_ISO
    else:
        assert FT_B_ISO in list(_scalars(_load_json(out))), "--json does not carry %r" % FT_B_ISO


@pytest.mark.parametrize("mode,vmin", [((), 14), ((), 10), (("--json",), 14)], ids=["text-3.14", "note-3.10", "json"])
def test_lb3_mlog_version_label(monkeypatch, tmp_path, mode, vmin):
    rc, out, err = inproc(monkeypatch, MC._intact(tmp_path).write(), "mlog", *mode, vmin=vmin)
    if mode:
        j = _load_json(out)
        # LB31: one top-level key for the ReFS version, `ReFSVersion` -- not `version`, `RefsVersion` or `refs_version`
        # beside it or instead of it
        refs_keys = [k for k in j if re.fullmatch(r"(?i)(?:refs_?)?version", k)]
        assert j.get("ReFSVersion") == "3.14" and refs_keys == ["ReFSVersion"], \
            "top-level ReFS version key(s): %r; decided `ReFSVersion` = '3.14' alone (LB31)" % {
                k: j[k] for k in refs_keys}
    else:
        assert "ReFS v3." not in out + err and "ReFS 3.%d" % vmin in out + err, \
            [ln for ln in (out + err).splitlines() if "ReFS" in ln]


@pytest.mark.parametrize("cs", [0x1000, 0x10000], ids=["4k", "64k"])
def test_lb3_mlog_sizes_are_bytes_in_key_value_lines_and_kib_in_text(monkeypatch, tmp_path, cs):
    rc, out, err = inproc(monkeypatch, MC._intact(tmp_path, cs).write(), "mlog")
    assert "cluster_size=%d" % cs in out, [ln for ln in out.splitlines() if "cluster_size" in ln]
    ctl = "\n".join(_section(out, "MLog Control Area"))
    _fx(ctl, "no control-area section")
    assert not re.search(r"\b0x1000\b", ctl) and re.search(r"\b4 KiB\b", ctl), \
        "the log block size is not '4 KiB': %r" % [ln for ln in ctl.splitlines() if "ize" in ln]


def test_lb3_mlog_text_prints_an_absent_value_as_none(monkeypatch, tmp_path):
    """N533 (1.14.0): the column holds the allocator clock, and a clock of 0 is a value, printed 0 -- not an absence
    (K20 A's '(none)' is for a value the record does not carry)."""
    rc, out, err = inproc(monkeypatch, _handle_log(tmp_path), "mlog", "-v")
    hdr, rows = _redo_table(out)
    r0 = [r for r in rows if not re.search(r"(?<![0-9a-fx])375(?![0-9])", r)]
    _fx(len(r0) == 1, "expected one record with clock 0: %r" % rows)
    assert re.search(r"\s0\s", r0[0]) and "(none)" not in r0[0] and "—" not in r0[0], "clock 0 printed as: %r" % r0[0]


def test_lb3_mlog_v_flags_are_hex_first_with_names_in_parentheses(monkeypatch, tmp_path):
    log = build_log(tmp_path / "log.raw", [[[redo_rec(0x04, 3)]], [[redo_rec(0x04, 1), redo_rec(0x04, 2)]]]).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "-v")
    hdr, rows = _redo_table(out)
    _fx(len(rows) == 3, "expected 3 records: %r" % rows)
    bad = []
    for row, fl in zip(rows, (3, 1, 2)):
        m = re.search(r"(?<![\w.])0x%x(?:\s*\(([^)]*)\))?(?![\w.])" % fl, row)
        if not m or re.search(r"\s(?:S\+C|S|C)\s", row) or (m.group(1) and not re.fullmatch(r"\w+(?:\|\w+)*", m.group(1))):
            bad.append(row)
    assert not bad, "flags not as '0x%%x (Name|Name)': %r" % bad


@pytest.mark.parametrize("mode", ["--csv", "--json"])
def test_lb3_mlog_lists_are_semicolon_joined_in_csv_and_lists_in_json(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", mode)
    if mode == "--csv":
        hdr, rows, _at = csv_table(out)
        cell = rows[0][_col(hdr, r"(?i)^opcodes$")]
        assert ";" in cell and " " not in cell and len(cell.split(";")) == 2, "payload 1's mnemonics: %r" % cell
        # critic D9: every list column, the opcode numbers included -- a column whose row-1 cell holds payload 1's two
        # opcodes (0x04, 0x04) in any separator or padding must hold them ';'-joined
        nums = [i for i, h in enumerate(hdr) if i < len(rows[0])
                and [int(t, 16) for t in re.split(r"[;\s,]+", rows[0][i].strip())
                     if re.fullmatch(r"0x[0-9a-fA-F]+", t)] == [0x04, 0x04]]
        bad = [(hdr[i], rows[0][i]) for i in nums if rows[0][i] != "0x4;0x4"]
        assert not bad, "list columns not ';'-joined unpadded hex: %r" % bad
    else:
        lists = [v for p, k, v in _walk(_load_json(out)) if k.lower() == "opcodes"]
        assert lists and all(isinstance(v, list) for v in lists), "Opcodes in --json: %r" % lists[:2]


MFT = "step5/win11refstestmftecmd.raw"
# The rows that name an unresolved directory 'OID 0x...' today on win11refstestmftecmd: 115 rows of `mlog --csv`, the
# same 115 of `mlog --parse`, and 115 MLog rows of `timeline --csv` (measured on the key 2026-10-15; the published
# sample `analysis/samples/disks/win11refstestmftecmd/forefst/mlog.csv`, made on the normal disks, has the same 115).
# K22 A: each takes one of `_usn_resolve_path`'s labels, holding the row's own OID (critic D10).
# Group 1 (1.14.0, the review's F4): a row now shows its name in that name row's own directory; on the sample three rows
# name a directory gone from today's tree (the activity log created and deleted xbpt_zulu_papa_302212.dat and
# elvis_dir_report_869722 inside elvis_dir_echo_418892, which no longer exists) and two no longer do: 115 -> 116
# Group 1b (1.14.0, N557): a row shows the directory of the name it names (the pair's old directory, or the first
# directory entry's), no longer an unrelated first table: 8 rows name a directory gone from today's tree. Checked
# against the sample's key on the directories it never renames, moves or deletes: 472 rows right, 0 wrong (the tool
# before: 45 wrong; RC1D/evidence/measures/g1b_dirs_sample.json)
MFT_UNRESOLVED = 8


def _path_cols(hdr):
    cols = [i for i, h in enumerate(hdr) if re.search(r"(?i)path", h)]
    _fx(cols, "no path column in %r" % hdr)
    return cols


def _k22_offenders(paths):
    lead = sorted({p.split(" ")[0] for p in paths if re.match(r"/[^/\s]", p)})
    oidf = sorted({p for p in paths if re.match(r"OID 0x", p)})
    return lead, oidf


def _labelled_rows(rows, path_cols, oid_col):
    """(rows whose path cells carry a `_usn_resolve_path` label, those whose label's OID is not the row's OID)."""
    lab, wrong = [], []
    for r in rows:
        ms = [_RESOLVE_LABEL.match(r[i]) for i in path_cols if i < len(r)]
        ms = [m for m in ms if m]
        if ms:
            lab.append(r)
            if oid_col is not None and any(_as_int("0x" + m.group(1)) != _as_int(r[oid_col] or "0") for m in ms):
                wrong.append(r)
    return lab, wrong


@pytest.mark.parametrize("mode", ["--csv", "--parse"])
def test_lb3_mlog_paths_take_the_files_fullpath_form_on_image_win11refstestmftecmd(mode):
    rc, out, err = cli(MFT, "mlog", mode)
    if mode == "--csv":
        hdr, rows, _at = csv_table(out)
        pc = _path_cols(hdr)                             # LB27: FullPath and ParentPath, both in the K22 form
        paths = [r[c] for r in rows for c in pc if c < len(r)]
        lab, wrong = _labelled_rows(rows, pc, _col(hdr, r"(?i)^oid$"))
    else:
        labels = [re.match(r"^  \[[^\]]+\]\s+(.*)$", row).group(1) for row, _n in _parse_rows(out)]
        paths, rows = labels, labels
        lab, wrong = [p for p in labels if _RESOLVE_LABEL.match(p)], []
    _fx(len(rows) > 1000, "%d rows: not the sample's 4,824" % len(rows))
    lead, oidf = _k22_offenders(paths)
    assert not lead and not oidf, "paths with a leading '/' (%d, e.g. %r) or 'OID 0x...' (%d, e.g. %r)" % (
        len(lead), lead[:2], len(oidf), oidf[:2])
    assert len(lab) == MFT_UNRESOLVED and not wrong, (
        "%d rows carry a `_usn_resolve_path` label (%d with another OID than the row's); the %d rows of an unresolved "
        "directory must (critic D10)" % (len(lab), len(wrong), MFT_UNRESOLVED))


def test_lb16_timeline_mlog_rows_take_the_files_fullpath_form_on_image_win11refstestmftecmd():
    rc, out, err = cli(MFT, "timeline", "--fast", "--csv")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    hdr = next(csv.reader(lines[:1]))
    rows = _timeline_mlog_rows(out, True)
    _fx(len(rows) > 4000, "%d MLog rows: not the 4,237 this image's timeline lists" % len(rows) + _ctx(rc, "", err))
    nc = _col(hdr, r"(?i)^(?:pathtoday|path|fullpath)$")       # acceptance 1.14.0 (Q-C): an MLog row's path is PathToday
    lead, oidf = _k22_offenders([r[nc] for r in rows if nc < len(r)])
    assert not lead and not oidf, "timeline MLog paths with a leading '/' (%d, e.g. %r) or 'OID 0x...' (%d, e.g. %r)" \
        % (len(lead), lead[:2], len(oidf), oidf[:2])
    lab, wrong = _labelled_rows(rows, [nc], _col(hdr, r"(?i)^oid$"))
    assert len(lab) == MFT_UNRESOLVED and not wrong, (
        "%d timeline MLog rows carry a `_usn_resolve_path` label (%d with another OID); the %d rows of an unresolved "
        "directory must" % (len(lab), len(wrong), MFT_UNRESOLVED))


def _files_join(parent, name):
    """`files`' FullPath of a name in a directory (fd:7061 `_full_path`): '.' or an empty parent gives the bare name."""
    return name if parent in ("", ".") else "%s/%s" % (parent, name)


def test_lb27_mlog_csv_splits_the_path_into_fullpath_and_parentpath(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", "--csv")
    hdr = csv_table(out)[0]
    # acceptance 1.14.0 (P10, decision 49 point 6): LB27's two columns are the live tree's path TODAY, so named so
    assert "PathToday" in hdr and "ParentPathToday" in hdr and not [h for h in hdr if h.lower() == "path"], (
        "CSV header %r: decided PathToday + ParentPathToday, no mixed Path column (LB27, P10)" % hdr)


def test_lb27_mlog_csv_fullpath_is_parentpath_and_name_on_image_win11refstestmftecmd():
    rc, out, err = cli(MFT, "mlog", "--csv")
    hdr, rows, _at = csv_table(out)
    _fx(len(rows) > 1000, "%d rows: not the sample's 4,824" % len(rows))
    # acceptance 1.14.0 (P10): FullPath / ParentPath are PathToday / ParentPathToday
    assert "PathToday" in hdr and "ParentPathToday" in hdr, "CSV header %r: no PathToday / ParentPathToday" % hdr
    fp, pp, nm = hdr.index("PathToday"), hdr.index("ParentPathToday"), _col(hdr, r"(?i)^name$")
    named = [r for r in rows if r[nm]]
    _fx(len(named) > 1000, "%d named rows: not the sample's 3,050" % len(named))
    # the `files` meanings (decision 35, one meaning per column): FullPath = ParentPath + '/' + Name on a named row
    bad = [(r[pp], r[nm], r[fp]) for r in named if r[pp] and r[fp] != _files_join(r[pp], r[nm])]
    assert not bad, "%d named rows whose FullPath is not ParentPath/Name, e.g. %r" % (len(bad), bad[:3])
    assert [r for r in named if r[pp]], "no named row carries its directory in ParentPath"


def _files_parent(full):
    """LB37: the ParentPath `files` gives an object whose FullPath is `full` -- the path up to its last '/', and '.'
    for an object in the root (fd:6540). None for the root itself or no path (not asserted: K22 leaves the root's form
    open), '' for a bare unresolved label (`<oid 0x..>`: the parent is unknown)."""
    if full in ("", ".", "/"):
        return None
    if _RESOLVE_LABEL.match(full) and _RESOLVE_LABEL.match(full).end() == len(full):
        return ""
    return full.rsplit("/", 1)[0] if "/" in full else "."


# win11refstestmftecmd, measured on the key 2026-10-15 (today's `path` column of `mlog --csv`): 1,774 of 4,824 rows have
# no name; 1,720 of them name a resolved object (1,286 below a directory, 434 in the root), 19 the root itself, 2 an
# unresolved directory, 33 no object.
MFT_UNNAMED_RESOLVED = 1720


def test_lb37_mlog_csv_parentpath_on_unnamed_rows_is_the_objects_parent_on_image_win11refstestmftecmd():
    rc, out, err = cli(MFT, "mlog", "--csv")
    hdr, rows, _at = csv_table(out)
    _fx(len(rows) > 1000, "%d rows: not the sample's 4,824" % len(rows))
    # acceptance 1.14.0 (P10): FullPath / ParentPath are PathToday / ParentPathToday
    assert "PathToday" in hdr and "ParentPathToday" in hdr, "CSV header %r: no PathToday / ParentPathToday" % hdr
    fp, pp, nm = hdr.index("PathToday"), hdr.index("ParentPathToday"), _col(hdr, r"(?i)^name$")
    oc = _col(hdr, r"(?i)^oid$")
    unnamed = [r for r in rows if not r[nm]]
    resolved = [r for r in unnamed if _files_parent(r[fp])]
    _fx(len(resolved) > 1000, "%d unnamed rows name a resolved object; %d measured on the key" % (
        len(resolved), MFT_UNNAMED_RESOLVED))
    # a known parent is given in the `files` form ('.' for the root); never the object itself, never left empty
    bad = [(r[fp], r[pp]) for r in resolved if r[pp] != _files_parent(r[fp])]
    assert not bad, "%d of %d unnamed rows whose ParentPath is not the object's own parent (LB37), e.g. %r" % (
        len(bad), len(resolved), bad[:3])
    # an unknown parent is empty: an unresolved object (a label naming its parent is accepted), or no object at all
    unknown = [r for r in unnamed if _files_parent(r[fp]) == ""]
    bad = [(r[fp], r[pp]) for r in unknown if r[pp] and not _RESOLVE_LABEL.match(r[pp])]
    bad += [(r[fp], r[pp]) for r in unnamed if not r[fp] and not r[oc] and r[pp]]
    assert not bad, "unnamed rows whose parent is unknown and whose ParentPath is not empty (LB37): %r" % bad[:3]


def test_lb3_control_counts_stay_decimal(monkeypatch, tmp_path):
    """K28/decision 35: counts stay decimal (a blanket hex conversion must not reach them)."""
    log = MC._intact(tmp_path).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--stats")
    # C1_LEAD_SETTLEMENTS C-5: N437's labels (`Redo records`, `Log records checked`) or the earlier ones
    _keep(re.search(r"(?m)^\s*(?:Total|Redo) records:\s+32\s*$", out)
          and re.search(r"(?m)^\s*(?:Log r|R)ecords checked:\s+32\s*$", out),
          "a count is no longer decimal" + _ctx(rc, out, err))
    rc, out, err = inproc(monkeypatch, log, "mlog", "--json")
    counts = [v for p, k, v in _walk(_load_json(out)) if k.lower() in ("checked", "verified", "failed")]
    _keep(counts and all(isinstance(v, int) and not isinstance(v, bool) for v in counts), "JSON counts %r" % counts)


def test_waveb_matchers_accept_a_sound_output_and_reject_todays():
    """The readers this file's REDs rest on: each accepts a sound form of the decided output and rejects today's."""
    good = "  16 record(s) of an earlier volume's log are left out; `mlog --earlier-logs` shows them"
    assert earlier_statement(good, (16,)) and not earlier_statement(good, (17,))
    assert not earlier_statement("  Total records:      48\n  (use --verbose)", (16, 48))
    assert _states_latest_payload_time("  A row's time is the latest FILETIME embedded in its log payload's records.")
    assert not _states_latest_payload_time("  the affected object's embedded $SI birth (approximate; ...)")
    for s in ("0x12.blk3", "PLCN 0x000012.03", "@PLCN 0x12.blk3+0xb8"):
        assert _LOC.search(s), s
    for s in ("block 291", "@PLCN 18.blk3+0xb8", "0x12.13", "0x123", "0x12.blk30"):
        assert not _LOC.search(s), s
    j = {"Control": {"PLCN": "0x1", "Sequence": 51},
         "ControlCopies": [{"PLCN": "0x1", "Verified": True}, {"PLCN": "0x2", "Verified": False}]}
    assert _copy_verdicts(j) == {1: True, 2: False}
    assert _copy_verdicts({"control": {"plcn": 1, "flags": 1}, "mlog_info": {"ctrl_plcn_0": 1}}) == {}
    assert _norm(None) == "" and _norm(["A", "B"]) == "A;B" and _norm(3) == "3" and _norm(True) == "true"
    assert _has_num("  3 undated log payloads", 3) and not _has_num("  0x3 (TxnStart)", 3) \
        and not _has_num("13 rows", 3)
    assert [m.group(1) for m in _PLCN_V.finditer("@PLCN 0x11.blk0+0xb8 @PLCN 17.blk0+0xb8")] == ["0x11", "17"]
    # amended 2026-10-15: the readers of the critic's D3, D6, D10, D11 and of LB14, LB26
    hits, other = stated_count(good, 16, (48,), _UNIT_RECORDS)
    assert hits and not other
    hits, other = stated_count("  48 record(s) of an earlier volume's log are left out; `mlog --earlier-logs` shows "
                               "them", 16, (48,), _UNIT_RECORDS)
    assert not hits and other
    tl = "  4 MLog row(s) of an earlier volume's log are left out; `mlog --earlier-logs` shows them"
    assert stated_count(tl, 4, (5, 10), _UNIT_ROWS) == ([tl], [])
    assert not stated_count(tl.replace("row(s)", "event(s)"), 4, (5, 10), _UNIT_ROWS)[0]
    assert _says_sorted_not_joined("  Sources merged: USN=1  MLog=4  (sorted by time; rows are not joined across sources)")
    assert not _says_sorted_not_joined("  Sources merged: USN=1  MLog=4  $SI-MACB=0  (time-sorted; correlated by name/path —")
    assert _RESOLVE_LABEL.match("<oid 0x707>/MSI9d8e4.tmp").group(1) == "707" and _RESOLVE_LABEL.match("<unlinked 0x7>")
    assert not _RESOLVE_LABEL.match("OID 0x707") and not _RESOLVE_LABEL.match("test/<oid 0x707>")
    assert _MIXED_ACRONYM.search("ControlPlcn0") and _MIXED_ACRONYM.search("PayloadUuid") and _MIXED_ACRONYM.search("Oid")
    assert not [n for n in ("ControlPLCN0", "PayloadUUID", "OID", "MLogInfo", "Side", "Void", "TxnStart")
                if _MIXED_ACRONYM.search(n)]
    assert _sys_path_literals('import sys\nsys.path.insert(0, "/workspace/refs/forefstdev")\n') == \
        [(2, "/workspace/refs/forefstdev")]
    assert _sys_path_literals('import sys\nP = "/x/y"\nsys.path.insert(0, P)\n') == [(3, "/x/y")]
    assert not _sys_path_literals('import os, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\n'
                                  'sys.path.insert(0, os.path.join(HERE, "..", "forefstdev"))\n')
    assert _files_join(".", "a.txt") == "a.txt" and _files_join("test", "a.txt") == "test/a.txt"
    tl_text = ("  Sources merged: USN=0  MLog=4  $SI-MACB=0\n  NOTE: USN journal inactive -- timeline is $SI + MLog only.\n"
               "  Caveat: USN and $SI carry exact FILETIMEs. MLog has NO wall-clock time\n"
               "  2026-05-16 16:55:20 UTC  MLog   —      MODIFY\n"
               "  2026-05-16T16:55:20.9805996Z  MLog   (none)  MODIFY\n"
               "  (undated)                MLog   0x701  test  DELETE\n")
    assert len(_timeline_mlog_rows(tl_text, False)) == 3
    # amended 2026-10-15, second pass: the readers of LB31, LB36 and LB37
    raw = ("  Control PLCN:      0x8000\n"
           "  VLCN 0x000011  PLCN 0x000011      MLog   sig=4d4c6f67  u32[0]=0x676f4c4d  u32[1]=0x5e524606\n"
           "  PLCN 0x12.blk0  MLog  sig=4d4c6f67  u32[0]=0x676f4c4d\n"
           "  0x13.blk3  MLog  sig=4d4c6f67\n"
           "  16 record(s) of an earlier volume's log are left out; `mlog --earlier-logs` shows them\n"
           "  Data area:         0x10 - 0x90 (128 clusters)\n")
    assert [p for p, _ln in _raw_rows(raw)] == [0x11, 0x12, 0x13]
    assert [_files_parent(x) for x in ("test/a/b", "test", "<oid 0x75b>", "<unlinked 0x7>/x", ".", "")] == \
        ["test/a", ".", "", "<unlinked 0x7>", None, None]
    assert [n for n in ("RefsVersion", "MlogInfo", "REFSVersion") if _PRODUCT_CASE.search(n)] == \
        ["RefsVersion", "MlogInfo", "REFSVersion"]
    assert not [n for n in ("ReFSVersion", "MLogInfo", "PageRefs", "TableHandle", "Control") if _PRODUCT_CASE.search(n)]
    # amended 2026-10-15, third pass: the LB38 reader (today's `--stats` lines name the copies and FAILED, but not
    # the copy in use)
    today = ("  Verified:           32\n  Failed:             0\n"
             "  Control copy 0 (PLCN 0x1): FAILED  stored=0x393d14ce computed=0x393d14cf\n"
             "  Control copy 1 (PLCN 0x2): FAILED  stored=0x393d14cf computed=0x393d14ce\n")
    assert not lb38_statements(today, (0, 1))
    for s in ("[forefst] MLog control copy 0 (PLCN 0x1), the copy in use, failed its fold; copy 1 (PLCN 0x2) failed "
              "too: the log start and end shown are unverified",
              "  Both MLog control copies fail their fold (copy 0 at PLCN 0x1, copy 1 at PLCN 0x2): the control area "
              "is unverified",
              today + "  The control copy in use fails its fold.",
              "  Control copy 0 (PLCN 0x1): FAILED -- this is the copy in use"):
        assert lb38_statements(s, (0, 1)), s
    for s in ("  exit 2: the MLog control area failed its fold",                     # no copy named
              "  MLog control copy 0 (PLCN 0x1) is in use",                         # no failure
              "  Control copy 0 (PLCN 0x1): FAILED (not in use)",                   # negated
              "  copy 0 (PLCN 0x1), the copy in use, failed its fold"):             # no control area named
        assert not lb38_statements(s, (0, 1)), s
    for s in ("  Control copy 0 (PLCN 0x1): verified (in use)\n  Control copy 1 (PLCN 0x2): FAILED",
              "  Control copy 0 (PLCN 0x1): in use\n  Control copy 1 (PLCN 0x2): FAILED",
              "  Control copy 1 (PLCN 0x2) FAILED its fold; the copy in use (copy 0) verifies",
              "  Control copy 1 (PLCN 0x2) FAILED its fold; no action needed, copy 0 verifies",
              "  All control copies verified, records failed: 0"):
        assert not lb38_statements(s, (1,)), s
    assert lb38_statements("  MLog control copy 1 (PLCN 0x2), the copy in use, failed its fold", (1,))
    # M1 (group-4 fixer): a negation after the in-use phrase -- RED_waveB_recheck's four sentences, none an LB38
    # statement -- and LB39's reader on the decided form and on what it must refuse
    for s in ("  MLog control copy 0 (PLCN 0x1) failed its fold; the copy in use is not affected",
              "  MLog control copy 0 (PLCN 0x1) failed its fold; the copy in use is unaffected",
              "  MLog control copy 0 (PLCN 0x1) failed its fold; the copy in use (copy 1) is not affected",
              "  MLog control copy 0 (PLCN 0x1) failed its fold; it is not the copy in use"):
        assert not lb38_statements(s, (0,)), s
    lb39 = ("[forefst] MLog control copy 1 (PLCN 0x2, sequence 50) fails its integrity check (stored=0x1, computed=0x2)."
            " It is not the copy in use: copy 0 (PLCN 0x1, sequence 51) verifies and is the one read, so the control "
            "area shown is not affected.")
    assert lb39_statements(lb39, (1,)) and not lb38_statements(lb39, (1,))
    for s in ("  MLog control copy 1 (PLCN 0x2) fails its integrity check",              # nothing about the copy in use
              "  copy 1 (PLCN 0x2) fails; the copy in use is not affected",              # no control area named
              "  MLog control copy 1 (PLCN 0x2): the copy in use is not affected"):      # no failure stated
        assert not lb39_statements(s, (1,)), s


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N413 / N414 / N415 (LB42, LB43, LB46; wave B part 3, written before the fix)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# What the driver does with the control area and the records (read on 17134, 26100.8115, 26100.9444, Insider 29574):
#   * LogWriteControlRecord writes the constant 1 at the control record header +0x08 and nothing reads it
#     (LogValidateEntryHeader checks header +0x00, +0x04, +0x0C, +0x10..+0x1F, +0x20, +0x28, +0x30, +0x38/+0x3C and the
#     entry header, never +0x08); the version the driver CHECKS is payload +0x40: MlLogOpenLog opens the log only when
#     it is 1 (8115 refs_win11.decomp.c :284325, 9444 :283913, Insider :350940, 17134 `(int)puVar13[8] == 1`), else
#     0xC0000032. 1 on 240/240 corpus copies, header +0x08 1 on 240/240 (part 1b, n411_summary.txt).
#   * LogValidateEntryHeader accepts a record of the open log only when its header +0x04 equals handle+0x2FE8 and its
#     header +0x10..+0x1F equal handle+0x28..+0x37 (8115 :134433-134447). handle+0x28 is the control payload's +0x28
#     (the handle is a byte copy of the payload); handle+0x2FE8 is MlLogOpenLog's param_11 = CmsVolume+0xCF0, which
#     ReadSuperBlock sets to CalculateVolumeSignature(superblock + 0x50) -- the XOR of the four u32 of the volume GUID,
#     1 when that is 0 (8115 :211353 / :213140 / :203716; 9444 :210658; Insider :280261; 17134 :53348). Measured on
#     every corpus volume before these REDs (`fixes/waveB_fix_evidence/part3/n414_summary.txt`): that signature, over
#     the superblock copy the tool reads, equals both control copies' header +0x04 (240/240), the checkpoint copies'
#     +0x0C (240/240) and the magic of every data record of the log instance (906,274), on 120/120 volumes.
#
# N413 (LB42): header +0x08 is shown raw with its offset (LB40's rule), never under a "version" name; payload +0x40 is
#   printed under its name. N414 (LB43): the earlier-volume filter keys on the volume's format magic and the payload's
#   +0x28 UUID, not on the control record header (a header edited and re-sealed decides nothing). N415 (LB46): a copy
#   in use whose payload +0x40 is not 1 -- the driver would not open this log -- is stated (the value read, the only
#   value the driver opens) and exits 2 in every mode of LB24's set and in `timeline`'s MLog source.

N413_HDR08 = 7                                  # planted at header +0x08: not a value the driver writes there (1)
N415_VERSION = 2                                # planted at payload +0x40: a log version the driver does not open
_VERSION_LABEL = re.compile(r"(?i)\bversion\b")       # a text label ("Log version")
_VERSION_KEY = re.compile(r"(?i)version")               # a JSON key: PascalCase (K21) has no word boundary ("LogVersion")


def _resealed_ctrl(log, edit):
    """Both control copies of `log` passed through `edit(buf, payload_offset)` and re-sealed (their folds verify)."""
    for i in range(2):
        b = bytearray(log.ctrl[i])
        edit(b, _payload_at(b))
        log.ctrl[i] = MC._seal(b)
    return log


def _n413_log(tmp_path, hdr08=N413_HDR08, version=1):
    log = SynLog(tmp_path / "n413.raw").run(1, 0x20, 1, session_start=True).control(END, END)

    def edit(b, p):
        struct.pack_into("<I", b, 0x08, hdr08)
        struct.pack_into("<I", b, p + 0x40, version)
    _resealed_ctrl(log, edit).write()
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs)
        c, p = MC.parse_block(blk), _payload_at(blk)
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and c["seq"] == 51 - i and le32(blk, 0x08) == hdr08
            and le32(blk, p + 0x40) == version, "control copy %d is not what the case needs" % i)
    return log


def test_n413_json_header_0x08_is_raw_bytes_with_its_offset_and_payload_0x40_is_the_version(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _n413_log(tmp_path), "mlog", "--json")
    c = _json_control(_load_json(out))
    named = {k: v for k, v in c.items() if _VERSION_KEY.search(k) and _as_int(v) == N413_HDR08}
    raw = [(o, h) for o, h in _raw_entries(c) if o == 0x08 and struct.pack("<I", N413_HDR08).hex() in h]
    ver = {k: v for k, v in c.items() if _VERSION_KEY.search(k) and isinstance(v, int) and not isinstance(v, bool)
           and v == 1}
    assert not named and raw and ver, "Control: header +0x08 (%d, planted) under a version name %r; shown as raw bytes " \
        "with its offset: %r; payload +0x40 (1, the version the driver checks) under a version name: %r; Control = %r" % (
            N413_HDR08, named, raw, ver, c)


@pytest.mark.parametrize("mode", [(), ("--stats",)], ids=["default", "stats"])
def test_n413_text_header_0x08_is_raw_bytes_with_its_offset_and_payload_0x40_is_the_version(monkeypatch, tmp_path,
                                                                                            mode):
    rc, out, err = inproc(monkeypatch, _n413_log(tmp_path), "mlog", *mode)
    labelled = _text_labelled(out, _VERSION_LABEL)
    named = [(lab, v) for lab, v in labelled if _has_num(v, N413_HDR08)]
    at = re.compile(r"(?i)(?<![0-9a-fx])0x0*8(?![0-9a-f])")
    raw = [ln for ln in out.splitlines() if at.search(ln) and struct.pack("<I", N413_HDR08).hex()
           in re.sub(r"[\s:]", "", ln).lower()]
    ver = [(lab, v) for lab, v in labelled if _has_num(v, 1)]
    assert not named and raw and ver, "`mlog %s`: header +0x08 (%d) under a version label %r; shown raw with its offset " \
        "%r; payload +0x40 (1) under a version label %r" % (" ".join(mode), N413_HDR08, named, raw, ver) \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [("--json",), ("--stats",)], ids=["json", "stats"])
def test_n413_header_0x08_and_the_log_version_on_image_win11refsmini(mode):
    """win11refsmini: header +0x08 and payload +0x40 are both 1 there (as on 240/240 copies), read here; the text and
    JSON show header +0x08 raw with its offset and the log version under its name."""
    rel = "step1/win11refsmini.raw"
    rc, out, err = cli(rel, "mlog", *mode)
    if mode == ("--json",):
        c = _json_control(_load_json(out))
        plcn = _as_int(_ci_get(c, "PLCN"))
    else:
        m = re.search(r"(?m)^\s*Control PLCN:\s+(0x[0-9a-f]+)", out)
        plcn = int(m.group(1), 16) if m else None
    _fx(plcn, "%s: the copy in use is not named" % rel)
    img = MC.corpus(rel)
    ps = MC._refs_ps(img)
    blk = MC.read_block(img, ps + plcn * MC._cluster_size(img, ps))
    _fx(le32(blk, 0x08) == 1 and le32(blk, _payload_at(blk) + 0x40) == 1, "%s: header +0x08 / payload +0x40 are not 1"
        % rel)
    if mode == ("--json",):
        raw = [(o, h) for o, h in _raw_entries(c) if o == 0x08 and h.startswith("01000000")]
        ver = [k for k, v in c.items() if _VERSION_KEY.search(k) and v == 1 and not isinstance(v, bool)]
        hdr = [k for k in c if re.fullmatch(r"(?i)version", k)]
        assert raw and ver and not hdr, "%s --json: header +0x08 raw %r; the log version %r; a bare `Version` key %r" % (
            rel, raw, ver, hdr)
    else:
        at = re.compile(r"(?i)(?<![0-9a-fx])0x0*8(?![0-9a-f])")
        raw = [ln for ln in out.splitlines() if at.search(ln) and "01000000" in re.sub(r"[\s:]", "", ln)]
        ver = [lab for lab, v in _text_labelled(out, _VERSION_LABEL) if _has_num(v, 1)]
        bare = [lab for lab, v in _text_labelled(out, _VERSION_LABEL) if lab.strip().lower() == "version"]
        assert raw and ver and not bare, "%s mlog --stats: header +0x08 raw %r; the log version %r; a bare `Version:` " \
            "label %r" % (rel, raw, ver, bare)


# ─── N414: the filter's key ────────────────────────────────────────────────────────────────────────────────────

N414_LAST = 13              # records 1..13; LCN 0x1e (data-area block 14 at 4 KiB) carries the volume's superblock


def _supb_block(signature_of):
    """A superblock cluster as far as the volume's format magic goes: 'SUPB' and a GUID at +0x50 whose four u32 XOR to
    `signature_of` (CalculateVolumeSignature). Nothing else of a superblock is read for the magic."""
    b = bytearray(MLOG_BLK)
    b[0:4] = b"SUPB"
    struct.pack_into("<IIII", b, 0x50, signature_of ^ 0x11111111 ^ 0x22222222 ^ 0x33333333, 0x11111111, 0x22222222,
                     0x33333333)
    return bytes(b)


def _n414_log(tmp_path, name, hdr_uuid=None, p28=None, hdr_magic=None, supb=None, dated=False, magic_slots=(0, 1)):
    """Records 1..13 of instance (MAGIC_A, UUID_A) (dated payloads when `dated`); both control copies carry
    `hdr_uuid` at header +0x10, `p28` at payload +0x28 and -- the copies in `magic_slots` (LB58) -- `hdr_magic` at
    header +0x04 when given (re-sealed); `supb`: the volume's format magic its superblock at LCN 0x1e gives (data-area
    block 14 of this 4 KiB log), or none."""
    log = SynLog(tmp_path / ("n414_%s.raw" % name))
    for k in range(1, N414_LAST + 1):
        prev = lsn(1, k - 1) if k > 1 else 0
        log.blocks[k] = (payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), prev, [[redo_rec(0x04, 3, 0, FT_A + k)]])
                         if dated else MC.data_block(MAGIC_A, UUID_A, 3, lsn(1, k), prev))
    log.control(lsn(1, N414_LAST + 1), lsn(1, N414_LAST + 1))

    for i in range(2):
        b = bytearray(log.ctrl[i])
        p = _payload_at(b)
        if hdr_uuid is not None:
            b[0x10:0x20] = hdr_uuid
        if p28 is not None:
            b[p + 0x28:p + 0x38] = p28
        if hdr_magic is not None and i in magic_slots:
            struct.pack_into("<I", b, 0x04, hdr_magic)
        log.ctrl[i] = MC._seal(b)
    if supb is not None:
        log.blocks[14] = _supb_block(supb)
    log.write()
    _fx(log.block_off(14) == 0x1E * log.cs, "LCN 0x1e is not data-area block 14 of this log")
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs)
        c, p = MC.parse_block(blk), _payload_at(blk)
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and c["uuid"] == (hdr_uuid or UUID_A)
            and bytes(blk[p + 0x28:p + 0x38]) == (p28 or UUID_A)
            and c["magic"] == (hdr_magic if hdr_magic is not None and i in magic_slots else MAGIC_A),
            "control copy %d is not what the case needs" % i)
    if supb is not None:
        s = MC.read_block(log.path, 0x1E * log.cs)
        _fx(s[:4] == b"SUPB" and le32(s, 0x50) ^ le32(s, 0x54) ^ le32(s, 0x58) ^ le32(s, 0x5C) == supb,
            "the planted superblock does not give the volume's format magic 0x%08x" % supb)
    return log


def _n414_counts(monkeypatch, log, mode=()):
    """(this volume's redo records listed by `mlog -v` / the default view, the earlier count stated, rc, out, err)."""
    rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
    listed = redo_records(out) or 0
    m = re.search(r"(\d+) log record\(s\) of an earlier (?:volume's log|log of this volume) (?:is|are) left out",
                  out + "\n" + err)
    return listed, int(m.group(1)) if m else 0, rc, out, err


@pytest.mark.parametrize("case", ["header-uuid-edited", "header-magic-edited"])
def test_n414_records_of_this_log_are_kept_when_only_the_control_header_differs(monkeypatch, tmp_path, case):
    """The records carry the payload's +0x28 UUID and the volume's format magic: the driver takes them as this log's,
    whatever the control record HEADER says (an edited, re-sealed header).

    LB58 (part 3c, sanctioned): the magic case edits copy 0 only (the newer, sequence 51). Since N418 the driver -- and
    the tool -- refuses a copy whose +0x04 is not the volume's signature, so with both copies edited no copy was read
    and every record was listed for that reason (N412), not through the record key; with copy 1 still accepted the
    filter runs, and the records are kept because their key is the volume's magic and the payload's UUID (a key taken
    from the edited header, 0x6d790647, would leave all 13 out). The premise below keeps that path."""
    log = (_n414_log(tmp_path, case, hdr_uuid=UUID_P) if case == "header-uuid-edited" else
           _n414_log(tmp_path, case, hdr_magic=MAGIC_B, supb=MAGIC_A, magic_slots=(0,)))
    listed, left, rc, out, err = _n414_counts(monkeypatch, log)
    _keep(not n412_statements(out + "\n" + err), "%s: no control copy is read, so nothing is filtered by the record key "
          "(LB58)" % case + _ctx(rc, out, err))
    assert listed == N414_LAST and not left, "%s: the %d records carry the payload's UUID and the volume's format magic " \
        "(LogValidateEntryHeader takes them as this log's); `mlog` lists %d of them and states %d left out as an " \
        "earlier volume's" % (case, N414_LAST, listed, left) + _ctx(rc, out, err)


def test_n414_records_whose_uuid_is_not_the_payloads_are_left_out(monkeypatch, tmp_path):
    """The payload's +0x28 UUID differs from the records' (and the header's): the driver rejects every record whose
    +0x10 is not handle+0x28, so none is this log's -- the count is stated, as LB1 states it."""
    listed, left, rc, out, err = _n414_counts(monkeypatch, _n414_log(tmp_path, "payload-uuid-edited", p28=UUID_P))
    assert listed == 0 and left == N414_LAST, "the payload's +0x28 UUID is not the records': `mlog` lists %d of the %d " \
        "records as this volume's and states %d left out" % (listed, N414_LAST, left) + _ctx(rc, out, err)


def test_n414_timeline_keys_its_mlog_rows_on_the_payload_uuid(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _n414_log(tmp_path, "dated-header-uuid-edited", hdr_uuid=UUID_P, dated=True),
                          "timeline", "--fast")
    rows = _timeline_mlog_rows(out, False)
    left = re.search(r"(\d+) MLog row\(s\) of an earlier (?:volume's log|log of this volume)", out + "\n" + err)
    assert len(rows) == N414_LAST and not left, "the control header's UUID was edited: `timeline` lists %d of the %d " \
        "MLog rows (the records carry the payload's UUID) and states %r" % (len(rows), N414_LAST, left and left.group(0)) \
        + _ctx(rc, out, err)


def test_n414_control_an_intact_log_keeps_every_record(monkeypatch, tmp_path):
    """Not a RED. The superblock gives the control header's magic (as on 120/120 corpus volumes) and the payload
    carries the header's UUID: every record is this log's, today and after the fix."""
    listed, left, rc, out, err = _n414_counts(monkeypatch, _n414_log(tmp_path, "intact", supb=MAGIC_A))
    assert rc == 0 and listed == N414_LAST and not left, _ctx(rc, out, err)


# ─── N415: the log version the driver checks ──────────────────────────────────────────────────────────────────

_N415_REFUSE = re.compile(r"(?i)\b(?:would|does|will)\s+not\s+(?:\w+\s+){0,2}open\b|\bnot\s+open\w*\b|\brefus\w*")
_N415_ONLY_1 = re.compile(r"(?i)\bonly\b[^.;\n]{0,60}(?<![\d.x])1(?![\d,.])|(?<![\d.x])1(?![\d,.])[^.;\n]{0,40}\bonly\b")


def n415_statements(text, value=N415_VERSION):
    """A line and the next two of its paragraph: the control area named, its log version (or payload +0x40) with the
    value read, the only value the driver opens (1), and that the driver would not open this log."""
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if (re.search(r"(?i)\bcontrol\b|\bMLog\b", w) and re.search(r"(?i)\bversion\b|\+0x40", w)
                    and _has_num(w, value) and _N415_ONLY_1.search(w) and _N415_REFUSE.search(w)):
                hits.append(w)
    return hits


def _n415_log(tmp_path, which=(0, 1), dated=False):
    """Both control copies (or those in `which`) carry log version 2 at payload +0x40, re-sealed; records 1..0x20
    (or the 4 dated payloads of `_dated_ctrl_log`)."""
    if dated:
        log = SynLog(tmp_path / ("n415_dated_%s.raw" % "".join(map(str, which))))
        for k in range(1, 5):
            log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                          [[redo_rec(0x04, 3, 0, FT_A + k)]])
        log.control(lsn(1, 5), lsn(1, 5))
    else:
        log = SynLog(tmp_path / ("n415_%s.raw" % "".join(map(str, which)))).run(1, 0x20, 1, session_start=True)
        log.control(END, END)
    for i in which:
        b = bytearray(log.ctrl[i])
        struct.pack_into("<I", b, _payload_at(b) + 0x40, N415_VERSION)
        log.ctrl[i] = MC._seal(b)
    log.write()
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs)
        c = MC.parse_block(blk)
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"]
            and le32(blk, _payload_at(blk) + 0x40) == (N415_VERSION if i in which else 1),
            "control copy %d is not what the case needs" % i)
    return log


@pytest.mark.parametrize("mode", _N412_MLOG_MODES, ids=_N412_MLOG_IDS)
def test_n415_a_log_version_the_driver_does_not_open_makes_every_mlog_mode_exit_2_with_a_statement(monkeypatch,
                                                                                                    tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _n415_log(tmp_path), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = n415_statements(err if export else out)
    assert rc == 2 and said, "the copy in use holds log version %d at payload +0x40 (MlLogOpenLog opens only 1): " \
        "`mlog %s` must exit 2 (exit %s; LB46) and state %s the value read, the only value the driver opens and that " \
        "it would not open this log (statement: %s)" % (N415_VERSION, " ".join(mode), rc, _lb38_where(export),
                                                         "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--jsonl",)], ids=["text", "csv", "json", "jsonl"])
def test_n415_a_log_version_the_driver_does_not_open_makes_timeline_exit_2_with_a_statement(monkeypatch, tmp_path,
                                                                                           mode):
    rc, out, err = inproc(monkeypatch, _n415_log(tmp_path, dated=True), "timeline", "--fast", *mode)
    _keep(len(_tl_mlog_rows(out, mode)) == 4, "the MLog rows are no longer listed (LB46 states the condition; it does "
          "not drop the rows)" + _ctx(rc, out, err))
    said = n415_statements(err if mode else out)
    assert rc == 2 and said, "the copy in use holds log version %d: `timeline %s` must exit 2 (exit %s; LB46) and state " \
        "it %s (statement: %s)" % (N415_VERSION, " ".join(mode), rc, _lb38_where(bool(mode)),
                                   "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--parse",), ("--csv",), ("--info",)], ids=["default", "parse", "csv", "info"])
def test_n415_control_a_copy_not_in_use_with_another_version_is_not_the_condition(monkeypatch, tmp_path, mode):
    """Not a RED. Only the OLDER copy (sequence 50, not in use) holds version 2: MlLogOpenLog checks the copy it read,
    the copy in use (LogCoreReadControlArea's newest copy that verifies), so the log opens -- exit 0, no statement."""
    rc, out, err = inproc(monkeypatch, _n415_log(tmp_path, which=(1,)), "mlog", *mode)
    _keep(rc == 0 and not n415_statements(out + "\n" + err), "`mlog %s` with only the copy not in use at version %d"
          % (" ".join(mode), N415_VERSION) + _ctx(rc, out, err))


def test_n413_n414_n415_matchers_accept_a_sound_output_and_reject_others():
    """The readers of the N413 / N415 REDs: each accepts a sound form and rejects what it must refuse."""
    sound = ("MLog control copy 0 (PLCN 0x1, sequence 51), the copy in use, holds log version 2 (payload +0x40); "
             "the driver opens a log only when its version is 1 (MlLogOpenLog), so it would not open this log.")
    assert n415_statements(sound) and n415_statements("[forefst] " + sound)
    for s in ("MLog control: log version 2 (payload +0x40).",                                  # nothing refused
              "MLog control: log version 1 (payload +0x40); the driver opens only 1.",           # not the value read
              "Log version: 2 (payload +0x40; the driver would not open this log)",            # the only value (1) missing
              "  Control copy 1 (PLCN 0x2): FAILED  stored=0x1 computed=0x2 (not in use)"):
        assert not n415_statements(s), s
    assert _text_labelled("  Log version:       1 (payload +0x40)", _VERSION_LABEL)
    assert _VERSION_KEY.search("LogVersion") and _VERSION_KEY.search("Version") and not _VERSION_KEY.search("Flags")
    # LB45: `_as_int` reads what int(v, 0) reads, and nothing else
    for v, want in (("0x1f", 31), ("31", 31), ("-7", -7), ("0", 0), (" 0x10 ", 16), ("0b101", 5), ("1_000", 1000),
                    ("007", None), ("0x", None), ("12a", None), ("", None), ("v3.14", None), (True, None), (4, 4)):
        assert _as_int(v) == want, (v, _as_int(v), want)
    assert not _text_labelled("  Header +0x08:      07000000 (raw)", _VERSION_LABEL)
    assert _raw_entries({"HeaderUndecodedBytes": [{"Offset": "0x8", "Length": 4, "Bytes": "07000000"}]}) == \
        [(0x8, "07000000")]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N418 / N419 / LB53 (wave B part 3b, written first, before the fix; WAVEB_PREP LB51, LB52, LB53)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Read before these REDs (26100.8115 refs_win11.decomp.c and the disassembly of refs_win11.sys 4b0558f6; the same
# tests on 17134, 26100.9444 and Insider 29574 unless said):
#   * LogCoreReadControlArea reads both control copies through LogReadControlRecord (:301803, :134105), which refuses
#     a copy that fails LogValidateEntryHeader (:134424-134478) -- header +0x00 'MLog', +0x04 == handle+0x2FE8, the
#     volume signature (CalculateVolumeSignature of the superblock GUID, N414) -- with 0xC03D0202, before its fold.
#     N418 (LB51): a copy whose +0x04 is not the volume's signature is not a copy the driver reads, so it is never the
#     copy in use; it is a failed copy (LB39 when the other copy is read, N412 when neither can be).
#   * MlLogOpenLog opens an existing log only when the copy LogCoreReadControlArea returned holds: +0x40 == 1 (N415),
#     +0x08 == handle+0x08 and +0x10 == handle+0x10, flags (+0x3C) bit 0 set when the handle's is, and, when an LSN is
#     passed, +0x18 <= it (:284324-284330). InitializeVolumeRedoLog passes the Logfile Information Table (OID 0x9) row's
#     data start LCN (value[0]) and size in clusters (value[2]) to CmsDurableLog::Start (0x1400fa751..0x1400fa796),
#     which shifts them to bytes; MlLogOpenLog stores start >> 12 and (start + size) >> 12, 4 KiB log blocks. Start
#     always sets param_9 bit 0 (0x140133403..0x14013340d) and passes &CHKP+0x70 of the checkpoint the volume is read
#     from as param_14 (Insider: param_15); 17134 passes NULL, so there is no start test on 17134. Measured on every
#     corpus MLog before these REDs (fixes/waveB_fix_evidence/part3b/n419_summary.txt): the range, flags-bit-0 and
#     start tests pass on 240 of 240 copies of 120 volumes. N419 (LB52): a copy in use that fails one of them is
#     stated -- the value read, what the driver requires -- and exits 2 in LB24's set and `timeline`'s MLog source.
#   * LB53: a record whose format magic is not the volume's belongs to an EARLIER VOLUME's log (a reformat); one with
#     the volume's signature and another UUID to an EARLIER LOG OF THIS VOLUME (MlLogOpenLog's create path draws a new
#     UUID, ExUuidCreate, :284363). The statements say which, with counts per case; `mlog --earlier-logs` (LB1's option,
#     renamed) shows both, each record labelled with its case.

# ─── N418: the control copy the driver reads ──────────────────────────────────────────────────────────────────

N418_MAGIC_HEX = "0x%08x" % MAGIC_B             # the magic planted at header +0x04 of a refused copy


def _n418_log(tmp_path, slots, dated=False):
    """`_n414_log`'s log (records 1..13 of (MAGIC_A, UUID_A); the volume's superblock at LCN 0x1e gives MAGIC_A) whose
    control copies in `slots` carry MAGIC_B at header +0x04, re-sealed: their folds verify, their magic is not the
    volume's signature."""
    log = _n414_log(tmp_path, "n418_%s%s" % ("".join(map(str, slots)) or "none", "_dated" if dated else ""),
                    supb=MAGIC_A, dated=dated)
    for i in slots:
        b = bytearray(log.ctrl[i])
        struct.pack_into("<I", b, 0x04, MAGIC_B)
        log.ctrl[i] = MC._seal(b)
    log.write()
    s = MC.read_block(log.path, 0x1E * log.cs)
    _fx(s[:4] == b"SUPB" and le32(s, 0x50) ^ le32(s, 0x54) ^ le32(s, 0x58) ^ le32(s, 0x5C) == MAGIC_A,
        "the planted superblock does not give the volume's signature 0x%08x" % MAGIC_A)
    for i in range(2):
        c = MC.parse_block(MC.read_block(log.path, (1 + i) * log.cs))
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and c["seq"] == 51 - i
            and c["magic"] == (MAGIC_B if i in slots else MAGIC_A), "control copy %d is not what the case needs" % i)
    return log


@pytest.mark.parametrize("mode", ["text", "json"])
def test_n418_a_control_copy_whose_magic_is_not_the_volumes_signature_is_never_the_copy_in_use(monkeypatch, tmp_path,
                                                                                               mode):
    """Copy 0 (sequence 51, the newer) carries another format magic: the driver refuses it, so the copy it reads -- and
    the control area shown -- is copy 1 (PLCN 0x2, sequence 50)."""
    log = _n418_log(tmp_path, (0,))
    if mode == "json":
        rc, out, err = inproc(monkeypatch, log, "mlog", "--json")
        c = _json_control(_load_json(out))
        plcn, seq = _as_int(_ci_get(c, "PLCN")), _as_int(_ci_get(c, "Sequence"))
    else:
        rc, out, err = inproc(monkeypatch, log, "mlog")
        m = re.search(r"(?m)^\s*Control PLCN:\s+(0x[0-9a-f]+)", out)
        plcn, seq = (int(m.group(1), 16) if m else None), labelled_int(out, "Sequence")
    assert (plcn, seq) == (2, 50), "copy 0's header +0x04 is %s, not the volume's signature 0x%08x (LogValidateEntryHeader " \
        "refuses it): the copy in use is copy 1 (PLCN 0x2, sequence 50); `mlog %s` shows PLCN %r, sequence %r" % (
            N418_MAGIC_HEX, MAGIC_A, mode, plcn, seq) + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", ["--stats", "--json"])
@pytest.mark.parametrize("slot", [0, 1], ids=["newer-copy-refused", "older-copy-refused"])
def test_n418_a_refused_copy_is_reported_where_redundancy_is_reported(monkeypatch, tmp_path, mode, slot):
    """The refused copy is a failed copy not in use (LB39): `--stats` and `--json` report it, naming its magic, and exit
    2."""
    rc, out, err = inproc(monkeypatch, _n418_log(tmp_path, (slot,)), "mlog", mode)
    if mode == "--stats":
        v = MC.control_verdicts(out)
        line = v.get(slot)
        ok = bool(line) and line[1] != "verified" and N418_MAGIC_HEX in (line[1] + line[2]).lower()
        what = "its `Control copy %d` line %r" % (slot, line)
    else:
        verdict = _copy_verdicts(_load_json(out)).get(1 + slot)
        said = [s for s in lb39_statements(err, (slot,)) if N418_MAGIC_HEX in s.lower()]
        ok = verdict is False and bool(said)
        what = "verdict %r; a stderr statement naming copy %d, its magic %s and that the copy in use is not affected: %s" \
            % (verdict, slot, N418_MAGIC_HEX, "found" if said else "none")
    assert rc == 2 and ok, "control copy %d carries another format magic (%s), which refs.sys refuses: `mlog %s` must " \
        "report it failed, naming the magic, and exit 2 (exit %s; LB39); %s" % (slot, N418_MAGIC_HEX, mode, rc, what) \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("-v",), ("--parse",), ("--csv",), ("--raw-scan",), ("--info",)],
                         ids=["default", "verbose", "parse", "csv", "raw-scan", "info"])
@pytest.mark.parametrize("slot", [0, 1], ids=["newer-copy-refused", "older-copy-refused"])
def test_n418_control_a_refused_copy_not_in_use_leaves_the_other_modes_at_exit_0(monkeypatch, tmp_path, mode, slot):
    """Not a RED. One copy refused, the other read: the other modes exit 0 and say nothing of the copy (V-a)."""
    rc, out, err = inproc(monkeypatch, _n418_log(tmp_path, (slot,)), "mlog", *mode)
    _keep(rc == 0 and not lb38_statements(out + "\n" + err, (slot,)),
          "`mlog %s` with one refused copy not in use" % " ".join(mode) + _ctx(rc, out, err))


@pytest.mark.parametrize("mode", _N412_MLOG_MODES, ids=_N412_MLOG_IDS)
def test_n418_both_copies_refused_is_the_no_readable_copy_condition(monkeypatch, tmp_path, mode):
    """Both copies carry another format magic: the driver reads neither (LogCoreReadControlArea fails), so the log has
    no readable control copy (N412): exit 2 in every mode, with N412's statement, which says why each copy is refused."""
    rc, out, err = inproc(monkeypatch, _n418_log(tmp_path, (0, 1)), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = [s for s in n412_statements(err if export else out) if N418_MAGIC_HEX in s.lower()]
    assert rc == 2 and said, "both control copies carry another format magic (%s): no copy is one refs.sys reads, so " \
        "`mlog %s` must exit 2 (exit %s; LB51 with LB41) and state %s that no control copy can be read, naming the " \
        "magic (statement: %s)" % (N418_MAGIC_HEX, " ".join(mode), rc, _lb38_where(export),
                                    "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--jsonl",)], ids=["text", "csv", "json", "jsonl"])
def test_n418_both_copies_refused_makes_timeline_exit_2_with_a_statement(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _n418_log(tmp_path, (0, 1), dated=True), "timeline", "--fast", *mode)
    _keep(len(_tl_mlog_rows(out, mode)) == N414_LAST, "the MLog rows are no longer listed" + _ctx(rc, out, err))
    said = [s for s in n412_statements(err if mode else out) if N418_MAGIC_HEX in s.lower()]
    assert rc == 2 and said, "both control copies carry another format magic: `timeline %s` must exit 2 (exit %s) and " \
        "state it %s (statement: %s)" % (" ".join(mode), rc, _lb38_where(bool(mode)), "found" if said else "none") \
        + _ctx(rc, out, err)


# ─── N419: MlLogOpenLog's other open tests ────────────────────────────────────────────────────────────────────

N419_CHKP_LCN = 4                    # a cluster of the synthetic image no other structure uses (control 1-2, data 16-)
N419_RANGE_END = 0x91                # planted at payload +0x10; OID 0x9 gives the data area as clusters 0x10 - 0x90
N419_CHKP_BEFORE = lsn(1, 0x20)      # a checkpoint log position before the log start END (1:0x21)


def _chkp_record(cs, lsn70, vc=7):
    """A checkpoint record as far as the open test goes: 'CHKP', the clocks at +0x10 / +0x60, the MLog LSN at +0x70,
    and one root reference (offset table at +0x94, count at +0x90, descriptor length at +0x5C) so that it parses."""
    b = bytearray(cs)
    b[0:4] = b"CHKP"
    struct.pack_into("<Q", b, 0x10, vc)
    struct.pack_into("<I", b, 0x5C, 0x30)
    struct.pack_into("<QQ", b, 0x60, vc, 0)
    struct.pack_into("<Q", b, 0x70, lsn70)
    struct.pack_into("<I", b, 0x78, 0)
    struct.pack_into("<II", b, 0x90, 1, 0x100)
    struct.pack_into("<Q", b, 0x100, 0x50)
    return bytes(b)


def _with_chkp(log, lsn70):
    with open(log.path, "r+b") as fh:
        fh.seek(N419_CHKP_LCN * log.cs)
        fh.write(_chkp_record(log.cs, lsn70))
    c = MC.read_block(log.path, N419_CHKP_LCN * log.cs, log.cs)
    _fx(c[:4] == b"CHKP" and le64(c, 0x70) == lsn70, "the planted checkpoint does not hold +0x70 = 0x%x" % lsn70)
    return log


def _n419_edit(test):
    def edit(b, p):
        if test == "range":
            struct.pack_into("<Q", b, p + 0x10, N419_RANGE_END)
        elif test == "flags":
            struct.pack_into("<I", b, p + 0x3C, le32(b, p + 0x3C) & ~1)
    return edit


def _n419_log(tmp_path, test, slots=(0, 1), dated=False, lsn70=None):
    """Records 1..0x20 (or 4 dated payloads) with log start = end; the control copies in `slots` fail the open test
    `test` -- 'range': payload +0x10 = 0x91, one block past the data area OID 0x9 gives (0x10 - 0x90); 'flags':
    payload +0x3C bit 0 clear; 'start': the planted checkpoint's +0x70 is one below the log start (both copies), or,
    when the checkpoint is not before it (`slots` = (1,)), those copies' log start is moved one past it. Re-sealed; a
    checkpoint record is planted at LCN 4 (+0x70 = `lsn70`: by default the log start, one below it for 'start')."""
    name = "n419_%s_%s%s" % (test, "".join(map(str, slots)), "_dated" if dated else "")
    if dated:
        log = SynLog(tmp_path / (name + ".raw"))
        for k in range(1, 5):
            log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                          [[redo_rec(0x04, 3, 0, FT_A + k)]])
        start = lsn(1, 5)
    else:
        log = SynLog(tmp_path / (name + ".raw")).run(1, 0x20, 1, session_start=True)
        start = END
    log.control(start, start)
    if lsn70 is None:
        lsn70 = start - 1 if (test == "start" and tuple(slots) == (0, 1)) else start
    for i in slots:
        b = bytearray(log.ctrl[i])
        p = _payload_at(b)
        if test != "start":
            _n419_edit(test)(b, p)
        elif lsn70 >= start:                # the checkpoint is not before the log start: move this copy's start past it
            struct.pack_into("<Q", b, p + 0x18, lsn70 + 1)
        log.ctrl[i] = MC._seal(b)
    log.write()
    _with_chkp(log, lsn70)
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs)
        c, p = MC.parse_block(blk), _payload_at(blk)
        bad = {"range": le64(blk, p + 0x10) == N419_RANGE_END, "flags": not le32(blk, p + 0x3C) & 1,
               "start": le64(blk, p + 0x18) > lsn70}[test]
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and bad == (i in slots),
            "control copy %d is not what the case needs" % i)
    return log


def _inproc_chkp(monkeypatch, log, cmd, *args):
    """`inproc`, with the patched bootstrap returning the planted checkpoint (LCN 4) as the superblock's list, so the
    tool's own checkpoint selection reads it."""
    calls = Counter()

    def _boot(image, partition_start=None):
        calls["bootstrap"] += 1
        return open(log.path, "rb"), 0, log.cs, MC._IdentityTr(), [], {}, 3, 14, [N419_CHKP_LCN]

    def _info(f, ps, cs, tr, obj_map):
        calls["get_mlog_info"] += 1
        return dict(log.info)

    monkeypatch.setattr(F, "bootstrap", _boot)
    monkeypatch.setattr(F, "get_mlog_info", _info)
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: {})
    _fresh_registers(monkeypatch)
    for name in _EXTRA_REGS:
        cur = getattr(F, name, None)
        if isinstance(cur, (list, dict)):
            monkeypatch.setattr(F, name, type(cur)())
    fn = {"mlog": F.cmd_mlog, "timeline": F.cmd_timeline}[cmd]
    out, err = io.StringIO(), io.StringIO()
    exited = None
    try:
        with UW.recording() as wrapped, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn(log.path, list(args), None)
    except SystemExit as e:
        exited = e.code
    except Exception:
        raise RedFixtureError("%s %s crashed (a crash is never the defect under test):\n%s"
                              % (cmd, " ".join(args), traceback.format_exc()))
    o, e = UW.unwrap_exact(out.getvalue(), wrapped), err.getvalue()
    if exited is not None:                  # as `inproc`: only an unknown option may exit before the volume is read
        _fx(calls["bootstrap"] == 0 and "unknown option" in e,
            "%s %s exited through die() (%r) for another reason:\n%s" % (cmd, " ".join(args), exited, e[-2000:]))
        return exited, o, e
    _fx(calls["bootstrap"] == 1 and calls["get_mlog_info"] >= 1,
        "%s no longer reaches the patched volume layer (%r)" % (cmd, dict(calls)))
    return _rc_escalate()(0 if rc is None else rc), o, e


def _hexnum(n):
    """`n` written in hex (0x..., any padding) or in decimal."""
    return re.compile(r"(?i)(?<![0-9a-fx])(?:0x0*%x|%d)(?![0-9a-f])" % (n, n))


_N419_FIELD = {"range": re.compile(r"(?i)\bdata\s+(?:area|range)\b|\+0x0?8\b|\+0x10\b|\brange\b"),
               "flags": re.compile(r"(?i)\bflags?\b|\+0x3c\b"),
               "start": re.compile(r"(?i)\blog\s+start\b|\+0x18\b")}


def n419_statements(text, test, lsn70=N419_CHKP_BEFORE, start=END):
    """A line and the next two of its paragraph: the control area named, the open test's field with the value read
    and what the driver requires, and that the driver would not open this log. 'range': the payload's end 0x91 and
    the data area's end 0x90 that OID 0x9 gives; 'flags': bit 0; 'start': the log start (`start`) and the
    checkpoint's +0x70 (`lsn70`)."""
    need = {"range": [_hexnum(N419_RANGE_END), _hexnum(SynLog.DS + SynLog.NBLK)],
            "flags": [re.compile(r"(?i)\bbit\s*0\b")],
            "start": [MC.lsn_re(start), MC.lsn_re(lsn70)]}[test]
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if (re.search(r"(?i)\bcontrol\b|\bMLog\b", w) and _N419_FIELD[test].search(w)
                    and all(r.search(w) for r in need) and _N415_REFUSE.search(w)):
                hits.append(w)
    return hits


_N419_TESTS = ["range", "flags", "start"]


@pytest.mark.parametrize("mode", _N412_MLOG_MODES, ids=_N412_MLOG_IDS)
@pytest.mark.parametrize("test", _N419_TESTS)
def test_n419_a_copy_in_use_the_driver_would_not_open_makes_every_mlog_mode_exit_2_with_a_statement(monkeypatch,
                                                                                                     tmp_path, test,
                                                                                                     mode):
    rc, out, err = _inproc_chkp(monkeypatch, _n419_log(tmp_path, test), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = n419_statements(err if export else out, test)
    assert rc == 2 and said, "the copy in use fails MlLogOpenLog's %s test, so refs.sys would not open this log: " \
        "`mlog %s` must exit 2 (exit %s; LB52) and state %s the value read, what the driver requires and that it would " \
        "not open this log (statement: %s)" % (test, " ".join(mode), rc, _lb38_where(export),
                                               "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--jsonl",)], ids=["text", "csv", "json", "jsonl"])
@pytest.mark.parametrize("test", _N419_TESTS)
def test_n419_a_copy_in_use_the_driver_would_not_open_makes_timeline_exit_2_with_a_statement(monkeypatch, tmp_path,
                                                                                              test, mode):
    log = _n419_log(tmp_path, test, dated=True)
    rc, out, err = _inproc_chkp(monkeypatch, log, "timeline", "--fast", *mode)
    _keep(len(_tl_mlog_rows(out, mode)) == 4, "the MLog rows are no longer listed (LB52 states the condition; it does "
          "not drop the rows)" + _ctx(rc, out, err))
    said = n419_statements(err if mode else out, test, lsn70=lsn(1, 5) - 1, start=lsn(1, 5))
    assert rc == 2 and said, "the copy in use fails MlLogOpenLog's %s test: `timeline %s` must exit 2 (exit %s; LB52) " \
        "and state it %s (statement: %s)" % (test, " ".join(mode), rc, _lb38_where(bool(mode)),
                                              "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--parse",), ("--csv",), ("--info",)], ids=["default", "parse", "csv", "info"])
@pytest.mark.parametrize("test", _N419_TESTS)
def test_n419_control_a_copy_not_in_use_failing_an_open_test_is_not_the_condition(monkeypatch, tmp_path, test, mode):
    """Not a RED. Only copy 1 (sequence 50, not in use) fails the test: MlLogOpenLog tests the copy it read, the copy
    in use, so the log opens -- exit 0, no statement."""
    rc, out, err = _inproc_chkp(monkeypatch, _n419_log(tmp_path, test, slots=(1,)), "mlog", *mode)
    # N554 (1.14.0): `--info`'s generated opcode reference says which driver builds refuse opcode 0x2d -- a fact about
    # the builds, not a statement about this log -- so the reference (REDO OPCODES .. TIMESTAMPS) is left out of the search
    text = re.sub(r"(?s)REDO OPCODES \(generated.*?\nTIMESTAMPS\n", "", out + "\n" + err)
    _keep(rc == 0 and not _N415_REFUSE.search(text), "`mlog %s` with only the copy not in use failing the "
          "%s test" % (" ".join(mode), test) + _ctx(rc, out, err))


def test_n419_control_a_log_start_at_the_checkpoints_position_opens(monkeypatch, tmp_path):
    """Not a RED. The test is `+0x18 <= CHKP+0x70`: a log start equal to the checkpoint's position opens (exit 0)."""
    log = _n419_log(tmp_path, "start", slots=(), lsn70=END)
    rc, out, err = _inproc_chkp(monkeypatch, log, "mlog", "--stats")
    _keep(rc == 0 and not n419_statements(out + "\n" + err, "start", lsn70=END), "log start == CHKP+0x70" +
          _ctx(rc, out, err))


@pytest.mark.parametrize("unit", ["blocks", "clusters"])
def test_n419_the_data_range_of_a_64k_log_is_compared_in_4k_blocks(monkeypatch, tmp_path, unit):
    """On a 64 KiB volume the handle's range is OID 0x9's start and start + size, in clusters, times 16 (MlLogOpenLog:
    bytes >> 12). A payload holding the range in 4 KiB blocks (as on the 7 corpus 64K volumes) opens; one holding it in
    clusters does not -- stated, exit 2 (the RED); the blocks case is its control."""
    log = SynLog(tmp_path / ("n419_64k_%s.raw" % unit), 0x10000).run(1, 0x20, 1, session_start=True)
    k = log.bpc if unit == "blocks" else 1
    log.ctrl = [MC.control_block(MAGIC_A, UUID_A, s, log.DS * k, log.de * k, END, END, 3) for s in (51, 50)]
    log.write()
    _with_chkp(log, END)
    rc, out, err = _inproc_chkp(monkeypatch, log, "mlog")
    said = [w for w in re.split(r"\n\s*\n", out) if re.search(r"(?i)\bcontrol\b", w) and _N419_FIELD["range"].search(w)
            and _hexnum(log.de).search(w) and _hexnum(log.de * log.bpc).search(w) and _N415_REFUSE.search(w)] \
        if unit == "clusters" else None
    if unit == "blocks":
        _keep(rc == 0 and not re.search(r"(?i)would\s+not\s+open", out + err), "a 64K payload range in 4 KiB blocks"
              + _ctx(rc, out, err))
    else:
        assert rc == 2 and said, "the 64K payload range is in clusters (0x%x - 0x%x), the driver's handle in 4 KiB blocks " \
            "(0x%x - 0x%x): `mlog` must exit 2 (exit %s) and state it (statement: %s)" % (
                log.DS, log.de, log.DS * log.bpc, log.de * log.bpc, rc, "found" if said else "none") \
            + _ctx(rc, out, err)


# ─── LB53: two cases, one option ──────────────────────────────────────────────────────────────────────────────

UUID_C = uuid.UUID("3c3c3c3c-0000-4000-8000-00000000000c").bytes_le          # an earlier log of this volume
UUID_C_STR = str(uuid.UUID(bytes_le=UUID_C))
N_LB53_VOL, N_LB53_LOG = 5, 7
LB53_VOL_K = list(range(0x21, 0x21 + N_LB53_VOL))                            # an earlier volume's log (MAGIC_B/UUID_B)
LB53_LOG_K = list(range(0x26, 0x26 + N_LB53_LOG))                            # an earlier log of this volume (MAGIC_A/UUID_C)
_CASE_VOL = re.compile(r"(?i)\bearlier\s+volume")
_CASE_THIS = re.compile(r"(?i)\bthis\s+volume")


def _lb53_log(tmp_path):
    """This log: records 1..0x20 (MAGIC_A, UUID_A, generation 1). An earlier volume's log: 5 records at blocks
    0x21..0x25 (MAGIC_B, UUID_B, generation 2). An earlier log of this volume: 7 records at 0x26..0x2c (the volume's
    MAGIC_A with UUID_C, generation 3). No superblock is read here, so the volume's magic is the control header's
    (MAGIC_A), as for LB1's uuid-only log."""
    log = SynLog(tmp_path / "lb53.raw").run(1, 0x20, 1, session_start=True)
    for k in LB53_VOL_K:
        log.blocks[k] = MC.data_block(MAGIC_B, UUID_B, 3, lsn(2, k), lsn(2, k - 1) if k > LB53_VOL_K[0] else 0)
    for k in LB53_LOG_K:
        log.blocks[k] = MC.data_block(MAGIC_A, UUID_C, 3, lsn(3, k), lsn(3, k - 1) if k > LB53_LOG_K[0] else 0)
    log.control(END, END).write()
    for ks, magic, uid in ((LB53_VOL_K, MAGIC_B, UUID_B), (LB53_LOG_K, MAGIC_A, UUID_C)):
        for k in ks:
            c = MC.parse_block(MC.read_block(log.path, log.block_off(k)))
            _fx(c and c["type"] == 2 and c["magic"] == magic and c["uuid"] == uid and c["fold"] == c["stored"],
                "block %#x is not the earlier record the case needs" % k)
    return log


def _lb53_dated_log(tmp_path):
    """This log: 4 dated payloads (generation 1). An earlier volume's log: 3 dated payloads (MAGIC_B / UUID_B). An
    earlier log of this volume: 2 dated payloads and 1 undated (MAGIC_A / UUID_C) -- 3 and 2 rows `timeline` would have
    printed."""
    log = SynLog(tmp_path / "lb53_dated.raw")
    for k in range(1, 5):
        log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_A + k)]])
    for k in range(5, 8):
        log.blocks[k] = payload_block(MAGIC_B, UUID_B, 7, lsn(2, k), lsn(2, k - 1) if k > 5 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_B + k)]])
    for k in range(8, 10):
        log.blocks[k] = payload_block(MAGIC_A, UUID_C, 9, lsn(3, k), lsn(3, k - 1) if k > 8 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_B + k)]])
    log.blocks[10] = payload_block(MAGIC_A, UUID_C, 9, lsn(3, 10), lsn(3, 9), [[redo_rec(0x03)]])
    return log.control(lsn(1, 5), lsn(1, 5)).write()


def _count_case(n, case, unit_words):
    """`n` given as a number of `case`'s records/rows: '<n> [unit] of an earlier volume's log' or '<n> [unit] of an
    earlier log of this volume'."""
    phrase = r"an?\s+earlier\s+volume'?s\s+log" if case == "volume" else r"an?\s+earlier\s+log\s+of\s+this\s+volume"
    return re.compile(r"(?i)(?<![0-9a-fx])%d\s+(?:(?:%s)\s+)?(?:of|from|belong\w*\s+to)\s+%s" % (n, unit_words, phrase))


_UNIT_WORDS_RECORDS = r"(?:log\s+)?(?:records?|record\(s\))"
_UNIT_WORDS_ROWS = r"(?:MLog\s+)?(?:rows?|row\(s\))"


def lb53_case_statements(text, n, case, unit_words, unit):
    """LB53: statements (a line or a two-line window) that give `n` as the number of `case`'s records/rows ('volume':
    an earlier volume's log; 'log': an earlier log of this volume), name the unit, and name `--earlier-logs`."""
    lines = text.splitlines()
    hits = []
    for i in range(len(lines)):
        for blob in (lines[i], " ".join(lines[i:i + 2])):
            if "--earlier-logs" in blob and unit.search(blob) and _count_case(n, case, unit_words).search(blob):
                hits.append(blob)
                break
    return hits


@pytest.mark.parametrize("mode", _LB1_MODES, ids=_LB1_IDS)
def test_lb53_mlog_states_each_case_with_its_own_count(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _lb53_log(tmp_path), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    text = err if export else out + "\n" + err
    vol = lb53_case_statements(text, N_LB53_VOL, "volume", _UNIT_WORDS_RECORDS, _UNIT_RECORDS)
    this = lb53_case_statements(text, N_LB53_LOG, "log", _UNIT_WORDS_RECORDS, _UNIT_RECORDS)
    misnamed = [ln for ln in text.splitlines() if _count_case(N_LB53_LOG, "volume", _UNIT_WORDS_RECORDS).search(ln)]
    assert vol and this and not misnamed, "`mlog %s`: %d records carry another format magic (an earlier volume's log) " \
        "and %d this volume's signature with another UUID (an earlier log of this volume): each count is stated with its " \
        "case and `mlog --earlier-logs` (LB53) -- earlier volume: %s; earlier log of this volume: %s; the %d named an " \
        "earlier volume's: %r" % (" ".join(mode), N_LB53_VOL, N_LB53_LOG, "found" if vol else "none",
                                  "found" if this else "none", N_LB53_LOG, misnamed[:2]) + _ctx(rc, out, err)
    _keep(rc == 0, "earlier logs are not a finding (Q1 A): exit %d" % rc)


@pytest.mark.parametrize("mode", [(), ("--csv",)], ids=["text", "csv"])
def test_lb53_timeline_states_each_case_in_rows(monkeypatch, tmp_path, mode):
    rc, out, err = inproc(monkeypatch, _lb53_dated_log(tmp_path), "timeline", "--fast", *mode)
    text = err if mode else out + "\n" + err
    vol = lb53_case_statements(text, 3, "volume", _UNIT_WORDS_ROWS, _UNIT_ROWS)
    this = lb53_case_statements(text, 2, "log", _UNIT_WORDS_ROWS, _UNIT_ROWS)
    _keep(len(_timeline_mlog_rows(out, bool(mode))) == 4 and rc == 0, "timeline lists this log's 4 rows, exit 0"
          + _ctx(rc, out, err))
    assert vol and this, "`timeline %s`: 3 rows of an earlier volume's log and 2 of an earlier log of this volume are " \
        "left out; each count is stated in rows with its case and `mlog --earlier-logs` (LB53): %s / %s" % (
            " ".join(mode), "found" if vol else "none", "found" if this else "none") + _ctx(rc, out, err)


def test_lb53_mlog_json_counts_each_case(monkeypatch, tmp_path):
    """The JSON says which case each earlier log is, with its count: an object holding 5 and an earlier volume's label,
    another holding 7 and this volume's label."""
    rc, out, err = inproc(monkeypatch, _lb53_log(tmp_path), "mlog", "--json")
    j = _load_json(out)

    def labelled(n, case):
        for d in _dicts(j):
            vals = list(d.values())
            words = " ".join(v for v in vals if isinstance(v, str))
            if n in [v for v in vals if isinstance(v, int) and not isinstance(v, bool)] and (
                    (_CASE_VOL.search(words) and not _CASE_THIS.search(words)) if case == "volume"
                    else (_CASE_THIS.search(words) and not _CASE_VOL.search(words))):
                return d
        return None
    vol, this = labelled(N_LB53_VOL, "volume"), labelled(N_LB53_LOG, "log")
    assert vol and this, "mlog --json: no object gives the %d records of an earlier volume's log (%r) and the %d of an " \
        "earlier log of this volume (%r) with their case (LB53)" % (N_LB53_VOL, vol, N_LB53_LOG, this)


def _lb53_clusters(log):
    return {log.cluster_of(k) for k in LB53_VOL_K}, {log.cluster_of(k) for k in LB53_LOG_K}


def _case_of(text, vol_set, this_set, plcn):
    """'volume' / 'log' when `text` labels the record at `plcn` as its case requires, else what is wrong."""
    want = "volume" if plcn in vol_set else "log"
    ok = (_CASE_VOL.search(text) and not _CASE_THIS.search(text)) if want == "volume" else \
        (_CASE_THIS.search(text) and not _CASE_VOL.search(text))
    return None if ok else (hex(plcn), want, text.strip()[:160])


def _parse_v_blocks(text):
    """`mlog --parse -v` row blocks: a `  [ACTION]` row line and the lines after it up to a blank line."""
    blocks, cur = [], None
    for ln in text.splitlines():
        if re.match(r"^  \[[^\]]+\]", ln) and not re.match(r"^  \[CLASS\] is DERIVED", ln):   # P8's legend line
            cur = [ln]
            blocks.append(cur)
        elif cur is not None and ln.strip():
            cur.append(ln)
        else:
            cur = None
    return ["\n".join(b) for b in blocks]


@pytest.mark.parametrize("form", ["csv", "json", "raw-scan", "parse-v", "verbose"])
def test_lb53_earlier_logs_labels_each_record_with_its_case(monkeypatch, tmp_path, form):
    log = _lb53_log(tmp_path)
    vol_set, this_set = _lb53_clusters(log)
    args = {"csv": ("--csv",), "json": ("--json",), "raw-scan": ("--raw-scan",), "parse-v": ("--parse", "-v"),
            "verbose": ("-v",)}[form]
    rc, out, err = inproc(monkeypatch, log, "mlog", "--earlier-logs", *args)
    assert not (rc == 1 and "unknown option" in err), "`mlog --earlier-logs` is not an option (LB53 renames LB1's " \
        "`--earlier-volume`)" + _ctx(rc, out, err)
    items = []                                       # (plcn, the text that labels it)
    if form == "csv":
        hdr, rows, _at = csv_table(out)
        pc = _col(hdr, r"(?i)^plcn$")
        items = [(_as_int(r[pc]), " ".join(r)) for r in rows]
    elif form == "json":
        for d in _dicts(_load_json(out)):
            pl = _as_int(_ci_get(d, "plcn"))
            if pl in vol_set | this_set and (_ci_get(d, "opcode") is not None or _ci_get(d, "action") is not None):
                items.append((pl, " ".join(str(v) for v in d.values() if isinstance(v, str))))
    elif form == "raw-scan":
        items = [(p, ln) for p, ln in _raw_rows(out) if p in vol_set | this_set]
    elif form == "parse-v":
        for b in _parse_v_blocks(out):
            pls = set(_parse_v_plcns(b))
            _fx(len(pls) == 1, "a --parse -v row names %d PLCNs: %r" % (len(pls), b[:200]))
            items.append((pls.pop(), b))
    else:
        for ln in _section(out, "LogCore Record Headers"):
            m = re.match(r"^\s+(0x[0-9a-f]+)\.blk\d+\s", ln)
            if m:
                items.append((int(m.group(1), 16), ln))
    got = {p for p, _t in items}
    _keep(got == vol_set | this_set, "`mlog --earlier-logs %s` lists records at %r; the earlier logs' are at %r" % (
        " ".join(args), sorted(hex(p) for p in got), sorted(hex(p) for p in vol_set | this_set)) + _ctx(rc, out, err))
    bad = [x for x in (_case_of(t, vol_set, this_set, p) for p, t in items) if x]
    assert not bad, "`mlog --earlier-logs %s`: records not labelled with their case (an earlier volume's log / an " \
        "earlier log of this volume; LB53): %r" % (" ".join(args), bad[:3])


def test_lb53_the_option_is_named_earlier_logs(monkeypatch, tmp_path):
    """LB53 replaces LB1's `--earlier-volume` (nothing is published yet): the old name is an unknown option."""
    rc, out, err = inproc(monkeypatch, _lb53_log(tmp_path), "mlog", "--earlier-volume")
    assert rc == 1 and "unknown option" in err, "`mlog --earlier-volume` is still accepted (exit %s): the option is " \
        "`--earlier-logs` (LB53)" % rc + _ctx(rc, out, err)


def test_n418_n419_lb53_matchers_accept_a_sound_output_and_reject_others():
    """The readers of the N418 / N419 / LB53 REDs: each accepts a sound form and rejects what it must refuse."""
    rng = ("MLog control copy 0 (PLCN 0x1, sequence 51), the copy in use, gives the data area as log blocks 0x10 - 0x91 "
           "(payload +0x08/+0x10); refs.sys opens a log only when they equal the range OID 0x9 gives, 0x10 - 0x90, so "
           "it would not open this one.")
    assert n419_statements(rng, "range") and not n419_statements(rng.replace("0x91", "0x90", 1), "range")
    assert not n419_statements(rng.replace("so it would not open this one", "it opens it"), "range")
    flg = ("MLog control copy 0 (PLCN 0x1), the copy in use, holds log flags 0x0 at payload +0x3C, bit 0 clear; refs.sys "
           "opens a log only when bit 0 is set, so it would not open this one.")
    assert n419_statements(flg, "flags") and not n419_statements(flg.replace("bit 0", "bit 1"), "flags")
    st = ("MLog control copy 0, the copy in use, holds log start 0x0000000100000021 (generation 1, offset 0x21) at "
          "payload +0x18, past the checkpoint's position 0x0000000100000020 (CHKP +0x70); refs.sys 26100 would not open "
          "this one.")
    assert n419_statements(st, "start") and not n419_statements(st.replace("0x0000000100000020", "0x0000000100000022"),
                                                                "start")
    s5 = "  5 log record(s) of an earlier volume's log are left out (format magic 0x6d790647); `mlog --earlier-logs` shows them"
    s7 = "  7 log record(s) of an earlier log of this volume are left out (UUID ...); `mlog --earlier-logs` shows them"
    assert lb53_case_statements(s5, 5, "volume", _UNIT_WORDS_RECORDS, _UNIT_RECORDS)
    assert lb53_case_statements(s7, 7, "log", _UNIT_WORDS_RECORDS, _UNIT_RECORDS)
    assert not lb53_case_statements(s7, 7, "volume", _UNIT_WORDS_RECORDS, _UNIT_RECORDS)
    assert not lb53_case_statements(s5.replace("--earlier-logs", "--earlier-volume"), 5, "volume", _UNIT_WORDS_RECORDS,
                                    _UNIT_RECORDS)
    both = ("  12 log record(s) of earlier logs are left out: 5 of an earlier volume's log (...) and 7 of an earlier log "
            "of this volume (...); `mlog --earlier-logs` shows them")
    assert lb53_case_statements(both, 5, "volume", _UNIT_WORDS_RECORDS, _UNIT_RECORDS) and \
        lb53_case_statements(both, 7, "log", _UNIT_WORDS_RECORDS, _UNIT_RECORDS)
    tl = "  3 MLog row(s) of an earlier volume's log are left out; `mlog --earlier-logs` shows them"
    assert lb53_case_statements(tl, 3, "volume", _UNIT_WORDS_ROWS, _UNIT_ROWS)
    assert not lb53_case_statements(tl, 3, "volume", _UNIT_WORDS_RECORDS, _UNIT_RECORDS)
    assert _case_of("0x31.blk0 MLog ... (an earlier volume's log)", {0x31}, set(), 0x31) is None
    assert _case_of("0x31.blk0 MLog ... (an earlier log of this volume)", {0x31}, set(), 0x31)
    assert _case_of("x,y,0x36,this volume", set(), {0x36}, 0x36) is None
    assert _case_of("x,y,0x36,earlier volume", set(), {0x36}, 0x36)
    assert _hexnum(0x91).search("0x91") and _hexnum(0x91).search("145") and not _hexnum(0x91).search("0x910")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N421 (LB57; wave B part 3c, written first, before the fix): the MLog open path, closed by a table
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# The table of EVERY test on the driver's path from InitializeVolumeRedoLog to MlLogOpenLog -- 26100.8115 with the
# 17134 / 26100.9444 / Insider 29574 differences, each row with the tool's state, the corpus measurement and the
# decision -- is in `analysis/reports/v1.13.2/fixes/FIX_GB_part3c.md` ("THE TABLE"). Measured on every corpus MLog
# before these REDs (fixes/waveB_fix_evidence/part3c/n421_summary.txt): 240 of 240 control copies and 120 of 120
# Logfile Information rows pass every test. These REDs cover the rows the tool did not apply before this part
# (26100.8115 refs_win11.decomp.c line numbers):
#   * InitializeVolumeRedoLog (:208070-208160) opens the Logfile Information Table as the failover pair OID 0xA /
#     OID 0x9 -- MsCreateDurableFailoverTableObject (:66532) looks up both object records and fails without either --
#     reads its row with the 4-byte key 1 (FindRow; not found: the error is returned), refuses a value shorter than
#     0x30 bytes or a value[2] (the log's size in clusters, signed) below 0x50 (0xC0000032), and hands Start value[0]
#     and value[2] -- never value[1] -- so the data area is [value[0], value[0] + value[2]). Start shifts value[2] by
#     the cluster shift in 64 bits; MlLogOpenLog refuses a size in bytes that is not more than 0x2000 (signed) or not
#     4 KiB-aligned (:284255, 0xC000000D). A failed test: stated and exit 2 in LB24's set and `timeline`'s MLog source.
#   * LogCoreReadControlArea (:301803-301826) reads both copies at value[3] / value[4], 0 included (block 0), and takes
#     copy 1 when copy 0 fails, or when copy 0's payload flags bit 1 is clear and copy 1's is set or copy 0's sequence
#     is lower; else copy 0.
#   * LogReadControlRecord (:134105) reads a control record as one 4 KiB block (handle+0xE50 x +0xE54 = 0x1000 bytes)
#     and folds those 4 KiB (LogVerifyChecksumEntryHeader(handle, 0x1000, ...) -> LogChecksumBlock over 0x1000 bytes,
#     17134 :LogChecksumBlock shows the length argument).
#   * LogValidateEntryHeader (:134424-134478; read size 0x1000, the log not open yet, so its instance tests do not
#     apply): +0x0C == 0x1000; +0x54 >= 0x78; +0x54 <= (u32)(+0x38 x 0x1000); +0x3C <= +0x38; (u32)(0x1000 x +0x3C)
#     <= 0x1000 (0xC03D0201); +0x54 <= 0x1000 (not on 17134). A copy failing one is refused before its fold, as N418's
#     magic is: never the copy in use; a failed copy where redundancy is reported (LB39); N412 when both fail.

N421_ROOT = {0x9: 0x90009, 0xA: 0x9000A}       # fake root VLCNs of OIDs 0x9 / 0xA in the patched Object Table
N421_NAME_ROW = (struct.pack("<I", 0), b"Logfile Information Table")      # row 0: a 4-byte key and 25 bytes, as on
#                                                                           120 of 120 corpus tables
N421_SMALL = 0x4F                              # a log size InitializeVolumeRedoLog refuses (it needs > 0x4f clusters)
N421_HUGE = 1 << 51                            # value[2] passing that test whose bytes (<< 12, 64-bit) are negative
N421_END_LCN = SynLog.DS + 0x20                # value[1] = the cluster of record 0x20: the data area cut one short
_N421_ROW_CASES = ["table", "norow", "short", "size", "overflow"]


def _n421_row(log, size=None, end=None, length=0x30):
    """Row 1 of the Logfile Information Table for `log`: value[0] data start, [1] end LCN, [2] size in clusters,
    [3] / [4] the control copies (clusters 1 and 2), [5] 0 -- 48 bytes, as on 120 of 120 corpus rows, or the first
    `length` bytes."""
    v = struct.pack("<6Q", log.DS, log.de if end is None else end, (log.de - log.DS) if size is None else size, 1, 2, 0)
    return struct.pack("<I", 1), v[:length]


def _n421_table(log, case):
    """(the OIDs the Object Table holds, the Logfile Information Table's rows) of `case`: 'intact'; 'table' -- OID 0xA
    missing; 'norow' -- no row 1; 'short' -- a 40-byte row 1; 'size' -- 0x4F clusters; 'overflow' -- 1 << 51 clusters;
    'end-lcn' -- value[1] the cluster of record 0x20 (the data area runs on to start + size)."""
    row = {"short": _n421_row(log, length=40), "size": _n421_row(log, size=N421_SMALL),
           "overflow": _n421_row(log, size=N421_HUGE), "end-lcn": _n421_row(log, end=N421_END_LCN)}.get(
        case, _n421_row(log))
    _fx(case in ("intact", "end-lcn") or case in _N421_ROW_CASES, "unknown row case %r" % case)
    return ([0x9] if case == "table" else [0x9, 0xA]), [N421_NAME_ROW] + ([] if case == "norow" else [row])


def _inproc_rows(monkeypatch, log, case, cmd, *args):
    """`inproc` with the REAL `get_mlog_info`: the patched bootstrap's Object Table holds `case`'s OIDs (fake root
    VLCNs) and `walk_bplus` returns the Logfile Information Table rows for them; any other walk is a fixture error.
    Everything from the row on is the tool's own code."""
    oids, rows = _n421_table(log, case)
    by_root = {N421_ROOT[o]: rows for o in oids}
    calls = Counter()
    real_info = F.get_mlog_info

    def _boot(image, partition_start=None):
        calls["bootstrap"] += 1
        return open(log.path, "rb"), 0, log.cs, MC._IdentityTr(), [], {o: [N421_ROOT[o]] for o in oids}, 3, 14, []

    def _info(*a, **k):
        calls["get_mlog_info"] += 1
        return real_info(*a, **k)

    def _walk(f, ps, cs, tr, vlcns, *a, **k):
        root = list(vlcns)[0] if list(vlcns) else None
        if root not in by_root:
            raise RedFixtureError("an unexpected table walk (root %r): adapt _inproc_rows" % (root,))
        calls["walk"] += 1
        return [(bytes(kd), bytes(vd)) for kd, vd in by_root[root]]

    monkeypatch.setattr(F, "bootstrap", _boot)
    monkeypatch.setattr(F, "get_mlog_info", _info)
    monkeypatch.setattr(F, "walk_bplus", _walk)
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: {})
    _fresh_registers(monkeypatch)
    for name in _EXTRA_REGS:
        cur = getattr(F, name, None)
        if isinstance(cur, (list, dict)):
            monkeypatch.setattr(F, name, type(cur)())
    fn = {"mlog": F.cmd_mlog, "timeline": F.cmd_timeline}[cmd]
    out, err = io.StringIO(), io.StringIO()
    try:
        with UW.recording() as wrapped, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn(log.path, list(args), None)
    except SystemExit as e:
        raise RedFixtureError("%s %s exited through die() (%r):\n%s" % (cmd, " ".join(args), e.code,
                                                                        err.getvalue()[-2000:]))
    except Exception:
        raise RedFixtureError("%s %s crashed (a crash is never the defect under test):\n%s"
                              % (cmd, " ".join(args), traceback.format_exc()))
    _fx(calls["bootstrap"] == 1 and calls["get_mlog_info"] >= 1 and calls["walk"] >= 1,
        "%s no longer reads the Logfile Information Table through the patched layer (%r)" % (cmd, dict(calls)))
    return _rc_escalate()(0 if rc is None else rc), UW.unwrap_exact(out.getvalue(), wrapped), err.getvalue()


def _n421_dated_log(tmp_path, name):
    """4 dated payloads (blocks 1..4, generation 1), log start = end = 1:5, as `_n412_dated_log`'s intact log."""
    log = SynLog(tmp_path / ("n421_dated_%s.raw" % name))
    for k in range(1, 5):
        log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                      [[redo_rec(0x04, 3, 0, FT_A + k)]])
    return log.control(lsn(1, 5), lsn(1, 5)).write()


_N421_TABLE_NAMED = re.compile(r"(?i)\blogfile\s+information\b|\bOID\s+0x0*9\b")
_N421_ROW_NEED = {
    "table": [re.compile(r"(?i)\b(?:no|not)\b[^.;\n]{0,40}\bOID\s+0x0*a\b"          # the copy that is not found
                         r"|\bOID\s+0x0*a\b[^.;\n]{0,40}\b(?:missing|not\s+found|absent)\b")],
    "norow": [re.compile(r"(?i)\b(?:row|key)\s+(?:with\s+(?:the\s+)?key\s+)?1\b")],  # row 1 / key 1
    "short": [_hexnum(40), _hexnum(0x30)],                                          # the length read; the minimum
    "size": [_hexnum(N421_SMALL), _hexnum(0x50)],                                   # the size read; the minimum
    "overflow": [_hexnum(N421_HUGE), re.compile(r"(?i)\b8\s*KiB\b|(?<![0-9a-fx])0x0*2000(?![0-9a-f])|\b8192\b")],
}


def n421_row_statements(text, case):
    """A line and the next two of its paragraph: the Logfile Information Table (or OID 0x9) named, `case`'s values --
    the copy not found, row 1, the length or the size read and what the driver requires -- and that the driver would
    not open the log (N415's reader)."""
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if (_N421_TABLE_NAMED.search(w) and all(r.search(w) for r in _N421_ROW_NEED[case])
                    and _N415_REFUSE.search(w)):
                hits.append(w)
    return hits


# ─── N421: the Logfile Information Table and its row 1 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", _N412_MLOG_MODES, ids=_N412_MLOG_IDS)
@pytest.mark.parametrize("case", _N421_ROW_CASES)
def test_n421_a_logfile_row_the_driver_refuses_makes_every_mlog_mode_exit_2_with_a_statement(monkeypatch, tmp_path,
                                                                                              case, mode):
    log = SynLog(tmp_path / ("n421_row_%s.raw" % case)).run(1, 0x20, 1, session_start=True).control(END, END).write()
    rc, out, err = _inproc_rows(monkeypatch, log, case, "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = n421_row_statements(err if export else out, case)
    assert rc == 2 and said, "the Logfile Information Table fails InitializeVolumeRedoLog's %s test, so refs.sys would " \
        "not open this log: `mlog %s` must exit 2 (exit %s; LB57) and state %s what was read, what the driver requires " \
        "and that it would not open the log (statement: %s)" % (case, " ".join(mode), rc, _lb38_where(export),
                                                               "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--jsonl",)], ids=["text", "csv", "json", "jsonl"])
@pytest.mark.parametrize("case", _N421_ROW_CASES)
def test_n421_a_logfile_row_the_driver_refuses_makes_timeline_exit_2_with_a_statement(monkeypatch, tmp_path, case,
                                                                                       mode):
    rc, out, err = _inproc_rows(monkeypatch, _n421_dated_log(tmp_path, case), case, "timeline", "--fast", *mode)
    if case != "norow":                 # with no row 1 the log cannot be located; otherwise its rows are still listed
        _keep(len(_tl_mlog_rows(out, mode)) == 4, "the MLog rows are no longer listed (LB57 states the condition; it "
              "does not drop the rows)" + _ctx(rc, out, err))
    said = n421_row_statements(err if mode else out, case)
    assert rc == 2 and said, "the Logfile Information Table fails InitializeVolumeRedoLog's %s test: `timeline %s` must " \
        "exit 2 (exit %s; LB57) and state it %s (statement: %s)" % (case, " ".join(mode), rc, _lb38_where(bool(mode)),
                                                                   "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("cmd,mode", [("mlog", ()), ("mlog", ("--stats",)), ("mlog", ("--json",)), ("timeline", ())],
                         ids=["mlog", "mlog-stats", "mlog-json", "timeline"])
def test_n421_control_an_intact_logfile_row_raises_no_finding(monkeypatch, tmp_path, cmd, mode):
    """Not a RED. Both OIDs, a 48-byte row 1, a size of 0x80 clusters (as on 120 of 120 corpus volumes): exit 0 and no
    row statement, read through the real get_mlog_info (the runner's guard)."""
    log = (_n421_dated_log(tmp_path, "intact") if cmd == "timeline" else
           SynLog(tmp_path / "n421_row_intact.raw").run(1, 0x20, 1, session_start=True).control(END, END).write())
    rc, out, err = _inproc_rows(monkeypatch, log, "intact", cmd, *(("--fast",) if cmd == "timeline" else mode))
    _keep(rc == 0 and not any(n421_row_statements(out + "\n" + err, c) for c in _N421_ROW_CASES),
          "`%s %s` on an intact Logfile Information Table" % (cmd, " ".join(mode)) + _ctx(rc, out, err))
    if cmd == "timeline":
        _keep(len(_tl_mlog_rows(out, ())) == 4, "timeline lists its 4 MLog rows" + _ctx(rc, out, err))


@pytest.mark.parametrize("mode", ["stats", "json"])
def test_n421_the_data_area_ends_at_start_plus_size_not_at_the_rows_end_lcn(monkeypatch, tmp_path, mode):
    """Start is handed value[0] and value[2] (the size), never value[1] (the end LCN): the log's data area is [start,
    start + size). Here value[1] is the cluster of record 0x20, so a scan to value[1] misses that record (and calls it
    missing); refs.sys's data area holds all 32 records, the log's end is not past them: exit 0."""
    log = SynLog(tmp_path / "n421_endlcn.raw").run(1, 0x20, 1, session_start=True).control(END, END).write()
    _fx(log.cluster_of(0x20) == N421_END_LCN and log.de - log.DS == 0x80, "record 0x20 is not in cluster 0x%x"
        % N421_END_LCN)
    rc, out, err = _inproc_rows(monkeypatch, log, "end-lcn", "mlog", "--%s" % mode)
    n = (len(_ci_get(_load_json(out), "Records") or []) if mode == "json"    # the top-level list (each transaction
         else redo_records(out))                           # repeats its own records)
    assert rc == 0 and n == 0x20, "the data area is start + size = 0x%x - 0x%x (value[1] = 0x%x is not read by the " \
        "driver): `mlog --%s` must read all 32 records and exit 0; it reads %r, exit %s" % (
            log.DS, log.de, N421_END_LCN, mode, n, rc) + _ctx(rc, out, err)


# ─── N421: the control copies' addresses, the 4 KiB read, the header tests, the copy choice ──────────────────

class _CopyAtZero(SynLog):
    """A log whose Logfile Information row gives control copy 1 the address 0 (value[4] = 0); copy 0 at cluster 1."""

    @property
    def info(self):
        d = dict(SynLog.info.fget(self))
        d["ctrl_plcn_1"] = 0
        return d


@pytest.mark.parametrize("mode", ["--stats", "--json"])
def test_n421_a_control_copy_at_address_0_is_read_and_reported_where_redundancy_is_reported(monkeypatch, tmp_path,
                                                                                            mode):
    """LogCoreReadControlArea reads copy 1 at the address the row gives, 0 included (block 0 holds no control record
    here), so the driver has one failed copy: a redundancy condition (LB39) -- `--stats` names copy 1 FAILED at PLCN
    0x0, `--json` gives its verdict and states it on stderr; exit 2."""
    log = _CopyAtZero(tmp_path / "n421_zero.raw").run(1, 0x20, 1, session_start=True).control(END, END).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", mode)
    if mode == "--stats":
        line = MC.control_verdicts(out).get(1)
        ok, what = bool(line) and line[0] == 0 and line[1] != "verified", "copy 1's line %r" % (line,)
    else:
        verdict = _copy_verdicts(_load_json(out), plcns=(0,)).get(0)
        # LB39 (copy 1 named, its failure, the copy in use NOT affected), its failure in N412's words for an
        # unreadable copy too -- "is not a readable control record: <what was read>", the words the --stats line
        # prints after FAILED
        said = [w for w in re.split(r"\n\s*\n", err) if _LB38_AREA.search(w) and 1 in _lb38_copies_named(w)
                and (_LB38_FAIL.search(w) or re.search(r"(?i)\bnot\s+a\s+readable\s+control\s+record\b", w))
                and re.search(r"(?i)\bin[ -]use\b", w) and _LB39_NOT_AFFECTED.search(w)]
        ok = verdict is False and bool(said)
        what = "copy 1 (PLCN 0x0) verdict %r; a stderr statement naming it: %s" % (verdict, "found" if said else "none")
    assert rc == 2 and ok, "control copy 1's address is 0: refs.sys reads it there and finds no control record, so " \
        "`mlog %s` must report the copy failed and exit 2 (exit %s; LB57 with LB39); %s" % (mode, rc, what) \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--parse",), ("--csv",)], ids=["default", "parse", "csv"])
def test_n421_control_a_copy_at_address_0_leaves_the_other_modes_at_exit_0(monkeypatch, tmp_path, mode):
    """Not a RED. Copy 0 is read and verifies: the other modes exit 0 and say nothing of copy 1 (V-a)."""
    log = _CopyAtZero(tmp_path / "n421_zero.raw").run(1, 0x20, 1, session_start=True).control(END, END).write()
    rc, out, err = inproc(monkeypatch, log, "mlog", *mode)
    _keep(rc == 0 and not lb38_statements(out + "\n" + err, (1,)), "`mlog %s` with copy 1 at address 0"
          % " ".join(mode) + _ctx(rc, out, err))


_N421_HDR_CASES = ["block-size", "entry-low", "entry-past-record", "3c-over-38", "3c-over-read"]
_N421_HDR_NEED = {                                    # what a statement about the refused copy must name, per case
    "block-size": [re.compile(r"(?i)\+0x0?c\b"), _hexnum(0x2000)],
    "entry-low": [re.compile(r"(?i)\+0x54\b"), _hexnum(0x70)],
    "entry-past-record": [re.compile(r"(?i)\+0x54\b"), re.compile(r"(?i)\+0x38\b")],
    "3c-over-38": [re.compile(r"(?i)\+0x3c\b"), re.compile(r"(?i)\+0x38\b")],
    "3c-over-read": [re.compile(r"(?i)\+0x3c\b"), re.compile(r"(?i)\b4\s*KiB\b|(?<![0-9a-fx])0x0*1000(?![0-9a-f])|"
                                                            r"\b4096\b")],
    "entry-past-read": [re.compile(r"(?i)\+0x54\b"), _hexnum(0x1008)],
}


def _seal_at_entry(b):
    """Re-seal a control record at its own entry header (+0x54 + 8), the field LogVerifyChecksumEntryHeader zeroes."""
    struct.pack_into("<Q", b, le32(b, 0x54) + 8, MC._fold(b))
    return bytes(b)


def _n421_hdr_record(rec, case):
    """`rec` (a sealed 4 KiB control record of SynLog's layout: entry header at 0x78, payload at 0xB0) with `case`'s
    header edit, re-sealed over its 4 KiB -- 'entry-past-read' (8 KiB, for a 64 KiB cluster) is not re-sealed: refs.sys
    refuses it before its fold."""
    b = bytearray(rec)
    if case == "block-size":
        struct.pack_into("<I", b, 0x0C, 0x2000)
    elif case == "entry-low":                         # the 0x38-byte entry header moved to 0x70; the payload stays
        b[0x70:0xA8] = rec[0x78:0xB0]
        b[0xA8:0xB0] = bytes(8)
        struct.pack_into("<I", b, 0x54, 0x70)
        struct.pack_into("<I", b, 0x70 + 0x28, 0x40)
    elif case == "entry-past-record":
        struct.pack_into("<II", b, 0x38, 0, 0)
    elif case == "3c-over-38":
        struct.pack_into("<I", b, 0x3C, 2)
    elif case == "3c-over-read":
        struct.pack_into("<II", b, 0x38, 2, 2)
    elif case == "entry-past-read":                   # entry header at 0x1008, payload at 0x1040, +0x38 = 2 blocks
        out = bytearray(2 * MLOG_BLK)
        out[:0x78] = rec[:0x78]
        out[0x1008:0x1040] = rec[0x78:0xB0]
        out[0x1040:0x1040 + 0xE48] = rec[0xB0:0xB0 + 0xE48]
        struct.pack_into("<I", out, 0x54, 0x1008)
        struct.pack_into("<II", out, 0x38, 2, 1)
        return bytes(out)
    else:
        raise RedFixtureError("unknown header case %r" % case)
    return _seal_at_entry(b)


def _n421_hdr_check(blk, case):
    """This module's reading of `case`'s planted header fields in `blk`."""
    eh, n38, n3c = le32(blk, 0x54), le32(blk, 0x38), le32(blk, 0x3C)
    return {"block-size": le32(blk, 0x0C) == 0x2000, "entry-low": eh == 0x70,
            "entry-past-record": eh == 0x78 and (n38, n3c) == (0, 0), "3c-over-38": (n38, n3c) == (1, 2),
            "3c-over-read": (n38, n3c) == (2, 2), "entry-past-read": eh == 0x1008 and (n38, n3c) == (2, 1)}[case]


def _n421_hdr_log(tmp_path, case, slots, dated=False):
    """Records 1..0x20 (or 4 dated payloads), control copies 0 (sequence 51) and 1 (50); the copies in `slots` carry
    `case`'s header edit -- re-sealed, so each folds to its stored value over its 4 KiB (all but 'entry-past-read', on
    a 64 KiB log)."""
    cs = 0x10000 if case == "entry-past-read" else 0x1000
    name = "n421_hdr_%s_%s%s" % (case, "".join(map(str, slots)), "_dated" if dated else "")
    if dated:
        log = SynLog(tmp_path / (name + ".raw"), cs)
        for k in range(1, 5):
            log.blocks[k] = payload_block(MAGIC_A, UUID_A, 3, lsn(1, k), lsn(1, k - 1) if k > 1 else 0,
                                          [[redo_rec(0x04, 3, 0, FT_A + k)]])
        log.control(lsn(1, 5), lsn(1, 5))
    else:
        log = SynLog(tmp_path / (name + ".raw"), cs).run(1, 0x20, 1, session_start=True).control(END, END)
    for i in slots:
        log.ctrl[i] = _n421_hdr_record(log.ctrl[i], case)
    log.write()
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs, 2 * MLOG_BLK)
        if case == "entry-past-read" and i in slots:  # refused before its fold: only its header is what the case needs
            ok = blk[:4] == b"MLog"
        else:
            c = MC.parse_block(blk[:MLOG_BLK])
            ok = c is not None and c["type"] == 1 and c["fold"] == c["stored"]
        _fx(ok and _n421_hdr_check(blk, case) == (i in slots), "control copy %d is not what the case needs" % i)
    return log


def _in_use_shown(rc, out, mode):
    """(PLCN, sequence) of the control copy the output shows in use (N418's reader)."""
    if mode == "json":
        c = _json_control(_load_json(out))
        return _as_int(_ci_get(c, "PLCN")), _as_int(_ci_get(c, "Sequence"))
    m = re.search(r"(?m)^\s*Control PLCN:\s+(0x[0-9a-f]+)", out)
    return (int(m.group(1), 16) if m else None), labelled_int(out, "Sequence")


@pytest.mark.parametrize("mode", ["text", "json"])
@pytest.mark.parametrize("case", _N421_HDR_CASES)
def test_n421_a_control_copy_failing_a_header_test_is_never_the_copy_in_use(monkeypatch, tmp_path, case, mode):
    """Copy 0 (sequence 51, the newer) fails one of LogValidateEntryHeader's tests and folds to its stored value: the
    driver refuses it before its fold, so the copy it reads -- and the control area shown -- is copy 1 (PLCN 0x2,
    sequence 50)."""
    rc, out, err = inproc(monkeypatch, _n421_hdr_log(tmp_path, case, (0,)), "mlog", *(("--json",) if mode == "json"
                                                                                     else ()))
    shown = _in_use_shown(rc, out, mode)
    assert shown == (2, 50), "copy 0 fails LogValidateEntryHeader's %s test (refs.sys refuses it): the copy in use is " \
        "copy 1 (PLCN 0x2, sequence 50); `mlog %s` shows PLCN %r, sequence %r" % (case, mode, shown[0], shown[1]) \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--info",), ("--earlier-logs",)],
                         ids=["default", "csv", "json", "info", "earlier-logs"])
@pytest.mark.parametrize("case", _N421_HDR_CASES + ["entry-past-read"])
def test_n421_both_copies_failing_a_header_test_is_the_no_readable_copy_condition(monkeypatch, tmp_path, case, mode):
    """Both copies fail the header test: LogCoreReadControlArea reads neither, so the log has no readable control copy
    (N412): exit 2, with N412's statement, which names why each copy is refused (the field and its value)."""
    rc, out, err = inproc(monkeypatch, _n421_hdr_log(tmp_path, case, (0, 1)), "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = [s for s in n412_statements(err if export else out) if all(r.search(s) for r in _N421_HDR_NEED[case])]
    assert rc == 2 and said, "both control copies fail LogValidateEntryHeader's %s test: no copy is one refs.sys reads, " \
        "so `mlog %s` must exit 2 (exit %s; LB57 with LB41) and state %s that no control copy can be read, naming the " \
        "field (statement: %s)" % (case, " ".join(mode), rc, _lb38_where(export), "found" if said else "none") \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", ["--stats", "--json"])
@pytest.mark.parametrize("case", _N421_HDR_CASES)
def test_n421_a_copy_failing_a_header_test_is_reported_where_redundancy_is_reported(monkeypatch, tmp_path, case, mode):
    """The refused copy is a failed copy not in use (LB39): `--stats` names it FAILED with the field, `--json` gives its
    verdict and states it on stderr; exit 2."""
    rc, out, err = inproc(monkeypatch, _n421_hdr_log(tmp_path, case, (0,)), "mlog", mode)
    need = _N421_HDR_NEED[case]
    if mode == "--stats":
        line = MC.control_verdicts(out).get(0)
        ok = bool(line) and line[1] != "verified" and all(r.search(line[1] + line[2]) for r in need)
        what = "its `Control copy 0` line %r" % (line,)
    else:
        verdict = _copy_verdicts(_load_json(out)).get(1)
        said = [s for s in lb39_statements(err, (0,)) if all(r.search(s) for r in need)]
        ok = verdict is False and bool(said)
        what = "verdict %r; a stderr statement naming copy 0 and the field: %s" % (verdict, "found" if said else "none")
    assert rc == 2 and ok, "control copy 0 fails LogValidateEntryHeader's %s test, which refs.sys refuses: `mlog %s` " \
        "must report it failed, naming the field, and exit 2 (exit %s; LB39); %s" % (case, mode, rc, what) \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",)], ids=["text", "csv"])
@pytest.mark.parametrize("case", ["block-size", "3c-over-read"])
def test_n421_both_copies_failing_a_header_test_makes_timeline_exit_2_with_a_statement(monkeypatch, tmp_path, case,
                                                                                         mode):
    rc, out, err = inproc(monkeypatch, _n421_hdr_log(tmp_path, case, (0, 1), dated=True), "timeline", "--fast", *mode)
    _keep(len(_tl_mlog_rows(out, mode)) == 4, "the MLog rows are no longer listed" + _ctx(rc, out, err))
    said = [s for s in n412_statements(err if mode else out) if all(r.search(s) for r in _N421_HDR_NEED[case])]
    assert rc == 2 and said, "both control copies fail LogValidateEntryHeader's %s test: `timeline %s` must exit 2 " \
        "(exit %s) and state it %s (statement: %s)" % (case, " ".join(mode), rc, _lb38_where(bool(mode)),
                                                        "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--parse",), ("--csv",), ("--info",)], ids=["default", "parse", "csv", "info"])
@pytest.mark.parametrize("case", ["entry-low", "3c-over-38"])
def test_n421_control_a_copy_failing_a_header_test_not_in_use_leaves_the_other_modes_at_exit_0(monkeypatch, tmp_path,
                                                                                                case, mode):
    """Not a RED. One copy refused, the other read: the other modes exit 0 and say nothing of it (V-a)."""
    rc, out, err = inproc(monkeypatch, _n421_hdr_log(tmp_path, case, (0,)), "mlog", *mode)
    _keep(rc == 0 and not lb38_statements(out + "\n" + err, (0,)), "`mlog %s` with one refused copy not in use"
          % " ".join(mode) + _ctx(rc, out, err))


def _n421_fold_log(tmp_path):
    """A 64 KiB log whose two control records declare 2 blocks (+0x38 = 2, +0x3C = 1), each sealed over its 4 KiB --
    what LogReadControlRecord reads and LogChecksumBlock folds -- with non-zero bytes in the next 4 KiB of the cluster,
    which refs.sys never reads."""
    log = SynLog(tmp_path / "n421_fold64k.raw", 0x10000).run(1, 0x20, 1, session_start=True).control(END, END)
    for i in range(2):
        b = bytearray(log.ctrl[i])
        struct.pack_into("<II", b, 0x38, 2, 1)
        log.ctrl[i] = MC._seal(b) + b"\x5a" * MLOG_BLK
    log.write()
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs, 2 * MLOG_BLK)
        c = MC.parse_block(blk[:MLOG_BLK])
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and le32(blk, 0x38) == 2
            and blk[MLOG_BLK:] == b"\x5a" * MLOG_BLK, "control copy %d is not what the case needs" % i)
    return log


@pytest.mark.parametrize("mode", ["default", "stats", "json"])
def test_n421_a_control_record_is_read_and_folded_as_one_4k_block(monkeypatch, tmp_path, mode):
    """On a 64 KiB volume refs.sys reads a control record as its first 4 KiB and folds those (LogReadControlRecord:
    0x1000 bytes; LogVerifyChecksumEntryHeader(handle, 0x1000, ...)): both copies verify, whatever the record's block
    count says and whatever the rest of the cluster holds -- exit 0, no failed copy."""
    rc, out, err = inproc(monkeypatch, _n421_fold_log(tmp_path), "mlog", *({"default": (), "stats": ("--stats",),
                                                                           "json": ("--json",)}[mode]))
    if mode == "stats":
        v = MC.control_verdicts(out)
        ok, what = set(v) == {0, 1} and all(s == "verified" for _p, s, _r in v.values()), "verdicts %r" % (v,)
    elif mode == "json":
        v = _copy_verdicts(_load_json(out))
        ok, what = v == {1: True, 2: True}, "verdicts %r" % (v,)
    else:
        ok, what = not lb38_statements(out, (0, 1)), "an LB38 statement: %r" % (lb38_statements(out, (0, 1))[:1],)
    assert rc == 0 and ok, "both 64 KiB control records verify over the 4 KiB refs.sys reads: `mlog %s` must show them " \
        "verified and exit 0 (exit %s); %s" % (mode, rc, what) + _ctx(rc, out, err)


# LogCoreReadControlArea's choice, case: ({slot: (sequence or None, set payload flags bit 1)}, (PLCN, sequence) taken)
_N421_CHOICE = {"older-copy-flags-bit1": ({1: (None, True)}, (2, 50)),
                "copy0-flags-bit1-copy1-newer": ({0: (None, True), 1: (52, False)}, (1, 51)),
                "both-flags-bit1-copy1-newer": ({0: (None, True), 1: (52, True)}, (1, 51))}
_N421_CHOICE_CONTROLS = {"copy1-newer": ({1: (52, False)}, (2, 52)), "tie": ({1: (51, False)}, (1, 51))}


def _n421_choice_log(tmp_path, case, edits):
    log = SynLog(tmp_path / ("n421_choice_%s.raw" % case)).run(1, 0x20, 1, session_start=True).control(END, END)
    for i, (seq, bit1) in edits.items():
        b = bytearray(log.ctrl[i])
        p = _payload_at(b)
        if seq is not None:
            struct.pack_into("<Q", b, p, seq)
        if bit1:
            struct.pack_into("<I", b, p + 0x3C, le32(b, p + 0x3C) | 2)
        log.ctrl[i] = MC._seal(b)
    log.write()
    for i in range(2):
        blk = MC.read_block(log.path, (1 + i) * log.cs)
        c, p = MC.parse_block(blk), _payload_at(blk)
        seq, bit1 = edits.get(i, (None, False))
        _fx(c and c["fold"] == c["stored"] and c["seq"] == (seq if seq is not None else 51 - i)
            and bool(le32(blk, p + 0x3C) & 2) == bit1 and le32(blk, p + 0x3C) & 1, "control copy %d is not what the "
            "case needs" % i)
    return log


@pytest.mark.parametrize("mode", ["text", "json"])
@pytest.mark.parametrize("case", sorted(_N421_CHOICE))
def test_n421_the_copy_in_use_is_the_one_logcorereadcontrolarea_takes(monkeypatch, tmp_path, case, mode):
    """Both copies pass every test; LogCoreReadControlArea prefers a copy whose payload flags bit 1 is set (the log
    re-created from a checkpoint position, its end not set yet) over a newer one, and keeps copy 0 when it has it."""
    edits, want = _N421_CHOICE[case]
    rc, out, err = inproc(monkeypatch, _n421_choice_log(tmp_path, case, edits), "mlog",
                          *(("--json",) if mode == "json" else ()))
    shown = _in_use_shown(rc, out, mode)
    assert shown == want, "%s: LogCoreReadControlArea takes the copy at PLCN 0x%x (sequence %d); `mlog %s` shows PLCN " \
        "%r, sequence %r" % (case, want[0], want[1], mode, shown[0], shown[1]) + _ctx(rc, out, err)


@pytest.mark.parametrize("case", sorted(_N421_CHOICE_CONTROLS))
def test_n421_control_with_flags_bit_1_clear_the_newer_copy_is_in_use_and_a_tie_keeps_copy_0(monkeypatch, tmp_path,
                                                                                              case):
    """Not a RED. Neither copy has flags bit 1: the newer copy is taken, a tie keeps copy 0 (as before this part)."""
    edits, want = _N421_CHOICE_CONTROLS[case]
    rc, out, err = inproc(monkeypatch, _n421_choice_log(tmp_path, case, edits), "mlog")
    _keep(_in_use_shown(rc, out, "text") == want and rc == 0, "%s: the copy in use" % case + _ctx(rc, out, err))


def test_n421_matchers_accept_a_sound_output_and_reject_others():
    """The readers of the N421 REDs: each accepts a sound form and rejects what it must refuse."""
    tbl = ("MLog: the Object Table holds no record of OID 0xA, one of the two copies of the Logfile Information Table "
           "(OID 0x9 and OID 0xA); refs.sys opens that table only when it finds both, so it would not open this log.")
    assert n421_row_statements(tbl, "table") and not n421_row_statements(tbl.replace("no record of OID 0xA",
                                                                                     "a record of OID 0xA"), "table")
    nr = ("MLog: the Logfile Information Table (OID 0x9) holds no row with key 1, the row that gives the log's place; "
          "refs.sys would not open a log on this volume.")
    assert n421_row_statements(nr, "norow") and not n421_row_statements(nr.replace("would not open", "opens"), "norow")
    sh = ("MLog: the Logfile Information Table (OID 0x9) row 1 holds 40 bytes; refs.sys reads the log's place from it "
          "only when it holds at least 48 (0x30), so it would not open this log.")
    assert n421_row_statements(sh, "short") and not n421_row_statements(sh.replace("48 (0x30)", "40"), "short")
    sz = ("MLog: the Logfile Information Table (OID 0x9) row 1 gives the log a size of 79 cluster(s); refs.sys opens a "
          "log only when it is at least 0x50 (80) clusters, so it would not open this log.")
    assert n421_row_statements(sz, "size") and not n421_row_statements(sz.replace("79", "81"), "size")
    ov = ("MLog: the Logfile Information Table (OID 0x9) row 1 gives the log a size of 2251799813685248 cluster(s); "
          "times the cluster size in 64 bits that is 0x8000000000000000 bytes, a negative size; MlLogOpenLog opens a "
          "log only above 8 KiB, so refs.sys would not open this log.")
    assert n421_row_statements(ov, "overflow") and not n421_row_statements(ov.replace("8 KiB", "a bound"), "overflow")
    assert not n421_row_statements("  Data area:   0x10 - 0x5f (79 clusters; 79 log blocks of 4 KiB)", "size")
    w = ("[forefst] MLog control: no control copy can be read. Copy 0 (PLCN 0x1, sequence 51): it fails the driver's "
         "header check: its log block size 0x2000 (+0x0C) is not 0x1000. Copy 1 (PLCN 0x2, sequence 50): the same. "
         "Without one the log instance (format magic and UUID) is unknown, so records of earlier logs cannot be told "
         "from the log in use's: none is left out, and every record of the data area is listed.")
    assert [s for s in n412_statements(w) if all(r.search(s) for r in _N421_HDR_NEED["block-size"])]
    assert not [s for s in n412_statements(w) if all(r.search(s) for r in _N421_HDR_NEED["entry-low"])]
    assert _N421_HDR_NEED["3c-over-read"][1].search("more than the 4 KiB refs.sys reads")
    assert not _N421_HDR_NEED["3c-over-read"][1].search("0x10000")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N423 (LB61) and N424 (LB62): wave B part 3d, written first, before the fix
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# N423. InitializeVolumeRedoLog opens the Logfile Information Table as the failover pair OID 0xA / OID 0x9
# (InitializeFailoverMetadataTable, 26100.8115 :208106-208110; 17134 :51788, 26100.9444 :207411, Insider :277479), and
# MsCreateDurableFailoverTableObject (:66532) looks up BOTH object records (:66666) and fails without either: with
# NEITHER in the Object Table the driver does not start the log. Part 3c applied the case of one copy missing (its
# table's T1) and left this one as its S2. LB61: a finding -- stated, exit 2 in LB24's set (`mlog` in every mode,
# `--info` and `--earlier-logs` included, and `timeline`'s MLog source), on stderr in export modes (LB10, LB38) -- not
# "Logfile Information Table (OID 0x9/0xA) not found" with exit 1 (`mlog`), not silence (`timeline`), not "no MLog on
# this volume" (the bundle manifest). Measured before these REDs (fixes/waveB_fix_evidence/part3d/pre_clear.jsonl):
# both OIDs in the Object Table of 120 of 120 corpus volumes.
#
# N424. A7's check (`mlog_tail_check`) clips the range [tail, log end) to the data area. A record's LSN offset is its
# 4 KiB block in the data area (F5: 885,709 of 885,709), so a log end (+0x20) whose offset lies past the data area's
# last block names no block of the log; the check then printed "0 record(s) of this volume's log are missing" (the
# tail at the area's end) or counted blocks up to the area's end against that end. LB62: a control log end past the
# data area is stated as that -- one finding, naming the log end and the data area's end -- never as a count of
# missing records. Measured before these REDs (pre_clear.jsonl): the log end lies inside the data area on 240 of 240
# corpus control copies (the highest end offset is 0.61 of the area), so no corpus row moves.

N423_IMAGE = "step1/win11refsmini.raw"          # battery base A: its Object Table holds OID 0x9 and OID 0xA (checked)


def _n423_regs(monkeypatch):
    """The run registers `inproc` resets, and the two at-exit ones an in-process real bootstrap or CSV export touches
    (`_ALL_TRS`, `_CSV_FORMULA_SEEN`), so this module leaves forefst as it found it (monkeypatch restores)."""
    _fresh_registers(monkeypatch)
    for name in _EXTRA_REGS + ("_ALL_TRS",):
        cur = getattr(F, name, None)
        if isinstance(cur, (list, dict)):
            monkeypatch.setattr(F, name, type(cur)())
    monkeypatch.setattr(F, "_CSV_FORMULA_SEEN", 0)


def _n423_call(cmd, image, args):
    fn = {"mlog": F.cmd_mlog, "timeline": F.cmd_timeline, "export": F.cmd_export_metadata}[cmd]
    out, err = io.StringIO(), io.StringIO()
    try:
        with UW.recording() as wrapped, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn(image, list(args), None)
    except SystemExit as e:
        raise RedFixtureError("%s %s exited through die() (%r):\n%s" % (cmd, " ".join(args), e.code,
                                                                        err.getvalue()[-2000:]))
    except Exception:
        raise RedFixtureError("%s %s crashed (a crash is never the defect under test):\n%s"
                              % (cmd, " ".join(args), traceback.format_exc()))
    return _rc_escalate()(0 if rc is None else rc), UW.unwrap_exact(out.getvalue(), wrapped), err.getvalue()


def _n423_inproc(monkeypatch, log, cmd, *args):
    """`inproc` with the REAL `get_mlog_info` over an Object Table that holds neither OID 0x9 nor OID 0xA: the
    patched bootstrap returns an empty object map (no table walk can be needed; one is a fixture error)."""
    calls = Counter()
    real_info = F.get_mlog_info

    def _boot(image, partition_start=None):
        calls["bootstrap"] += 1
        return open(log.path, "rb"), 0, log.cs, MC._IdentityTr(), [], {}, 3, 14, []

    def _info(*a, **k):
        calls["get_mlog_info"] += 1
        return real_info(*a, **k)

    def _walk(*a, **k):
        raise RedFixtureError("a table walk over an Object Table that holds no table: adapt _n423_inproc")

    monkeypatch.setattr(F, "bootstrap", _boot)
    monkeypatch.setattr(F, "get_mlog_info", _info)
    monkeypatch.setattr(F, "walk_bplus", _walk)
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: {})
    _n423_regs(monkeypatch)
    res = _n423_call(cmd, log.path, args)
    _fx(calls["bootstrap"] == 1 and calls["get_mlog_info"] >= 1,
        "%s no longer reads the Logfile Information Table through the patched layer (%r)" % (cmd, dict(calls)))
    return res


def _n423_image(monkeypatch, cmd, *args, drop=True):
    """`cmd` in-process on the corpus volume N423_IMAGE through the REAL bootstrap, its Object Table (as read) with
    OID 0x9 and OID 0xA dropped when `drop` -- the volume's own Logfile Information Table removed, nothing else."""
    img = MC.corpus(N423_IMAGE)
    real_boot = F.bootstrap
    calls = Counter()

    def _boot(image, partition_start=None):
        calls["bootstrap"] += 1
        r = list(real_boot(image, partition_start))
        _fx(0x9 in r[5] and 0xA in r[5], "%s: its Object Table does not hold OID 0x9 and OID 0xA" % N423_IMAGE)
        if drop:
            r[5] = {k: v for k, v in r[5].items() if k not in (0x9, 0xA)}
        return tuple(r)

    monkeypatch.setattr(F, "bootstrap", _boot)
    _n423_regs(monkeypatch)
    res = _n423_call(cmd, img, args)
    _fx(calls["bootstrap"] == 1, "%s did not read the volume through the patched bootstrap (%r)" % (cmd, dict(calls)))
    return res


_N423_NEITHER = re.compile(
    r"(?i)\bneither\b[^.;\n]{0,40}\bOID\s+0x0*9\b[^.;\n]{0,20}\bnor\b[^.;\n]{0,10}\b(?:OID\s+)?0x0*a\b"
    r"|\bneither\b[^.;\n]{0,40}\bOID\s+0x0*a\b[^.;\n]{0,20}\bnor\b[^.;\n]{0,10}\b(?:OID\s+)?0x0*9\b"
    r"|\bno\s+record\s+of\s+(?:either\s+)?OID\s+0x0*9\b[^.;\n]{0,10}\b(?:or|nor)\b[^.;\n]{0,10}\b(?:OID\s+)?0x0*a\b"
    r"|\bboth\b[^.;\n]{0,80}\b(?:missing|absent|not\s+(?:found|present|held))\b")


def n423_statements(text):
    """A line and the next two of its paragraph: the Logfile Information Table (or OID 0x9) named, BOTH of its copies
    (OID 0x9 and OID 0xa) said to be absent from the Object Table, and that the driver would not open the log (N415's
    reader). The one-copy statement of N421 (one OID named missing, the other present) is not this."""
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if _N421_TABLE_NAMED.search(w) and _N423_NEITHER.search(w) and _N415_REFUSE.search(w):
                hits.append(w)
    return hits


def _export_whole(mode, out):
    """LB10 / G3b's F1 rule: with an export to stdout, stdout holds the export alone -- a CSV whose first line is its
    header, or one JSON document (an empty listing is still a well-formed export)."""
    if mode == ("--csv",):
        first = (out.splitlines() or [""])[0]
        return bool(re.match(r"^\s*Seq,", first)), "stdout's first line %r" % first[:120]
    try:
        json.loads(out)
        return True, ""
    except ValueError as e:
        return False, "stdout is not one JSON document (%s): %r" % (e, out[:200])


@pytest.mark.parametrize("mode", _N412_MLOG_MODES, ids=_N412_MLOG_IDS)
def test_n423_no_logfile_information_table_makes_every_mlog_mode_exit_2_with_a_statement(monkeypatch, tmp_path, mode):
    log = SynLog(tmp_path / "n423_mlog.raw").run(1, 0x20, 1, session_start=True).control(END, END).write()
    rc, out, err = _n423_inproc(monkeypatch, log, "mlog", *mode)
    export = mode in (("--csv",), ("--json",))
    said = n423_statements(err if export else out)
    whole, why = _export_whole(mode, out) if export else (True, "")
    assert rc == 2 and said and whole, "the Object Table holds neither OID 0x9 nor OID 0xA, so refs.sys does not start " \
        "the log: `mlog %s` must exit 2 (exit %s; LB61) and state it %s -- both copies of the Logfile Information " \
        "Table missing, and that the driver would not open a log (statement: %s)%s" % (
            " ".join(mode), rc, _lb38_where(export), "found" if said else "none",
            "" if whole else "; and stdout must hold the export alone: " + why) + _ctx(rc, out, err)


@pytest.mark.parametrize("mode", [(), ("--csv",), ("--json",), ("--jsonl",)], ids=["text", "csv", "json", "jsonl"])
def test_n423_no_logfile_information_table_makes_timeline_exit_2_with_a_statement(monkeypatch, tmp_path, mode):
    rc, out, err = _n423_inproc(monkeypatch, _n421_dated_log(tmp_path, "n423"), "timeline", "--fast", *mode)
    _keep(not _tl_mlog_rows(out, mode), "with no Logfile Information Table no MLog row can be located"
          + _ctx(rc, out, err))
    said = n423_statements(err if mode else out)
    assert rc == 2 and said, "the Object Table holds neither OID 0x9 nor OID 0xA: `timeline %s`'s MLog source must " \
        "exit 2 (exit %s; LB61) and state it %s (statement: %s)" % (" ".join(mode), rc, _lb38_where(bool(mode)),
                                                                   "found" if said else "none") + _ctx(rc, out, err)


@pytest.mark.parametrize("cmd,mode", [("mlog", ("--stats",)), ("mlog", ("--json",)), ("timeline", ("--csv",))],
                         ids=["mlog-stats", "mlog-json", "timeline-csv"])
def test_n423_no_logfile_information_table_is_stated_and_exits_2_on_image_win11refsmini(monkeypatch, cmd, mode):
    """The volume's own Object Table, as bootstrap reads it, with OID 0x9 and OID 0xA dropped (nothing else changed);
    the command runs in-process through the real bootstrap and the real get_mlog_info."""
    args = (("--fast",) if cmd == "timeline" else ()) + mode
    rc, out, err = _n423_image(monkeypatch, cmd, *args)
    export = bool(mode) and mode != ("--stats",)
    said = n423_statements(err if export else out)
    assert rc == 2 and said, "%s with OID 0x9 and OID 0xA dropped from its Object Table: `%s %s` must exit 2 (exit %s; " \
        "LB61) and state the missing Logfile Information Table %s (statement: %s)" % (
            N423_IMAGE, cmd, " ".join(args), rc, _lb38_where(export), "found" if said else "none") \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("cmd,mode", [("mlog", ("--stats",)), ("mlog", ("--json",)), ("timeline", ("--csv",))],
                         ids=["mlog-stats", "mlog-json", "timeline-csv"])
def test_n423_control_the_same_volume_with_its_table_raises_no_such_finding_on_image_win11refsmini(monkeypatch, cmd,
                                                                                                   mode):
    """Not a RED. The same in-process run with the Object Table as read (both OIDs present): the volume's own exit
    code (0: no MLog finding on it, golden G3) and no N423 statement."""
    args = (("--fast",) if cmd == "timeline" else ()) + mode
    rc, out, err = _n423_image(monkeypatch, cmd, *args, drop=False)
    _keep(rc == 0 and not n423_statements(out + "\n" + err), "`%s %s` on %s as read" % (cmd, " ".join(args),
                                                                                       N423_IMAGE) + _ctx(rc, out, err))


@pytest.mark.parametrize("src", ["usn"])
def test_n423_control_timeline_says_nothing_of_the_mlog_when_it_does_not_read_it(monkeypatch, tmp_path, src):
    """Not a RED. `--source USN` leaves the MLog source unread (as for every MLog finding): no N423 statement and no
    exit 2 from it. (`--fileref` was the second case until 1.14.1, when it began to read the MLog: the next test.)"""
    args = ("--source", "USN")
    rc, out, err = _n423_inproc(monkeypatch, _n421_dated_log(tmp_path, "n423_" + src), "timeline", "--fast", *args)
    _keep(rc == 0 and not n423_statements(out + "\n" + err), "`timeline %s` reads no MLog" % " ".join(args)
          + _ctx(rc, out, err))


def test_n423_timeline_fileref_reads_the_mlog_so_states_the_missing_table_and_exits_2(monkeypatch, tmp_path):
    """U12 (1.14.1): `timeline --fileref` / `--id` merges the log payloads that name the object, so it reads the MLog:
    over an Object Table that holds neither copy of the Logfile Information Table it states it and exits 2, as
    `timeline` does."""
    args = ("--fileref", "0x701:0x2")
    rc, out, err = _n423_inproc(monkeypatch, _n421_dated_log(tmp_path, "n423_fileref"), "timeline", "--fast", *args)
    said = n423_statements(out + "\n" + err)
    assert rc == 2 and said, "`timeline %s` reads the MLog since 1.14.1: exit 2 (exit %s) and the statement (%s)" % (
        " ".join(args), rc, "found" if said else "none") + _ctx(rc, out, err)


def test_n423_export_metadata_names_the_missing_table_not_no_mlog_on_image_win11refsmini(monkeypatch, tmp_path):
    """The bundle manifest's MLog warning on the same volume (OID 0x9 and OID 0xA dropped): it names the condition --
    the Object Table holds neither copy of the Logfile Information Table -- and never "no MLog on this volume"."""
    outdir = str(tmp_path / "bundle")
    rc, out, err = _n423_image(monkeypatch, "export", "--what", "mlog", outdir)
    man = os.path.join(outdir, "manifest.json")
    _fx(os.path.isfile(man), "export metadata wrote no manifest" + _ctx(rc, out, err))
    with open(man) as fh:
        warn = [w for w in (jdoc(json.load(fh), F._BUNDLE_KEYS).get("warnings") or []) if w.get("what") == "mlog"]
    _keep(len(warn) == 1 and not warn[0].get("failed"), "the manifest's MLog warnings: %r" % (warn,))
    reason = warn[0].get("reason") or ""
    named = bool(_N421_TABLE_NAMED.search(reason) and _N423_NEITHER.search(reason))
    assert named and not re.search(r"(?i)\bno\s+MLog\s+on\s+this\s+volume\b", reason), "the manifest says %r: it " \
        "must name the missing Logfile Information Table (both copies, OID 0x9 and OID 0xa), not claim the volume has " \
        "no MLog (LB61)" % reason


# ─── N424: the control log end past the data area ─────────────────────────────────────────────────────────────

N424_PAST = 0x200                               # a log-end offset past SynLog's 0x80 data-area blocks
_N424_CASES = {                                 # (the last record's block, the log end)
    "zero": (0x7F, lsn(1, N424_PAST)),          # the tail is the data area's end: 1.13.1-3c printed "0 record(s)"
    "partial": (0x20, lsn(1, N424_PAST)),       # blocks 0x21..0x7f after the tail, the end past them all
    "next-generation": (0x7F, lsn(2, N424_PAST)),   # the end in the next generation, past the area too
}


def _n424_log(tmp_path, case):
    last, end = _N424_CASES[case] if case in _N424_CASES else (0x7F, lsn(1, 0x80))
    log = SynLog(tmp_path / ("n424_%s.raw" % case)).run(1, last, 1, session_start=True).control(lsn(1, 1), end)
    log.write()
    for i in range(2):
        c = MC.parse_block(MC.read_block(log.path, (1 + i) * log.cs))
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and c["end"] == end and c["start"] == lsn(1, 1),
            "control copy %d is not what the case needs: %r" % (i, c))
    _fx(log.NBLK == 0x80 and log.de - log.DS == 0x80, "the data area is not 0x80 blocks")
    return log, end


_N424_PAST_AREA = re.compile(r"(?i)\b(?:past|beyond|outside|after)\b[^.;\n]{0,40}\bdata\s+area\b")
_N424_LOG_END = re.compile(r"(?i)\blog\s+end\b|\+0x20\b")
_N424_COUNT = re.compile(r"(?i)\b\d+\s+(?:log\s+)?records?(?:\(s\))?\b[^.\n]{0,60}\bmissing\b"
                         r"|\bmissing\s+from\s+\d+\s+log\s+blocks?(?:\(s\))?")          # N576: the count in blocks


def n424_statements(text, end, log):
    """A line and the next two of its paragraph: MLog named, the log end (by name or +0x20) and its value, that it lies
    past the data area, and the data area's end -- its end LCN or its size in 4 KiB blocks."""
    area_end = re.compile(r"(?i)(?<![0-9a-fx])0x0*%x(?![0-9a-f])|\b%d\s+(?:\w+\s+){0,3}blocks?\b"
                          r"|\b0x0*%x\s+(?:\w+\s+){0,3}blocks?\b" % (log.de, log.de - log.DS, log.de - log.DS))
    end_re = MC.lsn_re(end)
    hits = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.splitlines() if ln.strip()]
        for i in range(len(lines)):
            w = "\n".join(lines[i:i + 3])
            if (re.search(r"(?i)\bMLog\b", w) and _N424_LOG_END.search(w) and end_re.search(w)
                    and _N424_PAST_AREA.search(w) and area_end.search(w)):
                hits.append(w)
    return hits


_N424_MODES = [("mlog", ()), ("mlog", ("--stats",)), ("mlog", ("--json",)), ("timeline", ()), ("timeline", ("--csv",))]
_N424_IDS = ["mlog", "mlog-stats", "mlog-json", "timeline", "timeline-csv"]


@pytest.mark.parametrize("cmd,mode", _N424_MODES, ids=_N424_IDS)
@pytest.mark.parametrize("case", sorted(_N424_CASES))
def test_n424_a_log_end_past_the_data_area_is_stated_as_that_not_as_missing_records(monkeypatch, tmp_path, case, cmd,
                                                                                     mode):
    log, end = _n424_log(tmp_path, case)
    rc, out, err = inproc(monkeypatch, log, cmd, *((("--fast",) if cmd == "timeline" else ()) + mode))
    export = mode in (("--csv",), ("--json",))
    said = n424_statements(err if export else out, end, log)
    counted = _N424_COUNT.findall(out + "\n" + err)
    _keep(not MC.destroyed_claims(out + "\n" + err), MC.destroyed_claims(out + "\n" + err))
    assert rc == 2 and said and not counted, "%s: the control log end %s lies past the data area (0x80 blocks of 4 KiB, " \
        "LCN 0x%x - 0x%x): `%s %s` must state that %s -- the log end and the data area's end -- as one finding, exit 2 " \
        "(exit %s; LB62), and never count missing records against that end (statement: %s; counts: %r)" % (
            case, "0x%016x" % end, log.DS, log.de, cmd,
            " ".join(mode), _lb38_where(export), rc, "found" if said else "none", counted) + _ctx(rc, out, err)


@pytest.mark.parametrize("cmd,mode", [("mlog", ("--stats",)), ("timeline", ())], ids=["mlog-stats", "timeline"])
def test_n424_control_a_log_end_at_the_data_areas_end_is_no_finding(monkeypatch, tmp_path, cmd, mode):
    """Not a RED. Records 1..0x7f fill the data area to its last block and the log end is 1:0x80 -- the area's end,
    the next record's place: nothing is missing and the end is not past the area (exit 0, no statement)."""
    log, end = _n424_log(tmp_path, "at-end")
    rc, out, err = inproc(monkeypatch, log, cmd, *((("--fast",) if cmd == "timeline" else ()) + mode))
    text = out + "\n" + err
    _keep(rc == 0 and not n424_statements(text, end, log) and not MC.a7_lines(text),
          "a log end at the data area's end" + _ctx(rc, out, err))


def test_n424_control_records_missing_inside_the_data_area_are_still_counted(monkeypatch, tmp_path):
    """Not a RED. Records 1..0x20 and a log end of 1:0x40, inside the data area: A7's count (31 log blocks, 1:0x21 up to
    the log end 1:0x40) and exit 2 stay as they are."""
    log = SynLog(tmp_path / "n424_inside.raw").run(1, 0x20, 1, session_start=True).control(lsn(1, 1), lsn(1, 0x40))
    log.write()
    rc, out, err = inproc(monkeypatch, log, "mlog", "--stats")
    text = out + "\n" + err
    _keep(rc == 2 and MC.a7_named(text, [lsn(1, 0x40), lsn(1, 0x21)]) and re.search(r"\bmissing\s+from\s+31\s+log\s+block", text)
          and not n424_statements(text, lsn(1, 0x40), log), "A7 inside the data area" + _ctx(rc, out, err))


def test_n423_n424_matchers_accept_a_sound_output_and_reject_others():
    """The readers of the N423 / N424 REDs: each accepts a sound form and rejects what it must refuse."""
    good = ("MLog: the Object Table holds neither OID 0x9 nor OID 0xa, the two copies of the Logfile Information "
            "Table; refs.sys opens a log only through that table, so it would not open a log on this volume.")
    assert n423_statements(good) and n423_statements(good.replace("neither OID 0x9 nor OID 0xa",
                                                                  "no record of OID 0x9 or OID 0xa"))
    assert not n423_statements(good.replace("would not open", "opens"))
    assert not n423_statements("Logfile Information Table (OID 0x9/0xA) not found")            # 1.13.1's line
    one = ("MLog: the Object Table holds no record of OID 0xa, one of the two copies of the Logfile Information Table "
           "(OID 0x9 and OID 0xa); refs.sys opens that table only when it finds both (MsCreateDurableFailoverTableObject, "
           "from InitializeVolumeRedoLog), so it would not open this log.")
    assert not n423_statements(one)                                                             # N421's one-copy case
    log = SynLog("/nonexistent/n424.raw")
    end = lsn(1, N424_PAST)
    st = ("MLog control copy 0 (PLCN 0x1), the copy in use, holds the log end 0x0000000100000200 (generation 1, offset "
          "0x200) at payload +0x20, past the end of the data area: the data area holds 128 log blocks of 4 KiB (LCN 0x10 "
          "- 0x90).")
    assert n424_statements(st, end, log) and not _N424_COUNT.search(st)
    assert not n424_statements(st.replace("past the end of", "inside"), end, log)
    assert not n424_statements(st.replace("0x0000000100000200 (generation 1, offset 0x200)",
                                          "0x0000000100000040 (generation 1, offset 0x40)"), end, log)
    assert not n424_statements(st.replace("128 log blocks", "some blocks").replace("0x90", "?"), end, log)
    assert _N424_COUNT.search("MLog: 0 record(s) of this volume's log are missing, from 0x0000000100000080")
    assert _N424_COUNT.search("MLog: 95 record(s) of this volume's log are missing")
    assert _N424_COUNT.search("MLog: records are missing from 95 log block(s) of this volume's log, from x")   # N576
    assert not _N424_COUNT.search("this log's newest records cannot be checked against it")
    assert _export_whole(("--csv",), "Seq,Timestamp,Action\n")[0] and not _export_whole(("--csv",), "x\n")[0]
    assert _export_whole(("--json",), "{}")[0] and not _export_whole(("--json",), "Logfile ... not found\n")[0]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# LB66 and LB68: wave B part 4 (step GBb), written first, before the fix
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# LB66 (the golden GB critic's U-1, a regression wave B made): N310's `Transactions[]` carried every record a second
# time (`Transactions[].Records`, beside the top-level `Records`), so the document was 2.7 times 1.13.1's, and on
# step3b/win11refs2tmillionsofactionsv2 (1 GiB log, 2,729,573 redo records) `mlog --json` needed more than the 8 GB host:
# a MemoryError under a 5,500 MB address-space cap, where prefix_GB completes with a 2,605 MB peak and exit 0
# (fixes/GB_critic_evidence/mlog_json_memory/README.txt). LB66: `mlog --json` carries each record ONCE (the top-level
# `Records`); each transaction refers to its records by index (`FirstRecordIndex` + `RecordCount` when they are
# contiguous, else `RecordIndices`), never by copy; the document is written as a stream so memory stays bounded.
#
# LB68 (the golden GB's F-1): N423's sentence "the Object Table holds neither OID 0x9 nor OID 0xa" was printed over an
# Object Table the tool could NOT read (the battery's A4: its root page, PLCN 0xc08 of step1/win11refsmini, punched to
# an image hole; `objects=0`). LB68: that sentence only when the Object Table was read and holds neither; when it could
# not be read, "the Object Table could not be read, so the Logfile Information Table could not be looked up" (exit 2
# stays) -- in every mode and in the bundle manifest.

LB66_MEM_IMAGE = "step3b/win11refs2tmillionsofactionsv2.raw"
LB66_PREFIX_RC = 0          # prefix_GB's `mlog --json` exit on that image (GB_critic_evidence/mlog_json_memory/README.txt)
LB66_CAP_MIB = 1024         # `ulimit -v`; the prefix peaked at 2,605 MB RSS (FIX_GBb: 152 MB, and it passes at 512)


def _lb66_refs(t):
    """The record indices a transaction refers to: FirstRecordIndex + RecordCount, or RecordIndices (LB66)."""
    if "FirstRecordIndex" in t:
        f, n = t.get("FirstRecordIndex"), t.get("RecordCount")
        return list(range(f, f + n)) if isinstance(f, int) and isinstance(n, int) else None
    idx = t.get("RecordIndices")
    return idx if isinstance(idx, list) and all(isinstance(i, int) for i in idx) else None


def _lb66_check(j, n_records, n_txns):
    """The document's records counted once, and every transaction referring to its own records by index. Returns the
    list of problems (empty when sound); the record count is asserted by the caller first."""
    top = j.get("Records")
    txns = j.get("Transactions")
    _fx(isinstance(top, list) and isinstance(txns, list) and len(txns) == n_txns,
        "the document has no top-level Records / Transactions lists, or not %d transactions" % n_txns)
    bad, covered = [], []
    for i, t in enumerate(txns):
        copies = [k for k, v in t.items() if isinstance(v, list) and any(isinstance(x, dict) for x in v)]
        if copies:
            bad.append("transaction %d carries record copies under %r" % (i, copies))
        idx = _lb66_refs(t)
        if idx is None or len(idx) != t.get("RecordCount"):
            bad.append("transaction %d refers to no records by index (keys %r)" % (i, sorted(t)))
            continue
        if any(not 0 <= x < len(top) for x in idx):
            bad.append("transaction %d refers to records outside Records: %r" % (i, idx[:4]))
            continue
        wrong = [x for x in idx if (top[x].get("PLCN"), top[x].get("Block")) != (t.get("PLCN"), t.get("Block"))]
        if wrong:
            bad.append("transaction %d (PLCN %s block %s) refers to records of another log record: %r"
                       % (i, t.get("PLCN"), t.get("Block"), wrong[:4]))
        covered += idx
    if not bad and sorted(covered) != list(range(n_records)):
        bad.append("the transactions do not refer to each record once: %d references for %d records"
                   % (len(covered), n_records))
    return bad


def test_lb66_mlog_json_carries_each_record_once_and_transactions_refer_to_them_by_index(monkeypatch, tmp_path):
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", "--json")
    j = _load_json(out)
    recs = _data_records(j)
    _keep(isinstance(j.get("Records"), list) and len(j["Records"]) == S_TXN,
          "the top-level Records no longer hold the log's %d records" % S_TXN + _ctx(rc, out, err))
    assert len(recs) == S_TXN, "the document carries %d redo records for the log's %d: each record once, in the " \
        "top-level Records (LB66)" % (len(recs), S_TXN)
    bad = _lb66_check(j, S_TXN, P_TXN)
    assert not bad, "each transaction must refer to its records by index (FirstRecordIndex + RecordCount, or " \
        "RecordIndices), never by copy (LB66): %s" % "; ".join(bad[:4])


def test_lb66_the_records_keep_what_the_transaction_parser_read(monkeypatch, tmp_path):
    """LB66 reading R1 (FIX_GBb.md): a record carried once keeps every field the document gave it -- the transaction
    parser's TargetOID, Key and Time, which wave B part 1 put on the per-transaction copies only."""
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", "--json")
    top = _load_json(out).get("Records") or []
    _fx(len(top) == S_TXN, "the top-level Records do not hold the log's %d records" % S_TXN)
    missing = sorted({k for r in top for k in ("TargetOID", "Key", "Time") if k not in r})
    assert not missing, "the top-level records lack %r, which the document carried for each record (LB66: the " \
        "record carried once, nothing lost)" % missing
    assert FT_B_ISO in [r.get("Time") for r in top], "no record carries its own time %s" % FT_B_ISO


def test_lb66_control_the_documents_top_level_keys_and_their_order_are_kept(monkeypatch, tmp_path):
    """Not a RED. The streamed document keeps the top-level keys, in their order, and the transactions keep the CSV's
    fields (N310's node checks the values)."""
    rc, out, err = inproc(monkeypatch, _txn_log(tmp_path), "mlog", "--json")
    j = _load_json(out)
    _keep(list(j) == ["ReFSVersion", "View", "LogInstance", "Control", "ControlCopies", "MLogInfo", "EarlierLogs",
                      "DataArea", "Integrity", "Records", "Transactions"], "top-level keys: %r" % list(j))
    _keep(out.endswith("}\n") and out.startswith("{\n"), "not one indented JSON document: %r ... %r"
          % (out[:20], out[-20:]))
    _keep(out == json.dumps(j, indent=2, ensure_ascii=False) + "\n", "the document is not laid out as json.dump "
          "(indent=2) lays it out")


@pytest.mark.parametrize("view", ["log-in-use", "earlier-logs"])
def test_lb66_mlog_json_carries_each_record_once_on_image_win11refs2gtargeted_reformated(view):
    """The reformatted volume: 84 log records of the log in use holding 386 redo records, 119 of an earlier volume's
    log (this module's walker of the driver's framing counts them)."""
    R = MC._Reformated()
    ks = sorted(R.cur if view == "log-in-use" else R.old)
    n, _starts = _own_redo_counts(MC.corpus(R.rel), MC.REFORMATED[2], ks)
    _fx(view != "log-in-use" or n == 386, "this module's walker reads %d records of the log in use, not 386" % n)
    rc, out, err = cli(R.rel, "mlog", *(("--earlier-logs", "--json") if view == "earlier-logs" else ("--json",)))
    j = _load_json(out)
    recs = _data_records(j)
    _keep(len(j.get("Records") or []) == n, "the top-level Records hold %d records, not the %d of this view"
          % (len(j.get("Records") or []), n))
    assert len(recs) == n, "`mlog --json` (%s) carries %d redo records for the %d of this view: each record once " \
        "(LB66)" % (view, len(recs), n)
    bad = _lb66_check(j, n, len(ks))
    assert not bad, "transactions by index, never by copy (LB66): %s" % "; ".join(bad[:4])


def test_lb66_mlog_json_completes_under_a_memory_cap_on_image_win11refs2tmillionsofactionsv2(tmp_path):
    """`mlog --json` on the 1 GiB log (2,729,573 redo records) under `ulimit -v` = LB66_CAP_MIB: the prefix's exit code,
    and one whole document whose records are each referred to once by the transactions. stdout is read as a stream
    (counted, never kept); stderr goes to a file under tmp_path."""
    img = MC.corpus(LB66_MEM_IMAGE)
    errp = tmp_path / "lb66_stderr.txt"
    cmd = ["bash", "-c", 'ulimit -v %d && exec "$@"' % (LB66_CAP_MIB * 1024), "lb66",
           sys.executable, "-B", FOREFST, img, "mlog", "--json"]
    n_lines = n_recs = n_refs = 0
    first = last = b""
    with open(errp, "wb") as ef:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=ef, cwd=REPO,
                             env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        try:
            for line in p.stdout:
                n_lines += 1
                if n_lines == 1:
                    first = line
                last = line
                s = line.lstrip()
                if s.startswith(b'"Opcode": '):
                    n_recs += 1
                elif s.startswith(b'"RecordCount": '):
                    n_refs += int(s[len(b'"RecordCount": '):].rstrip(b",\r\n"))
            rc = p.wait(timeout=MC.TIMEOUT)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            raise RedFixtureError("timeout after %d s: %s" % (MC.TIMEOUT, " ".join(cmd)))
    err = errp.read_text(errors="replace")
    assert rc == LB66_PREFIX_RC, "`mlog --json` on %s under a %d MiB address-space cap exits %s (the prefix: %d; " \
        "LB66: the document is written as a stream, memory bounded); stderr: %s" % (
            LB66_MEM_IMAGE, LB66_CAP_MIB, rc, LB66_PREFIX_RC, err[-1500:])
    assert first == b"{\n" and last == b"}\n" and n_recs > 2000000 and n_refs == n_recs, "not one whole document " \
        "whose transactions refer to each record once: first %r, last %r, %d records, %d referred to" % (
            first, last, n_recs, n_refs)


# ─── LB68: an Object Table the tool could not read is not "an Object Table that holds neither OID" ──────────

LB68_A4_HOLE = (0x1C08000, 0x1C0C000)   # the battery's A4 (P0.1 golden.json): the Object-Table root page, PLCN 0xc08 of
                                        # step1/win11refsmini (ps 0x1000000, 16 KiB page), punched to an image hole
# Wave C, C-2 (the sanctioned plant edit, LATER_GROUPS_TOLD "Added 2026-10-21 -- wave B closed"; applied by step C1's
# RED writer before B2's REDs): B2 reads the Object Table from its duplicate root when the primary's page fails its
# digest or cannot be read. On step1/win11refsmini the duplicate is checkpoint root 5 (table id 0x04), PLCN 0x3400
# (offset 0x4400000, 16 KiB), and holds OID 0x9 and 0xA, so the A4 copy would be read through it. The plant therefore
# punches the duplicate root too: the nodes below keep their meaning (NEITHER copy of the Object Table read). B2's
# own node for "primary unread, duplicate read in full" is in test_1132_red_c1_objtable.py.
LB68_A4_DUP_HOLE = (0x4400000, 0x4404000)
LB68_A4_HOLES = (LB68_A4_HOLE, LB68_A4_DUP_HOLE)
_LB68_UNREAD = re.compile(r"(?i)\bObject\s+Table\s+could\s+not\s+be\s+read\b[^.\n]*?\bLogfile\s+Information\s+Table\b"
                          r"[^.\n]*?\bcould\s+not\s+be\s+looked\s+up\b")


@contextlib.contextmanager
def _lb68_a4_copy():
    """A hole-preserving scratch copy of N423_IMAGE with the A4 range and (C-2) the duplicate root's range left as
    holes (the battery's punch, both copies of the Object Table), checked."""
    with MC.scratch_copy(N423_IMAGE, 64 << 20, omit=LB68_A4_HOLES) as (_src, p):
        for a, b in LB68_A4_HOLES:
            _fx(MC.read_block(p, a, b - a) == b"\0" * (b - a) and not [r for r in MC.data_ranges(p, a, b)],
                "the range 0x%x-0x%x is not a hole of the copy" % (a, b))
        yield p


def _lb68_run(path, *args):
    cmd = [sys.executable, "-B", FOREFST, path] + list(args)
    try:
        r = UW.run(cmd, capture_output=True, text=True, timeout=MC.TIMEOUT, cwd=os.path.dirname(path),
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


@pytest.mark.parametrize("cmd,mode", [("mlog", ("--stats",)), ("mlog", ("--json",)), ("mlog", ("--csv",)),
                                      ("timeline", ("--csv",))],
                         ids=["mlog-stats", "mlog-json", "mlog-csv", "timeline-csv"])
def test_lb68_an_object_table_that_could_not_be_read_is_not_said_to_hold_neither_oid_on_the_a4_copy(cmd, mode):
    args = (cmd,) + (("--fast",) if cmd == "timeline" else ()) + mode
    with _lb68_a4_copy() as p:
        rc, out, err = _lb68_run(p, *args)
    export = mode != ("--stats",)
    _keep(re.search(r"(?i)could not be read", err), "the run no longer says the Object Table's page could not be "
          "read" + _ctx(rc, out, err))
    said = _LB68_UNREAD.search(err if export else out)
    neither = n423_statements(out + "\n" + err)
    assert rc == 2 and said and not neither, "the A4 copy's Object Table could not be read: `%s` must exit 2 (exit %s), " \
        "say %s that the Object Table could not be read, so the Logfile Information Table could not be looked up " \
        "(%s), and never that it holds neither OID 0x9 nor OID 0xa (%d such statement(s); LB68)" % (
            " ".join(args), rc, _lb38_where(export), "said" if said else "not said", len(neither)) + _ctx(rc, out, err)


def test_lb68_the_a4_copys_bundle_manifest_says_the_object_table_could_not_be_read(tmp_path):
    outdir = str(tmp_path / "bundle")
    with _lb68_a4_copy() as p:
        rc, out, err = _lb68_run(p, "export", "metadata", "-o", outdir)
    man = os.path.join(outdir, "manifest.json")
    _fx(os.path.isfile(man), "export metadata wrote no manifest" + _ctx(rc, out, err))
    with open(man) as fh:
        warn = [w for w in (jdoc(json.load(fh), F._BUNDLE_KEYS).get("warnings") or []) if w.get("what") == "mlog"]
    _keep(len(warn) == 1 and not warn[0].get("failed"), "the manifest's MLog warnings: %r" % (warn,))
    reason = warn[0].get("reason") or ""
    assert _LB68_UNREAD.search(reason) and not _N423_NEITHER.search(reason), "the A4 bundle's manifest says %r: the " \
        "Object Table could not be read, so the Logfile Information Table could not be looked up -- not that it " \
        "holds neither OID (LB68)" % reason


def _lb68_partial_map(f):
    """The REAL build_object_map over a walk that reads ONE object row (OID 0x701) and records one page it could not
    read: an Object Table read in part, holding neither OID 0x9 nor OID 0xa among the rows read."""
    kd = b"\0" * 8 + struct.pack("<Q", 0x701)
    vd = bytearray(0x48)
    struct.pack_into("<Q", vd, 0x20, 0x50)

    def walk(*_a, **_k):
        F._walk_note_damage("unreadable", "page at plcn 0x99: short read (0 bytes) where a page was expected", page=0x99)
        return [(kd, bytes(vd))]
    real = F.walk_bplus
    F.walk_bplus = walk
    try:
        m = F.build_object_map(f, 0, 0x1000, MC._IdentityTr(), [0x99], register=False)
    finally:
        F.walk_bplus = real
    _fx(list(m) == [0x701], "the partial walk did not give the one object: %r" % (dict(m),))
    return m


@pytest.mark.parametrize("mode", [("--stats",), ("--json",)], ids=["stats", "json"])
def test_lb68_an_object_table_read_in_part_is_not_said_to_hold_neither_oid(monkeypatch, tmp_path, mode):
    """In-process: the patched bootstrap hands `cmd_mlog` the object map the real build_object_map made from a walk
    that read one row and could not read one page; the real get_mlog_info finds neither OID among the rows read."""
    log = SynLog(tmp_path / "lb68_mlog.raw").run(1, 0x20, 1, session_start=True).control(END, END).write()
    _n423_regs(monkeypatch)
    with open(log.path, "rb") as fh:
        om = _lb68_partial_map(fh)
    calls = Counter()

    def _boot(image, partition_start=None):
        calls["bootstrap"] += 1
        return open(log.path, "rb"), 0, log.cs, MC._IdentityTr(), [], om, 3, 14, []

    monkeypatch.setattr(F, "bootstrap", _boot)
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: {})
    rc, out, err = _n423_call("mlog", log.path, mode)
    _fx(calls["bootstrap"] == 1, "cmd_mlog did not read the volume through the patched bootstrap")
    export = mode == ("--json",)
    said = _LB68_UNREAD.search(err if export else out)
    neither = n423_statements(out + "\n" + err)
    assert rc == 2 and said and not neither, "an Object Table read in part (one page unread) holds neither OID 0x9 " \
        "nor OID 0xa among the rows read: `mlog %s` must exit 2 (exit %s), say %s that the Object Table could not be " \
        "read (in full), so the Logfile Information Table could not be looked up (%s), and never that it holds " \
        "neither (LB68)" % (" ".join(mode), rc, _lb38_where(export), "said" if said else "not said") \
        + _ctx(rc, out, err)


def test_lb68_matchers_accept_a_sound_output_and_reject_others():
    good = ("MLog: the Object Table could not be read, so the Logfile Information Table (OID 0x9 and OID 0xa), which "
            "gives the log's place, could not be looked up, and no log record can be located here.")
    assert _LB68_UNREAD.search(good) and _LB68_UNREAD.search(good.replace("be read,", "be read in full,"))
    assert not n423_statements(good)
    assert not _LB68_UNREAD.search("MLog: the Object Table holds neither OID 0x9 nor OID 0xa, the two copies of the "
                                   "Logfile Information Table; refs.sys would not open a log on this volume.")
    assert not _LB68_UNREAD.search("the Object Table could not be read")
