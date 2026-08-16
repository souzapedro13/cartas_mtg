import asyncio

import httpx

import app.services.ligamagic as liga


HTML_SEM_COTACAO = """
<html><head><title>Carta / Card | Busca</title></head><body><script>
var cards_editions = [];
var param = {"card": {"id": "1"}};
</script></body></html>
"""


def test_consulta_tenta_novamente_apos_429(monkeypatch):
    chamadas_ligamagic = 0

    async def sem_espera():
        return None

    async def sem_cooldown(_segundos):
        return None

    async def handler(request):
        nonlocal chamadas_ligamagic
        if request.url.host == "api.scryfall.com":
            return httpx.Response(404, request=request)
        chamadas_ligamagic += 1
        if chamadas_ligamagic == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, text=HTML_SEM_COTACAO, request=request)

    monkeypatch.setattr(liga, "_aguardar_janela_de_requisicao", sem_espera)
    monkeypatch.setattr(liga, "_aplicar_cooldown", sem_cooldown)
    liga._cache.clear()
    async def executar():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await liga.consultar_carta("Card", client)

    resultado = asyncio.run(executar())

    assert chamadas_ligamagic == 2
    assert resultado.status == "sem_cotacao"


def test_scryfall_completa_imagem_sem_substituir_preco(monkeypatch):
    async def sem_espera():
        return None

    async def handler(request):
        if request.url.host == "www.ligamagic.com.br":
            return httpx.Response(403, request=request)
        return httpx.Response(
            200,
            json={
                "name": "Brainstorm",
                "image_uris": {"normal": "https://cards.scryfall.io/normal/brainstorm.jpg"},
            },
            request=request,
        )

    monkeypatch.setattr(liga, "_aguardar_janela_de_requisicao", sem_espera)
    liga._cache.clear()

    async def executar():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await liga.consultar_carta("Brainstorm", client)

    resultado = asyncio.run(executar())

    assert resultado.status == "erro_consulta"
    assert resultado.preco_minimo is None
    assert resultado.imagem == "https://cards.scryfall.io/normal/brainstorm.jpg"
