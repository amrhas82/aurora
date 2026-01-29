"""Utility functions for embedding model management.

Provides functions to check model availability and download with progress display.
Also provides BackgroundModelLoader for non-blocking model initialization.
"""

import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from rich.console import Console

    from aurora_context_code.semantic.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)

# Default model used by EmbeddingProvider
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# HuggingFace cache directory
HF_CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"


# =============================================================================
# Exceptions
# =============================================================================


class MLDependencyError(Exception):
    """Raised when ML dependencies are missing or model download failed."""

    pass


# =============================================================================
# Helper functions
# =============================================================================


@contextmanager
def _suppress_model_loading_output():
    """Suppress verbose model loading messages from HuggingFace/PyTorch.

    Adjusts logging levels and environment variables to hide:
    - Noisy "Loading weights: X%" progress messages (logging)
    - tqdm progress bars from HuggingFace Hub (stdout/stderr)

    NOTE: Sets environment variables temporarily to suppress tqdm output
    without redirecting stdout/stderr (which could break module imports).
    """
    # Save original logging levels
    original_log_level = logging.getLogger("transformers").level
    original_hf_log_level = logging.getLogger("huggingface_hub").level

    # Save original environment variables
    original_env = {
        "HF_HUB_DISABLE_PROGRESS_BARS": os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS"),
        "TRANSFORMERS_VERBOSITY": os.environ.get("TRANSFORMERS_VERBOSITY"),
    }

    try:
        # Suppress transformers and huggingface_hub logging
        logging.getLogger("transformers").setLevel(logging.ERROR)
        logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

        # Suppress tqdm progress bars from HuggingFace Hub
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        os.environ["TRANSFORMERS_VERBOSITY"] = "error"

        yield

    finally:
        # Restore original logging levels
        logging.getLogger("transformers").setLevel(original_log_level)
        logging.getLogger("huggingface_hub").setLevel(original_hf_log_level)

        # Restore original environment variables
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


# =============================================================================
# Lightweight cache checking (can be imported without loading torch/transformers)
# =============================================================================


def is_model_cached_lightweight(model_name: str = DEFAULT_MODEL) -> bool:
    """Check if the embedding model is cached WITHOUT importing heavy dependencies.

    This function can be called very early in application startup without
    triggering the import of torch or sentence-transformers. Use this for
    quick checks before deciding whether to start background loading.

    Args:
        model_name: HuggingFace model identifier

    Returns:
        True if model files appear to be cached, False otherwise

    """
    # HuggingFace stores models with -- separator instead of /
    safe_name = model_name.replace("/", "--")
    cache_path = HF_CACHE_DIR / f"models--{safe_name}"

    if not cache_path.exists():
        return False

    snapshots_dir = cache_path / "snapshots"
    if not snapshots_dir.exists():
        return False

    # Check if at least one snapshot exists with model files
    try:
        for snapshot in snapshots_dir.iterdir():
            if snapshot.is_dir():
                model_file = snapshot / "model.safetensors"
                pytorch_file = snapshot / "pytorch_model.bin"
                if model_file.exists() or pytorch_file.exists():
                    return True
    except PermissionError:
        return False

    return False


def get_model_cache_path(model_name: str = DEFAULT_MODEL) -> Path:
    """Get the cache directory path for a model.

    Args:
        model_name: HuggingFace model identifier (e.g., "sentence-transformers/all-MiniLM-L6-v2")

    Returns:
        Path to the model cache directory

    """
    # HuggingFace stores models with -- separator instead of /
    safe_name = model_name.replace("/", "--")
    return HF_CACHE_DIR / f"models--{safe_name}"


def is_model_cached(model_name: str = DEFAULT_MODEL) -> bool:
    """Check if the embedding model is already downloaded.

    Args:
        model_name: HuggingFace model identifier

    Returns:
        True if model is cached and ready to use

    """
    cache_path = get_model_cache_path(model_name)

    # Check if cache directory exists and has snapshots
    if not cache_path.exists():
        return False

    snapshots_dir = cache_path / "snapshots"
    if not snapshots_dir.exists():
        return False

    # Check if at least one snapshot exists with model files
    for snapshot in snapshots_dir.iterdir():
        if snapshot.is_dir():
            # Check for essential model files
            model_file = snapshot / "model.safetensors"
            pytorch_file = snapshot / "pytorch_model.bin"
            if model_file.exists() or pytorch_file.exists():
                return True

    return False


def get_model_size_mb(model_name: str = DEFAULT_MODEL) -> int:
    """Get approximate download size for a model in MB.

    Args:
        model_name: HuggingFace model identifier

    Returns:
        Approximate size in MB (0 if unknown)

    """
    # Known sizes for common models
    known_sizes = {
        "sentence-transformers/all-MiniLM-L6-v2": 88,
        "all-MiniLM-L6-v2": 88,
    }
    return known_sizes.get(model_name, 0)


