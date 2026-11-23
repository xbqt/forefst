"""1.13.2 RED cases, group b2_journal: running-log items N131, N132, N148 (conditional), N195, N196.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` -- the fourth revision (top: N131 and N132 enter RC1, "A7, N126 and
N132 share one rule on image holes"), section 5 "RED first", decision 19 (the maintainer's bar: every RED fails on
1.13.1 BECAUSE of the defect, not because of an artefact, and is independently confirmed). The items have no plan
row of their own; their text and acceptance come from `RUNNING_LOG.md` (N131, N132, N148, N195, N196),
`RC1_DEPS_CHECKPOINT.md` table 2 (N131: RC1, removes a false exit 2 -- also PLAN D5; N132: RC1, wording),
`E2_RC2_CLASSIFICATION.md` (cause C11, new defects N-a and N-f, V-10 and the C01/C11 confirmations) and
`LAB_J_RESULTS.md` sections 2-4 (N195, N196). Report, with the observed or expected failure of every node:
`analysis/reports/v1.13.2/red/RED_b2_journal.md`.

The hole rule (C8 = B, the maintainer, 2026-10-01; it replaced the fourth revision's "reported as unreadable"): data
the volume needs that is missing, or reads as zero, inside an image hole is a finding -- exit 2 -- worded neutrally:
"the image stores this range as a hole: not captured, or zero on the disk; the cause cannot be told from the image".
Space the volume does not need (ring space past the journal's tail) is not a finding.

What each RED asserts
---------------------
N131 An allocated `$J` that holds no record and not one non-zero byte, on a volume where no file points into the
     journal (every per-file LastUsn and UsnJournalId is 0), is not reported as "never written OR wiped": the
     per-file witness separates the two, so `usn --info/--csv/--stats`, `timeline --csv` and `timestomp --csv` exit
     0 on win11afterblindaudit_empty (the 5 C11 golden rows). A journal that files DO point into keeps exit 2
     (controls, including a file whose only record is USN 0: the witness is the journal id, not LastUsn > 0).
N132 A zero metadata page is never labelled "acquisition gap" or "not damage" without evidence: a page inside an
     image hole is named as stored as a hole with the cause left open (C8 = B), a zero object root outside any hole is not
     called an acquisition gap, and no output string in either tool makes the claim (the class, found by rg:
     fd:1052, :1133, :14969, :15012, :15028, :15230). The finding itself (exit 2) is kept.
N148 (conditional -- it reproduces, so the RED is written.) `usn` and `timeline` (and `timestomp`, the third site
     found by rg: fd:9907) say that records in the written span of `$J` lie in an image hole, with the cause left
     open, and exit 2 (C8 = B).
     1.13.1 skips them with no note (a hole of one cluster: 38 records gone, exit 0) or calls them destroyed (a
     hole larger than 64 KiB). Controls: unwritten ring space stored as a hole is NOT reported, and zeros that
     are written (not a hole) are not called a hole.
N195 The per-file UsnJournalId is visible (`details`, `details --json`), and `summary` does not hide a journal id
     that a minority of files carry: on labJjournal m1-m3 carry the first journal's id 0x01dd4e57f72ac89e, the
     only on-volume trace of the delete-then-create, and `summary` prints only the majority 0x01dd4e57f84a6362.
N196 Pointers from a discarded journal instance are named, not silent: on labJjournal m1-m3's LastUsn (240, 256,
     272) lie below the current tail (31576) and point into records of other files; `usn --info`, `timeline` and
     `timestomp` must name the earlier instance (its id) as distinct from the current journal.

Three kinds of node
-------------------
* unit -- synthetic bytes in pytest's tmp dir, in-process, with the module's registers reset:
  - the ``_Journal`` harness: a sparse file carrying a synthetic `$J` (real USN_RECORD_V3 records, a real image hole
    where the case needs one), driven through the REAL `cmd_usn` / `cmd_timeline`, `read_usn_j_stream`,
    `parse_usn_records`, `parse_usn_journal_metadata`, `_usn_report_destroyed_tail` and exit rule. Only the volume
    plumbing is stubbed: `bootstrap`, `locate_change_journal`, `parse_usn_journal_streams`, `build_oid_path_map`,
    `get_mlog_info`, and `walk_directory_tree`, which supplies the per-file LastUsn/UsnJournalId witness
    (1.13.1 reads that witness through `walk_directory_tree`, fd:4880). The journal id reaches the tool through the
    real resident-$Max parse (fd:5015-5031), not a stub.
  - N132 probes of `_walk` (on a real sparse file) and `verify_object_root`, and a static scan of the string
    literals of both tools (docstrings excluded).
* ``image`` -- the real CLI, read-only, on a corpus image (win11afterblindaudit_empty, labJjournal,
  win11refs2tmillionsofactions, labBeforeF). Skipped when the image is absent. Nothing is written to the image.
* ``image`` planted -- a hole-preserving scratch copy of labBeforeF (8.7 MB allocated, battery-recipe style:
  `analysis/verification/phase0/P0.1_damaged_golden/bin/damage.py` ops "punch" and "zero"), built at test time
  under ``$FOREFST_RED_SCRATCH`` (default: ``forefst_red_scratch`` in the system temp directory), checked before and
  after the damage, and deleted by exact path when the module's image nodes end.

``pytest -k "not image"`` runs the unit nodes only (no corpus, no scratch copy).

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; the fix commit removes the mark and an XPASS fails the
  run. Only a plain ``assert`` states the acceptance.
* A fixture that is not what the case needs, a crash or a timeout raises ``RedFixtureError``; a property 1.13.1
  already has and the fix must keep raises ``KeptPropertyBroken``. Neither is an AssertionError.
* Premises are checked at test time from the bytes, by readers of this module that share no code with the tool:
  the `$J` records (own USN_RECORD_V3 carve), the per-file row fields (own directory-row reader at pinned offsets
  or by name), the image holes (SEEK_DATA). Nothing is trusted from a report.
* Each unit RED has a control that differs from it in the defect's trigger only and passes on 1.13.1 (a hole in the
  written span against a hole beyond it and against written zeros; no pointer against a pointer; a stale id
  against one id; a zero page in a hole against written zeros).
* The matchers are exercised by a non-xfail self-test that shows they accept a corrected wording and reject the
  1.13.1 lines.
"""
import ast
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions, carve, scratch discipline)
import test_1132_red_a_verdicts as AV                    # noqa: E402  (the A10 matchers: one hole rule, one reading)

FOREFST = AB.FOREFST
REFSANALYSIS = AB.REFSANALYSIS
SCRATCH = AB.SCRATCH
TIMEOUT = 900
MAX_SCRATCH_ALLOCATED = 64 << 20
RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, AB._red
_split, _sentences, _hole_stated = AV._split, AV._sentences, AV._hole_stated
_hex_id, _BOUNDARY, _DESTROYED_CLAIM, _JOURNAL, _HOLE, _HOLE_CAUSE = (
    AV._hex_id, AV._BOUNDARY, AV._DESTROYED_CLAIM, AV._JOURNAL, AV._HOLE, AV._HOLE_CAUSE)


def _page_hole_stated(texts, lcn):
    """Lines that name page `lcn` as stored as an image hole, with the cause left open (C8 = B)."""
    return [t for t in texts if ("0x%x" % lcn) in t and _HOLE.search(t) and _HOLE_CAUSE.search(t)]
_run_corpus, _corpus, _cctx, _rc_escalate = AV._run_corpus, AV._corpus, AV._cctx, AV._rc_escalate


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# matchers (each exercised by test_b2_journal_matchers_accept_corrected_wording_and_reject_the_1131_lines)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_WIPE = re.compile(r"(?i)\bwip(?:e|ed|ing)\b")
_NEVER_WRITTEN = re.compile(r"(?i)\bnever\s+written\b")
_CANNOT_SEPARATE = re.compile(r"(?i)\b(?:cannot|can ?not|could not)\s+(?:distinguish|tell|separate)\b")
_OR_PAIR = re.compile(r"(?i)never\s+written\W+(?:\w+\W+){0,6}?or\W+(?:\w+\W+){0,6}?wip"
                      r"|wip\w*\W+(?:\w+\W+){0,6}?or\W+(?:\w+\W+){0,6}?never\s+written")


def _undecided_wipe(sentences):
    """N131: a sentence that leaves the journal 'never written OR wiped' (1.13.1, fd:4677-4680: "this is a journal
    that was never written OR one that was wiped, and the stream cannot distinguish them")."""
    return [s for s in sentences if _JOURNAL.search(s) and (
        _OR_PAIR.search(s) or (_CANNOT_SEPARATE.search(s) and (_WIPE.search(s) or _NEVER_WRITTEN.search(s))))]


_JDAMAGE = re.compile(r"(?i)\bwip(?:e|ed|ing)\b|destroy\w*|\bzeroed\b|\bmissing\b|\bremoved\b|\blost\b|"
                      r"not on the volume|\bincomplete\b|not the whole")


