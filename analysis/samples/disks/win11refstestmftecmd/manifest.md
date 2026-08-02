# Sample command manifest — win11refstestmftecmd.raw

Every file under `forefst/` and `refsanalysis/`, and the exact command that produced it.
Regenerate with `analysis/tools/analysis_scripts/gen_samples.sh`. Image path shown as the basename.

## forefst/

| File | Command |
|------|---------|
| `files.csv` | `forefst win11refstestmftecmd.raw files -q` |
| `files.json` | `forefst win11refstestmftecmd.raw files --json -q` |
| `files.jsonl` | `forefst win11refstestmftecmd.raw files --jsonl -q` |
| `files.body` | `forefst win11refstestmftecmd.raw files --body -q` |
| `summary.txt` | `forefst win11refstestmftecmd.raw summary -q` |
| `search_test.txt` | `forefst win11refstestmftecmd.raw search test` |
| `specials.txt` | `forefst win11refstestmftecmd.raw specials` |
| `specials.ads.txt` | `forefst win11refstestmftecmd.raw specials ads` |
| `specials.reparse.txt` | `forefst win11refstestmftecmd.raw specials reparse` |
| `specials.hardlink.txt` | `forefst win11refstestmftecmd.raw specials hardlink` |
| `specials.snapshot.txt` | `forefst win11refstestmftecmd.raw specials snapshot` |
| `specials.sparse.txt` | `forefst win11refstestmftecmd.raw specials sparse` |
| `reparse.txt` | `forefst win11refstestmftecmd.raw reparse` |
| `reparse.index.txt` | `forefst win11refstestmftecmd.raw reparse --index` |
| `snapshots.txt` | `forefst win11refstestmftecmd.raw snapshots` |
| `snapshots.v.txt` | `forefst win11refstestmftecmd.raw snapshots -v` |
| `deleted.txt` | `forefst win11refstestmftecmd.raw deleted --no-slack` |
| `deleted.recovery.txt` | `forefst win11refstestmftecmd.raw deleted --max-scan 8000` |
| `deleted.full.txt` | `forefst win11refstestmftecmd.raw deleted --full --max-scan 8000` |
| `deleted.orphans.txt` | `forefst win11refstestmftecmd.raw deleted --orphans --max-scan 8000` |
| `recyclebin.txt` | `forefst win11refstestmftecmd.raw recyclebin` |
| `timeline.csv` | `forefst win11refstestmftecmd.raw timeline --csv` |
| `timeline.txt` | `forefst win11refstestmftecmd.raw timeline --limit 200` |
| `timeline.mlog.csv` | `forefst win11refstestmftecmd.raw timeline --source MLOG --csv` |
| `timestomp.txt` | `forefst win11refstestmftecmd.raw timestomp` |
| `timestomp.csv` | `forefst win11refstestmftecmd.raw timestomp --csv -` |
| `usn.txt` | `forefst win11refstestmftecmd.raw usn --stats` |
| `mlog.txt` | `forefst win11refstestmftecmd.raw mlog --stats` |
| `mlog.parsed.txt` | `forefst win11refstestmftecmd.raw mlog --parse` |
| `mlog.csv` | `forefst win11refstestmftecmd.raw mlog --csv mlog.csv` |
| `security.txt` | `forefst win11refstestmftecmd.raw security` |
| `security.files.txt` | `forefst win11refstestmftecmd.raw security --files` |
| `integrity.txt` | `forefst win11refstestmftecmd.raw integrity` |
| `dataruns.txt` | `forefst win11refstestmftecmd.raw dataruns` |
| `export.reparse.txt` | `forefst win11refstestmftecmd.raw export reparse` |
| `export.reparse.json` | `forefst win11refstestmftecmd.raw export reparse --json` |

## refsanalysis/

