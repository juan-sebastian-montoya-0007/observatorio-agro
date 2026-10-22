from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import session_factory
from app.services.importer.contracts import WorkbookContractError
from app.services.importer.import_service import EVAImportService, ImportFailed, ImportResult


def main(argv: Sequence[str] | None = None, *, session: Session | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eva")
    commands = parser.add_subparsers(dest="command", required=True)
    import_parser = commands.add_parser("import", help="Import a local EVA XLSX workbook")
    import_parser.add_argument("--path", type=Path, required=True)
    arguments = parser.parse_args(argv)

    if arguments.command != "import":
        parser.error("Unsupported command")

    if session is not None:
        return _run_import(arguments.path, session)

    with session_factory() as managed_session:
        return _run_import(arguments.path, managed_session)


def cli() -> None:
    raise SystemExit(main())


def _run_import(path: Path, session: Session) -> int:
    try:
        result = EVAImportService(session).import_file(path)
    except WorkbookContractError as error:
        _print_json({"status": "CONTRACT_ERROR", "code": error.code, "message": str(error)})
        return 2
    except ImportFailed as error:
        _print_json({"status": "FAILED", "code": error.code, "message": str(error)})
        return 3

    _print_json(_result_payload(result))
    return 0


def _result_payload(result: ImportResult) -> dict[str, object]:
    return {
        "status": result.status,
        "source_version_id": result.source_version_id,
        "import_run_id": result.import_run_id,
        "read_count": result.read_count,
        "inserted_count": result.inserted_count,
        "warning_count": result.warning_count,
        "reused": result.reused,
        "reconciliation": {
            "passed": result.reconciliation.passed,
            "page_rows": result.reconciliation.page_rows,
            "control_rows": result.reconciliation.control_rows,
            "mismatch_count": len(result.reconciliation.mismatches),
        },
    }


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
