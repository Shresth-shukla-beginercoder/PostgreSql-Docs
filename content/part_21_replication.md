# PART 21: REPLICATION AND DISTRIBUTED DATABASE CONCEPTS

## 21.1 Replication in PostgreSQL

Replication creates one or more *copies* of a database cluster on separate machines, providing high availability (HA), read scaling, and disaster recovery (DR).

### Three Types of Replication

| Type | Mechanism | Use Case | Latency |
|---|---|---|---|
| **Physical Streaming Replication** | Binary WAL shipping | HA/DR, read replicas | Milliseconds (local) to seconds (cross-region) |
| **Logical Replication** | Row-level change stream (decoded WAL) | Selective table sync, heterogeneous targets, upgrades | Seconds to minutes |
| **Synchronous vs Asynchronous** | Commit waits for standby vs returns immediately | Zero data loss vs performance | Config-dependent |

## 21.2 Physical Streaming Replication (the default)

**How it works:**
1. Standby connects to primary as a replication client.
2. Primary streams WAL segments as they're generated.
3. Standby applies (replays) WAL continuously.
4. Result: byte-for-byte identical replica.

**Setup (simplified):**

```bash
# On PRIMARY (postgresql.conf):
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB        # or use replication slots

# Create replication user:
CREATE ROLE replicator REPLICATION LOGIN PASSWORD 'secure';

# pg_hba.conf on PRIMARY:
host replication replicator 192.168.1.0/24 scram-sha-256

# On STANDBY:
# 1. Base backup:
pg_basebackup -h primary.example.com -U replicator -D /var/lib/postgresql/17/standby -P -R

# The -R flag creates standby.signal + adds connection info to postgresql.auto.conf:
# primary_conninfo = 'host=primary.example.com port=5432 user=replicator password=...'

# 2. Start the standby:
pg_ctl start -D /var/lib/postgresql/17/standby
```

**Monitoring replication lag:**

```sql
-- On PRIMARY:
SELECT client_addr, state, sent_lsn, replay_lsn,
       pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- On STANDBY:
SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(),
       pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()) AS lag;
```

## 21.3 Synchronous vs Asynchronous Replication

| Mode | Behavior | Guarantee | Performance |
|---|---|---|---|
| **Async (default)** | COMMIT returns after local WAL write | Lag = seconds/minutes; data loss possible on primary crash | Fast |
| **Sync** | COMMIT waits for standby confirmation | Zero data loss (confirmed on N standbys) | Slower (network RTT) |

**Configuration:**

```sql
-- postgresql.conf on PRIMARY:
synchronous_commit = on                     -- or 'remote_apply' for read-after-write
synchronous_standby_names = 'standby1'      -- or 'FIRST 1 (standby1, standby2)' for quorum
```

**Trade-off:** synchronous replication protects against data loss but adds latency (network round-trip to the standby) to every commit.

## 21.4 Logical Replication (PostgreSQL 10+)

**How it differs from physical:**
- **Selective:** replicate specific *tables*, not the whole cluster.
- **Target:** can replicate into a *different* PostgreSQL version, or even non-PostgreSQL (with third-party tools).
- **Flexibility:** DDL is *not* replicated automatically (must run on both sides).

**Setup:**

```sql
-- On PUBLISHER (source):
CREATE PUBLICATION my_pub FOR TABLE orders, products;

-- On SUBSCRIBER (target):
CREATE SUBSCRIPTION my_sub
  CONNECTION 'host=publisher.example.com dbname=shopdb user=replicator password=...'
  PUBLICATION my_pub;
```

**Monitoring:**

```sql
-- On PUBLISHER:
SELECT * FROM pg_stat_replication WHERE application_name ~ 'my_sub';

-- On SUBSCRIBER:
SELECT subname, pid, received_lsn, latest_end_lsn, last_msg_send_time
FROM pg_stat_subscription;
```

