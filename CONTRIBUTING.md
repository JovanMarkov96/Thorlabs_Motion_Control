# Contributing to ThorlabsMotionControl

Thank you for your interest in contributing to ThorlabsMotionControl! This document provides 
guidelines and instructions for contributing to this project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Adding New Controller Support](#adding-new-controller-support)
- [Documentation](#documentation)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a professional environment

---

## Getting Started

### Prerequisites

1. **Python 3.8+** — Required for type hints and modern syntax
2. **Thorlabs Kinesis** — Install from Thorlabs website
3. **Git** — For version control
4. **Hardware** — Access to Thorlabs controllers for testing

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/ThorlabsMotionControl.git
cd ThorlabsMotionControl

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL/ThorlabsMotionControl.git
```

---

## Development Setup

### Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### Install Dependencies

```bash
# Install runtime dependencies
pip install pythonnet pywin32 PyQt5

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy
```

### Verify Setup

```bash
# Check imports work
python -c "from Hardware.ThorlabsMotionControl import discover_devices; print('OK')"

# Run tests (with hardware connected)
python -m Hardware.ThorlabsMotionControl.tests.run_all_tests --list
```

---

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with the following specifics:

| Aspect | Standard |
|--------|----------|
| Line length | 100 characters max |
| Indentation | 4 spaces (no tabs) |
| Quotes | Double quotes for strings |
| Imports | Grouped (stdlib, third-party, local) |
| Type hints | Required for public APIs |

### Formatting with Black

```bash
# Format code
black --line-length 100 .

# Check formatting
black --check --line-length 100 .
```

### Linting with Flake8

```bash
# Run linter
flake8 --max-line-length 100 --ignore E203,W503 .
```

### Type Checking with MyPy

```bash
# Run type checker
mypy --ignore-missing-imports .
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `KDC101Controller` |
| Functions | snake_case | `discover_devices()` |
| Constants | UPPER_SNAKE | `KINESIS_PATH` |
| Private | _prefix | `_load_assemblies()` |
| Protected | _prefix | `_device` |

### Docstring Format

Use Google-style docstrings:

```python
def move_absolute(self, position: float, wait: bool = True, timeout: float = 60.0) -> bool:
    """
    Move stage to an absolute position.
    
    Args:
        position: Target position in real-world units (mm or degrees).
        wait: If True, block until movement completes.
        timeout: Maximum time to wait for movement (seconds).
    
    Returns:
        True if movement successful, False otherwise.
    
    Raises:
        MovementError: If movement fails or times out.
        ConnectionError: If device is not connected.
    
    Example:
        >>> ctrl.move_absolute(10.0, wait=True)
        True
        >>> ctrl.get_position()
        10.0
    """
```

---

## Testing Requirements

### All Changes Must Include Tests

| Change Type | Test Requirement |
|-------------|------------------|
| Bug fix | Test that reproduces the bug |
| New feature | Tests covering all use cases |
| New controller | Complete test suite (see template) |
| API change | Updated tests for changed behavior |

### Running Tests

```bash
# Run all tests (hardware required)
python -m Hardware.ThorlabsMotionControl.tests.run_all_tests

# Run specific device tests
python -m Hardware.ThorlabsMotionControl.tests.run_all_tests --type KDC

# List devices without testing
python -m Hardware.ThorlabsMotionControl.tests.run_all_tests --list
```

### Test Structure

Each test suite should follow this structure:

```python
class ControllerTestSuite:
    """Test suite for ControllerName."""
    
    def __init__(self, serial_number: int = None):
        self.ctrl = None
        self.serial = serial_number
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def run_all_tests(self):
        """Run complete test suite."""
        # Discovery tests
        # Connection tests
        # Functionality tests
        # Cleanup tests
```

### Test Categories

Every controller test suite must include:

1. **Discovery** — Device can be found
2. **Connection** — Connect/disconnect works
3. **Identification** — LED blink works
4. **Status** — Status queries work
5. **Position** — Position reading works
6. **Movement** — Home, absolute, relative moves
7. **Parameters** — Get/set velocity, acceleration
8. **Stop** — Emergency stop works

---

## Pull Request Process

### Before Submitting

1. **Update from upstream**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks**
   ```bash
   black --check --line-length 100 .
   flake8 --max-line-length 100 .
   python -m Hardware.ThorlabsMotionControl.tests.run_all_tests
   ```

3. **Update documentation** if needed

### PR Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages are clear and descriptive
- [ ] No merge conflicts

### Commit Message Format

```
<type>: <short description>

<longer description if needed>

<issue reference if applicable>
```

Types:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `test:` — Test additions/changes
- `refactor:` — Code refactoring
- `style:` — Formatting changes

Example:
```
feat: Add KIM102 controller support

- Implement KIM102Controller class
- Add test suite with 25 tests
- Update device_manager for auto-detection

Closes #42
```

### Review Process

1. Create PR with clear description
2. Wait for CI checks to pass
3. Address reviewer feedback
4. Squash commits if requested
5. Merge after approval

---

## Adding New Controller Support

### Step 1: Research the Controller

1. Find Kinesis DLL name: `Thorlabs.MotionControl.<Type>CLI.dll`
2. Identify class name in DLL (e.g., `KCubeDCServo`)
3. Document serial number prefix
4. List compatible stages

### Step 2: Create Controller Class

Create `kinesis/<controller>.py`:

```python
"""
<CONTROLLER> <Description> - Kinesis Backend

Uses Thorlabs Kinesis .NET DLLs via pythonnet.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import MotorController, ControllerState, ConnectionError, MovementError

KINESIS_PATH = Path(r"C:\Program Files\Thorlabs\Kinesis")


class <Controller>Controller(MotorController):
    """
    <Controller> <Description>.
    
    Attributes:
        serial_number: Device serial number.
        channel: Channel number (default 1).
    
    Example:
        >>> ctrl = <Controller>Controller(serial_number=12345678)
        >>> ctrl.connect()
        >>> ctrl.home(wait=True)
        >>> ctrl.move_absolute(10.0)
    """
    
    def __init__(self, serial_number: int, channel: int = 1):
        super().__init__(serial_number, channel)
        self._device = None
        self._is_initialized = False
    
    # Implement all abstract methods from MotorController
    # ...
```

### Step 3: Register Controller

Update `controllers.py`:

```python
CONTROLLER_TYPES = {
    # ... existing controllers ...
    '<CONTROLLER>': {
        'prefix': 'XX',  # Serial number prefix
        'channels': 1,
        'motor_type': 'dc_servo',  # or 'brushless', 'inertial', 'piezo'
        'description': '<Description>',
        'dll_name': 'Thorlabs.MotionControl.<Type>CLI',
        'class_name': '<ClassName>',
    },
}
```

### Step 4: Update Device Manager

Update `device_manager.py` to handle the new controller type.

### Step 5: Create Test Suite

Create `tests/test_<controller>.py` following existing test patterns.

### Step 6: Update Documentation

1. Add to README.md supported hardware table
2. Add to tests/README.md test coverage table
3. Update `__init__.py` exports

---

## Documentation

### Where to Document

| Content | Location |
|---------|----------|
| Package overview | `README.md` |
| API documentation | Docstrings in code |
| Testing guide | `tests/README.md` |
| Contributing guide | `CONTRIBUTING.md` |
| Module overview | Module docstrings |

### Documentation Style

- Use Markdown for all `.md` files
- Include code examples where helpful
- Keep language clear and concise
- Update docs with code changes

### Building Documentation

```bash
# Generate API docs (if using Sphinx)
cd docs
make html
```

---

## Questions?

- Open an issue for bugs or feature requests
- Tag maintainers for urgent issues
- Check existing issues before creating new ones

Thank you for contributing! 🎉
