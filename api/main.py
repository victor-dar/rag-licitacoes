import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

from ingest import config
from ingest.embeddings import get_modelo
from ingest.pipeline import indexar

from . import llm, retrieval
from .schemas import Busca, Fonte, Pergunta, Resposta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
_reindex_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_modelo()  # carrega o modelo antes da primeira requisição
    yield


app = FastAPI(title="RAG Licitações", version="1.0.0", lifespan=lifespan)


def _fontes(achados: list[dict]) -> list[Fonte]:
    return [
        Fonte(
            rotulo=retrieval.rotulo(a["payload"]),
            artigo=a["payload"].get("artigo"),
            contexto=a["payload"].get("contexto", ""),
            trecho=a["payload"]["texto"],
            score=round(a["score"], 4) if a["score"] is not None else None,
            origem=a["payload"].get("lei", ""),
        )
        for a in achados
    ]


def _exigir_base():
    if not retrieval.colecao_pronta():
        raise HTTPException(503, "base ainda vazia ou indisponível, aguarde a indexação")


@app.get("/health")
def health():
    return {"status": "ok", "base_pronta": retrieval.colecao_pronta(), "llm": llm.habilitado()}


@app.post("/search", response_model=Busca)
def search(req: Pergunta):
    _exigir_base()
    return Busca(fontes=_fontes(retrieval.buscar(req.pergunta, req.top_k)))


@app.post("/ask", response_model=Resposta)
def ask(req: Pergunta):
    _exigir_base()
    achados = retrieval.buscar(req.pergunta, req.top_k)
    fontes = _fontes(achados)

    if llm.habilitado():
        try:
            texto = llm.gerar(req.pergunta, [(f.rotulo, f.trecho) for f in fontes])
            return Resposta(resposta=texto, modo="llm", fontes=fontes)
        except Exception as e:
            log.warning("falha no LLM, devolvendo trechos: %s", e)

    principal = fontes[0].rotulo if fontes else "nenhum trecho"
    return Resposta(
        resposta=(
            "Resposta gerada sem LLM: os trechos mais relevantes estão em 'fontes'. "
            f"O mais próximo da pergunta é o {principal}."
        ),
        modo="extrativo",
        fontes=fontes,
    )


def _reindexar():
    if not _reindex_lock.acquire(blocking=False):
        log.info("reindexação já em andamento")
        return
    try:
        total = indexar()
        log.info("reindexação concluída: %d chunks", total)
    except Exception:
        log.exception("falha na reindexação")
    finally:
        _reindex_lock.release()


@app.post("/reindex", status_code=202)
def reindex(tasks: BackgroundTasks, x_admin_token: str = Header(default="")):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "token inválido")
    tasks.add_task(_reindexar)
    return {"status": "reindexação iniciada"}
