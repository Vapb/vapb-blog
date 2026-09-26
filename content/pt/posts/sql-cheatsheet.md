---
title: "SQL Cheatsheet: Queries Avançadas e Operações Essenciais"
author: "vapb"
description: "Cheatsheet prático de SQL (PostgreSQL)."
date: 2025-12-21
tags: ["database", "postgresql"]
toc: true
---

## Introdução

Referência rápida de SQL focada no que eu realmente uso no dia a dia. O básico está comprimido; o espaço vai para padrões, receitas e pegadinhas. Baseado em PostgreSQL, mas quase tudo roda em outros bancos relacionais.

---

## Ordem de Execução

A query é **escrita** numa ordem e **executada** em outra. É isso que explica por que você não pode usar um alias do SELECT no WHERE.

```
FROM / JOIN → WHERE → GROUP BY → HAVING → SELECT → window functions → DISTINCT → ORDER BY → LIMIT
```

- Filtrar **antes** de agregar → `WHERE`. Filtrar **depois** de agregar → `HAVING`.
- Filtrar pelo resultado de uma window function → envolva em subquery/CTE (não dá para usar no WHERE).
- Alias do SELECT funciona no `ORDER BY`, mas não no `WHERE`, `GROUP BY` (no padrão SQL) nem no `HAVING`.

---

## O Básico em Um Bloco

```sql
SELECT DISTINCT c.name, o.total AS valor
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.total BETWEEN 100 AND 500              -- inclusivo nas duas pontas
  AND o.status IN ('paid', 'shipped')
  AND c.email ILIKE '%@gmail.com'              -- ILIKE = case-insensitive (PG)
  AND c.name LIKE 'J_o%'                       -- % = qualquer coisa, _ = 1 char
  AND o.deleted_at IS NULL
ORDER BY o.total DESC NULLS LAST, c.name       -- ASC é o padrão
LIMIT 20 OFFSET 40;                            -- página 3 de 20
```

---

## Armadilhas de NULL

A maior fonte de bugs silenciosos em SQL.

```sql
WHERE col = NULL              -- ❌ nunca é true. Use: col IS NULL
WHERE col <> 'x'              -- ❌ NÃO retorna rows onde col é NULL
WHERE col IS DISTINCT FROM 'x' -- ✅ trata NULL como valor comparável

-- ❌ NOT IN com NULL na subquery retorna ZERO rows
WHERE id NOT IN (SELECT customer_id FROM orders)   -- se algum customer_id for NULL, quebra
-- ✅ Use NOT EXISTS
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)

COUNT(*)                      -- conta rows
COUNT(col)                    -- ignora NULLs
AVG(col)                      -- ignora NULLs (não conta como 0!)
SUM(col)                      -- retorna NULL se não houver rows → COALESCE(SUM(col), 0)

COALESCE(phone, email, '-')   -- primeiro não-NULL
x / NULLIF(y, 0)              -- divisão segura (retorna NULL em vez de erro)
```

**Bônus – divisão inteira:** `1 / 2 = 0`. Use `1.0 / 2` ou `col::numeric / total`.

---

## Joins

| Join | Retorna |
|------|---------|
| `INNER JOIN` | Só rows com match nos dois lados |
| `LEFT JOIN` | Tudo da esquerda + match da direita (NULL se não houver) |
| `RIGHT JOIN` | Espelho do LEFT (prefira reescrever como LEFT) |
| `FULL JOIN` | Tudo dos dois lados |
| `CROSS JOIN` | Produto cartesiano |

```sql
-- Anti-join: clientes sem pedidos
SELECT c.* FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);

-- ⚠️ Pegadinha: filtro na tabela da direita no WHERE vira INNER JOIN
SELECT c.name, o.id
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.status = 'paid';  -- ✅ filtro no ON
-- WHERE o.status = 'paid'  ❌ elimina clientes sem pedidos

-- LATERAL: subquery que "enxerga" a row externa (ex: últimos 3 pedidos por cliente)
SELECT c.name, o.*
FROM customers c
CROSS JOIN LATERAL (
    SELECT id, total, created_at FROM orders
    WHERE customer_id = c.id
    ORDER BY created_at DESC
    LIMIT 3
) o;
```

