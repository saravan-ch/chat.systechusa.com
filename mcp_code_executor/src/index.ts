#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { randomBytes } from 'crypto';
import { join } from 'path';
import { mkdir, writeFile } from 'fs/promises';
import { exec, ExecOptions } from 'child_process';
import { promisify } from 'util';
import { platform } from 'os';

// Environment variables
const CODE_STORAGE_DIR = process.env.CODE_STORAGE_DIR;
const CONDA_ENV_NAME = process.env.CONDA_ENV_NAME;

if (!CODE_STORAGE_DIR || !CONDA_ENV_NAME) {
    throw new Error('Missing required environment variables: CODE_STORAGE_DIR and CONDA_ENV_NAME');
}

// Ensure storage directory exists
await mkdir(CODE_STORAGE_DIR, { recursive: true });

const execAsync = promisify(exec);

/**
 * Get platform-specific command for Conda activation
 */
function getPlatformSpecificCommand(pythonCommand: string): { command: string, options: ExecOptions } {
    const isWindows = platform() === 'win32';
    
    if (isWindows) {
        return {
            command: `conda run -n ${CONDA_ENV_NAME} ${pythonCommand}`,
            options: {
                shell: 'cmd.exe'
            }
        };
    } else {
        return {
            command: `source $(conda info --base)/etc/profile.d/conda.sh && conda activate ${CONDA_ENV_NAME} && ${pythonCommand}`,
            options: {
                shell: '/bin/bash'
            }
        };
    }
}

/**
 * Execute Python code and return the result
 */
async function executeCode(code: string, filePath: string) {
    try {
        // Write code to file
        await writeFile(filePath, code, 'utf-8');

        // Get platform-specific command
        const pythonCmd = platform() === 'win32' ? `python "${filePath}"` : `python3 "${filePath}"`;
        const { command, options } = getPlatformSpecificCommand(pythonCmd);

        // Execute code
        const { stdout, stderr } = await execAsync(command, {
            cwd: CODE_STORAGE_DIR,
            env: { ...process.env },
            ...options
        });

        const response = {
            status: stderr ? 'error' : 'success',
            output: stderr || stdout,
            file_path: filePath
        };

        return {
            type: 'text',
            text: JSON.stringify(response),
            isError: !!stderr
        };
    } catch (error) {
        const response = {
            status: 'error',
            error: error instanceof Error ? error.message : String(error),
            file_path: filePath
        };

        return {
            type: 'text',
            text: JSON.stringify(response),
            isError: true
        };
    }
}

/**
 * Create an MCP server to handle code execution
 */
const server = new Server(
    {
        name: "code-executor",
        version: "0.1.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

/**
 * Handler for listing available tools.
 * Provides a tool to execute code in Python environment.
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "execute_code",
                description: "Execute Python code in the specified conda environment",
                inputSchema: {
                    type: "object",
                    properties: {
                        code: {
                            type: "string",
                            description: "Python code to execute"
                        },
                        filename: {
                            type: "string",
                            description: "Optional: Name of the file to save the code (default: generated UUID)"
                        }
                    },
                    required: ["code"]
                }
            }
        ]
    };
});

interface ExecuteCodeArgs {
    code?: string;
    filename?: string;
}

/**
 * Handler for the execute_code tool.
 * Executes code and returns the result.
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    switch (request.params.name) {
        case "execute_code": {
            const args = request.params.arguments as ExecuteCodeArgs;
            if (!args?.code) {
                throw new Error("Code is required");
            }

            const defaultFilename = `code_${randomBytes(4).toString('hex')}.py`;
            const userFilename = args.filename || defaultFilename;
            const filename = typeof userFilename === 'string' ? userFilename : defaultFilename;
            const filePath = join(CODE_STORAGE_DIR, filename.endsWith('.py') ? filename : `${filename}.py`);

            const result = await executeCode(args.code, filePath);

            return {
                content: [{
                    type: "text",
                    text: result.text,
                    isError: result.isError
                }]
            };
        }
        default:
            throw new Error("Unknown tool");
    }
});

/**
 * Start the server using stdio transport.
 */
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}

main().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
});