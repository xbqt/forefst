"""The code half, group 1 (MLog), 1.14.0: RUNNING_LOG N554, N533 (+ decision 53), N537 and PLAN section 10.2 A1.

  N554  the driver's names where the tool printed a placeholder: checkpoint flags 0x400 (the rollback-protection
        fields, E158) and 0x2000 (Insider's attestation HMAC, E159); refsanalysis `chkp` +0x88 / +0x8C (an
        offset and a length, E159; its field table, printed by plain `chkp`); redo opcodes 0x25 / 0x2B by their handlers (E160), 0x1A no longer unconfirmed;
        0x2D `RedoDeleteTable` (Insider 29683 logs every table deletion so, E160) with the DELETE class reading the
        handler, not the number 0x0F; the 0x2D note on stderr in every `mlog` mode and in `timeline` (the
        maintainer, 2026-11-12: "ok and yes for the timeline"); the per-build dispatch table it is generated from,
        checked against the tool's opcode tables (N554 (h)); two stale comments.
  N533  `_SmsRedoRecord`+0x20 is the allocator clock (E147), not a table handle: a record without a table path
        applies to PerformRedo's current table -- the previous record's of the same redo block, empty after a
        record whose branch uses no table, after 0x0F / 0x2D (RedoDeleteTable) and after 0x24 (the commit merge;
        KNOWLEDGE_INTAKE A165) -- never to the table of another record that carries the same +0x20 value; a name row
        is a directory's own entry only when its path has one component.
  D53   name rows whose old and new directory sets overlap without being equal: MOVE_OR_RENAME.
  N537  a path-less name row in the directory-row key form (u16 0x30, u16 1/2, the name at +4) keeps its whole name.
  A1    `summary`'s MLog pass runs with `--mlog` or `-v` only (the maintainer's third answers, 2026-11-11); without
        it the section says the log was not read and names both; refsanalysis `summary` the same.

Written RED before the fix (the run is recorded in `analysis/reports/v1.13.2/RC1D/G1_MLOG_NOTES.md`).
Synthetic logs: this file's own record builder over test_1132_red_waveb_mlog's log builder and in-process runner.
"""
import io
import json
import os
import re
import struct
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_waveb_mlog as WB                    # noqa: E402  (log builder, in-process runner)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
RA = os.path.join(REPO, "refsanalysis.py")
MINI = "step1/win11refsmini.raw"


@pytest.fixture(autouse=True)
def _volume_information(monkeypatch):
    """As in test_1132_red_waveb_mlog: the synthetic volumes hold a $VOLUME_INFORMATION (an absent OID 0x500 is a
    finding), created well before every record."""
    monkeypatch.setattr(F, "volume_information_read",
                        lambda *a, **k: ({"vol_create_time": WB.filetime(2020, 1, 1, 0, 0, 0, 0),
                                          "vol_modify_time": 0}, None))


# ═══ builders (this file's own; the tool's code is not used to build a fixture) ═══════════════════════════════

def comp_table(oid, attr=0x130):
    """A table-path component naming the table of object `oid`: u32 0xe030, u32 the table's schema, 12 zero bytes,
    the u64 object id at +20 (28 bytes; the form `parse_mlog_deep_record` and `ObjectIdFromRedoHelper` read)."""
    return struct.pack("<II12xQ", 0xE030, attr, oid)


def comp_row(name):
    """A second path component: the key of the row (in the directory's table) that holds an embedded table."""
    return struct.pack("<II4xHH", 0x130, 0x1E0, 0x30, 1) + name.encode("utf-16-le")


def dir_key(name, kflags=1):
    """A directory-row key: u16 0x30, u16 key flags (1 or 2), the name in UTF-16 at +4."""
    return struct.pack("<HH", 0x30, kflags) + name.encode("utf-16-le")


def rec(opcode, path=(), values=(), flags=3, clock=0):
    """One _SmsRedoRecord: +0 size, +4 opcode, +8 table path length, +0x0C the path descriptors' offset (0x38),
    +0x10 value count, +0x14 the value descriptors' offset (right after the path's), +0x18 / +0x20 the virtual /
    allocator clocks (`clock` both), +0x2C flags; then the components and values, each 8-aligned."""
    tpl, n = len(path), len(values)
    off = 0x38 + 8 * (tpl + n)
    descs, data = [], b""
    for part in list(path) + list(values):
        descs.append((off + len(data), len(part)))
        data += part + b"\0" * ((-len(part)) % 8)
    r = bytearray(off) + data
    struct.pack_into("<IIIIII", r, 0, len(r), opcode, tpl, 0x38, n, 0x38 + 8 * tpl)
    struct.pack_into("<QQ", r, 0x18, clock, clock)
    struct.pack_into("<I", r, 0x2C, flags)
    for i, (o, ln) in enumerate(descs):
        struct.pack_into("<II", r, 0x38 + 8 * i, o, ln)
    return bytes(r)


