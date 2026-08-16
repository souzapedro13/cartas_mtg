import pytest

from app.services.mtggoldfish import (
    MTGGoldfishError,
    parse_mtggoldfish_html,
    validar_url_mtggoldfish,
)


HTML_DECK = """
<html><body>
  <h1 class="title">Blue Terror <span class="author">by Teste</span></h1>
  <div class="deck-price-v2 paper">
    $ <span class="dollars">121</span><span class="cents">.78</span>
  </div>
  <p class="deck-container-information">Format: Pauper<br>Deck Date: Aug 1, 2026</p>
  <input name="deck_input[deck]" value="4 Brainstorm&#10;4 Counterspell&#10;52 Island&#10;sideboard&#10;3 Annul&#10;2 Hydroblast">
</body></html>
"""


@pytest.mark.parametrize(
    "url",
    [
        "https://www.mtggoldfish.com/archetype/exemplo#paper",
        "https://mtggoldfish.com/deck/123",
    ],
)
def test_validar_url_mtggoldfish_aceita_dominio_oficial(url):
    assert validar_url_mtggoldfish(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/archetype/teste",
        "https://mtggoldfish.com.example.com/deck/123",
        "not-a-url",
        "ftp://www.mtggoldfish.com/deck/123",
    ],
)
def test_validar_url_mtggoldfish_rejeita_url_invalida(url):
    assert not validar_url_mtggoldfish(url)


def test_parser_decklist_controlada():
    deck = parse_mtggoldfish_html(HTML_DECK, "https://www.mtggoldfish.com/deck/123")

    assert deck.nome == "Blue Terror"
    assert deck.formato == "Pauper"
    assert deck.preco_usd == 121.78
    assert deck.total_main == 60
    assert deck.total_sideboard == 5
    brainstorm = next(c for c in deck.cartas if c.nome == "Brainstorm")
    assert brainstorm.quantidade_main == 4
    assert brainstorm.quantidade_sideboard == 0


def test_parser_falha_sem_decklist():
    with pytest.raises(MTGGoldfishError, match="decklist"):
        parse_mtggoldfish_html(
            '<div class="deck-price-v2 paper">$ 10.00</div>',
            "https://www.mtggoldfish.com/deck/123",
        )
