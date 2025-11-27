"""
Syntax validation tests for Google Sheets connector.

These tests verify that all Python files have valid syntax.
"""

import py_compile
import pytest
from pathlib import Path


SRC_DIR = Path(__file__).parent.parent / 'src'


class TestSyntaxValidation:
    """Test syntax validation for all source files."""

    @pytest.mark.parametrize("module_name", [
        "__init__",
        "connector",
        "config",
        "auth",
        "client",
        "streams",
        "utils",
    ])
    def test_source_file_syntax(self, module_name):
        """Test that source file has valid Python syntax."""
        file_path = SRC_DIR / f"{module_name}.py"
        assert file_path.exists(), f"File {file_path} does not exist"

        # py_compile.compile raises SyntaxError if invalid
        try:
            py_compile.compile(str(file_path), doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in {module_name}.py: {e}")

    def test_all_python_files_valid(self):
        """Test all Python files in src directory have valid syntax."""
        errors = []
        for py_file in SRC_DIR.glob("*.py"):
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"{py_file.name}: {e}")

        if errors:
            pytest.fail(f"Syntax errors found:\n" + "\n".join(errors))
