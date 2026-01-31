"""Document parser implementations for PDF, DOCX, and Markdown."""

from aurora_context_doc.parser.base import DocumentParser

__all__ = ["DocumentParser"]


def __getattr__(name: str):
    """Lazy import for parser implementations."""
    if name == "PDFParser":
        from aurora_context_doc.parser.pdf import PDFParser

        return PDFParser
    elif name == "DOCXParser":
        from aurora_context_doc.parser.docx import DOCXParser

        return DOCXParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
