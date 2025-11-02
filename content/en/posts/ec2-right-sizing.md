---
title: "EC2 instance types and right-sizing"
author: "vapb"
description: "Introduction to EC2 instance types and the right-sizing concept."
date: 2025-06-26
tags: ["AWS", "EC2"]
toc: true
---

## 1. Introduction

In this post, we'll explore EC2 instance types, discuss selecting the right instance type, the practice of _right-sizing_, and briefly cover the **AWS Compute Optimizer** tool.

## 2. Amazon EC2 instance families

Amazon EC2 offers over **500 instance types**, organized into **families** and **subfamilies**. Each instance name indicates its purpose and available hardware resources.

### 2.1. Instance types

An EC2 instance is a virtual machine (VM) running in the AWS cloud. The instance type determines the host hardware that will be used. Each type offers different processing, memory, and storage capabilities, grouped into instance families based on these characteristics.

{{< hint info >}}
**Key concepts:**
- **Instance** = VM in AWS
- **Instance type** = Set of virtual resources (CPU, memory, etc.)
- **Instance Family** = Set of types optimized for a specific use
- **Subfamilies** = Variations based on processor or storage
{{< /hint >}}

## 3. The 5 AWS instance families

### 3.1. General purpose

Designed to provide a balance between CPU, memory, and network, they are the most versatile option for general applications.

#### 3.1.1. T Family (burstable)

Instances with variable CPU that accumulate credits when idle.

{{< details title="When to use" >}}
- Workloads with low or variable CPU usage
- Applications that need high performance only during peaks
{{< /details >}}

{{< details title="How it works" >}}
You earn **CPU credits** when the instance is below the CPU baseline and can use them for more performance during spikes:
- **Standard mode**: if credits run out, performance is reduced to baseline
- **Unlimited mode**: continues performing above baseline, but you pay for extra usage
{{< /details >}}

#### 3.1.2. M Family (consistent performance)

Instances with consistent CPU without a credit system.

{{< details title="When to use" >}}
- Workloads that need constant and predictable CPU
- Critical production environments
- Applications that use full CPU continuously
{{< /details >}}

### 3.2. Compute optimized

Designed with high-performance processors, these instances offer the highest CPU/memory ratio among all families, ideal for workloads demanding intensive computational power.

#### 3.2.1. C Family (compute)

Latest generation processors with high clock speed, optimized for CPU-intensive workloads. Best cost per vCPU.

{{< details title="When to use" >}}
- "CPU-bound" applications (limited by processing)
- Workloads that process data intensively
- When CPU is the critical resource, not memory
{{< /details >}}

### 3.3. Memory optimized

Designed to provide large amounts of RAM relative to CPU cores, these instances are ideal for workloads that process extensive in-memory datasets.


#### 3.3.1. R Family (RAM-optimized)

The most popular for memory-demanding workloads. Offers **8 GB of RAM per vCPU** (double that of general purpose).

#### 3.3.2. X Family (extreme memory)

Extreme memory with up to **16 GB of RAM per vCPU** and configurations of **4+ TB** per instance.

{{< details title="When to use" >}}
- Massive in-memory databases (SAP HANA)
- Legacy applications that don't scale horizontally
- Consolidation of large workloads on few servers
{{< /details >}}

#### 3.3.3. z1d Family (high compute + high memory)

Combines high CPU frequency (up to 4.0 GHz) with plenty of memory and local NVMe.

{{< details title="When to use" >}}
- Databases requiring high CPU and memory
- High-volume OLTP workloads
- Workloads needing fast processing and lots of RAM
{{< /details >}}

### 3.4. Storage optimized

Designed to provide ultra-high performance local storage with fast sequential access and extremely high IOPS (input/output operations per second), these instances are ideal for workloads requiring intensive data read/write operations.


#### 3.4.1. I Family (I/O intensive)

Local NVMe SSD with ultra-low latency and millions of IOPS. I4i instances deliver up to **60 GB/s** and **400k+ IOPS**.

{{< details title="When to use" >}}
- High-volume transactional databases
- Applications needing sub-millisecond latency
- Critical OLTP workloads
{{< /details >}}

#### 3.4.2. D Family (dense storage)

HDD optimized for sequential throughput with the highest storage density per cost (tens of TB per instance).

{{< details title="When to use" >}}
- Data lakes
- Historical log archives
- MapReduce processing
- Data warehouses with sequential scans
- Massive local storage
{{< /details >}}

#### 3.4.3. H1 Family (HDD optimized)

Optimized for big data frameworks (Hadoop, Spark) with focus on sequential throughput.

{{< details title="When to use" >}}
- Distributed processing clusters
- Workloads where cost per TB is critical
- Scenarios where latency is not the main bottleneck
{{< /details >}}

