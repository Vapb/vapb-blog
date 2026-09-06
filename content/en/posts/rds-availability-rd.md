---
title: "RDS PostgreSQL: High Availability and Disaster Recovery"
author: "vapb"
description: "Guide to RDS availability: Multi-AZ configurations, failover mechanisms, snapshots, read replicas, and disaster recovery strategies for mission-critical databases."
date: 2025-11-02
tags: ["aws", "postgresql", "rds"]
toc: true
---

## 1. Why High Availability Matters
Imagine waking up at 3 AM to alerts that your production database is down.
Your e-commerce site is offline. Every minute costs thousands in lost revenue.
Customers are frustrated. Your team is panicking.

This is why High Availability (HA) is not optional for production systems.

## 2. High Availability Options in RDS
RDS offers three deployment models, each with different availability guarantees.

### 2.1. Single-AZ (No Standby) ❌

```
    ┌─────────────────┐
    │  Availability   │
    │    Zone A       │
    │                 │
    │  ┌───────────┐  │
    │  │ Primary   │  │
    │  │ Instance  │  │
    │  └───────────┘  │
    │                 │
    └─────────────────┘

    No redundancy!
```

What happens if the primary fails:
* RDS detects the failure
* RDS provisions new EC2 instance
* RDS attaches EBS volumes
* PostgreSQL initializes
* Database becomes available

⏰ Downtime: Typically 10-30 minutes (sometimes longer)

When to use:
* Dev/test environments ✅
* Cost-sensitive non-critical workloads ✅
* Databases that can tolerate prolonged downtime ✅

⚠️ Single-AZ Risks
* Hardware failure → 10-30 min downtime
* AZ failure → Potentially hours of downtime
* Maintenance windows → Downtime during upgrades
* No automatic failover

**Conclusion: Single-AZ is NOT production-ready.**


### 2.2. Multi-AZ with One Standby (Synchronous) ✅
```
    ┌─────────────────┐        ┌─────────────────┐
    │   Availability  │        │   Availability  │
    │     Zone A      │        │      Zone B     │
    │                 │        │                 │
    │  ┌───────────┐  │        │  ┌───────────┐  │
    │  │ Primary   │  │◄──────►│  │ Standby   │  │
    │  │ Instance  │  │ Sync   │  │ Instance  │  │
    │  └─────┬─────┘  │ Replic │  └───────────┘  │
    │        │        │        │                 │
    └────────┼────────┘        └─────────────────┘
             │
             │ Apps connect here
             ▼
       DNS Endpoint
       mydb.abc.rds.amazonaws.com
```

This is the standard production setup for most workloads.

Synchronous Replication Flow:
1. App sends: INSERT INTO users...
2. Primary receives the write
3. Primary sends to standby: "I'm about to commit this"
4. Standby acknowledges: "Received, persisted"
5. Primary commits
6. Primary responds to app: "Success!"

Write only confirmed after standby acknowledges
Benefits:
* Zero data loss (RPO = 0)
* Fast failover (RTO = 1-2 min)
* Automatic (no manual intervention)
* Same endpoint (DNS change, no app changes)

#### 2.2.1. Failover Scenario 1: Primary instance fails

What happens:
* Primary crashes
* RDS health check detects failure
* RDS initiates failover
* DNS points to standby
* Standby promoted to primary
* New connections accepted ✅

⚠️ Total downtime: ~1-2 minutes

Your application sees:
* Existing connections: Dropped (need to reconnect)
* New connections: Brief rejection, then success
* Data loss: ZERO (everything was synchronized)

RDS automatically:
* Promotes standby to primary
* Updates DNS (no IP change for the app)
* Begins rebuilding new standby in background

#### 2.2.2. Scenario 2: Standby instance fails

What happens:
* Impact: NONE on your application

RDS actions:
1. Detects standby failure
2. Primary continues serving traffic normally
3. RDS provisions new standby in background
4. Synchronization resumes automatically

