# Observatorio Agro Identity and Chart Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebrand the public product as Observatorio Agro, remove the standalone Geovisor navigation entry, and complete consistent visible and accessible chart guidance.

**Architecture:** This is a presentation-layer change with one matching API metadata update. Product branding is replaced in public UI and operator documentation, while source-specific technical identifiers such as `EVAImportService` remain because they identify the ingested source. Existing ECharts option builders stay responsible for axis semantics; non-Cartesian views receive equivalent accessible labels and units.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 6, ECharts 6, Lucide React, Vitest, Playwright, FastAPI, pytest.

**Spec:** `docs/superpowers/specs/2026-10-23-observatorio-agro-rebrand-chat-design.md`

## Global Constraints

- **Observatorio Agro** is the only visible product name.
- EVA appears publicly only as data provenance: “Datos obtenidos de las Evaluaciones Agropecuarias Municipales (EVA), publicadas por la UPRA”.
- Source-specific technical names may retain EVA when they truthfully describe the source or import format.
- Geovisor is not a standalone navigation module; the territorial map belongs inside Resumen General.
- Every Cartesian chart names both axes and includes the indicator unit; maps and donut/list views use titles, legends, units, and accessible descriptions instead of artificial axes.
- This plan is local-only and does not publish or deploy the application.
- Historical decision records under `docs/superpowers/` may retain their original project wording; current public/operator documentation must use Observatorio Agro.
- Execution begins only after the in-progress Corte 2 period-mode task is either completed and committed or explicitly reverted by the controller; implementers must never overwrite that partial work.
- Preserve all uncommitted period-mode work already present in the checkout; no task may reset, overwrite, or stage unrelated changes.

## Review Focus

- Stale product wording in browser metadata, mobile navigation, OpenAPI metadata, or operator docs must not expose “EVA Explorer”; Task 1 pins this with exact string scans and rendering tests.
- Removing Geovisor must not remove or disable Resumen General; Task 1 asserts the dashboard link remains `/` and Geovisor is absent.
- All four indicators must map to the correct axis unit (`ha`, `t`, `t/ha`); Task 2 parameterizes the chart-option tests.
- Non-Cartesian charts and rankings must expose the indicator and unit to screen readers; Task 2 checks accessible names and text fallbacks.
- The longer Observatorio Agro brand must not overflow or hide the main navigation at mobile width; Task 3 adds a browser check at 390×844.

---

## File Structure

- `frontend/src/components/layout/sidebar.tsx`: product mark, navigation inventory, source attribution.
- `frontend/src/components/layout/header.tsx`: current page title and public brand.
- `frontend/src/app/layout.tsx`: browser metadata.
- `frontend/src/components/dashboard/historical-series.tsx`: line-chart axes and accessible description.
- `frontend/src/components/dashboard/crop-ranking.tsx`: bar-chart axes and accessible description.
- `frontend/src/components/dashboard/crop-distribution.tsx`: non-Cartesian indicator/unit description.
- `frontend/src/components/dashboard/territorial-ranking.tsx`: accessible ranking label with level, indicator, and unit.
- `backend/app/main.py`: public API title and POST-ready CORS remains owned by the later assistant plan.
- `README.md` and `docs/corte-1-verification.md`: current operator-facing product naming and provenance.

### Task 1: Replace the public identity and remove Geovisor navigation

