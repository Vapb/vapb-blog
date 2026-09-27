---
title: "Data Lakehouse no Google Cloud (Parte 1): lake, warehouse e lakehouse"
author: "vapb"
description: "Parte 1 do resumo do curso Build Data Lakes and Data Warehouses on Google Cloud: data lake vs. data warehouse, data lakehouse, Cloud Storage, Apache Iceberg, AlloyDB e federated queries."
date: 2026-09-27
tags: ["gcp", "bigquery", "gcp-lakehouse"]
toc: true
---

## Introdução

Esta série é baseada no curso [Build Data Lakes and Data Warehouses on Google Cloud](https://www.skills.google/paths/16/course_templates/54), do Google Cloud Skills Boost, que faz parte da trilha **Professional Data Engineer Certification**.

Dividi o resumo em três partes:

1. [Parte 1: lake, warehouse e lakehouse]({{< relref "gcp-lakehouse-parte-1.md" >}}) (módulos 1 e 2)
2. [Parte 2: BigQuery por dentro]({{< relref "gcp-lakehouse-parte-2.md" >}}) (módulo 3)
3. [Parte 3: governança, ML e migração]({{< relref "gcp-lakehouse-parte-3.md" >}}) (módulo 4)

Nesta primeira parte: **o que é um lakehouse e quais peças o formam**.

## Módulo 1: Introdução à engenharia de dados moderna no Google Cloud

### Os clássicos: data lake e data warehouse

Por anos, as empresas se apoiaram em dois modelos principais para armazenar dados em larga escala: **data lakes** e **data warehouses**. Eles têm propósitos diferentes e são otimizados para tipos de dados e cargas de trabalho diferentes.

#### Data lake

Pense em um data lake como um **grande reservatório**: ele guarda enormes volumes de dados brutos, no formato original. Cabe qualquer coisa:

1. **Dados estruturados**: tabelas de transações do banco de vendas.
2. **Dados semiestruturados**: logs JSON dos servidores web.
3. **Dados não estruturados**: imagens, vídeos e reviews de produtos enviados pelos clientes.

A premissa é *"guarde tudo agora, descubra como usar depois"*. A estrutura é aplicada **na leitura** (**schema-on-read**), não na escrita. Isso torna o data lake ideal para exploração, machine learning e processamento de big data. Os cientistas de dados da Cymbal (e-commerce fictício usado nos exemplos do curso), por exemplo, precisam do clickstream original, sem alterações, para treinar um novo motor de recomendação.

| Vantagens | Desvantagens |
|---|---|
| **Flexibilidade**: armazena qualquer tipo de dado | **Risco de virar um "data swamp"**: sem governança, vira um amontoado inutilizável |
| **Agilidade**: ingestão rápida | **Complexidade de gestão**: exige bastante esforço para manter |
| **Escalabilidade**: chega à escala de exabytes | **Análise demorada**: os dados precisam ser limpos antes de serem úteis |
| **Custo baixo**: usa object storage barato | **Riscos de segurança**: dados brutos aumentam riscos de compliance |
| **Suporte a analytics avançado**: ideal para treinar modelos de IA/ML | |

#### Data warehouse

Já o data warehouse é como uma **biblioteca muito bem organizada**: os dados são limpos, transformados e estruturados **antes** de serem armazenados (**schema-on-write**), já otimizados para análise e BI.

A premissa é *"estrutura e qualidade primeiro"*: o uso dos dados precisa estar definido antes do warehouse ser desenhado. Na Cymbal, métricas como *customer lifetime value* e vendas diárias já estão definidas, e o warehouse é construído para responder a elas de forma rápida e precisa.

| Vantagens | Desvantagens |
|---|---|
| **Velocidade**: otimizado para queries de alta performance | **Inflexibilidade**: não acomoda bem novos tipos de dados ou dados não estruturados |
| **Dados de alta qualidade**: informação consistente e confiável | **Custo**: caro para construir e manter |
| **Foco no negócio**: responde diretamente às perguntas do dia a dia | **Tipos de dados limitados**: pensado basicamente para dados estruturados |
| **Inteligência histórica**: análise profunda de tendências | **Desenvolvimento longo**: leva tempo para desenhar e implementar |

**Ficar preso a um só modelo é complicado, porque nenhum dos dois cobre bem todas as necessidades de dados de uma empresa.**

### A abordagem moderna: data lakehouse

Como os dois modelos são complementares, o ideal é juntar **a flexibilidade e o custo baixo do data lake** com **a velocidade e a precisão do data warehouse**. Daí nasce o **data lakehouse**.

A ideia é ter **uma plataforma única** que atenda BI tradicional, ciência de dados e IA **sem mover nem duplicar dados**. Isso é feito com uma **camada de metadados e governança** sobre arquivos em formato aberto guardados em object storage barato, como o Cloud Storage.

Para a Cymbal, o lakehouse resolve um problema clássico: **silos de dados**. Antes, as vendas ficavam no warehouse e as reviews dos clientes no data lake, e analisar as duas juntas era difícil. Com o lakehouse, uma única query consegue cruzar o sentimento das reviews com as tendências de venda.

No Google Cloud, isso é implementado com o **Lakehouse**, que aplica a governança e o motor de queries do BigQuery sobre dados no Google Cloud ou até em outras clouds, usando formatos abertos como **Parquet, ORC e Avro**.

Benefícios:

- Menos redundância de dados
- Governança unificada
- Fim dos silos
- Mais flexibilidade e escalabilidade

### Escolhendo a arquitetura certa

- **Data warehouse (BigQuery)**: quando o foco é BI interativo e rápido sobre dados estruturados de negócio, como o time de finanças da Cymbal.
- **Data lake (Cloud Storage)**: armazenamento inicial e barato de grandes volumes de dados brutos, ideal para P&D de IA/ML, quando o uso final ainda não está definido.
- **Data lakehouse (BigQuery + Lakehouse)**: quando é preciso fazer tudo, BI, IA e ciência de dados, sobre **uma única cópia governada** dos dados.

## Módulo 2: Construindo um data lakehouse com Cloud Storage, formatos abertos e BigQuery

### A fundação do data lake: Cloud Storage

O armazenamento principal do lakehouse é o **Cloud Storage**: object storage massivamente escalável, durável e barato, que aceita praticamente qualquer arquivo, de qualquer tamanho ou formato. Se a estratégia for multicloud, os dados também podem ficar no object storage de outro provedor.

Uma das maiores vantagens é armazenar **dados multimodais** no mesmo lugar:

- **Estruturados**: organizados em formato predefinido, como uma planilha com linhas e colunas. Na Cymbal: clientes, catálogo de produtos, transações de venda. Fáceis de buscar e processar.
- **Semiestruturados**: sem modelo rígido, mas com tags ou marcadores que criam hierarquia. Exemplo: pedidos em JSON, com estrutura geral consistente, mas campos que variam por produto.
- **Não estruturados**: sem nenhuma organização predefinida, como texto de reviews, logs de chat de suporte e imagens de produtos. Mais complexos de processar, mas cheios de insights para analytics e IA.

O Cloud Storage guarda tudo isso **sem precisar definir a estrutura antes**, o que é essencial para a Cymbal continuar coletando novos tipos de dados e analisá-los depois.

### Apache Iceberg: formato de tabela aberto

Arquivos soltos no Cloud Storage não bastam: o lakehouse precisa de **estrutura e performance**. É aí que entram os **open table formats**, e o **Apache Iceberg** é um dos principais.

Imagine milhões de pedidos em arquivos no Cloud Storage. Para achar *"todos os pedidos da última semana de clientes de uma região"*, uma query baseada em arquivos teria que ler tudo. **O Iceberg adiciona uma camada de metadados sobre esses arquivos**: não move os dados, só os organiza e gerencia, funcionando como índice e catálogo.

- **Schema evolution**: adicionar ou renomear colunas sem quebrar dados ou aplicações existentes.
- **Hidden partitioning**: o particionamento é gerenciado automaticamente; o analista não precisa conhecer a organização dos arquivos.
- **Time travel**: consultar versões passadas dos dados, por exemplo reproduzir exatamente o estado usado num relatório do mês passado. Ótimo para auditoria e debug.
- **Transações atômicas**: vários processos lendo e escrevendo na mesma tabela sem corromper dados.

### BigQuery como motor central de processamento

Cloud Storage + Iceberg são a base; o **BigQuery é o motor que ativa esses dados**. Criando **tabelas Lakehouse**, a Cymbal usa o SQL do BigQuery para consultar diretamente os dados Iceberg no Cloud Storage, **sem duplicar dados nem montar processos de ETL**.

Além disso, o BigQuery tem seu **próprio storage gerenciado e otimizado**, ideal para datasets "quentes" que exigem a maior performance, como os dashboards de marketing. Resultado: uma única interface para consultar o data lake, o storage nativo ou os dois.

### Dados operacionais no AlloyDB

Os dados que fazem a operação rodar no dia a dia pedem outra solução. Exemplos na Cymbal:

- Quando o cliente clica em **"comprar agora"**, a transação precisa ser gravada na hora e com precisão.
- **Estoque** atualizado em tempo real nos vários centros de distribuição.
- **Acesso seguro e sem atrito** dos clientes às suas contas.

Esses casos exigem alto volume de transações, latência baixíssima e consistência forte, coisas para as quais bancos analíticos não foram feitos.

O **AlloyDB for PostgreSQL** é um banco totalmente gerenciado e compatível com PostgreSQL, pensado para workloads enterprise:

1. **Alta performance**: bem mais rápido que o PostgreSQL padrão, ideal para processar milhões de pedidos.
2. **Alta disponibilidade**: construído para resiliência, mantendo a operação no ar mesmo durante falhas.
3. **Compatibilidade com PostgreSQL**: aproveita skills e ferramentas que o time já tem, facilitando a migração.

### Federated queries: juntando dados operacionais e analíticos

As **federated queries** permitem ao BigQuery consultar sistemas externos, como o AlloyDB, **em tempo real, sem mover nem copiar os dados**. É a ponte entre os dados operacionais ao vivo e o histórico analítico.

Para cruzar o estoque em tempo real (AlloyDB) com o histórico de vendas (tabelas Iceberg):

1. Um administrador cria uma **connection** no BigQuery com as credenciais e configurações para acessar a instância do AlloyDB (setup feito uma única vez).
2. O analista usa a função **`EXTERNAL_QUERY`**, que recebe o ID da conexão e a query a ser executada no AlloyDB.

```sql
SELECT
  s.product_id,
  SUM(s.quantity) AS total_vendido,
  i.estoque_atual
FROM `cymbal.lakehouse.sales` AS s
JOIN EXTERNAL_QUERY(
  'projeto.us.alloydb-connection',
  'SELECT product_id, estoque_atual FROM inventory'
) AS i
  ON s.product_id = i.product_id
GROUP BY s.product_id, i.estoque_atual;
```

### Caso real: juntando tudo

Cloud Storage como fundação, Iceberg trazendo estrutura, BigQuery como motor e AlloyDB para os dados operacionais formam uma arquitetura flexível que aproveita tudo, de arquivos multimídia brutos a transações em tempo real.

