"""Shared fixtures for the forefst / refsanalysis test suite.

Everything here builds SYNTHETIC byte structures — no disk corpus is required, so
the whole Tier-0/1/2 suite runs in CI on a clean checkout. The private corpus is
used only by the Tier-3 golden-hash harness (tools/golden_snapshot.sh).
"""
import os
import struct
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

SECTOR = 512


# ─── raw structure builders ──────────────────────────────────────────────────

def make_vbr(bytes_per_sector=512, sectors_per_cluster=8, vmaj=3, vmin=14,
             signature=b"ReFS", bytes_per_container=0x4000000):
    """A 512-byte ReFS VBR. Defaults are a valid 4 KiB-cluster v3.14 volume."""
    b = bytearray(SECTOR)
    b[3:3 + len(signature)] = signature
    struct.pack_into("<I", b, 0x20, bytes_per_sector)
    struct.pack_into("<I", b, 0x24, sectors_per_cluster)
    b[0x28] = vmaj
    b[0x29] = vmin
    struct.pack_into("<H", b, 0x2A, 2)
    struct.pack_into("<Q", b, 0x40, bytes_per_container)
    return bytes(b)


def make_gpt(num_parts=128, entry_size=128, part_lba=2, partitions=()):
    """Sector 0 (protective MBR) + sector 1 (GPT header) + the entry array.

    `partitions` is a sequence of (type_guid, first_lba, last_lba, name).
    """
    mbr = bytearray(SECTOR)
    hdr = bytearray(SECTOR)
    hdr[0:8] = b"EFI PART"
    struct.pack_into("<Q", hdr, 72, part_lba)
    struct.pack_into("<I", hdr, 80, num_parts)
    struct.pack_into("<I", hdr, 84, entry_size)

    real = max(entry_size, 128)
    entries = bytearray(real * max(len(partitions), 1))
    for i, (guid, first, last, name) in enumerate(partitions):
        off = i * real
        entries[off:off + 16] = guid
        struct.pack_into("<Q", entries, off + 32, first)
        struct.pack_into("<Q", entries, off + 40, last)
        nm = name.encode("utf-16-le")[:72]
        entries[off + 56:off + 56 + len(nm)] = nm
    return bytes(mbr) + bytes(hdr) + bytes(entries)


