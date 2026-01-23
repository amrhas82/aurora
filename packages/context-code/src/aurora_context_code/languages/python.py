"""Python code parser using tree-sitter.

This module provides the PythonParser class for extracting code elements
(functions, classes, methods) from Python source files.
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
    import tree_sitter_python
except ImportError:
    TREE_SITTER_AVAILABLE = False

# Check environment variable override
if os.getenv("AURORA_SKIP_TREESITTER"):
    TREE_SITTER_AVAILABLE = False


logger = logging.getLogger(__name__)


class PythonParser(CodeParser):
    """Python code parser using tree-sitter.

    Extracts functions, classes, and methods from Python source files,
    including:
    - Element name, signature, and location (line range)
    - Docstrings
    - Cyclomatic complexity metrics
    - Dependencies (imports and function calls)

    Handles parse errors gracefully by logging and returning empty results.
    """

    # Supported file extensions
    EXTENSIONS = {".py", ".pyi"}

    def __init__(self) -> None:
        """Initialize Python parser with tree-sitter grammar."""
        super().__init__(language="python")

        # Declare parser type (may be None if tree-sitter unavailable)
        self.parser: tree_sitter.Parser | None

        if TREE_SITTER_AVAILABLE:
            # Initialize tree-sitter parser
            # Wrap the PyCapsule in tree_sitter.Language
            python_language = tree_sitter.Language(tree_sitter_python.language())
            self.parser = tree_sitter.Parser(python_language)
            logger.debug("PythonParser initialized with tree-sitter")
        else:
            self.parser = None
            logger.warning(
                "Tree-sitter unavailable - using text chunking (reduced quality)\n"
                "→ Install with: pip install tree-sitter tree-sitter-python",
            )

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if file has .py or .pyi extension, False otherwise

        """
        return file_path.suffix in self.EXTENSIONS

    def parse(self, file_path: Path) -> list[CodeChunk]:
        """Parse a Python source file and extract code elements.

        Args:
            file_path: Absolute path to Python source file

        Returns:
            List of CodeChunk instances for functions, classes, and methods.
            Returns empty list if parsing fails or file contains no elements.

        """
        try:
            # Validate file path
            if not file_path.is_absolute():
                logger.error(f"File path must be absolute: {file_path}")
                return []

            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return []

            if not self.can_parse(file_path):
                logger.warning(f"File extension not supported: {file_path}")
                return []

            # Read source code
            try:
                source_code = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return []

            # Use fallback chunking if tree-sitter unavailable
            if self.parser is None:
                return self._get_fallback_chunks(file_path, source_code)

            # Parse with tree-sitter
            tree = self.parser.parse(bytes(source_code, "utf-8"))

            if tree.root_node.has_error:
                logger.warning(f"Parse errors in {file_path}, extracting partial results")

            # Extract all code elements
            chunks: list[CodeChunk] = []

            # Extract functions
            function_chunks = self._extract_functions(tree.root_node, file_path, source_code)
            chunks.extend(function_chunks)

            # Extract classes and methods
            class_and_method_chunks = self._extract_classes_and_methods(
                tree.root_node,
                file_path,
                source_code,
            )
            chunks.extend(class_and_method_chunks)

            # Extract dependencies (imports and function calls) for all chunks
            # Note: This is a simple implementation. Full dependency tracking would require
            # flow analysis and tracking variable assignments.
            imports = self._extract_imports(tree.root_node, source_code)
            for chunk in chunks:
                chunk.dependencies = self._identify_dependencies(chunk, imports, chunks)

            logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
            return chunks

        except Exception as e:
            # Catch-all for unexpected errors - log and return empty
            logger.error(f"Unexpected error parsing {file_path}: {e}", exc_info=True)
            return []

    def _extract_functions(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract function definitions from the AST.

        Args:
            root_node: Root node of the syntax tree
            file_path: Source file path
            source_code: Source code text

        Returns:
            List of CodeChunk instances for functions

        """
        chunks: list[CodeChunk] = []

        # Query for function definitions at module level
        # (Class methods will be handled separately in task 4.5)
        for node in self._find_nodes_by_type(root_node, "function_definition"):
            try:
                # Skip if this function is inside a class (it's a method)
                if self._is_inside_class(node):
                    continue

                # Extract function name
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                name = source_code[name_node.start_byte : name_node.end_byte]

                # Extract parameters for signature
                parameters_node = node.child_by_field_name("parameters")
                signature = None
                if parameters_node:
                    params_text = source_code[parameters_node.start_byte : parameters_node.end_byte]
                    signature = f"{name}{params_text}"

                # Get line numbers (tree-sitter uses 0-indexed, we use 1-indexed)
                line_start = node.start_point[0] + 1
                line_end = node.end_point[0] + 1

                # Generate chunk ID
                chunk_id = self._generate_chunk_id(file_path, name, line_start)

                # Extract docstring
                docstring = self._extract_docstring(node, source_code)

                # Calculate complexity
                complexity_score = self._calculate_complexity(node)

                # Create CodeChunk (dependencies added in later task)
                chunk = CodeChunk(
                    chunk_id=chunk_id,
                    file_path=str(file_path),
                    element_type="function",
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    signature=signature,
                    docstring=docstring,
                    dependencies=[],  # TODO: Extract in task 4.8
                    complexity_score=complexity_score,
                    language="python",
                )

                chunks.append(chunk)
                logger.debug(f"Extracted function: {name} at lines {line_start}-{line_end}")

            except Exception as e:
                logger.warning(f"Failed to extract function from node: {e}")
                continue

        return chunks

    def _extract_classes_and_methods(
        self,
        root_node: tree_sitter.Node,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract class definitions and their methods from the AST.

        Args:
            root_node: Root node of the syntax tree
            file_path: Source file path
            source_code: Source code text

        Returns:
            List of CodeChunk instances for classes and methods

        """
        chunks: list[CodeChunk] = []

        # Find all class definitions
        for class_node in self._find_nodes_by_type(root_node, "class_definition"):
            try:
                # Extract class name
                name_node = class_node.child_by_field_name("name")
                if not name_node:
                    continue
                class_name = source_code[name_node.start_byte : name_node.end_byte]

                # Extract class signature (with base classes if present)
                signature = class_name
                superclasses_node = class_node.child_by_field_name("superclasses")
                if superclasses_node:
                    bases_text = source_code[
                        superclasses_node.start_byte : superclasses_node.end_byte
                    ]
                    signature = f"{class_name}{bases_text}"

                # Get line numbers
                line_start = class_node.start_point[0] + 1
                line_end = class_node.end_point[0] + 1

                # Generate chunk ID for class
                chunk_id = self._generate_chunk_id(file_path, class_name, line_start)

                # Extract docstring
                docstring = self._extract_docstring(class_node, source_code)

                # Calculate complexity
                complexity_score = self._calculate_complexity(class_node)

                # Create CodeChunk for class
                chunk = CodeChunk(
                    chunk_id=chunk_id,
                    file_path=str(file_path),
                    element_type="class",
                    name=class_name,
                    line_start=line_start,
                    line_end=line_end,
                    signature=signature,
                    docstring=docstring,
                    dependencies=[],  # TODO: Extract in task 4.8
                    complexity_score=complexity_score,
                    language="python",
                )

                chunks.append(chunk)
                logger.debug(f"Extracted class: {class_name} at lines {line_start}-{line_end}")

                # Extract methods within this class
                class_body = class_node.child_by_field_name("body")
                if class_body:
                    method_chunks = self._extract_methods(
                        class_body,
                        class_name,
                        file_path,
                        source_code,
                    )
                    chunks.extend(method_chunks)

            except Exception as e:
                logger.warning(f"Failed to extract class from node: {e}")
                continue

        return chunks

    def _extract_methods(
        self,
        class_body_node: tree_sitter.Node,
        class_name: str,
        file_path: Path,
        source_code: str,
    ) -> list[CodeChunk]:
        """Extract methods from a class body.

        Args:
            class_body_node: Class body node
            class_name: Name of the containing class
            file_path: Source file path
            source_code: Source code text

        Returns:
            List of CodeChunk instances for methods

        """
        chunks: list[CodeChunk] = []

        # Find function definitions in the class body
        for method_node in self._find_nodes_by_type(class_body_node, "function_definition"):
            try:
                # Extract method name
                name_node = method_node.child_by_field_name("name")
                if not name_node:
                    continue
                method_name = source_code[name_node.start_byte : name_node.end_byte]

                # Create qualified name (ClassName.method_name)
                qualified_name = f"{class_name}.{method_name}"

                # Extract parameters for signature
                parameters_node = method_node.child_by_field_name("parameters")
                signature = None
                if parameters_node:
                    params_text = source_code[parameters_node.start_byte : parameters_node.end_byte]
                    signature = f"{qualified_name}{params_text}"

                # Get line numbers
                line_start = method_node.start_point[0] + 1
                line_end = method_node.end_point[0] + 1

                # Generate chunk ID (use qualified name)
                chunk_id = self._generate_chunk_id(file_path, qualified_name, line_start)

                # Extract docstring
                docstring = self._extract_docstring(method_node, source_code)

                # Calculate complexity
                complexity_score = self._calculate_complexity(method_node)

                # Create CodeChunk for method
                chunk = CodeChunk(
                    chunk_id=chunk_id,
                    file_path=str(file_path),
                    element_type="method",
                    name=qualified_name,
                    line_start=line_start,
                    line_end=line_end,
                    signature=signature,
                    docstring=docstring,
                    dependencies=[],  # TODO: Extract in task 4.8
                    complexity_score=complexity_score,
                    language="python",
                )

                chunks.append(chunk)
                logger.debug(f"Extracted method: {qualified_name} at lines {line_start}-{line_end}")

            except Exception as e:
                logger.warning(f"Failed to extract method from node: {e}")
                continue

        return chunks

    def _find_nodes_by_type(self, node: tree_sitter.Node, node_type: str) -> list[tree_sitter.Node]:
        """Find all nodes of a given type in the tree.

        Args:
            node: Root node to search from
            node_type: Node type to find (e.g., "function_definition")

        Returns:
            List of matching nodes

        """
        results: list[tree_sitter.Node] = []

        def traverse(n: tree_sitter.Node) -> None:
            if n.type == node_type:
                results.append(n)
            for child in n.children:
                traverse(child)

        traverse(node)
        return results

    def _is_inside_class(self, node: tree_sitter.Node) -> bool:
        """Check if a node is inside a class definition.

        Args:
            node: Node to check

        Returns:
            True if node is inside a class, False otherwise

        """
        current = node.parent
        while current:
            if current.type == "class_definition":
                return True
            current = current.parent
        return False

    def _extract_docstring(self, node: tree_sitter.Node, source_code: str) -> str | None:
        """Extract docstring from a function or class definition.

        A docstring is the first expression statement in the body that contains
        a string literal.

        Args:
            node: Function or class definition node
            source_code: Source code text

        Returns:
            Docstring text if found, None otherwise

        """
        try:
            # Get the body node
            body_node = node.child_by_field_name("body")
            if not body_node:
                return None

            # The body is typically a "block" node
            # Look for the first expression_statement containing a string
            for child in body_node.children:
                if child.type == "expression_statement":
                    # Check if it contains a string literal
                    for expr_child in child.children:
                        if expr_child.type == "string":
                            # Extract string content (strip quotes)
                            string_text = source_code[expr_child.start_byte : expr_child.end_byte]
                            # Remove quotes and clean up
                            docstring = self._clean_docstring(string_text)
                            return docstring if docstring else None
                # Stop at first non-docstring statement
                elif child.type not in ("comment", "newline"):
                    break

            return None

        except Exception as e:
            logger.debug(f"Failed to extract docstring: {e}")
            return None

    def _clean_docstring(self, raw_string: str) -> str | None:
        """Clean a raw docstring by removing quotes and normalizing whitespace.

        Args:
            raw_string: Raw string literal from source code

        Returns:
            Cleaned docstring text, or None if empty

        """
        # Remove triple quotes or single quotes
        cleaned = raw_string.strip()

        # Remove triple quotes (""" or ''')
        if cleaned.startswith('"""') or cleaned.startswith("'''"):
            cleaned = cleaned[3:]
        if cleaned.endswith('"""') or cleaned.endswith("'''"):
            cleaned = cleaned[:-3]

        # Remove single quotes (" or ')
        if cleaned.startswith('"') or cleaned.startswith("'"):
            cleaned = cleaned[1:]
        if cleaned.endswith('"') or cleaned.endswith("'"):
            cleaned = cleaned[:-1]

        # Strip whitespace
        cleaned = cleaned.strip()

        return cleaned if cleaned else None

    def _calculate_complexity(self, node: tree_sitter.Node) -> float:
        """Calculate cyclomatic complexity for a code element.

        Counts branch points (if, for, while, try, with, match, boolean operators)
        and normalizes to [0.0, 1.0] range using a sigmoid-like function.

        Args:
            node: Function, class, or method definition node

        Returns:
            Normalized complexity score in range [0.0, 1.0]

        """
        # Node types that represent branch points
        branch_types = {
            "if_statement",
            "for_statement",
            "while_statement",
            "try_statement",
            "with_statement",
            "match_statement",  # Python 3.10+
            "elif_clause",
            "except_clause",
            "boolean_operator",  # and/or operators
            "conditional_expression",  # ternary operator
        }

        branch_count = 0

        def count_branches(n: tree_sitter.Node) -> None:
            nonlocal branch_count
            if n.type in branch_types:
                branch_count += 1
            for child in n.children:
                count_branches(child)

        count_branches(node)

        # Normalize to [0.0, 1.0] range
        # Use a sigmoid-like function: score = branch_count / (branch_count + 10)
        # This ensures:
        # - 0 branches = 0.0
        # - 5 branches = ~0.33
        # - 10 branches = 0.5
        # - 20 branches = ~0.67
        # - 40+ branches = ~0.8+
        if branch_count == 0:
            return 0.0

        complexity_score = branch_count / (branch_count + 10)
        return min(complexity_score, 1.0)  # Ensure it doesn't exceed 1.0

    def _extract_imports(self, root_node: tree_sitter.Node, source_code: str) -> set[str]:
        """Extract all imported names from the module.

        Args:
            root_node: Root node of the syntax tree
            source_code: Source code text

        Returns:
            Set of imported names (modules, functions, classes)

        """
        imports: set[str] = set()

        # Find import_statement and import_from_statement nodes
        for node in self._find_nodes_by_type(root_node, "import_statement"):
            for child in node.children:
                if child.type == "dotted_name":
                    name = source_code[child.start_byte : child.end_byte]
                    imports.add(name.split(".")[0])  # Add base module name

        for node in self._find_nodes_by_type(root_node, "import_from_statement"):
            for child in node.children:
                if child.type == "dotted_name":
                    # Module being imported from
                    name = source_code[child.start_byte : child.end_byte]
                    imports.add(name.split(".")[0])
                elif child.type in {"aliased_import", "dotted_name"}:
                    # Names being imported
                    name = source_code[child.start_byte : child.end_byte]
                    if " as " in name:
                        # Handle "import foo as bar" - extract both names
                        parts = name.split(" as ")
                        imports.add(parts[0].strip())
                    else:
                        imports.add(name.strip())

        return imports

    def _identify_dependencies(
        self,
        _chunk: CodeChunk,
        _imports: set[str],
        _all_chunks: list[CodeChunk],
    ) -> list[str]:
        """Identify dependencies for a code chunk.

        This is a simplified implementation that:
        1. Identifies calls to other functions/methods in the same file
        2. Returns chunk IDs of those dependencies

        A full implementation would require control flow analysis and
        tracking variable assignments.

        Args:
            _chunk: The chunk to analyze (reserved for future implementation)
            _imports: Set of imported names (reserved for future implementation)
            _all_chunks: All chunks extracted from the file (reserved for future implementation)

        Returns:
            List of chunk IDs this chunk depends on

        """
        # For now, return empty list
        # Full implementation would:
        # 1. Parse the function/method body
        # 2. Find all function calls
        # 3. Match calls to chunks in the same file
        # 4. Return chunk IDs of matched dependencies
        #
        # This is complex and would require additional tree-sitter queries
        # and control flow analysis. Deferring to future enhancement.
        return []

    def _generate_chunk_id(self, file_path: Path, element_name: str, line_start: int) -> str:
        """Generate a unique chunk ID based on file path, element name, and location.

        Args:
            file_path: Source file path
            element_name: Name of the code element
            line_start: Starting line number

        Returns:
            Unique chunk identifier

        """
        # Create a deterministic ID based on file path, name, and location
        unique_string = f"{file_path}:{element_name}:{line_start}"
        hash_digest = hashlib.sha256(unique_string.encode()).hexdigest()
        return f"code:{self.language}:{hash_digest[:16]}"

    def _get_fallback_chunks(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Fallback chunking when tree-sitter is unavailable.

        Creates simple text-based chunks by splitting on double newlines
        and grouping into 50-line chunks.

        Args:
            file_path: Source file path
            content: File content as string

        Returns:
            List of CodeChunk instances with basic text chunks

        """
        chunks: list[CodeChunk] = []
        lines = content.split("\n")
        chunk_size = 50

        for i in range(0, len(lines), chunk_size):
            line_start = i + 1
            line_end = min(i + chunk_size, len(lines))

            # Generate chunk ID
            chunk_id = self._generate_chunk_id(file_path, f"chunk_{i}", line_start)

            # Create basic chunk (use 'function' as valid element_type)
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
                language="python",
            )
            chunks.append(chunk)

        return chunks


__all__ = ["PythonParser"]
