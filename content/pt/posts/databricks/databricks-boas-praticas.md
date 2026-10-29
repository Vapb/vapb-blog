---
title: "Databricks: boas práticas e padrões de engenharia de dados"
author: "vapb"
description: "Boas práticas e padrões para engenharia de dados no Databricks: organização no Unity Catalog, armazenamento Delta, ingestão, transformação, qualidade, orquestração, compute, CI/CD, segurança e custos."
date: 2026-10-28
tags: ["databricks", "unity-catalog", "delta-lake", "lakeflow", "data-engineering", "best-practices"]
toc: true
---

## Introdução

Boa parte dos problemas em projetos Databricks não vem do Spark, vem de decisões tomadas cedo e raramente revistas: onde ficam os dados, quem tem acesso, como o código chega à produção, quanto custa rodar. Este post reúne as **boas práticas** e os **padrões** que mais se repetem, organizados pelo ciclo de vida de um pipeline.

A ideia de fundo é uma só:

> **Prefira o que é declarativo, gerenciado e versionado ao que é manual, customizado e escondido num notebook.**

> **Nota:** o ecossistema muda rápido (nomes de produtos, padrões e recomendações). Trate o post como mapa e confirme os detalhes na documentação antes de adotar algo em produção.

## Visão geral

| Camada | Prática central |
|---|---|
| **Governança** | Tudo no Unity Catalog, permissões para grupos, ambientes separados |
| **Armazenamento** | Tabelas managed, liquid clustering, predictive optimization |
| **Ingestão** | Auto Loader / streaming tables / conectores gerenciados; bronze fiel à origem |
| **Transformação** | Pipelines declarativos, funções nativas do Spark, idempotência |
| **Qualidade** | Expectations nas bordas das camadas, monitoramento |
| **Orquestração** | Lakeflow Jobs com retries, repair e gatilhos por evento |
| **Compute** | Serverless ou job compute; all-purpose só para exploração |
| **CI/CD** | Código em arquivos, Asset Bundles, testes, deploy por service principal |
| **Custos** | Tags, system tables, policies |

## Governança e organização

### Unity Catalog como base de tudo

Todo dado novo deve nascer no **Unity Catalog** (veja a [hierarquia]({{< relref "/posts/databricks/databricks-objetos-de-dados.md" >}}) de objetos). O legado (Hive metastore, **DBFS root**, **mounts**) não oferece governança, linhagem nem permissões finas, e quanto mais tempo ele convive com o novo, mais caro fica migrar.

**Acesso ao storage: use external locations e volumes, nunca mounts ou senhas no código.**

O storage (S3, ADLS, GCS) é onde os arquivos ficam guardados na nuvem. Dá para chegar até ele de dois jeitos:

| Jeito antigo (evite) | Jeito certo (Unity Catalog) |
|---|---|
| **Mount:** um atalho `/mnt/...` que usa uma só credencial. Quem vê o atalho lê tudo o que ela alcança. | **External location:** um caminho do storage ligado a uma credencial, com permissão dada a quem precisa. |
| **Chave no código:** a senha fica escrita no notebook ou no cluster e acaba vazando. | **Volume:** uma "pasta" governada dentro do catálogo, em `/Volumes/catalogo/schema/volume/...`. |

Em uma frase: tabelas para dado tabular, **volumes** para arquivos soltos (CSV, imagens, PDFs) e **external locations** quando for preciso apontar para um caminho do storage. Em todos os casos quem controla o acesso é o Unity Catalog, não uma senha espalhada por aí.

**Linhagem, auditoria e descoberta vêm "de graça".**

Como tudo passa pelo Unity Catalog, ele anota sozinho o que acontece, sem você configurar nada:

- **Linhagem:** de onde cada tabela ou coluna veio e quem a usa.
- **Auditoria:** quem acessou o quê e quando.
- **Descoberta:** achar tabelas por busca, descrição e tags.

