#!/bin/bash

# DBMon - Quick Test Script
# This script helps you test the complete workflow:
# 1. Ensure Docker is running
# 2. Ensure Dashboard is running
# 3. Run a test SQL query
# 4. Trigger collector
# 5. Show results

set -e

echo "🚀 DBMon Quick Test Helper"
echo "=========================="

PROJECT_DIR="/Users/shatarupapradhan/Documents/Koushal/SQL-Server"
cd "$PROJECT_DIR"

# Step 1: Check if Docker is running
echo ""
echo "1️⃣  Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi

if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker daemon not running"
    exit 1
fi
echo "✅ Docker is running"

# Step 2: Check if containers are running
echo ""
echo "2️⃣  Checking containers..."
if ! docker-compose ps | grep -q elasticsearch; then
    echo "❌ Elasticsearch not running. Starting..."
    docker-compose up -d
    echo "⏳ Waiting for services to start (30 seconds)..."
    sleep 30
fi
echo "✅ Containers are running"

# Step 3: Check if dashboard is running
echo ""
echo "3️⃣  Checking dashboard..."
if ! curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "⚠️  Dashboard not running at http://localhost:8000"
    echo ""
    echo "Start dashboard in another terminal with:"
    echo "  cd $PROJECT_DIR"
    echo "  .venv/bin/python -m uvicorn dbmon.dashboard:app --host 0.0.0.0 --port 8000"
    echo ""
    exit 1
fi
echo "✅ Dashboard is running at http://localhost:8000"

# Step 4: Test SQL Server connection
echo ""
echo "4️⃣  Testing SQL Server connection..."
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/Users/shatarupapradhan/Documents/Koushal/SQL-Server')

try:
    from src.dbmon.settings import settings
    import pyodbc
    
    conn = pyodbc.connect(settings.sql_connection_string)
    cursor = conn.cursor()
    cursor.execute('SELECT @@VERSION')
    version = cursor.fetchone()[0]
    print(f"✅ SQL Server connected!")
    print(f"   Version: {version[:80]}...")
    conn.close()
except Exception as e:
    print(f"❌ SQL Server connection failed: {e}")
    sys.exit(1)
PYTHON_EOF

# Step 5: Instructions
echo ""
echo "✅ All systems ready!"
echo ""
echo "📖 NEXT STEPS:"
echo "=============="
echo ""
echo "1. Install mssql extension in VS Code (if not already installed)"
echo "   - Extensions → Search 'mssql' → Install"
echo ""
echo "2. Connect to Docker SQL Server"
echo "   - Command Palette (Cmd+Shift+P) → 'MS SQL: Add Connection'"
echo "   - Server: localhost,1433"
echo "   - User: sa"
echo "   - Password: (from docker-compose.yml)"
echo ""
echo "3. Create a new SQL query in VS Code"
echo "   - Right-click connection → New Query"
echo ""
echo "4. Run a slow query"
echo "   - Paste this:"
echo "     SELECT COUNT(*) FROM sys.all_objects o1"
echo "     CROSS JOIN sys.all_objects o2"
echo "     CROSS JOIN sys.all_objects o3;"
echo ""
echo "5. Go to dashboard: http://localhost:8000"
echo ""
echo "6. Click 'Run Collector Now'"
echo ""
echo "7. See problem appear in '🔴 Current Problems'"
echo ""
echo "8. Click 'AI Analysis' to see explanation"
echo ""
echo "🎉 Done! You're monitoring!"
echo ""
