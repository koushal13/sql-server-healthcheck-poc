from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from dbmon.elastic import create_client
from dbmon.explainer import explain_event
from dbmon.settings import settings
from dbmon.sql_queries import SQL_QUERIES

app = FastAPI(title="DBMon Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent.parent.parent / "static"
if not static_dir.exists():
    static_dir = Path.cwd() / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "DBMon Dashboard API running. Visit /docs for API documentation."}


@app.post("/run-collector")
async def run_collector() -> dict[str, Any]:
    """Trigger the collector to fetch fresh data from SQL Server or samples."""
    try:
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "dbmon.cli", "collect"],
            cwd=str(Path(__file__).parent.parent.parent),
            capture_output=True,
            timeout=30,
            text=True
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "message": "Data collected successfully" if result.returncode == 0 else result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Collector timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _time_range(start: Optional[str], end: Optional[str]) -> dict:
    """Time range for queries."""
    if not start and not end:
        return {"range": {"@timestamp": {"gte": "now-2m", "lte": "now"}}}
    return {"range": {"@timestamp": {"gte": start, "lte": end}}}


def _get_latest_collection(index: str, event_type: str) -> dict[str, Any]:
    """Get the most recent collection from Elasticsearch for comparison."""
    query = {
        "bool": {
            "filter": [{"term": {"event_type": event_type}}]
        }
    }
    response = _search(index, query, size=100, sort=[{"@timestamp": "desc"}])
    # Group by key fields to get unique items
    items_by_key = {}
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        # Use a composite key (session_id for blocking/open_tx, query text for slow queries, etc)
        key = None
        if "session_id" in source:
            key = source.get("session_id")
        elif "query_text" in source:
            key = source.get("query_text", "")[:100]  # First 100 chars
        elif "deadlock_id" in source:
            key = source.get("deadlock_id")
        
        if key and key not in items_by_key:
            items_by_key[key] = source
    
    return items_by_key


def _calculate_delta(current_items: list[dict], previous_items: dict[str, Any], key_field: str) -> dict[str, Any]:
    """
    Calculate delta between current and previous collections.
    
    Returns:
        - new: Items that didn't exist before
        - changed: Items that existed but values changed
        - resolved: Items that existed before but are gone now (marked but not shown)
    """
    current_by_key = {str(item.get(key_field)): item for item in current_items}
    previous_keys = set(previous_items.keys())
    current_keys = set(current_by_key.keys())
    
    delta = {
        "new": [],
        "changed": [],
        "resolved": [],  # Just for reference, won't be shown
        "all": current_items  # If nothing changed, show all
    }
    
    # Items that are new
    new_keys = current_keys - previous_keys
    delta["new"] = [current_by_key[k] for k in new_keys]
    
    # Items that changed
    for key in current_keys & previous_keys:
        current = current_by_key[key]
        previous = previous_items[str(key)]
        
        # Check if any important fields changed
        changed_fields = []
        for field in ["elapsed_time_ms", "cpu_time_ms", "logical_reads", "duration_seconds", 
                     "wait_time_ms", "transaction_begin_time", "status", "message"]:
            if field in current and field in previous:
                if current[field] != previous[field]:
                    changed_fields.append({
                        "field": field,
                        "old": previous[field],
                        "new": current[field]
                    })
        
        if changed_fields:
            delta["changed"].append({
                **current,
                "changed_fields": changed_fields
            })
    
    # Items that are resolved (existed before but not now)
    resolved_keys = previous_keys - current_keys
    delta["resolved"] = [previous_items[k] for k in resolved_keys]
    
    return delta


