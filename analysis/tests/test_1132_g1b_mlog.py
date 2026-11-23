"""The code half, group 1b (MLog), 1.14.0: RUNNING_LOG N556 and N557 (decision 55, the maintainer 2026-11-13).

  N556  a log row's move / rename class comes from the file's own records where they pair the two sides: the file's
        `$OBJ_LINK` row deleted as (old parent, old name) and inserted as (new parent, new name) in one table and
        transaction, or a `RedoReparentTable` from the old name row to the new one (KNOWLEDGE_INTAKE A167, A168).
        MOVE (parent changed, name kept), RENAME (same parent, new name), MOVE_AND_RENAME (both). A directory entry
        removed with no entry added for it is ENTRY_REMOVE, never RENAME. Where the records pair nothing (a 3.4
        directory) decision 53's directory-set rule stays, on the payload's NET entries (an entry inserted and removed
        again inside the payload is no change). 1.14.0-dev compared the sets of directories of the payload's name
        rows: 1,552 RENAME rows of the corpus leave no new name (lab314_main's 234 are files its script deletes), and
        5,713 of the 5,761 MOVE_OR_RENAME rows are decided by the file's records (RC1D/D53_PRECISION.md).
  N557  the directory of a row that shows a name: the first DEPTH-1 directory-entry record's, as the group 1 review's
        F4 asked; 1.14.0-dev took the first record with a name of any depth and kept an unrelated first table when
        that record was a file's `$OBJ_LINK` row (lab314_main t10_b: `LAB_0906` for a file in `LAB_0906/d1`).

Written RED before the fix (the run is recorded in `analysis/reports/v1.13.2/RC1D/G1b/`). Synthetic logs in the shape of
the lab314_main payloads read byte by byte (D53_PRECISION.md section 2); this file's own builders.
"""
import json
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_waveb_mlog as WB                    # noqa: E402  (log builder, in-process runner)
from test_1132_g1_mlog import (comp_table, comp_row, dir_key, rec, log_of, run, parse_rows, csv_rows,  # noqa: E402
                               DIR_A, DIR_B, DIR_C)


@pytest.fixture(autouse=True)
def _volume_information(monkeypatch):
    monkeypatch.setattr(F, "volume_information_read",
                        lambda *a, **k: ({"vol_create_time": WB.filetime(2020, 1, 1, 0, 0, 0, 0),
                                          "vol_modify_time": 0}, None))


# ═══ builders ═════════════════════════════════════════════════════════════════════════════════════════════════

def objlink_value(parent, name):
    """An `$OBJ_LINK` value (structure_reference.md): u32 marker 0x80000002, u16 type 0x39, u16 sub-type 0x0D, the
    parent OID at +0x08, 8 zero bytes, the name in UTF-16 at +0x18."""
    return struct.pack("<IHHQ8x", 0x80000002, 0x39, 0x0D, parent) + name.encode("utf-16-le")


def objlink_key(parent, name):
    """Its key: le64(the value's length), then the value."""
    v = objlink_value(parent, name)
    return struct.pack("<Q", len(v)) + v


def fid_row(fid, home):
    """A FileId row key: u32 0x80000040, u32 0, u64 the file id, u64 the home directory."""
    return struct.pack("<IIQQ", 0x80000040, 0, fid, home)


def comp_fid(fid, home):
    """A second path component naming a file's table held in its FileId row (the 12-byte prefix of `comp_row`)."""
    return struct.pack("<III", 0x130, 0x1E0, 0) + fid_row(fid, home)


def table_path(*comps):
    """A serialized table path (a RedoReparentTable's value 0): u32 count, u32 the offset of the (offset, length)
    array (8), the array, then the components, each 8-aligned."""
    n = len(comps)
    off = 8 + 8 * n
    arr, data = b"", b""
    for c in comps:
        arr += struct.pack("<II", off + len(data), len(c))
        data += c + b"\0" * ((-len(c)) % 8)
    return struct.pack("<II", n, 8) + arr + data


