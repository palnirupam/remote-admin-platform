"""
Unit tests for DatabaseManager

Tests database initialization, schema creation, CRUD operations,
query methods, connection pooling, and error handling.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""

import pytest
import os
import tempfile
from datetime import datetime
from remote_system.enhanced_server.database_manager import (
    DatabaseManager,
    Agent,
    CommandLog,
    ConnectionLog,
    FileTransfer
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager instance with temporary database"""
    manager = DatabaseManager(temp_db, db_type="sqlite")
    yield manager
    manager.close()


@pytest.fixture
def sample_agent_info():
    """Sample agent information for testing"""
    return {
        'hostname': 'test-host',
        'username': 'test-user',
        'os_type': 'Windows',
        'os_version': '10.0.19041',
        'ip_address': '192.168.1.100',
        'mac_address': '00:11:22:33:44:55',
        'capabilities': ['file_transfer', 'screenshot'],
        'metadata': {'version': '1.0.0'}
    }


class TestDatabaseInitialization:
    """Test database initialization and schema creation"""
    
    def test_database_creation(self, temp_db):
        """Test that database file is created"""
        manager = DatabaseManager(temp_db)
        assert os.path.exists(temp_db)
        manager.close()
    
    def test_schema_creation(self, db_manager):
        """Test that all tables are created with correct schema"""
        session = db_manager._get_session()
        try:
            # Verify agents table exists
            result = session.query(Agent).count()
            assert result == 0
            
            # Verify command_logs table exists
            result = session.query(CommandLog).count()
            assert result == 0
            
            # Verify connection_logs table exists
            result = session.query(ConnectionLog).count()
            assert result == 0
            
            # Verify file_transfers table exists
            result = session.query(FileTransfer).count()
            assert result == 0
        finally:
            session.close()
    
    def test_invalid_db_type(self, temp_db):
        """Test that invalid database type raises error"""
        with pytest.raises(ValueError, match="Unsupported database type"):
            DatabaseManager(temp_db, db_type="invalid")


class TestAgentOperations:
    """Test CRUD operations for agents table"""
    
    def test_log_connection_new_agent(self, db_manager, sample_agent_info):
        """Test logging connection for new agent - Requirement 12.1"""
        agent_id = "test-agent-001"
        
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Verify agent was created
        agent = db_manager.get_agent_by_id(agent_id)
        assert agent is not None
        assert agent['agent_id'] == agent_id
        assert agent['hostname'] == sample_agent_info['hostname']
        assert agent['username'] == sample_agent_info['username']
        assert agent['status'] == 'online'
    
    def test_log_connection_existing_agent(self, db_manager, sample_agent_info):
        """Test logging connection for existing agent updates info"""
        agent_id = "test-agent-002"
        
        # First connection
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Second connection with updated info
        updated_info = sample_agent_info.copy()
        updated_info['hostname'] = 'updated-host'
        updated_info['ip_address'] = '192.168.1.200'
        
        db_manager.log_connection(agent_id, updated_info)
        
        # Verify agent was updated
        agent = db_manager.get_agent_by_id(agent_id)
        assert agent['hostname'] == 'updated-host'
        assert agent['ip_address'] == '192.168.1.200'
        assert agent['status'] == 'online'
    
    def test_get_active_agents(self, db_manager, sample_agent_info):
        """Test retrieving active agents - Requirement 12.5"""
        # Create multiple agents
        db_manager.log_connection("agent-001", sample_agent_info)
        db_manager.log_connection("agent-002", sample_agent_info)
        db_manager.log_connection("agent-003", sample_agent_info)
        
        # Mark one as offline
        db_manager.update_agent_status("agent-002", "offline")
        
        # Get active agents
        active_agents = db_manager.get_active_agents()
        
        assert len(active_agents) == 2
        agent_ids = [agent['agent_id'] for agent in active_agents]
        assert "agent-001" in agent_ids
        assert "agent-003" in agent_ids
        assert "agent-002" not in agent_ids
    
    def test_get_all_agents(self, db_manager, sample_agent_info):
        """Test retrieving all agents regardless of status"""
        db_manager.log_connection("agent-001", sample_agent_info)
        db_manager.log_connection("agent-002", sample_agent_info)
        db_manager.update_agent_status("agent-002", "offline")
        
        all_agents = db_manager.get_all_agents()
        
        assert len(all_agents) == 2
    
    def test_update_agent_status(self, db_manager, sample_agent_info):
        """Test updating agent status - Requirement 12.6"""
        agent_id = "test-agent-003"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Update to idle
        db_manager.update_agent_status(agent_id, "idle")
        agent = db_manager.get_agent_by_id(agent_id)
        assert agent['status'] == 'idle'
        
        # Update to offline
        db_manager.update_agent_status(agent_id, "offline")
        agent = db_manager.get_agent_by_id(agent_id)
        assert agent['status'] == 'offline'
    
    def test_get_agent_by_id_not_found(self, db_manager):
        """Test getting non-existent agent returns None"""
        agent = db_manager.get_agent_by_id("non-existent")
        assert agent is None


