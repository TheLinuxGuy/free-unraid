# 2025 Experiment Notes

## Overview

This document serves as the staging area for experimental notes and ideas planned for 2025. The focus is on exploring new developments and enhancing the `free-unraid` solution.

## Current Research Focus

### Unraid Disk Parity Driver Integration

A significant development has emerged that opens new possibilities for the free-unraid project:

- **Discovery**: The Unraid disk parity driver has been made available as an open-source implementation
- **Source**: [nonraid project](https://github.com/qvr/nonraid) by qvr
- **Planned Integration**: Experimenting with combining this parity driver with bcache technology

### Objectives

1. **Evaluate** the nonraid parity driver's compatibility with existing free-unraid components
2. **Test** bcache integration for improved performance characteristics
3. **Document** findings and implementation steps for community benefit
4. **Enhance** the overall free-unraid solution based on experimental results

## Next Steps

- [ ] Set up test environment for nonraid driver
- [ ] Configure bcache integration testing
- [ ] Performance benchmarking against current solution
- [ ] Documentation of setup procedures and results

### Command line dump

Fresh install of Proxmox VE 9.0 and added the PPA config first.

```bash
apt install pve-headers-$(uname -r) nonraid-dkms nonraid-tools bcache-tools lsscsi pv fio parted jq mdadm
```

### Implement an unraid esque array with bcache powers

#### NVME cache RAID1

```bash
mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/nvme0n1 /dev/nvme1n1
mdadm --examine --scan >> /etc/mdadm/mdadm.conf 
echo 500000 > /proc/sys/dev/raid/speed_limit_min && echo 1000000 > /proc/sys/dev/raid/speed_limit_max
root@bpve:~# make-bcache -C /dev/md127 
UUID:			801ee96d-bffc-4654-a5db-dfecda09f06d
Set UUID:		0cb4df80-d977-49e0-8a5a-6c08bed69edb
version:		0
nbuckets:		3815200
block_size:		1
bucket_size:		1024
nr_in_set:		1
nr_this_dev:		0
first_bucket:		1

```
#### Data disks

```bash
root@bpve:~# umount /dev/sdb
root@bpve:~# umount /dev/sdc
root@bpve:~# umount /dev/sdd
root@bpve:~# wipefs -a /dev/sdb
/dev/sdb: 4 bytes were erased at offset 0x00000000 (xfs): 58 46 53 42
root@bpve:~# wipefs -a /dev/sdc
/dev/sdc: 4 bytes were erased at offset 0x00000000 (xfs): 58 46 53 42
root@bpve:~# wipefs -a /dev/sdd
/dev/sdd: 4 bytes were erased at offset 0x00000000 (xfs): 58 46 53 42
root@bpve:~# 
root@bpve:~# make-bcache -B /dev/sdc
UUID:			54c4e4d8-474f-437b-869c-dda01914da95
Set UUID:		803704af-61da-4179-9464-0618574bdf6e
version:		1
block_size:		1
data_offset:		16
root@bpve:~# make-bcache -B /dev/sdd
UUID:			47f399ed-93e3-4974-970d-6094508d2c86
Set UUID:		564a2210-e31a-4168-9e16-373c2d617919
version:		1
block_size:		8
data_offset:		16
```

## noraid setup on bcache backed disks (Blocked by bug)

```bash
root@bpve:~# sgdisk -o -a 8 -n 1:32K:0 /dev/bcache0
Creating new GPT entries in memory.
The operation has completed successfully.
root@bpve:~# sgdisk -o -a 8 -n 1:32K:0 /dev/bcache1
Creating new GPT entries in memory.
The operation has completed successfully.
root@bpve:~# nmdctl -v create
Creating a new array with a new superblock at: /nonraid.dat
Note: The superblock file will be created when the array is started
=== Creating New NonRAID Array ===

This will create a new array and assign disks to slots.
Only devices with an unused largest partition will be shown.

Scanning for available disks...
Error: No suitable disk devices found
Make sure disks are connected and are partitioned correctly
root@bpve:~# lsblk -n -I 8 -o path 2>/dev/null
/dev/sda
/dev/sda1
/dev/sda2
/dev/sda3
/dev/sdb
/dev/sdc
/dev/sdd
/dev/bcache0
/dev/bcache0p1
/dev/bcache1
/dev/bcache1p1
root@bpve:~# 

```

The setup using `nmdctl create` cannot continue because it filters out /dev/bcacheN type devices we're trying to use here. As seen in: https://github.com/qvr/nonraid/blob/378d6f60b541eb1aeb2c95d90254a291b7ac7b21/tools/nmdctl#L2659-L2681

Will contact the developer and ask if they have suggestions to workaround, or if they plan to consider the bcache use-case I am trying to do here.