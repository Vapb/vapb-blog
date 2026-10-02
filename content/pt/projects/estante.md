---
title: "Estante Virtual"
date: 2026-09-21T10:00:00-03:00
description: "Uma estante 3D no navegador com as lombadas, capas e colecionáveis dos meus livros de verdade"
tags: ["hugo", "javascript", "css", "python", "projeto"]
---

> 📚 **Veja ao vivo:** [Abrir a estante]({{< relref "/estante" >}})

## Motivação

Eu coleciono livros físicos — muito mangá de terror, alguns quadrinhos, livros técnicos e uma coisa ou outra aleatória. O problema de uma coleção física é que ela só existe na sala de casa. Quando alguém pergunta "o que você anda lendo?" ou "você tem o volume 3 de Shigurui?", a resposta é sempre uma foto torta tirada às pressas no celular.

As alternativas prontas não me convenciam:

- **Skoob, Goodreads e afins** resolvem o catálogo, mas viram uma **lista** — capa pequena, título, nota. Perde justamente o que torna uma estante legal: as lombadas lado a lado, a altura diferente de cada edição, a série inteira formando um desenho.
- **Planilha** é ótima pra mim, péssima pra mostrar pra alguém.
- E nenhuma delas tem lugar pros **extras**: marca-página exclusivo de pré-venda, card promocional, sobrecapa. Pra quem coleciona, isso é metade da graça.

Então a ideia foi simples: **e se a página parecesse uma estante de verdade?** Lombadas reais, você puxa o livro da prateleira, vira, abre, e o marca-página fica com a pontinha pra fora esperando ser puxado.

Também tinha um motivo mais egoísta: era uma desculpa pra brincar com **CSS 3D, animação e Web Audio** fora do contexto de trabalho — onde quase tudo que eu faço é dado, banco e cloud.

## O que ela faz

- **Prateleiras por categoria** — mangás, HQs, terror, exatas e "random". Cada aba troca a prateleira com animação.
- **Lombadas proporcionais** — a largura e a altura de cada livro vêm das dimensões reais da edição, então um volume grosso parece grosso.
- **Tirar o livro da prateleira** — clicar numa lombada puxa o livro em 3D. Dá pra girar, virar pro verso e **abrir pela capa** (aparece um ex-libris) ou **pelo verso**.
- **Séries agrupadas** — passar o mouse num volume destaca os outros da mesma coleção.
- **Colecionáveis** — livros com marca-página exclusivo mostram a pontinha saindo das páginas; um baralho "✦ Colecionáveis" reúne cards e marcadores, que dá pra girar com o mouse.
- **Sobrecapa** — quando a edição tem sobrecapa, é ela que aparece, do jeito que o livro fica na estante de verdade.
- **Busca, navegação por teclado e som** — setas pra navegar, efeitos sonoros sintetizados (sem arquivos de áudio) e respeito a `prefers-reduced-motion`.
- Um **easter egg** de terror escondido entre os livros. Não vou dizer qual. 👀

## Como funciona

A estante é uma página estática do Hugo — sem framework, sem build de JavaScript, sem backend.

| Peça | O que faz |
|---|---|
| `data/livros.json` | O catálogo: título, autor, editora, ISBN, páginas, dimensões, prateleira e detalhes dos extras |
| `static/images/estante/<pasta>/` | Uma pasta por livro com arquivos de nome fixo: `capa`, `lombada`, `capa-verso`, `sobrecapa`, `marca-pagina`, `colecionavel`… |
| `layouts/_default/estante.html` | Template Hugo + CSS + JavaScript puro numa página só |

O ponto que mais gostei de resolver foi a **convenção de pastas**. O template usa `readDir` do Hugo pra descobrir, em tempo de build, quais fotos cada livro tem. Não preciso declarar nada no JSON: se existe um `sobrecapa.jpg` na pasta, a sobrecapa aparece; se não existe lombada, entra um placeholder colorido. Adicionar um livro novo é jogar as fotos numa pasta.

Algumas coisas são resolvidas no navegador, em tempo de execução:

- **Cor da lombada** extraída dos pixels da foto via `canvas`, pra o placeholder e as bordas combinarem com o livro.
- **Recorte automático** dos PNGs transparentes de marca-páginas e cards — eu solto a foto crua e a página corta o espaço vazio.
- **Contracapa gerada** pros livros sem foto do verso: ficha técnica (editora, páginas, formato) e código de barras desenhado em SVG a partir do ISBN-13.

### Os scripts de apoio

Dois scripts em Python alimentam a estante:

- **`amazon_book_scraper.py`** — a partir de uma lista de links, busca os metadados de cada livro (ISBN, páginas, dimensões, editora) e grava no `livros.json`. Uso pessoal e esporádico, com intervalo aleatório entre requisições.
- **`cover_scanner.py`** — transforma a foto do livro tirada em cima da mesa numa "capa escaneada": detecta o retângulo, corrige a perspectiva e recorta, com OpenCV. Sem IA generativa de propósito — o resultado é a **minha foto endireitada**, não uma capa redesenhada.

## Como evoluiu

O projeto começou em setembro de 2026 como uma prateleira de lombadas coloridas, com placeholder pra tudo. De lá pra cá:

1. **Fotos reais** substituindo os placeholders, aos poucos, série por série.
2. **Animações** de puxar, virar e abrir o livro — várias delas escolhidas comparando variantes lado a lado numa página de laboratório descartável antes de ir pra estante.
3. **Colecionáveis e sobrecapas**, com a convenção de pastas por livro.

Nem tudo ficou: já testei tirar a sobrecapa pra ver a capa por baixo e etiquetas de "Lendo agora" / "Na fila" — funcionavam, mas deixavam a estante poluída e saíram.

## Próximos passos

- Trocar os placeholders que sobraram por fotos reais.
- Otimizar o peso das imagens (algumas sobrecapas em PNG passam de 3 MB).
- Talvez uma visão de "estatísticas" da coleção — páginas totais, editoras, autores.