ENTRY_VALUE = b"\0" * 84            # a link-form entry's value (FileId, home, times): its bytes are not read here


def _blocks(*txns):
    """Each transaction one redo block: bit 0 (start) on its first record, bit 1 (commit) on its last."""
    out = []
    for t in txns:
        out.append([rec(op, path, vals, flags=(1 if i == 0 else 0) | (2 if i == len(t) - 1 else 0))
                    for i, (op, path, vals) in enumerate(t)])
    return out


def split_txn(d, name, fid):
    """Transaction 1 of A167: the file's table moves out of its name row in `d` to a FileId row there, an `$OBJ_LINK`
    row (d, name) is inserted in it, and the name is written back into `d` in link form."""
    return [(0x05, [comp_table(d), comp_row(name)], [table_path(comp_table(d)), fid_row(fid, d)]),
            (0x01, [], [objlink_key(d, name), objlink_value(d, name)]),
            (0x01, [comp_table(d)], [dir_key(name, 2), ENTRY_VALUE])]


def change_txn(d, name, fid, nd, nname):
    """Transaction 2: the link-form name leaves `d`, the file's `$OBJ_LINK` row goes from (d, name) to (nd, nname), and
    the name `nname` is inserted into `nd`."""
    return [(0x02, [comp_table(d)], [dir_key(name, 2)]),
            (0x02, [comp_table(d), comp_fid(fid, d)], [objlink_key(d, name)]),
            (0x01, [], [objlink_key(nd, nname), objlink_value(nd, nname)]),
            (0x01, [comp_table(nd)], [dir_key(nname, 2), ENTRY_VALUE])]


def removal_txn(d, name, fid):
    """Transaction 2 of a deletion (lab314_main f_2.bin): the name and the file's `$OBJ_LINK` row go, nothing is added."""
    return [(0x02, [comp_table(d)], [dir_key(name, 2)]),
            (0x02, [comp_table(d), comp_fid(fid, d)], [objlink_key(d, name)]),
            (0x04, [], [b"\0" * 4])]


PATHS = {DIR_A: "/dirA", DIR_B: "/dirB", DIR_C: "/dirC"}


def _parse(monkeypatch, tmp_path, blocks, *extra, vmin=14):
    rc, out, err = run(monkeypatch, log_of(tmp_path, [blocks]), "mlog", "--parse", *extra, vmin=vmin, paths=PATHS)
    return parse_rows(out), out


def _csv(monkeypatch, tmp_path, blocks, vmin=14):
    rc, out, err = run(monkeypatch, log_of(tmp_path, [blocks]), "mlog", "--csv", vmin=vmin, paths=PATHS)
    return csv_rows(out)


# ═══ N556: the class from the file's own records ═════════════════════════════════════════════════════════════════

def test_n556_r1_a_move_after_the_split_is_a_move(monkeypatch, tmp_path):
    """lab314_main t7_big / t10_c / del_split: the name re-inserted into the old directory by the split made the sets
    {A} and {A, B} overlap (MOVE_OR_RENAME); the file's `$OBJ_LINK` goes (A, t.bin) -> (B, t.bin)."""
    rows, out = _parse(monkeypatch, tmp_path, _blocks(split_txn(DIR_A, "t.bin", 4),
                                                      change_txn(DIR_A, "t.bin", 4, DIR_B, "t.bin")))
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])
    assert "parent 0x700 → 0x800" in rows[0][1], rows


def test_n556_r2_a_move_with_a_new_name_is_move_and_rename(monkeypatch, tmp_path):
    """lab314_main recycle_me.bin -> $RLTM1PM.bin in the Recycle Bin (its `$I` record gives the original path)."""
    rows, out = _parse(monkeypatch, tmp_path, _blocks(split_txn(DIR_A, "t.bin", 4),
                                                      change_txn(DIR_A, "t.bin", 4, DIR_B, "$Rabc.bin")))
    assert [a for a, _ in rows] == ["MOVE_AND_RENAME"], (rows, out[-2500:])
    assert "parent 0x700 → 0x800" in rows[0][1] and "t.bin → $Rabc.bin" in rows[0][1], rows
    assert "MOVE_AND_RENAME" in F.MLOG_FILE_OPS


