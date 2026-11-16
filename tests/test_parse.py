from ingest.parse import extrair_chunks, html_para_linhas

HTML = """
<html><body>
<p>Presidência da República</p>
<p>LEI Nº 14.133, DE 1º DE ABRIL DE 2021</p>
<p>TÍTULO I</p>
<p>DISPOSIÇÕES PRELIMINARES</p>
<p>CAPÍTULO I</p>
<p>DO ÂMBITO DE APLICAÇÃO DESTA LEI</p>
<p>Art. 1º Esta Lei estabelece normas gerais de licitação e contratação.</p>
<p>§ 1º Subordinam-se ao regime desta Lei os órgãos da administração.</p>
<p><strike>§ 2º Texto revogado que não deve aparecer.</strike></p>
<p>Art. 2º Esta Lei aplica-se a:</p>
<p>I - alienação e concessão de direito real de uso de bens;</p>
<p>CAPÍTULO II</p>
<p>DOS PRINCÍPIOS</p>
<p>Art. 5º Na aplicação desta Lei, serão observados os princípios da legalidade.</p>
<p>Art. 75-A. Artigo com sufixo de letra.</p>
<p>Brasília, 1º de abril de 2021; 200º da Independência.</p>
<p>Art. 999 Isto vem depois da assinatura e deve ser ignorado.</p>
</body></html>
"""


def _chunks():
    return extrair_chunks(html_para_linhas(HTML), "Lei 14.133/2021", "teste.html")


def test_um_chunk_por_artigo():
    assert [c.meta["artigo"] for c in _chunks()] == ["1", "2", "5", "75-A"]


def test_texto_tachado_e_ignorado():
    art1 = _chunks()[0].texto
    assert "§ 1º" in art1
    assert "revogado" not in art1


def test_contexto_de_capitulo_e_titulo():
    ctx = _chunks()[0].meta["contexto"]
    assert "TÍTULO I - DISPOSIÇÕES PRELIMINARES" in ctx
    assert "CAPÍTULO I - DO ÂMBITO" in ctx
    assert "CAPÍTULO II" in _chunks()[2].meta["contexto"]
    assert "CAPÍTULO I -" not in _chunks()[2].meta["contexto"]


def test_para_na_assinatura():
    assert all(c.meta["artigo_num"] != 999 for c in _chunks())


def test_artigo_longo_e_dividido_com_caput():
    incisos = [f"{i} - item numero {i} com um texto razoavelmente comprido para ocupar espaço" for i in range(1, 80)]
    linhas = ["Art. 6º Para os fins desta Lei, consideram-se:"] + incisos
    # precisa de pelo menos 3 artigos para não cair no chunking genérico
    linhas += ["Art. 7º a.", "Art. 8º b."]
    chunks = [c for c in extrair_chunks(linhas, "Lei X", "x.txt") if c.meta["artigo_num"] == 6]
    assert len(chunks) > 1
    assert all(c.texto.startswith("Art. 6º Para os fins") for c in chunks)
    assert chunks[-1].meta["partes"] == len(chunks)
    achados = {l for c in chunks for l in c.texto.splitlines()}
    assert all(i in achados for i in incisos)


def test_documento_sem_artigos_usa_chunking_generico():
    linhas = [f"Cláusula {i}. Objeto do contrato número {i}." * 3 for i in range(40)]
    chunks = extrair_chunks(linhas, "Edital", "edital.pdf")
    assert len(chunks) > 1
    assert chunks[0].meta["artigo"] is None
