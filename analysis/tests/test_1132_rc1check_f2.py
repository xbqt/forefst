"""N577 (the auditor's RC1 check, F2): `extract` verifies the integrity stream of a file whose record is split.

A hard-linked or moved file's record is split out of its name row into a type-0x40 backing in its home directory;
the backing holds the $DATA row and its CRC-32C. `integrity --checksums` verified the backing (1.13.1's fix of the same
defect there); `extract` handed the verifier the entry built from the NAME row, which carries no record, so it printed
"no CRC-32C row this tool reads was found ... NOT verified" and exited 2 on a clean file -- and on a file with a
flipped bit printed the same warning and wrote the altered bytes. The split entry now carries its backing record.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_1132_red_mlog_chkp as MC                     # noqa: E402

SAMPLE = "step5/win11refstestmftecmd.raw"
TARGET = ("testintegrity/dir_gamma_404999/dir_whiskey_550421/dir_sierra_463915/dir_yankee_672946/dir_uniform_914766/"
          "xbpt_hardlink_mike_495558.bak")
FLIP = 0x4AEB5010                                        # a byte of the file's first data cluster (the auditor's)
NOT_READ = "no CRC-32C row this tool reads was found"


def _extract(p, out_dir):
    """`extract -o` into pytest's own directory: the scratch copy's directory holds the image only (its cleanup
    refuses a directory with anything else in it, and `extract` can write a sidecar beside its output)."""
    return MC.run_tool(MC.FOREFST, p, "extract", TARGET, "-o", str(out_dir / "extracted.bin"))


def test_n577_a_split_record_integrity_file_is_verified_on_image_win11refstestmftecmd(tmp_path):
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        rc, text = _extract(p, tmp_path)
    assert rc == 0 and NOT_READ not in text and "CRC32-C-verified" in text, \
        "the hard-linked file carries an integrity stream whose CRC rows are in its backing: extract must verify " \
        "them and exit 0 on the undamaged sample (exit %s)" % rc + MC._ctx(rc, text[-1500:])


def test_n577_a_flipped_bit_in_a_split_record_integrity_file_is_named_and_exits_2_on_image_win11refstestmftecmd(tmp_path):
    with MC.scratch_copy(SAMPLE, 450 << 20) as (src, p):
        with open(p, "r+b") as fh:
            fh.seek(FLIP)
            b = fh.read(1)
            fh.seek(FLIP)
            fh.write(bytes([b[0] ^ 0x01]))
        rc, text = _extract(p, tmp_path)
    assert rc == 2 and NOT_READ not in text and "INTEGRITY MISMATCH" in text, \
        "one bit flipped in the first data cluster: extract must name the checksum mismatch and exit 2, not say the " \
        "checksums were not read (exit %s)" % rc + MC._ctx(rc, text[-1500:])
