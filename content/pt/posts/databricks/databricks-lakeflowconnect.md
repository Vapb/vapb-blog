---
title: "Lakeflow Connect: ingestão, Delta Lake e medalhão"
author: "vapb"
description: "Anotações sobre o Lakeflow Connect: tipos de conectores (upload, standard e managed), como funcionam SaaS, CDC e community, métodos de ingestão (batch, incremental e streaming), tabelas UC/Delta e arquitetura medalhão."
date: 2026-10-14
tags: ["databricks", "lakeflow", "data-engineering"]
toc: true
aliases: ["/posts/databricks-lakeflowconnect/"]
---

## Introdução

Nas [anotações de fundamentos do Databricks]({{< relref "/posts/databricks/databricks.md" >}}) o **Lakeflow** apareceu como a camada de engenharia de dados da plataforma. Ele tem três peças:

- **Lakeflow Connect:** conectores de ingestão.
- **Spark Declarative Pipelines (SDP):** framework para construir pipelines batch e streaming em SQL e Python.
- **Lakeflow Jobs:** orquestração dos workloads e das tarefas de um fluxo.

Tudo isso roda sobre o Spark (com Structured Streaming), é governado pelo **Unity Catalog** e guarda o dado em formatos abertos (Delta, Parquet, Iceberg).

Aqui o foco é a primeira peça, a **ingestão**, ou seja, levar o dado das fontes para dentro do lakehouse. No fim, uma revisão de **Delta Lake** e **arquitetura medalhão**, que é para onde o dado ingerido vai.

> **Nota:** a plataforma muda rápido e conectores novos entram o tempo todo. A lista de fontes suportadas deve ser conferida na documentação oficial.

## O que é o Lakeflow Connect

O Lakeflow Connect é o conjunto de **conectores de ingestão** do Databricks. Ele traz dados de arquivos, cloud storage, bancos, aplicações corporativas e fontes de streaming direto para o lakehouse, numa plataforma única e gerenciada.

O destino é sempre o mesmo: **tabelas Delta governadas pelo Unity Catalog**, prontas para o resto do lakehouse.

### O problema da ingestão tradicional

Sem uma solução unificada, cada tipo de fonte exige a sua ferramenta: arquivos on-premises, sistemas legados, bancos, cloud storage, SaaS e streams de eventos. O resultado costuma ser uma mistura de ferramentas de terceiros e código próprio, com:

- mais **custo operacional**;
- **governança inconsistente**;
- **observabilidade fragmentada**.

### Benefícios

- **Solução gerenciada e eficiente:** menor custo e menos tempo até o dado estar disponível.
- **Interfaces self-service** para cada perfil (engenheiro, analista), democratizando o acesso ao dado.
- **Observabilidade e governança unificadas:** pipelines e tabelas seguros e monitorados no mesmo lugar.

## Categorias de conectores

O Lakeflow Connect tem três categorias, cada uma para um tipo de fonte e padrão de ingestão:

| Categoria | Para quê | Fontes |
| --- | --- | --- |
| **Upload Files** | Subir arquivos locais manualmente | Arquivo local → volume ou tabela |
| **Standard Connectors** | Ingestão programática, você controla o código | Cloud object storage, Kafka e outras fontes |
| **Managed Connectors** | Ingestão gerenciada de sistemas corporativos | SaaS e bancos de dados |

- **Upload Files:** o caminho rápido para testes e arquivos pontuais. Você sobe o arquivo para um **volume** do Unity Catalog ou cria uma tabela direto de um arquivo local.
- **Standard Connectors:** você escolhe o método de ingestão (batch, incremental ou streaming, na seção seguinte) e escreve a lógica em SQL ou Python.
- **Managed Connectors:** leituras e escritas **incrementais** feitas pelo Databricks, com configuração em vez de código. São mais rápidos, escaláveis e baratos que montar a ingestão à mão.

## Managed Connectors: dados corporativos

Até aqui a ingestão foi de arquivos em cloud storage. Mas boa parte do dado corporativo está em **bancos de dados e aplicações SaaS**, e para isso entram os **Managed Connectors**.

