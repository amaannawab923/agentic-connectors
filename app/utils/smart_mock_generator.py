"""Smart Mock Generator - Auto-generates test mocks from connector source code.

This module analyzes the generated connector's source code to automatically
create accurate mock fixtures, eliminating the need for trial-and-error mocking.

Key Features:
- Parses client.py to extract method signatures and return types
- Extracts example data from docstrings and type hints
- Auto-generates mock fixtures with correct data structures
- Supports multiple mocking strategies (library utils, MagicMock, VCR.py)
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ClientMethodInfo:
    """Information about a client class method."""

    def __init__(
        self,
        name: str,
        args: List[str],
        return_type: Optional[str] = None,
        docstring: Optional[str] = None,
    ):
        self.name = name
        self.args = args
        self.return_type = return_type
        self.docstring = docstring
        self.example_return = None

    def extract_example_from_docstring(self) -> Optional[Dict[str, Any]]:
        """Extract example return value from docstring."""
        if not self.docstring:
            return None

        # Look for JSON/dict examples in docstring
        # Pattern: {"key": "value", ...} or Example: {...}
        json_pattern = r'\{[^}]+\}'
        matches = re.findall(json_pattern, self.docstring, re.DOTALL)

        for match in matches:
            try:
                # Try to parse as JSON
                example = json.loads(match.replace("'", '"'))
                return example
            except json.JSONDecodeError:
                # Try to evaluate as Python dict
                try:
                    example = ast.literal_eval(match)
                    if isinstance(example, dict):
                        return example
                except (ValueError, SyntaxError):
                    continue

        return None

    def infer_mock_return_value(self) -> Any:
        """Infer a sensible mock return value based on method name and type."""
        # Try to get from docstring first
        example = self.extract_example_from_docstring()
        if example:
            return example

        # Infer from method name patterns
        method_lower = self.name.lower()

        if 'check' in method_lower or 'test' in method_lower:
            # Check methods should return boolean or status dict
            if self.return_type and 'bool' in self.return_type.lower():
                return True
            return {"success": True, "message": "Connected"}

        if 'get' in method_lower:
            if 'names' in method_lower or ('name' in method_lower and 'list' in self.return_type.lower() if self.return_type else False):
                return ["Sheet1", "Sheet2", "Sheet3"]
            elif 'metadata' in method_lower or 'info' in method_lower:
                return {
                    "id": "test-123",
                    "name": "Test Resource",
                    "properties": {"title": "Test"}
                }
            elif 'list' in method_lower or 'data' in method_lower or 'rows' in method_lower or 'values' in method_lower:
                return [
                    ["Header1", "Header2", "Header3"],
                    ["value1", "value2", "value3"],
                    ["value4", "value5", "value6"]
                ]
            else:
                return {"result": "test_data"}

        if 'list' in method_lower:
            return [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}]

        if 'create' in method_lower or 'insert' in method_lower:
            return {"id": "new-123", "status": "created"}

        if 'update' in method_lower:
            return {"id": "test-123", "status": "updated"}

        if 'delete' in method_lower:
            return {"status": "deleted"}

        # Default fallback
        if self.return_type:
            if 'bool' in self.return_type.lower():
                return True
            elif 'list' in self.return_type.lower():
                return []
            elif 'dict' in self.return_type.lower():
                return {}
            elif 'str' in self.return_type.lower():
                return "test_value"
            elif 'int' in self.return_type.lower():
                return 123

        return {"status": "success", "data": "test"}


class ClientAnalyzer:
    """Analyzes client.py to extract class and method information."""

    def __init__(self, client_file_path: Path):
        self.client_file = client_file_path
        self.source_code = client_file_path.read_text()
        self.tree = ast.parse(self.source_code)

    def analyze(self) -> Dict[str, Any]:
        """Analyze the client file and extract all relevant information."""
        client_info = {
            'class_name': None,
            'methods': [],
            'imports': self._extract_imports(),
            'api_library': self._detect_api_library()
        }

        # Find the main Client class (prioritize non-Error classes)
        client_classes = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                if 'Client' in node.name:
                    # Prioritize classes that don't end with Error/Exception
                    priority = 0 if not node.name.endswith(('Error', 'Exception')) else 1
                    client_classes.append((priority, node))

        # Sort by priority and take the first one
        if client_classes:
            client_classes.sort(key=lambda x: x[0])
            _, client_node = client_classes[0]
            client_info['class_name'] = client_node.name
            client_info['methods'] = self._extract_methods(client_node)

        return client_info

    def _extract_imports(self) -> List[str]:
        """Extract all import statements."""
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def _detect_api_library(self) -> Optional[str]:
        """Detect which API library is being used."""
        imports = self._extract_imports()

        if any('googleapiclient' in imp or 'google.oauth2' in imp for imp in imports):
            return 'googleapiclient'
        elif any('boto3' in imp or 'botocore' in imp for imp in imports):
            return 'boto3'
        elif 'stripe' in imports:
            return 'stripe'
        elif any('requests' in imp for imp in imports):
            return 'requests'
        elif any('httpx' in imp for imp in imports):
            return 'httpx'

        return 'unknown'

    def _extract_methods(self, class_node: ast.ClassDef) -> List[ClientMethodInfo]:
        """Extract all methods from the client class."""
        methods = []

        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                # Skip private methods and __init__
                if item.name.startswith('_'):
                    continue

                # Extract method information
                args = [arg.arg for arg in item.args.args if arg.arg != 'self']

                return_type = None
                if item.returns:
                    return_type = ast.unparse(item.returns)

                docstring = ast.get_docstring(item)

                method_info = ClientMethodInfo(
                    name=item.name,
                    args=args,
                    return_type=return_type,
                    docstring=docstring
                )

                methods.append(method_info)

        return methods


class MockCodeGenerator:
    """Generates mock fixture code from client analysis."""

    def __init__(self, client_info: Dict[str, Any]):
        self.client_info = client_info
        self.class_name = client_info['class_name']
        self.methods = client_info['methods']
        self.api_library = client_info['api_library']

    def generate_conftest(self) -> str:
        """Generate complete conftest.py with mock fixtures."""
        code = self._generate_header()
        code += self._generate_primary_mock_fixture()
        code += self._generate_library_specific_fixtures()
        return code

    def _generate_header(self) -> str:
        """Generate import statements and header."""
        return f'''"""Auto-generated test fixtures for {self.class_name}.

