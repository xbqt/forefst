# ReFS Concepts — Forensic Reference

This is the analyst's entry point to the *how-it-works* layer of the reference: the mechanisms, the
version history, and the forensic methodology that the byte-level [structure](../structures/README.md)
and [attribute](../attributes/README.md) pages assume. Where those two catalogs answer *"what does this
field hold?"*, the concept pages answer *"why is it shaped this way, what does it let me recover, and in
what order do I read it?"* If this is a fresh volume, start with the reading order in §3.

## 1. What ReFS forensics rests on

A handful of ideas recur on almost every page; carry them before opening any single one.

- **Every object is its own B+-tree.** A file, directory, or system table is reached by a 64-bit
  **Object ID (OID)** through the [Object Table](../structures/object_table.md); its metadata and
  [attributes](attributes.md) live in the rows of *that* tree, not in a central `$MFT`.
- **Addresses are virtual.** A cluster number in an extent or a table root is a VLCN — it must be
  translated to a physical cluster through the [Container Table](../structures/container_table.md). Skip
  the translation and you read the wrong sectors ([Virtual Addressing](virtual_addressing.md)).
- **Nothing is overwritten in place.** ReFS is [copy-on-write](copy_on_write.md): an update writes a new
  page and re-points its parent, leaving the old page intact until the allocator reuses it. This is why
  prior states survive ([Deletion Recovery](deletion_recovery.md), [What Survives](what_survives.md)).
- **Layouts are versioned.** Structure sizes and `$SI` layout change by ReFS version, checksum mode, and
  cluster size, so you must establish the version *first* ([Version Detection](version_detection.md)).
- **Identity is monotonic.** OIDs are never reused, so a gap in the sequence is permanent evidence of a
  past deletion ([OID Allocation](oid_allocation.md), [Object IDs and FileIds](object_ids_fileids.md)).

## 2. How these pages are organized

The reference has three page kinds. **Concept** pages (here) explain mechanism and method.
**[Structure](../structures/README.md)** pages give the on-disk byte layouts. **[Attribute](../attributes/README.md)**
pages give the typed metadata inside an object's row. A concept page links out to the structures and
attributes that embody it; follow those links when you need the exact offset.

Every page states its facts in clean prose and records its **evidence level and finding IDs** in a
`## Evidence` section; the per-claim provenance — which images,
which build — lives in the project's `analysis/` tree, reached through the finding ID. See
[how this was verified](../methodology.md).

## 3. Reading order for an analyst

A path that matches an actual investigation rather than the alphabet:

1. **Classify the volume.** [Version Detection](version_detection.md) → [Bootstrap Chain](bootstrap_chain.md)
   → [Architecture](architecture.md). Know the version and how to reach any table before parsing.
2. **Fix the addressing.** [Cluster and Page Size](cluster_page_size.md) and
   [Virtual Addressing](virtual_addressing.md) — so every later cluster number resolves correctly.
3. **Read the metadata.** [Attributes](attributes.md), [Object IDs and FileIds](object_ids_fileids.md),
   [Resident vs Non-Resident Storage](resident_storage.md) — what a file's record holds and where its
   content is.
4. **Build the timeline.** [Artifact Timeline](artifact_timeline.md) and
   [Timestomping Detection](timestomp_detection.md) — the MACB sources and how tampering shows.
5. **Recover.** [What Survives](what_survives.md) → [Deletion Recovery](deletion_recovery.md),
   [Snapshots and Versioning](snapshots_versioning.md), [Copy-on-Write](copy_on_write.md).
6. **Tie it together.** The [Forensic Analysis Workflow](forensic_analysis_workflow.md) is the end-to-end
   runbook; [Carrier Categories](carrier_categories.md) maps every artifact to a question;
   [Tool-to-Artifact Map](tool_artifact_map.md) names the command that surfaces each one.

## 4. The methodology in one place

Four pages carry the method rather than a mechanism: the end-to-end
[Forensic Analysis Workflow](forensic_analysis_workflow.md) (runbook), [Carrier Categories](carrier_categories.md)
(how the artifacts are organized), [What Survives](what_survives.md) (the delete/format/upgrade/crash
survival matrix), and [Tool-to-Artifact Map](tool_artifact_map.md) (goal → tool invocation). The
verification method behind every fact — the dual-evidence grading and how to trace a claim into
`analysis/` — is [How this was verified](../methodology.md).

## 5. The concept catalog

The 34 concept pages, grouped by what an investigation needs, each with what it is and why the analyst
cares.

### Background & cross-file-system context
| Page | What it is / why it matters |
|------|------------------------------|
| [File Systems](file_systems.md) | General file-system theory (allocation, links, consistency) — the vocabulary the rest assumes |
| [Windows File Systems](windows_file_systems.md) | The Windows I/O stack and driver model ReFS plugs into |
| [NTFS vs ReFS](ntfs_comparison.md) | The structural crosswalk for NTFS practitioners — and the reflexes that mislead (see §6) |

### Driver & on-disk architecture
| Page | What it is / why it matters |
|------|------------------------------|
| [Architecture](architecture.md) | The two-layer driver (Refs upper / Minstore lower) and the three-tier IRP dispatch |
| [Driver Interface](driver_architecture.md) | The static-analysis data sheet: imports, embedded codecs, class tables — *which features a build can produce* |
| [Bootstrap Chain](bootstrap_chain.md) | The fixed VBR → SUPB → CHKP → roots traversal every parse begins with |

