"""N593 (found 2026-11-17 accounting the F2 golden rows): `extract` of an empty split reparse point names its tag and
target, as it does for an embedded one.

F2 (N577) gave the split entry its backing record on one of its two branches. The other branch -- a split record whose
data is inline in the backing (E82), which every empty split file takes -- still carried no record, so `extract`'s
empty-file text had nothing to read: on `win11refs2tspecials` the 265 split reparse points (hard-linked symlinks,
`reparse` names each one's tag and target) printed "a REPARSE POINT, a reparse point; the link's own data stream is
empty", while the 243 embedded ones name the tag and the target. The target of a split record is read from its backing
as the walk reads it (`_t40_record_tuple`).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

IMG = "step3/win11refs2tspecials.raw"
DIR_OID = "0x702"                                        # testspecials
SPLIT = "hardlink_alpha_915629.lnk"                      # `reparse`: [split record]
SPLIT_TARGET = r"j:\testspecials\dir_november_947335\hardlink_beta_859345.lnk"
EMBEDDED = "symlink_gamma_119189.lnk"
EMBEDDED_TARGET = r"j:\testspecials\dir_lima_342873\dir_archive_409111\dir_romeo_975581\symlink_kilo_639983.lnk"
TAG = "0xa000000c (IO_REPARSE_TAG_SYMLINK)"


def _extract(name, out_dir):
    return MC.run_tool(MC.FOREFST, MC.corpus(IMG), "extract", name, "--oid", DIR_OID,
                       "-o", str(out_dir / "extracted.bin"))


def test_n593_an_empty_split_symlink_names_its_tag_and_target_on_image_win11refs2tspecials(tmp_path):
    rc, text = _extract(SPLIT, tmp_path)
    line = [ln for ln in text.splitlines() if ln.startswith("Extracting '%s'" % SPLIT)]
    assert rc == 0 and line and TAG in line[0] and ("it points to %s" % SPLIT_TARGET) in line[0], \
        "the hard-linked symlink's record is split; its backing holds the tag and target `reparse` prints: extract " \
        "must name both, as for an embedded symlink (exit %s, line %r)" % (rc, line) + MC._ctx(rc, text[-1500:])


def test_n593_control_an_embedded_symlink_keeps_its_text_on_image_win11refs2tspecials(tmp_path):
    rc, text = _extract(EMBEDDED, tmp_path)
    line = [ln for ln in text.splitlines() if ln.startswith("Extracting '%s'" % EMBEDDED)]
    assert rc == 0 and line and TAG in line[0] and ("it points to %s" % EMBEDDED_TARGET) in line[0], \
        "the embedded symlink: extract names its tag and target (exit %s, line %r)" % (rc, line) \
        + MC._ctx(rc, text[-1500:])
