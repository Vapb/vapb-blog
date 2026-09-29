---
title: "Database Migration Service: como o GCP migra bancos para o Cloud SQL"
author: "vapb"
description: "Os conceitos do Database Migration Service (DMS) do Google Cloud: connection profiles, migration jobs, migração one-time vs. contínua, dump e CDC, métodos de conectividade, validação e promoção do destino."
date: 2026-09-28
tags: ["gcp", "mysql", "cloud-sql", "database"]
toc: true
draft: false
---

## Introdução

Fiz uma sequência de labs do Google Cloud Skills Boost (skill badge **Migrate MySQL Data to Cloud SQL using Database Migration Service**) migrando MySQL de uma VM e de um Amazon RDS para o **Cloud SQL**. Em vez de documentar os labs, este post organiza **o que o Database Migration Service faz e como uma migração é montada**, do início ao fim.

O fluxo usa MySQL como exemplo. No final tem uma comparação com o PostgreSQL, que ganhou [um post próprio]({{< relref "gcp-datamigration-postgresql.md" >}}).

Em uma frase, o fluxo é:

> **Connection profile** (onde está a origem) → **Migration job** (o que migrar, para onde e como) → **Dump** (cópia inicial) → **CDC** (só no contínuo) → **Validação** → **Promote** (o destino vira o banco oficial).

Cada seção abaixo é uma etapa desse fluxo.

## O que é o DMS

O **Database Migration Service** é o serviço gerenciado do Google Cloud para mover bancos relacionais para dentro do GCP.

- **Serverless:** você não provisiona nem gerencia máquina de replicação. Configura o job e o serviço cuida da execução.
- **Origens:** MySQL, PostgreSQL, SQL Server e Oracle, onde quer que estejam: on-premises, em VMs, no Amazon RDS/Aurora, no Azure etc.
- **Destinos:** Cloud SQL (MySQL, PostgreSQL, SQL Server) e AlloyDB for PostgreSQL.
- **Custo:** migrações **homogêneas** para Cloud SQL e AlloyDB não têm cobrança adicional do DMS. Você paga a instância de destino e o tráfego de rede.

### Homogênea vs. heterogênea

| | **Homogênea** | **Heterogênea** |
|---|---|---|
| **Exemplo** | MySQL → Cloud SQL for MySQL | Oracle → Cloud SQL for PostgreSQL |
| **Schema** | Vai igual, mesmo engine | Precisa ser **convertido** (tipos, procedures, sintaxe) |
| **Como o DMS faz** | Usa os mecanismos **nativos** de replicação do engine | Usa um **conversion workspace** para traduzir o schema antes de mover os dados |
| **Complexidade** | Baixa | Alta: código de aplicação e procedures costumam precisar de ajuste |

Este post fala só de migração **homogênea de MySQL**, que é o caso que eu pratiquei.

### O que "usar replicação nativa" significa

No MySQL → Cloud SQL, o DMS não inventa um protocolo próprio. Ele faz basicamente o que um DBA faria na mão para montar uma réplica:

1. tira um **dump** dos databases da origem e carrega no destino;
2. configura o destino como **réplica** da origem, lendo o **binary log (binlog)** a partir do ponto exato em que o dump foi tirado.

A instância Cloud SQL passa a ser uma réplica de um servidor externo. O valor do DMS está em **orquestrar** isso: validar pré-requisitos, configurar rede, acompanhar o progresso e fazer a promoção no final.

> **Paralelo com a AWS:** o AWS DMS resolve o mesmo problema, mas lá você gerencia uma *replication instance* e o serviço aplica as mudanças como SQL no destino (o que tem efeitos colaterais, como contei [neste incidente com autovacuum]({{< relref "autovacuum-dms-postgresql-incidente.md" >}})). No GCP, para migração homogênea, o destino é uma réplica nativa do engine.

## Etapa 1: Connection profile

O **connection profile** guarda **como chegar na origem**. É a primeira coisa que se cria, direto no menu do DMS ou dentro do wizard do job.

