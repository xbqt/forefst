# Disk Image Generation Procedures

## Overview

This document describes how to create ReFS disk images with specific configurations for analysis. The workflow is: create raw image on host, attach to VM, initialize/format inside Windows, populate with data, properly unmount, detach, and analyze on the host.

## Step 1: Create the Raw Image on the Linux Host

```bash
# Standard sizes
qemu-img create -f raw win11refs2g.raw 2G
qemu-img create -f raw win11refs8g.raw 8G
qemu-img create -f raw win11refs2t.raw 2T
qemu-img create -f raw win11refs15t.raw 15T
```

## Step 2: Attach to VM and Initialize

```bash
virsh attach-disk win11 /mnt/usb/disks/step2/win11refs8g.raw sdr \
 --targetbus virtio --driver qemu --subdriver raw
```

Inside the Windows guest (PowerShell as Administrator):

```powershell
# Find the new disk
Get-Disk

# Initialize with GPT
Initialize-Disk -Number 1 -PartitionStyle GPT

# Create partition using all space
New-Partition -DiskNumber 1 -UseMaximumSize -DriveLetter H
```

## Step 3: Format the Volume

### Basic ReFS (default settings)

```powershell
# Win10 (produces ReFS 3.4, no checksums)
Format-Volume -FileSystem ReFS -Confirm:$false -NewFileSystemLabel "win10refs8g" -DriveLetter H

# Win11 (produces ReFS 3.14, CRC64 metadata checksums)
Format-Volume -FileSystem ReFS -Confirm:$false -NewFileSystemLabel "win11refs8g" -DriveLetter H
```

### 64K Cluster Size

```powershell
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "win11refs15t64k" `
 -Confirm:$false -AllocationUnitSize 64KB
```

Cluster size affects: CPC (clusters per container: 16384 for 4K, 1024 for 64K), container table row size (224 bytes instead of 160), and address translation shift (14 for 4K, 10 for 64K). Container size remains 64 MiB regardless.

### SHA256 Checksums (instead of default CRC64)

```powershell
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "sha256checksums" `
 -Confirm:$false -SHA256Checksums
```

Increases page reference size from 0x30 to 0x48 bytes (24 extra bytes for SHA-256 hash). Container table rows grow to 224 bytes.

### Integrity Streams

```powershell
# Integrity streams OFF (explicit)
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "setintegritystreams0" `
 -Confirm:$false -SetIntegrityStreams 0

# Integrity streams ON (enables per-file CRC32 data checksums)
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "setintegritystreams1" `
 -Confirm:$false -SetIntegrityStreams 1
```

When integrity streams are ON, Data Checksum Type becomes CRC32. Without this flag, file data is never checksummed regardless of metadata checksum settings.

### Other Format Options

```powershell
# Disable heat gathering (tiering)
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "disableheatgathering" `
 -Confirm:$false -DisableHeatGathering

# Disable TRIM
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "notrim" `
 -Confirm:$false -NoTrim
```

### Combined Configurations

64K clusters + SHA256 both independently produce 224-byte container table rows. They do not stack to a third format:

```powershell
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "win11refs2t64ksha256" `
 -Confirm:$false -AllocationUnitSize 64KB -SHA256Checksums
```

## Step 4: Disable BitLocker (Win11 Only)

Windows 11 automatically enables BitLocker on new volumes. This must be disabled before the image can be analyzed:

```powershell
# Check BitLocker status
Get-BitLockerVolume

# Disable BitLocker
Disable-BitLocker -MountPoint H

# Monitor decryption progress (wait until ProtectionStatus = Off)
Get-BitLockerVolume | Select MountPoint, EncryptionPercentage, VolumeStatus
```

Decryption takes time. Do not detach the disk until `VolumeStatus` shows `FullyDecrypted`. An encrypted image will fail analysis with "image is BitLocker-encrypted".

Win10 does not auto-enable BitLocker on data volumes. Insider Server also does not.

## Step 5: Populate with Data

### Using Generate-FSActivity

```powershell
# Standard baseline (1000 actions, reproducible via seed)
.\Generate-FSActivity.ps1 -RootDir H:\test -Count 1000 -LogDir H:\logs -Seed 12345

# Replay the lab baseline for consistency (same action set on every disk)
.\Generate-FSActivity.ps1 -RootDir H:\test -ReplayFile .\fsactivity_baseline.json -LogDir H:\logs

# Large files
.\Generate-FSActivity.ps1 -RootDir H:\testxyz -Count 1000 -LogDir H:\logs `
 -LargeFileSizeMB 11,63,64,65

# Heavy special-artefact run (extra hardlinks, symlinks, ADS) — same script, -HeavySpcials
.\Generate-FSActivity.ps1 -RootDir H:\test -Count 1000 -LogDir H:\logs -HeavySpcials
```

### Manual Operations for Specific Tests

