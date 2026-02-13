"""Integration tests for LSP analysis helpers and client normalization.

Tests pure logic — no running language servers, no network.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aurora_lsp.analysis import (
    CodeAnalyzer,
    _batched_ripgrep_search,
    _ext_to_rg_type,
    _fallback_grep_search,
)
from aurora_lsp.client import AuroraLSPClient

# ---------------------------------------------------------------------------
# _ext_to_rg_type
# ---------------------------------------------------------------------------


class TestExtToRgType:
    """Tests for file extension → ripgrep type mapping."""

    @pytest.mark.parametrize(
        "ext,expected",
        [
            (".py", "py"),
            (".pyi", "py"),
            (".js", "js"),
            (".jsx", "js"),
            (".mjs", "js"),
            (".ts", "ts"),
            (".tsx", "ts"),
            (".go", "go"),
            (".java", "java"),
        ],
    )
    def test_ext_to_rg_type_all(self, ext, expected):
        """Known extensions map to correct ripgrep types."""
        assert _ext_to_rg_type(ext) == expected

    def test_ext_to_rg_type_default(self):
        """Unknown extension defaults to 'py'."""
        assert _ext_to_rg_type(".rs") == "py"
        assert _ext_to_rg_type(".rb") == "py"
        assert _ext_to_rg_type(".xyz") == "py"


# ---------------------------------------------------------------------------
# _batched_ripgrep_search
# ---------------------------------------------------------------------------


class TestBatchedRipgrepSearch:
    """Tests for batched ripgrep symbol search."""

    def test_batched_ripgrep_empty_symbols(self, tmp_path):
        """Empty symbol list → empty dict."""
        result = _batched_ripgrep_search([], tmp_path)
        assert result == {}

    def test_batched_ripgrep_parse_json(self, tmp_path):
        """Mock subprocess produces correct symbol-to-file map."""
        # Build fake rg JSON output
        rg_lines = []
        for sym, fpath in [("foo", "./src/a.py"), ("bar", "./src/b.py"), ("foo", "./src/c.py")]:
            entry = {
                "type": "match",
                "data": {
                    "path": {"text": fpath},
                    "submatches": [{"match": {"text": sym}}],
                },
            }
            rg_lines.append(json.dumps(entry))

        fake_result = MagicMock()
        fake_result.stdout = "\n".join(rg_lines)
        fake_result.returncode = 0

        with patch("aurora_lsp.analysis.subprocess.run", return_value=fake_result):
            result = _batched_ripgrep_search(["foo", "bar"], tmp_path)

        assert set(result["foo"]) == {"./src/a.py", "./src/c.py"}
        assert result["bar"] == ["./src/b.py"]

    def test_batched_ripgrep_timeout(self, tmp_path):
        """TimeoutExpired → empty results for all symbols."""
        with patch(
            "aurora_lsp.analysis.subprocess.run",
            side_effect=subprocess.TimeoutExpired("rg", 30),
        ):
            result = _batched_ripgrep_search(["foo", "bar"], tmp_path)

        assert result == {"foo": [], "bar": []}

    def test_batched_ripgrep_rg_not_found(self, tmp_path):
        """FileNotFoundError → calls fallback grep search."""
        with patch(
            "aurora_lsp.analysis.subprocess.run",
            side_effect=FileNotFoundError("rg"),
        ):
            with patch(
                "aurora_lsp.analysis._fallback_grep_search",
                return_value={"foo": ["./x.py"]},
            ) as mock_fallback:
                result = _batched_ripgrep_search(["foo"], tmp_path)

        mock_fallback.assert_called_once()
        assert result == {"foo": ["./x.py"]}


# ---------------------------------------------------------------------------
# CodeAnalyzer helper methods
# ---------------------------------------------------------------------------


class TestCodeAnalyzerHelpers:
    """Tests for pure helper methods on CodeAnalyzer (no LSP server needed)."""

    def _make_analyzer(self, tmp_path):
        """Create analyzer with mock client."""
        client = MagicMock()
        return CodeAnalyzer(client=client, workspace=tmp_path)

    def test_is_callback_context(self):
        """Lines with .map(, .filter( etc. detected as callback context."""
        cb_methods = {"map", "filter", "then", "forEach"}
        assert CodeAnalyzer._is_callback_context("arr.map(fn)", cb_methods)
        assert CodeAnalyzer._is_callback_context("  promise.then(handler)", cb_methods)
        assert not CodeAnalyzer._is_callback_context("x = mapper(y)", cb_methods)
        assert not CodeAnalyzer._is_callback_context("", cb_methods)

    def test_flatten_symbols(self, tmp_path):
        """Nested children flattened to flat list."""
        analyzer = self._make_analyzer(tmp_path)
        symbols = [
            {
                "name": "ClassA",
                "kind": 5,
                "children": [
                    {"name": "method1", "kind": 6, "children": []},
                    {"name": "method2", "kind": 6},
                ],
            },
            {"name": "func_top", "kind": 12},
        ]
        flat = analyzer._flatten_symbols(symbols)
        names = [s["name"] for s in flat]
        assert names == ["ClassA", "method1", "method2", "func_top"]

    def test_flatten_symbols_empty(self, tmp_path):
        """Empty list → empty result."""
        analyzer = self._make_analyzer(tmp_path)
        assert analyzer._flatten_symbols([]) == []

    def test_get_source_files(self, tmp_path):
        """Finds .py files, excludes node_modules and __pycache__."""
        # Create test file structure
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("# main")
        (src / "utils.js").write_text("// utils")
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("// pkg")
        pc = tmp_path / "__pycache__"
        pc.mkdir()
        (pc / "cached.py").write_text("# cached")

        analyzer = self._make_analyzer(tmp_path)
        files = analyzer._get_source_files()

        file_names = {f.name for f in files}
        assert "main.py" in file_names
        assert "utils.js" in file_names
        assert "index.js" not in file_names  # excluded: node_modules
        assert "cached.py" not in file_names  # excluded: __pycache__

    def test_get_source_files_single_file(self, tmp_path):
        """Single file path returns list with just that file."""
        f = tmp_path / "single.py"
        f.write_text("# single")
        analyzer = self._make_analyzer(tmp_path)
        files = analyzer._get_source_files(f)
        assert len(files) == 1
        assert files[0] == f

    def test_is_same_location(self, tmp_path):
        """Same file+line → True, different → False."""
        analyzer = self._make_analyzer(tmp_path)
        f = tmp_path / "test.py"
        f.write_text("# test")

        ref_same = {"file": str(f), "line": 10}
        assert analyzer._is_same_location(ref_same, str(f), 10)

        ref_diff_line = {"file": str(f), "line": 20}
        assert not analyzer._is_same_location(ref_diff_line, str(f), 10)

        ref_diff_file = {"file": str(tmp_path / "other.py"), "line": 10}
        assert not analyzer._is_same_location(ref_diff_file, str(f), 10)

    @pytest.mark.asyncio
    async def test_read_line_caching(self, tmp_path):
        """Reads correct line and caches file content."""
        f = tmp_path / "lines.py"
        f.write_text("line0\nline1\nline2\n")
        analyzer = self._make_analyzer(tmp_path)

        result = await analyzer._read_line(str(f), 1)
        assert result == "line1"
        # File should now be cached
        assert str(f) in analyzer._file_cache

        # Second read uses cache
        result2 = await analyzer._read_line(str(f), 0)
        assert result2 == "line0"

    @pytest.mark.asyncio
    async def test_read_line_out_of_bounds(self, tmp_path):
        """Out-of-bounds line number returns empty string."""
        f = tmp_path / "short.py"
        f.write_text("only one line")
        analyzer = self._make_analyzer(tmp_path)
        result = await analyzer._read_line(str(f), 99)
        assert result == ""


# ---------------------------------------------------------------------------
# AuroraLSPClient normalization
# ---------------------------------------------------------------------------


class TestClientNormalization:
    """Tests for _normalize_locations and _to_relative."""

    def _make_client(self, tmp_path):
        """Create client without starting servers."""
        client = AuroraLSPClient(workspace=tmp_path)
        return client

    def test_normalize_locations_empty_none(self, tmp_path):
        """None or empty list → empty result."""
        client = self._make_client(tmp_path)
        assert client._normalize_locations(None) == []
        assert client._normalize_locations([]) == []

    def test_normalize_locations_absolute_path(self, tmp_path):
        """absolutePath key extracted correctly."""
        client = self._make_client(tmp_path)
        locs = [
            {
                "absolutePath": "/home/user/project/foo.py",
                "range": {"start": {"line": 5, "character": 10}},
            }
        ]
        result = client._normalize_locations(locs)
        assert len(result) == 1
        assert result[0]["file"] == "/home/user/project/foo.py"
        assert result[0]["line"] == 5
        assert result[0]["col"] == 10

    def test_normalize_locations_uri(self, tmp_path):
        """uri with file:// prefix stripped."""
        client = self._make_client(tmp_path)
        locs = [
            {"uri": "file:///home/user/foo.py", "range": {"start": {"line": 3, "character": 0}}}
        ]
        result = client._normalize_locations(locs)
        assert result[0]["file"] == "/home/user/foo.py"

    def test_normalize_locations_target_uri(self, tmp_path):
        """targetUri extracted and file:// stripped."""
        client = self._make_client(tmp_path)
        locs = [
            {
                "targetUri": "file:///proj/bar.py",
                "targetRange": {"start": {"line": 7, "character": 2}},
            }
        ]
        result = client._normalize_locations(locs)
        assert result[0]["file"] == "/proj/bar.py"
        assert result[0]["line"] == 7
        assert result[0]["col"] == 2

    def test_normalize_locations_fallback(self, tmp_path):
        """Fallback to 'file' or 'relativePath' keys."""
        client = self._make_client(tmp_path)
        locs = [{"file": "src/foo.py", "range": {"start": {"line": 0, "character": 0}}}]
        result = client._normalize_locations(locs)
        assert result[0]["file"] == "src/foo.py"

        locs2 = [{"relativePath": "src/bar.py", "range": {"start": {"line": 1, "character": 0}}}]
        result2 = client._normalize_locations(locs2)
        assert result2[0]["file"] == "src/bar.py"

    def test_normalize_locations_missing_range(self, tmp_path):
        """Missing range defaults to line=0, col=0."""
        client = self._make_client(tmp_path)
        locs = [{"absolutePath": "/foo.py"}]
        result = client._normalize_locations(locs)
        assert result[0]["line"] == 0
        assert result[0]["col"] == 0

    def test_to_relative_absolute(self, tmp_path):
        """Absolute path within workspace converted to relative."""
        client = self._make_client(tmp_path)
        abs_path = tmp_path / "src" / "foo.py"
        assert client._to_relative(abs_path) == "src/foo.py"

    def test_to_relative_already_relative(self, tmp_path):
        """Relative path returned unchanged."""
        client = self._make_client(tmp_path)
        assert client._to_relative("src/foo.py") == "src/foo.py"

    def test_to_relative_outside_workspace(self, tmp_path):
        """Absolute path outside workspace returned as-is."""
        client = self._make_client(tmp_path)
        result = client._to_relative("/completely/different/path.py")
        assert result == "/completely/different/path.py"


# ---------------------------------------------------------------------------
# Reference cache
# ---------------------------------------------------------------------------


class TestReferenceCache:
    """Tests for in-memory reference cache on AuroraLSPClient."""

    def _make_client(self, tmp_path):
        client = AuroraLSPClient(workspace=tmp_path)
        return client

    @pytest.mark.asyncio
    async def test_cache_hit_avoids_server_call(self, tmp_path):
        """Second call with same args returns cached result without querying LSP."""
        import time

        client = self._make_client(tmp_path)

        fake_server = AsyncMock()
        fake_server.request_references = AsyncMock(
            return_value=[
                {
                    "absolutePath": "/proj/foo.py",
                    "range": {"start": {"line": 10, "character": 0}},
                }
            ]
        )
        fake_server.open_file = MagicMock(return_value=MagicMock())

        with patch.object(client, "_ensure_server", return_value=fake_server):
            result1 = await client.request_references("src/foo.py", 5, 0)
            result2 = await client.request_references("src/foo.py", 5, 0)

        # Server queried only once — second call served from cache
        assert fake_server.request_references.call_count == 1
        assert result1 == result2
        assert len(result1) == 1

    @pytest.mark.asyncio
    async def test_cache_miss_different_location(self, tmp_path):
        """Different (file, line, col) triggers a fresh LSP query."""
        client = self._make_client(tmp_path)

        fake_server = AsyncMock()
        fake_server.request_references = AsyncMock(return_value=[])
        fake_server.open_file = MagicMock(return_value=MagicMock())

        with patch.object(client, "_ensure_server", return_value=fake_server):
            await client.request_references("src/a.py", 1, 0)
            await client.request_references("src/a.py", 2, 0)

        assert fake_server.request_references.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_expiry(self, tmp_path, monkeypatch):
        """Expired entries are evicted and LSP is re-queried."""
        import time as time_mod

        client = self._make_client(tmp_path)
        client._ref_cache_ttl = 0.0  # expire immediately

        fake_server = AsyncMock()
        fake_server.request_references = AsyncMock(return_value=[])
        fake_server.open_file = MagicMock(return_value=MagicMock())

        with patch.object(client, "_ensure_server", return_value=fake_server):
            await client.request_references("src/a.py", 1, 0)
            # TTL=0 means next call should miss cache
            await client.request_references("src/a.py", 1, 0)

        assert fake_server.request_references.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_empty_results(self, tmp_path):
        """Empty results are cached too (avoids re-querying dead symbols)."""
        client = self._make_client(tmp_path)

        fake_server = AsyncMock()
        fake_server.request_references = AsyncMock(return_value=[])
        fake_server.open_file = MagicMock(return_value=MagicMock())

        with patch.object(client, "_ensure_server", return_value=fake_server):
            r1 = await client.request_references("src/a.py", 1, 0)
            r2 = await client.request_references("src/a.py", 1, 0)

        assert r1 == r2 == []
        assert fake_server.request_references.call_count == 1

    def test_clear_ref_cache(self, tmp_path):
        """clear_ref_cache() empties the cache dict."""
        client = self._make_client(tmp_path)
        client._ref_cache[("src/a.py", 1, 0)] = (0.0, [])
        assert len(client._ref_cache) == 1
        client.clear_ref_cache()
        assert len(client._ref_cache) == 0

    @pytest.mark.asyncio
    async def test_close_clears_cache(self, tmp_path):
        """close() clears reference cache along with other state."""
        client = self._make_client(tmp_path)
        client._ref_cache[("src/a.py", 1, 0)] = (0.0, [{"file": "x", "line": 0, "col": 0}])
        await client.close()
        assert len(client._ref_cache) == 0