def test_n556_r3_a_removal_with_nothing_added_is_entry_remove_not_rename(monkeypatch, tmp_path):
    """lab314_main f_2.bin (deleted by its script; 1.13.1 and 1.14.0-dev: RENAME 'same parent'): the name is inserted
    by the split and removed again, the file's `$OBJ_LINK` goes, no entry is added."""
    rows, out = _parse(monkeypatch, tmp_path, _blocks(split_txn(DIR_A, "f.bin", 3), removal_txn(DIR_A, "f.bin", 3)))
    assert [a for a, _ in rows] == ["ENTRY_REMOVE"], (rows, out[-2500:])
    assert "f.bin" in rows[0][1], rows


def test_n556_r4_a_reparent_from_one_name_row_to_another_is_a_rename(monkeypatch, tmp_path):
    """An embedded file renamed: the reparent itself carries (A, a.bin) -> (A, b.bin); 1.14.0-dev: TABLE_REPARENTED
    (the public sample's key: 125 of 125 such rows are renames of its log)."""
    blk = _blocks([(0x05, [comp_table(DIR_A), comp_row("a.bin")], [table_path(comp_table(DIR_A)), dir_key("b.bin")]),
                   (0x04, [], [b"\0" * 4])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["RENAME"], (rows, out[-2500:])
    assert "same parent 0x700" in rows[0][1] and "a.bin → b.bin" in rows[0][1], rows


@pytest.mark.parametrize("vmin", [4, 14])
def test_n556_r5_a_reparent_into_another_directory_is_a_move(monkeypatch, tmp_path, vmin):
    """A file that stays embedded when moved (3.4, E144): the reparent from (A, a.bin) to (B, a.bin)."""
    blk = _blocks([(0x05, [comp_table(DIR_A), comp_row("a.bin")], [table_path(comp_table(DIR_B)), dir_key("a.bin")])])
    rows, out = _parse(monkeypatch, tmp_path, blk, vmin=vmin)
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])
    assert "parent 0x700 → 0x800" in rows[0][1], rows


def test_n556_r7_an_evidenced_removal_beside_a_creation_is_not_a_move(monkeypatch, tmp_path):
    """The public sample's 11 MOVE rows whose removed name its key deletes: x leaves A with its `$OBJ_LINK`, y is a new
    entry in B -- no file's records pair them."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("x.bin", 2)]),
                   (0x02, [comp_table(DIR_A), comp_fid(5, DIR_A)], [objlink_key(DIR_A, "x.bin")]),
                   (0x01, [comp_table(DIR_B)], [dir_key("y.bin"), ENTRY_VALUE])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["CREATE"], (rows, out[-2500:])
    assert "y.bin" in rows[0][1] and "x.bin" in rows[0][1], rows


@pytest.mark.parametrize("nd, want", [(DIR_A, "RENAME"), (DIR_B, "MOVE")])
def test_n556_r8_with_nothing_to_pair_the_directory_sets_decide(monkeypatch, tmp_path, nd, want):
    """A 3.4 directory carries no `$OBJ_LINK` (E77) and no reparent: decision 53's rule stays."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("d1")]), (0x01, [comp_table(nd)], [dir_key("d2"), ENTRY_VALUE])])
    rows, out = _parse(monkeypatch, tmp_path, blk, vmin=4)
    assert [a for a, _ in rows] == [want], (rows, out[-2500:])
    # review 2 (independent review #2): a class the directories alone give says so, and names both names
    assert "names not paired" in rows[0][1] and "d2" in rows[0][1], rows


