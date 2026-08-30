---
title: "Data Quality Fundamentals - Capítulo 3"
author: "vapb"
description: "Resumo do capítulo 3 de Data Quality Fundamentals: coleta de dados (logs de aplicação, respostas de API, dados de sensores), limpeza de dados e processamento batch vs. stream."
date: 2026-08-30
tags: ["data-quality-fundamentals"]
toc: false
---

## Introdução

O Capítulo 3, "Collecting, Cleaning, Transforming, and Testing Data", parte de uma constatação simples: **o dado no ponto de entrada do pipeline é o mais bruto que ele jamais será**, carregando todo o ruído e a irregularidade do mundo real que está sendo modelado. Esse dado pode vir de logs de aplicação, cliques de usuário ou sensores ao vivo, e tende a ser altamente heterogêneo — estruturado e não estruturado ao mesmo tempo —, o que já abre espaço para problemas mais adiante no pipeline.

**A escolha da fonte de dados raramente é do engenheiro de dados**: ela costuma depender de um objetivo de negócio ou de uma ferramenta upstream, como um serviço de analytics ou uma API. O capítulo organiza essas fontes em três categorias.

## Coletando dados

Três fontes cobrem a maior parte da coleta de dados analíticos:

- **Logs de aplicação**: registram ações dentro de um software. **Diferente de logs de sistema, o que entra ou some de um log é decisão do próprio time de desenvolvimento** — não é um histórico exaustivo do uso da aplicação. Costumam ser texto (ASCII/binário) com timestamp e nível (`INFO`, `WARN`, `ERROR`), e servem sobretudo a dois propósitos: **diagnóstico** (uma pergunta pontual, respondida por uma fração específica dos logs de erro/aviso) ou **auditoria** (histórico de uso, construído sobre agregações de logs `INFO`).
- **Respostas de API**: diferente de um log (fluxo de texto livre), uma resposta de API é um objeto estruturado ou semiestruturado — JSON é o formato mais comum. Costuma vir com um **código de resposta** (os HTTP são os mais conhecidos), que pode ser o dado relevante em si (ex.: taxa de erro 500) ou só um detalhe descartável se o que importa é o corpo da resposta.
- **Dados de sensores**: vêm de dispositivos com lógica interna simples (IoT, equipamento de pesquisa), então tendem a ser mais ruidosos e, principalmente, **falham silenciosamente** — um sensor quebrado não avisa `"ERROR"`, só manda valores absurdos ou para de mandar qualquer coisa, o que exige monitorar volume e intervalo entre lotes em vez de confiar em mensagens de erro.

## Limpando dados

Depois de coletado, o próximo passo é a limpeza: **remover dados imprecisos ou não representativos de um conjunto de dados que, de outra forma, seria utilizável.** O livro lista seis frentes recorrentes — remoção de outliers, poda de features irrelevantes, normalização, reconstrução de valores ausentes (interpolação/extrapolação), conversão de timestamps para UTC e coerção de tipos. **O destaque fica com fuso horário**: sem um padrão comum (UTC, que é um padrão de tempo, não um fuso), é impossível saber a ordem real entre eventos registrados em locais diferentes, e boa parte dos bugs de software (o Y2K sendo o exemplo mais famoso) remonta justamente a confusões desse tipo.

## Batch vs. Stream Processing

Existem duas formas principais de coletar dados analíticos: **processamento em batch**, que agrupa grandes volumes de dados em pacotes discretos ao longo de um período de tempo, e **processamento em stream**, que processa os dados quase imediatamente.

Um exemplo clássico é o processamento de pagamentos por cartão de crédito: do lado do lojista, a cobrança pode levar horas ou dias para liquidar (batch); do lado da operadora do cartão, transações potencialmente fraudulentas podem ser identificadas e alertadas quase que instantaneamente (stream) — e se esse dado não estiver atualizado, a detecção de fraude atrasa ou falha.

As alternativas: para processamento em batch, **Apache Hadoop** é um dos frameworks open source mais populares, dividindo arquivos em pacotes menores distribuídos entre nós de um cluster; alternativas gerenciadas incluem Google BigQuery, Snowflake, Microsoft Azure e Amazon Redshift. Para stream processing, as opções open source mais comuns vêm do ecossistema Apache — Spark, Kafka, Flink, Storm, Samza e Flume —, com **Spark** usando uma abordagem de micro-batch (dividindo o stream em pacotes pequenos) e **Kafka** analisando eventos conforme eles acontecem, mais próximo do tempo real; alternativas gerenciadas incluem Databricks, Cloudera e Azure.

