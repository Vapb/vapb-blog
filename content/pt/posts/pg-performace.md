---
title: "Performance no PostgreSQL: do diagnóstico à otimização"
author: "vapb"
description: "JOINs, EXPLAIN, índices e connection pooling: identifique e resolva gargalos no PostgreSQL."
date: 2026-02-21
tags: ["postgresql", "performance"]
toc: true
---

## Introdução

PostgreSQL é rápido. O problema quase nunca é o banco em si é como a aplicação o usa.

Na maioria dos casos, o gargalo vem de três lugares: queries sem índice que lêem tabelas inteiras, memória mal dimensionada que força o banco a ir ao disco, ou conexões sem pooling que desperdiçam recursos a cada request.

Este post segue um fluxo prático: primeiro entender como o PostgreSQL executa queries, depois identificar o que causa lentidão, aprender a diagnosticar com `EXPLAIN`, e por fim aplicar as soluções certas.

## Como o PostgreSQL processa queries

Dois conceitos aparecem em praticamente todo problema de performance: `work_mem` e os métodos de JOIN. Entendê-los ajuda a interpretar o que o `EXPLAIN` vai mostrar.

### work_mem: memória por operação

Memória alocada **por operação** (sort, hash join) **por query**.

```sql
SHOW work_mem;  -- Padrão: 4MB ou 64MB
```

### Métodos de JOIN

PostgreSQL escolhe automaticamente entre 3 métodos dependendo do tamanho das tabelas e índices disponíveis.

* **Nested Loop**: para cada linha da tabela A, busca no índice de B. Ótimo para tabelas pequenas com índice — desastre em tabelas grandes sem índice.
* **Hash Join**: lê B inteira, cria uma hash table na RAM, depois varre A buscando matches. Ideal para tabelas grandes, mas a hash table precisa caber no `work_mem`.
* **Merge Join**: ordena as duas tabelas e percorre juntas. Eficiente em memória e escala bem — mas paga o custo do sort se não há índice.

| Método | ✅ Melhor cenário | ❌ Pior cenário |
|--------|------------------|----------------|
| Nested Loop | Pequena × Grande com índice | Grande × Grande sem índice |
| Hash Join | Grande × Grande (cabe em RAM) | Hash não cabe → spill para disco |
| Merge Join | Dados já ordenados / com índice | Precisa ordenar tudo antes |


## O que causa lentidão

### Problemas mais comuns

* **Sequential scans**: lê tabela inteira → criar índice
* **Dead tuples**: bloat → `VACUUM ANALYZE` + autovacuum agressivo
* **JOINs ruins**: sem índice → planner escolhe método errado
* **Locks**: transações travando → fazer mais curtas

### Os 5 bottlenecks

| Bottleneck | Solução imediata |
|------------|------------------|
| CPU | Materialized views, read replicas |
| I/O | Criar índices, aumentar `shared_buffers` |
| Memória | Aumentar `shared_buffers` (25% RAM) |
| Network | Connection pooling, mesma região |
| Locks | Transações curtas, batch menor |

## Diagnosticando queries com EXPLAIN

### O que é query plan?

**Query plan** = árvore de operações que o PostgreSQL vai executar. Ver esse plano é a forma mais direta de encontrar gargalos: ele mostra exatamente o que o banco faz, em que ordem, e quanto custa.

### EXPLAIN: 3 níveis de detalhe

**1. EXPLAIN (só estimativa)**

Mostra o plano estimado sem executar a query.
* Tipo de operação (Seq Scan, Index Scan)
* Custo estimado
* Rows estimadas

**2. EXPLAIN ANALYZE (executa de verdade)**

Mostra:
* Tempo real de execução
* Rows reais (vs estimadas)

