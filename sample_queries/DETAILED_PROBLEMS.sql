-- ================================================================
-- SQL Server Problem Generator - Detailed Scripts
-- ================================================================
-- These scripts create various database problems that will be
-- detected and displayed in the DBMon dashboard.
--
-- IMPORTANT: Run in SQL Server Management Studio or any SQL client
-- ================================================================

-- ================================================================
-- STEP 1: Create Dedicated Database (BEST PRACTICE!)
-- ================================================================
-- Create a dedicated database for testing instead of using master

-- Check if database exists, drop if needed
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'DBMonTest')
BEGIN
    ALTER DATABASE DBMonTest SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE DBMonTest;
END
GO

-- Create new test database
CREATE DATABASE DBMonTest;
GO

-- Switch to the new database
USE DBMonTest;
GO

PRINT '✅ Database DBMonTest created and selected'
PRINT '   You are now working in a dedicated test database'
PRINT '   This keeps your master database clean!'
GO

-- ================================================================
-- STEP 2: Create Sample Tables
-- ================================================================

CREATE TABLE Orders (
    OrderId INT PRIMARY KEY IDENTITY(1,1),
    CustomerId INT,
    OrderDate DATETIME DEFAULT GETDATE(),
    TotalAmount DECIMAL(10,2),
    Status VARCHAR(50) DEFAULT 'New'
);

CREATE TABLE Customers (
    CustomerId INT PRIMARY KEY IDENTITY(1,1),
    CustomerName VARCHAR(100),
    Email VARCHAR(100),
    Phone VARCHAR(20)
);

INSERT INTO Customers VALUES ('John Doe', 'john@example.com', '555-1234');
INSERT INTO Customers VALUES ('Jane Smith', 'jane@example.com', '555-5678');
INSERT INTO Customers VALUES ('Bob Johnson', 'bob@example.com', '555-9999');

INSERT INTO Orders VALUES (1, GETDATE(), 100.00, 'New');
INSERT INTO Orders VALUES (2, GETDATE(), 250.50, 'Pending');
INSERT INTO Orders VALUES (3, GETDATE(), 75.25, 'Completed');

INSERT INTO Orders VALUES (1, GETDATE(), 150.00, 'Processing');
INSERT INTO Orders VALUES (2, GETDATE(), 300.75, 'Shipped');
INSERT INTO Orders VALUES (3, GETDATE(), 125.50, 'Delivered');

GO

-- ================================================================
-- PROBLEM 1: SLOW RUNNING QUERY
-- ================================================================
-- Impact: High query execution time, high CPU, blocking other queries
-- Alert Severity: MEDIUM
-- How to Trigger: Run this query and click "Run Collector Now"
-- Expected in Dashboard: "Slow Query: avg_elapsed > 20000ms"
--
-- TIP: Run in a separate window to see blocking + slow query together

PRINT '=== SLOW RUNNING QUERY ==='
PRINT 'Generating slow query (will take ~15 seconds)...'

SELECT TOP 10000
    o.OrderId,
    o.OrderDate,
    o.CustomerId,
    o.TotalAmount,
    c.CustomerId AS CustId,
    c.CustomerName,
    c.Email,
    c.Phone
FROM Orders o
CROSS JOIN Orders o2
CROSS JOIN Orders o3
LEFT JOIN Customers c ON o.CustomerId = c.CustomerId
WHERE o.OrderDate > '2020-01-01'
ORDER BY o.OrderDate DESC;

PRINT 'Slow query complete!'
GO

-- ================================================================
-- PROBLEM 2: BLOCKING CHAINS
-- ================================================================
-- Impact: Other sessions wait for locks to be released
-- Alert Severity: HIGH
-- How to Trigger: 
--   1. Run "BLOCKING STEP 1" in Window/Tab 1
--   2. Run "BLOCKING STEP 2" in Window/Tab 2
--   3. Quickly click "Run Collector Now" in dashboard
-- Expected in Dashboard: "Blocking: Session X blocked by Session Y (wait_time: ...ms)"

-- --- BLOCKING STEP 1: Create Lock (run in Window 1) ---
PRINT '=== BLOCKING CHAIN - STEP 1 ==='
PRINT 'Creating lock on Orders table...'

-- Switch to the new database
USE DBMonTest;
GO

