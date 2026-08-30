---
title: "Replicação PostgreSQL no RDS: Física vs Lógica"
author: "vapb"
description: "Entenda WAL, replication slots e recovery conflicts. Aprenda quando usar replicação física vs lógica no RDS PostgreSQL e evite problemas comuns de lag."
date: 2026-01-25
tags: ["postgresql", "dba", "rds"]
toc: true
---

## WAL (Write-Ahead Logging)

### O que é WAL?
WAL (Write-Ahead Logging) é o mecanismo do PostgreSQL para garantir integridade de dados, **registrando todas as alterações antes de serem escritas nos arquivos reais do banco de dados**. Pense nele como um diário de segurança que registra cada transação antes de modificar permanentemente seus dados.


### Componentes Principais
* **WAL Records (Registros WAL)**: As unidades básicas de informação que representam mudanças individuais no banco de dados.
* **WAL Segments (Segmentos WAL)**: Arquivos (16MB no PostgreSQL padrão, **64MB no RDS**) que contêm coleções de registros WAL, armazenados sequencialmente no diretório `pg_wal`.
* **Log Sequence Number (LSN)**: Um identificador único que rastreia a posição de cada registro no WAL.

### Como Funciona
Quando ocorrem alterações, elas seguem este caminho:
1. Registros WAL são escritos em buffers WAL na memória
2. O processo **WAL writer** faz flush desses buffers para disco (diretório `pg_wal`)
3. Separadamente, o processo **checkpointer** faz flush dos dados reais dos shared buffers para os arquivos de dados

Estes são dois processos distintos com responsabilidades diferentes - o WAL writer gerencia logs, enquanto o checkpointer cuida da persistência de dados.

### Por Que WAL É Importante

| Função | Descrição |
|--------|-----------|
| 🔄 **Crash Recovery** | Reproduz registros WAL para restaurar estado consistente |
| ⏰ **Point-in-Time Recovery** | Arquivos WAL permitem restaurar para momento específico |
| 🔁 **Replicação** | Réplicas consomem dados WAL para sincronizar |

Quando um segmento WAL preenche, PostgreSQL muda para um novo. Segmentos antigos são reciclados ou removidos após arquivamento.

💡 **Dica RDS:** Habilitar backups automáticos automaticamente habilita arquivamento WAL para S3.

### Dedicated Log Volumes (DLV) no RDS
**DLV** é um volume de armazenamento adicional especificamente para logs transacionais do banco de dados. Ele isola os logs transacionais dos arquivos de dados reais, evitando contenção entre processamento de consultas e transações.


## Replicação Física: Cópias Byte-a-Byte
A replicação física transmite registros WAL do primário para servidores standby em tempo real, criando cópias **idênticas byte-a-byte**. O processo WAL sender no primário se comunica com o processo WAL receiver nas réplicas.

### Como Funciona a Replicação Física
A replicação física opera transmitindo registros WAL diretamente do primário para servidores standby **sem esperar que os segmentos WAL sejam preenchidos completamente**. 

```markdown
┌──────────────┐         WAL Stream        ┌──────────────┐
│   PRIMÁRIO   │ ────────────────────────> │   RÉPLICA    │
│              │                           │              │
│ WAL sender   │ ═══════════════════════>  │ WAL receiver │
│              │   (sem esperar segment    │              │
│              │    preencher completo)    │              │
└──────────────┘                           └──────────────┘
```


Esse streaming é gerenciado por dois processos dedicados:

- **Processo WAL sender**: Executado no servidor primário e envia dados WAL
- **Processo WAL receiver**: Executado na réplica e recebe dados WAL

### Característica Chave: Cópia Exata

```markdown
PRIMÁRIO                          RÉPLICA
┌─────────────────┐              ┌─────────────────┐
│ Block Address 5 │              │ Block Address 5 │
│ id=1, nome=João │ ───────────> │ id=1, nome=João │
│ xmin=100        │   Idêntico   │ xmin=100        │
└─────────────────┘              └─────────────────┘
```

Se você consultar um endereço de bloco específico no primário, encontrará **exatamente os mesmos dados** no mesmo endereço na réplica.

### Modos de Replicação e Restrições
A replicação física pode ser configurada como **assíncrona** ou **síncrona**, embora as read replicas do RDS usem especificamente apenas replicação assíncrona.

⚠️ **Restrição Crítica**: WAL sender e receiver só se comunicam na mesma versão major!

