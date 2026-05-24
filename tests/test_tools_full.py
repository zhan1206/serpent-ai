"""
Comprehensive tests for SerpentAI tools module.
Tests all public methods and classes with mocking for external dependencies.
Target: 80%+ coverage
"""

import sys
import os
import json
import math
import datetime
import hashlib
import tempfile
import platform
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import pytest
import asyncio

# Mock resource module for Windows compatibility
# The resource module is Unix-only but tool_sandbox.py imports it at top level
if platform.system() == "Windows":
    sys.modules['resource'] = Mock()

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from tools import (
    MCPClient, MCPError,
    ToolRegistry, get_global_registry,
    ToolPrecompiler, get_global_precompiler,
    ToolDistiller, get_global_distiller
)
from tools.tool_executor import ToolExecutor, ToolExecutionError
from tools.tool_sandbox import ToolSandbox, DockerSandbox, create_sandbox
# SandboxError is not defined in tool_sandbox.py, creating mock
class SandboxError(Exception):
    pass
try:
    from tools.tool_sandbox import ToolSandbox
except Exception:
    pass
from tools.builtin_tools import (
    get_current_time, calculate, hash_text,
    generate_password, json_format,
    register_all_builtin_tools
)
from tools.system_tools import (
    fs_list_directory, fs_read_file, fs_write_file,
    fs_delete, fs_copy, fs_move, fs_mkdir, fs_exists,
    shell_execute, process_list, process_kill,
    system_info, system_disk_usage, register_system_tools
)
# SandboxError is defined locally above (not exported by tool_sandbox.py on Windows)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def reset_global_registry():
    """Reset global registry before each test."""
    from tools.tool_registry import _global_registry
    globals()['_global_registry_backup'] = None
    yield
    import tools.tool_registry as tr
    tr._global_registry = None


@pytest.fixture
def reset_global_precompiler():
    """Reset global precompiler before each test."""
    import tools.tool_precompiler as tp
    tp._global_precompiler = None
    yield
    tp._global_precompiler = None


@pytest.fixture
def reset_global_distiller():
    """Reset global distiller before each test."""
    import tools.tool_distiller as td
    td._global_distiller = None
    yield
    td._global_distiller = None


@pytest.fixture
def clean_registry():
    """Provide a clean ToolRegistry instance."""
    registry = ToolRegistry()
    yield registry


@pytest.fixture
def sample_tools():
    """Provide sample tool definitions."""
    return [
        {
            "name": "test_tool_1",
            "description": "A test tool for testing",
            "category": "test",
            "handler": lambda args: "result1",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "required": ["param1"]
            }
        },
        {
            "name": "test_tool_2",
            "description": "Another test tool with very long description that should be distilled properly",
            "category": "test",
            "handler": lambda args: "result2",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    ]


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = Mock(spec=MCPClient)
    client.transport = "stdio"
    client.command = "npx test-server"
    client.timeout = 30
    client.list_tools.return_value = {
        "tools": [
            {"name": "mcp_tool_1", "description": "MCP tool 1", "inputSchema": {}},
            {"name": "mcp_tool_2", "description": "MCP tool 2", "inputSchema": {}}
        ]
    }
    client.call_tool.return_value = {"result": "success"}
    return client


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file system tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# Tests for __init__.py
# ============================================================================

class TestInit:
    """Test module initialization and exports."""

    def test_imports(self):
        """Test that all expected symbols are exported."""
        from tools import (
            MCPClient, MCPError,
            ToolRegistry, get_global_registry,
            ToolPrecompiler, get_global_precompiler,
            ToolDistiller, get_global_distiller
        )
        assert MCPClient is not None
        assert MCPError is not None
        assert ToolRegistry is not None
        assert get_global_registry is not None
        assert ToolPrecompiler is not None
        assert get_global_precompiler is not None
        assert ToolDistiller is not None
        assert get_global_distiller is not None


# ============================================================================
# Tests for builtin_tools.py
# ============================================================================

class TestBuiltinTools:
    """Test builtin tool functions."""

    def test_get_current_time(self):
        """Test get_current_time function."""
        result = get_current_time({})
        assert "timestamp" in result
        assert "iso_format" in result
        assert "date" in result
        assert "time" in result
        assert "timezone" in result
        assert result["timezone"] == "local"

    def test_calculate_basic(self):
        """Test basic calculations."""
        result = calculate({"expression": "2 + 2"})
        assert result["result"] == 4

    def test_calculate_math_functions(self):
        """Test calculations with math functions."""
        result = calculate({"expression": "sqrt(16)"})
        assert result["result"] == 4.0

        result = calculate({"expression": "sin(0)"})
        assert result["result"] == 0.0

        result = calculate({"expression": "log(100, 10)"})
        assert result["result"] == 2.0

    def test_calculate_math_constants(self):
        """Test calculations with math constants."""
        result = calculate({"expression": "pi"})
        assert result["result"] == math.pi

        result = calculate({"expression": "e"})
        assert result["result"] == math.e

    def test_calculate_nested_expression(self):
        """Test nested mathematical expressions."""
        result = calculate({"expression": "(2 + 3) * 4"})
        assert result["result"] == 20

    def test_calculate_dangerous_keyword_rejected(self):
        """Test that dangerous keywords are rejected."""
        with pytest.raises(ValueError, match="Dangerous keyword not allowed"):
            calculate({"expression": "__import__('os')"})

        with pytest.raises(ValueError, match="Dangerous keyword not allowed"):
            calculate({"expression": "eval('2+2')"})

        with pytest.raises(ValueError, match="Dangerous keyword not allowed"):
            calculate({"expression": "exec('x=1')"})

    def test_calculate_invalid_expression(self):
        """Test invalid expression handling."""
        with pytest.raises(ValueError, match="Calculation error"):
            calculate({"expression": "invalid_syntax ++"})

    def test_hash_text_md5(self):
        """Test MD5 hashing."""
        result = hash_text({"text": "hello", "algorithm": "md5"})
        assert result["algorithm"] == "md5"
        assert result["hash"] == hashlib.md5(b"hello").hexdigest()

    def test_hash_text_sha256(self):
        """Test SHA256 hashing."""
        result = hash_text({"text": "hello", "algorithm": "sha256"})
        assert result["algorithm"] == "sha256"
        assert result["hash"] == hashlib.sha256(b"hello").hexdigest()

    def test_hash_text_sha1(self):
        """Test SHA1 hashing."""
        result = hash_text({"text": "hello", "algorithm": "sha1"})
        assert result["algorithm"] == "sha1"
        assert result["hash"] == hashlib.sha1(b"hello").hexdigest()

    def test_hash_text_sha512(self):
        """Test SHA512 hashing."""
        result = hash_text({"text": "hello", "algorithm": "sha512"})
        assert result["algorithm"] == "sha512"
        assert result["hash"] == hashlib.sha512(b"hello").hexdigest()

    def test_hash_text_unsupported_algorithm(self):
        """Test unsupported algorithm error."""
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            hash_text({"text": "hello", "algorithm": "md2"})

    def test_generate_password_default(self):
        """Test password generation with defaults."""
        result = generate_password({"length": 16})
        assert len(result["password"]) == 16
        assert result["length"] == 16
        assert result["includes_symbols"] is True
        assert result["includes_numbers"] is True

    def test_generate_password_no_symbols(self):
        """Test password generation without symbols."""
        result = generate_password({"length": 12, "include_symbols": False})
        assert len(result["password"]) == 12
        assert result["includes_symbols"] is False
        # Check no symbols in password
        import string
        has_symbol = any(c in string.punctuation for c in result["password"])
        assert has_symbol is False

    def test_generate_password_no_numbers(self):
        """Test password generation without numbers."""
        result = generate_password({"length": 12, "include_numbers": False})
        assert result["includes_numbers"] is False
        import string
        has_number = any(c in string.digits for c in result["password"])
        assert has_number is False

    def test_generate_password_min_length(self):
        """Test password generation with minimum length."""
        result = generate_password({"length": 8})
        assert len(result["password"]) == 8

    def test_generate_password_max_length(self):
        """Test password generation with maximum length."""
        result = generate_password({"length": 128})
        assert len(result["password"]) == 128

    def test_json_format_valid(self):
        """Test JSON formatting with valid JSON."""
        json_str = '{"name": "test", "value": 123}'
        result = json_format({"json_str": json_str})
        assert result["valid"] is True
        assert '"name"' in result["formatted"]
        assert '"test"' in result["formatted"]

    def test_json_format_with_indent(self):
        """Test JSON formatting with custom indent."""
        json_str = '{"name": "test"}'
        result = json_format({"json_str": json_str, "indent": 4})
        assert result["valid"] is True
        assert "    " in result["formatted"]  # 4 spaces

    def test_json_format_invalid(self):
        """Test JSON formatting with invalid JSON."""
        result = json_format({"json_str": "invalid json"})
        assert result["valid"] is False
        assert "error" in result

    def test_register_all_builtin_tools(self, reset_global_registry):
        """Test registering all builtin tools."""
        register_all_builtin_tools()
        registry = get_global_registry()
        tools = registry.list_tools()
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "get_current_time" in tool_names
        assert "calculate" in tool_names


