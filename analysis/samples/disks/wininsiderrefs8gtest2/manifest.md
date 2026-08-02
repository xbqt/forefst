# Sample command manifest — wininsiderrefs8gtest2.raw

Every file under `forefst/` and `refsanalysis/`, and the exact command that produced it.
Regenerate with `analysis/tools/analysis_scripts/gen_samples.sh`. Image path shown as the basename.

## forefst/

| File | Command |
|------|---------|
| `files.csv` | `forefst wininsiderrefs8gtest2.raw files -q` |
| `files.json` | `forefst wininsiderrefs8gtest2.raw files --json -q` |
| `files.jsonl` | `forefst wininsiderrefs8gtest2.raw files --jsonl -q` |
| `files.body` | `forefst wininsiderrefs8gtest2.raw files --body -q` |
| `summary.txt` | `forefst wininsiderrefs8gtest2.raw summary -q` |
| `search_test.txt` | `forefst wininsiderrefs8gtest2.raw search test` |
| `specials.txt` | `forefst wininsiderrefs8gtest2.raw specials` |
| `specials.ads.txt` | `forefst wininsiderrefs8gtest2.raw specials ads` |
| `specials.reparse.txt` | `forefst wininsiderrefs8gtest2.raw specials reparse` |
| `specials.hardlink.txt` | `forefst wininsiderrefs8gtest2.raw specials hardlink` |
| `specials.snapshot.txt` | `forefst wininsiderrefs8gtest2.raw specials snapshot` |
| `specials.sparse.txt` | `forefst wininsiderrefs8gtest2.raw specials sparse` |
| `reparse.txt` | `forefst wininsiderrefs8gtest2.raw reparse` |
| `reparse.index.txt` | `forefst wininsiderrefs8gtest2.raw reparse --index` |
| `snapshots.txt` | `forefst wininsiderrefs8gtest2.raw snapshots` |
| `snapshots.v.txt` | `forefst wininsiderrefs8gtest2.raw snapshots -v` |
| `deleted.txt` | `forefst wininsiderrefs8gtest2.raw deleted --no-slack` |
| `deleted.recovery.txt` | `forefst wininsiderrefs8gtest2.raw deleted --max-scan 8000` |
| `deleted.full.txt` | `forefst wininsiderrefs8gtest2.raw deleted --full --max-scan 8000` |
| `deleted.orphans.txt` | `forefst wininsiderrefs8gtest2.raw deleted --orphans --max-scan 8000` |
| `recyclebin.txt` | `forefst wininsiderrefs8gtest2.raw recyclebin` |
| `timeline.csv` | `forefst wininsiderrefs8gtest2.raw timeline --csv` |
| `timeline.txt` | `forefst wininsiderrefs8gtest2.raw timeline --limit 200` |
| `timeline.mlog.csv` | `forefst wininsiderrefs8gtest2.raw timeline --source MLOG --csv` |
| `timestomp.txt` | `forefst wininsiderrefs8gtest2.raw timestomp` |
| `timestomp.csv` | `forefst wininsiderrefs8gtest2.raw timestomp --csv -` |
| `usn.txt` | `forefst wininsiderrefs8gtest2.raw usn --stats` |
| `mlog.txt` | `forefst wininsiderrefs8gtest2.raw mlog --stats` |
| `mlog.parsed.txt` | `forefst wininsiderrefs8gtest2.raw mlog --parse` |
| `mlog.csv` | `forefst wininsiderrefs8gtest2.raw mlog --csv mlog.csv` |
| `security.txt` | `forefst wininsiderrefs8gtest2.raw security` |
| `security.files.txt` | `forefst wininsiderrefs8gtest2.raw security --files` |
| `integrity.txt` | `forefst wininsiderrefs8gtest2.raw integrity` |
| `dataruns.txt` | `forefst wininsiderrefs8gtest2.raw dataruns` |
| `export.reparse.txt` | `forefst wininsiderrefs8gtest2.raw export reparse` |
| `export.reparse.json` | `forefst wininsiderrefs8gtest2.raw export reparse --json` |

## refsanalysis/

| File | Command |
|------|---------|
| `summary.txt` | `refsanalysis wininsiderrefs8gtest2.raw summary` |
| `summary-plus.txt` | `refsanalysis wininsiderrefs8gtest2.raw summary++` |
| `files.txt` | `refsanalysis wininsiderrefs8gtest2.raw files` |
| `files.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw files -v` |
| `attributes.txt` | `refsanalysis wininsiderrefs8gtest2.raw attributes` |
| `boot.txt` | `refsanalysis wininsiderrefs8gtest2.raw boot` |
| `boot.vv.txt` | `refsanalysis wininsiderrefs8gtest2.raw boot -vv` |
| `supb.txt` | `refsanalysis wininsiderrefs8gtest2.raw supb` |
| `supb.vv.txt` | `refsanalysis wininsiderrefs8gtest2.raw supb -vv` |
| `chkp.txt` | `refsanalysis wininsiderrefs8gtest2.raw chkp` |
| `chkp.vv.txt` | `refsanalysis wininsiderrefs8gtest2.raw chkp -vv` |
| `objects.txt` | `refsanalysis wininsiderrefs8gtest2.raw objects` |
| `objects.vv.txt` | `refsanalysis wininsiderrefs8gtest2.raw objects -vv` |
| `schema.txt` | `refsanalysis wininsiderrefs8gtest2.raw schema` |
| `schema.vv.txt` | `refsanalysis wininsiderrefs8gtest2.raw schema -vv` |
| `parentchild.txt` | `refsanalysis wininsiderrefs8gtest2.raw parentchild` |
| `parentchild.vv.txt` | `refsanalysis wininsiderrefs8gtest2.raw parentchild -vv` |
| `containers.txt` | `refsanalysis wininsiderrefs8gtest2.raw containers` |
| `containers.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw containers -v` |
| `upcase.txt` | `refsanalysis wininsiderrefs8gtest2.raw upcase` |
| `upcase.vv.txt` | `refsanalysis wininsiderrefs8gtest2.raw upcase -vv` |
| `oid30.txt` | `refsanalysis wininsiderrefs8gtest2.raw oid30` |
| `oid30.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw oid30 -v` |
| `integrity.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst integrity` |
| `integrity.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst integrity -v` |
| `dataruns.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst dataruns` |
| `dataruns.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst dataruns -v` |
| `deleted.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst deleted` |
| `deleted.scan-pages.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst deleted --scan-pages` |
| `snapshots.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst snapshots` |
| `snapshots.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst snapshots -v` |
| `mlog.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst mlog` |
| `mlog.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst mlog -v` |
| `timeline.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst timeline` |
| `timestomp.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst timestomp` |
| `usn.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst usn` |
| `security.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst security` |
| `security.v.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst security -v` |
| `security.files.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst security --files` |
| `reparse.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst reparse` |
| `reparse.index.txt` | `refsanalysis wininsiderrefs8gtest2.raw forefst reparse --index` |
