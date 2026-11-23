"""N596 (1.14.0): a count of one takes the singular noun.

1.13.1 and the 1.14.0 development tree before N596 printed `Hard-linked: 1 files sharing 2 names`, `Names: 270 (269
files, plus 1 more names: 1 hard-linked files have 2 names)` and `Integrity State  1 rows` on the public sample
`win11refs2tsnapshots`; these cases fail on that text (the before-copy, RC1D/rc1check/before/forefst.py.*.n596).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import test_1132_red_mlog_chkp as MC                     # noqa: E402
import forefst as F                                      # noqa: E402

IMG = "step3/win11refs2tsnapshots.raw"


def test_n596_count_noun_takes_the_number_of_its_count():
    assert F.count_noun(1, "file") == "1 file" and F.count_noun(2, "file") == "2 files"
    assert F.count_noun(0, "entry", "entries") == "0 entries" and F.count_noun(1, "entry", "entries") == "1 entry"
    assert F.bytes_text(1) == "1 byte" and F.bytes_text(2) == "2 bytes"


def test_n596_summary_counts_of_one_are_singular_on_image_win11refs2tsnapshots():
    rc, text = MC.run_tool(MC.FOREFST, MC.corpus(IMG), "summary")
    assert "Hard-linked:        1 file sharing 2 names" in text, MC._ctx(rc, text[-1500:])
    assert "plus 1 more name: 1 hard-linked file has 2 names" in text, MC._ctx(rc, text[-1500:])
    assert re.search(r"(?m)^  Integrity State\s+1 row$", text), MC._ctx(rc, text[-1500:])
    assert not re.search(r"\b1 (files|names|rows|entries|objects)\b", text), \
        "no count of one with a plural noun in summary" + MC._ctx(rc, text[-1500:])
