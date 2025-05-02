# MCP Code Executor
[![smithery badge](https://smithery.ai/badge/@bazinga012/mcp_code_executor)](https://smithery.ai/server/@bazinga012/mcp_code_executor)

The MCP Code Executor is an MCP server that allows LLMs to execute Python code within a specified Conda environment. This enables LLMs to run code with access to libraries and dependencies defined in the Conda environment.

<a href="https://glama.ai/mcp/servers/45ix8xode3"><img width="380" height="200" src="https://glama.ai/mcp/servers/45ix8xode3/badge" alt="Code Executor MCP server" /></a>

## Features

- Execute Python code from LLM prompts
- Run code within a specified Conda environment 
- Configurable code storage directory

## Prerequisites

- Node.js installed
- Conda installed
- Desired Conda environment created

## Setup

1. Clone this repository:

```bash
git clone https://github.com/bazinga012/mcp_code_executor.git
```

2. Navigate to the project directory:

```bash 
cd mcp_code_executor
```

3. Install the Node.js dependencies:

```bash
npm install
```

4. Build the project:

```bash
npm run build
```

## Configuration

To configure the MCP Code Executor server, add the following to your MCP servers configuration file:

```json
{
  "mcpServers": {
    "mcp-code-executor": {
      "command": "node",
      "args": [
        "/path/to/mcp_code_executor/build/index.js" 
      ],
      "env": {
        "CODE_STORAGE_DIR": "/path/to/code/storage",
        "CONDA_ENV_NAME": "your-conda-env"
      }
    }
  }
}
```

Replace the placeholders:
- `/path/to/mcp_code_executor` with the absolute path to where you cloned this repository 
- `/path/to/code/storage` with the directory where you want the generated code to be stored
- `your-conda-env` with the name of the Conda environment you want the code to run in

## Usage

Once configured, the MCP Code Executor will allow LLMs to execute Python code by generating a file in the specified `CODE_STORAGE_DIR` and running it within the Conda environment defined by `CONDA_ENV_NAME`.

LLMs can generate and execute code by referencing this MCP server in their prompts.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.

