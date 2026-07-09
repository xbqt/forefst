#!/usr/bin/env python3
"""P0.2 — best-effort findings_register #N <-> reference_table ref_id crosswalk (token overlap). Residue flagged."""
import csv, re, os
_REPO=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..",".."))
_FINDINGS=os.environ.get("REFS_FINDINGS", os.path.join(_REPO,"analysis","findings_register.md"))  # private thesis register; not bundled
rt=list(csv.DictReader(open(os.path.join(_REPO,"analysis","reference_table.csv"))))
# parse findings_register.md table rows: | N | section | type | desc... | evidence | status |
fr=[]
for line in open(_FINDINGS):
    m=re.match(r"\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|(.*)\|([^|]*)\|([^|]*)\|\s*$", line)
    if m: fr.append((int(m.group(1)), m.group(4).strip()))
def toks(s):
    return set(re.findall(r"0x[0-9a-f]+|[A-Z][a-zA-Z]{4,}|[a-z]{5,}", s.lower()))
rt_tok=[(r["ref_id"], toks(r["description"])) for r in rt]
matches=[]; unmapped=0
for n,desc in fr:
    ft=toks(desc)
    best=None;bs=0
    for rid,rtk in rt_tok:
        ov=len(ft&rtk)
        if ov>bs: bs=ov;best=rid
    conf = "high" if bs>=6 else ("med" if bs>=3 else "low")
    if conf=="low": unmapped+=1
    matches.append({"finding":n,"ref_id":best if conf!="low" else "","overlap":bs,"confidence":conf})
with open(os.path.join(os.path.dirname(__file__),"crosswalk.csv"),"w",newline="") as fo:
    w=csv.DictWriter(fo,fieldnames=["finding","ref_id","overlap","confidence"]);w.writeheader();w.writerows(matches)
from collections import Counter
print(f"findings parsed: {len(fr)} | mapped(high/med): {len(fr)-unmapped} | residue(low,manual): {unmapped}")
print("confidence:", dict(Counter(m['confidence'] for m in matches)))
