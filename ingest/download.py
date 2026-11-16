import logging

import httpx

from . import config

log = logging.getLogger(__name__)


def baixar_lei(forcar: bool = False):
    """Baixa o texto da Lei 14.133/2021 do Planalto para data/."""
    destino = config.DATA_DIR / config.LEI_ARQUIVO
    if destino.exists() and not forcar:
        return destino

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    log.info("baixando %s", config.LEI_URL)
    resp = httpx.get(
        config.LEI_URL,
        headers={"User-Agent": "rag-licitacoes/1.0"},
        follow_redirects=True,
        timeout=60,
    )
    resp.raise_for_status()
    destino.write_bytes(resp.content)
    log.info("salvo em %s (%d KB)", destino, len(resp.content) // 1024)
    return destino
