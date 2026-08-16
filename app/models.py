from typing import Literal

from pydantic import BaseModel, Field


class DeckResumo(BaseModel):
    nome: str
    formato: str | None = None
    url: str
    main_deck_cartas: int
    sideboard_cartas: int
    preco_mtggoldfish_usd: float


class PrecoLigaMagic(BaseModel):
    preco_minimo: float
    preco_medio: float
    preco_maximo: float
    edicao_referencia: str | None = None


class SubtotalCarta(BaseModel):
    minimo: float
    medio: float
    maximo: float


class CartaResposta(BaseModel):
    nome: str
    nome_pt: str | None = None
    quantidade_main: int
    quantidade_sideboard: int
    quantidade_total: int
    imagem: str | None = None
    ligamagic: PrecoLigaMagic | None = None
    subtotal: SubtotalCarta | None = None
    status: Literal["ok", "sem_cotacao", "erro_consulta"]
    detalhe: str | None = None


class BrasilResumo(BaseModel):
    total_minimo_brl: float
    total_medio_brl: float
    total_maximo_brl: float
    cartas_com_cotacao: int = Field(description="Quantidade de nomes de cartas com cotação.")
    cartas_sem_cotacao: int = Field(description="Quantidade de nomes de cartas sem cotação.")


class ImportacaoResumo(BaseModel):
    deck_usd: float
    frete_usd: float
    total_usd: float
    cotacao_usd_brl: float
    total_brl: float
    fonte_cotacao: str
    aviso: str


class ComparacaoResumo(BaseModel):
    mais_barato: Literal["brasil", "importacao", "empate", "indisponivel"]
    referencia_brasil: str
    diferenca_brl: float
    confiavel: bool
    observacao: str | None = None


class AnaliseDeckResposta(BaseModel):
    deck: DeckResumo
    brasil: BrasilResumo
    importacao: ImportacaoResumo
    comparacao: ComparacaoResumo
    cartas: list[CartaResposta]
    avisos: list[str]
