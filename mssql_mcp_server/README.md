# Microsoft SQL Server MCP Server

A Model Context Protocol (MCP) server that enables secure interaction with Microsoft SQL Server databases. This server allows AI assistants to list tables, read data, and execute SQL queries through a controlled interface, making database exploration and analysis safer and more structured.

## Features

- List available SQL Server tables as resources
- Read table contents
- Execute SQL queries with proper error handling
- Secure database access through environment variables
- Comprehensive logging
- Automatic system dependency installation

## Installation

The package will automatically install required system dependencies (like FreeTDS) when installed through MCP:

```bash
pip install mssql-mcp-server
```

## Configuration

Set the following environment variables:

```bash
MSSQL_SERVER=localhost
MSSQL_USER=your_username
MSSQL_PASSWORD=your_password
MSSQL_DATABASE=your_database
```

## Usage

### With Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mssql": {
      "command": "uv",
      "args": [
        "--directory", 
        "path/to/mssql_mcp_server",
        "run",
        "mssql_mcp_server"
      ],
      "env": {
        "MSSQL_SERVER": "localhost",
        "MSSQL_USER": "your_username",
        "MSSQL_PASSWORD": "your_password",
        "MSSQL_DATABASE": "your_database"
      }
    }
  }
}
```

### As a standalone server

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m mssql_mcp_server
```

## Development

```bash
# Clone the repository
git clone https://github.com/RichardHan/mssql_mcp_server.git
cd mssql_mcp_server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest
```

## Security Considerations

- Never commit environment variables or credentials
- Use a database user with minimal required permissions
- Consider implementing query whitelisting for production use
- Monitor and log all database operations

## Security Best Practices

This MCP server requires database access to function. For security:

1. **Create a dedicated SQL Server login** with minimal permissions
2. **Never use sa credentials** or administrative accounts
3. **Restrict database access** to only necessary operations
4. **Enable logging** for audit purposes
5. **Regular security reviews** of database access

See [SQL Server Security Configuration Guide](SECURITY.md) for detailed instructions on:
- Creating a restricted SQL Server login
- Setting appropriate permissions
- Monitoring database access
- Security best practices

⚠️ IMPORTANT: Always follow the principle of least privilege when configuring database access.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
