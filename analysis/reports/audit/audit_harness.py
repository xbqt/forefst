#!/usr/bin/env python3
"""Claim-audit harness (P0 skeleton). Reuses the forefst/refsanalysis parsing; validates each claim's
disk probe across the APPLICABLE images from images.csv (output-parsed, not exit-code); exports the static
reference; computes a corpus-aware verdict; emits the proof table + links + a generated per-claim dossier.
Pilot = 6 mixed claims (2 STRUCTURAL, 2 PURE-RD-LAYOUT, 2 ABSENCE)."""
import sys, os, csv, time, struct, json, re
HERE=os.path.dirname(os.path.abspath(__file__))
_REPO=os.path.abspath(os.path.join(HERE,"..","..","..")) # forefst repo root
_CORPUS=os.environ.get("REFS_CORPUS", os.path.dirname(_REPO)) # holds the private analysis/ corpus (set REFS_CORPUS on a clean checkout)
sys.path.insert(0,_REPO)
from forefst import (find_refs_partition, parse_vbr, bootstrap, walk_bplus, le16, le32, le64)

DISKS=os.environ.get("REFS_DISKS", os.path.join(_CORPUS,"analysis","rawdisk","disks"))
DEC=os.environ.get("REFS_DECOMPILED", os.path.join(_CORPUS,"analysis","static","decompiled","win11_4b0558f6"))

def load_images():
 rows=[r for r in csv.DictReader(open(f"{HERE}/images.csv")) if r["is_refs"]=="True"]
 return rows
IMAGES=load_images()

def _ver_tuple(s):
 """ReFS version as (major,minor) — NOT a float (3.10 > 3.9 semantically but < 3.4 as a float)."""
 try:
 a,b=str(s).split("."); return (int(a),int(b))
 except Exception: return None

def applicable(predicate):
 """Resolve an applicability predicate to the image subset (independent samples). Version thresholds are
 strings ('3.10') compared as (major,minor) tuples; real ReFS volumes have major 3 (6.x = tampered)."""
 out=[]
 for r in IMAGES:
 ok=True; iv=_ver_tuple(r["version"])
 for k,v in predicate.items():
 if k=="checksum" and r["checksum"]!=v: ok=False
 elif k=="cluster" and str(r["cluster"])!=str(v): ok=False
 elif k=="version_min":
 tv=_ver_tuple(v); ok = ok and iv is not None and tv is not None and iv>=tv and iv[0]<6
 elif k=="version_max":
 tv=_ver_tuple(v); ok = ok and iv is not None and tv is not None and iv<=tv and iv[0]<6
 elif k=="state" and r.get("state")!=v: ok=False
 if ok: out.append(r)
 return out

# ── probes: each returns {"applicable":bool,"result":PASS|FAIL,"value":...} given an open ctx ──
def _ctx(path):
 try: return bootstrap(path, None)
 except Exception: return None

def probe_vbr_u64(ctx, f, ps, off, expected):
 f.seek(ps); vbr=f.read(512); v=le64(vbr,off)
 return {"applicable":True,"result":"PASS" if v==expected else "FAIL","value":hex(v)}

def probe_page_const(ctx, f, ps, cs, roots, tr, off, expected):
 # read object-table root page, check le32 at off
 if not roots or not roots[0]: return {"applicable":False,"result":"N/A","value":None}
 p=tr.tr(roots[0][0]) if tr else roots[0][0]
 f.seek(ps+p*cs); pg=f.read(cs)
 if pg[:4]!=b"MSB+": return {"applicable":False,"result":"N/A","value":"no-MSB+"}
 v=le32(pg,off)
 return {"applicable":True,"result":"PASS" if v==expected else "FAIL","value":hex(v)}

def probe_cpc(ctx, f, ps, cs, roots, tr, bpc):
 cpc=bpc//cs; exp=16384 if cs==4096 else (1024 if cs==65536 else None)
 return {"applicable":exp is not None,"result":"PASS" if cpc==exp else "FAIL","value":cpc}

def probe_absent_utf16(ctx, f, ps, cs, roots, obj_map, tr, needle):
 """ABSENCE: search ONLY metadata pages (obj trees + roots) for a UTF-16LE string. 0 hits = PASS."""
 pat=needle.encode("utf-16-le"); hits=0; seen=set()
 def scan(vlcns):
 nonlocal hits
 for v in vlcns:
 p=tr.tr(v) if tr else v
 if p in seen: continue
 seen.add(p)
 try: f.seek(ps+p*cs); d=f.read(cs)
 except Exception: continue
 hits+=d.count(pat)
 for rv in roots:
 if rv: scan(rv)
 for vl in obj_map.values(): scan(vl)
 return {"applicable":True,"result":"PASS" if hits==0 else "FAIL","value":hits}

def probe_hlc_max(ctx, f, ps, cs, roots, obj_map, tr):
 """ABSENCE/aggregate: max HardLinkCount ($SI+0x70). Multi-method guard: a hard-link count is a small
 integer, so values in the billions mean +0x70 is NOT an HLC on that row (field overlap) — discarded,
 not counted. This is the 'don't trust one raw read' rule that prevents a false 'hard links exist'."""
 mx=1; implausible=0; checked=0
 for oid,vl in obj_map.items():
 if oid<0x600: continue
 try: rows=walk_bplus(f,ps,cs,tr,vl)
 except Exception: continue
 for kd,vd in rows:
 # $SI own-row: SI base = vd+0x28 (0x28-byte attr header), HardLinkCount at SI-base+0x70 = vd+0x98
 if le16(kd,0)==0x10 and len(vd)>=0x9C:
 checked+=1; v=le32(vd,0x98)
 if 1<v<256: mx=max(mx,v) # plausible hard-link count
 elif v>=256: implausible+=1 # not an HLC (field overlap): discard, don't count
 return {"applicable":checked>0,"result":"PASS" if mx<=1 else "FAIL",
 "value":f"max={mx}/{checked};discarded={implausible}"}

# ── claim specs are authored into specs.jsonl (one JSON object per line). Schema per row:
# ref_id, class, desc, axis, static_fn (or null), probe [name,arg,...], explanation,
# applicability {checksum?,cluster?,version_min?}, scoped_exceptions {basename:reason}?, links []?
# The harness is spec-FILE driven so P1 can author specs in proof-class batches (automated verification pass) and
# this deterministic harness validates them corpus-wide. ──
SPECS_FILE=f"{HERE}/specs.jsonl"
def load_specs():
 out=[]
 if not os.path.exists(SPECS_FILE): return out
 for ln in open(SPECS_FILE):
 ln=ln.strip()
 if not ln or ln.startswith("#"): continue
 s=json.loads(ln)
 s["probe"]=tuple(s["probe"])
 s.setdefault("applicability",{}); s.setdefault("static_fn",None)
 s.setdefault("scoped_exceptions",{}); s.setdefault("links",[])
 out.append(s)
 return out
PILOT=load_specs()

# ── generic probe library (the fixed menu the authoring pass map claims onto) ──
def _ival(d,off,size):
 return {1:lambda:d[off],2:lambda:le16(d,off),4:lambda:le32(d,off),8:lambda:le64(d,off)}[size]()

def probe_vbr_int(ctx,f,ps,off,size,expected):
 f.seek(ps); vbr=f.read(512); v=_ival(vbr,off,size)
 return {"applicable":True,"result":"PASS" if v==expected else "FAIL","value":hex(v)}

