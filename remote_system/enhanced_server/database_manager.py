"""
Database Manager Module for Remote System Enhancement

This module provides database operations for logging agent connections,
command executions, file transfers, and managing agent registry.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
import json

Base = declarative_base()


class Agent(Base):
    """
    Schema for agents table
    Stores information about connected agents
    """
    __tablename__ = 'agents'
    
    agent_id = Column(String(36), primary_key=True)  # UUID
    hostname = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    os_type = Column(String(50), nullable=False)
    os_version = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv6 compatible
    mac_address = Column(String(17), nullable=False)
    connected_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), nullable=False, default='online')  # online, offline, idle
    capabilities = Column(JSON, nullable=False, default=list)  # List of available plugins
    agent_metadata = Column(JSON, nullable=True, default=dict)  # Additional metadata


class CommandLog(Base):
    """
    Schema for command_logs table
    Stores command execution history
    """
    __tablename__ = 'command_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(36), nullable=False)
    command = Column(Text, nullable=False)
    result = Column(Text, nullable=True)
    status = Column(String(20), nullable=False)  # success, error, timeout, pending
    executed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    execution_time = Column(Float, nullable=True)  # seconds


class ConnectionLog(Base):
    """
    Schema for connection_logs table
    Stores agent connection and disconnection events
    """
    __tablename__ = 'connection_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(36), nullable=False)
    connected_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    disconnected_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=False)


class FileTransfer(Base):
    """
    Schema for file_transfers table
    Stores file transfer operations
    """
    __tablename__ = 'file_transfers'
    
    transfer_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(36), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    checksum = Column(String(64), nullable=False)  # SHA256
    direction = Column(String(10), nullable=False)  # upload, download
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class DatabaseManager:
    """
    Database Manager for Remote System Enhancement
    
    Handles all database operations including agent registry,
    command logging, connection tracking, and file transfer logging.
    """
    
    def __init__(self, db_path: str, db_type: str = "sqlite"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to database file (for SQLite) or connection string
            db_type: Type of database (sqlite, postgresql)
        """
        if db_type == "sqlite":
            # Use check_same_thread=False for SQLite to allow multi-threaded access
            # Use QueuePool for connection pooling (10-50 connections)
            self.engine = create_engine(
                f'sqlite:///{db_path}',
                connect_args={'check_same_thread': False},
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=40,
                pool_pre_ping=True  # Verify connections before using
            )
        elif db_type == "postgresql":
            # PostgreSQL with connection pooling
            self.engine = create_engine(
                db_path,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=40,
                pool_pre_ping=True
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
    
    def _get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    def log_connection(self, agent_id: str, agent_info: Dict[str, Any]) -> None:
        """
        Log agent connection event
        
        Args:
            agent_id: Unique agent identifier
            agent_info: Dictionary containing agent information
                Required keys: hostname, username, os_type, os_version,
                              ip_address, mac_address, capabilities
        
        Requirements: 12.1
        """
        session = self._get_session()
        try:
            # Check if agent already exists
            existing_agent = session.query(Agent).filter_by(agent_id=agent_id).first()
            
            if existing_agent:
                # Update existing agent
                existing_agent.hostname = agent_info.get('hostname', existing_agent.hostname)
                existing_agent.username = agent_info.get('username', existing_agent.username)
                existing_agent.os_type = agent_info.get('os_type', existing_agent.os_type)
                existing_agent.os_version = agent_info.get('os_version', existing_agent.os_version)
                existing_agent.ip_address = agent_info.get('ip_address', existing_agent.ip_address)
                existing_agent.mac_address = agent_info.get('mac_address', existing_agent.mac_address)
                existing_agent.last_seen = datetime.now(timezone.utc)
                existing_agent.status = 'online'
                existing_agent.capabilities = agent_info.get('capabilities', existing_agent.capabilities)
                existing_agent.agent_metadata = agent_info.get('metadata', existing_agent.agent_metadata)
            else:
                # Create new agent record
                new_agent = Agent(
                    agent_id=agent_id,
                    hostname=agent_info['hostname'],
                    username=agent_info['username'],
                    os_type=agent_info['os_type'],
                    os_version=agent_info['os_version'],
                    ip_address=agent_info['ip_address'],
                    mac_address=agent_info['mac_address'],
                    connected_at=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                    status='online',
                    capabilities=agent_info.get('capabilities', []),
                    agent_metadata=agent_info.get('metadata', {})
                )
                session.add(new_agent)
            
            # Log connection event
            connection_log = ConnectionLog(
                agent_id=agent_id,
                connected_at=datetime.now(timezone.utc),
                ip_address=agent_info['ip_address']
            )
            session.add(connection_log)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def log_command(self, agent_id: str, command: str, result: Optional[str] = None,
                   status: str = 'pending', execution_time: Optional[float] = None) -> int:
        """
        Log command execution
        
        Args:
            agent_id: Unique agent identifier
            command: Command text
            result: Command execution result (optional)
            status: Execution status (pending, success, error, timeout)
            execution_time: Time taken to execute command in seconds (optional)
        
        Returns:
            log_id: ID of the created log entry
        
        Requirements: 12.2, 12.3
        """
        session = self._get_session()
        try:
            command_log = CommandLog(
                agent_id=agent_id,
                command=command,
                result=result,
                status=status,
                executed_at=datetime.now(timezone.utc),
                execution_time=execution_time
            )
            session.add(command_log)
            session.commit()
            log_id = command_log.log_id
            return log_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_command_log(self, log_id: int, result: str, status: str, execution_time: float) -> None:
        """
        Update command log with execution result
        
        Args:
            log_id: ID of the log entry to update
            result: Command execution result
            status: Execution status (success, error, timeout)
            execution_time: Time taken to execute command in seconds
        
        Requirements: 12.3
        """
        session = self._get_session()
        try:
            command_log = session.query(CommandLog).filter_by(log_id=log_id).first()
            if command_log:
                command_log.result = result
                command_log.status = status
                command_log.execution_time = execution_time
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_agent_history(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get command execution history for an agent
        
        Args:
            agent_id: Unique agent identifier
            limit: Maximum number of records to return
        
        Returns:
            List of command log dictionaries
        
        Requirements: 12.4
        """
        session = self._get_session()
        try:
            logs = session.query(CommandLog).filter_by(agent_id=agent_id)\
                         .order_by(CommandLog.executed_at.desc())\
                         .limit(limit).all()
            
            result = []
            for log in logs:
                result.append({
                    'log_id': log.log_id,
                    'agent_id': log.agent_id,
                    'command': log.command,
                    'result': log.result,
                    'status': log.status,
                    'executed_at': log.executed_at.isoformat() if log.executed_at else None,
                    'execution_time': log.execution_time
                })
            
            return result
        finally:
            session.close()
    
    def get_active_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of all active (online) agents
        
        Returns:
            List of agent information dictionaries
        
        Requirements: 12.5
        """
        session = self._get_session()
        try:
            agents = session.query(Agent).filter_by(status='online').all()
            
            result = []
            for agent in agents:
                result.append({
                    'agent_id': agent.agent_id,
                    'hostname': agent.hostname,
                    'username': agent.username,
                    'os_type': agent.os_type,
                    'os_version': agent.os_version,
                    'ip_address': agent.ip_address,
                    'mac_address': agent.mac_address,
                    'connected_at': agent.connected_at.isoformat() if agent.connected_at else None,
                    'last_seen': agent.last_seen.isoformat() if agent.last_seen else None,
                    'status': agent.status,
                    'capabilities': agent.capabilities,
                    'metadata': agent.agent_metadata
                })
            
            return result
        finally:
            session.close()
    
    def update_agent_status(self, agent_id: str, status: str) -> None:
        """
        Update agent status
        
        Args:
            agent_id: Unique agent identifier
            status: New status (online, offline, idle)
        
        Requirements: 12.6
        """
        session = self._get_session()
        try:
            agent = session.query(Agent).filter_by(agent_id=agent_id).first()
            if agent:
                agent.status = status
                agent.last_seen = datetime.now(timezone.utc)
                
                # If going offline, update connection log
                if status == 'offline':
                    connection_log = session.query(ConnectionLog)\
                                           .filter_by(agent_id=agent_id, disconnected_at=None)\
                                           .order_by(ConnectionLog.connected_at.desc())\
                                           .first()
                    if connection_log:
                        connection_log.disconnected_at = datetime.now(timezone.utc)
                
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def log_file_transfer(self, agent_id: str, file_path: str, file_size: int,
                         checksum: str, direction: str) -> None:
        """
        Log file transfer operation
        
        Args:
            agent_id: Unique agent identifier
            file_path: Path to the transferred file
            file_size: Size of file in bytes
            checksum: SHA256 checksum of file
            direction: Transfer direction (upload or download)
        
        Requirements: 12.4
        """
        session = self._get_session()
        try:
            file_transfer = FileTransfer(
                agent_id=agent_id,
                file_path=file_path,
                file_size=file_size,
                checksum=checksum,
                direction=direction,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(file_transfer)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of all agents (regardless of status)
        
        Returns:
            List of agent information dictionaries
        """
        session = self._get_session()
        try:
            agents = session.query(Agent).all()
            
            result = []
            for agent in agents:
                result.append({
                    'agent_id': agent.agent_id,
                    'hostname': agent.hostname,
                    'username': agent.username,
                    'os_type': agent.os_type,
                    'os_version': agent.os_version,
                    'ip_address': agent.ip_address,
                    'mac_address': agent.mac_address,
                    'connected_at': agent.connected_at.isoformat() if agent.connected_at else None,
                    'last_seen': agent.last_seen.isoformat() if agent.last_seen else None,
                    'status': agent.status,
                    'capabilities': agent.capabilities,
                    'metadata': agent.agent_metadata
                })
            
            return result
        finally:
            session.close()
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent information by ID
        
        Args:
            agent_id: Unique agent identifier
        
        Returns:
            Agent information dictionary or None if not found
        """
        session = self._get_session()
        try:
            agent = session.query(Agent).filter_by(agent_id=agent_id).first()
            
            if not agent:
                return None
            
            return {
                'agent_id': agent.agent_id,
                'hostname': agent.hostname,
                'username': agent.username,
                'os_type': agent.os_type,
                'os_version': agent.os_version,
                'ip_address': agent.ip_address,
                'mac_address': agent.mac_address,
                'connected_at': agent.connected_at.isoformat() if agent.connected_at else None,
                'last_seen': agent.last_seen.isoformat() if agent.last_seen else None,
                'status': agent.status,
                'capabilities': agent.capabilities,
                'metadata': agent.agent_metadata
            }
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connection and cleanup resources"""
        self.engine.dispose()

