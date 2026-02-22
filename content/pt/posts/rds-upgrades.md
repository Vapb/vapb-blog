---
title: "Upgrades no Amazon RDS e Aurora PostgreSQL: Guia Completo"
author: "vapb"
description: "Tudo sobre manutenção e upgrades no Amazon RDS e Aurora PostgreSQL. Entenda minor vs major versions, AMVU, Zero Downtime Patching e as quatro estratégias de upgrade: In-Place, Logical Replication, Blue/Green e DMS."
date: 2026-02-22
tags: ["PostgreSQL", "AWS RDS", "Aurora"]
toc: true
---

## Introdução

Fazer upgrade de banco de dados em produção é uma das tarefas que mais exige planejamento no dia a dia de quem trabalha com AWS. Neste post vou cobrir tudo sobre manutenção e upgrades no Amazon RDS e Aurora PostgreSQL, desde os conceitos básicos até as diferentes estratégias para executar um major version upgrade com o mínimo de impacto possível.

## O que é manutenção no RDS?

O RDS realiza três tipos de manutenção: **patches de SO**, **patches de software** (geralmente sem restart) e **upgrades de versão do engine** (minor ou major version upgrades). Tudo acontece dentro de uma janela de manutenção configurável, idealmente em horário de baixo tráfego.

Você consegue visualizar as manutenções pendentes na aba **Maintenance and Backups** no console do RDS, onde aparece o tipo da operação, o status e a data prevista para execução.

## Minor version vs Major version

- **Versões major** são os números inteiros: 11, 12, 13, 14, 15, 16, 17, 18...
- **Versões minor** são os decimais: 11.6, 12.5, 16.3, 18.1...

Um upgrade de 11.5 para 11.7 é **minor**. Um upgrade de 13 para 15 é **major**.

### Minor version upgrades

São patches nos binários do PostgreSQL. Não adicionam novas funcionalidades, mas podem conter correções de segurança importantes. As características principais são:

* Downtime curto
* Podem ser feitos automaticamente (**AMVU**)
* Não exigem novo parameter group
* São retrocompatíveis
* Estatísticas do otimizador são preservadas
* Não exigem testes extensivos

### Major version upgrades

Adicionam novas funcionalidades e podem alterar catálogos internos e formatos de página, ou seja, mexem nos dados em si. Por isso exigem mais cuidado:

* Downtime maior (pode ser vários minutos)
* Precisam de planejamento cuidadoso
* Exigem novo parameter group
* Exigem testes funcionais e de performance
* Estatísticas do otimizador não são transferidas automaticamente
* Extensions precisam ser atualizadas manualmente após o upgrade
* É possível pular versões (ex: ir direto de 13 para 15)

## Auto Minor Version Upgrade (AMVU)

O **AMVU** é uma opção que você ativa na instância para que o RDS atualize automaticamente para a **preferred minor version** durante a janela de manutenção.

⚠️ Um detalhe importante: a preferred version **não é necessariamente a mais recente**.

## Zero Downtime Patching (ZDP) no Aurora

Para minimizar o impacto de minor version upgrades e patches, o Aurora tem um recurso chamado **Zero Downtime Patching**. Ele funciona assim:

1. O Aurora monitora o banco em busca de um momento de "quietude"
2. Quando encontra, pausa novas transações temporariamente
3. Aplica o patch/upgrade
4. Restaura as conexões existentes

Você não precisa habilitar o **ZDP** explicitamente, ele é automático quando as condições permitem. No console, você consegue acompanhar os eventos do **ZDP** na seção **Events**.

## Estratégias para Major Version Upgrades

Existem quatro abordagens para executar um major version upgrade. Cada uma tem suas vantagens e trade-offs.

### 1. In-Place Upgrade

É a abordagem mais simples: você modifica a instância no console para a nova versão e o RDS cuida de tudo. O processo interno é:

1. **Pre-upgrade checks**: verifica se há prepared transactions abertas, data types incompatíveis, views que dependem de tabelas de catálogo, etc.
2. **Backup automático**: realizado apenas se você tiver automated backups habilitados (recomendado!)
3. **Shutdown do banco**
4. **Execução do pg_upgrade**: aqui acontece o downtime real
5. **Restart do engine**
6. **Novo backup**

Considerações importantes para in-place upgrade:

* Faça um backup manual pouco antes, como os backups são incrementais, quanto mais recente, mais rápido o processo
* Crie um novo parameter group para a versão target
* Limpe e arquive dados antes do upgrade para reduzir objetos e minimizar o downtime
* Garanta que não há transações longas abertas
* Rode `ANALYZE` após o upgrade para atualizar as estatísticas do planner (no PG 18+ isso já é automático)
* Atualize as extensions manualmente após o upgrade
* Réplicas cross-region e read replicas de Multi-AZ cluster precisam ser recriadas após o upgrade

