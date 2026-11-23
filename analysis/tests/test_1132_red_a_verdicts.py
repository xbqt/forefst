"""1.13.2 RED cases, group a_verdicts: plan rows A10 (fourth revision), A11 (with N133 folded in), A12, A13, N134.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 2 A (rows A10-A13), the fourth revision (top), section 5
"RED first" and decision 19 (the maintainer's bar: every RED fails on 1.13.1 BECAUSE of the defect, not because
of an artefact, and is independently confirmed). N133/N134: `RUNNING_LOG.md`; A10's evidence:
`E2_RC2_CLASSIFICATION.md` cause C10 and `RC1_DEPS_CHECKPOINT.md` section 1. Report, with the observed or expected
failure of every node: `analysis/reports/v1.13.2/red/RED_a_verdicts.md`.

Three kinds of node
-------------------
* unit -- synthetic bytes, a static read of the sources, or an in-process call with the module's registers reset.
  No corpus image. Runs anywhere.
* ``[synthetic]`` / ``[image]`` -- the ``vol`` fixture of `test_1132_red_a_bootstrap.py` (imported, not copied):
  a 1 MiB synthetic ReFS 3.14 volume, or a hole-preserving scratch copy of `win11refsmini.raw` (battery base A),
  damaged to order and checked before and after the damage. The CLI runs in a subprocess on that volume.
* ``[image-<name>]`` -- the real CLI, read-only, on a corpus image (labF/labG, the version-edit images). Skipped
  when the image is not in the tree. Nothing is written to the image.

``pytest -k "not image"`` runs the unit and synthetic nodes only (no corpus, no scratch copy).

How a RED can fail only because of its defect
---------------------------------------------
Same discipline as the a_bootstrap group: every RED is ``xfail(strict=True, raises=AssertionError)``; only a plain
``assert`` states the defect; a fixture that is not what the case needs raises ``RedFixtureError`` and a property
1.13.1 already has (which the fix must keep) raises ``KeptPropertyBroken`` -- neither is an AssertionError, so a
strict xfail can never count them as the expected failure. Premises that the REDs rest on are checked at test time
from the bytes (for A10: the last surviving record sits where the $J map says, and the missing range is an image
hole), not trusted from a report. The matchers are exercised by a non-xfail self-test that shows they accept a
corrected wording and reject the 1.13.1 lines.
"""
import csv
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

# The a_bootstrap group's volume machinery (fixture, damage recipes, exception classes, matchers). Imported by
# name -- never `import *`, which would re-collect that module's tests here.
import test_1132_red_a_bootstrap as _AB                   # noqa: E402
from test_1132_red_a_bootstrap import (                  # noqa: E402
    damage_chkp, damage_supb, make_tie, RedFixtureError, _fx, _keep, _red,
    _FAIL, _lcn_re, _ctx, FOREFST, REFSANALYSIS, SUPB_DESC, CLOCK_NEW, CLOCK_OLD, _synthetic_vol)

vol = _AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module

TIMEOUT = 900


def _rc_escalate():
    """The single exit rule: `rc_escalate` once A11 lands, `_escalate_rc` on 1.13.1."""
    fn = getattr(F, "rc_escalate", None) or getattr(F, "_escalate_rc", None)
    _fx(callable(fn), "neither rc_escalate nor _escalate_rc exists in forefst.py")
    return fn


_REG_NAMES = ("_FINDINGS", "_SKIP_FINDING", "_WALK_DAMAGE", "_REDUNDANCY_FINDING", "_CHKP_STALE",
              "_JOURNAL_TAIL_DESTROYED", "_VERSION_CONTRADICTED", "_SUPB_FELL_BACK", "_CONTENT_HOLES",
              "_CONTENT_UNDET", "_JOURNAL_WIPE_SUSPECT", "_HOLE_STREAMS")


def _fresh_registers(monkeypatch):
    """Give every run-level register of forefst a fresh empty value, so an in-process test starts clean and
    leaves the module as it found it (monkeypatch restores)."""
    for name in _REG_NAMES:
        cur = getattr(F, name, None)
        if isinstance(cur, (list, dict)):
            monkeypatch.setattr(F, name, type(cur)())


# ─── corpus runs (read-only, cached per process) ─────────────────────────────────────────────────────────────

_RUNS = {}


def _corpus(name):
    from test_image_holes_and_page_refs import _corpus_image
    p = _corpus_image(name)
    if p is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return p


def _run_corpus(tool, name, *args):
    """(rc, stdout, stderr) of `tool <image> args...`, run once per process. A traceback is a fixture error."""
    img = _corpus(name)
    key = (tool, img, args)
    if key not in _RUNS:
        cmd = [sys.executable, "-B", tool, img] + list(args)
        try:
            r = UW.run(cmd, capture_output=True, timeout=TIMEOUT, cwd=REPO)
        except subprocess.TimeoutExpired:
            raise RedFixtureError("timeout: %s" % " ".join(cmd))
        out = r.stdout.decode("utf-8", "replace")
        err = r.stderr.decode("utf-8", "replace")
        if "Traceback (most recent call last)" in err:
            raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + err[-3000:])
        _RUNS[key] = (r.returncode, out, err)
    return _RUNS[key]


def _cctx(name, args, rc, out, err):
    return "\n[image %s] %s | rc=%d\n--- stdout (tail) ---\n%s\n--- stderr (tail) ---\n%s" % (
        name, " ".join(args), rc, out[-3000:], err[-3000:])


# ─── reading CSV-bearing output: prose lines vs data rows ─────────────────────────────────────────────────────

# A data row is a line after one of these headers that parses to the header's field count AND looks like a row of
# that table (a prose sentence with the same number of commas does not start with a timestamp, a USN or a path
# followed by a tier). Everything else, and all of stderr, is prose.
_CSV_TABLES = (
    # timeline --csv writes an undated event (ts 0: the MLog rows it undates, fd:8407) as "(none)", and a time it
    # cannot convert as "0x<hex>" (_filetime_to_str, fd:7236-7244); "(undated)" is the TEXT-mode label only (fd:8469).
    # Without the first two forms those data rows fall into the prose and join into one long "sentence" the A10
    # matchers read (critic fix, 2026-09-27).
    # acceptance 1.14.0 (K21 names, K5 times -- an absent time is an empty cell (R1), an unrenderable one 0x<hex>;
    # Q-C: the timeline's Name and PathToday; N313: timestomp's Confidence is the 5th column)
    ("Timestamp,TimeSource,Source,OID,Name,PathToday,Event",
     lambda f: bool(re.match(r"\d{4}-\d\d-\d\dT[\d:.]+Z$|0x[0-9a-f]+$|$", f[0]))),
    ("ObjectRef,FullPath,RecordPlacement,DataResidency,Confidence,",
     lambda f: f[4] in ("HIGH", "MEDIUM", "LOW", "INFO", "NONE")),
    ("USN,Timestamp,Reason,", lambda f: f[0].isdigit()),
)


def _split(out, err):
    prose, rows, header, ok = [], [], None, None
    for ln in out.splitlines():
        if header is None:
            for h, check in _CSV_TABLES:
                if ln.startswith(h):
                    header, ok = next(csv.reader([ln])), check
                    break
            if header is not None:
                continue
        if header is not None:
            try:
                fields = next(csv.reader([ln]))
            except (csv.Error, StopIteration):
                fields = None
            if fields and len(fields) == len(header) and ok(fields):
                rows.append(fields)
                continue
        prose.append(ln)
    prose.extend(err.splitlines())
    return prose, header, rows


def _norm_digits(s):
    """4,439,864 / 4 439 864 / 4_439_864 -> 4439864, so a formatted number still matches."""
    return re.sub(r"(?<=\d)[,_\u202f\u00a0' ](?=\d{3}(?!\d))", "", s)


def _sentences(lines):
    text = _norm_digits(re.sub(r"\s+", " ", " ".join(l.strip() for l in lines)))
    return [s for s in re.split(r"(?<=[.;!?])\s+|(?<=:)\s+(?=[A-Z])", text) if s]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A10 -- the labF/labG journal gap: keep exit 2, state what is missing in neutral words, name the instance
#        boundary, report the range inside image holes as unreadable; no "DESTROYED (zeroed or overwritten)"
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

A10_IMAGES = ("labFafterreboot.raw", "labG_0.raw", "labG_1.raw", "labG_2.raw")
A10_IDS = ["image-%s" % n[:-4] for n in A10_IMAGES]
A10_CMDS = [("usn", "--info"), ("timeline", "--csv"), ("timestomp", "--csv")]      # the 12 golden rc-2 rows
A10_CMD_IDS = ["usn-info", "timeline-csv", "timestomp-csv"]

