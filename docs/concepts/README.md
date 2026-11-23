# ReFS Concepts — Forensic Reference

This is the analyst's entry point to the *how-it-works* layer of the reference: the mechanisms, the
version history, and the forensic methodology that the byte-level [structure](../structures/README.md)
and [attribute](../attributes/README.md) pages assume.

Those two catalogs say what each field holds. The concept pages explain why a structure is laid out as it is, what
it lets an analyst recover, and in what order to read it.

New to ReFS forensics? Start with the example **[A first examination](../examples/first_examination.md)**:
the short version, with what `forefst` shows at each step. Then the reading order in §3.

## 1. Five ideas behind every page

Five ideas recur on almost every page; learn them before reading any single page.

- **Every directory is its own B+-tree.** A directory or system table is reached by a 64-bit
  **Object ID (OID)** through the [Object Table](../structures/object_table.md); its metadata and
  [attributes](attributes.md) live in the rows of *that* tree, not in a central `$MFT`. **A file has no
  OID or tree of its own** — it is a set of rows inside a directory's tree, reached by path.
- **Addresses are virtual.** A cluster number in an extent or a table root is a VLCN — it must be
  translated to a physical cluster through the [Container Table](../structures/container_table.md). Skip
  the translation and you read the wrong sectors ([Virtual Addressing](virtual_addressing.md)).
- **Metadata pages are not overwritten in place.** ReFS is [copy-on-write](copy_on_write.md): an update of a
  B+-tree page writes a new page and re-points its parent, leaving the old page intact until the allocator reuses
  it. This is why prior states survive ([Deletion Recovery](deletion_recovery.md),
  [What Survives](what_survives.md)). The superblocks, the two checkpoint slots, the log and the change journal are
  rewritten in place.
- **Layouts are versioned.** Structure sizes and `$SI` layout change by ReFS version, checksum mode, and
  cluster size, so you must establish the version *first* ([Version Detection](version_detection.md)).
- **Identity is monotonic.** each new OID is above every live one, and none below the highest one in use is reused, so a
  gap in the sequence shows a directory that was deleted, or a creation that failed; files draw no OID
  ([OID Allocation](oid_allocation.md), [Object IDs](object_ids.md)).

## 2. How these pages are organized

The reference has three page kinds. **Concept** pages (here) explain mechanism and method.
**[Structure](../structures/README.md)** pages give the on-disk byte layouts. **[Attribute](../attributes/README.md)**
pages give the typed metadata inside an object's row. A concept page links out to the structures and
attributes that implement it; follow those links when you need the exact offset.

Every page states its facts in clean prose and records the evidence behind them in a `## Evidence` section (its
register rows are named in a comment of the page source); the per-claim provenance — which images, which build —
lives in the project's `analysis/` tree, reached through those rows.

See [how this was verified](../methodology.md).

## 3. Reading order for an analyst

A path that matches an actual investigation rather than the alphabet:

0. **Start here.** [A first examination](../examples/first_examination.md) is the short version of
   the steps below, as a worked example;
   [What ReFS Is](what_is_refs.md) says what the file system is for and why Microsoft built it.
1. **Classify the volume.** [Version Detection](version_detection.md) → [Bootstrap Chain](bootstrap_chain.md)
   → [Architecture](architecture.md). Know the version and how to reach any table before parsing.
2. **Fix the addressing.** [Cluster and Page Size](cluster_page_size.md) and
   [Virtual Addressing](virtual_addressing.md) — so every later cluster number resolves correctly.
3. **Read the metadata.** [Attributes](attributes.md), [Object IDs](object_ids.md), [File IDs](file_ids.md),
   [Record placement and data residency](placement_and_residency.md) — what a file's record holds and where its
   content is.
4. **Build the timeline.** [Artifact Timeline](artifact_timeline.md) and
   [Timestomping Detection](timestomp_detection.md) — the MACB sources and how tampering shows.
5. **Recover.** [What Survives](what_survives.md) → [Deletion Recovery](deletion_recovery.md),
   [Snapshots and Versioning](snapshots_versioning.md), [Copy-on-Write](copy_on_write.md).
6. **Tie it together.** The [Forensic Analysis Workflow](forensic_analysis_workflow.md) is the end-to-end
   runbook; [Carrier Categories](carrier_categories.md) maps every artifact to a question;
   [Tool-to-Artifact Map](../tools/tool_artifact_map.md) names the command that surfaces each one.

