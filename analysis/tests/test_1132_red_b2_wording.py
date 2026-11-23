"""1.13.2 RED cases, group b2_wording: plan rows C3 (with N149), C4, C5, C7 and I7 (with N147).

Plan: `analysis/reports/v1.13.2/PLAN_1.13.2.md` section 2 C (rows C3, C4, C5, C7), section 2 I (row I7), section 5
"RED first", section 7 (O4, O5) and decision 19 (the maintainer's bar: every RED fails on 1.13.1 BECAUSE of the
defect, not because of an artefact, and is independently confirmed). N147 and N149: `RUNNING_LOG.md`. Report, with
the observed or expected failure of every node: `analysis/reports/v1.13.2/red/RED_b2_wording.md`.

What each RED asserts (the row's Acceptance column)
---------------------------------------------------
C3    `summary` gives its file counts per residency category (inline / extents / snapshot-shared / unallocated;
      E87) and they sum to the file total -- or the non-inline count is relabelled "not inline" (O5 open, both
      branches accepted). A number labelled extent-backed never includes snapshot-shared or unallocated files.
N149  (folded into C3: "its acceptance 'sum to the file total' needs the file total defined") the file total counts
      each FILE once, as "Total file size" already does (K184): a file with k hard-link names is one file. A count
      of names, if printed, is labelled as names.
C4    `integrity` and `summary` print the same offset for each superblock copy (on a partition that does not start
      at byte 0). (The P0.3 half of the row is a battery change, not a pytest.)
C5    the `deleted --full` footer lists only what ran (a view carves nothing: only `export deleted` does), and
      `deleted --carve` without an export directory is not silently accepted -- O4 settles how; both of its
      branches pass (exit 1 with a usage message naming --carve, or a note that the view carves nothing).
C7    `deleted` prints no bare "resident", "non-resident" or "RESIDENT" (only the E87 words), and an AST scan of
      cmd_deleted's print strings (and the label constants it prints) finds 0 bare uses.
I7    an unknown `export` subverb is refused with exit 1 and the list of subverbs; nothing is written; the
      documented bare `export -o DIR` keeps working (control).
N147  `export deleted FLAG VALUE DIR` gives VALUE to FLAG and exports into DIR, as `export deleted DIR FLAG VALUE`
      does (control); `deleted` refuses a stray positional (`deleted report`) with exit 1.

Volumes
-------
* ``[synthetic]`` -- 1 MiB ReFS 3.14 volumes written into pytest's tmp dir, from the builders of
  `test_1132_red_a_bootstrap.py` (VBR, superblocks, checkpoints, root tables) and `test_1132_red_b2_deleted.py`
  (a directory tree with live rows and slack remnants), imported, not copied. No corpus image is read.
  - C3/N149: the tool runs through a small driver that wraps the REAL `walk_directory_tree` and overrides, on
    named rows only, the fields a 1 MiB synthetic volume cannot carry in its bytes: the data residency
    (`data_form`, set to the tool's own E87 constants) and, for two names of one file, the hard-link count and
    names. The FileRef of every row comes from the bytes (a name row's value+0x08:+0x00), and the driver reports
    it so the test can check it. Everything else -- the counting, the labels, the JSON -- is the tool's.
  - C4: the a_bootstrap volume placed 1 MiB into the file and opened with `--partition-start 0x100000`.
* ``[image]`` -- corpus images opened READ-ONLY (never damaged, never copied): win11refstestmftecmd (N149, C7 running
  case), win11refs2tsnapshots (C3: 3 snapshot-shared files), win11refsmini (C4, the measured image),
  win11refs8gtestmove_aftermove (C7, the measured image). Skipped when absent. ``pytest -k "not image"`` runs the
  rest.

How a RED can fail only because of its defect (the convention of test_1132_red_a_bootstrap.py)
-----------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)``; the fix commit removes the mark and an XPASS fails
  the run. Only a plain ``assert`` states the acceptance.
* A fixture that is not what the case needs, a crash or a timeout raises ``RedFixtureError``; a property 1.13.1
  already has and the fix must keep raises ``KeptPropertyBroken``. Neither is an AssertionError.
* Each synthetic RED has a control that passes on 1.13.1 and differs from it only in the defect's trigger (no
  snapshot-shared/unallocated file; no hard link; partition at byte 0 is not used -- the offsets are compared on
  the same volume; the flag after the directory; a valued flag's value instead of a stray positional; a real
  subverb; `--full` without `--carve`), and `test_b2w_matchers` runs every reader on 1.13.1's own output (the
  published 1.13.1 samples) and on a layout a fix could print.
"""
import ast
import contextlib
import csv
import io
import json
import os
import re
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                              # noqa: E402  (K21 readers)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (VBR/SUPB/root pages, exceptions)

FOREFST, REFSANALYSIS = AB.FOREFST, AB.REFSANALYSIS
TIMEOUT = 1800
CS = AB.CS
RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep, _red = AB._fx, AB._keep, AB._red
_SYN = ["--partition-start", "0"]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Running the tools
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _run(argv, cwd, timeout=TIMEOUT):
    """(rc, stdout, stderr) of `python -B argv...`. A traceback or a timeout is a fixture error, never the defect."""
    try:
        r = subprocess.run([sys.executable, "-B"] + list(argv), capture_output=True, text=True, timeout=timeout,
                           cwd=cwd)
    except subprocess.TimeoutExpired:
        raise RedFixtureError("timeout: %s" % " ".join(argv))
    if "Traceback (most recent call last)" in r.stderr:
        raise RedFixtureError("the tool crashed (a crash is never the defect under test):\n" + r.stderr[-3000:])
    return r.returncode, r.stdout, r.stderr


def _tool(tool, image, *args, cli=(), cwd=None):
    return _run([tool, image] + list(args) + list(cli), cwd or os.path.dirname(image))


def _ctx(rc, out, err=""):
    return "\n| rc=%s\n%s\n--- stderr ---\n%s" % (rc, out[-5000:], err[-2500:])


def _listing(d):
    """Every entry under d, relative, directories with a trailing '/'."""
    got = []
    for dp, dns, fns in os.walk(d):
        for x in dns:
            got.append(os.path.relpath(os.path.join(dp, x), d) + "/")
        for x in fns:
            got.append(os.path.relpath(os.path.join(dp, x), d))
    return sorted(got)


def _bd():
    """The b2_deleted volume builder (one builder for the batch). Missing -> a fixture error, never a skip."""
    try:
        import test_1132_red_b2_deleted as BD
        for a in ("DirVol", "_row", "_name_key", "_file_value", "_T", "_S"):
            getattr(BD, a)
    except (ImportError, AttributeError) as e:
        raise RedFixtureError("the b2_deleted volume builder is not available: %r" % (e,))
    return BD


