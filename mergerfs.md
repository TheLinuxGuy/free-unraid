# MergerFS 

MergerFS is used to "merge" all physical distint disk partitions (/mnt/disk*) into a single logical volume mount.

### Policies

https://github.com/trapexit/mergerfs#policy-descriptions

Assuming a home media server with top-level folders /movies and /tv - we likely want to keep season folders together on the same disk.

At the same time, you may want to fill up one hard drive first before starting to place data onto a secondary disk.

For my situation, I feel "most shared path" policies are best suited for this criteria. The real question is do we want to fill up a single disk to the brim before writing data to another disk?

#### Thoughts about CREATE policies

If we fill up a single disk to full before writing to disk2 - we run the risk that if disk1 fails and our snapraid backup fails we lose a lot of information.

If we already have 2 physical hard disks connected to the server, 24/7 even if spun down you are already consuming 5 watts of energy for that disk being connected to the server.

IMO, unless you want to "slowly grow" your number of hard drives its best to "spread across" your media usage across hard disks. This way, even if everything works as expected with snapraid being your backup - the data restore for a new whole disk replacement will take less time if it only needs to recover half the total raw storage disk size vs. a full-raw-disk.

Therefore `msplus (most shared path, least used space)` is what we would want. You can always change this later.

### /etc/fstab (TL;DR) config

The `/etc/fstab` for our slow disks running BTRFS would look like as follows:

```
# add fstab slow-storage
/mnt/disk* /mnt/slow-storage fuse.mergerfs defaults,nonempty,allow_other,use_ino,category.create=lfs,cache.files=off,moveonenospc=true,dropcacheonclose=true,minfreespace=300G,fsname=mergerfs 0 0

# add fstab /cache nvme
/cache:/mnt/slow-storage /mnt/cached fuse.mergerfs defaults,nonempty,allow_other,use_ino,noforget,inodecalc=path-hash,security_capability=false,cache.files=partial,category.create=lfs,moveonenospc=true,dropcacheonclose=true,minfreespace=4G,fsname=mergerfs 0 0
```

Caveats of `msplus` means each single disk needs to have the top-level folder created for it (e.g: "movies" and "tv" folder). Therefore `/mnt/diskX/movies` would allow the path walk-back logic to dump data into that disk. 

## NVME Tiered Cache Strategy

https://github.com/trapexit/mergerfs#tiered-caching

To attempt to mirror what unraid provides with their share "cache" we are going to setup yet another mergerfs "pool" or mountpoint with just our nvme disks. 

Recall that I chose to use ZFS and RAID1 mirror for this purpose to provide assurances that my data would not be lost before it gets moved onto parity-protected-snapraid-slow-storage-disks.

### NFS tweaks that were added

```
noforget,inodecalc=path-hash,security_capability=false,cache.files=partial,category.create=lfs
```

## Installing mergerfs on ubuntu 21.04 steps

```
wget https://github.com/trapexit/mergerfs/releases/download/2.33.5/mergerfs_2.33.5.ubuntu-focal_amd64.deb
dpkg -i mergerfs_2.33.5.ubuntu-focal_amd64.deb
```

## Other notes

1. Update /etc/snapraid.conf with disk maps.
1. Ensure `snapper` configs for each disk exist. (`snapper -c mergerfsdisk1 create-config -t mergerfsdisk /mnt/disk1`)
1. Install snapraid-btrfs and validate with `snapraid-btrfs ls` command.
1. Install snapraid-btrfs-runner (`git clone https://github.com/fmoledina/snapraid-btrfs-runner.git /opt/snapraid-btrfs-runner`)