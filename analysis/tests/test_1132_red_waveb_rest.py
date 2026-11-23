"""1.13.2 (ships as 1.14.0) RED cases, wave B stage 2b: groups 5 (checkpoint size) and 7 (passthrough), wave A's
journal residue, and N259's bundle-index half. The harness items (N386, N385, N399 (b), E-5) are in
test_1132_red_waveb_harness.py.

Read first: `analysis/reports/v1.13.2/fixes/WAVEB_PREP.md` (items; the lead's settlements LB1-LB37), `fixes/WAVEB_CENSUS.md`
(stage 1), `fixes/WAVES_COMMON_CONTEXT.md` (decisions 32-38), `fixes/CONSISTENCY_CHOICES.md`, PLAN_1.13.2 decisions 19-38
and the running-log rows named per section. Report, with the failure line of every node observed on the current tree:
`analysis/reports/v1.13.2/red/RED_waveB_rest.md`; amended 2026-10-15 after the RED critic (`red/RED_waveB_critic.md`)
and LB18-LB29: `red/RED_waveB_amend.md` (LB25: the F11 label's place; LB22: the bundle column `BlockIndex`), and again
after LB30-LB37 (LB30: the byte keys `CheckpointSHA256Bytes` / `SHA256Bytes`; LB32: `BlockIndex` values `0x%x`).

The confirmed REDs stay as they are: F11 / N190 / E118 (`test_1132_red_mlog_chkp.py`), A12 / A13 / N134
(`test_1132_red_a_verdicts.py`; A12's two code nodes are strict XPASS since A11: the fixer removes their marks). This
file adds what they do not pin:

  F11 (LB2, LB8, LB9)  every checkpoint hash row says what it hashes ("1 cluster, 4 KiB" / "1 cluster, 64 KiB"; LB25:
                       forefst on the CHKP line, the hash alone on its own line; refsanalysis after the hash); the
                       JSON carries CheckpointSHA256Bytes and, per copy, SHA256Bytes (LB30; 4096 / 65536);
                       `fastsummary` text, `summary --json` and refsanalysis `chkp -v/-vv/--raw` hash the one
                       cluster; the checkpoint read
                       is one cluster; 64 KiB controls (the value is already the cluster's there).
  N261                 the export manifest labels each checkpoint copy with checkpoint_select's role (in use / newest /
                       superseded / tied), on a stale view, a tie, N361's shape and an undamaged volume.
  N369 (widened)       on N361's shape (a newer copy whose root list cannot be read): the PRIMARY label, the JSON role
                       and the two "fallback" booleans, refsanalysis `supb -v` latest_checkpoint, `supb --verify`
                       latest_identified, `deleted`'s header and `containers`' note name the newest copy too; a root
                       reference past the one-cluster record is not worded "runs past the page" (K-9 b); control: the
                       root check reads inside one cluster (K-9 a, the 0x680 margin).
  N252                 closed on the current tree (passing checks, as LB7 asks for N254).
  A13                  the critic's missing control: the "payload is identical" note IS printed over equal payloads.
  N171                 the passthrough runs forefst with forefst's recursion limit and its BrokenPipe handling.
  N265 / N409          a contradicted boot-sector version is registered by forefst `integrity` and refsanalysis
                       `summary` and `boot --verify` too (decision 29's command set, exit 2); `summary`/`fastsummary`
                       text carry the same sentence as their JSON (with N134's major); controls.
  N396 (LB5)           timestomp's "cannot be corroborated before" clause names the earliest surviving record's time.
  N400                 timestomp --json journal_last_usn is the current sequence's last USN; `timeline`/`timestomp`
                       parse $J with the allocation as `usn` does (the USN-offset finding, exit 2).
  N401                 an all-zero $J beside files carrying an earlier journal id: decision 31's statement and S2's
                       naming, not "they point into this journal".
  N403                 journal findings are not worded as skipped work.
  N404                 a $J that is entirely an image hole: the empty-journal note says so (the hole clause).
  N405                 the G3b timeline-note node leaves forefst's run registers as it found them.
  N157                 no statement says ReFS leaves Source info (0x3C) at 0 / does not populate it.
  N255                 a nameless USN record is never filed under its home directory's path in `timeline`.
  N254                 closed on the current tree (LB7's check, passing).
  N259 (LB17, LB22)    `mlog_log_index.csv`'s `block_lcn` is renamed `BlockIndex` (values `0x%x`, the form LB32 sets
                       for the JSON key too); an old bundle still reads.

Conventions (those of test_1132_red_a_bootstrap.py / test_1132_red_mlog_chkp.py, whose helpers are imported)
-----------------------------------------------------------------------------------------------------------------
* Every RED is ``xfail(strict=True, raises=AssertionError)`` with ``reason="RED 1.13.2 <item>: ..."`` and fails on the
  current tree at a plain ``assert``. Anything else is ``RedFixtureError`` (the fixture is not what the case needs) or
  ``KeptPropertyBroken`` (a property the tool has today and the fix must keep) -- not AssertionErrors.
* Expected values come from this module's own reads (or the helpers' own reads it imports): checkpoint clusters and
  their hashes (``MC.Chkp``), boot-sector versions, $J records (``G3._carve`` and the premises of test_1132_red_g3.py),
  the synthetic volumes and journals this module builds. The tool's own output is used as an oracle only where a node
  says so and a control pins it (the version sentences of forefst `summary --json`; `usn --csv` for N255).
* Where a wording is not settled the node asserts the property and says so; decided values (LB2's "1 cluster, 4 KiB",
  LB8's key names, the role words of decision 25.4, exit codes) are asserted as such.
* Images are addressed by their step path. ``vol`` is test_1132_red_a_bootstrap's fixture ([synthetic] / [image]).

``pytest -k "not image"`` runs the unit and synthetic nodes only.
"""
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

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402  (exceptions, vol, plants, tie)
import test_1132_red_mlog_chkp as MC                     # noqa: E402  (corpus, Chkp, summary readers, _red)
from conftest import jget, jint, jdoc# noqa: E402  (K21 readers)
import test_1132_red_a_verdicts as AV                    # noqa: E402  (_flip_newest, _IDENTICAL_NOTE)
import test_1132_red_g2c as G2C                          # noqa: E402  (_run_split, plant_no_root_list)
import test_1132_red_g2c2 as G2C2                        # noqa: E402  (N361's plant, checked)
import test_1132_red_b2_journal as BJ                    # noqa: E402  (the journal harness)
import test_1132_red_g3 as G3                            # noqa: E402  (journal premises, own $J carve, matchers)
from test_1132_red_a_verdicts import _rc_escalate        # noqa: E402

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
FOREFST, REFSANALYSIS, CS = AB.FOREFST, AB.REFSANALYSIS, AB.CS
CLOCK_NEW, CLOCK_OLD = AB.CLOCK_NEW, AB.CLOCK_OLD
_red = MC._red
vol = AB.vol        # the pytest fixture ([synthetic] / [image]), re-exported so pytest finds it in this module


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Runners
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_RUNS = {}


def _crun(tool, rel, *args):
    """(rc, stdout, stderr) of a read-only run on a corpus image addressed by its step path, once per process."""
    img = MC.corpus(rel)
    key = (tool, img, args)
    if key not in _RUNS:
        _RUNS[key] = G2C._run_split(tool, img, *args, cwd=REPO)
    return _RUNS[key]


def _vrun(v, tool, *args):
    """(rc, stdout, stderr) on a `vol` volume (a fresh run: the volume may have been planted)."""
    return G2C._run_split(tool, v.path, *args, cwd=os.path.dirname(v.path), cli=v.geo.cli)


def _ctx(rc, out, err):
    return "\n| rc=%s\n--- stdout (tail) ---\n%s\n--- stderr (tail) ---\n%s" % (rc, out[-3000:], err[-2000:])


def _json(out, what):
    return jdoc(MC._json_of(out, what), F._SUMMARY_KEYS)                # K21: read by internal names


def _strings(o):
    """Every string value of a JSON document."""
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for x in o.values():
            yield from _strings(x)
    elif isinstance(o, list):
        for x in o:
            yield from _strings(x)


def _flat(text):
    """Text with each line's `[forefst]`-style prefix dropped and all whitespace runs collapsed: a sentence the tool
    wraps over several lines still reads as one string."""
    ls = [re.sub(r"^\s*\[(?:forefst|refsanalysis)[^\]]*\]\s*", "", ln) for ln in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(ls))


