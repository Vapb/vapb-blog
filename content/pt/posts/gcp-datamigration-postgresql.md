---
title: "Database Migration Service com PostgreSQL: pglogical, preparação da origem e pós-migração"
author: "vapb"
description: "Como o Database Migration Service (DMS) do Google Cloud migra PostgreSQL para o Cloud SQL: por que o pglogical é obrigatório, como preparar a origem, o problema das tabelas sem primary key, limitações da replicação lógica e o que configurar no Cloud SQL depois do promote (IAM auth e PITR)."
date: 2026-09-29
tags: ["gcp", "postgresql", "cloud-sql", "database"]
toc: true
---

## Introdução

Este post é a continuação de [Database Migration Service: como o GCP migra bancos para o Cloud SQL]({{< relref "gcp-datamigration.md" >}}), que explica o DMS usando MySQL como exemplo: connection profile, migration job, one-time vs. contínuo, conectividade, validação e promote.

Aqui o foco é o **PostgreSQL**.

O fluxo no DMS é **o mesmo** do MySQL. O que muda é **o mecanismo de replicação por baixo**, e isso muda bastante o trabalho de preparar a origem.

## Por que o pglogical é obrigatório

No MySQL, o Cloud SQL vira réplica da origem lendo o **binlog**, um recurso nativo do banco. O equivalente "óbvio" no PostgreSQL seria a replicação **física** (streaming replication), mas ela copia **blocos de disco**: a réplica precisa ser uma cópia binária exata do servidor desde o início. Um Cloud SQL gerenciado não pode ser réplica física de um servidor externo.

Então o DMS usa replicação **lógica**, que trafega **linhas**, e a ferramenta que ele usa para isso é a extensão **pglogical**. Ela é usada nas duas fases:

- **carga inicial:** o pglogical copia as tabelas para o destino;
- **CDC:** o pglogical lê o WAL decodificado por um **replication slot** e aplica as mudanças no destino.

Por isso o pglogical é obrigatório **até no job one-time**. Sem a extensão na origem, o DMS não funciona, e as alternativas viram migrações com downtime (`pg_dump`/`pg_restore`) ou replicação lógica nativa (`PUBLICATION`/`SUBSCRIPTION`) montada e gerenciada na mão.

## Preparando a origem

No MySQL, basicamente basta o binlog estar ligado. No PostgreSQL, preparar a origem é **a maior parte do trabalho** da migração:

| O quê | Por quê |
|---|---|
| **Instalar o pacote do pglogical** na versão do Postgres da origem | A extensão não vem com o PostgreSQL |
| `shared_preload_libraries = 'pglogical'` | O pglogical roda processos de background e precisa ser carregado na inicialização. Exige **restart**. |
| `wal_level = logical` | Faz o WAL carregar informação suficiente para ser decodificado em linhas. Exige **restart**. |
| `max_replication_slots`, `max_wal_senders`, `max_worker_processes` | Cada database migrado consome slot, sender e workers |
| `listen_addresses` e **`pg_hba.conf`** | O Postgres precisa aceitar conexões vindas da rede do DMS, e não só do `localhost` |
| `CREATE EXTENSION pglogical` em **cada database migrado e no database `postgres`** | O pglogical guarda metadados por database |
| Um **usuário de migração** com o atributo `REPLICATION` | Replicação lógica exige esse atributo |
| **Permissões** para o usuário no schema `pglogical` e nas tabelas | Ele precisa ler os dados e os metadados do pglogical |

> No **Amazon RDS / Aurora**, os parâmetros vão no parameter group (`rds.logical_replication = 1` e `pglogical` em `shared_preload_libraries`). No **Cloud SQL** como origem, existe a flag `cloudsql.enable_pglogical`.

### Passo a passo: habilitando o pglogical

Um roteiro mínimo para um PostgreSQL **self-managed** em Debian/Ubuntu (VM ou on-prem). Os exemplos usam o Postgres 14, então troque pela sua versão (`pg_lsclusters` mostra qual é).