Todas as alterações feitas no primário são automaticamente replicadas para todas as réplicas. Não há replicação seletiva com replicação física.

### Implementação no RDS
No RDS, é simples:
1. Acesse o console
2. Clique em "Create read replica"
3. Escolha região (in-region ou cross-region)
4. Pronto! Replicação configurada automaticamente

### Configuração do WAL Level
O parâmetro `wal_level` controla a quantidade de informações escritas nos logs WAL. Para replicação física, ele deve ser configurado para pelo menos `replica`, que inclui todos os dados necessários para arquivamento WAL e replicação.

### Recuperação por Versão
Para **RDS PostgreSQL ≤13**, a recuperação usa abordagem híbrida:

```markdown
┌──────────────┐
│   PRIMÁRIO   │
│              │
│   pg_wal/    │ ────┐
└──────────────┘     │
                     │ Arquivamento
                     ↓
              ┌─────────────┐
              │  Amazon S3  │
              └─────────────┘
                     ↑
                     │ Recuperação
┌──────────────┐     │ (quando atrasada)
│   RÉPLICA    │ ────┘
│              │
│ 1.Stream     │ ← Preferência
│ 2.S3 fallback│ ← Quando WAL removido do primário
└──────────────┘
```

1. O primário mantém um diretório `pg_wal` com arquivos WAL atuais
2. Um processo de arquivamento envia arquivos WAL para o Amazon S3
3. Quando uma réplica se conecta, ela primeiro tenta transmitir alterações do primário
4. Se a réplica está atrasada e não consegue encontrar os arquivos WAL necessários no primário, ela os recupera do S3
5. Uma vez atualizada, ela retoma o streaming do primário

⚠️ **Crítico:** Configure período de retenção apropriado! Se réplica atrasar além da retenção, não conseguirá recuperar.


### Cenário Real de Recuperação

```markdown
T0: Réplica está 2 horas atrasada
    ↓
T1: "could not receive data from WAL stream:
     requested WAL segment has been removed"
    └─> WAL necessário já foi removido do primário
    ↓
T2: "switched WAL source from stream to archive"
    └─> Réplica muda para recuperação via S3
    ↓
T3: "restored log from archive"
    └─> Recupera arquivos WAL faltantes do S3
    ↓
T4: "started streaming WAL from primary"
    └─> Volta ao streaming normal
```

### Replication Slots
Replication slots são um mecanismo automatizado que garante que o primário não remova segmentos WAL até que todos os standbys os recebam. Eles rastreiam o último registro WAL que cada réplica recebeu.

```markdown
RÉPLICA ATIVA                    RÉPLICA INATIVA
┌──────────────┐                 ┌──────────────┐
│ Consumindo   │                 │ Offline há   │
│ WAL normal   │                 │ 3 horas      │
└──────────────┘                 └──────────────┘
        ↓                                ↓
        ✅ WAL removido                  ❌ WAL RETIDO
           após consumo                     no primário!
```

**Como funcionam**: Se uma réplica está inativa e incapaz de receber registros WAL, esses registros são mantidos no primário. No entanto, esse acúmulo pode ser controlado através de parâmetros.

### Uso no RDS
| Tipo de Réplica | Método |
|-----------------|--------|
| Cross-region (todas) | ✅ Sempre slot-based |
| In-region (≥14) | ✅ Híbrido (slot + S3) |
| In-region (≤13) | S3 archive primário |

**Risco de armazenamento**: Replicação baseada em slots pode preencher rapidamente o armazenamento do primário se as réplicas atrasarem significativamente.

**Solução:** Configure `max_slot_wal_keep_size` para limitar acúmulo!


### Métodos de Recuperação por Versão do PostgreSQL

| Versão | Método Principal | Processo |
|--------|------------------|----------|
| **≤13** | Recuperação de arquivo S3 | Stream do primário → Se atrasando, recuperar do S3 → Retomar streaming |
| **≥14.1** | Abordagem híbrida | Mix de replicação baseada em slots e arquivo S3. Quando streaming é interrompido, usa slot ou S3 para recuperar |
| **Cross-region (todas)** | Slot-based | Sempre usam replicação baseada em slots |

## Recovery Conflicts: O Problema Invisível

Conflitos de recuperação são quando a aplicação de WAL **interfere com queries** rodando na réplica.

### Conflito 1: Atraso na Aplicação de WAL