def validate_ml_ready(
    model_name: str = DEFAULT_MODEL,
    console: "Console | None" = None,
) -> None:
    """Validate ML dependencies and download model if needed.

    This function performs fail-fast validation BEFORE any file processing
    begins, ensuring that ML dependencies are available and the embedding
    model is downloaded.

    Args:
        model_name: HuggingFace model identifier
        console: Rich Console for progress output (optional)

    Raises:
        MLDependencyError: If sentence-transformers is not installed or model
            download fails. The error message includes actionable instructions.

    """
    # 1. Check sentence-transformers installed
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise MLDependencyError(
            "sentence-transformers package not installed.\n\n"
            "[bold]Solution:[/]\n"
            "  1. Install the package:\n"
            "     [cyan]pip install sentence-transformers[/]\n"
            "  2. Or reinstall aurora-context-code:\n"
            "     [cyan]pip install -e packages/context-code[/]\n\n"
            f"[dim]Error: {e}[/]"
        ) from e

    # 2. Check if model is already cached
    if is_model_cached(model_name):
        logger.debug("Model %s already cached and ready", model_name)
        return

    # 3. Attempt download with progress
    model_size = get_model_size_mb(model_name)

    if console:
        from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

        size_info = f" (~{model_size}MB)" if model_size else ""
        console.print(f"\n[cyan]Downloading embedding model[/]: {model_name}{size_info}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Downloading model...", total=None)

            try:
                # This will download if not cached (suppress verbose output)
                with _suppress_model_loading_output():
                    SentenceTransformer(model_name)
                progress.update(task, description="[green]Download complete!")
                logger.info("Model %s downloaded successfully", model_name)
                return
            except Exception as e:
                progress.update(task, description=f"[red]Download failed: {e}")
                logger.error("Failed to download model %s: %s", model_name, e)
                # 4. Raise MLDependencyError if download fails
                raise MLDependencyError(
                    f"Failed to download embedding model: {model_name}\n\n"
                    "[bold]Solution:[/]\n"
                    "  1. Check internet connection\n"
                    "  2. Retry: [cyan]aur doctor --fix-ml[/]\n"
                    "  3. Manual download:\n"
                    "     [cyan]python -c 'from sentence_transformers import SentenceTransformer; "
                    f"SentenceTransformer(\"{model_name}\")\'[/]\n\n"
                    f"[dim]Error: {e}[/]"
                ) from e
    else:
        # No progress display - just download
        print(f"Downloading embedding model: {model_name}")

        try:
            with _suppress_model_loading_output():
                SentenceTransformer(model_name)
            logger.info("Model %s downloaded successfully", model_name)
            return
        except Exception as e:
            logger.error("Failed to download model %s: %s", model_name, e)
            raise MLDependencyError(
                f"Failed to download embedding model: {model_name}\n\n"
                "[bold]Solution:[/]\n"
                "  1. Check internet connection\n"
                "  2. Retry: [cyan]aur doctor --fix-ml[/]\n"
                "  3. Manual download:\n"
                "     [cyan]python -c 'from sentence_transformers import SentenceTransformer; "
                f"SentenceTransformer(\"{model_name}\")\'[/]\n\n"
                f"[dim]Error: {e}[/]"
            ) from e


def ensure_model_downloaded(
    model_name: str = DEFAULT_MODEL,
    show_progress: bool = True,
    console: "Console | None" = None,  # Rich Console for progress display
) -> bool:
    """Ensure the embedding model is downloaded, showing progress if needed.

    Args:
        model_name: HuggingFace model identifier
        show_progress: Whether to show download progress
        console: Rich Console for progress output (optional)

    Returns:
        True if model is available (was cached or downloaded successfully)
        False if download failed

    """
    # Already cached - nothing to do
    if is_model_cached(model_name):
        logger.debug("Model %s already cached", model_name)
        return True

    # Try to import sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning("sentence-transformers not installed. Semantic search will be unavailable.")
        return False

    # Download the model with progress display
    model_size = get_model_size_mb(model_name)

    if show_progress and console:
        from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

        size_info = f" (~{model_size}MB)" if model_size else ""
        console.print(f"\n[cyan]Downloading embedding model[/]: {model_name}{size_info}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Downloading model...", total=None)

            try:
                # This will download if not cached (suppress verbose output)
                with _suppress_model_loading_output():
                    SentenceTransformer(model_name)
                progress.update(task, description="[green]Download complete!")
                return True
            except Exception as e:
                progress.update(task, description=f"[red]Download failed: {e}")
                logger.error("Failed to download model %s: %s", model_name, e)
                return False
    else:
        # No progress display - just download
        if show_progress:
            print(f"Downloading embedding model: {model_name}")

        try:
            with _suppress_model_loading_output():
                SentenceTransformer(model_name)
            return True
        except Exception as e:
            logger.error("Failed to download model %s: %s", model_name, e)
            return False


