# EVA Explorer Corte 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar el fundamento ejecutable de EVA Explorer con importación agrícola idempotente y conciliada, una API analítica trazable y el Dashboard institucional conectado exclusivamente a datos reales.

**Architecture:** El monorepositorio separa un frontend Next.js de un backend FastAPI y una base PostgreSQL/PostGIS levantados con Docker Compose. El backend es un monolito modular en capas —routers, servicios de aplicación, repositorios y políticas estadísticas— y el frontend solo accede a datos mediante servicios tipados; el Excel se lee sin modificarlo, se valida y concilia antes de publicar cada versión.

**Tech Stack:** Node.js 24 LTS, Next.js 16.4.2, React 19.3.1, TypeScript 7.0.2, Tailwind CSS 4.3.3, Apache ECharts 6.1.0, Python 3.13, FastAPI 0.158.1, Pydantic 2.14.1, SQLAlchemy 2.1.6, Alembic 1.20.0, Polars 2.0.0, openpyxl 3.1.5, PostgreSQL 18/PostGIS 3.6, pytest, Vitest y Playwright.

**Spec:** `docs/superpowers/specs/2026-10-22-eva-explorer-design.md`

## Global Constraints

- Este plan implementa solo el Corte 1: fundamento, modelo, ETL, conciliación, catálogos, resumen, series, rankings y Dashboard real.
- `/` abre el Dashboard; no se crea landing, autenticación, Redis, colas, microservicios, predicciones ni datos ficticios.
- El archivo `C:\Users\User\Downloads\20260526_BaseAgricola20192025 (2).xlsx` se trata como solo lectura, nunca se modifica ni se añade a Git; su SHA-256 esperado es `355E70A7A5B8F3CE76F26F97463F77C24D4C5E63ABD7B28C9B6395A1F65854B0`.
- `BasePagina` es la fuente factual: 18 columnas y encabezado en la fila 9. `BaseSIPRA` es control de conciliación: 18 columnas y encabezado en la fila 1; nunca se inserta como una segunda tabla de hechos.
- Los códigos DIVIPOLA se conservan como texto de 2 y 5 caracteres; los códigos de cultivo tampoco se convierten a etiquetas visibles para filtrar.
- La clave factual es `(source_version_id, municipality_id, crop_variant_id, period_id, physical_state_id)` y las métricas se almacenan como `NUMERIC`.
- El rendimiento agregado siempre es `SUM(production_t) / SUM(harvested_area_ha)`; si el denominador es cero, el resultado es `null`, no cero.
- El modo `AGRICULTURAL_YEAR` usa anuales para permanentes y semestres para transitorios; cuando una serie transitoria contiene ambos granos, excluye el anual.
- Un esquema incompatible, una clave duplicada, un código territorial inválido o una conciliación fallida cancela todos los hechos de la carga; las cifras inusuales se conservan como advertencias.
- Las respuestas analíticas usan `{data, meta, coverage, warnings, methodology}` y exponen versión de fuente, unidad, filtros y limitaciones.
- El frontend refleja filtros compartidos en la URL, conserva el contexto territorial aplicable y no construye URLs de backend fuera de `frontend/src/services/`.
- La interfaz y los mensajes son español de Colombia; las unidades aparecen en tarjetas, ejes, tooltips y estados vacíos.
- Se fijan dependencias con `uv.lock` y `pnpm-lock.yaml`; Docker usa `postgis/postgis:18-3.6`, Node 24 y Python 3.13.

## Review Focus

- Diferente fila y vocabulario de encabezados entre `BasePagina` y `BaseSIPRA`: aceptar los dos contratos exactos y rechazar cualquier deriva antes de leer hechos; prueba en Task 3.
- Códigos con cero inicial o valor numérico entregado por Excel: normalizar `5`, `05` y `05001` sin producir municipios distintos ni perder anchura; prueba en Task 4.
- Series transitorias con filas anuales y semestrales simultáneas: el modo agrícola debe elegir semestres sin doble conteo y declarar cobertura parcial; prueba en Task 7.
- Cultivos que comparten código base pero difieren en desagregación o nombre científico, y hechos que difieren por estado físico: conservar variantes y claves factuales independientes; pruebas en Tasks 2 y 4.
- Reintento, fallo en un lote o conciliación no conforme: no dejar hechos parciales y hacer idempotente el mismo hash sin ocultar el intento fallido; prueba en Task 6.

---

## File Map