USN_LAST = 4439864            # the last surviving record of the old instance (E2 RL [M4], E2-verify [V11])
USN_LAST_END = 4439968        # its end (length 104)
USN_POINTER = 5119752         # the highest per-file LastUsn (1,654 files, all under /LABF, old journal id)
JID_OLD = 0x01DD485DE7522417  # the instance the records AND the pointers belong to (2026-09-19 17:40:04)
JID_NEW = 0x01DD48CCCC6EDB06  # the current journal, created 2026-09-20 06:53:53 after the unclean detach
J_BASE = 0x192DA000           # image offset of $J virtual 0 on these four images (one run; measured, checked below)

_DESTROYED_CLAIM = re.compile(r"(?i)\b(?:were|was|been)\s+destroyed\b|destroyed\s*\(zeroed or overwritten\)")
_CANNOT = re.compile(r"(?i)\b(?:cannot|can ?not|can't|could not|does not|do not|unable to|no way to)\b")
_TELL = re.compile(r"(?i)\b(?:tell|show|say|distinguish|determine|establish|decide|separate)\b")
_LOSS = re.compile(r"(?i)\b(?:lost|loss|los[ei]ng|never (?:reached|written|persisted|flushed)|unclean)\b")
_REMOVAL = re.compile(r"(?i)\b(?:remov\w*|delet\w*|wip\w*|destroy\w*|zeroed|overwrit\w*|tamper\w*)\b")
_HOLE = re.compile(r"(?i)\bholes?\b|\bsparse\b")
# C8 = B (the maintainer, 2026-10-01): data the volume needs, missing inside an image hole, is a finding (exit 2) worded
# neutrally -- "the image stores this range as a hole: not captured, or zero on the disk; the cause cannot be told
# from the image". A statement of the hole must give that cause as open; "unreadable" alone no longer meets it.
_HOLE_CAUSE = re.compile(r"(?i)\bnot captured\b|\bzeros? on (?:the )?disk\b|\bcan ?not be told\b|"
                         r"\b(?:cannot|can ?not|could not) (?:tell|say|show) (?:which|whether)\b")
_JOURNAL = re.compile(r"(?i)journal|\bUSN\b|\$J\b|UsnJrnl")
_BOUNDARY = re.compile(r"(?i)\binstances?\b|re-?created|\bnew journal\b|\b(?:earlier|previous|older|former|"
                       r"current|later) journal\b|\bdifferent journal\b")


def _hex_id(j):
    return re.compile(r"(?i)(?<![0-9a-f])(?:0x)?0*%x(?![0-9a-f])" % j)


def _names_range(sentences):
    """The pointer (b) and the end of the surviving records (a, as its USN or its end) are named in one sentence or
    in two consecutive ones (a range may be written as "records end at a. A file points at b.")."""
    a = re.compile(r"(?i)(?<![0-9a-f])(?:%d|%d|0x%x|0x%x)(?![0-9a-f])" % (USN_LAST, USN_LAST_END, USN_LAST, USN_LAST_END))
    b = re.compile(r"(?i)(?<![0-9a-f])(?:%d|0x%x)(?![0-9a-f])" % (USN_POINTER, USN_POINTER))
    out = []
    for i in range(len(sentences)):
        w = " ".join(sentences[i:i + 2])
        if a.search(w) and b.search(w):
            out.append(w)
    return out


def _cannot_tell(sentences):
    return [s for s in sentences if _CANNOT.search(s) and _TELL.search(s) and _LOSS.search(s) and _REMOVAL.search(s)]


def _hole_stated(sentences):
    """Journal sentences that say the range is an image hole AND leave the cause open (C8 = B)."""
    return [s for s in sentences if _HOLE.search(s) and _HOLE_CAUSE.search(s) and _JOURNAL.search(s)]


def _instance_boundary(prose):
    """The old instance's id is named, next to a boundary word, and the current id is named too."""
    old, new = _hex_id(JID_OLD), _hex_id(JID_NEW)
    if not any(new.search(l) for l in prose):
        return []
    hits = []
    for i, l in enumerate(prose):
        if old.search(l) and _BOUNDARY.search(" ".join(prose[max(0, i - 2):i + 3])):
            hits.append(l)
    return hits


def _a10_premise(name):
    """The bytes behind every A10 RED: the last surviving record is at J_BASE + USN_LAST (a USN_RECORD_V3 carrying
    that USN), and $J from the first 4 KiB boundary after it to past the pointer holds NO data -- an image hole."""
    img = _corpus(name)
    with open(img, "rb") as fh:
        fh.seek(J_BASE + USN_LAST)
        b = fh.read(0x40)
    rl, major = struct.unpack_from("<IH", b, 0)
    _fx(rl == USN_LAST_END - USN_LAST and major == 3 and struct.unpack_from("<Q", b, 0x28)[0] == USN_LAST,
        "%s: no USN_RECORD_V3 with USN %d at 0x%x (len %d, major %d)" % (name, USN_LAST, J_BASE + USN_LAST, rl, major))
    lo = J_BASE + ((USN_LAST_END + 0xFFF) & ~0xFFF)
    hi = J_BASE + USN_POINTER + 0x80
    fd = os.open(img, os.O_RDONLY)
    try:
        try:
            d = os.lseek(fd, lo, os.SEEK_DATA)
        except OSError:
            d = None                                      # ENXIO: no data after lo at all
    finally:
        os.close(fd)
    _fx(d is None or d >= hi, "%s: the missing $J range is not an image hole (data at 0x%x)" % (name, d or 0))


def _a10_run(name, args):
    _a10_premise(name)
    rc, out, err = _run_corpus(FOREFST, name, *args)
    prose, _hdr, _rows = _split(out, err)
    return rc, out, err, prose


# RED 1.13.2 A10: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", A10_CMDS, ids=A10_CMD_IDS)
@pytest.mark.parametrize("name", A10_IMAGES, ids=A10_IDS)
def test_a10_states_the_missing_range_and_that_loss_cannot_be_told_from_removal(name, args):
    rc, out, err, prose = _a10_run(name, args)
    _keep(rc == 2, "A10 keeps exit 2 on this row (fourth revision)" + _cctx(name, args, rc, out, err))
    s = _sentences(prose)
    assert _names_range(s), "no sentence names the missing range (USN %d .. %d)" % (USN_LAST, USN_POINTER) \
        + _cctx(name, args, rc, out, err)
    assert _cannot_tell(s), "nothing says the journal cannot tell loss from removal" + _cctx(name, args, rc, out, err)


# RED 1.13.2 A10: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", [("usn", "--info"), ("timeline", "--csv"), ("timestomp",)],
                         ids=["usn-info", "timeline-csv", "timestomp-text"])
@pytest.mark.parametrize("name", A10_IMAGES, ids=A10_IDS)
def test_a10_no_longer_says_the_missing_records_were_destroyed(name, args):
    rc, out, err, prose = _a10_run(name, args)
    _keep(rc == 2, "A10 keeps exit 2" + _cctx(name, args, rc, out, err))
    bad = [l for l in prose if _DESTROYED_CLAIM.search(l)]
    assert not bad, "still claims destruction: %r" % bad[:3] + _cctx(name, args, rc, out, err)


# RED 1.13.2 A10: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", A10_CMDS, ids=A10_CMD_IDS)
@pytest.mark.parametrize("name", A10_IMAGES, ids=A10_IDS)
def test_a10_names_the_journal_instance_boundary(name, args):
    rc, out, err, prose = _a10_run(name, args)
    _keep(rc == 2, "A10 keeps exit 2" + _cctx(name, args, rc, out, err))
    assert _instance_boundary(prose), ("no line names the earlier instance 0x%016x (the id the pointing files "
                                       "carry) as distinct from the current journal 0x%016x" % (JID_OLD, JID_NEW)) \
        + _cctx(name, args, rc, out, err)


# RED 1.13.2 A10: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", A10_CMDS, ids=A10_CMD_IDS)
@pytest.mark.parametrize("name", A10_IMAGES, ids=A10_IDS)
def test_a10_missing_range_inside_image_holes_is_stated_as_a_hole_with_the_cause_open(name, args):
    rc, out, err, prose = _a10_run(name, args)
    _keep(rc == 2, "A10 keeps exit 2 (C8 = B)" + _cctx(name, args, rc, out, err))
    assert _hole_stated(_sentences(prose)), ("nothing says the image stores the journal range as a hole, with the "
                                             "cause left open (not captured, or zero on the disk)") \
        + _cctx(name, args, rc, out, err)


