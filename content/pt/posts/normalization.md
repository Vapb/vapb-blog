---
title: "Normalização em Bancos de Dados Relacionais"
author: "vapb"
description: "Uma introdução ao conceito de normalização em bancos de dados relacionais e suas formas normais."
date: 2025-12-20
tags: ["Banco de Dados", "SQL"]
toc: true
---

## Introdução

Todo desenvolvedor já viu: aquela tabela com 50 colunas onde metade dos dados se repete em cada row, ou aquele update que precisa rodar em 5 lugares diferentes porque "o mesmo dado mora em várias tabelas". Normalização resolve esses problemas de forma sistemática, mas introduz outros: queries mais complexas, mais joins, schemas menos intuitivos para quem não conhece o domínio. Este post cobre as Formas normais, o processo de normalization, e quando os benefícios compensam os custos.

## O que é normalização em bancos de dados

Normalização é um dos conceitos mais fundamentais e frequentemente mal compreendidos em *database design*.
Trata-se do processo sistemático de organizar dados em um banco relacional para reduzir redundância e melhorar integridade, através da decomposição de tabelas em estruturas menores e bem definidas, estabelecendo relacionamentos claros entre elas.
O objetivo central é eliminar grupos repetidos de dados e garantir que cada elemento seja armazenado de forma lógica e consistente.
Porém, é crucial entender que a normalização não é um fim absoluto. Em determinados contextos, a desnormalização consciente pode ser necessária para atender requisitos específicos de *performance*.

## Formas normais

O processo de normalização é estruturado em níveis progressivos, conhecidos como formas normais.
Cada nível adiciona restrições que aumentam a integridade dos dados.

### 1NF

Uma tabela está em 1NF quando satisfaz três requisitos:
* *Primary key* definida: Cada registro deve ser unicamente identificável
* Atomicidade de valores: Cada campo contém apenas um valor, não múltiplos valores ou grupos repetidos
* Homogeneidade de tipos: Valores em cada coluna devem ser do mesmo tipo de dado

Exemplo de violação de 1NF:
```sql
-- Tabela NÃO está em 1NF
CREATE TABLE pedidos (
    pedido_id INT PRIMARY KEY,
    cliente VARCHAR(100),
    telefones VARCHAR(200)  -- "11-98765-4321, 11-3456-7890"
);

-- Correção para 1NF
CREATE TABLE pedidos (
    pedido_id INT PRIMARY KEY,
    cliente VARCHAR(100)
);

CREATE TABLE pedidos_telefones (
    pedido_id INT REFERENCES pedidos(pedido_id),
    telefone VARCHAR(20),
    PRIMARY KEY (pedido_id, telefone)
);
```

### 2NF

Uma tabela está em 2NF quando:
* Está em 1NF
* Todo atributo não-chave depende completamente da *primary key*
* Não existem dependências parciais (atributos dependendo apenas de parte de uma chave composta)

Exemplo de violação de 2NF:
```sql
-- Chave composta: (employee_id, project_id)
CREATE TABLE employee_projects (
    employee_id INT,
    project_id INT,
    employee_name VARCHAR(100),  -- Depende APENAS de employee_id
    job_code VARCHAR(10),        -- Depende APENAS de employee_id
    project_name VARCHAR(100),   -- Depende APENAS de project_id
    hours_allocated INT,         -- Depende da chave completa
    PRIMARY KEY (employee_id, project_id)
);

-- Correção para 2NF
CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100),
    job_code VARCHAR(10)
);

CREATE TABLE projects (
    project_id INT PRIMARY KEY,
    project_name VARCHAR(100)
);

CREATE TABLE employee_projects (
    employee_id INT REFERENCES employees(employee_id),
    project_id INT REFERENCES projects(project_id),
    hours_allocated INT,
    PRIMARY KEY (employee_id, project_id)
);
```

### 3NF

Uma tabela está em 3NF quando:
* Está em 2NF
* Todo atributo não-chave depende diretamente da *primary key*
* Não existem dependências transitivas (atributos dependendo de outros atributos não-chave)

```sql
-- Chave composta: (employee_id, project_id)
CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100),
    state_code CHAR(2),
    state_name VARCHAR(50)  -- state_name depende de state_code, não de employee_id
);

-- Correção para 3NF
CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100),
    job_code VARCHAR(10)
);

CREATE TABLE projects (
    project_id INT PRIMARY KEY,
    project_name VARCHAR(100)
);

CREATE TABLE employee_projects (
    employee_id INT REFERENCES employees(employee_id),
    project_id INT REFERENCES projects(project_id),
    hours_allocated INT,
    PRIMARY KEY (employee_id, project_id)
);
```

### Boyce-Codd Normal Form (BCNF)

Uma tabela está em BCNF quando:
* Está em 3NF
* Todo determinante (conjunto de atributos que identifica unicamente uma linha) é uma chave candidata

BCNF é uma versão mais restritiva de 3NF que lida com casos específicos de dependências onde 3NF ainda permite anomalias.
Na prática, muitos *schemas* em 3NF já satisfazem BCNF.

## O Processo de Normalização

* **Identificar a Estrutura Inicial**: Começar com a tabela em forma não-normalizada, geralmente refletindo como os dados são coletados ou apresentados ao usuário.
* **Aplicar 1NF**: Eliminar grupos repetidos e garantir atomicidade.
* **Aplicar 2NF**: Identificar e eliminar dependências parciais. Atributos que dependem apenas de parte da *primary key* devem ser movidos para tabelas separadas.
* **Aplicar 3NF**: Identificar e eliminar dependências transitivas. Atributos que dependem de outros atributos não-chave devem ser extraídos para suas próprias tabelas.
* **Validar BCNF (Opcional)**: Verificar se todos os determinantes são chaves candidatas. 

## Benefícios da Normalização

1. **Redução de Redundância**: Cada fato é armazenado uma única vez, eliminando duplicação desnecessária de dados. Isso economiza espaço de armazenamento e reduz inconsistências.
2. **Integridade Aprimorada**: Com dados não-redundantes, atualizações afetam apenas um local. Isso elimina anomalias de atualização onde o mesmo dado poderia ser alterado em alguns lugares mas não em outros.
3. **Manutenção Simplificada**: *Schemas* normalizados são mais fáceis de entender e modificar. Adicionar novos atributos ou entidades não requer alterações em múltiplas tabelas.
4. ***Queries* e *Reporting* Facilitados**: Relacionamentos bem definidos através de *foreign keys* tornam *joins* mais intuitivos e previnem combinações inválidas de dados.
5. ***Performance* Potencialmente Melhor**: Embora a normalização possa aumentar o número de *joins*, ela também reduz o tamanho das tabelas individuais, melhorando a eficiência de *cache* e reduzindo I/O em muitos cenários.

## Quando Desnormalizar

Normalização até 3NF é geralmente o objetivo ideal, mas existem cenários legítimos para desnormalização:
* ***Data Warehouses* e OLAP**: *Schemas* dimensionais (*star*/*snowflake*) intencionalmente desnormalizam para otimizar *queries* analíticas complexas.
* ***Workloads* de Leitura Intensiva**: Quando *queries* específicas são executadas milhares de vezes por segundo, duplicar dados pode eliminar *joins* custosos.
* ***Caching* de Valores Computados**: Armazenar valores agregados (totais, médias) que seriam caros de calcular repetidamente.
