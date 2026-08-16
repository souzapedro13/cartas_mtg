import asyncio
import html as html_lib
import json
import re
import time
from dataclasses import dataclass, replace
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.services.mtggoldfish import USER_AGENT


LIGAMAGIC_URL = "https://www.ligamagic.com.br/"
SCRYFALL_URL = "https://api.scryfall.com/cards/named"
CACHE_TTL_SEGUNDOS = 10 * 60
INTERVALO_ENTRE_REQUISICOES = 1.0
MAX_TENTATIVAS_RATE_LIMIT = 3

_cache: dict[str, tuple[float, "ResultadoLigaMagic"]] = {}
_semaforo = asyncio.Semaphore(2)
_rate_lock = asyncio.Lock()
_proximo_inicio = 0.0


@dataclass(slots=True)
class ResultadoLigaMagic:
    nome_en: str
    nome_pt: str | None
    preco_minimo: float | None
    preco_medio: float | None
    preco_maximo: float | None
    imagem: str | None
    edicao_referencia: str | None
    status: str
    detalhe: str | None = None


async def _aguardar_janela_de_requisicao() -> None:
    global _proximo_inicio
    async with _rate_lock:
        agora = time.monotonic()
        espera = max(0.0, _proximo_inicio - agora)
        if espera:
            await asyncio.sleep(espera)
        _proximo_inicio = time.monotonic() + INTERVALO_ENTRE_REQUISICOES


async def _aplicar_cooldown(segundos: float) -> None:
    global _proximo_inicio
    async with _rate_lock:
        _proximo_inicio = max(_proximo_inicio, time.monotonic() + segundos)


def _extrair_variavel_json(html: str, nome: str) -> Any:
    match = re.search(rf"\bvar\s+{re.escape(nome)}\s*=\s*", html)
    if not match:
        raise ValueError(f"Variável {nome} não encontrada.")
    try:
        valor, _ = json.JSONDecoder().raw_decode(html[match.end() :])
        return valor
    except json.JSONDecodeError as exc:
        raise ValueError(f"Conteúdo de {nome} não é um JSON válido.") from exc


def extrair_cards_editions(html: str) -> list[dict[str, Any]]:
    valor = _extrair_variavel_json(html, "cards_editions")
    if not isinstance(valor, list):
        raise ValueError("cards_editions não contém uma lista.")
    return valor


def _numero_positivo(valor: Any) -> float | None:
    try:
        numero = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None


def _preco_regular(edicao: dict[str, Any]) -> tuple[float, float, float] | None:
    preco = edicao.get("price")
    candidatos: list[Any] = []
    if isinstance(preco, list):
        candidatos.extend(preco)
    elif isinstance(preco, dict):
        if "0" in preco:
            candidatos.append(preco["0"])
        candidatos.extend(valor for chave, valor in preco.items() if chave != "0")

    for candidato in candidatos:
        if not isinstance(candidato, dict):
            continue
        minimo = _numero_positivo(candidato.get("p"))
        medio = _numero_positivo(candidato.get("m"))
        maximo = _numero_positivo(candidato.get("g"))
        if minimo is not None and medio is not None and maximo is not None:
            return minimo, medio, maximo
    return None


def _edicao_especial_ou_digital(edicao: dict[str, Any]) -> bool:
    nome = html_lib.unescape(str(edicao.get("name", ""))).casefold()
    codigo = str(edicao.get("code", "")).casefold()
    if int(edicao.get("ntl", 0) or 0) == 1:
        return True

    termos = (
        "secret lair",
        "world championship",
        "friday night magic",
        "masterpiece",
        "promo",
        "showcase",
        "borderless",
        "extended art",
        "collector booster",
        "japonês",
        "japanese",
        "mtgo",
        "magic online",
        "vintage masters",
    )
    return codigo.startswith(("sld", "sldex")) or any(termo in nome for termo in termos)


