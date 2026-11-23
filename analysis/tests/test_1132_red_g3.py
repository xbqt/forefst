"""1.13.2 RED cases for fix group 3 (Journal): the REDs the group still lacked after `test_1132_red_b2_journal.py`
(N131, N132, N148, N195, N196) and the A10 nodes of `test_1132_red_a_verdicts.py`.

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` rows A10 / A10-DOC, section 7 decisions 20 (20.9 = C8 = B, the hole
rule), 24 and 28-31; `fixes/GROUP3_PREP.md` (the lead's settlements, decision 30, the census's stop triggers S1-S4 and
their answers); `fixes/GROUP3_CENSUS.md` (the measured values: sections 2.3 and 3.5); running-log rows N219, N368,
N374. Report, with every node's observed failure: `analysis/reports/v1.13.2/red/RED_group3.md`. Measured on the
current dev tools (forefst cbb888e8, refsanalysis 2ec2ab8c).

What each RED asserts
---------------------
D30   (decision 30) On every volume whose `$J` holds the current journal's records below surviving records of an
      earlier instance (labFafterreboot, labG_0, labG_1, labG_2, win11afterblindaudit, labC2), `usn` (bare =
      `--stats`), `usn --list`, `usn --info`, and on stderr `usn --csv` / `usn --json`, state the boundary: the
      current journal's USN range (0..X) with its creation time (2026-09-20 06:53:53) and the earlier instance's
      range (from Y). Kept: exit 2 (A10), A10's missing-range sentence, the `usn --csv` header and the `usn --json`
      record keys exactly as today. Control: single-instance volumes state no boundary.
D31   (decision 31 = S1 option A) A journal re-creation evident from the bytes is stated neutrally and exits 2 in
      the journal commands (`usn --csv/--info/--stats`, `timeline --csv`, `timestomp --csv`), even when nothing is
      missing: the same-id restart on step6/win11refs8g (found by the USN order; the time printed is the first
      record of the current numbering, 2026-07-05 06:54:51, not the id's 2026-07-03 09:41:22; the id was kept),
      the earlier instance with no surviving record on winsiderv2 (NAMED, not compared) and on labJjournal.
      Controls: labFbeforereboot (one sequence) states nothing and exits 0; winsider (six clock steps in one
      wrapped sequence) is not called a restart and exits 0.
S2    (the lead's settlement) No command joins a file's LastUsn to a USN record today (code reading at cbb888e8:
      the pointer is printed as a number by `files`/`details`, maxed by the tail witness and by timestomp;
      timestomp's corroboration keys on the record's OWN FileRef). The 7 corpus pointers that land on another
      file's record of another instance (labG_1 1, labG_2 2, win11afterblindaudit 4) and the 25 same-id ones on
      win11refs8g are pinned in `details` / `details --json` as GUARDS (they pass today and must keep passing),
      and A10's missing range stays measured against the earlier instance's own last record.
N219  `timestomp`'s journal-coverage header says where the journal starts -- the earliest surviving record the
      cross-check can use, its USN and time (S4) -- and that files changed before it cannot be corroborated; in
      `--csv` mode on stderr (S4). Witness win11refstestmftecmd (first record USN 0 at 2026-05-23 07:38:44, after
      every stomp of the test/ replay); wrapped journals winsider / winsiderv2, whose start is not the id's time.
      T2 (the lead, 2026-10-09): on a wrapped journal the start stated is the LOWEST SURVIVING USN and its time
      (winsider: USN 40,906,752 at 2026-05-11 20:34:50, not the earliest timestamp USN 59,226,288 at 10:37:29), and
      where the journal's times step back the statement says so, with the count (winsider 6, winsiderv2 2: every
      backward step in USN order, own carve) and that times are as the clock recorded them.
      Controls: labBeforeF, a journal that predates the stomped files, keeps its 5 journal-corroborated HIGH rows;
      win11refstestmftecmd and labBeforeF, whose times never step back (own carve), state no step back.
N368  In bundle mode, a page the manifest lists in `source_holes` (every cluster of it) is said to be a hole of the
      source image with the cause left open (C8 = B), not "reads as all zeros on this volume" (bundle of
      win11refs2tmillionsofactions, pages 0x2f668c and 0x2fc300). Guard: a page whose head is stored gets no hole
      sentence. Control: a page that really is zero keeps "reads as all zeros".
N374  A checkpoint copy whose page is an image hole is worded with the hole sentence, not as a zeroed copy and not
      as "the superblock's checkpoint pointer may be corrupt" (plants hole_lo / hole_hi of the G2c2 critic K-5).
      Control: zero_lo / zero_hi (the same range written as zeros) are not called holes.
      T1 (the lead, 2026-10-09): a checkpoint copy that cannot be read (an image hole, or all zeros: no signature, no
      clock) exits 2 in EVERY command of both tools. forefst's forms, ra `supb --verify` and ra `containers` exit 2
      today on all four plants (kept: `_keep` in the REDs, plain asserts in the zero-plant control); ra `supb`,
      `supb -v`, `chkp`, `chkp -v`, `chkp --verify` exit 0 (REDs, on the hole AND the zero plants, with the copy then
      named by C8 = B's hole sentence for a hole and "all zeros" for zeros); and no clock is read from zeros (ra
      `supb`, `supb -v`, `supb --verify` print "vc=0 ac=0" for the copy: REDs). Control: the unplanted base volume
      exits 0 in every one of those forms and prints both copies' real clocks (vc=64 / vc=63).
      T1a (the lead, 2026-10-09): NO field at all is decoded from a copy that has no CHKP signature (not the clocks,
      not `supb -v`'s ver=0.0, not sig / self_block, nothing), and the copy is reported as unreadable (C8 = B's hole
      sentence / "all zeros"), in ra `supb`, `supb -v`, `supb -vv`, `chkp`, `chkp -v`, `chkp -vv` (REDs on all
      four plants; `chkp` decodes only the copy in use and never names the other: kept). Control: on the base those
      forms decode the real fields (each copy's clock, version 3.14; `chkp` the newest copy, clock 64).
      T1b (the lead, 2026-10-09): "every command" is pinned on decision 28's representative surface: forefst
      `files`, `search`, `timeline`, `deleted`, `summary`, `fastsummary`, `integrity`; ra `files`, `summary`, `supb`,
      `supb -v`, `supb -vv`, `supb --verify`, `chkp`, `chkp -v`, `chkp -vv`, `chkp --verify`, `containers`. ra
      `supb -vv` / `chkp -vv` exit 0 today (REDs, added to T1's exit RED); forefst `search` / `timeline` / `deleted`
      and ra `files` / `summary` exit 2 today (controls); the base exits 0 in every one of the 18 forms.
A10-DOC part 2  A PROOF node (not a RED): `analysis/tools/analysis_scripts/a10doc_usn_tail_proof.py` (stdlib, raw
      reads, no tool import) reproduces the LAB-F tail values on labBeforeF, labFbeforereboot, labFafterreboot.
      T3 (the lead, 2026-10-09): the highest per-file pointer is recorded with its scope -- the LIVE TREE's (the pages
      reachable from the checkpoint copy in use; labFbeforereboot 4,084,440, the value the claim cites) and the page
      copies OUTSIDE it (labFbeforereboot: 56 rows on 28 page copies, up to 4,462,624) -- and the script prints
      both, labelled. ST-2 (the lead, 2026-10-09): on labFbeforereboot those 28 copies were written after the
      checkpoint in use and are not yet part of its tree (none of their names is in it; their Changed times are later
      than its latest); on labFafterreboot the same copies are superseded (the replayed live tree holds their names).
      The script measures and prints which; USN wrap (reading 1): the script shows that no wrap occurred.
T4    (the lead, 2026-10-09) decision 30's boundary is stated in every `usn` form: bare / `--stats`, `--list`,
      `--info`, and on stderr for `--csv` / `--json` -- the 30 D30 nodes stand as written.
N386  Every corpus image is addressed by its step path (`_img`); no image is looked up by its bare name (the base
      of the plants is step1/win11refsmini.raw, battery base A of P0.1 golden.json; labJjournal's premise is read
      here from step7/labJjournal.raw, not through BJ's name lookup).

Tightened to the critic (`red/RED_group3_critic.md` section 5, settled in GROUP3_PREP.md, 2026-10-09)
------------------------------------------------------------------------------------------------------
R1a   N374 wording RED: a hole plant's copy is never called "all zeros" (a passage at its lines); `_n374_stated` too.
R1b   `_n374_stated` (the exit and T1a REDs): a zero plant's copy gets no hole word -- no generic "all zeros / may be
      a hole" sentence on either plant.
R2    S2 guards: `details` never prints the other record's name, FileRef, time (to the second) or reason. S4:
      labJjournal's m2_after_recreate_same.txt (LastUsn 256, the first id) joins them: it lands on m5's record.
R3    D31 naming (winsiderv2, labJjournal, the lineage): the old id is named AS an earlier instance (an earlier-
      instance phrase in the sentence that names it); listed beside "the current journal" is not enough.
R4    winsider (clock steps, one sequence): no restart / boundary statement in `timestomp` (text and --csv) either.
S1    D30 `usn --list`: the per-record lines are dropped before the boundary is looked for (labels do not suffice).
S2    the missing-range guard refuses a range measured from the current journal's end (an end phrase on X with the
      pointer, a range form X .. pointer, the byte count pointer - X), not any pairing of X with the pointer, so a
      correct boundary sentence followed by the tail sentence passes, its two halves joined by a comma or a semicolon.
N368  also never "[FAIL] ... Invalid signature" on a line naming a source-image hole page (C8 = B in every command).
ST-1  (the lead) on the restart volumes (win11refs8g; the labF/labG lineage) timestomp states coverage PER SEQUENCE:
      the current numbering from USN 0 and its time, the earlier sequence's surviving records with their USN and
      time span; the time between is not claimed as covered; never "files changed before <the current numbering's
      start> cannot be corroborated" where earlier records survive. Control: one-sequence volumes state one span.

Last critic items (`red/RED_group3_critic.md` section 5 S3/S5/S6/S7, R4's other forms, N196; settled in GROUP3_PREP.md)
---------------------------------------------------------------------------------------------------------------------
S3    N368: the RED requires the word "source" (the SOURCE image; C8 = B's sentence always says "image"); the guard
      keeps that each checkpoint copy is still named (a guard that reads no line naming it guards nothing).
S5    D31 on labJjournal: decision 31's sentence -- the numbering restarted at USN 0 at its first record's time
      (2026-09-27 08:12:42, m5's FILE_CREATE; the new id 08:12:42.572 shares that second, so "USN 0" binds the time
      to the record), a NEW id (never "the id was kept"), earlier records (here m1-m3's pointers) belonging to an
      earlier sequence; never the first id's 08:12:40 as the restart time. Control: D31's labFbeforereboot control.
S6    N374 zero plants: the copy is "all zeros" with NO cause -- never "the superblock's checkpoint pointer may be
      corrupt" or a rewording of it -- in every form that prints the copy (14: all but the four `chkp` forms), and no
      hole word (R1b); the hole plants keep the hole sentence, also in forefst search / timeline / deleted and ra files
      / summary (the five forms the wording RED did not run). Control: the intact base names no zeros, cause or hole.
S7    D31 on win11refs8g: the same-id restart is stated in every `usn` form (T4): also bare `usn`, `usn --list`
      (record blocks dropped, S1) and on `usn --json`'s stderr. Control: D30's single-instance control (same forms).
R4    winsider's clock steps are never a restart or a boundary in bare `usn`, `usn --list`, `usn --json` (stderr) and
      `timeline` either -- GUARDS (today's statement lines carry none; record names such as RestartAgent.exe are the
      records' own and are classified out by format; a `--list` head line must carry its record's own name, from the
      bytes, and nothing else).
N196  strict naming in this file (b2_journal's N196 RED keeps its weaker matcher): on labJjournal and winsiderv2,
      `usn --info`, `timeline --csv`, `timestomp`, the earlier id is named AS an earlier instance. Control:
      labFbeforereboot names no id, its own included, as an earlier instance.
USN 0 `_start_stated` (N219, ST-1) accepted "USN 0" only before a space or a bracket: "starts at USN 0, 2026-05-23
      07:38:44" and "... at USN 0." were refused (measured 2026-10-09). `_USN0` accepts a comma or full stop that ends
      the clause and still refuses "USN 0.5" / "USN 01".
MERGE `_sentences` joins a line without a full stop to the next. stderr's note "... still holding prior cluster
      contents" (win11refs8g, labJjournal, win11refstestmftecmd) then reads "prior cluster contents Journal ...":
      `_EARLIER_INSTANCE` (R3) accepted the critic's Y7 listing on labJjournal `usn --csv`, and `_EARLIER_SEQ` would
      have found an "earlier sequence" in any restart sentence there (both measured on a patched copy). Both now need
      the noun in lower case, `_EARLIER_SEQ` with at most two words between. S5 pairs a restart word with the time
      printed NEAREST to it (`_restart_times`): bare `usn` prints "Time range: 2026-09-27 08:12:42", the first record's
      second, into the same merged sentence.

The fixer's first step (`red/RED_group3_recheck.md`, settled in GROUP3_PREP.md "The narrow re-check", 2026-10-09)
-------------------------------------------------------------------------------------------------------------
R-A   winsider (one wrapped sequence, clock steps): no `_EARLIER_SEQ` phrase either ("records of an earlier sequence",
      ST-1's own words) -- in the N219 wrapped RED, the D31 winsider control and the R4 guards.
R-B   a copy of WRITTEN zeros gets none of the tool's own hole labels ("absent from the image (acquisition gap, not
      damage)", "not captured"): `_HOLE_WORDS`, in `_n374_contra` (the exit, T1a and S6 zero REDs) and the zero control.
Q1    `_named_as_earlier` binds the earlier-instance phrase to the id named nearest to it, and refuses the current id
      named as the earlier instance (inverted labels); Q2: the naming may continue into a next sentence that refers
      back to the id and names no other.
Q3    win11refs8g (D31, S7): the earlier-sequence clause on the CURRENT numbering's range is refused.
Q4/S5 S5 relaxed (a sanctioned oracle change): on labJjournal, where no earlier record survives in $J, the restart
      statement plus the earlier instance named anywhere in the statement output suffices. Q5: no USN above the last
      record (31,576) is named as surviving.
Q6    S2 guards: the other record's reason as a decimal int after a reason key, and its FileRef as `home_oid`/`file_id`
      ints (the tool's own `usn --json` style).
Q7    the missing-range guard: an end word on X with the pointer within the next TWO sentences.
Q8    ST-1: an open-ended coverage claim from the earlier sequence's first time is refused.
Q9    N368: a source-image hole page is never called "all zeros" on its line (`_ALL_ZEROS`, as the re-check names it).
Q10   R1a / S6 hole: "zero-filled", "zeroed", "only zero bytes" are zeros too (`_ZEROS_SAID`; not a bare "zero").
Q11   S6 zero: a removal cause (overwritten, wiped, destroyed, tampered) is a cause the bytes do not show.

The completion step (G3_CONTEXT "After the fixer stage -- the lead's settlements", 2026-10-09)
---------------------------------------------------------------------------------------------
N368c N368's counts: a count of pages is a count of DISTINCT pages and each command states what it counted ("N
      distinct page(s) that this command read are wholly in the source image's holes"; `integrity`: "N of the M pages
      the volume references"); a page met by two walks counts once, in the damage summary, `files`' written-file lines
      and the escalation text too. millionsofactions bundle and image: summary 14 (20 notes), files 6, integrity 14 of
      809, the image's number equal to the bundle's. Bundle mode: the checkpoint root-check hole sentence names the
      source image; the class search adds the unreadable-copy text for a page partly in the rehydrated image's holes
      (the bundle does not carry it) and a page only partly listed in `source_holes` (not a source-image hole as a
      whole). Controls: distinct pages each count; a page met once; the root check outside bundle mode.

G3b -- review round 1 (G3_CONTEXT "Review round 1 ... the lead's settlements, taken in G3b", 2026-10-10)
-------------------------------------------------------------------------------------------------------
F1    `timeline --csv` / `--json` / `--jsonl` written to stdout carry the export only; every statement goes to stderr
      (as `usn`, T4, and `timestomp`, S4): `--json` and `--fast --json` parse as one JSON array of event objects,
      `--fast --jsonl` is one event object per line, `--csv` starts with its header and every row is a timeline row,
      on labJjournal, win11refs8g, winsiderv2 and the five A10 volumes; their journal statements ("Journal instances:",
      and A10's "Journal tail:") are on stderr; exit 2 kept. Streamed (`_json_array_check`): nothing of a 130 MB export
      is held. Control: labFbeforereboot (no journal statement) exports cleanly, exit 0.
F2    `verify-bundle` reads its rehydrated copy with the bundle's context: on the millionsofactions bundle the pages the
      manifest lists whole in `source_holes` get the source-image hole sentence, never "reads as all zeros on this
      volume"; on a hole_lo bundle the checkpoint copy gets it too, never zeros. Control: the zero_lo bundle's copy is
      "all zeros", no hole word.
N9    `summary --json`'s `usn_journal_id` is the current journal's id (0x01dd48cccc6edb06 on the labF / labG lineage,
      not the earlier 0x01dd485de7522417), an integer as today (wave E converts types); with the current id not known
      (`_current_journal_id` patched to None in a runner) the key presents no file's id as the journal's and
      `UsnJournalIds` lists every id with its count, none marked current. Controls: labJjournal and labBeforeF, where
      the most common file id is the current journal's.
latent (decision 34) `_usn_hole_text` on a wrapped ring (in-process, a 256 KiB synthetic `$J`): a hole past the ring's
      wrap is placed at its own USN (794,624), not below the surviving records' end, and the stored bytes before it are
      counted; a missing range longer than the ring states its hole bytes. Controls: a hole before the wrap point, and
      an unwrapped journal (the corpus shape). `timeline`'s NOTE over a `$J` of non-zero bytes that hold no record (the
      per-file witness not read) says nothing about files pointing into it (BJ's harness). Control: N131's all-zero
      shape keeps "holds no records and no file points into it", exit 0.
supb-verify  refsanalysis `supb --verify` on the four N374 plants: the signature row takes the verdict of the copy's own
      row (WARN for a hole, FAIL for zeros), says the copy could not be read, never '??'. Control: the intact base's row
      is "OK  #1=CHKP, #2=CHKP".

Volumes
-------
* Read-only corpus images, addressed by their step path (two `win11refs8g.raw` exist, in step2 and step6; two
  `win11refsmini.raw`, in step1 and step5). ``blindaudit2.raw`` is refused by name. Skipped when the image is absent.
* Scratch (``$FOREFST_RED_SCRATCH``): hole-preserving copies of win11refsmini (N374 plants, the N368 control) and
  `export metadata --what vbr,chkp,supb,btree` bundles (about 13 MB for millionsofactions), deleted by exact path.
* ``pytest -k "not image"`` runs the image-free nodes only (the matcher self-test).

Discipline (as in test_1132_red_group2b.py): ``@_red`` = ``xfail(strict=True, raises=AssertionError)``; only a plain
``assert`` states the defect; ``_fx`` for a fixture or premise that is not what the case needs, ``_keep`` for a
property the current tool already has; every RED has a control that passes now. Premises are read from the bytes
by this module's own readers (USN_RECORD_V3 carve, directory rows at pinned offsets, SEEK_DATA), never from a report.
Large outputs are streamed: only prose lines are kept, CSV data rows are counted.
"""
import calendar
import csv
import io
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import test_1132_red_a_bootstrap as AB                    # noqa: E402  (exceptions, carve, Vol, plants' geometry)
import test_1132_red_a_verdicts as AV                     # noqa: E402  (the A10 matchers: one hole rule, one reading)
import test_1132_red_b2_journal as BJ                     # noqa: E402  (own USN/row readers, _carve_except)
from conftest import jget, jint                           # noqa: E402  (K21 readers)

FOREFST, REFSANALYSIS, SCRATCH = AB.FOREFST, AB.REFSANALYSIS, AB.SCRATCH
RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, AB._red
_sentences, _HOLE, _HOLE_CAUSE, _BOUNDARY, _JOURNAL = (AV._sentences, AV._HOLE, AV._HOLE_CAUSE, AV._BOUNDARY,
                                                        AV._JOURNAL)
TIMEOUT = 1800
CS = 4096
EPOCH = 116444736000000000

_WS = os.path.dirname(REPO) if os.path.basename(REPO) == "forefstdev" else REPO
PROOF_SCRIPT = os.path.join(_WS, "analysis", "tools", "analysis_scripts", "a10doc_usn_tail_proof.py")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# images, runs, readers
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _disks():
    """The corpus root (analysis/rawdisk/disks): the first such directory walking up from the working directory, then
    from REPO -- the search `_corpus_image` makes, but no image is looked up by its bare name (N386: two
    `win11refs8g.raw` and two `win11refsmini.raw` exist). None in a clone."""
    for start in (os.getcwd(), REPO):
        d = os.path.abspath(start)
        while True:
            root = os.path.join(d, "analysis", "rawdisk", "disks")
            if os.path.isdir(root):
                return root
            if os.path.dirname(d) == d:
                break
            d = os.path.dirname(d)
    return None


def _img(rel):
    """A corpus image by its step path ("step6/win11refs8g.raw"); skip when absent. blindaudit2 is refused."""
    if "blindaudit2" in rel:
        raise RedFixtureError("blindaudit2.raw is excluded from every run")
    root = _disks()
    p = os.path.join(root, rel) if root else None
    if not p or not os.path.isfile(p):
        pytest.skip("%s not in this tree (a clone ships no images)" % rel)
    return p


# The plants' base (AB.BASE_IMAGE names it by its bare name): battery base A of P0.1 golden.json, by its step path.
# step5/win11refsmini.raw holds the same bytes (same 172 stored ranges, same SHA-256 of them; measured 2026-10-09).
BASE = "step1/win11refsmini.raw"


class _R:
    def __init__(self, rc, out, err, prose, header, header_line, nrows):
        self.rc, self.out, self.err, self.prose = rc, out, err, prose
        self.header, self.header_line, self.nrows = header, header_line, nrows

    def ctx(self, what):
        tail = "\n".join(self.prose[-60:])
        return "\n[%s] rc=%d, %d data row(s), header %r\n--- prose (tail) ---\n%s" % (
            what, self.rc, self.nrows, self.header_line, tail[-5000:])


def _exec(path, args, tool=FOREFST, cwd=None, keep_out=False):
    """Run the tool, stream stdout: CSV data rows (AV._split's rule) are counted, every other line is prose. stderr
    is appended to the prose. A traceback or a timeout is a fixture error, never the defect."""
    cmd = [sys.executable, "-B", tool, path] + list(args)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd or REPO)
    errbuf = []
    t = threading.Thread(target=lambda: errbuf.append(p.stderr.read()))
    t.start()
    timer = threading.Timer(TIMEOUT, p.kill)
    timer.start()
    prose, header, header_line, ok, nrows, keep = [], None, None, None, 0, []
    try:
        for raw in p.stdout:
            ln = raw.decode("utf-8", "replace").rstrip("\r\n")
            if keep_out:
                keep.append(ln)
            if header is None:
                for h, check in AV._CSV_TABLES:
                    if ln.startswith(h):
                        header, header_line, ok = next(csv.reader([ln])), ln, check
                        break
                if header is not None:
                    continue
            else:
                try:
                    fields = next(csv.reader([ln]))
                except (csv.Error, StopIteration):
                    fields = None
                if fields and len(fields) == len(header) and ok(fields):
                    nrows += 1
                    continue
            prose.append(ln)
        p.wait()
    finally:
        timer.cancel()
        t.join()
    err = (errbuf[0] if errbuf else b"").decode("utf-8", "replace")
    if p.returncode < 0:
        raise RedFixtureError("timeout or kill (%d): %s" % (p.returncode, " ".join(cmd)))
    if "Traceback (most recent call last)" in err:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + err[-3000:])
    return _R(p.returncode, "\n".join(keep) if keep_out else None, err, prose + err.splitlines(), header,
              header_line, nrows)


_RUNS = {}


def _run(rel, *args, tool=FOREFST, keep_out=False):
    key = (tool, rel, args, keep_out)
    if key not in _RUNS:
        _RUNS[key] = _exec(_img(rel), args, tool=tool, keep_out=keep_out)
    return _RUNS[key]


def _ft(iso):
    """'2026-09-20T06:53:53.132826Z' -> FILETIME (the pinned times are written as the census prints them)."""
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\.(\d{6})Z$", iso)
    y, mo, d, h, mi, s, us = (int(x) for x in m.groups())
    return EPOCH + (calendar.timegm((y, mo, d, h, mi, s)) * 10 ** 6 + us) * 10


def _at(ts, iso):
    """A FILETIME (100 ns) equals a time printed to the microsecond."""
    return _ft(iso) <= ts < _ft(iso) + 10


_STDERR_FORMS = {("usn", "--csv"), ("usn", "--json"), ("timestomp", "--csv")}


def _where(args, r):
    """Where a statement belongs: stderr when stdout carries an export (decision 30's `usn --csv`/`--json`, S4's
    `timestomp --csv`), else the prose (stdout lines that are not data rows, then stderr). `timeline --csv` prints its
    journal statements on stderr since G3b (F1, the lead's settlement); its prose holds them wherever they are printed,
    and the G3b F1 nodes pin that stdout carries the export only."""
    return r.err.splitlines() if tuple(args) in _STDERR_FORMS else r.prose


def _rec_at(buf, o):
    """A USN_RECORD_V3 at buf[o] (own reader; an empty name is allowed: 199 records of labFbeforereboot have one):
    (len, usn, ts, reason, (file_oid, file_idx), name) or None."""
    if o + 0x50 > len(buf):
        return None
    rl, maj, mn = struct.unpack_from("<IHH", buf, o)
    if maj != 3 or mn != 0 or rl % 8 or not (0x50 <= rl <= 0x1000) or o + rl > len(buf):
        return None
    nl, no = struct.unpack_from("<HH", buf, o + 0x48)
    if no != 0x4C or nl % 2 or no + nl > rl:
        return None
    usn, ts, reason = struct.unpack_from("<qQI", buf, o + 0x28)
    fidx, foid = struct.unpack_from("<QQ", buf, o + 0x08)
    return rl, usn, ts, reason, (foid, fidx), buf[o + no:o + no + nl].decode("utf-16-le", "replace")


def _carve(buf, alloc=None):
    """Records whose USN is their offset in the $J buffer (modulo the allocation when it wrapped), USN order."""
    out, o = [], 0
    while o + 0x50 <= len(buf):
        r = _rec_at(buf, o)
        if r and r[1] >= 0 and (r[1] % alloc if alloc else r[1]) == o:
            out.append(r)
            o += r[0]
            continue
        o += 8
    return sorted(out, key=lambda r: r[1])


def _read_j(path, ps, extents, nbytes=None):
    """$J bytes from pinned extents [(plcn, clusters, file_vcn)] (each premise re-checks them by its carve)."""
    alloc = max(v + n for _p, n, v in extents) * CS
    buf = bytearray(alloc if nbytes is None else nbytes)
    with open(path, "rb") as fh:
        for pl, n, v in extents:
            lo = v * CS
            if lo >= len(buf):
                continue
            fh.seek(ps + pl * CS)
            d = fh.read(min(n * CS, len(buf) - lo))
            buf[lo:lo + len(d)] = d
    return bytes(buf), alloc


def _steps(recs):
    """Every backward time step of more than 1 s in USN order: (USN of the record above, clean split?) -- clean =
    every record from the step up is older than every record below it (the census's restart test)."""
    n = len(recs)
    pmin, m = [], None
    for r in recs:
        m = r[2] if m is None else min(m, r[2])
        pmin.append(m)
    smax, m = [0] * n, None
    for i in range(n - 1, -1, -1):
        m = recs[i][2] if m is None else max(m, recs[i][2])
        smax[i] = m
    return [(recs[i + 1][1], smax[i + 1] < pmin[i]) for i in range(n - 1) if recs[i + 1][2] < recs[i][2] - 10 ** 7]


def _row_at(path, off, name):
    """(LastUsn, UsnJournalId) of the type-0x30 row of `name` at a pinned image offset (BJ._dir_row, own reader)."""
    with open(path, "rb") as fh:
        fh.seek(off)
        r = BJ._dir_row(fh.read(0x800), 0, name)
    _fx(r is not None and r[1] is not None, "no type-0x30 row of %r with a LastUsn at 0x%x" % (name, off))
    return r[1], r[2]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# matchers (each exercised by test_g3_matchers_accept_corrected_wording_and_reject_todays_lines)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _num(*ns):
    alts = []
    for n in ns:
        alts += ["%d" % n, "0x%x" % n]
    return re.compile(r"(?i)(?<![0-9A-Za-z])(?:%s)(?![0-9A-Za-z])" % "|".join(alts))


_EARLIER = re.compile(r"(?i)\b(?:earlier|previous|older|prior|former)\b")
_RESTART = re.compile(r"(?i)\brestart\w*|\bre-?creat\w*|\bstart(?:ed|s)? (?:again|over)\b|\bbegan again\b|"
                      r"\bnumbering\b[^.;]{0,60}\b(?:began|begins|starts?|started|reset)\b")
_ID_KEPT = re.compile(r"(?i)\b(?:same|kept|unchanged|retained)\b[^.;]{0,40}\bid\b|"
                      r"\bid\b[^.;]{0,40}\b(?:kept|unchanged|retained|the same|did not change|was not changed|stayed)\b")
# An earlier word qualifying the noun (at most two words between; the noun in LOWER case). Tightened 2026-10-09: on
# win11refs8g and labJjournal stderr's note ends "... still holding prior cluster contents" and `_sentences` merges it
# into the statement line that follows ("prior cluster contents Journal instances: ..."), which the earlier
# `earlier-word [^.;]{0,40} noun` rule read as "earlier records belong to an earlier sequence" (measured on a patched copy).
_EARLIER_SEQ = re.compile(r"(?i)\b(?:earlier|previous|older|prior|former)\b,?\s+(?:(?!than\b)[\w$'-]+,?\s+){0,2}?"
                          r"(?-i:sequences?|numbering|instances?|epochs?|records?|journals?)\b")
_WIPED = re.compile(r"(?i)\bwip(?:e|ed|ing)\b|\bdestroy\w*")
_START = re.compile(r"(?i)\bstart\w*|\bbegin\w*|\bbegan\b|\bfirst (?:surviving )?record\b|\bearliest\b|\boldest\b|"
                    r"\bfrom USN\b|\bcover\w*")
_BEFORE = re.compile(r"(?i)\bbefore\b|\bearlier than\b|\bprior to\b|\bpredat\w*")
_UNCOVERED = re.compile(r"(?i)\b(?:cannot|can ?not|can't|could not|not|no)\b[^.;]{0,60}"
                        r"\b(?:corroborat\w*|cross-check\w*|covered|checked|confirm\w*|verif\w*)\b|"
                        r"\boutside\b[^.;]{0,30}\bcoverage\b|\buncorroborat\w*")
_POINTER_BLAME = re.compile(r"(?i)pointer may be corrupt")
# S3 (the lead): the SOURCE image -- C8 = B's sentence always says "image", so "image" proves nothing; the manifest key
# `source_holes` alone is not the word (\b does not split "source_holes")
_SOURCE = re.compile(r"(?i)\bsource\b")
# USN 0 as a whole number: not "USN 0.5" or "USN 01"; a comma or full stop that ends the clause is allowed (the earlier
# `0(?![0-9A-Za-z,.])` refused "starts at USN 0, 2026-05-23 07:38:44" and "... at USN 0.", measured 2026-10-09)
_USN0 = re.compile(r"(?i)\bUSN\s*#?\s*0(?![0-9A-Za-z]|[.,][0-9])")
# S6 (the lead): a cause the bytes do not show -- the superblock's (checkpoint) pointer blamed, in any wording ("pointer
# may be corrupt", "the pointer to it may be wrong", "a bad pointer"); a negated one ("the pointer is not corrupt") is no
# blame. "BAD (no CHKP signature)" names no pointer.
_POINTER_CAUSE = re.compile(r"(?i)\bpointers?\b[^.;]{0,60}?\b(?:corrupt\w*|wrong|bad|invalid|damaged|stale|incorrect|"
                            r"broken|bogus)\b|\b(?:corrupt\w*|wrong|bad|invalid|damaged|stale|incorrect|broken|bogus)\b"
                            r"[^.;]{0,30}?\bpointers?\b")
_NEGATED = re.compile(r"(?i)\b(?:not|never|no)\b")
# S5: decision 31's "(a new id)" on a volume whose id changed, and the same-id wording that must not be printed there
_ID_NEW = re.compile(r"(?i)\bnew\b[^.;]{0,20}\bid\b|\bdifferent\b[^.;]{0,20}\bid\b|"
                     r"\bid\b[^.;]{0,40}\b(?:changed|differs|is new|was replaced)\b|\bnew journal\b")
_ID_KEPT_CLAIM = re.compile(r"(?i)\b(?:journal )?id (?:was|is|stayed|remained) (?:kept|unchanged|retained|the same)\b|"
                            r"\bsame (?:journal )?id\b|\bkept (?:its|the) (?:journal )?id\b")
# T2: "its times step back N times; times are as the clock recorded them"
_STEP_BACK = re.compile(r"(?i)\bstep(?:s|ped|ping)?\s+back(?:wards?)?\b|"
                        r"\b(?:go(?:es)?|went|jump(?:s|ed)?|move(?:s|d)?|run(?:s)?|ran)\s+back(?:wards?)?\b|"
                        r"\bbackwards?\s+(?:steps?|jumps?)\b|\bclock\s+(?:steps?|jumps?)\b")