def _journal_damage(sentences):
    """A sentence that says journal records are gone (wiped, destroyed, missing ...): the N131 controls' finding."""
    return [s for s in sentences if _JOURNAL.search(s) and _JDAMAGE.search(s)]


_GAP = re.compile(r"(?i)acquisition\s+gap")
_NOT_DAMAGE = re.compile(r"(?i)\bnot\s+damage\b")
_GAP_HEDGE = re.compile(r"(?i)\b(?:cannot|can ?not|could not|does not|do not)\s+(?:tell|say|show|distinguish|"
                        r"separate|prove)\b|\bcan ?not be told\b|\beither\b|\bambiguous\b|"
                        r"\bor\s+(?:an?\s+|the\s+)?(?:\w+\s+)?(?:never|not|zeroed|unwritten)\b")


def _gap_claims(texts):
    """N132: a text that calls a zero page 'not damage', or an 'acquisition gap' without saying that a hole cannot
    tell that from a page never written or zeroed (1.13.1: fd:1052, :1133, :14969, :15012, :15028, :15230)."""
    out = []
    for s in texts:
        if _NOT_DAMAGE.search(s) or (_GAP.search(s) and not _GAP_HEDGE.search(s)):
            out.append(s)
    return out


def _id_re(j):
    """A journal id in any rendering: 0x-hex (zero-padded or not, any case) or decimal."""
    return re.compile(r"(?i)(?<![0-9a-fx])(?:0x)?0*%x(?![0-9a-f])|(?<!\d)%d(?!\d)" % (j, j))


def _names_other_instance(prose, old):
    """N196: a line names the earlier instance's id next to (+-2 lines) a boundary word (instance, re-created,
    previous/earlier/different journal ...)."""
    rid = _id_re(old)
    return [l for i, l in enumerate(prose)
            if rid.search(l) and _BOUNDARY.search(" ".join(prose[max(0, i - 2):i + 3]))]


_FT_ID = re.compile(r"(?i)(?<![0-9a-f])(?:0x)?(01d[0-9a-f]{13})(?![0-9a-f])")


