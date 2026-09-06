---
title: "PostgreSQL Bloat: Entendendo, Identificando e Resolvendo o Problema Invisível"
author: "vapb"
description: "Bloat degrada performance silenciosamente no PostgreSQL. Aprenda como MVCC causa acúmulo de dados mortos, identifique tabelas problemáticas, configure autovacuum corretamente e proteja seu banco contra transaction ID wraparound."
date: 2026-01-10
tags: ["postgresql"]
toc: true
---

## Introdução
A manutenção adequada do **PostgreSQL** é fundamental para garantir performance, confiabilidade e longevidade do seu banco de dados.
Neste guia abrangente, vamos explorar desde os conceitos fundamentais de bloat até técnicas avançadas de gerenciamento de índices, passando por todos os aspectos críticos que todo DBA ou desenvolvedor precisa dominar.

## Entendendo o MVCC e Por Que Bloat Acontece

O PostgreSQL usa MVCC (Multi-Version Concurrency Control) para manter atomicidade e isolamento (duas propriedades ACID) quando múltiplas transações são processadas concorrentemente.
O mecanismo funciona assim:

Cada tupla (linha) possui um header com:
* xmin: Transaction ID que criou a tupla
* xmax: Transaction ID que deletou/atualizou a tupla

```sql
UPDATE usuarios SET email = 'novo@email.com' WHERE id = 1;
```

O PostgreSQL **NÃO modifica** a linha existente. Em vez disso:

1. Marca a linha antiga com `xmax = <XID_atual>` (morta)
2. Cria uma **nova versão** da linha com `xmin = <XID_atual>` (viva)

```markdown
ANTES:
┌─────────────────────────────┐
│ id=1, email='old@email.com' │
│ xmin=100, xmax=NULL         │ ← VIVA
└─────────────────────────────┘

DEPOIS:
┌─────────────────────────────┐
│ id=1, email='old@email.com' │
│ xmin=100, xmax=200          │ ← MORTA (bloat!)
└─────────────────────────────┘
┌─────────────────────────────┐
│ id=1, email='new@email.com' │
│ xmin=200, xmax=NULL         │ ← VIVA
└─────────────────────────────┘
```

Por que isso é necessário? Para que transações concorrentes vejam dados consistentes. Mas há um preço: **bloat**.

O Custo do MVCC: Verificação de Visibilidade
Para cada linha que o PostgreSQL escaneia (mesmo em um simples SELECT), ele precisa verificar:

```python
if (xmin < minha_transacao AND 
    (xmax == NULL OR xmax > minha_transacao)):
    # Linha é visível
    incluir_no_resultado()
else:
    # Linha não é visível (pular)
    continuar_para_proxima()
```

## Identificando Bloat

### Causas Principais

| Causa | Descrição |
|-------|-----------|
| Updates/Deletes frequentes | Criam tuplas mortas devido ao MVCC |
| Transações longas | Impedem autovacuum de limpar (tuplas ainda podem ser necessárias) |
| Fill factor alto | Sem espaço para expandir linhas na mesma página |
| Autovacuum insuficiente | Thresholds padrão não acompanham a carga |
| Batch operations | Bulk inserts/updates/deletes |

### Impactos do Bloat

* 🐌 Performance degradada: Queries escaneiam dados mortos
* 📊 Planos ruins: Query planner usa estatísticas imprecisas
* 💾 Desperdício de disco: Versões antigas ocupam espaço
* 🔥 Throughput reduzido: Processamento mais lento


### pg_stat_user_tables
```sql
SELECT 
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
    last_autovacuum,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
WHERE n_dead_tup > 0
ORDER BY n_dead_tup DESC
LIMIT 10;
```

Interpretação:
* dead_pct > 20%: Bloat significativo
* last_autovacuum muito antigo: Autovacuum não está acompanhando

### pgstattuple Extension
```sql
CREATE EXTENSION pgstattuple;

-- Análise precisa (scan completo)
SELECT * FROM pgstattuple('minha_tabela');

-- Análise rápida (usa visibility map)
SELECT * FROM pgstattuple_approx('minha_tabela');
```

**Output:**
```
table_len    | 52428800    -- Tamanho total
tuple_count  | 100000      -- Tuplas vivas
dead_tuple_count | 25000   -- Tuplas mortas
dead_tuple_percent | 20.0  -- % de bloat
```

