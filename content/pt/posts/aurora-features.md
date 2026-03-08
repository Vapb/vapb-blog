---
title: "Aurora PostgreSQL: Por Dentro das Features Avançadas"
author: "vapb"
description: "Features avançadas do Aurora PostgreSQL: do storage distribuído ao Zero ETL."
date: 2026-03-07
tags: ["PostgreSQL", "AWS", "Aurora", "Database Administration"]
toc: true
---

Se você usa ou está avaliando o Amazon Aurora PostgreSQL, provavelmente já ouviu que ele é "mais rápido que o RDS comum". Mas o que exatamente faz essa diferença? Neste post vou destrinchar as principais features avançadas do Aurora Postgres, cobrindo a arquitetura de storage, otimizações de I/O e cache.

## A Grande Sacada: Compute e Storage Separados

A inovação central do Aurora é desacoplar o **compute** (as instâncias) do **storage**.

Quando você cria um cluster Aurora, apenas o writer é provisionado. Readers são opcionais e você adiciona conforme precisar. Mas o storage layer já nasce completo: **6 cópias** dos seus dados, distribuídas em **3 Availability Zones** (2 por AZ), de forma automática e sem nenhuma configuração.

Isso muda tudo em relação ao RDS tradicional:

| Característica | RDS Tradicional | Aurora |
|---|---|---|
| Storage por instância | Próprio (EBS) | Compartilhado entre todas |
| Replicação entre instâncias | WAL completo (pesado) | Não existe: leem o mesmo storage |
| Lag em read replicas | Proporcional ao volume | Geralmente abaixo de 100ms |
| Adicionar uma read replica | Precisa copiar dados | Rápido: storage já existe |
| Failover | Lento (novo writer precisa "aprender" o storage) | Rápido: novo writer já conhece o storage |

{{< hint info >}}
O storage cresce e encolhe automaticamente em incrementos de **10GB**, até **128TB**. Você nunca dimensiona ou gerencia os storage nodes, totalmente abstraídos pela AWS, similar ao que o S3 faz com objetos.
{{< /hint >}}

## Replicação: o Aurora não replica do jeito que você está acostumado

No Postgres tradicional e no RDS comum, replicação significa enviar o WAL completo (blocos de dados inteiros) do writer para cada replica. É pesado, consome rede e gera lag proporcional ao volume de dados.

No Aurora isso não existe dentro do cluster. Como writer e readers compartilham o mesmo storage, não há nada a replicar entre eles. O writer envia apenas **redo log records** (muito menores que blocos completos) para os storage nodes, e os readers simplesmente leem do mesmo storage.

```
Tradicional:
Writer ──WAL (blocos completos)──▶ Replica 1
Writer ──WAL (blocos completos)──▶ Replica 2

Aurora:
Writer ──redo log records──▶ Storage nodes (6x)
Reader 1 ◀──lê direto──▶ Storage nodes
Reader 2 ◀──lê direto──▶ Storage nodes
```

Readers ficam geralmente abaixo de **100ms de defasagem**, não porque a replicação é rápida, mas porque não há replicação.

{{< hint info >}}
A replicação lógica ainda existe no Aurora, mas para casos específicos **fora do cluster**.
{{< /hint >}}

## Alta Disponibilidade: Write Quorum de 4/6

Como o writer envia dados para os 6 storage nodes, o Aurora usa um **write quorum**: a escrita só é confirmada para a aplicação quando pelo menos **4 dos 6 nodes** respondem.

```
                    ┌── AZ 1 ────┐
                    │ Node 1 ✅ │
Writer ──escrita──▶ │ Node 2 ✅ │
                    ├── AZ 2 ────┤
                    │ Node 3 ✅ │
                    │ Node 4 ✅ │ ◀── 4 confirmações = escrita confirmada!
                    ├── AZ 3 ───┤
                    │ Node 5 ⚠️ │ (lento)
                    │ Node 6 ❌ │ (offline)
                    └────────────┘
```

Isso significa que você tolera até **2 nodes simultâneos offline**, incluindo uma AZ inteira, sem interromper operações. Para leitura, basta 1 node responder: como o writer já garantiu quorum na escrita, qualquer node disponível já tem dados consistentes.

Para failover, o Aurora usa **Route 53 DNS** por padrão. O **AWS JDBC Driver** é uma alternativa mais rápida, pois rastreia o cluster por IP ao invés de hostname.

## Dentro de um Storage Node

O que acontece internamente quando uma escrita chega ao storage node?

```
Writer ──redo log──▶ Incoming Queue ──▶ Hot Log ──▶ ACK para o writer
                                            │
                                      (background)
                                            ▼
                                     Update Queue ──▶ Data Pages
                                            │
                                            ▼
                                        Amazon S3 (backup/PITR)
```

{{< hint info >}}
Apenas **Incoming Queue** e **Hot Log** estão no caminho crítico. Tudo depois acontece em background, sem impactar a latência da aplicação. Se um node perder algum redo log, ele busca automaticamente nos peers antes de montar os data pages.
{{< /hint >}}

