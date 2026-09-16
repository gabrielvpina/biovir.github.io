#!/usr/bin/env python3
"""Gera a faixa de numeros da pagina inicial.

Saidas:
    _includes/stats-pt.html   usado por index.qmd
    _includes/stats-en.html   usado por en/index.qmd

Cada numero vem de um arquivo do proprio repositorio, para nao ficar
desatualizado a mao:

    Integrantes        linhas de _data/members.tsv
    Linhas de pesquisa blocos .research-line em linhas-de-pesquisa.qmd
    Publicacoes        _data/estatisticas.json (escrito por build-publicacoes.py)
    Colaboracoes       _data/estatisticas.json

Rode build-publicacoes.py antes deste script - o ./build.sh ja faz isso na ordem
certa.
"""

import csv
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEMBROS = ROOT / "_data" / "members.tsv"
ESTATS = ROOT / "_data" / "estatisticas.json"
LINHAS = ROOT / "linhas-de-pesquisa.qmd"
OUT = ROOT / "_includes"

# rotulo de cada numero nos dois idiomas
ROTULOS = {
    "integrantes": ("Integrantes", "Members"),
    "linhas": ("Linhas de pesquisa", "Research lines"),
    "publicacoes": ("Publicações", "Publications"),
    "colaboracoes": ("Colaborações", "Collaborations"),
}

# destino do link de cada numero (pt, en); None = sem link
DESTINOS = {
    "integrantes": ("membros.html", "members.html"),
    "linhas": ("linhas-de-pesquisa.html", "research.html"),
    "publicacoes": ("publicacoes.html", "publications.html"),
    # a ancora em pt leva acento porque o Quarto gera o id a partir do titulo
    "colaboracoes": ("publicacoes.html#colaborações", "publications.html#collaborations"),
}


def conta_membros():
    """Conta so quem esta no laboratorio hoje: alumni ficam de fora."""
    with MEMBROS.open(encoding="utf-8") as fh:
        return sum(1 for linha in csv.DictReader(fh, delimiter="\t")
                   if (linha.get("name") or "").strip()
                   and (linha.get("group") or "").strip() != "alumni")


def conta_linhas_de_pesquisa():
    if not LINHAS.exists():
        return 0
    return len(re.findall(r"^::: *\{\.research-line\}", LINHAS.read_text(encoding="utf-8"),
                          flags=re.MULTILINE))


def le_estatisticas():
    if not ESTATS.exists():
        print("  aviso: _data/estatisticas.json nao existe - "
              "rode scripts/build-publicacoes.py antes")
        return {}
    return json.loads(ESTATS.read_text(encoding="utf-8"))


def render(valores, lang):
    """Sai tudo em UMA linha de proposito.

    Se as tags ficarem em linhas separadas, o Pandoc trata <a> (que e' inline)
    como paragrafo e embrulha os quatro numeros num unico <p>. Ai o grid do
    .stat-row passa a ter um filho so e os numeros empilham em vez de ficarem
    lado a lado. Numa linha unica o bloco passa inteiro, sem <p>.
    """
    idx = 0 if lang == "pt" else 1
    itens = []
    for chave in ("integrantes", "linhas", "publicacoes", "colaboracoes"):
        valor = valores.get(chave)
        texto = "—" if not valor else str(valor)
        rotulo = html.escape(ROTULOS[chave][idx])
        href = html.escape(DESTINOS[chave][idx])
        itens.append(f'<a class="stat-item no-external" href="{href}">'
                     f'<span class="stat-value">{texto}</span>'
                     f'<span class="stat-label">{rotulo}</span></a>')
    return '<div class="stat-row">' + "".join(itens) + "</div>\n"


def main():
    est = le_estatisticas()
    valores = {
        "integrantes": conta_membros(),
        "linhas": conta_linhas_de_pesquisa(),
        "publicacoes": est.get("publicacoes"),
        "colaboracoes": est.get("colaboradores"),
    }
    OUT.mkdir(exist_ok=True)
    banner = "<!-- gerado por scripts/build-stats.py - nao editar a mao -->\n"
    (OUT / "stats-pt.html").write_text(banner + render(valores, "pt"), encoding="utf-8")
    (OUT / "stats-en.html").write_text(banner + render(valores, "en"), encoding="utf-8")
    print("stats: " + ", ".join(f"{k}={v}" for k, v in valores.items())
          + " -> _includes/stats-*.html")


if __name__ == "__main__":
    main()
