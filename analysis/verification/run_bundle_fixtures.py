#!/usr/bin/env python3
"""Run the bundle round-trip fixtures: a bundle must reproduce its source volume.

Published v1.12.1 shipped bundles that disagreed with their source volume on 31 split-record files, because
`export metadata` captured the pages its own walk enumerated and a listing also fetches some backing records
ON DEMAND. Gate 1h proves the fix in the maintainer's tree; this is the version a reader can run from a
clone, shipped like the hole fixtures.

Each row asserts two things and deliberately no more:
  * the bundle's `files --csv` is BYTE-IDENTICAL to the source volume's, and
  * the written index carries at least `min_ondemand` rows tagged `on-demand`.

It does not pin the exact on-demand count or the `inline_content` figure -- those are properties of one
sample, and pinning them would break the fixture on a harmless sample regeneration. The exact figures are
the golden's job.

Usage:  run_bundle_fixtures.py [--images DIR]
Skips (never passes) when a fixture volume is absent: a comparison of zero volumes proves nothing.
"""
import csv
import glob
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPEC = os.path.join(HERE, "bundle_fixtures.tsv")

sys.path.insert(0, HERE)
try:
    from run_hole_fixtures import volume_pin            # one definition of the content pin
except Exception:                                        # pragma: no cover
    volume_pin = None


def _locate(image):
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


def _tool():
    for cand in ("forefstdev/forefst.py", "forefst.py"):
        p = os.path.join(ROOT, cand)
        if os.path.exists(p):
            return p
    return None


def rows():
    out = []
    with open(SPEC, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                out.append((p[0], int(p[1]), p[2], p[3] if len(p) > 3 else ""))
    return out


def main():
    tool = _tool()
    if not tool:
        print("bundle fixtures: FAIL - forefst.py not found"); return 1
    spec = rows()
    if not spec:
        print("bundle fixtures: FAIL - no fixtures defined; the check would pass vacuously"); return 1

    ran, skipped, problems = 0, [], []
    for image, min_ondemand, pin, _why in spec:
        path = _locate(image)
        if not path:
            skipped.append(os.path.basename(image)); continue
        # Identity, not just a name: `_locate` searches by BASENAME, so without this a fixture could
        # silently run against a different volume that happens to share the name and still report PASS.
        if pin and volume_pin is not None:
            got = volume_pin(path)[:len(pin)]
            if got != pin:
                problems.append("%s: volume_pin %s, fixture expects %s -- this is not the volume the "
                                "fixture was written against" % (os.path.basename(path), got, pin))
                continue
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "bundle")
            r = subprocess.run([sys.executable, tool, path, "export", "metadata", out],
                               capture_output=True, text=True, timeout=3600)
            # C1-2 (1.14.0): the tool's exit contract -- 0 ran, 2 ran with a finding or with work it could not complete (its output says which), 1
            # could not run. Exit 2 was a "failed" export / listing here; it is a run. Any other exit is a problem.
            if r.returncode not in (0, 2):
                problems.append("%s: export metadata failed (exit %d: %s)"
                                % (os.path.basename(path), r.returncode, r.stderr.strip()[-120:]))
                continue
            a = subprocess.run([sys.executable, tool, path, "files", "--csv"],
                               capture_output=True, text=True, timeout=3600)
            b = subprocess.run([sys.executable, tool, out, "files", "--csv"],
                               capture_output=True, text=True, timeout=3600)
            if a.returncode not in (0, 2) or b.returncode not in (0, 2):
                problems.append("%s: could not list both the volume and its bundle (exit %d / %d)"
                                % (os.path.basename(path), a.returncode, b.returncode))
                continue
            if a.stdout != b.stdout:
                ra = list(csv.DictReader(io.StringIO(a.stdout)))
                rb = list(csv.DictReader(io.StringIO(b.stdout)))
                d = sum(1 for x, y in zip(ra, rb) if x != y) + abs(len(ra) - len(rb))
                problems.append("%s: bundle listing differs from the volume on %d row(s)"
                                % (os.path.basename(path), d))
            elif a.stdout.count("\n") < 2:
                problems.append("%s: the listings match but cover no rows" % os.path.basename(path))
            idx = os.path.join(out, "metadata_index.csv")
            n = 0
            if os.path.exists(idx):
                n = sum(1 for row in csv.reader(open(idx)) if len(row) > 3 and row[3] == "on-demand")
            if n < min_ondemand:
                problems.append("%s: %d on-demand row(s), expected at least %d -- the recording pass is "
                                "not capturing what the reader asks for"
                                % (os.path.basename(path), n, min_ondemand))
            ran += 1

    if problems:
        print("bundle fixtures: FAIL - %d problem(s) over %d fixture(s)" % (len(problems), ran))
        for p in problems:
            print("   - %s" % p)
        return 1
    if ran == 0:
        print("bundle fixtures: SKIP - no fixture volume present (looked for %s). A comparison of zero "
              "volumes proves nothing." % ", ".join(skipped))
        return 0
    note = ("; %d skipped (volume absent)" % len(skipped)) if skipped else ""
    print("bundle fixtures: PASS - %d of %d fixture(s); each bundle's listing is byte-identical to its "
          "volume and carries the on-demand pages the reader needs%s" % (ran, len(spec), note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
