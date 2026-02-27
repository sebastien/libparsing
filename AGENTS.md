# AGENTS.md - Agent Guidelines for libparsing

This file provides guidelines for AI agents working on the libparsing codebase.

## Project Overview

**libparsing** is a PEG-based parsing library written in C with Python bindings (via CFFI). It allows dynamic grammar construction for creating parsers for programming languages and software engineering tools.

## Build Commands

```bash
# Build all products (C library, Python module)
make

# Build with specific features (pcre, fortify, gc, debug, trace, assert)
make FEATURES="debug assert"

# Run all tests
make tests

# Run C static analysis checks
make check

# Clean build files
make clean

# Create Python distribution
make dist

# Display project info
make info
```

### Running a Single Test

#### Python Tests
```bash
# Run a specific Python test file
python3 test/python-bindings.py

# Run a specific Python test file with pytest (if available)
pytest test/python-bindings.py -v

# Run a specific test function
python3 -c "from test.python_bindings import *; test_function_name()"
```

#### C Tests
```bash
# Compile and run a specific C test
# First build the library, then compile test against it
gcc -I src/h test/c-parser-expr.c -L dist -lparsing -o test_c_parser_expr
./test_c_parser_expr
```

### Development Setup

```bash
# Install Python dependencies
pip install cffi

# Build Python module in-place
python3 setup.py build_ext --inplace
```

## Code Style Guidelines

### General Principles

- Keep functions focused and small (< 100 lines preferred)
- Write self-documenting code with clear variable names
- Add comments for complex logic, not trivial operations
- Maintain Python 2/3 compatibility where possible

### C Code Style

**Formatting:**
- K&R-style braces (opening brace on same line)
- 4-space indentation
- Max line length: 120 characters
- Use ALL_CAPS for macros and constants

```c
// Good
#define MATCH_STATS(m) ParsingContext_registerMatch(context, (Element*)this, m)
#define INDENT_WIDTH  2

void FunctionName(Type* param) {
    if (condition) {
        doSomething();
    }
}

// Bad
void FunctionName(Type* param)
{
    if (condition)
    {
        doSomething();
    }
}
```

**Naming:**
- Functions: `snake_case` (e.g., `parsing_element_free`)
- Types: `PascalCase` (e.g., `ParsingElement`)
- Macros: `ALL_CAPS` (e.g., `WITH_PCRE`)
- Variables: `snake_case` (e.g., `result`, `match_offset`)

**Error Handling:**
- Use assertions for development (`assert()`)
- Return NULL on failure for functions returning pointers
- Set errno where appropriate
- Use status codes for parsing results

**Memory Management:**
- Follow consistent allocation/deallocation patterns
- Use the GC (garbage collection) feature when available
- Clear pointers after freeing

### Python Code Style

**Formatting:**
- 4-space indentation (no tabs)
- Max line length: 120 characters
- Two blank lines between top-level definitions

```python
# Good
def function_name(param_one, param_two):
    """Short description.
    
    Longer description if needed.
    """
    if condition:
        result = do_something()
    return result

class ClassName:
    """Docstring for class."""
    
    CONSTANT_VALUE = 42
    
    def method_name(self):
        pass

# Bad
def function_name(param_one,param_two):
    result=do_something()
    return result
```

**Imports:**
- Group in this order: stdlib, third-party, local
- Sort alphabetically within each group
- Use explicit imports

```python
import os
import sys
import re

from cffi import FFI
from os.path import dirname, join, abspath

from . import _buildext
from .module import Something
```

**Naming:**
- Classes: `PascalCase` (e.g., `Grammar`, `ParsingElement`)
- Functions/methods: `camelCase` for methods, `snake_case` for standalone
- Variables: `snake_case` (e.g., `parsing_result`, `match_offset`)
- Constants: `ALL_CAPS` (e.g., `VERSION`, `STATUS_MATCHED`)

**Type Hints:**
- Use type hints for new code (Python 3.5+)
- Be consistent with existing patterns

```python
def parse_string(self, text: str) -> ParsingResult:
    ...
```

**Error Handling:**
- Use exceptions for errors, not return codes
- Provide meaningful error messages
- Catch specific exceptions, not bare `Exception`

```python
# Good
try:
    result = parser.parse(text)
except ValueError as e:
    raise ValueError(f"Failed to parse: {e}") from e

# Bad
try:
    result = parser.parse(text)
except:
    print("Error")
```

## Project Structure

```
src/
├── c/          # C source files
│   ├── parsing.c
│   └── gc.c
├── h/          # C header files
│   ├── parsing.h
│   ├── gc.h
│   ├── oo.h
│   └── testing.h
└── python/     # Python bindings
    └── libparsing/
        ├── __init__.py
        └── _buildext.py

test/
├── c-*.c       # C tests
└── python-*.py # Python tests
```

## Common Patterns

### Adding a New C Function

1. Declare in header file (`src/h/parsing.h`)
2. Implement in source file (`src/c/parsing.c`)
3. Export in FFI definition if Python binding needed
4. Add wrapper in Python (`src/python/libparsing/__init__.py`)

### Adding a New Test

1. C tests: Create `test/c-testname.c`
2. Python tests: Create `test/python-testname.py`
3. Ensure test can be run individually

### Working with Grammars

```python
from libparsing import Grammar

g = Grammar()
s = g.symbols
g.token("WS", r"\s+")
g.token("NUMBER", r"\d+")
g.rule("Value", s.NUMBER)
g.axiom(s.Value)
result = g.parseString("42")
```

## Testing Notes

- Tests use both C and Python
- C tests are compiled against the built shared library
- Python tests use CFFI to interface with C code
- The `make tests` target runs all available tests

## Version Management

- Version defined in `src/h/parsing.h` as `VERSION`
- Also updated in `setup.py` and `src/python/libparsing/__init__.py`
- Use `make update-python-version` to sync versions

## Troubleshooting

**Build fails:**
- Ensure `gcc` and `python3` are available
- Check that `cffi` is installed: `pip install cffi`
- Try `make clean && make`

**Python import fails:**
- Rebuild extensions: `python3 setup.py build_ext --inplace`
- Check that `_libparsing.so` exists in `src/python/libparsing/`

**Tests fail:**
- Ensure library is built: `make`
- Check for missing dependencies
- Run with verbose output for debugging
