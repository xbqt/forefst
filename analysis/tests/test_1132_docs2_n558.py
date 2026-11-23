"""1.14.0, docs part 2 (2026-11-16): N558 -- `extract` from a metadata bundle says the bytes it would take from a range
the bundle does not carry are not in the bundle, and to read the stream from the source image.

A bundle carries no extent-backed content: in its rehydrated image every extent cluster is a hole. `extract`'s main path
stated those bytes with the raw-image wording ("... does not by itself mean the data is missing"), which is false here:
the bundle is known not to hold them. The refusal itself was right (a bundle forces --refuse-holes; nothing written).
`content_holes`, used by the other content paths, says the same in its bundle sentence, with the same correction.
"""
import os
import subprocess
import sys

import pytest

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
from test_image_holes_and_page_refs import _corpus_image  # noqa: E402

FOREFST = os.path.join(REPO, "forefst.py")
SAMPLE = "step5/win11refstestmftecmd.raw"
# an extent-backed file of the public sample: 440,919 bytes, 4 extents; two data clusters (file offsets 0 and 425984),
# the other 106 clusters sparse runs (zeros by the file's own extent map, never read from an image)
TARGET = "/test/xbpt_config_log_714507.md"


def _run(argv, timeout=1800):
    return subprocess.run([sys.executable, "-B"] + argv, capture_output=True, text=True, timeout=timeout)


@pytest.fixture(scope="module")
def sample_bundle(tmp_path_factory):
    img = _corpus_image(SAMPLE)
    if img is None:
        pytest.skip("%s not in this tree" % SAMPLE)
    d = str(tmp_path_factory.mktemp("n558") / "bundle")
    r = _run([FOREFST, img, "export", "metadata", "-o", d])
    assert r.returncode in (0, 2), r.stderr[-800:]
    return img, d


def test_n558_extract_from_a_bundle_says_the_bytes_are_not_in_the_bundle(sample_bundle):
    _img, d = sample_bundle
    r = _run([FOREFST, d, "extract", TARGET])
    assert r.returncode == 2 and r.stdout == "", (r.returncode, r.stdout[:200], r.stderr[-1200:])
    err = " ".join(r.stderr.split())
    assert ("8192 of 440919 bytes of 'xbpt_config_log_714507.md' would be written from ranges this bundle does not "
            "carry") in err, err[-1500:]
    assert "read this stream from the source image" in err, err[-1500:]
    assert "does not by itself mean the data is missing" not in err, err[-1500:]
    assert "--refuse-holes: nothing written." in err


def test_n558_the_raw_image_keeps_its_wording(sample_bundle):
    """Control: the same file from the source image reads no byte from a hole (its sparse runs are never read), so
    `extract` writes it and exits 0 with no hole note; the raw-image wording itself is pinned in test_1132_d3_rest."""
    img, _d = sample_bundle
    r = subprocess.run([sys.executable, "-B", FOREFST, img, "extract", TARGET], capture_output=True, timeout=1800)
    assert r.returncode == 0, r.stderr[-800:]
    assert len(r.stdout) == 440919
    assert b"stores as holes" not in r.stderr and b"bundle" not in r.stderr.lower()
