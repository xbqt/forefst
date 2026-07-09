#!/usr/bin/env python3
"""P0.1 — build the canonical image manifest (images.csv) for the claim-audit system.
Reads VBR + CHKP directly (fast); classifies ReFS vs control; groups before/after lineages by serial."""
import sys, os, glob, csv, struct, hashlib
_REPO=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..",".."))
_CORPUS=os.environ.get("REFS_CORPUS", os.path.dirname(_REPO))
sys.path.insert(0, _REPO)
from forefst import find_refs_partition, parse_supb, parse_chkp, le16, le32, le64

DISKS = os.environ.get("REFS_DISKS", os.path.join(_CORPUS,"analysis","rawdisk","disks"))
CKSUM = {0: "None", 2: "CRC64", 4: "SHA256"}
DERIVED_KW = ("before", "after", "_opened", "remount", "detach", "salvage", "changing",
              "corruption", "corrupt", "rechanged", "_test2", "test3", "_unmount")

def probe(path):
    r = {"path": os.path.relpath(path, _CORPUS), "basename": os.path.basename(path),
         "is_refs": False, "version": "", "cluster": "", "checksum": "", "vol_flags": "",
         "state": "", "serial": "", "ext_guid": "", "note": ""}
    try:
        ps, desc = find_refs_partition(path)
    except Exception as e:
        ps = None; r["note"] = f"part:{type(e).__name__}"
    f = open(path, "rb")
    try:
        # sniff sig at ps (or 0)
        base = ps if ps is not None else 0
        f.seek(base); bs = f.read(512)
        if bs[3:7] == b"ReFS":
            r["is_refs"] = True
            r["version"] = f"{bs[0x28]}.{bs[0x29]}"
            cs = le32(bs, 0x20) * le32(bs, 0x24); r["cluster"] = cs
            r["checksum"] = CKSUM.get(le16(bs, 0x2A), f"0x{le16(bs,0x2a):x}")
            r["vol_flags"] = f"0x{le32(bs,0x2c):x}"
            r["serial"] = f"0x{le64(bs,0x38):x}"
            g = bs[0x48:0x58]; r["ext_guid"] = "set" if any(g) else "zero"
            # CHKP state
            try:
                chkp = parse_supb(f, ps, cs); best_vc = -1; flags = None
                for cl in chkp:
                    try:
                        vc, fl, _ = parse_chkp(f, ps, cs, cl)
                        if vc > best_vc: best_vc = vc; flags = fl
                    except Exception: pass
                if flags is not None:
                    low = flags & 0xFFF
                    r["state"] = {0x002: "original", 0x602: "upgraded", 0x682: "native",
                                  0x682 & 0xFFF: "native"}.get(low, f"flags=0x{flags:x}")
            except Exception as e:
                r["note"] += f" chkp:{type(e).__name__}"
        elif b"NTFS" in bs[:16]:
            r["note"] = "NTFS control"
        elif b"-FVE-FS-" in bs[:16]:
            r["note"] = "BitLocker control"
        else:
            r["note"] = r["note"] or "no ReFS sig"
    finally:
        f.close()
    bn = r["basename"].lower()
    r["derived"] = any(k in bn for k in DERIVED_KW)
    return r

rows = [probe(p) for p in sorted(glob.glob(f"{DISKS}/**/*.raw", recursive=True))]
# lineage groups by serial
from collections import defaultdict
by_serial = defaultdict(list)
for r in rows:
    if r["is_refs"] and r["serial"]: by_serial[r["serial"]].append(r)
for r in rows:
    r["baseline_group"] = r["serial"][:10] if r["serial"] else ""
    r["independent"] = r["is_refs"] and not r["derived"]

cols = ["path","basename","is_refs","version","cluster","checksum","state","vol_flags",
        "serial","ext_guid","baseline_group","derived","independent","note"]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images.csv")
with open(out, "w", newline="") as fo:
    w = csv.DictWriter(fo, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow({k: r.get(k, "") for k in cols})

refs = [r for r in rows if r["is_refs"]]
indep = [r for r in refs if r["independent"]]
print(f"total .raw: {len(rows)} | ReFS: {len(refs)} | controls: {len(rows)-len(refs)} | independent: {len(indep)} | lineages: {len(by_serial)}")
from collections import Counter
print("versions:", dict(Counter(r["version"] for r in refs)))
print("cluster:", dict(Counter(r["cluster"] for r in refs)))
print("checksum:", dict(Counter(r["checksum"] for r in refs)))
print("state:", dict(Counter(r["state"] for r in refs)))
print("→", out)