- `docker-compose.yml`, `.env.example`, `.gitignore`: contrato local de los tres servicios y exclusión explícita de datos crudos, secretos y artefactos.
- `backend/app/core/`: configuración y códigos de error; `backend/app/db/`: engine, sesiones y base declarativa.
- `backend/app/models/` y `backend/migrations/`: procedencia, territorio, catálogo agrícola, periodos, hechos e índices.
- `backend/app/services/importer/`: contrato del libro, lectura, normalización, conciliación e importación transaccional.
- `backend/app/statistics/`: reglas puras de grano temporal, rendimiento, cobertura y advertencias.
- `backend/app/repositories/`: SQL de catálogos y agregaciones; `backend/app/services/analytics.py`: orquestación analítica.
- `backend/app/api/v1/`: routers y esquemas HTTP; ningún router contiene SQL ni reglas estadísticas.
- `frontend/src/services/`: único acceso a la API y validación de contratos; `frontend/src/hooks/`: estado de filtros en URL.
- `frontend/src/components/layout/`: armazón institucional; `frontend/src/components/dashboard/`: filtros, KPIs, gráficos, ranking y estados.
- `backend/tests/`, `frontend/src/**/*.test.tsx`, `frontend/e2e/`: unitarias, integración y recorrido real del Dashboard.

### Task 1: Monorepo ejecutable y contratos de salud

**Files:**
- Create: `.gitignore`, `.env.example`, `docker-compose.yml`, `README.md`
- Create: `backend/pyproject.toml`, `backend/uv.lock`, `backend/Dockerfile`, `backend/alembic.ini`
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/db/base.py`, `backend/app/db/session.py`
- Create: `backend/tests/conftest.py`, `backend/tests/api/test_health.py`
- Create: `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/Dockerfile`, `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/postcss.config.mjs`, `frontend/vitest.config.ts`
- Create: `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/globals.css`, `frontend/src/app/page.test.tsx`

**Interfaces:**
- Consumes: ninguna; es la raíz del corte.
- Produces: `Settings` con `database_url`, `test_database_url`, `cors_origins`, `api_prefix`; `create_app() -> FastAPI`; `GET /health -> {"status":"ok"}`; servicios Compose `db`, `backend`, `frontend`.

- [ ] **Step 1: Write the failing backend health test**

```python
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the backend test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_health.py -v`

Expected: FAIL porque `app.main` todavía no existe.

- [ ] **Step 3: Implement the minimal backend app and configuration**

Crear `Settings` con `pydantic-settings`, una factoría `create_app() -> FastAPI`, CORS limitado a `cors_origins` y un endpoint de salud sin acceso a datos.

- [ ] **Step 4: Write and run the failing frontend route test**

```tsx
expect(screen.getByRole("heading", { name: "EVA Explorer" })).toBeVisible();
expect(screen.getByText("Cargando datos agrícolas…")).toBeVisible();
```

Run: `cd frontend && pnpm vitest run src/app/page.test.tsx`

Expected: FAIL porque la ruta aún no existe.

- [ ] **Step 5: Implement the minimal root route and deterministic toolchains**

Configurar TypeScript estricto, Tailwind, Vitest/Testing Library y una página sin cifras de muestra. Crear los Dockerfiles, lockfiles, `.env.example`, exclusiones de `backend/data/raw/`, `.env`, `.next`, caches y `.superpowers/`, y Compose con healthcheck de PostgreSQL.

- [ ] **Step 6: Verify the foundation**

Run: `docker compose config`

Expected: configuración válida con tres servicios y volumen de PostgreSQL 18 montado en `/var/lib/postgresql`.

Run: `cd backend && uv run pytest tests/api/test_health.py -v && uv run ruff check .`

Expected: PASS.

Run: `cd frontend && pnpm lint && pnpm vitest run && pnpm build`

Expected: PASS y `/` generado sin datos inventados.

- [ ] **Step 7: Commit**

```bash
git add .gitignore .env.example docker-compose.yml README.md backend frontend
git commit -m "chore: bootstrap EVA Explorer services"
```

### Task 2: Modelo relacional y migración inicial

**Files:**
- Create: `backend/app/models/provenance.py`, `backend/app/models/geography.py`, `backend/app/models/agriculture.py`, `backend/app/models/__init__.py`
- Create: `backend/migrations/env.py`, `backend/migrations/versions/20261022_0001_initial_schema.py`
- Create: `backend/tests/db/test_initial_migration.py`, `backend/tests/db/test_fact_constraints.py`
- Modify: `backend/app/db/base.py`, `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `Settings.test_database_url`, SQLAlchemy `Base` y `session_factory` de Task 1.
- Produces: modelos `Source`, `SourceVersion`, `ImportRun`, `ImportIssue`, `Department`, `Municipality`, `TerritorialGeometry`, `CropGroup`, `CropSubgroup`, `Crop`, `CropVariant`, `PhysicalState`, `Period`, `AgriculturalRecord`; enum `PeriodType`.

- [ ] **Step 1: Write failing migration and uniqueness tests**

```python
def test_initial_migration_creates_postgis_and_all_tables(migrated_connection):
    assert migrated_connection.scalar(text("SELECT postgis_version()"))
    assert EXPECTED_TABLES <= set(inspect(migrated_connection).get_table_names())

def test_fact_key_allows_variants_but_rejects_exact_duplicate(session, fact_factory):
    session.add(fact_factory(crop_variant_id=1, physical_state_id=1))
    session.commit()
    session.add(fact_factory(crop_variant_id=2, physical_state_id=1))
    session.commit()
    with pytest.raises(IntegrityError):
        session.add(fact_factory(crop_variant_id=1, physical_state_id=1))
        session.commit()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/db/test_initial_migration.py tests/db/test_fact_constraints.py -v`

