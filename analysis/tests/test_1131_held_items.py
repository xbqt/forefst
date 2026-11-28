"""1.13.1 item 7 -- the findings held at v1.13.0, each with the RED case that shows it on 1.13.0."""
import re

import forefst as F


# K172 -- a bare CLOSE was '0x80000000' in CSV/JSON and 'CLOSE' in --list: one record, two readings
def test_k172_bare_close_is_named_in_both_renderers():
    assert F.usn_reason_to_short(0x80000000) == "CLOSE"
    assert F.usn_reason_to_str(0x80000000) == "CLOSE"


def test_k172_an_unrecognised_reason_bit_is_shown_not_dropped():
    known = 0
    for b in F.USN_REASON_FLAGS:
        known |= b
    unk = next(1 << i for i in range(31) if not (1 << i) & known)
    # acceptance 1.14.0 (K14 / K16): the residual bit in the names, unpadded (`FILE_CREATE|0x8`)
    for render in (F.usn_reason_to_short, F.usn_reason_to_str):
        assert ("0x%x" % unk) in render(0x100 | unk).split("|"), render.__name__


def _fresh_registers(monkeypatch):
    """N420 (LB55): empty run registers for one node, restored by monkeypatch. The K173 nodes' journal notes (an
    expected data condition) went into the real `_SKIP_EXPECTED`, so the pytest process printed them at exit."""
    for name in ("_FINDINGS", "_SKIP_NOTES", "_SKIP_EXPECTED", "_SKIP_FINDING"):
        monkeypatch.setattr(F, name, type(getattr(F, name))())


# K173 -- the "non-zero byte(s)" count added 8 per skipped WORD, zero bytes included, and blamed a torn record
def test_k173_unparseable_journal_bytes_are_counted_as_bytes_not_words(capsys, monkeypatch):
    _fresh_registers(monkeypatch)                       # N420 (LB55): the note stays inside this node
    junk = bytes([0x41, 0, 0, 0, 0, 0, 0, 0]) * 3      # low u32 = 0x41: not a record length; 3 bytes non-zero
    F.parse_usn_records(junk + b"\0" * 4096)           # room enough that the scan reaches every junk word
    err = capsys.readouterr().err
    assert "3 non-zero byte(s)" in err, err             # 1.13.0 said 24
    assert "0x0+24" in err, err                         # one region, its offset and length printed
    assert "torn record at the write head" not in err


# K192 -- the path map read value+0x40 as the attribute field on EVERY row; on the embedded form it is +0x48
def test_k192_name_row_attributes_come_from_the_rows_own_layout():
    import struct
    short = bytearray(0x50); struct.pack_into("<I", short, 0x40, 0x10000000)            # <= 84 B: attrs @ +0x40
    embedded = bytearray(0xA8); struct.pack_into("<I", embedded, 0x40, 0x324A72C5)       # noise with bit 28 set
    struct.pack_into("<I", embedded, 0x48, 0x20)                                          # the real attrs: Archive
    assert F._name_row_attrs(bytes(short)) & 0x10000000                                   # a directory
    assert not (F._name_row_attrs(bytes(embedded)) & 0x10000000)                          # a FILE, not noise


# K086 -- forefst's walker copy had no cycle guard: a child pointing back at an ancestor recursed to RecursionError
def test_k086_walker_terminates_on_a_cyclic_tree(monkeypatch):
    def cyclic_entries(f, ps, cs, tr, vlcns, oid=None):
        other = 0x702 if oid == 0x701 else 0x701                        # each directory contains the other
        return [{"name": "d%x" % other, "is_dir": True, "child_oid": other, "resident": False,
                 "file_size": 0, "raw_value": b"", "create_time": 0, "modify_time": 0, "change_time": 0,
                 "access_time": 0, "file_attrs": 0x10000000, "flags": 0, "home_oid": 0, "file_id": 0,
                 "value_len": 0, "ads": []}]
    monkeypatch.setattr(F, "_parse_dir_entries", cyclic_entries)
    results = []
    F._walk_dir_tree(None, 0, 4096, None, {0x701: [1], 0x702: [2]}, 0x701, "", 0, F.DEFAULT_DEPTH, results)
    assert len(results) <= 4                                             # 1.13.0: RecursionError after 998 rows


# K098 -- the v3.4 $DATA row has its own key (`<id> | 80 00 | 00 00 00 00`), so the size lookup returned 0 for
# every embedded v3.4 file. Fixing the SIZE must not move the B2 gate, which decides that such a record's data
# is in extents: in 1.13.0 that gate tested "the lookup returned 0", and the first K098 build turned it off on
# every v3.4 volume (1,939 records) and on the two volumes upgraded from one (514) -- `extract`/`dataruns`
# found no extents and the walker called every such file resident.
def test_k098_size_is_read_and_the_extent_backed_verdict_survives():
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("step1/win10refsmini.raw")
    if img is None:
        import pytest
        pytest.skip("win10refsmini.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        ents = [e for e in F.walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, F.DEFAULT_DEPTH, False)
                if not e.get("is_dir")]
        assert len(ents) == 8
        assert all(e["file_size"] > 0 for e in ents), "K098: the v3.4 size is read, not 0"
        assert not [e["name"] for e in ents if e["is_resident"]], "B2: an extent-backed v3.4 file is not resident"
        assert all(e["data_form"] == F.DATA_EXTENTS for e in ents)
        decoded = []
        for oid in sorted({e["parent_oid"] for e in ents}):
            decoded += [i for i in F._analyze_dir_extents(f, ps, cs, tr, obj_map, oid) if i.get("extents")]
        assert len(decoded) == 8, "dataruns/extract must reach all 8 extent maps (1.13.0: 8)"
    finally:
        f.close()


