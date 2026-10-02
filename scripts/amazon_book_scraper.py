"""Scraper de produtos da Amazon (amazon.com.br) para popular a Estante do blog.

Uso:
    python scripts/amazon_book_scraper.py                # roda todos os grupos e salva em data/livros.json
    python scripts/amazon_book_scraper.py --list-groups   # lista os grupos disponiveis
    python scripts/amazon_book_scraper.py --groups terror random
    python scripts/amazon_book_scraper.py --no-save       # so mostra o resultado, nao grava nada
    python scripts/amazon_book_scraper.py --overwrite     # sobrescreve livros ja existentes no json

Todos os grupos vao pro mesmo data/livros.json, cada livro marcado com um
campo "shelf" (o nome do grupo) -- e o template filtra por esse campo em vez
de carregar um arquivo por estante.

Edite o dicionario GROUPS abaixo para adicionar/remover URLs e estantes.
Cada URL PRECISA terminar em virgula -- sem isso o Python concatena strings
vizinhas silenciosamente e a busca falha pra tudo aquele bloco.

A Amazon detecta e bloqueia scraping agressivo. Isso aqui e pensado para uso
pessoal, esporadico, com delay aleatorio entre requisicoes. Se a Amazon
responder com uma pagina de captcha/robot-check, salve o HTML da pagina
manualmente (Ctrl+S no navegador, "Pagina HTML completa") e use
parse_html_file() com o caminho do arquivo salvo.
"""

import argparse
import json
import random
import re
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data"

