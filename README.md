# SQL Server Health Check - DBMon

Real-time SQL Server monitoring with automated problem detection, AI-powered analysis, and actionable recommendations. Monitor deadlocks, blocking chains, slow queries, CPU/memory usage, TempDB health, and missing indexes.

## Demo

🎥 **Watch the System in Action**

<video src="https://github.com/koushal13/sql-server-healthcheck-poc/raw/main/demo.mp4" controls width="100%" style="max-width: 800px;">
  Your browser does not support the video tag. <a href="./demo.mp4">Download the demo video</a>
</video>

**What you'll see:**
- Connecting to SQL Server and detecting problems
- Real-time blocking chains and slow query detection  
- Triggering alerts with severity levels
- AI-powered explanations and recommendations
- Dashboard auto-refresh and manual collection

**Video Details:** 1 minute 19 seconds | 2394x1548 @ 60fps | 3.6MB

## Features

- 🔍 **7 Critical Metrics**: Deadlocks, blocking chains, open transactions, slow queries, CPU/memory, TempDB health, missing indexes
- 🤖 **AI-Powered Analysis**: Simple explanations and actionable recommendations for detected problems
- 📊 **Real-Time Dashboard**: Web UI with 30-second auto-refresh and on-demand collection
- 📈 **Historical Data**: 30-day retention in Elasticsearch for trend analysis
- ⚡ **Fast Setup**: Connect to any SQL Server (Docker, Express, Azure, on-prem) in 5 minutes
- 🧪 **Test Scripts**: SQL scripts to generate test problems for validation

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR SQL SERVER                              │
│  - Docker SQL Server (port 1433)                                     │
│  - SQL Server Express / Enterprise / Azure SQL                       │
│  - Problems: Deadlocks, Blocking, Slow Queries, etc.                 │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                          pyodbc connection
                          (ODBC Driver 18)
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   DBMON COLLECTOR (Python)                           │
│  - Queries 7 DMV views (sys.dm_exec_requests, etc.)                 │
│  - Detects: deadlocks, blocking, slow queries, CPU, memory          │
│  - Applies alerting rules (rules.yaml)                               │
│  - Enriches with AI explanations (optional: Ollama)                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                          bulk index API
                          (HTTP POST)
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              ELASTICSEARCH (Docker - port 9200)                      │
│  - Index: dbmon-metrics (raw DMV data)                               │
│  - Index: dbmon-alerts (triggered alerts with explanations)          │
│  - Retention: 30 days (configurable ILM)                             │
│  - Full-text search enabled                                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                          search queries
                          (Elasticsearch DSL)
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              FASTAPI DASHBOARD (Python - port 8000)                  │
│  - REST API: /alerts, /blocking, /slow-queries, /deadlocks          │
│  - Trigger: POST /run-collector (on-demand collection)               │
│  - AI Explain: POST /explain (problem analysis)                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                          HTTP requests
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   WEB UI (static/index.html)                         │
│  - Dashboard with charts & tables                                    │
│  - Auto-refresh: 30 seconds                                          │
│  - Manual trigger: "Run Collector Now" button                        │
│  - View: last 5/30 minutes or custom time range                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Docker Compose Stack

The system runs as a complete Docker stack with 5 services:

```yaml
services:
  elasticsearch:8.15.1  → Data storage (port 9200)
  kibana:8.15.1         → Optional: Data exploration UI (port 5601)
  mssql:2019           → SQL Server for testing (port 1433)
  ollama:latest        → Optional: AI analysis (port 11434)
  dashboard:latest     → FastAPI + Collector (port 8000)
```

**Network Flow:**
- Dashboard connects to Elasticsearch on `http://elasticsearch:9200` (Docker internal network)
- Dashboard connects to SQL Server on `mssql:1433` or external server
- User accesses dashboard at `http://localhost:8000` (host machine)
- Optional: Kibana UI at `http://localhost:5601` for advanced queries

## Process Flow

### Data Collection Flow

