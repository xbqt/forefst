# Sample command manifest — win11refs2tsnapshots.raw

Every file under `forefst/`, and the exact command that produced it. Run each against your
reassembled `win11refs2tsnapshots.raw` (see this image's README to recompose the disk).

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

Structure-analysis output. Naming convention: `<sub>.txt` = default run,
`<sub>.v.txt` / `<sub>.vv.txt` = higher verbosity, `<sub>.<opt>.txt` = that option
(e.g. `security.files.txt` = `refsanalysis win11refs2tsnapshots.raw security --files`,
`reparse.index.txt` = `refsanalysis win11refs2tsnapshots.raw reparse --index`).
The forensic subcommands were reached via the passthrough `refsanalysis win11refs2tsnapshots.raw forefst <cmd>`.
