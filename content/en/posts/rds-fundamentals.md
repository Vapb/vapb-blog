---
title: "RDS PostgreSQL Fundamentals: Performance and Optimization"
author: "vapb"
description: "Amazon RDS for PostgreSQL: instance selection, EBS storage types, auto-scaling, and cost optimization strategies."
date: 2025-11-01
tags: ["AWS", "RDS", "PostgreSQL"]
toc: true
---

## 1. Introduction

**Amazon RDS (Relational Database Service)** for PostgreSQL is a managed solution that simplifies PostgreSQL database administration in the cloud. In this post, we'll explore the key concepts and features you need to know to work with this powerful tool.

### 1.1. Performance: what really matters

Your RDS performance depends on two pillars:

1. **Instance class** - CPU, memory, and network
2. **Storage type** - I/O throughput

### 1.2. Scalability: the numbers

RDS offers independent scalability for compute and storage:

{{< details title="Compute limits" >}}
- **Up to 128 vCPUs**
- **Up to 4,096 GB of RAM**
{{< /details >}}

{{< details title="Storage limits" >}}
- **Up to 64 TB** of capacity
- **Up to 256,000 IOPS**
- Supports **auto-scaling** and **scale-down**
{{< /details >}}

{{< hint warning >}}
**⏰ Important detail**

* Storage modifications **DO NOT cause downtime**.
* ⚠️ **BUT** you need to wait **6 hours between modifications**.
* **This means:** plan your changes in advance. If you increased storage now, you'll have to wait 6 hours to make another adjustment.
{{< /hint >}}

## 2. Choosing the right instance class

Choosing the right instance class is crucial to achieve the best balance between performance and cost. RDS offers different instance families, each optimized for specific scenarios.

{{< details title="Available instance families" >}}
* **General Purpose** - Smaller workloads or with variable usage patterns
* **CPU Optimized** - Tasks demanding high computational power
* **Memory Optimized** - Memory-intensive queries and large cached datasets
* **Graviton** - Best choice in most cases
{{< /details >}}

### 2.1. How to choose?

The decision depends on your workload characteristics:

- **Analyze the current bottleneck:** Is it CPU? Memory? I/O?
- **Consider the usage pattern:** Constant or variable?
- **Evaluate cost-benefit:** Graviton usually wins
- **Test in staging:** Validate performance before going to production

## 3. Storage types: EBS in action

RDS uses **EBS (Elastic Block Store)** volumes as storage. Think of EBS as the HDD/SSD of your database in the cloud. There are three main options, each with different speed and cost characteristics.

### 3.1. Before starting: what is IOPS?

**IOPS** = Input/Output Operations Per Second

In simple terms: how many times per second your database can read or write data to disk.

{{< details title="In the database" >}}
- Each SELECT, INSERT, UPDATE = I/O operations
- **More IOPS** = database responds faster
- **Fewer IOPS** = queries wait in queue
{{< /details >}}

{{< details title="How to know how many IOPS I need?" >}}
- Monitor in **CloudWatch** - Metric: `ReadIOPS + WriteIOPS`
- If the sum is consistently above **80% of your limit** = time to increase
{{< /details >}}

{{< hint info >}}
**💡 Throughput vs IOPS**
- **IOPS:** How many operations per second (quantity)
- **Throughput:** How many MB/s you transfer (transfer speed)
{{< /hint >}}

### 3.2. GP2 (General Purpose SSD) - the legacy option

{{< details title="How it works: performance grows with volume size" >}}
**Performance examples:**
- 100 GB = ~300 IOPS
- 500 GB = ~1,500 IOPS
- 1 TB = ~3,000 IOPS
- 3,334 GB = 10,000 IOPS (base maximum)

**Characteristics:**
- Variable performance: larger disk, more IOPS
- Up to **1,000 MBps** throughput
- Decent price, but GP3 is generally better

**When to use:** Practically never. GP3 is superior.
{{< /details >}}

{{< hint warning >}}
**⚠️ GP2 problem**

If you need 10,000 IOPS but only use 200 GB, you'll have to pay for ~3 TB of storage just to get the necessary IOPS. Wasteful!
{{< /hint >}}

### 3.3. GP3 (General Purpose SSD) - standard choice ⭐

{{< details title="How it works: performance independent of size" >}}
- Any size = **3,000 IOPS baseline** (free)
- Need more? Can buy up to **16,000 extra IOPS**