#### 2.2.3. Scenario 3: Entire AZ fails

What happens:
* If Primary's AZ fails:
  * Standby in different AZ takes over
  * Failover time: ~1-2 minutes
  * Zero data loss
* If Standby's AZ fails:
  * Primary not affected
  * RDS rebuilds standby in healthy AZ
  * Zero impact on application

{{< details title="What causes automatic failover?" >}}
RDS automatically fails over for:
* Infrastructure failures:
  * Primary instance hardware failure
  * Underlying storage failure
  * AZ-level outage
  * Network connectivity loss between AZs
* Maintenance operations:
  * OS patching (applied to standby first, then failover)
  * Database engine upgrades (minimizes downtime)

Does NOT cause failover ❌ :
* Long-running queries (PostgreSQL issue, not infrastructure)
* Deadlocks (application/database logic issue)
* Out of connections (configuration issue)
* Full disk (need to increase storage)

For database-level issues: RDS restarts, doesn't fail over.
{{< /details >}}

{{< hint info >}}
🎯 Operational Advantages
* Backups run on standby
* Maintenance applied to standby first
   * Standby receives patch/upgrade
   * Failover happens (1-2 min downtime)
   * Old primary becomes new standby
   * New standby receives patch
   * Result: Minimal downtime for maintenance
* SLA guarantee
  * 99.95% monthly uptime SLA
  * Translates to ~22 minutes max downtime per month
* Same endpoint
  * DNS: mydb.abc.rds.amazonaws.com
  * No application changes after failover
  * Connection string remains the same
{{< /hint >}}


### 2.3. Multi-AZ DB Cluster (Semi-Synchronous) 🚀
```
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │     AZ A     │   │     AZ B     │   │     AZ C     │
    │              │   │              │   │              │
    │ ┌──────────┐ │   │ ┌──────────┐ │   │ ┌──────────┐ │
    │ │ Primary  │ │   │ │ Readable │ │   │ │ Readable │ │
    │ │ Instance │◄├───┤►│ Standby  │ │   │ │ Standby  │ │
    │ │          │ │   │ │    #1    │ │   │ │    #2    │ │
    │ └────┬─────┘ │   │ └────┬─────┘ │   │ └────┬─────┘ │
    │      │NVMe   │   │      │NVMe   │   │      │NVMe   │
    │      │SSD    │   │      │SSD    │   │      │SSD    │
    └──────┼───────┘   └──────┼───────┘   └──────┼───────┘
           │                  │                  │
           ▼                  ▼                  ▼
      Write Endpoint     Reader Endpoint    Reader Endpoint
```

This is the premium option for ultra-low RTO and integrated read scalability.

