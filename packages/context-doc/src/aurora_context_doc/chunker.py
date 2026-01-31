"""Section-aware document chunking utilities."""

from aurora_core.chunks import DocChunk


class DocumentChunker:
    """Utilities for section-aware chunk splitting and merging.

    Handles overlap for section boundaries and ensures chunks stay within
    reasonable size limits while preserving hierarchy.
    """

    def __init__(self, max_chunk_size: int = 2000, overlap: int = 200):
        """Initialize document chunker.

        Args:
            max_chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap at section boundaries

        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def split_large_section(self, chunk: DocChunk) -> list[DocChunk]:
        """Split a large section into multiple chunks with overlap.

        Args:
            chunk: DocChunk with content exceeding max_chunk_size

        Returns:
            List of DocChunk objects split from the original

        """
        if len(chunk.content) <= self.max_chunk_size:
            return [chunk]

        # Split content into overlapping windows
        chunks = []
        content = chunk.content
        start = 0
        part_num = 0

        while start < len(content):
            # Extract chunk with overlap
            end = min(start + self.max_chunk_size, len(content))

            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence end markers
                for marker in [".", "!", "?", "\n\n"]:
                    last_break = content.rfind(marker, start, end)
                    if last_break > start:
                        end = last_break + 1
                        break

            chunk_content = content[start:end]

            # Create new chunk with same metadata
            new_chunk = DocChunk(
                chunk_id=f"{chunk.chunk_id}-part{part_num}",
                file_path=chunk.file_path,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                element_type=chunk.element_type,
                name=f"{chunk.name} (part {part_num + 1})",
                content=chunk_content,
                parent_chunk_id=chunk.parent_chunk_id,
                section_path=chunk.section_path,
                section_level=chunk.section_level,
                document_type=chunk.document_type,
                created_at=chunk.created_at,
                updated_at=chunk.updated_at,
            )

            chunks.append(new_chunk)

            # Move start forward (with overlap)
            start = end - self.overlap
            part_num += 1

        return chunks

    def merge_small_sections(self, chunks: list[DocChunk]) -> list[DocChunk]:
        """Merge very small adjacent sections to reduce chunk count.

        Args:
            chunks: List of DocChunk objects to potentially merge

        Returns:
            List of merged DocChunk objects

        """
        if not chunks:
            return []

        merged = []
        current_merge = None

        for chunk in chunks:
            # Don't merge TOC entries (structural anchors)
            if chunk.element_type == "toc_entry":
                if current_merge:
                    merged.append(current_merge)
                    current_merge = None
                merged.append(chunk)
                continue

            # Start new merge if content is small
            if len(chunk.content) < self.max_chunk_size // 4:
                if current_merge is None:
                    current_merge = chunk
                else:
                    # Try to merge with current
                    combined_length = len(current_merge.content) + len(chunk.content)

                    if combined_length <= self.max_chunk_size:
                        # Merge into current
                        current_merge.content += "\n\n" + chunk.content
                        current_merge.name += f" + {chunk.name}"
                    else:
                        # Current merge is full, start new one
                        merged.append(current_merge)
                        current_merge = chunk
            else:
                # Large chunk, add current merge and this chunk separately
                if current_merge:
                    merged.append(current_merge)
                    current_merge = None
                merged.append(chunk)

        # Add final merge if any
        if current_merge:
            merged.append(current_merge)

        return merged


__all__ = ["DocumentChunker"]
