# Snapraid-btrfs-runner

We use this program to automate daily parity sync and scrub operations. This script is a wrapper to `snapraid-btrfs` in that it offers all of the same core options `diff`, `sync`, `scrub`.

## /opt/snapraid-btrfs-runner/snapraid-btrfs-runner.conf

The configuration file contents.

```
[snapraid-btrfs]
; path to the snapraid-btrfs executable (e.g. /usr/bin/snapraid-btrfs)
executable = /usr/local/bin/snapraid-btrfs
; optional: specify snapper-configs and/or snapper-configs-file as specified in snapraid-btrfs
; only one instance of each can be specified in this config
;snapper-configs =  /etc/snapper/configs
;snapper-configs = /etc/snapper/configs
;snapper-configs-file =
; specify whether snapraid-btrfs should run the pool command after the sync, and optionally specify pool-dir
pool = false
pool-dir =
; specify whether snapraid-btrfs-runner should automatically clean up all but the last snapraid-btrfs sync snapshot after a successful sync
cleanup = true

[snapper]
; path to snapper executable (e.g. /usr/bin/snapper)
executable = /usr/bin/snapper

[snapraid]
; path to the snapraid executable (e.g. /usr/bin/snapraid)
;executable = /usr/bin/snapraid
executable = /usr/local/bin/snapraid
; path to the snapraid config to be used
config = /etc/snapraid.conf
;config = /etc/snapraid.conf
; abort operation if there are more deletes than this, set to -1 to disable
deletethreshold = 300
; if you want touch to be ran each time
touch = false

[logging]
; logfile to write to, leave empty to disable
file = /var/log/snapraid.log
; maximum logfile size in KiB, leave empty for infinite
maxsize = 5000

[email]
; when to send an email, comma-separated list of [success, error]
sendon = success,error
; set to false to get full programm output via email
short = true
subject = [SnapRAID] Status Report:
from = changeme@gmail.com
to = changeme@gmail.com
; maximum email size in KiB
maxsize = 500

[smtp]
host =
; leave empty for default port
port =
; set to "true" to activate
ssl = false
tls = false
user =
password =

[scrub]
; set to true to run scrub after sync
enabled = false
; plan can be 0-100 percent, new, bad, or full
plan = 12
; only used for percent scrub plan
older-than = 10

```

## Scheduling via systemd timers

### /etc/systemd/system/snapraid-btrfs-runner.service

Contents

```
[Unit]
Description=Run snapraid-btrfs-runner every night

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/snapraid-btrfs-runner/snapraid-btrfs-runner.py -c /opt/snapraid-btrfs-runner/snapraid-btrfs-runner.conf

```

### /etc/systemd/system/snapraid-btrfs-runner.timer

Contents

```
[Unit]
Description=Run snapraid-btrfs-runner every night

[Timer]
OnCalendar=*-*-* 03:00:00
RandomizedDelaySec=30m

[Install]
WantedBy=timers.target

```

### Enable systemd timer

```
systemctl enable snapraid-btrfs-runner.timer --now
```