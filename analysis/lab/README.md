# ReFS Lab — generating disk images for testing

This directory is the harness for producing **reproducible ReFS disk images**: real volumes created on
Windows VMs, populated with controlled file-system activity, then detached as raw images you can parse
on the host with `forefst.py` / `refsanalysis.py`. Every sample and corpus image in this repo was made
this way.

Why VMs at all: since Windows 10 version 1709, only the **Enterprise** and **Pro for Workstations** editions of
Windows 10 and 11, and **Windows Server**, can *format* a ReFS volume (a Dev Drive aside); the other editions read and
write existing ones; the lab's VMs and their editions are in [`vm_setup.md`](vm_setup.md). Different Windows builds
emit different ReFS versions (3.4 → 3.14+), which is how the version-evolution corpus was captured.

## Files here

| File | What it gives you |
|------|-------------------|
| [`vm_setup.md`](vm_setup.md) | The Windows VMs (Win10 1803 = v3.4, Win11 24H2 = v3.14, Insider 29574 = v3.14+, plus 21H2/22H2/23H2 for v3.7/3.9/3.10) and the QEMU/libvirt config |
| [`disk_generation.md`](disk_generation.md) | The full create → format → populate → unmount → analyze procedure, **including every format variant** (64 KiB clusters, SHA-256, integrity streams, the Win10→Win11 upgrade, …) |
| [`Generate-FSActivity.ps1`](Generate-FSActivity.ps1) | The activity generator (v3.20): creates files/dirs/hard links/symlinks/ADS, renames, moves, deletes, sets timestamps — reproducibly |
| [`Generate-FSActivity_documentation.md`](Generate-FSActivity_documentation.md) | Every `Generate-FSActivity.ps1` parameter, the 16 action types, and the report/log format |
| [`fsactivity_baseline.json`](fsactivity_baseline.json) | The **frozen baseline** action set (schema 3.16, seed 153524984, 1000 actions) — replay it to put the *identical* tree on every disk |
| [`Inventory_RefsVolume.ps1`](Inventory_RefsVolume.ps1) | The ground truth of a volume, as Windows reports it (v2.1): run it last, before imaging — see [below](#before-imaging-record-the-ground-truth-inventory_refsvolumeps1) |
| [`powershell_commands.md`](powershell_commands.md) | Quick copy-paste reference for the host + guest commands |

## End-to-end: make a test image

Full detail (and all format options) is in [`disk_generation.md`](disk_generation.md); the essential path:

```bash
# 1. HOST — create a raw image and attach it to a running VM
qemu-img create -f raw /mnt/usb/disks/mytest.raw 8G
virsh attach-disk win11 /mnt/usb/disks/mytest.raw sdr --targetbus virtio --driver qemu --subdriver raw
```

```powershell
# 2. GUEST (PowerShell as Administrator) — initialize, format ReFS, clear BitLocker
Initialize-Disk -Number 1 -PartitionStyle GPT
New-Partition -DiskNumber 1 -UseMaximumSize -DriveLetter H
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "mytest" -Confirm:$false
Disable-BitLocker -MountPoint H        # if Get-BitLockerVolume shows it on; WAIT for VolumeStatus = FullyDecrypted

# 3. GUEST — populate. Either replay the frozen baseline (identical tree everywhere):
.\Generate-FSActivity.ps1 -ReplayFile .\fsactivity_baseline.json -RootDir H:\test -LogDir H:\logs
#    …or generate a fresh, seed-reproducible run:
.\Generate-FSActivity.ps1 -RootDir H:\test -Count 1000 -Seed 12345 -LogDir H:\logs
#    add -HeavySpcials for many hard links / symlinks / ADS (see the docs for all switches)

# 4. GUEST — record the ground truth, the last step before imaging (see below)
.\Inventory_RefsVolume.ps1 -Drive H -Label mytest

# 5. GUEST — unmount cleanly (both steps matter, or the volume is left dirty)
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath H:
Set-Disk -Number 1 -IsOffline $true
```

```bash
# 6. HOST — detach and analyze
virsh detach-disk win11 sdr
python3 forefst.py      /mnt/usb/disks/mytest.raw summary
python3 refsanalysis.py /mnt/usb/disks/mytest.raw boot -vv
```

## Before imaging: record the ground truth (`Inventory_RefsVolume.ps1`)

[`Inventory_RefsVolume.ps1`](Inventory_RefsVolume.ps1) (v2.1) records what Windows itself reports about every file
and directory of a mounted volume: an answer key the tools did not produce, to compare their output with.

**When:** as the last step of every lab and before every acquisition. After it, take the disk offline and image it,
with nothing in between.

**How:** in an **elevated Windows PowerShell 5.1** console (the script stops without administrator rights; it is pure
ASCII, which 5.1's parser needs):

```powershell
.\Inventory_RefsVolume.ps1 -Drive H -Label mytest
.\Inventory_RefsVolume.ps1 -Drive H -Label mytest -Journal -Security -Snapshots    # the optional outputs too
```

It writes to `<OutRoot>\<Label>_<yyyyMMdd_HHmmss>\` (`-OutRoot` is `C:\testrefs\inventory` by default) and stops
when that folder exists already or lies on the inventoried volume. `-ExcludeDir` leaves directories out of the walk.

**What it records:**

- `inventory.csv` — one row per entry, the root included as `.`: path, kind, size, allocation, the four times (UTC,
  to 100 ns, in the tools' form `2026-05-16T16:55:20.9805996Z`), attributes, reparse tag, the 128-bit file id (as
  `fsutil` prints it), volume serial number, link count, number of named streams, a file's SHA-256, and the Win32
  error of a query that failed.
- `streams.csv` — every named data stream of a file or a directory, with its length and SHA-256.
- `hardlinks.csv` — every name of every file with more than one link (`fsutil hardlink list`).
- `reparse.txt` — `fsutil reparsepoint query` for every entry with a reparse tag.
- `volume.txt` — the host, the Windows build, the `refs.sys` version and SHA-256, the time zone, the disk and
  partition geometry, `fsutil fsinfo refsinfo` and `volumeinfo`, `fsutil usn queryjournal`, the last-access policy
  and the BitLocker state.
- With `-Journal`, `journal.csv`: Windows' own decode of the change journal (`fsutil usn readjournal`). With
  `-Security`, `security.csv`: the owner and SDDL of every entry. With `-Snapshots`, `snapshots.csv`:
  `refsutil streamsnapshot /l "*"` for every file (slow).
- `errors.txt` (everything that could not be read), `transcript.txt` (the console) and `SHA256SUMS.txt` over every
  output file.

**What to know:**

- It reads every entry's metadata first, then the journal, then content, because reading content can touch a
  last-access time.
- Directory junctions and directory symbolic links are listed, never entered.
- An encrypted file is hashed only for a user who holds its key; otherwise `errors.txt` says so.
- When the volume is BitLocker-encrypted or being encrypted, it warns (on the console and in `errors.txt`) and goes
  on: an image of that disk will be encrypted. The lab's Windows 11 VM has encrypted a lab disk by itself while the
  disk was attached read-write.
- `-CopyToVolume` copies the output onto the inventoried volume afterwards. That changes the volume after the
  inventory: never use it for an image meant as a reference or as evidence.

## Targeting a specific feature

- **A different ReFS version** → format on the matching VM (see [`vm_setup.md`](vm_setup.md)): 21H2→3.7,
  22H2→3.9, 23H2→3.10, 24H2/Insider→3.14. The Win10→Win11 *upgrade* (v3.4 → v3.14) is in
  [`disk_generation.md`](disk_generation.md).
- **Format knobs** (all in `disk_generation.md`): `-AllocationUnitSize 64KB`, `-SHA256Checksums`,
  `-SetIntegrityStreams 1`, `-DisableHeatGathering`, `-NoTrim`.
- **Special artefacts / USN journal / snapshots** → `Generate-FSActivity.ps1 -HeavySpcials`,
  `fsutil usn createjournal … <vol>`, `refsutil streamsnapshot /c "<name>" <file>` (list them with
  `refsutil streamsnapshot /l "*" <file>`). Worked examples of each are in the per-image `provenance/commands.md`
  files under [`../samples/disks/`](../samples/).

## Reproducibility notes

- **Three volume states** the tools distinguish: original (CHKP flags `0x002`), upgraded (`0x602`),
  native v3.14 (`0x682`). The boot-sector fields `0x2A` (checksum selector) and `0x48` (Extended GUID) are set at
  format and kept their values across the corpus's two upgrades (3.4 → 3.14 and 3.9 → 3.14); `0x2C` (the volume
  flags) is written by the driver at run time.
- `Generate-FSActivity.ps1` writes a CSV log + a summary report per run; the report records the seed,
  so a `-Seed`/`-ReplayFile` run is fully reproducible. Keep those logs as the run's provenance.
- ReFS data is mostly sparse — `cp --sparse=always` (or `qemu-img convert`) before/after snapshots to
  capture upgrade or activity deltas without copying the whole nominal size.
