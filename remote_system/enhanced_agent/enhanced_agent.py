"""
Enhanced Agent Module for Remote System Enhancement

This module provides the core agent functionality with TLS encryption,
JWT authentication, plugin-based command execution, heartbeat mechanism,
automatic reconnection, and result buffering.

Requirements: 4.1, 4.2, 14.6, 19.2, 20.5, 20.6
"""

import socket
import time
import json
import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import ssl
from urllib.parse import urlparse

from remote_system.enhanced_agent.tls_wrapper import TLSAgentWrapper
from remote_system.enhanced_agent.plugin_manager import PluginManager


class EnhancedAgent:
    """
    Enhanced Agent for Remote System Management
    
    Provides TLS-encrypted connections, JWT authentication, plugin-based
    command execution, heartbeat response, automatic reconnection with
    exponential backoff, and result buffering for offline operations.
    """
    
    def __init__(self, server_address: str, token: str,
                 use_tls: bool = True, plugin_dir: str = "./plugins",
                 expected_fingerprint: Optional[str] = None):
        """
        Initialize enhanced agent
        
        Args:
            server_address: Server address in various formats:
                          - IP:PORT (e.g., "192.168.1.100:9999")
                          - Domain:PORT (e.g., "myserver.ddns.net:9999")
                          - Ngrok URL (e.g., "https://abc123.ngrok.io")
                          - HTTP/HTTPS URL with port (e.g., "https://example.com:9999")
            token: JWT authentication token
            use_tls: Whether to use TLS encryption
            plugin_dir: Directory containing plugins
            expected_fingerprint: Expected server certificate fingerprint for pinning
        
        Requirements: 4.1, 4.2, 14.2, 14.3, 14.4, 14.5, 14.6
        """
        if not server_address:
            raise ValueError("Server address cannot be empty")
        if not token:
            raise ValueError("Token cannot be empty")
        
        # Parse server address to extract host and port
        self.server_ip, self.server_port = self._parse_server_address(server_address)
        self.server_address = server_address  # Keep original for reference
        self.token = token
        self.use_tls = use_tls
        self.plugin_dir = plugin_dir
        self.expected_fingerprint = expected_fingerprint
        
        # Initialize plugin manager
        self.plugin_manager = PluginManager(plugin_dir)
        self.plugin_manager.load_plugins()
        
        # Connection state
        self.connection: Optional[ssl.SSLSocket] = None
        self.tls_wrapper: Optional[TLSAgentWrapper] = None
        self.connected = False
        self.running = False
        self.agent_id: Optional[str] = None
        
        # Result buffering for offline operations
        self.result_buffer: List[Dict[str, Any]] = []
        self.buffer_lock = threading.Lock()
        
        # Reconnection state
        self.reconnect_delay = 5  # Start with 5 seconds
        self.max_reconnect_delay = 60  # Maximum 60 seconds
    
    def _parse_server_address(self, address: str) -> Tuple[str, int]:
        """
        Parse server address in various formats and extract host and port
        
        Supports:
        - IP:PORT (e.g., "192.168.1.100:9999")
        - Domain:PORT (e.g., "myserver.ddns.net:9999")
        - Ngrok URL (e.g., "https://abc123.ngrok.io")
        - HTTP/HTTPS URL with port (e.g., "https://example.com:9999")
        
        Args:
            address: Server address in any supported format
        
        Returns:
            Tuple of (host, port)
        
        Raises:
            ValueError: If address format is invalid
        
        Requirements: 14.2, 14.3, 14.4, 14.5
        """
        # Try parsing as URL first (handles Ngrok, HTTPS, HTTP)
        if address.startswith(('http://', 'https://')):
            try:
                parsed = urlparse(address)
                host = parsed.hostname
                port = parsed.port
                
                if not host:
                    raise ValueError(f"Invalid URL: no hostname found in {address}")
                
                # Default ports for HTTP/HTTPS
                if port is None:
                    if parsed.scheme == 'https':
                        port = 443
                    elif parsed.scheme == 'http':
                        port = 80
                    else:
                        raise ValueError(f"Unknown scheme: {parsed.scheme}")
                
                print(f"[AGENT] Parsed URL: {address} -> {host}:{port}")
                return host, port
            except Exception as e:
                raise ValueError(f"Invalid URL format: {address}. Error: {e}")
        
        # Try parsing as IP:PORT or Domain:PORT
        if ':' in address:
            parts = address.rsplit(':', 1)  # Split from right to handle IPv6
            if len(parts) == 2:
                host, port_str = parts
                try:
                    port = int(port_str)
                    if port <= 0 or port > 65535:
                        raise ValueError(f"Port must be between 1 and 65535, got {port}")
                    
                    # Validate host (IP or domain)
                    if not host:
                        raise ValueError("Host cannot be empty")
                    
                    print(f"[AGENT] Parsed address: {address} -> {host}:{port}")
                    return host, port
                except ValueError as e:
                    raise ValueError(f"Invalid port in address {address}: {e}")
        
        # If no format matches, raise error
        raise ValueError(
            f"Invalid server address format: {address}. "
            "Supported formats: IP:PORT, Domain:PORT, https://domain, https://domain:port"
        )
    
    def connect(self) -> bool:
        """
        Connect to server with TLS handshake and authentication
        
        Implements the connection flow:
        1. Establish TLS connection (if enabled)
        2. Receive authentication request
        3. Send authentication response with token and system info
        4. Receive authentication result
        
        Returns:
            True if connection and authentication successful, False otherwise
        
        Requirements: 4.1, 4.2, 14.6
        """
        try:
            # Step 1: Establish connection
            if self.use_tls:
                self.tls_wrapper = TLSAgentWrapper(
                    server_ip=self.server_ip,
                    server_port=self.server_port,
                    expected_fingerprint=self.expected_fingerprint,
                    verify_cert=False,  # Use self-signed certificates
                    timeout=30
                )
                self.connection = self.tls_wrapper.connect()
                print(f"[TLS] Secure connection established to {self.server_ip}:{self.server_port}")
            else:
                # Plain socket connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)
                sock.connect((self.server_ip, self.server_port))
                self.connection = sock
                print(f"[CONNECTED] Connected to {self.server_ip}:{self.server_port}")
            
            # Step 2: Receive authentication request
            self.connection.settimeout(30)
            auth_request = self._receive_message()
            
            if not auth_request or auth_request.get("type") != "AUTH_REQUEST":
                print("[ERROR] Invalid authentication request from server")
                self._disconnect()
                return False
            
            # Step 3: Send authentication response
            agent_info = self._collect_system_info()
            auth_response = {
                "type": "AUTH_RESPONSE",
                "token": self.token,
                "agent_info": agent_info
            }
            self._send_message(auth_response)
            
            # Step 4: Receive authentication result
            auth_result = self._receive_message()
            
            if not auth_result:
                print("[ERROR] No authentication response from server")
                self._disconnect()
                return False
            
            if auth_result.get("type") == "AUTH_SUCCESS":
                self.agent_id = auth_result.get("agent_id")
                self.connected = True
                print(f"[AUTH] Authentication successful, agent_id: {self.agent_id}")
                
                # Send any buffered results
                self._send_buffered_results()
                
                return True
            else:
                error = auth_result.get("error", "Unknown error")
                print(f"[AUTH] Authentication failed: {error}")
                self._disconnect()
                return False
        
        except socket.timeout:
            print("[ERROR] Connection timeout")
            self._disconnect()
            return False
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            self._disconnect()
            return False
    
    def _disconnect(self) -> None:
        """
        Disconnect from server and cleanup resources
        """
        self.connected = False
        
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
        
        if self.tls_wrapper:
            try:
                self.tls_wrapper.disconnect()
            except Exception:
                pass
            self.tls_wrapper = None
    
    def agent_loop(self) -> None:
        """
        Main agent loop to receive and execute commands
        
        Implements the command loop:
        1. Connect to server (with reconnection logic)
        2. Receive commands or heartbeat messages
        3. Execute commands via plugin manager
        4. Send results back to server
        5. Respond to heartbeat messages
        6. Handle disconnections with exponential backoff
        
        Requirements: 4.1, 14.6, 19.2, 20.5, 20.6
        """
        self.running = True
        
        while self.running:
            # Connect to server with reconnection logic
            if not self.connected:
                if not self._reconnect():
                    continue
            
            try:
                # Set timeout for non-blocking receive
                self.connection.settimeout(1.0)
                
                # Receive message from server
                message = self._receive_message()
                
                if not message:
                    # Connection closed
                    print("[DISCONNECTED] Connection closed by server")
                    self.connected = False
                    continue
                
                message_type = message.get("type")
                
                if message_type == "COMMAND":
                    # Execute command via plugin manager
                    self._handle_command(message.get("data", {}))
                
                elif message_type == "HEARTBEAT":
                    # Respond to heartbeat
                    self._handle_heartbeat()
                
                else:
                    print(f"[WARNING] Unknown message type: {message_type}")
            
            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                print(f"[ERROR] Error in agent loop: {e}")
                self.connected = False
        
        # Cleanup on exit
        self._disconnect()
        print("[STOPPED] Agent has stopped")
    
    def stop(self) -> None:
        """
        Stop the agent loop
        """
        print("[STOPPING] Stopping agent...")
        self.running = False
    
    def _reconnect(self) -> bool:
        """
        Reconnect to server with exponential backoff
        
        Implements exponential backoff: 5s, 10s, 20s, 40s, 60s max
        
        Returns:
            True if reconnection successful, False otherwise
        
        Requirements: 20.5, 20.6
        """
        print(f"[RECONNECT] Attempting to reconnect in {self.reconnect_delay} seconds...")
        time.sleep(self.reconnect_delay)
        
        if self.connect():
            # Reset reconnection delay on successful connection
            self.reconnect_delay = 5
            return True
        else:
            # Increase reconnection delay with exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            return False
    
    def _handle_command(self, command: Dict[str, Any]) -> None:
        """
        Handle command execution via plugin manager
        
        Args:
            command: Command dictionary with plugin name and arguments
        
        Requirements: 4.1, 20.7
        """
        try:
            plugin_name = command.get("plugin")
            args = command.get("args", {})
            
            if not plugin_name:
                result = {
                    "success": False,
                    "error": "No plugin specified"
                }
            else:
                # Execute plugin
                plugin_result = self.plugin_manager.execute_plugin(plugin_name, args)
                
                # Convert PluginResult to dictionary
                result = {
                    "success": plugin_result.success,
                    "data": plugin_result.data,
                    "error": plugin_result.error,
                    "metadata": plugin_result.metadata
                }
            
            # Send result back to server
            result_message = {
                "type": "COMMAND_RESULT",
                "result": result
            }
            
            if self.connected:
                self._send_message(result_message)
            else:
                # Buffer result if offline
                self._buffer_result(result_message)
        
        except Exception as e:
            print(f"[ERROR] Error handling command: {e}")
            
            # Send error result
            error_result = {
                "type": "COMMAND_RESULT",
                "result": {
                    "success": False,
                    "error": f"Command execution error: {str(e)}"
                }
            }
            
            if self.connected:
                try:
                    self._send_message(error_result)
                except Exception:
                    self._buffer_result(error_result)
            else:
                self._buffer_result(error_result)
    
    def _handle_heartbeat(self) -> None:
        """
        Handle heartbeat message from server
        
        Responds with HEARTBEAT_ACK to indicate agent is alive
        
        Requirements: 19.2
        """
        try:
            heartbeat_ack = {"type": "HEARTBEAT_ACK"}
            self._send_message(heartbeat_ack)
        except Exception as e:
            print(f"[ERROR] Failed to send heartbeat acknowledgment: {e}")
            self.connected = False
    
    def _buffer_result(self, result: Dict[str, Any]) -> None:
        """
        Buffer result for later delivery when connection is restored
        
        Args:
            result: Result message to buffer
        
        Requirements: 20.7
        """
        with self.buffer_lock:
            self.result_buffer.append(result)
            print(f"[BUFFER] Result buffered (buffer size: {len(self.result_buffer)})")
    
    def _send_buffered_results(self) -> None:
        """
        Send all buffered results to server
        
        Called after successful reconnection to deliver offline results
        
        Requirements: 20.7
        """
        with self.buffer_lock:
            if not self.result_buffer:
                return
            
            print(f"[BUFFER] Sending {len(self.result_buffer)} buffered results...")
            
            for result in self.result_buffer:
                try:
                    self._send_message(result)
                except Exception as e:
                    print(f"[ERROR] Failed to send buffered result: {e}")
                    # Keep remaining results in buffer
                    break
            else:
                # All results sent successfully, clear buffer
                self.result_buffer.clear()
                print("[BUFFER] All buffered results sent successfully")
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """
        Collect system information for agent registration
        
        Returns:
            Dictionary with system information
        
        Requirements: 4.1
        """
        import platform
        import socket as sock_module
        import uuid
        
        try:
            hostname = platform.node()
        except Exception:
            hostname = "unknown"
        
        try:
            username = platform.system()  # Simplified for now
        except Exception:
            username = "unknown"
        
        try:
            os_type = platform.system()
        except Exception:
            os_type = "unknown"
        
        try:
            os_version = platform.release()
        except Exception:
            os_version = "unknown"
        
        try:
            mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                                   for elements in range(0, 2*6, 2)][::-1])
        except Exception:
            mac_address = "00:00:00:00:00:00"
        
        # Get list of loaded plugins
        capabilities = self.plugin_manager.list_plugins()
        
        return {
            "hostname": hostname,
            "username": username,
            "os_type": os_type,
            "os_version": os_version,
            "mac_address": mac_address,
            "capabilities": capabilities,
            "metadata": {}
        }
    
    def _send_message(self, message: Dict[str, Any]) -> None:
        """
        Send JSON message over connection
        
        Args:
            message: Message dictionary to send
        
        Raises:
            Exception: If send fails
        """
        if not self.connection:
            raise Exception("Not connected to server")
        
        try:
            data = json.dumps(message).encode('utf-8')
            # Send length prefix (4 bytes) followed by data
            length = len(data)
            self.connection.sendall(length.to_bytes(4, byteorder='big'))
            self.connection.sendall(data)
        except Exception as e:
            raise Exception(f"Failed to send message: {e}")
    
    def _receive_message(self) -> Optional[Dict[str, Any]]:
        """
        Receive JSON message from connection
        
        Returns:
            Message dictionary or None if connection closed
        """
        if not self.connection:
            return None
        
        try:
            # Receive length prefix (4 bytes)
            length_bytes = self._recv_exact(4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive message data
            data = self._recv_exact(length)
            if not data:
                return None
            
            return json.loads(data.decode('utf-8'))
        except socket.timeout:
            raise  # Re-raise timeout for caller to handle
        except Exception as e:
            print(f"[ERROR] Failed to receive message: {e}")
            return None
    
    def _recv_exact(self, num_bytes: int) -> Optional[bytes]:
        """
        Receive exact number of bytes from connection
        
        Args:
            num_bytes: Number of bytes to receive
        
        Returns:
            Bytes received or None if connection closed
        """
        if not self.connection:
            return None
        
        data = b''
        while len(data) < num_bytes:
            chunk = self.connection.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data


if __name__ == "__main__":
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Enhanced Agent for Remote System Management")
    parser.add_argument("--server", required=True, 
                       help="Server address (IP:PORT, Domain:PORT, https://ngrok-url, or https://domain:port)")
    parser.add_argument("--token", required=True, help="JWT authentication token")
    parser.add_argument("--no-tls", action="store_true", help="Disable TLS encryption")
    parser.add_argument("--plugins", default="./plugins", help="Plugin directory path")
    parser.add_argument("--fingerprint", help="Expected server certificate fingerprint")
    
    args = parser.parse_args()
    
    # Create and start agent
    agent = EnhancedAgent(
        server_address=args.server,
        token=args.token,
        use_tls=not args.no_tls,
        plugin_dir=args.plugins,
        expected_fingerprint=args.fingerprint
    )
    
    try:
        agent.agent_loop()
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Received keyboard interrupt")
        agent.stop()
