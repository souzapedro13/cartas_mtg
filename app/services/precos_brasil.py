import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.services.ligamagic import LIGAMAGIC_URL, consultar_carta


CACHE_ARQUIVO = Path(__file__).resolve().parents[1] / "data" / "precos_ligamagic.json"


@dataclass(slots=True)
class ResultadoPrecoBrasil:
    nome_en: str
    nome_pt: str | None
    preco_minimo: float | None
    preco_medio: float | None
    preco_maximo: float | None
    imagem: str | None
    edicao_referencia: str | None
    fonte: str
    url_fonte: str | None
    status: str
    detalhe: str | None = None


@lru_cache(maxsize=1)
def _carregar_snapshot() -> dict:
    try:
        dados = json.loads(CACHE_ARQUIVO.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"atualizado_em": None, "cartas": {}}
    return dados if isinstance(dados, dict) else {"atualizado_em": None, "cartas": {}}


def _consultar_snapshot(nome: str) -> ResultadoPrecoBrasil | None:
    dados = _carregar_snapshot()
    cartas = dados.get("cartas")
    if not isinstance(cartas, dict):
        return None
    carta = cartas.get(nome.casefold().strip())
    if not isinstance(carta, dict):
        return None
    try:
        minimo = float(carta["preco_minimo"])
        medio = float(carta["preco_medio"])
        maximo = float(carta["preco_maximo"])
    except (KeyError, TypeError, ValueError):
        return None

    atualizado_em = dados.get("atualizado_em")
    detalhe = "Snapshot local da LigaMagic"
    if isinstance(atualizado_em, str) and atualizado_em:
        detalhe += f", atualizado em {atualizado_em}"
    return ResultadoPrecoBrasil(
        nome_en=str(carta.get("nome_en") or nome),
        nome_pt=str(carta["nome_pt"]) if carta.get("nome_pt") else None,
        preco_minimo=minimo,
        preco_medio=medio,
        preco_maximo=maximo,
        imagem=str(carta["imagem"]) if carta.get("imagem") else None,
        edicao_referencia=(
            str(carta["edicao_referencia"])
            if carta.get("edicao_referencia")
            else None
        ),
        fonte="LigaMagic · snapshot",
        url_fonte=f"{LIGAMAGIC_URL}?{urlencode({'card': nome, 'view': 'cards/card'})}",
        status="ok",
        detalhe=detalhe,
    )


async def consultar_preco_brasil(
    nome: str, client: httpx.AsyncClient
) -> ResultadoPrecoBrasil:
    liga = await consultar_carta(nome, client)
    if liga.status == "ok":
        return ResultadoPrecoBrasil(
            nome_en=liga.nome_en,
            nome_pt=liga.nome_pt,
            preco_minimo=liga.preco_minimo,
            preco_medio=liga.preco_medio,
            preco_maximo=liga.preco_maximo,
            imagem=liga.imagem,
            edicao_referencia=liga.edicao_referencia,
            fonte="LigaMagic",
            url_fonte=f"{LIGAMAGIC_URL}?{urlencode({'card': nome, 'view': 'cards/card'})}",
            status="ok",
        )

    snapshot = _consultar_snapshot(nome)
    if snapshot is not None:
        if snapshot.imagem is None:
            snapshot.imagem = liga.imagem
        if snapshot.nome_pt is None:
            snapshot.nome_pt = liga.nome_pt
        return snapshot

    return ResultadoPrecoBrasil(
        nome_en=liga.nome_en,
        nome_pt=liga.nome_pt,
        preco_minimo=None,
        preco_medio=None,
        preco_maximo=None,
        imagem=liga.imagem,
        edicao_referencia=None,
        fonte="LigaMagic",
        url_fonte=f"{LIGAMAGIC_URL}?{urlencode({'card': nome, 'view': 'cards/card'})}",
        status=liga.status,
        detalhe=liga.detalhe,
    )