def test_n556_r9_an_entry_inserted_and_removed_again_is_no_change(monkeypatch, tmp_path):
    """The sets compared are the NET entries: z, inserted into A and removed again, does not put A on the new side
    ({A} vs {B}: MOVE, not MOVE_OR_RENAME)."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("x.bin")]),
                   (0x01, [comp_table(DIR_A)], [dir_key("z.bin"), ENTRY_VALUE]),
                   (0x02, [comp_table(DIR_A)], [dir_key("z.bin")]),
                   (0x01, [comp_table(DIR_B)], [dir_key("x.bin"), ENTRY_VALUE])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])


def test_n556_r10_mlog_json_carries_the_pairs(monkeypatch, tmp_path):
    rc, out, err = run(monkeypatch, log_of(tmp_path, [_blocks(split_txn(DIR_A, "t.bin", 4),
                                                              change_txn(DIR_A, "t.bin", 4, DIR_B, "$Rabc.bin"))]),
                       "mlog", "--json", paths=PATHS)
    doc = json.loads(out)
    tx = [t for t in doc["Transactions"] if t.get("DerivedAction") == "MOVE_AND_RENAME"]
    assert len(tx) == 1, [t.get("DerivedAction") for t in doc["Transactions"]]
    assert tx[0]["Entries"]["Pairs"] == [{"Kind": "MOVE_AND_RENAME", "OldParentOID": "0x700", "OldName": "t.bin",
                                         "NewParentOID": "0x800", "NewName": "$Rabc.bin"}], tx[0]


def test_n556_r11_info_and_the_counts_name_move_and_rename(monkeypatch, tmp_path):
    assert re.search(r"^\s+MOVE_AND_RENAME\s", F._MLOG_INFO_TEXT, re.M), F._MLOG_INFO_TEXT[:3000]
    rows, out = _parse(monkeypatch, tmp_path, _blocks(split_txn(DIR_A, "t.bin", 4),
                                                      change_txn(DIR_A, "t.bin", 4, DIR_B, "$Rabc.bin")))
    assert re.search(r"^\s+MOVE_AND_RENAME\s+1\s*$", out, re.M), out[-2500:]


def test_n556_r13_a_delete_row_names_the_rename_beside_it(monkeypatch, tmp_path):
    """A merged payload holding a table deletion and a rename: DELETE stays first; the rename is no longer hidden."""
    blk = _blocks([(0x0F, [comp_table(0x7AA)], [])],
                  [(0x05, [comp_table(DIR_A), comp_row("a.bin")], [table_path(comp_table(DIR_A)), dir_key("b.bin")])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["DELETE"], (rows, out[-2500:])
    assert "a.bin → b.bin" in rows[0][1], rows


# ═══ N557: the row's directory ═══════════════════════════════════════════════════════════════════════════════════

def test_n557_r6_a_move_after_an_unrelated_first_record_shows_the_old_directory(monkeypatch, tmp_path):
    """lab314_main t10_b: the payload starts with an update of dirA's own row in dirC; the row printed dirC/t10_b.bin."""
    first = [(0x03, [comp_table(DIR_C)], [dir_key("dirA", 2), ENTRY_VALUE])]
    rows = _csv(monkeypatch, tmp_path, _blocks(first, split_txn(DIR_A, "t.bin", 4),
                                               change_txn(DIR_A, "t.bin", 4, DIR_B, "t.bin")))
    assert len(rows) == 1 and rows[0]["DerivedAction"] == "MOVE", rows
    assert rows[0]["ParentPathToday"] == "dirA" and rows[0]["PathToday"] == "dirA/t.bin", rows[0]


