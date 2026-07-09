#!/usr/bin/env python3
"""verify_tool_tables.py — reference-table consistency gate for the ReFS tools.

The other gates verify values PARSED FROM DISK. This one verifies the tools' HARDCODED reference
tables (opcode/schema/OID/flag NAME maps) against the authoritative master — the blind spot that
let `0x17 → STATUS_LOG_CORRUPTION` and `$CBW4` survive in the tool source unnoticed.

Two layers, both read-only (it only imports the tools' map objects and asserts):
  CURATED   — each high-value / project-corrected entry must equal the master value (with a citation).
  STRUCTURAL— self-consistency that needs no external truth (contiguous opcode range, no orphan
              category label, cross-tool map agreement, same imported object).

  python3 verify_tool_tables.py            # gate: exit 0 iff all pass
  python3 verify_tool_tables.py --calibrate # prove the instrument fires (mutate copies → expect FAILs)
"""
import os, sys, copy, importlib.util

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOOLDIR = _REPO   # gate the published tools at the repo root

def _load():
    sys.path.insert(0, TOOLDIR)
    def imp(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec); sys.modules[name] = m
        spec.loader.exec_module(m); return m
    fe = imp("forefst", os.path.join(TOOLDIR, "forefst.py"))
    ra = imp("refsanalysis", os.path.join(TOOLDIR, "refsanalysis.py"))
    return fe, ra

def run_checks(fe, ra):
    """Return list of (layer, id, ok, detail). Maps are read off fe/ra so callers can pass mutated shims."""
    out = []
    def chk(layer, cid, ok, detail=""):
        out.append((layer, cid, bool(ok), detail))
    R314, R34, CAT = fe.REDO_OPS_V314, fe.REDO_OPS_V34, fe.OPCODE_CATEGORIES
    ATTR, OIDS, RT = fe._ATTR_NAMES, fe.KNOWN_SYSTEM_OIDS, fe.REPARSE_TAGS
    IFLAGS, CHALG, CHKPF = ra._INTERNAL_FLAGS, ra._CHECKSUM_ALGO_MAP, ra._CHKP_FLAG_BITS
    RART = getattr(ra, "_REPARSE_TAGS", getattr(ra, "REPARSE_TAGS", {}))

    # ── CURATED authoritative facts (each cited) ───────────────────────────
    chk("CUR", "redo_0x17=0xC0000427", R314.get(0x17) == "ERROR:0xC0000427",
        "decomp PerformRedo:239 (-0x3ffffbd9=0xC0000427); master §E.3 audit3 | got %r" % R314.get(0x17))
    chk("CUR", "no_STATUS_LOG_CORRUPTION", not any("STATUS_LOG_CORRUPTION" in str(v) for v in list(R314.values())+list(R34.values())),
        "the corrected label must be gone (audit3)")
    chk("CUR", "redo34_0x17=RedoGenerateChecksum", R34.get(0x17) == "RedoGenerateChecksum",
        "v3.4 0x17 is a valid handler (master §E.3) | got %r" % R34.get(0x17))
    chk("CUR", "redo_0x28=BreakWeakReferences", "BreakWeakReferences" in str(R314.get(0x28)),
        "#328: 0x28 = CmsBlockRefcount::BreakWeakReferences (not DuplicateCluster) | got %r" % R314.get(0x28))
    chk("CUR", "attr_0x100=$EFS", ATTR.get(0x100) == "$EFS",
        "E35 / CBW4.md: type 0x100 = $EFS | got %r" % ATTR.get(0x100))
    chk("CUR", "no_$CBW4", not any("$CBW4" in str(v) for v in ATTR.values()),
        "E35: $CBW4 is a fabrication (0 on disk, 0 in binary)")
    chk("CUR", "attr_0xF0=LOGGED_UTILITY", ATTR.get(0xF0) == "$LOGGED_UTILITY_STREAM",
        "master §F.2 (schema name; content = USN $Max) | got %r" % ATTR.get(0xF0))
    chk("CUR", "oid_0x520=FS_Metadata", OIDS.get(0x520) == "FS Metadata",
        "E19: OID 0x520 = FS Metadata dir, NOT a security mapping | got %r" % OIDS.get(0x520))
    chk("CUR", "oid_0x530=Security", "Security" in str(OIDS.get(0x530)),
        "OID 0x530 = security-descriptor table | got %r" % OIDS.get(0x530))
    chk("CUR", "iflag_0x01=DeleteDisposition",
        IFLAGS.get(1) == "DeleteDisposition" and fe._INTERNAL_FLAG_LABELS.get(1) == "DeleteDisposition",
        "E43: $SI+0x24 bit0 = delete-disposition (FCB bit27), NOT integrity; refsanalysis label must match the "
        "forefst canonical 'DeleteDisposition' (C2) | got ra=%r fe=%r"
        % (IFLAGS.get(1), fe._INTERNAL_FLAG_LABELS.get(1)))
    chk("CUR", "iflag_no_INTEGRITY", not any("INTEGRITY" in str(v) for v in IFLAGS.values()),
        "E43: integrity is FILE_ATTRIBUTE 0x8000 (at $SI+0x20), never in internal_flags")
    chk("CUR", "checksum_algo_map", CHALG == {0: "None", 2: "CRC64", 4: "SHA256"},
        "master §A: VBR 0x2A 0=None 2=CRC64 4=SHA256 | got %r" % CHALG)
    chk("CUR", "wsl_0x80000024=LX_FIFO", "LX_FIFO" in str(RT.get(0x80000024)),
        "E41: 0x80000024 = LX_FIFO (off-by-one corrected; not AF_UNIX) | got %r" % RT.get(0x80000024))
    chk("CUR", "wsl_0x80000023=AF_UNIX", "AF_UNIX" in str(RT.get(0x80000023)),
        "E41: 0x80000023 = AF_UNIX | got %r" % RT.get(0x80000023))
    chk("CUR", "chkp_0x80=native", any(s in str(CHKPF.get(0x80)).lower() for s in ("native", "win11")),
        "CHKP flag 0x80 = native-Win11-format (vs upgraded) | got %r" % CHKPF.get(0x80))
    chk("CUR", "chkp_0x2000=insider", "insider" in str(CHKPF.get(0x2000)).lower(),
        "CHKP flag 0x2000 = Insider build | got %r" % CHKPF.get(0x2000))

    # ── STRUCTURAL self-consistency ────────────────────────────────────────
    chk("STR", "redo314_contiguous_00-2B", set(R314.keys()) == set(range(0x00, 0x2C)),
        "v3.14 dispatched range is contiguous 0x00-0x2B (finding #328)")
    chk("STR", "redo34_contiguous_00-1C", set(R34.keys()) == set(range(0x00, 0x1D)),
        "v3.4 dispatched range is contiguous 0x00-0x1C")
    orphans = [v for v in list(R314.values()) + list(R34.values()) if v not in CAT]
    chk("STR", "no_orphan_category_label", not orphans,
        "every REDO_OPS label must have an OPCODE_CATEGORIES entry (catches a value/key break like the old 0x17) | orphans=%r" % orphans[:5])
    # cross-tool reparse-tag agreement on shared keys (forefst short name ⊂ refsanalysis full name)
    shared = set(RT) & set(RART)
    mism = [(hex(k), RT[k], RART[k]) for k in shared if str(RT[k]).lstrip("$").upper() not in str(RART[k]).upper()]
    chk("STR", "reparse_xtool_agree", not mism,
        "forefst.REPARSE_TAGS must agree with refsanalysis._REPARSE_TAGS on %d shared keys | mism=%r" % (len(shared), mism[:4]))

    # ── CROSS-TOOL import identity (no divergent copy) ─────────────────────
    # Post-CLI-migration (v3.5.0): the redo tables are forefst-only — refsanalysis's mlog command moved to
    # forefst, so refsanalysis no longer carries REDO_OPS_V314/V34. The invariant is "no DIVERGENT copy":
    # if refsanalysis still exposes the symbol it must BE forefst's object; if it dropped it, the getattr
    # default (forefst's own object) makes the identity trivially hold. Either way a divergent copy fails.
    chk("XT", "redo314_no_divergent_copy", getattr(ra, "REDO_OPS_V314", fe.REDO_OPS_V314) is fe.REDO_OPS_V314,
        "refsanalysis must not carry a divergent REDO_OPS_V314 (import from forefst or drop it)")
    chk("XT", "redo34_no_divergent_copy", getattr(ra, "REDO_OPS_V34", fe.REDO_OPS_V34) is fe.REDO_OPS_V34,
        "refsanalysis must not carry a divergent REDO_OPS_V34")
    return out