Expected: FAIL por ausencia de migración y modelos.

- [ ] **Step 3: Implement focused ORM models and the initial Alembic migration**

Usar códigos territoriales `VARCHAR(2)`/`VARCHAR(5)`, métricas `NUMERIC(18,4)`, geometría `Geometry(MULTIPOLYGON, 4326)`, hash único en `source_version`, la clave única factual aprobada e índices por versión-periodo-territorio-cultivo.

- [ ] **Step 4: Run migration tests**

Run: `cd backend && uv run alembic upgrade head && uv run pytest tests/db/test_initial_migration.py tests/db/test_fact_constraints.py -v`

Expected: PASS; PostGIS activo y la duplicación exacta rechazada.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/app/db/base.py backend/migrations backend/tests/db
git commit -m "feat: add agricultural provenance data model"
```

### Task 3: Contrato y lector del libro EVA

**Files:**
- Create: `backend/app/services/importer/contracts.py`, `backend/app/services/importer/source_contract.py`, `backend/app/services/importer/reader.py`, `backend/app/services/importer/__init__.py`
- Create: `backend/tests/fixtures/workbooks.py`, `backend/tests/importer/test_reader.py`

**Interfaces:**
- Consumes: una `Path` local de solo lectura.
- Produces: `WorkbookFingerprint(sha256, file_name)`, `ParsedWorkbook(page: pl.DataFrame, control: pl.DataFrame, notes: tuple[str, ...])`, `sha256_file(path: Path) -> str`, `read_eva_workbook(path: Path) -> ParsedWorkbook`, excepciones `WorkbookContractError` con `sheet`, `row` y `field`.

- [ ] **Step 1: Write failing tests for the two exact source contracts**

```python
def test_reader_uses_row_9_for_page_and_row_1_for_control(valid_workbook):
    parsed = read_eva_workbook(valid_workbook)
    assert parsed.page.height == 2
    assert parsed.control.height == 1
    assert parsed.notes[0].startswith("Fuente: EVA -UPRA")

def test_reader_rejects_header_drift_before_returning_rows(workbook_with_changed_header):
    with pytest.raises(WorkbookContractError, match="BasePagina.*Área sembrada"):
        read_eva_workbook(workbook_with_changed_header)
```

- [ ] **Step 2: Run reader tests to verify they fail**

Run: `cd backend && uv run pytest tests/importer/test_reader.py -v`

Expected: FAIL porque no existe el contrato.

- [ ] **Step 3: Implement streaming workbook inspection and reading**

Fijar en `source_contract.py` las cabeceras exactas y en este orden:

```python
BASE_PAGINA_HEADERS = (
    "Código Dane departamento", "Departamento", "Código Dane municipio", "Municipio",
    "Desagregación cultivo", "Cultivo", "Ciclo del cultivo", "Grupo cultivo", "Subgrupo",
    "Año", "Periodo", "Área sembrada (ha)", "Área cosechada (ha)", "Producción (t)",
    "Rendimiento (t/ha)", "Nombre científico del cultivo", "Código del cultivo",
    "Estado físico del cultivo",
)
BASE_SIPRA_HEADERS = (
    "codigoDepartamento", "departamento", "codigoMunicipio", "municipio", "especie",
    "nombre_tipo_ciclo", "grupo_especie", "subGrupo_Especie", "anho", "Periodo",
    "AreaSembrada", "AreaCosechada", "produccio", "rendimiento", "cod_cultiv",
    "nombre_cientifico", "EstadoFisicoProduccio", "Clasifica_grupo",
)
```

Abrir con `openpyxl.load_workbook(read_only=True, data_only=True)`, validar hojas/cabeceras antes de construir DataFrames de Polars y cerrar siempre el libro.

- [ ] **Step 4: Add fingerprint and inaccessible-file cases**

Probar que `sha256_file()` devuelve 64 caracteres y que ruta inexistente, libro corrupto u hoja ausente producen códigos estables `FILE_NOT_FOUND`, `INVALID_WORKBOOK` o `MISSING_SHEET`.

- [ ] **Step 5: Run reader tests**

Run: `cd backend && uv run pytest tests/importer/test_reader.py -v`

Expected: PASS sin crear ni modificar archivos junto a la fuente.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/importer backend/tests/fixtures backend/tests/importer/test_reader.py
git commit -m "feat: validate and read EVA workbooks"
```

### Task 4: Normalización de dimensiones, periodos y métricas

**Files:**
- Create: `backend/app/services/importer/normalizer.py`, `backend/app/services/importer/issues.py`
- Create: `backend/tests/importer/test_normalizer.py`

