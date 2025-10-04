# noraid manual setup commands via sysfs

- documentation: https://github.com/qvr/nonraid/blob/main/docs/nmdstat.5
- refs: https://github.com/qvr/nonraid/blob/main/docs/manual-management.md#creating-a-new-array

Since /dev/bcacheN is not supported, let's attempt to manual force it.

## Commands

```bash
root@bpve:~# lsscsi
[4:0:0:0]    disk    ATA      Samsung SSD 840  6B0Q  /dev/sda 
[5:0:0:0]    disk    ATA      WDC WD140EDFZ-11 0A81  /dev/sdb 
[6:0:0:0]    disk    ATA      ST18000NE000-3G6 EN01  /dev/sdc 
[7:0:0:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdd 
root@bpve:~# make-bcache -B /dev/sdb
UUID:			74689046-c7e1-4192-a781-92a449828db0
Set UUID:		2392b1d5-0f8d-4bbc-93b9-3ea843434ad6
version:		1
block_size:		1
data_offset:		16
root@bpve:~# make-bcache -B /dev/sdc
UUID:			78fce403-23a4-42da-af78-412bf336784d
Set UUID:		05dd6998-bb33-4084-8fe4-a02d8b4dfd19
version:		1
block_size:		1
data_offset:		16
root@bpve:~# make-bcache -B /dev/sdd
UUID:			1732da0a-2d3a-46b9-80b0-775fa303f544
Set UUID:		6c732a0d-dce5-47ab-bb1a-327a43beac94
version:		1
block_size:		8
data_offset:		16
root@bpve:~# 
root@bpve:~# ls -lah /dev/bcache/by-uuid/*
lrwxrwxrwx 1 root root 13 Oct  4 10:32 /dev/bcache/by-uuid/1732da0a-2d3a-46b9-80b0-775fa303f544 -> ../../bcache2
lrwxrwxrwx 1 root root 13 Oct  4 10:32 /dev/bcache/by-uuid/74689046-c7e1-4192-a781-92a449828db0 -> ../../bcache0
lrwxrwxrwx 1 root root 13 Oct  4 10:32 /dev/bcache/by-uuid/78fce403-23a4-42da-af78-412bf336784d -> ../../bcache1
```

We have the virtual /dev/bcache drives, we want noraid on it now.

Pre-requisite partitions for noraid.
```bash
root@bpve:~# sgdisk -o -a 8 -n 1:32K:0 /dev/bcache0
The operation has completed successfully.
root@bpve:~# sgdisk -o -a 8 -n 1:32K:0 /dev/bcache1
Creating new GPT entries in memory.
The operation has completed successfully.
root@bpve:~# sgdisk -o -a 8 -n 1:32K:0 /dev/bcache2
Creating new GPT entries in memory.
The operation has completed successfully.
root@bpve:~# 

```

### noraid array create force

- You must

```bash
root@bpve:~# lsblk
NAME          MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINTS
sda             8:0    0 238.5G  0 disk  
├─sda1          8:1    0  1007K  0 part  
├─sda2          8:2    0     1G  0 part  
└─sda3          8:3    0   237G  0 part  
sdb             8:16   0  12.7T  0 disk  
└─bcache0     251:0    0  12.7T  0 disk  
  └─bcache0p1 251:1    0  12.7T  0 part  
sdc             8:32   0  16.4T  0 disk  
└─bcache1     251:128  0  16.4T  0 disk  
  └─bcache1p1 251:129  0  16.4T  0 part  
sdd             8:48   0  16.4T  0 disk  
└─bcache2     251:256  0  16.4T  0 disk  
  └─bcache2p1 251:257  0  16.4T  0 part  
nvme1n1       259:0    0   1.8T  0 disk  
└─md127         9:127  0   1.8T  0 raid1 
nvme0n1       259:1    0   1.8T  0 disk  
nvme2n1       259:2    0   1.8T  0 disk  
└─md127         9:127  0   1.8T  0 raid1 
root@bpve:~# 

```