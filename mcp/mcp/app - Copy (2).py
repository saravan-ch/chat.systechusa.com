import json
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters, get_default_environment
import anthropic
import chainlit as cl
from chainlit.mcp import validate_mcp_command
from contextlib import AsyncExitStack
 
anthropic_client = anthropic.AsyncAnthropic()
SYSTEM = "You are a WizarD Assistant and you should not reveal you as Claude or Anthropic's Model."
 
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
    async with anthropic_client.messages.stream(
        system=SYSTEM,
        max_tokens=64000,
        messages=chat_messages,
        tools=tools,
        model="claude-3-7-sonnet-20250219",
    ) as stream:
        async for text in stream.text_stream:
            await msg.stream_token(text)
    await msg.send()
    response = await stream.get_final_message()
    return response
 
@cl.on_chat_start
async def start_chat():
    cl.user_session.set("chat_messages", [])
    cl.user_session.set("mcp_tools", {})  # Initialize the mcp_tools dict
    # Define the MCP connections we want to automatically establish
    mcp_connections = [
        {
            "name": "mssql_server",
            "command": "uvx --directory C:\\Users\\mcp_user\\mssql_mcp_server mssql_mcp_server",
            "type": "stdio"
        },
        {
            "name": "filesystem",
            "command": "uv run --directory C:\\Users\\mcp_user\\mcp-filesystem-python mcp-filesystem-python C:\\Users\\mcp_user\\OneDrive\\Documents\\Test",
            "type": "stdio"
        }
    ]
    # Connect to each MCP server
    for connection in mcp_connections:
        try:
            if connection["type"] == "stdio":
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
                await cl.Message(content=f"✅ Connected to MCP: {connection['name']}").send()
        except Exception as e:
            await cl.Message(content=f"❌ Failed to connect to MCP {connection['name']}: {str(e)}").send()
 
@cl.on_chat_end
async def end_chat():
    # Clean up MCP sessions when the chat ends
    try:
        for name, (session, exit_stack) in cl.context.session.mcp_sessions.items():
            try:
                if exit_stack:
                    await exit_stack.aclose()
            except Exception as e:
                print(f"Error closing MCP session {name}: {e}")
    except Exception as e:
        print(f"Error during MCP cleanup: {e}")
 
@cl.on_message
async def on_message(msg: cl.Message):   
    chat_messages = cl.user_session.get("chat_messages")
    chat_messages.append({"role": "user", "content": msg.content})
    response = await call_claude(chat_messages)
    while response.stop_reason == "tool_use":
        tool_use = next(block for block in response.content if block.type == "tool_use")
        tool_result = await call_tool(tool_use)
        messages = [
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": str(tool_result),
                    }
                ],
            },
        ]
        chat_messages.extend(messages)
        response = await call_claude(chat_messages)
    final_response = next(
        (block.text for block in response.content if hasattr(block, "text")),
        None,
    )
    chat_messages = cl.user_session.get("chat_messages")
    chat_messages.append({"role": "assistant", "content": final_response})