def log_of(tmp_path, payloads):
    """A synthetic log whose payloads are given as lists of redo blocks (each a list of records)."""
    return WB.build_log(tmp_path / "log.raw", payloads).write()


def run(monkeypatch, log, cmd, *args, vmin=14, paths=None):
    return WB.inproc(monkeypatch, log, cmd, *args, vmin=vmin, paths=paths)


def parse_rows(out):
    """The `[ACTION] label` lines of `mlog --parse`."""
    return [(a, l) for a, l in re.findall(r"^  \[([A-Z_]+)\s*\] (.*)$", out, re.M) if a != "CLASS"]


def csv_rows(out):
    import csv
    return list(csv.DictReader(io.StringIO(out)))


DIR_A, DIR_B, DIR_C = 0x700, 0x800, 0x900


# ═══ N554 (a)-(d), (f): names and comments ════════════════════════════════════════════════════════════════

def test_n554_flag_0x400_names_the_rollback_protection_fields():
    name = F._CHKP_FLAG_BITS[0x400]
    assert "rollback" in name.lower() and "0x9c" in name.lower() and "not read" not in name, name


def test_n554_flag_0x2000_names_the_attestation_hmac():
    name = F._CHKP_FLAG_BITS[0x2000]
    assert "hmac" in name.lower() and "0xa4" in name.lower() and "insider-build flag" not in name, name


def test_n554_opcodes_0x25_0x2b_are_named_by_their_handlers_and_0x2d_is_redo_delete_table():
    ops = F.REDO_OPS_V314
    assert ops[0x25] == "RedoTableSetWeakRefPurge", ops[0x25]
    assert ops[0x2B] == "RedoTableSetStrongRefMergeSingle", ops[0x2B]
    assert ops[0x1A] == "RedoAddCompressionUnitOffsets"
    assert ops.get(0x2D) == "RedoDeleteTable"
    assert 0x2C not in ops                                          # no build has a handler or a writer for it
    assert F._REDO_V314_UNCONFIRMED == frozenset((0x16,))
    assert F.redo_mnemonic(0x2D, ops) == F.redo_mnemonic(0x0F, ops) == "DELETE_TABLE"
    assert 0x2D not in F.REDO_OPS_V34                               # a 3.4 log's 0x2d stays UNKNOWN_0x2d


def test_n554_stale_comments_are_gone():
    src = open(FOREFST, encoding="utf-8").read()
    assert "capacity field 0x8C = 0x20" not in src
    assert "Opcodes 0x00–0x2B are a CONTIGUOUS dispatched range" not in src
    ra = open(RA, encoding="utf-8").read()
    assert "cap 0x20=32" not in ra


# ═══ N554 (e): 0x2D is a table deletion ═══════════════════════════════════════════════════════════════════

def _delete_log(tmp_path, opcode):
    """One payload: the table of DIR_A deleted by `opcode`, then its name row removed from DIR_B."""
    return log_of(tmp_path, [[[rec(0x02, [comp_table(DIR_B)], [dir_key("gone")], flags=1, clock=7),
                               rec(opcode, [comp_table(DIR_A)], [], flags=2, clock=7)]]])


def test_n554_a_0x2d_transaction_is_classed_delete_with_its_handler(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x2D), "mlog", "--parse")
    acts = [a for a, _ in parse_rows(out)]
    assert acts == ["DELETE"], (acts, out[-2000:])
    assert "DELETE_TABLE" in out and "UNKNOWN_0x2d" not in out, out[-2000:]


def test_n554_control_a_0x0f_transaction_is_classed_delete(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x0F), "mlog", "--parse")
    assert [a for a, _ in parse_rows(out)] == ["DELETE"], out[-2000:]


