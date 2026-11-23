"""The code half, group 2 (deleted / Trash), 1.14.0: PLAN section 10.2 E, RUNNING_LOG N555, N528, N531.

  10.2 E  the `deleted` view as drafted and accepted (the maintainer, 2026-11-11: "I think it is better, yes"): per page
          scan a status x recoverability table first, then one line per entry -- RECOVER, CREATED, NAME, FOUND IN --
          with the details under `-v` (`RC1D/G2/DRAFT_DELETED_VIEW_2026-11-11.md`, `RC1D/G2/DESIGN.md` section 3).
  N555    (b) a Trash row's key is the object's own reference {+0x00, +0x08} (two static readings,
          `RC1D/G2/TRASH_KEY_READING_1.md` / `_2.md`; 3 of 3 deletions on disk), so its ObjectRef is
          `<+0x08>:<+0x00>` -- a file's `<directory>:<ordinal>`, a directory's `<oid>:0x0`; 1.14.0-dev wrote
          `<+0x08>:0x0`, the file's DIRECTORY. (a) the walk's Trash set is empty at every caller, so its deleted mark
          (body file, `details`, `search`, `files`' "(N deleted)") never fired: removed.
  N528    `help deleted`'s example said `deleted --full` carves: a view carves nothing.
  N531    `help deleted` and the footer called plain `deleted` "seconds": 197.5 s and 401.0 s were measured on the two
          volumes with the most files (`LD/evidence/hc_timing.txt`).

Written RED before the fix (the run is recorded in `analysis/reports/v1.13.2/RC1D/G2/`). Volumes: the synthetic builder
of `test_1132_red_b2_deleted.py`; no corpus image.
"""
import csv
import inspect
import os
import re
import struct
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forefst as F                                      # noqa: E402
import test_1132_red_b2_deleted as D                     # noqa: E402  (DirVol, rows, the runners)

_T, _S = D._T, D._S
_row, _name_key, _file_value, _dir_value = D._row, D._name_key, D._file_value, D._dir_value
_syn, _syn_csv, _ctx = D._syn, D._syn_csv, D._ctx

_STATUSES = ("DELETED", "DELETED, OR RENAMED", "RENAMED", "SAME FILE, OTHER CREATION TIME", "STILL PRESENT")
_TABLE_ROW = re.compile(r"^\s+(DELETED, OR RENAMED|DELETED|RENAMED|SAME FILE, OTHER CREATION TIME|STILL PRESENT)"
                        r"[^\d\n]*?((?:\s+\d+\*?){6})\s*$", re.M)


def _iso(t):
    return F.ft_iso(t)


def _table(out):
    """{status: (bytes in the row, carve possible, metadata only, directory, empty, total)} of the first table; a
    starred count reads as its number, and the stars are returned apart."""
    i = out.find("What was found, and what can be recovered")
    assert i >= 0, "no status x recoverability table" + _ctx(0, out)
    res, stars = {}, set()
    for m in _TABLE_ROW.finditer(out[i:]):
        if m.group(1) in res:
            break
        cells = m.group(2).split()
        res[m.group(1)] = tuple(int(c.rstrip("*")) for c in cells)
        stars |= {(m.group(1), k) for k, c in enumerate(cells) if c.endswith("*")}
    return res, stars


def _status_section(out, status):
    """The lines of the one-line section of `status` (its head `── <STATUS>: N (...) ──`, up to the next head or a
    blank line)."""
    m = re.search(r"^  ── " + re.escape(status) + r": (\d+) \(", out, re.M)
    assert m, "no section for %s" % status + _ctx(0, out)
    rest = out[m.end():].split("\n")[1:]
    lines = []
    for ln in rest:
        if not ln.strip() or ln.startswith("  ──") or not ln.startswith("    "):
            break
        lines.append(ln)
    return int(m.group(1)), lines


def _header(lines):
    return next(ln for ln in lines if "RECOVER" in ln and "CREATED" in ln)


