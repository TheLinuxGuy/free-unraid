# Maintenance Tasks

## CPU / BIOS

### Intel Microcode releases
https://github.com/intel/Intel-Linux-Processor-Microcode-Data-Files/releases

Protip: wait until motherboard manufacturer bundles new microcode in BIOS update image file.

### BIOS updates for AsRock B660M Pro RS
https://www.asrock.com/mb/Intel/B660m%20Pro%20RS/index.asp#BIOS 


## Services

### NFS

Status
```
systemctl status nfs-kernel-server
```

Restart
```
systemctl restart nfs-kernel-server
```

Check NFS exports on server .54
```
showmount -e 192.168.1.54
```

Mounting on client
```
mount -t nfs 192.168.1.54:/mnt/cached /mnt/derp/ -vvv
```

Unmount force
```
umount -f -l /mnt/derp
```

## Storage

Monitor disk activity with the following command.
```
dstat -cd --disk-util --disk-tps
```
### Hard drive sleep (hd-idle)

```
systemctl status hd-idle
grep 'hd-idle' /var/log/syslog
```
### Btrfs scrubs (status, resume)

```
root@nas:/cache/music# btrfs scrub status /mnt/disk2
UUID:             8ff09467-056a-48ff-bb6e-7d72b67ca994
Scrub started:    Mon Oct 31 18:17:17 2022
Status:           interrupted
Duration:         0:29:47
Total to scrub:   12.19TiB
Rate:             100.96MiB/s
Error summary:    no errors found
root@nas:/cache/music# btrfs scrub resume /mnt/disk2
scrub resumed on /mnt/disk2, fsid 8ff09467-056a-48ff-bb6e-7d72b67ca994 (pid=1092977)
```

### Btrfs snapshots

List all snapshots
```
btrfs subvolume list -s /mnt/disk1
btrfs-list --snap-only /mnt/disk1
```

delete

```
root@nas:/home/gfm# btrfs subvolume list -s /mnt/disk1
ID 271 gen 36 cgen 36 top level 259 otime 2022-10-31 10:58:49 path .snapshots/10/snapshot
ID 272 gen 45 cgen 45 top level 259 otime 2022-11-01 00:44:52 path .snapshots/11/snapshot
root@nas:/home/gfm# btrfs subvolume delete /mnt/disk1/.snapshots/11/snapshot
Delete subvolume (no-commit): '/mnt/disk1/.snapshots/11/snapshot'
root@nas:/home/gfm# btrfs subvolume delete /mnt/disk1/.snapshots/10/snapshot
Delete subvolume (no-commit): '/mnt/disk1/.snapshots/10/snapshot'
```

### Array disk, disk space full. Upgrade to larger disk.

- **Scenario**: Time to upgrade to a larger hard drive with more capacity. We plan to remove the smallest disk in the array and replace it offline (thanks to Btrfs we can do this with little downtime).

1. Install new hard drive on system.
2. Have Btrfs move the data to new disk, online replacement.
3. Tell Brtfs to expand the disk to the new size.

We will be replacing `/mnt/disk1` 8TB that's 97% full with a new 18TB disk, not yet installed.

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sde        7.3T  7.0T  294G  97% /mnt/disk1
/dev/sdc         17T  6.1T   11T  37% /mnt/disk2
# fdisk -l /dev/sdf
Disk /dev/sdg: 16.37 TiB, 18000207937536 bytes, 35156656128 sectors
Disk model: WDC WD180EDGZ-11
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 4096 bytes
I/O size (minimum/optimal): 4096 bytes / 4096 bytes
```

Replacement disk was detected as `/dev/sdf` (note we can't rely on 'sdg' staying the same across reboots; I noted my controller slots not being enumerated well on this system). 

We will use btrfs labels to mitigate this problem.

#### Procedure 

**Note:** My observations are that `btrfs replace` is much slower than simply formatting a new hard disk then using rsync to migrate data. While `online` replacement handled by btrfs automatically is nicer and less involved, if you are in a time crunch keep this into consideration. 

```
# btrfs filesystem show /mnt/disk1
Label: 'mergerfsdisk1'  uuid: 007055ff-f9a3-458a-b3d4-56ca3daf6bd5
        Total devices 1 FS bytes used 6.98TiB
        devid    1 size 7.28TiB used 6.99TiB path /dev/sde
