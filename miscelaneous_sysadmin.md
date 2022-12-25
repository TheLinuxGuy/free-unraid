# Miscelaneous sysadmin notes
Scratchpad, tips related to system administrator tasks or configuration of certain services running on free-unraid OS.

## OpenWRT

### Calculating DHCP scope settings

```
ipcalc.sh network-ip mask-or-prefix start limit
```

https://forum.openwrt.org/t/dhcp-range-configuration/67452/7

## Ubuntu

### Newer ZFS repo
https://launchpad.net/~jonathonf/+archive/ubuntu/zfs
```
sudo add-apt-repository ppa:jonathonf/zfs
sudo apt update
```

## Plex Media Server

### Keeping plex-media-server package up-to-date

https://github.com/mrworf/plexupdate

## Proxmox

Disable subscription nag using this tool. https://tteck.github.io/Proxmox/

```
bash -c "$(wget -qLO - https://github.com/tteck/Proxmox/raw/main/misc/post-pve-install.sh)"
```

### Limit ZFS Memory usage to 3GB on NAS VM

Dynamic during runtime.
```
echo "$[3 * 1024*1024*1024]" >/sys/module/zfs/parameters/zfs_arc_max
```

Permanent, add/create `/etc/modprobe.d/zfs.conf`
```
options zfs zfs_arc_max=3221225472
```

## Samba

### Newer builds for ubuntu

https://launchpad.net/~linux-schools/+archive/ubuntu/samba-latest

## Docker
### Update all containers

```
docker run -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --run-once
```


### NTP

Ensure timesync. File: `/etc/systemd/timesyncd.conf`
```
[Time]
NTP=time.google.com time1.google.com time2.google.com time3.google.com
FallbackNTP=0.pool.ntp.org 1.pool.ntp.org 0.debian.pool.ntp.org
```

Restart `systemd-timesyncd.service` - done.

### Folder listings timestamp include year (ls)

Add to `.bashrc` file
```
export TIME_STYLE=long-iso
```

## Btrfs

### Change the partition label

If system is mounted (live change)
```
btrfs filesystem label <mountpoint> <newlabel>
```

If unmounted
```
btrfs filesystem label <device> <newlabel>
```

Make necessary updates in `/etc/fstab`

## NFS

Check if kernel supports which NFS versions
https://wiki.debian.org/NFSServerSetup

```
grep NFSD /boot/config-`uname -r`
```

check enabled versions
```
cat /proc/fs/nfsd/versions
```

Make sure to tweak these configuration files on the server to force NFS v4 always.

```
/etc/nfs.conf
/etc/default/nfs-common
/etc/default/nfs-kernel-server
```

### The easy way to enable NFS v4.2

```
# nfsconf --set nfsd vers4.2 y
root@nas:/home/gfm# nfsconf --get nfsd vers4.2
y
# cat /etc/nfs.conf
```

Important section
```
 vers2=n
 vers3=n
 vers4=n
 vers4.0=n
 vers4.1=y
 vers4.2=y
```

If `rpc-statd.service` complains after disabling V2 V3 NFS. Mask it.

```
systemctl mask rpc-statd.service
```

### Check dependencies and its service status

```
systemctl list-dependencies nfs-kernel-server
```

### Mounting NFSv4 on client 

When faced with error `mount.nfs4: mounting 192.168.1.54:/mnt/cached failed, reason given by server: No such file or directory`

The hint was `fsid=0` from https://askubuntu.com/questions/35077/cannot-mount-nfs4-share-no-such-file-or-directory and the path we use to mount.

In NFSv3 the old mount command was (when share had fsid=0 in its exports config):
```
mount -t nfs 192.168.1.54:/mnt/cached /mnt/derp/ 
```

NFSv4 format, fsid has special meaning to the path.

```
mount.nfs4 -o vers=4.2 192.168.1.54:/ /mnt/derp/
```

More on this: https://unix.stackexchange.com/questions/427597/implications-of-using-nfsv4-fsid-0-and-exporting-the-nfs-root-to-entire-lan-or

**You can avoid this altogether by simply using fsid=1 or anything other than zero.**