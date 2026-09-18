#!/usr/bin/env python3
"""Gera os blocos HTML da pagina de Membros a partir de _data/members.tsv.

Saidas:
  _includes/members-pt.html  (usado por membros.qmd)
  _includes/members-en.html  (usado por en/members.qmd)

Para adicionar/remover membros edite apenas _data/members.tsv e rode ./build.sh.
"""

import csv
import html
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "_data" / "members.tsv"
OUT = ROOT / "_includes"

# ordem de exibicao dos grupos e rotulo padrao de cada um
GROUPS = [
    ("professor", "Coordenação", "Principal Investigator"),
    ("researcher", "Pesquisa", "Researchers"),
    ("postdoc", "Pós-doutorado", "Postdoctoral Researchers"),
    ("phd", "Doutorado", "PhD Students"),
    ("master", "Mestrado", "MSc Students"),
    ("undergraduate", "Iniciação Científica", "Undergraduate Students"),
    ("alumni", "Alumni", "Alumni"),
]

# contagem que aparece a direita no bloco azul de cada grupo
CONTA = {
    "pt": ("1 pessoa", "{n} pessoas"),
    "en": ("1 person", "{n} people"),
}

# rotulo individual padrao (aparece embaixo do nome de cada pessoa)
ROLES = {
    "professor": ("Professor / Coordenador", "Principal Investigator"),
    "researcher": ("Pesquisador(a)", "Researcher"),
    "postdoc": ("Pós-doutorando(a)", "Postdoctoral Researcher"),
    "phd": ("Doutorando(a)", "PhD Student"),
    "master": ("Mestrando(a)", "MSc Student"),
    "undergraduate": ("Graduando(a)", "Undergraduate Student"),
    "alumni": ("Ex-integrante", "Former member"),
}


def read_members():
    with DATA.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    members = []
    for row in rows:
        row = {k: (v or "").strip() for k, v in row.items() if k}
        if not row.get("name"):
            continue
        if row["group"] not in ROLES:
            sys.exit(f"grupo desconhecido em members.tsv: {row['group']!r}")
        if row.get("photo") and not (ROOT / row["photo"]).exists():
            print(f"  aviso: foto de {row['name']} nao existe: {row['photo']}")
        members.append(row)
    return members


def card(member, lang, prefix):
    """Uma linha por card: markdown trata linhas indentadas como bloco de codigo."""
    name = html.escape(member["name"])
    role = member["role_pt"] if lang == "pt" else member["role_en"]
    if not role:
        role = ROLES[member["group"]][0 if lang == "pt" else 1]
    role = html.escape(role)
    photo = prefix + member["photo"]
    inner = (
        f'<img class="member-photo" src="{photo}" alt="{name}" loading="lazy" />'
        f'<p class="member-name">{name}</p>'
        f'<p class="member-role">{role}</p>'
    )
    if member.get("link"):
        link = html.escape(member["link"])
        inner = (
            f'<a class="member-link" href="{link}" target="_blank" rel="noopener">'
            f"{inner}</a>"
        )
    return f'<figure class="member-card">{inner}</figure>'


def render(members, lang, prefix):
    out = []
    for key, label_pt, label_en in GROUPS:
        group = [m for m in members if m["group"] == key]
        if not group:
            continue
        group.sort(key=lambda m: m["name"].casefold())
        label = html.escape(label_pt if lang == "pt" else label_en)
        n = len(group)
        conta = (CONTA[lang][0] if n == 1 else CONTA[lang][1].format(n=n))
        out.append(f'<h2 class="member-group-title">'
                   f'<span class="member-group-rotulo">{label}</span>'
                   f'<span class="member-group-conta">{conta}</span></h2>')
        out.append('<div class="member-grid">')
        out.extend(card(m, lang, prefix) for m in group)
        out.append("</div>")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    members = read_members()
    OUT.mkdir(exist_ok=True)
    banner = "<!-- gerado por scripts/build-members.py a partir de _data/members.tsv - nao editar a mao -->\n"
    (OUT / "members-pt.html").write_text(banner + render(members, "pt", ""), encoding="utf-8")
    (OUT / "members-en.html").write_text(banner + render(members, "en", "../"), encoding="utf-8")
    print(f"members: {len(members)} integrantes -> _includes/members-pt.html, _includes/members-en.html")


if __name__ == "__main__":
    main()
