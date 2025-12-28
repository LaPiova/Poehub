import pytest
import sys
from unittest.mock import MagicMock

# Mock redbot before any imports
module_mock = MagicMock()
sys.modules["redbot"] = module_mock
sys.modules["redbot.core"] = module_mock
sys.modules["redbot.core.bot"] = module_mock
sys.modules["redbot.core.utils"] = module_mock
sys.modules["redbot.core.utils.chat_formatting"] = module_mock 
sys.modules["httpx"] = module_mock

@pytest.fixture
def mock_logger(mocker):
    return mocker.patch("logging.getLogger")

@pytest.fixture
def mock_red_bot(mocker):
    """Mock the Red bot instance."""
    bot = MagicMock()
    return bot