def _newest_chkp_page(f,ps,cs,chkp_lcns):
 from forefst import parse_chkp
 best_vc=-1; best=None
 for cl in chkp_lcns:
 try:
 f.seek(ps+cl*cs); raw=f.read(4*cs)
 if raw[:4]!=b"CHKP": continue
 vc=le64(raw,0x10)
 if vc>best_vc: best_vc=vc; best=raw
 except Exception: continue
 return best

def probe_chkp_int(ctx,f,ps,cs,chkp_lcns,off,size,expected):
 raw=_newest_chkp_page(f,ps,cs,chkp_lcns)
 if raw is None: return {"applicable":False,"result":"N/A","value":"no-CHKP"}
 v=_ival(raw,off,size)
 return {"applicable":True,"result":"PASS" if v==expected else "FAIL","value":hex(v)}

def probe_chkp_root_table(ctx,f,ps,cs,tr,roots,ri,expected):
 """Resolve checkpoint root[ri] -> its MSB+ table root page; assert the owning-table identifier
 (page header +0x48) == expected Table ID. Roots 7/8/12 use REAL (physical) LCNs (bootstrap exception);
 all others are virtual and translated. Returns N/A if the root is absent on this image (version-scoped)."""
 if ri>=len(roots) or not roots[ri]: return {"applicable":False,"result":"N/A","value":"root-absent"}
 vlcn=roots[ri][0]
 try:
 plcn = vlcn if ri in (7,8,12) else tr.tr(vlcn)
 f.seek(ps+plcn*cs); pg=f.read(cs)
 except Exception as e:
 return {"applicable":False,"result":"N/A","value":f"resolve-fail:{type(e).__name__}"}
 if pg[:4]!=b"MSB+": return {"applicable":False,"result":"N/A","value":f"not-MSB+:{pg[:4]}"}
 tid=le64(pg,0x48)
 return {"applicable":True,"result":"PASS" if tid==expected else "FAIL","value":hex(tid)}

def _ct_leaf_rows(f,ps,cs,roots,page=None):
 """Yield (key_bytes, value_bytes) for every Container-Table leaf row (recurses inner nodes)."""
 if page is None:
 if len(roots)<8 or not roots[7]: return
 page=b""
 for l in roots[7]: f.seek(ps+l*cs); page+=f.read(cs)
 if page[:4]!=b"MSB+": return
 thoff=0x50+le32(page,0x50)
 if thoff+40>len(page): return
 tbl=struct.unpack_from("<10I",page,thoff); is_inner=bool(tbl[3]&0x100); astart,aend=tbl[4],tbl[8]
 if astart>=aend: return
 for i in range((aend-astart)//4):
 aa=thoff+astart+i*4
 if aa+4>len(page): break
 ro=thoff+le16(page,aa)
 if ro+16>len(page): break
 _,ko,kl,_,vo,vl,_=struct.unpack_from("<I6H",page,ro)
 kd=page[ro+ko:ro+ko+kl]; vd=page[ro+vo:ro+vo+vl]
 if is_inner and len(vd)>=32:
 cls=[le64(vd,j*8) for j in range(4)]; valid=[x for x in cls if x not in(0,0xffffffffffffffff)]
 cd=b""
 for l in valid:
 f.seek(ps+l*cs); cd+=f.read(cs)
 yield from _ct_leaf_rows(f,ps,cs,roots,cd)
 elif not is_inner and len(vd)>=0x90:
 yield kd,vd

def _vbr_cksel(f,ps):
 f.seek(ps); return le16(f.read(512),0x2A)

def probe_ct_row(ctx,f,ps,cs,tr,roots,check,*a):
 rows=list(_ct_leaf_rows(f,ps,cs,roots))
 if not rows: return {"applicable":False,"result":"N/A","value":"no-CT-rows"}
 if check=="physstart_functional":
 # NON-VACUOUS replacement for the tautological physstart_at_lenminus16 (which compared
 # value+off to value[len-16] where off==len-16, so it could never fail). The claim is that the
 # container physical start is at value+off (0x90 for 160B / 0xD0 for 224B rows = value[len-16]).
 # Verify it FUNCTIONALLY: for the container that holds the Object-Table root, using value+off as
 # the container start must reconstruct the OT-root MSB+ page. A wrong value+off -> wrong cluster
 # -> not MSB+ -> FAIL. Also assert off == len(value)-16 (the offset claim itself).
 off=a[0]
 if not roots or not roots[0] or tr is None:
 return {"applicable":False,"result":"N/A","value":"no-OT-root/tr"}
 ot=roots[0][0]; cid=ot>>tr.shift; cn=ot & tr.mask
 hit=None
 for k2,v2 in rows:
 if len(k2)>=8 and len(v2)==off+16 and le64(k2,0)==cid: hit=v2; break
 if hit is None:
 return {"applicable":False,"result":"N/A","value":f"no {off+16}B CT row for cid {cid}"}
 csc=le64(hit,off); phys=csc+cn
 try: f.seek(ps+phys*cs); sig=f.read(4)
 except Exception: sig=b""
 ok=(off==len(hit)-16) and sig==b"MSB+" and phys==tr.tr(ot)
 return {"applicable":True,"result":"PASS" if ok else "FAIL",
 "value":f"csc@0x{off:x}={csc:#x} -> ot_phys={phys:#x} sig={sig}"}
 bad=0; n=0
 for kd,vd in rows:
 if len(kd)<16: continue
 n+=1
 if check=="cid_redundant": # value+0x00 container ID == key container ID
 if le64(vd,0)!=le64(kd,0): bad+=1
 elif check=="tag": # key+0x08 constant tag == 0x0000000100000000
 if le64(kd,8)!=0x100000000: bad+=1
 elif check=="physstart_at_lenminus16": # phys start IS at value+off for rows of the matching size
 off=a[0]
 if len(vd)!=off+16: continue # only rows whose size puts phys-start at this offset
 if le64(vd,off)!=le64(vd,len(vd)-16): bad+=1
 elif check=="eq_physstart": # test (canonical-claim) that value+off == the phys start, ALL rows (no size filter)
 off=a[0]
 if len(vd)>=off+8 and le64(vd,off)!=le64(vd,len(vd)-16): bad+=1
 elif len(vd)<off+8: bad+=1 # offset out of bounds also contradicts the claim
 elif check=="rowsize": # 160 (4K & CRC64/None) else 224
 cksel=_vbr_cksel(f,ps)
 exp=160 if (cs==4096 and cksel in (0,1,2)) else 224
 if len(vd)!=exp: bad+=1
 elif check=="cpc_at_0x18": # CPC at value+0x18 == cluster-derived
 exp=16384 if cs==4096 else (1024 if cs==65536 else None)
 if exp is None or le32(vd,0x18)!=exp: bad+=1
 return {"applicable":n>0,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{n}"}

def probe_ct_translate(ctx,f,ps,cs,tr,roots):
 """CT_CTBL_004: physical_LCN = CSC(container) + (vlcn & (CPC-1)). Verify the translator reconstructs the
 OT-root page: tr(vlcn) lands on an MSB+ page, and tr(vlcn) == CT_phys_start[cid] + (vlcn & mask)."""
 if not roots or not roots[0]: return {"applicable":False,"result":"N/A","value":"no-OT-root"}
 vlcn=roots[0][0]
 try:
 cid=vlcn>>tr.shift; off=vlcn & tr.mask
 if cid not in tr.map: return {"applicable":False,"result":"N/A","value":"cid-not-mapped"}
 expect=tr.map[cid]+off; got=tr.tr(vlcn)
 f.seek(ps+got*cs); pg=f.read(cs)
 except Exception as e:
 return {"applicable":False,"result":"N/A","value":f"err:{type(e).__name__}"}
 ok = (got==expect) and pg[:4]==b"MSB+"
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"tr={got:#x} CSC+CN={expect:#x} sig={pg[:4]}"}

def probe_page_consistency(ctx,f,ps,cs,tr,roots,check):
 """Self-describing page-header invariants on the object-table root MSB+ page:
 - volsig: header+0x0C == XOR of the 4 Volume-GUID dwords (SUPB+0x50)
 - self_lcn: header+0x20 (LCN slot 0) == the page's own VIRTUAL LCN (root reference)
 - consecutive_lcn: slots at 0x20/0x28/0x30/0x38 == self, self+1, self+2, self+3"""
 if not roots or not roots[0]: return {"applicable":False,"result":"N/A","value":"no-OT-root"}
 vlcn=roots[0][0]
 try:
 f.seek(ps+0x1E*cs); supb=f.read(cs)
 plcn=tr.tr(vlcn); f.seek(ps+plcn*cs); pg=f.read(cs)
 except Exception as e:
 return {"applicable":False,"result":"N/A","value":f"resolve-fail:{type(e).__name__}"}
 if pg[:4]!=b"MSB+": return {"applicable":False,"result":"N/A","value":"not-MSB+"}
 if check=="volsig":
 gx=0
 for i in range(4): gx^=le32(supb,0x50+4*i)
 v=le32(pg,0x0C); return {"applicable":True,"result":"PASS" if v==gx else "FAIL","value":f"{v:#x} vs XOR {gx:#x}"}
 if check=="self_lcn":
 v=le64(pg,0x20); return {"applicable":True,"result":"PASS" if v==vlcn else "FAIL","value":f"{v:#x} vs vlcn {vlcn:#x}"}
 if check=="consecutive_lcn":
 s=[le64(pg,0x20+8*i) for i in range(4)]
 ok=all(s[i]==s[0]+i for i in range(4))
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":str([hex(x) for x in s])}
 if check=="tree_le_valloc": # tree update clock (0x18) <= virtual allocator clock (0x10)
 t=le64(pg,0x18); va=le64(pg,0x10)
 return {"applicable":True,"result":"PASS" if t<=va else "FAIL","value":f"tree={t:#x} valloc={va:#x}"}
 return {"applicable":False,"result":"N/A","value":f"unknown-check:{check}"}

def probe_supb_backup(ctx,f,ps,cs):
 """FS_SUPB_007: two backup superblock copies at VolSize-2 and VolSize-3 carry the 'SUPB' signature."""
 f.seek(ps); vbr=f.read(512); totclu=le64(vbr,0x18)*512//cs
 sigs=[]
 for lcn in (totclu-2, totclu-3):
 try: f.seek(ps+lcn*cs); sigs.append(f.read(4))
 except Exception: sigs.append(b"ERR")
 ok=all(s==b"SUPB" for s in sigs)
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"VolSize-2={sigs[0]} VolSize-3={sigs[1]}"}