## Qualidade de dados em stream processing

A diferença central entre batch e stream está no volume de dado processado por lote e na velocidade do processamento: batch prioriza reunir o máximo de dado possível, mesmo com atraso; stream prioriza velocidade, ao custo de alguma perda. **Por isso, a qualidade de dados tende a ser mais alta em sistemas batch, e a margem de erro cresce quando o dado é processado em tempo real.**

Um exemplo: times de marketing posicionam anúncios com base no comportamento do usuário, usando dados que fluem em tempo real entre produtos, CRMs e plataformas de anúncio. Uma simples mudança de schema numa API pode gerar dado incorreto, levando a gasto excessivo, receita perdida ou anúncios irrelevantes.

Tradicionalmente, qualidade de dados era garantida via **testes**: o time ingeria dados em batch, esperava que chegassem no intervalo definido (a cada 12h ou 24h, por exemplo) e escrevia testes com base em suposições sobre os dados — mas é impossível prever todos os resultados possíveis. Um novo erro de qualidade surgia, o time corria para investigar a causa raiz antes que o problema afetasse tabelas e usuários downstream, corrigia o problema e só então escrevia um teste para evitar que se repetisse. **Essa abordagem é difícil de escalar e, segundo o livro, cobre só cerca de 20% dos possíveis problemas de qualidade de dados — os "known unknowns".**

Quando, em meados dos anos 2010, empresas passaram a ingerir dados em tempo real (Kinesis, Kafka, Spark Streaming), **aplicaram essa mesma abordagem de teste — só que agora sobre dados que mudam a cada minuto ou segundo, não a cada 12h.** Se garantir confiabilidade já é difícil em batch, escalar testes para um fluxo contínuo é bem mais complicado, e um campo ausente, incorreto ou atrasado pode se propagar rápido pelos sistemas downstream sem que ninguém perceba a tempo. **Frameworks tradicionais (testes unitários, funcionais, de integração) cobrem o básico, mas não escalam para dados difíceis de prever e que evoluem em tempo real** — exigindo repensar qualidade de dados especificamente para stream processing.

### AWS Kinesis

O **Kinesis** é o serviço de streaming serverless da Amazon, com capacidade que escala sob demanda (sem precisar provisionar recursos antecipando picos de volume). Pode capturar dados de outros serviços AWS, microsserviços, logs de aplicação, dados mobile e de sensores, escalando para gigabytes de dados por segundo. Vantagens:

- **Disponibilidade sob demanda**: escala automaticamente com picos de volume, sem exigir um engenheiro dedicado a gerenciar cluster e partições.
- **Custo proporcional ao uso**, como em qualquer arquitetura serverless.
- **SDK mais abrangente**: suporta Java, Android, .NET e Go (o Kafka, por comparação, suporta só Java).
- **Integração nativa com o stack AWS** (S3, Redshift etc.), bem mais simples do que com alternativas de terceiros ou open source.

### Apache Kafka

O **Kafka** é uma plataforma open source de streaming de eventos; o **Kafka Streams** é a biblioteca cliente para consumir e produzir dados a partir de clusters Kafka, com latências tão baixas quanto 2 milissegundos (limitadas pela rede). Vantagens:

- **Comunidade open source** ativa, com fóruns, meetups e material de referência.
- **Mais configurável** que soluções gerenciadas como o Kinesis — inclusive o período de retenção dos dados pode ser definido manualmente (no Kinesis é fixo em 7 dias).
- **Throughput maior**: em testes, o Kafka sustentou até 30 mil registros/segundo, contra poucos milhares no Kinesis.

**A escolha entre os dois depende do time**: Kinesis favorece times menores que querem valor rápido com uma solução gerenciada; Kafka tende a compensar para times maiores com requisitos mais específicos, dispostos a lidar com uma curva de aprendizado maior. Em ambos os casos, dado tende a ser mais propenso a erro quanto mais em tempo real ele for — por isso, para casos de uso analíticos (em oposição a casos como corrida por app ou detecção de fraude em tempo real), **batch continua sendo o método preferido.**

Seja a coleta em batch ou streaming, o próximo passo é dar sentido ao dado por meio de transformações — e, na jornada de qualidade de dados, isso costuma começar pela **normalização de dados**.