def test_n557_r12_a_name_row_after_a_files_objlink_row_gives_the_directory(monkeypatch, tmp_path):
    """Not a pair: a new entry whose file's `$OBJ_LINK` row comes first -- path-less, in the file's table (depth 2),
    the first record with a name (the tool reads it from the value), as in lab314_main's payloads -- after an unrelated
    first table (dirC): the row shows the entry in dirA."""
    blk = _blocks([(0x03, [comp_table(DIR_C)], [b"\0" * 8]),
                   (0x04, [comp_table(DIR_A), comp_fid(6, DIR_A)], [b"\0" * 4]),
                   (0x01, [], [objlink_key(DIR_A, "n.bin"), objlink_value(DIR_A, "n.bin")]),
                   (0x01, [comp_table(DIR_A)], [dir_key("n.bin", 2), ENTRY_VALUE])])
    rows = _csv(monkeypatch, tmp_path, blk)
    assert len(rows) == 1 and rows[0]["DerivedAction"] == "CREATE", rows
    assert rows[0]["ParentPathToday"] == "dirA" and rows[0]["PathToday"] == "dirA/n.bin", rows[0]


def test_n556_r14_rows_the_records_cannot_decide_are_stated(monkeypatch, tmp_path):
    """Where nothing pairs the names and their directory sets overlap without being equal, the row is MOVE_OR_RENAME and
    the summary says how many such rows the parents could not be told apart for."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("x.txt")]),
                   (0x02, [comp_table(DIR_B)], [dir_key("x.txt", 2)]),
                   (0x01, [comp_table(DIR_A)], [dir_key("y.txt"), ENTRY_VALUE]),
                   (0x01, [comp_table(DIR_C)], [dir_key("y.txt", 2), ENTRY_VALUE])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["MOVE_OR_RENAME"], (rows, out[-2500:])
    assert re.search(r"1 MOVE_OR_RENAME row\(s\): the old and the new parent cannot be told apart", out), out[-2500:]


def test_golden_a_side_naming_several_directories_shows_both_sets(monkeypatch, tmp_path):
    """The group's golden (RC1D/G1b_golden): 54 directory-set rows on 7 volumes (29 MOVE, 25 MOVE_OR_RENAME) print
    `parents undetermined` -- a MOVE too, where a side names more than one directory (N431). The help, `--info` and the
    two pages said it of MOVE_OR_RENAME only (the group's rewrite dropped the 1.14.0-dev help's 'more than one
    directory on a side')."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("x.txt")]),
                   (0x02, [comp_table(DIR_B)], [dir_key("x.txt", 2)]),
                   (0x01, [comp_table(DIR_C)], [dir_key("y.txt"), ENTRY_VALUE])])
    rows, out = _parse(monkeypatch, tmp_path, blk, vmin=4)
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])
    assert "names not paired; parents undetermined: old 0x700;0x800, new 0x900" in rows[0][1], rows
    help_text = " ".join(F.CMD_HELP["mlog"]["desc"])
    docs = os.path.join(REPO, "docs")
    texts = {"help": help_text, "--info": F._MLOG_INFO_TEXT,
             "mlog.md": open(os.path.join(docs, "structures", "mlog.md"), encoding="utf-8").read(),
             "forefst.md": open(os.path.join(docs, "tools", "forefst.md"), encoding="utf-8").read()}
    for k, t in texts.items():
        assert re.search(r"more than\s+one\s+directory,?\s+both\s+sets\s+are\s+shown", t), k


# ═══ the independent review (RC1D/G1b/REVIEW_AGENT.md) and the self-review (REVIEW.md) ══════════════════════════════

def _rename_txn(d, old, fid, new, nd=None):
    """One file renamed (or moved, `nd`) in its own transaction, already in link form: its name leaves `d`, its
    `$OBJ_LINK` goes from (d, old) to (nd or d, new), the new name is inserted."""
    nd = d if nd is None else nd
    return [(0x02, [comp_table(d)], [dir_key(old, 2)]),
            (0x02, [comp_table(d), comp_fid(fid, d)], [objlink_key(d, old)]),
            (0x01, [], [objlink_key(nd, new), objlink_value(nd, new)]),
            (0x01, [comp_table(nd)], [dir_key(new, 2), ENTRY_VALUE])]


