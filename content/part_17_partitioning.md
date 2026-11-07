# PART 17: PARTITIONING AND LARGE DATABASES

## 17.1 Partitioning Basics

**Purpose:** split a large table into smaller, more manageable pieces.

**Types of partitioning:**
- **Range:** split by value ranges (dates, IDs).
- **List:** split by discrete values (regions, categories).
- **Hash:** split by hash of a column (even distribution).

## 17.2 Declarative Partitioning (PostgreSQL 10+)

```sql
CREATE TABLE measurements (
  log_date date NOT NULL,
  city_id int NOT NULL,
  peak_temp int,
  avg_temp int
) PARTITION BY RANGE (log_date);

-- Create partitions
CREATE TABLE measurements_y2026m01 PARTITION OF measurements
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE measurements_y2026m02 PARTITION OF measurements
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

## 17.3 Range Partitioning

**Use cases:**
- Time-series data (logs, metrics).
- Large tables with natural ranges (order dates, event timestamps).

**Example:**

```sql
CREATE TABLE orders (
  order_id bigint NOT NULL,
  customer_id int NOT NULL,
  order_date date NOT NULL,
  amount numeric(10,2)
) PARTITION BY RANGE (order_date);

-- Create monthly partitions
CREATE TABLE orders_y2026m01 PARTITION OF orders
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE orders_y2026m02 PARTITION OF orders
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

## 17.4 List Partitioning

**Use cases:**
- Categorical data (regions, product categories).
- Fixed, discrete values.

**Example:**

```sql
CREATE TABLE sales (
  sale_id bigint NOT NULL,
  region text NOT NULL,
  amount numeric(10,2)
) PARTITION BY LIST (region);

-- Create partitions
CREATE TABLE sales_east PARTITION OF sales
  FOR VALUES IN ('NY', 'NJ', 'CT');

CREATE TABLE sales_west PARTITION OF sales
  FOR VALUES IN ('CA', 'OR', 'WA');
```

## 17.5 Hash Partitioning

**Use cases:**
- Even distribution across partitions.
- No natural range or list.

**Example:**

```sql
CREATE TABLE users (
  user_id bigint NOT NULL,
  name text,
  email text
) PARTITION BY HASH (user_id);

-- Create partitions
CREATE TABLE users_p1 PARTITION OF users
  FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE users_p2 PARTITION OF users
  FOR VALUES WITH (MODULUS 4, REMAINDER 1);
```

## 17.6 Multi-Level Partitioning

**Use cases:**
- Large tables with multiple dimensions (time + region).

**Example:**

```sql
CREATE TABLE events (
  event_id bigint NOT NULL,
  event_time timestamptz NOT NULL,
  region text NOT NULL,
  data jsonb
) PARTITION BY RANGE (event_time);

-- Create time partitions
CREATE TABLE events_y2026 PARTITION OF events
  FOR VALUES FROM ('2026-01-01') TO ('2027-01-01')
  PARTITION BY LIST (region);

-- Create region partitions
CREATE TABLE events_y2026_east PARTITION OF events_y2026
  FOR VALUES IN ('NY', 'NJ', 'CT');

CREATE TABLE events_y2026_west PARTITION OF events_y2026
  FOR VALUES IN ('CA', 'OR', 'WA');
```

## 17.7 Partition Pruning

**How it works:**
- The planner eliminates non-matching partitions from the query plan.
- Only relevant partitions are scanned.

**Example:**

```sql
-- Only scans orders_y2026m01
SELECT * FROM orders WHERE order_date BETWEEN '2026-01-01' AND '2026-01-31';
```

## 17.8 Partition Maintenance

### Attach and Detach Partitions

```sql
-- Detach a partition
ALTER TABLE measurements DETACH PARTITION measurements_y2026m01;

-- Attach a partition
ALTER TABLE measurements ATTACH PARTITION measurements_y2026m01
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### Default Partition

```sql
-- Create a default partition for future data
CREATE TABLE measurements_default PARTITION OF measurements
  DEFAULT;
```

## 17.9 Partitioned Indexes

```sql
-- Create a global index (applies to all partitions)
CREATE INDEX idx_orders_customer ON orders (customer_id);

-- Create a local index (applies to a specific partition)
CREATE INDEX idx_orders_y2026m01_customer ON orders_y2026m01 (customer_id);
```

## 17.10 Partition Constraints

```sql
-- Partition-specific constraints
CREATE TABLE orders_y2026m01 PARTITION OF orders
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')
  WITH (tablespace = fastdisk);
```

## 17.11 Practical Examples

### 1. Time-Series Data (Logs)

```sql
CREATE TABLE logs (
  log_id bigserial NOT NULL,
  log_time timestamptz NOT NULL,
  level text NOT NULL,
  message text NOT NULL
) PARTITION BY RANGE (log_time);

