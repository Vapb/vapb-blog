---
title: "PostgreSQL Architecture: Understanding the Engine Behind Your Database"
author: "vapb"
description: "Deep dive into PostgreSQL's client-server model, background processes, memory architecture, and connection pooling."
date: 2025-11-23
tags: ["PostgreSQL"]
toc: true
---

## 1. Introduction:
Ever wondered what happens when you send a SELECT to PostgreSQL? Like, you write the query, hit enter, and boom - data appears. Seems like magic, but it's just really good engineering.

## 2. The Client-Server Model

PostgreSQL works on the classic client-server model. When your application connects to the database (using psycopg2, for example), Postgres doesn't share a single giant process among everyone. Nope. It spawns a dedicated backend process just for you. It's like having your own personal waiter at a restaurant.
This has its advantages: if one connection crashes or does something stupid, the others keep working just fine. Real isolation.

Let's trace what happens when your application runs a query:

1. **Connection established** — Your app connects via `psycopg2`. PostgreSQL spawns a dedicated backend process.
2. **Backend process takes over** — This process handles all queries for that session. It has access to:
   - **Shared memory** — The common space all processes can read/write (`shared_buffers`, `wal_buffers`, `clog_buffers`)
   - **Local memory** — Private to this process (`work_mem`, `temp_buffers`)
3. **Query execution** — The backend reads data pages into `shared_buffers` (if not already cached), processes your query using local memory for sorts/joins, and returns results.
4. **Background processes do the rest** — WAL Writer ensures your commits are durable, Checkpointer syncs data to disk, Autovacuum cleans up afterward.

This multi-process design is intentional. Each connection gets isolation. If one backend crashes or misbehaves, it doesn't take down other connections. It also scales naturally: more connections simply mean more backend processes.

This flow explains why memory configuration matters: `shared_buffers` affect everyone, while `work_mem` multiplied by `max_connections` determines your memory ceiling.

### 2.1. Connection Pooling: The Part Everyone Gets Wrong
Here's a classic mistake: thinking that each user = one connection to the database. Actually, it's not quite like that.
Imagine your API running on 5 Kubernetes pods. Each pod maintains a pool of, let's say, 10 open connections (via SQLAlchemy, for example). PostgreSQL sees 50 backend processes, doesn't matter if there are 10 or 10,000 users hitting your API at the same time.

Without pooling, each HTTP request would open a new connection, use it, and close it. This is absurdly expensive because spawning backend processes takes time. With pooling, connections stay open and get reused.

And if you have LOTS of scale? That's where PgBouncer comes in, adding a centralized pooling layer before the database. But that's a topic for another post.


## 3. Background Processes: The Silent Workers

While backend processes handle your queries, several background processes run continuously to keep the database healthy. Think of them as the maintenance crew working behind the scenes.

### 3.1. Keeping Data Safe (Durability)

* **WAL Writer**: Every time you commit, it ensures everything was written to the Write-Ahead Log before Postgres says "ok, saved it". Runs every 200ms.
* **Checkpointer**: From time to time (usually every 5 minutes), it takes all the data in memory and syncs everything to disk.
* **Background Writer**: Spreads out the I/O work. Instead of waiting for Checkpointer to dump everything at once (which could freeze your queries), it writes dirty pages gradually in the background.

### 3.2. Maintenance on Autopilot

* **Autovacuum**: When you delete a row, it doesn't actually delete it right away. Just marks it as "dead". Autovacuum comes by later and reclaims that space. It also updates the statistics that the query planner uses.

### 3.3. Replication and Recovery

* **Archiver**: Saves old WAL files before they get recycled. Super important if you need point-in-time recovery ("restore my database from yesterday at 3pm").

* **WAL Sender and Receiver**: This duo is responsible for keeping your replicas in sync. The Sender sends changes from the primary, the Receiver applies them to the replica.

### 3.4. Observability

* **Logger**: It's who writes to your log files. Want to track slow queries? That's it. Just keep an eye on disk space if you enable very verbose logging.


## 4. Memory Architecture

{{<figure class="post_image" src="../images/pg-architecture/01_pg_arch.png">}}

PostgreSQL divides memory into two distinct areas: shared memory (used by all processes) and local memory (per-connection).

### 4.1. Shared Memory

* **`shared_buffers`** is the central data cache. When PostgreSQL reads a page from disk, it goes here. When you modify data, the changes happen here first before being written to disk. **Think of it as your database's RAM**.
* **`wal_buffers`** Holds transaction records temporarily before they go to disk. Usually small (a few MB) because it's flushed frequently.
* **`clog_buffers`** Tracks the state of each transaction (committed, aborted, in progress).

### 4.2. Local Memory (Per-Process)

Each backend process gets its own local memory allocation:

* **`work_mem`** is used for sorting and hash joins. Each operation in a query can use up to this amount—so a complex query with multiple sorts might use several times `work_mem`. When insufficient, PostgreSQL spills to temporary files on disk, which is significantly slower.
* **`temp_buffers`** store temporary tables. Only allocated when you actually create temporary objects.
* **`maintenance_work_mem`** is used for maintenance operations like `VACUUM`, `CREATE INDEX`, and `ALTER TABLE`. Default is 64MB, but bumping this up can significantly speed up these operations.

### 4.3. The Memory Trade-off

There's an inherent tension here. `shared_buffers` benefits everyone but has diminishing returns past a certain point (the OS also caches). `work_mem` helps individual queries but multiply it by your `max_connections` and it can exhaust RAM quickly. Finding the right balance depends on your workload.

{{< hint warning >}}
**Memory formula**: Total memory usage ≈ `shared_buffers` + (`work_mem` × `max_connections` × operations per query). A complex query with 5 sorts using 256MB `work_mem` and 100 connections could consume 128GB just for sorting.
{{< /hint >}}

## 5. Why This Architecture Matters

"Okay, Victor, but I just want to write my queries and be happy."

I get it, but knowing this architecture gives you troubleshooting superpowers:

High CPU? Check if it's your backend processes (your queries) or background processes (maintenance).
Replication lagging? Look at the WAL Sender/Receiver.
Disk I/O spiked? Could be the Checkpointer doing its job.
Queries suddenly slow? Maybe Autovacuum needs to run more frequently.

At the end of the day, databases aren't magic. It's just good engineering. And when you understand how the pieces fit together, it's much easier to make everything work right.
