import asyncio

import httpx

import app.services.precos_brasil as precos
from app.services.ligamagic import ResultadoLigaMagic


def test_snapshot_substitui_consulta_ligamagic_indisponivel(monkeypatch):
    async def consulta_liga(_nome, _client):
        return ResultadoLigaMagic(
            nome_en="Brainstorm",
            nome_pt=None,
            preco_minimo=None,
            preco_medio=None,
            preco_maximo=None,
            imagem="https://cards.scryfall.io/brainstorm.jpg",
            edicao_referencia=None,
            status="erro_consulta",
            detalhe="LigaMagic bloqueada",
        )

    monkeypatch.setattr(precos, "consultar_carta", consulta_liga)
    monkeypatch.setattr(
        precos,
        "_carregar_snapshot",
        lambda: {
            "atualizado_em": "2026-08-16T20:00-03:00",
            "cartas": {
                "brainstorm": {
                    "nome_en": "Brainstorm",
                    "nome_pt": "Tempestade Cerebral",
                    "preco_minimo": 12.90,
                    "preco_medio": 16.86,
                    "preco_maximo": 19.99,
                    "imagem": None,
                    "edicao_referencia": "Masters 25",
                }
            },
        },
    )

    async def executar():
        async with httpx.AsyncClient() as client:
            return await precos.consultar_preco_brasil("Brainstorm", client)

    resultado = asyncio.run(executar())

    assert resultado.status == "ok"
    assert resultado.fonte == "LigaMagic · snapshot"
    assert resultado.preco_minimo == 12.90
    assert resultado.preco_medio == 16.86
    assert resultado.imagem == "https://cards.scryfall.io/brainstorm.jpg"
