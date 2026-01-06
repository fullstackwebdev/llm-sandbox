# Firecracker Backend Implementation

## Overview

The Firecracker backend provides microVM-based isolation for the LLM Sandbox, offering enhanced security and performance compared to traditional containerization technologies. Firecracker is an open-source virtualization technology that creates lightweight microVMs, combining the security and isolation properties of traditional VMs with the resource efficiency of containers.

## Architecture

### Components

1. **FirecrackerContainerAPI**: Implements the ContainerAPI protocol for Firecracker microVMs
2. **SandboxFirecrackerSession**: Extends BaseSession to provide Firecracker-specific functionality
3. **FirecrackerPoolManager**: Manages a pool of Firecracker microVMs
4. **Guest Agent**: Runs inside the VM to handle commands from the host via VSOCK

### Communication

- Host and guest communicate via VSOCK (Virtual Socket)
- Commands are sent as JSON over VSOCK connection
- Results are returned as JSON with exit codes, stdout, and stderr

### Filesystem

- Uses OverlayFS for efficient storage
- Base rootfs is mounted as read-only (lower directory)
- VM-specific changes are stored in overlay files (upper directory)
- Provides isolation while minimizing storage overhead

## Features

### Security
- VM-level isolation with separate kernel
- Network isolation per VM
- Resource limits enforcement at VM level
- Process isolation between host and guest

### Performance
- Fast startup times (typically under 125ms)
- Minimal memory footprint (~5MB base overhead)
- Efficient resource utilization through OverlayFS
- Snapshot/restore functionality for faster initialization

### Resource Management
- Configurable CPU and memory limits
- Proper cleanup of VM resources
- CID allocation for VSOCK communication
- Overlay file management

## Usage

### Basic Usage
```python
from llm_sandbox.interactive import InteractiveSandboxSession
from llm_sandbox.const import SandboxBackend

with InteractiveSandboxSession(
    backend=SandboxBackend.FIRECRACKER,
    lang="python",
    memory_size_mib=128,
    vcpu_count=1
) as session:
    result = session.run("print('Hello from Firecracker!')")
    print(result.stdout)
```

### With Custom Configuration
```python
firecracker_config = {
    "kernel_image_path": "/path/to/vmlinux.bin",
    "rootfs_path": "/path/to/rootfs.ext4",
    "memory_size_mib": 256,
    "vcpu_count": 2
}

with InteractiveSandboxSession(
    backend=SandboxBackend.FIRECRACKER,
    lang="python",
    firecracker_config=firecracker_config
) as session:
    result = session.run("print('Custom Firecracker VM!')")
    print(result.stdout)
```

### Using Pool Manager
```python
from llm_sandbox.pool import create_pool_manager, PoolConfig
from llm_sandbox.const import SandboxBackend, SupportedLanguage

pool_config = PoolConfig(
    max_pool_size=10,
    min_pool_size=3,
)

pool = create_pool_manager(
    backend=SandboxBackend.FIRECRACKER,
    config=pool_config,
    lang=SupportedLanguage.PYTHON,
    kernel_image_path="/path/to/vmlinux.bin",
    rootfs_path="/path/to/rootfs.ext4"
)

with pool:
    container = pool.acquire()
    try:
        # Use container...
        pass
    finally:
        pool.release(container)
```

## Configuration

### Runtime Configuration Options
- `memory_size_mib`: Memory size in MiB (default: 256)
- `vcpu_count`: Number of virtual CPUs (default: 1)
- `kernel_image_path`: Path to kernel image (default: ~/firecracker_data/vmlinux)
- `rootfs_path`: Path to root filesystem image (default: ~/firecracker_data/rootfs.ext4)

### Pool Configuration Options
- `max_pool_size`: Maximum number of VMs in the pool
- `min_pool_size`: Minimum number of VMs to maintain
- `health_check_interval`: Interval for health checking VMs
- `idle_timeout`: Time after which idle VMs are recycled

## Dependencies

- Firecracker binary (typically installed via package manager)
- Linux kernel image (vmlinux)
- Root filesystem image (ext4 format)
- Python libraries for subprocess management and JSON handling

## Implementation Details

### VM Lifecycle
1. Create overlay file for VM-specific changes
2. Generate Firecracker configuration with kernel, drives, and machine settings
3. Start Firecracker process with configuration
4. Establish VSOCK connection for command execution
5. Execute commands via guest agent
6. Clean up resources when VM is terminated

### OverlayFS Management
- Creates sparse ext4 overlay files for each VM
- Mounts base rootfs as read-only
- Stores VM-specific changes in overlay files
- Properly cleans up overlay files when VM is destroyed

### VSOCK Communication
- Uses VSOCK for efficient host-guest communication
- Implements handshake protocol for connection establishment
- Handles command serialization/deserialization
- Provides proper error handling and timeouts

## Security Considerations

- Each VM runs with its own kernel, providing strong isolation
- Network interfaces can be configured per VM for additional isolation
- Resource limits prevent one VM from affecting others
- Guest agent runs with minimal privileges inside the VM
- Communication channel (VSOCK) is isolated to the VM

## Performance Considerations

- VM startup time is typically under 125ms
- Memory overhead is minimal (~5MB base + configured amount)
- CPU overhead is low due to KVM acceleration
- I/O performance is good with proper storage configuration
- Snapshot/restore can reduce cold start times for common environments

## Troubleshooting

### Common Issues
1. **KVM not available**: Ensure virtualization is enabled in BIOS and KVM modules are loaded
2. **Permission errors**: Ensure proper permissions for Firecracker binary and device access
3. **VSOCK connection failures**: Verify guest agent is running inside the VM
4. **Resource limits**: Check system limits for processes, files, and memory

### Debugging
- Check Firecracker logs for VM startup issues
- Verify kernel and rootfs paths are correct and accessible
- Ensure guest agent is properly installed and running in the rootfs
- Monitor system resources to ensure sufficient capacity for VMs