@app.get("/blocking")
async def blocking(start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    """Return only NEW or CHANGED blocking events since last collection."""
    if settings.collector_mode != "live" or not settings.sql_connection_string:
        query = {
            "bool": {
                "filter": [
                    _time_range(start, end),
                    {"term": {"event_type": "blocking"}},
                ]
            }
        }
        response = _search(settings.elastic_index_metrics, query, size=200, sort=[{"@timestamp": "desc"}])
        events = [{"payload": hit["_source"].get("payload", {})} for hit in response["hits"]["hits"]]
        return {
            "events": events,
            "total": len(events),
            "new_count": 0,
            "changed_count": 0,
            "resolved_count": 0,
            "note": "Mock mode: showing blocking events from Elasticsearch",
        }
    # Get current live blocking data from database
    import pyodbc
    conn = pyodbc.connect(settings.sql_connection_string, timeout=10)
    cursor = conn.cursor()
    cursor.execute(SQL_QUERIES["blocking"])
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    
    current_items = [
        {col: val for col, val in zip(columns, row)}
        for row in rows
    ]
    
    # Get previous collection from Elasticsearch
    previous_items = _get_latest_collection(settings.elastic_index_metrics, "blocking")
    
    # Calculate delta
    delta = _calculate_delta(current_items, previous_items, "blocking_session_id")
    
    # Show new + changed only (not previously resolved items)
    items_to_show = delta["new"] + delta["changed"]
    
    # Add payload wrapper for frontend compatibility
    events = [{"payload": item} for item in items_to_show]
    
    return {
        "events": events,
        "total": len(events),
        "new_count": len(delta["new"]),
        "changed_count": len(delta["changed"]),
        "resolved_count": len(delta["resolved"]),
        "note": "Showing only NEW or CHANGED blocking issues since last collection"
    }



def _search(index: str, query: dict, size: int = 50, sort: Optional[List] = None) -> dict:
    client = create_client()
    body = {"query": query, "size": size}
    if sort:
        body["sort"] = sort
    return client.search(index=index, body=body)


def _aggregate(index: str, query: dict, aggs: dict) -> dict:
    client = create_client()
    body = {"query": query, "size": 0, "aggs": aggs}
    return client.search(index=index, body=body)


@app.get("/")
async def root():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "DBMon Dashboard API running. Visit /docs for API documentation."}