BEGIN TRANSACTION;
    UPDATE Orders SET Status = 'UnLocked' WHERE OrderId = 1;
    -- IMPORTANT: Keep this window open, DON'T commit yet!
    -- This keeps the lock active for Step 2 to wait on
    PRINT 'Lock acquired. Keep this window open.'
    PRINT 'Now run BLOCKING STEP 2 in another window...'
    WAITFOR DELAY '00:05:00'  -- Hold lock for 5 minutes
COMMIT;
ROLLBACK;

-- --- BLOCKING STEP 2: Get Blocked (run in Window 2, while Step 1 is running) ---
PRINT '=== BLOCKING CHAIN - STEP 2 ==='
PRINT 'Trying to update same row (will be blocked)...'

BEGIN TRANSACTION;
    UPDATE Orders SET Status = 'Waiting' WHERE OrderId = 1;
    -- This will HANG because OrderId 1 is locked by Step 1
    PRINT 'This line won''t execute until Step 1 commits!'
COMMIT;

GO

-- ================================================================
-- PROBLEM 3: OPEN TRANSACTIONS
-- ================================================================
-- Impact: Blocks other connections, holds locks, uses log space
-- Alert Severity: MEDIUM
-- How to Trigger:
--   1. Run this script
--   2. The transaction stays open (doesn't commit)
--   3. Click "Run Collector Now" in dashboard
-- Expected in Dashboard: "Open Transaction: Session X (duration: ...seconds)"

PRINT '=== OPEN TRANSACTION ==='
PRINT 'Starting long-running transaction...'

BEGIN TRANSACTION;
    UPDATE Orders SET TotalAmount = TotalAmount * 1.1 WHERE CustomerId = 1;
    -- IMPORTANT: Keep this transaction open!
    -- The collector will detect it as a long-running open transaction
    PRINT 'Transaction is open. Keep this window open for dashboard to detect it.'
    PRINT 'Click "Run Collector Now" to see this transaction in the dashboard'
    WAITFOR DELAY '00:10:00'  -- Keep open for 10 minutes
COMMIT;

GO

-- ================================================================
-- PROBLEM 4: HIGH CPU USAGE
-- ================================================================
-- Impact: Server becomes unresponsive, other queries slow down
-- Alert Severity: HIGH (if CPU > 85%)
-- How to Trigger: Run this script
-- Expected in Dashboard: "High CPU: X% (threshold: 85%)"
--
-- NOTE: This may impact your system! Run on test/dev only.

PRINT '=== HIGH CPU LOAD ==='
PRINT 'Generating CPU load (will take ~30 seconds)...'

DECLARE @i INT = 0;
WHILE @i < 10000000
BEGIN
    SELECT @i = @i + 1;
    -- Every 1M iterations, the collector will see high CPU
    IF @i % 1000000 = 0
        PRINT 'Progress: ' + CAST(@i / 1000000 AS VARCHAR) + 'M iterations';
END

PRINT 'CPU load complete!'
GO

-- ================================================================
-- PROBLEM 5: TEMPDB PRESSURE
-- ================================================================
-- Impact: Slow queries, storage allocation delays
-- Alert Severity: MEDIUM to HIGH (if free space < 10GB)
-- How to Trigger: Run this script
-- Expected in Dashboard: "TempDB Free: X GB (threshold: < 10GB)"
--
-- NOTE: Creates many temporary tables. May require cleanup.

PRINT '=== TEMPDB PRESSURE ==='
PRINT 'Creating pressure on TempDB (will take ~1 minute)...'

DECLARE @i INT = 0;
WHILE @i < 50
BEGIN
    -- Create large temp table
    SELECT TOP 5000 *
    INTO #TempData
    FROM sys.all_columns ac1
    CROSS JOIN sys.all_columns ac2
    WHERE ac1.column_id <= 100;
    
    -- Do some work with it
    SELECT COUNT(*) FROM #TempData;
    
    -- Drop it
    DROP TABLE #TempData;
    
    SET @i = @i + 1;
    IF @i % 10 = 0
        PRINT 'Progress: ' + CAST(@i AS VARCHAR) + '/50';
END

PRINT 'TempDB pressure complete!'
GO

-- ================================================================
-- PROBLEM 6: MISSING INDEXES (Query Performance)
-- ================================================================
-- Impact: Slow queries due to table scans instead of index seeks
-- Alert Severity: MEDIUM
-- How to Trigger:
--   1. Create the table below (if not exists)
--   2. Run the query repeatedly
--   3. Click "Run Collector Now"
-- Expected in Dashboard: "Missing Index Recommendation: Create index on (Email)"

-- Create test table WITHOUT index on Email
IF OBJECT_ID('TestCustomers') IS NOT NULL
    DROP TABLE TestCustomers;

CREATE TABLE TestCustomers (
    Id INT PRIMARY KEY,
    Name VARCHAR(100),
    Email VARCHAR(100),  -- No index here!
    Status VARCHAR(50)
);

-- Insert test data (1000 rows)
DECLARE @i INT = 1;
WHILE @i <= 1000
BEGIN
    INSERT INTO TestCustomers VALUES (@i, 'User' + CAST(@i AS VARCHAR), 'user' + CAST(@i AS VARCHAR) + '@test.com', 'Active');
    SET @i = @i + 1;
END

PRINT '=== MISSING INDEX TEST ==='
PRINT 'Searching by Email (no index) - will be slow...'

-- Run this multiple times - will trigger missing index detection
SELECT * FROM TestCustomers WHERE Email = 'user500@test.com';

-- Create the index (solves the problem)
PRINT 'Creating index to fix the problem...'
CREATE INDEX idx_email ON TestCustomers(Email);

-- Now this is fast!
PRINT 'Same query now fast with index:'
SELECT * FROM TestCustomers WHERE Email = 'user750@test.com';

GO

-- ================================================================
-- PROBLEM 7: DEADLOCK (Circular Locking)
-- ================================================================
-- Impact: One session rolled back, error returned, data integrity risk
-- Alert Severity: CRITICAL
-- How to Trigger: 
--   This is tricky to create reliably. Try this sequence:
--   1. Run "DEADLOCK STEP 1" in Window 1
--   2. Immediately run "DEADLOCK STEP 2" in Window 2
--   3. Quickly run "DEADLOCK STEP 3" in Window 1 (after Step 2 starts)
--   4. Click "Run Collector Now" - may see deadlock victim error
--
-- NOTE: Deadlock detection is complex. If not detected, the collector
--       tries to read from system_health extended events.

-- --- DEADLOCK STEP 1 ---
PRINT '=== DEADLOCK ATTEMPT - STEP 1 ==='
BEGIN TRANSACTION;
    UPDATE Orders SET TotalAmount = 100 WHERE OrderId = 1;
    -- Keep lock on OrderId 1
    WAITFOR DELAY '00:00:05';
    UPDATE Orders SET TotalAmount = 200 WHERE OrderId = 2;
COMMIT;

-- --- DEADLOCK STEP 2 (run in parallel Window 2) ---
PRINT '=== DEADLOCK ATTEMPT - STEP 2 ==='
BEGIN TRANSACTION;
    UPDATE Orders SET TotalAmount = 300 WHERE OrderId = 2;
    -- Lock acquired on OrderId 2
    WAITFOR DELAY '00:00:02';
    -- Now try to lock OrderId 1 (which Step 1 holds) - DEADLOCK!
    UPDATE Orders SET TotalAmount = 400 WHERE OrderId = 1;
COMMIT;

GO

-- ================================================================
-- CLEANUP: Remove Test Objects
-- ================================================================
-- Run this to clean up after testing

PRINT '=== CLEANUP ==='

USE DBMonTest;
GO

IF OBJECT_ID('TestCustomers') IS NOT NULL
    DROP TABLE TestCustomers;

IF OBJECT_ID('Orders') IS NOT NULL
    DROP TABLE Orders;

IF OBJECT_ID('Customers') IS NOT NULL
    DROP TABLE Customers;

PRINT 'Tables cleaned up!'
PRINT ''
PRINT 'To completely remove the test database, run:'
PRINT '  USE master;'
PRINT '  DROP DATABASE DBMonTest;'

GO

-- ================================================================
-- SUMMARY OF PROBLEMS
-- ================================================================
-- 
-- Problem Type           | File/Section          | Severity | Signal
-- =====================================================================
-- Slow Query             | PROBLEM 1             | MEDIUM   | avg_elapsed > 20s
-- Blocking              | PROBLEM 2 (2 windows) | HIGH     | wait_time > 30s
-- Open Transaction      | PROBLEM 3             | MEDIUM   | duration > 3600s
-- High CPU              | PROBLEM 4             | HIGH     | CPU > 85%
-- TempDB Pressure       | PROBLEM 5             | MEDIUM   | free_space < 10GB
-- Missing Index         | PROBLEM 6             | MEDIUM   | table_scan_count
-- Deadlock              | PROBLEM 7 (2 windows) | CRITICAL | deadlock detected
--
-- ================================================================