def _dir_volume(path, files, slack=(), log=False):
    """A synthetic volume: root 0x600 -> directory `d` (table 0x761) holding `files` as live name rows and `slack`
    as remnant rows in the page's free space. Each entry is (name, file id); the FileRef is 0x761:<file id>. `log`: the
    volume carries an empty MLog (DirVol's option), for the nodes that run `summary` (Q-D D3: it reads the log)."""
    BD = _bd()
    v = BD.DirVol(log=log)
    live = [BD._row(BD._name_key(n), BD._file_value(fid, 0x761, BD._T)) for n, fid in files]
    dead = [BD._row(BD._name_key(n), BD._file_value(fid, 0x761, BD._T + (3 + i) * BD._S))
            for i, (n, fid) in enumerate(slack)]
    v.objects = v.tree({0x600: {"name": ""},
                        0x761: {"parent": 0x600, "name": "d", "files": live, "slack": dead}})
    return v.write(path)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Readers (each one checked by test_b2w_matchers on 1.13.1's own output and on a fixed layout)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# ── C3 / N149: the file counts ────────────────────────────────────────────────────────────────────────────────

_E87 = {"DATA_INLINE": "inline", "DATA_EXTENTS": "extents", "DATA_SNAPSHOT_SHARED": "snapshot-shared",
        "DATA_SPARSE": "unallocated", "DATA_UNKNOWN": "unknown"}
_CATWORD = r"(not[ -]inline|non-inline|snapshot-shared|extent-backed|extents|inline|unallocated|unknown)"
_N_WORD = re.compile(r"(\d[\d,]*)[ \t]+" + _CATWORD + r"\b", re.I)               # one line only
_WORD_N = re.compile(r"\b" + _CATWORD + r"[ \t]*(?:files?)?[ \t]*:[ \t]*(\d[\d,]*)", re.I)


def _norm_cat(w):
    w = w.lower().replace("_", "-")
    if w in ("not inline", "not-inline", "non-inline"):
        return "not inline"
    if w in ("extent-backed", "extents"):
        return "extents"
    return w


def _cats(text):
    """{category: count} from 'N word' pairs, or else 'word: N' pairs (first occurrence of each category wins)."""
    got = {}
    for n, w in _N_WORD.findall(text):
        got.setdefault(_norm_cat(w), int(n.replace(",", "")))
    if not got:
        for w, n in _WORD_N.findall(text):
            got.setdefault(_norm_cat(w), int(n.replace(",", "")))
    return got


def _content_section(out):
    """The indented lines of the 'File System Content' block (forefst and refsanalysis print one each)."""
    i = out.find("File System Content")
    _fx(i >= 0, "no 'File System Content' block in the output")
    body, started = [], False
    for ln in out[i:].splitlines()[1:]:
        if not started and ln.strip() and set(ln.strip()) <= set("-="):
            continue                                     # the rule under the heading
        started = True
        if not ln.strip() or not ln.startswith(" "):
            break
        body.append(ln)
    _fx(body, "the 'File System Content' block is empty")
    return body


def _file_counts(block):
    """(file total, {category: count}, the lines read). The total is the first number on the 'Files' line that is
    not followed by 'name(s)'; the categories are read from that line and the lines indented below it."""
    for k, ln in enumerate(block):
        m = re.match(r"^(\s*)Files\b[^:\n]*:\s*(.*)$", ln)
        if not m:
            continue
        ind = len(m.group(1))
        region = [ln] + [x for x in _takewhile_indented(block[k + 1:], ind)]
        total = None
        for n, word in re.findall(r"(\d[\d,]*)\s*([A-Za-z-]*)", m.group(2)):
            if word.lower().startswith("name"):
                continue
            total = int(n.replace(",", ""))
            break
        return total, _cats("\n".join(region)), region
    raise RedFixtureError("no 'Files:' line in the File System Content block:\n" + "\n".join(block))


def _takewhile_indented(lines, ind):
    for x in lines:
        if len(x) - len(x.lstrip(" ")) <= ind:
            return
        yield x


def _count_mismatch(total, cats, want):
    """None when (total, cats) state `want` ({'total': n, category: n}); else what is wrong."""
    if total != want["total"]:
        return "file total %s, expected %d" % (total, want["total"])
    if not cats:
        return "no per-category count printed"
    for k, n in sorted(cats.items()):
        exp = want["total"] - want.get("inline", 0) if k == "not inline" else want.get(k, 0)
        if n != exp:
            return "%d labelled %r, expected %d" % (n, k, exp)
    if "not inline" in cats:
        if "inline" not in cats:
            return "'not inline' printed without the inline count"
        s = cats["inline"] + cats["not inline"]
    else:
        s = sum(cats.values())
    if s != want["total"]:
        return "the categories sum to %d, not the file total %d" % (s, want["total"])
    return None


def _assert_counts(total, cats, lines, variants, what):
    """Pass when the printed counts state ONE of `variants` ({name: want}) consistently."""
    why = {v: _count_mismatch(total, cats, w) for v, w in variants.items()}
    if not all(why.values()):
        return
    raise AssertionError("%s: %s\n  printed: %s\n  expected one of: %s"
                         % (what, "; ".join("%s -> %s" % kv for kv in sorted(why.items())),
                            " | ".join(x.strip() for x in lines), variants))


def _oracle(rows):
    """rows: (identity, category). {'names': per-row counts, 'files': per-identity counts}."""
    names = {"total": len(rows)}
    for _i, c in rows:
        names[c] = names.get(c, 0) + 1
    by_id = {}
    for i, c in rows:
        by_id.setdefault(i, set()).add(c)
    _fx(all(len(s) == 1 for s in by_id.values()), "one file with two residencies: %r" %
        {i: s for i, s in by_id.items() if len(s) > 1})
    files = {"total": len(by_id)}
    for s in by_id.values():
        c = next(iter(s))
        files[c] = files.get(c, 0) + 1
    return {"names": names, "files": files}


# ── C4: superblock offsets ────────────────────────────────────────────────────────────────────────────────────

_LCN_OFF = re.compile(r"\bLCN\s+(0x[0-9a-f]+)\s*\(offset\s+(0x[0-9a-f]+)\)", re.I)


def _offsets(out, lcns):
    """{lcn: [offsets printed on lines naming that LCN]} for the given LCNs."""
    got = {}
    for ln in out.splitlines():
        for m in _LCN_OFF.finditer(ln):
            lcn = int(m.group(1), 16)
            if lcn in lcns:
                got.setdefault(lcn, []).append(int(m.group(2), 16))
    return got


def _raised(exc, fn, *args):
    """The EXC that FN(*args) raised, or None when it raised nothing: for a control that must see a matcher refuse
    (N204: the expected exception is a result, not a swallowed one)."""
    try:
        fn(*args)
    except exc as e:
        return e
    return None


def _assert_same_offsets(summ, integ, lcns):
    s, i = _offsets(summ, lcns), _offsets(integ, lcns)
    bad = []
    for lcn in sorted(lcns):
        if not s.get(lcn) or not i.get(lcn):
            bad.append("LCN %#x: summary %s, integrity %s (each must print the copy's offset)"
                       % (lcn, s.get(lcn), i.get(lcn)))
        elif set(s[lcn]) != set(i[lcn]):
            bad.append("LCN %#x: summary offset %s, integrity offset %s"
                       % (lcn, "/".join("%#x" % x for x in s[lcn]), "/".join("%#x" % x for x in i[lcn])))
    assert not bad, "the two commands print different offsets for the same superblock copy:\n  " + "\n  ".join(bad)


# ── C5: the `deleted` methods footer ──────────────────────────────────────────────────────────────────────────

def _footer(out):
    i = out.find("── Recovery methods")
    _fx(i >= 0, "no '── Recovery methods' footer in the output")
    lines = []
    for ln in out[i:].splitlines():
        if not ln.strip():
            break
        lines.append(ln)
    return lines


def _sentences(lines):
    text = re.sub(r"\s+", " ", " ".join(lines)).replace("── Recovery methods ──", "").strip()
    return [s for s in re.split(r"(?<=[.;!?])\s+", text) if s]


_EXEMPT = re.compile(r"\b(export|not|no|only|without|never|needs?|requires?|skipped)\b", re.I)


def _claims_carve_ran(lines):
    """Sentences that describe THIS run (Mode:/Ran:/'This was'/'This is') and say it carved."""
    return [s for s in _sentences(lines)
            if re.match(r"(Mode:|Ran:|This (was|is)\b)", s) and re.search(r"\bcarv", s, re.I)
            and not _EXEMPT.search(s)]


def _claims_view_full_carves(lines):
    """Sentences that say `deleted --full` (the view) carves, without naming the export that does."""
    return [s for s in _sentences(lines)
            if re.search(r"deleted --full", s) and re.search(r"\bcarv", s, re.I) and not re.search(r"export", s)]


# ── C7: the retired bare word ─────────────────────────────────────────────────────────────────────────────────

# "resident", "non-resident", "RESIDENT" as words; not `resident-all` (a subverb), IsResident / is_resident
# (identifiers), residency / DataResidency.
BARE = re.compile(r"(?i)\b(?:non-)?resident\b(?!-all)")


def _bare_lines(text):
    return [ln for ln in text.splitlines() if BARE.search(ln)]


# ── I7: the subverb list ──────────────────────────────────────────────────────────────────────────────────────

# docs/tools/forefst.md "export" table and FORENSIC_SUBCOMMANDS["export"]: the eight documented subverbs.
_SUBVERBS = ("file", "ads", "reparse", "resident-all", "snapshots", "deleted", "recyclebin", "metadata")


def _lists_subverbs(text):
    return all(re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(s), text) for s in _SUBVERBS)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The readers, on 1.13.1's own output and on a layout a fix could print
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_OLD_SUMMARY = """------------------------------------------------------------------------------
File System Content (from directory walk)
------------------------------------------------------------------------------
  Directories:        237
  Files:              1507 (274 inline + 1233 extent-backed)
  Total file size:    1.3 GB
  Hard-linked:        168 files sharing 450 names
  File data:          not examined — every figure above comes from metadata;
                      `integrity` checks files that carry an integrity stream
"""                                                       # published win11refstestmftecmd/forefst/summary.txt:88-102

