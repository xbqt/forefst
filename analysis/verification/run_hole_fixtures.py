#!/usr/bin/env python3
"""Run every row of `hole_fixtures.tsv` in BOTH modes and check rc, bytes and sidecar.

The 1.11.2 defect existed because the fixture that finds it had only ever been run in default mode: the
note was checked, the sidecar and `--refuse-holes` were not. This runs both modes for every producer and
compares against the recipe's expectations, so "verified for the note only" cannot happen again.

Each row is a recipe: sparse-carve the source image (allocated ranges only -- these images are up to 2 TB
apparent for ~2 GB of data), punch one cluster, run `extract`, delete the carve.

    python3 analysis/verification/run_hole_fixtures.py [--tool forefstdev/forefst.py]
"""
import glob
import hashlib
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TSV = os.path.join(ROOT, "analysis/verification/hole_fixtures.tsv")
TOOL = os.path.join(ROOT, "forefstdev/forefst.py")


def allocated_sha256(path):
    """Hash the ALLOCATED ranges plus the file length.

    A whole-image hash would read 2 TB of holes to fingerprint 2 GB of data. Hashing the allocated extents
    (offset, length, bytes) plus the total size identifies the volume just as tightly and runs in seconds.
    """
    h = hashlib.sha256()
    size = os.path.getsize(path)
    h.update(b"size=%d\n" % size)
    fd = os.open(path, os.O_RDONLY)
    try:
        pos = 0
        while pos < size:
            try:
                ds = os.lseek(fd, pos, os.SEEK_DATA)
            except OSError:
                break
            try:
                de = os.lseek(fd, ds, os.SEEK_HOLE)
            except OSError:
                de = size
            h.update(b"ext=%d:%d\n" % (ds, de - ds))
            os.lseek(fd, ds, os.SEEK_SET)
            rem = min(de, size) - ds
            while rem > 0:
                chunk = os.read(fd, min(1 << 22, rem))
                if not chunk:
                    break
                h.update(chunk)
                rem -= len(chunk)
            pos = de
    finally:
        os.close(fd)
    return h.hexdigest()


def carve(src, dst):
    size = os.path.getsize(src)
    fd = os.open(src, os.O_RDONLY)
    try:
        with open(dst, "wb") as out:
            out.truncate(size)
            pos = 0
            while pos < size:
                try:
                    ds = os.lseek(fd, pos, os.SEEK_DATA)
                except OSError:
                    break
                try:
                    de = os.lseek(fd, ds, os.SEEK_HOLE)
                except OSError:
                    de = size
                os.lseek(fd, ds, os.SEEK_SET)
                out.seek(ds)
                rem = min(de, size) - ds
                while rem > 0:
                    chunk = os.read(fd, min(1 << 22, rem))
                    if not chunk:
                        break
                    out.write(chunk)
                    rem -= len(chunk)
                pos = de
    finally:
        os.close(fd)


def _locate(image):
    """Find the fixture volume by BASENAME, so the recipe is not tied to one machine's layout.

    The path in the TSV records where it sat when the fixture was written; what identifies the volume is
    its name plus the content hash checked below. Searched: an explicit --images directory, the recorded
    path, then anywhere under the repository.
    """
    base = os.path.basename(image)
    if "--images" in sys.argv:
        hits = glob.glob(os.path.join(sys.argv[sys.argv.index("--images") + 1], "**", base), recursive=True)
        if hits:
            return hits[0]
    exact = os.path.join(ROOT, image)
    if os.path.exists(exact):
        return exact
    hits = glob.glob(os.path.join(ROOT, "analysis", "**", base), recursive=True)
    return hits[0] if hits else None


def _locate_tool():
    """forefst.py sits at the repo root in a PUBLISHED tree and under forefstdev/ in the dev tree."""
    for cand in ("forefstdev/forefst.py", "forefst.py"):
        p = os.path.join(ROOT, cand)
        if os.path.exists(p):
            return p
    return None


