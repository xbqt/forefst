"""D13 (image holes) and the page-reference verifier (GN_PREF_RA_004).

D13's first design was wrong and these tests pin the correction. It warned whenever a file's extents
overlapped a hole in the sparse image — but a file's own zero-runs are legitimately stored as holes, so a
791 MB ISO, a 1-second silent WAV and 245 files with correct content all tripped it while extracting
perfectly. Overlap alone means nothing. Only "entirely zero AND the whole allocation is a hole" is
informative, and even that is ambiguous: 15 of 105,889 extent-backed files corpus-wide, mostly legitimately
pre-allocated. So the tool reports and never suppresses bytes.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
import forefst as F                                                     # noqa: E402


def _sparse(tmp_path, size, data_at=None):
    """A sparse file of `size` bytes, optionally with real data written at `data_at`."""
    p = tmp_path / "img.bin"
    with open(p, "wb") as fh:
        fh.truncate(size)
        if data_at is not None:
            fh.seek(data_at)
            fh.write(b"\xAA" * 4096)
    return p


def test_hole_bytes_counts_a_pure_hole(tmp_path):
    p = _sparse(tmp_path, 1 << 20)
    fd = os.open(p, os.O_RDONLY)
    try:
        n = F._hole_bytes_in(fd, 0, 1 << 20)
    finally:
        os.close(fd)
    if n is None:
        pytest.skip("SEEK_DATA/SEEK_HOLE not supported on this filesystem")
    assert n == 1 << 20


def test_hole_bytes_excludes_written_data(tmp_path):
    p = _sparse(tmp_path, 1 << 20, data_at=512 * 1024)
    fd = os.open(p, os.O_RDONLY)
    try:
        n = F._hole_bytes_in(fd, 0, 1 << 20)
    finally:
        os.close(fd)
    if n is None:
        pytest.skip("SEEK_DATA/SEEK_HOLE not supported on this filesystem")
    assert n < (1 << 20), "a region containing written data must not count as all hole"


def test_undeterminable_is_none_not_zero():
    """The three-valued contract: a closed/invalid fd yields None, never 0.

    0 would read as 'no holes here' and silently disable the check."""
    assert F._hole_bytes_in(-1, 0, 4096) is None


def test_no_extents_means_zero_not_unknown(tmp_path):
    """An empty extent list has no holes to report — that is a real 0, not 'cannot tell'."""
    p = _sparse(tmp_path, 4096)
    with open(p, "rb") as fh:
        assert F._extent_hole_bytes(fh, 0, 4096, []) == 0


# ── page references ──────────────────────────────────────────────────────────

def _corpus_image(name):
    seen = set()
    for start in (os.getcwd(), REPO):
        d = os.path.abspath(start)
        while d not in seen:
            seen.add(d)
            root = os.path.join(d, "analysis", "rawdisk", "disks")
            if os.path.isdir(root):
                for dirpath, _dirs, files in os.walk(root):
                    if name in files:
                        return os.path.join(dirpath, name)
                return None
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None



def _page_reference_targets(f, ps, cs, tr, roots):
    """Physical LCNs of the pages the LIVE object-table rows point at (the rows the reader uses)."""
    ot = F._select_ot_root(f, ps, cs, tr, roots)
    rows = [(kd, vd) for kd, vd in F.walk_bplus(f, ps, cs, tr, ot)
            if len(kd) >= 16 and len(vd) >= 0x50]
    used = {}
    for i, (kd, _vd) in enumerate(rows):
        used[F.le64(kd, 8)] = i                      # last row wins, as build_object_map does
    out = []
    for i, (kd, vd) in enumerate(rows):
        if used[F.le64(kd, 8)] != i:
            continue
        clen = F.le32(vd, 0x44)
        if clen not in (8, 32) or 0x48 + clen > len(vd):
            continue
        for j in range(4):
            x = F.le64(vd, 0x20 + 8 * j)
            if x not in (0, 0xFFFFFFFFFFFFFFFF):
                out.append(tr.tr(x))
    return sorted(set(out))

def test_page_references_verify_on_a_real_volume():
    img = _corpus_image("win11refsmini.raw")
    if img is None:
        pytest.skip("corpus image not present (a clone ships no images)")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        r = F.verify_page_references(f, ps, cs, tr, roots)
    finally:
        f.close()
    assert r["checked"] > 0
    assert r["failed"] == 0, "a healthy volume must have no mismatched page-reference checksum"
    assert r["verified"] == r["checked"]
    assert isinstance(r["algorithms"], list), "algorithms must be JSON-serialisable, not a set"


def test_page_reference_check_is_gated_on_checksums():
    """`integrity --checksums` verifies; plain `integrity` says how to ask for it.

    Verification is one 4-cluster read per object -- 26,681 of them on a real Windows volume, 427 MB and
    ~38 s. Running it unconditionally took `integrity` from 1.4 s to 38.2 s, so it sits behind the same flag
    as the other deep checks.
    """
    img = _corpus_image("win11refsmini.raw")
    if img is None:
        pytest.skip("corpus image not present")
    tool = os.path.join(REPO, "forefst.py")
    plain = subprocess.run([sys.executable, tool, img, "integrity"],
                           capture_output=True, text=True, timeout=900)
    deep = subprocess.run([sys.executable, tool, img, "integrity", "--checksums"],
                          capture_output=True, text=True, timeout=1800)
    assert plain.returncode == 0 and deep.returncode == 0
    assert "Page-reference checksums" in plain.stdout, "the section must be visible either way"
    assert "add `--checksums`" in plain.stdout, "plain integrity must say how to run the check"
    assert "Verified:" in deep.stdout, "--checksums must actually verify"


def test_summary_does_not_pay_for_page_verification():
    """A guard on the regression this caused: `summary` and `fastsummary` must not run the verification.

    It was briefly in the shared summary dict, which took `fastsummary` from 0.36 s to 36.70 s and `summary`
    from 4.72 s to 42.24 s on a real Windows volume."""
    img = _corpus_image("win11refsmini.raw")
    if img is None:
        pytest.skip("corpus image not present")
    tool = os.path.join(REPO, "forefst.py")
    for cmd in ("summary", "fastsummary"):
        r = subprocess.run([sys.executable, tool, img, cmd, "--json"],
                           capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, r.stderr[-300:]
        assert "page_refs" not in r.stdout, f"{cmd} must not carry the page-reference verification"


def test_absent_page_is_not_reported_as_a_failure():
    """A page the IMAGE does not contain must not read as an ALTERED volume.

    An all-zero page fails its checksum exactly like a tampered one, so before the `absent` counter existed
    a partial acquisition looked like evidence of alteration. The two need different actions -- re-acquire
    versus investigate -- so they are counted and worded separately.

    No corpus image happens to have a hole under a live object-table page reference, so the witness is built:
    a sparse copy of a real volume with the referenced page clusters punched out. Both branches are then
    exercised for real -- zeroed pages must land in `absent`, and a page with WRONG content in `failed`.
    """
    img = _corpus_image("win11refsmini.raw")
    if img is None:
        pytest.skip("corpus image not present")

    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        base = F.verify_page_references(f, ps, cs, tr, roots)
        assert set(base) >= {"checked", "verified", "failed", "absent", "superseded", "skipped"}, \
            "absent and superseded must be first-class outcomes, not folded into failed"
        assert base["checked"] > 0 and base["absent"] == 0 and base["failed"] == 0, \
            "the unmodified image is complete and unaltered"
        targets = _page_reference_targets(f, ps, cs, tr, roots)
    finally:
        f.close()
    assert targets, "need at least one page reference to punch"

    for fill, bucket in ((b"\x00", "absent"), (b"\xde", "failed")):
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tf:
            copy = tf.name
        try:
            # Sparse copy: reflink/hole-preserving, so this costs bytes-touched, not image size.
            subprocess.run(["cp", "--sparse=always", img, copy], check=True, timeout=600)
            with open(copy, "r+b") as w:
                for lcn in targets:
                    w.seek(ps + lcn * cs)
                    w.write(fill * cs)
            f2, ps2, cs2, tr2, roots2, _om, _a, _b, _c = F.bootstrap(copy, None)
            try:
                r = F.verify_page_references(f2, ps2, cs2, tr2, roots2)
            finally:
                f2.close()
            # `targets` are LCN slots (4 per reference on 4 KiB clusters); the counters are per REFERENCE,
            # so compare against `checked`, not against the slot count.
            assert r["checked"] > 0 and r[bucket] == r["checked"], (
                f"every reference whose page was filled with {fill!r} should be {bucket}, got {r}")
            other = "failed" if bucket == "absent" else "absent"
            assert r[other] == 0, f"a {bucket} page must not be counted as {other}: {r}"
        finally:
            os.unlink(copy)


def _first_extent_file(f, ps, cs, tr, obj_map, _skipped_dirs=None):
    """A file with a decodable extent map, for hole-punching."""
    if _skipped_dirs is None:
        _skipped_dirs = []
    seen = set()
    for e in F.walk_directory_tree(f, ps, cs, tr, obj_map, 0x600, F.DEFAULT_DEPTH, False, set()):
        if e.get("is_dir"):
            continue
        oid = e["parent_oid"]
        if oid in seen:
            continue
        seen.add(oid)
        try:
            infos = F._analyze_dir_extents(f, ps, cs, tr, obj_map, oid)
        except Exception as exc:                 # recorded, not swallowed: the helper is picking a witness,
            _skipped_dirs.append((oid, type(exc).__name__))   # so a failure here narrows the search, not hides it
            continue
        for info in infos:
            if (info.get("extents") or []) and (info.get("file_size") or 0) > 0:
                return info
    return None


def test_extract_reports_hole_sourced_bytes_but_still_writes_them():
    """D13: a hole is NOT evidence that data is missing, so the bytes are written and the ranges reported.

    Raw images are stored sparsely, and a sparse image stores a file's OWN zero content exactly the way it
    stores a range that was never captured. `cp --sparse=always` demonstrates it: it converts real zero
    clusters into holes, which is how this test builds its witness in the first place. An earlier version of
    this check refused such files as "an acquisition gap, not a zero-filled file" -- a claim the image cannot
    support in either direction.

    So: write the bytes, name the ranges, exit 2, and with -o leave a sidecar. `--refuse-holes` is the strict
    variant that writes nothing. The note must fire on a PARTIAL hole too -- a gap inside a file with real
    content is the case that used to pass silently.
    """
    img = info = None
    for cand in ("win11refs2g.raw", "win10refs2g.raw", "win10refsmini.raw"):
        img = _corpus_image(cand)
        if img is None:
            continue
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
        try:
            info = _first_extent_file(f, ps, cs, tr, obj_map)
        finally:
            f.close()
        if info is not None:
            break
    if img is None or info is None:
        pytest.skip("no corpus image with an extent-backed file")

    d = tempfile.mkdtemp()
    try:
        zeroed = os.path.join(d, "zeroed.raw")
        holed = os.path.join(d, "holed.raw")
        subprocess.run(["cp", "--sparse=always", img, zeroed], check=True, timeout=600)
        with open(zeroed, "r+b") as w:
            for ext in info["extents"]:
                w.seek(ps + ext["plcn"] * cs)
                w.write(b"\x00" * (ext["clusters"] * cs))
        subprocess.run(["cp", "--sparse=always", zeroed, holed], check=True, timeout=600)
        os.unlink(zeroed)

        tool = os.path.join(REPO, "forefst.py")
        out = os.path.join(d, "out.bin")

        # default: bytes ARE written, ranges reported, exit 2, sidecar present
        r = subprocess.run([sys.executable, tool, holed, "extract", info["name"], "-o", out],
                           capture_output=True, text=True, timeout=900)
        assert r.returncode == 2, f"hole-sourced bytes must exit 2, got {r.returncode}: {r.stderr[-400:]}"
        assert os.path.exists(out), "the bytes must be written, not withheld"
        assert os.path.getsize(out) == info["file_size"]
        assert "stores as holes" in r.stderr, r.stderr[-400:]
        # the wording must not assert a cause the image cannot establish
        low = r.stderr.lower()
        assert "acquisition gap" not in low and "fabricat" not in low, \
            "the report must stay neutral about why the range is a hole"
        side = out + ".holes.json"
        assert os.path.exists(side), "-o must leave a sidecar naming the ranges"
        rec = json.load(open(side))
        assert rec["ranges"] and rec["hole_bytes"] > 0
        assert sum(x["length"] for x in rec["ranges"]) == rec["hole_bytes"]

        # strict: same finding, nothing written at all
        out2 = os.path.join(d, "strict.bin")
        r = subprocess.run([sys.executable, tool, holed, "extract", info["name"], "-o", out2,
                            "--refuse-holes"], capture_output=True, text=True, timeout=900)
        assert r.returncode == 2
        assert not os.path.exists(out2), "--refuse-holes must write no file"
        assert not os.path.exists(out2 + ".holes.json"), "and no sidecar beside a file it did not write"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_a_file_with_no_holes_extracts_with_exit_zero():
    """The other half of the contract: no holes -> no note, no sidecar, exit 0."""
    img = info = None
    for cand in ("win11refs2g.raw", "win10refs2g.raw"):
        img = _corpus_image(cand)
        if img is None:
            continue
        f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
        try:
            cand_info = _first_extent_file(f, ps, cs, tr, obj_map)
            if cand_info is not None:
                holes = F._extent_hole_ranges(f, ps, cs, cand_info["extents"], cand_info["file_size"])
                if holes == []:
                    info = cand_info
        finally:
            f.close()
        if info is not None:
            break
    if img is None or info is None:
        pytest.skip("no fully-captured extent-backed file available")
    d = tempfile.mkdtemp()
    try:
        out = os.path.join(d, "clean.bin")
        r = subprocess.run([sys.executable, os.path.join(REPO, "forefst.py"), img,
                            "extract", info["name"], "-o", out],
                           capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, f"a fully-captured file must exit 0: {r.stderr[-300:]}"
        assert "stores as holes" not in r.stderr
        assert not os.path.exists(out + ".holes.json")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_hole_ranges_merge_across_extent_boundaries():
    """W7: one hole spanning two adjacent extents is ONE range, not one per extent.

    `_extent_hole_ranges` walks extent by extent, so a hole crossing a boundary arrived as two adjacent
    entries (0-4095, 4096-97672). That split describes the extent map, not the hole. The byte total was
    always right; the range list now is too.
    """
    cs = 4096
    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tf:
        path = tf.name
    try:
        # a sparse file: 8 clusters of hole, then one cluster of data
        with open(path, "wb") as w:
            w.truncate(8 * cs)
            w.seek(8 * cs)
            w.write(b"\xab" * cs)
        f = open(path, "rb")
        try:
            # two ADJACENT extents, each fully inside the hole: clusters 0 and 1..3
            exts = [{"file_vcn": 0, "plcn": 0, "clusters": 1},
                    {"file_vcn": 1, "plcn": 1, "clusters": 3}]
            got = F._extent_hole_ranges(f, 0, cs, exts, 4 * cs)
            if got is None:
                pytest.skip("SEEK_DATA/SEEK_HOLE unsupported on this filesystem")
            assert got == [(0, 4 * cs)], f"adjacent holes must merge into one range, got {got}"
            assert sum(n for _o, n in got) == 4 * cs

            # a gap between the two extents must NOT be merged away
            exts2 = [{"file_vcn": 0, "plcn": 0, "clusters": 1},
                     {"file_vcn": 2, "plcn": 2, "clusters": 1}]
            got2 = F._extent_hole_ranges(f, 0, cs, exts2, 3 * cs)
            assert got2 == [(0, cs), (2 * cs, cs)], f"non-adjacent ranges must stay separate, got {got2}"
        finally:
            f.close()
    finally:
        os.unlink(path)


def test_dataruns_reports_the_full_residency_vocabulary():
    """W6: `dataruns` must not flatten snapshot-shared or sparse into inline/extents.

    It keyed on the record's PLACEMENT and had two data states, so a snapshot-shared stream -- one owning no
    allocation because its bytes are still the snapshot's -- printed as "bytes stored in the record", which
    is wrong twice: they are neither inline nor this stream's. Both surfaces now resolve residency through
    `_stream_data_form`, the one classifier `files` uses.
    """
    img = _corpus_image("win11refs2tsnapshots.raw")
    if img is None:
        pytest.skip("corpus image not present")
    f, ps, cs, tr, roots, obj_map, vmaj, vmin, _ = F.bootstrap(img, None)
    try:
        walk = {e["path"]: e for e in F.walk_directory_tree(
            f, ps, cs, tr, obj_map, 0x600, F.DEFAULT_DEPTH, False, set()) if not e.get("is_dir")}
        shared = [e for e in walk.values() if e.get("data_form") == F.DATA_SNAPSHOT_SHARED]
        assert shared, "this image is the snapshot-shared witness; it must have some"

        seen, compared, mismatch = set(), 0, []
        for e in walk.values():
            oid = e["parent_oid"]
            if oid in seen:
                continue
            seen.add(oid)
            infos = F._analyze_dir_extents(f, ps, cs, tr, obj_map, oid)
            pp = e.get("parent_path")
            for info in infos:
                key = info["name"] if pp in (".", "", None) else pp + "/" + info["name"]
                w = walk.get(key)
                if w is None:
                    continue
                compared += 1
                if (w.get("data_form") or "") != (info.get("data_residency") or ""):
                    mismatch.append((key, w.get("data_form"), info.get("data_residency")))
        assert compared > 0, "a check that compared nothing is not a pass"
        assert not mismatch, f"dataruns disagrees with files on {len(mismatch)}: {mismatch[:3]}"
    finally:
        f.close()

    r = subprocess.run([sys.executable, os.path.join(REPO, "forefst.py"), img, "dataruns", "-v"],
                       capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stderr[-300:]
    assert "SHARED" in r.stdout, "a snapshot-shared file must print SHARED, not INLINE"
    assert "owned by the snapshot" in r.stdout