**Interfaces:**
- Consumes: `ParsedWorkbook` de Task 3.
- Produces: `NormalizedWorkbook(records, control_rows, dimensions, issues)`, `normalize_workbook(parsed: ParsedWorkbook) -> NormalizedWorkbook`, `parse_period(year: int, label: str) -> tuple[int, PeriodType]`, `ImportIssueData(severity, code, sheet, row, field, message)`.

- [ ] **Step 1: Write failing normalization tests**

```python
def test_codes_keep_required_width_and_zero_is_not_missing(parsed_workbook):
    normalized = normalize_workbook(parsed_workbook)
    row = normalized.records.row(0, named=True)
    assert row["department_code"] == "05"
    assert row["municipality_code"] == "05001"
    assert row["planted_area_ha"] == Decimal("0")

def test_variant_identity_keeps_scientific_name_and_physical_state(parsed_potato_workbook):
    normalized = normalize_workbook(parsed_potato_workbook)
    assert normalized.records.select("variant_key").n_unique() == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/importer/test_normalizer.py -v`

Expected: FAIL porque no existe el normalizador.

- [ ] **Step 3: Implement canonical normalization**

Recortar espacios, normalizar códigos con anchura fija sin convertir nombres, parsear `YYYY`, `YYYYA`, `YYYYB`, convertir métricas a `Decimal`, construir la tabla inequívoca de cultivo base desde `BaseSIPRA`, llevar `Clasifica_grupo` a la clasificación general del cultivo y conservar desagregación y nombre científico en la variante; el estado físico se mantiene como dimensión separada de la clave factual.

- [ ] **Step 4: Add fatal and warning cases**

Probar que métrica negativa, periodo incoherente, código DIVIPOLA inválido y mapeo base ambiguo son fatales; `harvested_area_ha > planted_area_ha` produce `HARVESTED_EXCEEDS_PLANTED` con severidad `WARNING` y conserva el registro.

- [ ] **Step 5: Run normalization tests**

Run: `cd backend && uv run pytest tests/importer/test_normalizer.py -v`

Expected: PASS con ceros y códigos preservados.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/importer/normalizer.py backend/app/services/importer/issues.py backend/tests/importer/test_normalizer.py
git commit -m "feat: normalize EVA agricultural records"
```

### Task 5: Conciliación independiente con BaseSIPRA

**Files:**
- Create: `backend/app/services/importer/reconciliation.py`
- Create: `backend/tests/importer/test_reconciliation.py`

**Interfaces:**
- Consumes: `NormalizedWorkbook` de Task 4.
- Produces: `ReconciliationMetric(name, page_value, control_value, difference)`, `ReconciliationReport(passed, page_rows, control_rows, mismatches)`, `reconcile_workbook(workbook: NormalizedWorkbook, tolerance: Decimal = Decimal("0.01")) -> ReconciliationReport`.

- [ ] **Step 1: Write failing exact and mismatch tests**

```python
def test_reconciliation_collapses_variants_to_control_grain(normalized_workbook):
    report = reconcile_workbook(normalized_workbook)
    assert report.passed is True
    assert report.mismatches == ()

def test_reconciliation_keeps_annual_and_semesters_separate(mixed_period_workbook):
    report = reconcile_workbook(mixed_period_workbook)
    assert report.passed is True
    assert report.control_rows == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/importer/test_reconciliation.py -v`

Expected: FAIL porque no existe la conciliación.

- [ ] **Step 3: Implement the control-grain aggregation**

Agrupar `BasePagina` al grano compartido de municipio, cultivo base, ciclo, grupo, subgrupo, año, periodo, nombre científico y estado físico; comparar conteos y sumas de área sembrada, área cosechada y producción con unión externa. No comparar rendimiento por suma ni mezclar periodos.

- [ ] **Step 4: Add diagnostic mismatch coverage**

Alterar una producción en el fixture y afirmar `passed is False`, código `RECONCILIATION_MISMATCH` y diferencia exacta asociada a una clave legible.

- [ ] **Step 5: Run reconciliation tests**

Run: `cd backend && uv run pytest tests/importer/test_reconciliation.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/importer/reconciliation.py backend/tests/importer/test_reconciliation.py
git commit -m "feat: reconcile EVA source and control sheets"
```

### Task 6: Importación transaccional, idempotencia y CLI

**Files:**
- Create: `backend/app/services/importer/import_service.py`, `backend/app/repositories/imports.py`, `backend/app/cli.py`
- Create: `backend/tests/importer/test_import_service.py`, `backend/tests/importer/test_cli.py`
- Modify: `backend/pyproject.toml`

**Interfaces:**
- Consumes: lector, normalizador y conciliador de Tasks 3–5; modelos de Task 2.
- Produces: `EVAImportService.import_file(path: Path) -> ImportResult`, `ImportResult(status, source_version_id, import_run_id, read_count, inserted_count, warning_count, reused, reconciliation: ReconciliationReport)`, comando `uv run eva import --path <xlsx>`.

- [ ] **Step 1: Write failing successful-import and idempotency tests**

```python
def test_import_is_idempotent_by_sha256(session, valid_workbook):
    first = EVAImportService(session).import_file(valid_workbook)
    second = EVAImportService(session).import_file(valid_workbook)
    assert first.inserted_count == 2
    assert second.reused is True
    assert session.scalar(select(func.count(AgriculturalRecord.id))) == 2
