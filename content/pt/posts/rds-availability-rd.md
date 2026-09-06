---
title: "RDS PostgreSQL: High Availability and Disaster Recovery"
author: "vapb"
description: "Guide to RDS availability: Multi-AZ configurations, failover mechanisms, snapshots, read replicas, and disaster recovery strategies for mission-critical databases."
date: 2025-11-02
tags: ["aws", "postgresql", "rds"]
toc: true
---

## 1. Por Que Alta Disponibilidade Importa
Imagine acordar às 3h da manhã com alertas de que seu banco de dados de produção está fora do ar.
Seu e-commerce está offline. Cada minuto custa milhares de reais em receita perdida.
Clientes estão frustrados. Seu time está em pânico.

É por isso que Alta Disponibilidade (HA) não é opcional para sistemas de produção.

## 2. Opções de Alta Disponibilidade no RDS
O RDS oferece três modelos de deployment, cada um com diferentes garantias de disponibilidade.

### 2.1. Single-AZ (Sem Standby) ❌

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


### 2.2. Multi-AZ com Um Standby (Síncrono) ✅
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

#### 2.2.1. Cenário de Failover 1: Instância primária falha

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

#### 2.2.2. Cenário 2: Instância standby falha

O que acontece:
* Impacto: NENHUM na sua aplicação

Ações do RDS:
1. Detecta falha do standby
2. Primária continua servindo tráfego normalmente
3. RDS provisiona novo standby em background
4. Sincronização resume automaticamente

#### 2.2.3. Cenário 3: AZ inteira falha

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


### 2.3. Multi-AZ DB Cluster (Semi-Síncrono) 🚀
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

## 3. Estratégias de Recuperação de Desastres

Alta Disponibilidade protege contra falhas de infraestrutura. Recuperação de Desastres protege contra eventos catastróficos: quedas em toda região, deleções acidentais, corrupção de dados, ransomware.

### 3.1. Snapshots do RDS
Snapshots são backups point-in-time do seu banco de dados inteiro.

{{< details title="Snapshots automatizados" >}}
```
Dia 1:
├─ 00:00 - Snapshot completo tirado
└─ Durante o dia: Logs transacionais capturados

Dia 2:
├─ 00:00 - Snapshot incremental (apenas mudanças)
└─ Durante o dia: Logs transacionais capturados

Dia 3:
├─ 00:00 - Snapshot incremental
└─ E assim por diante...
```

Funcionalidades:
* Backups automáticos diários
* Incrementais (apenas blocos alterados)
* Inclui logs transacionais (para restore point-in-time)
* Retenção padrão: 7 dias (configurável até 35 dias)
* Janela de backup: Especifique horário preferido (período de baixo tráfego)

Point-in-Time Restore (PITR) -> Cenário: DELETE acidental às 14:47.
Você pode restaurar para:
* 14:46 (antes do DELETE)
* 14:30 (30 min antes)
* 10:00 (hoje de manhã)
* Qualquer incremento de 5 minutos dentro do período de retenção

Custo:
* Incluído no preço do RDS
* Custo de storage: Mesmo que storage provisionado
* Exemplo: DB de 100 GB = ~R$ 50/mês para backups
{{< /details >}}

{{< details title="Snapshots manuais" >}}
```
Snapshots Automatizados:
├─ Acontecem automaticamente diariamente
├─ Deletados após período de retenção
├─ Suportam restore point-in-time
└─ Vinculados à instância

Snapshots Manuais:
├─ Você os dispara
├─ NUNCA deletados automaticamente
├─ SEM restore point-in-time (apenas o momento do snapshot)
└─ Independentes da instância (persistem após deleção)
```

Quando usar snapshots manuais:
*  Antes de mudanças maiores
*  Requisitos de compliance/auditoria
*  Antes de deletar instância

Custo:
* Paga apenas pelo storage
* $0,095/GB/mês em us-east-1
* Snapshot de 100 GB = $9,50/mês
{{< /details >}}

{{< hint info >}}
🎯 Estratégia de Snapshots para Produção
* Configure backups automatizados
* Tire snapshots manuais antes de mudanças:
  * Migrações de schema
  * Upgrades de versão maior
  * Mudanças de configuração
  * Antes de deletar instância
* Copie snapshots cross-region
* Teste restores regularmente
{{< /hint >}}

#### 3.1.1. Processo de Restore de Snapshot

Timeline:
1. Iniciar restore (chamada API): 1 minuto
2. RDS provisiona nova instância: 5-10 minutos
3. Restore dados do snapshot: 10-60 minutos (depende do tamanho)
4. Instância fica disponível: Total 15-70 minutos

Fatores que afetam o tempo:
* Tamanho do banco (maior = mais longo)
* Classe da instância (maior = restore mais rápido)
* Carga da região (horários de pico podem ser mais lentos)

Após restore -> Nova instância:
* Endpoint diferente (precisa atualizar connection strings)
* Mesmos dados do momento do snapshot
* Mesma configuração (classe de instância, parâmetros)
* Instância original ainda rodando (você escolhe qual manter)