| File | Command |
|------|---------|
| `summary.txt` | `refsanalysis win11refstestmftecmd.raw summary` |
| `summary-plus.txt` | `refsanalysis win11refstestmftecmd.raw summary++` |
| `files.txt` | `refsanalysis win11refstestmftecmd.raw files` |
| `files.v.txt` | `refsanalysis win11refstestmftecmd.raw files -v` |
| `attributes.txt` | `refsanalysis win11refstestmftecmd.raw attributes` |
| `boot.txt` | `refsanalysis win11refstestmftecmd.raw boot` |
| `boot.vv.txt` | `refsanalysis win11refstestmftecmd.raw boot -vv` |
| `supb.txt` | `refsanalysis win11refstestmftecmd.raw supb` |
| `supb.vv.txt` | `refsanalysis win11refstestmftecmd.raw supb -vv` |
| `chkp.txt` | `refsanalysis win11refstestmftecmd.raw chkp` |
| `chkp.vv.txt` | `refsanalysis win11refstestmftecmd.raw chkp -vv` |
| `objects.txt` | `refsanalysis win11refstestmftecmd.raw objects` |
| `objects.vv.txt` | `refsanalysis win11refstestmftecmd.raw objects -vv` |
| `schema.txt` | `refsanalysis win11refstestmftecmd.raw schema` |
| `schema.vv.txt` | `refsanalysis win11refstestmftecmd.raw schema -vv` |
| `parentchild.txt` | `refsanalysis win11refstestmftecmd.raw parentchild` |
| `parentchild.vv.txt` | `refsanalysis win11refstestmftecmd.raw parentchild -vv` |
| `containers.txt` | `refsanalysis win11refstestmftecmd.raw containers` |
| `containers.v.txt` | `refsanalysis win11refstestmftecmd.raw containers -v` |
| `upcase.txt` | `refsanalysis win11refstestmftecmd.raw upcase` |
| `upcase.vv.txt` | `refsanalysis win11refstestmftecmd.raw upcase -vv` |
| `oid30.txt` | `refsanalysis win11refstestmftecmd.raw oid30` |
| `oid30.v.txt` | `refsanalysis win11refstestmftecmd.raw oid30 -v` |
| `integrity.txt` | `refsanalysis win11refstestmftecmd.raw forefst integrity` |
| `integrity.v.txt` | `refsanalysis win11refstestmftecmd.raw forefst integrity -v` |
| `dataruns.txt` | `refsanalysis win11refstestmftecmd.raw forefst dataruns` |
| `dataruns.v.txt` | `refsanalysis win11refstestmftecmd.raw forefst dataruns -v` |
| `deleted.txt` | `refsanalysis win11refstestmftecmd.raw forefst deleted` |
| `deleted.scan-pages.txt` | `refsanalysis win11refstestmftecmd.raw forefst deleted --scan-pages` |
| `snapshots.txt` | `refsanalysis win11refstestmftecmd.raw forefst snapshots` |
| `snapshots.v.txt` | `refsanalysis win11refstestmftecmd.raw forefst snapshots -v` |
| `mlog.txt` | `refsanalysis win11refstestmftecmd.raw forefst mlog` |
| `mlog.v.txt` | `refsanalysis win11refstestmftecmd.raw forefst mlog -v` |
| `timeline.txt` | `refsanalysis win11refstestmftecmd.raw forefst timeline` |
| `timestomp.txt` | `refsanalysis win11refstestmftecmd.raw forefst timestomp` |
| `usn.txt` | `refsanalysis win11refstestmftecmd.raw forefst usn` |
| `security.txt` | `refsanalysis win11refstestmftecmd.raw forefst security` |
| `security.v.txt` | `refsanalysis win11refstestmftecmd.raw forefst security -v` |
| `security.files.txt` | `refsanalysis win11refstestmftecmd.raw forefst security --files` |
| `reparse.txt` | `refsanalysis win11refstestmftecmd.raw forefst reparse` |
| `reparse.index.txt` | `refsanalysis win11refstestmftecmd.raw forefst reparse --index` |
| `usn.v.txt` | `refsanalysis win11refstestmftecmd.raw forefst usn -v` |
