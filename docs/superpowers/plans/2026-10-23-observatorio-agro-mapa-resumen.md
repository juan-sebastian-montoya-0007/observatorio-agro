# Observatorio Agro Summary Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an official, traceable Colombian territorial choropleth inside Resumen General and keep Geovisor permanently out of the standalone navigation.

**Architecture:** A local preparation command downloads versioned DANE MGN 2025 GeoJSON snapshots, records hashes, and imports full plus topology-preserving simplified geometries into the existing PostGIS table. A read-only API joins simplified geometry to the same filtered analytics policy used by the dashboard. The frontend renders the returned GeoJSON with the existing ECharts stack, so application runtime does not depend on remote map tiles or the DANE service.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, GeoAlchemy2, PostgreSQL 18/PostGIS 3.6, Next.js 16, React 19, ECharts 6, Vitest, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-23-observatorio-agro-rebrand-chat-design.md`

## Global Constraints

- The map lives inside Resumen General and shares its filters; no standalone Geovisor page or navigation entry is created.
- Cartography comes from DANE MGN 2025 FeatureServer layer 319 (departments) and layer 317 (municipalities).
- Official service: `https://geoportal.dane.gov.co/mparcgis/rest/services/MGN2025/Serv_CapasMGN_2025/FeatureServer`.
- Department join key is `DPTO_CCDGO` (two characters); municipality join key is `MPIO_CDPMP` (five characters). Leading zeroes are preserved.
- Cartography attribution is “Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co”; license is CC BY 4.0.
- Agricultural values remain attributed to EVA/UPRA and follow the existing year-grain and weighted-yield policy.
- Remote DANE calls happen only in an explicit preparation command; dashboard/API runtime uses local PostGIS data.
- Every downloaded body is hashed with SHA-256, retained outside Git under `backend/data/raw/cartography/`, and imported with URL, version, retrieval time, feature count, hash, and license.
- Import is transactional and idempotent for the same version/hash; same version with a different hash fails with `CARTOGRAPHY_VERSION_CONFLICT` rather than silently replacing published geometry.
- Full and simplified valid MultiPolygon geometry are stored in EPSG:4326. Simplification tolerance is `0.01` degrees for departments and `0.003` degrees for municipalities using `ST_SimplifyPreserveTopology`.
- Every department/municipality code present in the published agricultural source must have geometry; import fails coverage validation otherwise, including an explicit regression assertion for code `27493` when present in the source.
- This plan is local-only and does not publish or deploy the application.
- Execution begins after the in-progress period-mode task is resolved; no implementer may reset or overwrite unrelated working-tree changes.

## Review Focus

- GeoJSON with a numeric/truncated DIVIPOLA code must fail instead of losing leading zeroes; Task 1 tests exact string contracts.
- Invalid/empty/self-intersecting geometry must be repaired or rejected before publication; Task 1 checks `ST_IsValid`, non-empty MultiPolygon output, and transaction rollback.
- A department filter must switch the map to municipalities from that department only; Task 2 checks both API query and returned codes.
- Territories without an agricultural value must remain visible with `value=null` and a no-data color, not disappear; Tasks 2–3 pin the left-join behavior.
- Missing local cartography must not break KPIs/charts; Tasks 2–3 require a warning/empty map state while the rest of Resumen General remains usable.

## Source Queries

- Departments: layer `319/query`, `where=1=1`, fields `DPTO_CCDGO,DPTO_CNMBRE,DPTO_NANO`, `returnGeometry=true`, `outSR=4326`, `f=geojson`.
- Municipalities: layer `317/query`, `where=1=1`, fields `DPTO_CCDGO,MPIO_CDPMP,MPIO_CNMBRE,MPIO_NANO,MPIO_TIPO`, `returnGeometry=true`, `outSR=4326`, `f=geojson`.
- The downloader must verify a GeoJSON `FeatureCollection`; it must not trust filename or content type alone.

---

## File Structure

- `backend/app/services/cartography/downloader.py`: official URLs, bounded download, SHA-256, local manifest.
- `backend/app/services/cartography/import_service.py`: validation, transactional import, coverage, idempotence.
- `backend/app/repositories/cartography.py`: local geometry and choropleth reads.
- `backend/app/cartography_cli.py`: explicit download/import commands.
- `backend/app/schemas/map.py`: FeatureCollection and feature property contract.
- `backend/app/services/map.py`: filtered value/geometry response assembly.
- `frontend/src/components/dashboard/territorial-map.tsx`: ECharts choropleth and accessible text fallback.
- `frontend/src/services/map.ts`: typed geography map request.

