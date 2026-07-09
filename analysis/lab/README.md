# ReFS Lab — generating disk images for testing

This directory is the harness for producing **reproducible ReFS disk images**: real volumes created on
Windows VMs, populated with controlled file-system activity, then detached as raw images you can parse
on the host with `forefst.py` / `refsanalysis.py`. Every sample and corpus image in this repo was made
this way.

Why VMs at all: ReFS can only be *formatted* by Windows 10/11 **Pro for Workstations** or **Server**
editions — standard Pro/Home cannot. Different Windows builds emit different ReFS versions (3.4 → 3.14+),
which is how the version-evolution corpus was captured.

## Files here

| File | What it gives you |
|------|-------------------|
| [`vm_setup.md`](vm_setup.md) | The Windows VMs (Win10 1803 = v3.4, Win11 24H2 = v3.14, Insider 29574 = v3.14+, plus 21H2/22H2/23H2 for v3.7/3.9/3.10) and the QEMU/libvirt config |
| [`disk_generation.md`](disk_generation.md) | The full create → format → populate → unmount → analyze procedure, **including every format variant** (64 KiB clusters, SHA-256, integrity streams, the Win10→Win11 upgrade, …) |
| [`Generate-FSActivity.ps1`](Generate-FSActivity.ps1) | The activity generator (v3.20): creates files/dirs/hard links/symlinks/ADS, renames, moves, deletes, sets timestamps — reproducibly |
| [`Generate-FSActivity_documentation.md`](Generate-FSActivity_documentation.md) | Every `Generate-FSActivity.ps1` parameter, the 16 action types, and the report/log format |
| [`fsactivity_baseline.json`](fsactivity_baseline.json) | The **frozen baseline** action set (schema 3.16, seed 153524984, 1000 actions) — replay it to put the *identical* tree on every disk |
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
Disable-BitLocker -MountPoint H        # Win11 auto-enables it; WAIT for VolumeStatus = FullyDecrypted

# 3. GUEST — populate. Either replay the frozen baseline (identical tree everywhere):
.\Generate-FSActivity.ps1 -ReplayFile .\fsactivity_baseline.json -RootDir H:\test -LogDir H:\logs
#    …or generate a fresh, seed-reproducible run:
.\Generate-FSActivity.ps1 -RootDir H:\test -Count 1000 -Seed 12345 -LogDir H:\logs
#    add -HeavySpcials for many hard links / symlinks / ADS (see the docs for all switches)

# 4. GUEST — unmount cleanly (both steps matter, or the volume is left dirty)
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath H:
Set-Disk -Number 1 -IsOffline $true
```

```bash
# 5. HOST — detach and analyze
virsh detach-disk win11 sdr
python3 forefst.py      /mnt/usb/disks/mytest.raw --summary-plus
python3 refsanalysis.py /mnt/usb/disks/mytest.raw boot -vv
```

## Targeting a specific feature

- **A different ReFS version** → format on the matching VM (see [`vm_setup.md`](vm_setup.md)): 21H2→3.7,
  22H2→3.9, 23H2→3.10, 24H2/Insider→3.14. The Win10→Win11 *upgrade* (v3.4 → v3.14, format-time fields
  frozen) is in [`disk_generation.md`](disk_generation.md).
- **Format knobs** (all in `disk_generation.md`): `-AllocationUnitSize 64KB`, `-SHA256Checksums`,
  `-SetIntegrityStreams 1`, `-DisableHeatGathering`, `-NoTrim`.
- **Special artefacts / USN journal / snapshots** → `Generate-FSActivity.ps1 -HeavySpcials`,
  `fsutil usn createjournal … <vol>`, `refsutil streamsnapshot /c …`. Worked examples of each are in the
  per-image `provenance/commands.md` files under [`../samples/disks/`](../samples/).

## Reproducibility notes

- **Three volume states** the tools distinguish: original (CHKP flags `0x002`), upgraded (`0x602`),
  native v3.14 (`0x682`). Format-time VBR fields at `0x2A`/`0x2C`/`0x48` are never touched by an upgrade.
- `Generate-FSActivity.ps1` writes a CSV log + a summary report per run; the report records the seed,
  so a `-Seed`/`-ReplayFile` run is fully reproducible. Keep those logs as the run's provenance.
- ReFS data is mostly sparse — `cp --sparse=always` (or `qemu-img convert`) before/after snapshots to
  capture upgrade or activity deltas without copying the whole nominal size.