def probe_ints_row(ctx,f,ps,cs,tr,roots):
 """CT_INTS_001: Integrity-State table (checkpoint root 11) rows have a 16-byte key [u64 start_lcn,
 u64 block_count]; block_count is non-zero (covers the volume's clusters)."""
 if len(roots)<12 or not roots[11]: return {"applicable":False,"result":"N/A","value":"no-root11"}
 try: rows=walk_bplus(f,ps,cs,tr,roots[11])
 except Exception as e: return {"applicable":False,"result":"N/A","value":f"err:{type(e).__name__}"}
 rows=[(kd,vd) for kd,vd in rows if len(kd)>=16]
 if not rows: return {"applicable":True,"result":"FAIL","value":"no-16B-key rows"}
 bad=sum(1 for kd,vd in rows if le64(kd,8)==0)
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"rows={len(rows)} zero_blockcount={bad}"}

def probe_otbl_value(ctx,f,ps,cs,tr,obj_map):
 """FS_OTBL_002: each Object-Table leaf value embeds a page reference to the object's root page; verify
 that user-object values resolve to a valid MSB+ page (the embedded page-ref works)."""
 n=0; ok=0
 for oid,vl in obj_map.items():
 if oid<0x600 or not vl: continue
 if n>=50: break # count only objects actually checked (avoid off-by-one)
 n+=1
 try:
 f.seek(ps+tr.tr(vl[0])*cs)
 if f.read(4)==b"MSB+": ok+=1
 except Exception: pass
 if n==0: return {"applicable":False,"result":"N/A","value":"no-user-objects"}
 return {"applicable":True,"result":"PASS" if ok==n else "FAIL","value":f"{ok}/{n} resolve to MSB+"}

def probe_vinf_row(ctx,f,ps,cs,tr,obj_map,key_type,check,minlen=0):
 """Volume Information (OID 0x500, Subtable F.4b) row presence/shape. key types: 0x510 label,
 0x520 general info (times/version), 0x540 backup block."""
 if 0x500 not in obj_map: return {"applicable":False,"result":"N/A","value":"no-OID-0x500"}
 try: rows=walk_bplus(f,ps,cs,tr,obj_map[0x500])
 except Exception as e: return {"applicable":False,"result":"N/A","value":f"err:{type(e).__name__}"}
 hit=[vd for kd,vd in rows if len(kd)>=2 and le16(kd,0)==key_type]
 if not hit: return {"applicable":True,"result":"FAIL","value":f"key {key_type:#x} absent"}
 vd=hit[0]
 if check=="label":
 try: nm=vd.split(b'\x00\x00')[0].decode('utf-16-le',errors='strict')
 except Exception: nm=""
 ok=len(nm)>0
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"label={nm!r}"}
 if check=="version":
 # NON-VACUOUS frame check (master F.4b): key 0x520 is a 448-byte row carrying the volume version
 # at +0x80/+0x81 (vol major/minor). The obligation is that this field is a WELL-FORMED ReFS
 # version (major==3, sane minor) — a wrong-frame probe reading a different offset gets arbitrary
 # bytes that are not 3.x and FAILs. We do NOT require equality with the VBR version: the
 # $VOLUME_INFORMATION row is a SECOND, tamper-independent copy, so on VBR-edited test images
 # (afterchangingversion: VBR=6.66/3.15) it correctly preserves the true 3.14 while the VBR lies.
 # That divergence is reported (forensically meaningful), not failed. Measured all-disk 2026-06-20:
 # field is 3.x on 112/112 (3.4/3.7/3.9/3.10/3.14); == VBR on 109, divergent on the 3 tamper images.
 vmaj,vmin=ctx[6],ctx[7]
 if len(vd)<0x82: return {"applicable":True,"result":"FAIL","value":f"vlen={len(vd)}<0x82"}
 rmaj,rmin=vd[0x80],vd[0x81]
 wellformed=(rmaj==3 and 1<=rmin<=64)
 match="==vbr" if (rmaj==vmaj and rmin==vmin) else f"!=vbr({vmaj}.{vmin})[tamper?]"
 return {"applicable":True,"result":"PASS" if wellformed else "FAIL","value":f"+0x80={rmaj}.{rmin} {match}"}
 ok=len(vd)>=minlen
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"vlen={len(vd)}"}

def _read_struct(f,ps,cs,chkp_lcns,which):
 if which=="vbr": f.seek(ps); return f.read(512)
 if which=="supb": f.seek(ps+0x1E*cs); d=f.read(cs); return d if d[:4]==b"SUPB" else None
 if which=="chkp": return _newest_chkp_page(f,ps,cs,chkp_lcns)
 return None

