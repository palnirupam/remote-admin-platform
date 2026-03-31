"""
Enhanced Server Module for Remote System Enhancement

This module provides the core server functionality with TLS encryption,
JWT authentication, agent registry, heartbeat mechanism, and multi-agent management.

Requirements: 1.1, 16.1, 16.2, 16.4, 19.1, 19.2, 19.3, 19.4, 19.5
"""

import socket
import threading
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import ssl

from remote_system.enhanced_server.tls_wrapper import TLSServerWrapper
from remote_system.enhanced_server.auth_module import AuthenticationModule
from remote_system.enhanced_server.database_manager import DatabaseManager
from remote_system.enhanced_server.legacy_handler import LegacyHandler
from remote_system.enhanced_server.cache_manager import CacheManager
from remote_system.enhanced_server.compression_utils import CompressionUtils
from remote_system.enhanced_server.resource_limiter import ResourceLimiter


class AgentConnection:
    """
    Represents an active agent connection
    
    Attributes:
        agent_id: Unique agent identifier
        connection: TLS socket connection
        address: Client address tuple (ip, port)
        last_heartbeat: Timestamp of last heartbeat response
        agent_info: Agent information dictionary
    """
    
    def __init__(self, agent_id: str, connection: ssl.SSLSocket, 
                 address: Tuple[str, int], agent_info: Dict[str, Any]):
        self.agent_id = agent_id
        self.connection = connection
        self.address = address
        self.last_heartbeat = time.time()
        self.agent_info = agent_info
        self.lock = threading.Lock()


