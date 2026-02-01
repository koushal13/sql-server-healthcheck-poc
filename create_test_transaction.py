#!/usr/bin/env python3
"""Create a test open transaction that can be killed from the dashboard."""
import pyodbc
import time

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

# Start a transaction
cursor.execute("BEGIN TRANSACTION")
cursor.execute("UPDATE Orders SET total_amount = 999 WHERE order_id = 1")

# Get session info
cursor.execute("SELECT @@SPID, DB_NAME(), SYSTEM_USER, HOST_NAME()")
spid, db, user, host = cursor.fetchone()

print(f"✅ Created open transaction:")
print(f"   Session ID (SPID): {spid}")
print(f"   Database: {db}")
print(f"   User: {user}")
print(f"   Host: {host}")
print(f"\n💡 This transaction will stay open for 5 minutes.")
print(f"   Go to the dashboard and click the kill button to terminate it.")
print(f"\n⏱️  Waiting (press Ctrl+C to rollback and exit)...")

try:
    time.sleep(300)  # 5 minutes
    print("\n⏰ Timeout reached, rolling back...")
    conn.rollback()
    print("✅ Transaction rolled back")
except KeyboardInterrupt:
    print("\n\n⚠️  Interrupted, rolling back...")
    conn.rollback()
    print("✅ Transaction rolled back")
finally:
    conn.close()