def main():
    skipped = []
    tool = _locate_tool()
    if "--tool" in sys.argv:
        tool = os.path.join(ROOT, sys.argv[sys.argv.index("--tool") + 1])
    # A MISSING tool is not a fixture result. Python exits 2 with no output when it cannot open the
    # script, which produces `2:none:nosidecar` -- byte-for-byte the signature of a correct --refuse-holes
    # run. Two of the three fixtures then "passed" against a tool that was not there, and only the
    # negative control failed. Caught by rehearsing the sync into a published-layout tree; asserted here
    # so it can never read as a pass again.
    if tool is None or not os.path.exists(tool):
        print("hole fixtures: FAIL — forefst.py not found (looked for forefstdev/forefst.py and "
              "forefst.py under %s). A missing tool looks exactly like a successful refusal, so this "
              "is a failure, not a skip." % ROOT)
        return 1
    probe = subprocess.run([sys.executable, tool, "--help"], capture_output=True, timeout=300)
    if probe.returncode != 0 and not probe.stdout:
        print("hole fixtures: FAIL — %s did not run (`--help` exited %d with no output)"
              % (tool, probe.returncode))
        return 1
    rows = []
    for line in open(TSV, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#") or line.startswith("id\t"):
            continue
        rows.append(line.split("\t"))
    if not rows:
        print("hole fixtures: FAIL — no rows in hole_fixtures.tsv")
        return 1

    failures = []
    for fid, producer, image, want_hash, offset_s, path, exp_def, exp_ref in rows:
        src = _locate(image)
        if src is None:
            # SKIP, not FAIL: the fixture volumes are large sample images that do not live in the
            # repository. Anyone holding them can run these; a clone without them must not report a
            # failure it cannot act on -- but it must not report a pass either.
            print(f"hole fixtures: SKIP — {fid}: {os.path.basename(image)} not found "
                  f"(pass --images DIR, or place it under analysis/)")
            skipped.append(fid)
            continue
        got_hash = allocated_sha256(src)
        if want_hash not in ("-", got_hash):
            failures.append(f"{fid}: image content hash changed — recipe pinned {want_hash[:16]}…, "
                            f"image is {got_hash[:16]}… (the fixture may no longer describe this volume)")
            continue
        offset = int(offset_s, 0)
        tmpd = tempfile.mkdtemp(prefix="holefx_")
        vol = os.path.join(tmpd, "vol.raw")
        try:
            carve(src, vol)
            rc = subprocess.run(["fallocate", "--punch-hole", "--keep-size", "--offset", str(offset),
                                 "--length", "4096", vol], capture_output=True).returncode
            if rc != 0:
                failures.append(f"{fid}: could not punch {offset:#x}")
                continue
            for mode, expect in (("default", exp_def), ("refuse", exp_ref)):
                out = os.path.join(tmpd, "out_" + mode)
                cmd = [sys.executable, tool, vol, "extract", path, "-o", out]
                if mode == "refuse":
                    cmd.append("--refuse-holes")
                got_rc = subprocess.run(cmd, capture_output=True, timeout=3600).returncode
                got = "%d:%s:%s" % (got_rc,
                                    "written" if os.path.exists(out) else "none",
                                    "sidecar" if os.path.exists(out + ".holes.json") else "nosidecar")
                if got != expect:
                    failures.append(f"{fid} [{producer}, {mode}]: expected {expect}, got {got}")
        finally:
            subprocess.run(["rm", "-rf", tmpd])
    if failures:
        print(f"hole fixtures: FAIL — {len(failures)} check(s):")
        for f in failures:
            print("   " + f)
        return 1
    ran = len(rows) - len(skipped)
    if not ran:
        print(f"hole fixtures: SKIP — none of the {len(rows)} fixture volumes are present here.")
        return 0
    print(f"hole fixtures: PASS — {ran} of {len(rows)} fixture(s), both modes each, "
          f"rc/bytes/sidecar as specified"
          + (f" ({len(skipped)} skipped: volume not present)" if skipped else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
