from time import time
from typing import Dict, List

from langfuse.decorators import observe

from app import logger
from app.cli.threads import (
    check_termination_conditions,
    terminate_thread,
    thread_is_already_finished,
)
from app.controllers.thread_controller import ThreadController


@observe(name="agent_chat", capture_input=False)
def process_chat_message(messages: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Process a chat message and handle the conversation flow in an agentic loop.

    This function:
    1. Sets up tracing and monitoring
    2. Processes messages through the ThreadController
    3. Extends the message list with new messages from each processing step
    4. Handles termination conditions and errors
    5. Returns the last assistant message after processing completes

    Args:
        messages: A list of message dictionaries in the conversation
                  (Each message has 'role' and 'content' keys)

    Returns:
        The last assistant message after processing completes
    """
    # Step 1: Setup the environment for processing

    # Initialize tracking variables
    start_time = time()  # Track when we started processing
    depth = 0  # Track how many back-and-forth exchanges we've had
    consecutive_errors = 0  # Track errors to prevent infinite error loops
    request_timeout = 300  # Maximum processing time in seconds (5 minutes)

    # Create our thread controller which will handle the actual message processing
    thread_controller = ThreadController()

    # Step 3: Main processing loop - continue until we get a final answer or hit limits
    while True:
        # Check if we've had too many errors in a row
        if consecutive_errors >= 3:
            logger.info("Too many consecutive errors, breaking out of loop.")
            break

        # Check if the thread is already finished (has a completion message)
        if thread_is_already_finished(messages):
            break

        # Check if we should terminate due to timeout or max depth
        reason = check_termination_conditions(start_time, request_timeout, depth)
        if reason:
            # If we need to terminate, add a termination message and process one last time
            messages.append(terminate_thread(reason))
            try:
                # Try to get a final response given the termination message
                processed = thread_controller.process_chat_message(
                    messages=messages,
                )
                # Extend messages with the processed response
                if processed:
                    messages.extend(processed)
            except Exception as error:
                # Log any errors during this final step, but continue to end the process
                logger.error(f"Error during final termination response: {error}")
            finally:
                # Always break out of the loop after termination
                break

        try:
            # Process the current state of the conversation
            processed = thread_controller.process_chat_message(messages=messages)

            # Extend messages with the processed response
            if processed:
                messages.extend(processed)

            # If we got a response with "stop" finish reason, we're done
            if processed and processed[0].get("finish_reason") == "stop":
                break
        except Exception as error:
            # Handle any errors during processing
            logger.error(f"Error during chat message processing: {error}")
            consecutive_errors += 1  # Increment error count
            continue  # Try again in the next loop iteration
        finally:
            # Always increment the depth counter, regardless of success or failure
            depth += 1

    # Step 4: Find the last assistant message

    # Find the most recent assistant message in the conversation
    assistant_messages = [message for message in messages if message.get("role") == "assistant"]

    if assistant_messages:
        # Return the most recent assistant message
        return assistant_messages[-1]
    else:
        # If no assistant messages found, create an error response
        error_message = {
            "role": "assistant",
            "content": "Sorry, I couldn't help with that, it looks like there's an internal error.",
        }
        # Append the error message to the conversation
        messages.append(error_message)
        return error_message
