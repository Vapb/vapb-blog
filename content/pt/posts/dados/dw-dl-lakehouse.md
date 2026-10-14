---
title: "Data Warehouse, Data Lake e Lakehouse: a evolução da arquitetura de dados"
author: "vapb"
description: "Diferenças entre data warehouse, data lake e lakehouse, o problema dos data silos, por que a arquitetura de duas camadas chegou ao limite operacional e como o lakehouse resolve isso. Bônus: onde o Databricks entra."
date: 2026-10-13
tags: ["data-engineering", "lakehouse", "data-warehouse", "data-lake", "databricks"]
toc: true
aliases: ["/posts/dw-dl-lakehouse/"]
---

## Introdução

Data warehouse (DW), data lake (DL) e lakehouse (LH) não são três produtos concorrentes: são **três respostas, em momentos diferentes, para a mesma pergunta**: *como guardar e analisar os dados de uma empresa?* Cada arquitetura nasceu para corrigir o que a anterior não conseguia fazer.

Neste post vou seguir essa linha do tempo: o que cada uma é, onde ela falha, como a combinação das duas gerou o problema dos **data silos** e por que o lakehouse surgiu como saída.

## Data warehouse (DW)

O DW é a arquitetura mais antiga (anos 80/90) e foi desenhado para uma coisa: **responder perguntas de negócio com SQL, de forma rápida e confiável**.

- Guarda dados **estruturados** (tabelas, linhas e colunas) vindos de sistemas transacionais (ERP, CRM, banco da aplicação).
- Usa **schema-on-write**: o modelo é definido **antes** de gravar. O dado passa por **ETL** (extrair, transformar, carregar) e só entra já limpo e modelado (star schema, dimensões e fatos).
- Oferece **transações ACID**, consistência e alta performance em consultas analíticas.
- Atende bem **BI, relatórios e dashboards**.

O conceito moderno vem do **Kimball Group** (anos 80/90), que tratou o armazenamento de dados como **ativo de negócio**, com metodologia própria de modelagem dimensional.

**Tecnologias atuais:**

| Tecnologia | Nuvem | Destaque |
|---|---|---|
| Amazon Redshift | AWS | Primeiro DW em nuvem amplamente popular; armazenamento colunar e processamento paralelo |
| Google BigQuery | Google Cloud | *Serverless*, escala conforme o uso |
| Snowflake | AWS, Google, Azure | Permite pagar computação e armazenamento separadamente |

**Onde falha:**

- **Caro**: storage e compute costumam ser acoplados e o formato é, em geral, proprietário.
- **Rígido**: mudar o modelo exige retrabalho no ETL; times pequenos iterando rápido sentem o *schema-on-write* como obstáculo.
- **Ruim para dados não estruturados** (logs, JSON, imagens, texto, áudio) e para **machine learning**, que quer acesso aberto a dados brutos, não só a tabelas já agregadas.
- **Só SQL**: sem suporte nativo a Python/Spark, então o dado de ML precisa **sair** do warehouse, e é nessa movimentação que aparecem problemas de volume, atualidade e schema.

## Data lake (DL)

Nos anos 2010, com o volume de dados explodindo (web, apps, IoT, logs), o DW ficou caro e limitado. O data lake surgiu como alternativa.

- Guarda **qualquer tipo de dado**, no formato original: estruturado, semiestruturado e não estruturado.
- Usa **schema-on-read**: você grava primeiro e só dá estrutura **na hora de ler**. Padrão ELT: carrega bruto, transforma depois.
- Fica sobre **object storage** barato e praticamente ilimitado (S3, ADLS, Cloud Storage) em **formatos abertos** (Parquet, ORC, Avro, JSON, CSV).
- É a base natural para **ciência de dados e ML**, que precisam do dado bruto.

O termo foi cunhado por **James Dixon** (ex-CTO da Pentaho), que o descreveu como um grande corpo d'água em estado mais natural, alimentado continuamente, onde cada usuário pode "mergulhar" ou colher amostras. Os primeiros lakes foram construídos sobre **Hadoop (HDFS + MapReduce)** e consultados via **Hive**. No começo dos anos 2010, o **Apache Spark** os tornou viáveis em escala. Hoje o armazenamento é, na maioria dos casos, **object storage em nuvem** (S3, ADLS, Cloud Storage).

**Onde falha:**

