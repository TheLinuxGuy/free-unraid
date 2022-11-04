# Performance

These are my notes about performance of this setup (and some experiments with `autotier` mergerfs competitor).

Performance is measured by this `fio` command. It's intended to test **sequential writes** with 1MB block size. Imitates write backup activity or large file copies (HD tv or movies).

```
fio --name=fiotest --filename=/mnt/samsung/zfscache/file123 --size=16Gb --rw=write --bs=1M --direct=1 --numjobs=8 --ioengine=libaio --iodepth=8 --group_reporting --runtime=60 --startdelay=60 
```

#### My hardware

```
root@nas:/home/gfm# lsscsi
[0:0:0:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdc
[0:0:1:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdd
[0:0:2:0]    disk    ATA      WDC WD80EFZX-68U 0A83  /dev/sde
[1:0:0:0]    disk    QEMU     QEMU HARDDISK    2.5+  /dev/sda
[1:0:0:1]    disk    QEMU     QEMU HARDDISK    2.5+  /dev/sdb
[3:0:0:0]    cd/dvd  QEMU     QEMU DVD-ROM     2.5+  /dev/sr0
[N:0:1:1]    disk    Samsung SSD 950 PRO 256GB__1               /dev/nvme0n1
root@nas:/home/gfm# df -h
Filesystem                         Size  Used Avail Use% Mounted on
udev                               1.9G     0  1.9G   0% /dev
tmpfs                              390M  2.8M  387M   1% /run
/dev/mapper/ubuntu--vg-ubuntu--lv   60G  9.8G   48G  18% /
tmpfs                              2.0G     0  2.0G   0% /dev/shm
tmpfs                              5.0M     0  5.0M   0% /run/lock
tmpfs                              2.0G     0  2.0G   0% /sys/fs/cgroup
mergerfs                           231G  1.0M  231G   1% /mnt/cached
mergerfs                            24T  121G   24T   1% /mnt/slow-storage
/dev/sda2                          2.0G  107M  1.7G   6% /boot
/dev/sda1                          1.1G  5.3M  1.1G   1% /boot/efi
/dev/sdc                            17T   51G   17T   1% /mnt/disk2
/dev/sdc                            17T   51G   17T   1% /mnt/snapraid-content/disk2
cache                              231G  1.0M  231G   1% /cache
/dev/sde                           7.3T   71G  7.3T   1% /mnt/snapraid-content/disk1
/dev/sde                           7.3T   71G  7.3T   1% /mnt/disk1
/dev/loop1                          64M   64M     0 100% /snap/core20/1634
/dev/loop3                          47M   47M     0 100% /snap/snapd/16292
/dev/loop2                          48M   48M     0 100% /snap/snapd/17336
/dev/loop0                          64M   64M     0 100% /snap/core20/1623
/dev/loop4                          68M   68M     0 100% /snap/lxd/22753
/dev/sdd1                           17T  117G   17T   1% /mnt/parity1
tmpfs                              390M     0  390M   0% /run/user/1000
root@nas:/home/gfm# zpool status
  pool: cache
 state: ONLINE
  scan: resilvered 12.0M in 0 days 00:00:00 with 0 errors on Thu Nov  3 23:34:42 2022
config:

        NAME         STATE     READ WRITE CKSUM
        cache        ONLINE       0     0     0
          mirror-0   ONLINE       0     0     0
            sdb      ONLINE       0     0     0
            nvme0n1  ONLINE       0     0     0

errors: No known data errors

```

### /cache ZFS Raw-disk performance (this is my "fast cache" for mergerfs)

**NOTE: ZFS filesystem uses memory catching L2ARC and other things that may 'inflate' results**

I have done tests on this same nvm0n1 disk and max writes are around 900MB/s (if you google for Samsung 950 256GB drives like mine you will find same benchmark results).

