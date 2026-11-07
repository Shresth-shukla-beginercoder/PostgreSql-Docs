# PART 16: JSON, JSONB AND SEMI-STRUCTURED DATA

## 16.1 JSON vs JSONB

| Feature | JSON | JSONB |
|---|---|---|
| Storage | Text (as given) | Binary (normalized) |
| Preserves key order | Yes | No |
| Duplicate keys | Kept | Collapsed |
| White space / comments | Kept | Stripped |
| Indexable | No | Yes (GIN) |
| Query speed | Slower | Faster |
| Size | Smaller | Larger (~30% bloat) |

**Rule:** store *arbitrary/flexible* data as **`JSONB`**; use `JSON` only when you need *the exact original text* (legal/audit documents).

## 16.2 JSON Operators

| Operator | Meaning | Example |
|---|---|---|
| `->` | JSON: field as JSON | `'{"a":1}'::json -> 'a'` → `1` |
| `->>` | JSON: field as TEXT | `'{"a":1}'::json ->> 'a'` → `'1'` |
| `#>` | JSON path (array of keys) | `'{"a":{"b":1}}'::json #> '{a,b}'` → `1` |
| `#>>` | JSON path as TEXT | `'{"a":{"b":1}}'::json #>> '{a,b}'` → `'1'` |
| `@>` | Containment (does left contain right?) | `'{"a":1,"b":2}'::json @> '{"a":1}'` → `true` |
| `<@` | Contained by | `'{"a":1}'::json <@ '{"a":1,"b":2}'::json` → `true` |
| `?` | Key exists (JSONB) | `'{"a":1}'::jsonb ? 'a'` → `true` |
| `?|` | Any key in list | `'{"a":1}'::jsonb ?\| array['a','b']` |
| `?&` | All keys in list | `'{"a":1,"b":2}'::jsonb ?& array['a','b']` |

## 16.3 JSONB Indexing

```sql
CREATE INDEX idx_metadata ON events USING gin (metadata jsonb_path_ops);

-- Fast: WHERE metadata @> '{"user_id": 42}'
```

- **`jsonb_path_ops`** is smaller and faster than default `jsonb_ops`, but only supports `@>` (containment), not key existence (`?`).

## 16.4 JSONB Functions

| Function | Purpose | Example |
|---|---|---|
| `jsonb_set(target, path, value)` | Set a value at path | `jsonb_set('{"a":{"b":1}}'::jsonb, '{a,b}', '2')` → `{"a":{"b":"2"}}` |
| `jsonb_insert(target, path, value)` | Insert a value at path | `jsonb_insert('{"a":{"b":1}}'::jsonb, '{a,c}', '2')` → `{"a":{"b":1,"c":"2"}}` |
| `jsonb_build_object(key1, val1, ...)` | Build a JSONB object | `jsonb_build_object('a', 1, 'b', 2)` → `{"a":1,"b":2}` |
| `jsonb_agg(expr)` | Aggregate to a JSONB array | `SELECT jsonb_agg(row_to_jsonb(r)) FROM (SELECT 1 AS a, 2 AS b) r` → `[{"a":1,"b":2}]` |
| `jsonb_array_elements(arr)` | Expand a JSONB array | `SELECT * FROM jsonb_array_elements('[1,2,3]'::jsonb)` → 3 rows |
| `jsonb_object_keys(obj)` | Get object keys | `SELECT jsonb_object_keys('{"a":1,"b":2}'::jsonb)` → `a`, `b` |
| `jsonb_to_record(jsonb)` | Convert JSONB to a record | `SELECT * FROM jsonb_to_record('{"a":1,"b":2}'::jsonb)` → `a=1, b=2` |
| `jsonb_to_recordset(jsonb)` | Convert JSONB array to a set of records | `SELECT * FROM jsonb_to_recordset('[{"a":1},{"a":2}]'::jsonb)` → 2 rows |

## 16.5 Practical Examples

### 1. Storing flexible metadata

```sql
CREATE TABLE events (
  event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_type text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Insert with metadata
INSERT INTO events (event_type, metadata)
VALUES ('user_login', '{"user_id": 42, "ip": "192.168.1.1"}'::jsonb);

-- Query metadata
SELECT * FROM events WHERE metadata @> '{"user_id": 42}';

-- Update metadata
UPDATE events SET metadata = jsonb_set(metadata, '{status}', 'success')
WHERE event_id = 1;
```

### 2. API response formatting

