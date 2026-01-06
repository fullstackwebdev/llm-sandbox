#!/usr/bin/env python3
"""
Test script to verify Firecracker backend functionality
"""

import os
import tempfile
import uuid
from pathlib import Path

from llm_sandbox.const import SandboxBackend, SupportedLanguage
from llm_sandbox.interactive import InteractiveSandboxSession


def test_firecracker_backend():
    """Test Firecracker backend functionality."""
    print("Testing Firecracker backend...")
    
    # Check if required files exist
    kernel_path = os.path.expanduser("~/firecracker_data/vmlinux")
    rootfs_path = os.path.expanduser("~/firecracker_data/rootfs.ext4")
    
    if not os.path.exists(kernel_path):
        print(f"ERROR: Kernel image not found at {kernel_path}")
        print("You need to set up Firecracker kernel and rootfs first.")
        return False
    
    if not os.path.exists(rootfs_path):
        print(f"ERROR: Rootfs image not found at {rootfs_path}")
        print("You need to set up Firecracker kernel and rootfs first.")
        return False
    
    print(f"Found kernel: {kernel_path}")
    print(f"Found rootfs: {rootfs_path}")
    
    # Test creating a session
    try:
        print("\nCreating Firecracker sandbox session...")
        with InteractiveSandboxSession(
            backend=SandboxBackend.FIRECRACKER,
            lang=SupportedLanguage.PYTHON,
            kernel_image_path=kernel_path,
            rootfs_path=rootfs_path,
            memory_size_mib=256,
            vcpu_count=1
        ) as session:
            print("Session created successfully!")
            
            # Test running a simple command
            print("Running test command...")
            result = session.run("python3 --version")
            print(f"Command result: {result}")
            print(f"Exit code: {result.exit_code}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            
            if result.exit_code == 0:
                print("\n✓ Firecracker backend test PASSED!")
                return True
            else:
                print(f"\n✗ Firecracker backend test FAILED: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"\n✗ Firecracker backend test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_firecracker_backend()
    if not success:
        print("\nFirecracker backend test failed.")
        exit(1)
    else:
        print("\nFirecracker backend test completed successfully!")
        exit(0)