def test_n554_a_0x2d_record_of_a_3_4_log_is_unknown_and_classes_nothing(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x2D), "mlog", "--parse", vmin=4)
    acts = [a for a, _ in parse_rows(out)]
    assert acts and "DELETE" not in acts, (acts, out[-2000:])
    assert "UNKNOWN_0x2d" in out
    assert "redo opcode 0x2d" not in err, "the 0x2d note on a 3.4 volume (its table does not name 0x2d): " + err[-1500:]


# ═══ N554 (j): the 0x2D note ══════════════════════════════════════════════════════════════════════════════

def _note(err):
    m = re.search(r"NOTE: (\d+) records? carr(?:y|ies) redo opcode 0x2d.*?(?=\n\S|\n\s*\n|\Z)", err, re.S)
    return m.group(0) if m else None


@pytest.mark.parametrize("mode", [(), ("--parse",), ("-v",), ("--stats",), ("--csv",), ("--json",), ("--parse", "-v")])
def test_n554_every_mlog_mode_prints_the_0x2d_note_once_on_stderr(monkeypatch, tmp_path, mode):
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x2D), "mlog", *mode)
    n = _note(err)
    assert n is not None, err[-3000:]
    assert err.count("redo opcode 0x2d") == 1, err[-3000:]
    assert "redo opcode 0x2d" not in out, "the note went to stdout"
    flat = " ".join(n.split())
    assert flat.startswith("NOTE: 1 record carries redo opcode 0x2d, RedoDeleteTable"), flat
    # the maintainer, 2026-11-12: the short form
    assert "Of the refs.sys builds read, only Insider 29683 logs a table deletion as 0x2d" in flat, flat
    assert "Windows 11 26100 (the 8 builds read) and Insider 29574 / 29659 log it as 0x0f" in flat, flat
    assert "refuse 0x2d when they replay a log" in flat, flat
    assert "Builds not read (later ones, or ones between 29659 and 29683) may log 0x2d too" in flat, flat
    for line in n.split("\n"):
        assert len(line) <= 100, line


def test_n554_control_no_note_without_a_0x2d_record(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x0F), "mlog", "--parse")
    assert "0x2d" not in err, err[-2000:]


def test_n554_timeline_prints_the_0x2d_note(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x2D), "timeline", "--fast", "--source", "MLOG")
    assert _note(err) is not None and err.count("redo opcode 0x2d") == 1, err[-3000:]


def test_n554_the_note_and_info_row_come_from_the_per_build_table(monkeypatch, tmp_path):
    """N554 (h): a build added to the table changes the note and `mlog --info` without another edit."""
    extra = {"build": "Insider 99999", "table": "3.14", "highest": 0x2D, "differs": {0x16: "no handler",
             0x2C: "no handler"}, "delete_table": 0x2D}
    monkeypatch.setattr(F, "REDO_DISPATCH_BUILDS", tuple(F.REDO_DISPATCH_BUILDS) + (extra,))
    flat = " ".join(F.redo_0x2d_note(3).split())
    assert flat.startswith("NOTE: 3 records carry redo opcode 0x2d"), flat
    assert "only Insider 29683 / 99999 log a table deletion as 0x2d" in flat, flat
    info = " ".join(F._gen_redo_opcode_table().split())
    assert "only Insider 29683 / 99999 log it, for a table deletion" in info, info[-1500:]


def test_n554_mlog_info_says_what_0x16_does_on_each_build():
    """Review F9: 26100 and 29574 call no handler for 0x16 either: they parse its value as a range, unused."""
    info = " ".join(F._gen_redo_opcode_table().split())
    assert "(Windows 11 26100 and Insider 29574 parse its value as a range and use it no further; Insider 29659 / " \
           "29683 call no handler)" in info, info[:3000]


def test_n554_mlog_info_states_the_0x2d_scope():
    info = " ".join(F._gen_redo_opcode_table().split())
    m = re.search(r"0x2d DELETE_TABLE RedoDeleteTable \(([^)]*)\)", info)
    assert m, info[-2500:]
    assert "of the builds read, writers searched for a fixed opcode, only Insider 29683 logs it, for a table deletion" \
        in m.group(1), m.group(1)
    assert "Windows 11 26100 and Insider 29574 / 29659 refuse it" in m.group(1), m.group(1)
    assert "builds not read may log it too" in m.group(1), m.group(1)


# ═══ N554 (h): the per-build dispatch table against the tool's opcode tables ══════════════════════════════