class BackgroundModelLoader:
    """Background loader for embedding models to avoid blocking startup.

    This singleton class manages loading the embedding model in a background
    thread, allowing the CLI to remain responsive during the ~30 second
    model initialization.

    The loader provides:
    - Non-blocking start_loading() to begin model loading in background
    - wait_for_model() to get the loaded model (blocks only if still loading)
    - Progress tracking for UI feedback

    Example:
        >>> loader = BackgroundModelLoader.get_instance()
        >>> loader.start_loading()  # Returns immediately
        >>>
        >>> # Do other initialization work...
        >>>
        >>> # When embeddings are needed:
        >>> provider = loader.wait_for_model(timeout=60.0)
        >>> if provider:
        ...     embedding = provider.embed_query("search query")

    """

    _instance: "BackgroundModelLoader | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize the background loader (use get_instance() instead)."""
        self._provider: EmbeddingProvider | None = None
        self._thread: threading.Thread | None = None
        self._error: Exception | None = None
        self._loading = False
        self._loaded = False
        self._load_start_time: float = 0.0
        self._load_end_time: float = 0.0
        self._model_name: str = "all-MiniLM-L6-v2"

    @classmethod
    def get_instance(cls) -> "BackgroundModelLoader":
        """Get the singleton instance of BackgroundModelLoader.

        Returns:
            The singleton BackgroundModelLoader instance

        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._provider = None
                cls._instance._thread = None
                cls._instance._error = None
                cls._instance._loading = False
                cls._instance._loaded = False
            cls._instance = None

    def start_loading(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Start loading the embedding model in a background thread.

        This method returns immediately. The model will be loaded in the
        background and can be retrieved later with wait_for_model().

        Args:
            model_name: Sentence-transformers model name

        Note:
            Calling this multiple times is safe - subsequent calls are ignored
            if loading is already in progress or complete.

        """
        with self._lock:
            # Already loading or loaded
            if self._loading or self._loaded:
                logger.debug("Model already loading or loaded, skipping")
                return

            self._loading = True
            self._model_name = model_name
            self._load_start_time = time.time()
            self._error = None

        # Start background thread
        self._thread = threading.Thread(target=self._load_model, daemon=True)
        self._thread.start()
        logger.debug("Started background model loading for %s", model_name)

    def _load_model(self) -> None:
        """Load the model in background thread."""
        try:
            # Set offline mode if model is cached (avoids network checks)
            if is_model_cached(self._model_name):
                os.environ["HF_HUB_OFFLINE"] = "1"

            # Import and create provider (this loads the model)
            # Suppress verbose loading messages
            with _suppress_model_loading_output():
                from aurora_context_code.semantic.embedding_provider import EmbeddingProvider

                provider = EmbeddingProvider(model_name=self._model_name)
                provider.preload_model()  # Force model to load now

            with self._lock:
                self._provider = provider
                self._loaded = True
                self._loading = False
                self._load_end_time = time.time()

            load_time = self._load_end_time - self._load_start_time
            logger.info("Background model loading complete (%.1fs)", load_time)

        except Exception as e:
            with self._lock:
                self._error = e
                self._loading = False
                self._load_end_time = time.time()

            logger.error("Background model loading failed: %s", e)

    def is_loading(self) -> bool:
        """Check if model is currently loading.

        Returns:
            True if loading is in progress

        """
        with self._lock:
            return self._loading

    def is_loaded(self) -> bool:
        """Check if model has been successfully loaded.

        Returns:
            True if model is loaded and ready

        """
        with self._lock:
            return self._loaded

    def get_error(self) -> Exception | None:
        """Get any error that occurred during loading.

        Returns:
            Exception if loading failed, None otherwise

        """
        with self._lock:
            return self._error

    def get_load_time(self) -> float:
        """Get the time taken to load the model.

        Returns:
            Load time in seconds (0 if not yet loaded)

        """
        with self._lock:
            if self._load_end_time > 0 and self._load_start_time > 0:
                return self._load_end_time - self._load_start_time
            return 0.0

    def wait_for_model(
        self,
        timeout: float = 60.0,
        poll_interval: float = 0.1,
    ) -> "EmbeddingProvider | None":
        """Wait for the model to finish loading and return the provider.

        Args:
            timeout: Maximum time to wait in seconds (default: 60s)
            poll_interval: Time between status checks (default: 0.1s)

        Returns:
            EmbeddingProvider if loaded successfully, None if failed/timeout

        """
        start = time.time()

        while time.time() - start < timeout:
            with self._lock:
                if self._loaded:
                    return self._provider
                if self._error is not None:
                    logger.warning("Model loading failed: %s", self._error)
                    return None
                if not self._loading:
                    # Not loading and not loaded - wasn't started
                    logger.warning("Model loading was not started")
                    return None

            time.sleep(poll_interval)

        logger.warning("Timeout waiting for model to load (%.1fs)", timeout)
        return None

    def get_provider_if_ready(self) -> "EmbeddingProvider | None":
        """Get the provider only if it's already loaded (non-blocking).

        Returns:
            EmbeddingProvider if loaded, None otherwise

        """
        with self._lock:
            if self._loaded:
                return self._provider
            return None