| Campo | O que é |
|---|---|
| **Engine** | MySQL, PostgreSQL, Amazon RDS for MySQL, Cloud SQL etc. |
| **Host / IP e porta** | Endereço da origem. Pode ser IP público ou interno, depende da conectividade que o job vai usar. |
| **Usuário e senha** | Um usuário da origem com permissão de leitura e replicação. |
| **Região** | Onde o profile fica. Tem que ser a mesma região do job. |
| **Criptografia** | `None`, SSL só do servidor ou SSL mútuo (servidor + cliente). |

Pontos importantes:

- **É reutilizável.** Um mesmo profile pode servir vários migration jobs. No challenge lab, um único profile alimentou dois jobs diferentes: um one-time e um contínuo.
- **O profile não define a rede.** Ele diz *onde* está a origem. *Como* o tráfego chega lá (allowlist, peering etc.) é escolhido depois, em cada job.
- **Hostname tem limite.** O MySQL aceita hostnames de até **60 caracteres**. Endpoints do Amazon RDS costumam ser maiores, então no lab foi preciso resolver o DNS (`dig`) e usar o **IP** no profile.
- **O usuário precisa de privilégios**, não só de login. Para o dump ele precisa ler tudo (`SELECT`, `SHOW VIEW`, `TRIGGER`, `EXECUTE` etc.). Para o contínuo, também de replicação (`REPLICATION SLAVE`, `REPLICATION CLIENT`).
- **SSL:** com `None` o dado trafega em texto puro. Serve para lab; em produção, principalmente quando o tráfego passa pela internet, use SSL.

## Etapa 2: Migration job

O **migration job** é a migração em si. O wizard tem uma sequência fixa de passos, e cada um corresponde a uma decisão:

| Passo | Decisão |
|---|---|
| **Get started** | Nome, engine de origem, região de destino e **tipo do job** (one-time ou contínuo) |
| **Define a source** | Qual **connection profile** usar |
| **Define a destination** | Criar uma **instância nova** ou usar uma **existente** |
| **Define connectivity** | Como o destino alcança a origem |
| **Configure databases** | Migrar **todos** os databases ou só alguns |
| **Test and create** | Rodar o **Test job** e então criar e iniciar |

Um job pode ser salvo como **draft** no meio do caminho. Isso é útil quando algo precisa ser feito fora do GCP antes de continuar, como liberar IPs no firewall da origem.

### Destino: instância nova vs. existente

- **Nova:** o wizard cria a instância Cloud SQL com a versão, tier e rede que você escolher.
- **Existente:** você aponta uma instância já criada. O DMS pede para **digitar o nome da instância para confirmar**, porque ela vai ser **sobrescrita** e rebaixada a réplica. Nada que estiver nela sobrevive.

Esse passo demora: ao escolher uma instância existente, o DMS reconfigura a instância para receber replicação, e isso pode levar vários minutos com o console aparentemente parado.

### Test job

Antes de criar, o **Test job** verifica de ponta a ponta:

- se o destino consegue **abrir conexão** com a origem;
- se as **credenciais** funcionam;
- se a origem atende os **pré-requisitos** (versão, binlog, privilégios).

É o melhor lugar para descobrir problemas de firewall e permissão, antes de qualquer dado ser movido.

## Etapa 3: One-time vs. contínuo

É a decisão mais importante do job, e muda tudo que vem depois.

| | **One-time** | **Contínuo** |
|---|---|---|
| **O que faz** | Só o **dump**: uma foto da origem naquele momento | **Dump + CDC**: a foto inicial e depois todas as mudanças |
| **Fim do job** | Termina sozinho (**Completed**) | Fica em **Running** até você **promover** |
| **Destino durante a cópia** | Só leitura | Só leitura |
| **Destino depois da cópia** | **Primário**, promovido automaticamente | **Read replica** da origem até o promote |
| **Mudanças feitas na origem durante a cópia** | **Perdidas** | Replicadas |
| **Downtime da aplicação** | Toda a duração do dump | Só a janela de cutover |
| **Pré-requisitos na origem** | Leitura dos dados | Leitura + **binlog** configurado + privilégios de replicação |
| **Quando usar** | Bancos pequenos, dev/teste, quando dá pra parar a aplicação | Produção, bancos grandes, downtime curto |

### Fase de dump (full load)

- Os dois tipos de job começam aqui.
- O DMS faz um **dump lógico** dos databases selecionados na origem e carrega no destino.
- O tempo depende do tamanho do banco e da banda entre origem e destino.
- No one-time, quando o dump termina, o job acaba.

