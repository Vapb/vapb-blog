"""Transforma fotos de livros (tiradas em cima da mesa) em capas "escaneadas".

Detecta o retangulo do livro na foto, corrige a perspectiva, recorta e
(com --enhance) da um ajuste leve de branco/contraste. Nao usa IA generativa de
proposito: o resultado e a SUA foto endireitada, sem redesenhar a arte.

Uso:
    python scripts/cover_scanner.py foto.jpg                       # salva foto-scan.jpg ao lado
    python scripts/cover_scanner.py foto.jpg -o static/images/estante/shigurui-3/capa-verso.jpeg
    python scripts/cover_scanner.py pasta_de_fotos/ -o static/images/estante/scans/
    python scripts/cover_scanner.py foto.jpg --ratio 15x21         # forca a proporcao (largura x altura)
    python scripts/cover_scanner.py foto.jpg --debug               # salva imagem com o contorno detectado
    python scripts/cover_scanner.py foto.jpg --corners "0.13,0.13 0.86,0.13 0.86,0.90 0.13,0.90"
    python scripts/cover_scanner.py pasta/ --corners-file cantos.json

Quando a deteccao automatica erra (livro preto no desk mat preto, por exemplo),
passe os cantos aproximados com --corners / --corners-file: fracoes da
largura/altura da foto. Um LLM olhando a foto consegue dar esse chute; o
script so ajusta cada lado pra borda real mais proxima.

Dicas para a foto: livro inteiro no quadro, fundo escuro e liso (o desk mat
preto e perfeito), luz sem reflexo forte em cima da capa.

Dependencias: pip install opencv-python-headless numpy pillow
Fotos .heic do iPhone: pip install pillow-heif
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
DETECT_SIZE = 1000  # lado maior usado na deteccao (a saida usa a resolucao original)


def load_image(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".heic", ".heif"}:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def order_points(pts: np.ndarray) -> np.ndarray:
    """Ordena 4 pontos como: topo-esq, topo-dir, baixo-dir, baixo-esq."""
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
        dtype="float32",
    )


def _quad_from_mask(mask: np.ndarray, min_area: float) -> np.ndarray | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        if cv2.contourArea(c) < min_area:
            break
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        for eps in (0.01, 0.02, 0.03, 0.05):
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) == 4:
                return approx.reshape(4, 2)
        # nao virou quadrilatero limpo: usa o retangulo minimo (ainda corrige rotacao)
        return cv2.boxPoints(cv2.minAreaRect(hull))
    return None


def _touches_border(quad: np.ndarray, shape, tol: float = 0.01) -> bool:
    h, w = shape[:2]
    x, y = quad[:, 0], quad[:, 1]
    return bool((x < w * tol).any() or (x > w * (1 - tol)).any() or (y < h * tol).any() or (y > h * (1 - tol)).any())


def _keep_band(counts: np.ndarray, center: int, jump: float = 1.6) -> tuple[int, int]:
    """A partir do centro, anda pra cima/baixo enquanto a largura do objeto nao 'pula'
    (sinal de que ele encostou em outra coisa: outro livro, borda da mesa...)."""
    lo_c, hi_c = max(center - len(counts) // 8, 0), center + len(counts) // 8
    ref = np.median(counts[lo_c:hi_c][counts[lo_c:hi_c] > 0])
    ok = (counts > 0) & (counts < ref * jump)
    a = b = center
    while a > 0 and ok[a - 1]:
        a -= 1
    while b < len(counts) - 1 and ok[b + 1]:
        b += 1
    return a, b + 1


def _robust_line(ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Reta x = a*y + b ignorando trechos que fogem da borda (abas, sombras)."""
    keep = np.abs(xs - np.median(xs)) <= max(2.5 * np.median(np.abs(xs - np.median(xs))), 2)
    fit = np.polyfit(ys[keep], xs[keep], 1)
    resid = np.abs(np.polyval(fit, ys) - xs)
    keep = resid <= max(np.percentile(resid, 70), 2)
    return np.polyfit(ys[keep], xs[keep], 1)


