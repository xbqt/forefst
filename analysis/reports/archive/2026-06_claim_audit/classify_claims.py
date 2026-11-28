#!/usr/bin/env python3
"""P0.3 — classify each reference_table claim into a proof class (the typed proof-obligation model)."""
import csv, re, os
_REPO=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..",".."))
CSV = os.path.join(_REPO,"analysis","reference_table.csv")  # in-tree canonical copy
rows = list(csv.DictReader(open(CSV)))
NEG = re.compile(r"\bnot\b|\bno\b|\bnever\b|\bzero\b|\babsent\b|fabricat|abolish|eliminat|unsupported|"
                 r"=\s*0\b|\b0/|does not|do not|n't\b|retract|no such|not a |not the ", re.I)
LIT = re.compile(r"PRADE|LEE|NORDVIK|GEORGES|WININT|literature|inferred|likely|may be|appears to", re.I)
OFF = re.compile(r"0x[0-9a-fA-F]{1,3}\b|offset|byte|field|@\+?0x")
def classify(r):
    sev = (r["static_evidence_level"] or "").strip().upper()
    vt = (r["verification_target"] or "").strip()
    desc = r["description"] or ""
    has_static = sev not in ("", "N/A") and "E" in sev
    has_rd = "RD" in sev or (r["raw_analysis_status"] or "") in ("CONFIRMED","ENRICHED","NEW","CORRECTED")
    if NEG.search(desc[:160]):
        return "ABSENCE"
    if not has_static and not has_rd:
        return "LITERATURE"
    if sev == "N/A" and has_rd:
        return "PURE-RD-LAYOUT"
    if has_static and not OFF.search(desc) and vt == "No":
        return "BEHAVIORAL"
    if OFF.search(desc) and (has_rd or has_static):
        return "STRUCTURAL"
    if has_static:
        return "BEHAVIORAL"
    return "PURE-RD-LAYOUT"
out=[]
for r in rows:
    out.append({"ref_id": r["ref_id"], "category": r["category"], "proof_class": classify(r),
                "static_evidence_level": r["static_evidence_level"],
                "verification_target": r["verification_target"]})
with open(os.path.join(os.path.dirname(__file__),"claim_class.csv"),"w",newline="") as fo:
    w=csv.DictWriter(fo,fieldnames=["ref_id","category","proof_class","static_evidence_level","verification_target"])
    w.writeheader(); w.writerows(out)
from collections import Counter
c=Counter(o["proof_class"] for o in out)
print("claim classes (n=%d):"%len(out), dict(c))
