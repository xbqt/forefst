"""1.13.2 (ships 1.14.0) step C4, area integrity: A5 + N357, A6, N398, N368 residue (i) and (ii).

Plan: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (C4 rows), settlements Q43-Q45; direct mode (PLAN decision 46):
about five nodes per item. A5's N4 nodes (tightened to O1) and A6's nodes are in `test_1132_red_a_coverage.py`.

A5   (decision 22's O1) `integrity --checksums` names its coverage in the Coverage line and in the VERDICT line itself,
     and points to `--fullchecksums`; never "no tampering" for pages outside it; exit unchanged.
N357 the page sub-verdict names its scope also above a redundancy condition; a condition of the checkpoint the volume
     is read from is named as it is (not "the bootstrap chain is damaged").
A6   `--fullchecksums` verifies the child pages below the extent and attribute indexes and counts them in Coverage.
N398 the volume-signature and clock checks credit only pages with a valid signature (an all-zero page passed both).
N368 (i) in bundle mode the checksum section's hole line is not labelled "In image holes"; (ii) its count says its scope
     (the pages this checksum walk reached), the same on the image and its bundle.
"""
import json
import os
import re
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
from conftest import jdoc                                # noqa: E402  (K21: internal names)

from test_1132_red_b_items import _run, _scratch, _image_or_skip, _ctx, _image_vol, FOREFST, AB  # noqa: E402
from test_1132_red_b2_journal import _carve_except, _is_hole                                       # noqa: E402
from test_1132_red_a_coverage import _plcns                                                        # noqa: E402

BASE = AB.BASE_IMAGE                                     # step1/win11refsmini.raw
SAMPLE = "step5/win11refstestmftecmd.raw"                # the public sample (A6's volume)


def _ck_section(out):
    m = re.search(r"Page Checksum Verification.*?\n(.*?)\n\n", out, re.S)
    return m.group(1) if m else ""


def _verdict(out):
    return [l.strip() for l in _ck_section(out).splitlines() if l.strip().startswith("VERDICT:")]


def _unscoped_claims(out):
    return [l for l in out.splitlines() if "no tampering" in l and not re.search(
        r"(?i)of the system root tables|in these pages|not covered", l)]


# ═══ A5 -- the VERDICT names its coverage ═════════════════════════════════════════════════════════════════════

def test_a5_checksums_verdict_names_its_coverage_and_points_to_fullchecksums():
    rc, out, err = _run(FOREFST, _image_or_skip(BASE), "integrity", "--checksums")
    v = _verdict(out)
    # D3 (N470, decision 49 point 8): "detected" and the checksum's limit
    assert v == ["VERDICT: all 15 checksummed pages of the system root tables VERIFIED — no tampering or corruption "
                 "detected in these pages (a checksum cannot prove the absence of a deliberate edit); the object "
                 "B+-trees' pages below their root pages are not covered: run --fullchecksums"], v
    assert rc == 0 and not _unscoped_claims(out), _ctx(rc, out, err)


def test_a5_checksums_coverage_line_names_the_object_root_pages():
    rc, out, err = _run(FOREFST, _image_or_skip(BASE), "integrity", "--checksums")
    cov = [l.strip() for l in _ck_section(out).splitlines() if l.strip().startswith("Coverage:")]
    assert cov and "each object's root page" in cov[0] and "--fullchecksums" in cov[0], cov


def test_a5_fullchecksums_verdict_names_its_coverage():
    rc, out, err = _run(FOREFST, _image_or_skip(BASE), "integrity", "--fullchecksums")
    v = _verdict(out)
    assert len(v) == 1 and re.match(r"VERDICT: all \d+ checksummed pages of the system root tables and \d+ object "
                                    r"B\+-trees, with the \d+ child page\(s\) below their extent and attribute "
                                    r"indexes VERIFIED — no tampering or corruption detected in these pages \(a "
                                    r"checksum cannot prove the absence of a deliberate edit\)$", v[0]), v
    assert rc == 0 and not _unscoped_claims(out)


# ═══ N357 -- above a redundancy condition ═════════════════════════════════════════════════════════════════════

def test_n357_the_sub_verdict_names_its_scope_above_a_checkpoint_copy_not_in_use_that_fails():
    with _image_vol() as v:
        AB.damage_chkp(v, v.geo.hi)                             # the older copy, not in use: its self-checksum fails
        rc, out, err = _run(FOREFST, v.path, "integrity", "--checksums")
        assert rc == 2 and re.search(r"(?m)^\s*Verdict:\s+WARN", out), _ctx(rc, out, err)
        assert _verdict(out) and all("of the system root tables" in x for x in _verdict(out)), _verdict(out)
        assert not _unscoped_claims(out), _unscoped_claims(out)


def test_n357_a_condition_of_the_copy_in_use_is_named_as_it_is():
    with _image_vol() as v:
        AB.damage_chkp(v, v.geo.lo)                             # the newer copy, in use until it fails
        rc, out, err = _run(FOREFST, v.path, "integrity", "--checksums")
        vd = _verdict(out)
        assert rc == 2 and vd and "the checkpoint the volume is read from has a condition: " in vd[0], vd
        assert "the bootstrap chain is damaged" not in out, vd


