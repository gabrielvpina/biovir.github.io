#!/usr/bin/env bash
# Build completo do site BioVirLab -> docs/
#
#   ./build.sh
#
# Etapas:
#   1. gera as listas de membros a partir de _data/members.tsv
#   2. renderiza a versao pt-BR na raiz de docs/
#   3. renderiza a versao em ingles (perfil "en") e copia para docs/en/
#
# Requisitos: quarto (>= 1.4) e python3.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> gerando listas de membros"
python3 scripts/build-members.py

echo "==> renderizando pt-BR -> docs/"
quarto render

echo "==> renderizando en -> docs/en/"
quarto render --profile en
rm -rf docs/en
cp -R _build-en/en docs/en
rm -rf _build-en

touch docs/.nojekyll

echo "==> pronto: docs/index.html e docs/en/index.html"
