"""
Syntax validation tests for the Notion connector.

These tests verify that all source files have valid Python syntax.
"""

import py_compile
import os
import pytest


class TestSyntaxValidation:
    """Test class for syntax validation."""

    SRC_DIR = os.path.join(os.path.dirname(__file__), '..', 'src')

    def test_connector_syntax(self):
        """Test connector.py has valid syntax."""
        filepath = os.path.join(self.SRC_DIR, 'connector.py')
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in connector.py: {e}")

    def test_config_syntax(self):
        """Test config.py has valid syntax."""
        filepath = os.path.join(self.SRC_DIR, 'config.py')
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in config.py: {e}")

    def test_auth_syntax(self):
        """Test auth.py has valid syntax."""
        filepath = os.path.join(self.SRC_DIR, 'auth.py')
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in auth.py: {e}")

    def test_client_syntax(self):
        """Test client.py has valid syntax."""
        filepath = os.path.join(self.SRC_DIR, 'client.py')
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in client.py: {e}")

    def test_streams_syntax(self):
        """Test streams.py has valid syntax."""
        filepath = os.path.join(self.SRC_DIR, 'streams.py')
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in streams.py: {e}")

    def test_utils_syntax(self):
        """Test utils.py has valid syntax."""
        filepath = os.path.join(self.SRC_DIR, 'utils.py')
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in utils.py: {e}")

    def test_init_syntax(self):
        """Test __init__.py has valid syntax."""
        filepath = os.path.join(self.SRC_DIR, '__init__.py')
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in __init__.py: {e}")
