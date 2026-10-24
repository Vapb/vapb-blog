"""Gera ESTANTE-TODO.md: fotos que ainda faltam em cada livro de data/livros.json.

Uso: python scripts/estante_todo.py
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FOTOS = os.path.join(ROOT, "static", "images", "estante")

# foto -> descrição do que falta
ESSENCIAIS = [("lombada", "lombada"), ("capa-verso", "verso da capa")]

with open(os.path.join(ROOT, "data", "livros.json"), encoding="utf-8") as f:
    livros = json.load(f)

faltas = {}
for livro in livros:
    pasta = livro.get("pasta", livro["id"])
    caminho = os.path.join(FOTOS, pasta)
    arquivos = os.listdir(caminho) if os.path.isdir(caminho) else []
    nomes = [os.path.splitext(a)[0].split("/")[-1] for a in arquivos]
    faltando = [
        desc
        for chave, desc in ESSENCIAIS
        if not any(n == chave or n.endswith("-" + chave) for n in nomes)
    ]
    if faltando:
        faltas.setdefault(livro.get("shelf", "outros"), []).append((livro["title"], pasta, faltando))

linhas = [
    "# TODO da estante",
    "",
    "Gerado por `python scripts/estante_todo.py` — rode de novo depois de adicionar fotos.",
    "Fotos vão em `static/images/estante/<pasta>/` (`lombada`, `capa-verso`, ...).",
    "",
]
total = 0
for prateleira, itens in sorted(faltas.items()):
    linhas.append(f"## {prateleira}")
    linhas.append("")
    for titulo, pasta, faltando in itens:
        total += 1
        linhas.append(f"- [ ] **{titulo}** (`{pasta}`): falta {', '.join(faltando)}")
    linhas.append("")

with open(os.path.join(ROOT, "ESTANTE-TODO.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(linhas))
print(f"{total} livros com pendências -> ESTANTE-TODO.md")
