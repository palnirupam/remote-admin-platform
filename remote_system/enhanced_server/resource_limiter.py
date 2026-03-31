"""
Resource Limiter Module for Remote System Enhancement

This module provides resource limits for command queues, concurrent transfers,
and screenshot rate limiting to prevent resource exhaustion.

Requirements: 23.7
"""

import time
import threading
from typing import Dict, Optional
from collections import deque


class ResourceLimiter:
    """
    Resource limiter for performance and stability
    
    Implements limits for:
    - Command queue size (max 100 per agent)
    - Concurrent file transfers (max 3 per agent)
    - Screenshot rate limiting (max 1 per 5 seconds per agent)
    """
    
    def __init__(self):
        """Initialize resource limiter"""
        # Command queue limits
        self.max_queue_size = 100
        self.command_queues: Dict[str, deque] = {}
        
        # File transfer limits
        self.max_concurrent_transfers = 3
        self.active_transfers: Dict[str, int] = {}
        
        # Screenshot rate limiting
        self.screenshot_rate_limit = 5.0  # seconds
        self.last_screenshot_time: Dict[str, float] = {}
        
        self.lock = threading.Lock()
    
    def can_queue_command(self, agent_id: str) -> bool:
        """
        Check if command can be queued for agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if queue has space, False if full
        
        Requirements: 23.7
        """
        with self.lock:
            if agent_id not in self.command_queues:
                return True
            
            return len(self.command_queues[agent_id]) < self.max_queue_size
    
    def queue_command(self, agent_id: str, command: Dict) -> bool:
        """
        Queue command for agent with size limit
        
        Args:
            agent_id: Agent identifier
            command: Command dictionary
        
        Returns:
            True if queued successfully, False if queue is full
        
        Requirements: 23.7
        """
        with self.lock:
            if agent_id not in self.command_queues:
                self.command_queues[agent_id] = deque()
            
            queue = self.command_queues[agent_id]
            
            if len(queue) >= self.max_queue_size:
                return False
            
            queue.append(command)
            return True
    
    def dequeue_command(self, agent_id: str) -> Optional[Dict]:
        """
        Dequeue next command for agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Command dictionary or None if queue is empty
        """
        with self.lock:
            if agent_id not in self.command_queues:
                return None
            
            queue = self.command_queues[agent_id]
            
            if len(queue) == 0:
                return None
            
            return queue.popleft()
    
    def get_queue_size(self, agent_id: str) -> int:
        """
        Get current queue size for agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Number of queued commands
        """
        with self.lock:
            if agent_id not in self.command_queues:
                return 0
            return len(self.command_queues[agent_id])
    
    def clear_queue(self, agent_id: str) -> None:
        """
        Clear command queue for agent
        
        Args:
            agent_id: Agent identifier
        """
        with self.lock:
            if agent_id in self.command_queues:
                self.command_queues[agent_id].clear()
    
    def can_start_transfer(self, agent_id: str) -> bool:
        """
        Check if file transfer can be started for agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if transfer can start, False if limit reached
        
        Requirements: 23.7
        """
        with self.lock:
            active_count = self.active_transfers.get(agent_id, 0)
            return active_count < self.max_concurrent_transfers
    
    def start_transfer(self, agent_id: str) -> bool:
        """
        Register start of file transfer
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if transfer started, False if limit reached
        
        Requirements: 23.7
        """
        with self.lock:
            active_count = self.active_transfers.get(agent_id, 0)
            
            if active_count >= self.max_concurrent_transfers:
                return False
            
            self.active_transfers[agent_id] = active_count + 1
            return True
    
    def end_transfer(self, agent_id: str) -> None:
        """
        Register end of file transfer
        
        Args:
            agent_id: Agent identifier
        """
        with self.lock:
            if agent_id in self.active_transfers:
                self.active_transfers[agent_id] = max(0, self.active_transfers[agent_id] - 1)
    
    def get_active_transfers(self, agent_id: str) -> int:
        """
        Get number of active transfers for agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Number of active transfers
        """
        with self.lock:
            return self.active_transfers.get(agent_id, 0)
    
    def can_take_screenshot(self, agent_id: str) -> bool:
        """
        Check if screenshot can be taken (rate limiting)
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if screenshot allowed, False if rate limited
        
        Requirements: 23.7
        """
        with self.lock:
            current_time = time.time()
            last_time = self.last_screenshot_time.get(agent_id, 0)
            
            return (current_time - last_time) >= self.screenshot_rate_limit
    
    def record_screenshot(self, agent_id: str) -> bool:
        """
        Record screenshot taken (for rate limiting)
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if screenshot recorded, False if rate limited
        
        Requirements: 23.7
        """
        with self.lock:
            current_time = time.time()
            last_time = self.last_screenshot_time.get(agent_id, 0)
            
            if (current_time - last_time) < self.screenshot_rate_limit:
                return False
            
            self.last_screenshot_time[agent_id] = current_time
            return True
    
    def get_time_until_next_screenshot(self, agent_id: str) -> float:
        """
        Get time until next screenshot is allowed
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Seconds until next screenshot allowed (0 if allowed now)
        """
        with self.lock:
            current_time = time.time()
            last_time = self.last_screenshot_time.get(agent_id, 0)
            time_since_last = current_time - last_time
            
            if time_since_last >= self.screenshot_rate_limit:
                return 0.0
            
            return self.screenshot_rate_limit - time_since_last
    
    def cleanup_agent(self, agent_id: str) -> None:
        """
        Cleanup resources for disconnected agent
        
        Args:
            agent_id: Agent identifier
        """
        with self.lock:
            if agent_id in self.command_queues:
                del self.command_queues[agent_id]
            if agent_id in self.active_transfers:
                del self.active_transfers[agent_id]
            if agent_id in self.last_screenshot_time:
                del self.last_screenshot_time[agent_id]
    
    def get_resource_stats(self) -> Dict[str, any]:
        """
        Get resource usage statistics
        
        Returns:
            Dictionary with resource statistics
        """
        with self.lock:
            total_queued = sum(len(q) for q in self.command_queues.values())
            total_transfers = sum(self.active_transfers.values())
            
            return {
                'total_queued_commands': total_queued,
                'agents_with_queued_commands': len(self.command_queues),
                'total_active_transfers': total_transfers,
                'agents_with_active_transfers': len([c for c in self.active_transfers.values() if c > 0]),
                'max_queue_size': self.max_queue_size,
                'max_concurrent_transfers': self.max_concurrent_transfers,
                'screenshot_rate_limit': self.screenshot_rate_limit
            }
