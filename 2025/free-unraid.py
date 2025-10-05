#!/usr/bin/env python3
"""
Author: Giovanni Mazzeo (github.com/thelinuxguy)

free-unraid.py - Manage physical hard drives and logical storage configurations on Linux systems.
Integrates with bcache and the nonraid project.
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
        'sgdisk': 'GPT partitioning',
        'make-bcache': 'bcache creation',
        'blockdev': 'device information',
        'smartctl': 'SMART status'
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
        
        # Get power-on hours
        for line in result.stdout.split('\n'):
            if 'Power_On_Hours' in line or 'Power On Hours' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i > 0:
                        hours = int(part)
                        break
    except Exception:
        pass
    
    return status, hours


def get_ata_slot(device: str) -> Optional[str]:
    """Get ATA/SATA slot mapping for the device"""
    try:
        # Get the device name without /dev/
        dev_name = device.replace('/dev/', '')
        
        # Try to find ATA slot in sysfs
        sys_block_path = f"/sys/block/{dev_name}"
        if os.path.exists(sys_block_path):
            device_link = os.readlink(sys_block_path)
            # Look for ata pattern in the path
            match = re.search(r'ata\d+\.\d+', device_link)
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
        Dict with bcache device and by-id path, or None
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
                            'by_id': by_id_path
                        }
                
                return {
                    'device': device,
                    'by_id': None
                }
            return None
        
        # Find the bcache device number
        bcache_dev_path = os.path.join(bcache_path, 'dev')
        if os.path.exists(bcache_dev_path):
            with open(bcache_dev_path, 'r') as f:
                bcache_dev = f.read().strip()
            
            # Find by-id symlink
            by_id_dir = Path('/dev/disk/by-id')
            if by_id_dir.exists():
                for symlink in by_id_dir.iterdir():
                    if symlink.name.startswith('bcache-'):
                        target = symlink.resolve()
                        if target.name == bcache_dev:
                            return {
                                'device': f"/dev/{bcache_dev}",
                                'by_id': str(symlink)
                            }
            
            return {
                'device': f"/dev/{bcache_dev}",
                'by_id': None
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
    
    for disk in disks:
        log_verbose(f"Scanning {disk}...")
        
        disk_info = {
            'disk_path': disk,
            'raw_disk_size': get_disk_size(disk),
            'disk_model': get_disk_model(disk),
            'disk_serial': get_disk_serial(disk),
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
    
    log_info(f"Discovery complete: {len(system)} disk(s) found")
    return system


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
            # Skip disks that already have bcache or nonraid config
            if disk_info['bcache'] or disk_info['nonraid_config']:
                status = "configured"
            elif disk_path in pending_configs:
                status = "pending"
            else:
                status = "available"
                available_disks.append(disk_path)
                disk_index_map[index] = disk_path
                index += 1
            
            # Display with index number for available disks
            if status == "available":
                display_index = len(disk_index_map)
                print(f"  [{display_index}] {disk_path} - {disk_info['disk_model']} ({disk_info['raw_disk_size']}) [{status}]")
            else:
                print(f"      {disk_path} - {disk_info['disk_model']} ({disk_info['raw_disk_size']}) [{status}]")
        
        if not available_disks:
            print("\nNo available disks to configure.")
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
            
            # Verify it's in available disks
            if disk_to_configure not in available_disks:
                log_error(f"Invalid disk selection: {user_input}")
                continue
        
        disk_info = system[disk_to_configure]
        
        # Warning about destructive operation
        print(f"\n{Colors.WARNING}WARNING: This will destroy all data on {disk_to_configure}!{Colors.ENDC}")
        print(f"Disk: {disk_info['disk_model']} ({disk_info['raw_disk_size']})")
        
        if not prompt_yes_no("Continue with this disk?", default=False):
            continue
        
        # Step 1: Bcache Setup
        log_info(f"Creating bcache backing device on {disk_to_configure}...")
        try:
            run_command(['make-bcache', '-B', disk_to_configure])
            log_info("Bcache created successfully")
        except Exception as e:
            log_error(f"Failed to create bcache: {e}")
            continue
        
        # Re-discover to get bcache info
        system = discover_system()
        disk_info = system[disk_to_configure]
        
        if not disk_info['bcache']:
            log_error("Failed to detect bcache device after creation")
            continue
        
        bcache_device = disk_info['bcache']['device']
        log_info(f"Bcache device: {bcache_device}")
        
        # Step 2: Partitioning
        log_info(f"Creating partition on {bcache_device}...")
        try:
            run_command(['sgdisk', '-o', '-a', '8', '-n', '1:32K:0', bcache_device])
            log_info("Partition created successfully")
        except Exception as e:
            log_error(f"Failed to create partition: {e}")
            continue
        
        # Partition path
        partition_path = f"{bcache_device}p1"
        
        # Wait for partition to appear
        import time
        for i in range(10):
            if os.path.exists(partition_path):
                break
            time.sleep(0.5)
        
        if not os.path.exists(partition_path):
            log_error(f"Partition {partition_path} did not appear")
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
        
        # Store configuration
        pending_configs[disk_to_configure] = {
            'slot': slot,
            'part_path': partition_path,
            'part_size': part_size,
            'type': disk_type,
            'import_cmd': import_cmd
        }
        
        log_info(f"Configuration prepared: Slot {slot}, Type {disk_type}")
        
        # Ask about additional disks
        if not prompt_yes_no("\nConfigure additional disks?", default=False):
            break
    
    # Step 5: Final Commit
    if not pending_configs:
        log_info("No configurations to commit")
        return 0
    
    print(f"\n{Colors.BOLD}Pending configurations:{Colors.ENDC}")
    for disk, config in pending_configs.items():
        print(f"  {disk}: Slot {config['slot']}, Type {config['type']}")
    
    if not prompt_yes_no("\nCommit configuration and exit?", default=False):
        log_warning("Configuration discarded")
        return 0
    
    # Execute import commands
    log_info("Committing configurations...")
    
    for disk, config in pending_configs.items():
        log_info(f"Importing {disk} to slot {config['slot']}...")
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
                log_info(f"✓ {disk} imported successfully")
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
    RESET command: Reset disk configuration.
    
    Implementation to be defined.
    
    Returns:
        Exit code (0 for success)
    """
    log_warning("RESET command not yet implemented")
    return 1


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
