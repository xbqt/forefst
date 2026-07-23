# Sample command manifest — wininsiderrefs8gtest2.raw

Every file under `forefst/`, and the exact command that produced it. Run each against your
decompressed `wininsiderrefs8gtest2.raw` (see this image's README to fetch it).

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
| `deleted.slack.txt` | `forefst wininsiderrefs8gtest2.raw deleted --max-scan 8000` |
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

Structure-analysis output. Naming convention: `<sub>.txt` = default run,
`<sub>.v.txt` / `<sub>.vv.txt` = higher verbosity, `<sub>.<opt>.txt` = that option
(e.g. `security.files.txt` = `refsanalysis wininsiderrefs8gtest2.raw security --files`,
`reparse.index.txt` = `refsanalysis wininsiderrefs8gtest2.raw reparse --index`).
The forensic subcommands were reached via the passthrough `refsanalysis wininsiderrefs8gtest2.raw forefst <cmd>`.
