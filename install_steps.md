# Installing OS and tools

Warning: this may be incomplete. I provide no support or guarantees these steps will always work.

Assumption: (1) blank virtual machine in proxmox will be our "free-unraid NAS" to be setup. (2) You passthru your physical hard disks to VM via passthrough. (3) You want to mirror my setup and have cockpit for Web UI to manage your shares and samba. (4) you know your way around linux / basic system admin stuff.

### High level overview

1. Install Ubuntu Server OS (enable SSH). Download ubuntu server DVD image; follow GUI install steps.
1. Do first login. Run all updates (apt-get update; apt-get dist-upgrade; 'do-release-upgrade')
1. Shutdown VM - in proxmox configure the PCI passthrough to SATA disks controllers. Map the NVME drive via passthrough.
1. Install repo https://repo.45drives.com via `curl -sSL https://repo.45drives.com/setup | sudo bash`
1. Install cockpit and other tools 
```
apt-get install zfsutils-linux cockpit-pcp btrfs-progs libbtrfsutil1 btrfs-compsize duc smartmontools cockpit-benchmark cockpit-file-sharing cockpit-identities cockpit-navigator lsscsi pv
```
1. Web UI cockpit should now be available at localhost:9090 (or whatever IP the VM has)
1. Create the /cache NVME RAID1 XFS mirror
```
mdadm  --stop /dev/md*
mdadm --create --verbose /dev/md0  --bitmap=none --level=mirror --raid-devices=2 /dev/nvme0n1 /dev/sdb
mkfs.xfs -f -L cache /dev/md0
mdadm --detail /dev/md0
```
1. Setup `/etc/fstab` for /cache ensuring it mounts at boot.
1. Install mergerfs (e.g: mergerfs_2.34.1.ubuntu-jammy_amd64.deb)
1. Refer to mergerfs.md for `/etc/fstab` configuration for disks. Ensure `/mnt/slow-storage` and `/mnt/cache` folders exists.
1. Install `hd-idle` ensure its enabled and its configuration file set to log to file `/var/log/hd-idle.log` and begin idle at 180 seconds.
1. Build a .deb package of snapraid (using docker).
```
# these steps assume a valid, working docker installation
apt update && apt install git -y
mkdir ~/tmp && cd ~/tmp
git clone https://github.com/IronicBadger/docker-snapraid
cd docker-snapraid
chmod +x build.sh
./build.sh
sudo dpkg -i build/snapraid-from-source.deb
```
1. Copy the .deb file to NAS server; install it. `dpkg -i snapraid-from-source.deb`. Verify with `snapraid --version`.
1. Ensure `/etc/snapraid.conf` contains:
```
# SnapRAID configuration file

# Parity location(s)
1-parity /mnt/parity/snapraid.parity
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
1. Install snapraid-runner `git clone https://github.com/Chronial/snapraid-runner.git /opt/snapraid-runner`
1. Create log file for snapraid runs `touch /var/log/snapraid.log`
1. `mv snapraid-runner.conf.example snapraid-runner.conf` then configure as expected, including cronjob.[Example file](snapraid_btrfs_runner.md).


