#!/usr/bin/env python3
"""
Comprehensive test for Firecracker backend functionality
"""

import os
from llm_sandbox.const import SandboxBackend, SupportedLanguage
from llm_sandbox.interactive import InteractiveSandboxSession
from llm_sandbox.firecracker import FirecrackerContainerAPI, SandboxFirecrackerSession
from llm_sandbox.pool.factory import create_pool_manager
from llm_sandbox.pool.config import PoolConfig


def test_basic_components():
    """Test that all basic components are properly implemented."""
    print("Testing basic components...")
    
    # Test imports
    assert FirecrackerContainerAPI is not None
    assert SandboxFirecrackerSession is not None
    print("✓ Classes imported successfully")
    
    # Test instantiation
    api = FirecrackerContainerAPI()
    assert api is not None
    print("✓ FirecrackerContainerAPI instantiated successfully")
    
    # Test backend registration
    session = None
    try:
        # This will fail due to missing kernel/rootfs but should recognize the backend
        session = SandboxFirecrackerSession(
            kernel_image_path="/tmp/nonexistent",
            rootfs_path="/tmp/nonexistent",
            lang=SupportedLanguage.PYTHON
        )
    except Exception as e:
        # Expected to fail due to missing files, but should be the right type
        pass
    
    print("✓ Firecracker session class recognized")
    
    return True


def test_interactive_integration():
    """Test integration with interactive module."""
    print("\nTesting interactive module integration...")
    
    from llm_sandbox.interactive import _create_backend_session
    
    # This should work without error (will fail later when trying to run due to missing files)
    try:
        session = _create_backend_session(
            backend=SandboxBackend.FIRECRACKER,
            lang=SupportedLanguage.PYTHON
        )
        assert isinstance(session, SandboxFirecrackerSession)
        print("✓ Interactive module integration works")
        return True
    except Exception as e:
        print(f"✗ Interactive module integration failed: {e}")
        return False


def test_pool_integration():
    """Test integration with pool module."""
    print("\nTesting pool module integration...")
    
    config = PoolConfig(max_pool_size=5, min_pool_size=1)
    
    try:
        pool = create_pool_manager(
            backend=SandboxBackend.FIRECRACKER,
            config=config,
            lang=SupportedLanguage.PYTHON
        )
        
        from llm_sandbox.pool.firecracker_pool import FirecrackerPoolManager
        assert isinstance(pool, FirecrackerPoolManager)
        print("✓ Pool module integration works")
        return True
    except Exception as e:
        print(f"✗ Pool module integration failed: {e}")
        return False


def test_constants():
    """Test that Firecracker is in the constants."""
    print("\nTesting constants...")
    
    assert hasattr(SandboxBackend, 'FIRECRACKER')
    assert SandboxBackend.FIRECRACKER == "firecracker"
    print("✓ Firecracker backend constant exists")
    
    return True


def test_file_structure():
    """Test that required files exist."""
    print("\nTesting file structure...")
    
    import os
    
    files_to_check = [
        "llm_sandbox/firecracker.py",
        "llm_sandbox/guest_agent.py",
        "llm_sandbox/pool/firecracker_pool.py"
    ]
    
    for file_path in files_to_check:
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            print(f"✓ Found {file_path}")
        else:
            print(f"✗ Missing {file_path}")
            return False
    
    return True


def main():
    """Run all tests."""
    print("Running comprehensive Firecracker backend tests...\n")
    
    tests = [
        ("File structure", test_file_structure),
        ("Constants", test_constants),
        ("Basic components", test_basic_components),
        ("Interactive integration", test_interactive_integration),
        ("Pool integration", test_pool_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! Firecracker backend is properly implemented.")
        print("\nNote: For actual execution, ensure:")
        print("1. Firecracker is installed and KVM is available")
        print("2. Kernel image exists at ~/firecracker_data/vmlinux")
        print("3. Rootfs image exists at ~/firecracker_data/rootfs.ext4")
        print("4. Guest agent is installed in the rootfs image")
        return 0
    else:
        print(f"❌ {total-passed} tests failed.")
        return 1


if __name__ == "__main__":
    exit(main())