def test_n554_every_value_a_build_dispatches_has_one_meaning_in_its_format_table():
    tables = {"3.14": F.REDO_OPS_V314, "3.4": F.REDO_OPS_V34}
    seen = {}
    assert F.REDO_DISPATCH_BUILDS, "no per-build table"
    for b in F.REDO_DISPATCH_BUILDS:
        ops = tables[b["table"]]
        for v in range(b["highest"] + 1):
            d = b["differs"].get(v)
            if d is None:
                assert v in ops, "%s dispatches 0x%x, which the %s table lacks" % (b["build"], v, b["table"])
                meaning = ops[v]
            else:
                assert d in ("no handler", "refused") or d == ops.get(v), (b["build"], hex(v), d)
                meaning = d
            if meaning in ("no handler", "refused") or meaning.startswith(("ERROR", "NoHandler")):
                continue
            prev = seen.setdefault((b["table"], v), (meaning, b["build"]))
            assert prev[0] == meaning, "0x%x: %s in %s, %s in %s" % (v, prev[0], prev[1], meaning, b["build"])
        dt = b["delete_table"]
        assert ops.get(dt) == "RedoDeleteTable", (b["build"], hex(dt))
    for name, ops in tables.items():                     # no name in a table that no build of its format dispatches
        top = max(b["highest"] for b in F.REDO_DISPATCH_BUILDS if b["table"] == name)
        assert max(ops) <= top, (name, hex(max(ops)), hex(top))


def _canonical_insider_table():
    """{row: {build: cell}} of redo_opcode_complete.md's "Insider 29659 and 29683" table (written from the
    decompilations, not from the tool), or skip when the canonical file is not in this layout."""
    p = os.path.join(os.path.dirname(REPO), "forclaude", "intelligence", "redo_opcode_complete.md")
    if not os.path.isfile(p):
        pytest.skip("the canonical redo table is not in this layout")
    text = open(p, encoding="utf-8").read()
    i = text.index("## Insider 29659 and 29683")
    rows = [l for l in text[i:].split("\n")[1:] if l.startswith("|")][:7]
    hdr = [c.strip() for c in rows[0].strip("|").split("|")]
    out = {}
    for l in rows[2:]:
        c = [x.strip().strip("*`") for x in l.strip("|").split("|")]
        cells = dict(zip(hdr[1:], c[1:]))
        for b in hdr[2:]:                                  # "same" means the cell to the left
            if cells[b] == "same":
                cells[b] = cells[hdr[hdr.index(b) - 1]]
        out[c[0]] = cells
    return out


def test_n554_the_per_build_table_agrees_with_the_canonical_dispatch_reading():
    """Review F11 (a): REDO_DISPATCH_BUILDS checked against an independent source -- the canonical Insider table of
    redo_opcode_complete.md (range dispatched, 0x16, 0x2C, 0x2D, who writes a table deletion)."""
    canon = _canonical_insider_table()
    col = {"Windows 11 26100": "26100.x", "Insider 29574": "Insider 29574", "Insider 29659": "Insider 29659",
           "Insider 29683": "Insider 29683"}
    for b in F.REDO_DISPATCH_BUILDS:
        if b["table"] != "3.14":
            continue
        c = col[b["build"]]
        hi = int(re.search(r"0x00-(0x[0-9A-F]+)", canon["range dispatched"][c]).group(1), 16)
        assert b["highest"] == hi, (b["build"], hex(b["highest"]), hex(hi))
        for op, row in ((0x16, "0x16"), (0x2C, "0x2C")):
            nh = canon[row][c].startswith("no handler")
            assert (b["differs"].get(op) == "no handler") == nh, (b["build"], hex(op), canon[row][c])
        writes_2d = "written by" in canon["0x2D"][c]
        assert (b["delete_table"] == 0x2D) == writes_2d, (b["build"], canon["0x2D"][c])
        assert ("error" in canon["0x2D"][c]) == (b["highest"] < 0x2D), (b["build"], canon["0x2D"][c])


# ═══ N554 (k): the Dispatch table line of `mlog` says which values the table names, and from which builds ═══════

@pytest.mark.parametrize("vmin, want", [
    (14, "Dispatch table:    the ReFS 3.14 table (45 opcodes: 0x0-0x2b, and 0x2d, which of the builds read only "
         "Insider 29683 dispatches; per build: `mlog --info`)"),
    (10, "Dispatch table:    the ReFS 3.14 table; names inferred for ReFS 3.10 (45 opcodes: 0x0-0x2b, and 0x2d, which "
         "of the builds read only Insider 29683 dispatches; per build: `mlog --info`)"),
    (4, "Dispatch table:    the ReFS 3.4 table (29 opcodes: 0x0-0x1c)")])
