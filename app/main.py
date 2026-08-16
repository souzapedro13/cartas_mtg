import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.models import (
    AnaliseDeckResposta,
    BrasilResumo,
    CartaResposta,
    ComparacaoResumo,
    DeckResumo,
    ImportacaoResumo,
    PrecoLigaMagic,
    SubtotalCarta,
)
from app.services.calculos import (
    calcular_importacao,
    calcular_totais_brasil,
    comparar_precos,
    moeda,
)
from app.services.cambio import CambioError, obter_cotacao_usd_brl
from app.services.ligamagic import consultar_carta
from app.services.mtggoldfish import MTGGoldfishError, USER_AGENT, obter_deck


app = FastAPI(
    title="API de Preços de Decks MTG",
    description="Compara uma estimativa brasileira com a importação de um deck do MTGGoldfish.",
    version=__version__,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def pagina_inicial() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api", tags=["Informações"])
async def inicio() -> dict[str, str]:
    return {
        "nome": "API de Preços de Decks MTG",
        "descricao": "Analisa decks do MTGGoldfish e consulta preços públicos da LigaMagic.",
        "versao": __version__,
        "interface": "/",
        "documentacao": "/docs",
    }


@app.get("/health", tags=["Informações"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/analisar-deck", response_model=AnaliseDeckResposta, tags=["Análise"])
async def analisar_deck(
    url: str = Query(..., description="URL pública de deck/archetype do MTGGoldfish"),
    frete_usd: float = Query(46.0, ge=0, description="Frete estimado em dólares"),
    cotacao_usd_brl: float | None = Query(
        None, gt=0, description="Cotação manual opcional; se omitida, consulta a AwesomeAPI"
    ),
) -> AnaliseDeckResposta:
    timeout = httpx.Timeout(20.0)
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True
    ) as client:
        try:
            deck, (cotacao, fonte_cotacao) = await asyncio.gather(
                obter_deck(url, client), obter_cotacao_usd_brl(cotacao_usd_brl, client)
            )
        except MTGGoldfishError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except CambioError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        resultados = await asyncio.gather(
            *(consultar_carta(carta.nome, client) for carta in deck.cartas)
        )

    cartas_resposta: list[CartaResposta] = []
    itens_totais = []
    for carta, resultado in zip(deck.cartas, resultados, strict=True):
        quantidade = carta.quantidade_total
        itens_totais.append(
            (
                quantidade,
                resultado.preco_minimo,
                resultado.preco_medio,
                resultado.preco_maximo,
            )
        )
        preco = subtotal = None
        if resultado.status == "ok":
            assert resultado.preco_minimo is not None
            assert resultado.preco_medio is not None
            assert resultado.preco_maximo is not None
            preco = PrecoLigaMagic(
                preco_minimo=resultado.preco_minimo,
                preco_medio=resultado.preco_medio,
                preco_maximo=resultado.preco_maximo,
                edicao_referencia=resultado.edicao_referencia,
            )
            subtotal = SubtotalCarta(
                minimo=moeda(quantidade * resultado.preco_minimo),
                medio=moeda(quantidade * resultado.preco_medio),
                maximo=moeda(quantidade * resultado.preco_maximo),
            )

        cartas_resposta.append(
            CartaResposta(
                nome=carta.nome,
                nome_pt=resultado.nome_pt,
                quantidade_main=carta.quantidade_main,
                quantidade_sideboard=carta.quantidade_sideboard,
                quantidade_total=quantidade,
                imagem=resultado.imagem,
                ligamagic=preco,
                subtotal=subtotal,
                status=resultado.status,
                detalhe=resultado.detalhe,
            )
        )

    brasil_dados = calcular_totais_brasil(itens_totais)
    importacao_dados = calcular_importacao(deck.preco_usd, frete_usd, cotacao)
    comparacao_dados = comparar_precos(
        float(importacao_dados["total_brl"]), float(brasil_dados["total_minimo_brl"])
    )

    return AnaliseDeckResposta(
        deck=DeckResumo(
            nome=deck.nome,
            formato=deck.formato,
            url=deck.url,
            main_deck_cartas=deck.total_main,
            sideboard_cartas=deck.total_sideboard,
            preco_mtggoldfish_usd=moeda(deck.preco_usd),
        ),
        brasil=BrasilResumo(**brasil_dados),
        importacao=ImportacaoResumo(
            **importacao_dados,
            fonte_cotacao=fonte_cotacao,
            aviso="Estimativa de importação. Não inclui tributação, IOF ou outras despesas.",
        ),
        comparacao=ComparacaoResumo(
            **comparacao_dados,
            confiavel=int(brasil_dados["cartas_sem_cotacao"]) == 0,
            observacao=(
                None
                if int(brasil_dados["cartas_sem_cotacao"]) == 0
                else "Comparação parcial: há cartas sem cotação que não entraram no total brasileiro."
            ),
        ),
        cartas=cartas_resposta,
        avisos=[
            "O valor do MTGGoldfish é uma referência em dólar e não representa necessariamente um carrinho real em uma única loja.",
            "Os totais brasileiros consideram somente as cartas que tiveram cotação válida.",
        ],
    )
