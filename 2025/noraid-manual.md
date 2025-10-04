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

#### Command cheatsheet

- `nmdctl reload` Force reset any config and superblock
- `nmdctl status` check status if noraid

### noraid array create force

- You must fix udev before attempting the below. 

Manual create command

Get size of raw disk
`blockdev --getsize /dev/bcache1` 

- returned `35156656112` --- BUT this must be divided by 2. **Use `17578328056` for manual import**

Make sure disk by-id udev works
```bash
root@bpve:~# ls -lah /dev/disk/by-id/ | grep bcache
...
```

- SLOT ID 0 or 29 is partity disks.
- SLOT ID 1 to 28 is data disks.

```bash
echo "import 1 bcache1 0 17578328056 0 bcache-ST18000NE000-3G6101-ZVTEFBA9" > /proc/nmdcmd
root@bpve:~# echo "import 1 bcache1 0 35156656112 0 bcache-ST18000NE000-3G6101-MYSERIAL" > /proc/nmdcmd
root@bpve:~# echo "start NEW_ARRAY" > /proc/nmdcmd
root@bpve:~# ls -lah /dev/nmd1p1
brw-rw---- 1 root disk 127, 1 Oct  4 11:51 /dev/nmd1p1
root@bpve:~# pv /dev/nmd1p1 -> /dev/null
^C53GiB 0:00:07 [ 235MiB/s] [             <=>                                                                                    ]
root@bpve:~# 
```

### VICTORY! (more work needed)

```bash
root@bpve:~# nmdctl status
=== NonRAID Array Status ===

Array State   : STARTED
Superblock    : /nonraid.dat
Disks Present : 1

WARNING: Driver internal state is inconsistent!
The array mdNum* counters show non-zero values, but all individual disks are DISK_OK status.
This can happen after initial array creation, but it may cause unexpected behavior.
Recommend reloading the driver and starting the array again: nmdctl reload && nmdctl start

Array Health  : DEGRADED (Invalid: 2, Disabled: 2, I/O Errors: 1)
Array Checked : never
Array Size    : 32.7 TB (1 data disk(s))
Parity        : No Parity

=== Disk Status ===

Slot  Status       Device        Size     FS       Mountpoint  Usage  Reads   Writes
----  -----------  ------------  -------  -------  ----------  -----  ------  ------
P     DISABLED     (unassigned)  0 B      P        -           -      0 B     0 B   
1     OK (1 errs)  bcache1       32.7 TB  unknown  unmounted   -      1.5 GB  0 B   
root@bpve:~# 

```

## A real-attempt at an array after learning the basics

Previous step I learned how to manually map and disk and array. Now let's try to make this real, given 3 hard drives (1 parity, 2 data) let's build something.

- DATA1 (smaller): bcache0 WD140EDFZ-11 0A81  /dev/sdb 
- PARITY: bcache1 ST18000NE000-3G6 EN01  /dev/sdc 
- DATA2 (match parity disk size): bcache2 WD180EDGZ-11 0A85  /dev/sdd 

#### Commands dumpster

1. Get disk sizes
```
root@bpve:~# device=/dev/bcache0; echo $(( $(blockdev --getsize "$device") / 2 ))
13672382456
root@bpve:~# device=/dev/bcache1; echo $(( $(blockdev --getsize "$device") / 2 ))
17578328056
root@bpve:~# device=/dev/bcache2; echo $(( $(blockdev --getsize "$device") / 2 ))
17578328056
```

2. Make sure disks have partitions. If one doesn't have partitions it won't show up in `status` command.  Use `partprobe /dev/bcache0` to force rescan if you just partitioned with `sgdisk -o -a 8 -n 1:32K:0 /dev/bcache0`

3. Configure the array.

```bash
echo "import 0 bcache1p1 0 17578328056 0 bcache-ST18000NE000-3G6101-ZVTEFBA9" > /proc/nmdcmd
echo "import 1 bcache0p1 0 13672382456 0 bcache-WDC_WD140EDFZ-11A0VA0-QBJ2NRVT" > /proc/nmdcmd
echo "import 2 bcache2p1 0 17578328056 0 bcache-WDC_WD180EDGZ-11B2DA0-3FHMY6ZT" > /proc/nmdcmd
```

