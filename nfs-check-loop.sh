#!/bin/bash
# Basic script to run on an endless loop on a NFS client
# idea is to catch failure in rpcinfo and log timestamp.

NFS_HOST_IP=192.168.1.54

counter=1
while :
do
    echo "Run " $counter + $(date)
    /usr/sbin/rpcinfo -T tcp $NFS_HOST_IP nfs 4;
    if [ $? -eq 1 ]
    then
        echo "NFS server unresponsive."
        break
    fi
    ((counter++))
    sleep 1
done
echo "NFS monitor script finished. " 