"""Unit tests for ActivationEngine instance caching.

Tests verify that ActivationEngine instances are properly cached based on
db_path, with thread-safe access and singleton pattern per database.

Test scenarios:
- Cache hit when same db_path (singleton pattern)
- Cache miss when different db_path
- Cache hit for :memory: database
- Thread-safe concurrent access
- Lazy initialization pattern
"""

import threading


# Mock classes for testing
class MockStore:
    """Mock storage backend."""

    def __init__(self, db_path):
        self.db_path = db_path


def test_engine_cache_same_db(tmp_path):
    """Test that two engines with same db_path return same instance.

    Task 2.1: Verify singleton pattern for same database path.
    """
    from aurora_core.activation.engine import get_cached_engine

    db_path = str(tmp_path / "test.db")

    # Create mock store
    store = MockStore(db_path)

    # Create two engines with same db_path
    engine1 = get_cached_engine(store)
    engine2 = get_cached_engine(store)

    # Verify they are the same object (singleton pattern)
    assert id(engine1) == id(engine2), "Same db_path should return singleton instance"


def test_engine_cache_different_db(tmp_path):
    """Test that two engines with different db_path return different instances.

    Task 2.2: Verify cache miss for different database paths.
    """
    from aurora_core.activation.engine import get_cached_engine

    db_path1 = str(tmp_path / "test1.db")
    db_path2 = str(tmp_path / "test2.db")

    # Create mock stores
    store1 = MockStore(db_path1)
    store2 = MockStore(db_path2)

    # Create two engines with different db_paths
    engine1 = get_cached_engine(store1)
    engine2 = get_cached_engine(store2)

    # Verify they are different objects
    assert id(engine1) != id(engine2), "Different db_path should return different instances"


def test_engine_cache_memory_db():
    """Test that :memory: database caches correctly.

    Task 2.3: Verify singleton pattern for in-memory database.
    """
    from aurora_core.activation.engine import get_cached_engine

    # Create mock stores with :memory: db_path
    store1 = MockStore(":memory:")
    store2 = MockStore(":memory:")

    # Create two engines with :memory: db_path
    engine1 = get_cached_engine(store1)
    engine2 = get_cached_engine(store2)

    # Verify they are the same object (singleton per :memory:)
    assert id(engine1) == id(engine2), ":memory: db_path should return singleton instance"


def test_engine_cache_thread_safety(tmp_path):
    """Test thread-safe concurrent access to engine cache.

    Task 2.4: Verify no race conditions with concurrent engine creation.
    Launch 5 threads creating engine concurrently, verify all get same instance.
    """
    from aurora_core.activation.engine import get_cached_engine

    db_path = str(tmp_path / "test.db")

    # Create mock store
    store = MockStore(db_path)

    # Store engine instances from each thread
    engines = []
    engine_lock = threading.Lock()
    errors = []

    def create_engine():
        """Create engine in thread."""
        try:
            engine = get_cached_engine(store)
            with engine_lock:
                engines.append(engine)
        except Exception as e:
            errors.append(e)

    # Launch 5 threads
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=create_engine)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Threads should not error: {errors}"

    # Verify all threads got engines
    assert len(engines) == 5, f"Should have 5 engines, got {len(engines)}"

    # Verify all engines are the same instance (no race conditions)
    first_id = id(engines[0])
    for i, engine in enumerate(engines[1:], start=1):
        assert id(engine) == first_id, (
            f"Engine {i} has different id: " f"{id(engine)} vs {first_id} (race condition detected)"
        )


def test_engine_cache_lazy_initialization():
    """Test that engine is not created until first access.

    Task 2.5: Verify lazy initialization pattern.
    """
    from aurora_core.activation.engine import _engine_cache, get_cached_engine

    # Clear cache before test
    _engine_cache.clear()

    # Verify cache is empty
    assert len(_engine_cache) == 0, "Cache should be empty initially"

    # Create store but don't access engine yet
    store = MockStore("/tmp/lazy_test.db")

    # Verify cache is still empty (no eager initialization)
    assert len(_engine_cache) == 0, "Cache should remain empty before first access"

    # Now access engine
    engine = get_cached_engine(store)

    # Verify engine was created
    assert engine is not None, "Engine should be created on first access"

    # Verify cache now has one entry
    assert len(_engine_cache) == 1, "Cache should have one entry after first access"
