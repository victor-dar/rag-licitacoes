import logging
import time
import uuid

from qdrant_client import QdrantClient, models

from . import config
from .download import baixar_lei
from .embeddings import dimensao, embed_passagens
from .parse import Chunk, carregar_linhas, extrair_chunks

log = logging.getLogger(__name__)

EXTENSOES = {".html", ".htm", ".txt", ".pdf"}
NS = uuid.UUID("6f1c2d52-8d0e-4b0b-9a53-0d6e7c1f7a11")


def conectar(tentativas: int = 30) -> QdrantClient:
    client = QdrantClient(url=config.QDRANT_URL)
    for i in range(tentativas):
        try:
            client.get_collections()
            return client
        except Exception:
            log.info("aguardando qdrant (%d/%d)", i + 1, tentativas)
            time.sleep(2)
    raise RuntimeError(f"qdrant não respondeu em {config.QDRANT_URL}")


def nome_da_lei(arquivo: str) -> str:
    if "14133" in arquivo:
        return "Lei 14.133/2021"
    return arquivo.rsplit(".", 1)[0]


def construir_chunks() -> list[Chunk]:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(
        p for p in config.DATA_DIR.iterdir() if p.suffix.lower() in EXTENSOES
    )
    if not arquivos:
        arquivos = [baixar_lei()]

    todos: list[Chunk] = []
    for caminho in arquivos:
        linhas = carregar_linhas(caminho)
        chunks = extrair_chunks(linhas, nome_da_lei(caminho.name), caminho.name)
        log.info("%s: %d linhas -> %d chunks", caminho.name, len(linhas), len(chunks))
        todos.extend(chunks)
    return todos


def indexar() -> int:
    chunks = construir_chunks()
    if not chunks:
        raise RuntimeError("nenhum chunk gerado, confira o conteúdo de data/")

    client = conectar()
    if client.collection_exists(config.COLLECTION):
        client.delete_collection(config.COLLECTION)
    client.create_collection(
        config.COLLECTION,
        vectors_config=models.VectorParams(
            size=dimensao(), distance=models.Distance.COSINE
        ),
    )
    client.create_payload_index(
        config.COLLECTION, "artigo_num", models.PayloadSchemaType.INTEGER
    )

    lote = 64
    for i in range(0, len(chunks), lote):
        parte = chunks[i : i + lote]
        vetores = embed_passagens([c.indexado for c in parte])
        client.upsert(
            config.COLLECTION,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid5(NS, c.id)), vector=v.tolist(), payload=c.meta
                )
                for c, v in zip(parte, vetores)
            ],
        )
        log.info("indexados %d/%d", min(i + lote, len(chunks)), len(chunks))
    return len(chunks)