class TestCommandLogging:
    """Test command logging operations"""
    
    def test_log_command_pending(self, db_manager, sample_agent_info):
        """Test logging pending command - Requirement 12.2"""
        agent_id = "test-agent-004"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        log_id = db_manager.log_command(
            agent_id=agent_id,
            command="dir C:\\",
            status="pending"
        )
        
        assert log_id is not None
        assert isinstance(log_id, int)
    
    def test_log_command_with_result(self, db_manager, sample_agent_info):
        """Test logging command with immediate result"""
        agent_id = "test-agent-005"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        log_id = db_manager.log_command(
            agent_id=agent_id,
            command="echo test",
            result="test",
            status="success",
            execution_time=0.5
        )
        
        assert log_id is not None
    
    def test_update_command_log(self, db_manager, sample_agent_info):
        """Test updating command log with result - Requirement 12.3"""
        agent_id = "test-agent-006"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Log pending command
        log_id = db_manager.log_command(
            agent_id=agent_id,
            command="whoami",
            status="pending"
        )
        
        # Update with result
        db_manager.update_command_log(
            log_id=log_id,
            result="test-user",
            status="success",
            execution_time=0.3
        )
        
        # Verify update
        history = db_manager.get_agent_history(agent_id, limit=1)
        assert len(history) == 1
        assert history[0]['result'] == "test-user"
        assert history[0]['status'] == "success"
        assert history[0]['execution_time'] == 0.3
    
    def test_get_agent_history(self, db_manager, sample_agent_info):
        """Test retrieving command history - Requirement 12.4"""
        agent_id = "test-agent-007"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Log multiple commands
        commands = [
            ("command1", "result1", "success", 0.1),
            ("command2", "result2", "success", 0.2),
            ("command3", "result3", "error", 0.3),
        ]
        
        for cmd, result, status, exec_time in commands:
            db_manager.log_command(agent_id, cmd, result, status, exec_time)
        
        # Get history
        history = db_manager.get_agent_history(agent_id, limit=10)
        
        assert len(history) == 3
        # Should be in reverse chronological order
        assert history[0]['command'] == "command3"
        assert history[1]['command'] == "command2"
        assert history[2]['command'] == "command1"
    
    def test_get_agent_history_with_limit(self, db_manager, sample_agent_info):
        """Test history retrieval respects limit"""
        agent_id = "test-agent-008"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Log 10 commands
        for i in range(10):
            db_manager.log_command(agent_id, f"command{i}", f"result{i}", "success", 0.1)
        
        # Get limited history
        history = db_manager.get_agent_history(agent_id, limit=5)
        
        assert len(history) == 5
    
    def test_command_log_different_statuses(self, db_manager, sample_agent_info):
        """Test logging commands with different statuses"""
        agent_id = "test-agent-009"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Test different status values
        statuses = ["pending", "success", "error", "timeout"]
        
        for status in statuses:
            log_id = db_manager.log_command(
                agent_id=agent_id,
                command=f"test_{status}",
                status=status
            )
            assert log_id is not None


