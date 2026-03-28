---
title: "Quando o autovacuum não é suficiente: um incidente real com AWS DMS e PostgreSQL"
author: "vapb"
description: "Como um ambiente com AWS DMS pode silenciosamente vencer o autovacuum, corromper as estatísticas do planner e transformar uma query de 9ms em 4 segundos, e o que fazer a respeito."
date: 2026-03-26
tags: ["PostgreSQL", "Performance", "AWS", "DMS", "Incidente"]
toc: true
---


## Introdução

Era uma tarde comum quando as primeiras mensagens chegaram. Lentidão no sistema. Nada catastrófico à primeira vista, o tipo de coisa que, antes de virar incidente, ainda parece só um ruído.

Mas ao abrir os logs de uma das APIs do sistema, o ruído tinha nome: uma consulta de busca de opções consumindo 4 segundos inteiros. Não era a soma de vários problemas, era ela sozinha, responsável por 99,7% do tempo total da requisição. Todas as outras operações juntas mal chegavam a 30ms.

O ambiente tinha índices corretos. O volume de dados era o esperado. A configuração do banco não tinha mudado. E mesmo assim, a query estava travando o sistema. Uma query que, semanas antes, respondia em frações de segundo.

---

## O incidente

As primeiras queixas vieram dos times que consumiam a API. Lentidão generalizada, o ambiente de desenvolvimento travando, CPU da instância RDS a 99%.

O primeiro passo foi abrir os logs do projeto. E aqui vale um parêntese: o sistema já tinha instrumentação de observabilidade nas consultas ao banco, o que tornou o diagnóstico inicial muito mais rápido do que poderia ter sido. Nos logs, ficou claro que a API fazia diversas consultas a diferentes bancos de dados, mas uma delas se destacava de forma absurda.

Uma única consulta consumia sozinha **99,7% do tempo total da requisição**.

Fomos então ao RDS investigar tudo que poderíamos: dados, índices, estrutura das tabelas, as próprias consultas. E fizemos isso comparando diretamente com o ambiente de produção, que, para nossa surpresa, estava se comportando normalmente. Mesmos índices, volume de dados similar, configuração aparentemente idêntica, mas planos de execução completamente diferentes.

Era aí que estava a resposta.

---

## A suspeita inicial: planner, dados ou índices diferentes?

Com a query como principal suspeita, a investigação passou para o banco. A pergunta era direta: por que o mesmo código, com os mesmos índices e volume de dados similar, se comportava de forma tão diferente entre os dois ambientes?

Comparamos tudo sistematicamente:

| Verificação | Resultado |
|---|---|
| Os índices eram os mesmos? | ✅ Sim |
| O volume de dados era similar? | ✅ Sim |
| O plano de execução era igual? | ❌ Não |

O ambiente de produção executava a consulta em ~9ms. O ambiente de desenvolvimento levava ~25ms, e quando finalmente olhamos para os planos de execução lado a lado, entendemos o porquê.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM options_summary tb
JOIN provider_config pc ON ...
WHERE tb.active = 'S'
LIMIT 10;
```

O ambiente de desenvolvimento estava escolhendo um **Bitmap Scan** em `options_summary`, uma tabela com quase 1,5 milhão de entradas. O Bitmap Scan não é necessariamente ruim, mas para essa consulta ele era a escolha errada: em vez de navegar diretamente pelas linhas relevantes via índice, o planner estava construindo um mapa de páginas na memória e varrendo blocos inteiros do disco. Em uma tabela desse tamanho, o custo era alto.

O ambiente de produção usava uma estratégia diferente e muito mais eficiente para o mesmo filtro.

Com índices idênticos e dados equivalentes, só havia uma explicação possível: o planner estava tomando decisões diferentes porque trabalhava com informações diferentes. **As estatísticas estavam desatualizadas no ambiente de desenvolvimento.**

---

## O que são estatísticas do planner e por que importam

Descobrimos que o problema eram as estatísticas. Mas o que isso significa na prática?

O planner do PostgreSQL *não executa a query* para decidir o melhor plano de execução. Ele **estima** com base em estatísticas armazenadas internamente em `pg_statistic`: quantas linhas uma condição vai retornar, quão seletivo é um filtro, se vale usar um índice ou fazer uma varredura sequencial. É uma decisão matemática baseada em informações coletadas em um momento anterior.

O problema é quando essas informações estão desatualizadas.

Se o planner acredita que uma tabela tem 10.000 linhas quando na verdade tem 1,5 milhão, ele vai tomar decisões calibradas para um volume que não existe mais. Foi exatamente isso que aconteceu: o planner do ambiente de desenvolvimento estimava **1.703 linhas** em um JOIN onde o ambiente de produção via apenas **12**. Com essa estimativa inflada, ele escolheu o Bitmap Scan achando que seria eficiente. Não era.

Você pode inspecionar as estatísticas de uma tabela diretamente:

```sql
SELECT
  attname,           -- o nome da coluna analisada
  n_distinct,        -- quantos valores únicos o planner acredita existir na coluna
  most_common_vals,  -- os valores mais frequentes observados
  most_common_freqs  -- a frequência estimada de cada um desses valores