def _journal_ids_named(text):
    """Every FILETIME-shaped journal id (0x01d...) a text names."""
    return {int(m, 16) for m in _FT_ID.findall(text)}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# independent readers (share no code with forefst)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _data_ranges(path, lo=0, hi=None):
    """[(start, end)] of the allocated (non-hole) ranges of a file inside [lo, hi)."""
    fd = os.open(path, os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        hi = size if hi is None else min(hi, size)
        out, pos = [], lo
        while pos < hi:
            try:
                d = os.lseek(fd, pos, os.SEEK_DATA)
            except OSError:
                break
            if d >= hi:
                break
            h = min(os.lseek(fd, d, os.SEEK_HOLE), hi)
            out.append((d, h))
            pos = h
        return out
    finally:
        os.close(fd)


def _is_hole(path, lo, n):
    return not _data_ranges(path, lo, lo + n)


def _usn_v3_at(buf, o):
    """(record_length, usn, name) if a plausible USN_RECORD_V3 starts at buf[o], else None."""
    if o + 0x50 > len(buf):
        return None
    rl, maj, mn = struct.unpack_from("<IHH", buf, o)
    if maj != 3 or mn != 0 or not (0x50 <= rl <= 0x250) or rl % 8 or o + rl > len(buf):
        return None
    nl, no = struct.unpack_from("<HH", buf, o + 0x48)
    ts = struct.unpack_from("<Q", buf, o + 0x30)[0]
    if no != 0x4C or not nl or nl % 2 or no + nl > rl or not (0x01D0000000000000 < ts < 0x01E0000000000000):
        return None
    return rl, struct.unpack_from("<Q", buf, o + 0x28)[0], buf[o + no:o + no + nl].decode("utf-16-le", "replace")


def _carve_journal(buf):
    """Records of a $J buffer whose USN IS their offset in it (the USN_RECORD_V3 invariant): [(usn, len, name)]."""
    out, o = [], 0
    while o <= len(buf) - 0x50:
        r = _usn_v3_at(buf, o)
        if r and r[1] == o:
            out.append((o, r[0], r[2]))
            o += r[0]
            continue
        o += 8
    return out


def _carve_anywhere(path):
    """Every plausible USN_RECORD_V3 in the allocated bytes of an image (not tied to a $J map)."""
    n = 0
    with open(path, "rb") as fh:
        for d, h in _data_ranges(path):
            fh.seek(d)
            buf = fh.read(h - d)
            o = 0
            while o <= len(buf) - 0x50:
                r = _usn_v3_at(buf, o)
                if r:
                    n += 1
                    o += r[0]
                    continue
                o += 8
    return n


def _dir_row(buf, r, name=None):
    """A type-0x30 directory row at buf[r]: (name, LastUsn value+0x68, UsnJournalId value+0x70) or None.
    Row header <I row_len><H key_off><H key_len><H flags><H val_off><H val_len>; key = u16 type 0x30, u16, UTF-16."""
    if r < 0 or r + 0x14 > len(buf):
        return None
    _rl, ko, kl, _fl, vo, vl = struct.unpack_from("<IHHHHH", buf, r)
    if ko != 0x10 or kl < 6 or struct.unpack_from("<H", buf, r + ko)[0] != 0x30 or r + vo + vl > len(buf):
        return None
    nm = buf[r + ko + 4:r + ko + kl].decode("utf-16-le", "replace")
    if name is not None and nm != name:
        return None
    if vl < 0x78:
        return nm, None, None
    return nm, struct.unpack_from("<Q", buf, r + vo + 0x68)[0], struct.unpack_from("<Q", buf, r + vo + 0x70)[0]


def _rows_by_name(path, names):
    """{name: [(image_offset, LastUsn, UsnJournalId)]} for every row copy of each name in the allocated bytes."""
    got = {n: [] for n in names}
    with open(path, "rb") as fh:
        for d, h in _data_ranges(path):
            fh.seek(d)
            buf = fh.read(h - d)
            for n in names:
                nb = n.encode("utf-16-le")
                i = buf.find(nb)
                while i >= 0:
                    row = _dir_row(buf, i - 0x14, n)
                    if row:
                        got[n].append((d + i - 0x14, row[1], row[2]))
                    i = buf.find(nb, i + 1)
    return got


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# the in-process harness: a synthetic $J on a sparse file, the real journal code path
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

HCS = 4096
J_PLCN = 0x10                           # $J virtual 0 = file offset 0x10000
JID_ONE = 0x01DD485DE7522417            # the labBeforeF / win11afterblindaudit_empty instance (created 2026-09-19)
JID_OLD = 0x01DD4E57F72AC89E            # labJjournal: the first journal (S1-S3), carried by m1-m3
JID_NEW = 0x01DD4E57F84A6362            # labJjournal: the journal re-created by deletejournal + createjournal (S5)
FT_BEFORE = JID_ONE - 10 ** 8           # 10 s before the journal was created (the journal id IS its creation time)

_REGISTERS = ("_FINDINGS", "_SKIP_FINDING", "_WALK_DAMAGE", "_WALK_DAMAGE_REPORTED", "_REDUNDANCY_FINDING",
              "_CHKP_STALE", "_JOURNAL_TAIL_DESTROYED", "_VERSION_CONTRADICTED", "_SUPB_FELL_BACK", "_CONTENT_HOLES",
              "_CONTENT_UNDET", "_JOURNAL_WIPE_SUSPECT", "_HOLE_STREAMS", "_SKIP_NOTES", "_SKIP_EXPECTED",
              "_DEFERRALS", "_OBJ_ROOT_REF", "_OBJ_ROOT_VERIFIED", "_OBJ_ROOT_LCNS")


def _fresh(monkeypatch):
    """Every run-level register of forefst starts empty and is restored afterwards (monkeypatch)."""
    for name in _REGISTERS:
        cur = getattr(F, name, None)
        if isinstance(cur, (list, dict, set)):
            monkeypatch.setattr(F, name, type(cur)())


def _usn_record(usn, name, fid, ts, reason=0x100):
    nm = name.encode("utf-16-le")
    rl = (0x4C + len(nm) + 7) & ~7
    b = bytearray(rl)
    struct.pack_into("<IHH", b, 0, rl, 3, 0)
    struct.pack_into("<QQ", b, 0x08, fid, 0x706)          # FileReferenceNumber 0x706:fid
    struct.pack_into("<QQ", b, 0x18, 0, 0x706)            # parent 0x706:0
    struct.pack_into("<QQII", b, 0x28, usn, ts, reason, 0)
    struct.pack_into("<IIHH", b, 0x40, 0, 0x20, len(nm), 0x4C)
    b[0x4C:0x4C + len(nm)] = nm
    return bytes(b)


class _Journal:
    """A sparse file carrying a $J of `nclusters` clusters at PLCN J_PLCN.

    `records` clusters are filled with USN_RECORD_V3s (USN = offset, never crossing a 4 KiB boundary, as on disk);
    those also in `holes` are NOT written (the records existed, the image stores the cluster as a hole); clusters in
    `zeros` are written as real zeros; every other cluster stays a hole (unwritten ring space). Checked after the
    build from the file itself: the hole layout (SEEK_DATA) and the records by this module's own carve."""

    def __init__(self, tmp_path, nclusters, records=(), holes=(), zeros=()):
        self.path = str(tmp_path / "target.raw")
        self.nclusters = nclusters
        self.recs = []                                   # (usn, len, cluster, in_hole)
        records, holes, zeros = set(records), set(holes), set(zeros)
        with open(self.path, "wb") as fh:
            fh.truncate((J_PLCN + nclusters + 16) * HCS)
            fh.seek(0)
            fh.write(b"\x01" * HCS)                      # one allocated cluster before the journal
            for c in range(nclusters):
                if c in zeros:
                    fh.seek((J_PLCN + c) * HCS)
                    fh.write(b"\0" * HCS)
                    continue
                if c not in records:
                    continue
                buf, off = bytearray(HCS), 0
                while True:
                    r = _usn_record(c * HCS + off, "f%02d_%04x.txt" % (c, off), 0x10 + c, JID_ONE + c * HCS + off)
                    if off + len(r) > HCS - 0x60:
                        break                            # the rest of the page stays zero padding
                    buf[off:off + len(r)] = r
                    self.recs.append((c * HCS + off, len(r), c, c in holes))
                    off += len(r)
                if c not in holes:
                    fh.seek((J_PLCN + c) * HCS)
                    fh.write(bytes(buf))
        # ---- fixture checks, from the file itself ----
        for c in range(nclusters):
            written = (c in zeros) or (c in records and c not in holes)
            _fx(_is_hole(self.path, (J_PLCN + c) * HCS, HCS) != written,
                "$J cluster %d: expected %s in the file" % (c, "data" if written else "a hole"))
        with open(self.path, "rb") as fh:
            fh.seek(J_PLCN * HCS)
            got = [u for u, _l, _n in _carve_journal(fh.read(nclusters * HCS))]
        want = [u for u, _l, _c, h in self.recs if not h]
        _fx(got == want, "the file carries %d records, the plan %d" % (len(got), len(want)))

    @property
    def usn_max(self):
        return max(u for u, _l, _c, _h in self.recs)

    def n(self, in_hole=None):
        return sum(1 for r in self.recs if in_hole is None or r[3] == in_hole)


def _entry(i, usn, jid, name=None, is_dir=False, ts=FT_BEFORE):
    """One row of the per-file witness, as walk_directory_tree returns it (LastUsn = "usn", "usn_journal_id")."""
    return {"name": name or "e%d.txt" % i, "path": "labJ/" + (name or "e%d.txt" % i), "is_dir": is_dir,
            "oid": 0x706 if is_dir else 0, "home_oid": 0x706, "file_id": 0 if is_dir else i,
            "create_time": ts, "modify_time": ts, "change_time": ts, "access_time": ts,
            "usn": usn, "usn_journal_id": jid, "file_size": 12, "is_resident": True}


def _empty_valid_mlog(monkeypatch, path, nclusters):
    """LB61 (wave B part 3d, N423; the sanctioned fixture edit): the harness's MLog is an EMPTY, VALID log. The harness
    stubbed `get_mlog_info` to None, which meant "no MLog on this volume"; since N423 None is an Object Table that
    holds neither OID 0x9 nor OID 0xA -- a finding of `timeline`'s MLog source, exit 2 -- so the stub keeps its meaning
    (the MLog source adds no row, no statement and no finding) by being a log that passes every check and holds
    nothing: a Logfile Information row as both table copies give it (48 bytes, a size of 0x50 clusters), two control
    copies built by test_1132_red_mlog_chkp's codec as its SynLog writes them (log start = log end: nothing logged),
    written into this file after its $J and its 16 spare clusters, and a data area of 0x50 clusters of written zeros."""
    import test_1132_red_mlog_chkp as MC
    base = J_PLCN + nclusters + 16                       # the end of the file as _Journal (and waveb_rest's _JFile) build it
    ds, size, at = base + 2, 0x50, MC.lsn(1, 1)
    with open(path, "r+b") as fh:
        fh.truncate(max(os.path.getsize(path), (ds + size) * HCS))
        for i, seq in enumerate((51, 50)):
            fh.seek((base + i) * HCS)
            fh.write(MC.control_block(MC.MAGIC_A, MC.UUID_A, seq, ds, ds + size, at, at, 3))
        fh.seek(ds * HCS)
        fh.write(b"\0" * (size * HCS))
    for i in range(2):                                   # checked from the file by the codec, not by the tool
        c = MC.parse_block(MC.read_block(path, (base + i) * HCS))
        _fx(c and c["type"] == 1 and c["fold"] == c["stored"] and (c["ds"], c["de"], c["start"], c["end"]) == (
            ds, ds + size, at, at), "the empty MLog's control copy %d is not what the stub needs: %r" % (i, c))
    info = {"oid": 0x9, "rows": 2, "table_oids": [0x9, 0xA], "row_len": 0x30, "table_name": "Logfile Information Table",
            "data_start_lcn": ds, "data_end_lcn": ds + size, "data_size_clusters": size,
            "ctrl_plcn_0": base, "ctrl_plcn_1": base + 1}
    monkeypatch.setattr(F, "get_mlog_info", lambda *a, **k: dict(info))


def _harness(monkeypatch, capsys, jr, cmd, args, entries, jid=JID_ONE):
    """Run the REAL cmd_usn / cmd_timeline over the synthetic $J. Returns (rc, stdout, stderr, walker_calls)."""
    _fresh(monkeypatch)
    raw = bytearray(0x24)                                # the resident $Max sub-record (fd:5015-5031)
    struct.pack_into("<I", raw, 8, 12)
    struct.pack_into("<QQQ", raw, 12, jr.nclusters * HCS, 0, jid)
    streams = {"j_extents": [{"vlcn": J_PLCN, "plcn": J_PLCN, "file_vcn": 0, "clusters": jr.nclusters,
                              "flags": 0x50}],           # flagged written, as the corpus $J runs are (E2 C11)
               "j_stream_size": 0x000E0080, "max_extents": [], "max_stream_size": 0,
               "metadata_raw": bytes(raw), "subrecord_count": 3, "j_declared": None}
    calls = {"walk": 0}

    def walk(*_a, **_k):
        calls["walk"] += 1
        return [dict(e) for e in entries]

    monkeypatch.setattr(F, "bootstrap", lambda image, ps: (open(jr.path, "rb"), 0, HCS, None, {},
                                                           {F.OID_FS_METADATA: [1]}, 3, 14, []))
    monkeypatch.setattr(F, "locate_change_journal", lambda *a, **k: (
        b"\0" * 720, {"value_len": 720, "stream_count": 3, "create_time": jid}))
    monkeypatch.setattr(F, "parse_usn_journal_streams", lambda *a, **k: dict(
        streams, j_extents=[dict(e) for e in streams["j_extents"]]))
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: {})
    _empty_valid_mlog(monkeypatch, jr.path, jr.nclusters)     # LB61: was get_mlog_info -> None ("no MLog")
    monkeypatch.setattr(F, "walk_directory_tree", walk)
    capsys.readouterr()
    fn = {"usn": F.cmd_usn, "timeline": F.cmd_timeline}[cmd]
    try:
        ret = fn(jr.path, list(args), None)
    except SystemExit as e:
        raise RedFixtureError("%s %s exited (%r) -- a usage or bootstrap error, not the defect:\n%s"
                              % (cmd, " ".join(args), e.code, capsys.readouterr().err[-2000:]))
    except Exception as e:                                # a crash is never the defect under test
        raise RedFixtureError("%s %s crashed: %r" % (cmd, " ".join(args), e)) from e
    rc = _rc_escalate()(0 if ret is None else ret)
    cap = capsys.readouterr()
    return rc, cap.out, cap.err, calls


def _hctx(cmd, args, rc, out, err):
    return "\n[harness] %s %s | rc=%d\n--- stdout (tail) ---\n%s\n--- stderr (tail) ---\n%s" % (
        cmd, " ".join(args), rc, out[-2500:], err[-2500:])


HARNESS_CMDS = [("usn", ("--info",)), ("usn", ("--stats",)), ("usn", ("--csv",)), ("timeline", ("--csv",))]
HARNESS_IDS = ["usn-info", "usn-stats", "usn-csv", "timeline-csv"]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N131 -- an allocated, all-zero $J that no file points into is not "never written OR wiped" (false exit 2)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _n131_entries():
    """win11afterblindaudit_empty's three entries: all written before the journal existed, LastUsn 0, id 0."""
    return [_entry(0, 0, 0, name="System Volume Information", is_dir=True),
            _entry(2, 0, 0, name="WPSettings.dat"),
            _entry(0x18, 0, 0, name="FVE2.{8252fd17-a486-4ad4-b1ca-f4fe64d23218}")]


