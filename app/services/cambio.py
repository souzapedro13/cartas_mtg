import httpx

from app.services.mtggoldfish import USER_AGENT


AWESOMEAPI_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rate/USD/BRL"


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
        fontes = (
            (AWESOMEAPI_URL, lambda dados: dados["USDBRL"]["bid"], "AwesomeAPI (USD/BRL bid)"),
            (FRANKFURTER_URL, lambda dados: dados["rate"], "Frankfurter (USD/BRL)"),
        )
        ultimo_erro: Exception | None = None
        for url, extrair, nome_fonte in fontes:
            try:
                response = await client.get(url)
                response.raise_for_status()
                cotacao = float(extrair(response.json()))
                if cotacao <= 0:
                    raise ValueError("cotação inválida")
                return cotacao, nome_fonte
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                ultimo_erro = exc

        raise CambioError(
            "Não foi possível obter a cotação USD/BRL nas fontes automáticas. "
            "Informe cotacao_usd_brl manualmente."
        ) from ultimo_erro
    finally:
        if owns_client:
            await client.aclose()