FROM pg_stats
WHERE schemaname = 'your_schema'
  AND tablename = 'options_summary';
```

Exemplo de retorno:

| attname | n_distinct | most_common_vals | most_common_freqs |
|---|---|---|---|
| active | 2 | {S,N} | {0.92,0.08} |
| provider | -1 | null | null |
| category | 15 | {A,B,C,...} | {0.31,0.18,0.12,...} |

* **`active`**: apenas 2 valores possíveis (`S` e `N`), sendo `S` presente em 92% das linhas. Se a query filtra `WHERE active = 'S'`, o planner sabe que vai retornar quase tudo e deveria evitar o índice.
* **`provider`**: `n_distinct = -1` significa que o planner estima que cada linha tem um valor único (cardinalidade alta). Útil para JOINs.
* **`category`**: distribuição conhecida por categoria. O planner consegue estimar com razoável precisão quantas linhas cada filtro vai retornar.

Se os números aqui não refletem a realidade da tabela, o planner vai errar. *E vai errar silenciosamente.*

---

## A correção e a pulga atrás da orelha

A hipótese era clara: estatísticas desatualizadas. A correção, em teoria, simples.

```sql
ANALYZE your_schema.options_summary;
```

Rodamos o `ANALYZE` manualmente na tabela principal. O planner atualizou as estatísticas, reavaliou o plano e trocou o Bitmap Scan por uma estratégia melhor. Problema resolvido?

Não exatamente. A query caiu de 25ms para... **327ms**. *Piorou.*

O que aconteceu: com estatísticas corretas para `options_summary`, o planner finalmente enxergou o volume real da tabela e abandonou o índice ruim. Mas o JOIN com `provider_config` ainda estava sendo estimado com base em estatísticas antigas. O planner via 1.703 linhas onde o ambiente de produção enxergava apenas 12. Com essa estimativa errada, ele escolheu uma estratégia de junção inadequada para o volume real, e o custo subiu.

Rodamos `ANALYZE` também em `provider_config`. Dessa vez o plano convergiu de verdade: **de 327ms para 7ms**.

Mas aí veio a pulga atrás da orelha.

Se *duas* tabelas estavam com estatísticas ruins, quantas outras estariam na mesma situação? Fomos verificar o estado geral do schema e o que encontramos foi preocupante: a maioria das tabelas nunca tinha sido analisada. O `last_autoanalyze` estava nulo em quase tudo.

O `autovacuum` estava configurado. Mas claramente não estava rodando. Por quê?

---

## A pergunta que não podia ficar sem resposta

**"Mas espera, o autovacuum não deveria ter feito isso automaticamente?"**

Sim. E aqui está o ponto central do post.

O `autovacuum` **inclui o `ANALYZE`**: quando ele roda em uma tabela, ele atualiza as estatísticas do planner automaticamente. Em condições normais, não é preciso rodar os dois separadamente. O PostgreSQL cuida disso sozinho.

Mas o `autovacuum` não dispara o tempo todo. Ele tem um threshold:

```
linhas modificadas > threshold + (scale_factor × total de linhas)
```

Com `scale_factor = 0.05` e uma tabela de 1,5M linhas, o `autovacuum` só dispara após **75.000 modificações**. Em um banco transacional comum, isso é razoável. O problema é que esse ambiente não era um banco transacional comum.

O ambiente usava **AWS DMS** (*Database Migration Service*) para replicar dados de outro sistema em tempo real. O DMS é um serviço da AWS que move dados entre bancos de forma contínua, e quando está em modo de replicação contínua (CDC), ele gera um volume absurdo de operações de `INSERT`, `UPDATE` e `DELETE` no banco de destino. O `autovacuum` começava a rodar, o DMS já tinha modificado mais 75.000 linhas, e o threshold era ultrapassado novamente antes do ciclo fechar. *O autovacuum nunca conseguia terminar o que começou.*

Verificamos o estado real das tabelas:

```sql
SELECT relname, last_analyze, last_autoanalyze,
       n_live_tup, n_mod_since_analyze
