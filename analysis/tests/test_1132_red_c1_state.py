"""1.13.2 (ships as 1.14.0) RED cases, wave C step C1, area `state`: N426 (module registers that outlive their volume)
and N434 N-6 (the $VOLUME_INFORMATION version: one definition and its single_source.tsv row).

Read first: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md`, `fixes/WAVEC_INVENTORY.md` and `fixes/WAVEC_CENSUS.md` (the
N426 row: `_OBJ_ROOT_REF` / `_OBJ_ROOT_VERIFIED` / `_OBJ_ROOT_LCNS` filled by `build_object_map`; `_CHKP_STALE` and
`_findings(...)` read by `cmd_integrity`; ra `cmd_supb` / `cmd_chkp` / `cmd_containers` calling `parse_supb` directly),
`fixes/FIX_GB_part3d.md` section 10 (open items O1, O2, O6), `fixes/REVIEW_GB_correctness.md` N-6. Report:
`analysis/reports/v1.13.2/fixes/RED_C1.md`.

  N426  "every module register listed in a table with its owner (volume, view or run) and reset where it belongs"
        (RUNNING_LOG N426; LATER_GROUPS_TOLD "N426 (first code item)"). Two volumes, one process:
          * `_OBJ_ROOT_VERIFIED` is never cleared: an object verified on one volume is never verified on the next, so an
            ALTERED root page of the second volume passes (O1);
          * `files --cow-before`: `cow_recovery`'s bootstrap of the before-image replaces the after-image's root-page
            digests (`_OBJ_ROOT_REF`), so the after-image's own unaltered page is reported ALTERED (O1, a real CLI path);
          * `integrity` reads `_CHKP_STALE` and `_findings("page-reference mismatch")`, run registers, as facts of the
            volume it reports: an earlier volume's stale checkpoint or altered page becomes this volume's verdict (O2);
          * refsanalysis `supb` calls `parse_supb` directly, so `_SUPB_FELL_BACK` of an earlier volume names the copy in
            use of the next (O6);
          * the table itself: one mapping, register -> owner, covering every module register.
  N434 N-6  the version stamps of the $VOLUME_INFORMATION row (OID 0x500, key 0x0520, +0x80/+0x81) are read by three
        functions (forefst `read_volume_information` and `cmd_fastsummary`, refsanalysis `cmd_summary`); one definition,
        named in single_source.tsv.

In-process nodes give every run register a fresh value and restore it (monkeypatch). Two corpus images (read-only):
step1/win11refsmini (ReFS 3.14) and step1/win10refsmini (ReFS 3.4), both 4 KiB clusters, both with a CRC64 digest for
OID 0x600's root page in their Object Tables; synthetic volumes are test_1132_red_a_bootstrap's.
"""
import ast
import contextlib
import io
import os
import re
import sys

from _repo import REPO                                   # layout-independent; see _repo.py
import _unwrap as UW                                 # A3 (1.14.0): what the tool wrapped, read as one line
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402
import test_1132_red_a_bootstrap as AB                   # noqa: E402
import test_1132_red_mlog_chkp as MC                     # noqa: E402
import test_1132_red_waveb_rest as WR                    # noqa: E402  (_n425_fresh, _n425_vols)
import test_1132_red_c1_objtable as OT                   # noqa: E402  (planted copies, single_source rows)

RedFixtureError, KeptPropertyBroken = AB.RedFixtureError, AB.KeptPropertyBroken
_fx, _keep = AB._fx, AB._keep
_red = OT._red

IMG_A = "step1/win11refsmini.raw"
IMG_B = "step1/win10refsmini.raw"
ROOT_DIR = 0x600


def _fresh(monkeypatch):
    """Every register forefst's exit rule reads, the journal harness's list, the run lists -- and the Object-Table root
    registers -- fresh, restored afterwards."""
    WR._n425_fresh(monkeypatch)
    for name in ("_OBJ_ROOT_REF", "_OBJ_ROOT_LCNS"):
        monkeypatch.setattr(F, name, {}, raising=False)
    monkeypatch.setattr(F, "_OBJ_ROOT_VERIFIED", set(), raising=False)


