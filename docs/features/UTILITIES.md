# Blender GraphQL MCP Utility Modules

This documentation provides an overview of the utility modules available in the Blender GraphQL MCP addon. These modules provide robust file handling, error management, and asynchronous operations to support the GraphQL API functionality.

## Available Utility Modules

The Blender GraphQL MCP includes the following utility modules:

### 1. File Utilities (`fileutils.py`)

A comprehensive module for file and path handling operations with enhanced cross-platform compatibility and robust error handling.

#### Key Features:

- **Path Normalization and Manipulation**
  - `normalize_path()`: Standardizes path formats across platforms
  - `is_absolute_path()`: Validates absolute paths (with UNC path support)
  - `join_paths()`: Safely combines path segments
  - `get_file_extension()`, `get_filename()`, `get_directory()`: Path component extraction
  - `get_relative_path()`, `resolve_path()`: Path conversion utilities
  - `is_path_within()`: Safely check if a path is within a parent directory

- **Safe File Operations**
  - `ensure_directory()`: Creates directories with proper error handling
  - `safe_delete()`: Safely removes files with protection against critical paths
  - `safe_copy()`, `safe_move()`: Atomic file operations
  - `get_file_info()`: Retrieves comprehensive file metadata
  - `list_files()`, `find_files_by_extension()`: File search utilities

- **Content Operations**
  - `safe_read_file()`, `safe_write_file()`: Error-handled file I/O
  - `safe_read_json()`, `safe_write_json()`: JSON file operations
  - `atomic_write_file()`: Context manager for atomic file writes

- **Resource Management**
  - `create_temp_directory()`, `create_temp_file()`: Temporary resource creation
  - `temp_directory()`: Context manager for temporary directories
  - `get_cache_path()`, `clear_cache()`: Cache management utilities

### 2. UI Error Handler (`ui_error_handler.py`)

A module for displaying error messages in the Blender UI with proper styling and consistent formatting.

#### Key Features:

- **Error Display**
  - `display_error_message()`: Shows error messages to the user via the Blender UI
  - `show_error_dialog()`: Creates detailed error dialogs with context information
  - `show_error_report_panel()`: Generates comprehensive error reports

- **Error Management**
  - Error severity levels (INFO, WARNING, ERROR, CRITICAL)
  - Error logging with detailed context preservation
  - Error categorization and appropriate response formatting

- **UI Integration**
  - Custom Blender operators for error reporting
  - Error log file access integration
  - Context-specific error visualization

### 3. Asynchronous File Handler (`async_file_handler.py`)

A module for performing file operations asynchronously without blocking the Blender UI.

#### Key Features:

- **Task Management**
  - Thread pool for managing concurrent file operations
  - Task queuing and prioritization
  - Timeout and cancellation support

- **Asynchronous Operations**
  - Async reading and writing of files and JSON data
  - Async file copying, moving, and deletion
  - Async directory creation and file listing
  - Callback-based completion notification

- **Monitoring and Control**
  - Task status tracking (pending, running, success, failure, timeout)
  - Active task listing and statistics
  - Task result and error reporting

## Usage Examples

### Basic File Operations

```python
from utils import fileutils

# Normalize a path for the current platform
path = fileutils.normalize_path("/some/path/to/file.txt")

# Create a directory safely
fileutils.ensure_directory("/path/to/new/directory")

# Safe file operations
fileutils.safe_write_file("/path/to/file.txt", "File content here")
content = fileutils.safe_read_file("/path/to/file.txt")

# JSON operations
data = {"name": "Example", "values": [1, 2, 3]}
fileutils.safe_write_json("/path/to/data.json", data)
```

### Error Handling in the UI

```python
from utils import ui_error_handler
from utils.ui_error_handler import ErrorSeverity

# Simple error message display
ui_error_handler.display_error_message(
    "Operation Failed", 
    "Could not complete the requested operation.",
    ErrorSeverity.ERROR
)

# Detailed error dialog with context
try:
    # Some operation that might fail
    result = perform_risky_operation()
except Exception as e:
    error_log_file = ui_error_handler.show_error_dialog(
        "Processing Error",
        "Failed to process the operation.",
        e,
        {"context": "user_operation", "input_data": input_value}
    )
```

### Asynchronous File Operations

```python
from utils import async_file_handler

# Callback function for when operation completes
def on_file_read(task):
    if task.status == async_file_handler.OperationStatus.SUCCESS:
        print(f"File content: {task.result}")
    else:
        print(f"Error reading file: {task.error}")

# Start a background file read operation
task_id = async_file_handler.read_file_async(
    file_path="/path/to/large/file.txt",
    callback=on_file_read
)

# Write a file asynchronously
def on_write_complete(task):
    print(f"File write complete: {task.status.value}")

write_task_id = async_file_handler.write_file_async(
    file_path="/path/to/output.txt",
    content="Large content to write...",
    callback=on_write_complete
)

# Check task status
manager = async_file_handler.AsyncFileManager.get_instance()
status = manager.get_task_status(task_id)
```

## Integration with the Blender GraphQL MCP

These utility modules are designed to enhance the reliability and performance of the Blender GraphQL MCP addon by providing:

1. **Robust File Operations**: Ensuring file operations are secure, atomic, and error-handled
2. **User-Friendly Error Reporting**: Providing clear, contextual error messages to users
3. **Non-Blocking Operations**: Allowing large file operations to run in the background 

The modules automatically handle their own registration with Blender when the addon is enabled.

## Demo and Testing

A demo module (`demo_utils.py`) is provided to showcase the functionality of these utilities:

```python
from utils import demo_utils

# Run all demos
demo_utils.run_all_demos()

# Or run specific demos
demo_utils.demo_file_utils()
demo_utils.demo_ui_error_handler()
demo_utils.demo_async_file_handler()
```

Within Blender, you can also run the demo via the operator:
```
bpy.ops.mcp.run_utils_demo()
```