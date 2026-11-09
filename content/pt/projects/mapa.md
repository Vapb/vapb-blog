---
title: "Mapa do Blog"
date: 2026-10-14T10:00:00-03:00
description: "A estrutura do blog (posts, seções, projetos e tags) desenhada como um grafo direcionado navegável"
tags: ["hugo", "javascript", "css", "projeto"]
---

> 🕸️ **Veja ao vivo:** [Abrir o mapa]({{< relref "/mapa" >}})

## Motivação

Com o blog crescendo, uma lista cronológica e uma nuvem de tags deixam de mostrar **como as coisas se organizam**. A ideia, assim como na [Estante]({{< relref "/projects/estante.md" >}}), é transformar a estrutura do próprio projeto numa visualização, no estilo de um *sitemap* visual.

A primeira tentativa foi um **grafo de forças**, mas ele era difícil de ler e de interagir: nós se mexendo o tempo todo, tags embolando as seções. Passei então para uma **árvore** em lista, que mostrava o mesmo conteúdo de forma mais direta, mas sem passar a ideia de caminho entre as páginas.

A versão atual volta ao grafo de outro jeito: em vez de uma simulação de forças, um **grafo direcionado em camadas**, com posições determinísticas e setas do pai para o filho. A árvore em lista foi removida.

## O que ela mostra

```
VAPB BLOG ─▶ posts ─▶ seção ─▶ post
          ├─▶ projetos ─▶ projeto
          └─▶ sobre mim
```

- Os nós são ligados por **setas**, da esquerda para a direita; passar o mouse acende o **caminho da raiz até o nó**
- Um clique **seleciona** (e, numa pasta, abre ou fecha, com o número de filhos no selo); a página só abre com **duplo clique**, com o ícone ↗ ou com Enter, para evitar cliques acidentais
- Dá para **arrastar** para mover o grafo e usar **Ctrl + rolagem** (ou os botões) para o zoom
- **Tags** e **busca** filtram o grafo: ficam só os ramos com resultado, e os selos contam só o que sobrou
- **Teclado**: setas para navegar, abrir e fechar pastas, Enter para abrir a página

## Como funciona

O Hugo gera só a lista de nós (cada um com o seu pai) a partir das seções e das páginas, e um JS pequeno desenha o resto em SVG, sem canvas nem dependências. Uma seção ou post novo entra sozinho.

O layout é por camadas: a **profundidade** vira a coluna, cada nó fica centrado sobre os filhos e as arestas são curvas com ponta de seta. As posições só mudam quando uma pasta abre ou fecha, e o nó clicado fica parado na tela.

## Próximos passos

- Nível de **série** entre a seção e o post (partes de um mesmo assunto)
- Selos de "novo" e tempo de leitura nos posts
- Guardar filtros e pastas abertas na URL
