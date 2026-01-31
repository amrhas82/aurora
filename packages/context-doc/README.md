# aurora-context-doc

Document parsing and indexing for Aurora memory system.

## Overview

`aurora-context-doc` provides hierarchical document indexing capabilities for PDF, DOCX, and Markdown files. It extracts document structure (TOC, sections, paragraphs) and stores them as DocChunks with parent-child relationships.

## Features

- **PDF Support**: Extract TOC and sections from PDF files using PyMuPDF
- **DOCX Support**: Parse Word documents with heading-based structure
- **Markdown Support**: Extract headings and sections from Markdown files
- **Hierarchical Storage**: Pre-computed section paths (breadcrumbs) for efficient retrieval
- **Lazy Loading**: Optional dependencies (PDF/DOCX parsers) loaded on demand

## Installation

Basic installation (no document parsing):
```bash
pip install aurora-context-doc
```

With PDF support:
```bash
pip install aurora-context-doc[pdf]
```

With DOCX support:
```bash
pip install aurora-context-doc[docx]
```

With all parsers:
```bash
pip install aurora-context-doc[all]
```

## Usage

### Indexing a PDF

```python
from aurora_context_doc import DocumentIndexer
from aurora_core.store import SQLiteStore

store = SQLiteStore(".aurora/memory.db")
indexer = DocumentIndexer(store)

# Index a single PDF
chunk_count = indexer.index_file("/path/to/manual.pdf")
print(f"Indexed {chunk_count} chunks")

# Index a directory of documents
chunk_count = indexer.index_directory("/path/to/docs")
print(f"Indexed {chunk_count} chunks from all documents")
```

### Querying Document Chunks

```python
from aurora_context_code.semantic import HybridRetriever

retriever = HybridRetriever(store, engine, provider)
results = retriever.retrieve("installation requirements", top_k=5)

for result in results:
    chunk = result['chunk']
    if hasattr(chunk, 'section_path'):
        breadcrumb = " > ".join(chunk.section_path)
        print(f"{breadcrumb}: {result['hybrid_score']:.3f}")
```

## Architecture

### Document Hierarchy

Documents are stored with dual hierarchy representation:

1. **parent_chunk_id**: Foreign key to parent chunk (DB efficiency)
2. **section_path**: Pre-computed breadcrumb list (O(1) display)

Example:
```python
DocChunk(
    chunk_id="doc-123",
    element_type="section",
    name="2.1.3 Dependencies",
    parent_chunk_id="doc-122",  # Points to "2.1 Installation"
    section_path=["Chapter 2", "2.1 Installation", "2.1.3 Dependencies"],
    page_start=15,
    page_end=16
)
```

### Element Types

- **toc_entry**: Header-only chunk (high signal, structural anchor)
- **section**: Full section with content
- **paragraph**: Standalone paragraph (fallback)
- **table**: Extracted table content

### Tiered Extraction (PDF)

1. **Tier 1**: Use `doc.get_toc()` for explicit TOC
2. **Tier 2**: Font size detection for inferred headings
3. **Tier 3**: Paragraph clustering with overlap

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/context_doc/ -v

# Integration tests
pytest tests/integration/context_doc/ -v
```

### Code Quality

```bash
# Lint
ruff check src/

# Format
ruff format src/

# Type check
mypy src/
```

## License

MIT License - see LICENSE file for details.
