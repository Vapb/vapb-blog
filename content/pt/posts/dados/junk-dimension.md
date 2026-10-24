---
title: "Junk Dimension: o que fazer com flags e indicadores soltos no modelo dimensional"
author: "vapb"
description: "O que é uma junk dimension na modelagem dimensional de Kimball, que problema ela resolve, como construir (com SQL) e como fica a tabela fato antes e depois."
date: 2026-10-24
tags: ["data-engineering", "data-warehouse", "modelagem-dimensional", "kimball", "sql"]
toc: true
aliases: ["/posts/junk-dimension/"]
---

## Introdução

Quando você modela uma tabela fato de pedidos, quase sempre sobra um punhado de atributos pequenos que **não pertencem a nenhuma dimensão óbvia**: um flag de "pedido presente?", o tipo de pagamento, o canal de venda, se usou cupom, se a entrega foi expressa. Cada um tem poucos valores possíveis, não tem hierarquia e não justifica uma tabela própria.

As saídas intuitivas são duas, e as duas são ruins:

- **Deixar tudo na tabela fato** como colunas de texto, o que deixa a fato larga, repetitiva e cheia de strings.
- **Criar uma dimensão para cada um**, o que enche o modelo de tabelinhas com 2 ou 3 linhas e a fato de chaves estrangeiras.

A **junk dimension** (dimensão lixo) é a terceira saída, proposta por Ralph Kimball: **juntar esses atributos de baixa cardinalidade em uma única dimensão**, e a fato passa a guardar só uma chave para ela. O nome é feio, mas a ideia é boa: o "lixo" é tudo o que sobra e não tem onde morar.

## O problema: atributos órfãos na tabela fato

Vamos usar um exemplo de e-commerce. A fato de pedidos tem as métricas (valor, quantidade) e as chaves das dimensões que fazem sentido de verdade (data, cliente, produto). Mas o sistema de origem também traz estes campos:

| Atributo | Valores possíveis |
|---|---|
| `canal_venda` | Site, App, Loja física |
| `tipo_pagamento` | Cartão, Pix, Boleto |
| `entrega_expressa` | Sim, Não |
| `presente` | Sim, Não |
| `cupom_usado` | Sim, Não |

Nenhum deles é um "cliente" ou um "produto". São características **do pedido**, pequenas e sem relação forte entre si.

### Opção 1: tudo na fato

```sql
CREATE TABLE fato_pedidos (
    data_key          INT,
    cliente_key       INT,
    produto_key       INT,
    canal_venda       VARCHAR(20),   -- 'Site', 'App', 'Loja física'
    tipo_pagamento    VARCHAR(20),   -- 'Cartão', 'Pix', 'Boleto'
    entrega_expressa  BOOLEAN,
    presente          BOOLEAN,
    cupom_usado       BOOLEAN,
    valor_total       NUMERIC(12,2),
    quantidade        INT
);
```

Resultado: cada linha repete as mesmas strings milhões de vezes, e a fato (que é a maior tabela do DW) fica desnecessariamente larga. Filtrar por "pedidos de Pix com cupom" vira um `WHERE` em várias colunas de texto.

### Opção 2: uma dimensão para cada atributo

```sql
-- 5 tabelas minúsculas
dim_canal_venda       (3 linhas)
dim_tipo_pagamento    (3 linhas)
dim_entrega_expressa  (2 linhas)
dim_presente          (2 linhas)
dim_cupom             (2 linhas)
```

Agora a fato tem **cinco FKs a mais**, o diagrama vira uma aranha e quem escreve a query precisa de cinco `JOIN`s só para chegar em atributos triviais.

## A solução: uma junk dimension

A ideia é **uma única tabela, onde cada linha é uma combinação de valores** desses atributos. A fato guarda apenas a chave dessa combinação.

```sql
CREATE TABLE dim_pedido_perfil (
    perfil_key        INT PRIMARY KEY,   -- surrogate key
    canal_venda       VARCHAR(20) NOT NULL,
    tipo_pagamento    VARCHAR(20) NOT NULL,
    entrega_expressa  VARCHAR(3)  NOT NULL,   -- 'Sim' / 'Não'
    presente          VARCHAR(3)  NOT NULL,
    cupom_usado       VARCHAR(3)  NOT NULL
);
```

Como fica o conteúdo (parte das linhas, com os nomes das colunas abreviados):

| perfil_key | canal | pagamento | expressa | presente | cupom |
|---:|---|---|---|---|---|
| 1 | Site | Cartão | Não | Não | Não |
| 2 | Site | Cartão | Não | Não | Sim |
| 3 | Site | Cartão | Não | Sim | Não |
| 4 | Site | Cartão | Não | Sim | Sim |
| 5 | Site | Cartão | Sim | Não | Não |
| ... | ... | ... | ... | ... | ... |
| 38 | App | Pix | Sim | Não | Sim |
| ... | ... | ... | ... | ... | ... |

Cada linha é **um "perfil" possível de pedido**. O pedido de um cliente que comprou pelo App, pagou no Pix, com entrega expressa, sem presente e usando cupom aponta para a linha 38, e pronto.

