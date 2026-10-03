---
title: "BigQuery: modelo mental, custo, acesso e carga de dados"
author: "vapb"
description: "O essencial do BigQuery: a hierarquia projeto > dataset > tabela, formas de acesso (console, bq, API), custo por bytes lidos, carga de dados e quando usar BigQuery ou Cloud SQL."
date: 2026-10-02
tags: ["gcp", "bigquery", "cloud-sql"]
toc: true
---

## BigQuery: o modelo mental

**BigQuery** é o **data warehouse serverless** do Google Cloud. Você não provisiona nem gerencia servidores: carrega os dados, escreve SQL, e o Google distribui o processamento na infraestrutura dele. Ele aguenta escala de petabytes.

### Projeto > dataset > tabela

Tudo no BigQuery segue essa hierarquia:

- **Projeto**: o projeto do Google Cloud. É nele que ficam a **cobrança** e as permissões.
- **Dataset**: um agrupador de tabelas e views. É a unidade principal de **controle de acesso** e é onde se define a **região** dos dados. Uma tabela não existe fora de um dataset.
- **Tabela** (ou view): onde os dados de fato estão.

O nome completo de uma tabela segue essa hierarquia:

```sql
SELECT * FROM `bigquery-public-data.london_bicycles.cycle_hire`;
--             projeto              .dataset       .tabela
```

Se a tabela está no seu próprio projeto, dá para omitir o projeto (`babynames.names_2014`). As crases são necessárias quando o nome tem caracteres como `-`.

### Datasets públicos

O projeto `bigquery-public-data` tem centenas de datasets públicos (bike sharing de Londres, natalidade nos EUA, obras de Shakespeare...). Um ponto importante:

- "Fixar" (*star*) esse projeto no console **não troca seu projeto**. Você só passa a enxergar os dados dele.
- A **query roda e é cobrada no seu projeto**. O dado é de outro, o processamento é seu.

Isso mostra uma ideia central do BigQuery: **armazenamento e processamento são separados**. Dá para consultar dados de outro projeto (com permissão) sem copiar nada.

### Custo: você paga pelos bytes lidos

No modelo **on-demand**, o BigQuery cobra pela **quantidade de dados lidos** pela query, não pelo tempo nem pelo número de linhas devolvidas. Como o armazenamento é **colunar**, isso traz algumas consequências práticas:

- **`SELECT *` é caro**: lê todas as colunas. Selecionar só o que precisa reduz o custo direto.
- **`LIMIT` não economiza**: a tabela é lida inteira do mesmo jeito; o `LIMIT` só corta o resultado. (Em tabelas *clustered* isso pode mudar um pouco, mas não conte com isso.)
- **`WHERE` comum também não**, a não ser que a tabela seja **particionada** ou **clusterizada** pela coluna filtrada.
- O **validador** do editor (o check verde) mostra **quantos bytes a query vai processar** antes de rodar. É a forma mais simples de estimar o custo. Na CLI, o equivalente é `bq query --dry_run`.

### GoogleSQL vs. legacy SQL

O BigQuery tem dois dialetos:

| | **GoogleSQL** (antigo "standard SQL") | **Legacy SQL** |
| --- | --- | --- |
| Status | padrão atual, compatível com ANSI | antigo, mantido por compatibilidade |
| Referência de tabela | `` `projeto.dataset.tabela` `` | `[projeto:dataset.tabela]` |

> **Atenção:** o console já usa GoogleSQL por padrão, então o prefixo `#standardSQL` que aparece em exemplos antigos é desnecessário. Já a CLI `bq query` **ainda usa legacy SQL por padrão**, por isso a flag `--use_legacy_sql=false` aparece em todo exemplo. Dá para torná-la padrão no arquivo `~/.bigqueryrc`.

## Formas de acessar o BigQuery

| Interface | Quando faz sentido |
| --- | --- |
| **Console (web UI)** | explorar dados, testar queries, ver schema e preview |
| **`bq` (CLI)** | scripts, automação, Cloud Shell; vem instalado no Cloud SDK |
| **REST API / client libraries** | integrar com aplicações (Python, Java, .NET, Go...) |
| **Ferramentas de terceiros** | BI, visualização, ETL |

Os comandos de `bq` seguem o padrão `bq <ação> <recurso>`:

| Comando | O que faz |
| --- | --- |
| `bq show projeto:dataset.tabela` | mostra schema, número de linhas e tamanho |
| `bq ls` / `bq ls projeto:` / `bq ls dataset` | lista datasets do seu projeto, de outro projeto, ou tabelas de um dataset |
| `bq mk dataset` | cria um dataset |
| `bq load dataset.tabela arquivo schema` | cria (ou atualiza) a tabela **e** carrega os dados em um passo só |
| `bq query --use_legacy_sql=false '...'` | roda uma query |
| `bq rm -r dataset` | apaga o dataset; o `-r` apaga as tabelas dentro dele junto |
| `bq help <comando>` | ajuda de um comando |

