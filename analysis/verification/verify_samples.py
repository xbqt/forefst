#!/usr/bin/env python3
"""Public golden for the four sample volumes — runnable from a clone, no private corpus needed.

The maintainer's gate pins 3,498 output fingerprints across ~100 images, none of which ship. That makes the
published claims unreproducible by anyone else, so this pins the same kind of fingerprint for the four
volumes that DO ship (git-lfs) and can be run by anyone with the repo.

  python3 analysis/verification/verify_samples.py --images DIR      # check against the committed golden
  python3 analysis/verification/verify_samples.py --images DIR --generate   # re-bless (maintainer)

DIR is searched recursively for the sample .raw files. Rows are keyed by BASENAME, not by path, so the
images can live anywhere. The tool VERSION is normalised out of the captured output, so a version bump alone
produces a zero-row diff and only real behaviour changes show up.

ALL FOUR images must be present: the script exits non-zero naming the missing ones rather than checking a
subset, because a partial run that reported PASS would certify less than it appears to. Decompress the
git-lfs samples first (they are stored compressed) and point --images at the directory holding them.

Exit 0 when every row matches (or, with --generate, when the golden is written).
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))          # analysis/verification -> analysis -> repo
GOLDEN = os.path.join(HERE, "golden_samples.txt")

SAMPLES = ("win11refs2tsnapshots.raw", "win11refs2tspecials.raw",
           "win11refstestmftecmd.raw", "wininsiderrefs8gtest2.raw")

# The same shape as the maintainer's golden: one row per (image, command), hashing stdout+stderr together.
FE_CMDS = ("files --csv", "files --json", "summary --json", "fastsummary --json", "deleted",
           "usn --stats", "timeline --csv", "timestomp --csv", "specials --json", "ads --json",
           "security --files", "reparse --index", "snapshots -v", "integrity", "integrity --checksums",
           "dataruns", "search a")
# `integrity --checksums` is listed separately from `integrity`: the page-reference verification it gates is
# never reached by the plain command, so without this row the feature has no public coverage at all.
RA_CMDS = ("summary --json", "boot -vv", "supb -vv", "chkp -vv", "objects", "schema", "containers")


def find_images(root):
    found = {}
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn in SAMPLES and fn not in found:
                found[fn] = os.path.join(dirpath, fn)
    return found


def tool_version():
    try:
        with open(os.path.join(REPO, "forefst.py"), encoding="utf-8") as fh:
            m = re.search(r'^VERSION\s*=\s*"([^"]+)"', fh.read(), re.M)
        return m.group(1) if m else "?"
    except OSError:
        return "?"


def rows(images, ver):
    pat = re.compile(r"\[forefst v" + re.escape(ver) + r"\]")
    for name in SAMPLES:
        img = images.get(name)
        if img is None:
            continue
        for tool, cmds in (("forefst.py", FE_CMDS), ("refsanalysis.py", RA_CMDS)):
            path = os.path.join(REPO, tool)
            if not os.path.exists(path):
                continue
            for c in cmds:
                r = subprocess.run([sys.executable, path, img] + c.split(),
                                   capture_output=True, text=True, timeout=1800)
                out = pat.sub("[forefst v@VER@]", (r.stdout or "") + (r.stderr or ""))
                # The image PATH is printed by several commands (`refsanalysis boot -vv` prints an
                # "Image:" line), so without this the fingerprint depends on where the caller keeps the
                # images -- the golden would only ever match in the tree it was blessed in, which is the
                # opposite of what this file is for. Normalise the directory, keeping the basename, which
                # is the part that identifies the volume.
                out = out.replace(img, "@IMG@/" + name)
                d = os.path.dirname(os.path.abspath(img))
                if d:
                    out = out.replace(d, "@IMG@")
                yield "%s|%s %s|rc=%d|%s" % (name, tool, c, r.returncode,
                                             hashlib.sha256(out.encode("utf-8", "replace")).hexdigest())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--images", required=True,
                    help="directory searched recursively for the sample .raw files; ALL FOUR must be present")
    ap.add_argument("--generate", action="store_true", help="write the golden instead of checking it")
    a = ap.parse_args()
    images = find_images(a.images)
    missing = [s for s in SAMPLES if s not in images]
    if missing:
        print("MISSING sample image(s) under %s: %s" % (a.images, ", ".join(missing)))
        print("A partial run cannot certify the release; fetch the git-lfs objects and retry.")
        return 2
    got = sorted(rows(images, tool_version()))
    if a.generate:
        with open(GOLDEN, "w", encoding="utf-8") as fh:
            fh.write("\n".join(got) + "\n")
        print("wrote %s (%d rows) for %d images" % (GOLDEN, len(got), len(images)))
        return 0
    if not os.path.exists(GOLDEN):
        print("no golden at %s — run with --generate first" % GOLDEN)
        return 1
    want = [l.rstrip("\n") for l in open(GOLDEN, encoding="utf-8") if l.strip()]
    if got == want:
        print("PASS — %d rows, 0 changed (%d images, tool v%s)" % (len(got), len(images), tool_version()))
        return 0
    wset, gset = set(want), set(got)
    changed = sorted(gset - wset)
    print("FAIL — %d of %d rows differ" % (len(changed), len(want)))
    for row in changed[:20]:
        print("   now: %s" % row)
    return 1


if __name__ == "__main__":
    sys.exit(main())
