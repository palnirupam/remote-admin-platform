"""
Compression Utilities for Remote System Enhancement

This module provides data compression for large command results
to reduce bandwidth usage and improve performance.

Requirements: 23.6
"""

import gzip
import json
from typing import Any, Dict, Union


class CompressionUtils:
    """
    Compression utilities for command results and data transfer
    
    Uses gzip compression for data larger than 1KB threshold
    """
    
    # Compression threshold in bytes (1KB)
    COMPRESSION_THRESHOLD = 1024
    
    @staticmethod
    def should_compress(data: Union[str, bytes]) -> bool:
        """
        Determine if data should be compressed
        
        Args:
            data: Data to check (string or bytes)
        
        Returns:
            True if data size exceeds compression threshold
        
        Requirements: 23.6
        """
        if isinstance(data, str):
            data_size = len(data.encode('utf-8'))
        else:
            data_size = len(data)
        
        return data_size > CompressionUtils.COMPRESSION_THRESHOLD
    
    @staticmethod
    def compress_data(data: Union[str, bytes], compression_level: int = 6) -> bytes:
        """
        Compress data using gzip
        
        Args:
            data: Data to compress (string or bytes)
            compression_level: Compression level (1-9, default 6)
        
        Returns:
            Compressed data as bytes
        
        Requirements: 23.6
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return gzip.compress(data, compresslevel=compression_level)
    
    @staticmethod
    def decompress_data(compressed_data: bytes) -> bytes:
        """
        Decompress gzip-compressed data
        
        Args:
            compressed_data: Compressed data as bytes
        
        Returns:
            Decompressed data as bytes
        
        Requirements: 23.6
        """
        return gzip.decompress(compressed_data)
    
    @staticmethod
    def compress_command_result(result: Any) -> Dict[str, Any]:
        """
        Compress command result if it exceeds threshold
        
        Args:
            result: Command result (any JSON-serializable type)
        
        Returns:
            Dictionary with compressed data or original result
            Format: {
                'compressed': bool,
                'data': bytes or original result,
                'original_size': int (if compressed),
                'compressed_size': int (if compressed)
            }
        
        Requirements: 23.6
        """
        # Serialize result to JSON
        result_json = json.dumps(result)
        result_bytes = result_json.encode('utf-8')
        original_size = len(result_bytes)
        
        # Check if compression is beneficial
        if CompressionUtils.should_compress(result_bytes):
            compressed = CompressionUtils.compress_data(result_bytes)
            compressed_size = len(compressed)
            
            # Only use compression if it actually reduces size
            if compressed_size < original_size:
                return {
                    'compressed': True,
                    'data': compressed,
                    'original_size': original_size,
                    'compressed_size': compressed_size
                }
        
        # Return uncompressed if below threshold or compression doesn't help
        return {
            'compressed': False,
            'data': result,
            'original_size': original_size
        }
    
    @staticmethod
    def decompress_command_result(compressed_result: Dict[str, Any]) -> Any:
        """
        Decompress command result if it was compressed
        
        Args:
            compressed_result: Result dictionary from compress_command_result()
        
        Returns:
            Original command result
        
        Requirements: 23.6
        """
        if not compressed_result.get('compressed', False):
            return compressed_result['data']
        
        # Decompress and deserialize
        decompressed_bytes = CompressionUtils.decompress_data(compressed_result['data'])
        result_json = decompressed_bytes.decode('utf-8')
        return json.loads(result_json)
