---
title: "Arquitetura do PostgreSQL: Entendendo o Motor por Trás do Seu Banco de Dados"
author: "vapb"
description: "Mergulho profundo no modelo cliente-servidor do PostgreSQL, processos em background, arquitetura de memória e connection pooling."
date: 2025-11-23
tags: ["PostgreSQL"]
toc: true
---

## 1. Introdução:
Você já parou pra pensar no que acontece quando você manda um SELECT pro PostgreSQL? Tipo, você escreve a query, aperta enter, e boom - os dados aparecem. Parece mágica, mas é só engenharia muito bem feita.

## 2. O Modelo Cliente-Servidor

O PostgreSQL funciona no estilo cliente-servidor clássico. Quando sua aplicação conecta no banco (usando psycopg2, por exemplo), o Postgres não compartilha um único processo gigante entre todo mundo. Não, não. Ele cria um processo backend dedicado só pra você. É tipo ter seu próprio garçom particular num restaurante.
Isso tem suas vantagens: se uma conexão trava ou faz alguma besteira, as outras continuam funcionando de boa. É isolamento de verdade.

Vamos rastrear o que acontece quando sua aplicação executa uma query:
1. **Conexão estabelecida** — Sua app conecta via `psycopg2`. PostgreSQL cria um processo backend dedicado.
2. **Backend process assume** — Este processo lida com todas as queries daquela sessão. Ele tem acesso a:
   - **Memória compartilhada** — O espaço comum que todos os processos podem ler/escrever (`shared_buffers`, `wal_buffers`, `clog_buffers`)
   - **Memória local** — Privada deste processo (`work_mem`, `temp_buffers`)
3. **Execução da query** — O backend lê páginas de dados nos `shared_buffers` (se ainda não estiverem em cache), processa sua query usando memória local para ordenações/joins, e retorna resultados.
4. **Processos em background fazem o resto** — WAL Writer garante que seus commits são duráveis, Checkpointer sincroniza dados no disco, Autovacuum limpa depois.

Esse design multi-processo é intencional. Cada conexão tem isolamento. Se um backend trava ou se comporta mal, não derruba outras conexões. Também escala naturalmente: mais conexões simplesmente significam mais processos backend.

Esse fluxo explica por que a configuração de memória importa: `shared_buffers` afetam todos, enquanto `work_mem` multiplicado por `max_connections` determina seu teto de memória.

### 2.1. Connection Pooling: A Parte Que Todo Mundo Confunde
Aqui vai um erro clássico: pensar que cada usuário = uma conexão no banco. Na real, não é bem assim.
Imagina sua API rodando em 5 pods no Kubernetes. Cada pod mantém um pool de, digamos, 10 conexões abertas (via SQLAlchemy, por exemplo). O PostgreSQL vê 50 processos backend, não importa se tem 10 ou 10.000 usuários acessando sua API ao mesmo tempo.

Sem pooling, cada requisição HTTP abriria uma nova conexão, usaria, e fecharia. Isso é absurdamente caro porque criar processos backend demora. Com pooling, as conexões ficam abertas e são reutilizadas.

E se você tem MUITA escala? Aí entra o PgBouncer, que adiciona uma camada de pooling centralizada antes do banco. Mas isso é assunto pra outro post.

## 3. Processos em Background: Os Trabalhadores Silenciosos

Enquanto processos backend lidam com suas queries, vários processos em background rodam continuamente para manter o banco saudável. Pense neles como a equipe de manutenção trabalhando nos bastidores.

### 3.1. Mantendo Dados Seguros (Durabilidade)

* **WAL Writer**: Cada vez que você dá commit, ele garante que tudo foi escrito no Write-Ahead Log antes do Postgres dizer "ok, salvei". Roda a cada 200ms.
* **Checkpointer**: De tempos em tempos (geralmente a cada 5 minutos), ele pega todos os dados que estão na memória e sincroniza tudo pro disco.
* **Background Writer**: Distribui o trabalho de I/O. Em vez de esperar o Checkpointer despejar tudo de uma vez (o que poderia congelar suas queries), ele escreve páginas sujas gradualmente em background.

