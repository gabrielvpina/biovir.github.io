#!/usr/bin/env python3
"""Gera o mapa da secao "Onde estamos" a partir de _data/locais.tsv.

Uso:

    python3 scripts/build-mapa.py           # regenera so o HTML
    python3 scripts/build-mapa.py --gerar   # baixa e redesenha a imagem do mapa

O mapa e' uma IMAGEM ESTATICA guardada no repositorio (assets/mapa-campi.png).
Quem visita o site nao carrega biblioteca de mapa nem busca tiles em servico
externo: nada depende de chave de API, de CDN no ar ou da politica de uso de
terceiros. Em troca o mapa nao tem zoom - clicar nele abre o OpenStreetMap.

O ./build.sh roda a versao SEM --gerar, entao o site compila sem internet.
Rode com --gerar so quando mudar os pontos em _data/locais.tsv, e commite a
imagem junto.

Saidas:
    assets/mapa-campi.jpg     imagem do mapa (so muda com --gerar)
    _includes/mapa-pt.html    usado por index.qmd
    _includes/mapa-en.html    usado por en/index.qmd
"""

import argparse
import csv
import html
import math
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DADOS = ROOT / "_data" / "locais.tsv"
OUT = ROOT / "_includes"
IMAGEM = ROOT / "assets" / "mapa-campi.jpg"

# Tamanho da imagem gerada. E' o dobro do tamanho de exibicao, para ficar nitida
# em tela retina; o CSS reduz pela metade.
LARGURA, ALTURA = 2270, 760

# Folga em volta dos pontos, como fracao da distancia entre eles.
FOLGA = 0.30

# Servico que devolve o recorte do mapa ja pronto, sem chave de API.
# Para trocar de provedor, mude esta funcao e a atribuicao em TXT.
EXPORT = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
          "World_Street_Map/MapServer/export")

# Cores dos pinos (mesma paleta de styles/biovir.scss)
AZUL = (48, 78, 161)
BRANCO = (255, 255, 255)

UA = {"User-Agent": "biovirlab-site/1.0 (+https://www.biovirlab.com.br)"}

TXT = {
    "pt": {
        "alt": "Mapa com a localização dos campi do BioVirLab",
        "rotas": "Ver rotas",
        "abrir": "Abrir no OpenStreetMap",
        "credito": "Mapa: Esri, OpenStreetMap",
    },
    "en": {
        "alt": "Map showing the location of the BioVirLab campuses",
        "rotas": "Get directions",
        "abrir": "Open in OpenStreetMap",
        "credito": "Map: Esri, OpenStreetMap",
    },
}


# ----------------------------------------------------------- coordenadas ---

def mercator(lat, lon):
    """Graus decimais -> metros em Web Mercator (EPSG:3857)."""
    x = lon * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
    return x, y * 20037508.34 / 180


