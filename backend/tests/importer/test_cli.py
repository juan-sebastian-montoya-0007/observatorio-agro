import json

from app.cli import main


def test_cli_import_prints_json_summary_without_source_rows(
    session,
    valid_workbook,
    capsys,
):
    exit_code = main(["import", "--path", str(valid_workbook)], session=session)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "IMPORTED"
    assert payload["inserted_count"] == 2
    assert "rows" not in payload
    assert "records" not in payload


def test_cli_contract_error_returns_code_2(session, tmp_path, capsys):
    exit_code = main(["import", "--path", str(tmp_path / "missing.xlsx")], session=session)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["code"] == "FILE_NOT_FOUND"


def test_cli_data_error_returns_code_3(session, duplicate_key_workbook, capsys):
    exit_code = main(
        ["import", "--path", str(duplicate_key_workbook)],
        session=session,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["code"] == "DUPLICATE_FACT_KEY"
