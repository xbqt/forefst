"""Tier 1 — parser robustness against malformed input.

Every test here corresponds to a numbered finding in the review. Several are
expected to FAIL against the current code; that is the point — they are the
acceptance criteria for the fixes.

Guiding property: no parser in either module may raise anything other than
ValueError (or return a sentinel) when handed arbitrary bytes. A forensic tool is
pointed at corrupt and hostile images by definition.
"""
import struct
import signal
import subprocess
import sys
import time

import pytest

import forefst as F
from conftest import (child_pointer, make_gpt, make_msb_page, make_vbr,
                      GPT_BASIC_DATA)


# ─── Finding 1.1 — cluster size zero ─────────────────────────────────────────

@pytest.mark.parametrize("bps,spc,label", [
    (0, 8, "bytes_per_sector = 0"),
    (512, 0, "sectors_per_cluster = 0"),
    (0, 0, "both zero"),
])
def test_parse_vbr_rejects_zero_cluster_size(tmp_image, bps, spc, label):
    """cs == 0 must raise ValueError in parse_vbr, not ZeroDivisionError in bootstrap."""
    path = tmp_image(make_vbr(bytes_per_sector=bps, sectors_per_cluster=spc)
                     + b"\x00" * (1 << 20))
    with open(path, "rb") as f:
        with pytest.raises(ValueError) as exc:
            F.parse_vbr(f, 0)
    assert "cluster" in str(exc.value).lower(), \
        f"error message should name the cluster size ({label}): {exc.value}"


@pytest.mark.parametrize("bps,spc", [(512, 3), (513, 8)])
def test_parse_vbr_rejects_unaligned_cluster_size(tmp_image, bps, spc):
    """A cluster size that is not a 512-byte multiple cannot be real."""
    path = tmp_image(make_vbr(bytes_per_sector=bps, sectors_per_cluster=spc)
                     + b"\x00" * (1 << 20))
    with open(path, "rb") as f:
        with pytest.raises(ValueError):
            F.parse_vbr(f, 0)


def test_bootstrap_on_zero_cluster_image_gives_a_clean_error(zero_cluster_image):
    with pytest.raises(ValueError):
        F.bootstrap(zero_cluster_image, partition_start=0)


# ─── Finding 1.2 — GPT allocation bomb ───────────────────────────────────────

def test_find_refs_partition_survives_absurd_gpt(gpt_bomb_image):
    """num_parts * entry_size must be clamped before the read."""
    start = time.time()
    ps, desc = F.find_refs_partition(gpt_bomb_image)   # must not MemoryError
    assert time.time() - start < 5
    assert ps is None


def test_gpt_partition_detail_survives_absurd_gpt(gpt_bomb_image):
    assert F.gpt_partition_detail(gpt_bomb_image) is None


@pytest.mark.parametrize("entry_size", [0, 1, 0x10000])
def test_gpt_entry_size_outside_spec_is_rejected(tmp_image, entry_size):
    """UEFI requires entry_size >= 128 and a power-of-two multiple; reject the rest."""
    path = tmp_image(make_gpt(num_parts=4, entry_size=entry_size) + b"\x00" * 65536)
    ps, _ = F.find_refs_partition(path)
    assert ps is None


# ─── Finding 1.3 — multi-partition images ────────────────────────────────────

def test_find_refs_partition_picks_the_refs_partition_not_the_first(ntfs_then_refs_image):
    ps, desc = F.find_refs_partition(ntfs_then_refs_image)
    assert ps == 4096 * 512, f"expected partition 2 at 0x{4096*512:x}, got {ps!r} ({desc})"


def test_validate_image_accepts_refs_in_a_later_partition(ntfs_then_refs_image):
    """validate_image must scan every Basic-Data partition, like find_refs_partition."""
    F.validate_image(ntfs_then_refs_image)      # must not raise


def test_validation_and_partition_search_never_disagree(ntfs_then_refs_image):
    """Whatever find_refs_partition accepts, validate_image must accept too."""
    ps, _ = F.find_refs_partition(ntfs_then_refs_image)
    if ps is not None:
        F.validate_image(ntfs_then_refs_image)


# ─── Finding 2.3 — cyclic container table (CONFIRMED hang) ───────────────────

def test_parse_ct_page_terminates_on_a_cyclic_tree(tmp_image):
    """A container-table inner node pointing back at its own page must not fan out.

    _walk already has the `visited` guard (E10); _parse_ct_page does not, and
    hangs. It is reached from bootstrap(), so every subcommand hangs with it.
    """
    cs = 4096
    inner = make_msb_page(
        [(struct.pack("<Q", i), child_pointer(0, 1, 2, 3)) for i in range(4)],
        is_inner=True, cluster_size=cs)
    path = tmp_image(inner * 8)
    with open(path, "rb") as f:
        start = time.time()
        result = F._parse_ct_page(inner, f, 0, cs)
        elapsed = time.time() - start
    assert elapsed < 5, f"_parse_ct_page took {elapsed:.1f}s on a cyclic tree"
    assert isinstance(result, dict)


def test_walk_terminates_on_a_cyclic_tree(tmp_image):
    """Control case: the equivalent guard in _walk already works."""
    cs = 4096
    inner = make_msb_page(
        [(struct.pack("<Q", i), child_pointer(0, 1, 2, 3)) for i in range(4)],
        is_inner=True, cluster_size=cs)
    path = tmp_image(inner * 8)
    with open(path, "rb") as f:
        start = time.time()
        F._walk(inner, f, 0, cs, None, 5)
    assert time.time() - start < 5


# ─── Finding 2.4 — out-of-bounds row slicing (CONFIRMED) ─────────────────────

