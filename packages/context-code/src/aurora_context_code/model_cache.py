"""Lightweight model cache checking - NO torch/transformers imports.

This module provides a fast way to check if the embedding model is cached
without triggering the heavy torch/sentence-transformers imports. This is
critical for fast CLI startup times.

IMPORTANT: Do NOT add imports from .semantic or any module that imports
torch/sentence-transformers. This module must stay lightweight.

Usage:
    from aurora_context_code.model_cache import is_model_cached_fast, start_background_loading

    # Check cache quickly (< 10ms)
    if is_model_cached_fast():
        # Start loading in background (returns immediately)
        start_background_loading()
"""

from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass  # Keep this empty - no heavy imports even for type checking

# Default embedding model
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# HuggingFace cache directory
_HF_CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"


def is_model_cached_fast(model_name: str = DEFAULT_MODEL) -> bool:
    """Check if embedding model is cached - FAST, no heavy imports.

    This function checks only the filesystem and does NOT import
    torch or sentence-transformers. Safe to call during CLI startup.

    Args:
        model_name: Model identifier (default: all-MiniLM-L6-v2)

    Returns:
        True if model appears to be cached

    """
    # Convert model name to cache path format
    safe_name = model_name.replace("/", "--")
    cache_path = _HF_CACHE_DIR / f"models--{safe_name}"

    if not cache_path.exists():
        return False

    snapshots_dir = cache_path / "snapshots"
    if not snapshots_dir.exists():
        return False

    # Check for model files in any snapshot
    try:
        for snapshot in snapshots_dir.iterdir():
            if snapshot.is_dir():
                if (snapshot / "model.safetensors").exists():
                    return True
                if (snapshot / "pytorch_model.bin").exists():
                    return True
    except (PermissionError, OSError):
        pass

    return False


def start_background_loading(model_name: str = "all-MiniLM-L6-v2") -> bool:
    """Start loading embedding model in background thread.

    This function imports the heavy dependencies (torch, sentence-transformers)
    in a background thread so the main thread can continue immediately.

    IMPORTANT: Imports semantic module in main thread FIRST to avoid race conditions
    with Python's import system.

    Args:
        model_name: Model name for sentence-transformers

    Returns:
        True if background loading was started, False if not possible

    """
    import threading

    # CRITICAL: Import the semantic module in main thread BEFORE starting background thread
    # This prevents race conditions where background thread partially initializes the module
    # while main thread tries to import from it (causes KeyError in sys.modules)
    try:
        import aurora_context_code.semantic  # noqa: F401 - ensures module is in sys.modules
    except Exception:
        return False  # Can't import - skip background loading

    def _load_in_background() -> None:
        """Background thread function that does the heavy importing."""
        try:
            import os

            # Set offline mode to avoid network checks
            os.environ["HF_HUB_OFFLINE"] = "1"

            # Import the full semantic module (triggers torch import)
            from aurora_context_code.semantic.model_utils import BackgroundModelLoader

            loader = BackgroundModelLoader.get_instance()
            loader.start_loading(model_name=model_name)
        except Exception:
            pass  # Silently fail - embedding will use fallback BM25

    # Start background thread
    thread = threading.Thread(target=_load_in_background, daemon=True)
    thread.start()
    return True