# R3: an earlier-instance phrase -- an earlier word that qualifies "instance" / "journal" (at most two words between,
# never "than": "files older than the current journal" does not call an id an earlier instance)
# The noun is matched in LOWER case (2026-10-09, measured on a patched copy): `_sentences` merges a line without a full
# stop into the next, so stderr's "... still holding prior cluster contents" followed by "  Journal ids carried by
# files: 0x01dd4e57f72ac89e (3 files)" read as "prior cluster contents Journal" -- the critic's Y7 accepted on
# labJjournal `usn --csv`. A capitalised "Journal" starts another line's statement; "an earlier USN journal" still counts.
_EARLIER_INSTANCE = re.compile(r"(?i)\b(?:earlier|previous|older|prior|former|discarded|replaced),?\s+"
                               r"(?:(?!than\b)[\w$'-]+,?\s+){0,2}?(?-i:instance|journal)s?\b")
# S1: one record of `usn --list` (fd cmd_usn: "  USN %-10d %s", then the indented field lines)
_LIST_HEAD = re.compile(r"^  USN \d+\s")
_LIST_FIELD = re.compile(r"^    (?:Time|Reason|FileRef|Parent|Attrs|Source|SecID|RecLen):")
# N368: a verdict that the page FAILED (integrity's "[FAIL] LCN 0x..: Invalid signature: b'\x00\x00\x00\x00'")
_FAIL_SIG = re.compile(r"\[FAIL\]|(?i:\binvalid signature\b)")
# R2: the USN reason flags by name (own table: the USN_REASON_* names of the Windows SDK, as a join would print them)
_USN_REASON_NAMES = {
    0x1: "DATA_OVERWRITE", 0x2: "DATA_EXTEND", 0x4: "DATA_TRUNCATION", 0x10: "NAMED_DATA_OVERWRITE",
    0x20: "NAMED_DATA_EXTEND", 0x40: "NAMED_DATA_TRUNCATION", 0x100: "FILE_CREATE", 0x200: "FILE_DELETE",
    0x400: "EA_CHANGE", 0x800: "SECURITY_CHANGE", 0x1000: "RENAME_OLD_NAME", 0x2000: "RENAME_NEW_NAME",
    0x4000: "INDEXABLE_CHANGE", 0x8000: "BASIC_INFO_CHANGE", 0x10000: "HARD_LINK_CHANGE",
    0x20000: "COMPRESSION_CHANGE", 0x40000: "ENCRYPTION_CHANGE", 0x80000: "OBJECT_ID_CHANGE",
    0x100000: "REPARSE_POINT_CHANGE", 0x200000: "STREAM_CHANGE", 0x400000: "TRANSACTED_CHANGE",
    0x800000: "INTEGRITY_CHANGE", 0x80000000: "CLOSE"}
_CLOCK = re.compile(r"(?i)\bclock\b")
_COUNT_WORDS = {2: "two", 6: "six"}
# ── the fixer's first step (G3_CONTEXT, `red/RED_group3_recheck.md`), 2026-10-09 ──
# R-B: the tool's own hole vocabulary -- a hole word, or the labels forefst gives image holes ("absent from the image
# (acquisition gap, not damage)", "not captured"): never for a copy of WRITTEN zeros (N132: zeros outside a hole are
# never an acquisition gap)
_HOLE_WORDS = re.compile(r"(?i)\bholes?\b|\bsparse\b|\bacquisition[- ]gap\b|\babsent[- ]from[- ](?:this |the )?image\b|"
                         r"\bnot[- ]captured\b")
# Q10 (R1a, S6 hole): zeros said of a hole in any wording -- never a bare "zero": C8 = B's sentence itself
# says "zero on the disk"
_ZEROS_SAID = re.compile(r"(?i)\ball[ -]zero(?:s|ed)?\b|\bzero-filled\b|\bzeroed\b|\bonly zero bytes\b")
# Q11 (S6): a removal cause the bytes do not show (AV._REMOVAL-like), unless negated just before it
_REMOVAL_CAUSE = re.compile(r"(?i)\boverwrit\w*|\bwip(?:e|ed|ing)\b|\bdestroy\w*|\btamper\w*")
_NEGATED_BEFORE = re.compile(r"(?i)\b(?:not|never|no)\b\W*(?:\w+\W+){0,2}$")
# Q2: a sentence that refers back to the id the previous sentence named last ("It is the id of an earlier instance")
_BACKREF = re.compile(r"(?i)^\W*(?:it|this|that|its|which|the (?:id|journal id|journal|instance))\b")
# Q5: a survive word, and the same negated ("whose records no longer survive", "none of its records survive")
_SURVIVE = re.compile(r"(?i)\bsurviv\w*")
_NOT_SURVIVE = re.compile(r"(?i)\b(?:no longer|not|none of|never|no)\b[^.;]{0,30}?\bsurviv")
# Q8: a coverage word
_COVER_WORD = re.compile(r"(?i)\bcover\w*")
# Q3: a clause boundary inside a sentence (a comma, a colon, "and", "while", "but")
_CLAUSE_SPLIT = re.compile(r"(?i),|:|\band\b|\bwhile\b|\bbut\b")
# T1: a clock value printed for a checkpoint copy ("vc=0 ac=0", "vclock=0", "Virtual clock ... 0")
_CLOCK_VALUE = r"(?i)\b(?:vc|ac|v?clock|virtual clock|allocator clock)\b\s*[=:]?\s*%d(?![0-9a-z.])"
_ZERO_CLOCK = re.compile(_CLOCK_VALUE % 0)
_ALL_ZEROS = re.compile(r"(?i)\ball[ -]zero(?:s|ed)?\b")
# T1a: a value decoded from a checkpoint copy's bytes, in the layouts ra supb / chkp print: `key=value` (supb: sig=....,
# sig=b'\x00\x00\x00\x00', vc=0, ac=0, ver=0.0, self_block=0x0) or a field row / key-value line (chkp: "Virtual clock
# 0x10 ... 63", "Version echo  3.14"). A value is bytes, dots (the signature's non-printables), hex or a number --
# never a word ("sig=none", "no CHKP signature: all zeros" are statements, not decoded values).
_FIELD_VALUE = re.compile(
    r"(?i)(?<![0-9a-z_])(?:sig|vc|ac|ver|self_block)\s*=\s*(?:b'[^']*'|\.{4}(?!\.)|0x[0-9a-f]+|[0-9]+(?:\.[0-9]+)?)"
    r"(?![0-9a-z])|\b(?:signature|virtual clock(?: \(body\))?|allocator clock|version(?: echo)?|self-block lcn)"
    r"\s*[=:]?\s+(?:0x[0-9a-f]+|[0-9]+(?:\.[0-9]+)?)(?![0-9a-z])")


def _windows(sentences, k=3):
    return [" ".join(sentences[i:i + k]) for i in range(len(sentences))]


def _boundary_stated(sentences, xs, ys, when):
    """Decision 30: one passage (up to 3 consecutive sentences) names the current journal's last USN or its end (x),
    the earlier instance's first USN (y), the current journal's creation time (`when`, to the second), an instance /
    current-journal word and an 'earlier' word."""
    rx, ry, rt = _num(*xs), _num(*ys), re.compile(when)
    return [w for w in _windows(sentences) if rx.search(w) and ry.search(w) and rt.search(w)
            and _BOUNDARY.search(w) and _EARLIER.search(w)]


def _restart_windows(sentences, when):
    """Decision 31: passages with a re-creation / restart word and the time of the current numbering's first record."""
    rt = re.compile(when)
    return [w for w in _windows(sentences) if _RESTART.search(w) and rt.search(w)]


_TIME = re.compile(r"\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d")


def _restart_times(sentences):
    """S5: (passage, time) for each restart / re-creation word in a passage (up to 3 sentences) and the time printed
    NEAREST to it -- the time it is stated at. `_sentences` merges lines without a full stop, so on labJjournal bare
    `usn` / `--stats` ('Time range: 2026-09-27 08:12:42 UTC to ...') and `usn --info` ('Created: 2026-09-27 08:12:42')
    put the first record's second into the sentence a statement starts; a wrong restart time printed after it would pass
    `_restart_windows` (any time in the passage)."""
    out = []
    for w in _windows(sentences):
        times = [(m.start(), m.end(), m.group(0)) for m in _TIME.finditer(w)]
        if not times:
            continue
        for m in _RESTART.finditer(w):
            dist = [(a - m.end() if a >= m.end() else m.start() - b if b <= m.start() else 0, t) for a, b, t in times]
            out.append((w, min(dist)[1]))
    return out


def _start_stated(sentences, pairs):
    """N219 / S4: a passage (up to 2 sentences) with a journal word, a start word, a USN and that record's own time,
    for one of the accepted (usn, time-regex) pairs."""
    out = []
    for w in _windows(sentences, 2):
        if not (_JOURNAL.search(w) and _START.search(w)):
            continue
        for usn, when in pairs:
            rn = _USN0 if usn == 0 else _num(usn)
            if rn.search(w) and re.search(when, w):
                out.append(w)
                break
    return out


def _steps_back_stated(sentences, n):
    """T2: a passage (up to 2 sentences) says the journal's times step back, n times (digits or the word), and that
    times are as the clock recorded them (a clock word)."""
    rn = re.compile(r"(?i)(?<![0-9])(?:%d|%s)(?![0-9])" % (n, _COUNT_WORDS.get(n, "%d" % n)))
    return [w for w in _windows(sentences, 2) if _STEP_BACK.search(w) and rn.search(w) and _CLOCK.search(w)]


def _before_uncovered(sentences):
    """N219: a sentence saying that files (changes, timestamps) from before the start cannot be corroborated."""
    return [s for s in sentences if _BEFORE.search(s) and _UNCOVERED.search(s)
            and re.search(r"(?i)\bfiles?\b|\bchang\w*|\btimestamps?\b|\bstomp\w*", s)]


def _drop_list_records(lines):
    """S1: the lines without `usn --list`'s per-record blocks (a USN head line followed by its `Time:` line, and the
    field lines under it), so a label on each record cannot stand in for decision 30's statement."""
    out, in_rec = [], False
    for i, ln in enumerate(lines):
        if _LIST_HEAD.match(ln) and i + 1 < len(lines) and lines[i + 1].startswith("    Time:"):
            in_rec = True
            continue
        if in_rec and _LIST_FIELD.match(ln):
            continue
        in_rec = False
        out.append(ln)
    return out


def _cause_named(w):
    """S6: the pointer blame a passage carries (`_POINTER_CAUSE`, not negated); Q11 (the re-check): and a removal cause
    the bytes do not show ('the copy was overwritten', wiped, destroyed, tampered), not negated just before it."""
    return [m.group(0) for m in _POINTER_CAUSE.finditer(w) if not _NEGATED.search(m.group(0))] + \
        [m.group(0) for m in _REMOVAL_CAUSE.finditer(w) if not _NEGATED_BEFORE.search(w[max(0, m.start() - 30):m.start()])]


# R4: the lines of winsider's outputs that are a RECORD's own content, classified by the format the tool prints them in
# (fd cmd_usn: "  USN %-10d %s" + the field lines; the stats' "Top files by record count" block; fd cmd_timeline:
# "  %-23s  %-5s  %-10s  %-26s  %s" with Src USN / $SI / MLog) -- a name such as RestartAgent.exe is the record's, not
# a statement. Everything else on stdout, and all of stderr, is a statement line.
_LIST_HEAD_NAME = re.compile(r"^  USN (\d+) +")
# acceptance 1.14.0 (K5 / K20): a time is `2026-05-16T16:55:20.9805996Z`, an absent one `(none)`
_TL_EVENT = re.compile(r"^  (?:\d{4}-\d\d-\d\dT[\d:.]+Z|\(none\)|\(undated\)|0x[0-9a-f]+) *  (?:USN|\$SI|MLog) *  "
                       "(?:0x[0-9a-f]+|\u2014) *  ")
_JSON_KEY = re.compile(r'^( *)"([A-Za-z_]\w*)":')
_INSTANCE_KEY = re.compile(r"(?i)instance|restart|recreat|sequence|epoch|boundar")


class _Scan:
    def __init__(self):
        self.rc, self.statements, self.mismatched, self.keys, self.heads, self.err = None, [], [], set(), 0, ""
        self.top, self.rec_keys = None, set()     # 1.14.0: the top-level key a line is under; the Records' own keys

    def ctx(self, what):
        return "\n[%s] rc=%s, %d record head(s); statement lines (tail):\n%s" % (
            what, self.rc, self.heads, "\n".join(self.statements[-40:])[-4000:])


def _r4_classify(sc, form, lines, names):
    """Fill `sc` from stdout lines (an iterable): statement lines, the `--list` head lines that carry anything but the
    record's own name (from the bytes: `names`, USN -> name), the JSON keys (indent, key)."""
    in_top = False
    for ln in lines:
        if form == ("usn", "--json"):
            m = _JSON_KEY.match(ln)
            if m:
                sc.keys.add((len(m.group(1)), m.group(2)))
                if len(m.group(1)) == 2:
                    sc.top = m.group(2)
                elif len(m.group(1)) == 6 and sc.top == "Records":   # 1.14.0: a record's keys (Records[] objects)
                    sc.rec_keys.add(m.group(2))
            continue                                   # stdout carries the export; a statement goes to stderr
        if form == ("usn",):
            if ln.startswith("  Top files by record count:"):
                in_top = True
                sc.statements.append(ln)
                continue
            if in_top:
                if ln.strip():
                    continue                           # a record's own name and its count
                in_top = False
        if form == ("usn", "--list"):
            m = _LIST_HEAD_NAME.match(ln)
            if m:
                sc.heads += 1
                name = ln[17:] if len(m.group(1)) <= 10 else ln[m.end():]
                if names.get(int(m.group(1))) != name and len(sc.mismatched) < 20:
                    sc.mismatched.append(ln)
                continue
            if _LIST_FIELD.match(ln):
                continue
        if form == ("timeline",) and _TL_EVENT.match(ln):
            continue
        sc.statements.append(ln)
    return sc


def _r4_scan(rel, args, names):
    """Run forefst and classify stdout as it streams (winsider's `usn --list` is 1.5 M lines, `usn --json` 3.9 M,
    `timeline` 0.9 M: nothing is cached); stderr lines are statements. A traceback or a timeout is a fixture error."""
    cmd = [sys.executable, "-B", FOREFST, _img(rel)] + list(args)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO)
    errbuf = []
    t = threading.Thread(target=lambda: errbuf.append(p.stderr.read()))
    t.start()
    timer = threading.Timer(TIMEOUT, p.kill)
    timer.start()
    sc = _Scan()
    try:
        _r4_classify(sc, tuple(args), (raw.decode("utf-8", "replace").rstrip("\r\n") for raw in p.stdout), names)
        p.wait()
    finally:
        timer.cancel()
        t.join()
    sc.err = (errbuf[0] if errbuf else b"").decode("utf-8", "replace")
    if p.returncode < 0:
        raise RedFixtureError("timeout or kill (%d): %s" % (p.returncode, " ".join(cmd)))
    if "Traceback (most recent call last)" in sc.err:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + sc.err[-3000:])
    sc.rc = p.returncode
    sc.statements += sc.err.splitlines()
    return sc


def _id_mentions(s, ids):
    """[(start, end, id)]: every FILETIME-shaped journal id a sentence names (hex), and each id of `ids` in any
    rendering (BJ._id_re: hex, zero-padded or not, or decimal)."""
    out = [(m.start(), m.end(), int(m.group(1), 16)) for m in BJ._FT_ID.finditer(s)]
    for j in ids:
        for m in BJ._id_re(j).finditer(s):
            if not [1 for a, b, _j in out if a <= m.start() < b or m.start() <= a < m.end()]:
                out.append((m.start(), m.end(), j))
    return sorted(out)


def _bound_ids(s, ids):
    """Q1 (the re-check): the journal id each earlier-instance phrase of a sentence is bound to -- the id named
    NEAREST to the phrase (before or after it), so 'X (the current journal) and Y (an earlier journal instance)' binds
    the phrase to Y, not to X."""
    men = _id_mentions(s, ids)
    out = []
    for m in _EARLIER_INSTANCE.finditer(s):
        if not men:
            break

        def dist(t):
            a, b, _j = t
            return a - m.end() if a >= m.end() else m.start() - b if b <= m.start() else 0
        out.append(min(men, key=dist)[2])
    return out


def _named_as_earlier(prose, old, cur=None):
    """R3: the sentences that name the journal id `old` AND call it an earlier instance -- an id merely listed, or
    listed beside 'the current journal', is not named as an earlier one. Q1 (the re-check): the earlier-instance phrase
    is bound to the id named nearest to it, and with `cur` (the current journal's id) nothing counts when the current
    id is named as the earlier instance anywhere (inverted labels). Q2: the naming may continue into the next sentence
    when that sentence names no id, refers back to the id ('It is the id of an earlier journal instance') and the id
    is the last one the first sentence names."""
    ids = [j for j in (old, cur) if j is not None]
    ss = _sentences(prose)
    if cur is not None and [s for s in ss if cur in _bound_ids(s, ids)]:
        return []
    out = []
    for i, s in enumerate(ss):
        men = _id_mentions(s, ids)
        if old in _bound_ids(s, ids):
            out.append(s)
        elif men and men[-1][2] == old and i + 1 < len(ss):
            nxt = ss[i + 1]
            if not _id_mentions(nxt, ids) and _BACKREF.search(nxt) and _EARLIER_INSTANCE.search(nxt):
                out.append(s + " " + nxt)
    return out


def _current_called_earlier(sentences, cur_nums, old_nums):
    """Q3 (the re-check): the clauses that put an earlier-sequence phrase on the CURRENT numbering's range -- an
    `_EARLIER_SEQ` phrase in a clause that names one of `cur_nums` (the current numbering's last USN / its end) and none
    of `old_nums` (the earlier sequence's USNs): 'USN 0 .. 173,744 belong to an earlier sequence'."""
    rc, ro = _num(*cur_nums), _num(*old_nums)
    out = []
    for s in sentences:
        for clause in _CLAUSE_SPLIT.split(s):
            if _EARLIER_SEQ.search(clause) and rc.search(clause) and not ro.search(clause):
                out.append(s)
                break
    return out


def _survivors_claimed_above(sentences, tail):
    """Q5 (the re-check): sentences that name a USN above the journal's last record (`tail`) as surviving -- a survive
    word, not negated, with 'USN n' or a range 'n .. m' whose n is above `tail`."""
    out = []
    for s in sentences:
        if not _SURVIVE.search(s) or _NOT_SURVIVE.search(s):
            continue
        ns = [int(x) for x in re.findall(r"(?i)\bUSN\s*#?\s*(\d+)", s)]
        ns += [int(a) for a, _b in re.findall(r"(?<![0-9.:])(\d+)\s*(?:\.\.\.?|…|–|—|\bto\b|\bthrough\b)"
                                               r"\s*(?:USN\s*)?(\d+)(?![0-9])", s)]
        if [n for n in ns if n > tail]:
            out.append(s)
    return out