O porém: só vale para o que passa pelo catálogo. Quem lê por mount ou por chave direta fica invisível. E descrições e tags alguém ainda precisa escrever.

### Separar ambientes e camadas

Há dois eixos para organizar `catalogo.schema.objeto`, e a escolha mais comum é combiná-los:

| Estratégia | Exemplo | Quando faz sentido |
|---|---|---|
| **Catálogo por ambiente** | `dev`, `stg`, `prod` | Times pequenos, isolamento claro entre ambientes |
| **Catálogo por domínio** | `vendas`, `financeiro` | Organizações grandes, donos de dados por área |
| **Schema por camada** | `bronze`, `silver`, `gold` | Quase sempre, dentro do catálogo |

Um padrão comum: `prod_vendas.silver.pedidos`, onde o **código é igual em todos os ambientes** e só o nome do catálogo muda (parametrizado, nunca escrito fixo no código).

### Permissões

- **Conceda a grupos**, não a usuários. Entrada e saída de pessoas vira gestão de grupo.
- **Princípio do menor privilégio:** `USE CATALOG`/`USE SCHEMA` mais `SELECT` onde precisa; escrita só para o pipeline.
- **Pipelines rodam como service principal**, não como uma pessoa. Se o dono sai da empresa, nada quebra.
- **Row filters e column masks** na própria tabela (e, em cenários maiores, controle baseado em **tags/atributos**) em vez de multiplicar views de segurança.

### Convenções de nomes

Defina cedo e documente: `snake_case`, singular ou plural (escolha um), sufixos que digam algo (`_dim`, `_fato`), **comentários e tags** em tabelas e colunas importantes. Metadados bons valem muito mais agora que busca e Genie dependem deles.

Alguns exemplos do que combinar com o time:

| O que nomear | Exemplo | Por quê |
|---|---|---|
| **Catálogo** | `prod`, `dev`, `vendas_prod` | Mostra o ambiente (ou a área) logo de cara |
| **Schema** | `bronze`, `silver`, `gold`, `financeiro` | Mostra a camada ou o domínio |
| **Tabela de fato** | `fato_pedidos`, `fato_vendas` | Quem lê entende o papel da tabela |
| **Tabela de dimensão** | `dim_cliente`, `dim_produto` | Separa dimensões de fatos |
| **Coluna** | `data_pedido`, `valor_total`, `cliente_id` | `snake_case`, sem acento, sem abreviação obscura |
| **Volume** | `vendas_prod.bronze.arquivos_nf` | Diz de que dado são os arquivos |
| **Job** | `vendas_diario_silver` | Dono, frequência e camada no nome |

Alguns padrões de coluna ajudam muito: `_id` para chaves (`cliente_id`), `data_` ou `_em` para datas (`data_pedido`, `criado_em`), `flag_` ou `is_` para booleanos (`is_ativo`) e unidade no nome quando houver ambiguidade (`valor_brl`, `peso_kg`).

O mais importante não é qual padrão escolher, e sim **escolher um e aplicar em tudo**. Um mix de `dim_cliente`, `ClienteDim` e `tb_clientes` faz mais estrago do que qualquer convenção imperfeita.

## Armazenamento com Delta Lake

### Tabelas managed por padrão

**Managed** é o padrão recomendado: armazenamento gerenciado, otimizações automáticas e `UNDROP` como rede de segurança. Use **external** só quando outro sistema precisa ser dono dos arquivos.

### Liquid clustering em vez de partição e ZORDER

O **liquid clustering** (`CLUSTER BY`) substitui o par particionamento + `ZORDER` e permite **trocar as colunas depois** sem reescrever tudo.

```sql
CREATE TABLE prod.silver.pedidos (
  pedido_id BIGINT, cliente_id BIGINT, data_pedido DATE, valor DECIMAL(12,2)
)
CLUSTER BY (data_pedido, cliente_id);
```

