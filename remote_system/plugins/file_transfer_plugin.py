"""
File Transfer Plugin for Enhanced Agent

Handles bidirectional file transfer between server and agent with chunked
transfer, checksum validation, and resume capability.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 20.7
"""

import os
import hashlib
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from remote_system.enhanced_agent.plugin_manager import Plugin


@dataclass
class TransferResult:
    """
    Result of a file transfer operation
    
    Attributes:
        success: Whether the transfer completed successfully
        bytes_transferred: Number of bytes transferred
        total_bytes: Total size of the file
        checksum: SHA256 checksum of the file
        error: Error message if transfer failed
        transfer_time: Time taken for transfer in seconds
    """
    success: bool
    bytes_transferred: int
    total_bytes: int
    checksum: str
    error: Optional[str]
    transfer_time: float


@dataclass
class FileInfo:
    """
    Information about a file
    
    Attributes:
        name: File name
        path: Full file path
        size: File size in bytes
        modified_time: Last modification timestamp
        is_directory: Whether this is a directory
    """
    name: str
    path: str
    size: int
    modified_time: float
    is_directory: bool


class FileTransferPlugin(Plugin):
    """
    File Transfer Plugin
    
    Provides file upload, download, directory listing, and hash calculation.
    Implements chunked transfer with retry logic and resume capability.
    
    Requirements:
    - 1.1: Transfer file from server to agent in chunks
    - 1.2: Transfer file from agent to server in chunks
    - 1.3: Verify data integrity using checksum validation
    - 1.4: Support resuming from last successful chunk
    - 1.5: Report error on checksum validation failure
    - 1.6: Return file names, sizes, and modification times
    - 1.7: Use chunk sizes between 4KB and 1MB
    - 20.7: Preserve partial data and support resume on retry
    """
    
    def __init__(self):
        """Initialize the file transfer plugin"""
        self.default_chunk_size = 65536  # 64KB default
        self.min_chunk_size = 4096  # 4KB minimum
        self.max_chunk_size = 1048576  # 1MB maximum
        self.max_retries = 3
    
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the plugin with the given arguments
        
        Args:
            args: Dictionary containing:
                - action: 'upload', 'download', 'list_directory', or 'get_file_hash'
                - Additional args based on action
                
        Returns:
            Result based on the action
            
        Raises:
            ValueError: If action is invalid or required args are missing
        """
        action = args.get('action')
        
        if action == 'upload':
            return self._upload_file(args)
        elif action == 'download':
            return self._download_file(args)
        elif action == 'list_directory':
            return self._list_directory(args)
        elif action == 'get_file_hash':
            return self._get_file_hash(args)
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def get_name(self) -> str:
        """
        Get the name of the plugin
        
        Returns:
            The plugin name
        """
        return "file_transfer"
    
    def get_required_arguments(self) -> List[str]:
        """
        Get the list of required argument names
        
        Returns:
            List of required argument names
        """
        return ['action']
    
    def upload_file(self, local_path: str, remote_path: str, 
                   chunk_size: int = None) -> TransferResult:
        """
        Upload file from server to agent
        
        Implements chunked transfer with retry logic and resume capability.
        
        Args:
            local_path: Path to source file (on server)
            remote_path: Path to destination file (on agent)
            chunk_size: Size of chunks (4KB-1MB, default 64KB)
            
        Returns:
            TransferResult with transfer status and statistics
            
        Requirements: 1.1, 1.3, 1.4, 1.5, 1.7, 20.7
        """
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        
        # Validate chunk size (Requirement 1.7)
        chunk_size = max(self.min_chunk_size, min(chunk_size, self.max_chunk_size))
        
        start_time = time.time()
        
        try:
            # Check if source file exists
            if not os.path.exists(local_path):
                return TransferResult(
                    success=False,
                    bytes_transferred=0,
                    total_bytes=0,
                    checksum="",
                    error=f"Source file not found: {local_path}",
                    transfer_time=0.0
                )
            
            # Get file size
            total_bytes = os.path.getsize(local_path)
            bytes_transferred = 0
            
            # Check for partial file (Requirement 1.4, 20.7)
            partial_path = remote_path + ".partial"
            if os.path.exists(partial_path):
                bytes_transferred = os.path.getsize(partial_path)
            
            # Initialize checksum calculator
            checksum_calculator = hashlib.sha256()
            
            # Open source file
            with open(local_path, 'rb') as source_file:
                # Seek to resume position if resuming
                if bytes_transferred > 0:
                    source_file.seek(bytes_transferred)
                    # Recalculate checksum for already transferred data
                    with open(partial_path, 'rb') as partial_file:
                        while True:
                            chunk = partial_file.read(chunk_size)
                            if not chunk:
                                break
                            checksum_calculator.update(chunk)
                
                # Open destination file (append mode if resuming)
                mode = 'ab' if bytes_transferred > 0 else 'wb'
                with open(partial_path, mode) as dest_file:
                    # Transfer chunks (Requirement 1.1)
                    while bytes_transferred < total_bytes:
                        chunk = source_file.read(chunk_size)
                        if not chunk:
                            break
                        
                        chunk_size_actual = len(chunk)
                        
                        # Retry logic (max 3 retries per chunk)
                        retry_count = 0
                        success = False
                        
                        while retry_count < self.max_retries and not success:
                            try:
                                dest_file.write(chunk)
                                dest_file.flush()
                                checksum_calculator.update(chunk)
                                bytes_transferred += chunk_size_actual
                                success = True
                            except Exception as e:
                                retry_count += 1
                                if retry_count >= self.max_retries:
                                    return TransferResult(
                                        success=False,
                                        bytes_transferred=bytes_transferred,
                                        total_bytes=total_bytes,
                                        checksum="",
                                        error=f"Chunk write failed after {self.max_retries} retries: {str(e)}",
                                        transfer_time=time.time() - start_time
                                    )
                                time.sleep(1)
            
            # Calculate final checksum
            final_checksum = checksum_calculator.hexdigest()
            
            # Verify checksum (Requirement 1.3)
            source_checksum = self.get_file_hash(local_path)
            
            if final_checksum != source_checksum:
                # Checksum mismatch (Requirement 1.5)
                return TransferResult(
                    success=False,
                    bytes_transferred=bytes_transferred,
                    total_bytes=total_bytes,
                    checksum=final_checksum,
                    error="Checksum mismatch: transfer corrupted",
                    transfer_time=time.time() - start_time
                )
            
            # Rename partial file to final name
            if os.path.exists(remote_path):
                os.remove(remote_path)
            os.rename(partial_path, remote_path)
            
            return TransferResult(
                success=True,
                bytes_transferred=bytes_transferred,
                total_bytes=total_bytes,
                checksum=final_checksum,
                error=None,
                transfer_time=time.time() - start_time
            )
        
        except Exception as e:
            return TransferResult(
                success=False,
                bytes_transferred=bytes_transferred if 'bytes_transferred' in locals() else 0,
                total_bytes=total_bytes if 'total_bytes' in locals() else 0,
                checksum="",
                error=f"Upload failed: {str(e)}",
                transfer_time=time.time() - start_time
            )

    
    def download_file(self, remote_path: str, local_path: str, 
                     chunk_size: int = None) -> TransferResult:
        """
        Download file from agent to server
        
        Implements chunked transfer with checksum validation and resume capability.
        
        Args:
            remote_path: Path to source file (on agent)
            local_path: Path to destination file (on server)
            chunk_size: Size of chunks (4KB-1MB, default 64KB)
            
        Returns:
            TransferResult with transfer status and statistics
            
        Requirements: 1.2, 1.3, 1.4, 1.5, 1.7, 20.7
        """
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        
        # Validate chunk size (Requirement 1.7)
        chunk_size = max(self.min_chunk_size, min(chunk_size, self.max_chunk_size))
        
        start_time = time.time()
        
        try:
            # Check if source file exists
            if not os.path.exists(remote_path):
                return TransferResult(
                    success=False,
                    bytes_transferred=0,
                    total_bytes=0,
                    checksum="",
                    error=f"Source file not found: {remote_path}",
                    transfer_time=0.0
                )
            
            # Get file size
            total_bytes = os.path.getsize(remote_path)
            bytes_transferred = 0
            
            # Check for partial file (Requirement 1.4, 20.7)
            partial_path = local_path + ".partial"
            if os.path.exists(partial_path):
                bytes_transferred = os.path.getsize(partial_path)
            
            # Initialize checksum calculator
            checksum_calculator = hashlib.sha256()
            
            # Open source file
            with open(remote_path, 'rb') as source_file:
                # Seek to resume position if resuming
                if bytes_transferred > 0:
                    source_file.seek(bytes_transferred)
                    # Recalculate checksum for already transferred data
                    with open(partial_path, 'rb') as partial_file:
                        while True:
                            chunk = partial_file.read(chunk_size)
                            if not chunk:
                                break
                            checksum_calculator.update(chunk)
                
                # Open destination file (append mode if resuming)
                mode = 'ab' if bytes_transferred > 0 else 'wb'
                with open(partial_path, mode) as dest_file:
                    # Transfer chunks (Requirement 1.2)
                    while bytes_transferred < total_bytes:
                        chunk = source_file.read(chunk_size)
                        if not chunk:
                            break
                        
                        chunk_size_actual = len(chunk)
                        
                        # Retry logic (max 3 retries per chunk)
                        retry_count = 0
                        success = False
                        
                        while retry_count < self.max_retries and not success:
                            try:
                                dest_file.write(chunk)
                                dest_file.flush()
                                checksum_calculator.update(chunk)
                                bytes_transferred += chunk_size_actual
                                success = True
                            except Exception as e:
                                retry_count += 1
                                if retry_count >= self.max_retries:
                                    return TransferResult(
                                        success=False,
                                        bytes_transferred=bytes_transferred,
                                        total_bytes=total_bytes,
                                        checksum="",
                                        error=f"Chunk write failed after {self.max_retries} retries: {str(e)}",
                                        transfer_time=time.time() - start_time
                                    )
                                time.sleep(1)
            
            # Calculate final checksum
            final_checksum = checksum_calculator.hexdigest()
            
            # Verify checksum (Requirement 1.3)
            source_checksum = self.get_file_hash(remote_path)
            
            if final_checksum != source_checksum:
                # Checksum mismatch (Requirement 1.5)
                return TransferResult(
                    success=False,
                    bytes_transferred=bytes_transferred,
                    total_bytes=total_bytes,
                    checksum=final_checksum,
                    error="Checksum mismatch: transfer corrupted",
                    transfer_time=time.time() - start_time
                )
            
            # Rename partial file to final name
            if os.path.exists(local_path):
                os.remove(local_path)
            os.rename(partial_path, local_path)
            
            return TransferResult(
                success=True,
                bytes_transferred=bytes_transferred,
                total_bytes=total_bytes,
                checksum=final_checksum,
                error=None,
                transfer_time=time.time() - start_time
            )
        
        except Exception as e:
            return TransferResult(
                success=False,
                bytes_transferred=bytes_transferred if 'bytes_transferred' in locals() else 0,
                total_bytes=total_bytes if 'total_bytes' in locals() else 0,
                checksum="",
                error=f"Download failed: {str(e)}",
                transfer_time=time.time() - start_time
            )
    
    def list_directory(self, path: str) -> List[FileInfo]:
        """
        List files in a directory
        
        Args:
            path: Directory path to list
            
        Returns:
            List of FileInfo objects with file information
            
        Requirement: 1.6
        """
        try:
            if not os.path.exists(path):
                raise ValueError(f"Directory not found: {path}")
            
            if not os.path.isdir(path):
                raise ValueError(f"Path is not a directory: {path}")
            
            file_list = []
            
            for entry in os.listdir(path):
                entry_path = os.path.join(path, entry)
                
                try:
                    stat_info = os.stat(entry_path)
                    
                    file_info = FileInfo(
                        name=entry,
                        path=entry_path,
                        size=stat_info.st_size,
                        modified_time=stat_info.st_mtime,
                        is_directory=os.path.isdir(entry_path)
                    )
                    
                    file_list.append(file_info)
                
                except Exception:
                    # Skip files that can't be accessed
                    continue
            
            return file_list
        
        except Exception as e:
            raise ValueError(f"Failed to list directory: {str(e)}")
    
    def get_file_hash(self, path: str) -> str:
        """
        Calculate SHA256 hash of a file
        
        Args:
            path: Path to file
            
        Returns:
            SHA256 hash as hexadecimal string
            
        Raises:
            ValueError: If file doesn't exist or can't be read
        """
        try:
            if not os.path.exists(path):
                raise ValueError(f"File not found: {path}")
            
            if not os.path.isfile(path):
                raise ValueError(f"Path is not a file: {path}")
            
            sha256_hash = hashlib.sha256()
            
            with open(path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(65536), b''):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
        
        except Exception as e:
            raise ValueError(f"Failed to calculate hash: {str(e)}")
    
    def _upload_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle upload action
        
        Args:
            args: Dictionary containing local_path, remote_path, and optional chunk_size
            
        Returns:
            Dictionary representation of TransferResult
        """
        local_path = args.get('local_path')
        remote_path = args.get('remote_path')
        chunk_size = args.get('chunk_size')
        
        if not local_path:
            raise ValueError("local_path is required for upload")
        if not remote_path:
            raise ValueError("remote_path is required for upload")
        
        result = self.upload_file(local_path, remote_path, chunk_size)
        
        return {
            'success': result.success,
            'bytes_transferred': result.bytes_transferred,
            'total_bytes': result.total_bytes,
            'checksum': result.checksum,
            'error': result.error,
            'transfer_time': result.transfer_time
        }
    
    def _download_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle download action
        
        Args:
            args: Dictionary containing remote_path, local_path, and optional chunk_size
            
        Returns:
            Dictionary representation of TransferResult
        """
        remote_path = args.get('remote_path')
        local_path = args.get('local_path')
        chunk_size = args.get('chunk_size')
        
        if not remote_path:
            raise ValueError("remote_path is required for download")
        if not local_path:
            raise ValueError("local_path is required for download")
        
        result = self.download_file(remote_path, local_path, chunk_size)
        
        return {
            'success': result.success,
            'bytes_transferred': result.bytes_transferred,
            'total_bytes': result.total_bytes,
            'checksum': result.checksum,
            'error': result.error,
            'transfer_time': result.transfer_time
        }
    
    def _list_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle list_directory action
        
        Args:
            args: Dictionary containing path
            
        Returns:
            Dictionary with file list
        """
        path = args.get('path')
        
        if not path:
            raise ValueError("path is required for list_directory")
        
        file_list = self.list_directory(path)
        
        return {
            'files': [
                {
                    'name': f.name,
                    'path': f.path,
                    'size': f.size,
                    'modified_time': f.modified_time,
                    'is_directory': f.is_directory
                }
                for f in file_list
            ]
        }
    
    def _get_file_hash(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to handle get_file_hash action
        
        Args:
            args: Dictionary containing path
            
        Returns:
            Dictionary with hash
        """
        path = args.get('path')
        
        if not path:
            raise ValueError("path is required for get_file_hash")
        
        file_hash = self.get_file_hash(path)
        
        return {
            'path': path,
            'hash': file_hash,
            'algorithm': 'SHA256'
        }