```
Jobs: 8 (f=8): [W(8)][100.0%][w=344MiB/s][w=344 IOPS][eta 00m:00s]
fiotest: (groupid=0, jobs=8): err= 0: pid=17709: Thu Nov  3 23:58:41 2022
  write: IOPS=1240, BW=1240MiB/s (1300MB/s)(72.7GiB/60017msec); 0 zone resets
    slat (usec): min=82, max=103024, avg=6447.15, stdev=11814.99
    clat (usec): min=2, max=548443, avg=45148.97, stdev=80640.79
     lat (usec): min=1015, max=617530, avg=51596.52, stdev=91759.09
    clat percentiles (msec):
     |  1.00th=[    4],  5.00th=[    7], 10.00th=[    8], 20.00th=[    8],
     | 30.00th=[    8], 40.00th=[    8], 50.00th=[    9], 60.00th=[    9],
     | 70.00th=[   16], 80.00th=[   64], 90.00th=[  159], 95.00th=[  234],
     | 99.00th=[  380], 99.50th=[  418], 99.90th=[  472], 99.95th=[  498],
     | 99.99th=[  542]
   bw (  MiB/s): min=  111, max= 6468, per=99.93%, avg=1239.24, stdev=193.05, samples=960
   iops        : min=  107, max= 6468, avg=1238.93, stdev=193.07, samples=960
  lat (usec)   : 4=0.01%, 10=0.01%, 1000=0.01%
  lat (msec)   : 2=0.24%, 4=1.84%, 10=63.16%, 20=6.46%, 50=6.25%
  lat (msec)   : 100=6.65%, 250=11.16%, 500=4.17%, 750=0.05%
  cpu          : usr=0.70%, sys=2.84%, ctx=671054, majf=0, minf=92
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=99.9%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,74429,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=1240MiB/s (1300MB/s), 1240MiB/s-1240MiB/s (1300MB/s-1300MB/s), io=72.7GiB (78.0GB), run=60017-60017msec
```

### /mnt/slow-storage - mergerfs aggregate of spinning disks 18TB, 8TB

These HDDs provide about 170MB/s max write speeds. The older 8TB drive may give 140MB/s.

The mergerfs `/etc/fstab` for this mount looks like:
```
/mnt/disk* /mnt/slow-storage fuse.mergerfs defaults,nonempty,allow_other,use_ino,category.create=eplus,cache.files=off,moveonenospc=true,dropcacheonclose=true,minfreespace=300G,fsname=mergerfs 0 0
```

results

```
fiotest: (g=0): rw=write, bs=(R) 1024KiB-1024KiB, (W) 1024KiB-1024KiB, (T) 1024KiB-1024KiB, ioengine=libaio, iodepth=8
...
fio-3.16
Starting 8 processes
fiotest: Laying out IO file (1 file / 16384MiB)
Jobs: 8 (f=3): [f(8)][100.0%][w=241MiB/s][w=241 IOPS][eta 00m:00s]
fiotest: (groupid=0, jobs=8): err= 0: pid=23616: Fri Nov  4 00:03:59 2022
  write: IOPS=184, BW=185MiB/s (194MB/s)(10.8GiB/60076msec); 0 zone resets
    slat (usec): min=19, max=728722, avg=43252.77, stdev=36616.24
    clat (msec): min=23, max=1335, avg=302.65, stdev=93.08
     lat (msec): min=23, max=1376, avg=345.90, stdev=99.29
    clat percentiles (msec):
     |  1.00th=[  165],  5.00th=[  205], 10.00th=[  224], 20.00th=[  245],
     | 30.00th=[  262], 40.00th=[  275], 50.00th=[  288], 60.00th=[  305],
     | 70.00th=[  321], 80.00th=[  347], 90.00th=[  397], 95.00th=[  435],
     | 99.00th=[  542], 99.50th=[  835], 99.90th=[ 1284], 99.95th=[ 1318],
     | 99.99th=[ 1334]
   bw (  KiB/s): min=51200, max=296960, per=100.00%, avg=189680.43, stdev=4517.78, samples=952
   iops        : min=   50, max=  290, avg=184.69, stdev= 4.43, samples=952
  lat (msec)   : 50=0.17%, 100=0.18%, 250=22.55%, 500=75.15%, 750=1.44%
  lat (msec)   : 1000=0.17%, 2000=0.33%
  cpu          : usr=0.12%, sys=0.14%, ctx=22235, majf=0, minf=92
  IO depths    : 1=0.1%, 2=0.1%, 4=0.3%, 8=99.5%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=99.9%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,11087,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=185MiB/s (194MB/s), 185MiB/s-185MiB/s (194MB/s-194MB/s), io=10.8GiB (11.6GB), run=60076-60076msec

```

### /mnt/cached - mergerfs ZFS only zpool mount of /cache (no spinning disks)

TL;DR **performance penalty on mergerfs**

```
WRITE: bw=374MiB/s (392MB/s), 374MiB/s-374MiB/s (392MB/s-392MB/s), io=21.9GiB (23.6GB),
```