### Task 1: Download, validate, and import official cartography

**Files:**
- Create: `backend/migrations/versions/20261023_0002_cartography_provenance.py`
- Modify: `backend/app/models/geography.py`
- Create: `backend/app/services/cartography/__init__.py`
- Create: `backend/app/services/cartography/downloader.py`
- Create: `backend/app/services/cartography/import_service.py`
- Create: `backend/app/repositories/cartography.py`
- Create: `backend/app/cartography_cli.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `backend/tests/db/test_initial_migration.py`
- Create: `backend/tests/fixtures/cartography.py`
- Create: `backend/tests/services/cartography/test_downloader.py`
- Create: `backend/tests/services/cartography/test_import_service.py`
- Create: `backend/tests/test_cartography_cli.py`

**Interfaces:**
- Produces: `CartographyDownloader.download_all(output_dir: Path) -> CartographyManifest`.
- Produces: `CartographyImportService.import_manifest(manifest_path: Path) -> CartographyImportResult`.
- Produces: CLI `observatorio-cartography download --output-dir <path>` and `observatorio-cartography import --manifest <path>`.
- Produces `TerritorialGeometry.source_sha256: str` and `retrieved_at: datetime` while retaining existing source URL, version, license, level, code, and simplified flag.

- [ ] **Step 1: Write failing migration/model tests**

  Assert `territorial_geometries` has non-null `source_sha256` (64 characters) and timezone-aware `retrieved_at`; retain the existing identity unique constraint and spatial index. Use an Alembic upgrade from the current revision, not a rewritten initial migration.

- [ ] **Step 2: Run migration tests to verify RED**

  Run: `cd backend && uv run pytest tests/db/test_initial_migration.py -v`

  Expected: FAIL because provenance columns do not exist.

- [ ] **Step 3: Add the provenance migration and model fields**

  Backfill existing rows only if any exist: use a 64-zero legacy sentinel and migration timestamp, then enforce non-null/check constraints. New imports never use the sentinel.

- [ ] **Step 4: Write failing downloader tests using local HTTP fixtures**

  Assert exact official layer URLs/fields, 60-second timeout, 100 MB maximum per response, FeatureCollection validation, atomic `.part` replacement, SHA-256 manifest values, retrieval timestamp, and cleanup on HTTP/JSON/size failure. Tests must not call DANE.

- [ ] **Step 5: Run downloader tests to verify RED**

  Run: `cd backend && uv run pytest tests/services/cartography/test_downloader.py -v`

  Expected: FAIL because the downloader is missing.

- [ ] **Step 6: Implement the standard-library downloader and manifest**

  Use `urllib.request` with explicit User-Agent and bounded chunked reads. Manifest entries contain level, local filename, official query URL, version `MGN 2025`, retrieval timestamp, hash, feature count, join fields, and CC BY 4.0 attribution.

- [ ] **Step 7: Write failing import/CLI tests**

  Use small department/municipality GeoJSON fixtures. Assert string codes, polygon/multipolygon acceptance, geometry repair through PostGIS, full+simplified rows, tolerances, exact agriculture-code coverage, idempotent same-hash reuse, version/hash conflict, invalid feature rollback, and code `27493` preservation. Assert CLI JSON status and non-zero stable error codes.

- [ ] **Step 8: Run import tests to verify RED**

  Run: `cd backend && uv run pytest tests/services/cartography/test_import_service.py tests/test_cartography_cli.py -v`

  Expected: FAIL because import service and CLI do not exist.

- [ ] **Step 9: Implement transactional PostGIS import**

  Convert GeoJSON with `ST_GeomFromGeoJSON`, `ST_SetSRID(…,4326)`, `ST_MakeValid`, polygon extraction, and `ST_Multi`; reject empty/non-polygon output. Insert full geometry and simplified geometry derived in PostGIS. Validate published agricultural code coverage before commit.

- [ ] **Step 10: Run Task 1 tests and Ruff**

  Run: `cd backend && uv run pytest tests/db/test_initial_migration.py tests/services/cartography tests/test_cartography_cli.py -v && uv run ruff check app/services/cartography app/repositories/cartography.py app/cartography_cli.py tests/services/cartography tests/test_cartography_cli.py`

  Expected: PASS and clean lint.

- [ ] **Step 11: Commit**

  ```bash
  git add backend/migrations/versions/20261023_0002_cartography_provenance.py backend/app/models/geography.py backend/app/services/cartography backend/app/repositories/cartography.py backend/app/cartography_cli.py backend/pyproject.toml backend/uv.lock backend/tests/db/test_initial_migration.py backend/tests/fixtures/cartography.py backend/tests/services/cartography backend/tests/test_cartography_cli.py
  git commit -m "feat: import official DANE cartography"
  ```

### Task 2: Expose filtered choropleth GeoJSON from PostGIS

**Files:**
- Create: `backend/app/schemas/map.py`
- Create: `backend/app/services/map.py`
- Modify: `backend/app/repositories/cartography.py`
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/api/v1/geography.py`
- Create: `backend/tests/repositories/test_cartography.py`
- Create: `backend/tests/api/test_map.py`
- Modify: `backend/tests/api/test_openapi.py`