- **Sem garantias transacionais**: arquivos são só arquivos. Duas escritas concorrentes podem corromper uma tabela, e não há `UPDATE`/`DELETE` confiável.
- **Sem garantia de schema**: transformar assumindo um schema sem validá-lo é o *"blind ETL"*, que quebra quando algo muda upstream.
- **Sem governança embutida**: controle de acesso, catálogo e qualidade são improvisados.
- **Performance fraca para BI**: consultar milhões de arquivos soltos é lento sem otimizações.
- Sem disciplina, vira um **data swamp** ("pântano de dados"): ninguém sabe o que existe, quem é o dono nem se o dado é confiável.

## Comparando DW e DL

| | **Data warehouse** | **Data lake** |
|---|---|---|
| **Tipos de dado** | Estruturado | Qualquer tipo |
| **Schema** | *Schema-on-write* (definido antes) | *Schema-on-read* (definido na leitura) |
| **Processo** | ETL | ELT |
| **Armazenamento** | Geralmente proprietário e caro | Object storage barato, formatos abertos |
| **Garantias** | ACID, consistência | Nenhuma nativa |
| **Uso principal** | BI, relatórios, SQL | ML, ciência de dados, dado bruto |
| **Governança** | Forte | Fraca, a cargo de quem monta |
| **Usuários típicos** | Analistas de negócio | Engenheiros e cientistas de dados |
| **Risco** | Rigidez e custo | Pântano de dados |

O ponto central: **DW e DL têm forças opostas**. O DW é confiável e rápido, mas caro e fechado. O DL é barato e flexível, mas sem garantias. Nenhum dos dois atende sozinho a empresa inteira.

## Data silos: o problema que nasce da combinação

Como nenhum atendia tudo, a solução prática foi **ficar com os dois**. A arquitetura típica passou a ser de **duas camadas**:

```
Fontes ──► Data Lake (dado bruto, ML) ──ETL──► Data Warehouse (BI)
```

Funciona, mas cria o problema dos **data silos**: dados isolados em sistemas separados, que não conversam bem entre si.

Um **data silo** é um repositório de dados controlado por uma área ou sistema e **inacessível ou incompatível** com o resto da organização. Vendas tem seu banco, marketing tem seu data mart, o time de dados tem o lake, o financeiro tem o DW. Cada um enxerga uma parte da verdade.

**Como os silos se formam:**

- Times e áreas escolhem **ferramentas diferentes** para necessidades diferentes.
- Cada sistema usa **formato e modelo próprios**, o que dificulta integrar.
- Dados são **copiados** de um lugar para outro por pipelines pontuais, sem dono claro.
- Ferramentas proprietárias **prendem o dado** dentro de um fornecedor.

**Consequências:**

- **Duplicação de dados** e de custo de armazenamento.
- **Inconsistência**: o "faturamento do mês" tem um valor no DW e outro no lake, e ninguém sabe qual está certo.
- **Dados desatualizados**: o DW só vê o que o ETL já copiou, então a análise é sempre um retrato atrasado.
- **Governança duplicada**: duas políticas de acesso, dois catálogos, duas trilhas de auditoria, e o risco de uma delas ficar para trás.
- **Visão fragmentada**: difícil cruzar BI com ML, ou ter uma visão única do cliente.
- **Time de dados vira gargalo**, gastando tempo mantendo pipelines de cópia em vez de gerar valor.

## O limite operacional da arquitetura de duas camadas

Foi aqui que o modelo **atingiu o limite operacional**. Não foi uma limitação de tecnologia pura, foi o custo de **operar** tudo isso:

| Problema | Impacto |
|---|---|
| **Pipelines ETL lake → DW** | Frágeis, caros de manter, e cada falha atrasa o dado |
| **Dado em dois lugares** | Pagar storage e processamento duas vezes, com versões divergentes |
| **Latência** | O DW sempre está atrás do lake |
| **Governança em duas frentes** | Permissões, auditoria e *lineage* repetidos e difíceis de manter consistentes |
| **ML e BI em stacks separadas** | Cientistas usam o lake; analistas, o DW; ninguém trabalha sobre o mesmo dado |
| **Lock-in** | O dado no DW proprietário só é lido pelo próprio DW |
| **Escala de pessoas** | Quanto mais fontes e times, mais pipelines, mais silos, mais manutenção |

Ou seja: cada nova fonte, time ou caso de uso **multiplicava a complexidade**. A arquitetura escalava em dados, mas **não escalava em operação**. A pergunta passou a ser: *e se o próprio lake pudesse oferecer o que o DW oferece?*

## Lakehouse (LH) como solução

O lakehouse junta o melhor dos dois mundos em **uma única arquitetura**:

> **Lakehouse = armazenamento barato e aberto do data lake + confiabilidade, governança e performance de um data warehouse.**

### Antes e depois

