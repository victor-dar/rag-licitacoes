from pydantic import BaseModel, Field


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(5, ge=1, le=10)


class Fonte(BaseModel):
    rotulo: str
    artigo: str | None = None
    contexto: str = ""
    trecho: str
    score: float | None = None
    origem: str = ""


class Resposta(BaseModel):
    resposta: str
    modo: str  # "llm" ou "extrativo"
    fontes: list[Fonte]


class Busca(BaseModel):
    fontes: list[Fonte]
