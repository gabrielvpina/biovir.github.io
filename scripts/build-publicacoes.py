#!/usr/bin/env python3
"""Gera as paginas de Publicacoes a partir do perfil do coordenador no OpenAlex.

Uso:

    python3 scripts/build-publicacoes.py              # regenera o HTML do cache
    python3 scripts/build-publicacoes.py --atualizar  # busca na internet e regenera

O ./build.sh roda a versao SEM --atualizar: ela le somente o cache em
_data/publicacoes.json, entao o site continua compilando sem conexao. Rode com
--atualizar quando sair publicacao nova; o cache atualizado deve ser commitado.

Saidas:
    _data/publicacoes.json         cache dos dados (so muda com --atualizar)
    _data/estatisticas.json        numeros para a faixa da pagina inicial
    _includes/publicacoes-pt.html  usado por publicacoes.qmd
    _includes/publicacoes-en.html  usado por en/publications.qmd

Integrantes do laboratorio sao reconhecidos a partir de _data/members.tsv e
aparecem em negrito; os demais autores entram na contagem de "Colaboracoes".
"""

import argparse
import csv
import html
import json
import pathlib
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "_data" / "publicacoes.json"
ESTATS = ROOT / "_data" / "estatisticas.json"
MEMBROS = ROOT / "_data" / "members.tsv"
OUT = ROOT / "_includes"

# --------------------------------------------------------------- ajustes ---
# Perfil do coordenador no OpenAlex (https://openalex.org/A5031219064)
AUTOR_OPENALEX = "A5031219064"

# So entram publicacoes deste ano em diante
ANO_INICIAL = 2023

# Quantos autores aparecem antes do "et al."
MAX_AUTORES = 6

# Registros a ignorar, com o motivo. O OpenAlex indexa coisas que nao sao
# artigos do laboratorio (pareceres, redeposito de artigo antigo etc.).
EXCLUIR = {
    "10.17615/tdnb-6w70":
        "redeposito em repositorio do artigo de 2021 (Sisal Virome)",
    "10.21203/rs.3.rs-4868315/v1":
        "pre-print da versao publicada em 10.3389/fmicb.2025.1570606 "
        "(mesmos 16 autores, mesma ordem, titulo mudou de Spiroplasma para Wolbachia)",
    "10.29327/1331270.2-4":
        "resumo de congresso, nao artigo - apague esta linha para lista-lo",
}

# DOIs que o filtro por data nao alcanca mas devem entrar (ex.: artigo com
# publicacao online no ano anterior e edicao impressa dentro do periodo).
INCLUIR_EXTRA = [
    "10.1007/s10142-022-00932-x",   # Functional & Integrative Genomics 23(1), mar/2023
]

# Correcoes pontuais de metadados do OpenAlex: doi -> {campo: valor}
AJUSTES = {
    # edicao impressa e de mar/2023 (vol 23, n. 1); o OpenAlex marca o online de 2022
    "10.1007/s10142-022-00932-x": {"ano": 2023, "venue": "Functional & Integrative Genomics"},
    "10.64898/2026.02.25.26346099": {"venue": "medRxiv"},
    "10.64898/2026.05.19.26353615": {"venue": "medRxiv"},
    "10.22541/au.174113476.64158351/v1": {"venue": "Authorea"},
}

# Tipos do OpenAlex que nunca viram publicacao na pagina
TIPOS_IGNORADOS = {"peer-review", "grant", "retraction", "erratum", "paratext"}

# Prefixos de DOI que identificam pre-print (vao para a secao separada)
PREFIXOS_PREPRINT = ("10.1101/", "10.21203/", "10.22541/", "10.64898/",
                     "10.20944/", "10.2139/", "10.31219/", "10.31234/")

UA = {"User-Agent": "biovir.github.io (mailto:contato@biovirlab.com)"}

# nomes de servidores de pre-print como o OpenAlex devolve -> como exibir
VENUES = {
    "bioRxiv (Cold Spring Harbor Laboratory)": "bioRxiv",
    "medRxiv (Cold Spring Harbor Laboratory)": "medRxiv",
    "Research Square (Research Square)": "Research Square",
    "SSRN Electronic Journal": "SSRN",
}

