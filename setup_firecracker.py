#!/usr/bin/env python3
"""
Setup script for Firecracker environment in LLM Sandbox
"""

import os
import shutil
import subprocess
from pathlib import Path


def check_firecracker_installation():
    """Check if Firecracker is properly installed."""
    print("Checking Firecracker installation...")
    
    # Check if firecracker binary exists
    if shutil.which("firecracker"):
        print("✓ Firecracker binary found")
    else:
        print("✗ Firecracker binary not found")
        return False
    
    # Check if KVM is available
    if os.path.exists("/dev/kvm"):
        print("✓ KVM available")
    else:
        print("✗ KVM not available - Firecracker requires KVM")
        return False
    
    return True


def check_kernel_rootfs():
    """Check if kernel and rootfs exist."""
    print("\nChecking kernel and rootfs...")
    
    kernel_path = os.path.expanduser("~/firecracker_data/vmlinux")
    rootfs_path = os.path.expanduser("~/firecracker_data/rootfs.ext4")
    
    if os.path.exists(kernel_path):
        print(f"✓ Kernel found: {kernel_path}")
    else:
        print(f"✗ Kernel not found: {kernel_path}")
        print("  You need to provide a kernel image for Firecracker")
        return False
    
    if os.path.exists(rootfs_path):
        print(f"✓ Rootfs found: {rootfs_path}")
    else:
        print(f"✗ Rootfs not found: {rootfs_path}")
        print("  You need to provide a rootfs image for Firecracker")
        return False
    
    return True


def check_guest_agent_in_rootfs():
    """Check if guest agent is installed in the rootfs."""
    print("\nChecking guest agent in rootfs...")
    
    # This is a simplified check - in reality, we'd need to mount the rootfs
    # and check if the guest agent is installed
    print("Note: The guest agent needs to be installed inside the rootfs image")
    print("The guest agent should be located at /root/guest_agent.py in the rootfs")
    print("And should be configured to run as a service or at boot time")
    
    return True  # Just informational for now


def setup_guest_agent_in_rootfs():
    """Instructions for setting up guest agent in rootfs."""
    print("\nTo properly set up the guest agent in your rootfs:")
    print("1. Mount your rootfs image:")
    print("   sudo mkdir /mnt/firecracker_rootfs")
    print("   sudo mount -o loop ~/firecracker_data/rootfs.ext4 /mnt/firecracker_rootfs")
    print()
    print("2. Copy the guest agent to the rootfs:")
    print("   sudo cp llm_sandbox/guest_agent.py /mnt/firecracker_rootfs/root/")
    print()
    print("3. Install Python dependencies in the rootfs if needed:")
    print("   sudo chroot /mnt/firecracker_rootfs apt update && apt install -y python3")
    print()
    print("4. Create a systemd service or add to rc.local to start the guest agent at boot:")
    print("   Create /mnt/firecracker_rootfs/etc/systemd/system/guest-agent.service")
    print("   Or add to /mnt/firecracker_rootfs/etc/rc.local:")
    print("   /usr/bin/python3 /root/guest_agent.py &")
    print()
    print("5. Unmount the rootfs:")
    print("   sudo umount /mnt/firecracker_rootfs")
    print()


def main():
    """Main function to check Firecracker setup."""
    print("Firecracker Backend Setup Check for LLM Sandbox")
    print("=" * 50)
    
    # Check Firecracker installation
    if not check_firecracker_installation():
        print("\nFirecracker is not properly installed. Please install Firecracker and ensure KVM is available.")
        return 1
    
    # Check kernel and rootfs
    if not check_kernel_rootfs():
        print("\nKernel or rootfs not found. Please set up your Firecracker images.")
        return 1
    
    # Check guest agent
    check_guest_agent_in_rootfs()
    setup_guest_agent_in_rootfs()
    
    print("\n" + "=" * 50)
    print("Setup check completed.")
    print("Note: The guest agent must be properly installed in your rootfs for VSOCK communication to work.")
    
    return 0


if __name__ == "__main__":
    exit(main())