- São conectores **nativos do Databricks**, de baixo código e **totalmente gerenciados**: menos configuração manual e nenhum código de integração para manter.
- Podem ser configurados por **interface (point and click)** ou por **API**.
- Fontes de exemplo: Workday, Salesforce, PostgreSQL, SQL Server e outras.
- Usam **leituras e escritas incrementais**, o que deixa a ingestão mais rápida, escalável e barata, com o dado sempre fresco para quem consome.
- Cada conector está em um **estágio de release** diferente (alguns em public preview, outros em GA), então vale conferir a documentação.

### Como o dado é lido

Dentro dos managed (e dos community), os conectores se diferenciam por **como o dado é lido na fonte**:

| Tipo | Fontes típicas | Como lê |
| --- | --- | --- |
| **SaaS** | Salesforce, Workday, ServiceNow, Google Analytics | Pela API da própria aplicação |
| **CDC** | Bancos de dados (ex.: SQL Server, MySQL, PostgreSQL) | Lendo o log de transações do banco |
| **Query-based** | Bancos e warehouses | Executando consultas (full ou incremental por coluna de controle) |
| **Community** | Qualquer fonte sem conector oficial | Código da comunidade ou próprio, sobre a infra do Databricks |

**CDC** (*change data capture*) captura só o que mudou (inserts, updates e deletes) a partir do log do banco, com baixo impacto na fonte. O **query-based** é o caminho quando não dá para ler o log: ele consulta a fonte, e por isso depende de uma coluna que indique o que mudou (ex.: `updated_at`) para ser incremental.

### Arquitetura SaaS

O fluxo é o mais simples, porque a fonte é **pública** (uma API ou um endpoint OLAP acessível pela internet):

1. Um job de **Declarative Pipelines serverless** busca as **credenciais** no **Unity Catalog** (como uma *connection*), sem ficar em código ou notebook.
2. O job acessa a fonte pública (API, porta OLAP aberta etc.).
3. O serviço transforma o dado e o grava em uma **streaming table** (Delta).

Para isso existe um tipo novo de pipeline, o **managed ingestion pipeline**: ele é em grande parte **predefinido e gerenciado pelo Databricks**, que já lida com as particularidades de cada fonte.

Todo o movimento de dados acontece no **data plane**. O **control plane** só é usado para configurar o pipeline, monitorar (ler o event log) e gerenciar.

### Arquitetura de banco de dados (ex.: RDS, CDC)

O destino é o mesmo (streaming tables), mas a arquitetura é mais envolvida porque o banco pode estar **on-premises ou numa nuvem privada**. Entram dois elementos novos: o **ingestion gateway** e o **volume do Unity Catalog**.

1. Um job de Declarative Pipelines em **compute clássico** (o ingestion gateway) busca as credenciais no **Unity Catalog**.
2. Com elas, conecta ao banco e extrai **metadata, snapshots e change logs**.
3. O **estado mais recente e os dados de staging** são salvos em um **volume do Unity Catalog**.
4. Um job de Declarative Pipelines **serverless** (o ingestion pipeline) processa esses dados e grava nas **streaming tables**.

O **volume** é a camada intermediária de staging que permite ao pipeline seguinte pegar os dados. Ele é protegido pelos mecanismos normais do UC e, por padrão, o acesso é limitado a quem roda o pipeline.

**Por que existe o gateway?**

- **Rede:** muitos bancos ficam atrás de firewall e não são públicos. Sem opções como Private Link, o gateway pode ser implantado **dentro da sua rede**.
- **Carga no banco:** o ideal é limitar as conexões diretas à fonte. Separando o gateway do pipeline, **um gateway fala com o banco e distribui para N pipelines**. Nos conectores SaaS isso não é problema, porque a carga já é limitada pelos limites de API.

Além disso, o volume desacopla as duas partes: o gateway fica sempre capturando e o pipeline processa depois, sem perder mudanças se estiver parado.

### Conectores da comunidade

São conectores para fontes que não têm suporte oficial. Rodam sobre a mesma base (Unity Catalog para credenciais e governança, SDP para executar o pipeline), mas o **código de leitura da fonte** vem da comunidade ou é escrito por você, normalmente usando a API de *Python data source* do Spark.

### Categorias de fontes

Os conectores também podem ser vistos pelo **tipo de origem**:

