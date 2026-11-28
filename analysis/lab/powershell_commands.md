# PowerShell and Host Commands Reference

Quick reference for all commands used in ReFS disk image creation and analysis.

## Disk Management (Windows Guest)

### Disk Detection and Initialization

```powershell
# List all disks
Get-Disk

# Initialize a raw disk with GPT
Initialize-Disk -Number 1 -PartitionStyle GPT

# Create a partition using all available space
New-Partition -DiskNumber 1 -UseMaximumSize -DriveLetter H

# Assign a drive letter to an existing partition
Set-Partition -DiskNumber 1 -PartitionNumber 2 -NewDriveLetter H
```

### Inventory (the last step before imaging)

Record what Windows reports about every entry of the volume, then take the disk offline and image it, with nothing
in between. Elevated Windows PowerShell 5.1; what the script records is in [`README.md`](README.md#before-imaging-record-the-ground-truth-inventory_refsvolumeps1).

```powershell
# Every entry: times, sizes, attributes, file id, links, streams, hashes; volume.txt; errors.txt
.\Inventory_RefsVolume.ps1 -Drive H -Label mytest

# Also the change journal (Windows' decode), owners and SDDL, and the stream snapshots of every file (slower)
.\Inventory_RefsVolume.ps1 -Drive H -Label mytest -Journal -Security -Snapshots
```

### Unmounting (Must Do Before Detach)

```powershell
# Remove drive letter
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath H:

# Set disk offline
Set-Disk -Number 1 -IsOffline $true
```

## Format-Volume (ReFS)

### Basic

```powershell
Format-Volume -FileSystem ReFS -Confirm:$false -NewFileSystemLabel "label" -DriveLetter H
```

### With Options

```powershell
# 64K cluster size
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "64kclusters" `
 -Confirm:$false -AllocationUnitSize 64KB

# SHA-256 metadata checksums (instead of the default CRC64)
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "sha256" `
 -Confirm:$false -SHA256Checksums

# Integrity streams on for new files: per-cluster data checksums, CRC32-C on a 4 KiB-cluster volume
# (CRC64 on 64 KiB clusters, SHA-256 on a SHA-256 volume)
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "integrity" `
 -Confirm:$false -SetIntegrityStreams 1

# Integrity streams explicitly off
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "nointeg" `
 -Confirm:$false -SetIntegrityStreams 0

# Disable heat gathering (tiering engine)
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "noheat" `
 -Confirm:$false -DisableHeatGathering

# Disable TRIM
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "notrim" `
 -Confirm:$false -NoTrim

# Combined: 64K clusters + SHA256
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "64ksha256" `
 -Confirm:$false -AllocationUnitSize 64KB -SHA256Checksums
```

### NTFS (for negative testing)

```powershell
Format-Volume -FileSystem NTFS -Confirm:$false -NewFileSystemLabel "ntfstest" -DriveLetter H
```

## fsutil Commands

### ReFS-Specific Information

```powershell
# ReFS version, cluster size, checksums, free space
fsutil fsinfo refsinfo H:
```

Sample output (`win11refs2g`, formatted by Windows 11 24H2; abridged):
```
Volume Serial Number: 0x944a29564a293680
ReFS Version: 3.14
Number of Sectors: 0x003e0000
Total Clusters: 0x7c000
Free Clusters: 0x20b00
Bytes Per Sector: 512
Bytes Per Cluster: 4096
Metadata Checksum Type: CHECKSUM_TYPE_CRC64
Data Checksum Type: CHECKSUM_TYPE_NONE
```

### Volume Information (Capabilities)

```powershell
# Capabilities, flags, filesystem type
fsutil fsinfo volumeinfo H:
```

Lists the capabilities the mounted volume reports, as `Supports ...` lines (Hard Links, POSIX-style Unlink and
Rename, Stream Snapshots, Case-Sensitive Directories, Encrypted File System, Extended Attributes, ...); which lines
appear depends on the Windows build and on the volume. `Supports Transactions` appeared in one recorded output: a
volume mounted by Insider build 29574; no recorded output of a release build (ReFS 3.4 to 3.14) shows it.

### USN Journal

```powershell
# Create the USN journal (m = maximum size, a = allocation delta, in bytes)
fsutil usn createjournal m=0x800000 a=0x100000 H:

# Query journal info
fsutil usn queryjournal H:

# Read journal entries
fsutil usn readjournal H: csv
```

### Hard Links

```powershell
# Every name of a file (one line per link)
fsutil hardlink list H:\test\file.txt
```

### Case-Sensitive Directories

```powershell
# Enable case sensitivity on a directory
fsutil file setCaseSensitiveInfo H:\mydir enable

# Query case sensitivity
fsutil file queryCaseSensitiveInfo H:\mydir
```

## BitLocker Management

The lab's Windows 11 VM has encrypted a lab disk by itself, with no step asking for it, while the disk was attached
read-write: check the state before imaging (the inventory script records it and warns). An image of an encrypted
volume is encrypted.

```powershell
# Check BitLocker status on all volumes
Get-BitLockerVolume

# Check specific volume
Get-BitLockerVolume -MountPoint H

# Disable BitLocker (starts decryption)
Disable-BitLocker -MountPoint H

# Monitor decryption progress
Get-BitLockerVolume | Select MountPoint, EncryptionPercentage, VolumeStatus
# Wait until VolumeStatus = "FullyDecrypted"
```

## File Integrity

```powershell
# Check integrity state of a file
Get-FileIntegrity H:\test\file.txt

# Enable integrity on a directory (new files inherit)
Set-FileIntegrity H:\testintegrity -Enable $true

# Disable integrity
Set-FileIntegrity H:\testintegrity -Enable $false
```

## Stream Snapshots

```powershell
# Create a stream snapshot of a file, named "snap1"
refsutil streamsnapshot /c "snap1" H:\test\file.txt

# List every snapshot of a file
refsutil streamsnapshot /l "*" H:\test\file.txt
```

## Compression (Win11 ReFS)

```powershell
# Query compression state
refsutil compression H: /q

# Configure LZ4 compression
refsutil compression H: /c /level:9 /chunksize:32768 /algorithm:lz4

# Configure ZSTD compression
refsutil compression H: /c /level:13 /chunksize:262144 /algorithm:zstd

# Enable dedup+compress, then run the job (the compression settings alone compress nothing)
Enable-ReFSDedup -Volume H: -Type DedupAndCompress
Start-ReFSDedupJob -Volume H:
```

The volume's compression settings (format, level, chunk size) are shown by neither `fsutil fsinfo volumeinfo` nor
`fsutil fsinfo refsinfo`; `refsutil compression /q` prints them, and on a ReFS 3.14 volume they are in the Container
Table's root page (format at page offset 0xA4, level at 0xA6, chunk size at 0xA8). On the lab's compression test
volume (Windows 11 24H2) these steps changed the settings and ran deduplication, but compressed 0 bytes.

## ReFS Salvage

```powershell
# Diagnose without repair (the working directory receives its logs)
refsutil salvage -D H: C:\tools\salvagelogs\

# Quick scan, then copy every file found to <target dir> (the argument order as Microsoft documents it: check it
# against refsutil's own help on your build)
refsutil salvage -QA H: <working dir> <target dir>

# Rewrite the boot sector (CHANGES IT: on the one volume measured, it set the checksum selector, the serial number,
# the container size and the Extended GUID to 0 and the volume flags 0x66 -> 0x04; a writable mount then writes the
# 64 MiB default container size back). Image the volume first.
refsutil fixboot H: <parameters>
```

## Registry Settings

```powershell
# Enable last-access time updates (the default, 1, leaves them disabled)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
 -Name "RefsDisableLastAccessUpdate" -Value 0

# Check current value
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
 -Name "RefsDisableLastAccessUpdate"
```

## Host Commands (Linux)

### virsh (libvirt)

```bash
# List running VMs
virsh list

# Attach disk (virtio bus)
virsh attach-disk win10 /mnt/usb/disks/win10refs8g.raw vdm \
 --targetbus virtio --driver qemu --subdriver raw

# Attach disk (SATA bus)
virsh attach-disk win11 /mnt/usb/disks/win11refs8g.raw sda \
 --targetbus sata --driver qemu --subdriver raw

# Detach disk
virsh detach-disk win11 sda
virsh detach-disk win10 vdm
```

### qemu-img

```bash
# Create sparse raw image
qemu-img create -f raw image.raw 8G

# Check image info
qemu-img info image.raw
```

### Image Management

```bash
# Copy preserving sparseness (critical for TB-sized images)
cp --sparse=always source.raw destination.raw

# Compute SHA-256 hash
sha256sum image.raw
```

### Manual Structural Verification

```bash
# Partition layout
fdisk -l image.raw
mmls image.raw

# The offsets below are those of the lab images: GPT, the ReFS partition at LBA 32768 (512-byte sectors, byte
# 0x1000000), 4 KiB clusters. Take the partition start from mmls / fdisk for any other image.

# VBR at the partition start
xxd -l 64 -s 0x1000000 image.raw

# ReFS version: major at VBR+0x28, minor at VBR+0x29
xxd -l 2 -s 0x1000028 image.raw
# 03 04 = v3.4, 03 0e = v3.14

# Superblock at LCN 0x1E: partition start + 30 * cluster size (0x1E000 with 4 KiB clusters)
xxd -l 16 -s 0x101e000 image.raw
# The page starts with the signature "SUPB" (53 55 50 42)
```