def _other_record_shown(text, rec):
    """R2: what a text shows of `rec`, the USN record of ANOTHER file that a pointer lands on: its FileRef
    (0x<oid>:0x<idx>), its time to the second (either separator), its reason (a flag name, or its hex value after the
    word 'reason'). Its name is checked by the guard's first assert."""
    _rl, _usn, ts, reason, (oid, idx), _name = rec
    got = []
    if re.search(r"(?i)(?<![0-9a-f])0x0*%x:0x0*%x(?![0-9a-f])" % (oid, idx), text):
        got.append("its FileRef 0x%x:0x%x" % (oid, idx))
    sec = time.strftime("%Y-%m-%d[ T]%H:%M:%S", time.gmtime((ts - EPOCH) // 10 ** 7))
    if re.search(sec, text):
        got.append("its time %s" % sec.replace("[ T]", " "))
    names = [n for b, n in sorted(_USN_REASON_NAMES.items()) if reason & b]
    if names and re.search(r"(?<![A-Za-z_])(?:%s)(?![A-Za-z_])" % "|".join(names), text):
        got.append("its reason %s" % "|".join(names))
    if re.search(r"(?i)\breason\W{0,20}(?:0x)?0*%x(?![0-9a-f])" % reason, text):
        got.append("its reason 0x%08x" % reason)
    # Q6 (the re-check): the tool's own `usn --json` style -- decimal ints: the reason after a reason key, the FileRef
    # as the `home_oid` / `file_id` pair
    if re.search(r"(?i)\breason\W{0,20}%d(?![0-9])" % reason, text):
        got.append("its reason %d (decimal)" % reason)
    _ho, _fi = r'"home_oid"\s*:\s*%d(?![0-9])' % oid, r'"file_id"\s*:\s*%d(?![0-9])' % idx
    if re.search(r"%s[^{}]{0,160}?%s|%s[^{}]{0,160}?%s" % (_ho, _fi, _fi, _ho), text):
        got.append("its FileRef as home_oid %d / file_id %d" % (oid, idx))
    return got


def _range_from_current_end(sentences, xs, ptr, old_ends):
    """S2: the passages that measure a missing range from the CURRENT journal's end (`xs` = its last USN and that
    record's end) to the pointer `ptr`, which belongs to the earlier instance: a range form 'X .. ptr' / 'X to ptr';
    the byte count ptr - X; X and ptr in one sentence with neither of the earlier instance's ends (`old_ends`) between
    them; or X named where the records end ('end at', 'last', 'tail' ...) with ptr after it in that sentence or the
    next, and no earlier-instance end between. Positional, because `_sentences` merges a line without a full stop
    into the next ('USN range: 0 -- 4439864 Journal tail: ...'). The boundary statement ('USN 0 .. X belong to the
    current journal ...') followed by A10's tail sentence is none of these, its two halves joined by a comma or a
    semicolon."""
    xa = "|".join("%d" % x for x in xs)
    rx, rp, ro = _num(*xs), _num(ptr), _num(*old_ends)
    end_x = re.compile(r"(?i)\b(?:end(?:s|ed|ing)?|last|tail|stop(?:s|ped)?|highest|newest|latest)\b[^.;]{0,40}?"
                       r"(?<![0-9])(?:%s)(?![0-9])" % xa)
    span = re.compile(r"(?i)(?<![0-9])(?:%s)\s*(?:\.\.\.?|\u2026|\u2013|\u2014|-|to|through|until)\s*(?:USN\s*)?"
                      r"%d(?![0-9])" % (xa, ptr))
    gap = _num(*(ptr - x for x in xs))

    def unbridged(text, a, b):
        """No earlier-instance end between positions a and b of text (either order)."""
        lo, hi = min(a, b), max(a, b)
        return not ro.search(text[lo:hi])
    out = []
    for i, s in enumerate(sentences):
        w2 = " ".join(sentences[i:i + 2])           # `_sentences` splits after "..", so a range form spans two
        # Q7 (the re-check): the end word on X with the pointer after it reaches the NEXT TWO sentences ("... end at
        # USN 16,096. Every record after that is missing. A file ... still points at USN 5,119,752.")
        w3 = " ".join(sentences[i:i + 3])
        pairs = [(mx, mp) for mx in rx.finditer(s) for mp in rp.finditer(s)]
        ends = [(m, mp) for m in end_x.finditer(s) for mp in rp.finditer(w3) if mp.start() > m.end()]
        if span.search(w2) or gap.search(s) or [1 for mx, mp in pairs if unbridged(s, mx.start(), mp.start())] \
                or [1 for m, mp in ends if unbridged(w3, m.end(), mp.start())]:
            out.append(w3)
    return out


# ST-1: times of day in a statement (the date stripped first, so a date's hyphens are not read as a range)
_HMS = re.compile(r"(?<![0-9:])(\d\d:\d\d:\d\d)(?![0-9:])")
_DATE = re.compile(r"\d{4}-\d\d-\d\d[ T]")
_RANGE_TO = re.compile(r"(?i)\b(?:to|through|thru|until|till)\b|\.\.|\u2026|\u2013|\u2014|-")
_CURRENT_START = re.compile(r"(?i)\bcurrent\b[^.;]{0,30}\b(?:numbering|journal|sequence|instance)\b")


def _sec(iso):
    """'2026-07-05T06:54:51.092533Z' -> a regex for that time to the second, either separator."""
    return iso[:10] + "[ T]" + iso[11:19]


def _span_stated(sentences, lo, lo_time, his, hi_hms):
    """ST-1: a passage (up to 3 sentences) names an earlier sequence (an earlier word) with its surviving records'
    USN span (its lowest USN `lo`; its highest USN or that record's end, `his`) and time span (the lowest record's
    time `lo_time`, a regex to the second; the highest record's time of day `hi_hms`, with or without its date)."""
    rl, rh, rt = _num(lo), _num(*his), re.compile(lo_time)
    return [w for w in _windows(sentences) if _EARLIER.search(w) and rl.search(w) and rh.search(w) and rt.search(w)
            and hi_hms in _HMS.findall(_DATE.sub("", w))]


def _gap_claimed(sentences, old_first, cur_hms, old_last=None):
    """ST-1: the sentences that give ONE span from the earlier sequence's first time (`old_first`, HH:MM:SS) straight
    to a time of the current numbering (`cur_hms`): the next time named after it is a current one, a range word
    stands between them, and the sentence says nothing is uncovered -- the time between the sequences claimed as
    covered. Naming the earlier sequence's last time in between (two spans) is not. Q8 (the re-check): with `old_last`,
    also an open-ended coverage claim -- a coverage word with the earlier first time in a sentence that names neither
    the earlier last time nor an uncovered phrase ('the two sequences cover the changes made since <earlier first>')."""
    out = []
    for s in sentences:
        t = _DATE.sub("", s)
        hits = [(m.start(), m.end(), m.group(1)) for m in _HMS.finditer(t)]
        for k in range(len(hits) - 1):
            if hits[k][2] == old_first and hits[k + 1][2] in cur_hms and _RANGE_TO.search(t[hits[k][1]:hits[k + 1][0]]) \
                    and not _UNCOVERED.search(s):
                out.append(s)
                break
        else:
            hms = [h[2] for h in hits]
            if old_last is not None and _COVER_WORD.search(s) and old_first in hms and old_last not in hms \
                    and not _UNCOVERED.search(s):
                out.append(s)
    return out


def _before_current_start(sentences, cur_hms, old_last):
    """ST-1: 'files changed before <the current numbering's start> cannot be corroborated' -- a before / cannot-be-
    corroborated sentence whose time (its own, or else the last one the previous sentence names) is the current
    numbering's first record (`cur_hms`), or which refers to the current numbering in words, and which does not bound
    the gap with the earlier sequence's last time (`old_last`)."""
    out = []
    for i, s in enumerate(sentences):
        if not _before_uncovered([s]):
            continue
        own = _HMS.findall(_DATE.sub("", s))
        if old_last in own:
            continue
        prev = _HMS.findall(_DATE.sub("", sentences[i - 1])) if i else []
        if cur_hms in own or (not own and prev[-1:] == [cur_hms]) or (not own and _CURRENT_START.search(s)):
            out.append(s)
    return out


def _line_windows(lines, lcn, k=3):
    """Passages of up to k lines that start at a line naming this LCN (hex, any case)."""
    r = AB._lcn_re(lcn)
    return [" ".join(x.strip() for x in lines[i:i + k]) for i, ln in enumerate(lines) if r.search(ln)]


def _hole_named(lines, lcn):
    """C8 = B on one page / copy: a passage naming this LCN says the image stores it as a hole, cause left open."""
    return [w for w in _line_windows(lines, lcn) if _HOLE.search(w) and _HOLE_CAUSE.search(w)]


def _copy_re(lcn):
    """A checkpoint copy of the plants' volume, named by its LCN or by its byte offset (ra prints both)."""
    return re.compile(r"(?i)(?<![0-9a-z])0x0*(?:%x|%x)(?![0-9a-z])" % (lcn, AB.IMG.ps + lcn * CS))


def _copy_passages(lines, lcn, other, k=3):
    """T1a: the text that describes the copy at `lcn`: from its mention to the end of that line (cut at a mention of
    the other copy), then up to k-1 following lines, stopping at a blank line or a line that names either copy."""
    me, oth = _copy_re(lcn), _copy_re(other)
    out = []
    for i, ln in enumerate(lines):
        m = me.search(ln)
        if not m:
            continue
        head = ln[m.start():]
        mo = oth.search(head)
        seg = [head[:mo.start()] if mo else head]
        if not mo:
            for nxt in lines[i + 1:i + k]:
                if not nxt.strip() or oth.search(nxt) or me.search(nxt):
                    break
                seg.append(nxt)
        out.append(" ".join(x.strip() for x in seg))
    return out


def _copy_fields(lines, lcn, other):
    """T1a: every value decoded for the copy at `lcn` (its passages, `_FIELD_VALUE`)."""
    return [m.group(0) for w in _copy_passages(lines, lcn, other) for m in _FIELD_VALUE.finditer(w)]


def _chkp_decodes(lines, lcn, clock):
    """`chkp` decodes ONE copy: its header names that copy's byte offset ('(CHKP) at offset 0x..' / 'CHKP offset
    0x..') and its virtual-clock row reads `clock`."""
    off = re.compile(r"(?i)\bCHKP\)? (?:at )?offset\s+0x0*%x(?![0-9a-z])" % (AB.IMG.ps + lcn * CS))
    clk = re.compile(r"(?i)^\s*virtual clock\b.*?(?<![0-9a-z])%d\s*$" % clock)
    return bool([ln for ln in lines if off.search(ln)] and [ln for ln in lines if clk.search(ln)])


def _header_region(r):
    """timestomp's report header: stdout up to the tier legend, then stderr (the coverage statement's places)."""
    out = []
    for ln in r.prose:
        if "This flags timestamps" in ln:
            break
        out.append(ln)
    return out + r.err.splitlines()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# D30 -- decision 30: two journal instances in one usn listing; the boundary is stated, the CSV/JSON unchanged
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

J_LABF = 0x192DA000                      # $J offset 0 on the labF/labG/win11afterblindaudit/labC2 images (one run)
JID_NEW = 0x01DD48CCCC6EDB06             # the current journal (2026-09-20 06:53:53.132826)
JID_OLD = 0x01DD485DE7522417             # the earlier instance (2026-09-19 17:40:04.106)
NEW_CREATED = r"2026-09-20[ T]06:53:53"
OLD_LAST, OLD_LAST_END, POINTER = 4439864, 4439968, 5119752

# GROUP3_CENSUS.md section 2.3: below the restart (the current journal) n, USN 0..X (end); from the restart up (the
# earlier instance) n, from Y to 4,439,864. Re-measured by the premise from the bytes.
D30 = {
    "step7/labFafterreboot.raw": (2, 128, 256, 43734, 4096),
    "step7/labG_0.raw": (120, 11904, 12016, 43664, 12288),
    "step7/labG_1.raw": (140, 13952, 14064, 43624, 16384),
    "step7/labG_2.raw": (160, 15984, 16096, 43624, 16384),
    "step7/win11afterblindaudit.raw": (417, 45504, 45616, 43319, 49152),
    "step7/labC2.raw": (417, 45504, 45616, 43319, 49152),
}
D30_IDS = ["image-" + os.path.basename(k)[:-4] for k in D30]
# T4 (settled by the lead 2026-10-09): the boundary is stated in EVERY `usn` form -- bare (= `--stats`), `--list`,
# `--info`, and on stderr for `--csv` / `--json` (stdout carries the export), as A10's and S4's statements are.
D30_FORMS =[("usn",), ("usn", "--list"), ("usn", "--info"), ("usn", "--csv"), ("usn", "--json")]
D30_FORM_IDS = ["usn", "usn-list", "usn-info", "usn-csv-stderr", "usn-json-stderr"]
# acceptance 1.14.0 (K21; N308: usn's CSV and JSON carry one key set; N313: timestomp's columns in every format)
USN_CSV_HEADER = ("USN,Timestamp,Reason,ReasonHex,FileName,IsDirectory,ObjectRef,HomeOID,FileID,ParentOID,FullPath,"
                  "FileAttributes,FileAttributesHex,RecordLength,SecurityId,SourceInfo,SourceInfoHex,ParentFileID,"
                  "StreamOffset")                     # acceptance 1.14.0 E2 close (review S3): SourceInfo names + hex
USN_JSON_KEYS = set(USN_CSV_HEADER.split(","))
TIMESTOMP_CSV_HEADER = ("ObjectRef,FullPath,RecordPlacement,DataResidency,Confidence,Basis,Signals,EvidenceRefs,"
                        "Created,Modified,Changed,Accessed")
_D30_PREMISE = {}


def _d30_premise(rel):
    """From the bytes: $J at J_LABF holds two USN blocks split cleanly at Y (a cluster boundary, zeros between): the
    low block 0..X is newer than the current id's FILETIME, the high block Y..4,439,864 older. Returns the total."""
    if rel in _D30_PREMISE:
        return _D30_PREMISE[rel]
    n_lo, x, x_end, n_hi, y = D30[rel]
    path = _img(rel)
    with open(path, "rb") as fh:
        fh.seek(J_LABF)
        j = fh.read(OLD_LAST_END + 0x200)
    recs = _carve(j)
    lo = [r for r in recs if r[1] < y]
    hi = [r for r in recs if r[1] >= y]
    _fx(len(lo) == n_lo and lo[0][1] == 0 and lo[-1][1] == x and lo[-1][1] + lo[-1][0] == x_end,
        "%s: the current block is not %d records USN 0..%d (end %d)" % (rel, n_lo, x, x_end))
    _fx(len(hi) == n_hi and hi[0][1] == y and hi[-1][1] == OLD_LAST and hi[-1][1] + hi[-1][0] == OLD_LAST_END,
        "%s: the earlier block is not %d records USN %d..%d" % (rel, n_hi, y, OLD_LAST))
    _fx(all(r[2] >= JID_NEW for r in lo) and all(r[2] < JID_NEW for r in hi),
        "%s: the blocks do not split at the current journal's creation time" % rel)
    _fx(_steps(recs) == [(y, True)] and y % CS == 0 and not any(j[x_end:y]),
        "%s: not one clean split on a cluster boundary with zeros between" % rel)
    _D30_PREMISE[rel] = len(recs)
    return len(recs)


def _d30_check_kept(rel, args, r):
    """The properties every D30 form keeps: exit 2 (A10), A10's missing-range sentence, the CSV header / JSON keys."""
    _keep(r.rc == 2, "A10 keeps exit 2 on this volume" + r.ctx(rel))
    _keep(AV._names_range(_sentences(_where(args, r))), "A10's missing range (USN %d .. %d) must stay named" %
          (OLD_LAST, POINTER) + r.ctx(rel))
    total = _d30_premise(rel)
    if args == ("usn", "--csv"):
        _keep(r.header_line == USN_CSV_HEADER and r.nrows == total,
              "usn --csv: header and %d rows exactly as today (decision 30: CSV columns unchanged)" % total
              + r.ctx(rel))
    if args == ("usn", "--json"):
        try:
            doc = json.loads(r.out)
        except ValueError as e:
            raise RedFixtureError("usn --json printed no JSON document on stdout: %s" % e)
        keys = {tuple(sorted(rec)) for rec in jget(doc, "records", default=[])}
        _keep(keys == {tuple(sorted(USN_JSON_KEYS))} and jget(doc, "record_count") == total,
              "usn --json: the per-record keys and the count exactly as today (a per-record instance key is 1.14)"
              + r.ctx(rel))


# RED 1.13.2 D30: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", D30_FORMS, ids=D30_FORM_IDS)
@pytest.mark.parametrize("rel", list(D30), ids=D30_IDS)
def test_d30_usn_states_the_journal_instance_boundary(rel, args):
    _d30_premise(rel)
    r = _run(rel, *args, keep_out=(args == ("usn", "--json")))
    _d30_check_kept(rel, args, r)
    _n, x, x_end, _m, y = D30[rel]
    prose = _where(args, r)
    # S1 (the critic): the statement, not a label on each record -- `usn --list`'s per-record blocks are dropped first
    # (on labFafterreboot record USN 128's own Time: line reads 06:53:53, so labels alone would pass)
    assert _boundary_stated(_sentences(_drop_list_records(prose)), (x, x_end), (y,), NEW_CREATED), (
        "%s %s: nothing states that USN 0..%d belong to the current journal (created 2026-09-20 06:53:53) and USN "
        "%d.. to an earlier instance%s" % (rel, " ".join(args), x, y,
                                           " (on stderr: stdout carries the export)" if prose is not r.prose else "")
    ) + r.ctx(rel)


D30_CONTROLS = ["step7/labFbeforereboot.raw", "step7/labBeforeF.raw"]


@pytest.mark.parametrize("args", D30_FORMS, ids=D30_FORM_IDS)
@pytest.mark.parametrize("rel", D30_CONTROLS, ids=["image-labFbeforereboot", "image-labBeforeF"])
def test_d30_control_a_single_instance_volume_states_no_boundary(rel, args):
    """Not a RED. One journal instance, one numbering sequence (own carve: no backward step of more than 1 s): no
    boundary or instance word, exit 0, and the CSV header / JSON record keys pinned as today."""
    path = _img(rel)
    with open(path, "rb") as fh:
        fh.seek(J_LABF)
        recs = _carve(fh.read(OLD_LAST_END + 0x200))
    _fx(recs and recs[0][1] == 0 and not _steps(recs), "%s: not one numbering sequence" % rel)
    r = _run(rel, *args, keep_out=(args == ("usn", "--json")))
    assert r.rc == 0, r.ctx(rel)
    assert not [ln for ln in r.prose if _BOUNDARY.search(ln) or _RESTART.search(ln)], r.ctx(rel)
    if args == ("usn", "--csv"):
        assert r.header_line == USN_CSV_HEADER and r.nrows == len(recs), r.ctx(rel)
    if args == ("usn", "--json"):
        doc = json.loads(r.out)
        assert {tuple(sorted(rec)) for rec in jget(doc, "records")} == {tuple(sorted(USN_JSON_KEYS))}, r.ctx(rel)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# D31 -- decision 31: a journal re-creation evident from the bytes is stated neutrally and exits 2
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

JOURNAL_CMDS = [("usn", "--csv"), ("usn", "--info"), ("usn", "--stats"), ("timeline", "--csv"), ("timestomp", "--csv")]
JOURNAL_IDS = ["usn-csv", "usn-info", "usn-stats", "timeline-csv", "timestomp-csv"]

R8G = "step6/win11refs8g.raw"
R8G_EXT = [(0x82100, 7936, 0)]            # $J vcn 0..7935 (the records' range); the other 84 runs hold no record
R8G_ID = 0x01DD0AD01B8938ED              # kept by `createjournal` over the existing journal (2026-07-03 09:41:22)
R8G_RESTART_TIME = r"2026-07-05[ T]06:54:51"     # first record of the current numbering (06:54:51.092533)
R8G_ID_TIME = r"2026-07-03[ T]09:41:22"
# Q3: the current numbering's last USN and its end; the earlier sequence's lowest, highest and end (census 2.3)
R8G_CUR, R8G_OLD = (173744, 173912), (176128, 487944, 488048)
_R8G_PREMISE = []


def _r8g_premise():
    """GROUP3_CENSUS.md 2.3, from the bytes: 1,619 records USN 0..173,744 (2026-07-05 06:54:51.092-06:54:56.941)
    below 2,353 records USN 176,128..487,944 (2026-07-03 10:12:01.637-11:05:40.459), one clean split on a cluster
    boundary, zeros between; every record of BOTH blocks is newer than the id's FILETIME (the id was kept)."""
    if _R8G_PREMISE:
        return
    j, _alloc = _read_j(_img(R8G), 0x1000000, R8G_EXT, nbytes=491520)
    recs = _carve(j)
    lo = [r for r in recs if r[1] < 176128]
    hi = [r for r in recs if r[1] >= 176128]
    _fx(len(lo) == 1619 and lo[0][1] == 0 and lo[0][5] == "ads_size_sweep" and lo[-1][1] == 173744
        and _at(lo[0][2], "2026-07-05T06:54:51.092533Z") and _at(max(r[2] for r in lo), "2026-07-05T06:54:56.941848Z"),
        "win11refs8g: the current numbering is not 1,619 records USN 0..173,744 from 06:54:51.092533")
    _fx(len(hi) == 2353 and hi[0][1] == 176128 and hi[-1][1] == 487944
        and _at(min(r[2] for r in hi), "2026-07-03T10:12:01.637487Z"),
        "win11refs8g: the earlier numbering is not 2,353 records USN 176,128..487,944 from 2026-07-03 10:12:01")
    _fx(_steps(recs) == [(176128, True)] and not any(j[173912:176128]),
        "win11refs8g: not one clean split at 176,128 with zeros between")
    _fx(all(r[2] > R8G_ID for r in recs), "win11refs8g: a record older than the journal id")
    _R8G_PREMISE.append(True)


# RED 1.13.2 D31: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", JOURNAL_CMDS, ids=JOURNAL_IDS)
def test_d31_same_id_restart_is_stated_and_exits_2_on_image_win11refs8g(args):
    _r8g_premise()
    r = _run(R8G, *args)
    if args == ("usn", "--info"):
        _fx(re.search(r"Journal ID:\s+0x%016x\b" % R8G_ID, "\n".join(r.prose)), "usn --info: not the pinned id")
    if args == ("usn", "--csv"):
        _keep(r.header_line == USN_CSV_HEADER and r.nrows == 3972, "usn --csv: header and 3,972 rows as today"
              + r.ctx(R8G))
    if args == ("timestomp", "--csv"):
        _keep(r.header_line == TIMESTOMP_CSV_HEADER, "timestomp --csv: header as today" + r.ctx(R8G))
    s = _sentences(_where(args, r))
    win = _restart_windows(s, R8G_RESTART_TIME)
    assert win, ("nothing states that the journal's numbering restarted at USN 0 at 2026-07-05 06:54:51 (the first "
                 "record of the current numbering)") + r.ctx(R8G)
    assert [w for w in win if _ID_KEPT.search(w)], "the restart statement does not say the id was kept: %r" % win[:2]
    assert [w for w in win if _EARLIER_SEQ.search(w)], ("the restart statement does not say the earlier records "
                                                        "belong to an earlier sequence: %r" % win[:2])
    # Q3 (the re-check): the earlier-sequence clause on the CURRENT numbering's range is not the statement
    bad = _current_called_earlier(_sentences(win), R8G_CUR, R8G_OLD)
    assert not bad, "the current numbering's range (USN 0 .. 173,744) is called an earlier sequence: %r" % bad[:1]
    assert not [w for w in win if _WIPED.search(w)], "never 'wiped'/'destroyed' (decision 31): %r" % win[:2]
    assert not [w for w in _windows(s) if _RESTART.search(w) and re.search(R8G_ID_TIME, w)
                and not re.search(R8G_RESTART_TIME, w)], "the id's 2026-07-03 time is given as the restart time"
    assert r.rc == 2, "a journal re-creation evident from the bytes exits 2 (decision 31), rc=%d" % r.rc + r.ctx(R8G)


# S7 (the lead, 2026-10-09): T4's "every usn form" also for the same-id restart -- the forms JOURNAL_CMDS does not run
S7_FORMS = [("usn",), ("usn", "--list"), ("usn", "--json")]
S7_IDS = ["usn", "usn-list", "usn-json-stderr"]


# RED 1.13.2 D31: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", S7_FORMS, ids=S7_IDS)
def test_d31_s7_same_id_restart_is_stated_in_every_usn_form_on_image_win11refs8g(args):
    _r8g_premise()
    r = _run(R8G, *args, keep_out=(args == ("usn", "--json")))
    if args == ("usn",):
        _keep([ln for ln in r.prose if "USN Journal Statistics (3972 records)" in ln],
              "bare usn: the statistics of the 3,972 records as today" + r.ctx(R8G))
    if args == ("usn", "--list"):
        _keep(len([ln for ln in r.prose if _LIST_HEAD.match(ln)]) == 3972, "usn --list: the 3,972 records listed as "
              "today" + r.ctx(R8G))
    if args == ("usn", "--json"):
        try:
            doc = json.loads(r.out)
        except ValueError as e:
            raise RedFixtureError("usn --json printed no JSON document on stdout: %s" % e)
        _keep({tuple(sorted(rec)) for rec in jget(doc, "records", default=[])} == {tuple(sorted(USN_JSON_KEYS))}
              and jget(doc, "record_count") == 3972, "usn --json: the per-record keys and the count exactly as today "
              "(a per-record instance key is 1.14)" + r.ctx(R8G))
    prose = _where(args, r)
    if args == ("usn", "--list"):
        prose = _drop_list_records(prose)                    # S1: a label on each record is not the statement
    s = _sentences(prose)
    win = _restart_windows(s, R8G_RESTART_TIME)
    assert win, ("S7: %s: nothing states that the journal's numbering restarted at USN 0 at 2026-07-05 06:54:51 (the "
                 "first record of the current numbering)%s" % (
                     " ".join(args), " on stderr (stdout carries the export)" if args == ("usn", "--json") else "")
                 ) + r.ctx(R8G)
    assert [w for w in win if _ID_KEPT.search(w)], "the restart statement does not say the id was kept: %r" % win[:2]
    assert [w for w in win if _EARLIER_SEQ.search(w)], ("the restart statement does not say the earlier records "
                                                        "belong to an earlier sequence: %r" % win[:2])
    # Q3 (the re-check): the earlier-sequence clause on the CURRENT numbering's range is not the statement
    bad = _current_called_earlier(_sentences(win), R8G_CUR, R8G_OLD)
    assert not bad, "the current numbering's range (USN 0 .. 173,744) is called an earlier sequence: %r" % bad[:1]
    assert not [w for w in win if _WIPED.search(w)], "never 'wiped'/'destroyed' (decision 31): %r" % win[:2]
    assert not [w for w in _windows(s) if _RESTART.search(w) and re.search(R8G_ID_TIME, w)
                and not re.search(R8G_RESTART_TIME, w)], "the id's 2026-07-03 time is given as the restart time"
    assert r.rc == 2, "a journal re-creation evident from the bytes exits 2 (decision 31), rc=%d" % r.rc + r.ctx(R8G)


V2 = "step7/winsiderv2.raw"
V2_PS = 0xD900000
V2_EXT = [(4941947, 6021, 0), (4249486, 2171, 6021)]
V2_ID = 0x01DD480A647AAD83               # the current journal (2026-09-19 07:42:16.361)
V2_OLD = 0x01DCE1857F465FDD              # winsider's journal; 7,488 files and 2,038 directories still carry it
V2_ROWS = (("desktop.ini", 0x1A97C378, 63094784), ("ActivationStore.dat", 0x16D8C378, 58551712))
V2_LOWEST, V2_LOWEST_TIME, V2_HIGHEST = 312762368, "2026-09-19T09:14:02.480539Z", 346314464
_V2_PREMISE = []


def _v2_premise():
    """From the bytes: the current $J holds one wrapped sequence USN 312,762,368..346,314,464 (2 clock steps, no clean
    split), and rows of earlier files carry winsider's id with pointers below its lowest surviving USN."""
    if _V2_PREMISE:
        return
    path = _img(V2)
    j, alloc = _read_j(path, V2_PS, V2_EXT)
    recs = _carve(j, alloc)
    _fx(len(recs) == 236073 and recs[0][1] == V2_LOWEST and recs[-1][1] == V2_HIGHEST
        and _at(recs[0][2], V2_LOWEST_TIME) and min(r[2] for r in recs) == recs[0][2],
        "winsiderv2: the $J is not 236,073 records USN %d..%d from %s" % (V2_LOWEST, V2_HIGHEST, V2_LOWEST_TIME))
    st = _steps(recs)
    _fx(len(st) == 2 and not any(c for _u, c in st), "winsiderv2: not two clock steps without a clean split")
    for name, off, usn in V2_ROWS:
        _fx(_row_at(path, off, name) == (usn, V2_OLD) and usn < V2_LOWEST,
            "winsiderv2: the row of %s at 0x%x does not carry winsider's id with LastUsn %d" % (name, off, usn))
    _V2_PREMISE.append(True)


# RED 1.13.2 D31: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", JOURNAL_CMDS, ids=JOURNAL_IDS)
def test_d31_earlier_instance_without_records_is_named_and_exits_2_on_image_winsiderv2(args):
    _v2_premise()
    r = _run(V2, *args)
    prose = _where(args, r)
    # R3 (the critic): named AS an earlier instance -- the id listed beside "the current journal" does not pass
    assert _named_as_earlier(prose, V2_OLD, V2_ID), (                  # R3, Q1
        "nothing names the earlier journal instance 0x%016x that files' pointers belong to (as an earlier instance, "
        "in the sentence that names the id)" % V2_OLD) + r.ctx(V2)
    assert not [ln for ln in prose if AV._DESTROYED_CLAIM.search(ln) or _WIPED.search(ln)], (
        "an instance with no surviving record is named, not compared: nothing is 'destroyed'") + r.ctx(V2)
    assert r.rc == 2, "a journal re-creation evident from the bytes exits 2 (decision 31), rc=%d" % r.rc + r.ctx(V2)


LABJ = "step7/labJjournal.raw"
LABJ_OLD = 0x01DD4E57F72AC89E
_LABJ_PREMISE = []


def _labj_premise():
    """BJ._labj_premise's checks (LAB-J's rows and m5's record, BJ's pinned offsets and readers), on the image addressed
    by its step path: BJ's own premise looks the image up by its bare name (N386)."""
    if _LABJ_PREMISE:
        return
    img = _img(LABJ)
    _fx(os.path.getsize(img) == 4294967296, "labJjournal: size")
    _fx(BJ.JID_OLD == LABJ_OLD, "BJ's first journal id moved")
    with open(img, "rb") as fh:
        for name, (offs, usn, jid) in BJ.LABJ_ROWS.items():
            for off in offs:
                fh.seek(off)
                row = BJ._dir_row(fh.read(0x800), 0, name)
                _fx(row == (name, usn, jid), "labJjournal row 0x%x: %r (want %s, 0x%x, 0x%016x)"
                    % (off, row, name, usn, jid))
        fh.seek(BJ.LABJ_M5_CLOSE)
        rec = fh.read(0x100)
    r = BJ._usn_v3_at(rec, 0)
    _fx(r is not None and r[1] == 0x100 and r[2] == "m5_after_delete_create.txt"
        and struct.unpack_from("<I", rec, 0x38)[0] == 0x80000102,
        "labJjournal: $J USN 256 is not m5's close record: %r" % (r,))
    _fx(all(u < BJ.LABJ_TAIL for (_o, u, _j) in BJ.LABJ_ROWS.values()), "a stale pointer is not below the tail")
    _LABJ_PREMISE.append(True)


# RED 1.13.2 D31: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", JOURNAL_CMDS, ids=JOURNAL_IDS)
def test_d31_recreated_journal_is_named_and_exits_2_on_image_labJjournal(args):
    _labj_premise()
    r = _run(LABJ, *args)
    prose = _where(args, r)
    assert _named_as_earlier(prose, LABJ_OLD, LABJ_NEW), (             # R3, Q1
        "nothing names the earlier journal instance 0x%016x (as an earlier instance, in the sentence that names the "
        "id)" % LABJ_OLD) + r.ctx(LABJ)
    assert r.rc == 2, "a journal re-creation evident from the bytes exits 2 (decision 31), rc=%d" % r.rc + r.ctx(LABJ)


# S5 (the lead, 2026-10-09): decision 31's sentence on labJjournal. From the bytes (own carve, `_labj_seq_premise`): the
# re-created journal's $J holds ONE numbering sequence, 249 records USN 0..31,576; USN 0 is m5's FILE_CREATE at
# 08:12:42.613558, newer than the new id (0x01dd4e57f84a6362, 08:12:42.572886 -- the same second, so only "USN 0" binds a
# printed time to the first record); the first id (0x01dd4e57f72ac89e) is 08:12:40.688041. Nothing of the first
# instance survives in $J (census): its "earlier records" are m1-m3's pointers.
LABJ_NEW = BJ.JID_NEW
LABJ_FIRST = "2026-09-27T08:12:42.613558Z"
LABJ_RESTART_TIME = r"2026-09-27[ T]08:12:42"
LABJ_OLD_TIME = r"2026-09-27[ T]08:12:40"
_LABJ_SEQ = []


def _labj_seq_premise():
    """From the bytes: $J offset 0 (BJ.LABJ_M5_CLOSE - 256, the cluster of m5's close record) holds 249 records USN
    0..31,576 in one sequence (no backward step), USN 0 = m5_after_delete_create.txt FILE_CREATE at LABJ_FIRST, every
    record newer than the new id and the new id newer than the first one; the two ids' times differ by a second."""
    if _LABJ_SEQ:
        return
    with open(_img(LABJ), "rb") as fh:
        fh.seek(BJ.LABJ_M5_CLOSE - 0x100)
        recs = _carve(fh.read(0x10000))
    _fx(len(recs) == 249 and recs[0][1] == 0 and recs[-1][1] == 31576 and recs[0][5] == "m5_after_delete_create.txt"
        and recs[0][3] == 0x100 and _at(recs[0][2], LABJ_FIRST), "labJjournal: $J is not 249 records USN 0..31,576 "
        "from m5's FILE_CREATE at %s" % LABJ_FIRST)
    _fx(not [i for i in range(len(recs) - 1) if recs[i + 1][2] < recs[i][2]], "labJjournal: a backward time step")
    _fx(all(r[2] > LABJ_NEW for r in recs) and LABJ_OLD < LABJ_NEW and _at(LABJ_OLD, "2026-09-27T08:12:40.688041Z")
        and _at(LABJ_NEW, "2026-09-27T08:12:42.572886Z"), "labJjournal: the ids' times moved")
    _LABJ_SEQ.append(True)


# RED 1.13.2 D31: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", JOURNAL_CMDS, ids=JOURNAL_IDS)
def test_d31_s5_labJjournal_states_the_restart_at_its_first_records_time(args):
    _labj_premise()
    _labj_seq_premise()
    r = _run(LABJ, *args)
    s = _sentences(_where(args, r))
    stated = _restart_times(s)
    win = [w for w, t in stated if re.match(LABJ_RESTART_TIME, t) and _USN0.search(w)]
    assert win, ("S5: nothing states that the journal's numbering restarted at USN 0 at 2026-09-27 08:12:42 (the first "
                 "record of the current numbering)%s" % (" on stderr" if tuple(args) in _STDERR_FORMS else "")) \
        + r.ctx(LABJ)
    assert [w for w in win if _ID_NEW.search(w)], "S5: the restart statement does not say the id is new: %r" % win[:2]
    assert not [w for w in win if _ID_KEPT_CLAIM.search(w)], ("S5: the restart statement says the id was kept; on "
                                                              "labJjournal it changed: %r" % win[:2])
    # S5 relaxed (the lead, GROUP3_PREP "The narrow re-check", a sanctioned oracle change; the re-check's Q4): decision
    # 31's clause "earlier records, where they survive, belong to an earlier sequence" has no object on labJjournal --
    # nothing of the first instance survives in $J -- so the restart statement plus N196's naming of the earlier
    # instance, in any statement of the output, suffices (the naming bound to the id, Q1)
    assert _named_as_earlier(_where(args, r), LABJ_OLD, LABJ_NEW), (
        "S5: the restart is stated, but the earlier instance 0x%016x (m1-m3's pointers) is not named as an earlier "
        "instance anywhere in the statement output: %r" % (LABJ_OLD, win[:2])) + r.ctx(LABJ)
    # Q5 (the re-check): and no USN range above the journal's last record (31,576) is named as surviving -- none does
    claimed = _survivors_claimed_above(s, BJ.LABJ_TAIL)
    assert not claimed, ("S5: records above the last record (USN %d) are said to survive, and none does: %r"
                         % (BJ.LABJ_TAIL, claimed[:1])) + r.ctx(LABJ)
    assert not [w for w in win if _WIPED.search(w)], "never 'wiped'/'destroyed' (decision 31): %r" % win[:2]
    assert not [w for w, t in stated if re.match(LABJ_OLD_TIME, t)], ("S5: the first id's time (08:12:40) is given as "
                                                                       "the restart time") + r.ctx(LABJ)


D31_LINEAGE = ["step7/win11afterblindaudit.raw", "step7/labC2.raw"]


# RED 1.13.2 D31: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", [("timeline", "--csv"), ("timestomp", "--csv")], ids=["timeline-csv", "timestomp-csv"])
@pytest.mark.parametrize("rel", D31_LINEAGE, ids=["image-win11afterblindaudit", "image-labC2"])
def test_d31_new_id_recreation_is_named_in_timeline_and_timestomp(rel, args):
    _d30_premise(rel)
    r = _run(rel, *args)
    _keep(r.rc == 2, "A10 keeps exit 2 on this volume" + r.ctx(rel))
    prose = _where(args, r)
    assert _named_as_earlier(prose, JID_OLD, JID_NEW) and BJ._id_re(JID_NEW).search("\n".join(prose)), (  # R3, Q1
        "nothing names the earlier instance 0x%016x as distinct from the current journal 0x%016x (as an earlier "
        "instance, in the sentence that names the id)" % (JID_OLD, JID_NEW)) + r.ctx(rel)


def _ids_named(r):
    return BJ._journal_ids_named("\n".join(r.prose))


@pytest.mark.parametrize("args", JOURNAL_CMDS, ids=JOURNAL_IDS)
def test_d31_control_one_numbering_sequence_states_no_recreation_on_image_labFbeforereboot(args):
    """Not a RED. labFbeforereboot: one instance, one numbering sequence (own carve), the files' pointers below the
    last record. No re-creation / restart / instance statement, no other journal id, exit 0 (golden: rc 0)."""
    rel = "step7/labFbeforereboot.raw"
    with open(_img(rel), "rb") as fh:
        fh.seek(J_LABF)
        recs = _carve(fh.read(OLD_LAST_END + 0x200))
    _fx(len(recs) == 43771 and not _steps(recs), "labFbeforereboot: not 43,771 records in one sequence")
    r = _run(rel, *args)
    assert r.rc == 0, r.ctx(rel)
    assert not [ln for ln in r.prose if _RESTART.search(ln) or _BOUNDARY.search(ln)], r.ctx(rel)
    assert _ids_named(r) <= {JID_OLD}, r.ctx(rel)


WS = "step4/winsider.raw"
WS_ID = 0x01DCE1857F465FDD
WS_LOWEST, WS_LOWEST_TIME = 40906752, "2026-05-11T20:34:50.257808Z"
WS_EARLIEST_USN, WS_EARLIEST_TIME = 59226288, "2026-05-11T10:37:29.730386Z"
_WS_PREMISE = []


def _ws_premise():
    """From the bytes: one wrapped sequence USN 40,906,752..74,459,840 (217,892 records); six backward time steps of
    more than 1 s, none a clean split (the census's restart test is false here); the earliest timestamp is NOT at the
    lowest USN (a clock step)."""
    if _WS_PREMISE:
        return
    j, alloc = _read_j(_img(WS), V2_PS, V2_EXT)
    recs = _carve(j, alloc)
    _fx(len(recs) == 217892 and recs[0][1] == WS_LOWEST and recs[-1][1] == 74459840
        and _at(recs[0][2], WS_LOWEST_TIME), "winsider: not 217,892 records USN %d.. from %s" % (WS_LOWEST,
                                                                                                    WS_LOWEST_TIME))
    et = min(recs, key=lambda r: r[2])
    _fx(et[1] == WS_EARLIEST_USN and _at(et[2], WS_EARLIEST_TIME), "winsider: the earliest timestamp moved")
    st = _steps(recs)
    _fx(len(st) == 6 and not any(c for _u, c in st), "winsider: not six clock steps without a clean split: %r" % st)
    _WS_NAMES.update((r[1], r[5]) for r in recs)          # R4: each record's own name, from the bytes
    _WS_PREMISE.append(True)


_WS_NAMES = {}


@pytest.mark.parametrize("args", JOURNAL_CMDS + [("timestomp",)], ids=JOURNAL_IDS + ["timestomp"])
def test_d31_control_clock_steps_are_not_a_restart_on_image_winsider(args):
    """Not a RED. winsider: six clock steps inside one wrapped sequence. A rule keyed on timestamps against the id
    would call 75,448 records an earlier instance; the USN-order rule must not. No restart / instance statement, no
    other journal id, exit 0 (golden: rc 0). R4 (the critic): also `timestomp` (text), where N219's statement lives
    (the same run as N219's wrapped RED; its whole prose carries no restart / boundary word today, measured)."""
    _ws_premise()
    r = _run(WS, *args)
    assert r.rc == 0, r.ctx(WS)
    # R-A (the re-check): nor ST-1's own words, an earlier sequence (`_EARLIER_SEQ`)
    assert not [ln for ln in r.prose if _RESTART.search(ln) or _BOUNDARY.search(ln) or _EARLIER_SEQ.search(ln)], \
        r.ctx(WS)
    assert _ids_named(r) <= {WS_ID}, r.ctx(WS)


# R4's other forms (the lead, 2026-10-09): no restart / boundary wording on winsider in any journal command. Measured on
# cbb888e8: bare `usn`, `usn --list`, `usn --json` (stderr) and `timeline` (text) state none today -- every hit of the
# restart / boundary / id matchers is a record's own name (RestartAgent.exe, ..restartup-repairbde..,
# previous.driver.stl, a manifest name with a FILETIME-shaped hex) -- so these are GUARDS.
R4_FORMS = [("usn",), ("usn", "--list"), ("usn", "--json"), ("timeline",)]
R4_IDS = ["usn", "usn-list", "usn-json-stderr", "timeline"]


@pytest.mark.parametrize("args", R4_FORMS, ids=R4_IDS)
def test_r4_guard_clock_steps_are_not_a_restart_in_the_other_journal_forms_on_image_winsider(args):
    """Not a RED: a guard (passes today, must keep passing). winsider: one wrapped sequence whose times step back six
    times (`_ws_premise`). Its statement lines (stdout minus the records' own lines, by the tool's print format, plus
    stderr) carry no restart / instance-boundary word and no journal id but its own; a `usn --list` head line carries
    its record's own name and nothing else (a per-record '[earlier instance]' label is a statement too); `usn --json`'s
    per-record keys stay the 16 of today (decision 30) and no key names an instance or a restart. Exit 0 (golden)."""
    _ws_premise()
    sc = _r4_scan(WS, args, _WS_NAMES)
    what = "winsider " + " ".join(args)
    assert sc.rc == 0, sc.ctx(what)
    # R-A (the re-check): nor ST-1's own words, an earlier sequence (`_EARLIER_SEQ`)
    said = [ln for ln in sc.statements if _RESTART.search(ln) or _BOUNDARY.search(ln) or _EARLIER_SEQ.search(ln)]
    assert not said, ("R4: winsider's clock steps are inside one wrapped sequence, yet %s calls them a restart / names "
                      "an instance boundary: %r" % (what, said[:2])) + sc.ctx(what)
    assert BJ._journal_ids_named("\n".join(sc.statements)) <= {WS_ID}, sc.ctx(what)
    if args == ("usn",):
        _keep([ln for ln in sc.statements if "USN Journal Statistics (217892 records)" in ln],
              "bare usn: the statistics of the 217,892 records as today" + sc.ctx(what))
    if args == ("usn", "--list"):
        _keep(sc.heads == 217892, "usn --list: the 217,892 records listed as today" + sc.ctx(what))
        assert not sc.mismatched, ("R4: a usn --list head line carries more than its record's own name (a label): %r"
                                   % sc.mismatched[:2]) + sc.ctx(what)
    if args == ("usn", "--json"):
        # acceptance 1.14.0 (N308): the records' keys are the CSV's columns; the Journal object's keys sit beside them
        assert sc.rec_keys == USN_JSON_KEYS, sorted(sc.rec_keys)
        assert not [k for _i, k in sc.keys if _INSTANCE_KEY.search(k)], sorted(sc.keys)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N196 -- strict naming: the earlier id is named AS an earlier instance (the node that binds the fix)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# test_1132_red_b2_journal.py's N196 image RED (N196_IMG_CMDS) runs these forms on labJjournal with
# `_names_other_instance`, which accepts the id listed within two lines of any `_BOUNDARY` word -- "the current
# journal" included (the critic's R3/Y7). That RED keeps its matcher (the lead); these nodes bind the fix.
N196_FORMS = [("usn", "--info"), ("timeline", "--csv"), ("timestomp",)]
N196_FORM_IDS = ["usn-info", "timeline-csv", "timestomp"]
N196_STRICT = {LABJ: (LABJ_OLD, LABJ_NEW), V2: (V2_OLD, V2_ID)}


# RED 1.13.2 N196: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", N196_FORMS, ids=N196_FORM_IDS)
@pytest.mark.parametrize("rel", [LABJ, V2], ids=["image-labJjournal", "image-winsiderv2"])
def test_n196_strict_the_earlier_id_is_named_as_an_earlier_instance(rel, args):
    (_labj_premise if rel == LABJ else _v2_premise)()
    old, cur = N196_STRICT[rel]
    r = _run(rel, *args)
    if args == ("usn", "--info"):
        _keep(BJ._id_re(cur).search("\n".join(r.prose)) is not None, "usn --info must still print the current journal "
              "id 0x%016x" % cur + r.ctx(rel))
    assert _named_as_earlier(_where(args, r), old, cur), (                # Q1
        "N196: nothing names 0x%016x, the id the files' pointers carry, as an earlier journal instance (in the sentence "
        "that names the id)" % old) + r.ctx(rel)


@pytest.mark.parametrize("args", N196_FORMS, ids=N196_FORM_IDS)
def test_n196_strict_control_a_single_instance_volume_names_no_id_as_an_earlier_instance(args):
    """Not a RED: the control of the strict N196 nodes. labFbeforereboot: one journal instance, one numbering sequence
    (own carve), its files carry the current id 0x01dd485de7522417. No id -- its own above all -- is named as an
    earlier instance, no other id is named, exit 0. Refuses a fix that calls every id the files carry an earlier one."""
    rel = "step7/labFbeforereboot.raw"
    with open(_img(rel), "rb") as fh:
        fh.seek(J_LABF)
        recs = _carve(fh.read(OLD_LAST_END + 0x200))
    _fx(len(recs) == 43771 and not _steps(recs), "labFbeforereboot: not 43,771 records in one sequence")
    r = _run(rel, *args)
    assert r.rc == 0, r.ctx(rel)
    assert _ids_named(r) <= {JID_OLD}, r.ctx(rel)
    assert not _named_as_earlier(r.prose, JID_OLD), r.ctx(rel)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# S2 -- pointers compared with their own instance; a pointer is never joined to a record of another instance
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# GROUP3_CENSUS.md 3.5 / Appendix B.1 ('other'): (volume, path, is_dir, LastUsn, the row's UsnJournalId, the image
# offset of the file's type-0x30 row (None for a directory: its pointer is in its own $SI), and the record that starts
# at that USN: its name and FileRef). Each is a pointer of an EARLIER instance (labG/win11afterblindaudit) or of the
# earlier numbering (win11refs8g, same id) that lands on a record of the current one.
S2_CASES = [
    ('step7/labG_1.raw', 'LABE/e5_control_realzeros.bin', False, 12288, 0x01dd485de7522417, 0x1609748, '_selftest', 0x765, 0x0),
    ('step7/labG_2.raw', 'LABA/dir2', True, 15488, 0x01dd485de7522417, None, '_selftest', 0x766, 0x0),
    ('step7/labG_2.raw', 'LABE/e5_control_realzeros.bin', False, 12288, 0x01dd485de7522417, 0x1609748, '_selftest', 0x765, 0x0),
    ('step7/win11afterblindaudit.raw', 'LABA/dir2', True, 15488, 0x01dd485de7522417, None, '_selftest', 0x766, 0x0),
    ('step7/win11afterblindaudit.raw', 'LABC/plain/c1_1500.bin', False, 42880, 0x01dd485de7522417, 0x120ced8, 'labc2_actions.csv', 0x76c, 0x2),
    ('step7/win11afterblindaudit.raw', 'LABD/donor.bin', False, 38048, 0x01dd485de7522417, 0x12083f0, 'c1_512.bin', 0x76d, 0x2),
    ('step7/win11afterblindaudit.raw', 'LABE/e5_control_realzeros.bin', False, 12288, 0x01dd485de7522417, 0x1609748, '_selftest', 0x765, 0x0),
    ('step6/win11refs8g.raw', 'blabla/clean_1.txt', False, 208, 0x01dd0ad01b8938ed, 0x1a04348, 'host_001.txt', 0x752, 0x2),
    ('step6/win11refs8g.raw', 'blabla/clean_10.txt', False, 3016, 0x01dd0ad01b8938ed, 0x1a076c0, 'host_004.txt', 0x752, 0x5),
    ('step6/win11refs8g.raw', 'blabla/clean_11.txt', False, 3328, 0x01dd0ad01b8938ed, 0x1809c88, 'host_005.txt', 0x752, 0x6),
    ('step6/win11refs8g.raw', 'blabla/clean_12.txt', False, 3640, 0x01dd0ad01b8938ed, 0x1809e00, 'host_005.txt', 0x752, 0x6),
    ('step6/win11refs8g.raw', 'blabla/clean_13.txt', False, 3952, 0x01dd0ad01b8938ed, 0x1809f78, 'host_006.txt', 0x752, 0x7),
    ('step6/win11refs8g.raw', 'blabla/clean_14.txt', False, 4304, 0x01dd0ad01b8938ed, 0x180a0f0, 'host_006.txt', 0x752, 0x7),
    ('step6/win11refs8g.raw', 'blabla/clean_15.txt', False, 4616, 0x01dd0ad01b8938ed, 0x180a268, 'host_007.txt', 0x752, 0x8),
    ('step6/win11refs8g.raw', 'blabla/clean_16.txt', False, 4928, 0x01dd0ad01b8938ed, 0x180a3e0, 'host_007.txt', 0x752, 0x8),
    ('step6/win11refs8g.raw', 'blabla/clean_17.txt', False, 5240, 0x01dd0ad01b8938ed, 0x180a558, 'host_007.txt', 0x752, 0x8),
    ('step6/win11refs8g.raw', 'blabla/clean_18.txt', False, 5552, 0x01dd0ad01b8938ed, 0x180a6d0, 'host_008.txt', 0x752, 0x9),
    ('step6/win11refs8g.raw', 'blabla/clean_19.txt', False, 5864, 0x01dd0ad01b8938ed, 0x180a848, 'host_008.txt', 0x752, 0x9),
    ('step6/win11refs8g.raw', 'blabla/clean_2.txt', False, 520, 0x01dd0ad01b8938ed, 0x1a04900, 'host_001.txt', 0x752, 0x2),
    ('step6/win11refs8g.raw', 'blabla/clean_20.txt', False, 6176, 0x01dd0ad01b8938ed, 0x180ab38, 'host_009.txt', 0x752, 0xa),
    ('step6/win11refs8g.raw', 'blabla/clean_3.txt', False, 832, 0x01dd0ad01b8938ed, 0x1a04eb8, 'host_001.txt', 0x752, 0x2),
    ('step6/win11refs8g.raw', 'blabla/clean_4.txt', False, 1144, 0x01dd0ad01b8938ed, 0x1a05470, 'host_002.txt', 0x752, 0x3),
    ('step6/win11refs8g.raw', 'blabla/clean_5.txt', False, 1456, 0x01dd0ad01b8938ed, 0x1a05a28, 'host_002.txt', 0x752, 0x3),
    ('step6/win11refs8g.raw', 'blabla/clean_6.txt', False, 1768, 0x01dd0ad01b8938ed, 0x1a05fe0, 'host_003.txt', 0x752, 0x4),
    ('step6/win11refs8g.raw', 'blabla/clean_7.txt', False, 2080, 0x01dd0ad01b8938ed, 0x1a06598, 'host_003.txt', 0x752, 0x4),
    ('step6/win11refs8g.raw', 'blabla/clean_8.txt', False, 2392, 0x01dd0ad01b8938ed, 0x1a06b50, 'host_004.txt', 0x752, 0x5),
    ('step6/win11refs8g.raw', 'blabla/clean_9.txt', False, 2704, 0x01dd0ad01b8938ed, 0x1a07108, 'host_004.txt', 0x752, 0x5),
    ('step6/win11refs8g.raw', 'blabla/rangefile.bin', False, 1040, 0x01dd0ad01b8938ed, 0x1808598, 'host_002.txt', 0x752, 0x3),
    ('step6/win11refs8g.raw', 'forefst_test/clone_source.bin', False, 5656, 0x01dd0ad01b8938ed, 0x3e01f60, 'host_008.txt', 0x752, 0x9),
    ('step6/win11refs8g.raw', 'test/dir_record_449015/dir_papa_104235/dir_sync_718743/dir_gamma_109016/dir_config_541148/test_uniform_alpha_203203.json', False, 129216, 0x01dd0ad01b8938ed, 0x1210f08, 'multibig_12.bin', 0x753, 0xd),
    ('step6/win11refs8g.raw', 'test/dir_record_449015/dir_papa_104235/dir_sync_718743/dir_gamma_109016/dir_zulu_984398/dir_cache_558805', True, 159360, 0x01dd0ad01b8938ed, None, 'EFS0.LOG', 0x701, 0x1f),
    ('step6/win11refs8g.raw', 'test/dir_record_449015/test_india_delta_132534.bak', False, 149104, 0x01dd0ad01b8938ed, 0x4c14a68, 'junction1', 0x75b, 0x0),
    # S4 (the critic): labJjournal's m2 carries the FIRST id (0x01dd4e57f72ac89e) with LastUsn 256; the re-created
    # journal's USN 256 is m5's close record (0x706:0x8) -- the N196 witness itself (LAB-J's row, BJ.LABJ_ROWS)
    ('step7/labJjournal.raw', 'labJ/m2_after_recreate_same.txt', False, 256, 0x01dd4e57f72ac89e, 0x1400f20, 'm5_after_delete_create.txt', 0x706, 0x8),
]
S2_IDS = ["image-%s-%s" % (os.path.basename(c[0])[:-4], os.path.basename(c[1])[:40]) for c in S2_CASES]
# a directory's `details --json` is its object dump (named by OID, not by path): the directories' own OIDs (census)
S2_DIR_OID = {("step7/labG_2.raw", "LABA/dir2"): 0x70E, ("step7/win11afterblindaudit.raw", "LABA/dir2"): 0x70E,
              ("step6/win11refs8g.raw", S2_CASES[30][1]): 0x710}
# $J offset 0 (win11refs8g: one run up to vcn 7936; labJjournal: BJ.LABJ_M5_CLOSE - 256, the same cluster); else J_LABF
_J0 = {"step6/win11refs8g.raw": 0x83100000, "step7/labJjournal.raw": BJ.LABJ_M5_CLOSE - 0x100}


def _s2_premise(case):
    """From the bytes: the record that starts at the pointer's USN (its name and FileRef pinned) and, for a file, the
    type-0x30 row carrying the pointer and the pinned id. Returns that record (`_rec_at`), for R2's checks."""
    rel, path_in_vol, is_dir, usn, jid, row_off, rec_name, rec_oid, rec_idx = case
    img = _img(rel)
    with open(img, "rb") as fh:
        fh.seek(_J0.get(rel, J_LABF) + usn)
        rec = _rec_at(fh.read(0x1000), 0)
    _fx(rec is not None and rec[1] == usn and rec[5] == rec_name and rec[4] == (rec_oid, rec_idx),
        "%s: the record at USN %d is not %r 0x%x:0x%x (%r)" % (rel, usn, rec_name, rec_oid, rec_idx, rec))
    if not is_dir:
        _fx(_row_at(img, row_off, os.path.basename(path_in_vol)) == (usn, jid),
            "%s: the row of %s does not carry LastUsn %d with id 0x%016x" % (rel, path_in_vol, usn, jid))
    return rec


@pytest.mark.parametrize("fmt", ["text", "json"])
@pytest.mark.parametrize("case", S2_CASES, ids=S2_IDS)
def test_s2_guard_details_does_not_attach_another_files_record(case, fmt):
    """Not a RED: a guard (passes today, must keep passing). The file's LastUsn lands on a record of ANOTHER file
    (another name, another FileRef) written by the current journal / numbering; a join by USN would hand that
    record to this file. `details` prints the pointer and must never present that record as this file's: not its
    name, and (R2, the critic) not its FileRef, its time or its reason either (measured: none of them is in any of
    today's 66 outputs)."""
    rec = _s2_premise(case)
    rel, path_in_vol, _d, usn, _j, _o, rec_name, _ro, _ri = case
    args = ("details", "/" + path_in_vol) + (("--json",) if fmt == "json" else ())
    r = _run(rel, *args)
    text = "\n".join(r.prose)
    oid = S2_DIR_OID.get((rel, path_in_vol))
    named = os.path.basename(path_in_vol) in text or (oid is not None and '"oid": "0x%x"' % oid in text)
    _keep(r.rc == 0 and named, "details must still describe the object" + r.ctx(rel))
    _keep(re.search(r"(?i)(?<![0-9a-z])(?:%d|0x%x)(?![0-9a-z])" % (usn, usn), text) is not None,
          "details must still show the pointer %d" % usn + r.ctx(rel))
    assert rec_name.lower() not in text.lower(), (
        "%s: the record at USN %d belongs to %r (another file, another instance or numbering) and is attributed to "
        "this file" % (path_in_vol, usn, rec_name)) + r.ctx(rel)
    shown = _other_record_shown(text, rec)
    assert not shown, (
        "R2: %s: details prints %s of the record at USN %d, which belongs to %r (another file, another instance or "
        "numbering): a join by USN, without the name" % (path_in_vol, ", ".join(shown), usn, rec_name)) + r.ctx(rel)


@pytest.mark.parametrize("rel", list(D30), ids=D30_IDS)
def test_s2_guard_the_missing_range_is_measured_against_the_earlier_instances_own_records(rel):
    """Not a RED: a guard. The 1,654 pointers past the last record carry the EARLIER id, and the records they outrun
    are that instance's (the upper block): A10's range is 4,439,864 .. 5,119,752. A fix that compared them with the
    CURRENT journal's records (USN 0..X) would state a range from X -- never. S2 (the critic): the rule is the range
    measured from X (`_range_from_current_end`), not any 2-sentence window naming X and the pointer, which refused a
    correct boundary sentence followed by the tail sentence when its two halves were joined by a comma."""
    _d30_premise(rel)
    _n, x, x_end, _m, _y = D30[rel]
    r = _run(rel, "usn", "--info")
    s = _sentences(r.prose)
    assert AV._names_range(s), r.ctx(rel)
    wrong = _range_from_current_end(s, (x, x_end), POINTER, (OLD_LAST, OLD_LAST_END))
    assert not wrong, ("a missing range is measured from the current journal's end (%d) to the earlier instance's "
                       "pointer: %r" % (x_end, wrong[:1])) + r.ctx(rel)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N219 (+ S4) -- timestomp says where the journal starts and that earlier changes cannot be corroborated
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

MFT = "step5/win11refstestmftecmd.raw"
MFT_J0 = 0x1000000 + 99137 * CS           # $J vcn 0 (the first of the journal's extents: 452 clusters)
MFT_FIRST_TIME = "2026-05-23T07:38:44.286731Z"
MFT_ID = 0x01DCEA86B624A787              # 2026-05-23 07:35:21.664 (the id is the journal's creation FILETIME)
_MFT_PREMISE = []


def _mft_premise():
    """From the bytes: the journal's own USN 0 survives (nothing was overwritten), a FILE_CREATE of 'test2' at
    07:38:44.286731, 3 min 23 s after the id's time; the records of the first extent are one sequence."""
    if _MFT_PREMISE:
        return
    with open(_img(MFT), "rb") as fh:
        fh.seek(MFT_J0)
        recs = _carve(fh.read(452 * CS))
    _fx(recs and recs[0][1] == 0 and recs[0][5] == "test2" and recs[0][3] == 0x100
        and _at(recs[0][2], MFT_FIRST_TIME) and recs[0][2] > MFT_ID and not _steps(recs),
        "win11refstestmftecmd: $J USN 0 is not the FILE_CREATE of test2 at %s" % MFT_FIRST_TIME)
    _MFT_PREMISE.append(True)


# RED 1.13.2 N219: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("mode", ["text", "csv"], ids=["timestomp", "timestomp-csv-stderr"])
def test_n219_timestomp_states_where_the_journal_starts_on_image_win11refstestmftecmd(mode):
    _mft_premise()
    args = ("timestomp",) + (("--csv",) if mode == "csv" else ())
    r = _run(MFT, *args)
    _keep(r.rc == 0, "N219 moves no exit code (S4)" + r.ctx(MFT))
    if mode == "csv":
        _keep(r.header_line == TIMESTOMP_CSV_HEADER and r.nrows == 194, "timestomp --csv: header and 194 rows as "
              "today" + r.ctx(MFT))
    region = r.err.splitlines() if mode == "csv" else _header_region(r)
    s = _sentences(region)
    assert _start_stated(s, [(0, r"2026-05-23[ T]07:38:44")]), (
        "the coverage statement does not say the journal starts at USN 0, 2026-05-23 07:38:44 (its earliest surviving "
        "record)%s" % (" on stderr" if mode == "csv" else "")) + r.ctx(MFT)
    assert _before_uncovered(s), "nothing says that files changed before that start cannot be corroborated" \
        + r.ctx(MFT)


# S4 + T2 (settled by the lead 2026-10-09): on a wrapped journal the start is the LOWEST SURVIVING USN and its time
# (the USN order is the order of writes), never the journal id's time; where a clock step puts an earlier timestamp
# above it (winsider: USN 59,226,288 at 10:37:29), that record is not the start. When the journal's times step back,
# the statement says so: winsider 6 times, winsiderv2 2 times -- every backward step in USN order, any size (own
# carve, `_steps` and a 0 s threshold give the same count on both volumes; measured 2026-10-09).
N219_WRAPPED = {
    WS: ((WS_LOWEST, r"2026-05-11[ T]20:34:50"), r"2026-05-11[ T]20:33:59", r"2026-05-11[ T]10:37:29", 6),
    V2: ((V2_LOWEST, r"2026-09-19[ T]09:14:02"), r"2026-09-19[ T]07:42:16", None, 2),
}


# RED 1.13.2 N219: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("mode", ["text", "csv"], ids=["timestomp", "timestomp-csv-stderr"])
@pytest.mark.parametrize("rel", list(N219_WRAPPED), ids=["image-winsider", "image-winsiderv2"])
def test_n219_wrapped_journal_start_is_the_earliest_surviving_record(rel, mode):
    (_ws_premise if rel == WS else _v2_premise)()
    lowest, id_time, stepped_time, n_steps = N219_WRAPPED[rel]
    args = ("timestomp",) + (("--csv",) if mode == "csv" else ())
    r = _run(rel, *args)
    _keep(r.rc == 0 or (rel == V2 and r.rc == 2), "N219 moves no exit code (S4)" + r.ctx(rel))
    region = r.err.splitlines() if mode == "csv" else _header_region(r)
    s = _sentences(region)
    assert _start_stated(s, [lowest]), ("the coverage statement does not name the lowest surviving USN and its time "
                                        "(USN %d)" % lowest[0]) + r.ctx(rel)
    # N396 (LB5, the sanctioned change of this node, wave B part 3): the "cannot be corroborated before" clause now names
    # the EARLIEST surviving record's time (winsider 10:37:29), so the stepped-time check reads the sentences WITHOUT
    # that clause -- it asks that the earliest time is not given as the START, which the clause does not do; the
    # id-time check is unchanged
    s_wo = [x for x in s if x not in _before_uncovered(s)]
    for t, what, sents in ((id_time, "the journal id's creation time", s),
                           (stepped_time, "the earliest timestamp (a clock step, above the lowest USN)", s_wo)):
        assert t is None or not [w for w in _windows(sents, 2) if _START.search(w) and _JOURNAL.search(w)
                                 and re.search(t, w) and not re.search(lowest[1], w)], (
            "%s is given as the start; on a wrapped journal the start is the lowest surviving USN" % what) + r.ctx(rel)
    assert _steps_back_stated(s, n_steps), (
        "nothing says that the journal's times step back (%d times in USN order) and that times are as the clock "
        "recorded them" % n_steps) + r.ctx(rel)
    # R4 (the critic): winsider's clock steps are inside ONE wrapped sequence -- never a restart or an instance
    # boundary, here either (winsiderv2's re-creation IS stated: decision 31)
    # R-A (the re-check): nor in ST-1's own words, an earlier sequence (`_EARLIER_SEQ`)
    said = [ln for ln in region if _RESTART.search(ln) or _BOUNDARY.search(ln) or _EARLIER_SEQ.search(ln)]
    assert rel != WS or not said, (
        "winsider: one wrapped sequence whose clock steps back, yet the statement calls it a restart / names a journal "
        "instance boundary or an earlier sequence: %r" % said[:2]) + r.ctx(rel)
    # N396 (LB5, sanctioned): the clause names the earliest surviving record's time -- winsider's clock-step time
    # (10:37:29), or the lowest-USN record's time where no record is dated before it (winsiderv2)
    earliest = stepped_time or lowest[1]
    assert [c for c in _before_uncovered(s) if re.search(earliest, c)], (
        "nothing says that files changed before the earliest surviving record's time (%s) cannot be corroborated"
        % earliest) + r.ctx(rel)


# ST-1 (the lead, 2026-10-09): where the USN order shows a restart, coverage is stated PER SEQUENCE. The two sequences
# of each restart volume, from the bytes (own carve, `_n219_seq_premise`; inside each block every record is in time
# order, so its lowest USN is its earliest time): the current numbering's first record (USN 0) and last (USN, time);
# the earlier sequence's lowest USN and its time, its highest USN, that record's end and its time. Measured 2026-10-09.
N219_SEQ = {
    R8G: ("2026-07-05T06:54:51.092533Z", 173744, "2026-07-05T06:54:56.941848Z",
          176128, "2026-07-03T10:12:01.637487Z", 487944, 488048, "2026-07-03T11:05:40.459390Z"),
    "step7/labFafterreboot.raw": ("2026-09-20T06:53:53.162774Z", 128, "2026-09-20T06:53:53.162774Z",
                                  4096, "2026-09-20T06:22:33.010872Z", OLD_LAST, OLD_LAST_END,
                                  "2026-09-20T06:43:36.666897Z"),
    "step7/labG_0.raw": ("2026-09-20T06:53:53.162774Z", 11904, "2026-09-20T06:56:14.308515Z",
                         12288, "2026-09-20T06:22:36.364572Z", OLD_LAST, OLD_LAST_END, "2026-09-20T06:43:36.666897Z"),
    "step7/labG_1.raw": ("2026-09-20T06:53:53.162774Z", 13952, "2026-09-20T06:57:55.728945Z",
                         16384, "2026-09-20T06:31:02.654622Z", OLD_LAST, OLD_LAST_END, "2026-09-20T06:43:36.666897Z"),
    "step7/labG_2.raw": ("2026-09-20T06:53:53.162774Z", 15984, "2026-09-20T06:59:17.361856Z",
                         16384, "2026-09-20T06:31:02.654622Z", OLD_LAST, OLD_LAST_END, "2026-09-20T06:43:36.666897Z"),
    "step7/win11afterblindaudit.raw": ("2026-09-20T06:53:53.162774Z", 45504, "2026-09-20T19:13:04.058173Z",
                                       49152, "2026-09-20T06:42:59.406082Z", OLD_LAST, OLD_LAST_END,
                                       "2026-09-20T06:43:36.666897Z"),
    "step7/labC2.raw": ("2026-09-20T06:53:53.162774Z", 45504, "2026-09-20T19:13:04.058173Z",
                        49152, "2026-09-20T06:42:59.406082Z", OLD_LAST, OLD_LAST_END, "2026-09-20T06:43:36.666897Z"),
}
N219_SEQ_IDS = ["image-" + os.path.basename(k)[:-4] for k in N219_SEQ]
_SEQ_PREMISE = {}


def _n219_seq_premise(rel):
    """From the bytes: the volume's two numbering sequences are N219_SEQ[rel] -- the current one from USN 0 up to its
    pinned last record, the earlier one from its pinned lowest USN to its highest -- and neither steps back in time
    (so each one's lowest USN is its earliest time and its highest USN its latest)."""
    if rel in _SEQ_PREMISE:
        return
    if rel == R8G:
        _r8g_premise()
        j, _alloc = _read_j(_img(R8G), 0x1000000, R8G_EXT, nbytes=491520)
    else:
        _d30_premise(rel)
        with open(_img(rel), "rb") as fh:
            fh.seek(J_LABF)
            j = fh.read(OLD_LAST_END + 0x200)
    c0, cx, cxt, o0, o0t, ox, oxe, oxt = N219_SEQ[rel]
    recs = _carve(j)
    cur, old = [r for r in recs if r[1] < o0], [r for r in recs if r[1] >= o0]
    for blk in (cur, old):
        _fx(not [i for i in range(len(blk) - 1) if blk[i + 1][2] < blk[i][2]], "%s: a sequence steps back in time" % rel)
    _fx(cur[0][1] == 0 and _at(cur[0][2], c0) and cur[-1][1] == cx and _at(cur[-1][2], cxt),
        "%s: the current numbering is not USN 0 (%s) .. %d (%s)" % (rel, c0, cx, cxt))
    _fx(old[0][1] == o0 and _at(old[0][2], o0t) and old[-1][1] == ox and old[-1][1] + old[-1][0] == oxe
        and _at(old[-1][2], oxt), "%s: the earlier sequence is not USN %d (%s) .. %d (%s)" % (rel, o0, o0t, ox, oxt))
    _SEQ_PREMISE[rel] = True


# RED 1.13.2 N219: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("mode", ["text", "csv"], ids=["timestomp", "timestomp-csv-stderr"])
@pytest.mark.parametrize("rel", list(N219_SEQ), ids=N219_SEQ_IDS)
def test_n219_restart_volume_states_coverage_per_sequence(rel, mode):
    _n219_seq_premise(rel)
    c0, _cx, cxt, o0, o0t, ox, oxe, oxt = N219_SEQ[rel]
    args = ("timestomp",) + (("--csv",) if mode == "csv" else ())
    r = _run(rel, *args)
    if rel != R8G:
        _keep(r.rc == 2, "A10 keeps exit 2 on this volume" + r.ctx(rel))
    if mode == "csv":
        _keep(r.header_line == TIMESTOMP_CSV_HEADER, "timestomp --csv: header as today" + r.ctx(rel))
    region = r.err.splitlines() if mode == "csv" else _header_region(r)
    s = _sentences(region)
    assert _start_stated(s, [(0, _sec(c0))]), (
        "ST-1: the coverage statement does not say the current numbering starts at USN 0, %s%s" % (
            _sec(c0).replace("[ T]", " "), " on stderr" if mode == "csv" else "")) + r.ctx(rel)
    assert _span_stated(s, o0, _sec(o0t), (ox, oxe), oxt[11:19]), (
        "ST-1: nothing states the earlier sequence's surviving records with their span: USN %d .. %d, %s .. %s"
        % (o0, ox, _sec(o0t).replace("[ T]", " "), oxt[11:19])) + r.ctx(rel)
    gap = _gap_claimed(s, o0t[11:19], {c0[11:19], cxt[11:19]}, oxt[11:19])          # Q8: and open-ended claims
    assert not gap, ("ST-1: one span is given from the earlier sequence's first record to the current numbering: the "
                     "time between (%s .. %s) is not covered: %r" % (oxt[11:19], c0[11:19], gap[:1])) + r.ctx(rel)
    before = _before_current_start(s, c0[11:19], oxt[11:19])
    assert not before, ("ST-1: 'files changed before the current numbering's start (%s) cannot be corroborated', yet "
                        "the earlier sequence's records (from %s) survive: %r" % (c0[11:19], o0t[11:19], before[:1])) \
        + r.ctx(rel)


@pytest.mark.parametrize("mode", ["text", "csv"], ids=["timestomp", "timestomp-csv-stderr"])
@pytest.mark.parametrize("rel", ["step7/labFbeforereboot.raw", "step7/labBeforeF.raw"],
                         ids=["image-labFbeforereboot", "image-labBeforeF"])
def test_n219_control_one_numbering_sequence_states_one_span(rel, mode):
    """Not a RED: ST-1's control. The lineage before the reboot -- labFbeforereboot (43,771 records) and labBeforeF
    (440) -- holds ONE numbering sequence from USN 0 (own carve: never a step back in time), so timestomp's coverage
    statement names no earlier sequence and no restart: ST-1's per-sequence wording is keyed to the restart."""
    with open(_img(rel), "rb") as fh:
        fh.seek(J_LABF)
        recs = _carve(fh.read(OLD_LAST_END + 0x200))
    _fx(len(recs) in (43771, 440) and recs[0][1] == 0
        and not [i for i in range(len(recs) - 1) if recs[i + 1][2] < recs[i][2]], "%s: not one sequence from USN 0" % rel)
    r = _run(rel, *(("timestomp",) + (("--csv",) if mode == "csv" else ())))
    region = r.err.splitlines() if mode == "csv" else _header_region(r)
    assert not [w for w in _sentences(region) if _EARLIER_SEQ.search(w) or _RESTART.search(w)], r.ctx(rel)


@pytest.mark.parametrize("mode", ["text", "csv"], ids=["timestomp", "timestomp-csv-stderr"])
@pytest.mark.parametrize("rel", [MFT, "step7/labBeforeF.raw"], ids=["image-win11refstestmftecmd", "image-labBeforeF"])
def test_n219_control_a_journal_whose_times_never_step_back_states_no_step(rel, mode):
    """Not a RED. T2's statement is for a journal whose times step back. The whole journal of each volume (own carve:
    win11refstestmftecmd 9,371 records in its first extent, the census's total; labBeforeF 440 in its first 48 KiB)
    has no backward step at any size, so nothing may say its times step back."""
    if rel == MFT:
        _mft_premise()
        with open(_img(MFT), "rb") as fh:
            fh.seek(MFT_J0)
            recs = _carve(fh.read(452 * CS))
        _fx(len(recs) == 9371, "win11refstestmftecmd: not 9,371 records in the first extent")
    else:
        with open(_img(rel), "rb") as fh:
            fh.seek(J_LABF)
            recs = _carve(fh.read(0xC000))
        _fx(len(recs) == 440, "labBeforeF: not 440 records")
    _fx(not [i for i in range(len(recs) - 1) if recs[i + 1][2] < recs[i][2]], "%s: a backward time step" % rel)
    r = _run(rel, *(("timestomp",) + (("--csv",) if mode == "csv" else ())))
    region = r.err.splitlines() if mode == "csv" else _header_region(r)
    assert not [ln for ln in region if _STEP_BACK.search(ln)], r.ctx(rel)


BF = "step7/labBeforeF.raw"
BF_HIGH = ("LABA/dir1/beta_renamed.bin", "LABA/dir1/delta_control.bin", "LABA/dir1/eps_link_a.bin",
           "LABA/dir1/eps_link_b.bin", "LABA/dir1/gamma.bin")


def test_n219_control_journal_that_predates_the_stomps_keeps_its_corroborated_rows_on_image_labBeforeF():
    """Not a RED. labBeforeF: the journal (first record USN 0 at 06:19:11) holds the FILE_CREATE and the standalone
    BASIC_INFO_CHANGE records of the stomped files 0x70d:0x3-0x6 (own carve), although their $SI times read 2019:
    a time before the start is not a change before it. The 5 journal-corroborated HIGH rows stay, exit 0."""
    with open(_img(BF), "rb") as fh:
        fh.seek(J_LABF)
        recs = _carve(fh.read(0xC000))
    for idx in (3, 4, 5, 6):
        reasons = {r[3] for r in recs if r[4] == (0x70D, idx)}
        _fx(0x100 in reasons and 0x8000 in reasons, "labBeforeF: no FILE_CREATE + BASIC_INFO_CHANGE for 0x70d:0x%x"
            % idx)
    r = _exec(_img(BF), ("timestomp", "--csv"), keep_out=True)
    # acceptance 1.14.0 (N313, K21): the rows are read by their header (FullPath, Confidence, EvidenceRefs)
    rows = list(csv.DictReader(io.StringIO(r.out)))
    high = sorted(x["FullPath"] for x in rows if x.get("Confidence") == "HIGH" and "usn:" in (x.get("EvidenceRefs") or ""))
    assert r.rc == 0 and tuple(high) == BF_HIGH, r.ctx(BF) + "\nHIGH rows: %r" % high


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N368 -- bundle mode: pages listed in source_holes are holes of the source image (C8 = B)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

MOA = "step3/win11refs2tmillionsofactions.raw"
MOA_PS = 0x1000000
MOA_PAGES = (0x2F668C, 0x2FC300)          # two of the 14 whole-hole pages; the walk meets both (census 3.3)
MOA_CHKP = (0x51EB04, 0x3D702AC)          # checkpoint copies: their 4-cluster read lists 3 hole clusters, head stored
_BUNDLE_WHAT = "vbr,chkp,supb,btree"      # the parts the page walk reads; the 52 MB MLog area is left out


def _drop_dir(d):
    """Delete the files of a directory this module created, each by its exact path, then the directory."""
    if os.path.isdir(d):
        for n in os.listdir(d):
            p = os.path.join(d, n)
            if os.path.isdir(p):
                _drop_dir(p)
            else:
                os.unlink(p)
        os.rmdir(d)


def _export(src, d, name="bundle"):
    b = os.path.join(d, name)
    r = _exec(src, ("export", "metadata", b, "--what", _BUNDLE_WHAT), cwd=d)
    _fx(os.path.isfile(os.path.join(b, "manifest.json")), "export metadata wrote no manifest" + r.ctx("export"))
    size = sum(os.path.getsize(os.path.join(b, n)) for n in os.listdir(b))
    _fx(size < (64 << 20), "the bundle is %d bytes" % size)
    # acceptance 1.14.0 (E-2, K21): the manifest read as the bundle reader reads it -- its internal names and integers
    # (`read_bundle_manifest`; the written forms are test_1132_e2b_machine's)
    return b, AB.F.read_bundle_manifest(b)


@pytest.fixture(scope="module")
def moa_bundle():
    src = _img(MOA)
    for lcn in MOA_PAGES:
        _fx(BJ._is_hole(src, MOA_PS + lcn * CS, 4 * CS), "page 0x%x is not an image hole" % lcn)
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="g3_n368_", dir=SCRATCH)
    try:
        b, man = _export(src, d)
        listed = {h["lcn"] for h in man["source_holes"] if h["hole_bytes"] == h["clusters"] * CS}
        for lcn in MOA_PAGES:
            _fx(all(lcn + i in listed for i in range(4)), "the manifest does not list every cluster of 0x%x" % lcn)
        for lcn in MOA_CHKP:
            _fx(not BJ._is_hole(src, MOA_PS + lcn * CS, CS), "checkpoint 0x%x: the head cluster is a hole" % lcn)
        yield b, man
    finally:
        _drop_dir(d)


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["files", "summary", "integrity"])
def test_n368_image_bundle_pages_listed_in_source_holes_are_stated_as_holes_of_the_source_image(moa_bundle, cmd):
    b, _man = moa_bundle
    r = _exec(b, (cmd,), cwd=os.path.dirname(b))
    lines = r.prose
    _keep(r.rc == 2, "a page the volume needs, missing in a hole, keeps exit 2 (C8 = B)" + r.ctx("bundle " + cmd))
    _keep([ln for ln in lines if AB._lcn_re(MOA_PAGES[0]).search(ln)], "page 0x%x must still be named" % MOA_PAGES[0]
          + r.ctx("bundle " + cmd))
    assert [w for w in _hole_named(lines, MOA_PAGES[0]) if _SOURCE.search(w)], (
        "page 0x%x (every cluster listed in the manifest's source_holes): nothing says the source image stores it as "
        "a hole with the cause left open" % MOA_PAGES[0]) + r.ctx("bundle " + cmd)
    assert not [w for w in _line_windows(lines, MOA_PAGES[0], 1) if re.search(r"(?i)reads as all zeros on this "
                                                                            r"volume", w)], (
        "a source-image hole is called 'reads as all zeros on this volume'") + r.ctx("bundle " + cmd)
    # the critic's note N2, settled: C8 = B's hole sentence in every command, never FAIL -- integrity prints
    # "[FAIL] LCN 0x2f668c: Invalid signature: b'\x00\x00\x00\x00'" for a source-image hole today (both pages are)
    failed = [w for lcn in MOA_PAGES for w in _line_windows(lines, lcn, 1) if _FAIL_SIG.search(w)]
    assert not failed, ("a source-image hole is reported as FAILED (C8 = B: the hole sentence, never FAIL): %r"
                        % failed[:2]) + r.ctx("bundle " + cmd)
    # Q9 (the re-check; R1a's principle on the page lines, `_ALL_ZEROS` as the re-check names it): a source-image hole
    # page is never called "all zeros" either ("[WARN] LCN 0x2f668c: no page signature (all zeros)")
    zeros = [w for lcn in MOA_PAGES for w in _line_windows(lines, lcn, 1) if _ALL_ZEROS.search(w)]
    assert not zeros, ("a source-image hole page is called zeros: %r" % zeros[:2]) + r.ctx("bundle " + cmd)