- **Applications:** sistemas SaaS (CRM, ERP, marketing, analytics).
- **File sources:** arquivos em object storage ou SFTP.
- **Databases:** bancos transacionais, normalmente via CDC.
- **Warehouses:** outros data warehouses, normalmente via query-based.
- **Message buses:** Kafka, Kinesis, Event Hubs e similares.
- **Zerobus Ingest:** envio de eventos **direto para tabelas Delta**, sem precisar de um message bus no meio. A aplicação escreve na tabela, em vez de publicar num broker que depois alguém precisa consumir.

### Partner Connect

Quando **não existe managed connector** para a sua fonte, uma alternativa é o **Partner Connect**:

- Permite criar **contas de teste** com parceiros de tecnologia selecionados e conectar o workspace às soluções deles **direto pela interface do Databricks**.
- Assim dá para **testar a solução com os seus dados** no lakehouse e adotar a que atender melhor.
- Os parceiros de ingestão oferecem uma ampla gama de conectores, com funcionalidades profundas mantidas por times dedicados. Exemplos: Informatica, Qlik, Rivery, Alteryx, Prophecy e Fivetran.
- Mesmo quando há conector nativo para uma fonte, a opção pelo parceiro continua existindo: a ideia é dar **escolha** ao cliente.

## Métodos de ingestão

Nos **Standard Connectors** há três métodos. A escolha depende de quanto dado há, de quão rápido ele precisa chegar e do custo aceitável.

| Método | O que processa | Quando usar |
| --- | --- | --- |
| **Batch** | **Todos** os registros da fonte, a cada execução | Cargas pequenas, dado que muda por inteiro ou recarga completa |
| **Incremental batch** | Só o que é **novo**; o que já foi carregado é pulado | Maioria das cargas periódicas: mais rápido e barato, por processar menos dado |
| **Streaming** | Continuamente, em quase tempo real | Quando a latência importa |

Técnicas comuns do **incremental batch**:

- **SQL:** `COPY INTO`.
- **Python:** `spark.readStream` com **Auto Loader** e um *trigger* agendado (processa o que está pendente e para).
- **Declarative Pipelines:** `CREATE OR REFRESH STREAMING TABLE`.

O Auto Loader e as streaming tables são as mesmas peças do modo streaming. A diferença entre incremental batch e streaming é só o **gatilho**: rodar sob demanda ou agendado, versus ficar sempre ligado.

> O guia de escolha é simples: se o dado não precisa chegar em segundos, o incremental batch costuma ser a melhor relação entre custo e simplicidade.

## Revisão de Delta Lake

### Ingerir arquivos como tabelas UC

O objetivo da ingestão com Standard Connectors é pegar **arquivos de fontes externas** (por exemplo, cloud object storage) e gravá-los em **Delta Lake como tabelas do Unity Catalog (UC tables)**. O arquivo de origem não é alterado: a ingestão faz uma **cópia** em formato Delta, com schema e governança.

**Delta Lake** é um protocolo open source para ler e escrever arquivos em cloud storage. As tabelas UC são o formato de tabela aberto que sustenta a arquitetura lakehouse em AWS, Azure e GCP.

### Componentes de uma tabela

Por dentro, uma tabela é uma **pasta com arquivos**:

- Os dados ficam em **arquivos Parquet**.
- Ao lado, o Delta Lake mantém o **transaction log**, em arquivos JSON.
- O log registra cada insert, update e delete como uma transação e acompanha as **versões** da tabela.

É o log que dá as funcionalidades abaixo: ele mantém o estado da tabela, permite visões consistentes e o acesso a versões antigas.

### Principais recursos

| Recurso | O que entrega |
| --- | --- |
| **ACID** | Vários usuários leem e escrevem ao mesmo tempo sem conflitos |
| **DML** | `INSERT`, `UPDATE`, `DELETE` e `MERGE` direto no lake |
| **Time travel** | Consultar ou reverter para versões anteriores (auditoria e recuperação) |
| **Schema enforcement e evolution** | Valida o schema e permite mudanças sem quebrar fluxos existentes |
| **Outros** | Batch e streaming unificados, otimizações de performance, escalabilidade |

Num data lake tradicional, alterar dado significava recriar arquivos na mão e controlar as mudanças por conta própria. No Delta, a modificação é simples e segura.

