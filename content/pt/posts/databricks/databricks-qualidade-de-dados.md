---
title: "Databricks: constraints, expectations e Great Expectations"
author: "vapb"
description: "Como garantir qualidade de dados no Databricks: constraints do Delta (NOT NULL, CHECK), expectations dos pipelines declarativos (Lakeflow SDP) e Great Expectations, com o papel de cada um, exemplos e quando combiná-los."
date: 2026-10-26
tags: ["databricks", "data-quality", "delta-lake", "expectations", "great-expectations", "lakeflow", "unity-catalog"]
toc: true
---

## Introdução

Qualidade de dados não é uma ferramenta, é uma **decisão sobre onde e como reagir** quando o dado chega errado. No Databricks existem três mecanismos que respondem a essa pergunta em lugares diferentes:

| Mecanismo | Onde vive | Pergunta que responde |
|---|---|---|
| **Constraints** (Delta) | Na própria tabela | "Esta tabela **aceita** este dado?" |
| **Expectations** (Lakeflow SDP) | No pipeline declarativo | "Este dado **deve seguir** adiante neste pipeline?" |
| **Great Expectations** (GX) | Em código Python, fora da plataforma | "Este conjunto de dados **está de acordo** com o contrato?" |

Eles não competem: cada um cobre uma camada diferente. O post de [boas práticas]({{< relref "/posts/databricks/databricks-boas-praticas.md" >}}) resume a ideia (qualidade declarada junto do pipeline); aqui o foco é entender cada peça e como combiná-las. Para a base conceitual (dimensões de qualidade, observabilidade), veja a série [Data Quality Fundamentals]({{< relref "/posts/data-quality/data-quality-fundamentals-cap1.md" >}}).

> **Nota:** o ecossistema muda rápido (nomes de produtos e APIs). Confirme detalhes de sintaxe na documentação antes de levar algo à produção.

## Constraints do Delta

Constraints são regras **guardadas na tabela** e verificadas a cada escrita, por qualquer pessoa ou ferramenta que escreva nela. É a defesa mais baixa e mais difícil de contornar.

### Enforced: NOT NULL e CHECK

```sql
CREATE TABLE prod.silver.pedidos (
  pedido_id  BIGINT NOT NULL,
  cliente_id BIGINT,
  valor      DECIMAL(12,2),
  status     STRING
);

ALTER TABLE prod.silver.pedidos
  ADD CONSTRAINT valor_positivo CHECK (valor > 0);

ALTER TABLE prod.silver.pedidos
  ADD CONSTRAINT status_valido CHECK (status IN ('novo', 'pago', 'cancelado'));
```

- **Violou, a transação falha.** Não existe "descartar a linha": o lote inteiro é rejeitado com erro. É um mecanismo binário, tudo ou nada.
- **Ao adicionar, o Databricks verifica os dados existentes.** Se alguma linha já viola a regra, o `ADD CONSTRAINT` falha. Corrija o passado antes de impor a regra.
- A expressão do `CHECK` precisa ser **determinística** e sobre a própria linha: nada de UDFs, agregações ou janelas. Regras que envolvem várias linhas ou outras tabelas não cabem aqui.
- Requer **Delta Lake**. Adicionar uma constraint pode elevar o protocolo de escrita da tabela, o que afeta clientes Delta externos antigos.
- Para listar o que existe: `DESCRIBE DETAIL` ou `SHOW TBLPROPERTIES`.

### Informational: PRIMARY KEY, FOREIGN KEY e UNIQUE

No Unity Catalog você também pode declarar chaves, mas elas **não são impostas**:

```sql
ALTER TABLE prod.silver.pedidos
  ADD CONSTRAINT pk_pedidos PRIMARY KEY (pedido_id);
```

Servem como **documentação** (aparecem no Catalog Explorer e em ferramentas de BI/modelagem) e podem ajudar o otimizador. Declarar uma PK **não impede duplicatas**: unicidade continua sendo responsabilidade do seu pipeline (deduplicação, `MERGE`) ou de uma expectation/teste.

| Constraint | Imposta? | Comportamento ao violar |
|---|---|---|
| `NOT NULL` | Sim | Escrita falha |
| `CHECK` | Sim | Escrita falha |
| `PRIMARY KEY` / `FOREIGN KEY` / `UNIQUE` | **Não** (informativa) | Nada acontece |