def test_n554_the_dispatch_table_line_states_the_values_and_their_builds(monkeypatch, tmp_path, vmin, want):
    """The group-1 golden (2026-11-13): the line printed the table's length alone, "the ReFS 3.14 table (45 opcodes)"
    once 0x2d was named -- read as what ReFS 3.14 dispatches, while each build read has its own set (Windows 11 26100
    0x0-0x2b, Insider 29574 / 29659 0x0-0x2c, Insider 29683 0x0-0x2d; 0x2c, no handler on any, is not named). The
    first fix said "the union of the builds read": the union of what they dispatch is 46 values (structures/mlog.md)."""
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x0F), "mlog", "--stats", vmin=vmin)
    lines = [ln.strip() for ln in out.splitlines() if "Dispatch table:" in ln]
    assert lines == [want], (lines, out[:3000])


def test_n554_the_dispatch_table_line_follows_the_per_build_table(monkeypatch, tmp_path):
    """(k) from REDO_DISPATCH_BUILDS, as the note and `mlog --info` (h): a build added there changes the line."""
    extra = {"build": "Insider 99999", "table": "3.14", "highest": 0x2D, "differs": {0x16: "no handler",
             0x2C: "no handler"}, "delete_table": 0x2D}
    monkeypatch.setattr(F, "REDO_DISPATCH_BUILDS", tuple(F.REDO_DISPATCH_BUILDS) + (extra,))
    rc, out, err = run(monkeypatch, _delete_log(tmp_path, 0x0F), "mlog", "--stats")
    assert "and 0x2d, which of the builds read only Insider 29683 / 99999 dispatch; per build: `mlog --info`)" in out, \
        out[:3000]


# ═══ N533: the record's table is PerformRedo's current table ═════════════════════════════════════════════

def _rename_log(tmp_path, between=None, block_break=False, depth2=False, cont=False, unknown=None, vmin_names=False):
    """An unrelated update of DIR_C (clock 5), then the old name removed from DIR_A (own path, clock 6), then the new
    name inserted by a path-less record (clock 5, the unrelated record's value): 1.14.0-dev filled the path-less
    record from the clock and called the rename a MOVE into DIR_C. `between`: a record put between the two name rows
    (an opcode after which the current table is empty); `block_break`: the new-name row starts the next redo block;
    `depth2`: an update of a table embedded in a row of DIR_A comes before the new-name row (whose table is then that
    embedded table, not the directory)."""
    oldn, newn = ("a", "b") if vmin_names else ("old.txt", "new.txt")
    first = [(0x03, [comp_table(DIR_C)], [b"\0" * 8], 5), (0x02, [comp_table(DIR_A)], [dir_key(oldn)], 6)]
    if unknown is not None:
        first.append((unknown, [], [b"\0" * 8], 6))       # a value the format's table does not name, path-less
    if between is not None:
        first.append((between, [comp_table(0x7AA)] if between == 0x0F else [], [], 6))
    if depth2:
        first.append((0x03, [comp_table(DIR_A), comp_row("host.txt")], [b"\0" * 8], 6))
    # group 1b (N556): the new name's key in value 0, as every depth-1 entry record of the corpus carries it (of 1.39 M
    # depth-1 row records on 124 volumes, 661,242 carry an entry key, all in value 0, none only in a later value:
    # RC1D/evidence/measures/g1b_v1form_corpus.jsonl); the fixture had it in value 1, a form not seen on disk
    new = (0x01, [], [dir_key(newn), b"\0" * 8], 5)
    blocks = [first, [new]] if block_break else [first + [new]]
    out = []
    for bi, b in enumerate(blocks):           # bit 0 on a block's first record, bit 1 (commit) on its last
        out.append([rec(op, path, vals, flags=(1 if i == 0 and not (cont and bi > 0) else 0)
                        | (2 if i == len(b) - 1 else 0), clock=c)
                    for i, (op, path, vals, c) in enumerate(b)])
    return log_of(tmp_path, [out])


