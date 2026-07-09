# How to export the stream snapshots of a targeted file

A ReFS **stream snapshot** is a point-in-time copy of one file's data stream (created with
`refsutil streamsnapshot /c "<name>" <file>`). This walkthrough shows the three steps to go from
"which files even have snapshots?" to "the prior versions of one file, written out as files."

Image used: `win11refs2tsnapshots.raw` (ReFS 3.14). Replace `forefst.py <image>` with your image path.

## Step 1 — find which files have snapshots

```
$ forefst.py win11refs2tsnapshots.raw snapshots
==============================================================================
ReFS Stream Snapshot Analysis
==============================================================================
  Image:        win11refs2tsnapshots.raw
  ReFS version: 3.14
  Files with snapshots: 5
  Total snapshots:      10
------------------------------------------------------------------------------
  FILE testsnapshots/arg.txt
    Snapshots:    1
  FILE testsnapshots/lasttest.txt
    Snapshots:    2
  ...
```

`snapshots` lists every file that carries one or more stream snapshots, with a version count each.
(`SnapshotCount` is also a column in `files` / `files --filter snapshot`, and `specials snapshot`
gives the same list.)

## Step 2 — preview one file's versions (see the names + sizes, and a content preview)

```
$ forefst.py win11refs2tsnapshots.raw snapshots --file lasttest.txt --show
  FILE testsnapshots/lasttest.txt
    Resident:     1600 bytes
    Snapshots:    2
    [1] "sameaslastversion"
        Stream size:   201 bytes
    [2] "first"
        Stream size:   ...
    Recovered content (2 version(s)):
      [first] ... 'aaaaaaaa...'
```

`--show` recovers and previews each version's content so you can confirm which one you want.
`--file` matches on a path substring, so `--file lasttest.txt` isolates that one file.

## Step 3 — export that file's snapshot versions to a folder

```
$ forefst.py win11refs2tsnapshots.raw export snapshots ./versions/ --file lasttest.txt
      -> wrote ./versions/testsnapshots_lasttest.txt__first
      -> wrote ./versions/testsnapshots_lasttest.txt__sameaslastversion
```

Each version is written to its **own file**, named `<path>__<snapshot-name>`. This is binary-safe —
the bytes go straight to files, never to the terminal — so a snapshot of a binary stream (an image,
a database page, an EXE) is written exactly as-is:

```
$ ls ./versions/
testsnapshots_lasttest.txt__first
testsnapshots_lasttest.txt__sameaslastversion
```

If you omit the directory (`export snapshots --file lasttest.txt`), a timestamped
`forefst_export_snapshots_<stamp>/` folder is created for you.

### `--file` matching, name collisions, and the output folder

- **`--file` is a path substring**, not an exact name. `--file lasttest.txt` matches every path that
  *contains* that text. If two different files share a name (e.g. `a/report.txt` and `b/report.txt`),
  `--file report.txt` exports the snapshots of **both** — there is no collision on disk because each
  output file is named after its **full path** (`a_report.txt__v1`, `b_report.txt__v1`). To isolate one,
  pass more of the path: `--file b/report.txt`.
- **The folder is whatever you name it.** `./versions/` in Step 3 is just the output directory you chose;
  any path works, and omitting it auto-creates `forefst_export_snapshots_<stamp>/`.
- **All versions of every match are exported by default.** `export snapshots DIR --file NAME` writes *every*
  snapshot version of *every* matching file.
- **Select ONE version with `--snapshot SEL`.** `SEL` is either the 1-based `[N]` index shown in the listing,
  or part of a version name — e.g. `export snapshots DIR --file report.txt --snapshot 2` (index) or
  `--snapshot first` (name). Combine with `--show` to preview just that version before extracting.

## One-liners

| Goal | Command |
|------|---------|
| Which files have snapshots? | `forefst.py IMG snapshots` |
| Preview one file's versions | `forefst.py IMG snapshots --file NAME --show` |
| Extract one file's versions | `forefst.py IMG export snapshots DIR --file NAME` |
| Extract **one specific version** | `forefst.py IMG export snapshots DIR --file NAME --snapshot SEL` |
| Extract **all** snapshots on the volume | `forefst.py IMG export snapshots DIR` |

> Note on partial (CoW-shared) snapshots: a snapshot of a file that was modified *after* it was taken
> stores only the changed region's extents, so its recovered content can be shorter than the version's
> full size (the unchanged part is shared with the base). `--show` reports the recovered length.