### Quando usar

- **Invariantes que nunca podem ser quebradas** (chave não nula, valor positivo, enum válido), principalmente em tabelas **silver e gold** que muitos escrevem.
- Como **última barreira**: mesmo que alguém contorne o pipeline com um `INSERT` manual, a regra continua valendo.
- **Não use** quando o comportamento desejado é separar linhas ruins e seguir em frente: uma linha inválida derruba a carga inteira.

## Expectations nos pipelines declarativos

As **expectations** fazem parte das **Lakeflow Spark Declarative Pipelines** (SDP, antigas DLT). Em vez de falhar sempre, você escolhe **o que acontece** com a linha que viola a regra, e a plataforma **registra métricas** de quantas passaram e quantas falharam.

### Três ações

| Ação | SQL | Python | Efeito |
|---|---|---|---|
| **Warn** (padrão) | `EXPECT (expr)` | `@dp.expect` | Linha inválida **é gravada**; só a métrica é registrada |
| **Drop** | `... ON VIOLATION DROP ROW` | `@dp.expect_or_drop` | Linha inválida **é descartada** |
| **Fail** | `... ON VIOLATION FAIL UPDATE` | `@dp.expect_or_fail` | A atualização **para** na primeira violação |

Em SQL:

```sql
CREATE OR REFRESH STREAMING TABLE prod.silver.pedidos (
  CONSTRAINT pedido_com_id  EXPECT (pedido_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT valor_positivo EXPECT (valor > 0)             ON VIOLATION DROP ROW,
  CONSTRAINT data_razoavel  EXPECT (data_pedido >= '2020-01-01')
)
AS SELECT * FROM STREAM prod.bronze.pedidos;
```

Em Python, a variante `expect_all*` recebe um **dicionário** nome → regra, que pode ser reaproveitado em vários datasets:

```python
from pyspark import pipelines as dp

regras = {
    "pedido_com_id":  "pedido_id IS NOT NULL",
    "valor_positivo": "valor > 0",
}

@dp.table
@dp.expect_all_or_drop(regras)
def pedidos_silver():
    return spark.readStream.table("prod.bronze.pedidos")
```

> **Nota:** o módulo do Python mudou de nome ao longo do tempo (`import dlt` nas versões antigas, `from pyspark import pipelines as dp` nas atuais). O conceito é o mesmo.

### Onde vê o resultado

- Na UI do pipeline, aba **Data quality** do dataset: quantos registros passaram e falharam em cada expectation.
- No **event log** do pipeline, consultável por SQL, o que permite alertas e dashboards:

```sql
SELECT
  r.dataset,
  r.name,
  SUM(r.passed_records) AS passaram,
  SUM(r.failed_records) AS falharam
FROM (
  SELECT explode(from_json(
    details:flow_progress:data_quality:expectations,
    'array<struct<name:string, dataset:string, passed_records:int, failed_records:int>>'
  )) AS r
  FROM event_log(TABLE(prod.silver.pedidos))
  WHERE event_type = 'flow_progress'
)
GROUP BY r.dataset, r.name;
```

Uma consequência importante: **ações `FAIL` não geram métrica**, já que a atualização aborta. Para observar tendências, a combinação *warn/drop + alerta sobre o event log* funciona melhor.

### Padrão de quarentena

`DROP ROW` descarta em silêncio. Para não perder as linhas rejeitadas, aplique a **regra invertida** num segundo dataset:

```python
filtro_valido = " AND ".join(f"({r})" for r in regras.values())

@dp.table
@dp.expect_all_or_drop(regras)
def pedidos_silver():
    return spark.readStream.table("prod.bronze.pedidos")

@dp.table
def pedidos_quarentena():
    return (spark.readStream.table("prod.bronze.pedidos")
            .filter(f"NOT COALESCE(({filtro_valido}), false)"))
```

O `COALESCE` evita um detalhe traiçoeiro de SQL: `NOT (NULL)` é `NULL`, e o filtro descartaria justamente as linhas com valores nulos.

### Limitações