@pytest.mark.parametrize("cmd", ["summary", "integrity"])
def test_n368_guard_image_bundle_pages_whose_head_is_stored_get_no_hole_sentence(moa_bundle, cmd):
    """Not a RED: a guard. The manifest also lists continuation clusters of pages whose head is stored (the census:
    on 108 of 112 volumes only such entries); the checkpoint copies' 4-cluster read lists 3 such clusters each. A
    fix keyed on 'some cluster listed' would call these readable copies holes -- never."""
    b, _man = moa_bundle
    r = _exec(b, (cmd,), cwd=os.path.dirname(b))
    for lcn in MOA_CHKP:
        # S3 (the critic, settled): a guard that reads no line naming the copy guards nothing -- today summary names
        # each copy in its CHKP row and WARN lines, integrity in its Checkpoint row and redundancy lines
        _keep([ln for ln in r.prose if AB._lcn_re(lcn).search(ln)], "S3: the checkpoint copy at LCN 0x%x must still be "
              "named" % lcn + r.ctx("bundle " + cmd))
        assert not [w for w in _line_windows(r.prose, lcn, 1) if _HOLE.search(w)], r.ctx("bundle " + cmd)


ZP_LCN = 0x1800                           # win11refsmini: the page of directory 0x70b ('plusrienneva', 3 files)