-- Create daily partitions
CREATE TABLE logs_y2026m01d01 PARTITION OF logs
  FOR VALUES FROM ('2026-01-01') TO ('2026-01-02');

CREATE TABLE logs_y2026m01d02 PARTITION OF logs
  FOR VALUES FROM ('2026-01-02') TO ('2026-01-03');
```

### 2. Sales Data by Region

```sql
CREATE TABLE sales (
  sale_id bigserial NOT NULL,
  region text NOT NULL,
  amount numeric(10,2) NOT NULL,
  sale_time timestamptz NOT NULL
) PARTITION BY LIST (region);

-- Create region partitions
CREATE TABLE sales_east PARTITION OF sales
  FOR VALUES IN ('NY', 'NJ', 'CT');

CREATE TABLE sales_west PARTITION OF sales
  FOR VALUES IN ('CA', 'OR', 'WA');
```

### 3. User Data by Hash

```sql
CREATE TABLE users (
  user_id bigint NOT NULL,
  name text,
  email text
) PARTITION BY HASH (user_id);

-- Create hash partitions
CREATE TABLE users_p1 PARTITION OF users
  FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE users_p2 PARTITION OF users
  FOR VALUES WITH (MODULUS 4, REMAINDER 1);
```

### 4. Multi-Level Partitioning (Time + Region)

```sql
CREATE TABLE events (
  event_id bigint NOT NULL,
  event_time timestamptz NOT NULL,
  region text NOT NULL,
  data jsonb
) PARTITION BY RANGE (event_time);

-- Create time partitions
CREATE TABLE events_y2026 PARTITION OF events
  FOR VALUES FROM ('2026-01-01') TO ('2027-01-01')
  PARTITION BY LIST (region);

-- Create region partitions
CREATE TABLE events_y2026_east PARTITION OF events_y2026
  FOR VALUES IN ('NY', 'NJ', 'CT');

CREATE TABLE events_y2026_west PARTITION OF events_y2026
  FOR VALUES IN ('CA', 'OR', 'WA');
```

### 5. Partitioning for Large Tables

```sql
CREATE TABLE orders (
  order_id bigint NOT NULL,
  customer_id int NOT NULL,
  order_date date NOT NULL,
  amount numeric(10,2)
) PARTITION BY RANGE (order_date);

-- Create monthly partitions
CREATE TABLE orders_y2026m01 PARTITION OF orders
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE orders_y2026m02 PARTITION OF orders
  FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

## 17.12 Partitioning vs Sharding

| Feature | Partitioning | Sharding |
|---|---|---|
| **Definition** | Splitting a table into smaller tables within the same database | Splitting data across multiple databases or servers |
| **Querying** | Single query across partitions | Requires application logic to query multiple shards |
| **Joins** | Efficient (within the same database) | Inefficient (cross-shard joins are expensive) |
| **Scalability** | Vertical (within one database) | Horizontal (across multiple databases) |
| **Consistency** | Strong (ACID transactions) | Eventual (requires application-level coordination) |
| **Use case** | Large tables within a single database | Distributed systems, high write throughput |

## 17.13 Common Mistakes

1. **Not using declarative partitioning** → manual partition management.
2. **Choosing the wrong partition key** → poor pruning efficiency.
3. **Forgetting to create indexes on partitions** → slow queries on large partitions.
4. **Assuming all queries will use the partition key** → queries on non-partitioned columns scan all partitions.
5. **Not creating a default partition** → inserts fail for out-of-range values.
6. **Ignoring partition maintenance** → partitions grow without bound.
7. **Using list partitioning for continuous ranges** → range partitioning is better.
8. **Assuming hash partitioning is for load balancing** → it's for even distribution, not performance.
9. **Not testing partition pruning** → queries may scan all partitions.
10. **Ignoring the impact on autovacuum** → partitions need separate autovacuum settings.

## 17.14 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| What is partitioning? | Splitting a large table into smaller, more manageable pieces |
| What are the types of partitioning? | Range, list, hash |
| What is partition pruning? | The planner eliminates non-matching partitions from the query plan |
| What is a default partition? | A partition that catches out-of-range values |
| What is a partitioned index? | An index that applies to all partitions (global) or a specific partition (local) |
| What is the difference between partitioning and sharding? | Partitioning is within a single database; sharding is across multiple databases |
| What is multi-level partitioning? | Partitioning by multiple dimensions (e.g., time + region) |
| What is a partition key? | The column used to determine which partition a row belongs to |
| What is a partition constraint? | A constraint that applies to a specific partition |
| What is a partition maintenance? | Managing partitions (creating, attaching, detaching, dropping) |
