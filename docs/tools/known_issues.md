# Known issues in 1.14.1

These are the known limits of this release that can change what an examiner reports: what the tools do not read or
do not check.

Each item says what the output shows and what to do.

**Coverage of the checks**

- **`export recyclebin` does not write the files inside a recycled folder.** It writes each recycled file and its
  named streams; a recycled folder is named, with how many files it holds, and the command exits 2 when it holds any.
  No test volume holds a recycled folder with files in it, so the writer is not there yet.

  What to do: list the folder's files with `files` (their paths are under the folder's `$R` name in `$RECYCLE.BIN`)
  and write each with `export file <path>`.

- **Compressed and compacted containers are not read.** A container whose Container Table row marks it compressed
  or compacted, or that is mapped by more than one range, is listed with the reason (`summary`, `integrity`,
  refsanalysis `containers`). Every read into it is a recorded skip: the command says what it could not read and
  exits 2. Its clusters are never read as if they held the data.

  What to do: report the files whose data lies in such a container as not examined by the tool.

- **A metadata page below a table's root page is checked only on request.** Every command checks the root page of
  each table it reads against the digest recorded for it: the checkpoint's tables when it opens the volume, each
  object's when it reads the object. A page below a root is checked against its parent's digest only with
  `--verify-pages` (the pages the command reads) or `integrity --fullchecksums` (every page of every object B-tree).
  Without them an altered page below a root is read as found, unchecked.

  What to do: run `integrity --fullchecksums` once on the volume, or the command you report from with
  `--verify-pages`.

- **The MLog is checked only up to the log end the control area recorded at its last write.** `mlog`, `timeline` and
  `summary --mlog` (its MLog section) report records missing below that end as a finding (exit 2). Records written
  after the control area's last write are not covered, so their loss is not seen.

  What to do: read a clean result as "no record is missing up to the recorded log end", not as proof that the log is
  complete.

**Deleted files**

- **An earlier version of a live file is not carved.** When `deleted` finds an earlier row of a file that is still
  live (`RENAMED`, `SAME FILE, OTHER CREATION TIME`, `STILL PRESENT`), it offers no carve of that row's extent map and
  does not write the bytes the row holds inline; `extract` gives the live file's current content.

  The entry says so (`metadata + extent map, not carved` / `metadata + N B inline, not written`). For a map it says
  where the map's clusters are now: for example in the live file's extents, in another live file's (named), or in no
  live file's, where they may still hold the earlier version.

  What to do: where the entry says the clusters lie in no live file's extents, report the earlier version as not
  recovered by the tool, not as absent.

**USN journal and timestamps**

- **A file's journal pointer is checked only at the end of the journal.** `usn --info`, `timeline` and `timestomp`
  compare the highest `LastUsn` the files hold with the journal's last record. A `LastUsn` inside the journal's range
  that names no record, or names another object's record, draws no warning.

  What to do: before citing a file's `LastUsn` as its last journal event, find that USN in `usn --csv` and check that
  the record's `ObjectRef` is the file's.

- **A re-created journal is seen only through what survives of the earlier one.** `usn`, `timeline` and
  `timestomp` name a re-creation from the journal's own numbering, from records of the earlier journal still in
  `$J`, or from files that still carry its id. A re-creation that left none of these reads as one journal.

  What to do: do not read a clean result as proof that the journal was never re-created. Where an earlier image or
  collection of this volume recorded its `Journal ID`, compare it with the one `usn --info` prints.

- **An MLog row's time is a time its records wrote into the metadata, not the moment the log was written.** A record
  is dated by the times its value holds (a `$SI`, an index entry, the volume information), and a `mlog --parse` or
  `timeline` MLog row takes the latest time its log payload's records carry. So:
  - a payload can merge up to 15 redo blocks, and the row's time can belong to another operation of the same payload;
  - a record that rewrites a row without changing its times carries the row's earlier times: such a row is dated
    before rows the log holds ahead of it;
  - a time a program set forward is taken as the row's time;
  - a rename or delete that embeds no time takes the paired `$SI` update's time; a record that writes only part of a
    row (a file's inline bytes, its sizes) carries no time. Both outputs say so.

  What to do: do not date an operation from its MLog row alone; corroborate it with the file's `$SI` times or its USN
  records.
