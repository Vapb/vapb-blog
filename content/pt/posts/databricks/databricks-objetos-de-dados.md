---
title: "Objetos de dados do Databricks: tabelas, views, MVs e ST"
author: "vapb"
description: "Anotações sobre os objetos de dados do Databricks no Unity Catalog: hierarquia, tabelas managed e external, volumes, views, materialized views, streaming tables, funções e modelos, e quando usar cada um."
date: 2026-10-25
tags: ["databricks", "unity-catalog", "delta-lake", "lakeflow", "data-engineering", "sql"]
toc: true
aliases: ["/posts/databricks-objetos-de-dados/"]
---

## Introdução

No Databricks, "criar uma tabela" não é uma coisa só. **Tabelas**, **views**, **materialized views** e **streaming tables** aparecem no catálogo com cara de tabela, mas se comportam de jeitos bem diferentes. A pergunta que organiza tudo é:

> **Quem calcula o resultado, e quando?**

> **Nota:** as **Lakeflow Spark Declarative Pipelines (SDP)** são o antigo **Delta Live Tables (DLT)**, e muito tutorial ainda usa o nome antigo.

## Hierarquia no Unity Catalog

Todos os objetos vivem no **Unity Catalog**, em três níveis:

```
metastore
└── catalog
    └── schema
        ├── tables (managed, external, foreign)
        ├── views, materialized views, streaming tables
        ├── volumes
        ├── functions
        └── models
```

Um objeto é endereçado como `catalogo.schema.objeto`, e é nesse nível que se aplicam permissões, linhagem e auditoria.

## Visão geral

| Objeto | Guarda dados? | Quando calcula | Para que serve |
|---|---|---|---|
| **Tabela** | Sim | Quando você escreve | Dado em qualquer camada |
| **View** | Não, só a consulta | A cada leitura | Reuso de lógica, fachada, segurança |
| **Materialized view (MV)** | Sim (resultado) | No refresh, incremental quando possível | Joins e agregações (silver/gold) |
| **Streaming table (ST)** | Sim | No refresh, só o dado novo | Ingestão (bronze) |
| **Volume** | Arquivos, não tabelas | Não se aplica | CSV, JSON, imagens, PDFs, bibliotecas |
| **Função** | Não | A cada chamada | Lógica reutilizável (UDF) |
| **Modelo** | Artefato | Não se aplica | Modelos de ML versionados |

## Tabelas

Quase tudo é uma **tabela Delta**: arquivos Parquet mais um transaction log (veja a [revisão de Delta Lake]({{< relref "/posts/databricks/databricks-lakeflowconnect.md" >}}) no post de ingestão). A diferença entre os tipos está em **quem cuida do armazenamento**:

| Tipo | Arquivos ficam | `DROP TABLE` | Quando usar |
|---|---|---|---|
| **Managed** | Em local gerenciado pelo Unity Catalog | Apaga também os arquivos (após 7 dias de recuperação, com `UNDROP`) | **Padrão e recomendado** |
| **External** | Num caminho seu (`LOCATION`) | Apaga só o registro; os arquivos ficam | Dado compartilhado com outros sistemas ou já existente |
| **Foreign** | No sistema de origem (Lakehouse Federation) | Não toca no dado | Consultar outro banco sem copiar (só leitura) |

```sql
-- managed (padrão)
CREATE TABLE main.silver.clientes (cliente_id INT, nome STRING, cidade STRING);

-- external
CREATE TABLE main.bronze.clientes_ext LOCATION 's3://meu-bucket/clientes/';
```

As **managed** custam menos para armazenar e consultar, se mantêm sozinhas (**predictive optimization**) e continuam acessíveis a clientes externos por APIs abertas. Também existem tabelas em formato **Iceberg**, gerenciadas pelo Unity Catalog.

Dois recursos de organização: **liquid clustering** (`CLUSTER BY`), que substitui particionamento e `ZORDER`, e **clone** (`DEEP`/`SHALLOW CLONE`), útil para testes e backups.

## Volumes

Tabelas guardam dado **estruturado**. Para **arquivos** (CSV, JSON, Parquet cru, imagens, PDFs, bibliotecas) existem os **volumes**: um diretório governado pelo Unity Catalog, acessado por caminho:

```
/Volumes/<catalogo>/<schema>/<volume>/<pasta>/arquivo.csv
```

- **Managed volume:** os arquivos ficam no storage gerenciado pelo Unity Catalog.
- **External volume:** aponta para um caminho seu no cloud storage.

É o lugar clássico de uma **landing zone**: os arquivos chegam num volume e o Auto Loader (ou uma streaming table) os ingere para o bronze. Volumes não são tabelas: não há schema nem SQL sobre eles, só arquivos com permissões e linhagem.

## Views

Uma **view** é uma **consulta salva** com nome. Não guarda dado: toda leitura executa a consulta de novo.

```sql
CREATE OR REPLACE VIEW main.gold.clientes_sp AS
SELECT cliente_id, nome FROM main.silver.clientes WHERE cidade = 'São Paulo';
```

| Tipo | Escopo | Para que serve |
|---|---|---|
| **View** | Permanente, no Unity Catalog | Reusar lógica e expor uma "fachada" da tabela |
| **Temporary view** | Só a sessão (ou, num pipeline, só dentro dele) | Passo intermediário que ninguém mais precisa ver |
| **Metric view** | Unity Catalog | Definir métricas de negócio num lugar só, para BI e Genie |