**Characteristics:**
- **3,000 IOPS baseline** independent of size
- **125 MBps** throughput baseline (can increase up to 1,000 MBps)
- **~20% cheaper** than GP2 with same performance
- You adjust IOPS and throughput separately from size

**When to use:** This should be your standard choice for **90% of cases**.
{{< /details >}}

### 3.4. IO1 / IO2 Block Express - maximum performance 🚀

{{< details title="How it works: you provision exactly how many IOPS you need" >}}
**Available options:**
- **IO1:** Up to 64,000 IOPS per volume
- **IO2:** Up to 256,000 IOPS per volume
- **IO2 Block Express:** Up to 256,000 IOPS + better durability

**Characteristics:**
- **Provisioned and guaranteed IOPS** - no surprises
- **Ultra-low latency** - single-digit milliseconds
- **Consistent performance** - doesn't depend on credits or variations
- **More expensive** - you pay for provisioned IOPS
{{< /details >}}

{{< details title="When to use IO2 Block Express" >}}
Use IO2 Block Express when:
- Critical app that can't have variable latency
- Need **>16,000 IOPS** consistent
- **Intensive OLTP** with thousands of transactions/second
- **Mission-critical** database (banking, healthcare, large e-commerce)
{{< /details >}}

### 3.5. Comparison between storage types

| Feature | GP2 (Legacy) | GP3 (Standard) ⭐ | IO2 Block Express (Premium) |
|----------------|--------------|-----------------|------------------------------|
| **Baseline IOPS** | 3 per GB | 3,000 (fixed) | You choose |
| **Maximum IOPS** | 16,000 | 16,000 | 256,000 |
| **Throughput** | Up to 1,000 MBps | Up to 1,000 MBps | Up to 4,000 MBps |
| **Latency** | Variable | Low | Ultra-low (consistent) |
| **Cost** | $$ | $ | $$$$ |
| **Flexibility** | ❌ Tied to size | ✅ Independent | ✅ Total control |
| **Best for** | Nothing (use GP3) | 90% of cases | Critical apps |

## 4. Auto storage scaling: let RDS manage

One of the most practical RDS features is **auto-scaling storage**. Configure once and let the system expand automatically when needed.

### 4.1. When is auto-scaling triggered?

RDS monitors your database 24/7 and triggers auto-scaling when it detects:

{{< details title="Auto-scaling triggers" >}}
**Trigger 1: Free space ≤ 10% of total capacity**
- Simple and direct: running out of space = automatic expansion

**Trigger 2: Predicted growth**
- RDS analyzes history and predicts: "Based on recent days, you'll run out of space soon"
- **Why is this important?** Prevents running out of space during an unexpected spike
{{< /details >}}

### 4.2. Cooldown protection (6 hours)

{{< hint warning >}}
**⏰ Cooldown protection**

To avoid cascading expansions that could cause instability:

**Rule:** Auto-scaling only adds capacity if no modification occurred in the last **6 hours**.

**Why does this exist?**
- Avoids rapid fluctuations that can impact performance
- Prevents uncontrolled growth from bugs
- Gives RDS time to stabilize the new size

⚠️ **Important implication:** If you're growing VERY fast (>10% every 6h), auto-scaling may not keep up. In these cases, size manually with margin.
{{< /hint >}}

### 4.3. Essential CloudWatch alarms

{{< hint info >}}
**💡 Don't rely only on the maximum limit!**

Configure proactive alerts:

**Low space alert (70%)**
- Detect problems before they become critical
- Gives time to investigate abnormal growth

**Rapid growth alert**
- Monitor storage growth rate
- Identify unexpected spikes that may indicate problems

**Near limit alert (90%)**
- Last warning before hitting the configured maximum
- Time to increase maximum limit if needed

**Important tip:** Set a reasonable maximum limit to avoid billing surprises. If something goes wrong (like an uncontrolled process generating data), you don't want to wake up with a 64 TB volume!
{{< /hint >}}

## 5. Cost optimization

Performance is essential, but nobody wants surprises on the AWS bill. The good news? You can have both - excellent performance **AND** controlled costs.

### 5.1. Strategy 1: Dynamic scaling (schedule-based scaling)

{{< details title="Implementation options" >}}
**Option 1: AWS Lambda + Scheduler**
- More flexibility and programmatic control
- Ideal for complex scaling rules