### Fase de CDC (change data capture)

Só no contínuo. Terminado o dump, o destino passa a **ler o binlog da origem** e aplicar cada `INSERT`, `UPDATE` e `DELETE` que aconteceu depois do ponto do dump.

Para isso funcionar, a origem precisa:

- ter o **binary logging habilitado**, com `binlog_format = ROW`;
- ter um `server_id` configurado (como qualquer servidor que participa de replicação);
- **reter o binlog tempo suficiente.** Se o dump demorar mais que a retenção, os logs que o destino precisa já terão sido apagados e o CDC não consegue continuar.

A métrica para acompanhar aqui é o **replication delay**: o quanto o destino está atrás da origem. Ela é que diz se já dá para fazer o cutover.

### Ciclo de vida do job

`Not started` → `Starting` → `Running` → `Completed`

- **One-time:** `Running` durante o dump. Quando acaba, o job vai para `Completed` e o destino é **promovido automaticamente**: vira primário e fica independente da origem.
- **Contínuo:** `Running` na fase de dump e depois em CDC, **indefinidamente**, com o destino como **read replica**. Só vai para `Completed` depois do promote manual.
- Um job também pode ser **parado**, **retomado**, **reiniciado** (recomeça do dump) ou **apagado**.

## Etapa 4: Conectividade

O tráfego vai **do destino para a origem**: é o Cloud SQL que abre a conexão para fazer o dump e ler o binlog. Por isso a pergunta é sempre "como o Cloud SQL chega na origem?".

| Método | Como funciona | Quando usar |
|---|---|---|
| **IP allowlist** | O Cloud SQL conecta no **IP público** da origem. A origem precisa liberar os **IPs de saída** do Cloud SQL (o wizard mostra quais são). | Origem com IP público, como outra nuvem. Mais simples, mas o tráfego passa pela internet. |
| **Reverse SSH tunnel** | Uma VM bastion no GCP abre um túnel SSH até a origem, e o tráfego passa por ele. | Origem sem IP público e sem VPN/Interconnect. |
| **VPC peering** | O tráfego usa **IP interno** entre a VPC do Cloud SQL e a VPC onde a origem está. | Origem já no GCP, ou alcançável via Cloud VPN / Interconnect. |
| **Private Service Connect interfaces** | Conectividade privada via PSC, sem peering. | Alternativa privada mais recente ao peering. |

### IP allowlist na prática

É uma liberação de firewall **na origem**. No lab com Amazon RDS, significou adicionar cada IP de saída do Cloud SQL no **Security Group** do RDS, na porta 3306, como `/32`:

```bash
aws ec2 authorize-security-group-ingress \
    --group-id <SECURITY_GROUP_DO_RDS> \
    --protocol tcp --port 3306 \
    --cidr <IP_DE_SAIDA_DO_CLOUD_SQL>/32
```

O job fica em **draft** enquanto isso é feito, e só depois o Test job passa.

### VPC peering na prática

O Cloud SQL não roda na sua VPC. Ele fica numa **VPC gerenciada pelo Google**, e o acesso privado é feito com um peering entre essa VPC e a sua (o que o GCP chama de *private services access*). Por isso:

- a **Service Networking API** precisa estar habilitada, porque é ela que cria esse peering;
- o connection profile deve apontar para o **IP interno** da origem;
- a origem nunca precisa ser exposta na internet. Esse foi o objetivo do job contínuo no challenge lab: "remover a dependência do IP externo".

## Etapa 5: Validação

O DMS diz que o job está `Running` ou `Completed`, mas isso não prova que o dado está certo. A validação é sua:

- **Estrutura:** os databases esperados existem no destino?
- **Volume:** a contagem de linhas bate com a origem?

```sql
USE customers_data;
SELECT COUNT(*) FROM customers;  -- mesmo número na origem e no destino
```

- **CDC (no contínuo):** a melhor prova é **mudar a origem e observar o destino**. Nos labs, um `INSERT` de duas linhas e um `UPDATE` feitos na origem apareceram no destino segundos depois:

```sql
-- na origem
UPDATE customers SET gender = 'FEMALE' WHERE addressKey = 934;
-- no destino, pouco depois, a mesma linha já aparece alterada
```