```markdown
LINHA DO TEMPO:

T0: Réplica executando SELECT * FROM tabela_grande
    Primário gera: W1, W2, W3, W4, W5...
    └─> Réplica recebe mas NÃO PODE APLICAR
        (query ainda está lendo!)

T1: Queue de WAL crescendo...
    W1, W2, W3, W4, W5, W6, W7, W8...
    └─> 30 segundos de atraso acumulado

T2: ❌ ERRO!
    "canceling statement due to conflict with recovery"
    └─> Query cancelada (mesmo que começou há 5 segundos!)
```

**Por quê?** O limite é sobre **atraso em aplicar WAL**, não duração da query!

**Solução: max_standby_streaming_delay**

Este parâmetro define o atraso máximo permitido na aplicação de WAL. Aumentar este valor permite que queries longas completem sem serem canceladas.
```sql
-- Ver configuração atual
SHOW max_standby_streaming_delay;

-- Opções de configuração:
-- 30s (padrão) - Cancela após 30s de atraso
ALTER SYSTEM SET max_standby_streaming_delay = '30s';

-- -1 - Nunca cancela queries (permite lag indefinido)
ALTER SYSTEM SET max_standby_streaming_delay = '-1';

-- 5min - Para cargas analíticas mais longas
ALTER SYSTEM SET max_standby_streaming_delay = '5min';

-- Aplicar mudanças
SELECT pg_reload_conf();
```

**⚠️ Cuidados**:
- Valores altos ou `-1` **aumentam significativamente o lag de replicação**
- Dados na réplica ficam cada vez mais desatualizados enquanto queries longas rodam
- Use réplicas dedicadas para analytics com esta configuração


### Conflito 2: Limpeza do VACUUM
Outro conflito comum ocorre com operações de VACUUM:

```markdown
LINHA DO TEMPO:

T0: Réplica executando SELECT * FROM usuarios
    Primário executa: DELETE FROM usuarios WHERE inativo = true
    └─> WAL gerado e enviado

T1: Primário executa VACUUM usuarios
    └─> Quer remover tuplas mortas
    └─> ⚠️ MAS réplica ainda está lendo essas tuplas!

T2: ❌ ERRO na réplica!
    "canceling statement due to conflict with recovery"
    └─> Linhas precisam ser removidas mas estão em uso
```

**Problema**: Primário não sabe sobre queries nas réplicas!

**Solução: hot_standby_feedback**

Este parâmetro permite que a réplica informe ao primário sobre suas queries ativas, fazendo o primário adiar o **VACUUM** até que as queries completem.

```sql
-- Habilitar feedback da réplica para o primário
ALTER SYSTEM SET hot_standby_feedback = on;
```

**⚠️ Cuidados**:
- Adia VACUUM no primário, causando **bloat (inchaço) no banco de dados**
- Quanto mais longas as queries na réplica, mais bloat acumula no primário
- Bloat excessivo **degrada performance do primário**
- **Monitore bloat** constantemente se habilitar este parâmetro
- Considere habilitar apenas em réplicas dedicadas para analytics

## Replicação Lógica: Flexibilidade e Seletividade
A replicação lógica foi introduzida nativamente no PostgreSQL na **versão 10**. Diferentemente da replicação física, ela usa um modelo de **publicação e assinatura** (publish/subscribe) e envolve decodificação lógica do WAL antes de enviá-lo para o lado do assinante.

### Características Principais

**Decodificação lógica**: Realizada usando plugins, sendo **pgoutput** o plugin padrão do PostgreSQL.

**Suporte a diferentes versões major**: Você pode replicar entre versões major diferentes. Por exemplo, de PostgreSQL 16 para 17, permitindo usar replicação lógica para upgrades de versão.

**Replicação seletiva**: Diferente da replicação física, você pode replicar apenas um subconjunto de objetos do banco de dados - tabelas específicas, colunas específicas, ou até linhas específicas.

**Paralelismo**: Suporta workers paralelos para aplicação de mudanças.

**Replicação transacional**: Não é replicação byte-a-byte como a física, mas sim baseada em transações lógicas.

### Como Funciona a Replicação Lógica

```markdown
PUBLISHER                         SUBSCRIBER
┌──────────────┐                 ┌──────────────┐
│              │                 │              │
│ WAL → Plugin │ ══Decodifica══> │ Apply Worker │
│  (pgoutput)  │   Transações    │              │
│              │                 │              │
└──────────────┘                 └──────────────┘
```

O processo envolve vários componentes:
1. **WAL sender process**: Envia os registros WAL (como na replicação física)
2. **Plugin de decodificação lógica**: pgoutput decodifica o WAL no lado do publisher
3. **Apply worker**: Aplica as mudanças decodificadas no subscriber

