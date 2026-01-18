import pytest


@pytest.fixture
def anyio_backend():
    # Force AnyIO tests to run only on asyncio backend.
    # This avoids requiring the optional 'trio' dependency.
    return "asyncio"
