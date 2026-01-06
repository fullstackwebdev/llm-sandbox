"""
Guest agent for Firecracker VMs in LLM Sandbox.

This agent runs inside the Firecracker VM and handles commands
from the host via VSOCK communication.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time


def handle_command(conn, command_str):
    """Handle a command received from the host."""
    try:
        command_data = json.loads(command_str)
        
        if "command" in command_data:
            cmd = command_data["command"]
            
            # Handle different types of commands
            if isinstance(cmd, str):
                # Regular command execution
                result = execute_command(cmd)
            elif isinstance(cmd, dict) and cmd.get("command") == "copy_file":
                # File copy command
                result = handle_copy_file(cmd)
            elif isinstance(cmd, dict) and cmd.get("command") == "read_file":
                # File read command
                result = handle_read_file(cmd)
            else:
                result = {
                    "status": "error",
                    "error": f"Unknown command format: {cmd}"
                }
        else:
            result = {
                "status": "error",
                "error": "No command provided in request"
            }
        
        # Send result back to host
        response = json.dumps(result).encode()
        conn.send(response)
        
    except json.JSONDecodeError:
        error_response = json.dumps({
            "status": "error",
            "error": "Invalid JSON in command"
        }).encode()
        conn.send(error_response)
    except Exception as e:
        error_response = json.dumps({
            "status": "error", 
            "error": f"Error handling command: {str(e)}"
        }).encode()
        conn.send(error_response)


def execute_command(cmd):
    """Execute a shell command and return the result."""
    try:
        # Use shell=True to allow command chaining (&&, ||, etc.)
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout for safety
        )
        
        return {
            "status": "success",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "exit_code": 124,  # Standard timeout exit code
            "stdout": "",
            "stderr": "Command timed out"
        }
    except Exception as e:
        return {
            "status": "error",
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Command execution failed: {str(e)}"
        }


def handle_copy_file(data):
    """Handle file copy command."""
    try:
        destination = data.get("destination")
        content_hex = data.get("content")
        
        if not destination or not content_hex:
            return {
                "status": "error",
                "error": "Missing destination or content in copy_file command"
            }
        
        # Decode the hex content back to binary
        content = bytes.fromhex(content_hex)
        
        # Create directory if it doesn't exist
        dest_dir = os.path.dirname(destination)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        
        # Write the file
        with open(destination, 'wb') as f:
            f.write(content)
        
        return {
            "status": "success",
            "message": f"File copied to {destination}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"File copy failed: {str(e)}"
        }


def handle_read_file(data):
    """Handle file read command."""
    try:
        source = data.get("source")
        
        if not source:
            return {
                "status": "error",
                "error": "Missing source in read_file command"
            }
        
        # Read the file
        with open(source, 'rb') as f:
            content = f.read()
        
        return {
            "status": "success",
            "content": content.hex()  # Encode binary as hex
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"File not found: {source}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"File read failed: {str(e)}"
        }


def main():
    """Main function to start the guest agent."""
    # Use VSOCK CID 3 (standard for communication with host)
    guest_cid = 3
    
    # Create VSOCK socket
    sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    
    try:
        # Bind to any port on the guest CID
        sock.bind((guest_cid, 0))
        sock.listen(1)
        print(f"Guest agent listening on CID {guest_cid}")
        
        while True:
            # Accept connections
            conn, addr = sock.accept()
            print(f"Connection from {addr}")
            
            try:
                # Receive handshake
                handshake = conn.recv(1024).decode().strip()
                if handshake.startswith("CONNECT"):
                    conn.send(b"OK\n")
                    
                    # Receive command
                    command_data = conn.recv(65536).decode()
                    if command_data:
                        handle_command(conn, command_data)
                else:
                    conn.send(b"ERROR: Invalid handshake\n")
            except Exception as e:
                print(f"Error handling connection: {e}")
            finally:
                conn.close()
                
    except KeyboardInterrupt:
        print("Shutting down guest agent...")
    except Exception as e:
        print(f"Guest agent error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()