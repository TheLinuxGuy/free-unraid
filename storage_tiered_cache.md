# Tiered Storage Solution

I want to mimize the benefits of NVME speeds (super fast) with the large storage capacity benefits of spinning hard drives on my media. Ideal situation is that any new writes of data end up in the NVME drive (/cache), later `stale` or `unused` gets purged to /mnt/slow-storage disks.

Achiving this hybrid setup will require some automatic script to do the file housekeeping. The author of mergerfs has some basic scripts: https://github.com/trapexit/mergerfs#time-based-expiring - while those are great. If you are looking for advanced tiered storage management you basically will need to write your own scripts with advanced logic in them.

### Use cases that an ideal script should consider

1. NVME cache almost full (/cache). Avoid `no space left on device` errors; script would need to purge data and free space if this condition happens. If we want to keep using the nvme for fast cache.

*Note: mergerfs has a minfreespace setting (default 4GB) that will write to next disk in the mount point settings. In mergerfs.md I used fall-back to `/mnt/slow-storage` when nvme gets full; so if you wanted to keep things simple you don't really need a script.*

2. Special rules per mount (e.g: "movies" vs. "documents").

We probably want to purge large files in "movies" cache, rather than moving 'documents' out of the NVME when in a space crunch. Documents probably deserve to be purged out of cache disk after X days unmodified (since I setup ZFS raid1 protection in `/cache` - our slow disks have snapraid on a scheduled job, meaning there's a gap in time that dataloss is possible in the `/mnt/slow-storage` mount)

Possible idea/workaround: use **ZFS datasets with quota** defined to limit how much writes can go into /cache/movies (% of total available disk). This in theory should force mergerfs to fallback writes to `/mnt/slow-storage`. (to be tested)

If no ZFS dataset-quota is pursued,  https://duc.zevv.nl could be used to index total disk space utilization on /cache - then use scripting rules to check when /cache/movies folder exceeds X GB then execute a purge. 

#### rsync notes
https://linux.die.net/man/1/rsync

=== mergerfs owner recommends these options ===
`axqHAXWESR`

```
a = archive mode
x = don't cross filesystem boundaries
q = quiet
H = preserve hard links
A = preserve ACLs (implies -p)
X = preserve extended attributes
W = copy files whole (w/o delta-xfer algorithm)
E = preserve executability
S = handle sparse files efficiently
R = Use relative paths. This means that the full path names specified on the command line are sent to the server rather than just the last parts of the filenames
```

=== unraid === 
`dIWRpEAXogt`

```
d = transfer directories without recursing
I = don't skip files that match size and time
W = With this option rsync's delta-transfer algorithm is not used and the whole file is sent as-is instead
R = Use relative paths. This means that the full path names specified on the command line are sent to the server rather than just the last parts of the filenames
p = preserve permissions
E = preserve executability
A = preserve ACLs (implies -p)
X = preserve extended attributes
o = preserve owner (super-user only)
g = preserve group
t = preserve modification times
```