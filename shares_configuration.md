# Samba and NFS shares

Notes regarding setting up NFS and Samba shares. Since I mostly use cockpit-project for this; this page will be mostly notes, tricks or tips.

### Apple Time Machine SMB settings

Add these additional settings to OSX defaults.
```
create mask = 0600
directory mask = 0700
spotlight = yes
fruit:aapl = yes
fruit:time machine = yes
```

## Permissions on new share

After creating a user; creating a new ZFS filesystem in the cache drive. We need to grant permissions.

```
chown username:shares /cache/test/
```

The group `shares` for multi-user. SMB should now be writable. 

## NFS

Special settings to force user and group mapping to specific linux UIDs (the NAS user/group of your choice). In our case "proxmox" user (1001) and "shares" group (1002) should be mapped to all NFS requests of /mnt/cached

**NOTE** NFSv4-only and fsid=0 will give you headaches. Always use fsid >0 to avoid NFS namespaces.

```
rw,sync,no_subtree_check,fsid=1,async,all_squash,anonuid=1001,anongid=1002
```

### Temporary allow and map root to allow rsync from old server

Without this no_root_squash flag rsync copy will fail as the chgrp command will error out.

```
rw,sync,no_subtree_check,fsid=1,async,no_root_squash
```