## VACUUM: Tipos e Diferenças
O PostgreSQL oferece três tipos principais de vacuum, cada um com características distintas:

| Aspecto | VACUUM | AUTOVACUUM | VACUUM FULL |
|---------|--------|------------|-------------|
| Iniciação | Manual | Automática | Manual |
| Online? | ✅ Sim | ✅ Sim | ❌ Não |
| Lock | Share Update Exclusive | Share Update Exclusive | Access Exclusive |
| Retorna espaço ao SO | ❌ Não | ❌ Não | ✅ Sim |
| Atualiza estatísticas | Com ANALYZE | ✅ Sim | ❌ Não |
| DML permitido | ✅ Sim | ✅ Sim | ❌ Não |

### VACUUM (Manual)
O que faz:
* Remove tuplas mortas
* Marca espaço como reutilizável (não retorna ao SO)
* Atualiza visibility map e free space map
* Com ANALYZE: atualiza estatísticas

Quando usar:
* Manutenção de rotina
* Após bulk operations
* Quando autovacuum não acompanha a carga

### AUTOVACUUM
Processo daemon que roda automaticamente em background. Configurável globalmente ou por tabela.

### VACUUM FULL
O que faz:
* Reescreve completamente a tabela
* Move todas as linhas vivas para novas páginas
* Descarta páginas mortas
* Retorna espaço ao SO
* Reconstrói índices

⚠️ PROBLEMAS CRÍTICOS:
* **Requer lock ACCESS EXCLUSIVE (tabela OFFLINE)**
* Nenhuma operação permitida durante execução
* Precisa de espaço temporário (2x tamanho da tabela)
* Muito lento

Quando usar: Apenas como último recurso em casos extremos de bloat.

## Autovacuum: Manutenção Automatizada
Parâmetros Principais
* Scheduling
  * autovacuum_naptime: Frequência de verificação
  * autovacuum_max_workers: workers paralelos
* Thresholds
    * autovacuum_vacuum_threshold
    * autovacuum_vacuum_scale_factor
    * autovacuum_vacuum_insert_threshold
    * autovacuum_vacuum_insert_scale_factor
* Analyze
    * autovacuum_analyze_threshold
    * autovacuum_analyze_scale_factor
* I/O Control
  * autovacuum_vacuum_cost_delay -- Delay entre operações (controla pressão de I/O)
  * autovacuum_vacuum_cost_limit -- Limite de custo antes de aplicar delay
* Transation ID protection
  * autovacuum_freeze_max_age -- Idade máxima antes de forçar freeze
  * autovacuum_multixact_freeze_max_age
* Configuração por Tabela
    ```sql
    -- Tabela com alta taxa de updates
    ALTER TABLE usuarios SET (
        autovacuum_vacuum_scale_factor = 0.05,    -- Mais agressivo (5%)
        autovacuum_vacuum_threshold = 1000,
        autovacuum_analyze_scale_factor = 0.02
    );

    -- Tabela insert-only
    ALTER TABLE logs SET (
        autovacuum_vacuum_insert_scale_factor = 0.1,
        autovacuum_vacuum_insert_threshold = 10000
    );
    ```

### Como Funciona (Internamente)
```markdown
1. AUTOVACUUM LAUNCHER (daemon principal)
   └─ Verifica periodicamente (autovacuum_naptime)
   └─ Identifica tabelas que precisam vacuum/analyze

2. SPAWNA WORKERS (até autovacuum_max_workers)
   └─ Cada worker processa uma tabela
   └─ Trabalham concorrentemente

3. WORKER executa:
   ├─ VACUUM: Remove dead tuples
   ├─ ANALYZE: Atualiza estatísticas
   └─ FREEZE: Congela tuplas antigas
```

### Tuning por Carga de Trabalho
* **Alta velocidade transacional** (muitos UPDATEs/DELETEs): Reduza `scale_factor` para 0.01-0.05 (1-5%) e aumente `autovacuum_max_workers` se houver recursos disponíveis. Isso força vacuum mais frequente antes que o bloat se acumule.

* **Média velocidade transacional**: Mantenha configurações padrão e ajuste **apenas se** o monitoramento mostrar `last_autovacuum` muito antigo ou `dead_pct > 20%`.
  
* **Insert-only** (logs, eventos): Configure `autovacuum_vacuum_insert_threshold` e execute `VACUUM FREEZE` periodicamente para atualizar o visibility map e habilitar index-only scans.
  
