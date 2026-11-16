"""Avalia só a recuperação: o artigo certo aparece entre os top-k trechos?

Mede hit@1, hit@3, hit@5 e MRR sobre eval/perguntas.jsonl. Não depende de LLM,
então o resultado é determinístico e barato de reproduzir.

    python eval/run_eval.py            # API em http://localhost:8000
    API_URL=http://host:8000 python eval/run_eval.py
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")
AQUI = Path(__file__).parent
K = 5


def artigos_unicos(fontes: list[dict]) -> list[int]:
    """Ordem de aparição dos artigos, sem repetir (um artigo longo gera vários chunks)."""
    vistos: list[int] = []
    for f in fontes:
        if not f.get("artigo"):
            continue
        n = int("".join(ch for ch in f["artigo"].split("-")[0] if ch.isdigit()))
        if n not in vistos:
            vistos.append(n)
    return vistos


def main() -> int:
    casos = [json.loads(l) for l in (AQUI / "perguntas.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    posicoes: list[int | None] = []
    erros = []
    for caso in casos:
        r = httpx.post(f"{API_URL}/search", json={"pergunta": caso["pergunta"], "top_k": K}, timeout=60)
        r.raise_for_status()
        ranking = artigos_unicos(r.json()["fontes"])
        pos = next((i + 1 for i, a in enumerate(ranking) if a in caso["artigos"]), None)
        posicoes.append(pos)
        if pos is None or pos > 1:
            erros.append((caso, ranking, pos))

    n = len(casos)
    hit = lambda k: sum(1 for p in posicoes if p is not None and p <= k) / n
    mrr = sum(1 / p for p in posicoes if p) / n

    linhas = [
        f"Avaliação de recuperação em {date.today().isoformat()} ({n} perguntas)",
        "",
        "| métrica | valor |",
        "|---|---|",
        f"| hit@1 | {hit(1):.2f} |",
        f"| hit@3 | {hit(3):.2f} |",
        f"| hit@5 | {hit(5):.2f} |",
        f"| MRR   | {mrr:.2f} |",
        "",
        "Perguntas em que o artigo esperado não ficou em 1º lugar:",
        "",
    ]
    for caso, ranking, pos in erros:
        linhas.append(f"- {caso['pergunta']}")
        linhas.append(f"  esperado: {caso['artigos']} | recuperado: {ranking} | posição: {pos or 'fora do top-' + str(K)}")

    saida = "\n".join(linhas) + "\n"
    print(saida)
    (AQUI / "resultados.md").write_text(saida, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
