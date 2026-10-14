---
title: "Data Quality Fundamentals - Capítulo 2"
author: "vapb"
description: "Resumo do capítulo 2 de Data Quality Fundamentals: dados operacionais vs. analíticos, data warehouses, data lakes, lakehouses, métricas de qualidade de dados e catálogo de dados."
date: 2026-08-22
tags: ["data-quality-fundamentals"]
toc: false
---

## Introdução

O Capítulo 2, "Assembling the Building Blocks of a Reliable Data System", é escrito em conjunto com Ryan Kearns. Resolver qualidade de dados e construir pipelines mais confiáveis se resume a três componentes: **processo**, **tecnologia** e **pessoas** (o assunto do Capítulo 8). **Este capítulo cobre só o componente de tecnologia: as peças do pipeline de dados e o que é preciso para medir, corrigir e prevenir *data downtime* em cada etapa.**

## Dados operacionais vs. analíticos

Uma das distinções mais fundamentais num time de dados é entre **dados operacionais** e **dados analíticos**. O foco do livro é qualidade de dados analíticos, já que dados operacionais costumam ser responsabilidade de DevOps e SRE.

| | Dados operacionais | Dados analíticos |
|---|---|---|
| Definição | Produzidos pela operação do dia a dia da empresa | Usados para decisões de negócio orientadas a dados |
| Exemplos | Snapshot de estoque, impressão de cliente, registro de transação | Churn de marketing, taxa de cliques, impressões por região |
| Papel | *Roda* o negócio | *Gerencia* o negócio |
| Posição no pipeline | Upstream: normalmente a fonte bruta | Downstream: resultado de agregações e transformações sobre o dado operacional |
| Otimizado para | Baixa latência | Alto throughput |