- Escolha colunas **muito usadas em filtros** (data, chave de cliente).
- Com **predictive optimization** ligada, existe até a opção `CLUSTER BY AUTO`, em que o Databricks escolhe as colunas conforme o uso.
- **Evite particionar** tabelas pequenas ou médias: partições demais geram arquivos pequenos e metadados caros. Particionar só faz sentido em tabelas muito grandes e com padrão de acesso estável.

### Manutenção automática

| Operação | O que faz | Prática |
|---|---|---|
| `OPTIMIZE` | Compacta arquivos pequenos | Deixe a **predictive optimization** cuidar disso |
| `VACUUM` | Remove arquivos antigos | Idem; **não reduza a retenção** abaixo do padrão sem motivo (quebra *time travel* e leitores lentos) |
| `ANALYZE` | Estatísticas para o otimizador | Idem |

O problema clássico é o dos **arquivos pequenos**: muitas escritas minúsculas deixam as leituras lentas. Gravar em lotes maiores e deixar a otimização automática trabalhar resolve a maioria dos casos.

### Tipos e esquema

- Use o **tipo certo**: `DATE`/`TIMESTAMP` em vez de string, `DECIMAL` para dinheiro (nunca `DOUBLE`).
- **Evolua o esquema de forma deliberada:** `ALTER TABLE` ou `mergeSchema` consciente, não schema-on-read por acidente.
- Datas e horas: guarde em **UTC** e converta só na apresentação.

## Arquitetura medalhão na prática

A [arquitetura medalhão]({{< relref "/posts/databricks/databricks-lakeflowconnect.md" >}}) é um acordo sobre **o que cada camada garante**:

| Camada | Garantia | O que fazer | O que evitar |
|---|---|---|---|
| **Bronze** | Fiel à origem | Gravar o dado **como veio**, com colunas de metadata (arquivo, hora de ingestão) | Limpar, filtrar ou regra de negócio |
| **Silver** | Limpo e conforme | Tipar, deduplicar, validar, aplicar CDC | Agregações de negócio |
| **Gold** | Pronto para consumo | Modelo dimensional, agregações, métricas | Reprocessar a partir de bronze direto, pulando a silver |

- Mantenha o bronze **imutável e reprocessável**: é a sua fonte da verdade para refazer silver e gold quando a lógica mudar.
- **Não pule camadas** só para ganhar tempo. O atalho vira dívida na primeira correção de dados.
- Para o modelo da gold, veja o post de [Slowly Changing Dimensions]({{< relref "/posts/dados/slowly-changing-dimensions.md" >}}).

## Ingestão

### Escolha a ferramenta pela origem

| Origem | Ferramenta |
|---|---|
| Arquivos em cloud storage ou volume | **Auto Loader** (direto ou via streaming table) |
| SaaS e bancos (CDC) | **Lakeflow Connect** (conectores gerenciados) |
| Mensageria (Kafka, Event Hubs, Pub/Sub) | **Structured Streaming** / streaming table |
| Carga pontual | `CREATE TABLE AS SELECT` |

Detalhes de cada método estão no post de [Lakeflow Connect]({{< relref "/posts/databricks/databricks-lakeflowconnect.md" >}}).

### Práticas

- **Incremental sempre que possível.** Reler toda a origem a cada execução é o jeito mais fácil de queimar dinheiro.
- **Prefira Auto Loader a `COPY INTO`** em projetos novos: escala melhor com muitos arquivos e evolui esquema.
- **Preserve a coluna `_rescued_data`** em vez de descartar o que não encaixou no esquema: ela salva você quando a origem muda sem avisar.
- **Landing em volume**, com pastas por origem e por data, separada do bronze.
- **Não duplique o que um conector gerenciado já faz.** Para SaaS e CDC de banco, escrever extrator próprio costuma custar mais em manutenção do que o conector em licença.

