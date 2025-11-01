"""
Async helper utilities for Flask
Properly handles async operations without blocking the main thread
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import threading

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)


def run_async_in_thread(async_func, *args, **kwargs):
    """
    Run an async function in a separate thread with its own event loop
    This prevents "event loop already running" errors in Flask
    """
    def run_in_new_loop():
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()

    # Submit to thread pool and wait for result
    future = executor.submit(run_in_new_loop)
    return future.result(timeout=300)  # 5 minute timeout


def async_route(f):
    """
    Decorator for Flask routes that need to call async functions
    Usage:
        @app.route('/test')
        @async_route
        async def test_route():
            result = await some_async_function()
            return jsonify(result)
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        return run_async_in_thread(f, *args, **kwargs)
    return wrapper
