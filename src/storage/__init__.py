"""Storage implementations for application state."""
from storage.base import StorageInterface
from storage.memory import InMemoryStorage

__all__ = [
    'StorageInterface',
    'InMemoryStorage',
]
