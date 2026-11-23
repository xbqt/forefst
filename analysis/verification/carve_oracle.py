#!/usr/bin/env python3
"""The public carve oracle -- a third source for recovered content, runnable from a clone.

Why this exists. The v1.13.0 release classified 111 refused carves as fabrications without a ground-truth
control, and was wrong: 86 of them are byte-identical to the file that is still live. The control was on the
same public volume the whole time. This oracle IS that control, so the classification cannot be issued
without it again.

Three independent sources, none of them this tool's opinion of itself:
  1. the LIVE TWIN -- the file still on the volume with the same name and size as the deleted remnant;
  2. WINDOWS' OWN JOURNAL -- `fsutil usn readjournal`, exported on the live system before imaging and
     shipped with the sample (provenance/usn_readjournal_export.txt). It holds history the image's
     journal ring has since overwritten;
  3. the carve itself.

A twin is used only when Windows' journal shows its data was written in ONE close-bounded episode and
never changed afterwards: then any prior version captured after that write must equal the live file.

For each such file the oracle requires one of:
  * the carve EQUALS the twin;
  * the carve differs ONLY inside the runs the tool DISCLOSED as zero-filled (`unwritten_runs` in the
    manifest), and is zero there;
  * there is no carve, and the manifest says why (`refused_all_unwritten`).
Anything else fails: a difference outside disclosed runs is invented content; a refusal without a reason
is silent loss.

N565 (1.14.0): WC-3 carves no map of a file that is still live (`RecoverabilityCode` live_file_map: the clusters may
hold its current content; carving an earlier version of a live file is planned for a later release), and those were
nearly all the carves this oracle judged (1.13.1 on the sample: 318 judged; 1.14.0: 1). For those records the oracle
checks 1.14.0's contract instead: no carve file, and the reason stated (`NoCarveReason`).

  python3 analysis/verification/carve_oracle.py --images DIR [--tool PATH]
"""
import argparse, csv, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(os.path.dirname(HERE))
SAMPLE = "win11refstestmftecmd"
DATA_REASONS = 0x1 | 0x2 | 0x4            # data overwrite | data extend | data truncation
CLOSE = 0x80000000


def find(root, name):
    for d, _s, fs in os.walk(root):
        if name in fs:
            return os.path.join(d, name)
    return None


def journal(path):
    """{(home_oid, file_id): [(usn, reason), ...]} from a `fsutil usn readjournal` text export."""
    out, cur = {}, {}
    def flush():
        if "File ID" in cur and "Reason" in cur and "Usn" in cur:
            fid = cur["File ID"]
            key = (int(fid[:16], 16), int(fid[16:], 16))
            out.setdefault(key, []).append((int(cur["Usn"]), int(cur["Reason"].split(":")[0], 16)))
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip():
            flush(); cur = {}
            continue
        m = re.match(r"([A-Za-z][\w ]*?)\s*:\s(.*)$", line)
        if m:
            cur[m.group(1).strip()] = m.group(2).strip()
    flush()
    return out


def written_once(history):
    """True iff every data-changing record falls before the FIRST close that ends a data episode."""
    closed = False
    for _usn, r in sorted(history):
        if r & DATA_REASONS:
            if closed:
                return False
            if r & CLOSE:
                closed = True
        elif closed is False and (r & CLOSE) and any(x & DATA_REASONS for _u, x in history if _u < _usn):
            closed = True
    return any(r & DATA_REASONS for _u, r in history)