# K097 -- `refsanalysis files -v` printed a split name's CACHED size, stale on hard-linked names (55 rows,
# 5 volumes); `files`, `attributes` and `details` report the object's own. Now all four agree.
def test_k097_refsanalysis_files_prints_the_objects_size_not_the_names_cached_copy():
    import os, re, subprocess, sys
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("win11refs2tspecials.raw")
    if img is None:
        import pytest
        pytest.skip("win11refs2tspecials.raw not in this tree")
    ra = os.path.join(os.path.dirname(F.__file__), "refsanalysis.py")
    out = subprocess.run([sys.executable, "-B", ra, img, "files", "-v"], capture_output=True, text=True,
                         timeout=900).stdout
    row = [l for l in out.splitlines() if l.startswith("  FILE") and l.endswith("/papa_victor_867137.csv")]
    assert len(row) == 1, row
    assert re.search(r"\s479429 \d{4}-", row[0]), row[0]         # 1.13.0: 293302, the name's cached copy


# K095 -- `files` paired the $DATA descriptor's size with the name-row header's allocation. The header is a
# cached copy; on 3 records (real installations) it is stale, and the row read 3,271,312 bytes in 3,211,264.
def _k095_record(h58, h60, size, total, disk, monkeypatch):
    import struct
    vd = bytearray(0xA8)
    struct.pack_into("<QQ", vd, 0x58, h58, h60)
    key = b"\x00" * 12 + b"\x80\x00" + b"\x00\x00" + struct.pack("<Q", 0x1000)     # current stream, sub_id 0x1000
    row = bytearray(0x50)
    struct.pack_into("<I", row, 0x04, F.SNAP_DATA_DESC)
    struct.pack_into("<QQ", row, 0x30, total, size)
    struct.pack_into("<Q", row, 0x48, disk)
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda v, ctx=None: [(key, bytes(row))])
    sz, tot, dsk, form = F._resident_data_sizes(bytes(vd))
    return sz, F._reported_alloc(bytes(vd), sz, tot, dsk, form)


def test_k095_a_stale_header_allocation_is_not_paired_with_the_current_size(monkeypatch):
    # the audit's witness, winsider wpndatabase.db-wal: header 3,188,912/3,211,264, descriptor 3,271,312/3,276,800
    assert _k095_record(3188912, 3211264, 3271312, 3276800, 3276800, monkeypatch) == (3271312, 3276800)


def test_k095_a_current_header_keeps_its_own_allocation(monkeypatch):
    # snapshotted file: blocks shared, total 12,288 / disk 8,192; the header follows total -- and is kept
    assert _k095_record(9296, 12288, 9296, 12288, 8192, monkeypatch) == (9296, 12288)
    # sparse file: the header follows disk_alloc -- kept too; neither descriptor field would reproduce both
    assert _k095_record(13631488, 5242880, 13631488, 13631488, 5242880, monkeypatch) == (13631488, 5242880)


def test_k095_a_stale_header_with_an_ambiguous_descriptor_reports_unknown(monkeypatch):
    assert _k095_record(100, 4096, 9296, 12288, 8192, monkeypatch) == (9296, None)


# K041 -- a bootstrap copy with a zeroed self-reference failed its checksum for that reason alone, so a copy
# damaged BEYOND it printed the same line. Restoring the own-LCN and re-verifying tells the two apart.
def _k041_page(own_lcn, cs=4096):
    import hashlib, struct
    b = bytearray(cs)
    b[0:4] = b"CHKP"
    struct.pack_into("<Q", b, 0x20, own_lcn)                    # the header's self-reference
    b[0x200:0x210] = b"payload-payload!"
    # N335 (decision 27.5), a fixture correction: a CHKP declares its self-descriptor in its header (CHKP+0x58 offset,
    # +0x5C length), and one that declares none (pointer 0/0) fails its self-checksum, as in the 26100 driver. This
    # page used to put its descriptor at +0x50, over the pointer, which then read 0/0 and sent the tool to its old
    # descriptor scan; it now sits where a CHKP keeps it (+0xE0) and the header declares it.
    d = 0xE0                                                     # self-descriptor: SHA-256, 32-byte digest
    struct.pack_into("<II", b, 0x58, d, 0x48)                    # declared: offset 0xE0, length 0x48
    b[d + 0x22] = 4; b[d + 0x23] = 8; struct.pack_into("<I", b, d + 0x24, 32)
    z = bytearray(b); z[d:d + 0x48] = b"\0" * 0x48               # the window zeroed before hashing
    b[d + 0x28:d + 0x48] = hashlib.sha256(bytes(z)).digest()
    return b


def test_k041_a_zeroed_self_reference_alone_verifies_once_restored():
    page = _k041_page(0x27d0)
    assert F._verify_self_checksum(bytes(page), 4096)[0] is True
    page[0x20:0x28] = b"\0" * 8                                  # the CTF image's damage
    assert F._verify_self_checksum(bytes(page), 4096)[0] is False
    assert F._verify_with_own_lcn(bytes(page), 4096, 0x27d0) is True
    assert "only its self-reference" in F._restored_note({"cksum_ok_restored": True})


def test_k041_damage_beyond_the_self_reference_is_reported_as_such():
    page = _k041_page(0x27d0)
    page[0x20:0x28] = b"\0" * 8
    page[0x0c] ^= 0x01                                           # the audit's flip, at +0x0C
    assert F._verify_with_own_lcn(bytes(page), 4096, 0x27d0) is False     # 1.13.0 printed the same line
    assert "beyond its self-reference" in F._restored_note({"cksum_ok_restored": False})


