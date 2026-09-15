#!/usr/bin/env bash
# Build completo do site BioVirLab -> docs/
#
#   ./build.sh
#
# Etapas:
#   1. gera membros, eventos e publicacoes a partir de _data/ e eventos/
#   2. renderiza a versao pt-BR na raiz de docs/
#   3. renderiza a versao em ingles (perfil "en") e copia para docs/en/
#
# Requisitos: quarto (>= 1.4) e python3.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> gerando listas de membros"
python3 scripts/build-members.py

echo "==> gerando paginas de eventos"
python3 scripts/build-eventos.py

# le somente o cache _data/publicacoes.json: nao acessa a internet.
# para buscar publicacoes novas, rode antes:
#   python3 scripts/build-publicacoes.py --atualizar
echo "==> gerando lista de publicacoes"
python3 scripts/build-publicacoes.py

echo "==> renderizando pt-BR -> docs/"
quarto render

echo "==> renderizando en -> docs/en/"
quarto render --profile en
rm -rf docs/en
cp -R _build-en/en docs/en
rm -rf _build-en

touch docs/.nojekyll

echo "==> pronto: docs/index.html e docs/en/index.html"