**Join multiplicando rows?** Um dos lados tem mais de um match por chave. Agregue antes de juntar (CTE/subquery) em vez de usar `DISTINCT` para esconder o problema.

---

## Agregações

```sql
SELECT
    category,
    COUNT(*)                                   AS total,
    COUNT(DISTINCT customer_id)                AS clientes_unicos,
    SUM(total)                                 AS receita,
    ROUND(AVG(total), 2)                       AS ticket_medio,
    COUNT(*) FILTER (WHERE status = 'paid')    AS pagos,        -- agregação condicional
    SUM(total) FILTER (WHERE status = 'paid')  AS receita_paga,
    STRING_AGG(DISTINCT name, ', ' ORDER BY name) AS nomes,     -- concatena
    ARRAY_AGG(id ORDER BY created_at)          AS ids,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total) AS mediana
FROM orders
GROUP BY category
HAVING COUNT(*) > 10;

-- Subtotais + total geral numa query só
SELECT region, category, SUM(total)
FROM sales
GROUP BY ROLLUP (region, category);   -- NULL nas colunas = linha de subtotal
-- CUBE(a, b) = todas as combinações | GROUPING SETS ((a), (b), ()) = escolhe quais
```

### DISTINCT ON (PostgreSQL)

A forma mais curta de pegar "a row mais recente por grupo":

```sql
SELECT DISTINCT ON (customer_id) customer_id, id, total, created_at
FROM orders
ORDER BY customer_id, created_at DESC;  -- ORDER BY deve começar pelas colunas do DISTINCT ON
```

---

## CASE

```sql
SELECT
    CASE
        WHEN total < 50  THEN 'small'
        WHEN total < 100 THEN 'medium'   -- avalia em ordem, para no primeiro true
        ELSE 'large'
    END AS order_size,
    CASE status WHEN 'paid' THEN 1 ELSE 0 END AS is_paid  -- forma curta
FROM orders;

-- Ordenação customizada
ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END;
```

---

## Subqueries & CTEs

```sql
-- Scalar: acima da média
SELECT * FROM products WHERE price > (SELECT AVG(price) FROM products);

-- Correlacionada: acima da média DA SUA categoria (roda por row → prefira window function)
SELECT * FROM products p
WHERE price > (SELECT AVG(price) FROM products WHERE category = p.category);

-- CTE: subquery nomeada, deixa a query legível de cima para baixo
WITH receita_mensal AS (
    SELECT date_trunc('month', created_at) AS mes, SUM(total) AS receita
    FROM orders
    GROUP BY 1
)
SELECT mes, receita,
       receita - LAG(receita) OVER (ORDER BY mes) AS variacao
FROM receita_mensal;
```

### CTE Recursiva (hierarquias, árvores)

```sql
WITH RECURSIVE org AS (
    SELECT id, name, manager_id, 1 AS nivel          -- âncora: o topo
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.id, e.name, e.manager_id, org.nivel + 1 -- passo recursivo
    FROM employees e
    JOIN org ON e.manager_id = org.id
)
SELECT * FROM org ORDER BY nivel;
```

### MATERIALIZED

Desde o PG12, CTEs usadas uma única vez são "inlined" automaticamente. Force o comportamento se precisar:

```sql
WITH MATERIALIZED x AS (...)      -- calcula 1x e reutiliza (bom se é caro e usado várias vezes)
WITH NOT MATERIALIZED x AS (...)  -- deixa o otimizador empurrar filtros para dentro
```

---

## Window Functions

Calculam sobre um conjunto de rows **sem colapsar** o resultado (diferente do GROUP BY).

```sql
func() OVER (PARTITION BY grupo ORDER BY coluna ROWS BETWEEN ... AND ...)
```