# K072 -- `<oid 0x..>` is documented as "the directory is gone"; 8,931 winsider records wore it over a parent
# still in the Object Table (unlinked, not reclaimed). And a root child's path lacked the leading '/'.
def test_k072_a_live_but_unlinked_parent_is_not_labelled_gone():
    paths = {0x600: "/", 0x701: "/Users"}
    live = {0x600: [1], 0x701: [2], 0x807: [3]}
    assert F._usn_resolve_path(0x807, paths, live) == "<unlinked 0x807>"
    assert F._usn_resolve_path(0x9999, paths, live) == "<oid 0x9999>"          # absent: the documented meaning
    assert F._usn_resolve_path(0x701, paths, live) == "/Users"


def test_k072_a_root_child_gets_the_same_leading_slash_as_every_other_path():
    # acceptance 1.14.0 (K22): every path in `files`' FullPath form -- no leading '/', the root '.', a root child its
    # bare name (the one form K072 asked for, now without the slash); a '/' parent is the root too
    assert F._usn_full_path(".", "pagefile.sys") == "pagefile.sys"
    assert F._usn_full_path("/", "pagefile.sys") == "pagefile.sys"
    assert F._usn_full_path("Users", "a.txt") == "Users/a.txt"
    assert F._usn_full_path("", "x") == "x"
    assert F._usn_full_path(".", ".") == "."                                    # the root's own records


