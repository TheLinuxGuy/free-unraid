# Promox Virtual Environment

This is a list of notes related to Proxmox. We use Proxmox as the top-layer of my setup (meaning NAS is a VM with PCIe passthrough for disks HBA controllers).

## CPU Pinning (to be researched)

https://www.youtube.com/watch?v=-c_451HV6fE < useful info>

```
#lscpu -e
# lstopo
```

## Avoid pvestatd mkdir bug

Looks like proxmox has a daemon that checks NFS mount points configured with "ISO" and "Container Templates" constantly to make sure the NFS share is responsive (<2 seconds). This may be problematic if unraid-mover.py script keeps deleting folder 'templates/iso/' and /templates/cache/'

You may see these kind of errors (its because NAS didnt respond quick enough to directory listing; due to hdd sleeping in the slow branch where folders exist)
```
Nov 24 01:36:50 centrix pvestatd[2102]: storage 'unraid' is not online
Nov 24 01:36:53 centrix pvestatd[2102]: unable to activate storage 'unraid' - directory '/mnt/pve/unraid' does not exist or is unreachable
Nov 24 01:37:00 centrix pvestatd[2102]: mkdir /mnt/pve/unraid/template: No space left on device at /usr/share/perl5/PVE/Storage/Plugin.pm line 1323.
Nov 24 01:37:10 centrix pvestatd[2102]: mkdir /mnt/pve/unraid/template: No space left on device at /usr/share/perl5/PVE/Storage/Plugin.pm line 1323.
Nov 24 01:37:20 centrix pvestatd[2102]: mkdir /mnt/pve/unraid/template: No space left on device at /usr/share/perl5/PVE/Storage/Plugin.pm line 1323.
```

Let's set a flag attribute to prevent deletion of these folders so they are always on NVME and no seek to slow-storage is needed.

```
root@nas:/cache# mkdir -p template/iso
root@nas:/cache# mkdir -p template/cache
root@nas:/cache# chattr +i -RV template
root@nas:/cache# chattr +i -RV template/iso
root@nas:/cache# chattr +i -RV template/cache
```