* **Tabelas com TOAST**: Adicione configurações específicas com prefixo `toast.` para garantir que dados grandes também sejam mantidos adequadamente.

### Adaptive Autovacuum (AWS RDS/Aurora)
 Recurso exclusivo da AWS que ajusta **dinamicamente** parâmetros de autovacuum para prevenir transaction ID wraparound.

#### Como Funciona
```markdown
1. MONITORA CloudWatch metric: "Maximum Used Transaction IDs"

2. DISPARA quando aproxima de:
   - autovacuum_freeze_max_age OU
   - 500 milhões de XIDs

3. AJUSTA automaticamente:
   - Aumenta agressividade do autovacuum
   - Reduz thresholds temporariamente
   - Aloca mais recursos

4. GERA EVENTOS para monitoramento
```

## Transaction ID Wraparound
### O Problema

PostgreSQL usa **32 bits** para Transaction IDs (XIDs):
```
2³² = 4.294.967.296 valores possíveis
Mas apenas ~2 bilhões são utilizáveis (2³¹)
```

**Por quê limitar a 2 bilhões?**
- Metade é reservada para o "passado"
- Metade para o "futuro"
- Permite comparações circulares

### Como Funciona

Cada transação recebe um XID sequencial. Quando atinge o limite, **"dá a volta"** (wraparound):
```
... → 2.147.483.647 → 0 → 1 → 2 → ...
                      ↑ wraparound!
```

**Problema:** PostgreSQL não consegue mais determinar qual XID é mais antigo!
```markdown 
Exemplo:
Tupla criada em XID 100 (primeiro ciclo)
Transação atual: XID 100 (segundo ciclo, pós-wraparound)

São o MESMO número, mas são DIFERENTES!
Como saber qual é qual? 🤔
```

**Consequência:** Dados do passado podem ficar **invisíveis** = **perda de dados**!

### Solução: VACUUM FREEZE

O que é?
Durante o processo VACUUM FREEZE, tuplas antigas são marcadas como "frozen" (congeladas).
Benefícios

Linha congelada = permanente: visível para todas as transações futuras
PostgreSQL não precisa mais rastrear a idade do XID dessa linha
Previne wraparound: ajuda a evitar problemas relacionados ao esgotamento de XIDs

Por que é necessário?
Um sistema moderno com alto throughput transacional pode esgotar o limite de 2³⁰ XIDs rapidamente.

#### O que é Freeze?
Quando uma tupla é **frozen**:
```
ANTES:
xmin = 1.234.567  (precisa comparar com XID atual)

DEPOIS:
xmin = FrozenTransactionId (2)  (SEMPRE visível, sem comparação!)
```

#### Como Funciona
**Processo:**
```markdown
VACUUM FREEZE tabela;

1. Para cada tupla:
   ├─ Se age(xmin) > vacuum_freeze_min_age
   ├─ Marcar xmin = FrozenTransactionId
   └─ Tupla agora é "eterna"

2. Atualizar metadados:
   ├─ pg_class.relfrozenxid (por tabela)
   └─ pg_database.datfrozenxid (por database)

3. Liberar XIDs antigos para reciclagem
```

## VACUUM FULL e Alternativas

**Problemas críticos:**
- **ACCESS EXCLUSIVE Lock**: Tabela completamente offline, nenhuma operação permitida
- **Extremamente lento**: Reescreve tabela inteira + reconstrói todos os índices
- **Espaço temporário**: Precisa de ~2x o tamanho da tabela em disco
- **Sem estatísticas**: Não atualiza estatísticas (precisa executar ANALYZE depois)

### Alternativas Superiores

**pg_repack** é a melhor alternativa para reorganização planejada. Funciona com locks mínimos (apenas segundos no início/fim), mantendo a tabela acessível 95% do tempo. Ideal para manutenção trimestral/anual, bloat > 30%, ou após bulk deletes. Requer instalação da extensão no banco e cliente na mesma versão.

**pg_squeeze** oferece manutenção automatizada contínua rodando em background. Configure via agendamento cron-style e esqueça. Perfeito para ambientes high-write onde bloat se acumula rapidamente. Trabalha incrementalmente com impacto mínimo em recursos.

**CREATE TABLE AS SELECT (CTAS)** dá controle total do processo. Você cria uma nova tabela compactada, reconstrói índices, e faz swap atômico em transação. Downtime apenas no momento do swap (< 1 segundo). Útil quando precisa fazer transformações nos dados simultaneamente. Desvantagem: precisa recriar manualmente constraints, triggers e foreign keys.

