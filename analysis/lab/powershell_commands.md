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

# SHA256 metadata checksums (instead of default CRC64)
Format-Volume -DriveLetter H -FileSystem ReFS -NewFileSystemLabel "sha256" `
 -Confirm:$false -SHA256Checksums

# Integrity streams enabled (adds per-file CRC32 data checksums)
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

Sample output (Win11 24H2):
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

Reports supported features: Hard Links, POSIX Unlink/Rename, Stream Snapshots, Case-Sensitive Directories, EFS, Extended Attributes, Transactions (Insider only).

### USN Journal

```powershell
# Create a USN journal (v2 or v3)
fsutil usn createjournal m=0x800000 a=0x100000 H:

# Query journal info
fsutil usn queryjournal H:

# Read journal entries
fsutil usn readjournal H: csv
```

### Case-Sensitive Directories

```powershell
# Enable case sensitivity on a directory
fsutil file setCaseSensitiveInfo H:\mydir enable

# Query case sensitivity
fsutil file queryCaseSensitiveInfo H:\mydir
```

## BitLocker Management

Windows 11 auto-enables BitLocker on new volumes. Must disable before image analysis.

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

## Compression (Win11 ReFS)

```powershell
# Query compression state
refsutil compression H: /q

# Configure LZ4 compression
refsutil compression H: /c /level:9 /chunksize:32768 /algorithm:lz4

# Configure ZSTD compression
refsutil compression H: /c /level:13 /chunksize:262144 /algorithm:zstd

# Enable dedup+compress
Enable-ReFSDedup -Type DedupAndCompress
Start-ReFSDedupJob
```

Compression configuration is stored in the Container Table root page header, not visible via fsutil. Only `refsutil compression /q` and raw disk analysis can read it.

## ReFS Salvage

```powershell
# Diagnose without repair
refsutil salvage -D H:

# Quick + All scan (copies recoverable files)
refsutil salvage -QA H: <outputdir> <logdir>

# Fix boot sector (DANGEROUS: zeroes container_size in VBR)
refsutil fixboot H:
```

## Registry Settings

```powershell
# Enable last access time updates (default is disabled = 1)
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

# VBR at partition start (LBA 32768 * 512 = 0x1000000)
xxd -l 64 -s 0x1000000 image.raw

# ReFS version at VBR+0x28
xxd -l 4 -s 0x1000028 image.raw
# 0x0304 = v3.4, 0x030E = v3.14

# SUPB signature at partition_start + 30 * cluster_size
xxd -l 16 -s 0x101e000 image.raw
# Should show "SUPB" (0x53555042)
```
