#!/usr/bin/env python3
"""Desenha o mapa da secao "Onde estamos" (pagina inicial).

    python3 scripts/build-mapa.py

O mapa e' um SVG desenhado aqui mesmo, sem servico de mapas: a geografia
(costa, rios, matas, cidades, rodovias) vem de _data/mapa-osm.json, extraido
uma unica vez do OpenStreetMap por scripts/baixar-mapa-osm.py. Os campi vem de
_data/locais.tsv, com a foto de cada um na coluna "foto".

So usa a biblioteca padrao do Python e nao acessa a internet: o ./build.sh
roda este script sempre.

Saidas:
    _includes/mapa-pt.html    usado por index.qmd
    _includes/mapa-en.html    usado por en/index.qmd

Para ajustar a aparencia, mexa nas constantes abaixo (cores, rotulos dos rios,
posicao dos cartoes com foto).
"""

import csv
import html
import json
import math
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DADOS = ROOT / "_data" / "locais.tsv"
GEO = ROOT / "_data" / "mapa-osm.json"
GEO_BRASIL = ROOT / "_data" / "mapa-brasil.json"
OUT = ROOT / "_includes"

# Largura do desenho (unidades do SVG). A altura sai da proporcao do recorte.
LARGURA = 1200

# Paleta. Mar e rios em azul, mata em verde; o resto neutro para os campi
# (azul do site) se destacarem.
COR = {
    "terra": "#f3f0e3",
    "mata": "#cfe3b8",
    "mangue": "#cfe5d6",
    "urbano": "#e6ded0",
    "urbano_borda": "#d3c7b2",
    "mar": "#9fcbe9",
    "mar_fundo": "#7fb6df",
    "agua": "#9fcbe9",
    "rio": "#86bde2",
    "riacho": "#b3d6ee",
    "estrada_borda": "#cdbb98",
    "estrada": "#fffdf6",
    "arvore": "#7db365",
    "arvore_escura": "#5d9549",
    "tronco": "#8a6a4a",
    "cidade": "#17233f",
    "rio_texto": "#2b6a9e",
    "pino": "#304ea1",
    "pino_escuro": "#17233f",
}

# Rios com nome escrito no mapa: (nome no OSM, posicao ao longo do rio de 0 a
# 1, deslocamento perpendicular em px). Os outros rios sao desenhados sem nome.
ROTULOS_RIOS = [
    ("Rio Cachoeira", 0.62, -11),
    ("Rio Almada", 0.55, -8),
    ("Rio Santana", 0.45, -8),
    ("Rio Fundão", 0.55, -8),
]

# Cidades: (nome, lat, lon) - centro do texto.
CIDADES = [
    ("Itabuna", -14.7880, -39.2810),
    ("Ilhéus", -14.7930, -39.0490),
]

# Cartao com foto de cada campus, pela sigla: (dx, dy) do centro do cartao em
# relacao ao pino, em px do desenho.
CARTOES = {
    "UFSB": (-50, -175),
    "UESC": (95, 150),
}
CARTAO_L, CARTAO_FOTO_A, CARTAO_LEGENDA_A = 236, 140, 40

# Miniatura de localizacao (Brasil com o estado destacado), no canto
# superior direito, sobre o mar. Tamanho do quadro em px do desenho.
MINI_L, MINI_A = 150, 172

# Espacamento entre arvores desenhadas na mata (px).
PASSO_ARVORE = 30

# Simplificacao das areas no desenho (px) e area minima para aparecer (px^2).
# Detalhe abaixo de ~1 px nao se ve e so engorda o HTML.
TOL_AREA = 1.6
AREA_MIN_PX = 60

TXT = {
    "pt": {
        "titulo": "Mapa dos campi do BioVirLab",
        "desc": "Mapa da regiao entre Itabuna e Ilheus, na Bahia, com a "
                "localizacao da UESC e da UFSB, os rios, as matas e o mar.",
        "ver": "Ver no Google Maps",
        "rotas": "Como chegar",
        "abrir": "Abrir a região no Google Maps",
        "credito": "© colaboradores do OpenStreetMap",
        "mar": "Oceano Atlântico",
        "km": "km",
        "rolar": "Arraste para ver o mapa inteiro",
    },
    "en": {
        "titulo": "Map of the BioVirLab campuses",
        "desc": "Map of the area between Itabuna and Ilheus, Bahia, Brazil, "
                "showing UESC and UFSB, the rivers, forests and the sea.",
        "ver": "View on Google Maps",
        "rotas": "Get directions",
        "abrir": "Open the area in Google Maps",
        "credito": "© OpenStreetMap contributors",
        "mar": "Atlantic Ocean",
        "km": "km",
        "rolar": "Drag to see the whole map",
    },
}


