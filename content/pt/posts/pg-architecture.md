---
title: "Arquitetura do PostgreSQL: Entendendo o Motor por Trás do Seu Banco de Dados"
author: "vapb"
description: "Mergulho profundo no modelo cliente-servidor do PostgreSQL, processos em background, arquitetura de memória e connection pooling."
date: 2025-11-23
tags: ["PostgreSQL"]
toc: true
---
## 1. O Modelo Cliente-Servidor

O PostgreSQL segue uma arquitetura cliente-servidor direta. Quando sua aplicação se conecta ao banco de dados, isso é o que acontece:

1. Sua aplicação (usando `psycopg2` em Python, `JDBC` em Java) inicia uma conexão
2. O processo principal do Postgres recebe a requisição
3. Um **backend process** dedicado é criado apenas para aquela conexão
4. Esse backend processa todas as queries daquela sessão específica

Esse design multi-processo é intencional. Cada conexão tem isolamento. Se um backend trava ou se comporta mal, não derruba outras conexões. Também escala naturalmente: mais conexões simplesmente significam mais processos backend.


### 1.1. Como uma Conexão Realmente Funciona

Vamos rastrear o que acontece quando sua aplicação executa uma query:

1. **Conexão estabelecida** — Sua app conecta via `psycopg2`. PostgreSQL cria um processo backend dedicado.
2. **Backend process assume** — Este processo lida com todas as queries daquela sessão. Ele tem acesso a:
   - **Memória compartilhada** — O espaço comum que todos os processos podem ler/escrever (`shared_buffers`, `wal_buffers`, `clog_buffers`)
   - **Memória local** — Privada deste processo (`work_mem`, `temp_buffers`)
3. **Execução da query** — O backend lê páginas de dados nos `shared_buffers` (se ainda não estiverem em cache), processa sua query usando memória local para ordenações/joins, e retorna resultados.
4. **Processos em background fazem o resto** — WAL Writer garante que seus commits são duráveis, Checkpointer sincroniza dados no disco, Autovacuum limpa depois.

Esse fluxo explica por que a configuração de memória importa: `shared_buffers` afetam todos, enquanto `work_mem` multiplicado por `max_connections` determina seu teto de memória.

### 1.2. Conexões em Produção: Pods, Pools e Realidade

Um equívoco comum: "cada usuário = uma conexão." Não exatamente. Em um setup típico com uma API rodando em múltiplos pods:

```
Usuários A, B, C ──► Pod 1 ──┐
                              ├──► Connection Pool ──► Backend Processes
Usuários D, E, F ──► Pod 2 ──┘
```

Cada pod mantém um **connection pool** (via SQLAlchemy, HikariCP, etc.). Se você tem 5 pods com um pool de 10 conexões cada, PostgreSQL vê 50 processos backend—independente de 100 ou 10.000 usuários estarem acessando sua API.

Sem pooling, cada requisição HTTP abriria uma nova conexão, usaria brevemente, e fecharia. Criar processos backend é caro, então isso mata a performance. Com pooling, conexões ficam abertas e são reutilizadas entre requisições. Para cenários de alta escala, **PgBouncer** adiciona pooling centralizado entre todos os pods.


## 2. Processos em Background: Os Trabalhadores Silenciosos

Enquanto processos backend lidam com suas queries, vários processos em background rodam continuamente para manter o banco saudável. Pense neles como a equipe de manutenção trabalhando nos bastidores.

### 2.1. Mantendo Dados Seguros (Durabilidade)

{{< details title="WAL Writer" >}}
Seu guardião de transações. Cada mudança que você commita precisa estar no disco antes do PostgreSQL dizer "pronto." Este processo descarrega os buffers do Write-Ahead Log para o disco a cada 200ms, garantindo que seus dados sobrevivam a crashes.
{{< /details >}}

{{< details title="Checkpointer" >}}
Sincroniza tudo periodicamente. Enquanto o WAL Writer salva o log de "o que mudou", o Checkpointer escreve as páginas de dados reais da memória para o disco. Roda a cada 5 minutos ou quando o WAL atinge 2GB.
{{< /details >}}

