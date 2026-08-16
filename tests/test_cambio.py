import httpx
import pytest

from app.services.cambio import obter_cotacao_usd_brl


@pytest.mark.anyio
async def test_cotacao_manual_nao_consulta_servico():
    cotacao, fonte = await obter_cotacao_usd_brl(5.25)

    assert cotacao == 5.25
    assert fonte == "informada na requisição"


@pytest.mark.anyio
async def test_awesomeapi_e_fonte_principal():
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "economia.awesomeapi.com.br"
        return httpx.Response(200, json={"USDBRL": {"bid": "5.22"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
        cotacao, fonte = await obter_cotacao_usd_brl(client=client)

    assert cotacao == 5.22
    assert fonte == "AwesomeAPI (USD/BRL bid)"


@pytest.mark.anyio
async def test_frankfurter_e_fallback_quando_awesomeapi_limita():
    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.host == "economia.awesomeapi.com.br":
            return httpx.Response(429)
        assert request.url.host == "api.frankfurter.dev"
        return httpx.Response(200, json={"rate": 5.1854})

    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
        cotacao, fonte = await obter_cotacao_usd_brl(client=client)

    assert cotacao == 5.1854
    assert fonte == "Frankfurter (USD/BRL)"