**Use cases:**
- Major-version upgrades (logical replication from PG 14 → 17).
- Multi-tenant sharding (each tenant's tables replicated to separate subscribers).
- Selective data feeds (publish only `orders` to a data warehouse).

## 21.5 Failover and Switchover

### Failover (unplanned)
When the primary dies, promote a standby to primary:

```bash
# On the STANDBY (now becoming primary):
pg_ctl promote -D /var/lib/postgresql/17/standby

# Or from SQL (if the server is running):
SELECT pg_promote();
```

The standby stops replay, becomes writable, and diverges from the old primary. **Danger:** if the old primary comes back up, it's a *split-brain* (two primaries writing) — **never** restart the old primary as a primary; rebuild it as a standby.

### Switchover (planned)
1. Stop writes to primary (maintenance window).
2. Wait for standby to catch up (`pg_stat_replication.replay_lsn = sent_lsn`).
3. Promote standby.
4. Reconfigure old primary as a standby to the new primary.

**Orchestration tools:** `Patroni`, `repmgr`, `pg_auto_failover`, AWS RDS Multi-AZ (automatic).

## 21.6 Replication Slots

**Purpose:** guarantee that WAL needed by a standby is not recycled (prevent "WAL segment removed" errors).

```sql
-- On PRIMARY:
SELECT pg_create_physical_replication_slot('standby1_slot');

-- STANDBY's primary_slot_name in postgresql.auto.conf or recovery.conf:
primary_slot_name = 'standby1_slot'
```

**Monitoring (critical):**

```sql
SELECT slot_name, active, active_pid,
       pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_wal_bytes
FROM pg_replication_slots;
```

**Danger:** a broken/inactive slot retains WAL forever and **fills the disk**. Drop inactive slots: `SELECT pg_drop_replication_slot('slot_name');`.

## 21.7 Cascading Replication

Standby → Standby → Standby (tree topology). Reduces load on the primary.

```
PRIMARY ──→ STANDBY_1 ──→ STANDBY_2
         ──→ STANDBY_3
```

**Setup:** STANDBY_2's `primary_conninfo` points at STANDBY_1 (not PRIMARY).

## 21.8 Distributed Database Concepts

PostgreSQL is *single-node* (one writer). For *multi-writer* distributed systems:

### CAP Theorem
**Consistency, Availability, Partition Tolerance** — pick 2:
- **CP:** PostgreSQL (with synchronous replication) — consistent + partition-tolerant, but unavailable on network split.
- **AP:** DynamoDB, Cassandra — available + partition-tolerant, but eventually consistent.
- **CA:** Single-node databases (network partition → outage).

In practice: modern distributed SQL (CockroachDB, YugabyteDB) uses Raft/Paxos for **CP** with automatic failover.

### Eventual Consistency
**Async replication = eventual consistency:** standby may lag; a read from standby can return stale data.

**Solutions:**
- **Synchronous replication** (strong consistency).
- **Read-your-writes:** route reads to primary after a write.
- **Causal consistency** (application-level versioning).

### Two-Phase Commit (2PC)
Distributed transaction protocol: all participants PREPARE, then COMMIT (or ROLLBACK if any fail).

```sql
-- On each participant:
PREPARE TRANSACTION 'txn_123';

-- Coordinator collects votes, then:
COMMIT PREPARED 'txn_123';  -- or ROLLBACK PREPARED
```

**PostgreSQL supports 2PC** (`PREPARE TRANSACTION`) but rarely used (most apps use eventual consistency + idempotency).

### Sharding
Split data across multiple *independent* PostgreSQL clusters (horizontal scaling):
- **By tenant:** each customer's data on a separate cluster.
- **By range:** users 1-100K on shard1, 100K-200K on shard2.
- **By hash:** `user_id % N`.

**Challenges:**
- Cross-shard joins require application logic.
- Distributed transactions (2PC) or eventual consistency.
- Rebalancing shards on growth.

**Tools:** Citus (sharding extension for PostgreSQL), application-level sharding (microservices).

## 21.9 PostgreSQL vs Distributed SQL

| Feature | PostgreSQL | CockroachDB / YugabyteDB |
|---|---|---|
| **Writers** | 1 primary | Multiple (consensus-based) |
| **Consistency** | Strong (single-node) | Strong (Raft/Paxos) |
| **Horizontal write scaling** | No (sharding needed) | Yes |
| **Operational complexity** | Low | High |
| **Use case** | Most apps | Global, multi-region with high write throughput |

## 21.10 Interview Questions

- **Q:** Physical vs logical replication? **A:** Physical = whole cluster, byte-for-byte; logical = selective tables, row-level, cross-version.
- **Q:** Sync vs async replication? **A:** Sync = zero data loss, slower; async = fast, possible lag/data loss.
- **Q:** What is a replication slot? **A:** Guarantees WAL retention for a standby; prevents "WAL removed" errors but can fill disk if inactive.
- **Q:** How do you promote a standby? **A:** `pg_ctl promote` or `SELECT pg_promote();`.
- **Q:** What is split-brain? **A:** Two primaries accepting writes = data corruption. Fixed by fencing the old primary.
- **Q:** What is the CAP theorem? **A:** Consistency, Availability, Partition Tolerance — pick 2. PostgreSQL is CP (with sync replication).
- **Q:** What is 2PC? **A:** Two-phase commit: distributed transaction protocol (PREPARE + COMMIT).
- **Q:** How does sharding work? **A:** Split data across multiple clusters; application routes queries to the correct shard.
