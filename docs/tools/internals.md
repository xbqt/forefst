# forefst internals

How `forefst.py` and `refsanalysis.py` are built: the order in which a volume is read, the functions that do each
step, the rule each one follows and why, and where that rule comes from in the ReFS driver. It is written for a
developer who changes the code and for an examiner who wants to judge a result. What each command prints and how to
call it is in the [forefst reference](forefst.md) and the [refsanalysis reference](refsanalysis.md); what changed in a
release is in the [changelog](../changelog.md).

Function names below are the code's, and a documentation gate checks that each one still exists. Driver function names
(`ReadLatestCheckpoint`, `CmsRestarter::ForEachRedoInBlock`, ...) are the symbols of the `refs.sys` builds read
statically ([Driver builds](../methodology/driver_builds.md)); where a rule was read on some builds only, the text says
which.

## The shape of the code

- **Two files, the Python standard library only** (Python 3.7 or later). `forefst.py` holds everything that reads a
  volume. `refsanalysis.py` is the lab tool: it imports `forefst` and uses its readers, so the two never parse a
  structure two ways. It runs only with the `forefst` of its own release and stops with a message otherwise.
- **Read-only.** `forefst` opens the image read-only and writes only the output files it is asked for.
  `refsanalysis bootedit` (marked dangerous in its help) is the one command that can write to the image it is given,
  and only with `--inplace`; by default it writes a sparse copy.
- **One definition per rule.** A fact several commands need (which checkpoint copy is used, which superblock copy is
  read, what the exit code is) is computed by one function, listed in the single-source table of the verification
  harness; a gate fails when a second computation of the same fact appears (see the last section).
- **Findings go to one sink.** Every condition that should change the exit code is recorded with `_finding` (or one of
  the older registers `rc_escalate` reads), and the exit code is computed from that record, never from what a command
  happened to print.

## Reading a volume: `bootstrap`

`bootstrap` returns the volume view every command reads: the file, the partition start, the cluster size, the address
translator, the global roots, the object map, the version and the checkpoint list. Its steps, in order:

