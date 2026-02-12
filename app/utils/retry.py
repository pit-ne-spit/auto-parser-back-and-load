"""Retry mechanism for API calls."""

import asyncio
import time
from typing import Callable, TypeVar, Optional, Any, Tuple
from functools import wraps
from datetime import datetime, timedelta

from app.utils.logger import logger
from app.utils.config import config

T = TypeVar('T')


def _get_retry_settings(
    max_attempts: Optional[int] = None,
    interval_seconds: Optional[int] = None,
    total_timeout_seconds: Optional[int] = None
) -> Tuple[int, int, int]:
    """
    Get retry settings from config, considering test mode.
    
    Args:
        max_attempts: Override for max attempts
        interval_seconds: Override for interval
        total_timeout_seconds: Override for total timeout
        
    Returns:
        Tuple of (max_attempts, interval_seconds, total_timeout_seconds)
    """
    retry_config = config.get_retry_config()
    api_config = config.get_api_config()
    
    # Check if test mode is enabled
    test_mode = retry_config.get('test_mode', False)
    
    if test_mode:
        max_att = max_attempts or retry_config.get('test_max_attempts', 3)
        interval = interval_seconds or retry_config.get('test_interval_seconds', 5)
        
        # Calculate total timeout considering HTTP request timeout
        # Each attempt can take up to HTTP timeout, plus intervals between attempts
        http_timeout = api_config.get('timeout_seconds', 30)
        if total_timeout_seconds:
            timeout = total_timeout_seconds
        elif 'test_total_timeout_seconds' in retry_config:
            timeout = retry_config.get('test_total_timeout_seconds')
        else:
            # Calculate: (max_attempts * http_timeout) + ((max_attempts - 1) * interval)
            # This ensures we have enough time for all attempts + intervals
            timeout = (max_att * http_timeout) + ((max_att - 1) * interval)
    else:
        max_att = max_attempts or retry_config.get('max_attempts', 20)
        interval = interval_seconds or retry_config.get('interval_seconds', 720)  # 12 minutes
        timeout = total_timeout_seconds or retry_config.get('total_timeout_seconds', 14400)  # 4 hours
    
    return max_att, interval, timeout


async def retry_async(
    func: Callable[..., T],
    *args,
    max_attempts: Optional[int] = None,
    interval_seconds: Optional[int] = None,
    total_timeout_seconds: Optional[int] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs
) -> T:
    """
    Retry async function with configurable parameters.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for function
        max_attempts: Maximum number of attempts (default from config)
        interval_seconds: Interval between attempts in seconds (default from config)
        total_timeout_seconds: Total timeout in seconds (default from config)
        on_retry: Optional callback function called on each retry (attempt_number, exception)
        **kwargs: Keyword arguments for function
        
    Returns:
        Result of function call
        
    Raises:
        Last exception if all attempts failed
    """
    max_attempts, interval_seconds, total_timeout_seconds = _get_retry_settings(
        max_attempts, interval_seconds, total_timeout_seconds
    )
    
    start_time = datetime.now()
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Retry successful on attempt {attempt}")
            return result
            
        except Exception as e:
            last_exception = e
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            # Check if total timeout exceeded
            if elapsed_time >= total_timeout_seconds:
                logger.error(
                    f"Retry timeout exceeded after {elapsed_time:.0f} seconds "
                    f"(max {total_timeout_seconds} seconds). Last error: {e}"
                )
                raise
            
            # Check if this was the last attempt
            if attempt >= max_attempts:
                logger.error(
                    f"All {max_attempts} retry attempts failed. Last error: {e}"
                )
                raise
            
            # Log retry attempt
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {interval_seconds} seconds..."
            )
            
            # Call optional retry callback
            if on_retry:
                try:
                    on_retry(attempt, e)
                except Exception as callback_error:
                    logger.warning(f"Error in retry callback: {callback_error}")
            
            # Wait before next attempt
            await asyncio.sleep(interval_seconds)
    
    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry mechanism failed unexpectedly")


def retry_sync(
    func: Callable[..., T],
    *args,
    max_attempts: Optional[int] = None,
    interval_seconds: Optional[int] = None,
    total_timeout_seconds: Optional[int] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs
) -> T:
    """
    Retry sync function with configurable parameters.
    
    Args:
        func: Sync function to retry
        *args: Positional arguments for function
        max_attempts: Maximum number of attempts (default from config)
        interval_seconds: Interval between attempts in seconds (default from config)
        total_timeout_seconds: Total timeout in seconds (default from config)
        on_retry: Optional callback function called on each retry (attempt_number, exception)
        **kwargs: Keyword arguments for function
        
    Returns:
        Result of function call
        
    Raises:
        Last exception if all attempts failed
    """
    max_attempts, interval_seconds, total_timeout_seconds = _get_retry_settings(
        max_attempts, interval_seconds, total_timeout_seconds
    )
    
    start_time = datetime.now()
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Retry successful on attempt {attempt}")
            return result
            
        except Exception as e:
            last_exception = e
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            # Check if total timeout exceeded
            if elapsed_time >= total_timeout_seconds:
                logger.error(
                    f"Retry timeout exceeded after {elapsed_time:.0f} seconds "
                    f"(max {total_timeout_seconds} seconds). Last error: {e}"
                )
                raise
            
            # Check if this was the last attempt
            if attempt >= max_attempts:
                logger.error(
                    f"All {max_attempts} retry attempts failed. Last error: {e}"
                )
                raise
            
            # Log retry attempt
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {interval_seconds} seconds..."
            )
            
            # Call optional retry callback
            if on_retry:
                try:
                    on_retry(attempt, e)
                except Exception as callback_error:
                    logger.warning(f"Error in retry callback: {callback_error}")
            
            # Wait before next attempt
            time.sleep(interval_seconds)
    
    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry mechanism failed unexpectedly")
