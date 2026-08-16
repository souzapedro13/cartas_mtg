import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127 Safari/537.36"
)


class MTGGoldfishError(RuntimeError):
    pass


@dataclass(slots=True)
class CartaDeck:
    nome: str
    quantidade_main: int = 0
    quantidade_sideboard: int = 0

    @property
    def quantidade_total(self) -> int:
        return self.quantidade_main + self.quantidade_sideboard


@dataclass(slots=True)
class DeckExtraido:
    nome: str
    formato: str | None
    url: str
    preco_usd: float
    cartas: list[CartaDeck]

    @property
    def total_main(self) -> int:
        return sum(c.quantidade_main for c in self.cartas)

    @property
    def total_sideboard(self) -> int:
        return sum(c.quantidade_sideboard for c in self.cartas)


def validar_url_mtggoldfish(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in {
        "mtggoldfish.com",
        "www.mtggoldfish.com",
    }


def _texto_direto(elemento) -> str:
    for item in elemento.contents:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return elemento.get_text(" ", strip=True)


def _parse_decklist_texto(texto: str) -> list[CartaDeck]:
    cartas: dict[str, CartaDeck] = {}
    sideboard = False

    for linha in texto.replace("\r", "").split("\n"):
        linha = linha.strip()
        if not linha:
            continue
        if linha.casefold() in {"sideboard", "side board"}:
            sideboard = True
            continue

        match = re.match(r"^(\d+)\s+(.+?)\s*$", linha)
        if not match:
            continue
        quantidade = int(match.group(1))
        nome = match.group(2).strip()
        if quantidade <= 0 or not nome:
            continue

        chave = nome.casefold()
        carta = cartas.setdefault(chave, CartaDeck(nome=nome))
        if sideboard:
            carta.quantidade_sideboard += quantidade
        else:
            carta.quantidade_main += quantidade

    return list(cartas.values())


def parse_mtggoldfish_html(html: str, url: str) -> DeckExtraido:
    soup = BeautifulSoup(html, "html.parser")

    titulo = soup.select_one("h1.title")
    nome = _texto_direto(titulo) if titulo else "Deck sem nome"

    informacoes = soup.select_one(".deck-container-information")
    formato = None
    if informacoes:
        match_formato = re.search(
            r"Format:\s*([^\n\r]+)", informacoes.get_text("\n", strip=True), re.IGNORECASE
        )
        if match_formato:
            formato = match_formato.group(1).strip()

    preco_elemento = soup.select_one(".deck-price-v2.paper")
    preco_usd = None
    if preco_elemento:
        dollars = preco_elemento.select_one(".dollars")
        cents = preco_elemento.select_one(".cents")
        if dollars:
            texto_preco = dollars.get_text(strip=True) + (cents.get_text(strip=True) if cents else "")
        else:
            texto_preco = preco_elemento.get_text(" ", strip=True)
        match_preco = re.search(r"(\d[\d,]*)(?:\.(\d{1,2}))?", texto_preco)
        if match_preco:
            inteiro = match_preco.group(1).replace(",", "")
            decimal = match_preco.group(2) or "00"
            preco_usd = float(f"{inteiro}.{decimal}")

    entrada_deck = soup.select_one('input[name="deck_input[deck]"]')
    deck_texto = entrada_deck.get("value", "") if entrada_deck else ""
    cartas = _parse_decklist_texto(deck_texto)

    if preco_usd is None:
        raise MTGGoldfishError("Não foi possível localizar o preço paper do deck no MTGGoldfish.")
    if not cartas:
        raise MTGGoldfishError("Não foi possível localizar a decklist no HTML do MTGGoldfish.")

    return DeckExtraido(
        nome=nome,
        formato=formato,
        url=url,
        preco_usd=preco_usd,
        cartas=cartas,
    )


async def obter_deck(url: str, client: httpx.AsyncClient | None = None) -> DeckExtraido:
    if not validar_url_mtggoldfish(url):
        raise MTGGoldfishError("A URL deve pertencer ao domínio mtggoldfish.com.")

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT}, timeout=20.0, follow_redirects=True
        )
    try:
        assert client is not None
        response = await client.get(url)
        response.raise_for_status()
        return parse_mtggoldfish_html(response.text, str(response.url))
    except httpx.HTTPError as exc:
        raise MTGGoldfishError(f"Falha ao consultar o MTGGoldfish: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()
