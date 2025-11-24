---
title: "PostgreSQL Architecture: Understanding the Engine Behind Your Database"
author: "vapb"
description: "Deep dive into PostgreSQL's client-server model, background processes, memory architecture, and connection pooling."
date: 2025-11-23
tags: ["PostgreSQL"]
toc: true
---
## 1. The Client-Server Model

PostgreSQL follows a straightforward client-server architecture. When your application connects to the database, here's what happens:

1. Your client (using `psycopg2` in Python, `JDBC` in Java) initiates a connection
2. The main Postgres server process receives the request
3. A dedicated **backend process** is spawned just for that connection
4. This backend handles all queries for that specific session

This multi-process design is intentional. Each connection gets isolation. If one backend crashes or misbehaves, it doesn't take down other connections. It also scales naturally: more connections simply mean more backend processes.


### 1.1. How a Connection Actually Works

Let's trace what happens when your application runs a query:

1. **Connection established** — Your app connects via `psycopg2`. PostgreSQL spawns a dedicated backend process.
2. **Backend process takes over** — This process handles all queries for that session. It has access to:
   - **Shared memory** — The common space all processes can read/write (`shared_buffers`, `wal_buffers`, `clog_buffers`)
   - **Local memory** — Private to this process (`work_mem`, `temp_buffers`)
3. **Query execution** — The backend reads data pages into `shared_buffers` (if not already cached), processes your query using local memory for sorts/joins, and returns results.
4. **Background processes do the rest** — WAL Writer ensures your commits are durable, Checkpointer syncs data to disk, Autovacuum cleans up afterward.

This flow explains why memory configuration matters: `shared_buffers` affect everyone, while `work_mem` multiplied by `max_connections` determines your memory ceiling.

### 1.2. Connections in Production: Pods, Pools, and Reality

A common misconception: "each user = one connection." Not quite. In a typical setup with an API running across multiple pods:

```
Users A, B, C ──► Pod 1 ──┐
                          ├──► Connection Pool ──► Backend Processes
Users D, E, F ──► Pod 2 ──┘
```

Each pod maintains a **connection pool** (via SQLAlchemy, HikariCP, etc.). If you have 5 pods with a pool of 10 connections each, PostgreSQL sees 50 backend processes—regardless of whether 100 or 10,000 users are hitting your API.

Without pooling, every HTTP request would open a new connection, use it briefly, and close it. Spawning backend processes is expensive, so this kills performance. With pooling, connections stay open and get reused across requests. For high-scale scenarios, **PgBouncer** adds centralized pooling across all pods.


## 2. Background Processes: The Silent Workers

While backend processes handle your queries, several background processes run continuously to keep the database healthy. Think of them as the maintenance crew working behind the scenes.

### 2.1. Keeping Data Safe (Durability)

{{< details title="WAL Writer" >}}
Your transaction guardian. Every change you commit needs to be on disk before PostgreSQL says "done." This process flushes the Write-Ahead Log buffers to disk every 200ms, ensuring your data survives crashes.
{{< /details >}}

{{< details title="Checkpointer" >}}
Syncs everything periodically. While WAL Writer saves the "what changed" log, Checkpointer writes the actual data pages from memory to disk. Runs every 5 minutes or when WAL reaches 2GB.
{{< /details >}}

{{< details title="Background Writer" >}}
Spreads out the I/O work. Instead of waiting for Checkpointer to dump everything at once (which could freeze your queries), it writes dirty pages gradually in the background.
{{< /details >}}

### 2.2. Maintenance on Autopilot

{{< details title="Autovacuum Launcher and Workers" >}}
Your cleanup crew. PostgreSQL doesn't delete rows immediately—it marks them as dead. Autovacuum reclaims that space and updates statistics for the query planner. It also prevents transaction ID wraparound, a rare but catastrophic issue if ignored.
{{< /details >}}

### 2.3. Replication and Recovery

{{< details title="Archiver" >}}
Saves WAL files before they're recycled. Critical if you need point-in-time recovery ("restore my database to yesterday at 3pm") or feed replicas that fell behind.
{{< /details >}}

{{< details title="WAL Sender and Receiver" >}}
Handle streaming replication. Sender ships WAL from primary to replicas; Receiver applies it. This is how read replicas stay in sync.
{{< /details >}}

### 2.4. Observability

{{< details title="Logger" >}}
Writes to your log files based on configuration. Slow query logging, error tracking, connection attempts—all here. Just watch your disk space if you enable verbose logging.
{{< /details >}}


## 3. Memory Architecture

{{<figure class="post_image" src="../images/pg-architecture/01_pg_arch.png">}}

PostgreSQL divides memory into two distinct areas: shared memory (used by all processes) and local memory (per-connection).

### 3.1. Shared Memory

* **`shared_buffers`** is the central data cache. When PostgreSQL reads a page from disk, it goes here. When you modify data, the changes happen here first before being written to disk.
* **`wal_buffers`** temporarily hold transaction log records before the WAL Writer flushes them to disk. These are typically small (a few MB) since they're flushed frequently.
* **`clog_buffers`** track transaction states—whether each transaction was committed, aborted, or is still in progress. Essential for MVCC to determine tuple visibility.

### 3.2. Local Memory (Per-Process)

Each backend process gets its own local memory allocation:

* **`work_mem`** is used for sorting and hash joins. Each operation in a query can use up to this amount—so a complex query with multiple sorts might use several times `work_mem`. When insufficient, PostgreSQL spills to temporary files on disk, which is significantly slower.
* **`temp_buffers`** store temporary tables. Only allocated when you actually create temporary objects.
* **`maintenance_work_mem`** is used for maintenance operations like `VACUUM`, `CREATE INDEX`, and `ALTER TABLE`. Default is 64MB, but bumping this up can significantly speed up these operations.

### 3.3. The Memory Trade-off

There's an inherent tension here. `shared_buffers` benefits everyone but has diminishing returns past a certain point (the OS also caches). `work_mem` helps individual queries but multiply it by your `max_connections` and it can exhaust RAM quickly. Finding the right balance depends on your workload.

{{< hint warning >}}
**Memory formula**: Total memory usage ≈ `shared_buffers` + (`work_mem` × `max_connections` × operations per query). A complex query with 5 sorts using 256MB `work_mem` and 100 connections could consume 128GB just for sorting.
{{< /hint >}}

## 4. Why This Architecture Matters

Understanding this architecture helps you troubleshoot and optimize. When you see high CPU usage, you can check if it's backend processes (your queries) or background processes (maintenance tasks). When replication lags, you know to look at WAL Sender/Receiver. When disk I/O spikes, it might be the checkpointer doing its job.