TXT = {
    "pt": {
        "preprints": "Pré-prints",
        "conta_uma": "1 publicação",
        "conta_varias": "{n} publicações",
        "colab": "Colaborações",
        "incl": "inclui",
        "vazio": "Nenhuma publicação no cache. Rode "
                 "<code>python3 scripts/build-publicacoes.py --atualizar</code>.",
        "resumo": ("As {tot} publicações acima reúnem <strong>{ext} pesquisadores "
                   "externos ao laboratório</strong>, de instituições do Brasil e do "
                   "exterior."),
    },
    "en": {
        "preprints": "Preprints",
        "conta_uma": "1 publication",
        "conta_varias": "{n} publications",
        "colab": "Collaborations",
        "incl": "incl.",
        "vazio": "No publications cached. Run "
                 "<code>python3 scripts/build-publicacoes.py --atualizar</code>.",
        "resumo": ("The {tot} publications above bring together <strong>{ext} "
                   "researchers from outside the laboratory</strong>, at institutions "
                   "in Brazil and abroad."),
    },
}

# --------------------------------------------------------------- nomes -----

PARTICULAS = {"de", "da", "do", "dos", "das", "del", "van", "den", "der",
              "e", "y", "la", "le"}
SUFIXOS = {"junior", "jr", "filho", "neto", "sobrinho"}