```

- [ ] **Step 2: Write the rollback regression test from Review Focus**

```python
def test_failed_batch_leaves_no_partial_facts(session, duplicate_key_workbook):
    with pytest.raises(ImportFailed, match="DUPLICATE_FACT_KEY"):
        EVAImportService(session, batch_size=1).import_file(duplicate_key_workbook)
    assert session.scalar(select(func.count(AgriculturalRecord.id))) == 0
    assert latest_run(session).status == "FAILED"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/importer/test_import_service.py tests/importer/test_cli.py -v`

Expected: FAIL porque el servicio y la CLI no existen.

- [ ] **Step 4: Implement staged transaction boundaries**

Registrar el intento y su hash, ejecutar dimensiones/hechos/conciliación dentro de una transacción atómica, insertar hechos en lotes configurables y solo marcar la versión `PUBLISHED` tras conciliación exitosa. En fallo, revertir los datos del intento y persistir `FAILED` con sus `import_issue`; un hash ya publicado devuelve `ALREADY_IMPORTED`.

- [ ] **Step 5: Implement the private CLI**

La CLI acepta solo una ruta local, imprime JSON resumido sin filas de datos y devuelve código 0 para `IMPORTED`/`ALREADY_IMPORTED`, código 2 para contrato inválido y código 3 para fallo de datos o conciliación.

- [ ] **Step 6: Run importer tests and migration suite**

Run: `cd backend && uv run pytest tests/importer tests/db -v`

Expected: PASS; ninguna prueba deja hechos fuera de su transacción.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/importer/import_service.py backend/app/repositories/imports.py backend/app/cli.py backend/pyproject.toml backend/tests/importer
git commit -m "feat: import EVA workbooks transactionally"
```

### Task 7: Políticas estadísticas y filtros analíticos

**Files:**
- Create: `backend/app/statistics/types.py`, `backend/app/statistics/policies.py`, `backend/app/statistics/warnings.py`, `backend/app/statistics/__init__.py`
- Create: `backend/app/schemas/filters.py`, `backend/tests/statistics/test_policies.py`, `backend/tests/schemas/test_filters.py`

**Interfaces:**
- Consumes: `PeriodType` y campos normalizados de los modelos.
- Produces: `PeriodMode = SOURCE | AGRICULTURAL_YEAR`, `Indicator`, `AgricultureFilters`, `weighted_yield(production: Decimal, harvested: Decimal) -> Decimal | None`, `select_period_grain(records, mode) -> PeriodSelection`, `comparison_warnings(filters) -> tuple[AnalyticalWarning, ...]`.

- [ ] **Step 1: Write failing weighted-yield and zero-denominator tests**

```python
assert weighted_yield(Decimal("30"), Decimal("5")) == Decimal("6")
assert weighted_yield(Decimal("0"), Decimal("0")) is None
```

- [ ] **Step 2: Write the mixed-grain regression test from Review Focus**

```python
def test_agricultural_year_prefers_semesters_for_transient_overlap():
    selected = select_period_grain([annual(100), semester_a(40), semester_b(60)], AGRICULTURAL_YEAR)
    assert selected.production_t == Decimal("100")
    assert selected.used_period_types == {SEMESTER_A, SEMESTER_B}
    assert selected.excluded_period_types == {ANNUAL}
```

Añadir un caso con solo semestre A que afirme `coverage.status == "PARTIAL"` y advertencia `PARTIAL_SEMESTER_COVERAGE`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/statistics tests/schemas/test_filters.py -v`

Expected: FAIL porque las políticas no existen.

- [ ] **Step 4: Implement pure statistical policies and validated filters**

Validar rangos 2019–2025, dependencia municipio-departamento y códigos estables. Emitir `TRANSIENT_METHODOLOGY_BREAK_2021_2022` cuando aplique a cosecha, producción o rendimiento y `RECENT_DATA_PROVISIONAL` para los dos años más recientes de la versión.

- [ ] **Step 5: Run policy tests**

Run: `cd backend && uv run pytest tests/statistics tests/schemas/test_filters.py -v`

Expected: PASS sin acceso a HTTP ni a componentes visuales.

- [ ] **Step 6: Commit**

```bash
git add backend/app/statistics backend/app/schemas/filters.py backend/tests/statistics backend/tests/schemas
git commit -m "feat: define EVA statistical policies"
```

### Task 8: Catálogos, geografía y contrato analítico HTTP

**Files:**
- Create: `backend/app/schemas/common.py`, `backend/app/schemas/catalog.py`, `backend/app/repositories/catalog.py`
- Create: `backend/app/api/v1/router.py`, `backend/app/api/v1/catalog.py`, `backend/app/api/v1/geography.py`
- Create: `backend/tests/api/test_catalog.py`, `backend/tests/api/test_geography.py`, `backend/tests/api/test_openapi.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: modelos y sesión; versión `PUBLISHED` más reciente.
- Produces: `AnalyticalResponse[T]`, `GET /api/v1/catalog/crops`, `/periods`, `/sources`, `/geography/departments`, `/geography/municipalities?department_code=05`.