# ═══ A6 -- the index child pages, counted ═════════════════════════════════════════════════════════════════════

def test_a6_fullchecksums_verifies_the_index_child_pages_of_the_public_sample():
    rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "integrity", "--fullchecksums")
    sec = _ck_section(out)
    assert "with the 29 child page(s) below their extent and attribute indexes" in sec, sec
    assert re.search(r"Pages verified:\s+407\b", sec) and rc == 0, sec      # 1.13.1: 378 (measured)


def test_a6_control_checksums_does_not_reach_the_index_child_pages():
    rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "integrity", "--checksums")
    assert "child page(s) below" not in _ck_section(out)


# ═══ N398 / N368 -- a system-table page that is zeros, or a hole ══════════════════════════════════════════════

def _sys_page(img):
    """A live system-table root page that bootstrap does not need: (ps, cs, root index, [plcn...])."""
    f, ps, cs, tr, roots, obj_map, _a, _b, _c = F.bootstrap(img, None)
    try:
        for idx in (4, 3, 6, 9, 10, 11):
            rv = roots[idx] if idx < len(roots) else None
            if rv:
                pl = _plcns(rv, tr)
                if pl:
                    return ps, cs, idx, pl
    finally:
        f.close()
    raise AB.RedFixtureError("no system-table root page to plant on %s" % img)


def _jsonl(out):
    """`integrity --json`'s page statistics (the counters of the page walk)."""
    i = out.find("{")
    return jdoc(json.JSONDecoder().raw_decode(out[i:])[0])["page_statistics"]     # K21: internal names


def _header_counts_add_up(r):
    return (r["pages_volsig_match"] + r["pages_volsig_mismatch"] == r["pages_valid_sig"] ==
            r["pages_vc_ok"] + r["pages_vc_exceed"])


def test_n398_a_zeroed_page_is_not_credited_with_the_header_checks():
    with _image_vol() as v:
        ps, cs, idx, pl = _sys_page(v.path)
        for p in pl:
            v.write(ps + p * cs, b"\0" * cs)
        rc, out, err = _run(FOREFST, v.path, "integrity", "--json")
        r = _jsonl(out)
        assert r["pages_invalid_sig"] >= 1 and _header_counts_add_up(r), {k: r[k] for k in r if k.startswith("pages")}


@pytest.fixture(scope="module")
def holed():
    """base A with one system-table root page (every cluster of it) punched: (path, scratch dir, plcns)."""
    img = _image_or_skip(BASE)
    ps, cs, idx, pl = _sys_page(img)
    with _scratch("c4int") as s:
        p = os.path.join(s, "target.raw")
        _carve_except(img, p, [(ps + x * cs, cs) for x in pl])
        yield p, s, pl


def test_n398_a_page_in_a_hole_is_not_credited_with_the_header_checks(holed):
    p, s, pl = holed
    rc, out, err = _run(FOREFST, p, "integrity", "--json")
    r = _jsonl(out)
    assert r.get("PagesInHoles", 0) >= 1 and _header_counts_add_up(r), {k: r[k] for k in r if k.startswith("pages")}


def test_n398_control_an_intact_volume_credits_every_page():
    rc, out, err = _run(FOREFST, _image_or_skip(BASE), "integrity", "--json")
    r = _jsonl(out)
    assert r["pages_volsig_match"] == r["pages_valid_sig"] == r["pages_checked"] == r["pages_vc_ok"], r


def _hole_line(out):
    return [l.strip() for l in _ck_section(out).splitlines() if re.match(r"\s*In (image )?holes:", l)]


def test_n368_i_the_bundles_checksum_hole_line_is_not_labelled_image(holed):
    p, s, pl = holed
    b = os.path.join(s, "b")
    _run(FOREFST, p, "export", "metadata", b, cwd=s)
    rc, out, err = _run(FOREFST, b, "integrity", "--checksums", cwd=s)
    hl = _hole_line(out)
    assert hl and hl[0].startswith("In holes:") and "the source image stores them as holes" in hl[0], hl


def test_n368_ii_the_hole_count_says_its_scope_the_same_on_the_image_and_its_bundle(holed):
    p, s, pl = holed
    b = os.path.join(s, "b2")
    _run(FOREFST, p, "export", "metadata", b, cwd=s)
    rc1, o1, _e = _run(FOREFST, p, "integrity", "--checksums", cwd=s)
    rc2, o2, _e = _run(FOREFST, b, "integrity", "--checksums", cwd=s)
    n = [re.search(r"holes:\s+(\d+ of the \d+ pages this checksum walk reached)", x[0]) for x in
         (_hole_line(o1), _hole_line(o2)) if x]
    assert len(n) == 2 and all(n) and n[0].group(1) == n[1].group(1), (_hole_line(o1), _hole_line(o2))
    assert rc1 == rc2 == 2
