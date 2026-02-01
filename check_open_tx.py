#!/usr/bin/env python3
import pyodbc

conn = pyodbc.connect(
    'Driver={ODBC Driver 18 for SQL Server};'
    'Server=localhost,1433;'
    'Database=DBMonTest;'
    'UID=sa;'
    'PWD=YourStrong!Passw0rd;'
    'TrustServerCertificate=yes;',
    timeout=10
)

cursor = conn.cursor()
cursor.execute('''
    SELECT
        at.transaction_id,
        at.name AS transaction_name,
        at.transaction_begin_time,
        at.transaction_state,
        s.session_id,
        s.login_name,
        s.host_name,
        s.program_name
    FROM sys.dm_tran_active_transactions at
    INNER JOIN sys.dm_tran_session_transactions st ON at.transaction_id = st.transaction_id
    INNER JOIN sys.dm_exec_sessions s ON st.session_id = s.session_id;
''')

rows = cursor.fetchall()
print(f'Found {len(rows)} open transactions:')
for row in rows:
    print(f'  Session {row.session_id}: txn {row.transaction_id} (state: {row.transaction_state}, started: {row.transaction_begin_time})')

conn.close()
