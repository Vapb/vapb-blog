---
title: "Tipos de instância EC2 e Right-Sizing"
author: "vapb"
description: "Introdução aos tipos de instância EC2 e ao conceito de Right-Sizing."
date: 2025-06-26
tags: ["AWS", "EC2"]
toc: true
---

## Introdução
Neste pequeno post, vamos entender os tipos de instâncias EC2, abordar a seleção do tipo correto de instância, a prática do right-sizing e, de forma breve, a ferramenta AWS Compute Optimizer.

## Famílias de Instâncias EC2 da Amazon
A Amazon EC2 oferece mais de 500 tipos de instâncias.
Essas instâncias são organizadas em famílias de instâncias e, dentro delas, em subfamílias.
O nome de cada instância indica sua função e os recursos de hardware disponíveis.

### Tipos de Instância
Uma instância EC2 é uma máquina virtual (VM) que roda na nuvem da AWS.
O tipo de instância determina o hardware do host que será usado. Cada tipo oferece diferentes capacidades de processamento, memória e armazenamento, sendo agrupado em famílias de instância com base nessas características.

**Importante lembrar:**
* Instância = VM na AWS
* Tipo de instância = Conjunto de recursos virtuais (como CPU e memória)
* Família de instância = Conjunto de tipos otimizados para um tipo de uso específico
* Subfamílias = Variações dentro da família baseadas no tipo de processador e armazenamento

### As 5 Famílias de Instância da AWS

#### Uso Geral (General Purpose):
* Equilíbrio entre CPU, memória e rede.
* Ideal para: servidores web, repositórios de código.
* Instâncias burstáveis (T family):
    * Boa para cargas intermitentes que não usam CPU o tempo todo.
    * Oferecem desempenho base com capacidade de "explodir" para desempenho maior por curtos períodos.

#### Otimizada para Processamento (Compute Optimized):
* Ideal para tarefas intensivas de CPU como:
    * Processamento em lote
    * Transcodificação de mídia
    * Servidores de jogos
    * Modelagem científica
    * Inferência de Machine Learning

#### Otimizada para Memória (Memory Optimized):
* Alta performance para cargas que precisam processar grandes volumes de dados em memória.

#### Otimizada para Armazenamento (Storage Optimized):
* Ideal para acesso intenso e sequencial a grandes volumes de dados.
* Otimizadas para alto IOPS (operações de leitura/gravação por segundo).

#### Computação Acelerada (Accelerated Computing):
* Usam aceleradores de hardware como GPUs, FPGAs ou AWS Inferentia
* Perfeitas para tarefas paralelas como:
    * Cálculos de ponto flutuante
    * Processamento gráfico
    * Reconhecimento de padrões

### Como entender os nomes das instâncias

Exemplo: m5zn.xlarge
* m → Família (Uso geral)
* 5 → Geração (quanto maior, mais novo)
* z → Atributo (alta frequência, ideal para tarefas com um único thread)
* n → Otimização adicional (rede com alta largura de banda e baixa latência)
* xlarge → Tamanho (quanto maior, mais recursos de CPU e memória)

#### Tamanhos de instância
* Variam de nano (mínimo de recursos) até 32xlarge (128 vCPUs e 1024 GiB de memória).
* Tamanho define a quantidade de hardware virtual alocada: CPU, memória, rede e armazenamento.

#### Crescimento das famílias de instância
Cada família cresce de acordo com o recurso que é seu foco principal (processador, memória, etc.).

#### Sufixos adicionais nos nomes das instâncias:
* a – Processadores AMD
* g – AWS Graviton
* i – Processadores Intel
* d – Armazenamento local (Instance Store)
* n – Otimização de rede
* b – Otimização para armazenamento em blocos
* e – Memória ou armazenamento extra
* z – Alta frequência de CPU

## Selecionando o Tipo Correto de Instância (Right-Sizing)
A Amazon EC2 oferece uma grande variedade de tipos de instâncias, e muitas vezes você perceberá que sua carga de trabalho pode rodar bem em diferentes tipos e tamanhos de instância.

O objetivo ao escolher o tipo correto de instância é equilibrar o desempenho necessário com o custo adequado.

Right-sizing é o processo de combinar o tipo e o tamanho de recursos com os requisitos reais da sua carga de trabalho.

### Benefícios de novas gerações de instâncias
Usar instâncias de gerações mais recentes, com os novos processadores da AWS, pode:
* Melhorar o desempenho
* Reduzir custos

### Alterando a instância conforme a necessidade
Depois de escolher uma instância, **você não é obrigado a usá-la para sempre**. Se sua carga de trabalho mudar, é possível redimensionar a instância, mudando o tipo dela. Caso ela esteja sobrecarregada ou subutilizada.

Obs: Algumas instâncias permitem troca de tipo com a instância em execução. Outras exigem que a instância seja parada antes da troca. Também é possível criar uma nova instância e migrar sua aplicação para ela


## AWS Compute Optimizer
O AWS Compute Optimizer é uma ferramenta de recomendação de dimensionamento correto (right-sizing) que ajuda a melhorar a eficiência da sua infraestrutura na AWS, fornecendo recomendações de dimensionamento com foco em desempenho e custo.

Ele analisa a configuração atual dos seus recursos e suas métricas de utilização como uso de CPU, memória e armazenamento com base nos dados coletados pelo Amazon CloudWatch nos últimos 14 dias.

Durante essa análise, o serviço identifica padrões e características específicas da carga de trabalho, como uso intensivo de CPU, acessos frequentes a armazenamento local ou variações de uso ao longo do dia. Com essas informações, o Compute Optimizer consegue determinar quais são os recursos de hardware mais adequados para cada workload, sugerindo ajustes que podem reduzir custos e melhorar o desempenho.

    💡 O serviço não tem custo adicional por padrão.