**Files:**
- Modify: `frontend/src/components/layout/sidebar.tsx`
- Modify: `frontend/src/components/layout/header.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/layout.test.ts`
- Modify: `frontend/src/components/layout/app-shell.test.tsx`
- Modify: `frontend/src/app/page.test.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/pnpm-lock.yaml`
- Modify: `backend/app/main.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `backend/tests/api/test_openapi.py`
- Modify: `README.md`
- Modify: `docs/corte-1-verification.md`

**Interfaces:**
- Consumes: existing `AppShell`, `/` dashboard route, and source catalog naming.
- Produces: public brand “Observatorio Agro”; navigation labels `Resumen General`, `Consultas`, `Comparador`, `Repositorio`, `Acerca de`; OpenAPI title `Observatorio Agro API`.

- [ ] **Step 1: Write failing public-brand and navigation tests**

  Update `app-shell.test.tsx` to assert a heading/brand named `Observatorio Agro`, the Resumen General link at `/`, absence of `Geovisor`, exactly four `Próximamente` labels, and visible source attribution containing `EVA` and `UPRA`. Add `layout.test.ts` asserting `metadata.title === "Observatorio Agro"`. Update `page.test.tsx` to use the new brand.

- [ ] **Step 2: Write the failing API-title test**

  Extend `test_openapi.py` with `assert document["info"]["title"] == "Observatorio Agro API"`.

- [ ] **Step 3: Run the focused tests to verify RED**

  Run: `cd frontend && pnpm test -- src/components/layout/app-shell.test.tsx src/app/layout.test.ts src/app/page.test.tsx`

  Expected: FAIL because the old brand and Geovisor entry are still rendered.

  Run: `cd backend && uv run pytest tests/api/test_openapi.py -v`

  Expected: FAIL because the OpenAPI title is still `EVA Explorer API`.

- [ ] **Step 4: Implement the public rebrand and navigation inventory**

  Replace the public brand with `Observatorio Agro`, remove the `Map` import and Geovisor module, keep Resumen General at `/`, and render the approved EVA/UPRA source statement only in the provenance area. Set Next metadata and FastAPI title to Observatorio Agro.

- [ ] **Step 5: Rename package metadata without renaming source-specific code**

  Set the frontend package name to `observatorio-agro-frontend`, backend project name to `observatorio-agro-backend`, and backend description to Observatorio Agro. Regenerate only the corresponding lock metadata. Keep the `eva` CLI and `EVAImportService` because they refer to the source importer.

- [ ] **Step 6: Update current operator documentation**

  Reword `README.md` and the title/current-product passages in `docs/corte-1-verification.md` as Observatorio Agro. Preserve references to the EVA workbook and Evaluaciones Agropecuarias Municipales as provenance.

- [ ] **Step 7: Run focused tests and stale-string checks**

  Run: `cd frontend && pnpm test -- src/components/layout/app-shell.test.tsx src/app/layout.test.ts src/app/page.test.tsx`

  Expected: PASS.

  Run: `cd backend && uv run pytest tests/api/test_openapi.py -v`

  Expected: PASS.

  Run: `rg -n "EVA Explorer|Geovisor" frontend/src backend/app README.md docs/corte-1-verification.md`

  Expected: no matches. References to plain `EVA` are allowed only when they identify the data source or importer.

- [ ] **Step 8: Commit**

  ```bash
  git add frontend/src/components/layout/sidebar.tsx frontend/src/components/layout/header.tsx frontend/src/app/layout.tsx frontend/src/app/layout.test.ts frontend/src/components/layout/app-shell.test.tsx frontend/src/app/page.test.tsx frontend/package.json frontend/pnpm-lock.yaml backend/app/main.py backend/pyproject.toml backend/uv.lock backend/tests/api/test_openapi.py README.md docs/corte-1-verification.md
  git commit -m "feat: rebrand platform as Observatorio Agro"
  ```

### Task 2: Complete chart labels, units, and accessible equivalents

**Files:**
- Modify: `frontend/src/components/dashboard/chart-guidance.test.tsx`
- Modify: `frontend/src/components/dashboard/historical-series.tsx`
- Modify: `frontend/src/components/dashboard/crop-ranking.tsx`
- Modify: `frontend/src/components/dashboard/crop-distribution.tsx`
- Modify: `frontend/src/components/dashboard/territorial-ranking.tsx`
- Modify: `frontend/src/components/dashboard/dashboard.test.tsx`

**Interfaces:**
- Consumes: `Indicator`, `indicatorLabel()`, `indicatorUnit()`, `formatIndicator()`, `EChart` text fallback.
- Produces: `buildHistoricalSeriesOption(indicator, points)` and `buildCropRankingOption(indicator, items)` with exact visible/ARIA axis names; unit-bearing accessible names for non-Cartesian views.

- [ ] **Step 1: Add parameterized axis contract tests**

  In `chart-guidance.test.tsx`, cover:

  ```ts
  [
    ["planted_area_ha", "Área sembrada (ha)"],
    ["harvested_area_ha", "Área cosechada (ha)"],
    ["production_t", "Producción (t)"],
    ["yield_t_ha", "Rendimiento (t/ha)"],
  ]
  ```

  For every row assert historical X=`Año`, historical Y=`<label> (<unit>)`, crop-ranking X=`<label> (<unit>)`, and crop-ranking Y=`Cultivo`. These are characterization assertions for already-present labels and must remain green.

- [ ] **Step 2: Add failing accessible-equivalent tests for non-Cartesian views**

  Assert the crop distribution image is named `Distribución de Producción (t) por cultivo` and the territorial ordered list is named `Ranking de departamentos por Producción (t)`. Assert both retain readable text data.

- [ ] **Step 3: Run the focused tests to verify the missing semantics fail**

  Run: `cd frontend && pnpm test -- src/components/dashboard/chart-guidance.test.tsx src/components/dashboard/dashboard.test.tsx`

  Expected: axis characterization passes; non-Cartesian accessible-name assertions FAIL.

- [ ] **Step 4: Implement the missing unit-bearing accessible labels**

  Preserve existing visible axes. Add the indicator unit to `CropDistribution`'s ECharts ARIA description and `EChart.ariaLabel`. Give the `TerritorialRanking` `<ol>` an `aria-label` containing level, indicator, and unit. Keep tooltips and text fallbacks aligned with the same helpers.

- [ ] **Step 5: Run the focused frontend tests**

  Run: `cd frontend && pnpm test -- src/components/dashboard/chart-guidance.test.tsx src/components/dashboard/dashboard.test.tsx`

  Expected: PASS with no warnings.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/components/dashboard/chart-guidance.test.tsx frontend/src/components/dashboard/historical-series.tsx frontend/src/components/dashboard/crop-ranking.tsx frontend/src/components/dashboard/crop-distribution.tsx frontend/src/components/dashboard/territorial-ranking.tsx frontend/src/components/dashboard/dashboard.test.tsx
  git commit -m "fix: complete chart guidance and units"
  ```

