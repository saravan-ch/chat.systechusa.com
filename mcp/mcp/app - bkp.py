import json
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters, get_default_environment
import boto3
import chainlit as cl
from chainlit.mcp import validate_mcp_command
from contextlib import AsyncExitStack

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-west-2",
    aws_access_key_id="",
    aws_secret_access_key=""
)

SYSTEM = "You are a WizarD Assistant and you should not reveal you as Claude or Anthropic's Model. Also, While generating and executing the SQL Queries, read the Maverick_Annotation_File.txt file using read_file tool for reference."

def flatten(xss):
    return [x for xs in xss for x in xs]

# Keep the original MCP connection handler for UI connections (if any)
@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
    result = await session.list_tools()
    tools = [{
        "name": t.name,
        "description": t.description,
        "input_schema": t.inputSchema,
    } for t in result.tools]
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = tools
    cl.user_session.set("mcp_tools", mcp_tools)

@cl.step(type="tool") 
async def call_tool(tool_use):
    tool_name = tool_use.name
    tool_input = tool_use.input
    current_step = cl.context.current_step
    current_step.name = tool_name
    # Identify which mcp is used
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_name = None
    for connection_name, tools in mcp_tools.items():
        if any(tool.get("name") == tool_name for tool in tools):
            mcp_name = connection_name
            break
    if not mcp_name:
        current_step.output = json.dumps({"error": f"Tool {tool_name} not found in any MCP connection"})
        return current_step.output
    mcp_session, _ = cl.context.session.mcp_sessions.get(mcp_name, (None, None))
    if not mcp_session:
        current_step.output = json.dumps({"error": f"MCP {mcp_name} not found in session"})
        return current_step.output
    try:
        current_step.output = await mcp_session.call_tool(tool_name, tool_input)
    except Exception as e:
        current_step.output = json.dumps({"error": str(e)})
    return current_step.output

async def call_claude(chat_messages):
    msg = cl.Message(content="")
    mcp_tools = cl.user_session.get("mcp_tools", {})
    # Flatten the tools from all MCP connections
    tools = flatten([tools for _, tools in mcp_tools.items()])
    
    # Format messages for Bedrock
    formatted_messages = []
    for message in chat_messages:
        formatted_messages.append({
            "role": message["role"],
            "content": message["content"]
        })
    
    # Prepare request body for Bedrock
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,  # Smaller value for faster responses
        "temperature": 0.7,  # Slightly lower temperature for faster responses
        "messages": formatted_messages,
        "system": SYSTEM
    }
    
    # Add tools if available
    if tools:
        request_body["tools"] = tools
    
    # Stream response from Bedrock
    try:
        response_stream = bedrock_runtime.invoke_model_with_response_stream(
            body=json.dumps(request_body),
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            contentType="application/json"
        )
        
        # Process streaming response
        response_body = {}
        for event in response_stream.get("body"):
            if "chunk" in event:
                chunk = json.loads(event["chunk"]["bytes"].decode())
                
                # Update response body with new data
                if not response_body:
                    response_body = chunk
                else:
                    # Handle delta updates
                    if "delta" in chunk and "text" in chunk["delta"]:
                        # Stream token to UI
                        await msg.stream_token(chunk["delta"]["text"])
                        
                        # Update content if needed
                        if "content" in response_body and isinstance(response_body["content"], list):
                            for block in response_body["content"]:
                                if block.get("type") == "text":
                                    block["text"] = block.get("text", "") + chunk["delta"]["text"]
        
        await msg.send()
        
        # Return complete response for tool handling
        return response_body
    
    except Exception as e:
        print(f"Error calling Claude via Bedrock: {str(e)}")
        await msg.update(content=f"Error: {str(e)}")
        return {"stop_reason": "error", "content": [{"type": "text", "text": str(e)}]}

