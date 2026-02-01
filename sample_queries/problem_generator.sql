-- DBMon Test Scripts - SQL Server Problem Generator
-- Run these scripts to create various problems that will be captured by the collector

-- ========================================
-- 1. CREATE OPEN TRANSACTIONS
-- ========================================
-- Run this in one window and keep it open:
BEGIN TRANSACTION;
UPDATE Orders SET Status = 'Processing' WHERE OrderId = 1;
-- Keep this window open to simulate long-running transaction
-- COMMIT; -- Don't commit yet, let it hang to trigger alerts


-- ========================================
-- 2. CREATE BLOCKING SCENARIO
-- ========================================
-- Window 1: Start transaction and lock resource
BEGIN TRANSACTION;
UPDATE Orders SET Status = 'Locked' WHERE OrderId = 2;
-- Don't commit, keep holding the lock


-- Window 2: Try to access same resource (will be blocked)
BEGIN TRANSACTION;
UPDATE Orders SET Status = 'Waiting' WHERE OrderId = 2;
-- This will be blocked by Window 1's lock


-- ========================================
-- 3. CREATE SLOW RUNNING QUERY
-- ========================================
-- This query will be captured as slow:
SELECT TOP 10000
    o.OrderId,
    o.OrderDate,
    o.CustomerId,
    o.TotalAmount,
    c.CustomerName,
    c.Email,
    c.Phone
INTO #SlowQueryResult
FROM Orders o
CROSS JOIN Orders o2
CROSS JOIN Orders o3
LEFT JOIN Customers c ON o.CustomerId = c.CustomerId
WHERE o.OrderDate > '2020-01-01'
ORDER BY o.OrderDate DESC;

DROP TABLE #SlowQueryResult;


-- ========================================
-- 4. CREATE TEMPDB PRESSURE
-- ========================================
-- This creates pressure on TempDB:
DECLARE @i INT = 0;
WHILE @i < 100
BEGIN
    SELECT TOP 10000 *
    INTO #TempData
    FROM sys.all_columns ac1
    CROSS JOIN sys.all_columns ac2
    WHERE ac1.column_id <= 100;
    
    DROP TABLE #TempData;
    SET @i = @i + 1;
END


-- ========================================
-- 5. CREATE HIGH CPU LOAD
-- ========================================
-- Run this to generate CPU load:
DECLARE @i INT = 0;
WHILE @i < 1000000
BEGIN
    SELECT @i = @i + 1;
END


-- ========================================
-- 6. CREATE MISSING INDEX SCENARIO
-- ========================================
-- Create table without index on frequently searched column:
IF OBJECT_ID('TestTable') IS NOT NULL
    DROP TABLE TestTable;

CREATE TABLE TestTable (
    Id INT PRIMARY KEY,
    Name VARCHAR(100),
    Email VARCHAR(100),
    Status VARCHAR(50)
);

-- Insert test data
DECLARE @i INT = 1;
WHILE @i <= 1000
BEGIN
    INSERT INTO TestTable VALUES (@i, 'User' + CAST(@i AS VARCHAR), 'user' + CAST(@i AS VARCHAR) + '@test.com', 'Active');
    SET @i = @i + 1;
END

-- Run this repeatedly to trigger "missing index" detection:
SELECT * FROM TestTable WHERE Email = 'user500@test.com';


-- ========================================
-- CLEANUP (run when done testing)
-- ========================================
-- Cleanup script:
/*
DROP TABLE IF EXISTS TestTable;
DROP TABLE IF EXISTS #TempData;
DROP TABLE IF EXISTS #SlowQueryResult;
*/
