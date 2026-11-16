import re

from qdrant_client import QdrantClient, models

from ingest import config
from ingest.embeddings import embed_consulta

RE_ARTIGO_CITADO = re.compile(r"\bart(?:igos?)?\.?\s*(\d{1,3})\b", re.IGNORECASE)

_client: QdrantClient | None = None


def cliente() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=config.QDRANT_URL)
    return _client


def colecao_pronta() -> bool:
    try:
        c = cliente()
        return c.collection_exists(config.COLLECTION) and (
            c.count(config.COLLECTION).count > 0
        )
    except Exception:
        return False


def rotulo(payload: dict) -> str:
    if payload.get("artigo"):
        return f"Art. {payload['artigo']}"
    return f"{payload.get('fonte', 'doc')} #{payload.get('parte')}"


def buscar(pergunta: str, k: int = 5) -> list[dict]:
    """Busca vetorial. Se a pergunta citar um artigo ("o que diz o art. 75?"),
    os chunks desse artigo entram primeiro, porque embedding não é bom em número."""
    c = cliente()
    vetor = embed_consulta(pergunta).tolist()
    semanticos = c.query_points(
        config.COLLECTION, query=vetor, limit=k, with_payload=True
    ).points

    resultado: list[dict] = []
    vistos: set = set()

    citados = [int(n) for n in RE_ARTIGO_CITADO.findall(pergunta)]
    if citados:
        pts, _ = c.scroll(
            config.COLLECTION,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="artigo_num", match=models.MatchAny(any=citados)
                    )
                ]
            ),
            limit=3 * len(citados),
            with_payload=True,
        )
        for p in sorted(pts, key=lambda p: (p.payload["artigo_num"], p.payload["parte"])):
            vistos.add(p.id)
            resultado.append({"id": p.id, "score": None, "payload": p.payload})

    for p in semanticos:
        if p.id not in vistos:
            vistos.add(p.id)
            resultado.append({"id": p.id, "score": p.score, "payload": p.payload})

    return resultado[:k]
