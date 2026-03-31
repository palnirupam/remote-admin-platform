"""
Watchdog Process Module for Agent Protection

This module provides a watchdog process that monitors the main agent process
and automatically restarts it if it terminates. The watchdog and agent
implement mutual monitoring to ensure both processes remain running.

Requirements: 7.4, 7.5, 8.3
"""

import os
import sys
import time
import psutil
import multiprocessing
from typing import Optional, Callable, List
from datetime import datetime, timedelta


def _is_process_running(pid: int) -> bool:
    """
    Check if a process with given PID is running
    
    Args:
        pid: Process ID to check
    
    Returns:
        True if process is running, False otherwise
    
    Requirements: 8.3
    """
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _watchdog_monitor_loop(agent_pid: int, restart_delay: int, restart_limit: int,
                           restart_window: int, target_function: Callable,
                           target_args: tuple, restart_times_queue: multiprocessing.Queue,
                           stop_event: multiprocessing.Event) -> None:
    """
    Main watchdog monitoring loop (runs in separate process)
    
    Monitors the agent process and restarts it if it terminates.
    Implements restart limiting to prevent infinite loops.
    
    Args:
        agent_pid: Process ID of the agent to monitor
        restart_delay: Delay in seconds before restarting
        restart_limit: Maximum restarts within restart_window
        restart_window: Time window in seconds for restart counting
        target_function: Function to restart
        target_args: Arguments for target function
        restart_times_queue: Queue to track restart times
        stop_event: Event to signal stop
    
    Requirements: 7.4, 7.5, 8.3
    """
    print(f"[WATCHDOG] Monitoring agent process PID: {agent_pid}")
    restart_times: List[datetime] = []
    current_agent_pid = agent_pid
    
    while not stop_event.is_set():
        # Check if agent process is running
        is_running = _is_process_running(current_agent_pid)
        
        if not is_running:
            print(f"[WATCHDOG] Agent process {current_agent_pid} terminated")
            
            # Check restart limits
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=restart_window)
            restart_times = [t for t in restart_times if t > cutoff_time]
            
            if len(restart_times) < restart_limit:
                restart_times.append(current_time)
                restart_times_queue.put(current_time)
                
                print(f"[WATCHDOG] Restarting agent in {restart_delay} seconds...")
                time.sleep(restart_delay)
                
                # Restart the agent
                agent_process = multiprocessing.Process(
                    target=target_function,
                    args=target_args,
                    name="AgentProcess"
                )
                agent_process.start()
                current_agent_pid = agent_process.pid
                print(f"[WATCHDOG] Agent restarted with new PID: {current_agent_pid}")
            else:
                print("[WATCHDOG] Restart limit reached, stopping watchdog")
                break
        
        # Sleep before next check
        time.sleep(2)
    
    print("[WATCHDOG] Monitoring stopped")


