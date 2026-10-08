---
title: "Estante Virtual"
date: 2026-09-21T10:00:00-03:00
description: "Uma estante 3D no navegador com as lombadas, capas e colecionáveis dos meus livros de verdade"
tags: ["hugo", "javascript", "css", "python", "projeto"]
---

> 📚 **Veja ao vivo:** [Abrir a estante]({{< relref "/estante" >}})

## Motivação

Coleciono livros físicos — muito mangá de terror, HQs e livros técnicos — mas a coleção só existia na sala de casa. Apps como Skoob e Goodreads transformam tudo numa **lista** e perdem o que faz uma estante ser legal: as lombadas lado a lado, as séries formando um desenho e os **extras** de colecionador (marca-páginas, cards, sobrecapas).

A ideia: uma página que pareça uma **estante de verdade**. E, de quebra, uma desculpa pra brincar com CSS 3D e animação fora do trabalho.

## O que ela faz

- Prateleiras por categoria, com lombadas no **tamanho real** de cada edição
- Clicar numa lombada **puxa o livro** em 3D: dá pra virar, abrir pela capa ou pelo verso
- **Colecionáveis**: marca-páginas saindo das páginas e um baralho de cards que gira com o mouse
- Busca, navegação por teclado, efeitos sonoros e um easter egg escondido 👀

## Como funciona

Página estática do Hugo, sem framework nem backend:

| Peça | Papel |
|---|---|
| `data/livros.json` | Catálogo com os metadados de cada livro |
| `static/images/estante/<pasta>/` | Uma pasta por livro com fotos de nome fixo (`capa`, `lombada`, `sobrecapa`…) |
| `layouts/_default/estante.html` | Template + CSS + JavaScript puro |

O template descobre sozinho quais fotos cada livro tem — adicionar um livro é só criar a pasta. Dois scripts em Python ajudam: um **scraper** que busca os metadados na Amazon e um **scanner** que endireita e recorta as fotos das capas com OpenCV.
