# PART 24: POSTGRESQL EXTENSIONS

PostgreSQL's extensibility is one of its most powerful features. Extensions allow you to add new functions, data types, and indexing methods.

## 1. Core Extensions

### 1.1 pg_stat_statements
The most important extension for performance tuning. It tracks execution statistics of all SQL statements.
```sql
CREATE EXTENSION pg_stat_statements;
-- View slow queries
SELECT query, calls, total_exec_time, mean_exec_time 
FROM pg_stat_statements 
ORDER BY total_exec_time DESC LIMIT 5;
```

### 1.2 uuid-ossp
Provides functions to generate Universally Unique Identifiers (UUIDs).
```sql
CREATE EXTENSION "uuid-ossp";
SELECT uuid_generate_v4();
```

### 1.3 pgcrypto
Provides cryptographic functions (hashing, encryption). Useful for password hashing in older systems (though many now hash in application code).

## 2. Advanced Capability Extensions

### 2.1 PostGIS
The industry standard for geographic information systems (GIS). Adds support for geographic objects.
- **Data Types:** `GEOMETRY`, `GEOGRAPHY`.
- **Functions:** `ST_Distance`, `ST_Intersects`.

### 2.2 pgvector
Adds vector similarity search to PostgreSQL. Crucial for AI/LLM applications (storing embeddings).
```sql
CREATE EXTENSION vector;
CREATE TABLE items (id serial primary key, embedding vector(3));
-- Query nearest neighbor
SELECT * FROM items ORDER BY embedding <-> '[1,2,3]' LIMIT 5;
```

### 2.3 TimescaleDB
Transforms PostgreSQL into a time-series database.
- **Hypertables:** Automatically partition data by time.
- **Continuous Aggregates:** Automatically refresh materialized views for time-series data.

## 3. Connectivity & Federation

### 3.1 postgres_fdw
Foreign Data Wrapper for accessing data in other PostgreSQL databases.
- **Use Case:** Querying across different microservice databases.

### 3.2 file_fdw
Allows PostgreSQL to query CSV or other files directly as if they were tables.

## 4. Security & Auditing

### 4.1 pgaudit
Provides detailed session and/or object audit logging via the standard logging facility. Essential for compliance (SOC2, HIPAA).

## 5. How to Manage Extensions
- **List installed:** `\dx` in psql or `SELECT * FROM pg_extension;`.
- **List available:** `SELECT * FROM pg_available_extensions;`.
- **Installation:** `CREATE EXTENSION name;`. Note that some require superuser privileges.
- **Removal:** `DROP EXTENSION name;`.