class _Shim:
    """Lightweight stand-in exposing mutated map copies for calibration."""
    def __init__(self, src, overrides):
        self._src = src
        for k, v in overrides.items(): setattr(self, k, v)
    def __getattr__(self, n): return getattr(self._src, n)

def calibrate(fe, ra):
    """Prove the gate is sensitive: inject known-wrong values into COPIES and confirm the matching check fails."""
    print("CALIBRATION — inject wrong values, expect the matching check to FAIL:")
    cases = [
        ("redo_0x17 -> STATUS_LOG_CORRUPTION", {"REDO_OPS_V314": {**fe.REDO_OPS_V314, 0x17: "ERROR:STATUS_LOG_CORRUPTION"}}, None,
         "redo_0x17=0xC0000427"),
        ("attr_0x100 -> $CBW4/$EFS", {"_ATTR_NAMES": {**fe._ATTR_NAMES, 0x100: "$CBW4/$EFS"}}, None, "attr_0x100=$EFS"),
        ("oid_0x520 -> Security ID mapping", {"KNOWN_SYSTEM_OIDS": {**fe.KNOWN_SYSTEM_OIDS, 0x520: "Security ID mapping"}}, None,
         "oid_0x520=FS_Metadata"),
        ("iflag_0x01 -> INTEGRITY", None, {"_INTERNAL_FLAGS": {**ra._INTERNAL_FLAGS, 1: "INTEGRITY"}}, "iflag_0x01=DeleteDisposition"),
        ("orphan label (drop 0x17 from categories)", {"REDO_OPS_V314": {**fe.REDO_OPS_V314, 0x17: "ERROR:NEW_UNMAPPED"}}, None,
         "no_orphan_category_label"),
    ]
    ok_all = True
    for name, fov, rov, expect_id in cases:
        feS = _Shim(fe, fov) if fov else fe
        raS = _Shim(ra, rov) if rov else ra
        res = run_checks(feS, raS)
        failed = {cid for (_, cid, ok, _) in res if not ok}
        fired = expect_id in failed
        ok_all &= fired
        print("  %-42s -> %s (%s)" % (name, "FIRED ✓" if fired else "MISSED ✗", expect_id))
    print("calibration:", "PASS — instrument is sensitive ✓" if ok_all else "FAIL — a planted error went undetected ✗")
    return ok_all

def main():
    fe, ra = _load()
    if "--calibrate" in sys.argv:
        sys.exit(0 if calibrate(fe, ra) else 1)
    res = run_checks(fe, ra)
    fails = [r for r in res if not r[2]]
    for layer, cid, ok, detail in res:
        if not ok: print("  FAIL [%s] %-34s %s" % (layer, cid, detail))
    npass = sum(1 for r in res if r[2])
    print("TOTAL: %d PASS / %d FAIL  (tools: %s)" % (npass, len(fails), TOOLDIR))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
