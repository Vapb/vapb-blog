---
title: "Tipos de instância EC2 e right-sizing"
author: "vapb"
description: "Introdução aos tipos de instância EC2 e ao conceito de right-sizing."
date: 2025-06-26
tags: ["AWS", "EC2"]
toc: true
---

## 1. Introdução

Neste post, vamos entender os tipos de instâncias EC2, abordar a seleção do tipo correto de instância, a prática do _right-sizing_ e, de forma breve, a ferramenta **AWS Compute Optimizer**.

## 2. Famílias de instâncias EC2 da Amazon

A Amazon EC2 oferece mais de **500 tipos de instâncias**, organizadas em **famílias** e **subfamílias**. O nome de cada instância indica sua função e os recursos de hardware disponíveis.

### 2.1. Tipos de instância

Uma instância EC2 é uma máquina virtual (VM) que roda na nuvem da AWS. O tipo de instância determina o hardware do host que será usado. Cada tipo oferece diferentes capacidades de processamento, memória e armazenamento, sendo agrupado em famílias de instância com base nessas características.

{{< hint info >}}
**Conceitos importantes:**
- **Instância** = VM na AWS
- **Tipo de instância** = Conjunto de recursos virtuais (CPU, memória, etc.)
- **Família de instância** = Conjunto de tipos otimizados para um uso específico
- **Subfamílias** = Variações com base no processador ou armazenamento
{{< /hint >}}

## 3. As 5 famílias de instância da AWS

### 3.1. Uso geral (General Purpose)

Projetadas para oferecer um equilíbrio entre CPU, memória e rede, são a opção mais versátil para aplicações gerais.

#### 3.1.1. Família T (burstable)

Instâncias com CPU variável que acumulam créditos quando ociosas.

{{< details title="Quando usar" >}}
- Workloads com uso de CPU baixo ou variável
- Aplicações que precisam de performance elevada apenas em picos
{{< /details >}}

{{< details title="Como funciona" >}}
Você ganha **créditos de CPU** quando a instância está abaixo do baseline de CPU e pode usá-los para ter mais performance durante picos:
- **Modo standard**: se os créditos acabam, o desempenho é reduzido ao baseline
- **Modo unlimited**: continua performando acima do baseline, mas você paga pelo extra usado
{{< /details >}}

#### 3.1.2. Família M (performance constante)

Instâncias com CPU consistente sem sistema de créditos.

{{< details title="Quando usar" >}}
- Workloads que precisam de CPU constante e previsível
- Ambientes de produção críticos
- Aplicações que usam CPU total continuamente
{{< /details >}}

### 3.2. Otimizadas para processamento (Compute Optimized)

Projetadas com processadores de alto desempenho, essas instâncias oferecem a maior relação CPU/memória entre todas as famílias, sendo ideais para cargas de trabalho que demandam poder computacional intensivo.

#### 3.2.1. Família C (compute)

Processadores de última geração com alto clock, otimizada para cargas CPU-intensive. Melhor custo por vCPU.

{{< details title="Quando usar" >}}
- Aplicações "CPU-bound" (limitadas por processamento)
- Workloads que processam dados intensivamente
- Quando CPU é o recurso crítico, não memória
{{< /details >}}

### 3.3. Otimizadas para memória (Memory Optimized)

Projetadas para fornecer grandes quantidades de memória RAM em relação aos núcleos de CPU, essas instâncias são ideais para cargas de trabalho que processam extensos conjuntos de dados na memória.

#### 3.3.1. Família R (RAM-optimized)

A mais popular para workloads com alta demanda de memória. Oferece **8 GB de RAM por vCPU** (dobro das general purpose).

#### 3.3.2. Família X (extreme memory)

Memória extrema com até **16 GB de RAM por vCPU** e configurações de **4+ TB** por instância.

{{< details title="Quando usar" >}}
- Bancos de dados in-memory massivos (SAP HANA)
- Aplicações legacy que não escalam horizontalmente
- Consolidação de grandes cargas em poucos servidores
{{< /details >}}

#### 3.3.3. Família z1d (high compute + high memory)