def _quiet_boot(path, ps=None):
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        return F.bootstrap(path, ps)


def _root_page(boot, oid):
    f, ps, cs, tr = boot[0], boot[1], boot[2], boot[3]
    return b"".join(F._seek_read(f, ps + tr.tr(v) * cs, cs) for v in boot[5][oid])


def _ot_rows(page):
    """(key, value) of every row of one MSB+ leaf page, read by this module (the page header's table offset at +0x50,
    the row-offset array between the table header's +0x10 and +0x20)."""
    thoff = 0x50 + F.le32(page, 0x50)
    astart, aend = F.le32(page, thoff + 0x10), F.le32(page, thoff + 0x20)
    out = []
    for i in range((aend - astart) // 4):
        ro = thoff + F.le16(page, thoff + astart + 4 * i)
        ko, kl, vo, vl = (F.le16(page, ro + 4), F.le16(page, ro + 6), F.le16(page, ro + 10), F.le16(page, ro + 12))
        out.append((bytes(page[ro + ko:ro + ko + kl]), bytes(page[ro + vo:ro + vo + vl])))
    return out


def _premise_root(boot, oid, name):
    """The volume's object `oid` has a CRC64 digest in its Object Table (the row's value +0x44 length 8, +0x48 digest;
    this module's own read of the Object Table's root page, a single leaf on both images) and its root page matches
    it. Returns (the root page, the digest)."""
    f, ps, cs, tr, roots = boot[0], boot[1], boot[2], boot[3], boot[4]
    ot = b"".join(F._seek_read(f, ps + tr.tr(v) * cs, cs) for v in roots[0])
    _fx(ot[:4] == b"MSB+" and not (F.le32(ot, 0x50 + F.le32(ot, 0x50) + 0x0C) & 0x100),
        "%s: the Object Table's root page is not one MSB+ leaf" % name)
    rows = [vd for kd, vd in _ot_rows(ot) if len(kd) >= 16 and F.le64(kd, 8) == oid]
    _fx(len(rows) == 1 and F.le32(rows[0], 0x44) == 8, "%s: no single row with a CRC64 digest for 0x%x" % (name, oid))
    digest = rows[0][0x48:0x50]
    pg = _root_page(boot, oid)
    _fx(F.refs_crc64(pg) == int.from_bytes(digest, "little"),
        "%s: object 0x%x's root page does not match its Object Table digest" % (name, oid))
    return pg, digest


# ─── N426 (O1): _OBJ_ROOT_VERIFIED ───────────────────────────────────────────────────────────────────────────────

def test_n426_control_an_altered_root_page_is_reported_when_its_volume_is_read_alone(monkeypatch):
    """Not a RED: the premise. Volume B alone: its OID 0x600 root page, one byte altered, fails its digest (False, a
    'page-reference mismatch' finding)."""
    _fresh(monkeypatch)
    b = _quiet_boot(MC.corpus(IMG_B))
    try:
        pg, _ref = _premise_root(b, ROOT_DIR, "B")
        bad = bytearray(pg)
        bad[0x2000] ^= 0x01
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ok = F.verify_object_root(ROOT_DIR, bytes(bad))
    finally:
        b[0].close()
    _keep(ok is False and F._findings("page-reference mismatch"), "B alone: an altered root page verifies (%r)" % ok)


# RED 1.13.2 N426: _OBJ_ROOT_VERIFIED is never cleared: an object verified on one volume is never checked on the next -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n426_an_altered_root_page_of_the_second_volume_is_reported(monkeypatch):
    _fresh(monkeypatch)
    a = _quiet_boot(MC.corpus(IMG_A))
    try:
        _premise_root(a, ROOT_DIR, "A")
        F.walk_bplus(a[0], a[1], a[2], a[3], a[5][ROOT_DIR], oid=ROOT_DIR)      # the walk every lister makes
    finally:
        a[0].close()
    b = _quiet_boot(MC.corpus(IMG_B))
    try:
        pg, _ref = _premise_root(b, ROOT_DIR, "B")
        bad = bytearray(pg)
        bad[0x2000] ^= 0x01
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ok = F.verify_object_root(ROOT_DIR, bytes(bad))
    finally:
        b[0].close()
    assert ok is False, "volume B's OID 0x600 root page, one byte altered, no longer matches B's digest: after volume " \
        "A in the same process verify_object_root returns %r -- A's 'already verified' mark (never cleared) skips the " \
        "check (N426: the register belongs to its volume)" % ok


# ─── N426 (O1): files --cow-before ────────────────────────────────────────────────────────────────────────────────

# RED 1.13.2 N426: files --cow-before: the before-image's bootstrap replaces the after-image's root digests (_OBJ_ROOT_REF) -- green with wave C step C1's fix (the strict xfail mark removed)
# acceptance 1.14.0 (E-6): `cow_recovery` became `cow_compare`, which compares two images of ONE volume and refuses two
# volumes; the pair is one volume whose OID 0x600 root page moved between the captures (labG_1 after labG_0: the root
# page at LCN 0x11a04 and 0x12c0c), so a replaced digest would fail A's own page
COW_NEW, COW_OLD = "step7/labG_1.raw", "step7/labG_0.raw"


def test_n426_cow_recovery_leaves_the_after_images_root_digests_in_place(monkeypatch):
    """`cmd_files` bootstraps the after-image (A) and walks it, then `cow_compare` bootstraps the before-image (B, the
    same volume) and walks it. A's own UNALTERED root page of OID 0x600 must still verify against A's digest after
    that."""
    _fresh(monkeypatch)
    b = _quiet_boot(MC.corpus(COW_OLD))                 # the premise's own read of B, before A (a bootstrap outside
    try:                                                # cow_compare's view would replace A's register in the test)
        _pg_b, digest_b = _premise_root(b, ROOT_DIR, "B")
    finally:
        b[0].close()
    _fresh(monkeypatch)
    a = _quiet_boot(MC.corpus(COW_NEW))
    try:
        pg_a, digest_a = _premise_root(a, ROOT_DIR, "A")
        _fx(digest_a != digest_b, "the premise: the two captures' OID 0x600 root pages carry different digests")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            results = F.walk_directory_tree(a[0], a[1], a[2], a[3], a[5], 0x600, F.DEFAULT_DEPTH, True)
            rows, _lines = F.cow_compare(a[0], a[1], a[2], results, True, MC.corpus(COW_OLD), None, F.DEFAULT_DEPTH,
                                         a[8])
            ok = F.verify_object_root(ROOT_DIR, pg_a)
    finally:
        a[0].close()
    altered = [t for t in F._findings("page-reference mismatch") if "0x600" in t]
    assert ok is True and not altered, "after `cow_compare` read the before-image, the after-image's own unaltered " \
        "OID 0x600 root page verifies %r and %d 'ALTERED' finding(s) name it: the before-image's bootstrap replaced the " \
        "after-image's root-page digests (N426: the register belongs to the view in use)" % (ok, len(altered))


# ─── N426 (O2): integrity's per-view verdict from run registers ─────────────────────────────────────────────────

def _integrity(path, *args, ps=None):
    out, err = io.StringIO(), io.StringIO()
    with UW.recording() as wrapped, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = F.cmd_integrity(path, list(args), ps)
        except SystemExit as e:
            rc = e.code
    return rc, UW.unwrap_exact(out.getvalue(), wrapped), err.getvalue()


def _verdicts(text):
    return [ln for ln in text.splitlines() if re.search(r"^\s*VERDICT:", ln)]


def test_n426_control_integrity_of_the_sound_volume_alone_is_clean(monkeypatch):
    """Not a RED: the premise. `integrity --checksums` on B alone (in-process): its page verdict is the clean one."""
    _fresh(monkeypatch)
    rc, out, err = _integrity(MC.corpus(IMG_B), "--checksums")
    v = _verdicts(out)
    # D3 (N470): the clean verdict's words since 1.14.0 -- "no tampering or corruption detected" with the checksum's limit
    _keep(v and "no tampering or corruption detected" in v[0] and rc == 0, "B alone: rc %r, verdicts %r" % (rc, v))


# RED 1.13.2 N426: integrity reads _CHKP_STALE, a run register, as the current volume's 'bootstrap chain is damaged' -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n426_integrity_does_not_report_an_earlier_volumes_stale_checkpoint_as_this_ones(monkeypatch, tmp_path):
    """Volume S (synthetic, its newest checkpoint copy fails its self-checksum: a stale view, `_CHKP_STALE`) is read
    first; then `integrity --checksums` on B, whose checkpoint is sound."""
    _fresh(monkeypatch)
    s = AB._synthetic_vol(tmp_path)
    AB.damage_chkp(s, s.geo.lo)
    fh = _quiet_boot(s.path, s.geo.ps)[0]
    fh.close()
    _fx(F._CHKP_STALE, "the synthetic volume's stale view was not registered")
    rc, out, err = _integrity(MC.corpus(IMG_B), "--checksums")
    v = _verdicts(out)
    assert v and not re.search(r"(?i)bootstrap chain is damaged", " ".join(v)), "B's checkpoint is sound, but its page " \
        "verdict after the synthetic volume reads %r -- the earlier volume's stale checkpoint (_CHKP_STALE, a run " \
        "register) is reported as B's (N426: a fact of the view, reset where it belongs)" % v


# RED 1.13.2 N426: integrity reads _findings('page-reference mismatch') of an earlier volume as the current volume's -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n426_integrity_does_not_report_an_earlier_volumes_altered_page_as_this_ones(monkeypatch):
    """Volume A is read first and one of its root pages fails its digest (a 'page-reference mismatch' finding); then
    `integrity --checksums` on B, whose pages all verify."""
    _fresh(monkeypatch)
    a = _quiet_boot(MC.corpus(IMG_A))
    try:
        pg, _ref = _premise_root(a, ROOT_DIR, "A")
        bad = bytearray(pg)
        bad[0x2000] ^= 0x01
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            F.verify_object_root(ROOT_DIR, bytes(bad))
    finally:
        a[0].close()
    _fx(F._findings("page-reference mismatch"), "A's altered page made no finding")
    rc, out, err = _integrity(MC.corpus(IMG_B), "--checksums")
    v = _verdicts(out)
    assert v and "no tampering or corruption detected" in v[0] and not re.search(r"(?i)ALTERED", " ".join(v)), \
        "B's pages all " \
        "verify, but its page verdict after volume A reads %r -- A's page-reference mismatch (a run register) is B's " \
        "verdict (N426)" % v


# ─── N426 (O6): refsanalysis supb ─────────────────────────────────────────────────────────────────────────────────

def _ra_supb(path, ps):
    import refsanalysis as RA
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = RA.cmd_supb(path, [], ps)
        except SystemExit as e:
            rc = e.code
    return rc, out.getvalue(), err.getvalue()


def test_n426_control_ra_supb_of_the_sound_volume_alone_shows_its_primary(monkeypatch, tmp_path):
    """Not a RED: the premise. ra `supb` on the sound synthetic volume alone: no NOTE about a backup copy."""
    _fresh(monkeypatch)
    _va, vb = WR._n425_vols(tmp_path)
    rc, out, err = _ra_supb(vb.path, vb.geo.ps)
    _keep(not re.search(r"(?i)NOTE:.*not usable", out) and "0x7CFFD000" not in out, "B alone: %s" % out[:600])


def _no_supb_verifies(v):
    """Every superblock copy of synthetic `v` fails its self-checksum (one GUID byte flipped in each): no copy verifies
    (decision 26: the volume is read from the primary, with the finding)."""
    for lcn in (v.geo.supb,) + v.geo.backups:
        v.flip(v.at(lcn, 0x50))
    _fx(all(v.verifies(x) is False for x in (v.geo.supb,) + v.geo.backups), "a superblock copy still verifies")


# RED 1.13.2 N426: ra supb reads _findings(_SUPB_NONE_VERIFIES), a run register: an earlier volume's finding is B's NOTE -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n426_ra_supb_after_a_volume_where_no_superblock_verifies_shows_its_own_primary(monkeypatch, tmp_path):
    """O2 (FIX_GB_part3d): refsanalysis `supb`'s NOTE reads `_findings(_SUPB_NONE_VERIFIES)[-1]`. Synthetic A (no
    superblock copy verifies) is bootstrapped first; then ra `supb` on the sound synthetic B in the same process. Not
    covered by the fallback node above: A's register `_SUPB_FELL_BACK` is not what this NOTE reads (critic S-3)."""
    _fresh(monkeypatch)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    va, vb = AB._synthetic_vol(tmp_path / "a"), AB._synthetic_vol(tmp_path / "b")
    _no_supb_verifies(va)
    _quiet_boot(va.path, va.geo.ps)[0].close()
    _fx(F._findings(F._SUPB_NONE_VERIFIES), "A made no 'no verified superblock copy' finding")
    rc, out, err = _ra_supb(vb.path, vb.geo.ps)
    note = [ln for ln in out.splitlines() if re.search(r"(?i)NOTE:", ln) and re.search(r"(?i)superblock", ln)]
    assert not note, "B's primary superblock verifies, but ra `supb` on B after A says %r -- A's finding (a run " \
        "register read as a fact of this view) is B's NOTE (N426 / O2)" % note[:1]


def _ra_chkp_v(path, ps):
    import refsanalysis as RA
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = RA.cmd_chkp(path, ["-v"], ps)
        except SystemExit as e:
            rc = e.code
    m = re.search(r"(?im)^\s*Superblock version\s*[:.]?\s*(\S+)", out.getvalue())
    return rc, (m.group(1) if m else None), out.getvalue()


# `_st_s1` (C2 ST-S1's RED mark for the nodes B15's decided output changed) removed in step C2, area supb


# RED 1.13.2 N426: ra chkp -v reads _SUPB_FELL_BACK['used_lcn'] of an earlier volume: B's superblock fields from A's copy -- green with wave C step C1's fix (the strict xfail mark removed)
# RED 1.13.2 B15 (C2 ST-S1 a2): A's primary fails and both backups verify with equal +0x68: A is read from end-2
# (Q3); the tool reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_n426_ra_chkp_after_a_volume_that_fell_back_shows_its_own_superblock(monkeypatch, tmp_path):
    """O6 (FIX_GB_part3d): ra `chkp` calls `parse_supb` directly and `-v` reads the superblock page at
    `_SUPB_FELL_BACK.get("used_lcn")` (ra:2191). Synthetic B: primary sound, its end-2 backup's +0x68 (the superblock
    version) altered, so that copy fails its self-checksum and B is read from its primary. B alone: `chkp -v` shows the
    primary's +0x68. After synthetic A fell back to its end-2 backup, it must still show B's primary's (critic S-4).
    C2 ST-S1 (a2): A's fallback is end-2 (Q3; it was end-3, the tool's first backup before B15), so B's plant moves to
    end-2 too -- the page a stale register would point at."""
    _fresh(monkeypatch)
    va, vb = WR._n425_vols(tmp_path)
    vb.flip(vb.at(AB.SYN.backups[1], 0x68), xor=0x40)
    _fx(vb.verifies(AB.SYN.supb) is True and vb.verifies(AB.SYN.backups[1]) is False, "B's plant")
    rc0, alone, out0 = _ra_chkp_v(vb.path, vb.geo.ps)
    _fx(alone is not None and alone == str(F.le64(vb.block(AB.SYN.supb), 0x68)),
        "B alone: chkp -v shows superblock version %r (B's primary: %d)" % (alone, F.le64(vb.block(AB.SYN.supb), 0x68)))
    _fresh(monkeypatch)
    _quiet_boot(va.path, va.geo.ps)[0].close()
    # C2 ST-S1 (a2): end-2 (was end-3); an assert, no longer a fixture check: the value B15 changes
    assert F._SUPB_FELL_BACK.get("used_lcn") == AB.SYN.backups[1], "A did not fall back to end-2: %r" \
        % dict(F._SUPB_FELL_BACK)
    rc, after, out = _ra_chkp_v(vb.path, vb.geo.ps)
    assert after == alone, "B's primary superblock verifies and B alone shows its superblock version %s; after A fell " \
        "back to its backup at LCN 0x%x, ra `chkp -v` on B shows %r -- B's fields read from A's copy in use (N426 / " \
        "O6: the register belongs to its view)" % (alone, AB.SYN.backups[1], after)


# RED 1.13.2 N426: ra supb calls parse_supb directly: an earlier volume's superblock fallback names the next volume's copy -- green with wave C step C1's fix (the strict xfail mark removed)
# RED 1.13.2 B15 (C2 ST-S1 a2): A's primary fails and both backups verify with equal +0x68: A is read from end-2
# (Q3); the tool reads end-3 (the strict xfail mark removed: fixed in step C2, area supb)
def test_n426_ra_supb_after_a_volume_that_fell_back_shows_its_own_primary(monkeypatch, tmp_path):
    """Synthetic A (primary superblock damaged: read from its backup 0xfe, end-2 -- C2 ST-S1 (a2), Q3; it was 0xfd, the
    tool's first backup before B15) is bootstrapped first; then ra `supb` on the sound synthetic B in the same
    process."""
    _fresh(monkeypatch)
    va, vb = WR._n425_vols(tmp_path)
    _quiet_boot(va.path, va.geo.ps)[0].close()
    # C2 ST-S1 (a2): end-2 (was end-3); an assert, no longer a fixture check: the value B15 changes
    assert F._SUPB_FELL_BACK.get("used_lcn") == AB.SYN.backups[1], "A did not fall back to end-2: %r" \
        % dict(F._SUPB_FELL_BACK)
    rc, out, err = _ra_supb(vb.path, vb.geo.ps)
    note = [ln for ln in out.splitlines() if re.search(r"(?i)NOTE:.*(?:not usable|backup)", ln)]
    assert not note, "B's primary superblock verifies, but ra `supb` on B after A says %r -- A's fallback register " \
        "(_SUPB_FELL_BACK, never cleared on this path) names B's copy in use (N426 / O6)" % note[:1]


# ─── N426: the table of registers ─────────────────────────────────────────────────────────────────────────────────

_OWNERS = {"volume", "view", "run"}
_NOT_REGISTERS = {"_REFS_CRC64_TBL", "_CRC32C_TABLE"}   # lookup tables filled once (at import / first use), never per volume


def _module_registers(path):
    """The module-level registers of a tool (read by this module from the source, not from the running module):
    `_NAME = [] / {} / set() / _DamageList()` at module level, empty when created, and -- critic S-2 -- every
    module-level name a function rebinds through a `global` statement (`_REFUSE_HOLES`, `_VERIFY_PAGES`, `_BUNDLE`,
    `_CSV_GUARD`, `_CSV_FORMULA_SEEN`, `_usn_nonv3_warned` on the pre-step tree): state of the module that outlives a
    volume as much as a container does."""
    t = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for node in t.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n, v = node.targets[0].id, node.value
            if not re.match(r"^_[A-Z][A-Z0-9_]*$", n) or n in _NOT_REGISTERS:
                continue
            empty = (isinstance(v, (ast.List, ast.Set)) and not v.elts) or (isinstance(v, ast.Dict) and not v.keys) \
                or (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                    and v.func.id in ("set", "dict", "list", "_DamageList") and not v.args)
            if empty:
                out.append(n)
    module_names = {tg.id for node in t.body if isinstance(node, (ast.Assign, ast.AnnAssign))
                    for tg in (node.targets if isinstance(node, ast.Assign) else [node.target])
                    if isinstance(tg, ast.Name)}
    for node in ast.walk(t):
        if isinstance(node, ast.Global):
            for n in node.names:
                if n.startswith("_") and n in module_names and n not in _NOT_REGISTERS and n not in out:
                    out.append(n)
    return out


def _owner_of(v):
    """The owner a table entry names: a string, or the first string of a tuple/list, that is (or starts with the word)
    volume / view / run."""
    ws = [v] if isinstance(v, str) else ([x for x in v if isinstance(x, str)] if isinstance(v, (tuple, list)) else [])
    for w in ws:
        m = re.match(r"(?i)\s*(volume|view|run)\b", w)
        if m:
            return m.group(1).lower()
    return None


def _register_name(k):
    """A table key as a register name: `_NAME`, or `forefst._NAME` / `refsanalysis._NAME`."""
    return k.split(".", 1)[1] if isinstance(k, str) and re.match(r"^(?:forefst|refsanalysis)\._", k) else k


def _register_tables(mod):
    """Every module-level table register -> owner: a dict {name: owner or (owner, ...)}, or a sequence of tuples
    (name, ..., owner, ...) -- the owner one of volume / view / run."""
    out = []
    for name, val in vars(mod).items():
        if isinstance(val, dict):
            pairs = list(val.items())
        elif isinstance(val, (tuple, list)) and val and all(isinstance(t, (tuple, list)) and t for t in val):
            pairs = [(t[0], next((x for x in t[1:] if _owner_of(x)), None)) for t in val]
        else:
            continue
        pairs = [(_register_name(k), v) for k, v in pairs]
        if len(pairs) >= 5 and all(isinstance(k, str) and k.startswith("_") for k, _v in pairs) \
                and all(_owner_of(v) for _k, v in pairs):
            out.append((name, dict(pairs)))
    return out


def test_n426_control_the_register_list_is_what_the_source_holds():
    """Not a RED: the instrument emits what it finds (34 registers on the pre-step tree: 28 empty containers and 6
    names rebound through `global`; the Object-Table root registers and `_CHKP_STALE` among them)."""
    regs = _module_registers(os.path.join(REPO, "forefst.py"))
    _keep({"_OBJ_ROOT_REF", "_OBJ_ROOT_VERIFIED", "_OBJ_ROOT_LCNS", "_CHKP_STALE", "_SUPB_FELL_BACK",
           "_REFUSE_HOLES", "_BUNDLE"} <= set(regs) and len(regs) >= 20
          and not {"_CRC32C_TABLE", "_REFS_CRC64_TBL"} & set(regs), "registers read from forefst.py: %r" % regs)


# RED 1.13.2 N426: no table lists every module register with its owner (volume, view or run) -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n426_every_module_register_has_an_owner_in_one_table():
    import refsanalysis as RA
    regs = _module_registers(os.path.join(REPO, "forefst.py")) + _module_registers(os.path.join(REPO, "refsanalysis.py"))
    tables = _register_tables(F) + _register_tables(RA)
    covered = set().union(*[set(t) for _n, t in tables]) if tables else set()
    missing = [r for r in regs if r not in covered]
    # critic S-1: a fix that leaves no module register at all needs no table
    assert (tables or not regs) and not missing, "N426: every module register listed in a table with its owner " \
        "(volume, view or run) " \
        "-- tables found: %r; registers without an owner (%d of %d): %s" % (
            [n for n, _t in tables], len(missing), len(regs), ", ".join(missing))


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# N434 N-6 -- the $VOLUME_INFORMATION version: one definition and its single_source.tsv row
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════

def _version_readers(path):
    """Functions (top level) that read value +0x80 and +0x81 by subscript in a body that names the row key 0x520:
    the $VOLUME_INFORMATION version stamps (structure_reference F.4b)."""
    t = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for fn in t.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        consts = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, int)}
        subs = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Subscript):
                s = n.slice
                if isinstance(s, ast.Constant) and isinstance(s.value, int):
                    subs.add(s.value)
        if 0x520 in consts and {0x80, 0x81} <= subs:
            out.append(fn.name)
    return out