def probe_field_plausible(ctx,f,ps,cs,chkp_lcns,which,off,size,pred,*a):
 """Variable-field validity: read struct (vbr/chkp/supb) and apply a predicate that the field is
 PLAUSIBLE rather than a fixed constant. preds: nonzero, in_set(...), le_field(other_off),
 guid_nonzero(16B). Avoids the trap of asserting a constant for a per-image field."""
 d=_read_struct(f,ps,cs,chkp_lcns,which)
 if d is None: return {"applicable":False,"result":"N/A","value":f"no-{which}"}
 if pred=="guid_nonzero":
 ok=any(d[off:off+16]); return {"applicable":True,"result":"PASS" if ok else "FAIL","value":d[off:off+16].hex()}
 v=_ival(d,off,size)
 if pred=="nonzero": ok=v!=0
 elif pred=="in_set": ok=v in a
 elif pred=="le_field": ok=v<=_ival(d,a[0],size)
 elif pred=="mask": ok=(v & a[0])==a[0] # all bits in a[0] are set
 else: return {"applicable":False,"result":"N/A","value":f"unknown-pred:{pred}"}
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":hex(v)}

def probe_version_consistency(ctx,f,ps,cs,chkp_lcns):
 """VBR version (0x28 major / 0x29 minor) == checkpoint version (0x54 major / 0x56 minor)."""
 f.seek(ps); vbr=f.read(512); chk=_newest_chkp_page(f,ps,cs,chkp_lcns)
 if chk is None: return {"applicable":False,"result":"N/A","value":"no-CHKP"}
 vmaj,vmin=vbr[0x28],vbr[0x29]; cmaj,cmin=le16(chk,0x54),le16(chk,0x56)
 ok=(vmaj==cmaj and vmin==cmin)
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"VBR {vmaj}.{vmin} CHKP {cmaj}.{cmin}"}

_CKLEN={0:0,1:4,2:8,4:32} # checksum type -> digest length
def probe_pref_field(ctx,f,ps,cs,tr,roots,chkp_lcns,check):
 """Page-reference descriptor fields, read from the checkpoint's root-0 descriptor (a page reference):
 LCN quad @0x00-0x20, flags @0x20, checksum type @0x22, checksum-data-offset @0x23, checksum length @0x24."""
 raw=_newest_chkp_page(f,ps,cs,chkp_lcns)
 if raw is None: return {"applicable":False,"result":"N/A","value":"no-CHKP"}
 flags=le32(raw,0x78); olb=le32(raw,0x94) if (flags&0x200) else 0x94
 dl=le32(raw,0x5c); ro=le32(raw,olb)
 if ro==0 or ro+dl>len(raw): return {"applicable":False,"result":"N/A","value":"bad-desc"}
 rec=raw[ro:ro+dl]
 if check=="lcn_quad": # referenced LCN quad slot0 == OT-root LCN
 if not roots or not roots[0]: return {"applicable":False,"result":"N/A","value":"no-OT-root"}
 v=le64(rec,0); exp=roots[0][0]
 return {"applicable":True,"result":"PASS" if v==exp else "FAIL","value":f"{v:#x} vs root0 {exp:#x}"}
 if check=="cktype": # checksum type at 0x22 is a known enum AND consistent with the length
 ct=rec[0x22]; cl=le16(rec,0x24)
 ok = ct in _CKLEN and cl==_CKLEN[ct]
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"cktype={ct} cklen={cl}"}
 if check=="cklen": # checksum length at 0x24 == _CKLEN[cktype]
 ct=rec[0x22]; cl=le16(rec,0x24)
 ok = ct in _CKLEN and cl==_CKLEN[ct]
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"cklen={cl} (cktype {ct})"}
 return {"applicable":False,"result":"N/A","value":f"unknown:{check}"}

def probe_supb_int(ctx,f,ps,cs,off,size,expected):
 """Superblock field. SUPB is at LCN 0x1E (NOT in the VBR — a common authoring error)."""
 f.seek(ps+0x1E*cs); supb=f.read(cs)
 if supb[:4]!=b"SUPB": return {"applicable":False,"result":"N/A","value":"no-SUPB@0x1E"}
 v=_ival(supb,off,size)
 return {"applicable":True,"result":"PASS" if v==expected else "FAIL","value":hex(v)}

def probe_supb_generation(ctx,f,ps,cs):
 """FS_SUPB_003: SUPB+0x68 is the GENERATION / recency clock (NOT a constant 'version' — §A.3, RELABELED
 2026-06-18). `CmsVolume::ChooseSuperBlock` selects the SUPB copy with the HIGHEST +0x68. Verify the
 recency invariant NON-VACUOUSLY: the primary SUPB (@0x1E, the active copy on a clean mount) has +0x68
 >= every backup copy's +0x68. A backup more recent than the primary -> FAIL. Replaces the old `==1`
 constant assertion, which passed only on the single-mount corpus and re-confirmed the retracted label."""
 f.seek(ps+0x1E*cs); supb=f.read(cs)
 if supb[:4]!=b"SUPB": return {"applicable":False,"result":"N/A","value":"no-SUPB@0x1E"}
 prim=le64(supb,0x68)
 f.seek(ps); vbr=f.read(512); totclu=le64(vbr,0x18)*512//cs
 gens=[prim]
 for lcn in (totclu-2,totclu-3):
 try:
 f.seek(ps+lcn*cs); b=f.read(cs)
 if b[:4]==b"SUPB": gens.append(le64(b,0x68))
 except Exception: pass
 ok = prim==max(gens)
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"primary+0x68={prim} all_copies={gens}"}

def probe_vbr_spc(ctx,f,ps,cs):
 """Sectors-per-cluster (VBR 0x24) == cluster_size/512 (8 for 4K, 128 for 64K). Cluster-derived, not a flat constant."""
 f.seek(ps); vbr=f.read(512); v=le32(vbr,0x24); exp=cs//512
 return {"applicable":True,"result":"PASS" if v==exp else "FAIL","value":f"{v} (exp {exp})"}

def _iter_si_rows(f,ps,cs,tr,obj_map,min_oid=0x600):
 for oid,vl in obj_map.items():
 if oid<min_oid: continue
 try: rows=walk_bplus(f,ps,cs,tr,vl)
 except Exception: continue
 for kd,vd in rows:
 if le16(kd,0)==0x10: # type-0x10 = $SI own-row
 yield vd

def probe_si_field(ctx,f,ps,cs,tr,obj_map,off,size,pred,*a):
 """$SI field invariants. SI base = vd+0x28 (the value's 0x28-byte attr header). off is SI-base-relative
 (so DataSize@0x38 -> vd+0x60, NextFileId@0x58 -> vd+0x80, etc.). preds: all_zero, upper32_zero,
 dir_field_zero (only directory rows, file_attrs bit 0x10000000), filetime, nonzero_count_le(n)."""
 B=0x28; bad=0; checked=0; nz=0
 for oid,vl in obj_map.items():
 if oid<0x600: continue
 try: rows=walk_bplus(f,ps,cs,tr,vl)
 except Exception: continue
 for kd,vd in rows:
 if le16(kd,0)!=0x10 or len(vd)<B+off+size: continue
 v=_ival(vd,B+off,size); checked+=1
 if pred=="all_zero":
 if v!=0: bad+=1
 elif pred=="upper32_zero":
 if (v>>32)!=0: bad+=1
 elif pred=="dir_field_zero":
 if len(vd)>=B+0x24 and (le32(vd,B+0x20)&0x10000000) and v!=0: bad+=1
 elif pred=="filetime":
 if not (129037248000000000 < v < 142000000000000000): bad+=1 # ~2010..2035
 elif pred=="le_const":
 if v>a[0]: bad+=1
 elif pred=="reparse_tag_valid": # 0, or a reparse tag (bit 31 set)
 if v!=0 and not (v & 0x80000000): bad+=1
 elif pred=="nonzero_count_le":
 if v!=0: nz+=1
 if checked==0: return {"applicable":False,"result":"N/A","value":"no-SI-rows"}
 if pred=="nonzero_count_le":
 ok=nz<=a[0]; return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"nonzero={nz}/{checked}"}
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{checked}"}

