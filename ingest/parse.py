"""Leitura de arquivos e chunking.

A estratégia principal é um chunk por artigo. Artigos longos (o art. 6º, por
exemplo, tem dezenas de incisos) são quebrados em blocos menores, e cada bloco
repete o caput para não perder o contexto. Se o documento não tiver estrutura
de artigos (um edital em PDF, por exemplo), cai num chunking por parágrafos.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

MAX_CHARS = 1800
MAX_CHARS_GENERICO = 1200

RE_ARTIGO = re.compile(r"^Art\.?\s*(\d+)\s*[º°o]?(?:\s*-\s*([A-Z]))?\b")
RE_TITULO = re.compile(
    r"^(LIVRO|T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O|SUBSE[ÇC][ÃA]O)\s+([IVXLCDM]+|[ÚU]NICO|\d+)\b",
    re.IGNORECASE,
)
RE_FIM = re.compile(r"^Bras[íi]lia,")

NIVEIS = {"livro": 0, "titulo": 1, "capitulo": 2, "secao": 3, "subsecao": 4}


@dataclass
class Chunk:
    id: str
    texto: str  # o que é mostrado ao usuário
    indexado: str  # o que vira embedding (texto + contexto)
    meta: dict


# ---------------------------------------------------------------- leitura

class _HTMLParaLinhas(HTMLParser):
    BLOCOS = {"p", "div", "br", "li", "tr", "table", "h1", "h2", "h3", "h4", "h5", "h6"}
    IGNORAR = {"strike", "s", "del", "script", "style"}  # texto tachado = revogado

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.linhas: list[str] = []
        self._atual: list[str] = []
        self._ignorando = 0

    def _fechar(self):
        txt = " ".join("".join(self._atual).split())
        if txt:
            self.linhas.append(txt)
        self._atual = []

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORAR:
            self._ignorando += 1
        elif tag in self.BLOCOS:
            self._fechar()

    def handle_endtag(self, tag):
        if tag in self.IGNORAR:
            self._ignorando = max(0, self._ignorando - 1)
        elif tag in self.BLOCOS:
            self._fechar()

    def handle_data(self, data):
        if not self._ignorando:
            self._atual.append(data)

    def close(self):
        super().close()
        self._fechar()


def html_para_linhas(html: str) -> list[str]:
    p = _HTMLParaLinhas()
    p.feed(html)
    p.close()
    return p.linhas


def _decodificar(raw: bytes) -> str:
    # o Planalto serve windows-1252
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def carregar_linhas(caminho: Path) -> list[str]:
    ext = caminho.suffix.lower()
    if ext in (".html", ".htm"):
        return html_para_linhas(_decodificar(caminho.read_bytes()))
    if ext == ".txt":
        texto = _decodificar(caminho.read_bytes())
        return [" ".join(l.split()) for l in texto.splitlines() if l.strip()]
    if ext == ".pdf":
        from pypdf import PdfReader

        linhas = []
        for pagina in PdfReader(str(caminho)).pages:
            for l in (pagina.extract_text() or "").splitlines():
                l = " ".join(l.split())
                if l:
                    linhas.append(l)
        return linhas
    raise ValueError(f"formato não suportado: {caminho.name}")


# --------------------------------------------------------------- chunking

def _sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _dividir(linhas: list[str], limite: int = MAX_CHARS) -> list[list[str]]:
    if sum(len(l) + 1 for l in linhas) <= limite:
        return [linhas]

    caput = linhas[0]
    prefixo = caput if len(caput) <= 300 else caput[:297] + "..."

    partes: list[list[str]] = []
    buf: list[str] = []
    tam = 0
    reais = 0  # linhas do artigo no bloco, sem contar o prefixo repetido
    for l in linhas:
        if reais and tam + len(l) + 1 > limite:
            partes.append(buf)
            buf, tam, reais = [prefixo], len(prefixo) + 1, 0
        buf.append(l)
        tam += len(l) + 1
        reais += 1
    partes.append(buf)
    return partes


def chunks_por_artigo(linhas: list[str], lei: str, fonte: str) -> list[Chunk]:
    niveis: dict[int, str] = {}
    esperando_titulo: int | None = None
    artigos: list[dict] = []
    atual: dict | None = None

    for linha in linhas:
        if RE_FIM.match(linha):
            break

        m = RE_ARTIGO.match(linha)
        if m:
            contexto = " > ".join(niveis[k] for k in sorted(niveis))
            atual = {
                "num": int(m.group(1)),
                "sufixo": m.group(2) or "",
                "contexto": contexto,
                "linhas": [linha],
            }
            artigos.append(atual)
            esperando_titulo = None
            continue

        h = RE_TITULO.match(linha) if len(linha) < 90 else None
        if h:
            nivel = NIVEIS[_sem_acento(h.group(1))]
            niveis = {k: v for k, v in niveis.items() if k < nivel}
            niveis[nivel] = linha
            esperando_titulo = nivel
            atual = None
            continue

        if atual is None:
            if esperando_titulo is not None:
                niveis[esperando_titulo] += " - " + linha
                esperando_titulo = None
            continue

        atual["linhas"].append(linha)

    chunks = []
    for art in artigos:
        rotulo = f"{art['num']}{('-' + art['sufixo']) if art['sufixo'] else ''}"
        partes = _dividir(art["linhas"])
        for i, parte in enumerate(partes, start=1):
            texto = "\n".join(parte)
            cabecalho = lei
            if art["contexto"]:
                cabecalho += f" | {art['contexto']}"
            chunks.append(
                Chunk(
                    id=f"{fonte}:{rotulo}:{i}",
                    texto=texto,
                    indexado=f"{cabecalho}\n{texto}",
                    meta={
                        "lei": lei,
                        "fonte": fonte,
                        "artigo": rotulo,
                        "artigo_num": art["num"],
                        "contexto": art["contexto"],
                        "parte": i,
                        "partes": len(partes),
                        "texto": texto,
                    },
                )
            )
    return chunks


def chunks_genericos(linhas: list[str], lei: str, fonte: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    buf: list[str] = []
    tam = 0

    def fechar():
        if not buf:
            return
        n = len(chunks) + 1
        texto = "\n".join(buf)
        chunks.append(
            Chunk(
                id=f"{fonte}:trecho:{n}",
                texto=texto,
                indexado=f"{lei}\n{texto}",
                meta={
                    "lei": lei,
                    "fonte": fonte,
                    "artigo": None,
                    "artigo_num": None,
                    "contexto": "",
                    "parte": n,
                    "partes": None,
                    "texto": texto,
                },
            )
        )

    for l in linhas:
        if buf and tam + len(l) + 1 > MAX_CHARS_GENERICO:
            fechar()
            buf = buf[-1:]  # uma linha de sobreposição
            tam = sum(len(x) + 1 for x in buf)
        buf.append(l)
        tam += len(l) + 1
    fechar()
    return chunks


def extrair_chunks(linhas: list[str], lei: str, fonte: str) -> list[Chunk]:
    chunks = chunks_por_artigo(linhas, lei, fonte)
    if len({c.meta["artigo_num"] for c in chunks}) >= 3:
        return chunks
    return chunks_genericos(linhas, lei, fonte)