# ----------------------------------------------------------- projecao ---

class Projecao:
    """lat/lon -> px do desenho, em Web Mercator."""

    def __init__(self, recorte):
        w, s, e, n = recorte
        self.x0, self.y1 = self._merc(n, w)
        self.x1, self.y0 = self._merc(s, e)
        self.esc = LARGURA / (self.x1 - self.x0)
        self.altura = round((self.y0 - self.y1) * self.esc)
        lat_media = math.radians((s + n) / 2)
        # px por km no centro do mapa (no Mercator, 1 m no chao vale
        # 1/cos(lat) m na projecao)
        self.px_km = self.esc * 1000 / math.cos(lat_media)

    @staticmethod
    def _merc(lat, lon):
        r = 6378137
        return (math.radians(lon) * r,
                -math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * r)

    def __call__(self, lat, lon):
        x, y = self._merc(lat, lon)
        return (x - self.x0) * self.esc, (y - self.y1) * self.esc


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def caminho(aneis_px, fechar=True, inteiro=False):
    fmt = (lambda v: str(round(v))) if inteiro else f
    partes = []
    for anel in aneis_px:
        if len(anel) < 2:
            continue
        partes.append("M" + " ".join(f"{fmt(x)},{fmt(y)}" for x, y in anel)
                      + ("Z" if fechar else ""))
    return "".join(partes)


def area_anel(anel):
    return abs(sum(anel[i - 1][0] * anel[i][1] - anel[i][0] * anel[i - 1][1]
                   for i in range(len(anel)))) / 2


def para_px(proj, coords):
    return [proj(lat, lon) for lon, lat in coords]


# -------------------------------------------------------- utilidades 2D ---

