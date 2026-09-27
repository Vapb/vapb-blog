---
title: "Data Lakehouse no Google Cloud (Parte 2): BigQuery por dentro"
author: "vapb"
description: "Parte 2 do resumo do curso Build Data Lakes and Data Warehouses on Google Cloud: arquitetura do BigQuery (Dremel, Colossus, slots), storage nativo vs. data lake, particionamento, clustering e tabelas externas com Lakehouse."
date: 2026-09-27
tags: ["gcp", "bigquery", "gcp-lakehouse"]
toc: true
---

## Introdução

Segunda parte do resumo do curso [Build Data Lakes and Data Warehouses on Google Cloud](https://www.skills.google/paths/16/course_templates/54). Na [parte 1]({{< relref "gcp-lakehouse-parte-1.md" >}}) vimos o que é um data lakehouse e as peças que o formam no Google Cloud. Agora o foco é o **BigQuery**: como ele funciona por dentro e como consulta dados tanto no storage nativo quanto no data lake.

Série:

1. [Parte 1: lake, warehouse e lakehouse]({{< relref "gcp-lakehouse-parte-1.md" >}}) (módulos 1 e 2)
2. [Parte 2: BigQuery por dentro]({{< relref "gcp-lakehouse-parte-2.md" >}}) (módulo 3)
3. [Parte 3: governança, ML e migração]({{< relref "gcp-lakehouse-parte-3.md" >}}) (módulo 4)

## Módulo 3: Modernizando o data warehouse com BigQuery e Lakehouse

### Fundamentos do BigQuery

#### O problema do warehouse tradicional

A Cymbal gera diariamente um volume enorme de dados: vendas, cliques, estoque, feedback de clientes. Num warehouse on-premises, os arquitetos passariam boa parte do tempo com **capacity planning**: quantos servidores para a Black Friday? E os picos inesperados? Provisionar hardware, aplicar patches, rebalancear dados... **Um overhead caro que atrasa os insights.**

#### Fully managed e serverless

O **BigQuery** é o data warehouse **enterprise, totalmente gerenciado e serverless** do Google.

- **Fully managed**: hardware, rede e software de baixo nível ficam com o Google. Nada de patches, updates ou falhas de hardware para o seu time.
- **Serverless**: vai além. Não existe servidor para provisionar: você carrega os dados e consulta. O BigQuery aloca os recursos necessários e escala conforme a complexidade da query.

#### Separação entre storage e compute

O grande diferencial está na arquitetura: **storage e compute são separados**.

A analogia é uma biblioteca: os livros (dados) ficam guardados de forma confiável e barata no sistema de arquivos distribuído do Google (**Colossus**). Os bibliotecários são o compute, e o BigQuery pode chamar **milhares deles ao mesmo tempo** para varrer a biblioteca inteira. Esse motor de processamento distribuído é o **Dremel**.

Como são independentes, storage e compute **escalam separadamente**: mais dados, mais storage; queries mais pesadas, mais compute, pago só enquanto a query roda (dependendo do modelo de cobrança).

#### As peças por trás do BigQuery

Quando você roda uma query, quatro tecnologias internas do Google trabalham juntas:

| Peça | Papel | Na analogia da biblioteca |
|---|---|---|
| **Dremel** | Motor de execução: quebra a query em pedaços e executa em paralelo em milhares de slots | Os bibliotecários |
| **Colossus** | Sistema de arquivos distribuído do Google, onde os dados ficam guardados | As estantes |
| **Jupiter** | Rede interna de petabits que liga compute e storage (e faz o shuffle) | Os corredores entre estantes |
| **Borg** | Orquestrador de clusters que aloca as máquinas onde os slots rodam | O gerente que escala os bibliotecários |

O ponto-chave é que **o Dremel não guarda dados**: ele lê do storage pela rede Jupiter, processa e descarta. Como essa rede é extremamente rápida, separar compute e storage não custa performance, e é isso que torna a arquitetura viável.

#### Storage nativo vs. storage do data lake

Aqui é fácil confundir as coisas, então vale separar os dois caminhos:

**1. Storage nativo do BigQuery (tabelas gerenciadas).** Quando você carrega dados numa tabela do BigQuery, eles são gravados num **formato colunar proprietário (Capacitor)** dentro do **Colossus**. Você não vê arquivos nem buckets: o BigQuery cuida da compressão, da organização, da replicação e dos metadados. É o caminho de maior performance, ideal para dados "quentes".

Alguns detalhes práticos:

- **Os dados são seus, mas os arquivos não ficam visíveis**: o acesso é sempre via BigQuery, seja por SQL, pela **Storage Read API** (usada por Spark, Dataflow, Python) ou exportando para o Cloud Storage com `EXPORT DATA` (CSV, JSON, Avro ou Parquet).
- **Onde ficam**: na **location** escolhida ao criar o dataset, uma região (ex.: `southamerica-east1`, São Paulo) ou multi-região (`US`, `EU`), com replicação automática entre zonas. Essa escolha importa para latência, custo e compliance (LGPD).
- **Cobrança**: storage é cobrado separado do compute, por tamanho lógico ou físico (comprimido), e tabelas sem alteração há 90 dias ficam mais baratas (*long-term storage*).

**2. Storage do data lake (Cloud Storage).** No lake, os dados ficam em **buckets do Cloud Storage**, em **formatos abertos** (Parquet, ORC, Avro, com o Iceberg por cima). Os arquivos são seus: você enxerga, organiza e pode ler com outros motores, como Spark. O BigQuery lê esses arquivos via Lakehouse, sem copiá-los para o storage nativo.

**Detalhe curioso:** o próprio Cloud Storage também roda em cima do Colossus. Ou seja, fisicamente os dois acabam no mesmo sistema de arquivos. **A diferença real não é *onde* o dado fica, e sim *quem controla o formato e os metadados*:**

| | Storage nativo do BigQuery | Data lake no Cloud Storage |
|---|---|---|
| **Formato** | Capacitor (proprietário) | Parquet, ORC, Avro + Iceberg (abertos) |
| **Quem gerencia** | O BigQuery, de forma transparente | Você (buckets e arquivos visíveis) |
| **Quem consegue ler** | Só o BigQuery (ou via APIs dele) | BigQuery, Spark, Dataproc e outros motores |
| **Performance** | Máxima | Alta, mas depende da organização dos arquivos |
| **Uso típico** | Dashboards, BI, dados "quentes" | Dados brutos, grandes volumes, IA/ML, multicloud |

#### Slots e shuffle

- **Slot**: um "trabalhador virtual", uma unidade de CPU, RAM e rede. Numa query, o Dremel distribui potencialmente **milhares de slots**, cada um processando um pedaço dos dados em paralelo (**massively parallel processing**).
- **Shuffle**: quando os resultados parciais precisam ser combinados (`GROUP BY`, `JOIN`), o shuffle redistribui os dados intermediários entre os slots da próxima etapa, usando a rede interna de petabits do Google, o **Jupiter**.

#### Um motor, várias fontes

Essa separação é o que permite ao BigQuery consultar dados de várias origens:

| Fonte | Como o Dremel acessa |
|---|---|
| **Tabelas nativas do BigQuery** | Lê direto do storage colunar otimizado no Colossus (o caminho mais eficiente) |
| **Cloud Storage (ex.: Iceberg)** | O Lakehouse funciona como ponte, e o Dremel processa os dados do lake como se fossem nativos |
| **Bancos externos (ex.: AlloyDB)** | Federated queries: parte da query é "empurrada" (*push down*) para o banco, que devolve só os resultados para o join/agregação final |

**Com isso, o BigQuery deixa de ser só um data warehouse e vira um motor de analytics unificado**: uma única query SQL cruzando warehouse, data lake e bancos operacionais.

### Particionamento e clustering no BigQuery

Mesmo no BigQuery, com datasets do tamanho dos da Cymbal, queries que varrem tudo ficam lentas e caras. Duas técnicas resolvem isso: **particionamento** e **clustering**.

#### Particionamento

Particionar é como colocar **divisórias num arquivo de gavetas**: em vez de uma gaveta gigante, uma seção para cada ano, mês ou dia. No BigQuery, a tabela pode ser particionada por uma **coluna de data ou de inteiro**.

Exemplo com uma tabela de vendas fictícia da Cymbal, particionada por `transaction_date`:

**Partição `2025-08-01`**

| transaction_date | customer_id | product_category | sales_amount |
|---|---|---|---|
| 2025-08-01 | CUST002 | Headsets | 52 |
| 2025-08-01 | CUST002 | Keyboards | 186 |
| 2025-08-01 | CUST003 | Headsets | 465 |
| 2025-08-01 | CUST005 | Headsets | 57 |

**Partição `2025-08-02`**

| transaction_date | customer_id | product_category | sales_amount |
|---|---|---|---|
| 2025-08-02 | CUST003 | Shoes | 413 |
| 2025-08-02 | CUST002 | Headsets | 118 |
| 2025-08-02 | CUST004 | Consoles | 455 |

Numa query filtrando por um intervalo de datas (por exemplo, as vendas da semana passada), **o BigQuery só lê as partições daqueles dias** e ignora todas as outras. Menos dados lidos = query mais rápida e mais barata.

Criar uma tabela particionada (e já clusterizada, como veremos a seguir) é simples:

```sql
CREATE TABLE cymbal.sales
(
  transaction_date DATE,
  customer_id STRING,
  product_category STRING,
  sales_amount NUMERIC
)
PARTITION BY transaction_date
CLUSTER BY customer_id, product_category;
```

##### Na prática: a demo

O curso mostra uma demo com duas tabelas idênticas de page views da Wikipedia (mesmas colunas, mesmas linhas, mesmo volume), a única diferença é que uma é particionada por data. A mesma query foi rodada nas duas, comparando o **Execution details**:

| Métrica | Não particionada | Particionada |
|---|---|---|
| **Elapsed time** (tempo de relógio) | 14 s | 10 s |
| **Slot time consumed** (soma do tempo de todos os slots) | 7 h 16 min | 4 h 34 min |
| **Bytes shuffled** (dados movidos entre slots) | ~100 MB | ~100 KB |

O *slot time* é o que mais chama atenção: rodando num único processador, a primeira query levaria mais de 7 horas. **Só particionar a tabela reduziu bastante o consumo de recursos e, portanto, o custo.**

#### Clustering

Se o particionamento divide os dados em blocos grandes, o **clustering ordena os dados dentro de cada bloco**. É como organizar em ordem alfabética as pastas dentro de cada gaveta.

A Cymbal poderia clusterizar a tabela de vendas por `customer_id` ou `product_category`. Na partição `2025-08-01`, clusterizada por `customer_id`, as linhas ficam agrupadas por cliente:

| transaction_date | customer_id | product_category | sales_amount |
|---|---|---|---|
| 2025-08-01 | CUST002 | Headsets | 52 |
| 2025-08-01 | CUST002 | Keyboards | 186 |
| 2025-08-01 | CUST003 | Headsets | 465 |
| 2025-08-01 | CUST005 | Headsets | 57 |

```sql
SELECT *
FROM cymbal_sales
WHERE transaction_date = '2025-08-01'
  AND customer_id = 'CUST003';
```

O BigQuery primeiro vai na partição certa (pela data) e, como os dados estão ordenados por `customer_id`, **pula direto para os dados daquele cliente** em vez de ler a partição inteira.

#### E nas tabelas Iceberg?

Com tabelas Apache Iceberg no Cloud Storage, **o BigQuery não aplica seu próprio particionamento e clustering**: ele aproveita a estrutura que já está definida nos **metadados do Iceberg**. É o poder dos padrões abertos.

**Particionamento no Iceberg.** As partições normalmente são definidas e escritas por um motor de processamento como o **Apache Spark** (por exemplo, por `transaction_date`). Os metadados do Iceberg registram quais arquivos no Cloud Storage pertencem a cada data. Numa query com `WHERE transaction_date = '2025-08-15'`, o BigQuery (via Lakehouse) lê primeiro os metadados, identifica exatamente os arquivos daquela data e **descarta todo o resto** (*partition pruning*).

**Clustering no Iceberg.** O equivalente ao clustering é a **ordenação dos dados e as estatísticas por arquivo**. Os dados dentro dos arquivos Parquet ou ORC costumam estar ordenados por colunas como `customer_id`, e os metadados guardam estatísticas como os **valores mínimo e máximo** de `customer_id` em cada arquivo.

**Predicate pushdown.** Quando a query filtra um cliente específico, o planner consulta essas estatísticas e **pula qualquer arquivo cujo intervalo min/max não contém aquele `customer_id`**, mesmo que esteja na partição certa. É um nível de *pruning* ainda mais fino.

#### Por que isso importa

Particionamento e clustering juntos dão ao BigQuery controle fino sobre quais dados ler, com ganho de performance e economia que crescem junto com os dados. Seja em tabelas nativas ou Iceberg, o princípio é o mesmo: **usar metadados para pular dados desnecessários, e assim ter queries mais rápidas e mais baratas.**

### Lakehouse e tabelas externas

Na prática, os dados valiosos de uma empresa como a Cymbal estão espalhados em vários lugares e formatos. Como vimos na [parte 1]({{< relref "gcp-lakehouse-parte-1.md" >}}), manter warehouse e lake separados gera **silos**, **pipelines de ETL** que duplicam dados (com latência e custo) e **governança duplicada** em dois sistemas. O lakehouse resolve isso, e no Google Cloud o serviço que o torna real é o **Lakehouse**.

#### Tabelas externas

O Lakehouse funciona como **storage engine e conector**: estende o BigQuery para os dados que estão no object storage. Ele permite criar tabelas no BigQuery que **não guardam os dados**, apenas **apontam para os arquivos no data lake**. São as **tabelas externas**.

Exemplo da Cymbal: o time de ciência de dados guarda logs de servidor web em JSON num bucket. Antes, era preciso um pipeline para fazer o parse e carregar tudo no BigQuery. Com o Lakehouse, basta criar uma tabela externa sobre os arquivos:

```sql
CREATE EXTERNAL TABLE cymbal.clickstream_logs
WITH CONNECTION `projeto.us.lakehouse-connection`
OPTIONS (
  format = 'NEWLINE_DELIMITED_JSON',
  uris = ['gs://cymbal-datalake/weblogs/*.json']
);
```

A partir daí, dá para consultar o clickstream com SQL **como se fosse uma tabela nativa**, e até fazer **JOIN com a tabela de vendas nativa** para cruzar comportamento no site com hábitos de compra, sem mover nem duplicar nada.

#### Governança e segurança: access delegation

Um dos pontos mais fortes do Lakehouse é **centralizar a governança no BigQuery**, com segurança em nível de **linha** e **coluna** direto nas tabelas do Lakehouse. Isso funciona por **access delegation**:

1. A tabela do Lakehouse é associada a uma **service account** (via a *connection*) que tem permissão de leitura no bucket.
2. O usuário final precisa de permissão **só na tabela do BigQuery**, e não no bucket.

Assim, o time de governança da Cymbal pode liberar para um analista de marketing só as colunas `product_page_url` e `timestamp`, **mascarando dados pessoais** como `ip_address`. O analista acessa o que precisa, mas **nunca consegue contornar o BigQuery** para ler os arquivos brutos do lake.

#### Padrões abertos e Iceberg

Formatos abertos como o **Apache Iceberg** evitam **lock-in** com um fornecedor e garantem interoperabilidade. O Iceberg traz para o lake a confiabilidade de uma tabela SQL tradicional: transações ACID, schema evolution e time travel (detalhados na [parte 1]({{< relref "gcp-lakehouse-parte-1.md" >}})).

- **Suporte nativo no BigQuery**: jobs Spark escrevem tabelas Iceberg no Cloud Storage, a tabela é registrada no Lakehouse e fica disponível na hora para queries de alta performance no BigQuery.
- **Além da leitura**: dá para rodar `UPDATE`, `DELETE` e `MERGE` direto do BigQuery nas tabelas Iceberg. Útil para correções de dados ou para pedidos de **direito ao esquecimento** (LGPD/GDPR) usando SQL padrão.

#### O ganho para a Cymbal

Com o Lakehouse e formatos abertos, a Cymbal tem uma plataforma unificada e aberta: **um único ponto de acesso para analytics**, **governança consistente** sobre todos os dados e liberdade para usar a melhor ferramenta para cada tarefa (Spark para processamento, BigQuery para análise interativa), tudo sobre **uma única fonte da verdade**.