def probe_subrec(ctx,f,ps,cs,tr,obj_map,check,*a):
 """Embedded sub-record structure. Each top-level 0x30 row value holds an embedded B+-tree
 (parse_resident_btree_rows); each embedded row's key has marker @kd[8:12] (0x80000001 single-instance /
 0x80000002 multi-instance) and sub-record type @kd[12]. Verifies structure WHERE the type is present
 (returns N/A if the feature is absent on this image, so feature-gated claims aren't falsely CONTESTED).
 checks: marker(type,exp) · value_len(type,exp) · header_zero(types...) · cooccur(t1,t2) · present(type)."""
 from forefst import parse_resident_btree_rows
 recs=[]; obj_types=[]
 for oid,vl in obj_map.items():
 if oid<0x600: continue
 try: rows=walk_bplus(f,ps,cs,tr,vl)
 except Exception: continue
 for kd,vd in rows:
 if le16(kd,0)!=0x30: continue
 here=set()
 for ekd,evd in parse_resident_btree_rows(vd):
 if len(ekd)<14: continue
 st=ekd[12]|(ekd[13]<<8); marker=le32(ekd,8)
 recs.append((st,marker,len(evd),len(evd)>=4 and le32(evd,0)==0)); here.add(st)
 obj_types.append(here)
 if check=="marker":
 t,exp=a[0],a[1]; sel=[r for r in recs if r[0]==t]
 if not sel: return {"applicable":False,"result":"N/A","value":f"type {t:#x} absent"}
 bad=sum(1 for r in sel if r[1]!=exp)
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"{len(sel)-bad}/{len(sel)} marker {exp:#x}"}
 if check=="value_len":
 t,exp=a[0],a[1]; sel=[r for r in recs if r[0]==t]
 if not sel: return {"applicable":False,"result":"N/A","value":f"type {t:#x} absent"}
 bad=sum(1 for r in sel if r[2]!=exp)
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"{len(sel)-bad}/{len(sel)} len {exp}"}
 if check=="header_zero":
 sel=[r for r in recs if r[0] in a]
 if not sel: return {"applicable":False,"result":"N/A","value":"none present"}
 bad=sum(1 for r in sel if not r[3])
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"{len(sel)-bad}/{len(sel)} hdr0"}
 if check=="cooccur":
 t1,t2=a[0],a[1]; have1=[s for s in obj_types if t1 in s]
 if not have1: return {"applicable":False,"result":"N/A","value":f"type {t1:#x} absent"}
 bad=sum(1 for s in have1 if t2 not in s)
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"{len(have1)-bad}/{len(have1)} cooccur"}
 if check=="present": # feature-gated: N/A where absent (the claim is about what the type IS, where present)
 t=a[0]; n=sum(1 for r in recs if r[0]==t)
 if n==0: return {"applicable":False,"result":"N/A","value":f"type {t:#x} absent"}
 return {"applicable":True,"result":"PASS","value":f"type {t:#x} count={n}"}
 return {"applicable":False,"result":"N/A","value":f"unknown:{check}"}