### 2. Logical Replication (manual)

Com a replicação lógica, você consegue replicar entre major versions diferentes, algo impossível com replicação física. Isso permite criar uma instância nova já na versão target e sincronizá-la com a produção antes do corte.

O fluxo é:

1. Criar uma nova instância na versão target (ex: PG 17)
2. Configurar a logical replication entre source (PG 16) e target (PG 17)
3. Aguardar o target ficar em sincronia com o source
4. No momento do corte, parar as escritas no source, apontar a aplicação para o novo endpoint e desligar o antigo

O downtime fica reduzido **apenas ao tempo do corte final**, que pode ser de segundos. O trabalho pesado de copiar os dados já aconteceu antes, sem impacto na produção.

A logical replication usa um modelo publish/subscribe e decodifica as transações SQL via WAL (Write-Ahead Log) para aplicá-las no target. Diferente da replicação física (byte a byte), ela permite replicar apenas databases ou tabelas específicas.

### 3. Blue/Green Deployment

O Blue/Green Deployment é essencialmente a mesma ideia da logical replication, mas com a AWS automatizando toda a orquestração.

Como funciona:

1. Você clica em **"Create Blue/Green Deployment"** no console
2. Seleciona a instância blue (produção atual) e define a versão target do green
3. A AWS cria o ambiente green como cópia exata do blue e configura a logical replication automaticamente
4. Você acompanha o status até o green estar em sincronia
5. Você testa no ambiente green (pode conectar diretamente no endpoint do green)
6. Quando estiver confiante, clica em **"Switchover"**
7. A AWS gerencia o corte automaticamente e redireciona o endpoint sem você precisar alterar nada na aplicação

O timeout do switchover é configurável, com mínimo de 30 segundos, e o processo é abortado automaticamente se exceder o limite definido. O ambiente blue fica disponível por um tempo para rollback caso necessário.

### 4. AWS DMS

O AWS DMS também usa logical replication por baixo, mas é um serviço separado e mais genérico, pensado para migrações em geral. Faz sentido quando você tem cenários mais complexos.

Diferenciais do DMS:

* Suporta fontes fora da AWS (on-prem, outra cloud)
* Suporta migrações heterogêneas (Oracle → PostgreSQL, por exemplo)
* Oferece três modos de operação:
  * **Full Load**: cópia completa do source para o target em um ponto no tempo
  * **Full Load + CDC**: cópia completa e depois captura contínua de mudanças
  * **CDC puro**: captura apenas as mudanças a partir de um LSN específico
* Para instâncias com múltiplos databases, é possível criar tasks paralelas por database para aumentar o throughput

## Comparativo das estratégias

| Critério | In-Place | Logical Replication | Blue/Green | DMS |
|:---------|:--------:|:-------------------:|:----------:|:---:|
| **Complexidade** | Baixa | Alta | Média | Média/Alta |
| **Downtime** | Minutos | Segundos (só o corte) | Segundos (só o switchover) | Segundos (só o corte) |
| **Automação** | Total pelo RDS | Manual | Alta (AWS gerencia) | Média |
| **Rollback** | Snapshot | Manual | Ambiente blue disponível | Manual |
| **Cenários extra** | — | Replicação granular | — | Heterogêneo, on-prem |
| **Custo adicional** | Nenhum | Nenhum | Nenhum | Sim (serviço separado) |

## Boas práticas para Major Version Upgrades

Independente da estratégia escolhida, algumas práticas são essenciais.

**Antes do upgrade:**

* Leia a documentação da estratégia escolhida para entender os pré-requisitos e possíveis caveats
* Faça um backup manual pouco antes do upgrade (os backups do RDS são incrementais, quanto mais recente, mais rápido)
* Execute a limpeza do banco: vacuum, arquivamento de dados antigos, remoção de objetos desnecessários. Quanto menos objetos, menor o downtime
* Crie o novo parameter group para a versão target
* Garanta que não há prepared transactions abertas
* Faça testes funcionais e de performance em um ambiente clone (RDS restore ou Aurora clone) antes de executar em produção
* Planeje com antecedência considerando o impacto no negócio

**Após o upgrade:**

* Rode `ANALYZE` para atualizar as estatísticas do query planner (evita lentidão nas queries)
* Faça o upgrade manual das extensions
* Verifique a saúde das réplicas e recrie as que foram removidas
* Monitore o comportamento da aplicação nas primeiras horas

## TLDR

Para minor upgrades, use o AMVU e deixe o RDS cuidar. Para major upgrades, o **Blue/Green Deployment** é a escolha mais segura na maioria dos casos. baixo downtime, automático e sem mudança de endpoint. Use DMS se vier de outro engine ou de fora da AWS. Qualquer que seja a estratégia: **teste antes, faça backup e planeje a janela**.