### Task 3: Verify the rebrand in desktop and mobile flows

**Files:**
- Modify: `frontend/e2e/dashboard.spec.ts`
- Modify: `frontend/src/app/globals.css` only if the mobile test reveals an actual overflow or inaccessible control.

**Interfaces:**
- Consumes: public AppShell and chart accessible names from Tasks 1–2.
- Produces: browser-level proof that the new identity, navigation, and chart guidance survive the real stack at desktop and 390×844.

- [ ] **Step 1: Extend the browser test with brand/navigation/chart assertions**

  Before changing CSS, assert `Observatorio Agro` is visible, `Geovisor` is absent, Resumen General remains usable, and the production series exposes `Año` and `Producción (t)` through its accessible image name.

- [ ] **Step 2: Add the mobile viewport case**

  Set viewport to 390×844, load `/`, and assert the brand, Resumen General control, indicator selector, and assistant-independent dashboard content are reachable without horizontal document overflow (`document.documentElement.scrollWidth <= window.innerWidth`).

- [ ] **Step 3: Run E2E and repair only observed responsive defects**

  Run: `cd frontend && pnpm e2e -- e2e/dashboard.spec.ts`

  Expected: PASS. If RED is caused by real overflow, make the minimum `globals.css` adjustment and rerun.

- [ ] **Step 4: Run the complete local verification**

  Run: `cd frontend && pnpm test && pnpm lint && pnpm build`

  Expected: all tests pass, lint is clean, production build succeeds.

  Run: `cd backend && uv run ruff check . && uv run pytest -m "not full_source" -v`

  Expected: all non-full-source tests pass and Ruff is clean.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/e2e/dashboard.spec.ts frontend/src/app/globals.css
  git commit -m "test: verify Observatorio Agro identity"
  ```

