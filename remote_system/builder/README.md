# Enhanced Builder

The Enhanced Builder creates production-ready agent executables with embedded configuration, custom icons, metadata, and security features.

## Features

- **Unique Secret_Key Generation**: Each build generates a cryptographically secure 64-character secret key for server binding
- **Embedded Configuration**: Server IP, port, token, and Secret_Key are hardcoded into the agent
- **Custom Icons**: Embed custom .ico files for professional appearance
- **Executable Metadata**: Set company name, version, and copyright information
- **Multiple Output Formats**: Generate both .bat and .exe files
- **Silent Mode**: Run agents without console windows (--noconsole)
- **Code Obfuscation**: Optional PyArmor integration for code protection
- **Anti-Debugging**: Optional anti-debugging features to prevent analysis

## Requirements

### Basic Requirements
- Python 3.7+
- secrets module (standard library)

### For .exe Generation
- PyInstaller: `pip install pyinstaller`

### Optional
- PyArmor: `pip install pyarmor` (for code obfuscation)

## Usage

### Command-Line Interface

#### Basic Build
```bash
python enhanced_builder.py \
  --server-ip 192.168.1.100 \
  --server-port 9999 \
  --token mytoken123
```

#### Build with Custom Icon and Metadata
```bash
python enhanced_builder.py \
  --server-ip 192.168.1.100 \
  --server-port 9999 \
  --token mytoken123 \
  --icon myicon.ico \
  --company "My Company" \
  --version "1.0.0.0" \
  --copyright "Copyright 2024 My Company"
```

#### Build Silent Agent (No Console)
```bash
python enhanced_builder.py \
  --server-ip 192.168.1.100 \
  --server-port 9999 \
  --token mytoken123 \
  --silent
```

#### Build Only .exe Format
```bash
python enhanced_builder.py \
  --server-ip 192.168.1.100 \
  --server-port 9999 \
  --token mytoken123 \
  --format exe
```

#### Build with Security Features
```bash
python enhanced_builder.py \
  --server-ip 192.168.1.100 \
  --server-port 9999 \
  --token mytoken123 \
  --anti-debug \
  --obfuscate
```

### Python API

```python
from enhanced_builder import EnhancedBuilder

# Create builder
builder = EnhancedBuilder(
    server_ip="192.168.1.100",
    server_port=9999,
    token="mytoken123",
    output_dir="./output",
    icon_file="myicon.ico",
    company="My Company",
    version="1.0.0.0",
    copyright_text="Copyright 2024",
    silent=True,
    anti_debug=True
)

# Build agent
results = builder.build(formats=["bat", "exe"])

if results["success"]:
    print(f"Secret Key: {results['secret_key']}")
    print(f"Output files: {results['outputs']}")
else:
    print(f"Errors: {results['errors']}")
```

## Output

The builder generates files in the output directory (default: `remote_system/output/`):

- `enhanced_agent.bat` - Batch file launcher
- `enhanced_agent.exe` - Standalone executable (if PyInstaller is available)
- `agent_customized.py` - Customized agent script with embedded configuration

## Secret Key

Each build generates a unique 64-character hexadecimal Secret_Key. This key is:

- **Cryptographically secure**: Generated using Python's `secrets` module
- **Unique per build**: Each build gets a different key
- **Embedded in agent**: Hardcoded into the agent executable
- **Used for server binding**: Ensures agents only connect to authorized servers

**IMPORTANT**: Save the Secret_Key displayed after building. You'll need it to configure the server to accept connections from this agent.

Example output:
```
[BUILD COMPLETE]
Secret Key: a1b2c3d4e5f6...
Output Directory: remote_system/output/
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server-ip` | Server IP address or hostname | Required |
| `--server-port` | Server port number | Required |
| `--token` | JWT authentication token | Required |
| `--output-dir` | Output directory path | `remote_system/output/` |
| `--icon` | Path to .ico file | None |
| `--company` | Company name for metadata | "Remote System" |
| `--version` | Version string (e.g., 1.0.0.0) | "1.0.0.0" |
| `--copyright` | Copyright text | "Copyright (c) {company}" |
| `--silent` | Run without console window | False |
| `--obfuscate` | Use PyArmor obfuscation | False |
| `--anti-debug` | Enable anti-debugging | False |
| `--format` | Output format (bat, exe, both) | both |

## Examples

### Example 1: Development Build
Quick build for testing:
```bash
python enhanced_builder.py \
  --server-ip localhost \
  --server-port 9999 \
  --token dev_token \
  --format bat
```

### Example 2: Production Build
Full production build with all features:
```bash
python enhanced_builder.py \
  --server-ip production.example.com \
  --server-port 8443 \
  --token prod_token_secure_123 \
  --icon company_logo.ico \
  --company "ACME Corporation" \
  --version "2.1.0.0" \
  --copyright "Copyright 2024 ACME Corporation" \
  --silent \
  --anti-debug \
  --format exe
```

### Example 3: Internet Deployment
Build for internet-accessible server:
```bash
python enhanced_builder.py \
  --server-ip 203.0.113.42 \
  --server-port 443 \
  --token internet_token_xyz \
  --silent \
  --format exe
```

## Testing

Run the test suite:
```bash
python -m pytest test_enhanced_builder.py -v
```

Run the demo:
```bash
python demo_builder.py
```

## Architecture

The builder follows this workflow:

1. **Initialize**: Validate parameters and generate Secret_Key
2. **Customize Agent**: Create agent script with embedded configuration
3. **Build .bat**: Generate batch file launcher
4. **Build .exe**: Use PyInstaller to create standalone executable
5. **Add Metadata**: Embed icon and version information
6. **Cleanup**: Remove temporary build artifacts

## Security Considerations

### Secret Key Security
- Each agent has a unique Secret_Key
- Keys are 256-bit (64 hex characters) for strong security
- Keys are embedded at build time, not runtime
- Server must validate Secret_Key before accepting connections

### Anti-Debugging
When enabled, the agent will:
- Check for debugger attachment using `sys.gettrace()`
- Check Windows debugger presence using `IsDebuggerPresent()`
- Exit immediately if debugger is detected

### Code Obfuscation
When enabled with PyArmor:
- Python bytecode is encrypted
- Source code is protected from decompilation
- Runtime decryption prevents static analysis

## Troubleshooting

### PyInstaller Not Found
```
Error: PyInstaller is not installed
Solution: pip install pyinstaller
```

### Icon File Not Found
```
Error: Icon file not found
Solution: Verify icon path is correct and file exists
```

### Build Directory Permissions
```
Error: Permission denied
Solution: Ensure write permissions for output directory
```

### Import Errors in Built .exe
```
Error: Module not found in executable
Solution: Add hidden imports using --hidden-import flag
```

## Requirements Mapping

This implementation satisfies the following requirements:

- **6.1**: Accept server IP and port as required parameters
- **6.2**: Support embedding custom icon files
- **6.3**: Allow setting executable metadata (company, version, copyright)
- **6.4**: Generate both .bat and .exe output formats
- **6.5**: Support silent mode (no console window)
- **6.6**: Embed unique Secret_Key for server binding
- **6.7**: Output to configured directory
- **9.1**: Embed server IP and port as hardcoded values
- **9.2**: Embed unique Secret_Key known only to authorized server
- **10.6**: Support code obfuscation using PyArmor
- **10.7**: Support anti-debugging features

## License

Part of the Remote System Enhancement project.
