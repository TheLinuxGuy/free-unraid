# free-unraid

This repository is a `work-in-progress` of notes and experiments with attempting to replicate UNRAID features using all open-source tools, scripts and utilities. 

This repository makes no guarantees; use information presented here at your own risk. Do you wish to contribute? Submit a pull request. 

#### 12/25/2022 update

My original intended configuration with BRTFS+ZFS while working in practice gave me a lot of instability issues with NFS and down several *troubleshooting rabbit holes* - you will find notes about those issues scattered in the individual markdown sections in the repository.

This also means that "ideal setup" is not up to date with my `real` current configuration. Right now my setup is:
- /cache mdadm RAID1 NVME XFS mirror (bitmap disabled to improve performance)
- XFS filesystem on all physical hard disks. This means I am not using `snapraid-btrfs` and using simple snapraid+snapraid-runner.

Once my setup has several `airmiles` being stable and not crashing when sharing NFS/SMB I will do a cleanup of all markdown files. 

See [install_steps.md](install_steps.md) for a quick and dirty guide on standing up my current environment. Other sections may have more details on the specifics (e.g: mergerfs create policies & other settings)

## The "unraid" ideal setup

After several years running ZFS arrays, in 2022 I decided I wanted to experiment and take a different approach to my home media-server, which as of this writting has 30TB of digital media on a ZFS array.

ZFS is a robust filesystem and solution but it requires having all of your hard drives spinning 24x7 when serving data off the array. Most often than not I have about 2-3 concurrent Plex streams reading some media file that could be read from a single hard drive rather than 5 disks. Therefore one of my goals in 2022 is to lower my power consumption of my 24/7 home server.

### What's important for me?

1. **Low power consumption for 24/7 operation**. This means most hard drives must be spun-down.
1. **Must run opensource or free software (no licenses)**. Linux ideally.
1. **Some protection against bit-rot and checksumming of my data files**.
1. **File system should be able to detect hardware errors** (automatic repair is not necessary, since this isn't an array).
1. **I should be able to recover my files from a single disk catastropic event** (e.g: hardware failure, or specific data block bitrot)
1. **NVME caching (tiered storage)**. I want to write all new files to superfast storage (nvme) and later 'archive' my data into spinning hard drives.

### The recipe

The following open-source projects seem to be able to help reach my goals. It requires elbow grease and stich this all together manually to mimic unraid.

- [SnapRAID](https://www.snapraid.it). Provides data parity, backups, checksumming of existing backups. 
    - [Claims to be better than UNRAID's](https://www.snapraid.it/compare) own parity system with the ability to 'fix silent errors' and 'verify file integrity' among others.
- [BRTFS Filesystem](https://btrfs.wiki.kernel.org/index.php/Main_Page) similar to ZFS in that it provides be the ability to 'send/receive' data streams (ala `zfs send`) with the added benefit that I can run individual `disk scrubs` to detect hardware issues that require me to restore from snapraid parity. **My observed Btrfs performance is that its poor compared to XFS filesystem on linux.** *Since we use btrfs only for the 'data' disks in the slow mergerfs pool we are not sensitive to speed.*
- **XFS Filesystem for NVME cache on mdadm array**. After finding bugs and instability in my ZFS+NFS+mergerfs implementation my cache disks are now formatted to XFS in RAID1. I did not use btrfs raid1 natively here because btrfs performance was poor (50% throughtput penalty). XFS was able to match ZFS raw speeds (without arc) ~900MB/s.
- [MergerFS](https://github.com/trapexit/mergerfs). FUSE filesystem that allows me to 'stitch together' multiple hard drives with different mountpoints and takes care of directing I/O operations based on a set of rules/criteria/policies.
- [snapraid-btrfs](https://github.com/automorphism88/snapraid-btrfs). Automation and helper script for BRTFS based snapraid configurations. Using BRTFS snapshots as the data source for running 'snapraid sync' allows me to continue using my system 24/7 without data corruption risks or downtime when I want to build my parity/snapraid backups.
- [snapraid-btrfs-runner](https://github.com/fmoledina/snapraid-btrfs-runner). Helper script that runs `snapraid-btrfs` sending its output to the console, a log file and via email. 
- [hd-idle](https://github.com/adelolmo/hd-idle). Helper script running on systemd ensuring that spinning hard drives are spun down (standby) and set into a lower power consumption power state. 
- [btrfs-list](https://github.com/speed47/btrfs-list). Script providing a nice tree-style view of btrfs subvolumes/snapshots (ala `zfs list`).

## OS install and base packages install

```
apt-get install zfsutils-linux cockpit-pcp btrfs-progs libbtrfsutil1 btrfs-compsize duc smartmontools
```

## ~~ZFS cache pool setup~~
**WARNING! DEPRECATED** NFS+ZFS is unstable with this setup. Follow XFS+mdadm below.

RAID1 of two SSD disks. We'll write all stuff here then purge to 'cold-storage' slower disks via cron.

```
zpool create -o ashift=12 cache mirror /dev/sdb /dev/nvme0n1
```

## XFS RAID1 mirror mdadm

See [mergerfs](mergerfs.md) for details on ZFS instability. For our cache pool we will use XFS filesystem. Set up the NVME cache as follows:

```
mdadm --create --verbose /dev/md0  --bitmap=none --level=mirror --raid-devices=2 /dev/nvme0n1 /dev/sdb
mkfs.xfs -f -L cache /dev/md0
mdadm --detail /dev/md0
```

Remember to add a mountpoint to start at boot. 

## BTRFS (disk setup guide)

### BTRFS Commands TL;DR

```
btrfs device scan
```

We will format the entire disk without a partition scheme. 

```
mkfs.btrfs -L disk1 /dev/sdb
mkdir /mnt/disk1
mount /dev/sdb /mnt/disk1
mkfs.btrfs -L disk2 /dev/sdc 
mkdir /mnt/disk2
mount /dev/sdc /mnt/disk2
```

Confirm

```
btrfs filesystem show
btrfs filesystem usage /mnt/disk1
btrfs filesystem usage /mnt/disk2
```

## Disk scrubbing on BTRFS

```
btrfs scrub start /mnt/disk1
btrfs scrub status /mnt/disk1
```

## Checking tiered storage mover process state

```
ps -auxq $(cat /var/run/mover.pid)
```