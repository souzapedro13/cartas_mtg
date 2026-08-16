import httpx

from app.services.mtggoldfish import USER_AGENT


CAMBIO_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL"


class CambioError(RuntimeError):
    pass


async def obter_cotacao_usd_brl(
    cotacao_manual: float | None = None, client: httpx.AsyncClient | None = None
) -> tuple[float, str]:
    if cotacao_manual is not None:
        if cotacao_manual <= 0:
            raise CambioError("A cotação manual deve ser maior que zero.")
        return float(cotacao_manual), "informada na requisição"

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=10.0)
    try:
        assert client is not None
        response = await client.get(CAMBIO_URL)
        response.raise_for_status()
        cotacao = float(response.json()["USDBRL"]["bid"])
        if cotacao <= 0:
            raise ValueError("cotação inválida")
        return cotacao, "AwesomeAPI (USD/BRL bid)"
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise CambioError(
            "Não foi possível obter a cotação USD/BRL. Informe cotacao_usd_brl manualmente."
        ) from exc
    finally:
        if owns_client:
            await client.aclose()