- [ ] **Step 1: Write failing catalog and dependent-municipality tests**

```python
def test_municipalities_requires_and_applies_department(client, imported_dataset):
    response = client.get("/api/v1/geography/municipalities", params={"department_code": "05"})
    assert response.status_code == 200
    assert {item["department_code"] for item in response.json()["data"]} == {"05"}
```

Verificar además que cultivos conservan `base_code`, variantes anidadas y que fuentes incluyen hash, cobertura y estado sin exponer rutas locales.

- [ ] **Step 2: Run API tests to verify they fail**

Run: `cd backend && uv run pytest tests/api/test_catalog.py tests/api/test_geography.py tests/api/test_openapi.py -v`

Expected: FAIL por rutas ausentes.

- [ ] **Step 3: Implement repositories, schemas and routers**

Ordenar catálogos por nombre normalizado, devolver códigos como texto, filtrar siempre por versión publicada y usar el envelope común también para catálogos/geografía. Registrar `/api/v1` en `create_app()`.

- [ ] **Step 4: Verify OpenAPI and invalid filters**

Probar que OpenAPI enumera las cinco rutas, que un departamento inválido devuelve error estable `INVALID_DEPARTMENT_CODE` y que no existen endpoints públicos de importación o escritura.

- [ ] **Step 5: Run API tests**

Run: `cd backend && uv run pytest tests/api/test_catalog.py tests/api/test_geography.py tests/api/test_openapi.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas backend/app/repositories/catalog.py backend/app/api/v1 backend/app/main.py backend/tests/api
git commit -m "feat: expose EVA catalogs and geography"
```

### Task 9: Resumen, series y rankings reales

**Files:**
- Create: `backend/app/schemas/agriculture.py`, `backend/app/repositories/agriculture.py`, `backend/app/services/analytics.py`, `backend/app/api/v1/agriculture.py`
- Create: `backend/tests/repositories/test_agriculture.py`, `backend/tests/services/test_analytics.py`, `backend/tests/api/test_agriculture.py`
- Modify: `backend/app/api/v1/router.py`

**Interfaces:**
- Consumes: `AgricultureFilters`, políticas de Task 7 y `AnalyticalResponse` de Task 8.
- Produces: `AgricultureRepository.summary(filters)`, `.series(filters)`, `.rankings(filters, dimension, indicator, limit)`; `AnalyticsService`; endpoints `GET /api/v1/agriculture/summary`, `/series`, `/rankings`.

- [ ] **Step 1: Write failing repository aggregation tests**

```python
def test_summary_uses_ratio_of_sums(repository, seeded_records):
    result = repository.summary(AgricultureFilters(year_from=2024, year_to=2024))
    assert result.production_t == Decimal("30")
    assert result.harvested_area_ha == Decimal("5")
    assert result.yield_t_ha == Decimal("6")
```

Añadir filtros por departamento, municipio, cultivo/variante, grupo, subgrupo, ciclo, estado físico y modo temporal; probar que una combinación sin filas produce cobertura vacía, no KPIs cero inventados.

- [ ] **Step 2: Run repository tests to verify they fail**

Run: `cd backend && uv run pytest tests/repositories/test_agriculture.py -v`

Expected: FAIL porque el repositorio no existe.

- [ ] **Step 3: Implement bounded aggregate queries**

Construir una base SQL compartida, aplicar versión publicada y filtros permitidos, agrupar series por año y rankings por `department | municipality | crop`; calcular rendimiento con sumas en SQL y devolver `null` si `SUM(harvested_area_ha)=0`. Limitar rankings a 1–100.

- [ ] **Step 4: Write failing response-envelope tests**

```python
def test_summary_exposes_source_coverage_warnings_and_methodology(client, imported_dataset):
    body = client.get("/api/v1/agriculture/summary", params={"year_from": 2021, "year_to": 2022}).json()
    assert set(body) == {"data", "meta", "coverage", "warnings", "methodology"}
    assert body["meta"]["source_version"]
```

- [ ] **Step 5: Implement AnalyticsService and routers**

El servicio combina resultados, unidad por indicador, cobertura, versión y advertencias; el router solo valida query params y serializa. Un ranking municipal sin departamento devuelve `MISSING_PARENT_FILTER`.

- [ ] **Step 6: Run backend acceptance suite**

Run: `cd backend && uv run pytest -v && uv run ruff check .`