Um exemplo concreto amarra a relação entre os dois: a taxa de cliques de um usuário específico, na sessão dele às 5h da manhã, é um dado operacional; a taxa de cliques agregada de toda a campanha de marketing de dezembro é o dado analítico correspondente, construído em cima de milhares de eventos operacionais como esse. **Apesar de parecer que o dado analítico é o mais "importante" por informar decisões de negócio, ele quase sempre depende dessa base operacional por trás.** É a mesma distinção feita entre OLTP e OLAP (processamento transacional vs. analítico), também usada em *Designing Data-Intensive Applications* (O'Reilly).

### O trade-off entre throughput e latência

Uma analogia explica por que bancos operacionais e analíticos são otimizados de formas diferentes: uma cafeteria com fila. **Latência** é o tempo entre entrar na fila e receber o café; **throughput** é quantos clientes são atendidos numa hora. Com um número fixo de funcionários, otimizar um sacrifica o outro: colocar todo mundo no caixa reduz a latência mas destrói o throughput (ninguém limpa as mesas), e vice-versa.

Isso acontece porque sistemas de processamento de dados são construídos com um número limitado de *handlers* de requisição e poder computacional fixo: **não dá pra ter throughput alto e latência baixa ao mesmo tempo, é preciso escolher onde alocar os recursos.**

Bancos de dados **operacionais** (transacionais) precisam buscar informação como detalhes de um pedido o mais rápido possível na hora de carregar uma página, então são otimizados para baixa latência. Bancos **analíticos** atendem usuários rodando agregações grandes sobre volumes massivos de dados, então são otimizados para alto throughput. **Por isso não se consulta o Snowflake a partir da UI de um cliente, nem se roda agregações de trilhões de linhas no Postgres.**

## Data Warehouses vs. Data Lakes vs. Lakehouses

**Data warehouse** e **data lake** não são intercambiáveis, mas estão convergindo, cada um incorporando o melhor do outro. **Muitas empresas precisam dos dois dentro do mesmo pipeline, só que para propósitos bem diferentes.**

> **Conceitos gerais:** a explicação completa de cada arquitetura, tecnologias e por que o lakehouse surgiu está em [Data Warehouse, Data Lake e Lakehouse]({{< relref "dw-dl-lakehouse.md" >}}). Abaixo ficam só os pontos do livro sobre **qualidade de dados**.

### Data warehouses: schema-on-write

- Estrutura definida **na entrada**: mais rigidez, mas **melhor higiene de dados** e leitura mais simples.
- Totalmente gerenciado, SQL forte, integração pronta com BI (Looker, Tableau).
- **Desafios para qualidade:** flexibilidade limitada (JSON costuma ficar de fora); só SQL, então o dado de ML sai do warehouse, e é nessa **movimentação** que surgem problemas de volume, atualidade e schema; fluxos engessados.
- Exemplos: Redshift, BigQuery, Snowflake.

### Data lakes: manipulação no nível de arquivo

- *Schema-on-read*: a estrutura só é inferida no uso. É a versão "faça você mesmo" do warehouse (você escolhe metadados, storage e compute).
- **Desafios para qualidade:**
  1. **Integridade de dados**: sem garantia de schema no nível de arquivo. Transformar sem validar é o *"blind ETL"*, que quebra com mudanças upstream.
  2. **Swampification**: dívida técnica e conhecimento tácito acumulados até só uma pessoa saber onde está cada dado. O lago vira *data swamp*.
  3. **Mais endpoints**: mais formas de coletar e transformar, mais chances de erro.
- Exemplos: HDFS, S3, ADLS, Cloud Storage (armazenamento); Hive e Spark (motores).

### E o data lakehouse?

- Dados continuam como arquivos no lake, com uma camada por cima que dá **schema, SQL e transações ACID**: queries analíticas direto sobre o lake, **uma única cópia** para BI e ML.
- **Desafios para qualidade:** categoria ainda em maturação, com tooling de qualidade menos consolidado; e a base **continua sendo um lake**, então os problemas de schema e governança são mitigados, não eliminados.
- Peças: Parquet (schema), Delta Lake e Hudi (ACID), Presto e Spark (SQL), Databricks, Athena e Glue (gerenciados).
- Segundo o livro, com dados em tempo real e streaming (Uber, DoorDash, Airbnb), o lakehouse tende a ganhar espaço.


## Sincronizando dados entre warehouses e lakes

Warehouses e lakes diferentes são conectados por uma **camada de integração de dados**. Ferramentas como AWS Glue, Fivetran e Matillion coletam dados de fontes distintas, unificam e transformam esses dados rumo a uma fonte upstream, um caso clássico sendo coletar dados de um lake e carregá-los, já estruturados, num warehouse.

O processo mais conhecido dentro dessa integração é o **ETL** (*extract-transform-load*): os dados são extraídos de uma ou mais fontes, transformados numa nova estrutura ou formato, e finalmente carregados num destino.

## Métricas de qualidade de dados

Com o mapa do pipeline montado (dados operacionais e analíticos, warehouses, lakes e lakehouses), **a pergunta prática que resta é: quais métricas realmente importam para medir qualidade de dados?**

Não existe qualidade de dados sem **métricas de qualidade de dados**: KPIs ou outros indicadores de que os dados estão saudáveis e confiáveis o suficiente para os stakeholders usarem.

Qualidade de dados é medida em termos de **data downtime**: períodos em que os dados estão parciais, com erro, ausentes ou de alguma forma imprecisos. O termo "downtime" é uma referência aos primórdios da internet, quando aplicações online eram um "bônus" e ficar fora do ar não era grande coisa. Hoje, aplicações online são críticas para praticamente todo negócio, e empresas monitoram uptime com rigor. **Dados deveriam receber o mesmo nível de rigor, algo que a maioria das empresas ainda não pratica: SLAs de dados existem, mas ainda não são a norma.**

### Monitorando métricas em toda a stack

Conforme a stack de dados cresce e incorpora mais tecnologias e fontes, monitorar métricas de qualidade em todos os lugares vira um desafio, já que os dados podem quebrar em qualquer ponto do pipeline. É preciso puxar métricas e metadados não só do warehouse, mas de todos os outros ativos: lakes, ETL, dashboards de BI. **Observabilidade de dados de verdade cobre a stack inteira, não só o warehouse, o que evita que um problema pequeno vire uma bola de neve.**

### Exemplo: coletando métricas de qualidade no Snowflake

O livro usa o Snowflake como exemplo prático (o processo é parecido em Redshift, BigQuery e outros warehouses OLAP), em quatro passos:

| Passo | Fonte no Snowflake | O que responde |
|---|---|---|
| 1. Mapear o inventário | `information_schema.tables`, `information_schema.columns`, `SHOW VIEWS`, `SHOW EXTERNAL TABLES` | Quais tabelas, views e schemas existem, e o que precisa ser monitorado |
| 2. Monitorar *freshness* e volume | Linhas, bytes e data de última atualização por tabela | Se uma tabela parou de atualizar ou fugiu do padrão esperado |
| 3. Construir histórico de queries | `query_history`, `copy_history` | Quem escreveu em cada tabela, quando, e como os dados foram carregados (linhagem e uso) |
| 4. Health check | Métricas por campo: completude, distinção, taxa de zeros, quantis | Se um campo específico tem IDs ausentes, duplicados, ou valores fora do esperado |

Views são mais difíceis de medir dessa forma, já que sua *freshness* depende das tabelas usadas na query.

Essas métricas só são úteis se estiverem acessíveis ao resto do time, com **notificações automáticas** quando algo quebra e uma **interface centralizada** para investigar. Isso é o que separa uma resolução rápida de um incidente de dados que se arrasta por dias.

### Usando query logs para entender qualidade no warehouse

Os **logs de query** são uma fonte de metadados poderosa: **eles respondem quem está acessando um dado, de onde ele vem e para onde vai, com que frequência uma transformação roda, e quantas linhas ela afeta.** Essa informação vem em tabelas de sistema na maioria dos warehouses (a família `QUERY_HISTORY` no Snowflake, os `AuditLogs` no BigQuery, a família `STL_QUERY` no Redshift).

Um detalhe prático: essas tabelas de log costumam guardar só alguns dias de histórico e têm muito mais informação do que o necessário para qualidade de dados, **então vale a pena armazenar as métricas relevantes num lugar mais permanente.** De ready-made, dá pra extrair: o usuário que rodou a query, o texto SQL (e um hash dela), o tempo total de execução, o código de erro (se houve), e o tamanho de entrada/saída. A partir disso é possível responder perguntas como: quando essa tabela foi consultada pela última vez, isso segue um padrão regular ou quebra o padrão, qual a carga do warehouse por horário do dia, essa query está ficando mais lenta com o tempo, e quem (ou qual bot) tem acesso a um recurso que não deveria.

### Usando query logs para entender qualidade no lake

Data lakes são diferentes: como seguem *schema-on-read*, o schema não é imposto na hora da inserção, **o que torna várias métricas típicas de warehouse mais difíceis (ou impossíveis) de obter.**

**Ainda assim, parte dos metadados vem de graça.** Serviços como o Amazon S3 já guardam data de inserção e tamanho de payload por necessidade própria de gestão de objetos, e isso pode ser aproveitado para responder perguntas como "quando esse objeto foi atualizado pela última vez?" ou "o tamanho médio dos arquivos desse tipo está crescendo?". **Metadados de sistema** comuns em data lakes incluem: data de inserção, tamanho em bytes, formato do arquivo (se reconhecido) e se a criptografia está habilitada.

Além disso, é possível definir **metadados customizados** na hora da criação do objeto, como qual pipeline ou usuário criou aquele objeto, ou qual schema ele depende (por exemplo, usando um hash do schema para saber se um recurso está configurado para um determinado fluxo de ETL, ou se ficou obsoleto). **Uma alternativa mais holística para saber quem é responsável por um objeto é simplesmente restringir permissões de escrita a um único pipeline por vez.**

O próximo elemento da stack de dados que entra na discussão de qualidade é o **catálogo de dados**.

## Catálogo de dados

Um **data catalog** é, por analogia, o catálogo de uma biblioteca física: **um inventário de metadados que dá ao time a informação necessária para avaliar acessibilidade, saúde e localização dos dados.** Empresas como Alation, Collibra e Informatica oferecem soluções que, além de rastrear os dados, integram machine learning e automação para tornar os dados mais descobríveis, colaborativos e em conformidade com regulações organizacionais, do setor ou governamentais.

Como funciona como fonte única de verdade sobre as fontes de dados de uma empresa, o catálogo ajuda a entender a linhagem de uma fonte específica (reforçando confiança nos dados), e a rastrear onde **informação pessoal identificável (PII)** está armazenada e para onde ela se espalha no pipeline, além de quem tem permissão de acesso a ela.

Um catálogo de dados é desenhado para responder perguntas como:
1. Onde devo procurar meu dado?
2. Esse dado importa?
3. O que esse dado representa?
4. Esse dado é relevante e importante?
5. Como posso usar esse dado?

### Por que catalogar manualmente não escala

A abordagem mais simples para responder essas perguntas seria reunir tudo numa planilha gigante, e por muito tempo foi assim que cataloging de dados foi resolvido: no Excel. O problema é que warehouses com dezenas de milhares de tabelas tornam a automação inevitável. **Métodos tradicionais de catalogação dependem de entrada manual de dados pelo próprio time, o que consome tempo que poderia ir para projetos de maior impacto.**

Além disso, boa parte dos dados armazenados hoje é não estruturada e muito fluida, o tipo de dado que alimenta pipelines de machine learning e que costuma morar num data lake. É praticamente impossível manter um catálogo manual para esse tipo de dado. Some a isso o fato de que produtor e consumidor de um dado (e até consumidores diferentes entre si) costumam entender o significado desse dado de formas bem diferentes. Ou seja: **catálogo manual não é mais suficiente**.

### Construindo um catálogo de dados

Antes de construir ou investir num catálogo, é preciso alinhar com os times de operações e analytics quais dados são mais importantes para o negócio e, por isso, precisam ser documentados. Depois desse alinhamento, times costumam atribuir **donos** (*owners*) responsáveis por manter cada fonte atualizada, seja por fonte, schema ou domínio de dados.

**No nível mais básico, um catálogo de dados é uma coleção de metadados que dá contexto sobre localização, propriedade e possíveis usos de cada dado.** Na forma mais simples, isso já é um catálogo:

| Tabela | Dashboard/relatório | Última atualização | Dono | Notas |
|---|---|---|---|---|
| `orders_fact` | Forecast Financeiro (Looker) | 2026-03-03 | Time de Finanças | Base para projeções de receita |
| `marketing_leads` | Modelo de Demanda (Looker) | 2026-03-03 | Time de Marketing | Alimenta modelos de geração de demanda |
| `legacy_report_v2` | Dashboard X (Tableau) | 2021-10-30 | — | Dono desconhecido, uso incerto |

Para popular esse catálogo, o time pode vasculhar manualmente cada tabela do warehouse, ou usar **parsers de SQL automatizados** (como Sqlparse, ANTLR, Apache Calcite ou o SQL Parser do MySQL) que separam uma instrução SQL em suas partes (palavras-chave, identificadores, cláusulas) para que outras rotinas processem essa informação.

Uma vez parseado, o SQL precisa de um lugar para ser armazenado e processado. **Bancos open source como o stack ELK, PostgreSQL, MySQL e MariaDB são opções comuns para construir um catálogo do zero.** Ferramentas de query como GraphQL, REST e Cube.js permitem consultar esses dados e renderizá-los em serviços de visualização e descoberta como Amundsen, Apache Atlas, DataHub ou CKAN.

### Os limites do catálogo e a virada para "data discovery"

**Catálogos de dados funcionam bem quando o modelo de dados é rígido**. Conforme pipelines ficam mais complexos e dados não estruturados viram a norma, o entendimento estático de um catálogo (o que o dado faz, quem usa, como é usado) deixa de refletir a realidade. **A próxima geração de catálogos tende a aprender, entender e inferir sobre os dados, com metadados ativos e descoberta automatizada, a ponto de ser possível consultar dados do warehouse por um canal como Slack ou Teams.**

Esse é o papel do **data discovery**: uma abordagem para entender a saúde de ativos de dados distribuídos em tempo real, emprestando conceitos do *data mesh* de Zhamak Dehghani, como donos de domínio responsáveis por seus dados como produto. **Em vez de descrever o estado "ideal" (catalogado) do dado, data discovery expõe o estado atual do dado, baseado em como ele está sendo ingerido, armazenado, agregado e usado.**

Perguntas que o data discovery ajuda a responder, sobre o estado atual (não o ideal) dos dados:
1. Qual conjunto de dados é mais recente? Quais podem ser descontinuados?
2. Quando foi a última atualização dessa tabela?
3. O que um determinado campo significa no meu domínio?
4. Quem tem acesso a esse dado? Quando e por quem foi usado pela última vez?
5. Quais as dependências upstream e downstream desse dado?
6. Esse dado tem qualidade de produção?
7. O que importa para os requisitos de negócio do meu domínio?
8. Quais são minhas suposições sobre esse dado, e elas estão sendo cumpridas?

### Características de um catálogo orientado à qualidade

1. **Descoberta self-service e automação**: o time de dados deve conseguir usar o catálogo sem depender de um time de suporte dedicado, o que reduz silos entre etapas do pipeline e aumenta a adoção dos dados.
2. **Escalabilidade conforme os dados evoluem**: usar machine learning para manter uma visão atualizada dos ativos de dados à medida que crescem, em vez de depender de documentação desatualizada ou decisões no "achismo".
3. **Linhagem de dados para descoberta distribuída**: linhagem automatizada em nível de tabela e campo, mapeando dependências upstream e downstream, o que ajuda a identificar a causa raiz quando um pipeline quebra (assunto do Capítulo 7).

Na prática, todo time de dados já investe em algum tipo de *data discovery*, seja pela verificação manual que fazem, por regras de validação customizadas que escrevem, ou pelo custo de decisões tomadas em cima de dados quebrados ou erros silenciosos. **Times mais maduros automatizam isso com monitoramento de qualidade de dados e plataformas de observabilidade ponta a ponta, que alertam quando os dados quebram para permitir uma resolução rápida da causa raiz.**

## Resumo do capítulo

**Ter dados descobríveis de verdade exige mais do que catalogá-los: eles também precisam ser precisos, limpos e totalmente observáveis, da ingestão ao consumo, ou seja, confiáveis.** Só entendendo os dados, seu estado, e como são usados em cada estágio do ciclo de vida (e entre domínios) é possível confiar neles.