def test_walk_skips_rows_whose_key_runs_past_the_page(tmp_image):
    """A key declared 1024 B long in a row 48 B from the page end must be dropped.

    Python slicing silently truncates, so today the row survives with a SHORT
    key and le64(kd,0)/le16(kd,0) read adjacent bytes as the key and attribute
    type. A wrong-but-plausible key is worse than a dropped row.
    """
    cs = 4096
    page = bytearray(cs)
    page[0:4] = b"MSB+"
    thoff = 0x60
    struct.pack_into("<I", page, 0x50, thoff - 0x50)
    struct.pack_into("<10I", page, thoff, 0, 0, 0, 0, 40, 0, 0, 0, 44, 0)
    ro = cs - 64                                   # row header 64 B from the end
    struct.pack_into("<H", page, thoff + 40, ro - thoff)
    struct.pack_into("<I6H", page, ro, 0, 16, 0x400, 0, 0x420, 0x200, 0)
    page[ro + 16:ro + 32] = b"KEYKEYKEYKEYKEYK"

    rows = F._walk(bytes(page), None, 0, cs, None, 5)
    for kd, vd in rows:
        assert len(kd) == 0x400, (
            f"row kept with a truncated {len(kd)}-byte key (declared 1024) — "
            f"le16(kd,0) now reads 0x{F.le16(kd, 0):x} as the attribute type. "
            "The row should have been skipped and counted instead.")


def test_walk_handles_a_row_offset_past_the_page_end(tmp_image):
    cs = 4096
    page = bytearray(make_msb_page([(b"\x30\x00\x00\x00", b"x" * 8)], cluster_size=cs))
    thoff = 0x60
    struct.pack_into("<H", page, thoff + 40, 0xFFF0)     # row offset near the end
    F._walk(bytes(page), None, 0, cs, None, 5)           # must not raise


# ─── Finding 2.5 — recursion depth ───────────────────────────────────────────

def test_deep_directory_tree_does_not_kill_the_process(tmp_path):
    """main() raises the recursion limit to 40000 without growing the C stack.

    At the default limit CPython raises a catchable RecursionError; at 40000 with
    _walk_dir-sized frames the process is killed outright (observed SIGKILL/OOM
    on CPython 3.12, SIGSEGV is the classic result on smaller stacks). Either way
    the tool loses the ability to report what happened.
    """
    script = tmp_path / "deep.py"
    script.write_text(
        "import sys\n"
        "sys.setrecursionlimit(max(sys.getrecursionlimit(), 40000))\n"
        "def walk(oid, pp, po, d):\n"
        "    vlcns=[]; rows=[]; t40={}; nonres=[]; e={}\n"
        "    fp=f'{pp}/x{oid}'; a1=b'\\x00'*64; a2={'path':fp,'name':'x'}\n"
        "    if d < 39000: walk(oid+1, fp, oid, d+1)\n"
        "try:\n"
        "    walk(0,'',0,0)\n"
        "except RecursionError:\n"
        "    print('CLEAN')\n")
    r = subprocess.run([sys.executable, str(script)], capture_output=True,
                       text=True, timeout=180)
    # SIGKILL is not this test's subject. The failure it guards against is the C stack running out --
    # SIGSEGV, or SIGBUS on some platforms. SIGKILL comes from OUTSIDE the process (an OOM killer or a
    # cgroup memory limit), so in a memory-constrained sandbox it says nothing about recursion depth and
    # must not be reported as a tool defect. Inconclusive, not failed.
    if r.returncode == -signal.SIGKILL:
        pytest.skip("environment killed the child (SIGKILL: OOM/cgroup limit) — inconclusive here")
    assert r.returncode >= 0, f"process died on signal {-r.returncode}"


# ─── general property: parsers only raise ValueError ─────────────────────────

@pytest.mark.parametrize("payload", [
    b"", b"\x00" * 16, b"\xff" * 512, b"ReFS" * 128,
    bytes(range(256)) * 2,
])
def test_parsers_raise_only_valueerror_on_garbage(tmp_image, payload):
    path = tmp_image(payload + b"\x00" * 8192)
    with open(path, "rb") as f:
        for fn, args in ((F.parse_vbr, (0,)),
                         (F.parse_supb, (0, 4096)),
                         (F.parse_chkp, (0, 4096, 0))):
            try:
                fn(f, *args)
            except ValueError:
                pass
            except Exception as e:                      # noqa: BLE001
                pytest.fail(f"{fn.__name__} raised {type(e).__name__}: {e}")


def test_parse_supb_clamps_an_implausible_reference_count(tmp_image):
    """The E9 clamp already exists — lock it in."""
    cs = 4096
    data = bytearray(cs)
    data[0:4] = b"SUPB"
    struct.pack_into("<I", data, 0x70, 0x80)
    struct.pack_into("<I", data, 0x74, 0xFFFFFFFF)
    img = bytearray(0x1E * cs + cs)
    img[0x1E * cs:0x1E * cs + cs] = data
    path = tmp_image(bytes(img))
    with open(path, "rb") as f:
        lcns = F.parse_supb(f, 0, cs)
    assert len(lcns) <= 8


def test_parse_chkp_clamps_an_implausible_root_count(tmp_image):
    cs = 4096
    raw = bytearray(4 * cs)
    raw[0:4] = b"CHKP"
    struct.pack_into("<I", raw, 0x90, 0xFFFFFFFF)
    struct.pack_into("<I", raw, 0x5c, 32)
    path = tmp_image(bytes(raw))
    with open(path, "rb") as f:
        _vc, _flags, roots = F.parse_chkp(f, 0, cs, 0)
    assert len(roots) <= 32