GROUPS = {
    "mangas": [
        "https://www.amazon.com.br/Shigurui-Frenesi-Morte-Mang%C3%A1-Vol/dp/6554482628",
        "https://www.amazon.com.br/Parasyte-Full-Color-Vol-01/dp/6555946253/",
        "https://www.amazon.com.br/Parasyte-Full-Color-Vol-02/dp/6555947071",
        "https://www.amazon.com.br/Parasyte-Full-Color-Vol-03/dp/6555947845/",
        "https://www.amazon.com.br/Parasyte-Full-Color-Vol-04/dp/655594885X/",
        "https://www.amazon.com.br/Parasyte-Full-Color-Vol-05/dp/6555949732/",
        "https://www.amazon.com.br/Old-Boy-mang%C3%A1-1-3/dp/650130315X",
        "https://www.amazon.com.br/Old-Boy-mang%C3%A1-2-3/dp/6501360552",
        "https://www.amazon.com.br/Old-Boy-mang%C3%A1-3/dp/6501379563",
        "https://www.amazon.com.br/Gannibal-Vila-Canibais-Masaaki-Ninomiya/dp/6599866158",
        "https://www.amazon.com.br/Gannibal-Vila-Canibais-Masaaki-Ninomiya/dp/6583627175",
        "https://www.amazon.com.br/PTSD-Radio-Frequ%C3%AAncias-Terror-Mang%C3%A1/dp/6554482415",
        "https://www.amazon.com.br/PTSD-Radio-Frequ%C3%AAncias-Terror-Mang%C3%A1/dp/6554482644",
        "https://www.amazon.com.br/PTSD-Radio-Frequ%C3%AAncias-Terror-Mang%C3%A1-ebook/dp/B0DZY47S6T",
        "https://www.amazon.com.br/Mang%C3%A1-Dead-V%C3%A1rios-Autores/dp/8577877736",
        "https://www.amazon.com.br/Rev-Hideout-Vol-001/dp/8542601734",
        "https://www.amazon.com.br/Black-Paradox-Junji-Ito/dp/6555945648",
        "https://www.amazon.com.br/Death-Note-Black-Tsugumi-Ohba/dp/8577876861",
        "https://www.amazon.com.br/Happyland-Parque-Divers%C3%B5es-do-Inferno/dp/6558034336",
        "https://www.amazon.com.br/Cidade-L%C3%A1pides-acompanha-cards-exclusivos/dp/6589912807",
        "https://www.amazon.com.br/Esculturas-Cabe%C3%A7a-acompanha-cards-exclusivos/dp/655448003X",
        "https://www.amazon.com.br/Monster-Kanzenban-Vol-Capa-Dura/dp/6555121254",
        "https://www.amazon.com.br/Battle-Royale-Omnibus-Vol-exclusivos/dp/6554480714",
        "https://www.amazon.com.br/Gannibal-Vila-Canibais-Masaaki-Ninomiya/dp/6599866174",
        "https://www.amazon.com.br/Gannibal-Vila-Canibais-Masaaki-Ninomiya/dp/6598287634",
        "https://www.amazon.com.br/Shigurui-Frenesi-Morte-Mang%C3%A1-Vol/dp/6554482512",
        "https://www.amazon.com.br/H-P-Lovecraft-cor-caiu-espa%C3%A7o/dp/655594787X",
    ],
    "hqs": [
        "https://www.amazon.com.br/Joe-Hill-Dark-Collection-v/dp/6555984848",
        "https://www.amazon.com.br/Joe-Hill-Dark-Collection-v/dp/8594542127",
        "https://www.amazon.com.br/dp/6555980117",
        "https://www.amazon.com.br/Hailstone-Rafael-Scavone/dp/6555982349",
        "https://www.amazon.com.br/Ed-Gein-Harold-Schechter/dp/6555981687",
        "https://www.amazon.com.br/Wytches-Scott-Snyder/dp/859454037X/",
        "https://www.amazon.com.br/Floresta-Thomas-Ott/dp/6555982063",
        "https://www.amazon.com.br/Cinema-Panopticum-Thomas-Ott/dp/6555981318/",
        "https://www.amazon.com.br/N%C3%BAmero-73304-23-4153-6-96-8-Thomas-Ott/dp/6555983140",
        "https://www.amazon.com.br/Boys-6-Sociedade-Autopreserva%C3%A7%C3%A3o/dp/6555140305",
    ],
    "exatas": [
        "https://www.amazon.com.br/Fundamentos-Qualidade-Dados-Pipelines-Confi%C3%A1veis/dp/8550821136",
        "https://www.amazon.com.br/Projetando-Aplica%C3%A7%C3%B5es-com-Intensivo-Dados/dp/6583913062",
        "https://www.amazon.com.br/Fundamentos-Engenharia-Dados-Construa-Sistemas/dp/8575228765",
        "https://www.amazon.com.br/Storytelling-com-Dados-Visualiza%C3%A7%C3%A3o-Profissionais/dp/8550804681",
        "https://www.amazon.com.br/Storytelling-com-dados-vamos-praticar/dp/8550817546",
        "https://www.amazon.com.br/Como-Mentir-Estat%C3%ADstica-Darrell-Huff/dp/858057952X",
        "https://www.amazon.com.br/dp/6555605774/",
        "https://www.amazon.com.br/Malware-Data-Science-Detection-Attribution/dp/1593278594",
        "https://www.amazon.com.br/poder-pensamento-matem%C3%A1tico-ci%C3%AAncia-errado/dp/8537814210",
        "https://www.amazon.com.br/Data-Science-zero-Joel-Grus/dp/857608998X",
        "https://www.amazon.com.br/Interactive-Data-Visualization-Web-Introduction-ebook/dp/B074JKZ9Z3",
    ],
    "terror": [
        "https://www.amazon.com.br/dp/8581053041/",
        "https://www.amazon.com.br/Casas-estranhas-Vol/dp/8551013130",
        "https://www.amazon.com.br/Casas-estranhas-mist%C3%A9rio-plantas-baixas/dp/8551011936",
        "https://www.amazon.com.br/Imagens-estranhas-Uketsu/dp/8556512542",
        "https://www.amazon.com.br/livro-maldito-Creepypastas-macabras-contos/dp/8542216652",
        "https://www.amazon.com.br/Casa-do-Passado-Heloisa-Seixas/dp/8501058815",
        "https://www.amazon.com.br/Hist%C3%B3rias-extraordin%C3%A1rias-Edgar-Allan-Poe/dp/8535912320",
    ],
    "random": [
        "https://www.amazon.com.br/Murdoku-mist%C3%A9rios-resolver-usando-l%C3%B3gica/dp/8543111536",
        "https://www.amazon.com.br/SPQR-Mary-Beard/dp/8542209400",
    ],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

BOT_CHECK_MARKERS = (
    "Sorry, we just need to make sure you're not a robot",
    "Digite os caracteres que você vê",
    "Type the characters you see in this image",
    "api-services-support@amazon.com",
)


class BlockedError(RuntimeError):
    """Levantado quando a Amazon devolve uma página de captcha/robot-check."""


def fetch_html(url, session=None, timeout=15, max_retries=3, retry_backoff=4.0):
    """Busca a página, tentando de novo em erros 5xx transitórios.

    A Amazon às vezes devolve uma página de erro genérica ("503 - Erro de
    serviço indisponível", HTTP 500) pra uma URL que na verdade é válida —
    tentar de novo alguns segundos depois costuma resolver.
    """
    session = session or requests
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status and 500 <= status < 600 and attempt <= max_retries:
                wait = retry_backoff * attempt + random.uniform(0, 2)
                print(f"[retry] {url} -> {status}, tentando de novo em {wait:.1f}s ({attempt}/{max_retries})")
                time.sleep(wait)
                continue
            raise

    html = resp.text
    if any(marker in html for marker in BOT_CHECK_MARKERS):
        raise BlockedError(
            "A Amazon devolveu uma página de verificação (captcha/robot-check) para "
            f"{url}. Salve a página manualmente (Ctrl+S no navegador, formato 'Página "
            "HTML completa') e use parse_html_file() com o caminho do arquivo salvo."
        )
    return html


ZERO_WIDTH_RE = re.compile(r"[‎‏]")


def clean_text(text):
    if text is None:
        return None
    text = ZERO_WIDTH_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_key(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


DETAIL_KEY_MAP = {
    "editora": "publisher",
    "data da publicacao": "publishedDate",
    "edicao": "edition",
    "idioma": "language",
    "numero de paginas": "pages",
    "isbn-10": "isbn10",
    "isbn-13": "isbn13",
    "peso do produto": "weight",
    "idade de leitura": "readingAge",
    "dimensoes": "dimensions",
}


def parse_detail_bullets(soup):
    """Extrai a lista 'Detalhes do produto' (cobre os dois formatos que a Amazon usa)."""
    raw = {}

    bullets = soup.select_one("#detailBullets_feature_div")
    if bullets:
        for li in bullets.select("li"):
            text = clean_text(li.get_text(" ", strip=True))
            if ":" in text:
                key, _, value = text.partition(":")
                raw[normalize_key(key)] = clean_text(value)

    table = soup.select_one("#productDetails_detailBullets_sections1")
    if table:
        for row in table.select("tr"):
            th, td = row.select_one("th"), row.select_one("td")
            if th and td:
                raw[normalize_key(th.get_text(strip=True))] = clean_text(
                    td.get_text(" ", strip=True)
                )

    details = {}
    for raw_key, value in raw.items():
        field = DETAIL_KEY_MAP.get(raw_key)
        if field:
            details[field] = value
    return details


def parse_title(soup):
    el = soup.select_one("#productTitle")
    return clean_text(el.get_text()) if el else None


NOT_AN_AUTHOR_RE = re.compile(r"^&\s*\d+\s*mais$", flags=re.I)


def parse_authors(soup):
    authors = []
    byline = soup.select_one("#bylineInfo")
    if byline:
        for a in byline.select("a.a-link-normal"):
            name = clean_text(a.get_text(" ", strip=True))
            if not name or NOT_AN_AUTHOR_RE.match(name):
                continue  # "& N mais" é o botão de expandir a lista, não um autor
            if name not in authors:
                authors.append(name)
    return authors


def parse_series_name(soup, title=None):
    """Nome da série, só quando a Amazon mostra um widget de série de verdade."""
    widget = soup.select_one("#seriesBulletWidget_feature_div, #series-page-link")
    if not widget:
        return None
    link = widget.select_one("a")
    raw = clean_text(link.get_text(" ", strip=True)) if link else clean_text(widget.get_text(" ", strip=True))
    raw = re.sub(r"^\s*Parte de:\s*", "", raw or "", flags=re.I)
    raw = re.sub(r"^\s*Livro\s+\d+\s+de\s+\d+:\s*", "", raw, flags=re.I).strip()
    if not raw:
        return None
    if re.search(r"\(\d+\s+livros?\)$", raw, flags=re.I):
        return None  # "X (N livros)" é o selo/coleção da editora, não série do livro
    if title and raw.lower() == title.strip().lower():
        return None  # o widget às vezes só linka de volta pro próprio livro
    return raw


def extract_volume(title):
    """Só usado internamente pra desambiguar o id de livros da mesma série (ex.: parasyte-full-color-4)."""
    if not title:
        return None
    match = re.search(r"\bv(?:ol(?:ume)?)?\.?\s*0*?(\d+)\b", title, flags=re.I)
    return int(match.group(1)) if match else None


def parse_image_url(soup):
    img = soup.select_one("#landingImage, #imgBlkFront")
    if not img:
        return None
    src = img.get("data-old-hires") or img.get("src")
    if src:
        return src
    dynamic = img.get("data-a-dynamic-image")
    if dynamic:
        try:
            candidates = json.loads(dynamic)
            widest = max(candidates.items(), key=lambda kv: (kv[1] or [0])[0])
            return widest[0]
        except (ValueError, TypeError):
            return None
    return None


SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(*parts):
    text = " ".join(str(p) for p in parts if p)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = SLUG_RE.sub("-", text.lower()).strip("-")
    return text


def scrape_book(url, session=None):
    html = fetch_html(url, session=session)
    return parse_book_html(html, url)


def parse_html_file(path, url=""):
    """Alternativa quando a Amazon bloqueia a requisição: rode sobre um HTML salvo manualmente."""
    html = Path(path).read_text(encoding="utf-8")
    return parse_book_html(html, url)


def parse_book_html(html, url=""):
    soup = BeautifulSoup(html, "html.parser")
    details = parse_detail_bullets(soup)
    title = parse_title(soup)
    authors = parse_authors(soup)
    series = parse_series_name(soup, title)

    book = {
        "id": None,
        "title": title,
        "url": url,
        "imageUrl": parse_image_url(soup),
        "author": authors[0] if authors else None,
        "series": series,
        "publisher": details.get("publisher"),
        "publishedDate": details.get("publishedDate"),
        "edition": details.get("edition"),
        "language": details.get("language"),
        "pages": details.get("pages"),
        "isbn10": details.get("isbn10"),
        "isbn13": details.get("isbn13"),
        "weight": details.get("weight"),
        "readingAge": details.get("readingAge"),
        "dimensions": details.get("dimensions"),
    }

    book["id"] = slugify(series if series else title, extract_volume(title))

    missing = [k for k in ("title", "publisher", "pages", "dimensions") if not book.get(k)]
    if missing:
        print(f"[aviso] {url}\n  campos não encontrados: {', '.join(missing)}")

    return book


def scrape_books(urls, delay_range=(3, 6), session=None):
    session = session or requests.Session()
    books, errors, seen_ids = [], [], set()
    for i, url in enumerate(urls):
        try:
            book = scrape_book(url, session=session)
            if book["id"] in seen_ids:
                # evita que dois livros diferentes colidam no mesmo id e um "suma" no merge
                base_id, n = book["id"], 2
                while book["id"] in seen_ids:
                    book["id"] = f"{base_id}-{n}"
                    n += 1
                print(f"[aviso] id duplicado, renomeado para {book['id']!r}")
            seen_ids.add(book["id"])
            books.append(book)
            print(f"[ok] {book['title']}")
        except Exception as exc:
            errors.append((url, exc))
            print(f"[erro] {url}\n  {exc}")
        if i < len(urls) - 1:
            time.sleep(random.uniform(*delay_range))
    return books, errors


def scrape_groups(groups, delay_range=(3, 6), group_delay=(8, 14), session=None):
    session = session or requests.Session()
    results = {}
    group_names = list(groups)
    for gi, name in enumerate(group_names):
        print(f"\n=== {name} ({len(groups[name])} urls) ===")
        results[name] = scrape_books(groups[name], delay_range=delay_range, session=session)
        if gi < len(group_names) - 1:
            time.sleep(random.uniform(*group_delay))
    return results


def load_existing(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_all(results, path, overwrite_existing=False):
    """Mescla os livros de todos os grupos num único livros.json, marcando cada um com 'shelf'.

    Casa livros pela 'url' (chave estável da Amazon), não pelo 'id' -- o id é só
    um slug pra leitura, e pode mudar de uma raspagem pra outra (ex.: a Amazon
    às vezes não renderiza o widget de série numa tentativa e renderiza na outra).
    """
    existing = load_existing(path)
    by_url = {b["url"]: i for i, b in enumerate(existing) if b.get("url")}

    for shelf, (books, _errors) in results.items():
        for book in books:
            book["shelf"] = shelf
            if book["url"] in by_url:
                if overwrite_existing:
                    old = existing[by_url[book["url"]]]
                    # preserva campos que não vêm da Amazon (ex.: spineImageUrl,
                    # curado à mão) em vez de sobrescrever o registro inteiro
                    existing[by_url[book["url"]]] = {**old, **book}
                    print(f"[substituído] {book['id']}")
                else:
                    print(f"[pulado] {book['id']} já existe em {path} (overwrite_existing=False)")
                continue
            existing.append(book)
            by_url[book["url"]] = len(existing) - 1

    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[backup] {backup}")

    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[salvo] {path} ({len(existing)} livros no total)")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--groups", nargs="+", choices=list(GROUPS), help="grupos a rodar (padrão: todos)")
    parser.add_argument("--list-groups", action="store_true", help="lista os grupos e quantidade de URLs, sem buscar nada")
    parser.add_argument("--delay-min", type=float, default=3.0, help="delay mínimo (s) entre requisições do mesmo grupo")
    parser.add_argument("--delay-max", type=float, default=6.0, help="delay máximo (s) entre requisições do mesmo grupo")
    parser.add_argument("--group-delay-min", type=float, default=8.0, help="delay mínimo (s) entre grupos")
    parser.add_argument("--group-delay-max", type=float, default=14.0, help="delay máximo (s) entre grupos")
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR / "livros.json", help="arquivo json de saída (todos os grupos, marcados com 'shelf')")
    parser.add_argument("--overwrite", action="store_true", help="sobrescreve livros já existentes no json (por padrão só adiciona novos)")
    parser.add_argument("--no-save", action="store_true", help="só busca e mostra o resumo, não grava nada em disco")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list_groups:
        for name, urls in GROUPS.items():
            print(f"{name}: {len(urls)} urls")
        return

    groups = {name: GROUPS[name] for name in (args.groups or GROUPS)}
    results = scrape_groups(
        groups,
        delay_range=(args.delay_min, args.delay_max),
        group_delay=(args.group_delay_min, args.group_delay_max),
    )

    print("\n=== RESUMO ===")
    for group, (books, errors) in results.items():
        print(f"{group}: {len(books)} ok, {len(errors)} erro(s)")
        for url, exc in errors:
            print(f"  [erro] {url} -> {exc}")

    if not args.no_save:
        save_all(results, path=args.output, overwrite_existing=args.overwrite)


if __name__ == "__main__":
    main()
