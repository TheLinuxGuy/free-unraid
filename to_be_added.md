
[3:0:0:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sdc << parity /mnt/parity1
[3:0:1:0]    disk    ATA      WDC WD80EFZX-68U 0A83  /dev/sdd << /mnt/btrfs-roots/mergerfsdisk1
[3:0:2:0]    disk    ATA      WDC WD180EDGZ-11 0A85  /dev/sde << /mnt/btrfs-roots/mergerfsdisk2


mkfs.btrfs -f -L mergerfsdisk1 /dev/sdd
mkfs.btrfs -f -L mergerfsdisk2 /dev/sde
# add to /etc/fstab (root btrfs)
mount /mnt/btrfs-roots/mergerfsdisk1
btrfs subvolume create /mnt/btrfs-roots/mergerfsdisk1/data
mount /mnt/btrfs-roots/mergerfsdisk2
btrfs subvolume create /mnt/btrfs-roots/mergerfsdisk2/data
mkdir /mnt/disk{1,2}
# add to /etc/fstab (data subvolumes)
mount /mnt/disk1
mount /mnt/disk2
btrfs subvolume create /mnt/btrfs-roots/mergerfsdisk1/content
btrfs subvolume create /mnt/btrfs-roots/mergerfsdisk2/content
mkdir -p /mnt/snapraid-content/disk{1,2}
mount /mnt/snapraid-content/disk1
mount /mnt/snapraid-content/disk2
# Now we can unmount the parent-root-mounts
umount /mnt/btrfs-roots/mergerfsdisk1
umount /mnt/btrfs-roots/mergerfsdisk2


# mergerfs
wget https://github.com/trapexit/mergerfs/releases/download/2.33.5/mergerfs_2.33.5.ubuntu-focal_amd64.deb
dpkg -i mergerfs_2.33.5.ubuntu-focal_amd64.deb

# add fstab slow-storage
/mnt/disk* /mnt/storage fuse.mergerfs defaults,nonempty,allow_other,use_ino,cache.files=off,moveonenospc=true,dropcacheonclose=true,minfreespace=200G,fsname=mergerfs 0 0

# Update /etc/snapraid.conf file with disks maps.

# Snapper configs for each disks
snapper -c mergerfsdisk1 create-config -t mergerfsdisk /mnt/disk1
snapper -c mergerfsdisk2 create-config -t mergerfsdisk /mnt/disk2

# verify
snapper list-configs

# instsall snapraid-btrfs setup and then verify with
snapraid-btrfs ls

# install runner
git clone https://github.com/fmoledina/snapraid-btrfs-runner.git /opt/snapraid-btrfs-runner