_OLD_INTEGRITY = """  Superblock copies:       3 intact
      [PRIMARY] LCN 0x1e (offset 0x1e000) — checksum OK
      [backup ] LCN 0xfbffd (offset 0xfbffd000) — checksum OK
      [backup ] LCN 0xfbffe (offset 0xfbffe000) — checksum OK
"""                                                       # published win11refstestmftecmd/forefst/integrity.txt:44-47
_OLD_SUMMARY_SUPB = """  SUPB primary     LCN 0x1e (offset 0x101e000)  — checksum OK
  CHKP primary     LCN 0x1f28 (offset 0x2f28000)  — checksum OK, vclock=1234
  SUPB backup      LCN 0xfbffd (offset 0xfcffd000)  — checksum OK
  SUPB backup      LCN 0xfbffe (offset 0xfcffe000)  — checksum OK
"""                                                       # published summary.txt:23-32 (CHKP line abridged)

_OLD_FULL_FOOTER = """── Recovery methods ──
  Mode: full.  Ran: Trash table (0xD), checkpoint diff, B+-tree node-slack scan (live + orphan pages).
  This was `--full` (complete): live + whole-volume orphan-page slack + carve. `deleted` (no
  --full) is the quicker, live-pages-only pass.
  Fine-grained: --no-slack · --scan-pages · --orphans · --carve · --search SUB · --csv/--json/--jsonl FILE · `export deleted DIR`.
"""
_OLD_RECOVERY_FOOTER = """── Recovery methods ──
  Mode: recovery.  Ran: Trash table (0xD), checkpoint diff, B+-tree node-slack scan (live pages only).
  This is `recovery` (quick, seconds): live-page slack only. Run `deleted --full` to ALSO scan
  orphan pages (the freed pages of deleted objects) and carve extent-backed content — that reads
  the WHOLE volume once (about a minute per 60-100 GB), but it typically finds far more.
  Fine-grained: --no-slack · --scan-pages · --orphans · --carve · --search SUB · --csv/--json/--jsonl FILE · `export deleted DIR`.
"""
_NEW_FULL_FOOTER = """── Recovery methods ──
  Mode: full.  Ran: Trash table (0xD), checkpoint diff, B+-tree node-slack scan (live + orphan pages).
  This was `--full` (complete): live + whole-volume orphan-page slack. A view carves nothing: `export
  deleted --full DIR` also carves extent-backed content.
"""
_NEW_RECOVERY_FOOTER = """── Recovery methods ──
  Mode: recovery.  Ran: Trash table (0xD), checkpoint diff, B+-tree node-slack scan (live pages only).
  This is `recovery` (quick, seconds): live-page slack only. Run `deleted --full` to ALSO scan orphan
  pages; `export deleted --full DIR` also carves extent-backed content.
"""