def caixa(pontos):
    """Retangulo em Web Mercator que cobre os pontos, na proporcao da imagem."""
    xs, ys = zip(*[mercator(p["lat"], p["lon"]) for p in pontos])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # um ponto so (ou pontos alinhados) nao tem largura: usa um raio minimo
    larg = max(x1 - x0, 1500.0)
    alt = max(y1 - y0, 1500.0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    larg *= 1 + 2 * FOLGA
    alt *= 1 + 2 * FOLGA
    # ajusta para a proporcao da imagem, sempre crescendo (nunca cortando)
    proporcao = LARGURA / ALTURA
    if larg / alt < proporcao:
        larg = alt * proporcao
    else:
        alt = larg / proporcao
    return cx - larg / 2, cy - alt / 2, cx + larg / 2, cy + alt / 2


def para_pixel(lat, lon, cx):
    """Coordenada geografica -> pixel na imagem."""
    x0, y0, x1, y1 = cx
    mx, my = mercator(lat, lon)
    return ((mx - x0) / (x1 - x0) * LARGURA,
            (1 - (my - y0) / (y1 - y0)) * ALTURA)


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
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                sys.exit(f"{DADOS.name}: linha {n}: coordenada fora de faixa")
            linha["lat"], linha["lon"] = lat, lon
            locais.append(linha)
    if not locais:
        sys.exit(f"{DADOS.name}: nenhum ponto")
    return locais


# ----------------------------------------------------------------- imagem --

def fonte(tamanho):
    """Fonte para o numero do pino, com alternativas por sistema."""
    from PIL import ImageFont
    candidatas = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for c in candidatas:
        if pathlib.Path(c).exists():
            try:
                return ImageFont.truetype(c, tamanho)
            except OSError:
                pass
    return ImageFont.load_default(size=tamanho)


def gerar_imagem(locais):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        sys.exit("--gerar precisa do Pillow:  python3 -m pip install Pillow")

    cx = caixa(locais)
    url = EXPORT + "?" + urllib.parse.urlencode({
        "bbox": ",".join(f"{v:.2f}" for v in cx),
        "bboxSR": 3857, "imageSR": 3857,
        "size": f"{LARGURA},{ALTURA}",
        "format": "png32", "transparent": "false", "f": "image",
    })
    try:
        dados = urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=120).read()
    except Exception as erro:
        sys.exit(f"falha ao baixar o mapa: {erro}")

    import io
    img = Image.open(io.BytesIO(dados)).convert("RGB")
    desenho = ImageDraw.Draw(img)

    raio = 30
    fnt = fonte(34)
    for i, local in enumerate(locais, 1):
        x, y = para_pixel(local["lat"], local["lon"], cx)
        # sombra suave, para o pino nao sumir sobre area clara
        desenho.ellipse([x - raio - 3, y - raio - 3, x + raio + 3, y + raio + 3],
                        fill=(23, 35, 63, 60))
        desenho.ellipse([x - raio, y - raio, x + raio, y + raio],
                        fill=AZUL, outline=BRANCO, width=5)
        desenho.text((x, y + 1), str(i), font=fnt, fill=BRANCO, anchor="mm")

    IMAGEM.parent.mkdir(parents=True, exist_ok=True)
    # JPEG, e nao PNG: o mapa e' quase todo sombreado suave, que PNG comprime
    # mal (800 KB contra 150 KB no JPEG, sem diferenca visivel a 1:1)
    img.save(IMAGEM, "JPEG", quality=82, optimize=True, progressive=True)
    kb = IMAGEM.stat().st_size / 1024
    print(f"mapa: imagem {LARGURA}x{ALTURA} -> "
          f"{IMAGEM.relative_to(ROOT)} ({kb:.0f} KB)")


# ------------------------------------------------------------------ html ---

def render(locais, lang):
    t = TXT[lang]
    prefixo = "" if lang == "pt" else "../"

    itens = []
    for i, local in enumerate(locais, 1):
        end = local.get(f"endereco_{lang}") or local.get("endereco_pt", "")
        rota = f'https://www.openstreetmap.org/directions?to={local["lat"]},{local["lon"]}'
        itens.append(
            f'<li><span class="local-num">{i}</span>'
            f'<span class="local-corpo">'
            f'<span class="local-nome">{html.escape(local["nome"])}</span>'
            f'<span class="local-end">{html.escape(end)}</span>'
            f'<a class="local-rota" href="{rota}" target="_blank" rel="noopener">'
            f'{t["rotas"]}</a></span></li>')

    # o link abre o mapa interativo para quem quiser explorar
    lat = sum(l["lat"] for l in locais) / len(locais)
    lon = sum(l["lon"] for l in locais) / len(locais)
    osm = f"https://www.openstreetmap.org/#map=12/{lat:.4f}/{lon:.4f}"

    return (
        '<div class="mapa-wrap">'
        f'<a class="mapa-img no-external" href="{osm}" target="_blank" rel="noopener" '
        f'title="{html.escape(t["abrir"])}">'
        f'<img src="{prefixo}assets/mapa-campi.jpg" alt="{html.escape(t["alt"])}" '
        f'width="{LARGURA // 2}" height="{ALTURA // 2}" loading="lazy" />'
        f'<span class="mapa-credito">{html.escape(t["credito"])}</span></a>'
        f'<ul class="local-list">{"".join(itens)}</ul>'
        '</div>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gerar", action="store_true",
                    help="baixa e redesenha assets/mapa-campi.png")
    args = ap.parse_args()

    locais = ler_locais()
    if args.gerar:
        gerar_imagem(locais)
    elif not IMAGEM.exists():
        sys.exit(f"{IMAGEM.relative_to(ROOT)} nao existe. "
                 "Rode uma vez com --gerar.")

    OUT.mkdir(exist_ok=True)
    banner = ("<!-- gerado por scripts/build-mapa.py a partir de "
              "_data/locais.tsv - nao editar a mao -->\n")
    for lang, arq in (("pt", "mapa-pt.html"), ("en", "mapa-en.html")):
        (OUT / arq).write_text(banner + render(locais, lang), encoding="utf-8")
    print(f"mapa: {len(locais)} ponto(s) -> _includes/mapa-*.html")


if __name__ == "__main__":
    main()