**3. EXPLAIN (ANALYZE, BUFFERS) (completo)**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE customer_id = 123;
```

**Mostra onde buscou dados**:
```markdown
Buffers: shared hit=235 read=7890
```
* `shared hit` = memória (RAM) ✅
* `read` = disco ❌
* **Neste exemplo**: 7890 leituras de disco vs 235 de memória -> cache hit ratio crítico. Revise índices ou aumente `shared_buffers`.

### Sinais de problema no EXPLAIN

#### 1. Estimado ≠ real
```markdown
Estimated rows: 100
Actual rows: 50.000
```
**Solução**: `ANALYZE tabela;`

#### 2. Sequential scan inesperado
```markdown
Seq Scan on orders (rows=1000000)
```
**Solução**: Criar índice

#### 3. Alto buffer read (disco)
```markdown
Buffers: shared hit=10 read=5000
```
**Solução**: Aumentar `shared_buffers` ou criar índices

#### 4. Sort spillando (temp files)
```markdown
Sort Method: external merge  Disk: 50MB
```
**Problema**: Sort não coube em `work_mem`, foi pro disco.

**Solução**: `SET work_mem = '256MB';`

#### 5. Filtros pós-join
```markdown
Rows Removed by Join Filter: 100.000
```
**Problema**: Fez join ANTES de filtrar.

**Solução**: Mover WHERE pra antes do JOIN.

### Opções do EXPLAIN

| Opção | O que faz |
|-------|-----------|
| ANALYZE | Executa query, mostra tempo real |
| BUFFERS | Mostra memória vs disco |
| VERBOSE | Detalhes extras |
| FORMAT JSON | Saída em JSON |

## Índices: o essencial

### Tipos principais

**B-tree (padrão, 95% dos casos)**:
```sql
CREATE INDEX idx_customer ON orders(customer_id);
-- Usa pra: =, >, <, BETWEEN, ORDER BY
```

**BRIN (tabelas gigantes com dados ordenados)**:
```sql
CREATE INDEX idx_date ON logs USING BRIN(created_at);
-- Muito pequeno! Timestamps, IDs sequenciais
```

**GIN (arrays, JSON, full-text)**:
```sql
CREATE INDEX idx_tags ON posts USING GIN(tags);
```

### Estratégias avançadas

**Índice composto (ordem importa!)**:
```sql
-- ✅ Igualdade → Range → ORDER BY
CREATE INDEX idx_orders
ON orders(status, customer_id, order_date);
```

**Covering index (query nem toca na tabela)**:
```sql
CREATE INDEX idx_orders_covering
ON orders(customer_id)
INCLUDE (order_date, total);

-- Usa tudo do índice!
SELECT order_date, total
FROM orders
WHERE customer_id = 123;
```

**Partial index (só subset)**:
```sql
CREATE INDEX idx_active_orders
ON orders(customer_id)
WHERE status = 'active';
-- 90% completo? Usa só 10% espaço!
```

### Problemas comuns

**Índices não usados (overhead)**:
```sql
SELECT indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;  -- Nunca usado!

DROP INDEX idx_nao_usado;
```

**Index bloat (inchado)**:
```sql
-- Detectar
SELECT * FROM pgstattuple('idx_nome');
-- dead_tuple_percent > 40% = BLOAT!

-- Corrigir (sem travar tabela)
REINDEX INDEX CONCURRENTLY idx_nome;
```

**Colunas não seletivas (inútil)**:
```sql
-- ❌ RUIM
CREATE INDEX idx_gender ON users(gender);
-- gender = 'M'/'F' (50% cada) = não ajuda!

-- Índice só vale se retorna < 15% da tabela
```

## Otimizações essenciais

### 1. Estatísticas (sempre atualizadas!)

```sql
ANALYZE tabela;  -- Roda semanal ou após grandes cargas
```

### 2. Parâmetros críticos

```ini
# postgresql.conf
random_page_cost = 1.5              # SSD (padrão 4 é HDD)
default_statistics_target = 200     # Queries complexas
work_mem = 64MB                     # ⚠️ Por operação!
shared_buffers = 8GB                # 25% RAM
```

## Connection pooling

### O problema

Criar conexão PostgreSQL é caro (CPU, memória, tempo).

```python
# ❌ SEM POOLING (cria/fecha toda vez)
for _ in range(100):
    conn = psycopg2.connect(host="localhost", database="mydb")
    # query
    conn.close()
# = 100 conexões criadas/fechadas = LENTO!
```

### A solução

Pool de conexões reutilizadas:

```python
# ✅ COM POOLING (reutiliza)
from psycopg2 import pool

db_pool = pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host="localhost",
    database="mydb"
)

# Usar
conn = db_pool.getconn()
try:
    # queries
finally:
    db_pool.putconn(conn)  # SEMPRE devolver!
```

### Benefícios

1. **Performance** - Não cria/fecha repetidamente
2. **Limita conexões** - PostgreSQL tem limite (default: 100)
3. **Escalabilidade** - 1000 clientes com 20 conexões
4. **Custo** - Menos recursos

## TL;DR

| Sintoma | Causa provável | Ação |
|---------|---------------|------|
| Query lenta sem índice | Sequential scan | `CREATE INDEX` na coluna do WHERE |
| Sort spillando para disco | `work_mem` baixo | `SET work_mem = '256MB'` |
| Cache hit ratio < 99% | `shared_buffers` insuficiente | Aumentar para 25% da RAM |
| Hash Join lento | Hash table não coube na RAM | Aumentar `work_mem` ou criar índice |
| Estimado ≠ real no EXPLAIN | Estatísticas desatualizadas | `ANALYZE tabela;` |
| Queries lentas + bloat | Autovacuum não acompanha | Tunar `autovacuum_vacuum_scale_factor` |
| Muitas conexões | Sem pooling | PgBouncer ou pool na aplicação |
| Locks frequentes | Transações longas | Quebrar em transações menores |

💡 Diagnóstico padrão: `EXPLAIN (ANALYZE, BUFFERS)` → identifica o gargalo → aplica a correção da tabela acima.
