---
title: "Data Lakehouse no Google Cloud (Parte 3): governança, ML e migração"
author: "vapb"
description: "Parte 3 do resumo do curso Build Data Lakes and Data Warehouses on Google Cloud: Knowledge Catalog, Sensitive Data Protection, IAM, BigQuery ML, Agent Platform, arquitetura medalhão, migração e custos."
date: 2026-09-27
tags: ["gcp", "bigquery", "gcp-lakehouse"]
toc: true
---

## Introdução

Terceira e última parte do resumo do curso [Build Data Lakes and Data Warehouses on Google Cloud](https://www.skills.google/paths/16/course_templates/54). Depois de ver os fundamentos do lakehouse na [parte 1]({{< relref "gcp-lakehouse-parte-1.md" >}}) e o BigQuery na [parte 2]({{< relref "gcp-lakehouse-parte-2.md" >}}), aqui entram os temas de uma plataforma de dados "de empresa": **governança, segurança, machine learning, migração e custos**.

Série:

1. [Parte 1: lake, warehouse e lakehouse]({{< relref "gcp-lakehouse-parte-1.md" >}}) (módulos 1 e 2)
2. [Parte 2: BigQuery por dentro]({{< relref "gcp-lakehouse-parte-2.md" >}}) (módulo 3)
3. [Parte 3: governança, ML e migração]({{< relref "gcp-lakehouse-parte-3.md" >}}) (módulo 4)

## Módulo 4: Padrões avançados de lakehouse e governança de dados

### Governança e segurança numa plataforma unificada

Para um varejista global como a Cymbal, cuidar bem dos dados não é só tarefa técnica: é **função central do negócio**. Dados de clientes, vendas e estoque precisam ser **precisos, fáceis de encontrar e seguros**, porque alimentam desde o marketing personalizado até a cadeia de suprimentos.

#### Knowledge Catalog: o hub de metadados

**Metadados são dados sobre os dados.** Eles respondem: quem criou, quando, o que contém, como se relaciona com outros dados, quem é o dono e qual o nível de sensibilidade.

Sem um sistema central de metadados, gerenciar dados em escala vira caos. O **Knowledge Catalog** é um **catálogo universal** de todos os ativos de dados da Cymbal, estejam eles no BigQuery, no Cloud Storage ou no Lakehouse. Em vez de procurar em vários sistemas, os analistas usam o catálogo para:

- **descobrir** os datasets de que precisam;
- entender a **linhagem** (*lineage*) dos dados, ou seja, de onde vêm e por onde passaram;
- gerenciar e **enriquecer os metadados**.

Com uma única fonte de referência, a Cymbal gerencia dados em escala mantendo **consistência e qualidade**.

#### Sensitive Data Protection

Nomes, endereços e números de cartão de crédito são dados sensíveis: um vazamento significa dano à reputação e multas pesadas. O **Sensitive Data Protection** atua em três etapas sobre todo o lakehouse:

1. **Descoberta**: scans em tabelas do BigQuery e buckets do Cloud Storage procuram padrões como números de cartão ou e-mails.
2. **Classificação**: o dado encontrado é classificado por nível de sensibilidade, para receber os controles certos.
3. **Proteção**: técnicas de **mascaramento** ou **tokenização** desidentificam o dado. Um atendente, por exemplo, vê só os 4 últimos dígitos do cartão, e o número completo é substituído por um *token* sem valor sensível.

#### IAM e o princípio do menor privilégio

O **Identity and Access Management (IAM)** é a base do controle de acesso. A Cymbal segue o **princípio do menor privilégio**: cada pessoa recebe só o acesso mínimo necessário para o seu trabalho. No lakehouse, isso se traduz assim:

| Serviço | Granularidade | Quem acessa |
|---|---|---|
| **Cloud Storage** | Nível de bucket | Engenheiros e service accounts responsáveis pela ingestão |
| **BigQuery** | Nível de dataset e tabela | Analistas: leitura dos dados curados de vendas. Cientistas de dados: criar e alterar tabelas em datasets de *sandbox* |
| **Lakehouse** | Linha e coluna, sobre dados no Cloud Storage | Estende a segurança fina do BigQuery ao lake (via access delegation, vista na [parte 2]({{< relref "gcp-lakehouse-parte-2.md" >}})) |

#### Segurança fina: linhas e colunas

- **Column-level security**: restringe colunas específicas. Um analista de marketing vê o histórico de compras, mas não os dados de contato do cliente. Ideal para proteger **PII** (dados pessoais identificáveis).
- **Row-level security**: filtra quais linhas cada usuário enxerga. O gerente de vendas da América do Norte só vê as vendas da sua região, algo essencial numa multinacional como a Cymbal.

Um exemplo de row-level security no BigQuery:

```sql
CREATE ROW ACCESS POLICY vendas_america_norte
ON cymbal.sales
GRANT TO ('group:vendas-na@cymbal.com')
FILTER USING (region = 'North America');
```

Nas tabelas do Lakehouse no Cloud Storage também dá para aplicar **dynamic data masking**, que mascara o valor da coluna na hora da consulta conforme quem está consultando.

### Demo: Data Loss Prevention

A demo mostra o Sensitive Data Protection na prática com um cenário comum: a Cymbal lançou um **programa de fidelidade** e os dados dos novos clientes (incluindo e-mails, telefones e comentários livres de pesquisas) precisam ser liberados para o marketing **sem expor PII**.

O ponto central é que, num data lake, **não dá para encontrar dado sensível manualmente**: são milhares de tabelas, arquivos e colunas, e o dado sensível aparece onde menos se espera (um CPF dentro de um campo de comentário, por exemplo). A ferramenta resolve isso com alguns conceitos:

- **Discovery contínuo**: em vez de uma auditoria pontual, o scan roda automaticamente sempre que tabelas são criadas ou os dados mudam. A proteção acompanha o crescimento do lake.
- **InfoTypes e likelihood**: a ferramenta procura *tipos* de informação (documentos, e-mails, cartões, datas de nascimento) e atribui uma **probabilidade** de cada campo ser sensível. É um trade-off entre encontrar tudo que *pode* ser sensível e evitar falsos positivos.
- **Visão de risco**: além de dizer *onde* está o dado sensível, mede o **nível de exposição** que ele cria, ajudando a priorizar o que proteger primeiro.
- **Resultados como dados**: os achados são publicados em tabelas do BigQuery, então dá para consultar, montar dashboards e acompanhar a postura de segurança com SQL.

**A lógica é: primeiro descobrir e classificar, depois proteger.** Com o mapa do dado sensível em mãos, seja numa tabela Iceberg no Cloud Storage, no storage nativo do BigQuery ou num banco transacional, aplicam-se os controles vistos acima: mascaramento, tokenização e segurança por linha e coluna.

### Analytics e machine learning no lakehouse

Tradicionalmente, treinar um modelo de ML exigia **tirar os dados do warehouse** e levá-los para outro ambiente: um processo lento, caro e que criava mais silos. No lakehouse do Google Cloud, a ideia se inverte: **o ML vai até os dados**, e não o contrário.

#### BigQuery ML: ML com SQL

O **BigQuery ML** permite criar e usar modelos de machine learning **com SQL**, sem precisar dominar Python ou TensorFlow. Isso **democratiza o ML**: analistas de dados passam a construir modelos preditivos sem sair do BigQuery.

O exemplo do curso é prever **churn** (clientes com risco de não comprar de novo). O ciclo segue as etapas clássicas de ML, só que tudo em SQL:

1. **Feature engineering**: uma query cria os sinais que podem prever churn, como *recency* (dias desde a última compra), *frequency* (compras no último ano), *monetary value* (total gasto) e tempo de casa do cliente.
2. **Treino**: um único `CREATE MODEL`. Por ser uma classificação binária (churn ou não), regressão logística ou *boosted trees* são boas escolhas. O BigQuery cuida de toda a complexidade do treino.
3. **Avaliação**: `ML.EVALUATE` devolve métricas como acurácia, precisão e recall.
4. **Predição**: `ML.PREDICT` gera a probabilidade de churn de cada cliente, que vira insumo para campanhas de reengajamento.

```sql
CREATE OR REPLACE MODEL cymbal_ecommerce.customer_churn_predictor
OPTIONS (model_type = 'LOGISTIC_REG') AS
SELECT
  customer_id,
  recency,
  frequency,
  monetary_value,
  (total_purchases > 1) AS will_return -- label
FROM cymbal_ecommerce.customer_purchase_summary;
```

#### Agent Platform: quando o BigQuery ML não basta

Para projetos mais complexos, como um **motor de recomendação de produtos**, é preciso a flexibilidade de uma plataforma de ML completa. Aí entra o **Agent Platform** (plataforma end-to-end do Google Cloud para construir, publicar e gerenciar modelos; antes conhecida como **Vertex AI**). O diferencial é a **integração nativa com o BigQuery**.

O fluxo típico cobre todo o ciclo de vida do modelo:

- **Exploração e preparação**: no próprio BigQuery, com notebooks integrados, misturando Python e SQL.
- **Treino customizado**: modelos em TensorFlow ou PyTorch rodando em infraestrutura gerenciada, que provisiona o compute sozinha e **lê os dados direto do BigQuery**, sem extração manual.
- **Registro e deploy**: o **Model Registry** centraliza e versiona os modelos, e o deploy num *endpoint* expõe uma API REST que o site da Cymbal chama para recomendações em tempo real.
- **MLOps e monitoramento**: pipelines retreinam o modelo conforme chegam novos dados de compra, e o monitoramento detecta **prediction drift** para evitar que a performance degrade com o tempo.

**Resumindo:** BigQuery ML para casos simples e acessíveis a analistas; Agent Platform para modelos customizados e MLOps completo. Nos dois casos, **os dados não saem do lakehouse**.

### Arquiteturas de lakehouse na prática e estratégias de migração

Depois de ver governança, segurança, analytics e ML, a última lição do módulo junta tudo: **como organizar um lakehouse** e **como sair de uma arquitetura tradicional para ele**.

#### Arquitetura medalhão

O padrão mais comum organiza os dados em **três zonas**, em que cada uma aumenta o nível de refinamento:

| Zona | O que é | Onde fica | Exemplos na Cymbal |
|---|---|---|---|
| **Bronze** (bruto) | Porta de entrada de tudo que chega, **imutável**: o registro histórico do que foi recebido | Cloud Storage | Clickstream via Pub/Sub, exports em CSV/Avro do banco transacional, JSON de campanhas em redes sociais |
| **Silver** (limpo e padronizado) | Dados limpos, validados e enriquecidos, onde acontecem as primeiras transformações | Cloud Storage, em formato aberto (Parquet, Iceberg) consultável via Lakehouse | Clickstream virando sessões estruturadas, transações unidas às dimensões de cliente, datas padronizadas |
| **Gold** (curado para o negócio) | Dados agregados e otimizados para análise: **a fonte única da verdade** das métricas | Quase sempre tabelas **nativas do BigQuery**, pela performance | Vendas diárias agregadas, visão 360° do cliente, desempenho de estoque |

Repare como a arquitetura aproveita o melhor de cada storage: **o lake barato e aberto para os dados brutos e intermediários, e o storage nativo do BigQuery para os dados "quentes"** consumidos por dashboards (a mesma distinção vista na [parte 2]({{< relref "gcp-lakehouse-parte-2.md" >}})).

#### Estratégia de migração: por fases, guiada por caso de uso

Para uma empresa rodando um warehouse on-premises (Teradata, Hadoop), migrar tudo de uma vez é **arriscado e disruptivo demais**. O que costuma funcionar é uma abordagem **incremental, um caso de uso por vez**:

1. **Montar a fundação**: projeto, IAM, rede, buckets das zonas e o Knowledge Catalog para governança desde o início.
2. **Escolher um caso de uso de alto impacto**: por exemplo, **analytics de marketing**, que ganha muito ao combinar dados estruturados e não estruturados.
3. **Migrar só os dados necessários**: histórico via **BigQuery Data Transfer Service** e dados novos em tempo real via pipelines (ex.: **Dataflow**) para a zona Bronze.
4. **Construir os novos pipelines e relatórios**: popular Silver e Gold e apontar os dashboards (ex.: **Looker**) para as tabelas Gold.
5. **Desligar o legado e repetir**: com a solução validada pelo negócio, os relatórios antigos são desativados. Isso **demonstra valor e gera tração** para o próximo caso de uso (supply chain, financeiro...).

A lógica é **reduzir risco e provar valor cedo**, em vez de apostar tudo num "big bang".

#### Gestão de custos

O modelo *pay-as-you-go* da nuvem exige cuidado ativo com custos. As boas práticas:

- **Classe de storage certa**: dados pouco acessados (como a zona Bronze) podem ir para classes mais baratas do Cloud Storage, como **Nearline** ou **Coldline**.
- **Queries eficientes**: treinar analistas em SQL eficiente, **estimar o custo antes de rodar** (o BigQuery mostra quantos bytes a query vai ler) e usar **particionamento e clustering** para ler menos dados.
- **Modelo de cobrança adequado**: para workloads previsíveis, trocar o *on-demand* (paga por byte lido) por **capacidade reservada** (slots dedicados a custo fixo). O curso chama isso de *flat-rate*; hoje esse modelo foi substituído pelas **BigQuery Editions**, mas o conceito é o mesmo.
- **Orçamentos e alertas**: budgets por projeto no console de billing, com alertas quando o gasto se aproxima do limite.

## Conclusão

O fio condutor do curso é que **não é preciso escolher entre data lake e data warehouse**. No Google Cloud, o lakehouse junta os dois:

- **Cloud Storage** como fundação barata e aberta, com **Apache Iceberg** trazendo estrutura, transações e time travel;
- **BigQuery** como motor único (Dremel + Colossus), consultando storage nativo, o lake via **Lakehouse** e bancos operacionais como o **AlloyDB** via federated queries;
- **Governança centralizada** com Knowledge Catalog, Sensitive Data Protection, IAM e segurança por linha e coluna;
- **Analytics e ML sem mover dados**, do BigQuery ML ao Agent Platform;
- **Arquitetura medalhão** e **migração por fases** como caminho prático para chegar lá.

Tudo isso sobre **uma única cópia dos dados**, governada e acessível para BI, ciência de dados e IA.
