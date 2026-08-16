# Analisador de preços de decks de Magic

Projeto final da disciplina de APIs, FastAPI, Docker e deploy. A aplicação recebe um link público de deck/archetype do MTGGoldfish, lê a lista de cartas, consulta referências de preço na LigaMagic e compara uma estimativa brasileira com uma estimativa simples de importação.

A raiz da aplicação também oferece uma interface web responsiva chamada **DeckValor**. Nela, o usuário informa apenas a URL do deck e o frete estimado. O resultado apresenta a comparação, os totais e uma galeria das cartas com imagens. O Swagger continua disponível em `/docs`.

## Como funciona

1. O MTGGoldfish fornece nome, formato, decklist e preço paper do deck em dólar.
2. As cartas distintas são consultadas na página pública da LigaMagic, com no máximo duas requisições simultâneas, intervalo mínimo de um segundo entre chamadas e cache em memória de dez minutos. Respostas `429` acionam espera progressiva e novas tentativas.
3. A aplicação soma `quantidade × preço` para os cenários mínimo, médio e máximo no Brasil.
4. A importação soma o preço de referência do deck e o frete (US$ 46,00 por padrão), depois converte o total pela cotação USD/BRL. A AwesomeAPI é a fonte principal e a Frankfurter funciona como alternativa automática se a primeira estiver indisponível ou limitar as requisições.

O parser do MTGGoldfish prioriza o campo textual `deck_input[deck]` presente no HTML, que contém a separação `sideboard`. Assim, não depende das tabelas que a página carrega depois com JavaScript.

Na LigaMagic, o projeto interpreta a variável JavaScript `cards_editions`. Os campos `p`, `m` e `g` correspondem aos valores mínimo, médio e máximo mostrados pela página. Para não misturar versões diferentes, são considerados apenas valores positivos da carta principal, é priorizado o registro comum (`price["0"]`) e são descartadas, por regras simples, edições digitais ou claramente especiais. Entre as edições restantes, a edição com o menor preço médio é usada como referência; mínimo, médio, máximo e imagem vêm dessa mesma edição. Se nenhuma cotação for válida, a carta recebe status próprio e o restante do deck continua sendo processado.

## Fontes e limitações

- **MTGGoldfish:** decklist e preço paper de referência em dólar.
- **LigaMagic:** nomes, imagem e preços brasileiros obtidos de páginas públicas. Não é usada uma integração oficial e mudanças no HTML podem exigir ajuste do parser.
- **AwesomeAPI:** fonte principal da cotação pública USD/BRL (`bid`), sem chave.
- **Frankfurter:** segunda fonte pública sem chave, usada automaticamente quando a AwesomeAPI não responde. Uma cotação manual ainda pode ser enviada se ambas estiverem indisponíveis.

Os preços mudam e representam estimativas. Cartas sem cotação não entram nos totais brasileiros; quando isso ocorre, `comparacao.confiavel` é `false` e a resposta explica que a comparação é parcial. Não há otimização por loja, frete nacional, estoque, impostos, IOF, autenticação ou banco de dados. O Scryfall não foi necessário nesta versão.

A LigaMagic pode apresentar um desafio do Cloudflare para endereços de datacenter. Quando nenhuma carta recebe cotação brasileira, a API marca a comparação como `indisponivel` em vez de tratar o total zero como uma opção mais barata. O restante da análise e a estimativa internacional continuam disponíveis.

O valor do MTGGoldfish é uma referência e não representa necessariamente um carrinho real em uma única loja. A importação é uma estimativa e não inclui tributação, IOF ou outras despesas.

## Instalação e execução local

No PowerShell, entre na pasta do projeto e escolha Conda ou `venv`.

### Conda

```powershell
cd D:\GenAI\Produtos_GenAI\Projeto_final_paulo
conda env create -f environment.yml
conda activate mtg-deck-prices
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### venv

```powershell
cd D:\GenAI\Produtos_GenAI\Projeto_final_paulo
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/` para usar a interface ou `http://127.0.0.1:8000/docs` para usar o Swagger. Exemplos:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health

$deck = [uri]::EscapeDataString('https://www.mtggoldfish.com/archetype/pauper-blue-terror-2b4f6710-ccb2-4660-b5f9-ea85c8875ec5#paper')
Invoke-RestMethod "http://127.0.0.1:8000/analisar-deck?url=$deck&frete_usd=46"

Invoke-RestMethod "http://127.0.0.1:8000/analisar-deck?url=$deck&frete_usd=46&cotacao_usd_brl=5.25"
```

Para executar os testes sem depender da internet:

```powershell
python -m pytest -p no:cacheprovider
```

## Docker

```powershell
docker build -t mtg-deck-prices .
docker run --rm -p 8000:8000 mtg-deck-prices
```

O contêiner usa Python 3.12 slim e inicia o Uvicorn na porta 8000.

## Endpoints

- `GET /` — interface web do DeckValor.
- `GET /api` — informações da API.
- `GET /health` — verificação simples de saúde.
- `GET /analisar-deck` — parâmetros `url`, `frete_usd` e `cotacao_usd_brl`.

## Estrutura

```text
app/
  main.py
  models.py
  static/
    index.html
    styles.css
    app.js
  services/
    mtggoldfish.py
    ligamagic.py
    cambio.py
    calculos.py
tests/
Dockerfile
requirements.txt
environment.yml
```
