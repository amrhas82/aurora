"""Aurora LSP - Code intelligence powered by Language Server Protocol.

Provides:
- Find usages (excluding imports)
- Dead code detection
- Linting diagnostics
- Call hierarchy (where supported)

Built on multilspy (Microsoft) with custom import filtering and analysis layers.
"""

from aurora_lsp.client import AuroraLSPClient
from aurora_lsp.analysis import CodeAnalyzer, SymbolKind
from aurora_lsp.filters import ImportFilter
from aurora_lsp.diagnostics import DiagnosticsFormatter
from aurora_lsp.facade import AuroraLSP

__all__ = [
    "AuroraLSP",
    "AuroraLSPClient",
    "CodeAnalyzer",
    "ImportFilter",
    "DiagnosticsFormatter",
    "SymbolKind",
]

__version__ = "0.1.0"
