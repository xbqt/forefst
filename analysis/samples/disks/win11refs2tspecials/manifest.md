# Sample command manifest — win11refs2tspecials.raw

Every file under `forefst/`, and the exact command that produced it. Run each against your
reassembled `win11refs2tspecials.raw` (see this image's README to recompose the disk).

## forefst/

| File | Command |
|------|---------|
| `files.csv` | `forefst win11refs2tspecials.raw files -q` |
| `files.json` | `forefst win11refs2tspecials.raw files --json -q` |
| `files.jsonl` | `forefst win11refs2tspecials.raw files --jsonl -q` |
| `files.body` | `forefst win11refs2tspecials.raw files --body -q` |
| `summary.txt` | `forefst win11refs2tspecials.raw summary -q` |
| `search_test.txt` | `forefst win11refs2tspecials.raw search test` |
| `specials.txt` | `forefst win11refs2tspecials.raw specials` |
| `specials.ads.txt` | `forefst win11refs2tspecials.raw specials ads` |
| `specials.reparse.txt` | `forefst win11refs2tspecials.raw specials reparse` |
| `specials.hardlink.txt` | `forefst win11refs2tspecials.raw specials hardlink` |
| `specials.snapshot.txt` | `forefst win11refs2tspecials.raw specials snapshot` |
| `specials.sparse.txt` | `forefst win11refs2tspecials.raw specials sparse` |
| `reparse.txt` | `forefst win11refs2tspecials.raw reparse` |
| `reparse.index.txt` | `forefst win11refs2tspecials.raw reparse --index` |
| `snapshots.txt` | `forefst win11refs2tspecials.raw snapshots` |
| `snapshots.v.txt` | `forefst win11refs2tspecials.raw snapshots -v` |
| `deleted.txt` | `forefst win11refs2tspecials.raw deleted --no-slack` |
| `deleted.slack.txt` | `forefst win11refs2tspecials.raw deleted --max-scan 8000` |
| `recyclebin.txt` | `forefst win11refs2tspecials.raw recyclebin` |
| `timeline.csv` | `forefst win11refs2tspecials.raw timeline --csv` |
| `timeline.txt` | `forefst win11refs2tspecials.raw timeline --limit 200` |
| `timeline.mlog.csv` | `forefst win11refs2tspecials.raw timeline --source MLOG --csv` |
| `timestomp.txt` | `forefst win11refs2tspecials.raw timestomp` |
| `timestomp.csv` | `forefst win11refs2tspecials.raw timestomp --csv -` |
| `usn.txt` | `forefst win11refs2tspecials.raw usn --stats` |
| `mlog.txt` | `forefst win11refs2tspecials.raw mlog --stats` |
| `mlog.parsed.txt` | `forefst win11refs2tspecials.raw mlog --parse` |
| `mlog.csv` | `forefst win11refs2tspecials.raw mlog --csv mlog.csv` |
| `security.txt` | `forefst win11refs2tspecials.raw security` |
| `security.files.txt` | `forefst win11refs2tspecials.raw security --files` |
| `integrity.txt` | `forefst win11refs2tspecials.raw integrity` |
| `dataruns.txt` | `forefst win11refs2tspecials.raw dataruns` |
| `export.reparse.txt` | `forefst win11refs2tspecials.raw export reparse` |
| `export.reparse.json` | `forefst win11refs2tspecials.raw export reparse --json` |

## refsanalysis/

Structure-analysis output. Naming convention: `<sub>.txt` = default run,
`<sub>.v.txt` / `<sub>.vv.txt` = higher verbosity, `<sub>.<opt>.txt` = that option
(e.g. `security.files.txt` = `refsanalysis win11refs2tspecials.raw security --files`,
`reparse.index.txt` = `refsanalysis win11refs2tspecials.raw reparse --index`).
The forensic subcommands were reached via the passthrough `refsanalysis win11refs2tspecials.raw forefst <cmd>`.
