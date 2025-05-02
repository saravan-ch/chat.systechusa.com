# MCP Filesystem Python

A Model Context Protocol (MCP) server that provides secure, read-only access to files in a specified directory.

## Features

- Exposes files as MCP resources using \`file://\` URI scheme
- Provides file search capabilities through MCP tools
- Respects .gitignore patterns
- Security features including path traversal protection
- MIME type detection

## Installation

Using UV:

```bash
uv add mcp-filesystem-python
```

## Usage

Run the server:

```bash
uv run src/filesystem/server.py /path/to/directory
```

## Claude Desktop Integration

### Configuration Examples

Example configurations for Claude Desktop can be found in the \`examples\` directory:

- \`examples/claude_desktop_config.json\`: Example for macOS/Linux
- \`examples/claude_desktop_config_windows.json\`: Example for Windows

These files should be placed at:
- macOS: \`~/Library/Application Support/Claude/claude_desktop_config.json\`
- Windows: \`%AppData%\\Claude\\claude_desktop_config.json\`

Make sure to:
1. Replace the paths with your actual paths
2. Use forward slashes (\`/\`) for macOS/Linux and backslashes (\`\\\\\`) for Windows
3. Use absolute paths (not relative paths)

## Development

1. Clone the repository
2. Create virtual environment and sync requirements, ```uv sync```

## License

[MIT](LICENSE)
