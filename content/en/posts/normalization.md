---
title: "Database Normalization in Relational Databases"
author: "vapb"
description: "An introduction to the concept of database normalization in relational databases and its normal forms."
date: 2025-12-20
tags: ["Database", "SQL"]
toc: true
---

## Introduction

Every developer has seen it: that table with 50 columns where half the data repeats in each row, or that update that needs to run in 5 different places because "the same data lives in multiple tables". Normalization solves these problems systematically, but introduces others: more complex queries, more joins, schemas less intuitive for those unfamiliar with the domain. This post covers normal forms, the normalization process, and when the benefits outweigh the costs.

## What is database normalization

Normalization is one of the most fundamental and frequently misunderstood concepts in database design.
It is the systematic process of organizing data in a relational database to reduce redundancy and improve integrity, through the decomposition of tables into smaller, well-defined structures, establishing clear relationships between them.
The central goal is to eliminate repeating groups of data and ensure that each element is stored logically and consistently.
However, it's crucial to understand that normalization is not an absolute end. In certain contexts, conscious denormalization may be necessary to meet specific performance requirements.

## Normal forms

The normalization process is structured in progressive levels, known as normal forms.
Each level adds constraints that increase data integrity.

### 1NF

A table is in 1NF when it satisfies three requirements:
* Primary key defined: Each record must be uniquely identifiable
* Atomicity of values: Each field contains only one value, not multiple values or repeating groups
* Type homogeneity: Values in each column must be of the same data type

Example of 1NF violation:
```sql
-- Table is NOT in 1NF
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer VARCHAR(100),
    phones VARCHAR(200)  -- "11-98765-4321, 11-3456-7890"
);

-- Correction to 1NF
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer VARCHAR(100)
);

CREATE TABLE order_phones (
    order_id INT REFERENCES orders(order_id),
    phone VARCHAR(20),
    PRIMARY KEY (order_id, phone)
);
```

### 2NF

A table is in 2NF when:
* It is in 1NF
* Every non-key attribute depends completely on the primary key
* No partial dependencies exist (attributes depending only on part of a composite key)

Example of 2NF violation:
```sql
-- Composite key: (employee_id, project_id)
CREATE TABLE employee_projects (
    employee_id INT,
    project_id INT,
    employee_name VARCHAR(100),  -- Depends ONLY on employee_id
    job_code VARCHAR(10),        -- Depends ONLY on employee_id
    project_name VARCHAR(100),   -- Depends ONLY on project_id
    hours_allocated INT,         -- Depends on the complete key
    PRIMARY KEY (employee_id, project_id)
);

-- Correction to 2NF
CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100),
    job_code VARCHAR(10)
);

CREATE TABLE projects (
    project_id INT PRIMARY KEY,
    project_name VARCHAR(100)
);

CREATE TABLE employee_projects (
    employee_id INT REFERENCES employees(employee_id),
    project_id INT REFERENCES projects(project_id),
    hours_allocated INT,
    PRIMARY KEY (employee_id, project_id)
);
```

### 3NF

A table is in 3NF when:
* It is in 2NF
* Every non-key attribute depends directly on the primary key
* No transitive dependencies exist (attributes depending on other non-key attributes)

```sql
-- Composite key: (employee_id, project_id)
CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100),
    state_code CHAR(2),
    state_name VARCHAR(50)  -- state_name depends on state_code, not on employee_id
);

-- Correction to 3NF
CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100),
    job_code VARCHAR(10)
);

CREATE TABLE projects (
    project_id INT PRIMARY KEY,
    project_name VARCHAR(100)
);

CREATE TABLE employee_projects (
    employee_id INT REFERENCES employees(employee_id),
    project_id INT REFERENCES projects(project_id),
    hours_allocated INT,
    PRIMARY KEY (employee_id, project_id)
);
```

### Boyce-Codd Normal Form (BCNF)

A table is in BCNF when:
* It is in 3NF
* Every determinant (set of attributes that uniquely identifies a row) is a candidate key

BCNF is a more restrictive version of 3NF that deals with specific dependency cases where 3NF still allows anomalies.
In practice, many schemas in 3NF already satisfy BCNF.

## The Normalization Process

* **Identify the Initial Structure**: Start with the table in non-normalized form, usually reflecting how data is collected or presented to the user.
* **Apply 1NF**: Eliminate repeating groups and ensure atomicity.
* **Apply 2NF**: Identify and eliminate partial dependencies. Attributes that depend only on part of the primary key should be moved to separate tables.
* **Apply 3NF**: Identify and eliminate transitive dependencies. Attributes that depend on other non-key attributes should be extracted to their own tables.
* **Validate BCNF (Optional)**: Verify that all determinants are candidate keys.

## Benefits of Normalization

1. **Redundancy Reduction**: Each fact is stored once, eliminating unnecessary data duplication. This saves storage space and reduces inconsistencies.
2. **Improved Integrity**: With non-redundant data, updates affect only one location. This eliminates update anomalies where the same data could be changed in some places but not in others.
3. **Simplified Maintenance**: Normalized schemas are easier to understand and modify. Adding new attributes or entities doesn't require changes to multiple tables.
4. **Facilitated Queries and Reporting**: Well-defined relationships through foreign keys make joins more intuitive and prevent invalid data combinations.
5. **Potentially Better Performance**: Although normalization may increase the number of joins, it also reduces the size of individual tables, improving cache efficiency and reducing I/O in many scenarios.

## When to Denormalize

Normalization to 3NF is generally the ideal goal, but there are legitimate scenarios for denormalization:
* **Data Warehouses and OLAP**: Dimensional schemas (star/snowflake) intentionally denormalize to optimize complex analytical queries.
* **Read-Heavy Workloads**: When specific queries are executed thousands of times per second, duplicating data can eliminate expensive joins.
* **Caching Computed Values**: Storing aggregated values (totals, averages) that would be expensive to calculate repeatedly.
