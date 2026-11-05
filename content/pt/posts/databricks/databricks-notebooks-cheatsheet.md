---
title: "Cheatsheet de notebooks Databricks: magic commands e Volumes"
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
| `%run ./outro_notebook` | Executa outro notebook e traz suas variáveis (veja abaixo) |
| `%fs ls /caminho` | Atalho para `dbutils.fs` |

## Reaproveitar código com `%run`

`%run` executa **todas as células** de outro notebook **na mesma sessão** do notebook atual. Não é uma cópia do arquivo: é uma execução real, então funções, variáveis, imports e DataFrames definidos lá ficam disponíveis nas células seguintes.

```python
%run ./Includes/Setup-Common
```

```python
# depois do %run, o que foi definido no outro notebook já existe aqui
print(f"Username: {spark.sql('SELECT current_user()').first()[0]}")
print(f"Catalog:  {my_catalog}")
print(f"Schema:   {my_schema}")
```

- **Caminho relativo:** `./` é relativo à pasta do notebook atual.
- **SQL também compartilha a sessão:** variáveis criadas com `SET VAR my_catalog = ...` no notebook incluído ficam visíveis nas células SQL.
- **Encadeamento:** um notebook de setup pode dar `%run` em outro. Um padrão comum é o `Setup-Common` definir as funções utilitárias, o `Setup-1` rodá-lo e criar catálogo, schema e volume do usuário, e o notebook da aula rodar o `Setup-1` e herdar tudo.

Pontos de atenção:

- **O estado vive no kernel, não no arquivo.** Se reiniciar o kernel ou desanexar o compute, tudo some e é preciso rodar o `%run` de novo. Um `NameError` em `my_catalog` ou numa função do setup quase sempre significa que o `%run` não foi executado nessa sessão.
- **A ordem importa:** a célula com `%run` precisa rodar antes das que usam o que ela define.
- **Para código reutilizável de verdade**, um módulo Python com `import` é a alternativa; para setup de curso ou de ambiente, `%run` é o padrão.

## Navegar no Unity Catalog

A hierarquia é `catalog.schema.tabela`. Arquivos ficam em `/Volumes/catalog/schema/volume/...`.

```sql
SHOW CATALOGS;
SHOW SCHEMAS IN samples;
SHOW TABLES IN samples.nyctaxi;
SHOW VOLUMES IN samples.databricks;

DESCRIBE TABLE samples.nyctaxi.trips;
DESCRIBE EXTENDED samples.nyctaxi.trips;   -- local, formato, owner
```

Quando aparece "table not found", quase sempre falta o prefixo `catalog.schema.` ou o `USE` correto.

## Comandos úteis: onde estou e como mudar

Sempre que o notebook usa um nome sem o caminho completo (`vendas` em vez de `catalogo.schema.vendas`), o Databricks procura no **catálogo e schema de trabalho** da sessão. Por isso vale saber ver e trocar esse contexto.

### Ver onde você está

```sql
SELECT current_catalog(), current_schema();   -- catálogo e schema de trabalho
SELECT current_user();                         -- quem é você
```

```python
print(f"Username: {spark.sql('SELECT current_user()').first()[0]}")
print(f"Catalog:  {spark.sql('SELECT current_catalog()').first()[0]}")
print(f"Schema:   {spark.sql('SELECT current_schema()').first()[0]}")
```

### Mudar o catálogo e o schema de trabalho

```sql
USE CATALOG meu_catalog;
USE SCHEMA meu_schema;

-- ou os dois de uma vez
USE meu_catalog.meu_schema;
```

Depois disso, os nomes curtos funcionam:

```sql
SHOW TABLES;                 -- lista as tabelas do schema atual
SHOW VOLUMES;                -- lista os volumes do schema atual
SELECT * FROM voos;          -- em vez de meu_catalog.meu_schema.voos
```

Em Python, o mesmo efeito vem do `spark.sql` ou do `spark.catalog`:

```python
spark.sql("USE meu_catalog.meu_schema")

spark.catalog.currentCatalog()        # catálogo atual
spark.catalog.currentDatabase()       # schema atual
spark.catalog.setCurrentCatalog("meu_catalog")
spark.catalog.setCurrentDatabase("meu_schema")
```

### Guardar o nome em variável

Para não repetir o nome em todo lugar, dá para parametrizar:

```python
my_catalog = "meu_catalog"
my_schema = "meu_schema"
spark.sql(f"USE {my_catalog}.{my_schema}")
```

```sql
DECLARE OR REPLACE VARIABLE my_catalog STRING DEFAULT 'meu_catalog';
USE CATALOG IDENTIFIER(my_catalog);
```

O `IDENTIFIER(...)` é o que permite usar uma variável (ou widget) onde o SQL espera um nome de objeto.

Pontos de atenção:

- **O `USE` vale só para a sessão.** Ao reiniciar o kernel ou desanexar o compute, o contexto volta ao padrão. Em notebooks que rodam como job, o `USE` precisa estar numa célula.
- **O caminho completo sempre vence.** `catalogo.schema.tabela` ignora o `USE`, então dá para misturar nomes curtos e completos.
- **Volumes não usam o `USE`.** Os caminhos de arquivo continuam sendo `/Volumes/catalogo/schema/volume/...` por inteiro.

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