1. **Where the volume starts** (`find_refs_partition`): the first GPT Basic-Data partition whose boot sector carries
   the ReFS signature, or else the first one that can be read (step 2 then tests it). Without a GPT the volume's
   offset is given with `--partition-start` (0 for a bare volume image, the partition's offset on an MBR disk).
2. **The boot sector** (`boot_sector_copy`, `parse_vbr`): the primary sector when it passes its tests, otherwise a
   backup found at the end of the volume or before a container boundary, which is said and is a finding. The fields
   read are the cluster size, the version, the checksum selector and the container size.
3. **The superblock** (`parse_supb`): the copy the driver reads, and its checkpoint list. The driver keeps the first
   valid copy in slot order and lets a later valid copy replace it only when that copy's `+0x68` is strictly higher
   and the chosen copy is not the primary: a valid primary is always read, and of two valid backups the second is
   read only when its `+0x68` is higher. Reading a backup is a finding. The copies are compared on what they share
   (`_supb_payload` masks what each holds for itself: its own LCN, its self-checksum, the header clocks of its
   write), so copies that differ only there are redundancy, not divergence.
4. **The checkpoint** (`checkpoint_select`): the driver's rule, read on 17134, 26100.8115, .8521, .8972, .9444,
   .9549 and Insider 29574 (`ReadLatestCheckpoint` with `ChooseCheckpointRecord`):
   - the copies are read in superblock slot order, a copy that fails validation is skipped, and a later copy replaces
     the chosen one only when its clock at `+0x60` is strictly greater; on a tie slot 0 stays chosen;
   - validation is the copy's own self-checksum, a root list that parses, and the record tests of the builds whose
     tests apply (an offset plus a length is summed as each build sums it, `_chkp_sum`: wrapping at 32 bits on 17134
     and 26100.x, read on .8115 and .9711; in 64 bits on Insider 29574);
   - roots 0xC, 7 and 8 are checked against the digests each copy records; a failure does not change the choice (the
     copy is read if it can be), and the output says what the 26100 driver's strict first pass would do.

   Every caller (`summary`, `deleted`, refsanalysis `chkp`, ...) gets its copy from this one function.
5. **The Container Table** (`container_table_copy`, `container_table_read`): root 7, or root 8 when root 7 fails, as
   the driver reads it; each row is checked once here for every reader, and overlapping or inconsistent rows are
   conditions of the view.
6. **The Object Table** (`object_table_copy`, `build_object_map`): root 0, or root 5, its second copy, when root 0's
   page cannot be read or does not match the digest the checkpoint copy in use records for it (a root whose address the
   Container Table cannot translate is not read, and is said to be unverifiable, named by its VLCN); then object id to root
   LCNs, with each object's root-page digest recorded, so that every later read of an object's root page is checked
   against it.
7. **The checkpoint's other roots** (`_chkp_other_root_findings`): roots 1-4, 6 and 9-11, and root 5 when root 0 is
   read, each against the digest the checkpoint copy in use records for it (`_chkp_root_failures`, the test steps
   4-6 make of roots 0xC, 7, 8 and the two pairs). A page that does not match, or that cannot be verified (no
   reference, a checksum type the tool does not compute, a declared digest length the algorithm's digest does not
   have, or an address the Container Table cannot translate, which is then not read), is a condition of the view, and
   the table is read as it is; a second copy the tool does not read (root 5 while root 0 is read, root 9, the Schema
   Table's failover copy) is a redundancy condition instead (`system_table_findings`), as a backup copy's is. With
   steps 4-7 every root the
   checkpoint lists is checked when the volume is opened; a page below a root is checked against its parent's digest
   only with `--verify-pages` or `integrity --fullchecksums`.

**A new view.** The registers that describe one volume (its findings, its damaged pages, the superblock it fell
back to) are reset when its superblock is read (`_new_view`), before anything of the view is recorded, so a statement
about this volume never carries an earlier volume's state.

refsanalysis also runs `validate_image` before each command: a pre-flight check of the file itself (missing, a
directory, too small) and, without `--partition-start`, of what its first sectors hold (NTFS and BitLocker refused by
name, blank). When the
input is a bundle, its manifest applies to its own rehydrated image only (`_bundle_of`): another image the same run
reads, such as `files --cow-before`'s earlier image, keeps its own holes.

**Conditions of the view.** A condition that changes what every command reads — the volume read from a backup
boot sector or superblock, from a stale checkpoint copy, through overlapping containers — is said by `bootstrap` on
stderr, and every command exits 2. For the checkpoint pair, `_checkpoint_conditions` words every condition once, at
one of two levels: `view` (said through `_view_conditions`) or `redundancy`, a condition of a copy that is not read
(it fails its self-checksum, a root of it does not verify). `summary`, `fastsummary` and `integrity` list the
redundancy conditions and exit 2; the other commands keep their exit code, except one that reads that copy too:
`deleted`'s checkpoint comparison reads the other checkpoint copy, and states that copy's conditions
(`_copy_redundancy_conditions`).

## Addresses: container translation (`Translator`)

Most addresses in ReFS metadata are virtual (VLCN). `Translator.tr` maps one to a physical cluster: the container
id is the VLCN shifted right by the bit length of the clusters-per-container value (the driver's
`GetContainerIdFromRealRange` adds one bit to the log2 width), the offset is the low bits, and the physical cluster
is the container's base from the Container Table plus that offset.

Container ids start at 2, so an address below the first container id is already physical. Roots 7 and 8 (the
Container Table and its copy) and 12 hold physical LCNs and are read without translation. An address past its
container's one range is read linearly from the container's start, though refs.sys refuses such an address, and is a
finding.

## Tables: the B+-tree walk

`walk_bplus` reads a table's root page and checks it against the digest the Object Table recorded for it
(`verify_object_root`), with the bytes already read: the object the caller names or, when the caller names none, the
object whose root LCNs these are (`_OBJ_ROOT_BY_LCNS`, filled with the digests by `build_object_map`), so a walk cannot
read an object's root page unchecked by leaving its name out; `_system_table_copy` tests each copy of a pair itself.
`_walk` then descends to the leaves.

- A root page that fails is a finding, and its object is kept for the view in `_OBJ_ROOT_FAILED`, so a verdict read
  from that table can say so: `security --audit` gives `UNDETERMINED` when the Security Descriptor Stream's root page
  (0x530) failed, and `usn --info` marks the journal's entry when the system metadata table's (0x520) did.
- A child page is checked against the digest its parent's reference carries when `--verify-pages` is given (it costs
  a hash per page, so it is opt-in).
- A page that cannot be read, carries no node signature, reads as all zeros or is not the page its reference names is
  recorded in the damage register (`_DamageList`, counted in distinct pages) and never read as an empty table: a
  count, a listing or a verdict over a table read in part says so and exits 2.

## Files: names, records, residency

A directory is a table. Its name rows (type 0x30) are read by `_parse_dir_entries`; `walk_directory_tree` walks the
whole tree for `files`, `summary` and the other listings, and `_analyze_dir_extents` resolves, for one directory,
every file's data: what `extract`, `export` and `recyclebin` read.

- **Identity.** A file's reference is `HomeOID:FileID`: the object id of the directory that created it (its home)
  and an ordinal within that home (`_entry_identity`). It does not change when the file is renamed or moved.
- **Record placement.** A name row either embeds the file's record or points to it: a hard link or a move to another
  directory splits the record out into a type-0x40 backing kept in the home directory. `_home_backings` reads a
  home's backings once; `_t40_record_tuple` is the one definition of what a backing says (sizes, last USN,
  security id, attributes, the reparse tag and target, its named streams). The facts of a split file come from its
  backing: the name row keeps copies of some of them (its size, for one) that the driver does not refresh on every
  update.