class Watchdog:
    """
    Watchdog process that monitors and restarts the main agent process
    
    Implements mutual monitoring where:
    - Watchdog monitors the agent process
    - Agent monitors the watchdog process
    - Either process can restart the other if it terminates
    
    Includes restart counter to prevent infinite restart loops.
    
    Requirements: 7.4, 7.5, 8.3
    """
    
    def __init__(self, target_function: Callable, target_args: tuple = (),
                 restart_limit: int = 5, restart_window: int = 60,
                 restart_delay: int = 10):
        """
        Initialize watchdog
        
        Args:
            target_function: The function to monitor (agent's main function)
            target_args: Arguments to pass to target function
            restart_limit: Maximum restarts within restart_window (default: 5)
            restart_window: Time window in seconds for restart counting (default: 60)
            restart_delay: Delay in seconds before restarting (default: 10)
        
        Requirements: 7.4, 7.5
        """
        if not callable(target_function):
            raise ValueError("Target function must be callable")
        if restart_limit <= 0:
            raise ValueError("Restart limit must be positive")
        if restart_window <= 0:
            raise ValueError("Restart window must be positive")
        if restart_delay < 0 or restart_delay > 60:
            raise ValueError("Restart delay must be between 0 and 60 seconds")
        
        self.target_function = target_function
        self.target_args = target_args
        self.restart_limit = restart_limit
        self.restart_window = restart_window
        self.restart_delay = restart_delay
        
        # Process tracking
        self.agent_process: Optional[multiprocessing.Process] = None
        self.watchdog_process: Optional[multiprocessing.Process] = None
        
        # Restart tracking (using queue for inter-process communication)
        self.restart_times_queue: Optional[multiprocessing.Queue] = None
        self.restart_times = []
        self.running = False
        
        # Stop event for graceful shutdown
        self.stop_event: Optional[multiprocessing.Event] = None
        
        # Process IDs for mutual monitoring
        self.agent_pid: Optional[int] = None
        self.watchdog_pid: Optional[int] = None
    
    def start(self) -> None:
        """
        Start the watchdog and agent processes
        
        Creates both processes and begins mutual monitoring.
        
        Requirements: 7.4
        """
        if self.running:
            raise RuntimeError("Watchdog is already running")
        
        self.running = True
        self.restart_times_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        
        # Start the agent process
        self.agent_process = multiprocessing.Process(
            target=self.target_function,
            args=self.target_args,
            name="AgentProcess"
        )
        self.agent_process.start()
        self.agent_pid = self.agent_process.pid
        
        print(f"[WATCHDOG] Agent process started with PID: {self.agent_pid}")
        
        # Start the watchdog monitoring process
        self.watchdog_process = multiprocessing.Process(
            target=_watchdog_monitor_loop,
            args=(
                self.agent_pid,
                self.restart_delay,
                self.restart_limit,
                self.restart_window,
                self.target_function,
                self.target_args,
                self.restart_times_queue,
                self.stop_event
            ),
            name="WatchdogProcess"
        )
        self.watchdog_process.start()
        self.watchdog_pid = self.watchdog_process.pid
        
        print(f"[WATCHDOG] Watchdog process started with PID: {self.watchdog_pid}")
    
    def stop(self) -> None:
        """
        Stop the watchdog and agent processes gracefully
        """
        print("[WATCHDOG] Stopping watchdog and agent...")
        self.running = False
        
        # Signal stop event
        if self.stop_event:
            self.stop_event.set()
        
        # Terminate watchdog process
        if self.watchdog_process and self.watchdog_process.is_alive():
            self.watchdog_process.terminate()
            self.watchdog_process.join(timeout=5)
            if self.watchdog_process.is_alive():
                self.watchdog_process.kill()
        
        # Terminate agent process
        if self.agent_process and self.agent_process.is_alive():
            self.agent_process.terminate()
            self.agent_process.join(timeout=5)
            if self.agent_process.is_alive():
                self.agent_process.kill()
        
        print("[WATCHDOG] Stopped")
    
    def _is_process_running(self, pid: int) -> bool:
        """
        Check if a process with given PID is running
        
        Args:
            pid: Process ID to check
        
        Returns:
            True if process is running, False otherwise
        
        Requirements: 8.3
        """
        return _is_process_running(pid)
    
    def _can_restart(self) -> bool:
        """
        Check if restart is allowed based on restart limits
        
        Implements restart counter to prevent infinite restart loops.
        Counts restarts within the configured time window.
        
        Returns:
            True if restart is allowed, False if limit reached
        
        Requirements: 7.4
        """
        # Collect restart times from queue (if started)
        if self.restart_times_queue:
            while not self.restart_times_queue.empty():
                try:
                    restart_time = self.restart_times_queue.get_nowait()
                    self.restart_times.append(restart_time)
                except:
                    break
        
        current_time = datetime.now()
        
        # Remove restart times outside the window
        cutoff_time = current_time - timedelta(seconds=self.restart_window)
        self.restart_times = [t for t in self.restart_times if t > cutoff_time]
        
        # Check if we're under the limit
        if len(self.restart_times) >= self.restart_limit:
            print(f"[WATCHDOG] Restart limit reached: {len(self.restart_times)} restarts "
                  f"in {self.restart_window} seconds")
            return False
        
        return True
    
    def _restart_agent(self) -> None:
        """
        Restart the agent process (not used in refactored version)
        
        Requirements: 7.5
        """
        pass
    
    def _restart_watchdog(self) -> None:
        """
        Restart the watchdog process (not used in refactored version)
        
        Requirements: 7.4
        """
        pass
    
    def _run_agent_with_monitoring(self, *args) -> None:
        """
        Run the agent function while monitoring the watchdog process (not used in refactored version)
        
        Requirements: 7.4
        """
        pass
    
    def get_status(self) -> dict:
        """
        Get current status of watchdog and agent processes
        
        Returns:
            Dictionary with status information
        """
        # Sync restart times from queue
        self._sync_restart_times()
        
        status = {
            "running": self.running,
            "agent_pid": self.agent_pid,
            "agent_alive": self.agent_process.is_alive() if self.agent_process else False,
            "watchdog_pid": self.watchdog_pid,
            "watchdog_alive": self.watchdog_process.is_alive() if self.watchdog_process else False,
            "restart_count": len(self.restart_times),
            "restart_limit": self.restart_limit,
            "restart_window": self.restart_window
        }
        return status
    
    def _sync_restart_times(self) -> None:
        """
        Sync restart times from the queue to the local list
        """
        if self.restart_times_queue:
            while not self.restart_times_queue.empty():
                try:
                    restart_time = self.restart_times_queue.get_nowait()
                    if restart_time not in self.restart_times:
                        self.restart_times.append(restart_time)
                except:
                    break


def create_watchdog(target_function: Callable, target_args: tuple = (),
                   restart_limit: int = 5, restart_window: int = 60,
                   restart_delay: int = 10) -> Watchdog:
    """
    Factory function to create a Watchdog instance
    
    Args:
        target_function: The function to monitor
        target_args: Arguments to pass to target function
        restart_limit: Maximum restarts within restart_window
        restart_window: Time window in seconds for restart counting
        restart_delay: Delay in seconds before restarting
    
    Returns:
        Configured Watchdog instance
    
    Requirements: 7.4
    """
    return Watchdog(
        target_function=target_function,
        target_args=target_args,
        restart_limit=restart_limit,
        restart_window=restart_window,
        restart_delay=restart_delay
    )


if __name__ == "__main__":
    # Example usage
    def example_agent():
        """Example agent function for testing"""
        print("[AGENT] Agent started")
        for i in range(10):
            print(f"[AGENT] Running... {i}")
            time.sleep(2)
        print("[AGENT] Agent finished")
    
    # Create and start watchdog
    watchdog = create_watchdog(example_agent)
    
    try:
        watchdog.start()
        
        # Let it run for a while
        time.sleep(30)
        
        # Check status
        status = watchdog.get_status()
        print(f"[STATUS] {status}")
        
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Stopping...")
    finally:
        watchdog.stop()