def test_b2w_matchers():
    """Control: every reader, on 1.13.1's published output and on a layout a fix could print."""
    # C3 / N149
    total, cats, lines = _file_counts(_content_section(_OLD_SUMMARY))
    _keep((total, cats) == (1507, {"inline": 274, "extents": 1233}), "1.13.1's Files line read as %r %r"
          % (total, cats))
    _keep(_count_mismatch(total, cats, {"total": 1225, "inline": 214, "extents": 1011}) == "file total 1507, "
          "expected 1225", "1.13.1's per-name total is not read as the N149 defect")
    c3 = {"total": 4, "inline": 1, "extents": 1, "snapshot-shared": 1, "unallocated": 1}
    _keep(_count_mismatch(4, {"inline": 1, "extents": 3}, c3) == "3 labelled 'extents', expected 1",
          "1.13.1's 'N extent-backed' over shared/unallocated files is not read as the C3 defect")
    for fixed in ("  Files:              4 (1 inline + 1 extents + 1 snapshot-shared + 1 unallocated)\n",
                  "  Files:              4\n    inline:           1\n    extents:          1\n"
                  "    snapshot-shared:  1\n    unallocated:      1\n",
                  "  Files:              4 (1 inline + 3 not inline)\n",
                  "  Files:              4 (5 names; 1 inline + 1 extent-backed + 1 snapshot-shared + 1 unallocated)\n"):
        t, c, _l = _file_counts(("  Directories:        1\n" + fixed + "  Total file size:    500 B").splitlines())
        _keep(_count_mismatch(t, c, c3) is None, "a fixed layout is not accepted: %r -> %r %r" % (fixed, t, c))
    t, c, _l = _file_counts(["  Files:              4 names (3 files: 1 inline + 2 extents)"])
    _keep((t, c) == (3, {"inline": 1, "extents": 2}), "a per-name count labelled as names is read as the total")
    # C4
    lcns = {0x1E, 0xFBFFD, 0xFBFFE}
    _keep(_offsets(_OLD_INTEGRITY, lcns) == {0x1E: [0x1E000], 0xFBFFD: [0xFBFFD000], 0xFBFFE: [0xFBFFE000]},
          "integrity's superblock offsets are not read")
    _keep(_offsets(_OLD_SUMMARY_SUPB, lcns) == {0x1E: [0x101E000], 0xFBFFD: [0xFCFFD000], 0xFBFFE: [0xFCFFE000]},
          "summary's superblock offsets are not read (or the CHKP line leaked in)")
    if _raised(AssertionError, _assert_same_offsets, _OLD_SUMMARY_SUPB, _OLD_INTEGRITY, lcns) is None:
        raise KeptPropertyBroken("1.13.1's two offsets are read as the same")
    _assert_same_offsets(_OLD_SUMMARY_SUPB, _OLD_INTEGRITY.replace("(offset 0x1e000)", "(offset 0x101e000)")
                         .replace("(offset 0xfbffd000)", "(offset 0xfcffd000)")
                         .replace("(offset 0xfbffe000)", "(offset 0xfcffe000)"), lcns)
    # C5
    _keep(len(_claims_carve_ran(_footer(_OLD_FULL_FOOTER))) == 1, "1.13.1's '+ carve' is not read as a claim")
    _keep(len(_claims_view_full_carves(_footer(_OLD_RECOVERY_FOOTER))) == 1,
          "1.13.1's 'Run `deleted --full` to ... carve' is not read as a claim")
    _keep(not _claims_carve_ran(_footer(_OLD_RECOVERY_FOOTER)), "the recovery footer is read as a carve claim")
    _keep(not _claims_carve_ran(_footer(_NEW_FULL_FOOTER)) and not _claims_view_full_carves(
        _footer(_NEW_FULL_FOOTER)), "a fixed --full footer is read as a carve claim")
    _keep(not _claims_view_full_carves(_footer(_NEW_RECOVERY_FOOTER)), "a fixed recovery footer is read as a claim")
    # C7
    for w in ("resident", "non-resident", "RESIDENT", "NON-RESIDENT", "(resident, live-slack", "(non-resident —"):
        _keep(BARE.search(w), "%r is not caught" % w)
    for w in ("resident-all", "IsResident", "is_resident", "residency", "DataResidency", "inline", "extents",
              "embedded", "split", "presidents"):
        _keep(not BARE.search(w), "%r is caught" % w)
    # I7
    _keep(not _lists_subverbs("[forefst v1.13.1] Opening t.raw...\n  + manifest.json"), "no list read as a list")
    _keep(_lists_subverbs("forefst: error: unknown export subverb 'dir' -- choose one of: file, ads, reparse, "
                          "resident-all, snapshots, deleted, recyclebin, metadata"), "a subverb list is not read")
    _keep(not _lists_subverbs("resident-all only"), "'resident-all' is read as 'reparse' or 'file'")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# C3 + N149 -- summary's file counts: per residency category, each file once
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
#
# The driver wraps the real walker and overrides, by row name, the fields named in the spec. The tool's own E87
# constants are named with '@' and resolved inside the driver, so the rows carry exactly the values the walker
# would have produced for such files. The driver reports which rows it edited and their FileRef (from the bytes).

_DRIVER = r'''
import atexit, json, runpy, sys
REPO, TOOL, SPEC = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, REPO)
import forefst as F
spec = json.load(open(SPEC))
_seen = {}
_real = F.walk_directory_tree
def _walk(*a, **k):
    rows = _real(*a, **k)
    for r in rows:
        edit = spec.get(r.get("name"))
        if edit is None or r.get("is_dir"):
            continue
        for fld, val in edit.items():
            r[fld] = getattr(F, val[1:]) if isinstance(val, str) and val.startswith("@") else val
        _seen[r["name"]] = "0x%x:0x%x" % (r.get("home_oid") or 0, r.get("file_id") or 0)
    return rows
F.walk_directory_tree = _walk
atexit.register(lambda: sys.stderr.write("[driver] edited: %s\n" % json.dumps(_seen, sort_keys=True)))
sys.argv = [TOOL] + sys.argv[4:]
if TOOL.endswith("refsanalysis.py"):
    runpy.run_path(TOOL, run_name="__main__")
else:
    try:
        rc = F.main()
        rc = F._escalate_rc(0 if rc is None else rc)          # the tool's own __main__ block
    except SystemExit as e:
        c = 0 if e.code is None else e.code
        rc = F._escalate_rc(c) if isinstance(c, int) else 1
    sys.exit(rc)
'''

# (name, file id, E87 constant). The FileRef is 0x761:<file id>; two names with one file id are hard links.
_C3_ROWS = [("a.txt", 2, "DATA_INLINE"), ("c.txt", 4, "DATA_EXTENTS"),
            ("s.txt", 5, "DATA_SNAPSHOT_SHARED"), ("u.txt", 6, "DATA_SPARSE")]
_N149_ROWS = [("a.txt", 2, "DATA_INLINE"), ("b1.txt", 3, "DATA_EXTENTS"), ("b2.txt", 3, "DATA_EXTENTS"),
              ("c.txt", 4, "DATA_EXTENTS")]
_CTRL_ROWS = [("a.txt", 2, "DATA_INLINE"), ("c.txt", 4, "DATA_EXTENTS")]


class _Scenario:
    def __init__(self, tmp, rows):
        for const, word in _E87.items():
            _fx(getattr(F, const, None) == word, "F.%s is not %r (the E87 vocabulary moved)" % (const, word))
        self.tmp, self.rows = str(tmp), rows
        files = []
        for n, fid, _c in rows:
            files.append((n, fid))
        self.image = _dir_volume(os.path.join(self.tmp, "target.raw"), files, log=True)
        self.spec = {}
        for n, fid, c in rows:
            self.spec[n] = {"data_form": "@" + c}
            links = sorted(m for m, f2, _c2 in rows if f2 == fid)
            if len(links) > 1:
                self.spec[n].update({"hard_link_count": len(links), "hard_link_names": links})
        with open(os.path.join(self.tmp, "walk_driver.py"), "w") as fh:
            fh.write(_DRIVER)
        with open(os.path.join(self.tmp, "walk_spec.json"), "w") as fh:
            json.dump(self.spec, fh)
        self.oracle = _oracle([(fid, _E87[c]) for _n, fid, c in rows])
        self._runs = {}

    def run(self, tool, *args):
        key = (tool,) + args
        if key not in self._runs:
            rc, out, err = _run([os.path.join(self.tmp, "walk_driver.py"), REPO, tool,
                                 os.path.join(self.tmp, "walk_spec.json"), self.image] + list(args) + _SYN,
                                cwd=self.tmp)
            m = re.search(r"^\[driver\] edited: (\{.*\})$", err, re.M)
            _fx(m, "the driver did not report its edits" + _ctx(rc, out, err))
            seen = json.loads(m.group(1))
            want = {n: "0x761:0x%x" % fid for n, fid, _c in self.rows}
            _fx(seen == want, "the walk did not return the scenario's rows with their FileRefs: %r, expected %r"
                % (seen, want))
            self._runs[key] = (rc, out, err)
        return self._runs[key]


