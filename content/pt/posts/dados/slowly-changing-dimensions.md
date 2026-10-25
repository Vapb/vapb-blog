---
title: "Slowly Changing Dimensions (SCD) com exemplos no Databricks"
author: "vapb"
description: "O que são Slowly Changing Dimensions na modelagem dimensional, os tipos 1 e 2 com exemplos, e como implementar SCD no Databricks com MERGE INTO no Delta Lake e com AUTO CDC nas Lakeflow Spark Declarative Pipelines."
date: 2026-10-25
tags: ["data-engineering", "data-warehouse", "modelagem-dimensional", "kimball", "scd", "databricks", "delta-lake", "sql"]
toc: true
aliases: ["/posts/slowly-changing-dimensions/"]
---

## Introdução

Dimensões descrevem o contexto dos fatos: quem comprou, qual produto, onde. Esse contexto muda: o cliente se muda de cidade, o produto troca de categoria. Uma **Slowly Changing Dimension (SCD)** é uma dimensão cujos atributos mudam de vez em quando, e a pergunta da modelagem é:

> Quando o atributo muda, as vendas antigas passam a mostrar o valor novo ou continuam mostrando o valor da época?

Kimball catalogou as respostas em **tipos de SCD**. Na prática, quase tudo se resolve com o **tipo 1** e o **tipo 2**, que são os que vamos ver.

## Exemplo

A Ana morava em São Paulo e se mudou para Curitiba em 10/03/2026.

| cliente_id | nome | cidade |
|---:|---|---|
| 1 | Ana | São Paulo |

## Tipo 1: sobrescrever

Atualiza o valor no lugar. **Não guarda histórico.**

| cliente_id | nome | cidade |
|---:|---|---|
| 1 | Ana | **Curitiba** |

- Simples: uma linha por entidade.
- **Reescreve o passado**: as vendas antigas da Ana passam a aparecer como "Curitiba".
- Serve para **correções** (nome com erro de digitação) e para atributos em que o histórico não importa.

## Tipo 2: uma linha por versão

Em vez de sobrescrever, **fecha a linha antiga e abre uma nova**.

| cliente_sk | cliente_id | nome | cidade | início | fim | atual |
|---:|---:|---|---|---|---|---|
| 101 | 1 | Ana | São Paulo | 2025-01-15 | 2026-03-10 | não |
| 205 | 1 | Ana | **Curitiba** | 2026-03-10 | *(nulo)* | sim |

- **Chave natural** (`cliente_id`): vem da origem e se repete entre as versões.
- **Surrogate key** (`cliente_sk`): identifica **uma versão**, e é ela que a fato guarda.
- **Vigência** (`início`/`fim`): período em que a versão era a verdadeira. A atual tem `fim` nulo.
- **Flag `atual`**: atalho para filtrar só a versão vigente.

O ponto-chave: **na carga da fato, a venda recebe a surrogate key da versão vigente na data da venda**. Uma venda de fevereiro aponta para a linha 101 (São Paulo) e uma de abril para a 205 (Curitiba), e o histórico fica correto sem cálculo na consulta.

> Com tipo 2, `COUNT(*)` na dimensão deixa de ser "número de clientes". Use `COUNT(DISTINCT cliente_id)` ou filtre `atual = true`.

## E os outros tipos?

Existem outras estratégias, menos usadas:

- **Tipo 0:** o atributo nunca muda (ex.: data de nascimento).
- **Tipo 3:** uma coluna extra guarda só o valor anterior (`cidade_anterior`).
- **Tipos 4 e 6:** mini-dimensões e híbridos dos anteriores, para casos específicos.

Dá para **misturar tipos na mesma dimensão**, escolhendo um por atributo. Por exemplo: `cidade` tipo 2, `nome` tipo 1. Pergunta-guia: *"se esse valor mudar, a análise do passado deve mudar junto?"* Sim → tipo 1. Não → tipo 2.

Atenção a atributos que mudam **toda hora** (status, saldo): em tipo 2 a dimensão cresce sem parar, e eles provavelmente pertencem a uma fato.

## SCD no Databricks

O Databricks não tem um "tipo de tabela SCD". Existem duas formas de implementar:

| | `MERGE INTO` (Delta Lake) | `AUTO CDC` (Lakeflow Spark Declarative Pipelines) |
|---|---|---|
| Estilo | Você escreve a lógica | Você descreve o resultado |
| Onde roda | Notebook, job ou SQL warehouse | Dentro de um pipeline |
| Dados fora de ordem | Você trata | Resolvido pela coluna de sequência |
| Surrogate key | Pode usar coluna `IDENTITY` | Não gera |

> **Time travel do Delta não substitui SCD tipo 2.** As versões antigas expiram (log com 30 dias por padrão, `VACUUM` remove arquivos). Serve para auditoria e rollback, não para histórico de negócio.

### MERGE: tipo 1

