---
title: "RDS PostgreSQL Fundamentals: Performance e Otimização"
author: "vapb"
description: "Amazon RDS: escolha de instâncias, tipos de armazenamento EBS, auto-scaling e estratégias de otimização de custos."
date: 2025-11-01
tags: ["aws", "rds", "postgresql"]
toc: true
---

## 1. Introdução

O **Amazon RDS (Relational Database Service)** para PostgreSQL é uma solução gerenciada que simplifica a administração de bancos de dados PostgreSQL na nuvem. Neste post, vamos explorar os principais conceitos e funcionalidades que você precisa conhecer para trabalhar com esta poderosa ferramenta.

### 1.1. Performance: o que realmente importa

O desempenho do seu RDS depende de dois pilares:

1. **Classe da instância** - CPU, memória e rede
2. **Tipo de armazenamento** - Throughput de I/O

### 1.2. Escalabilidade: os números

O RDS oferece escalabilidade independente para computação e armazenamento:

{{< details title="Limites de computação" >}}
- **Até 128 vCPUs**
- **Até 4.096 GB de RAM**
{{< /details >}}

{{< details title="Limites de armazenamento" >}}
- **Até 64 TB** de capacidade
- **Até 256.000 IOPS**
- Suporta **auto-scaling** e **scale-down**
{{< /details >}}

{{< hint warning >}}
**⏰ Detalhe importante**

* Modificações no armazenamento **NÃO causam downtime**.
* ⚠️ **MAS** você precisa esperar **6 horas entre modificações**.
* **Isso significa:** planeje suas mudanças com antecedência. Se você aumentou o storage agora, terá que esperar 6 horas para fazer outro ajuste.
{{< /hint >}}

## 2. Escolhendo a classe de instância certa

A escolha da classe de instância é crucial para obter o melhor equilíbrio entre performance e custo. O RDS oferece diferentes famílias de instâncias, cada uma otimizada para cenários específicos.

* **General Purpose**: Workloads menores ou com padrões de uso variável
* **CPU Optimized**: Tarefas que demandam alto poder computacional
* **Memory Optimized**: Queries intensivas em memória e grandes conjuntos de dados em cache
* **Graviton**: Melhor escolha na maioria dos casos.

### 2.1. Como escolher?

A decisão depende das características da sua workload:

- **Analise o gargalo atual:** É CPU? Memória? I/O?
- **Considere o padrão de uso:** Constante ou variável?
- **Avalie o custo-benefício:** Graviton geralmente vence
- **Teste em staging:** Valide a performance antes de ir para produção

## 3. Tipos de armazenamento: EBS em ação

O RDS usa volumes **EBS (Elastic Block Store)** como storage. Pense no EBS como o HD/SSD do seu banco de dados na nuvem. Existem três opções principais, cada uma com características diferentes de velocidade e custo.

### 3.1. Antes de começar: o que é IOPS?

**IOPS** = Input/Output Operations Per Second (Operações de Entrada/Saída por Segundo)

Em português simples: quantas vezes por segundo seu banco consegue ler ou escrever dados no disco.

**No banco de dados:**
- Cada SELECT, INSERT, UPDATE = operações de I/O
- **Mais IOPS** = banco responde mais rápido
- **Menos IOPS** = queries ficam esperando na fila

**Como saber quantos IOPS eu preciso?**
- Monitore no CloudWatch - Métrica: `ReadIOPS + WriteIOPS`
- Se a soma está consistentemente acima de **80% do seu limite** = hora de aumentar


{{< hint info >}}
**💡 Throughput vs IOPS**
- **IOPS:** Quantas operações por segundo (quantidade)
- **Throughput:** Quantos MB/s você transfere (velocidade de transferência)
{{< /hint >}}

### 3.2. GP2 (General Purpose SSD) - a opção legada

{{< details title="Como funciona: performance cresce com o tamanho do volume" >}}
**Exemplos de performance:**
- 100 GB = ~300 IOPS
- 500 GB = ~1.500 IOPS
- 1 TB = ~3.000 IOPS
- 3.334 GB = 10.000 IOPS (máximo base)

**Características:**
- Performance variável: quanto maior o disco, mais IOPS
- Até **1.000 MBps** de throughput
- Preço decente, mas GP3 geralmente é melhor

**Quando usar:** Praticamente nunca. GP3 é superior.
{{< /details >}}

{{< hint warning >}}
**⚠️ Problema do GP2**

Se você precisa de 10.000 IOPS mas só usa 200 GB, terá que pagar por ~3 TB de armazenamento só para ter os IOPS necessários. Desperdício!
{{< /hint >}}