vs. without mergerfs (pure zpool)
```
  WRITE: bw=1240MiB/s (1300MB/s), 1240MiB/s-1240MiB/s (1300MB/s-1300MB/s), io=72.7GiB (78.0GB), run=60017-60017msec
```

mergerfs `/etc/fstab` is
```
/cache /mnt/cached fuse.mergerfs nonempty,allow_other,use_ino,cache.files=off,category.create=lfs,moveonenospc=true,dropcacheonclose=true,minfreespace=4G,fsname=mergerfs 0 0
```

results

```
Jobs: 8 (f=3): [f(2),W(2),f(1),W(1),f(2)][25.7%][w=557MiB/s][w=556 IOPS][eta 05m:49s]
fiotest: (groupid=0, jobs=8): err= 0: pid=25212: Fri Nov  4 00:08:15 2022
  write: IOPS=373, BW=374MiB/s (392MB/s)(21.9GiB/60084msec); 0 zone resets
    slat (usec): min=10, max=1081.4k, avg=21349.93, stdev=56883.73
    clat (usec): min=4, max=2673.2k, avg=149732.07, stdev=290258.09
     lat (usec): min=287, max=2795.8k, avg=171082.91, stdev=321499.99
    clat percentiles (msec):
     |  1.00th=[    3],  5.00th=[   11], 10.00th=[   16], 20.00th=[   24],
     | 30.00th=[   33], 40.00th=[   43], 50.00th=[   54], 60.00th=[   69],
     | 70.00th=[  100], 80.00th=[  176], 90.00th=[  347], 95.00th=[  642],
     | 99.00th=[ 1636], 99.50th=[ 2005], 99.90th=[ 2400], 99.95th=[ 2500],
     | 99.99th=[ 2668]
   bw (  KiB/s): min=16374, max=2783526, per=100.00%, avg=392628.80, stdev=58773.48, samples=931
   iops        : min=   14, max= 2717, avg=382.85, stdev=57.39, samples=931
  lat (usec)   : 10=0.01%, 500=0.35%, 750=0.11%, 1000=0.10%
  lat (msec)   : 2=0.36%, 4=0.80%, 10=2.36%, 20=11.42%, 50=31.95%
  lat (msec)   : 100=22.79%, 250=15.45%, 500=7.80%, 750=2.37%, 1000=1.41%
  lat (msec)   : 2000=2.22%, >=2000=0.49%
  cpu          : usr=0.27%, sys=0.23%, ctx=30547, majf=0, minf=95
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=99.8%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,22467,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=374MiB/s (392MB/s), 374MiB/s-374MiB/s (392MB/s-392MB/s), io=21.9GiB (23.6GB), run=60084-60084msec
```

### Let's remove ZFS from the equation (mergerfs)

