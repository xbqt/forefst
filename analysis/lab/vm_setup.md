# VM Setup for ReFS Disk Image Generation

## Overview

Three Windows VMs are used to produce ReFS disk images spanning versions 3.4 through 3.14+. All run under QEMU/KVM on a Linux host (Debian, kernel 6.19.8+).

| VM | OS | Build | ReFS Version | Purpose |
|----|-----|-------|-------------|---------|
| win10 | Win10 Pro for Workstations 1803 | 17134 | 3.4 | Baseline ReFS, no checksums, no EFS/hardlinks |
| win11 | Win11 Pro for Workstations 24H2 | 26100 | 3.14 | Full-featured ReFS with CRC64, EFS, hardlinks |
| winsider | Windows Server Insider | 29574 | 3.14 (driver max 3.15) | Insider-only features: Transactions, SHA256, 0x2000 flag |

Additional VMs used for version-specific testing:

| VM | OS | Build | ReFS Version | Purpose |
|----|-----|-------|-------------|---------|
| win1121h2 | Win11 21H2 | 22000 | 3.7 | First Win11 ReFS (adds Hard Links) |
| win1122h2 | Win11 22H2 | 22621 | 3.9 | Adds POSIX Unlink/Rename, Stream Snapshots |
| win1123h2 | Win11 23H2 | 22631 | 3.10 | Critical transition: compact refs, CRC64 declared, OID 0x30 |

## Why Pro for Workstations

ReFS formatting requires Windows 10/11 Pro for Workstations or Server editions. Standard Pro/Home cannot format ReFS volumes (Format-Volume -FileSystem ReFS will fail).

## QEMU/libvirt Configuration

### Prerequisites

```bash
# Verify KVM is available
ls /dev/kvm

# Required packages
apt-get install -y qemu-system-x86 libvirt-daemon-system virtinst
```

### VM Creation

Windows 10 Pro for Workstations 1803:

```bash
# Create the OS disk
qemu-img create -f qcow2 /var/lib/libvirt/images/win10.qcow2 60G

# Install (attach ISO, VirtIO drivers ISO)
virt-install \
 --name win10 \
 --ram 4096 --vcpus 4 \
 --disk path=/var/lib/libvirt/images/win10.qcow2,bus=virtio \
 --cdrom /path/to/Win10_1803_Workstations.iso \
 --disk path=/path/to/virtio-win.iso,device=cdrom \
 --os-variant win10 \
 --network default \
 --graphics vnc
```

Windows 11 Pro for Workstations 24H2:

```bash
qemu-img create -f qcow2 /var/lib/libvirt/images/win11.qcow2 80G

virt-install \
 --name win11 \
 --ram 8192 --vcpus 4 \
 --disk path=/var/lib/libvirt/images/win11.qcow2,bus=virtio \
 --cdrom /path/to/Win11_24H2.iso \
 --disk path=/path/to/virtio-win.iso,device=cdrom \
 --os-variant win11 \
 --network default \
 --graphics vnc \
 --features smm.state=on \
 --boot uefi \
 --tpm backend.type=emulator,backend.version=2.0
```

Win11 requires TPM 2.0 (emulated via swtpm) and Secure Boot (UEFI with SMM).

Windows Server Insider (build 29574):

```bash
qemu-img create -f qcow2 /var/lib/libvirt/images/winsider.qcow2 80G

virt-install \
 --name winsider \
 --ram 8192 --vcpus 4 \
 --disk path=/var/lib/libvirt/images/winsider.qcow2,bus=virtio \
 --cdrom /path/to/WindowsServerInsider_29574.iso \
 --disk path=/path/to/virtio-win.iso,device=cdrom \
 --os-variant win2k22 \
 --network default \
 --graphics vnc \
 --boot uefi
```

### Post-Install: VirtIO Drivers

Install VirtIO storage drivers from the virtio-win ISO inside the guest. This enables the `virtio` disk bus for data disks, which provides better performance than SATA.

## Creating Data Disks

Data disks are raw images attached to the VM for ReFS formatting:

```bash
# Create a sparse raw disk image (does not allocate full size on host)
qemu-img create -f raw /mnt/usb/disks/step2/win11refs8g.raw 8G

# Large volumes use the same command
qemu-img create -f raw /mnt/usb/disks/step3/win11refs15t.raw 15T
qemu-img create -f raw /mnt/usb/disks/step3/win11refs2t.raw 2T
```

### Attaching Disks to Running VMs

```bash
# Attach with virtio bus (Win10, or Win11 with VirtIO drivers)
virsh attach-disk win10 /mnt/usb/disks/step2/win10refs8g.raw vdm \
 --targetbus virtio --driver qemu --subdriver raw

# Attach with SATA bus (fallback if virtio causes issues)
virsh attach-disk win11 /mnt/usb/disks/step2/win11refs8g.raw sda \
 --targetbus sata --driver qemu --subdriver raw
```

Full absolute paths are required. Relative paths cause "Cannot access storage file" errors.

### Detaching Disks

Inside the Windows guest (PowerShell, run as Administrator):

```powershell
# Remove drive letter
Remove-PartitionAccessPath -PartitionNumber 2 -DiskNumber 1 -AccessPath H:

# Set disk offline (CRITICAL before detaching)
Set-Disk -Number 1 -IsOffline $true
```

On the Linux host:

```bash
virsh detach-disk win11 sda
# or
virsh detach-disk win10 vdm
```

Failure to properly offline the disk before detaching can leave the volume in a dirty state that Windows refuses to mount. This happened with the original millionsofactions image, which became permanently unmountable.

### Copying Sparse Images

```bash
# Preserve sparseness when copying (avoids inflating 15 TB images to full size)
cp --sparse=always source.raw destination.raw
```

## Key Differences Between VMs

| Property | Win10 (3.4) | Win11 (3.14) | Insider (3.14) |
|----------|-------------|--------------|----------------|
| VBR volume flags | 0x06 | 0x66 | 0x66 |
| VBR checksum algo (0x2A) | 0x0000 | 0x0002 (CRC64) | 0x0002 or 0x0004 (SHA256) |
| VBR format GUID (0x48) | all zeros | populated | populated |
| CHKP flags | 0x002 | 0x682 | 0x2682 |
| CHKP ref size | 0x68 (104 bytes) | 0x30 (48 bytes) | 0x30 or 0x48 (SHA256) |
| Metadata checksums | None | CRC64 | CRC64 or SHA256 |
| Hard links | No | Yes | Yes |
| EFS encryption | No | Yes | Yes |
| Transactions | No | No | Yes |
| BitLocker auto-enabled | No | Yes | No |