{{< details title="Background Writer" >}}
Distribui o trabalho de I/O. Em vez de esperar o Checkpointer despejar tudo de uma vez (o que poderia congelar suas queries), ele escreve páginas sujas gradualmente em background.
{{< /details >}}

### 2.2. Manutenção no Piloto Automático

{{< details title="Autovacuum Launcher and Workers" >}}
Sua equipe de limpeza. PostgreSQL não deleta linhas imediatamente—ele as marca como mortas. Autovacuum recupera esse espaço e atualiza estatísticas para o planejador de queries. Também previne transaction ID wraparound, um problema raro mas catastrófico se ignorado.
{{< /details >}}

### 2.3. Replicação e Recuperação

{{< details title="Archiver" >}}
Salva arquivos WAL antes de serem reciclados. Crítico se você precisa de point-in-time recovery ("restaure meu banco para ontem às 15h") ou alimentar réplicas que ficaram para trás.
{{< /details >}}

{{< details title="WAL Sender and Receiver" >}}
Lidam com streaming replication. Sender envia WAL do primário para réplicas; Receiver aplica. É assim que read replicas ficam sincronizadas.
{{< /details >}}

### 2.4. Observabilidade

{{< details title="Logger" >}}
Escreve nos seus arquivos de log baseado na configuração. Log de queries lentas, rastreamento de erros, tentativas de conexão—tudo aqui. Só fique atento ao espaço em disco se habilitar logging verboso.
{{< /details >}}


## 3. Arquitetura de Memória

{{<figure class="post_image" src="../images/pg-architecture/01_pg_arch.png">}}

PostgreSQL divide memória em duas áreas distintas: memória compartilhada (usada por todos os processos) e memória local (por conexão).

### 3.1. Memória Compartilhada

* **`shared_buffers`** é o cache central de dados. Quando PostgreSQL lê uma página do disco, ela vai para cá. Quando você modifica dados, as mudanças acontecem aqui primeiro antes de serem escritas no disco.
* **`wal_buffers`** temporariamente guardam registros de log de transação antes do WAL Writer descarregá-los no disco. São tipicamente pequenos (alguns MB) já que são descarregados frequentemente.
* **`clog_buffers`** rastreiam estados de transação—se cada transação foi commitada, abortada, ou ainda está em progresso. Essencial para MVCC determinar visibilidade de tuplas.

### 3.2. Memória Local (Por Processo)

Cada processo backend recebe sua própria alocação de memória local:

* **`work_mem`** é usado para ordenação e hash joins. Cada operação em uma query pode usar até essa quantidade—então uma query complexa com múltiplas ordenações pode usar várias vezes `work_mem`. Quando insuficiente, PostgreSQL despeja para arquivos temporários no disco, o que é significativamente mais lento.
* **`temp_buffers`** armazenam tabelas temporárias. Só alocado quando você realmente cria objetos temporários.
* **`maintenance_work_mem`** é usado para operações de manutenção como `VACUUM`, `CREATE INDEX`, e `ALTER TABLE`. O padrão é 64MB, mas aumentar isso pode acelerar significativamente essas operações.

### 3.3. O Trade-off de Memória

Existe uma tensão inerente aqui. `shared_buffers` beneficia todos mas tem retornos decrescentes após certo ponto (o SO também faz cache). `work_mem` ajuda queries individuais mas multiplique pelo seu `max_connections` e pode esgotar RAM rapidamente. Encontrar o balanço certo depende do seu workload.

{{< hint warning >}}
**Fórmula de memória**: Uso total de memória ≈ `shared_buffers` + (`work_mem` × `max_connections` × operações por query). Uma query complexa com 5 ordenações usando 256MB de `work_mem` e 100 conexões poderia consumir 128GB só para ordenação.
{{< /hint >}}

## 4. Por Que Esta Arquitetura Importa

Entender esta arquitetura ajuda você a debugar e otimizar. Quando você vê alto uso de CPU, pode verificar se são processos backend (suas queries) ou processos em background (tarefas de manutenção). Quando replicação atrasa, você sabe olhar para WAL Sender/Receiver. Quando I/O de disco dispara, pode ser o checkpointer fazendo seu trabalho.
