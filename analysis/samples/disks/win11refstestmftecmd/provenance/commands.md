# win11refstestmftecmd — provenance

How this ReFS volume was created, how its USN change journal was enabled, and how the journal was
exported. Commands are from the session transcript (`logmftecmdtest/mftecmdtest*.txt`) and
cross-checked against the directories on the image. This volume was the ReFS side of a cross-tool
journal test; an NTFS twin (`win11ntfstestmftecmd`, drive `m:`) was processed in parallel and is not
part of this image.

## Verified volume settings (read directly from the image)

| Property | Value |
|----------|-------|
| ReFS version | 3.14 |
| Cluster size | 4 KiB (page size 16 KiB) |
| Metadata checksum | CRC64 |
| Volume label | win11refstestmftecmd |
| Nominal size | 4 GiB |

## 1. Partition, format, and enable the USN journal

```powershell
New-Partition -DiskNumber 2 -UseMaximumSize -DriveLetter n
Format-Volume -DriveLetter n -FileSystem ReFS -NewFileSystemLabel "win11refstestmftecmd" -Confirm:$false
Disable-BitLocker -MountPoint n                       # Win11 auto-enables BitLocker; wait for full decryption
fsutil usn createjournal m=134217728 a=16777216 n:    # create the journal: 128 MiB max, 16 MiB allocation delta
```

## 2. Populate (verified against the on-disk directories)

Four baseline replays into separate roots — these generate the file-system activity the journal records:

```powershell
.\Generate-FSActivity.ps1 -ReplayFile C:\tools\fsactivity_baseline.json -RootDir n:\test\          # report: ..._093358_replay_report.txt
.\Generate-FSActivity.ps1 -ReplayFile C:\tools\fsactivity_baseline.json -RootDir n:\test2\         # ..._093844
.\Generate-FSActivity.ps1 -ReplayFile C:\tools\fsactivity_baseline.json -RootDir n:\testspecials   # ..._094415
.\Generate-FSActivity.ps1 -ReplayFile C:\tools\fsactivity_baseline.json -RootDir n:\testintegrity\ # ..._095346
```

## 3. Export the USN journal

```powershell
fsutil usn queryjournal n: > n_usnqueryfirst.txt
fsutil usn readjournal  n: > n_usnreadlast.txt        # -> provenance/usn_readjournal_export.txt
```

The export (`usn_readjournal_export.txt`, **9 367 records**) was read from the **live** volume; the
image's on-disk journal holds **6 805 records**. They are the **same journal**, both starting at
First USN 0 (no wrap), and they agree **record-for-record over USN 0–917 280 (exactly 6 805 records
on each side)**. The export's additional 2 562 records all lie *beyond* the image's last record
(USN 917 280 → Next USN 1 261 144) — file-system activity that post-dates this snapshot. So the count
difference is purely capture timing (the `.raw` is an earlier snapshot than the live `readjournal`
read), and the exact overlap validates the tool's journal parser against `fsutil`. Cross-check
against `refsanalysis/usn.txt`.

## 4. Unmount

```powershell
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 2 -AccessPath n:
Set-Disk -Number 2 -IsOffline $true
```

Per-run activity reports are in `provenance/fsactivity/`.