Now we see it configured as expected and we should start it.

```
root@bpve:~# nmdctl status
=== NonRAID Array Status ===

Array State   : NEW_ARRAY
Superblock    : /nonraid.dat
Disks Present : 3
Array Health  : NEW (New array, parity needs to be built)
Array Checked : never
Array Size    : 0 B (0 data disk(s))
Parity        : No Parity

Disk reconstruction pending: Parity-Sync P
Start the array and use 'nmdctl check' command to start the operation

=== Disk Status ===

Slot  Status  Device     Size   
----  ------  ---------  -------
P     NEW     bcache1p1  16.3 TB
1     NEW     bcache0p1  12.7 TB
2     NEW     bcache2p1  16.3 TB
root@bpve:~# 
```

4. Start array and rebuild.

```bash
root@bpve:~# nmdctl status
=== NonRAID Array Status ===

Array State   : STARTED
Superblock    : /nonraid.dat
Disks Present : 3
Array Health  : DEGRADED (Invalid: 2, Disabled: 1, I/O Errors: 2)
Array Checked : never
Array Size    : 29.1 TB (2 data disk(s))
Parity        : No Parity

Disk reconstruction pending: Parity-Sync P
Use 'nmdctl check' command to start the operation

=== Disk Status ===

Slot  Status       Device     Size     FS       Mountpoint  Usage  Reads  Writes
----  -----------  ---------  -------  -------  ----------  -----  -----  ------
P     INVALID      bcache1p1  16.3 TB  P        -           -      0 B    0 B   
1     OK (1 errs)  bcache0p1  12.7 TB  unknown  unmounted   -      20 kB  0 B   
2     OK (1 errs)  bcache2p1  16.3 TB  unknown  unmounted   -      20 kB  0 B   
root@bpve:~# nmdctl check
Warning: A sync operation other than parity check is pending: Parity-Sync P
Do you want to proceed with Parity-Sync P? (y/N): y
Starting Parity-Sync P...
Parity-Sync P started
root@bpve:~# 
```

Errors during parity sync, could this be due to wrong disk size? I had used `blockdev --getsize` on parent /dev/bcacheN and not the partition. TBD.

```
[ 3559.284700] I/O error, dev sdc, sector 8144 op 0x1:(WRITE) flags 0x0 phys_seg 16 prio class 0
[ 3559.284936] nmd: disk0 write error, sector=8064
[ 3559.285170] nmd: disk0 write error, sector=8072
[ 3559.285410] nmd: disk0 write error, sector=8080
[ 3559.285648] nmd: disk0 write error, sector=8088
[ 3559.285887] nmd: disk0 write error, sector=8096
[ 3559.286126] nmd: disk0 write error, sector=8104
[ 3559.286389] nmd: disk0 write error, sector=8112
[ 3559.286627] nmd: disk0 write error, sector=8120
[ 3559.286861] nmd: disk0 write error, sector=8128
[ 3559.287100] nmd: disk0 write error, sector=8136
[ 3559.287336] nmd: disk0 write error, sector=8144
[ 3559.287573] nmd: disk0 write error, sector=8152
[ 3559.287806] nmd: disk0 write error, sector=8160
[ 3559.288048] nmd: disk0 write error, sector=8168
[ 3559.288282] nmd: disk0 write error, sector=8176
[ 3559.288518] nmd: disk0 write error, sector=8184
[ 3559.288756] ata7: EH complete
[ 3559.291681] nmd: recovery thread: exit status: -4
[ 3570.215118] Buffer I/O error on dev nmd1p1, logical block 3418095612, async page read
[ 3570.223774] Buffer I/O error on dev nmd2p1, logical block 4394582012, async page read
[ 3575.302502] Buffer I/O error on dev nmd1p1, logical block 3418095612, async page read
[ 3575.311644] Buffer I/O error on dev nmd2p1, logical block 4394582012, async page read
```