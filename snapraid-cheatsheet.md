# SnapRaid Cheatsheet & Debugging

Notes related to snapraid.

https://www.snapraid.it/manual

## List of devices to log

`snapraid -l devices.log devices`

## List all the files at the time of last `sync`

`snapraid list`

output snippet. Our snapraid has data backup for 12TB of 89718 files.

```
   89718 files, for 12353 GB
       0 links
```

## Delete snapraid data & backup files to start from scratch

From your snapraid.conf - delete all parity and content files.

```
# du -sh /var/snapraid.content /mnt/snapraid-content/disk*/snapraid.content /mnt/parity1/snapraid.parity
737M    /var/snapraid.content
737M    /mnt/snapraid-content/disk1/snapraid.content
737M    /mnt/snapraid-content/disk2/snapraid.content
13T     /mnt/parity1/snapraid.parity
```