from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pyodbc

from dbmon.settings import settings
from dbmon.sql_queries import DEADLOCK_QUERY, SQL_QUERIES


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(columns: list[str], row: Any) -> dict:
    return {col: row[i] for i, col in enumerate(columns)}


def _build_event(event_type: str, payload: dict) -> dict:
    return {
        "@timestamp": _now_iso(),
        "event_type": event_type,
        "host": settings.host_name,
        "sql_instance": settings.sql_instance,
        "payload": payload,
    }


def collect_from_sql() -> list[dict]:
    if not settings.sql_connection_string:
        raise ValueError("SQL_CONNECTION_STRING is required for live collection.")

    events: list[dict] = []
    
    # First, ensure DBMonTest database exists by connecting to master
    master_conn_string = settings.sql_connection_string.replace("Database=DBMonTest", "Database=master")
    try:
        with pyodbc.connect(master_conn_string, timeout=10) as conn:
            cursor = conn.cursor()
            # Create database if it doesn't exist
            cursor.execute("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'DBMonTest') CREATE DATABASE DBMonTest")
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not ensure DBMonTest exists: {e}")
    
    # Now connect to DBMonTest for actual data collection
    with pyodbc.connect(settings.sql_connection_string, timeout=10) as conn:
        cursor = conn.cursor()
        for event_type, query in SQL_QUERIES.items():
            try:
                cursor.execute(query)
                columns = [column[0] for column in cursor.description]
                for row in cursor.fetchall():
                    events.append(_build_event(event_type, _row_to_dict(columns, row)))
            except Exception as e:
                print(f"Warning: Error collecting {event_type}: {e}")

        try:
            cursor.execute(DEADLOCK_QUERY)
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                for row in cursor.fetchall():
                    payload = _row_to_dict(columns, row)
                    events.append(_build_event("deadlocks", payload))
        except Exception as e:
            print(f"Warning: Error collecting deadlocks: {e}")

    return events


def collect_mock(sample_events: list[dict]) -> list[dict]:
    now = _now_iso()
    enriched = []
    for event in sample_events:
        event_copy = {**event}
        event_copy["@timestamp"] = now
        event_copy.setdefault("host", settings.host_name)
        event_copy.setdefault("sql_instance", settings.sql_instance)
        enriched.append(event_copy)
    return enriched
