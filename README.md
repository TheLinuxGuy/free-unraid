# free-unraid

This repository is a `work-in-progress` of notes and experiments with attempting to replicate UNRAID features using all open-source tools, scripts and utilities. 

This repository makes no guarantees; use information presented here at your own risk. Do you wish to contribute? Submit a pull request. 

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

## The recipe

The following open-source projects seem to be able to help reach my goals. It requires elbow grease and stich this all together manually to mimic unraid.

- [SnapRAID](https://www.snapraid.it). Provides data parity, backups, checksumming of existing backups. 
    - [Claims to be better than UNRAID's](https://www.snapraid.it/compare) own parity system with the ability to 'fix silent errors' and 'verify file integrity' among others.
- [BRTFS Filesystem](https://btrfs.wiki.kernel.org/index.php/Main_Page) similar to ZFS in that it provides be the ability to 'send/receive' data streams (ala `zfs send`) with the added benefit that I can run individual `disk scrubs` to detect hardware issues that require me to restore from snapraid parity. 
- [MergerFS](https://github.com/trapexit/mergerfs). FUSE filesystem that allows me to 'stitch together' multiple hard drives with different mountpoints and takes care of directing I/O operations based on a set of rules/criteria/policies.
- [snapraid-btrfs](https://github.com/automorphism88/snapraid-btrfs). Automation and helper script for BRTFS based snapraid configurations. Using BRTFS snapshots as the data source for running 'snapraid sync' allows me to continue using my system 24/7 without data corruption risks or downtime when I want to build my parity/snapraid backups.
- [snapraid-btrfs-runner](https://github.com/fmoledina/snapraid-btrfs-runner). Helper script that runs `snapraid-btrfs` sending its output to the console, a log file and via email. 