**Option 2: AWS Systems Manager (no code)**
- Visual interface, no programming needed
- Good for simple use cases

**Option 3: Third-party tools**
- AWS Instance Scheduler, CloudHealth, or Terraform with cron jobs
- More robust solutions for large environments
{{< /details >}}

### 5.2. Strategy 2: Reserved Instances (RIs)

{{< hint info >}}
**💰 Free money on the table**

If you're SURE you'll use RDS for 1-3 years, RIs are guaranteed savings:
- **Up to 72% discount** vs On-Demand
- **No operational changes** - just financial benefit
- **Payment flexibility** - All upfront, partial, or none
{{< /hint >}}

### 5.3. Strategy 3: Graviton

**Migrating to Graviton** is probably the easiest optimization with highest ROI:
- **Up to 40% cheaper** than equivalent x86 instances
- **Equal or superior performance** on most workloads
- **Simple migration** - usually just change instance type

### 5.4. Strategy 4: Storage - GP2 → GP3

**Simple migration** with immediate **~20%** savings:
- Same performance (or better)
- No downtime
- Independent adjustment of IOPS and throughput

### 5.5. Strategy 5: Review read replicas

{{< details title="Optimizing read replicas" >}}
**Read replicas** are great for performance, but each one duplicates your compute costs.

**Questions to ask:**
- Are all replicas being actively used?
- Could you consolidate read workloads into fewer replicas?
- Would smaller replicas meet your needs?
- Could connection pooling reduce the need for replicas?

**Action:** Monitor each replica's utilization and remove or reduce underutilized ones.
{{< /details >}}

### 5.6. You can't optimize what you don't measure

{{< hint info >}}
**📊 Essential CloudWatch metrics**

Monitor constantly:
- **CPU Utilization** - Identify oversizing
- **Read/Write IOPS** - Optimize storage type
- **Database Connections** - Size correctly
- **Free Storage Space** - Prevent problems
- **Replication Lag** - Read replica health
{{< /hint >}}

## 6. RDS configuration: Parameter Groups and connections

If you've worked with "traditional" PostgreSQL (installed on a server), you know that configuring the database involves editing text files. In RDS, AWS simplified (and in some cases complicated a bit) this process.

### 6.1. Traditional PostgreSQL vs RDS

{{< details title="Traditional PostgreSQL (self-managed)" >}}
You have direct access to configuration files:

**1. postgresql.conf** - Server configurations
```bash
max_connections = 100
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
```

**2. pg_hba.conf** - Access control
```bash
# Who can connect from where and how
host    all    all    192.168.1.0/24    md5
host    all    all    10.0.0.0/8        trust
```

**How to modify:**
```bash
# 1. Edit the file
sudo nano /var/lib/postgresql/data/postgresql.conf

# 2. Reload configuration
sudo systemctl reload postgresql

# or if restart is needed
sudo systemctl restart postgresql
```
{{< /details >}}

{{< details title="Amazon RDS" >}}
You **DO NOT have direct access** to files.

**Why?** Because RDS is managed - AWS takes care of the infrastructure.

**Instead, you use:**
* **Parameter Groups** (replaces postgresql.conf)
* **Security Groups** (replaces pg_hba.conf)
{{< /details >}}

### 6.2. Parameter Groups

Think of **Parameter Group** as a configuration profile for your database.

```
┌─────────────────────┐
│  Parameter Group    │ ← Configuration set
│  "prod-default"     │
│                     │
│  max_connections=200│
│  shared_buffers=8GB │
│  work_mem=16MB      │
└──────────┬──────────┘
           │
           │ applied to ↓
           │
    ┌──────┴──────┐
    │ RDS Instance│
    │  my-db-prod │
    └─────────────┘
```

#### 6.2.1. Types of Parameter Groups

{{< details title="Default Parameter Group vs Custom" >}}
**Default Parameter Group (created by AWS)**
- Conservative default settings
- **Cannot be modified**
- Serves as initial template

**Custom Parameter Group (created by you)**
- **Fully configurable**
- You control all parameters
- Can be shared between instances

⚠️ **Important:** You should **ALWAYS** create a custom parameter group. Never use default in production!

{{< /details >}}

#### 6.2.2. Parameter types

Not all parameters work the same way. Some can be changed "on the fly", others require restart.

{{< details title="Static parameters" >}}
**Definition:** Require **instance reboot** to apply.