```sql
MERGE INTO main.gold.dim_cliente AS d
USING main.silver.clientes_atualizados AS s
   ON d.cliente_id = s.cliente_id
WHEN MATCHED AND NOT (d.cidade <=> s.cidade) THEN
    UPDATE SET d.nome = s.nome, d.cidade = s.cidade
WHEN NOT MATCHED THEN
    INSERT (cliente_id, nome, cidade) VALUES (s.cliente_id, s.nome, s.cidade);
```

O `<=>` é a comparação **null-safe**: com `<>`, comparar com nulo dá nulo e a mudança passaria despercebida.

### MERGE: tipo 2

Primeiro a tabela, com uma coluna identity como surrogate key:

```sql
CREATE TABLE main.gold.dim_cliente (
    cliente_sk       BIGINT GENERATED ALWAYS AS IDENTITY,
    cliente_id       INT       NOT NULL,
    nome             STRING,
    cidade           STRING,
    inicio_vigencia  TIMESTAMP NOT NULL,
    fim_vigencia     TIMESTAMP,          -- nulo = versão atual
    atual            BOOLEAN   NOT NULL
);
```

Quando algo muda, é preciso **fechar** a versão atual e **inserir** a nova, mas um `MERGE` faz uma ação por linha da origem. O truque é a origem aparecer **duas vezes** para quem mudou:

1. Cópia com `merge_key` = chave natural: **casa** com a versão atual e fecha a vigência.
2. Cópia com `merge_key` **nulo**: nunca casa, então cai no `INSERT` da nova versão.

```sql
MERGE INTO main.gold.dim_cliente AS d
USING (
    SELECT s.cliente_id AS merge_key, s.*
    FROM main.silver.clientes_atualizados s

    UNION ALL

    SELECT NULL AS merge_key, s.*
    FROM main.silver.clientes_atualizados s
    JOIN main.gold.dim_cliente d
      ON d.cliente_id = s.cliente_id AND d.atual = true
    WHERE NOT (d.cidade <=> s.cidade) OR NOT (d.nome <=> s.nome)
) AS u
   ON d.cliente_id = u.merge_key AND d.atual = true

WHEN MATCHED AND (NOT (d.cidade <=> u.cidade) OR NOT (d.nome <=> u.nome)) THEN
    UPDATE SET d.atual = false, d.fim_vigencia = u.data_alteracao

WHEN NOT MATCHED THEN
    INSERT (cliente_id, nome, cidade, inicio_vigencia, fim_vigencia, atual)
    VALUES (u.cliente_id, u.nome, u.cidade, u.data_alteracao, NULL, true);
```

| Cliente | O que acontece |
|---|---|
| **Novo** | A cópia 1 não casa e vai para o `INSERT` |
| **Mudou** | A cópia 1 fecha a antiga e a cópia 2 insere a nova |
| **Não mudou** | A cópia 1 casa, mas a condição é falsa: nada acontece |

Cuidados:

- A origem precisa ter **uma linha por chave** (a mais recente), senão o `MERGE` falha.
- `data_alteracao` deve vir da **origem**, não de `current_timestamp()`, para que reprocessar dê o mesmo resultado.
- O `MERGE` assume mudanças **em ordem**. Fora de ordem, as vigências saem erradas.
- **Deletes não são tratados** neste exemplo: cliente que some da origem continua com a versão aberta. Veja abaixo.

### Consultando

```sql
-- Estado atual
SELECT * FROM main.gold.dim_cliente WHERE atual = true;

-- Join pontual: versão vigente na data da venda
SELECT d.cidade, SUM(f.valor) AS faturamento
FROM main.gold.fato_vendas f
JOIN main.gold.dim_cliente d
  ON  d.cliente_id = f.cliente_id
  AND f.data_venda >= d.inicio_vigencia
  AND (f.data_venda < d.fim_vigencia OR d.fim_vigencia IS NULL)
GROUP BY d.cidade;
```

Se a fato já guarda a `cliente_sk`, o join volta a ser uma igualdade simples, que é o formato recomendado (joins por intervalo são mais caros).

## AUTO CDC: SCD declarativo

Nas **Lakeflow Spark Declarative Pipelines** (o antigo Delta Live Tables), o `AUTO CDC` faz tudo isso por você: você informa a **chave**, **como ordenar as mudanças** e **o tipo de SCD**.

> A API antiga se chamava `APPLY CHANGES INTO` / `apply_changes`. O `AUTO CDC` a substitui com a mesma sintaxe. O nome antigo ainda funciona e aparece em muito tutorial.

A origem é um **feed de mudanças (CDC)**: cada linha traz os dados, a operação e uma **coluna de sequência** com a ordem dos eventos.

| cliente_id | nome | cidade | operacao | seq |
|---:|---|---|---|---:|
| 1 | Ana | São Paulo | INSERT | 1 |
| 2 | Bruno | Recife | INSERT | 1 |
| 1 | Ana | Curitiba | UPDATE | 5 |
| 2 | Bruno | Recife | DELETE | 7 |

