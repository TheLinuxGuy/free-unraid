# Baseline benchmarks

### Hardware specs
- Intel i5 13400
- 64GB DDR4
- Asus Prime Z790M-Plus D4
  
#### Disks

```bash
root@bpve:~# lsscsi
[4:0:0:0]    disk    ATA      Samsung SSD 840  6B0Q  /dev/sda 
[5:0:0:0]    disk    ATA      ST18000NE000-3G6 EN01  /dev/sde 
[6:0:0:0]    disk    ATA      WDC WD140EDFZ-11 0A81  /dev/sdc 
[7:0:0:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdd 
[8:0:0:0]    disk    Linux    File-Stor Gadget 0510  /dev/sdb 
[N:0:6:1]    disk    Samsung SSD 980 PRO 2TB__1                 /dev/nvme0n1
[N:1:1:1]    disk    Samsung SSD 990 PRO 2TB__1                 /dev/nvme1n1
[N:2:6:1]    disk    Samsung SSD 970 EVO Plus 2TB__1            /dev/nvme2n1
root@bpve:~# uname -a
Linux bpve 6.14.11-3-pve #1 SMP PREEMPT_DYNAMIC PMX 6.14.11-3 (2025-09-22T10:13Z) x86_64 GNU/Linux

```

### Preparation

```bash
DEVICE=sdc && sudo mkfs.xfs -f /dev/$DEVICE && sudo mkdir -p /mnt/$DEVICE && sudo mount /dev/$DEVICE /mnt/$DEVICE
root@bpve:~# mount | grep xfs
/dev/sdc on /mnt/sdc type xfs (rw,relatime,attr2,inode64,logbufs=8,logbsize=32k,noquota)
/dev/sdd on /mnt/sdd type xfs (rw,relatime,attr2,inode64,logbufs=8,logbsize=32k,noquota)
/dev/sdb on /mnt/sdb type xfs (rw,relatime,attr2,inode64,logbufs=8,logbsize=32k,noquota)
root@bpve:~# lsscsi
[5:0:0:0]    disk    ATA      ST18000NE000-3G6 EN01  /dev/sdb 
[6:0:0:0]    disk    ATA      WDC WD140EDFZ-11 0A81  /dev/sdc 
[7:0:0:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdd 
```

## Baselines

### /dev/sdb ST18000NE000

```bash
Run status group 0 (all jobs):
  WRITE: bw=194MiB/s (203MB/s), 194MiB/s-194MiB/s (203MB/s-203MB/s), io=11.4GiB (12.2GB), run=60245-60245msec

Disk stats (read/write):
  sdb: ios=0/12235, sectors=0/24424736, merge=0/46, ticks=0/3959195, in_queue=3964198, util=99.90%
write_iops: (g=0): rw=randwrite, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=libaio, iodepth=64

Run status group 0 (all jobs):
  WRITE: bw=6471KiB/s (6626kB/s), 6471KiB/s-6471KiB/s (6626kB/s-6626kB/s), io=379MiB (398MB), run=60055-60055msec

Disk stats (read/write):
  sdb: ios=0/99091, sectors=0/805880, merge=0/1642, ticks=0/3922171, in_queue=3923568, util=99.87%
read_throughput: (g=0): rw=read, bs=(R) 1024KiB-1024KiB, (W) 1024KiB-1024KiB, (T) 1024KiB-1024KiB, ioengine=libaio, iodepth=64

Run status group 0 (all jobs):
   READ: bw=213MiB/s (224MB/s), 213MiB/s-213MiB/s (224MB/s-224MB/s), io=12.6GiB (13.5GB), run=60279-60279msec

Disk stats (read/write):
  sdb: ios=13273/5, sectors=26759168/128, merge=49/5, ticks=3973674/1524, in_queue=3975535, util=99.93%


Run status group 0 (all jobs):
   READ: bw=49.0MiB/s (51.4MB/s), 49.0MiB/s-49.0MiB/s (51.4MB/s-51.4MB/s), io=2943MiB (3086MB), run=60004-60004msec

Disk stats (read/write):
  sdb: ios=743801/5, sectors=6063952/128, merge=14193/5, ticks=3904867/48, in_queue=3904945, util=99.88%
```

### /dev/sdc WDC WD140EDFZ-11

```bash
Run status group 0 (all jobs):
  WRITE: bw=189MiB/s (199MB/s), 189MiB/s-189MiB/s (199MB/s-199MB/s), io=11.2GiB (12.0GB), run=60378-60378msec

Disk stats (read/write):
  sdc: ios=0/12805, sectors=0/23865632, merge=0/92, ticks=0/3972163, in_queue=3975964, util=99.89%
write_iops: (g=0): rw=randwrite, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=libaio, iodepth=64

Run status group 0 (all jobs):
  WRITE: bw=7588KiB/s (7771kB/s), 7588KiB/s-7588KiB/s (7771kB/s-7771kB/s), io=446MiB (467MB), run=60129-60129msec

Disk stats (read/write):
  sdc: ios=0/118047, sectors=0/959480, merge=0/1883, ticks=0/3904867, in_queue=3909161, util=99.87%


Run status group 0 (all jobs):
   READ: bw=206MiB/s (216MB/s), 206MiB/s-206MiB/s (216MB/s-216MB/s), io=12.2GiB (13.1GB), run=60358-60358msec

Disk stats (read/write):
  sdc: ios=12898/5, sectors=25907200/128, merge=50/5, ticks=3971068/1486, in_queue=3972918, util=99.89%

Run status group 0 (all jobs):
   READ: bw=27.4MiB/s (28.7MB/s), 27.4MiB/s-27.4MiB/s (28.7MB/s-28.7MB/s), io=1642MiB (1721MB), run=60007-60007msec

Disk stats (read/write):
  sdc: ios=420247/5, sectors=3423456/128, merge=7688/5, ticks=3907777/146, in_queue=3908028, util=99.89%
```