@app.get("/health")
async def health(start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    query = {"bool": {"filter": [_time_range(start, end)]}}
    response = _search(settings.elastic_index_metrics, query, size=0)
    return {
        "start": start,
        "end": end,
        "total_events": response["hits"]["total"]["value"],
    }


@app.get("/stats")
async def stats(start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    query = {"bool": {"filter": [_time_range(start, end)]}}
    aggs = {
        "by_event_type": {"terms": {"field": "event_type"}},
        "avg_cpu": {"avg": {"field": "payload.cpu_percent"}},
        "avg_free_tempdb": {"avg": {"field": "payload.free_space_kb"}},
    }
    response = _aggregate(settings.elastic_index_metrics, query, aggs)
    return {
        "event_counts": response.get("aggregations", {}).get("by_event_type", {}).get("buckets", []),
        "avg_cpu": response.get("aggregations", {}).get("avg_cpu", {}).get("value"),
        "avg_free_tempdb": response.get("aggregations", {}).get("avg_free_tempdb", {}).get("value"),
    }


@app.get("/alerts")
async def alerts(start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    query = {"bool": {"filter": [_time_range(start, end)]}}
    response = _search(settings.elastic_index_alerts, query, size=200, sort=[{"@timestamp": "desc"}])
    return {"alerts": [hit["_source"] for hit in response["hits"]["hits"]]}


@app.get("/slow-queries")
async def slow_queries(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    query = {
        "bool": {
            "filter": [
                _time_range(start, end),
                {"term": {"event_type": "slow_queries"}},
            ]
        }
    }
    response = _search(settings.elastic_index_metrics, query, size=limit, sort=[{"@timestamp": "desc"}])
    return {"events": [hit["_source"] for hit in response["hits"]["hits"]]}


@app.get("/blocking")
async def blocking(start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    query = {
        "bool": {
            "filter": [
                _time_range(start, end),
                {"term": {"event_type": "blocking"}},
            ]
        }
    }
    response = _search(settings.elastic_index_metrics, query, size=50, sort=[{"@timestamp": "desc"}])
    return {"events": [hit["_source"] for hit in response["hits"]["hits"]]}


@app.get("/deadlocks")
async def deadlocks(start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    """Deadlock monitoring - query from Elasticsearch."""
    query = {"bool": {"filter": [_time_range(start, end), {"term": {"event_type": "deadlocks"}}]}}
    response = _search(settings.elastic_index_metrics, query, size=50, sort=[{"@timestamp": "desc"}])
    events = [{"payload": hit["_source"]} for hit in response["hits"]["hits"]]
    return {
        "events": events,
        "total": len(events),
        "note": "Deadlock monitoring from Elasticsearch"
    }


@app.get("/slow-queries")
async def slow_queries(start: Optional[str] = None, end: Optional[str] = None, limit: int = Query(10, ge=1, le=100)) -> dict[str, Any]:
    """Return only CURRENTLY EXECUTING slow queries. Completed queries are auto-resolved."""
    import pyodbc
    conn = pyodbc.connect(settings.sql_connection_string, timeout=10)
    cursor = conn.cursor()
    cursor.execute(SQL_QUERIES["slow_queries"])
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    
    current_items = [
        {col: val for col, val in zip(columns, row)}
        for row in rows
    ][:limit]
    
    # Show ALL current queries (they're all actively running now)
    # Don't compare with Elasticsearch - assume anything not currently running is finished
    events = [{"payload": item} for item in current_items]
    
    return {
        "events": events,
        "total": len(events),
        "new_count": 0,
        "changed_count": 0,
        "resolved_count": 0,
        "note": f"Showing {len(events)} currently executing slow queries. Completed queries auto-resolved."
    }



@app.get("/api/events")
async def get_events(
    event_type: str = Query(..., description="Event type to filter"),
    start: Optional[str] = None, 
    end: Optional[str] = None
) -> dict[str, Any]:
    """Generic endpoint to query events by type.
    
    For open_transactions: queries SQL Server live (real-time)
    For others: queries Elasticsearch (historical data)
    """
    import pyodbc
    
    # For open transactions, query SQL Server directly to get live data
    if event_type == "open_transactions":
        try:
            conn = pyodbc.connect(settings.sql_connection_string, timeout=10)
            cursor = conn.cursor()
            cursor.execute(SQL_QUERIES["open_transactions"])
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                event_dict = {col: val for col, val in zip(columns, row)}
                event_dict["event_type"] = "open_transactions"
                event_dict["@timestamp"] = event_dict.get("transaction_begin_time", datetime.now(timezone.utc))
                # Wrap in payload for frontend compatibility
                events.append({"payload": event_dict})
            
            return {"events": events}
        except Exception as e:
            # Fallback to Elasticsearch if live SQL query fails
            query = {
                "bool": {
                    "filter": [
                        _time_range(start, end),
                        {"term": {"event_type": "open_transactions"}},
                    ]
                }
            }
            response = _search(settings.elastic_index_metrics, query, size=50, sort=[{"@timestamp": "desc"}])
            return {"events": [hit["_source"] for hit in response["hits"]["hits"]], "error": str(e)}
    
    # For all other events, query Elasticsearch
    query = {
        "bool": {
            "filter": [
                _time_range(start, end),
                {"term": {"event_type": event_type}},
            ]
        }
    }
    response = _search(settings.elastic_index_metrics, query, size=50, sort=[{"@timestamp": "desc"}])
    return {"events": [hit["_source"] for hit in response["hits"]["hits"]]}


@app.get("/recommendations")
async def recommendations(start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    query = {
        "bool": {
            "filter": [_time_range(start, end)]
        }
    }
    response = _search(settings.elastic_index_alerts, query, size=100, sort=[{"@timestamp": "desc"}])
    recommendations = []
    for hit in response["hits"]["hits"]:
        recs = hit["_source"].get("recommendations", [])
        recommendations.extend(recs)
    return {"recommendations": recommendations}


@app.post("/explain")
async def explain(event: dict[str, Any]) -> dict[str, Any]:
    return explain_event(event)


@app.post("/kill-session")
async def kill_session(request: dict[str, Any]) -> dict[str, Any]:
    """Kill a SQL Server session (SPID)."""
    import pyodbc
    from dbmon.settings import settings
    
    session_id = request.get("session_id")
    if not session_id:
        return {"status": "error", "message": "session_id is required"}
    
    try:
        # KILL command must run outside transactions - use autocommit
        conn = pyodbc.connect(settings.sql_connection_string, timeout=10, autocommit=True)
        cursor = conn.cursor()
        
        # First check if session exists and is active
        cursor.execute(
            "SELECT session_id, login_name, program_name FROM sys.dm_exec_sessions WHERE session_id = ?",
            session_id
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"status": "error", "message": "⚠️ Session not found (already terminated or stale data from Elasticsearch)."}
        
        # Check if it's our own session
        cursor.execute("SELECT @@SPID")
        current_spid = cursor.fetchone()[0]
        if int(session_id) == current_spid:
            conn.close()
            return {"status": "error", "message": "❌ Cannot kill dashboard's own session."}
        
        # Now kill it
        cursor.execute(f"KILL {session_id}")
        conn.close()
        return {"status": "success", "message": f"Session {session_id} killed successfully"}
    except pyodbc.Error as e:
        error_msg = str(e)
        # Handle specific SQL Server errors
        if "6104" in error_msg or "kill your own process" in error_msg.lower():
            return {"status": "error", "message": "❌ Cannot kill dashboard's own session. This is a system session."}
        elif "6106" in error_msg or "6107" in error_msg or "not an active process" in error_msg.lower():
            return {"status": "error", "message": "⚠️ Session not found or already terminated."}
        else:
            return {"status": "error", "message": f"Failed to kill session: {error_msg}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