## Normalizando dados

A **normalização** é a primeira camada de transformação operacional: um programa que move dado de um ou mais formatos de origem para um formato de destino. Como ela acontece sobre dado de entrypoint — onde ruído e heterogeneidade estão no auge —, essa etapa tem desafios próprios.

### Lidando com fontes heterogêneas

Dado chegando na normalização costuma ter algumas características em comum:

- **Otimizado para latência**: dado de streaming é entregue assim que criado, o que — dado o trade-off de throughput vs. latência já discutido — significa **esperar lotes incompletos**, empurrados adiante mesmo sem ter chegado ao seu estado final.
- **Formato não hierárquico**: em vez do regime limpo de warehouse (schema + tabela), o dado costuma estar "despejado" num repositório central, como um bucket S3.
- **Formato bruto**: reflete o formato original de origem — não vale a pena converter log de aplicação ou dado de sensor para tabular nessa etapa, seria caro e desnecessário.
- **Campos opcionais**: diferente do warehouse (que exige valor pra todo campo do schema), formatos brutos como JSON toleram campos ausentes — e cabe a quem consome inferir o que essa ausência significa (`NULL`? zero? o timestamp atual?).

Essas características explicam por que **data lakes** costumam ser o destino preferido pra dado de entrypoint: têm restrições bem mais soltas do que um warehouse. É comum, então, ver serviços de streaming (Kinesis, Kafka) despejando dado semiestruturado num lake, e uma primeira camada de transformações operacionais — funções **AWS Lambda** no caso do Kinesis, ou **consumers** no caso do Kafka Streams — elevando pedaços desse dado para forma estruturada no warehouse (o **AWS Glue** ajuda quando essa movimentação acontece em intervalos regulares).

### Checagem de schema e coerção de tipo

**Checagem de schema** valida se a estrutura do dado é a esperada: os campos necessários estão presentes, no formato certo? Mudança de schema é uma das principais causas de quebra de dado — um campo pode sumir por uma atualização de versão de API, ou ser renomeado "pra ficar mais consistente", e de repente scripts que dependiam dele param de funcionar mesmo que "o dado seja o mesmo". Por isso vale manter registro dos schemas esperados e sinalizar mudanças de forma visível, em vez de descobri-las só quando algo quebra.

**Coerção de tipo** é converter dado que não está no formato esperado para o formato certo (também chamado de *casting*). Pode ser sutil e traiçoeira: converter a string `"4"` para inteiro `4` não é problema, mas converter o float `4.00` para inteiro já descarta precisão — e converter `4.99` para inteiro `4` é **truncamento, não arredondamento** (não é o arredondamento que se aprende na escola). São detalhes que parecem básicos, mas geram bugs difíceis de rastrear.

### Ambiguidade sintática vs. semântica

**Ambiguidade sintática** é confusão na forma como o dado é apresentado: a mesma métrica aparecendo sob nomes de campo diferentes em lugares diferentes (`clickthrough_annual` vs. `clickthrough_rate_yr`), ou como inteiro no lake e float no warehouse.

**Ambiguidade semântica** é mais perigosa: confusão sobre o *propósito* do dado. Um campo pode existir pra medir performance de pipeline, mas um analista de negócio olha o nome vago, assume que mede outra coisa e o coloca num dashboard — o dado passa a representar errado uma métrica de negócio importante, mesmo sem nenhum erro técnico envolvido. **Documentação proativa** é a defesa principal contra esse tipo de ambiguidade, que tende a se espalhar rápido conforme o time cresce.

## Gerenciando transformações operacionais no Kinesis e no Kafka

Transformações operacionais lidam com dado em estado bruto, mas isso não significa operar "às cegas": as próprias ferramentas de streaming oferecem alertas e checagens de qualidade prontas.

No **Kinesis**, essas checagens são configuradas via funções **AWS Lambda** (escritas em .NET, Go, Java, Node.js, Python ou Ruby), conectadas em "Connect to a Source" → "Record pre-processing with AWS Lambda" no console do Kinesis — a Lambda roda antes de qualquer SQL da aplicação ou snapshot de schema.

No **Kafka**, a curva de aprendizado é maior, mas a configurabilidade também: distribuidores gerenciados como Confluent, Instaclustr e AWS facilitam a operação e já cobrem parte da prevenção de *data downtime* — o Confluent, por exemplo, oferece um **schema registry**, que permite checar e versionar schemas para evitar problemas de qualidade. Por padrão, métricas de streaming são reportadas via **JMX** (visualizáveis com JConsole, ou acessadas via `KafkaStreams#metrics()`).