## 4. The methodology in one place

Four pages describe the method rather than a mechanism: the end-to-end
[Forensic Analysis Workflow](forensic_analysis_workflow.md) (runbook), [Carrier Categories](carrier_categories.md)
(how the artifacts are organized), [What Survives](what_survives.md) (the delete/format/upgrade/crash
survival matrix), and [Tool-to-Artifact Map](../tools/tool_artifact_map.md) (goal → tool invocation). The
verification method behind every fact — the dual-evidence grading and how to trace a claim into
`analysis/` — is [How this was verified](../methodology.md).

## 5. The concept catalog

The 39 concept pages, grouped by what an investigation needs, each with what it is and why the analyst
cares.

### Background & cross-file-system context
| Page | What it is / why it matters |
|------|------------------------------|
| [File Systems](file_systems.md) | General file-system theory (allocation, links, consistency) — the vocabulary the rest assumes |
| [Windows File Systems](windows_file_systems.md) | The Windows I/O stack and driver model ReFS plugs into |
| [What ReFS Is](what_is_refs.md) | What ReFS is for, why Microsoft built it, what it left out and gained, where it is used, and how it compares with ZFS, Btrfs and APFS |
| [NTFS vs ReFS](ntfs_comparison.md) | The structural crosswalk for NTFS practitioners, and the NTFS habits that mislead on ReFS (see §6) |

### Driver & on-disk architecture
| Page | What it is / why it matters |
|------|------------------------------|
| [Architecture](architecture.md) | The two-layer driver (Refs upper / Minstore lower) and the three-tier IRP dispatch |
| [Driver Interface](driver_architecture.md) | The static-analysis data sheet: imports, embedded codecs, class tables — *which features a build can produce* |
| [Driver Evolution](driver_evolution.md) | What changed between the `refs.sys` builds read (across the 26100 builds the on-disk format does not change), and the driver functions that change a file's storage, per build, with the on-disk witness for each; the builds themselves are listed on [Driver builds analysed](../methodology/driver_builds.md) |
| [Bootstrap Chain](bootstrap_chain.md) | The fixed VBR → SUPB → CHKP → roots traversal every parse begins with |

### Versioning & upgrade state
| Page | What it is / why it matters |
|------|------------------------------|
| [Version Detection](version_detection.md) | The procedure to classify a volume's version and original-vs-upgraded state from the VBR fields and CHKP flags |
| [Version Evolution](version_evolution.md) | The canonical record of what changed at each transition (v3.4 → Insider) |

### Addressing, layout & allocation
| Page | What it is / why it matters |
|------|------------------------------|
| [Cluster and Page Size](cluster_page_size.md) | The format-time 4 KiB vs 64 KiB choice that fixes page size and CPC |
| [Virtual Addressing](virtual_addressing.md) | The two-level VLCN → PLCN translation — a step an NTFS tool does not make |
| [Space Allocation](allocation_space_mgmt.md) | The three-tier bitmap allocator and the recently-deallocated carving window |

### Integrity, redundancy & crash consistency
| Page | What it is / why it matters |
|------|------------------------------|
| [Checksum Architecture](checksum_architecture.md) | The Merkle-tree metadata checksums (CRC64 / SHA-256) and when they are active |
| [Integrity Streams](integrity_streams.md) | Per-file opt-in block checksums (file attribute `0x8000`, `IntegrityStream`) and how to detect them |
| [Redundancy](redundancy.md) | The boot-sector, superblock, and checkpoint copies a recovery can fall back to |
| [Transactions / Crash Consistency](transactions_crash_consistency.md) | Redo-only MLog + checkpoint atomicity — and why there are no undo pre-images |

### Identity & metadata
| Page | What it is / why it matters |
|------|------------------------------|
| [Attributes](attributes.md) | The two-layer attribute model: row types and the embedded sub-record chain |
| [Object IDs](object_ids.md) | The volume-wide 64-bit directory identity — the reliable cross-table join key |
| [File IDs](file_ids.md) | How a file is identified: the FileRef = creation-directory OID + per-directory ordinal |
| [OID Allocation](oid_allocation.md) | The monotonic counter; why a gap shows a deleted directory or a failed creation |