```python
(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", "/Volumes/prod/bronze/_schemas/pedidos")
    .load("/Volumes/prod/landing/pedidos/")
    .writeStream
    .option("checkpointLocation", "/Volumes/prod/bronze/_checkpoints/pedidos")
    .trigger(availableNow=True)
    .toTable("prod.bronze.pedidos"))
```

`trigger(availableNow=True)` processa tudo o que chegou e **encerra**: você mantém a semântica de streaming (incremental, com checkpoint) pagando como um job em lote.

## Transformação

### Pipelines declarativos primeiro

As **Lakeflow Spark Declarative Pipelines (SDP)**, antigas DLT, resolvem de uma vez dependências, checkpoints, retries e qualidade. Você declara **o resultado**, e a engine decide a ordem e o modo de execução.

- **Streaming table** para dado que só chega, **materialized view** para joins e agregações, `AUTO CDC` para dado que muda. A [comparação]({{< relref "/posts/databricks/databricks-objetos-de-dados.md" >}}) está no post de objetos de dados.
- Use jobs com notebooks ou scripts só onde o declarativo não alcança.

### Idempotência

Um pipeline é **idempotente** quando rodar duas vezes produz o mesmo resultado que rodar uma. É o que torna seguro reexecutar depois de falha, e isso muda tudo em operação.

- **Prefira `MERGE` a `INSERT` puro** quando há chave natural:

```sql
MERGE INTO prod.silver.pedidos AS t
USING novos AS s
ON t.pedido_id = s.pedido_id
WHEN MATCHED AND s.atualizado_em > t.atualizado_em THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```

- **Sobrescrita por partição lógica** (`replaceWhere`) para recargas de uma janela de datas.
- **Deduplique na silver**, porque a origem entrega duplicatas mais do que se admite.
- Nunca dependa de "rodar uma vez só por dia".

### Performance do código

- **Funções nativas do Spark** antes de UDFs. UDFs Python quebram otimizações e serializam dado entre processos; se for inevitável, prefira **pandas UDFs** ou SQL.
- **Evite `collect()` e `toPandas()`** em dado grande: trazem tudo para o driver.
- **Filtre cedo e selecione só as colunas necessárias**, para o Spark poder pular arquivos.
- **Joins:** tabela pequena num join com uma grande se beneficia de *broadcast*; o AQE (Adaptive Query Execution) já ajusta muita coisa, então **meça antes de forçar hints**.
- **Cuidado com skew** (chaves muito desbalanceadas) e `shuffle` desnecessário.
- **Evite `for` linha a linha**: pense em conjuntos.
- Dê uma olhada no **Query Profile** antes de tunar às cegas.

## Qualidade de dados

A qualidade deve ser **declarada junto do pipeline**, não verificada por scripts soltos depois.

```sql
CREATE OR REFRESH STREAMING TABLE prod.silver.pedidos (
  CONSTRAINT valor_positivo EXPECT (valor > 0) ON VIOLATION DROP ROW,
  CONSTRAINT pedido_com_id  EXPECT (pedido_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT data_valida    EXPECT (data_pedido >= '2020-01-01')
)
AS SELECT * FROM STREAM prod.bronze.pedidos;
```

| Ação da expectation | Efeito | Use quando |
|---|---|---|
| Só `EXPECT` | Registra a métrica, mantém a linha | Você quer **observar** antes de bloquear |
| `DROP ROW` | Descarta a linha inválida | Erro isolado e tolerável |
| `FAIL UPDATE` | Interrompe a execução | Violação que **não pode** passar |

- **Valide nas fronteiras:** de bronze para silver (conformidade) e de silver para gold (regra de negócio).
- **Não descarte em silêncio:** guarde as linhas rejeitadas numa tabela de quarentena para análise.
- **Comece permissivo** (só registrar) e endureça conforme entende o dado.
- Para o dado *depois* de publicado, use **monitoramento** (Lakehouse Monitoring, alertas SQL) para detectar drift e atrasos.

## Orquestração

O [Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/) é o orquestrador nativo e, em geral, dispensa um Airflow só para encadear tarefas da plataforma.

