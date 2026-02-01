#!/usr/bin/env python3
"""
Test AI Analysis from Terminal
Run with: python test_ai_analysis.py
"""
import json
from dbmon.explainer import explain_event
from dbmon.settings import settings

print("=" * 60)
print("DBMon AI Analysis Test")
print("=" * 60)
print(f"AI Enabled: {settings.use_ai_analysis}")
print(f"Ollama URL: {settings.ollama_url}")
print(f"Model: {settings.ollama_model}")
print("=" * 60)

# Test 1: Slow Query
print("\n🔍 TEST 1: Slow Query Analysis\n")
slow_query_event = {
    'event_type': 'slow_queries',
    '@timestamp': '2026-02-01T12:00:00Z',
    'payload': {
        'avg_elapsed_time_ms': 15000,
        'execution_count': 50,
        'query_text': 'SELECT * FROM Orders WHERE Status = @status',
        'avg_logical_reads': 25000,
        'avg_cpu_time_ms': 12000
    }
}

result = explain_event(slow_query_event)
print(json.dumps(result, indent=2))

# Test 2: Blocking
print("\n" + "=" * 60)
print("\n🔍 TEST 2: Blocking Session Analysis\n")
blocking_event = {
    'event_type': 'blocking',
    '@timestamp': '2026-02-01T12:00:00Z',
    'payload': {
        'blocked_session_id': 123,
        'blocking_session_id': 456,
        'wait_type': 'LCK_M_X',
        'wait_time_ms': 45000,
        'database_name': 'DBMonTest'
    }
}

result = explain_event(blocking_event)
print(json.dumps(result, indent=2))

# Test 3: Deadlock
print("\n" + "=" * 60)
print("\n🔍 TEST 3: Deadlock Analysis\n")
deadlock_event = {
    'event_type': 'deadlocks',
    '@timestamp': '2026-02-01T12:00:00Z',
    'payload': {
        'deadlock_xml': '<deadlock>...</deadlock>'
    }
}

result = explain_event(deadlock_event)
print(json.dumps(result, indent=2))

print("\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)
