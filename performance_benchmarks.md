# Performance

**Note: after upgrading from ZFS 0.8.4 to ZFS 2.1.4 (+kernel 5.15.0-52-generic) the noted ZFS performance issues have gone away. There appears to be almost no performance penalty of using ZFS+mergerfs.**

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

**Update: 11/05/22 - After upgrade from ZFS 0.8.4 to ZFS 2.1.4 the below performance issues don't exist.**

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

### /mnt/cached ZFS 2.1.4 write to mergerfs-ZFS benchmarks (performance fixed!)

```
# dpkg -l | grep zfs
ii  libzfs4linux                          2.1.4-0ubuntu0.1                        amd64        OpenZFS filesystem library for Linux - general support
ii  zfs-zed                               2.1.4-0ubuntu0.1                        amd64        OpenZFS Event Daemon
ii  zfsutils-linux                        2.1.4-0ubuntu0.1                        amd64        command-line tools to manage OpenZFS filesystems
# fio --name=fiotest --filename=/mnt/cached/speed --size=16Gb --rw=write --bs=1M --direct=1 --numjobs=8 --ioengine=libaio --iodepth=8 --group_reporting --runtime=60 --startdelay=60
Starting 8 processes
fiotest: Laying out IO file (1 file / 16384MiB)
Jobs: 8 (f=0): [f(8)][100.0%][w=707MiB/s][w=707 IOPS][eta 00m:00s]
fiotest: (groupid=0, jobs=8): err= 0: pid=93346: Sat Nov  5 01:56:46 2022
  write: IOPS=944, BW=944MiB/s (990MB/s)(55.3GiB/60039msec); 0 zone resets
    slat (usec): min=12, max=81965, avg=8457.02, stdev=8863.16
    clat (usec): min=177, max=349728, avg=59322.78, stdev=55613.28
     lat (usec): min=198, max=392259, avg=67780.92, stdev=63148.08
    clat percentiles (msec):
     |  1.00th=[    3],  5.00th=[    9], 10.00th=[   14], 20.00th=[   18],
     | 30.00th=[   23], 40.00th=[   31], 50.00th=[   40], 60.00th=[   51],
     | 70.00th=[   65], 80.00th=[   97], 90.00th=[  142], 95.00th=[  184],
     | 99.00th=[  245], 99.50th=[  266], 99.90th=[  305], 99.95th=[  326],
     | 99.99th=[  338]
   bw (  KiB/s): min=198656, max=5643635, per=99.82%, avg=964905.73, stdev=88839.34, samples=952
   iops        : min=  194, max= 5511, avg=942.20, stdev=86.75, samples=952
  lat (usec)   : 250=0.01%, 500=0.15%, 750=0.20%, 1000=0.18%
  lat (msec)   : 2=0.39%, 4=0.67%, 10=5.83%, 20=18.35%, 50=34.41%
  lat (msec)   : 100=20.43%, 250=18.56%, 500=0.81%
  cpu          : usr=0.97%, sys=0.64%, ctx=106614, majf=0, minf=107
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=99.9%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,56678,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=944MiB/s (990MB/s), 944MiB/s-944MiB/s (990MB/s-990MB/s), io=55.3GiB (59.4GB), run=60039-60039msec

```

Performance 990MB/s on RAID1 ZFS of dual nvme. Goal achieved.

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
/dev/nvme0n1 on /cache type btrfs (rw,relatime,ssd,space_cache,subvolid=5,subvol=/)

```


#### Does btrfs raid1 work with mergerfs?

Let's test.

```
root@nas:/home/gfm# mkfs.btrfs -f -L cached-mirror -m raid1 -d raid1 /dev/nvme0n1 /dev/sdb                               btrfs-progs v5.4.1
See http://btrfs.wiki.kernel.org for more information.

Label:              cached-mirror
UUID:               0c4241e9-e4ea-41b6-9dab-a3cc4b936edb
Node size:          16384
Sector size:        4096
Filesystem size:    476.96GiB
Block group profiles:
  Data:             RAID1             1.00GiB
  Metadata:         RAID1             1.00GiB
  System:           RAID1             8.00MiB
