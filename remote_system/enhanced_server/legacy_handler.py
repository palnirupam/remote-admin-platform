"""
Legacy Handler Module for Backward Compatibility

This module provides backward compatibility with the legacy agent system,
allowing old agents to connect to the enhanced server without authentication.

Requirements: 25.1, 25.2, 25.3, 25.4, 25.5, 25.6, 25.7
"""

import socket
import threading
import time
import json
import os
import sqlite3
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime


class LegacyAgentConnection:
    """
    Represents a legacy agent connection
    
    Attributes:
        connection: Socket connection
        address: Client address tuple (ip, port)
        agent_info: Agent information string
        connected_at: Connection timestamp
    """
    
    def __init__(self, connection: socket.socket, address: Tuple[str, int]):
        self.connection = connection
        self.address = address
        self.agent_info = ""
        self.connected_at = time.time()
        self.lock = threading.Lock()


class LegacyHandler:
    """
    Handler for legacy agent connections
    
    Provides backward compatibility by:
    - Detecting legacy vs enhanced agent connections
    - Handling legacy agents with simple text-based protocol
    - Providing basic command execution without authentication
    - Supporting simultaneous legacy and enhanced agent connections
    """
    
    def __init__(self, enabled: bool = True, db_manager=None):
        """
        Initialize legacy handler
        
        Args:
            enabled: Whether legacy mode is enabled
            db_manager: Database manager instance for logging
        
        Requirements: 25.1, 25.6, 25.7
        """
        self.enabled = enabled
        self.db_manager = db_manager
        self.legacy_agents: Dict[str, LegacyAgentConnection] = {}
        self.agents_lock = threading.Lock()
        
        # Command queue for legacy agents
        self.command_queues: Dict[str, List[str]] = {}
        self.queue_lock = threading.Lock()
    
    def is_legacy_connection(self, connection: socket.socket, timeout: float = 2.0) -> bool:
        """
        Detect if connection is from a legacy agent
        
        Legacy agents send system info immediately on connect without waiting
        for AUTH_REQUEST. Enhanced agents wait for AUTH_REQUEST before sending.
        
        Args:
            connection: Socket connection to test
            timeout: Timeout in seconds to wait for initial data
        
        Returns:
            True if legacy agent, False if enhanced agent
        
        Requirements: 25.1, 25.2
        """
        if not self.enabled:
            return False
        
        try:
            # Set short timeout to check for immediate data
            connection.settimeout(timeout)
            
            # Try to receive data without sending AUTH_REQUEST
            # Legacy agents send data immediately, enhanced agents wait
            data = connection.recv(1024, socket.MSG_PEEK)
            
            if data:
                # Check if it looks like legacy protocol (plain text, no JSON)
                try:
                    # Enhanced agents send JSON with length prefix
                    # Legacy agents send plain text
                    decoded = data.decode('utf-8', errors='ignore')
                    
                    # Legacy agents typically send "[AGENT ONLINE]" messages
                    if decoded.startswith('[AGENT ONLINE]') or decoded.startswith('['):
                        return True
                    
                    # Try to parse as JSON - if it fails, likely legacy
                    json.loads(decoded)
                    return False  # Valid JSON = enhanced agent
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return True  # Not JSON = legacy agent
            
            # No immediate data = enhanced agent waiting for AUTH_REQUEST
            return False
        
        except socket.timeout:
            # No immediate data = enhanced agent
            return False
        except Exception as e:
            print(f"[LEGACY] Error detecting connection type: {e}")
            return False
        finally:
            # Reset timeout
            connection.settimeout(None)
    
    def handle_legacy_agent(self, connection: socket.socket, address: Tuple[str, int]) -> None:
        """
        Handle legacy agent connection
        
        Implements the simple legacy protocol:
        1. Receive initial system info message
        2. Send ACK response
        3. Loop: receive messages, send ACK
        4. Support basic command execution
        
        Args:
            connection: Socket connection
            address: Client address tuple
        
        Requirements: 25.1, 25.2, 25.3
        """
        if not self.enabled:
            print(f"[LEGACY] Legacy mode disabled, rejecting connection from {address}")
            connection.close()
            return
        
        agent_id = f"legacy_{address[0]}_{address[1]}"
        
        try:
            print(f"[LEGACY] Handling legacy agent connection from {address}")
            
            # Create legacy agent connection object
            legacy_conn = LegacyAgentConnection(connection, address)
            
            # Register agent
            with self.agents_lock:
                self.legacy_agents[agent_id] = legacy_conn
            
            with self.queue_lock:
                self.command_queues[agent_id] = []
            
            # Receive initial system info
            connection.settimeout(30)
            initial_data = connection.recv(1024).decode('utf-8', errors='ignore')
            
            if initial_data:
                legacy_conn.agent_info = initial_data.strip()
                print(f"[LEGACY] Agent {agent_id}: {legacy_conn.agent_info}")
                
                # Send ACK
                connection.send("ACK".encode())
                
                # Log connection if database available
                if self.db_manager:
                    try:
                        agent_info = self._parse_legacy_info(initial_data)
                        agent_info["legacy"] = True
                        agent_info["ip_address"] = address[0]
                        self.db_manager.log_connection(agent_id, agent_info)
                    except Exception as e:
                        print(f"[LEGACY] Failed to log connection: {e}")
            
            # Command loop
            connection.settimeout(1.0)
            
            while True:
                try:
                    # Check for pending commands
                    command = self._get_next_command(agent_id)
                    
                    if command:
                        # Send command to agent
                        connection.send(command.encode())
                        
                        # Wait for result
                        connection.settimeout(60)
                        result = connection.recv(4096).decode('utf-8', errors='ignore')
                        
                        print(f"[LEGACY] Command result from {agent_id}: {result[:100]}")
                        
                        # Log command if database available
                        if self.db_manager:
                            try:
                                self.db_manager.log_command(
                                    agent_id=agent_id,
                                    command=command,
                                    result=result,
                                    status="success"
                                )
                            except Exception as e:
                                print(f"[LEGACY] Failed to log command: {e}")
                        
                        connection.settimeout(1.0)
                    
                    # Try to receive any messages from agent
                    try:
                        data = connection.recv(1024).decode('utf-8', errors='ignore')
                        
                        if not data:
                            break  # Connection closed
                        
                        print(f"[LEGACY] Message from {agent_id}: {data[:100]}")
                        
                        # Send ACK
                        connection.send("ACK".encode())
                    
                    except socket.timeout:
                        # Normal timeout, continue loop
                        continue
                
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[LEGACY] Error in command loop for {agent_id}: {e}")
                    break
        
        except Exception as e:
            print(f"[LEGACY] Error handling legacy agent {address}: {e}")
        
        finally:
            # Cleanup
            with self.agents_lock:
                if agent_id in self.legacy_agents:
                    del self.legacy_agents[agent_id]
            
            with self.queue_lock:
                if agent_id in self.command_queues:
                    del self.command_queues[agent_id]
            
            # Update status if database available
            if self.db_manager:
                try:
                    self.db_manager.update_agent_status(agent_id, "offline")
                except Exception:
                    pass
            
            try:
                connection.close()
            except Exception:
                pass
            
            print(f"[LEGACY] Disconnected legacy agent {agent_id}")
    
    def send_command_to_legacy_agent(self, agent_id: str, command: str) -> bool:
        """
        Queue command for legacy agent
        
        Args:
            agent_id: Legacy agent identifier
            command: Command string to execute
        
        Returns:
            True if command queued, False if agent not found
        
        Requirements: 25.2, 25.3
        """
        with self.queue_lock:
            if agent_id in self.command_queues:
                self.command_queues[agent_id].append(command)
                return True
        return False
    
    def get_legacy_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of connected legacy agents
        
        Returns:
            List of legacy agent information
        
        Requirements: 25.3
        """
        agents = []
        
        with self.agents_lock:
            for agent_id, conn in self.legacy_agents.items():
                agents.append({
                    "agent_id": agent_id,
                    "address": f"{conn.address[0]}:{conn.address[1]}",
                    "agent_info": conn.agent_info,
                    "connected_at": datetime.fromtimestamp(conn.connected_at).isoformat(),
                    "legacy": True
                })
        
        return agents
    
    def _get_next_command(self, agent_id: str) -> Optional[str]:
        """
        Get next pending command for agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Command string or None if no commands pending
        """
        with self.queue_lock:
            if agent_id in self.command_queues and self.command_queues[agent_id]:
                return self.command_queues[agent_id].pop(0)
        return None
    
    def _parse_legacy_info(self, info_string: str) -> Dict[str, Any]:
        """
        Parse legacy agent info string into structured data
        
        Args:
            info_string: Legacy info string like "[AGENT ONLINE] hostname|user|os"
        
        Returns:
            Dictionary with parsed agent information
        
        Requirements: 25.4
        """
        # Default values
        agent_info = {
            "hostname": "unknown",
            "username": "unknown",
            "os_type": "unknown",
            "os_version": "unknown",
            "mac_address": "unknown",
            "capabilities": [],
            "metadata": {}
        }
        
        try:
            # Remove "[AGENT ONLINE]" prefix if present
            if "[AGENT ONLINE]" in info_string:
                info_string = info_string.replace("[AGENT ONLINE]", "").strip()
            
            # Parse pipe-separated values
            parts = info_string.split("|")
            
            if len(parts) >= 1:
                agent_info["hostname"] = parts[0].strip()
            if len(parts) >= 2:
                agent_info["username"] = parts[1].strip()
            if len(parts) >= 3:
                agent_info["os_type"] = parts[2].strip()
            if len(parts) >= 4:
                agent_info["os_version"] = parts[3].strip()
            if len(parts) >= 5:
                agent_info["mac_address"] = parts[4].strip()
        
        except Exception as e:
            print(f"[LEGACY] Error parsing agent info: {e}")
        
        return agent_info


class ConfigMigrator:
    """
    Utility for migrating legacy configuration to new format
    
    Requirements: 25.4
    """
    
    @staticmethod
    def migrate_config(legacy_config_path: str, new_config_path: str) -> bool:
        """
        Migrate legacy configuration file to new format
        
        Legacy format: Simple key=value pairs
        New format: JSON with nested structure
        
        Args:
            legacy_config_path: Path to legacy config file
            new_config_path: Path to save new config file
        
        Returns:
            True if migration successful, False otherwise
        
        Requirements: 25.4
        """
        try:
            if not os.path.exists(legacy_config_path):
                print(f"[MIGRATION] Legacy config not found: {legacy_config_path}")
                return False
            
            # Read legacy config
            legacy_config = {}
            with open(legacy_config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        legacy_config[key.strip()] = value.strip()
            
            # Convert to new format
            new_config = {
                "server": {
                    "host": legacy_config.get("SERVER_HOST", "0.0.0.0"),
                    "port": int(legacy_config.get("SERVER_PORT", "9999")),
                    "use_tls": True,
                    "secret_key": legacy_config.get("SECRET_KEY", "change_me")
                },
                "database": {
                    "path": legacy_config.get("DB_PATH", "./remote_system.db"),
                    "type": "sqlite"
                },
                "legacy": {
                    "enabled": True,
                    "note": "Migrated from legacy configuration"
                },
                "migrated_at": datetime.now().isoformat()
            }
            
            # Write new config
            with open(new_config_path, 'w') as f:
                json.dump(new_config, f, indent=2)
            
            print(f"[MIGRATION] Configuration migrated successfully to {new_config_path}")
            return True
        
        except Exception as e:
            print(f"[MIGRATION] Error migrating configuration: {e}")
            return False


class LogMigrator:
    """
    Utility for migrating legacy logs to new database schema
    
    Requirements: 25.5
    """
    
    @staticmethod
    def migrate_logs(legacy_log_path: str, db_manager) -> Tuple[int, int]:
        """
        Migrate legacy logs to new database schema
        
        Legacy logs: Plain text file with timestamped entries
        New schema: SQLite database with structured tables
        
        Args:
            legacy_log_path: Path to legacy log file
            db_manager: Database manager instance
        
        Returns:
            Tuple of (successful_migrations, failed_migrations)
        
        Requirements: 25.5
        """
        success_count = 0
        failure_count = 0
        
        try:
            if not os.path.exists(legacy_log_path):
                print(f"[MIGRATION] Legacy log not found: {legacy_log_path}")
                return (0, 0)
            
            with open(legacy_log_path, 'r') as f:
                for line in f:
                    try:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse legacy log format: [timestamp] [address] message
                        # Example: [2024-01-01 12:00:00] [192.168.1.100:5000] [AGENT ONLINE] ...
                        
                        if '[' not in line:
                            continue
                        
                        # Extract components
                        parts = line.split(']', 2)
                        if len(parts) < 3:
                            continue
                        
                        timestamp_str = parts[0].replace('[', '').strip()
                        address_str = parts[1].replace('[', '').strip()
                        message = parts[2].strip()
                        
                        # Parse address
                        if ':' in address_str:
                            ip, port = address_str.split(':')
                            agent_id = f"legacy_{ip}_{port}"
                        else:
                            agent_id = f"legacy_{address_str}"
                        
                        # Determine log type and insert
                        if '[AGENT ONLINE]' in message or 'CONNECTED' in message:
                            # Connection log
                            agent_info = {
                                "hostname": "migrated",
                                "username": "migrated",
                                "os_type": "unknown",
                                "os_version": "unknown",
                                "mac_address": "unknown",
                                "ip_address": ip if ':' in address_str else address_str,
                                "legacy": True,
                                "migrated": True
                            }
                            db_manager.log_connection(agent_id, agent_info)
                        else:
                            # Command log
                            db_manager.log_command(
                                agent_id=agent_id,
                                command="migrated_legacy_log",
                                result=message,
                                status="migrated"
                            )
                        
                        success_count += 1
                    
                    except Exception as e:
                        print(f"[MIGRATION] Error migrating log entry: {e}")
                        failure_count += 1
            
            print(f"[MIGRATION] Logs migrated: {success_count} successful, {failure_count} failed")
            return (success_count, failure_count)
        
        except Exception as e:
            print(f"[MIGRATION] Error migrating logs: {e}")
            return (success_count, failure_count)


if __name__ == "__main__":
    # Example usage
    print("Legacy Handler Module")
    print("This module provides backward compatibility with legacy agents")
    print()
    print("Features:")
    print("- Detect legacy vs enhanced agent connections")
    print("- Handle legacy agents with simple text protocol")
    print("- Support simultaneous old and new agents")
    print("- Migrate configuration and logs")