def test_n434_n6_control_the_reader_finder_finds_the_known_reader(tmp_path):
    """Not a RED: the instruments find `read_volume_information` (the function N265 made) and the three readers."""
    # critic S-5: read from the PRE-STEP snapshot (fixes/prefix_C1, read as text, not run) and from forms a fix may
    # take, so the control does not pin the place of the definition the fix chooses
    pre = os.path.join(os.path.dirname(REPO), "analysis", "reports", "v1.13.2", "fixes", "prefix_C1")
    _fx(os.path.isfile(os.path.join(pre, "forefst.py")), "the pre-step snapshot is not at %s" % pre)
    _keep("read_volume_information" in _version_readers(os.path.join(pre, "forefst.py")),
          "the finder misses read_volume_information")
    _keep(_stamp_readers(os.path.join(pre, "forefst.py")) == ["cmd_fastsummary", "read_volume_information"]
          and _stamp_readers(os.path.join(pre, "refsanalysis.py")) == ["cmd_summary"],
          "the offsets finder on the pre-step tree: %r / %r" % (_stamp_readers(os.path.join(pre, "forefst.py")),
                                                              _stamp_readers(os.path.join(pre, "refsanalysis.py"))))
    src = os.path.join(str(tmp_path), "forms.py")
    with open(src, "w") as fh:
        fh.write("def a(vd):\n    return vd[0x80], vd[0x81]\n"
                 "def b(vd):\n    return le16(vd, 0x80)\n"
                 "def c(vd):\n    return struct.unpack_from('<BB', vd, 0x80)\n"
                 "def d(vd):\n    return vd[0x80]\n")
    _keep(_stamp_readers(src) == ["a", "b", "c"], "the offsets finder on the decoder forms: %r" % _stamp_readers(src))