```sql
CREATE OR REPLACE FUNCTION get_user_profile(user_id int)
RETURNS jsonb LANGUAGE sql AS $$
  SELECT jsonb_build_object(
    'user', jsonb_build_object(
      'id', u.user_id,
      'name', u.name,
      'email', u.email
    ),
    'orders', (
      SELECT jsonb_agg(
        jsonb_build_object(
          'id', o.order_id,
          'total', o.total_cents,
          'placed_at', o.placed_at
        )
      ) FROM orders o WHERE o.customer_id = u.user_id
    )
  )
  FROM users u WHERE u.user_id = get_user_profile.user_id;
$$;

-- Call the function
SELECT get_user_profile(42);
```

### 3. Dynamic configuration

```sql
CREATE TABLE app_config (
  key text PRIMARY KEY,
  value jsonb NOT NULL,
  description text
);

-- Insert config
INSERT INTO app_config (key, value, description)
VALUES ('features', '{"checkout": true, "discounts": false}', 'Feature flags');

-- Query config
SELECT value->>'checkout' FROM app_config WHERE key = 'features';

-- Update config
UPDATE app_config SET value = jsonb_set(value, '{discounts}', 'true')
WHERE key = 'features';
```

### 4. Full-text search with JSONB

```sql
CREATE TABLE articles (
  article_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title text NOT NULL,
  body text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  fts tsvector GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, '')) ||
    to_tsvector('english', coalesce(metadata->>'tags', ''))
  ) STORED
);

CREATE INDEX idx_articles_fts ON articles USING gin (fts);

-- Search
SELECT article_id, title
FROM articles
WHERE fts @@ to_tsquery('postgres & performance');
```

### 5. Data migration from JSON to JSONB

```sql
-- Add a new JSONB column
ALTER TABLE events ADD COLUMN metadata_new jsonb;

-- Migrate data
UPDATE events SET metadata_new = metadata::jsonb;

-- Drop the old column
ALTER TABLE events DROP COLUMN metadata;

-- Rename the new column
ALTER TABLE events RENAME COLUMN metadata_new TO metadata;
```

## 16.6 Performance Considerations

- **`JSONB` is faster** for queries (binary format, smaller index).
- **`JSON` preserves the original text** (whitespace, comments, duplicate keys).
- **Indexing:** `@>` is the JSONB workhorse for "has field X with value Y" — it is indexable with GIN (Part 11). `->>` in a `WHERE` is *not* indexable without an expression index or a GIN operator-class match.
- **Size:** `JSONB` is ~30% larger than `JSON` (due to normalization).
- **Updates:** `JSONB` is faster for updates (binary format).

## 16.7 Common Mistakes

1. **Using `JSON` when you need indexing** → slower queries.
2. **Assuming `JSON` and `JSONB` are the same** → different storage, behavior, and performance.
3. **Not using `jsonb_path_ops`** → larger index, slower queries.
4. **Assuming `->>` is indexable** → it is not (unless you add an expression index).
5. **Not handling duplicate keys in `JSON`** → unexpected behavior.
6. **Assuming `JSONB` is always smaller** → it is ~30% larger due to normalization.
7. **Using `JSON` for audit documents** → prefer `JSON` only when you need the exact original text.
8. **Not using `jsonb_set`/`jsonb_insert`** → manual JSON manipulation is error-prone.
9. **Assuming `jsonb_agg` is fast** → it is moderately expensive; do not call it per row on millions.
10. **Not using `GENERATED ALWAYS AS` for computed columns** → avoids redundant computation.

## 16.8 Interview-Style Quick Reference

| Question | Answer |
|---|---|
| What is the difference between JSON and JSONB? | JSON preserves text; JSONB is binary, indexable, dedupes keys |
| How do you index JSONB? | Use GIN on `jsonb_path_ops` for containment (`@>`) |
| What is the performance difference between JSON and JSONB? | JSONB is faster for queries and updates |
| How do you query a nested field in JSONB? | Use `->` or `#>` |
| How do you check if a key exists in JSONB? | Use `?` or `?|` |
| How do you aggregate rows to JSONB? | Use `jsonb_agg` |
| How do you convert JSONB to a record? | Use `jsonb_to_record` |
| How do you convert JSONB array to a set of records? | Use `jsonb_to_recordset` |
| How do you update a nested field in JSONB? | Use `jsonb_set` or `jsonb_insert` |
| How do you build a JSONB object? | Use `jsonb_build_object` |
| How do you expand a JSONB array? | Use `jsonb_array_elements` |
| How do you get object keys from JSONB? | Use `jsonb_object_keys` |
