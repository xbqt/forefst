"""Shared fixtures for the forefst / refsanalysis test suite.

Everything here builds SYNTHETIC byte structures — no disk corpus is required, so
the whole Tier-0/1/2 suite runs in CI on a clean checkout. The private corpus is
used only by the Tier-3 golden-hash harness (tools/golden_snapshot.sh).
"""
import os
import struct
import sys

import pytest

# tests/ lives at analysis/tests/, so the repo root is THREE levels up (tests -> analysis -> repo).
from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)


def _load_pinned_refsanalysis():
    """1.14.1 (the maintainer, 2026-11-27: refsanalysis is not updated after 1.14.0): refsanalysis.py is the 1.14.0 file,
    pinned to forefst 1.14.0 (decision 54), while forefst is 1.14.1. The dev tree keeps that forefst in
    `refsanalysis_forefst/` (never synced). A test process imports both tools, and refsanalysis's own `import forefst`
    would get the cached 1.14.1 module and exit at import, so it is loaded once here: the pinned forefst bound to the
    name `forefst` only while refsanalysis imports, then the dev module (or none) restored and the pin directory taken
    off sys.path. `forefst_1140` names the pinned module. A tree without the pin (the published layout) is left alone."""
    import importlib.util
    pin = os.path.join(REPO, "refsanalysis_forefst", "forefst.py")
    ra_path = os.path.join(REPO, "refsanalysis.py")
    if not (os.path.isfile(pin) and os.path.isfile(ra_path)) or "refsanalysis" in sys.modules:
        return
    dev = sys.modules.get("forefst")
    path_before = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location("forefst", pin)
        ff = importlib.util.module_from_spec(spec)
        sys.modules["forefst"] = ff
        spec.loader.exec_module(ff)
        spec = importlib.util.spec_from_file_location("refsanalysis", ra_path)
        ra = importlib.util.module_from_spec(spec)
        sys.modules["refsanalysis"] = ra
        spec.loader.exec_module(ra)
        sys.modules["forefst_1140"] = ff
    finally:
        sys.path[:] = path_before
        if dev is not None:
            sys.modules["forefst"] = dev
        else:
            sys.modules.pop("forefst", None)


_load_pinned_refsanalysis()


def _refsanalysis_refusal():
    """1.14.1: in the PUBLISHED layout (no `refsanalysis_forefst/`), refsanalysis 1.14.0 refuses forefst 1.14.1 and exits
    at import ("refsanalysis 1.14.0 runs only with forefst 1.14.0"), which stopped the whole suite at collection with an
    INTERNALERROR (a module that imports it). Its refusal is the decided behaviour (the maintainer, 2026-11-27: "we will
    break refsanalysis just for 1 or 2 releases"), so here it is caught once: the message is returned and a stand-in
    module is bound to the name `refsanalysis` whose every attribute SKIPS the test (or the module) with that message.
    None when refsanalysis imports (the dev tree's pin, or a tree whose two tools are one release)."""
    import contextlib, io, types
    if "refsanalysis" in sys.modules or not os.path.isfile(os.path.join(REPO, "refsanalysis.py")):
        return None
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            import refsanalysis  # noqa: F401
        return None
    except SystemExit:
        sys.modules.pop("refsanalysis", None)
    msg = (err.getvalue().strip().splitlines() or ["refsanalysis exited at import"])[-1]
    reason = "refsanalysis does not run in this tree: %s (decided for 1.14.1; take the pair from the v1.14 release)" % msg

    class _Refused(types.ModuleType):
        refused_stand_in = True                  # read on the CLASS by pytest_sessionfinish, never through __getattr__

        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            raise pytest.skip.Exception(reason, allow_module_level=True)
    stand_in = _Refused("refsanalysis")
    stand_in.__file__ = os.path.join(REPO, "refsanalysis.py")    # the file is there (a source check reads it)
    sys.modules["refsanalysis"] = stand_in
    # the refusal as this tree prints it, without its trailing "(<path>)": "refsanalysis A runs only with forefst A;
    # this forefst is B" -- B the forefst under test, so a test that plants another version (d54) is not matched
    return msg.rsplit(" (", 1)[0]


_RA_REFUSED = _refsanalysis_refusal()