def test_n533_a_path_less_name_row_takes_the_previous_records_table_not_another_tables_clock(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _rename_log(tmp_path), "mlog", "--parse")
    rows = parse_rows(out)
    assert [a for a, _ in rows] == ["RENAME"], (rows, out[-2500:])
    assert "same parent 0x700" in out, out[-2500:]


@pytest.mark.parametrize("op", [0x0F, 0x24, 0x11])
def test_n533_the_current_table_is_empty_after_a_deletion_a_commit_merge_or_a_tableless_record(monkeypatch,
                                                                                              tmp_path, op):
    rc, out, err = run(monkeypatch, _rename_log(tmp_path, between=op), "mlog", "--parse", "-v")
    m = re.search(r"0x1\s+RedoInsertRow\s+target_oid=(\S+)", out)
    assert m and m.group(1) == "(none)", out[-3000:]
    assert "RENAME" not in [a for a, _ in parse_rows(out)], out[-3000:]


def test_n533_a_block_that_starts_a_transaction_leaves_the_table_undetermined(monkeypatch, tmp_path):
    """Review F2: a block whose first record starts a transaction goes to a queue the driver picks by object id
    (`RedoOneRecordBlock`); that queue's table is not known from the log: '(none)', not determined."""
    rc, out, err = run(monkeypatch, _rename_log(tmp_path, block_break=True), "mlog", "--parse", "-v")
    m = re.search(r"0x1\s+RedoInsertRow\s+target_oid=(\S+)", out)
    assert m and m.group(1) == "(none)", out[-3000:]


def test_n533_a_block_that_continues_a_transaction_carries_the_table(monkeypatch, tmp_path):
    """Review F2: a block whose first record does not start a transaction stays on the previous block's queue, whose
    current table carries into it (`CmsLogRedoQueue`+0xf0 is zeroed only by the queue's constructor)."""
    rc, out, err = run(monkeypatch, _rename_log(tmp_path, block_break=True, cont=True), "mlog", "--parse", "-v")
    assert re.search(r"0x1\s+RedoInsertRow\s+target_oid=0x700 \(inherited\)", out), out[-3000:]
    assert [a for a, _ in parse_rows(out)] == ["RENAME"], out[-3000:]


@pytest.mark.parametrize("vmin, op", [(4, 0x1D), (14, 0x2C)], ids=["3.4-above-0x1c", "3.14-0x2c"])
def test_n533_an_unnamed_value_the_driver_resolves_keeps_the_table(monkeypatch, tmp_path, vmin, op):
    """Review F3: 17134 keeps a table after a value above 0x1c, the Insider builds after 0x2c (no handler)."""
    rc, out, err = run(monkeypatch, _rename_log(tmp_path, unknown=op), "mlog", "--parse", "-v", vmin=vmin)
    assert re.search(r"0x1\s+RedoInsertRow\s+target_oid=0x700 \(inherited\)", out), out[-3000:]


def test_n533_a_value_no_build_dispatches_empties_the_table(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _rename_log(tmp_path, unknown=0x3C), "mlog", "--parse", "-v")
    m = re.search(r"0x1\s+RedoInsertRow\s+target_oid=(\S+)", out)
    assert m and m.group(1) == "(none)", out[-3000:]


def test_n533_the_parse_v_legend_names_no_handle(monkeypatch, tmp_path):
    """Review F1: the legend says what target_oid is -- the key's table, '(inherited)' or '(none)' -- and no longer
    N218's withdrawn "the table its handle (+0x20) was opened on"."""
    rc, out, err = run(monkeypatch, _rename_log(tmp_path), "mlog", "--parse", "-v")
    legend = out[out.index("(-v: each redo record"):][:600]
    assert "handle" not in legend and "(inherited)" in legend and "not determined" in legend, legend


def test_n533_a_rename_row_shows_its_name_in_the_name_rows_directory(monkeypatch, tmp_path):
    """Review F4: a row that shows a name shows it in that name row's own directory, not in the payload's first user
    table (here the unrelated update of DIR_C)."""
    rc, out, err = run(monkeypatch, _rename_log(tmp_path), "mlog", "--csv",
                       paths={DIR_A: "/dirA", DIR_C: "/dirC"})
    rows = csv_rows(out)
    assert len(rows) == 1 and rows[0]["DerivedAction"] == "RENAME", rows
    assert rows[0]["PathToday"] == "dirA/old.txt" and rows[0]["ParentPathToday"] == "dirA" \
        and rows[0]["OID"] == "0x700", rows[0]