# K066 -- `summary` printed the allocator's unallocated count as "free". Windows' own fsutil output for this
# volume (transcripts/win10testchecksum.txt): total 507,904, free 244,188, reserved 83,232.
def test_k066_used_is_windows_figure_and_the_rest_is_not_called_free():
    import os, subprocess, sys
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("step1/win10refsmini.raw")
    if img is None:
        import pytest
        pytest.skip("win10refsmini.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        c = F.alloc_capacity(f, ps, cs, tr, roots)
    finally:
        f.close()
    assert c["covered_clusters"] == 507904                        # Windows' Total Clusters
    assert c["used_clusters"] == 507904 - 244188 - 83232          # Windows' used, exactly (180,484)
    assert c["free_clusters"] == 244188 + 83232                   # free PLUS reserved -- not Windows' free
    out = subprocess.run([sys.executable, "-B", os.path.join(os.path.dirname(F.__file__), "forefst.py"), img,
                          "summary"], capture_output=True, text=True, timeout=600).stdout
    line = [l for l in out.splitlines() if "Space used:" in l]
    assert line and "not allocated" in line[0] and " free" not in line[0], line


# K006 -- a split file's attributes are its backing's (+0x48), not the name row's cached +0x40. The journal settles
# it: the latest USN record matches the backing on 79/79 differing names over two volumes, the name row on 0.
def test_k006_a_split_files_attributes_come_from_its_own_record():
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("win11refstestmftecmd.raw")
    if img is None:
        import pytest
        pytest.skip("win11refstestmftecmd.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        hit = [e for e in F.walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, F.DEFAULT_DEPTH, True)
               if e.get("name") == "xbpt_hardlink_tango_460823.xml"]
    finally:
        f.close()
    assert hit, "witness name not found"
    # name row +0x40 = 0x20 (Archive), backing +0x48 = 0, the latest USN record 0x80 (NORMAL: no attribute)
    assert all(e["file_attrs"] & 0x20 == 0 for e in hit), [hex(e["file_attrs"]) for e in hit]


# Option C (maintainer's decision, 2026-09-24) -- timestomp's hard-link grouping keyed on RECORD PLACEMENT, and its
# storage column on DATA RESIDENCY. 1.13.0 used one flag for both: correcting the column (split files whose data is
# inline) would have removed 565 of 1,938 multi-name groups from the divergence check.
def test_hardlink_groups_key_on_placement_not_on_residency():
    rows = [
        {"placement": "split", "resident": True, "home_oid": 0x70b, "file_id": 7, "path": "t15/linked.bin"},
        {"placement": "split", "resident": True, "home_oid": 0x70b, "file_id": 7, "path": "t15/linked_alias.bin"},
        {"placement": "split", "resident": False, "home_oid": 0x706, "file_id": 3, "path": "d1/big_link.bin"},
        {"placement": "embedded", "resident": True, "home_oid": 0x701, "file_id": 9, "path": "small.txt"},
        {"placement": "split", "is_dir": True, "home_oid": 0, "file_id": 0, "path": "d1"},
    ]
    g = F._hardlink_groups(rows)
    assert sorted(len(v) for v in g.values()) == [1, 2]          # 1.13.0's filter kept only big_link.bin
    assert {r["path"] for r in g[(0x70b, 7)]} == {"t15/linked.bin", "t15/linked_alias.bin"}


def test_a_split_file_with_inline_data_is_walked_as_inline_and_still_grouped():
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("lab314_main.raw")
    if img is None:
        import pytest
        pytest.skip("lab314_main.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        rows = []
        F._walk_dir_tree(f, ps, cs, tr, obj_map, 0x600, "", 0, F.DEFAULT_DEPTH, rows)
    finally:
        f.close()
    pair = [r for r in rows if r["path"].endswith(("t15/linked.bin", "t15/linked_alias.bin"))]
    assert len(pair) == 2
    assert all(r["placement"] == "split" and r["resident"] for r in pair)   # `files`: split / inline
    groups = F._hardlink_groups([r for r in rows if r["type"] == "FILE"])
    assert any(len(v) == 2 and set(map(id, v)) == set(map(id, pair)) for v in groups.values())


# K173, second pass (the sample-golden critic): a zero low half with written bytes after it, and the tail the loop
# never reaches, were not counted -- 117 bytes on win11refstestmftecmd.
def test_k173_half_zero_words_and_the_unscanned_tail_are_counted(capsys, monkeypatch):
    _fresh_registers(monkeypatch)                       # N420 (LB55): the note stays inside this node
    half = bytes(4) + b"\x01\x02\x03\x00"                     # low u32 0, high half written: 3 non-zero bytes
    tail = b"\x00" * 16 + b"\x05" * 8                         # inside the last 80 bytes: 8 non-zero bytes
    F.parse_usn_records(b"\0" * 64 + half + b"\0" * 4096 + tail)
    err = capsys.readouterr().err
    assert "11 non-zero byte(s)" in err, err


# The corpus-golden accounting (1.13.1) found three integrity-verifier defects that made "every checksummed cluster
# matches" claim more than was checked. Each case below fails on the build before the fix.
def _integrity_holder(rows, index_rows, clusters=4, cs=4096):
    """A synthetic current-stream holder: extent node at +0x88, `rows` = [(vlcn, fvcn, crc)] in physical slots of
    28 bytes (8-byte step 32), and a key index naming only the slots listed in `index_rows`."""
    import io, struct
    N, step = 0x88, 32
    node = bytearray(0x28 + step * len(rows) + 4 * len(index_rows))
    struct.pack_into("<I", node, 0, 0x28)
    for i, (vlcn, fvcn, crc) in enumerate(rows):
        o = 0x28 + step * i
        struct.pack_into("<QHHIII", node, o, vlcn, 0x0090, 28, fvcn, 0, 1)     # flags CRC|written, size 28, run 1
        struct.pack_into("<I", node, o + 24, crc)
    idx = 0x28 + step * len(rows)
    struct.pack_into("<III", node, 0x10, idx, len(index_rows), 0)
    struct.pack_into("<I", node, 0x20, idx + 4 * len(index_rows))
    for j, slot in enumerate(index_rows):
        struct.pack_into("<HH", node, idx + 4 * j, 0x28 + step * slot, 0)
    v = bytearray(N) + node
    struct.pack_into("<II", v, 0, N, F.SNAP_DATA_DESC)
    key = b"\x00" * 12 + b"\x80\x00" + b"\x00\x00" + struct.pack("<Q", 0x1000)
    disk = bytearray(clusters * cs)
    for c in range(clusters):
        disk[c * cs:(c + 1) * cs] = bytes([0x41 + c]) * cs
    return key, bytes(v), io.BytesIO(bytes(disk)), bytes(disk)


def test_integrity_walks_the_key_index_not_the_physical_slots(monkeypatch):
    cs = 4096
    _, _, _, disk = _integrity_holder([(1, 0, 0), (2, 0, 0)], [1])
    # slot 0: a superseded row with a stale CRC; slot 1: the live row, the only one the key index names
    key, v, f, disk = _integrity_holder([(1, 0, 0xDEADBEEF), (2, 0, F._crc32c(disk[2 * cs:3 * cs]))], [1])
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None: [(key, v)])
    r = F._verify_inline_integrity(f, 0, cs, None, b"x")
    assert (r["clusters_with_crc"], r["checked"], r["ok"], r["bad_count"]) == (1, 1, 1, 0)   # 1.13.0: read the stale slot


def test_integrity_translates_a_virtual_cluster_above_the_physical_count(monkeypatch):
    cs = 4096

    class _Tr:                      # container 1 (virtual 0x100..0x1ff) maps to physical 0..
        shift, map = 8, {1: 0}
        def tr(self, vl):
            return vl & 0xFF if vl >> 8 == 1 else vl
    _, _, _, disk = _integrity_holder([(0x102, 0, 0)], [0])
    key, v, f, disk = _integrity_holder([(0x102, 0, F._crc32c(disk[2 * cs:3 * cs]))], [0])
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None: [(key, v)])
    # C2 ST-L3 (the lead, 2026-10-24; REVIEW_C2_tests N-1): the physical count this node tests against is the disk's,
    # len(disk) // cs clusters. Since wave C step C2 (B3) the tool reads the volume length from the boot sector, which
    # this synthetic disk does not hold (its fill gave a count of 5.9e17, so the node no longer caught the defect).
    # raising=False: tools from before C2 have no volume_clusters.
    ncl = len(disk) // cs
    monkeypatch.setattr(F, "volume_clusters", lambda f_, ps, cs_: ncl, raising=False)
    monkeypatch.setattr(F, "_volume_ncl", lambda f_, ps, cs_: ncl, raising=False)
    r = F._verify_inline_integrity(f, 0, cs, _Tr(), b"x")
    assert r is not None and (r["checked"], r["ok"]) == (1, 1)   # 1.13.0: vlcn 0x102 >= 4 clusters -> dropped