- **Tarefas pequenas e com uma responsabilidade**, ligadas por dependências, em vez de um notebook de 2.000 linhas.
- **Retries e timeouts** em cada tarefa: falhas transitórias (rede, throttling) são rotina.
- **Repair run:** ao falhar uma tarefa, reexecute só ela e as dependentes, não o job inteiro. Isso só é seguro porque as tarefas são idempotentes.
- **Gatilhos por evento** quando fizer sentido: chegada de arquivo ou **atualização de tabela** em vez de um cron "chute" que roda antes do dado existir.
- **Parâmetros** (data, ambiente, janela) em vez de valores fixos, o que permite *backfill* sem editar código.
- **Notificações** de falha e de duração anormal, para um canal que alguém lê.
- Se o ecossistema já tem outro orquestrador (Airflow, Dagster), tudo bem: dispare jobs do Databricks por ele, mas não reimplemente a lógica de dependência nos dois lados.

## Compute

| Tipo | Uso | Observação |
|---|---|---|
| **Serverless** | Jobs, pipelines, SQL | Padrão sensato: sem gestão de cluster, inicia em segundos |
| **Job compute** | Jobs que exigem configuração própria | Cluster efêmero, criado e destruído por execução |
| **All-purpose** | Exploração interativa | **Mais caro**, não use para produção |
| **SQL warehouse** | BI e consultas SQL | Serverless para cargas variáveis |

- **Produção nunca em all-purpose.** É o erro de custo mais comum.
- **Cluster policies** limitam tamanho, runtime e tags, evitando surpresas na fatura.
- **Autoscaling** com mínimo baixo; **auto-terminate** curto nos interativos.
- **Runtime LTS** em produção, atualizado com regularidade.
- **Photon** acelera SQL e DataFrames na maior parte dos casos, e normalmente compensa o custo extra.
- **Dimensione por medição**, não por palpite: comece pequeno e suba olhando o tempo e o spill em disco.

## Desenvolvimento e CI/CD

O que separa um projeto amador de um profissional não é a lógica, é **como ela chega à produção**.

- **Código em arquivos** (`.py`, `.sql`) versionados no Git, não em notebooks soltos. Notebooks servem para explorar e para orquestrar passos simples.
- **Lógica em funções testáveis**, empacotadas num módulo ou *wheel*, e o notebook/job só as chama.
- **Testes unitários** (pytest) rodando fora do cluster em funções puras, mais testes de integração num ambiente de dev.
- **Databricks Asset Bundles (DABs):** a infraestrutura do projeto (jobs, pipelines, permissões) descrita em YAML, versionada e implantada por `databricks bundle deploy`.

```yaml
bundle:
  name: pedidos

variables:
  catalog:
    default: dev

targets:
  dev:
    mode: development
    default: true
  prod:
    mode: production
    variables:
      catalog: prod
    run_as:
      service_principal_name: "<application-id>"
```

- **Mesmo código, ambientes diferentes:** só mudam as variáveis do *target*.
- **Deploy pelo CI** (GitHub Actions, Azure DevOps…) com service principal, nunca da máquina de uma pessoa.
- **Revisão de código** e PRs para tudo que vai à produção, inclusive SQL e configuração.
- **Sem segredos no código:** use **secrets** do Databricks e autenticação **OAuth/service principal**, em vez de tokens pessoais (PAT) de longa duração.

## Observabilidade e custos

Você só otimiza o que mede, e o Databricks já registra bastante coisa em **system tables**.

| Pergunta | Onde olhar |
|---|---|
| Quanto estamos gastando e com quê? | `system.billing.usage` |
| Quem acessou o quê? | `system.access.audit` |
| De onde vem esta tabela? | Linhagem no Unity Catalog |
| Por que o pipeline foi lento ou falhou? | Event log do pipeline e Query Profile |