- **Data residency.** A file's bytes are either inline in its record or in extents (`_stream_data_form`, with
  `_resident_data_sizes` for the sizes): a property separate from record placement, so a split file can still
  keep its data inline in the backing. When a record's extent map is itself a nested node of its embedded attribute
  tree, `_embedded_data_extents` returns it only when it covers the record's whole allocation exactly, so a partial
  walk fails cleanly instead of returning part of a file.
- **The v3.4 key form.** A v3.4 volume keys a file's `$DATA` row without the instance marker later formats use, and
  a volume upgraded from 3.4 keeps that form on its old records; `_is_v34_data_key` is the one definition the
  readers of a `$DATA` row use.
- **Counting files, not names.** `_one_row_per_file` keeps a hard-linked file once, by its reference, wherever a
  count or a total is of files.
- **`IsMoved`** (`_is_moved`) is decided by a stated rule from the metadata — the record's reference, and whether
  the name sits in the directory that created the file — and refined by the change journal's moves where the journal
  can be read (`_journal_moves`). A case the metadata cannot decide (a hard-linked file's name outside its creation
  directory) is `undetermined`, never printed as true or false.
- **Volume facts.** `volume_information_fields` is the one decode of `$VOLUME_INFORMATION` (the volume's and the
  last driver's version stamps, the creation and last read-write mount times); `journal_state` gives the change
  journal's state in the three words `summary` uses (`Active`, `Inactive`, `unknown`).

## Content: extents, holes, never-written runs, integrity

`get_file_content` is the one cascade every content reader goes through: inline bytes, a snapshot-shared copy, an
inline extent map, or extents. Three rules decide what is read:

- **The read-time floor** (`_extent_never_read`): no cluster is read for a sparse hole (extent flag 0x20), for a run
  marked allocated but never written (non-zero flags without 0x10), or for VLCN 0. Those ranges come out as zeros. Reading a
  never-written run would return whatever another file left in those clusters.
- **Image holes** (`content_holes`): every producer of output bytes asks, through this one function, whether the
  clusters it is about to emit are stored as holes in the image file. Such bytes are a finding, worded with the
  cause left open: a sparse image keeps a file's own zeros the same way it keeps a range never captured. When the
  host cannot answer (no `SEEK_DATA`), `_hole_unchecked` says so once per run and records a finding. Each producer
  that reads clusters takes `_hole_mark()` (both registers, `_CONTENT_HOLES` and `_CONTENT_UNDET`) before it makes the
  bytes, so the writer sees an unchecked range as well as a hole (inline bytes come from the record and read no
  cluster); `_bulk_hole_finish` writes `holes.json` and counts the streams `--refuse-holes` withheld by cause.
- **Integrity streams** (`_verify_inline_integrity`): an integrity file's extent rows carry a CRC-32C per cluster
  (row flag 0x80; the row's declared size says how many). Each checksummed cluster is read and compared. Clusters
  in rows without a CRC-32C are counted apart, by what the row says: never written (no data, nothing to verify) or
  written without a CRC-32C (not verified). A row whose flags declare a CRC64 per cluster (0x100;
  `_extent_row_is_crc64`) is stepped over by its own declared size, 24 + 8 x run (`_extent_row_size`), and its clusters
  are counted as not verified. The rows are walked in key-index order through the same function
  extraction uses (`_extent_leaf_rows`), so a superseded row in the node is not read in place of the live one.

A large extent-mapped file is written by `_StreamedContent`, in file order and in batches, without being held in
memory; its bytes are those of the in-memory path.

## Journals: the change journal and the MLog

**The change journal** is the stream of the Change Journal object under OID 0x520 (`locate_change_journal`, which
names the object to `walk_bplus`, so the table's root page is verified before the entry is read from it).
`parse_usn_records` reads its ring of records. A record's USN, modulo the journal's allocated size, is its byte
offset in the stream; every genuine record satisfies it, and a record that breaks it is reported, never dropped. Bytes inside the written span that the image
stores as holes are a finding; ring space past the last record is not. Non-zero bytes in a `$J` that holds no record
are a recorded skip: with no record, nothing shows they are unwritten ring space rather than records that are gone.
`usn --info` reads the checkpoint's journal cursor from the copy `checkpoint_select` chooses (`_usn_checkpoint_cursor`:
the 32-byte area at +0x88 / +0x8C, {FirstUsn, NextUsn, wrap base, wrap size}) and counts the current journal's records
at or past NextUsn, the current journal being the first sequence of `_usn_journal_state` after a re-creation.

**The MLog** is found where the driver finds it (`get_mlog_info`, after `InitializeVolumeRedoLog`): the row with key
1 of the Logfile Information Table, opened as the failover pair of OID 0xA and 0x9. Of its two control copies,
`mlog_control_copies` uses one whose own integrity value verifies, as `LogCoreReadControlArea` does. A record belongs
to this volume's log when its header carries the volume's signature and the control area's UUID; a record of an
earlier log left on the disk is shown only by `mlog --earlier-logs`.

The log is read in three layers. A log payload holds up to fifteen merged redo
blocks (`iter_redo_blocks`, after `CmsRestarter::ForEachBlockInMergedBlock`); each block's records are budgeted by
the block header's total size (`CmsRestarter::ForEachRedoInBlock`); and each record's opcode is dispatched by the
table of the volume's version (`PerformRedo`'s tables, 44 values on 3.14, 29 on 3.4). Each record carries an 8-byte
integrity value, recomputed as the driver does before replay. A control-area record found inside the data area is
not read as redo. Log payloads and transaction starts are counted apart (`Log payloads: N (M transaction starts)`): a
payload can hold more than one merged block.

An LSN is a generation (high 32 bits) and a block offset (low 32 bits). The generation goes up by one when the
offset wraps to the start of the data area, and when a log is begun to follow an earlier one, keeping the offset
(`MlLogOpenLog`, read on 26100.9818).

`mlog_tail_check` compares the tail of this log (its newest record plus that record's length) with the log end of the
control area: the forward distance between their offsets, modulo the area's blocks, is the number of 4 KiB log blocks
whose records are missing. It is exact while a record of the log is in the area, since a whole lap would have
overwritten that record's block.

When the area holds no record of the log and the log end says records were written (past block 1 of the first
generation), there is nothing to count from: that is a finding of its own, the records below the log end missing and
their number not known. Every ReFS volume of the corpus holds records of its
own log, the fewest 56, so no volume of the corpus is in that state. `_mlog_missing_why` words what the image says of the
blocks (written, an image hole, a range a bundle does not carry) for both statements.

A record names the table it changes by its key path, whose first component is the table's object id; its `+0x18` and
`+0x20` are the volume's virtual and allocator clocks when the record was added, not a handle. `mlog --parse` names
each transaction's action from the records it holds (`classify_mlog_transaction`): a rename or move is the change one
file's own records pair, and records whose opcode dispatches no handler (0x12 and 0x15) do not decide the class. A
row's time is the latest time its records carry (`_mlog_extract_timestamp`: the latest of a `$SI` update's or an
inserted row's times, a row update's volume-information write time first), or that of the paired `$SI` update
(`mlog_time_source`).
`summary`'s MLog section is built by `mlog`'s own functions (`mlog_summary`, `_print_mlog_section`), so the two state
the same facts. `mlog --json` reads the log in three passes joined by record offset: that assumes the source does
not change between them, which holds for an image file and would have to be checked by a reader of a live volume.

## Comparing two images: `files --cow-before`

`cow_compare` compares this image's tree with an earlier image of the same volume (refused, exit 1, when the
superblock's volume GUID differs: `_view_volume_guid`), object by object (`_cow_objects`: a hard-linked file's names
folded into its one object); a walk that recorded damage or skipped a directory makes the comparison partial, and it
says so.