**Interfaces:**
- Consumes: simplified `TerritorialGeometry`, published agricultural version, `AgricultureFilters`, and the same metric/period policy as `AgricultureRepository`.
- Produces: `CartographyRepository.choropleth(filters: AgricultureFilters, level: Literal["department", "municipality"]) -> list[MapFeatureRow]`.
- Produces: `GET /api/v1/geography/map?level=department|municipality&...` returning `AnalyticalResponse[GeoFeatureCollection]`.
- Produces feature properties `{code, name, value, unit, record_count, has_data}` and map metadata `{cartography_version, cartography_source, cartography_license}`.

- [ ] **Step 1: Write failing repository tests**

  Assert department features left-join filtered production/area/yield values, preserve a geometry with no facts as `value=None`, use simplified geometry only, and apply agricultural-year/source-period rules exactly. Assert municipality level is restricted to the selected department and invalid geometry is never emitted.

- [ ] **Step 2: Run repository tests to verify RED**

  Run: `cd backend && uv run pytest tests/repositories/test_cartography.py -v`

  Expected: FAIL because choropleth queries do not exist.

- [ ] **Step 3: Implement shared metric expressions without duplicating statistics**

  Extract only the minimum reusable filtered aggregation from `AgricultureRepository` if required; keep weighted yield as `sum(production) / nullif(sum(harvested), 0)`. Join aggregation to geometry by canonical code and serialize with `ST_AsGeoJSON`.

- [ ] **Step 4: Write failing API tests**

  Assert national department response, department-scoped municipality response, 422 `MISSING_PARENT_FILTER` for national municipality requests, unit/metadata/source attribution, no-data features, missing-cartography warning with empty FeatureCollection, and no DANE network activity.

- [ ] **Step 5: Run API tests to verify RED**

  Run: `cd backend && uv run pytest tests/api/test_map.py tests/api/test_openapi.py -v`

  Expected: FAIL because the map endpoint is absent.

- [ ] **Step 6: Implement schemas, service, and read-only route**

  Parse stored GeoJSON as dictionaries at the response boundary. Extend `ResponseMeta` with optional cartography fields without changing existing response JSON when absent. Include the map GET route in OpenAPI and retain only read-only methods.

- [ ] **Step 7: Run Task 2 tests**

  Run: `cd backend && uv run pytest tests/repositories/test_cartography.py tests/api/test_map.py tests/api/test_openapi.py -v`

  Expected: PASS with exact units and attribution.

- [ ] **Step 8: Commit**

  ```bash
  git add backend/app/schemas/map.py backend/app/services/map.py backend/app/repositories/cartography.py backend/app/schemas/common.py backend/app/api/v1/geography.py backend/tests/repositories/test_cartography.py backend/tests/api/test_map.py backend/tests/api/test_openapi.py
  git commit -m "feat: expose territorial choropleth data"
  ```

### Task 3: Integrate the interactive map into Resumen General

**Files:**
- Modify: `frontend/src/components/common/echart.tsx`
- Create: `frontend/src/components/dashboard/territorial-map.tsx`
- Create: `frontend/src/components/dashboard/territorial-map.test.tsx`
- Modify: `frontend/src/components/dashboard/dashboard.tsx`
- Modify: `frontend/src/components/dashboard/dashboard.test.tsx`
- Create: `frontend/src/services/map.ts`
- Create: `frontend/src/services/map.test.ts`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Consumes: Task 2 map endpoint and current `DashboardFilters` state.
- Produces: `getTerritorialMap(filters, level, signal) -> AnalyticalEnvelope<GeoFeatureCollection>`.
- Produces: `<TerritorialMap collection indicator level onSelectTerritory />` with ECharts map registration, choropleth legend, tooltip, zoom/pan, click selection, and text fallback.

- [ ] **Step 1: Write failing typed-service tests**

  Assert the map request serializes the same dashboard filters, sends level `department` nationally and `municipality` with a department, validates FeatureCollection/features/properties, and forwards cancellation.