SSD detected:       yes
Incompat features:  extref, skinny-metadata
Checksum:           crc32c
Number of devices:  2
Devices:
   ID        SIZE  PATH
    1   238.47GiB  /dev/nvme0n1
    2   238.49GiB  /dev/sdb

root@nas:/home/gfm# mount /dev/nvme0n1 /cache/
fio-3.16
Starting 8 processes
fiotest: Laying out IO file (1 file / 16384MiB)
Jobs: 7 (f=7): [W(1),_(1),W(6)][75.7%][eta 00m:44s]
fiotest: (groupid=0, jobs=8): err= 0: pid=14619: Fri Nov  4 01:48:09 2022
  write: IOPS=438, BW=438MiB/s (459MB/s)(32.5GiB/76061msec); 0 zone resets
    slat (usec): min=28, max=44590k, avg=7783.12, stdev=487469.23
    clat (usec): min=329, max=44735k, avg=134311.57, stdev=1290330.14
     lat (usec): min=532, max=44735k, avg=142095.86, stdev=1378714.43
    clat percentiles (usec):
     |  1.00th=[     644],  5.00th=[   13304], 10.00th=[   17957],
     | 20.00th=[   29492], 30.00th=[   43254], 40.00th=[   53740],
     | 50.00th=[   67634], 60.00th=[   83362], 70.00th=[  101188],
     | 80.00th=[  122160], 90.00th=[  181404], 95.00th=[  231736],
     | 99.00th=[  383779], 99.50th=[  463471], 99.90th=[17112761],
     | 99.95th=[17112761], 99.99th=[17112761]
   bw (  KiB/s): min=163819, max=2094826, per=100.00%, avg=739932.10, stdev=58373.76, samples=727
   iops        : min=  159, max= 2045, avg=721.74, stdev=56.99, samples=727
  lat (usec)   : 500=0.05%, 750=1.04%, 1000=0.50%
  lat (msec)   : 2=0.62%, 4=0.34%, 10=0.54%, 20=9.06%, 50=24.23%
  lat (msec)   : 100=33.28%, 250=26.57%, 500=3.46%, 750=0.17%, 1000=0.01%
  lat (msec)   : >=2000=0.15%
  cpu          : usr=0.43%, sys=0.45%, ctx=46384, majf=0, minf=88
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=99.8%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,33328,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=438MiB/s (459MB/s), 438MiB/s-438MiB/s (459MB/s-459MB/s), io=32.5GiB (34.9GB), run=76061-76061msec
```

BTRFS raid1 performance is really... poor wow. This isn't even with mergerfs enabled.

Let's see about it. **results are 15% performance penalty** in line with past mergerfs tests on btrfs.  Outcome: RAID1 on btrfs is probably not a good idea; lost 50% of raw performance before even mergerfs comes into play.

```
Run status group 0 (all jobs):
  WRITE: bw=296MiB/s (311MB/s), 296MiB/s-296MiB/s (311MB/s-311MB/s), io=17.4GiB (18.7GB), run=60172-60172msec
```

#### mdadm ext4 raid1 test

```
root@nas:/home/gfm# sgdisk -Z /dev/nvme0n1
Creating new GPT entries in memory.
GPT data structures destroyed! You may now partition the disk using fdisk or
other utilities.
root@nas:/home/gfm# sgdisk -Z /dev/sdb
Creating new GPT entries in memory.
GPT data structures destroyed! You may now partition the disk using fdisk or
other utilities.
root@nas:/home/gfm# mdadm --create /dev/md/cache /dev/nvme0n1 /dev/sdb --level=1 --raid-devices=2
mdadm: Note: this array has metadata at the start and
    may not be suitable as a boot device.  If you plan to
    store '/boot' on this device please ensure that
    your boot-loader understands md/v1.x metadata, or use
    --metadata=0.90
Continue creating array? y
mdadm: Defaulting to version 1.2 metadata
mdadm: array /dev/md/cache started.
root@nas:/home/gfm# mdadm --detail /dev/md/cache
/dev/md/cache:
           Version : 1.2
     Creation Time : Fri Nov  4 02:02:11 2022
        Raid Level : raid1
        Array Size : 249926976 (238.35 GiB 255.93 GB)
     Used Dev Size : 249926976 (238.35 GiB 255.93 GB)
      Raid Devices : 2
     Total Devices : 2
       Persistence : Superblock is persistent

     Intent Bitmap : Internal

       Update Time : Fri Nov  4 02:02:38 2022
             State : clean, resyncing
    Active Devices : 2
   Working Devices : 2
    Failed Devices : 0
     Spare Devices : 0

