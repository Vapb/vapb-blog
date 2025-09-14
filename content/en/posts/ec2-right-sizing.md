---
title: "EC2 Instance Types and Right-Sizing"
author: "vapb"
description: "Guide to EC2 instance types, right-sizing, and AWS Compute Optimizer."
date: 2025-06-26
tags: ["AWS", "EC2"]
toc: true
---

## 1. Introduction

This post explores EC2 instance types, how to select the correct type, the concept of right-sizing, and the **AWS Compute Optimizer** tool.

## 2. EC2 Instance Families

Amazon EC2 offers **500+ instance types** organized into **families** and **subfamilies**. Each instance name indicates its function and available hardware resources.

### 2.1. The 5 Instance Families

#### 2.1.1. General Purpose
- **Balanced CPU, memory, and network**
- Use cases: web servers, code repositories
- **Burstable instances (T family)**: Good for intermittent workloads with baseline performance and temporary bursts

#### 2.1.2. Compute Optimized
- High-performance processors for CPU-intensive tasks:
  - Batch processing
  - Media transcoding
  - Gaming servers
  - Scientific modeling
  - Machine Learning inference

#### 2.1.3. Memory Optimized
- High performance for large in-memory datasets

#### 2.1.4. Storage Optimized
- Intensive sequential data access
- Optimized for high IOPS

#### 2.1.5. Accelerated Computing
- Use **GPUs, FPGAs, or AWS Inferentia** for:
  - Floating point calculations
  - Graphics processing
  - Pattern recognition

### 2.2. Understanding Instance Names

Example: `m5zn.xlarge`

| Segment  | Meaning                     |
| -------- | --------------------------- |
| `m`      | Family: general purpose     |
| `5`      | Generation (higher = newer) |
| `z`      | High frequency CPU          |
| `n`      | Network optimization        |
| `xlarge` | Instance size               |

{{<figure class="post_image" src="../images/ec2-right-sizing/ec2.png">}}

### 2.3. Common Suffixes

| Suffix | Meaning                        |
| ------ | ------------------------------ |
| `a`    | AMD processor                  |
| `g`    | AWS Graviton                   |
| `i`    | Intel processor                |
| `d`    | Local storage (Instance Store) |
| `n`    | Network optimization           |
| `b`    | Block storage optimization     |
| `e`    | Extra memory or storage        |
| `z`    | High CPU frequency             |

## 3. Right-Sizing

Right-sizing **balances performance and cost** based on your application's actual needs, avoiding over or under-utilized instances.

### 3.1. Benefits of Newer Generations
- Better performance
- Lower cost

### 3.2. Changing Instance Types
You can resize instances when workload requirements change. Some instances allow type changes while running, others require stopping the instance first.

> **Note**: You can also create a new instance and migrate your application to it.

## 4. AWS Compute Optimizer

**AWS Compute Optimizer** is a right-sizing tool that improves infrastructure efficiency by providing performance and cost-focused recommendations.

It analyzes current resource configuration and utilization metrics (CPU, memory, storage) using **Amazon CloudWatch** data from the last 14 days. The service identifies workload patterns and suggests optimal hardware resources to reduce costs and improve performance.

> **Note**: AWS Compute Optimizer is **free** by default.

## 5. TLDR

- **EC2 offers 500+ instance types** across 5 families: General Purpose, Compute Optimized, Memory Optimized, Storage Optimized, and Accelerated Computing
- **Instance names** follow pattern: `family + generation + attributes + size` (e.g., `m5zn.xlarge`)
- **Right-sizing** balances performance and cost by matching instance types to actual workload needs
- **AWS Compute Optimizer** provides free recommendations based on 14 days of CloudWatch metrics
- **Instance types can be changed** after deployment to optimize for changing requirements