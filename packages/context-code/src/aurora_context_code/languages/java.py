"""Java code parser using tree-sitter.

This module provides the JavaParser class for extracting code elements
(classes, interfaces, methods, enums) from Java source files.
"""

import hashlib
import logging
import os
from pathlib import Path

from aurora_context_code.parser import CodeParser
from aurora_core.chunks.code_chunk import CodeChunk

# Try to import tree-sitter, fall back to text chunking if unavailable
TREE_SITTER_AVAILABLE = True
try:
    import tree_sitter
    import tree_sitter_java
except ImportError:
    TREE_SITTER_AVAILABLE = False

# Check environment variable override
if os.getenv("AURORA_SKIP_TREESITTER"):
    TREE_SITTER_AVAILABLE = False


logger = logging.getLogger(__name__)


class JavaParser(CodeParser):
    """Java code parser using tree-sitter.

    Extracts classes, interfaces, methods, and enums from Java files.
    """

    EXTENSIONS = {".java"}

    def __init__(self) -> None:
        """Initialize Java parser with tree-sitter grammar."""
        super().__init__(language="java")

        self.parser: tree_sitter.Parser | None

        if TREE_SITTER_AVAILABLE:
            java_language = tree_sitter.Language(tree_sitter_java.language())
            self.parser = tree_sitter.Parser(java_language)
            logger.debug("JavaParser initialized with tree-sitter")
        else:
            self.parser = None
            logger.warning(
                "Tree-sitter unavailable - using text chunking (reduced quality)\n"
                "Install with: pip install tree-sitter tree-sitter-java",
            )

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix in self.EXTENSIONS

    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Parse a Java source file and extract code elements."""
        try:
            if not file_path.is_absolute():
                logger.error(f"File path must be absolute: {file_path}")
                return []

            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return []

            if not self.can_parse(file_path):
                logger.warning(f"File extension not supported: {file_path}")
                return []

            try:
                source_code = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return []

            if self.parser is None:
                return self._get_fallback_chunks(file_path, source_code)

            tree = self.parser.parse(bytes(source_code, "utf-8"))

            if tree.root_node.has_error:
                logger.warning(f"Parse errors in {file_path}, extracting partial results")

            chunks: list[CodeChunk] = []

            # Extract classes and their methods
            chunks.extend(self._extract_classes(tree.root_node, file_path, source_code))

            # Extract interfaces
            chunks.extend(self._extract_interfaces(tree.root_node, file_path, source_code))

            # Extract enums
            chunks.extend(self._extract_enums(tree.root_node, file_path, source_code))

            logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Unexpected error parsing {file_path}: {e}", exc_info=True)
            return []

    def _extract_classes(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
        parent_name: str = "",
    ) -> list[CodeChunk]:
        """Extract class declarations and their methods."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "class_declaration"):
            try:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                class_name = source_code[name_node.start_byte : name_node.end_byte]
                qualified_name = f"{parent_name}.{class_name}" if parent_name else class_name

                # Build signature
                signature = self._build_class_signature(node, source_code, "class")

                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, qualified_name, line_start)
                docstring = self._extract_javadoc(node, source_code)
                complexity = self._calculate_complexity(node)

                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        file_path=str(file_path),
                        element_type="class",
                        name=qualified_name,
                        line_start=line_start,
                        line_end=line_end,
                        signature=signature,
                        docstring=docstring,
                        dependencies=[],
                        complexity_score=complexity,
                        language="java",
                    )
                )

                # Extract methods
                body_node = node.child_by_field_name("body")
                if body_node:
                    chunks.extend(
                        self._extract_methods(body_node, qualified_name, file_path, source_code)
                    )

            except Exception as e:
                logger.warning(f"Failed to extract class: {e}")
                continue

        return chunks

    def _extract_interfaces(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract interface declarations."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "interface_declaration"):
            try:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                name = source_code[name_node.start_byte : name_node.end_byte]

                signature = self._build_class_signature(node, source_code, "interface")

                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, name, line_start)
                docstring = self._extract_javadoc(node, source_code)

                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        file_path=str(file_path),
                        element_type="class",
                        name=name,
                        line_start=line_start,
                        line_end=line_end,
                        signature=signature,
                        docstring=docstring,
                        dependencies=[],
                        complexity_score=0.0,
                        language="java",
                    )
                )

                # Extract methods in interface
                body_node = node.child_by_field_name("body")
                if body_node:
                    chunks.extend(self._extract_methods(body_node, name, file_path, source_code))

            except Exception as e:
                logger.warning(f"Failed to extract interface: {e}")
                continue

        return chunks

    def _extract_enums(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract enum declarations."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "enum_declaration"):
            try:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                name = source_code[name_node.start_byte : name_node.end_byte]

                signature = f"enum {name}"

                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, name, line_start)
                docstring = self._extract_javadoc(node, source_code)

                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        file_path=str(file_path),
                        element_type="class",
                        name=name,
                        line_start=line_start,
                        line_end=line_end,
                        signature=signature,
                        docstring=docstring,
                        dependencies=[],
                        complexity_score=0.0,
                        language="java",
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to extract enum: {e}")
                continue

        return chunks

    def _extract_methods(
        self,
        class_body: tree_sitter.Node,
        class_name: str,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract methods from a class/interface body."""
        chunks: list[CodeChunk] = []

        for child in class_body.children:
            if child.type not in ("method_declaration", "constructor_declaration"):
                continue

            try:
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                method_name = source_code[name_node.start_byte : name_node.end_byte]
                qualified_name = f"{class_name}.{method_name}"

                # Build signature
                params_node = child.child_by_field_name("parameters")
                type_node = child.child_by_field_name("type")
                signature = ""
                if type_node:
                    signature += source_code[type_node.start_byte : type_node.end_byte] + " "
                signature += qualified_name
                if params_node:
                    signature += source_code[params_node.start_byte : params_node.end_byte]

                line_start = child.start_point[0] + 1
                line_end = child.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, qualified_name, line_start)
                docstring = self._extract_javadoc(child, source_code)
                complexity = self._calculate_complexity(child)

                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        file_path=str(file_path),
                        element_type="method",
                        name=qualified_name,
                        line_start=line_start,
                        line_end=line_end,
                        signature=signature,
                        docstring=docstring,
                        dependencies=[],
                        complexity_score=complexity,
                        language="java",
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to extract method: {e}")
                continue

        return chunks

    def _build_class_signature(self, node: tree_sitter.Node, source_code: str, keyword: str) -> str:
        """Build class/interface signature with extends/implements."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return keyword
        name = source_code[name_node.start_byte : name_node.end_byte]
        signature = f"{keyword} {name}"

        for child in node.children:
            if child.type == "superclass":
                signature += " " + source_code[child.start_byte : child.end_byte]
            elif child.type == "super_interfaces":
                signature += " " + source_code[child.start_byte : child.end_byte]

        return signature

    def _find_nodes_by_type(self, node: tree_sitter.Node, node_type: str) -> list[tree_sitter.Node]:
        """Find all nodes of a given type in the tree."""
        results: list[tree_sitter.Node] = []

        def traverse(n: tree_sitter.Node) -> None:
            if n.type == node_type:
                results.append(n)
            for child in n.children:
                traverse(child)

        traverse(node)
        return results

    def _extract_javadoc(self, node: tree_sitter.Node, source_code: str) -> str | None:
        """Extract Javadoc comment preceding a node."""
        try:
            prev_sibling = node.prev_sibling
            while prev_sibling and prev_sibling.type in ("comment", "block_comment", ""):
                text = source_code[prev_sibling.start_byte : prev_sibling.end_byte]
                if text.startswith("/**"):
                    return self._clean_javadoc(text)
                prev_sibling = prev_sibling.prev_sibling
            return None
        except Exception:
            return None

    def _clean_javadoc(self, comment: str) -> str | None:
        """Clean a Javadoc comment."""
        cleaned = comment.strip()
        if cleaned.startswith("/**"):
            cleaned = cleaned[3:]
        if cleaned.endswith("*/"):
            cleaned = cleaned[:-2]

        lines = []
        for line in cleaned.split("\n"):
            line = line.strip()
            if line.startswith("*"):
                line = line[1:].strip()
            lines.append(line)

        result = "\n".join(lines).strip()
        return result if result else None

    def _calculate_complexity(self, node: tree_sitter.Node) -> float:
        """Calculate cyclomatic complexity for a code element."""
        branch_types = {
            "if_statement",
            "for_statement",
            "enhanced_for_statement",
            "while_statement",
            "do_statement",
            "switch_expression",
            "switch_block_statement_group",
            "catch_clause",
            "ternary_expression",
        }

        branch_count = 0

        def count_branches(n: tree_sitter.Node) -> None:
            nonlocal branch_count
            if n.type in branch_types:
                branch_count += 1
            elif n.type == "binary_expression":
                for child in n.children:
                    if child.type in ("&&", "||"):
                        branch_count += 1
                        break
            for child in n.children:
                count_branches(child)

        count_branches(node)

        if branch_count == 0:
            return 0.0
        return min(branch_count / (branch_count + 10), 1.0)

    def _generate_chunk_id(self, file_path: Path, element_name: str, line_start: int) -> str:
        """Generate a unique chunk ID."""
        unique_string = f"{file_path}:{element_name}:{line_start}"
        hash_digest = hashlib.sha256(unique_string.encode()).hexdigest()
        return f"code:{self.language}:{hash_digest[:16]}"

    def _get_fallback_chunks(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Fallback chunking when tree-sitter is unavailable."""
        chunks: list[CodeChunk] = []
        lines = content.split("\n")
        chunk_size = 50

        for i in range(0, len(lines), chunk_size):
            line_start = i + 1
            line_end = min(i + chunk_size, len(lines))
            chunk_id = self._generate_chunk_id(file_path, f"chunk_{i}", line_start)

            chunk = CodeChunk(
                chunk_id=chunk_id,
                file_path=str(file_path),
                element_type="function",
                name=f"fallback_lines_{line_start}_{line_end}",
                line_start=line_start,
                line_end=line_end,
                signature="",
                docstring="Fallback text chunk (tree-sitter unavailable)",
                dependencies=[],
                complexity_score=0.0,
                language="java",
            )
            chunks.append(chunk)

        return chunks


__all__ = ["JavaParser"]