Generated by SmartMockGenerator - mocks based on actual client code analysis.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import json
from pathlib import Path

'''

    def _generate_primary_mock_fixture(self) -> str:
        """Generate the main mock fixture for the client class."""
        code = f'''
@pytest.fixture
def mock_{self.class_name.lower()}():
    """Auto-generated mock for {self.class_name}.

    This mock is generated by analyzing the actual client code.
    Mock return values are inferred from method names, docstrings, and type hints.
    """
    with patch('src.client.{self.class_name}') as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

'''

        # Generate mock return values for each method
        for method in self.methods:
            mock_value = method.infer_mock_return_value()

            # Format the mock value nicely
            if isinstance(mock_value, (dict, list)):
                mock_value_str = json.dumps(mock_value, indent=12)
            else:
                mock_value_str = repr(mock_value)

            code += f'''        # {method.name}: {method.return_type or "inferred"}
        mock_instance.{method.name}.return_value = {mock_value_str}

'''

        code += '''        yield mock_instance


'''
        return code

    def _generate_library_specific_fixtures(self) -> str:
        """Generate library-specific mock fixtures if applicable."""
        code = ""

        if self.api_library == 'googleapiclient':
            code += self._generate_google_api_fixtures()
        elif self.api_library == 'boto3':
            code += self._generate_boto3_fixtures()
        elif self.api_library in ['requests', 'httpx']:
            code += self._generate_http_fixtures()

        return code

    def _generate_google_api_fixtures(self) -> str:
        """Generate Google API specific fixtures using HttpMock."""
        return '''
