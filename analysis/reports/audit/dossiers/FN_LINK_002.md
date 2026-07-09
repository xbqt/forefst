# Dossier — FN_LINK_002 (STRUCTURAL)

**Claim (this audit tests):** Hard-link mechanism (v3.14): each name = a separate type-0x30 non-resident dir entry (key_flags 0x02, 84B value). value+0x00 = per-directory child ordinal (= NextFileId $SI+0x58), shared by one file's names but NOT a globally-unique FileId (reused per directory, collides across sibling dirs under a shared home). value+0x08 = home-dir backref OID (the directory the file was first created in, #327). No explicit on-disk HardLinkCount; link count = number of entries sharing (home backref, ordinal, size, created, modified). $SI+0x70 'HardLinkCount' is a resident-layout field, always 1. Supersedes the retracted '110 true hard links' artifact (#292/E33).

**Canonical claim (reference_table.csv):** File Name: Hard-link mechanism (v3.14): each name = a separate type-0x30 non-resident dir entry (key_flags 0x02, 84B value). value+0x00 = per-directory child ordinal (= NextFileId $SI+0x58), shared by one file's names but NOT a globally-unique FileId (reused per directory, collides across sibling dirs under a shared home). value+0x08 = home-dir backref OID (the directory the file was first created in, #327). No explicit on-disk HardLinkCount; link count = number of entries sharing (home backref, ordinal, size, created, modified). $SI+0x70 'HardLinkCount' is a resident-layout field, always 1. Supersedes the retracted '110 true hard links' artifact (#292/E33).

**Re-verification verdict (all-disk, 2026-06-18):** **CONFIRMED-ALLDISK** — v3.14 hard-link mechanism confirmed on disk: every non-resident type-0x30 entry has key_flags=0x02 and value length EXACTLY 84 bytes (112645/113191 on v3.14; the rest are 72B legacy entries on upgrade volumes). value+0x00 = per-directory ordinal (0 for dirs, nonzero for files); value+0x08 = home-dir backref OID (always a real OID). Hard-link groups verified: names sharing the same (home, ordinal) appear as separate type-0x30 rows in DIFFERENT parent directories (e.g. specials image home=0x702 ord=6 shared by 7 names across 7 parent dirs). 180 such groups on win10refs2tspecials; 35003 group-keys corpus-wide. Ordinal is per-home (reused across homes), NOT globally unique - matches the claim's nuance.

**Original audit verdict:** CONFIRMED-ALLDISK (disk held 1/1 at audit time) · **Registry status:** CONFIRMED · **Evidence:** E2+RD

> Regenerated 2026-06-18 from the corrected registry + the all-disk re-verification (NOT by re-running the
> audit harness, whose static-cited / single-image probes produced the false positives). CONTRADICTED = the
> audit confirmed a claim the disk disproves; INFERRED = offset/value RD-confirmed but the semantic label is
> E2/E1/behavioral, not disk-checkable; CONFIRMED-ALLDISK = re-measured across the corpus.

## Static-analysis proof
- proofs/static/RefsConvertToStandardInfoLinkCount__decomp.txt
- E2+RD. Static (win11_4b0558f6): RefsComputeStandardInformationFromFcb ($SI+0x70<-FCB+0xb4, $SI+0x58<-SCB+0x1b8), RefsConvertToStandardInfoLinkCount (writes 0x70/size 4), RefsLinkFileToSelf/RefsAddLink (copy home pair, tag 0x80000040); all absent in win10 v3.4. RD (win11refs2gtargeted): fsutil hardlink list = file1 4 names, file2 2, survivor 1; on disk file1's 4 entries all ordinal 3 / home 0x600, file2 ordinal 4; ordinal 3 reused across dir1+dir2 (per-directory, not unique). Cited (mechanism demonstrated on the step6 image; not a single-field corpus probe).

## Raw-disk proof
- probe `cite` ; validation matrix: `proofs/validation/FN_LINK_002.csv`
- corrected registry note: win11refs2gtargeted.raw: fsutil oracle file1=4 names, file2=2, survivor=1; on disk (raw struct.unpack) file1's 4 entries all ordinal 3, file2's 2 all ordinal 4, survivor 5, all home backref 0x600; ordinal 3 reused across dir1(0x705)+dir2(0x706) proving per-directory (not unique). Grouping by (home,ordinal,size,ctime,mtime) reproduces fsutil hardlink list exactly.

## Proof links
- `proofs/static/RefsConvertToStandardInfoLinkCount__decomp.txt` (static) — RefsConvertToStandardInfoLinkCount
- `proofs/validation/FN_LINK_002.csv` (matrix) — 