**Um ponto importante**: como essa etapa prioriza latência sobre throughput, as checagens que fazem sentido aqui também seguem essa lógica — evitar verificações pesadas como detecção de *data drift*, e focar em checagens de baixa latência, como comparar schema histórico com o que está chegando ou acompanhar o volume de bytes lido ao longo do tempo. **Boa parte desse "monitoramento" nem é sobre qualidade de dado propriamente dita** — é sobre garantir que o dado que chega não estoure a capacidade, o armazenamento ou a memória disponíveis.

## Rodando transformações analíticas de dados

**Transformações analíticas** são as feitas sobre dado analítico — o termo também vale pra camada de integração entre fonte operacional e analítica, como um AWS Glue configurado entre um lake em S3 e um warehouse Redshift. Como dado analítico difere do operacional em vários pontos, os cuidados na hora de transformá-lo também mudam.

### Qualidade de dados no ETL

**ETL** (*extract-transform-load*) é o processo mais comum de transformação analítica, em três passos:

1. **Extract**: dado bruto é exportado de fontes upstream (servidores MySQL/NoSQL, CRM, arquivos brutos num lake) para uma área de staging.
2. **Transform**: a parte mais pesada — o dado em staging é combinado e processado conforme a especificação de quem projeta o pipeline. Pode ser trivial (praticamente uma cópia) ou bem intenso.
3. **Load**: o dado já transformado sai do staging e vai para o destino final, geralmente uma tabela específica num warehouse.

### Qualidade de dados durante a transformação

A diferença entre **ETL** e **ELT** (*extract-load-transform*) está em onde a transformação acontece: no ETL, o dado passa por staging antes de chegar ao destino; no ELT, ele é carregado direto no sistema alvo e só então transformado. **O ETL dá a chance de validar o dado antes de ele chegar em produção; o ELT é mais rápido, mas tende a sair com qualidade pior se não vier acompanhado de testes e monitoramento à parte.**

Motivos comuns para transformar dado de origem:

- Renomear campos pra bater com o schema do destino.
- Filtrar, agregar, resumir, deduplicar ou de alguma forma limpar e consolidar o dado.
- Converter tipo e unidade — por exemplo, padronizar campos de moeda diferentes tudo em dólar e em float.
- Criptografar campos sensíveis, por exigência regulatória ou do setor.
- E, o mais relevante aqui: **rodar auditorias de governança ou checagens de qualidade de dados** nessa mesma etapa.

## Alerting e testes

Ferramentas de ETL/ELT (dbt, WhereScape, Informatica) também quebram, então rodar isso em produção exige um sistema robusto de teste e alerta. **Testar dado é validar as suposições que o time faz sobre ele, antes ou durante a produção** — checagens básicas de unicidade e não-nulidade já cobrem boa parte das suposições que se faz sobre um dado de origem.

Os testes de qualidade mais comuns:

| Teste | Pergunta que responde |
|---|---|
| Valores nulos | Algum valor está `NULL`? |
| Volume | Chegou dado? Chegou volume demais ou de menos? |
| Distribuição | Os valores de uma coluna estão dentro da faixa esperada? |
| Unicidade | Algum valor está duplicado? |
| Invariantes conhecidos | Duas grandezas relacionadas continuam consistentes entre si — ex.: lucro é sempre receita menos custo? |

O fluxo básico pra rodar esses testes: carregar o dado já transformado numa tabela de staging temporária, e rodar os testes contra ela pra confirmar que está dentro dos limites exigidos em produção. **Se um teste falha, um alerta é disparado pro responsável pelo asset e o pipeline não roda** — o que evita que o problema chegue a impactar usuários ou sistemas downstream. Isso pode ser feito antes da transformação e depois de cada etapa dela.

O livro destaca três ferramentas open source pra isso: **dbt tests**, **Great Expectations** e **Deequ**.

### dbt

O `dbt run` executa as transformações dos models via SQL; o `dbt test` roda os testes definidos sobre esses models. Um teste dbt em SQL segue um padrão simples: você escreve uma query que identifica a condição que **não** deveria acontecer, e o teste "afirma" que essa query não deve retornar nenhuma linha — se retornar algo, o teste falha.

