# win11refs2tsnapshots — provenance

How this ReFS volume was created and populated. The populate, stream-snapshot, and unmount commands
are taken from the session PowerShell transcript (`transcript_testsnapshot.txt`) and were
cross-checked against the directories that actually exist on the image. This is the stream-snapshot
image in the set.

## Verified volume settings (read directly from the image)

| Property | Value |
|----------|-------|
| ReFS version | 3.14 |
| Cluster size | 4 KiB (page size 16 KiB) |
| Metadata checksum | CRC64 |
| Volume label | win11refs2tsnapshots |
| Nominal size | 2 TiB |

## 1. Partition & format

The format step itself was not captured in the transcript. A volume with the settings above is
produced by:

```powershell
New-Partition -DiskNumber 2 -UseMaximumSize -DriveLetter k
Format-Volume -DriveLetter k -FileSystem ReFS -NewFileSystemLabel "win11refs2tsnapshots" -Confirm:$false
Disable-BitLocker -MountPoint k   # Win11 auto-enables BitLocker; wait for full decryption
```

## 2. Populate (verified against the on-disk directories)

```powershell
# baseline replay  ->  creates  \test          (report: fsactivity_185150_replay_report.txt)
.\Generate-FSActivity.ps1 -ReplayFile C:\tools\fsactivity_baseline.json -RootDir K:\test\ -LogDir C:\tools\step3snapshotlogs
```

## 3. Stream snapshots (the feature this image showcases)

ReFS stream snapshots are point-in-time copies of a file's data stream, created with
`refsutil streamsnapshot`. The transcript creates a dedicated directory and exercises the full
create / list / query / delete cycle:

```powershell
mkdir k:\testsnapshots
"arg" | Set-Content K:\testsnapshots\arg.txt
cd K:\testsnapshots

refsutil streamsnapshot /c "test1" .\arg.txt     # create snapshot "test1"
refsutil streamsnapshot /l "*"     .\arg.txt     # list snapshots
# (arg.txt is then edited, so "test1" preserves the prior content)
refsutil streamsnapshot /q "test1" .\arg.txt     # query snapshot
refsutil streamsnapshot /d "test1" .\arg.txt     # delete snapshot "test1"
refsutil streamsnapshot /c "test2" .\arg.txt     # create snapshot "test2"
```

Snapshots were also taken on several files under `K:\test\` from the baseline replay. On the
resulting volume the tool reports **5 files carrying 10 stream snapshots**
(`refsanalysis/snapshots.txt`).

## 4. Unmount

```powershell
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 2 -AccessPath k:
Set-Disk -Number 2 -IsOffline $true
```

Per-run activity reports are in `provenance/fsactivity/`.