# ============================================================================
# Tests for mcp_client.py
# ============================================================================

class TestMCPError:
    """Test MCPError exception."""

    def test_init(self):
        """Test MCPError initialization."""
        error = MCPError(100, "Test error", {"detail": "info"})
        assert error.code == 100
        assert error.message == "Test error"
        assert error.data == {"detail": "info"}
        assert "MCP Error 100: Test error" in str(error)


class TestMCPClient:
    """Test MCPClient class."""

    @patch('subprocess.Popen')
    def test_stdio_connect(self, mock_popen):
        """Test connecting via stdio transport."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"capabilities": {}}
        })
        mock_popen.return_value = mock_process

        client = MCPClient(transport="stdio", command="npx test-server")
        result = client.connect()

        assert result == {"capabilities": {}}
        mock_popen.assert_called_once()

    @patch('requests.post')
    def test_http_connect(self, mock_post):
        """Test connecting via HTTP transport."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"capabilities": {}}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = MCPClient(transport="http", url="http://localhost:8080/mcp")
        result = client.connect()

        assert result == {"capabilities": {}}
        mock_post.assert_called_once()

    @patch('subprocess.Popen')
    def test_stdio_list_tools(self, mock_popen):
        """Test listing tools via stdio."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": [{"name": "tool1", "description": "Tool 1"}]}
        })
        mock_popen.return_value = mock_process

        client = MCPClient(transport="stdio", command="npx test-server")
        client.process = mock_process  # Skip connect
        result = client.list_tools()

        assert len(result) == 1
        assert result[0]["name"] == "tool1"

    @patch('subprocess.Popen')
    def test_stdio_list_tools_cached(self, mock_popen):
        """Test that list_tools caches results."""
        client = MCPClient(transport="stdio", command="npx test-server")
        client._tools_cache = [{"name": "cached_tool"}]

        result = client.list_tools()
        assert len(result) == 1
        assert result[0]["name"] == "cached_tool"

    @patch('subprocess.Popen')
    def test_stdio_list_tools_force_refresh(self, mock_popen):
        """Test force refresh of tools list."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": [{"name": "new_tool"}]}
        })
        mock_popen.return_value = mock_process

        client = MCPClient(transport="stdio", command="npx test-server")
        client.process = mock_process
        client._tools_cache = [{"name": "cached_tool"}]

        result = client.list_tools(force_refresh=True)
        assert len(result) == 1
        assert result[0]["name"] == "new_tool"

    @patch('subprocess.Popen')
    def test_stdio_call_tool(self, mock_popen):
        """Test calling tool via stdio."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"text": "tool result"}]}
        })
        mock_popen.return_value = mock_process

        client = MCPClient(transport="stdio", command="npx test-server")
        client.process = mock_process
        result = client.call_tool("test_tool", {"arg": "value"})

        assert result == {"content": [{"text": "tool result"}]}

    def test_call_tool_no_process(self):
        """Test calling tool without connected process."""
        client = MCPClient(transport="stdio", command=None)
        with pytest.raises(MCPError, match="No command provided"):
            client.call_tool("test_tool", {})

    def test_http_no_url(self):
        """Test HTTP transport without URL."""
        client = MCPClient(transport="http", url=None)
        with pytest.raises(MCPError, match="No URL provided"):
            client.connect()

    @patch('subprocess.Popen')
    def test_close(self, mock_popen):
        """Test closing MCP client."""
        mock_process = Mock()
        mock_popen.return_value = mock_process

        client = MCPClient(transport="stdio", command="npx test-server")
        client.process = mock_process
        client._tools_cache = [{"name": "tool1"}]
        client.close()

        mock_process.terminate.assert_called_once()
        assert client.process is None
        assert client._tools_cache is None

    def test_context_manager(self):
        """Test MCPClient as context manager."""
        client = MCPClient(transport="http", url="http://test")
        with patch.object(client, 'connect') as mock_connect:
            with patch.object(client, 'close') as mock_close:
                with client as c:
                    assert c is client
                    mock_connect.assert_called_once()
                mock_close.assert_called_once()

    def test_next_id(self):
        """Test request ID generation."""
        client = MCPClient()
        assert client._next_id() == 1
        assert client._next_id() == 2
        assert client._next_id() == 3

    def test_unsupported_transport(self):
        """Test unsupported transport error."""
        client = MCPClient(transport="invalid")
        with pytest.raises(MCPError, match="Unsupported transport"):
            client.connect()

    @patch('subprocess.Popen')
    def test_response_id_mismatch(self, mock_popen):
        """Test handling of response ID mismatch."""
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stdout.readline.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 999,  # Wrong ID
            "result": {}
        })
        mock_popen.return_value = mock_process

        client = MCPClient(transport="stdio", command="npx test")
        client.process = mock_process
        with pytest.raises(MCPError, match="Response ID mismatch"):
            client._send_stdio_request("test_method")


class TestMCPClientHelpers:
    """Test MCPClient helper functions."""

    def test_create_stdio_client(self):
        """Test create_stdio_client helper."""
        client = create_stdio_client("npx test-server", timeout=60)
        assert client.transport == "stdio"
        assert client.command == "npx test-server"
        assert client.timeout == 60

    def test_create_http_client(self):
        """Test create_http_client helper."""
        client = create_http_client("http://localhost:8080", timeout=60)
        assert client.transport == "http"
        assert client.url == "http://localhost:8080"
        assert client.timeout == 60


# ============================================================================
# Tests for system_tools.py
# ============================================================================

class TestSystemTools:
    """Test system tool functions."""

    def test_fs_list_directory_current(self, temp_dir):
        """Test listing current directory."""
        # Create test files
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test")
        test_dir = Path(temp_dir) / "subdir"
        test_dir.mkdir()

        result = fs_list_directory({"path": temp_dir})
        assert result["success"] is True
        assert result["count"] >= 2
        names = [item["name"] for item in result["items"]]
        assert "test.txt" in names
        assert "subdir" in names

    def test_fs_list_directory_nonexistent(self):
        """Test listing nonexistent directory."""
        result = fs_list_directory({"path": "/nonexistent/path"})
        assert result["success"] is False
        assert "does not exist" in result["error"]

    def test_fs_list_directory_not_directory(self, temp_dir):
        """Test listing a file as directory."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test")

        result = fs_list_directory({"path": str(test_file)})
        assert result["success"] is False
        assert "Not a directory" in result["error"]

    def test_fs_list_directory_hidden(self, temp_dir):
        """Test listing with hidden files."""
        hidden_file = Path(temp_dir) / ".hidden"
        hidden_file.write_text("hidden")

        result = fs_list_directory({"path": temp_dir, "show_hidden": False})
        names = [item["name"] for item in result["items"]]
        assert ".hidden" not in names

        result = fs_list_directory({"path": temp_dir, "show_hidden": True})
        names = [item["name"] for item in result["items"]]
        assert ".hidden" in names

    def test_fs_read_file(self, temp_dir):
        """Test reading a file."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Hello, World!")

        result = fs_read_file({"path": str(test_file)})
        assert result["success"] is True
        assert result["content"] == "Hello, World!"

    def test_fs_read_file_nonexistent(self):
        """Test reading nonexistent file."""
        result = fs_read_file({"path": "/nonexistent/file.txt"})
        assert result["success"] is False
        assert "does not exist" in result["error"]

    def test_fs_read_file_limited_lines(self, temp_dir):
        """Test reading file with line limit."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")

        result = fs_read_file({"path": str(test_file), "lines": 3})
        assert result["success"] is True
        assert result["content"].count("\n") == 2  # 3 lines = 2 newlines

    def test_fs_read_file_too_large(self, temp_dir):
        """Test reading file that is too large."""
        test_file = Path(temp_dir) / "large.txt"
        test_file.write_text("x" * (11 * 1024 * 1024))  # 11MB

        result = fs_read_file({"path": str(test_file)})
        assert result["success"] is False
        assert "too large" in result["error"]

    def test_fs_write_file(self, temp_dir):
        """Test writing to a file."""
        test_file = Path(temp_dir) / "output.txt"

        result = fs_write_file({"path": str(test_file), "content": "Hello!"})
        assert result["success"] is True
        assert test_file.read_text() == "Hello!"

    def test_fs_write_file_append(self, temp_dir):
        """Test appending to a file."""
        test_file = Path(temp_dir) / "append.txt"
        test_file.write_text("First line\n")

        result = fs_write_file({
            "path": str(test_file),
            "content": "Second line",
            "mode": "append"
        })
        assert result["success"] is True
        assert "First line" in test_file.read_text()
        assert "Second line" in test_file.read_text()

    def test_fs_write_file_create_dirs(self, temp_dir):
        """Test writing file creates parent directories."""
        nested_file = Path(temp_dir) / "a" / "b" / "test.txt"

        result = fs_write_file({"path": str(nested_file), "content": "nested"})
        assert result["success"] is True
        assert nested_file.read_text() == "nested"

    def test_fs_delete_file(self, temp_dir):
        """Test deleting a file."""
        test_file = Path(temp_dir) / "to_delete.txt"
        test_file.write_text("delete me")

        result = fs_delete({"path": str(test_file)})
        assert result["success"] is True
        assert not test_file.exists()

    def test_fs_delete_directory_empty(self, temp_dir):
        """Test deleting an empty directory."""
        test_dir = Path(temp_dir) / "empty_dir"
        test_dir.mkdir()

        result = fs_delete({"path": str(test_dir)})
        assert result["success"] is True
        assert not test_dir.exists()

    def test_fs_delete_directory_not_empty(self, temp_dir):
        """Test deleting non-empty directory without force."""
        test_dir = Path(temp_dir) / "nonempty_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test")

        result = fs_delete({"path": str(test_dir), "force": False})
        assert result["success"] is False
        assert "not empty" in result["error"]

    def test_fs_delete_directory_force(self, temp_dir):
        """Test force deleting non-empty directory."""
        test_dir = Path(temp_dir) / "nonempty_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test")

        result = fs_delete({"path": str(test_dir), "force": True})
        assert result["success"] is True
        assert not test_dir.exists()

    def test_fs_copy_file(self, temp_dir):
        """Test copying a file."""
        src_file = Path(temp_dir) / "source.txt"
        src_file.write_text("copy me")
        dst_file = Path(temp_dir) / "dest.txt"

        result = fs_copy({"source": str(src_file), "destination": str(dst_file)})
        assert result["success"] is True
        assert dst_file.read_text() == "copy me"

    def test_fs_copy_directory(self, temp_dir):
        """Test copying a directory."""
        src_dir = Path(temp_dir) / "src_dir"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("test")
        dst_dir = Path(temp_dir) / "dst_dir"

        result = fs_copy({"source": str(src_dir), "destination": str(dst_dir)})
        assert result["success"] is True
        assert (dst_dir / "file.txt").read_text() == "test"

    def test_fs_move(self, temp_dir):
        """Test moving/renaming a file."""
        src_file = Path(temp_dir) / "old.txt"
        src_file.write_text("move me")
        dst_file = Path(temp_dir) / "new.txt"

        result = fs_move({"source": str(src_file), "destination": str(dst_file)})
        assert result["success"] is True
        assert not src_file.exists()
        assert dst_file.read_text() == "move me"

    def test_fs_mkdir(self, temp_dir):
        """Test creating a directory."""
        new_dir = Path(temp_dir) / "new_directory"

        result = fs_mkdir({"path": str(new_dir)})
        assert result["success"] is True
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_fs_mkdir_nested(self, temp_dir):
        """Test creating nested directories."""
        nested_dir = Path(temp_dir) / "a" / "b" / "c"

        result = fs_mkdir({"path": str(nested_dir)})
        assert result["success"] is True
        assert nested_dir.exists()

    def test_fs_exists(self, temp_dir):
        """Test checking if path exists."""
        test_file = Path(temp_dir) / "exists.txt"
        test_file.write_text("test")

        result = fs_exists({"path": str(test_file)})
        assert result["success"] is True
        assert result["exists"] is True
        assert result["is_file"] is True
        assert result["is_dir"] is False

    def test_fs_exists_not_exists(self):
        """Test checking nonexistent path."""
        result = fs_exists({"path": "/nonexistent"})
        assert result["success"] is True
        assert result["exists"] is False

    @patch('subprocess.run')
    def test_shell_execute_success(self, mock_run):
        """Test successful shell command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="command output",
            stderr=""
        )

        result = shell_execute({"command": "echo test"})
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert result["stdout"] == "command output"

    @patch('subprocess.run')
    def test_shell_execute_failure(self, mock_run):
        """Test failed shell command execution."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="error message"
        )

        result = shell_execute({"command": "false"})
        assert result["success"] is False
        assert result["exit_code"] == 1

    @patch('subprocess.run')
    def test_shell_execute_timeout(self, mock_run):
        """Test shell command timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)

        result = shell_execute({"command": "sleep 100", "timeout": 1})
        assert result["success"] is False
        assert "timed out" in result["error"]

    def test_shell_execute_no_command(self):
        """Test shell execute with no command."""
        result = shell_execute({})
        assert result["success"] is False
        assert "Missing required argument" in result["error"]

    @patch('subprocess.run')
    def test_process_list_windows(self, mock_run):
        """Test listing processes on Windows."""
        with patch('platform.system', return_value="Windows"):
            mock_run.return_value = Mock(
                stdout='"process1","1234"\n"process2","5678"\n',
                text=True
            )

            result = process_list({})
            assert result["success"] is True
            assert len(result["processes"]) == 2

    @patch('subprocess.run')
    def test_process_list_linux(self, mock_run):
        """Test listing processes on Linux."""
        with patch('platform.system', return_value="Linux"):
            mock_run.return_value = Mock(
                stdout="user 1234 0.0 0.0 process1 arg1\n",
                text=True
            )

            result = process_list({})
            assert result["success"] is True

    def test_process_list_with_filter(self):
        """Test listing processes with filter."""
        with patch('platform.system', return_value="Windows"):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    stdout='"python.exe","1234"\n"notepad.exe","5678"\n',
                    text=True
                )

                result = process_list({"filter_name": "python"})
                assert result["success"] is True
                assert len(result["processes"]) == 1
                assert result["processes"][0]["name"] == "python.exe"

    @patch('subprocess.run')
    def test_process_kill_by_pid(self, mock_run):
        """Test killing process by PID."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = process_kill({"pid": 1234})
        assert result["success"] is True

    @patch('subprocess.run')
    def test_process_kill_by_name(self, mock_run):
        """Test killing process by name."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = process_kill({"name": "notepad.exe"})
        assert result["success"] is True

    def test_process_kill_no_args(self):
        """Test killing process without PID or name."""
        result = process_kill({})
        assert result["success"] is False
        assert "Missing required argument" in result["error"]

    def test_system_info(self):
        """Test getting system information."""
        result = system_info({})
        assert result["success"] is True
        assert "info" in result
        assert "system" in result["info"]
        assert "python_version" in result["info"]

    def test_system_disk_usage(self):
        """Test getting disk usage."""
        result = system_disk_usage({})
        assert result["success"] is True
        assert "total_gb" in result
        assert "used_gb" in result
        assert "free_gb" in result
        assert "percent_used" in result

    def test_register_system_tools(self, reset_global_registry):
        """Test registering system tools."""
        register_system_tools()
        registry = get_global_registry()
        tools = registry.list_tools()
        tool_names = [t["name"] for t in tools]
        assert "fs_list" in tool_names
        assert "fs_read" in tool_names
        assert "shell_exec" in tool_names


# ============================================================================
# Tests for tool_registry.py
# ============================================================================

class TestToolRegistry:
    """Test ToolRegistry class."""

    def test_init(self):
        """Test registry initialization."""
        registry = ToolRegistry()
        assert len(registry.tools) == 0
        assert len(registry.mcp_clients) == 0
        assert len(registry.categories) == 0

    def test_register_builtin_tool(self, clean_registry):
        """Test registering a builtin tool."""
        tool = {
            "name": "test_tool",
            "description": "A test tool",
            "category": "test",
            "handler": lambda args: "result"
        }
        clean_registry.register_builtin_tool(tool)

        assert "test_tool" in clean_registry.tools
        assert clean_registry.tools["test_tool"]["type"] == "builtin"
        assert "test" in clean_registry.categories
        assert "test_tool" in clean_registry.categories["test"]

    def test_register_mcp_server(self, clean_registry, mock_mcp_client):
        """Test registering an MCP server."""
        tools = clean_registry.register_mcp_server("test_server", mock_mcp_client)

        assert len(tools) == 2
        assert "test_server.mcp_tool_1" in clean_registry.tools
        assert mock_mcp_client in clean_registry.mcp_clients.values()

    def test_register_custom_tool(self, clean_registry):
        """Test registering a custom tool."""
        tool = {
            "name": "custom_tool",
            "description": "A custom tool",
            "category": "custom",
            "handler": lambda args: "custom"
        }
        clean_registry.register_custom_tool(tool)

        assert "custom_tool" in clean_registry.tools
        assert clean_registry.tools["custom_tool"]["type"] == "custom"

    def test_get_tool(self, clean_registry):
        """Test getting a tool by name."""
        tool = {
            "name": "get_test",
            "description": "Test get_tool",
            "category": "test",
            "handler": lambda args: "test"
        }
        clean_registry.register_builtin_tool(tool)

        result = clean_registry.get_tool("get_test")
        assert result is not None
        assert result["name"] == "get_test"

    def test_get_tool_not_found(self, clean_registry):
        """Test getting nonexistent tool."""
        result = clean_registry.get_tool("nonexistent")
        assert result is None

    def test_get_tool_by_unique_name(self, clean_registry, mock_mcp_client):
        """Test getting tool by unique name."""
        clean_registry.register_mcp_server("server1", mock_mcp_client)

        result = clean_registry.get_tool("server1.mcp_tool_1")
        assert result is not None

    def test_list_tools(self, clean_registry):
        """Test listing tools."""
        tool1 = {
            "name": "tool1",
            "description": "Tool 1",
            "category": "cat1",
            "handler": lambda args: "1"
        }
        tool2 = {
            "name": "tool2",
            "description": "Tool 2",
            "category": "cat2",
            "handler": lambda args: "2"
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)

        all_tools = clean_registry.list_tools()
        assert len(all_tools) == 2

    def test_list_tools_by_category(self, clean_registry):
        """Test listing tools filtered by category."""
        tool1 = {
            "name": "tool1",
            "description": "Tool 1",
            "category": "math",
            "handler": lambda args: "1"
        }
        tool2 = {
            "name": "tool2",
            "description": "Tool 2",
            "category": "system",
            "handler": lambda args: "2"
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)

        math_tools = clean_registry.list_tools(category="math")
        assert len(math_tools) == 1
        assert math_tools[0]["name"] == "tool1"

    def test_list_tools_by_type(self, clean_registry):
        """Test listing tools filtered by type."""
        builtin_tool = {
            "name": "builtin1",
            "description": "Builtin",
            "category": "test",
            "handler": lambda args: "b"
        }
        clean_registry.register_builtin_tool(builtin_tool)

        builtin_tools = clean_registry.list_tools(tool_type="builtin")
        assert len(builtin_tools) == 1

    def test_search_tools(self, clean_registry):
        """Test searching tools."""
        tool1 = {
            "name": "search_tool",
            "description": "A tool for searching",
            "category": "web",
            "handler": lambda args: "search"
        }
        tool2 = {
            "name": "calc_tool",
            "description": "A calculator tool",
            "category": "math",
            "handler": lambda args: "calc"
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)

        results = clean_registry.search_tools("search")
        assert len(results) == 1
        assert results[0]["name"] == "search_tool"

        results = clean_registry.search_tools("tool")
        assert len(results) == 2

    def test_call_builtin_tool(self, clean_registry):
        """Test calling a builtin tool."""
        handler_mock = Mock(return_value="mock result")
        tool = {
            "name": "callable_tool",
            "description": "Callable",
            "category": "test",
            "handler": handler_mock
        }
        clean_registry.register_builtin_tool(tool)

        result = clean_registry.call_tool("callable_tool", {"arg": "value"})
        assert result == "mock result"
        handler_mock.assert_called_once_with({"arg": "value"})

    def test_call_tool_not_found(self, clean_registry):
        """Test calling nonexistent tool."""
        with pytest.raises(ValueError, match="Tool not found"):
            clean_registry.call_tool("nonexistent", {})

    def test_call_tool_no_handler(self, clean_registry):
        """Test calling tool without handler."""
        tool = {
            "name": "no_handler",
            "description": "No handler",
            "category": "test"
        }
        clean_registry.register_builtin_tool(tool)

        with pytest.raises(ValueError, match="No handler"):
            clean_registry.call_tool("no_handler", {})

    def test_list_categories(self, clean_registry):
        """Test listing categories."""
        tool1 = {
            "name": "cat_tool1",
            "description": "Tool 1",
            "category": "math",
            "handler": lambda args: "1"
        }
        tool2 = {
            "name": "cat_tool2",
            "description": "Tool 2",
            "category": "math",
            "handler": lambda args: "2"
        }
        tool3 = {
            "name": "cat_tool3",
            "description": "Tool 3",
            "category": "system",
            "handler": lambda args: "3"
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)
        clean_registry.register_builtin_tool(tool3)

        categories = clean_registry.list_categories()
        assert categories["math"] == 2
        assert categories["system"] == 1

    def test_remove_tool(self, clean_registry):
        """Test removing a tool."""
        tool = {
            "name": "to_remove",
            "description": "Remove me",
            "category": "test",
            "handler": lambda args: "removed"
        }
        clean_registry.register_builtin_tool(tool)

        assert "to_remove" in clean_registry.tools
        result = clean_registry.remove_tool("to_remove")
        assert result is True
        assert "to_remove" not in clean_registry.tools

    def test_remove_tool_not_found(self, clean_registry):
        """Test removing nonexistent tool."""
        result = clean_registry.remove_tool("nonexistent")
        assert result is False

    def test_clear(self, clean_registry):
        """Test clearing all tools."""
        tool = {
            "name": "tool1",
            "description": "Tool 1",
            "category": "test",
            "handler": lambda args: "1"
        }
        clean_registry.register_builtin_tool(tool)
        clean_registry.mcp_clients["test"] = Mock()

        clean_registry.clear()
        assert len(clean_registry.tools) == 0
        assert len(clean_registry.mcp_clients) == 0
        assert len(clean_registry.categories) == 0


class TestGlobalRegistryFunctions:
    """Test global registry convenience functions."""

    def test_get_global_registry(self, reset_global_registry):
        """Test getting global registry."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        assert registry1 is registry2  # Singleton

    def test_register_builtin_tool_global(self, reset_global_registry):
        """Test registering builtin tool to global registry."""
        tool = {
            "name": "global_tool",
            "description": "Global",
            "category": "test",
            "handler": lambda args: "global"
        }
        register_builtin_tool(tool)

        registry = get_global_registry()
        assert "global_tool" in registry.tools

    def test_list_tools_global(self, reset_global_registry):
        """Test listing tools from global registry."""
        tool = {
            "name": "list_tool",
            "description": "List",
            "category": "test",
            "handler": lambda args: "list"
        }
        register_builtin_tool(tool)

        tools = list_tools()
        assert len(tools) >= 1

    def test_call_tool_global(self, reset_global_registry):
        """Test calling tool via global registry."""
        handler_mock = Mock(return_value="called")
        tool = {
            "name": "call_tool",
            "description": "Call",
            "category": "test",
            "handler": handler_mock
        }
        register_builtin_tool(tool)

        result = call_tool("call_tool", {"arg": "val"})
        assert result == "called"