### Versioning & upgrade state
| Page | What it is / why it matters |
|------|------------------------------|
| [Version Detection](version_detection.md) | The procedure to classify a volume's version and original-vs-upgraded state from CHKP flags |
| [Version Evolution](version_evolution.md) | The canonical record of what changed at each transition (v3.4 → Insider) |

### Addressing, layout & allocation
| Page | What it is / why it matters |
|------|------------------------------|
| [Cluster and Page Size](cluster_page_size.md) | The format-time 4 KiB vs 64 KiB choice that fixes page size and CPC |
| [Virtual Addressing](virtual_addressing.md) | The two-level VLCN → PLCN translation — the #1 thing an NTFS tool gets wrong |
| [Space Allocation](allocation_space_mgmt.md) | The three-tier bitmap allocator and the recently-deallocated carving window |

### Integrity, redundancy & crash consistency
| Page | What it is / why it matters |
|------|------------------------------|
| [Checksum Architecture](checksum_architecture.md) | The Merkle-tree metadata checksums (CRC64 / SHA-256) and when they are active |
| [Integrity Streams](integrity_streams.md) | Per-file opt-in block checksums (`file_attrs & 0x8000`) and how to detect them |
| [Redundancy](redundancy.md) | The boot-sector, superblock, and checkpoint copies a recovery can fall back to |
| [Transactions / Crash Consistency](transactions_crash_consistency.md) | Redo-only MLog + checkpoint atomicity — and why there are no undo pre-images |

### Identity & metadata
| Page | What it is / why it matters |
|------|------------------------------|
| [Attributes](attributes.md) | The two-layer attribute model: row types and the embedded sub-record chain |
| [Object IDs and FileIds](object_ids_fileids.md) | The cross-table join key — OID vs the per-directory ordinal |
| [OID Allocation](oid_allocation.md) | The monotonic counter; why gaps are permanent deletion evidence |

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
| [Tool-to-Artifact Map](tool_artifact_map.md) | For each forensic goal, the `forefst.py` / `refsanalysis.py` invocation that surfaces it |
| [Artifact Timeline](artifact_timeline.md) | The timestamp sources and how to build a super-timeline |
| [Timestomping Detection](timestomp_detection.md) | Multi-source tamper detection (`$SI` change-time + USN + volume-creation bound) |

### Special features
| Page | What it is / why it matters |
|------|------------------------------|
| [Hard Links](hard_links.md) | Multi-name files: the shared FileId, and why `$SI+0x70` is a decoy counter |
| [Resident vs Non-Resident Storage](resident_storage.md) | The inline-vs-extent threshold — why small-file content hides in the metadata tree |
| [Compression](compression.md) | Per-container 24H2 volume compression (not the NTFS per-file model) |
| [Tiered Storage](tiering.md) | Fast/slow tier relocation and the heat engine |
| [WSL / Linux Metadata](wsl_metadata.md) | The `$LX*` EAs and `LX_*` reparse tags — high-confidence evidence of WSL use |

## 6. Concepts that diverge from NTFS reflexes

The habits that mislead an NTFS-trained analyst on ReFS, and where the correct model lives:

- **No flat metadata table.** There is no `$MFT` to scan — reach an object through the
  [Object Table](../structures/object_table.md) ([Attributes](attributes.md)).
- **Cluster numbers are virtual.** A VLCN is not a disk offset; translate it
  ([Virtual Addressing](virtual_addressing.md)).
- **Names are not a `$FILE_NAME` attribute.** They live in the directory-entry rows; there are no 8.3
  short names (see [attributes §4](../attributes/README.md)).
- **The resident threshold is far higher.** Far more files keep content inline
  ([Resident vs Non-Resident Storage](resident_storage.md)), so NTFS-calibrated carving under-counts.
- **The change journal is wider.** ReFS uses `USN_RECORD_V3` (128-bit file IDs), not V2
  ([USN Journal](../structures/usn_journal.md)).
- **Timestomping needs a different cross-check.** ReFS carries one `$SI` timestamp set *per name*, so a
  single-named file has no `$SI`-vs-`$FN` twin to compare — use the filesystem-controlled change-time plus
  the USN anchor. A *hard-linked* file, though, keeps an independent timestamp copy per name, and a
  name-scoped timestomp leaves the sibling names at the true birth; comparing a file's names' MACB is thus a
  ReFS-specific tamper check — journal-independent, and stronger than NTFS's `$SI`-vs-`$FN`, where all hard
  links share one `$SI` ([Timestomping Detection](timestomp_detection.md)).
- **The log has no undo.** MLog is redo-only — prior states come from dereferenced CoW pages, not a
  backward log scan ([Copy-on-Write](copy_on_write.md), [NTFS vs ReFS](ntfs_comparison.md)).

## Evidence and verification

Every concept here is grounded in the same dual evidence as the rest of the reference — the decompiled
`refs.sys` driver (`E2`) and the raw-disk corpus (`RD`) — and each page records the specific findings and
errata that back it in its `## Evidence` section. See
[how this was verified](../methodology.md) for the methodology, the evidence levels, and how to trace any
claim to the exact images and measurements in the project's `analysis/` tree.