def _iso_key(ts):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)(?:\.(\d+))?", ts or "")
    if not m:
        return None
    frac = (m.group(7) or "0")[:6].ljust(6, "0")
    return tuple(int(x) for x in m.groups()[:6]) + (int(frac),)


NEW_JOURNAL_CREATED = (2026, 9, 20, 6, 53, 53, 132826)   # FILETIME of JID_NEW (E2 RL [M4])
OLD_LAST_RECORD = (2026, 9, 20, 6, 43, 36, 666897)       # the old instance's last record (E2-verify [V11])


# RED 1.13.2 A10: green with group 3's fix (the strict xfail mark removed)
def test_a10_mixed_instance_usn_listing_marks_the_boundary_on_image_labG_2():
    name, args = "labG_2.raw", ("usn", "--csv")
    rc, out, err = _run_corpus(FOREFST, name, *args)
    prose, header, rows = _split(out, err)
    _fx(header and "USN" in header and "Timestamp" in header and len(rows) > 40000,          # K21 (acceptance 1.14.0)
        "usn --csv did not produce the record table" + _cctx(name, args, rc, out, err))
    iu, it = header.index("USN"), header.index("Timestamp")
    new, old, odd = [], [], []
    for r in rows:
        k = _iso_key(r[it])
        if k is None:
            continue
        (new if k >= NEW_JOURNAL_CREATED else old if k <= OLD_LAST_RECORD else odd).append(r)
    # premise: two instances, each a contiguous USN block -- the new one restarted at 0 below the old survivors
    _fx(new and old and not odd, "records do not split cleanly at the new journal's creation (new %d, old %d, "
        "between %d)" % (len(new), len(old), len(odd)))
    new_hi = max(int(r[iu]) for r in new)
    old_lo = min(int(r[iu]) for r in old)
    _fx(min(int(r[iu]) for r in new) == 0 and new_hi < old_lo,
        "the new instance is not the block below the old survivors (new ..%d, old %d..)" % (new_hi, old_lo))
    # (a) a per-record instance column that partitions exactly as the timestamps do
    labelled = False
    for ci, col in enumerate(header):
        if re.search(r"(?i)instance|journal", col):
            nv, ov = {r[ci] for r in new}, {r[ci] for r in old}
            if len(nv) == 1 and len(ov) == 1 and nv != ov:
                labelled = True
    # (b) or a marker (a prose line or an inserted row) naming the boundary: an instance word and a boundary USN
    marks = [l for l in prose + [",".join(r) for r in rows]
             if re.search(r"(?i)\binstance|boundary|re-?created", l)
             and re.search(r"(?<!\d)(?:%d|%d)(?!\d)" % (new_hi, old_lo), _norm_digits(l))]
    assert labelled or marks, ("labG_2 usn --csv: %d records of the new journal (USN 0..%d) run straight into %d "
                               "records of the old one (USN %d..) with no instance column and no boundary marker"
                               % (len(new), new_hi, len(old), old_lo)) + _cctx(name, args, rc, out[:2000], err)


def test_a10_control_journal_is_whole_and_exits_0_on_image_labFbeforereboot():
    """E2 control C-P7a/b: the image taken right after the detach, before the reboot. The files point to 4,084,440,
    below the last record (4,439,864): no records are missing, so none of the three commands may say otherwise."""
    for args in A10_CMDS:
        rc, out, err = _run_corpus(FOREFST, "labFbeforereboot.raw", *args)
        prose, _h, _r = _split(out, err)
        s = _sentences(prose)
        assert rc == 0, _cctx("labFbeforereboot", args, rc, out, err)
        assert not _names_range(s) and not [l for l in prose if _DESTROYED_CLAIM.search(l)], \
            _cctx("labFbeforereboot", args, rc, out, err)
        assert not _hole_stated(s), "a whole journal reported as a hole" + \
            _cctx("labFbeforereboot", args, rc, out, err)


# RED 1.13.2 A10: the published Known-issues advice tells the examiner to report 'journal re-created', not the DESTROYED figure, when the ids differ -- on labF/labG that discards a real gap (N126, E2 N-h) -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_a10_published_advice_no_longer_says_to_discard_the_figure_when_the_ids_differ():
    p = os.path.join(REPO, "docs", "tools", "forefst.md")
    _fx(os.path.isfile(p), "docs/tools/forefst.md not found")
    md = open(p, encoding="utf-8").read()
    bad = re.findall(r"(?i)[^.]*not the DESTROYED figure[^.]*\.", md)
    assert not bad, bad


# the image-free half of A10: the text of the one function that produces the usn/timeline statement today

class _Rec(SimpleNamespace):
    pass


# RED 1.13.2 A10: green with group 3's fix (the strict xfail mark removed)
def test_a10_tail_report_text_is_neutral_and_keeps_the_finding(monkeypatch, capsys):
    """Site probe (fd:4889-4903): the witness is stubbed to the labF pointer, the surviving records end at the labF
    last USN. The finding must stay a finding (exit 2 through the single exit rule); the words must change."""
    _fresh_registers(monkeypatch)
    monkeypatch.setattr(F, "_usn_highest_file_pointer", lambda *a, **k: USN_POINTER)
    F._usn_report_destroyed_tail(None, 0, 4096, None, {}, [_Rec(usn=1024), _Rec(usn=USN_LAST)])
    out = capsys.readouterr()
    text = out.out + out.err
    _keep(_rc_escalate()(0) == 2, "the missing tail must still exit 2:\n" + text)
    lines = text.splitlines()
    s = _sentences(lines)
    _keep(bool(_names_range(s)), "the range is named today and must stay named:\n" + text)
    assert not [l for l in lines if _DESTROYED_CLAIM.search(l)], text
    assert _cannot_tell(s), text


_TEXT_1131_USN = """\
    Journal tail:   DAMAGED — the surviving records end at USN 4439864, but a file on this volume still points at USN 5119752.
                    That pointer lives in the file's own record, not in $J, so it survived: 679888 bytes of journal after the last surviving record were DESTROYED (zeroed or overwritten).
                    The records listed are NOT the whole journal and the timeline they support is incomplete."""
_TEXT_1131_TIMESTOMP = ("  USN journal:     present but TRUNCATED - 679888 bytes after the last surviving record were "
                        "destroyed; the cross-check is INCOMPLETE")
_TEXT_CORRECTED = """\
    Journal tail:   INCOMPLETE — 679,784 bytes of journal records between the last surviving record (USN 4,439,864)
                    and the highest pointer from a file (USN 5,119,752) are not on the volume; the journal cannot show
                    whether they were lost (for example at an unclean detach) or removed.
                    Those records belong to the earlier journal instance 0x01dd485de7522417; the current journal
                    0x01dd48cccc6edb06 was re-created after them.
                    The image stores the $J range that would hold them as a hole: not captured, or zero on the
                    disk; the cause cannot be told from the image."""


