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
    chamadas = 0

    async def sem_espera():
        return None

    async def sem_cooldown(_segundos):
        return None

    async def handler(request):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, text=HTML_SEM_COTACAO, request=request)

    monkeypatch.setattr(liga, "_aguardar_janela_de_requisicao", sem_espera)
    monkeypatch.setattr(liga, "_aplicar_cooldown", sem_cooldown)
    liga._cache.clear()
    async def executar():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await liga.consultar_carta("Card", client)

    resultado = asyncio.run(executar())

    assert chamadas == 2
    assert resultado.status == "sem_cotacao"