### 3.2. Manutenção no Piloto Automático

* **Autovacuum**: Quando você deleta uma linha, ele não apaga de verdade na hora. Só marca como "morta". O Autovacuum passa depois e recupera esse espaço. Ele também atualiza as estatísticas que o planejador de queries usa.

### 3.3. Replicação e Recuperação

* **Archiver**: Salva os arquivos WAL antigos antes deles serem reciclados. Super importante se você precisa fazer point-in-time recovery ("me restaura o banco de ontem às 15h").

* **WAL Sender e Receiver**: Essa dupla é responsável por manter suas réplicas sincronizadas. O Sender envia as mudanças do primário, o Receiver aplica na réplica.

### 3.4. Observabilidade

* **Logger**: É quem escreve nos seus arquivos de log. Quer rastrear queries lentas? É ele. Só fica esperto com o espaço em disco se habilitar logging muito verboso.


## 4. Arquitetura de Memória

{{<figure class="post_image" src="../images/pg-architecture/01_pg_arch.png">}}

PostgreSQL divide memória em duas áreas distintas: memória compartilhada (usada por todos os processos) e memória local (por conexão).

### 4.1. Memória Compartilhada

* **`shared_buffers`** é o cache central de dados. Quando PostgreSQL lê uma página do disco, ela vai para cá. Quando você modifica dados, as mudanças acontecem aqui primeiro antes de serem escritas no disco. **Pense nele como a RAM do seu banco**.
* **`wal_buffers`** Guarda os registros de transação temporariamente antes de irem pro disco. Geralmente é pequeno (poucos MB) porque é descarregado frequentemente.
* **`clog_buffers`** Rastreia o estado de cada transação (commitada, abortada, em progresso). 

### 4.2. Memória Local (Por Processo)

Cada processo backend recebe sua própria alocação de memória local:

* **`work_mem`** é usado para ordenação e hash joins. Cada operação em uma query pode usar até essa quantidade—então uma query complexa com múltiplas ordenações pode usar várias vezes `work_mem`. Quando insuficiente, PostgreSQL despeja para arquivos temporários no disco, o que é significativamente mais lento.
* **`temp_buffers`** armazenam tabelas temporárias. Só alocado quando você realmente cria objetos temporários.
* **`maintenance_work_mem`** é usado para operações de manutenção como `VACUUM`, `CREATE INDEX`, e `ALTER TABLE`. O padrão é 64MB, mas aumentar isso pode acelerar significativamente essas operações.

### 4.3. O Trade-off de Memória

Existe uma tensão inerente aqui. `shared_buffers` beneficia todos mas tem retornos decrescentes após certo ponto (o SO também faz cache). `work_mem` ajuda queries individuais mas multiplique pelo seu `max_connections` e pode esgotar RAM rapidamente. Encontrar o balanço certo depende do seu workload.

{{< hint warning >}}
**Fórmula de memória**: Uso total de memória ≈ `shared_buffers` + (`work_mem` × `max_connections` × operações por query). Uma query complexa com 5 ordenações usando 256MB de `work_mem` e 100 conexões poderia consumir 128GB só para ordenação.
{{< /hint >}}

## 5. Por Que Esta Arquitetura Importa

"Tá, Victor, mas eu só quero escrever minhas queries e ser feliz."

Eu te entendo, mas conhecer essa arquitetura te dá superpoderes de troubleshooting:

CPU alto? Verifica se são seus processos backend (suas queries) ou processos em background (manutenção).
Replicação atrasada? Olha pros WAL Sender/Receiver.
I/O de disco disparou? Pode ser o Checkpointer fazendo seu trabalho.
Queries lentas do nada? Talvez o Autovacuum precise rodar com mais frequência.

No final das contas, banco de dados não é magia. É só engenharia bem feita. E quando você entende como as peças se encaixam, fica muito mais fácil fazer tudo funcionar direito.