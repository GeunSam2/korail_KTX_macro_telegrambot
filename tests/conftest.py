"""Pytest configuration and shared fixtures."""
import os
import sys
import pytest
from testcontainers.redis import RedisContainer

# Start Redis container before any imports
_redis_container = None


def pytest_configure(config):
    """Set up Redis container before test collection."""
    global _redis_container
    _redis_container = RedisContainer("redis:7-alpine")
    _redis_container.start()

    # Set environment variables
    os.environ["REDIS_HOST"] = _redis_container.get_container_host_ip()
    os.environ["REDIS_PORT"] = str(_redis_container.get_exposed_port(6379))
    os.environ["REDIS_DB"] = "0"


def pytest_unconfigure(config):
    """Clean up Redis container after all tests."""
    global _redis_container
    if _redis_container:
        _redis_container.stop()


@pytest.fixture(scope="session")
def redis_container():
    """Get the running Redis container."""
    return _redis_container
