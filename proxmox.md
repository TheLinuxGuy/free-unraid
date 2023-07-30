# Promox Virtual Environment

This is a list of notes related to Proxmox. We use Proxmox as the top-layer of my setup (meaning NAS is a VM with PCIe passthrough for disks HBA controllers).

## CPU Pinning (to be researched)

https://www.youtube.com/watch?v=-c_451HV6fE < useful info>

```
#lscpu -e
# lstopo
```

## Disable subscription nag / initial setup helper script

Disable subscription nag using this tool. https://tteck.github.io/Proxmox/

```
bash -c "$(wget -qLO - https://github.com/tteck/Proxmox/raw/main/misc/post-pve-install.sh)"
```

## PCI passthrough SATA onboard controller AHCI 

```
lspci -knn
```

You will need to edit `udev` and a few other things.

https://gist.github.com/kiler129/4f765e8fdc41e1709f1f34f7f8f41706 

-- probably not needed. Just add softdep to the /etc/modprobe.d/asmedia-sata.conf

```
options vfio-pci ids=8086:43d3
softdep ahci pre: vfio-pci
```

## Building corefreq-cli fails

Error
```
make[1]: *** /lib/modules/6.2.11-2-pve/build: No such file or directory.  Stop.
make: *** [Makefile:86: all] Error 2
```
You need to install headers. 
```
apt-get install linux-headers-`uname -r`
```

## Intel GPU passthru

Enable kernel `kvmgt` module in /etc/modules 

also add `i915.enable_gvt=1` to /etc/kernel/cmdline

Run
`update-initramfs -u -k all` and refresh

## VM not discovering hard disks (plug and unplug)

Try changing the `/etc/kernel/cmdline` to set `iommu=soft`

```
root=ZFS=rpool/ROOT/pve-1 boot=zfs intel_iommu=on iommu=soft pcie_aspm=force pcie_aspm.policy=powersupersave vfio-pci.ids=144d:a802,8086:7ae2 initcall_blacklist=sysfb_init
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