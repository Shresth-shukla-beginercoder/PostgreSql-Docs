# PART 13: TRANSACTIONS AND ACID

## 13.1 ACID Properties

| Property | Meaning | PostgreSQL Implementation |
|---|---|---|
| **Atomicity** | All-or-nothing | `COMMIT`/`ROLLBACK` |
| **Consistency** | Constraints are preserved | Constraint checks at commit |
| **Isolation** | Concurrent transactions don't interfere | MVCC + lock modes |
| **Durability** | Committed data survives crashes | WAL (Write-Ahead Log) |

## 13.2 BEGIN / COMMIT / ROLLBACK

```sql
BEGIN;
UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;
UPDATE accounts SET balance = balance + 500 WHERE user_id = 2;
COMMIT;

-- Or in one statement:
BEGIN;
  UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;
  UPDATE accounts SET balance = balance + 500 WHERE user_id = 2;
COMMIT;
```

**Autocommit:** psql's default (`autocommit = on`).

## 13.3 SAVEPOINT / ROLLBACK TO SAVEPOINT

```sql
BEGIN;
  INSERT INTO orders ...;
  SAVEPOINT before_payment;
  INSERT INTO payments ...;
  IF payment_failed THEN ROLLBACK TO SAVEPOINT before_payment;
COMMIT;
```

## 13.4 Isolation Levels

| Level | Dirty Reads | Non-Repeatable Reads | Phantom Reads | Serialization Failures |
|---|---|---|---|---|
| **READ UNCOMMITTED** | Yes | Yes | Yes | Yes |
| **READ COMMITTED** | No | Yes | Yes | Yes |
| **REPEATABLE READ** | No | No | Yes | Yes |
| **SERIALIZABLE** | No | No | No | No |

**PostgreSQL's actual implementation:**
- `READ UNCOMMITTED` → `READ COMMITTED` (no dirty reads).
- `SERIALIZABLE` → strict two-phase locking (no phantom reads).

## 13.5 MVCC and Visibility

- **MVCC:** each row version has `xmin`/`xmax` (transaction IDs).
- **Visibility rule:** a row is visible if `xmin < current_tx_id < xmax`.

```sql
-- A row's visibility timeline
Row: xmin=10, xmax=15

Tx 10: visible (xmin=10)
Tx 11: visible (xmin=10, xmax=15)
Tx 15: invisible (xmax=15)
```

## 13.6 Transaction Logs and WAL

- **WAL (Write-Ahead Log):** sequential file of all changes.
- **Checkpoints:** WAL is flushed to disk periodically.
- **Recovery:** on crash, PostgreSQL replays WAL to restore consistency.

## 13.7 Commit Durability

- **`fsync`:** WAL is flushed to disk (default).
- **`synchronous_commit`:** `on` (default) → wait for WAL write; `off` → return immediately (risky).

```sql
SET synchronous_commit = off;   -- faster commits, but risk of data loss
```

## 13.8 Dirty Reads, Non-Repeatable Reads, Phantom Reads

| Problem | Description | Fix |
|---|---|---|
| **Dirty Read** | Read uncommitted data | Use `READ COMMITTED` or higher |
| **Non-Repeatable Read** | Same query returns different data | Use `REPEATABLE READ` or `SERIALIZABLE` |
| **Phantom Read** | New rows appear in repeated queries | Use `SERIALIZABLE` |

## 13.9 Lost Updates

**Problem:** two transactions read the same value and both update it.

```sql
-- Tx 1
BEGIN;
SELECT balance FROM accounts WHERE user_id = 1;   -- balance = 1000
UPDATE accounts SET balance = 1000 - 500 WHERE user_id = 1;
COMMIT;

-- Tx 2 (runs concurrently)
BEGIN;
SELECT balance FROM accounts WHERE user_id = 1;   -- balance = 1000
UPDATE accounts SET balance = 1000 - 300 WHERE user_id = 1;
COMMIT;
```

**Result:** balance = 700 (should be 200).

**Fix:** `SELECT ... FOR UPDATE` (row lock).

## 13.10 Write Skew

**Problem:** two transactions read the same state and write conflicting updates.