Combina alta frequência de CPU (até 4.0 GHz) com muita memória e NVMe local.

{{< details title="Quando usar" >}}
- Bancos de dados que exigem CPU e memória elevadas
- Cargas OLTP de alto volume
- Workloads que precisam de processamento rápido e muita RAM
{{< /details >}}

### 3.4. Otimizadas para armazenamento (Storage Optimized)

Projetadas para fornecer armazenamento local de altíssima performance com acesso sequencial rápido e IOPS (operações de entrada/saída por segundo) extremamente elevados, essas instâncias são ideais para cargas de trabalho que exigem leitura e gravação intensiva de dados.

#### 3.4.1. Família I (I/O intensive)

NVMe SSD local com baixíssima latência e milhões de IOPS. Instâncias I4i entregam até **60 GB/s** e **400k+ IOPS**.

{{< details title="Quando usar" >}}
- Bancos de dados transacionais de alto volume
- Aplicações que precisam de latência submilissegundo
- Cargas OLTP críticas
{{< /details >}}

#### 3.4.2. Família D (dense storage)

HDD otimizado para throughput sequencial com maior densidade de armazenamento por custo (dezenas de TB por instância).

{{< details title="Quando usar" >}}
- Data lakes
- Arquivos de log históricos
- Processamento MapReduce
- Data warehouses com scan sequencial
- Armazenamento massivo local
{{< /details >}}

#### 3.4.3. Família H1 (HDD optimized)

Otimizada para frameworks de big data (Hadoop, Spark) com foco em throughput sequencial.

{{< details title="Quando usar" >}}
- Clusters de processamento distribuído
- Workloads onde custo por TB é crítico
- Cenários onde latência não é o principal gargalo
{{< /details >}}

{{< hint warning >}}
**⚠️ Armazenamento efêmero**: O storage dessas instâncias é local e temporário (instance store). Se a instância for parada ou encerrada, todos os dados são perdidos. Use EBS ou S3 para persistência de longo prazo.
{{< /hint >}}

### 3.5. Computação acelerada (Accelerated Computing)

Equipadas com hardware especializado como GPUs, FPGAs ou chips customizados da AWS, essas instâncias são projetadas para realizar cálculos paralelos massivos que seriam ineficientes ou extremamente lentos em CPUs tradicionais.

{{< details title="Quando usar" >}}
- Treinamento e inferência de modelos de machine learning e deep learning
- Processamento de imagens e vídeos em larga escala
- Renderização 3D e computação gráfica
- Simulações científicas e modelagem computacional
- Análise genômica e bioinformática
- Mineração de criptomoedas e cálculos de blockchain
- Reconhecimento de padrões e processamento de linguagem natural (NLP)
{{< /details >}}

#### 3.5.1. Família P (performance GPU - NVIDIA)

GPUs NVIDIA de alta performance (A100, V100, H100) para treinamento de modelos e computação científica.

{{< details title="Quando usar" >}}
- Treinamento de redes neurais profundas
- Pesquisa em IA
- Simulações de dinâmica molecular
- Análise de dados científicos complexos
{{< /details >}}

#### 3.5.2. Família G (graphics - GPU de propósito geral)

GPUs NVIDIA (T4, A10G) balanceadas para machine learning e computação gráfica.

{{< details title="Quando usar" >}}
- Estações de trabalho virtuais
- Streaming de jogos
- Renderização de vídeo
- Inferência de modelos de ML em produção
- Aplicações que combinam gráficos e IA
{{< /details >}}

#### 3.5.3. Família Inf (AWS Inferentia)

Chips customizados da AWS otimizados exclusivamente para inferência de modelos ML (não treinamento).

{{< details title="Quando usar" >}}
- Recomendação de produtos
- Classificação de imagens
- Chatbots
- Detecção de fraudes
- Deploy de modelos já treinados em produção
{{< /details >}}

#### 3.5.4. Família Trn (AWS Trainium)

Chips customizados da AWS para treinamento de deep learning com melhor custo-benefício que GPUs.

{{< details title="Quando usar" >}}
- Treinamento de modelos de linguagem (LLMs)
- Modelos de visão computacional
- Workloads de treinamento distribuído
{{< /details >}}