| Função | Faz |
|--------|-----|
| `ROW_NUMBER()` | 1, 2, 3, 4 (único, empate desempatado arbitrariamente) |
| `RANK()` | 1, 2, 2, 4 (pula após empate) |
| `DENSE_RANK()` | 1, 2, 2, 3 (não pula) |
| `NTILE(4)` | Divide em quartis |
| `LAG(col, n, default)` / `LEAD(...)` | Valor da row anterior / seguinte |
| `FIRST_VALUE` / `LAST_VALUE` | Primeiro / último da janela |
| `SUM/AVG/COUNT() OVER` | Agregação sem colapsar |

```sql
SELECT
    order_date, amount,
    SUM(amount) OVER (ORDER BY order_date)                          AS acumulado,
    AVG(amount) OVER (ORDER BY order_date
                      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)     AS media_movel_7d,
    amount * 100.0 / SUM(amount) OVER ()                            AS pct_do_total,
    amount - LAG(amount) OVER (ORDER BY order_date)                 AS delta,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS n_pedido_cliente
FROM orders;

-- Reutilizar a mesma janela
SELECT SUM(x) OVER w, AVG(x) OVER w FROM t WINDOW w AS (PARTITION BY g ORDER BY d);
```

⚠️ **LAST_VALUE pegadinha:** com `ORDER BY`, o frame padrão vai só até a row atual. Use `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` ou inverta a ordenação e use `FIRST_VALUE`.

---

## Receitas Prontas

### Top N por grupo

```sql
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC) AS rn
    FROM products
) t
WHERE rn <= 3;
```

### Remover duplicatas (mantendo a mais recente)

```sql
-- Ver duplicatas
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;

-- Deletar, mantendo o maior id
DELETE FROM users
WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY email ORDER BY id DESC) AS rn
        FROM users
    ) t WHERE rn > 1
);
```

### Pivot (linhas → colunas)

```sql
SELECT
    product_id,
    SUM(amount) FILTER (WHERE EXTRACT(MONTH FROM sold_at) = 1) AS jan,
    SUM(amount) FILTER (WHERE EXTRACT(MONTH FROM sold_at) = 2) AS fev,
    SUM(amount) FILTER (WHERE EXTRACT(MONTH FROM sold_at) = 3) AS mar
FROM sales
GROUP BY product_id;
```

### Preencher dias sem dados (série de datas)

```sql
SELECT d::date AS dia, COALESCE(SUM(o.total), 0) AS receita
FROM generate_series('2025-01-01'::date, '2025-01-31'::date, '1 day') d
LEFT JOIN orders o ON o.created_at::date = d::date
GROUP BY d
ORDER BY d;
```

### Dias consecutivos (gaps & islands)

```sql
-- Sequências de dias seguidos de login por usuário
SELECT user_id, MIN(dia) AS inicio, MAX(dia) AS fim, COUNT(*) AS dias
FROM (
    SELECT user_id, dia,
           dia - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY dia)::int AS grp
    FROM (SELECT DISTINCT user_id, login_at::date AS dia FROM logins) x
) t
GROUP BY user_id, grp;
```

### Crescimento mês a mês

```sql
SELECT mes, receita,
       ROUND(100.0 * (receita - LAG(receita) OVER (ORDER BY mes))
             / NULLIF(LAG(receita) OVER (ORDER BY mes), 0), 1) AS crescimento_pct
FROM (
    SELECT date_trunc('month', created_at) AS mes, SUM(total) AS receita
    FROM orders GROUP BY 1
) t;
```

### Paginação por cursor (keyset)

`OFFSET` alto é lento (o banco lê e descarta todas as rows anteriores). Use a última row da página como cursor:

```sql
SELECT * FROM posts
WHERE (created_at, id) < ('2025-06-01 10:00', 1234)   -- valores da última row vista
ORDER BY created_at DESC, id DESC
LIMIT 20;
-- Index: (created_at DESC, id DESC)
```

---

## Datas

```sql
NOW()                                   -- timestamptz atual
CURRENT_DATE                            -- data de hoje
NOW() - INTERVAL '7 days'
date_trunc('month', ts)                 -- 2025-06-17 14:32 → 2025-06-01 00:00
EXTRACT(YEAR FROM ts)                   -- também: MONTH, DOW, WEEK, EPOCH
EXTRACT(EPOCH FROM (fim - inicio))      -- diferença em segundos
AGE(birth_date)                         -- intervalo "32 years 4 mons"
to_char(ts, 'DD/MM/YYYY HH24:MI')       -- formatar
ts AT TIME ZONE 'America/Sao_Paulo'     -- converter fuso
```