@pytest.fixture(scope="module")
def c3_vol(tmp_path_factory):
    return _Scenario(tmp_path_factory.mktemp("c3"), _C3_ROWS)


@pytest.fixture(scope="module")
def n149_vol(tmp_path_factory):
    return _Scenario(tmp_path_factory.mktemp("n149"), _N149_ROWS)


@pytest.fixture(scope="module")
def ctrl_vol(tmp_path_factory):
    return _Scenario(tmp_path_factory.mktemp("c3ctrl"), _CTRL_ROWS)


_TOOLS = [pytest.param(FOREFST, id="forefst"), pytest.param(REFSANALYSIS, id="refsanalysis")]


def _summary_counts(vol, tool):
    rc, out, err = vol.run(tool, "summary")
    _keep(rc == 0, "summary exits %s on a healthy synthetic volume" % rc + _ctx(rc, out, err))
    return _file_counts(_content_section(out))


@pytest.mark.parametrize("tool", _TOOLS)
def test_c3_control_inline_and_extents_only_already_sum_to_the_total(ctrl_vol, tool):
    """Control: no snapshot-shared or unallocated file and no hard link -- 1.13.1's line is already right."""
    total, cats, lines = _summary_counts(ctrl_vol, tool)
    _assert_counts(total, cats, lines, ctrl_vol.oracle, "control")


# C3: green in wave E step E1a (RED until then: summary labels snapshot-shared and unallocated files 'extent-backed' (files - inline, fd:5653, :6554; ra:642); counts must be per residency categor...)
@pytest.mark.parametrize("tool", _TOOLS)
def test_c3_summary_counts_each_residency_category(c3_vol, tool):
    total, cats, lines = _summary_counts(c3_vol, tool)
    _assert_counts(total, cats, lines, c3_vol.oracle, "C3")


# C3: green in wave E step E1a (RED until then: (class site fd:17298, outside the row's lines) the `files` log line labels snapshot-shared and unallocated files 'extent-backed' with the same subt...)
def test_c3_files_log_line_counts_each_residency_category(c3_vol):
    rc, out, err = c3_vol.run(FOREFST, "files")
    _keep(rc == 0, "files exits %s on a healthy synthetic volume" % rc + _ctx(rc, out, err))
    m = re.search(r"^\[forefst\][^\n]*\bdirs?\b[^\n]*$", err, re.M)
    _fx(m, "no '[forefst] N dirs, N files (...)' line on stderr" + _ctx(rc, "", err))
    t = re.search(r"(\d[\d,]*)\s+files\b", m.group(0))
    _fx(t, "no file count on the line: %r" % m.group(0))
    _assert_counts(int(t.group(1).replace(",", "")), _cats(m.group(0)), [m.group(0)], c3_vol.oracle,
                   "C3 (files log line)")


# N149: green in wave E step E1a (RED until then: summary's 'Files' counts one row per hard-link name (fd:5643-5645), while 'Total file size' counts each file once (K184); a file with k names is co...)
@pytest.mark.parametrize("tool", _TOOLS)
def test_n149_summary_counts_each_file_once(n149_vol, tool):
    total, cats, lines = _summary_counts(n149_vol, tool)
    _assert_counts(total, cats, lines, {"files": n149_vol.oracle["files"]}, "N149")


@pytest.mark.parametrize("tool", _TOOLS)
def test_c3_control_summary_json_keeps_its_keys(c3_vol, tool):
    """Control (O5: new keys go beside non_resident_files, which is kept, not renamed): the JSON keys scripts read
    today stay."""
    rc, out, err = c3_vol.run(tool, "summary", "--json")
    try:
        j = jdoc(json.loads(out), F._SUMMARY_KEYS)                    # K21: read by internal names
    except ValueError:
        raise RedFixtureError("summary --json is not JSON" + _ctx(rc, out, err))
    # acceptance 1.14.0: N305 / K17 removed resident_files / non_resident_files (Residency counts every category),
    # so the keys scripts read are Files and Residency (the volume carries its log: `_Scenario`'s DirVol(log=True))
    _keep(rc == 0, "summary --json exits %s" % rc + _ctx(rc, out, err))
    for k in ("files", "residency"):
        _keep(k in j, "summary --json lost the key %r" % k)


# ── image nodes ───────────────────────────────────────────────────────────────────────────────────────────────

_IMAGE_RUNS = {}


def _image_or_skip(name):
    img = _corpus_image(name)
    if img is None:
        pytest.skip("%s not in this tree (a clone ships no images)" % name)
    return img


def _image_run(tmp, tool, name, *args):
    key = (tool, name) + args
    if key not in _IMAGE_RUNS:
        _IMAGE_RUNS[key] = _tool(tool, _image_or_skip(name), *args, cwd=str(tmp))
    return _IMAGE_RUNS[key]


def _image_oracle(tmp, name):
    """Per-row and per-file residency counts from the same tool's `files --csv` on the same image: one row per
    name; ObjectRef (HomeOID:FileID) is the file's identity, as N149 and K184 use it."""
    rc, out, err = _image_run(tmp, FOREFST, name, "files", "-q", "--csv")
    _fx(rc in (0, 2) and out.startswith("ObjectRef,"), "files --csv did not produce a listing" + _ctx(rc, "", err))
    rows = []
    for k, r in enumerate(csv.DictReader(io.StringIO(out))):
        if r["IsDirectory"] == "true":                        # K19 (1.14.0)
            continue
        _fx(r["IsDirectory"] == "false", "IsDirectory %r" % r["IsDirectory"])
        rows.append((r["ObjectRef"] or ("row", k), _norm_cat(r["DataResidency"] or "unknown")))
    _fx(rows, "files --csv listed no file")
    return _oracle(rows)


# N149: green in wave E step E1a (RED until then: summary prints 'Files: 1507' on win11refstestmftecmd, which holds 1,225 files (168 of them under 450 names); expected on 1.13.1: file total 1507, e...)
@pytest.mark.parametrize("tool", _TOOLS)
def test_n149_image_mftecmd_summary_counts_each_file_once(tmp_path, tool):
    name = "win11refstestmftecmd.raw"
    orc = _image_oracle(tmp_path, name)
    _fx(orc["names"]["total"] > orc["files"]["total"], "no hard-linked file on %s: nothing to test" % name)
    rc, out, err = _image_run(tmp_path, tool, name, "summary")
    _fx(rc in (0, 2), "summary exits %s" % rc + _ctx(rc, out, err))
    total, cats, lines = _file_counts(_content_section(out))
    _assert_counts(total, cats, lines, {"files": orc["files"]}, "N149 (%s)" % name)


# C3: green in wave E step E1a (RED until then: summary prints '261 extent-backed' on win11refs2tsnapshots, where 258 names (257 files) are extents and 3 are snapshot-shared)
@pytest.mark.parametrize("tool", _TOOLS)
def test_c3_image_snapshots_summary_counts_each_residency_category(tmp_path, tool):
    name = "win11refs2tsnapshots.raw"
    orc = _image_oracle(tmp_path, name)
    _fx(orc["names"].get("snapshot-shared", 0) + orc["names"].get("unallocated", 0) > 0,
        "no snapshot-shared or unallocated file on %s: nothing to test" % name)
    rc, out, err = _image_run(tmp_path, tool, name, "summary")
    _fx(rc in (0, 2), "summary exits %s" % rc + _ctx(rc, out, err))
    total, cats, lines = _file_counts(_content_section(out))
    _assert_counts(total, cats, lines, orc, "C3 (%s)" % name)     # per-name or per-file; N149 is its own node


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# C4 -- integrity prints partition-relative superblock offsets, summary absolute ones
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_C4_PS = 0x100000
_C4_SUPB = {AB.SYN.supb} | set(AB.SYN.backups)          # 0x1E, 0xFD, 0xFE


