import asyncio

import pytest

from poehub.core.memory import ThreadSafeMemory


@pytest.mark.asyncio
async def test_initialization():
    """Test memory initialization."""
    # Empty init
    mem = ThreadSafeMemory()
    assert await mem.get_messages() == []

    # Init with messages
    initial = [{"role": "user", "content": "hi"}]
    mem = ThreadSafeMemory(initial)
    assert await mem.get_messages() == initial
    # Ensure deep copy behavior (or at least list copy) on init/get
    initial.append({"role": "system", "content": "bad"})
    assert len(await mem.get_messages()) == 1

@pytest.mark.asyncio
async def test_add_get_clear():
    """Test basic operations."""
    mem = ThreadSafeMemory()
    msg = {"role": "user", "content": "msg1"}

    await mem.add_message(msg)
    messages = await mem.get_messages()
    assert len(messages) == 1
    assert messages[0] == msg

    await mem.clear()
    assert await mem.get_messages() == []

@pytest.mark.asyncio
async def test_concurrency_safety():
    """Test concurrent additions."""
    mem = ThreadSafeMemory()
    count = 100

    async def adder(i):
        await mem.add_message({"role": "user", "content": f"msg{i}"})

    tasks = [adder(i) for i in range(count)]
    await asyncio.gather(*tasks)

    messages = await mem.get_messages()
    assert len(messages) == count
    # Verify content integrity
    contents = {m["content"] for m in messages}
    assert len(contents) == count

@pytest.mark.asyncio
async def test_process_summary_deadlock_freedom():
    """Test that summarizer does NOT deadlock when accessing memory.

    This verifies that the lock is released during the I/O phase.
    """
    mem = ThreadSafeMemory([
        {"role": "user", "content": "1"},
        {"role": "user", "content": "2"}
    ])

    async def summarizer(messages):
        # Allow internal context switch to ensure we aren't just getting lucky
        await asyncio.sleep(0.01)

        # CRITICAL CHECK: Can we add a message while summarizing?
        # If lock was held, this would hang forever (deadlock).
        await mem.add_message({"role": "user", "content": "new_during_summary"})

        return {"role": "system", "content": "summary"}

    # Run process_summary
    # Timeout protects test suite from hanging if we fail the deadlock check
    try:
        async with asyncio.timeout(1.0):
            await mem.process_summary(summarizer)
    except TimeoutError:
        pytest.fail("Deadlock detected! summarizer could not acquire lock.")

    messages = await mem.get_messages()

    # Expected behavior:
    # 1. Start with [1, 2]
    # 2. Snapshot [1, 2] taken.
    # 3. Summarizer called -> adds "new_during_summary" -> returns "summary"
    # 4. Buffer at this point (before update) is [1, 2, new_during_summary]
    # 5. process_summary logic:
    #    - snapshot_count = 2
    #    - new_messages = buffer[2:] -> ["new_during_summary"]
    #    - buffer = [summary] + ["new_during_summary"]

    assert len(messages) == 2
    assert messages[0]["content"] == "summary"
    assert messages[1]["content"] == "new_during_summary"

@pytest.mark.asyncio
async def test_process_summary_concurrent_arrival():
    """Test messages arriving during summarization are preserved."""
    mem = ThreadSafeMemory([{"role": "user", "content": "old"}])

    async def slow_summarizer(messages):
        await asyncio.sleep(0.1)
        return {"role": "system", "content": "summary"}

    async def background_adder():
        await asyncio.sleep(0.05)
        await mem.add_message({"role": "user", "content": "new"})

    summary_task = asyncio.create_task(mem.process_summary(slow_summarizer))
    adder_task = asyncio.create_task(background_adder())

    await asyncio.gather(summary_task, adder_task)

    messages = await mem.get_messages()
    # Expect: [summary, new]
    assert len(messages) == 2
    assert messages[0]["content"] == "summary"
    assert messages[1]["content"] == "new"

@pytest.mark.asyncio
async def test_process_summary_buffer_shrink():
    """Test buffer shrinking during summarization (e.g. clear called)."""
    mem = ThreadSafeMemory([{"role": "user", "content": "old"}])

    async def clearing_summarizer(messages):
        await mem.clear() # Simulate external clear
        return {"role": "system", "content": "summary"}

    await mem.process_summary(clearing_summarizer)

    messages = await mem.get_messages()
    # Expect: empty (summary discarded because buffer shrank)
    assert messages == []
