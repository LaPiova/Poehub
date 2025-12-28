import time
from unittest.mock import patch

import pytest

from poehub.utils.logging import (
    RequestContext,
    _request_id,
    clear_request_id,
    get_request_id,
    set_request_id,
)


def test_request_id_management():
    """Test getting, setting, and clearing request IDs."""
    # Start fresh
    clear_request_id()

    # Auto-generate
    rid1 = get_request_id()
    assert rid1 is not None
    assert get_request_id() == rid1

    # Set specific
    set_request_id("custom-id")
    assert get_request_id() == "custom-id"

    # Clear
    clear_request_id()
    assert _request_id.get() is None

    # Auto-generate new
    rid2 = get_request_id()
    assert rid2 != "custom-id"

def test_request_context_manager():
    """Test RequestContext context manager."""
    clear_request_id()

    with RequestContext(request_id="test-ctx", user="alice") as ctx:
        assert get_request_id() == "test-ctx"
        assert ctx.request_id == "test-ctx"
        assert ctx.context == {"user": "alice"}

        # Check formatting
        msg = ctx._format_message("Hello", status="ok")
        assert "[test-ctx] Hello" in msg
        assert "user=alice" in msg
        assert "status=ok" in msg

    # Should revert to previous (None)
    assert _request_id.get() is None

@pytest.mark.asyncio
async def test_request_context_async_manager():
    """Test RequestContext async context manager."""
    clear_request_id()

    async with RequestContext(request_id="async-ctx"):
        assert get_request_id() == "async-ctx"

    assert _request_id.get() is None

def test_request_context_nesting():
    """Test nesting RequestContext."""
    set_request_id("outer")

    with RequestContext(request_id="inner"):
        assert get_request_id() == "inner"

    assert get_request_id() == "outer"

def test_logging_methods():
    """Test logging methods proxy to logging module."""
    with patch("poehub.utils.logging.log") as mock_log:
        with RequestContext(request_id="log-ctx") as ctx:
            ctx.debug("debug msg")
            ctx.info("info msg")
            ctx.warning("warning msg")
            ctx.error("error msg")
            ctx.exception("exception msg")

            # Allow some time to pass
            time.sleep(0.001)
            assert ctx.elapsed > 0

        mock_log.debug.assert_called()
        mock_log.info.assert_called()
        mock_log.warning.assert_called()
        mock_log.error.assert_called()
        mock_log.exception.assert_called()

        # Check format
        args, _ = mock_log.info.call_args
        assert "[log-ctx] info msg" in args[0]