### Local Write Forwarding

E se sua aplicação não sabe diferenciar endpoints de leitura e escrita? O **Local Write Forwarding** resolve isso: a read replica aceita escritas e as encaminha transparentemente para o writer primário.

## Query Plan Management (QPM)

O planner do Postgres normalmente escolhe bons planos, mas mudanças no banco (estatísticas desatualizadas, índice removido, configuração alterada) podem levá-lo a um plano subótimo com impacto drástico de performance.

O QPM permite **fixar os planos aprovados** para as queries mais críticas. Com ele ativo, mesmo que você remova um índice ou as estatísticas fiquem desatualizadas, o plano aprovado continuará sendo usado.

O QPM também permite capturar novos planos à medida que o banco evolui, avaliá-los em ambiente seguro e aprová-los quando estiver pronto, sem risco de regressão automática em produção.

{{< hint info >}}
Com planos pré-aprovados, o Postgres pula boa parte do processo de decisão, ganhando eficiência.
{{< /hint >}}

## Cluster Cache Management (CCM)

{{< hint warning >}}
Após um failover, o novo writer começa com **cache frio**. Como cache é 2-3 ordens de magnitude mais rápido que storage, isso causa degradação de performance até o cache reaquecer.
{{< /hint >}}

O CCM resolve designando uma replica como **failover target preferido** (prioridade 0) e mantendo seu cache sincronizado com o writer atual. Quando o failover ocorre, o novo writer já tem o cache quente.

## IO Optimized

No Aurora Standard, você paga por compute, storage e I/O. Leituras em storage custam por bloco de **8KB**; escritas custam por chunk de **4KB**.

O IO Optimized remove completamente a cobrança por I/O, aumentando levemente o custo de compute e storage.

{{< hint info >}}
Se I/O representa mais de **~25% da sua conta Aurora**, a troca costuma valer a pena.
{{< /hint >}}

## Optimized Reads

O Optimized Reads usa o **NVMe local** da instância (ao invés de EBS ou Aurora storage) para dados efêmeros, com ganhos de até **8x em latência** e **30% em custo de I/O**.

É especialmente útil para:
- Queries com joins/sorts pesados
- Dashboards com muitas queries simultâneas
- Criação de índices
- Workloads com pgvector/Gen AI
- SLAs rígidos de latência

## Aurora Global Database

Até aqui falamos de features dentro de uma região. O **Aurora Global Database** expande o cluster para múltiplas regiões AWS, mantendo um único banco logicamente unificado. A replicação acontece na camada de storage, com infraestrutura dedicada e sem passar pelo engine do Postgres — por isso o impacto na região primária é mínimo mesmo a altas velocidades de escrita.

Dois casos de uso principais:
- **Disaster Recovery:** réplicas em outras regiões em tempo real. Se a região primária cair, você promove uma secundária em menos de **1 minuto**
- **Data locality:** usuários globais leem de uma região próxima, reduzindo latência de forma significativa

### Como funciona por baixo

A replicação entre regiões é **física** (não lógica), paralela, criptografada em trânsito e acontece com lag abaixo de **1 segundo**.

```
┌─────────────────────────────────────┐
│           REGIÃO PRIMÁRIA (Ohio)    │
│                                     │
│  ┌──────────┐     ┌──────────────┐  │
│  │  Writer  │────▶│   Storage    │  │
│  └──────────┘     │   Layer      │  │
│  ┌──────────┐     │  (6 nodes)   │  │
│  │ Reader 1 │────▶│              │  │
│  └──────────┘     └──────┬───────┘  │
│                          │          │
│                   Replication       │
│                   Servers           │
└──────────────────────────┼──────────┘
                           │
              (físico, paralelo, <1s)
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
┌─────────────────────┐         ┌─────────────────────┐
│  REGIÃO SECUNDÁRIA  │         │  REGIÃO SECUNDÁRIA  │
│  (N. Virginia)      │         │  (Ireland)          │
│                     │         │                     │
│  Replication Agent  │         │  Replication Agent  │
│         │           │         │         │           │
│         ▼           │         │         ▼           │
│     Storage         │         │     Storage         │
│     Layer           │         │     Layer           │
│  ┌──────────┐       │         │  ┌──────────┐       │
│  │ Reader 1 │       │         │  │ Reader 1 │       │
│  │ Reader 2 │       │         │  └──────────┘       │
│  └──────────┘       │         │                     │
└─────────────────────┘         └─────────────────────┘
```

### Write Forwarding

Assim como o Local Write Forwarding dentro do cluster, você pode habilitar escritas nas regiões secundárias que são tuneladas automaticamente de volta para a primária. Mesmos três modos de consistência (Session, Eventual, Global), mas com latências maiores por ser cross-region.

{{< hint warning >}}
O Write Forwarding cross-region tem latência de **~195ms de ida e volta**. Para workloads write-heavy com SLA rígido, considere sempre escrever direto na região primária.
{{< /hint >}}