@pytest.fixture(scope="module", params=["intact", "backup-zeroed"])
def c4_vol(request, tmp_path_factory):
    """The a_bootstrap volume placed 1 MiB into the file. `backup-zeroed` zeroes the SUPB copy at 0xFD, which
    `integrity` prints on its MISSING/DAMAGED line (fd:15172) instead of the intact one (fd:15177)."""
    d = tmp_path_factory.mktemp("c4")
    raw = str(d / "vol.raw")
    AB._build_synthetic(raw)
    with open(raw, "rb") as fh:
        vol = fh.read()
    os.unlink(raw)
    path = str(d / "target.raw")
    with open(path, "wb") as fh:
        fh.truncate(_C4_PS + len(vol))
        fh.seek(_C4_PS)
        fh.write(vol)
    if request.param == "backup-zeroed":
        with open(path, "r+b") as fh:
            fh.seek(_C4_PS + AB.SYN.backups[0] * CS)
            fh.write(b"\0" * CS)
    with open(path, "rb") as fh:
        for lcn in sorted(_C4_SUPB):
            fh.seek(_C4_PS + lcn * CS)
            sig = fh.read(4)
            _fx(sig == (b"\0" * 4 if request.param == "backup-zeroed" and lcn == AB.SYN.backups[0] else b"SUPB"),
                "SUPB copy at LCN %#x: %r" % (lcn, sig))
    return path


def test_c4_control_a_partition_at_byte_0_already_prints_the_same_offsets(tmp_path):
    """Control: the same volume at byte 0 of the file -- the two bases coincide and the reader finds every copy's
    offset in both outputs, so the RED below differs from this only in the partition start."""
    p = str(tmp_path / "target.raw")
    AB._build_synthetic(p)
    rs, outs, _e = _tool(FOREFST, p, "summary", cli=_SYN)
    ri, outi, erri = _tool(FOREFST, p, "integrity", cli=_SYN)
    _keep(rs == 0 and ri == 0, "summary rc %s, integrity rc %s" % (rs, ri) + _ctx(ri, outi, erri))
    try:
        _assert_same_offsets(outs, outi, _C4_SUPB)
    except AssertionError as e:
        raise KeptPropertyBroken(str(e))


def test_c4_integrity_and_summary_print_the_same_superblock_offsets(c4_vol):
    cli = ["--partition-start", hex(_C4_PS)]
    rs, outs, errs = _tool(FOREFST, c4_vol, "summary", cli=cli)
    ri, outi, erri = _tool(FOREFST, c4_vol, "integrity", cli=cli)
    _fx(rs in (0, 2) and ri in (0, 2), "summary rc %s, integrity rc %s" % (rs, ri) + _ctx(ri, outi, erri))
    _assert_same_offsets(outs, outi, _C4_SUPB)


def test_c4_image_winrefsmini_integrity_and_summary_print_the_same_superblock_offsets(tmp_path):
    img = _image_or_skip("step1/win11refsmini.raw")
    ps = F.find_refs_partition(img)[0]
    _fx(ps, "win11refsmini: the partition starts at byte 0 or was not found; the two bases cannot differ")
    lcns = {AB.IMG.supb} | set(AB.IMG.backups)           # 0x1E, 0x7BFFD, 0x7BFFE
    rs, outs, errs = _tool(FOREFST, img, "summary", cwd=str(tmp_path))
    ri, outi, erri = _tool(FOREFST, img, "integrity", cwd=str(tmp_path))
    _fx(rs in (0, 2) and ri in (0, 2), "summary rc %s, integrity rc %s" % (rs, ri))
    _assert_same_offsets(outs, outi, lcns)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The `deleted` volume (C5, C7, N147): one live file and one remnant whose FileRef is live nowhere
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

class _DelVol:
    def __init__(self, tmp):
        self.tmp = str(tmp)
        self.image = _dir_volume(os.path.join(self.tmp, "target.raw"), [("a.txt", 2)], [("gone.txt", 9)])
        rc, out, err = self.run("files", "-q")
        _fx(rc == 0 and re.search(r"^0x761:0x2,d/a\.txt,", out, re.M) and "gone.txt" not in out,
            "the live tree is not d/a.txt (0x761:0x2) alone" + _ctx(rc, out, err))
        # group 2 (1.14.0, PLAN 10.2 E): an entry's block (`FILE gone.txt  (...)`, its verdict) is printed under -v; the
        # default view lists it on one line (RECOVER, CREATED, NAME, FOUND IN)
        rc, out, err = self.run("deleted", "-v")
        _fx(rc == 0 and re.search(r"^\s+FILE gone\.txt\s", out, re.M),
            "`deleted -v` does not list the remnant gone.txt" + _ctx(rc, out, err))
        self.plain = (rc, out, err)
        rc, out, err = self.run("deleted")
        _fx(rc == 0 and re.search(r"^    metadata only  \S+  +gone\.txt  +d$", out, re.M),
            "`deleted` does not list the remnant gone.txt on one line" + _ctx(rc, out, err))
        self.view = (rc, out, err)

    def run(self, *args, cwd=None):
        return _tool(FOREFST, self.image, *args, cli=_SYN, cwd=cwd or self.tmp)

    def run_in(self, tmp_path, *args):
        """Run in an empty directory of its own and return (rc, out, err, listing of what the run wrote)."""
        d = tmp_path / ("cwd%d" % len(os.listdir(str(tmp_path))))
        d.mkdir()
        rc, out, err = self.run(*args, cwd=str(d))
        return rc, out, err, _listing(str(d)), str(d)


@pytest.fixture(scope="module")
def dvol(tmp_path_factory):
    return _DelVol(tmp_path_factory.mktemp("deleted"))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# C5 -- the footer's '+ carve'; `deleted --carve` accepted and doing nothing
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# C5: green in wave D step D1 (RED until then: the `deleted --full` footer says 'This was --full (complete): live + whole-volume orphan-page slack + carve' (fd:14426); a view carves nothing, onl...)
def test_c5_full_view_footer_lists_only_what_ran(dvol):
    rc, out, err = dvol.run("deleted", "--full")
    _keep(rc == 0, "deleted --full exits %s on a healthy volume" % rc + _ctx(rc, out, err))
    claims = _claims_carve_ran(_footer(out))
    assert not claims, "the footer of a view that carved nothing says it carved: %r" % claims


# C5: green in wave D step D1 (RED until then: the recovery-mode footer says 'Run `deleted --full` to ALSO scan orphan pages ... and carve extent-backed content' (fd:14422-14423); `deleted --ful...)
def test_c5_recovery_footer_does_not_say_the_full_view_carves(dvol):
    rc, out, err = dvol.plain
    claims = _claims_view_full_carves(_footer(out))
    assert not claims, "the footer says `deleted --full` carves: %r" % claims