| | **Antes: dois ambientes** | **Agora: lakehouse** |
|---|---|---|
| **Sistemas** | Um lake (ML, dado bruto) e um DW (BI), cada um para um fim | **Uma plataforma** para BI, engenharia, streaming e ML |
| **Cópias do dado** | Lake e DW, sincronizados por ETL | **Uma só cópia**, sem mover nem duplicar |
| **Complexidade** | Dois sistemas, pipelines de cópia, duas stacks para operar | **Fim da complexidade de manter dois sistemas** |
| **Performance** | Boa só no DW; o lake era lento para SQL | SQL de alta performance **direto sobre o lake** |
| **Formato** | Proprietário no DW, arquivos soltos no lake | **Formato aberto** (Parquet + camada de tabela) |
| **Governança** | Duplicada, uma em cada lado | **Unificada**: um catálogo, um controle de acesso, um lineage |
| **Custo** | Storage e processamento pagos duas vezes | Object storage barato, compute sob demanda |

### O que viabiliza: Delta Lake e os formatos de tabela abertos

O truque é uma **camada de metadados/transações** em cima dos arquivos do lake: os **formatos de tabela abertos**, como **Delta Lake**, **Apache Iceberg** e **Apache Hudi**.

O **Delta Lake** (criado pelo Databricks, hoje projeto aberto da Linux Foundation) é o exemplo mais conhecido. Os dados continuam sendo arquivos **Parquet** no object storage, mas ao lado deles existe um **transaction log** (`_delta_log`) que registra, em ordem, cada operação feita na tabela: quais arquivos foram adicionados e quais removidos. A "tabela" passa a ser **o que o log diz que ela é**, não o conteúdo bruto da pasta. É isso que dá transação, versão e consistência a algo que antes era só um monte de arquivos.

O arquivo Parquet sozinho não sabe o que é uma transação; o formato de tabela mantém o *log* de quais arquivos compõem cada versão da tabela e, com isso, entrega:

- **Transações ACID** direto no object storage.
- **Schema enforcement e evolução de schema**.
- **Versionamento e time travel** (consultar a tabela como ela era ontem).
- **`UPDATE`, `DELETE` e `MERGE`** confiáveis.
- **Batch e streaming** sobre a mesma tabela.
- **Performance de consulta** com índices, estatísticas e organização de arquivos.

Além disso:

- **Uma só cópia do dado** serve BI, engenharia, streaming e ML, sem ETL de um sistema para o outro.
- **Storage e compute desacoplados**: escala um sem escalar o outro.
- **Governança centralizada** (catálogo, controle de acesso, *lineage*) válida para tudo.
- **Formatos abertos** reduzem o lock-in: várias engines (Spark, Trino, Flink, DuckDB) leem a mesma tabela.

### Tecnologias que entregam cada peça

| Peça | Tecnologias | O que resolve |
|---|---|---|
| Formato de arquivo | Parquet | Colunar, com schema, base de tudo |
| ACID e camada de tabela | Delta Lake, Apache Iceberg, Apache Hudi | Transações como num banco tradicional, sobre object storage |
| SQL de alta performance | Spark, Presto/Trino, Databricks SQL, BigQuery | Consultas quase interativas direto no lake, sem ETL para um DW |
| Serviços gerenciados | Databricks, Amazon Athena, AWS Glue, BigQuery + Iceberg | Reduz o esforço de operar essas peças |

### O que o lakehouse ainda não resolve

- É uma **categoria em maturação**: práticas e ferramentas de qualidade de dados são menos consolidadas que em DWs tradicionais.
- **A base continua sendo um lake**: o formato de tabela mitiga os problemas de schema e confiabilidade, mas **não elimina a necessidade de disciplina** (modelagem, ownership, catálogo). Sem isso, o pântano reaparece.

### Evolução em uma linha

```
Data Warehouse ──► Data Lake ──► Lakehouse
(estruturado,      (qualquer dado,  (lake aberto e barato
 confiável, caro)   barato, sem      + garantias e governança
                    garantias)       do warehouse)
```

### Três arquiteturas lado a lado

| | **Data warehouse** | **Data lake** | **Lakehouse** |
|---|---|---|---|
| **Dados** | Estruturados | Todos os tipos | Todos os tipos |
| **Armazenamento** | Proprietário | Object storage | Object storage |
| **Formato** | Fechado | Aberto, sem camada de tabela | Aberto, com camada de tabela (Delta, Iceberg, Hudi) |
| **ACID** | Sim | Não | Sim |
| **BI / SQL** | Excelente | Fraco | Bom |
| **ML / dado bruto** | Fraco | Excelente | Excelente |
| **Governança** | Forte | Fraca | Forte e unificada |
| **Custo** | Alto | Baixo | Baixo |
| **Cópias do dado** | Uma, mas isolada | Uma, mas sem garantias | Uma só, para tudo |
| **Silos** | Cria silos | Cria silos | Reduz silos |