### Global Writer Endpoint

Um único endpoint para escritas em todas as regiões. Quando uma secundária é promovida a primária, o endpoint se atualiza automaticamente, sem reconfigurar a aplicação.

## Amazon RDS Proxy

Um serviço gerenciado que fica entre a aplicação e o banco, assumindo o gerenciamento de conexões. Totalmente gerenciado pela AWS, sem manutenção de OS ou software.

### Connection Pooling

Abrir uma conexão com o banco não é barato: envolve **TLS negotiation**, autenticação e alocação de CPU e memória. Com RDS Proxy, esse custo fica no proxy, não no banco.

```
Sem Proxy:
App (milhares de conexões) ──────────────▶ Banco (sobrecarregado)

Com Proxy:
App (centenas de milhares) ──▶ Proxy ──▶ Banco (poucas conexões gerenciadas)
                              (multiplexing)
```

O proxy é **transaction-aware**: só compartilha conexões entre transações, nunca no meio de uma, evitando problemas de estado compartilhado indevido.

{{< hint info >}}
Especialmente valioso para **Lambda e microserviços**, onde conexões são abertas e fechadas a cada invocação. O proxy absorve esse padrão sem sobrecarregar o banco.
{{< /hint >}}

## Aurora Machine Learning

Integração nativa do Aurora com serviços de ML da AWS via **SQL puro**, sem ETL, sem aprender frameworks de ML, sem construir integrações extras. O dado já está no Aurora; você chama o modelo direto na query.

Dois serviços suportados:

| Serviço | Quando usar |
|---|---|
| **Amazon SageMaker** | Modelo customizado treinado com seus próprios dados |
| **Amazon Comprehend** | Análise de sentimento pronta, sem treinar modelo |

## Logical Replication Cache (WAL Cache)

Com replicação lógica ativa (CDC para DMS, Kafka, Debezium, etc.), cada escrita vai para o storage duas vezes: transaction log e WAL. Quando o consumidor solicita os dados, o Aurora precisa ler de volta do storage para o logical decoding, um round trip extra desnecessário.

O **WAL Cache** elimina esse round trip mantendo os dados do WAL em memória logo após a escrita:

```
Sem WAL Cache:
Escrita ──▶ Storage (WAL)
Consumidor ──▶ lê do storage ──▶ logical decoding ──▶ Consumidor

Com WAL Cache:
Escrita ──▶ Storage (WAL) + Cache (memória)
Consumidor ──▶ lê do cache ──▶ logical decoding ──▶ Consumidor
```

## Zero ETL

Levar dados do Aurora para o Redshift normalmente exige uma pipeline complexa:

```
Aurora ──▶ DMS ──▶ S3 ──▶ Glue/EMR ──▶ S3 ──▶ Redshift
```

O **Zero ETL** substitui tudo isso com uma integração direta e gerenciada, configurável via console, CLI ou SDK.

Por baixo, o processo é:

1. Cria **replication slot** no Aurora
2. **Seed inicial** para o Redshift (na storage layer, sem impacto no Postgres)
3. **CDC contínuo** via replication slot
4. **Monitoramento automático** com reseed se necessário

{{< hint info >}}
Lag e performance da integração ficam disponíveis via **Redshift system tables** ou **CloudWatch metrics**.
{{< /hint >}}

## Resumo

O Aurora não é só "RDS mais rápido". Cada feature resolve um problema específico de produção — desde estabilidade de queries até replicação global e integração com analytics. A tabela abaixo consolida o que vimos:

| Feature | O que resolve | Ganho principal |
|---|---|---|
| **Arquitetura** | Storage compartilhado entre writer e readers | Elimina lag de replicação dentro do cluster |
| **Storage Internals** | Writes confirmados com quorum de 4/6 nodes | Tolerância a falhas sem impacto na latência |
| **QPM** | Planos de query instáveis após mudanças no banco | Estabilidade de performance sem regressões |
| **CCM** | Cache frio após failover | Novo writer já começa com cache quente |
| **IO Optimized** | Custo de I/O variável e imprevisível | Preço fixo, mais throughput para workloads I/O-heavy |
| **Optimized Reads** | Queries pesadas que extrapolam shared buffers | NVMe local como cache extra, até 8x menos latência |
| **Global Database** | DR multi-region e latência para usuários globais | Lag < 1s entre regiões, failover em < 1 minuto |
| **RDS Proxy** | Explosão de conexões (Lambda, microserviços) | Connection pooling gerenciado, failover mais rápido |
| **Aurora ML** | Inferência ML exige ETL e integração complexa | Chame SageMaker ou Comprehend direto via SQL |
| **WAL Cache** | Round trip extra de storage no logical decoding | Menos latência e I/O no caminho do CDC |
| **Zero ETL** | Pipeline complexa para Aurora → Redshift | Integração direta e gerenciada, sem DMS nem Glue |