# C5: green in wave D step D1 (RED until then: `deleted --carve` without an export directory is accepted, exits 0 and prints exactly what `deleted` prints (O4: reject with exit 1 and a usage mes...)
def test_c5_carve_without_an_export_directory_is_not_silently_accepted(dvol, tmp_path):
    rc0, out0, err0 = dvol.plain
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, "deleted", "--carve")
    _keep(not wrote, "a view wrote files: %r" % wrote)
    if rc == 1:                                          # O4 recommendation: refused as a usage error
        assert re.search(r"--carve", out + err), "exit 1, but the message does not name --carve" + _ctx(rc, out, err)
        return
    new = [ln for ln in (out + "\n" + err).splitlines()
           if ln not in set((out0 + "\n" + err0).splitlines()) and re.search(r"carv", ln, re.I)]
    assert new, ("`deleted --carve` without an export directory: rc %s and no line about --carve that `deleted` "
                 "does not print -- the option is accepted and does nothing" % rc)


def test_c5_control_full_view_without_an_export_directory_still_runs(dvol):
    """Control: O4 concerns an explicit --carve; `deleted --full` is a view and keeps running (exit 0)."""
    rc, out, err = dvol.run("deleted", "--full")
    _keep(rc == 0 and re.search(r"Mode: full", out), "deleted --full does not run as a view" + _ctx(rc, out, err))


def test_c5_control_export_deleted_with_carve_is_accepted(dvol, tmp_path):
    """Control: --carve with an export directory is the documented form and keeps working."""
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, "export", "deleted", "OUT", "--carve")
    _keep(rc == 0 and "OUT/deleted_files.csv" in wrote, "export deleted OUT --carve" + _ctx(rc, out, err))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# C7 -- the retired bare word "resident" in `deleted`
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

# C7: green in wave D step D1 (RED until then: `deleted` prints the retired bare word: row headers '(non-resident, live-slack ...)', the _RECOVER_LABEL verdicts and the Restorability lines ('a R...)
@pytest.mark.parametrize("mode", [(), ("--full",)], ids=["recovery", "full"])
def test_c7_deleted_prints_no_bare_resident(dvol, mode):
    # group 2: the row header and the verdict are printed under -v; the default view is checked too
    rc, out, err = dvol.run("deleted", *mode, "-v") if mode else dvol.plain
    _keep(rc == 0, "deleted exits %s" % rc + _ctx(rc, out, err))
    _fx(re.search(r"^\s+FILE gone\.txt\s", out, re.M), "the remnant is not listed, so no row header is printed")
    rc2, out2, err2 = dvol.run("deleted", *mode) if mode else dvol.view
    _keep(rc2 == 0, "deleted exits %s" % rc2 + _ctx(rc2, out2, err2))
    out, err = out + "\n" + out2, err + "\n" + err2
    bad = _bare_lines(out + "\n" + err)
    assert not bad, "%d line(s) carry a bare 'resident' word:\n  %s" % (len(bad), "\n  ".join(bad[:8]))


# C7: green in wave D step D1 (RED until then: `help deleted` (CMD_HELP, fd:16408-16441) uses the bare words RESIDENT / NON-RESIDENT / non-resident)
def test_c7_help_deleted_prints_no_bare_resident():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        F._render_cmd_help("deleted")
    text = buf.getvalue()
    _fx("deleted" in text and "--full" in text, "help deleted rendered nothing:\n" + text[:500])
    bad = _bare_lines(text)
    assert not bad, "%d help line(s) carry a bare 'resident' word:\n  %s" % (len(bad), "\n  ".join(bad))