@pytest.fixture
def mock_google_api_with_httpmock():
    """Mock Google API using googleapiclient.http.HttpMock.

    This uses Google's official testing utilities for more accurate mocking.
    Uncomment and customize if you prefer HttpMock over MagicMock.
    """
    # from googleapiclient.http import HttpMockSequence
    #
    # http = HttpMockSequence([
    #     ({'status': '200'}, open('fixtures/response1.json').read()),
    #     ({'status': '200'}, open('fixtures/response2.json').read()),
    # ])
    #
    # yield http
    pass


'''

    def _generate_boto3_fixtures(self) -> str:
        """Generate boto3 specific fixtures using moto."""
        return '''
@pytest.fixture
def mock_aws_with_moto():
    """Mock AWS services using moto library.

    Install: pip install moto
    """
    # from moto import mock_s3, mock_dynamodb, etc.
    #
    # with mock_s3():
    #     yield
    pass


'''

    def _generate_http_fixtures(self) -> str:
        """Generate HTTP mocking fixtures using responses library."""
        return '''
@pytest.fixture
def mock_http_with_responses():
    """Mock HTTP requests using responses library.

    Install: pip install responses
    """
    # import responses
    #
    # @responses.activate
    # def test_with_responses():
    #     responses.add(
    #         responses.GET,
    #         'https://api.example.com/endpoint',
    #         json={'key': 'value'},
    #         status=200
    #     )
    #     yield
    pass


'''


class SmartMockGenerator:
    """Main interface for smart mock generation."""

    def __init__(self, connector_dir: Path):
        """Initialize with connector directory path."""
        self.connector_dir = Path(connector_dir)
        self.src_dir = self.connector_dir / "src"
        self.tests_dir = self.connector_dir / "tests"
        self.client_file = self.src_dir / "client.py"

    def generate(self) -> Tuple[bool, str]:
        """Generate smart mocks for the connector.

        Returns:
            Tuple[bool, str]: (success, conftest_code or error_message)
        """
        try:
            # Validate paths
            if not self.client_file.exists():
                return False, f"Client file not found: {self.client_file}"

            # Analyze the client
            logger.info(f"Analyzing client file: {self.client_file}")
            analyzer = ClientAnalyzer(self.client_file)
            client_info = analyzer.analyze()

            if not client_info['class_name']:
                return False, "No Client class found in client.py"

            logger.info(f"Found client class: {client_info['class_name']}")
            logger.info(f"Detected API library: {client_info['api_library']}")
            logger.info(f"Found {len(client_info['methods'])} public methods")

            # Generate mock code
            generator = MockCodeGenerator(client_info)
            conftest_code = generator.generate_conftest()

            return True, conftest_code

        except Exception as e:
            logger.error(f"Error generating mocks: {e}", exc_info=True)
            return False, f"Error: {str(e)}"

    def save_to_file(self, conftest_code: str, output_file: Optional[Path] = None) -> Path:
        """Save generated conftest to file.

        Args:
            conftest_code: Generated conftest.py content
            output_file: Optional output path (defaults to tests/conftest_generated.py)

        Returns:
            Path: Path to saved file
        """
        if output_file is None:
            output_file = self.tests_dir / "conftest_generated.py"

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(conftest_code)

        logger.info(f"Saved generated conftest to: {output_file}")
        return output_file


# Convenience function for easy use
def generate_smart_mocks(connector_dir: str) -> Tuple[bool, str]:
    """Generate smart mocks for a connector directory.

    Args:
        connector_dir: Path to connector directory

    Returns:
        Tuple[bool, str]: (success, conftest_code or error_message)

    Example:
        >>> success, code = generate_smart_mocks("./output/source-google-sheets")
        >>> if success:
        >>>     print(code)
    """
    generator = SmartMockGenerator(connector_dir)
    return generator.generate()