def _stamp_readers(path):
    """Top-level functions that read BOTH +0x80 and +0x81 of a buffer -- by subscript, as constant call arguments, or
    through a call that reads exactly the two bytes at 0x80 (`le16(vd, 0x80)`, `struct.unpack_from` with a two-byte
    format such as "<BB") -- whether or not the function names the row key 0x520 (critic S-5: a decoder that
    takes the row's value is the definition too). On the pre-step tree exactly the three readers of N-6 (forefst
    `cmd_fastsummary`, `read_volume_information`; refsanalysis `cmd_summary`)."""
    import struct as _st
    t = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for fn in t.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        offs = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, int):
                offs.add(n.slice.value)
            elif isinstance(n, ast.Call):
                ints = {a.value for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, int)}
                offs |= ints
                if 0x80 in ints:
                    name = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
                    fmts = [a.value for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                    wide = name == "le16"
                    for fm in fmts:
                        try:
                            wide = wide or _st.calcsize(fm) == 2
                        except _st.error:
                            pass
                    if wide:
                        offs.add(0x81)
        if {0x80, 0x81} <= offs:
            out.append(fn.name)
    return out


# RED 1.13.2 N434: N-6: the $VOLUME_INFORMATION version is read by three functions and has no single_source.tsv row -- green with wave C step C1's fix (the strict xfail mark removed)
def test_n434_n6_the_volume_information_version_has_one_definition_and_a_single_source_row():
    """One definition, in forefst.py, named by a single_source.tsv row in every copy; refsanalysis reads no copy of
    its own. Critic S-5: the definition may be `read_volume_information` itself or a decoder of the row's value it
    calls (one that does not name the key 0x520), so the readers are found by the two offsets alone."""
    fd = _stamp_readers(os.path.join(REPO, "forefst.py"))
    ra = _stamp_readers(os.path.join(REPO, "refsanalysis.py"))
    bad = []
    for p, rows in OT._single_source_copies():
        if len(fd) != 1 or not [r for r in rows if len(r) >= 3 and r[1] == fd[0] and r[2].endswith("forefst.py")]:
            bad.append(p)
    assert len(fd) == 1 and not ra and not bad, "the $VOLUME_INFORMATION version (+0x80/+0x81 of row 0x520) is read " \
        "by forefst %s and refsanalysis %s; one definition in forefst.py, imported by refsanalysis, named by a " \
        "single_source.tsv row (copies without it: %s) (N434 N-6)" % (fd, ra, bad or "none")
