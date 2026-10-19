---
title: "Cheatsheet Spark para notebooks Databricks"
author: "vapb"
description: "Guia de consulta rápida de PySpark e Spark SQL para quem está começando com notebooks no Databricks: display, leitura e escrita, seleção, filtros, joins, agregações, window functions, Delta e dicas do notebook."
date: 2026-10-17
tags: ["databricks", "spark", "pyspark", "cheatsheet"]
toc: true
---

## Introdução

Referência rápida para quem está começando com **notebooks no Databricks**. Os exemplos usam **PySpark** e **Spark SQL**. No Databricks a `spark` (SparkSession) já vem criada, então não é preciso instanciar nada.

```python
from pyspark.sql import functions as F
from pyspark.sql import Window
from pyspark.sql.types import *
```

> **Nota:** os nomes de catálogo, schema e tabela abaixo (`main.vendas.pedidos`) são só exemplos.

## Conceitos em um minuto

- **DataFrame**: tabela distribuída com schema, imutável. Cada transformação devolve um novo DataFrame.
- **Transformações são lazy**: `select`, `filter`, `join` só montam o plano. Nada executa até uma **ação**.
- **Ações** disparam a execução: `display`, `show`, `count`, `collect`, `write`.
- **Unity Catalog**: tabelas são referenciadas como `catalogo.schema.tabela`.

## Ver o resultado: display e amigos

| Comando | O que faz |
|---|---|
| `display(df)` | Tabela interativa do Databricks, com ordenação, filtro e botão para virar gráfico |
| `df.show(20, truncate=False)` | Imprime como texto, sem truncar colunas |
| `df.printSchema()` | Mostra colunas e tipos |
| `df.columns` / `df.dtypes` | Lista de colunas / tipos |
| `df.count()` | Número de linhas (dispara um job) |
| `df.describe().show()` | Estatísticas básicas |
| `display(df.summary())` | Estatísticas com percentis |
| `df.limit(10)` | Pega só 10 linhas, útil para inspecionar sem custo |

```python
df = spark.table("main.vendas.pedidos")
display(df)                  # tabela interativa
display(df.limit(100))       # mais leve em tabelas grandes
df.printSchema()
```

O `display` também aceita DataFrames com resultado de agregação, e no resultado dá para clicar em **+ → Visualization** e montar um gráfico sem escrever código.

`displayHTML("<h2>Título</h2>")` renderiza HTML no notebook.

## Criar DataFrames

```python
# A partir de uma lista
df = spark.createDataFrame(
    [(1, "Ana", 30), (2, "Bruno", 25)],
    ["id", "nome", "idade"],
)

# Com schema explícito
schema = StructType([
    StructField("id", IntegerType(), False),
    StructField("nome", StringType(), True),
])
df = spark.createDataFrame([(1, "Ana")], schema)

# De uma tabela
df = spark.table("main.vendas.pedidos")

# De uma query SQL
df = spark.sql("SELECT * FROM main.vendas.pedidos WHERE valor > 100")

# Intervalo de números (bom para testes)
df = spark.range(1000)
```

## Ler arquivos

```python
# CSV
df = (spark.read
      .option("header", True)
      .option("inferSchema", True)   # em produção, prefira schema explícito
      .csv("/Volumes/main/bronze/raw/clientes.csv"))

# JSON
df = spark.read.json("/Volumes/main/bronze/raw/eventos/")

# Parquet
df = spark.read.parquet("/Volumes/main/bronze/raw/pedidos/")

# Delta (por caminho)
df = spark.read.format("delta").load("/Volumes/main/silver/pedidos")
```

Em arquivos novos no Unity Catalog, o caminho costuma ser um **Volume**: `/Volumes/<catalogo>/<schema>/<volume>/...`.

## Selecionar e criar colunas

```python
df.select("id", "nome")
df.select(F.col("valor") * 1.1)
df.selectExpr("id", "valor * 1.1 AS valor_com_taxa")

# Criar / sobrescrever coluna
df = df.withColumn("valor_com_taxa", F.col("valor") * 1.1)

# Renomear
df = df.withColumnRenamed("valor", "valor_bruto")

# Remover
df = df.drop("coluna_inutil")

# Cast de tipo
df = df.withColumn("data", F.col("data").cast("date"))

# Valor fixo
df = df.withColumn("origem", F.lit("sistema_a"))

# Condicional (CASE WHEN)
df = df.withColumn(
    "faixa",
    F.when(F.col("valor") >= 1000, "alto")
     .when(F.col("valor") >= 100, "medio")
     .otherwise("baixo"),
)
```

