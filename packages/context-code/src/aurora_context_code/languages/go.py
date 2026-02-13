"""Go code parser using tree-sitter.

This module provides the GoParser class for extracting code elements
(functions, methods, structs, interfaces) from Go source files.
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
    import tree_sitter_go
except ImportError:
    TREE_SITTER_AVAILABLE = False

# Check environment variable override
if os.getenv("AURORA_SKIP_TREESITTER"):
    TREE_SITTER_AVAILABLE = False


logger = logging.getLogger(__name__)


class GoParser(CodeParser):
    """Go code parser using tree-sitter.

    Extracts functions, methods, structs, and interfaces from Go files.
    """

    EXTENSIONS = {".go"}

    def __init__(self) -> None:
        """Initialize Go parser with tree-sitter grammar."""
        super().__init__(language="go")

        self.parser: tree_sitter.Parser | None

        if TREE_SITTER_AVAILABLE:
            go_language = tree_sitter.Language(tree_sitter_go.language())
            self.parser = tree_sitter.Parser(go_language)
            logger.debug("GoParser initialized with tree-sitter")
        else:
            self.parser = None
            logger.warning(
                "Tree-sitter unavailable - using text chunking (reduced quality)\n"
                "Install with: pip install tree-sitter tree-sitter-go",
            )

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix in self.EXTENSIONS

    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Parse a Go source file and extract code elements."""
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

            # Extract functions
            chunks.extend(self._extract_functions(tree.root_node, file_path, source_code))

            # Extract methods (functions with receivers)
            chunks.extend(self._extract_methods(tree.root_node, file_path, source_code))

            # Extract type declarations (structs, interfaces)
            chunks.extend(self._extract_type_declarations(tree.root_node, file_path, source_code))

            logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Unexpected error parsing {file_path}: {e}", exc_info=True)
            return []

    def _extract_functions(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract top-level function declarations (no receiver)."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "function_declaration"):
            try:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                name = source_code[name_node.start_byte : name_node.end_byte]

                params_node = node.child_by_field_name("parameters")
                result_node = node.child_by_field_name("result")
                signature = f"func {name}"
                if params_node:
                    signature += source_code[params_node.start_byte : params_node.end_byte]
                if result_node:
                    signature += " " + source_code[result_node.start_byte : result_node.end_byte]

                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, name, line_start)
                docstring = self._extract_go_doc(node, source_code)
                complexity = self._calculate_complexity(node)

                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        file_path=str(file_path),
                        element_type="function",
                        name=name,
                        line_start=line_start,
                        line_end=line_end,
                        signature=signature,
                        docstring=docstring,
                        dependencies=[],
                        complexity_score=complexity,
                        language="go",
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to extract function: {e}")
                continue

        return chunks

    def _extract_methods(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract method declarations (functions with receivers)."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "method_declaration"):
            try:
                name_node = node.child_by_field_name("name")
                receiver_node = node.child_by_field_name("receiver")
                if not name_node:
                    continue

                method_name = source_code[name_node.start_byte : name_node.end_byte]

                # Extract receiver type name for qualified name
                receiver_type = ""
                if receiver_node:
                    for child in receiver_node.children:
                        if child.type == "parameter_declaration":
                            type_node = child.child_by_field_name("type")
                            if type_node:
                                receiver_type = source_code[
                                    type_node.start_byte : type_node.end_byte
                                ].lstrip("*")

                qualified_name = f"{receiver_type}.{method_name}" if receiver_type else method_name

                params_node = node.child_by_field_name("parameters")
                result_node = node.child_by_field_name("result")
                signature = "func "
                if receiver_node:
                    signature += (
                        source_code[receiver_node.start_byte : receiver_node.end_byte] + " "
                    )
                signature += method_name
                if params_node:
                    signature += source_code[params_node.start_byte : params_node.end_byte]
                if result_node:
                    signature += " " + source_code[result_node.start_byte : result_node.end_byte]

                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, qualified_name, line_start)
                docstring = self._extract_go_doc(node, source_code)
                complexity = self._calculate_complexity(node)

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
                        language="go",
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to extract method: {e}")
                continue

        return chunks

    def _extract_type_declarations(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract type declarations (structs, interfaces)."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "type_declaration"):
            for child in node.children:
                if child.type != "type_spec":
                    continue
                try:
                    name_node = child.child_by_field_name("name")
                    type_node = child.child_by_field_name("type")
                    if not name_node:
                        continue

                    name = source_code[name_node.start_byte : name_node.end_byte]

                    element_type = "class"
                    if type_node and type_node.type == "struct_type":
                        signature = f"type {name} struct"
                    elif type_node and type_node.type == "interface_type":
                        signature = f"type {name} interface"
                    else:
                        signature = f"type {name}"

                    line_start = child.start_point[0] + 1
                    line_end = child.end_point[0] + 1
                    chunk_id = self._generate_chunk_id(file_path, name, line_start)
                    docstring = self._extract_go_doc(node, source_code)

                    chunks.append(
                        CodeChunk(
                            chunk_id=chunk_id,
                            file_path=str(file_path),
                            element_type=element_type,
                            name=name,
                            line_start=line_start,
                            line_end=line_end,
                            signature=signature,
                            docstring=docstring,
                            dependencies=[],
                            complexity_score=0.0,
                            language="go",
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to extract type declaration: {e}")
                    continue

        return chunks

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

    def _extract_go_doc(self, node: tree_sitter.Node, source_code: str) -> str | None:
        """Extract Go doc comment preceding a node."""
        try:
            prev_sibling = node.prev_sibling
            lines = []
            while prev_sibling and prev_sibling.type == "comment":
                comment = source_code[prev_sibling.start_byte : prev_sibling.end_byte]
                if comment.startswith("//"):
                    lines.insert(0, comment[2:].strip())
                prev_sibling = prev_sibling.prev_sibling

            result = "\n".join(lines).strip()
            return result if result else None
        except Exception:
            return None

    def _calculate_complexity(self, node: tree_sitter.Node) -> float:
        """Calculate cyclomatic complexity for a code element."""
        branch_types = {
            "if_statement",
            "for_statement",
            "expression_switch_statement",
            "type_switch_statement",
            "select_statement",
            "expression_case",
            "type_case",
            "communication_case",
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
                language="go",
            )
            chunks.append(chunk)

        return chunks


__all__ = ["GoParser"]