def _entries(lines):
    """[(name, (recover, created, found in, the notes after it))] of a section's one-line entries, read at the columns
    its header line gives (RECOVER  CREATED  NAME  FOUND IN: the maintainer, 2026-11-14, "Ok for name first"); the
    order kept."""
    hdr = _header(lines)
    ci, ni, fi = hdr.index("CREATED"), hdr.index("NAME"), hdr.index("FOUND IN")
    res = []
    for ln in lines:
        if ln is hdr or not ln.startswith("    ") or ln[4] == " ":
            continue
        found, _, note = ln[fi:].partition("  [")
        res.append((ln[ni:fi].rstrip(), (ln[4:ci].rstrip(), ln[ci:ni].strip(), found.rstrip(),
                                         ("[" + note) if note else "")))
    return res


# ═══ a volume with one entry of each kind the builder can make ═══════════════════════════════════════════════

@pytest.fixture(scope="module")
def vw(tmp_path_factory):
    """Root 0x600 with two live directories (keep 0x701, newdir 0x762) and, in its page's free space: 'olddir' (a
    directory, OID 0x750 -- below the highest live OID, so checkable (E66) -- live nowhere: DELETED), 'gone.bin' (a split file row 0x600:0x5, live nowhere: DELETED, no
    extent map: metadata only), 'oldname' (OID 0x762, live as newdir: RENAMED) and 'keep' (a copy of the live row:
    STILL PRESENT). Runs `deleted` and `deleted -v` once each."""
    v = D.DirVol()
    v.objects = v.tree({0x600: {"name": "",
                                "slack": [_row(_name_key("olddir"), _dir_value(0x750, _T + 1 * _S)),
                                          _row(_name_key("gone.bin"), _file_value(5, 0x600, _T + 2 * _S)),
                                          _row(_name_key("oldname"), _dir_value(0x762, _T + 3 * _S)),
                                          _row(_name_key("keep"), _dir_value(0x701, _T))]},
                        0x701: {"parent": 0x600, "name": "keep"},
                        0x762: {"parent": 0x600, "name": "newdir"}})
    path = v.write(str(tmp_path_factory.mktemp("g2view") / "target.raw"))
    rc, out, err = _syn(path, "deleted")
    rcv, outv, errv = _syn(path, "deleted", "-v")
    return {"rc": rc, "out": out, "err": err, "rcv": rcv, "outv": outv, "errv": errv}


def test_g2_view_table_counts_every_status_by_what_can_be_recovered(vw):
    """The table (all five statuses, zeros shown): DELETED 1 metadata only + 1 directory; RENAMED 1 directory; STILL
    PRESENT 1 directory; the other two 0."""
    assert vw["rc"] == 0, _ctx(vw["rc"], vw["out"], vw["err"])
    t, _ = _table(vw["out"])
    assert set(t) == set(_STATUSES), (t, _ctx(0, vw["out"]))
    assert t["DELETED"] == (0, 0, 1, 1, 0, 2), t
    assert t["RENAMED"] == (0, 0, 0, 1, 0, 1), t
    assert t["STILL PRESENT"] == (0, 0, 0, 1, 0, 1), t
    assert t["DELETED, OR RENAMED"] == t["SAME FILE, OTHER CREATION TIME"] == (0, 0, 0, 0, 0, 0), t


def test_g2_view_table_comes_before_the_entries_and_the_rollup_is_gone(vw):
    """The table is printed before the first entry section; the roll-up paragraph that repeated its counts ("Content of
    the DELETED, ... entries (N): ...") is not printed any more, in either view."""
    out = vw["out"]
    assert out.find("What was found, and what can be recovered") < out.find("  ── DELETED: "), _ctx(0, out)
    for o in (vw["out"], vw["outv"]):
        assert "Content of the DELETED" not in o and "STILL PRESENT entries (" not in o, _ctx(0, o)