def test_a10_matchers_accept_a_corrected_wording_and_reject_the_1131_lines():
    """Not a RED: shows every A10 matcher accepts a plausible corrected text and rejects what 1.13.1 prints."""
    old = _TEXT_1131_USN.splitlines() + [_TEXT_1131_TIMESTOMP]
    so = _sentences(old)
    assert [l for l in old if _DESTROYED_CLAIM.search(l)] and len([l for l in old if _DESTROYED_CLAIM.search(l)]) == 2
    assert _names_range(so)                                         # 1.13.1 does name the range
    assert not _cannot_tell(so) and not _hole_stated(so) and not _instance_boundary(old)
    new = _TEXT_CORRECTED.splitlines() + ["    Journal ID:     0x01dd48cccc6edb06"]
    sn = _sentences(new)
    assert not [l for l in new if _DESTROYED_CLAIM.search(l)]
    assert _names_range(sn) and _cannot_tell(sn) and _hole_stated(sn) and _instance_boundary(new)
    # the fourth revision's wording ("unreadable", no cause) no longer meets C8 = B
    assert not _hole_stated(_sentences(["The $J range that would hold them is unreadable: the image stores it as a "
                                        "hole."]))
    # digit grouping and the record-end form of a are both accepted; an unrelated number is not
    assert _names_range(_sentences(["records USN 4 439 968 to 5_119_752 are missing"]))
    assert not _names_range(_sentences(["records end at USN 4084440 and a file points at 5119752"]))
    # _split: timeline --csv data rows in all three first-field forms are rows, not prose; the tail lines before the
    # header are prose
    # acceptance 1.14.0 (K21, K5, R1: an absent time is an empty cell; Q-C)
    tl = "\n".join(_TEXT_1131_USN.splitlines() + [
        "Timestamp,TimeSource,Source,OID,Name,PathToday,Event",
        "2026-09-20T06:19:11.0000000Z,latest FILETIME of the log payload,MLog,0x702,x,System Volume Information/x,"
        "CREATE (derived)",
        ",,MLog,0x703,lost and deleted - cannot tell.txt,LABF/lost and deleted - cannot tell.txt,"
        "DELETE (derived) [MLog time unreliable]",
        "0x1ffffffffffffffff,USN record,USN,0x708,a.txt,,FILE_DELETE"])
    p, h, r = _split(tl, "")
    assert h == ["Timestamp", "TimeSource", "Source", "OID", "Name", "PathToday", "Event"] and len(r) == 3 \
        and p == _TEXT_1131_USN.splitlines()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A11 -- refsanalysis (and forefst's own copies) as a class: checkpoint_select, supb_validate, rc_escalate are
#        single-source facts; the call-site lint sees every inline copy; the displays use the checkpoint in use
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# The verification tree sits beside forefstdev/ in the maintainer's workspace; in the published tree it is the
# tree's own analysis/verification/, where sync_dev_to_pub.sh ships the lint and its list (single_source.tsv,
# check_single_source.py), so the lint nodes run there too. They skip in a tree that lacks either file.
_WS = os.path.dirname(REPO) if os.path.basename(REPO) == "forefstdev" else REPO
VERIFICATION = os.path.join(_WS, "analysis", "verification")
SINGLE_SOURCE_TSV = os.path.join(VERIFICATION, "single_source.tsv")
LINT = os.path.join(VERIFICATION, "check_single_source.py")


def _need_verification_tree():
    if not (os.path.isfile(SINGLE_SOURCE_TSV) and os.path.isfile(LINT)):
        pytest.skip("analysis/verification/single_source.tsv or check_single_source.py is not in this tree")


def _ss_rows():
    _need_verification_tree()
    rows = {}
    for line in open(SINGLE_SOURCE_TSV, encoding="utf-8"):
        line = line.rstrip("\n")
        if line and not line.startswith("#"):
            p = line.split("\t")
            if len(p) >= 3:
                rows[p[0]] = p
    _fx(rows.get("checkpoint_parse", [None, None])[1] == "parse_chkp", "single_source.tsv is not the expected file")
    return rows


def _defs_and_refs(path):
    import ast
    tree = ast.parse(open(path, encoding="utf-8").read())
    defs, refs = {}, set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs[n.name] = defs.get(n.name, 0) + 1
        elif isinstance(n, ast.Name):
            refs.add(n.id)
        elif isinstance(n, ast.Attribute):
            refs.add(n.attr)
        elif isinstance(n, ast.alias):
            refs.add(n.asname or n.name)
            refs.add(n.name)
    return defs, refs


@pytest.mark.parametrize("fact", ["checkpoint_select", "supb_validate", "rc_escalate"])
def test_a11_fact_is_one_forefst_function_that_refsanalysis_imports(fact):
    rows = _ss_rows()
    assert fact in rows, "single_source.tsv has no row for %s" % fact
    fn, owner = rows[fact][1], rows[fact][2]
    assert owner.endswith("forefst.py"), "%s is owned by %s, not forefst.py" % (fact, owner)
    fdefs, _ = _defs_and_refs(os.path.join(REPO, "forefst.py"))
    rdefs, rrefs = _defs_and_refs(os.path.join(REPO, "refsanalysis.py"))
    assert fdefs.get(fn) == 1, "%s(): %d definition(s) in forefst.py" % (fn, fdefs.get(fn, 0))
    assert fn not in rdefs, "refsanalysis.py defines its own %s()" % fn
    assert fn in rrefs, "refsanalysis.py never uses forefst's %s()" % fn


# The call-site pass. Each plant is a VERBATIM 1.13.1 site from the item record (only wrapped in a def and given a
# unique name), appended to a copy of the tool in a scratch tree laid out like the repo. The lint is the repo's own
# `check_single_source.py`, copied with every top-level file of analysis/verification, and run on that tree.

_PLANTS_SELECT = {
    # ra:381-386 -- refsanalysis summary: `>=` over parse_chkp()'s first value, no checksum check
    "ra-summary-ge": ("refsanalysis.py", '''
        def _red_plant_ra_summary_ge(f, ps, cs, chkp_lcns):
            best_vc = 0; best_flags = 0
            for cl in chkp_lcns:
                try:
                    vc, flags, _ = _forefst_parse_chkp(f, ps, cs, cl)
                    if vc >= best_vc: best_vc = vc; best_flags = flags
                except Exception as _e: _skip_note("summary: checkpoint", f"lcn {cl}", _e)
            return best_vc, best_flags
    '''),
    # ra:958-966 -- refsanalysis supb: max() over the +0x10 clock (the `*` marker and latest_identified)
    "ra-supb-max": ("refsanalysis.py", '''
        def _red_plant_ra_supb_max(f, supb_page, chkp_off, _cnt, bo, cs, img_size):
            checkpoints = []
            for i in range(_cnt):
                block = le64(supb_page, chkp_off + i * 8)
                resolved = bo + block * cs
                chkp_hdr = {}
                if resolved + 0x80 <= img_size:
                    h = _read_at(f, resolved, 0x80)
                    chkp_hdr = {"signature": h[0:4], "virtual_clock": le64(h, 0x10)}
                checkpoints.append({"index": i+1, "block": block, "resolved": resolved, "chkp": chkp_hdr})
            valid_chkp = [c for c in checkpoints if c["chkp"].get("signature") == b"CHKP"]
            latest = max(valid_chkp, key=lambda c: c["chkp"]["virtual_clock"]) if valid_chkp else None
            return latest
    '''),
    # ra:1700-1708 -- refsanalysis chkp: `>` over le64(raw, 0x10) of a CHKP page
    "ra-chkp-gt": ("refsanalysis.py", '''
        def _red_plant_ra_chkp_gt(f, ps, cs, chkp_lcns):
            best_raw = None; best_vc = -1; best_off = 0
            for lcn in chkp_lcns:
                off = ps + lcn * cs
                raw = _read_at(f, off, _page_bytes(cs))
                if raw[:4] != b"CHKP": continue
                vc = le64(raw, 0x10)
                if vc > best_vc:
                    best_raw = raw; best_vc = vc; best_off = off
            return best_raw, best_off
    '''),
    # ra:2403-2408 -- refsanalysis containers: `>=` over parse_chkp()'s first value, roots taken from the winner
    "ra-containers-ge": ("refsanalysis.py", '''
        def _red_plant_ra_containers_ge(f, ps, cs, chkp_lcns):
            best_vc = 0; best_roots = None
            for cl in chkp_lcns:
                try:
                    vc, fl, rts = _forefst_parse_chkp(f, ps, cs, cl)
                    if vc >= best_vc: best_vc = vc; best_roots = rts
                except Exception as _e:
                    _skip_note("containers: checkpoint", f"lcn {cl}", _e)
            return best_roots
    '''),
    # fd:6094-6100 -- fastsummary/summary Checkpoint section and CHKP hash: `>=` over parse_chkp()'s first value
    "fd-fastsummary-ge": ("forefst.py", '''
        def _red_plant_fd_fastsummary_ge(f, ps, cs, chkp_lcns):
            best_vc = 0; best_flags = 0; chkp_sha = ""
            for cl in chkp_lcns:
                try:
                    vc, flags, _ = parse_chkp(f, ps, cs, cl)
                    if vc >= best_vc:
                        best_vc = vc; best_flags = flags
                        chkp_sha = _hash_page(f, ps + cl * cs, _page_bytes(cs))
                except Exception as _e: _skip_note("fastsummary: checkpoint", f"lcn {cl}", _e)
            return best_vc, chkp_sha
    '''),
    # fd:14131-14137 -- deleted: sort by parse_chkp()'s first value
    "fd-deleted-sort": ("forefst.py", '''
        def _red_plant_fd_deleted_sort(f, ps, cs, chkp_lcns):
            checkpoints = []
            for lcn in chkp_lcns:
                try:
                    vc, flags, chkp_roots = _forefst_parse_chkp(f, ps, cs, lcn)
                    checkpoints.append((vc, chkp_roots, lcn))
                except Exception as _e:
                    _skip_note("cmd_deleted", "a deleted-file candidate", _e)
            checkpoints.sort(key=lambda x: x[0], reverse=True)
            return checkpoints
    '''),
    # fd:14844-14854 -- integrity `Checkpoint VC:` header: `>` over le64(raw, 0x60) of a CHKP page
    "fd-integrity-header": ("forefst.py", '''
        def _red_plant_fd_integrity_header(f, ps, cs, chkp_lcns):
            best_vc = -1; best_volsig = 0; best_chk = None; best_lcn = None
            for cl in chkp_lcns:
                try:
                    f.seek(ps + cl * cs); raw = f.read(_page_bytes(cs))
                    if raw[:4] == b"CHKP":
                        vc = le64(raw, 0x60)
                        if vc > best_vc or (vc == best_vc and (best_lcn is None or cl < best_lcn)):
                            best_vc = vc; best_volsig = le32(raw, 0x0C); best_chk = raw; best_lcn = cl
                except Exception as _e:
                    _skip_note("cmd_integrity", "a page checksum", _e)
            return best_chk
    '''),
    # fd:15420-15429 -- export metadata: max() over le64(p, 0x60) of the CHKP pages
    "fd-export-max": ("forefst.py", '''
        def _red_plant_fd_export_max(rd, chkp_lcns):
            _chkp_pages = {}
            for cl in chkp_lcns:
                _chkp_pages[cl] = rd(cl, 4)
            _chkp_clk = {cl: (le64(p, 0x60) if len(p) >= 0x68 and p[:4] == b"CHKP" else None)
                         for cl, p in _chkp_pages.items()}
            _seen_clk = [v for v in _chkp_clk.values() if v is not None]
            _best_clk = max(_seen_clk) if _seen_clk else None
            return _best_clk
    '''),
}

_PLANTS_EXIT = {
    # ra:4351 -- refsanalysis main: sys.exit(handler(...)) with no escalation
    "ra-exit-handler": ("refsanalysis.py", '''
        def _red_plant_ra_exit_handler(image, remaining, partition_start):
            handler = _HANDLERS.get("summary")
            sys.exit(handler(image, remaining, partition_start))
    '''),
    # the acceptance's own example: a planted sys.exit(rc) bypass
    "ra-exit-rc": ("refsanalysis.py", '''
        def _red_plant_ra_exit_rc(image, remaining, partition_start):
            rc = cmd_summary(image, remaining, partition_start)
            sys.exit(rc)
    '''),
}


def _lint_tree(tmp_path):
    """A scratch tree the lint resolves as the repo: analysis/verification/<its top-level files> + forefstdev/."""
    _need_verification_tree()
    root = tmp_path / "tree"
    ver = root / "analysis" / "verification"
    tools = root / "forefstdev"
    ver.mkdir(parents=True)
    tools.mkdir()
    for n in os.listdir(VERIFICATION):
        p = os.path.join(VERIFICATION, n)
        if os.path.isfile(p):
            shutil.copy2(p, str(ver / n))
    for n in ("forefst.py", "refsanalysis.py"):
        shutil.copy2(os.path.join(REPO, n), str(tools / n))
    return root


def _run_lint(root):
    r = subprocess.run([sys.executable, "-B", str(root / "analysis" / "verification" / "check_single_source.py")],
                       capture_output=True, text=True, timeout=300, cwd=str(root))
    return r.returncode, r.stdout + r.stderr


def _plant(root, tool, code):
    path = root / "forefstdev" / tool
    src = path.read_text(encoding="utf-8")
    first = src.count("\n") + 3
    body = textwrap.dedent(code).strip("\n")
    path.write_text(src + "\n\n" + body + "\n", encoding="utf-8")
    fn = re.search(r"def (\w+)", body).group(1)
    return fn, range(first, first + body.count("\n") + 1)


def _names_plant(out, tool, fn, lines):
    if fn in out:
        return True
    for m in re.finditer(r"%s\D{0,12}?(\d+)" % re.escape(tool), out):
        if int(m.group(1)) in lines:
            return True
    return False


def _lint_red(tmp_path, plants, pid):
    root = _lint_tree(tmp_path)
    rc0, out0 = _run_lint(root)
    _keep(rc0 == 0, "the lint must pass on the unplanted tree (acceptance: 0 violations after the fix):\n" + out0)
    tool, code = plants[pid]
    fn, lines = _plant(root, tool, code)
    rc, out = _run_lint(root)
    _fx("Traceback" not in out, "the lint crashed on the planted tree:\n" + out)
    assert rc != 0, "the lint passed with %s planted in %s (lines %d-%d):\n%s" % (fn, tool, lines[0], lines[-1], out)
    assert _names_plant(out, tool, fn, lines), "the lint failed but does not name the plant %s:\n%s" % (fn, out)


@pytest.mark.parametrize("pid", sorted(_PLANTS_SELECT))
def test_a11_lint_fails_on_a_planted_checkpoint_clock_selection(tmp_path, pid):
    _lint_red(tmp_path, _PLANTS_SELECT, pid)


@pytest.mark.parametrize("pid", sorted(_PLANTS_EXIT))
def test_a11_lint_fails_on_a_planted_exit_that_bypasses_rc_escalate(tmp_path, pid):
    _lint_red(tmp_path, _PLANTS_EXIT, pid)


# Not 1.13.1 sites: the shapes a regression would take AFTER A11 (review N1, REVIEW_A11_correctness.md section 5.1,
# plants R1-R4). refsanalysis re-ranks the copies that forefst's checkpoint_select returns. The clock sits under a
# key ("vc", "vc_page") that only forefst.py stores, so a lint that derives its keys one file at a time never sees
# these. Each is planted in refsanalysis.py, where the 1.13.1 copies of the selection lived.
_PLANTS_SELECT_POST_A11 = {
    "R1-ra-copies-max": ("refsanalysis.py", '''
        def _red_plant_r1_ra_copies_max(f, ps, cs, chkp_lcns):
            return max(checkpoint_select(f, ps, cs, chkp_lcns)["copies"], key=lambda c: c["vc"])
    '''),
    "R2-ra-copies-sorted": ("refsanalysis.py", '''
        def _red_plant_r2_ra_copies_sorted(f, ps, cs, chkp_lcns):
            copies = checkpoint_select(f, ps, cs, chkp_lcns)["copies"]
            return sorted(copies, key=lambda c: -c["vc"])[0]
    '''),
    "R3-ra-copies-ge": ("refsanalysis.py", '''
        def _red_plant_r3_ra_copies_ge(f, ps, cs, chkp_lcns):
            sel = checkpoint_select(f, ps, cs, chkp_lcns)
            a, b = sel["copies"][0], sel["copies"][1]
            return a if a["vc"] >= b["vc"] else b
    '''),
    "R4-ra-copies-max-page-clock": ("refsanalysis.py", '''
        def _red_plant_r4_ra_copies_max_page_clock(f, ps, cs, chkp_lcns):
            return max(checkpoint_select(f, ps, cs, chkp_lcns)["copies"], key=lambda c: c["vc_page"])
    '''),
}


@pytest.mark.parametrize("pid", sorted(_PLANTS_SELECT_POST_A11))
def test_a11_lint_fails_on_a_planted_reselection_keyed_by_the_other_tool(tmp_path, pid):
    _lint_red(tmp_path, _PLANTS_SELECT_POST_A11, pid)


@pytest.mark.parametrize("pid", sorted(_PLANTS_SELECT_POST_A11))
def test_a11_lint_control_the_same_reselection_in_forefst_is_caught(tmp_path, pid):
    """Control for the test above: each plant's body, planted in forefst.py -- the file that stores "vc" and
    "vc_page" itself -- is caught even by a lint that derives its keys one file at a time (the pre-N1 lint caught all
    four; REVIEW_N1.md check 4). So each shape is a violation the lint recognises, and the plants above could fail
    on the pre-N1 lint only because the key comes from the other file."""
    tool, code = _PLANTS_SELECT_POST_A11[pid]
    _lint_red(tmp_path, {pid + "-in-forefst": ("forefst.py", code)}, pid + "-in-forefst")


def test_a11_plants_are_verbatim_1131_sites():
    """Not a RED: every planted body of _PLANTS_SELECT and _PLANTS_EXIT (not the post-A11 shapes R1-R4) has its
    selection or exit line still in the 1.13.1 tool it came from, so a plant is a real site's shape, not an
    invented one. (After the fix the sites move; this test then documents what the plants were copied from.)"""
    key_lines = {
        "ra-summary-ge": "if vc >= best_vc: best_vc = vc; best_flags = flags",
        "ra-supb-max": 'latest = max(valid_chkp, key=lambda c: c["chkp"]["virtual_clock"]) if valid_chkp else None',
        "ra-chkp-gt": "vc = le64(raw, 0x10)",
        "ra-containers-ge": "if vc >= best_vc: best_vc = vc; best_roots = rts",
        "fd-fastsummary-ge": "chkp_sha = _hash_page(f, ps + cl * cs, _page_bytes(cs))",
        "fd-deleted-sort": "checkpoints.sort(key=lambda x: x[0], reverse=True)",
        "fd-integrity-header": "if vc > best_vc or (vc == best_vc and (best_lcn is None or cl < best_lcn)):",
        "fd-export-max": "_best_clk = max(_seen_clk) if _seen_clk else None",
        "ra-exit-handler": "sys.exit(handler(image, remaining, partition_start))",
    }
    # Checked against the 1.13.1 tools as tagged: the verification tree keeps them (versions/v1.13.1/, the files of
    # tag v1.13.1 = d4d5fd28, versions/MANIFEST.tsv), so the check no longer depends on the published tree, which
    # left 1.13.1 at the RC2 sync (N640). The published tree's own copy of the tests has no versions/ folder.
    pub = os.path.join(VERIFICATION, "versions", "v1.13.1")
    try:
        ver = re.search(r'^VERSION = "([^"]+)"', open(os.path.join(pub, "forefst.py"), encoding="utf-8").read(), re.M)
    except OSError:
        ver = None
    if not ver or ver.group(1) != "1.13.1":
        pytest.skip("the kept 1.13.1 tools (analysis/verification/versions/v1.13.1/) are not in this tree")
    for pid, needle in key_lines.items():
        tool = (_PLANTS_SELECT.get(pid) or _PLANTS_EXIT.get(pid))[0]
        src = open(os.path.join(pub, tool), encoding="utf-8").read()
        assert needle in src, "%s: %r not in %s" % (pid, needle, tool)
        assert needle in textwrap.dedent((_PLANTS_SELECT.get(pid) or _PLANTS_EXIT.get(pid))[1]), pid


# ── the displays that rank checkpoints by clock without checking them (battery case A1_chkp_flip_newest) ───────

def _off_re(off):
    return re.compile(r"(?i)(?<![0-9a-z])0x0*%x(?![0-9a-z])" % off)


def _flip_newest(v):
    """Battery A1_chkp_flip_newest: the newest copy (slot 0, the lower LCN, vclock 64) fails its self-checksum."""
    damage_chkp(v, v.geo.lo)
    _fx(v.verifies(v.geo.hi) is True, "the older copy must still verify")
    return v.geo.lo, v.at(v.geo.lo), v.geo.hi, v.at(v.geo.hi)


def _active_marks(text):
    """Lines carrying the active-checkpoint marker of refsanalysis supb (` *` at the end in the compact view,
    `<- active` in -v, which sits on the line after the one naming the cluster) and the latest_checkpoint row. Wave E step
    E1c (N377): a table row's details wrap; the row is read with its continuation lines (`conftest.unwrap_table_rows`)."""
    from conftest import unwrap_table_rows
    ls = unwrap_table_rows(text).splitlines()
    out = []
    for i, l in enumerate(ls):
        # wave E step E1c (N355): decision 25.4's words -- "(* = the checkpoint copy in use)", "<- in use",
        # `checkpoint_in_use` -- replaced "active" / "latest"; both are read
        if re.search(r"\s\*\s*$", l) and "(* = active" not in l and "(* = the checkpoint copy in use" not in l:
            out.append(l)
        elif "<- active" in l or "<- in use" in l:
            out.append((ls[i - 1] if i else "") + " " + l)
        elif re.search(r"(?i)latest_checkpoint|latest checkpoint|checkpoint_in_use", l):
            out.append(l)
    return out


def test_a11_control_supb_marks_the_newest_valid_copy_active(vol):
    """Undamaged: the newest copy (slot 0, vclock 64) carries the marker. A fix may not move it to the older one."""
    for args in (("supb",), ("supb", "-v")):
        rc, out = vol.run(REFSANALYSIS, *args)
        marks = _active_marks(out)
        assert rc == 0 and marks and all(_lcn_re(vol.geo.lo).search(m) or _off_re(vol.at(vol.geo.lo)).search(m)
                                         for m in marks), _ctx(vol, rc, out)


@pytest.mark.parametrize("verbose", [(), ("-v",)], ids=["compact", "verbose"])
def test_a11_refsanalysis_supb_does_not_mark_a_failed_checkpoint_active(vol, verbose):
    lo, lo_off, hi, hi_off = _flip_newest(vol)
    rc, out = vol.run(REFSANALYSIS, "supb", *verbose)
    marks = _active_marks(out)
    bad = [m for m in marks if (_lcn_re(lo).search(m) or _off_re(lo_off).search(m)) and not _FAIL.search(m)]
    assert not bad, "the failed copy is marked active: %r" % bad + _ctx(vol, rc, out)


def test_a11_control_chkp_describes_the_newest_copy(vol):
    rc, out = vol.run(REFSANALYSIS, "chkp")
    assert rc == 0 and re.search(r"CHKP\) at offset 0x0*%x\b" % vol.at(vol.geo.lo), out), _ctx(vol, rc, out)


def test_a11_refsanalysis_chkp_describes_the_checkpoint_in_use_or_names_the_failed_copy(vol):
    lo, lo_off, hi, hi_off = _flip_newest(vol)
    rc, out = vol.run(REFSANALYSIS, "chkp")
    shows_in_use = re.search(r"(?i)CHKP\) at offset 0x0*%x\b" % hi_off, out)
    names_failed = [l for l in out.splitlines()
                    if (_lcn_re(lo).search(l) or _off_re(lo_off).search(l)) and _FAIL.search(l)]
    assert shows_in_use or names_failed, "chkp describes the failed copy at 0x%x as if it were in use" % lo_off \
        + _ctx(vol, rc, out)


def test_a11_refsanalysis_containers_discloses_which_checkpoint_it_read(vol):
    lo, lo_off, hi, hi_off = _flip_newest(vol)
    rc, out = vol.run(REFSANALYSIS, "containers")
    names_failed = [l for l in out.splitlines()
                    if (_lcn_re(lo).search(l) or _off_re(lo_off).search(l)) and _FAIL.search(l)]
    names_in_use = [l for l in out.splitlines() if _lcn_re(hi).search(l) or _off_re(hi_off).search(l)]
    assert names_failed or names_in_use, "containers names neither the failed copy nor the copy it read" \
        + _ctx(vol, rc, out)


def test_a11_control_integrity_header_is_the_newest_clock(vol):
    rc, out = vol.run(FOREFST, "integrity")
    m = re.search(r"Checkpoint VC:\s+(\d+)", out)
    assert rc == 0 and m and int(m.group(1)) == CLOCK_NEW, _ctx(vol, rc, out)


def test_a11_integrity_checkpoint_vc_header_is_the_copy_in_use(vol):
    _flip_newest(vol)
    rc, out = vol.run(FOREFST, "integrity")
    m = re.search(r"^.*Checkpoint VC:.*$", out, re.M)
    _fx(m, "integrity printed no `Checkpoint VC:` header" + _ctx(vol, rc, out))
    vc = re.search(r"Checkpoint VC:\s+(\d+)", m.group(0))
    assert (vc and int(vc.group(1)) == CLOCK_OLD) or _FAIL.search(m.group(0)), \
        "header: %r" % m.group(0) + _ctx(vol, rc, out)


# ── F1 closes with checkpoint_select: on a +0x60 tie with both copies valid the driver keeps SUPERBLOCK SLOT 0 ──

def _primary_lcn(text, cmd):
    pat = (r"Checkpoint \[PRIMARY\s*\]:\s+LCN (0x[0-9a-f]+)" if cmd == "integrity"
           else r"CHKP primary\s+LCN (0x[0-9a-f]+)")
    m = re.search(pat, text, re.I)
    return int(m.group(1), 16) if m else None


@pytest.mark.parametrize("cmd", ["integrity", "summary"])
def test_a11_f1_tie_control_slot0_lower_lcn_both_rules_agree(vol, cmd):
    """slot 0 = the lower LCN (the corpus order): 'earlier slot' and 'lowest LCN' pick the same copy."""
    make_tie(vol, slot0_higher=False)
    rc, out = vol.run(FOREFST, cmd)
    assert rc == 0 and _primary_lcn(out, cmd) == vol.geo.lo, _ctx(vol, rc, out)


@pytest.mark.parametrize("cmd", ["integrity", "summary"])
def test_a11_f1_tie_the_copy_in_use_is_superblock_slot_0(vol, cmd):
    make_tie(vol, slot0_higher=True)
    _fx(vol.refs(vol.geo.supb)[0] == vol.geo.hi, "slot 0 is not the higher LCN after the swap")
    rc, out = vol.run(FOREFST, cmd)
    _keep(rc == 0, "a tie with both copies valid is not a finding" + _ctx(vol, rc, out))
    p = _primary_lcn(out, cmd)
    _fx(p is not None, "no primary checkpoint line" + _ctx(vol, rc, out))
    assert p == vol.geo.hi, "primary/in-use copy is LCN 0x%x; the driver keeps slot 0 = 0x%x" % (p, vol.geo.hi) \
        + _ctx(vol, rc, out)


def test_a11_f1_tie_note_does_not_state_the_lowest_lcn_rule(vol):
    make_tie(vol, slot0_higher=True)
    rc, out = vol.run(FOREFST, "integrity")
    _keep(re.search(r"(?i)\btie\b", out), "the tie is reported today and must stay reported" + _ctx(vol, rc, out))
    bad = [l for l in out.splitlines() if re.search(r"(?i)chosen by (?:the )?lowest[- ]LCN", l)]
    assert not bad, bad


# ── N133, folded into A11: one condition, one exit code and one stated reason, whatever the command ────────────

def test_n133_timestomp_csv_states_why_it_exits_2_on_image_labFafterreboot():
    name, args = "labFafterreboot.raw", ("timestomp", "--csv")
    rc, out, err = _run_corpus(FOREFST, name, *args)
    prose, header, rows = _split(out, err)
    _fx(header and rows, "timestomp --csv produced no CSV table" + _cctx(name, args, rc, out, err))
    _keep(rc == 2, "the tail is really missing; exit 2 stays" + _cctx(name, args, rc, out, err))
    why = [l for l in prose if _JOURNAL.search(l) and re.search(
        r"(?i)missing|incomplete|truncat|not on the volume|unreadable|hole|\b%d\b" % USN_POINTER, _norm_digits(l))]
    assert why, "rc 2 with no stated reason; prose was: %r" % [l for l in prose if l.strip()][:8]


def test_n133_summary_json_carries_the_redundancy_finding_on_image_labFbeforereboot():
    name, args = "labFbeforereboot.raw", ("summary", "--json")
    rc, out, err = _run_corpus(FOREFST, name, *args)
    try:
        json.loads(out)
    except ValueError:
        raise RedFixtureError("summary --json is not JSON" + _cctx(name, args, rc, out, err))
    _keep(rc == 2, "the unclean dismount is a finding (E2 C09)" + _cctx(name, args, rc, out, err))
    assert re.search(r"(?i)dismount", out), "rc 2 and no JSON field names the finding" + _cctx(name, args, rc, "", err)


@pytest.mark.parametrize("fmt", [(), ("--json",)], ids=["text", "json"])
def test_n133_fastsummary_reports_the_unclean_dismount_as_summary_does_on_image_labFbeforereboot(fmt):
    name = "labFbeforereboot.raw"
    src, sout, serr = _run_corpus(FOREFST, name, "summary")
    _keep(src == 2 and re.search(r"(?i)not cleanly dismounted", sout),
          "summary's finding (E2 C09) must stay" + _cctx(name, ("summary",), src, sout, serr))
    rc, out, err = _run_corpus(FOREFST, name, "fastsummary", *fmt)
    assert rc == src, "fastsummary rc %d, summary rc %d on the same volume" % (rc, src)
    assert re.search(r"(?i)dismount", out + err), "fastsummary does not name the finding" + \
        _cctx(name, ("fastsummary",) + fmt, rc, out, err)


def test_n133_control_summary_and_fastsummary_agree_on_image_labFafterreboot():
    """E2 controls C-P5c/C-P6: the recovered twin carries no redundancy finding; both summaries exit 0."""
    name = "labFafterreboot.raw"
    for args in (("summary",), ("fastsummary",)):
        rc, out, err = _run_corpus(FOREFST, name, *args)
        assert rc == 0 and not re.search(r"(?i)not cleanly dismounted", out + err), _cctx(name, args, rc, out, err)


@pytest.mark.parametrize("args", [("usn", "--stats"), ("usn", "--csv")], ids=["stats", "csv"])
def test_n133_usn_stats_and_csv_report_the_missing_tail_and_exit_2_on_image_labFafterreboot(args):
    name = "labFafterreboot.raw"
    _a10_premise(name)
    irc, iout, ierr = _run_corpus(FOREFST, name, "usn", "--info")
    _keep(irc == 2, "usn --info reports the gap with exit 2 today" + _cctx(name, ("usn", "--info"), irc, iout, ierr))
    rc, out, err = _run_corpus(FOREFST, name, *args)
    prose, _h, _r = _split(out, err)
    said = [l for l in prose if re.search(r"(?<!\d)%d(?!\d)" % USN_POINTER, _norm_digits(l))]
    assert rc == 2, "usn %s exits %d while usn --info exits 2 on the same journal" % (args[1], rc) + \
        _cctx(name, args, rc, out[:1500], err)
    assert said, "no line names the missing range" + _cctx(name, args, rc, out[:1500], err)


def _fake_recycle_volume(tmp_path, monkeypatch, draw_from_hole):
    """cmd_recyclebin's own code on stubbed reads: one $RECYCLE.BIN with one $I item. When `draw_from_hole`, the
    item's content is produced through the REAL content_holes() check over a real sparse file whose run is a hole
    -- the path an extent-backed $I would take (get_file_content -> content_holes). N133 calls this latent."""
    img = tmp_path / "sparse.raw"
    with open(str(img), "wb") as fh:
        fh.truncate(1 << 20)
    fh = open(str(img), "rb")
    rows = [(struct.pack("<HH", 0x30, 0) + "$RECYCLE.BIN".encode("utf-16-le"),
             struct.pack("<QQ", 0, 0x7000))]
    monkeypatch.setattr(F, "bootstrap", lambda image, ps=None: (fh, 0, 4096, None, [], {0x600: [1]}, 3, 14, []))
    monkeypatch.setattr(F, "walk_bplus", lambda *a, **k: list(rows) if k.get("oid") == 0x600 else [])

    def walk_recycle(f, ps, cs, tr, obj_map, oid, path, depth, recs):
        _fx(oid == 0x7000, "cmd_recyclebin did not follow the $RECYCLE.BIN row")
        if draw_from_hole:
            got = F.content_holes(f, ps, cs, [(16, 1, 0)], "$I content of $IABC123.txt", stream_size=544)
            _fx(got == 544, "the sparse fixture did not read as a hole (content_holes -> %r)" % (got,))
        recs.append({"sid": "S-1-5-21-1", "i_name": "$IABC123.txt", "r_name": "$RABC123.txt",
                     "r_present": False, "meta": None})
    monkeypatch.setattr(F, "_walk_recycle", walk_recycle)
    return str(img), fh


def test_n133_control_recyclebin_with_no_hole_exits_0(tmp_path, monkeypatch, capsys):
    _fresh_registers(monkeypatch)
    img, fh = _fake_recycle_volume(tmp_path, monkeypatch, draw_from_hole=False)
    try:
        rc = _rc_escalate()(F.cmd_recyclebin(img, [], None))
    finally:
        fh.close()
    assert rc == 0, capsys.readouterr()


def test_n133_recyclebin_output_drawn_from_holes_exits_2(tmp_path, monkeypatch, capsys):
    _fresh_registers(monkeypatch)
    img, fh = _fake_recycle_volume(tmp_path, monkeypatch, draw_from_hole=True)
    try:
        rc = _rc_escalate()(F.cmd_recyclebin(img, [], None))
    finally:
        fh.close()
    _fx(F._CONTENT_HOLES, "the hole was not recorded by content_holes()")
    assert rc == 2, "rc %d with %r recorded" % (rc, F._CONTENT_HOLES)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A12 -- the `refsanalysis <image> forefst <cmd>` passthrough loses the exit 2 that forefst.py's __main__ adds
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# RED 1.13.2 A12: green since A11 (rc_escalate on the passthrough), confirmed by wave B part 2 (the strict xfail mark removed)
def test_a12_passthrough_summary_exits_2_as_forefst_summary_does(vol):
    _flip_newest(vol)
    frc, fout = vol.run(FOREFST, "summary")
    _keep(frc == 2, "forefst.py summary exits 2 on battery A1_chkp_flip_newest" + _ctx(vol, frc, fout))
    rc, out = vol.run(REFSANALYSIS, "forefst", "summary")
    _fx(re.search(r"(?i)Volume GUID", out), "the passthrough did not run forefst summary" + _ctx(vol, rc, out))
    assert rc == frc, "passthrough rc %d, forefst.py rc %d" % (rc, frc) + _ctx(vol, rc, out)


def test_a12_control_passthrough_keeps_a_commands_own_exit_2(vol):
    """integrity --checksums returns 2 itself (a verdict), so the passthrough already keeps it."""
    _flip_newest(vol)
    frc, fout = vol.run(FOREFST, "integrity", "--checksums")
    rc, out = vol.run(REFSANALYSIS, "forefst", "integrity", "--checksums")
    assert frc == 2 and rc == 2, _ctx(vol, rc, out)


def test_a12_control_passthrough_summary_exits_0_on_the_undamaged_volume(vol):
    rc, out = vol.run(REFSANALYSIS, "forefst", "summary")
    assert rc == 0 and re.search(r"(?i)Volume GUID", out), _ctx(vol, rc, out)


def _refsanalysis_md():
    p = os.path.join(REPO, "docs", "tools", "refsanalysis.md")
    _fx(os.path.isfile(p), "docs/tools/refsanalysis.md not found")
    return open(p, encoding="utf-8").read()


# RED 1.13.2 A12: docs/tools/refsanalysis.md (the passthrough section) says the passthrough can exit 0 where forefst.py exits 2 -- green with the RC1-docs step (1.14.0; the strict xfail mark removed)
def test_a12_refsanalysis_md_passthrough_section_states_the_same_exit_code():
    md = _refsanalysis_md()
    m = re.search(r"^## Running forefst commands via refsanalysis\n(.*?)(?=^## )", md, re.S | re.M)
    _fx(m, "the passthrough section is gone or renamed")
    sec = m.group(1)
    bad = re.findall(r"(?i)[^.]*(?:except the exit code|can exit 0 where|is not, so the passthrough)[^.]*\.", sec)
    assert not bad, bad


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A13 -- "their payload is identical -- redundancy, not divergence" is printed without comparing the payloads
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_IDENTICAL_NOTE = re.compile(r"(?i)payload\W+(?:\w+\W+){0,3}identical")
_DIFFERS = re.compile(r"(?i)\b(?:differ\w*|diverg\w*|mismatch\w*|not identical|disagree\w*|inconsistent)\b")


def _flip_backup_guid(v, reseal):
    """One GUID byte flipped in the first backup superblock. `reseal`: the copy's self-checksum is recomputed, so it
    PASSES its checksum and only its payload differs (A13 alone); otherwise it also fails its checksum (N113's
    measured case, where A1 applies too)."""
    b = v.geo.backups[0]
    if reseal:
        def edit(buf):
            buf[0x50] ^= 0x01
        v.reseal(b, edit, SUPB_DESC)
        _fx(v.verifies(b) is True, "the resealed backup does not verify")
    else:
        damage_supb(v, "backup")
    _fx(v.block(b)[0x50:0x60] != v.block(v.geo.supb)[0x50:0x60], "the backup's GUID equals the primary's")
    return b


def test_a13_control_undamaged_copies_are_not_called_divergent(vol):
    for cmd in ("summary", "fastsummary"):
        rc, out = vol.run(FOREFST, cmd)
        bad = [l for l in out.splitlines()
               if _DIFFERS.search(l) and any(_lcn_re(x).search(l) for x in (vol.geo.supb,) + vol.geo.backups)]
        assert rc == 0 and not bad, _ctx(vol, rc, out)


# RED 1.13.2 A13: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("reseal", [True, False], ids=["backup-resealed", "backup-checksum-failed"])
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_a13_identical_payload_note_only_after_a_comparison_and_the_differing_copy_is_named(vol, cmd, reseal):
    b = _flip_backup_guid(vol, reseal)
    rc, out = vol.run(FOREFST, cmd)
    notes = [l for l in out.splitlines() if _IDENTICAL_NOTE.search(l)]
    assert not notes, "note printed over differing payloads: %r" % notes + _ctx(vol, rc, out)
    named = [l for l in out.splitlines() if _lcn_re(b).search(l) and (_DIFFERS.search(l) or re.search(r"(?i)GUID", l))]
    assert named, "the differing backup at LCN 0x%x is not named" % b + _ctx(vol, rc, out)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N134 -- the version-contradiction sentence prints the boot sector's version as "v3.%d": 6.66 reads "v3.66"
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _contradiction_in_process(tmp_path, monkeypatch, vmaj, vmin, vol_major=3, vol_minor=14):
    """cmd_fastsummary on the synthetic volume, bootstrapped in-process, with the boot-sector version given as
    (vmaj, vmin) and a $VOLUME_INFORMATION row (OID 0x500, key 0x0520) stamping vol/driver (vol_major, vol_minor)."""
    _fresh_registers(monkeypatch)
    v = _synthetic_vol(tmp_path)
    f, ps, cs, tr, roots, obj_map, _vmaj, _vmin, chkp_lcns = F.bootstrap(v.path, 0)
    orig = F.walk_bplus
    seen = []

    def walk(f_, ps_, cs_, tr_, vlcns, *a, **k):
        if k.get("oid") == 0x500:
            seen.append(1)
            vd = bytearray(0xA8)
            vd[0x80:0x84] = bytes([vol_major, vol_minor, vol_major, vol_minor])
            return [(struct.pack("<H", 0x0520) + b"\0" * 6, bytes(vd))]
        return orig(f_, ps_, cs_, tr_, vlcns, *a, **k)
    monkeypatch.setattr(F, "walk_bplus", walk)
    om = dict(obj_map)
    om[0x500] = [1]
    try:
        s = F.cmd_fastsummary(f, ps, cs, tr, roots, om, vmaj, vmin, chkp_lcns, v.path, plus_mode=True)
    finally:
        f.close()
    _fx(seen, "cmd_fastsummary did not read $VOLUME_INFORMATION through OID 0x500")
    _fx(s.get("volume_version") == "%d.%d" % (vol_major, vol_minor), "the stub row was not used: %r" % s.get("volume_version"))
    return s.get("version_contradiction") or []


def test_n134_control_a_3x_boot_sector_is_printed_as_3x(tmp_path, monkeypatch):
    texts = _contradiction_in_process(tmp_path, monkeypatch, 3, 15)
    # K29 (wave C step C1, N437): the version form is `ReFS 3.15` -- either form names the boot sector's own version
    assert texts and any(re.search(r"boot sector says (?:v|ReFS )3\.15\b", t) for t in texts), texts


# RED 1.13.2 N134: green with wave B part 2's fix (the strict xfail mark removed)
def test_n134_contradiction_prints_the_boot_sectors_own_major(tmp_path, monkeypatch):
    texts = _contradiction_in_process(tmp_path, monkeypatch, 6, 66)
    _keep(any(re.search(r"declares (?:v|ReFS )6\.66\b", t) for t in texts),
          "the implausibility sentence is right today: %r" % texts)                    # K29: `ReFS 6.66` too
    vi = [t for t in texts if "VOLUME_INFORMATION" in t]
    _keep(vi, "the $VOLUME_INFORMATION contradiction must still be reported: %r" % texts)
    assert not [t for t in texts if re.search(r"(?:v|ReFS )3\.66\b", t)], texts                      # K29 too
    assert any(re.search(r"boot sector says (?:v|ReFS )6\.66\b", t) for t in vi), vi


# RED 1.13.2 N134: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", [("summary", "--json"), ("fastsummary", "--json")],
                         ids=["summary-json", "fastsummary-json"])      # the text modes print no sentence at all
@pytest.mark.parametrize("name", ["win11refsmini_afterchangingversion.raw",
                                  "win11refsmini_afterchangingversion_opened.raw"],
                         ids=["image-afterchangingversion", "image-afterchangingversion_opened"])
def test_n134_version_edited_image_names_v6_66_not_v3_66(name, args):
    img = _corpus(name)
    with open(img, "rb") as fh:
        fh.seek(0x1000000)
        vbr = fh.read(512)
    _fx(vbr[3:7] == b"ReFS" and (vbr[0x28], vbr[0x29]) == (6, 66), "%s: the boot sector is not 6.66" % name)
    rc, out, err = _run_corpus(FOREFST, name, *args)
    _keep(rc == 2 and re.search(r"(?i)VERSION CONTRADICTED|version_contradiction|contradict", out),
          "the contradiction finding (E2 C07) must stay" + _cctx(name, args, rc, out, err))
    assert "v3.66" not in out, [l for l in out.splitlines() if "v3.66" in l]