## Arquitetura medalhão

Depois de ingerido (em batch, streaming ou ambos), o dado é refinado em camadas, melhorando estrutura e qualidade **de forma progressiva**:

| Camada | Conteúdo | Uso |
| --- | --- | --- |
| **Bronze** | Dado bruto, "como veio" da fonte | Base de armazenamento de tudo; permite reprocessar |
| **Silver** | Dado limpo, transformado e enriquecido | Análise e base para as outras camadas |
| **Gold** | Dado curado e agregado, em nível de negócio | BI, relatórios, ML e IA |

A ingestão do Lakeflow Connect alimenta principalmente a **Bronze**. O processamento entre as camadas é o papel dos Declarative Pipelines.

## Ingestão a partir de cloud storage

Arquivos em CSV, JSON, Parquet e similares são comuns pela flexibilidade, mas não têm transações, versionamento nem schema forçado. O objetivo é **convertê-los em tabelas Delta**. Isso é feito com os **Standard Connectors** e três métodos: **CTAS**, **COPY INTO** e **Auto Loader**.

### CREATE TABLE AS (CTAS): batch

```sql
CREATE OR REPLACE TABLE main.bronze.vendas AS
SELECT *
FROM read_files(
  '/Volumes/main/bronze/landing/vendas/',
  format => 'csv',
  header => true
);
```

- Cria uma tabela **Delta** (o padrão) a partir dos arquivos.
- `read_files()` lê os arquivos do local indicado e devolve o resultado em forma de tabela.
- Formatos: JSON, CSV, XML, TEXT, BINARYFILE, PARQUET, AVRO, ORC.
- Detecta o formato e **infere um schema unificado** entre os arquivos. Opções específicas de cada formato podem ser passadas.
- É **batch**: cada execução lê **todos** os arquivos de novo e **não é idempotente**. O `CREATE OR REPLACE` substitui a tabela inteira pelo resultado atual da leitura. Com um `CREATE TABLE` simples, rodar de novo daria erro porque a tabela já existe.

### COPY INTO: incremental batch

```sql
CREATE TABLE IF NOT EXISTS main.bronze.vendas;

COPY INTO main.bronze.vendas
FROM '/Volumes/main/bronze/landing/vendas/'
FILEFORMAT = CSV
FORMAT_OPTIONS ('header' = 'true', 'inferSchema' = 'true', 'mergeSchema' = 'true')
COPY_OPTIONS ('mergeSchema' = 'true');
```

- Faz uma **carga em massa** dos arquivos para a tabela, que pode começar vazia.
- **Idempotente:** pula arquivos já carregados, então só os novos entram. Se `vendas_03.csv` chegar no volume e o comando rodar de novo, só ele é carregado. Também é *retriable*, podendo ser repetido em caso de falha.
- Ideal quando o local **recebe arquivos continuamente** e a execução é agendada.
- `FORMAT_OPTIONS()` controla **como ler os arquivos** (depende do formato). O `mergeSchema` aqui une os schemas dos vários arquivos lidos.
- `COPY_OPTIONS()` controla **o comportamento do comando**:
  - `mergeSchema`: evolui o schema **da tabela**. Se chegar um arquivo com a coluna nova `desconto`, ela é adicionada à tabela e as linhas antigas ficam com `NULL`. Sem a opção, o comando falha porque o schema não bate.
  - `force`: recarrega arquivos já carregados (desliga a idempotência e **duplica** as linhas desses arquivos).

### Auto Loader: incremental ou streaming

O Auto Loader processa **arquivos novos conforme chegam** no storage, sem configuração complexa, e escala para **bilhões de arquivos**. Roda sobre o Spark Structured Streaming e pode ser usado em **batch incremental ou streaming**.

**Em Python**, a ideia do fluxo é:

1. `readStream` com formato `cloudFiles` ativa o Auto Loader.
2. Define-se o formato dos arquivos e o `cloudFiles.schemaLocation`, onde ele guarda a inferência e a evolução do schema.
3. `load()` aponta para os arquivos, por exemplo um caminho em `/Volumes` (Unity Catalog).
4. Na escrita, `writeStream` usa um **checkpoint** (estado e progresso) e um *trigger* (ex.: a cada 5 segundos).
5. `toTable()` grava na tabela Delta `catalogo.schema.tabela`.

