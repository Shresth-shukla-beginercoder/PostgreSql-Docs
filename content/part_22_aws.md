# PART 22: AWS DATABASE ENGINEERING

> PostgreSQL on AWS spans five major services: **RDS for PostgreSQL**, **Aurora PostgreSQL**, **DynamoDB**, **Redshift**, and the glue (DMS, RDS Proxy, Secrets Manager). This part compares them, documents the RDS/Aurora-specific configuration surface, and gives migration and DR playbooks.

## 22.1 The AWS Database Ecosystem

| Service | Category | When to pick it |
|---|---|---|
| **RDS for PostgreSQL** | Managed OLTP | Most workloads; full PG feature set; simple operations |
| **Aurora PostgreSQL** | Managed OLTP (storage-scale) | High read volume, need for serverless scale, minimal failover impact |
| **DynamoDB** | NoSQL key-value/document | Massive horizontal scale, sub-millisecond p99, sparse writes |
| **Redshift** | OLAP warehouse | Aggregations over billions of rows, BI/reporting |
| **ElastiCache** | In-memory cache | Hot key/value, sessions, rate-limit counters |
| **DocumentDB** | Mongo-compatible | Existing Mongo codebases needing managed ops |
| **Neptune** | Graph | Relationship-heavy analytics (fraud, recommendation) |

**Rule of thumb:** default to RDS PostgreSQL; move to Aurora when *I/O or read concurrency* is the bottleneck; use DynamoDB/Redshift for genuinely different access patterns, not as a substitute for a bigger PG instance.

## 22.2 RDS for PostgreSQL — Key Features

**Managed:** patching, automated backups, point-in-time recovery (PITR up to 35 days), Multi-AZ, read replicas, parameter groups.

**Instance classes:** `db.t4g`/`db.m7g` (general), `db.r7g` (memory-optimized), `db.x2id` (extra large). Choose by RAM and IOPS, not marketing.

**Storage types:**
- **gp3** (default): baseline IOPS + burstable; the default for most.
- **io2/io1**: provisioned high IOPS/throughput for very hot OLTP.

**Multi-AZ (RDS):**
- AWS maintains a *synchronous* standby in a different AZ.
- Automatic failover on instance failure (typically < 120 s).
- Same endpoint; app reconnects.
- **Cost:** storage + I/O paid twice; standby is *not* for reads (single-AZ reads only, by default).

**Read Replicas (RDS):**
- Up to 5 per primary (Aurora: 15).
- Asynchronous; latency = WAL lag.
- Promotable to a primary (for DR or cutover).

**Parameter Groups:**
- `default.postgres17` is the base; copy and tune (`shared_buffers`, `work_mem`, `max_connections`).
- Some params require a *restart* (check the "restart required" flag in the console).

**Backups and PITR:**
- Automated backups (snapshots) + continuous WAL.
- Retention: 1–35 days.
- PITR: restore to any second in the retention window.
- Manual snapshots: unlimited, non-versioned.

**Security:**
- VPC + Security Groups (inbound 5432 from app SG only).
- **IAM Auth** (app ↔ RDS) avoids stored passwords.
- **Secrets Manager** stores credentials; app fetches at runtime (rotated).
- **Encryption:** at-rest (KMS), in-transit (TLS required via `rds_force_ssl` for PG13+).

## 22.3 Aurora PostgreSQL — What's Different

**Storage:**
- 6 copies of data across 3 AZs (12 disks in total).
- Storage scales automatically up to 128 TB.
- **Shared storage:** read replicas read the *same* storage (not a WAL replica) → near-zero replication lag.

**Compute:**
- Single-node or multi-node (up to 15 readers).
- **Aurora Serverless v2:** scales in ACU (Amazon Capacity Units); no `shared_buffers` tuning needed (memory auto-scales); scales down to near-zero for idle workloads.

**Failover:**
- Multi-node (or Serverless v2) failover is *fast* (typically 15–30 s) because readers don't need to catch up on WAL (shared storage).

**PostgreSQL compatibility:**
- Aurora PostgreSQL 15/17 supports most PG extensions (`pg_stat_statements`, `pg_repack` not included; `plv8` not supported).
- Some features are *not* supported: `pg_basebackup` (use `rds_backup`), `wal_level = logical` is fine, `CREATE ROLE ... SUPERUSER` not allowed.

**Cost model:**
- Compute is billed per ACU-hour (Serverless) or instance-hour (provisioned).
- Storage is billed per GB-month (typically 3× the price of gp3).

## 22.4 RDS Proxy

**What it is:** a managed connection pooler *in front of* RDS/Aurora.

**When to use:**
- Connection churn from serverless / containerized apps (ECS/Lambda).
- Application can't use `max_connections` headroom.
- Need for credential rotation without app restart.

**What it does:**
- Pools and reuses physical connections.
- Supports IAM authentication for credential rotation.
- Does *not* understand SQL (unlike PgBouncer) — it's a pass-through pooler.

**Limitations:**
- Adds ~1 ms of latency (network hop).
- Cannot do query-level routing (unlike PgBouncer in transaction mode).
- No built-in read-replica routing (you must configure it per-endpoint).

## 22.5 Database Migration Service (DMS)