def _ws(s):
    return re.sub(r"\s+", " ", s).strip()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# F11 (LB2, LB8, LB9) -- the checkpoint SHA-256 is the ONE cluster's, every row says so, the read is one cluster
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Decided: LB2 (the value replaces the page hash in place; "Text names what is hashed in the decided form ('1 cluster,
# 4 KiB'); machine values 4096"), LB8 (chkp_sha256 and each copy's sha256 keep their names in wave B), LB30 (the NEW
# keys are words with upper-case acronyms: CheckpointSHA256Bytes and, per copy, SHA256Bytes -- they replace LB8's
# ChkpSha256Bytes / Sha256Bytes, so those spellings are refused), LB9 (the label and the machine value print on EVERY
# volume, 64K
# included: "1 cluster, 64 KiB"), LB25 (the label's place: forefst puts "(1 cluster, 4 KiB)" on the CHKP line and keeps
# the hash ALONE on its own line; refsanalysis puts it AFTER the hash -- so `test_1132_red_b_items._HASH_TXT` and the
# `SHA-256:?\s+<hash>` reader of test_1132_red_mlog_chkp.py keep working unedited). The existing F11 nodes pin the
# value of `summary` text, `fastsummary --json` and bare refsanalysis `chkp`; these add the label, the byte counts,
# the other forms and the read itself.

K64 = "step2/win11refs5g64k.raw"
_HASH_ALONE = re.compile(r"^\s+[0-9a-f]{64}\s*$")       # test_1132_red_b_items._HASH_TXT (LB25 keeps it working)


def _one_cluster(cs):
    return re.compile(r"\b1 cluster, %d KiB\b" % (cs // 1024))


def _chkp_rows(text):
    """[(lcn, CHKP line, hash line, hash)] of the `CHKP primary|secondary LCN 0x..` lines (the hash on its own line)."""
    ls = text.splitlines()
    out = []
    for i, ln in enumerate(ls):
        m = re.search(r"CHKP (?:primary|secondary)\s+LCN (0x[0-9a-f]+)", ln)
        if m:
            nxt = next((l2 for l2 in ls[i + 1:i + 3] if re.search(r"\b[0-9a-f]{64}\b", l2)), "")
            h = re.search(r"\b[0-9a-f]{64}\b", nxt)
            out.append((int(m.group(1), 16), ln, nxt, h.group(0) if h else None))
    return out


def _unlabelled(rows, cs):
    """LB25 (forefst): the CHKP rows whose CHKP line does not name what the hash covers, or whose hash line is not the
    hash alone."""
    rx = _one_cluster(cs)
    return [r[1].strip() + " / " + r[2].strip() for r in rows if not (rx.search(r[1]) and _HASH_ALONE.match(r[2]))]


# LB30: the names of the two new byte keys; any other spelling of "the bytes the SHA-256 covers" is a second key for
# one fact (decision 35) -- LB8's ChkpSha256Bytes / Sha256Bytes, or a snake_case chkp_sha256_bytes.
TOP_BYTES, COPY_BYTES = "CheckpointSHA256Bytes", "SHA256Bytes"
_BYTES_KEY = re.compile(r"(?i)sha_?256_?bytes$")


def _byte_key_problems(j, cps, want):
    """LB30: [problem] of a `summary --json` / `fastsummary --json` document whose checkpoint byte keys are not
    `CheckpointSHA256Bytes` = want at the top and `SHA256Bytes` = want in each copy, alone."""
    bad = []
    if j.get(TOP_BYTES) != want:
        bad.append("%s = %r; decided %d" % (TOP_BYTES, j.get(TOP_BYTES), want))
    got = [c.get(COPY_BYTES) for c in cps]
    if got != [want] * len(cps):
        bad.append("per-copy %s = %r; decided %r" % (COPY_BYTES, got, [want] * len(cps)))
    other = sorted({k for k in j if _BYTES_KEY.search(k) and k != TOP_BYTES}
                   | {k for c in cps for k in c if _BYTES_KEY.search(k) and k != COPY_BYTES})
    if other:
        bad.append("other spellings of the byte keys: %r" % other)
    return bad


def _ra_hash_lines(text):
    """refsanalysis `chkp`'s checkpoint hash lines (`SHA-256: <h>`, `CHKP SHA-256  <h>`) with the line before each."""
    ls = text.splitlines()
    return [(ls[i - 1] if i else "", ln, re.search(r"\b[0-9a-f]{64}\b", ln).group(0)) for i, ln in enumerate(ls)
            if re.search(r"SHA-256", ln) and re.search(r"\b[0-9a-f]{64}\b", ln)]


def _ra_unlabelled(hl, cs):
    """LB25 (refsanalysis): the hash lines that do not carry the label AFTER the hash (`SHA-256:? <hash> ... 1 cluster,
    N KiB`), the form the `SHA-256:?\\s+<hash>` reader of test_1132_red_mlog_chkp.py keeps reading."""
    return [l.strip() for _p, l, h in hl
            if not re.search(r"SHA-256:?\s+%s\b.*\b1 cluster, %d KiB\b" % (h, cs // 1024), l)]


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_f11_lb2_text_names_what_each_checkpoint_hash_covers(vol, cmd):
    rc, out, err = _vrun(vol, FOREFST, cmd)
    rows = _chkp_rows(out)
    _fx(len(rows) == 2 and all(r[3] for r in rows), "%s printed CHKP rows %r" % (cmd, rows) + _ctx(rc, out, err))
    bad = _unlabelled(rows, CS)
    assert not bad, "CHKP rows whose CHKP line does not name '1 cluster, 4 KiB' or whose hash line is not the hash " \
                    "alone (LB25): %r" % bad + _ctx(rc, out, err)


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_fastsummary_text_chkp_rows_hash_one_cluster(vol):
    ck = MC.Chkp(vol.path, ps=vol.geo.ps, cs=CS)
    rc, out, err = _vrun(vol, FOREFST, "fastsummary")
    MC._assert_summary_rows(ck, out, "fastsummary [%s]" % vol.geo.kind)


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_summary_json_chkp_hashes_are_one_cluster(vol):
    ck = MC.Chkp(vol.path, ps=vol.geo.ps, cs=CS)
    rc, out, err = _vrun(vol, FOREFST, "summary", "--json")
    j = _json(out, "summary --json")
    top = jget(j, "chkp_sha256", F._SUMMARY_KEYS)                  # acceptance 1.14.0 (K21)
    pairs = MC._json_chkp_hashes(j, set(ck.lcns))
    spans = set(ck.one.values()) | set(ck.page.values())
    _fx(top and len(pairs) == 2 and top in spans and all(h in spans for _l, h in pairs),
        "summary --json: the checkpoint hashes cover no span of a copy: %r %r" % (top, pairs))
    assert top in ck.one.values(), "chkp_sha256 %s.. is not a one-cluster hash" % top[:16]
    wrong = [(hex(l), h[:16]) for l, h in pairs if h != ck.one[l]]
    assert not wrong, "bootstrap_backups.checkpoints[].sha256 not over one cluster: %r" % wrong


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_f11_lb8_json_states_the_bytes_each_checkpoint_hash_covers(vol, cmd):
    rc, out, err = _vrun(vol, FOREFST, cmd, "--json")
    j = _json(out, cmd + " --json")
    cps = jget(jget(j, "bootstrap_backups") or {}, "checkpoints") or []
    _fx(len(cps) == 2, "%s --json: %d checkpoint copies" % (cmd, len(cps)))
    # acceptance 1.14.0 (K21): the hashes take the output names wave E gives every key (CHKPSHA256, SHA256)
    assert F.out_key("chkp_sha256", F._SUMMARY_KEYS) in j and all(F.out_key("sha256") in c for c in cps), sorted(j)
    bad = _byte_key_problems(j, cps, CS)
    assert not bad, "%s --json, the checkpoint byte keys (LB8, LB30): %s" % (cmd, "; ".join(bad))


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("args", [("chkp",), ("chkp", "-v"), ("chkp", "-vv"), ("chkp", "--raw")],
                         ids=["chkp", "chkp-v", "chkp-vv", "chkp-raw"])
def test_f11_refsanalysis_chkp_hash_is_one_cluster_and_says_so(vol, args):
    ck = MC.Chkp(vol.path, ps=vol.geo.ps, cs=CS)
    rc, out, err = _vrun(vol, REFSANALYSIS, *args)
    hl = _ra_hash_lines(out)
    spans = set(ck.one.values()) | set(ck.page.values())
    _fx(hl and all(h in spans for _p, _l, h in hl), "refsanalysis %s: hash lines %r" % (" ".join(args), hl)
        + _ctx(rc, out, err))
    assert all(h in ck.one.values() for _p, _l, h in hl), "refsanalysis %s: hash(es) not over one cluster: %r" % (
        " ".join(args), [h[:16] for _p, _l, h in hl])
    bad = _ra_unlabelled(hl, CS)
    assert not bad, "refsanalysis %s: hash lines without '1 cluster, 4 KiB' after the hash (LB25): %r" % (
        " ".join(args), bad)


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_lb2_the_checkpoint_read_is_one_cluster(vol):
    with open(vol.path, "rb") as fh:
        sel = F.checkpoint_select(fh, vol.geo.ps, CS, F.parse_supb(fh, vol.geo.ps, CS), require_roots=True)
    cps = sel["copies"]
    _fx(len(cps) == 2 and all(c["sig_ok"] and "raw" in c for c in cps), "checkpoint_select copies: %r" % (
        [(c.get("lcn"), c.get("sig_ok")) for c in cps],))
    _keep(sel["in_use"] is not None and sel["in_use"]["lcn"] == vol.geo.lo, "the copy in use is the newest (vclock 64)")
    sizes = {hex(c["lcn"]): len(c["raw"]) for c in cps}
    assert all(n == CS for n in sizes.values()), "bytes read per checkpoint copy %r; one cluster is %d" % (sizes, CS)
    assert all(c["raw"] == vol.block(c["lcn"]) for c in cps), "the bytes read are not the copy's own cluster"


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_f11_lb9_64k_rows_name_what_they_hash_on_image_win11refs5g64k(cmd):
    ck = MC.Chkp(MC.corpus(K64))
    _fx(ck.cs == 0x10000 and len(ck.lcns) == 2, "%s: not a 64 KiB-cluster volume with two copies" % K64)
    rc, out, err = _crun(FOREFST, K64, cmd)
    rows = _chkp_rows(out)
    _fx(len(rows) == 2, "%s %s: CHKP rows %r" % (K64, cmd, rows) + _ctx(rc, out, err))
    _keep(all(r[3] == ck.one[r[0]] for r in rows), "64K: the rows already hash the one cluster (E118)")
    bad = _unlabelled(rows, ck.cs)
    assert not bad, "64K CHKP rows that do not name '1 cluster, 64 KiB' on the CHKP line, the hash alone below " \
                    "(LB25): %r" % bad
    rc, out, err = _crun(FOREFST, K64, cmd, "--json")
    j = _json(out, cmd + " --json")
    cps = jget(jget(j, "bootstrap_backups") or {}, "checkpoints") or []
    _fx(len(cps) == 2, "%s %s --json: %d checkpoint copies" % (K64, cmd, len(cps)))
    bad = _byte_key_problems(j, cps, 65536)
    assert not bad, "64K %s --json, the checkpoint byte keys (LB8, LB9, LB30): %s" % (cmd, "; ".join(bad))


# RED 1.13.2 F11: green with wave B part 2's fix (the strict xfail mark removed)
def test_f11_lb9_64k_refsanalysis_chkp_names_what_it_hashes_on_image_win11refs5g64k():
    ck = MC.Chkp(MC.corpus(K64))
    rc, out, err = _crun(REFSANALYSIS, K64, "chkp", "-v")
    hl = _ra_hash_lines(out)
    _fx(hl, "refsanalysis chkp -v printed no hash" + _ctx(rc, out, err))
    _keep(all(h in ck.one.values() for _p, _l, h in hl), "64K: the hash is already the one cluster's")
    bad = _ra_unlabelled(hl, ck.cs)
    assert not bad, "hash lines without '1 cluster, 64 KiB' after the hash (LB25): %r" % bad


def test_f11_lb25_control_the_label_readers_accept_the_decided_places():
    """Not a RED. The LB25 readers: the label on forefst's CHKP line with the hash alone below it (the line
    test_1132_red_b_items._HASH_TXT reads), and after the hash on refsanalysis's line (what the `SHA-256:?\\s+<hash>`
    reader reads); the label in any other place is refused."""
    h = "ab" * 32
    good = [(0x48, "  CHKP primary   LCN 0x48 (1 cluster, 4 KiB)  checksum OK, vclock=64, in use", "    " + h, h)]
    assert not _unlabelled(good, 0x1000)
    assert _unlabelled([(0x48, "  CHKP primary   LCN 0x48  checksum OK", "    %s  (1 cluster, 4 KiB)" % h, h)], 0x1000)
    assert _unlabelled([(0x48, "  CHKP primary   LCN 0x48 (1 cluster, 4 KiB)", "    %s  (1 cluster, 4 KiB)" % h, h)],
                       0x1000)
    assert not _ra_unlabelled([("", "  CHKP SHA-256  %s  (1 cluster, 4 KiB)" % h, h)], 0x1000)
    assert not _ra_unlabelled([("", "  SHA-256: %s (1 cluster, 64 KiB)" % h, h)], 0x10000)
    assert _ra_unlabelled([("", "  SHA-256 (1 cluster, 4 KiB): %s" % h, h)], 0x1000)
    assert _ra_unlabelled([("  (1 cluster, 4 KiB)", "  SHA-256: %s" % h, h)], 0x1000)


def test_f11_lb30_control_the_byte_key_reader():
    """Not a RED. The LB30 reader: `CheckpointSHA256Bytes` and per copy `SHA256Bytes` alone pass; LB8's superseded
    spellings, a snake_case twin beside the decided key, a wrong value, or a missing copy key are refused."""
    j = {"chkp_sha256": "ab" * 32, "CheckpointSHA256Bytes": 4096}
    cps = [{"sha256": "cd" * 32, "SHA256Bytes": 4096}, {"sha256": "ef" * 32, "SHA256Bytes": 4096}]
    assert not _byte_key_problems(j, cps, 4096)
    assert _byte_key_problems(j, cps, 65536)
    assert _byte_key_problems({"ChkpSha256Bytes": 4096}, [{"Sha256Bytes": 4096}] * 2, 4096)       # LB8's names
    assert _byte_key_problems(dict(j, chkp_sha256_bytes=4096), cps, 4096)                       # a twin key
    assert _byte_key_problems(j, [cps[0], {"sha256": "ef" * 32}], 4096)                         # a copy without it
    assert _byte_key_problems(j, [dict(cps[0], Sha256Bytes=4096), cps[1]], 4096)                # a twin per copy


@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_f11_control_64k_json_hashes_are_already_the_cluster_on_image_win11refs5g64k(cmd):
    """Not a RED. On 64K the page is one cluster, so the JSON values already hash the one cluster and must stay."""
    ck = MC.Chkp(MC.corpus(K64))
    rc, out, err = _crun(FOREFST, K64, cmd, "--json")
    j = _json(out, cmd + " --json")
    pairs = MC._json_chkp_hashes(j, set(ck.lcns))
    top = jget(j, "chkp_sha256", F._SUMMARY_KEYS)                  # acceptance 1.14.0 (K21)
    assert top in ck.one.values() and len(pairs) == 2 and all(h == ck.one[l] for l, h in pairs), (top, pairs)


def test_f11_control_the_64k_checkpoint_read_is_already_one_cluster_on_image_win11refs5g64k():
    """Not a RED. checkpoint_select reads max(16 KiB, cluster) = one cluster on 64K; after LB2 it still does."""
    p = MC.corpus(K64)
    ps = MC._refs_ps(p)
    cs = MC._cluster_size(p, ps)
    with open(p, "rb") as fh:
        sel = F.checkpoint_select(fh, ps, cs, F.parse_supb(fh, ps, cs), require_roots=True)
    assert cs == 65536 and [len(c["raw"]) for c in sel["copies"]] == [cs, cs], [len(c["raw"]) for c in sel["copies"]]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N261 -- the export manifest's checkpoint labels are checkpoint_select's roles (decision 25.4)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Today `export metadata` labels a copy `current` when its clock is the top clock, whatever its self-checksum, and both
# copies of a tie `current (tied)` (fd:17176-17195; it calls checkpoint_select WITHOUT require_roots). Decided (decision
# 25.4, N261's row): the labels come from checkpoint_select's roles -- in use / newest / superseded / tied. The roles
# expected here follow from each plant: a stale view (the newest copy, vclock 64, fails its self-checksum) -> newest +
# in use; a tie (both copies vclock 64, slot 0 kept by F1) -> in use + tied; N361's shape (the newer copy has no root
# list, K-9 c) -> newest + in use; undamaged -> in use + superseded.

_ROLE = re.compile(r"(?i)\b(in use|newest|superseded|tied|current)\b")


def _n261_tie(v):
    AB.make_tie(v, False)


_N261 = {"undamaged": (lambda v: None, "in use", "superseded"),
         "stale": (AV._flip_newest, "newest", "in use"),
         "tie": (_n261_tie, "in use", "tied"),
         "n361-shape": (lambda v: G2C2._n361b_plant(v, "verifies"), "newest", "in use")}


def _export_chkp_labels(v, tmp_path):
    d = str(tmp_path / ("bundle_%d" % len(os.listdir(str(tmp_path)))))
    rc, out, err = G2C._run_split(FOREFST, v.path, "export", "metadata", d, "--what", "chkp",
                                  cwd=os.path.dirname(v.path), cli=v.geo.cli)
    mp = os.path.join(d, "manifest.json")
    _fx(os.path.isfile(mp), "export metadata wrote no manifest" + _ctx(rc, out, err))
    man = F.read_bundle_manifest(d)          # acceptance 1.14.0 (E-2, K21): read as the bundle reader reads it
    arts = {a.get("lcn"): a for a in man.get("artifacts", []) if re.match(r"checkpoint_\d+_lcn", a.get("file", ""))}
    _fx(set(arts) == {v.geo.lo, v.geo.hi}, "exported checkpoints %r" % sorted(arts))
    shutil.rmtree(d, ignore_errors=True)
    return rc, {l: a.get("source", "") for l, a in arts.items()}


# RED 1.13.2 N261: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("shape", sorted(_N261))
def test_n261_manifest_labels_are_checkpoint_selects_roles(vol, tmp_path, shape):
    plant, lo_role, hi_role = _N261[shape]
    plant(vol)
    rc, src = _export_chkp_labels(vol, tmp_path)
    for lcn, want in ((vol.geo.lo, lo_role), (vol.geo.hi, hi_role)):
        words = {w.lower() for w in _ROLE.findall(src[lcn])}
        allowed = {want} | ({"tied"} if shape == "tie" else set())
        assert want in words and words <= allowed, (
            "%s: the checkpoint copy at LCN 0x%x is labelled %r; checkpoint_select's role is %r (decision 25.4)"
            % (shape, lcn, src[lcn], want))


def test_n261_control_undamaged_volume_labels_the_newest_copy_at_the_top(vol, tmp_path):
    """Not a RED. Undamaged: the copy in use (vclock 64) carries the top label ('current' today, 'in use' after the fix)
    and the older copy 'superseded' -- the label sits on the right copy; only the word changes."""
    rc, src = _export_chkp_labels(vol, tmp_path)
    assert re.search(r"(?i)\b(current|in use)\b", src[vol.geo.lo]) and "superseded" in src[vol.geo.hi], src


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N369 (widened) -- on N361's shape every label names the newest copy too; E118's margin and wording
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N361's shape (G2c2's plant): the newest copy (slot 0, the lower LCN, vclock 64) passes its self-checksum but has no
# root list (+0x90 = 0), so the volume is read from the older copy (vclock 63) and every command says the stale view and
# exits 2 (N361 (b), kept). These sites still describe only the copies checkpoint_select takes as candidates (FIX_G2c2
# section 6 items 1-2; REVIEW_G2c2_correctness C2; REVIEW_G2c2_tests T4; GOLDEN_G2c2_critic K-9). Decided: they name the
# newest copy too (N369's row). The control for each site is the stale view (the newest copy FAILED its self-checksum),
# where every one of them already names the newer copy.

def _n361(v):
    G2C2._n361b_plant(v, "verifies")


# RED 1.13.2 N369: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_n369_primary_label_names_the_newest_copy_on_n361s_shape(vol, cmd):
    _n361(vol)
    rc, out, err = _vrun(vol, FOREFST, cmd)
    prim = [ln for ln in out.splitlines() if re.search(r"CHKP primary\s+LCN", ln)]
    _fx(len(prim) == 1, "%s: CHKP primary lines %r" % (cmd, prim) + _ctx(rc, out, err))
    _keep(rc == 2, "N361 (b): the stale view exits 2" + _ctx(rc, out, err))
    assert AB._lcn_re(vol.geo.lo).search(prim[0]) and re.search(r"vclock=%d\b" % CLOCK_NEW, prim[0]), (
        "CHKP primary names %r; the newest copy is LCN 0x%x (vclock %d)" % (prim[0].strip(), vol.geo.lo, CLOCK_NEW))


# RED 1.13.2 N369: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_n369_json_role_names_the_newest_copy_on_n361s_shape(vol, cmd):
    _n361(vol)
    rc, out, err = _vrun(vol, FOREFST, cmd, "--json")
    cps = {jint(jget(c, "lcn")): c for c in jget(jget(_json(out, cmd + " --json"), "bootstrap_backups") or {},
                                                  "checkpoints", default=[])}             # acceptance 1.14.0 (K21, K9)
    _fx(set(cps) == {vol.geo.lo, vol.geo.hi}, "checkpoint copies %r" % sorted(cps))
    _keep(jget(cps[vol.geo.lo], "use") == "newest" and jget(cps[vol.geo.hi], "use") == "in use",
          "decision 25.4's role words (`use`) are right on this shape today: %r" % {hex(l): jget(c, "use")
                                                                                for l, c in cps.items()})
    got = {hex(l): jget(c, "role") for l, c in cps.items()}
    assert jget(cps[vol.geo.lo], "role") == "PRIMARY" and jget(cps[vol.geo.hi], "role") == "secondary", (
        "JSON role %r; PRIMARY is the newest copy, LCN 0x%x" % (got, vol.geo.lo))


# RED 1.13.2 N369: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_n369_json_fallback_keys_say_the_newest_copy_is_not_used_on_n361s_shape(vol, cmd):
    """The keys' own meaning, settled by LB18 (report S1; FIX_G2c2 section 6 item 1): the copy in use is not the newest
    (selected via a fallback), and the newest copy cannot be used (its root list) -- both true on this shape."""
    _n361(vol)
    rc, out, err = _vrun(vol, FOREFST, cmd, "--json")
    bb = jget(_json(out, cmd + " --json"), "bootstrap_backups") or {}
    got = (jget(bb, "checkpoint_selected_via_fallback"), jget(bb, "checkpoint_authoritative_unusable"))
    assert got == (True, True), "checkpoint_selected_via_fallback / checkpoint_authoritative_unusable = %r" % (got,)


def _n369_site(v, site):
    """The line(s) of one N369 site, and whether they name the newer copy (slot 0, LCN lo, vclock 64)."""
    off = v.at(v.geo.lo)
    off_rx = re.compile(r"(?i)(?<![0-9a-z])0x0*%x(?![0-9a-z])" % off)
    if site == "supb-v-latest_checkpoint":
        rc, out, err = _vrun(v, REFSANALYSIS, "supb", "-v")
        lines = [ln for ln in out.splitlines() if ln.strip().startswith("checkpoint_in_use")]     # E1c: N355
        named = [ln for ln in lines if off_rx.search(ln)]
    elif site == "supb-verify-latest_identified":
        rc, out, err = _vrun(v, REFSANALYSIS, "supb", "--verify")
        lines = [ln for ln in out.splitlines() if re.match(r"\s*in_use_identified\b", ln)]       # E1c: N355
        named = [ln for ln in lines if re.search(r"#1\b|\bvc=%d\b" % CLOCK_NEW, ln) or off_rx.search(ln)]
    elif site == "deleted-header":
        rc, out, err = _vrun(v, FOREFST, "deleted")
        lines = [ln for ln in out.splitlines() if re.match(r"\s*Checkpoints:", ln)]
        named = [ln for ln in lines if re.search(r"\b%d\b[^;)]*\bnewest\b" % CLOCK_NEW, ln)]
    else:                                                    # containers-note
        rc, out, err = _vrun(v, REFSANALYSIS, "containers")
        lines = [ln for ln in out.splitlines() if re.search(r"(?i)tables below are read from", ln)]
        named = [ln for ln in lines if AB._lcn_re(v.geo.lo).search(ln)]
    return rc, out, err, lines, named


_N369_SITES = ["supb-v-latest_checkpoint", "supb-verify-latest_identified", "deleted-header", "containers-note"]


# RED 1.13.2 N369: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("site", _N369_SITES)
def test_n369_each_site_names_the_newest_copy_too_on_n361s_shape(vol, site):
    _n361(vol)
    rc, out, err, lines, named = _n369_site(vol, site)
    _keep(rc == 2, "N361 (b): the stale view exits 2" + _ctx(rc, out, err))
    if site != "containers-note":
        _fx(len(lines) == 1, "%s: lines %r" % (site, lines) + _ctx(rc, out, err))
    assert named, ("%s does not name the newest checkpoint copy (LCN 0x%x, offset 0x%x, vclock %d): %r"
                   % (site, vol.geo.lo, vol.at(vol.geo.lo), CLOCK_NEW, lines)) + _ctx(rc, out, err)


@pytest.mark.parametrize("site", [s for s in _N369_SITES if s != "supb-verify-latest_identified"])
def test_n369_control_a_failed_newer_copy_is_named_by_each_site(vol, site):
    """Not a RED. The stale view (the newest copy FAILED its self-checksum): each of these sites already names the newer
    copy -- the form N369 asks for on N361's shape. (`supb --verify` latest_identified names only the copy in use here
    too: report S2, settled by LB19 inside N369; the group-5 fixer writes that RED first.)"""
    AV._flip_newest(vol)
    rc, out, err, lines, named = _n369_site(vol, site)
    assert rc == 2 and named, "%s: %r" % (site, lines) + _ctx(rc, out, err)


def test_n369_lb19_supb_verify_latest_identified_names_the_newer_copy_on_a_stale_view(vol):
    """LB19 (inside N369, group 5, XS; written first by the group-5 fixer, WAVEB_PREP LB19). On the stale view (the
    newest copy, slot 0 at vclock 64, FAILED its self-checksum) refsanalysis `supb --verify`'s latest_identified row
    names the newer copy too -- its index (#1), its clock (vc=64) or its offset -- as every other N369 site does on
    this shape (the control above: `supb -v` latest_checkpoint, `deleted`'s header, `containers`' note; decision 35,
    N261's role vocabulary). Today it names only the copy in use (#2 vc=63)."""
    AV._flip_newest(vol)
    rc, out, err, lines, named = _n369_site(vol, "supb-verify-latest_identified")
    _keep(rc == 2, "the stale view exits 2 (a FAILED self-checksum row, decision 25.2)" + _ctx(rc, out, err))
    _fx(len(lines) == 1, "supb --verify latest_identified lines %r" % lines + _ctx(rc, out, err))
    assert named, ("supb --verify latest_identified does not name the newer checkpoint copy (LCN 0x%x, offset 0x%x, "
                   "vclock %d) on the stale view: %r" % (vol.geo.lo, vol.at(vol.geo.lo), CLOCK_NEW, lines)) \
        + _ctx(rc, out, err)


def test_n369_control_the_json_fallback_keys_are_true_on_a_stale_view(vol):
    """Not a RED. The stale view: both keys already say the newest copy is not used."""
    AV._flip_newest(vol)
    rc, out, err = _vrun(vol, FOREFST, "summary", "--json")
    bb = jget(_json(out, "summary --json"), "bootstrap_backups") or {}
    assert jget(bb, "checkpoint_selected_via_fallback") is True and jget(bb, "checkpoint_authoritative_unusable") is True


def _root_check_extent(raw):
    """The highest byte (exclusive) the root check reads for roots 0xC, 7, 8 of a CHKP record: the offset-table entries
    and each reference (layout read here: +0x5C reference length, +0x78 flags bit 0x200 = indirect table at +0x94)."""
    dl = max(struct.unpack_from("<I", raw, 0x5C)[0], 0x30)
    flags = struct.unpack_from("<I", raw, 0x78)[0]
    olb = struct.unpack_from("<I", raw, 0x94)[0] if flags & 0x200 else 0x94
    hi = 0
    for idx in (0xC, 7, 8):
        oe = olb + 4 * idx
        hi = max(hi, oe + 4)
        ro = struct.unpack_from("<I", raw, oe)[0] if oe + 4 <= len(raw) else 0
        if ro:
            hi = max(hi, ro + dl)
    return hi


def test_n369_control_the_root_check_reads_inside_one_cluster(vol):
    """Not a RED (K-9 a). The highest byte the root check reads is 0x680 on every corpus copy (census 2.2); on both
    test volumes it lies inside the first cluster and the check passes for both copies, so the one-cluster read (LB2)
    changes no root verdict here -- today and after the fix."""
    ext = {hex(l): _root_check_extent(vol.block(l)) for l in (vol.geo.lo, vol.geo.hi)}
    _fx(all(x <= CS for x in ext.values()), "the root check reads past one cluster: %r" % ext)
    with open(vol.path, "rb") as fh:
        sel = F.checkpoint_select(fh, vol.geo.ps, CS, F.parse_supb(fh, vol.geo.ps, CS), require_roots=True)
    assert all(c["root_fail"] == [] and c["root_unchecked"] == [] for c in sel["copies"]), [
        (c["lcn"], c["root_fail"], c["root_unchecked"]) for c in sel["copies"]]


# RED 1.13.2 N369: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("where", ["reference", "offset-table"])
def test_n369_a_root_reference_past_the_record_is_worded_with_e118(vol, where):
    raw = bytearray(vol.block(vol.geo.lo))                  # the checkpoint record: one cluster
    flags = struct.unpack_from("<I", raw, 0x78)[0]
    olb = struct.unpack_from("<I", raw, 0x94)[0] if flags & 0x200 else 0x94
    if where == "reference":
        idx = 7
        struct.pack_into("<I", raw, olb + 4 * idx, CS + 0x100)        # root 7's reference lies past the record
    else:
        idx = 0xC
        struct.pack_into("<I", raw, 0x78, flags | 0x200)              # an indirect offset table ...
        struct.pack_into("<I", raw, 0x94, CS - 0x10)                  # ... whose entries lie past the record
    why = []
    with open(vol.path, "rb") as fh:
        F._chkp_root_failures(fh, vol.geo.ps, CS, bytes(raw), [], why)
    texts = [w for i, w in why if i == idx]
    _fx(texts, "the root check did not report root %#x of a record whose %s lies past it: %r" % (idx, where, why))
    assert not [w for w in texts if re.search(r"(?i)\bpage\b", w)], (
        "root %#x: %r -- the record is one cluster (E118); 'the page' is the 16 KiB allocation" % (idx, texts))
    assert [w for w in texts if re.search(r"(?i)\b(?:record|cluster)\b", w)], (
        "root %#x: %r does not say it runs past the checkpoint record (one cluster)" % (idx, texts))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N252 -- closed on the current tree (not REDs; the check LB7 asks for N254, applied to N252: "if it is still open")
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N252: on a tie `summary`'s CHKP lines showed no tie; on an upgraded volume `summary` printed a bare 'DIFFERS' while
# `integrity` explained the backup boot sector's older version. Measured on this tree: both are fixed (B1/N252 in
# group 2: `_chkp_status` adds "tied clock", `_redundancy_notes` is printed by `summary` and carried in its JSON).

@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_n252_closed_summary_shows_a_checkpoint_tie(vol, cmd):
    AB.make_tie(vol, False)
    rc, out, err = _vrun(vol, FOREFST, cmd)
    rows = _chkp_rows(out)
    assert len(rows) == 2 and all(re.search(r"(?i)\btied\b", r[1]) for r in rows), [r[1] for r in rows]
    rc, out, err = _vrun(vol, FOREFST, cmd, "--json")
    bb = jget(_json(out, cmd + " --json"), "bootstrap_backups") or {}
    assert jget(bb, "checkpoint_tie") is True and all(jget(c, "tied_clock") for c in jget(bb, "checkpoints", default=[]))


UPGRADED = "step3/win10to11refs4g.raw"


def _boot_versions(rel):
    """(primary, backup) boot-sector versions, read here: the VBR at the partition start, the backup at its last sector."""
    p = MC.corpus(rel)
    ps = MC._refs_ps(p)
    with open(p, "rb") as fh:
        fh.seek(ps)
        v = fh.read(512)
        tot, ss = struct.unpack_from("<Q", v, 0x18)[0], struct.unpack_from("<I", v, 0x20)[0]
        fh.seek(ps + (tot - 1) * ss)
        b = fh.read(512)
    _fx(v[3:7] == b"ReFS" and b[3:7] == b"ReFS", "%s: no primary/backup boot sector" % rel)
    return "%d.%d" % (v[0x28], v[0x29]), "%d.%d" % (b[0x28], b[0x29])


@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_n252_closed_summary_explains_the_upgraded_backup_boot_sectors_version_on_image_win10to11refs4g(cmd):
    pv, bv = _boot_versions(UPGRADED)
    _fx((pv, bv) == ("3.14", "3.4"), "%s: boot sectors %s / %s" % (UPGRADED, pv, bv))
    rc, out, err = _crun(FOREFST, UPGRADED, cmd)
    # K29 (wave C step C1, N437): the versions are written `ReFS 3.14` (they were `v3.14`); either form is read
    _v = lambda ver, t: re.search(r"(?:\bv|\bReFS )%s(?!\d|\.\d)" % re.escape(ver), t)   # C1-15: a sentence-final "3.4." matches
    notes = [ln for ln in out.splitlines() if re.search(r"(?i)\bnote\b", ln) and _v(pv, ln) and _v(bv, ln)]
    assert notes, "no note names both boot-sector versions" + _ctx(rc, out, err)
    rc, out, err = _crun(FOREFST, UPGRADED, cmd, "--json")
    rn = jget(_json(out, cmd + " --json"), "redundancy_notes") or []
    assert [n for n in rn if _v(pv, n) and _v(bv, n)], rn


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A13 -- the critic's missing control: the "payload is identical" note over EQUAL payloads
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _supb_payload(block):
    """A superblock copy with its own fields masked (census a13_supb.py): the page-header self-LCN (+0x20, 8 bytes) and
    the self-descriptor the header declares (+0x78 offset, +0x7C length)."""
    b = bytearray(block)
    b[0x20:0x28] = b"\0" * 8
    d, n = struct.unpack_from("<II", block, 0x78)
    if 0 < d < len(b) and 0 < n <= len(b) - d:
        b[d:d + n] = b"\0" * n
    return bytes(b)


@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
def test_a13_control_the_identical_payload_note_is_printed_over_equal_payloads(vol, cmd):
    """Not a RED. All three superblock copies verify and their payloads are equal (checked here, masked); the note
    'their payload is identical' is printed today and must still be printed after A13's comparison (120 of 120 corpus
    volumes are this case, census section 5)."""
    copies = (vol.geo.supb,) + vol.geo.backups
    _fx(all(vol.verifies(l) is True for l in copies), "a superblock copy does not verify")
    _fx(len({_supb_payload(vol.block(l)) for l in copies}) == 1, "the superblock payloads differ")
    rc, out, err = _vrun(vol, FOREFST, cmd)
    assert rc == 0 and [ln for ln in out.splitlines() if AV._IDENTICAL_NOTE.search(ln)], _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N417 (LB50; wave B part 3, written before the fix) -- two VERIFIED superblock copies whose payloads differ
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Since A13 (part 2) `summary` names a superblock copy whose payload differs from the copy the volume is read from, and
# changes no exit code. LB50: when both copies VERIFY (each passes its own self-checksum) a payload difference is a
# disagreement between redundant copies -- a redundancy condition (V-a, decision 20.3): exit 2 in the commands that
# report redundancy (`summary`, `fastsummary`, `integrity`, refsanalysis `supb --verify`), the differing copies named
# (A13). 0 corpus volumes (equal on 120/120, census a13_supb.py). Plant: test_1132_red_a_verdicts' `_flip_backup_guid`
# with `reseal` (one GUID byte of the first backup flipped, its self-checksum recomputed: it verifies).

_N417_CMDS = {"summary": (FOREFST, "summary"), "fastsummary": (FOREFST, "fastsummary"),
              "integrity": (FOREFST, "integrity"), "ra-supb-verify": (REFSANALYSIS, "supb", "--verify")}


def _n417_named(out, lcn):
    """The lines that name the backup at `lcn` together with a difference (or the GUID it carries)."""
    return [ln for ln in out.splitlines() if AB._lcn_re(lcn).search(ln)
            and (AV._DIFFERS.search(ln) or re.search(r"(?i)GUID|payload", ln))]


@pytest.mark.parametrize("cmd", sorted(_N417_CMDS))
def test_n417_two_verified_superblock_copies_whose_payloads_differ_exit_2_where_redundancy_is_reported(vol, cmd):
    b = AV._flip_backup_guid(vol, True)
    _fx(vol.verifies(vol.geo.supb) is True and vol.verifies(b) is True, "the two superblock copies do not both verify")
    tool, *args = _N417_CMDS[cmd]
    rc, out, err = _vrun(vol, tool, *args)
    named = _n417_named(out + "\n" + err, b)
    assert rc == 2 and named, "two superblock copies verify and their payloads differ (the backup at LCN 0x%x): `%s` " \
        "must exit 2 (exit %d; LB50) and name the differing copy (%s)" % (b, " ".join(args), rc,
                                                                           "named" if named else "not named") \
        + _ctx(rc, out, err)


@pytest.mark.parametrize("cmd", [(FOREFST, "files", "--csv"), (FOREFST, "usn", "--stats"), (REFSANALYSIS, "supb")],
                         ids=["files-csv", "usn-stats", "ra-supb"])
def test_n417_control_other_commands_keep_their_exit_code(vol, cmd):
    """Not a RED. V-a: the volume is read the same way (from the primary, which verifies), so the commands that do not
    report redundancy keep their exit code over the differing backup. (Wave E step E1c, N257: compared with the same
    command before the flip -- `usn` exits 2 on this volume since then, for a reason of its own: it has no system
    metadata table, so whether there is a journal is not determined, as `summary` says.)"""
    tool, *args = cmd
    rc0, out0, err0 = _vrun(vol, tool, *args)
    AV._flip_backup_guid(vol, True)
    rc, out, err = _vrun(vol, tool, *args)
    assert rc == rc0, "%d before the flip, %d after" % (rc0, rc) + _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N171 -- the passthrough runs forefst with forefst's recursion limit and BrokenPipe handling
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `refsanalysis <image> forefst <cmd>` calls forefst.main() inside refsanalysis's main(), which has already set its own
# recursion limit (40,000, ra:4649); forefst's main sets max(current, 4000) (fd:18460), so the passthrough keeps 40,000.
# forefst.py's __main__ handles a closed pipe (fd:19242); refsanalysis's __main__ catches SystemExit only (ra:4820-4827).
# Decided (N171's row, "lands with A12"; placed: decision 34 sweep): the passthrough uses forefst's limit and handler.

class _Stop(BaseException):
    """Raised by the patched bootstrap: the run has reached the command; nothing else is needed."""


# RED 1.13.2 N171: green with wave B part 2's fix (the strict xfail mark removed)
def test_n171_passthrough_runs_forefst_with_forefsts_recursion_limit(monkeypatch, tmp_path):
    import refsanalysis as RA
    v = AB._synthetic_vol(tmp_path)
    seen = {}
    run = []
    stopped = []

    def stop(*_a, **_k):
        seen[run[-1]] = sys.getrecursionlimit()
        raise _Stop()
    monkeypatch.setattr(F, "bootstrap", stop)
    _fx(sys.modules.get("forefst") is F, "refsanalysis would run another forefst module")
    old = sys.getrecursionlimit()
    try:
        for name, argv, fn in (("direct", ["forefst.py", v.path, "files"], F.main),
                               ("passthrough", ["refsanalysis.py", v.path, "forefst", "files"], RA.main)):
            run.append(name)
            sys.setrecursionlimit(1000)
            monkeypatch.setattr(sys, "argv", argv)
            try:
                fn()
            except _Stop:                                 # LB45: the expected stop, recorded and checked below
                stopped.append(name)
            except SystemExit as e:
                raise RedFixtureError("%s exited (%r) before reaching the command" % (name, e.code))
    finally:
        sys.setrecursionlimit(old)
    _fx(set(seen) == {"direct", "passthrough"} and stopped == ["direct", "passthrough"],
        "a run did not reach bootstrap: %r (stopped there: %r)" % (seen, stopped))
    assert seen["passthrough"] == seen["direct"], (
        "recursion limit at the command: passthrough %d, forefst.py %d" % (seen["passthrough"], seen["direct"]))


PIPE_IMG = "step1/win11refsmini.raw"


def _closed_pipe_run(tool, img, *args):
    """(rc, stderr) of a run whose stdout reader closes at once: the tool's first flush hits EPIPE."""
    p = subprocess.Popen([sys.executable, "-B", tool, img] + list(args), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, cwd=REPO)
    p.stdout.close()
    try:
        err = p.stderr.read()
        p.wait(timeout=AB.TIMEOUT)
    except subprocess.TimeoutExpired:
        p.kill()
        raise RedFixtureError("timeout with a closed stdout")
    return p.returncode, err.decode("utf-8", "replace")


def _pipe_premise():
    rc, out, err = _crun(FOREFST, PIPE_IMG, "files", "--json")
    _fx(rc == 0 and len(out) > 2 * 8192, "files --json writes %d bytes: too little to fill the stdout buffer" % len(out))


# RED 1.13.2 N171: green with wave B part 2's fix (the strict xfail mark removed)
def test_n171_passthrough_handles_a_closed_pipe_as_forefst_does_on_image_win11refsmini():
    _pipe_premise()
    rc, err = _closed_pipe_run(REFSANALYSIS, MC.corpus(PIPE_IMG), "forefst", "files", "--json")
    frc, ferr = _closed_pipe_run(FOREFST, MC.corpus(PIPE_IMG), "files", "--json")
    _keep(frc == 0 and "Traceback" not in ferr, "forefst.py's own handler (fd:19242): rc %d\n%s" % (frc, ferr[-1500:]))
    assert "Traceback" not in err and "BrokenPipeError" not in err, "passthrough stderr:\n" + err[-1500:]
    assert rc == frc, "passthrough rc %d, forefst.py rc %d" % (rc, frc)


def test_n171_control_forefst_handles_a_closed_pipe_on_image_win11refsmini():
    """Not a RED. The direct run: no traceback, exit 0 -- the behaviour the passthrough must take over."""
    _pipe_premise()
    rc, err = _closed_pipe_run(FOREFST, MC.corpus(PIPE_IMG), "files", "--json")
    assert rc == 0 and "Traceback" not in err and "BrokenPipeError" not in err, err[-1500:]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N265 / N409 -- a contradicted boot-sector version: decision 29's command set, one sentence in text and JSON
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Today only cmd_fastsummary registers it (`_VERSION_CONTRADICTED`): forefst `summary`/`fastsummary` exit 2, while
# `integrity` (all forms), refsanalysis `summary` (both forms) and `boot --verify` exit 0 with no version finding
# (census 2.3). Decided (decision 29's pattern, N265's settlement in the decision scan): forefst `summary`, `fastsummary`,
# `integrity`, refsanalysis `summary` and `boot --verify` report it with the shared text and exit 2; every other command
# keeps its exit code. N409 (decision 35): the TEXT of `summary`/`fastsummary` carries the same sentence as the JSON's
# `version_contradiction`, with N134's major (6.66 reads "v6.66"). Oracle for "the shared text": forefst `summary
# --json`'s `version_contradiction` list (its N134 fix moves the oracle with it); pinned by the controls below.

STEP4C = "step4continuing/win11refsmini_afterchangingversion"
V666, V666O, V315 = STEP4C + ".raw", STEP4C + "_opened.raw", STEP4C + "_opened_rechangedtoversion315.raw"
V312 = STEP4C + "_opened_rechangedtoversion312.raw"
CONTRA = [V666, V666O, V315]
CONTRA_IDS = ["image-6.66", "image-6.66-opened", "image-3.15"]


def _vbr_version(rel):
    p = MC.corpus(rel)
    ps = MC._refs_ps(p)
    with open(p, "rb") as fh:
        fh.seek(ps)
        v = fh.read(512)
    _fx(v[3:7] == b"ReFS", "%s: no boot sector" % rel)
    return v[0x28], v[0x29]


_CONTRA_SENT = {}


def _contra_sentences(rel):
    """The shared sentences (forefst `summary --json` `version_contradiction`), checked against the boot sector read
    here: it declares 6.66 or 3.15 while $VOLUME_INFORMATION says 3.14."""
    if rel not in _CONTRA_SENT:
        maj, mn = _vbr_version(rel)
        _fx((maj, mn) in ((6, 66), (3, 15)), "%s: the boot sector declares %d.%d" % (rel, maj, mn))
        rc, out, err = _crun(FOREFST, rel, "summary", "--json")
        sents = jget(_json(out, "summary --json"), "version_contradiction") or []
        # K29 (wave C step C1, N437): the version form `ReFS 6.66` (it was `v6.66`), either read
        _fx(rc == 2 and len(sents) == 2 and any(re.search(r"declares (?:v|ReFS )%d\.%d\b" % (maj, mn), s)
                                                for s in sents),
            "%s: summary --json's version_contradiction %r (rc %d)" % (rel, sents, rc))
        _CONTRA_SENT[rel] = (maj, mn, [_ws(s) for s in sents])
    return _CONTRA_SENT[rel]


_N265_SET = {"fd-integrity": (FOREFST, ("integrity",)), "fd-integrity-checksums": (FOREFST, ("integrity", "--checksums")),
             "fd-integrity-json": (FOREFST, ("integrity", "--json")), "ra-summary": (REFSANALYSIS, ("summary",)),
             "ra-summary-json": (REFSANALYSIS, ("summary", "--json")), "ra-boot-verify": (REFSANALYSIS, ("boot", "--verify"))}


def _says_all(tool_args_out, sents):
    """Every shared sentence is in the output: as a JSON string value (a JSON output) or in the flattened text."""
    args, out = tool_args_out
    if "--json" in args:
        vals = [_ws(s) for s in _strings(_json(out, " ".join(args)))]
        return [s for s in sents if not any(s in v for v in vals)]
    flat = _flat(out)
    return [s for s in sents if s not in flat]


# RED 1.13.2 N265: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", sorted(_N265_SET))
@pytest.mark.parametrize("rel", CONTRA, ids=CONTRA_IDS)
def test_n265_the_command_set_states_the_contradiction_and_exits_2(rel, cmd):
    maj, mn, sents = _contra_sentences(rel)
    tool, args = _N265_SET[cmd]
    rc, out, err = _crun(tool, rel, *args)
    missing = _says_all((args, out + ("\n" + err if "--json" not in args else "")), sents)
    assert not missing, "%s does not state %r" % (cmd, missing) + _ctx(rc, out, err)
    assert rc == 2, "%s exits %d on a contradicted boot-sector version (decision 29's set: 2)" % (cmd, rc)


@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
@pytest.mark.parametrize("rel", CONTRA, ids=CONTRA_IDS)
def test_n265_control_forefst_summary_already_registers_it(rel, cmd):
    """Not a RED. forefst `summary`/`fastsummary --json` carry the finding and exit 2 today (the oracle's own command)."""
    maj, mn, sents = _contra_sentences(rel)
    rc, out, err = _crun(FOREFST, rel, cmd, "--json")
    assert rc == 2 and [_ws(s) for s in _json(out, cmd).get("version_contradiction", [])] == sents


_N265_OTHERS = {"fd-files-csv": (FOREFST, ("files", "--csv")), "fd-usn-stats": (FOREFST, ("usn", "--stats")),
                "ra-boot": (REFSANALYSIS, ("boot",)), "ra-boot-vv": (REFSANALYSIS, ("boot", "-vv"))}


@pytest.mark.parametrize("cmd", sorted(_N265_OTHERS))
def test_n265_control_other_commands_keep_their_exit_code_on_image_afterchangingversion(cmd):
    """Not a RED. Decision 29's V-a pattern: a command outside the set reads the volume the same way and keeps exit 0
    (golden rc 0 for the golden forms among these)."""
    _contra_sentences(V666)
    tool, args = _N265_OTHERS[cmd]
    rc, out, err = _crun(tool, V666, *args)
    assert rc == 0, "%s exits %d" % (cmd, rc) + _ctx(rc, out, err)


@pytest.mark.parametrize("cmd", ["fd-integrity", "ra-summary", "ra-boot-verify"])
def test_n265_control_a_corroborated_314_boot_sector_is_no_finding_on_image_rechangedtoversion312(cmd):
    """Not a RED. A 3.14 boot sector corroborated by $VOLUME_INFORMATION: no version finding, exit 0 (N265's control)."""
    _fx(_vbr_version(V312) == (3, 14), "%s: not a 3.14 boot sector" % V312)
    tool, args = _N265_SET[cmd]
    rc, out, err = _crun(tool, V312, *args)
    assert rc == 0 and not re.search(r"(?i)contradict|not corroborated|the boot sector (?:says|declares) v",
                                     out + err), _ctx(rc, out, err)


# RED 1.13.2 N409: green with wave B part 2's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd", ["summary", "fastsummary"])
@pytest.mark.parametrize("rel", CONTRA, ids=CONTRA_IDS)
def test_n409_text_carries_the_same_contradiction_sentence_as_the_json(rel, cmd):
    maj, mn, sents = _contra_sentences(rel)
    rc, out, err = _crun(FOREFST, rel, cmd)
    _keep(rc == 2 and "VERSION CONTRADICTED" in out, "the text's volume state" + _ctx(rc, out, err))
    text = _flat(out + "\n" + err)
    missing = [s for s in sents if s not in text]
    assert not missing, "%s text does not carry the JSON's sentence(s) %r" % (cmd, missing) + _ctx(rc, out, err)
    assert re.search(r"boot sector says (?:v|ReFS )%d\.%d\b" % (maj, mn), text) and not re.search(
        r"(?:v|ReFS )3\.66\b", out + err), (
        "the text's sentence must give the boot sector's own version v%d.%d (N134)" % (maj, mn))


def test_n409_control_the_315_sentence_is_already_right_in_the_json():
    """Not a RED. N409's control: on the 3.15 image the JSON's sentence names the boot sector's own version."""
    maj, mn, sents = _contra_sentences(V315)
    assert any(re.search(r"the boot sector says (?:v|ReFS )3\.15\b", s) for s in sents), sents      # K29 too


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N396 (LB5, T2a) -- timestomp's "cannot be corroborated before" clause names the earliest surviving record's time
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# step4/winsider: one wrapped sequence whose clock steps back 6 times; the lowest surviving USN 40,906,752 is dated
# 2026-05-11 20:34:50, while 75,448 surviving records are dated back to 10:37:29 (USN 59,226,288). Today the clause says
# "Files changed before 20:34:50 cannot be corroborated by it" (fd:5976). LB5: the start stays the lowest surviving USN and
# its time with T2's step-back note; the clause names the EARLIEST time among the surviving records. The times come from
# test_1132_red_g3's own carve (`_ws_premise`). One mode is run (`--csv`, the statement on stderr; the text mode prints
# the same `_usn_coverage_lines`) to bound the cost on the key (about 100 s per winsider run).

WS_EARLIEST = r"2026-05-11[ T]10:37:29"
WS_LOWEST_T = r"2026-05-11[ T]20:34:50"


def _ws_run():
    G3._ws_premise()
    r = G3._run(G3.WS, "timestomp", "--csv")
    _keep(r.rc == 0, "N219 moves no exit code on winsider" + r.ctx(G3.WS))
    return r, G3._sentences(r.err.splitlines())


# RED 1.13.2 N396: green with wave B part 3's fix (the strict xfail mark removed)
def test_n396_the_clause_names_the_earliest_surviving_records_time_on_image_winsider():
    r, s = _ws_run()
    clause = G3._before_uncovered(s)
    _fx(clause, "no 'cannot be corroborated before' clause on stderr" + r.ctx(G3.WS))
    assert [c for c in clause if re.search(WS_EARLIEST, c)], (
        "the clause %r does not name the earliest surviving record's time (%s)" % (clause, G3.WS_EARLIEST_TIME))
    assert not [c for c in clause if re.search(WS_LOWEST_T, c) and not re.search(WS_EARLIEST, c)], clause


def test_n396_control_the_start_stays_the_lowest_usn_with_the_step_back_note_on_image_winsider():
    """Not a RED. LB5 keeps the start: the lowest surviving USN 40,906,752 and its time, and T2's note (6 steps)."""
    r, s = _ws_run()
    assert G3._start_stated(s, [(G3.WS_LOWEST, WS_LOWEST_T)]) and G3._steps_back_stated(s, 6), r.ctx(G3.WS)


@pytest.mark.parametrize("rel,premise,earliest", [
    (G3.MFT, G3._mft_premise, r"2026-05-23[ T]07:38:44"),
    (G3.R8G, lambda: G3._n219_seq_premise(G3.R8G), r"2026-07-03[ T]10:12:01")],
    ids=["image-win11refstestmftecmd", "image-win11refs8g"])
def test_n396_control_the_clause_already_names_the_earliest_time_elsewhere(rel, premise, earliest):
    """Not a RED. A journal whose times never step back (the lowest USN is the earliest time) and a restart journal
    (the earlier sequence's first record is the earliest): the clause names the earliest surviving time today."""
    premise()
    r = G3._run(rel, "timestomp", "--csv")
    clause = G3._before_uncovered(G3._sentences(r.err.splitlines()))
    assert [c for c in clause if re.search(earliest, c)], (clause, r.ctx(rel))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The journal harness (BJ._harness's patches, plus a path map and `timestomp`) and $J builders of this module
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

HCS, J_PLCN = BJ.HCS, BJ.J_PLCN
JID_EARLIER = BJ.JID_ONE - 10 ** 13       # an id (= creation FILETIME) about 11.6 days before the current journal's


def _usn_rec(usn, name, fid, ts, reason=0x100, home=0x706, parent=0x706):
    """One USN_RECORD_V3 (own builder; an empty name allowed): FileReferenceNumber = home:fid, parent = parent:0."""
    nm = name.encode("utf-16-le")
    rl = (0x4C + len(nm) + 7) & ~7
    b = bytearray(rl)
    struct.pack_into("<IHH", b, 0, rl, 3, 0)
    struct.pack_into("<QQ", b, 0x08, fid, home)
    struct.pack_into("<QQ", b, 0x18, 0, parent)
    struct.pack_into("<QQII", b, 0x28, usn, ts, reason, 0)
    struct.pack_into("<IIHH", b, 0x40, 0, 0x20, len(nm), 0x4C)
    b[0x4C:0x4C + len(nm)] = nm
    return bytes(b)


class _JFile:
    """A sparse file carrying a $J of `nclusters` clusters at PLCN J_PLCN; `recs` = [(offset, record bytes)];
    `zeros` = clusters written as real zeros. Checked from the file by test_1132_red_g3's own carve."""

    def __init__(self, tmp_path, nclusters, recs, zeros=()):
        self.path, self.nclusters = str(tmp_path / "target.raw"), nclusters
        with open(self.path, "wb") as fh:
            fh.truncate((J_PLCN + nclusters + 16) * HCS)
            fh.seek(0)
            fh.write(b"\x01" * HCS)
            for c in zeros:
                fh.seek((J_PLCN + c) * HCS)
                fh.write(b"\0" * HCS)
            for off, b in recs:
                fh.seek(J_PLCN * HCS + off)
                fh.write(b)
        with open(self.path, "rb") as fh:
            fh.seek(J_PLCN * HCS)
            self.data = fh.read(nclusters * HCS)


def _jharness(monkeypatch, capsys, jr, cmd, args, entries, jid=BJ.JID_ONE, paths=None):
    """BJ._harness with two additions: `build_oid_path_map` returns `paths`, and `timestomp` is a command."""
    BJ._fresh(monkeypatch)
    raw = bytearray(0x24)
    struct.pack_into("<I", raw, 8, 12)
    struct.pack_into("<QQQ", raw, 12, jr.nclusters * HCS, 0, jid)
    streams = {"j_extents": [{"vlcn": J_PLCN, "plcn": J_PLCN, "file_vcn": 0, "clusters": jr.nclusters, "flags": 0x50}],
               "j_stream_size": 0x000E0080, "max_extents": [], "max_stream_size": 0, "metadata_raw": bytes(raw),
               "subrecord_count": 3, "j_declared": None}
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
    monkeypatch.setattr(F, "build_oid_path_map", lambda *a, **k: dict(paths or {}))
    BJ._empty_valid_mlog(monkeypatch, jr.path, jr.nclusters)  # LB61: was get_mlog_info -> None ("no MLog")
    monkeypatch.setattr(F, "walk_directory_tree", walk)
    capsys.readouterr()
    fn = {"usn": F.cmd_usn, "timeline": F.cmd_timeline, "timestomp": F.cmd_timestomp}[cmd]
    try:
        ret = fn(jr.path, list(args), None)
    except SystemExit as e:
        raise RedFixtureError("%s %s exited (%r):\n%s" % (cmd, " ".join(args), e.code, capsys.readouterr().err[-2000:]))
    except Exception as e:
        raise RedFixtureError("%s %s crashed: %r" % (cmd, " ".join(args), e)) from e
    rc = _rc_escalate()(0 if ret is None else ret)
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def _seq_journal(tmp_path, n=6):
    """Records USN = offset, times rising by 1 (one sequence)."""
    t0 = BJ.JID_ONE + 10 ** 8
    recs, off = [], 0
    for i in range(n):
        b = _usn_rec(off, "f%d.txt" % i, 0x10 + i, t0 + i)
        recs.append((off, b))
        off += len(b)
    return recs, off


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N400 -- journal_last_usn is the current sequence's; `timeline`/`timestomp` parse $J with the allocation
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# (a) `timestomp --json` `journal_last_usn` = max(r.usn) over every surviving record (fd:11371): on a restart journal
#     that is the EARLIER sequence's highest USN. Decided (N400's row; LB8 keeps the key's name in wave B): the current
#     numbering's last USN. Values from test_1132_red_g3's own carve (`_n219_seq_premise`): win11refs8g 173,744 (not
#     487,944), labG_2 15,984 (not 4,439,864).
# (b) `usn` parses $J with `alloc=len(j_data)` (fd:9465), `timeline` (fd:9800) and `timestomp` (fd:11361) without it, so
#     the "USN is not its journal offset" finding exits 2 in `usn` only (0 corpus journals have such a record: a plant).

N400_IMAGES = [G3.R8G, "step7/labG_2.raw"]


# RED 1.13.2 N400: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("rel", N400_IMAGES, ids=["image-win11refs8g", "image-labG_2"])
def test_n400_journal_last_usn_is_the_current_sequences_last_usn(rel):
    G3._n219_seq_premise(rel)
    cur_last, old_hi = G3.N219_SEQ[rel][1], G3.N219_SEQ[rel][5]
    rc, out, err = _crun(FOREFST, rel, "timestomp", "--json")
    j = _json(out, "timestomp --json")
    _keep("journal_last_usn" in j, "LB8: journal_last_usn keeps its name in wave B")
    _fx(j["journal_last_usn"] in (cur_last, old_hi), "journal_last_usn %r is neither sequence's end" % j["journal_last_usn"])
    assert j["journal_last_usn"] == cur_last, ("journal_last_usn %d; the current numbering ends at USN %d (the earlier "
                                               "sequence at %d)" % (j["journal_last_usn"], cur_last, old_hi))


def _restart_journal(tmp_path):
    """The current numbering from USN 0 (cluster 0, newer times) and an earlier sequence above it (cluster 4, older
    times), the clusters between written as zeros: the restart shape of win11refs8g / labG_2, in miniature."""
    t_new, t_old = BJ.JID_ONE + 10 ** 10, BJ.JID_ONE + 10 ** 8
    recs, off = [], 0
    for i in range(5):
        b = _usn_rec(off, "cur%d.txt" % i, 0x10 + i, t_new + i)
        recs.append((off, b))
        off += len(b)
    cur_last = recs[-1][0]
    off = 4 * HCS
    for i in range(5):
        b = _usn_rec(off, "old%d.txt" % i, 0x40 + i, t_old + i)
        recs.append((off, b))
        off += len(b)
    jr = _JFile(tmp_path, 6, recs, zeros=(1, 2, 3))
    got = [r[1] for r in G3._carve(jr.data)]
    _fx(got == [o for o, _b in recs], "the $J carries USNs %r" % got)
    return jr, cur_last, recs[-1][0]


# RED 1.13.2 N400: green with wave B part 3's fix (the strict xfail mark removed)
def test_n400_journal_last_usn_unit_restart_journal(monkeypatch, capsys, tmp_path):
    jr, cur_last, old_hi = _restart_journal(tmp_path)
    rc, out, err = _jharness(monkeypatch, capsys, jr, "timestomp", ("--json",), [BJ._entry(1, cur_last, BJ.JID_ONE)])
    j = _json(out, "timestomp --json")
    _keep(re.search(r"(?i)restart", err), "decision 31: the restart is stated" + _ctx(rc, out, err))
    assert jget(j, "journal_last_usn") == cur_last, "journal_last_usn %r; the current numbering ends at USN %d (old %d)" % (
        jget(j, "journal_last_usn"), cur_last, old_hi)


def test_n400_control_journal_last_usn_of_one_sequence_is_its_last_usn(monkeypatch, capsys, tmp_path):
    """Not a RED. One numbering sequence: journal_last_usn is its last record's USN, today and after the fix."""
    recs, end = _seq_journal(tmp_path)
    jr = _JFile(tmp_path, 1, recs)
    rc, out, err = _jharness(monkeypatch, capsys, jr, "timestomp", ("--json",), [BJ._entry(1, recs[-1][0], BJ.JID_ONE)])
    assert jget(_json(out, "timestomp --json"), "journal_last_usn") == recs[-1][0], out[-1500:]


def _offset_journal(tmp_path):
    """Six records; the fourth carries a USN 8 bytes above its own offset (a record whose USN is not its offset)."""
    t0 = BJ.JID_ONE + 10 ** 8
    recs, off = [], 0
    for i in range(6):
        b = _usn_rec(off + (8 if i == 3 else 0), "f%d.txt" % i, 0x10 + i, t0 + i)
        recs.append((off, b))
        off += len(b)
    jr = _JFile(tmp_path, 1, recs)
    _fx(len(F.parse_usn_records(jr.data)) == 6, "the plant does not parse as six records")
    return jr, recs


_OFFSET_SAID = re.compile(r"(?i)\bUSN\b[^.]{0,80}\bnot\b[^.]{0,40}\boffset\b")


# RED 1.13.2 N400: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd,args", [("timeline", ("--csv",)), ("timestomp", ("--csv",)), ("timeline", ())],
                         ids=["timeline-csv", "timestomp-csv", "timeline"])
def test_n400_timeline_and_timestomp_raise_the_usn_offset_finding(monkeypatch, capsys, tmp_path, cmd, args):
    jr, recs = _offset_journal(tmp_path)
    rc, out, err = _jharness(monkeypatch, capsys, jr, cmd, args, [BJ._entry(1, recs[-1][0], BJ.JID_ONE)])
    said = [ln for ln in (out + "\n" + err).splitlines() if _OFFSET_SAID.search(ln)]
    assert said, "%s does not state the record whose USN is not its journal offset" % cmd + _ctx(rc, out, err)
    assert rc == 2, "%s exits %d over that finding (`usn`: 2)" % (cmd, rc)


def test_n400_control_usn_raises_the_usn_offset_finding(monkeypatch, capsys, tmp_path):
    """Not a RED. `usn --stats` parses with the allocation: the finding is stated and exits 2 (the behaviour to share)."""
    jr, recs = _offset_journal(tmp_path)
    rc, out, err = _jharness(monkeypatch, capsys, jr, "usn", ("--stats",), [BJ._entry(1, recs[-1][0], BJ.JID_ONE)])
    assert rc == 2 and [ln for ln in err.splitlines() if _OFFSET_SAID.search(ln)], _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N401 -- an all-zero $J beside files carrying an EARLIER journal id
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `_usn_empty_lines` counts a pointer with any id as pointing "into this journal" (fd:6160) and the empty branch returns
# before `_usn_instance_lines` (fd:6183-6190), so decision 31's re-creation statement and S2's naming of the earlier
# instance are not printed. Decided (N401's row, decision 31 and S2): they are; exit 2 either way (kept). Matchers:
# test_1132_red_g3's `_RESTART`, test_1132_red_b2_journal's `_names_other_instance`.

_INTO_THIS = re.compile(r"(?i)\bpoint\w*\s+into\s+this\s+journal\b")


def _n401_journal(tmp_path):
    jr = BJ._Journal(tmp_path, 8, zeros=range(8))
    return jr


# RED 1.13.2 N401: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd,args", BJ.HARNESS_CMDS, ids=BJ.HARNESS_IDS)
def test_n401_an_earlier_ids_pointer_beside_an_empty_journal_is_a_recreation(monkeypatch, capsys, tmp_path, cmd, args):
    jr = _n401_journal(tmp_path)
    ents = [BJ._entry(1, 20000, JID_EARLIER, name="earlier_instance.txt", ts=JID_EARLIER + 10 ** 7)]
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, cmd, args, ents)
    prose = (out + "\n" + err).splitlines()
    ctx = BJ._hctx(cmd, args, rc, out, err)
    _keep(rc == 2, "exit 2 either way (N401's row)" + ctx)
    assert not [ln for ln in prose if _INTO_THIS.search(ln)], "the earlier id's pointer is called 'into this journal'" + ctx
    assert BJ._names_other_instance(prose, JID_EARLIER), "the earlier journal id is not named as another instance" + ctx
    assert [ln for ln in prose if G3._RESTART.search(ln)], "no re-creation statement (decision 31)" + ctx


@pytest.mark.parametrize("cmd,args", BJ.HARNESS_CMDS, ids=BJ.HARNESS_IDS)
def test_n401_control_a_current_ids_pointer_points_into_this_journal(monkeypatch, capsys, tmp_path, cmd, args):
    """Not a RED. The same $J with a file carrying the CURRENT id and a pointer: 'point into this journal', exit 2."""
    jr = _n401_journal(tmp_path)
    ents = [BJ._entry(1, 20000, BJ.JID_ONE, name="points_into.txt", ts=BJ.JID_ONE + 10 ** 7)]
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, cmd, args, ents)
    assert rc == 2 and [ln for ln in (out + err).splitlines() if _INTO_THIS.search(ln)], \
        BJ._hctx(cmd, args, rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N403 -- a journal finding is not worded as skipped work
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Journal data findings go through `_skip_note`, whose template says "WARNING: USN journal skipped <finding>: ValueError:
# ..." and whose at-exit summary says "N unit(s) of work were skipped and are NOT reflected in the output above"
# (fd:2848, :2869). Sites: N131's finding branch (an empty $J files point into, fd:6187), A10's zero runs inside the
# written span (fd:5527), the USN-offset check (fd:5494). Decided (N403's row): a finding is worded as a finding; the
# exit code (2) is right and kept.

def _n403_shape(tmp_path, shape):
    if shape == "empty-journal-pointed-into":
        jr = BJ._Journal(tmp_path, 8, zeros=range(8))
        return jr, ("usn", ("--info",)), [BJ._entry(1, 20000, BJ.JID_ONE)], r"holds no record"
    if shape == "zeros-inside-the-written-span":
        jr = BJ._Journal(tmp_path, 19, records={0, 18}, zeros=set(range(1, 18)))
        return jr, ("usn", ("--stats",)), [BJ._entry(1, jr.usn_max, BJ.JID_ONE)], r"(?i)written span|zero byte"
    jr, recs = _offset_journal(tmp_path)
    return jr, ("usn", ("--stats",)), [BJ._entry(1, recs[-1][0], BJ.JID_ONE)], r"(?i)\boffset\b"


# RED 1.13.2 N403: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("shape", ["empty-journal-pointed-into", "zeros-inside-the-written-span", "usn-not-its-offset"])
def test_n403_a_journal_finding_is_not_worded_as_skipped_work(monkeypatch, capsys, tmp_path, shape):
    jr, (cmd, args), ents, what = _n403_shape(tmp_path, shape)
    rc, out, err = _jharness(monkeypatch, capsys, jr, cmd, args, ents)
    ctx = _ctx(rc, out, err)
    _keep(rc == 2 and re.search(what, err), "the finding is stated and exits 2 (kept)" + ctx)
    monkeypatch.setattr(F, "_SKIP_SUMMARY_DONE", [])
    capsys.readouterr()
    F._skip_summary()
    tail = capsys.readouterr().err
    stmt = [ln for ln in err.splitlines() if re.search(what, ln)]
    assert not [ln for ln in stmt if re.search(r"(?i)\bskipped\b", ln)], "the finding is worded as skipped work: %r" % (
        stmt[:1],) + ctx
    assert not re.search(r"(?i)unit\(s\) of work were skipped", tail), "the exit summary counts it as skipped work: %r" % tail


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N404 -- a $J that is entirely an image hole: the note says so
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# The settled N131 note ("the N-byte $J stream holds no records and no file points into it") has no hole clause, and
# `all_zero_len` counts hole bytes as zeros, against N148's rule (C8 = B: a hole is stated, its cause left open). Exit 0
# is right (kept). The rule does not depend on the copy; the image node's premise (the $J a hole on THIS copy) rests on
# the key's hole layout: RE-CHECK on the normal disks (GROUP3_CENSUS saw it a hole on the originals too).

def _hole_clause(lines):
    return [ln for ln in lines if re.search(r"\$J", ln) and MC._HOLE.search(ln) and MC._HOLE_CAUSE.search(ln)]


# RED 1.13.2 N404: green with wave B part 3's fix (the strict xfail mark removed)
@pytest.mark.parametrize("cmd,args", BJ.HARNESS_CMDS, ids=BJ.HARNESS_IDS)
def test_n404_an_all_hole_journal_is_stated_as_a_hole(monkeypatch, capsys, tmp_path, cmd, args):
    jr = BJ._Journal(tmp_path, 8)                        # every $J cluster a hole of the file
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, cmd, args, BJ._n131_entries())
    ctx = BJ._hctx(cmd, args, rc, out, err)
    _keep(rc == 0, "exit 0 is right (N404's row)" + ctx)
    assert _hole_clause((out + "\n" + err).splitlines()), "no line says the $J is stored as a hole (cause open)" + ctx


@pytest.mark.parametrize("cmd,args", BJ.HARNESS_CMDS, ids=BJ.HARNESS_IDS)
def test_n404_control_an_all_zero_written_journal_claims_no_hole(monkeypatch, capsys, tmp_path, cmd, args):
    """Not a RED. The same $J written as real zeros: no hole is claimed, exit 0 (N131's note, as settled)."""
    jr = BJ._Journal(tmp_path, 8, zeros=range(8))
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, cmd, args, BJ._n131_entries())
    assert rc == 0 and not [ln for ln in (out + err).splitlines() if MC._HOLE.search(ln)], \
        BJ._hctx(cmd, args, rc, out, err)


EMPTY_J = "step7/win11afterblindaudit_empty.raw"


# RED 1.13.2 N404: green with wave B part 3's fix (the strict xfail mark removed)
def test_n404_usn_info_states_the_hole_on_image_win11afterblindaudit_empty():
    rc, out, err = _crun(FOREFST, EMPTY_J, "usn", "--info")
    ext = [(int(m.group(1), 16), int(m.group(2))) for m in
           re.finditer(r"PLCN=(0x[0-9a-f]+)\s+vcn=(?:0x[0-9a-f]+|\d+)\s+len=(\d+)", out)]   # K9: a VCN in hex (1.14.0)
    _fx(ext, "usn --info lists no $J extent" + _ctx(rc, out, err))
    p = MC.corpus(EMPTY_J)
    ps, cs = MC._refs_ps(p), MC._cluster_size(p, MC._refs_ps(p))
    for plcn, n in ext:                                  # premise: the whole $J is a hole of THIS copy (key layout)
        _fx(not MC.data_ranges(p, ps + plcn * cs, ps + (plcn + n) * cs),
            "the $J at PLCN 0x%x is not a hole of this copy (RE-CHECK on the normal disks)" % plcn)
    _keep(rc == 0, "exit 0 is right" + _ctx(rc, out, err))
    assert _hole_clause((out + "\n" + err).splitlines()), "no line says the $J is stored as a hole" + _ctx(rc, out, err)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N405 -- the G3b timeline-note node leaves forefst's run registers as it found them
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

_N405_REGS = ("_SKIP_EXPECTED", "_SKIP_NOTES", "_SKIP_FINDING", "_FINDINGS")


def _copy(o):
    return dict(o) if isinstance(o, dict) else list(o)


# RED 1.13.2 N405: green with wave B part 3's fix (the strict xfail mark removed)
def test_n405_the_g3b_timeline_note_node_leaves_the_run_registers_unchanged(monkeypatch, capsys, tmp_path):
    node = getattr(G3, "test_g3b_timeline_note_claims_nothing_about_pointers_it_did_not_read", None)
    _fx(node is not None, "the node is gone or renamed")
    regs = {n: getattr(F, n) for n in _N405_REGS}
    snap = {n: _copy(o) for n, o in regs.items()}
    try:
        with monkeypatch.context() as mp:
            node(mp, capsys, tmp_path)
    except AssertionError as e:
        raise RedFixtureError("the node itself failed: %s" % e)
    finally:
        changed = {n: (snap[n], _copy(o)) for n, o in regs.items() if _copy(o) != snap[n]}
        for n, o in regs.items():                        # restore: this check must not add the noise it detects
            o.clear()
            o.update(snap[n]) if isinstance(o, dict) else o.extend(snap[n])
    assert not changed, "the node changed forefst's real run registers: %r" % changed


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N157 -- no statement says ReFS leaves Source info (0x3C) at 0 / does not populate it
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `usn --info` says "ReFS leaves Source info (0x3C) and Security ID (0x40) = 0 in every USN record (not populated by the
# filesystem) ... these three fields ... carry no per-record signal" (fd:9614-9617); the CSV comments (fd:9628-9636) and
# the `usn` help (fd:18013) say the same. False for Source info: RefsMarkHandle -> CCB+0x54 -> RefsCommonWrite ->
# RefsWriteUsnJournalChanges stores it at +0x3C (three builds, N157's row). Security ID 0 is right. Decided: the false
# statement goes; the census adds: the reworded sentence must not claim a non-zero value was observed (0 of 38 corpus
# journals carry one). The wording of the replacement is not settled: the nodes assert the property.

_SRC_FALSE = [r"(?i)Source info \(0x3C\)[^.]*= ?0 in every USN record", r"(?i)not populated by the filesystem",
              r"(?i)they carry no per-record signal", r"(?i)does not populate SourceInfo", r"(?i)all structurally 0 on ReFS",
              r"(?i)security_id/source_info/parent_idx are 0"]
_SRC_OBSERVED = re.compile(r"(?i)source ?info[^.]{0,80}\b(?:observed|found|seen)\b[^.]{0,40}\bnon-?zero\b|"
                           r"\bnon-?zero\b[^.]{0,40}source ?info[^.]{0,40}\b(?:observed|found|seen)\b")


# RED 1.13.2 N157: green with wave B part 3's fix (the strict xfail mark removed)
def test_n157_usn_info_does_not_say_source_info_is_never_populated(monkeypatch, capsys, tmp_path):
    jr = BJ._Journal(tmp_path, 2, records={0})
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, "usn", ("--info",), [BJ._entry(1, jr.usn_max, BJ.JID_ONE)])
    flat = _flat(out)
    _keep(re.search(r"0x3c\s+4\s+Source info", out), "the record layout still lists Source info at 0x3c"   # K15 (1.14.0)
          + _ctx(rc, out, err))
    bad = [p for p in _SRC_FALSE if re.search(p, flat)]
    assert not bad, "usn --info still says: %r" % bad
    assert not _SRC_OBSERVED.search(flat), "a non-zero Source info is claimed as observed (0 of 38 journals carry one)"


# RED 1.13.2 N157: green with wave B part 3's fix (the strict xfail mark removed)
def test_n157_no_comment_or_help_says_source_info_is_never_populated():
    src = open(os.path.join(REPO, "forefst.py"), encoding="utf-8").read().splitlines()
    hits = ["fd:%d: %s" % (i, ln.strip()[:120]) for i, ln in enumerate(src, 1)
            if any(re.search(p, ln) for p in _SRC_FALSE)]
    assert not hits, "\n".join(hits)


def test_n157_control_the_csv_keeps_the_source_info_column(monkeypatch, capsys, tmp_path):
    """Not a RED. The record field and its column stay: `usn --csv` still carries `source_info` (its names, with
    SourceInfoHex beside it since the E2 close)."""
    jr = BJ._Journal(tmp_path, 2, records={0})
    rc, out, err, calls = BJ._harness(monkeypatch, capsys, jr, "usn", ("--csv",), [BJ._entry(1, jr.usn_max, BJ.JID_ONE)])
    hdr = next(csv.reader([out.splitlines()[0]])) if out.strip() else []
    assert rc == 0 and [h for h in hdr if h.lower().replace("_", "") == "sourceinfo"], hdr


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N255 -- a nameless USN record is never filed under its home directory's path
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `timeline` writes `getattr(r, 'filename', '') or oid_paths.get(r.file_oid, '')` (fd:9806): a record with no name gets
# the path of its home OID -- the containing DIRECTORY for a file. Census: 2,281 such records on 16 journals (all
# FILE_DELETE + CLOSE, 80 bytes, name length 0, parent 0x0). Decided (N255's row): the record's own (empty) name, or
# `<no name> 0x77d:0x2` -- never the home path. Both forms are accepted (a property): the name is empty or names the
# record's FileRef.

def _timeline_usn_rows(out):
    rows = []
    for ln in out.splitlines():
        if not ln or ln.startswith("Timestamp,"):                 # acceptance 1.14.0 (K21)
            continue
        try:
            f = next(csv.reader([ln]))
        except (csv.Error, StopIteration) as e:          # LB45: `timeline --csv` prints no such line; never skipped
            raise RedFixtureError("timeline --csv printed a line the csv module cannot read (%r): %r" % (e, ln[:200]))
        if len(f) == 7 and f[2] == "USN":                        # Q-C: (time, source, Source, OID, Name, PathToday, Event)
            rows.append([f[0], f[2], f[3], f[4], f[6]])          # the reader's (time, source, oid, name, event)

    return rows


def _nameless_journal(tmp_path):
    t0 = BJ.JID_ONE + 10 ** 8
    named = _usn_rec(0, "named.txt", 0x2, t0)
    nameless = _usn_rec(len(named), "", 0x3, t0 + 1, reason=0x80000200, parent=0)
    jr = _JFile(tmp_path, 1, [(0, named), (len(named), nameless)])
    got = G3._carve(jr.data)
    _fx([(r[1], r[5]) for r in got] == [(0, "named.txt"), (len(named), "")], "the $J carries %r" % got)
    return jr


# RED 1.13.2 N255: green with wave B part 3's fix (the strict xfail mark removed)
def test_n255_a_nameless_record_is_not_filed_under_its_home_path(monkeypatch, capsys, tmp_path):
    jr = _nameless_journal(tmp_path)
    rc, out, err = _jharness(monkeypatch, capsys, jr, "timeline", ("--csv",), [BJ._entry(1, 0x60, BJ.JID_ONE)],
                             paths={0x706: "labJ"})
    rows = [r for r in _timeline_usn_rows(out) if r[4] == "FILE_DELETE|CLOSE"]
    _fx(len(rows) == 1, "timeline --csv USN FILE_DELETE rows %r" % rows + _ctx(rc, out, err))
    nm = rows[0][3]
    assert nm != "labJ" and (nm == "" or re.search(r"(?i)0x706:0x3\b", nm)), (
        "the nameless record is named %r; its own name is empty (or <no name> 0x706:0x3), never the home path" % nm)


def test_n255_control_a_named_record_keeps_its_own_name(monkeypatch, capsys, tmp_path):
    """Not a RED. The named record of the same journal carries its own name."""
    jr = _nameless_journal(tmp_path)
    rc, out, err = _jharness(monkeypatch, capsys, jr, "timeline", ("--csv",), [BJ._entry(1, 0x60, BJ.JID_ONE)],
                             paths={0x706: "labJ"})
    rows = [r for r in _timeline_usn_rows(out) if r[4] == "FILE_CREATE"]
    assert len(rows) == 1 and re.search(r"(?:^|/)named\.txt$", rows[0][3]), rows


NAMELESS_USN, NAMELESS_REF = 487712, (0x77D, 0x2)    # win11refstestmftecmd (running log N255; census 2.6)


def _mft_nameless():
    """The nameless record of win11refstestmftecmd, read here (test_1132_red_g3's carve of the journal's first extent)."""
    G3._mft_premise()
    with open(MC.corpus(G3.MFT), "rb") as fh:
        fh.seek(G3.MFT_J0)
        recs = G3._carve(fh.read(452 * CS))
    hit = [r for r in recs if r[1] == NAMELESS_USN]
    _fx(len(hit) == 1 and hit[0][5] == "" and hit[0][4] == NAMELESS_REF and hit[0][3] == 0x80000200,
        "win11refstestmftecmd: USN %d is not the nameless FILE_DELETE | CLOSE of 0x77d:0x2: %r" % (NAMELESS_USN, hit))
    return sum(1 for r in recs if r[5] == "")


# RED 1.13.2 N255: green with wave B part 3's fix (the strict xfail mark removed)
def test_n255_a_nameless_record_is_not_filed_under_its_home_path_on_image_win11refstestmftecmd():
    _mft_nameless()
    rc, out, err = _crun(FOREFST, G3.MFT, "timeline", "--csv")
    rows = _timeline_usn_rows(out)
    _fx(rows, "timeline --csv printed no USN row" + _ctx(rc, out, err))
    pathy = [r for r in rows if "/" in r[3]]
    assert not pathy, "%d USN row(s) carry a path (a record's own name never holds '/'): %r" % (len(pathy), pathy[:2])
    mine = [r for r in rows if r[2] == "0x77d" and r[4] == "FILE_DELETE|CLOSE"
            and (r[3] == "" or re.search(r"(?i)0x77d:0x2\b", r[3]))]
    assert mine, "no USN row names the nameless record by an empty name or its FileRef 0x77d:0x2"


def test_n255_control_usn_lists_the_nameless_record_with_its_empty_name_on_image_win11refstestmftecmd():
    """Not a RED. `usn --csv` lists USN 487712 with an empty name, FileRef 0x77d:0x2 and parent 0x0 (the oracle the
    timeline row is compared with; the record's bytes are read in the RED's premise)."""
    _mft_nameless()
    rc, out, err = _crun(FOREFST, G3.MFT, "usn", "--csv")
    rows = [r for r in csv.DictReader(io.StringIO(out)) if r.get("USN") == str(NAMELESS_USN)]   # acceptance 1.14.0
    assert len(rows) == 1 and rows[0]["FileName"] == "" and rows[0]["ObjectRef"] == "0x77d:0x2" \
        and rows[0]["ParentOID"] == "0x0", rows


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N254 -- closed on the current tree (LB7's check; passing)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N254: on a volume whose journal tail is missing, `timeline --csv/--json/--jsonl` to stdout began with the three
# 'Journal tail' lines. G3b F1 routed every statement to stderr when stdout carries the export. Checked here on the
# row's own volume, step7/labFafterreboot: stdout is the export alone from its first line, the statement is on stderr.

N254 = "step7/labFafterreboot.raw"


@pytest.mark.parametrize("args", G3.F1_FORMS, ids=G3.F1_FORM_IDS)
def test_n254_closed_timeline_export_to_stdout_is_the_export_alone_on_image_labFafterreboot(args):
    G3._f1_premise(N254)
    r = G3._f1_exec(N254, args)
    ctx = G3._f1_ctx(N254, args, r)
    assert r["rc"] == 2, "the journal findings keep exit 2" + ctx
    if "--csv" in args:
        assert r["first"] == G3.TIMELINE_CSV_HEADER.split(","), ctx
    else:
        assert r["error"] is None, ctx
    assert not r["nbad"] and r["n"] > 0, ctx
    assert G3._F1_TAIL_STMT.search(r["err"]), "A10's 'Journal tail:' statement is not on stderr" + ctx


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N259 (LB17) -- the bundle's `mlog_log_index.csv` names the block index for what it is; old bundles still read
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `export metadata` writes `mlog_log_index.csv` with the column `block_lcn` (fd:17257), a 4 KiB MLog block INDEX (plcn x
# blocks-per-cluster + block, fd:4611), read back by `verify-bundle` and the bundle reader (fd:11803-11877, :12061-12106).
# Decided (LB17, decision 33): renamed in place for the block index; the reader keeps reading old bundles' `block_lcn`.
# LB22: the new name is `BlockIndex`, the same name as N259's JSON key (K21). The RED asserts it -- no `block_lcn`, a
# `BlockIndex` column (critic D2 a), whose values locate each exported 4 KiB block.

BUNDLE_IMG = "step1/win11refsmini.raw"


def _export_bundle(tmp_path, name):
    d = str(tmp_path / name)
    rc, out, err = G2C._run_split(FOREFST, MC.corpus(BUNDLE_IMG), "export", "metadata", d, cwd=REPO)
    _fx(os.path.isfile(os.path.join(d, "mlog_log_index.csv")), "no mlog_log_index.csv" + _ctx(rc, out, err))
    return d


def _bundle_reads(d):
    """(verify-bundle rc, the bundle reader's `mlog --stats` Total records)."""
    rc, out, err = G2C._run_split(FOREFST, d, "verify-bundle", cwd=os.path.dirname(d))
    rc2, out2, err2 = G2C._run_split(FOREFST, d, "mlog", "--stats", cwd=os.path.dirname(d))
    m = re.search(r"(?:Total|Redo) records:\s+(\d+)", out2)      # C1 C-5: N437's label too
    return rc, (int(m.group(1)) if m else None), (out + err)[-1500:]


def _image_records():
    rc, out, err = _crun(FOREFST, BUNDLE_IMG, "mlog", "--stats")
    m = re.search(r"(?:Total|Redo) records:\s+(\d+)", out)      # C1 C-5: N437's label too
    _fx(rc == 0 and m, "mlog --stats on the image" + _ctx(rc, out, err))
    return int(m.group(1))


def test_n259_lb17_the_bundle_index_names_the_block_index(tmp_path):
    d = _export_bundle(tmp_path, "bundle")
    with open(os.path.join(d, "mlog_log_index.csv"), encoding="utf-8") as fh:
        hdr = fh.readline().rstrip("\n").split(",")
        rows = [ln.rstrip("\n").split(",") for ln in fh if ln.strip()]
    _fx(rows, "mlog_log_index.csv holds no row")
    assert "block_lcn" not in hdr, "mlog_log_index.csv header %r: block_lcn holds a 4 KiB block index" % hdr
    col = [i for i, h in enumerate(hdr) if h == "BlockIndex"]
    assert col, "mlog_log_index.csv header %r has no `BlockIndex` column (LB22)" % hdr
    # LB32: the column's values keep the form they have today, `0x%x` (fd:17258) -- the form `mlog --json` BlockIndex
    # takes too (one form for one information)
    odd = [r[col[0]] for r in rows
           if not re.fullmatch(r"0x[0-9a-f]+", r[col[0]]) or r[col[0]] != "0x%x" % int(r[col[0]], 16)]
    _keep(not odd, "BlockIndex values not in the form 0x%%x (LB32): %r" % odd[:3])
    # the values locate each exported block: image bytes at the block == the blob slice at its byte offset
    p = MC.corpus(BUNDLE_IMG)
    ps = MC._refs_ps(p)
    cs = MC._cluster_size(p, ps)
    bpc = max(1, cs // 0x1000)
    off_col = [i for i, h in enumerate(hdr) if re.search(r"(?i)byte.?offset", h)]
    _keep(off_col, "the byte-offset column is still there: %r" % hdr)
    with open(os.path.join(d, "mlog_log_pages.bin"), "rb") as blob, open(p, "rb") as img:
        for r in rows[:16]:
            k, o = int(r[col[0]], 0), int(r[off_col[0]])
            img.seek(ps + (k // bpc) * cs + (k % bpc) * 0x1000)
            blob.seek(o)
            _keep(img.read(0x1000) == blob.read(0x1000), "row %r does not locate its block" % (r,))
    rc, n, tail = _bundle_reads(d)
    _keep(rc == 0 and n == _image_records(), "the bundle reads back (verify-bundle %d, %r records):\n%s" % (rc, n, tail))
    shutil.rmtree(d, ignore_errors=True)


def _as_old_bundle(d):
    """Rewrite the index header to the pre-1.14 `block_lcn` (a no-op today) and re-seal the files it touches."""
    ip = os.path.join(d, "mlog_log_index.csv")
    with open(ip, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    hdr = lines[0].split(",")
    if "block_lcn" in hdr:
        return False
    col = [i for i, h in enumerate(hdr) if re.search(r"(?i)block", h)]
    _fx(len(col) == 1, "cannot tell the block column of %r" % hdr)
    hdr[col[0]] = "block_lcn"
    data = ("\n".join([",".join(hdr)] + lines[1:])).encode("utf-8")
    with open(ip, "wb") as fh:
        fh.write(data)
    mp = os.path.join(d, "manifest.json")
    with open(mp, encoding="utf-8") as fh:
        man = json.load(fh)
    for a in man.get("Artifacts", []):                     # acceptance 1.14.0 (K21): the written names
        if a.get("File") == "mlog_log_index.csv":
            a["SHA256"], a["Bytes"] = hashlib.sha256(data).hexdigest(), len(data)
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2)
    sp = os.path.join(d, "sha256sums.txt")
    with open(sp, encoding="utf-8") as fh:
        sums = [ln for ln in fh.read().split("\n") if ln.strip()]
    out = []
    for ln in sums:
        _h, _s, name = ln.partition("  ")
        if name in ("mlog_log_index.csv", "manifest.json"):
            with open(os.path.join(d, name), "rb") as fh:
                ln = "%s  %s" % (hashlib.sha256(fh.read()).hexdigest(), name)
        out.append(ln)
    with open(sp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return True


def test_n259_lb17_control_an_old_bundle_with_block_lcn_still_reads(tmp_path):
    """Not a RED. A bundle whose mlog_log_index.csv says `block_lcn` (every bundle written before the fix; made here by
    rewriting the header and re-sealing once the exporter writes the new name) passes verify-bundle and its MLog reads
    back with the image's record count -- today and after the fix (LB17: old bundles still read)."""
    d = _export_bundle(tmp_path, "old_bundle")
    _as_old_bundle(d)
    rc, n, tail = _bundle_reads(d)
    assert rc == 0 and n == _image_records(), "old-form bundle: verify-bundle %d, %r records\n%s" % (rc, n, tail)
    shutil.rmtree(d, ignore_errors=True)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N425 (LB64; wave B part 3d, written first, before the fix) -- bootstrap's superblock-fallback register, per bootstrap
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# `parse_supb` fills the module register `_SUPB_FELL_BACK` when the primary superblock is not usable and a backup is
# read; the readers of "the superblock copy THIS view is read from" (`_scan_backup_copies`' `used`, `volume_format_magic`,
# `summary`'s GUID and SUPB hash, refsanalysis `supb` / `chkp` / `summary`) take its `used_lcn`. Nothing cleared it, so
# in one process over several volumes every volume after one that fell back was read as fallen back too: measured
# before the fix (fixes/waveB_fix_evidence/part3d/pre_noclear.jsonl against pre_clear.jsonl), 56 of the 120 corpus
# volumes read after win11refsmini_aftercorruption in one process name its backup LCN 0x7bffd as the copy in use (the
# volume signature differs on 50 of them). The CLI reads one volume per process. LB64: cleared per bootstrap. Kept
# (controls): the run's exit code still says a volume of this run was read from a backup superblock (exit 2), and the
# volume read last keeps its own fallback. Two synthetic volumes (test_1132_red_a_bootstrap's), one process.

def _n425_fresh(monkeypatch):
    """Every run register forefst's exit rule reads (its own code), the journal harness's list and the bootstrap's
    at-exit list, fresh and restored afterwards (monkeypatch), so the real bootstraps here leave no trace."""
    names = set(F.rc_escalate.__code__.co_names) | set(BJ._REGISTERS) | {"_ALL_TRS", "_OT_MAX_LSN"}
    for name in sorted(names):
        cur = vars(F).get(name)
        if isinstance(cur, (list, dict, set)):
            monkeypatch.setattr(F, name, type(cur)())


# `_st_s1` (C2 ST-S1's RED mark for the nodes B15's decided output changed) removed in step C2, area supb


# _ST_S1_N425 (C2 ST-S1 a2): the mark the four N425 nodes carried, removed in step C2, area supb


def _n425_vols(tmp_path):
    """(A, B): A's primary superblock fails its self-checksum (one GUID byte flipped), so A is read from end-2 (C2
    ST-S1 (a2): Q3, both backups verify with equal +0x68; it was end-3, the tool's first backup before B15); B is
    undamaged."""
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    va, vb = AB._synthetic_vol(a), AB._synthetic_vol(b)
    _fx(AB.damage_supb(va, "primary") == AB.SYN.supb, "A's primary superblock was not damaged")
    return va, vb


def _n425_boot(v):
    """bootstrap `v` in this process; (the register after it, the superblock copies `_scan_backup_copies` marks used)."""
    fh, ps, cs, _tr, _roots, _om, _vj, _vn, chkp = F.bootstrap(v.path, v.geo.ps)
    try:
        used = [s["lcn"] for s in F._scan_backup_copies(fh, ps, cs, chkp).get("supb", []) if s.get("used")]
    finally:
        fh.close()
    return dict(F._SUPB_FELL_BACK), used


# RED 1.13.2 B15 (C2 ST-S1 a2): A's primary fails and both backups verify with equal +0x68: A is read from end-2
# (Q3); the tool reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_n425_a_volume_read_after_one_that_fell_back_is_read_from_its_own_superblock(monkeypatch, tmp_path):
    _n425_fresh(monkeypatch)
    va, vb = _n425_vols(tmp_path)
    reg_a, used_a = _n425_boot(va)
    # C2 ST-S1 (a2): end-2 (was end-3); an assert, no longer a fixture check: the value B15 changes
    assert reg_a.get("used_lcn") == AB.SYN.backups[1] and used_a == [AB.SYN.backups[1]], \
        "A is not read from end-2: register %r, used %r" % (reg_a, used_a)
    reg_b, used_b = _n425_boot(vb)
    assert not reg_b.get("used_lcn") and used_b == [AB.SYN.supb], "B's primary superblock verifies, so B is read from " \
        "it (LCN 0x%x); after A in the same process the register still says %r and B's copy in use is %s (LB64: " \
        "cleared per bootstrap)" % (AB.SYN.supb, reg_b, ["0x%x" % x for x in used_b])


# RED 1.13.2 B15 (C2 ST-S1 a2): A's primary fails and both backups verify with equal +0x68: A is read from end-2
# (Q3); the tool reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_n425_control_the_run_still_exits_2_for_the_earlier_volumes_fallback(monkeypatch, tmp_path):
    """A then B in one run: a volume of this run was read from a backup superblock, so the run's exit stays 2 (decision
    27.2, as in one process today) and the escalation texts still name A's backup LCN (end-2: C2 ST-S1 (a2); a RED
    until B15 lands, the exit kept)."""
    _n425_fresh(monkeypatch)
    va, vb = _n425_vols(tmp_path)
    _n425_boot(va)
    _n425_boot(vb)
    texts = F._escalation_texts()
    _keep(F.rc_escalate(0) == 2, "the run's exit after A then B: rc %r" % F.rc_escalate(0))
    # C2 ST-S1 (a2): end-2 (was end-3), split from the _keep
    assert [t for t in texts if AB._lcn_re(AB.SYN.backups[1]).search(t)], \
        "the texts after A then B name A's end-2: %r" % texts


# RED 1.13.2 B15 (C2 ST-S1 a2): A's primary fails and both backups verify with equal +0x68: A is read from end-2
# (Q3); the tool reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_n425_control_the_volume_read_last_keeps_its_own_fallback(monkeypatch, tmp_path):
    """B then A: A, read last, is read from its backup -- the register and the copy in use say so (end-2: C2 ST-S1 (a2);
    a RED until B15 lands, the exit kept)."""
    _n425_fresh(monkeypatch)
    va, vb = _n425_vols(tmp_path)
    _n425_boot(vb)
    reg_a, used_a = _n425_boot(va)
    _keep(F.rc_escalate(0) == 2, "A after B: rc %r" % F.rc_escalate(0))
    # C2 ST-S1 (a2): end-2 (was end-3), split from the _keep
    assert reg_a.get("used_lcn") == AB.SYN.backups[1] and used_a == [AB.SYN.backups[1]], \
        "A after B: register %r, used %r" % (reg_a, used_a)


# RED 1.13.2 B15 (C2 ST-S1 a2): A's primary fails and both backups verify with equal +0x68: A is read from end-2
# (Q3); the tool reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_n425_control_a_volume_read_twice_names_its_fallback_once(monkeypatch, tmp_path):
    """A read twice in one process (a command that bootstraps its volume again): still read from its backup, and the
    escalation texts name that fallback once (end-2: C2 ST-S1 (a2); a RED until B15 lands)."""
    _n425_fresh(monkeypatch)
    va, _vb = _n425_vols(tmp_path)
    _n425_boot(va)
    reg, used = _n425_boot(va)
    named = [t for t in F._escalation_texts() if AB._lcn_re(AB.SYN.backups[1]).search(t)]
    # C2 ST-S1 (a2): end-2 (was end-3; a _keep)
    assert reg.get("used_lcn") == AB.SYN.backups[1] and used == [AB.SYN.backups[1]] and len(named) == 1, \
        "A twice: register %r, used %r, texts %r" % (reg, used, named)


def test_n423_control_the_journal_harness_mlog_is_an_empty_valid_log(monkeypatch, capsys, tmp_path):
    """Not a RED. LB61's sanctioned fixture edit: the journal harnesses' MLog (`BJ._empty_valid_mlog`, which replaced
    the stub `get_mlog_info -> None`) is read by `timeline`'s MLog source and adds what the None stub added before N423:
    no MLog row, no MLog statement, no finding (exit 0 on a sound journal)."""
    jr = BJ._Journal(tmp_path, 4, records=range(2))
    rc, out, err, _calls = BJ._harness(monkeypatch, capsys, jr, "timeline", ("--csv",),
                                       [BJ._entry(1, jr.usn_max, BJ.JID_ONE)])
    rows = [r for r in csv.reader(out.splitlines()[1:]) if len(r) > 1 and r[1] == "MLog"]
    said = [ln for ln in err.splitlines() if re.search(r"\bMLog\b", ln)]
    _keep(rc == 0 and not rows and not said, "timeline over the harness's empty MLog: rc %d, rows %r, MLog lines %r"
          % (rc, rows[:2], said[:2]) + BJ._hctx("timeline", ("--csv",), rc, out, err))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# LB69 (wave B part 4, step GBb; the golden GB's F-2), written first, before the fix
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# A13's sentence for a superblock copy whose payload differs from the copy the volume is read from ended "(each copy's
# own LCN and self-checksum left out; the payloads are equal on every corpus volume, so a difference points to an edited
# or damaged copy)". The golden printed it on two corpus volumes whose copies differ (win11refsmini_aftercorruption and
# _openedwith34), so the clause claimed more than was measured (A38: copies that pass their self-checksum) and
# contradicted the volume it was printed on. LB69: the tool's output does not cite corpus statistics -- the sentence
# ends "...; a difference points to an edited or damaged copy". One definition (`supb_payload_differs_text`) serves
# `summary`, `fastsummary`, `integrity`, refsanalysis `summary` and `supb --verify`; each is run here, on the plant of
# N417 (both copies verify) and of A13 (the differing backup also fails its self-checksum).

_LB69_CMDS = {"summary": (FOREFST, "summary"), "fastsummary": (FOREFST, "fastsummary"),
              "integrity": (FOREFST, "integrity"), "ra-summary": (REFSANALYSIS, "summary"),
              "ra-supb-verify": (REFSANALYSIS, "supb", "--verify")}
_LB69_END = re.compile(r";\s*a difference points to an edited or damaged copy\)")


def _lb69_sentences(text, lcn):
    """The lines that name the superblock copy at `lcn` as differing in its payload (A13's sentence)."""
    return [ln for ln in text.splitlines() if AB._lcn_re(lcn).search(ln) and re.search(r"(?i)differs in its payload", ln)]


@pytest.mark.parametrize("reseal", [True, False], ids=["both-verify", "backup-checksum-failed"])
@pytest.mark.parametrize("cmd", sorted(_LB69_CMDS))
def test_lb69_the_differing_superblock_sentence_cites_no_corpus_statistic(vol, cmd, reseal):
    b = AV._flip_backup_guid(vol, reseal)
    tool, *args = _LB69_CMDS[cmd]
    rc, out, err = _vrun(vol, tool, *args)
    lines = _lb69_sentences(out + "\n" + err, b)
    _fx(lines, "`%s` printed no sentence naming the differing backup at LCN 0x%x" % (" ".join(args), b)
        + _ctx(rc, out, err))
    cited = [ln for ln in lines if re.search(r"(?i)\bcorpus\b", ln)]
    # C2 supb (decision 44's pre-sanctioned form edit, N449 / WAVEC_BRIEF Q5): when both copies verify, the decided
    # sentence draws no editing or damage conclusion, so it does not end with LB69's clause; it is accepted when it
    # carries no such conclusion at all. The A13 branch (the backup fails its self-checksum) keeps LB69's ending.
    unended = [ln for ln in lines if not _LB69_END.search(ln)
               and not (reseal and not re.search(r"(?i)edited or damaged", ln))]
    assert not cited and not unended, "the differing-copy sentence must cite no corpus statistic and end '...; a " \
        "difference points to an edited or damaged copy' (LB69): %r" % (cited or unended)[:2]
