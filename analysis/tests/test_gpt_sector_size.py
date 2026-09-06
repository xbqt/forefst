"""GPT is at LBA 1, so its byte offset depends on the disk's logical sector size.

512-native and 512e media put it at byte 512; 4Kn media put it at 4096. These tests build tiny synthetic
images of both shapes — no corpus image required — and check that the reader finds the partition either way.

The 4Kn path is otherwise **unexercised**: this project has no 4Kn media, so these synthetic images are the
only thing standing behind it. They prove the arithmetic is consistent, not that a real 4Kn ReFS volume
parses end to end.
"""
import struct

import pytest

import forefst as F

GPT_BASIC = bytes.fromhex("a2a0d0ebe5b9334487c068b6b72699c7")


def _build(path, lba, part_lba=64, entries_lba=2, esz=128, nparts=128):
    """A minimal GPT: header at LBA 1, one Basic-Data entry, a ReFS VBR signature at the partition start."""
    buf = bytearray((part_lba + 8) * lba)
    hdr = bytearray(92)
    hdr[0:8] = b"EFI PART"
    struct.pack_into("<Q", hdr, 72, entries_lba)
    struct.pack_into("<I", hdr, 80, nparts)
    struct.pack_into("<I", hdr, 84, esz)
    buf[lba:lba + len(hdr)] = hdr
    ent = bytearray(esz)
    ent[0:16] = GPT_BASIC
    struct.pack_into("<Q", ent, 32, part_lba)
    struct.pack_into("<Q", ent, 40, part_lba + 7)
    buf[entries_lba * lba: entries_lba * lba + esz] = ent
    vbr = bytearray(512)
    vbr[3:7] = b"ReFS"
    buf[part_lba * lba: part_lba * lba + 512] = vbr
    path.write_bytes(bytes(buf))
    return part_lba * lba


@pytest.mark.parametrize("lba", [512, 4096])
def test_find_refs_partition_honours_sector_size(tmp_path, lba):
    img = tmp_path / f"synth_{lba}.img"
    expected = _build(img, lba)
    start, _desc = F.find_refs_partition(str(img))
    assert start == expected, f"LBA {lba}: partition start {start!r}, expected {expected}"


@pytest.mark.parametrize("lba", [512, 4096])
def test_gpt_detail_scales_with_sector_size(tmp_path, lba):
    img = tmp_path / f"detail_{lba}.img"
    expected = _build(img, lba)
    det = F.gpt_partition_detail(str(img))
    assert det is not None and det["start_bytes"] == expected
    assert det["size_bytes"] == 8 * lba          # 8 LBAs, scaled by the sector size


@pytest.mark.parametrize("lba", [512, 4096])
def test_validate_image_accepts_both_sector_sizes(tmp_path, lba):
    img = tmp_path / f"validate_{lba}.img"
    _build(img, lba)
    F.validate_image(str(img))                    # raises on failure


def test_no_gpt_still_reports_cleanly(tmp_path):
    """A file with no GPT at either offset must still be rejected with the original message."""
    img = tmp_path / "empty.img"
    img.write_bytes(bytes(1 << 16))
    start, msg = F.find_refs_partition(str(img))
    assert start is None and "no GPT partition table found" in msg