def _extend_along_sides(obj: np.ndarray, gray: np.ndarray, gap: int = 4) -> np.ndarray:
    """Partes escuras do livro (ex: caixa do logo na lombada) somem no limiar contra o
    fundo escuro. Segue as bordas laterais do objeto pra cima/baixo enquanto elas ainda
    aparecem como bordas fortes na foto, e preenche o que faltava."""
    rows = np.where(obj.any(axis=1))[0]
    if len(rows) < 20:
        return obj
    left = np.array([np.argmax(obj[r]) for r in rows])
    right = np.array([len(obj[r]) - 1 - np.argmax(obj[r][::-1]) for r in rows])
    fl, fr = _robust_line(rows, left), _robust_line(rows, right)
    grad = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    w = gray.shape[1]

    def side_strength(r: int, fit) -> float:
        x = int(round(np.polyval(fit, r)))
        return float(grad[r, max(x - 3, 0) : min(x + 4, w)].max()) if 0 <= x < w else 0.0

    ref = np.median([min(side_strength(r, fl), side_strength(r, fr)) for r in rows[:: max(len(rows) // 50, 1)]])
    for start, step in ((rows[0], -1), (rows[-1], 1)):
        r, misses, last_ok = start, 0, start
        while 0 <= r + step < obj.shape[0] and misses <= gap:
            r += step
            if min(side_strength(r, fl), side_strength(r, fr)) > 0.35 * ref:
                misses, last_ok = 0, r
            else:
                misses += 1
        if step < 0:
            top = last_ok
        else:
            bottom = last_ok
    # redesenha o objeto so entre as bordas retas: descarta "abas" como a lateral
    # das paginas que aparece do lado da lombada
    out = np.zeros_like(obj)
    for rr in range(top, bottom + 1):
        a, b = int(round(np.polyval(fl, rr))), int(round(np.polyval(fr, rr)))
        out[rr, max(a, 0) : min(b + 1, w)] = 1
    return out


def _isolate_center(mask: np.ndarray, gray: np.ndarray) -> np.ndarray:
    """Quando o livro encosta em outros objetos claros, corta o que nao pertence
    ao objeto do centro da foto, olhando a largura dele linha a linha e coluna a coluna."""
    h, w = mask.shape
    _, labels = cv2.connectedComponents(mask)
    center_label = labels[h // 2, w // 2]
    if center_label == 0:
        return mask
    obj = (labels == center_label).astype("uint8")
    for _ in range(2):  # linhas, depois colunas (com as linhas ja limpas)
        a, b = _keep_band(obj.sum(axis=1), h // 2)
        obj[:a], obj[b:] = 0, 0
        a, b = _keep_band(obj.sum(axis=0), w // 2)
        obj[:, :a], obj[:, b:] = 0, 0
    return _extend_along_sides(obj, gray) * 255


def _contrast_image(small: np.ndarray) -> np.ndarray:
    """Luminancia com contraste local realcado: faz a borda de um livro preto
    aparecer contra o desk mat preto."""
    l = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)[:, :, 0]
    l = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l)
    return cv2.bilateralFilter(l, 9, 40, 9)


def _edge_strength(img: np.ndarray, p0: np.ndarray, p1: np.ndarray, d: int = 3, n: int = 80) -> float:
    """Forca de borda ao longo do segmento p0-p1: media da diferenca de brilho entre
    um lado e o outro da linha. Borda real tem sinal constante e soma; textura do
    fundo tem sinal aleatorio e se cancela."""
    h, w = img.shape
    pts = p0 + (p1 - p0) * np.linspace(0.05, 0.95, n)[:, None]
    direction = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-6)
    normal = np.array([-direction[1], direction[0]])
    total = 0.0
    for k in (d - 1, d, d + 2):
        a = (pts + normal * k).round().astype(int)
        b = (pts - normal * k).round().astype(int)
        a[:, 0], b[:, 0] = a[:, 0].clip(0, w - 1), b[:, 0].clip(0, w - 1)
        a[:, 1], b[:, 1] = a[:, 1].clip(0, h - 1), b[:, 1].clip(0, h - 1)
        total += (img[a[:, 1], a[:, 0]].astype(float) - img[b[:, 1], b[:, 0]]).mean()
    return abs(total) / 3


def _intersect(a0, a1, b0, b1) -> np.ndarray:
    da, db = a1 - a0, b1 - b0
    cross = lambda u, v: u[0] * v[1] - u[1] * v[0]
    t = cross(b0 - a0, db) / cross(da, db)
    return a0 + t * da


def refine_quad(img: np.ndarray, quad: np.ndarray, radius: int) -> np.ndarray:
    """Ajusta cada lado de um quadrilatero aproximado pra borda mais forte por
    perto: move cada ponta do lado ate `radius` px na direcao perpendicular
    (isso cobre deslocamento e leve rotacao) e depois recalcula os cantos."""
    q = order_points(quad)
    sides = []
    for i in range(4):
        p0, p1 = q[i], q[(i + 1) % 4]
        direction = (p1 - p0) / np.linalg.norm(p1 - p0)
        normal = np.array([-direction[1], direction[0]])
        best, best_score = (p0, p1), -1.0
        for o0 in range(-radius, radius + 1):
            for o1 in range(-radius, radius + 1):
                c0, c1 = p0 + normal * o0, p1 + normal * o1
                score = _edge_strength(img, c0, c1)
                if score > best_score:
                    best, best_score = (c0, c1), score
        sides.append(best)
    return np.array([_intersect(*sides[i - 1], *sides[i]) for i in range(4)], dtype="float32")


def find_book(img: np.ndarray) -> np.ndarray | None:
    """Retorna os 4 cantos do livro (coordenadas da imagem original) ou None."""
    h, w = img.shape[:2]
    scale = DETECT_SIZE / max(h, w)
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    min_area = 0.08 * small.shape[0] * small.shape[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))

    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)

    # 1) Fundo escuro: Otsu separa livro (claro) do desk mat (escuro)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # fundo claro (folha branca, mesa clara): o livro e a parte escura, inverte.
    # Quem decide e a moldura da foto, que quase sempre e fundo.
    border = np.concatenate([mask[:10].ravel(), mask[-10:].ravel(), mask[:, :10].ravel(), mask[:, -10:].ravel()])
    if border.mean() > 127:
        mask = 255 - mask
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    quad = _quad_from_mask(mask, min_area)

    # 1b) Livro encostado em outra coisa clara (outro livro, borda da mesa): o contorno
    # vaza ate a borda da foto. Isola o objeto do centro (aceita objetos finos, tipo lombada).
    if quad is None or _touches_border(quad, small.shape):
        isolated = _quad_from_mask(_isolate_center(mask, gray), 0.02 * small.shape[0] * small.shape[1])
        if isolated is not None:
            quad = isolated

    # 2) Fallback: bordas (fundos claros/estampados)
    if quad is None:
        edges = cv2.dilate(cv2.Canny(gray, 50, 150), kernel, iterations=2)
        quad = _quad_from_mask(edges, min_area)

    return None if quad is None else quad / scale


def quad_from_hint(img: np.ndarray, hint: str, radius: int) -> np.ndarray:
    """Cantos aproximados vindos de fora (de voce ou de um LLM olhando a foto), como
    fracoes da largura/altura: "x,y x,y x,y x,y" em qualquer ordem. Cada lado e
    ajustado pra borda real mais proxima, entao o chute nao precisa ser exato."""
    h, w = img.shape[:2]
    pts = np.array([[float(v) for v in p.split(",")] for p in hint.split()], dtype="float32")
    if pts.shape != (4, 2):
        raise ValueError(f"--corners precisa de 4 pontos x,y, recebi: {hint!r}")
    scale = DETECT_SIZE / max(h, w)
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    quad = pts * [small.shape[1], small.shape[0]]
    if radius > 0:
        quad = refine_quad(_contrast_image(small), quad, radius)
    return quad / scale


def warp(img: np.ndarray, quad: np.ndarray, ratio: float | None) -> np.ndarray:
    tl, tr, br, bl = order_points(quad)
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    if ratio:  # ratio = largura / altura
        height = int(round(width / ratio))
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    m = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl]), dst)
    return cv2.warpPerspective(img, m, (width, height), flags=cv2.INTER_CUBIC)