⚠️ **Filtro por período:** não aplique função na coluna, senão o index não é usado.

```sql
WHERE date_trunc('month', created_at) = '2025-01-01'           -- ❌ não usa index
WHERE created_at >= '2025-01-01' AND created_at < '2025-02-01' -- ✅ usa index
```

---

## Strings

```sql
'a' || 'b'                              -- concatenar (NULL || 'x' = NULL)
CONCAT_WS(' ', first, middle, last)     -- concatena ignorando NULLs
LOWER(s), UPPER(s), TRIM(s), LENGTH(s)
LEFT(s, 3), RIGHT(s, 3), SUBSTRING(s FROM 2 FOR 3)
SPLIT_PART('a@b.com', '@', 2)           -- 'b.com'
REPLACE(s, 'de', 'para')
REGEXP_REPLACE(phone, '\D', '', 'g')    -- remove tudo que não é dígito
s ~ '^\d{5}-\d{3}$'                     -- regex match (~* = case-insensitive)
POSITION('x' IN s)
```

---

## JSONB

```sql
data -> 'address'                 -- retorna JSONB
data ->> 'name'                   -- retorna TEXT
data #>> '{address,city}'         -- caminho aninhado como TEXT
(data ->> 'age')::int             -- cast

WHERE data @> '{"plan": "premium"}'   -- contém (usa index GIN)
WHERE data ? 'phone'                  -- chave existe

jsonb_build_object('id', id, 'name', name)       -- montar objeto
jsonb_agg(row_to_json(t))                        -- agregar rows em array JSON
jsonb_array_elements(data -> 'items')            -- explodir array em rows
data || '{"verified": true}'                     -- merge
data - 'password'                                -- remover chave
jsonb_set(data, '{address,city}', '"SP"')        -- atualizar caminho
```

---

## Escrita: INSERT, UPDATE, DELETE

```sql
-- RETURNING: pega o resultado sem SELECT extra
INSERT INTO users (email, name) VALUES ('a@b.com', 'Ana') RETURNING id;

-- INSERT a partir de SELECT
INSERT INTO archive_orders SELECT * FROM orders WHERE created_at < '2024-01-01';

-- UPDATE com join
UPDATE orders o
SET priority = 'high'
FROM customers c
WHERE o.customer_id = c.id AND c.tier = 'gold';

-- DELETE com join
DELETE FROM sessions s
USING users u
WHERE s.user_id = u.id AND u.status = 'banned';
```

⚠️ **Antes de UPDATE/DELETE em produção:** rode como `SELECT` com o mesmo `WHERE`, e faça dentro de `BEGIN;` para poder dar `ROLLBACK`.

### UPSERT (INSERT ... ON CONFLICT)

Insere ou atualiza atomicamente. Requer UNIQUE constraint ou PK nas colunas do conflito.

```sql
INSERT INTO users (email, name, last_login)
VALUES ('user@example.com', 'John', NOW())
ON CONFLICT (email) DO UPDATE SET
    name       = EXCLUDED.name,          -- EXCLUDED = valores que tentou inserir
    last_login = EXCLUDED.last_login
WHERE users.name IS DISTINCT FROM EXCLUDED.name;   -- opcional: só escreve se mudou

-- Ignorar duplicatas (idempotência / dedup de eventos)
INSERT INTO events (event_id, payload) VALUES ('evt_123', '{}')
ON CONFLICT (event_id) DO NOTHING;

-- Contador incremental
INSERT INTO api_usage (api_key, day, requests) VALUES ('k1', CURRENT_DATE, 1)
ON CONFLICT (api_key, day) DO UPDATE SET requests = api_usage.requests + 1
RETURNING requests;
```

Bulk: use um único `INSERT ... VALUES (...), (...), ...` ou `INSERT ... SELECT` em vez de loop com um INSERT por row.

