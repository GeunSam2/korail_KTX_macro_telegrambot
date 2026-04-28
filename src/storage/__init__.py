"""Storage implementations for application state."""
from storage.base import StorageInterface
from storage.redis import RedisStorage

__all__ = [
    'StorageInterface',
    'RedisStorage',
]