```
1. TRIGGER
   ├─ Manual: User clicks "Run Collector Now" button
   ├─ API: POST /run-collector
   └─ Scheduled: Cron job (e.g., every 5 minutes)
                 └─> python -m dbmon.cli collect

2. QUERY SQL SERVER (collector.py)
   ├─ Connect via pyodbc
   ├─ Execute 7 DMV queries:
   │  ├─ sys.dm_exec_requests (slow queries, blocking)
   │  ├─ sys.dm_tran_active_transactions (open transactions)
   │  ├─ sys.dm_os_performance_counters (CPU, memory)
   │  ├─ sys.dm_db_file_space_usage (TempDB)
   │  ├─ sys.dm_db_missing_index_details (missing indexes)
   │  └─ system_health XEvents (deadlocks)
   └─ Parse results into metrics (JSON)

3. APPLY ALERTING RULES (alerts.py)
   ├─ Load rules from alerting/rules.yaml
   ├─ Evaluate conditions:
   │  ├─ Slow query: avg_elapsed_ms > 20000
   │  ├─ Blocking: wait_time_ms > 30000
   │  ├─ Open transaction: duration_seconds > 3600
   │  ├─ High CPU: cpu_percent > 85
   │  ├─ TempDB low: free_space_gb < 10
   │  └─ etc.
   └─ Generate alerts (with severity: low/medium/high/critical)

4. ENRICH WITH AI (explainer.py - optional)
   ├─ For each alert:
   │  ├─ Send to Ollama LLM (or OpenAI)
   │  ├─ Get simple explanation (plain English)
   │  └─ Get actionable recommendations
   └─ Add to alert object

5. SHIP TO ELASTICSEARCH (elastic.py)
   ├─ Bulk index metrics → dbmon-metrics index
   ├─ Bulk index alerts → dbmon-alerts index
   └─ Add @timestamp for time-series queries

6. DASHBOARD DISPLAY (dashboard.py)
   ├─ Query Elasticsearch for last N minutes
   ├─ Aggregate by:
   │  ├─ Alert type (blocking, slow query, etc.)
   │  ├─ Severity (critical, high, medium, low)
   │  └─ Time buckets (for charts)
   ├─ Return JSON to frontend
   └─ Frontend renders tables + charts

7. USER INTERACTION
   ├─ View alerts with explanations
   ├─ Click "Show Details" for recommendations
   ├─ Click "Run Collector Now" to refresh
   └─ Change time range to view history
```

### Query Execution Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│ T=0s: User clicks "Run Collector Now"                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ T=0-2s: Connect to SQL Server & Execute 7 DMV Queries           │
│   - sys.dm_exec_requests          (0.2s)                        │
│   - sys.dm_tran_active_transactions (0.1s)                      │
│   - sys.dm_os_performance_counters (0.1s)                       │
│   - sys.dm_db_file_space_usage    (0.3s)                        │
│   - sys.dm_db_missing_index_details (0.5s)                      │
│   - system_health deadlocks       (0.8s)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ T=2-3s: Apply Alerting Rules                                    │
│   - Evaluate 15+ conditions                                     │
│   - Filter out non-critical issues                              │
│   - Assign severity levels                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ T=3-5s: AI Enrichment (optional, if enabled)                    │
│   - Send 3-5 alerts to Ollama                                   │
│   - Get explanations + recommendations                           │
│   - Fallback: Use template explanations if AI unavailable       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ T=5-6s: Bulk Index to Elasticsearch                             │
│   - 100-500 metric documents                                    │
│   - 3-10 alert documents                                        │
│   - Async write (non-blocking)                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ T=6s: Dashboard Auto-Refresh                                    │
│   - Query Elasticsearch (last 30 min)                           │
│   - Render updated alerts                                       │
│   - Show "Last updated: 2 seconds ago"                          │
└─────────────────────────────────────────────────────────────────┘

Total Time: ~6 seconds (with AI) or ~3 seconds (without AI)
```

## Prerequisites

- Python 3.9+
- Docker (for Elasticsearch & Kibana)
- SQL Server 2016+ (Docker, Express, Azure SQL, or on-premises)
- SQL Server login with `VIEW SERVER STATE` permission

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/koushal13/sql-server-healthcheck-poc.git
cd sql-server-healthcheck-poc
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Start Elasticsearch & Kibana

```bash
docker-compose up -d
```

Wait 30 seconds for services to start, then verify:
```bash
curl http://localhost:9200
curl http://localhost:5601
```

### 3. Configure Connection

Copy `.env.example` to `.env` and edit:

```bash
# Mock mode (uses sample data)
COLLECTOR_MODE=mock

