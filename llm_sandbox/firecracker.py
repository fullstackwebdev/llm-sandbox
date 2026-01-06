"""Firecracker implementation for LLM Sandbox.

This module provides Firecracker microVM support for the LLM Sandbox,
offering enhanced security through VM-level isolation.
"""

import asyncio
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Tuple

from llm_sandbox.const import DefaultImage, SupportedLanguage
from llm_sandbox.core.config import SessionConfig
from llm_sandbox.core.session_base import BaseSession
from llm_sandbox.exceptions import ContainerError, NotOpenSessionError
from llm_sandbox.security import SecurityPolicy


class FirecrackerContainerAPI:
    """Firecracker implementation of the ContainerAPI protocol."""

    def __init__(self, firecracker_binary: str = "/usr/local/bin/firecracker", stream: bool = False) -> None:
        """Initialize Firecracker container API."""
        self.firecracker_binary = firecracker_binary
        self.stream = stream
        self.vm_processes: dict = {}  # Maps VM IDs to process objects
        self.api_sockets: dict = {}  # Maps VM IDs to API socket paths
        self.vsock_paths: dict = {}  # Maps VM IDs to VSOCK socket paths

    def create_container(self, config: dict) -> str:
        """Create Firecracker VM with the given configuration."""
        vm_id = str(uuid.uuid4())
        
        # Extract configuration parameters
        kernel_path = config.get("kernel_image_path")
        rootfs_path = config.get("rootfs_path")
        memory_size_mib = config.get("memory_size_mib", 256)
        vcpu_count = config.get("vcpu_count", 1)
        vsock_path = config.get("vsock_path")
        api_socket_path = config.get("api_socket_path")
        
        # Create overlay file for this VM
        overlay_path = self._create_overlay_file(vm_id, size_mb=2048)
        
        # Create drives configuration
        drives = [
            {
                "drive_id": "rootfs",
                "path_on_host": rootfs_path,
                "is_root_device": True,
                "is_read_only": True,
            },
            {
                "drive_id": "overlay",
                "path_on_host": overlay_path,
                "is_root_device": False,
                "is_read_only": False,
            },
        ]
        
        # Generate Firecracker configuration
        fc_config = {
            "boot-source": {
                "kernel_image_path": kernel_path,
                "boot_args": "console=ttyS0 reboot=k panic=1 pci=off",
            },
            "drives": drives,
            "machine-config": {
                "vcpu_count": vcpu_count,
                "mem_size_mib": memory_size_mib,
                "smt": False,
            },
            "vsock": {
                "guest_cid": 3,  # Standard guest CID for communication
                "uds_path": vsock_path,
            },
        }
        
        # Write config to temporary file
        config_path = f"/tmp/fc_config_{vm_id}.json"
        with open(config_path, 'w') as f:
            json.dump(fc_config, f)
        
        # Start Firecracker process
        try:
            # Validate KVM availability
            if not os.path.exists('/dev/kvm'):
                raise RuntimeError("KVM not available")
            
            # Start Firecracker with the configuration
            process = subprocess.Popen([
                self.firecracker_binary,
                "--api-sock", api_socket_path,
                "--config-file", config_path,
            ], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Store references
            self.vm_processes[vm_id] = process
            self.api_sockets[vm_id] = api_socket_path
            self.vsock_paths[vm_id] = vsock_path
            
            # Wait for API socket to be created
            for _ in range(20):  # 10 seconds
                if os.path.exists(api_socket_path):
                    break
                time.sleep(0.5)
            else:
                process.terminate()
                raise RuntimeError("API socket not created")
            
            # Start the instance via API
            self._start_instance_via_api(api_socket_path)
            
            return vm_id
            
        except Exception as e:
            # Cleanup on failure
            if os.path.exists(config_path):
                os.remove(config_path)
            raise e

    def _create_overlay_file(self, vm_id: str, size_mb: int = 1024) -> str:
        """Create sparse ext4 overlay file for VM-specific changes."""
        overlay_path = f"/tmp/fc_overlay_{vm_id}.ext4"

        try:
            # Create sparse file
            result = subprocess.run([
                "dd", "if=/dev/zero", f"of={overlay_path}",
                "bs=1M", "count=0", f"seek={size_mb}"
            ], check=True, capture_output=True, text=True)

            # Format as ext4
            result = subprocess.run([
                "mkfs.ext4", "-F", "-q", overlay_path
            ], check=True, capture_output=True, text=True)

            # Set permissions
            os.chmod(overlay_path, 0o644)

            return overlay_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Overlay creation failed: {e}")

    def _start_instance_via_api(self, api_socket_path: str) -> None:
        """Start the Firecracker instance via its API."""
        import subprocess
        proc = subprocess.run([
            "curl", "--unix-socket", api_socket_path,
            "-X", "PUT", "http://localhost/actions",
            "-d", '{"action_type": "InstanceStart"}'
        ], capture_output=True, text=True)
        
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to start instance: {proc.stderr}")

    def start_container(self, container_id: str) -> None:
        """Start Firecracker VM (already started during creation)."""
        # VM is started during creation, so this is a no-op
        pass

    def stop_container(self, container_id: str) -> None:
        """Stop Firecracker VM and cleanup resources."""
        if container_id in self.vm_processes:
            process = self.vm_processes[container_id]
            process.terminate()
            
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            # Cleanup resources
            if container_id in self.api_sockets:
                api_socket = self.api_sockets[container_id]
                if os.path.exists(api_socket):
                    os.remove(api_socket)
            
            if container_id in self.vsock_paths:
                vsock_path = self.vsock_paths[container_id]
                if os.path.exists(vsock_path):
                    os.remove(vsock_path)
            
            # Remove overlay file
            overlay_path = f"/tmp/fc_overlay_{container_id}.ext4"
            if os.path.exists(overlay_path):
                os.remove(overlay_path)
            
            # Remove from tracking
            del self.vm_processes[container_id]
            if container_id in self.api_sockets:
                del self.api_sockets[container_id]
            if container_id in self.vsock_paths:
                del self.vsock_paths[container_id]

    def execute_command(self, container_id: str, command: str, **kwargs: Any) -> Tuple[int, Any]:
        """Execute command in Firecracker VM via VSOCK."""
        if container_id not in self.vsock_paths:
            raise ContainerError(f"VM {container_id} not found")
        
        vsock_path = self.vsock_paths[container_id]
        workdir = kwargs.get("workdir")
        
        # Prepare command with working directory if specified
        if workdir:
            full_command = f"cd {workdir} && {command}"
        else:
            full_command = command
        
        try:
            # Connect to the guest agent via VSOCK
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(30.0)  # 30-second timeout
                sock.connect(vsock_path)
                
                # Send CONNECT handshake
                sock.send(b"CONNECT 5000\n")
                response = sock.recv(1024)
                
                if not response.startswith(b"OK"):
                    raise ContainerError(f"VSOCK handshake failed: {response}")
                
                # Send command
                payload = json.dumps({"command": full_command}).encode()
                sock.send(payload)
                
                # Receive result
                data = sock.recv(65536)
                if not data:
                    raise ContainerError("No response from guest agent")
                
                result = json.loads(data.decode())
                
                if "error" in result:
                    return 1, (result["error"], "")
                
                return result.get("exit_code", 0), (
                    result.get("stdout", ""),
                    result.get("stderr", "")
                )
                
        except socket.timeout:
            raise ContainerError("Guest agent timeout - is it running inside VM?")
        except Exception as e:
            raise ContainerError(f"VSOCK communication error: {str(e)}")

    def copy_to_container(self, container_id: str, src: str, dest: str, **kwargs: Any) -> None:
        """Copy file to Firecracker VM via VSOCK or shared volume."""
        if container_id not in self.vsock_paths:
            raise ContainerError(f"VM {container_id} not found")
        
        vsock_path = self.vsock_paths[container_id]
        
        # Read the source file
        with open(src, 'rb') as f:
            file_content = f.read()
        
        try:
            # Connect to the guest agent via VSOCK
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(30.0)  # 30-second timeout
                sock.connect(vsock_path)
                
                # Send CONNECT handshake
                sock.send(b"CONNECT 5000\n")
                response = sock.recv(1024)
                
                if not response.startswith(b"OK"):
                    raise ContainerError(f"VSOCK handshake failed: {response}")
                
                # Send file copy command
                payload = json.dumps({
                    "command": "copy_file",
                    "destination": dest,
                    "content": file_content.hex()  # Encode binary as hex
                }).encode()
                
                sock.send(payload)
                
                # Receive result
                data = sock.recv(65536)
                if not data:
                    raise ContainerError("No response from guest agent")
                
                result = json.loads(data.decode())
                
                if result.get("status") != "success":
                    raise ContainerError(f"File copy failed: {result.get('error', 'Unknown error')}")
                    
        except socket.timeout:
            raise ContainerError("Guest agent timeout - is it running inside VM?")
        except Exception as e:
            raise ContainerError(f"VSOCK communication error during file copy: {str(e)}")

    def copy_from_container(self, container_id: str, src: str, **kwargs: Any) -> Tuple[bytes, dict]:
        """Copy file from Firecracker VM via VSOCK or shared volume."""
        if container_id not in self.vsock_paths:
            raise ContainerError(f"VM {container_id} not found")
        
        vsock_path = self.vsock_paths[container_id]
        
        try:
            # Connect to the guest agent via VSOCK
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(30.0)  # 30-second timeout
                sock.connect(vsock_path)
                
                # Send CONNECT handshake
                sock.send(b"CONNECT 5000\n")
                response = sock.recv(1024)
                
                if not response.startswith(b"OK"):
                    raise ContainerError(f"VSOCK handshake failed: {response}")
                
                # Send file read command
                payload = json.dumps({
                    "command": "read_file",
                    "source": src
                }).encode()
                
                sock.send(payload)
                
                # Receive result
                data = sock.recv(65536)
                if not data:
                    raise ContainerError("No response from guest agent")
                
                result = json.loads(data.decode())
                
                if result.get("status") != "success":
                    raise ContainerError(f"File read failed: {result.get('error', 'Unknown error')}")
                
                # Decode the file content from hex
                file_content = bytes.fromhex(result.get("content", ""))
                
                # Create a basic stat dict
                stat_dict = {
                    "name": src,
                    "size": len(file_content),
                    "mtime": time.time(),
                    "mode": 0o644,
                    "linkTarget": "",
                }
                
                return file_content, stat_dict
                    
        except socket.timeout:
            raise ContainerError("Guest agent timeout - is it running inside VM?")
        except Exception as e:
            raise ContainerError(f"VSOCK communication error during file read: {str(e)}")


class SandboxFirecrackerSession(BaseSession):
    r"""Sandbox session implemented using Firecracker microVMs.

    This class provides a sandboxed environment for code execution by leveraging Firecracker.
    It handles VM lifecycle, code execution, library installation, and file operations
    within the Firecracker microVM.
    """

    def __init__(
        self,
        kernel_image_path: str | None = None,
        rootfs_path: str | None = None,
        firecracker_config: dict | None = None,
        client: Any = None,  # Not used for Firecracker but kept for compatibility
        image: str | None = None,
        lang: str = SupportedLanguage.PYTHON,
        verbose: bool = False,
        stream: bool = False,
        runtime_configs: dict | None = None,
        workdir: str = "/sandbox",
        security_policy: SecurityPolicy | None = None,
        default_timeout: float | None = None,
        execution_timeout: float | None = None,
        session_timeout: float | None = None,
        container_id: str | None = None,  # This will be VM ID for Firecracker
        skip_environment_setup: bool = False,
        **kwargs: Any,
    ) -> None:
        r"""Initialize Firecracker session.

        Args:
            kernel_image_path: Path to the kernel image to use
            rootfs_path: Path to the root filesystem image
            firecracker_config: Additional Firecracker-specific configuration
            client: Not used for Firecracker but kept for compatibility
            image: Not used for Firecracker but kept for compatibility
            lang: The language to use
            verbose: Whether to enable verbose output
            stream: Whether to stream the output
            runtime_configs: Firecracker runtime configurations
            workdir: The working directory to use
            security_policy: The security policy to use
            default_timeout: The default timeout to use
            execution_timeout: The execution timeout to use
            session_timeout: The session timeout to use
            container_id: ID of existing VM to connect to
            skip_environment_setup: Skip language-specific environment setup
            **kwargs: Additional keyword arguments

        Returns:
            None

        """
        # Set up default paths if not provided
        if kernel_image_path is None:
            kernel_image_path = os.path.expanduser("~/firecracker_data/vmlinux")
        if rootfs_path is None:
            rootfs_path = os.path.expanduser("~/firecracker_data/rootfs.ext4")
        
        # Store Firecracker-specific configuration
        self.kernel_image_path = kernel_image_path
        self.rootfs_path = rootfs_path
        self.firecracker_config = firecracker_config or {}
        
        # Create session config
        config = SessionConfig(
            image=image,
            lang=SupportedLanguage(lang.upper()),
            verbose=verbose,
            workdir=workdir,
            runtime_configs=runtime_configs or {},
            security_policy=security_policy,
            default_timeout=default_timeout,
            execution_timeout=execution_timeout,
            session_timeout=session_timeout,
            container_id=container_id,
            skip_environment_setup=skip_environment_setup,
        )

        super().__init__(config=config, **kwargs)

        # Initialize Firecracker API
        self.container_api = FirecrackerContainerAPI(stream=stream)

        # For compatibility with base class
        self.stream = stream
        self.using_existing_vm = config.is_using_existing_container()

    def _ensure_directory_exists(self, path: str) -> None:
        r"""Ensure the directory exists in the VM.

        Args:
            path (str): The path to ensure exists.

        """
        mkdir_result = self.container_api.execute_command(self.container, f"mkdir -p '{path}'")
        if mkdir_result[0] != 0:
            stdout_output, stderr_output = self._process_non_stream_output(mkdir_result[1])
            error_msg = stderr_output if stderr_output else stdout_output
            self._log(f"Failed to create directory {path}: {error_msg}", "error")

    def _ensure_ownership(self, paths: list[str]) -> None:
        r"""Ensure ownership of the given paths in the VM.

        This method changes the ownership of specified paths to the current user

        Args:
            paths (list[str]): The paths to ensure ownership of.

        """
        # For Firecracker, we'll ensure paths are accessible
        # This is a simplified implementation - in a real scenario, 
        # we'd need to handle user mapping properly
        for path in paths:
            self.container_api.execute_command(self.container, f"chmod 755 '{path}'")

    def _process_non_stream_output(self, output: Any) -> tuple[str, str]:
        """Process non-streaming Firecracker output."""
        if isinstance(output, tuple) and len(output) == 2:  # (stdout, stderr)
            stdout_data, stderr_data = output
            return str(stdout_data), str(stderr_data)
        return "", ""

    def _process_stream_output(self, output: Any) -> tuple[str, str]:
        """Process streaming Firecracker output (not used but required by mixin)."""
        return self._process_non_stream_output(output)

    def _handle_timeout(self) -> None:
        """Handle Firecracker timeout cleanup."""
        if self.container:
            try:
                self.close()
            except Exception as e:  # noqa: BLE001
                self._log(f"Error during timeout cleanup: {e}", "error")

    def _connect_to_existing_container(self, vm_id: str) -> None:
        """Connect to an existing Firecracker VM.

        Args:
            vm_id (str): The ID of the existing VM to connect to.

        Raises:
            ContainerError: If the VM cannot be found or accessed.

        """
        # For now, we'll just store the VM ID
        # In a real implementation, we'd verify the VM is running
        self.container = vm_id
        self._log(f"Connected to existing VM {vm_id}")

    def open(self) -> None:
        r"""Open Firecracker session.

        This method prepares the Firecracker environment for code execution by:
        - Creating a microVM with the specified configuration
        - Setting up the environment (if not using existing VM)

        Raises:
            ContainerError: If VM creation or initialization fails.

        """
        super().open()

        if self.using_existing_vm and self.config.container_id:
            # Connect to existing VM
            self._connect_to_existing_container(self.config.container_id)
        else:
            # Create new VM
            vm_config = {
                "kernel_image_path": self.kernel_image_path,
                "rootfs_path": self.rootfs_path,
                "memory_size_mib": self.config.runtime_configs.get("memory_size_mib", 256),
                "vcpu_count": self.config.runtime_configs.get("vcpu_count", 1),
                "vsock_path": f"/tmp/fc_vsock_{uuid.uuid4()}.sock",
                "api_socket_path": f"/tmp/fc_api_{uuid.uuid4()}.sock",
            }
            vm_config.update(self.firecracker_config)

            self.container = self.container_api.create_container(vm_config)

        # Setup environment (skipped for existing VMs)
        if not self.using_existing_vm:
            self.environment_setup()

    def close(self) -> None:
        r"""Close the Firecracker sandbox session.

        This method cleans up Firecracker resources by:
        1. Stopping the microVM if we created it.
        2. Cleaning up associated resources.

        Note: When using existing VMs, we only disconnect but don't stop the VM.

        """
        super().close()

        if self.container:
            # Only stop VM if we created it (not existing VM)
            if not self.using_existing_vm:
                try:
                    self.container_api.stop_container(self.container)
                    self._log("Stopped VM")
                except Exception as e:  # noqa: BLE001
                    self._log(f"Error cleaning up VM: {e}", "error")
            else:
                self._log("Disconnected from existing VM")

            self.container = None