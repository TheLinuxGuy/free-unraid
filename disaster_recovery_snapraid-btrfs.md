# Disaster Recovery Scenarios

#### Expected behavior

1. Install new physical hard drive
1. Format with btrfs / prep.
1. Snapraid restores missing data on new physical disk (recovery).
1. After restore is complete, we should be back online. 

## Helpful sources

https://github.com/trapexit/backup-and-recovery-howtos/blob/master/docs/recovery_(mergerfs,snapraid).md 

## Pulling out a disk from the array

Given the following setup
```
/dev/sdc1                           17T  2.3T   15T  14% /mnt/parity1
/dev/sdd                           7.3T  140M  7.3T   1% /mnt/disk1
/dev/sde                            17T  2.4T   15T  15% /mnt/disk2
/dev/sdd                           7.3T  140M  7.3T   1% /mnt/snapraid-content/disk1
/dev/sde                            17T  2.4T   15T  15% /mnt/snapraid-content/disk2
mergerfs                            24T  2.4T   22T  10% /mnt/slow-storage
```

Let's pull out `/mnt/disk2` from the system. As you can see 2.4TB of data is used.

```
Oct 31 18:26:06 nas kernel: [40691.137391] BTRFS info (device sde): forced readonly
Oct 31 18:26:06 nas kernel: [40691.137392] BTRFS warning (device sde): Skipping commit of aborted transaction.
Oct 31 18:26:06 nas kernel: [40691.137392] BTRFS: error (device sde) in cleanup_transaction:1826: errno=-5 IO failure
Oct 31 18:26:06 nas kernel: [40691.137400] BTRFS info (device sde): delayed_refs has NO entry
Oct 31 18:26:06 nas kernel: [40691.137455] BTRFS error (device sde): commit super ret -5
Oct 31 18:26:06 nas systemd[1]: mnt-disk2.mount: Succeeded.
Oct 31 18:26:06 nas systemd[1]: Unmounted /mnt/disk2.
```


#### Procedure

1. Verify current /etc/snapraid.conf

```
# SnapRAID configuration file

# Parity location(s)
1-parity /mnt/parity1/snapraid.parity
#2-parity /mnt/parity2/snapraid.parity

# Content file location(s)
content /var/snapraid.content
content /mnt/snapraid-content/disk1/snapraid.content
content /mnt/snapraid-content/disk2/snapraid.content

# Data disks
data d1 /mnt/disk1
data d2 /mnt/disk2
#data d3 /mnt/disk3
#data d4 /mnt/disk4

# Excludes hidden files and directories
exclude *.unrecoverable
exclude /tmp/
exclude /lost+found/
exclude downloads/
exclude appdata/
exclude *.!sync
exclude /.snapshots/
```

We're failing `/dev/sde` aka `/mnt/disk2` aka `d2` in the config.

### /dev/sdf Brand new physical disk configure 

The `/dev/sde` drive is BTRFS configured with LABEL `mergerfsdisk2` let's format the replacement the same way.

```
mkfs.btrfs -L mergerfsdisk2 /dev/sdf
```

Let's temporarily mount it so we can create subvolumes. Folder `mergerfsdisk2` should already exist, if not create it.

```
mount /dev/sdf /mnt/btrfs-roots/mergerfsdisk2
```

Now let's create the subvolumes (mountpoints) used for DATA + snapraid.

```
btrfs subvolume create /mnt/btrfs-roots/mergerfsdisk2/data
btrfs subvolume create /mnt/btrfs-roots/mergerfsdisk2/content
umount /mnt/btrfs-roots/mergerfsdisk2
```

Let's remount the old existing `/etc/fstab` that was broken when we pulled the drives.

```
mount /mnt/snapraid-content/disk2
mount /mnt/disk2
```

Let's run recovery from snapraid (inside 'screen' recommended). This will read parity disk and write on the new disk recovered data fragments. 

```
mkdir -p /root/drecovery/
snapraid -d d2 -l /root/drecovery/snapraid-disk2-fix.log fix
```

Expected output

```
100% completed, 0 MB accessed in 2:59

 8870882 errors
 8870882 recovered errors
       0 unrecoverable errors
Everything OK
```

Now we need to verify data (hashing verification stage).

`snapraid -d d2 -a check`