Expected: PASS para ETL, políticas, repositorios, API y OpenAPI.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/agriculture.py backend/app/repositories/agriculture.py backend/app/services/analytics.py backend/app/api/v1 backend/tests
git commit -m "feat: add agricultural dashboard analytics API"
```

### Task 10: Servicios frontend y filtros persistentes en URL

**Files:**
- Create: `frontend/src/types/api.ts`, `frontend/src/types/filters.ts`
- Create: `frontend/src/services/http.ts`, `frontend/src/services/catalog.ts`, `frontend/src/services/agriculture.ts`
- Create: `frontend/src/hooks/use-dashboard-filters.ts`, `frontend/src/hooks/use-dashboard-filters.test.tsx`
- Create: `frontend/src/utils/format.ts`, `frontend/src/utils/format.test.ts`
- Modify: `frontend/package.json`, `frontend/pnpm-lock.yaml`

**Interfaces:**
- Consumes: contratos `/api/v1` de Tasks 8–9 y `NEXT_PUBLIC_API_BASE_URL`.
- Produces: `getCatalogs`, `getDepartments`, `getMunicipalities`, `getSummary`, `getSeries`, `getRankings`; `DashboardFilters`; `useDashboardFilters()` con `setFilter`/`resetFilters`; formateadores que distinguen `0` de `null`.

- [ ] **Step 1: Write failing filter-state tests**

```tsx
expect(readFilters("?department=05&municipality=05001&year=2024")).toEqual({
  department: "05", municipality: "05001", year: 2024, periodMode: "AGRICULTURAL_YEAR"
});
expect(clearDepartment(filters).municipality).toBeUndefined();
```

- [ ] **Step 2: Write failing service and formatter tests**

Verificar que `getSummary(filters)` llama solo a `/api/v1/agriculture/summary`, codifica códigos sin coerción numérica, valida el envelope y que `formatMetric(0)` muestra `0` mientras `formatMetric(null)` muestra `No disponible`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && pnpm vitest run src/hooks/use-dashboard-filters.test.tsx src/utils/format.test.ts`

Expected: FAIL porque los módulos no existen.

- [ ] **Step 4: Implement the typed service boundary and URL state**

Centralizar `fetch` y errores en `services/http.ts`; ningún componente conoce el host. Usar `URLSearchParams` y navegación reemplazable, invalidar municipio al cambiar departamento y adoptar 2025/`AGRICULTURAL_YEAR` como valores iniciales únicamente cuando la URL no los especifique.

- [ ] **Step 5: Run frontend unit tests**

Run: `cd frontend && pnpm vitest run`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types frontend/src/services frontend/src/hooks frontend/src/utils frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat: add typed dashboard data services"
```

### Task 11: Armazón institucional y Dashboard conectado

**Files:**
- Create: `frontend/src/components/layout/app-shell.tsx`, `frontend/src/components/layout/sidebar.tsx`, `frontend/src/components/layout/header.tsx`
- Create: `frontend/src/components/common/async-state.tsx`, `frontend/src/components/common/echart.tsx`, `frontend/src/components/common/methodology-alert.tsx`
- Create: `frontend/src/components/dashboard/dashboard.tsx`, `dashboard-filters.tsx`, `kpi-grid.tsx`, `historical-series.tsx`, `crop-ranking.tsx`, `territorial-ranking.tsx`, `crop-distribution.tsx`
- Create: `frontend/src/components/dashboard/dashboard.test.tsx`, `frontend/src/components/layout/app-shell.test.tsx`
- Modify: `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/globals.css`

**Interfaces:**
- Consumes: servicios, filtros y formatters de Task 10.
- Produces: Dashboard de `/` con cinco estados (`loading`, `data`, `empty`, `error`, `warning`), sidebar de seis rutas, header contextual, filtros dependientes, cuatro KPIs y cuatro visualizaciones reales.

- [ ] **Step 1: Write failing shell and data-state component tests**

```tsx
expect(screen.getByRole("navigation", { name: "Navegación principal" })).toBeVisible();
expect(screen.getByRole("heading", { name: "Resumen General" })).toBeVisible();
expect(screen.getByText("Producción")).toBeVisible();
expect(screen.queryByText(/dato de ejemplo/i)).not.toBeInTheDocument();
```

Cubrir por separado skeleton estable, mensaje vacío asociado a filtros, reintento en error y advertencia metodológica próxima al gráfico afectado.

- [ ] **Step 2: Run component tests to verify they fail**

Run: `cd frontend && pnpm vitest run src/components/layout/app-shell.test.tsx src/components/dashboard/dashboard.test.tsx`

Expected: FAIL porque los componentes no existen.

- [ ] **Step 3: Implement the approved institutional shell**

Crear sidebar verde institucional, header blanco, fondo neutro, superficies blancas, bordes discretos, Lucide con trazo uniforme y tipografía Inter empaquetada. Mostrar los seis módulos; solo Resumen General es enlace en Corte 1 y los demás son etiquetas no interactivas con estado “Disponible en próximos cortes”.

- [ ] **Step 4: Implement filters and the four KPI states**

Consultar catálogos, hacer municipio dependiente del departamento, actualizar URL y solicitar summary/series/rankings en paralelo. Mostrar áreas en ha, producción en t y rendimiento en t/ha; `null` se representa como no disponible.

- [ ] **Step 5: Implement data visualizations with ECharts core**

Usar líneas para serie histórica, barras horizontales para cultivos y territorios, y dona o barras apiladas para distribución según legibilidad. Cargar únicamente módulos ECharts usados, conservar unidades en ejes/tooltips y ofrecer una lista accesible equivalente para cada gráfico.

- [ ] **Step 6: Run component, lint and build checks**

Run: `cd frontend && pnpm lint && pnpm vitest run && pnpm build`

Expected: PASS; `/` no contiene constantes de cifras agrícolas ni llamadas directas a URLs.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app frontend/src/components
git commit -m "feat: build real-data institutional dashboard"
```

