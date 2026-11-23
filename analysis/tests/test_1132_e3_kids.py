"""E3 (1.14.0): pytest cases for three findings of the 2026-09 blind audit that had none.

The audit read v1.12.3, where the four defect cases fail and the two controls pass; v1.13.0 and later pass all six
(run 2026-11-18 with FOREFST_REPO set to analysis/verification/versions/v1.12.3 and v1.13).

K031  `integrity --checksums` under a page cap (`--max-pages`) checks part of the volume; v1.12.3 printed a clean
      verdict and exited 0. The verdict must say the coverage is incomplete, name the cap, and exit 2.
K062  `integrity` on an undamaged 4Kn volume (4,096-byte sectors) reported the backup boot sector missing and fewer
      than two superblock copies, from offsets computed with 512-byte sectors. It must find both and pass, exit 0.
K081  `timestomp --margin-days` took any integer, a negative one included (4,620 of 4,668 files then HIGH), and let a
      fraction escape as a Python error. Both must be refused with a message, exit 1.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

SMALL = "step1/win10refsmini.raw"                        # a small, undamaged ReFS 3.4 volume
K4N = "step6/lab314_4kn.raw"                             # undamaged, 4,096 bytes per sector


def test_k031_a_page_cap_makes_the_checksum_verdict_incomplete_on_image_win10refsmini():
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(SMALL), "integrity", "--checksums", "--max-pages", "2")
    verdict = [ln for ln in text.splitlines() if ln.lstrip().startswith("Verdict:")]
    assert rc == 2 and verdict and "INCOMPLETE" in verdict[0] and "page cap reached" in " ".join(text.split()), \
        "a capped checksum walk checked part of the volume: the verdict says INCOMPLETE and names the cap, exit 2 " \
        "(exit %s, verdict %r)" % (rc, verdict) + MC._ctx(rc, text[-1500:])
    assert "no tampering" not in text.lower() and "certified clean" not in text.lower().replace("not certified clean", ""), \
        "a capped walk must not certify the volume" + MC._ctx(rc, text[-1500:])


def test_k031_control_the_uncapped_walk_passes_on_image_win10refsmini():
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(SMALL), "integrity", "--checksums")
    verdict = [ln for ln in text.splitlines() if ln.lstrip().startswith("Verdict:")]
    assert rc == 0 and verdict and verdict[0].split("Verdict:")[1].strip().startswith("PASS"), \
        "the same volume, uncapped: PASS, exit 0 (exit %s, verdict %r)" % (rc, verdict) + MC._ctx(rc, text[-1500:])


def test_k062_an_undamaged_4kn_volume_passes_integrity_on_image_lab314_4kn():
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(K4N), "integrity")
    flat = " ".join(text.split()).lower()
    verdict = [ln for ln in text.splitlines() if ln.lstrip().startswith("Verdict:")]
    assert "backup boot sector" not in flat or "missing" not in flat.split("backup boot sector", 1)[1][:80], \
        "the 4Kn volume's backup boot sector is at the volume's last 4,096-byte sector: found" + MC._ctx(rc, text[-1500:])
    assert "fewer than 2" not in flat, "both superblock backups are found on 4Kn" + MC._ctx(rc, text[-1500:])
    assert rc == 0 and verdict and verdict[0].split("Verdict:")[1].strip().startswith("PASS"), \
        "an undamaged 4Kn volume passes, exit 0 (exit %s, verdict %r)" % (rc, verdict) + MC._ctx(rc, text[-1500:])


def _timestomp(margin):
    return MC.run_tool(MC.FOREFST, MC.corpus(SMALL), "timestomp", "--margin-days", margin)


def test_k081_a_negative_margin_is_refused():
    rc, text = _timestomp("-1")
    assert rc == 1 and "--margin-days" in text and "Traceback" not in text, \
        "a negative tolerance is a usage error, exit 1, with a message" + MC._ctx(rc, text[-1500:])


def test_k081_a_fractional_margin_is_refused_with_a_message():
    rc, text = _timestomp("0.5")
    assert rc == 1 and "--margin-days" in text and "Traceback" not in text and "invalid literal" not in text, \
        "a fraction is refused with the option named, not a Python error" + MC._ctx(rc, text[-1500:])


def test_k081_control_a_whole_margin_is_accepted():
    rc, text = _timestomp("2")
    assert rc in (0, 2) and "Traceback" not in text and "invalid value" not in text, \
        "a whole non-negative margin runs (exit %s)" % rc + MC._ctx(rc, text[-1500:])
