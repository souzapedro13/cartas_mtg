from app.services.ligamagic import extrair_cards_editions, parse_ligamagic_html


HTML_LIGA = """
<html><head><title>Tempestade Cerebral / Brainstorm | Busca de Cartas</title></head>
<body><script>
var cards_editions = [
  {"id": 1, "idcard": 4214, "name": "Secret Lair Drop Series", "code": "sld1", "img": "//img/special.jpg", "ntl": 0,
   "price": [{"p": "1.00", "m": "2.00", "g": "3.00"}]},
  {"id": 2, "idcard": 9999, "name": "Outra carta", "code": "abc", "img": "//img/wrong.jpg", "ntl": 0,
   "price": [{"p": "0.50", "m": "1.00", "g": "2.00"}]},
  {"id": 3, "idcard": 4214, "name": "Masters 25", "code": "a25", "img": "//img/a25.jpg", "ntl": 0,
   "price": {"0": {"p": "12.90", "m": "16.86", "g": "19.99"}, "2": {"p": "23.26", "m": "28.01", "g": "35.00"}}},
  {"id": 4, "idcard": 4214, "name": "Commander", "code": "cmd", "img": "//img/cmd.jpg", "ntl": 0,
   "price": [{"p": "10.91", "m": "23.68", "g": "54.00"}]}
];
var param = {"card": {"id": "4214"}};
</script></body></html>
"""


def test_extrair_cards_editions():
    edicoes = extrair_cards_editions(HTML_LIGA)

    assert len(edicoes) == 4
    assert edicoes[2]["price"]["0"]["m"] == "16.86"


def test_parser_escolhe_edicao_regular_com_menor_media():
    resultado = parse_ligamagic_html(HTML_LIGA, "Brainstorm")

    assert resultado.status == "ok"
    assert resultado.nome_pt == "Tempestade Cerebral"
    assert resultado.preco_minimo == 12.90
    assert resultado.preco_medio == 16.86
    assert resultado.preco_maximo == 19.99
    assert resultado.edicao_referencia == "Masters 25"
    assert resultado.imagem == "https://img/a25.jpg"