```
zpool destroy cache
mkfs.btrfs -f -L cachebtrfs /dev/nvme0n1
btrfs-progs v5.4.1
See http://btrfs.wiki.kernel.org for more information.

Detected a SSD, turning off metadata duplication.  Mkfs with -m dup if you want to force metadata duplication.
Label:              cachebtrfs
UUID:               53afb172-2ac8-43be-98e0-d749217bf129
Node size:          16384
Sector size:        4096
Filesystem size:    238.47GiB
Block group profiles:
  Data:             single            8.00MiB
  Metadata:         single            8.00MiB
  System:           single            4.00MiB
SSD detected:       yes
Incompat features:  extref, skinny-metadata
Checksum:           crc32c
Number of devices:  1
Devices:
   ID        SIZE  PATH
    1   238.47GiB  /dev/nvme0n1

root@nas:/home/gfm# mkdir /cache
root@nas:/home/gfm# mount /dev/nvme0n1 /cache
root@nas:/home/gfm# mount
sysfs on /sys type sysfs (rw,nosuid,nodev,noexec,relatime)
proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)
udev on /dev type devtmpfs (rw,nosuid,noexec,relatime,size=1948816k,nr_inodes=487204,mode=755)
devpts on /dev/pts type devpts (rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000)
tmpfs on /run type tmpfs (rw,nosuid,nodev,noexec,relatime,size=398812k,mode=755)
/dev/mapper/ubuntu--vg-ubuntu--lv on / type ext4 (rw,relatime)
securityfs on /sys/kernel/security type securityfs (rw,nosuid,nodev,noexec,relatime)
tmpfs on /dev/shm type tmpfs (rw,nosuid,nodev)
tmpfs on /run/lock type tmpfs (rw,nosuid,nodev,noexec,relatime,size=5120k)
tmpfs on /sys/fs/cgroup type tmpfs (ro,nosuid,nodev,noexec,mode=755)
cgroup2 on /sys/fs/cgroup/unified type cgroup2 (rw,nosuid,nodev,noexec,relatime,nsdelegate)
cgroup on /sys/fs/cgroup/systemd type cgroup (rw,nosuid,nodev,noexec,relatime,xattr,name=systemd)
pstore on /sys/fs/pstore type pstore (rw,nosuid,nodev,noexec,relatime)
efivarfs on /sys/firmware/efi/efivars type efivarfs (rw,nosuid,nodev,noexec,relatime)
none on /sys/fs/bpf type bpf (rw,nosuid,nodev,noexec,relatime,mode=700)
cgroup on /sys/fs/cgroup/blkio type cgroup (rw,nosuid,nodev,noexec,relatime,blkio)
cgroup on /sys/fs/cgroup/cpu,cpuacct type cgroup (rw,nosuid,nodev,noexec,relatime,cpu,cpuacct)
cgroup on /sys/fs/cgroup/freezer type cgroup (rw,nosuid,nodev,noexec,relatime,freezer)
cgroup on /sys/fs/cgroup/devices type cgroup (rw,nosuid,nodev,noexec,relatime,devices)
cgroup on /sys/fs/cgroup/cpuset type cgroup (rw,nosuid,nodev,noexec,relatime,cpuset)
cgroup on /sys/fs/cgroup/perf_event type cgroup (rw,nosuid,nodev,noexec,relatime,perf_event)
cgroup on /sys/fs/cgroup/hugetlb type cgroup (rw,nosuid,nodev,noexec,relatime,hugetlb)
cgroup on /sys/fs/cgroup/pids type cgroup (rw,nosuid,nodev,noexec,relatime,pids)
cgroup on /sys/fs/cgroup/net_cls,net_prio type cgroup (rw,nosuid,nodev,noexec,relatime,net_cls,net_prio)
cgroup on /sys/fs/cgroup/rdma type cgroup (rw,nosuid,nodev,noexec,relatime,rdma)
cgroup on /sys/fs/cgroup/memory type cgroup (rw,nosuid,nodev,noexec,relatime,memory)
systemd-1 on /proc/sys/fs/binfmt_misc type autofs (rw,relatime,fd=28,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=3020)
hugetlbfs on /dev/hugepages type hugetlbfs (rw,relatime,pagesize=2M)
mqueue on /dev/mqueue type mqueue (rw,nosuid,nodev,noexec,relatime)
debugfs on /sys/kernel/debug type debugfs (rw,nosuid,nodev,noexec,relatime)
tracefs on /sys/kernel/tracing type tracefs (rw,nosuid,nodev,noexec,relatime)
sunrpc on /run/rpc_pipefs type rpc_pipefs (rw,relatime)
nfsd on /proc/fs/nfsd type nfsd (rw,relatime)
fusectl on /sys/fs/fuse/connections type fusectl (rw,nosuid,nodev,noexec,relatime)
configfs on /sys/kernel/config type configfs (rw,nosuid,nodev,noexec,relatime)
binfmt_misc on /proc/sys/fs/binfmt_misc type binfmt_misc (rw,nosuid,nodev,noexec,relatime)
mergerfs on /mnt/slow-storage type fuse.mergerfs (rw,relatime,user_id=0,group_id=0,default_permissions,allow_other)
/dev/sda2 on /boot type ext4 (rw,relatime)
/dev/sda1 on /boot/efi type vfat (rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=iso8859-1,shortname=mixed,errors=remount-ro)
/dev/sdc on /mnt/disk2 type btrfs (rw,relatime,space_cache,subvolid=257,subvol=/data)
/dev/sdc on /mnt/snapraid-content/disk2 type btrfs (rw,relatime,space_cache,subvolid=258,subvol=/content)
/dev/sde on /mnt/snapraid-content/disk1 type btrfs (rw,relatime,space_cache,subvolid=258,subvol=/content)
/dev/sde on /mnt/disk1 type btrfs (rw,relatime,space_cache,subvolid=256,subvol=/data)
/var/lib/snapd/snaps/core20_1634.snap on /snap/core20/1634 type squashfs (ro,nodev,relatime,x-gdu.hide)
/var/lib/snapd/snaps/snapd_16292.snap on /snap/snapd/16292 type squashfs (ro,nodev,relatime,x-gdu.hide)
/var/lib/snapd/snaps/snapd_17336.snap on /snap/snapd/17336 type squashfs (ro,nodev,relatime,x-gdu.hide)
/var/lib/snapd/snaps/core20_1623.snap on /snap/core20/1623 type squashfs (ro,nodev,relatime,x-gdu.hide)
/var/lib/snapd/snaps/lxd_22753.snap on /snap/lxd/22753 type squashfs (ro,nodev,relatime,x-gdu.hide)
/dev/sdd1 on /mnt/parity1 type xfs (rw,relatime,attr2,inode64,logbufs=8,logbsize=32k,noquota)
tmpfs on /run/snapd/ns type tmpfs (rw,nosuid,nodev,noexec,relatime,size=398812k,mode=755)
nsfs on /run/snapd/ns/lxd.mnt type nsfs (rw)
tracefs on /sys/kernel/debug/tracing type tracefs (rw,nosuid,nodev,noexec,relatime)
tmpfs on /run/user/1000 type tmpfs (rw,nosuid,nodev,relatime,size=398808k,mode=700,uid=1000,gid=1000)
autotier on /mnt/autotier type fuse.autotier (rw,nosuid,nodev,relatime,user_id=0,group_id=0,default_permissions,allow_other)
/dev/nvme0n1 on /cache type btrfs (rw,relatime,ssd,space_cache,subvolid=5,subvol=/)

```