def test_integrity_on_the_public_sample_covers_every_crc_cluster():
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("win11refstestmftecmd.raw")
    if img is None:
        import pytest
        pytest.skip("win11refstestmftecmd.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        r = F._verify_volume_integrity_streams(f, ps, cs, tr, obj_map)
    finally:
        f.close()
    # hard-linked/moved files (their CRCs are in their own record) and multi-level extent maps included;
    # 1.13.0: 23 files, 127 of 142 checked, "every ... matches"
    assert (r["files"], r["with_crc"], r["checked"], r["ok"], r["bad"], r["unreadable"], r["unresolved"]) == \
        (189, 55586, 55586, 55586, 0, 0, 0)


def test_expected_conditions_are_not_counted_as_skipped_work(capsys):
    F._SKIP_NOTES.clear(); F._SKIP_EXPECTED.clear(); del F._SKIP_SUMMARY_DONE[:]
    F._skip_note("USN journal", "ring space", ValueError("unwritten journal ring space"), expected=True)
    F._skip_summary()
    err = capsys.readouterr().err
    assert "unit(s) of work were skipped" not in err and "describe the data" in err, err
    assert "note: USN journal: ring space" in err and "WARNING" not in err, err      # said as a note, never "skipped"
    F._SKIP_NOTES.clear(); F._SKIP_EXPECTED.clear(); del F._SKIP_SUMMARY_DONE[:]



def test_an_expected_note_does_not_use_up_the_print_budget_of_real_skips(capsys):
    """An expected note was counted in the same (stage, exception) slot as real skips: with 3 real skips
    printed, the note took count 4 (where 'further ... suppressed' is said) and returned early, so a 4th real
    skip at count 5 printed nothing and no line said it was suppressed."""
    F._SKIP_NOTES.clear(); F._SKIP_EXPECTED.clear(); del F._SKIP_SUMMARY_DONE[:]
    for i in range(3):
        F._skip_note("USN journal", "real %d" % i, ValueError("unparseable journal bytes"))
    F._skip_note("USN journal", "BEYOND", ValueError("unwritten journal ring space"), expected=True)
    F._skip_note("USN journal", "INSIDE", ValueError("unparseable journal bytes"))
    F._skip_summary()
    err = capsys.readouterr().err
    assert "further ValueError skips suppressed" in err, err
    assert "4 unit(s) of work were skipped" in err and "USN journal: 4 x ValueError" in err, err
    assert "note: USN journal: BEYOND" in err and "1 condition(s) reported above" in err, err
    F._SKIP_NOTES.clear(); F._SKIP_EXPECTED.clear(); del F._SKIP_SUMMARY_DONE[:]


def test_an_integrity_file_whose_extent_map_cannot_be_walked_in_full_is_not_reported_clean(monkeypatch):
    """A child page the walk cannot follow lowered 'carrying' and 'checked' together, so 'every ... matches'
    held. Asked about an integrity file (expect_crc), the verifier now counts the lost subtree as not verified;
    extraction (expect_crc False) is unchanged."""
    import io, struct
    cs, N = 4096, 0x88
    node = bytearray(0x28 + 0x40 + 4)
    struct.pack_into("<I", node, 0, 0x28)
    node[0x0C] = 1                                          # an INDEX node: its rows reference child pages
    ro = 0x28
    struct.pack_into("<I6H", node, ro, 0x40, 0, 0, 0, 0x10, 32, 0)     # value (child ref) at +0x10, 32 bytes
    struct.pack_into("<QQQQ", node, ro + 0x10, 0x5000, 0, 0, 0)        # a child address the map cannot translate
    idx = 0x28 + 0x40
    struct.pack_into("<III", node, 0x10, idx, 1, 0)
    struct.pack_into("<I", node, 0x20, idx + 4)
    struct.pack_into("<HH", node, idx, ro, 0)
    v = bytearray(N) + node
    struct.pack_into("<II", v, 0, N, F.SNAP_DATA_DESC)
    key = b"\x00" * 12 + b"\x80\x00" + b"\x00\x00" + struct.pack("<Q", 0x1000)

    class _Tr:
        shift, map = 8, {1: 0}
        def tr(self, vl):
            return vl & 0xFF
    monkeypatch.setattr(F, "parse_resident_btree_rows", lambda vd, ctx=None: [(key, bytes(v))])
    f = io.BytesIO(bytes(4 * cs))
    assert F._verify_inline_integrity(f, 0, cs, _Tr(), b"x") is None                      # extraction: as before
    r = F._verify_inline_integrity(f, 0, cs, _Tr(), b"x", expect_crc=True)
    assert r is not None and r["rows_unreadable"] == 1 and r["lost_subtrees"] == ["child address not mappable"]


# Round 4 (maintainer, 2026-09-24): the storage column in files' five words; allocator wording; N105 option A.
def test_the_storage_label_uses_the_same_words_as_files():
    assert F._walk_storage_word({"data_form": "snapshot-shared"}) == "(snapshot-shared)"   # 1.13.0/early 1.13.1: (extents)
    assert F._walk_storage_word({"data_form": "unallocated"}) == "(unallocated)"
    assert F._walk_storage_word({"data_form": "unknown"}) == "(unknown)"
    assert F._walk_storage_word({"resident": True}) == "(inline)"


def _sample_run(name, tool, *args):
    import os, subprocess, sys
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image(name)
    if img is None:
        import pytest
        pytest.skip("%s not in this tree" % name)
    return subprocess.run([sys.executable, "-B", os.path.join(os.path.dirname(F.__file__), tool), img] + list(args),
                          capture_output=True, text=True, timeout=900)


def test_timestomp_names_a_snapshot_shared_stream():
    import csv, io
    r = _sample_run("win11refs2tsnapshots.raw", "forefst.py", "timestomp", "--csv", "--all")
    # acceptance 1.14.0 (N313 / N314): FullPath; storage split into its two axes, the data residency `snapshot-shared`
    st = {row["FullPath"]: row["DataResidency"] for row in csv.DictReader(io.StringIO(r.stdout))}
    assert st.get("testsnapshots/lasttest.txt") == "snapshot-shared", st.get("testsnapshots/lasttest.txt")


def test_allocators_say_not_allocated_per_tier():
    r = _sample_run("step1/win10refsmini.raw", "refsanalysis.py", "allocators")
    tier = [l for l in r.stdout.splitlines() if "from rows:" in l or "from summary:" in l]
    assert tier and all("not allocated" in l and " free " not in l for l in tier), tier


def test_timeline_fileref_is_one_files_history():
    import csv, io
    r = _sample_run("lab314_main.raw", "forefst.py", "timeline", "--fileref", "0x70b:0x7", "--csv")
    rows = list(csv.DictReader(io.StringIO(r.stdout)))
    # acceptance 1.14.0 (Q-C): a row's path today (a USN row has none: its Name)
    own = [row for row in rows if row["Source"] != "MLog"]
    assert own and {row["PathToday"] or row["Name"] for row in own} == {"LAB_0906/t15/linked.bin",
                                                                        "LAB_0906/t15/linked_alias.bin"}
    # U12 (1.14.1): `--fileref` / `--id` merges the log payloads whose records name the file; a payload row shows its
    # own table (it can be the parent's), and each says how it was kept
    mlog = [row for row in rows if row["Source"] == "MLog"]
    assert mlog and all(re.search(r"\[by (its file id|one of its names)\]$", row["Event"]) for row in mlog), mlog
    assert re.search(r"timeline --id 0x70b:0x7: %d log payload rows of \d+ \(" % len(mlog), r.stderr), r.stderr[-800:]
    assert "leaves out MLog events" not in r.stderr


def test_timeline_oid_includes_the_si_events_of_files_filed_under_it():
    import csv, io
    r = _sample_run("lab314_main.raw", "forefst.py", "timeline", "--oid", "0x70b", "--source", "SI", "--csv")
    names = {row["PathToday"] for row in csv.DictReader(io.StringIO(r.stdout))}      # acceptance 1.14.0 (Q-C)
    assert "LAB_0906/t15/linked.bin" in names          # 1.13.0: a file's $SI rows carried no oid and were dropped


def test_timeline_text_header_describes_the_oid_the_si_rows_show():
    """The text-mode header said '$SI shows OID —' for files after the $SI rows began carrying the file's home
    OID; the golden runs only --csv, so it could not see the contradiction."""
    r = _sample_run("lab314_main.raw", "forefst.py", "timeline", "--fileref", "0x70b:0x7", "--source", "SI")
    rows = [l for l in r.stdout.splitlines() if "  $SI  " in l]
    assert rows and all(" 0x70b " in l for l in rows), rows
    assert "$SI shows OID —" not in r.stdout and "HOME directory's OID in $SI and USN" in r.stdout, r.stdout[:900]


def test_timeline_fileref_with_no_usn_event_does_not_call_the_journal_inactive():
    """--fileref filters USN records as they are read, so a FileRef with no USN event left the count at 0 and the
    text header claimed 'USN journal inactive on this image' over an active journal."""
    r = _sample_run("win11refstestmftecmd.raw", "forefst.py", "timeline", "--fileref", "0x600:0x99999", "--fast")
    assert "USN journal inactive" not in r.stdout, r.stdout[:1200]
    assert "no USN event matches" in r.stdout, r.stdout[:1200]
    # an MLog transaction cannot be tied to a FileRef: it is left out, whatever --source says
    r = _sample_run("lab314_main.raw", "forefst.py", "timeline", "--fileref", "0x70b:0x7", "--source", "SI")
    assert "MLog=0 " in r.stdout, r.stdout[:600]


def test_a_split_file_whose_record_cannot_be_found_is_walked_as_unknown(monkeypatch):
    """No corpus row reaches this: a split file whose type-0x40 record is not in its home directory. Its name
    row says nothing about where the data is, so the walk says (unknown) -- 1.13.0 said (extents)."""
    def one_split_file(f, ps, cs, tr, vlcns, oid=None):
        return [{"name": "orphan.bin", "is_dir": False, "child_oid": 0, "resident": False, "file_size": 0,
                 "raw_value": b"", "create_time": 0, "modify_time": 0, "change_time": 0, "access_time": 0,
                 "file_attrs": 0x20, "flags": 0, "value_len": 0x40, "ads": []}]
    monkeypatch.setattr(F, "_parse_dir_entries", one_split_file)
    monkeypatch.setattr(F, "_entry_identity", lambda raw, is_dir, oid: (0x70b, 7))
    monkeypatch.setattr(F, "_home_backings", lambda *a: {})
    results = []
    F._walk_dir_tree(None, 0, 4096, None, {0x701: [1]}, 0x701, "", 0, F.DEFAULT_DEPTH, results)
    assert [(r["placement"], F._walk_storage_word(r)) for r in results] == [("split", "(unknown)")]


def test_dataruns_reports_a_split_files_attributes_from_its_own_record_as_files_does():
    """K006 moved `files` to the backing's +0x48; `dataruns` kept reading the name row's cached copy, so the two
    disagreed on the Archive bit for 27 split records in the shipped samples (1 on this volume:
    papa_kilo_757910.json, 'attrs=Archive' in dataruns, no attributes in files)."""
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("win11refs2tspecials.raw")
    if img is None:
        import pytest
        pytest.skip("win11refs2tspecials.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        walk = {e["path"]: e for e in F.walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, F.DEFAULT_DEPTH, True)}
        dirs = [("", 0x600)] + [(p, e["oid"]) for p, e in walk.items() if e.get("is_dir") and e.get("oid")]
        compared, differ = 0, []
        for dpath, doid in dirs:
            for info in F._analyze_dir_extents(f, ps, cs, tr, obj_map, doid):
                p = (dpath + "/" + info["name"]) if dpath else info["name"]
                if info.get("record_placement") != "split" or p not in walk:
                    continue
                compared += 1
                if info["file_attrs"] != walk[p].get("file_attrs"):
                    differ.append((p, hex(info["file_attrs"]), hex(walk[p].get("file_attrs") or 0)))
    finally:
        f.close()
    assert compared > 100 and not differ, (compared, differ[:5])


def _specials_walk():
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("win11refs2tspecials.raw")
    if img is None:
        import pytest
        pytest.skip("win11refs2tspecials.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        return {e["path"]: e for e in F.walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, F.DEFAULT_DEPTH, True)}
    finally:
        f.close()


def test_refsanalysis_attributes_storage_is_the_data_residency_files_reports():
    """`attributes` printed RESIDENT / NON-RESIDENT from the walk's raw flag (embedded AND inline), so the 278
    split files on this volume whose data is inline read NON-RESIDENT while `files` says inline."""
    walk = _specials_walk()
    r = _sample_run("win11refs2tspecials.raw", "refsanalysis.py", "attributes")
    storage, cur = {}, None
    for line in r.stdout.splitlines():
        if line.startswith("  FILE "):
            cur = line[7:]
        elif line.startswith("  DIR "):
            cur = None
        elif cur and line.strip().startswith("Storage:"):
            storage[cur] = line.split("Storage:", 1)[1].split()[0]
    files = {p: F._data_residency(e) for p, e in walk.items() if not e.get("is_dir")}
    assert len(storage) == len(files) > 1000, (len(storage), len(files))
    wrong = [(p, storage[p], files[p]) for p in files if storage.get(p) != files[p]]
    assert not wrong, (len(wrong), wrong[:3])
    split_inline = sum(1 for p, e in walk.items() if not e.get("is_dir") and files[p] == "inline"
                       and F._record_placement(e) == "split")
    # wave E E1 close (review RE1-4, acceptance change; the node's property is unchanged): `attributes`' summary counts
    # files once each (by their FileRef, as `summary`), in `files_count_text`'s form -- the inline count is of files,
    # no longer of names (its "Inline files:" line counted names)
    objs = {}
    for p, e in walk.items():
        if not e.get("is_dir"):
            objs.setdefault(F._object_key(e), files[p])
    n_inline = sum(1 for v in objs.values() if v == "inline")
    line = next(l for l in r.stdout.splitlines() if l.strip().startswith("Files:"))
    assert re.search(r"\b%d inline\b" % n_inline, line) and split_inline > 0, (n_inline, line)


def test_refsanalysis_details_says_a_split_files_inline_data_is_inline():
    """`details` said 'non-resident file (no OID of its own; data in out-of-line extents)' for every split file,
    including those whose bytes are inline in their own record."""
    walk = _specials_walk()
    p = next(p for p, e in sorted(walk.items()) if not e.get("is_dir")
             and F._data_residency(e) == "inline" and F._record_placement(e) == "split")
    r = _sample_run("win11refs2tspecials.raw", "refsanalysis.py", "details", p)
    line = next(l for l in r.stdout.splitlines() if l.strip().startswith("Storage:"))
    assert line.split("Storage:", 1)[1].split()[0] == "inline" and "split" in line, line


def test_search_storage_placeholder_is_the_data_residency(monkeypatch):
    row = {"name": "a.bin", "path": "d/a.bin", "is_dir": False, "oid": 0, "is_resident": False,
           "record_embedded": False, "data_form": "inline", "file_size": 5, "modify_time": 0}
    monkeypatch.setattr(F, "walk_directory_tree", lambda *a, **k: [row])
    m = F.cmd_search(None, 0, 4096, None, {}, 3, 14, "a.bin")
    # acceptance 1.14.0 (K1 / K20): a file has no OID of its own -- the field is absent (null), never a residency word
    assert m[0]["oid"] is None and m[0]["data"] == "inline", m[0]


def test_a_dash_after_an_output_flag_means_stdout_in_every_command():
    """`--csv -` is documented as stdout and works in files/search/usn/mlog/deleted, which parse it themselves;
    the shared selector left the '-' behind, so timeline, timestomp, specials and the rest rejected it
    ('unknown option: -'). That is how the samples shipped a 0-byte timestomp.csv (N108)."""
    assert F._extract_output_fmt(["--csv", "-"]) == ("csv", "-", [])
    assert F._extract_output_fmt(["--json", "-", "--all"]) == ("json", "-", ["--all"])
    assert F._extract_output_fmt(["--csv", "out.csv"]) == ("csv", "out.csv", [])
    assert F._extract_output_fmt(["--csv", "--all"]) == ("csv", "-", ["--all"])


def test_timestomp_screen_trailer_counts_the_info_rows_it_hides():
    """The default (HIGH-only) view hid 95 INFO rows on this volume under '(0 MEDIUM + 0 LOW row(s) hidden -- --min
    MEDIUM / --min LOW to show)', and --min LOW does not show INFO (it ranks below LOW)."""
    info = sum(1 for l in _sample_run("win11refs2tspecials.raw", "forefst.py", "timestomp", "--min", "INFO").stdout
               .splitlines() if l.startswith("  INFO "))
    r = _sample_run("win11refs2tspecials.raw", "forefst.py", "timestomp")
    trailer = [l for l in r.stdout.splitlines() if "hidden" in l or "lower-tier" in l]
    assert info > 0 and trailer and all(("%d INFO" % info) in l and "--min INFO" in l for l in trailer), (info, trailer)


def test_export_resident_all_counts_empty_and_extent_files_by_what_they_are(tmp_path):
    """K183's summary counted every embedded record whose bytes are in extents as '0-byte content' (it tested
    the record's placement label, not where the data is): on win11refstestmftecmd '1011 with 0-byte content'
    included 767 extent-backed files, one of them 264,326 bytes."""
    import re
    walk = _specials_walk()
    fl = [e for e in walk.values() if not e.get("is_dir")]
    zero = sum(1 for e in fl if not e.get("file_size"))
    ext = sum(1 for e in fl if e.get("file_size") and F._data_residency(e) not in ("inline", "snapshot-shared"))
    r = _sample_run("win11refs2tspecials.raw", "forefst.py", "export", "resident-all", str(tmp_path / "out"))
    m = re.search(r"wrote (\d+) of (\d+) file\(s\).*not written: (\d+) with 0-byte content, (\d+) non-inline", r.stderr)
    assert m, r.stderr[-800:]
    wrote, seen, z, n = map(int, m.groups())
    assert (seen, z, n) == (len(fl), zero, ext) and wrote == seen - zero - ext, (m.groups(), len(fl), zero, ext)


def test_refsanalysis_details_prints_the_fileref_files_prints_for_an_embedded_file():
    """For an embedded file whose data is in extents, `details` read the FileRef from the split-row layout
    (value+0x08/+0x00) because it gated on the walk's raw flag, printing e.g. 'FileRef: 0x1e000000001:0x10028000000a8'
    and a false 'relocated/hard-linked' line; `files` gives the file's real ObjectRef."""
    walk = _specials_walk()
    p, e = next((p, e) for p, e in sorted(walk.items()) if not e.get("is_dir")
                and F._record_placement(e) == "embedded" and F._data_residency(e) == "extents")
    out = _sample_run("win11refs2tspecials.raw", "refsanalysis.py", "details", p).stdout
    ref = [l for l in out.splitlines() if l.strip().startswith("ObjectRef:")]       # acceptance 1.14.0 (N497)
    assert ref and ref[0].split()[1] == F._file_ref(e), (p, ref, F._file_ref(e))
    assert ("relocated" in out) == (e.get("home_oid") != e.get("parent_oid")), out[:1500]


def test_refsanalysis_details_finds_the_walk_record_whatever_case_the_path_is_typed_in():
    """resolve_path accepts a path in another letter case (or with '//'), but `details` looked the walk record
    up by the exact typed string, so it fell back to the name row's attributes and the old storage words."""
    walk = _specials_walk()
    p, e = next((p, e) for p, e in sorted(walk.items()) if not e.get("is_dir") and "/" in p
                and F._data_residency(e) == "inline" and F._record_placement(e) == "split")
    typed = "/" + p.split("/", 1)[0].upper() + "//" + p.split("/", 1)[1]
    out = _sample_run("win11refs2tspecials.raw", "refsanalysis.py", "details", typed).stdout
    line = next(l for l in out.splitlines() if l.strip().startswith("Storage:"))
    assert line.split("Storage:", 1)[1].split()[0] == "inline", (typed, line)


def test_forefst_details_of_a_directory_lists_each_file_as_files_does():
    """`details <dir>` labelled each child's storage by its row length (placement) and printed a split file's
    attributes from the name row's cached copy: papa_kilo_757910.json showed 0x00000020 where `files` has 0."""
    from test_image_holes_and_page_refs import _corpus_image
    walk = _specials_walk()
    target = next(e for p, e in walk.items() if p.endswith("/papa_kilo_757910.json"))
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(_corpus_image("win11refs2tspecials.raw"), None)
    try:
        d = F.cmd_oid_detail(f, ps, cs, tr, obj_map, vmaj, vmin, target["parent_oid"], json_mode=True)
    finally:
        f.close()
    kids = {e["name"]: e for e in walk.values() if e.get("parent_oid") == target["parent_oid"] and not e.get("is_dir")}
    rows = [x for x in d["attributes"]["0x30"]["entries"] if x.get("filename") in kids]
    assert len(rows) == len(kids) > 1, (len(rows), len(kids))
    wrong = [(x["filename"], x["storage"], F._data_residency(kids[x["filename"]]), x.get("file_attrs"),
              kids[x["filename"]].get("file_attrs")) for x in rows
             if x["storage"] != F._data_residency(kids[x["filename"]])
             or ("file_attrs" in x and int(x["file_attrs"], 16) != (kids[x["filename"]].get("file_attrs") or 0))]
    assert not wrong, wrong[:4]


def test_extract_of_an_empty_extent_form_file_does_not_say_inline_form():
    """An embedded empty file whose data record is extent-form was reported '(0 bytes -- ..., inline form)'
    because the test read the record's placement label; `files` says extents."""
    from test_image_holes_and_page_refs import _corpus_image
    img = _corpus_image("win11refstestmftecmd.raw")
    if img is None:
        import pytest
        pytest.skip("win11refstestmftecmd.raw not in this tree")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        p = next(e["path"] for e in F.walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, F.DEFAULT_DEPTH, True)
                 if not e.get("is_dir") and not e.get("file_size") and F._record_placement(e) == "embedded"
                 and F._data_residency(e) == "extents")
    finally:
        f.close()
    r = _sample_run("win11refstestmftecmd.raw", "forefst.py", "extract", p)
    line = next(l for l in r.stderr.splitlines() if l.startswith("Extracting"))
    assert "0 bytes" in line and "inline form" not in line, (p, line)


def test_refsanalysis_summary_names_the_file_partition_as_forefst_summary_does():
    """The count is the data-residency partition (inline / extent-backed) but was worded 'resident +
    non-resident', the words `attributes` and `files` no longer use for it."""
    ra = _sample_run("win11refs2tspecials.raw", "refsanalysis.py", "summary").stdout
    fe = _sample_run("win11refs2tspecials.raw", "forefst.py", "summary").stdout
    ra_line = next(l for l in ra.splitlines() if l.strip().startswith("Files:"))
    fe_line = next(l for l in fe.splitlines() if l.strip().startswith("Files:"))
    assert ra_line.split("Files:", 1)[1].split() == fe_line.split("Files:", 1)[1].split(), (ra_line, fe_line)