### 3.3. GP3 (General Purpose SSD) - escolha padrão

{{< details title="Como funciona: performance independente do tamanho" >}}
- Qualquer tamanho = **3.000 IOPS baseline** (grátis)
- Precisa mais? Pode comprar até **16.000 IOPS extra**

**Características:**
- **3.000 IOPS baseline** independente do tamanho
- **125 MBps** throughput baseline (pode aumentar até 1.000 MBps)
- **~20% mais barato** que GP2 com mesma performance
- Você ajusta IOPS e throughput separadamente do tamanho

**Quando usar:** Esta deveria ser sua escolha padrão para **90% dos casos**.
{{< /details >}}

### 3.4. IO1 / IO2 Block Express - performance máxima

{{< details title="Como funciona: você provisiona exatamente quantos IOPS precisa" >}}
**Opções disponíveis:**
- **IO1:** Até 64.000 IOPS por volume
- **IO2:** Até 256.000 IOPS por volume
- **IO2 Block Express:** Até 256.000 IOPS + melhor durabilidade

**Características:**
- **IOPS provisionado e garantido** - sem surpresas
- **Latência ultra-baixa** - single-digit milliseconds
- **Performance consistente** - não depende de créditos ou variações
- **Mais caro** - você paga por IOPS provisionado
{{< /details >}}

{{< details title="Quando usar IO2 Block Express" >}}
Use IO2 Block Express quando:
- App crítica que não pode ter latência variável
- Precisa de **>16.000 IOPS** consistentes
- **OLTP intensivo** com milhares de transações/segundo
- Banco de dados de **missão crítica** (banking, saúde, e-commerce grande)
{{< /details >}}

### 3.5. Comparação entre tipos de armazenamento

| Característica | GP2 (Legado) | GP3 (Padrão)| IO2 Block Express (Premium) |
|----------------|--------------|-----------------|------------------------------|
| **IOPS Baseline** | 3 por GB | 3.000 (fixo) | Você escolhe |
| **IOPS Máximo** | 16.000 | 16.000 | 256.000 |
| **Throughput** | Até 1.000 MBps | Até 1.000 MBps | Até 4.000 MBps |
| **Latência** | Variável | Baixa | Ultra-baixa (consistente) |
| **Custo** | $$ | $ | $$$$ |
| **Flexibilidade** | ❌ Presa ao tamanho | ✅ Independente | ✅ Total controle |
| **Melhor para** | Nada (use GP3) | 90% dos casos | Apps críticas |

## 4. Auto storage scaling: deixe o RDS gerenciar

Uma das funcionalidades mais práticas do RDS é o **auto-scaling de armazenamento**. Configure uma vez e deixe o sistema expandir automaticamente quando necessário.

### 4.1. Quando o auto-scaling é acionado?

O RDS monitora seu banco 24/7 e dispara o auto-scaling quando detecta:

{{< details title="Gatilhos de auto-scaling" >}}
**Gatilho 1: Espaço livre ≤ 10% da capacidade total**
- Simples e direto: espaço acabando = expansão automática

**Gatilho 2: Crescimento previsto**
- O RDS analisa o histórico e prevê: "Com base nos últimos dias, você vai ficar sem espaço em breve"
- **Por que isso é importante?** Evita que você fique sem espaço durante um pico inesperado
{{< /details >}}

### 4.2. Proteção de cooldown (6 horas)

{{< hint warning >}}
**⏰ Proteção de cooldown**

Para evitar expansões em cascata que poderiam causar instabilidade:

**Regra:** O auto-scaling só adiciona capacidade se nenhuma modificação ocorreu nas últimas **6 horas**.

**Por que existe isso?**
- Evita flutuações rápidas que podem impactar performance
- Previne crescimento descontrolado por bugs
- Dá tempo para o RDS estabilizar o novo tamanho

⚠️ **Implicação importante:** Se você está crescendo MUITO rápido (>10% a cada 6h), o auto-scaling pode não acompanhar. Nesses casos, dimensione manualmente com folga.
{{< /hint >}}

### 4.3. CloudWatch alarms essenciais

{{< hint info >}}
**💡 Não dependa só do limite máximo!** Configure alertas proativos:

- **Alerta de Espaço Baixo (70%)**
- **Alerta de Crescimento Rápido**
- **Alerta de Limite Próximo (90%)**

**Dica importante:** Defina um limite máximo razoável para evitar surpresas na fatura. Se algo der errado (como um processo descontrolado gerando dados), você não quer acordar com um volume de 64 TB!
{{< /hint >}}

