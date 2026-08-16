from app.services.calculos import (
    calcular_importacao,
    calcular_totais_brasil,
    comparar_precos,
)


def test_calcular_totais_brasil_ignora_sem_cotacao():
    resultado = calcular_totais_brasil(
        [
            (4, 10.0, 12.5, 15.0),
            (2, 5.0, 7.0, 9.0),
            (3, None, None, None),
        ]
    )

    assert resultado == {
        "total_minimo_brl": 50.0,
        "total_medio_brl": 64.0,
        "total_maximo_brl": 78.0,
        "cartas_com_cotacao": 2,
        "cartas_sem_cotacao": 1,
    }


def test_calcular_importacao():
    resultado = calcular_importacao(deck_usd=121.78, frete_usd=46.0, cotacao=5.25)

    assert resultado["total_usd"] == 167.78
    assert resultado["total_brl"] == 880.85


def test_comparar_brasil_e_importacao():
    brasil = comparar_precos(total_importacao_brl=880.85, total_brasil_minimo=500.0)
    importacao = comparar_precos(total_importacao_brl=400.0, total_brasil_minimo=500.0)

    assert brasil["mais_barato"] == "brasil"
    assert brasil["diferenca_brl"] == 380.85
    assert importacao["mais_barato"] == "importacao"
    assert importacao["diferenca_brl"] == 100.0


def test_comparacao_indisponivel_sem_cotacao_brasileira():
    resultado = comparar_precos(
        total_importacao_brl=880.85,
        total_brasil_minimo=0.0,
        possui_cotacao_brasil=False,
    )

    assert resultado["mais_barato"] == "indisponivel"
    assert resultado["diferenca_brl"] == 0.0