**Em SQL**, a recomendação do Databricks é usar **streaming tables** em vez de `COPY INTO`:

- Uma streaming table é uma tabela registrada no Unity Catalog com suporte a processamento incremental.
- Ao criar uma, um **pipeline é gerado automaticamente** por trás.
- Serve para carga incremental de **Kafka** e de **cloud storage**.
- Usa-se `read_files` com a palavra-chave `STREAM` no `FROM`.
- No Databricks SQL, elas rodam em **Spark Declarative Pipelines serverless**, então o workspace precisa suportar pipelines serverless. Também é possível construir seus próprios pipelines SDP, com mais recursos de otimização e monitoramento.

```sql
CREATE OR REFRESH STREAMING TABLE nova_tabela AS
SELECT *
FROM STREAM read_files(
  '/Volumes/main/bronze/landing/',
  format => 'json'
);
```

Para a maioria das ingestões de cloud storage, a recomendação é **Auto Loader com Declarative Pipelines**: juntos, carregam de forma incremental e idempotente datasets que crescem continuamente.

### Comparativo

| | **CTAS** | **COPY INTO** | **Auto Loader** |
| --- | --- | --- | --- |
| **Tipo** | Batch | Incremental batch | Incremental (batch ou streaming) |
| **Escala** | Datasets menores | Milhares de arquivos | Milhões de arquivos por hora; backfills com bilhões |
| **Interface** | Python (`spark.read`) ou SQL (CTAS) | SQL | Python (`readStream`), SQL com SDP ou streaming tables |
| **Idempotente** | Não | Sim | Sim |
| **Evolução de schema** | Manual ou inferida na leitura | Com opções (`mergeSchema`) | Automática: detecta colunas novas |
| **Latência** | Alta | Moderada (agendada) | Baixa ou alta, conforme a configuração |
| **Facilidade** | Simples | Simples, baseado em SQL | Intermediário a avançado |
| **Melhor para** | Carga pontual ou ad hoc | Jobs agendados de ingestão incremental | Quase tempo real, ou incremental com muita automação e escala |

Em resumo: **CTAS** para o pontual, **COPY INTO** para o incremental simples e **Auto Loader** quando a escala ou a latência pedem.

### Colunas de metadata na ingestão

Ao criar a tabela Bronze, dá para acrescentar a cada linha **informações do arquivo de origem**, como o nome do arquivo e a data da última modificação. Isso preserva o contexto de onde o dado veio, útil para **auditoria, linhagem e debug**.

Quem fornece isso é a coluna especial **`_metadata`**:

- É uma coluna **oculta**, disponível para todos os formatos de arquivo.
- Por ser oculta, não aparece no `SELECT *`: é preciso **selecioná-la explicitamente** na consulta de leitura.
- Dois campos comuns:

| Campo | Retorna |
| --- | --- |
| `_metadata.file_name` | Nome do arquivo de origem de cada linha |
| `_metadata.file_modification_time` | Data/hora da última modificação do arquivo |

```sql
CREATE OR REPLACE TABLE main.bronze.vendas AS
SELECT
  *,
  _metadata.file_name              AS source,
  _metadata.file_modification_time AS last_mod_time
FROM read_files(
  '/Volumes/main/bronze/landing/vendas/',
  format => 'csv',
  header => true
);
```

A tabela Bronze fica com as colunas originais mais `source` e `last_mod_time`. Se uma linha vier errada, dá para saber de qual arquivo ela saiu e quando ele foi modificado.

### Rescued data column

Na ingestão, às vezes o dado de entrada **não bate com o schema esperado**. A coluna **`_rescued_data`** garante que esses valores sejam **resgatados em vez de descartados**, evitando perda silenciosa de dado.

- Está disponível com `read_files()`, `spark.read` e Auto Loader (ou seja, também em CTAS e `COPY INTO`).
- Os valores que não batem com o schema são guardados como uma **string em formato JSON** na coluna `_rescued_data`, junto com o caminho do arquivo (`_file_path`).
- Linhas **sem divergência** entram normalmente e ficam com `_rescued_data = null`.
- Depois da ingestão, dá para consultar essa coluna, investigar e corrigir.