def sem_acento(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def tokens(nome):
    s = re.sub(r"[^a-z ]", " ", sem_acento(nome).lower())
    return [t for t in s.split() if t and t not in PARTICULAS]


def tira_sufixo(t):
    if len(t) > 1 and t[-1] in SUFIXOS:
        return t[:-1]
    return t


def compativel(a, b):
    """Nomes do meio compativeis: um pode ser a abreviacao do outro."""
    i = j = 0
    while i < len(a) and j < len(b):
        x, y = a[i], b[j]
        if x == y or (len(x) == 1 and y.startswith(x)) or (len(y) == 1 and x.startswith(y)):
            i += 1
            j += 1
        else:
            return False
    return True


def mesma_pessoa(a, b):
    """a e b sao listas de tokens ja sem particulas nem sufixo."""
    if not a or not b or a[-1] != b[-1]:
        return False
    x, y = a[0], b[0]
    if not (x == y or (len(x) == 1 and y.startswith(x)) or (len(y) == 1 and x.startswith(y))):
        return False
    return compativel(a[1:-1], b[1:-1])


def carrega_membros():
    """[{'nome': 'Nome como esta no TSV', 't': [tokens]}, ...]"""
    membros = []
    with MEMBROS.open(encoding="utf-8") as fh:
        for linha in csv.DictReader(fh, delimiter="\t"):
            nome = (linha.get("name") or "").strip()
            if nome:
                membros.append({"nome": nome, "t": tira_sufixo(tokens(nome))})
    return membros


def membro_de(nome, membros):
    """Devolve o integrante correspondente a este nome de autor, ou None."""
    t = tira_sufixo(tokens(nome))
    if not t:
        return None
    for m in membros:
        if mesma_pessoa(t, m["t"]):
            return m
    return None


def vancouver(nome):
    """'Lucas Yago Melo Ferreira' -> 'Ferreira LYM'"""
    partes = [p for p in re.split(r"\s+", nome.strip()) if p]
    if not partes:
        return nome
    sufixo = ""
    t = tokens(partes[-1])
    if len(partes) > 1 and t and t[0] in SUFIXOS:
        sufixo = " " + partes[-1].title()
        partes = partes[:-1]
    familia = partes[-1]
    if familia.isupper():
        familia = familia.title()
    iniciais = "".join(p[0].upper() for p in partes[:-1]
                       if sem_acento(p).lower() not in PARTICULAS)
    return f"{familia} {iniciais}".strip() + sufixo


# --------------------------------------------------------------- coleta ----

def busca_openalex():
    works, cursor = [], "*"
    while cursor:
        url = ("https://api.openalex.org/works"
               f"?filter=author.id:{AUTOR_OPENALEX},"
               f"from_publication_date:{ANO_INICIAL}-01-01"
               f"&per-page=200&cursor={urllib.parse.quote(cursor)}")
        req = urllib.request.Request(url, headers=UA)
        try:
            dados = json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as erro:
            sys.exit(f"falha ao consultar o OpenAlex: {erro}")
        works += dados["results"]
        if not dados["results"]:
            break
        cursor = dados["meta"].get("next_cursor")

    for doi in INCLUIR_EXTRA:
        if any((w.get("doi") or "").endswith(doi) for w in works):
            continue
        req = urllib.request.Request(f"https://api.openalex.org/works/doi:{doi}",
                                     headers=UA)
        try:
            works.append(json.load(urllib.request.urlopen(req, timeout=60)))
        except Exception as erro:
            print(f"  aviso: nao consegui buscar {doi}: {erro}")
    return works


def chave_titulo(t):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", sem_acento(t or "").lower()).split())


def e_preprint(doi, tipo):
    return doi.startswith(PREFIXOS_PREPRINT) or tipo == "preprint"


def normaliza(works):
    """Converte a resposta do OpenAlex no formato do cache, ja sem duplicatas."""
    pubs = []
    for w in works:
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        if not doi or doi in EXCLUIR:
            continue
        if w.get("type") in TIPOS_IGNORADOS:
            continue
        if w["publication_year"] < ANO_INICIAL and doi not in AJUSTES:
            continue
        fonte = ((w.get("primary_location") or {}).get("source") or {})
        pub = {
            "doi": doi,
            "titulo": re.sub(r"\s+", " ", w["display_name"] or "").strip(),
            "ano": w["publication_year"],
            "venue": VENUES.get(fonte.get("display_name") or "",
                                fonte.get("display_name") or ""),
            "tipo": w.get("type") or "article",
            "autores": [a["author"]["display_name"] for a in w.get("authorships", [])],
        }
        pub.update({k: v for k, v in AJUSTES.get(doi, {}).items()})
        pubs.append(pub)

    # duplicatas (pre-print + versao publicada): fica a versao publicada
    escolhidos = {}
    for p in sorted(pubs, key=lambda p: (e_preprint(p["doi"], p["tipo"]), -p["ano"])):
        k = chave_titulo(p["titulo"])
        if k not in escolhidos:
            escolhidos[k] = p
    pubs = [p for p in escolhidos.values() if p["ano"] >= ANO_INICIAL]
    pubs.sort(key=lambda p: (-p["ano"], chave_titulo(p["titulo"])))
    return pubs


# ------------------------------------------------------------ montagem -----

def separa_autores(pubs, membros):
    """Devolve (colaboradores externos ordenados, set de integrantes que assinam).

    Os integrantes sao contados pelo nome em members.tsv, e nao pela grafia que
    aparece no artigo: "J dos Santos Silva" e "Jonatha dos Santos Silva" sao a
    mesma pessoa e contam uma vez so.
    """
    grupos, internos = [], set()
    for p in pubs:
        for nome in p["autores"]:
            t = tira_sufixo(tokens(nome))
            if not t:
                continue
            m = membro_de(nome, membros)
            if m:
                internos.add(m["nome"])
                continue
            for g in grupos:
                if mesma_pessoa(t, g["t"]):
                    if len(t) > len(g["t"]):
                        g["t"] = t
                    g["nomes"].add(nome)
                    break
            else:
                grupos.append({"t": t, "nomes": {nome}})

    def exibicao(g):
        # entre as variantes, a mais completa; evita versoes em CAIXA ALTA
        return sorted(g["nomes"], key=lambda n: (n.isupper(), -len(n), n))[0]

    externos = sorted((exibicao(g) for g in grupos),
                      key=lambda n: sem_acento(n).split()[-1].lower())
    return externos, internos


def e_membro(nome, membros):
    return membro_de(nome, membros) is not None


def autores_html(autores, membros, lang):
    mostrados = autores[:MAX_AUTORES]
    partes = []
    for a in mostrados:
        v = html.escape(vancouver(a))
        partes.append(f"<strong>{v}</strong>" if e_membro(a, membros) else v)
    texto = ", ".join(partes)
    if len(autores) > MAX_AUTORES:
        texto += ", <em>et al.</em>"
        extras = [a for a in autores[MAX_AUTORES:] if e_membro(a, membros)]
        if extras:
            nomes = ", ".join(f"<strong>{html.escape(vancouver(a))}</strong>" for a in extras)
            texto += f" ({TXT[lang]['incl']} {nomes})"
    return texto


def item(p, membros, lang):
    titulo = html.escape(p["titulo"])
    venue = html.escape(p["venue"] or "—")
    return ('  <li>\n'
            f'    <span class="pub-title">{titulo}.</span>\n'
            f'    {autores_html(p["autores"], membros, lang)}.\n'
            f'    <span class="pub-venue">{venue}</span>, {p["ano"]}.\n'
            f'    <a class="pub-doi" href="https://doi.org/{p["doi"]}">doi:{p["doi"]}</a>\n'
            '  </li>')


def render(pubs, membros, lang):
    t = TXT[lang]
    if not pubs:
        return f"<p>{t['vazio']}</p>\n"

    artigos = [p for p in pubs if not e_preprint(p["doi"], p["tipo"])]
    preprints = [p for p in pubs if e_preprint(p["doi"], p["tipo"])]
    externos, _ = separa_autores(pubs, membros)

    def gaveta(rotulo, itens, aberta):
        """Uma gaveta <details> com o titulo em bloco azul e a lista dentro."""
        conta = (t["conta_uma"] if len(itens) == 1
                 else t["conta_varias"].format(n=len(itens)))
        return "\n".join([
            f'<details class="pub-gaveta"{" open" if aberta else ""}>',
            '<summary class="pub-gaveta-cab">'
            f'<span class="pub-gaveta-rotulo">{html.escape(str(rotulo))}</span>'
            f'<span class="pub-gaveta-conta">{html.escape(conta)}</span>'
            '</summary>',
            '<ul class="pub-list">',
            *[item(p, membros, lang) for p in itens],
            "</ul>",
            "</details>\n",
        ])

    out = []
    # so o ano mais recente comeca aberto: a pagina abre mostrando conteudo,
    # sem despejar as 48 publicacoes de uma vez
    anos = sorted({p["ano"] for p in artigos}, reverse=True)
    for i, ano in enumerate(anos):
        out.append(gaveta(ano, [p for p in artigos if p["ano"] == ano], i == 0))

    if preprints:
        out.append(gaveta(t["preprints"], preprints, False))

    out.append(f"## {t['colab']}\n")
    out.append('::: {.lead}')
    out.append(t["resumo"].format(tot=len(pubs), ext=len(externos)))
    out.append(':::')
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atualizar", action="store_true",
                    help="consulta o OpenAlex e reescreve _data/publicacoes.json")
    args = ap.parse_args()

    if args.atualizar:
        works = busca_openalex()
        pubs = normaliza(works)
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(pubs, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
        print(f"publicacoes: {len(works)} registros no OpenAlex -> "
              f"{len(pubs)} publicacoes em {CACHE.relative_to(ROOT)}")
    elif not CACHE.exists():
        sys.exit(f"{CACHE.relative_to(ROOT)} nao existe. "
                 "Rode uma vez com --atualizar.")

    pubs = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else []
    membros = carrega_membros()
    externos, internos = separa_autores(pubs, membros)

    banner = ("<!-- gerado por scripts/build-publicacoes.py a partir de "
              "_data/publicacoes.json - nao editar a mao -->\n")
    OUT.mkdir(exist_ok=True)
    for lang, arq in (("pt", "publicacoes-pt.html"), ("en", "publicacoes-en.html")):
        (OUT / arq).write_text(banner + render(pubs, membros, lang), encoding="utf-8")

    # numeros usados pela faixa de estatisticas da pagina inicial
    ESTATS.write_text(json.dumps({
        "publicacoes": len(pubs),
        "colaboradores": len(externos),
        "integrantes_que_assinam": len(internos),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    preprints = sum(1 for p in pubs if e_preprint(p["doi"], p["tipo"]))
    print(f"publicacoes: {len(pubs)} ({len(pubs) - preprints} artigos, "
          f"{preprints} pre-prints), {len(internos)} integrantes, "
          f"{len(externos)} colaboradores -> _includes/publicacoes-*.html")


if __name__ == "__main__":
    main()