**1. Instalar o pacote**

```bash
sudo apt update
sudo apt install -y postgresql-14-pglogical
```

**2. Ajustar os parâmetros**

O `ALTER SYSTEM` grava as configurações no `postgresql.auto.conf`, sem precisar editar o `postgresql.conf` na mão:

```sql
-- sudo -u postgres psql
ALTER SYSTEM SET wal_level = 'logical';
ALTER SYSTEM SET shared_preload_libraries = 'pglogical';
ALTER SYSTEM SET max_replication_slots = 10;
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET max_worker_processes = 8;
ALTER SYSTEM SET listen_addresses = '*';
```

> Se o `shared_preload_libraries` já tiver outra extensão (ex.: `pg_stat_statements`), mantenha as duas: `'pg_stat_statements,pglogical'`.

**3. Liberar a conexão no `pg_hba.conf`**

Adicione uma linha permitindo o usuário de migração a partir da faixa de IP de onde o DMS vai conectar:

```text
host    all    migration_user    10.0.0.0/8    scram-sha-256
```

**4. Reiniciar e conferir**

```bash
sudo systemctl restart postgresql
sudo -u postgres psql -c "SHOW wal_level;" -c "SHOW shared_preload_libraries;"
```

Os dois precisam retornar `logical` e `pglogical`.

**5. Criar a extensão**

Em **cada database** que vai ser migrado **e** no `postgres`:

```sql
\c postgres
CREATE EXTENSION IF NOT EXISTS pglogical;

\c orders
CREATE EXTENSION IF NOT EXISTS pglogical;
```

**6. Criar o usuário de migração**

```sql
CREATE USER migration_user WITH REPLICATION PASSWORD '********';
```

Em cada database migrado (e os grants do schema `pglogical` também no `postgres`):

```sql
GRANT USAGE ON SCHEMA pglogical TO migration_user;
GRANT SELECT ON ALL TABLES IN SCHEMA pglogical TO migration_user;

GRANT USAGE ON SCHEMA public TO migration_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO migration_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO migration_user;
```

**7. Checar primary keys** com a query da próxima seção.

Com isso, a origem está pronta: é só criar o connection profile com esse usuário e rodar o **Test job**.

## Primary keys

Esse é o ponto mais traiçoeiro. Na replicação lógica, para aplicar um `UPDATE` ou `DELETE` no destino, é preciso **identificar a linha**, e quem faz isso é a primary key. Em tabelas **sem PK**, o CDC só replica `INSERT`s. `UPDATE`s e `DELETE`s ficam para trás, e o destino **diverge silenciosamente** da origem.

O pior é que o job não falha: ele roda normalmente e a divergência só aparece depois. Por isso, a query abaixo é das primeiras a rodar na origem, e toda tabela listada precisa ganhar uma PK antes de iniciar o job:

```sql
-- tabelas sem primary key
SELECT t.table_schema, t.table_name
FROM information_schema.tables t
LEFT JOIN information_schema.table_constraints c
  ON c.table_schema = t.table_schema
 AND c.table_name = t.table_name
 AND c.constraint_type = 'PRIMARY KEY'
WHERE t.table_type = 'BASE TABLE'
  AND t.table_schema NOT IN ('pg_catalog', 'information_schema', 'pglogical')
  AND c.constraint_name IS NULL;
```

## Outras limitações da replicação lógica

- **DDL não é replicado** durante o CDC. Um `ALTER TABLE` na origem no meio da migração precisa ser repetido no destino.
- **Large objects** (`pg_largeobject`) não são migrados.
- **Usuários e roles** não vão junto. É preciso recriá-los no destino.
- **O replication slot segura WAL.** Se o job travar ou for abandonado, a origem continua acumulando WAL e o disco pode encher. Depois da migração, confirme que o slot foi removido.