@pytest.fixture(scope="module")
def zero_page_bundle():
    """win11refsmini with the 16 KiB page at PLCN 0x1800 overwritten with WRITTEN zeros (not a hole), and its bundle."""
    base = _img(BASE)
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="g3_n368z_", dir=SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
        AB._carve(base, p)
        v = AB.Vol(AB.IMG, p)
        v.pin()
        pg = v.read(v.at(ZP_LCN), 0x4000)
        _fx(pg[:4] == b"MSB+" and "bat.txt".encode("utf-16-le") in pg, "PLCN 0x%x is not plusrienneva's page" % ZP_LCN)
        v.zero(v.at(ZP_LCN), 0x4000)
        _fx(not BJ._is_hole(p, v.at(ZP_LCN), 0x4000), "the zeroed page must stay WRITTEN")
        b, man = _export(p, d)
        _fx(not [h for h in man["source_holes"] if ZP_LCN <= h["lcn"] < ZP_LCN + 4], "the zeroed page is listed")
        yield b
    finally:
        _drop_dir(d)


def test_n368_control_image_a_page_that_is_really_zero_keeps_the_zeroed_page_wording(zero_page_bundle):
    """Not a RED. The trigger (a source-image hole) removed: the page reads zero because it IS zero in the source.
    'reads as all zeros on this volume' is right here; no hole sentence; exit 2."""
    r = _exec(zero_page_bundle, ("files",), cwd=os.path.dirname(zero_page_bundle))
    assert r.rc == 2, r.ctx("zero-page bundle files")
    assert [w for w in _line_windows(r.prose, ZP_LCN, 1) if re.search(r"(?i)reads as all zeros", w)], \
        r.ctx("zero-page bundle files")
    assert not _hole_named(r.prose, ZP_LCN) and not [w for w in _line_windows(r.prose, ZP_LCN, 1)
                                                     if _HOLE.search(w)], r.ctx("zero-page bundle files")


# ── N368's counts (the lead's settlement after the fixer stage, G3_CONTEXT "After the fixer stage", 2026-10-09) ──
# A count of pages is a count of DISTINCT pages, and each command states what it counted: "N distinct page(s) that
# this command read are wholly in the source image's holes"; `integrity`: "of the N pages the volume references". A
# page met by two walks counts once; the damage summary's "N metadata page(s) could not be read" counts distinct pages
# too. Measured 2026-10-09 (forefst in-process, the damage register's notes): on the millionsofactions bundle and on
# its image, `summary` records 20 notes naming 14 distinct pages (bootstrap's Object-Table walk meets 6 of them, the
# root-table counts meet all 14 again), `files` 6 notes naming the same 6, and `integrity` checks 809 referenced pages
# of which these 14 are wholly in holes (its walk records the 6).

MOA_HOLE_PAGES = (0x2F668C, 0x2FC300, 0x2F858C, 0x2FCC30, 0x2F81F4, 0x2FA9A8, 0x2FB5BC, 0x2FA370, 0x2FC938,
                  0x2FBDF4, 0x2FF918, 0x2F99B4, 0x2F8380, 0x6381C)   # census 3.3: the 14 whole-page holes
MOA_OT_HOLE_PAGES = (0x2F668C, 0x2F81F4, 0x2F858C, 0x2FA9A8, 0x2FC300, 0x2FCC30)   # met by bootstrap's walk
# the settled wording; "page(s)" or "pages"; the image's form says "the image's holes"
_DISTINCT_HOLES = re.compile(r"(\d+) distinct pages?(?:\(s\))? that this command read (?:are|is) wholly in the "
                             r"(source image's|image's) holes")
_DAMAGE_HEAD = re.compile(r"WARNING: (\d+) metadata page\(s\) could not be read")
_REFERENCED = re.compile(r"Pages in holes:\s+(\d+) of the (\d+) pages the volume references")
_PAGES_CHECKED = re.compile(r"^\s*Pages checked:\s+(\d+)\s*$")


@pytest.fixture(scope="module")
def moa_hole_premise(moa_bundle):
    """The 14 heads are whole holes of the image (4 clusters each, own SEEK_DATA) and the bundle's manifest lists every
    cluster of each in `source_holes` with all its bytes a hole."""
    src = _img(MOA)
    _b, man = moa_bundle
    listed = {h["lcn"] for h in man["source_holes"] if h["hole_bytes"] == h["clusters"] * CS}
    for lcn in MOA_HOLE_PAGES:
        _fx(BJ._is_hole(src, MOA_PS + lcn * CS, 4 * CS), "page 0x%x is not a whole hole of the image" % lcn)
        _fx(all(lcn + i in listed for i in range(4)), "the manifest does not list every cluster of 0x%x" % lcn)
    return True


N368C_WANT = {"summary": len(MOA_HOLE_PAGES), "files": len(MOA_OT_HOLE_PAGES), "integrity": len(MOA_HOLE_PAGES)}


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "files", "integrity"])
def test_n368_image_bundle_page_counts_are_distinct_pages_and_say_what_they_counted(moa_bundle, moa_hole_premise,
                                                                                      cmd):
    b, _man = moa_bundle
    r = _exec(b, (cmd,), cwd=os.path.dirname(b))
    _keep(r.rc == 2, "pages the volume needs, missing in holes, keep exit 2 (C8 = B)" + r.ctx("bundle " + cmd))
    text = "\n".join(r.prose)
    want = N368C_WANT[cmd]
    said = [(int(n), w) for n, w in _DISTINCT_HOLES.findall(text)]
    assert said == [(want, "source image's")], (
        "bundle %s: the damage summary must state %d distinct page(s) that this command read are wholly in the source "
        "image's holes (a page met twice counts once); it states %r" % (cmd, want, said)) + r.ctx("bundle " + cmd)
    head = [int(n) for n in _DAMAGE_HEAD.findall(text)]
    assert head == [want], ("bundle %s: 'N metadata page(s) could not be read' must count the %d distinct pages, "
                            "printed %r" % (cmd, want, head)) + r.ctx("bundle " + cmd)
    if cmd == "integrity":
        checked = [int(m.group(1)) for m in map(_PAGES_CHECKED.match, r.prose) if m]
        _fx(len(checked) == 1, "integrity prints one 'Pages checked' line: %r" % checked)
        ref = [(int(a), int(c)) for a, c in _REFERENCED.findall(text)]
        assert ref == [(len(MOA_HOLE_PAGES), checked[0])], (
            "integrity must state the scope of its count: 'Pages in holes: %d of the %d pages the volume references'; "
            "printed %r" % (len(MOA_HOLE_PAGES), checked[0], ref)) + r.ctx("bundle integrity")


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "files", "integrity"])
def test_n368_image_the_image_and_its_bundle_give_the_same_count_for_the_same_scope(moa_bundle, moa_hole_premise, cmd):
    b, _man = moa_bundle
    rb = _exec(b, (cmd,), cwd=os.path.dirname(b))
    ri = _run(MOA, cmd)
    want = N368C_WANT[cmd]
    on_b = [int(n) for n, _w in _DISTINCT_HOLES.findall("\n".join(rb.prose))]
    on_i = [(int(n), w) for n, w in _DISTINCT_HOLES.findall("\n".join(ri.prose))]
    assert on_i == [(want, "image's")], ("image %s: the damage summary must state %d distinct page(s) that this "
                                         "command read are wholly in the image's holes; it states %r"
                                         % (cmd, want, on_i)) + ri.ctx(MOA + " " + cmd)
    assert on_b == [n for n, _w in on_i], ("%s: the bundle states %r, the image %r -- the same pages, the same scope"
                                           % (cmd, on_b, on_i)) + rb.ctx("bundle " + cmd)


def _n368c_data_file(tmp_path, clusters):
    """A file whose clusters all hold data (0x01 bytes): a page handed to `_walk` as zeros is a page of WRITTEN zeros
    there (not an image hole), so each walk of it records one 'zeroed-page' note naming its head cluster."""
    p = str(tmp_path / "n368c_data.raw")
    with open(p, "wb") as fh:
        fh.write(b"\x01" * (clusters * 0x1000))
    return p


def _n368c_walk(monkeypatch, capsys, tmp_path, pages):
    """Walk each page of `pages` (lists of 4 slot clusters) as an all-zero page with the tool's own `_walk`; return the
    damage summary's text (stderr) and the escalation texts."""
    F = AB.F
    BJ._fresh(monkeypatch)
    monkeypatch.setattr(F, "_BUNDLE", None)
    p = _n368c_data_file(tmp_path, max(max(s) for s in pages) + 1)
    capsys.readouterr()
    with open(p, "rb") as fh:
        for slots in pages:
            _fx(F._walk(b"\0" * 0x4000, fh, 0, 0x1000, None, 3, None, list(slots)) == [], "a zero page gave rows")
    _fx({k for k, _d in F._WALK_DAMAGE} == {"zeroed-page"}, "kinds %r" % {k for k, _d in F._WALK_DAMAGE})
    F._walk_damage_summary()
    return capsys.readouterr().err, list(F._escalation_texts())


_N368C_KIND = re.compile(r"zeroed-page: (\d+) page")


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
def test_n368_a_page_met_by_two_walks_counts_once(monkeypatch, capsys, tmp_path):
    err, esc = _n368c_walk(monkeypatch, capsys, tmp_path, [(4, 5, 6, 7), (4, 5, 6, 7), (8, 9, 10, 11)])
    head = [int(n) for n in _DAMAGE_HEAD.findall(err)]
    kind = [int(n) for n in _N368C_KIND.findall(err)]
    _fx(len(head) == 1 and len(kind) == 1, "one summary and one kind line expected: %r" % err)
    assert head == [2], "two distinct pages, one met twice: the summary must say 2, it says %r\n%s" % (head, err)
    assert kind == [2], "the kind line must count 2 distinct pages, it says %r\n%s" % (kind, err)
    assert "2 metadata page(s) could not be read" in esc, "the escalation text must count 2 pages: %r" % esc


def test_n368_control_distinct_pages_are_each_counted(monkeypatch, capsys, tmp_path):
    """Not a RED: three distinct pages, each met once, are three pages (today and after the fix)."""
    err, esc = _n368c_walk(monkeypatch, capsys, tmp_path, [(4, 5, 6, 7), (8, 9, 10, 11), (12, 13, 14, 15)])
    assert [int(n) for n in _DAMAGE_HEAD.findall(err)] == [3], err
    assert [int(n) for n in _N368C_KIND.findall(err)] == [3], err
    assert "3 metadata page(s) could not be read" in esc, esc


# `files --csv FILE`: its two written-file lines carry the same count. The runner walks one all-zero page twice with
# the tool's own `_walk` (the page's four slots are the superblock cluster 0x1e of win11refsmini, which holds data, so
# the note is a 'zeroed-page' one, not a hole), then runs `files --csv FILE` through forefst.main() + rc_escalate.
_N368C_RUNNER = r'''
import os, sys
repo, img, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, repo)
import forefst
with open(img, "rb") as fh:
    for _i in range(int(os.environ["N368C_TIMES"])):
        forefst._walk(b"\0" * 0x4000, fh, 0x1000000, 0x1000, None, 3, None, [0x1E] * 4)
sys.argv = ["forefst.py", img, "files", "--csv", out]
try:
    _rc = forefst.main()
    sys.exit(forefst.rc_escalate(0 if _rc is None else _rc))
except SystemExit as _se:
    sys.exit(forefst.rc_escalate(0 if _se.code is None else _se.code))
'''
_N368C_FILES = re.compile(r"Wrote \d+ entr(?:y|ies) to .*? INCOMPLETE: (\d+) metadata page\(s\)/table\(s\) could not be read")


def _n368c_files(tmp_path, times):
    img = _img(BASE)
    runner, out = str(tmp_path / "n368c_runner.py"), str(tmp_path / "n368c.csv")
    with open(runner, "w") as fh:
        fh.write(_N368C_RUNNER)
    p = subprocess.run([sys.executable, "-B", runner, REPO, img, out], capture_output=True, timeout=TIMEOUT,
                       env=dict(os.environ, N368C_TIMES=str(times)))
    if os.path.exists(out):
        os.unlink(out)
    text = (p.stdout + p.stderr).decode("utf-8", "replace")
    _fx("Traceback" not in text, "the runner raised:\n" + text[-3000:])
    return p.returncode, text, [int(n) for n in _N368C_FILES.findall(text)], \
        [int(n) for n in _DAMAGE_HEAD.findall(text)]


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
def test_n368_files_written_file_line_counts_a_page_met_twice_once(tmp_path):
    rc, text, line, head = _n368c_files(tmp_path, 2)
    _fx(len(line) == 1 and len(head) == 1, "one files line and one summary line expected:\n" + text[-3000:])
    _keep(rc == 2, "a page that could not be read exits 2\n" + text[-3000:])
    assert line == [1], "files' line must count 1 distinct page, it says %r\n%s" % (line, text[-3000:])
    assert head == [1], "the summary must count 1 distinct page, it says %r\n%s" % (head, text[-3000:])


def test_n368_control_files_written_file_line_one_page_met_once(tmp_path):
    """Not a RED: the page met once is one page (today and after the fix)."""
    rc, text, line, head = _n368c_files(tmp_path, 1)
    assert rc == 2 and line == [1] and head == [1], (line, head, text[-3000:])


# ── the bundle-mode hole sentences that do not say "the source image" (G3_CONTEXT: the root-check wording at
# forefst.py ~1040; the class search adds the checkpoint-copy text for a page partly in a hole, and the page whose
# clusters are partly listed in `source_holes`) ──

def _n368c_chkp_raw(slots, stored=0x1234):
    """A checkpoint page with ONE root reference, root 0xC's, at +0x100: `slots`, CRC64 (type 2), a stored digest
    that is neither the sentinel nor the CRC of zeros. Roots 7 and 8 have no reference."""
    raw = bytearray(0x4000)
    raw[0:4] = b"CHKP"
    struct.pack_into("<I", raw, 0x5C, 0x30)                    # the reference length
    struct.pack_into("<I", raw, 0x78, 0)                       # flags: the root-offset table at +0x94
    struct.pack_into("<I", raw, 0x94 + 0xC * 4, 0x100)
    for i, s in enumerate(slots):
        struct.pack_into("<Q", raw, 0x100 + i * 8, s)
    raw[0x100 + 0x22] = 2
    struct.pack_into("<I", raw, 0x100 + 0x24, 8)
    struct.pack_into("<Q", raw, 0x100 + 0x28, stored)
    return bytes(raw)


def _n368c_bundle(monkeypatch, listed):
    """Bundle mode in-process: a manifest whose `source_holes` lists each cluster of `listed` as a whole hole."""
    monkeypatch.setattr(AB.F, "_BUNDLE", {"manifest": {"cluster_size": CS, "source_holes": [
        {"lcn": l, "clusters": 1, "hole_bytes": CS} for l in listed]}})


def _n368c_root_text(fh):
    out = AB.F._chkp_root_failures(fh, 0, CS, _n368c_chkp_raw([8, 9, 10, 11]))
    got = [w for i, w in out if i == 0xC]
    _fx(len(got) == 1, "root 0xC's check: %r" % out)
    return got[0]


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
def test_n368_bundle_root_check_hole_names_the_source_image(monkeypatch, tmp_path):
    p = _n368c_data_file(tmp_path, 12)
    with open(p, "r+b") as fh:                                 # the root page's clusters read as zeros
        fh.seek(8 * CS)
        fh.write(b"\0" * 4 * CS)
    _n368c_bundle(monkeypatch, range(8, 12))
    with open(p, "rb") as fh:
        t = _n368c_root_text(fh)
    assert _SOURCE.search(t) and _HOLE.search(t) and _HOLE_CAUSE.search(t), (
        "root 0xC's clusters are holes of the SOURCE image (the manifest lists them): its check must say so, with the "
        "cause left open: %r" % t)
    assert not re.search(r"(?i)\bimage hole\b", t), "the rehydrated image's hole is not the statement: %r" % t


def test_n368_control_root_check_outside_bundle_mode(monkeypatch, tmp_path):
    """Not a RED: outside bundle mode a root page in a hole of the image file gets the image's hole sentence (no
    'source'), and one of WRITTEN zeros gets no hole word at all (today and after the fix)."""
    monkeypatch.setattr(AB.F, "_BUNDLE", None)
    d = str(tmp_path)
    _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
    hole = os.path.join(d, "n368c_hole.raw")
    with open(hole, "wb") as fh:
        fh.write(b"\x01" * 8 * CS)
        fh.truncate(12 * CS)                                   # clusters 8-11: a hole of the file
    _fx(BJ._is_hole(hole, 8 * CS, 4 * CS), "clusters 8-11 are not a hole")
    with open(hole, "rb") as fh:
        t = _n368c_root_text(fh)
    assert _HOLE.search(t) and _HOLE_CAUSE.search(t) and not _SOURCE.search(t), t
    zero = _n368c_data_file(tmp_path, 12)
    with open(zero, "r+b") as fh:
        fh.seek(8 * CS)
        fh.write(b"\0" * 4 * CS)
    with open(zero, "rb") as fh:
        t = _n368c_root_text(fh)
    assert not _HOLE_WORDS.search(t) and re.search(r"(?i)does not match the digest", t), t


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
def test_n368_bundle_unreadable_checkpoint_copy_partly_in_a_hole_names_the_bundle(monkeypatch, tmp_path):
    d = str(tmp_path)
    _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
    p = os.path.join(d, "n368c_partial.raw")
    with open(p, "wb") as fh:
        fh.write(b"\x01" * 8 * CS + b"\0" * CS)                # cluster 8 written zeros
        fh.truncate(12 * CS)                                   # clusters 9-11 a hole
    _fx(BJ._is_hole(p, 9 * CS, 3 * CS) and not BJ._is_hole(p, 8 * CS, CS), "the plant is not as intended")
    _n368c_bundle(monkeypatch, [])
    with open(p, "rb") as fh:
        t = AB.F._chkp_unreadable_text(fh, 0, CS, 8, b"\0" * 4 * CS)
    assert re.search(r"(?i)\bbundle\b", t) and not re.search(r"(?i)\bthe image stores\b", t), (
        "in bundle mode the rehydrated image's hole is bytes the bundle does not carry: %r" % t)


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
def test_n368_bundle_page_partly_listed_in_source_holes_is_not_called_a_source_image_hole(monkeypatch, capsys,
                                                                                          tmp_path):
    F = AB.F
    BJ._fresh(monkeypatch)
    d = str(tmp_path)
    _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
    p = os.path.join(d, "n368c_mixed.raw")
    with open(p, "wb") as fh:
        fh.write(b"\x01" * 8 * CS)
        fh.truncate(12 * CS)                                   # clusters 8-11 a hole of the rehydrated file
    _n368c_bundle(monkeypatch, [8, 9, 10])                     # the manifest lists 8-10 only
    with open(p, "rb") as fh:
        _fx(F._walk(b"\0" * 0x4000, fh, 0, CS, None, 3, None, [8, 9, 10, 11]) == [], "a zero page gave rows")
    notes = list(F._WALK_DAMAGE)
    _fx(len(notes) == 1, "one note expected: %r" % notes)
    kind, detail = notes[0]
    assert not _SOURCE.search(detail) and re.search(r"(?i)\bbundle\b", detail), (
        "cluster 11 is not listed as a source-image hole: the page as a whole is bytes this bundle does not carry, "
        "not a hole of the source image: %r" % (notes[0],))


# `integrity --scan-range A-B` inspects each LCN as one standalone cluster (not a page): a scanned cluster in a hole is
# not "this page", and the count is of the clusters scanned. MOA_PAGES[0]'s four clusters, all in a hole.
_N368C_SCAN = ("integrity", "--scan-range", "0x%x-0x%x" % (MOA_PAGES[0], MOA_PAGES[0] + 4))


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
def test_n368_image_integrity_scan_range_names_clusters_not_pages(moa_hole_premise):
    r = _run(MOA, *_N368C_SCAN)
    holes = [ln for ln in r.prose if re.match(r"\s*\[HOLE\] LCN 0x", ln)]
    _fx(len(holes) == 4, "four [HOLE] lines expected: %r" % holes + r.ctx(MOA))
    assert not [ln for ln in holes if re.search(r"(?i)\bpage\b", ln)], (
        "a scanned LCN is one cluster, not a page: %r" % holes[:2]) + r.ctx(MOA)
    assert re.search(r"Pages in holes:\s+4 of the 4 clusters scanned", "\n".join(r.prose)), r.ctx(MOA)


# The class search (printed counts of pages, N368's rule; N336 widened's shape): `--verify-pages`' at-exit report counts
# the pages that did not match their parent's digest by the length of its list of examples, which stops at 32.

class _N368cExit(Exception):
    pass


def _n368c_verify_report(monkeypatch, capsys, n_bad):
    """`n_bad` distinct child pages that do not match the digest their parent records, through the tool's own
    `_verify_child_page`; then its at-exit report (its `os._exit(2)` replaced by an exception)."""
    F = AB.F
    monkeypatch.setattr(F, "_PAGE_VERIFY", {"checked": 0, "ok": 0, "bad": [], "no_digest": 0, "unreadable": 0,
                                            "_seen": set()})

    def _no_exit(code):
        raise _N368cExit(code)
    monkeypatch.setattr(F.os, "_exit", _no_exit)
    page = b"\x5a" * 0x4000
    for i in range(n_bad):
        vd = bytearray(0x30)
        struct.pack_into("<I", vd, 0x24, 8)
        struct.pack_into("<Q", vd, 0x28, 0x1000 + i)            # never the CRC64 of `page`
        _fx(F._verify_child_page(bytes(vd), page, "page %d" % i) is False, "a digest matched")
    capsys.readouterr()
    with pytest.raises(_N368cExit):
        F._report_page_verification()
    return capsys.readouterr().err


_N368C_BAD = re.compile(r"WARNING: (\d+) page\(s\) DID NOT match")
_N368C_MORE = re.compile(r"and (\d+) more")


# RED 1.13.2 N368: green with group 3's fix (the strict xfail mark removed)
def test_n368_verify_pages_counts_every_page_that_did_not_match(monkeypatch, capsys):
    err = _n368c_verify_report(monkeypatch, capsys, 40)
    _fx("0/40 metadata page(s) matched" in err, "the report does not count 40 checked pages:\n" + err)
    assert [int(n) for n in _N368C_BAD.findall(err)] == [40], (
        "40 distinct pages did not match their parent's digest; the report must say 40:\n" + err)
    assert [int(n) for n in _N368C_MORE.findall(err)] == [32], "8 are named, '... and 32 more':\n" + err


def test_n368_control_verify_pages_under_the_example_cap(monkeypatch, capsys):
    """Not a RED: 9 pages that did not match are 9 (today and after the fix)."""
    err = _n368c_verify_report(monkeypatch, capsys, 9)
    assert [int(n) for n in _N368C_BAD.findall(err)] == [9] and [int(n) for n in _N368C_MORE.findall(err)] == [1], err


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N374 -- a checkpoint copy whose page is an image hole: the hole sentence, not a zeroed copy or a corrupt pointer
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

N374_FORMS = [(FOREFST, ("files",)), (FOREFST, ("summary",)), (FOREFST, ("fastsummary",)),
              (FOREFST, ("integrity",)), (REFSANALYSIS, ("supb",)), (REFSANALYSIS, ("supb", "--verify")),
              (REFSANALYSIS, ("containers",))]
N374_IDS = ["fd-files", "fd-summary", "fd-fastsummary", "fd-integrity", "ra-supb", "ra-supb-verify", "ra-containers"]
# T1: the exit rule. The forms that exit 2 on all four plants today (forefst's bootstrap records a skip; ra `supb
# --verify` prints FAIL rows; ra `containers` the skip) -- kept; and the refsanalysis forms that exit 0 today -- REDs.
N374_EXIT2_TODAY = [f for f in N374_FORMS if f != (REFSANALYSIS, ("supb",))]
N374_RA_EXIT_FORMS = [(REFSANALYSIS, ("supb",)), (REFSANALYSIS, ("supb", "-v")), (REFSANALYSIS, ("chkp",)),
                      (REFSANALYSIS, ("chkp", "-v")), (REFSANALYSIS, ("chkp", "--verify")),
                      # T1b: the -vv forms of the representative surface (exit 0 on all four plants, measured)
                      (REFSANALYSIS, ("supb", "-vv")), (REFSANALYSIS, ("chkp", "-vv"))]
N374_RA_EXIT_IDS = ["ra-supb", "ra-supb-v", "ra-chkp", "ra-chkp-v", "ra-chkp-verify", "ra-supb-vv", "ra-chkp-vv"]
# T1b: the rest of decision 28's representative surface, not pinned above, which exits 2 on all four plants today
# (bootstrap records a skip and names the copy) -- controls
N374_EXIT2_MORE = [(FOREFST, ("search", "ok")), (FOREFST, ("timeline",)), (FOREFST, ("deleted",)),
                   (REFSANALYSIS, ("files",)), (REFSANALYSIS, ("summary",))]
N374_EXIT2_MORE_IDS = ["fd-search", "fd-timeline", "fd-deleted", "ra-files", "ra-summary"]
# T1: "never clocks read from zeros" -- the forms that print a clock for each copy the superblock lists
N374_CLOCK_FORMS = [(REFSANALYSIS, ("supb",)), (REFSANALYSIS, ("supb", "-v")), (REFSANALYSIS, ("supb", "--verify"))]
N374_CLOCK_IDS = ["ra-supb", "ra-supb-v", "ra-supb-verify"]
# T1a: "no field at all is decoded from a copy that has no CHKP signature" -- the forms the lead names
N374_FIELD_FORMS = [(REFSANALYSIS, ("supb",)), (REFSANALYSIS, ("supb", "-v")), (REFSANALYSIS, ("supb", "-vv")),
                    (REFSANALYSIS, ("chkp",)), (REFSANALYSIS, ("chkp", "-v")), (REFSANALYSIS, ("chkp", "-vv"))]
N374_FIELD_IDS = ["ra-supb", "ra-supb-v", "ra-supb-vv", "ra-chkp", "ra-chkp-v", "ra-chkp-vv"]
# every form the plants (and the base control) run: T1b's 18
N374_ALL_FORMS = N374_FORMS + [f for f in N374_RA_EXIT_FORMS if f not in N374_FORMS] + N374_EXIT2_MORE
_N374_FORM_ID = dict(zip(N374_FORMS + N374_RA_EXIT_FORMS + N374_EXIT2_MORE,
                         N374_IDS + N374_RA_EXIT_IDS + N374_EXIT2_MORE_IDS))
N374_ALL_IDS = [_N374_FORM_ID[f] for f in N374_ALL_FORMS]
N374_PLANTS = ["hole_lo", "hole_hi", "zero_lo", "zero_hi"]
N374_PLANT_IDS = ["image-" + p for p in N374_PLANTS]
# the copy each plant leaves in use, and its clock (+0x10 == +0x60): lo planted -> 0xee34 (63), hi -> 0x13f8 (64)
N374_SURVIVOR = {"lo": (0xEE34, 63), "hi": (0x13F8, 64)}
_N374 = {}


def _n374(plant):
    """Build the plant on a fresh hole-preserving copy of win11refsmini, run every form once, delete the copy.
    hole_lo / hole_hi: the copy's 16 KiB left as a hole (BJ._carve_except, the critic's recipe); zero_lo / zero_hi:
    the same range written as zeros. lo = LCN 0x13f8 (the newer copy, 64), hi = LCN 0xee34 (63)."""
    if plant in _N374:
        return _N374[plant]
    base = _img(BASE)
    lcn = AB.IMG.lo if plant.endswith("_lo") else AB.IMG.hi
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="g3_n374_", dir=SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
        AB._carve(base, p)
        AB.Vol(AB.IMG, p).pin()                              # the base is what the case needs, before the plant
        os.unlink(p)
        if plant.startswith("hole"):
            BJ._carve_except(base, p, [(AB.IMG.ps + lcn * CS, 0x4000)])
            _fx(BJ._is_hole(p, AB.IMG.ps + lcn * CS, 0x4000), "the copy is not a hole")
        else:
            AB._carve(base, p)
            AB.Vol(AB.IMG, p).zero(AB.IMG.ps + lcn * CS, 0x4000)
            _fx(not BJ._is_hole(p, AB.IMG.ps + lcn * CS, 0x4000), "the zeroed copy must stay WRITTEN")
        other = AB.IMG.hi if lcn == AB.IMG.lo else AB.IMG.lo
        with open(p, "rb") as fh:
            fh.seek(AB.IMG.ps + other * CS)
            _fx(fh.read(4) == b"CHKP", "the other checkpoint copy is not intact")
        outs = {}
        for tool, args in N374_ALL_FORMS:
            r = _exec(p, args, tool=tool, cwd=d)
            outs[(tool, args)] = r
        _N374[plant] = (lcn, outs)
        return _N374[plant]
    finally:
        if os.path.exists(p):
            os.unlink(p)
        os.rmdir(d)


# RED 1.13.2 N374: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("form", N374_FORMS, ids=N374_IDS)
@pytest.mark.parametrize("plant", ["hole_lo", "hole_hi"], ids=["image-hole_lo", "image-hole_hi"])
def test_n374_checkpoint_copy_in_an_image_hole_is_worded_with_the_hole_sentence(plant, form):
    lcn, outs = _n374(plant)
    r = outs[form]
    lines = r.prose
    _keep(AB._lines("\n".join(lines), lcn), "the copy at LCN 0x%x must still be named" % lcn + r.ctx(plant))
    if form in N374_EXIT2_TODAY:
        _keep(r.rc == 2, "T1: an unreadable checkpoint copy exits 2 in every command (this form already does)"
              + r.ctx(plant))
    assert _hole_named(lines, lcn), ("LCN 0x%x: nothing says the image stores this checkpoint copy as a hole, with the "
                                     "cause left open (not captured, or zero on the disk)" % lcn) + r.ctx(plant)
    assert not [w for w in _line_windows(lines, lcn, 2) if _POINTER_BLAME.search(w)], (
        "a hole is blamed on the superblock's checkpoint pointer") + r.ctx(plant)
    # R1a (the critic): the hole sentence on one line while another still calls the copy "all zeros" is not the fix
    zeros = _n374_contra(plant, lines, lcn)
    assert not zeros, ("R1a: LCN 0x%x is an image hole, yet a passage at its lines calls it 'all zeros': %r"
                       % (lcn, zeros[:1])) + r.ctx(plant)


@pytest.mark.parametrize("form", N374_FORMS, ids=N374_IDS)
@pytest.mark.parametrize("plant", ["zero_lo", "zero_hi"], ids=["image-zero_lo", "image-zero_hi"])
def test_n374_control_a_zeroed_checkpoint_copy_is_not_called_a_hole(plant, form):
    """Not a RED. The same range WRITTEN as zeros (the trigger, an image hole, removed): the copy is still named and
    no line calls it a hole. Today the outputs are byte-identical to the hole plants' (the G2c2 critic K-5). T1: a
    zeroed copy cannot be read either, and the forms that exit 2 today keep it (plain asserts: they pass now)."""
    lcn, outs = _n374(plant)
    r = outs[form]
    assert AB._lines("\n".join(r.prose), lcn), r.ctx(plant)
    # R-B (the re-check): no hole word, and not the tool's own hole labels either ("acquisition gap", "absent from the
    # image", "not captured" -- `_HOLE_WORDS`)
    assert not [w for w in _line_windows(r.prose, lcn, 2) if _HOLE_WORDS.search(w)], r.ctx(plant)
    if form in N374_EXIT2_TODAY:
        assert r.rc == 2, "T1: a checkpoint copy of all zeros exits 2 in every command" + r.ctx(plant)


def _n374_contra(plant, lines, lcn):
    """R1a / R1b (the critic): the passages at the copy's lines that word it as the OTHER kind -- "all zeros" for an
    image hole (the image holds no zeros there), a hole word for a copy of written zeros. The fixer's first step (the
    re-check): Q10 -- "zero-filled", "zeroed", "only zero bytes" for a hole too (`_ZEROS_SAID`; never a bare "zero":
    C8 = B's sentence says "zero on the disk"); R-B -- for written zeros, also the tool's own hole labels ("absent from
    the image (acquisition gap, not damage)", "not captured"; `_HOLE_WORDS`)."""
    other = _ZEROS_SAID if plant.startswith("hole") else _HOLE_WORDS
    return [w for w in _line_windows(lines, lcn, 2) if other.search(w)]


def _n374_stated(plant, lines, lcn):
    """T1's wording, on the lines naming the copy: C8 = B's hole sentence for a hole plant, "all zeros" for a zero one;
    and (R1a / R1b) no passage at those lines words it as the other kind -- so one generic "no CHKP signature (all
    zeros); the image may store it as a hole" sentence states neither."""
    if _n374_contra(plant, lines, lcn):
        return []
    if plant.startswith("hole"):
        return _hole_named(lines, lcn)
    return [w for w in _line_windows(lines, lcn, 2) if _ALL_ZEROS.search(w)]


def _n374_unstated(plant, lines, lcn):
    """The failure text of `_n374_stated`: what is missing, and the contradicting passage when there is one."""
    want = "C8 = B's hole sentence" if plant.startswith("hole") else "'all zeros'"
    contra = _n374_contra(plant, lines, lcn)
    if contra:
        return "%s, but a passage at its lines words it as %s: %r" % (
            want, "all zeros (R1a)" if plant.startswith("hole") else "a hole (R1b)", contra[:1])
    return want


