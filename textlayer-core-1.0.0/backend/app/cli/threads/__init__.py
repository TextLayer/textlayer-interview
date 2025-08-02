from time import time
from typing import Optional

# Maximum number of back-and-forth exchanges allowed in a conversation
# This prevents infinite loops and excessive token usage
MAX_THREAD_DEPTH = 10


def thread_is_already_finished(thread: list) -> bool:
    """
    Check if a conversation thread is already finished.

    A thread is considered finished if:
    1. It's empty (has no messages)
    2. The last message is from the assistant and has the "stop" finish reason

    Args:
        thread: List of message dictionaries in the conversation

    Returns:
        bool: True if the thread is finished, False otherwise
    """
    # Case 1: Empty thread
    if not thread:
        print("Thread is empty")
        return True

    # Case 2: Check the last message
    last_message = thread[-1]  # Get the last message from the thread

    # A message from the assistant with finish_reason="stop" means the
    # conversation has reached a natural conclusion
    return last_message.get("finish_reason") == "stop" and last_message.get("role") == "assistant"


def check_termination_conditions(start_time: float, request_timeout: int, depth: int) -> Optional[str]:
    """Check if we need to terminate the conversation early.

    We terminate if:
    1. The conversation has been running too long (timeout)
    2. The conversation is too deep (too many back-and-forth exchanges)

    Args:
        start_time: When the conversation processing started (Unix timestamp)
        request_timeout: Maximum allowed time in seconds
        depth: Current depth of the conversation (number of exchanges)

    Returns:
        str or None: Termination reason if we should terminate, None otherwise
    """
    # Check for timeout - has the conversation been running too long?
    if time() - start_time > request_timeout:
        return "TIMEOUT"

    # Check for maximum depth - have we had too many exchanges?
    if depth >= MAX_THREAD_DEPTH:
        return "MAX_DEPTH"

    # No termination needed
    return None


def terminate_thread(reason: str) -> dict:
    """
    Create a termination message to add to the conversation.

    This adds a special message to the thread that tells the LLM
    why the conversation is being terminated.

    Args:
        reason: The reason for termination (e.g., "TIMEOUT", "MAX_DEPTH")

    Returns:
        dict: A message dictionary to add to the conversation
    """
    return {
        "role": "user",  # Message appears to come from the user
        "content": f"TERMINATED: {reason}",  # Clear indication of termination
    }