@cl.on_chat_start
async def start_chat():
    cl.user_session.set("chat_messages", [])
    cl.user_session.set("mcp_tools", {})  # Initialize the mcp_tools dict
    # Define the MCP connections we want to automatically establish
    mcp_connections = [
        {
            "name": "mssql_server2",
            "command": "uv  --directory C:\\Users\\mcp_user\\mssql_mcp_server run C:\\Users\\mcp_user\\mssql_mcp_server\\src\\mssql_mcp_server\\server.py",
            "type": "stdio"
        },
        {
            "name": "filesystem1",
            "command": "uv run --directory C:\\Users\\mcp_user\\mcp-filesystem-python mcp-filesystem-python C:\\Users\\mcp_user\\OneDrive\\Documents\\Test",
            "type": "stdio"
        },
        {
            "name": "code_executor1",
            "command": "CODE_STORAGE_DIR=C:\\Users\\mcp_user\\code_storage CONDA_ENV_NAME=my_env node C:\\Users\\mcp_user\\mcp_code_executor\\build\\index.js",
            "type": "stdio"
        }
    ]
    
    # Connect to each MCP server in parallel
    connection_tasks = []
    for connection in mcp_connections:
        if connection["type"] == "stdio":
            connection_tasks.append(connect_to_mcp(connection))
    
    # Wait for all connections to be established
    await asyncio.gather(*connection_tasks, return_exceptions=True)

async def connect_to_mcp(connection):
    try:
        # Validate and prepare command
        env_vars, command, args = validate_mcp_command(connection["command"])
        # Create environment for the process
        process_env = get_default_environment()
        process_env.update(env_vars)
        # Create server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=process_env
        )
        # Use AsyncExitStack to manage the async context managers
        exit_stack = AsyncExitStack()
        # Create the transport
        transport = await exit_stack.enter_async_context(stdio_client(server_params))
        read, write = transport
        # Create and initialize the session
        mcp_session = await exit_stack.enter_async_context(
            ClientSession(read_stream=read, write_stream=write)
        )
        # Initialize the session
        await mcp_session.initialize()
        # Store the session and exit_stack
        cl.context.session.mcp_sessions[connection["name"]] = (mcp_session, exit_stack)
        # Get tools and store them
        result = await mcp_session.list_tools()
        tools = [{
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema,
        } for t in result.tools]
        mcp_tools = cl.user_session.get("mcp_tools", {})
        mcp_tools[connection["name"]] = tools
        cl.user_session.set("mcp_tools", mcp_tools)
    except Exception as e:
        # Log the error to console but don't show in the chat
        print(f"Failed to connect to MCP {connection['name']}: {str(e)}")

@cl.on_chat_end
async def end_chat():
    # Clean up MCP sessions when the chat ends
    try:
        close_tasks = []
        for name, (session, exit_stack) in cl.context.session.mcp_sessions.items():
            if exit_stack:
                close_tasks.append(exit_stack.aclose())
        
        # Close all connections in parallel
        await asyncio.gather(*close_tasks, return_exceptions=True)
    except Exception as e:
        print(f"Error during MCP cleanup: {e}")

@cl.on_message
async def on_message(msg: cl.Message):   
    chat_messages = cl.user_session.get("chat_messages")
    chat_messages.append({"role": "user", "content": msg.content})
    response = await call_claude(chat_messages)
    
    # Handle tool usage
    while response.get("stop_reason") == "tool_use":
        tool_use = next((block for block in response.get("content", []) if block.get("type") == "tool_use"), None)
        if not tool_use:
            break
            
        tool_result = await call_tool(tool_use)
        messages = [
            {"role": "assistant", "content": response.get("content", [])},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.get("id"),
                        "content": str(tool_result),
                    }
                ],
            },
        ]
        chat_messages.extend(messages)
        response = await call_claude(chat_messages)
    
    # Extract final text content
    text_content = ""
    for block in response.get("content", []):
        if block.get("type") == "text":
            text_content += block.get("text", "")
    
    chat_messages.append({"role": "assistant", "content": text_content})
    cl.user_session.set("chat_messages", chat_messages)