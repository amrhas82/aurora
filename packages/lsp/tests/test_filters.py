"""Tests for import filtering."""

import pytest
from aurora_lsp.filters import ImportFilter, get_filter_for_file


class TestImportFilter:
    """Tests for ImportFilter class."""

    def test_python_import_detection(self):
        """Test Python import patterns."""
        f = ImportFilter("python")

        # Should detect as imports
        assert f.is_import_line("import os")
        assert f.is_import_line("import os, sys")
        assert f.is_import_line("from pathlib import Path")
        assert f.is_import_line("from typing import TYPE_CHECKING")
        assert f.is_import_line("  import os  # with indent")
        assert f.is_import_line("from . import module")
        assert f.is_import_line("from ..parent import something")

        # Should NOT detect as imports
        assert not f.is_import_line("x = import_data()")
        assert not f.is_import_line("def import_file():")
        assert not f.is_import_line("# import os")
        assert not f.is_import_line("result = my_import")
        assert not f.is_import_line("class MyClass:")

    def test_typescript_import_detection(self):
        """Test TypeScript import patterns."""
        f = ImportFilter("typescript")

        # Should detect as imports
        assert f.is_import_line("import { foo } from 'bar'")
        assert f.is_import_line("import * as React from 'react'")
        assert f.is_import_line("import type { MyType } from './types'")
        assert f.is_import_line("const fs = require('fs')")

        # Should NOT detect as imports
        assert not f.is_import_line("const x = importData()")
        assert not f.is_import_line("function importFile() {}")

    def test_go_import_detection(self):
        """Test Go import patterns."""
        f = ImportFilter("go")

        assert f.is_import_line('import "fmt"')
        assert f.is_import_line("import (")
        assert f.is_import_line('  "strings"')  # Inside import block

        assert not f.is_import_line("func main() {")

    def test_rust_import_detection(self):
        """Test Rust import patterns."""
        f = ImportFilter("rust")

        assert f.is_import_line("use std::io;")
        assert f.is_import_line("use crate::module::Type;")
        assert f.is_import_line("extern crate serde;")

        assert not f.is_import_line("fn main() {")

    def test_java_import_detection(self):
        """Test Java import patterns."""
        f = ImportFilter("java")

        assert f.is_import_line("import java.util.List;")
        assert f.is_import_line("import static java.lang.Math.PI;")

        assert not f.is_import_line("public class MyClass {")

    def test_get_filter_for_file(self):
        """Test filter selection by file extension."""
        assert get_filter_for_file("main.py").language == "python"
        assert get_filter_for_file("app.ts").language == "typescript"
        assert get_filter_for_file("main.go").language == "go"
        assert get_filter_for_file("lib.rs").language == "rust"
        assert get_filter_for_file("App.java").language == "java"

    @pytest.mark.asyncio
    async def test_filter_references(self):
        """Test filtering references into usages and imports."""
        f = ImportFilter("python")

        refs = [
            {"file": "a.py", "line": 1},  # import line
            {"file": "a.py", "line": 10},  # usage line
            {"file": "b.py", "line": 5},  # import line
        ]

        async def mock_reader(file: str, line: int) -> str:
            lines = {
                ("a.py", 1): "from module import MyClass",
                ("a.py", 10): "obj = MyClass()",
                ("b.py", 5): "import module",
            }
            return lines.get((file, line), "")

        usages, imports = await f.filter_references(refs, mock_reader)

        assert len(usages) == 1
        assert len(imports) == 2
        assert usages[0]["line"] == 10
        assert imports[0]["line"] == 1