**Particionamento** é a solução definitiva para tabelas gigantes (> 100GB). Cada partição tem sua própria tabela e índices, tornando VACUUM muito mais rápido. DROP TABLE de partições antigas é instantâneo. Requer planejamento no design inicial, mas vale muito a pena para dados com ciclo de vida definido (logs, eventos, vendas por período).


### Estratégia Combinada
```markdown
1. AUTOVACUUM (sempre ativo)
   └─ Limpeza básica contínua

2. PG_SQUEEZE (manutenção de rotina)
   └─ Background worker contínuo
   └─ Tabelas com alta taxa de update

3. PG_REPACK (manutenção planejada)
   └─ Trimestral/anual
   └─ Tabelas críticas ou muito grandes
   └─ Após bulk operations

4. PARTICIONAMENTO (design)
   └─ Tabelas gigantes (> 100GB)
   └─ Dados com ciclo de vida (logs, eventos)

5. VACUUM FULL (nunca!)
   └─ Apenas emergências extremas
   └─ Quando TODAS as outras opções falharam
```

## TOAST Tables: Dados Grandes, Problemas Específicos

### O Que É TOAST?

TOAST (The Oversized-Attribute Storage Technique) move automaticamente dados > 2KB para armazenamento separado. Afeta tipos como TEXT, JSON/JSONB, XML, BYTEA e arrays grandes.

Quando você insere dados grandes, o PostgreSQL armazena apenas um ponteiro pequeno (~18 bytes) na tabela principal, e divide o conteúdo real em chunks de ~2KB numa tabela TOAST separada (`pg_toast.pg_toast_<oid>`).

**Estratégias disponíveis:**
- **PLAIN**: Nunca comprime nem faz TOAST (tipos simples)
- **EXTENDED**: Comprime primeiro, depois faz TOAST se ainda grande (padrão para TEXT)
- **EXTERNAL**: Faz TOAST sem comprimir (útil para dados já comprimidos como JSON)
- **MAIN**: Comprime mas evita TOAST quando possível


```sql
CREATE TABLE documentos (
    id INT,
    titulo TEXT,
    conteudo TEXT  -- Pode ser TOASTed
);

INSERT INTO documentos VALUES (
    1, 
    'Manual PostgreSQL',
    'Conteúdo muito longo... (5KB)'
);
```


```markdown
-- Tabela Principal
┌─────┬──────────────────┬─────────────────┐
│ id  │ titulo           │ conteudo        │
├─────┼──────────────────┼─────────────────┤
│ 1   │ Manual Postgres  │ [TOAST POINTER] │ ← ~18 bytes
└─────┴──────────────────┴─────────────────┘
                              │
                              ▼

-- Tabela TOAST (`pg_toast.pg_toast_12345`)
┌───────────┬───────────┬──────────────┐
│ chunk_id  │ chunk_seq │ chunk_data   │
├───────────┼───────────┼──────────────┤
│ 5001      │ 0         │ [2KB]        │
│ 5001      │ 1         │ [2KB]        │
│ 5001      │ 2         │ [1KB]        │
└───────────┴───────────┴──────────────┘
      ▲
      └── ID único para este valor
```

### O Problema: TOAST Também Sofre de Bloat

Quando você faz UPDATE em uma coluna TOASTed, o PostgreSQL cria uma **nova versão completa** na tabela TOAST. A versão antiga vira dead tuple, acumulando bloat rapidamente.

**Pior ainda:** Cada versão TOAST recebe um OID único. Tabelas com muitos UPDATEs em dados grandes podem **esgotar OIDs**, causando problemas com autovacuum e até potencial corrupção de dados.

## Gerenciamento de Índices

3 Atividades Principais
* Rebuilding - Reconstruir índices com bloat
* Duplicate Removal - Remover índices duplicados
* Unused Index Removal - Remover índices não utilizados

### Rebuilding de Índices

Índices acumulam bloat assim como tabelas. Páginas vazias ou quase vazias degradam performance e desperdiçam espaço.
Rebuild quando: bloat > 20%, índice corrompido (hardware failure, bugs), ou query planner para de usá-lo.

**Identificar bloat:**
```sql
CREATE EXTENSION amcheck;
SELECT bt_index_check('nome_indice');

-- Ou use queries de bloat (documentação AWS)
```