# RED 1.13.2 N131: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd,args", HARNESS_CMDS, ids=HARNESS_IDS)
@pytest.mark.parametrize("form", ["hole", "zeros"])
def test_n131_journal_no_file_points_into_is_not_called_possibly_wiped(monkeypatch, capsys, tmp_path, form, cmd, args):
    """form: the $J is an image hole (as on win11afterblindaudit_empty, whose 32 MiB $J holds 0 allocated bytes) or
    written zeros. Either way no record exists and no file carries this journal's id or a LastUsn."""
    jr = _Journal(tmp_path, 8, zeros=range(8) if form == "zeros" else ())
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, cmd, args, _n131_entries())
    prose, _h, _r = _split(out, err)
    ctx = _hctx(cmd, args, rc, out, err)
    assert not _undecided_wipe(_sentences(prose)), "the journal is still left 'never written OR wiped'" + ctx
    assert rc == 0, "a journal nothing was written to is not a finding: exit 0" + ctx


@pytest.mark.parametrize("witness", ["pointer-past-0", "pointer-at-usn-0"])
def test_n131_control_journal_files_point_into_keeps_exit_2(monkeypatch, capsys, tmp_path, witness):
    """Not a RED. The same all-zero $J, written zeros (a wipe on written blocks, the hole rule's exit-2 case), and a
    file whose record says the journal WAS written: LastUsn 20000 with this journal's id, or LastUsn 0 with this
    journal's id (a file whose only record is USN 0 -- the witness is the id, not LastUsn > 0). 1.13.1 exits 2
    (through the all-zero check); the fix must keep exit 2 and say that records are gone.
    If a fix reads the per-file witness through a walker other than walk_directory_tree, extend _harness."""
    jr = _Journal(tmp_path, 8, zeros=range(8))
    usn = 20000 if witness == "pointer-past-0" else 0
    ents = _n131_entries() + [_entry(0x30, usn, JID_ONE, name="written_after_the_journal.txt", ts=JID_ONE + 10 ** 7)]
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, "usn", ("--info",), ents)
    prose, _h, _r = _split(out, err)
    ctx = _hctx("usn", ("--info",), rc, out, err)
    assert rc == 2, ctx
    assert _journal_damage(_sentences(prose)), "nothing says the journal's records are gone" + ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N148 -- records inside an image hole in the written span of $J: the hole is stated, cause open, exit 2 (C8 = B)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _n148_journal(tmp_path, size):
    """small: 8 clusters, records in 0-4, cluster 2 an image hole (38 records), 5-7 unwritten ring (holes).
    large: 32 clusters, records in 0-21, clusters 2-19 an image hole (18 clusters = 73,728 B > USN_MAX_RECORD),
    22-31 unwritten ring (holes)."""
    if size == "small":
        return _Journal(tmp_path, 8, records=range(5), holes={2})
    return _Journal(tmp_path, 32, records=range(22), holes=set(range(2, 20)))


# RED 1.13.2 N148: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd,args", HARNESS_CMDS, ids=HARNESS_IDS)
@pytest.mark.parametrize("size", ["small", "large"])
def test_n148_records_inside_a_hole_in_the_written_span_are_stated_as_a_hole_and_exit_2(monkeypatch, capsys,
                                                                                        tmp_path, size, cmd, args):
    jr = _n148_journal(tmp_path, size)
    _fx(jr.n(in_hole=True) > 0 and jr.n(in_hole=False) > 0, "the hole must hold records and records must survive")
    ents = [_entry(1, jr.usn_max, JID_ONE, ts=JID_ONE + 10 ** 7)]      # the tail is whole: only the hole is missing
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, cmd, args, ents)
    prose, _hdr, rows = _split(out, err)
    ctx = _hctx(cmd, args, rc, out, err)
    survivors = jr.n(in_hole=False)
    if (cmd, args) == ("usn", ("--info",)):
        _keep(re.search(r"Count:\s+%d\b" % survivors, out) is not None,
              "usn --info must still count the %d records outside the hole" % survivors + ctx)
    if (cmd, args) == ("usn", ("--csv",)):
        _keep(len(rows) == survivors, "usn --csv must still list the %d records outside the hole (lists %d)"
              % (survivors, len(rows)) + ctx)
    assert _hole_stated(_sentences(prose)), (
        "%d record(s) in %d byte(s) of $J that the image stores as a hole: nothing says so with the cause left open "
        "(not captured, or zero on the disk)" % (jr.n(in_hole=True), HCS * (1 if size == "small" else 18))) + ctx
    assert rc == 2, "records the journal needs are missing inside an image hole: exit 2 (C8 = B)" + ctx


# RED 1.13.2 N148: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd,args", [("usn", ("--info",)), ("timeline", ("--csv",))], ids=["usn-info", "timeline-csv"])
def test_n148_a_hole_in_the_written_span_is_not_called_destroyed(monkeypatch, capsys, tmp_path, cmd, args):
    jr = _n148_journal(tmp_path, "large")
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, cmd, args, [_entry(1, jr.usn_max, JID_ONE)])
    prose, _h, _r = _split(out, err)
    bad = [l for l in prose if _DESTROYED_CLAIM.search(l)]
    assert not bad, "an image hole is reported as destroyed journal: %r" % bad[:2] + _hctx(cmd, args, rc, out, err)


@pytest.mark.parametrize("cmd,args", HARNESS_CMDS, ids=HARNESS_IDS)
def test_n148_control_unwritten_ring_space_in_a_hole_is_not_reported(monkeypatch, capsys, tmp_path, cmd, args):
    """Not a RED. The same journal with no hole inside the written span: the ring beyond the last record is a hole,
    as on every sparse corpus image (labBeforeF: 48 KiB written, the other 32 MiB holes). Nothing is missing, so
    nothing may be reported as a hole, and the run exits 0 (1.13.1 does; the fix must keep it)."""
    jr = _Journal(tmp_path, 8, records=range(5))
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, cmd, args, [_entry(1, jr.usn_max, JID_ONE)])
    prose, _h, _r = _split(out, err)
    ctx = _hctx(cmd, args, rc, out, err)
    assert not _hole_stated(_sentences(prose)), "unwritten ring space reported as a hole" + ctx
    assert rc == 0, ctx


@pytest.mark.parametrize("cmd,args", [("usn", ("--info",)), ("timeline", ("--csv",))], ids=["usn-info", "timeline-csv"])
def test_n148_control_written_zeros_in_the_span_are_not_called_a_hole(monkeypatch, capsys, tmp_path, cmd, args):
    """Not a RED. The small case with cluster 2 WRITTEN as zeros instead of a hole: the same bytes, the trigger
    (an image hole) removed. The tool may not call it a hole (below 64 KiB it is the stated N48 limit, "surgical
    removal under 65,536 B", PLAN section 6). 1.13.1 says nothing; the fix must not claim a hole here."""
    jr = _Journal(tmp_path, 8, records={0, 1, 3, 4}, zeros={2})
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, cmd, args, [_entry(1, jr.usn_max, JID_ONE)])
    prose, _h, _r = _split(out, err)
    assert not _hole_stated(_sentences(prose)), (
        "a journal with NO image hole in its written span (cluster 2 is written zeros; only the ring past the tail, "
        "clusters 5-7, is a hole) is reported as a hole") + _hctx(cmd, args, rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N196 -- pointers from a discarded journal instance below the new tail are silent
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _n196_entries(stale):
    """labJjournal's shape: the current journal's files, a file written with no journal (id 0), and -- when
    `stale` -- m1-m3, whose LastUsn (240, 256, 272) and id belong to the discarded first journal."""
    ents = [_entry(5, 0x100, JID_NEW, name="m5_after_delete_create.txt", ts=JID_NEW + 10 ** 5),
            _entry(3, 0, 0, name="m0_no_journal_yet.txt"),
            _entry(9, None, JID_NEW, name="toucher.txt", ts=JID_NEW + 10 ** 6)]
    if stale:
        ents += [_entry(4, 240, JID_OLD, name="m1_after_create.txt", ts=JID_OLD + 10 ** 5),
                 _entry(7, 256, JID_OLD, name="m2_after_recreate_same.txt", ts=JID_OLD + 10 ** 6),
                 _entry(6, 272, JID_OLD, name="m3_after_recreate_resize.txt", ts=JID_OLD + 10 ** 7)]
    return ents


def _n196_journal(tmp_path):
    return _Journal(tmp_path, 8, records=range(3))                   # 3 written clusters, the rest unwritten ring


N196_CMDS = [("usn", ("--info",)), ("timeline", ("--csv",))]
N196_IDS = ["usn-info", "timeline-csv"]


# RED 1.13.2 N196: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd,args", N196_CMDS, ids=N196_IDS)
def test_n196_pointers_from_a_discarded_journal_instance_are_named(monkeypatch, capsys, tmp_path, cmd, args):
    jr = _n196_journal(tmp_path)
    ents = _n196_entries(stale=True)
    for e in ents:
        if e["usn"] is None:
            e["usn"] = jr.usn_max                                       # toucher: the current tail
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, cmd, args, ents, jid=JID_NEW)
    prose, _h, _r = _split(out, err)
    ctx = _hctx(cmd, args, rc, out, err)
    if cmd == "usn":
        _keep(_id_re(JID_NEW).search(out) is not None, "usn --info must still print the current journal id" + ctx)
    assert _names_other_instance(prose, JID_OLD), (
        "nothing names the earlier journal instance 0x%016x that 3 files' LastUsn/id belong to" % JID_OLD) + ctx


