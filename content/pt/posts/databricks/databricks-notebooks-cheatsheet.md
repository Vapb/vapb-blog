---
title: "Cheatsheet de notebooks Databricks: magic commands, Unity Catalog e Volumes"
author: "vapb"
description: "Guia de consulta rápida para quem está começando com notebooks no Databricks: magic commands, navegação no Unity Catalog, leitura de arquivos em Volumes com SQL e read_files, atalhos e como alternar entre SQL e Python."
date: 2026-10-17
tags: ["databricks", "notebooks", "unity-catalog", "cheatsheet"]
toc: true
---

## Introdução

Referência rápida para os primeiros passos com **notebooks no Databricks**: como misturar linguagens, navegar no **Unity Catalog**, ler arquivos que estão em **Volumes** e passar dados entre SQL e Python. Para operações de DataFrame (filtros, joins, window functions, Delta), veja o [Cheatsheet Spark para notebooks Databricks]({{< relref "/posts/databricks/databricks-spark-cheatsheet.md" >}}).

## Magic commands

Uma célula começa com um *magic* para trocar a linguagem ou o comportamento daquela célula.

| Comando | Para quê |
|---|---|
| `%sql` | Roda SQL |
| `%python` | Roda Python (padrão em notebook Python) |
| `%scala`, `%r` | Outras linguagens |
| `%md` | Markdown, para documentar o notebook |
| `%sh` | Shell no nó driver |
| `%pip install pacote` | Instala biblioteca na sessão do notebook |
| `%run ./outro_notebook` | Executa outro notebook e traz suas variáveis |
| `%fs ls /caminho` | Atalho para `dbutils.fs` |

## Navegar no Unity Catalog

A hierarquia é `catalog.schema.tabela`. Arquivos ficam em `/Volumes/catalog/schema/volume/...`.

```sql
SHOW CATALOGS;
SHOW SCHEMAS IN samples;
SHOW TABLES IN samples.nyctaxi;
SHOW VOLUMES IN samples.databricks;

DESCRIBE TABLE samples.nyctaxi.trips;
DESCRIBE EXTENDED samples.nyctaxi.trips;   -- local, formato, owner

USE CATALOG samples;
USE SCHEMA nyctaxi;
SELECT current_catalog(), current_schema();
```

Quando aparece "table not found", quase sempre falta o prefixo `catalog.schema.` ou o `USE` correto.

## Arquivos em Volumes

**Volumes** guardam arquivos brutos (CSV, JSON, Parquet, imagens...) sob governança do Unity Catalog. Tabelas, por outro lado, têm schema, histórico e permissões. O fluxo comum é ler o arquivo do volume e gravar o resultado numa tabela.

### Listar e espiar

```sql
LIST '/Volumes/samples/databricks/datasets/airlines';
```

```python
dbutils.fs.ls("/Volumes/samples/databricks/datasets/airlines")
dbutils.fs.head("/Volumes/.../arquivo.csv", 500)   # primeiros bytes
```

### Consultar o arquivo direto

A sintaxe é `formato.`caminho``, com crase no caminho:

```sql
SELECT * FROM csv.`/Volumes/samples/databricks/datasets/airlines/*`;
SELECT * FROM json.`/Volumes/.../pasta/`;
SELECT * FROM parquet.`/Volumes/.../pasta/`;
```

Esse formato usa as **opções padrão**: em CSV isso significa sem header, tudo como string e colunas chamadas `_c0`, `_c1`... É ótimo para espiar, mas não para uso real.

### Controlar a leitura com `read_files`

```sql
SELECT *
FROM read_files(
  '/Volumes/samples/databricks/datasets/airlines/',
  format => 'csv',
  header => true,
  inferSchema => true
);
```

O equivalente em Python:

```python
df = (spark.read
      .format("csv")
      .option("header", True)
      .option("inferSchema", True)
      .load("/Volumes/samples/databricks/datasets/airlines/"))

display(df)
df.printSchema()
```

### Do arquivo para a tabela

```sql
CREATE OR REPLACE TABLE meu_catalog.meu_schema.voos AS
SELECT * FROM read_files('/Volumes/...', format => 'csv', header => true);
```

```python
df.write.mode("overwrite").saveAsTable("meu_catalog.meu_schema.voos")
```

## Alternar entre SQL e Python

Uma view temporária faz a ponte entre as duas linguagens:

```python
df.createOrReplaceTempView("voos_tmp")   # agora %sql enxerga "voos_tmp"
```

```python
resultado = spark.sql("SELECT origem, count(*) AS qtd FROM voos_tmp GROUP BY origem")
```

O resultado da última célula `%sql` também fica disponível como DataFrame na variável `_sqldf`, na célula seguinte em Python.

## Parâmetros com widgets

```python
dbutils.widgets.text("data", "2024-01-01")
data = dbutils.widgets.get("data")
```

```sql
SELECT * FROM voos WHERE dia = :data;
```

Os widgets aparecem no topo do notebook e viram parâmetros quando ele roda como job.

## Atalhos úteis

| Atalho | Ação |
|---|---|
| `Shift + Enter` | Roda a célula e avança |
| `Ctrl + Enter` | Roda e permanece na célula |
| `Esc`, depois `A` / `B` | Nova célula acima / abaixo |
| `Esc`, depois `D D` | Apaga a célula |
| `Ctrl + /` | Comenta a linha |
| `Ctrl + Alt + P` | Abre o Databricks Assistant |

## Três ideias para guardar

1. **Spark é lazy.** `filter`, `select` e `join` só descrevem o plano; nada executa até uma *ação* (`display`, `show`, `count`, `write`).
2. **Arquivo não é tabela.** Volume guarda arquivo bruto; tabela Delta tem schema, histórico e permissões.
3. **Nome de três níveis.** `catalog.schema.tabela` evita boa parte dos erros de "não encontrado".

## Para praticar

Usando o dataset `airlines` dos exemplos acima:

1. Rodar `LIST` e `SELECT` direto no volume.
2. Refazer a leitura com `read_files` e `header => true`.
3. Salvar o resultado como tabela no seu próprio schema.
4. Fazer um `GROUP BY` (por exemplo, voos por origem) e usar o botão de gráfico do `display`.
5. Repetir o fluxo em Python com `spark.read`.

## Referências

- [Documentação do Databricks: notebooks](https://docs.databricks.com/aws/en/notebooks/)
- [Documentação do Databricks: função `read_files`](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files)
- [Documentação do Databricks: Unity Catalog Volumes](https://docs.databricks.com/aws/en/volumes/)
