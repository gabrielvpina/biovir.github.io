# biovir.github.io

Site oficial do **BioVirLab** — Laboratório de Bioinformática e Virologia.

Construído com [Quarto](https://quarto.org/docs/websites/). Todo o conteúdo é
escrito em arquivos `.qmd` e o HTML gerado vai para `docs/`, que é a pasta
publicada pelo GitHub Pages.

## Como gerar o site

```bash
./build.sh
```

O script faz sete coisas:

1. gera as listas de membros a partir de `_data/members.tsv`;
2. gera as páginas de eventos a partir das pastas em `eventos/`;
3. gera a lista de publicações a partir de `_data/publicacoes.json`;
4. gera o mapa dos campi a partir de `_data/locais.tsv`;
5. gera a faixa de números da página inicial;
6. renderiza a versão **pt-BR** na raiz de `docs/`;
7. renderiza a versão **en** e copia para `docs/en/`.

O passo 3 lê apenas o cache local — **o build não acessa a internet**.

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
eventos.qmd               Eventos e notícias
membros.qmd               Membros

en/index.qmd              Home              ->  docs/en/index.html
en/research.qmd           Research
en/publications.qmd       Publications
en/events.qmd             Events & news
en/members.qmd            Members

_quarto.yml               configuração comum aos dois idiomas
_quarto-pt.yml            perfil pt-BR (menu, rodapé, lista de páginas)
_quarto-en.yml            perfil en
_data/members.tsv         lista de membros (fonte única das duas línguas)
_data/publicacoes.json    cache das publicações vindas do OpenAlex
_data/locais.tsv          endereços e coordenadas do mapa da página inicial
_data/estatisticas.json   números da faixa da página inicial (gerado)
eventos/<slug>/           um evento por pasta (texto, capa e fotos)
scripts/build-members.py  gera _includes/members-*.html a partir do TSV
scripts/build-eventos.py  gera as páginas de eventos a partir de eventos/
scripts/build-publicacoes.py  gera _includes/publicacoes-*.html
scripts/build-mapa.py     desenha o mapa dos campi (SVG) a partir de _data/
scripts/baixar-mapa-osm.py  baixa a geografia do mapa do OpenStreetMap (raro)
scripts/build-stats.py    gera a faixa de números da página inicial
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
| `link` | link opcional (Lattes, ORCID…). Com ele, o card inteiro vira link e o nome sublinha ao passar o mouse. Sem ele, o card fica estático |

Os campos são separados por **tabulação**. As fotos são exibidas em formato
circular (recorte automático), então imagens quadradas funcionam melhor.

As fotos ficam em **WebP**, com o menor lado em 400 px (o site as mostra com
120 px, então isso cobre telas retina com folga). Para uma foto nova, converta
antes de commitar e aponte o `photo` do TSV para o `.webp`:

```bash
magick foto-original.png -auto-orient -resize '400x400^>' -strip -quality 82 members/phd/nome.webp
```

Os originais em PNG/JPEG da conversão ficam em `members_backup/`, que está no
`.gitignore` (não vai para o repositório). Só `.webp` dentro de `members/` é
publicado — veja `resources` em `_quarto.yml`.

O título de cada grupo é um bloco azul com a contagem de pessoas à direita — o
mesmo bloco das gavetas de Publicações, definido uma vez só no SCSS
(`%bloco-azul`). Mudar a cor ou o espaçamento lá vale para as duas páginas.

## Atualizar as publicações

A página de Publicações é montada a partir do perfil do coordenador no
[OpenAlex](https://openalex.org/A5031219064), que é a mesma base do Google
Scholar porém consultável por API e com a lista completa de autores (o Scholar
corta em "et al."). Entram as publicações de **2023 em diante**.

Quando sair publicação nova:

```bash
python3 scripts/build-publicacoes.py --atualizar
./build.sh
```

O `--atualizar` é a única etapa que acessa a internet. Ele reescreve o cache
`_data/publicacoes.json`, que deve ser **commitado** junto — assim o
`./build.sh` continua funcionando offline e o site não muda sozinho quando a
base externa muda.

### O que a página mostra

- artigos agrupados por ano, cada ano numa **gaveta retrátil** (bloco azul com
  seta) que abre ao ser clicada — só o ano mais recente começa aberto; para
  mudar isso, veja `i == 0` na função `render` de `scripts/build-publicacoes.py`;
- pré-prints na última gaveta (bioRxiv, medRxiv, Research Square, SSRN,
  Authorea são reconhecidos pelo prefixo do DOI);
- **Colaborações**: o total de publicações e quantos autores externos ao
  laboratório elas reúnem.

Integrantes aparecem em **negrito**, reconhecidos por cruzamento com
`_data/members.tsv`. Por isso, manter o TSV em dia melhora a página de
Publicações também. A comparação tolera abreviações (`J dos Santos Silva`
casa com `Jonatha dos Santos Silva`) e sufixos (`Junior`, `Neto`, `Filho`).

As gavetas usam `<details>`/`<summary>` nativos do HTML: abrem sem JavaScript,
funcionam com teclado e, ao imprimir a página, todas aparecem abertas.

Listas longas são cortadas nos 6 primeiros autores com `et al.`, mas
integrantes que ficariam de fora do corte são acrescentados entre parênteses,
para não sumirem da própria página.

### Ajustes manuais

Bases automáticas indexam coisas que não são artigos do laboratório. Os quatro
pontos de ajuste ficam no topo de `scripts/build-publicacoes.py`:

| constante | para quê |
| --- | --- |
| `ANO_INICIAL` | ano de corte (hoje `2023`) |
| `EXCLUIR` | DOIs a ignorar, cada um com o motivo escrito ao lado |
| `INCLUIR_EXTRA` | DOIs que o filtro por data não alcança (artigo publicado online num ano e impresso no seguinte) |
| `AJUSTES` | correções de ano ou de periódico em um DOI específico |

O script também remove sozinho os pares pré-print + versão publicada quando os
títulos coincidem. Quando o título muda entre as duas versões, a duplicata
precisa ir no `EXCLUIR` à mão — há um exemplo comentado lá.

### A faixa de números da página inicial

Os quatro números da home (Integrantes, Linhas de pesquisa, Publicações,
Colaborações) são gerados por `scripts/build-stats.py` e cada um vem de um
arquivo do próprio repositório:

| número | origem |
| --- | --- |
| Integrantes | linhas de `_data/members.tsv` |
| Linhas de pesquisa | blocos `.research-line` em `linhas-de-pesquisa.qmd` |
| Publicações | `_data/estatisticas.json` |
| Colaborações | `_data/estatisticas.json` |

`_data/estatisticas.json` é escrito por `build-publicacoes.py`, por isso o
`./build.sh` roda os dois nessa ordem. Nenhum dos números precisa ser editado à
mão — eles acompanham os dados. Cada um é um link para a página correspondente.

## Prêmios e distinções

Ficam no fim de `publicacoes.qmd` (e `en/publications.qmd`), escritos em
Markdown puro — sem HTML — e exibidos como uma árvore por ano. Cada ano é um
bloco `.premios-ano` e cada prêmio dentro dele é um bloco `.premio`; para
adicionar um, copie um bloco existente:

```markdown
:::: {.premios-ano ano="2025"}

::: {.premio}
**Melhor Pôster**

Categoria Graduação · Virologia de Plantas e Invertebrados · “Título do trabalho”

- Henrique Andrade Rabelo Bomfim
- Lucas Yago Melo Ferreira
- Gabriel Victor Pina Rodrigues

36º Congresso Brasileiro de Virologia (SBV)
:::

::::
```

| parte | o que é |
| --- | --- |
| `ano="..."` (no bloco do ano) | selo azul na raiz da árvore |
| 1º parágrafo, em **negrito** | título do prêmio |
| parágrafos do meio | detalhe opcional (categoria, área, título do trabalho) |
| lista `- Nome` | membros do lab autores do trabalho, na ordem de autoria, sem o orientador |
| último parágrafo | evento ou instituição |

A medalha, o tronco e os galhos da árvore, o selo do ano e as etiquetas dos
nomes vêm do CSS (`.premios` em `styles/biovir.scss`). Mantenha os anos do
mais recente para o mais antigo.

## Mudar os pontos do mapa

O mapa da seção "Onde estamos" é um **SVG desenhado pelo próprio site**
(`scripts/build-mapa.py`): mar, rios, matas com árvores, áreas urbanas,
rodovias, os nomes das cidades e dos rios, e um pino com ícone de
universidade para cada campus, ligado a um cartão com a foto. Quem visita o
site não carrega biblioteca de mapa nem busca nada em serviço externo.

A geografia vem do OpenStreetMap (`_data/mapa-osm.json`) e, para a
miniatura do Brasil com a Bahia destacada, do Natural Earth
(`_data/mapa-brasil.json`). Os dois já estão guardados no repositório — o build
não acessa a internet.

Os campi saem de `_data/locais.tsv`, um por linha:

| coluna | descrição |
| --- | --- |
| `nome` | nome da instituição; a sigla entre parênteses vai para o cartão do mapa |
| `endereco_pt` | endereço completo em português |
| `endereco_en` | endereço em inglês (vazio = usa o português) |
| `lat` / `lon` | coordenadas em graus decimais, com **ponto** |
| `foto` | foto do campus, a partir da raiz (ex.: `assets/campi/uesc.webp`) |

Campos separados por **tabulação**, como em `members.tsv`. Depois de mudar,
basta rodar `./build.sh`.

### Ajustar a aparência do mapa

As constantes ficam no topo de `scripts/build-mapa.py`:

| constante | para quê |
| --- | --- |
| `COR` | paleta: mar, mata, rios, cidades, pinos |
| `CIDADES` | nomes de cidade escritos no mapa e onde |
| `ROTULOS_RIOS` | quais rios recebem nome; a posição (0–1) indica em que parte do rio o nome deve ficar — o script procura o trecho mais reto por perto |
| `CARTOES` | onde fica o cartão com foto de cada campus, em relação ao pino (pela sigla) |
| `MINI_L` / `MINI_A` | tamanho da miniatura do Brasil no canto superior direito (o estado destacado vem de `ESTADO` em `scripts/baixar-mapa-osm.py`) |
| `PASSO_ARVORE` | distância entre as árvores desenhadas na mata (menor = mais árvores) |
| `TOL_AREA` / `AREA_MIN_PX` | quanto simplificar as formas; menos detalhe = página mais leve |

### Mudar o recorte ou atualizar a geografia

Só é preciso se o mapa tiver que mostrar outra região (por exemplo, um campus
fora de Ilhéus–Itabuna). Ajuste `RECORTE` em `scripts/baixar-mapa-osm.py` e
rode, uma vez, com internet:

```bash
python3 -m pip install shapely
python3 scripts/baixar-mapa-osm.py
./build.sh
```

Commite os `_data/mapa-osm.json` e `_data/mapa-brasil.json` gerados. Os dados
regionais são © colaboradores do OpenStreetMap (licença ODbL) — o crédito já
aparece no canto do mapa; o Natural Earth é domínio público.

**Como achar as coordenadas:** abra [openstreetmap.org](https://www.openstreetmap.org),
clique com o botão direito no ponto e escolha "Mostrar endereço". A URL passa a
conter `mlat=` e `mlon=` — são exatamente os valores de `lat` e `lon`.

### Por que imagem e não mapa interativo

A primeira versão usava Leaflet com tiles carregados na hora. Dois provedores
gratuitos falharam em sequência: `tile.openstreetmap.org` passou a devolver
**"Access blocked"** (a política deles barra sites publicados e requisições sem
`Referer`, inclusive ao abrir o HTML direto do disco) e `basemaps.cartocdn.com`
passou a escrever **"API KEY REQUIRED"** por cima do mapa. Serviços sem chave
mudam de política sem aviso, e o site quebra sozinho.

A imagem estática elimina essa classe inteira de problema. Se um dia o mapa
precisar de zoom de verdade, a saída é criar conta em um serviço com camada
gratuita (MapTiler, Stadia, Mapbox) e usar a chave deles.

## Adicionar um evento

Cada evento é uma **pasta** dentro de `eventos/`. Na página de Eventos e
notícias ele aparece como um item da lista e, ao ser clicado, abre a página completa do
evento — com texto, capa e galeria de fotos.

### Passo a passo

1. Copie a pasta modelo, dando a ela um nome no formato `AAAA-MM-DD-nome-curto`
   (só letras minúsculas, números e hífens — esse nome vira o endereço da
   página):

   ```bash
   cp -R eventos/_modelo eventos/2026-05-20-congresso-de-virologia
   ```

2. Preencha `evento.yml` (uma linha por campo, no formato `chave: valor`).
3. Escreva o texto em `texto-pt.md` e, se quiser, `texto-en.md`.
4. Coloque a capa na pasta e as fotos dentro de `fotos/`.
5. Apague `fotos/LEIA-ME.txt` e rode `./build.sh`.

### O que vai em cada arquivo

```
eventos/2026-05-20-congresso-de-virologia/
  evento.yml     dados do evento (obrigatório)
  texto-pt.md    texto da página, em Markdown
  texto-en.md    versão em inglês (opcional — sem ele, usa o texto em português)
  capa.jpg       imagem de capa (opcional)
  fotos/         imagens da galeria (opcional)
    01-abertura.jpg
    02-sessao-de-posteres.jpg
```

### Campos do `evento.yml`

| campo | obrigatório | descrição |
| --- | --- | --- |
| `titulo_pt` | **sim** | nome do evento em português |
| `titulo_en` | não | nome em inglês (vazio = usa o português) |
| `categoria` | não | `organizado` (evento do laboratório, ex.: workshop) ou `participacao` (congresso, prêmio, notícia; é o padrão) |
| `data` | **sim** | data de início, sempre `AAAA-MM-DD` |
| `data_texto_pt` | não | como a data aparece escrita (ex.: `20–22 mai 2026`) |
| `data_texto_en` | não | idem, em inglês |
| `local_pt` / `local_en` | não | cidade, estado ou instituição |
| `resumo_pt` / `resumo_en` | não | uma frase, aparece na lista de eventos |
| `capa` | não | nome do arquivo de capa dentro da pasta |
| `link` | não | site oficial do evento |

A página tem duas seções, escolhidas pelo campo `categoria`: **Organizados
pelo BioVirLab** (`organizado`) e **Participações e notícias**
(`participacao`). Dentro de cada uma, o campo `data` ordena a lista (do mais
recente para o mais antigo); eventos com data no futuro aparecem com o selo
**Em breve**, que some sozinho quando a data passa.

### Fotos

Tudo que estiver em `fotos/` com extensão `.jpg`, `.jpeg`, `.png` ou `.webp`
vira galeria, na ordem alfabética do nome do arquivo. Por isso vale numerar. O
nome do arquivo depois do número vira a legenda:

```
03-apresentacao-do-lucas.jpg   ->   legenda "Apresentacao do lucas"
```

Sem a pasta `fotos/` (ou com ela vazia), a página simplesmente não tem galeria.

### Observações

- Pastas cujo nome começa com `_` são ignoradas — é assim que `eventos/_modelo`
  não vira uma página. Renomear um evento para `_2024-algo` é uma forma rápida
  de tirá-lo do ar sem apagar nada.
- Os arquivos `eventos/*/index.qmd` e `en/events/*/index.qmd` são **gerados** a
  cada `./build.sh`. Não edite esses arquivos: as alterações são sobrescritas.
- Para remover um evento, apague a pasta e rode `./build.sh` — o script também
  limpa as páginas geradas do evento que sumiu.

## Instituições colaboradoras

As logos da seção **Instituições colaboradoras** (página Linhas de Pesquisa)
vêm direto da pasta `assets/colaboradores/`: basta colocar a imagem lá e rodar
`./build.sh`. Não há lista para editar — o script
`scripts/build-colaboradores.py` lê a pasta a cada build.

- formatos: `.png`, `.jpg`, `.jpeg`, `.svg`, `.webp`, `.gif`;
- o nome do arquivo vira o texto da logo (dica ao passar o mouse e texto para
  leitores de tela): `universidade-federal-da-bahia.png` →
  "Universidade federal da bahia". Use nomes descritivos;
- a ordem é alfabética; para escolher a ordem, comece o nome com um número:
  `01-ufba.png`, `02-fiocruz.svg` (o número não aparece no site);
- arquivos começados por `_` são ignorados — útil para tirar uma logo do ar
  sem apagá-la;
- as logos aparecem pequenas (até 68 px de altura), então prefira SVG ou PNG
  com fundo transparente, **recortado rente à logo** (margem em branco na
  imagem deixa a logo minúscula) e até ~400 KB; o build avisa sobre arquivos
  maiores.

Com a pasta vazia, a seção mostra um texto provisório.

## Ferramentas

A página **Ferramentas** (`ferramentas.qmd` / `en/tools.qmd`) é escrita
diretamente em HTML dentro do `.qmd`. Cada ferramenta tem um botão
`tool-pick` (a aba) e uma `section.tool-panel` com o mesmo `id`; as etapas do
fluxo são pares `flow-step` / `flow-detail`, na mesma ordem. O comportamento
(abas, etapas, filtro de leituras curtas/longas e contagem de programas) está
em `js/ferramentas.js` e os logos em `assets/tool-*.{webp,svg}`. Links como
`ferramentas.html#vapor` abrem direto na ferramenta.

## Adicionar uma página nova

1. crie `nova-pagina.qmd` e `en/new-page.qmd`;
2. registre `nova-pagina.qmd` em `_quarto-pt.yml` (`project.render` e `navbar`)
   e a versão em inglês em `_quarto-en.yml`;
3. adicione o par `["nova-pagina.html", "new-page.html"]` em
   `js/lang-switch.html` para que o seletor de idioma funcione na página.

## Publicação no GitHub Pages

Em *Settings → Pages*, selecione **Deploy from a branch**, branch `main` e
pasta `/docs`. Basta commitar `docs/` junto com as fontes.