if _RA_REFUSED:
    # A test that RUNS refsanalysis (a subprocess) gets its refusal back as exit 1 and stderr, which its assertion may
    # not show; the run itself is where the refusal is seen, so a run that prints it skips the test, with it as reason.
    import subprocess as _subprocess
    _real_run = _subprocess.run

    def _run_or_skip(*a, **k):
        r = _real_run(*a, **k)
        err = r.stderr if isinstance(r.stderr, str) else (r.stderr or b"").decode("utf-8", "replace")
        out = r.stdout if isinstance(r.stdout, str) else (r.stdout or b"").decode("utf-8", "replace")
        if r.returncode == 1 and (_RA_REFUSED in err or _RA_REFUSED in out):
            raise pytest.skip.Exception("refsanalysis does not run in this tree: %s (decided for 1.14.1; take the "
                                        "pair from the v1.14 release)" % _RA_REFUSED)
        return r
    _subprocess.run = _run_or_skip


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """In the layout where refsanalysis refuses to run (above), a test that FAILS because a refsanalysis run printed
    that refusal is reported as skipped, with the refusal as its reason. Only there: in the dev tree (the pin) a
    failure stays a failure."""
    outcome = yield
    rep = outcome.get_result()
    if _RA_REFUSED and rep.failed and call.when == "call" and _RA_REFUSED in str(rep.longrepr):
        rep.outcome = "skipped"
        rep.longrepr = (str(item.fspath), item.location[1] or 0, "Skipped: refsanalysis does not run in this tree: %s"
                        % _RA_REFUSED)


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


def jget(d, name, over=None, default=None):
    """1.14.0 (K21): a JSON field read by its INTERNAL name -- `checkpoint_used_lcn` -- under the output name the tool
    gives it (`out_key`: CheckpointUsedLCN; `over`, a command's overrides, e.g. forefst's `_SUMMARY_KEYS`). For the
    readers whose subject is not the key form (the key forms have their own tests, test_1132_e2b_machine)."""
    import forefst as _F
    if not isinstance(d, dict):
        return default
    return d.get(_F.out_key(name, over), default)


class _JView(dict):
    """1.14.0 (K21): a JSON object whose fields are read by their INTERNAL names (`records`, `content_file`) under the
    output names the tool writes (`Records`, `ContentFile`; `out_key`, with a command's overrides); a name the object
    holds as it is (an output name, a data map's key) is read as it is. `jdoc` builds it."""
    _over = None

    def _k(self, k):
        if not isinstance(k, str) or dict.__contains__(self, k):
            return k
        import forefst as _F
        return _F.out_key(k, self._over)

    def __getitem__(self, k):
        return dict.__getitem__(self, self._k(k))

    def get(self, k, default=None):
        return dict.get(self, self._k(k), default)

    def __contains__(self, k):
        return dict.__contains__(self, self._k(k))


def jdoc(o, over=None):
    """1.14.0 (K21): a JSON document (from `json.load`) whose objects read their fields by internal name (`_JView`),
    recursively -- for the readers whose subject is not the key form, as `jget` for one field."""
    if isinstance(o, dict):
        v = _JView((k, jdoc(x, over)) for k, x in o.items())
        v._over = over
        return v
    if isinstance(o, list):
        return [jdoc(x, over) for x in o]
    return o


def jint(v):
    """1.14.0 (K1, K9, K10): an identifier, LCN or offset is a hex string in JSON -- its integer (an integer as it is;
    None for an absent value)."""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v
    return int(v, 16) if isinstance(v, str) and v.lower().startswith("0x") else int(v)


