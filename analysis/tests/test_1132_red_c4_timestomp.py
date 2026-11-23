"""1.13.2 (ships 1.14.0) step C4, area timestomp: N114, N160 and decision 22's O6 (B4's nodes: test_1132_red_b_items).

Plan: `analysis/reports/v1.13.2/fixes/WAVEC_BRIEF.md` (C4 rows), settlement Q46; direct mode (PLAN decision 46).

N114 ROUND_TIMESTAMPS alone is INFO and never raises a tier: the legend said "LOW only".
N160 `--min` with a value that is not a tier exits 1 (it behaved as `--min INFO`); the screen column printing the change
     time is "Changed", not "Last real write".
O6   LOW is not shown by default and is shown with `--min LOW`; CSV/JSON keep every tier unless `--min` is given.
"""
import csv
import io
import re
import sys

from _repo import REPO                                   # layout-independent; see _repo.py
sys.path.insert(0, REPO)
import forefst as F                                      # noqa: E402

from test_1132_red_b_items import _run, _image_or_skip, _ctx, FOREFST   # noqa: E402

SAMPLE = "step5/win11refstestmftecmd.raw"                # the public sample: HIGH 137 / INFO 57 (measured)


def _rows(out):
    """The screen listing's rows: (tier, basis, claimed birth, changed, path). Acceptance 1.14.0 (K5): a time is one
    token, `2026-05-16T16:55:20.9805996Z`."""
    _t = r"(\d{4}-\d\d-\d\dT[\d:.]+Z)"
    return [m.groups() for m in re.finditer(r"(?m)^  (HIGH|MEDIUM|LOW|INFO) +(\S+) +%s +%s +(.+)$" % (_t, _t), out)]


# ═══ N114 -- ROUND_TIMESTAMPS ═════════════════════════════════════════════════════════════════════════════════

def test_n114_round_timestamps_alone_is_info():
    assert F.timestomp_verdict(["ROUND_TIMESTAMPS"])[0] == "INFO"
    assert F.timestomp_verdict(["CHANGE_LATE"], round_ts=True)[0] == "MEDIUM"      # it never raises a tier
    assert F.timestomp_verdict(["PRE_FORMAT", "CHANGE_LATE"], round_ts=True)[0] == "INFO"


def test_n114_the_legend_says_so():
    rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "timestomp", "--min", "INFO")
    leg = out[out.index("Signal legend"):]
    assert "LOW only" not in leg and re.search(r"alone it is INFO and it never raises a\s+tier", leg), leg


# ═══ N160 -- --min and the Changed column ═════════════════════════════════════════════════════════════════════

def test_n160_a_min_typo_exits_1_and_lists_nothing():
    for bad in ("HIHG", "none", "2"):
        rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "timestomp", "--min", bad)
        assert rc == 1 and "invalid value for --min: '%s'" % bad in err and not _rows(out), (bad, _ctx(rc, out, err))


def test_n160_control_a_tier_in_any_case_is_accepted():
    rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "timestomp", "--min", "medium")
    assert rc == 0 and _rows(out), _ctx(rc, out, err)


def test_n160_the_changed_column_is_the_change_time():
    img = _image_or_skip(SAMPLE)
    rc, out, err = _run(FOREFST, img, "timestomp")
    assert re.search(r"(?m)^  Conf +Basis +Claimed birth +Changed +Path$", out) and "Last real write" not in out
    rc2, c, _e = _run(FOREFST, img, "timestomp", "--csv", "-")
    changed = {r["FullPath"]: r["Changed"] for r in csv.DictReader(io.StringIO(c))}      # K21 / N313 (1.14.0)
    rows = _rows(out)
    assert rows and all(changed[p] == ch for _t, _b, _c, ch, p in rows), rows[:3]


# ═══ O6 -- LOW hidden by default, every tier in CSV ════════════════════════════════════════════════════════════

def test_o6_the_screen_shows_high_by_default_and_csv_every_tier():
    img = _image_or_skip(SAMPLE)
    rc, out, err = _run(FOREFST, img, "timestomp")
    tiers = {t for t, *_x in _rows(out)}
    assert tiers == {"HIGH"} and len(_rows(out)) == 137, (tiers, len(_rows(out)))
    rc2, c, _e = _run(FOREFST, img, "timestomp", "--csv", "-")
    got = [r["Confidence"] for r in csv.DictReader(io.StringIO(c))]
    assert len(got) == 194 and set(got) == {"HIGH", "INFO"}, (len(got), set(got))
    assert not [r for r in csv.DictReader(io.StringIO(c)) if "FUTURE" in r["Signals"]]


def test_o6_min_low_shows_the_low_tier_and_not_info():
    rc, out, err = _run(FOREFST, _image_or_skip(SAMPLE), "timestomp", "--min", "LOW")
    assert rc == 0 and {t for t, *_x in _rows(out)} <= {"HIGH", "MEDIUM", "LOW"} and len(_rows(out)) == 137
    assert "LOW    — anything else (no current signal reaches it)." in out


def test_o6_planted_low_is_hidden_by_default_and_shown_with_min_low(monkeypatch, capsys):
    """RC-13 (wave C's close): no real input reaches LOW (the 128-input enumeration), so the node above cannot fail if
    `--min LOW` hid LOW. Here every row's tier is planted LOW: the default screen lists none, `--min LOW` lists them,
    the CSV keeps them (O6)."""
    img = _image_or_skip(SAMPLE)
    _real = F.timestomp_verdict
    monkeypatch.setattr(F, "timestomp_verdict",
                        lambda flags, *a, **k: ("LOW", _real(flags, *a, **k)[1]) if flags else _real(flags, *a, **k))

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["forefst.py", img, "timestomp"] + list(args))
        try:
            rc = F.main()
        except SystemExit as e:
            rc = e.code
        return rc, capsys.readouterr().out

    rc, out = run()
    assert not _rows(out), _rows(out)[:3]
    rc2, out2 = run("--min", "LOW")
    rows = _rows(out2)
    assert rows and {t for t, *_x in rows} == {"LOW"}, rows[:3]
    rc3, c = run("--csv", "-")
    got = {r["Confidence"] for r in csv.DictReader(io.StringIO(c))}
    assert "LOW" in got, got