def _module_constant_strings(tree, names):
    out = []
    for n in tree.body:
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            tnames = set()
            for t in targets:
                tnames |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
            if tnames & names and n.value is not None:
                out += [(x.lineno, x.value) for x in ast.walk(n.value)
                        if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    return out


# C7: green in wave D step D1 (RED until then: an AST scan of cmd_deleted's print strings, the strings it assigns for printing and the label constants it prints (_RECOVER_LABEL) finds 9 bare use...)
def test_c7_cmd_deleted_print_strings_have_no_bare_resident():
    with open(os.path.join(REPO, "forefst.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    top = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    # since wave E step E1a the body is `_cmd_deleted` (N276: `cmd_deleted` sends the report to stderr around it)
    fn = top.get("_cmd_deleted") or top.get("cmd_deleted")
    _fx(fn is not None, "no cmd_deleted in forefst.py")
    strings = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            for a in list(node.args) + [k.value for k in node.keywords]:
                strings += [(x.lineno, x.value) for x in ast.walk(a)
                            if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        elif isinstance(node, ast.Assign):                # e.g. _hdr_res = ("resident" if ... else "non-resident")
            strings += [(x.lineno, x.value) for x in ast.walk(node.value)
                        if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    # module-level constants that cmd_deleted, or a function it calls directly, reads (the verdict labels)
    called = {x.id for x in ast.walk(fn) if isinstance(x, ast.Name)}
    names = set(called)
    for c in called & set(top):
        names |= {x.id for x in ast.walk(top[c]) if isinstance(x, ast.Name)}
    strings += _module_constant_strings(tree, names - set(top))
    _fx(len(strings) > 100, "the scan found only %d strings: it is not reading cmd_deleted" % len(strings))
    bad = sorted({(ln, s) for ln, s in strings if BARE.search(s)})
    assert not bad, "%d print string(s) with a bare 'resident' word:\n  %s" % (
        len(bad), "\n  ".join("fd:%d %r" % (ln, s[:90]) for ln, s in bad))


# C7: green in wave D step D1 (RED until then: (class site) `export deleted` writes the same verdict labels into deleted_files.csv/.json and the recovery log, which also says 'Carved non-residen...)
def test_c7_export_deleted_index_and_log_carry_no_bare_resident(dvol, tmp_path):
    rc, out, err, wrote, d = dvol.run_in(tmp_path, "export", "deleted", "OUT")
    _keep(rc == 0, "export deleted OUT exits %s" % rc + _ctx(rc, out, err))
    for f in ("OUT/deleted_files.csv", "OUT/deleted_files.json", "OUT/recovery_log.txt"):
        _fx(f in wrote, "export deleted did not write %s: %r" % (f, wrote))
    bad = []
    for f in ("OUT/deleted_files.csv", "OUT/deleted_files.json", "OUT/recovery_log.txt"):
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            bad += ["%s: %s" % (f, ln.strip()[:120]) for ln in _bare_lines(fh.read())]
    assert not bad, "%d line(s) carry a bare 'resident' word:\n  %s" % (len(bad), "\n  ".join(bad[:8]))


# C7: green in wave D step D1 (RED until then: `deleted` on win11refs8gtestmove_aftermove prints '(resident, live-slack ...)' and 'a RESIDENT deleted file' (the row's measurement))
def test_c7_image_aftermove_deleted_prints_no_bare_resident(tmp_path):
    rc, out, err = _image_run(tmp_path, FOREFST, "win11refs8gtestmove_aftermove.raw", "deleted")
    _fx(rc in (0, 2) and "DELETED" in out, "deleted listed nothing" + _ctx(rc, out, err))
    bad = _bare_lines(out + "\n" + err)
    assert not bad, "%d line(s) carry a bare 'resident' word:\n  %s" % (len(bad), "\n  ".join(bad[:8]))


# C7: green in wave D step D1 (RED until then: on the 101's running case `deleted --max-scan 8000` (the sample command) prints 1,439 lines with a bare 'resident' word (1,322 'non-resident'; publ...)
def test_c7_image_mftecmd_deleted_recovery_prints_no_bare_resident(tmp_path):
    rc, out, err = _image_run(tmp_path, FOREFST, "win11refstestmftecmd.raw", "deleted", "--max-scan", "8000")
    _fx(rc in (0, 2) and "DELETED" in out, "deleted listed nothing" + _ctx(rc, out, err))
    bad = _bare_lines(out + "\n" + err)
    assert not bad, "%d line(s) carry a bare 'resident' word, e.g.:\n  %s" % (len(bad), "\n  ".join(bad[:8]))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# I7 -- an unknown `export` subverb silently writes a metadata bundle
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def plain_vol(tmp_path_factory):
    d = tmp_path_factory.mktemp("i7")
    p = str(d / "target.raw")
    AB._build_synthetic(p)
    v = AB.Vol(AB.SYN, p)
    v.pin()
    return p


def _run_in(image, tmp_path, *args):
    d = tmp_path / ("cwd%d" % len(os.listdir(str(tmp_path))))
    d.mkdir()
    rc, out, err = _tool(FOREFST, image, *args, cli=_SYN, cwd=str(d))
    return rc, out, err, _listing(str(d)), str(d)


# I7: green in wave E step E1a (RED until then: an unknown export subverb fell through to the metadata bundle: `export dir
# /test OUT` wrote a bundle into ./dir, ignored /test and OUT, and exited 0)
@pytest.mark.parametrize("args", [("dir", "/test", "OUT"), ("metdata", "OUT")], ids=["dir-test-OUT", "typo-metdata"])
def test_i7_unknown_export_subverb_is_refused_with_the_subverb_list(plain_vol, tmp_path, args):
    rc, out, err, wrote, _d = _run_in(plain_vol, tmp_path, "export", *args)
    assert rc == 1, "`export %s` exits %s and wrote %d entr(ies): %r" % (" ".join(args), rc, len(wrote), wrote[:6])
    assert not wrote, "`export %s` was refused but wrote %r" % (" ".join(args), wrote)
    assert _lists_subverbs(out + "\n" + err), "the refusal does not list the subverbs %s:%s" % (
        ", ".join(_SUBVERBS), _ctx(rc, out, err))


@pytest.mark.parametrize("args, where", [(("-o", "X"), "X"), (("metadata", "X"), "X")],
                         ids=["bare-o", "metadata"])
def test_i7_control_documented_forms_keep_writing_the_bundle(plain_vol, tmp_path, args, where):
    """Control: the documented bare `export -o DIR` (docs/tools/forefst.md:688, fd:16527) and `export metadata DIR`
    keep writing the bundle."""
    rc, out, err, wrote, _d = _run_in(plain_vol, tmp_path, "export", *args)
    _keep(rc == 0 and "%s/manifest.json" % where in wrote and "%s/sha256sums.txt" % where in wrote,
          "`export %s` did not write the bundle into %s: %r" % (" ".join(args), where, wrote) + _ctx(rc, out, err))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N147 -- `export deleted FLAG VALUE DIR` takes VALUE as the directory; `deleted` ignores stray positionals
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _flag_output_ok(path, flag):
    """What FLAG's VALUE must hold: the recovery log, or the deleted-entries listing in that format."""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if flag == "--log":
        return "recovery log" in text
    if flag == "--csv":
        return text.startswith("FileName,")
    if flag == "--json":
        return isinstance(_json_or_error(text)[0], list)
    first = text.splitlines()[0] if text else ""
    return "FileName" in (_json_or_error(first)[0] or {})


def _json_or_error(text):
    """(value, None), or (None, the ValueError) when TEXT is not JSON. "Not JSON" is this predicate's answer, not a
    skipped measurement, and the reason stays available to a caller that wants it (N204)."""
    try:
        return json.loads(text), None
    except ValueError as e:
        return None, e


_N147_FLAGS = [pytest.param(f, id=f.lstrip("-")) for f in ("--log", "--csv", "--json", "--jsonl")]


def _check_export_split(d, wrote, flag, what):
    assert os.path.isdir(os.path.join(d, "DIR")) and "DIR/deleted_files.csv" in wrote, (
        "%s: the export did not go into DIR (%s): %r" % (what, "DIR is a file" if os.path.isfile(
            os.path.join(d, "DIR")) else "no DIR", wrote))
    assert _flag_output_ok(os.path.join(d, "VAL"), flag), (
        "%s: %s VAL did not write %s to VAL (%s): %r" % (what, flag, "the recovery log" if flag == "--log" else
                                                          "the listing", "VAL is a directory" if os.path.isdir(
                                                              os.path.join(d, "VAL")) else "no VAL", wrote))


# N147: green in wave E step E1a (RED until then: `export deleted FLAG VAL DIR` exported into VAL and wrote FLAG's output to
# DIR: the dispatcher's valued-flag skip list lacked --log/--csv/--json/--jsonl)
@pytest.mark.parametrize("flag", _N147_FLAGS)
def test_n147_export_deleted_valued_flag_before_the_directory_keeps_its_value(dvol, tmp_path, flag):
    rc, out, err, wrote, d = dvol.run_in(tmp_path, "export", "deleted", flag, "VAL", "DIR")
    _keep(rc == 0, "export deleted %s VAL DIR exits %s" % (flag, rc) + _ctx(rc, out, err))
    _check_export_split(d, wrote, flag, "export deleted %s VAL DIR" % flag)


@pytest.mark.parametrize("flag", _N147_FLAGS)
def test_n147_control_flag_after_the_directory(dvol, tmp_path, flag):
    """Control: the same flag after the directory already parses as intended."""
    rc, out, err, wrote, d = dvol.run_in(tmp_path, "export", "deleted", "DIR", flag, "VAL")
    _keep(rc == 0, "export deleted DIR %s VAL exits %s" % (flag, rc) + _ctx(rc, out, err))
    try:
        _check_export_split(d, wrote, flag, "export deleted DIR %s VAL" % flag)
    except AssertionError as e:
        raise KeptPropertyBroken(str(e))


# N147: green in wave E step E1a (RED until then: `deleted report` ignored the stray positional, ran the full listing and
# exited 0)
def test_n147_deleted_refuses_a_stray_positional(dvol, tmp_path):
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, "deleted", "report")
    _keep(not wrote, "a view wrote files: %r" % wrote)
    assert rc == 1, "`deleted report` exits %s (the listing ran: %s)" % (rc, "FILE gone.txt" in out)
    assert re.search(r"\breport\b", out + err), "the refusal does not name 'report'" + _ctx(rc, out, err)


def test_n147_control_a_valued_flags_value_is_not_a_stray_positional(dvol, tmp_path):
    """Control: `deleted --search report` (the value of a valued flag) runs, exit 0."""
    rc, out, err, wrote, _d = dvol.run_in(tmp_path, "deleted", "--search", "report")
    _keep(rc == 0 and not wrote, "deleted --search report" + _ctx(rc, out, err))