# RED 1.13.2 N374: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("form", N374_RA_EXIT_FORMS, ids=N374_RA_EXIT_IDS)
@pytest.mark.parametrize("plant", N374_PLANTS, ids=N374_PLANT_IDS)
def test_n374_unreadable_checkpoint_copy_exits_2_in_every_command(plant, form):
    lcn, outs = _n374(plant)
    r = outs[form]
    other, clock = N374_SURVIVOR[plant[-2:]]
    _keep(re.search(r"(?i)(?:\bvc=|\bvirtual clock\b[^\n]*?)(?<![0-9])%d(?![0-9])" % clock, "\n".join(r.prose)),
          "the view must still be read from the other copy (LCN 0x%x, clock %d)" % (other, clock) + r.ctx(plant))
    assert r.rc == 2, ("T1: the checkpoint copy at LCN 0x%x cannot be read (%s), yet %s exits %d"
                       % (lcn, "an image hole" if plant.startswith("hole") else "all zeros",
                          " ".join(("refsanalysis",) + form[1]), r.rc)) + r.ctx(plant)
    assert _n374_stated(plant, r.prose, lcn), (
        "the exit 2 is not explained: nothing names the copy at LCN 0x%x with %s" % (
            lcn, _n374_unstated(plant, r.prose, lcn))) + r.ctx(plant)


# RED 1.13.2 N374: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("form", N374_CLOCK_FORMS, ids=N374_CLOCK_IDS)
@pytest.mark.parametrize("plant", N374_PLANTS, ids=N374_PLANT_IDS)
def test_n374_no_clock_is_read_from_an_unreadable_checkpoint_copy(plant, form):
    lcn, outs = _n374(plant)
    r = outs[form]
    _keep(AB._lines("\n".join(r.prose), lcn), "the copy at LCN 0x%x must still be named" % lcn + r.ctx(plant))
    zero = [w for w in _line_windows(r.prose, lcn, 2) if _ZERO_CLOCK.search(w)]
    assert not zero, ("LCN 0x%x has no signature and no clock, yet a clock of 0 is printed for it: %r"
                      % (lcn, zero[:1])) + r.ctx(plant)


# RED 1.13.2 N374: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("form", N374_FIELD_FORMS, ids=N374_FIELD_IDS)
@pytest.mark.parametrize("plant", N374_PLANTS, ids=N374_PLANT_IDS)
def test_n374_no_field_is_decoded_from_an_unreadable_checkpoint_copy(plant, form):
    lcn, outs = _n374(plant)
    r = outs[form]
    other, clock = N374_SURVIVOR[plant[-2:]]
    what = "an image hole" if plant.startswith("hole") else "all zeros"
    cmd = " ".join(("refsanalysis",) + form[1])
    if form[1][0] == "supb":
        _keep(AB._lines("\n".join(r.prose), lcn), "the superblock's reference to the copy at LCN 0x%x must still be "
              "listed" % lcn + r.ctx(plant))
    else:
        _keep(_chkp_decodes(r.prose, other, clock), "chkp must still decode the copy in use (LCN 0x%x, clock %d), "
              "never the unreadable one" % (other, clock) + r.ctx(plant))
    fields = _copy_fields(r.prose, lcn, other)
    assert not fields, ("T1a: the checkpoint copy at LCN 0x%x has no CHKP signature (%s), yet %s decodes fields from "
                        "it: %r" % (lcn, what, cmd, fields)) + r.ctx(plant)
    assert _n374_stated(plant, r.prose, lcn), (
        "T1a: %s does not report the checkpoint copy at LCN 0x%x as unreadable (%s)" % (
            cmd, lcn, _n374_unstated(plant, r.prose, lcn))) + r.ctx(plant)


@pytest.mark.parametrize("form", N374_FIELD_FORMS, ids=N374_FIELD_IDS)
def test_n374_control_the_intact_base_decodes_the_real_checkpoint_fields(form):
    """Not a RED: the control of T1a's REDs. On the unplanted base (read-only; pinned first) both copies carry their
    signature and the fields these forms decode are the real ones: supb / -v / -vv print each listed copy's own clock
    in that copy's passage (LCN 0x13f8: vc=64, LCN 0xee34: vc=63), -v / -vv its version (ver=3.14); chkp / -v / -vv
    decode the newest copy (LCN 0x13f8, offset 0x23f8000, virtual clock 64). So the copy passages and the field
    matcher read what these forms print, and the REDs are keyed to the plant."""
    AB.Vol(AB.IMG, _img(BASE)).pin()
    tool, args = form
    r = _run(BASE, *args, tool=tool)
    if args[0] == "supb":
        for lcn, other, clock in ((AB.IMG.lo, AB.IMG.hi, AB.CLOCK_NEW), (AB.IMG.hi, AB.IMG.lo, AB.CLOCK_OLD)):
            fields = _copy_fields(r.prose, lcn, other)
            assert [f for f in fields if re.fullmatch(r"(?i)vc\s*=\s*%d" % clock, f)], (
                "LCN 0x%x: no vc=%d in its passage: %r" % (lcn, clock, fields)) + r.ctx(BASE)
            if len(args) > 1:
                assert [f for f in fields if re.fullmatch(r"(?i)ver\s*=\s*3\.14", f)], (
                    "LCN 0x%x: no ver=3.14 in its passage: %r" % (lcn, fields)) + r.ctx(BASE)
    else:
        assert _chkp_decodes(r.prose, AB.IMG.lo, AB.CLOCK_NEW), r.ctx(BASE)
        assert [ln for ln in r.prose if re.match(r"(?i)\s*virtual clock\b", ln) and _FIELD_VALUE.search(ln)], \
            r.ctx(BASE)


@pytest.mark.parametrize("form", N374_EXIT2_MORE, ids=N374_EXIT2_MORE_IDS)
@pytest.mark.parametrize("plant", N374_PLANTS, ids=N374_PLANT_IDS)
def test_n374_control_an_unreadable_checkpoint_copy_already_exits_2_in_these_commands(plant, form):
    """Not a RED: T1b's control. The forms of decision 28's representative surface that no node above pins --
    forefst `search`, `timeline`, `deleted`, ra `files`, `summary` -- already exit 2 on all four plants (bootstrap
    records a skip that names the copy) and must keep doing so. The base exits 0 in each (the control below)."""
    lcn, outs = _n374(plant)
    r = outs[form]
    assert r.rc == 2, "T1: an unreadable checkpoint copy exits 2 in every command" + r.ctx(plant)
    assert AB._lines("\n".join(r.prose), lcn), "the exit 2 has no reason: the copy at LCN 0x%x is not named" % lcn \
        + r.ctx(plant)


@pytest.mark.parametrize("form", N374_ALL_FORMS, ids=N374_ALL_IDS)
def test_n374_control_the_intact_base_exits_0_and_prints_both_copies_clocks(form):
    """Not a RED: the control of T1's REDs. The unplanted base (step1/win11refsmini.raw, read-only; pinned first)
    exits 0 in every form the plants run (T1b's 18), and the forms that print each listed copy's clock print the real
    ones (LCN 0x13f8: 64, LCN 0xee34: 63) -- so the exit REDs and controls are keyed to the plant and the zero-clock
    matcher reads the clock these forms print."""
    AB.Vol(AB.IMG, _img(BASE)).pin()
    tool, args = form
    r = _run(BASE, *args, tool=tool)
    assert r.rc == 0, r.ctx(BASE)
    if form in N374_CLOCK_FORMS:
        for lcn, clock in ((AB.IMG.lo, AB.CLOCK_NEW), (AB.IMG.hi, AB.CLOCK_OLD)):
            win = _line_windows(r.prose, lcn, 2)
            assert [w for w in win if re.search(_CLOCK_VALUE % clock, w)], r.ctx(BASE)
            assert not [w for w in win if _ZERO_CLOCK.search(w)], r.ctx(BASE)


# S6 (the lead, 2026-10-09): a zeroed checkpoint copy is "all zeros" with no cause in EVERY form that prints it, forefst
# and refsanalysis. Measured on cbb888e8 / 2ec2ab8c (the t1ab probe, both zero plants): 14 of T1b's 18 forms name the
# copy (ra chkp / -v / -vv / --verify describe only the copy in use: T1a's report half covers them); forefst's
# bootstrap / checkpoint-skip message ("... got b'\x00\x00\x00\x00'. The superblock's checkpoint pointer may be corrupt")
# reaches 10 of them (every forefst form, ra files / summary / containers); "all zeros" is said only by summary,
# fastsummary, integrity and ra summary ([WARN] ... no CHKP signature: all zeros).
N374_S6_FORMS = [f for f in N374_ALL_FORMS if f[1][0] != "chkp"]
N374_S6_IDS = [_N374_FORM_ID[f] for f in N374_S6_FORMS]


# RED 1.13.2 N374: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("form", N374_S6_FORMS, ids=N374_S6_IDS)
@pytest.mark.parametrize("plant", ["zero_lo", "zero_hi"], ids=["image-zero_lo", "image-zero_hi"])
def test_n374_s6_zeroed_checkpoint_copy_is_all_zeros_with_no_cause(plant, form):
    lcn, outs = _n374(plant)
    r = outs[form]
    lines = r.prose
    _keep(AB._lines("\n".join(lines), lcn), "the copy at LCN 0x%x must still be named" % lcn + r.ctx(plant))
    assert [w for w in _line_windows(lines, lcn, 2) if _ALL_ZEROS.search(w)], (
        "S6: LCN 0x%x is written zeros, yet no passage at its lines says 'all zeros'" % lcn) + r.ctx(plant)
    cause = [w for w in _line_windows(lines, lcn, 2) if _cause_named(w)]
    assert not cause, ("S6: LCN 0x%x is all zeros, which shows no cause, yet a passage at its lines blames the "
                       "superblock's pointer: %r" % (lcn, cause[:1])) + r.ctx(plant)
    assert not _n374_contra(plant, lines, lcn), ("R1b: LCN 0x%x is written zeros, yet a passage at its lines calls it "
                                                 "a hole: %r" % (lcn, _n374_contra(plant, lines, lcn)[:1])) + r.ctx(plant)


# RED 1.13.2 N374: green with group 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("form", N374_EXIT2_MORE, ids=N374_EXIT2_MORE_IDS)
@pytest.mark.parametrize("plant", ["hole_lo", "hole_hi"], ids=["image-hole_lo", "image-hole_hi"])
def test_n374_s6_hole_copy_keeps_the_hole_sentence_in_the_other_forms_that_print_it(plant, form):
    lcn, outs = _n374(plant)
    r = outs[form]
    lines = r.prose
    _keep(AB._lines("\n".join(lines), lcn), "the copy at LCN 0x%x must still be named" % lcn + r.ctx(plant))
    _keep(r.rc == 2, "T1: an unreadable checkpoint copy exits 2 in every command (this form already does)" + r.ctx(plant))
    assert _hole_named(lines, lcn), ("LCN 0x%x: nothing says the image stores this checkpoint copy as a hole, with the "
                                     "cause left open (not captured, or zero on the disk)" % lcn) + r.ctx(plant)
    cause = [w for w in _line_windows(lines, lcn, 2) if _cause_named(w)]
    assert not cause, "a hole is blamed on the superblock's pointer: %r" % cause[:1] + r.ctx(plant)
    zeros = _n374_contra(plant, lines, lcn)
    assert not zeros, ("R1a: LCN 0x%x is an image hole, yet a passage at its lines calls it 'all zeros': %r"
                       % (lcn, zeros[:1])) + r.ctx(plant)


@pytest.mark.parametrize("form", N374_S6_FORMS, ids=N374_S6_IDS)
def test_n374_s6_control_the_intact_base_names_no_zeros_no_cause_and_no_hole(form):
    """Not a RED: S6's control. On the unplanted base (read-only; pinned first) both copies carry their signature: no
    passage at either copy's lines says 'all zeros', blames a pointer or uses a hole word, in the 14 forms -- so the S6
    REDs are keyed to the plant, and a fix that words every copy as all zeros is refused."""
    AB.Vol(AB.IMG, _img(BASE)).pin()
    tool, args = form
    r = _run(BASE, *args, tool=tool)
    for lcn in (AB.IMG.lo, AB.IMG.hi):
        bad = [w for w in _line_windows(r.prose, lcn, 2) if _ALL_ZEROS.search(w) or _cause_named(w) or _HOLE.search(w)]
        assert not bad, "LCN 0x%x: %r" % (lcn, bad[:1]) + r.ctx(BASE)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A10-DOC part 2 -- the proof script (a PROOF node, not a RED)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# Expected values: re-measured 2026-10-09 by the script itself, and checked against E2_RC2_CLASSIFICATION.md (C10,
# RV [V11]), NEXT_STEPS_2026-10-01.md (side analysis) and GROUP3_CENSUS.md (see RED_group3.md for the comparison).
A10DOC = {
    "step7/labBeforeF.raw": dict(
        records_in_j=440, first=(0, "2026-09-20T06:19:11.035841Z"), last=(47824, "2026-09-20T06:37:09.701319Z", 47952),
        hi_ptr=47584, hi_ptr_id="0x01dd485de7522417", past=(0, 0, None), zero=[47952, 35241984],
        hole=[49152, 35241984]),
    "step7/labFbeforereboot.raw": dict(
        records_in_j=43771, first=(0, "2026-09-20T06:19:11.035841Z"),
        last=(4439864, "2026-09-20T06:43:36.666897Z", 4439968), hi_ptr=4462624, hi_ptr_id="0x01dd485de7522417",
        past=(56, 56, ["2026-09-20T06:43:36.666897Z", "2026-09-20T06:43:36.822607Z"]), zero=[4439968, 35241984],
        hole=[4440064, 35241984]),
    "step7/labFafterreboot.raw": dict(
        records_in_j=43736, first=(0, "2026-09-20T06:53:53.162774Z"),
        last=(4439864, "2026-09-20T06:43:36.666897Z", 4439968), hi_ptr=5119752, hi_ptr_id="0x01dd485de7522417",
        past=(1716, 1654, ["2026-09-20T06:43:36.666897Z", "2026-09-20T06:43:41.775951Z"]),
        zero=[4439968, 35241984], hole=[4440064, 35241984]),
}
# T3 (settled by the lead 2026-10-09): the highest per-file pointer WITH ITS SCOPE. `live` = the live tree, the pages
# reachable from the checkpoint copy in use (copy LCN, its +0x60, pages walked, objects): the highest pointer there,
# its journal id, the rows / names past the last record. `outside` = the page copies OUTSIDE the live tree: the highest
# pointer they carry, its id, the rows past the last record and the page copies holding them. On labFbeforereboot the
# claim cites the live tree's 4,084,440 (the metadata the volume and the tool read); the 28 page copies outside it,
# whose 56 rows point up to 4,462,624, are stated separately with that scope. `hi_ptr` above stays the maximum over
# every copy. Measured 2026-10-09 by the script; its live page set equals forefst's own `_walk_btree_pages` over every
# checkpoint root and every Object-Table object on all three images (65 / 902 / 1,335 pages, 0 different; a one-off
# check outside the script and the tests, RED_group3.md).
# ST-2 (settled by the lead 2026-10-09): `relation` = how those outside copies' past-tail rows relate to the live tree,
# measured by the script: (relation, names, names in the live tree, names there with an equal or higher pointer,
# Changed range, the live tree's latest Changed, page clocks). On labFbeforereboot they were WRITTEN AFTER THE
# CHECKPOINT IN USE, NOT YET PART OF ITS TREE (none of their names in it; Changed after its latest; page clock 3986 =
# the copy in use's +0x60); on labFafterreboot the same 28 copies are SUPERSEDED (the replayed live tree holds all 56
# names with an equal or higher pointer).
A10DOC_SCOPED = {
    "step7/labBeforeF.raw": dict(
        live=((10356, 3975, 65, 30), 47584, "0x01dd485de7522417", 0, 0),
        outside=(47584, "0x01dd485de7522417", 0, 0), live_past_pages=0,
        relation=(None, 0, 0, 0, None, "2026-09-20T06:35:30.964287Z", None)),
    "step7/labFbeforereboot.raw": dict(
        live=((123892, 3986, 902, 96), 4084440, "0x01dd485de7522417", 0, 0),
        outside=(4462624, "0x01dd485de7522417", 56, 28), live_past_pages=0,
        relation=("written_after_checkpoint", 56, 0, 0, ["2026-09-20T06:43:36.666897Z", "2026-09-20T06:43:36.822607Z"],
                  "2026-09-20T06:43:33.534930Z", [3986, 3986])),
    "step7/labFafterreboot.raw": dict(
        live=((10356, 4002, 1335, 96), 5119752, "0x01dd485de7522417", 1660, 1654),
        outside=(4462624, "0x01dd485de7522417", 56, 28), live_past_pages=894,
        relation=("superseded", 56, 56, 56, ["2026-09-20T06:43:36.666897Z", "2026-09-20T06:43:36.822607Z"],
                  "2026-09-20T06:43:41.775951Z", [3986, 3986])),
}
# USN wrap (reading 1: USN = $J offset only until the journal wraps, RefsFileOffsetFromUsn): the record at $J offset 0
# (USN, time) -- USN 0 on all three -- and every record carved in the image at $J offset = its USN
A10DOC_WRAP = {
    "step7/labBeforeF.raw": (0, "2026-09-20T06:19:11.035841Z", 440),
    "step7/labFbeforereboot.raw": (0, "2026-09-20T06:19:11.035841Z", 43771),
    "step7/labFafterreboot.raw": (0, "2026-09-20T06:53:53.162774Z", 43736),
}
_OUTSIDE_PHRASE = {"written_after_checkpoint": "written after the checkpoint in use, not yet part of its tree",
                   "superseded": "superseded: the live tree holds every one of their"}
_A10DOC_RUN = {}
_A10DOC_TEXT = {}


@pytest.mark.parametrize("rel", list(A10DOC), ids=["image-labBeforeF", "image-labFbeforereboot",
                                                   "image-labFafterreboot"])
def test_a10doc_proof_script_reproduces_the_labF_tail_values(rel):
    """PROOF node (A10-DOC part 2). Runs `a10doc_usn_tail_proof.py --json` (stdlib, raw reads, no tool import) on
    the three LAB-F images and checks what the reference text will rest on: the last record (USN 4,439,864,
    06:43:36.666897), the highest per-file pointer (5,119,752 after the reboot, every one of the 1,654 names changed
    06:43:36.667-06:43:41.776), $J zero and an image hole from the 4 KiB block after the last record to past the
    end of $J on both images, and no USN record past the tail ANYWHERE in the image. T3: the highest pointer with its
    scope -- the live tree's (labFbeforereboot 4,084,440, the claim) and the page copies' outside it (up to
    4,462,624) -- and the script's text output prints both, labelled. ST-2: how those outside copies relate to the
    live tree (labFbeforereboot: written after the checkpoint in use, not yet part of its tree; labFafterreboot:
    superseded), measured and printed. USN wrap: none on the three images ($J offset 0 holds USN 0; every carved
    record at $J offset = its USN), printed. Skips only without the images."""
    img = _img(rel)
    _fx(os.path.isfile(PROOF_SCRIPT), "the proof script is not at %s" % PROOF_SCRIPT)
    if rel not in _A10DOC_RUN:
        r = subprocess.run([sys.executable, "-B", PROOF_SCRIPT, "--json", img], capture_output=True, text=True,
                           timeout=TIMEOUT)
        _fx(r.returncode == 0, "the proof script failed:\n" + r.stderr[-3000:])
        _A10DOC_RUN[rel] = json.loads(r.stdout)["images"][0]
    m, e = _A10DOC_RUN[rel], A10DOC[rel]
    got = dict(
        records_in_j=m["records_in_j"], first=(m["first_record"]["usn"], m["first_record"]["time"]),
        last=(m["last_record"]["usn"], m["last_record"]["time"], m["last_record"]["end"]),
        hi_ptr=m["highest_file_pointer"], hi_ptr_id=m["highest_file_pointer_journal_id"],
        past=(m["pointer_rows_past_last_record"], m["names_past_last_record"], m["changed_range_past_last_record"]),
        zero=m["j_zero_range"], hole=m["image_hole_range"])
    assert m["j_base_image_offset"] == "0x%x" % J_LABF and m["records_elsewhere"] == 0, m
    assert got == e, "the proof script's values moved:\n got %r\nwant %r" % (got, e)
    assert m["carved_anywhere_past_last_record"] == 0 and m["highest_usn_carved_anywhere"] == e["last"][0], m
    # the shape the A10 text and the reference page rest on
    assert m["image_hole_range"][0] == (m["last_record"]["end"] + CS - 1) // CS * CS, m
    assert m["j_zero_range"][1] >= 33554432 and m["image_hole_range"][1] >= 33554432, m    # past the 32 MiB $J
    if rel == "step7/labFafterreboot.raw":
        assert m["j_zero_range"][0] < m["highest_file_pointer"] < m["j_zero_range"][1], m
    # USN wrap (reading 1): none -- $J offset 0 holds USN 0, every carved record lies at $J offset = its USN
    w, (w_usn, w_time, w_n) = m["usn_wrap"], A10DOC_WRAP[rel]
    assert (w["no_wrap"] is True and w["j_offset_0_record"]["usn"] == w_usn and w["j_offset_0_record"]["time"] == w_time
            and w["records_carved"] == w["records_at_j_offset_equal_usn"] == w_n
            and w["records_at_another_offset"] == 0), w
    # T3: the pointer with its scope -- the live tree's and the outside page copies' -- and both printed, labelled
    s, x = m["scoped_pointers"], A10DOC_SCOPED[rel]
    cp = s["checkpoint_in_use"]
    o = s["outside_live_tree_past_last_record"]
    got_scoped = dict(
        live=((cp["lcn"], cp["clock60"], s["live_tree_pages"], s["live_tree_objects"]),
              s["highest_file_pointer_live_tree"], s["highest_file_pointer_live_tree_journal_id"],
              s["pointer_rows_past_last_record_live_tree"], s["names_past_last_record_live_tree"]),
        outside=(s["highest_file_pointer_outside_live_tree"], s["highest_file_pointer_outside_live_tree_journal_id"],
                 s["pointer_rows_past_last_record_outside_live_tree"], s["pages_past_last_record_outside_live_tree"]),
        live_past_pages=s["pages_past_last_record_in_live_tree"],
        relation=(o["relation"], o["names"], o["names_in_live_tree"], o["names_in_live_tree_with_equal_or_higher_pointer"],
                  o["changed_range"], o["live_tree_latest_changed"], o["page_clock_range"]))
    assert got_scoped == x, "the scoped pointer values moved:\n got %r\nwant %r" % (got_scoped, x)
    assert cp["self_checksum"] is True, s
    assert cp["clock60"] == max(c[2] for c in m["checkpoints_lcn_clock10_clock60_clock68"]), s    # the newest copy
    assert m["highest_file_pointer"] == max(s["highest_file_pointer_live_tree"],
                                            s["highest_file_pointer_outside_live_tree"]), s       # every copy = both
    assert m["pointer_rows_past_last_record"] == (s["pointer_rows_past_last_record_live_tree"]
                                                  + s["pointer_rows_past_last_record_outside_live_tree"]), s
    if rel == "step7/labFbeforereboot.raw":
        # the claim's value (live tree) is below the last record; only page copies outside the tree point past it --
        # copies written after the checkpoint in use, not yet part of its tree (ST-2)
        assert s["highest_file_pointer_live_tree"] < e["last"][0] < s["highest_file_pointer_outside_live_tree"], s
        assert o["changed_range"][0] > o["live_tree_latest_changed"] and o["page_clock_range"] == [cp["clock60"]] * 2, o
    if rel not in _A10DOC_TEXT:
        r = subprocess.run([sys.executable, "-B", PROOF_SCRIPT, img], capture_output=True, text=True, timeout=TIMEOUT)
        _fx(r.returncode == 0, "the proof script failed (text mode):\n" + r.stderr[-3000:])
        _A10DOC_TEXT[rel] = r.stdout
    text = _A10DOC_TEXT[rel]
    for label, value in (("LIVE TREE", x["live"][1]), ("PAGE COPIES OUTSIDE THE LIVE TREE", x["outside"][0]),
                         ("EVERY PAGE COPY", e["hi_ptr"])):
        head = "highest per-file pointer, %s" % label
        assert [ln for ln in text.splitlines() if head in ln and re.search(r": %d(?![0-9])" % value, ln)], (
            "the script's text output does not print the %s pointer %d, labelled" % (label.lower(), value)) \
            + "\n" + text
    # ST-2: the outside line says what the copies are (measured), and never calls labFbeforereboot's copies "stale"
    outside_ln = [ln for ln in text.splitlines() if "highest per-file pointer, PAGE COPIES OUTSIDE" in ln]
    phrase = _OUTSIDE_PHRASE.get(x["relation"][0])
    assert len(outside_ln) == 1 and (phrase is None or phrase in outside_ln[0]) \
        and not re.search(r"(?i)\bstale\b", outside_ln[0]), "the outside line: %r" % outside_ln
    assert [ln for ln in text.splitlines() if ln.strip().startswith("USN wrap: NONE")], \
        "the script's text output does not print the USN wrap check\n" + text


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# the matchers, on today's lines and on a plausible corrected wording
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_TODAY_TAIL = [
    "  Journal tail:   DAMAGED — the surviving records end at USN 4439864, but a file on this volume still points "
    "at USN 5119752.",
    "                  That pointer lives in the file's own record, not in $J, so it survived: 679888 bytes of "
    "journal after the last surviving record were DESTROYED (zeroed or overwritten).",
    "                  The records listed are NOT the whole journal and the timeline they support is incomplete."]
_TODAY_INFO_ID = "    Journal ID:     0x01dd48cccc6edb06"
_TODAY_TIMESTOMP = "  USN journal:     present (authoritative cross-check ON)"
_TODAY_CHKP_HOLE = [
    "[forefst] WARNING: bootstrap skipped a bootstrap structure: ValueError: checkpoint (CHKP) not found at LCN 0x13f8 "
    "(offset 0x23f8000): expected 'CHKP', got b'\\x00\\x00\\x00\\x00'. The superblock's checkpoint pointer may be "
    "corrupt — run `refsanalysis.py <image> chkp -v` to inspect.",
    "  [WARN] the checkpoint copy at LCN 0x13f8 is missing or damaged (no CHKP signature: all zeros)",
    "  CHKP #1: cluster 0x13F8 -> 0x23F8000  vc=0 ac=0"]
_TODAY_BUNDLE = ["[forefst]          zeroed-page: 6 page(s) — e.g. page at plcn 0x2f668c reads as all zeros on this "
                 "volume; page at plcn 0x2fc300 reads as all zeros on this volume"]
# T1a: ra supb -v / supb -vv on hole_lo (measured 2026-10-09), and ra chkp's header + clock row (the copy in use)
_TODAY_SUPB_V = ["  #1: cluster 0x13F8 -> 0x23F8000", "       sig=.... vc=0 ac=0 ver=0.0",
                 "  #2: cluster 0xEE34 -> 0xFE34000", "       sig=CHKP vc=63 ac=60 ver=3.14 <- active"]
_TODAY_SUPB_VV = ["  Checkpoint #1: block=0x13f8 -> 0x23f8000", "    sig=b'\\x00\\x00\\x00\\x00' vc=0 ac=0",
                  "    self_block=0x0 ver=0.0", "", "  Checkpoint #2: block=0xee34 -> 0xfe34000",
                  "    sig=b'CHKP' vc=63 ac=60", "    self_block=0xee34 ver=3.14"]
_TODAY_CHKP = ["ReFS Checkpoint (CHKP) at offset 0xFE34000",
               "Virtual clock         0x10    3f 00 00 00 00 00 00 00              63                         ",
               "  CHKP offset                    0xfe34000", "  Virtual clock                  63"]