#### Fluxo de Configuração

```sql
-- 1. Copiar o schema da origem para o destino
pg_dump --schema-only -d origem | psql -d destino

-- 2. Criar publication no lado da origem
CREATE PUBLICATION minha_pub FOR TABLE tabela2, tabela3;

-- 3. Criar subscription no lado do destino
CREATE SUBSCRIPTION minha_sub 
CONNECTION 'host=origem port=5432 dbname=db user=usuario password=senha' 
PUBLICATION minha_pub;

-- 4. Slot de replicação é criado automaticamente
-- 5. Snapshot inicial é copiado automaticamente
-- 6. Mudanças contínuas são transmitidas
--    WAL é escrito → Decodificado → Enviado → Aplicado
```

### Parâmetros do Banco de Dados
#### No Publisher (Publicador):

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `wal_level` | `logical` | Não `replica` como na replicação física |
| `max_replication_slots` | Baseado no número de assinantes | Controla slots disponíveis |
| `max_wal_senders` | Baseado no número de processos de envio | Controla senders simultâneos |

#### No Subscriber (Assinante):

| Parâmetro | Descrição |
|-----------|-----------|
| `wal_level` | Também precisa estar configurado adequadamente |
| `max_logical_replication_workers` | Define quantos workers farão o processo de replicação lógica |

### Recursos Avançados
#### Row Filtering (Filtragem de Linhas)
Você não precisa replicar a tabela inteira - pode replicar apenas um subconjunto de linhas usando uma cláusula WHERE:

```sql
CREATE PUBLICATION minha_pub 
FOR TABLE produtos WHERE (preco > 100);
```

#### Column Lists (Listas de Colunas)
Desde o PostgreSQL **versão 15+**, você pode replicar apenas colunas específicas de uma tabela:

```sql
CREATE PUBLICATION minha_pub 
FOR TABLE produtos (id, nome, preco);
```


### Limitações Importantes

| Limitação | Impacto |
|-----------|---------|
| ❌ DDL não replica | Mudanças de schema: manual em ambos lados |
| ❌ Sequences | Não replicam automaticamente |
| ❌ Large objects | Não suportados |
| ❌ Generated columns | Não suportados |
| ⚠️ Apenas tabelas | Views/materialized views causam erros |



## Comparação: Replicação Física vs Lógica

| Aspecto | Replicação Física | Replicação Lógica |
|---------|-------------------|-------------------|
| **Compatibilidade de Versões** | ❌ Mesma versão major obrigatória (WAL sender/receiver precisam ser compatíveis) | ✅ Entre versões major diferentes (ideal para upgrades 16→17) |
| **Tipo de Replicação** | Byte-a-byte (bit-by-bit) - cópia exata | Baseada em transações lógicas |
| **Replicação de DDL** | ✅ Automática (replica tudo) | ❌ Não nativa (PG Logical oferece função) |
| **Roles e Usuários** | ✅ Replica roles/users | ❌ Não replica roles/users |
| **Seletividade** | ❌ Tudo ou nada - replica banco inteiro | ✅ Tabelas/databases específicos |
| **Processo de Transmissão** | Streaming nativo de WAL direto | Decodificação de WAL necessária (Aurora: write-through cache) |
| **Índices Adicionais na Réplica** | ❌ Não permitido (mesmo endereço = mesmos dados) | ✅ Permitido (banco standalone) |
| **Modificações na Réplica** | ❌ Réplica é read-only exata | ✅ Pode modificar tabelas não replicadas (atenção a conflitos) |
| **Processos** | WAL sender → WAL receiver | WAL sender → Decodificação (plugin) → Apply worker |
| **Parâmetro wal_level** | Mínimo: `replica` | Mínimo: `logical` |
| **Uso no RDS** | Read replicas in-region e cross-region, Multi-AZ | Blue-Green Deployments, upgrades de versão |


### Quando Usar

#### Replicação Física

✅ **Use quando**:
- Replicar banco completo
- Mesma versão major
- Alta disponibilidade (Multi-AZ)
- Disaster recovery
- Distribuição de carga de leitura

#### Replicação Lógica

✅ **Use quando**:
- Replicar tabelas específicas
- Upgrades de versão major
- Consolidação de dados de múltiplas fontes
- Migração entre diferentes ambientes
- Necessidade de customizar réplica (índices adicionais, etc.)