**Exemplo:** os arquivos têm as colunas `users` e `cost`, e a tabela espera `users` como `STRING` e `cost` como `BIGINT`.

| users | cost (no arquivo) | Resultado |
| --- | --- | --- |
| Peter | `$100` | `users = Peter`, `cost = null`; o valor `$100` vai para `_rescued_data` como JSON |
| zebi | `300` | Linha lida sem problemas, `_rescued_data = null` |

Na primeira linha, `"$100"` não é um `BIGINT`, então não entra em `cost`. Em vez de se perder, fica em `_rescued_data`, com algo como `{"cost":"$100","_file_path":"..."}`.

```sql
-- linhas que tiveram algum valor resgatado
SELECT *
FROM main.bronze.vendas
WHERE _rescued_data IS NOT NULL;
```

## Ingestão de dados semi-estruturados: JSON

Ingerir JSON permite transformar uma entrada complexa e aninhada em tabelas Delta estruturadas. Entender o formato ajuda a decidir como fazer o parsing.

### Estrutura do JSON

- **Objeto:** conjunto de pares chave-valor entre chaves `{ }`.
- **Valor:** string, número, booleano, `null`, **array** (`[ ]`) ou outro objeto (**objeto aninhado**).

### Colunas com JSON

Depois da ingestão, é comum uma coluna guardar **JSON como texto**. Isso acontece quando o JSON não foi totalmente parseado na ingestão, ou quando ele vem embutido em outro campo (uma mensagem de log, por exemplo).

```json
{"name": "John Doe", "age": 35,
 "address": {"city": "Anytown", "state": "CA"},
 "children": [{"name": "Owen", "age": 10}, {"name": "Eva", "age": 8}]}
```

Há três abordagens para trabalhar com isso:

| Abordagem | Como é | Prós e contras |
| --- | --- | --- |
| **STRING** | JSON guardado como texto | Aceita qualquer JSON, mas é o **menos performático** |
| **STRUCT** | JSON parseado com um schema definido | Impõe estrutura e tipos; consulta **mais eficiente** |
| **VARIANT** | Tipo novo para dado semi-estruturado | Flexível, **sem schema prévio**, e melhor desempenho que STRING e STRUCT |

### STRING: acesso com `:`

Dá para extrair campos direto do texto com a sintaxe de dois pontos:

```sql
SELECT json_column:name,
       json_column:address.city
FROM tabela;
```

### STRUCT: tipar o JSON

Converter para `STRUCT` exige um schema que diga como interpretar cada parte do JSON. O mapeamento do exemplo acima:

- `STRUCT<...>` é o contêiner de toda a estrutura.
- `name` é `STRING` e `age` é `INT`.
- `address` é um objeto, logo um `STRUCT` aninhado com `city` e `state`.
- `children` é um array de objetos, logo `ARRAY<STRUCT<...>>`.

```sql
STRUCT<
  name: STRING,
  age: INT,
  address: STRUCT<city: STRING, state: STRING>,
  children: ARRAY<STRUCT<name: STRING, age: INT>>
>
```

Em vez de escrever o schema à mão, são dois passos:

**1. `schema_of_json`** deriva o schema a partir de um JSON de exemplo:

```sql
SELECT schema_of_json('{"name": "John Doe", "age": 35, "address": {"city": "Anytown", "state": "CA"}, "children": [{"name": "Owen", "age": 10}]}');
```

O retorno é o `STRUCT<...>` acima, pronto para ser reaproveitado.

**2. `from_json`** aplica o schema à coluna e devolve uma coluna `STRUCT`:

```sql
SELECT from_json(json_column, 'STRUCT<name: STRING, age: INT, address: STRUCT<city: STRING, state: STRING>, children: ARRAY<STRUCT<name: STRING, age: INT>>>') AS struct_column
FROM tabela;
```

Depois disso os campos são acessados como colunas comuns: `struct_column.address.city`.

### VARIANT

É a abordagem mais nova para JSON no Databricks:

- Guarda qualquer tipo de dado, inclusive JSON, e se adapta a formatos diferentes **sem schema rígido**.
- Tem desempenho melhor que STRING e STRUCT.
- Na aula estava em **public preview** (2025 Q2), com a GA ainda por vir.