def test_n533_a_one_character_rename_is_a_rename(monkeypatch, tmp_path):
    """Review F5: a one-character name's key is 6 bytes; "a" -> "b" was UPDATE."""
    rc, out, err = run(monkeypatch, _rename_log(tmp_path, vmin_names=True), "mlog", "--parse")
    assert [a for a, _ in parse_rows(out)] == ["RENAME"], out[-2500:]
    assert 'name: "a"' in out and 'name: "b"' in out, out[-2500:]


def test_n533_a_name_row_of_an_embedded_table_is_not_a_directory_entry(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _rename_log(tmp_path, depth2=True), "mlog", "--parse")
    acts = [a for a, _ in parse_rows(out)]
    assert not set(acts) & {"RENAME", "MOVE", "MOVE_OR_RENAME"}, (acts, out[-2500:])


def test_n533_parse_v_marks_an_inherited_table(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _rename_log(tmp_path), "mlog", "--parse", "-v")
    m = re.search(r"0x1\s+RedoInsertRow\s+target_oid=0x700 \(inherited\)", out)
    assert m, out[-3000:]
    assert re.search(r"0x2\s+RedoDeleteRow\s+target_oid=0x700\s", out), out[-3000:]


def test_n533_mlog_v_names_the_allocator_clock_in_decimal(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _rename_log(tmp_path), "mlog", "-v")
    hdr = [l for l in out.split("\n") if re.search(r"#\s+Opcode\s+Name", l)]
    assert hdr and "Handle" not in hdr[0] and "AllocClock" in hdr[0], hdr
    assert re.search(r"RedoInsertRow\s+5\s", out), out[-3000:]


def test_n533_mlog_json_record_carries_the_allocator_clock_and_the_inherited_table(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, _rename_log(tmp_path), "mlog", "--json")
    doc = json.loads(out)
    recs = doc["Records"]
    assert all("TableHandle" not in r for r in recs), recs[0]
    new = [r for r in recs if r["Opcode"] == "0x1"][0]
    assert new["AllocatorClock"] == 5, new
    assert new["TargetOID"] is None, new                          # READ: the record's own key names no table
    assert new["InheritedTableOID"] == "0x700", new               # DERIVED: PerformRedo's current table
    old = [r for r in recs if r["Opcode"] == "0x2"][0]
    assert old["TargetOID"] == "0x700" and old["InheritedTableOID"] is None, old


# ═══ decision 53: MOVE_OR_RENAME ═════════════════════════════════════════════════════════════════════════

def test_d53_overlapping_unequal_directory_sets_are_move_or_rename(monkeypatch, tmp_path):
    blk = [rec(0x02, [comp_table(DIR_A)], [dir_key("x.txt")], flags=1),
           rec(0x02, [comp_table(DIR_B)], [dir_key("x.txt", 2)], flags=0),
           rec(0x05, [comp_table(0x7AB)], [b"\0" * 16], flags=0),
           rec(0x01, [comp_table(DIR_A)], [dir_key("y.txt")], flags=0),
           rec(0x01, [comp_table(DIR_C)], [dir_key("y.txt", 2)], flags=2)]
    rc, out, err = run(monkeypatch, log_of(tmp_path, [[blk]]), "mlog", "--parse")
    rows = parse_rows(out)
    assert [a for a, _ in rows] == ["MOVE_OR_RENAME"], (rows, out[-2500:])
    assert "parents undetermined: old 0x700;0x800, new 0x700;0x900" in out, out[-2500:]
    assert "MOVE_OR_RENAME" in F.MLOG_FILE_OPS


def test_d53_mlog_info_describes_move_or_rename():
    assert re.search(r"^\s+MOVE_OR_RENAME\s", F._MLOG_INFO_TEXT, re.M), F._MLOG_INFO_TEXT[:3000]


# ═══ N537: a path-less directory-key name row ════════════════════════════════════════════════════════════

def test_n537_a_path_less_directory_key_row_keeps_its_whole_name(monkeypatch, tmp_path):
    blk = [rec(0x03, [comp_table(0x600)], [b"\0" * 8], flags=1),
           rec(0x01, [], [dir_key("System Volume Information")], flags=2)]
    rc, out, err = run(monkeypatch, log_of(tmp_path, [[blk]]), "mlog", "--csv")
    names = [r["Name"] for r in csv_rows(out)]
    assert names == ["System Volume Information"], (names, out[-1500:])


