import asyncio
import logging
import os
import pyodbc
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mssql_mcp_server")

def get_db_config():
    """Get database configuration from environment variables."""
    config = {
        "server": os.getenv("MSSQL_SERVER", "shwnyf7mmzfuzkmii43jjx2unq-3to45ygmr6qu7f5bfnsxdntvqy.datawarehouse.fabric.microsoft.com"),
        "user": os.getenv("MSSQL_USER", "saravananc@systechusa.com"),
        "password": os.getenv("MSSQL_PASSWORD", "Sol1@mcp"),
        "database": os.getenv("MSSQL_DATABASE", "gaming_warehouse")
    }
    
    if not all([config["user"], config["password"], config["database"]]):
        logger.error("Missing required database configuration. Please check environment variables:")
        logger.error("MSSQL_USER, MSSQL_PASSWORD, and MSSQL_DATABASE are required")
        raise ValueError("Missing required database configuration")
    
    return config

def get_connection():
    """Create a pyodbc connection using ActiveDirectoryPassword authentication."""
    config = get_db_config()
    conn_str = f"""
        DRIVER={{ODBC Driver 17 for SQL Server}};
        SERVER={config["server"]};
        DATABASE={config["database"]};
        UID={config["user"]};
        PWD={config["password"]};
        Authentication=ActiveDirectoryPassword;
    """
    
    try:
        conn = pyodbc.connect(conn_str)
        logger.info(f"Successfully connected to {config['server']}/{config['database']}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise

# Initialize server
app = Server("mssql_mcp_server")

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List SQL Server tables as resources."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Query to get user tables from the current database
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        tables = cursor.fetchall()
        logger.info(f"Found tables: {tables}")
        
        resources = []
        for table in tables:
            resources.append(
                Resource(
                    uri=f"mssql://{table[0]}/data",
                    name=f"Table: {table[0]}",
                    mimeType="text/plain",
                    description=f"Data in table: {table[0]}"
                )
            )
        cursor.close()
        conn.close()
        return resources
    except Exception as e:
        logger.error(f"Failed to list resources: {str(e)}")
        return []

@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read table contents."""
    uri_str = str(uri)
    logger.info(f"Reading resource: {uri_str}")
    
    if not uri_str.startswith("mssql://"):
        raise ValueError(f"Invalid URI scheme: {uri_str}")
        
    parts = uri_str[8:].split('/')
    table = parts[0]
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Use TOP 100 for MSSQL (equivalent to LIMIT in MySQL)
        cursor.execute(f"SELECT TOP 100 * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        result = [",".join(map(str, row)) for row in rows]
        cursor.close()
        conn.close()
        return "\n".join([",".join(columns)] + result)
                
    except Exception as e:
        logger.error(f"Database error reading resource {uri}: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available SQL Server tools."""
    logger.info("Listing tools...")
    return [
        Tool(
            name="WizarD_Analyst",
            description="Execute an SQL query on the SQL Server",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to execute"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute SQL commands."""
    logger.info(f"Calling tool: {name} with arguments: {arguments}")
    
    if name != "WizarD_Analyst":
        raise ValueError(f"Unknown tool: {name}")
    
    query = arguments.get("query")
    if not query:
        raise ValueError("Query is required")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Special handling for table listing
        if query.strip().upper().startswith("SELECT") and "INFORMATION_SCHEMA.TABLES" in query.upper():
            tables = cursor.fetchall()
            config = get_db_config()
            result = ["Tables_in_" + config["database"]]  # Header
            result.extend([table[0] for table in tables])
            cursor.close()
            conn.close()
            return [TextContent(type="text", text="\n".join(result))]
        
        # Regular SELECT queries
        elif query.strip().upper().startswith("SELECT"):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [",".join(map(str, row)) for row in rows]
            cursor.close()
            conn.close()
            return [TextContent(type="text", text="\n".join([",".join(columns)] + result))]
        
        # Non-SELECT queries
        else:
            conn.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            conn.close()
            return [TextContent(type="text", text=f"Query executed successfully. Rows affected: {affected_rows}")]
                
    except Exception as e:
        logger.error(f"Error executing SQL '{query}': {e}")
        return [TextContent(type="text", text=f"Error executing query: {str(e)}")]

async def main():
    """Main entry point to run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    logger.info("Starting MSSQL MCP server...")
    config = get_db_config()
    logger.info(f"Database config: {config['server']}/{config['database']} as {config['user']}")
    
    # Test connection on startup
    try:
        conn = get_connection()
        conn.close()
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
    
    async with stdio_server() as (read_stream, write_stream):
        try:
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
        except Exception as e:
            logger.error(f"Server error: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    asyncio.run(main())