### Copy-on-write, recovery & survivability
| Page | What it is / why it matters |
|------|------------------------------|
| [Copy-on-Write](copy_on_write.md) | The fundamental update model and the prior-page recovery it enables |
| [Deletion Recovery](deletion_recovery.md) | The recovery methods: Trash Table, checkpoint differential, orphan scan, CoW prior-content, node-slack carve |
| [Snapshots and Versioning](snapshots_versioning.md) | `$SNAPSHOT` stream snapshots and deterministic prior-content recovery |
| [What Survives](what_survives.md) | The artifact-vs-event survival matrix (delete / format / upgrade / unmount / crash) |
| [Deduplication](deduplication.md) | Opt-in post-process block sharing and its refcount footprint |

### Forensic methodology & timelines
| Page | What it is / why it matters |
|------|------------------------------|
| [Forensic Analysis Workflow](forensic_analysis_workflow.md) | The end-to-end runbook from image to findings |
| [Carrier Categories](carrier_categories.md) | Carrier's five data categories mapped onto ReFS structures |
| [Artifact Timeline](artifact_timeline.md) | The timestamp sources and how to build a super-timeline |
| [Timestomping Detection](timestomp_detection.md) | Multi-source tamper detection (`$SI` change-time + USN + volume-creation floor) |

### Special features
| Page | What it is / why it matters |
|------|------------------------------|
| [Hard Links](hard_links.md) | Multi-name files: the shared FileId, and where `$SI+0x70` holds the count (the backing, not the name row) |
| [Record placement and data residency](placement_and_residency.md) | Where a file's record is stored (embedded in its name row, or split into a backing record) and where its bytes are (inline in the record, or in extents): the rules, seven measured examples and the byte-level detail |
| [Compression](compression.md) | Per-container volume compression (not the NTFS per-file model) |
| [Tiered Storage](tiering.md) | Fast/slow tier relocation and the heat engine |
| [WSL / Linux Metadata](wsl_metadata.md) | The `$LX*` EAs and `LX_*` reparse tags, evidence of WSL use |

## 6. Where NTFS habits mislead

The habits that mislead an NTFS-trained analyst on ReFS, and where the correct model lives:

- **No flat metadata table.** There is no `$MFT` to scan — reach an object through the
  [Object Table](../structures/object_table.md) ([Attributes](attributes.md)).
- **Cluster numbers are virtual.** A VLCN is not a disk offset; translate it
  ([Virtual Addressing](virtual_addressing.md)).
- **Names are not a `$FILE_NAME` attribute.** They live in the directory-entry rows; there are no 8.3
  short names (see [attributes §4](../attributes/README.md)).
- **Small files keep their data in the record.** On a volume at format 3.11 or later a file's data written while
  it is under 2 KiB stays inline unless a conversion trigger fires, so a carver that expects every file's data in
  clusters misses it (below 3.11 the main data is always in extents)
  ([Record placement and data residency](placement_and_residency.md)).
- **The change journal is wider.** ReFS uses `USN_RECORD_V3` (128-bit file IDs), not V2
  ([USN Journal](../structures/usn_journal.md)).
- **Timestomping needs a different cross-check.** ReFS keeps one `$SI` timestamp set per file, in its record, and
  a cached copy in each name's index entry; there is no `$SI`-vs-`$FILE_NAME` twin to compare — use the
  filesystem-controlled change-time plus the USN journal.

  On a *hard-linked* file the names' cached copies can diverge (as each NTFS link's `$FILE_NAME` times can). The
  file's own record takes the new time for every name at once; what diverges is each name's index entry, a cache
  refreshed when the file is opened, read or closed through that name (a directory listing does not refresh it).
  A divergence of the names' Created times is evidence (their Changed times diverge routinely: a hard link added
  later carries the time it was added); equal Created times do not show that the file was not stomped, and opening the file through another name erases
  the difference
  ([Timestomping Detection](timestomp_detection.md)).
- **The log has no undo.** MLog is redo-only — it holds no pre-images; prior states come from dereferenced CoW
  pages, and older redo records still in the log keep earlier values ([Copy-on-Write](copy_on_write.md),
  [NTFS vs ReFS](ntfs_comparison.md)).

## Evidence and verification

Every concept here is checked the same way as the rest of the reference — against the decompiled `refs.sys`
driver and the disk corpus, wherever both can be read — and each page records the evidence that backs it in its
`## Evidence` section.

See [how this was verified](../methodology.md) for the methodology, the evidence levels, and how to trace any
claim to the exact images and measurements in the project's `analysis/` tree.