## Filtrar e ordenar

```python
df.filter(F.col("valor") > 100)
df.where("valor > 100 AND status = 'pago'")      # string SQL também funciona

df.filter((F.col("status") == "pago") | (F.col("status") == "enviado"))
df.filter(F.col("status").isin("pago", "enviado"))
df.filter(F.col("nome").like("A%"))
df.filter(F.col("email").isNotNull())

df.orderBy(F.col("valor").desc())
df.orderBy("categoria", F.col("valor").desc())

df.distinct()
df.dropDuplicates(["id"])
```

> Em PySpark use `&`, `|`, `~` e **sempre com parênteses** em cada condição. `and`, `or`, `not` do Python não funcionam em colunas.

## Nulos

```python
df.dropna()                         # remove linhas com qualquer nulo
df.dropna(subset=["id"])            # só considera a coluna id
df.fillna({"valor": 0, "nome": "n/d"})
df.withColumn("v", F.coalesce("valor", F.lit(0)))
```

## Agregações

```python
df.groupBy("categoria").agg(
    F.count("*").alias("qtd"),
    F.sum("valor").alias("total"),
    F.avg("valor").alias("media"),
    F.min("valor").alias("minimo"),
    F.max("valor").alias("maximo"),
    F.countDistinct("cliente_id").alias("clientes"),
)

# Agregação global (sem groupBy)
df.agg(F.sum("valor"), F.count("*"))

# Pivot
df.groupBy("ano").pivot("categoria").sum("valor")
```

## Joins

```python
pedidos.join(clientes, on="cliente_id", how="inner")
pedidos.join(clientes, pedidos.cliente_id == clientes.id, "left")
```

| `how` | Resultado |
|---|---|
| `inner` | Só o que casa nos dois lados |
| `left` / `right` | Todas as linhas de um lado, nulos onde não casa |
| `outer` | Todas as linhas dos dois lados |
| `left_semi` | Linhas da esquerda que têm correspondência (sem trazer colunas da direita) |
| `left_anti` | Linhas da esquerda que **não** têm correspondência |
| `cross` | Produto cartesiano |

```python
# Tabela pequena? Faça broadcast para evitar shuffle
from pyspark.sql.functions import broadcast
pedidos.join(broadcast(paises), "pais_id")

# União de DataFrames com as mesmas colunas
a.unionByName(b)
```

## Datas e strings

```python
# Datas
F.current_date(), F.current_timestamp()
F.to_date("data_str", "dd/MM/yyyy")
F.to_timestamp("ts_str")
F.date_format("data", "yyyy-MM")
F.year("data"), F.month("data"), F.dayofweek("data")
F.date_add("data", 7), F.datediff("fim", "inicio")
F.date_trunc("month", "data")

# Strings
F.upper("nome"), F.lower("nome"), F.trim("nome")
F.concat_ws(" ", "nome", "sobrenome")
F.substring("cpf", 1, 3)
F.regexp_replace("tel", "[^0-9]", "")
F.split("tags", ",")
F.length("nome")
```

## Window functions

```python
w = Window.partitionBy("cliente_id").orderBy(F.col("data").desc())

df = (df
      .withColumn("rn", F.row_number().over(w))
      .withColumn("pedido_anterior", F.lag("valor", 1).over(w))
      .withColumn("acumulado", F.sum("valor").over(
          Window.partitionBy("cliente_id").orderBy("data")
                .rowsBetween(Window.unboundedPreceding, Window.currentRow))))

# Padrão clássico: ficar com o registro mais recente de cada cliente
ultimos = df.withColumn("rn", F.row_number().over(w)).filter("rn = 1").drop("rn")
```

## Arrays, structs e JSON

```python
F.explode("itens")                      # uma linha por elemento do array
F.col("endereco.cidade")                # acessar campo de struct
F.col("itens")[0]                       # primeiro elemento
F.size("itens")
F.array_contains("tags", "promo")
F.from_json("payload", schema)          # string JSON -> struct
F.to_json(F.struct("id", "nome"))       # struct -> string JSON
F.get_json_object("payload", "$.user.id")
```

## Escrever dados