> **Cuidado com a ideia de que o lakehouse "elimina" o DW.** Ele **absorve** o que o warehouse tinha de bom (ACID, SQL, governança) em cima de um lake. Na prática, muita empresa convive com os dois por um tempo e migra de forma gradual. Na [série de Lakehouse no Google Cloud]({{< relref "/posts/gcp/gcp-lakehouse-parte-1.md" >}}) isso aparece no BigQuery lendo tabelas Iceberg do Cloud Storage.

## Quando usar cada um

- **Data warehouse**: foco em BI interativo e rápido sobre dados estruturados de negócio, com métricas já bem definidas (financeiro, vendas diárias).
- **Data lake**: armazenamento inicial e barato de grandes volumes de dado bruto, quando o uso final ainda não está definido (P&D de IA/ML).
- **Lakehouse**: quando é preciso fazer tudo (BI, IA e ciência de dados) sobre **uma única cópia governada** dos dados.

## Arquitetura medalhão

Dentro de um lakehouse, é comum organizar os dados em **camadas de qualidade crescente**, a chamada **arquitetura medalhão**:

| Camada | Conteúdo |
|---|---|
| **Bronze** | Dado bruto, como chegou da fonte, sem transformação |
| **Silver** | Dado limpo, deduplicado, com schema aplicado e entidades integradas |
| **Gold** | Dado agregado e modelado para consumo (BI, métricas, features de ML) |

É uma forma de trazer para dentro do lake a disciplina de modelagem que o DW sempre teve, sem perder o dado bruto.

## Bônus: e o Databricks?

O conceito de lakehouse foi popularizado pelo **Databricks**, criado pelos mesmos autores do Apache Spark e do Delta Lake. A empresa propôs o termo justamente para descrever essa fusão entre lake e warehouse e construiu sua plataforma em cima dessa ideia.

No Databricks, as peças do lakehouse aparecem assim:

| Conceito do lakehouse | Peça no Databricks |
|---|---|
| Armazenamento aberto e barato | Dados no object storage do próprio cliente (S3, ADLS, GCS) |
| Camada de tabela com ACID | **Delta Lake** (com suporte a **Iceberg**) |
| Processamento | **Apache Spark** e o motor **Photon** |
| O lado "warehouse" (SQL e BI) | **Databricks SQL** e SQL warehouses |
| Ingestão e pipelines | **Lakeflow** |
| Governança unificada | **Unity Catalog** |
| Camadas bronze/silver/gold | Padrão recomendado para organizar as tabelas |

Em resumo: o Databricks não é "o" lakehouse, é **uma implementação** dele. A mesma ideia pode ser montada com outras peças (por exemplo, Iceberg + Trino/Spark no S3, ou BigQuery lendo Iceberg no Cloud Storage), e o que importa é o princípio: **uma cópia do dado, em formato aberto, com garantias e governança únicas**.

Para entrar nos detalhes da plataforma (Spark vs. Databricks, Delta e Iceberg, Lakeflow, Lakebase, Unity Catalog), veja o post de [fundamentos do Databricks]({{< relref "/posts/databricks/databricks.md" >}}).

## Resumo

- **DW**: dados estruturados, schema-on-write, ETL, ACID e ótimo para BI, mas caro, rígido e ruim para dados não estruturados e ML.
- **DL**: qualquer dado, schema-on-read, barato e ótimo para ML, mas sem ACID nem governança, com risco de virar pântano.
- **Data silos**: ter DW e DL separados gera cópias, inconsistência, dados atrasados e governança duplicada.
- **Limite operacional**: a arquitetura de duas camadas escala em dados, mas não em operação (pipelines frágeis, custo dobrado, times travados).
- **Lakehouse**: lake aberto e barato com a confiabilidade do warehouse, graças aos **formatos de tabela abertos** (Delta, Iceberg, Hudi).
- **Databricks** popularizou o conceito e é uma das implementações, mas a ideia é independente de fornecedor.

## Referências

- [What is a Data Lakehouse? (Databricks)](https://www.databricks.com/glossary/data-lakehouse)
- [Lakehouse: A New Generation of Open Platforms that Unify Data Warehousing and Advanced Analytics (CIDR 2021)](https://www.cidrdb.org/cidr2021/papers/cidr2021_paper17.pdf)
- [Delta Lake](https://delta.io/) e [Apache Iceberg](https://iceberg.apache.org/)