#### Btrfs raw-speed disk results.

As expected, ~900 MB/s writes. Matches observations in unraid trial for the same hardware.

```
Starting 8 processes
fiotest: Laying out IO file (1 file / 16384MiB)
Jobs: 4 (f=0): [_(2),f(3),_(1),f(1),_(1)][100.0%][w=894MiB/s][w=893 IOPS][eta 00m:00s]
fiotest: (groupid=0, jobs=8): err= 0: pid=53864: Fri Nov  4 00:44:23 2022
  write: IOPS=901, BW=902MiB/s (946MB/s)(52.9GiB/60059msec); 0 zone resets
    slat (usec): min=434, max=202119, avg=1705.52, stdev=5436.46
    clat (msec): min=3, max=263, avg=69.19, stdev=34.71
     lat (msec): min=3, max=277, avg=70.90, stdev=35.30
    clat percentiles (msec):
     |  1.00th=[   14],  5.00th=[   20], 10.00th=[   24], 20.00th=[   32],
     | 30.00th=[   50], 40.00th=[   61], 50.00th=[   70], 60.00th=[   78],
     | 70.00th=[   87], 80.00th=[  102], 90.00th=[  111], 95.00th=[  126],
     | 99.00th=[  161], 99.50th=[  174], 99.90th=[  207], 99.95th=[  222],
     | 99.99th=[  243]
   bw (  KiB/s): min=442249, max=2527361, per=99.97%, avg=923157.66, stdev=47906.96, samples=960
   iops        : min=  431, max= 2467, avg=901.15, stdev=46.79, samples=960
  lat (msec)   : 4=0.01%, 10=0.04%, 20=6.16%, 50=23.95%, 100=49.08%
  lat (msec)   : 250=20.76%, 500=0.01%
  cpu          : usr=0.30%, sys=5.05%, ctx=59733, majf=0, minf=88
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=99.9%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,54162,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=902MiB/s (946MB/s), 902MiB/s-902MiB/s (946MB/s-946MB/s), io=52.9GiB (56.8GB), run=60059-60059msec

```

#### /cache BTRFS mergerfs test.

TL;DR **Surprising results, w/o ZFS. Performance penalty is ~15%!**