def _create_txn(d, name, fid):
    """A file created in link form (its name row and its `$OBJ_LINK`)."""
    return [(0x01, [comp_table(d), comp_fid(fid, d)], [objlink_key(d, name), objlink_value(d, name)]),
            (0x01, [comp_table(d)], [dir_key(name, 2), ENTRY_VALUE])]


def test_review_1a_an_atomic_save_shows_both_renames(monkeypatch, tmp_path):
    """doc -> doc.bak, then doc.tmp -> doc, in one payload: the name doc is freed and taken again. A pair is judged in
    its own transaction, so neither file's rename is lost (the payload-wide rule saw doc as unchanged and paired nothing:
    a directory-set RENAME of 'doc')."""
    rows, out = _parse(monkeypatch, tmp_path, _blocks(_rename_txn(DIR_A, "doc", 5, "doc.bak"),
                                                      _rename_txn(DIR_A, "doc.tmp", 6, "doc")))
    assert [a for a, _ in rows] == ["RENAME"], (rows, out[-2500:])
    assert "doc → doc.bak" in rows[0][1] and "doc.tmp → doc" in rows[0][1], rows


def test_review_1b_a_file_created_and_renamed_in_one_payload(monkeypatch, tmp_path):
    """doc.tmp created, then doc -> doc.bak and doc.tmp -> doc: both renames shown (the payload-wide rule: CREATE of
    doc.bak)."""
    rows, out = _parse(monkeypatch, tmp_path, _blocks(_create_txn(DIR_A, "doc.tmp", 6),
                                                      _rename_txn(DIR_A, "doc", 5, "doc.bak"),
                                                      _rename_txn(DIR_A, "doc.tmp", 6, "doc")))
    assert [a for a, _ in rows] == ["RENAME"], (rows, out[-2500:])
    assert "doc → doc.bak" in rows[0][1] and "doc.tmp → doc" in rows[0][1], rows


def test_review_1c_a_log_rotation(monkeypatch, tmp_path):
    """app.log.1 -> app.log.2, app.log -> app.log.1, a new app.log: two renames and a creation."""
    rows, out = _parse(monkeypatch, tmp_path, _blocks(_rename_txn(DIR_A, "app.log.1", 7, "app.log.2"),
                                                      _rename_txn(DIR_A, "app.log", 8, "app.log.1"),
                                                      _create_txn(DIR_A, "app.log", 9)))
    assert [a for a, _ in rows] == ["RENAME"], (rows, out[-2500:])
    d = rows[0][1]
    assert "app.log.1 → app.log.2" in d and "app.log → app.log.1" in d and "added app.log" in d, rows


def test_review_3_a_second_move_in_also_names_its_file(monkeypatch, tmp_path):
    rows, out = _parse(monkeypatch, tmp_path, _blocks(split_txn(DIR_A, "a.bin", 4), change_txn(DIR_A, "a.bin", 4, DIR_B, "a.bin"),
                                                      split_txn(DIR_A, "b.bin", 5), change_txn(DIR_A, "b.bin", 5, DIR_B, "b.bin")))
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])
    assert re.search(r"also MOVE b\.bin: parent 0x700 → 0x800", rows[0][1]), rows


def test_review_4_a_moved_directory_kept_as_itself_shows_its_own_name(monkeypatch, tmp_path):
    """A file created in `sub` (0x710, today dirB/sub), then `sub` moved A -> B: the row is `sub` (the directory itself),
    never 'dirB/sub → x.txt' (x.txt was not moved)."""
    blk = _blocks([(0x01, [comp_table(0x710)], [dir_key("x.txt"), ENTRY_VALUE])],
                  [(0x02, [comp_table(DIR_A)], [dir_key("sub", 2)]),
                   (0x02, [comp_table(0x710)], [objlink_key(DIR_A, "sub")]),
                   (0x01, [], [objlink_key(DIR_B, "sub"), objlink_value(DIR_B, "sub")]),
                   (0x01, [comp_table(DIR_B)], [dir_key("sub", 2), ENTRY_VALUE])])
    rc, out, err = run(monkeypatch, log_of(tmp_path, [blk]), "mlog", "--csv",
                       paths={DIR_A: "/dirA", DIR_B: "/dirB", 0x710: "/dirB/sub"})
    r = csv_rows(out)
    assert len(r) == 1 and r[0]["DerivedAction"] == "MOVE", r
    assert r[0]["Name"] == "sub" and "x.txt" not in r[0]["PathToday"], r[0]


