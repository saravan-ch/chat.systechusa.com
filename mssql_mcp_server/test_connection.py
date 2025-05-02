import pymssql

config = {
    "server": "{DB Server}}",
    "user": "{SQL account}}",
    "password": "{SQL password}",
    "database": "{DB Name}}"
}

try:
    print("Attempting to connect to SQL Server...")
    conn = pymssql.connect(**config)
    cursor = conn.cursor()
    print("Connection successful!")
    
    print("\nTesting query execution...")
    cursor.execute("SELECT TOP 1 * FROM INFORMATION_SCHEMA.TABLES")
    row = cursor.fetchone()
    print(f"Query result: {row}")
    
    cursor.close()
    conn.close()
    print("\nConnection test completed successfully!")
except Exception as e:
    print(f"Error: {str(e)}")