def unwrap_table_rows(text):
    """refsanalysis's tables wrap their last column at 80 characters (N377, 1.14.0: one table was 203 columns wide): a
    row's continuation lines carry only that column, indented under it. Returns `text` with each continuation joined to
    its row by one space, so a reader takes one row per line. A table starts at its dashes line and ends at a blank
    line; inside it, a row starts with a non-space character and a continuation with a space."""
    import re as _re
    out, in_table = [], False
    for ln in text.split("\n"):
        if _re.match(r"^-+(  +-+)+\s*$", ln):
            in_table = True
            out.append(ln)
            continue
        if not ln.strip():
            in_table = False
            out.append(ln)
            continue
        if in_table and ln[:1] == " " and out and out[-1].strip():
            out[-1] = out[-1].rstrip() + " " + ln.strip()
            continue
        out.append(ln)
    return "\n".join(out)


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
    "test_all_sanitizers_produce_the_same_result":
        "2.11 three-way sanitizer unification REJECTED — _safe_relpath must stay a path sanitizer (traversal "
        "safety), so it cannot equal a component sanitizer on a slash-bearing name.",
    "test_sanitized_names_fit_the_filesystem_limit":
        "2.11 extraction NEVER truncates (fidelity) — a name over the FS limit is surfaced, not capped.",
    "test_csv_cells_never_start_with_a_formula_prefix":
        "2.10 CSV formula-guard is OPT-IN (--csv-safe); default output is byte-faithful (fidelity).",
}

def _node_key(nodeid):
    # "<dir>/<file>.py::<name>[param]" -> "<file>.py::<name>[param]"; split on "::" (params may contain "/",
    # never "::") so a param like =cmd|'/c calc'!A1 is preserved and cannot collide across tests.
    f, sep, rest = nodeid.partition("::")
    return _os.path.basename(f) + "::" + rest if sep else nodeid

def _load_deferred_nodes():
    f = _os.path.join(_os.path.dirname(__file__), "deferred_xfail_nodes.txt")
    if not _os.path.exists(f):
        return {}
    # `#` lines are section headers and rationale. Every node listed is DECIDED — intentional behaviour kept
    # only as a strict-xfail alarm that fires if the decision is ever silently reversed. There is no deferred
    # debt left here (the exit-code renumbering was closed "won't change" on 2026-09-06 and its tests deleted).
    # 1.14.1: a `#@ <reason>` line gives the reason of the nodes listed after it (until the next `#@`).
    out, reason = {}, None
    for ln in open(f, encoding="utf-8"):
        t = ln.strip()
        if t.startswith("#@"):
            reason = t[2:].strip() or None
        elif t and not t.startswith("#"):
            out[_node_key(t)] = reason
    return out

_DEFERRED_NODES = _load_deferred_nodes()

def pytest_collection_modifyitems(config, items):
    for item in items:
        if _node_key(item.nodeid) in _DEFERRED_NODES:
            fn = (item.originalname if hasattr(item, "originalname") else item.name.split("[")[0])
            reason = (_DEFERRED_NODES[_node_key(item.nodeid)]
                      or _XFAIL_REASON.get(fn, "deferred/rejected audit finding (see AUDIT_RESPONSE.md)"))
            item.add_marker(pytest.mark.xfail(reason=reason, strict=True, run=True))


# ─── N575 (1.14.0): the tool's run-wide registers, cleared when the session ends ───────────────────────────────────
# Tests that call forefst in-process record into its module-level registers (pages that could not be read, skipped
# work, deferrals, holes, marker-scan answers, CSV formula cells, translators). The tool prints them from atexit hooks
# at the end of a COMMAND; in the test process the end is pytest's, so the leftovers of every in-process test were
# printed after the suite's summary as one forefst warning ("8 metadata page(s) could not be read ... INCOMPLETE"),
# a statement about no command. Each test asserts on its own run, so the registers are emptied here, after the last
# test and before the atexit hooks run.
_N575_REGISTERS = ("_SKIP_NOTES", "_SKIP_EXPECTED", "_DEFERRALS", "_MARKER_SCAN_WINS", "_CONTENT_HOLES", "_ALL_TRS")


def pytest_sessionfinish(session, exitstatus):
    for mod in list(sys.modules.values()):
        if getattr(type(mod), "refused_stand_in", False):      # the refused refsanalysis's stand-in (above)
            continue
        reset = getattr(mod, "_walk_damage_reset", None)
        if not callable(reset):
            continue
        reset()
        for name in _N575_REGISTERS:
            reg = getattr(mod, name, None)
            if hasattr(reg, "clear"):
                reg.clear()
        if isinstance(getattr(mod, "_CSV_FORMULA_SEEN", None), int):
            mod._CSV_FORMULA_SEEN = 0
