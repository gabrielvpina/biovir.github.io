#!/usr/bin/env python3
"""Gera a vitrine de logos das instituicoes colaboradoras (Linhas de Pesquisa).

Toda imagem colocada em assets/colaboradores/ entra automaticamente na secao
"Instituicoes colaboradoras" no proximo ./build.sh. Nao ha lista para editar.

  - formatos aceitos: .png .jpg .jpeg .svg .webp .gif
  - o nome exibido (texto alternativo e dica ao passar o mouse) vem do nome do
    arquivo, trocando - e _ por espaco e mantendo as maiusculas do arquivo:
    "Fiocruz-Bahia.png" -> "Fiocruz Bahia", "UFBA.svg" -> "UFBA"
  - a ordem e' alfabetica pelo nome do arquivo; para forcar uma ordem, comece o
    nome com um numero: "01-ufba.png", "02-fiocruz.svg" (o numero nao aparece)
  - arquivos que comecam com "_" ou "." sao ignorados (ex.: "_rascunho.png")

Saidas:
  _includes/colaboradores-pt.html  (usado por linhas-de-pesquisa.qmd)
  _includes/colaboradores-en.html  (usado por en/research.qmd)
"""

import html
import pathlib
import re
import unicodedata
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
PASTA = "assets/colaboradores"
DIR = ROOT / PASTA
OUT = ROOT / "_includes"

EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}

# acima disso a imagem pesa no carregamento da pagina sem ganho visual: as
# logos aparecem pequenas. Vale reduzir antes de colocar na pasta.
LIMITE_KB = 400

# texto quando a pasta esta vazia
VAZIO = {
    "pt": "Mantemos parcerias com grupos de pesquisa de instituições nacionais e "
          "internacionais. Esta seção será detalhada em breve.",
    "en": "We maintain partnerships with research groups at institutions in "
          "Brazil and abroad. This section will be detailed soon.",
}

ROTULO = {"pt": "Instituições colaboradoras", "en": "Collaborating institutions"}


def nome_legivel(arquivo):
    base = re.sub(r"^\d+[-_ .]*", "", arquivo.stem)  # tira o numero de ordem
    base = re.sub(r"[-_]+", " ", base).strip()
    return base[:1].upper() + base[1:] if base else arquivo.stem


def ler_logos():
    if not DIR.is_dir():
        return []
    logos = []
    for arq in sorted(DIR.iterdir(), key=lambda p: p.name.lower()):
        if not arq.is_file() or arq.name.startswith(("_", ".")):
            continue
        if arq.suffix.lower() not in EXTS:
            print(f"  aviso: ignorado (formato nao suportado): {arq.name}")
            continue
        kb = arq.stat().st_size / 1024
        if kb > LIMITE_KB:
            print(f"  aviso: {arq.name} tem {kb:.0f} KB; considere reduzir a imagem")
        logos.append(arq)
    return logos


def render(logos, lang, prefix):
    if not logos:
        return f"<p>{html.escape(VAZIO[lang])}</p>\n"
    linhas = [f'<ul class="partner-logos" aria-label="{ROTULO[lang]}">']
    for arq in logos:
        # o macOS entrega nomes com acento decompostos (NFD: "c" + cedilha),
        # mas o git grava composto (NFC). O GitHub Pages compara o caminho
        # byte a byte, entao o link precisa estar em NFC ou a logo some.
        arquivo = unicodedata.normalize("NFC", arq.name)
        nome = html.escape(unicodedata.normalize("NFC", nome_legivel(arq)))
        src = html.escape(prefix + urllib.parse.quote(f"{PASTA}/{arquivo}"))
        # uma linha por item: markdown trata linhas indentadas como codigo
        linhas.append(
            f'<li class="partner-logo" title="{nome}">'
            f'<img src="{src}" alt="{nome}" loading="lazy"></li>'
        )
    linhas.append("</ul>")
    return "\n".join(linhas) + "\n"


def main():
    logos = ler_logos()
    OUT.mkdir(exist_ok=True)
    for lang, prefix in (("pt", ""), ("en", "../")):
        destino = OUT / f"colaboradores-{lang}.html"
        destino.write_text(render(logos, lang, prefix), encoding="utf-8")
    print(f"  {len(logos)} logo(s) em {PASTA}/")


if __name__ == "__main__":
    main()