Semi-Synchronous Replication:
1. App sends: INSERT INTO orders...
2. Primary receives the write
3. Primary sends to BOTH standbys
4. Primary waits for ANY ONE standby to acknowledge
5. Primary commits (doesn't wait for both)
6. Primary responds to app: "Success!"
7. Only one standby needs to confirm (faster than full sync)

Key differences from Multi-AZ with One Standby:
* 2 standbys instead of 1 (three AZs total)
* Standbys are readable (can serve SELECT queries)
* Faster failover (<35 seconds vs 1-2 minutes)
* Local NVMe SSDs (better I/O performance)
* Reader endpoint (automatic load balancing)

{{< hint info >}}
🎯 Operational Advantages
1. Ultra-Fast Failover (<35 seconds)
2. Integrated Read Scalability
3. Automatic Reader Endpoint
4. Better Performance
{{< /hint >}}

When to Use Multi-AZ Cluster:
* RTO < 35 seconds required
* Mission-critical applications
* Financial services, healthcare
* E-commerce during seasonal peaks
* Heavy read workload

| Feature | Single-AZ | Multi-AZ (1 Standby) | Multi-AZ Cluster |
|---------|-----------|----------------------|------------------|
| **Availability Zones** | 1 | 2 | 3 |
| **Replication** | None | Synchronous | Semi-synchronous |
| **RTO** | 10-30 min | 1-2 min | <35 sec |
| **RPO** | Minutes to hours | 0 (no data loss) | 0 (no data loss) |
| **Readable Standbys** | N/A | ❌ No | ✅ Yes (2) |
| **Automatic Failover** | ❌ No | ✅ Yes | ✅ Yes |
| **Storage Type** | EBS | EBS | Local NVMe SSD |
| **SLA** | None | 99.95% | 99.99% |
| **Cost** | $ | $$ (2x Single-AZ) | $$$$ (4x Single-AZ) |
| **Best For** | Dev/test | Production (standard) | Mission-critical |

## 3. Disaster Recovery Strategies

High Availability protects against infrastructure failures. Disaster Recovery protects against catastrophic events: region-wide outages, accidental deletions, data corruption, ransomware.

### 3.1. RDS Snapshots
Snapshots are point-in-time backups of your entire database.

{{< details title="Automated snapshots" >}}
```
Day 1:
├─ 00:00 - Full snapshot taken
└─ During the day: Transaction logs captured

Day 2:
├─ 00:00 - Incremental snapshot (only changes)
└─ During the day: Transaction logs captured

Day 3:
├─ 00:00 - Incremental snapshot
└─ And so on...
```

Features:
* Automatic daily backups
* Incremental (only changed blocks)
* Includes transaction logs (for point-in-time restore)
* Default retention: 7 days (configurable up to 35 days)
* Backup window: Specify preferred time (low-traffic period)

Point-in-Time Restore (PITR) -> Scenario: Accidental DELETE at 14:47.
You can restore to:
* 14:46 (before the DELETE)
* 14:30 (30 min before)
* 10:00 (this morning)
* Any 5-minute increment within retention period

Cost:
* Included in RDS pricing
* Storage cost: Same as provisioned storage
* Example: 100 GB DB = ~$10/month for backups
{{< /details >}}

{{< details title="Manual snapshots" >}}
```
Automated Snapshots:
├─ Happen automatically daily
├─ Deleted after retention period
├─ Support point-in-time restore
└─ Tied to instance

Manual Snapshots:
├─ You trigger them
├─ NEVER automatically deleted
├─ NO point-in-time restore (only snapshot moment)
└─ Independent of instance (persist after deletion)
```

When to use manual snapshots:
*  Before major changes
*  Compliance/audit requirements
*  Before deleting instance

Cost:
* Pay only for storage
* $0.095/GB/month in us-east-1
* 100 GB snapshot = $9.50/month
{{< /details >}}

{{< hint info >}}
🎯 Production Snapshot Strategy
* Configure automated backups
* Take manual snapshots before changes:
  * Schema migrations
  * Major version upgrades
  * Configuration changes
  * Before deleting instance
* Copy snapshots cross-region
* Test restores regularly
{{< /hint >}}

#### 3.1.1. Snapshot Restore Process

Timeline:
1. Initiate restore (API call): 1 minute
2. RDS provisions new instance: 5-10 minutes
3. Restore data from snapshot: 10-60 minutes (depends on size)
4. Instance becomes available: Total 15-70 minutes

Factors affecting time:
* Database size (larger = longer)
* Instance class (larger = faster restore)
* Region load (peak times may be slower)

After restore -> New instance:
* Different endpoint (need to update connection strings)
* Same data from snapshot moment
* Same configuration (instance class, parameters)
* Original instance still running (you choose which to keep)

### 3.2. Read Replicas for DR
Read replicas serve TWO purposes:
* Read scalability (offload SELECT queries)
* Disaster recovery (can be promoted to standalone)

```
  ┌─────────────────┐        ┌─────────────────┐
  │  us-east-1      │        │  us-west-2      │
  │                 │        │                 │
  │  ┌───────────┐  │        │  ┌───────────┐  │
  │  │ Primary   │  │───────►│  │  Read     │  │
  │  │ (Source)  │  │ Async  │  │  Replica  │  │
  │  └─────┬─────┘  │ Replic │  └───────────┘  │
  │        │        │        │                 │
  └────────┼────────┘        └─────────────────┘
           │
    Write traffic
```

Asynchronous Replication:
1. App writes to primary
2. Primary commits immediately
3. Primary sends change to replica
4. Replica applies change (eventually)
5. Replica may lag behind primary (seconds to minutes) ⚠️

Key characteristics:
* Async replication (no impact on write latency)
* Can be in same region or cross-region
* Can have different instance class from primary
* Can be promoted to standalone instance
* Replication lag possible (monitor closely)

####  3.2.1. In-Region vs Cross-Region Read Replicas
| Characteristic | In-Region | Cross-Region |
|----------------|-----------|--------------|
| **Topology** | Primary (us-east-1a) → Replica (us-east-1b) | Primary (us-east-1) → Replica (eu-west-1) |
| **Replication Lag** | <1 second (typically) | 1-5 seconds (depends on distance) |
| **Cost** | ~2x instance cost | 2x instance + data transfer ($0.02/GB) |
| **Data Transfer** | ✅ No charge | ❌ Charged ($0.02/GB out) |
| **Latency** | Very low (~ms) | Variable (10-200ms depending on distance) |
| **Primary Use Case** | Read scalability | Disaster recovery + global reads |
| **Best For** | Offload reads from primary | Cross-region DR, compliance, global users |


When to use cross-region:
* Disaster recovery (protection against region-wide failure)
* Compliance (data residency requirements)
* Global application (serve users from nearest region)
* Lower read latency for geographically distributed users

#### 3.2.2. Read Replica Sizing
Replica can be different size from primary

Benefits of larger replica:
* Handles heavy read workload easily
* No performance degradation
* Good for analytical queries

Risk of smaller replica:
* Replica can't keep up with primary
* Replication lag increases
* Eventually replica falls too far behind
* Bad for disaster recovery!

Rule of thumb: Replica should be ≥ same class as primary for DR purposes.

## 4. High Availability vs Disaster Recovery

| Aspect | High Availability (HA) | Disaster Recovery (DR) |
|--------|------------------------|------------------------|
| **Purpose** | Protect against infrastructure failures | Protect against catastrophic events |
| **Technology** | Multi-AZ (sync replication) | Snapshots + Read Replicas (async) |
| **RPO** | 0 (no data loss) | Minutes to hours (depends on backup) |
| **RTO** | 1-2 min (35 sec for cluster) | Hours (snapshot restore) |
| **Scope** | Same region, different AZs | Cross-region |
| **Replication** | Synchronous | Asynchronous |
| **Instance Class** | Same as primary | Can differ |
| **Cost** | 2x instance cost | 2x + storage + data transfer |
| **Failover** | Automatic | Manual (promote replica) |
| **Protects Against** | AZ failure, hardware issues | Region failure, data corruption, accidents |


## 5. Conclusion
High Availability and Disaster Recovery are not optional for production databases—they're essential insurance against inevitable failures.

8.1. Key Takeaways
High Availability:
* Use Multi-AZ for all production (RTO: 1-2 min, RPO: 0) ✅
* Use Multi-AZ Cluster for mission-critical (RTO: <35 sec) 🚀
* Never use Single-AZ for production ❌

Disaster Recovery:
* Enable automated backups (35-day retention) ✅
* Take manual snapshots before major changes ✅
* Use cross-region read replica for critical systems ✅
* Test DR quarterly (restore, promote, measure) ✅

Application Design:
* Retry logic for connections ✅
* Idempotent transactions ✅
* Health checks and monitoring ✅

Costs:
* Multi-AZ: ~2x Single-AZ cost (~$300/month for typical setup)
* ROI: Pays for itself preventing <1 hour downtime/month

Critical Metrics:
* Monitor: DatabaseConnections, ReplicaLag, FreeStorageSpace
* Alert: Lag >60s, Storage <10 GB, Connections >80%