def test_g3_matchers_accept_corrected_wording_and_reject_todays_lines():
    """Not a RED."""
    # D30
    today = _sentences(_TODAY_TAIL + [_TODAY_INFO_ID])
    assert not _boundary_stated(today, (15984, 16096), (16384,), NEW_CREATED)
    fixed = _sentences(["  Journal instances: USN 0 .. 15,984 belong to the current journal 0x01dd48cccc6edb06 "
                        "(created 2026-09-20 06:53:53); USN 16,384 .. 4,439,864 belong to an earlier instance "
                        "(0x01dd485de7522417), whose records survive above it."])
    assert _boundary_stated(fixed, (15984, 16096), (16384,), NEW_CREATED)
    assert not _boundary_stated(fixed, (15984, 16096), (16384,), r"2026-09-19[ T]17:40:04")
    assert not _boundary_stated(_sentences(["cluster_size=4096 | 128 objects"]), (128, 256), (4096,), NEW_CREATED)
    # D31
    r8g = _sentences(["[forefst] USN journal: the journal's numbering restarted at USN 0 at 2026-07-05 06:54:51 (the "
                      "id was kept); the earlier records, USN 176,128 .. 487,944, belong to an earlier sequence."])
    w = _restart_windows(r8g, R8G_RESTART_TIME)
    assert w and _ID_KEPT.search(w[0]) and _EARLIER_SEQ.search(w[0]) and not _WIPED.search(w[0])
    assert not _restart_windows(_sentences(["the journal was created 2026-07-03 09:41:22 and restarted"]),
                                R8G_RESTART_TIME)
    assert not _restart_windows(today, NEW_CREATED) and not _RESTART.search(" ".join(_TODAY_TAIL))
    assert BJ._names_other_instance(["  Journal instances: 9,526 file(s) carry the id 0x01dce1857f465fdd of an "
                                     "earlier journal instance; none of its records survive."], V2_OLD)
    # R3: named AS an earlier instance; the critic's wrong fix (the old id listed beside "the current journal") is not
    v2_fixed = ["  Journal instances: 9,526 file(s) carry the id 0x01dce1857f465fdd of an earlier journal instance; "
                "none of its records survive."]
    y7 = ["    Journal ids carried by files: 0x01dd4e57f72ac89e (3 files)",
          "                                  0x01dd4e57f84a6362 (the current journal, 50 files)"]
    assert _named_as_earlier(v2_fixed, V2_OLD) and not _named_as_earlier(v2_fixed, LABJ_OLD)
    assert BJ._names_other_instance(y7, LABJ_OLD) and not _named_as_earlier(y7, LABJ_OLD)
    for bad in ("    0x01dd4e57f72ac89e: 3 files older than the current journal",
                "    0x01dd4e57f72ac89e (3 files). An earlier journal instance is not named."):
        assert not _named_as_earlier([bad], LABJ_OLD), bad
    for ok in ("  USN 16,384 .. 4,439,864 belong to an earlier instance (0x01dd485de7522417), whose records survive.",
               "  0x01dd485de7522417: the previous, discarded journal (1,654 files point into it)",
               "  0x01dd485de7522417 is the id of an earlier USN journal instance"):
        assert _named_as_earlier([ok], JID_OLD), ok
    # today's stderr note merged with Y7's listing (labJjournal usn --csv on a patched copy): not a naming
    merged = ["[forefst] note: USN journal: 2354365 non-zero byte(s) in 12 region(s) BEYOND the last record (0x20600+8 "
              "...): ring space not yet written by the journal, still holding prior cluster contents"] + y7
    assert not _named_as_earlier(merged, LABJ_OLD)
    # the same note before a restart sentence with no earlier-sequence clause: no earlier sequence is named
    note = merged[0]
    for line in ("  Journal instances: the journal's numbering restarted at USN 0 at 2026-07-05 06:54:51 (the id was "
                 "kept).", "  Journal instances: the journal was re-created: USN 0 at 2026-09-27 08:12:42 (a new id)."):
        assert not [w for w in _windows(_sentences([note, line])) if _EARLIER_SEQ.search(w)], line
    for ok in ("the earlier records, USN 176,128 .. 487,944, belong to an earlier sequence",
               "records of an earlier numbering survive above it", "3 file(s) carry the id of an earlier journal instance",
               "the previous journal's records"):
        assert _EARLIER_SEQ.search(ok), ok
    # S1: usn --list's per-record blocks are dropped (labels alone pass without that); a statement line is kept
    lst = ["  Journal instances: USN 0 .. 128 belong to the current journal (created 2026-09-20 06:53:53); USN "
           "4,096 .. 4,439,864 belong to an earlier instance.", "",
           "  USN 128        AadRecoveryPasswordDelete  [current journal]", "    Time:    2026-09-20 06:53:53 UTC",
           "    Reason:  SECURITY_CHANGE | CLOSE (0x80000800)", "    FileRef: 0x703:0x0  (directory)",
           "    Parent:  0x701  -> /System Volume Information", "    Attrs:   D", "",
           "  USN 4096       labe_expected.csv  [earlier instance]", "    Time:    2026-09-20 06:22:33 UTC",
           "    Attrs:   A"]
    assert _drop_list_records(lst) == [lst[0], "", ""]
    assert _boundary_stated(_sentences(lst[1:]), (128, 256), (4096,), NEW_CREATED)             # labels pass unfiltered
    assert not _boundary_stated(_sentences(_drop_list_records(lst[1:])), (128, 256), (4096,), NEW_CREATED)
    assert _boundary_stated(_sentences(_drop_list_records(lst)), (128, 256), (4096,), NEW_CREATED)
    # S2: the range from the current journal's end; a correct boundary sentence + tail passes, comma or semicolon
    xs, ends = (15984, 16096), (OLD_LAST, OLD_LAST_END)
    tail = ["    Journal tail:   records are missing: the earlier instance's surviving records end at USN 4,439,864, "
            "but a file on this volume still points at USN 5,119,752; the journal cannot tell whether they were lost "
            "(for example at an unclean detach) or removed."]
    for join in (", USN 16,384 to 4,439,864 to an earlier instance (0x01dd485de7522417).",
                 "; USN 16,384 to 4,439,864 belong to an earlier instance (0x01dd485de7522417)."):
        ok = ["    Journal instances: USN 0 to 15,984 belong to the current journal 0x01dd48cccc6edb06 (created "
              "2026-09-20 06:53:53)" + join] + tail
        assert not _range_from_current_end(_sentences(ok), xs, POINTER, ends), ok
        assert AV._names_range(_sentences(ok)) and _boundary_stated(_sentences(ok), xs, (16384,), NEW_CREATED)
    assert not _range_from_current_end(_sentences(_TODAY_TAIL), xs, POINTER, ends)
    for bad in ("the surviving records end at USN 15,984, but a file on this volume still points at USN 5,119,752.",
                "The current journal's records end at USN 16,096. A file on this volume still points at USN "
                "5,119,752.", "USN 15,984 .. 5,119,752 are missing.",
                "5,103,656 bytes of journal after the last surviving record are missing.",
                "a file points at USN 5,119,752, but the current journal ends at 15,984."):
        assert _range_from_current_end(_sentences([bad] + _TODAY_TAIL), xs, POINTER, ends), bad
        # usn --info's line before the tail has no full stop ("USN range: 0 -- 4439864") and merges into it
        assert _range_from_current_end(_sentences(["    USN range:      0 — 4439864", "    Journal tail:   " + bad]
                                                  + _TODAY_TAIL), xs, POINTER, ends), bad
    for ok in ("USN 0 .. 15,984 belong to the current journal, USN 16,384 .. 4,439,864 to an earlier instance, and a "
               "file points at USN 5,119,752.",
               "The current journal's records end at USN 15,984. Journal tail: the earlier instance's records end at "
               "4,439,864, but a file points at USN 5,119,752."):
        assert not _range_from_current_end(_sentences([ok]), xs, POINTER, ends), ok
    # R2: what of another file's record a details text shows (FileRef, time to the second, reason)
    rec = (96, 12288, _ft("2026-09-20T06:57:55.728945Z"), 0x80000100, (0x765, 0x0), "_selftest")
    assert _other_record_shown("  Last USN record: USN 12288  2026-09-20 06:57:55.728  FILE_CREATE|CLOSE  (file "
                               "0x765:0x0)", rec) == ["its FileRef 0x765:0x0", "its time 2026-09-20 06:57:55",
                                                      "its reason FILE_CREATE|CLOSE"]
    assert _other_record_shown('"usn_record": {"reason": "0x80000100", "timestamp": "2026-09-20T06:57:55.728945Z"}',
                               rec) == ["its time 2026-09-20 06:57:55", "its reason 0x80000100"]
    assert not _other_record_shown("  USN:                12288\n  Changed:            2026-09-20 06:22:36.3645723\n"
                                   "  File attributes:    0x00000020 (Archive)", rec)
    # ST-1: per-sequence coverage on a restart volume (win11refs8g's values)
    c0, _cx, cxt, o0, o0t, ox, oxe, oxt = N219_SEQ[R8G]
    cur = {c0[11:19], cxt[11:19]}

    def st1(lines):
        s = _sentences(lines)
        return (bool(_start_stated(s, [(0, _sec(c0))])), bool(_span_stated(s, o0, _sec(o0t), (ox, oxe), oxt[11:19])),
                bool(_gap_claimed(s, o0t[11:19], cur)), bool(_before_current_start(s, c0[11:19], oxt[11:19])))
    spans = ("  USN journal:     present; two numbering sequences survive. The current numbering starts at USN 0 "
             "(2026-07-05 06:54:51) and runs to USN 173,744 (06:54:56); records of an earlier sequence survive above "
             "it, USN 176,128 to 487,944 (2026-07-03 10:12:01 to 11:05:40).")
    assert st1([spans + " The time between 2026-07-03 11:05:40 and 2026-07-05 06:54:51 is not covered, and files "
                "changed before 2026-07-03 10:12:01 cannot be corroborated by it."]) == (True, True, False, False)
    assert st1([spans + " Changes between them are not covered. Files changed before 2026-07-03 10:12:01 cannot be "
                "corroborated."]) == (True, True, False, False)
    assert st1(["  USN journal:     present; it starts at USN 0 (2026-07-05 06:54:51), its lowest surviving record. "
                "Files changed before that time cannot be corroborated by it."]) == (True, False, False, True)
    assert st1([spans + " Files changed before 2026-07-05 06:54:51 cannot be corroborated."])[2:] == (False, True)
    assert st1([spans + " Files changed before the current numbering's start cannot be corroborated."])[3]
    assert st1([spans + " The journal covers 2026-07-03 10:12:01 to 2026-07-05 06:54:56."])[2:] == (True, False)
    assert st1(["  USN journal:     present; it starts at USN 176,128 (2026-07-03 10:12:01), its earliest record. "
                "Files changed before that time cannot be corroborated by it."])[0] is False
    # R1a / R1b: the hole sentence for a hole, "all zeros" for zeros, never one generic sentence for both
    at = "  checkpoint copy at LCN 0x13f8 (offset 0x23f8000): cannot be read: "
    generic = [at + "no CHKP signature (all zeros); the image may store it as a hole -- not captured, or zero on the "
               "disk; the cause cannot be told from the image"]
    hole_ok = [at + "the image stores this checkpoint copy as a hole -- not captured, or zero on the disk; the cause "
               "cannot be told from the image"]
    zero_ok = [at + "no CHKP signature (all zeros)"]
    assert not _n374_stated("hole_lo", generic, 0x13F8) and not _n374_stated("zero_lo", generic, 0x13F8)
    assert _n374_stated("hole_lo", hole_ok, 0x13F8) and not _n374_stated("zero_lo", hole_ok, 0x13F8)
    assert _n374_stated("zero_lo", zero_ok, 0x13F8) and not _n374_stated("hole_lo", zero_ok, 0x13F8)
    patched = ["[forefst] WARNING: bootstrap skipped a bootstrap structure: ValueError: checkpoint (CHKP) not found at "
               "LCN 0x13f8 (offset 0x23f8000): the image stores this checkpoint copy as a hole -- not captured, or zero "
               "on the disk; the cause cannot be told from the image.", _TODAY_CHKP_HOLE[1]]       # the critic's D1
    assert _hole_named(patched, 0x13F8) and _n374_contra("hole_lo", patched, 0x13F8)
    assert "R1a" in _n374_unstated("hole_lo", generic, 0x13F8) and "R1b" in _n374_unstated("zero_lo", generic, 0x13F8)
    # N368: integrity's FAIL line for a source-image hole
    assert _FAIL_SIG.search("  [FAIL] LCN 0x2f668c: Invalid signature: b'\\x00\\x00\\x00\\x00'")
    # N219 / S4
    ts_today = _sentences([_TODAY_TIMESTOMP])
    assert not _start_stated(ts_today, [(0, r"2026-05-23[ T]07:38:44")]) and not _before_uncovered(ts_today)
    ts_fixed = _sentences(["  USN journal:     present; it starts at USN 0 (2026-05-23 07:38:44, its earliest "
                           "surviving record). Files changed before that time cannot be corroborated by it."])
    assert _start_stated(ts_fixed, [(0, r"2026-05-23[ T]07:38:44")]) and _before_uncovered(ts_fixed)
    assert not _start_stated(_sentences(["the journal starts at USN 1024 (2026-05-23 07:38:44)"]),
                             [(0, r"2026-05-23[ T]07:38:44")])
    wrapped = _sentences(["USN journal: present; the earliest surviving record is USN 40,906,752 (2026-05-11 "
                          "20:34:50); the journal was created 2026-05-11 20:33:59."])
    assert _start_stated(wrapped, [N219_WRAPPED[WS][0]])
    # N219 / T2: the start is the lowest surviving USN; the times' step back is stated with its count and the clock
    ws_lowest = [N219_WRAPPED[WS][0]]
    assert not _start_stated(_sentences(["USN journal: present; it starts at its earliest record, USN 59,226,288 "
                                         "(2026-05-11 10:37:29)."]), ws_lowest)
    stepped = _sentences(["USN journal: present; it starts at USN 40,906,752 (2026-05-11 20:34:50), its lowest "
                          "surviving record; its times step back 6 times; times are as the clock recorded them."])
    assert _start_stated(stepped, ws_lowest) and _steps_back_stated(stepped, 6)
    assert not _steps_back_stated(stepped, 2) and not _steps_back_stated(ts_today, 6)
    assert not _steps_back_stated(_sentences(["its times step back 6 times."]), 6)          # no clock word
    assert _steps_back_stated(_sentences(["The journal's clock went back two times; times are as it recorded them."]),
                              2)
    # N374 / T1: no clock read from zeros; "all zeros" for a zeroed copy
    assert _ZERO_CLOCK.search(_TODAY_CHKP_HOLE[2]) and _ZERO_CLOCK.search("       sig=.... vc=0 ac=0 ver=0.0")
    for ok in ("  CHKP #1: cluster 0x13F8 -> 0x23F8000  vc=64 ac=61 *", "Virtual clock  0x10  3f 00 00 00  63",
               "Virtual clock (body)  0x60    3f 00", "  CHKP #1: cluster 0x13F8 -> 0x23F8000  (no clock: all zeros)",
               "       sig=CHKP vc=64 ac=61 ver=3.14 <- active"):
        assert not _ZERO_CLOCK.search(ok), ok
    assert re.search(_CLOCK_VALUE % 64, "  CHKP #1: cluster 0x13F8 -> 0x23F8000  vc=64 ac=61 *")
    assert _n374_stated("zero_lo", _TODAY_CHKP_HOLE, 0x13F8)          # today's forefst line already says all zeros
    assert not _n374_stated("zero_lo", [_TODAY_CHKP_HOLE[2]], 0x13F8)   # ra supb's line does not
    # N374 / T1a: no field decoded from the unreadable copy; the passage is the copy's own (cut at the other copy)
    assert _copy_fields([_TODAY_CHKP_HOLE[2]], 0x13F8, 0xEE34) == ["vc=0", "ac=0"]
    assert _copy_fields(_TODAY_SUPB_V, 0x13F8, 0xEE34) == ["sig=....", "vc=0", "ac=0", "ver=0.0"]
    assert _copy_fields(_TODAY_SUPB_V, 0xEE34, 0x13F8) == ["vc=63", "ac=60", "ver=3.14"]
    assert _copy_fields(_TODAY_SUPB_VV, 0x13F8, 0xEE34) == ["sig=b'\\x00\\x00\\x00\\x00'", "vc=0", "ac=0",
                                                            "self_block=0x0", "ver=0.0"]
    assert _copy_fields(["  CHKP #1: cluster 0x13F8 -> 0x23F8000  vc=0 ac=0",
                         "  CHKP #2: cluster 0xEE34 -> 0xFE34000  vc=63 ac=60 *"], 0x13F8, 0xEE34) == ["vc=0", "ac=0"]
    fixed_v = ["  #1: cluster 0x13F8 -> 0x23F8000", "       cannot be read: no CHKP signature (all zeros); no field is "
               "decoded from it", "  #2: cluster 0xEE34 -> 0xFE34000", "       sig=CHKP vc=63 ac=60 ver=3.14 <- active"]
    assert not _copy_fields(fixed_v, 0x13F8, 0xEE34) and _n374_stated("zero_lo", fixed_v, 0x13F8)
    for ok in (["latest_checkpoint  checkpoint #2 @ 0xfe34000 (vc=63, ac=60); #1 @ 0x23f8000 cannot be read "
                "(all zeros)"],
               ["checkpoint #1 @ 0x23f8000 (all zeros); #2 @ 0xfe34000 (vc=63, ac=60)"],
               ["  CHKP #1: cluster 0x13F8 -> 0x23F8000  (no clock: all zeros)", "  sig=none"],
               ["  CHKP #1: cluster 0x13F8 -> 0x23F8000  unreadable: the image stores it as a hole -- not captured, or "
                "zero on the disk; the cause cannot be told from the image"]):
        assert not _copy_fields(ok, 0x13F8, 0xEE34), ok
    assert _hole_named(["  CHKP #1: cluster 0x13F8 -> 0x23F8000  unreadable: the image stores it as a hole -- not "
                        "captured, or zero on the disk; the cause cannot be told from the image"], 0x13F8)
    assert _chkp_decodes(_TODAY_CHKP, 0xEE34, 63) and _chkp_decodes(_TODAY_CHKP[2:], 0xEE34, 63)
    assert not _chkp_decodes(_TODAY_CHKP, 0x13F8, 63) and not _chkp_decodes(_TODAY_CHKP, 0xEE34, 0)
    assert _FIELD_VALUE.search(_TODAY_CHKP[1]) and _FIELD_VALUE.search(_TODAY_CHKP[3])
    # N374 / N368
    assert not _hole_named(_TODAY_CHKP_HOLE, 0x13F8)
    assert [w for w in _line_windows(_TODAY_CHKP_HOLE, 0x13F8, 2) if _POINTER_BLAME.search(w)]
    assert _hole_named(["  [WARN] the checkpoint copy at LCN 0x13f8 cannot be read: the image stores it as a hole --",
                        "         not captured, or zero on the disk; the cause cannot be told from the image"], 0x13F8)
    assert not _hole_named(_TODAY_BUNDLE, 0x2F668C)
    fixed_b = ["page at plcn 0x2f668c: the source image stores this page as a hole (listed in the manifest's "
               "source_holes): not captured, or zero on the disk; the cause cannot be told from the image"]
    assert [x for x in _hole_named(fixed_b, 0x2F668C) if _SOURCE.search(x)] and not _FAIL_SIG.search(fixed_b[0])
    # ── the last critic items (2026-10-09) ──
    # USN 0: a comma or full stop ending the clause is accepted; "USN 0.5" / "USN 01" are not USN 0
    for ok in ("USN journal: present; it starts at USN 0, 2026-05-23 07:38:44, its earliest surviving record.",
               "USN journal: present; it starts at 2026-05-23 07:38:44 with USN 0.",
               "USN journal: present; it starts at USN 0 (2026-05-23 07:38:44)."):
        assert _start_stated(_sentences([ok]), [(0, r"2026-05-23[ T]07:38:44")]), ok
    for bad in ("USN journal: it starts at USN 0.5 (2026-05-23 07:38:44).",
                "USN journal: it starts at USN 01 (2026-05-23 07:38:44)."):
        assert not _start_stated(_sentences([bad]), [(0, r"2026-05-23[ T]07:38:44")]), bad
    # S3: "source" is required; C8 = B's "image" alone, or the manifest key, is not it
    assert not _SOURCE.search("page at plcn 0x2f668c: the image stores this page as a hole -- not captured, or zero on "
                              "the disk; the cause cannot be told from the image")
    assert not _SOURCE.search("page at plcn 0x2f668c (listed in the manifest's source_holes) reads as a hole")
    # S6: the pointer blamed, in today's words or reworded; never a negated or pointer-less line
    assert _cause_named(_TODAY_CHKP_HOLE[0])
    for bad in ("checkpoint copy at LCN 0x13f8: no CHKP signature (all zeros); the superblock's pointer to it may be "
                "wrong", "checkpoint copy at LCN 0x13f8 (all zeros): a bad checkpoint pointer in the superblock"):
        assert _cause_named(bad), bad
        assert not _POINTER_BLAME.search(bad), bad            # why S6 does not reuse the wording RED's narrow matcher
    for ok in ("checkpoint copy at LCN 0x13f8 (offset 0x23f8000): cannot be read: no CHKP signature (all zeros)",
               "  CHKP secondary   LCN 0x13f8 (offset 0x23f8000)  — BAD (no CHKP signature) (roots unreadable)",
               "the superblock's pointer to it is not corrupt; the copy is all zeros",
               "the superblock's checkpoint pointer is valid; the copy it points at is all zeros"):
        assert not _cause_named(ok), ok
    # S5: decision 31's sentence on labJjournal (USN 0 at the first record's time, a new id, an earlier sequence)
    def s5(lines):
        stated = _restart_times(_sentences(lines))
        win = [w for w, t in stated if re.match(LABJ_RESTART_TIME, t) and _USN0.search(w)]
        old_time = [w for w, t in stated if re.match(LABJ_OLD_TIME, t)]
        return (bool(win), bool([w for w in win if _ID_NEW.search(w)]), bool([w for w in win if _ID_KEPT_CLAIM.search(w)]),
                bool([w for w in win if _EARLIER_SEQ.search(w)]), bool(old_time))
    # the merged statistics line (bare usn / --stats) carries the first record's second; a wrong time stated after it is
    # still refused, a right one still accepted
    stats = ["  USN range:           0 — 31576", "  Time range:          2026-09-27 08:12:42 UTC",
             "                    to 2026-09-27 08:20:38 UTC"]
    assert s5(stats + ["  Journal instances: the journal's numbering restarted at USN 0 at 2026-09-27 08:12:40 (a new "
                       "id); 3 file(s) carry the id 0x01dd4e57f72ac89e of an earlier journal instance."]) \
        == (False, False, False, False, True)
    assert _restart_windows(_sentences(stats + ["  Journal instances: the journal's numbering restarted at USN 0 at "
                                                "2026-09-27 08:12:40 (a new id)."]), LABJ_RESTART_TIME)  # any-time rule
    labj_ok = ["  Journal instances: the journal was re-created: its numbering restarted at USN 0 at 2026-09-27 "
               "08:12:42 (a new id, 0x01dd4e57f84a6362); 3 file(s) carry the id 0x01dd4e57f72ac89e of an earlier "
               "journal instance, whose records no longer survive in $J."]
    assert s5(labj_ok) == (True, True, False, True, False) and _named_as_earlier(labj_ok, LABJ_OLD)
    assert s5(stats + labj_ok) == (True, True, False, True, False)                    # after the statistics lines
    assert s5(["  Journal instances: 3 file(s) carry the id 0x01dd4e57f72ac89e of an earlier journal instance; none "
               "of its records survive in $J."])[0] is False                                        # no re-creation
    assert s5(["  the journal's numbering restarted at USN 0 at 2026-09-27 08:12:42 (the id was kept); the earlier "
               "records belong to an earlier sequence."])[1:3] == (False, True)                     # r8g's sentence
    assert s5(["  the journal's numbering restarted at USN 0 at 2026-09-27 08:12:40 (a new id); 3 file(s) carry the "
               "id 0x01dd4e57f72ac89e of an earlier journal instance."]) == (False, False, False, False, True)
    assert s5(["  the journal was re-created at 2026-09-27 08:12:42 (a new id); 3 file(s) carry the id "
               "0x01dd4e57f72ac89e of an earlier journal instance."])[0] is False                   # no USN 0
    assert not _ID_KEPT_CLAIM.search(labj_ok[0]) and not _ID_KEPT_CLAIM.search("3 files kept the earlier id")
    # R4: a record's own content is classified out by its print format; a label or an added line is a statement
    names = {40906752: "amd64_x.manifest", 44615872: "amd64_microsoft-windows-s..restartup-repairbde_31bf"}
    lst = ["  USN %-10d %s" % (40906752, names[40906752]), "    Time:    2026-05-11 20:34:50 UTC",
           "    Reason:  FILE_CREATE (0x00000100)", "", "  USN %-10d %s" % (44615872, names[44615872]),
           "    Time:    2026-05-11 20:35:01 UTC", "    Attrs:   A", ""]
    sc = _r4_classify(_Scan(), ("usn", "--list"), lst, names)
    assert sc.heads == 2 and not sc.mismatched and sc.statements == ["", ""], (sc.statements, sc.mismatched)
    sc = _r4_classify(_Scan(), ("usn", "--list"), [lst[0] + "  [earlier instance]", "    Instance: earlier"] + lst[1:],
                      names)
    assert len(sc.mismatched) == 1 and [ln for ln in sc.statements if _BOUNDARY.search(ln)], sc.statements
    ev = "  %-28s  %-5s  %-10s  %-26s  %s" % ("2026-05-11T10:42:46.0000000Z", "USN", "0x9717", "RestartAgent.exe",
                                             "FILE_CREATE")                              # acceptance 1.14.0 (K5)
    und = "  %-23s  %-5s  %-10s  %-26s  %s" % ("(undated)", "MLog", "—", "Restart…", "RENAME")
    sc = _r4_classify(_Scan(), ("timeline",), [ev, und, "  the journal restarted at 2026-05-11 10:37:29"], {})
    assert sc.statements == ["  the journal restarted at 2026-05-11 10:37:29"], sc.statements
    sc = _r4_classify(_Scan(), ("usn",), ["  Top files by record count:", "    RestartAgent.exe     12", "",
                                          "  Unique filenames:    5"], {})
    assert sc.statements == ["  Top files by record count:", "", "  Unique filenames:    5"], sc.statements
    sc = _r4_classify(_Scan(), ("usn", "--json"), ['  "Records": [', '      "USN": 1,', '      "instance": "earlier"'], {})
    assert sc.keys == {(2, "Records"), (6, "USN"), (6, "instance")} and sc.rec_keys == {"USN", "instance"} \
        and not sc.statements
    # the streaming runner's row rule is AV._split's
    p, h, rows = AV._split("prose line\n" + USN_CSV_HEADER + "\n0,2026-09-20T06:53:53.1620000Z"
                           + ",x" * (len(USN_CSV_HEADER.split(",")) - 2) + "\n", "e")      # acceptance 1.14.0: 18 columns
    assert h and len(rows) == 1 and p == ["prose line", "e"]
    # ── the fixer's first step (the narrow re-check, 2026-10-09): R-A, R-B, Q1-Q11, S5 ──
    # R-A: ST-1's own words are caught on winsider's lines; T2's correct statement is not
    assert _EARLIER_SEQ.search("  Records of an earlier sequence survive above USN 59,226,288 (from 2026-05-11 "
                               "10:37:29)")
    assert not [ln for ln in stepped if _EARLIER_SEQ.search(ln) or _RESTART.search(ln) or _BOUNDARY.search(ln)]
    # R-B: the tool's own hole label on written zeros is a hole word; "all zeros" alone is not
    gap_label = [at + "no CHKP signature (all zeros) -- absent from the image (acquisition gap, not damage)"]
    assert _n374_contra("zero_lo", gap_label, 0x13F8) and not _n374_stated("zero_lo", gap_label, 0x13F8)
    for w in ("absent from this image", "acquisition gap", "not captured", "a hole", "sparse"):
        assert _HOLE_WORDS.search(w), w
    assert not _n374_contra("zero_lo", zero_ok, 0x13F8) and _n374_stated("zero_lo", zero_ok, 0x13F8)
    # Q1: the phrase is bound to the id named nearest to it; inverted labels are refused; the lineage's correct
    # statement and labJjournal's are accepted with the current id given
    inv = ["    Journal ids carried by files: 0x01dd4e57f72ac89e (3 files, the current journal) and 0x01dd4e57f84a6362 "
           "(50 files, an earlier journal instance)."]
    assert not _named_as_earlier(inv, LABJ_OLD, LABJ_NEW) and not _named_as_earlier(inv, LABJ_OLD)
    lineage_ok = ["[forefst] Journal instances: USN 0 .. 45,504 belong to the current journal 0x01dd48cccc6edb06 "
                  "(created 2026-09-20 06:53:53); USN 49,152 .. 4,439,864 belong to an earlier instance, "
                  "0x01dd485de7522417."]
    assert _named_as_earlier(lineage_ok, JID_OLD, JID_NEW) and _named_as_earlier(labj_ok, LABJ_OLD, LABJ_NEW)
    assert _named_as_earlier(v2_fixed, V2_OLD, V2_ID) and not _named_as_earlier(y7, LABJ_OLD, LABJ_NEW)
    # Q2: a correct naming over two sentences ("It is the id of an earlier journal instance") is accepted, an unrelated
    # next sentence is not
    two = ["    Journal ids carried by files: 0x01dd4e57f72ac89e (3 files). It is the id of an earlier journal instance, "
           "whose records no longer survive in $J."]
    assert _named_as_earlier(two, LABJ_OLD, LABJ_NEW)
    assert not _named_as_earlier(["    Journal ids carried by files: 0x01dd4e57f72ac89e (3 files). Another file "
                                  "carries the id of an earlier journal instance."], LABJ_OLD, LABJ_NEW)
    # Q3: the earlier-sequence clause on the current numbering's range is caught; r8g's correct sentence is not
    assert _current_called_earlier(_sentences(["the journal's numbering restarted at USN 0 at 2026-07-05 06:54:51 (the "
                                               "id was kept); USN 0 .. 173,744 belong to an earlier sequence."]),
                                   R8G_CUR, R8G_OLD)
    assert not _current_called_earlier(r8g, R8G_CUR, R8G_OLD)
    assert not _current_called_earlier(_sentences(["the current numbering runs to USN 173,744, and records of an "
                                                   "earlier sequence survive from USN 176,128"]), R8G_CUR, R8G_OLD)
    # Q5: earlier records claimed to survive above labJjournal's last record are caught; "no longer survive" is not
    fake = ["  Journal instances: the journal was re-created: its numbering restarted at USN 0 at 2026-09-27 08:12:42 (a "
            "new id, 0x01dd4e57f84a6362); records of an earlier sequence survive above it, USN 32,768 .. 40,960."]
    assert _survivors_claimed_above(_sentences(fake), 31576) and not _survivors_claimed_above(_sentences(labj_ok), 31576)
    # Q6: the decimal reason after a reason key, and the FileRef as home_oid / file_id ints
    assert _other_record_shown('  "last_usn_record": {"usn": 12288, "reason": 2147483904, "home_oid": 1893, '
                               '"file_id": 0},', rec) == ["its reason 2147483904 (decimal)",
                                                          "its FileRef as home_oid 1893 / file_id 0"]
    assert _other_record_shown("  Last USN record:    USN 12288  reason 2147483904  (file 1893:0)", rec) == \
        ["its reason 2147483904 (decimal)"]
    assert not _other_record_shown('  "file_id": "0x0", "creation_dir_oid": "0x765", "usn": 12288', rec)
    # Q7: a range from the current end spread over three sentences
    own3 = ["    Journal tail:   the current journal's records end at USN 16,096. Every record after that is missing. A "
            "file on this volume still points at USN 5,119,752."]
    assert _range_from_current_end(_sentences(own3), xs, POINTER, ends)
    # Q8: an open-ended coverage claim from the earlier first time
    q8 = _sentences([spans + " Together the two sequences cover the changes made since 2026-07-03 10:12:01."])
    assert _gap_claimed(q8, o0t[11:19], cur, oxt[11:19]) and not _gap_claimed(q8, o0t[11:19], cur)
    assert not _gap_claimed(_sentences([spans + " Files changed before 2026-07-03 10:12:01 cannot be corroborated."]),
                            o0t[11:19], cur, oxt[11:19])
    # Q10 (and Q9 with `_ALL_ZEROS`): zeros in any wording, never a bare "zero" (C8 = B says "zero on the disk")
    for w in ("(all zeros)", "zero-filled", "zeroed", "only zero bytes", "all-zero"):
        assert _ZEROS_SAID.search(w), w
    assert not _ZEROS_SAID.search(hole_ok[0]) and not _ZEROS_SAID.search(fixed_b[0])
    assert _n374_contra("hole_lo", [at + "no CHKP signature: zero-filled"], 0x13F8)
    # Q11: a removal cause is a cause; negated, it is not
    assert _cause_named("checkpoint copy at LCN 0x13f8: no CHKP signature (all zeros): the copy was overwritten")
    assert not _cause_named("checkpoint copy at LCN 0x13f8: no CHKP signature (all zeros); it was not overwritten")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# G3b -- review round 1 (2026-10-10): F1, F2, N9, the two latent defects of group 3's new code, and refsanalysis
# `supb --verify` on an unreadable checkpoint copy (G3_CONTEXT "Review round 1 ... the lead's settlements, taken in
# G3b"; REVIEW_G3_correctness.md F1, F2, N2, N3, N9, N12; REVIEW_G3_tests.md F1). RED first: written and run on the
# tools of `fixes/prefix_G3b/` (forefst 34ea7f97, refsanalysis e28d03ce) before any tool edit.
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

TIMELINE_CSV_HEADER = "Timestamp,TimeSource,Source,OID,Name,PathToday,Event"    # acceptance 1.14.0 (K21, P9, Q-C)
TIMELINE_KEYS = frozenset(TIMELINE_CSV_HEADER.split(","))
_TL_ROW = AV._CSV_TABLES[0][1]           # the timeline row rule: a time, "(none)", "(undated)" or 0x<hex> first


class _JStream:
    """A text stream read in 1 MiB chunks for incremental JSON decoding: `peek` the next non-whitespace character,
    `value` decode one JSON value at the position (reading more as needed)."""

    def __init__(self, stream):
        self.stream, self.dec = stream, json.JSONDecoder()
        self.buf, self.pos, self.eof = "", 0, False

    def more(self):
        chunk = self.stream.read(1 << 20)
        self.buf, self.pos = self.buf[self.pos:] + chunk, 0
        self.eof = not chunk
        return bool(chunk)

    def peek(self):
        """The next non-whitespace character (None at the end of the stream), the position left on it."""
        while True:
            b, p = self.buf, self.pos
            while p < len(b) and b[p] in " \t\r\n":
                p += 1
            self.pos = p
            if p < len(b):
                return b[p]
            if self.eof or not self.more():
                return None

    def value(self):
        """(value, None) or (None, error): the next JSON value, whitespace before it skipped."""
        if self.peek() is None:
            return None, "the stream ends where a value belongs"
        while True:
            try:
                obj, end = self.dec.raw_decode(self.buf, self.pos)
                self.pos = end
                return obj, None
            except ValueError as e:
                if self.eof or not self.more():
                    return None, "does not decode (%s): %r" % (e, self.buf[self.pos:self.pos + 160])

    def around(self):
        return self.buf[self.pos:self.pos + 160]


def _stream_array(js, keys):
    """At a '[': its elements, each an object whose keys are `keys`, one decoded at a time. (count, error)."""
    n = 0
    if js.peek() != "[":
        return n, "no JSON array here: %r" % js.around()
    js.pos += 1
    if js.peek() == "]":
        js.pos += 1
        return n, None
    while True:
        if js.peek() is None:
            return n, "the stream ends inside the array, after element %d" % n
        obj, err = js.value()
        if err:
            return n, "element %d %s" % (n, err)
        if not isinstance(obj, dict) or set(obj) != set(keys):
            return n, "element %d is not an event object: %r" % (n, obj)
        n += 1
        c = js.peek()
        if c == ",":
            js.pos += 1
            continue
        if c == "]":
            js.pos += 1
            return n, None
        return n, "after element %d: %r where ',' or ']' belongs" % (n, js.around())


def _json_array_check(stream, keys):
    """Stream-check that the text `stream` holds exactly ONE JSON array of objects whose keys are `keys`, and nothing
    else but whitespace. One element is decoded at a time (a 130 MB export is never held). Returns (objects, error):
    error None when the stream is that array."""
    js = _JStream(stream)
    if js.peek() != "[":
        return 0, "stdout does not start with a JSON array: %r" % js.around()
    n, err = _stream_array(js, keys)
    if err:
        return n, err
    if js.peek() is not None:
        return n, "text after the JSON array: %r" % js.around()
    return n, None


TIMELINE_ENVELOPE = ("SourceCounts", "Statements", "Events")       # N312 (1.14.0)


def _json_envelope_check(stream, keys):
    """1.14.0 (N312): `timeline --json` is ONE object -- SourceCounts, Statements, then Events, an array of event
    objects whose keys are `keys` -- and nothing else but whitespace; Events streamed as `_json_array_check` streams
    its array. Returns (events, error)."""
    js = _JStream(stream)
    if js.peek() != "{":
        return 0, "stdout does not start with a JSON object: %r" % js.around()
    js.pos += 1
    seen, n = [], 0
    while True:
        c = js.peek()
        if c == "}":
            js.pos += 1
            break
        if seen:
            if c != ",":
                return n, "after %r: %r where ',' or '}' belongs" % (seen[-1], js.around())
            js.pos += 1
        key, err = js.value()
        if err or not isinstance(key, str):
            return n, "a key %s" % (err or repr(key))
        if js.peek() != ":":
            return n, "no ':' after %r" % key
        js.pos += 1
        seen.append(key)
        if key == "Events":
            n, err = _stream_array(js, keys)
            if err:
                return n, err
        else:
            _v, err = js.value()
            if err:
                return n, "%s %s" % (key, err)
    if not (seen and seen[0] == "SourceCounts" and seen[-1] == "Events" and "Statements" in seen
            and set(seen) <= set(TIMELINE_ENVELOPE) | {"USNRecordsRead", "MLogRowsUndated"}):
        return n, "the envelope's keys are %r, not %r (+ USNRecordsRead / MLogRowsUndated)" % (seen, TIMELINE_ENVELOPE)
    if js.peek() is not None:
        return n, "text after the JSON object: %r" % js.around()
    return n, None


_F1_RUNS = {}


def _f1_exec(rel, args):
    """`timeline` in an export form, stdout streamed and checked, nothing of the export kept: --csv through
    csv.reader (its first row; the later rows that are not 5 fields with a timeline first field), --json through
    `_json_array_check`, --jsonl line by line (each an event object). stderr is kept. A traceback or a timeout is a
    fixture error, never the defect."""
    key = (rel, tuple(args))
    if key in _F1_RUNS:
        return _F1_RUNS[key]
    cmd = [sys.executable, "-B", FOREFST, _img(rel)] + list(args)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO)
    errbuf = []
    t = threading.Thread(target=lambda: errbuf.append(p.stderr.read()))
    t.start()
    timer = threading.Timer(TIMEOUT, p.kill)
    timer.start()
    res = {"first": None, "n": 0, "nbad": 0, "bad": [], "error": None}
    out = io.TextIOWrapper(p.stdout, encoding="utf-8", errors="replace", newline="")
    try:
        if "--csv" in args:
            for i, row in enumerate(csv.reader(out)):
                if i == 0:
                    res["first"] = row
                    continue
                res["n"] += 1
                if len(row) != len(TIMELINE_KEYS) or not _TL_ROW(row):
                    res["nbad"] += 1
                    if len(res["bad"]) < 3:
                        res["bad"].append(",".join(row)[:200])
        elif "--jsonl" in args:
            for ln in out:
                if res["first"] is None:
                    res["first"] = ln.rstrip("\r\n")[:200]
                try:
                    o = json.loads(ln)
                    ok = isinstance(o, dict) and set(o) == TIMELINE_KEYS
                except ValueError:
                    ok = False
                if ok:
                    res["n"] += 1
                else:
                    res["nbad"] += 1
                    if len(res["bad"]) < 3:
                        res["bad"].append(ln.rstrip("\r\n")[:200])
        else:
            res["n"], res["error"] = _json_envelope_check(out, TIMELINE_KEYS)    # acceptance 1.14.0 (N312)
        for _chunk in iter(lambda: out.read(1 << 20), ""):      # drain what a failed check left unread
            pass
        p.wait()
    finally:
        timer.cancel()
        t.join()
    err = (errbuf[0] if errbuf else b"").decode("utf-8", "replace")
    if p.returncode < 0:
        raise RedFixtureError("timeout or kill (%d): %s" % (p.returncode, " ".join(cmd)))
    if "Traceback (most recent call last)" in err:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + err[-3000:])
    res["rc"], res["err"] = p.returncode, err
    _F1_RUNS[key] = res
    return res