```sql
CREATE OR REFRESH STREAMING TABLE dim_cliente;

CREATE FLOW dim_cliente_flow AS AUTO CDC INTO
  dim_cliente
FROM STREAM(bronze.clientes_cdc)
KEYS (cliente_id)
APPLY AS DELETE WHEN operacao = 'DELETE'
SEQUENCE BY seq
COLUMNS * EXCEPT (operacao, seq)
STORED AS SCD TYPE 2;      -- SCD TYPE 1 para sobrescrever
```

O mesmo em Python:

```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col, expr

dp.create_streaming_table("dim_cliente")

dp.create_auto_cdc_flow(
    target="dim_cliente",
    source="clientes_cdc",
    keys=["cliente_id"],
    sequence_by=col("seq"),
    apply_as_deletes=expr("operacao = 'DELETE'"),
    except_column_list=["operacao", "seq"],
    stored_as_scd_type=2,
)
```

No tipo 2, o pipeline adiciona `__START_AT` e `__END_AT`:

| cliente_id | nome | cidade | `__START_AT` | `__END_AT` |
|---:|---|---|---:|---:|
| 1 | Ana | São Paulo | 1 | 5 |
| 1 | Ana | Curitiba | 5 | *(nulo)* |
| 2 | Bruno | Recife | 1 | 7 |

- Os dois campos herdam o tipo da coluna do `SEQUENCE BY` (com timestamp, a vigência é data/hora real). A versão atual tem `__END_AT` nulo.
- **Fora de ordem não é problema:** a posição de cada evento vem da sequência, não da ordem de chegada. No tipo 2, um evento atrasado entra no histórico no lugar certo.
- `SEQUENCE BY` não aceita nulos. Para desempatar, use `STRUCT(col1, col2)`.
- Para **histórico só em alguns atributos**, use `TRACK HISTORY ON * EXCEPT (telefone)`: mudar `cidade` cria versão nova, mudar `telefone` corrige a versão atual no lugar (tipo 1).
- Se a origem só entrega o **estado completo** (snapshots), existe o `AUTO CDC FROM SNAPSHOT`, que deduz o que mudou comparando snapshots.

## O que acontece com deletes no tipo 2

| | Comportamento |
|---|---|
| **`AUTO CDC`** | O delete **fecha a vigência** (`__END_AT` recebe a sequência do delete). A linha não é apagada. Se a chave voltar depois, abre uma nova versão. |
| **`MERGE`** | Nada, a menos que você trate. Com uma flag de delete na origem, adicione um `WHEN MATCHED AND u.operacao = 'DELETE'` que faz `atual = false` e preenche `fim_vigencia`. Com snapshot completo, use `WHEN NOT MATCHED BY SOURCE AND d.atual = true`. |

Não use `NOT MATCHED BY SOURCE` com origem incremental: "não apareceu" não significa "foi deletado".

## MERGE ou AUTO CDC?

- **`AUTO CDC`:** você já tem um feed CDC com sequência confiável, eventos podem chegar fora de ordem, ou quer histórico só em alguns atributos.
- **`MERGE`:** precisa de surrogate key identity, tem regra fora do padrão, ou não usa pipelines.

Com `AUTO CDC`, a dimensão **não tem surrogate key**: derive uma (`xxhash64(cliente_id, __START_AT)`) ou faça o join por chave natural e intervalo. Além disso, a tabela destino recebe updates e deletes, então ler dela em *streaming* exige tratamento (`skipChangeCommits`); o mais simples é consumir em batch ou por uma materialized view.

## Resumo

- **SCD** trata atributos de dimensão que mudam ao longo do tempo. A pergunta central: o passado deve refletir o valor novo ou o da época?
- **Tipo 1** sobrescreve, **tipo 2** cria uma linha por versão (surrogate key, vigência, flag de atual). Existem outras estratégias (0, 3, 4, 6), menos usadas, e dá para escolher o tipo **por atributo**.
- No tipo 2, a fato guarda a **surrogate key da versão vigente na data do fato**.
- No Databricks: **`MERGE INTO`** (lógica manual, tipo 2 com o truque da origem duplicada) ou **`AUTO CDC`** (declarativo, com `__START_AT`/`__END_AT`, sequência e `TRACK HISTORY ON`).
- Delete no tipo 2 **fecha a vigência**, não apaga. O `AUTO CDC` faz isso sozinho, o `MERGE` precisa ser instruído.
- Time travel do Delta não é SCD: ele expira.

## Referências

- [Slowly Changing Dimensions (Kimball Group)](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/)
- [The AUTO CDC APIs (Databricks)](https://docs.databricks.com/aws/en/dlt/cdc)
- [MERGE INTO (Databricks)](https://docs.databricks.com/aws/en/sql/language-manual/delta-merge-into.html)
- *The Data Warehouse Toolkit*, Ralph Kimball e Margy Ross
- Posts relacionados: [Junk Dimension]({{< relref "/posts/dados/junk-dimension.md" >}}), [Data Warehouse, Data Lake e Lakehouse]({{< relref "/posts/dados/dw-dl-lakehouse.md" >}})
