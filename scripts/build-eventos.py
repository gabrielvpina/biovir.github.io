#!/usr/bin/env python3
"""Gera as paginas de eventos a partir das pastas em eventos/.

Cada subpasta de eventos/ e um evento e deve conter:

    eventos/<slug>/evento.yml    dados do evento (chave: valor)
    eventos/<slug>/texto-pt.md   texto da pagina em portugues
    eventos/<slug>/texto-en.md   texto em ingles (opcional; cai para o pt)
    eventos/<slug>/capa.jpg      imagem de capa (opcional)
    eventos/<slug>/fotos/        imagens da galeria (opcional)

Pastas cujo nome comeca com "_" sao ignoradas (ex.: eventos/_modelo).

Saidas:
    _includes/eventos-pt.html        lista usada por eventos.qmd
    _includes/eventos-en.html        lista usada por en/events.qmd
    eventos/<slug>/index.qmd         pagina pt-BR do evento
    en/events/<slug>/index.qmd       pagina em ingles do evento

Todas as saidas sao regeradas a cada ./build.sh - nao edite a mao.
"""

import datetime
import html
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "eventos"
OUT_INC = ROOT / "_includes"
OUT_EN = ROOT / "en" / "events"

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

CAMPOS_OBRIGATORIOS = ["titulo_pt", "data"]

TXT = {
    "pt": {
        "voltar": "← Todos os eventos",
        "galeria": "Galeria",
        "site": "Site do evento",
        "proximos": "Próximos",
        "realizados": "Realizados",
        "vazio": "Nenhum evento cadastrado ainda.",
    },
    "en": {
        "voltar": "← All events",
        "galeria": "Gallery",
        "site": "Event website",
        "proximos": "Upcoming",
        "realizados": "Past",
        "vazio": "No events registered yet.",
    },
}


