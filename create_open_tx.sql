-- Create a new open transaction for testing
USE DBMonTest;
GO

BEGIN TRANSACTION;

UPDATE Orders 
SET total_amount = 1000 
WHERE order_id = 1;

-- Keep transaction open - do NOT commit
SELECT 
    session_id, 
    transaction_id,
    DATEDIFF(SECOND, transaction_begin_time, GETDATE()) as age_seconds
FROM sys.dm_tran_active_transactions t
JOIN sys.dm_tran_session_transactions st ON t.transaction_id = st.transaction_id
WHERE session_id = @@SPID;

PRINT 'Transaction is open. Run ROLLBACK or COMMIT to close it.';
WAITFOR DELAY '00:10:00';  -- Keep it open for 10 minutes
ROLLBACK;  -- Auto-rollback after 10 min