def test_review_5_a_deletion_beside_an_unpaired_move_is_named(monkeypatch, tmp_path):
    """a.bin deleted (its link removed), b.bin's name leaves A and appears in B with no record pairing them: the
    directory-set row names the deletion too."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("a.bin", 2)]),
                   (0x02, [comp_table(DIR_A), comp_fid(4, DIR_A)], [objlink_key(DIR_A, "a.bin")]),
                   (0x02, [comp_table(DIR_A)], [dir_key("b.bin")]),
                   (0x01, [comp_table(DIR_B)], [dir_key("b.bin"), ENTRY_VALUE])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])
    d = rows[0][1]
    assert "names not paired" in d and "removed a.bin" in d and "b.bin" in d, rows


def test_review_7_an_undetermined_link_table_is_no_evidence(monkeypatch, tmp_path):
    """The link insert's table is undetermined (after a record that empties the current table): its delete alone is not
    evidence that the file lost the name -- not CREATE + removed."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("t.bin", 2)]),
                   (0x02, [comp_table(DIR_A), comp_fid(4, DIR_A)], [objlink_key(DIR_A, "t.bin")]),
                   (0x11, [], []),
                   (0x01, [], [objlink_key(DIR_B, "t.bin"), objlink_value(DIR_B, "t.bin")]),
                   (0x01, [comp_table(DIR_B)], [dir_key("t.bin", 2), ENTRY_VALUE])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])
    assert "names not paired" in rows[0][1], rows


def test_review_16_a_delete_row_shows_the_directory_entrys_directory(monkeypatch, tmp_path):
    """N557's fallback (no entry the class names): a DELETE whose first named record is a file's `$OBJ_LINK` (depth 2,
    path-less) and whose directory entry is in dirA, after an unrelated first table (dirC)."""
    blk = _blocks([(0x03, [comp_table(DIR_C)], [b"\0" * 8])],
                  [(0x0F, [comp_table(0x7AA)], [])],
                  [(0x04, [comp_table(DIR_A), comp_fid(6, DIR_A)], [b"\0" * 4]),
                   (0x02, [], [objlink_key(DIR_A, "n.bin")]),
                   (0x02, [comp_table(DIR_A)], [dir_key("n.bin", 2)])])
    r = _csv(monkeypatch, tmp_path, blk)
    assert len(r) == 1 and r[0]["DerivedAction"] == "DELETE", r
    assert r[0]["ParentPathToday"] == "dirA", r[0]


def test_review_17a_one_hard_link_removed_is_entry_remove(monkeypatch, tmp_path):
    """A file with two names (two `$OBJ_LINK` rows); one name and its link row removed: ENTRY_REMOVE of that name."""
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("l2.bin", 2)]),
                   (0x02, [comp_table(DIR_A), comp_fid(4, DIR_A)], [objlink_key(DIR_A, "l2.bin")])])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert [a for a, _ in rows] == ["ENTRY_REMOVE"] and "l2.bin" in rows[0][1], (rows, out[-2500:])


def test_review_17b_a_case_only_rename_is_a_rename(monkeypatch, tmp_path):
    rows, out = _parse(monkeypatch, tmp_path, _blocks(_rename_txn(DIR_A, "Foo.txt", 4, "foo.txt")))
    assert [a for a, _ in rows] == ["RENAME"] and "Foo.txt → foo.txt" in rows[0][1], (rows, out[-2500:])