```python
# Tabela Delta gerenciada (padrão no Databricks)
df.write.mode("overwrite").saveAsTable("main.silver.pedidos")

# Modos: append | overwrite | ignore | errorifexists
df.write.mode("append").saveAsTable("main.silver.pedidos")

# Particionando
df.write.partitionBy("ano").mode("overwrite").saveAsTable("main.silver.pedidos")

# Em arquivo (Volume)
df.write.mode("overwrite").parquet("/Volumes/main/gold/export/pedidos")

# View temporária para usar em SQL no mesmo notebook
df.createOrReplaceTempView("pedidos_tmp")
```

## Delta Lake

```python
from delta.tables import DeltaTable

# MERGE (upsert)
destino = DeltaTable.forName(spark, "main.silver.clientes")
(destino.alias("t")
 .merge(novos.alias("s"), "t.id = s.id")
 .whenMatchedUpdateAll()
 .whenNotMatchedInsertAll()
 .execute())
```

```sql
-- Histórico de alterações
DESCRIBE HISTORY main.silver.clientes;

-- Time travel
SELECT * FROM main.silver.clientes VERSION AS OF 3;
SELECT * FROM main.silver.clientes TIMESTAMP AS OF '2026-10-01';

-- Voltar a tabela para uma versão antiga
RESTORE TABLE main.silver.clientes TO VERSION AS OF 3;

-- Manutenção
OPTIMIZE main.silver.clientes;
VACUUM main.silver.clientes;
```

## Spark SQL no notebook

Cada célula pode usar uma linguagem diferente com **magic commands**:

| Magic | Uso |
|---|---|
| `%python` | Célula Python |
| `%sql` | Célula SQL (o resultado já aparece como `display`) |
| `%scala` | Célula Scala |
| `%md` | Texto em Markdown |
| `%sh` | Comandos de shell no driver |
| `%run ./outro_notebook` | Executa outro notebook e traz suas definições |

```sql
%sql
SELECT categoria, SUM(valor) AS total
FROM main.vendas.pedidos
GROUP BY categoria
ORDER BY total DESC
```

Misturando as duas:

```python
df = spark.sql("SELECT * FROM main.vendas.pedidos")      # SQL -> DataFrame
df.createOrReplaceTempView("p")
display(spark.sql("SELECT COUNT(*) FROM p"))             # DataFrame -> SQL
```

Em células `%sql`, o resultado da última query fica disponível em Python como `_sqldf`.

## Utilitários do Databricks (dbutils)

```python
dbutils.fs.ls("/Volumes/main/bronze/raw/")       # listar arquivos
dbutils.fs.head("/Volumes/main/bronze/raw/a.csv")  # espiar começo do arquivo
dbutils.fs.cp(origem, destino)
dbutils.fs.rm(caminho, recurse=True)

# Widgets: parâmetros do notebook
dbutils.widgets.text("data_ref", "2026-10-01")
data_ref = dbutils.widgets.get("data_ref")

# Segredos (nunca deixe senha no código)
senha = dbutils.secrets.get(scope="meu-scope", key="db-senha")

# Chamar outro notebook
dbutils.notebook.run("./outro", timeout_seconds=600, arguments={"data_ref": "2026-10-01"})

dbutils.help()   # lista os módulos
```

## Boas práticas e armadilhas

- **Evite `collect()` e `toPandas()` em dados grandes**: trazem tudo para a memória do driver. Use `limit` antes, ou `display`.
- **Prefira funções nativas (`F.*`) a UDFs Python**: UDFs são bem mais lentas, pois saem do otimizador do Spark.
- **Schema explícito em produção**: `inferSchema` lê o arquivo duas vezes e pode errar tipos.
- **Use `cache()` com parcimônia**: só vale se o mesmo DataFrame é reutilizado várias vezes.
- **`count()` dispara um job completo**: não use só para "ver se funcionou".
- **Veja o plano**: `df.explain()` mostra como o Spark vai executar, útil para entender joins e shuffles.
- **Shuffle é o custo principal**: `join`, `groupBy`, `distinct` e `orderBy` movem dados entre nós. Filtre e selecione colunas **antes** deles.
- **Cuidado com `overwrite` em tabelas compartilhadas**: confira o destino antes de rodar.

## Referências

- [Documentação PySpark (SQL / DataFrame)](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/index.html)
- [Referência de funções do Spark SQL](https://spark.apache.org/docs/latest/api/sql/index.html)
- [Notebooks no Databricks](https://docs.databricks.com/aws/en/notebooks/)