# ============================================================================
# Tests for tool_precompiler.py
# ============================================================================

class TestToolPrecompiler:
    """Test ToolPrecompiler class."""

    def test_init(self):
        """Test precompiler initialization."""
        precompiler = ToolPrecompiler()
        assert len(precompiler.id_map) == 0
        assert len(precompiler.reverse_map) == 0
        assert len(precompiler.compiled_tools) == 0

    def test_precompile_tool(self, clean_registry):
        """Test precompiling a single tool."""
        tool = {
            "name": "precompile_me",
            "description": "A tool to precompile",
            "category": "test",
            "handler": lambda args: "precompiled",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        tool_id = precompiler.precompile_tool("precompile_me")

        assert len(tool_id) == 8
        assert tool_id in precompiler.id_map
        assert "precompile_me" in precompiler.reverse_map
        assert tool_id in precompiler.compiled_tools

    def test_precompile_tool_not_found(self, clean_registry):
        """Test precompiling nonexistent tool."""
        precompiler = ToolPrecompiler(clean_registry)
        with pytest.raises(ValueError, match="Tool not found"):
            precompiler.precompile_tool("nonexistent")

    def test_precompile_all(self, clean_registry):
        """Test precompiling all tools."""
        tool1 = {
            "name": "tool1",
            "description": "Tool 1",
            "category": "test",
            "handler": lambda args: "1"
        }
        tool2 = {
            "name": "tool2",
            "description": "Tool 2",
            "category": "test",
            "handler": lambda args: "2"
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)

        precompiler = ToolPrecompiler(clean_registry)
        result = precompiler.precompile_all()

        assert len(result) == 2

    def test_generate_tool_id(self, clean_registry):
        """Test tool ID generation."""
        precompiler = ToolPrecompiler(clean_registry)
        tool_id = precompiler._generate_tool_id("test_tool_name")

        assert len(tool_id) == 8
        # Same name should generate same ID
        assert precompiler._generate_tool_id("test_tool_name") == tool_id

    def test_get_tool_id(self, clean_registry):
        """Test getting tool ID."""
        tool = {
            "name": "get_id_tool",
            "description": "Get ID",
            "category": "test",
            "handler": lambda args: "id"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        tool_id = precompiler.precompile_tool("get_id_tool")

        assert precompiler.get_tool_id("get_id_tool") == tool_id
        assert precompiler.get_tool_id("nonexistent") is None

    def test_get_tool_name(self, clean_registry):
        """Test getting tool name from ID."""
        tool = {
            "name": "get_name_tool",
            "description": "Get Name",
            "category": "test",
            "handler": lambda args: "name"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        tool_id = precompiler.precompile_tool("get_name_tool")

        assert precompiler.get_tool_name(tool_id) == "get_name_tool"
        assert precompiler.get_tool_name("nonexistent") is None

    def test_get_compiled_tool(self, clean_registry):
        """Test getting compiled tool info."""
        tool = {
            "name": "compiled_tool",
            "description": "Compiled",
            "category": "test",
            "handler": lambda args: "compiled"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        tool_id = precompiler.precompile_tool("compiled_tool")

        compiled = precompiler.get_compiled_tool(tool_id)
        assert compiled is not None
        assert compiled["name"] == "compiled_tool"

    def test_get_tools_prompt(self, clean_registry):
        """Test generating tools prompt."""
        tool = {
            "name": "prompt_tool",
            "description": "A tool for testing prompt generation",
            "category": "test",
            "handler": lambda args: "prompt"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        prompt = precompiler.get_tools_prompt()

        assert "prompt_tool" in prompt
        assert "TOOL_CALL:" in prompt

    def test_get_tools_prompt_truncates_description(self, clean_registry):
        """Test that get_tools_prompt truncates long descriptions."""
        tool = {
            "name": "long_desc_tool",
            "description": "A" * 100,  # Very long description
            "category": "test",
            "handler": lambda args: "long"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        prompt = precompiler.get_tools_prompt()

        # Description should be truncated to 50 chars
        assert len([line for line in prompt.split("\n") if "long_desc_tool" in line][0]) < 100

    def test_decompile_tool_call(self, clean_registry):
        """Test decompiling tool call."""
        tool = {
            "name": "decompile_tool",
            "description": "Decompile",
            "category": "test",
            "handler": lambda args: "decompiled"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        tool_id = precompiler.precompile_tool("decompile_tool")

        tool_call = f"TOOL_CALL: {tool_id} {{\"query\": \"test\"}}"
        result = precompiler.decompile_tool_call(tool_call)

        assert result["tool_name"] == "decompile_tool"
        assert result["arguments"]["query"] == "test"

    def test_decompile_tool_call_invalid_format(self, clean_registry):
        """Test decompiling invalid tool call format."""
        precompiler = ToolPrecompiler(clean_registry)
        with pytest.raises(ValueError, match="Invalid tool call format"):
            precompiler.decompile_tool_call("INVALID: xxx")

    def test_decompile_tool_call_unknown_id(self, clean_registry):
        """Test decompiling tool call with unknown ID."""
        precompiler = ToolPrecompiler(clean_registry)
        with pytest.raises(ValueError, match="Unknown tool ID"):
            precompiler.decompile_tool_call("TOOL_CALL: unknown_id {}")

    def test_save_and_load(self, clean_registry, temp_dir):
        """Test saving and loading precompiled tools."""
        tool = {
            "name": "save_load_tool",
            "description": "Save and Load",
            "category": "test",
            "handler": lambda args: "saved"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        precompiler.precompile_all()

        filepath = Path(temp_dir) / "precompiled.json"
        precompiler.save(str(filepath))

        assert filepath.exists()

        new_precompiler = ToolPrecompiler()
        new_precompiler.load(str(filepath))

        assert len(new_precompiler.id_map) == len(precompiler.id_map)


class TestGlobalPrecompilerFunctions:
    """Test global precompiler convenience functions."""

    def test_get_global_precompiler(self, reset_global_precompiler):
        """Test getting global precompiler."""
        precompiler1 = get_global_precompiler()
        precompiler2 = get_global_precompiler()
        assert precompiler1 is precompiler2

    def test_precompile_tools(self, reset_global_precompiler, reset_global_registry):
        """Test precompile_tools convenience function."""
        tool = {
            "name": "conv_tool",
            "description": "Convenience",
            "category": "test",
            "handler": lambda args: "conv"
        }
        register_builtin_tool(tool)

        result = precompile_tools()
        assert len(result) >= 1

    def test_get_tools_prompt_global(self, reset_global_precompiler, reset_global_registry):
        """Test get_tools_prompt convenience function."""
        tool = {
            "name": "prompt_conv",
            "description": "Prompt Convenience",
            "category": "test",
            "handler": lambda args: "prompt"
        }
        register_builtin_tool(tool)

        prompt = get_tools_prompt()
        assert "prompt_conv" in prompt

    def test_decompile_tool_call_global(self, reset_global_precompiler, reset_global_registry):
        """Test decompile_tool_call convenience function."""
        tool = {
            "name": "decompile_conv",
            "description": "Decompile Convenience",
            "category": "test",
            "handler": lambda args: "decompile"
        }
        register_builtin_tool(tool)

        precompile_tools()

        tool_id = get_global_precompiler().get_tool_id("decompile_conv")
        tool_call = f"TOOL_CALL: {tool_id} {{}}"

        result = decompile_tool_call(tool_call)
        assert result["tool_name"] == "decompile_conv"


# ============================================================================
# Tests for tool_distiller.py
# ============================================================================

class TestToolDistiller:
    """Test ToolDistiller class."""

    def test_init(self):
        """Test distiller initialization."""
        distiller = ToolDistiller()
        assert len(distiller.distilled_tools) == 0
        assert len(distiller.full_tools) == 0

    def test_distill_tool(self, clean_registry):
        """Test distilling a single tool."""
        tool = {
            "name": "distill_me",
            "description": "A tool for distilling with very long description that should be shortened",
            "category": "test",
            "handler": lambda args: "distilled",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                }
            }
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        precompiler.precompile_all()

        distiller = ToolDistiller(clean_registry, precompiler)
        result = distiller.distill_tool("distill_me")

        assert "id" in result
        assert "desc" in result
        assert "params" in result
        assert result["distilled"] is True

    def test_distill_tool_not_found(self, clean_registry):
        """Test distilling nonexistent tool."""
        distiller = ToolDistiller(clean_registry)
        with pytest.raises(ValueError, match="Tool not found"):
            distiller.distill_tool("nonexistent")

    def test_distill_all(self, clean_registry):
        """Test distilling all tools."""
        tool1 = {
            "name": "distill1",
            "description": "Tool 1 for distilling",
            "category": "test",
            "handler": lambda args: "1"
        }
        tool2 = {
            "name": "distill2",
            "description": "Tool 2 for distilling",
            "category": "test",
            "handler": lambda args: "2"
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)

        precompiler = ToolPrecompiler(clean_registry)
        precompiler.precompile_all()

        distiller = ToolDistiller(clean_registry, precompiler)
        result = distiller.distill_all()

        assert len(result) == 2

    def test_distill_description(self, clean_registry):
        """Test description distillation."""
        distiller = ToolDistiller(clean_registry)

        # Test basic distillation
        long_desc = "This is a very long description " * 20
        distilled = distiller._distill_description(long_desc)
        assert len(distilled) <= 200

        # Test removal of redundant phrases
        redundant_desc = "This tool is used to do something useful"
        distilled = distiller._distill_description(redundant_desc)
        assert "This tool is used to" not in distilled

        # Test whitespace normalization
        whitespace_desc = "Too    many     spaces"
        distilled = distiller._distill_description(whitespace_desc)
        assert "  " not in distilled

    def test_distill_description_removes_examples(self, clean_registry):
        """Test that distillation removes examples."""
        distiller = ToolDistiller(clean_registry)

        desc_with_example = "This tool does X. Example: This is how you use it. More info."
        distilled = distiller._distill_description(desc_with_example)
        assert "Example:" not in distilled

    def test_distill_input_schema(self, clean_registry):
        """Test input schema distillation."""
        distiller = ToolDistiller(clean_registry)

        schema = {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "A parameter"},
                "param2": {"type": "integer", "description": "Another parameter"}
            }
        }

        distilled = distiller._distill_input_schema(schema)
        assert "param1" in distilled
        assert distilled["param1"] == "string"
        assert "param2" in distilled
        assert distilled["param2"] == "integer"

    def test_distill_input_schema_empty(self, clean_registry):
        """Test distilling empty input schema."""
        distiller = ToolDistiller(clean_registry)
        distilled = distiller._distill_input_schema({})
        assert distilled == {}

    def test_get_distilled_prompt(self, clean_registry):
        """Test getting distilled prompt."""
        tool = {
            "name": "prompt_distill",
            "description": "A tool for testing distilled prompt",
            "category": "test",
            "handler": lambda args: "prompt",
            "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}}
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        precompiler.precompile_all()

        distiller = ToolDistiller(clean_registry, precompiler)
        prompt = distiller.get_distilled_prompt()

        assert "prompt_distill" in prompt
        assert "TOOL_CALL:" in prompt

    def test_get_full_tool_info(self, clean_registry):
        """Test getting full tool info."""
        tool = {
            "name": "full_info",
            "description": "Full info tool with complete description",
            "category": "test",
            "handler": lambda args: "full"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        precompiler.precompile_all()

        distiller = ToolDistiller(clean_registry, precompiler)
        distilled = distiller.distill_all()

        tool_id = list(distilled.keys())[0]
        full_info = distiller.get_full_tool_info(tool_id)

        assert full_info is not None
        assert full_info["name"] == "full_info"
        assert "Full info tool" in full_info["description"]

    def test_save_and_load(self, clean_registry, temp_dir):
        """Test saving and loading distilled tools."""
        tool = {
            "name": "save_distill",
            "description": "Save and load distilled tools",
            "category": "test",
            "handler": lambda args: "save"
        }
        clean_registry.register_builtin_tool(tool)

        precompiler = ToolPrecompiler(clean_registry)
        precompiler.precompile_all()

        distiller = ToolDistiller(clean_registry, precompiler)
        distiller.distill_all()

        filepath = Path(temp_dir) / "distilled.json"
        distiller.save(str(filepath))

        assert filepath.exists()

        new_distiller = ToolDistiller()
        new_distiller.load(str(filepath))

        assert len(new_distiller.distilled_tools) == len(distiller.distilled_tools)


class TestGlobalDistillerFunctions:
    """Test global distiller convenience functions."""

    def test_get_global_distiller(self, reset_global_distiller):
        """Test getting global distiller."""
        distiller1 = get_global_distiller()
        distiller2 = get_global_distiller()
        assert distiller1 is distiller2

    def test_distill_tools(self, reset_global_distiller, reset_global_registry):
        """Test distill_tools convenience function."""
        tool = {
            "name": "distill_conv",
            "description": "Distill convenience",
            "category": "test",
            "handler": lambda args: "distill"
        }
        register_builtin_tool(tool)

        # Need to precompile first
        precompile_tools()

        result = distill_tools()
        assert len(result) >= 1

    def test_get_distilled_prompt_global(self, reset_global_distiller, reset_global_registry):
        """Test get_distilled_prompt convenience function."""
        tool = {
            "name": "prompt_distill_conv",
            "description": "Prompt distill convenience",
            "category": "test",
            "handler": lambda args: "prompt"
        }
        register_builtin_tool(tool)

        precompile_tools()
        distill_tools()

        prompt = get_distilled_prompt()
        assert "prompt_distill_conv" in prompt


# ============================================================================
# Tests for tool_executor.py
# ============================================================================

class TestToolExecutionError:
    """Test ToolExecutionError exception."""

    def test_init(self):
        """Test ToolExecutionError initialization."""
        error = ToolExecutionError(
            "Test error",
            tool_name="test_tool",
            arguments={"arg": "val"},
            original_error=ValueError("Original")
        )
        assert error.message == "Test error"
        assert error.tool_name == "test_tool"
        assert error.arguments == {"arg": "val"}
        assert isinstance(error.original_error, ValueError)


class TestToolExecutor:
    """Test ToolExecutor class."""

    def test_init(self):
        """Test executor initialization."""
        executor = ToolExecutor()
        assert executor.max_retries == 3
        assert executor.timeout == 60

        executor = ToolExecutor(max_retries=5, timeout=30)
        assert executor.max_retries == 5
        assert executor.timeout == 30

    def test_execute_success(self, clean_registry):
        """Test successful tool execution."""
        handler_mock = Mock(return_value="success")
        tool = {
            "name": "exec_tool",
            "description": "Exec",
            "category": "test",
            "handler": handler_mock
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry)
        result = executor.execute("exec_tool", {"arg": "val"})

        assert result == "success"
        handler_mock.assert_called_once_with({"arg": "val"})

    def test_execute_with_retry(self, clean_registry):
        """Test tool execution with retry."""
        handler_mock = Mock(side_effect=[Exception("Fail 1"), Exception("Fail 2"), "success"])
        tool = {
            "name": "retry_tool",
            "description": "Retry",
            "category": "test",
            "handler": handler_mock
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry, max_retries=2)
        result = executor.execute("retry_tool", {})

        assert result == "success"
        assert handler_mock.call_count == 3

    def test_execute_all_retries_fail(self, clean_registry):
        """Test tool execution when all retries fail."""
        handler_mock = Mock(side_effect=Exception("Always fails"))
        tool = {
            "name": "fail_tool",
            "description": "Fail",
            "category": "test",
            "handler": handler_mock
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry, max_retries=2)

        with pytest.raises(ToolExecutionError, match="Tool execution failed"):
            executor.execute("fail_tool", {})

    def test_execute_permission_denied(self, clean_registry):
        """Test tool execution with permission denied."""
        tool = {
            "name": "restricted_tool",
            "description": "Restricted",
            "category": "test",
            "handler": lambda args: "result"
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry)
        context = {"user_role": "restricted"}

        with pytest.raises(ToolExecutionError, match="Permission denied"):
            executor.execute("restricted_tool", {}, context)

    def test_execute_permission_admin(self, clean_registry):
        """Test tool execution with admin role."""
        handler_mock = Mock(return_value="admin result")
        tool = {
            "name": "admin_tool",
            "description": "Admin",
            "category": "test",
            "handler": handler_mock
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry)
        context = {"user_role": "admin"}

        result = executor.execute("admin_tool", {}, context)
        assert result == "admin result"

    def test_execute_permission_user_dangerous(self, clean_registry):
        """Test tool execution with dangerous tool and user role."""
        tool = {
            "name": "fs_delete",
            "description": "Delete",
            "category": "filesystem",
            "handler": lambda args: "deleted"
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry)
        context = {"user_role": "user", "confirmed": False}

        with pytest.raises(ToolExecutionError, match="Permission denied"):
            executor.execute("fs_delete", {}, context)

    @pytest.mark.asyncio
    async def test_execute_async(self, clean_registry):
        """Test async tool execution."""
        handler_mock = Mock(return_value="async result")
        tool = {
            "name": "async_tool",
            "description": "Async",
            "category": "test",
            "handler": handler_mock
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry)
        result = await executor.execute_async("async_tool", {})

        assert result == "async result"

    def test_batch_execute(self, clean_registry):
        """Test batch tool execution."""
        def handler1(args):
            return "result1"

        def handler2(args):
            return "result2"

        tool1 = {
            "name": "batch1",
            "description": "Batch 1",
            "category": "test",
            "handler": handler1
        }
        tool2 = {
            "name": "batch2",
            "description": "Batch 2",
            "category": "test",
            "handler": handler2
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)

        executor = ToolExecutor(clean_registry)
        tool_calls = [
            {"tool_name": "batch1", "arguments": {}},
            {"tool_name": "batch2", "arguments": {}}
        ]
        results = executor.batch_execute(tool_calls)

        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_batch_execute_with_error(self, clean_registry):
        """Test batch execution with one tool failing."""
        def handler_success(args):
            return "success"

        tool1 = {
            "name": "success_tool",
            "description": "Success",
            "category": "test",
            "handler": handler_success
        }
        tool2 = {
            "name": "nonexistent_tool",
            "description": "Nonexistent",
            "category": "test",
            "handler": lambda args: "never called"
        }
        clean_registry.register_builtin_tool(tool1)

        executor = ToolExecutor(clean_registry)
        tool_calls = [
            {"tool_name": "success_tool", "arguments": {}},
            {"tool_name": "nonexistent_tool", "arguments": {}}
        ]
        results = executor.batch_execute(tool_calls)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False

    @pytest.mark.asyncio
    async def test_batch_execute_async(self, clean_registry):
        """Test async batch tool execution."""
        def handler1(args):
            return "async1"

        def handler2(args):
            return "async2"

        tool1 = {
            "name": "abatch1",
            "description": "Async Batch 1",
            "category": "test",
            "handler": handler1
        }
        tool2 = {
            "name": "abatch2",
            "description": "Async Batch 2",
            "category": "test",
            "handler": handler2
        }
        clean_registry.register_builtin_tool(tool1)
        clean_registry.register_builtin_tool(tool2)

        executor = ToolExecutor(clean_registry)
        tool_calls = [
            {"tool_name": "abatch1", "arguments": {}},
            {"tool_name": "abatch2", "arguments": {}}
        ]
        results = await executor.batch_execute_async(tool_calls)

        assert len(results) == 2
        assert all(r["success"] for r in results)

    @patch('subprocess.run')
    def test_execute_in_docker_docker_unavailable(self, mock_run, clean_registry):
        """Test Docker execution when Docker is unavailable."""
        mock_run.side_effect = FileNotFoundError("docker not found")

        handler_mock = Mock(return_value="fallback result")
        tool = {
            "name": "docker_tool",
            "description": "Docker",
            "category": "test",
            "handler": handler_mock
        }
        clean_registry.register_builtin_tool(tool)

        executor = ToolExecutor(clean_registry)
        result = executor._execute_in_docker("docker_tool", {})

        # Should fallback to regular execute
        assert result == "fallback result"

    def test_execute_in_sandbox_unsupported(self, clean_registry):
        """Test unsupported sandbox type."""
        executor = ToolExecutor(clean_registry)
        with pytest.raises(ToolExecutionError, match="Unsupported sandbox type"):
            executor.execute_in_sandbox("test_tool", {}, sandbox_type="unsupported")


class TestGlobalExecutorFunctions:
    """Test global executor convenience functions."""

    def test_execute_tool(self, reset_global_registry):
        """Test execute_tool convenience function."""
        handler_mock = Mock(return_value="global exec")
        tool = {
            "name": "global_exec_tool",
            "description": "Global Exec",
            "category": "test",
            "handler": handler_mock
        }
        register_builtin_tool(tool)

        result = execute_tool("global_exec_tool", {})
        assert result == "global exec"

    @pytest.mark.asyncio
    async def test_execute_tool_async(self, reset_global_registry):
        """Test execute_tool_async convenience function."""
        handler_mock = Mock(return_value="global async")
        tool = {
            "name": "global_async_tool",
            "description": "Global Async",
            "category": "test",
            "handler": handler_mock
        }
        register_builtin_tool(tool)

        result = await execute_tool_async("global_async_tool", {})
        assert result == "global async"

    def test_batch_execute_tools(self, reset_global_registry):
        """Test batch_execute_tools convenience function."""
        def handler(args):
            return "batch result"

        tool = {
            "name": "batch_conv_tool",
            "description": "Batch Convenience",
            "category": "test",
            "handler": handler
        }
        register_builtin_tool(tool)

        tool_calls = [{"tool_name": "batch_conv_tool", "arguments": {}}]
        results = batch_execute_tools(tool_calls)

        assert len(results) == 1
        assert results[0]["success"] is True


# ============================================================================
# Tests for tool_sandbox.py
# ============================================================================

class TestToolSandbox:
    """Test ToolSandbox class."""

    def test_init(self):
        """Test sandbox initialization."""
        sandbox = ToolSandbox()
        assert sandbox.sandbox_type == "subprocess"
        assert sandbox.max_memory_mb == 512
        assert sandbox.max_cpu_time == 30

        sandbox = ToolSandbox(sandbox_type="docker", max_memory_mb=256, max_cpu_time=60)
        assert sandbox.sandbox_type == "docker"
        assert sandbox.max_memory_mb == 256
        assert sandbox.max_cpu_time == 60

    def test_execute_unsupported_type(self):
        """Test executing with unsupported sandbox type."""
        sandbox = ToolSandbox(sandbox_type="unsupported")
        with pytest.raises(ToolExecutionError, match="Unsupported sandbox type"):
            sandbox.execute("test_tool", {})

    @patch('subprocess.run')
    def test_execute_subprocess_success(self, mock_run, temp_dir):
        """Test successful subprocess sandbox execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"result": "sandbox success"}),
            stderr=""
        )

        sandbox = ToolSandbox(sandbox_type="subprocess")
        code = "import json; print(json.dumps({'result': 'sandbox success'}))"

        result = sandbox._execute_subprocess("test_tool", {}, code)
        assert result == {"result": "sandbox success"}

    @patch('subprocess.run')
    def test_execute_subprocess_timeout(self, mock_run):
        """Test subprocess sandbox timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)

        sandbox = ToolSandbox(sandbox_type="subprocess", max_cpu_time=1)
        code = "import time; time.sleep(100)"

        with pytest.raises(ToolExecutionError, match="timed out"):
            sandbox._execute_subprocess("test_tool", {}, code)

    @patch('subprocess.run')
    def test_execute_subprocess_failure(self, mock_run):
        """Test subprocess sandbox execution failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Execution failed"
        )

        sandbox = ToolSandbox(sandbox_type="subprocess")
        code = "raise Exception('fail')"

        with pytest.raises(ToolExecutionError, match="Execution failed"):
            sandbox._execute_subprocess("test_tool", {}, code)

    def test_execute_subprocess_no_code(self):
        """Test subprocess sandbox without code."""
        sandbox = ToolSandbox(sandbox_type="subprocess")
        with pytest.raises(ToolExecutionError, match="not yet implemented"):
            sandbox._execute_subprocess("test_tool", {})

    @patch('subprocess.run')
    def test_execute_docker_docker_unavailable(self, mock_run):
        """Test Docker execution when Docker is unavailable."""
        mock_run.side_effect = FileNotFoundError("docker not found")

        sandbox = ToolSandbox(sandbox_type="docker")
        result = sandbox._execute_docker("test_tool", {})

        # Should fallback to regular execute
        assert result is not None

    @patch('subprocess.run')
    def test_execute_gvisor_unavailable(self, mock_run):
        """Test gVisor execution when unavailable."""
        mock_run.side_effect = FileNotFoundError("runsc not found")

        sandbox = ToolSandbox(sandbox_type="gvisor")
        result = sandbox._execute_gvisor("test_tool", {})

        # Should fallback to Docker
        assert result is not None

    def test_execute_safe_success(self):
        """Test safe execution that succeeds."""
        sandbox = ToolSandbox(sandbox_type="subprocess")

        with patch.object(sandbox, 'execute', return_value="safe result"):
            result = sandbox.execute_safe("test_tool", {})

            assert result["success"] is True
            assert result["result"] == "safe result"
            assert result["error"] is None

    def test_execute_safe_failure(self):
        """Test safe execution that fails."""
        sandbox = ToolSandbox(sandbox_type="subprocess")

        with patch.object(sandbox, 'execute', side_effect=Exception("Safe fail")):
            result = sandbox.execute_safe("test_tool", {})

            assert result["success"] is False
            assert result["result"] is None
            assert "Safe fail" in result["error"]


class TestDockerSandbox:
    """Test DockerSandbox class."""

    def test_init(self):
        """Test DockerSandbox initialization."""
        sandbox = DockerSandbox()
        assert sandbox.sandbox_type == "docker"
        assert sandbox.image == "python:3.12-slim"
        assert sandbox.max_memory_mb == 512

        sandbox = DockerSandbox(image="python:3.11", max_memory_mb=256, max_cpu_time=60)
        assert sandbox.image == "python:3.11"
        assert sandbox.max_memory_mb == 256

    def test_execute_docker_no_code(self):
        """Test Docker execution without code."""
        sandbox = DockerSandbox()
        with pytest.raises(ToolExecutionError, match="requires code parameter"):
            sandbox._execute_docker("test_tool", {})


class TestSandboxFunctions:
    """Test sandbox convenience functions."""

    def test_create_sandbox_subprocess(self):
        """Test creating subprocess sandbox."""
        sandbox = create_sandbox(sandbox_type="subprocess")
        assert isinstance(sandbox, ToolSandbox)
        assert sandbox.sandbox_type == "subprocess"

    def test_create_sandbox_docker(self):
        """Test creating Docker sandbox."""
        sandbox = create_sandbox(sandbox_type="docker")
        assert isinstance(sandbox, DockerSandbox)
        assert sandbox.sandbox_type == "docker"

    def test_create_sandbox_default(self):
        """Test creating default sandbox."""
        sandbox = create_sandbox()
        assert isinstance(sandbox, ToolSandbox)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the entire tools module."""

    def test_full_tool_lifecycle(self, reset_global_registry, reset_global_precompiler, reset_global_distiller):
        """Test full lifecycle: register, precompile, distill, execute."""
        # Register tool
        def my_handler(args):
            return f"Hello, {args.get('name', 'World')}!"

        tool = {
            "name": "greet",
            "description": "Greet someone with a personalized message",
            "category": "social",
            "handler": my_handler,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
        register_builtin_tool(tool)

        # Precompile
        precompile_tools()

        # Distill
        distill_tools()

        # Execute
        result = call_tool("greet", {"name": "SerpentAI"})
        assert "SerpentAI" in result

        # Get distilled prompt
        prompt = get_distilled_prompt()
        assert "greet" in prompt

    def test_mcp_integration(self, reset_global_registry):
        """Test MCP server integration."""
        mock_client = Mock()
        mock_client.list_tools.return_value = {
            "tools": [
                {"name": "mcp_greet", "description": "MCP Greet", "inputSchema": {}}
            ]
        }
        mock_client.call_tool.return_value = {"content": [{"text": "MCP Hello"}]}

        registry = get_global_registry()
        registry.register_mcp_server("test_mcp", mock_client)

        tools = registry.list_tools()
        mcp_tools = [t for t in tools if t.get("server") == "test_mcp"]
        assert len(mcp_tools) == 1

        result = registry.call_tool("test_mcp.mcp_greet", {})
        assert result == {"content": [{"text": "MCP Hello"}]}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