def test_g2_view_one_line_per_entry_recover_created_name_found_in(vw):
    """DELETED: 2 -- 'gone.bin' (metadata only) before 'olddir' (directory): the table's column order; each line its
    recoverability, the row's creation time, its name, then the directory whose page held it ('.', the root): NAME
    before FOUND IN (the maintainer, 2026-11-14), so a deep folder path does not push the name to the right."""
    n, lines = _status_section(vw["out"], "DELETED")
    hdr = _header(lines)
    assert hdr.split() == ["RECOVER", "CREATED", "NAME", "FOUND", "IN"], hdr
    ents = _entries(lines)
    assert n == 2 and [e[0] for e in ents] == ["gone.bin", "olddir"], (n, lines)
    d = dict(ents)
    assert d["gone.bin"][:3] == ("metadata only", _iso(_T + 2 * _S), "."), d
    assert d["olddir"][:3] == ("directory", _iso(_T + 1 * _S), "."), d


def test_g2_view_renamed_line_names_the_live_file(vw):
    """RENAMED: 'oldname' is live as 'newdir': the line says so after the name."""
    n, lines = _status_section(vw["out"], "RENAMED")
    d = dict(_entries(lines))
    assert n == 1 and "oldname" in d, lines
    assert d["oldname"][0] == "directory" and d["oldname"][3].startswith("[now: newdir"), d


def test_g2_view_details_only_under_v(vw):
    """The default view prints no per-entry block ('Found in a page of', 'Recoverable:'), and a line that says what
    -v adds; `deleted -v` prints the table and every entry's block."""
    out, outv = vw["out"], vw["outv"]
    assert "Found in a page of" not in out and "Recoverable:" not in out, _ctx(0, out)
    assert re.search(r"^\s+-v: .*locator.*both times.*copies", out, re.M), _ctx(0, out)
    assert vw["rcv"] == 0 and "What was found, and what can be recovered" in outv, _ctx(vw["rcv"], outv, vw["errv"])
    assert "Found in a page of: ." in outv and "Recoverable: directory entry" in outv, _ctx(0, outv)


def test_g2_view_no_recover_line_when_nothing_holds_content(vw):
    """No entry holds bytes or an extent map: no 'To recover:' line (it would promise content)."""
    assert "To recover:" not in vw["out"], _ctx(0, vw["out"])


def test_g2_footer_makes_no_seconds_claim(vw):
    """N531: plain `deleted` is not 'quick, seconds' (197.5 s and 401.0 s measured on the volumes with the most files)."""
    foot = vw["out"][vw["out"].find("── Recovery methods"):]
    assert "── Recovery methods" in vw["out"] and "seconds" not in foot, foot


def test_g2_view_columns_cover_every_verdict():
    """Each verdict `_deleted_recoverability` returns lands in one column of the table: inline bytes (a live file's
    starred), a carve, metadata only, a directory, empty."""
    want = {"recoverable_inline": 0, "live_file_inline": 0, "extent_backed": 1, "map_not_carveable": 2,
            "metadata_only": 2, "content_zero_or_absent": 2, "live_file_map": 2, "fragment_only": 2, "directory": 3,
            "empty": 4, "empty_symlink": 4}
    assert F._VIEW_COLUMN == want, F._VIEW_COLUMN
    assert F._VIEW_STARRED == {"live_file_inline"}, F._VIEW_STARRED


# ═══ N555 (b): the Trash row's ObjectRef ═════════════════════════════════════════════════════════════════════

def _trash_vol(tmp_path, key):
    v = D.DirVol()
    v.objects = v.tree({0x600: {"name": ""}, 0xD: {"files": [_row(key, b"\x11" * 0x30)]}})
    return v.write(str(tmp_path / "target.raw"))


def _trash_text(out):
    i = out.find("── Trash Table")
    assert i >= 0, _ctx(0, out)
    return out[i:out.find("\n\n", i)]