def test_review_17c_v_shows_the_link_and_the_reparent_target(monkeypatch, tmp_path):
    blk = _blocks(split_txn(DIR_A, "t.bin", 4), change_txn(DIR_A, "t.bin", 4, DIR_B, "t.bin"),
                  [(0x05, [comp_table(DIR_A), comp_row("a.bin")], [table_path(comp_table(DIR_B)), dir_key("a.bin")])])
    rc, out, err = run(monkeypatch, log_of(tmp_path, [blk]), "mlog", "--parse", "-v", paths=PATHS)
    assert 'link=0x800 "t.bin"' in out and 'to=0x800 "a.bin"' in out and "to=0x700 FileId 0x4" in out, out[-3000:]


def test_review_17d_json_entries_name_the_removed_and_added(monkeypatch, tmp_path):
    blk = _blocks([(0x02, [comp_table(DIR_A)], [dir_key("x.bin", 2)]),
                   (0x02, [comp_table(DIR_A), comp_fid(5, DIR_A)], [objlink_key(DIR_A, "x.bin")]),
                   (0x01, [comp_table(DIR_B)], [dir_key("y.bin"), ENTRY_VALUE])])
    rc, out, err = run(monkeypatch, log_of(tmp_path, [blk]), "mlog", "--json", paths=PATHS)
    e = json.loads(out)["Transactions"][0]["Entries"]
    assert e["Removed"] == [{"ParentOID": "0x700", "Name": "x.bin"}] and e["Added"] == [{"ParentOID": "0x800",
                                                                                          "Name": "y.bin"}], e


@pytest.mark.parametrize("vals", [
    [b"\x05\x00\x00\x00\x08\x00\x00\x00", b"\0" * 2],                    # a path count with no array behind it
    [b"\0" * 3, b"\x30\x00"],                                               # values too short to read
    [struct.pack("<IIII", 1, 8, 0x1000, 28), dir_key("b.bin")]])              # a component past the value
def test_review_17e_a_damaged_reparent_is_read_without_a_crash(monkeypatch, tmp_path, vals):
    blk = _blocks([(0x05, [comp_table(DIR_A), comp_row("a.bin")], vals)])
    rows, out = _parse(monkeypatch, tmp_path, blk)
    assert len(rows) == 1 and rows[0][0] not in ("RENAME", "MOVE", "MOVE_AND_RENAME"), (rows, out[-2500:])


def test_review_6_a_control_character_in_a_name_is_escaped(monkeypatch, tmp_path):
    """A crafted name with a newline must not break the one-row-per-line text."""
    rows, out = _parse(monkeypatch, tmp_path, _blocks(_rename_txn(DIR_A, "a\nb.txt", 4, "c.txt")))
    assert [a for a, _ in rows] == ["RENAME"], (rows, out[-2500:])
    assert "a\\x0ab.txt → c.txt" in rows[0][1], rows


def test_self_review_4_a_link_row_carried_into_the_next_block_still_pairs(monkeypatch, tmp_path):
    """The file's `$OBJ_LINK` delete closes one redo block and its path-less insert opens the next block of the same
    transaction (no transaction start): the insert takes the carried path, and the pair holds."""
    d, n = DIR_A, "t.bin"
    t2 = [rec(0x02, [comp_table(d)], [dir_key(n, 2)], flags=1),
          rec(0x02, [comp_table(d), comp_fid(4, d)], [objlink_key(d, n)], flags=0)]
    t2b = [rec(0x01, [], [objlink_key(DIR_B, n), objlink_value(DIR_B, n)], flags=0),
           rec(0x01, [comp_table(DIR_B)], [dir_key(n, 2), ENTRY_VALUE], flags=2)]
    rows, out = _parse(monkeypatch, tmp_path, _blocks(split_txn(d, n, 4)) + [t2, t2b])
    assert [a for a, _ in rows] == ["MOVE"], (rows, out[-2500:])
    assert "parent 0x700 → 0x800" in rows[0][1], rows