- [ ] **Step 2: Write failing map component tests**

  Assert map ARIA label contains level, indicator, and unit; text fallback lists territory/value or “Sin datos”; option contains a visual map legend and gray no-data style; a feature click calls the canonical code; missing cartography renders a setup message without hiding other dashboard panels.

- [ ] **Step 3: Run focused tests to verify RED**

  Run: `cd frontend && pnpm test -- src/services/map.test.ts src/components/dashboard/territorial-map.test.tsx src/components/dashboard/dashboard.test.tsx`

  Expected: FAIL because service/component/integration are missing.

- [ ] **Step 4: Extend the ECharts wrapper for map registration and events**

  Register `MapChart`, `GeoComponent`, and `VisualMapComponent`. Add optional typed map registration and click event props; attach/detach handlers within the existing chart lifecycle and preserve resize/disposal behavior.

- [ ] **Step 5: Implement the choropleth and dashboard integration**

  Fetch map data in the dashboard request group. National view selects a department; department view selects a municipality. Use the active indicator's label/unit for tooltip, legend, ARIA, and text values. Insert the map as the first wide visual panel while retaining rankings as a non-map fallback.

- [ ] **Step 6: Add responsive layout and loading/error states**

  Keep a stable map height, readable legend, zoom/pan controls, keyboard-reachable text fallback, and no horizontal overflow at 390 px. A map-only failure displays within its panel and never replaces KPIs, series, rankings, or filters.

- [ ] **Step 7: Run focused and full frontend tests**

  Run: `cd frontend && pnpm test -- src/services/map.test.ts src/components/dashboard/territorial-map.test.tsx src/components/dashboard/dashboard.test.tsx`

  Expected: PASS.

  Run: `cd frontend && pnpm test && pnpm lint && pnpm build`

  Expected: all tests pass, lint is clean, production build succeeds.

- [ ] **Step 8: Commit**

  ```bash
  git add frontend/src/components/common/echart.tsx frontend/src/components/dashboard/territorial-map.tsx frontend/src/components/dashboard/territorial-map.test.tsx frontend/src/components/dashboard/dashboard.tsx frontend/src/components/dashboard/dashboard.test.tsx frontend/src/services/map.ts frontend/src/services/map.test.ts frontend/src/types/api.ts frontend/src/app/globals.css
  git commit -m "feat: embed territorial map in dashboard"
  ```

### Task 4: Verify source preparation and the complete map flow

**Files:**
- Create: `docs/cartography.md`
- Modify: `README.md`
- Modify: `frontend/e2e/dashboard.spec.ts`
- Create: `backend/tests/acceptance/test_cartography_snapshot.py`
- Modify: `backend/pyproject.toml`

**Interfaces:**
- Consumes: Tasks 1–3 and a user-authorized local DANE snapshot.
- Produces: reproducible download/import instructions, opt-in snapshot acceptance, and browser verification of filter↔map interaction.

- [ ] **Step 1: Document official download/import and licensing**

  Record URLs, layers, fields, license, attribution, local paths, SHA manifest, commands, expected idempotence, and the fact that MGN 2025 boundaries are reference cartography rather than historical boundaries for 2019–2024.

- [ ] **Step 2: Add opt-in full-snapshot acceptance**

  Register marker `cartography_snapshot`; skip unless `DANE_CARTOGRAPHY_MANIFEST` is set. Import into the test database, assert all published agricultural department/municipality codes are covered, code `27493` when present, all simplified geometries valid/non-empty, and same-manifest reuse without row growth.

- [ ] **Step 3: Extend browser verification**

  With local cartography imported, assert the department map is visible and names the active indicator/unit; click a known department and verify URL/filter switch plus municipality map; reset and verify national map; repeat visual availability at 390×844 with no console errors or horizontal overflow.

- [ ] **Step 4: Run default verification**

  Run: `cd backend && uv run ruff check . && uv run pytest -m "not full_source and not cartography_snapshot" -v`

  Expected: all default tests PASS.

  Run: `cd frontend && pnpm test && pnpm lint && pnpm build`

  Expected: all frontend checks PASS.

- [ ] **Step 5: Run opt-in snapshot and browser verification after import**

  Run: `cd backend && uv run pytest -m cartography_snapshot tests/acceptance/test_cartography_snapshot.py -v`

  Run: `cd frontend && pnpm e2e -- e2e/dashboard.spec.ts`

  Expected: snapshot coverage and full browser flow PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add docs/cartography.md README.md frontend/e2e/dashboard.spec.ts backend/tests/acceptance/test_cartography_snapshot.py backend/pyproject.toml
  git commit -m "docs: verify embedded territorial map"
  ```