**REINDEX CONCURRENTLY (recomendado para produção):**
```sql
-- Ajustar memória primeiro
SET maintenance_work_mem = '2GB';
SET max_parallel_maintenance_workers = 4;

-- Rebuild
REINDEX INDEX CONCURRENTLY idx_usuarios_email;

-- Monitorar progresso
SELECT * FROM pg_stat_progress_create_index;
```

### Índices Duplicados

Múltiplos índices na mesma tabela com critérios idênticos ou muito similares. Geralmente criados por acidente (falha de comunicação, mudanças de schema sem cleanup).

**Por que remover:** Desperdiçam espaço, deixam writes mais lentos (cada índice precisa atualizar), confundem o query planner, aumentam overhead de manutenção sem benefício.

**Identificar:**
```sql
SELECT 
    indrelid::regclass AS table_name,
    array_agg(indexrelid::regclass) AS duplicate_indexes,
    pg_size_pretty(SUM(pg_relation_size(indexrelid))) AS wasted_size
FROM (
    SELECT 
        indrelid,
        indexrelid,
        array_to_string(indkey, ' ') AS columns
    FROM pg_index
    WHERE indisvalid
) sub
GROUP BY indrelid, columns
HAVING COUNT(*) > 1
ORDER BY SUM(pg_relation_size(indexrelid)) DESC;
```

**Output exemplo:**
```
table_name  | duplicate_indexes                    | wasted_size
------------+--------------------------------------+-------------
usuarios    | {idx_email, idx_email_dup}           | 450 MB
pedidos     | {idx_status, idx_status_new}         | 1.2 GB
```

**Processo seguro de remoção:**
```sql
-- 1. Renomear (não dropar!)
ALTER INDEX idx_logs_tipo RENAME TO idx_logs_tipo_UNUSED_20240110;

-- 2. Documentar
COMMENT ON INDEX idx_logs_tipo_UNUSED_20240110 IS 
    'Renamed 2024-01-10. Drop on 2024-04-10 if no issues.';

-- 3. Monitorar por 90 dias

-- 4. Se OK, dropar
DROP INDEX CONCURRENTLY idx_logs_tipo_UNUSED_20240110;
```

### Índices Não Utilizados

Índices que existem mas não são usados por nenhuma query. Surgem de mudanças em padrões de queries, updates de aplicação, ou over-indexing no design inicial.

**Por que remover:** Consomem espaço, deixam writes mais lentos, podem confundir o planner, aumentam overhead de manutenção.

**Identificar:**
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(relid)) AS table_size
FROM pg_stat_user_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  AND idx_scan = 0
  AND indexrelname NOT LIKE 'pg_toast%'
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Output exemplo:**
```
tablename  | indexname          | size   | scans | table_size
-----------+--------------------+--------+-------+------------
logs       | idx_logs_tipo      | 2.1 GB | 0     | 15 GB
eventos    | idx_eventos_user   | 450 MB | 0     | 3.2 GB
```


## Conclusão

**O problema:** PostgreSQL usa MVCC para concorrência, criando novas versões de dados ao invés de modificar in-place. UPDATE/DELETE deixam tuplas mortas (bloat) que degradam performance até você limpá-las.

**A solução:** VACUUM remove bloat e mantém o banco saudável. Três tipos principais:
- **VACUUM** (manual): Remove dead tuples, marca espaço reutilizável, tabela continua online
- **AUTOVACUUM** (automático): Deve estar **sempre habilitado**, monitora e limpa continuamente
- **VACUUM FULL**: ❌ **Evite!** Trava tabela completamente. Use `pg_repack` ou `pg_squeeze` ao invés

**Transaction ID wraparound:** PostgreSQL tem ~2 bilhões de XIDs disponíveis. Quando esgota, pode fazer **shutdown forçado**. `VACUUM FREEZE` marca tuplas antigas como "eternas", liberando XIDs para reciclagem. Monitore `age(datfrozenxid)` religiosamente.

**TOAST tables:** Dados > 2KB vão para armazenamento separado. Sofrem bloat como tabelas normais mas autovacuum roda menos frequentemente. Configure thresholds mais agressivos em tabelas com dados grandes e alta taxa de updates.

**Índices:** Precisam de rebuild periódico (bloat > 20%), remoção de duplicados (desperdício), e remoção de não utilizados (overhead). Use `REINDEX CONCURRENTLY` em produção. Menos índices = vacuum mais rápido.
