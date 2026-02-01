from __future__ import annotations

import json
from typing import Any

import requests

from dbmon.settings import settings


def _get_fallback_explanation(event: dict[str, Any]) -> dict[str, Any]:
    """Fallback to static explanations if AI is unavailable."""
    event_type = event.get("event_type", "unknown")
    payload = event.get("payload", {})

    if event_type == "blocking":
        blocked = payload.get("blocked_session_id")
        blocking = payload.get("blocking_session_id")
        wait = payload.get("wait_type")
        wait_ms = payload.get("wait_time_ms")
        return {
            "summary": f"🔒 Your query (session {blocked}) is stuck waiting",
            "details": f"It's been waiting for {wait_ms} ms because session {blocking} is using the same data.",
            "analysis": "Think of it like waiting in line: someone else is modifying the same table/row you need. Your query can't proceed until they're done.",
            "recommendations": [
                "👉 If the blocking session is yours: Make sure your code commits or rollbacks the transaction quickly (add COMMIT or ROLLBACK).",
                "👉 If the blocking session is someone else's: Ask them to finish their transaction or contact your DBA.",
                "💡 Prevention: Keep transactions SHORT - don't leave BEGIN TRANSACTION open while waiting for user input or doing long operations.",
                "💡 Add WHERE clauses to update/delete only the rows you need (less blocking for others).",
            ],
        }

    if event_type == "deadlocks":
        return {
            "summary": "💀 DEADLOCK: Two queries got stuck waiting for each other",
            "details": "SQL Server detected a circular wait and killed one of the queries to break the deadlock.",
            "analysis": "Imagine two people at a narrow doorway, each blocking the other. Neither can proceed. This happens when queries lock tables in different orders.",
            "recommendations": [
                "👉 IMMEDIATE FIX: Retry the failed query - it will work now that the deadlock is broken.",
                "💡 Long-term fix: Always access tables in the SAME ORDER in all your code (e.g., always update Users before Orders, not sometimes reversed).",
                "💡 Use smaller transactions - don't lock multiple tables at once if you can avoid it.",
                "💡 Add proper indexes to make queries faster (less time holding locks = fewer deadlocks).",
            ],
        }

    if event_type == "open_transactions":
        txn = payload.get("transaction_id")
        session = payload.get("session_id", "unknown")
        return {
            "summary": f"⚠️ A transaction has been left open (session {session})",
            "details": f"Transaction {txn} started but never finished with COMMIT or ROLLBACK.",
            "analysis": "It's like leaving your database 'in progress' - the database is holding locks waiting for you to say 'I'm done!' This blocks other users and can cause slowdowns.",
            "recommendations": [
                "👉 CHECK YOUR CODE: Do you have a BEGIN TRANSACTION without a matching COMMIT or ROLLBACK?",
                "👉 COMMON BUG: Exceptions/errors in your code might skip the COMMIT. Always use try/catch/finally to ensure transactions complete.",
                "💡 Code pattern: BEGIN TRANSACTION → do work → if success COMMIT else ROLLBACK",
                "💡 Avoid: Transactions spanning multiple API calls or user interactions (transaction should complete in milliseconds, not minutes).",
            ],
        }

    if event_type == "missing_indexes":
        table = payload.get("table_name")
        impact = payload.get("avg_user_impact")
        seeks = payload.get("user_seeks", 0)
        scans = payload.get("user_scans", 0)
        return {
            "summary": f"📊 SQL Server suggests adding an index to {table}",
            "details": f"Your queries would be ~{impact}% faster. This suggestion came from {seeks + scans} queries scanning this table.",
            "analysis": "Without an index, the database reads EVERY row in the table to find what you need (like reading a book page by page instead of using the index). An index makes lookups instant.",
            "recommendations": [
                "👉 SHARE THIS WITH YOUR DBA: They can add the index safely in production.",
                "💡 For learning: In SQL Server Management Studio, run your slow query and click 'Display Estimated Execution Plan' - green text shows missing index suggestions.",
                "💡 Quick test: Ask your DBA to add the index in a test database first to verify the improvement.",
                f"💡 The suggested columns to index are shown in the data (equality_columns, inequality_columns).",
            ],
        }

    if event_type == "slow_queries":
        avg_ms = payload.get("avg_elapsed_time_ms", 0)
        exec_count = payload.get("execution_count", 0)
        query_text = (payload.get("query_text") or "")[:200]
        avg_reads = payload.get("avg_logical_reads", 0)
        
        # Calculate human-readable timing
        if avg_ms > 1000:
            timing = f"{avg_ms/1000:.1f} seconds"
        else:
            timing = f"{avg_ms:.0f} milliseconds"
        
        return {
            "summary": f"🐢 Slow query taking {timing} on average",
            "details": f"Executed {exec_count} times. Reading {avg_reads:,.0f} data pages per execution. Query: {query_text}...",
            "analysis": "Your query is taking too long. This could be: (1) missing indexes (searching row-by-row), (2) fetching too much data, or (3) joining too many tables inefficiently.",
            "recommendations": [
                "👉 STEP 1: Add WHERE clauses to filter data early - don't fetch everything then filter in your code.",
                "👉 STEP 2: Only SELECT the columns you actually need (avoid SELECT *).",
                "💡 Check for missing indexes: Run your query in SQL Server Management Studio → Query → Display Estimated Execution Plan → look for table scans or missing index hints.",
                "💡 Large result sets? Use pagination (OFFSET/FETCH or TOP N) instead of loading thousands of rows.",
                "💡 Joins: Make sure you're joining on indexed columns (usually primary/foreign keys).",
            ],
        }

    if event_type == "cpu_memory":
        cpu = payload.get("cpu_percent")
        avail = payload.get("available_memory_mb")
        total = payload.get("total_memory_mb", 0)
        sql_in_use = payload.get("sql_memory_in_use_mb", 0)
        
        return {
            "summary": "💻 Server resource snapshot",
            "details": f"CPU: {cpu}% | Available memory: {avail:,.0f} MB of {total:,.0f} MB | SQL Server using: {sql_in_use:,.0f} MB",
            "analysis": "High CPU means queries are working hard (calculations, sorting, etc.). Low memory means the server might be swapping to disk (very slow).",
            "recommendations": [
                "👉 HIGH CPU? Look at slow queries above - one expensive query can max out CPU.",
                "💡 If CPU is constantly high: Consider adding indexes, optimizing queries, or scaling up your server.",
                "💡 LOW MEMORY? Contact your DBA - they may need to adjust SQL Server memory settings or add more RAM.",
                "💡 For developers: Write efficient queries (use WHERE, avoid functions in WHERE clause, use proper joins).",
            ],
        }

    if event_type == "tempdb_health":
        free_kb = payload.get("free_space_kb", 0)
        free_mb = free_kb / 1024
        user_kb = payload.get("user_objects_kb", 0)
        internal_kb = payload.get("internal_objects_kb", 0)
        
        return {
            "summary": "🗄️ TempDB (SQL Server's scratch space) status",
            "details": f"Free space: {free_mb:.1f} MB | User objects: {user_kb/1024:.1f} MB | Internal: {internal_kb/1024:.1f} MB",
            "analysis": "TempDB is like SQL Server's notepad - it stores temporary tables, sorting results, etc. If it fills up, queries will fail or become very slow.",
            "recommendations": [
                "👉 LOW SPACE? Check if your code is creating large #TempTables or doing ORDER BY on huge result sets.",
                "💡 Avoid: SELECT * from large tables then sorting - filter with WHERE first to reduce data.",
                "💡 Avoid: Huge JOIN results that need sorting - add indexes to avoid TempDB spills.",
                "💡 #TempTables: Make sure you DROP them when done (they use TempDB space).",
            ],
        }

    return {
        "summary": "📊 Database metric captured",
        "details": "This metric is being tracked for monitoring trends.",
        "analysis": "No specific issue detected with this metric right now.",
        "recommendations": ["Keep monitoring - if values change significantly, it might indicate a problem."],
    }