### Antes e depois da tabela fato

**Antes** (atributos soltos na fato):

| pedido | canal | pagamento | expressa | presente | cupom | valor |
|---:|---|---|---|---|---|---:|
| 1001 | App | Pix | Sim | Não | Sim | 249,90 |
| 1002 | Site | Cartão | Não | Sim | Não | 89,00 |
| 1003 | Site | Boleto | Não | Não | Não | 249,90 |

**Depois** (uma FK para a junk dimension):

| pedido | **perfil_key** | valor |
|---:|---:|---:|
| 1001 | 38 | 249,90 |
| 1002 | 3 | 89,00 |
| 1003 | 17 | 249,90 |

Cinco colunas de texto/flag viraram **um inteiro**. A fato fica menor, mais rápida de varrer e com um modelo mais limpo.

```sql
CREATE TABLE fato_pedidos (
    data_key     INT NOT NULL,
    cliente_key  INT NOT NULL,
    produto_key  INT NOT NULL,
    perfil_key   INT NOT NULL REFERENCES dim_pedido_perfil (perfil_key),
    valor_total  NUMERIC(12,2),
    quantidade   INT
);
```

### Como consultar

Para o analista, a dimensão é só mais um `JOIN`, e filtrar por qualquer combinação dos atributos fica simples:

```sql
-- Faturamento por canal, só de pedidos pagos com Pix e cupom
SELECT
    p.canal_venda,
    SUM(f.valor_total) AS faturamento
FROM fato_pedidos f
JOIN dim_pedido_perfil p ON p.perfil_key = f.perfil_key
WHERE p.tipo_pagamento = 'Pix'
  AND p.cupom_usado    = 'Sim'
GROUP BY p.canal_venda;
```

Uma ferramenta de BI também ganha: em vez de cinco filtros espalhados, aparece uma pasta "Perfil do pedido" com todos os atributos juntos.

## Como construir

Existem duas estratégias, e a escolha depende de quantas combinações existem.

### Estratégia 1: produto cartesiano (todas as combinações)

Gera **todas** as combinações possíveis de uma vez, antes de carregar qualquer fato. Faz sentido quando o total é pequeno e fechado. Aqui são 3 × 3 × 2 × 2 × 2 = **72 linhas**.

```sql
INSERT INTO dim_pedido_perfil
SELECT
    ROW_NUMBER() OVER (ORDER BY c.v, t.v, e.v, g.v, u.v) AS perfil_key,
    c.v, t.v, e.v, g.v, u.v
FROM (VALUES ('Site'), ('App'), ('Loja física'))  AS c(v)
CROSS JOIN (VALUES ('Cartão'), ('Pix'), ('Boleto')) AS t(v)
CROSS JOIN (VALUES ('Não'), ('Sim')) AS e(v)
CROSS JOIN (VALUES ('Não'), ('Sim')) AS g(v)
CROSS JOIN (VALUES ('Não'), ('Sim')) AS u(v);
```

**Vantagem:** a carga da fato vira só um lookup, sem se preocupar em inserir dimensão nova. 

**Desvantagem:** gera combinações que nunca acontecem (ex.: "Loja física + Pix + Entrega expressa" pode ser impossível no negócio), e a tabela explode se alguém adicionar mais um atributo.

### Estratégia 2: só as combinações que existem (a mais comum)

A dimensão cresce **conforme os dados chegam**: no ETL, olhamos as combinações presentes no lote e inserimos só as que ainda não existem.

```sql
-- 1) Combinações distintas do lote que ainda não estão na dimensão
INSERT INTO dim_pedido_perfil
    (perfil_key, canal_venda, tipo_pagamento, entrega_expressa, presente, cupom_usado)
SELECT
    (SELECT COALESCE(MAX(perfil_key), 0) FROM dim_pedido_perfil)
        + ROW_NUMBER() OVER (ORDER BY s.canal_venda, s.tipo_pagamento,
                                      s.entrega_expressa, s.presente, s.cupom_usado),
    s.canal_venda, s.tipo_pagamento, s.entrega_expressa, s.presente, s.cupom_usado
FROM (
    SELECT DISTINCT
        canal_venda,
        tipo_pagamento,
        CASE WHEN entrega_expressa THEN 'Sim' ELSE 'Não' END AS entrega_expressa,
        CASE WHEN presente         THEN 'Sim' ELSE 'Não' END AS presente,
        CASE WHEN cupom_id IS NOT NULL THEN 'Sim' ELSE 'Não' END AS cupom_usado
    FROM stg_pedidos
) s
LEFT JOIN dim_pedido_perfil d
       ON  d.canal_venda      = s.canal_venda
       AND d.tipo_pagamento   = s.tipo_pagamento
       AND d.entrega_expressa = s.entrega_expressa
       AND d.presente         = s.presente
       AND d.cupom_usado      = s.cupom_usado
WHERE d.perfil_key IS NULL;

-- 2) Carga da fato, resolvendo a chave da junk dimension
INSERT INTO fato_pedidos (data_key, cliente_key, produto_key, perfil_key, valor_total, quantidade)
SELECT
    s.data_key, s.cliente_key, s.produto_key, d.perfil_key, s.valor_total, s.quantidade
FROM stg_pedidos s
JOIN dim_pedido_perfil d
  ON  d.canal_venda      = s.canal_venda
  AND d.tipo_pagamento   = s.tipo_pagamento
  AND d.entrega_expressa = CASE WHEN s.entrega_expressa THEN 'Sim' ELSE 'Não' END
  AND d.presente         = CASE WHEN s.presente         THEN 'Sim' ELSE 'Não' END
  AND d.cupom_usado      = CASE WHEN s.cupom_id IS NOT NULL THEN 'Sim' ELSE 'Não' END;
```

