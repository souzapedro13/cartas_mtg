"""Atualiza o snapshot de preços usando uma rede com acesso à LigaMagic."""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

from app.services.ligamagic import consultar_carta
from app.services.mtggoldfish import USER_AGENT, obter_deck


ARQUIVO = RAIZ_PROJETO / "app" / "data" / "precos_ligamagic.json"


async def atualizar(urls: list[str]) -> tuple[int, int]:
    cartas: dict[str, dict] = {}
    if ARQUIVO.exists():
        try:
            atual = json.loads(ARQUIVO.read_text(encoding="utf-8"))
            if isinstance(atual.get("cartas"), dict):
                cartas.update(atual["cartas"])
        except (OSError, json.JSONDecodeError, AttributeError):
            pass

    timeout = httpx.Timeout(25.0)
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True
    ) as client:
        decks = await asyncio.gather(*(obter_deck(url, client) for url in urls))
        nomes = sorted({carta.nome for deck in decks for carta in deck.cartas})
        resultados = await asyncio.gather(*(consultar_carta(nome, client) for nome in nomes))

    atualizadas = 0
    for nome, resultado in zip(nomes, resultados, strict=True):
        if resultado.status != "ok":
            continue
        cartas[nome.casefold().strip()] = {
            "nome_en": resultado.nome_en,
            "nome_pt": resultado.nome_pt,
            "preco_minimo": resultado.preco_minimo,
            "preco_medio": resultado.preco_medio,
            "preco_maximo": resultado.preco_maximo,
            "imagem": resultado.imagem,
            "edicao_referencia": resultado.edicao_referencia,
        }
        atualizadas += 1

    payload = {
        "atualizado_em": datetime.now().astimezone().isoformat(timespec="minutes"),
        "cartas": dict(sorted(cartas.items())),
    }
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return atualizadas, len(nomes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", help="URLs públicas de decks do MTGGoldfish")
    args = parser.parse_args()
    atualizadas, total = asyncio.run(atualizar(args.urls))
    print(f"Snapshot atualizado: {atualizadas}/{total} cartas com cotação.")


if __name__ == "__main__":
    main()
