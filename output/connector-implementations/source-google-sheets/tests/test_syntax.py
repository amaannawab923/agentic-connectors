"""
Syntax validation tests for Google Sheets connector source files.
"""
import ast
import os
import py_compile
import sys

import pytest


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')


def get_source_files():
    """Get all Python source files in src directory."""
    files = []
    for filename in os.listdir(SRC_DIR):
        if filename.endswith('.py'):
            files.append(os.path.join(SRC_DIR, filename))
    return files


class TestSyntaxValidation:
    """Test Python syntax is valid in all source files."""

    @pytest.mark.parametrize("filepath", get_source_files(), ids=lambda x: os.path.basename(x))
    def test_py_compile(self, filepath):
        """Test that each source file compiles without syntax errors."""
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in {filepath}: {e}")

    @pytest.mark.parametrize("filepath", get_source_files(), ids=lambda x: os.path.basename(x))
    def test_ast_parse(self, filepath):
        """Test that each source file can be parsed as valid Python AST."""
        try:
            with open(filepath, 'r') as f:
                source = f.read()
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"AST parse error in {filepath}: {e}")

    def test_src_init_exists(self):
        """Test that __init__.py exists in src directory."""
        init_path = os.path.join(SRC_DIR, '__init__.py')
        assert os.path.exists(init_path), f"Missing __init__.py in {SRC_DIR}"

    def test_required_files_exist(self):
        """Test that all required source files exist."""
        required_files = [
            '__init__.py',
            'connector.py',
            'config.py',
            'auth.py',
            'client.py',
            'streams.py',
            'utils.py',
        ]
        for filename in required_files:
            filepath = os.path.join(SRC_DIR, filename)
            assert os.path.exists(filepath), f"Missing required file: {filename}"
