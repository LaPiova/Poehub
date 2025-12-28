# Testing PoeHub

This repository includes a suite of unit tests to ensure the reliability of core components, including the API client, pricing logic, encryption, and conversation management.

## Prerequisites

The tests require additional development dependencies. You can install them in your virtual environment:

```bash
# If using the standard automated deployment or manual venv:
source ~/.redenv/bin/activate  # or source .venv/bin/activate
pip install -r requirements-dev.txt
```

If `requirements-dev.txt` is missing, you need:
- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-mock`

## Running Tests

### Option 1: Using the Test Runner Script (Recommended)

A helper script is provided to automatically set up the environment and run tests with coverage:

```bash
./run_tests.sh
```

### Option 2: Manual Execution

To run all tests manually:

```bash
# From the repository root
python3 -m pytest tests/
```

**Note:** Ensure your `PYTHONPATH` includes the `src` directory if you encounter import errors (though `pytest` usually handles this):
```bash
PYTHONPATH=src python3 -m pytest tests/
```

## Running with Coverage

To check code coverage:

```bash
python3 -m pytest tests/ --cov=src/poehub --cov-report=term-missing
```

This will display a coverage report in the terminal, showing which lines of code are covered by tests.

## Test Structure

- **`tests/conftest.py`**: Shared fixtures (logging mocks, Red-DiscordBot mocks).
- **`tests/test_api_client.py`**: Tests for `PoeClient` and `OpenAIProvider`, including streaming responses and error handling/retry logic.
- **`tests/test_conversation_manager.py`**: Tests for conversation state, history pruning, and encryption integration.
- **`tests/test_encryption.py`**: Tests for `EncryptionHelper` (Fernet encryption/decryption).
- **`tests/test_i18n.py`**: Tests for internationalization helpers.
- **`tests/test_pricing_oracle.py`**: Tests for cost calculation logic across different providers.

## Writing New Tests

When adding new features, please add corresponding unit tests in `tests/`.
- Use `pytest.mark.asyncio` for async functions.
- Use `unittest.mock` or `pytest-mock` to mock external dependencies (Discord, File I/O, Network requests).
- Avoid making real network requests in tests; always mock API responses.