FROM pg_stat_user_tables
WHERE schemaname = 'your_schema';
```

O resultado foi revelador:

| relname | last_analyze | last_autoanalyze | n_live_tup | n_mod_since_analyze |
|---|---|---|---|---|
| options_summary | null | null | 1.487.203 | 1.487.203 |
| provider_config | null | null | 84.301 | 84.301 |
| processing_rules | null | null | 203.847 | 198.100 |
| integration_config | null | 2026-01-03 | 42.100 | 38.900 |

Tabelas com `last_autoanalyze` **nulo** nunca tinham sido analisadas. E `n_mod_since_analyze` igual ao total de linhas vivas significa que o planner nunca teve estatísticas válidas para trabalhar, estava operando completamente no escuro desde o início.

O `autovacuum` estava configurado corretamente. Ele simplesmente não conseguia vencer a corrente contrária do DMS.

Confirmamos a interferência da replicação:

```sql
SHOW hot_standby_feedback;
SHOW vacuum_defer_cleanup_age;
```

`hot_standby_feedback = on` faz com que réplicas informem ao primário quais transações ainda estão ativas, impedindo o vacuum de limpar versões antigas de linhas que a réplica ainda pode precisar. `vacuum_defer_cleanup_age` define quantas transações o vacuum deve esperar antes de agir. Combinados com a carga do DMS, esses dois parâmetros criavam um ambiente onde o `autovacuum` era sistematicamente bloqueado antes de completar o trabalho.

---

## A lição: o que fazer em ambientes com replicação

O incidente deixou claro que configurar o `autovacuum` corretamente não é suficiente quando o ambiente tem uma fonte contínua de modificações competindo com ele. Em ambientes com DMS ou replicação lógica, é preciso assumir que o `autovacuum` pode estar perdendo a corrida, e monitorar ativamente para saber quando isso acontece.

O que aprendemos na prática:

**Monitorar `n_mod_since_analyze` ativamente.** Não assuma que o `autovacuum` acompanhou. A query abaixo vira um aliado importante nesse contexto.

**Ter uma rotina de `ANALYZE` manual após cargas de replicação.** Especialmente em janelas onde o DMS processa grandes volumes.

**Configurar alertas no CloudWatch para AAS e CPU.** A CPU a 99% foi o primeiro sinal visível, mas o problema já existia antes disso. Alertas antecipados evitam que o incidente chegue ao usuário final.

**Considerar `SET STATISTICS` maior em colunas críticas de filtro.** O valor padrão é 100. Em colunas com alta cardinalidade ou distribuição irregular, aumentar esse valor dá ao planner uma visão mais precisa da distribuição dos dados.

Para monitorar quais tabelas estão mais desatualizadas:

```sql
SELECT relname, n_mod_since_analyze, n_live_tup,
       round(100.0 * n_mod_since_analyze / nullif(n_live_tup, 0), 1) AS pct_modified
FROM pg_stat_user_tables
WHERE schemaname = 'your_schema'
  AND n_mod_since_analyze > 0
ORDER BY pct_modified DESC;
```

Qualquer tabela com `pct_modified` alto é uma candidata a estar com estatísticas ruins, e potencialmente fazendo o planner tomar decisões erradas *nesse exato momento*.

---

## Conclusão

No final, o incidente que começou com reclamações de lentidão e CPU a 99% tinha uma causa surpreendentemente específica: o `autovacuum`, configurado corretamente, simplesmente não conseguia terminar o que começava. O DMS era rápido demais. As estatísticas nunca eram atualizadas. E o planner, operando no escuro, tomava decisões erradas que se manifestavam como lentidão inexplicável em uma query que, no ambiente ao lado, rodava em 9ms.

A moral não é *"rode `ANALYZE` sempre"*. É: **entenda o que impede o `autovacuum` de funcionar no seu ambiente específico.**

O `autovacuum` foi projetado para cargas transacionais normais. Em ambientes com replicação em alta velocidade, ele perde silenciosamente a corrida contra o volume de modificações. E quando perde, o problema não aparece como "`autovacuum` atrasado", aparece como query lenta, CPU estourada, times reclamando de lentidão numa tarde comum.