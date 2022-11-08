# Miscelaneous sysadmin notes
Scratchpad, tips related to system administrator tasks or configuration of certain services running on free-unraid OS.

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