@pytest.mark.parametrize("cmd,args", N196_CMDS, ids=N196_IDS)
def test_n196_control_one_journal_instance_names_no_other(monkeypatch, capsys, tmp_path, cmd, args):
    """Not a RED. The same volume without the three stale rows: every file carries the current id or 0. No other
    journal id may be named, and the run exits 0 (1.13.1 does; the fix must keep it)."""
    jr = _n196_journal(tmp_path)
    ents = _n196_entries(stale=False)
    for e in ents:
        if e["usn"] is None:
            e["usn"] = jr.usn_max
    rc, out, err, _c = _harness(monkeypatch, capsys, jr, cmd, args, ents, jid=JID_NEW)
    ctx = _hctx(cmd, args, rc, out, err)
    assert _journal_ids_named(out + err) <= {JID_NEW}, ctx
    assert rc == 0, ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N132 -- zero pages are not labelled "acquisition gap, not damage" without evidence
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

N132_LCN = 0x40                                        # a 16 KiB page (4 clusters) at file offset 0x40000


def _n132_file(tmp_path, form):
    p = str(tmp_path / "vol.raw")
    with open(p, "wb") as fh:
        fh.truncate(1 << 20)
        fh.seek(0)
        fh.write(b"\x01" * HCS)
        if form == "zeros":
            fh.seek(N132_LCN * HCS)
            fh.write(b"\0" * 4 * HCS)
    _fx(_is_hole(p, N132_LCN * HCS, 4 * HCS) == (form == "hole"),
        "the page region is not %s" % ("a hole" if form == "hole" else "written"))
    return p


def _walk_zero_page(monkeypatch, capsys, path):
    _fresh(monkeypatch)
    capsys.readouterr()
    with open(path, "rb") as fh:
        rows = F._walk(b"\0" * (4 * HCS), fh, 0, HCS, None, 3, None, [N132_LCN + i for i in range(4)])
    F._walk_damage_summary()
    cap = capsys.readouterr()
    texts = ["%s: %s" % kd for kd in F._WALK_DAMAGE] + (cap.out + cap.err).splitlines()
    _fx(rows == [], "a zero page yields rows: %r" % rows[:2])
    return texts


# RED 1.13.2 N132: green with group 3's fix (the strict xfail mark removed)
def test_n132_walk_zero_page_in_a_hole_is_stated_as_a_hole_with_no_acquisition_gap_claim(monkeypatch, capsys,
                                                                                          tmp_path):
    texts = _walk_zero_page(monkeypatch, capsys, _n132_file(tmp_path, "hole"))
    _keep(_rc_escalate()(0) == 2, "a page the volume needs, inside an image hole, keeps exit 2 (C8 = B):\n"
          + "\n".join(texts))
    assert not _gap_claims(texts), "\n".join(texts)
    assert _page_hole_stated(texts, N132_LCN), ("page 0x%x: nothing says the image stores it as a hole with the cause "
                                                "left open (not captured, or zero on the disk):\n" % N132_LCN) \
        + "\n".join(texts)


def test_n132_control_walk_zero_page_written_on_the_volume_is_damage_with_no_gap_claim(monkeypatch, capsys, tmp_path):
    """Not a RED. The same zero page stored as WRITTEN zeros (no hole): 1.13.1 already says it 'reads as all zeros on
    this volume' and exits 2. The fix must keep both and must not call it an acquisition gap either."""
    texts = _walk_zero_page(monkeypatch, capsys, _n132_file(tmp_path, "zeros"))
    assert _rc_escalate()(0) == 2, "\n".join(texts)
    assert [t for t in texts if ("0x%x" % N132_LCN) in t and re.search(r"(?i)all zeros", t)], "\n".join(texts)
    assert not _gap_claims(texts), "\n".join(texts)


# RED 1.13.2 N132: green with group 3's fix (the strict xfail mark removed)
def test_n132_zero_object_root_is_not_labelled_an_acquisition_gap(monkeypatch, capsys):
    """Site probe of verify_object_root (fd:1109-1142): the Object Table recorded a CRC64 for object 0x777's root,
    and the page read back is all zeros. Nothing tells whether the page is in an image hole, so 'acquisition gap' is
    a claim without evidence; the finding (exit 2) is kept."""
    _fresh(monkeypatch)
    oid = 0x777
    F._OBJ_ROOT_REF[oid] = (8, b"\x11" * 8)
    F._OBJ_ROOT_LCNS[oid] = [0x40, 0x41, 0x42, 0x43]
    capsys.readouterr()
    F.verify_object_root(oid, b"\0" * (4 * HCS))
    cap = capsys.readouterr()
    texts = ["%s: %s" % kt for kt in F._FINDINGS] + (cap.out + cap.err).splitlines()
    _keep(_rc_escalate()(0) == 2, "the zero root must stay a finding:\n" + "\n".join(texts))
    assert not _gap_claims(texts), "\n".join(texts)


def _output_strings(path):
    """(line, text) of every string literal and f-string of a Python source, docstrings excluded (comments are not
    in the AST). An f-string is one text, its placeholders '{}'; its literal parts are not listed again."""
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    docs = set()                                          # docstrings, and the literal parts of f-strings
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            b0 = node.body[0]
            if isinstance(b0, ast.Expr) and isinstance(b0.value, ast.Constant) and isinstance(b0.value.value, str):
                docs.add(id(b0.value))
        if isinstance(node, ast.JoinedStr):
            docs.update(id(v) for v in node.values)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            out.append((node.lineno, "".join(v.value if isinstance(v, ast.Constant) and isinstance(v.value, str)
                                             else "{}" for v in node.values)))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            out.append((node.lineno, node.value))
    return sorted(set(out))


# RED 1.13.2 N132: green with group 3's fix (the strict xfail mark removed)
def test_n132_no_output_string_in_either_tool_claims_an_acquisition_gap():
    """The class, searched over both tools as PLAN section 5 requires ("Search the whole code base for the class").
    A string may still name an acquisition gap as ONE possibility beside never-written/zeroed."""
    bad = []
    for tool in (FOREFST, REFSANALYSIS):
        _fx(os.path.isfile(tool), "%s not found" % tool)
        bad += ["%s:%d: %s" % (os.path.basename(tool), ln, s.strip()[:140])
                for ln, s in _output_strings(tool) if _gap_claims([s])]
    assert not bad, "\n".join(bad)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# the matchers, on 1.13.1's own lines and on a plausible corrected wording
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_L1131_WIPE = ("[forefst] WARNING: USN journal skipped the $J stream is allocated (33554432 bytes) but holds NO "
               "records and not one non-zero byte: this is a journal that was never written OR one that was wiped, "
               "and the stream cannot distinguish them -- do not read it as 'no activity': ValueError: journal "
               "allocated but entirely zero")
_L1131_DESTROYED = ("[forefst] WARNING: USN journal skipped 73856 zero byte(s) in 1 run(s) INSIDE the written span, "
                    "each larger than one whole record: this is not unwritten ring space, it is journal that was "
                    "destroyed, and the surviving records are NOT the whole journal: ValueError: zeroed journal region")
_L1131_GAP = [
    "[forefst]          absent-from-image: 6 page(s) — e.g. page at plcn 0x2f668c is not present in this image "
    "(acquisition gap, not damage); page at plcn 0x2fc300 is not present in this image (acquisition gap, not damage)",
    "root page absent: the root page of object 0x777 reads as all zeros (acquisition gap)",
    "  Absent from this image:  3   <-- reads as all zeros; an acquisition gap, not an altered page",
    "  Absent (image holes):    3 (referenced page reads as all zeros in an image hole — acquisition gap)",
    "  VERDICT: the 12 checksummed pages present VERIFIED; 3 referenced page(s) are absent from this image "
    "(acquisition gap) and are NOT covered",
    "{} page(s) absent from this image (acquisition gap)",
]