---

## Transações & Locks

```sql
BEGIN;
    UPDATE accounts SET balance = balance - 100 WHERE id = 1;
    SAVEPOINT sp1;
    UPDATE accounts SET balance = balance + 100 WHERE id = 2;
    -- deu ruim? ROLLBACK TO SAVEPOINT sp1;
COMMIT;   -- ou ROLLBACK;
```

```sql
-- Travar rows para ler-e-atualizar sem race condition
SELECT * FROM seats WHERE seat = 'A1' FOR UPDATE;

-- Fila de jobs com múltiplos workers (cada worker pega jobs diferentes)
SELECT id FROM jobs
WHERE status = 'pending'
ORDER BY id
LIMIT 10
FOR UPDATE SKIP LOCKED;

-- Não esperar lock para sempre
SET lock_timeout = '5s';
SET statement_timeout = '30s';
```

| Isolation level | Na prática (PG) |
|-----------------|-----------------|
| `READ COMMITTED` | **Padrão.** Cada statement vê dados commitados até ele começar |
| `REPEATABLE READ` | Snapshot fixo da transação inteira. Pode falhar com erro de serialização → retry |
| `SERIALIZABLE` | Como se rodasse uma por vez. Mais seguro, exige retry |
| `READ UNCOMMITTED` | No PG se comporta igual a READ COMMITTED |

---

## Indexes

Aceleram leitura, custam espaço e deixam escrita mais lenta.

| Tipo | Quando usar |
|------|-------------|
| **B-tree** (padrão) | `=`, `<`, `>`, `BETWEEN`, `ORDER BY`, `LIKE 'abc%'` |
| **GIN** | JSONB (`@>`, `?`), arrays, full-text search, `pg_trgm` para `LIKE '%abc%'` |
| **GiST** | Geometria (PostGIS), ranges, exclusion constraints |
| **BRIN** | Tabelas enormes append-only ordenadas fisicamente (logs, time-series). Minúsculo |
| **Hash** | Só `=`. Raramente vale sobre B-tree |

```sql
CREATE INDEX idx_orders_customer ON orders (customer_id);                -- sempre indexe FKs
CREATE INDEX idx_orders_cust_date ON orders (customer_id, created_at);   -- composto
CREATE UNIQUE INDEX idx_users_email ON users (LOWER(email));             -- expressão + unique
CREATE INDEX idx_active ON users (email) WHERE status = 'active';        -- parcial
CREATE INDEX idx_cover ON orders (customer_id) INCLUDE (total, status);  -- covering (index-only scan)
CREATE INDEX idx_meta ON users USING GIN (metadata);                     -- JSONB
CREATE INDEX CONCURRENTLY idx_x ON big_table (col);                      -- sem travar writes (fora de transação)
```

**Regras do index composto `(a, b, c)`:**
- Serve para filtros em `a`, `a + b`, `a + b + c`. **Não** serve para `b` sozinho (leftmost prefix).
- Coloque colunas de **igualdade primeiro** e a de **range/ORDER BY por último**: `WHERE status = 'x' AND created_at > ...` → `(status, created_at)`.

**Coisas que impedem o uso do index:**
- Função na coluna (`WHERE LOWER(email) = ...` sem index de expressão)
- `LIKE '%abc'` (wildcard no começo) → use `pg_trgm`
- Cast implícito de tipo (`WHERE id_texto = 123`)
- Partial index cuja condição não aparece na query

### EXPLAIN

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;   -- executa de verdade! Cuidado com UPDATE/DELETE
```

| Nó | Significa |
|----|-----------|
| `Seq Scan` | Leu a tabela inteira (ok em tabela pequena ou quando retorna muitas rows) |
| `Index Scan` | Usou index + buscou na tabela |
| `Index Only Scan` | Tudo veio do index (ótimo) |
| `Bitmap Heap Scan` | Index para muitas rows, lê em lote |
| `Nested Loop` / `Hash Join` / `Merge Join` | Estratégias de join |

Sinal de alerta: `rows=` estimado muito diferente do `actual rows=` → estatísticas desatualizadas, rode `ANALYZE tabela;`.

---

## Functions, Procedures & Triggers

| | Function | Procedure |
|--|----------|-----------|
| Retorno | Sim (`RETURNS`) | Não (ou `OUT` params) |
| Chamada | Dentro de `SELECT`, `WHERE`... | `CALL nome(...)` |
| `COMMIT`/`ROLLBACK` dentro | Não | Sim |

```sql
-- Function
CREATE OR REPLACE FUNCTION preco_final(preco NUMERIC, desconto NUMERIC)
RETURNS NUMERIC LANGUAGE sql IMMUTABLE AS $$
    SELECT preco * (1 - desconto / 100);