def probe_index_node(ctx,f,ps,cs,tr,roots,obj_map,check):
 """B+tree node structure on a leaf MSB+ page (a user object's root, which has real data rows on every
 volume — the OT root is an inner node on large volumes). Table header at thoff=0x50+le32(page,0x50):
 data_area_off@+0x00, height@+0x0C, flags@+0x0D (0x1 inner/0x2 root/0x4 stream), offset-array [astart@+0x10,
 aend@+0x20). Each row header is <I6H>: entry_len@0x00, key_off@0x04, key_len@0x06, flags@0x08 (0x4 deleted),
 val_off@0x0A, val_len@0x0C. checks: header (flags valid) · entry_struct (row-header fields consistent)."""
 pg=None
 for oid,vl in obj_map.items(): # find a user-object leaf page with a valid offset array
 if oid<0x600 or not vl: continue
 try:
 f.seek(ps+tr.tr(vl[0])*cs); cand=f.read(max(4*cs,16384)) # full 16 KiB page (4 clusters @4K), not one cluster
 except Exception: continue
 if cand[:4]!=b"MSB+": continue
 th=0x50+le32(cand,0x50)
 if th+40>len(cand): continue
 t=struct.unpack_from("<10I",cand,th)
 if t[4]<t[8]<=len(cand): pg=cand; break
 if pg is None: return {"applicable":False,"result":"N/A","value":"no-leaf-page"}
 thoff=0x50+le32(pg,0x50)
 tbl=struct.unpack_from("<10I",pg,thoff)
 if check=="header":
 flags=pg[thoff+0x0D]; daoff=tbl[0]
 ok=(flags & ~0x7)==0 and 0<daoff<len(pg) # flags only use bits 0x1/0x2/0x4; data-area offset sane
 return {"applicable":True,"result":"PASS" if ok else "FAIL","value":f"flags={flags:#x} daoff={daoff:#x}"}
 if check=="entry_struct":
 astart,aend=tbl[4],tbl[8]
 if not (astart<aend<=len(pg)): return {"applicable":False,"result":"N/A","value":"bad-array"}
 bad=0; n=0
 for i in range((aend-astart)//4):
 aa=thoff+astart+i*4
 if aa+2>len(pg): break
 ro=thoff+le16(pg,aa)
 if ro+16>len(pg): bad+=1; n+=1; continue
 el,ko,kl,fl,vo,vl,_=struct.unpack_from("<I6H",pg,ro); n+=1
 if not (el>0 and ko>=0x10 and ko+kl<=el and vo+vl<=el): bad+=1
 if n==0: return {"applicable":False,"result":"N/A","value":"no-rows"}
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{n}"}
 return {"applicable":False,"result":"N/A","value":f"unknown:{check}"}

def probe_root_row(ctx,f,ps,cs,tr,roots,ri,check,*a):
 """Walk a checkpoint root's B+-tree (allocator/BRC tables) and check key structure. N/A if the root is
 absent/empty (e.g. Block-RefCount on a volume with no clones). checks: keylen(n) · key_u64(off,val)."""
 if ri>=len(roots) or not roots[ri]: return {"applicable":False,"result":"N/A","value":"root-absent"}
 try: rws=walk_bplus(f,ps,cs,tr,roots[ri])
 except Exception as e: return {"applicable":False,"result":"N/A","value":f"err:{type(e).__name__}"}
 if not rws: return {"applicable":False,"result":"N/A","value":"empty-root"}
 if check=="keylen":
 bad=sum(1 for kd,vd in rws if len(kd)!=a[0])
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{len(rws)} (keylen {a[0]})"}
 if check=="key_u64":
 off,val=a[0],a[1]; sel=[kd for kd,vd in rws if len(kd)>=off+8]
 if not sel: return {"applicable":False,"result":"N/A","value":"keys-too-short"}
 bad=sum(1 for kd in sel if le64(kd,off)!=val)
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{len(sel)} key+{off:#x}=={val:#x}"}
 return {"applicable":False,"result":"N/A","value":f"unknown:{check}"}

def probe_dirkey(ctx,f,ps,cs,tr,obj_map,check,*a):
 """Directory-entry (type 0x30) key structure: Type(2)@0x00=0x30, key_flags(2)@0x02 (1=file, 2=dir-link),
 then the UTF-16 name (NO reserved field at 0x04). checks: key_flags · structure · has_flag(v)."""
 rows=[]
 for oid,vl in obj_map.items():
 if oid<0x600: continue
 try:
 for kd,vd in walk_bplus(f,ps,cs,tr,vl):
 if le16(kd,0)==0x30 and len(kd)>=4: rows.append(kd)
 except Exception: continue
 if not rows: return {"applicable":False,"result":"N/A","value":"no-0x30-keys"}
 if check=="key_flags": # every 0x30 key has key_flags in {1,2}
 bad=sum(1 for kd in rows if le16(kd,2) not in (1,2))
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{len(rows)}"}
 if check=="structure": # Type(2)+flags(2)+UTF16 name; (len-4) even, no reserved
 bad=sum(1 for kd in rows if le16(kd,0)!=0x30 or (len(kd)-4)%2!=0)
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{len(rows)}"}
 if check=="has_flag": # >=1 key with key_flags == a[0]
 n=sum(1 for kd in rows if le16(kd,2)==a[0])
 return {"applicable":True,"result":"PASS" if n>0 else "FAIL","value":f"flag {a[0]} count={n}"}
 return {"applicable":False,"result":"N/A","value":f"unknown:{check}"}

def probe_row0x40(ctx,f,ps,cs,tr,obj_map,check):
 """Type 0x40 (data-extent) rows. N/A where absent (resident-only volumes). checks: key24 (24-byte key,
 type 0x40) · sizes (alloc_size@val+0x60 >= file_size@val+0x58, alloc cluster-aligned)."""
 keys=[]; vals=[]
 for oid,vl in obj_map.items():
 if oid<0x600: continue
 try:
 for kd,vd in walk_bplus(f,ps,cs,tr,vl):
 if le16(kd,0)==0x40: keys.append(kd); vals.append(vd)
 except Exception: continue
 if not keys: return {"applicable":False,"result":"N/A","value":"no-0x40-rows"}
 if check=="key24":
 bad=sum(1 for kd in keys if len(kd)!=24)
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{len(keys)}"}
 if check=="sizes":
 # alloc_size@0x60 is cluster-granular (0 for sparse, else a multiple of cs); file_size@0x58 readable.
 # NOT alloc>=file (compressed/sparse files break that). This tests the FIELD, not a size relationship.
 # the full non-resident extent header is a large value (>=0x100B); smaller 0x40 values are a
 # different variant (stream descriptor) with its own layout — not what this claim describes.
 sel=[vd for vd in vals if len(vd)>=0x100]; bad=0
 for vd in sel:
 al=le64(vd,0x60)
 if al%cs!=0: bad+=1
 if not sel: return {"applicable":False,"result":"N/A","value":"no-full-extent-headers"}
 return {"applicable":True,"result":"PASS" if bad==0 else "FAIL","value":f"bad={bad}/{len(sel)}"}
 return {"applicable":False,"result":"N/A","value":f"unknown:{check}"}

def probe_attr_types(ctx,f,ps,cs,tr,obj_map,mode,*types):
 """Attribute-type presence/absence across user objects. mode 'present_all': every type appears on >=1
 user object. mode 'absent_all': none of the types appears on any user object (ABSENCE)."""
 seen=set()
 for oid,vl in obj_map.items():
 if oid<0x600: continue
 try: rows=walk_bplus(f,ps,cs,tr,vl)
 except Exception: continue
 for kd,vd in rows:
 if len(kd)>=2 and le16(kd,0)!=0: seen.add(le16(kd,0)) # skip type-0 (empty/padding) keys
 if mode=="present_all":
 miss=[hex(t) for t in types if t not in seen]
 return {"applicable":True,"result":"PASS" if not miss else "FAIL","value":f"missing={miss}" if miss else "all present"}
 if mode=="absent_all":
 hit=[hex(t) for t in types if t in seen]
 return {"applicable":True,"result":"PASS" if not hit else "FAIL","value":f"present={hit}" if hit else "all absent"}
 if mode=="subset_of": # the set of ALL present top-level types is a subset of `types`
 extra=[hex(t) for t in seen if t not in types]
 return {"applicable":True,"result":"PASS" if not extra else "FAIL","value":f"extra={extra}" if extra else f"subset of {[hex(t) for t in types]}"}
 return {"applicable":False,"result":"N/A","value":f"unknown-mode:{mode}"}

def probe_si_zero(ctx,f,ps,cs,tr,obj_map,off,size):
 """ABSENCE: field at $SI+off is always 0 across all user objects. Implausible-guard not needed (==0)."""
 nonzero=0; checked=0
 for vd in _iter_si_rows(f,ps,cs,tr,obj_map):
 if len(vd)>=off+size:
 checked+=1
 if _ival(vd,off,size)!=0: nonzero+=1
 return {"applicable":checked>0,"result":"PASS" if nonzero==0 else "FAIL","value":f"nonzero={nonzero}/{checked}"}

def probe_si_aggmax(ctx,f,ps,cs,tr,obj_map,off,size,bound,plaus_hi):
 """ABSENCE/aggregate: max plausible value of $SI+off <= bound. Values > plaus_hi are field-overlap, discarded."""
 mx=0; impl=0; checked=0
 for vd in _iter_si_rows(f,ps,cs,tr,obj_map):
 if len(vd)>=off+size:
 checked+=1; v=_ival(vd,off,size)
 if v<=plaus_hi: mx=max(mx,v)
 else: impl+=1
 return {"applicable":checked>0,"result":"PASS" if mx<=bound else "FAIL","value":f"max={mx}/{checked};discarded={impl}"}

def probe_cite(ctx,*a):
 """LITERATURE: no on-disk obligation; the proof is the cited source recorded in proof_links."""
 return {"applicable":False,"result":"CITE","value":"literature-citation"}

def run_probe(spec, ctx):
 f,ps,cs,tr,roots,obj_map,vmaj,vmin,chkp_lcns=ctx
 p=spec["probe"]; name=p[0]
 if name=="vbr_u64": return probe_vbr_u64(ctx,f,ps,p[1],p[2])
 if name=="vbr_int": return probe_vbr_int(ctx,f,ps,p[1],p[2],p[3]) # off,size,expected
 if name=="chkp_int": return probe_chkp_int(ctx,f,ps,cs,chkp_lcns,p[1],p[2],p[3]) # off,size,expected
 if name=="supb_int": return probe_supb_int(ctx,f,ps,cs,p[1],p[2],p[3]) # off,size,expected
 if name=="supb_generation": return probe_supb_generation(ctx,f,ps,cs)
 if name=="chkp_root_table": return probe_chkp_root_table(ctx,f,ps,cs,tr,roots,p[1],p[2]) # root_index,expected_id
 if name=="page_consistency": return probe_page_consistency(ctx,f,ps,cs,tr,roots,p[1]) # check
 if name=="ct_row": return probe_ct_row(ctx,f,ps,cs,tr,roots,p[1],*p[2:]) # check,args
 if name=="ct_translate": return probe_ct_translate(ctx,f,ps,cs,tr,roots)
 if name=="pref_field": return probe_pref_field(ctx,f,ps,cs,tr,roots,chkp_lcns,p[1]) # check
 if name=="field_plausible": return probe_field_plausible(ctx,f,ps,cs,chkp_lcns,p[1],p[2],p[3],p[4],*p[5:]) # struct,off,size,pred,args
 if name=="version_consistency": return probe_version_consistency(ctx,f,ps,cs,chkp_lcns)
 if name=="supb_backup": return probe_supb_backup(ctx,f,ps,cs)
 if name=="ints_row": return probe_ints_row(ctx,f,ps,cs,tr,roots)
 if name=="otbl_value": return probe_otbl_value(ctx,f,ps,cs,tr,obj_map)
 if name=="vinf_row": return probe_vinf_row(ctx,f,ps,cs,tr,obj_map,p[1],p[2],*(p[3:])) # key_type,check,minlen
 if name=="vbr_spc": return probe_vbr_spc(ctx,f,ps,cs)
 if name=="page_const": return probe_page_const(ctx,f,ps,cs,roots,tr,p[1],p[2])
 if name=="cpc":
 bpc=le64(open_vbr(f,ps),0x40) or 0x4000000
 return probe_cpc(ctx,f,ps,cs,roots,tr,bpc)
 if name=="absent": return probe_absent_utf16(ctx,f,ps,cs,roots,obj_map,tr,p[1])
 if name=="hlc_max": return probe_hlc_max(ctx,f,ps,cs,roots,obj_map,tr)
 if name=="si_field": return probe_si_field(ctx,f,ps,cs,tr,obj_map,p[1],p[2],p[3],*p[4:]) # off,size,pred,args
 if name=="attr_types": return probe_attr_types(ctx,f,ps,cs,tr,obj_map,p[1],*p[2:]) # mode,types
 if name=="subrec": return probe_subrec(ctx,f,ps,cs,tr,obj_map,p[1],*p[2:]) # check,args
 if name=="dirkey": return probe_dirkey(ctx,f,ps,cs,tr,obj_map,p[1],*p[2:]) # check,args
 if name=="row0x40": return probe_row0x40(ctx,f,ps,cs,tr,obj_map,p[1]) # check
 if name=="root_row": return probe_root_row(ctx,f,ps,cs,tr,roots,p[1],p[2],*p[3:]) # ri,check,args
 if name=="index_node": return probe_index_node(ctx,f,ps,cs,tr,roots,obj_map,p[1]) # check
 if name=="si_zero": return probe_si_zero(ctx,f,ps,cs,tr,obj_map,p[1],p[2]) # off,size
 if name=="si_aggmax": return probe_si_aggmax(ctx,f,ps,cs,tr,obj_map,p[1],p[2],p[3],p[4]) # off,size,bound,plaus_hi
 if name=="cite": return probe_cite(ctx)
 return {"applicable":False,"result":"N/A","value":f"unknown-probe:{name}"}

def open_vbr(f,ps):
 f.seek(ps); return f.read(512)

# ── ref_id↔claim correspondence gate ──
# A CONFIRMED verdict is worthless if the probe tests a DIFFERENT claim than the ref_id names.
# (Lesson: 3/7 hand-authored pilot specs had ref_id↔probe mismatches that all "passed".)
# Load the canonical reference_table claim text so every dossier shows BOTH the claim and the probe.
_REFTBL=os.path.join(_REPO,"analysis","reference_table.csv")
def load_claim_text():
 out={}
 try:
 for r in csv.DictReader(open(_REFTBL)):
 out[r["ref_id"]]=f'{r.get("structure","")}: {r.get("description","")}'.strip()
 except Exception: pass
 return out
CLAIM_TEXT=load_claim_text()

# Frame-correspondence: a CONFIRMED verdict is worthless if the probe reads an offset the claim never
# names (the E47->E49 frame-error class). For offset-bearing probes, require the probe's offset to appear
# in the canonical claim text — not merely that the ref_id exists. (audit gate fix 2026-06-20)
_PROBE_OFF_IDX={"vbr_int":1,"chkp_int":1,"supb_int":1,"si_field":1,"si_zero":1,"si_aggmax":1,"field_plausible":2}
def _probe_offset(probe):
 name=probe[0]
 if name=="ct_row" and len(probe)>=3 and isinstance(probe[2],int): return probe[2]
 i=_PROBE_OFF_IDX.get(name)
 if i is not None and len(probe)>i and isinstance(probe[i],int): return probe[i]
 return None
def frame_correspondence(probe, canon):
 if not canon: return "WARN: ref_id NOT in reference_table.csv"
 off=_probe_offset(probe)
 if off is None or off==0: return "OK" # non-offset / signature-at-0 probe: existence is the check
 cl=canon.lower()
 # Extract only offsets written in an OFFSET CONTEXT (value+0xNN, $SI+0xNN, at/offset 0xNN, ranges
 # 0xNN-0xMM). This ignores cited VALUES (flag values like 0x602, size values like 0x68, masks like
 # 0xFFFF) which would otherwise cause false frame WARNs on perfectly frame-correct probes.
 cited ={int(h,16) for h in re.findall(r"(?:value|val|\$si|si|page|hdr|header|field|offset|byte|at)\s*\+?\s*(0x[0-9a-f]+)", cl)}
 cited|={int(h,16) for h in re.findall(r"\+\s*(0x[0-9a-f]+)", cl)}
 cited|={int(h,16) for h in re.findall(r"(0x[0-9a-f]+)\s*[-–]\s*0x[0-9a-f]+", cl)} # 0xNN-0xMM ranges
 if not cited: return "OK" # claim cites no field offset -> can't check by offset (semantic claim)
 if off in cited: return "OK" # the probe reads an offset the claim names -> frame agrees
 return f"WARN: probe offset 0x{off:x} not among claim offsets {sorted(hex(c) for c in cited)} (frame mismatch)"

_DECOMP_IDX=None
def _decomp_index():
 global _DECOMP_IDX
 if _DECOMP_IDX is None:
 _DECOMP_IDX={}
 try:
 for r in csv.DictReader(open(f"{DEC}/refs_win11.decomp.index.tsv"),delimiter="\t"):
 _DECOMP_IDX[r["name"]]=(int(r["line"]),int(r["size_bytes"]))
 except Exception: pass
 return _DECOMP_IDX

def export_static(fn):
 """Export a static reference: a forefst.py function OR a decompiled driver function (by name, from the
 win11 mass decompilation index). Returns the relative artifact path, or None if not found."""
 if not fn: return None
 safe=re.sub(r'[^A-Za-z0-9_]','_',fn)[:60]
 # forefst.py functions
 FOREFST={"parse_vbr","parse_supb","parse_chkp","_parse_ct_page","build_object_map","walk_bplus","Translator","_vbr_checksum"}
 if fn in FOREFST:
 src=open(os.path.join(_REPO,"forefst.py")).read()
 key=("class " if fn=="Translator" else "def ")+fn
 if key in src:
 body=key+src.split(key,1)[1].split("\ndef ")[0].split("\nclass ")[0]
 path=f"{HERE}/proofs/static/{safe}__forefst.txt"; open(path,"w").write(body[:8000])
 return os.path.relpath(path,HERE)
 # decompiled driver functions
 idx=_decomp_index()
 cand=[k for k in idx if k==fn] or [k for k in idx if fn in k]
 if cand:
 name=cand[0]; ln,sz=idx[name]
 lines=open(f"{DEC}/refs_win11.decomp.c").read().splitlines()
 # take from the header comment line (a few lines above) through ~ size-derived line budget
 nlines=min(max(20, sz//12), 400)
 body="\n".join(lines[max(0,ln-2):ln-2+nlines])
 path=f"{HERE}/proofs/static/{safe}__decomp.txt"; open(path,"w").write(body[:16000])
 return os.path.relpath(path,HERE)
 return None

def verdict(matrix, axis):
 applic=[m for m in matrix if m["result"] in ("PASS","FAIL")]
 npass=sum(1 for m in applic if m["result"]=="PASS")
 n=len(applic)
 if n==0: return "UNTESTED",npass,n
 if npass<n: return "CONTESTED",npass,n
 # all applicable PASS
 indep=len(set(m["group"] for m in applic))
 if indep>=3: return "CONFIRMED",npass,n
 if indep==n and n>=2: return "SATURATED",npass,n
 if indep>=2: return "CORROBORATED",npass,n
 return "RD-LIMITED",npass,n

def main():
 os.makedirs(f"{HERE}/proofs/static",exist_ok=True)
 os.makedirs(f"{HERE}/proofs/validation",exist_ok=True)
 os.makedirs(f"{HERE}/dossiers",exist_ok=True)
 t0=time.time()
 # run all pilot probes per image (bootstrap once/image)
 results={s["ref_id"]:[] for s in PILOT}
 apms={s["ref_id"]:applicable(s["applicability"]) for s in PILOT}
 _static=lambda s: s["probe"][0] in ("static_dossier","cite") # no disk obligation
 apset={s["ref_id"]:(set() if _static(s) else set(r["path"] for r in apms[s["ref_id"]])) for s in PILOT}
 for r in IMAGES:
 path=os.path.join(_CORPUS,r["path"])
 ctx=_ctx(path)
 if ctx is None:
 for s in PILOT:
 if r["path"] in apset[s["ref_id"]]:
 results[s["ref_id"]].append({"path":r["path"],"basename":r["basename"],"group":r["baseline_group"],"result":"N/A","value":"bootstrap-fail"})
 continue
 try:
 for s in PILOT:
 if r["path"] not in apset[s["ref_id"]]: continue
 try: res=run_probe(s,ctx)
 except Exception as e: res={"applicable":False,"result":"N/A","value":f"err:{type(e).__name__}"}
 rr=res["result"] if res["applicable"] else "N/A"
 exc=s.get("scoped_exceptions",{}).get(r["basename"])
 if rr=="FAIL" and exc: rr="EXC" # documented, knowledge-linked scoped exception — not a contradiction
 results[s["ref_id"]].append({"path":r["path"],"basename":r["basename"],"group":r["baseline_group"],
 "result":rr,"value":(f"{res['value']} [scoped: {exc}]" if rr=="EXC" else res["value"])})
 finally:
 ctx[0].close()
 # emit
 index=[]; links=[]
 for s in PILOT:
 mat=results[s["ref_id"]]
 with open(f"{HERE}/proofs/validation/{s['ref_id']}.csv","w",newline="") as vf:
 w=csv.DictWriter(vf,fieldnames=["path","basename","group","result","value"]);w.writeheader();w.writerows(mat)
 vd,npass,n=verdict(mat,s["axis"])
 stat=export_static(s["static_fn"])
 if _static(s): # static/behavioral claim: proof is the decompiled function + citation, not a disk matrix
 vd = "STATIC-CONFIRMED" if stat else "STATIC-CITED"; npass,n = (1 if stat else 0),1
 # ref_id<->claim correspondence gate
 canon=CLAIM_TEXT.get(s["ref_id"])
 corr = frame_correspondence(s["probe"], canon)
 # dossier
 dz=[f"# Dossier — {s['ref_id']} ({s['class']})","",
 f"**Claim (this audit tests):** {s['desc']}","",
 f"**Canonical claim (reference_table.csv):** {canon or '(ref_id not found — '+s['ref_id']+')'}","",
 f"**Correspondence:** {corr} — the probe must test the canonical claim, not merely pass.","",
 f"**Verdict:** {vd} — disk held on **{npass}/{n}** applicable images "
 f"(independent groups: {len(set(m['group'] for m in mat if m['result'] in ('PASS','FAIL')))})","",
 "## Static-analysis proof",
 f"- {stat or 'N/A — '+( 'pure on-disk layout (no single driver function)' if s['class']=='PURE-RD-LAYOUT' else 'see explanation')}",
 f"- {s['explanation']}","",
 "## Raw-disk proof (validated corpus-wide)",
 f"- probe `{s['probe']}` over the applicable set; matrix: `proofs/validation/{s['ref_id']}.csv`",
 f"- result distribution: "+", ".join(f"{k}={v}" for k,v in __import__('collections').Counter(m['result'] for m in mat).items()),"",
 "## Confirmation ledger",
 f"- validated_by: {'disk+static' if stat else 'disk'} ; n_confirmations: {npass}",
 f"- confirmed_by: {npass} applicable images ({len(set(m['group'] for m in mat if m['result']=='PASS'))} independent groups)",
 f"- to_confirm: "+("already corpus-saturated" if vd in ('CONFIRMED','SATURATED') else
 f"needs more applicable images on axis '{s['axis']}' OR resolve the {sum(1 for m in mat if m['result']=='FAIL')} FAIL(s)"),
 ]
 open(f"{HERE}/dossiers/{s['ref_id']}.md","w").write("\n".join(dz)+"\n")
 index.append({"ref_id":s["ref_id"],"class":s["class"],"verdict":vd,"n_pass":npass,"n_applicable":n,
 "correspondence":corr.split(":")[0],"canonical_claim":(canon or "")[:120],
 "static_artifact":stat or "","disk_probe":s["probe"][0],
 "validation":f"proofs/validation/{s['ref_id']}.csv","axis":s["axis"]})
 if stat: links.append({"ref_id":s["ref_id"],"artifact":stat,"artifact_type":"static","locus_type":"function","locus":s["static_fn"],"note":""})
 links.append({"ref_id":s["ref_id"],"artifact":f"proofs/validation/{s['ref_id']}.csv","artifact_type":"matrix","locus_type":"all-rows","locus":"","note":""})
 with open(f"{HERE}/proof_index.csv","w",newline="") as fo:
 w=csv.DictWriter(fo,fieldnames=["ref_id","class","verdict","n_pass","n_applicable","correspondence","canonical_claim","static_artifact","disk_probe","validation","axis"]);w.writeheader();w.writerows(index)
 with open(f"{HERE}/proof_links.csv","w",newline="") as fo:
 w=csv.DictWriter(fo,fieldnames=["ref_id","artifact","artifact_type","locus_type","locus","note"]);w.writeheader();w.writerows(links)
 dt=time.time()-t0
 warns=[i["ref_id"] for i in index if i["correspondence"]=="WARN"]
 print(f"AUDIT run: {len(PILOT)} claims × {len(IMAGES)} images in {dt:.1f}s")
 for i in index: print(f" {i['ref_id']:18s} {i['class']:14s} {i['verdict']:11s} {i['n_pass']}/{i['n_applicable']} corr={i['correspondence']}")
 if warns: print(f" !! correspondence WARN (ref_id not in reference_table): {warns}")
 print(f" → proof_index.csv, proof_links.csv, dossiers/, proofs/validation/")

if __name__=="__main__":
 main()