> **Notação:** na CLI, a separação entre projeto e dataset usa **dois-pontos** (`bigquery-public-data:samples.shakespeare`), herança da notação legacy. Dentro de uma query GoogleSQL, é **ponto**.

Ao passar SQL na linha de comando, cuidado com **aspas**: use aspas simples por fora e duplas por dentro (ou o contrário), ou escape com `\`.

## Colocando dados no BigQuery

Para ter uma tabela própria, a sequência é sempre **criar o dataset → criar a tabela carregando um arquivo**.

- **Origem do arquivo:** upload local, **Cloud Storage** (o mais comum), ou outras fontes como Drive.
- **Formatos:** CSV, JSON (newline-delimited), Avro, Parquet, ORC.
- **Schema:** pode ser definido explicitamente em texto (`name:string,gender:string,count:integer`) ou **detectado automaticamente** (*auto-detect*). Formatos autodescritivos como Avro e Parquet já trazem o schema no arquivo.
- **Encoding:** o BigQuery espera **UTF-8**. Arquivos em Latin-1 (ISO-8859-1) precisam ser sinalizados (flag `-E` no `bq load`), senão os acentos quebram.

Depois de carregada, uma tabela própria é consultada exatamente como uma pública. O que muda é só o nome.

## Cloud SQL e quando usar cada um

**Cloud SQL** é o serviço **gerenciado** de bancos relacionais do Google Cloud: **MySQL, PostgreSQL e SQL Server**. O Google cuida de backup, patches, replicação e failover. Você ainda escolhe o tamanho da instância (vCPU, memória, disco) e a disponibilidade (uma zona ou alta disponibilidade com réplica em outra zona).

### BigQuery vs. Cloud SQL

Os dois "falam SQL", mas resolvem problemas diferentes:

| | **BigQuery** | **Cloud SQL** |
| --- | --- | --- |
| Tipo | data warehouse (**OLAP**) | banco relacional (**OLTP**) |
| Carga típica | poucas queries que leem **muitas linhas** (agregações, relatórios) | muitas operações pequenas: ler/gravar **poucas linhas** por vez |
| Escala | petabytes | até dezenas de TB por instância |
| Infraestrutura | serverless | você escolhe e paga a instância |
| Cobrança | bytes lidos (ou slots) + armazenamento | instância ligada + disco |
| Armazenamento | colunar | por linha |
| Uso típico | analytics, BI, ML | backend de aplicação, transações |

Uma regra prática: se a pergunta é "**qual o total / média / ranking** sobre milhões de registros?", é BigQuery. Se é "**grava este pedido** / busca o cliente 123", é Cloud SQL.

### Movendo dados entre os dois

Não existe uma "seta direta" do BigQuery para o Cloud SQL. O caminho padrão passa pelo **Cloud Storage como área intermediária**:

1. Exportar o resultado do BigQuery (CSV, JSON, Avro ou Parquet) para um bucket.
2. Importar no Cloud SQL a partir do bucket.

O **import do Cloud SQL** aceita dois formatos:

- **SQL dump** (`.sql`): o script com `CREATE`/`INSERT`, gerado por `mysqldump` ou `pg_dump`. Recria estrutura e dados.
- **CSV**: só dados. A **tabela de destino precisa existir antes**, com as colunas na mesma ordem do arquivo.

> **Cuidado com o cabeçalho do CSV:** exports normalmente incluem uma linha de cabeçalho, e o import do Cloud SQL pode carregá-la como se fosse dado. No MySQL, o texto `"num"` numa coluna `INT` acaba virando `0`, criando uma linha falsa. O ideal é exportar sem cabeçalho ou limpar logo depois do import.

Para conectar de forma rápida a uma instância, `gcloud sql connect <instância> --user=root` abre um cliente MySQL/psql já autorizado, sem precisar liberar IP manualmente.

## Resumo

- No BigQuery tudo é **projeto > dataset > tabela**; o dataset define acesso e região.
- O BigQuery cobra por **bytes lidos**: evite `SELECT *`, e lembre que `LIMIT` não reduz custo. Veja a estimativa antes de rodar.
- Use **GoogleSQL**; na CLI, lembre do `--use_legacy_sql=false`.
- **BigQuery = analytics (OLAP)**, **Cloud SQL = transações (OLTP)**. Dados circulam entre eles via **Cloud Storage**.