{{< hint warning >}}
**⚠️ Ephemeral storage**: The storage on these instances is local and temporary (instance store). If the instance is stopped or terminated, all data is lost. Use EBS or S3 for long-term persistence.
{{< /hint >}}

### 3.5. Accelerated computing

Equipped with specialized hardware like GPUs, FPGAs, or AWS custom chips, these instances are designed to perform massive parallel calculations that would be inefficient or extremely slow on traditional CPUs.

#### 3.5.1. P Family (performance GPU - NVIDIA)

High-performance NVIDIA GPUs (A100, V100, H100) for model training and scientific computing.

{{< details title="When to use" >}}
- Deep neural network training
- AI research
- Molecular dynamics simulations
- Complex scientific data analysis
{{< /details >}}

#### 3.5.2. G Family (graphics - general purpose GPU)

NVIDIA GPUs (T4, A10G) balanced for both machine learning and graphics computing.

{{< details title="When to use" >}}
- Virtual workstations
- Game streaming
- Video rendering
- ML model inference in production
- Applications combining graphics and AI
{{< /details >}}

#### 3.5.3. Inf Family (AWS Inferentia)

AWS custom chips optimized exclusively for ML model inference (not training).

{{< details title="When to use" >}}
- Product recommendations
- Image classification
- Chatbots
- Fraud detection
- Deploying pre-trained models in production
{{< /details >}}

#### 3.5.4. Trn Family (AWS Trainium)

AWS custom chips for deep learning training with better cost-effectiveness than GPUs.

{{< details title="When to use" >}}
- Language model training (LLMs)
- Computer vision models
- Distributed training workloads
{{< /details >}}

#### 3.5.5. F Family (FPGA - Field Programmable Gate Arrays)

Programmable FPGAs that allow creating custom hardware for specific algorithms.

{{< details title="When to use" >}}
- High-frequency financial data processing
- Real-time compression/decompression
- Cryptographic algorithm acceleration
- Network analysis and security
{{< /details >}}

{{< hint warning >}}
**💰 High cost**: These are the most expensive AWS instances. A single P5 instance can cost over $30/hour. Make sure you really need this computational power.
{{< /hint >}}

### 3.6. Understanding instance names

Example: `m5zn.xlarge`

| Segment  | Meaning                     |
|----------|----------------------------|
| `m`      | Family: general purpose     |
| `5`      | Generation (higher = newer) |
| `z`      | Special attribute: high frequency |
| `n`      | Network optimization        |
| `xlarge` | Instance size               |

#### 3.6.1. Available sizes

- Range from `nano` to `32xlarge` (128 vCPUs and 1024 GiB of memory)
- Size defines CPU, memory, network, and storage resources

### 3.7. Common suffixes

| Suffix | Meaning                          |
|--------|----------------------------------|
| `a`    | AMD processor                    |
| `g`    | AWS Graviton                     |
| `i`    | Intel processor                  |
| `d`    | Local storage (instance store)   |
| `n`    | Network optimization             |
| `b`    | Block storage optimization       |
| `e`    | More memory or storage           |
| `z`    | High CPU frequency               |

## 4. Selecting the right instance type (right-sizing)

Amazon EC2 offers a wide variety of instance types, and often you'll find that your workload can run well on different instance types and sizes.

The goal of _right-sizing_ is to **balance performance and cost** based on your application's actual needs, preventing the instance from being overloaded or underutilized.

### 4.1. Benefits of newer generations

{{< hint info >}}
**🚀 Better cost-effectiveness**: Using newer generation instances with AWS's latest processors can bring better performance and lower cost.
{{< /hint >}}

### 4.2. Changing the instance as needed

After choosing an instance, **you're not obligated to use it forever**. If your workload changes, you can resize the instance by changing its type if it's overloaded or underutilized.

{{< hint warning >}}
**⚠️ Resizing considerations**: Some instances allow type changes with the instance running. Others require the instance to be stopped before changing. You can also create a new instance and migrate your application to it.
{{< /hint >}}

## 5. AWS Compute Optimizer

**AWS Compute Optimizer** is a _right-sizing_ tool that helps improve your AWS infrastructure efficiency by providing sizing recommendations focused on performance and cost.

It analyzes your current resource configuration and utilization metrics such as CPU, memory, and storage usage based on data collected by **Amazon CloudWatch** over the last **14 days**.

{{< details title="How Compute Optimizer works" >}}
During analysis, the service identifies specific workload patterns and characteristics, such as:
- Intensive CPU usage
- Frequent local storage access
- Usage variations throughout the day

With this information, **Compute Optimizer** can determine which hardware resources are most suitable for each workload, suggesting adjustments that can reduce costs and improve performance.
{{< /details >}}

{{< hint info >}}
**💡 No additional cost**: Compute Optimizer has no additional cost by default.
{{< /hint >}}
