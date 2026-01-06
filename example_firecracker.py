#!/usr/bin/env python3
"""
Example usage of the Firecracker backend in LLM Sandbox
"""

from llm_sandbox.const import SandboxBackend, SupportedLanguage
from llm_sandbox.interactive import InteractiveSandboxSession


def example_usage():
    """Example of how to use the Firecracker backend."""
    print("Firecracker Backend Example")
    print("=" * 30)
    
    print("\n1. Basic usage:")
    print("```python")
    print("from llm_sandbox.interactive import InteractiveSandboxSession")
    print("from llm_sandbox.const import SandboxBackend, SupportedLanguage")
    print()
    print("# Create a Firecracker sandbox session")
    print("with InteractiveSandboxSession(")
    print("    backend=SandboxBackend.FIRECRACKER,")
    print("    lang=SupportedLanguage.PYTHON,")
    print("    memory_size_mib=256,  # 256MB memory")
    print("    vcpu_count=1          # 1 virtual CPU")
    print(") as session:")
    print("    result = session.run(\"print('Hello from Firecracker VM!')\")")
    print("    print(result.stdout)")
    print("```")
    
    print("\n2. With custom configuration:")
    print("```python")
    print("# With custom kernel and rootfs paths")
    print("with InteractiveSandboxSession(")
    print("    backend=SandboxBackend.FIRECRACKER,")
    print("    lang=SupportedLanguage.PYTHON,")
    print("    kernel_image_path=\"/path/to/vmlinux.bin\",")
    print("    rootfs_path=\"/path/to/rootfs.ext4\",")
    print("    memory_size_mib=512,")
    print("    vcpu_count=2")
    print(") as session:")
    print("    result = session.run(\"python3 -c \\\"import sys; print(f'Python {sys.version}\\\"\")")
    print("    print(result.stdout)")
    print("```")
    
    print("\n3. Using with pool manager:")
    print("```python")
    print("from llm_sandbox.pool import create_pool_manager, PoolConfig")
    print()
    print("# Create a pool of Firecracker VMs")
    print("pool_config = PoolConfig(")
    print("    max_pool_size=10,  # Max 10 VMs in pool")
    print("    min_pool_size=2,   # Keep at least 2 VMs ready")
    print("    health_check_interval=30  # Check health every 30 seconds")
    print(")")
    print()
    print("pool = create_pool_manager(")
    print("    backend=SandboxBackend.FIRECRACKER,")
    print("    config=pool_config,")
    print("    lang=SupportedLanguage.PYTHON,")
    print("    kernel_image_path=\"/path/to/vmlinux.bin\",")
    print("    rootfs_path=\"/path/to/rootfs.ext4\"")
    print(")")
    print()
    print("with pool:")
    print("    container = pool.acquire()  # Get a VM from the pool")
    print("    try:")
    print("        # Execute code in the VM")
    print("        result = container.container_api.execute_command(")
    print("            container.container_id,")
    print("            \"echo 'Running in pooled Firecracker VM'\"")
    print("        )")
    print("        print(result)")
    print("    finally:")
    print("        pool.release(container)  # Return VM to pool")
    print("```")
    
    print("\n" + "=" * 30)
    print("Firecracker Backend Features:")
    print("• VM-level isolation with separate kernel")
    print("• Fast startup times (typically < 125ms)")
    print("• Minimal memory overhead (~5MB base)")
    print("• Resource limits enforcement")
    print("• Secure multi-tenant execution")
    print("• Compatible with existing LLM Sandbox API")
    print("=" * 30)


if __name__ == "__main__":
    example_usage()