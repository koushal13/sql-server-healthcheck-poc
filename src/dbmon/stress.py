from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

EVENT_TYPES = [
    "blocking",
    "deadlocks",
    "open_transactions",
    "missing_indexes",
    "slow_queries",
    "cpu_memory",
    "tempdb_health",
]


def _now_iso(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def generate_event(event_type: str) -> dict:
    if event_type == "blocking":
        return {
            "event_type": event_type,
            "payload": {
                "blocked_session_id": random.randint(50, 200),
                "blocking_session_id": random.randint(1, 49),
                "wait_type": random.choice(["LCK_M_S", "LCK_M_X", "PAGEIOLATCH"]),
                "wait_time_ms": random.randint(1000, 120000),
                "database_name": random.choice(["Sales", "HR", "Orders"]),
            },
        }
    if event_type == "deadlocks":
        return {
            "event_type": event_type,
            "payload": {"deadlock_xml": "<deadlock>...</deadlock>"},
        }
    if event_type == "open_transactions":
        return {
            "event_type": event_type,
            "payload": {
                "transaction_id": random.randint(100000, 999999),
                "transaction_state": random.randint(1, 6),
            },
        }
    if event_type == "missing_indexes":
        return {
            "event_type": event_type,
            "payload": {
                "database_name": "Sales",
                "table_name": "dbo.Orders",
                "avg_user_impact": random.randint(10, 95),
                "equality_columns": "CustomerId",
            },
        }
    if event_type == "slow_queries":
        return {
            "event_type": event_type,
            "payload": {
                "avg_elapsed_time_ms": random.randint(500, 60000),
                "execution_count": random.randint(1, 1000),
                "query_text": "SELECT * FROM Orders WHERE Status = 'Pending'",
            },
        }
    if event_type == "cpu_memory":
        return {
            "event_type": event_type,
            "payload": {
                "cpu_percent": random.randint(5, 100),
                "available_memory_mb": random.randint(100, 64000),
                "total_memory_mb": 65536,
            },
        }
    if event_type == "tempdb_health":
        return {
            "event_type": event_type,
            "payload": {
                "user_objects_kb": random.randint(10000, 200000),
                "internal_objects_kb": random.randint(10000, 200000),
                "version_store_kb": random.randint(10000, 200000),
                "free_space_kb": random.randint(1000, 50000),
            },
        }
    return {"event_type": event_type, "payload": {}}


def generate_events(count: int) -> list[dict]:
    events = []
    for i in range(count):
        event_type = random.choice(EVENT_TYPES)
        event = generate_event(event_type)
        event["@timestamp"] = _now_iso(offset_seconds=i)
        events.append(event)
    return events


def write_jsonl(path: str, events: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")
