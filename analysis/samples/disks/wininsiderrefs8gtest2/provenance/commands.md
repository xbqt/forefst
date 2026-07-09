# wininsiderrefs8gtest2 — provenance

How this ReFS volume was created and populated. The populate and unmount commands are taken from the
session PowerShell transcript (`transcript_wininsider.txt`) and were cross-checked against the
directories that actually exist on the image. This volume was created under a Windows Insider Server
build (29574).

## Verified volume settings (read directly from the image)

| Property | Value |
|----------|-------|
| ReFS version | 3.14 |
| Cluster size | 64 KiB (page size 64 KiB) |
| Metadata checksum | SHA-256 |
| Volume label | wininsiderrefs8gtest2 |
| Nominal size | 8 GiB |

This is the format-variant image in the set: 64 KiB clusters **and** SHA-256 metadata checksums
(both grow container-table rows to 224 bytes and change page-reference sizing).

## 1. Partition & format

The format step itself was not captured in the transcript. A volume with the settings above is
produced by:

```powershell
New-Partition -DiskNumber 1 -UseMaximumSize -DriveLetter R
Format-Volume -DriveLetter R -FileSystem ReFS -NewFileSystemLabel "wininsiderrefs8gtest2" `
  -AllocationUnitSize 64KB -SHA256Checksums -Confirm:$false
# Insider Server does not auto-enable BitLocker on data volumes — no Disable-BitLocker needed.
```

## 2. Populate (verified against the on-disk directories)

```powershell
# heavy special-artefact runs  ->  \testspecials   (reports: fsactivity_124238_report.txt , fsactivity_125727_report.txt)
.\Generate-FSActivity.ps1 -Count 1000 -SpecialEveryN 25 -HeavySpcials -LargeFileSizeMB 64,65,66,133 `
  -RootDir r:\testspecials -LogDir c:\tools\log

# baseline replay into the integrity directory  ->  \testintegrity
#   (reports: fsactivity_124641_replay_report.txt , fsactivity_130051_replay_report.txt)
.\Generate-FSActivity.ps1 -ReplayFile .\fsactivity_baseline.json -RootDir r:\testintegrity\ -LogDir c:\tools\log

# turn on integrity streams for that directory (per-file CRC data checksums)
Set-FileIntegrity r:\testintegrity\ -Enable $true
```

## 3. Unmount

```powershell
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath R:
Set-Disk -Number 1 -IsOffline $true
```

Per-run activity reports are in `provenance/fsactivity/`. The image reflects the state after the
`r:` session above; a later run that wrote to a `q:`-mounted volume
(`…aftermountedwithinsider`) is **not** present on this image, and two baseline-replay runs with no
`-RootDir` replayed to `C:\` rather than this volume — none of those are included here.