@pytest.mark.parametrize("key,ref", [
    (struct.pack("<QQ", 2, 0x70B), "0x70b:0x2"),          # LAB-L's t_snap.bin, key {2, 0x70b} (labL_5 #1068)
    (struct.pack("<QQ", 0, 0x705), "0x705:0x0"),          # a directory: {0, its own OID} (both readings)
])
def test_g2_trash_row_object_ref_is_the_objects_reference(tmp_path, key, ref):
    """The text and the CSV give the Trash row's ObjectRef as `<+0x08>:<+0x00>` (not `<+0x08>:0x0`, nor 'OID')."""
    path = _trash_vol(tmp_path, key)
    rc, out, err = _syn(path, "deleted", "--trash")
    keyline = [ln for ln in _trash_text(out).splitlines() if ln.strip().startswith("Key (")]
    assert rc == 0 and len(keyline) == 1 and ("(ObjectRef %s)" % ref) in keyline[0] and "(OID " not in keyline[0], \
        _ctx(rc, out, err)
    rc, out, err, rows = _syn_csv(path, "deleted", "--no-slack")
    tr = [r for r in rows if r["RecoverySource"] == "Trash table"]
    assert len(tr) == 1 and tr[0]["ObjectRef"] == ref and tr[0]["RawKey"] == key.hex(), (tr, _ctx(rc, out, err))


def test_g2_trash_row_with_another_key_length_has_no_object_ref(tmp_path):
    """A key that is not 16 bytes is not a reference: no ObjectRef, the raw key kept."""
    key = struct.pack("<QI", 2, 0x70B)
    path = _trash_vol(tmp_path, key)
    rc, out, err, rows = _syn_csv(path, "deleted", "--no-slack")
    tt = _trash_text(out)
    tr = [r for r in rows if r["RecoverySource"] == "Trash table"]
    assert rc == 0 and "ObjectRef" not in tt and len(tr) == 1 and tr[0]["ObjectRef"] == "" \
        and tr[0]["RawKey"] == key.hex(), (tt, tr)


# ═══ N555 (a): the dead deleted-mark paths ═══════════════════════════════════════════════════════════════════

def test_g2_walk_takes_no_trash_set_and_marks_nothing_deleted():
    """`walk_directory_tree` has no Trash-set parameter (every caller passed an empty set), so no entry of the live
    walk carries a deleted mark."""
    assert "trash_set" not in inspect.signature(F.walk_directory_tree).parameters
    src = inspect.getsource(F.walk_directory_tree)
    assert '"is_deleted"' not in src and '"deletion_source"' not in src


def test_g2_listings_print_no_deleted_mark():
    """The body file's ' (deleted)', `details`' 'Is deleted', `search`'s '[DEL]' and `files`' '(N deleted)' are gone."""
    src = inspect.getsource(F)
    for gone in ('" (deleted)"', "Is deleted:", '" [DEL]"', "deleted) ->"):
        assert gone not in src, gone


def test_g2_files_done_line_counts_no_deletions(tmp_path):
    """`files`' closing line on stderr says how many entries it wrote, no deletion count."""
    v = D.DirVol()
    v.objects = v.tree({0x600: {"name": ""}, 0x701: {"parent": 0x600, "name": "keep"}})
    path = v.write(str(tmp_path / "target.raw"))
    rc, out, err = _syn(path, "files", "--csv", str(tmp_path / "f.csv"))
    done = [ln for ln in err.splitlines() if "Done." in ln]
    assert rc == 0 and done and "deleted" not in done[0], _ctx(rc, out, err)


# ═══ N528 / N531: help deleted ═══════════════════════════════════════════════════════════════════════════════

def _help():
    h = F.CMD_HELP["deleted"]
    return h, "\n".join(h["desc"])


def test_g2_help_full_example_does_not_say_the_view_carves():
    """N528: the `deleted --full` example: a view carves nothing (only `export deleted DIR` writes content)."""
    h, _ = _help()
    ex = dict(h["ex"])
    assert "deleted --full" in ex and "carve" not in ex["deleted --full"].replace("carves nothing", ""), ex


def test_g2_help_makes_no_seconds_claim_for_plain_deleted():
    """N531: plain `deleted` is neither '[FAST — seconds]' nor in the FAST list; the help says what its time follows."""
    _, desc = _help()
    assert "seconds]" not in desc and not re.search(r"FAST\s+`deleted`", desc), desc
    assert re.search(r"every live file's extent map", desc), desc


def test_g2_help_says_what_the_view_prints_and_what_v_adds():
    """The help describes the table, the one line per entry, and `-v` (accepted by `deleted`)."""
    h, desc = _help()
    opts = dict(h["opts"])
    assert any(k.startswith("-v") for k in opts), opts
    assert "table" in desc and "one line per entry" in desc, desc