def _nomes_da_pagina(html: str, nome_consultado: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    titulo = soup.title.get_text(" ", strip=True) if soup.title else ""
    cabecalho = titulo.split("|")[0].strip()
    partes = [html_lib.unescape(p.strip()) for p in re.split(r"\s+/\s+", cabecalho, maxsplit=1)]
    if len(partes) == 2:
        esquerda, direita = partes
        if direita.casefold() == nome_consultado.casefold():
            return direita, esquerda
        if esquerda.casefold() == nome_consultado.casefold():
            return esquerda, direita
        return nome_consultado, esquerda
    return nome_consultado, None


def parse_ligamagic_html(html: str, nome_consultado: str) -> ResultadoLigaMagic:
    edicoes = extrair_cards_editions(html)
    nome_en, nome_pt = _nomes_da_pagina(html, nome_consultado)

    id_principal = None
    try:
        parametro = _extrair_variavel_json(html, "param")
        id_principal = int(parametro.get("card", {}).get("id"))
    except (ValueError, TypeError, AttributeError):
        pass

    cotacoes: list[tuple[float, float, float, dict[str, Any]]] = []
    for edicao in edicoes:
        if id_principal is not None:
            try:
                if int(edicao.get("idcard", -1) or -1) != id_principal:
                    continue
            except (TypeError, ValueError):
                continue
        if _edicao_especial_ou_digital(edicao):
            continue
        preco = _preco_regular(edicao)
        if preco:
            cotacoes.append((*preco, edicao))

    if not cotacoes:
        return ResultadoLigaMagic(
            nome_en=nome_en,
            nome_pt=nome_pt,
            preco_minimo=None,
            preco_medio=None,
            preco_maximo=None,
            imagem=None,
            edicao_referencia=None,
            status="sem_cotacao",
            detalhe="Nenhuma cotação válida foi encontrada nas edições em papel.",
        )

    minimo, medio, maximo, edicao = min(cotacoes, key=lambda item: item[1])
    imagem = edicao.get("img")
    if isinstance(imagem, str) and imagem.startswith("//"):
        imagem = "https:" + imagem
    elif not isinstance(imagem, str) or not imagem.startswith(("http://", "https://")):
        imagem = None

    return ResultadoLigaMagic(
        nome_en=nome_en,
        nome_pt=nome_pt,
        preco_minimo=minimo,
        preco_medio=medio,
        preco_maximo=maximo,
        imagem=imagem,
        edicao_referencia=html_lib.unescape(str(edicao.get("name", ""))) or None,
        status="ok",
    )


async def _completar_imagem_scryfall(
    resultado: ResultadoLigaMagic, nome: str, client: httpx.AsyncClient
) -> ResultadoLigaMagic:
    try:
        response = await client.get(
            SCRYFALL_URL,
            params={"exact": nome},
            headers={"Accept": "application/json;q=0.9,*/*;q=0.8"},
        )
        response.raise_for_status()
        dados = response.json()

        imagens = dados.get("image_uris")
        if not isinstance(imagens, dict):
            faces = dados.get("card_faces")
            if isinstance(faces, list) and faces and isinstance(faces[0], dict):
                imagens = faces[0].get("image_uris")

        imagem = imagens.get("normal") if isinstance(imagens, dict) else None
        if not isinstance(imagem, str) or not imagem.startswith("https://"):
            return resultado

        nome_pt = dados.get("printed_name")
        return replace(
            resultado,
            nome_en=str(dados.get("name") or resultado.nome_en),
            nome_pt=str(nome_pt) if nome_pt else resultado.nome_pt,
            imagem=imagem,
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return resultado


async def consultar_carta(
    nome: str, client: httpx.AsyncClient | None = None
) -> ResultadoLigaMagic:
    chave = nome.casefold().strip()
    agora = time.monotonic()
    item_cache = _cache.get(chave)
    if item_cache and agora - item_cache[0] < CACHE_TTL_SEGUNDOS:
        return item_cache[1]

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT}, timeout=15.0, follow_redirects=True
        )

    try:
        assert client is not None
        async with _semaforo:
            for tentativa in range(MAX_TENTATIVAS_RATE_LIMIT):
                await _aguardar_janela_de_requisicao()
                response = await client.get(
                    LIGAMAGIC_URL, params={"card": nome, "view": "cards/card"}
                )
                if response.status_code != 429:
                    response.raise_for_status()
                    break

                retry_after = response.headers.get("Retry-After")
                try:
                    espera = max(float(retry_after or 0), float(2 ** (tentativa + 1)))
                except ValueError:
                    espera = float(2 ** (tentativa + 1))
                await _aplicar_cooldown(espera)
            else:
                response.raise_for_status()
        resultado = parse_ligamagic_html(response.text, nome)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        resultado = ResultadoLigaMagic(
            nome_en=nome,
            nome_pt=None,
            preco_minimo=None,
            preco_medio=None,
            preco_maximo=None,
            imagem=None,
            edicao_referencia=None,
            status="erro_consulta",
            detalhe=f"Não foi possível consultar ou interpretar a LigaMagic: {exc}",
        )
    try:
        if resultado.imagem is None:
            assert client is not None
            resultado = await _completar_imagem_scryfall(resultado, nome, client)
    finally:
        if owns_client:
            await client.aclose()

    _cache[chave] = (agora, resultado)
    return resultado
