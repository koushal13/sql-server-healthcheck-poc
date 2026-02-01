-- ================================================================
-- DBMon Test Database Setup
-- ================================================================
-- This script creates a dedicated database for DBMon testing.
-- BEST PRACTICE: Don't use master or other system databases!
-- ================================================================

-- Step 1: Check if database already exists
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'DBMonTest')
BEGIN
    PRINT '⚠️  Database DBMonTest already exists'
    PRINT '   Dropping and recreating...'
    
    -- Set to single user to drop all connections
    ALTER DATABASE DBMonTest SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE DBMonTest;
    
    PRINT '✅ Old database dropped'
END
GO

-- Step 2: Create new database
CREATE DATABASE DBMonTest
GO

PRINT '✅ Database DBMonTest created successfully!'
GO

-- Step 3: Switch to new database
USE DBMonTest;
GO

-- Step 4: Verify we're in the right database
SELECT 
    DB_NAME() AS CurrentDatabase,
    SUSER_SNAME() AS CurrentUser,
    GETDATE() AS CreatedAt;
GO

PRINT ''
PRINT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
PRINT '✅ DATABASE READY!'
PRINT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
PRINT ''
PRINT 'You are now in the DBMonTest database.'
PRINT 'All test tables and queries will be created here.'
PRINT ''
PRINT 'NEXT STEPS:'
PRINT '  1. Run the table creation script'
PRINT '  2. Or run DETAILED_PROBLEMS.sql (it creates tables automatically)'
PRINT ''
PRINT 'To connect from VS Code or other tools:'
PRINT '  Server: localhost,1433'
PRINT '  Database: DBMonTest  ← Use this instead of master'
PRINT '  User: sa'
PRINT '  Password: (your Docker password)'
PRINT ''
GO

-- Step 5: Create basic tables for testing
PRINT 'Creating sample tables...'
GO

CREATE TABLE Orders (
    OrderId INT PRIMARY KEY IDENTITY(1,1),
    CustomerId INT,
    OrderDate DATETIME DEFAULT GETDATE(),
    TotalAmount DECIMAL(10,2),
    Status VARCHAR(50) DEFAULT 'New'
);
GO

CREATE TABLE Customers (
    CustomerId INT PRIMARY KEY IDENTITY(1,1),
    CustomerName VARCHAR(100),
    Email VARCHAR(100),
    Phone VARCHAR(20)
);
GO

PRINT '✅ Tables created: Orders, Customers'
GO

-- Step 6: Insert sample data
PRINT 'Inserting sample data...'
GO

INSERT INTO Customers (CustomerName, Email, Phone) VALUES 
    ('John Doe', 'john@example.com', '555-1234'),
    ('Jane Smith', 'jane@example.com', '555-5678'),
    ('Bob Johnson', 'bob@example.com', '555-9999');

INSERT INTO Orders (CustomerId, OrderDate, TotalAmount, Status) VALUES 
    (1, GETDATE(), 100.00, 'New'),
    (2, GETDATE(), 250.50, 'Pending'),
    (3, GETDATE(), 75.25, 'Completed'),
    (1, GETDATE(), 150.00, 'Processing'),
    (2, GETDATE(), 300.75, 'Shipped'),
    (3, GETDATE(), 125.50, 'Delivered');

PRINT '✅ Sample data inserted'
GO

-- Step 7: Verify setup
PRINT ''
PRINT 'Verifying setup...'
GO

SELECT 
    'Orders' AS TableName, 
    COUNT(*) AS RowCount 
FROM Orders
UNION ALL
SELECT 
    'Customers' AS TableName, 
    COUNT(*) AS RowCount 
FROM Customers;
GO

PRINT ''
PRINT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
PRINT '🎉 SETUP COMPLETE!'
PRINT '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
PRINT ''
PRINT 'Database: DBMonTest'
PRINT 'Tables: Orders (6 rows), Customers (3 rows)'
PRINT ''
PRINT 'You can now:'
PRINT '  ✅ Run queries from DETAILED_PROBLEMS.sql'
PRINT '  ✅ Connect from VS Code using database "DBMonTest"'
PRINT '  ✅ Test dashboard monitoring'
PRINT ''
PRINT 'To drop this database later:'
PRINT '  USE master;'
PRINT '  DROP DATABASE DBMonTest;'
PRINT ''
GO