# ═══ the review's findings 2 and 3 (RC1D/G2/REVIEW_AGENT.md, REVIEW_RESPONSE.md) ═════════════════════════════════

def _dvol(tmp_path, dirs):
    v = D.DirVol()
    v.objects = v.tree(dirs)
    return v.write(str(tmp_path / "target.raw"))


def test_g2_view_renamed_line_carries_each_fact_it_has(vw):
    """Review 2: a RENAMED entry whose own times differ from the live file's gives both facts after the name -- the
    live name, then the times that differ."""
    _, lines = _status_section(vw["out"], "RENAMED")
    d = dict(_entries(lines))
    assert d["oldname"][3] == "[now: newdir]  [earlier version: Created, Modified, Changed, Accessed differ]", d


def test_g2_view_same_file_line_names_the_live_files_creation_time(tmp_path):
    """Review 2: a split row of the live file a.txt (0x761:0x5) with another creation time -- SAME FILE, OTHER CREATION
    TIME -- gives the live file's creation time after the name."""
    path = _dvol(tmp_path, {0x600: {"name": ""},
                            0x761: {"parent": 0x600, "name": "d",
                                    "files": [_row(_name_key("a.txt"), _file_value(5, 0x761, _T))],
                                    "slack": [_row(_name_key("a.txt"), _file_value(5, 0x761, _T + 400 * _S))]}})
    rc, out, err = _syn(path, "deleted")
    n, lines = _status_section(out, "SAME FILE, OTHER CREATION TIME")
    d = dict(_entries(lines))
    assert rc == 0 and n == 1 and d["a.txt"][1] == _iso(_T + 400 * _S), (d, _ctx(rc, out, err))
    assert d["a.txt"][3].startswith("[live file created %s]" % _iso(_T)), d


@pytest.fixture(scope="module")
def carv(tmp_path_factory):
    """/d's page holds, in its free space, two deleted embedded rows whose holder maps 3 written clusters each (a carve
    can use the map): user.bin, and FVE2.{0} -- system churn by `_deleted_category`."""
    import test_1132_red_b2_carve as C
    import test_1132_d2_carve_extract as X
    rows = []
    for name, lcn in (("user.bin", 0x40), ("FVE2.{0}", 0x48)):
        hv = C.holder_value(3 * C.CS, 3 * C.CS, [C.ext_row(lcn, 0, 3, C.W)])
        rows.append(_row(_name_key(name), C.long_row([(C.key80(0x1000), hv)], size=3 * C.CS, alloc=3 * C.CS)))
    return X._vol(tmp_path_factory.mktemp("g2carve"), {0x600: {"name": ""},
                                                        0x761: {"parent": 0x600, "name": "d", "slack": rows}})


@pytest.mark.parametrize("args,cmd,n", [
    ((), "export deleted DIR --carve", 2),
    (("--no-system",), "export deleted DIR --carve --no-system", 1),
    (("--search", "user"), "export deleted DIR --carve --search user", 1),
], ids=["all", "no-system", "search"])
def test_g2_to_recover_counts_what_the_export_writes(carv, tmp_path, args, cmd, n):
    """Review 3: `To recover:` names the export for the run's options and counts what it writes -- the system churn
    left out under --no-system, the --search filter applied -- and that export, run, writes that many carves."""
    rc, out, err = _syn(carv, "deleted", *args)
    tr = [ln for ln in out.splitlines() if ln.startswith("  To recover:")]
    assert rc == 0 and tr == ["  To recover: `%s` carves the %d whose extent map survives (best effort)." % (cmd, n)], \
        (tr, _ctx(rc, out, err))
    d = str(tmp_path / "exp")
    rc2, out2, err2 = _syn(carv, "export", "deleted", d, *cmd.split()[3:])
    cdir = os.path.join(d, "content")
    carved = sorted(f for f in os.listdir(cdir) if f.endswith(".carved")) if os.path.isdir(cdir) else []
    assert rc2 in (0, 2) and len(carved) == n, (carved, _ctx(rc2, out2, err2))