def test_b2_journal_matchers_accept_corrected_wording_and_reject_the_1131_lines():
    """Not a RED."""
    # N131
    assert _undecided_wipe(_sentences([_L1131_WIPE]))
    for ok in ["[forefst] note: USN journal: the $J stream (33,554,432 bytes) holds no record, and no file on the "
               "volume points into it (every LastUsn and UsnJournalId is 0): it was never written, not wiped.",
               "    Count:          0   (no file carries this journal's id: nothing was ever written to it)"]:
        assert not _undecided_wipe(_sentences([ok])), ok
    assert _journal_damage(_sentences([_L1131_WIPE]))
    assert _journal_damage(_sentences(["[forefst] WARNING: USN journal: the $J holds no record although 33 files "
                                       "point into it (up to USN 47584): its records were wiped."]))
    # N148 (the A10 matchers, reused): the 1.13.1 lines neither state the hole with the cause open nor avoid
    # 'destroyed'; the fourth revision's "unreadable" wording no longer meets C8 = B
    assert not _hole_stated(_sentences([_L1131_DESTROYED])) and _DESTROYED_CLAIM.search(_L1131_DESTROYED)
    fixed = ("[forefst] WARNING: USN journal: 73,728 bytes of $J inside the written span are stored as a hole in "
             "this image: not captured, or zero on the disk; the cause cannot be told from the image.")
    assert _hole_stated(_sentences([fixed])) and not _DESTROYED_CLAIM.search(fixed)
    assert not _hole_stated(_sentences(["[forefst] WARNING: USN journal: 73,728 bytes of $J inside the written span "
                                        "are stored as a hole in this image, so the records there are unreadable."]))
    content_holes_1131 = ("[forefst] WARNING: 4096 byte(s) of USN $J change-journal stream come from ranges the image "
                          "stores as HOLES and read back as zeros. A sparse image stores a file's own zero content the "
                          "same way it stores a range never captured, so this does not by itself prove data is missing")
    assert not _hole_stated(_sentences([content_holes_1131])), "the export-metadata wording is not the B wording"
    # N132
    assert len(_gap_claims(_L1131_GAP)) == len(_L1131_GAP)
    assert _page_hole_stated(["absent-from-image: page at plcn 0x2f668c: the image stores it as a hole -- not "
                              "captured, or zero on the disk; the cause cannot be told from the image"], 0x2f668c)
    assert not _page_hole_stated(["page at plcn 0x2f668c is not present in this image (acquisition gap, not damage)",
                                  "page at plcn 0x2f668c is unreadable: the image stores it as a hole"], 0x2f668c)
    for ok in ["page at plcn 0x2f668c is unreadable: the image stores it as a hole, and a hole cannot tell a page "
               "never written from one the acquisition did not capture",
               "  Absent (image holes):    3 (unreadable: an image hole -- an acquisition gap or a page never "
               "written; the image cannot tell)",
               "page at plcn 0x40 reads as all zeros on this volume"]:
        assert not _gap_claims([ok]), ok
    # N196 / N195
    assert not _names_other_instance(["    Journal ID:     0x01dd4e57f84a6362"], JID_OLD)
    assert _names_other_instance(["  Journal instances: 3 file(s) carry journal id 0x01dd4e57f72ac89e, an earlier "
                                  "journal instance than the current 0x01dd4e57f84a6362."], JID_OLD)
    assert _id_re(JID_OLD).search('"usn_journal_id": 134349703606880414')
    assert _id_re(JID_OLD).search("UsnJournalId:       0x01DD4E57F72AC89E")
    assert not _id_re(JID_OLD).search("0x01dd4e57f84a6362 1343497036068804140")
    assert _journal_ids_named("Journal ID: 0x01dd4e57f84a6362; USN 256") == {JID_NEW}


def test_b2_journal_harness_builds_what_it_claims(tmp_path):
    """Not a RED. The synthetic $J of the unit cases, read back by this module's own readers (the _Journal
    constructor already checks the hole layout and the record carve; this pins the sizes the report quotes)."""
    for sub in ("s", "l", "z"):
        (tmp_path / sub).mkdir()
    small = _n148_journal(tmp_path / "s", "small")
    per = small.n() // 5
    assert small.n() == 5 * per and small.n(in_hole=True) == per and small.nclusters == 8
    assert _is_hole(small.path, (J_PLCN + 2) * HCS, HCS) and not _is_hole(small.path, (J_PLCN + 3) * HCS, HCS)
    assert _is_hole(small.path, (J_PLCN + 5) * HCS, 3 * HCS)                 # the unwritten ring
    large = _n148_journal(tmp_path / "l", "large")
    assert large.n(in_hole=True) == 18 * per and large.n(in_hole=False) == 4 * per
    assert _is_hole(large.path, (J_PLCN + 2) * HCS, 18 * HCS) and 18 * HCS > F.USN_MAX_RECORD
    z = _Journal(tmp_path / "z", 8, zeros=range(8))
    with open(z.path, "rb") as fh:
        fh.seek(J_PLCN * HCS)
        assert not any(fh.read(8 * HCS))
    assert not _is_hole(z.path, J_PLCN * HCS, 8 * HCS)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# image nodes (the serial runner confirms these; read-only on the corpus, or a planted scratch copy)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

IMG_EMPTY = "win11afterblindaudit_empty.raw"
IMG_BEFOREF = "labBeforeF.raw"
IMG_LABJ = "labJjournal.raw"
IMG_MILLIONS = "win11refs2tmillionsofactions.raw"

# labBeforeF (step7): $J virtual 0 at image offset 0x192DA000 (the same run as labF/labG, A10's J_BASE); 440 records
# at USN 0..47824, all in the first 48 KiB (12 clusters, 26-40 records each); every other byte of the journal region
# is an image hole. Measured 2026-09-27 by this module's carve; re-checked at test time.
BF_J_BASE, BF_WRITTEN, BF_N, BF_LAST = 0x192DA000, 0xC000, 440, 47824
BF_HOLE_CLUSTER = 5                                      # USN 20480..24575: 38 records
BF_JID = JID_ONE

# labJjournal (step7): the directory rows of the markers (two copies each, pages 0x1400000 and 0x1600000), read by
# LAB-J's own reader (runlog labJ_2026-09-27.txt section 2) and re-read at test time by _dir_row.
LABJ_ROWS = {
    "m1_after_create.txt": ((0x1400CD0, 0x1600CD0), 0xF0, JID_OLD),
    "m2_after_recreate_same.txt": ((0x1400F20, 0x1600F20), 0x100, JID_OLD),
    "m3_after_recreate_resize.txt": ((0x1401180, 0x1601180), 0x110, JID_OLD),
    "m5_after_delete_create.txt": ((0x1400390, 0x1600390), 0x100, JID_NEW),
}
LABJ_TAIL = 31576
LABJ_M5_CLOSE = 0x1914D100                               # $J USN 256 = m5's close record (reason 0x80000102)

# win11refs2tmillionsofactions (step3): partition at 0x1000000, 4 KiB clusters; the two pages every C01 run names.
MOA_PS, MOA_CS, MOA_LCNS = 0x1000000, 4096, (0x2F668C, 0x2FC300)


def _img_run(path, *args):
    """(rc, stdout, stderr) of forefst on a scratch copy; a traceback or a timeout is a fixture error."""
    cmd = [sys.executable, "-B", FOREFST, path] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, cwd=os.path.dirname(path))
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(cmd))
    out, err = r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    if "Traceback (most recent call last)" in err:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + err[-3000:])
    return r.returncode, out, err