def trim(img: np.ndarray, pct: float) -> np.ndarray:
    """Corta uma margem fina para sumir com restos de fundo/sombra nas bordas."""
    h, w = img.shape[:2]
    dy, dx = int(h * pct), int(w * pct)
    return img[dy : h - dy, dx : w - dx]


def enhance(img: np.ndarray) -> np.ndarray:
    """Ajuste leve: neutraliza o tom da luz usando as partes mais claras (papel/branco)
    e estica um pouco o contraste. Nao mexe na paleta da arte como um todo."""
    f = img.astype("float32")
    white = np.percentile(f.reshape(-1, 3), 99, axis=0)
    f *= 1 + 0.6 * (white.max() / white - 1)  # 60% da correcao: evita exagero
    lo, hi = np.percentile(f, (0.5, 99.5))
    f = (f - lo) * 255 / max(hi - lo, 1)
    return np.clip(f, 0, 255).astype("uint8")


def parse_ratio(value: str | None) -> float | None:
    if not value:
        return None
    w, h = (float(x.replace(",", ".")) for x in value.lower().split("x"))
    return w / h


def process(src: Path, dst: Path, args, hint: str | None = None) -> bool:
    img = load_image(src)
    quad = quad_from_hint(img, hint, args.refine) if hint else find_book(img)
    if quad is None:
        print(f"[falhou] {src.name}: nao achei o livro na foto")
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    if args.debug:
        dbg = img.copy()
        cv2.polylines(dbg, [order_points(quad).astype(int)], True, (0, 255, 0), max(3, img.shape[1] // 300))
        cv2.imwrite(str(dst.with_name(dst.stem + "-debug.jpg")), dbg)

    out = trim(warp(img, quad, parse_ratio(args.ratio)), args.trim)
    if args.enhance:
        out = enhance(out)
    if args.max_size and max(out.shape[:2]) > args.max_size:
        s = args.max_size / max(out.shape[:2])
        out = cv2.resize(out, (int(out.shape[1] * s), int(out.shape[0] * s)), interpolation=cv2.INTER_AREA)

    Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)).save(dst, quality=92)
    print(f"[ok] {src.name} -> {dst} ({out.shape[1]}x{out.shape[0]})")
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", type=Path, help="foto ou pasta de fotos")
    p.add_argument("-o", "--output", type=Path, help="arquivo de saida (ou pasta, se input for pasta)")
    p.add_argument("--ratio", help="forca proporcao largura x altura, ex: 15x21 (tirado de 'dimensions')")
    p.add_argument("--trim", type=float, default=0.006, help="margem cortada em cada borda (fracao, padrao 0.006)")
    p.add_argument("--max-size", type=int, default=1500, help="lado maior da saida em px (0 = sem limite)")
    p.add_argument("--enhance", action="store_true", help="ajuste leve de branco/contraste (padrao: cores da foto)")
    p.add_argument("--debug", action="store_true", help="salva tambem a foto com o contorno detectado")
    p.add_argument("--corners", help='cantos aproximados em fracao da foto: "x,y x,y x,y x,y" (pula a deteccao)')
    p.add_argument("--corners-file", type=Path, help="JSON {nome_do_arquivo: \"x,y x,y x,y x,y\"} para lotes")
    p.add_argument("--refine", type=int, default=12, help="raio (px, na escala de deteccao) do ajuste dos cantos; 0 = usa exato")
    args = p.parse_args()
    hints = json.loads(args.corners_file.read_text(encoding="utf-8")) if args.corners_file else {}

    if args.input.is_dir():
        files = sorted(f for f in args.input.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        out_dir = args.output or args.input / "scans"
        results = [process(f, out_dir / f"{f.stem}.jpeg", args, hints.get(f.name)) for f in files]
        print(f"\n{sum(results)}/{len(results)} processadas")
    else:
        dst = args.output or args.input.with_name(f"{args.input.stem}-scan.jpeg")
        if dst.suffix == "" or dst.is_dir():
            dst = dst / f"{args.input.stem}.jpeg"
        process(args.input, dst, args, args.corners or hints.get(args.input.name))


if __name__ == "__main__":
    main()
