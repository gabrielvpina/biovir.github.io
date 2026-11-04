#!/usr/bin/env python3
"""Baixa a geografia do mapa "Onde estamos", que scripts/build-mapa.py usa:

    _data/mapa-osm.json      costa, rios, matas, cidades e rodovias da regiao
                             (OpenStreetMap)
    _data/mapa-brasil.json   contorno do Brasil e da Bahia, para a miniatura
                             no canto do mapa (Natural Earth)

Rode SO quando quiser atualizar a geografia (raramente): precisa de internet
e da biblioteca shapely. O build normal (./build.sh) nao roda este script e
nao precisa de nenhum dos dois.

    python3 -m pip install shapely
    python3 scripts/baixar-mapa-osm.py              # baixa tudo
    python3 scripts/baixar-mapa-osm.py --osm bruto.json --ne estados.geojson
                                                    # reprocessa downloads

Dados (c) colaboradores do OpenStreetMap, licenca ODbL - o credito aparece no
proprio mapa. Natural Earth e' dominio publico.
"""

import json
import pathlib
import sys
import urllib.parse
import urllib.request

try:
    from shapely.geometry import LineString, MultiLineString, Polygon, box, mapping
    from shapely.ops import linemerge, polygonize, split, unary_union
except ImportError:
    sys.exit("precisa do shapely:  python3 -m pip install shapely")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAIDA = ROOT / "_data" / "mapa-osm.json"
SAIDA_BRASIL = ROOT / "_data" / "mapa-brasil.json"

# estados do mundo na escala 1:50 milhoes - suficiente para uma miniatura
NATURAL_EARTH = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
                 "master/geojson/ne_50m_admin_1_states_provinces.geojson")
ESTADO = "Bahia"
SIMPLIFICAR_BRASIL = 0.08   # graus; a miniatura tem ~150 px de largura

# Recorte do mapa (oeste, sul, leste, norte), em graus. Vai de Itabuna ate um
# pouco de mar depois de Ilheus. Mudou aqui -> rode este script de novo.
RECORTE = (-39.31, -14.865, -38.99, -14.705)

# O download pega uma margem a mais, para a costa e os rios atravessarem o
# recorte inteiro antes de serem cortados.
MARGEM = 0.02

# Simplificacao das formas, em graus (0.0001 ~ 11 m). Menos detalhe = HTML
# menor; o mapa e' exibido com ~1100 px de largura, entao ~30 m por pixel.
SIMPLIFICAR = 0.00012

# Areas menores que isso (graus^2; 1e-6 ~ 1,2 ha) sao descartadas.
AREA_MINIMA = 2e-6

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = {"User-Agent": "biovirlab-site/1.0 (+https://www.biovirlab.com.br)"}


def consulta():
    w, s, e, n = RECORTE
    bb = f"{s - MARGEM},{w - MARGEM},{n + MARGEM},{e + MARGEM}"
    return f"""[out:json][timeout:180][bbox:{bb}];
(
 way["natural"="coastline"];
 way["waterway"~"^(river|stream)$"];
 way["natural"="water"]; relation["natural"="water"];
 way["landuse"="residential"];
 way["highway"~"^(motorway|trunk|primary)$"];
 way["natural"="wood"]; relation["natural"="wood"];
 way["landuse"="forest"]; relation["landuse"="forest"];
 way["natural"="wetland"]; relation["natural"="wetland"];
);
out geom;"""


def baixar():
    dados = urllib.parse.urlencode({"data": consulta()}).encode()
    for url in OVERPASS:
        print(f"baixando de {url} ...")
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(url, data=dados, headers=UA), timeout=300)
            return json.loads(resp.read())
        except Exception as erro:
            print(f"  falhou: {erro}")
    sys.exit("nenhum servidor Overpass respondeu; tente mais tarde")


# ------------------------------------------------------------ geometrias ---

def linha(geom):
    return LineString([(p["lon"], p["lat"]) for p in geom])


def poligonos(el):
    """Way fechado ou relacao multipolygon -> geometria shapely (ou None)."""
    if el["type"] == "way":
        g = el.get("geometry") or []
        if len(g) < 4 or g[0] != g[-1]:
            return None
        p = Polygon([(q["lon"], q["lat"]) for q in g])
        return p if p.is_valid else p.buffer(0)
    externos, internos = [], []
    for m in el.get("members", []):
        if m.get("type") != "way" or not m.get("geometry"):
            continue
        (internos if m.get("role") == "inner" else externos).append(linha(m["geometry"]))
    fora = unary_union(list(polygonize(linemerge(externos)))) if externos else None
    if fora is None or fora.is_empty:
        return None
    if internos:
        dentro = unary_union(list(polygonize(linemerge(internos))))
        fora = fora.difference(dentro)
    return fora


def aneis(geom):
    """Poligono/multipoligono -> lista de poligonos, cada um lista de aneis."""
    if geom.is_empty:
        return []
    partes = getattr(geom, "geoms", [geom])
    saida = []
    for p in partes:
        if p.geom_type != "Polygon" or p.area < AREA_MINIMA:
            continue
        rs = [p.exterior] + [i for i in p.interiors if Polygon(i).area >= AREA_MINIMA]
        saida.append([[[round(x, 5), round(y, 5)] for x, y in r.coords] for r in rs])
    return saida


def linhas(geom):
    if geom.is_empty:
        return []
    partes = getattr(geom, "geoms", [geom])
    return [[[round(x, 5), round(y, 5)] for x, y in l.coords]
            for l in partes if l.geom_type == "LineString" and len(l.coords) > 1]