Durante o contínuo, o destino é uma **read replica**: aceita consultas, o que permite validar sem parar nada, mas **não aceita escrita**.

## Etapa 6: Promote e cutover

**Promover** é o passo que encerra uma migração contínua:

- a replicação com a origem é **cortada**;
- o destino deixa de ser read replica e vira uma instância **primária e standalone**, com leitura e escrita;
- o job vai para **Completed**;
- **não tem volta.** Depois de promovido, o destino não recebe mais nada da origem.

Por isso a promoção é o centro do **cutover**, que numa migração real segue esta ordem:

1. **Validar** o destino (volume, consistência, queries críticas da aplicação).
2. **Parar as escritas** na origem (manutenção ou read-only).
3. **Esperar o replication delay zerar**, para garantir que o destino tem tudo.
4. **Promover.**
5. **Apontar a aplicação** para o Cloud SQL (connection string, DNS, secrets).
6. Manter a origem por um tempo como **rollback**.

O downtime real é só do passo 2 ao 5. Esse é o ganho do contínuo em relação ao one-time, em que a aplicação precisa ficar parada durante todo o dump.

## E no PostgreSQL?

O fluxo no DMS é **o mesmo**: connection profile, migration job, conectividade, Test job, dump, CDC e promote. O que muda é **o mecanismo de replicação por baixo**:

| | **MySQL** | **PostgreSQL** |
|---|---|---|
| **Replicação usada** | Nativa: o Cloud SQL vira réplica lendo o **binlog** | **Lógica**, via extensão **pglogical** |
| **Por quê** | O MySQL permite réplica de servidor externo | A replicação física do Postgres copia blocos de disco, e um Cloud SQL gerenciado não pode ser réplica física de um servidor externo |
| **Preparar a origem** | Binlog em `ROW` e usuário com privilégios de replicação | Instalar o pglogical, `wal_level = logical`, restart, extensão em cada database, usuário com `REPLICATION` |
| **One-time** | Só o dump, sem requisitos de replicação | **Também exige o pglogical** |
| **Pegadinha principal** | Retenção do binlog | Tabelas **sem primary key** não replicam `UPDATE`/`DELETE` |

Em resumo: no MySQL o DMS aproveita um recurso que o banco já tem; no PostgreSQL, preparar a origem é boa parte do trabalho. Os detalhes estão no post [Database Migration Service com PostgreSQL]({{< relref "gcp-datamigration-postgresql.md" >}}).

## Resumo

- O **DMS** orquestra migrações para Cloud SQL/AlloyDB sem infraestrutura de replicação para gerenciar. Na migração homogênea, ele usa a **replicação nativa** do engine.
- **Connection profile** = onde está a origem e como autenticar. Reutilizável e independente da rede.
- **Migration job** = tipo, origem, destino, conectividade e databases, validados pelo **Test job**.
- **One-time** = só dump, termina sozinho. **Contínuo** = dump + **CDC via binlog**, e o destino fica como read replica.
- **Conectividade** é sempre do destino para a origem: **IP allowlist** (IP público + firewall), **VPC peering** (IP interno + Service Networking), reverse SSH ou PSC.
- **Valide** mudando a origem e conferindo o destino.
- **Promote** corta a replicação, torna o destino primário e é irreversível: é o momento do cutover.
- **No PostgreSQL**, o fluxo é o mesmo, mas o DMS usa replicação lógica via **pglogical**, e preparar a origem dá mais trabalho.

## Referências

- [Database Migration Service documentation](https://cloud.google.com/database-migration/docs)
- [Configure connectivity (MySQL)](https://cloud.google.com/database-migration/docs/mysql/configure-connectivity)
- [Types of migration](https://cloud.google.com/database-migration/docs/mysql/migration-types)
- [Cloud SQL for MySQL documentation](https://cloud.google.com/sql/docs/mysql)
- [Database Migration Service com PostgreSQL]({{< relref "gcp-datamigration-postgresql.md" >}}), a continuação deste post
- [Parte 1 da série de Data Engineering no Google Cloud]({{< relref "gcp-data-engineering-parte-1.md" >}}), onde o DMS aparece no contexto de replicação e migração
