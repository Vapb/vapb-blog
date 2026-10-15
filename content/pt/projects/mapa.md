---
title: "Mapa do Blog"
date: 2026-10-14T10:00:00-03:00
description: "A estrutura do blog (posts, seções, projetos e tags) desenhada como uma árvore navegável"
tags: ["hugo", "javascript", "css", "projeto"]
aliases: ["/projects/grafo/"]
---

> 🌳 **Veja ao vivo:** [Abrir o mapa]({{< relref "/mapa" >}})

## Motivação

Com o blog crescendo, uma lista cronológica e uma nuvem de tags deixam de mostrar **como as coisas se organizam**. A ideia, assim como na [Estante]({{< relref "/projects/estante.md" >}}), é transformar a estrutura do próprio projeto numa visualização, no estilo de um *sitemap* visual.

A primeira tentativa foi um **grafo de forças**, mas ele era difícil de ler e de interagir: nós se mexendo o tempo todo, tags embolando as seções. Como o blog tem uma hierarquia clara, uma **árvore** mostra o mesmo conteúdo de forma mais direta.

## O que ela mostra

```
VAPB BLOG
 ├─ posts ─ seção ─ post
 ├─ projetos ─ projeto
 └─ sobre mim
```

- Clicar numa seção **abre e fecha**; o ícone ↗ (ou o duplo clique, ou Enter) abre a página
- A profundidade se lê pelo recuo, pelos ícones e pelo peso do texto, com um único acento de cor
- **Tags** e **busca** filtram a árvore: ficam só os ramos com resultado, com contadores como "3 de 7"
- Navegação completa por **teclado**, no padrão ARIA de árvore

## Como funciona

HTML e CSS gerados pelo próprio Hugo a partir das seções e das tags, mais um JS pequeno para o filtro, a animação de abrir e fechar e o teclado. Sem canvas nem dependências, então uma seção ou post novo entra sozinho.

## Próximos passos

- Nível de **série** entre a seção e o post (partes de um mesmo assunto)
- Selos de "novo" e tempo de leitura nos posts
- Guardar filtros e seções abertas na URL