## Deleted data: `deleted` and the carve

`cmd_deleted` reads four sources and labels every entry with what decided it:

- **The Trash table** (OID 0xD): raw rows of objects deleted and not yet reclaimed (`_scan_trash_table`); a row's
  key is the object's own reference.
- **The checkpoint comparison**: the tree of the copy in use against the tree of the other checkpoint copy, object by
  object by reference, at any depth (`_tree_objects`). The other copy is the previous one, or the newer one when the
  newest copy is not the one read; its own conditions are stated, since the comparison reads it.
- **The slack scan** (`_scan_page_slack`): deleting a row removes its slot from the page's offset array and leaves
  its bytes, until a later copy-on-write rewrites the page; the scan finds the name rows that no slot references and
  that validate as rows (`_row_span_end` bounds each by its own size). `--no-slack` skips it.
- **The old-page scan** (`--full`): metadata pages the live tree no longer references, over the whole volume.

Each row found is checked against the live tree (`_LiveIndex`, built once by `_build_live_identity`) by its identity
before it is called deleted, renamed or still present (`_classify_remnants`: one entry per name, creation time and
kind, every copy kept).

`_remnant_identity` gives a row's reference:

- a directory's own OID;
- a split row's home and ordinal;
- an embedded row's reference from the journal record its last USN names (`_journal_ref_lookup`: an embedded row holds
  no home of its own, and a page can hold another directory's rows);
