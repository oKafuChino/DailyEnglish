from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from app.domain.time import UTC
from app.services.excel_export import build_favorite_words_xlsx


def test_build_favorite_words_xlsx_contains_expected_sheet_data() -> None:
    favorite = SimpleNamespace(
        created_at=datetime(2026, 7, 11, 8, 30, tzinfo=UTC),
        content=SimpleNamespace(
            text_en="resilient",
            phonetic="/rɪˈzɪliənt/",
            part_of_speech="adjective",
            difficulty="B2",
            translation_zh="有韧性的",
            example_en="She remained resilient after the setback.",
        ),
    )

    data = build_favorite_words_xlsx([favorite])

    assert data.startswith(b"PK")
    with ZipFile(BytesIO(data)) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "resilient" in sheet
    assert "有韧性的" in sheet
    assert "She remained resilient" in sheet
