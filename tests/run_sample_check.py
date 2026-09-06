#!/usr/bin/env python3
"""Re-run every command in the shipped sample manifests and diff against the stored output.

The published repo ships four sample volumes under `analysis/samples/disks/<name>/`, each with a
`manifest.md` listing exactly which command produced each recorded file. That manifest is the
spec: this runner parses it, re-executes each command against the image, and compares. It is how
a fresh clone checks the tool without the private corpus.

Usage:
    python3 tests/run_sample_check.py --images DIR [--sample NAME] [--tool ./forefst.py]

DIR holds the decompressed sample images (`<name>.raw`); the archives ship as `.zst`.
Exit 0 when every recorded output reproduces byte-for-byte, 1 otherwise.

Note: `extract` writes BINARY to stdout, so its recorded files are compared as bytes, never
through a text pipeline.
"""
import argparse
import os
import re
import subprocess
import sys

ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*$")


def manifest_rows(path):
    """[(recorded_file, argv_tail)] for one manifest.md."""
    out = []
    section = None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^##\s+(\S+)/\s*$", line.strip())
        if m:
            section = m.group(1)
            continue
        m = ROW.match(line.rstrip("\n"))
        if m and section:
            out.append((os.path.join(section, m.group(1)), m.group(2)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, help="directory holding the decompressed <name>.raw")
    ap.add_argument("--sample", help="check only this sample")
    ap.add_argument("--tool", default=None, help="path to forefst.py (default: beside this repo)")
    ap.add_argument("--samples-root", default=None)
    a = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = a.samples_root or os.path.join(repo, "analysis", "samples", "disks")
    tools = {"forefst": a.tool or os.path.join(repo, "forefst.py"),
             "refsanalysis": os.path.join(repo, "refsanalysis.py")}
    if not os.path.isdir(root):
        print("no samples at %s" % root)
        return 1

    total = same = missing = differ = 0
    for name in sorted(os.listdir(root)):
        if a.sample and name != a.sample:
            continue
        d = os.path.join(root, name)
        man = os.path.join(d, "manifest.md")
        if not os.path.isfile(man):
            continue
        img = os.path.join(a.images, name + ".raw")
        if not os.path.isfile(img):
            print("SKIP %-34s image not found: %s" % (name, img), flush=True)
            continue
        for rel, cmd in manifest_rows(man):
            recorded = os.path.join(d, rel)
            if not os.path.isfile(recorded):
                continue
            total += 1
            # Progress must be visible: a 77-command run against a 2 TB image takes minutes, and
            # buffered stdout made it look hung.
            print("  [%3d] %-30s %s" % (total, rel, cmd), flush=True)
            parts = cmd.split()
            tool = tools.get(parts[0])
            if not tool:
                continue
            argv = [sys.executable, tool, img] + parts[2:]
            try:
                got = subprocess.run(argv, capture_output=True, timeout=1800).stdout
            except subprocess.TimeoutExpired:
                print("TIMEOUT %-30s %s" % (name, rel), flush=True)
                differ += 1
                continue
            want = open(recorded, "rb").read()
            if got == want:
                same += 1
            else:
                differ += 1
                print("DIFFER  %-30s %-28s recorded=%d bytes, got=%d"
                      % (name, rel, len(want), len(got)), flush=True)
    print("\n%d compared: %d identical, %d differ, %d missing" % (total, same, differ, missing))
    return 0 if differ == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