### Task 12: Importación completa y verificación vertical del Corte 1

**Files:**
- Create: `backend/tests/acceptance/test_full_workbook.py`, `frontend/e2e/dashboard.spec.ts`, `frontend/playwright.config.ts`
- Create: `docs/corte-1-verification.md`
- Modify: `README.md`, `frontend/package.json`, `frontend/pnpm-lock.yaml`

**Interfaces:**
- Consumes: el sistema completo y el libro de fuente suministrado.
- Produces: evidencia reproducible de hash, 166.733 hechos, 151.312 filas de control, conciliación aprobada, Dashboard real y comandos de arranque para Windows.

- [ ] **Step 1: Write the opt-in full-workbook acceptance test**

```python
@pytest.mark.full_source
def test_supplied_workbook_reconciles_and_imports(source_path, session):
    result = EVAImportService(session).import_file(source_path)
    assert result.read_count == 166_733
    assert result.inserted_count == 166_733
    assert result.reconciliation.control_rows == 151_312
    assert result.reconciliation.passed is True
    assert result.warning_count >= 13_208
```

La prueba se omite con mensaje explícito si `EVA_SOURCE_XLSX` no existe y verifica primero el SHA-256 aprobado.

- [ ] **Step 2: Run the full import against a clean database**

Run: `docker compose up -d db && cd backend && uv run alembic upgrade head && $env:EVA_SOURCE_XLSX='C:\Users\User\Downloads\20260526_BaseAgricola20192025 (2).xlsx'; uv run pytest -m full_source tests/acceptance/test_full_workbook.py -v`

Expected: PASS con 166.733 hechos leídos, conciliación contra 151.312 controles y sin alteración del hash del archivo.

- [ ] **Step 3: Write the failing Dashboard E2E test**

El test visita `/`, espera fuente y versión visibles, cambia departamento y cultivo, confirma que la URL cambia, recarga y comprueba que filtros y KPIs se conservan; también fuerza un filtro vacío y verifica el mensaje “No hay datos para estos filtros”.

- [ ] **Step 4: Run E2E to verify the test fails before final wiring**

Run: `cd frontend && pnpm exec playwright test e2e/dashboard.spec.ts`

Expected: FAIL hasta que la configuración `webServer`, los orígenes CORS y las URLs Compose estén alineados.

- [ ] **Step 5: Wire the production-like local stack and document Windows execution**

Completar README y `docs/corte-1-verification.md` con prerrequisitos, copia de `.env.example`, migración, importación, arranque, URLs, reimportación idempotente, pruebas y solución de errores sin incluir secretos ni el Excel.

- [ ] **Step 6: Run the complete vertical verification**

Run: `docker compose up --build -d && docker compose ps`

Expected: `db`, `backend` y `frontend` sanos.

Run: `cd backend && uv run ruff check . && uv run pytest -m "not full_source" -v`

Expected: PASS.

Run: `cd frontend && pnpm lint && pnpm vitest run && pnpm build && pnpm exec playwright test`

Expected: PASS en escritorio; no hay errores de consola ni respuestas con datos ficticios.

Run: `git status --short`

Expected: solo cambios del Corte 1 previstos; no aparecen `.env`, `backend/data/raw/` ni `.xlsx`.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/acceptance frontend/e2e frontend/playwright.config.ts frontend/package.json frontend/pnpm-lock.yaml README.md docs/corte-1-verification.md
git commit -m "test: verify EVA Explorer corte 1 end to end"
```

## Self-Review Record

- Spec coverage: el plan cubre todos los entregables del Corte 1 y deja records, exportaciones, comparación, mapa, repositorio UI, responsive completo y accesibilidad de endurecimiento para sus cortes aprobados posteriores.
- Step scan: cada tarea tiene una falla observable, una interfaz concreta, implementación mínima, verificación y commit; no incluye cuerpos de producción completos.
- Type consistency: `ParsedWorkbook -> NormalizedWorkbook -> ReconciliationReport -> ImportResult`; `AgricultureFilters` y `AnalyticalResponse` son contratos únicos reutilizados por repositorios, routers y frontend.
- Review Focus: los cinco riesgos tienen una prueba indicada en Tasks 2, 3, 4, 6 y 7.
- Proportion: el plan fija decisiones e invariantes del Corte 1 sin transcribir la implementación.
