# biovir.github.io

Site oficial do **BioVirLab** — Laboratório de Bioinformática e Virologia.

Construído com [Quarto](https://quarto.org/docs/websites/). Todo o conteúdo é
escrito em arquivos `.qmd` e o HTML gerado vai para `docs/`, que é a pasta
publicada pelo GitHub Pages.

## Como gerar o site

```bash
./build.sh
```

O script faz cinco coisas:

1. gera as listas de membros a partir de `_data/members.tsv`;
2. gera as páginas de eventos a partir das pastas em `eventos/`;
3. gera a lista de publicações a partir de `_data/publicacoes.json`;
4. renderiza a versão **pt-BR** na raiz de `docs/`;
5. renderiza a versão **en** e copia para `docs/en/`.

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
_data/publicacoes.json    cache das publicações vindas do OpenAlex
eventos/<slug>/           um evento por pasta (texto, capa e fotos)
scripts/build-members.py  gera _includes/members-*.html a partir do TSV
scripts/build-eventos.py  gera as páginas de eventos a partir de eventos/
scripts/build-publicacoes.py  gera _includes/publicacoes-*.html
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

- artigos agrupados por ano, com autores, periódico e DOI;
- pré-prints em seção separada (bioRxiv, medRxiv, Research Square, SSRN,
  Authorea são reconhecidos pelo prefixo do DOI);
- **Colaborações**: o total de publicações e os nomes de todos os autores que
  não são integrantes do laboratório.

Integrantes aparecem em **negrito**, reconhecidos por cruzamento com
`_data/members.tsv`. Por isso, manter o TSV em dia melhora a página de
Publicações também. A comparação tolera abreviações (`J dos Santos Silva`
casa com `Jonatha dos Santos Silva`) e sufixos (`Junior`, `Neto`, `Filho`).

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

## Adicionar um evento

Cada evento é uma **pasta** dentro de `eventos/`. Na página de Eventos ele
aparece como um item da lista e, ao ser clicado, abre em uma nova aba a página
completa do evento — com texto, capa e galeria de fotos.

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
| `data` | **sim** | data de início, sempre `AAAA-MM-DD` |
| `data_texto_pt` | não | como a data aparece escrita (ex.: `20–22 mai 2026`) |
| `data_texto_en` | não | idem, em inglês |
| `local_pt` / `local_en` | não | cidade, estado ou instituição |
| `resumo_pt` / `resumo_en` | não | uma frase, aparece na lista de eventos |
| `capa` | não | nome do arquivo de capa dentro da pasta |
| `link` | não | site oficial do evento |

O campo `data` faz duas coisas: ordena a lista (do mais recente para o mais
antigo) e decide se o evento entra em **Próximos** (data no futuro) ou em
**Realizados** (data no passado). A troca acontece sozinha quando a data passa —
não é preciso mexer em nada.

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

## Adicionar uma página nova

1. crie `nova-pagina.qmd` e `en/new-page.qmd`;
2. registre `nova-pagina.qmd` em `_quarto-pt.yml` (`project.render` e `navbar`)
   e a versão em inglês em `_quarto-en.yml`;
3. adicione o par `["nova-pagina.html", "new-page.html"]` em
   `js/lang-switch.html` para que o seletor de idioma funcione na página.

## Publicação no GitHub Pages

Em *Settings → Pages*, selecione **Deploy from a branch**, branch `main` e
pasta `/docs`. Basta commitar `docs/` junto com as fontes.
