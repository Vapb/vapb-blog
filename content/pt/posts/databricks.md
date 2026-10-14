---
title: "Databricks Fundamentals: lakehouse, formatos abertos, governança e a plataforma de dados com IA"
author: "vapb"
description: "Anotações de fundamentos do Databricks: Spark vs. Databricks, formatos abertos (Delta e Iceberg), Lakeflow, Lakebase, Unity Catalog, AI Gateway e Genie."
date: 2026-10-13
tags: ["databricks", "lakehouse", "data-engineering"]
toc: true
---

## Introdução

O Databricks se apresenta hoje como uma **Data Intelligence Platform**: uma plataforma construída em cima do **data lakehouse**, com IA embutida em cada camada (ingestão, processamento, governança e consumo). Estas são minhas anotações de fundamentos, baseadas no curso introdutório do Databricks Academy, e a ideia é entender **o que cada peça resolve**, não decorar a interface.

> **Nota:** a plataforma evolui rápido e os nomes dos produtos mudam bastante. Vale conferir a documentação oficial para o estado atual.

## O lakehouse no Databricks

O **lakehouse** é a ideia em que a plataforma inteira se apoia: em vez de manter um data lake (dado bruto e ML) e um data warehouse (BI) separados, com pipelines copiando dados entre eles, o Databricks propõe **uma só cópia do dado**, atendendo todos os usos. Foi o próprio Databricks quem popularizou o termo.

> A explicação completa do problema (DW vs. DL, data silos, limite da arquitetura de duas camadas) está em [Data Warehouse, Data Lake e Lakehouse]({{< relref "dw-dl-lakehouse.md" >}}). Aqui o foco é como o Databricks coloca isso em prática.

Na prática, o Databricks entrega o lakehouse assim:

- **O dado fica na nuvem do cliente**, como arquivos abertos em object storage (S3, ADLS ou GCS). O Databricks não é dono do dado.
- **Formato de tabela aberto** (Delta Lake ou Iceberg) por cima dos arquivos, que adiciona o que o lake não tinha: transações, schema e versionamento.
- **Governança em um só lugar**, o Unity Catalog, que cobre tudo isso com o mesmo modelo de acesso.
- **Engines diferentes sobre a mesma tabela:** Spark para engenharia e ML, SQL Warehouse para BI.
- **Compute separado do storage:** o processamento sobe e desce sem mexer nos dados.

Cada um desses pontos aparece com mais detalhe nas próximas seções.

## Spark vs. Databricks

É uma confusão comum, mas são coisas de naturezas diferentes: **Spark é um motor de processamento; Databricks é uma plataforma construída em volta dele**.

- **Apache Spark** é um framework open source de **processamento distribuído** (batch, streaming, SQL, ML). Ele só *processa*: não gerencia cluster, não tem catálogo, não controla acesso, não orquestra jobs.
- **Databricks** foi criado pelos mesmos criadores do Spark e entrega o Spark **como serviço gerenciado**, junto com tudo o que falta em volta dele.

| | **Apache Spark** | **Databricks** |
|---|---|---|
| **O que é** | Engine de processamento distribuído (open source) | Plataforma gerenciada de dados e IA, na nuvem |
| **Infraestrutura** | Você monta e opera o cluster (YARN, Kubernetes, standalone) | Clusters e compute serverless gerenciados, com autoscaling |
| **Armazenamento** | Não tem: lê de HDFS, S3, etc. | Lakehouse sobre object storage, com Delta/Iceberg |
| **Governança** | Não tem | Unity Catalog (acesso, lineage, auditoria) |
| **Orquestração e pipelines** | Não tem (usa Airflow, etc.) | Lakeflow Jobs e Declarative Pipelines |
| **Desenvolvimento** | Você escolhe a ferramenta | Notebooks colaborativos, SQL editor, integração com Git |
| **Performance** | Spark "puro" | Runtime otimizado (como o motor **Photon**) |
| **Custo** | Sem licença, mas com custo de operar | Pago por uso (DBUs) + a infra da nuvem |

Em resumo: o Databricks **usa** o Spark como um dos motores, mas o valor está na plataforma ao redor (gerenciamento, governança, colaboração e integração com IA). Dá para rodar Spark sem Databricks, mas aí toda essa operação passa a ser sua.

## Infraestrutura aberta: Delta e Iceberg

O que dá ao lakehouse suas garantias é o **formato de tabela aberto** por cima de arquivos **Parquet**. O arquivo Parquet sozinho não sabe o que é uma transação; o formato de tabela guarda, em um *log* de metadados, quais arquivos compõem a tabela em cada versão.

| Formato | Origem | Observações |
|---|---|---|
| **Delta Lake** | Databricks (hoje projeto aberto, Linux Foundation) | Formato nativo do Databricks. ACID via *transaction log*, time travel, `MERGE`, evolução de schema |
| **Apache Iceberg** | Netflix (Apache) | Muito adotado fora do Databricks (Snowflake, AWS, engines variadas) |

