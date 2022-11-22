# Plex Media Server 

Notes about Plex and hardware transcoding. My setup is LXC container on Proxmox; with NFS mount to my unraid.

## Intel GPU monitoring (hw transcoding)
![Alt text](img\intel-gpu-top.png?raw=true "intel_gpu_top")

Use this tool. Requires `apt-get install intel-gpu-tools`
```
intel_gpu_top
```

## LXC container settings

```
lxc.cgroup2.devices.allow: c 226:0 rwm
lxc.cgroup2.devices.allow: c 226:128 rwm
lxc.cgroup2.devices.allow: c 29:0 rwm
lxc.mount.entry: /dev/fb0 dev/fb0 none bind,optional,create=file
lxc.mount.entry: /dev/dri dev/dri none bind,optional,create=dir
lxc.mount.entry: /dev/dri/renderD128 dev/renderD128 none bind,optional,create=file
```

Install packages inside the LXC container. (non-free apt repo req)

```
apt install intel-media-va-driver-non-free
```

## Setup Proxmox host for GPU passthru to LXC

- proxmox kernel must be 5.19 or later.

Based on: https://wiki.archlinux.org/title/intel_graphics

I have Rocket Lake, so `3`

```
echo “options i915 enable_guc=3” >> /etc/modprobe.d/i915.conf
```

```
nano /etc/kernel/cmdline
```
add `initcall_blacklist=sysfb_init`

refresh boot environment. `proxmox-boot-tool refresh`