# Sample command manifest — win11refs2tsnapshots.raw

Every file under `forefst/` and `refsanalysis/`, and the exact command that produced it.
Regenerate with `analysis/tools/analysis_scripts/gen_samples.sh`. Image path shown as the basename.

## forefst/

| File | Command |
|------|---------|
| `files.csv` | `forefst win11refs2tsnapshots.raw files -q` |
| `files.json` | `forefst win11refs2tsnapshots.raw files --json -q` |
| `files.jsonl` | `forefst win11refs2tsnapshots.raw files --jsonl -q` |
| `files.body` | `forefst win11refs2tsnapshots.raw files --body -q` |
| `summary.txt` | `forefst win11refs2tsnapshots.raw summary -q` |
| `search_test.txt` | `forefst win11refs2tsnapshots.raw search test` |
| `specials.txt` | `forefst win11refs2tsnapshots.raw specials` |
| `specials.ads.txt` | `forefst win11refs2tsnapshots.raw specials ads` |
| `specials.reparse.txt` | `forefst win11refs2tsnapshots.raw specials reparse` |
| `specials.hardlink.txt` | `forefst win11refs2tsnapshots.raw specials hardlink` |
| `specials.snapshot.txt` | `forefst win11refs2tsnapshots.raw specials snapshot` |
| `specials.sparse.txt` | `forefst win11refs2tsnapshots.raw specials sparse` |
| `reparse.txt` | `forefst win11refs2tsnapshots.raw reparse` |
| `reparse.index.txt` | `forefst win11refs2tsnapshots.raw reparse --index` |
| `snapshots.txt` | `forefst win11refs2tsnapshots.raw snapshots` |
| `snapshots.v.txt` | `forefst win11refs2tsnapshots.raw snapshots -v` |
| `deleted.txt` | `forefst win11refs2tsnapshots.raw deleted --no-slack` |
| `deleted.slack.txt` | `forefst win11refs2tsnapshots.raw deleted --max-scan 8000` |
| `recyclebin.txt` | `forefst win11refs2tsnapshots.raw recyclebin` |
| `timeline.csv` | `forefst win11refs2tsnapshots.raw timeline --csv` |
| `timeline.txt` | `forefst win11refs2tsnapshots.raw timeline --limit 200` |
| `timeline.mlog.csv` | `forefst win11refs2tsnapshots.raw timeline --source MLOG --csv` |
| `timestomp.txt` | `forefst win11refs2tsnapshots.raw timestomp` |
| `timestomp.csv` | `forefst win11refs2tsnapshots.raw timestomp --csv -` |
| `usn.txt` | `forefst win11refs2tsnapshots.raw usn --stats` |
| `mlog.txt` | `forefst win11refs2tsnapshots.raw mlog --stats` |
| `mlog.parsed.txt` | `forefst win11refs2tsnapshots.raw mlog --parse` |
| `mlog.csv` | `forefst win11refs2tsnapshots.raw mlog --csv mlog.csv` |
| `security.txt` | `forefst win11refs2tsnapshots.raw security` |
| `security.files.txt` | `forefst win11refs2tsnapshots.raw security --files` |
| `integrity.txt` | `forefst win11refs2tsnapshots.raw integrity` |
| `dataruns.txt` | `forefst win11refs2tsnapshots.raw dataruns` |
| `export.reparse.txt` | `forefst win11refs2tsnapshots.raw export reparse` |
| `export.reparse.json` | `forefst win11refs2tsnapshots.raw export reparse --json` |

## refsanalysis/

| File | Command |
|------|---------|
| `summary.txt` | `refsanalysis win11refs2tsnapshots.raw summary` |
| `summary-plus.txt` | `refsanalysis win11refs2tsnapshots.raw summary++` |
| `files.txt` | `refsanalysis win11refs2tsnapshots.raw files` |
| `files.v.txt` | `refsanalysis win11refs2tsnapshots.raw files -v` |
| `attributes.txt` | `refsanalysis win11refs2tsnapshots.raw attributes` |
| `boot.txt` | `refsanalysis win11refs2tsnapshots.raw boot` |
| `boot.vv.txt` | `refsanalysis win11refs2tsnapshots.raw boot -vv` |
| `supb.txt` | `refsanalysis win11refs2tsnapshots.raw supb` |
| `supb.vv.txt` | `refsanalysis win11refs2tsnapshots.raw supb -vv` |
| `chkp.txt` | `refsanalysis win11refs2tsnapshots.raw chkp` |
| `chkp.vv.txt` | `refsanalysis win11refs2tsnapshots.raw chkp -vv` |
| `objects.txt` | `refsanalysis win11refs2tsnapshots.raw objects` |
| `objects.vv.txt` | `refsanalysis win11refs2tsnapshots.raw objects -vv` |
| `schema.txt` | `refsanalysis win11refs2tsnapshots.raw schema` |
| `schema.vv.txt` | `refsanalysis win11refs2tsnapshots.raw schema -vv` |
| `parentchild.txt` | `refsanalysis win11refs2tsnapshots.raw parentchild` |
| `parentchild.vv.txt` | `refsanalysis win11refs2tsnapshots.raw parentchild -vv` |
| `containers.txt` | `refsanalysis win11refs2tsnapshots.raw containers` |
| `containers.v.txt` | `refsanalysis win11refs2tsnapshots.raw containers -v` |
| `upcase.txt` | `refsanalysis win11refs2tsnapshots.raw upcase` |
| `upcase.vv.txt` | `refsanalysis win11refs2tsnapshots.raw upcase -vv` |
| `oid30.txt` | `refsanalysis win11refs2tsnapshots.raw oid30` |
| `oid30.v.txt` | `refsanalysis win11refs2tsnapshots.raw oid30 -v` |
| `integrity.txt` | `refsanalysis win11refs2tsnapshots.raw forefst integrity` |
| `integrity.v.txt` | `refsanalysis win11refs2tsnapshots.raw forefst integrity -v` |
| `dataruns.txt` | `refsanalysis win11refs2tsnapshots.raw forefst dataruns` |
| `dataruns.v.txt` | `refsanalysis win11refs2tsnapshots.raw forefst dataruns -v` |
| `deleted.txt` | `refsanalysis win11refs2tsnapshots.raw forefst deleted` |
| `deleted.scan-pages.txt` | `refsanalysis win11refs2tsnapshots.raw forefst deleted --scan-pages` |
| `snapshots.txt` | `refsanalysis win11refs2tsnapshots.raw forefst snapshots` |
| `snapshots.v.txt` | `refsanalysis win11refs2tsnapshots.raw forefst snapshots -v` |
| `mlog.txt` | `refsanalysis win11refs2tsnapshots.raw forefst mlog` |
| `mlog.v.txt` | `refsanalysis win11refs2tsnapshots.raw forefst mlog -v` |
| `timeline.txt` | `refsanalysis win11refs2tsnapshots.raw forefst timeline` |
| `timestomp.txt` | `refsanalysis win11refs2tsnapshots.raw forefst timestomp` |
| `usn.txt` | `refsanalysis win11refs2tsnapshots.raw forefst usn` |
| `security.txt` | `refsanalysis win11refs2tsnapshots.raw forefst security` |
| `security.v.txt` | `refsanalysis win11refs2tsnapshots.raw forefst security -v` |
| `security.files.txt` | `refsanalysis win11refs2tsnapshots.raw forefst security --files` |
| `reparse.txt` | `refsanalysis win11refs2tsnapshots.raw forefst reparse` |
| `reparse.index.txt` | `refsanalysis win11refs2tsnapshots.raw forefst reparse --index` |