**Por que "aberto" importa:**

- Evita **vendor lock-in**: o dado não fica preso a um motor ou fornecedor.
- **Várias engines** (Spark, Trino, Flink, DuckDB...) leem a mesma tabela.
- Há esforço de **interoperabilidade** (como UniForm e o suporte a Iceberg no Unity Catalog), para que uma tabela Delta possa ser lida como Iceberg e vice-versa, reduzindo a "guerra de formatos".

## Mapa dos produtos

A tese atual do Databricks é que a plataforma deve servir não só analistas, mas também **agentes de IA** que consultam e agem sobre dados. Ela se organiza em seis nomes principais, e cada um agrupa vários componentes.

| Produto | Papel em uma frase |
|---|---|
| **Lakeflow** | Engenharia de dados: ingerir, transformar e orquestrar |
| **Lakehouse** | Onde o dado vive e é processado e consultado |
| **Lakebase** | Banco transacional (OLTP) para aplicações e agentes |
| **Unity Catalog** | Catálogo e governança de dados e IA |
| **Unity AI Gateway** | Governança do acesso a modelos de IA |
| **Genie** | Perguntas em linguagem natural sobre os dados |

### Lakeflow

Pipeline de ponta a ponta, em três partes. A ideia é trocar a colcha de retalhos (um ingestor, um orquestrador e um framework de transformação) por **uma ferramenta integrada**:

| Componente | O que faz |
|---|---|
| **Lakeflow Connect** | Conectores gerenciados para bancos (com **CDC**), SaaS e outras fontes, sem código de ingestão |
| **Lakeflow Spark Declarative Pipelines** | Você declara tabelas e transformações (SQL ou Python); a plataforma resolve dependências, retentativas e infra. Batch e streaming, com **expectations** (regras de qualidade) |
| **Lakeflow Jobs** | Orquestração: agenda e encadeia tarefas (notebooks, pipelines, SQL), com dependências, gatilhos e alertas |

Ferramentas de apoio: **Auto Loader** (ingestão incremental de arquivos novos no storage), **Structured Streaming** (streaming do Spark, por baixo dos pipelines) e **Asset Bundles** (jobs e pipelines como código, com deploy entre ambientes).

### Lakehouse

Armazenamento e computação analítica:

| Componente | O que faz |
|---|---|
| **Delta Lake / Iceberg** | Formatos de tabela abertos sobre Parquet (ACID, time travel, `MERGE`) |
| **Spark e Databricks Runtime** | O motor de processamento distribuído, na versão otimizada da plataforma |
| **Photon** | Motor vetorizado em C++ que acelera SQL e DataFrames sem mudar o código |
| **Databricks SQL e SQL Warehouse** | O "lado warehouse": editor SQL, dashboards e compute dedicado a SQL, usado por BI e conexões JDBC/ODBC |
| **Serverless compute** | Compute gerenciado, sem configurar cluster, que escala sozinho |
| **Volumes** | Área governada para arquivos (CSV, JSON, imagens) |

#### Photon

O Spark roda na JVM (Java/Scala), e isso impõe custos: coleta de lixo, processamento linha a linha em vários caminhos de código e pouca exploração do hardware moderno. O **Photon** é a resposta do Databricks: um **motor de execução reescrito em C++**, que substitui partes do plano de execução do Spark mantendo a mesma API.

- **Execução vetorizada:** processa **lotes de valores de uma coluna** de uma vez, aproveitando cache e instruções SIMD da CPU, em vez de linha a linha.
- **Compatível com o código existente:** SQL, DataFrames e a API do Spark continuam iguais. Não há reescrita, é só ativar no cluster (ou usar um SQL Warehouse, onde já vem ligado).
- **Fallback:** se algum operador não é suportado, aquele trecho do plano roda no Spark normal e o resto segue no Photon.
- **Onde mais ajuda:** consultas SQL pesadas, junções, agregações, escrita em Delta/Parquet e tabelas muito largas. Para código que gasta tempo em UDFs Python ou em chamadas externas, o ganho é pequeno.
- **Custo:** consome mais DBUs por hora, mas costuma **terminar o trabalho bem mais rápido**, então o custo total do job frequentemente cai.

#### Databricks SQL

É o **"lado warehouse"** do lakehouse: a experiência de **SQL e BI** para analistas, que não precisam saber de Spark nem de clusters.

| Componente | O que faz |
|---|---|
| **SQL Warehouse** | O compute dedicado a SQL. Vem em três tipos: **Serverless** (sobe em segundos, escala sozinho e usa o Photon), **Pro** e **Classic** |
| **Editor SQL** | Escrever, salvar e compartilhar consultas, com autocomplete e histórico |
| **Dashboards e alertas** | Visualizações sobre as consultas e notificações quando uma métrica passa de um limite |
| **Conectores** | JDBC/ODBC e drivers (Python, Go, Node...), que permitem que **Power BI, Tableau, dbt** e aplicações consultem o lakehouse |
| **Query history / profile** | Histórico e perfil de execução para investigar consultas lentas |

