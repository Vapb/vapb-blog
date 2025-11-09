---
title: "RDS PostgreSQL: High Availability and Disaster Recovery"
author: "vapb"
description: "Guide to RDS availability: Multi-AZ configurations, failover mechanisms, snapshots, read replicas, and disaster recovery strategies for mission-critical databases."
date: 2025-11-02
tags: ["AWS", "RDS", "PostgreSQL"]
toc: true
---

## Por Que Alta Disponibilidade Importa
Imagine acordar às 3h da manhã com alertas de que seu banco de dados de produção está fora do ar.
Seu e-commerce está offline. Cada minuto custa milhares de reais em receita perdida.
Clientes estão frustrados. Seu time está em pânico.

É por isso que Alta Disponibilidade (HA) não é opcional para sistemas de produção.

## Opções de Alta Disponibilidade no RDS
O RDS oferece três modelos de deployment, cada um com diferentes garantias de disponibilidade.

### Single-AZ (Sem Standby) ❌

```
    ┌─────────────────┐
    │  Availability   │
    │    Zone A       │
    │                 │
    │  ┌───────────┐  │
    │  │ Primary   │  │
    │  │ Instance  │  │
    │  └───────────┘  │
    │                 │
    └─────────────────┘

    Sem redundância!
```

O que acontece se a primária falhar:
* RDS detecta a falha
* RDS provisiona nova instância EC2
* RDS anexa volumes EBS
* PostgreSQL inicializa
* Banco de dados fica disponível

⏰ Downtime: Tipicamente 10-30 minutos (às vezes mais)

Quando usar:
* Ambientes dev/test ✅
* Workloads não-críticos sensíveis a custo ✅
* Bancos que podem tolerar downtime prolongado ✅

⚠️ Riscos do Single-AZ
* Falha de hardware → 10-30 min de downtime
* Falha de AZ → Potencialmente horas de downtime
* Janelas de manutenção → Downtime durante upgrades
* Sem failover automático

**Conclusão: Single-AZ NÃO é pronto para produção.**


### Multi-AZ com Um Standby (Síncrono) ✅
```
    ┌─────────────────┐        ┌─────────────────┐
    │   Availability  │        │   Availability  │
    │     Zone A      │        │      Zone B     │
    │                 │        │                 │
    │  ┌───────────┐  │        │  ┌───────────┐  │
    │  │ Primary   │  │◄──────►│  │ Standby   │  │
    │  │ Instance  │  │ Replic │  │ Instance  │  │
    │  └─────┬─────┘  │ Sínc   │  └───────────┘  │
    │        │        │        │                 │
    └────────┼────────┘        └─────────────────┘
             │
             │ Apps conectam aqui
             ▼
       DNS Endpoint
       mydb.abc.rds.amazonaws.com
```

Este é o setup padrão de produção para a maioria dos workloads.

Fluxo de Replicação Síncrona:
1. App envia: INSERT INTO users...
2. Primária recebe a escrita
3. Primária envia para standby: "Vou commitar isso"
4. Standby reconhece: "Recebi, persistido"
5. Primária faz commit
6. Primária responde para app: "Sucesso!"

Escrita só confirmada após standby reconhecer
Benefícios:
* Zero perda de dados (RPO = 0)
* Failover rápido (RTO = 1-2 min)
* Automático (sem intervenção manual)
* Mesmo endpoint (mudança de DNS, sem alterações no app)

#### Cenário de Failover 1: Instância primária falha

O que acontece:
* Primária trava
* Health check do RDS detecta falha
* RDS inicia failover
* DNS aponta para standby
* Standby promovida a primária
* Novas conexões aceitas ✅

⚠️ Downtime total: ~1-2 minutos

Sua aplicação vê:
* Conexões existentes: Dropadas (precisam reconectar)
* Novas conexões: Breve rejeição, depois sucesso
* Perda de dados: ZERO (tudo estava sincronizado)

RDS automaticamente:
* Promove standby a primária
* Atualiza DNS (sem mudança de IP para o app)
* Começa a reconstruir novo standby em background

#### Cenário 2: Instância standby falha

O que acontece:
* Impacto: NENHUM na sua aplicação

Ações do RDS:
1. Detecta falha do standby
2. Primária continua servindo tráfego normalmente
3. RDS provisiona novo standby em background
4. Sincronização resume automaticamente

#### Cenário 3: AZ inteira falha

O que acontece:
* Se AZ da Primária falha:
  * Standby em AZ diferente assume
  * Tempo de failover: ~1-2 minutos
  * Zero perda de dados
* Se AZ do Standby falha:
  * Primária não afetada
  * RDS reconstrói standby em AZ saudável
  * Zero impacto na aplicação