Consistency Policy : bitmap

     Resync Status : 2% complete

              Name : nas:cache  (local to host nas)
              UUID : dda209ab:ace57985:25895a5b:f3d95068
            Events : 4

    Number   Major   Minor   RaidDevice State
       0     259        0        0      active sync   /dev/nvme0n1
       1       8       16        1      active sync   /dev/sdb
root@nas:/home/gfm#  mkfs.ext4  /dev/md/cache
mke2fs 1.45.5 (07-Jan-2020)
Discarding device blocks: done
Creating filesystem with 62481744 4k blocks and 15622144 inodes
Filesystem UUID: 9bda5776-f50e-40fa-a826-8b2424de3f07
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424, 20480000, 23887872

Allocating group tables: done
Writing inode tables: done
Creating journal (262144 blocks): done
Writing superblocks and filesystem accounting information: done

root@nas:/home/gfm# mount /dev/md/cache /cache/
```

After waiting for resync to be complete. IO test. Maybe ZFS is just better at RAID1 w/o performance impacts.

```
Run status group 0 (all jobs):
  WRITE: bw=478MiB/s (502MB/s), 478MiB/s-478MiB/s (502MB/s-502MB/s), io=28.1GiB (30.1GB), run=60069-60069msec

Disk stats (read/write):
    md127: ios=0/228818, merge=0/0, ticks=0/0, in_queue=0, util=0.00%, aggrios=0/230087, aggrmerge=0/27, aggrticks=0/6898163, aggrin_queue=6647102, aggrutil=94.28%
  nvme0n1: ios=0/230087, merge=0/27, ticks=0/13717574, in_queue=13258980, util=54.05%
  sdb: ios=0/230087, merge=0/27, ticks=0/78753, in_queue=35224, util=94.28%

```

https://raid.wiki.kernel.org/index.php/Write-intent_bitmap
https://louwrentius.com/the-impact-of-the-mdadm-bitmap-on-raid-performance.html 

Write intent bitman may be screwing write performance. Let's disable

```
mdadm /dev/md127 --grow --bitmap=none
mdadm --detail /dev/md/cache
# mount
/dev/md127 on /cache type btrfs (rw,relatime,ssd,space_cache,subvolid=5,subvol=/)
# fio results
Run status group 0 (all jobs):
  WRITE: bw=540MiB/s (567MB/s), 540MiB/s-540MiB/s (567MB/s-567MB/s), io=31.7GiB (34.0GB), run=60032-60032msec

```

Interestingly, performance starts at peak speeds. Then CPU utilization jumps to 100% dropping performance. 

```
WRITE: bw=568MiB/s (596MB/s), 568MiB/s-568MiB/s (596MB/s-596MB/s), io=33.3GiB (35.8GB), run=60034-60034msec
```

Try something else but didn't help pefromance. 

```
mdadm --grow --bitmap=internal --bitmap-chunk=131072 /dev/md127
Run status group 0 (all jobs):
  WRITE: bw=329MiB/s (345MB/s), 329MiB/s-329MiB/s (345MB/s-345MB/s), io=19.4GiB (20.8GB), run=60263-60263msec

```

Kill mdadm array

```
mdadm -S /dev/md127
mdadm --zero-superblock /dev/sdb /dev/nvme0n1
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

Results, poor as expected (below results using ZFS)

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

#### Verify if ZFS is the reason for poor performance on autotier

Let's use btrfs here for this test. Same hardware, this time I made btrfs a RAID1. Re-mounted, same options. **autotier did not work with btrfs filesystem**.

```
mkfs.btrfs -f -L cachebtrfs -m raid1 -d raid1 /dev/sdb /dev/nvme0n1
```

debug btrfs

```
dmesg | grep BTRFS | egrep 'error|warning|failed'
```

