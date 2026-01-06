"""Firecracker-specific container pool manager."""

from typing import Any

from llm_sandbox.const import SupportedLanguage
from llm_sandbox.pool.base import ContainerPoolManager
from llm_sandbox.pool.config import PoolConfig


class FirecrackerPoolManager(ContainerPoolManager):
    """Container pool manager for Firecracker backend.

    This manager creates and manages a pool of Firecracker microVMs,
    reusing the standard session logic for VM initialization and
    environment setup (venv, pip, library installation, etc.).
    """

    def __init__(
        self,
        config: PoolConfig,
        lang: SupportedLanguage | str,
        image: str | None = None,  # Not used for Firecracker but kept for compatibility
        kernel_image_path: str | None = None,
        rootfs_path: str | None = None,
        firecracker_config: dict | None = None,
        client: Any = None,  # Not used for Firecracker but kept for compatibility
        runtime_configs: dict | None = None,
        **session_kwargs: Any,
    ) -> None:
        """Initialize Firecracker pool manager.

        Args:
            config: Pool configuration
            lang: Programming language
            image: Not used for Firecracker but kept for compatibility
            kernel_image_path: Path to the kernel image to use
            rootfs_path: Path to the root filesystem image
            firecracker_config: Additional Firecracker-specific configuration
            client: Not used for Firecracker but kept for compatibility
            runtime_configs: Firecracker runtime configurations
            **session_kwargs: Additional session arguments

        """
        self.kernel_image_path = kernel_image_path
        self.rootfs_path = rootfs_path
        self.firecracker_config = firecracker_config or {}
        self.runtime_configs = runtime_configs or {}

        # For Firecracker, we'll use a placeholder for image since it's not applicable
        # but we still need to pass something to the base class
        image_placeholder = f"firecracker-{lang.lower()}" if image is None else image

        super().__init__(client=client, config=config, lang=lang, image=image_placeholder, **session_kwargs)

    def _create_session_for_container(self) -> Any:
        """Create a Firecracker session for initializing a VM.

        This creates a session that, when opened, will:
        1. Create a Firecracker VM
        2. Set up the environment (venv, pip, libraries, etc.)

        Returns:
            FirecrackerSession instance (not yet opened)

        """
        from llm_sandbox.firecracker import SandboxFirecrackerSession

        # Create session with same configuration as the pool
        # The session handles all initialization automatically
        return SandboxFirecrackerSession(
            kernel_image_path=self.kernel_image_path,
            rootfs_path=self.rootfs_path,
            firecracker_config=self.firecracker_config,
            lang=str(self.lang),
            runtime_configs=self.runtime_configs,
            **self.session_kwargs,
        )

    def _destroy_container_impl(self, vm_id: str) -> None:
        """Destroy a Firecracker VM.

        Args:
            vm_id: VM ID to destroy

        """
        from llm_sandbox.firecracker import FirecrackerContainerAPI
        
        # Create a temporary API instance to stop the VM
        api = FirecrackerContainerAPI()
        try:
            api.stop_container(vm_id)
        except Exception:
            self.logger.exception("Failed to destroy VM")

    def _get_container_id(self, vm_id: str) -> str:
        """Get Firecracker VM ID.

        Args:
            vm_id: Firecracker VM ID

        Returns:
            VM ID string

        """
        return str(vm_id)

    def _health_check_impl(self, vm_id: str) -> bool:
        """Perform health check on Firecracker VM.

        Args:
            vm_id: VM to check

        Returns:
            True if healthy, False otherwise

        """
        from llm_sandbox.firecracker import FirecrackerContainerAPI
        
        try:
            # Try to execute a simple command to verify VM responsiveness
            api = FirecrackerContainerAPI()
            exit_code, _ = api.execute_command(vm_id, "echo health_check")
            return bool(exit_code == 0)
        except Exception:
            self.logger.exception("Health check error")
            return False