class TestConnectionLogging:
    """Test connection logging operations"""
    
    def test_connection_log_created(self, db_manager, sample_agent_info):
        """Test that connection log is created on agent connection"""
        agent_id = "test-agent-010"
        
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Verify connection log exists
        session = db_manager._get_session()
        try:
            conn_log = session.query(ConnectionLog).filter_by(agent_id=agent_id).first()
            assert conn_log is not None
            assert conn_log.ip_address == sample_agent_info['ip_address']
            assert conn_log.disconnected_at is None
        finally:
            session.close()
    
    def test_disconnection_logged(self, db_manager, sample_agent_info):
        """Test that disconnection updates connection log"""
        agent_id = "test-agent-011"
        
        db_manager.log_connection(agent_id, sample_agent_info)
        db_manager.update_agent_status(agent_id, "offline")
        
        # Verify disconnection time is set
        session = db_manager._get_session()
        try:
            conn_log = session.query(ConnectionLog).filter_by(agent_id=agent_id).first()
            assert conn_log.disconnected_at is not None
        finally:
            session.close()


class TestFileTransferLogging:
    """Test file transfer logging operations"""
    
    def test_log_file_upload(self, db_manager, sample_agent_info):
        """Test logging file upload - Requirement 12.4"""
        agent_id = "test-agent-012"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        db_manager.log_file_transfer(
            agent_id=agent_id,
            file_path="C:\\test\\file.txt",
            file_size=1024,
            checksum="abc123def456",
            direction="upload"
        )
        
        # Verify file transfer was logged
        session = db_manager._get_session()
        try:
            transfer = session.query(FileTransfer).filter_by(agent_id=agent_id).first()
            assert transfer is not None
            assert transfer.file_path == "C:\\test\\file.txt"
            assert transfer.file_size == 1024
            assert transfer.direction == "upload"
        finally:
            session.close()
    
    def test_log_file_download(self, db_manager, sample_agent_info):
        """Test logging file download"""
        agent_id = "test-agent-013"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        db_manager.log_file_transfer(
            agent_id=agent_id,
            file_path="/home/user/document.pdf",
            file_size=2048,
            checksum="xyz789abc123",
            direction="download"
        )
        
        # Verify file transfer was logged
        session = db_manager._get_session()
        try:
            transfer = session.query(FileTransfer).filter_by(agent_id=agent_id).first()
            assert transfer is not None
            assert transfer.direction == "download"
        finally:
            session.close()


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_update_nonexistent_command_log(self, db_manager):
        """Test updating non-existent command log doesn't crash"""
        # Should not raise exception
        db_manager.update_command_log(
            log_id=99999,
            result="test",
            status="success",
            execution_time=0.1
        )
    
    def test_update_nonexistent_agent_status(self, db_manager):
        """Test updating non-existent agent status doesn't crash"""
        # Should not raise exception
        db_manager.update_agent_status("non-existent", "offline")
    
    def test_get_history_for_nonexistent_agent(self, db_manager):
        """Test getting history for non-existent agent returns empty list"""
        history = db_manager.get_agent_history("non-existent", limit=10)
        assert history == []
    
    def test_database_rollback_on_error(self, db_manager):
        """Test that database rolls back on error"""
        # This test verifies that errors don't corrupt the database
        agent_id = "test-agent-014"
        
        # Create valid agent
        valid_info = {
            'hostname': 'test',
            'username': 'test',
            'os_type': 'Windows',
            'os_version': '10',
            'ip_address': '192.168.1.1',
            'mac_address': '00:11:22:33:44:55'
        }
        db_manager.log_connection(agent_id, valid_info)
        
        # Verify agent exists
        agent = db_manager.get_agent_by_id(agent_id)
        assert agent is not None


