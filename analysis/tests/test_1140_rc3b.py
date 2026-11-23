"""1.14.0 RC3b (the tool batch after the second round): the items with a behaviour a test can hold.

N643: `extract -o DIR` (DIR an existing directory) wrote the `<DIR>.holes.json` sidecar beside the directory and then
refused the run ("-o ... is a directory -- give a FILE path"): a refused command left a file behind, named after the
refused path. The directory is now refused before anything is written.
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_1132_g3_forms_exits import FOREFST, _img, MINI314, SAMPLE, INLINE, EXTENTS   # noqa: E402


def _refused_into_dir(tmp_path, image, name):
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run([sys.executable, "-B", FOREFST, _img(image), "extract", name, "-o", str(out)],
                       capture_output=True, text=True, timeout=1800)
    return r, out


@pytest.mark.parametrize("image,name", [(MINI314, INLINE), (SAMPLE, EXTENTS)], ids=["inline", "extents"])
def test_n643_extract_into_a_directory_writes_nothing(tmp_path, image, name):
    r, out = _refused_into_dir(tmp_path, image, name)
    assert "Traceback" not in r.stderr, r.stderr[-2000:]
    assert r.returncode == 1 and "is a directory" in r.stderr, (r.returncode, r.stderr[-1500:])
    assert not os.path.exists(str(out) + ".holes.json"), \
        "a refused run must leave no sidecar beside the directory it refused (N643)"
    assert sorted(os.listdir(tmp_path)) == ["out"] and os.listdir(out) == [], \
        "nothing may be written by a refused run: %r / %r" % (os.listdir(tmp_path), os.listdir(out))


# RC3b item 7 (S10): an extent row whose flags declare a CRC64 per cluster (0x100 without 0x80) is stepped over by its own
# declared size, 24 + 8 x run; the CRC-32C rule (24 + 4 x run with 0x80) and the plain row (24) are unchanged, and a
# size the flags do not declare is still refused (0). No corpus row carries 0x100, so the rows are built here.
import struct  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import forefst as _fe  # noqa: E402


def _row(flags, run, size):
    return struct.pack("<QHHQI", 0x1234, flags, size, 0, run) + b"\0" * max(0, size - 24)


@pytest.mark.parametrize("flags,run,size,want", [
    (0x0100, 3, 24 + 8 * 3, 48),      # CRC64 per cluster: its own size
    (0x0180, 3, 24 + 8 * 3, 0),       # both bits: not the CRC64 form, and not 24 + 4 x run
    (0x0080, 3, 24 + 4 * 3, 36),      # CRC-32C per cluster (unchanged)
    (0x0000, 3, 24, 24),              # plain run (unchanged)
    (0x0000, 3, 24 + 8 * 3, 0),       # a CRC64-sized row without the flag: refused
])
def test_item7_extent_row_size_crc64(flags, run, size, want):
    v = _row(flags, run, size)
    assert _fe._extent_row_size(v, 0, run) == want
    assert _fe._extent_row_step(v, 0, run) == ((want + 7) & ~7 if want else 0)
    if flags == 0x0100:
        assert _fe._extent_row_is_crc64(v, 0) and _fe._extent_row_crcs(v, 0, run) == ([], None)


# RC3b item 8 (U05, N665): a stream that owns no clusters and that no snapshot shares (`unallocated`) is written as its size
# in zeros, with exit 0 and the state said; until RC3 `extract` wrote nothing and exited 2 ("its $DATA is not a plain
# inline stream ... use `snapshots --extract`").
import hashlib  # noqa: E402

ATTR2 = "step4continuing/win11refs4gattributestest2.raw"


def _sha256_zeros(n):
    h, z = hashlib.sha256(), b"\0" * (1 << 20)
    while n > 0:
        k = min(n, len(z))
        h.update(z[:k])
        n -= k
    return h.hexdigest()


def test_item8_unallocated_stream_is_written_as_zeros_on_image_win11refs4gattributestest2(tmp_path):
    out = tmp_path / "sparse.bin"
    r = subprocess.run([sys.executable, "-B", FOREFST, _img(ATTR2), "extract", "sparse.dat", "-o", str(out)],
                       capture_output=True, text=True, timeout=1800)
    assert "Traceback" not in r.stderr, r.stderr[-2000:]
    assert r.returncode == 0 and "(unallocated)" in r.stderr, (r.returncode, r.stderr[-1500:])
    assert os.path.getsize(out) == 423456789
    h = hashlib.sha256()
    with open(out, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    assert h.hexdigest() == _sha256_zeros(423456789), "every byte of an unallocated stream reads as zero"
    side = open(str(out) + ".holes.json", encoding="utf-8").read()
    assert '"Status": "none"' in side, side


# RC3b D2 (E170 amended): `usn --info` prints the checkpoint's journal cursor and counts only the CURRENT journal's records
# at or past its next USN. On labG_0 the journal was re-created: the records above the cursor are the earlier instance's
# (USN 12288 up) and are not counted -- E170 had read them as records written after the checkpoint.
@pytest.mark.parametrize("image,next_usn,recreated", [
    ("step7/labG_0.raw", 12016, True),
    ("step6/win11refs2gtargeted.raw", 10536, False),
])
def test_d2_usn_info_checkpoint_cursor(image, next_usn, recreated):
    r = subprocess.run([sys.executable, "-B", FOREFST, _img(image), "usn", "--info"],
                       capture_output=True, text=True, timeout=1800)
    assert "Traceback" not in r.stderr, r.stderr[-2000:]
    want = "    Next USN:       %d  (0 records%s at or past it: written after this checkpoint)" % (
        next_usn, " of the current journal" if recreated else "")
    assert want in r.stdout.splitlines(), r.stdout[-2500:]
    assert ("(the records of an earlier journal instance, above, are not compared)" in r.stdout) == recreated
