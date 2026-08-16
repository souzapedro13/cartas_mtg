from collections.abc import Iterable


def moeda(valor: float) -> float:
    return round(float(valor) + 1e-9, 2)


def calcular_totais_brasil(
    itens: Iterable[tuple[int, float | None, float | None, float | None]],
) -> dict[str, float | int | None]:
    minimo = medio = maximo = 0.0
    com_cotacao = sem_cotacao = 0
    todos_com_media = todos_com_maximo = True
    for quantidade, preco_minimo, preco_medio, preco_maximo in itens:
        if preco_minimo is None:
            sem_cotacao += 1
            continue
        com_cotacao += 1
        minimo += quantidade * float(preco_minimo)
        if preco_medio is None:
            todos_com_media = False
        else:
            medio += quantidade * float(preco_medio)
        if preco_maximo is None:
            todos_com_maximo = False
        else:
            maximo += quantidade * float(preco_maximo)
    return {
        "total_minimo_brl": moeda(minimo),
        "total_medio_brl": moeda(medio) if com_cotacao and todos_com_media else None,
        "total_maximo_brl": moeda(maximo) if com_cotacao and todos_com_maximo else None,
        "cartas_com_cotacao": com_cotacao,
        "cartas_sem_cotacao": sem_cotacao,
    }


def calcular_importacao(deck_usd: float, frete_usd: float, cotacao: float) -> dict[str, float]:
    total_usd = deck_usd + frete_usd
    return {
        "deck_usd": moeda(deck_usd),
        "frete_usd": moeda(frete_usd),
        "total_usd": moeda(total_usd),
        "cotacao_usd_brl": round(float(cotacao), 4),
        "total_brl": moeda(total_usd * cotacao),
    }


def comparar_precos(
    total_importacao_brl: float,
    total_brasil_minimo: float,
    possui_cotacao_brasil: bool = True,
) -> dict[str, str | float]:
    if not possui_cotacao_brasil:
        return {
            "mais_barato": "indisponivel",
            "referencia_brasil": "sem cotação brasileira disponível",
            "diferenca_brl": 0.0,
        }

    diferenca = moeda(abs(total_importacao_brl - total_brasil_minimo))
    if total_importacao_brl < total_brasil_minimo:
        mais_barato = "importacao"
    elif total_importacao_brl > total_brasil_minimo:
        mais_barato = "brasil"
    else:
        mais_barato = "empate"
    return {
        "mais_barato": mais_barato,
        "referencia_brasil": "preço mínimo das cartas com cotação",
        "diferenca_brl": diferenca,
    }
