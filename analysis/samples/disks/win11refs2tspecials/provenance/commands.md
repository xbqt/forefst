# win11refs2tspecials — provenance

How this ReFS volume was created and populated. The populate and unmount commands are taken
verbatim from the session PowerShell transcript (`transcript_step3-4.txt` / `transcript_step3-4b.txt`)
and were cross-checked against the directories that actually exist on the image.

## Verified volume settings (read directly from the image)

| Property | Value |
|----------|-------|
| ReFS version | 3.14 |
| Cluster size | 4 KiB (page size 16 KiB) |
| Metadata checksum | CRC64 |
| Volume label | win11refs2tspecials |
| Nominal size | 2 TiB |

## 1. Partition & format

The format step itself was not captured in the transcript. A volume with the settings above is
produced by:

```powershell
New-Partition -DiskNumber 3 -UseMaximumSize -DriveLetter j
Format-Volume -DriveLetter j -FileSystem ReFS -NewFileSystemLabel "win11refs2tspecials" -Confirm:$false
Disable-BitLocker -MountPoint j   # Win11 auto-enables BitLocker; wait for full decryption
```

## 2. Populate (verified against the on-disk directories)

```powershell
# baseline replay  ->  creates  \test          (report: fsactivity_184125_replay_report.txt)
.\Generate-FSActivity.ps1 -ReplayFile C:\tools\fsactivity_baseline.json -RootDir J:\test\ -LogDir C:\tools\step3logs

# heavy special-artefact runs  ->  create  \testspecials  and  \testspecials2
#   reports: fsactivity_183426_report.txt , fsactivity_183742_report.txt
#   The session invoked the Generate-FSActivitySpecials.ps1 variant; that behaviour is now part of
#   the lab's unified Generate-FSActivity.ps1 (v3.20) as the -HeavySpcials switch.
.\Generate-FSActivity.ps1 -Count 1000 -RootDir j:\testspecials  -HeavySpcials -SpecialEveryN 25 -LogDir C:\tools\step3logs
.\Generate-FSActivity.ps1 -Count 1000 -RootDir j:\testspecials2 -HeavySpcials -SpecialEveryN 25 -LogDir C:\tools\step3logs
```

These runs produce the special artefacts this image showcases — hard links, symbolic links, and
alternate data streams. On the resulting volume the tool reports 109 ADS on 76 files
(`refsanalysis/snapshots.txt`) plus the hard links and symlinks counted in the
fsactivity reports.

## 3. Unmount

```powershell
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 3 -AccessPath j:
Set-Disk -Number 3 -IsOffline $true
```

Per-run activity reports are in `provenance/fsactivity/` (one per `Generate-FSActivity` run that
shaped this volume). The other drives mounted during the same session wrote to different disks and
are not part of this image.