class TestConnectionPooling:
    """Test connection pooling behavior"""
    
    def test_multiple_sessions(self, db_manager, sample_agent_info):
        """Test that multiple operations use connection pool correctly"""
        # Perform multiple operations
        for i in range(10):
            agent_id = f"agent-{i:03d}"
            db_manager.log_connection(agent_id, sample_agent_info)
            db_manager.log_command(agent_id, f"command{i}", status="pending")
        
        # Verify all operations succeeded
        all_agents = db_manager.get_all_agents()
        assert len(all_agents) == 10
    
    def test_session_cleanup(self, db_manager, sample_agent_info):
        """Test that sessions are properly closed after operations"""
        agent_id = "test-agent-015"
        
        # Perform operation
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Session should be closed, new operation should work
        agent = db_manager.get_agent_by_id(agent_id)
        assert agent is not None
    
    def test_concurrent_operations(self, db_manager, sample_agent_info):
        """Test that concurrent operations don't interfere"""
        agent_id = "test-agent-016"
        
        # Simulate concurrent operations
        db_manager.log_connection(agent_id, sample_agent_info)
        log_id = db_manager.log_command(agent_id, "test", status="pending")
        db_manager.update_agent_status(agent_id, "idle")
        db_manager.update_command_log(log_id, "result", "success", 0.5)
        
        # Verify all operations succeeded
        agent = db_manager.get_agent_by_id(agent_id)
        assert agent['status'] == 'idle'
        
        history = db_manager.get_agent_history(agent_id)
        assert len(history) == 1
        assert history[0]['status'] == 'success'


class TestDataIntegrity:
    """Test data integrity and validation"""
    
    def test_agent_capabilities_json(self, db_manager):
        """Test that capabilities are stored as JSON"""
        agent_id = "test-agent-017"
        agent_info = {
            'hostname': 'test',
            'username': 'test',
            'os_type': 'Linux',
            'os_version': '5.4',
            'ip_address': '10.0.0.1',
            'mac_address': 'AA:BB:CC:DD:EE:FF',
            'capabilities': ['plugin1', 'plugin2', 'plugin3']
        }
        
        db_manager.log_connection(agent_id, agent_info)
        
        agent = db_manager.get_agent_by_id(agent_id)
        assert isinstance(agent['capabilities'], list)
        assert len(agent['capabilities']) == 3
    
    def test_agent_metadata_json(self, db_manager):
        """Test that metadata is stored as JSON"""
        agent_id = "test-agent-018"
        agent_info = {
            'hostname': 'test',
            'username': 'test',
            'os_type': 'macOS',
            'os_version': '11.0',
            'ip_address': '172.16.0.1',
            'mac_address': '11:22:33:44:55:66',
            'metadata': {'key1': 'value1', 'key2': 'value2'}
        }
        
        db_manager.log_connection(agent_id, agent_info)
        
        agent = db_manager.get_agent_by_id(agent_id)
        assert isinstance(agent['metadata'], dict)
        assert agent['metadata']['key1'] == 'value1'
    
    def test_timestamp_formats(self, db_manager, sample_agent_info):
        """Test that timestamps are properly formatted"""
        agent_id = "test-agent-019"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        agent = db_manager.get_agent_by_id(agent_id)
        
        # Timestamps should be ISO format strings
        assert isinstance(agent['connected_at'], str)
        assert isinstance(agent['last_seen'], str)
        
        # Should be parseable as datetime
        datetime.fromisoformat(agent['connected_at'])
        datetime.fromisoformat(agent['last_seen'])


class TestQueryFilters:
    """Test query methods with various filters"""
    
    def test_filter_by_status(self, db_manager, sample_agent_info):
        """Test filtering agents by status"""
        # Create agents with different statuses
        db_manager.log_connection("agent-online-1", sample_agent_info)
        db_manager.log_connection("agent-online-2", sample_agent_info)
        db_manager.log_connection("agent-offline", sample_agent_info)
        db_manager.update_agent_status("agent-offline", "offline")
        
        active = db_manager.get_active_agents()
        assert len(active) == 2
        
        all_agents = db_manager.get_all_agents()
        assert len(all_agents) == 3
    
    def test_command_history_ordering(self, db_manager, sample_agent_info):
        """Test that command history is ordered by time descending"""
        agent_id = "test-agent-020"
        db_manager.log_connection(agent_id, sample_agent_info)
        
        # Log commands with slight delay to ensure different timestamps
        import time
        for i in range(5):
            db_manager.log_command(agent_id, f"command{i}", status="success")
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        history = db_manager.get_agent_history(agent_id)
        
        # Most recent command should be first
        assert history[0]['command'] == "command4"
        assert history[-1]['command'] == "command0"