def dentro(pt, anel):
    """Ponto dentro do anel (par-impar)."""
    x, y = pt
    res = False
    j = len(anel) - 1
    for i in range(len(anel)):
        xi, yi = anel[i]
        xj, yj = anel[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            res = not res
        j = i
    return res


class Areas:
    """Conjunto de poligonos (com furos) para teste de ponto."""

    def __init__(self, poligonos):
        self.itens = []
        for aneis in poligonos:
            xs = [p[0] for p in aneis[0]]
            ys = [p[1] for p in aneis[0]]
            self.itens.append(((min(xs), min(ys), max(xs), max(ys)), aneis))

    def contem(self, pt):
        x, y = pt
        for (a, b, c, d), aneis in self.itens:
            if a <= x <= c and b <= y <= d and dentro(pt, aneis[0]) \
                    and not any(dentro(pt, furo) for furo in aneis[1:]):
                return True
        return False


def comprimento(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def simplificar(pts, tol):
    """Douglas-Peucker. Aneis fechados (1o ponto = ultimo) sao partidos no
    ponto mais distante do inicio, senao o algoritmo os reduz a nada."""
    if len(pts) < 3:
        return pts
    if pts[0] == pts[-1]:
        k = max(range(len(pts)), key=lambda i: math.dist(pts[0], pts[i]))
        if k == 0:
            return pts[:1]
        return simplificar(pts[:k + 1], tol)[:-1] + simplificar(pts[k:], tol)
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norma = math.hypot(dx, dy) or 1e-9
    i_max, d_max = 0, 0.0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norma
        if d > d_max:
            i_max, d_max = i, d
    if d_max <= tol:
        return [pts[0], pts[-1]]
    return simplificar(pts[:i_max + 1], tol)[:-1] + simplificar(pts[i_max:], tol)


def trecho(pts, ini, fim):
    """Pedaco da polilinha entre as distancias ini e fim (px)."""
    saida, acum = [], 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.dist(a, b)
        if seg == 0:
            continue
        for alvo in (ini, fim):
            if acum <= alvo <= acum + seg:
                t = (alvo - acum) / seg
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                if alvo == ini:
                    saida = [p]
                else:
                    saida.append(p)
                    return saida
        if saida and acum + seg > ini:
            saida.append(b)
        acum += seg
    return saida


def trecho_reto(pts, largura, pos):
    """Escolhe o trecho de comprimento `largura` mais reto da polilinha,
    preferindo ficar perto da fracao `pos` do comprimento. Devolve a corda
    (inicio, fim) - texto em linha reta le melhor que texto serpenteando."""
    total = comprimento(pts)
    if total < largura:
        return None
    melhor, nota_melhor = None, float("inf")
    ini = 0.0
    while ini + largura <= total:
        tr = trecho(pts, ini, ini + largura)
        if len(tr) >= 2:
            (x1, y1), (x2, y2) = tr[0], tr[-1]
            corda = math.dist(tr[0], tr[-1]) or 1e-9
            desvio = max(abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / corda
                         for x, y in tr)
            inclinacao = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            inclinacao = min(inclinacao, 180 - inclinacao)
            longe = abs((ini + largura / 2) / total - pos)
            # reto, pouco inclinado e perto da posicao pedida
            nota = desvio + max(0, inclinacao - 35) * 0.3 + longe * 60
            if nota < nota_melhor:
                melhor, nota_melhor = (tr[0], tr[-1]), nota
        ini += 6
    return melhor


def deslocar(pts, d):
    """Polilinha paralela, d px para a esquerda do sentido de percurso."""
    saida = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        saida.append((x + dy / n * d, y - dx / n * d))
    return saida


# ----------------------------------------------------------------- dados ---

def ler_locais():
    if not DADOS.exists():
        sys.exit(f"{DADOS.relative_to(ROOT)} nao existe")
    locais = []
    with DADOS.open(encoding="utf-8") as fh:
        for n, linha in enumerate(csv.DictReader(fh, delimiter="\t"), 2):
            linha = {k: (v or "").strip() for k, v in linha.items() if k}
            if not linha.get("nome"):
                continue
            try:
                lat, lon = float(linha["lat"]), float(linha["lon"])
            except (KeyError, ValueError):
                sys.exit(f"{DADOS.name}: linha {n}: lat/lon invalidos "
                         f"({linha.get('lat')!r}, {linha.get('lon')!r}) - "
                         "use graus decimais com ponto")
            linha["lat"], linha["lon"] = lat, lon
            locais.append(linha)
    if not locais:
        sys.exit(f"{DADOS.name}: nenhum ponto")
    return locais


def sigla(nome):
    """'Universidade ... (UESC)' -> 'UESC'; sem parenteses, o nome inteiro."""
    m = re.search(r"\(([^)]+)\)\s*$", nome)
    return m.group(1) if m else nome


def gmaps_ver(local):
    return ("https://www.google.com/maps/search/?api=1&amp;query="
            f'{local["lat"]},{local["lon"]}')


def gmaps_rota(local):
    return ("https://www.google.com/maps/dir/?api=1&amp;destination="
            f'{local["lat"]},{local["lon"]}')


# ------------------------------------------------------------- desenho ---

# icone de universidade (predio com frontao e colunas), centrado em 0,0,
# cabe num quadrado de ~22 px
ICONE_UNIVERSIDADE = (
    '<path d="M0,-11 L12,-4.5 L-12,-4.5 Z"/>'
    '<rect x="-11" y="-3.5" width="22" height="2.2"/>'
    '<rect x="-9.5" y="-0.5" width="3" height="8"/>'
    '<rect x="-4.5" y="-0.5" width="3" height="8"/>'
    '<rect x="1.5" y="-0.5" width="3" height="8"/>'
    '<rect x="6.5" y="-0.5" width="3" height="8"/>'
    '<rect x="-12" y="8.3" width="24" height="2.7"/>'
)


def miniatura(brasil, locais, W):
    """Brasil inteiro, estado destacado e um ponto onde ficam os campi."""
    pais = [a for p in brasil["pais"] for a in p]
    lons = [x for a in pais for x, _ in a]
    lats = [y for a in pais for _, y in a]
    w, e, s_, n = min(lons), max(lons), min(lats), max(lats)
    coslat = math.cos(math.radians((s_ + n) / 2))
    margem, topo = 12, 12
    area_l, area_a = MINI_L - 2 * margem, MINI_A - topo - 30
    esc = min(area_l / ((e - w) * coslat), area_a / (n - s_))
    ox = W - 12 - MINI_L + margem + (area_l - (e - w) * coslat * esc) / 2
    oy = 12 + topo

    def pt(lon, lat):
        return ox + (lon - w) * coslat * esc, oy + (n - lat) * esc

    def d(aneis):
        return caminho([[pt(x, y) for x, y in a] for a in aneis])

    lat = sum(l["lat"] for l in locais) / len(locais)
    lon = sum(l["lon"] for l in locais) / len(locais)
    px, py = pt(lon, lat)
    bx0 = W - 12 - MINI_L
    return (
        '<g class="mapa-mini">'
        f'<rect x="{bx0}" y="12" width="{MINI_L}" height="{MINI_A}" rx="10" '
        'fill="#fff" fill-opacity="0.92"/>'
        f'<path d="{d(pais)}" fill="{COR["terra"]}" stroke="#9aa6b8" '
        'stroke-width="0.9" stroke-linejoin="round"/>'
        f'<path d="{d([a for p in brasil["estado"] for a in p])}" '
        f'fill="{COR["arvore"]}" stroke="{COR["arvore_escura"]}" stroke-width="0.9" '
        'stroke-linejoin="round"/>'
        f'<circle cx="{f(px)}" cy="{f(py)}" r="7" fill="#d6453d" fill-opacity="0.25"/>'
        f'<circle cx="{f(px)}" cy="{f(py)}" r="3.6" fill="#d6453d" stroke="#fff" '
        'stroke-width="1.5"/>'
        f'<text class="mapa-mini-pais" x="{f(bx0 + MINI_L / 2)}" y="{MINI_A - 6}" '
        'text-anchor="middle">BRASIL</text>'
        f'<text class="mapa-mini-estado" x="{f(px - 9)}" y="{f(py + 4)}" '
        f'text-anchor="end">{html.escape(brasil["estado_nome"])}</text>'
        '</g>')


def desenhar(geo, locais, lang, brasil=None):
    t = TXT[lang]
    prefixo = "" if lang == "pt" else "../"
    proj = Projecao(geo["recorte"])
    W, H = LARGURA, proj.altura

    def polys(chave):
        saida = []
        for p in geo[chave]:
            aneis = [simplificar(para_px(proj, anel), TOL_AREA) for anel in p]
            aneis = [a for a in aneis if len(a) >= 4 and area_anel(a) >= AREA_MIN_PX]
            if aneis and area_anel(aneis[0]) >= AREA_MIN_PX:
                saida.append(aneis)
        return saida

    mar, agua, mangue = polys("mar"), polys("agua"), polys("mangue")
    mata, urbano = polys("mata"), polys("urbano")

    s = []
    s.append(
        f'<svg class="mapa-svg" viewBox="0 0 {W} {H}" role="img" '
        f'aria-labelledby="mapa-titulo-{lang} mapa-desc-{lang}" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'<title id="mapa-titulo-{lang}">{t["titulo"]}</title>'
        f'<desc id="mapa-desc-{lang}">{t["desc"]}</desc>'
        '<defs>'
        f'<linearGradient id="mapa-mar" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{COR["mar"]}"/>'
        f'<stop offset="1" stop-color="{COR["mar_fundo"]}"/></linearGradient>'
        '<filter id="mapa-sombra" x="-30%" y="-30%" width="160%" height="160%">'
        '<feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#17233f" '
        'flood-opacity="0.28"/></filter>'
        # arvore: copa redonda com sombra e tronco
        '<symbol id="mapa-arvore" viewBox="-6 -12 12 14" overflow="visible">'
        f'<rect x="-0.9" y="-3" width="1.8" height="4.5" fill="{COR["tronco"]}"/>'
        f'<circle cx="0" cy="-6.5" r="5" fill="{COR["arvore_escura"]}"/>'
        f'<circle cx="-0.8" cy="-7.2" r="4.2" fill="{COR["arvore"]}"/>'
        '</symbol>'
        '<symbol id="mapa-palmeira" viewBox="-6 -12 12 14" overflow="visible">'
        f'<path d="M0,1.5 L0,-8" stroke="{COR["tronco"]}" stroke-width="1.3"/>'
        f'<path d="M0,-8 q-4,-2 -6,1 M0,-8 q4,-2 6,1 M0,-8 q-2,-4 -5,-3 '
        f'M0,-8 q2,-4 5,-3" stroke="{COR["arvore_escura"]}" stroke-width="1.6" '
        'fill="none" stroke-linecap="round"/>'
        '</symbol>'
        '</defs>')

    # ---- fundo, mar, areas
    s.append(f'<rect width="{W}" height="{H}" fill="{COR["terra"]}"/>')
    s.append(f'<path d="{caminho((a for p in mata for a in p), inteiro=True)}" '
             f'fill="{COR["mata"]}" fill-rule="evenodd"/>')
    s.append(f'<path d="{caminho((a for p in mangue for a in p), inteiro=True)}" '
             f'fill="{COR["mangue"]}" fill-rule="evenodd"/>')
    s.append(f'<path d="{caminho((a for p in urbano for a in p), inteiro=True)}" '
             f'fill="{COR["urbano"]}" stroke="{COR["urbano_borda"]}" '
             'stroke-width="0.8" fill-rule="evenodd"/>')

    # ---- riachos e rios
    riachos = [para_px(proj, l) for l in geo["riachos"]]
    s.append(f'<path d="{caminho(riachos, False)}" fill="none" '
             f'stroke="{COR["riacho"]}" stroke-width="0.9" stroke-linecap="round"/>')
    rios_px = {}
    for rio in geo["rios"]:
        ls = [para_px(proj, l) for l in rio["linhas"]]
        if not ls:
            continue
        rios_px[rio["nome"]] = ls
        larg = 2.6 if rio["nome"] in ("Rio Cachoeira", "Rio Almada") else 1.6
        s.append(f'<path d="{caminho(ls, False)}" fill="none" '
                 f'stroke="{COR["rio"]}" stroke-width="{larg}" '
                 'stroke-linecap="round" stroke-linejoin="round"/>')
    s.append(f'<path d="{caminho((a for p in agua for a in p), inteiro=True)}" '
             f'fill="{COR["agua"]}" fill-rule="evenodd"/>')
    s.append(f'<path d="{caminho(a for p in mar for a in p)}" '
             'fill="url(#mapa-mar)" fill-rule="evenodd"/>')

    # ---- rodovias
    estradas = [para_px(proj, l) for e in geo["estradas"] for l in e["linhas"]]
    d = caminho(estradas, False)
    s.append(f'<path d="{d}" fill="none" stroke="{COR["estrada_borda"]}" '
             'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    s.append(f'<path d="{d}" fill="none" stroke="{COR["estrada"]}" '
             'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')

    # ---- posicoes dos campi e dos cartoes (as arvores desviam deles)
    pinos, reservado = [], []
    for local in locais:
        x, y = proj(local["lat"], local["lon"])
        sg = sigla(local["nome"])
        dx, dy = CARTOES.get(sg, (0, -170))
        cx, cy = x + dx, y + dy
        alt = CARTAO_FOTO_A + CARTAO_LEGENDA_A
        bx = min(max(cx - CARTAO_L / 2, 10), W - CARTAO_L - 10)
        by = min(max(cy - alt / 2, 10), H - alt - 10)
        pinos.append((local, sg, x, y, bx, by))
        reservado.append((bx - 8, by - 8, bx + CARTAO_L + 8, by + alt + 8))
        reservado.append((x - 26, y - 62, x + 26, y + 6))

    rotulos_cidades = []
    for nome, lat, lon in CIDADES:
        x, y = proj(lat, lon)
        rotulos_cidades.append((nome, x, y))
        larg = len(nome) * 21
        reservado.append((x - larg / 2 - 8, y - 30, x + larg / 2 + 8, y + 14))

    # ---- arvores: grade com sorteio, so dentro da mata e longe do resto
    areas_mata, areas_urb, areas_mar = Areas(mata), Areas(urbano), Areas(mar)
    sorte = random.Random(7)
    arvores = []
    for gy in range(14, H - 4, PASSO_ARVORE):
        for gx in range(8, W - 8, PASSO_ARVORE):
            px = gx + sorte.uniform(-9, 9) + (PASSO_ARVORE / 2 if (gy // PASSO_ARVORE) % 2 else 0)
            py = gy + sorte.uniform(-8, 8)
            if not areas_mata.contem((px, py)):
                continue
            if areas_urb.contem((px, py)) or areas_mar.contem((px, py)):
                continue
            if any(a <= px <= c and b <= py <= d for a, b, c, d in reservado):
                continue
            arvores.append((py, px, sorte.random()))
    arvores.sort()
    usos = []
    for py, px, r in arvores:
        simb = "mapa-palmeira" if r < 0.18 else "mapa-arvore"
        tam = 11 + r * 4
        usos.append(f'<use href="#{simb}" x="{f(px - tam / 2)}" y="{f(py - tam)}" '
                    f'width="{f(tam)}" height="{f(tam * 14 / 12)}"/>')
    s.append('<g class="mapa-arvores">' + "".join(usos) + '</g>')

    # ---- rotulos dos rios, ao lado do trecho mais reto de cada um
    for nome, pos, desl in ROTULOS_RIOS:
        ls = rios_px.get(nome)
        if not ls:
            continue
        pts = max(ls, key=comprimento)
        largura_txt = len(nome) * 7.4 + 14
        corda = trecho_reto(pts, largura_txt, pos)
        if not corda:
            continue
        a, b = corda
        if a[0] > b[0]:
            a, b = b, a
        (x1, y1), (x2, y2) = deslocar([a, b], -desl)
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        s.append(f'<text class="mapa-rio-nome" fill="{COR["rio_texto"]}" '
                 f'x="{f((x1 + x2) / 2)}" y="{f((y1 + y2) / 2)}" text-anchor="middle" '
                 f'dominant-baseline="middle" '
                 f'transform="rotate({f(ang)} {f((x1 + x2) / 2)} {f((y1 + y2) / 2)})">'
                 f'{html.escape(nome)}</text>')

    # ---- mar
    mx = W - 34
    s.append(f'<text class="mapa-mar-nome" x="{mx}" y="{H * 0.62:.0f}" '
             f'transform="rotate(-90 {mx} {H * 0.62:.0f})" text-anchor="middle">'
             f'{t["mar"]}</text>')

    # ---- cidades
    for nome, x, y in rotulos_cidades:
        s.append(f'<text class="mapa-cidade" x="{f(x)}" y="{f(y)}" '
                 f'text-anchor="middle">{html.escape(nome)}</text>')

    # ---- cartoes com foto + linha ate o pino
    for local, sg, x, y, bx, by in pinos:
        alt = CARTAO_FOTO_A + CARTAO_LEGENDA_A
        # a linha sai do lado do cartao mais perto do pino
        ax = min(max(x, bx + 20), bx + CARTAO_L - 20)
        ay = by + alt if by + alt / 2 < y else by
        ty = y - 46 if ay < y else y + 2
        s.append(f'<path d="M{f(ax)},{f(ay)} L{f(x)},{f(ty)}" '
                 f'stroke="{COR["pino_escuro"]}" stroke-width="1.6" '
                 'stroke-dasharray="4 3" fill="none"/>')
        clip = f"mapa-foto-{lang}-{sg}"
        s.append(f'<g filter="url(#mapa-sombra)">'
                 f'<rect x="{f(bx)}" y="{f(by)}" width="{CARTAO_L}" height="{alt}" '
                 'rx="10" fill="#fff"/></g>')
        foto = local.get("foto", "")
        if foto and (ROOT / foto).exists():
            s.append(f'<clipPath id="{clip}"><rect x="{f(bx + 5)}" y="{f(by + 5)}" '
                     f'width="{CARTAO_L - 10}" height="{CARTAO_FOTO_A - 5}" rx="6"/>'
                     '</clipPath>')
            s.append(f'<image href="{prefixo}{html.escape(foto)}" x="{f(bx + 5)}" '
                     f'y="{f(by + 5)}" width="{CARTAO_L - 10}" '
                     f'height="{CARTAO_FOTO_A - 5}" preserveAspectRatio="xMidYMid slice" '
                     f'clip-path="url(#{clip})"/>')
        elif foto:
            print(f"mapa: aviso: foto {foto} nao existe", file=sys.stderr)
        nome_curto = re.sub(r"\s*\([^)]*\)\s*$", "", local["nome"])
        ly = by + CARTAO_FOTO_A + 16
        s.append(f'<text class="mapa-cartao-sigla" x="{f(bx + 12)}" y="{f(ly)}">'
                 f'{html.escape(sg)}</text>')
        s.append(f'<text class="mapa-cartao-nome" x="{f(bx + 12)}" y="{f(ly + 15)}">'
                 f'{html.escape(nome_curto)}</text>')

    # ---- pinos (por cima de tudo)
    for local, sg, x, y, bx, by in pinos:
        s.append(
            f'<g transform="translate({f(x)} {f(y)})" filter="url(#mapa-sombra)">'
            f'<path d="M0,0 C-6,-12 -21,-22 -21,-38 A21,21 0 1 1 21,-38 '
            f'C21,-22 6,-12 0,0 Z" fill="{COR["pino"]}" stroke="#fff" stroke-width="3"/>'
            f'<g transform="translate(0 -38)" fill="#fff">{ICONE_UNIVERSIDADE}</g>'
            '</g>')

    # ---- escala e norte
    km = 5
    larg = proj.px_km * km
    ex, ey = 24, H - 26
    s.append(f'<g class="mapa-escala">'
             f'<rect x="{ex - 8}" y="{ey - 32}" width="{f(larg + 54)}" height="46" '
             'rx="6" fill="#fff" fill-opacity="0.85"/>'
             f'<path d="M{ex},{ey - 6} v6 h{f(larg)} v-6" fill="none" '
             f'stroke="{COR["cidade"]}" stroke-width="2"/>'
             f'<text x="{ex}" y="{ey - 11}">0</text>'
             f'<text x="{f(ex + larg)}" y="{ey - 11}" text-anchor="middle">'
             f'{km} {t["km"]}</text>'
             f'<g transform="translate({f(ex + larg + 28)} {ey - 4})">'
             f'<path d="M0,-14 L6,4 L0,0 L-6,4 Z" fill="{COR["cidade"]}"/>'
             '<text x="0" y="-16" text-anchor="middle">N</text></g>'
             '</g>')

    if brasil:
        s.append(miniatura(brasil, locais, W))

    s.append(f'<text class="mapa-credito" x="{W - 10}" y="{H - 10}" '
             f'text-anchor="end">{t["credito"]}</text>')
    s.append('</svg>')
    return "".join(s)


def render(geo, locais, lang, brasil=None):
    t = TXT[lang]
    itens = []
    for local in locais:
        nome = html.escape(local["nome"])
        end = html.escape(local.get(f"endereco_{lang}") or local.get("endereco_pt", ""))
        itens.append(
            f'<li class="local-card">'
            f'<span class="local-icone" aria-hidden="true">'
            f'<svg viewBox="-14 -14 28 28">{ICONE_UNIVERSIDADE}</svg></span>'
            f'<span class="local-corpo">'
            f'<span class="local-nome">{nome}</span>'
            f'<span class="local-end">{end}</span>'
            f'<span class="local-links">'
            f'<a href="{gmaps_ver(local)}" target="_blank" rel="noopener">{t["ver"]}</a>'
            f'<a href="{gmaps_rota(local)}" target="_blank" rel="noopener">{t["rotas"]}</a>'
            '</span></span></li>')

    lat = sum(l["lat"] for l in locais) / len(locais)
    lon = sum(l["lon"] for l in locais) / len(locais)
    geral = f"https://www.google.com/maps/@{lat:.4f},{lon:.4f},12z"

    # tudo numa linha so: o Pandoc trata o bloco como HTML cru ate a
    # primeira linha em branco
    return (
        '<div class="mapa-wrap">'
        f'<div class="mapa-quadro">{desenhar(geo, locais, lang, brasil)}</div>'
        f'<p class="mapa-legenda"><span class="mapa-rolar">{t["rolar"]}</span>'
        f'<a href="{geral}" target="_blank" rel="noopener">{t["abrir"]}</a></p>'
        f'<ul class="local-list">{"".join(itens)}</ul>'
        '</div>\n')


def main():
    locais = ler_locais()
    if not GEO.exists():
        sys.exit(f"{GEO.relative_to(ROOT)} nao existe. "
                 "Rode uma vez: python3 scripts/baixar-mapa-osm.py")
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    # a miniatura do Brasil e' opcional: sem o arquivo, o mapa sai sem ela
    brasil = (json.loads(GEO_BRASIL.read_text(encoding="utf-8"))
              if GEO_BRASIL.exists() else None)

    OUT.mkdir(exist_ok=True)
    banner = ("<!-- gerado por scripts/build-mapa.py a partir de "
              "_data/locais.tsv e _data/mapa-osm.json - nao editar a mao -->\n")
    for lang, arq in (("pt", "mapa-pt.html"), ("en", "mapa-en.html")):
        conteudo = render(geo, locais, lang, brasil)
        (OUT / arq).write_text(banner + conteudo, encoding="utf-8")
    kb = len(conteudo.encode()) / 1024
    print(f"mapa: {len(locais)} campi -> _includes/mapa-*.html ({kb:.0f} KB cada)")


if __name__ == "__main__":
    main()
