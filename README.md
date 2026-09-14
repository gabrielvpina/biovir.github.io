# biovir.github.io

Site oficial do **BioVirLab** — Laboratório de Bioinformática e Virologia.

Construído com [Quarto](https://quarto.org/docs/websites/). Todo o conteúdo é
escrito em arquivos `.qmd` e o HTML gerado vai para `docs/`, que é a pasta
publicada pelo GitHub Pages.

## Como gerar o site

```bash
./build.sh
```

O script faz três coisas:

1. gera as listas de membros a partir de `_data/members.tsv`;
2. renderiza a versão **pt-BR** na raiz de `docs/`;
3. renderiza a versão **en** e copia para `docs/en/`.

Requisitos: `quarto` (≥ 1.4) e `python3`.

Para visualizar enquanto edita (apenas pt-BR, com recarga automática):

```bash
quarto preview
```

## Estrutura

```
index.qmd                 Início            ->  docs/index.html
linhas-de-pesquisa.qmd    Linhas de Pesquisa
publicacoes.qmd           Publicações
eventos.qmd               Eventos
membros.qmd               Membros

en/index.qmd              Home              ->  docs/en/index.html
en/research.qmd           Research
en/publications.qmd       Publications
en/events.qmd             Events
en/members.qmd            Members

_quarto.yml               configuração comum aos dois idiomas
_quarto-pt.yml            perfil pt-BR (menu, rodapé, lista de páginas)
_quarto-en.yml            perfil en
_data/members.tsv         lista de membros (fonte única das duas línguas)
scripts/build-members.py  gera _includes/members-*.html a partir do TSV
styles/biovir.scss        tema visual (cores, tipografia, componentes)
styles/fonts.css          @font-face das fontes locais em fonts/
js/lang-switch.html       mantém a página ao trocar de idioma
assets/                   logotipos
members/                  fotos dos integrantes
docs/                     saída gerada — não editar à mão
```

## Editar os membros

Edite **apenas** `_data/members.tsv` e rode `./build.sh`. Colunas:

| coluna | descrição |
| --- | --- |
| `group` | `professor`, `researcher`, `postdoc`, `phd`, `master`, `undergraduate` ou `alumni` |
| `name` | nome completo |
| `photo` | caminho da foto a partir da raiz do repositório |
| `role_pt` | cargo em português (vazio = rótulo padrão do grupo) |
| `role_en` | cargo em inglês (vazio = rótulo padrão do grupo) |
| `link` | link opcional (Lattes, ORCID…) aplicado ao card |

Os campos são separados por **tabulação**. As fotos são exibidas em formato
circular (recorte automático), então imagens quadradas funcionam melhor.

## Adicionar uma página nova

1. crie `nova-pagina.qmd` e `en/new-page.qmd`;
2. registre `nova-pagina.qmd` em `_quarto-pt.yml` (`project.render` e `navbar`)
   e a versão em inglês em `_quarto-en.yml`;
3. adicione o par `["nova-pagina.html", "new-page.html"]` em
   `js/lang-switch.html` para que o seletor de idioma funcione na página.

## Publicação no GitHub Pages

Em *Settings → Pages*, selecione **Deploy from a branch**, branch `main` e
pasta `/docs`. Basta commitar `docs/` junto com as fontes.