def _labbeforef_journal(path):
    """The pinned $J premise of labBeforeF, from the bytes: [(usn, len, name)] of the 440 records."""
    _fx(os.path.getsize(path) == 4294967296, "%s: not the 4 GiB labBeforeF" % path)
    with open(path, "rb") as fh:
        fh.seek(BF_J_BASE)
        recs = _carve_journal(fh.read(BF_WRITTEN))
    _fx(len(recs) == BF_N and recs[0][0] == 0 and recs[-1][0] == BF_LAST,
        "labBeforeF $J at 0x%x: %d records (want %d, USN 0..%d)" % (BF_J_BASE, len(recs), BF_N, BF_LAST))
    _fx(all(u // HCS == (u + l - 1) // HCS for u, l, _n in recs), "a record crosses a 4 KiB boundary")
    return recs


def _carve_except(src, dst, holes):
    """Hole-preserving copy of `src` (the SEEK_DATA/SEEK_HOLE method of AB._carve: only allocated ranges are
    written) that never writes the 4 KiB-aligned ranges in `holes`, so each stays an image hole in the copy -- the
    damage.py op "punch", without fallocate(1). Checked afterwards with SEEK_DATA."""
    for off, n in holes:
        _fx(off % HCS == 0 and n % HCS == 0 and n > 0, "a planted hole must be 4 KiB-aligned: 0x%x+0x%x" % (off, n))
    size = os.path.getsize(src)
    with open(src, "rb") as fi, open(dst, "wb") as out:
        out.truncate(size)
        for d, h in _data_ranges(src):
            pieces = [(d, h)]
            for off, n in holes:
                nxt = []
                for a, b in pieces:
                    if off + n <= a or off >= b:
                        nxt.append((a, b))
                        continue
                    if a < off:
                        nxt.append((a, off))
                    if off + n < b:
                        nxt.append((off + n, b))
                pieces = nxt
            for a, b in pieces:
                fi.seek(a)
                out.seek(a)
                rem = b - a
                while rem > 0:
                    chunk = fi.read(min(4 << 20, rem))
                    if not chunk:
                        break
                    out.write(chunk)
                    rem -= len(chunk)
    for off, n in holes:
        _fx(_is_hole(dst, off, n), "the punched range 0x%x+0x%x is not a hole in the copy" % (off, n))


class _Copy:
    def __init__(self, path, info):
        self.path, self.info, self.runs = path, info, {}

    def run(self, *args):
        if args not in self.runs:
            self.runs[args] = _img_run(self.path, *args)
        return self.runs[args]


def _scratch_copy(base_name, holes=(), zeros=()):
    """Yield-less builder used by the module fixtures: returns (dir, path) of the planted copy, checked."""
    base = _corpus_image(base_name)
    if base is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % base_name)
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="b2_journal_", dir=SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file; refusing to write a dense 4 GiB copy" % d)
        _carve_except(base, p, holes)
        for off, n in zeros:
            with open(p, "r+b") as fh:
                fh.seek(off)
                before = fh.read(n)
                _fx(any(before), "0x%x+0x%x is already zero: zeroing it would damage nothing" % (off, n))
                fh.seek(off)
                fh.write(b"\0" * n)
            with open(p, "rb") as fh:
                fh.seek(off)
                _fx(not any(fh.read(n)), "zero did not land at 0x%x" % off)
            _fx(not _is_hole(p, off, n), "the zeroed range 0x%x+0x%x must stay WRITTEN (not a hole)" % (off, n))
        alloc = os.stat(p).st_blocks * 512
        _fx(alloc < MAX_SCRATCH_ALLOCATED, "the scratch copy allocated %d bytes" % alloc)
        return d, p
    except BaseException:
        if os.path.exists(p):
            os.unlink(p)
        os.rmdir(d)
        raise


def _drop(d, p):
    if os.path.exists(p):
        os.unlink(p)
    if os.path.isdir(d):
        os.rmdir(d)


@pytest.fixture(scope="module")
def beforef_hole_copy():
    """labBeforeF with $J cluster 5 (USN 20480..24575, 38 records) punched: an image hole in the written span."""
    base = _corpus_image(IMG_BEFOREF)
    if base is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % IMG_BEFOREF)
    recs = _labbeforef_journal(base)
    lo = BF_J_BASE + BF_HOLE_CLUSTER * HCS
    _fx(not _is_hole(base, lo, HCS), "labBeforeF: $J cluster %d is already a hole" % BF_HOLE_CLUSTER)
    gone = [r for r in recs if r[0] // HCS == BF_HOLE_CLUSTER]
    _fx(len(gone) == 38, "labBeforeF: $J cluster %d holds %d records (want 38)" % (BF_HOLE_CLUSTER, len(gone)))
    d, p = _scratch_copy(IMG_BEFOREF, holes=[(lo, HCS)])
    try:
        with open(p, "rb") as fh:
            fh.seek(BF_J_BASE)
            left = _carve_journal(fh.read(BF_WRITTEN))
        _fx(left == [r for r in recs if r[0] // HCS != BF_HOLE_CLUSTER],
            "the copy's $J does not hold exactly the %d records outside the hole" % (BF_N - len(gone)))
        yield _Copy(p, {"gone": gone, "left": left})
    finally:
        _drop(d, p)


def _beforef_journal_extents(base):
    """The $J extents of labBeforeF as the tool decodes them (in a subprocess, read-only), checked against the
    carve: the first extent must start at BF_J_BASE."""
    code = ("import json,sys; sys.path.insert(0, %r); import forefst as F\n"
            "f, ps, cs, tr, roots, om, a, b, c = F.bootstrap(%r, None)\n"
            "vd, _m = F.locate_change_journal(f, ps, cs, tr, om)\n"
            "st = F.parse_usn_journal_streams(vd, cs, tr)\n"
            "print(json.dumps({'ps': ps, 'cs': cs, 'ext': [[e['plcn'], e['clusters'], e['file_vcn']] "
            "for e in st['j_extents']]}))\n" % (REPO, base))
    try:
        r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout decoding the $J extents")
    _fx(r.returncode == 0 and r.stdout.strip(), "could not decode labBeforeF's $J extents:\n" + r.stderr[-2000:])
    j = json.loads(r.stdout.strip().splitlines()[-1])
    ext = sorted(j["ext"], key=lambda e: e[2])
    _fx(ext and ext[0][2] == 0 and j["ps"] + ext[0][0] * j["cs"] == BF_J_BASE and ext[0][1] * j["cs"] >= BF_WRITTEN,
        "labBeforeF: $J extent 0 is not at 0x%x: %r" % (BF_J_BASE, j))
    return [(j["ps"] + pl * j["cs"], n * j["cs"]) for pl, n, _v in ext]


@pytest.fixture(scope="module")
def beforef_wiped_copy():
    """labBeforeF with every allocated byte of every $J extent overwritten with WRITTEN zeros: a wipe on written
    blocks, while 33 files still carry this journal's id with LastUsn up to 47,584 (E2 RL [M4])."""
    base = _corpus_image(IMG_BEFOREF)
    if base is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % IMG_BEFOREF)
    _labbeforef_journal(base)
    zeros = []
    for lo, n in _beforef_journal_extents(base):
        for d0, h0 in _data_ranges(base, lo, lo + n):
            with open(base, "rb") as fh:
                fh.seek(d0)
                if any(fh.read(h0 - d0)):
                    zeros.append((d0, h0 - d0))
    _fx(zeros and zeros[0][0] == BF_J_BASE, "labBeforeF: the $J's written bytes do not start at 0x%x" % BF_J_BASE)
    d, p = _scratch_copy(IMG_BEFOREF, zeros=zeros)
    try:
        for lo, n in _beforef_journal_extents(p):
            for d0, h0 in _data_ranges(p, lo, lo + n):
                with open(p, "rb") as fh:
                    fh.seek(d0)
                    _fx(not any(fh.read(h0 - d0)), "the copy's $J still holds non-zero bytes at 0x%x" % d0)
        yield _Copy(p, {"zeroed": zeros})
    finally:
        _drop(d, p)


# ─── N131 on win11afterblindaudit_empty (the 5 C11 golden rows) ─────────────────────────────────────────────────

N131_CMDS = [("usn", "--info"), ("usn", "--csv"), ("usn", "--stats"), ("timeline", "--csv"), ("timestomp", "--csv")]
N131_IDS = ["usn-info", "usn-csv", "usn-stats", "timeline-csv", "timestomp-csv"]
_N131_PREMISE = []


def _n131_premise():
    """From the bytes: no USN_RECORD_V3 anywhere in the image's allocated data, and both files' rows carry
    LastUsn 0 and UsnJournalId 0 (the directory's row is split, 84 bytes, and carries neither)."""
    if _N131_PREMISE:
        return
    img = _corpus(IMG_EMPTY)
    _fx(_carve_anywhere(img) == 0, "%s holds USN records: the journal was written" % IMG_EMPTY)
    rows = _rows_by_name(img, ["WPSettings.dat", "FVE2.{8252fd17-a486-4ad4-b1ca-f4fe64d23218}"])
    for n, rs in rows.items():
        _fx(rs and all(u == 0 and j == 0 for _o, u, j in rs), "%s: row fields %r (want LastUsn 0, id 0)" % (n, rs))
    _N131_PREMISE.append(True)


# RED 1.13.2 N131: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", N131_CMDS, ids=N131_IDS)
def test_n131_image_empty_journal_no_file_points_into_exits_0(args):
    _n131_premise()
    rc, out, err = _run_corpus(FOREFST, IMG_EMPTY, *args)
    prose, _h, _r = _split(out, err)
    ctx = _cctx(IMG_EMPTY, args, rc, out, err)
    assert not _undecided_wipe(_sentences(prose)), "the journal is still left 'never written OR wiped'" + ctx
    assert rc == 0, "a false exit 2 (every other golden row of this image exits 0)" + ctx


@pytest.mark.parametrize("args", [("usn", "--info"), ("timeline", "--csv")], ids=["usn-info", "timeline-csv"])
def test_n131_control_image_labBeforeF_planted_wipe_keeps_exit_2(beforef_wiped_copy, args):
    """Not a RED. labBeforeF (every golden row rc 0) with its $J overwritten by written zeros: files point into the
    journal, so the records were there and are gone. 1.13.1 exits 2 (the all-zero check); the fix must keep it."""
    rc, out, err = beforef_wiped_copy.run(*args)
    prose, _h, _r = _split(out, err)
    ctx = _cctx("labBeforeF+wipe", args, rc, out, err)
    assert rc == 2, ctx
    assert _journal_damage(_sentences(prose)), "nothing says the journal's records are gone" + ctx


# ─── N132 on win11refs2tmillionsofactions ─────────────────────────────────────────────────────────────────────────

N132_CMDS = [("integrity",), ("integrity", "--checksums"), ("summary",)]
N132_IDS = ["integrity", "integrity-checksums", "summary"]


def _n132_premise(img):
    with open(img, "rb") as fh:
        fh.seek(MOA_PS)
        v = fh.read(512)
    _fx(v[3:7] == b"ReFS" and struct.unpack_from("<I", v, 0x20)[0] * struct.unpack_from("<I", v, 0x24)[0] == MOA_CS,
        "%s: no 4 KiB-cluster ReFS boot sector at 0x%x" % (IMG_MILLIONS, MOA_PS))
    for lcn in MOA_LCNS:
        _fx(_is_hole(img, MOA_PS + lcn * MOA_CS, 4 * MOA_CS), "page 0x%x is not an image hole" % lcn)


# RED 1.13.2 N132: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", N132_CMDS, ids=N132_IDS)
def test_n132_image_millionsofactions_hole_pages_carry_no_acquisition_gap_claim(args):
    _n132_premise(_corpus(IMG_MILLIONS))
    rc, out, err = _run_corpus(FOREFST, IMG_MILLIONS, *args)
    lines = (out + "\n" + err).splitlines()
    ctx = _cctx(IMG_MILLIONS, args, rc, out, err)
    _keep(rc == 2, "C01 is a FINDING (E2): exit 2 is kept" + ctx)
    bad = _gap_claims(lines)
    assert not bad, "claims without evidence: %r" % [b.strip()[:160] for b in bad[:3]] + ctx
    assert _page_hole_stated(lines, MOA_LCNS[0]), ("page 0x%x: nothing says the image stores it as a hole with the "
                                                   "cause left open (C8 = B)" % MOA_LCNS[0]) + ctx


# ─── N148 on a planted copy of labBeforeF ────────────────────────────────────────────────────────────────────────

N148_IMG_CMDS = [("usn", "--info"), ("usn", "--csv"), ("timeline", "--csv"), ("timestomp",)]
N148_IMG_IDS = ["usn-info", "usn-csv", "timeline-csv", "timestomp"]


# RED 1.13.2 N148: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", N148_IMG_CMDS, ids=N148_IMG_IDS)
def test_n148_image_labBeforeF_planted_hole_is_stated_as_a_hole_and_exits_2(beforef_hole_copy, args):
    rc, out, err = beforef_hole_copy.run(*args)
    prose, _hdr, rows = _split(out, err)
    ctx = _cctx("labBeforeF+hole", args, rc, out, err)
    left = beforef_hole_copy.info["left"]
    if args == ("usn", "--csv"):
        got = sorted(int(r[0]) for r in rows)
        _keep(got == [u for u, _l, _n in left], "usn --csv must list exactly the %d records outside the hole "
              "(lists %d)" % (len(left), len(got)) + ctx)
    assert _hole_stated(_sentences(prose)), (
        "38 records in the $J range the image stores as a hole (USN 20480..24575): nothing says so with the cause "
        "left open") + ctx
    assert rc == 2, "records the journal needs are missing inside an image hole: exit 2 (C8 = B)" + ctx


@pytest.mark.parametrize("args", [("usn", "--info"), ("timeline", "--csv")], ids=["usn-info", "timeline-csv"])
def test_n148_control_image_labBeforeF_unwritten_ring_in_holes_is_not_reported(args):
    """Not a RED. labBeforeF as captured: its $J is 48 KiB written and 32 MiB of image holes beyond the tail. The
    fix must not report that ring space as a hole; exit 0 (golden) is kept."""
    img = _corpus(IMG_BEFOREF)
    _labbeforef_journal(img)
    _fx(_is_hole(img, BF_J_BASE + BF_WRITTEN, 0x2000000 - BF_WRITTEN), "labBeforeF: the ring past 48 KiB is not a hole")
    rc, out, err = _run_corpus(FOREFST, IMG_BEFOREF, *args)
    prose, _h, _r = _split(out, err)
    ctx = _cctx(IMG_BEFOREF, args, rc, out, err)
    assert rc == 0, ctx
    assert not _hole_stated(_sentences(prose)), "unwritten ring space reported as a hole" + ctx


# ─── N195 / N196 on labJjournal ─────────────────────────────────────────────────────────────────────────────────

_LABJ_PREMISE = []


def _labj_premise():
    """From the bytes: both row copies of m1-m3 carry the first journal's id and m5 the current one; m2's LastUsn
    (256) is the USN of m5's close record in the current $J; every stale LastUsn is below the tail."""
    if _LABJ_PREMISE:
        return
    img = _corpus(IMG_LABJ)
    _fx(os.path.getsize(img) == 4294967296, "labJjournal: size")
    with open(img, "rb") as fh:
        for name, (offs, usn, jid) in LABJ_ROWS.items():
            for off in offs:
                fh.seek(off)
                row = _dir_row(fh.read(0x800), 0, name)
                _fx(row == (name, usn, jid), "labJjournal row 0x%x: %r (want %s, 0x%x, 0x%016x)"
                    % (off, row, name, usn, jid))
        fh.seek(LABJ_M5_CLOSE)
        rec = fh.read(0x100)
    r = _usn_v3_at(rec, 0)
    _fx(r is not None and r[1] == 0x100 and r[2] == "m5_after_delete_create.txt"
        and struct.unpack_from("<I", rec, 0x38)[0] == 0x80000102,
        "labJjournal: $J USN 256 is not m5's close record: %r" % (r,))
    _fx(all(u < LABJ_TAIL for (_o, u, _j) in LABJ_ROWS.values()), "a stale pointer is not below the tail")
    _LABJ_PREMISE.append(True)


N195_DETAILS = [("m1_after_create.txt", JID_OLD), ("m5_after_delete_create.txt", JID_NEW)]


# RED 1.13.2 N195: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("fmt", ["text", "json"])
@pytest.mark.parametrize("name,jid", N195_DETAILS, ids=["m1-old-id", "m5-current-id"])
def test_n195_image_labJ_details_shows_the_files_own_journal_id(name, jid, fmt):
    _labj_premise()
    args = ("details", "/labJ/" + name) + (("--json",) if fmt == "json" else ())
    rc, out, err = _run_corpus(FOREFST, IMG_LABJ, *args)
    ctx = _cctx(IMG_LABJ, args, rc, out, err)
    _keep(rc == 0 and name in out, "details must still describe %s" % name + ctx)
    _keep(re.search(r"(?<!\d)%d(?!\d)" % LABJ_ROWS[name][1], out) is not None,
          "details must still show the file's LastUsn %d" % LABJ_ROWS[name][1] + ctx)
    assert _id_re(jid).search(out), "the file's own UsnJournalId 0x%016x is not shown" % jid + ctx


# RED 1.13.2 N195: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("fmt", ["text", "json"])
def test_n195_image_labJ_summary_names_every_journal_id_the_files_carry(fmt):
    _labj_premise()
    args = ("summary",) + (("--json",) if fmt == "json" else ())
    rc, out, err = _run_corpus(FOREFST, IMG_LABJ, *args)
    ctx = _cctx(IMG_LABJ, args, rc, out, err)
    _keep(_id_re(JID_NEW).search(out) is not None, "summary must still name the current journal id" + ctx)
    assert _id_re(JID_OLD).search(out), ("the journal id 0x%016x carried by 3 files is not reported" % JID_OLD) + ctx


N196_IMG_CMDS = [("usn", "--info"), ("timeline", "--csv"), ("timestomp",)]
N196_IMG_IDS = ["usn-info", "timeline-csv", "timestomp"]


# RED 1.13.2 N196: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", N196_IMG_CMDS, ids=N196_IMG_IDS)
def test_n196_image_labJ_names_the_discarded_instance_of_the_stale_pointers(args):
    _labj_premise()
    rc, out, err = _run_corpus(FOREFST, IMG_LABJ, *args)
    prose, _h, _r = _split(out, err)
    ctx = _cctx(IMG_LABJ, args, rc, out, err)
    if args == ("usn", "--info"):
        _keep(_id_re(JID_NEW).search(out) is not None, "usn --info must still print the current journal id" + ctx)
    assert _names_other_instance(prose, JID_OLD), (
        "nothing names the earlier journal instance 0x%016x that m1-m3's pointers belong to" % JID_OLD) + ctx


@pytest.mark.parametrize("args", [("usn", "--info"), ("summary",)], ids=["usn-info", "summary"])
def test_n196_control_image_labBeforeF_names_no_other_journal_instance(args):
    """Not a RED. labBeforeF has one journal instance (0x01dd485de7522417; 33 files carry it, the rest 0): no other
    journal id may be named, and exit 0 (golden) is kept."""
    img = _corpus(IMG_BEFOREF)
    _labbeforef_journal(img)
    rc, out, err = _run_corpus(FOREFST, IMG_BEFOREF, *args)
    ctx = _cctx(IMG_BEFOREF, args, rc, out, err)
    assert rc == 0, ctx
    assert _journal_ids_named(out + err) <= {BF_JID}, ctx