- Funcionam em **streaming tables, materialized views e views temporárias** do pipeline. Não existem para tabelas Delta comuns escritas por jobs.
- A regra é uma **expressão SQL sobre a linha**: sem funções Python customizadas, serviços externos ou subconsultas em outras tabelas.
- Verificações **entre linhas ou entre tabelas** (unicidade, integridade referencial, volume esperado) não cabem bem; modele-as como um dataset à parte ou use outra ferramenta.

## Great Expectations

**Great Expectations (GX)** é uma biblioteca open source em Python para **validar dados e documentar o que se espera deles**. Ela não depende do Databricks: roda em qualquer lugar com Python, e no Databricks recebe um **DataFrame Spark** para validar.

### Conceitos

| Conceito | O que é |
|---|---|
| **Expectation** | Uma asserção sobre o dado ("`valor` nunca é nulo", "`pedido_id` é único") |
| **Expectation Suite** | Conjunto de expectations de um dataset |
| **Data Source / Data Asset** | De onde vêm os dados (aqui, um DataFrame Spark) |
| **Batch Definition** | Que fatia do asset será validada (para DataFrames, o DataFrame inteiro) |
| **Validation Definition** | Liga uma suite a uma batch definition |
| **Checkpoint** | Executa validações e dispara ações (notificar, publicar resultados) |
| **Data Docs** | Relatório HTML legível com o resultado |

A biblioteca traz um **catálogo grande de expectations prontas**, incluindo as que SQL puro faz mal: unicidade, distribuição, valores dentro de um conjunto, comprimento de strings, regex, relação entre colunas.

### Exemplo em um notebook ou job

```python
%pip install great_expectations
```

```python
import great_expectations as gx

context = gx.get_context()

source = context.data_sources.add_spark(name="spark")
asset = source.add_dataframe_asset(name="pedidos")
batch_def = asset.add_batch_definition_whole_dataframe("pedidos_completo")

suite = context.suites.add(gx.ExpectationSuite(name="pedidos_silver"))
suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="pedido_id"))
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="pedido_id"))
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
    column="valor", min_value=0, strict_min=True))
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
    column="status", value_set=["novo", "pago", "cancelado"]))

validacao = context.validation_definitions.add(
    gx.ValidationDefinition(name="pedidos_silver_vd", data=batch_def, suite=suite)
)

df = spark.table("prod.silver.pedidos")
resultado = validacao.run(batch_parameters={"dataframe": df})

if not resultado.success:
    raise Exception("Validação de qualidade falhou: pedidos_silver")
```

O `raise` é o que transforma a validação em **portão**: a tarefa do job falha e as tarefas seguintes (por exemplo, a gold) não rodam.

### Como encaixar no Databricks

- Como **uma tarefa de um Lakeflow Job**, entre a transformação e o consumo: `silver → validar → gold`.
- **Guarde os resultados numa tabela** (por exemplo `prod.quality.resultados_validacao`) para histórico, dashboards e alertas, em vez de depender só dos Data Docs.
- **Versione as suites no Git**, junto do código do pipeline, e implante com [Asset Bundles]({{< relref "/posts/databricks/databricks-boas-praticas.md" >}}).
- Cuidado com **compatibilidade de versão e de compute**: a versão do GX precisa conversar com o Spark do runtime, e o **serverless** usa Spark Connect, que nem toda versão suporta da mesma forma. Teste no tipo de compute que vai usar em produção.

### Custo e limites

- GX **lê os dados** para validar (cada expectation vira uma ou mais consultas Spark). Em tabelas grandes isso custa compute, então valide **incrementos** ou amostras quando fizer sentido.
- É **mais um componente** para manter: dependência, configuração de contexto e armazenamento de resultados.
- A validação roda **depois** da escrita (a menos que você valide o DataFrame antes de gravar), então precisa de um desenho que impeça o dado ruim de chegar ao consumidor.

## E o DQX?

O **DQX** (Databricks Labs) é um projeto open source que ocupa o espaço de GX com foco em Databricks: regras declaradas em código ou YAML, mais de 80 checks prontos e a ideia de **separar linhas válidas de inválidas** (quarentena). É um projeto **Labs**: oferecido como está, sem suporte formal ou SLA da Databricks, então avalie o risco antes de torná-lo requisito de produção.

## Comparando