#### 3.5.5. Família F (FPGA - Field Programmable Gate Arrays)

FPGAs programáveis que permitem criar hardware customizado para algoritmos específicos.

{{< details title="Quando usar" >}}
- Processamento de dados financeiros de alta frequência
- Compressão/descompressão em tempo real
- Aceleração de algoritmos de criptografia
- Análise de redes e segurança
{{< /details >}}

{{< hint warning >}}
**💰 Custo elevado**: Essas são as instâncias mais caras da AWS. Uma única instância P5 pode custar mais de $30/hora. Certifique-se de que realmente precisa desse poder computacional.
{{< /hint >}}

### 3.6. Como entender os nomes das instâncias

Exemplo: `m5zn.xlarge`

| Segmento | Significado |
|----------|-------------|
| `m`      | Família: uso geral |
| `5`      | Geração (quanto maior, mais novo) |
| `z`      | Atributo especial: alta frequência |
| `n`      | Otimização de rede |
| `xlarge` | Tamanho da instância |

#### 3.6.1. Tamanhos disponíveis

- Variam de `nano` até `32xlarge` (128 vCPUs e 1024 GiB de memória)
- Tamanho define recursos de CPU, memória, rede e armazenamento

### 3.7. Sufixos comuns

| Sufixo | Significado                           |
|--------|---------------------------------------|
| `a`    | Processador AMD                      |
| `g`    | AWS Graviton                         |
| `i`    | Processador Intel                    |
| `d`    | Armazenamento local (instance store) |
| `n`    | Otimização de rede                   |
| `b`    | Otimização para armazenamento em blocos |
| `e`    | Mais memória ou armazenamento        |
| `z`    | Alta frequência de CPU               |

## 4. Selecionando o tipo correto de instância (right-sizing)

A Amazon EC2 oferece uma grande variedade de tipos de instâncias, e muitas vezes você perceberá que sua carga de trabalho pode rodar bem em diferentes tipos e tamanhos de instância.

O objetivo do _right-sizing_ é **equilibrar desempenho e custo** com base nas necessidades reais da sua aplicação, evitando que a instância fique sobrecarregada ou subutilizada.

### 4.1. Benefícios de novas gerações

{{< hint info >}}
**🚀 Melhor custo-benefício**: Usar instâncias de gerações mais recentes, com os novos processadores da AWS, pode trazer melhor desempenho e menor custo.
{{< /hint >}}

### 4.2. Alterando a instância conforme a necessidade

Depois de escolher uma instância, **você não é obrigado a usá-la para sempre**. Se sua carga de trabalho mudar, é possível redimensionar a instância, mudando o tipo dela caso esteja sobrecarregada ou subutilizada.

{{< hint warning >}}
**⚠️ Atenção ao redimensionar**: Algumas instâncias permitem troca de tipo com a instância em execução. Outras exigem que a instância seja parada antes da troca. Também é possível criar uma nova instância e migrar sua aplicação para ela.
{{< /hint >}}

## 5. AWS Compute Optimizer

O **AWS Compute Optimizer** é uma ferramenta de _right-sizing_ que ajuda a melhorar a eficiência da sua infraestrutura na AWS, fornecendo recomendações de dimensionamento com foco em desempenho e custo.

Ele analisa a configuração atual dos seus recursos e suas métricas de utilização como uso de CPU, memória e armazenamento com base nos dados coletados pelo **Amazon CloudWatch** nos últimos **14 dias**.

{{< details title="Como funciona o Compute Optimizer" >}}
Durante a análise, o serviço identifica padrões e características específicas da carga de trabalho, como:
- Uso intensivo de CPU
- Acessos frequentes a armazenamento local
- Variações de uso ao longo do dia

Com essas informações, o **Compute Optimizer** consegue determinar quais são os recursos de hardware mais adequados para cada workload, sugerindo ajustes que podem reduzir custos e melhorar o desempenho.
{{< /details >}}

{{< hint info >}}
**💡 Sem custo adicional**: O Compute Optimizer não tem custo adicional por padrão.
{{< /hint >}}