**Common examples:**
```yaml
shared_buffers:
  - What it is: PostgreSQL cache memory
  - Typical: 25% of instance RAM
  - Example: On 32 GB RAM instance → shared_buffers = 8 GB
  - Why reboot: Memory is allocated at startup

max_connections:
  - What it is: Maximum number of simultaneous connections
  - Typical: 100-500 (depends on workload)
  - Why reboot: Memory structures are pre-allocated

wal_buffers:
  - What it is: Buffers for Write-Ahead Logging
  - Typical: -1 (auto, based on shared_buffers)
  - Why reboot: Buffer is pre-allocated
```

**How to apply:**
1. Modify the parameter group
2. Apply to instance
3. RDS requires reboot
4. Downtime of ~5-10 minutes
{{< /details >}}

{{< details title="Dynamic parameters" >}}
**Definition:** Can be applied **immediately, without reboot**.

**Common examples:**
```yaml
work_mem:
  - What it is: Memory for sorting/hash operations
  - Typical: 4-16 MB (careful: per operation!)
  - Can be: Changed per session
  - Impact: Immediate

maintenance_work_mem:
  - What it is: Memory for VACUUM, CREATE INDEX, etc
  - Typical: 256 MB - 2 GB
  - Can be: Changed without reboot
  - Impact: Immediate

log_min_duration_statement:
  - What it is: Log queries above X ms
  - Typical: 1000 (log queries >1s)
  - Can be: Changed per session
  - Impact: Immediate

random_page_cost:
  - What it is: Estimated cost of random read (SSD = 1.1)
  - Typical: 1.1 for SSD, 4.0 for HDD
  - Can be: Changed immediately
  - Impact: Affects query planner
```

**How to apply:**
1. Modify the parameter group
2. Apply to instance with **"Apply Immediately"**
3. **No downtime!**
4. Change in seconds
{{< /details >}}

### 6.3. Connections to RDS

**Security Groups** do the job of "who can connect from where":

```
┌─────────────────────────┐
│   Security Group        │ ← Controls IPs/networks
│   "rds-prod-sg"         │
│                         │
│   Inbound Rules:        │
│   ✅ 10.0.1.0/24:5432   │ (app network)
│   ✅ 203.0.113.5/32:5432│ (admin fixed IP)
│   ❌ 0.0.0.0/0          │ (rest blocked)
└────────┬────────────────┘
         │
         │ protects ↓
         │
  ┌──────┴────────┐
  │  RDS Instance │
  │  my-db        │
  └───────────────┘
```

#### 6.3.1. Authentication methods in RDS

{{< details title="Authentication options" >}}
**1. Username/Password (Default)**
- Traditional and simplest method
- Credentials stored in RDS
- Ideal to get started

**2. IAM Authentication (Recommended)**
- **No passwords** - uses temporary IAM tokens
- **More secure** - automatic credential rotation
- **Integrated auditing** - track who accesses via CloudTrail
- Ideal for modern AWS applications

**3. Kerberos (Enterprise)**
- Centralized authentication for corporate environments
- Active Directory integration
- For companies with existing Kerberos infrastructure
{{< /details >}}

## 7. TLDR
**Instance choice**
* Default: M6g (Graviton) - best cost-benefit
* CPU-heavy: M6g with larger class
* Memory-heavy: R6g
* Dev/test: T4g (burstable)

**Storage**
* Use GP3 (not GP2!) for 90% of cases
* Free baseline: 3,000 IOPS
* IO2 Block Express: Only if you need >16k consistent IOPS

**Auto-Scaling**
* Always enable
* Set maximum limit (3-5x current)
* Configure CloudWatch alarms (70%, 90%)

**Cost optimization**
* GP2 → GP3 (30 min, 20-50% storage savings)
* x86 → Graviton (1 week test, 20-40% savings)
* Reserved Instances (30 min, 30-54% baseline savings)
* Remove unnecessary replicas (variable savings)
* Downsize oversized instances (analyze CPU <30%)

**Parameter Groups**
* 🚫 Never use default in production
* Create custom group
* Essential parameters:
    * shared_buffers = 25% RAM (static)
    * random_page_cost = 1.1 (dynamic)
    * work_mem = 16MB (dynamic)
    * log_min_duration_statement = 1000 (dynamic)

**Connections**
* Security Groups control network access
* IAM Authentication recommended (no hardcoded passwords)
* Never expose RDS publicly (always in private VPC)
