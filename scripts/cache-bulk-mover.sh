#!/bin/bash
# github.com/TheLinuxGuy Tiered Storage mover (/cache -> /mnt/slow-storage)

# This is my customized 'mover' script used for moving files from the cache ZFS pool to the
# main mergerfs pool (/mnt/slow-storage).  It is typically invoked via cron and this is 
# inspired unraid-mover script.

# After checking if it's valid for this script to run, we check each of the top-level
# directories (shares) on the cache disk.  Right now this script moves everything out of
# /cache ZFS pool and into the slower disks. 

# The script is set up so that hidden directories (i.e., directory names beginning with a '.'
# character) at the topmost level of the cache drive are also not moved.  This behavior can be
# turned off by uncommenting the following line:
# shopt -s dotglob

# Files at the top level of the cache disk are never moved to the array.

# The 'find' command generates a list of all files and directories on the cache disk.
# For each file, if the file is not "in use" by any process (as detected by 'fuser' command),
# then the file is copied to the array, and upon success, deleted from the cache disk.
# For each directory, if the directory is empty, then the directory is created on the array,
# and upon success, deleted from the cache disk.

# For each file or directory, we use 'rsync' to copy the file or directory to the array.
# We specify the proper options to rsync so that files and directories get copied to the
# array while preserving ownership, permissions, access times, and extended attributes (this
# is why we use rsync: a simple mv command will not preserve all metadata properly).

# If an error occurs in copying (or overwriting) a file from the cache disk to the array, the
# file on the array, if present, is deleted and the operation continues on to the next file.

# Only run script if cache disk enabled and in use
if [ ! -d /cache -o ! -d /mnt/cached ]; then
  exit 0
fi

# If a previous invokation of this script is already running, exit
if [ -f /var/run/mover.pid ]; then
  if ps h `cat /var/run/mover.pid` | grep mover ; then
      echo "mover already running"
      exit 0
  fi
fi
echo $$ >/var/run/mover.pid
echo "mover started"

cd /cache
shopt -s nullglob
for Share in */ ; do
    echo "moving \"${Share%/}\""
    find "./$Share" -depth \( \( -type f ! -exec fuser -s {} \; \) -o \( -type d -empty \) \) -print \
        \( -exec rsync -i -dIWRpEAXogt --numeric-ids --inplace {} /mnt/slow-storage/ \; -delete \) -o \( -type f -exec rm -f /mnt/slow-storage/{} \; \)
done

rm /var/run/mover.pid
echo "mover finished"
