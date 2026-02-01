from __future__ import annotations

SQL_QUERIES: dict[str, str] = {
    "blocking": """
    SELECT
        r.session_id AS blocked_session_id,
        r.blocking_session_id AS blocking_session_id,
        r.wait_type,
        r.wait_time AS wait_time_ms,
        r.wait_resource,
        r.cpu_time AS cpu_time_ms,
        r.total_elapsed_time AS elapsed_time_ms,
        s.host_name,
        s.program_name,
        s.login_name,
        DB_NAME(r.database_id) AS database_name,
        t.text AS query_text
    FROM sys.dm_exec_requests r
    INNER JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
    OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
    WHERE r.blocking_session_id <> 0;
    """,
    "open_transactions": """
    SELECT
        at.transaction_id,
        at.name AS transaction_name,
        at.transaction_begin_time,
        at.transaction_state,
        DATEDIFF(SECOND, at.transaction_begin_time, GETDATE()) AS duration_seconds,
        s.session_id,
        s.login_name,
        s.host_name,
        s.program_name,
        DB_NAME(r.database_id) AS database_name,
        ISNULL(SUBSTRING(ib.event_info, 1, 500), ISNULL(SUBSTRING(t.text, 1, 500), 'No query text available')) AS query_text,
        CASE WHEN ISNULL(r.blocking_session_id, 0) > 0 THEN 1 ELSE 0 END AS is_blocking,
        ISNULL(r.blocking_session_id, 0) AS blocking_session_id,
        ISNULL(r.wait_type, 'IDLE') AS wait_type,
        ISNULL(r.wait_time, 0) AS wait_time_ms
    FROM sys.dm_tran_active_transactions at
    INNER JOIN sys.dm_tran_session_transactions st ON at.transaction_id = st.transaction_id
    INNER JOIN sys.dm_exec_sessions s ON st.session_id = s.session_id
    LEFT JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
    OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
    OUTER APPLY sys.dm_exec_input_buffer(s.session_id, NULL) ib
    WHERE s.session_id != @@SPID
    AND s.program_name NOT LIKE 'dbmon%';
    """,
    "missing_indexes": """
    SELECT
        DB_NAME(mid.database_id) AS database_name,
        migs.user_seeks,
        migs.user_scans,
        migs.avg_total_user_cost,
        migs.avg_user_impact,
        mid.statement AS table_name,
        mid.equality_columns,
        mid.inequality_columns,
        mid.included_columns
    FROM sys.dm_db_missing_index_group_stats migs
    INNER JOIN sys.dm_db_missing_index_groups mig ON migs.group_handle = mig.index_group_handle
    INNER JOIN sys.dm_db_missing_index_details mid ON mig.index_handle = mid.index_handle;
    """,
    "slow_queries": """
    -- Show ONLY currently executing slow queries (NOT completed)
    -- Once a query finishes, it disappears from dashboard automatically
    SELECT TOP 20
        r.session_id,
        r.start_time,
        r.status,
        r.command,
        r.total_elapsed_time AS elapsed_time_ms,
        r.total_elapsed_time AS avg_elapsed_time_ms,
        r.cpu_time AS cpu_time_ms,
        r.logical_reads AS avg_logical_reads,
        r.writes,
        r.wait_type,
        r.wait_time AS wait_time_ms,
        DB_NAME(r.database_id) AS database_name,
        s.host_name,
        s.program_name,
        s.login_name,
        COALESCE(
            SUBSTRING(t.text, 
                (r.statement_start_offset/2) + 1,
                ((CASE r.statement_end_offset 
                    WHEN -1 THEN DATALENGTH(t.text)
                    ELSE r.statement_end_offset 
                END - r.statement_start_offset)/2) + 1
            ),
            t.text,
            'Query text not available'
        ) AS query_text,
        1 AS execution_count
    FROM sys.dm_exec_requests r
    INNER JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
    OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
    WHERE r.session_id <> @@SPID
        AND r.session_id > 50
        AND s.is_user_process = 1
        AND r.total_elapsed_time > 1000
        AND r.status IN ('RUNNING', 'RUNNABLE')
    ORDER BY r.total_elapsed_time DESC;
    """,
    
    "slow_queries_historical": """
    -- HISTORICAL: Keep this for analytics/trends (not used in live dashboard)
    -- Senior DBA Best Practice: Multi-dimensional slow query analysis
    SELECT TOP 20
        qs.total_elapsed_time / qs.execution_count AS avg_elapsed_time_ms,
        qs.total_elapsed_time AS total_elapsed_time_ms,
        qs.execution_count,
        qs.last_execution_time,
        
        -- CPU analysis (high CPU vs high wait indicates different problems)
        qs.total_worker_time / qs.execution_count AS avg_cpu_time_ms,
        qs.total_worker_time AS total_cpu_time_ms,
        CASE 
            WHEN qs.total_elapsed_time > 0 
            THEN (qs.total_worker_time * 100.0) / qs.total_elapsed_time 
            ELSE 0 
        END AS cpu_percentage,
        
        -- I/O pressure indicators
        qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
        qs.total_physical_reads / qs.execution_count AS avg_physical_reads,
        qs.total_logical_writes / qs.execution_count AS avg_logical_writes,
        
        -- Row efficiency (high reads with low rows = inefficiency)
        qs.total_rows / qs.execution_count AS avg_rows_returned,
        CASE 
            WHEN qs.total_rows > 0 
            THEN (qs.total_logical_reads * 1.0) / qs.total_rows 
            ELSE qs.total_logical_reads 
        END AS reads_per_row,
        
        -- Memory and parallelism
        qs.total_grant_kb / qs.execution_count AS avg_grant_kb,
        qs.total_used_grant_kb / qs.execution_count AS avg_used_grant_kb,
        qs.total_dop / qs.execution_count AS avg_dop,
        
        -- Query identification
        DB_NAME(st.dbid) AS database_name,
        SUBSTRING(st.text, (qs.statement_start_offset/2) + 1,
            ((CASE qs.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE qs.statement_end_offset
            END - qs.statement_start_offset)/2) + 1) AS query_text,
        
        -- Cumulative impact score (considers frequency + duration)
        (qs.total_elapsed_time * 1.0) / 1000000 AS total_elapsed_seconds,
        
        -- Plan age (old plans might be stale)
        qs.creation_time,
        DATEDIFF(HOUR, qs.creation_time, GETDATE()) AS plan_age_hours
        
    FROM sys.dm_exec_query_stats qs
    CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
    WHERE qs.execution_count > 0
        -- Filter out trivial queries (< 100ms avg AND < 10 execs AND < 1000 reads)
        AND (
            (qs.total_elapsed_time / qs.execution_count > 100000) -- Avg > 100ms
            OR (qs.execution_count > 100 AND qs.total_elapsed_time / qs.execution_count > 50000) -- Frequent queries > 50ms
            OR (qs.total_logical_reads / qs.execution_count > 10000) -- High I/O
            OR (qs.total_worker_time / qs.execution_count > 50000) -- High CPU
            OR (qs.total_elapsed_time > 300000000) -- Total elapsed > 5 min cumulative
        )
    ORDER BY 
        -- Prioritize by cumulative impact, then average duration
        (qs.total_elapsed_time * 0.6 + (qs.total_elapsed_time / qs.execution_count) * qs.execution_count * 0.4) DESC;
    """,
    "cpu_memory": """
    SELECT
        (SELECT TOP 1 cntr_value FROM sys.dm_os_performance_counters
            WHERE counter_name = 'Processor Time' AND instance_name = '_Total') AS cpu_percent,
        (SELECT available_physical_memory_kb / 1024 FROM sys.dm_os_sys_memory) AS available_memory_mb,
        (SELECT total_physical_memory_kb / 1024 FROM sys.dm_os_sys_memory) AS total_memory_mb,
        (SELECT physical_memory_in_use_kb / 1024 FROM sys.dm_os_process_memory) AS sql_memory_in_use_mb;
    """,
    "tempdb_health": """
    SELECT
        SUM(user_object_reserved_page_count) * 8 AS user_objects_kb,
        SUM(internal_object_reserved_page_count) * 8 AS internal_objects_kb,
        SUM(version_store_reserved_page_count) * 8 AS version_store_kb,
        SUM(unallocated_extent_page_count) * 8 AS free_space_kb
    FROM tempdb.sys.dm_db_file_space_usage;
    """,
}

DEADLOCK_QUERY = """
IF EXISTS (SELECT 1 FROM sys.server_event_sessions WHERE name = 'system_health')
BEGIN
    DECLARE @path NVARCHAR(260);
    SELECT @path = CAST(target_data AS XML).value('(EventFileTarget/File/@name)[1]', 'nvarchar(260)')
    FROM sys.dm_xe_sessions s
    JOIN sys.dm_xe_session_targets t ON s.address = t.event_session_address
    WHERE s.name = 'system_health' AND t.target_name = 'event_file';

    SELECT TOP 20
        CAST(event_data AS XML) AS deadlock_xml,
        DATEADD(mi, DATEDIFF(mi, GETUTCDATE(), CURRENT_TIMESTAMP),
            CAST(event_data AS XML).value('(event/@timestamp)[1]', 'datetime2')) AS event_time
    FROM sys.fn_xe_file_target_read_file(@path, NULL, NULL, NULL)
    WHERE object_name = 'xml_deadlock_report'
    ORDER BY event_time DESC;
END
"""
