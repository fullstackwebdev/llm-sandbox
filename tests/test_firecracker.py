"""Tests for Firecracker backend implementation."""

import unittest
from unittest.mock import Mock, patch, MagicMock

from llm_sandbox.const import SandboxBackend, SupportedLanguage
from llm_sandbox.firecracker import FirecrackerContainerAPI, SandboxFirecrackerSession
from llm_sandbox.pool.factory import create_pool_manager


class TestFirecrackerContainerAPI(unittest.TestCase):
    """Test Firecracker container API implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = FirecrackerContainerAPI()

    @patch('llm_sandbox.firecracker.subprocess.run')
    @patch('llm_sandbox.firecracker.os.path.exists')
    @patch('llm_sandbox.firecracker.subprocess.Popen')
    def test_create_container(self, mock_popen, mock_exists, mock_subprocess_run):
        """Test creating a Firecracker container."""
        # Mock KVM availability
        mock_exists.return_value = True

        # Mock the subprocess.run calls in _create_overlay_file
        mock_subprocess_run.return_value = Mock()

        # Mock process
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        config = {
            "kernel_image_path": "/path/to/kernel",
            "rootfs_path": "/path/to/rootfs",
            "memory_size_mib": 256,
            "vcpu_count": 1,
            "vsock_path": "/tmp/test_vsock.sock",
            "api_socket_path": "/tmp/test_api.sock",
        }

        vm_id = self.api.create_container(config)

        # Verify the process was started
        mock_popen.assert_called_once()
        self.assertIsNotNone(vm_id)
        self.assertIn(vm_id, self.api.vm_processes)

    def test_execute_command_method_signature(self):
        """Test that execute_command method has the expected signature."""
        # Just verify the method exists and has the expected name
        self.assertTrue(hasattr(self.api, 'execute_command'))
        # Check that it accepts the expected parameters
        import inspect
        sig = inspect.signature(self.api.execute_command)
        params = list(sig.parameters.keys())
        # Should have self, container_id, command, **kwargs
        self.assertIn('container_id', params)
        self.assertIn('command', params)
        # Check that it has **kwargs by looking for a parameter with kind VAR_KEYWORD
        var_kwargs_params = [p for p in sig.parameters.values() if p.kind == inspect.Parameter.VAR_KEYWORD]
        self.assertTrue(len(var_kwargs_params) > 0, "Method should accept **kwargs")


class TestSandboxFirecrackerSession(unittest.TestCase):
    """Test Firecracker session implementation."""

    def test_initialization(self):
        """Test Firecracker session initialization."""
        session = SandboxFirecrackerSession(
            kernel_image_path="/path/to/kernel",
            rootfs_path="/path/to/rootfs",
            lang=SupportedLanguage.PYTHON
        )
        
        self.assertIsNotNone(session)
        self.assertEqual(session.config.lang, SupportedLanguage.PYTHON)
        self.assertTrue(hasattr(session, 'container_api'))

    def test_backend_registration(self):
        """Test that Firecracker backend is properly registered."""
        # This tests that the interactive module recognizes the backend
        from llm_sandbox.interactive import _create_backend_session
        session = _create_backend_session(backend=SandboxBackend.FIRECRACKER, lang=SupportedLanguage.PYTHON)
        
        self.assertIsInstance(session, SandboxFirecrackerSession)


class TestFirecrackerPoolManager(unittest.TestCase):
    """Test Firecracker pool manager."""

    def test_pool_creation(self):
        """Test creating a Firecracker pool manager."""
        from llm_sandbox.pool.config import PoolConfig
        
        config = PoolConfig(max_pool_size=5, min_pool_size=1)
        
        pool_manager = create_pool_manager(
            backend=SandboxBackend.FIRECRACKER,
            config=config,
            lang=SupportedLanguage.PYTHON,
            kernel_image_path="/path/to/kernel",
            rootfs_path="/path/to/rootfs"
        )
        
        from llm_sandbox.pool.firecracker_pool import FirecrackerPoolManager
        self.assertIsInstance(pool_manager, FirecrackerPoolManager)


if __name__ == '__main__':
    unittest.main()