def _call_ollama_ai(event: dict[str, Any]) -> dict[str, Any] | None:
    """Call Ollama API for AI-powered analysis."""
    try:
        event_type = event.get("event_type", "unknown")
        payload = event.get("payload", {})
        
        # Build context-rich prompt for the AI
        prompt = f"""You are a database expert helping a junior developer understand a SQL Server issue.

EVENT TYPE: {event_type}
EVENT DATA: {json.dumps(payload, indent=2)}

Provide a developer-friendly explanation with:
1. SUMMARY (one line, use emojis): What's happening in simple terms
2. DETAILS: Key metrics and what they mean
3. ANALYSIS: Why this is a problem (use analogies, no jargon)
4. RECOMMENDATIONS (3-5 items): Actionable steps starting with 👉 for immediate actions and 💡 for prevention tips

Keep it conversational and practical. Assume the developer knows SQL basics but not DBA concepts.

Respond ONLY with valid JSON in this exact format:
{{
  "summary": "...",
  "details": "...",
  "analysis": "...",
  "recommendations": ["...", "..."]
}}"""

        response = requests.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 500,
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_text = result.get("response", "")
            
            # Extract JSON from response (handle markdown code blocks)
            ai_text = ai_text.strip()
            if "```json" in ai_text:
                ai_text = ai_text.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_text:
                ai_text = ai_text.split("```")[1].split("```")[0].strip()
            
            # Parse the JSON response
            ai_explanation = json.loads(ai_text)
            return ai_explanation
            
    except requests.exceptions.RequestException:
        # Ollama not available
        return None
    except (json.JSONDecodeError, KeyError, ValueError):
        # AI response wasn't valid JSON
        return None
    except Exception:
        # Any other error
        return None
    
    return None


def explain_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Explain database events using AI (Ollama) or fallback to static explanations.
    Provides developer-friendly analysis for database issues.
    """
    # Try AI analysis if enabled
    if settings.use_ai_analysis:
        ai_result = _call_ollama_ai(event)
        if ai_result:
            return ai_result
    
    # Fallback to static explanations
    return _get_fallback_explanation(event)