A ordem importa: **primeiro atualiza a dimensão, depois carrega a fato**, senão o lookup falha para combinações novas.

### Comparando as duas

| | Cartesiano | Só combinações existentes |
|---|---|---|
| Linhas na dimensão | Todas as possíveis | Só as que ocorreram |
| Combinações impossíveis | Aparecem na dimensão | Não aparecem |
| Carga da fato | Lookup simples | Atualizar a dimensão antes |
| Atributo novo | Recria tudo | Dimensão cresce sozinha |
| Melhor quando | Poucos atributos, domínio fechado | Muitos atributos ou domínio aberto |

## Junk dimension, degenerate dimension e dimensão normal

Esses três conceitos vivem perto um do outro e são fáceis de confundir:

| Tipo | O que é | Exemplo |
|---|---|---|
| **Dimensão normal** | Entidade com atributos descritivos e, em geral, hierarquia | Cliente, produto, data |
| **Degenerate dimension** | Identificador que vive **na própria fato**, sem tabela de dimensão (não tem atributos extras) | Número do pedido, número da nota fiscal |
| **Junk dimension** | Vários atributos pequenos, sem relação entre si, agrupados em **uma** dimensão | Flags, canal, tipo de pagamento |

> **Regra prática:** se o atributo tem poucos valores e nenhuma hierarquia, é candidato a junk. Se tem identidade própria (um código único por linha da fato), é degenerate. Se tem vários atributos descritivos que sempre caminham juntos, é uma dimensão de verdade.

## Quando usar e quando evitar

**Use quando:**

- Os atributos têm **baixa cardinalidade** (poucos valores cada).
- Não têm **hierarquia** nem relação semântica forte entre si.
- Estão **sobrando** na fato ou gerariam várias minidimensões.
- O número de combinações reais é **administrável** (na casa de centenas ou poucos milhares).

**Evite quando:**

- **O produto cartesiano explode.** Com 10 atributos de 10 valores, são 10 bilhões de combinações possíveis. Mesmo na estratégia "só as que existem", dimensão grande demais perde o benefício.
- Algum atributo tem **alta cardinalidade** (ex.: código de campanha com milhares de valores). Esse merece dimensão própria.
- Os atributos **mudam ao longo do tempo** de forma independente e você precisa do histórico (SCD) de cada um. Na junk dimension, mudar um atributo significa apontar para **outra linha**, o que complica a análise de histórico.
- Os atributos **fazem sentido juntos** e têm identidade própria. Nesse caso, são uma dimensão normal.

Uma saída comum quando o grupo fica grande é **dividir em duas ou mais junk dimensions**, agrupando os atributos por afinidade (ex.: uma para pagamento e outra para logística).

## Cuidados práticos

- **Nomeie bem.** "junk" é um termo de modelagem, não precisa ir para o nome da tabela. Algo como `dim_pedido_perfil` ou `dim_pedido_flags` é mais claro para quem consome.
- **Tenha uma linha "desconhecido".** Para o caso de o sistema de origem mandar nulos, vale ter uma linha com `perfil_key = 0` e valores como "Não informado", em vez de deixar a FK nula.
- **Evite NULL nos atributos.** Troque por um valor textual ("Não informado") para que o filtro e o `GROUP BY` do BI se comportem direito.
- **Documente o que está dentro.** Como não é uma entidade do negócio, ninguém vai descobrir sozinho o que a dimensão contém. Um comentário na tabela e uma linha no catálogo ajudam.

## Resumo

- **Junk dimension** junta vários atributos de baixa cardinalidade (flags, indicadores, códigos curtos) em **uma única dimensão**, em que cada linha é uma combinação de valores.
- A tabela fato guarda **uma FK** para essa combinação, em vez de várias colunas soltas ou várias FKs para minidimensões.
- Dá para construir pelo **produto cartesiano** (todas as combinações) ou **só pelas combinações que existem** (a mais comum), atualizando a dimensão antes de carregar a fato.
- Não confunda com **degenerate dimension**, que é um identificador (número do pedido) guardado direto na fato.
- Evite quando as combinações explodem, quando há atributos de alta cardinalidade ou quando cada atributo precisa de histórico próprio.

## Referências

- [Junk Dimensions (Kimball Group)](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/junk-dimension/)
- *The Data Warehouse Toolkit*, Ralph Kimball e Margy Ross
- Post relacionado: [Data Warehouse, Data Lake e Lakehouse]({{< relref "/posts/dados/dw-dl-lakehouse.md" >}})
