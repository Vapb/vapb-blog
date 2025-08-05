---
title: "Tipos de instância EC2 e Right-Sizing"
author: "vapb"
description: "Introdução aos tipos de instância EC2 e ao conceito de Right-Sizing."
date: 2025-06-26
tags: ["AWS", "EC2"]
toc: true
---

## Introdução

Neste pequeno post, vamos entender os tipos de instâncias EC2, abordar a seleção do tipo correto de instância, a prática do _right-sizing_ e, de forma breve, a ferramenta **AWS Compute Optimizer**.

---

## Famílias de Instâncias EC2 da Amazon

A Amazon EC2 oferece mais de **500 tipos de instâncias**, organizadas em **famílias** e **subfamílias**. O nome de cada instância indica sua função e os recursos de hardware disponíveis.

### Tipos de Instância
Uma instância EC2 é uma máquina virtual (VM) que roda na nuvem da AWS.
O tipo de instância determina o hardware do host que será usado. Cada tipo oferece diferentes capacidades de processamento, memória e armazenamento, sendo agrupado em famílias de instância com base nessas características.

**Importante lembrar:**
- **Instância** = VM na AWS  
- **Tipo de instância** = Conjunto de recursos virtuais (CPU, memória, etc.)  
- **Família de instância** = Conjunto de tipos otimizados para um uso específico  
- **Subfamílias** = Variações com base no processador ou armazenamento  

---

### As 5 Famílias de Instância da AWS

#### Uso Geral (General Purpose)

- **Equilíbrio entre CPU, memória e rede**
- Ideal para: servidores web, repositórios de código
- **Instâncias burstáveis (família T):**
    - Boa para cargas intermitentes
    - Oferecem desempenho base com picos temporários

#### Otimizadas para Processamento (Compute Optimized)

- Ideais para tarefas intensivas de CPU:
    - Processamento em lote
    - Transcodificação de mídia
    - Servidores de jogos
    - Modelagem científica
    - Inferência de Machine Learning

#### Otimizadas para Memória (Memory Optimized)

- Alta performance para grandes volumes de dados em memória

#### Otimizadas para Armazenamento (Storage Optimized)

- Foco em acesso intenso e sequencial a dados
- Otimizadas para alto IOPS

#### Computação Acelerada (Accelerated Computing)

- Utilizam **GPUs, FPGAs ou AWS Inferentia**:
    - Cálculos de ponto flutuante
    - Processamento gráfico
    - Reconhecimento de padrões

### Como Entender os Nomes das Instâncias

Exemplo: `m5zn.xlarge`

| Segmento | Significado |
|----------|-------------|
| `m`      | Família: uso geral |
| `5`      | Geração (quanto maior, mais novo) |
| `z`      | Atributo especial: alta frequência |
| `n`      | Otimização de rede |
| `xlarge`| Tamanho da instância |

#### Tamanhos Disponíveis

- Variam de `nano` até `32xlarge` (128 vCPUs e 1024 GiB de memória)
- Tamanho define recursos de CPU, memória, rede e armazenamento

### Sufixos Comuns

| Sufixo | Significado                           |
|--------|---------------------------------------|
| `a`    | Processador AMD                      |
| `g`    | AWS Graviton                         |
| `i`    | Processador Intel                    |
| `d`    | Armazenamento local (Instance Store)|
| `n`    | Otimização de rede                   |
| `b`    | Otimização para armazenamento em blocos |
| `e`    | Mais memória ou armazenamento        |
| `z`    | Alta frequência de CPU               |

---

## Selecionando o Tipo Correto de Instância (Right-Sizing)
A Amazon EC2 oferece uma grande variedade de tipos de instâncias, e muitas vezes você perceberá que sua carga de trabalho pode rodar bem em diferentes tipos e tamanhos de instância.

O objetivo do _right-sizing_ é **equilibrar desempenho e custo** com base nas necessidades reais da sua aplicação, evitando que a instância fique sobrecarregada ou subutilizada.

### Benefícios de Novas Gerações
Usar instâncias de gerações mais recentes, com os novos processadores da AWS, pode:
- Melhor desempenho
- Menor custo

### Alterando a instância conforme a necessidade
Depois de escolher uma instância, **você não é obrigado a usá-la para sempre**. Se sua carga de trabalho mudar, é possível redimensionar a instância, mudando o tipo dela. Caso ela esteja sobrecarregada ou subutilizada.

> ⚠️ Algumas instâncias permitem troca de tipo com a instância em execução. Outras exigem que a instância seja parada antes da troca. Também é possível criar uma nova instância e migrar sua aplicação para ela

---

## AWS Compute Optimizer

O **AWS Compute Optimizer** é uma ferramenta de_right-sizing_ que ajuda a melhorar a eficiência da sua infraestrutura na AWS, fornecendo recomendações de dimensionamento com foco em desempenho e custo.

Ele analisa a configuração atual dos seus recursos e suas métricas de utilização como uso de CPU, memória e armazenamento com base nos dados coletados pelo **Amazon CloudWatch** nos últimos 14 dias.

Durante essa análise, o serviço identifica padrões e características específicas da carga de trabalho, como uso intensivo de CPU, acessos frequentes a armazenamento local ou variações de uso ao longo do dia. Com essas informações, o **Compute Optimizer** consegue determinar quais são os recursos de hardware mais adequados para cada workload, sugerindo ajustes que podem reduzir custos e melhorar o desempenho.

> 💡 O Compute Optimizer **não tem custo adicional** por padrão.