### 3.2. Read Replicas para DR
Read replicas servem a DOIS propósitos:
* Escalabilidade de leitura (descarregar queries SELECT)
* Recuperação de desastres (pode ser promovida a standalone)

```
  ┌─────────────────┐        ┌─────────────────┐
  │  us-east-1      │        │  us-west-2      │
  │                 │        │                 │
  │  ┌───────────┐  │        │  ┌───────────┐  │
  │  │ Primary   │  │───────►│  │  Read     │  │
  │  │ (Source)  │  │ Async  │  │  Replica  │  │
  │  └─────┬─────┘  │ Replic │  └───────────┘  │
  │        │        │        │                 │
  └────────┼────────┘        └─────────────────┘
           │
    Tráfego de escrita          
```

Replicação Assíncrona:
1. App escreve na primária
2. Primária faz commit imediatamente
3. Primária envia mudança para réplica
4. Réplica aplica mudança (eventualmente)
5. Réplica pode estar atrasada em relação à primária (segundos a minutos) ⚠️

Características-chave:
* Replicação async (sem impacto na latência de escrita)
* Pode estar na mesma região ou cross-region
* Pode ter classe de instância diferente da primária
* Pode ser promovida a instância standalone
* Lag de replicação possível (monitore de perto)

####  3.2.1. Read Replicas In-Region vs Cross-Region
| Característica | In-Region | Cross-Region |
|----------------|-----------|--------------|
| **Topologia** | Primária (us-east-1a) → Réplica (us-east-1b) | Primária (us-east-1) → Réplica (eu-west-1) |
| **Lag de Replicação** | <1 segundo (tipicamente) | 1-5 segundos (depende da distância) |
| **Custo** | ~2x custo da instância | 2x instância + transferência de dados ($0,02/GB) |
| **Transferência de Dados** | ✅ Sem cobrança | ❌ Cobrado ($0,02/GB out) |
| **Latência** | Muito baixa (~ms) | Variável (10-200ms conforme distância) |
| **Caso de Uso Principal** | Escalabilidade de leitura | Recuperação de desastres + leituras globais |
| **Melhor Para** | Descarregar reads da primária | DR cross-region, compliance, usuários globais |


Quando usar cross-region:
* Recuperação de desastres (proteção contra falha em toda região)
* Compliance (requisitos de residência de dados)
* Aplicação global (servir usuários da região mais próxima)
* Menor latência de leitura para usuários geograficamente distribuídos

#### 3.2.2. Dimensionamento de Read Replica
Réplica pode ser de tamanho diferente da primária

Benefícios replica maior:
* Lida com workload pesado de leitura facilmente
* Sem degradação de performance
* Bom para queries analíticas

Risco replica menor:
* Réplica não consegue acompanhar primária
* Lag de replicação aumenta
* Eventualmente réplica fica muito atrasada
* Ruim para recuperação de desastres!

Regra prática: Réplica deve ser ≥ mesma classe que primária para propósitos de DR.

## 4. Alta Disponibilidade vs Recuperação de Desastres

| Aspecto | Alta Disponibilidade (HA) | Recuperação de Desastres (DR) |
|---------|---------------------------|-------------------------------|
| **Propósito** | Proteger contra falhas de infraestrutura | Proteger contra eventos catastróficos |
| **Tecnologia** | Multi-AZ (replicação sync) | Snapshots + Read Replicas (async) |
| **RPO** | 0 (sem perda de dados) | Minutos a horas (depende do backup) |
| **RTO** | 1-2 min (35 seg para cluster) | Horas (restore de snapshot) |
| **Escopo** | Mesma região, AZs diferentes | Cross-region |
| **Replicação** | Síncrona | Assíncrona |
| **Classe de Instância** | Mesma que primária | Pode diferir |
| **Custo** | 2x custo da instância | 2x + storage + transferência de dados |
| **Failover** | Automático | Manual (promover réplica) |
| **Protege Contra** | Falha de AZ, problemas de hardware | Falha de região, corrupção de dados, acidentes |


## 5. Conclusão
Alta Disponibilidade e Recuperação de Desastres não são opcionais para bancos de dados de produção—são seguro essencial contra falhas inevitáveis.

8.1. Principais Conclusões
Alta Disponibilidade:
* Use Multi-AZ para toda produção (RTO: 1-2 min, RPO: 0) ✅ 
* Use Multi-AZ Cluster para mission-critical (RTO: <35 seg) 🚀 
* Nunca use Single-AZ para produção ❌ 

Recuperação de Desastres:
* Habilite backups automatizados (retenção de 35 dias) ✅
* Tire snapshots manuais antes de mudanças maiores ✅
* Use read replica cross-region para sistemas críticos ✅
* Teste DR trimestralmente (restore, promova, meça) ✅

Design de Aplicação:
* Lógica de retry para conexões ✅
* Transações idempotentes ✅
* Health checks e monitoramento ✅

Custos:
* Multi-AZ: ~2x custo Single-AZ (~R$ 1.500/mês para setup típico)
* ROI: Se paga prevenindo <1 hora downtime/mês

Métricas Críticas:
* Monitore: DatabaseConnections, ReplicaLag, FreeStorageSpace
* Alerte: Lag >60s, Storage <10 GB, Conexões >80%