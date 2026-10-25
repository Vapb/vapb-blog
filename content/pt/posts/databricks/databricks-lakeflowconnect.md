---
title: "Lakeflow Connect: ingestão, Delta Lake e medalhão"
author: "vapb"
description: "Anotações sobre o Lakeflow Connect: o que é, os tipos de conectores (SaaS, CDC, query-based e community), como cada um funciona por baixo com Unity Catalog e Spark Declarative Pipelines, e as categorias de fontes suportadas."
date: 2026-10-14
tags: ["databricks", "lakeflow", "data-engineering"]
toc: true
aliases: ["/posts/databricks-lakeflowconnect/"]
---

## Introdução

Nas [anotações de fundamentos do Databricks]({{< relref "/posts/databricks/databricks.md" >}}) o **Lakeflow** apareceu como a camada de engenharia de dados da plataforma, dividida em Connect, Spark Declarative Pipelines e Jobs. Aqui o foco é a primeira peça: o **Lakeflow Connect**, que cuida da **ingestão**, ou seja, de levar o dado das fontes para dentro do lakehouse.

> **Nota:** a plataforma muda rápido e conectores novos entram o tempo todo. A lista de fontes suportadas deve ser conferida na documentação oficial.

## O que é o Lakeflow Connect

O Lakeflow Connect é o conjunto de **conectores de ingestão** do Databricks. A proposta é trocar o trabalho que normalmente se faz à mão (script de extração, controle de incremental, tratamento de schema, retentativas, agendamento) por conectores **gerenciados**, configurados na própria plataforma e já integrados à governança do **Unity Catalog**.

O destino é sempre o mesmo: **tabelas Delta governadas pelo Unity Catalog**, prontas para serem usadas pelo resto do lakehouse.

## Como funciona: tipos de conectores

Os conectores se dividem por **a forma como o dado é lido na fonte**, e isso muda bastante a arquitetura por baixo:

| Tipo | Fontes típicas | Como lê |
| --- | --- | --- |
| **SaaS** | Salesforce, Workday, ServiceNow, Google Analytics | Pela API da própria aplicação |
| **CDC** | Bancos de dados (ex.: SQL Server, MySQL, PostgreSQL) | Lendo o log de transações do banco |
| **Query-based** | Bancos e warehouses | Executando consultas (full ou incremental por coluna de controle) |
| **Community** | Qualquer fonte sem conector oficial | Código da comunidade ou próprio, sobre a infra do Databricks |

**CDC** (*change data capture*) captura só o que mudou (inserts, updates e deletes) a partir do log do banco, com baixo impacto na fonte. O **query-based** é o caminho quando não dá para ler o log: ele consulta a fonte, e por isso depende de uma coluna que indique o que mudou (ex.: `updated_at`) para ser incremental.

## Funcionamento por tipo

### Conectores SaaS

O fluxo é o mais simples, porque a fonte já expõe uma API:

1. **Credenciais** da aplicação guardadas no **Unity Catalog** (como uma *connection*), sem ficar em código ou notebook.
2. Um **pipeline do SDP** (Spark Declarative Pipelines) é criado e usa essa conexão.
3. O pipeline chama a **API** da aplicação.
4. O resultado é gravado em **streaming tables** (tabelas Delta).

### Conectores de banco com CDC (ex.: RDS)

Aqui o banco é uma fonte "viva" e a leitura do log exige uma peça a mais, o **ingestion gateway**:

1. A *connection* com as credenciais fica no **Unity Catalog**.
2. O **ingestion gateway** se conecta ao banco e lê o log de mudanças continuamente.
3. As mudanças são gravadas num **staging**, que é um **volume do Unity Catalog**.
4. O **ingestion pipeline** (SDP) lê do staging e aplica as mudanças.
5. O destino são **streaming tables Delta**, já refletindo inserts, updates e deletes.

A separação em duas partes é intencional: o **gateway** fica sempre conectado ao banco e só captura; o **pipeline** processa e aplica. O volume de staging desacopla os dois e evita perder mudanças caso o pipeline esteja parado.

### Conectores da comunidade

São conectores para fontes que não têm suporte oficial. Rodam sobre a mesma base (Unity Catalog para credenciais e governança, SDP para executar o pipeline), mas o **código de leitura da fonte** vem da comunidade ou é escrito por você, normalmente usando a API de *Python data source* do Spark.

## Categorias de fontes

Os conectores também podem ser vistos pelo **tipo de origem**:

- **Applications:** sistemas SaaS (CRM, ERP, marketing, analytics).
- **File sources:** arquivos em object storage ou SFTP.
- **Databases:** bancos transacionais, normalmente via CDC.
- **Warehouses:** outros data warehouses, normalmente via query-based.
- **Message buses:** Kafka, Kinesis, Event Hubs e similares.
- **Zerobus Ingest:** envio de eventos **direto para tabelas Delta**, sem precisar de um message bus no meio. A aplicação escreve na tabela, em vez de publicar num broker que depois alguém precisa consumir.

## Demo

*(a anotar)*
