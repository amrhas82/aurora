"""Document parsing and indexing for Aurora memory system.

This package provides hierarchical document indexing for PDF, DOCX, and Markdown
files with support for TOC extraction, section hierarchy, and pre-computed breadcrumbs.
"""

__version__ = "0.10.3"

# Lazy imports to avoid startup penalty
__all__ = [
    "DocumentIndexer",
    "DocumentParser",
    "PDFParser",
    "DOCXParser",
]


def __getattr__(name: str):
    """Lazy import for package components."""
    if name == "DocumentIndexer":
        from aurora_context_doc.indexer import DocumentIndexer

        return DocumentIndexer
    elif name == "DocumentParser":
        from aurora_context_doc.parser.base import DocumentParser

        return DocumentParser
    elif name == "PDFParser":
        from aurora_context_doc.parser.pdf import PDFParser

        return PDFParser
    elif name == "DOCXParser":
        from aurora_context_doc.parser.docx import DOCXParser

        return DOCXParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