**What it does:** replicates data from source (Oracle, SQL Server, MySQL, self-managed PG) to target (RDS, Aurora, or self-managed), with *continuous* change-data-capture (CDC) to minimize cutover.

**Two phases:**
1. **Full load** (initial snapshot).
2. **CDC** (ongoing changes via WAL / change logs).

**Cutover checklist:**
1. DMS is in "caught up" state (CDC lag ≈ 0).
2. Freeze writes on source (maintenance window).
3. Run a final DMS sync.
4. Verify row counts + checksums on a sample.
5. Point the app at the target; test a few critical transactions.
6. Monitor DMS for stragglers; keep the source available for rollback.

**SCT (Schema Conversion Tool):**
- Converts DDL from Oracle/SQL Server to PostgreSQL.
- Handles type mapping (NUMBER → NUMERIC, CLOB → TEXT), syntax differences (NVL → COALESCE), and pl/sql → plpgsql (manual review needed).

## 22.6 Performance Monitoring

**CloudWatch metrics (RDS/Aurora):**
- `CPUUtilization`, `FreeableMemory`, `DatabaseConnections`, `SwapUsage`.
- `ReadIOPS`, `WriteIOPS`, `ReadThroughput`, `WriteThroughput`.
- `FreeStorageSpace` (disk full = outage).
- `ReplicationLag` (read replicas).
- `DBClusterCacheHitRatio` (Aurora).

**Performance Insights (PI):**
- **AAS (Average Active Sessions):** the single most useful metric.
  - AAS ≈ 1 → database is idle.
  - AAS ≈ cores/2 → database is saturated.
- **Workload breakdown:** by user, by SQL statement, by wait event.
- **Diagnosis:** find the exact query that caused an incident (no app logs needed).

**pg_stat_statements on RDS/Aurora:**
- Enabled by default in Aurora; on RDS, load via `shared_preload_libraries`.
- Query: `SELECT query, calls, total_exec_time FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 25;`

## 22.7 High Availability and DR on AWS

**HA (Multi-AZ):**
- RDS Multi-AZ or Aurora Multi-Node.
- RPO ≈ 0 (synchronous), RTO ≈ minutes.

**DR (Cross-Region):**
- **Option A:** Aurora Global Database (multi-active, read/write in up to 5 regions).
- **Option B:** RDS Read Replica in a different region (asynchronous; RPO = lag; RTO = promotion time).
- **Option C:** PITR from automated backups in a different region (RPO = backup interval; RTO = restore time).

**Cost vs RPO/RTO trade-off:**

| Strategy | RPO | RTO | Cost |
|---|---|---|---|
| Multi-AZ (same region) | ~0 | Minutes | Low |
| Aurora Global (multi-region) | ~0 | Seconds–minutes | High |
| Cross-region read replica | Seconds–minutes | Minutes | Medium |
| PITR from S3 backup | Minutes–hours | Hours | Low |

## 22.8 Interview Questions (AWS Database)

- **Q:** RDS vs Aurora? **A:** RDS = managed PG on EC2 (provisioned I/O, WAL-based replication). Aurora = cloud-native (shared storage, 6 copies, faster failover, serverless compute).
- **Q:** How to scale a write-heavy RDS workload? **A:** Vertical (bigger instance) → Aurora (I/O headroom) → application sharding or read/write splitting.
- **Q:** What is Multi-AZ? **A:** Synchronous standby in a different AZ; automatic failover; same endpoint; storage/I/O cost × 2.
- **Q:** Read replica lag? **A:** Asynchronous; monitor `pg_last_wal_replay_lsn()` on the replica; route post-write reads to primary.
- **Q:** What is RDS Proxy? **A:** Managed connection pooler; solves connection churn for serverless apps; adds ~1 ms; not a query router.
- **Q:** How do you do a zero-downtime migration to Aurora? **A:** DMS full load + CDC, freeze writes, final sync, verify, cutover; keep source for rollback.
- **Q:** RPO/RTO of Aurora Global vs PITR? **A:** Global ≈ 0/seconds (multi-active); PITR ≈ backup interval/restore time (typically 15 min / 30 min–2 h).
- **Q:** How do you monitor a RDS incident? **A:** CloudWatch (AAS, I/O, connections), Performance Insights (top queries), `pg_stat_activity` for blocking, `pg_locks` for deadlocks.
- **Q:** What is Aurora Serverless v2? **A:** Auto-scaling compute in ACUs; scales to near-zero when idle; no `shared_buffers` tuning; ideal for spiky workloads.
- **Q:** IAM Auth for RDS? **A:** App uses an IAM role to get a short-lived token; no stored password; reduces credential sprawl.

## 22.9 Practical: Deploying a Production RDS PostgreSQL

```text
1. VPC: 2 public + 2 private subnets (2 AZs).
2. DB Subnet Group: use the private subnets.
3. RDS instance: db.m7g.large (2 vCPU / 8 GB), gp3 storage, 500 GB.
4. Multi-AZ: enabled (for HA).
5. Parameter Group: tune shared_buffers, work_mem.
6. Security Group: allow 5432 from app SG only.
7. Secrets Manager: store credentials; app fetches at boot.
8. Performance Insights: enable; set AAS alarm.
9. Automated backups: 35 days PITR.
10. Monitoring: CloudWatch alarms on FreeableMemory, SwapUsage, ReplicationLag.
```
