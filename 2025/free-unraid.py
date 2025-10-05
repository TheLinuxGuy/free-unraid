#!/usr/bin/env python3
"""
Author: Giovanni Mazzeo (github.com/thelinuxguy)

free-unraid.py - Manage physical hard drives and logical storage configurations on Linux systems.
Integrates with bcache and the nonraid project.

DISK IDENTIFICATION STRATEGY:
This script uses a robust unique identifier system to track disks throughout their lifecycle,
even when device paths change due to kernel renaming (e.g., /dev/sde -> /dev/sdc).

1. NORMAL CASE (disk has unique serial):
   - unique_id = serial number from smartctl
   - Example: "WD-WCATR1234567"

2. EDGE CASE: Disk has no serial number:
   - unique_id = "NO_SERIAL_<device_name>"
   - Example: "NO_SERIAL_sda"
   - WARNING: Tracking may be lost if device is disconnected/reconnected
   - User is warned during configuration

3. EDGE CASE: Multiple disks with duplicate serial (rare but possible):
   - unique_id = "<serial>_<device_name>"
   - Example: "ABC123_sda" and "ABC123_sdb"
   - Differentiates by appending device name
   - User is warned about duplicate serial during discovery

All configuration tracking uses unique_id as the key, ensuring consistent disk identification
regardless of device path changes during cleanup, bcache creation, or system reboots.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Config:
    """Global configuration and state"""
    verbose = False
    auto_yes = False


def log_verbose(message: str) -> None:
    """Print message only if verbose mode is enabled"""
    if Config.verbose:
        print(f"{Colors.OKCYAN}[VERBOSE]{Colors.ENDC} {message}")


def log_info(message: str) -> None:
    """Print informational message"""
    print(f"{Colors.OKGREEN}[INFO]{Colors.ENDC} {message}")


def log_warning(message: str) -> None:
    """Print warning message"""
    print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {message}")


def log_error(message: str) -> None:
    """Print error message"""
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {message}", file=sys.stderr)


def run_command(cmd: List[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    """
    Execute a system command and return the result.
    
    Args:
        cmd: Command and arguments as a list
        check: Raise exception on non-zero exit code
        capture_output: Capture stdout and stderr
    
    Returns:
        CompletedProcess object with returncode, stdout, stderr
    """
    log_verbose(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=check
        )
        log_verbose(f"Command exit code: {result.returncode}")
        if capture_output and result.stdout:
            log_verbose(f"Command stdout: {result.stdout.strip()}")
        if capture_output and result.stderr:
            log_verbose(f"Command stderr: {result.stderr.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {' '.join(cmd)}")
        log_error(f"Exit code: {e.returncode}")
        if e.stdout:
            log_error(f"Stdout: {e.stdout}")
        if e.stderr:
            log_error(f"Stderr: {e.stderr}")
        raise
    except FileNotFoundError:
        log_error(f"Command not found: {cmd[0]}")
        raise


def dependency_check() -> bool:
    """
    Validate that all required system tools are available.
    
    Returns:
        True if all dependencies are met, False otherwise
    """
    dependencies = {
        'parted': 'partition management',
        'partprobe': 'partition table refresh',
        'sgdisk': 'GPT partitioning',
        'make-bcache': 'bcache creation',
        'blockdev': 'device information',
        'smartctl': 'SMART status',
        'wipefs': 'filesystem signature removal',
        'pvs': 'LVM physical volume scan',
        'vgremove': 'LVM volume group removal',
        'pvremove': 'LVM physical volume removal',
        'dmsetup': 'device-mapper management',
        'udevadm': 'device event management',
        'dd': 'low-level disk operations'
    }
    
    log_info("Checking dependencies...")
    missing = []
    
    for cmd, description in dependencies.items():
        try:
            result = run_command(['which', cmd], check=False)
            if result.returncode == 0:
                log_verbose(f"✓ {cmd} found ({description})")
            else:
                log_error(f"✗ {cmd} not found ({description})")
                missing.append(cmd)
        except Exception:
            log_error(f"✗ {cmd} not found ({description})")
            missing.append(cmd)
    
    if missing:
        log_error(f"Missing dependencies: {', '.join(missing)}")
        return False
    
    log_info("All dependencies satisfied")
    return True


def get_disk_list() -> List[str]:
    """
    Get list of physical disk devices.
    
    Returns:
        List of device paths (e.g., ['/dev/sda', '/dev/sdb'])
    """
    disks = []
    
    # Use lsblk to find disk devices
    try:
        result = run_command(['lsblk', '-ndo', 'NAME,TYPE'])
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == 'disk':
                device = f"/dev/{parts[0]}"
                disks.append(device)
    except Exception as e:
        log_error(f"Failed to get disk list: {e}")
        return []
    
    log_verbose(f"Found {len(disks)} disk(s): {', '.join(disks)}")
    return disks


def get_disk_size(device: str) -> Optional[str]:
    """Get human-readable disk size"""
    try:
        result = run_command(['blockdev', '--getsize64', device])
        size_bytes = int(result.stdout.strip())
        
        # Convert to human-readable format
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}PB"
    except Exception:
        return None


def get_disk_model(device: str) -> Optional[str]:
    """Get disk model from smartctl"""
    try:
        result = run_command(['smartctl', '-i', device], check=False)
        for line in result.stdout.split('\n'):
            if 'Device Model:' in line or 'Product:' in line or 'Model Family:' in line:
                return line.split(':', 1)[1].strip()
        return None
    except Exception:
        return None


def get_disk_serial(device: str) -> Optional[str]:
    """Get disk serial number from smartctl"""
    try:
        result = run_command(['smartctl', '-i', device], check=False)
        for line in result.stdout.split('\n'):
            if 'Serial Number:' in line or 'Serial number:' in line:
                return line.split(':', 1)[1].strip()
        return None
    except Exception:
        return None


def get_smart_status(device: str) -> Tuple[str, int]:
    """
    Get SMART health status and power-on hours.
    
    Returns:
        Tuple of (status_string, hours)
    """
    status = "UNKNOWN"
    hours = 0
    
    try:
        result = run_command(['smartctl', '-H', '-A', device], check=False)
        
        # Check health status
        for line in result.stdout.split('\n'):
            if 'SMART overall-health' in line or 'SMART Health Status:' in line:
                if 'PASSED' in line or 'OK' in line:
                    status = "HEALTHY"
                else:
                    status = "FAILING"
        
        # Get power-on hours - use RAW_VALUE (last column)
        for line in result.stdout.split('\n'):
            if 'Power_On_Hours' in line or 'Power On Hours' in line:
                parts = line.split()
                # The RAW_VALUE is typically the last field in smartctl -A output
                # Format: ID ATTRIBUTE_NAME FLAG VALUE WORST THRESH TYPE UPDATED WHEN_FAILED RAW_VALUE
                if len(parts) >= 10:
                    # Last field is the raw value
                    try:
                        hours = int(parts[-1])
                    except ValueError:
                        # Sometimes raw value might have additional info, try to extract first number
                        raw_value = parts[-1].split()[0]
                        hours = int(raw_value)
    except Exception:
        pass
    
    return status, hours


def get_ata_slot(device: str) -> Optional[str]:
    """Get ATA/SATA slot mapping or SCSI address for the device"""
    try:
        # Get the device name without /dev/
        dev_name = device.replace('/dev/', '')
        
        # Try to find slot info in sysfs
        sys_block_path = f"/sys/block/{dev_name}"
        if os.path.exists(sys_block_path):
            device_link = os.readlink(sys_block_path)
            
            # Look for SCSI address pattern (e.g., 5:0:0:0 for SATA)
            match = re.search(r'(\d+:\d+:\d+:\d+)/block/', device_link)
            if match:
                return match.group(1)
            
            # Look for NVMe PCI address pattern (e.g., 0000:08:00.0)
            if 'nvme' in dev_name:
                match = re.search(r'(0000:[0-9a-f]{2}:[0-9a-f]{2}\.\d+)/nvme', device_link)
                if match:
                    # Return just the bus:device.function part for readability
                    pci_addr = match.group(1)
                    # Strip the leading 0000: domain
                    return pci_addr.replace('0000:', '')
            
            # Fallback to ata pattern (e.g., ata6)
            match = re.search(r'ata\d+', device_link)
            if match:
                return match.group(0)
        
        return None
    except Exception:
        return None


def get_partitions(device: str) -> List[Dict[str, str]]:
    """
    Get list of partitions on a device.
    
    Returns:
        List of dicts with partition information
    """
    partitions = []
    
    try:
        result = run_command(['lsblk', '-nlo', 'NAME,SIZE,FSTYPE,MOUNTPOINT', device])
        lines = result.stdout.strip().split('\n')
        
        for line in lines[1:]:  # Skip first line (the device itself)
            if not line.strip():
                continue
            parts = line.split(None, 3)
            if len(parts) >= 2:
                part_info = {
                    'name': f"/dev/{parts[0].strip()}",
                    'size': parts[1] if len(parts) > 1 else '',
                    'fstype': parts[2] if len(parts) > 2 else '',
                    'mountpoint': parts[3] if len(parts) > 3 else ''
                }
                partitions.append(part_info)
    except Exception as e:
        log_verbose(f"Could not get partitions for {device}: {e}")
    
    return partitions


def get_bcache_info(device: str) -> Optional[Dict[str, str]]:
    """
    Get bcache information for a device.
    
    Returns:
        Dict with bcache device, by-id path, UUID, and cache set UUID, or None
    """
    try:
        # Check if device is a bcache backing device
        dev_name = device.replace('/dev/', '')
        bcache_path = f"/sys/block/{dev_name}/bcache"
        
        if not os.path.exists(bcache_path):
            # Check if this is a bcache device itself
            if dev_name.startswith('bcache'):
                serial = get_disk_serial(device)
                model = get_disk_model(device)
                
                if serial and model:
                    # Try to construct by-id path
                    by_id_path = f"/dev/disk/by-id/bcache-{model.replace(' ', '_')}-{serial}"
                    if os.path.exists(by_id_path):
                        return {
                            'device': device,
                            'by_id': by_id_path,
                            'uuid': None,
                            'cache_set_uuid': None
                        }
                
                return {
                    'device': device,
                    'by_id': None,
                    'uuid': None,
                    'cache_set_uuid': None
                }
            return None
        
        # Find the bcache device - 'dev' is a symlink to the bcache device
        bcache_dev_symlink = os.path.join(bcache_path, 'dev')
        if os.path.islink(bcache_dev_symlink):
            # Read the symlink target
            target = os.readlink(bcache_dev_symlink)
            # Extract bcache device name from path like ../../../../../virtual/block/bcache0
            bcache_dev = os.path.basename(target)
            
            # Get bcache UUIDs
            backing_dev_uuid = None
            cache_set_uuid = None
            
            try:
                uuid_path = os.path.join(bcache_path, 'backing_dev_uuid')
                if os.path.exists(uuid_path):
                    with open(uuid_path, 'r') as f:
                        backing_dev_uuid = f.read().strip()
            except Exception:
                pass
            
            try:
                cache_uuid_path = os.path.join(bcache_path, 'cache_set')
                if os.path.islink(cache_uuid_path):
                    # Extract UUID from symlink target
                    cache_target = os.readlink(cache_uuid_path)
                    cache_set_uuid = os.path.basename(cache_target)
            except Exception:
                pass
            
            # Find by-id symlink
            by_id = None
            by_id_dir = Path('/dev/disk/by-id')
            if by_id_dir.exists():
                for symlink in by_id_dir.iterdir():
                    if symlink.name.startswith('bcache-') and not symlink.name.endswith('-part1'):
                        target = symlink.resolve()
                        if target.name == bcache_dev:
                            by_id = str(symlink)
                            break
            
            return {
                'device': f"/dev/{bcache_dev}",
                'by_id': by_id,
                'uuid': backing_dev_uuid,
                'cache_set_uuid': cache_set_uuid
            }
    except Exception as e:
        log_verbose(f"Could not get bcache info for {device}: {e}")
    
    return None


def get_nonraid_config(device: str) -> Optional[Dict]:
    """
    Get nonraid configuration for a device by reading /proc/nmdcmd.
    
    Returns:
        Dict with nonraid configuration or None
    """
    try:
        if not os.path.exists('/proc/nmdcmd'):
            return None
        
        with open('/proc/nmdcmd', 'r') as f:
            content = f.read()
        
        # Parse nmdcmd output to find this device
        # This is a placeholder - actual implementation depends on nmdcmd format
        # Example format: "1 /dev/bcache0p1 0 27344764815 0 bcache-WDC_WD140EDFZ-11A0VA0-QBJ2NRVT"
        
        for line in content.split('\n'):
            if device in line:
                parts = line.split()
                if len(parts) >= 6:
                    return {
                        'slot': int(parts[0]),
                        'part_path': parts[1],
                        'part_size': int(parts[3]),
                        'type': 'PARITY' if parts[0] == '0' else 'DATA',
                        'import_cmd': f'echo "import {line.strip()}" > /proc/nmdcmd'
                    }
    except Exception as e:
        log_verbose(f"Could not get nonraid config for {device}: {e}")
    
    return None


def discover_system() -> Dict:
    """
    Scan system and build comprehensive disk information dictionary.
    
    Returns:
        Nested dictionary with all disk information
    """
    log_info("Discovering system storage configuration...")
    
    system = {}
    disks = get_disk_list()
    serial_to_disks = {}  # Track duplicate serials
    
    for disk in disks:
        log_verbose(f"Scanning {disk}...")
        
        disk_serial = get_disk_serial(disk)
        
        # Track duplicate serials
        if disk_serial:
            if disk_serial in serial_to_disks:
                serial_to_disks[disk_serial].append(disk)
            else:
                serial_to_disks[disk_serial] = [disk]
        
        disk_info = {
            'disk_path': disk,
            'raw_disk_size': get_disk_size(disk),
            'disk_model': get_disk_model(disk),
            'disk_serial': disk_serial,
            'disk_smart_status': None,
            'disk_hours': 0,
            'ata_slot': get_ata_slot(disk),
            'partitions': get_partitions(disk),
            'bcache': get_bcache_info(disk),
            'nonraid_config': get_nonraid_config(disk)
        }
        
        # Get SMART status
        status, hours = get_smart_status(disk)
        disk_info['disk_smart_status'] = status
        disk_info['disk_hours'] = hours
        
        system[disk] = disk_info
    
    # Check for duplicate or missing serials and create unique identifiers
    for disk, disk_info in system.items():
        serial = disk_info['disk_serial']
        
        if not serial:
            # No serial number - create unique ID from device path
            unique_id = f"NO_SERIAL_{disk.replace('/dev/', '')}"
            disk_info['unique_id'] = unique_id
            log_warning(f"Disk {disk} has no serial number, using fallback ID: {unique_id}")
        elif len(serial_to_disks.get(serial, [])) > 1:
            # Duplicate serial - append device name to make it unique
            unique_id = f"{serial}_{disk.replace('/dev/', '')}"
            disk_info['unique_id'] = unique_id
            log_warning(f"Disk {disk} has duplicate serial {serial}, using unique ID: {unique_id}")
        else:
            # Normal case - serial is unique
            disk_info['unique_id'] = serial
    
    # Warn about duplicate serials
    for serial, disk_list in serial_to_disks.items():
        if len(disk_list) > 1:
            log_warning(f"Duplicate serial number detected: {serial}")
            log_warning(f"  Affected disks: {', '.join(disk_list)}")
            log_warning(f"  Using device-specific unique IDs to differentiate")
    
    log_info(f"Discovery complete: {len(system)} disk(s) found")
    return system


def find_disk_by_serial(serial: str) -> Optional[str]:
    """
    Find a disk device path by its serial number.
    
    Args:
        serial: Disk serial number to search for
    
    Returns:
        Device path (e.g., '/dev/sda') or None if not found
    """
    if not serial:
        return None
    
    disks = get_disk_list()
    for disk in disks:
        disk_serial = get_disk_serial(disk)
        if disk_serial == serial:
            log_verbose(f"Found disk with serial {serial} at {disk}")
            return disk
    
    return None


def find_disk_by_unique_id(unique_id: str) -> Optional[str]:
    """
    Find a disk device path by its unique identifier.
    Handles both regular serials and fallback IDs for disks without serials or with duplicates.
    
    Args:
        unique_id: Unique identifier (serial, or fallback ID like "NO_SERIAL_sda" or "SERIAL123_sda")
    
    Returns:
        Device path (e.g., '/dev/sda') or None if not found
    """
    if not unique_id:
        return None
    
    # Check if this is a fallback ID format (contains underscore and device name)
    if unique_id.startswith('NO_SERIAL_'):
        # Extract device name from "NO_SERIAL_sda"
        dev_name = unique_id.replace('NO_SERIAL_', '')
        device_path = f"/dev/{dev_name}"
        if os.path.exists(device_path):
            log_verbose(f"Found disk with fallback ID {unique_id} at {device_path}")
            return device_path
        return None
    
    # Check for duplicate serial format "SERIAL_sda"
    if '_' in unique_id:
        # This might be a duplicate serial with device suffix
        # Try to extract the device name (last part after underscore)
        parts = unique_id.rsplit('_', 1)
        if len(parts) == 2:
            dev_name = parts[1]
            device_path = f"/dev/{dev_name}"
            if os.path.exists(device_path):
                # Verify the serial matches (first part before underscore)
                disk_serial = get_disk_serial(device_path)
                if disk_serial == parts[0]:
                    log_verbose(f"Found disk with duplicate serial ID {unique_id} at {device_path}")
                    return device_path
    
    # Standard case: search by serial number
    return find_disk_by_serial(unique_id)


def calculate_nmdcmd_size(device_path: str) -> Optional[int]:
    """
    Calculate partition size for nonraid import command.
    
    Steps:
    1. Verify block device exists
    2. Get sector count: blockdev --getsz
    3. Round down to nearest multiple of 8 sectors
    4. Convert to KB (sectors / 2)
    5. Return size in KB or error code
    
    Args:
        device_path: Path to the partition device
    
    Returns:
        Size in KB, or None on error
    """
    try:
        # Verify device exists
        if not os.path.exists(device_path):
            log_error(f"Device {device_path} does not exist")
            return None
        
        # Get sector count
        result = run_command(['blockdev', '--getsz', device_path])
        sector_count = int(result.stdout.strip())
        log_verbose(f"Sector count for {device_path}: {sector_count}")
        
        # Round down to nearest multiple of 8 sectors
        rounded_sectors = (sector_count // 8) * 8
        log_verbose(f"Rounded sectors: {rounded_sectors}")
        
        # Convert to KB (sectors / 2)
        size_kb = rounded_sectors // 2
        log_verbose(f"Size in KB: {size_kb}")
        
        return size_kb
    except Exception as e:
        log_error(f"Failed to calculate size for {device_path}: {e}")
        return None


def prompt_yes_no(question: str, default: bool = False) -> bool:
    """
    Prompt user for yes/no answer.
    
    Args:
        question: Question to ask
        default: Default answer if user just presses Enter
    
    Returns:
        True for yes, False for no
    """
    if Config.auto_yes:
        log_verbose(f"Auto-yes enabled, answering 'yes' to: {question}")
        return True
    
    suffix = " [Y/n]: " if default else " [y/N]: "
    
    while True:
        response = input(question + suffix).strip().lower()
        
        if not response:
            return default
        
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            print("Please answer 'y' or 'n'")


def prompt_quit_option(question: str) -> Optional[bool]:
    """
    Prompt user for yes/no/quit answer.
    
    Returns:
        True for yes, False for no, None for quit
    """
    while True:
        response = input(question + " [y/n/quit]: ").strip().lower()
        
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        elif response in ('q', 'quit'):
            return None
        else:
            print("Please answer 'y', 'n', or 'quit'")


def prompt_slot_number() -> Optional[int]:
    """
    Prompt user for data disk slot number (1-28).
    
    Returns:
        Slot number or None if invalid
    """
    while True:
        try:
            response = input("Select data disk slot (1-28): ").strip()
            slot = int(response)
            
            if 1 <= slot <= 28:
                return slot
            else:
                print("Slot must be between 1 and 28")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            return None


def cmd_show(args) -> int:
    """
    SHOW command: Display comprehensive system storage information.
    
    Returns:
        Exit code (0 for success)
    """
    # Run dependency check
    if not dependency_check():
        return 1
    
    # Discover system
    system = discover_system()
    
    # Display header
    print(f"\n{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}System Storage Configuration{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        hostname = subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
        print(f"Hostname: {hostname}")
    except Exception:
        print("Hostname: <unknown>")
    
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
    
    # Display each disk
    for disk_path, disk_info in system.items():
        print(f"{Colors.HEADER}{Colors.BOLD}Disk: {disk_path}{Colors.ENDC}")
        print(f"  Model: {disk_info['disk_model'] or 'Unknown'}")
        print(f"  Serial: {disk_info['disk_serial'] or 'Unknown'}")
        print(f"  Size: {disk_info['raw_disk_size'] or 'Unknown'}")
        print(f"  SMART Status: {disk_info['disk_smart_status']}")
        print(f"  Power-On Hours: {disk_info['disk_hours']}")
        
        # Show slot with appropriate label based on device type
        if 'nvme' in disk_path:
            print(f"  NVMe PCI Slot: {disk_info['ata_slot'] or 'Unknown'}")
        else:
            print(f"  ATA Slot: {disk_info['ata_slot'] or 'Unknown'}")
        
        # Partitions
        if disk_info['partitions']:
            print(f"\n  {Colors.OKBLUE}Partitions:{Colors.ENDC}")
            for part in disk_info['partitions']:
                mount = f" (mounted at {part['mountpoint']})" if part['mountpoint'] else ""
                fstype = f" [{part['fstype']}]" if part['fstype'] else ""
                print(f"    - {part['name']} ({part['size']}){fstype}{mount}")
        else:
            print(f"\n  Partitions: None")
        
        # Bcache
        if disk_info['bcache']:
            print(f"\n  {Colors.OKBLUE}Bcache:{Colors.ENDC}")
            print(f"    Device: {disk_info['bcache']['device']}")
            if disk_info['bcache']['by_id']:
                print(f"    By-ID: {disk_info['bcache']['by_id']}")
            if disk_info['bcache']['uuid']:
                print(f"    Backing Device UUID: {disk_info['bcache']['uuid']}")
            if disk_info['bcache']['cache_set_uuid']:
                print(f"    Cache Set UUID: {disk_info['bcache']['cache_set_uuid']}")
        else:
            print(f"\n  Bcache: Not configured")
        
        # Nonraid
        if disk_info['nonraid_config']:
            print(f"\n  {Colors.OKBLUE}Nonraid Configuration:{Colors.ENDC}")
            print(f"    Slot: {disk_info['nonraid_config']['slot']}")
            print(f"    Type: {disk_info['nonraid_config']['type']}")
            print(f"    Partition: {disk_info['nonraid_config']['part_path']}")
            print(f"    Size: {disk_info['nonraid_config']['part_size']} KB")
        else:
            print(f"\n  Nonraid: Not configured")
        
        print()
    
    return 0


def cmd_configure(args) -> int:
    """
    CONFIGURE command: Automated disk configuration workflow.
    
    Returns:
        Exit code (0 for success)
    """
    # Run dependency check
    if not dependency_check():
        return 1
    
    # Discover system
    system = discover_system()
    
    # Track pending configurations
    pending_configs = {}
    
    while True:
        # Show available disks with enumeration
        print(f"\n{Colors.BOLD}Available disks:{Colors.ENDC}")
        available_disks = []
        disk_index_map = {}  # Map index to disk path
        index = 1
        
        for disk_path, disk_info in system.items():
            # Check disk status by unique_id (handles serials, missing serials, and duplicates)
            unique_id = disk_info.get('unique_id')
            if unique_id and unique_id in pending_configs:
                status = "pending"
                status_color = Colors.OKCYAN
            elif disk_info['bcache'] or disk_info['nonraid_config']:
                status = "configured"
                status_color = Colors.WARNING
            else:
                status = "available"
                status_color = Colors.OKGREEN
            
            # All disks are selectable
            available_disks.append(disk_path)
            disk_index_map[index] = disk_path
            
            # Display with index number and color coding
            print(f"  [{index}] {disk_path} - {disk_info['disk_model']} ({disk_info['raw_disk_size']}) {status_color}[{status}]{Colors.ENDC}")
            index += 1
        
        if not available_disks:
            print("\nNo disks found.")
            break
        
        # Prompt for disk selection
        print()
        user_input = input("Enter disk number, name, or path (or 'done' to finish): ").strip()
        
        if user_input.lower() == 'done':
            break
        
        # Parse user input - accept number, /dev/sda, or sda
        disk_to_configure = None
        
        # Try to parse as index number
        try:
            disk_num = int(user_input)
            if disk_num in disk_index_map:
                disk_to_configure = disk_index_map[disk_num]
            else:
                log_error(f"Invalid disk number. Please enter a number between 1 and {len(disk_index_map)}")
                continue
        except ValueError:
            # Not a number, try as device path or name
            # Normalize input
            if user_input.startswith('/dev/'):
                disk_to_configure = user_input
            elif user_input:
                disk_to_configure = f"/dev/{user_input}"
            
            # Verify it's in the system
            if disk_to_configure not in system:
                log_error(f"Invalid disk selection: {user_input}")
                continue
        
        disk_info = system[disk_to_configure]
        
        # Store original device path and unique_id for device rename detection
        original_device_path = disk_to_configure
        device_serial = disk_info['disk_serial']
        unique_id = disk_info.get('unique_id')
        
        # Validate we have a unique identifier
        if not unique_id:
            log_error(f"Cannot configure disk {disk_to_configure}: no unique identifier available")
            log_error("This is a system error - please report this bug")
            continue
        
        # Warn if disk has no serial or duplicate serial
        if unique_id.startswith('NO_SERIAL_'):
            log_warning(f"This disk has no serial number. Using device path for tracking.")
            log_warning(f"If the device is disconnected/reconnected, tracking may be lost!")
        elif '_' in unique_id and not unique_id.startswith('NO_SERIAL_'):
            log_warning(f"This disk has a duplicate serial number: {device_serial}")
            log_warning(f"Using unique ID: {unique_id}")
        
        # Check if disk is already configured and warn user
        needs_cleanup = False
        if disk_info['bcache'] or disk_info['nonraid_config']:
            print(f"\n{Colors.WARNING}WARNING: {disk_to_configure} is already configured!{Colors.ENDC}")
            if disk_info['bcache']:
                print(f"  Current bcache device: {disk_info['bcache']['device']}")
            if disk_info['nonraid_config']:
                print(f"  Current nonraid slot: {disk_info['nonraid_config']['slot']} ({disk_info['nonraid_config']['type']})")
            print(f"{Colors.WARNING}Reconfiguring will DESTROY the existing configuration and ALL data!{Colors.ENDC}")
            if not prompt_yes_no("Are you sure you want to reconfigure this disk?", default=False):
                continue
            needs_cleanup = True
        
        # Consolidated warning and confirmation prompt
        print()
        print(f"Disk: {disk_info['disk_model']} ({disk_info['raw_disk_size']})")
        if device_serial:
            print(f"Serial number: {device_serial}")
        else:
            print(f"Serial number: NOT AVAILABLE")
        if unique_id != device_serial:
            print(f"Unique ID: {unique_id}")
        confirm_msg = "Continue with this disk? This will be unrecoverable"
        if not prompt_yes_no(confirm_msg, default=False):
            log_info("Skipping disk configuration")
            continue
        
        # Step 0: Cleanup if disk is already configured
        if needs_cleanup:
            log_info(f"Cleaning up existing configuration on {disk_to_configure}...")
            
            # If there's a bcache device, we need to clean up everything on top of it
            if disk_info['bcache']:
                bcache_dev = disk_info['bcache']['device']
                bcache_name = bcache_dev.replace('/dev/', '')
                
                # Step 0.1: Check for and remove LVM volumes on the bcache device
                log_info(f"Checking for LVM volumes on {bcache_dev}...")
                try:
                    # First, remove any device-mapper entries
                    result = run_command(['dmsetup', 'ls', '--target', 'linear'], check=False)
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if line and bcache_name in line:
                                dm_name = line.split()[0]
                                log_info(f"Removing device-mapper entry: {dm_name}")
                                run_command(['dmsetup', 'remove', dm_name], check=False)
                                import time
                                time.sleep(1)
                    
                    # Check if there are any LVM physical volumes
                    result = run_command(['pvs', '--noheadings', '-o', 'pv_name'], check=False)
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            pv_name = line.strip()
                            if bcache_name in pv_name or bcache_dev in pv_name:
                                log_info(f"Found LVM PV: {pv_name}")
                                
                                # Get volume group name
                                vg_result = run_command(['pvs', '--noheadings', '-o', 'vg_name', pv_name], check=False)
                                if vg_result.returncode == 0:
                                    vg_name = vg_result.stdout.strip()
                                    if vg_name:
                                        log_info(f"Removing volume group: {vg_name}")
                                        run_command(['vgremove', '-f', vg_name], check=False)
                                        import time
                                        time.sleep(1)
                                
                                # Remove physical volume
                                log_info(f"Removing physical volume: {pv_name}")
                                run_command(['pvremove', '-ff', pv_name], check=False)
                                import time
                                time.sleep(1)
                except Exception as e:
                    log_verbose(f"LVM cleanup issue (may be normal): {e}")
                
                # Step 0.2: Unmount any partitions
                log_info(f"Checking for mounted partitions on {bcache_dev}...")
                try:
                    result = run_command(['lsblk', '-nlo', 'NAME,MOUNTPOINT', bcache_dev], check=False)
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            parts = line.split(None, 1)
                            if len(parts) == 2 and parts[1]:
                                mountpoint = parts[1]
                                log_info(f"Unmounting {mountpoint}...")
                                run_command(['umount', '-f', mountpoint], check=False)
                except Exception as e:
                    log_verbose(f"Unmount issue (may be normal): {e}")
                
                # Step 0.3: Remove partitions from bcache device
                log_info(f"Removing partitions from {bcache_dev}...")
                try:
                    # Use wipefs on the bcache device itself
                    run_command(['wipefs', '-a', bcache_dev], check=False)
                    import time
                    time.sleep(1)
                except Exception as e:
                    log_verbose(f"Could not wipe bcache device partitions: {e}")
                
                # Step 0.4: Unregister the bcache device
                log_info(f"Unregistering bcache device {bcache_dev}...")
                try:
                    # Stop the bcache device
                    stop_path = f"/sys/block/{bcache_name}/bcache/stop"
                    if os.path.exists(stop_path):
                        with open(stop_path, 'w') as f:
                            f.write('1')
                        log_verbose(f"Stopped bcache device {bcache_dev}")
                        import time
                        time.sleep(2)
                except Exception as e:
                    log_verbose(f"Could not stop bcache device: {e}")
                
                # Try to detach from backing device
                try:
                    dev_name = disk_to_configure.replace('/dev/', '')
                    detach_path = f"/sys/block/{dev_name}/bcache/detach"
                    if os.path.exists(detach_path):
                        with open(detach_path, 'w') as f:
                            f.write('1')
                        log_verbose(f"Detached bcache from {disk_to_configure}")
                        import time
                        time.sleep(2)
                except Exception as e:
                    log_verbose(f"Could not detach bcache: {e}")
                
                # Unregister the backing device
                try:
                    dev_name = disk_to_configure.replace('/dev/', '')
                    unregister_path = f"/sys/block/{dev_name}/bcache/unregister"
                    if os.path.exists(unregister_path):
                        with open(unregister_path, 'w') as f:
                            f.write('1')
                        log_info(f"Unregistered bcache backing device")
                        import time
                        time.sleep(2)
                except Exception as e:
                    log_verbose(f"Could not unregister backing device: {e}")
            
            # Step 0.5: Wipe filesystem signatures from the raw disk
            log_info(f"Wiping filesystem signatures from {disk_to_configure}...")
            try:
                run_command(['wipefs', '-af', disk_to_configure])
                log_info("Filesystem signatures wiped")
            except Exception as e:
                log_error(f"Failed to wipe filesystem signatures: {e}")
                continue
            
            # Step 0.6: Zero out the superblock area
            log_info(f"Clearing bcache superblock from {disk_to_configure}...")
            try:
                # Zero out first 4MB and bcache superblock location
                run_command(['dd', 'if=/dev/zero', f'of={disk_to_configure}', 'bs=1M', 'count=4', 'conv=fsync'], check=False)
                import time
                time.sleep(1)
            except Exception as e:
                log_verbose(f"Could not zero superblock: {e}")
            
            # Step 0.7: Reload partition table
            log_info(f"Reloading partition table for {disk_to_configure}...")
            try:
                run_command(['blockdev', '--rereadpt', disk_to_configure], check=False)
                run_command(['partprobe', disk_to_configure], check=False)
                log_verbose("Partition table reloaded")
            except Exception as e:
                log_verbose(f"Could not reload partition table: {e}")
            
            # Step 0.8: Wait for udev to settle
            log_info("Waiting for device to become available...")
            try:
                run_command(['udevadm', 'settle', '-t', '10'], check=False)
            except Exception as e:
                log_verbose(f"udevadm settle failed: {e}")
            
            # Additional wait to ensure device is fully available
            import time
            time.sleep(3)
            
            # Verify device exists before proceeding
            if not os.path.exists(disk_to_configure):
                log_warning(f"Device {disk_to_configure} not found after cleanup!")
                log_info("The device may have been renamed by the kernel during cleanup.")
                log_info(f"Searching for disk by unique ID: {unique_id}")
                
                # Try to find the disk by unique ID
                new_path = find_disk_by_unique_id(unique_id)
                if new_path:
                    log_info(f"Found disk at new location: {new_path}")
                    log_info(f"Device was renamed from {disk_to_configure} to {new_path}")
                    disk_to_configure = new_path
                    # Update disk_info to reflect new path
                    system = discover_system()
                    disk_info = system[disk_to_configure]
                    # Verify unique_id still matches
                    if disk_info.get('unique_id') != unique_id:
                        log_error(f"Unique ID mismatch after cleanup! Expected {unique_id}, got {disk_info.get('unique_id')}")
                        log_error("This indicates a serious tracking issue. Aborting configuration for safety.")
                        continue
                else:
                    log_error(f"Could not find disk with unique ID {unique_id}")
                    if device_serial:
                        log_error(f"  (Serial: {device_serial})")
                    log_error("Please run 'show' command to see current device names.")
                    continue
            
            log_info("Cleanup complete")
        
        # Step 1: Bcache Setup
        log_info(f"Creating bcache backing device on {disk_to_configure}...")
        bcache_uuid = None
        cache_set_uuid = None
        try:
            result = run_command(['make-bcache', '-B', disk_to_configure])
            # Parse UUID from make-bcache output
            for line in result.stdout.split('\n'):
                if line.startswith('UUID:'):
                    bcache_uuid = line.split(':', 1)[1].strip()
                    log_verbose(f"Bcache UUID: {bcache_uuid}")
                elif line.startswith('Set UUID:'):
                    cache_set_uuid = line.split(':', 1)[1].strip()
                    log_verbose(f"Cache Set UUID: {cache_set_uuid}")
            log_info("Bcache created successfully")
        except Exception as e:
            log_error(f"Failed to create bcache: {e}")
            continue
        
        # Wait for udev to create bcache device
        log_info("Waiting for bcache device to appear...")
        try:
            run_command(['udevadm', 'settle', '-t', '10'], check=False)
        except Exception as e:
            log_verbose(f"udevadm settle failed: {e}")
        
        import time
        time.sleep(2)
        
        # Re-discover to get bcache info
        system = discover_system()
        
        # Check if device was renamed after bcache creation
        if disk_to_configure not in system:
            log_warning(f"Device {disk_to_configure} not found after bcache creation!")
            log_info("The device may have been renamed by the kernel.")
            log_info(f"Searching for disk by unique ID: {unique_id}")
            
            # Try to find the disk by unique ID
            new_path = find_disk_by_unique_id(unique_id)
            if new_path:
                log_info(f"Found disk at new location: {new_path}")
                log_info(f"Device was renamed from {disk_to_configure} to {new_path}")
                disk_to_configure = new_path
            else:
                log_error(f"Could not find disk with unique ID {unique_id}")
                if device_serial:
                    log_error(f"  (Serial: {device_serial})")
                log_error("Please run 'show' command to see current device names.")
                continue
        
        disk_info = system[disk_to_configure]
        
        if not disk_info['bcache']:
            log_error("Failed to detect bcache device after creation")
            log_error(f"The device {disk_to_configure} may have been renamed or bcache failed to attach")
            log_error("Please run 'show' command to check current configuration")
            continue
        
        bcache_device = disk_info['bcache']['device']
        
        # Verify the bcache device actually exists
        if not os.path.exists(bcache_device):
            log_error(f"Bcache device {bcache_device} does not exist!")
            log_error("This may indicate a kernel issue or udev problem")
            continue
        
        # Wait for bcache device to be fully ready (readable/writable)
        log_info(f"Verifying bcache device {bcache_device} is ready...")
        bcache_ready = False
        for attempt in range(10):
            try:
                # Try to read from the device to ensure it's accessible
                result = run_command(['blockdev', '--getsize64', bcache_device], check=False)
                if result.returncode == 0:
                    log_verbose(f"Bcache device is accessible (attempt {attempt + 1})")
                    bcache_ready = True
                    break
                else:
                    log_verbose(f"Bcache device not ready yet (attempt {attempt + 1})")
            except Exception as e:
                log_verbose(f"Error checking bcache device (attempt {attempt + 1}): {e}")
            
            import time
            time.sleep(1)
        
        if not bcache_ready:
            log_error(f"Bcache device {bcache_device} is not accessible after waiting!")
            log_error("The device may be experiencing I/O errors or initialization issues")
            continue
        
        log_info(f"Bcache device: {bcache_device}")
        if bcache_uuid:
            log_info(f"Bcache UUID: {bcache_uuid}")
        
        # Step 2: Partitioning
        log_info(f"Creating partition on {bcache_device}...")
        try:
            # Bcache devices sometimes have stale GPT headers, run sgdisk twice to ensure it works
            # First run clears the table
            run_command(['sgdisk', '-o', '-a', '8', '-n', '1:32K:0', bcache_device], check=False)
            
            # Force kernel to re-read partition table after first write
            run_command(['partprobe', bcache_device], check=False)
            run_command(['blockdev', '--rereadpt', bcache_device], check=False)
            run_command(['udevadm', 'settle', '-t', '5'], check=False)
            
            # Wait for device to stabilize after first write
            import time
            time.sleep(2)
            
            # Second run to ensure partition is actually created
            result = run_command(['sgdisk', '-o', '-a', '8', '-n', '1:32K:0', bcache_device], check=False)
            if result.returncode != 0:
                log_error(f"sgdisk failed with exit code {result.returncode}")
                log_error(f"Output: {result.stdout}")
                log_error(f"Error: {result.stderr}")
                
                # Check if this is an I/O error (read error 5, exit code 4)
                if result.returncode == 4 or 'Read error' in result.stderr or 'Read error' in result.stdout:
                    log_error("The bcache device is experiencing I/O errors!")
                    log_error("This may indicate the backing disk went offline or has hardware issues.")
                    log_error(f"Please check 'dmesg' for kernel messages about {disk_to_configure}")
                continue
            
            # Verify partition was created in the table
            verify_result = run_command(['sgdisk', '-p', bcache_device], check=False)
            if 'Number  Start' not in verify_result.stdout or verify_result.stdout.count('\n') < 10:
                log_error("Partition table verification failed - no partition entries found")
                log_error(f"Partition table output:\n{verify_result.stdout}")
                continue
            
            # Force kernel to re-read partition table one final time
            run_command(['partprobe', bcache_device], check=False)
            run_command(['blockdev', '--rereadpt', bcache_device], check=False)
            run_command(['udevadm', 'settle', '-t', '5'], check=False)
            log_info("Partition created successfully")
        except Exception as e:
            log_error(f"Failed to create partition: {e}")
            continue
        
        # Partition path
        partition_path = f"{bcache_device}p1"
        
        # Wait for partition to appear with extended timeout
        import time
        log_verbose(f"Waiting for partition {partition_path} to appear...")
        partition_appeared = False
        for i in range(20):  # Increased from 10 to 20 iterations
            if os.path.exists(partition_path):
                partition_appeared = True
                log_verbose(f"Partition appeared after {i * 0.5} seconds")
                break
            # Try to trigger udev
            if i == 5:
                log_verbose("Triggering udev event...")
                run_command(['udevadm', 'trigger', '--subsystem-match=block'], check=False)
                run_command(['udevadm', 'settle'], check=False)
            time.sleep(0.5)
        
        if not partition_appeared:
            log_error(f"Partition {partition_path} did not appear after waiting")
            # Try to list what partitions exist
            log_error("Attempting to diagnose...")
            try:
                result = run_command(['lsblk', '-o', 'NAME,TYPE', bcache_device], check=False)
                log_error(f"Current device state:\n{result.stdout}")
                result = run_command(['sgdisk', '-p', bcache_device], check=False)
                log_error(f"Partition table:\n{result.stdout}")
            except Exception:
                pass
            continue
        
        # Step 3: Size Calculation
        log_info(f"Calculating partition size for {partition_path}...")
        part_size = calculate_nmdcmd_size(partition_path)
        
        if part_size is None:
            log_error("Failed to calculate partition size")
            continue
        
        log_info(f"Partition size: {part_size} KB")
        
        # Step 4: Nonraid Configuration
        is_data = prompt_yes_no("\nWill this disk be used for DATA storage?", default=True)
        
        if is_data:
            slot = prompt_slot_number()
            if slot is None:
                log_warning("Configuration cancelled")
                continue
            disk_type = "DATA"
        else:
            is_primary = prompt_quit_option("Primary parity (slot 0)?")
            if is_primary is None:
                log_warning("Configuration cancelled")
                continue
            elif is_primary:
                slot = 0
                disk_type = "PARITY"
            else:
                slot = 29
                disk_type = "PARITY2"
        
        # Build import command
        by_id = disk_info['bcache']['by_id'] or bcache_device
        import_cmd = f'echo "import {slot} {partition_path} 0 {part_size} 0 {os.path.basename(by_id)}" > /proc/nmdcmd'
        
        # Store configuration with additional metadata
        # Use unique_id as key (handles serials, missing serials, and duplicates)
        pending_configs[unique_id] = {
            'slot': slot,
            'part_path': partition_path,
            'part_size': part_size,
            'type': disk_type,
            'import_cmd': import_cmd,
            'disk_model': disk_info['disk_model'],
            'disk_size': disk_info['raw_disk_size'],
            'disk_serial': device_serial,
            'unique_id': unique_id,
            'disk_path': disk_to_configure,
            'bcache_device': bcache_device,
            'bcache_uuid': bcache_uuid
        }
        
        # Display appropriate confirmation message
        if device_serial:
            log_info(f"Configuration prepared for {disk_info['disk_model']} (S/N: {device_serial}): Slot {slot}, Type {disk_type}")
        else:
            log_info(f"Configuration prepared for {disk_info['disk_model']} (ID: {unique_id}): Slot {slot}, Type {disk_type}")
        
        # Ask about additional disks
        if not prompt_yes_no("\nConfigure additional disks?", default=False):
            break
    
    # Step 5: Final Commit
    if not pending_configs:
        log_info("No configurations to commit")
        return 0
    
    print(f"\n{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}Pending Configurations Summary{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")
    for unique_id, config in pending_configs.items():
        type_color = Colors.OKGREEN if config['type'] == 'DATA' else Colors.WARNING
        print(f"\n{Colors.HEADER}{config['disk_path']}{Colors.ENDC} - {config['disk_model']} ({config['disk_size']})")
        if config['disk_serial']:
            print(f"  Serial: {config['disk_serial']}")
        else:
            print(f"  Serial: NOT AVAILABLE")
        if unique_id != config['disk_serial']:
            print(f"  Unique ID: {unique_id}")
        print(f"  Slot: {type_color}{config['slot']}{Colors.ENDC}")
        print(f"  Type: {type_color}{config['type']}{Colors.ENDC}")
        print(f"  Bcache Device: {config['bcache_device']}")
        if config.get('bcache_uuid'):
            print(f"  Bcache UUID: {config['bcache_uuid']}")
        print(f"  Partition: {config['part_path']}")
        print(f"  Size: {config['part_size']} KB ({config['part_size'] // 1024 // 1024} GB)")
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")
    
    if not prompt_yes_no("\nCommit configuration and import to nonraid?", default=False):
        log_warning("Configuration discarded")
        return 0
    
    # Execute import commands
    log_info("Committing configurations...")
    
    for unique_id, config in pending_configs.items():
        if config['disk_serial']:
            disk_identifier = f"{config['disk_model']} (S/N: {config['disk_serial']})"
        else:
            disk_identifier = f"{config['disk_model']} (ID: {unique_id})"
        
        log_info(f"Importing {disk_identifier} to slot {config['slot']}...")
        log_verbose(f"Command: {config['import_cmd']}")
        
        try:
            # Execute the import command using shell
            result = subprocess.run(
                config['import_cmd'],
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                log_info(f"✓ {config['disk_path']} imported successfully")
            else:
                log_error(f"✗ Failed to import {disk}")
                if result.stderr:
                    log_error(f"Error: {result.stderr}")
        except Exception as e:
            log_error(f"✗ Failed to import {disk}: {e}")
    
    log_info("Configuration complete")
    return 0


def cmd_reset(args) -> int:
    """
    RESET command: Reset disk configuration for specified disks.
    Usage: ./free-unraid.py reset /dev/sdb /dev/sde ...
    For each disk passed as argument:
      - Only operate if disk is discovered in system
      - Check partition/bcache state before wipe
      - Execute wipefs -af <disk>
      - Check partition/bcache state after wipe
      - Exit successfully if all disks are wiped and no longer visible
    Returns:
        Exit code (0 for success)
    """
    if not dependency_check():
        return 1

    # Discover system at start
    system = discover_system()

    # Get disks to reset from args
    disks_to_reset = [d for d in args if d.startswith('/dev/')]
    import time
    failed = []
    for disk in disks_to_reset:
        print(f"\n{Colors.BOLD}Resetting disk: {disk}{Colors.ENDC}")
        if disk not in system:
            log_error(f"Disk {disk} not discovered by system. Skipping.")
            failed.append(disk)
            continue
        disk_info = system[disk]
        print(f"  Model: {disk_info['disk_model'] or 'Unknown'}")
        print(f"  Serial: {disk_info['disk_serial'] or 'Unknown'}")
        print(f"  Size: {disk_info['raw_disk_size'] or 'Unknown'}")
        print(f"  Partitions: {len(disk_info['partitions'])}")
        if disk_info['bcache']:
            print(f"  Bcache: {disk_info['bcache']['device']}")
        else:
            print(f"  Bcache: Not configured")

        # --- Robust cleanup: Remove bcache, partitions, superblock ---
        # Remove bcache device if present
        if disk_info['bcache']:
            bcache_dev = disk_info['bcache']['device']
            bcache_name = bcache_dev.replace('/dev/', '')
            log_info(f"Cleaning up bcache device: {bcache_dev}")
            # Unregister bcache device
            try:
                stop_path = f"/sys/block/{bcache_name}/bcache/stop"
                if os.path.exists(stop_path):
                    with open(stop_path, 'w') as f:
                        f.write('1')
                    log_verbose(f"Stopped bcache device {bcache_dev}")
                    time.sleep(2)
            except Exception as e:
                log_verbose(f"Could not stop bcache device: {e}")
            try:
                unregister_path = f"/sys/block/{bcache_name}/bcache/unregister"
                if os.path.exists(unregister_path):
                    with open(unregister_path, 'w') as f:
                        f.write('1')
                    log_verbose(f"Unregistered bcache device {bcache_dev}")
                    time.sleep(2)
            except Exception as e:
                log_verbose(f"Could not unregister bcache device: {e}")
            # Detach bcache from backing device
            try:
                dev_name = disk.replace('/dev/', '')
                detach_path = f"/sys/block/{dev_name}/bcache/detach"
                if os.path.exists(detach_path):
                    with open(detach_path, 'w') as f:
                        f.write('1')
                    log_verbose(f"Detached bcache from {disk}")
                    time.sleep(2)
            except Exception as e:
                log_verbose(f"Could not detach bcache: {e}")

        # Unmount all partitions
        for part in disk_info['partitions']:
            if part['mountpoint']:
                try:
                    log_info(f"Unmounting {part['name']} from {part['mountpoint']}...")
                    run_command(['umount', '-f', part['mountpoint']], check=False)
                except Exception as e:
                    log_verbose(f"Unmount issue: {e}")

        # Wipe filesystem signatures
        try:
            log_info(f"Wiping filesystem signatures from {disk}...")
            run_command(['wipefs', '-af', disk])
            log_info("Filesystem signatures wiped")
        except Exception as e:
            log_error(f"Failed to wipe {disk}: {e}")
            failed.append(disk)
            continue

        # Zero out superblock area
        try:
            log_info(f"Zeroing superblock area on {disk}...")
            run_command(['dd', 'if=/dev/zero', f'of={disk}', 'bs=1M', 'count=4', 'conv=fsync'], check=False)
            time.sleep(1)
        except Exception as e:
            log_verbose(f"Could not zero superblock: {e}")

        # Reload partition table
        try:
            run_command(['blockdev', '--rereadpt', disk], check=False)
            run_command(['partprobe', disk], check=False)
            log_verbose("Partition table reloaded")
        except Exception as e:
            log_verbose(f"Could not reload partition table: {e}")

        # Wait for udev to settle
        try:
            run_command(['udevadm', 'settle', '-t', '10'], check=False)
        except Exception as e:
            log_verbose(f"udevadm settle failed: {e}")
        time.sleep(3)

        # Re-discover system after wipe
        post_system = discover_system()
        if disk in post_system:
            post_info = post_system[disk]
            still_has_parts = bool(post_info['partitions'])
            still_has_bcache = bool(post_info['bcache'])
            if still_has_parts or still_has_bcache:
                log_error(f"Disk {disk} still has partitions or bcache after full cleanup!")
                # Try to force partition removal
                try:
                    log_info(f"Attempting to remove all partitions from {disk}...")
                    run_command(['sgdisk', '-Z', disk], check=False)
                    run_command(['partprobe', disk], check=False)
                    run_command(['blockdev', '--rereadpt', disk], check=False)
                    run_command(['udevadm', 'settle', '-t', '5'], check=False)
                    time.sleep(2)
                except Exception as e:
                    log_verbose(f"Partition removal issue: {e}")
                # Re-check
                post_system2 = discover_system()
                post_info2 = post_system2.get(disk)
                if post_info2 and (post_info2['partitions'] or post_info2['bcache']):
                    log_error(f"Disk {disk} still not clean after forced partition removal!")
                    failed.append(disk)
                    continue
                else:
                    log_info(f"Disk {disk} wiped and partitions removed.")
            else:
                log_info(f"Disk {disk} wiped successfully and is clean.")
        else:
            log_info(f"Disk {disk} no longer visible to system after wipe (expected for full reset).")

    if failed:
        log_error(f"Reset failed for: {', '.join(failed)}")
        return 1
    log_info("All specified disks wiped and reset successfully.")
    return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Manage physical hard drives and logical storage configurations on Linux systems.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable detailed output for debugging'
    )
    
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Auto-approve destructive operations (configure mode only)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # SHOW command
    parser_show = subparsers.add_parser(
        'show',
        help='Display comprehensive system storage information'
    )
    parser_show.set_defaults(func=cmd_show)
    
    # CONFIGURE command
    parser_configure = subparsers.add_parser(
        'configure',
        help='Configure disks for bcache and nonraid'
    )
    parser_configure.set_defaults(func=cmd_configure)
    
    # RESET command
    parser_reset = subparsers.add_parser(
        'reset',
        help='Reset disk configuration'
    )
    parser_reset.add_argument(
        'disks',
        nargs='+',
        help='Disk devices to reset (e.g. /dev/sdb /dev/sdc)'
    )
    parser_reset.set_defaults(func=cmd_reset)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set global config
    Config.verbose = args.verbose
    Config.auto_yes = args.yes
    
    # Ensure root privileges
    if os.geteuid() != 0:
        log_error("This script must be run as root")
        return 1
    
    # Execute command
    if hasattr(args, 'func'):
        try:
            if args.command == 'reset':
                return args.func(args.disks)
            else:
                return args.func(args)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            return 130
        except Exception as e:
            log_error(f"Unexpected error: {e}")
            if Config.verbose:
                import traceback
                traceback.print_exc()
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
