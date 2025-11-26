"""Syntax validation tests for Google Sheets connector source files."""

import ast
import os
import sys
import pytest

# Path to source files
SRC_DIR = os.path.join(os.path.dirname(__file__), '..', 'src')


class TestSyntaxValidation:
    """Test that all Python source files have valid syntax."""

    def get_source_files(self):
        """Get all Python files in the src directory."""
        py_files = []
        for filename in os.listdir(SRC_DIR):
            if filename.endswith('.py'):
                py_files.append(os.path.join(SRC_DIR, filename))
        return py_files

    def test_connector_syntax(self):
        """Test connector.py has valid syntax."""
        filepath = os.path.join(SRC_DIR, 'connector.py')
        with open(filepath, 'r') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in connector.py: {e}")

    def test_config_syntax(self):
        """Test config.py has valid syntax."""
        filepath = os.path.join(SRC_DIR, 'config.py')
        with open(filepath, 'r') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in config.py: {e}")

    def test_auth_syntax(self):
        """Test auth.py has valid syntax."""
        filepath = os.path.join(SRC_DIR, 'auth.py')
        with open(filepath, 'r') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in auth.py: {e}")

    def test_client_syntax(self):
        """Test client.py has valid syntax."""
        filepath = os.path.join(SRC_DIR, 'client.py')
        with open(filepath, 'r') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in client.py: {e}")

    def test_streams_syntax(self):
        """Test streams.py has valid syntax."""
        filepath = os.path.join(SRC_DIR, 'streams.py')
        with open(filepath, 'r') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in streams.py: {e}")

    def test_utils_syntax(self):
        """Test utils.py has valid syntax."""
        filepath = os.path.join(SRC_DIR, 'utils.py')
        with open(filepath, 'r') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in utils.py: {e}")

    def test_init_syntax(self):
        """Test __init__.py has valid syntax."""
        filepath = os.path.join(SRC_DIR, '__init__.py')
        with open(filepath, 'r') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in __init__.py: {e}")

    def test_all_files_have_valid_syntax(self):
        """Test all Python files in src directory have valid syntax."""
        errors = []
        for filepath in self.get_source_files():
            filename = os.path.basename(filepath)
            try:
                with open(filepath, 'r') as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                errors.append(f"{filename}: {e}")

        if errors:
            pytest.fail(f"Syntax errors found:\n" + "\n".join(errors))