## 5. Otimização de custos

Performance é essencial, mas ninguém quer surpresas na fatura da AWS. A boa notícia? Você pode ter ambos - performance excelente E custos controlados.

* **Estratégia 1:** Escalonamento Dinâmico (Schedule-Based Scaling): 
    * **Opção 1:** AWS Lambda + Scheduler
    * **Opção 2:** AWS Systems Manager (sem código)
    * **Opção 3:** Ferramentas de terceiros: AWS Instance Scheduler, CloudHealth ou Terraform com cron jobs
* **Estratégia 2:** Reserved Instances (RIs): Se você TEM CERTEZA que vai usar RDS por 1-3 anos, RIs são dinheiro grátis na mesa.
* **Estratégia 3:** Graviton: Migrar para Graviton é provavelmente a otimização mais fácil com maior ROI
* **Estratégia 4:** Storage - GP2 → GP3: Migração simples com economia imediata de ~20%.
* **Estratégia 5:** Revise Read Replicas: Read replicas são ótimas para performance, mas cada uma duplica seus custos de computação.

{{< hint info >}}
**Você não pode otimizar o que não mede -> Métricas do CloudWatch**
{{< /hint >}}

## 6. Configuração do RDS: Parameter Groups e conexões

Se você já trabalhou com PostgreSQL "tradicional" (instalado em um servidor), sabe que configurar o banco envolve editar arquivos de texto. No RDS, a AWS simplificou (e em alguns casos complicou um pouco) esse processo.

### 6.1. PostgreSQL tradicional vs RDS

{{< details title="PostgreSQL tradicional (self-managed)" >}}
Você tem acesso direto aos arquivos de configuração:

**1. postgresql.conf** - Configurações do servidor
```bash
max_connections = 100
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
```

**2. pg_hba.conf** - Controle de acesso
```bash
# Quem pode conectar de onde e como
host    all    all    192.168.1.0/24    md5
host    all    all    10.0.0.0/8        trust
```

**Como modificar:**
```bash
# 1. Edita o arquivo
sudo nano /var/lib/postgresql/data/postgresql.conf

# 2. Recarrega configuração
sudo systemctl reload postgresql

# ou se precisar reiniciar
sudo systemctl restart postgresql
```
{{< /details >}}

{{< details title="Amazon RDS" >}}
Você **NÃO tem acesso direto** aos arquivos.

**Por quê?** Porque o RDS é gerenciado - a AWS cuida da infraestrutura.

**Em vez disso, você usa:**
* **Parameter Groups** (substitui postgresql.conf)
* **Security Groups** (substitui pg_hba.conf)
{{< /details >}}

### 6.2. Parameter Groups

Pense em **Parameter Group** como um perfil de configuração para seu banco de dados.

```
┌─────────────────────┐
│  Parameter Group    │ ← Conjunto de configurações
│  "prod-default"     │
│                     │
│  max_connections=200│
│  shared_buffers=8GB │
│  work_mem=16MB      │
└──────────┬──────────┘
           │
           │ aplicado em ↓
           │
    ┌──────┴──────┐
    │ RDS Instance│
    │  meu-db-prod│
    └─────────────┘
```

#### 6.2.1. Tipos de Parameter Groups

{{< details title="Default Parameter Group vs Custom" >}}
**Default Parameter Group (criado pela AWS)**
- Configurações padrão conservadoras
- **Não pode ser modificado**
- Serve como template inicial

**Custom Parameter Group (criado por você)**
- **Totalmente configurável**
- Você controla todos os parâmetros
- Pode ser compartilhado entre instâncias

⚠️ **Importante:** Você **SEMPRE** deve criar um custom parameter group. Nunca use o default em produção!

{{< /details >}}

#### 6.2.2. Tipos de parâmetros

Nem todos os parâmetros funcionam da mesma forma. Alguns podem ser alterados "na hora", outros exigem reinicialização.

{{< details title="Parâmetros estáticos (Static)" >}}
**Definição:** Requerem **reboot da instância** para aplicar.

**Exemplos comuns:**
```yaml
shared_buffers: 
  - O que é: Memória cache do PostgreSQL
  - Típico: 25% da RAM da instância
  - Exemplo: Em instância de 32 GB RAM → shared_buffers = 8 GB
  - Por que reboot: Memória é alocada na inicialização
  
max_connections:
  - O que é: Número máximo de conexões simultâneas
  - Típico: 100-500 (depende do workload)
  - Por que reboot: Estruturas de memória são pré-alocadas
  
wal_buffers:
  - O que é: Buffers para Write-Ahead Logging
  - Típico: -1 (auto, baseado em shared_buffers)
  - Por que reboot: Buffer é pré-alocado
```

