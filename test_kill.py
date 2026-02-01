#!/usr/bin/env python3
import pyodbc

conn = pyodbc.connect(
    'Driver={ODBC Driver 18 for SQL Server};'
    'Server=localhost,1433;'
    'Database=DBMonTest;'
    'UID=sa;'
    'PWD=YourStrong!Passw0rd;'
    'TrustServerCertificate=yes;',
    timeout=10,
    autocommit=True  # KILL must run outside transactions
)

session_id = 53  # Test with session 53

print(f'Attempting to kill session {session_id}...')

try:
    cursor = conn.cursor()
    cursor.execute(f"KILL {session_id}")
    print(f'✅ Session {session_id} killed successfully')
except Exception as e:
    print(f'❌ Error: {e}')

conn.close()