```
root@nas:/mnt# btrfs fi df /cache/
Data, RAID1: total=33.00GiB, used=31.78GiB
System, RAID1: total=8.00MiB, used=16.00KiB
Metadata, RAID1: total=1.00GiB, used=17.23MiB
GlobalReserve, single: total=17.12MiB, used=0.00B
```

**Autotier on BTRFS did not work. Process was getting hung**. Let's use `ext4` filesystem instead.

```
root@nas:/home/gfm# umount /cache/
umount: /cache/: target is busy.
root@nas:/home/gfm# ps aux | grep autotier
root        9511  6.0  0.2 832460 11180 ?        Ssl  01:33   0:13 autotierfs /mnt/autotier -o allow_other,default_permissions
root       10949  0.0  0.0   6432   724 pts/0    S+   01:37   0:00 grep --color=auto autotier
root@nas:/home/gfm# kill -9 9511
root@nas:/home/gfm# umount /cache/
root@nas:/home/gfm# rm /var/lib/autotier/5685251811202329732/
adhoc.socket   conflicts.log  db/
root@nas:/home/gfm# rm /var/lib/autotier/5685251811202329732/adhoc.socket
root@nas:/home/gfm# mkfs -t ext4 /dev/nvme0n1
mke2fs 1.45.5 (07-Jan-2020)
/dev/nvme0n1 contains a btrfs file system labelled 'testme'
Proceed anyway? (y,N) y
Discarding device blocks: done
Creating filesystem with 62514774 4k blocks and 15630336 inodes
Filesystem UUID: ce2eed9e-8e10-4e0c-ab06-d11f17eefe2d
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424, 20480000, 23887872

Allocating group tables: done
Writing inode tables: done
Creating journal (262144 blocks):
done
Writing superblocks and filesystem accounting information: done

```

#### Now EXT4 autotier test results.

```
fio-3.16
Starting 8 processes
fiotest: Laying out IO file (1 file / 16384MiB)
Jobs: 8 (f=8): [W(8)][100.0%][w=640MiB/s][w=639 IOPS][eta 00m:00s]
fiotest: (groupid=0, jobs=8): err= 0: pid=12306: Fri Nov  4 01:41:48 2022
  write: IOPS=657, BW=658MiB/s (689MB/s)(38.5GiB/60030msec); 0 zone resets
    slat (usec): min=45, max=276076, avg=12158.02, stdev=19153.35
    clat (usec): min=828, max=562034, avg=85134.29, stdev=60544.23
     lat (usec): min=1052, max=573771, avg=97292.87, stdev=64876.67
    clat percentiles (msec):
     |  1.00th=[   40],  5.00th=[   46], 10.00th=[   51], 20.00th=[   55],
     | 30.00th=[   58], 40.00th=[   62], 50.00th=[   65], 60.00th=[   68],
     | 70.00th=[   73], 80.00th=[   87], 90.00th=[  155], 95.00th=[  213],
     | 99.00th=[  355], 99.50th=[  447], 99.90th=[  535], 99.95th=[  542],
     | 99.99th=[  558]
   bw (  KiB/s): min=94154, max=1044480, per=99.88%, avg=672475.66, stdev=22655.00, samples=960
   iops        : min=   90, max= 1020, avg=656.37, stdev=22.13, samples=960
  lat (usec)   : 1000=0.01%
  lat (msec)   : 2=0.01%, 4=0.01%, 10=0.02%, 20=0.06%, 50=9.76%
  lat (msec)   : 100=70.81%, 250=17.09%, 500=1.93%, 750=0.32%
  cpu          : usr=0.36%, sys=0.87%, ctx=121217, majf=0, minf=92
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=99.9%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.1%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,39471,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=8

Run status group 0 (all jobs):
  WRITE: bw=658MiB/s (689MB/s), 658MiB/s-658MiB/s (689MB/s-689MB/s), io=38.5GiB (41.4GB), run=60030-60030msec

```

2/3 of the drive's raw performance. `mergerfs` still much better. The only benefit to `autotier` would be its automatic promoting of files between tiers based on age and usage.

I'm a little uneasy on placing a depedency on `autotier` given that it doesn't seem to be maintained. IMO - `mergerfs + btrfs` is the winner combination.