Existem dois tipos:

- **Singular**: SQL isolado, específico de um model, salvo no diretório de testes. Por exemplo, uma query que soma os valores de pagamento por pedido e falha se o total ficar negativo.
- **Genérico**: um teste "templatizado", parametrizável (recebe nome de coluna, thresholds etc.) e aplicado a diferentes models via arquivo `.yml`. O dbt já vem com quatro testes genéricos prontos: `unique`, `not_null`, `accepted_values` (valor precisa estar num conjunto finito) e `relationships` (integridade referencial entre tabelas, tipo IDs).

Limitações apontadas pelo livro:

- **Dívida técnica**: testes são mantidos manualmente como código, e models de ELT tendem a "andar" conforme o negócio muda — testes complexos garantem qualidade, mas custam quase tanto quanto manter os models em si.
- **Fadiga de teste e conhecimento tácito**: um teste só é útil se for significativo. Se alguém escreve um teste mal fundamentado e, meses depois, outra pessoa não entende por que ele existe, a tendência é simplesmente remover o teste pra destravar o CI — nesse ponto, o teste não ajuda em nada e só atrapalha.
- **Visibilidade limitada**: um teste pode falhar por um problema bem upstream (ex.: uma Lambda do Glue mal configurada) que já corrompeu o dado antes dele chegar ao warehouse. O teste avisa que algo está errado, mas não aponta a causa — ainda é preciso investigar o resto do stack, porque o esquema de teste do dbt não é fim a fim.

### Great Expectations

Ferramenta open source em **Python**, mais extensível que o dbt por não depender de um framework de transformação específico. Testes são escritos como asserções — por exemplo, garantir que uma coluna de CEP só tenha valores entre 1 e 99999 — e podem rodar sobre volumes bem diferentes de dado, de um lote pequeno até uma transformação inteira. Depois de rodar, gera um relatório legível chamado **Data Doc**, com taxa de falha por teste e amostragem das linhas que falharam.

Vantagens: **fácil de usar** (pacote Python, CLI, integra com Jupyter, e um único arquivo `.yaml` centraliza a configuração mesmo com várias fontes de dado diferentes) e **integração com Slack** (alertas configuráveis, também por e-mail).

Limitações: **restrito a Python** (se o stack do time é majoritariamente SQL ou R, não ajuda tanto) e **desacoplado da transformação/orquestração** — ao contrário do dbt, onde teste e model vivem juntos, aqui é uma ferramenta à parte, com curva de aprendizado própria.

### Deequ

Biblioteca open source da **AWS**, construída sobre **Apache Spark** — testa qualquer coisa que caiba num Spark DataFrame (CSV, JSON, tabela de warehouse, log de aplicação), com um pacote **PyDeequ** pra quem prefere Python. Funciona de forma parecida com dbt e Great Expectations (afirma condições e retorna linhas/lotes que falham), mas como se integra nativamente ao pipeline de streaming/transformação da AWS, consegue **"colocar em quarentena"** dado ruim antes que ele alimente fontes upstream.

O ponto de entrada é a classe `VerificationSuite`: associa o dado a testar com `.onData()` e empilha checagens com `.addCheck()` — tamanho esperado, colunas não-nulas, unicidade, valores dentro de um conjunto aceito, quantis dentro de uma faixa etc.

Vantagens: **integração nativa com AWS** (Glue, bem documentado), **alta escalabilidade** (roda sobre Scala, aproveitando paralelismo e DataFrames já pensados pra big data), **cálculo com estado** (recalcula métricas de forma incremental à medida que mais dado chega, em vez de reprocessar tudo — útil pra volumes grandes de streaming) e **detecção de anomalia embutida**, mais sofisticada que a do Great Expectations (média e desvio de métricas ao longo do tempo, não só threshold fixo).

Limitações: **curva de aprendizado do Scala** (pouco amigável pra quem não é do mundo de engenharia de dados), **pouco adequado a teste de integração** (roda sobre qualquer lote isolado, sem a mesma integração natural do dbt com o pipeline inteiro) e **UI pouco intuitiva** (sem nada parecido com o Data Doc do Great Expectations).

Teste é uma peça importante da qualidade de dados, mas não a única medida proativa — a próxima frente do capítulo é usar o **Apache Airflow** pra construir *circuit breakers* e outras checagens na camada de orquestração.

###################### EM ANDAMENTO