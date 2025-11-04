"""
Stream Multiplexing Utilities for GAIA Platform

Provides utilities for merging async streams with prioritization,
particularly for combining LLM output streams with NATS event queues.
"""

import asyncio
from typing import AsyncGenerator, Dict, Any


async def merge_async_streams(
    llm_stream: AsyncGenerator[Dict[str, Any], None],
    nats_queue: asyncio.Queue,
    timeout: float = 30.0
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Merge LLM async stream with NATS event queue, prioritizing NATS events.

    CRITICAL: NATS events must be checked FIRST (before LLM chunks) to ensure
    visual updates arrive before narrative text.

    Implementation pattern:
    1. Check NATS queue with get_nowait() (immediate, non-blocking)
    2. If NATS event available, yield it immediately
    3. Otherwise, wait for either LLM or NATS with asyncio.wait()
    4. Continue until both streams exhausted
    5. Proper cleanup with finally block

    Args:
        llm_stream: Async generator producing LLM response chunks
        nats_queue: Queue receiving NATS events
        timeout: Maximum time to wait for next item (seconds)

    Yields:
        Dict[str, Any]: Either LLM chunks or NATS events

    Raises:
        Exception: Any error from the LLM stream is propagated
        asyncio.TimeoutError: If no data received within timeout
    """
    # Create internal queue for LLM chunks
    llm_queue: asyncio.Queue = asyncio.Queue()
    llm_done = False
    llm_error = None

    # Consumer task to read from LLM stream and put into queue
    async def consume_llm():
        nonlocal llm_done, llm_error
        try:
            async for chunk in llm_stream:
                await llm_queue.put(chunk)
        except Exception as e:
            llm_error = e
        finally:
            llm_done = True

    # Start consuming LLM stream
    llm_task = asyncio.create_task(consume_llm())

    try:
        # Continue until both streams are exhausted
        while not llm_done or not llm_queue.empty() or not nats_queue.empty():
            # Priority 1: Check NATS queue first (non-blocking)
            # This ensures visual updates arrive before narrative text
            try:
                nats_event = nats_queue.get_nowait()
                yield nats_event
                continue  # Check NATS again before proceeding to LLM
            except asyncio.QueueEmpty:
                pass  # NATS queue empty, proceed to wait for either source

            # If both queues are empty and LLM is done, we're finished
            if llm_done and llm_queue.empty() and nats_queue.empty():
                break

            # Priority 2: Wait for either LLM or NATS queue with timeout
            # Create tasks for getting from each queue
            llm_get_task = asyncio.create_task(llm_queue.get())
            nats_get_task = asyncio.create_task(nats_queue.get())

            try:
                done, pending = await asyncio.wait(
                    {llm_get_task, nats_get_task},
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=timeout
                )

                if not done:
                    # Timeout occurred - gracefully exit instead of raising
                    llm_get_task.cancel()
                    nats_get_task.cancel()
                    break

                # Process completed task(s)
                for task in done:
                    data = await task
                    yield data

                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            except asyncio.CancelledError:
                # Clean up tasks if we're being cancelled
                llm_get_task.cancel()
                nats_get_task.cancel()
                raise

            # Check if LLM stream had an error
            if llm_error:
                raise llm_error

    finally:
        # Cleanup: Cancel LLM consumer task if still running
        if not llm_task.done():
            llm_task.cancel()
            try:
                await llm_task
            except asyncio.CancelledError:
                pass

        # Re-raise LLM error if it occurred
        if llm_error:
            raise llm_error