# OR Live mode (connect to your SQL Server)
COLLECTOR_MODE=live
SQL_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=master;UID=sa;PWD=YourPassword;TrustServerCertificate=yes
```

**Common Connection Strings:**
- **Docker SQL Server**: `DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=master;UID=sa;PWD=YourPassword;TrustServerCertificate=yes`
- **Windows Authentication**: `DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=master;Trusted_Connection=yes`
- **Azure SQL**: `DRIVER={ODBC Driver 18 for SQL Server};SERVER=yourserver.database.windows.net;DATABASE=master;UID=username;PWD=password`

### 4. Run Collector (One-time)

```bash
python -m dbmon.cli collect
```

This collects metrics once and ships to Elasticsearch.

### 5. Start Dashboard

```bash
uvicorn dbmon.dashboard:app --host 0.0.0.0 --port 8000
```

Open browser: http://localhost:8000

## Dashboard Features

- **Run Collector Now**: Trigger immediate data collection (button in UI)
- **Auto-Refresh**: Dashboard updates every 30 seconds
- **Time Range**: View data from last 5 minutes, 30 minutes, or custom range
- **Alerts**: See triggered alerts with severity and explanations
- **Blocking Sessions**: View blocking chains with wait times
- **Slow Queries**: Identify queries taking > 20 seconds
- **Deadlocks**: See deadlock victims and participants
- **Recommendations**: Get AI-powered fixes for each problem

## API Endpoints

- `GET /health?start=&end=` - Health status summary
- `GET /alerts?start=&end=` - Triggered alerts
- `GET /slow-queries?start=&end=&limit=10` - Slow query list
- `GET /blocking?start=&end=` - Blocking sessions
- `GET /deadlocks?start=&end=` - Deadlock events
- `GET /recommendations?start=&end=` - AI recommendations
- `POST /run-collector` - Trigger data collection
- `POST /explain` - Get AI analysis for a problem

## Testing with Sample Problems

Use the provided SQL scripts to generate test problems:

```sql
-- Create test database and problems
-- File: sample_queries/DETAILED_PROBLEMS.sql

-- Run in SQL Server Management Studio or any SQL client
-- Includes 7 problems: slow queries, blocking, open transactions,
-- high CPU, TempDB pressure, missing indexes, and deadlocks
```

**Quick Test:**
1. Run `sample_queries/DETAILED_PROBLEMS.sql` in SSMS
2. Click "Run Collector Now" in dashboard
3. See detected problems with AI explanations

## Project Structure

```
.
├── src/dbmon/              # Main package
│   ├── collector.py        # SQL Server metric collector
│   ├── dashboard.py        # FastAPI web server
│   ├── explainer.py        # AI problem analysis
│   ├── elastic.py          # Elasticsearch client
│   └── sql_queries.py      # DMV queries
├── sample_queries/         # Test SQL scripts
│   └── DETAILED_PROBLEMS.sql
├── alerting/
│   └── rules.yaml          # Alert definitions
├── static/
│   └── index.html          # Dashboard UI
├── docker-compose.yml      # Elasticsearch & Kibana
└── .env.example           # Configuration template
```

## Monitored Metrics

1. **Deadlocks**: Detected from system_health extended events
2. **Blocking Chains**: Sessions waiting > 30 seconds for locks
3. **Open Transactions**: Transactions open > 1 hour
4. **Slow Queries**: Queries with avg execution time > 20 seconds
5. **CPU Usage**: Server CPU > 85%
6. **Memory Pressure**: Available memory < 2GB
7. **TempDB Health**: Free space < 10GB
8. **Missing Indexes**: Recommended indexes with high impact

## Advanced Usage

### Stress Testing

Generate high-volume test data:
```bash
python -m dbmon.cli stress --count 100000 --output sample_inputs/stress_metrics.jsonl
python -m dbmon.cli load-samples --path sample_inputs/stress_metrics.jsonl
```

### Scheduled Collection

Run collector every 5 minutes with cron:
```bash
*/5 * * * * /path/to/.venv/bin/python -m dbmon.cli collect
```

### Custom Alert Rules

Edit `alerting/rules.yaml` to customize thresholds:
```yaml
rules:
  - name: slow_query
    condition: avg_elapsed_ms > 20000
    severity: medium
    message: "Query is taking longer than 20 seconds"
```

## Troubleshooting

**Elasticsearch not starting:**
```bash
docker-compose down
docker-compose up -d
docker-compose logs
```

**SQL Server connection fails:**
- Verify connection string in `.env`
- Check SQL Server is running: `docker ps` or Windows Services
- Test ODBC driver: `python -c "import pyodbc; print(pyodbc.drivers())"`
- Verify login has `VIEW SERVER STATE` permission

**No data in dashboard:**
- Click "Run Collector Now" to trigger collection
- Check collector logs: `python -m dbmon.cli collect`
- Verify Elasticsearch has data: `curl http://localhost:9200/dbmon-metrics/_count`

**Dashboard not loading:**
- Verify port 8000 is not in use: `lsof -i :8000`
- Check FastAPI logs for errors
- Try different port: `uvicorn dbmon.dashboard:app --port 8001`

## Requirements

See `requirements.txt` for full list. Key dependencies:
- `pyodbc` - SQL Server connection
- `elasticsearch` - Metric storage
- `fastapi` - Web API
- `uvicorn` - ASGI server

## License

This is a proof-of-concept project for SQL Server health monitoring.

## Contributing

Issues and pull requests welcome at: https://github.com/koushal13/sql-server-healthcheck-poc
