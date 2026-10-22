from collections.abc import Callable, Generator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.models import (
    AgriculturalRecord,
    Crop,
    CropGroup,
    CropSubgroup,
    CropVariant,
    Department,
    Municipality,
    Period,
    PeriodType,
    PhysicalState,
    Source,
    SourceVersion,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
pytest_plugins = ("tests.fixtures.workbooks",)


@pytest.fixture
def client(session: Session) -> Generator[TestClient]:
    application = create_app()

    def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine]:
    test_url = make_url(Settings().test_database_url)
    database_name = test_url.database
    if not database_name:
        raise RuntimeError("TEST_DATABASE_URL must include a database name")

    maintenance_url = test_url.set(database="postgres")
    maintenance_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    quoted_database = maintenance_engine.dialect.identifier_preparer.quote(database_name)

    with maintenance_engine.connect() as connection:
        connection.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :database_name AND pid <> pg_backend_pid()"
            ),
            {"database_name": database_name},
        )
        connection.execute(text(f"DROP DATABASE IF EXISTS {quoted_database}"))
        connection.execute(text(f"CREATE DATABASE {quoted_database}"))

    engine = create_engine(test_url, pool_pre_ping=True)
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "sqlalchemy.url",
        test_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    with engine.begin() as connection:
        alembic_config.attributes["connection"] = connection
        command.upgrade(alembic_config, "head")

    try:
        yield engine
    finally:
        engine.dispose()
        with maintenance_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": database_name},
            )
            connection.execute(text(f"DROP DATABASE IF EXISTS {quoted_database}"))
        maintenance_engine.dispose()


@pytest.fixture
def migrated_connection(test_engine: Engine):
    with test_engine.connect() as connection:
        yield connection


@pytest.fixture
def session(test_engine: Engine) -> Generator[Session]:
    with test_engine.connect() as connection:
        transaction = connection.begin()
        db_session = Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield db_session
        finally:
            db_session.close()
            transaction.rollback()


@pytest.fixture
def imported_dataset(session: Session, valid_workbook):
    from app.services.importer.import_service import EVAImportService

    return EVAImportService(session).import_file(valid_workbook)


@pytest.fixture
def fact_factory(session: Session) -> Callable[..., AgriculturalRecord]:
    source = Source(id=1, name="EVA", publisher="UPRA")
    source_version = SourceVersion(
        id=1,
        source=source,
        version_label="2019-2025",
        coverage_start_year=2019,
        coverage_end_year=2025,
        sha256="a" * 64,
        file_name="fixture.xlsx",
    )
    department = Department(code="05", name="ANTIOQUIA")
    municipality = Municipality(id=1, code="05001", name="MEDELLÍN", department=department)
    group = CropGroup(id=1, name="ALIMENTARIOS")
    subgroup = CropSubgroup(id=1, name="TUBÉRCULOS", group=group)
    crop = Crop(
        id=1,
        base_code="10807",
        name="PAPA",
        cycle="TRANSITORIO",
        group=group,
        subgroup=subgroup,
        general_classification="ALIMENTARIOS",
    )
    variants = [
        CropVariant(
            id=1,
            crop=crop,
            source_code="1080701",
            disaggregation="PAPA CRIOLLA",
            scientific_name="Solanum phureja",
        ),
        CropVariant(
            id=2,
            crop=crop,
            source_code="1080702",
            disaggregation="PAPA CAPIRA",
            scientific_name="Solanum tuberosum",
        ),
    ]
    physical_state = PhysicalState(id=1, name="EN FRESCO")
    period = Period(
        id=1,
        year=2025,
        period_type=PeriodType.ANNUAL,
        original_label="2025",
        chronological_order=202500,
    )
    session.add_all([source_version, municipality, crop, *variants, physical_state, period])
    session.commit()

    defaults: dict[str, Any] = {
        "source_version_id": 1,
        "municipality_id": 1,
        "crop_variant_id": 1,
        "period_id": 1,
        "physical_state_id": 1,
        "planted_area_ha": Decimal("10.0000"),
        "harvested_area_ha": Decimal("9.0000"),
        "production_t": Decimal("18.0000"),
        "reported_yield_t_ha": Decimal("2.0000"),
        "source_row": 10,
        "trace_metadata": {"sheet": "BasePagina"},
    }

    def factory(**overrides: Any) -> AgriculturalRecord:
        return AgriculturalRecord(**(defaults | overrides))

    return factory