# btrfs replace start 1 /dev/sdf /mnt/disk1
```

Let's verify `/dev/sdf` was added to label `mergerfsdisk1` btrfs.

```
root@nas:/home/gfm# btrfs filesystem show /mnt/disk1
Label: 'mergerfsdisk1'  uuid: 007055ff-f9a3-458a-b3d4-56ca3daf6bd5
        Total devices 2 FS bytes used 6.98TiB
        devid    0 size 7.28TiB used 6.99TiB path /dev/sdf
        devid    1 size 7.28TiB used 6.99TiB path /dev/sde

root@nas:/home/gfm# btrfs replace status -1 /mnt/disk1
0.1% done, 0 write errs, 0 uncorr. read errs

```

Once the status command returns complete, we need to ensure that `btrfs replace` command also cloned the subvolume we use for parity (`content`).

```
btrfs subvolume list /mnt/disk1
```

Checking device ID and members. We see ID 0 is our new disk `/dev/sdf` and that we will gain about ~9TB of disk space once we force expand the btrfs filesystem after the `btrfs replace` is complete.

```
root@nas:/home/gfm# btrfs dev usage /mnt/disk1/
/dev/sdf, ID: 0
   Device size:            16.37TiB
   Device slack:            9.09TiB
   Unallocated:             7.28TiB

/dev/sde, ID: 1
   Device size:             7.28TiB
   Device slack:              0.00B
   Data,single:             6.97TiB
   Metadata,DUP:           18.00GiB
   System,DUP:             80.00MiB
   Unallocated:           291.95GiB

```

Verify `btrfs replace` completed. Note `/dev/sdf` (18TB) is now the single disk:
```
# btrfs replace status -1 /mnt/disk1
Started on  6.Nov 21:22:39, finished on  7.Nov 18:01:39, 0 write errs, 0 uncorr. read errs
root@nas:/home/gfm# btrfs filesystem show /mnt/disk1
Label: 'mergerfsdisk1'  uuid: 007055ff-f9a3-458a-b3d4-56ca3daf6bd5
        Total devices 1 FS bytes used 6.98TiB
        devid    1 size 7.28TiB used 6.99TiB path /dev/sdf

root@nas:/home/gfm# lsscsi
[0:0:0:0]    disk    QEMU     QEMU HARDDISK    2.5+  /dev/sda
[0:0:0:1]    disk    QEMU     QEMU HARDDISK    2.5+  /dev/sdb
[7:0:0:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdc
[7:0:1:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdd
[7:0:2:0]    disk    ATA      WDC WD80EFZX-68U 0A83  /dev/sde
[7:0:6:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdf
[N:0:1:1]    disk    Samsung SSD 950 PRO 256GB__1               /dev/nvme0n1
# btrfs dev usage /mnt/disk1/
/dev/sdf, ID: 1
   Device size:            16.37TiB
   Device slack:            9.09TiB
   Data,single:             6.97TiB
   Metadata,DUP:           18.00GiB
   System,DUP:             80.00MiB
   Unallocated:           291.95GiB
```

There's 9TB of unclaimed space we can expand so it can be used. 

```
# btrfs filesystem resize 1:max /mnt/disk1
Resize device id 1 (/dev/sdf) from 7.28TiB to max
root@nas:/home/gfm# btrfs dev usage /mnt/disk1/
/dev/sdf, ID: 1
   Device size:            16.37TiB
   Device slack:              0.00B
   Data,single:             6.97TiB
   Metadata,DUP:           18.00GiB
   System,DUP:             80.00MiB
   Unallocated:             9.38TiB
root@nas:/home/gfm# df -h /mnt/disk1
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdf         17T  7.0T  9.4T  43% /mnt/disk1
```

**That's it. You have completed a live-replace of `/dev/sde` with `/dev/sdf` a larger drive w/o downtime.**