"""
Unit and Property-Based Tests for FileTransferPlugin

Tests file upload, download, directory listing, hash calculation,
chunked transfer, checksum validation, and resume capability.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

import pytest
import os
import tempfile
import shutil
import hashlib
from typing import Dict, Any
from hypothesis import given, strategies as st, settings, HealthCheck
from remote_system.plugins.file_transfer_plugin import (
    FileTransferPlugin,
    TransferResult,
    FileInfo
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def plugin():
    """Create a FileTransferPlugin instance"""
    return FileTransferPlugin()


class TestFileTransferPluginBasics:
    """Test basic plugin functionality"""
    
    def test_plugin_name(self, plugin):
        """Test plugin name"""
        assert plugin.get_name() == "file_transfer"
    
    def test_required_arguments(self, plugin):
        """Test required arguments"""
        required = plugin.get_required_arguments()
        assert 'action' in required
    
    def test_execute_invalid_action(self, plugin):
        """Test execute with invalid action"""
        with pytest.raises(ValueError, match="Invalid action"):
            plugin.execute({'action': 'invalid_action'})


class TestFileHash:
    """Test file hash calculation"""
    
    def test_get_file_hash_basic(self, plugin, temp_dir):
        """Test basic hash calculation - Requirement 1.3"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        content = b"Hello, World!"
        
        with open(test_file, 'wb') as f:
            f.write(content)
        
        # Calculate hash
        file_hash = plugin.get_file_hash(test_file)
        
        # Verify hash is correct
        expected_hash = hashlib.sha256(content).hexdigest()
        assert file_hash == expected_hash
    
    def test_get_file_hash_nonexistent(self, plugin):
        """Test hash calculation for non-existent file"""
        with pytest.raises(ValueError, match="File not found"):
            plugin.get_file_hash("/nonexistent/file.txt")
    
    def test_get_file_hash_directory(self, plugin, temp_dir):
        """Test hash calculation for directory (should fail)"""
        with pytest.raises(ValueError, match="not a file"):
            plugin.get_file_hash(temp_dir)
    
    def test_get_file_hash_via_execute(self, plugin, temp_dir):
        """Test hash calculation via execute method"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'wb') as f:
            f.write(b"Test content")
        
        result = plugin.execute({
            'action': 'get_file_hash',
            'path': test_file
        })
        
        assert 'hash' in result
        assert 'algorithm' in result
        assert result['algorithm'] == 'SHA256'


class TestListDirectory:
    """Test directory listing"""
    
    def test_list_directory_basic(self, plugin, temp_dir):
        """Test basic directory listing - Requirement 1.6"""
        # Create test files
        file1 = os.path.join(temp_dir, "file1.txt")
        file2 = os.path.join(temp_dir, "file2.txt")
        subdir = os.path.join(temp_dir, "subdir")
        
        with open(file1, 'w') as f:
            f.write("content1")
        with open(file2, 'w') as f:
            f.write("content2")
        os.makedirs(subdir)
        
        # List directory
        file_list = plugin.list_directory(temp_dir)
        
        # Verify results
        assert len(file_list) == 3
        
        names = [f.name for f in file_list]
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "subdir" in names
        
        # Check FileInfo attributes
        for file_info in file_list:
            assert isinstance(file_info, FileInfo)
            assert file_info.name
            assert file_info.path
            assert file_info.size >= 0
            assert file_info.modified_time > 0
            assert isinstance(file_info.is_directory, bool)
    
    def test_list_directory_nonexistent(self, plugin):
        """Test listing non-existent directory"""
        with pytest.raises(ValueError, match="Directory not found"):
            plugin.list_directory("/nonexistent/directory")
    
    def test_list_directory_file(self, plugin, temp_dir):
        """Test listing a file (should fail)"""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("content")
        
        with pytest.raises(ValueError, match="not a directory"):
            plugin.list_directory(test_file)
    
    def test_list_directory_via_execute(self, plugin, temp_dir):
        """Test directory listing via execute method"""
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("content")
        
        result = plugin.execute({
            'action': 'list_directory',
            'path': temp_dir
        })
        
        assert 'files' in result
        assert len(result['files']) == 1
        assert result['files'][0]['name'] == 'test.txt'


class TestFileUpload:
    """Test file upload functionality"""
    
    def test_upload_file_basic(self, plugin, temp_dir):
        """Test basic file upload - Requirements 1.1, 1.3"""
        # Create source file
        source_file = os.path.join(temp_dir, "source.txt")
        content = b"Test content for upload"
        
        with open(source_file, 'wb') as f:
            f.write(content)
        
        # Upload to destination
        dest_file = os.path.join(temp_dir, "dest.txt")
        result = plugin.upload_file(source_file, dest_file)
        
        # Verify result
        assert result.success is True
        assert result.error is None
        assert result.bytes_transferred == len(content)
        assert result.total_bytes == len(content)
        assert result.checksum
        assert result.transfer_time >= 0
        
        # Verify file was created
        assert os.path.exists(dest_file)
        
        # Verify content matches
        with open(dest_file, 'rb') as f:
            dest_content = f.read()
        assert dest_content == content
        
        # Verify checksum matches
        expected_hash = hashlib.sha256(content).hexdigest()
        assert result.checksum == expected_hash
    
    def test_upload_file_nonexistent_source(self, plugin, temp_dir):
        """Test upload with non-existent source file"""
        source_file = os.path.join(temp_dir, "nonexistent.txt")
        dest_file = os.path.join(temp_dir, "dest.txt")
        
        result = plugin.upload_file(source_file, dest_file)
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_upload_file_custom_chunk_size(self, plugin, temp_dir):
        """Test upload with custom chunk size - Requirement 1.7"""
        # Create source file
        source_file = os.path.join(temp_dir, "source.txt")
        content = b"X" * 10000  # 10KB
        
        with open(source_file, 'wb') as f:
            f.write(content)
        
        # Upload with 8KB chunks
        dest_file = os.path.join(temp_dir, "dest.txt")
        result = plugin.upload_file(source_file, dest_file, chunk_size=8192)
        
        assert result.success is True
        assert result.bytes_transferred == len(content)
    
    def test_upload_file_chunk_size_limits(self, plugin, temp_dir):
        """Test chunk size is clamped to valid range - Requirement 1.7"""
        # Create source file
        source_file = os.path.join(temp_dir, "source.txt")
        content = b"Test content"
        
        with open(source_file, 'wb') as f:
            f.write(content)
        
        dest_file = os.path.join(temp_dir, "dest.txt")
        
        # Test with too small chunk size (should be clamped to 4KB)
        result = plugin.upload_file(source_file, dest_file, chunk_size=100)
        assert result.success is True
        
        # Test with too large chunk size (should be clamped to 1MB)
        dest_file2 = os.path.join(temp_dir, "dest2.txt")
        result = plugin.upload_file(source_file, dest_file2, chunk_size=10000000)
        assert result.success is True


class TestFileDownload:
    """Test file download functionality"""
    
    def test_download_file_basic(self, plugin, temp_dir):
        """Test basic file download - Requirements 1.2, 1.3"""
        # Create source file
        source_file = os.path.join(temp_dir, "source.txt")
        content = b"Test content for download"
        
        with open(source_file, 'wb') as f:
            f.write(content)
        
        # Download to destination
        dest_file = os.path.join(temp_dir, "dest.txt")
        result = plugin.download_file(source_file, dest_file)
        
        # Verify result
        assert result.success is True
        assert result.error is None
        assert result.bytes_transferred == len(content)
        assert result.total_bytes == len(content)
        assert result.checksum
        assert result.transfer_time >= 0
        
        # Verify file was created
        assert os.path.exists(dest_file)
        
        # Verify content matches
        with open(dest_file, 'rb') as f:
            dest_content = f.read()
        assert dest_content == content
        
        # Verify checksum matches
        expected_hash = hashlib.sha256(content).hexdigest()
        assert result.checksum == expected_hash
    
    def test_download_file_nonexistent_source(self, plugin, temp_dir):
        """Test download with non-existent source file"""
        source_file = os.path.join(temp_dir, "nonexistent.txt")
        dest_file = os.path.join(temp_dir, "dest.txt")
        
        result = plugin.download_file(source_file, dest_file)
        
        assert result.success is False
        assert "not found" in result.error.lower()


class TestResumeCapability:
    """Test resume capability for interrupted transfers"""
    
    def test_upload_resume_from_partial(self, plugin, temp_dir):
        """Test upload resume from partial file - Requirements 1.4, 20.7"""
        # Create source file
        source_file = os.path.join(temp_dir, "source.txt")
        content = b"X" * 10000  # 10KB
        
        with open(source_file, 'wb') as f:
            f.write(content)
        
        # Create partial file (simulate interrupted transfer)
        dest_file = os.path.join(temp_dir, "dest.txt")
        partial_file = dest_file + ".partial"
        partial_content = content[:5000]  # First 5KB
        
        with open(partial_file, 'wb') as f:
            f.write(partial_content)
        
        # Resume upload
        result = plugin.upload_file(source_file, dest_file)
        
        # Verify success
        assert result.success is True
        assert result.bytes_transferred == len(content)
        
        # Verify final file is complete
        with open(dest_file, 'rb') as f:
            final_content = f.read()
        assert final_content == content
        
        # Verify partial file is removed
        assert not os.path.exists(partial_file)
    
    def test_download_resume_from_partial(self, plugin, temp_dir):
        """Test download resume from partial file - Requirements 1.4, 20.7"""
        # Create source file
        source_file = os.path.join(temp_dir, "source.txt")
        content = b"Y" * 10000  # 10KB
        
        with open(source_file, 'wb') as f:
            f.write(content)
        
        # Create partial file (simulate interrupted transfer)
        dest_file = os.path.join(temp_dir, "dest.txt")
        partial_file = dest_file + ".partial"
        partial_content = content[:5000]  # First 5KB
        
        with open(partial_file, 'wb') as f:
            f.write(partial_content)
        
        # Resume download
        result = plugin.download_file(source_file, dest_file)
        
        # Verify success
        assert result.success is True
        assert result.bytes_transferred == len(content)
        
        # Verify final file is complete
        with open(dest_file, 'rb') as f:
            final_content = f.read()
        assert final_content == content
        
        # Verify partial file is removed
        assert not os.path.exists(partial_file)


class TestChecksumValidation:
    """Test checksum validation"""
    
    def test_checksum_validation_success(self, plugin, temp_dir):
        """Test successful checksum validation - Requirement 1.3"""
        # Create and transfer file
        source_file = os.path.join(temp_dir, "source.txt")
        content = b"Test content"
        
        with open(source_file, 'wb') as f:
            f.write(content)
        
        dest_file = os.path.join(temp_dir, "dest.txt")
        result = plugin.upload_file(source_file, dest_file)
        
        # Verify checksum validation passed
        assert result.success is True
        
        # Verify checksums match
        source_hash = plugin.get_file_hash(source_file)
        dest_hash = plugin.get_file_hash(dest_file)
        assert source_hash == dest_hash
        assert result.checksum == source_hash


class TestPropertyBasedFileTransferIntegrity:
    """
    Property-Based Tests for File Transfer Integrity
    
    Property 3: File Transfer Integrity - Transferred files must have identical checksums
    Validates: Requirements 1.3, 1.5
    """
    
    @given(
        file_content=st.binary(min_size=1, max_size=10485760)  # 1 byte to 10MB
    )
    @settings(max_examples=20, deadline=10000)
    def test_property_upload_preserves_content(self, file_content):
        """
        **Validates: Requirements 1.3**
        
        Property 3: File Transfer Integrity - Upload must preserve content
        
        For all binary file contents:
        - Upload operation MUST preserve exact byte content
        - Source and destination checksums MUST match
        - Transfer MUST report success
        - Bytes transferred MUST equal file size
        """
        temp_dir = tempfile.mkdtemp()
        try:
            plugin = FileTransferPlugin()
            
            # Create source file
            source_file = os.path.join(temp_dir, "source.bin")
            with open(source_file, 'wb') as f:
                f.write(file_content)
            
            # Calculate source checksum
            source_checksum = hashlib.sha256(file_content).hexdigest()
            
            # Upload file
            dest_file = os.path.join(temp_dir, "dest.bin")
            result = plugin.upload_file(source_file, dest_file)
            
            # Property: Transfer must succeed
            assert result.success is True, \
                f"Upload must succeed. Error: {result.error}"
            
            # Property: Bytes transferred must equal file size
            assert result.bytes_transferred == len(file_content), \
                f"Bytes transferred ({result.bytes_transferred}) must equal file size ({len(file_content)})"
            
            # Property: Checksum must match source
            assert result.checksum == source_checksum, \
                f"Destination checksum must match source. Source: {source_checksum}, Dest: {result.checksum}"
            
            # Property: Destination file must exist
            assert os.path.exists(dest_file), \
                "Destination file must exist after successful transfer"
            
            # Property: Destination content must match source
            with open(dest_file, 'rb') as f:
                dest_content = f.read()
            assert dest_content == file_content, \
                "Destination content must exactly match source content"
            
            # Property: Destination checksum verification
            dest_checksum = plugin.get_file_hash(dest_file)
            assert dest_checksum == source_checksum, \
                f"Destination file checksum must match source. Source: {source_checksum}, Dest: {dest_checksum}"
        
        finally:
            shutil.rmtree(temp_dir)
    
    @given(
        file_content=st.binary(min_size=1, max_size=10485760)  # 1 byte to 10MB
    )
    @settings(max_examples=20, deadline=10000)
    def test_property_download_preserves_content(self, file_content):
        """
        **Validates: Requirements 1.3**
        
        Property 3: File Transfer Integrity - Download must preserve content
        
        For all binary file contents:
        - Download operation MUST preserve exact byte content
        - Source and destination checksums MUST match
        - Transfer MUST report success
        - Bytes transferred MUST equal file size
        """
        temp_dir = tempfile.mkdtemp()
        try:
            plugin = FileTransferPlugin()
            
            # Create source file
            source_file = os.path.join(temp_dir, "source.bin")
            with open(source_file, 'wb') as f:
                f.write(file_content)
            
            # Calculate source checksum
            source_checksum = hashlib.sha256(file_content).hexdigest()
            
            # Download file
            dest_file = os.path.join(temp_dir, "dest.bin")
            result = plugin.download_file(source_file, dest_file)
            
            # Property: Transfer must succeed
            assert result.success is True, \
                f"Download must succeed. Error: {result.error}"
            
            # Property: Bytes transferred must equal file size
            assert result.bytes_transferred == len(file_content), \
                f"Bytes transferred ({result.bytes_transferred}) must equal file size ({len(file_content)})"
            
            # Property: Checksum must match source
            assert result.checksum == source_checksum, \
                f"Destination checksum must match source. Source: {source_checksum}, Dest: {result.checksum}"
            
            # Property: Destination file must exist
            assert os.path.exists(dest_file), \
                "Destination file must exist after successful transfer"
            
            # Property: Destination content must match source
            with open(dest_file, 'rb') as f:
                dest_content = f.read()
            assert dest_content == file_content, \
                "Destination content must exactly match source content"
            
            # Property: Destination checksum verification
            dest_checksum = plugin.get_file_hash(dest_file)
            assert dest_checksum == source_checksum, \
                f"Destination file checksum must match source. Source: {source_checksum}, Dest: {dest_checksum}"
        
        finally:
            shutil.rmtree(temp_dir)
    
    @given(
        file_content=st.binary(min_size=1000, max_size=50000),  # 1KB to 50KB
        chunk_size=st.integers(min_value=4096, max_value=16384)  # 4KB to 16KB
    )
    @settings(
        max_examples=10, 
        deadline=None, 
        suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large, HealthCheck.too_slow]
    )
    def test_property_chunked_transfer_integrity(self, file_content, chunk_size):
        """
        **Validates: Requirements 1.3, 1.7**
        
        Property 3: File Transfer Integrity - Chunked transfer must preserve content
        
        For all file contents and valid chunk sizes:
        - Transfer with any valid chunk size MUST preserve content
        - Checksum MUST match regardless of chunk size
        - Transfer MUST succeed
        """
        temp_dir = tempfile.mkdtemp()
        try:
            plugin = FileTransferPlugin()
            
            # Create source file
            source_file = os.path.join(temp_dir, "source.bin")
            with open(source_file, 'wb') as f:
                f.write(file_content)
            
            # Calculate source checksum
            source_checksum = hashlib.sha256(file_content).hexdigest()
            
            # Transfer with specified chunk size
            dest_file = os.path.join(temp_dir, "dest.bin")
            result = plugin.upload_file(source_file, dest_file, chunk_size=chunk_size)
            
            # Property: Transfer must succeed
            assert result.success is True, \
                f"Transfer with chunk size {chunk_size} must succeed. Error: {result.error}"
            
            # Property: Checksum must match regardless of chunk size
            assert result.checksum == source_checksum, \
                f"Checksum must match with chunk size {chunk_size}. Source: {source_checksum}, Dest: {result.checksum}"
            
            # Property: Content must be identical
            with open(dest_file, 'rb') as f:
                dest_content = f.read()
            assert dest_content == file_content, \
                f"Content must be identical with chunk size {chunk_size}"
        
        finally:
            shutil.rmtree(temp_dir)
    
    @given(
        file_content=st.binary(min_size=1000, max_size=50000),  # 1KB to 50KB
        partial_size=st.integers(min_value=500, max_value=25000)  # Partial transfer size
    )
    @settings(
        max_examples=10, 
        deadline=None, 
        suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large, HealthCheck.too_slow]
    )
    def test_property_resume_preserves_integrity(self, file_content, partial_size):
        """
        **Validates: Requirements 1.3, 1.5**
        
        Property 3: File Transfer Integrity - Resume must preserve content
        
        For all file contents and partial transfer sizes:
        - Resume from partial transfer MUST complete successfully
        - Final checksum MUST match source
        - Content MUST be identical to source
        """
        # Ensure partial size is less than file size
        if partial_size >= len(file_content):
            partial_size = len(file_content) // 2
        
        temp_dir = tempfile.mkdtemp()
        try:
            plugin = FileTransferPlugin()
            
            # Create source file
            source_file = os.path.join(temp_dir, "source.bin")
            with open(source_file, 'wb') as f:
                f.write(file_content)
            
            # Calculate source checksum
            source_checksum = hashlib.sha256(file_content).hexdigest()
            
            # Create partial file (simulate interrupted transfer)
            dest_file = os.path.join(temp_dir, "dest.bin")
            partial_file = dest_file + ".partial"
            with open(partial_file, 'wb') as f:
                f.write(file_content[:partial_size])
            
            # Resume transfer
            result = plugin.upload_file(source_file, dest_file)
            
            # Property: Resume must succeed
            assert result.success is True, \
                f"Resume from {partial_size} bytes must succeed. Error: {result.error}"
            
            # Property: Final checksum must match source
            assert result.checksum == source_checksum, \
                f"Resumed transfer checksum must match source. Source: {source_checksum}, Dest: {result.checksum}"
            
            # Property: Final content must match source
            with open(dest_file, 'rb') as f:
                dest_content = f.read()
            assert dest_content == file_content, \
                "Resumed transfer content must match source"
            
            # Property: Partial file must be removed
            assert not os.path.exists(partial_file), \
                "Partial file must be removed after successful resume"
        
        finally:
            shutil.rmtree(temp_dir)
