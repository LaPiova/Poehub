import sys
from unittest.mock import MagicMock

import pytest


class MockCog:
    """Mock base class for Red cogs."""
    def __init__(self, bot):
        self.bot = bot

    @classmethod
    def listener(cls, name=None):
        return lambda func: func

# Mock redbot before any imports
module_mock = MagicMock()
core_mock = MagicMock()
module_mock.core = core_mock

# commands
commands_mock = MagicMock()
commands_mock.Cog = MockCog
commands_mock.command = lambda **kwargs: lambda func: func
commands_mock.hybrid_command = lambda **kwargs: lambda func: func
commands_mock.group = lambda **kwargs: lambda func: func
commands_mock.is_owner = lambda: lambda func: func
core_mock.commands = commands_mock

# bot
bot_module_mock = MagicMock()
bot_module_mock.Red = MagicMock()
core_mock.bot = bot_module_mock

# config
config_mock = MagicMock()
core_mock.Config = config_mock

# utils
utils_mock = MagicMock()
core_mock.utils = utils_mock

sys.modules["redbot"] = module_mock
sys.modules["redbot.core"] = core_mock
sys.modules["redbot.core.bot"] = bot_module_mock
sys.modules["redbot.core.commands"] = commands_mock
sys.modules["redbot.core.utils"] = utils_mock
# Also need chat_formatting
sys.modules["redbot.core.utils.chat_formatting"] = MagicMock()
sys.modules["httpx"] = MagicMock()


@pytest.fixture
def mock_logger(mocker):
    return mocker.patch("logging.getLogger")


@pytest.fixture
def mock_red_bot(mocker):
    """Mock the Red bot instance."""
    bot = MagicMock()
    return bot