# ═══ A1: summary's MLog pass behind --mlog / -v ══════════════════════════════════════════════════════════

def _img(rel):
    p = _corpus_image(rel)
    if p is None:
        pytest.skip("%s not in this tree" % rel)
    return p


def _cli(tool, image, *args):
    r = UW.run([sys.executable, "-B", tool, image] + list(args), capture_output=True, text=True,
               timeout=600, cwd=os.path.dirname(image))
    assert "Traceback (most recent call last)" not in r.stderr, r.stderr[-3000:]
    return r.returncode, r.stdout, r.stderr


def _mlog_section(out):
    """`summary`'s MLog section: its heading, the rule under it and its lines up to the blank line that ends it."""
    m = re.search(r"^(MLog[^\n]*)\n-{20,}\n(.*?)(?:\n[ \t]*\n|\Z)", out, re.M | re.S)
    return (m.group(1) + "\n" + m.group(2)) if m else ""


@pytest.mark.parametrize("tool", [FOREFST, RA])
def test_a1_summary_does_not_read_the_log_by_default_and_names_both_options(tool):
    rc, out, err = _cli(tool, _img(MINI), "summary")
    sec = _mlog_section(out)
    assert sec, out[-3000:]
    assert "not read" in sec and "summary --mlog" in sec and "summary -v" in sec, sec
    assert "Control copy:" not in sec, sec


@pytest.mark.parametrize("tool", [FOREFST, RA])
@pytest.mark.parametrize("opt", ["--mlog", "-v"])
def test_a1_summary_mlog_or_v_runs_the_pass(tool, opt):
    rc, out, err = _cli(tool, _img(MINI), "summary", opt)
    sec = _mlog_section(out)
    assert "Control copy:" in sec and "not read" not in sec, sec


def test_a1_summary_json_says_the_log_was_not_read():
    rc, out, err = _cli(FOREFST, _img(MINI), "summary", "--json")
    doc = json.loads(out)
    assert doc.get("MLog") == {"Read": False}, doc.get("MLog")
    rc, out, err = _cli(FOREFST, _img(MINI), "summary", "--json", "--mlog")
    doc = json.loads(out)
    assert doc["MLog"].get("Read") is True and "ControlCopySlot" in doc["MLog"], doc["MLog"]


@pytest.mark.parametrize("args", [("files", "-qv"), ("files", "--verb"), ("files", "--ml"), ("-v", "@IMG", "files")],
                         ids=["combined", "abbrev-verbose", "abbrev-mlog", "before-the-image"])
def test_a1_another_command_refuses_the_summary_options_in_every_spelling(args):
    """Review F6: decided from the parsed options, not from the raw words."""
    img = _img(MINI)
    argv = [img if a == "@IMG" else a for a in args]
    if "@IMG" not in args:
        argv = [img] + argv
    r = subprocess.run([sys.executable, "-B", FOREFST] + argv, capture_output=True, text=True, timeout=600,
                       cwd=os.path.dirname(img))
    assert r.returncode == 1 and "unrecognized arguments" in r.stderr, (r.returncode, r.stderr[-800:])


def test_a1_control_a_search_for_the_name_v_after_double_dash_still_runs():
    rc, out, err = _cli(FOREFST, _img(MINI), "search", "--", "-v")
    assert rc == 0 and "unrecognized arguments" not in err, (rc, err[-800:])


@pytest.mark.parametrize("opt", ["--mlog", "-v"])
def test_a1_control_another_command_refuses_the_summary_options(opt):
    rc, out, err = _cli(FOREFST, _img(MINI), "files", opt)
    assert rc == 1 and "unrecognized arguments: %s" % opt in err, (rc, err[-800:])      # the one exit rule: 1


# ═══ N554 (c): refsanalysis chkp (its field table) ══════════════════════════════════════════════════════════════════════

def test_n554_refsanalysis_chkp_names_0x88_and_0x8c_as_an_offset_and_a_length():
    rc, out, err = _cli(RA, _img(MINI), "chkp")
    assert "Data area end" not in out and "Max root capacity" not in out, out[-4000:]
    l88 = [l for l in out.split("\n") if re.search(r"\s0x88\s", l)]
    l8c = [l for l in out.split("\n") if re.search(r"\s0x8c\s", l)]
    assert l88 and "offset" in l88[0].lower(), l88
    assert l8c and "length" in l8c[0].lower(), l8c