| | **Constraints** | **Expectations (SDP)** | **Great Expectations** |
|---|---|---|---|
| **Onde roda** | Em toda escrita na tabela | Dentro do pipeline declarativo | Em código (notebook/job) |
| **Escopo** | Tabelas Delta | Streaming tables, MVs, views do pipeline | Qualquer DataFrame ou fonte |
| **Granularidade** | Linha | Linha | Linha, coluna, dataset |
| **Reação a falha** | **Sempre** falha a escrita | Warn, drop ou fail | Você decide no código (`raise`, alerta) |
| **Regras entre linhas** | Não | Limitado | **Sim** (unicidade, distribuição) |
| **Métricas** | Nenhuma | Event log e UI | Resultados e Data Docs |
| **Instalação** | Nenhuma | Nenhuma | Biblioteca extra |
| **Custo extra** | Mínimo | Baixo (avalia durante o processamento) | Consultas adicionais |

## Como combinar

Uma estratégia simples e comum é usar cada um onde ele é mais forte:

| Camada | Mecanismo | Postura |
|---|---|---|
| **Bronze** | Quase nada (talvez `EXPECT` só para medir) | Fiel à origem; **não descarte** |
| **Bronze → Silver** | **Expectations** `DROP`/`FAIL` + quarentena | Conformidade: tipo, nulos, domínio, duplicatas |
| **Tabelas silver/gold** | **Constraints** `NOT NULL`/`CHECK` | Invariantes inegociáveis como rede de segurança |
| **Silver → Gold** | **Great Expectations** (ou expectations de MV) | Regras de negócio e de conjunto: unicidade, volume, distribuição |
| **Depois de publicado** | Monitoramento e alertas | Detectar drift e atraso (veja a série de [Data Quality Fundamentals]({{< relref "/posts/data-quality/data-quality-fundamentals-cap1.md" >}})) |

Algumas regras práticas:

- **Comece permissivo.** Use só `EXPECT` (warn) para descobrir quanto do dado viola cada regra; endureça para `DROP` e `FAIL` depois de entender.
- **Falhar só no que não pode passar.** Cada `FAIL` é um alerta noturno em potencial; reserve para violações que tornam o dado inútil.
- **Não descarte em silêncio.** Quarentena ou métrica monitorada, sempre.
- **Alerte sobre a métrica, não só sobre o erro.** Uma expectation de `DROP` que passa de 0,1% para 20% de rejeição é um incidente, mesmo sem nenhuma falha de job.
- **Não duplique regras nos três lugares.** Escolha o mecanismo mais adequado para cada regra; repetir a mesma regra em `CHECK`, expectation e GX só triplica a manutenção.

## Resumo

- **Constraints** (`NOT NULL`, `CHECK`) são **impostas pela tabela** e falham a escrita inteira; PK/FK/UNIQUE são **apenas informativas**.
- **Expectations** dos pipelines declarativos permitem **escolher a reação** (warn, drop, fail), geram métricas no event log, mas se limitam a regras SQL por linha dentro do pipeline.
- **Great Expectations** cobre o que os outros não alcançam (regras de conjunto, unicidade, distribuição), ao custo de ser mais um componente e de ler os dados novamente.
- Combine: **expectations** para filtrar na transição entre camadas, **constraints** como rede de segurança e **GX** para validações de negócio mais ricas. Meça as rejeições e alerte sobre elas.

## Referências

- [Manage data quality with pipeline expectations (Databricks)](https://docs.databricks.com/aws/en/ldp/expectations)
- [Constraints on Databricks (Databricks)](https://docs.databricks.com/aws/en/tables/constraints)
- [GX Core overview (Great Expectations)](https://docs.greatexpectations.io/docs/core/introduction/gx_overview)
- [Connect to dataframe data (Great Expectations)](https://docs.greatexpectations.io/docs/core/connect_to_data/dataframes)
- [DQX (Databricks Labs)](https://github.com/databrickslabs/dqx)
- Posts relacionados: [Boas práticas no Databricks]({{< relref "/posts/databricks/databricks-boas-praticas.md" >}}), [Objetos de dados]({{< relref "/posts/databricks/databricks-objetos-de-dados.md" >}}), [Lakeflow Connect]({{< relref "/posts/databricks/databricks-lakeflowconnect.md" >}}), [Data Quality Fundamentals]({{< relref "/posts/data-quality/data-quality-fundamentals-cap1.md" >}})
