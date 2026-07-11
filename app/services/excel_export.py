from datetime import datetime
from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.db.models import Favorite


def build_favorite_words_xlsx(favorites: list[Favorite]) -> bytes:
    rows = [
        ["单词", "音标", "词性", "难度", "中文释义", "英文例句", "收藏时间"],
        *[
            [
                favorite.content.text_en,
                favorite.content.phonetic or "",
                favorite.content.part_of_speech or "",
                favorite.content.difficulty or "",
                favorite.content.translation_zh,
                favorite.content.example_en or "",
                format_datetime(favorite.created_at),
            ]
            for favorite in favorites
        ],
    ]
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml())
        archive.writestr("_rels/.rels", package_rels_xml())
        archive.writestr("xl/workbook.xml", workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml(rows))
        archive.writestr("xl/styles.xml", styles_xml())
    return buffer.getvalue()


def format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def cell_ref(row_index: int, column_index: int) -> str:
    column = ""
    index = column_index
    while index:
        index, remainder = divmod(index - 1, 26)
        column = chr(65 + remainder) + column
    return f"{column}{row_index}"


def sheet_xml(rows: list[list[str]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        style = ' s="1"' if row_index == 1 else ""
        for column_index, value in enumerate(row, start=1):
            cells.append(
                f'<c r="{cell_ref(row_index, column_index)}" t="inlineStr"{style}>'
                f"<is><t>{escape(str(value))}</t></is></c>"
            )
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        "<cols>"
        '<col min="1" max="1" width="18" customWidth="1"/>'
        '<col min="2" max="4" width="14" customWidth="1"/>'
        '<col min="5" max="6" width="48" customWidth="1"/>'
        '<col min="7" max="7" width="18" customWidth="1"/>'
        "</cols>"
        f"<sheetData>{''.join(row_xml)}</sheetData>"
        "</worksheet>"
    )


def content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )


def package_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def workbook_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="收藏单词" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def workbook_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        "</styleSheet>"
    )