- else, as a candidate only, the page's owner and the row's ordinal.

`_show_entries` prints the table of statuses first, then each entry (`_entry_block`, `_present_line`).
`--earlier-volumes` shows only the rows of pages another ReFS volume left on the disk, at the address the page itself
names (`_earlier_volumes_view`, `_page_at_own_address`); the old-page scan does not read clusters the image stores as
holes (`_scan_hole_clusters`).

A carve (`export deleted --carve`) is planned once per remnant (`_carve_plan`, kept on the entry by
`_entry_carve_plan`) and made by `_carve_extent_backed`: never-written runs are zero-filled, clusters whose row
carries a CRC-32C are checked, a live file's earlier extent map is not carved (its clusters can hold the live file's
data), and a refused carve states its reason. Which live file holds a cluster comes from `_LiveClusterIndex` (every
live stream's clusters, by holder), with each run cut at container boundaries by `_plcn_pieces`.

## Findings and exit codes

- `_finding(kind, text)` records a finding for the run (the exit code) and for the current volume view (a statement
  about this volume never borrows an earlier view's findings). `_skip_note` records a unit of work skipped, with what
  was skipped and why; `_DamageList` holds the pages that could not be read.
- `rc_escalate` is the one exit rule, in both tools, over one list of registers (`_escalation_registers`, read also by
  `integrity`'s verdict and by the text that names the findings): a command that would exit 0 exits 2 when the run recorded a
  finding or skipped work it reports as complete. A usage error, an unreadable input or an output that could not be
  written is 1; a write that failed while the command went on is 2.
- A *held reading* (`_held_reading`) is one that only uses what it reads for a value another command states; its
  findings are kept apart, so that they are not said twice.
- A decode is reused (one decoded home tree per walk) only when `_run_state_mark`, taken before and after it, shows it
  recorded nothing: a decode that met damage is redone, so its findings are recorded each time.

## Output forms

- **One form per kind of value.** A time is `ft_iso` (UTC, seven fraction digits, ISO 8601, so it sorts as text);
  an identifier, LCN, offset or flag word is `hexid` (lower-case hex, unpadded); a flag word is `flag_text` in text
  (`0x20 (Archive|Directory)`) and two fields in CSV and JSON (`flag_cells`: the names, the hex; a bit with no name
  is written as its hex, never dropped); a reparse tag likewise (`reparse_tag_cells`); a list of names in one CSV
  cell is `csv_list_cell` (escaped, so it splits back); an absent value is null in JSON (`json_null`); an ACE is
  `ace_text` in text and `_ace_machine` in machine outputs; a USN source is `usn_source_text`. A byte count in text
  is `bytes_text`; a count and its noun are `count_noun`, which writes the noun in the number the count takes
  (`1 file`, `2 files`), at every site whose count can be 1; a value that is not a number (`None`, a `?` placeholder)
  is written as it is, with the plural.
- **Names.** `out_key` (and `out_keys`, recursively) maps an internal key to its output name: a command's own
  overrides first, then the `files` column names, then one rule for the rest; two keys that would take one name are
  a defect, raised. **Values.** `machine_forms` writes identifiers, LCNs, offsets, flag words, tags and hashes as
  lower-case hex strings in JSON, a flag word with its names beside it.
- **Files.** A machine-output file is written under `FILE.partial` and renamed when complete (`_PartialFile`): no
  file under the asked name is ever incomplete, and a failed write names the file.
- **One builder per document.** `summary_document` builds `summary`'s and `fastsummary`'s document, which refsanalysis
  `summary` states too; `_parse_security_descriptor` is the one parser of a security descriptor, for `security` and
  `files` alike; `read_bundle_manifest` and `bundle_manifest_document` are a bundle manifest's one reader and writer.
- **Arguments.** `_parse_args` takes the options; a word a command does not take is a usage error
  (`_stray_argument`, exit 1), never ignored.
- **The last write.** Text small enough to stay in the output buffer fails only when it is flushed at exit; the
  flush is done inside the handlers (`_exit_flushed`, `_flush_stdout`), so a full disk ends with the error line and
  exit 1, not a silent exit 0; a reader that closes the pipe early (`| head`) leaves the command's own exit code.

## The rules behind the code: static analysis

| Tool function | Driver behaviour it follows | Read on |
|---|---|---|
| `checkpoint_select` | `ReadLatestCheckpoint`, `ChooseCheckpointRecord<0>`: slot order, skip a failing copy, switch only on a strictly greater `+0x60` | 17134, 26100.8115, .8521, .8972, .9444, .9549, Insider 29574 |
| `parse_supb` | `CmsVolume::ReadSuperBlock`, `ChooseSuperBlock`: the first valid copy, replaced only by a later one with a strictly higher `+0x68` when the chosen copy is not the primary | 17134, 26100.8115, .9444, .9549, Insider 29574 |
| `Translator` | `GetContainerIdFromRealRange`, `IsValidContainerLcn` | — |
| `_system_table_copy` | `MsCreateDurableFailoverTableObject`: both object records of a pair looked up, neither copy a primary | 26100.8115 |
| `iter_redo_blocks` and the record budget | `CmsRestarter::ForEachBlockInMergedBlock`, `CmsRestarter::ForEachRedoInBlock` | — |
| the opcode tables | `PerformRedo`'s dispatch | 17134, 26100.x, Insider |
| `mlog_tail_check` | `MlLogOpenLog` (a log begun after another), the wrap of the data area | 26100.9818 |
| `_parse_si_full` (`$SI+0x70`, the link count) | `RefsConvertToStandardInfoLinkCount` | — |

Each rule is a row of the project's claim register, with its static and on-disk evidence and, where the table says
"—", the builds it was read on; the corrections to the register are its errata (both are in the repository's
`analysis/` directory).

## How the rules are kept single

The verification harness (`analysis/verification/`) runs, besides the test suite and the golden outputs of every
command on every corpus image:

- `check_single_source.py`: each computed fact of the single-source table has exactly one definition, and no
  checkpoint clock is read, compared or sorted outside `checkpoint_select` (a few display sites are listed by name).
- `check_finding_reachability.py`: no failure counter is only printed; each one reaches the exit code.
- `check_content_hole_coverage.py`: every producer of output bytes goes through `content_holes`.
- `lint_silent_skips.py`: no exception handler drops work without recording it, beyond a pinned inventory.
- `longitudinal.py`: the tools of every tagged release (kept with their hashes, checked against the public
  repository) and the development tools are run on the public samples; every output change since the last tag must
  be announced by a row of `output_changes.tsv` that points to its changelog or migration entry, and every row
  must match a change.

## Changes in 1.14.0 that change how a result is reached

| What | Where | Why |
|---|---|---|
| One checkpoint selection for every command | `checkpoint_select` | the copies were ranked by more than one rule; now the driver's rule, once |
| The MLog's missing records counted in log blocks across generations | `mlog_tail_check` | a generation is not a lap: it also goes up when a log is begun anew at the same offset |
| A log with no record left is a finding, not "none missing" | `mlog_tail_check` | with no record the count started at the log start, which equals the log end on most volumes |
| Every walk verifies its object's root page | `walk_bplus`, `_OBJ_ROOT_BY_LCNS` | a walk that did not name its object read the root page unchecked: `files` printed an altered security entry |
| A split file's snapshots read from its backing record | `_t40_record_tuple`, `_split_snapshot_entry` | the driver keeps a hard-linked or moved file's snapshot rows in its backing; `snapshots` and `SnapshotCount` skipped them |
| A per-object bundle is refused as a volume | `_bundle_open`, `_bundle_per_object` | it holds each object's pages without their addresses and read back as a volume of 0 objects |
| The checkpoint's other root tables checked when the volume is opened | `_chkp_other_root_findings` | roots 1-4, 6, 9-11 and the Object Table's second copy were read without the check: an altered allocator root page went unnamed |
| A split file's record handed to every reader | `_analyze_dir_extents` (both branches) | `extract` read the name row, which holds no data rows: integrity was not verified and a split symlink's target not named |
| The checkpoint comparison names the newer copy and states the compared copy's conditions | `cmd_deleted`, `_copy_redundancy_conditions` | the comparison reads that copy |
| `chkp --verify` checks every checkpoint copy's self-checksum | refsanalysis `cmd_chkp` | a damaged copy not decoded went unsaid |
| Clusters without a CRC-32C counted by what their row says | `_verify_inline_integrity` | they are never-written runs, not unverified data |

The [changelog](../changelog.md) lists every change of the release, with the outputs it moved.