def run(tool, *args, out=None):
    return subprocess.run([sys.executable, "-B", tool] + list(args), capture_output=True,
                          text=out is None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--tool", default=None)
    a = ap.parse_args()
    tool = a.tool or next((p for p in (os.path.join(TREE, "forefst.py"),
                                       os.path.join(os.path.dirname(TREE), "forefst.py")) if os.path.isfile(p)), None)
    img = find(a.images, SAMPLE + ".raw")
    exp = find(os.path.join(TREE, "analysis", "samples"), "usn_readjournal_export.txt")
    if not (tool and img and exp):
        print("carve oracle: SKIP -- need the tool, %s.raw (git-lfs) and the shipped journal export" % SAMPLE)
        return 0
    hist = journal(exp)
    live = {}
    for r in csv.DictReader(io.StringIO(run(tool, img, "files", "--csv").stdout)):
        try:
            h, fid = (int(x, 16) for x in r["ObjectRef"].split(":"))
            live.setdefault((r["FileName"], int(r["FileSize"] or -1)), []).append(((h, fid), r["FullPath"]))
        except (ValueError, KeyError):
            continue
    work = tempfile.mkdtemp(prefix="carve_oracle_")
    try:
        run(tool, img, "export", "deleted", "--carve", work)
        man = json.load(open(os.path.join(work, "recovery_manifest.json"), encoding="utf-8"))
        # N565 (1.14.0): the manifest's keys are the index's (N317: `Records`, `FileName`, `RecoverabilityCode`, ...;
        # `is_resident` no longer written); read by the 1.13.1 names the oracle raised KeyError on the 1.14.0 tool.
        # Both forms are read, so it runs against either release.
        def g(m, new, old):
            return m.get(new, m.get(old))
        entries = g(man, "Records", "records")   # "Entries" is the COUNT; the per-file records are under "Records"
        tally = {"equal": 0, "differs_only_in_disclosed_runs": 0, "refused_with_reason": 0,
                 "FAIL_undisclosed_difference": 0, "FAIL_silent_refusal": 0, "no_usable_twin": 0}
        livemap = {"live_map_not_carved_stated": 0, "FAIL_live_map_carved": 0, "FAIL_live_map_silent": 0}
        fails = []
        cs = 4096
        for m in entries:
            if g(m, "RecoverabilityCode", "recoverable") == "live_file_map":
                if g(m, "ContentFile", "content_file"):
                    livemap["FAIL_live_map_carved"] += 1; fails.append(("a live file's map carved", g(m, "FileName", "name")))
                elif not m.get("NoCarveReason"):
                    livemap["FAIL_live_map_silent"] += 1; fails.append(("a live file's map, no reason", g(m, "FileName", "name")))
                else:
                    livemap["live_map_not_carved_stated"] += 1
                continue
            if m.get("is_resident") or g(m, "RecoverabilityCode", "recoverable") != "extent_backed":
                continue
            # a refused carve has no carved size; without the declared one it could never be matched, and a
            # refusal that cannot be matched is one the oracle silently never judges
            size = g(m, "CarvedDeclaredSize", "carved_declared_size") or g(m, "DeclaredSize", "declared_size") or 0
            cands = live.get((g(m, "FileName", "name"), size)) or []
            cands = [(k, p) for k, p in cands if k in hist and written_once(hist[k])]
            if len(cands) != 1:
                tally["no_usable_twin"] += 1
                continue
            _k, path = cands[0]
            tw = os.path.join(work, "_twin.bin")
            run(tool, img, "extract", "/" + path, "-o", tw, out=True)
            if not os.path.isfile(tw):
                tally["no_usable_twin"] += 1
                continue
            twin = open(tw, "rb").read(); os.remove(tw)
            cf = g(m, "ContentFile", "content_file")
            if not cf:
                if g(m, "RefusedAllUnwritten", "refused_all_unwritten"):
                    tally["refused_with_reason"] += 1
                else:
                    tally["FAIL_silent_refusal"] += 1; fails.append(("silent refusal", g(m, "FileName", "name")))
                continue
            carve = open(os.path.join(work, cf), "rb").read()
            if carve == twin:
                tally["equal"] += 1
                continue
            allowed = set()
            for fv, n in (g(m, "UnwrittenRuns", "unwritten_runs") or []) + (g(m, "HoleRuns", "hole_runs") or []):
                allowed.update(range(fv * cs, (fv + n) * cs))       # both are "this version held no data here"
            bad = [i for i in range(min(len(carve), len(twin))) if carve[i] != twin[i]
                   and not (i in allowed and carve[i] == 0)]
            if bad or len(carve) != len(twin):
                tally["FAIL_undisclosed_difference"] += 1
                fails.append(("differs outside disclosed runs (%d byte(s))" % len(bad), g(m, "FileName", "name")))
            else:
                tally["differs_only_in_disclosed_runs"] += 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for why, n in fails[:10]:
        print("  FAIL %-44s %s" % (why, n))
    judged = sum(v for k, v in tally.items() if k != "no_usable_twin")
    print("  " + "  ".join("%s=%d" % kv for kv in tally.items()))
    print("  " + "  ".join("%s=%d" % kv for kv in livemap.items()))
    bad = tally["FAIL_undisclosed_difference"] + tally["FAIL_silent_refusal"] + livemap["FAIL_live_map_carved"] \
        + livemap["FAIL_live_map_silent"]
    if judged == 0 and not livemap["live_map_not_carved_stated"]:
        bad = 1                                   # N565: a run that judged no carve has checked nothing
        print("  FAIL no carve judged (%d manifest record(s), %d extent-backed): the oracle checked nothing"
              % (len(entries), sum(1 for m in entries if g(m, "RecoverabilityCode", "recoverable") == "extent_backed")))
    print("carve oracle: %s -- %d carve(s) judged against a live twin whose data Windows' journal shows "
          "written once, %d live file map(s) not carved with the reason stated, %d fail"
          % ("FAIL" if bad else "PASS", judged, livemap["live_map_not_carved_stated"], bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