Ideias-chave:

- **Separa o compute de SQL do compute de engenharia.** BI e pipelines rodam em recursos diferentes e não competem entre si; cada warehouse escala e é cobrado de forma independente.
- **Mesma tabela, outro motor.** O SQL Warehouse lê as **mesmas tabelas Delta** que os pipelines escrevem, sem copiar nada para um warehouse separado. Esse é o ponto central do lakehouse.
- **Concorrência:** o warehouse escala com o número de consultas simultâneas (adiciona clusters sob demanda e remove quando a fila acaba).
- **Governado pelo Unity Catalog:** as permissões, os filtros de linha e as máscaras de coluna valem também para SQL.
- **SQL padrão ANSI** com extensões para o lakehouse (`MERGE`, time travel, `COPY INTO`, funções de IA como `ai_query`).

### Lakebase

Banco **PostgreSQL gerenciado** (OLTP) integrado à plataforma, com compute e storage separados. A motivação: aplicações e agentes precisam de **leitura e escrita transacional de baixa latência**, algo que o lakehouse analítico não faz bem. Com o Lakebase, o dado operacional e o analítico ficam **próximos e governados juntos**, sem pipelines de sincronização entre um Postgres externo e o lakehouse.

### Unity Catalog

Com um único lugar para todos os dados, a governança também precisa ser única. O Unity Catalog governa **dados e IA** com o mesmo modelo:

- **Hierarquia de três níveis:** `catalog.schema.objeto` (tabelas, views, volumes, modelos, funções).
- **Controle de acesso** centralizado (grants, row filters, column masks), válido para qualquer workspace e engine.
- **Lineage** automático, da tabela/coluna de origem até dashboards e modelos.
- **Auditoria e descoberta** (busca e tags).
- **Delta Sharing:** protocolo aberto para compartilhar dados com outras organizações sem copiá-los.

### Unity AI Gateway

É o equivalente do Unity Catalog para o tráfego de IA: um ponto único por onde passam as chamadas aos modelos (LLMs), com **controle de acesso, limites de uso, logs de auditoria, guardrails e monitoramento de custo**. Evita que cada time conecte seu próprio LLM por fora da governança.

### Genie

Interface de linguagem natural: usuários de negócio perguntam, o Genie gera o SQL e responde, sem que ninguém precise escrever consulta.

- Depende do **contexto semântico** dos dados: descrições, relacionamentos entre tabelas, métricas e exemplos de consultas. É a ideia de uma **ontologia** (o que "cliente ativo" ou "receita" significam *aqui*).
- Respeita as permissões do Unity Catalog: cada pessoa só enxerga o que já poderia consultar.
- Mostra o **SQL gerado**, o que permite auditar a resposta.

A lição é que a qualidade da IA em cima de dados é, em grande parte, **qualidade dos metadados e da governança**. Sem catálogo bem descrito, não há agente confiável.

> A plataforma muda rápido e os nomes são reorganizados com frequência (o Lakeflow, por exemplo, reuniu produtos que antes tinham outros nomes, como o Delta Live Tables). Confira na documentação.

## Visão geral

```
Fontes ──► Lakeflow ──► Lakehouse (Delta/Iceberg) ──► Genie / BI / ML / Agentes
                              │                              ▲
                              └────────► Lakebase ───────────┘
                    ───────── Unity Catalog + AI Gateway (governança) ─────────
```

Pontos para guardar:

- **Lakehouse** une o lake (barato, aberto) com o warehouse (confiável, rápido).
- **Formatos abertos** (Delta, Iceberg) são o que evita lock-in e permite várias engines.
- **Lakeflow** (pipelines), **Lakehouse** (análise) e **Lakebase** (OLTP) cobrem do dado bruto ao dado operacional.
- **Unity Catalog** e **AI Gateway** dão governança única para dados e IA.
- **Genie** fecha o ciclo com consumo em linguagem natural, apoiado em contexto semântico.

## Referências

- [Data Ingestion with Lakeflow Connect (Databricks Academy)](https://customer-academy.databricks.com/learn/learning-plans/10/data-engineer-learning-plan/courses/2963/data-ingestion-with-lakeflow-connect/lessons/39065/before-we-get-started)
- [Documentação do Databricks](https://docs.databricks.com/)
- [Ingesting Data into Databricks | Data Engineering in Databricks](https://www.youtube.com/watch?v=hEv5y_s0L3c) (Alex The Analyst)
- [Learn Databricks for FREE (Step-by-Step Guide)](https://www.youtube.com/watch?v=trJTgk8miw4) (Data with Baraa)
- [How to learn Databricks for data engineers fast (step by step guide)](https://www.youtube.com/watch?v=USKnnzUvKM4) (Data with Baraa)