class EnhancedServer:
    """
    Enhanced Server for Remote System Management
    
    Provides TLS-encrypted connections, JWT authentication, agent registry,
    heartbeat monitoring, and multi-agent command broadcasting.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 9999, 
                 db_path: str = "./remote_system.db", use_tls: bool = True,
                 secret_key: str = "default_secret_key_change_in_production",
                 legacy_mode: bool = True):
        """
        Initialize enhanced server
        
        Args:
            host: Host address to bind to
            port: Port number to listen on
            db_path: Path to database file
            use_tls: Whether to use TLS encryption
            secret_key: Secret key for JWT authentication
            legacy_mode: Whether to enable legacy agent support
        
        Requirements: 1.1, 16.1, 25.1, 25.6, 25.7
        """
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.secret_key = secret_key
        
        # Initialize components
        self.db_manager = DatabaseManager(db_path)
        self.auth_module = AuthenticationModule(secret_key)
        self.legacy_handler = LegacyHandler(enabled=legacy_mode, db_manager=self.db_manager)
        self.cache_manager = CacheManager()
        self.resource_limiter = ResourceLimiter()
        self.compression_utils = CompressionUtils()
        
        if use_tls:
            self.tls_wrapper = TLSServerWrapper(
                cert_path="server.crt",
                key_path="server.key",
                auto_generate=True,
                common_name=host if host != "0.0.0.0" else "localhost"
            )
        else:
            self.tls_wrapper = None
        
        # Server state
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.active_agents: Dict[str, AgentConnection] = {}
        self.agents_lock = threading.Lock()
        
        # Start cache cleanup thread
        self.cache_cleanup_thread = threading.Thread(target=self._cache_cleanup_loop, daemon=True)
        self.cache_cleanup_thread.start()
    
    def start(self) -> None:
        """
        Start the enhanced server
        
        Binds to the configured host and port, then accepts connections
        in a loop. Each connection is handled in a separate thread.
        
        Requirements: 16.1, 16.2
        """
        if self.running:
            print("[WARNING] Server is already running")
            return
        
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            
            tls_status = "with TLS" if self.use_tls else "without TLS"
            print(f"[STARTED] Enhanced Server listening on {self.host}:{self.port} {tls_status}")
            
            # Accept connections loop
            while self.running:
                try:
                    # Accept new connection
                    conn, addr = self.server_socket.accept()
                    print(f"[CONNECTION] New connection from {addr}")
                    
                    # Handle connection in separate thread
                    handler_thread = threading.Thread(
                        target=self._handle_agent_connection,
                        args=(conn, addr),
                        daemon=True
                    )
                    handler_thread.start()
                
                except OSError as e:
                    if self.running:
                        print(f"[ERROR] Socket error: {e}")
                    break
                except Exception as e:
                    print(f"[ERROR] Unexpected error accepting connection: {e}")
        
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}")
            self.running = False
        
        finally:
            if self.server_socket:
                self.server_socket.close()
            print("[STOPPED] Server has stopped")
    
    def stop(self) -> None:
        """
        Stop the enhanced server
        
        Closes all active connections and shuts down the server socket.
        """
        print("[STOPPING] Shutting down server...")
        self.running = False
        
        # Close all agent connections
        with self.agents_lock:
            for agent_id, agent_conn in list(self.active_agents.items()):
                try:
                    agent_conn.connection.close()
                except Exception:
                    pass
            self.active_agents.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
    
    def _cache_cleanup_loop(self) -> None:
        """
        Background thread to periodically clean expired cache entries
        
        Requirements: 23.3, 23.4, 23.5
        """
        while True:
            time.sleep(60)  # Run every minute
            try:
                self.cache_manager.clear_expired_entries()
            except Exception as e:
                print(f"[ERROR] Cache cleanup error: {e}")
    
    def _handle_agent_connection(self, conn: socket.socket, addr: Tuple[str, int]) -> None:
        """
        Handle agent connection following the design algorithm
        
        Implements the complete connection flow:
        1. Detect legacy vs enhanced agent
        2. Route to appropriate handler
        3. For enhanced agents:
           - TLS handshake
           - Authentication
           - Agent registration
           - Command loop with heartbeat
           - Cleanup on disconnect
        
        Args:
            conn: Socket connection
            addr: Client address tuple
        
        Requirements: 1.1, 16.1, 16.2, 19.1, 19.2, 19.3, 19.4, 19.5, 25.1, 25.2, 25.3
        """
        # Step 0: Detect legacy vs enhanced agent
        if self.legacy_handler.is_legacy_connection(conn):
            print(f"[LEGACY] Detected legacy agent connection from {addr}")
            self.legacy_handler.handle_legacy_agent(conn, addr)
            return
        
        # Continue with enhanced agent handling
        tls_conn = None
        agent_id = None
        
        try:
            # Step 1: TLS Handshake
            if self.use_tls:
                try:
                    tls_conn = self.tls_wrapper.wrap_socket(conn)
                    print(f"[TLS] Secure connection established with {addr}")
                except Exception as e:
                    print(f"[ERROR] TLS handshake failed with {addr}: {e}")
                    conn.close()
                    return
            else:
                tls_conn = conn
            
            # Step 2: Authentication
            try:
                # Request authentication
                self._send_message(tls_conn, {"type": "AUTH_REQUEST"})
                
                # Receive authentication response (30 second timeout)
                tls_conn.settimeout(30)
                auth_response = self._receive_message(tls_conn)
                
                if not auth_response or auth_response.get("type") != "AUTH_RESPONSE":
                    print(f"[AUTH] Invalid authentication response from {addr}")
                    self._send_message(tls_conn, {"type": "AUTH_FAILED", "error": "Invalid response"})
                    tls_conn.close()
                    return
                
                # Validate token
                token = auth_response.get("token", "")
                validation = self.auth_module.validate_token(token)
                
                if not validation.valid:
                    print(f"[AUTH] Authentication failed for {addr}: {validation.error}")
                    self._send_message(tls_conn, {"type": "AUTH_FAILED", "error": validation.error})
                    tls_conn.close()
                    return
                
                # Extract agent info
                agent_info = auth_response.get("agent_info", {})
                agent_info["ip_address"] = addr[0]
                
                # Validate required fields
                required_fields = ["hostname", "username", "os_type", "os_version", "mac_address"]
                for field in required_fields:
                    if field not in agent_info:
                        print(f"[AUTH] Missing required field: {field}")
                        self._send_message(tls_conn, {"type": "AUTH_FAILED", "error": f"Missing field: {field}"})
                        tls_conn.close()
                        return
                
                # Step 3: Register Agent
                agent_id = self._register_agent(tls_conn, addr, agent_info)
                
                # Send authentication success
                self._send_message(tls_conn, {"type": "AUTH_SUCCESS", "agent_id": agent_id})
                print(f"[AUTH] Agent {agent_id} authenticated successfully")
            
            except socket.timeout:
                print(f"[ERROR] Authentication timeout for {addr}")
                try:
                    self._send_message(tls_conn, {"type": "AUTH_FAILED", "error": "Timeout"})
                except Exception:
                    pass
                tls_conn.close()
                return
            except Exception as e:
                print(f"[ERROR] Authentication error for {addr}: {e}")
                try:
                    self._send_message(tls_conn, {"type": "AUTH_FAILED", "error": str(e)})
                except Exception:
                    pass
                tls_conn.close()
                return
            
            # Step 4: Command Loop with Heartbeat
            tls_conn.settimeout(1.0)  # 1 second timeout for non-blocking receive
            last_heartbeat = time.time()
            
            while self.running:
                try:
                    # Check for pending commands
                    command = self._get_next_command(agent_id)
                    
                    if command:
                        # Send command to agent
                        start_time = time.time()
                        log_id = self.db_manager.log_command(
                            agent_id=agent_id,
                            command=json.dumps(command),
                            status="pending"
                        )
                        
                        self._send_message(tls_conn, {"type": "COMMAND", "data": command})
                        
                        # Wait for result (5 minute timeout)
                        tls_conn.settimeout(300)
                        try:
                            result_msg = self._receive_message(tls_conn)
                            end_time = time.time()
                            
                            if result_msg and result_msg.get("type") == "COMMAND_RESULT":
                                result = result_msg.get("result", "")
                                
                                # Compress result if large
                                compressed_result = self.compression_utils.compress_command_result(result)
                                result_to_store = json.dumps(compressed_result)
                                
                                self.db_manager.update_command_log(
                                    log_id=log_id,
                                    result=result_to_store,
                                    status="success",
                                    execution_time=end_time - start_time
                                )
                            else:
                                self.db_manager.update_command_log(
                                    log_id=log_id,
                                    result="Invalid result format",
                                    status="error",
                                    execution_time=end_time - start_time
                                )
                        except socket.timeout:
                            self.db_manager.update_command_log(
                                log_id=log_id,
                                result="Command execution timeout",
                                status="timeout",
                                execution_time=300
                            )
                        
                        tls_conn.settimeout(1.0)  # Reset to 1 second
                    
                    # Heartbeat mechanism (60 second intervals)
                    current_time = time.time()
                    if current_time - last_heartbeat > 60:
                        # Send heartbeat
                        self._send_message(tls_conn, {"type": "HEARTBEAT"})
                        
                        # Wait for heartbeat response (10 second timeout)
                        tls_conn.settimeout(10)
                        try:
                            heartbeat_response = self._receive_message(tls_conn)
                            
                            if heartbeat_response and heartbeat_response.get("type") == "HEARTBEAT_ACK":
                                last_heartbeat = current_time
                                self.db_manager.update_agent_status(agent_id, "online")
                            else:
                                print(f"[HEARTBEAT] Invalid response from agent {agent_id}")
                                break  # Connection lost
                        except socket.timeout:
                            print(f"[HEARTBEAT] No response from agent {agent_id}")
                            break  # Connection lost
                        
                        tls_conn.settimeout(1.0)  # Reset to 1 second
                
                except socket.timeout:
                    # Normal timeout, continue loop
                    continue
                except Exception as e:
                    print(f"[ERROR] Error in command loop for agent {agent_id}: {e}")
                    break
        
        except Exception as e:
            print(f"[ERROR] Unexpected error handling connection from {addr}: {e}")
        
        finally:
            # Step 5: Cleanup
            if agent_id:
                self._unregister_agent(agent_id)
            
            if tls_conn:
                try:
                    tls_conn.close()
                except Exception:
                    pass
            
            print(f"[DISCONNECTED] Connection closed for {addr}")
    
    def _register_agent(self, connection: ssl.SSLSocket, address: Tuple[str, int],
                       agent_info: Dict[str, Any]) -> str:
        """
        Register a new agent connection
        
        Args:
            connection: TLS socket connection
            address: Client address tuple
            agent_info: Agent information dictionary
        
        Returns:
            agent_id: Unique agent identifier
        
        Requirements: 16.1, 19.1, 23.3
        """
        # Generate agent_id from hostname and timestamp
        import uuid
        agent_id = str(uuid.uuid4())
        
        # Add default fields
        if "capabilities" not in agent_info:
            agent_info["capabilities"] = []
        if "metadata" not in agent_info:
            agent_info["metadata"] = {}
        
        # Create agent connection object
        agent_conn = AgentConnection(agent_id, connection, address, agent_info)
        
        # Add to active agents
        with self.agents_lock:
            self.active_agents[agent_id] = agent_conn
        
        # Log connection to database
        try:
            self.db_manager.log_connection(agent_id, agent_info)
        except Exception as e:
            print(f"[ERROR] Failed to log connection for agent {agent_id}: {e}")
        
        # Invalidate agent list cache
        self.cache_manager.invalidate_agent_list()
        
        return agent_id
    
    def _unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent and cleanup resources
        
        Args:
            agent_id: Agent identifier to unregister
        
        Requirements: 16.4, 19.4, 23.3, 23.7
        """
        # Remove from active agents
        with self.agents_lock:
            if agent_id in self.active_agents:
                del self.active_agents[agent_id]
        
        # Cleanup resource limiter
        self.resource_limiter.cleanup_agent(agent_id)
        
        # Update database status
        try:
            self.db_manager.update_agent_status(agent_id, "offline")
        except Exception as e:
            print(f"[ERROR] Failed to update status for agent {agent_id}: {e}")
        
        # Invalidate agent list cache
        self.cache_manager.invalidate_agent_list()
    
    def broadcast_command(self, command: Dict[str, Any], 
                         agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Broadcast command to multiple agents (both enhanced and legacy)
        
        Args:
            command: Command dictionary to send
            agent_ids: List of agent IDs to send to (None = all agents)
        
        Returns:
            Dictionary mapping agent_id to status
        
        Requirements: 16.2, 23.7, 25.2, 25.3
        """
        results = {}
        
        with self.agents_lock:
            # Determine target agents
            if agent_ids is None:
                target_agents = list(self.active_agents.keys())
            else:
                target_agents = [aid for aid in agent_ids if aid in self.active_agents]
            
            # Queue command for each target enhanced agent with resource limits
            for agent_id in target_agents:
                if self.resource_limiter.can_queue_command(agent_id):
                    if self.resource_limiter.queue_command(agent_id, command):
                        results[agent_id] = "queued"
                    else:
                        results[agent_id] = "queue_full"
                else:
                    results[agent_id] = "queue_full"
        
        # Handle legacy agents
        if agent_ids is None:
            # Broadcast to all legacy agents
            legacy_agents = self.legacy_handler.get_legacy_agents()
            for legacy_agent in legacy_agents:
                agent_id = legacy_agent["agent_id"]
                # Convert command dict to simple string for legacy agents
                command_str = command.get("command", str(command))
                if self.legacy_handler.send_command_to_legacy_agent(agent_id, command_str):
                    results[agent_id] = "queued"
                else:
                    results[agent_id] = "not_found"
        else:
            # Send to specific legacy agents if in list
            for agent_id in agent_ids:
                if agent_id.startswith("legacy_"):
                    command_str = command.get("command", str(command))
                    if self.legacy_handler.send_command_to_legacy_agent(agent_id, command_str):
                        results[agent_id] = "queued"
                    else:
                        results[agent_id] = "not_found"
        
        return results
    
    def get_active_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of all active agents (both enhanced and legacy)
        
        Returns:
            List of agent information dictionaries
        
        Requirements: 16.1, 23.3, 25.3
        """
        try:
            # Check cache first
            cached_agents = self.cache_manager.get_agent_list()
            if cached_agents is not None:
                return cached_agents
            
            # Get enhanced agents from database
            enhanced_agents = self.db_manager.get_active_agents()
            
            # Get legacy agents
            legacy_agents = self.legacy_handler.get_legacy_agents()
            
            # Combine both lists
            all_agents = enhanced_agents + legacy_agents
            
            # Cache the result
            self.cache_manager.set_agent_list(all_agents)
            
            return all_agents
        except Exception as e:
            print(f"[ERROR] Failed to get active agents: {e}")
            return []
    
    def _get_next_command(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get next pending command for an agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Command dictionary or None if no commands pending
        
        Requirements: 23.7
        """
        return self.resource_limiter.dequeue_command(agent_id)
    
    def _send_message(self, connection: ssl.SSLSocket, message: Dict[str, Any]) -> None:
        """
        Send JSON message over connection
        
        Args:
            connection: Socket connection
            message: Message dictionary to send
        """
        try:
            data = json.dumps(message).encode('utf-8')
            # Send length prefix (4 bytes) followed by data
            length = len(data)
            connection.sendall(length.to_bytes(4, byteorder='big'))
            connection.sendall(data)
        except Exception as e:
            raise Exception(f"Failed to send message: {e}")
    
    def _receive_message(self, connection: ssl.SSLSocket) -> Optional[Dict[str, Any]]:
        """
        Receive JSON message from connection
        
        Args:
            connection: Socket connection
        
        Returns:
            Message dictionary or None if connection closed
        """
        try:
            # Receive length prefix (4 bytes)
            length_bytes = self._recv_exact(connection, 4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive message data
            data = self._recv_exact(connection, length)
            if not data:
                return None
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"[ERROR] Failed to receive message: {e}")
            return None
    
    def _recv_exact(self, connection: ssl.SSLSocket, num_bytes: int) -> Optional[bytes]:
        """
        Receive exact number of bytes from connection
        
        Args:
            connection: Socket connection
            num_bytes: Number of bytes to receive
        
        Returns:
            Bytes received or None if connection closed
        """
        data = b''
        while len(data) < num_bytes:
            chunk = connection.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data


if __name__ == "__main__":
    # Example usage
    server = EnhancedServer(
        host="0.0.0.0",
        port=9999,
        db_path="./remote_system.db",
        use_tls=True,
        secret_key="change_this_secret_key_in_production"
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Received keyboard interrupt")
        server.stop()