- **Tags de custo** (time, projeto, ambiente) em jobs, clusters e warehouses, para atribuir a conta a alguém.
- **Orçamentos e alertas** de consumo antes do susto, não depois.
- **Pare o que ninguém usa:** tabelas, jobs e dashboards órfãos custam sem entregar nada.
- **Incremental e serverless** costumam ser as maiores economias, antes de qualquer ajuste fino.

## Anti-padrões

| Anti-padrão | Por que dói | Alternativa |
|---|---|---|
| Produção em cluster all-purpose | Caro e instável | Serverless ou job compute |
| Tudo num notebook gigante | Não testa, não revisa, não reaproveita | Funções em módulos + tarefas pequenas |
| Reler a origem inteira a cada execução | Custo e tempo crescem sem parar | Auto Loader, streaming tables, MVs |
| Particionar por coluna de alta cardinalidade | Milhares de arquivos pequenos | Liquid clustering |
| Permissão para usuários individuais | Ingestão e saída viram trabalho manual | Grupos + service principals |
| Limpar e filtrar no bronze | Perde a fonte da verdade | Bronze fiel; limpeza na silver |
| Pipeline que não pode ser reexecutado | Falha vira intervenção manual | Idempotência (`MERGE`, `replaceWhere`) |
| Tokens e senhas no código | Vazamento certo, cedo ou tarde | Secrets + OAuth |
| `VACUUM` com retenção mínima | Quebra *time travel* e leituras em curso | Padrão de 7 dias |
| Ajustar Spark às cegas | Piora tanto quanto melhora | Medir no Query Profile primeiro |

## Checklist rápido

- [ ] Dados no Unity Catalog, tabelas **managed**, schemas por camada
- [ ] Permissões em **grupos**, pipelines com **service principal**
- [ ] **Liquid clustering** e **predictive optimization** ligados
- [ ] Ingestão **incremental**, bronze fiel à origem
- [ ] Pipelines **declarativos** com **expectations** nas fronteiras de camada
- [ ] Tarefas **idempotentes**, com retries, timeout e **repair run**
- [ ] Produção em **serverless/job compute**, nunca all-purpose
- [ ] Código no Git, **testes**, deploy por **Asset Bundles** e CI
- [ ] **Tags de custo** e consulta regular às system tables
- [ ] Alertas de falha chegando a alguém que vai agir

## Resumo

- A base é **Unity Catalog**: governança, linhagem e permissões vêm junto, desde que tudo passe por ele.
- No armazenamento, prefira **managed**, **liquid clustering** e **predictive optimization**; evite partição e manutenção manual.
- Em ingestão e transformação, o caminho é **incremental e declarativo**, com **idempotência** e **bronze imutável**.
- **Qualidade** declarada no pipeline (expectations), e não verificada depois por scripts.
- Em operação, **Lakeflow Jobs** com retries e repair, **serverless** em produção e **tags** em tudo.
- **CI/CD** com código em arquivos, testes, Asset Bundles e service principal separa um projeto sustentável de um que depende de uma pessoa.

## Referências

- [Best practices for the lakehouse (Databricks)](https://docs.databricks.com/aws/en/lakehouse-architecture/)
- [Unity Catalog best practices (Databricks)](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices)
- [Liquid clustering (Databricks)](https://docs.databricks.com/aws/en/delta/clustering)
- [Manage data quality with pipeline expectations (Databricks)](https://docs.databricks.com/aws/en/ldp/expectations)
- [Databricks Asset Bundles (Databricks)](https://docs.databricks.com/aws/en/dev-tools/bundles/)
- Posts relacionados: [Databricks Fundamentals]({{< relref "/posts/databricks/databricks.md" >}}), [Lakeflow Connect]({{< relref "/posts/databricks/databricks-lakeflowconnect.md" >}}), [Objetos de dados]({{< relref "/posts/databricks/databricks-objetos-de-dados.md" >}}), [Slowly Changing Dimensions]({{< relref "/posts/dados/slowly-changing-dimensions.md" >}})