def _f1_ctx(rel, args, r):
    return ("\n[%s %s] rc=%d, %d event(s), first stdout row %r, %d bad row(s) %r, error %r\n--- stderr (tail) ---\n%s"
            % (rel, " ".join(args), r["rc"], r["n"], r["first"], r["nbad"], r["bad"][:2], r["error"],
               r["err"][-3000:]))


# The volumes on which the journal commands state the journal's state (group 3: decisions 30 and 31, A10): every one
# exits 2 with a "Journal instances:" statement; the five A10 volumes also with A10's "Journal tail:" one.
F1_TAIL = ["step7/labFafterreboot.raw", "step7/labG_0.raw", "step7/labG_1.raw", "step7/labG_2.raw",
           "step7/win11afterblindaudit.raw"]
F1_VOLS = [LABJ, R8G, V2] + F1_TAIL
F1_IDS = ["image-" + os.path.basename(v)[:-4] for v in F1_VOLS]
F1_FORMS = [("timeline", "--json"), ("timeline", "--fast", "--json"), ("timeline", "--csv"),
            ("timeline", "--fast", "--jsonl")]
F1_FORM_IDS = ["timeline-json", "timeline-fast-json", "timeline-csv", "timeline-fast-jsonl"]
_F1_INSTANCES = re.compile(r"Journal instances:")
_F1_TAIL_STMT = re.compile(r"Journal tail:")


def _f1_premise(rel):
    """The bytes behind each volume's journal statements, by the premises this module already reads."""
    if rel == LABJ:
        _labj_premise()
    elif rel == R8G:
        _r8g_premise()
    elif rel == V2:
        _v2_premise()
    else:
        _d30_premise(rel)


# RED 1.13.2 G3b F1: green with G3b's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", F1_FORMS, ids=F1_FORM_IDS)
@pytest.mark.parametrize("rel", F1_VOLS, ids=F1_IDS)
def test_g3b_f1_timeline_export_to_stdout_carries_only_the_export(rel, args):
    _f1_premise(rel)
    r = _f1_exec(rel, args)
    ctx = _f1_ctx(rel, args, r)
    _keep(r["rc"] == 2, "the journal statements' findings keep exit 2 on this volume" + ctx)
    if "--csv" in args:
        assert r["first"] == TIMELINE_CSV_HEADER.split(","), (
            "stdout carries the export only: it must start with the CSV header, yet its first row is %r"
            % (r["first"],)) + ctx
    elif "--jsonl" in args:
        assert not r["nbad"], ("stdout carries the export only: %d line(s) are not an event object, e.g. %r"
                               % (r["nbad"], r["bad"][:2])) + ctx
    else:
        assert r["error"] is None, "stdout carries the export only, one JSON array: %s" % r["error"] + ctx
    assert not r["nbad"] and r["n"] > 0, "the export holds %d event(s) and %d other row(s)" % (r["n"], r["nbad"]) + ctx
    assert _F1_INSTANCES.search(r["err"]), "the journal's instance statement is not on stderr" + ctx
    if rel in F1_TAIL:
        assert _F1_TAIL_STMT.search(r["err"]), "A10's statement of the missing records is not on stderr" + ctx


F1_CONTROL = "step7/labFbeforereboot.raw"


@pytest.mark.parametrize("args", F1_FORMS, ids=F1_FORM_IDS)
def test_g3b_f1_control_a_volume_without_journal_statements_exports_cleanly(args):
    """Not a RED. labFbeforereboot: one journal instance, one numbering sequence (own carve, as D30's control reads it),
    so no journal statement: its timeline export to stdout is the export alone, exit 0, today and after the fix."""
    with open(_img(F1_CONTROL), "rb") as fh:
        fh.seek(J_LABF)
        recs = _carve(fh.read(OLD_LAST_END + 0x200))
    _fx(recs and recs[0][1] == 0 and not _steps(recs), "%s: not one numbering sequence" % F1_CONTROL)
    r = _f1_exec(F1_CONTROL, args)
    ctx = _f1_ctx(F1_CONTROL, args, r)
    assert r["rc"] == 0, ctx
    if "--csv" in args:
        assert r["first"] == TIMELINE_CSV_HEADER.split(","), ctx
    assert r["error"] is None and not r["nbad"] and r["n"] > 0, ctx
    assert not _F1_INSTANCES.search(r["err"]) and not _F1_TAIL_STMT.search(r["err"]), ctx


# ── F2: `verify-bundle` reads its rehydrated copy with the bundle's context (N368's and N374's hole sentences) ──

_G3B_CHKP_BUNDLE = {}


def _g3b_chkp_bundle(plant):
    """hole_lo / zero_lo of win11refsmini (the N374 plants' recipe: the 16 KiB copy at LCN 0x13f8 left as a hole, or
    written as zeros), its bundle (`export metadata --what vbr,chkp,supb,btree`), and `verify-bundle` on it; the
    copies are deleted after the run. Returns (lcn, the run)."""
    if plant in _G3B_CHKP_BUNDLE:
        return _G3B_CHKP_BUNDLE[plant]
    base = _img(BASE)
    lcn = AB.IMG.lo
    os.makedirs(SCRATCH, exist_ok=True)
    d = tempfile.mkdtemp(prefix="g3b_f2_", dir=SCRATCH)
    p = os.path.join(d, "target.raw")
    try:
        _fx(AB._sparse_capable(d), "%s cannot hold a sparse file" % d)
        AB._carve(base, p)
        AB.Vol(AB.IMG, p).pin()                              # the base is what the case needs, before the plant
        os.unlink(p)
        if plant.startswith("hole"):
            BJ._carve_except(base, p, [(AB.IMG.ps + lcn * CS, 0x4000)])
            _fx(BJ._is_hole(p, AB.IMG.ps + lcn * CS, 0x4000), "the copy is not a hole")
        else:
            AB._carve(base, p)
            AB.Vol(AB.IMG, p).zero(AB.IMG.ps + lcn * CS, 0x4000)
            _fx(not BJ._is_hole(p, AB.IMG.ps + lcn * CS, 0x4000), "the zeroed copy must stay WRITTEN")
        b, man = _export(p, d)
        os.unlink(p)
        listed = {h["lcn"] + i for h in man.get("source_holes") or [] if h["hole_bytes"] == h["clusters"] * CS
                  for i in range(h["clusters"])}
        if plant.startswith("hole"):
            # LB48 (wave B part 3, the sanctioned premise edit): N190 exports the copy's ONE cluster (the record, E118),
            # so the manifest lists that cluster as a source hole -- not the page's four
            _fx(lcn in listed, "the manifest does not list the copy's cluster as a hole")
        else:
            _fx(not [x for x in listed if lcn <= x < lcn + 4], "the manifest lists the zeroed copy as a hole")
        r = _exec(b, ("verify-bundle",), cwd=d)
        _G3B_CHKP_BUNDLE[plant] = (lcn, r)
        return _G3B_CHKP_BUNDLE[plant]
    finally:
        if os.path.exists(p):
            os.unlink(p)
        _drop_dir(d)


# RED 1.13.2 G3b F2: green with G3b's fix (the strict xfail mark removed)
def test_g3b_f2_verify_bundle_states_pages_listed_in_source_holes_as_holes_of_the_source_image(moa_bundle):
    b, _man = moa_bundle
    r = _exec(b, ("verify-bundle",), cwd=os.path.dirname(b))
    lines = r.prose
    _keep(r.rc == 2, "the bundle is whole and reading it records a finding: exit 2" + r.ctx("bundle verify-bundle"))
    _keep([ln for ln in lines if AB._lcn_re(MOA_PAGES[0]).search(ln)], "page 0x%x must still be named" % MOA_PAGES[0]
          + r.ctx("bundle verify-bundle"))
    said = [w for lcn in MOA_PAGES for w in _line_windows(lines, lcn, 1)
            if re.search(r"(?i)reads as all zeros on this volume", w)]
    assert not said, ("pages the manifest lists whole in source_holes are called 'reads as all zeros on this volume': "
                      "%r" % said[:1]) + r.ctx("bundle verify-bundle")
    assert [w for w in _hole_named(lines, MOA_PAGES[0]) if _SOURCE.search(w)], (
        "page 0x%x: nothing says the source image stores it as a hole, with the cause left open" % MOA_PAGES[0]) \
        + r.ctx("bundle verify-bundle")
    zeros = [w for lcn in MOA_PAGES for w in _line_windows(lines, lcn, 1) if _ALL_ZEROS.search(w)]
    assert not zeros, "a source-image hole page is called zeros: %r" % zeros[:1] + r.ctx("bundle verify-bundle")


# RED 1.13.2 G3b F2: green with G3b's fix (the strict xfail mark removed)
def test_g3b_f2_verify_bundle_names_a_checkpoint_copy_in_a_source_hole_with_the_source_image_hole_sentence():
    lcn, r = _g3b_chkp_bundle("hole_lo")
    lines = r.prose
    _keep(r.rc == 2, "T1: an unreadable checkpoint copy exits 2 (verify-bundle already does)" + r.ctx("hole_lo bundle"))
    _keep(AB._lines("\n".join(lines), lcn), "the copy at LCN 0x%x must still be named" % lcn + r.ctx("hole_lo bundle"))
    assert [w for w in _hole_named(lines, lcn) if _SOURCE.search(w)], (
        "LCN 0x%x is listed whole in the manifest's source_holes: nothing says the source image stores the copy as a "
        "hole, with the cause left open" % lcn) + r.ctx("hole_lo bundle")
    zeros = _n374_contra("hole_lo", lines, lcn)
    assert not zeros, ("R1a: the copy at LCN 0x%x is a hole of the source image, yet a passage at its lines calls it "
                       "zeros: %r" % (lcn, zeros[:1])) + r.ctx("hole_lo bundle")


def test_g3b_f2_control_verify_bundle_calls_a_zeroed_checkpoint_copy_all_zeros():
    """Not a RED. The same bundle of a copy WRITTEN as zeros (the trigger, a source-image hole, removed): verify-bundle
    names the copy 'all zeros', no hole word (R1b / R-B), exit 2 -- today and after the fix."""
    lcn, r = _g3b_chkp_bundle("zero_lo")
    assert r.rc == 2, r.ctx("zero_lo bundle")
    assert [w for w in _line_windows(r.prose, lcn, 2) if _ALL_ZEROS.search(w)], r.ctx("zero_lo bundle")
    assert not _n374_contra("zero_lo", r.prose, lcn), r.ctx("zero_lo bundle")


# ── N9 (decision 33): `summary --json`'s `usn_journal_id` is the current journal's id (its JSON type kept) ──

# RED 1.13.2 G3b N9: green with G3b's fix (the strict xfail mark removed)
@pytest.mark.parametrize("rel", list(D30), ids=D30_IDS)
def test_g3b_n9_summary_json_usn_journal_id_is_the_current_journals_id(rel):
    _d30_premise(rel)
    r = _run(rel, "summary", "--json", keep_out=True)
    try:
        doc = json.loads(r.out)
    except ValueError as e:
        raise RedFixtureError("summary --json printed no JSON document: %s" % e)
    # acceptance 1.14.0 (K21 / LB26: USNJournalIDs, USNJournalID; K12: the id a padded hex string)
    cur = [e for e in doc.get("USNJournalIDs") or [] if e.get("IsCurrent") is True]
    _keep(len(cur) == 1 and int(cur[0]["USNJournalID"], 16) == JID_NEW,
          "USNJournalIDs must still mark the current journal 0x%016x: %r" % (JID_NEW, doc.get("USNJournalIDs"))
          + r.ctx(rel))
    raw = doc.get("USNJournalID")
    _keep(isinstance(raw, str) and re.fullmatch(r"0x[0-9a-f]{16}", raw), "USNJournalID is the K12 form: %r" % (raw,)
          + r.ctx(rel))
    v = jint(raw)
    assert v == JID_NEW, ("usn_journal_id is 0x%016x, the id of an earlier journal instance; the current journal's id "
                          "is 0x%016x" % (v, JID_NEW)) + r.ctx(rel)


N9_CONTROLS = [(LABJ, LABJ_NEW), ("step7/labBeforeF.raw", JID_OLD)]


@pytest.mark.parametrize("rel,jid", N9_CONTROLS, ids=["image-labJjournal", "image-labBeforeF"])
def test_g3b_n9_control_the_most_common_file_id_is_the_current_journals(rel, jid):
    """Not a RED. labJjournal (50 files carry the current id 0x01dd4e57f84a6362, 3 the first journal's) and labBeforeF
    (one journal, 0x01dd485de7522417, the lineage's first): the most common file id IS the current journal's id, so
    usn_journal_id is that id, an integer, today and after the fix."""
    if rel == LABJ:
        _labj_premise()
    else:
        BJ._labbeforef_journal(_img(rel))
    r = _run(rel, "summary", "--json", keep_out=True)
    doc = json.loads(r.out)
    v = doc.get("USNJournalID")                                   # acceptance 1.14.0 (K21, K12)
    assert isinstance(v, str) and re.fullmatch(r"0x[0-9a-f]{16}", v) and jint(v) == jid, "%r" % (v,) + r.ctx(rel)


# The current journal's id cannot be read (no `$Max`, or no journal): `summary` must not present a FILE's id as the
# journal's. The runner patches `_current_journal_id` to answer None, then runs `summary --json` through main() and
# rc_escalate, as the tool runs.
_N9_RUNNER = r'''
import sys
repo, img = sys.argv[1], sys.argv[2]
sys.path.insert(0, repo)
import forefst
forefst._current_journal_id = lambda *a, **k: None
sys.argv = ["forefst.py", img, "summary", "--json"]
try:
    _rc = forefst.main()
    sys.exit(forefst.rc_escalate(0 if _rc is None else _rc))
except SystemExit as _se:
    sys.exit(forefst.rc_escalate(0 if _se.code is None else _se.code))
'''


# RED 1.13.2 G3b N9: green with G3b's fix (the strict xfail mark removed)
@pytest.mark.parametrize("rel", ["step7/labG_2.raw", "step7/labBeforeF.raw"], ids=["image-labG_2", "image-labBeforeF"])
def test_g3b_n9_summary_json_without_the_current_id_presents_no_files_id_as_the_journals(rel, tmp_path):
    if rel == "step7/labBeforeF.raw":
        BJ._labbeforef_journal(_img(rel))
    else:
        _d30_premise(rel)
    runner = str(tmp_path / "n9_runner.py")
    with open(runner, "w") as fh:
        fh.write(_N9_RUNNER)
    p = subprocess.run([sys.executable, "-B", runner, REPO, _img(rel)], capture_output=True, timeout=TIMEOUT)
    err = p.stderr.decode("utf-8", "replace")
    _fx("Traceback" not in err, "the runner raised:\n" + err[-3000:])
    try:
        doc = json.loads(p.stdout.decode("utf-8", "replace"))
    except ValueError as e:
        raise RedFixtureError("summary --json printed no JSON document: %s\n%s" % (e, err[-2000:]))
    ctx = "\n[%s summary --json, current id unknown] rc=%d USNJournalID=%r USNJournalIDs=%r" % (
        rel, p.returncode, doc.get("USNJournalID"), doc.get("USNJournalIDs"))
    ids = doc.get("USNJournalIDs") or []
    assert "USNJournalID" not in doc, ("the current journal's id is not known, yet USNJournalID presents a file's "
                                       "id as the journal's") + ctx
    assert ids and all(e.get("IsCurrent") is None for e in ids) and sum(e.get("FileCount", 0) for e in ids) > 0, (
        "every id the files carry is listed with its file count, none marked current (N195)") + ctx


# ── latent (decision 34): `_usn_hole_text` across the ring's wrap (REVIEW_G3_correctness N2) ──
# A synthetic $J ring of 256 KiB whose surviving records lie at offsets 0x30000..0x33000: with `base` 0x80000 the
# journal has wrapped (USN = 0x80000 + offset on this lap; the ring maps USN u to offset u % 256 KiB, KNOWLEDGE_INTAKE A7
# and the tool's own `usn % alloc == offset` check), with `base` 0 it has not. A file points past the last record, so
# records are missing (A10), and the image stores part of the missing range as a hole (C8 = B).

_G3B_ALLOC = 0x40000
_G3B_JID = JID_OLD                        # the synthetic journal's id (any FILETIME-shaped id)


def _g3b_ring(base, first_cluster):
    """(j, records): 3 clusters of USN_RECORD_V3s (BJ's builder) from `first_cluster`, USN = base + offset."""
    j = bytearray(_G3B_ALLOC)
    for c in range(first_cluster, first_cluster + 3):
        off = 0
        while True:
            usn = base + c * CS + off
            rec = BJ._usn_record(usn, "w%02x_%04x.txt" % (c, off), 0x10 + c, _G3B_JID + usn)
            if off + len(rec) > CS - 0x60:
                break
            j[c * CS + off:c * CS + off + len(rec)] = rec
            off += len(rec)
    recs = AB.F.parse_usn_records(bytes(j))
    _fx(len(recs) == 114 and recs[0].usn == base + first_cluster * CS, "the synthetic ring carries %d records" % len(recs))
    return bytes(j), recs


def _g3b_hole_report(monkeypatch, base, first_cluster, ptr, holes):
    """`_usn_journal_report` over the ring, one file pointing at `ptr` with the journal's own id, `holes` the $J
    ranges the image stores as holes. Returns (end of the last record, the statement's sentences)."""
    F = AB.F
    BJ._fresh(monkeypatch)
    j, recs = _g3b_ring(base, first_cluster)
    end = recs[-1].usn + recs[-1].record_length
    monkeypatch.setattr(F, "walk_directory_tree", lambda *a, **k: iter(
        [{"is_dir": False, "usn": ptr, "usn_journal_id": _G3B_JID, "name": "points_past.txt"}]))
    buf = io.StringIO()
    st = F._usn_journal_report(None, 0, CS, None, {}, recs, _G3B_JID, j, len(j), holes, "hole", indent="", file=buf)
    _fx(len(st["missing"]) == 1 and st["missing"][0]["ptr"] == ptr, "the missing range is not the planted one: %r"
        % (st["missing"],))
    return end, _sentences(buf.getvalue().splitlines())


def _g3b_hole_sentences(sentences):
    return [s for s in sentences if _HOLE.search(s) and _HOLE_CAUSE.search(s)]


def _g3b_usns(sentences):
    return [int(u) for s in sentences for u in re.findall(r"\bUSN (\d+)", s)]


# (base, first cluster, pointer, holes, the hole's first USN, the hole's USN end or None when it runs through the
# pointer). `wrapped-after`: the hole lies past the ring's wrap point (offsets 0x2000..0x9000 = USN 794,624..
# 823,296, through the pointer at USN 819,200); `wrapped-before` (control): before it (offsets 0x38000..0x3a000 = USN
# 753,664..761,856); `unwrapped` (control, the corpus shape): USN = offset.
G3B_WRAP = {
    "wrapped-after": (0x80000, 0x30, 0xC8000, [(0x2000, 0x9000)], 0xC2000, None),
    "wrapped-before": (0x80000, 0x30, 0xC8000, [(0x38000, 0x3A000)], 0xB8000, 0xBA000),
    "unwrapped": (0, 0x10, 0x28000, [(0x20000, 0x29000)], 0x20000, None),
}


# RED 1.13.2 G3b latent: green with G3b's fix (the strict xfail mark removed)
def test_g3b_usn_hole_text_places_a_hole_past_the_rings_wrap_at_its_own_usn(monkeypatch):
    base, fc, ptr, holes, a_usn, _b = G3B_WRAP["wrapped-after"]
    end, ss = _g3b_hole_report(monkeypatch, base, fc, ptr, holes)
    ctx = "\n[the wrapped ring: end of the last record USN %d, pointer USN %d]\n%s" % (end, ptr, "\n".join(ss))
    _fx(_G3B_ALLOC > ptr - end > AB.F.USN_MAX_RECORD, "the plant is not a missing range shorter than the ring")
    _keep([s for s in ss if _num(ptr).search(s)], "A10's statement names the pointer" + ctx)
    hole = _g3b_hole_sentences(ss)
    assert hole, "the missing range lies over a hole of the image: nothing says so (C8 = B)" + ctx
    below = [u for u in _g3b_usns(hole) if u < end]
    assert not below, ("the hole sentence places the hole at USN %r, below the end of the surviving records (USN %d): "
                       "the ring's wrap is not applied" % (below, end)) + ctx
    assert a_usn in _g3b_usns(hole), "the hole starts at USN %d (offset 0x2000 after the wrap)" % a_usn + ctx
    assert [s for s in ss if re.search(r"\b%d byte\(s\) before it\b" % (a_usn - end), s)], (
        "the %d stored bytes between the last record and the hole are not counted" % (a_usn - end)) + ctx


# RED 1.13.2 G3b latent: green with G3b's fix (the strict xfail mark removed)
def test_g3b_usn_hole_text_states_a_hole_when_the_missing_range_is_longer_than_the_ring(monkeypatch):
    ptr = 0x108000                            # USN 1,081,344: more than one whole ring (256 KiB) past the end
    end, ss = _g3b_hole_report(monkeypatch, 0x80000, 0x30, ptr, [(0x20000, 0x21000)])
    ctx = "\n[end of the last record USN %d, pointer USN %d]\n%s" % (end, ptr, "\n".join(ss))
    _fx(ptr - end > _G3B_ALLOC, "the pointer is not a whole ring past the end")
    hole = _g3b_hole_sentences(ss)
    assert hole, ("the missing range covers every byte of $J, and the image stores 4,096 of them as a hole: nothing "
                  "says so (C8 = B)") + ctx
    assert [s for s in hole if re.search(r"\b4096\b", s)], "the 4,096 hole bytes are not counted" + ctx
    assert not [u for u in _g3b_usns(hole) if u < end], "a hole is placed below the surviving records' end" + ctx


@pytest.mark.parametrize("case", ["wrapped-before", "unwrapped"])
def test_g3b_usn_hole_text_control_a_hole_the_mapping_already_places(monkeypatch, case):
    """Not a RED. A hole before the ring's wrap point, and an unwrapped journal (the corpus shape: every corpus journal
    with a missing range): the hole's first USN is stated, none below the end -- today and after the fix."""
    base, fc, ptr, holes, a_usn, b_usn = G3B_WRAP[case]
    end, ss = _g3b_hole_report(monkeypatch, base, fc, ptr, holes)
    hole = _g3b_hole_sentences(ss)
    ctx = "\n".join(ss)
    assert hole and a_usn in _g3b_usns(hole) and not [u for u in _g3b_usns(hole) if u < end], ctx
    if b_usn is not None:
        # acceptance 1.14.0 (N406): the range is named by its first and LAST USN ("from USN 753664 to USN 761855"),
        # the end exclusive no longer
        assert b_usn - 1 in _g3b_usns(hole) and b_usn not in _g3b_usns(hole), ctx
    assert [s for s in ss if re.search(r"\b%d byte\(s\) before it are stored and read as zeros\b" % (a_usn - end), s)], ctx


# ── latent (decision 34): `timeline`'s NOTE says only what was read (REVIEW_G3_correctness N3) ──

# RED 1.13.2 G3b latent: green with G3b's fix (the strict xfail mark removed)
def test_g3b_timeline_note_claims_nothing_about_pointers_it_did_not_read(monkeypatch, capsys, tmp_path):
    # N405 (wave B part 3): the premise below runs parse_usn_records, which records skip notes; the run registers are
    # made fresh first (monkeypatch restores them), so its note does not land in forefst's real registers and print
    # after pytest's summary line
    BJ._fresh(monkeypatch)
    jr = BJ._Journal(tmp_path, 8)                          # every $J cluster a hole of the file
    with open(jr.path, "r+b") as fh:                       # clusters 0-3: bytes that parse as no USN record, not zeros
        fh.seek(BJ.J_PLCN * BJ.HCS)
        fh.write(b"\xab" * 4 * BJ.HCS)
    with open(jr.path, "rb") as fh:
        fh.seek(BJ.J_PLCN * BJ.HCS)
        data = fh.read(8 * BJ.HCS)
    _fx(any(data) and not BJ._carve_journal(data) and not AB.F.parse_usn_records(data),
        "the plant is not a $J of non-zero bytes that hold no record")
    ents = [BJ._entry(1, 20000, BJ.JID_ONE, name="points_into_the_journal.txt", ts=BJ.JID_ONE + 10 ** 7)]
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, "timeline", (), ents)
    ctx = BJ._hctx("timeline", (), rc, out, err)
    _keep(re.search(r"NOTE: no USN events", out), "the timeline still says it holds no USN event" + ctx)
    said = [ln for ln in (out + err).splitlines() if re.search(r"(?i)\bno file points into\b", ln)]
    assert not said, ("a file on this volume points into the journal (LastUsn 20,000, its id), and the pointers were "
                      "not read here; the NOTE says no file points into it: %r" % said[:1]) + ctx


def test_g3b_timeline_note_control_an_all_zero_journal_no_file_points_into(monkeypatch, capsys, tmp_path):
    """Not a RED. N131's shape (an allocated $J of written zeros; every LastUsn and id 0): the per-file witness IS read
    there, so the NOTE's 'no file points into it' is a measured statement; exit 0 -- today and after the fix."""
    jr = BJ._Journal(tmp_path, 8, zeros=range(8))
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, "timeline", (), BJ._n131_entries())
    ctx = BJ._hctx("timeline", (), rc, out, err)
    assert rc == 0 and re.search(r"NOTE: no USN events .*holds no records and no file points into it", out), ctx


# ── refsanalysis `supb --verify` on an unreadable checkpoint copy: one verdict for one condition ──

_VERIFY_ROW = re.compile(r"^(\w+)\s+(OK|FAIL|WARN)\s+(.*?)\s*$")


def _verify_rows(lines):
    """refsanalysis `--verify`'s table: {check: [(result, details)]} (a check may repeat: supb_backup_checksum)."""
    rows = {}
    for ln in lines:
        m = _VERIFY_ROW.match(ln)
        if m:
            rows.setdefault(m.group(1), []).append((m.group(2), m.group(3)))
    return rows


# RED 1.13.2 G3b supb-verify: green with G3b's fix (the strict xfail mark removed)
@pytest.mark.parametrize("plant", N374_PLANTS, ids=N374_PLANT_IDS)
def test_g3b_supb_verify_gives_an_unreadable_checkpoint_copy_one_verdict(plant):
    lcn, outs = _n374(plant)
    r = outs[(REFSANALYSIS, ("supb", "--verify"))]
    rows = _verify_rows(r.prose)
    copy = [(k, res, det) for k, v in rows.items() if re.fullmatch(r"chkp_\d+_checksum", k) for res, det in v
            if AB._lcn_re(lcn).search(det)]
    _fx(len(copy) == 1, "one checksum row of the copy at LCN 0x%x expected: %r" % (lcn, copy) + r.ctx(plant))
    k, res, _det = copy[0]
    idx = int(k.split("_")[1])
    _keep(r.rc == 2, "T1: an unreadable checkpoint copy exits 2" + r.ctx(plant))
    _keep(res == ("WARN" if plant.startswith("hole") else "FAIL"), "the copy's own row keeps its verdict: a hole cannot "
          "be verified (WARN), zeros fail (FAIL); it says %s" % res + r.ctx(plant))
    sig = rows.get("all_checkpoint_signatures") or []
    _fx(len(sig) == 1, "one all_checkpoint_signatures row expected: %r" % sig + r.ctx(plant))
    sres, sdet = sig[0]
    assert "??" not in sdet, ("the signature row shows copy #%d as '??', a value the copy does not have: %r"
                              % (idx, sdet)) + r.ctx(plant)
    assert sres == res, ("one condition, two verdicts: copy #%d's own row says %s, the signature row %s"
                         % (idx, res, sres)) + r.ctx(plant)
    assert re.search(r"#%d\b[^,]*\b(?:unreadable|could not be read)\b" % idx, sdet), (
        "the signature row does not say that copy #%d could not be read: %r" % (idx, sdet)) + r.ctx(plant)
    other = _ZEROS_SAID if plant.startswith("hole") else _HOLE_WORDS
    assert not other.search(sdet), "R1a / R1b: the signature row words the copy as the other kind: %r" % sdet \
        + r.ctx(plant)


def test_g3b_supb_verify_control_the_intact_base_signatures_row():
    """Not a RED. The unplanted base (read-only; pinned first): both copies carry their signature, so the signature row
    is 'OK  #1=CHKP, #2=CHKP' and every copy's checksum row OK -- today and after the fix (its form unchanged)."""
    AB.Vol(AB.IMG, _img(BASE)).pin()
    r = _run(BASE, "supb", "--verify", tool=REFSANALYSIS)
    rows = _verify_rows(r.prose)
    assert rows.get("all_checkpoint_signatures") == [("OK", "#1=CHKP, #2=CHKP")], r.ctx(BASE)
    assert [res for k, v in rows.items() if re.fullmatch(r"chkp_\d+_checksum", k) for res, _d in v] == ["OK", "OK"], \
        r.ctx(BASE)


def test_g3b_matchers_accept_corrected_wording_and_reject_todays_lines():
    """Not a RED: the G3b helpers on today's lines and on the corrected forms."""
    # the streaming JSON check: an export alone passes; prose before it, text after it, a bad element do not
    ev = {"Timestamp": "2026-09-27T08:12:42.6135580Z", "TimeSource": "USN record", "Source": "USN", "OID": "0x706",
          "Name": "m5.txt", "PathToday": None, "Event": "FILE_CREATE"}                  # acceptance 1.14.0
    good = json.dumps([ev, dict(ev, Name="b, \"quoted\" ] name")], indent=2, ensure_ascii=False) + "\n"
    assert _json_array_check(io.StringIO(good), TIMELINE_KEYS) == (2, None)
    assert _json_array_check(io.StringIO("[]\n"), TIMELINE_KEYS) == (0, None)
    for bad in ("  Journal instances: the journal was re-created: its numbering restarted at USN 0.\n" + good,
                good + "[forefst] note: something\n", good.replace('"Source"', '"Src"', 1), good[:-3],
                "[" + json.dumps(ev) + ",]"):
        n, e = _json_array_check(io.StringIO(bad), TIMELINE_KEYS)
        assert e is not None, bad[:80]
    # a large export streams through the chunked reader (elements split across the 1 MiB chunks)
    big = json.dumps([dict(ev, Name="n%06d" % i) for i in range(30000)], indent=2) + "\n"
    assert len(big) > 3 << 20 and _json_array_check(io.StringIO(big), TIMELINE_KEYS) == (30000, None)
    # 1.14.0 (N312): the timeline envelope, Events streamed the same way
    env = json.dumps({"SourceCounts": {"USN": 2}, "Statements": ["a, ] b"], "Events": [ev, ev]}, indent=2) + "\n"
    assert _json_envelope_check(io.StringIO(env), TIMELINE_KEYS) == (2, None)
    for bad in (good, env + "x", env.replace('"Statements"', '"Notes"'), env[:-4],
                json.dumps({"SourceCounts": {}, "Statements": [], "Events": [dict(ev, Src=1)]})):
        assert _json_envelope_check(io.StringIO(bad), TIMELINE_KEYS)[1] is not None, bad[:80]
    bigenv = json.dumps({"SourceCounts": {}, "Statements": [], "Events": [dict(ev, Name="n%06d" % i)
                                                                         for i in range(30000)]}, indent=2)
    assert _json_envelope_check(io.StringIO(bigenv), TIMELINE_KEYS) == (30000, None)
    # the timeline row rule and header are AV's (one rule)
    assert AV._CSV_TABLES[0][0] == TIMELINE_CSV_HEADER
    assert _TL_ROW(["2026-09-27T08:12:42.6135580Z", "USN record", "USN", "0x706", "m5.txt", "", "FILE_CREATE"])
    assert not _TL_ROW(["  Journal instances: the journal was re-created", "x", "y", "z", "w", "v", "u"])
    # supb --verify rows: today's hole line refused, the corrected one accepted
    today = ["all_checkpoint_signatures  FAIL    #1=??, #2=CHKP",
             "chkp_1_checksum            WARN    LCN 0x13f8 (offset 0x23f8000): unreadable: it carries no CHKP signature: "
             "the image stores it as a hole: not captured, or zero on the disk; the cause cannot be told from the image"]
    rows = _verify_rows(today)
    assert rows["all_checkpoint_signatures"] == [("FAIL", "#1=??, #2=CHKP")] and rows["chkp_1_checksum"][0][0] == "WARN"
    fixed = _verify_rows(["all_checkpoint_signatures  WARN    #1 could not be read, #2=CHKP"])["all_checkpoint_signatures"]
    assert re.search(r"#1\b[^,]*\b(?:unreadable|could not be read)\b", fixed[0][1]) and "??" not in fixed[0][1]
    assert not re.search(r"#2\b[^,]*\b(?:unreadable|could not be read)\b", fixed[0][1])
    # the hole sentence's USNs are read after the digits are normalised
    ss = _sentences(["The image stores $J from USN 794,624 on as a hole, through the record at USN 819,200: not "
                     "captured, or zero on the disk; the cause cannot be told from the image."])
    assert _g3b_hole_sentences(ss) and _g3b_usns(_g3b_hole_sentences(ss)) == [794624, 819200]
    assert not _g3b_hole_sentences(_sentences(["The 61,520 byte(s) before it are stored and read as zeros."]))
