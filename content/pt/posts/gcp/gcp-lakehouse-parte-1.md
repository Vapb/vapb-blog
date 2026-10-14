---
title: "Data Lakehouse no Google Cloud (Parte 1): lake, warehouse e lakehouse"
author: "vapb"
description: "Parte 1 do resumo do curso Build Data Lakes and Data Warehouses on Google Cloud: data lake vs. data warehouse, data lakehouse, Cloud Storage, Apache Iceberg, AlloyDB e federated queries."
date: 2026-09-27
tags: ["gcp", "bigquery", "gcp-lakehouse"]
toc: true
aliases: ["/posts/gcp-lakehouse-parte-1/"]
---

## Introdução

Esta série é baseada no curso [Build Data Lakes and Data Warehouses on Google Cloud](https://www.skills.google/paths/16/course_templates/54), do Google Cloud Skills Boost, que faz parte da trilha **Professional Data Engineer Certification**.

Dividi o resumo em três partes:

1. [Parte 1: lake, warehouse e lakehouse]({{< relref "/posts/gcp/gcp-lakehouse-parte-1.md" >}}) (módulos 1 e 2)
2. [Parte 2: BigQuery por dentro]({{< relref "/posts/gcp/gcp-lakehouse-parte-2.md" >}}) (módulo 3)
3. [Parte 3: governança, ML e migração]({{< relref "/posts/gcp/gcp-lakehouse-parte-3.md" >}}) (módulo 4)

Nesta primeira parte: **o que é um lakehouse e quais peças o formam**.

## Módulo 1: Introdução à engenharia de dados moderna no Google Cloud

> **Conceitos gerais:** a comparação completa entre DW, DL e lakehouse (vantagens, desvantagens, data silos e por que o lakehouse surgiu) está em [Data Warehouse, Data Lake e Lakehouse]({{< relref "/posts/dados/dw-dl-lakehouse.md" >}}). Aqui ficam só as anotações do curso.

### Lake vs. warehouse (resumo do curso)

- **Data lake**: dado bruto em qualquer formato, **schema-on-read**. Bom para exploração e ML (ex.: a Cymbal, e-commerce fictício do curso, treina recomendação com o clickstream original). Risco: *data swamp*.
- **Data warehouse**: dado limpo e estruturado antes de gravar, **schema-on-write**. Bom para BI com métricas já definidas (ex.: *customer lifetime value*, vendas diárias). Risco: inflexível e caro.
- Ficar preso a um só modelo não cobre todas as necessidades.

### Lakehouse no Google Cloud

- Plataforma única para BI, ciência de dados e IA **sem mover nem duplicar dados**: camada de metadados e governança sobre arquivos abertos (**Parquet, ORC, Avro**) em object storage.
- Resolve o **silo** da Cymbal: vendas no warehouse, reviews no lake. Uma única query cruza sentimento das reviews com tendência de vendas.
- Implementado com o **Lakehouse**, que aplica governança e motor de queries do **BigQuery** sobre dados no Google Cloud ou em outras clouds.

### Escolhendo a arquitetura

- **DW (BigQuery)**: BI interativo sobre dados estruturados (finanças).
- **DL (Cloud Storage)**: armazenamento bruto e barato, uso final indefinido (P&D de IA/ML).
- **Lakehouse (BigQuery + Lakehouse)**: BI, IA e ciência de dados sobre **uma única cópia governada**.

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

