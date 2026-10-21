"""Gera looker/painel_sheets.xlsx: um workbook mínimo em que cada aba importa um CSV enxuto do site
(dashboard/data/sheets/*.csv) via IMPORTDATA. Subido ao Google Drive como Planilha Google, vira a
ponte gratuita entre o site e o Looker Studio (o Sheets reexecuta IMPORTDATA ~a cada hora).

Uso: python looker/make_sheet.py  (depois: enviar o .xlsx ao Drive e abrir como Planilha Google)
"""
import base64
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

BASE = "https://dudaroeira.github.io/painel-imobiliario/data/sheets/"
SHEETS = ["credito_contratado", "credito_taxa_ltv", "credito_indexador", "credito_carteira",
          "credito_inadimplencia", "funding", "oferta_cbic", "oferta_amostras", "precos",
          "imoveis", "macro_custos", "series", "indicadores"]
OUT = Path(__file__).with_name("painel_sheets.xlsx")


def formula(name: str) -> str:
    # locale en_US: o CSV usa ponto decimal; sem isso uma planilha pt-BR lê "9.1" como data (9/jan)
    return f'IMPORTDATA("{BASE}{name}.csv", ",", "en_US")'


def build() -> bytes:
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(SHEETS)))
                   + '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{n}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, n in enumerate(SHEETS))
                   + '</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>' for i in range(len(SHEETS)))
                   + '</Relationships>')
        for i, n in enumerate(SHEETS):
            z.writestr(f"xl/worksheets/sheet{i+1}.xml",
                       '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                       '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                       f'<row r="1"><c r="A1"><f>{escape(formula(n))}</f></c></row>'
                       '</sheetData></worksheet>')
    return buf.getvalue()


if __name__ == "__main__":
    data = build()
    OUT.write_bytes(data)
    print(f"{OUT} ({len(data)} bytes)", file=sys.stderr)
    if "--b64" in sys.argv:
        print(base64.b64encode(data).decode())