def make_msb_page(rows, is_inner=False, cluster_size=4096,
                  key_len_override=None, val_len_override=None):
    """A minimal MSB+ B+-tree page.

    rows: list of (key_bytes, value_bytes).
    key_len_override / val_len_override let a test declare a length that runs
    past the end of the page, to exercise bounds checking.
    """
    page = bytearray(cluster_size)
    page[0:4] = b"MSB+"
    thoff = 0x60
    struct.pack_into("<I", page, 0x50, thoff - 0x50)

    astart, aend = 40, 40 + 4 * len(rows)
    tbl = [0] * 10
    tbl[3] = 0x100 if is_inner else 0
    tbl[4] = astart
    tbl[8] = aend
    struct.pack_into("<10I", page, thoff, *tbl)

    rowbase = thoff + aend + 16
    stride = max(0x40, (cluster_size - rowbase) // max(len(rows), 1))
    for i, (k, v) in enumerate(rows):
        ro = rowbase + i * stride
        struct.pack_into("<H", page, thoff + astart + i * 4, ro - thoff)
        ko, vo = 16, 16 + len(k)
        kl = key_len_override if key_len_override is not None else len(k)
        vl = val_len_override if val_len_override is not None else len(v)
        struct.pack_into("<I6H", page, ro, 0, ko, kl, 0, vo, vl, 0)
        page[ro + ko:ro + ko + len(k)] = k
        page[ro + vo:ro + vo + len(v)] = v
    return bytes(page)


def child_pointer(*lcns):
    """A 32-byte inner-node value holding up to four child cluster numbers."""
    padded = (list(lcns) + [0, 0, 0, 0])[:4]
    return struct.pack("<4Q", *padded)


# ─── image fixtures ──────────────────────────────────────────────────────────

GPT_BASIC_DATA = bytes.fromhex("a2a0d0ebe5b9334487c068b6b72699c7")


@pytest.fixture
def tmp_image(tmp_path):
    """Factory: write bytes to a temp file and return its path."""
    counter = {"n": 0}

    def _make(data, name=None):
        counter["n"] += 1
        p = tmp_path / (name or f"img{counter['n']}.raw")
        p.write_bytes(data)
        return str(p)

    return _make


@pytest.fixture
def raw_refs_image(tmp_image):
    """A raw (no GPT) image whose sector 0 is a well-formed ReFS VBR.

    Structurally valid down to the VBR only — the superblock is absent, so
    bootstrap must fail with a clean ValueError, never a traceback.
    """
    return tmp_image(make_vbr() + b"\x00" * (1 << 20))


@pytest.fixture
def zero_cluster_image(tmp_image):
    """VBR advertising bytes_per_sector = 0  ->  cluster size 0.  (Finding 1.1)"""
    return tmp_image(make_vbr(bytes_per_sector=0, sectors_per_cluster=0)
                     + b"\x00" * (1 << 20))


@pytest.fixture
def gpt_bomb_image(tmp_image):
    """GPT header advertising 0xFFFFFFFF entries of 0xFFFF bytes.  (Finding 1.2)"""
    return tmp_image(make_gpt(num_parts=0xFFFFFFFF, entry_size=0xFFFF)
                     + b"\x00" * (1 << 20))


@pytest.fixture
def ntfs_then_refs_image(tmp_image):
    """Two Basic-Data partitions: NTFS first, ReFS second.  (Finding 1.3)"""
    ntfs = bytearray(SECTOR)
    ntfs[3:7] = b"NTFS"
    parts = [(GPT_BASIC_DATA, 2048, 4095, "Windows"),
             (GPT_BASIC_DATA, 4096, 8191, "Data")]
    img = bytearray(make_gpt(num_parts=2, partitions=parts))
    img.extend(b"\x00" * (8192 * SECTOR - len(img)))
    img[2048 * SECTOR:2048 * SECTOR + SECTOR] = ntfs
    img[4096 * SECTOR:4096 * SECTOR + SECTOR] = make_vbr()
    return tmp_image(bytes(img))


@pytest.fixture
def tiny_image(tmp_image):
    """Below the 4096-byte floor validate_image enforces."""
    return tmp_image(b"\x00" * 100)


# ── Deferred/rejected findings: xfail EXACTLY the known-failing (test, param) node IDs ────────────────
# These findings were DELIBERATELY not adopted (see AUDIT_RESPONSE.md); their tests encode the auditor's
# design preference against a project constraint (forensic fidelity, or forefst being one self-contained file).
# We xfail the PRECISE node IDs that fail — never a whole parametrized function — so the params that legitimately
# pass stay live and a future regression on them still surfaces as a real FAILURE. If a deferred decision is
# reversed, its node XPASSes and pytest flags it for review. The node list lives in deferred_xfail_nodes.txt.
import os as _os

_XFAIL_REASON = {
    "test_unknown_flag_is_always_exit_2":
        "2.13 exit-code renumbering DEFERRED — 2 is a documented, scriptable 'findings' code; forensic commands "
        "exit 1 on a bad flag. Contract documented + locked instead of renumbered.",
    "test_missing_option_value_says_so":
        "2.9 exit code is part of 2.13 (DEFERRED) — the message is fixed; the exit code stays 1.",
    "test_all_sanitizers_produce_the_same_result":
        "2.11 three-way sanitizer unification REJECTED — _safe_relpath must stay a path sanitizer (traversal "
        "safety), so it cannot equal a component sanitizer on a slash-bearing name.",
    "test_sanitized_names_fit_the_filesystem_limit":
        "2.11 extraction NEVER truncates (fidelity) — a name over the FS limit is surfaced, not capped.",
    "test_csv_cells_never_start_with_a_formula_prefix":
        "2.10 CSV formula-guard is OPT-IN (--csv-safe); default output is byte-faithful (fidelity).",
    "test_no_duplicated_function_bodies_across_modules":
        "4.5 refs/ package REJECTED — forefst.py stays one self-contained file; some duplication is intentional.",
}

def _node_key(nodeid):
    # "<dir>/<file>.py::<name>[param]" -> "<file>.py::<name>[param]"; split on "::" (params may contain "/",
    # never "::") so a param like =cmd|'/c calc'!A1 is preserved and cannot collide across tests.
    f, sep, rest = nodeid.partition("::")
    return _os.path.basename(f) + "::" + rest if sep else nodeid

def _load_deferred_nodes():
    f = _os.path.join(_os.path.dirname(__file__), "deferred_xfail_nodes.txt")
    if not _os.path.exists(f):
        return set()
    return {_node_key(ln.strip()) for ln in open(f) if ln.strip()}

_DEFERRED_NODES = _load_deferred_nodes()

def pytest_collection_modifyitems(config, items):
    for item in items:
        if _node_key(item.nodeid) in _DEFERRED_NODES:
            fn = (item.originalname if hasattr(item, "originalname") else item.name.split("[")[0])
            reason = _XFAIL_REASON.get(fn, "deferred/rejected audit finding (see AUDIT_RESPONSE.md)")
            item.add_marker(pytest.mark.xfail(reason=reason, strict=True, run=True))