> **Nota:** como é um recurso novo, vale conferir na documentação se já saiu do preview.

## Outros recursos de integração

Além dos conectores, o Databricks tem recursos que ampliam integração, compartilhamento e colaboração. Eles ficam fora do foco do curso, mas valem o mapa:

| Recurso | O que faz |
| --- | --- |
| **Lakehouse Federation** | Consulta fontes externas **sem mover o dado** |
| **Zerobus** | Envia eventos direto para tabelas Delta, sem message bus no meio (parte do Lakeflow Connect) |
| **Delta Sharing** | Protocolo aberto para compartilhar dados entre organizações e plataformas, sem cópia |
| **Databricks Marketplace** | Troca de data products, construída sobre o Delta Sharing |

**Lakehouse Federation** é útil quando mover o dado não compensa:

- relatórios ad hoc;
- provas de conceito;
- fase exploratória de novos pipelines ETL ou relatórios;
- apoio a workloads durante uma migração incremental.

### Databricks Marketplace

Marketplace aberto para dados, analytics e IA, movido pelo padrão open source **Delta Sharing**. Troca **datasets, notebooks, dashboards, modelos de ML e solution accelerators**.

Para usar um ativo, são três passos: abrir o Marketplace na barra lateral do workspace, buscar o ativo (dá para começar pelos oferecidos pelo próprio Databricks) e clicar em **Get instant access**. Depois disso:

- O ativo é adicionado ao **Unity Catalog** automaticamente.
- O acesso é imediato, sem fluxo de aprovação para ativos gratuitos.
- Dá para consultar por SQL, notebooks ou dashboards.
- O dado continua **vivo e atualizado via Delta Sharing**, sem cópia.

## Ingestão em tabelas Delta existentes: MERGE INTO

Os métodos anteriores adicionam dado novo. Quando é preciso **atualizar, inserir e apagar** numa tabela que já existe com base em outra, o comando é o **`MERGE INTO`**: ele aplica tudo isso numa **única operação atômica**.

Ele aceita enforcement e evolução de schema e permite ações diferentes conforme a linha tenha ou não correspondência entre origem (*source*) e destino (*target*):

| Situação | Ações possíveis |
| --- | --- |
| **Matched** (existe nos dois) | `UPDATE` ou `DELETE` |
| **Not matched by target** (só na origem) | `INSERT` |
| **Not matched by source** (só no destino) | `UPDATE` ou `DELETE` |

É por isso que o `MERGE INTO` é a base para **dimensões que mudam lentamente (SCD)**, **cargas incrementais** e cenários de **CDC**.

### Exemplo

A `target_table` tem os usuários `peter` e `zebi`, ambos `current`. A `source_table` traz três mudanças:

| users | email | status | O que fazer |
| --- | --- | --- | --- |
| peter | peter@email.com | `delete` | remover do destino |
| zebi | zebi@other.com | `update` | atualizar o e-mail |
| samarth | samarth@other.com | `new` | inserir como linha nova |

```sql
MERGE INTO target_table target
USING source_table source
ON target.users = source.users
WHEN MATCHED AND source.status = 'update' THEN
  UPDATE SET
    target.email  = source.email,
    target.status = source.status
WHEN MATCHED AND source.status = 'delete' THEN
  DELETE
WHEN NOT MATCHED THEN
  INSERT (users, email, status)
  VALUES (source.users, source.email, source.status);
```

Lendo em partes:

1. `MERGE INTO ... USING ...`: declara o destino e a origem.
2. `ON`: a condição que define quando duas linhas são "a mesma".
3. `WHEN MATCHED AND ... 'update'`: se existe nos dois e a origem pede atualização, atualiza.
4. `WHEN MATCHED AND ... 'delete'`: se existe nos dois e a origem pede remoção, apaga.
5. `WHEN NOT MATCHED`: se só existe na origem, insere.

Resultado: `peter` some, `zebi` fica com o e-mail novo e `samarth` entra. Tudo numa operação só.

> O SQL da aula é uma versão resumida, com a lista de colunas do `INSERT` incompleta. O de cima é uma adaptação minha, usando `users` como chave.

## Demo

*(a anotar)*