**Como aplicar:**
1. Modifica o parameter group
2. Aplica na instância  
3. RDS requer reboot
4. Downtime de ~5-10 minutos
{{< /details >}}

{{< details title="Parâmetros dinâmicos (Dynamic)" >}}
**Definição:** Podem ser aplicados **imediatamente, sem reboot**.

**Exemplos comuns:**
```yaml
work_mem:
  - O que é: Memória para operações de sorting/hash
  - Típico: 4-16 MB (cuidado: por operação!)
  - Pode ser: Alterado por sessão
  - Impacto: Imediato
  
maintenance_work_mem:
  - O que é: Memória para VACUUM, CREATE INDEX, etc
  - Típico: 256 MB - 2 GB
  - Pode ser: Alterado sem reboot
  - Impacto: Imediato
  
log_min_duration_statement:
  - O que é: Loga queries acima de X ms
  - Típico: 1000 (loga queries >1s)
  - Pode ser: Alterado por sessão
  - Impacto: Imediato

random_page_cost:
  - O que é: Custo estimado de leitura aleatória (SSD = 1.1)
  - Típico: 1.1 para SSD, 4.0 para HDD
  - Pode ser: Alterado imediatamente
  - Impacto: Afeta query planner
```

**Como aplicar:**
1. Modifica o parameter group
2. Aplica na instância com "Apply Immediately"
3. Sem downtime!
4. Mudança em segundos
{{< /details >}}

### 6.3. Conexões ao RDS

**Security Groups** fazem o trabalho de "quem pode conectar de onde":

```
┌─────────────────────────┐
│   Security Group        │ ← Controla IPs/networks
│   "rds-prod-sg"         │
│                         │
│   Inbound Rules:        │
│   ✅ 10.0.1.0/24:5432   │ (rede de apps)
│   ✅ 203.0.113.5/32:5432│ (IP fixo admin)
│   ❌ 0.0.0.0/0          │ (resto bloqueado)
└────────┬────────────────┘
         │
         │ protege ↓
         │
  ┌──────┴────────┐
  │  RDS Instance │
  │  meu-db       │
  └───────────────┘
```

#### 6.3.1. Métodos de autenticação no RDS

{{< details title="Opções de autenticação" >}}
**1. Username/Password (Padrão)**
- Método tradicional e mais simples
- Credenciais armazenadas no RDS
- Ideal para começar

**2. IAM Authentication (Recomendado)**
- **Sem senhas** - usa tokens temporários do IAM
- **Mais seguro** - rotação automática de credenciais
- **Auditoria integrada** - rastreie quem acessa via CloudTrail
- Ideal para aplicações modernas na AWS

**3. Kerberos (Empresarial)**
- Autenticação centralizada para ambientes corporativos
- Integração com Active Directory
- Para empresas com infraestrutura Kerberos existente
{{< /details >}}

## 7. TLDR
**Escolha de Instância**
* Default: M6g (Graviton) - melhor custo-benefício
* CPU-heavy: M6g com classe maior
* Memory-heavy: R6g
* Dev/test: T4g (burstable)

**Storage**
* Use GP3 (não GP2!) para 90% dos casos
* Baseline grátis: 3.000 IOPS
* IO2 Block Express: Só se precisar >16k IOPS consistente

**Auto-Scaling**
* Sempre habilite
* Defina limite máximo (3-5x atual)
* Configure CloudWatch alarms (70%, 90%)

**Otimização de Custos**
* GP2 → GP3 (30 min, 20-50% economia storage)
* x86 → Graviton (1 semana teste, 20-40% economia)
* Reserved Instances (30 min, 30-54% economia baseline)
* Remover réplicas desnecessárias (economia variável)
* Downsize sobredimensionados (analise CPU <30%)

**Parameter Groups**
* 🚫 Nunca use default em produção
* Crie custom group
* Parâmetros essenciais:
    * shared_buffers = 25% RAM (static)
    * random_page_cost = 1.1 (dynamic)
    * work_mem = 16MB (dynamic)
    * log_min_duration_statement = 1000 (dynamic)

**Conexões**
* Security Groups controlam acesso de rede
* IAM Authentication recomendado (sem senhas hardcoded)
* Nunca exponha RDS publicamente (sempre em VPC privada)