```powershell
# Mass file creation (100,000 files)
1..100000 | ForEach-Object { Set-Content -Path "H:\dir\file_$($_.ToString('D6')).txt" -Value "content $_" }

# Deep directory nesting (up to ~40 levels before MAX_PATH)
$path = "H:\"
1..40 | ForEach-Object { $path = Join-Path $path "d_$($_.ToString('D3'))"; New-Item -Path $path -ItemType Directory -Force }

# Sparse files
$f = [System.IO.File]::Create("H:\zero.bin"); $f.SetLength(52MB); $f.Close()

# EFS encrypted files
cipher /e H:\encrypted_dir

# Set file integrity on specific directory
Set-FileIntegrity H:\testintegrity -Enable $true

# Stream snapshots
# (Created via ReFS API; requires programmatic access)

# Case-sensitive directory
fsutil file setCaseSensitiveInfo H:\casesensitive enable
```

## Step 6: Verify Before Detaching

```powershell
# Confirm ReFS version and settings
fsutil fsinfo refsinfo H:

# Confirm volume info and capabilities
fsutil fsinfo volumeinfo H:

# Confirm BitLocker is off (Win11)
Get-BitLockerVolume -MountPoint H
```

## Step 7: Properly Unmount and Detach

Inside Windows (PowerShell as Administrator):

```powershell
# Remove drive letter
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath H:

# Set disk offline
Set-Disk -Number 1 -IsOffline $true
```

On the Linux host:

```bash
virsh detach-disk win11 sdr
```

Both steps are critical. Skipping them can leave the volume dirty or unmountable.

## Step 8: Verify on Host

```bash
# Quick structural verification
python3 forefst.py /mnt/usb/disks/step2/win11refs8g.raw -q | head -5

# Or with refsanalysis
python3 refsanalysis.py /mnt/usb/disks/step2/win11refs8g.raw summary
```

## Example: Creating a Baseline Image

```bash
# Host: create image
qemu-img create -f raw /mnt/usb/disks/step1/win11refsmini.raw 2G

# Host: attach
virsh attach-disk win11 /mnt/usb/disks/step1/win11refsmini.raw sdr \
 --targetbus virtio --driver qemu --subdriver raw
```

```powershell
# Guest: initialize, format, verify
Initialize-Disk -Number 1 -PartitionStyle GPT
New-Partition -DiskNumber 1 -UseMaximumSize -DriveLetter H
Format-Volume -FileSystem ReFS -Confirm:$false -NewFileSystemLabel "minirefs" -DriveLetter H
Disable-BitLocker -MountPoint H # Win11 only; wait for decryption
fsutil fsinfo refsinfo H:

# Guest: unmount
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath H:
Set-Disk -Number 1 -IsOffline $true
```

```bash
# Host: detach and verify
virsh detach-disk win11 sdr
python3 refsanalysis.py /mnt/usb/disks/step1/win11refsmini.raw boot
```

## Example: Creating a Stress-Test Image

```bash
qemu-img create -f raw /mnt/usb/disks/step3/win11refs2tmillionsofactionsv2.raw 2T
virsh attach-disk win11 /mnt/usb/disks/step3/win11refs2tmillionsofactionsv2.raw sdr \
 --targetbus virtio --driver qemu --subdriver raw
```

```powershell
Initialize-Disk -Number 1 -PartitionStyle GPT
New-Partition -DiskNumber 1 -UseMaximumSize -DriveLetter X
Format-Volume -DriveLetter X -FileSystem ReFS -NewFileSystemLabel "win11refs2tmillionsofactionsv2" -Confirm:$false
Disable-BitLocker -MountPoint X

# Run multiple rounds of activity
.\Generate-FSActivity.ps1 -RootDir X:\test -Count 1000 -LogDir X:\logs
.\Generate-FSActivity.ps1 -RootDir X:\test2 -Count 2000 -LogDir X:\logs

# Mass creation
1..100000 | ForEach-Object { Set-Content "X:\hello\ciao\ciao_$($_.ToString('D6')).txt" -Value "content" }

# Unmount
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath X:
Set-Disk -Number 1 -IsOffline $true
```

## Example: Creating a Version-Analysis Image

To capture the upgrade from ReFS 3.4 to 3.14:

```bash
# Create image and format on Win10
qemu-img create -f raw win10to11refs4g.raw 4G
# ... attach to win10 VM, format, populate, unmount ...

# Snapshot before Win11 mount
cp --sparse=always win10to11refs4g.raw win10to11refs4g_beforewin11mount.raw

# Attach to Win11 VM (auto-upgrades on mount)
virsh attach-disk win11 win10to11refs4g.raw sdr --targetbus virtio --driver qemu --subdriver raw

# In Win11 guest: just assign a letter and let it mount
Set-Partition -DiskNumber 1 -PartitionNumber 2 -NewDriveLetter H
fsutil fsinfo refsinfo H: # Now shows version 3.14

# Unmount, detach, snapshot after
cp --sparse=always win10to11refs4g.raw win10to11refs4g_afterwin11mount.raw
```

The upgrade is non-reversible. Once mounted by Win11, the volume cannot be used by Win10.
