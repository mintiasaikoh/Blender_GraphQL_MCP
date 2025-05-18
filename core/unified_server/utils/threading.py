"""
Thread management utilities for Blender GraphQL MCP unified server.
Provides utilities for managing threads, particularly for Blender main thread execution.
"""

import threading
import time
import functools
import inspect
import queue
from typing import Any, Callable, Optional, TypeVar, cast, Dict, List, Tuple

# Import logger
from .logging import get_logger

logger = get_logger("threading")

# Type variable for function return type
T = TypeVar('T')

# Global registry of running threads for tracking
_running_threads: Dict[str, threading.Thread] = {}
_thread_registry_lock = threading.RLock()


def register_thread(thread: threading.Thread, name: Optional[str] = None) -> str:
    """
    Register a thread for tracking.
    
    Args:
        thread: Thread to register
        name: Optional name for the thread. If None, uses thread name or generates one
        
    Returns:
        Thread ID used for tracking
    """
    with _thread_registry_lock:
        thread_id = name or thread.name or f"thread-{id(thread)}"
        _running_threads[thread_id] = thread
        return thread_id


def unregister_thread(thread_id: str) -> None:
    """
    Unregister a thread from tracking.
    
    Args:
        thread_id: ID of thread to unregister
    """
    with _thread_registry_lock:
        if thread_id in _running_threads:
            del _running_threads[thread_id]


def get_thread(thread_id: str) -> Optional[threading.Thread]:
    """
    Get a registered thread by ID.
    
    Args:
        thread_id: ID of thread to retrieve
        
    Returns:
        Thread if found, None otherwise
    """
    with _thread_registry_lock:
        return _running_threads.get(thread_id)


def list_threads() -> List[Tuple[str, threading.Thread]]:
    """
    List all registered threads.
    
    Returns:
        List of (thread_id, thread) tuples
    """
    with _thread_registry_lock:
        return list(_running_threads.items())


def shutdown_all_threads(timeout: float = 5.0) -> None:
    """
    Attempt to gracefully shut down all registered threads.
    
    Args:
        timeout: Maximum time to wait for each thread to terminate
    """
    thread_list = list_threads()
    
    for thread_id, thread in thread_list:
        logger.debug(f"Shutting down thread: {thread_id}")
        
        # If thread has a stop method, call it
        if hasattr(thread, 'stop') and callable(thread.stop):
            try:
                thread.stop()
            except Exception as e:
                logger.error(f"Error stopping thread {thread_id}: {e}")
        
        # Wait for thread to terminate
        if thread.is_alive():
            thread.join(timeout)
            
        # Unregister thread regardless of whether it terminated
        unregister_thread(thread_id)


class StoppableThread(threading.Thread):
    """
    Thread class with a stop event and method.
    Base class for server threads that need graceful termination.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        
        # Auto-register thread when created
        self.thread_id = register_thread(self, self.name)
        
    def stop(self) -> None:
        """Signal the thread to stop."""
        self._stop_event.set()
        
    def stopped(self) -> bool:
        """Check if stop has been signaled."""
        return self._stop_event.is_set()
    
    def run(self) -> None:
        """Override to clean up thread registry on exit."""
        try:
            super().run()
        finally:
            unregister_thread(self.thread_id)


# Blender Main Thread Execution
# =============================

# Queue for main thread execution
_main_thread_queue = queue.Queue()
_main_thread_running = threading.Event()
_main_thread = None


def is_in_main_thread() -> bool:
    """
    Check if the current thread is the main Blender thread.
    
    Returns:
        True if in main thread, False otherwise
    """
    if _main_thread is None:
        # We haven't set the main thread, so assume this is the main thread
        return True
    
    return threading.current_thread() is _main_thread


def execute_in_main_thread(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure a function is executed in the main Blender thread.
    
    Args:
        func: Function to execute in main thread
        
    Returns:
        Wrapped function that executes in main thread
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # If already in main thread, execute directly
        if is_in_main_thread():
            return func(*args, **kwargs)
        
        # Check if main thread processing is running
        if not _main_thread_running.is_set():
            logger.warning("Main thread execution queue is not running. Starting on-demand.")
            start_main_thread_processing()
        
        # Create future for result
        result_event = threading.Event()
        result_container = {"result": None, "exception": None}
        
        # Define task to run in main thread
        def main_thread_task():
            try:
                result_container["result"] = func(*args, **kwargs)
            except Exception as e:
                result_container["exception"] = e
            finally:
                result_event.set()
        
        # Queue task for main thread
        _main_thread_queue.put(main_thread_task)
        
        # Wait for result
        result_event.wait()
        
        # Raise exception if one occurred
        if result_container["exception"] is not None:
            raise result_container["exception"]
        
        return result_container["result"]
    
    return wrapper


def start_main_thread_processing() -> None:
    """
    Start processing main thread queue.
    This should be called from the main Blender thread.
    """
    global _main_thread
    
    # Set current thread as main thread
    _main_thread = threading.current_thread()
    
    # Signal that main thread processing is running
    _main_thread_running.set()
    
    logger.info("Started main thread execution queue")


def process_main_thread_queue(timeout: float = 0.0) -> bool:
    """
    Process a single item from the main thread queue.
    
    Args:
        timeout: Time to wait for an item (0 = non-blocking)
        
    Returns:
        True if an item was processed, False if queue was empty
    """
    if not is_in_main_thread():
        logger.warning("process_main_thread_queue called from non-main thread")
        return False
    
    try:
        # Get a task from the queue
        task = _main_thread_queue.get(block=timeout > 0, timeout=timeout)
        
        # Execute the task
        task()
        
        # Mark task as done
        _main_thread_queue.task_done()
        
        return True
    except queue.Empty:
        return False


def stop_main_thread_processing() -> None:
    """
    Stop processing main thread queue.
    """
    _main_thread_running.clear()
    logger.info("Stopped main thread execution queue")