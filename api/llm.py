import os

import httpx

BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY", "")
MODELO = os.getenv("LLM_MODEL", "gpt-4o-mini")

SISTEMA = (
    "Você responde perguntas sobre licitações e contratos públicos no Brasil usando "
    "somente os trechos fornecidos. Cite o artigo entre colchetes, por exemplo [Art. 75]. "
    "Se os trechos não bastarem para responder, diga que não encontrou na base. "
    "Não invente valores, prazos ou artigos. Responda em português, de forma direta."
)


def habilitado() -> bool:
    return bool(API_KEY)


def gerar(pergunta: str, trechos: list[tuple[str, str]]) -> str:
    contexto = "\n\n".join(f"[{rotulo}]\n{texto}" for rotulo, texto in trechos)
    resp = httpx.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": MODELO,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SISTEMA},
                {
                    "role": "user",
                    "content": f"Trechos:\n\n{contexto}\n\nPergunta: {pergunta}",
                },
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