```
root@nas:/mnt# mount /mnt/cached/
root@nas:/mnt# df -h /mnt/cached/
Filesystem      Size  Used Avail Use% Mounted on
mergerfs        239G   17G  222G   7% /mnt/cached
Starting 8 processes
fiotest: Laying out IO file (1 file / 16384MiB)
Jobs: 3 (f=3): [_(3),f(1),_(2),f(2)][100.0%][eta 00m:00s]
fiotest: (groupid=0, jobs=8): err= 0: pid=55377: Fri Nov  4 00:48:28 2022
  write: IOPS=770, BW=771MiB/s (808MB/s)(45.2GiB/60022msec); 0 zone resets
    slat (usec): min=16, max=80166, avg=10360.79, stdev=5295.21
    clat (msec): min=2, max=203, avg=72.59, stdev=13.58
     lat (msec): min=2, max=219, avg=82.95, stdev=14.65
    clat percentiles (msec):
     |  1.00th=[   40],  5.00th=[   61], 10.00th=[   63], 20.00th=[   69],
     | 30.00th=[   70], 40.00th=[   70], 50.00th=[   71], 60.00th=[   72],
     | 70.00th=[   73], 80.00th=[   74], 90.00th=[   83], 95.00th=[   96],
     | 99.00th=[  132], 99.50th=[  144], 99.90th=[  165], 99.95th=[  171],
     | 99.99th=[  190]
   bw (  KiB/s): min=571253, max=913408, per=99.87%, avg=788216.07, stdev=7550.71, samples=960
   iops        : min=  557, max=  892, avg=769.35, stdev= 7.39, samples=960
  lat (msec)   : 4=0.01%, 10=0.09%, 20=0.11%, 50=1.72%, 100=93.88%
  lat (msec)   : 250=4.20%
  cpu          : usr=0.28%, sys=1.29%, ctx=89094, majf=0, minf=89
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=99.9%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,46262,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=771MiB/s (808MB/s), 771MiB/s-771MiB/s (808MB/s-808MB/s), io=45.2GiB (48.5GB), run=60022-60022msec

```

# Autotier experiment

TL;DR **Worst performance out of all (50% mergerfs performance). Unmaintained project by 45Drives.**

Unrelated to mergerfs and just for fun. https://github.com/45Drives/autotier feels to be an `abandoned` project (I based this on a lack of response by the owner on open issues and lack of updates since 2021), still this project is another FUSE solution that seems to natively integrate the "move files between storage tiers for me" ideals.

Let's kick the tires on it on my setup. I expect poor performance here: https://github.com/45Drives/autotier/issues/38

### autotierfs

Filesystem is mounted manually via these options:

```
autotierfs /mnt/autotier -o allow_other,default_permissions
```

The configuration of it:

```
# cat /etc/autotier.conf
# autotier config
[Global]                       # global settings
Log Level = 1                  # 0 = none, 1 = normal, 2 = debug
Tier Period = 1000             # number of seconds between file move batches
Copy Buffer Size = 1 MiB       # size of buffer for moving files between tiers

[Tier 1]                       # tier name (can be anything)
Path = /cache                         # full path to tier storage pool
Quota = 20 %                  # absolute or % usage to keep tier under
# Quota format: x ( % | [K..T][i]B )
# Example: Quota = 5.3 TiB

[Tier 2]
Path = /mnt/slow-storage
Quota = 100 %

```

Results, poor as expected.

```
Starting 8 processes
Jobs: 8 (f=8): [W(2),f(3),W(2),f(1)][15.2%][w=215MiB/s][w=215 IOPS][eta 11m:16s]
fiotest: (groupid=0, jobs=8): err= 0: pid=43270: Fri Nov  4 00:17:35 2022
  write: IOPS=183, BW=184MiB/s (193MB/s)(10.8GiB/60112msec); 0 zone resets
    slat (usec): min=101, max=854743, avg=43446.05, stdev=34704.34
    clat (msec): min=23, max=1337, avg=304.13, stdev=85.28
     lat (msec): min=23, max=1341, avg=347.57, stdev=92.01
    clat percentiles (msec):
     |  1.00th=[  171],  5.00th=[  211], 10.00th=[  228], 20.00th=[  249],
     | 30.00th=[  266], 40.00th=[  279], 50.00th=[  296], 60.00th=[  313],
     | 70.00th=[  330], 80.00th=[  351], 90.00th=[  384], 95.00th=[  418],
     | 99.00th=[  493], 99.50th=[  919], 99.90th=[ 1217], 99.95th=[ 1250],
     | 99.99th=[ 1301]
   bw (  KiB/s): min=67571, max=274432, per=100.00%, avg=189065.93, stdev=4192.32, samples=952
   iops        : min=   65, max=  268, avg=184.20, stdev= 4.11, samples=952
  lat (msec)   : 50=0.01%, 100=0.09%, 250=20.19%, 500=78.80%, 750=0.41%
  lat (msec)   : 1000=0.06%, 2000=0.44%
  cpu          : usr=0.08%, sys=0.34%, ctx=34828, majf=0, minf=98
  IO depths    : 1=0.1%, 2=0.1%, 4=0.3%, 8=99.5%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=99.9%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,11051,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=184MiB/s (193MB/s), 184MiB/s-184MiB/s (193MB/s-193MB/s), io=10.8GiB (11.6GB), run=60112-60112msec

```