def parse_campos(path):
    """Le um arquivo simples de 'chave: valor'. Ignora comentarios e vazios."""
    dados = {}
    for n, linha in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if ":" not in linha:
            sys.exit(f"{path}: linha {n} sem ':' -> {linha!r}")
        chave, valor = linha.split(":", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        dados[chave.strip()] = valor
    return dados


def ler_texto(pasta, lang):
    arq = pasta / f"texto-{lang}.md"
    if arq.exists() and arq.read_text(encoding="utf-8").strip():
        return arq.read_text(encoding="utf-8").strip()
    if lang == "en":
        return ler_texto(pasta, "pt")
    return ""


def legenda(nome):
    """01-abertura-do-evento.jpg -> 'Abertura do evento'"""
    base = re.sub(r"^[\d]+[-_\s]*", "", pathlib.Path(nome).stem)
    base = base.replace("-", " ").replace("_", " ").strip()
    return base[:1].upper() + base[1:] if base else ""


def campo(dados, nome, lang):
    """titulo_pt / titulo_en, com queda para a versao pt se a en faltar."""
    valor = dados.get(f"{nome}_{lang}", "").strip()
    if not valor and lang == "en":
        valor = dados.get(f"{nome}_pt", "").strip()
    return valor


def ler_eventos():
    if not SRC.is_dir():
        return []
    eventos = []
    for pasta in sorted(SRC.iterdir()):
        if not pasta.is_dir() or pasta.name.startswith("_") or pasta.name.startswith("."):
            continue
        yml = pasta / "evento.yml"
        if not yml.exists():
            print(f"  aviso: {pasta.name}/ sem evento.yml - ignorado")
            continue
        dados = parse_campos(yml)
        for obrig in CAMPOS_OBRIGATORIOS:
            if not dados.get(obrig):
                sys.exit(f"{yml}: campo obrigatorio ausente ou vazio: {obrig}")
        try:
            data = datetime.date.fromisoformat(dados["data"])
        except ValueError:
            sys.exit(f"{yml}: 'data' deve estar no formato AAAA-MM-DD (achei {dados['data']!r})")

        capa = dados.get("capa", "").strip()
        if capa and not (pasta / capa).exists():
            sys.exit(f"{yml}: capa '{capa}' nao existe em {pasta.name}/")

        fotos = []
        dir_fotos = pasta / "fotos"
        if dir_fotos.is_dir():
            fotos = sorted(
                f.name for f in dir_fotos.iterdir()
                if f.is_file() and f.suffix.lower() in IMG_EXT
            )

        eventos.append({
            "slug": pasta.name,
            "pasta": pasta,
            "dados": dados,
            "data": data,
            "capa": capa,
            "fotos": fotos,
            "texto_pt": ler_texto(pasta, "pt"),
            "texto_en": ler_texto(pasta, "en"),
        })
    eventos.sort(key=lambda e: e["data"], reverse=True)
    return eventos


# --------------------------------------------------------------- lista ---

def item_lista(ev, lang, prefixo_href):
    d = ev["dados"]
    titulo = html.escape(campo(d, "titulo", lang))
    data_txt = html.escape(campo(d, "data_texto", lang)) or ev["data"].strftime("%d/%m/%Y")
    local = html.escape(campo(d, "local", lang))
    resumo = html.escape(campo(d, "resumo", lang))
    href = f"{prefixo_href}{ev['slug']}/"

    descricao = " — ".join(p for p in (local, resumo) if p)
    capa = ""
    if ev["capa"]:
        src = html.escape(f"{prefixo_img(lang)}{ev['slug']}/{ev['capa']}")
        capa = (f'<span class="event-thumb">'
                f'<img src="{src}" alt="" loading="lazy" /></span>')

    return (
        f'<a class="event-item event-link" href="{html.escape(href)}" '
        f'target="_blank" rel="noopener">'
        f'<span class="event-date">{data_txt}</span>'
        f'<span class="event-body">'
        f'<span class="event-title">{titulo}</span>'
        f'<span class="event-desc">{descricao}</span>'
        f"</span>{capa}</a>"
    )


def prefixo_img(lang):
    # eventos.qmd fica na raiz; en/events.qmd fica em en/
    return "eventos/" if lang == "pt" else "../eventos/"


def render_lista(eventos, lang):
    hoje = datetime.date.today()
    prefixo = "eventos/" if lang == "pt" else "events/"
    proximos = [e for e in eventos if e["data"] >= hoje]
    realizados = [e for e in eventos if e["data"] < hoje]
    t = TXT[lang]

    out = []
    if not eventos:
        return f"<p>{t['vazio']}</p>\n"
    for rotulo, grupo in ((t["proximos"], proximos), (t["realizados"], realizados)):
        if not grupo:
            continue
        out.append(f'<h2 class="event-group-title">{rotulo}</h2>')
        out.append('<div class="event-list">')
        out.extend(item_lista(e, lang, prefixo) for e in grupo)
        out.append("</div>")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------- pagina ---

def render_pagina(ev, lang):
    d = ev["dados"]
    t = TXT[lang]
    titulo = campo(d, "titulo", lang)
    data_txt = campo(d, "data_texto", lang) or ev["data"].strftime("%d/%m/%Y")
    local = campo(d, "local", lang)
    resumo = campo(d, "resumo", lang)
    link = d.get("link", "").strip()
    texto = ev["texto_pt"] if lang == "pt" else ev["texto_en"]

    # caminho das imagens a partir da pagina renderizada
    #   pt:  docs/eventos/<slug>/index.html      -> arquivo ao lado
    #   en:  docs/en/events/<slug>/index.html    -> ../../../eventos/<slug>/
    img = "" if lang == "pt" else f"../../../eventos/{ev['slug']}/"
    voltar = "../../eventos.html" if lang == "pt" else "../../events.html"

    aspas = '"'
    fm = [
        "---",
        f'title: {aspas}{titulo.replace(aspas, "")}{aspas}',
        f'pagetitle: {aspas}{titulo.replace(aspas, "")} — BioVirLab{aspas}',
    ]
    if resumo:
        fm.append(f'description-meta: {aspas}{resumo.replace(aspas, "")}{aspas}')
    fm += ["---", "",
           "<!-- gerado por scripts/build-eventos.py - nao editar a mao;",
           f"     edite eventos/{ev['slug']}/ e rode ./build.sh -->", ""]

    body = [
        '<p class="event-back"><a href="%s">%s</a></p>' % (html.escape(voltar), t["voltar"]),
        "",
        '::: {.event-meta}',
        f"{html.escape(data_txt)}" + (f" · {html.escape(local)}" if local else ""),
        ":::",
        "",
    ]
    if ev["capa"]:
        body += [
            f'![]({img}{ev["capa"]}){{.event-cover fig-alt="{html.escape(titulo)}"}}',
            "",
        ]
    if resumo:
        body += ["::: {.lead}", resumo, ":::", ""]
    if texto:
        body += [texto, ""]
    if link:
        body += [f'[{t["site"]}]({link}){{.btn-biovir-ghost target="_blank" rel="noopener"}}', ""]
    if ev["fotos"]:
        body += [f"## {t['galeria']}", "", '<div class="event-gallery">']
        for nome in ev["fotos"]:
            alt = html.escape(legenda(nome) or titulo)
            src = html.escape(f"{img}fotos/{nome}")
            body.append(
                f'<figure><img src="{src}" alt="{alt}" loading="lazy" />'
                + (f"<figcaption>{alt}</figcaption>" if legenda(nome) else "")
                + "</figure>"
            )
        body += ["</div>", ""]

    return "\n".join(fm + body).rstrip() + "\n"


# ----------------------------------------------------------------- main ---

def limpar_geradas(eventos):
    """Remove index.qmd de eventos que deixaram de existir."""
    validos = {e["slug"] for e in eventos}
    if OUT_EN.is_dir():
        for p in OUT_EN.iterdir():
            if p.is_dir() and p.name not in validos:
                shutil.rmtree(p)
    if SRC.is_dir():
        for p in SRC.iterdir():
            if p.is_dir() and p.name not in validos:
                (p / "index.qmd").unlink(missing_ok=True)


def main():
    eventos = ler_eventos()
    OUT_INC.mkdir(exist_ok=True)
    OUT_EN.mkdir(parents=True, exist_ok=True)

    banner = ("<!-- gerado por scripts/build-eventos.py a partir de eventos/ "
              "- nao editar a mao -->\n")
    (OUT_INC / "eventos-pt.html").write_text(banner + render_lista(eventos, "pt"), encoding="utf-8")
    (OUT_INC / "eventos-en.html").write_text(banner + render_lista(eventos, "en"), encoding="utf-8")

    for ev in eventos:
        (ev["pasta"] / "index.qmd").write_text(
            render_pagina(ev, "pt"), encoding="utf-8")
        destino = OUT_EN / ev["slug"]
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.qmd").write_text(
            render_pagina(ev, "en"), encoding="utf-8")

    limpar_geradas(eventos)
    n_fotos = sum(len(e["fotos"]) for e in eventos)
    print(f"eventos: {len(eventos)} evento(s), {n_fotos} foto(s) -> "
          f"_includes/eventos-*.html, eventos/*/index.qmd, en/events/*/index.qmd")


if __name__ == "__main__":
    main()