## No migration job

A criação do job é igual à do MySQL (tipo, conectividade, destino, promote). Duas diferenças práticas:

- **Seleção de databases:** no Postgres é comum migrar **só alguns databases** em vez de todos, já que cada database precisa da extensão e consome um replication slot.
- **Test job:** quando falha, a causa quase sempre está na preparação da origem: `wal_level`, `shared_preload_libraries`, `pg_hba.conf`, `listen_addresses` ou permissões do usuário.

## Depois da migração: o Cloud SQL como banco oficial

Depois do **promote**, o Cloud SQL deixa de ser réplica e passa a ser o banco de produção. Duas configurações fazem sentido logo nesse momento.

### IAM database authentication

Em vez de criar usuários com senha dentro do Postgres, dá para deixar **identidades do IAM** (usuários ou service accounts do Google Cloud) fazerem login no banco:

- a instância precisa da flag `cloudsql.iam_authentication` ligada;
- o principal do IAM é adicionado como usuário da instância, do tipo **Cloud IAM**;
- o login usa um **token OAuth de curta duração** no lugar de uma senha fixa.

O detalhe importante: **o IAM controla quem entra, não o que a pessoa pode fazer lá dentro.** Depois de criar o usuário IAM, ainda é preciso dar as permissões pelo SQL de sempre:

```sql
GRANT SELECT ON TABLE minha_tabela TO "usuario@dominio.com";
```

Separado disso, para um cliente conectar pelo **IP público** do Cloud SQL, o IP dele precisa estar nas **authorized networks** da instância. É a mesma ideia do IP allowlist da migração, só que no sentido contrário: agora é o Cloud SQL que libera quem pode entrar nele.

### Point-in-time recovery (PITR)

Backup diário protege contra perder o banco. O **PITR** protege contra perder **o que aconteceu desde o último backup**, como um `DELETE` sem `WHERE` às 14h37.

- Com o PITR habilitado, o Cloud SQL **arquiva o WAL** além dos backups automáticos.
- A **retenção dos logs** (em dias) define até quando no passado dá para voltar.
- A restauração **não sobrescreve a instância original**: ela cria um **clone** da instância no estado exato de um timestamp.

```bash
gcloud sql instances clone <INSTANCIA_ORIGINAL> <NOVA_INSTANCIA> \
  --point-in-time "2026-09-07T07:02:15.123Z"
```

Ou seja: o clone reflete o banco **antes** do erro, e a instância original continua intacta. Dali, dá para recuperar os dados perdidos do clone ou apontar a aplicação para ele.

## Resumo

- O fluxo do DMS é o mesmo do MySQL, mas o mecanismo é **replicação lógica via pglogical**, obrigatória **até no one-time**.
- Preparar a origem exige **instalar o pglogical**, `wal_level = logical`, `shared_preload_libraries`, **restart**, `pg_hba.conf`, a extensão em cada database (e no `postgres`) e um usuário com `REPLICATION`.
- **Toda tabela precisa de primary key**, senão `UPDATE`s e `DELETE`s não são replicados.
- **DDL, large objects e roles** não são migrados, e o **replication slot** precisa ser monitorado.
- Depois do promote: **IAM database authentication** (o IAM controla quem entra, os `GRANT`s controlam o que pode fazer) e **PITR** (a restauração cria um clone num timestamp).

## Referências

- [Database Migration Service: como o GCP migra bancos para o Cloud SQL]({{< relref "gcp-datamigration.md" >}})
- [Configure your source (PostgreSQL)](https://cloud.google.com/database-migration/docs/postgres/configure-source-database)
- [Cloud SQL IAM database authentication](https://cloud.google.com/sql/docs/postgres/iam-authentication)
- [Cloud SQL point-in-time recovery](https://cloud.google.com/sql/docs/postgres/backup-recovery/pitr)
- [pglogical (GitHub)](https://github.com/2ndQuadrant/pglogical)