{{< details title="O que causa failover automático?" >}}
RDS faz failover automaticamente para:
* Falhas de infraestrutura:
  * Falha de hardware da instância primária
  * Falha de storage subjacente
  * Queda em nível de AZ
  * Perda de conectividade de rede entre AZs
* Operações de manutenção:
  * Patching de SO (aplicado no standby primeiro, depois failover)
  * Upgrades de engine do banco (minimiza downtime)

NÃO causa failover ❌ :
* Queries de longa duração (problema do PostgreSQL, não infraestrutura)
* Deadlocks (problema de lógica da aplicação/banco)
* Out of connections (problema de configuração)
* Disco cheio (precisa aumentar storage)

Para problemas em nível de banco: RDS reinicia, não faz failover.
{{< /details >}}

{{< hint info >}}
🎯 Vantagens Operacionais
* Backups rodam no standby
* Manutenção aplicada no standby primeiro
   * Standby recebe patch/upgrade
   * Failover acontece (1-2 min de downtime)
   * Primária antiga vira novo standby
   * Novo standby recebe patch
   * Resultado: Downtime mínimo para manutenção
* Garantia de SLA
  * 99,95% de uptime mensal no SLA
  * Traduz para ~22 minutos máx de downtime por mês
* Mesmo endpoint
  * DNS: mydb.abc.rds.amazonaws.com
  * Sem mudanças na aplicação após failover
  * Connection string permanece a mesma
{{< /hint >}}


### Multi-AZ DB Cluster (Semi-Síncrono) 🚀
```
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │     AZ A     │   │     AZ B     │   │     AZ C     │
    │              │   │              │   │              │
    │ ┌──────────┐ │   │ ┌──────────┐ │   │ ┌──────────┐ │
    │ │ Primary  │ │   │ │ Readable │ │   │ │ Readable │ │
    │ │ Instance │◄├───┤►│ Standby  │ │   │ │ Standby  │ │
    │ │          │ │   │ │    #1    │ │   │ │    #2    │ │
    │ └────┬─────┘ │   │ └────┬─────┘ │   │ └────┬─────┘ │
    │      │NVMe   │   │      │NVMe   │   │      │NVMe   │
    │      │SSD    │   │      │SSD    │   │      │SSD    │
    └──────┼───────┘   └──────┼───────┘   └──────┼───────┘
           │                  │                  │
           ▼                  ▼                  ▼
      Write Endpoint     Reader Endpoint    Reader Endpoint
```

Esta é a opção premium para RTO ultra-baixo e escalabilidade de leitura integrada.

Replicação Semi-Síncrona:
1. App envia: INSERT INTO orders...
2. Primária recebe a escrita
3. Primária envia para AMBOS standbys
4. Primária aguarda QUALQUER UM dos standbys reconhecer
5. Primária faz commit (não espera pelos dois)
6. Primária responde ao app: "Sucesso!"
7. Apenas um standby precisa confirmar (mais rápido que sync total)

Diferenças-chave do Multi-AZ com Um Standby:
* 2 standbys em vez de 1 (três AZs no total)
* Standbys são legíveis (podem servir queries SELECT)
* Failover mais rápido (<35 segundos vs 1-2 minutos)
* SSDs NVMe locais (melhor performance de I/O)
* Reader endpoint (balanceamento automático)

{{< hint info >}}
🎯 Vantagens Operacionais
1. Failover Ultra-Rápido (<35 segundos)
2. Escalabilidade de Leitura Integrada
3. Reader Endpoint Automático
4. Melhor Performance
{{< /hint >}}

Quando Usar Multi-AZ Cluster: 
* RTO < 35 segundos necessário
* Aplicações mission-critical
* Serviços financeiros, saúde
* E-commerce durante picos sazonais
* Workload pesado em leitura

| Funcionalidade | Single-AZ | Multi-AZ (1 Standby) | Multi-AZ Cluster |
|----------------|-----------|----------------------|------------------|
| **Availability Zones** | 1 | 2 | 3 |
| **Replicação** | Nenhuma | Síncrona | Semi-síncrona |
| **RTO** | 10-30 min | 1-2 min | <35 seg |
| **RPO** | Minutos a horas | 0 (sem perda de dados) | 0 (sem perda de dados) |
| **Standbys Legíveis** | N/A | ❌ Não | ✅ Sim (2) |
| **Failover Automático** | ❌ Não | ✅ Sim | ✅ Sim |
| **Tipo de Storage** | EBS | EBS | NVMe SSD Local |
| **SLA** | Nenhum | 99,95% | 99,99% |
| **Custo** | $ | $$ (2x Single-AZ) | $$$$ (4x Single-AZ) |
| **Melhor Para** | Dev/test | Produção (padrão) | Mission-critical |

## Estratégias de Recuperação de Desastres