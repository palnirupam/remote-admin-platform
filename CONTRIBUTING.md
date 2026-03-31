# Contributing Guidelines

Thank you for your interest in contributing to the Remote System Enhancement project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior

- Be respectful and considerate
- Welcome newcomers and help them get started
- Provide constructive feedback
- Focus on what is best for the project
- Show empathy towards other contributors

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other conduct inappropriate in a professional setting

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of client-server architecture
- Familiarity with Python development

### Finding Issues to Work On

1. Check the [issue tracker](https://github.com/your-repo/issues)
2. Look for issues labeled `good first issue` or `help wanted`
3. Comment on the issue to express interest
4. Wait for maintainer assignment before starting work

### Communication Channels

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and discussions
- Pull Requests: Code contributions

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/remote-system-enhancement.git
cd remote-system-enhancement

# Add upstream remote
git remote add upstream https://github.com/original-repo/remote-system-enhancement.git
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 4. Verify Setup

```bash
# Run tests
pytest

# Check code style
flake8 remote_system/
black --check remote_system/

# Run type checker
mypy remote_system/
```

## Development Workflow

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### Branch Naming Convention

- `feature/` - New features
- `bugfix/` - Bug fixes
- `hotfix/` - Urgent fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications

Examples:
- `feature/add-registry-plugin`
- `bugfix/fix-connection-timeout`
- `docs/update-api-documentation`

### 2. Make Changes

```bash
# Make your changes
# Add tests for new functionality
# Update documentation as needed

# Run tests frequently
pytest tests/

# Check code style
black remote_system/
flake8 remote_system/
```

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add registry plugin for Windows"
```

### Commit Message Guidelines

Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Build process or auxiliary tool changes

Example:
```
feat(plugins): Add Windows registry editor plugin

Implement registry plugin with read, write, and delete operations.
Supports all registry hives and value types.

Closes #123
```

### 4. Push Changes

```bash
# Push to your fork
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select your feature branch
4. Fill out the PR template
5. Submit the pull request

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

**Line Length:**
- Maximum 100 characters per line
- Use parentheses for line continuation

**Imports:**
```python
# Standard library imports
import os
import sys

# Third-party imports
import requests
from flask import Flask

# Local imports
from remote_system.enhanced_server import EnhancedServer
```

**Naming Conventions:**
```python
# Classes: PascalCase
class EnhancedServer:
    pass

# Functions and variables: snake_case
def execute_command(command_text):
    result_data = process_command(command_text)
    return result_data

# Constants: UPPER_SNAKE_CASE
MAX_CONNECTIONS = 1000
DEFAULT_TIMEOUT = 300

# Private methods: _leading_underscore
def _internal_helper(self):
    pass
```

**Type Hints:**
```python
from typing import List, Dict, Optional

def get_agents(status: Optional[str] = None) -> List[Dict[str, any]]:
    """
    Get list of agents filtered by status.
    
    Args:
        status: Optional status filter ('online', 'offline', 'idle')
        
    Returns:
        List of agent dictionaries
    """
    pass
```

**Docstrings:**

Use Google-style docstrings:

```python
def transfer_file(source: str, destination: str, chunk_size: int = 4096) -> bool:
    """
    Transfer file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        chunk_size: Size of chunks for transfer (default: 4096)
        
    Returns:
        True if transfer successful, False otherwise
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        PermissionError: If insufficient permissions
        
    Example:
        >>> transfer_file('/tmp/source.txt', '/tmp/dest.txt')
        True
    """
    pass
```

### Code Organization

**File Structure:**
```
remote_system/
├── enhanced_server/
│   ├── __init__.py
│   ├── enhanced_server.py
│   ├── database_manager.py
│   └── auth_module.py
├── enhanced_agent/
│   ├── __init__.py
│   ├── enhanced_agent.py
│   └── plugin_manager.py
└── plugins/
    ├── __init__.py
    ├── file_transfer_plugin.py
    └── screenshot_plugin.py
```

**Class Organization:**
```python
class MyClass:
    """Class docstring."""
    
    # Class variables
    CLASS_CONSTANT = 100
    
    def __init__(self):
        """Initialize instance."""
        # Instance variables
        self.public_var = None
        self._private_var = None
    
    # Public methods
    def public_method(self):
        """Public method docstring."""
        pass
    
    # Private methods
    def _private_method(self):
        """Private method docstring."""
        pass
    
    # Properties
    @property
    def my_property(self):
        """Property docstring."""
        return self._private_var
    
    # Static methods
    @staticmethod
    def static_method():
        """Static method docstring."""
        pass
    
    # Class methods
    @classmethod
    def class_method(cls):
        """Class method docstring."""
        pass
```

### Error Handling

```python
# Good: Specific exception handling
try:
    result = execute_command(command)
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    return PluginResult(False, None, f"File not found: {e}")
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    return PluginResult(False, None, f"Permission denied: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return PluginResult(False, None, f"Unexpected error: {e}")

# Bad: Bare except
try:
    result = execute_command(command)
except:
    return None
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed information for debugging")
logger.info("General informational messages")
logger.warning("Warning messages for potentially harmful situations")
logger.error("Error messages for serious problems")
logger.critical("Critical messages for very serious errors")

# Include context in log messages
logger.info(f"Agent {agent_id} connected from {ip_address}")
logger.error(f"Failed to execute command: {command}", exc_info=True)
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/
│   ├── test_enhanced_server.py
│   ├── test_database_manager.py
│   └── test_auth_module.py
├── integration/
│   ├── test_agent_connection.py
│   └── test_file_transfer.py
├── property/
│   ├── test_authentication_properties.py
│   └── test_file_transfer_properties.py
└── conftest.py
```

### Writing Unit Tests

```python
import unittest
from unittest.mock import Mock, patch
from remote_system.enhanced_server import EnhancedServer

class TestEnhancedServer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.server = EnhancedServer(
            host="localhost",
            port=9999,
            db_path=":memory:"
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.server.stop()
    
    def test_server_initialization(self):
        """Test server initializes correctly."""
        self.assertEqual(self.server.host, "localhost")
        self.assertEqual(self.server.port, 9999)
    
    @patch('socket.socket')
    def test_agent_connection(self, mock_socket):
        """Test agent connection handling."""
        mock_conn = Mock()
        mock_socket.return_value = mock_conn
        
        result = self.server.handleAgentConnection(mock_conn, ("127.0.0.1", 12345))
        
        self.assertTrue(result)
        mock_conn.send.assert_called()
```

### Writing Integration Tests

```python
import pytest
from remote_system.enhanced_server import EnhancedServer
from remote_system.enhanced_agent import EnhancedAgent

@pytest.fixture
def server():
    """Create test server."""
    server = EnhancedServer(host="localhost", port=9999, db_path=":memory:")
    server.start()
    yield server
    server.stop()

@pytest.fixture
def agent(server):
    """Create test agent."""
    agent = EnhancedAgent(server_ip="localhost", server_port=9999, token="test_token")
    agent.connect()
    yield agent
    agent.disconnect()

def test_agent_connection(server, agent):
    """Test agent can connect to server."""
    assert agent.is_connected()
    assert len(server.get_active_agents()) == 1

def test_command_execution(server, agent):
    """Test command execution flow."""
    command = {"plugin": "executor", "action": "execute_command", "args": {"command": "echo test"}}
    result = server.send_command(agent.agent_id, command)
    
    assert result.success
    assert "test" in result.data["stdout"]
```

### Writing Property-Based Tests

```python
from hypothesis import given, strategies as st
from remote_system.enhanced_server.auth_module import AuthenticationModule

@given(agent_id=st.uuids(), metadata=st.dictionaries(st.text(), st.text()))
def test_token_generation_and_validation(agent_id, metadata):
    """
    Property: Any generated token must validate successfully before expiration.
    """
    auth = AuthenticationModule(secret_key="test_key", token_expiry=3600)
    
    # Generate token
    token = auth.generate_token(str(agent_id), metadata)
    
    # Validate token
    validation = auth.validate_token(token)
    
    # Assert property holds
    assert validation.valid
    assert validation.agent_id == str(agent_id)
```

### Test Coverage

Aim for:
- Unit tests: 80%+ coverage
- Integration tests: Critical paths covered
- Property tests: Core invariants verified

Run coverage:
```bash
pytest --cov=remote_system --cov-report=html
```

## Documentation

### Code Documentation

- Add docstrings to all public classes, methods, and functions
- Include type hints for function parameters and return values
- Provide usage examples in docstrings
- Document exceptions that can be raised

### User Documentation

When adding features, update:
- README.md - If it affects quick start
- USAGE.md - Add usage examples
- API.md - Document new API endpoints
- PLUGINS.md - Document new plugins

### Developer Documentation

When making architectural changes, update:
- ARCHITECTURE.md - Document design decisions
- CONTRIBUTING.md - Update development guidelines

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages follow guidelines
- [ ] Branch is up to date with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass

## Related Issues
Closes #123
```

### Review Process

1. Automated checks run (tests, linting, coverage)
2. Maintainer reviews code
3. Address review comments
4. Maintainer approves and merges

### After Merge

- Delete feature branch
- Update local main branch
- Close related issues

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen

**Screenshots**
If applicable, add screenshots

**Environment:**
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.10]
- Version: [e.g. 1.0.0]

**Additional context**
Any other relevant information
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Describe the solution you'd like**
Clear description of desired solution

**Describe alternatives you've considered**
Alternative solutions considered

**Additional context**
Any other relevant information
```

## Development Tips

### Debugging

```python
# Use logging instead of print
logger.debug(f"Variable value: {variable}")

# Use pdb for interactive debugging
import pdb; pdb.set_trace()

# Use pytest with -s flag to see print output
pytest -s tests/test_file.py
```

### Performance Profiling

```python
# Profile code
python -m cProfile -o profile.stats script.py

# Analyze profile
python -m pstats profile.stats
```

### Common Pitfalls

1. **Not updating tests**: Always update tests when changing functionality
2. **Ignoring type hints**: Use type hints for better code quality
3. **Poor error handling**: Handle specific exceptions, not bare except
4. **Missing documentation**: Document all public APIs
5. **Not testing edge cases**: Test boundary conditions and error cases

## Getting Help

- Check existing documentation
- Search closed issues
- Ask in GitHub Discussions
- Contact maintainers

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to Remote System Enhancement!