def processar(bruto):
    quadro = box(*RECORTE)
    els = bruto["elements"]

    def tags(e):
        return e.get("tags", {})

    def area(filtro, encolher=0.0):
        gs = [poligonos(e) for e in els if filtro(tags(e))]
        g = unary_union([x for x in gs if x is not None and not x.is_empty])
        if encolher:
            # junta quarteiroes vizinhos numa mancha so
            g = g.buffer(encolher).buffer(-encolher * 0.7)
        return g.intersection(quadro).simplify(SIMPLIFICAR)

    # mar: corta o quadro pela linha de costa e fica com os pedacos que
    # encostam na borda leste (o mar fica a leste de Ilheus)
    costa = linemerge([linha(e["geometry"]) for e in els
                       if tags(e).get("natural") == "coastline"])
    pedacos = split(quadro, costa).geoms if not costa.is_empty else []
    leste = RECORTE[2]
    mar = unary_union([p for p in pedacos if abs(p.bounds[2] - leste) < 1e-9]
                      or [Polygon()])
    mar = mar.simplify(SIMPLIFICAR)

    agua = area(lambda t: t.get("natural") == "water")
    mata = area(lambda t: t.get("natural") == "wood" or t.get("landuse") == "forest")
    mangue = area(lambda t: t.get("natural") == "wetland")
    urbano = area(lambda t: t.get("landuse") == "residential", encolher=0.0012)
    mata = mata.difference(urbano)

    # rios com nome (para os rotulos) e riachos sem destaque
    nomes = {}
    riachos = []
    for e in els:
        t = tags(e)
        if t.get("waterway") == "river":
            nomes.setdefault(t.get("name") or "", []).append(linha(e["geometry"]))
        elif t.get("waterway") == "stream":
            riachos.append(linha(e["geometry"]))
    rios = []
    for nome, ls in sorted(nomes.items()):
        g = linemerge(ls).intersection(quadro).simplify(SIMPLIFICAR)
        rios.append({"nome": nome, "linhas": linhas(g)})
    riachos = linhas(unary_union(riachos).intersection(quadro).simplify(SIMPLIFICAR))

    estradas = {}
    for e in els:
        t = tags(e)
        if t.get("highway") in ("motorway", "trunk", "primary"):
            estradas.setdefault(t.get("ref", "").split(";")[0], []).append(linha(e["geometry"]))
    estradas = [{"ref": ref, "linhas": linhas(linemerge(ls).intersection(quadro)
                                               .simplify(SIMPLIFICAR))}
                for ref, ls in sorted(estradas.items())]

    return {
        "fonte": "OpenStreetMap (ODbL), " + bruto.get("osm3s", {}).get(
            "timestamp_osm_base", ""),
        "recorte": list(RECORTE),
        "mar": aneis(mar),
        "agua": aneis(agua),
        "mangue": aneis(mangue),
        "mata": aneis(mata),
        "urbano": aneis(urbano),
        "rios": rios,
        "riachos": riachos,
        "estradas": estradas,
    }


def brasil(estados):
    """Estados do Natural Earth -> contorno do Brasil e do estado destacado."""
    from shapely.geometry import shape
    br = [f for f in estados["features"] if f["properties"].get("adm0_a3") == "BRA"]
    if not br:
        sys.exit("Natural Earth: nenhum estado do Brasil encontrado")
    formas = {f["properties"]["name"]: shape(f["geometry"]).buffer(0) for f in br}
    if ESTADO not in formas:
        sys.exit(f"Natural Earth: estado {ESTADO!r} nao encontrado")
    # o pequeno buffer fecha frestas entre estados vizinhos
    pais = unary_union(list(formas.values())).buffer(0.02).buffer(-0.02)

    def limpar(g):
        g = g.simplify(SIMPLIFICAR_BRASIL)
        partes = [p for p in getattr(g, "geoms", [g])
                  if p.geom_type == "Polygon" and p.area > 0.3]
        return [[[[round(x, 3), round(y, 3)] for x, y in p.exterior.coords]]
                for p in partes]

    return {"fonte": "Natural Earth (dominio publico)",
            "pais": limpar(pais), "estado_nome": ESTADO,
            "estado": limpar(formas[ESTADO])}


def ler_ou_baixar(caminho, url=None):
    if caminho:
        return json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))
    print(f"baixando {url} ...")
    try:
        resp = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                      timeout=300)
        return json.loads(resp.read())
    except Exception as erro:
        sys.exit(f"falha ao baixar: {erro}")


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--osm", help="usa um download do Overpass ja salvo")
    ap.add_argument("--ne", help="usa um geojson de estados do Natural Earth ja salvo")
    args = ap.parse_args()

    dados_br = brasil(ler_ou_baixar(args.ne, NATURAL_EARTH))
    SAIDA_BRASIL.write_text(json.dumps(dados_br, ensure_ascii=False,
                                       separators=(",", ":")), encoding="utf-8")
    kb = SAIDA_BRASIL.stat().st_size / 1024
    print(f"mapa: {SAIDA_BRASIL.relative_to(ROOT)} ({kb:.0f} KB)")

    bruto = ler_ou_baixar(args.osm) if args.osm else baixar()
    dados = processar(bruto)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
                     encoding="utf-8")
    kb = SAIDA.stat().st_size / 1024
    print(f"mapa: {SAIDA.relative_to(ROOT)} ({kb:.0f} KB) - "
          f"{len(dados['mata'])} matas, {len(dados['urbano'])} areas urbanas, "
          f"{len(dados['rios'])} rios")


if __name__ == "__main__":
    main()