```sql
-- Tx 1: transfer $500 from A to B
BEGIN;
SELECT balance FROM accounts WHERE user_id IN (1, 2);
UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;
UPDATE accounts SET balance = balance + 500 WHERE user_id = 2;
COMMIT;

-- Tx 2: transfer $300 from B to A
BEGIN;
SELECT balance FROM accounts WHERE user_id IN (1, 2);
UPDATE accounts SET balance = balance - 300 WHERE user_id = 2;
UPDATE accounts SET balance = balance + 300 WHERE user_id = 1;
COMMIT;
```

**Result:** possible final state: A=800, B=800 (should be A=1000, B=1000).

**Fix:** `SERIALIZABLE` isolation (PostgreSQL detects and rolls back one tx).

## 13.11 Serialization Failures

**Problem:** two transactions conflict at commit time.

```sql
-- Tx 1
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT balance FROM accounts WHERE user_id = 1;
-- ...
COMMIT;

-- Tx 2 (runs concurrently)
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT balance FROM accounts WHERE user_id = 1;
-- ...
COMMIT;   -- ERROR: could not serialize access due to concurrent update
```

**Fix:** retry the transaction (idempotent operations).

## 13.12 Retry Logic

```js
// Node.js example with exponential backoff
async function transferMoney(from, to, amount) {
  const maxRetries = 3;
  let retryCount = 0;

  while (retryCount < maxRetries) {
    try {
      await client.query('BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE');
      const { rows } = await client.query(
        'SELECT balance FROM accounts WHERE user_id = $1 FOR UPDATE', [from]
      );
      if (rows[0].balance < amount) {
        throw new Error('Insufficient funds');
      }
      await client.query(
        'UPDATE accounts SET balance = balance - $1 WHERE user_id = $2', [amount, from]
      );
      await client.query(
        'UPDATE accounts SET balance = balance + $1 WHERE user_id = $2', [amount, to]
      );
      await client.query('COMMIT');
      return;
    } catch (err) {
      await client.query('ROLLBACK');
      if (err.code === '40001' && retryCount < maxRetries) {  // serialization_failure
        retryCount++;
        await new Promise(resolve => setTimeout(resolve, 100 * Math.pow(2, retryCount)));
      } else {
        throw err;
      }
    }
  }
}
```

## 13.13 Lock Contention

**Problem:** too many row locks → contention.

**Diagnosis:**

```sql
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid;
```

**Fix:**
- Reduce transaction duration.
- Use `NOWAIT` to fail fast.
- Optimize queries to hold locks for less time.
- Use `SKIP LOCKED` for job queues.

## 13.14 Two-Phase Commit (PREPARE TRANSACTION)

```sql
-- Phase 1: prepare
BEGIN;
UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;
PREPARE TRANSACTION 'transfer_123';

-- Phase 2: commit
COMMIT PREPARED 'transfer_123';
```

**Use case:** distributed transactions (e.g., bank transfer across databases).

## 13.15 Practical Banking Transaction Example

```sql
-- Transfer $500 from account 1 to account 2
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- Check balances
SELECT balance FROM accounts WHERE user_id IN (1, 2) FOR UPDATE;

-- Debit source
UPDATE accounts SET balance = balance - 500 WHERE user_id = 1;

-- Credit destination
UPDATE accounts SET balance = balance + 500 WHERE user_id = 2;

-- Record the transfer
INSERT INTO transfers (from_id, to_id, amount, status)
VALUES (1, 2, 500, 'completed');

COMMIT;
```

## 13.16 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| What are the ACID properties? | Atomicity, Consistency, Isolation, Durability |
| What does `BEGIN` do? | Starts a transaction |
| What is MVCC? | Multi-Version Concurrency Control (row versions with xmin/xmax) |
| What is a dirty read? | Reading uncommitted data (not possible in PostgreSQL) |
| What is a non-repeatable read? | Same query returns different data (fixed by REPEATABLE READ) |
| What is a phantom read? | New rows appear in repeated queries (fixed by SERIALIZABLE) |
| What is a serialization failure? | Two transactions conflict at commit time (fixed by retry) |
| What is a lost update? | Two transactions read the same value and both update it (fixed by FOR UPDATE) |
| What is write skew? | Two transactions read the same state and write conflicting updates (fixed by SERIALIZABLE) |
| What is a two-phase commit? | PREPARE TRANSACTION followed by COMMIT PREPARED |
