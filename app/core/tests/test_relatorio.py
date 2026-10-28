import io
from datetime import datetime

import pytest
from openpyxl import load_workbook

from app.core.relatorio import (
    Coluna,
    FormatoRelatorio,
    Tabela,
    TipoColuna,
    gerar_arquivo,
    resposta_arquivo,
)


@pytest.fixture
def tabela():
    return Tabela(
        titulo="Relatório de Teste",
        colunas=[
            Coluna("Nome"),
            Coluna("Data", TipoColuna.DATA),
            Coluna("Criado", TipoColuna.DATA_HORA),
            Coluna("Valor", TipoColuna.MOEDA),
        ],
        linhas=[
            ['Ação; "cível"', datetime(2026, 10, 30), datetime(2026, 10, 1, 9, 5), 1234567.5],
            ['=HYPERLINK("http://x")', None, None, 0.0],
        ],
        resumo=[("Saldo", 10.5)],
    )


def test_csv_usa_ponto_e_virgula_bom_e_formatos_brasileiros(tabela):
    arquivo = gerar_arquivo(tabela, FormatoRelatorio.CSV)

    assert arquivo.media_type.startswith("text/csv")
    assert arquivo.conteudo.startswith(b"\xef\xbb\xbf")
    linhas = arquivo.conteudo.decode("utf-8-sig").splitlines()
    assert linhas[0] == "Nome;Data;Criado;Valor"
    assert linhas[1] == '"Ação; ""cível""";30/10/2026;01/10/2026 09:05;1.234.567,50'


def test_csv_neutraliza_formulas_e_aceita_vazios(tabela):
    linhas = gerar_arquivo(tabela, FormatoRelatorio.CSV).conteudo.decode("utf-8-sig").splitlines()

    assert linhas[2].startswith("\"'=HYPERLINK(")
    assert linhas[2].endswith(";;;0,00")


def test_xlsx_preserva_tipos_formatos_e_resumo(tabela):
    arquivo = gerar_arquivo(tabela, FormatoRelatorio.XLSX)

    planilha = load_workbook(io.BytesIO(arquivo.conteudo)).active
    assert planilha.title == "Relatório de Teste"
    assert [c.value for c in planilha[1]] == ["Nome", "Data", "Criado", "Valor"]
    assert planilha["A1"].font.bold
    assert planilha["B2"].value == datetime(2026, 10, 30)
    assert planilha["B2"].number_format == "DD/MM/YYYY"
    assert planilha["D2"].value == 1234567.5
    assert "R$" in planilha["D2"].number_format
    assert planilha["A3"].value.startswith("'=HYPERLINK(")
    assert planilha["B3"].value is None
    assert (planilha["A5"].value, planilha["B5"].value) == ("Saldo", 10.5)


def test_pdf_e_um_documento_valido(tabela):
    arquivo = gerar_arquivo(tabela, FormatoRelatorio.PDF)

    assert arquivo.media_type == "application/pdf"
    assert arquivo.conteudo.startswith(b"%PDF")


def test_pdf_aceita_texto_com_marcacao_e_tabela_vazia():
    tabela = Tabela(
        titulo="<b>Vazio</b> & cia",
        colunas=[Coluna("A <i>")],
        linhas=[["<script>&"]],
        resumo=[("Total <x>", "texto")],
    )

    assert gerar_arquivo(tabela, FormatoRelatorio.PDF).conteudo.startswith(b"%PDF")
    vazio = Tabela(titulo="Vazio", colunas=[Coluna("A")], linhas=[])
    for formato in FormatoRelatorio:
        assert gerar_arquivo(vazio, formato).conteudo


def test_resposta_define_download_com_nome_do_arquivo(tabela):
    resposta = resposta_arquivo(gerar_arquivo(tabela, FormatoRelatorio.CSV), "processos")

    disposicao = resposta.headers["content-disposition"]
    assert disposicao.startswith('attachment; filename="processos_')
    assert disposicao.endswith('.csv"')
