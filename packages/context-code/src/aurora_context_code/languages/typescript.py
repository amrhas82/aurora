"""TypeScript code parser using tree-sitter.

This module provides the TypeScriptParser class for extracting code elements
(functions, classes, methods, interfaces) from TypeScript and TSX source files.
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
    import tree_sitter_typescript
except ImportError:
    TREE_SITTER_AVAILABLE = False

# Check environment variable override
if os.getenv("AURORA_SKIP_TREESITTER"):
    TREE_SITTER_AVAILABLE = False


logger = logging.getLogger(__name__)


class TypeScriptParser(CodeParser):
    """TypeScript code parser using tree-sitter.

    Extracts functions, classes, methods, and interfaces from TypeScript/TSX files.
    Handles both .ts and .tsx (React) file extensions.
    """

    # Supported file extensions
    EXTENSIONS = {".ts", ".tsx"}

    def __init__(self) -> None:
        """Initialize TypeScript parser with tree-sitter grammar."""
        super().__init__(language="typescript")

        self.parser: tree_sitter.Parser | None
        self.tsx_parser: tree_sitter.Parser | None

        if TREE_SITTER_AVAILABLE:
            # Initialize parsers for both TS and TSX
            ts_language = tree_sitter.Language(tree_sitter_typescript.language_typescript())
            tsx_language = tree_sitter.Language(tree_sitter_typescript.language_tsx())
            self.parser = tree_sitter.Parser(ts_language)
            self.tsx_parser = tree_sitter.Parser(tsx_language)
            logger.debug("TypeScriptParser initialized with tree-sitter")
        else:
            self.parser = None
            self.tsx_parser = None
            logger.warning(
                "Tree-sitter unavailable - using text chunking (reduced quality)\n"
                "Install with: pip install tree-sitter tree-sitter-typescript",
            )

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix in self.EXTENSIONS

    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Parse a TypeScript source file and extract code elements."""
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

            # Use TSX parser for .tsx files, regular parser for .ts
            parser = self.tsx_parser if file_path.suffix == ".tsx" else self.parser
            if parser is None:
                return self._get_fallback_chunks(file_path, source_code)
            tree = parser.parse(bytes(source_code, "utf-8"))

            if tree.root_node.has_error:
                logger.warning(f"Parse errors in {file_path}, extracting partial results")

            chunks: list[CodeChunk] = []

            # Extract functions (including arrow functions and function expressions)
            chunks.extend(self._extract_functions(tree.root_node, file_path, source_code))

            # Extract classes and methods
            chunks.extend(self._extract_classes_and_methods(tree.root_node, file_path, source_code))

            # Extract interfaces
            chunks.extend(self._extract_interfaces(tree.root_node, file_path, source_code))

            # Extract type aliases
            chunks.extend(self._extract_type_aliases(tree.root_node, file_path, source_code))

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
        """Extract function definitions from the AST."""
        chunks: list[CodeChunk] = []

        # Function declarations: function foo() {}
        for node in self._find_nodes_by_type(root_node, "function_declaration"):
            if self._is_inside_class(node):
                continue
            chunk = self._extract_function_chunk(node, file_path, source_code)
            if chunk:
                chunks.append(chunk)

        # Arrow functions assigned to variables: const foo = () => {}
        # Lexical declarations with arrow functions
        for node in self._find_nodes_by_type(root_node, "lexical_declaration"):
            if self._is_inside_class(node):
                continue
            chunk = self._extract_arrow_function(node, file_path, source_code)
            if chunk:
                chunks.append(chunk)

        # Export statements with functions
        for node in self._find_nodes_by_type(root_node, "export_statement"):
            # Check for exported function declaration
            for child in node.children:
                if child.type == "function_declaration":
                    chunk = self._extract_function_chunk(child, file_path, source_code)
                    if chunk:
                        chunks.append(chunk)
                elif child.type == "lexical_declaration":
                    chunk = self._extract_arrow_function(child, file_path, source_code)
                    if chunk:
                        chunks.append(chunk)

        return chunks

    def _extract_function_chunk(
        self,
        node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> CodeChunk | None:
        """Extract a function declaration into a CodeChunk."""
        try:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return None
            name = source_code[name_node.start_byte : name_node.end_byte]

            # Build signature
            params_node = node.child_by_field_name("parameters")
            return_type = node.child_by_field_name("return_type")
            signature = f"function {name}"
            if params_node:
                signature += source_code[params_node.start_byte : params_node.end_byte]
            if return_type:
                signature += source_code[return_type.start_byte : return_type.end_byte]

            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            chunk_id = self._generate_chunk_id(file_path, name, line_start)
            docstring = self._extract_jsdoc(node, source_code)
            complexity = self._calculate_complexity(node)

            return CodeChunk(
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
                language="typescript",
            )
        except Exception as e:
            logger.warning(f"Failed to extract function: {e}")
            return None

    def _extract_arrow_function(
        self,
        node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> CodeChunk | None:
        """Extract arrow function from lexical declaration."""
        try:
            # Find variable declarator with arrow function
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")

                    if not name_node or not value_node:
                        continue

                    # Check if value is an arrow function
                    if value_node.type != "arrow_function":
                        continue

                    name = source_code[name_node.start_byte : name_node.end_byte]

                    # Build signature
                    params_node = value_node.child_by_field_name("parameters")
                    return_type = value_node.child_by_field_name("return_type")
                    signature = f"const {name} = "
                    if params_node:
                        signature += source_code[params_node.start_byte : params_node.end_byte]
                    signature += " =>"
                    if return_type:
                        signature += source_code[return_type.start_byte : return_type.end_byte]

                    line_start = node.start_point[0] + 1
                    line_end = node.end_point[0] + 1
                    chunk_id = self._generate_chunk_id(file_path, name, line_start)
                    docstring = self._extract_jsdoc(node, source_code)
                    complexity = self._calculate_complexity(value_node)

                    return CodeChunk(
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
                        language="typescript",
                    )
            return None
        except Exception as e:
            logger.warning(f"Failed to extract arrow function: {e}")
            return None

    def _extract_classes_and_methods(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract class definitions and their methods."""
        chunks: list[CodeChunk] = []

        for class_node in self._find_nodes_by_type(root_node, "class_declaration"):
            try:
                name_node = class_node.child_by_field_name("name")
                if not name_node:
                    continue
                class_name = source_code[name_node.start_byte : name_node.end_byte]

                # Build signature with extends/implements
                signature = f"class {class_name}"
                heritage = class_node.child_by_field_name("heritage")
                if heritage:
                    signature += " " + source_code[heritage.start_byte : heritage.end_byte]

                line_start = class_node.start_point[0] + 1
                line_end = class_node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, class_name, line_start)
                docstring = self._extract_jsdoc(class_node, source_code)
                complexity = self._calculate_complexity(class_node)

                chunk = CodeChunk(
                    chunk_id=chunk_id,
                    file_path=str(file_path),
                    element_type="class",
                    name=class_name,
                    line_start=line_start,
                    line_end=line_end,
                    signature=signature,
                    docstring=docstring,
                    dependencies=[],
                    complexity_score=complexity,
                    language="typescript",
                )
                chunks.append(chunk)

                # Extract methods
                body_node = class_node.child_by_field_name("body")
                if body_node:
                    chunks.extend(
                        self._extract_methods(body_node, class_name, file_path, source_code),
                    )

            except Exception as e:
                logger.warning(f"Failed to extract class: {e}")
                continue

        return chunks

    def _extract_methods(
        self,
        class_body: tree_sitter.Node,
        class_name: str,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract methods from a class body."""
        chunks: list[CodeChunk] = []

        for child in class_body.children:
            if child.type not in ("method_definition", "public_field_definition"):
                continue

            try:
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                method_name = source_code[name_node.start_byte : name_node.end_byte]
                qualified_name = f"{class_name}.{method_name}"

                # Build signature
                params_node = child.child_by_field_name("parameters")
                return_type = child.child_by_field_name("return_type")
                signature = qualified_name
                if params_node:
                    signature += source_code[params_node.start_byte : params_node.end_byte]
                if return_type:
                    signature += source_code[return_type.start_byte : return_type.end_byte]

                line_start = child.start_point[0] + 1
                line_end = child.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, qualified_name, line_start)
                docstring = self._extract_jsdoc(child, source_code)
                complexity = self._calculate_complexity(child)

                chunk = CodeChunk(
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
                    language="typescript",
                )
                chunks.append(chunk)

            except Exception as e:
                logger.warning(f"Failed to extract method: {e}")
                continue

        return chunks

    def _extract_interfaces(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract interface definitions."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "interface_declaration"):
            try:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                name = source_code[name_node.start_byte : name_node.end_byte]

                # Build signature with extends
                signature = f"interface {name}"
                for child in node.children:
                    if child.type == "extends_type_clause":
                        signature += " " + source_code[child.start_byte : child.end_byte]
                        break

                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, name, line_start)
                docstring = self._extract_jsdoc(node, source_code)

                chunk = CodeChunk(
                    chunk_id=chunk_id,
                    file_path=str(file_path),
                    element_type="class",  # Use "class" for interfaces
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    signature=signature,
                    docstring=docstring,
                    dependencies=[],
                    complexity_score=0.0,
                    language="typescript",
                )
                chunks.append(chunk)

            except Exception as e:
                logger.warning(f"Failed to extract interface: {e}")
                continue

        return chunks

    def _extract_type_aliases(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract type alias definitions."""
        chunks: list[CodeChunk] = []

        for node in self._find_nodes_by_type(root_node, "type_alias_declaration"):
            try:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                name = source_code[name_node.start_byte : name_node.end_byte]

                # Get the full type definition for signature
                signature = source_code[node.start_byte : node.end_byte].split("\n")[0]
                if len(signature) > 100:
                    signature = signature[:100] + "..."

                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1
                chunk_id = self._generate_chunk_id(file_path, name, line_start)
                docstring = self._extract_jsdoc(node, source_code)

                chunk = CodeChunk(
                    chunk_id=chunk_id,
                    file_path=str(file_path),
                    element_type="class",  # Use "class" for type aliases
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    signature=signature,
                    docstring=docstring,
                    dependencies=[],
                    complexity_score=0.0,
                    language="typescript",
                )
                chunks.append(chunk)

            except Exception as e:
                logger.warning(f"Failed to extract type alias: {e}")
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

    def _is_inside_class(self, node: tree_sitter.Node) -> bool:
        """Check if a node is inside a class definition."""
        current = node.parent
        while current:
            if current.type == "class_declaration":
                return True
            current = current.parent
        return False

    def _extract_jsdoc(self, node: tree_sitter.Node, source_code: str) -> str | None:
        """Extract JSDoc comment preceding a node."""
        try:
            # Look for comment node before this node
            prev_sibling = node.prev_sibling
            while prev_sibling and prev_sibling.type in ("comment", "newline", ""):
                if prev_sibling.type == "comment":
                    comment = source_code[prev_sibling.start_byte : prev_sibling.end_byte]
                    # Check if it's a JSDoc comment
                    if comment.startswith("/**"):
                        return self._clean_jsdoc(comment)
                prev_sibling = prev_sibling.prev_sibling
            return None
        except Exception:
            return None

    def _clean_jsdoc(self, comment: str) -> str | None:
        """Clean a JSDoc comment."""
        # Remove /** and */
        cleaned = comment.strip()
        if cleaned.startswith("/**"):
            cleaned = cleaned[3:]
        if cleaned.endswith("*/"):
            cleaned = cleaned[:-2]

        # Remove leading * from each line
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
            "for_in_statement",
            "while_statement",
            "do_statement",
            "switch_statement",
            "switch_case",
            "catch_clause",
            "ternary_expression",
            "binary_expression",  # && and || operators
        }

        branch_count = 0

        def count_branches(n: tree_sitter.Node) -> None:
            nonlocal branch_count
            if n.type in branch_types:
                # For binary expressions, only count && and ||
                if n.type == "binary_expression":
                    for child in n.children:
                        if child.type == "&&" or child.type == "||":
                            branch_count += 1
                            break
                else:
                    branch_count += 1
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
                language="typescript",
            )
            chunks.append(chunk)

        return chunks


__all__ = ["TypeScriptParser"]
