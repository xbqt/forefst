"""The `export metadata` bundle: it must round-trip, and it must refuse when it is not whole.

A bundle is an evidence artefact that will be read without the disk it came from, so the two properties
that matter are:

  1. what it reproduces is IDENTICAL to the source volume, and
  2. anything missing or altered is REFUSED, never quietly half-read.

The corruption cases are synthetic so they run anywhere. The round-trip needs a real ReFS volume and skips
when none is present -- a skip, never a pass, because a comparison of zero files proves nothing.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))            # .../forefstdev
TOOL = os.path.join(REPO, "forefst.py")
WORKSPACE = os.path.dirname(REPO)                        # .../refs


def run(*argv, timeout=1800):
    return subprocess.run([sys.executable, TOOL, *argv], capture_output=True, text=True, timeout=timeout)


def _sample_image():
    """A ReFS volume to round-trip, preferring one that SHIPS.

    A clone has the published samples under analysis/samples/disks/<name>/ once `git lfs pull` and
    `zstd -d` have run, so the round-trip is reproducible by a reader and not only in the maintainer's
    tree. The corpus images are the fallback for a development checkout.
    """
    pub = os.path.join(REPO, "analysis", "samples", "disks")
    if os.path.isdir(pub):
        for name in sorted(os.listdir(pub)):
            cand = os.path.join(pub, name, name + ".raw")
            if os.path.exists(cand):
                return cand
    for rel in ("analysis/rawdisk/disks/step1/win11refsmini.raw",
                "analysis/rawdisk/disks/step1/win10refsmini.raw"):
        p = os.path.join(WORKSPACE, rel)
        if os.path.exists(p):
            return p
    return None


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    img = _sample_image()
    if img is None:
        pytest.skip("no small ReFS sample image available")
    d = tmp_path_factory.mktemp("bundle_src")
    out = str(d / "b")
    r = run(img, "export", "metadata", out)
    assert r.returncode == 0, r.stderr[-400:]
    return img, out


def _reseal(bdir):
    """Rewrite sha256sums.txt so a deliberately damaged bundle fails on the DAMAGE, not on the seal."""
    lines = []
    for name in sorted(os.listdir(bdir)):
        if name == "sha256sums.txt":
            continue
        h = hashlib.sha256(open(os.path.join(bdir, name), "rb").read()).hexdigest()
        lines.append(f"{h}  {name}")
    open(os.path.join(bdir, "sha256sums.txt"), "w").write("\n".join(lines) + "\n")


# ─── it round-trips ──────────────────────────────────────────────────────────

def test_listing_from_bundle_is_identical_to_the_volume(bundle):
    img, bdir = bundle
    a = run(img, "files", "--csv", "-q")
    b = run(bdir, "files", "--csv", "-q")
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout, "listing from the bundle differs from the source volume"
    assert a.stdout.count("\n") > 1, "the comparison covered no rows"


def test_verify_bundle_passes_on_a_whole_bundle(bundle):
    _img, bdir = bundle
    r = run(bdir, "verify-bundle")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout


def test_bundle_states_that_it_carries_inline_content(bundle):
    """A 'metadata' bundle holds every inline stream, so it must say so rather than imply otherwise."""
    _img, bdir = bundle
    man = json.load(open(os.path.join(bdir, "manifest.json")))
    assert "inline_content" in man, "manifest does not declare its inline content"
    r = run(bdir, "summary", "-q")
    assert "inline" in r.stderr.lower(), "the banner does not warn that inline content travels with it"


def test_manifest_records_where_it_came_from(bundle):
    _img, bdir = bundle
    prov = json.load(open(os.path.join(bdir, "manifest.json")))["provenance"]
    for key in ("tool_version", "source_path", "source_content_pin", "exported_utc", "host"):
        assert prov.get(key), f"provenance is missing {key}"


def test_inline_content_reads_back_but_extent_content_is_refused(bundle):
    """The two halves of the contract, on one volume: inline is real, extent-backed is refused."""
    img, bdir = bundle
    rows = run(img, "files", "--csv", "-q").stdout.splitlines()
    hdr = rows[0].split(",")
    ix_path, ix_res, ix_size = hdr.index("FullPath"), hdr.index("DataResidency"), hdr.index("FileSize")
    inline = next((r.split(",") for r in rows[1:]
                   if len(r.split(",")) > ix_res and r.split(",")[ix_res] == "inline"
                   and r.split(",")[ix_size].isdigit() and int(r.split(",")[ix_size]) > 0), None)
    if inline is None:
        pytest.skip("no inline file on this volume")
    a = subprocess.run([sys.executable, TOOL, img, "extract", inline[ix_path]],
                       capture_output=True, timeout=600)
    b = subprocess.run([sys.executable, TOOL, bdir, "extract", inline[ix_path]],
                       capture_output=True, timeout=600)
    assert a.stdout == b.stdout and a.stdout, "inline content did not survive the bundle"

    ext = next((r.split(",") for r in rows[1:]
                if len(r.split(",")) > ix_res and r.split(",")[ix_res] == "extents"), None)
    if ext is not None:
        c = subprocess.run([sys.executable, TOOL, bdir, "extract", ext[ix_path]],
                           capture_output=True, timeout=600)
        assert c.stdout == b"", "a bundle returned bytes for extent-backed content it does not hold"
        assert c.returncode == 2, f"expected exit 2 for content not in the bundle, got {c.returncode}"


# ─── it refuses when it is not whole ─────────────────────────────────────────

def test_a_directory_without_a_manifest_is_not_a_bundle(tmp_path):
    d = tmp_path / "plain"
    d.mkdir()
    r = run(str(d), "summary")
    assert r.returncode == 1
    assert "not a regular file" in r.stderr


def test_broken_seal_is_refused(bundle, tmp_path):
    _img, bdir = bundle
    dup = str(tmp_path / "tampered")
    shutil.copytree(bdir, dup)
    with open(os.path.join(dup, "metadata_pages.bin"), "r+b") as f:
        f.seek(64)
        f.write(b"\xff\xff\xff\xff")
    r = run(dup, "summary")
    assert r.returncode == 1
    assert "verification" in r.stderr.lower() or "does not match" in r.stderr.lower()
    v = run(dup, "verify-bundle")
    assert v.returncode == 2 and "FAIL" in v.stdout


def test_missing_artefact_is_refused(bundle, tmp_path):
    _img, bdir = bundle
    dup = str(tmp_path / "incomplete")
    shutil.copytree(bdir, dup)
    os.remove(os.path.join(dup, "metadata_pages.bin"))
    r = run(dup, "summary")
    assert r.returncode == 1, "a bundle missing a blob was opened anyway"
    v = run(dup, "verify-bundle")
    assert v.returncode == 2 and "FAIL" in v.stdout


def test_index_row_past_the_end_of_its_blob_is_caught(bundle, tmp_path):
    """A row pointing outside its blob must fail verification, not read whatever is there."""
    _img, bdir = bundle
    dup = str(tmp_path / "badindex")
    shutil.copytree(bdir, dup)
    idx = os.path.join(dup, "metadata_index.csv")
    lines = open(idx).read().rstrip("\n").split("\n")
    parts = lines[1].split(",")
    parts[2] = str(1 << 40)                      # byte_offset far past the blob
    lines[1] = ",".join(parts)
    open(idx, "w").write("\n".join(lines) + "\n")
    _reseal(dup)
    v = run(dup, "verify-bundle")
    assert v.returncode == 2, "an index row past the end of its blob was accepted"
    assert "past the end" in v.stdout


def test_truncated_blob_is_caught(bundle, tmp_path):
    _img, bdir = bundle
    dup = str(tmp_path / "truncated")
    shutil.copytree(bdir, dup)
    p = os.path.join(dup, "metadata_pages.bin")
    with open(p, "r+b") as f:
        f.truncate(os.path.getsize(p) // 2)
    _reseal(dup)
    v = run(dup, "verify-bundle")
    assert v.returncode == 2, "a truncated page blob passed verification"
