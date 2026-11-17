import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Adapters cache provider responses; every test starts cold."""
    cache.clear()