- **Sempre fresca, sempre recalculada:** se for pesada e muito consultada, você paga o custo toda vez. É aí que entra a MV.
- **Segurança:** dá para expor só algumas colunas ou linhas. Hoje o recomendado é **row filters** e **column masks** na própria tabela, mas views seguem muito usadas.
- **Metric views** são recentes e a sintaxe tem evoluído; confira a documentação antes de usar.

## Materialized views (MV)

Guarda o **resultado pré-calculado** de uma consulta, e o Databricks o mantém sincronizado com as origens. Consulta-se como uma tabela.

```sql
CREATE MATERIALIZED VIEW main.gold.vendas_por_cidade
SCHEDULE EVERY 1 HOUR
AS
SELECT c.cidade, SUM(v.valor) AS faturamento
FROM main.silver.vendas v
JOIN main.silver.clientes c USING (cliente_id)
GROUP BY c.cidade;
```

- **Declarativa:** você descreve o **resultado**; não há `MERGE` para escrever.
- **Refresh:** no `SCHEDULE` ou sob demanda (`REFRESH MATERIALIZED VIEW nome`).
- **Incremental quando possível:** processa só o que mudou nas origens; senão, recalcula tudo, e o resultado continua **correto**. O que aconteceu fica no **event log**.
- **Sempre correta:** se uma dimensão muda, o join é **recalculado**.
- **Limites:** latência de segundos a minutos; nem toda consulta é incremental; mudança em **UDF** pode não ser detectada e exige **full refresh**; só o pipeline dono altera a MV.

## Streaming tables (ST)

Uma tabela Delta com **processamento incremental**: cada refresh lê só o **dado novo** da origem e o acrescenta, e cada linha é processada **uma única vez**. É o objeto natural da **ingestão**, sobre o Auto Loader ou mensageria (Kafka, Event Hubs, Pub/Sub).

```sql
CREATE OR REFRESH STREAMING TABLE main.bronze.pedidos
SCHEDULE EVERY 1 HOUR
AS
SELECT * FROM STREAM read_files('/Volumes/main/landing/pedidos/', format => 'json');
```

- **Origem append-only.** A ST só sabe **acrescentar** linhas. Se a origem também **atualiza ou apaga** registros, você recebe um **feed de mudanças (CDC, Change Data Capture)**: cada linha vem com a operação (insert, update, delete) e uma coluna de sequência. Quem aplica esse feed numa tabela é o `AUTO CDC`, que atualiza e apaga as linhas certas. Os detalhes estão no post de [SCD]({{< relref "/posts/dados/slowly-changing-dimensions.md" >}}).
- **Não reprocessa o passado:** mudar a consulta afeta só as linhas novas. Reaplicar em tudo exige **full refresh**.
- **Joins não são recalculados:** se uma dimensão muda, as linhas já processadas ficam como estavam.
- **Estado limitado:** agregações e joins entre streams precisam de **watermark**.
- **Full refresh com cuidado:** se a origem não guarda histórico (ex.: tópico Kafka com retenção curta), ele pode apagar dado que a origem já perdeu.

## Funções e modelos

Dois objetos menores que completam o schema:

- **Funções:** UDFs em SQL ou Python registradas no Unity Catalog, reutilizáveis e governadas como qualquer outro objeto.
- **Modelos:** modelos de ML versionados (via MLflow), com permissões e linhagem.

## ST ou MV?

A diferença de fundo é **o que cada uma garante**:

| | Streaming table | Materialized view |
|---|---|---|
| **Processa** | Cada linha nova, **uma vez** | O **resultado**, mantido correto |
| **Origem** | Append-only (arquivos, mensageria) | Qualquer consulta suportada |
| **Se a dimensão muda** | Linhas antigas **não** mudam | O join é **recalculado** |
| **Boa para** | Ingestão, limpeza linha a linha | Joins e agregações |

Na arquitetura medalhão: **bronze com ST**, **silver com ST** (ou `AUTO CDC`, se o dado muda), **gold com MV**.

## Como escolher

- **Arquivos brutos (landing):** volume.
- **Dado que só chega:** streaming table.
- **Agregação ou join sempre correto:** materialized view.
- **Lógica reusada ou controle de acesso, sem armazenar:** view.
- **Tabela de uso geral:** managed, ou external se o storage precisar ficar sob seu controle.

## Resumo

- Tudo vive no Unity Catalog como `catalogo.schema.objeto`.
- A pergunta-guia é **quem calcula e quando**: tabela (você escreve), view (a cada consulta), MV (pré-calculada e mantida), ST (só o dado novo, uma vez).
- **Managed** é o padrão recomendado; **external** deixa os arquivos num caminho seu e o `DROP` não os apaga; **foreign** é consulta a outro sistema.
- **Volumes** guardam arquivos; **funções** e **modelos** completam o schema.
- Padrão comum: **bronze com ST, silver com ST ou `AUTO CDC`, gold com MV**.

## Referências

- [Materialized views (Databricks)](https://docs.databricks.com/aws/en/ldp/materialized-views)
- [Streaming tables (Databricks)](https://docs.databricks.com/aws/en/ldp/streaming-tables)
- [Managed tables (Databricks)](https://docs.databricks.com/aws/en/tables/managed)
- [Volumes (Databricks)](https://docs.databricks.com/aws/en/volumes/)
- Posts relacionados: [Databricks Fundamentals]({{< relref "/posts/databricks/databricks.md" >}}), [Lakeflow Connect]({{< relref "/posts/databricks/databricks-lakeflowconnect.md" >}}), [Slowly Changing Dimensions]({{< relref "/posts/dados/slowly-changing-dimensions.md" >}})