$$;

SELECT name, preco_final(price, discount) FROM products;
```

```sql
-- Trigger clássico: updated_at automático
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

- `BEFORE` → validar/modificar `NEW`. `AFTER` → auditoria, side effects.
- Triggers são "mágica escondida": use pouco e documente.

### PL/pgSQL em Um Bloco

```sql
DO $$
DECLARE
    total NUMERIC := 0;
    rec   RECORD;
BEGIN
    FOR rec IN SELECT id, price FROM products LOOP      -- também: FOR i IN 1..10, WHILE, LOOP + EXIT WHEN
        IF rec.price > 100 THEN
            total := total + rec.price;
        ELSIF rec.price IS NULL THEN
            CONTINUE;
        END IF;
    END LOOP;
    RAISE NOTICE 'Total: %', total;                     -- DEBUG | NOTICE | WARNING | EXCEPTION
EXCEPTION
    WHEN unique_violation THEN RAISE NOTICE 'Duplicado';
    WHEN OTHERS THEN RAISE WARNING 'Erro: %', SQLERRM;
END;
$$;
```

Se dá para fazer com uma query só (set-based), não faça loop.

---

## Diagnóstico

```sql
-- Queries rodando agora (mais lentas primeiro)
SELECT pid, state, NOW() - query_start AS duracao, LEFT(query, 100)
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duracao DESC;

-- Quem está bloqueando quem
SELECT pid, pg_blocking_pids(pid) AS bloqueado_por, LEFT(query, 100)
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- Matar query
SELECT pg_cancel_backend(pid);      -- cancela a query (gentil)
SELECT pg_terminate_backend(pid);   -- derruba a conexão

-- Maiores tabelas (com indexes)
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS tamanho
FROM pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;

-- Indexes nunca usados (candidatos a DROP)
SELECT relname, indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Manutenção
VACUUM ANALYZE tabela;              -- limpa dead tuples + atualiza estatísticas
REINDEX INDEX CONCURRENTLY idx_x;   -- reconstrói index inchado
```

### psql

| Comando | Faz |
|---------|-----|
| `\l` / `\c db` | Listar bancos / conectar |
| `\dt` / `\d tabela` | Listar tabelas / descrever tabela |
| `\di` / `\df` / `\dn` | Indexes / functions / schemas |
| `\x auto` | Output vertical quando a linha é larga |
| `\timing` | Mostra tempo de cada query |
| `\e` | Abre a última query no editor |
| `\copy t TO 'f.csv' CSV HEADER` | Exportar CSV (também `FROM` para importar) |

---

## Performance: Checklist

1. **Indexe** colunas de `WHERE`, `JOIN` e `ORDER BY` — e todas as foreign keys.
2. **`EXPLAIN (ANALYZE, BUFFERS)`** antes de achar qualquer coisa.
3. **Não aplique função na coluna filtrada**; reescreva como range ou crie index de expressão.
4. **Selecione só as colunas necessárias** (evita I/O e permite index-only scan).
5. **`NOT EXISTS` em vez de `NOT IN`** (performance e NULL-safety).
6. **Keyset pagination** em vez de `OFFSET` alto.
7. **Window functions em vez de self-joins/subqueries correlacionadas.**
8. **Agregue antes de juntar** quando o join multiplica rows.
9. **Operações em lote** (bulk insert/upsert) em vez de loops row a row.
10. **Particione** tabelas gigantes por data para o planner pular partições inteiras.
