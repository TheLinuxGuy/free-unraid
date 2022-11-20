# Monitoring / CheckMK

### Plugins

https://exchange.checkmk.com/p/btrfs-health 

## hd-idle (custom solutioning)

### Identify log lines

```
grep -o --perl-regexp 'hd-idle\[\d+]: \K.*' /var/log/syslog
```