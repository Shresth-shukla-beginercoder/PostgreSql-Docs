# PART 23: OTHER DATABASE TECHNOLOGIES USED IN INDUSTRY

## 1. The Relational Landscape (SQL)
While PostgreSQL is excellent, other relational databases have specific niches.

### 1.1 MySQL & MariaDB
- **Focus:** Simplicity and high-performance reads for web applications.
- **Key Difference:** MySQL has a "pluggable" storage engine architecture (InnoDB, MyISAM).
- **When to use:** Standard LAMP stack applications, WordPress, very simple schemas.

### 1.2 Oracle & SQL Server
- **Focus:** Enterprise features, legacy support, and deep integration with ecosystem tools.
- **Cost:** Significantly higher licensing costs compared to open-source PostgreSQL.

### 1.3 Distributed SQL (CockroachDB, YugabyteDB)
- **Focus:** "Spanner-like" global consistency and horizontal write scaling.
- **PostgreSQL Compatibility:** YugabyteDB is built on PostgreSQL code; CockroachDB implements the PostgreSQL wire protocol.

## 2. NoSQL Databases
Used when the relational model is not the best fit.

### 2.1 Key-Value & Document (DynamoDB, MongoDB)
- **Use Case:** Flexible schemas, extreme horizontal scale, session management.
- **PostgreSQL Comparison:** Use `JSONB` in PostgreSQL for document storage unless you need the specific scaling properties of MongoDB/DynamoDB.

### 2.2 In-Memory (Redis)
- **Use Case:** Caching, message queues, real-time leaderboards.
- **Speed:** Sub-millisecond latency.

## 3. Analytical & Data Warehousing (OLAP)
PostgreSQL is optimized for OLTP (Online Transactional Processing). For OLAP, specialized engines are better.

### 3.1 Snowflake & BigQuery
- **Focus:** Huge aggregations across billions of rows.
- **Storage:** Columnar storage (vs PostgreSQL's row-based storage).

### 3.2 DuckDB
- **Focus:** In-process analytical database.
- **Use Case:** "SQLite for Analytics". Extremely fast for local data processing.

## 4. Specialized Databases
- **Time-Series (TimescaleDB):** An extension for PostgreSQL optimized for time-series data.
- **Graph (Neo4j):** Optimized for traversing relationships (friends of friends).
- **Search (Elasticsearch/OpenSearch):** Optimized for full-text search and relevance ranking.

## 5. Comparison Table: When to use what?

| Technology | Primary Use Case | Scaling Model | SQL Support |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | General Purpose / Complex Apps | Vertical + Read Replicas | Excellent |
| **MySQL** | Web / Simple Apps | Vertical + Read Replicas | Good |
| **DynamoDB** | High Scale / Serverless | Horizontal (Auto) | No (PartiQL) |
| **Redis** | Caching / Real-time | Horizontal | No |
| **Snowflake** | Big Data Analytics | Horizontal | Excellent |
| **Neo4j** | Relationship Mapping | Specialized | No (Cypher) |

## 6. Real-World Scenario: Polyglot Persistence
Most modern apps use multiple databases:
- **PostgreSQL:** User profiles, orders, transactions (Single source of truth).
- **Redis:** Session storage and active user cache.
- **Elasticsearch:** Product search and catalog filtering.
- **Redshift:** Weekly business intelligence reports.
