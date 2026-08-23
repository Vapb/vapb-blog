---
title: "Data Quality Fundamentals - Capítulo 1"
author: "vapb"
description: "Resumo do primeiro capítulo do livro Data Quality Fundamentals (Barr Moses, Lior Gavish e Molly Vorwerck), sobre por que qualidade de dados se tornou prioridade nos times de dados."
date: 2026-08-22
tags: ["Fundamentos_da_Qualidade_de_Dados"]
toc: false
---

## Introdução

Decidi começar a fazer resumos dos livros que vou lendo por aqui, tanto para ajudar a fixar o conteúdo quanto para ter um registro que eu possa consultar depois. A ideia é ir publicando um resumo por capítulo, na medida em que for lendo.

O primeiro livro da série é *Data Quality Fundamentals*, de Barr Moses, Lior Gavish e Molly Vorwerck (O'Reilly). Vamos começar pelo Capítulo 1, "Why Data Quality Deserves Attention—Now", que estabelece o problema central do livro: o *data downtime*.

## O que é "data downtime"

**Data downtime** é o termo usado para períodos em que os dados estão ausentes, incorretos ou de alguma forma equivocados, resultando em dashboards desatualizados, relatórios imprecisos e decisões ruins.

Barr Moses e Lior Gavish chegaram a esse conceito entrevistando centenas de times de dados, e identificaram um problema praticamente universal: *schemas* que mudam e quebram pipelines, duplicação de linhas em relatórios críticos, dados que somem sem aviso.

## Qualidade de dados e o paralelo com DevOps

O livro define qualidade de dados como **a saúde dos dados em qualquer estágio do seu ciclo de vida**, podendo ser afetada antes da ingestão, durante o processamento em produção ou até na hora da análise final. É uma definição ampla, que reconhece que qualidade não é um checkpoint único, mas algo monitorado continuamente ao longo do pipeline (ingestão → transformação → carga → análise).

O capítulo traça um paralelo com engenharia de software: assim como *uptime* de aplicação é uma métrica crítica em SRE, com o padrão das *"cinco noves"* (99,999%) de disponibilidade, times de dados precisam pensar em **confiabilidade de dados** da mesma forma. Essa mentalidade é batizada de **DataOps**: aplicar à área de dados práticas que já são padrão em DevOps, como CI/CD e observabilidade, só que voltadas para pipelines de dados em vez de código de aplicação. Netflix, Uber, Airbnb e Intuit são citadas como pioneiras em publicar sobre esse assunto desde 2019.

## O impacto (e o custo) de dados não confiáveis

Números que ilustram a urgência do tema:

- Times de dados gastam **até 40% do tempo** lidando com problemas de qualidade em vez de projetos mais interessantes.
- Um levantamento da ZoomInfo (2019) mostrou que **1 em cada 5 empresas** perdeu um cliente por causa de um problema de qualidade de dados.
- O caso clássico da sonda *Mars Climate Orbiter* da NASA (1999): um erro de conversão entre unidades SI e não-SI fez a sonda se aproximar demais do planeta e ser destruída, um prejuízo de **US$ 125 milhões**.

A comparação com esse caso: assim como uma espaçonave, *pipelines analíticos podem ser extremamente vulneráveis à mudança mais inocente em qualquer estágio do processo*.

## Os 5 fatores por trás do aumento do data downtime

Cinco tendências, combinadas, explicam por que esse problema está crescendo:

1. **Migração para a nuvem**: data warehouses e data lakes saíram do "porão da empresa" para soluções como Snowflake, Redshift e BigQuery, tornando os dados mais acessíveis, mas também expondo mais gente a eles.
2. **Mais fontes de dados**: empresas hoje integram dezenas ou centenas de fontes internas e externas, e qualquer uma pode mudar sem aviso prévio.
3. **Pipelines cada vez mais complexos**: múltiplas etapas de processamento e dependências não triviais entre ativos de dados, sem visibilidade clara de quem depende de quem.
4. **Times de dados mais especializados**: mais analistas, engenheiros e cientistas de dados trabalhando em paralelo aumenta o risco de mudanças de um time quebrarem o pipeline de outro.
5. **Times de dados descentralizados**: um paralelo com a migração de arquiteturas monolíticas para microsserviços no mundo de software, com analistas cada vez mais distribuídos pelas áreas de negócio, o que facilita duplicação, dados obsoletos e falta de coordenação. Isso **não é a mesma coisa que data mesh**, que é um paradigma organizacional específico baseado em domínios; o capítulo apenas cita o termo para evitar essa confusão, sem se aprofundar nele.

## Outras tendências do momento atual

Além dos 5 fatores centrais, três movimentos de mercado também empurram a qualidade de dados para o topo da lista de prioridades.

**Data mesh.** Assim como a engenharia de software migrou de aplicações monolíticas para microsserviços, o *data mesh* é, de certa forma, a versão "microsserviços" da plataforma de dados. É um conceito ainda recente, cunhado por Zhamak Dehghani (Thoughtworks), e descrito como um paradigma sociotécnico baseado em *domain-driven design*: em vez de um data lake central cuidando de tudo, cada domínio de negócio passa a tratar seus próprios dados como um produto (o termo do livro é *data-as-a-product*), com pipelines e times de dados dedicados. O que conecta esses domínios é uma camada de interoperabilidade comum, com os mesmos padrões e sintaxe de dados. Um data mesh só funciona se os dados de cada domínio forem confiáveis, o que exige testes, monitoramento e observabilidade consistentes entre eles. Intuit e JPMorgan Chase são citados como exemplos de empresas que adotaram essa arquitetura.

**Streaming data.** Historicamente, qualidade de dados era garantida testando dados em *batch* antes de entrarem em produção. Com a adoção crescente de *streaming* (dados fluindo continuamente para gerar insights em tempo real), esse modelo de teste tradicional fica mais difícil de aplicar, já que os dados estão constantemente *"em movimento"*. Como a maioria das empresas está adotando batch e streaming ao mesmo tempo, os times de dados precisam repensar como testam e observam seus dados.

**A ascensão do data lakehouse.** Data warehouse (dados estruturados) e data lake (dados brutos, não estruturados) vêm convergindo: provedores de data warehouse na nuvem passaram a oferecer recursos de data lake (como o Redshift Spectrum) e vice-versa (data lakes ganhando SQL e schema, como o Databricks Lakehouse). O resultado é o *data lakehouse*, uma camada única combinando os dois mundos. Essa migração torna os pipelines ainda mais complexos, seja usando um único fornecedor para as duas funções, seja combinando múltiplas camadas de storage e processamento, o que cria mais pontos onde os dados podem quebrar mesmo com testes extensivos.
